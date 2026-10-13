// Preset edge cases on LIVE production in a real browser: clipboard denial, duplicates, long/Unicode/markup/blank names,
// storage failure, persistence across reload, 20-preset cap, delete, same-file re-import, filename sanitizing.
import path from 'path';
import fs from 'fs';
import { launch, reporter, sleep, invariant, appState, toastText, files, openPanel, closeAnyDialog } from './rc_lib.mjs';
const url = process.argv[2], root = process.argv[3], which = process.argv[4] || 'chrome';
const { check, known, done } = reporter(`rc_presets ${which}`);
const S = await launch({ url, root, which });
const { p, dl, log } = S;
console.log(`== ${which} ${S.version} ${url}`);
const openPresets = async () => { if (!(await p.evaluate(() => window.__app.isModalOpen()))) { await p.click('#btn-preset-trigger'); await sleep(300); } };
const setName = async v => { await openPresets(); await p.$eval('#preset-name-input', el => { el.value = ''; }); if (v) await p.type('#preset-name-input', v, { delay: 0 }); };
const stored = () => p.evaluate(() => JSON.parse(localStorage.getItem('mobius_custom_presets') || '[]'));
const listLabels = () => p.$$eval('#user-presets-list > div', rows => rows.map(r => r.firstChild.textContent));
const save = async v => { await setName(v); const before = new Set(files(dl)); await p.click('#btn-preset-save'); await sleep(900); return files(dl).filter(f => !before.has(f)); };

// --- 1 duplicate names
let f1 = await save('Dup'); let f2 = await save('Dup');
let st = await stored();
check('duplicate names: two entries stored, both listed (documented: no duplicate-name handling)', st.length === 2 && st[0].name === 'Dup' && st[1].name === 'Dup', JSON.stringify(st.map(x => x.name)));
check('duplicate names: second download is renamed by the browser ("dup.mobius (1).json"), nothing overwritten', f1[0] === 'dup.mobius.json' && f2[0] === 'dup.mobius (1).json', JSON.stringify([f1, f2]));
// --- 2 long name
const long = 'L'.repeat(600);
const fl = await save(long); st = await stored();
const lt = await toastText(p);
check('long name (600 chars): saved, stored, file downloaded with a browser-safe name', st[0]?.name.length === 600 && fl.length === 1, JSON.stringify({ stored: st[0]?.name.length, file: fl[0]?.slice(0, 40), toast: lt.slice(0, 60) }));
// does it import back? (validator caps name at 512)
const fp = path.join(dl, fl[0]);
const importFile = async f => { await openPresets(); const [ch] = await Promise.all([p.waitForFileChooser(), p.click('#btn-preset-import')]); await ch.accept([f]); await sleep(800); return (await toastText(p)).replace(/\n/g, ' '); };
const ti = await importFile(fp);
known('MINOR F-1: a 600-character preset name is saved, but its own file is then rejected on import (validator caps names at 512)', /Loaded preset/.test(ti), ti.slice(0, 140));
// --- 3 Unicode, markup, quotes, path chars
const nasty = [
  ['unicode', 'Möbius ∑ 日本語 🌀'],
  ['markup', '<img src=x onerror="window.__xss=1"><b>bold</b>'],
  ['quotes', 'He said "hi" & \'bye\''],
  ['pathchars', 'a/b\\c:d*e?f"g<h>i|j'],
  ['dots', '..'],
  ['spaces+newline', 'multi   space\tTab'],
];
for (const [k, nm] of nasty) {
  const fl2 = await save(nm); st = await stored(); const labels = await listLabels();
  const xss = await p.evaluate(() => window.__xss === undefined && document.querySelectorAll('#user-presets-list img, #user-presets-list b').length === 0);
  check(`name "${k}": saved & listed as literal text, no markup injection`, st[0]?.name === nm.trim() && xss && labels[0].startsWith(nm.trim()), JSON.stringify({ file: fl2, label: labels[0]?.slice(0, 50) }));
  check(`name "${k}": a .json file lands on disk and parses`, fl2.length === 1 && /\.json$/.test(fl2[0]) && (() => { try { return JSON.parse(fs.readFileSync(path.join(dl, fl2[0]), 'utf8')).name === nm.trim(); } catch (e) { return false; } })(), JSON.stringify(fl2));
}
// --- 4 load a saved preset from the list restores state; delete
await closeAnyDialog(p); await p.click('#btn-mode-reference'); await sleep(300);
await openPresets();
const loads = await p.$$('#user-presets-list .load-user-preset'); const n0 = (await stored()).length;
await loads[0].click(); await sleep(500);
const sAfter = await appState(p);
check('Load from saved list works and closes dialog', /Loaded preset/.test(await toastText(p)) && !(await p.evaluate(() => window.__app.isModalOpen())), JSON.stringify(sAfter));
await openPresets(); const dels = await p.$$('#user-presets-list .del-user-preset'); await dels[0].click(); await sleep(300);
check('Delete removes exactly one saved preset immediately (no confirmation: documented minor)', (await stored()).length === n0 - 1);
// --- 5 20-preset cap
for (let i = 0; i < 24; i++) { await setName('Cap ' + i); await p.click('#btn-preset-save'); await sleep(250); }
st = await stored(); const capToast = await toastText(p);
check('cap: never more than 20 stored; newest kept; user told when the oldest is dropped', st.length === 20 && st[0].name === 'Cap 23' && /20-preset limit/.test(capToast), `${st.length} ${st[0]?.name} | ${capToast}`);
// --- 6 reload persistence
await closeAnyDialog(p); await p.reload({ waitUntil: 'load' }); await sleep(2500);
await openPresets(); const labels2 = await listLabels();
check('saved presets survive a reload', labels2.length === 20 && labels2[0].startsWith('Cap 23'), `${labels2.length} ${labels2[0]}`);
// --- 7 same file twice through the chooser
const sameF = path.join(dl, 'dup.mobius.json'); await closeAnyDialog(p);
const t1 = await importFile(sameF); const t2 = await importFile(sameF);
check('import the same file twice in a row: both loads happen (input is reset)', /Loaded preset: Dup/.test(t1) && /Loaded preset: Dup/.test(t2), t1 + ' || ' + t2);
// --- 8 clipboard denial (real browser permission, not a stub)
await closeAnyDialog(p);
const cdp = await p.createCDPSession();
let denied = 'n/a';
try {
  await cdp.send('Browser.setPermission', { permission: { name: 'clipboard-sanitized-write' }, setting: 'denied', origin: new URL(url).origin });
  await cdp.send('Browser.setPermission', { permission: { name: 'clipboard-write' }, setting: 'denied', origin: new URL(url).origin });
  denied = 'set';
} catch (e) { denied = 'ERR ' + e.message.slice(0, 80); }
await setName('Clip Denied'); await p.click('#btn-preset-copy'); await sleep(900);
const denyToast = (await toastText(p)).replace(/\n/g, ' ');
const clipNow = await p.evaluate(async () => { try { return await navigator.clipboard.readText(); } catch (e) { return 'ERR'; } });
console.log('INFO clipboard permission override:', denied, '| toast:', denyToast, '| clipboard now:', clipNow.slice(0, 40));
check('clipboard write denied: the app does NOT claim "copied" unless the clipboard really received the JSON', denyToast !== 'Preset JSON copied to clipboard!' || /Clip Denied/.test(clipNow), denyToast + ' | ' + clipNow.slice(0, 40));
// restore permissions
try { await cdp.send('Browser.resetPermissions'); await p.browserContext().overridePermissions(new URL(url).origin, ['clipboard-read', 'clipboard-write', 'clipboard-sanitized-write']); } catch (e) {}
// --- 9 JS-level clipboard rejection and no-clipboard-API (what the code handles)
await closeAnyDialog(p);
const r1 = await p.evaluate(async () => { const orig = navigator.clipboard.writeText; navigator.clipboard.writeText = () => Promise.reject(new DOMException('no', 'NotAllowedError')); window.__app.copyPresetJSON(); await new Promise(r => setTimeout(r, 300)); const t = document.getElementById('toast-banner').innerText; navigator.clipboard.writeText = orig; return t; });
check('clipboard API rejects (NotAllowedError): honest failure message', /Could not copy/i.test(r1), r1);
const r2 = await p.evaluate(async () => { const d = Object.getOwnPropertyDescriptor(Navigator.prototype, 'clipboard'); Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true }); window.__app.copyPresetJSON(); const t = document.getElementById('toast-banner').innerText; delete navigator.clipboard; return t; });
check('clipboard API missing: honest failure message', /unavailable/i.test(r2), r2);
// --- 10 storage failure on save (quota) — real localStorage replaced with a throwing setItem
await p.evaluate(() => { window.__origSet = Storage.prototype.setItem; Storage.prototype.setItem = function () { throw new DOMException('quota', 'QuotaExceededError'); }; });
const fq = await save('Quota Fail'); const qt = (await toastText(p)).replace(/\n/g, ' ');
check('storage quota failure: file still downloads and the message says it was NOT kept in the browser', fq.length === 1 && /Could not keep/.test(qt) && /still downloaded/.test(qt), qt);
await p.evaluate(() => { Storage.prototype.setItem = window.__origSet; });
// --- 11 storage read failure at boot (localStorage throws on getItem) in a fresh page
const p2 = await S.browser.newPage(); await p2.setViewport({ width: 1366, height: 768 });
const e2 = []; p2.on('pageerror', e => e2.push(e.message));
await p2.evaluateOnNewDocument(() => { Storage.prototype.getItem = function () { throw new DOMException('denied', 'SecurityError'); }; Storage.prototype.setItem = function () { throw new DOMException('denied', 'SecurityError'); }; });
await p2.goto(url, { waitUntil: 'load' }); await sleep(2500);
await p2.click('#btn-preset-trigger'); await sleep(400);
const emptyMsg = await p2.$eval('#user-presets-list', el => el.innerText);
const refBad = await invariant(p2);
check('localStorage unreadable at boot: app loads in Reference, preset dialog opens with an empty list, no exceptions', e2.length === 0 && refBad.length === 0 && /Nothing saved/.test(emptyMsg), JSON.stringify({ e2, refBad, emptyMsg }));
await p2.close();
// --- 12 corrupt stored JSON in localStorage
await p.evaluate(() => localStorage.setItem('mobius_custom_presets', '{corrupt'));
await p.reload({ waitUntil: 'load' }); await sleep(2500); await openPresets();
const corruptMsg = await p.$eval('#user-presets-list', el => el.innerText);
check('corrupt stored preset list: treated as empty, dialog still works', /Nothing saved/.test(corruptMsg) && log.pageErrors.length === 0, corruptMsg + JSON.stringify(log.pageErrors));
// saving after corruption heals the list
const fc = await save('After Corrupt'); st = await stored();
check('saving after corruption works and replaces the bad data', fc.length === 1 && st.length === 1 && st[0].name === 'After Corrupt', JSON.stringify(st.map(x => x.name)));
// stored list with garbage items (non-object)
await p.evaluate(() => localStorage.setItem('mobius_custom_presets', JSON.stringify([null, 5, 'x', { name: 7 }, { name: 'ok', symmetry: 8 }])));
await p.reload({ waitUntil: 'load' }); await sleep(2500);
let garbageOK = true; let gerr = '';
try { await openPresets(); await sleep(300); } catch (e) { garbageOK = false; gerr = e.message; }
known('MINOR F-2: a stored preset list containing a non-object item (only possible via tampered storage) stops the Presets dialog from opening', garbageOK && log.pageErrors.length === 0, gerr + JSON.stringify(log.pageErrors));
check('no failed requests / HTTP >= 400', log.failed.length === 0 && log.http.length === 0, JSON.stringify([log.failed, log.http]));
console.log('page errors:', JSON.stringify(log.pageErrors), '\nconsole:', JSON.stringify(log.console.slice(0, 10)));
done(); await S.browser.close();
