// Explore-mode interaction matrix on LIVE production with real input: pointer, shock, pan, wheel zoom, sliders at extremes, drift, rapid toggles, 90 s drift soak.
import { launch, reporter, sleep, invariant, appState, openSection, closeAnyDialog, randomizeStyle } from './rc_lib.mjs';
const [url, root, which = 'chrome'] = process.argv.slice(2);
const { check, done } = reporter(`rc_explore ${which}`);
const S = await launch({ url, root, which }); const { p, log } = S;
console.log(`== ${which} ${S.version} ${url}`);
const fin = () => p.evaluate(() => { const m = window.__math, r = window.__renderer; const z = c => Number.isFinite(c.r) && Number.isFinite(c.i); return [m.a, m.b, m.c, m.d, m.baseA, m.baseB, m.baseC, m.baseD, m.userOffsetA, m.userOffsetB, m.userOffsetC, m.userOffsetD, m.pointerCurrent, m.pointerTarget].every(z) && Number.isFinite(m.shockMag) && Number.isFinite(m.time) && Number.isFinite(r.zoom) && Number.isFinite(r.targetZoom) && r.viewCenter.every(Number.isFinite) && Number.isInteger(m.n); });
const mathv = () => p.evaluate(() => { const m = window.__math, r = window.__renderer; return { pc: [m.pointerCurrent.r, m.pointerCurrent.i], pt: [m.pointerTarget.r, m.pointerTarget.i], shock: m.shockMag, zoom: r.targetZoom, vc: [...r.targetViewCenter], time: m.time, drift: m.evolving }; });
const mag = v => Math.hypot(v[0], v[1]);

await p.click('#btn-mode-explore'); await sleep(400);
// pointer perturbation
await p.mouse.move(300, 300); await p.mouse.move(900, 500, { steps: 12 }); await sleep(600); let v = await mathv();
check('Explore: hovering over the canvas bends the mathematics (pointer perturbation non-zero)', mag(v.pt) > 0 || mag(v.pc) > 0, JSON.stringify(v));
// pointerleave returns target to zero
await p.evaluate(() => document.getElementById('gl-canvas').dispatchEvent(new PointerEvent('pointerleave', { bubbles: true }))); await p.mouse.move(683, 5); await sleep(250); // real pointer leaves canvas to top bar region? (bar is above canvas)
await p.mouse.move(683, 30); await sleep(1500); v = await mathv();
check('pointer leaving the canvas (to the UI bar) returns the perturbation to neutral', mag(v.pt) < 1e-6 || mag(v.pc) < 0.02, JSON.stringify(v));
// shock
await p.mouse.move(700, 450); await p.mouse.down(); await sleep(60); const sh = (await mathv()).shock; await p.mouse.up(); await sleep(2500); const sh2 = (await mathv()).shock;
check('click shock fires and then decays', sh > 0 && sh2 < sh, JSON.stringify([sh, sh2]));
// wheel zoom
const z0 = (await mathv()).zoom; await p.mouse.move(700, 450); for (let i = 0; i < 6; i++) { await p.mouse.wheel({ deltaY: -120 }); await sleep(40); } await sleep(300); const z1 = (await mathv()).zoom;
for (let i = 0; i < 400; i++) { await p.mouse.wheel({ deltaY: -400 }); } await sleep(300); const zmax = (await mathv()).zoom; for (let i = 0; i < 600; i++) { await p.mouse.wheel({ deltaY: 400 }); } await sleep(300); const zmin = (await mathv()).zoom;
check('wheel zoom in increases zoom; hammering it stays within [0.3, 500] both ways', z1 > z0 && zmax <= 500.0001 && zmin >= 0.2999, JSON.stringify({ z0, z1, zmax, zmin }));
check('state stays finite after wheel hammering', await fin());
// pan (Shift-drag) and R reset
await p.keyboard.down('Shift'); await p.mouse.move(500, 400); await p.mouse.down(); await p.mouse.move(700, 520, { steps: 10 }); await p.mouse.up(); await p.keyboard.up('Shift'); await sleep(300); const vc = (await mathv()).vc;
check('Shift-drag pans the view', vc[0] !== 0 || vc[1] !== 0, JSON.stringify(vc));
await p.keyboard.press('r'); await sleep(1500); v = await mathv(); check('R resets the view (zoom back to 1.65, centre 0,0) and stays in Explore', Math.abs(v.zoom - 1.65) < 1e-6 && v.vc[0] === 0 && v.vc[1] === 0 && (await appState(p)).mode === 'explore', JSON.stringify(v));
// zoom buttons
await openSection(p, 'view'); await p.click('#btn-zoom-in'); await sleep(300); const zi = (await mathv()).zoom; await p.click('#btn-zoom-out'); await sleep(300); await p.click('#btn-zoom-reset'); await sleep(900);
check('zoom +/−/reset buttons work in Explore', zi > 1.65 && Math.abs((await mathv()).zoom - 1.65) < 1e-6, String(zi));
// sliders: extremes by real keyboard (Home/End) and real mouse drag
await openSection(p, 'math'); await p.evaluate(() => { if (!window.__app.coeffDrawerVisible) document.getElementById('btn-coeff').click(); }); await sleep(400);
for (const id of ['slider-a-re', 'slider-b-im', 'slider-c-re', 'slider-d-im']) {
  await p.focus('#' + id); await p.keyboard.press('Home'); await sleep(120); const lo = await fin(); await p.keyboard.press('End'); await sleep(120); const hi = await fin();
  const val = await p.$eval('#' + id, e => [e.min, e.max, e.value]);
  check(`slider ${id}: extremes (Home/End ${val[0]}..${val[2]}) keep every value finite`, lo && hi, JSON.stringify(val));
}
await sleep(1200); const sRender = await p.evaluate(() => new Promise(r => { let n = 0; const end = performance.now() + 1000; const f = t => { n++; t < end ? requestAnimationFrame(f) : r(n); }; requestAnimationFrame(f); })); check('still animating (>=40 frames/s) with sliders at maximum', sRender >= 40, String(sRender));
await p.click('#btn-reset-coeffs'); await sleep(400); const zeroed = await p.evaluate(() => [window.__math.userOffsetA, window.__math.userOffsetB, window.__math.userOffsetC, window.__math.userOffsetD].every(c => c.r === 0 && c.i === 0)); check('Reset offsets zeroes all four offsets', zeroed);
// drift
await p.keyboard.press('Escape'); await closeAnyDialog(p);
const t0 = (await mathv()); await p.evaluate(() => { window.__math.evolving = true; }); await sleep(2000); const t1 = await mathv(); check('drift on: time advances', t1.time > t0.time, JSON.stringify([t0.time, t1.time]));
await p.evaluate(() => document.activeElement?.blur?.()); await p.keyboard.press(' '); await sleep(300); const pausedState = (await mathv()).drift; const tp0 = (await mathv()).time; await sleep(1000); const tp1 = (await mathv()).time;
check('Space pauses drift (time stops)', pausedState === false && Math.abs(tp1 - tp0) < 1e-9, JSON.stringify([pausedState, tp0, tp1])); await p.keyboard.press(' '); await sleep(300);
check('Space resumes drift', (await mathv()).drift === true);
// Documented caveat: with a toolbar button focused, Space activates that button (by design). Record what actually happens.
await p.focus('#btn-readout'); const ro0 = await p.evaluate(() => window.__app.readoutVisible); await p.keyboard.press(' '); await sleep(250); const ro1 = await p.evaluate(() => window.__app.readoutVisible); console.log('INFO Space with a focused toolbar button: drift state unchanged =', (await mathv()).drift, '| the focused button was activated instead =', ro0 !== ro1); await p.keyboard.press(' '); await p.evaluate(() => document.activeElement?.blur?.());
// bloom / readout / raw / debug toggles
for (const [k, label] of [['b', 'bloom'], ['o', 'readout'], ['t', 'raw'], ['d', 'debug']]) { await p.keyboard.press(k); await sleep(250); await p.keyboard.press(k); await sleep(250); }
check('toggle keys B/O/T/D twice each leave everything finite and alive', await fin() && log.pageErrors.length === 0);
// rapid mode toggling stress: stash invariants
await p.keyboard.press('3'); await sleep(250); await openSection(p, 'math'); await p.click('.sym-btn[data-n="8"]'); await sleep(200); await p.keyboard.press('Escape'); const snapN = (await appState(p)).n;
for (let i = 0; i < 40; i++) { await p.click('#btn-mode-reference'); await p.click('#btn-mode-explore'); }
await sleep(500); const afterN = (await appState(p)).n;
check('40 rapid Reference<->Explore toggles: Explore session intact (n unchanged), state finite', afterN === snapN && await fin(), `${snapN} -> ${afterN}`);
await p.click('#btn-mode-reference'); await sleep(400); const bad = await invariant(p); check('...and Reference canonical afterwards', bad.length === 0, bad.join());
// 90 s drift soak in Explore chaotic
await p.keyboard.press('2'); await randomizeStyle(p, 'chaotic'); await p.evaluate(() => { window.__math.evolving = true; }); const f0 = await p.evaluate(() => window.__renderer.accumulationFrames);
await p.mouse.move(400, 300); for (let i = 0; i < 18; i++) { await p.mouse.move(400 + (i % 6) * 120, 250 + (i % 3) * 120, { steps: 5 }); await sleep(5000); if (i % 6 === 5) await p.mouse.click(700, 450); }
const okFinite = await fin(); const lost = await p.evaluate(() => window.__renderer.gl.isContextLost()); const gerr = await p.evaluate(() => window.__renderer.gl.getError());
check('90 s of drift + pointer motion + shocks in chaotic Explore: everything finite, context healthy, no GL error', okFinite && !lost && gerr === 0, JSON.stringify({ okFinite, lost, gerr }));
await p.click('#btn-mode-reference'); await sleep(400); const bad2 = await invariant(p); check('after the 90 s soak, Reference canonical', bad2.length === 0, bad2.join());
check('no uncaught page errors', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
check('no console errors/warnings', !log.console.some(m => /^(error|warning)/.test(m)), JSON.stringify(log.console.slice(0, 5)));
done(); await S.browser.close();
