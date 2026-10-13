// Console / network / runtime audit on LIVE production: fresh profile first load, idle, warm reload, then a USED profile (same profile dir relaunched).
import fs from 'fs';
import path from 'path';
import { launch, reporter, sleep, invariant, files, inspectPng } from './rc_lib.mjs';
const [url, root, which = 'chrome'] = process.argv.slice(2);
const { check, done } = reporter(`rc_net ${which}`);
const origin = new URL(url).origin;
const collect = (p) => {
  const reqs = [], cons = [], errs = [], csp = [];
  p.on('request', r => reqs.push({ url: r.url(), method: r.method(), type: r.resourceType(), t: Date.now() }));
  p.on('response', r => { const q = reqs.find(x => x.url === r.url() && !x.status); if (q) { q.status = r.status(); q.fromCache = r.fromCache(); q.len = r.headers()['content-length']; q.ct = r.headers()['content-type']; q.cc = r.headers()['cache-control']; } });
  p.on('requestfailed', r => { const q = reqs.find(x => x.url === r.url() && !x.status); if (q) q.status = 'FAILED ' + (r.failure()?.errorText || ''); });
  p.on('console', m => cons.push(m.type() + ': ' + m.text().slice(0, 200)));
  p.on('pageerror', e => errs.push(e.message));
  return { reqs, cons, errs, csp };
};
// ---------- 1. fresh profile
const S = await launch({ url: 'about:blank', root, which, perms: false });
const { p } = S; const c1 = collect(p);
await p.evaluateOnNewDocument(() => { window.__csp = []; document.addEventListener('securitypolicyviolation', e => window.__csp.push(e.violatedDirective + ' ' + e.blockedURI)); });
console.log(`== ${which} ${S.version} ${url}`);
const cdp = await p.createCDPSession(); await cdp.send('Network.enable');
const wire = []; cdp.on('Network.loadingFinished', e => wire.push(e.encodedDataLength));
await p.setViewport({ width: 1366, height: 768 });
await p.goto(url, { waitUntil: 'load' }); await sleep(3000);
const after = c1.reqs.length; await sleep(20000); const idleReqs = c1.reqs.length - after;
const hosts = [...new Set(c1.reqs.map(r => { try { return new URL(r.url).host; } catch (e) { return r.url.slice(0, 30); } }))];
const nonOk = c1.reqs.filter(r => !(typeof r.status === 'number' && r.status < 400));
console.log('requests:', c1.reqs.map(r => `${r.status} ${r.type} ${r.url.replace(origin, '')} ${r.len || ''}`).join('\n   '));
console.log('total wire bytes (first load):', wire.reduce((a, b) => a + b, 0));
check('first load: every request is same-origin (no third-party hosts / trackers)', hosts.length === 1 && hosts[0] === new URL(url).host, JSON.stringify(hosts));
check('first load: every request succeeded (status < 400)', nonOk.length === 0, JSON.stringify(nonOk.map(r => [r.url.replace(origin, ''), r.status])));
check('first load: all requests are HTTPS', c1.reqs.every(r => r.url.startsWith('https://') || r.url.startsWith('data:') || r.url.startsWith('blob:')), '');
check('idle 20 s: no periodic/background network traffic', idleReqs === 0, String(idleReqs));
check('first load: zero page errors', c1.errs.length === 0, JSON.stringify(c1.errs));
const bad = c1.cons.filter(m => /^(error|warning)/.test(m)); check('first load: zero console errors/warnings', bad.length === 0, JSON.stringify(bad));
console.log('all console output on first load:', JSON.stringify(c1.cons.slice(0, 20)));
check('first load: zero CSP violations', (await p.evaluate(() => window.__csp)).length === 0);
const gl = await p.evaluate(() => { const g = window.__renderer.gl; const ext = g.getExtension('WEBGL_debug_renderer_info'); return { renderer: ext ? g.getParameter(ext.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER), vendor: ext ? g.getParameter(ext.UNMASKED_VENDOR_WEBGL) : '', err: g.getError(), version: g.getParameter(g.VERSION), lost: g.isContextLost() }; });
console.log('WebGL:', JSON.stringify(gl));
check('WebGL: context healthy and no pending GL error at idle', !gl.lost && gl.err === 0, JSON.stringify(gl));
// headers of the main documents
const hdr = async (u) => (await fetch(u, { method: 'GET' })).headers;
const heads = {}; for (const f of ['', 'app.js', 'renderer.js', 'favicon.ico']) { const r = await fetch(url + f); heads[f || '/'] = { status: r.status, cc: r.headers.get('cache-control'), ct: r.headers.get('content-type'), hsts: r.headers.get('strict-transport-security'), xcto: r.headers.get('x-content-type-options'), etag: r.headers.get('etag') }; }
console.log('headers:', JSON.stringify(heads, null, 1));
check('favicon resolves (no 404 on every load)', heads['favicon.ico'].status === 200, JSON.stringify(heads['favicon.ico']));
check('JS served with a JavaScript content type, HTML as text/html', /javascript/.test(heads['app.js'].ct) && /text\/html/.test(heads['/'].ct), `${heads['app.js'].ct} | ${heads['/'].ct}`);
console.log('INFO cache-control (html, js):', heads['/'].cc, '|', heads['app.js'].cc, '| HSTS:', heads['/'].hsts, '| nosniff:', heads['/'].xcto);
// state to carry into the used profile: save a preset into localStorage via the real UI
await p.click('#btn-preset-trigger'); await sleep(300); await p.type('#preset-name-input', 'Used Profile Preset'); await p.click('#btn-preset-save'); await sleep(900); await p.keyboard.press('Escape'); await sleep(300);
// ---------- 2. warm reload
c1.reqs.length = 0; await p.reload({ waitUntil: 'load' }); await sleep(2500);
console.log('warm reload requests:', c1.reqs.map(r => `${r.status}${r.fromCache ? ' (cache)' : ''} ${r.url.replace(origin, '')}`).join(' | '));
check('warm reload: no failed requests, no errors, Reference invariant', c1.reqs.every(r => typeof r.status === 'number' && r.status < 400) && c1.errs.length === 0 && (await invariant(p)).length === 0, JSON.stringify([c1.errs]));
await S.browser.close(); await sleep(1500);
// ---------- 3. USED profile: relaunch the same profile dir (cache, localStorage, downloads dir all populated)
const U = await launch({ url, root, which, fresh: false });
const up = U.p; const c2 = { errs: U.log.pageErrors, cons: U.log.console };
const inv = await invariant(up); check('used profile: app starts in canonical Reference with warm cache', inv.length === 0, inv.join());
await up.click('#btn-preset-trigger'); await sleep(400);
const labels = await up.$$eval('#user-presets-list > div', rows => rows.map(r => r.firstChild.textContent)); check('used profile: preset saved in the previous session is still listed', labels.some(l => /Used Profile Preset/.test(l)), JSON.stringify(labels));
await up.keyboard.press('Escape'); await sleep(300);
const before = new Set(files(U.dl)); await up.click('#btn-export-trigger'); await sleep(300); await up.click('.export-res-btn[data-w="1920"]'); await up.click('.export-pass-btn[data-passes="30"]'); await up.click('#btn-export-start');
for (let i = 0; i < 80; i++) { await sleep(250); if (await up.evaluate(() => !document.getElementById('export-result').hidden)) break; } await sleep(800);
const added = files(U.dl).filter(f => !before.has(f)); check('used profile: export still lands as a valid file (name collides with the earlier session → renamed, not overwritten)', added.length === 1 && inspectPng(U.dl, added[0]).ok, JSON.stringify([added, files(U.dl)]));
check('used profile: zero page errors / console errors', c2.errs.length === 0 && !c2.cons.some(m => /^error/.test(m)), JSON.stringify([c2.errs, c2.cons]));
await U.browser.close();
done();
