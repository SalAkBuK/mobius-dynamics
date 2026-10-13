// Shared helpers for the release-candidate real-browser checks (headful Chrome/Edge, profile with a real downloads dir).
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';
export const sleep = ms => new Promise(r => setTimeout(r, ms));
// Browser locations (override with CHROME_PATH / EDGE_PATH).
export const EXE = {
  chrome: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  edge: process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
};
export async function launch({ url, root: rootArg, which = 'chrome', width = 1366, height = 768, perms = true, fresh = true, args = [], init = null }) {
  const root = path.resolve(rootArg);   // Chrome needs an absolute download directory
  if (fresh) fs.rmSync(root, { recursive: true, force: true });
  const profile = path.join(root, 'profile'), dl = path.join(root, 'Downloads');
  fs.mkdirSync(path.join(profile, 'Default'), { recursive: true }); fs.mkdirSync(dl, { recursive: true });
  if (fresh) fs.writeFileSync(path.join(profile, 'Default', 'Preferences'), JSON.stringify({ download: { default_directory: dl.replace(/\//g, '\\'), prompt_for_download: false, directory_upgrade: true } }));
  const browser = await puppeteer.launch({ executablePath: EXE[which], headless: false, userDataDir: profile, args: ['--use-gl=angle', '--use-angle=d3d11', `--window-size=${width + 40},${height + 140}`, '--enable-precise-memory-info', ...args] });
  const origin = new URL(url).origin;
  if (perms) await browser.defaultBrowserContext().overridePermissions(origin, ['clipboard-read', 'clipboard-write', 'clipboard-sanitized-write']);
  const p = await browser.newPage(); await p.bringToFront(); await p.setViewport({ width, height });
  const log = { pageErrors: [], console: [], failed: [], http: [] };
  p.on('pageerror', e => log.pageErrors.push(e.message));
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') log.console.push(m.type() + ': ' + m.text()); });
  p.on('requestfailed', r => log.failed.push(r.url() + ' ' + (r.failure()?.errorText || '')));
  p.on('response', r => { if (r.status() >= 400) log.http.push(r.status() + ' ' + r.url()); });
  if (init) await p.evaluateOnNewDocument(init);
  await p.goto(url, { waitUntil: 'load' }); await sleep(2500);
  return { browser, p, dl, log, profile, root, version: await browser.version(), which };
}
export function reporter(title) {
  const R = [];
  const check = (n, ok, d = '') => { R.push([ok ? 'PASS' : 'FAIL', n, d]); console.log(ok ? 'PASS' : 'FAIL', n, d ? '— ' + String(d).slice(0, 400) : ''); return ok; };
  // A recorded MINOR finding: prints KNOWN-MINOR while it reproduces (not a failure) and PASS once it no longer does.
  const known = (n, ok, d = '') => { R.push([ok ? 'PASS' : 'KNOWN-MINOR', n, d]); console.log(ok ? 'PASS' : 'KNOWN-MINOR', n, d ? '— ' + String(d).slice(0, 400) : ''); return ok; };
  const done = () => {
    const f = R.filter(r => r[0] === 'FAIL'), k = R.filter(r => r[0] === 'KNOWN-MINOR');
    console.log(`\n${title}: ${R.length - f.length - k.length}/${R.length} passed${k.length ? `, ${k.length} known minor finding(s) reproduced` : ''}${f.length ? ' — FAILED: ' + f.map(x => x[1]).join(' | ') : ''}`);
    if (f.length) process.exitCode = 1;
    return { total: R.length, failed: f.length, known: k.length };
  };
  return { check, known, done, R };
}
// Reference invariant, read from the live app (window.__app/__math/__renderer).
export const invariant = p => p.evaluate(async () => {
  const { CONRADI_REFERENCE: C } = await import('/math.js');
  const m = window.__math, r = window.__renderer, a = window.__app, bad = [];
  const t = (n, ok) => { if (!ok) bad.push(n); };
  const eq = (x, y) => Math.abs(x.r - y.r) < 1e-12 && Math.abs(x.i - y.i) < 1e-12, zero = x => x.r === 0 && x.i === 0;
  t('app.mode=reference', a.mode === 'reference'); t('math.mode=reference', m.mode === 'reference'); t('n=16', m.n === 16);
  for (const k of ['a', 'b', 'c', 'd']) { t('base' + k, eq(m['base' + k.toUpperCase()], C[k])); t('active ' + k, eq(m[k], C[k])); t('offset' + k, zero(m['userOffset' + k.toUpperCase()])); }
  t('pointerTarget0', zero(m.pointerTarget)); t('pointerCurrent0', zero(m.pointerCurrent)); t('shockMag0', m.shockMag === 0);
  t('drift off', m.evolving === false); t('time 0', m.time === 0); t('pointer disabled', m.pointerPerturbationEnabled === false); t('shock disabled', m.shockEnabled === false);
  t('zoom 1.65', r.zoom === 1.65 && r.targetZoom === 1.65); t('center 0', r.viewCenter[0] === 0 && r.viewCenter[1] === 0 && r.targetViewCenter[0] === 0 && r.targetViewCenter[1] === 0);
  t('palette cobalt', r.activePalette === 'cobalt');
  return bad;
});
export const appState = p => p.evaluate(() => { const a = window.__app, m = window.__math, r = window.__renderer; return { mode: a.mode, n: m.n, drift: m.evolving, pal: r.activePalette, zoom: r.zoom, a: [m.baseA.r, m.baseA.i], exporting: a.isExporting, tier: r.adaptive.mode }; });
export const toastText = p => p.evaluate(() => document.getElementById('toast-banner').innerText);
export const files = dl => fs.readdirSync(dl).filter(f => !f.endsWith('.crdownload') && !f.endsWith('.tmp')).sort();
export const inspectPng = (dl, f) => {
  let b; try { b = fs.readFileSync(path.join(dl, f)); } catch (e) { return { ok: false, why: 'unreadable' }; }
  if (!b.length) return { ok: false, why: 'zero bytes' };
  if (b.slice(0, 8).toString('hex') !== '89504e470d0a1a0a') return { ok: false, why: 'bad signature' };
  let o = 8, w = 0, h = 0, ct = 0, bd = 0, idat = [], iend = false;
  while (o + 8 <= b.length) { const len = b.readUInt32BE(o), type = b.slice(o + 4, o + 8).toString(); if (type === 'IHDR') { w = b.readUInt32BE(o + 8); h = b.readUInt32BE(o + 12); bd = b[o + 16]; ct = b[o + 17]; } if (type === 'IDAT') idat.push(b.slice(o + 8, o + 8 + len)); if (type === 'IEND') { iend = true; break; } o += 12 + len; }
  let inflated = -1; try { inflated = zlib.inflateSync(Buffer.concat(idat)).length; } catch (e) {}
  const ch = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 }[ct] || 0; const expect = h * (1 + Math.ceil(w * ch * bd / 8));
  return { ok: iend && inflated === expect, w, h, size: b.length, why: iend ? (inflated === expect ? '' : 'IDAT mismatch') : 'no IEND' };
};
export const openPanel = async p => { if (!(await p.evaluate(() => window.__app.panelOpen))) { await p.click('#btn-controls'); await sleep(350); } };
export const openSection = async (p, name) => { await openPanel(p); const open = await p.$eval('#panel-section-' + name, el => el.getAttribute('aria-expanded') === 'true'); if (!open) { await p.click('#panel-section-' + name); await sleep(250); } };
export const closeAnyDialog = async p => { for (let i = 0; i < 3; i++) { if (!(await p.evaluate(() => window.__app.isModalOpen()))) break; await p.keyboard.press('Escape'); await sleep(250); } };
export const randomizeStyle = async (p, style) => { await p.click('#btn-randomize-toggle'); await sleep(150); await p.click(`.rnd-style-btn[data-style="${style}"]`); await sleep(250); };
