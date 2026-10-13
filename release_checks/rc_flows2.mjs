// Remaining Stage 2/5/9/12 flow-matrix rows on LIVE production, real browser:
// settled Reference does no GPU work, every Randomize family (interact / Reference / return / re-randomize), export cancel at specific stages
// (developing / near completion / encoding) with retry, export after preset load + Explore interaction + settle, default-permission clipboard (real paste),
// controls and modal backdrops never leak input to the artwork.
import fs from 'fs';
import path from 'path';
import { launch, reporter, sleep, invariant, appState, files, inspectPng, openSection, closeAnyDialog, randomizeStyle } from './rc_lib.mjs';
const [url, root, which = 'chrome'] = process.argv.slice(2);
const { check, done } = reporter(`rc_flows2 ${which}`);
const R = n => path.join(root, n);

// ---------- A. settled Reference + Auto reporting + draw-call accounting
{
  const S = await launch({
    url, root: R('settle'), which, perms: false, init: () => {
      const proto = WebGL2RenderingContext.prototype; window.__draws = 0; window.__queries = 0;
      for (const n of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced', 'drawRangeElements']) { const o = proto[n]; if (o) proto[n] = function (...a) { window.__draws++; return o.apply(this, a); }; }
      for (const n of ['beginQuery']) { const o = proto[n]; if (o) proto[n] = function (...a) { window.__queries++; return o.apply(this, a); }; }
    }
  });
  const { p, log } = S;
  const t0 = Date.now(); let settled = false; while (Date.now() - t0 < 120000) { settled = await p.evaluate(() => window.__renderer.referenceSettled === true); if (settled) break; await sleep(1000); }
  const secs = ((Date.now() - t0) / 1000).toFixed(0);
  check('Reference development completes ("settled") on its own', settled, `after ~${secs}s`);
  await sleep(1500); const d0 = await p.evaluate(() => ({ draws: window.__draws, q: window.__queries, frames: window.__renderer.accumulationFrames })); await sleep(4000); const d1 = await p.evaluate(() => ({ draws: window.__draws, q: window.__queries, frames: window.__renderer.accumulationFrames, settled: window.__renderer.referenceSettled }));
  check('settled Reference at rest: zero draw calls, zero timer queries and no new accumulation frames in 4 s', d1.settled && d1.draws === d0.draws && d1.q === d0.q && d1.frames === d0.frames, JSON.stringify([d0, d1]));
  // opening/closing UI does not restart expensive work
  await p.click('#btn-controls'); await sleep(500); await p.keyboard.press('Escape'); await sleep(500); await p.click('#btn-help'); await sleep(400); await p.keyboard.press('Escape'); await sleep(800);
  const d2 = await p.evaluate(() => ({ draws: window.__draws, settled: window.__renderer.referenceSettled }));
  check('opening Controls/Help over a settled Reference does not restart simulation (no new draw calls)', d2.settled && d2.draws <= d1.draws + 4, JSON.stringify([d1.draws, d2]));
  // Explore wakes it; Reference re-settles
  await p.click('#btn-mode-explore'); await sleep(1500); const awake = await p.evaluate(() => ({ settled: window.__renderer.referenceSettled, draws: window.__draws }));
  await p.click('#btn-mode-reference'); const t1 = Date.now(); let s2 = false; while (Date.now() - t1 < 120000) { s2 = await p.evaluate(() => window.__renderer.referenceSettled === true); if (s2) break; await sleep(1000); }
  check('Explore does real work, and returning to Reference re-settles', awake.draws > d2.draws && s2, JSON.stringify({ awake, s2, secs: ((Date.now() - t1) / 1000).toFixed(0) }));
  const bad = await invariant(p); check('Reference canonical after settle / wake / re-settle', bad.length === 0, bad.join());
  // Auto tier reporting
  await openSection(p, 'quality'); const tl = await p.evaluate(() => ({ txt: document.getElementById('quality-current-tier').textContent, hidden: document.getElementById('quality-current-tier').hidden }));
  check('Auto: panel reports "Current tier: <name>"', !tl.hidden && /^Current tier: \w+/.test(tl.txt), JSON.stringify(tl));
  await p.click('.quality-btn[data-tier="high"]'); await sleep(300); const tl2 = await p.evaluate(() => document.getElementById('quality-current-tier').hidden); await p.click('.quality-btn[data-tier="bruteforce"]'); await sleep(300);
  const warn = await p.evaluate(() => ({ hidden: document.getElementById('quality-warning').hidden, txt: document.getElementById('quality-warning').textContent }));
  check('manual tier hides the Auto line; Brute Force shows the exact warning', tl2 === true && warn.hidden === false && warn.txt.trim() === 'Maximum live GPU load — high-end hardware recommended.', JSON.stringify(warn));
  await p.click('.quality-btn[data-tier="auto"]'); await sleep(300);
  check('no page errors', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
  await S.browser.close();
}

// ---------- B..F share one browser session
const S = await launch({ url, root: R('main'), which }); const { p, dl, log } = S;
const finite = () => p.evaluate(() => { const m = window.__math; return [m.a, m.b, m.c, m.d].every(z => Number.isFinite(z.r) && Number.isFinite(z.i)) && Number.isInteger(m.n) && m.n >= 2 && m.n <= 64; });
const ui = () => p.evaluate(() => ({ running: window.__app.isExporting, result: !document.getElementById('export-result').hidden, notice: !document.getElementById('export-notice').hidden ? document.getElementById('export-notice').innerText.replace(/\n/g, ' ') : '', label: document.getElementById('export-status-label').innerText, pct: parseInt(document.getElementById('export-status-pct').innerText) || 0, pctTxt: document.getElementById('export-status-pct').innerText }));
const waitEnd = async (ms = 120000) => { const t = Date.now(); while (Date.now() - t < ms) { const s = await ui(); if (s.result || s.notice) return s; await sleep(120); } return await ui(); };

// B. every randomize family: generate -> interact -> Reference -> return to Explore -> randomize again
for (const style of ['conradi-like', 'subtle', 'organic', 'dense lace', 'symmetric', 'chaotic']) {
  await randomizeStyle(p, style); const a1 = await appState(p);
  await p.mouse.move(500, 350); await p.mouse.move(800, 480, { steps: 8 }); await p.mouse.click(800, 480); await p.keyboard.press('r'); await sleep(250);
  const f1 = await finite(); await p.click('#btn-mode-reference'); await sleep(350); const refBad = await invariant(p);
  await p.click('#btn-mode-explore'); await sleep(350); const a2 = await appState(p); await randomizeStyle(p, style); const a3 = await appState(p);
  check(`Randomize [${style}]: generate → interact → Reference → Explore (session resumes, n=${a1.n}) → randomize again`, a1.mode === 'explore' && f1 && refBad.length === 0 && a2.mode === 'explore' && a2.n === a1.n && a2.a[0] === a1.a[0] && a3.mode === 'explore' && await finite(), JSON.stringify([a1.n, a2.n, a1.a[0] === a2.a[0], refBad]));
}
await p.click('#btn-mode-reference'); await sleep(300);

// C. export cancel at specific stages, with retry + file hygiene
const cdp = await p.createCDPSession();
const openMaster = async (passes = '240') => { if (!(await p.evaluate(() => window.__app.exportModal.classList.contains('visible')))) { await p.click('#btn-export-trigger'); await sleep(250); } await p.click('#tab-export-refmaster'); await p.click(`.refmaster-pass-btn[data-passes="${passes}"]`); };
const usable = async () => { await p.evaluate(() => { const b = document.getElementById('btn-export-cancel'); if (b && !window.__app.isExporting && document.getElementById('export-modal').classList.contains('visible')) b.click(); }); await sleep(300); await p.click('#btn-mode-explore'); await sleep(200); await p.click('#btn-randomize-action'); await sleep(250); const ok = (await appState(p)).mode === 'explore' && await finite(); await p.click('#btn-mode-reference'); await sleep(300); return ok; };
const stageCancel = async (name, pred) => {
  const before = new Set(files(dl)); await cdp.send('Emulation.setCPUThrottlingRate', { rate: 10 });
  await openMaster('240'); await p.click('#btn-export-start'); let hit = null; const t = Date.now();
  while (Date.now() - t < 90000) { const s = await ui(); if (s.running && pred(s)) { hit = s; break; } if (!s.running && (s.result || s.notice)) break; await sleep(40); }
  if (hit) await p.click('#btn-export-cancel'); const end = await waitEnd(60000); await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 }); await sleep(2500);
  const added = files(dl).filter(f => !before.has(f)); const st = await ui();
  const zero = added.filter(f => fs.statSync(path.join(dl, f)).size === 0);
  check(`cancel ${name}: reached the stage (${hit ? hit.label + ' ' + hit.pctTxt : 'NOT REACHED'}), "Export canceled", no file, no success claim, no stale progress, no zero-byte file`, !!hit && /canceled/i.test(end.notice) && !end.result && added.length === 0 && zero.length === 0 && st.pctTxt === '' && st.label === '', JSON.stringify({ hit, end: end.notice, added }));
  check(`cancel ${name}: app remains usable`, await usable());
  // retry
  const b2 = new Set(files(dl)); await openMaster('120'); await p.click('#btn-export-start'); const s2 = await waitEnd(120000); await sleep(1200); const a2 = files(dl).filter(f => !b2.has(f));
  check(`retry after cancel ${name}: completes with one valid 4096² PNG`, s2.result && a2.length === 1 && inspectPng(dl, a2[0]).ok && inspectPng(dl, a2[0]).w === 4096, JSON.stringify({ a2 }));
  await p.evaluate(() => { const b = document.getElementById('btn-export-cancel'); if (b && !window.__app.isExporting) b.click(); }); await sleep(300);
};
await stageCancel('mid-development (<40%)', s => /Developing/.test(s.label) && s.pct >= 10 && s.pct < 40);
await stageCancel('near completion (>=90%, still developing or finishing)', s => s.pct >= 90);
await stageCancel('during PNG encoding', s => /Encoding/.test(s.label));

// D. export after preset load / Explore interaction / settle, 60-pass default, no duplicate downloads from one click
const expStd = async (res, passes) => { const before = new Set(files(dl)); await p.click('#btn-export-trigger'); await sleep(250); await p.click('#tab-export-standard'); await p.click(`.export-res-btn[data-w="${res}"]`); await p.click(`.export-pass-btn[data-passes="${passes}"]`); await p.click('#btn-export-start'); const s = await waitEnd(120000); await sleep(1200); const added = files(dl).filter(f => !before.has(f)); await p.click('#btn-export-cancel'); await sleep(300); return { s, added }; };
await p.click('#btn-preset-trigger'); await sleep(300); const cur = await p.$$('#curated-presets-list button'); await cur[2].click(); await sleep(600); for (const h of cur) await h.dispose();
const r1 = await expStd('1920', '60');
check('export after loading a curated preset (Explore, 1920×1080, default 60 passes): one valid PNG, Explore session intact', r1.s.result && r1.added.length === 1 && inspectPng(dl, r1.added[0]).ok && inspectPng(dl, r1.added[0]).w === 1920 && (await appState(p)).mode === 'explore', JSON.stringify(r1.added));
await p.mouse.move(500, 350); await p.mouse.move(900, 500, { steps: 8 }); await p.mouse.click(900, 500); await sleep(300);
const r2 = await expStd('3840', '120');
check('export right after Explore hover/shock interaction (3840×2160, 120): valid PNG, no duplicate file from one click', r2.s.result && r2.added.length === 1 && inspectPng(dl, r2.added[0]).ok && inspectPng(dl, r2.added[0]).w === 3840, JSON.stringify(r2.added));
await p.click('#btn-mode-reference'); await sleep(300); const r3 = await expStd('1920', '60');
check('Reference export (1920×1080, 60 passes) valid and named after the Reference', r3.s.result && r3.added.length === 1 && /reference/i.test(r3.added[0]) && inspectPng(dl, r3.added[0]).ok, JSON.stringify(r3.added));
check('Reference canonical after all of the above', (await invariant(p)).length === 0);

// E. controls and modal backdrops never leak input to the artwork
await p.click('#btn-mode-explore'); await sleep(300);
await p.evaluate(() => { window.__maxShock = 0; window.__maxPt = 0; setInterval(() => { const m = window.__math; window.__maxShock = Math.max(window.__maxShock, m.shockMag); window.__maxPt = Math.max(window.__maxPt, Math.hypot(m.pointerTarget.r, m.pointerTarget.i)); }, 16); });
await p.mouse.move(683, 30); await sleep(1500); await p.evaluate(() => { window.__maxShock = 0; window.__maxPt = 0; });
await p.click('#btn-controls'); await sleep(500); await openSection(p, 'math'); await p.evaluate(() => { if (!window.__app.coeffDrawerVisible) document.getElementById('btn-coeff').click(); }); await sleep(300);
for (const sel of ['.sym-btn[data-n="8"]', '.sym-btn[data-n="16"]', '#btn-reset-coeffs', '#btn-pause']) { await p.click(sel).catch(() => { }); await sleep(120); }
const sl = await p.$('#slider-a-re'); await sl.evaluate(e => e.scrollIntoView({ block: 'center' })); const bx = await sl.boundingBox(); await p.mouse.move(bx.x + bx.width * 0.5, bx.y + bx.height / 2); await p.mouse.down(); await p.mouse.move(bx.x + bx.width * 0.9, bx.y + bx.height / 2, { steps: 8 }); await p.mouse.up(); await sl.dispose();
await sleep(500); const leak1 = await p.evaluate(() => ({ s: window.__maxShock, pt: window.__maxPt }));
check('clicking and dragging controls in the open panel causes no shock / pointer disturbance on the artwork', leak1.s === 0 && leak1.pt < 1e-9, JSON.stringify(leak1));
await p.keyboard.press('Escape'); await sleep(300); await p.evaluate(() => { window.__maxShock = 0; window.__maxPt = 0; });
for (const [trig, id] of [['#btn-help', 'help-modal'], ['#btn-preset-trigger', 'preset-modal'], ['#btn-export-trigger', 'export-modal']]) {
  await p.click(trig); await sleep(400); const before = JSON.stringify(await appState(p)); const cam0 = await p.evaluate(() => ({ z: window.__renderer.targetZoom, vc: window.__renderer.targetViewCenter.slice() }));
  await p.mouse.move(250, 400); await p.mouse.move(1100, 420, { steps: 8 }); await p.mouse.click(1100, 420); await p.mouse.click(60, 700); await p.keyboard.down('Shift'); await p.mouse.move(300, 300); await p.mouse.down(); await p.mouse.move(500, 400, { steps: 5 }); await p.mouse.up(); await p.keyboard.up('Shift'); await p.mouse.wheel({ deltaY: -600 }); await sleep(300);
  const after = JSON.stringify(await appState(p)); const open = await p.evaluate(id => document.getElementById(id).classList.contains('visible'), id); const lk = await p.evaluate(() => ({ s: window.__maxShock, pt: window.__maxPt, zoom: window.__renderer.targetZoom, vc: window.__renderer.targetViewCenter.slice() }));
  check(`${id}: mouse move/click/Shift-drag/wheel on the backdrop does not touch the artwork (no shock, no pan/zoom, state unchanged)`, before === after && lk.s === 0 && lk.pt < 1e-9 && lk.zoom === cam0.z && lk.vc[0] === cam0.vc[0] && lk.vc[1] === cam0.vc[1], JSON.stringify({ lk, cam0, same: before === after, open }));
  await closeAnyDialog(p);
}
await p.click('#btn-mode-reference'); await sleep(300);

// F. fresh profile default permissions: Copy JSON succeeds and a REAL paste (Ctrl+V) yields the JSON
{
  const F = await launch({ url, root: R('fresh'), which, perms: false }); const q = F.p;
  await q.click('#btn-preset-trigger'); await sleep(300); await q.type('#preset-name-input', 'Paste Check'); await q.click('#btn-preset-copy'); await sleep(700);
  const toast = await q.evaluate(() => document.getElementById('toast-banner').innerText);
  await q.$eval('#preset-name-input', e => { e.value = ''; e.focus(); }); await q.keyboard.down('Control'); await q.keyboard.press('v'); await q.keyboard.up('Control'); await sleep(300);
  const pasted = await q.$eval('#preset-name-input', e => e.value);
  check('fresh profile (no permission overrides): Copy JSON reports success and a real Ctrl+V paste contains the JSON with the typed name', /copied to clipboard/i.test(toast) && /"name":\s*"Paste Check"/.test(pasted) && /"symmetry":\s*16/.test(pasted), toast + ' | ' + pasted.slice(0, 80));
  await F.browser.close();
}
check('no uncaught page errors', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
const cons = log.console.filter(m => !/Export error|Reference Master Export/.test(m)); check('no unexpected console errors/warnings', cons.length === 0, JSON.stringify(cons.slice(0, 5)));
done(); await S.browser.close();
