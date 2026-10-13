// Public-link robustness: malformed / extreme URL parameters on LIVE production. Each case gets its own browser launch and a hard time limit.
import fs from 'fs';
import path from 'path';
import { launch, sleep } from './rc_lib.mjs';
const [base, root, which = 'chrome', filter = ''] = process.argv.slice(2);
const cases = [
  ['n=abc'], ['n=0'], ['n=-5'], ['n=1000000'], ['n=7.5'],
  ['zoom=abc'], ['zoom=0'], ['zoom=-3'], ['zoom=1e300'], ['zoom=2&cx=abc&cy=1e999'],
  ['dpr=abc'], ['dpr=0'], ['dpr=-1'], ['dpr=64'],
  ['particles=abc'], ['particles=-1'], ['particles=0'], ['particles=5000000'],
  ['steps=abc'], ['steps=0'], ['steps=-1'], ['steps=500'],
  ['palette=%3Cimg%20src%3Dx%20onerror%3Dwindow.__xss%3D1%3E'], ['palette=nope'],
  ['randomize=%3Cb%3E'], ['randomize=zzz'], ['morph=zzz'], ['tier=zzz'], ['mode=zzz'], ['mode=explore'],
  ['view=raw'], ['debug'], ['randomize=chaotic&n=32&palette=solar'],
].filter(c => !filter || c[0].includes(filter));
const out = [];
for (const [q] of cases) {
  const r = path.join(root, 'c' + out.length);
  let S; const rec = { q, loaded: false };
  try {
    S = await launch({ url: 'about:blank', root: r, which, perms: false });
    const { p } = S; const errs = []; p.on('pageerror', e => errs.push(e.message.slice(0, 120)));
    const t0 = Date.now();
    try { await p.goto(base + '?' + q, { waitUntil: 'load', timeout: 30000 }); rec.loaded = true; } catch (e) { rec.loaded = 'nav-timeout'; }
    await sleep(3500);
    const probe = await Promise.race([
      p.evaluate(() => { const a = window.__app, m = window.__math, r = window.__renderer; const fin = a && [m.baseA, m.baseB, m.baseC, m.baseD].every(z => Number.isFinite(z.r) && Number.isFinite(z.i)); return { app: !!a, gfxError: !!document.getElementById('graphics-error'), mode: a?.mode, n: m?.n, finiteCoeffs: fin, zoom: r?.zoom, finiteZoom: Number.isFinite(r?.zoom), vc: r?.viewCenter, canvas: [document.getElementById('gl-canvas').width, document.getElementById('gl-canvas').height], lost: !!r?.gl?.isContextLost?.(), xss: window.__xss === undefined, particles: r?.numParticles, steps: r?.stepsPerFrame }; }),
      sleep(12000).then(() => 'UNRESPONSIVE(>12s)'),
    ]);
    rec.probe = probe; rec.errs = errs;
    if (probe !== 'UNRESPONSIVE(>12s)' && probe.app) {
      // does it still animate? measure rAF over 1.5s
      rec.raf = await Promise.race([p.evaluate(() => new Promise(res => { let n = 0; const end = performance.now() + 1500; const f = t => { n++; if (t < end) requestAnimationFrame(f); else res(n); }; requestAnimationFrame(f); })), sleep(8000).then(() => 'raf-stalled')]);
      try { await p.screenshot({ path: path.join(root, `c${out.length}.jpg`), type: 'jpeg', quality: 40 }); } catch (e) { }
    }
    rec.secs = ((Date.now() - t0) / 1000).toFixed(1);
  } catch (e) { rec.fatal = e.message.slice(0, 120); }
  console.log(JSON.stringify(rec).slice(0, 700));
  out.push(rec);
  try { await Promise.race([S.browser.close(), sleep(8000)]); } catch (e) { }
  await sleep(1200);
}
fs.writeFileSync(path.join(root, 'results.json'), JSON.stringify(out, null, 1));
