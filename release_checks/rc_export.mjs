// Export lifecycle on LIVE production, real browser: cancel at several stages, retry, Esc/shortcuts during export,
// hidden tab / foreground change, context loss mid-export + retry, double-start, reload mid-export, Current View size.
import fs from 'fs';
import { launch, reporter, sleep, invariant, appState, files, inspectPng, closeAnyDialog, openSection } from './rc_lib.mjs';
const url = process.argv[2], root = process.argv[3], which = process.argv[4] || 'chrome';
const { check, done } = reporter(`rc_export ${which}`);
const S = await launch({ url, root, which });
const { p, dl, log } = S;
console.log(`== ${which} ${S.version} ${url}`);
const ui = () => p.evaluate(() => ({ running: window.__app.isExporting, modal: document.getElementById('export-modal').classList.contains('visible'), result: !document.getElementById('export-result').hidden, notice: document.getElementById('export-notice').hidden ? '' : document.getElementById('export-notice').innerText.replace(/\n/g, ' '), pct: document.getElementById('export-status-pct').innerText, label: document.getElementById('export-status-label').innerText, ui: window.__app._exportUiState, start: document.getElementById('btn-export-start').innerText, startHidden: document.getElementById('btn-export-start').hidden }));
const openExport = async (kind = 'standard', res = '3840', passes = '60') => {
  if (!(await p.evaluate(() => window.__app.exportModal.classList.contains('visible')))) { await p.click('#btn-export-trigger'); await sleep(300); }
  if (kind === 'master') { await p.click('#tab-export-refmaster'); await p.click(`.refmaster-pass-btn[data-passes="${passes}"]`); }
  else { await p.click('#tab-export-standard'); await p.click(`.export-res-btn[data-w="${res}"]`); if (passes) await p.click(`.export-pass-btn[data-passes="${passes}"]`); }
};
const waitEnd = async (ms = 60000) => { const t = Date.now(); while (Date.now() - t < ms) { const s = await ui(); if (s.result || s.notice) return s; await sleep(200); } return await ui(); };
const waitNewFile = async (before, ms = 15000) => { const t = Date.now(); while (Date.now() - t < ms) { const n = files(dl).filter(f => !before.has(f)); if (n.length) { await sleep(500); return files(dl).filter(f => !before.has(f)); } await sleep(250); } return []; };
const snapshot = () => files(dl);
const closeExport = async () => { const s = await ui(); if (s.modal && !s.running) { await p.click('#btn-export-cancel'); await sleep(300); } };

// 1. cancel immediately after start
let before = new Set(snapshot());
await openExport('standard', '3840', '120'); await p.click('#btn-export-start'); await sleep(40); await p.click('#btn-export-cancel');
let s = await waitEnd(30000);
await sleep(1500); let added = snapshot().filter(f => !before.has(f));
check('cancel ~40 ms after start: ends in a truthful state (canceled, or already completed) with a consistent file result', (/canceled/i.test(s.notice) && added.length === 0) || (s.result && added.length === 1), JSON.stringify({ s, added }));
check('after the immediate cancel: export flag cleared and dialog usable', (await ui()).running === false);
await closeExport();
// 2. cancel mid-run (Reference Master 240 ~4-5 s)
before = new Set(snapshot());
await openExport('master', null, '240'); await p.click('#btn-export-start'); await sleep(1400);
const mid = await ui(); await p.click('#btn-export-cancel'); s = await waitEnd(30000); await sleep(2500); added = snapshot().filter(f => !before.has(f));
check('Reference Master 240: progress was visible mid-run (running, % shown)', mid.running && /%/.test(mid.pct) && mid.label.length > 0, JSON.stringify(mid));
check('cancel mid-run: "Export canceled" notice, nothing downloaded (no file, no partial)', /canceled/i.test(s.notice) && added.length === 0, JSON.stringify({ s: s.notice, added }));
check('after cancel: stale progress cleared', (await ui()).pct === '' && (await ui()).label === '');
// 3. retry right after cancel -> completes, valid file
before = new Set(snapshot()); await p.click('#btn-export-start'); s = await waitEnd(90000); added = await waitNewFile(before);
const ir = added[0] ? inspectPng(dl, added[0]) : null;
check('retry after cancel (Reference Master 240): completes, one valid 4096² PNG', s.result && added.length === 1 && ir?.ok && ir.w === 4096 && ir.h === 4096, JSON.stringify({ added, ir }));
await closeExport();
// 4. Esc, shortcuts, backdrop click, 'e' during an active export (CPU throttled so the export is still active while we poke it)
await p.keyboard.press('2'); await sleep(200); await p.keyboard.press('1'); await sleep(200);
const sBefore = await appState(p); before = new Set(snapshot());
const cdpT = await p.createCDPSession(); await cdpT.send('Emulation.setCPUThrottlingRate', { rate: 10 });
await openExport('master', null, '240'); await p.click('#btn-export-start'); await sleep(500);
const pokeLog = [];
await p.keyboard.press('Escape'); await sleep(100); pokeLog.push(['Esc', (await ui()).running]);
for (const k of ['1', '2', '3', 'h', 'b', 'x', 's', '?', 'e', ' ', 'r', 'o', 'p', 'd']) { await p.keyboard.press(k); await sleep(40); }
pokeLog.push(['14 shortcut keys', (await ui()).running]);
await p.mouse.click(8, 8); await sleep(100); pokeLog.push(['backdrop click', (await ui()).running]);
const during = await ui(); const sDuring = await appState(p);
check('Esc + 14 shortcut keys + backdrop click during an ACTIVE export: export keeps running, dialog stays open', during.running && during.modal && pokeLog.every(x => x[1]), JSON.stringify({ pokeLog, during }));
check('...and nothing mutated the session behind it (mode, n, drift, palette, UI not hidden)', sDuring.mode === sBefore.mode && sDuring.n === sBefore.n && sDuring.drift === sBefore.drift && sDuring.pal === sBefore.pal && (await p.evaluate(() => !document.body.classList.contains('ui-hidden'))), JSON.stringify([sBefore, sDuring]));
s = await waitEnd(120000); await cdpT.send('Emulation.setCPUThrottlingRate', { rate: 1 }); added = await waitNewFile(before);
check('that export still completed after being poked (valid 4096² PNG)', s.result && added.length === 1 && inspectPng(dl, added[0]).ok, JSON.stringify({ added }));
// Esc after completion dismisses
await p.keyboard.press('Escape'); await sleep(400);
check('Esc after a completed export dismisses the dialog', !(await ui()).modal);
// 5. double-click Start => one export only
before = new Set(snapshot()); await openExport('standard', '1920', '30'); await p.click('#btn-export-start', { clickCount: 2, delay: 10 }); s = await waitEnd(60000); added = await waitNewFile(before); await sleep(1500); added = snapshot().filter(f => !before.has(f));
check('double-clicking Start produces exactly one file', added.length === 1, JSON.stringify(added));
await closeExport();
// 6. Current View size
before = new Set(snapshot()); await openExport('standard', 'viewport', '30'); await p.click('#btn-export-start'); s = await waitEnd(60000); added = await waitNewFile(before);
const vp = await p.evaluate(() => [Math.round(innerWidth * devicePixelRatio), Math.round(innerHeight * devicePixelRatio), document.getElementById('export-summary').innerText]);
const iv = added[0] ? inspectPng(dl, added[0]) : null;
check('Current View export: valid PNG; announced size matches the file', s.result && iv?.ok && (await p.evaluate(() => document.getElementById('export-result-size').innerText)) === `${iv.w} × ${iv.h} px`, JSON.stringify({ added, iv, vp }));
await closeExport();
// 7. hidden tab during export
before = new Set(snapshot()); await openExport('master', null, '240'); await p.click('#btn-export-start'); await sleep(700);
const other = await S.browser.newPage(); await other.goto('about:blank'); await other.bringToFront(); await sleep(3500);
const hiddenState = await p.evaluate(() => document.visibilityState);
await p.bringToFront(); await sleep(300); s = await waitEnd(90000); added = await waitNewFile(before);
const ih = added[0] ? inspectPng(dl, added[0]) : null;
check('export while the tab is in the background (3.5 s) then foregrounded: ends truthfully (valid file iff "complete")', hiddenState === 'hidden' && ((s.result && added.length === 1 && ih?.ok) || (/failed|canceled/i.test(s.notice) && added.length === 0)), JSON.stringify({ hiddenState, s: s.notice || (s.result ? 'complete' : '?'), added, ih }));
console.log('INFO hidden-tab outcome:', s.result ? 'completed' : s.notice);
await other.close(); await closeExport();
// 8. context loss mid export, then recovery + retry
before = new Set(snapshot()); await openExport('master', null, '240'); await p.click('#btn-export-start'); await sleep(1200);
await p.evaluate(() => { window.__lc = window.__renderer.gl.getExtension('WEBGL_lose_context'); window.__lc.loseContext(); });
s = await waitEnd(30000); await sleep(1500); added = snapshot().filter(f => !before.has(f));
console.log('INFO context-lost mid-export state:', JSON.stringify({ notice: s.notice, result: s.result, added }));
check('context lost mid-export: the export does not claim success and delivers no file', !s.result && added.length === 0 && /failed|canceled|lost/i.test(s.notice), JSON.stringify({ s: s.notice, added }));
await p.evaluate(() => window.__lc.restoreContext()); await sleep(3000);
const rec = await p.evaluate(() => ({ lost: window.__app.contextLost, exporting: window.__app.isExporting }));
check('after restore: renderer recovered and export flag cleared', rec.lost === false && rec.exporting === false, JSON.stringify(rec));
before = new Set(snapshot()); const s8 = await ui();
if (!s8.modal) await openExport('master', null, '240');
await p.click('#btn-export-start'); s = await waitEnd(90000); added = await waitNewFile(before);
check('retry after context recovery: completes with a valid PNG', s.result && added.length === 1 && inspectPng(dl, added[0]).ok, JSON.stringify({ s: s.notice, added }));
await closeExport();
const bad = await invariant(p); check('(page is in Reference — invariant intact after all exports/aborts)', bad.length === 0, bad.join());
// 9. reload mid-export
before = new Set(snapshot()); await openExport('master', null, '240'); await p.click('#btn-export-start'); await sleep(900);
await p.reload({ waitUntil: 'load' }); await sleep(2500); await sleep(1500); added = snapshot().filter(f => !before.has(f));
const bad2 = await invariant(p); const st2 = await p.evaluate(() => ({ exporting: window.__app.isExporting, modal: window.__app.exportModal.classList.contains('visible') }));
check('reload during export: clean start, no partial file, Reference invariant', bad2.length === 0 && !st2.exporting && !st2.modal && added.length === 0, JSON.stringify({ bad2, st2, added }));
// 10. leftover blob/crdownload hygiene
check('no leftover .crdownload/.tmp files', !fs.readdirSync(dl).some(f => /\.(crdownload|tmp)$/.test(f)), JSON.stringify(fs.readdirSync(dl)));
check('no uncaught page errors', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
check('no failed requests / HTTP >= 400', log.failed.length === 0 && log.http.length === 0, JSON.stringify([log.failed, log.http]));
console.log('console:', JSON.stringify(log.console.slice(0, 10)), '\nfiles:', JSON.stringify(snapshot()));
done(); await S.browser.close();
