// Reference invariant through every path + Explore + Randomize, on LIVE production, real input events.
import path from 'path';
import fs from 'fs';
import { launch, reporter, sleep, invariant, appState, toastText, files, inspectPng, openPanel, openSection, closeAnyDialog, randomizeStyle } from './rc_lib.mjs';
const url = process.argv[2], root = process.argv[3], which = process.argv[4] || 'chrome';
const { check, done } = reporter(`rc_ref ${which}`);
const S = await launch({ url, root, which });
const { p, dl, log } = S;
console.log(`== ${which} ${S.version} ${url}`);
const refOK = async (name) => { await sleep(350); const bad = await invariant(p); return check(`Reference invariant: ${name}`, bad.length === 0, bad.join(',')); };
const clickMode = async m => { await p.click(`#btn-mode-${m}`); await sleep(300); };

await refOK('first load');

// ---- Explore, then back via button
await clickMode('explore'); let st = await appState(p);
check('Explore button enters Explore', st.mode === 'explore');
await clickMode('reference'); await refOK('Explore -> Reference button');
// ---- keyboard
await p.keyboard.press('2'); await sleep(250); check('key 2 enters Explore', (await appState(p)).mode === 'explore');
await p.keyboard.press('1'); await refOK('key 1');
// ---- Reference canvas input must not perturb
await p.mouse.move(600, 400); await p.mouse.move(700, 450, { steps: 10 }); await p.mouse.click(700, 450); await p.mouse.move(300, 300, { steps: 6 });
await sleep(400); await refOK('mouse move + click over canvas while in Reference');
await p.mouse.wheel({ deltaY: -300 }); await sleep(300); await refOK('wheel over canvas in Reference (framing locked)');
// shift-drag pan in Reference
await p.keyboard.down('Shift'); await p.mouse.move(500, 400); await p.mouse.down(); await p.mouse.move(650, 480, { steps: 8 }); await p.mouse.up(); await p.keyboard.up('Shift'); await sleep(300); await refOK('Shift-drag pan in Reference');
// keyboard R resets view; B bloom; etc must not break Reference math
for (const k of ['r', 'b', 'b', 't', 't', 'o', 'o', 'd', 'd', 'p', 'p']) { await p.keyboard.press(k); await sleep(120); }
await refOK('R/B/T/O/D/P keys in Reference');

// ---- Randomize: all six families, each twice, via menu, then Reference restores
for (const s of ['conradi-like', 'subtle', 'organic', 'dense lace', 'symmetric', 'chaotic']) {
  for (let rep = 0; rep < 2; rep++) {
    await randomizeStyle(p, s); st = await appState(p);
    const fin = await p.evaluate(() => { const m = window.__math; return [m.baseA, m.baseB, m.baseC, m.baseD].every(z => Number.isFinite(z.r) && Number.isFinite(z.i)) && m.n >= 2 && m.n <= 64; });
    check(`Randomize [${s}] #${rep + 1}: Explore, finite coefficients, sane n`, st.mode === 'explore' && fin, JSON.stringify(st) + ' | ' + (await toastText(p)).replace(/\n/g, ' '));
  }
  await clickMode('reference'); await refOK(`after Randomize [${s}] x2 -> Reference button`);
}
// Randomize action button + key 3 repeatedly (20x)
await p.click('#btn-randomize-action'); await sleep(200);
for (let i = 0; i < 20; i++) { await p.keyboard.press('3'); await sleep(60); }
check('20x rapid Randomize (key 3): still Explore, no page errors', (await appState(p)).mode === 'explore' && log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
await p.keyboard.press('1'); await refOK('after repeated Randomize -> key 1');
// Reset (R) in Explore after randomize returns to Reference-like? (R = reset view; record)
await p.keyboard.press('3'); await sleep(200); await p.keyboard.press('r'); await sleep(300);
const rst = await appState(p); check('Explore + R (reset view) keeps Explore (documented behaviour)', rst.mode === 'explore', JSON.stringify(rst));
await p.keyboard.press('1'); await refOK('Explore+R -> Reference');

// ---- Order-n buttons, palette from Reference (enter Explore), then back
await openSection(p, 'math');
await p.click('.sym-btn[data-n="8"]'); await sleep(300); st = await appState(p);
check('Order-n 8 from Reference enters Explore with n=8', st.mode === 'explore' && st.n === 8, JSON.stringify(st));
await clickMode('reference'); await refOK('Order-n 8 -> Reference button');
await openSection(p, 'view'); await p.click('#btn-palette-toggle'); await sleep(150); await p.click('.palette-select-btn[data-pal="solar"]'); await sleep(300); st = await appState(p);
check('Palette solar from Reference enters Explore', st.mode === 'explore' && st.pal === 'solar', JSON.stringify(st));
await clickMode('reference'); await refOK('palette solar -> Reference button');
// ---- Explore stash resume
await clickMode('explore'); await openSection(p, 'math'); await p.click('.sym-btn[data-n="5"]'); await sleep(250);
await clickMode('reference'); await refOK('Explore n=5 -> Reference'); await clickMode('explore'); st = await appState(p);
check('Explore session resumes after Reference (n=5)', st.n === 5, JSON.stringify(st));
await clickMode('reference'); await refOK('after resume -> Reference');
// ---- Start fresh
await clickMode('explore'); await openSection(p, 'math'); await p.click('.sym-btn[data-n="3"]'); await sleep(200); await p.click('#btn-start-fresh'); await sleep(350); st = await appState(p);
const freshBad = await p.evaluate(async () => { const { CONRADI_REFERENCE: C } = await import('/math.js'); const m = window.__math; return m.n === 16 && m.baseA.r === C.a.r && m.baseD.i === C.d.i && !m.evolving ? '' : 'baseline mismatch'; });
check('Start fresh: Explore restarts from canonical baseline', st.mode === 'explore' && !freshBad, JSON.stringify(st) + freshBad);
await clickMode('reference'); await refOK('Start fresh -> Reference');

// ---- Presets: curated, user, malformed
await p.click('#btn-preset-trigger'); await sleep(350);
const curated = await p.$$eval('#curated-presets-list button', bs => bs.map(b => b.textContent.trim().slice(0, 40)));
check('curated presets list is populated', curated.length >= 3, JSON.stringify(curated));
for (let i = 0; i < curated.length; i++) {
  if (!(await p.evaluate(() => window.__app.isModalOpen()))) { await p.click('#btn-preset-trigger'); await sleep(300); }
  const btns = await p.$$('#curated-presets-list button'); await btns[i].click(); await sleep(450);
  const t = (await toastText(p)).replace(/\n/g, ' ');
  const s2 = await appState(p); const fin = await p.evaluate(() => { const m = window.__math; return Number.isFinite(m.baseA.r) && Number.isFinite(m.baseB.i); });
  check(`curated preset #${i + 1} "${curated[i]}" loads (${s2.mode}, n=${s2.n}) and is finite`, /Loaded preset/.test(t) && fin, t);
  await closeAnyDialog(p); await clickMode('reference'); await refOK(`curated preset "${curated[i]}" -> Reference`);
}
// malformed preset import: Reference stays untouched
const tmp = path.join(S.root, 'bad'); fs.mkdirSync(tmp, { recursive: true });
const mk = (name, content) => { const f = path.join(tmp, name); fs.writeFileSync(f, content); return f; };
const importFile = async f => { if (!(await p.evaluate(() => window.__app.isModalOpen()))) { await p.click('#btn-preset-trigger'); await sleep(300); } const [ch] = await Promise.all([p.waitForFileChooser(), p.click('#btn-preset-import')]); await ch.accept([f]); await sleep(700); return (await toastText(p)).replace(/\n/g, ' '); };
const bads = {
  'notjson.json': 'this is not json {{{',
  'empty.json': '',
  'array.json': '[1,2,3]',
  'nofields.json': '{"name":"x"}',
  'nan.json': JSON.stringify({ name: 'nan', version: '1.0', mode: 'explore', symmetry: 5, coefficients: { a: { r: 'NaN', i: 0 }, b: { r: 0, i: 0 }, c: { r: 1, i: 0 }, d: { r: 1, i: 0 } } }),
  'hugen.json': JSON.stringify({ name: 'bign', version: '1.0', mode: 'explore', symmetry: 99999, coefficients: { a: { r: 1, i: 0 }, b: { r: 0, i: 0 }, c: { r: 0, i: 0 }, d: { r: 1, i: 0 } } }),
  'proto.json': '{"__proto__":{"polluted":1},"name":"p","symmetry":5}',
};
for (const [n, c] of Object.entries(bads)) {
  await closeAnyDialog(p); await clickMode('reference'); await closeAnyDialog(p);
  const t = await importFile(mk(n, c)); const s3 = await appState(p); const pol = await p.evaluate(() => ({}).polluted === undefined && Object.prototype.polluted === undefined);
  const accepted = /^Loaded preset/.test(t);
  if (n === 'nofields.json' || n === 'proto.json') check(`import "${n}": schema-valid by design (legacy-permissive) -> loads; no prototype pollution`, accepted && pol, t + ' | mode now ' + s3.mode);
  else check(`malformed import "${n}": rejected with a message, session untouched (still Reference), no pollution`, /Unable to load preset|too large|Invalid/i.test(t) && s3.mode === 'reference' && pol, t);
}
await closeAnyDialog(p); await clickMode('reference'); await closeAnyDialog(p);
const big = '{"name":"' + 'x'.repeat(1.2 * 1024 * 1024) + '"}';
const tb = await importFile(mk('big.json', big));
check('oversized (>1 MB) import rejected before parsing', /too large/i.test(tb), tb);
await closeAnyDialog(p); await refOK('after malformed/oversized imports');

// ---- reload
await p.reload({ waitUntil: 'load' }); await sleep(2500); await refOK('reload');
// ---- context loss / recovery
await clickMode('explore'); await openSection(p, 'math'); await p.click('.sym-btn[data-n="12"]'); await sleep(200); await clickMode('reference'); await sleep(200);
const lost = await p.evaluate(async () => { const gl = window.__renderer.gl; const ext = gl.getExtension('WEBGL_lose_context'); if (!ext) return 'no-ext'; ext.loseContext(); await new Promise(r => setTimeout(r, 800)); const wasLost = window.__app.contextLost; ext.restoreContext(); await new Promise(r => setTimeout(r, 2500)); return { wasLost, nowLost: window.__app.contextLost }; });
check('forced WebGL context loss then restore: app recovers (contextLost false)', lost && lost.wasLost === true && lost.nowLost === false, JSON.stringify(lost));
await refOK('after context loss/recovery (Reference)');
const banner = await p.evaluate(() => ({ disp: document.getElementById('status-banner').style.display, txt: document.getElementById('status-banner-text').textContent }));
check('status banner cleared after recovery', banner.disp === 'none' || banner.disp === '', JSON.stringify(banner));
// Explore -> context loss -> recovery -> Reference
await clickMode('explore'); await randomizeStyle(p, 'organic');
const lost2 = await p.evaluate(async () => { const gl = window.__renderer.gl; const ext = gl.getExtension('WEBGL_lose_context'); ext.loseContext(); await new Promise(r => setTimeout(r, 600)); ext.restoreContext(); await new Promise(r => setTimeout(r, 2500)); return { nowLost: window.__app.contextLost, mode: window.__app.mode }; });
check('context loss while in Explore: recovers', lost2.nowLost === false, JSON.stringify(lost2));
await clickMode('reference'); await refOK('Explore -> context loss -> Reference');

// ---- export paths and Reference invariant
await p.click('#btn-export-trigger'); await sleep(300); await p.click('.export-res-btn[data-w="1920"]'); await p.click('.export-pass-btn[data-passes="30"]'); await p.click('#btn-export-start');
for (let i = 0; i < 100; i++) { await sleep(250); if (await p.evaluate(() => !document.getElementById('export-result').hidden)) break; }
await p.click('#btn-export-cancel'); await sleep(300); await refOK('after a completed export (Reference)');
await p.click('#btn-export-trigger'); await sleep(300); await p.click('#tab-export-refmaster').catch(() => {}); await p.click('.refmaster-pass-btn[data-passes="240"]'); await p.click('#btn-export-start'); await sleep(900);
await p.click('#btn-export-cancel'); await sleep(2500); // cancel mid-run
const afterCancel = await p.evaluate(() => ({ exporting: window.__app.isExporting, notice: !document.getElementById('export-notice').hidden || !document.getElementById('export-result').hidden }));
check('Reference Master 240 canceled mid-run: export stopped', afterCancel.exporting === false, JSON.stringify(afterCancel));
await closeAnyDialog(p); await refOK('after canceled Reference Master export');
// Explore export -> Explore state preserved
await clickMode('explore'); await openSection(p, 'math'); await p.click('.sym-btn[data-n="24"]'); await sleep(250);
const before = await appState(p);
await p.click('#btn-export-trigger'); await sleep(300); await p.click('.export-res-btn[data-w="1920"]'); await p.click('.export-pass-btn[data-passes="30"]'); await p.click('#btn-export-start');
for (let i = 0; i < 100; i++) { await sleep(250); if (await p.evaluate(() => !document.getElementById('export-result').hidden)) break; }
await p.click('#btn-export-cancel'); await sleep(400); const after = await appState(p);
check('Explore export leaves the Explore session intact (mode, n, palette)', before.mode === after.mode && before.n === after.n && before.pal === after.pal, JSON.stringify([before, after]));
await clickMode('reference'); await refOK('Explore export -> Reference');
// Reference Master export from Explore must not alter Explore, and not leak into Reference
await clickMode('explore'); const beforeM = await appState(p);
await p.click('#btn-export-trigger'); await sleep(300); await p.click('#tab-export-refmaster'); await p.click('.refmaster-pass-btn[data-passes="120"]'); await p.click('#btn-export-start');
for (let i = 0; i < 200; i++) { await sleep(250); if (await p.evaluate(() => !document.getElementById('export-result').hidden)) break; }
await p.click('#btn-export-cancel'); await sleep(500); const afterM = await appState(p);
check('Reference Master export from Explore leaves Explore session intact', beforeM.mode === afterM.mode && beforeM.n === afterM.n && beforeM.pal === afterM.pal && JSON.stringify(beforeM.a) === JSON.stringify(afterM.a), JSON.stringify([beforeM, afterM]));
await clickMode('reference'); await refOK('Explore -> Reference Master export -> Reference');
// ---- Brute force + Reference
await openSection(p, 'quality'); await p.click('.quality-btn[data-tier="bruteforce"]'); await sleep(600); await refOK('Brute Force tier selected in Reference (math untouched)'); await p.click('.quality-btn[data-tier="auto"]'); await sleep(300);

check('no uncaught page errors in whole run', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
check('no failed requests / HTTP >= 400', log.failed.length === 0 && log.http.length === 0, JSON.stringify([log.failed, log.http]));
console.log('console errors/warnings:', JSON.stringify(log.console.slice(0, 10)));
done(); await S.browser.close();
