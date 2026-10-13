// Release-candidate Stage 1: real browser (headful), normal-style profile, LIVE production.
// Usage: node rc_stage1.mjs <url> <rootDir> <chrome|edge>
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';
const url = process.argv[2]; const root = path.resolve(process.argv[3]); const which = process.argv[4] || 'chrome';
const exe = which === 'edge' ? (process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe') : (process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe');
fs.rmSync(path.resolve(root), { recursive: true, force: true });
const profile = path.join(root, 'profile'); const dl = path.join(root, 'Downloads');
fs.mkdirSync(path.join(profile, 'Default'), { recursive: true }); fs.mkdirSync(dl, { recursive: true });
fs.writeFileSync(path.join(profile, 'Default', 'Preferences'), JSON.stringify({ download: { default_directory: dl.replace(/\//g, '\\'), prompt_for_download: false, directory_upgrade: true } }));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const browser = await puppeteer.launch({ executablePath: exe, headless: false, userDataDir: profile, args: ['--use-gl=angle', '--use-angle=d3d11', '--window-size=1400,900', '--no-first-run', '--no-default-browser-check'] });
const version = await browser.version();
const origin = new URL(url).origin;
await browser.defaultBrowserContext().overridePermissions(origin, ['clipboard-read', 'clipboard-write', 'clipboard-sanitized-write']);
const p = await browser.newPage(); await p.bringToFront(); await p.setViewport({ width: 1366, height: 768 });
const errs = [], failedReq = [], consoleErr = [];
p.on('pageerror', e => errs.push(e.message));
p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') consoleErr.push(m.type() + ': ' + m.text()); });
p.on('requestfailed', r => failedReq.push(r.url() + ' ' + (r.failure()?.errorText || '')));
p.on('response', r => { if (r.status() >= 400) failedReq.push(r.status() + ' ' + r.url()); });
await p.goto(url, { waitUntil: 'load' }); await sleep(3000);
const R = []; const check = (n, ok, d = '') => { R.push([ok ? 'PASS' : 'FAIL', n, d]); console.log(ok ? 'PASS' : 'FAIL', n, d ? '— ' + d : ''); };
const files = () => fs.readdirSync(dl).filter(f => !f.endsWith('.crdownload') && !f.endsWith('.tmp')).sort();
// Full PNG inspection from disk: signature, IHDR dims, chunk walk to IEND, IDAT inflates to the expected raw size.
const inspectPng = f => {
  let b; try { b = fs.readFileSync(path.join(dl, f)); } catch (e) { return { ok: false, why: 'unreadable' }; }
  if (!b.length) return { ok: false, why: 'zero bytes' };
  if (b.slice(0, 8).toString('hex') !== '89504e470d0a1a0a') return { ok: false, why: 'bad signature' };
  let o = 8, w = 0, h = 0, ct = 0, bd = 0, idat = [], iend = false;
  while (o + 8 <= b.length) { const len = b.readUInt32BE(o), type = b.slice(o + 4, o + 8).toString(); if (type === 'IHDR') { w = b.readUInt32BE(o + 8); h = b.readUInt32BE(o + 12); bd = b[o + 16]; ct = b[o + 17]; } if (type === 'IDAT') idat.push(b.slice(o + 8, o + 8 + len)); if (type === 'IEND') { iend = true; break; } o += 12 + len; }
  let inflated = -1; try { inflated = zlib.inflateSync(Buffer.concat(idat)).length; } catch (e) {}
  const ch = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 }[ct] || 0; const expect = h * (1 + Math.ceil(w * ch * bd / 8));
  return { ok: iend && inflated === expect, w, h, size: b.length, iend, inflatedOk: inflated === expect, why: iend ? (inflated === expect ? '' : 'IDAT size mismatch') : 'no IEND' };
};
const waitFile = async (name, ms = 20000) => { const t = Date.now(); while (Date.now() - t < ms) { if (files().includes(name)) { await sleep(400); return true; } await sleep(250); } return false; };
const isDone = () => p.evaluate(() => !document.getElementById('export-result').hidden || !document.getElementById('export-notice').hidden);
const doExport = async (resSel, passN, wantFile, maxIter = 600) => {
  const before = new Set(files());
  await p.click('#btn-export-trigger'); await sleep(250);
  if (resSel) await p.click(resSel); await p.click(`.export-pass-btn[data-passes="${passN}"]`);
  const t0 = Date.now(); await p.click('#btn-export-start');
  for (let i = 0; i < maxIter; i++) { await sleep(250); if (await isDone()) break; }
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  const shown = await p.evaluate(() => document.getElementById('export-result-file').textContent);
  const notice = await p.evaluate(() => document.getElementById('export-notice').innerText);
  let landed = await waitFile(wantFile || shown, 20000);
  const added = files().filter(f => !before.has(f));
  await p.click('#btn-export-cancel'); await sleep(300);
  return { shown, landed, added, secs, notice: notice.slice(0, 100) };
};

console.log(`== ${which} ${version} | ${url} ==`);
// ---------- PRESETS ----------
await p.click('#btn-preset-trigger'); await sleep(300);
await p.type('#preset-name-input', 'Real Flow Test'); await p.click('#btn-preset-save'); await sleep(1500);
let pj = files().find(f => /\.mobius\.json$/.test(f));
let parsed = null; try { parsed = JSON.parse(fs.readFileSync(path.join(dl, pj), 'utf8')); } catch (e) {}
check('Save & Download: a real .mobius.json lands in Downloads, parses as JSON, typed name preserved', !!pj && parsed?.name === 'Real Flow Test', pj || '(none)');
check('Save & Download: file name derived from the typed name', pj === 'real_flow_test.mobius.json', pj);
check('Save & Download: file is non-empty', !!pj && fs.statSync(path.join(dl, pj)).size > 100, String(pj && fs.statSync(path.join(dl, pj)).size));

// Copy JSON with typed name -> real clipboard
await p.evaluate(() => navigator.clipboard.writeText('sentinel'));
await p.$eval('#preset-name-input', el => { el.value = ''; }); await p.type('#preset-name-input', 'Copy Typed Name'); await p.click('#btn-preset-copy'); await sleep(700);
const clip = await p.evaluate(async () => { try { return await navigator.clipboard.readText(); } catch (e) { return 'ERR ' + e.message; } });
let cj = null; try { cj = JSON.parse(clip); } catch (e) {}
check('Copy JSON: real clipboard receives valid preset JSON with the TYPED name', !!cj && cj.version === '1.0' && cj.name === 'Copy Typed Name', String(clip).slice(0, 80));
// Unicode / markup name
await p.$eval('#preset-name-input', el => { el.value = ''; }); await p.type('#preset-name-input', 'Möbius ∑ <b>x</b> "q"'); await p.click('#btn-preset-copy'); await sleep(600);
const clipU = await p.evaluate(() => navigator.clipboard.readText()); let cu = null; try { cu = JSON.parse(clipU); } catch (e) {}
check('Copy JSON: Unicode/markup/quote name survives literally', cu?.name === 'Möbius ∑ <b>x</b> "q"', cu?.name);

// Blank name fallback: Copy vs Save
await p.$eval('#preset-name-input', el => { el.value = ''; });
await p.click('#btn-preset-copy'); await sleep(600);
const clipB = await p.evaluate(() => navigator.clipboard.readText()); let cb = null; try { cb = JSON.parse(clipB); } catch (e) {}
const beforeBlank = new Set(files());
await p.click('#btn-preset-save'); await sleep(1500);
const blankFile = files().find(f => !beforeBlank.has(f) && /\.mobius\.json$/.test(f));
let sb = null; try { sb = JSON.parse(fs.readFileSync(path.join(dl, blankFile), 'utf8')); } catch (e) {}
const tsOf = n => { const m = /^Preset (.+)$/.exec(n || ''); return m ? m[1] : null; };
const toSec = s => { const m = /(\d{1,2}):(\d{2}):(\d{2})/.exec(s || ''); return m ? (+m[1]) * 3600 + (+m[2]) * 60 + (+m[3]) : NaN; };
check('Blank name: Copy JSON and Save & Download use the same "Preset <time>" fallback (times within 5 s)', !!tsOf(cb?.name) && !!tsOf(sb?.name) && Math.abs(toSec(tsOf(cb.name)) - toSec(tsOf(sb.name))) <= 5, `${cb?.name} | ${sb?.name} | ${blankFile}`);

// Import via real file chooser: the Save file
let toast;
const importFile = async f => { const [chooser] = await Promise.all([p.waitForFileChooser(), p.click('#btn-preset-import')]); await chooser.accept([f]); await sleep(900); return p.evaluate(() => document.getElementById('toast-banner').innerText); };
await p.click('#btn-preset-trigger').catch(() => {}); await sleep(100);
const modalOpen = () => p.evaluate(() => document.getElementById('preset-modal').classList.contains('visible'));
if (!(await modalOpen())) { await p.click('#btn-preset-trigger'); await sleep(300); }
toast = await importFile(path.join(dl, pj));
check('Import (real file chooser): the saved .mobius.json loads under its name', /Loaded preset: Real Flow Test/.test(toast), toast.replace(/\n/g, ' '));
// Import the copied JSON (written to a file the way a user would paste into a text file)
const copiedFile = path.join(root, 'pasted-copy.json'); fs.writeFileSync(copiedFile, clip);
if (!(await modalOpen())) { await p.click('#btn-preset-trigger'); await sleep(300); }
toast = await importFile(copiedFile);
check('Import: the JSON copied from Copy JSON keeps the typed name', /Loaded preset: Copy Typed Name/.test(toast), toast.replace(/\n/g, ' '));

// ---------- EXPORTS ----------
const e1 = await doExport('.export-res-btn[data-w="1920"]', 30);
const i1 = inspectPng(e1.shown);
check('Export #1 1920×1080: file exists, non-zero, valid PNG (IEND, IDAT decodes), 1920×1080, .png', e1.landed && /\.png$/.test(e1.shown) && i1.ok && i1.w === 1920 && i1.h === 1080, JSON.stringify({ shown: e1.shown, ...i1, secs: e1.secs }));
const e2 = await doExport(null, 30, null);
const dupName = e1.shown.replace(/\.png$/, ' (1).png');
const i2 = inspectPng(e2.added[0] || '');
check('Export #2 immediately after (1920×1080): second file lands, also valid PNG 1920×1080', e2.landed && e2.added.length === 1 && i2.ok && i2.w === 1920 && i2.h === 1080, JSON.stringify({ shown: e2.shown, added: e2.added, ...i2, secs: e2.secs }));
check('Export #2: duplicate name handled (browser renamed OR distinct name; first file untouched)', (e2.shown === e1.shown ? e2.added[0] === dupName : e2.added[0] === e2.shown) && inspectPng(e1.shown).ok, `${e1.shown} -> ${e2.added[0]}`);
const e3 = await doExport('.export-res-btn[data-w="3840"]', 120, null, 1500);
const i3 = inspectPng(e3.added[0] || '');
check('Export 4K (3840×2160, 120 passes): lands, valid PNG, correct dimensions', e3.landed && e3.added.length === 1 && i3.ok && i3.w === 3840 && i3.h === 2160, JSON.stringify({ shown: e3.shown, added: e3.added, ...i3, secs: e3.secs }));
// Reference Master 120
const before = new Set(files());
await p.click('#btn-export-trigger'); await sleep(250); await p.click('#tab-export-refmaster'); await p.click('.refmaster-pass-btn[data-passes="120"]');
const t0 = Date.now(); await p.click('#btn-export-start');
for (let i = 0; i < 2400; i++) { await sleep(250); if (await isDone()) break; }
const mname = await p.evaluate(() => document.getElementById('export-result-file').textContent);
const msecs = ((Date.now() - t0) / 1000).toFixed(1);
const mland = await waitFile(mname, 30000); const madded = files().filter(f => !before.has(f)); const im = inspectPng(madded[0] || '');
check('Reference Master (4096², 120 passes): lands, valid PNG, 4096×4096', mland && madded.length === 1 && im.ok && im.w === 4096 && im.h === 4096, JSON.stringify({ mname, madded, ...im, secs: msecs }));
await p.click('#btn-export-cancel'); await sleep(300);
// Responsive afterwards
await p.click('#btn-preset-trigger'); await sleep(300);
check('Page responsive after the whole battery (dialog opens)', await modalOpen());
check('No page errors during the battery', errs.length === 0, JSON.stringify(errs));
check('No failed/4xx network requests during the battery', failedReq.length === 0, JSON.stringify(failedReq));
console.log('console errors/warnings:', JSON.stringify(consoleErr.slice(0, 10)));
console.log('files in Downloads:', JSON.stringify(files().map(f => [f, fs.statSync(path.join(dl, f)).size])));
console.log(`${R.filter(r => r[0] === 'PASS').length}/${R.length} passed (${which} ${version})`);
await browser.close();
