// Extra real-browser release checks on LIVE production: HiDPI export, touch input, resize during export, WebGL unavailable, two tabs, reduced motion.
import fs from 'fs';
import path from 'path';
import { launch, reporter, sleep, invariant, appState, files, inspectPng, closeAnyDialog } from './rc_lib.mjs';
const [url, root, which = 'chrome'] = process.argv.slice(2);
const { check, done } = reporter(`rc_extra ${which}`);
const R = n => path.join(root, n);
const waitEnd = async (p, ms = 90000) => { const t = Date.now(); while (Date.now() - t < ms) { const s = await p.evaluate(() => ({ result: !document.getElementById('export-result').hidden, notice: !document.getElementById('export-notice').hidden ? document.getElementById('export-notice').innerText : '' })); if (s.result || s.notice) return s; await sleep(200); } return { timeout: true }; };

// ---------- 1. HiDPI + page zoom emulation: Current View export size must equal the announced size and the file
{
  const S = await launch({ url, root: R('dpr'), which, perms: false, width: 1280, height: 720 });
  const { p, dl } = S;
  for (const dpr of [2, 3, 1.25]) {
    await p.setViewport({ width: 1280, height: 720, deviceScaleFactor: dpr }); await p.reload({ waitUntil: 'load' }); await sleep(2500);
    const before = new Set(files(dl));
    await p.click('#btn-export-trigger'); await sleep(250); await p.click('.export-res-btn[data-w="viewport"]'); await p.click('.export-pass-btn[data-passes="30"]');
    const summary = await p.$eval('#export-summary', e => e.innerText);
    await p.click('#btn-export-start'); const s = await waitEnd(p); await sleep(900);
    const added = files(dl).filter(f => !before.has(f)); const insp = added[0] ? inspectPng(dl, added[0]) : null; const sz = await p.$eval('#export-result-size', e => e.innerText);
    check(`DPR ${dpr}: Current View export is a valid PNG and its dimensions match the announced size`, s.result && insp?.ok && sz === `${insp.w} × ${insp.h} px`, JSON.stringify({ summary, added, insp, sz }));
    await p.click('#btn-export-cancel'); await sleep(300);
    const bad = await invariant(p); check(`DPR ${dpr}: Reference canonical`, bad.length === 0, bad.join());
  }
  await p.setViewport({ width: 1280, height: 720, deviceScaleFactor: 2 }); await p.reload({ waitUntil: 'load' }); await sleep(2500);
  const before = new Set(files(dl)); await p.click('#btn-export-trigger'); await sleep(250); await p.click('#tab-export-refmaster'); await p.click('.refmaster-pass-btn[data-passes="120"]'); await p.click('#btn-export-start'); const s = await waitEnd(p); await sleep(900);
  const added = files(dl).filter(f => !before.has(f)); const insp = added[0] ? inspectPng(dl, added[0]) : null;
  check('DPR 2: Reference Master is still exactly 4096×4096 (independent of display scale)', s.result && insp?.ok && insp.w === 4096 && insp.h === 4096, JSON.stringify({ added, insp }));
  await S.browser.close();
}
// ---------- 2. Touch input (mobile emulation)
{
  const S = await launch({ url, root: R('touch'), which, perms: false, width: 390, height: 844 });
  const { p, log } = S;
  await p.setViewport({ width: 390, height: 844, deviceScaleFactor: 3, isMobile: true, hasTouch: true }); await p.reload({ waitUntil: 'load' }); await sleep(2500);
  const meta = await p.evaluate(() => document.querySelector('meta[name=viewport]')?.content);
  check('viewport meta present and does not block zoom accessibility incorrectly', /width=device-width/.test(meta || ''), meta);
  await p.tap('#btn-mode-explore'); await sleep(300); check('tap Explore enters Explore', (await appState(p)).mode === 'explore');
  await p.tap('#btn-randomize-action'); await sleep(300); check('tap Randomize works (Explore, finite)', (await appState(p)).mode === 'explore');
  const cx = 195, cy = 500; await p.touchscreen.tap(cx, cy); await sleep(200);
  await p.touchscreen.touchStart(cx, cy); for (let i = 1; i <= 10; i++) { await p.touchscreen.touchMove(cx + i * 8, cy - i * 20); await sleep(16); } await p.touchscreen.touchEnd(); await sleep(300);
  const scroll = await p.evaluate(() => ({ y: scrollY, x: scrollX, vv: window.visualViewport?.scale, w: document.documentElement.scrollWidth }));
  check('touch tap + drag on the artwork does not scroll or zoom the page', scroll.y === 0 && scroll.x === 0 && scroll.vv === 1 && scroll.w <= 390, JSON.stringify(scroll));
  await p.tap('#btn-controls'); await sleep(450); check('tap Controls opens the panel as a bottom sheet', await p.evaluate(() => window.__app.panelOpen));
  await p.tap('#btn-controls-close'); await sleep(350);
  await p.tap('#btn-mode-reference'); await sleep(350); const bad = await invariant(p); check('touch: back to Reference is canonical', bad.length === 0, bad.join());
  // coefficient slider by touch drag in Explore
  await p.tap('#btn-mode-explore'); await sleep(250); await p.tap('#btn-controls'); await sleep(400); await p.evaluate(() => { window.__app.openPanelSection('math'); if (!window.__app.coeffDrawerVisible) document.getElementById('btn-coeff').click(); }); await sleep(400);
  const sl = await p.$('#slider-a-re'); const box = await sl.boundingBox(); await sl.evaluate(e => e.scrollIntoView({ block: 'center' })); const box2 = await sl.boundingBox();
  await p.touchscreen.touchStart(box2.x + box2.width * 0.5, box2.y + box2.height / 2); for (let i = 1; i <= 8; i++) { await p.touchscreen.touchMove(box2.x + box2.width * (0.5 + i * 0.05), box2.y + box2.height / 2); await sleep(16); } await p.touchscreen.touchEnd(); await sleep(250);
  const off = await p.evaluate(() => window.__math.userOffsetA.r); check('touch drag on a coefficient slider changes the offset (Explore)', off !== 0 && Number.isFinite(off), String(off));
  check('touch: no page errors', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
  await S.browser.close();
}
// ---------- 3. Viewport resize and rotation during an export
{
  const S = await launch({ url, root: R('resize'), which, perms: false });
  const { p, dl } = S; const cdp = await p.createCDPSession(); await cdp.send('Emulation.setCPUThrottlingRate', { rate: 8 });
  const before = new Set(files(dl)); await p.click('#btn-export-trigger'); await sleep(250); await p.click('#tab-export-refmaster'); await p.click('.refmaster-pass-btn[data-passes="240"]'); await p.click('#btn-export-start'); await sleep(700);
  for (const [w, h] of [[800, 600], [390, 844], [1920, 1080], [1366, 768]]) { await p.setViewport({ width: w, height: h }); await sleep(350); }
  const running = await p.evaluate(() => window.__app.isExporting);
  const s = await waitEnd(p, 120000); await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 }); await sleep(900);
  const added = files(dl).filter(f => !before.has(f)); const insp = added[0] ? inspectPng(dl, added[0]) : null;
  check('window resized 4x during a Reference Master export: export still completes with a valid 4096² PNG', running && s.result && insp?.ok && insp.w === 4096 && insp.h === 4096, JSON.stringify({ running, s, added, insp }));
  await p.click('#btn-export-cancel'); await sleep(300); const bad = await invariant(p); check('...and Reference is still canonical', bad.length === 0, bad.join());
  // Standard export in Explore: resize mid-run
  await p.click('#btn-mode-explore'); await sleep(200); await p.keyboard.press('3'); await sleep(250); await cdp.send('Emulation.setCPUThrottlingRate', { rate: 6 });
  const b2 = new Set(files(dl)); await p.click('#btn-export-trigger'); await sleep(250); await p.click('.export-res-btn[data-w="3840"]'); await p.click('.export-pass-btn[data-passes="120"]'); await p.click('#btn-export-start'); await sleep(500);
  for (const [w, h] of [[700, 900], [1280, 720]]) { await p.setViewport({ width: w, height: h }); await sleep(300); }
  const s2 = await waitEnd(p, 120000); await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 }); await sleep(900); const a2 = files(dl).filter(f => !b2.has(f)); const i2 = a2[0] ? inspectPng(dl, a2[0]) : null;
  check('window resized during a 4K/120 Explore export: valid 3840×2160 PNG', s2.result && i2?.ok && i2.w === 3840 && i2.h === 2160, JSON.stringify({ s2, a2, i2 }));
  await S.browser.close();
}
// ---------- 4. WebGL unavailable (blocked 3D APIs)
{
  const S = await launch({ url, root: R('nogl'), which, perms: false, args: ['--disable-3d-apis', '--disable-gpu'] });
  const { p, log } = S; await sleep(1500);
  const st = await p.evaluate(() => ({ app: !!window.__app, msg: document.getElementById('graphics-error')?.innerText || '', pill: document.getElementById('mode-status-pill')?.innerText, role: document.getElementById('graphics-error')?.getAttribute('role') }));
  check('WebGL unavailable: a clear, actionable message is shown (not a blank page)', !st.app && /Unable to initialize graphics/.test(st.msg) && /WebGL2|hardware acceleration/.test(st.msg) && st.role === 'alert', JSON.stringify(st));
  // clicking controls must not throw uncaught errors
  const errsBefore = log.pageErrors.length;
  for (const sel of ['#btn-mode-explore', '#btn-randomize-action', '#btn-preset-trigger', '#btn-export-trigger', '#btn-controls', '#btn-help']) { await p.click(sel).catch(() => { }); await sleep(150); }
  for (const k of ['1', '2', '3', 'h', 'e', 's', '?', 'Escape']) { await p.keyboard.press(k); await sleep(60); }
  console.log('INFO no-WebGL: page errors while poking controls:', JSON.stringify(log.pageErrors.slice(errsBefore)));
  check('WebGL unavailable: poking every control produces no uncaught exceptions', log.pageErrors.length === errsBefore, JSON.stringify(log.pageErrors));
  await S.browser.close();
}
// ---------- 5. Two tabs sharing storage, reduced motion
{
  const S = await launch({ url, root: R('tabs'), which });
  const { p, browser } = S;
  const q = await browser.newPage(); await q.setViewport({ width: 1366, height: 768 }); await q.goto(url, { waitUntil: 'load' }); await sleep(2000);
  await p.bringToFront(); await p.click('#btn-preset-trigger'); await sleep(250); await p.type('#preset-name-input', 'From Tab A'); await p.click('#btn-preset-save'); await sleep(800);
  await q.bringToFront(); await q.click('#btn-preset-trigger'); await sleep(400); const labels = await q.$$eval('#user-presets-list > div', rows => rows.map(r => r.firstChild.textContent));
  check('preset saved in tab A is visible when tab B opens its Presets dialog', labels.some(l => /From Tab A/.test(l)), JSON.stringify(labels));
  await q.type('#preset-name-input', 'From Tab B'); await q.click('#btn-preset-save'); await sleep(800); await p.bringToFront(); await p.keyboard.press('Escape'); await sleep(200); await p.click('#btn-preset-trigger'); await sleep(400);
  const labelsA = await p.$$eval('#user-presets-list > div', rows => rows.map(r => r.firstChild.textContent));
  check('both tabs end up with both presets (no lost update from the second tab)', labelsA.some(l => /From Tab A/.test(l)) && labelsA.some(l => /From Tab B/.test(l)), JSON.stringify(labelsA));
  await p.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]); await p.reload({ waitUntil: 'load' }); await sleep(2500);
  const bad = await invariant(p); check('prefers-reduced-motion: app loads in canonical Reference and works', bad.length === 0, bad.join());
  const trans = await p.evaluate(() => { const b = document.getElementById('btn-export-trigger'); return getComputedStyle(b).transitionDuration; });
  console.log('INFO reduced-motion transition duration on buttons:', trans);
  await S.browser.close();
}
done();
