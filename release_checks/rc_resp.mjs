// Responsive release check on LIVE production: 8 viewports x release surfaces, programmatic layout assertions + screenshots.
import fs from 'fs';
import path from 'path';
import { launch, reporter, sleep, closeAnyDialog } from './rc_lib.mjs';
const url = process.argv[2], root = process.argv[3], which = process.argv[4] || 'chrome';
const only = process.argv[5] ? process.argv[5].split(',') : null;
const { check, done } = reporter(`rc_resp ${which}`);
const S = await launch({ url, root, which });
const { p, log } = S;
console.log(`== ${which} ${S.version} ${url}`);
const shots = path.join(root, 'shots'); fs.mkdirSync(shots, { recursive: true });
const VIEWPORTS = [[1920, 1080], [1440, 900], [1366, 768], [1280, 720], [1024, 768], [768, 1024], [430, 932], [390, 844]];

// ---- in-page measurement helpers (installed per page load)
const install = () => p.evaluate(() => {
  window.__rc = {
    visible(e) { const r = e.getBoundingClientRect(), cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && !e.closest('[hidden]') && !e.closest('[inert]'); },
    overflowX() { return Math.max(0, document.documentElement.scrollWidth - innerWidth, document.body.scrollWidth - innerWidth); },
    // every interactive element inside `root` can be scrolled to and is actually hit-testable there (not covered by a sticky header / sibling)
    reach(rootSel) {
      const root = document.querySelector(rootSel); const bad = []; if (!root) return ['missing ' + rootSel];
      const els = [...root.querySelectorAll('button, input, select, a[href], summary, [tabindex="0"]')].filter(e => this.visible(e));
      for (const e of els) {
        e.scrollIntoView({ block: 'center', inline: 'nearest' });
        const r = e.getBoundingClientRect(); const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        const name = e.id || e.className.toString().slice(0, 30) || e.tagName;
        if (r.left < -1 || r.right > innerWidth + 1) { bad.push(name + ' x-out'); continue; }
        if (cy < 0 || cy > innerHeight) { bad.push(name + ' y-out'); continue; }
        const hit = document.elementFromPoint(cx, cy);
        const lab = hit?.closest('label');
        if (!hit || !(hit === e || e.contains(hit) || hit.contains(e) || (lab && lab.contains(e)))) bad.push(name + ' covered by ' + (hit?.id || hit?.className?.toString().slice(0, 30) || hit?.tagName));
      }
      return bad;
    },
    overlaps(sel) {
      const els = [...document.querySelectorAll(sel)].filter(e => this.visible(e)); const out = [];
      for (let i = 0; i < els.length; i++) for (let j = i + 1; j < els.length; j++) {
        if (els[i].contains(els[j]) || els[j].contains(els[i])) continue;
        const a = els[i].getBoundingClientRect(), b = els[j].getBoundingClientRect();
        const w = Math.min(a.right, b.right) - Math.max(a.left, b.left), h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (w > 2 && h > 2) out.push((els[i].id || els[i].textContent.trim().slice(0, 12)) + '×' + (els[j].id || els[j].textContent.trim().slice(0, 12)));
      }
      return out;
    },
    inViewport(sel) { const e = document.querySelector(sel); if (!e || !this.visible(e)) return 'not-visible'; const r = e.getBoundingClientRect(); return (r.left >= -1 && r.right <= innerWidth + 1 && r.top >= -1 && r.bottom <= innerHeight + 1) ? '' : `rect ${Math.round(r.left)},${Math.round(r.top)},${Math.round(r.right)},${Math.round(r.bottom)} vs ${innerWidth}x${innerHeight}`; },
    clippedText(rootSel) { const root = document.querySelector(rootSel) || document.body; return [...root.querySelectorAll('button, .pill-reference, .pill-explore, label, h1, h2, h3, dt, dd, p, span')].filter(e => this.visible(e) && e.children.length === 0 && e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflow !== 'visible' && getComputedStyle(e).textOverflow !== 'ellipsis').map(e => (e.id || e.textContent.trim().slice(0, 20))); },
    minTarget(rootSel) { const root = document.querySelector(rootSel); const sizes = [...root.querySelectorAll('button, input[type=range], select')].filter(e => this.visible(e)).map(e => { const r = e.getBoundingClientRect(); return Math.min(r.width, r.height); }); return sizes.length ? Math.round(Math.min(...sizes)) : null; },
  };
});
const shot = async (vp, name) => { try { await p.screenshot({ path: path.join(shots, `${vp[0]}x${vp[1]}_${name}.jpg`), type: 'jpeg', quality: 55 }); } catch (e) { } };
const T = (vp, n) => `${vp[0]}×${vp[1]} ${n}`;
const ui = () => p.evaluate(() => ({ running: window.__app.isExporting, result: !document.getElementById('export-result').hidden, notice: !document.getElementById('export-notice').hidden }));
const closeExportDone = async () => { const s = await ui(); if (!s.running) { await p.evaluate(() => { const b = document.getElementById('btn-export-cancel'); if (b && document.getElementById('export-modal').classList.contains('visible')) b.click(); }); await sleep(300); } };

for (const vp of VIEWPORTS) {
  if (only && !only.includes(vp[0] + 'x' + vp[1])) continue;
  const mobile = vp[0] < 500;
  await p.setViewport({ width: vp[0], height: vp[1], deviceScaleFactor: 1, isMobile: mobile, hasTouch: mobile });
  await p.reload({ waitUntil: 'load' }); await sleep(2200); await install();
  // ---- primary bar at rest
  check(T(vp, 'no horizontal page scroll (default view)'), (await p.evaluate(() => window.__rc.overflowX())) === 0, String(await p.evaluate(() => window.__rc.overflowX())));
  const barBad = await p.evaluate(() => { const r = window.__rc; return { overlaps: r.overlaps('#controls-bar button'), out: [...document.querySelectorAll('#controls-bar button')].filter(e => r.visible(e)).filter(e => { const b = e.getBoundingClientRect(); return b.left < -1 || b.right > innerWidth + 1 || b.top < -1 || b.bottom > innerHeight + 1; }).map(e => e.id || e.textContent.trim()), clipped: r.clippedText('#controls-bar') }; });
  check(T(vp, 'primary bar: all controls inside viewport, none overlapping, no clipped labels'), barBad.overlaps.length === 0 && barBad.out.length === 0 && barBad.clipped.length === 0, JSON.stringify(barBad));
  const reachBar = await p.evaluate(() => window.__rc.reach('#controls-bar'));
  check(T(vp, 'primary bar: every control reachable & hit-testable'), reachBar.length === 0, JSON.stringify(reachBar));
  const canvasFrac = await p.evaluate(() => { const c = document.getElementById('gl-canvas').getBoundingClientRect(); const ui = document.querySelector('#top-bar-container').getBoundingClientRect(); const readout = document.getElementById('equation-readout').getBoundingClientRect(); return Math.round((ui.height * ui.width + readout.height * readout.width) / (c.width * c.height) * 100); });
  console.log(`INFO ${T(vp, 'UI boxes (bar+readout) cover about')} ${canvasFrac}% of the artwork area at rest`);
  await shot(vp, 'bar');
  console.log(`INFO ${T(vp, 'smallest primary-bar target')} ${await p.evaluate(() => window.__rc.minTarget('#controls-bar'))}px`);

  // ---- toast + status banner
  await p.evaluate(() => { window.__app.showToast('Randomized [conradi-like]: Conradi Attractor Basin Variant · a rather long toast message to test wrapping at narrow widths', 60000); });
  await sleep(500); const toastIn = await p.evaluate(() => window.__rc.inViewport('#toast-banner')); await shot(vp, 'toast');
  check(T(vp, 'toast fully inside the viewport'), toastIn === '', toastIn);
  await p.evaluate(() => { window.__app.showStatusBanner('Graphics context lost — recovering… (long message for layout test) This is a longer sentence to see wrapping behaviour at narrow widths.', { level: 'warn', reload: true }); });
  await sleep(300); const banIn = await p.evaluate(() => window.__rc.inViewport('#status-banner')); const banCover = await p.evaluate(() => { const b = document.getElementById('status-banner').getBoundingClientRect(); return [...document.querySelectorAll('#controls-bar button')].filter(e => { const r = e.getBoundingClientRect(); const w = Math.min(r.right, b.right) - Math.max(r.left, b.left), h = Math.min(r.bottom, b.bottom) - Math.max(r.top, b.top); return w > 2 && h > 2; }).map(e => e.id); });
  await shot(vp, 'banner');
  check(T(vp, 'status banner inside viewport and does not cover primary controls'), banIn === '' && banCover.length === 0, JSON.stringify({ banIn, banCover }));
  await p.evaluate(() => { document.getElementById('status-banner').style.display = 'none'; window.__app.toastBanner.classList.remove('show'); });

  // ---- Controls panel with every section open
  await p.click('#btn-controls'); await sleep(450);
  for (const sec of ['view', 'math', 'quality', 'developer']) { const open = await p.$eval('#panel-section-' + sec, e => e.getAttribute('aria-expanded') === 'true'); if (!open) { await p.evaluate(s => document.getElementById('panel-section-' + s).click(), sec); await sleep(200); } }
  await p.evaluate(() => { if (!window.__app.coeffDrawerVisible) document.getElementById('btn-coeff').click(); }); await sleep(300);
  await shot(vp, 'panel_all');
  check(T(vp, 'panel open: no horizontal page scroll'), (await p.evaluate(() => window.__rc.overflowX())) === 0);
  const panelReach = await p.evaluate(() => window.__rc.reach('#controls-panel'));
  check(T(vp, 'Controls panel (all sections + coefficients): every control reachable by scrolling and not covered'), panelReach.length === 0, JSON.stringify(panelReach));
  const panelFit = await p.evaluate(() => { const r = document.getElementById('controls-panel').getBoundingClientRect(); const bar = document.getElementById('top-bar-container').getBoundingClientRect(); return { l: Math.round(r.left), t: Math.round(r.top), r: Math.round(r.right), b: Math.round(r.bottom), barBottom: Math.round(bar.bottom), vw: innerWidth, vh: innerHeight, over: window.__rc.overlaps('#controls-panel, #controls-bar button') }; });
  check(T(vp, 'panel rect inside viewport and clear of the primary bar'), panelFit.l >= -1 && panelFit.r <= panelFit.vw + 1 && panelFit.b <= panelFit.vh + 1 && panelFit.over.length === 0, JSON.stringify(panelFit));
  const clippedPanel = await p.evaluate(() => window.__rc.clippedText('#controls-panel'));
  check(T(vp, 'panel: no clipped (non-ellipsis) text'), clippedPanel.length === 0, JSON.stringify(clippedPanel));
  const readoutVsPanel = await p.evaluate(() => window.__rc.overlaps('#controls-panel, #equation-readout'));
  check(T(vp, 'readout chip does not overlap the open panel'), readoutVsPanel.length === 0, JSON.stringify(readoutVsPanel));
  console.log(`INFO ${T(vp, 'smallest panel target')} ${await p.evaluate(() => window.__rc.minTarget('#controls-panel'))}px`);
  await p.keyboard.press('Escape'); await sleep(350);

  // ---- dialogs
  const dlg = async (name, trig, id) => {
    await p.click(trig); await sleep(450); await shot(vp, name);
    const fit = await p.evaluate((id) => { const d = document.getElementById(id).querySelector('.modal-dialog'); const r = d.getBoundingClientRect(); return { l: Math.round(r.left), r: Math.round(r.right), t: Math.round(r.top), b: Math.round(r.bottom), vw: innerWidth, vh: innerHeight, sw: d.scrollWidth, cw: d.clientWidth, x: window.__rc.overflowX() }; }, id);
    const reach = await p.evaluate((id) => window.__rc.reach('#' + id + ' .modal-dialog'), id);
    check(T(vp, `${name}: dialog inside viewport horizontally, no content overflow, no page scroll`), fit.l >= -1 && fit.r <= fit.vw + 1 && fit.sw <= fit.cw + 1 && fit.x === 0, JSON.stringify(fit));
    check(T(vp, `${name}: every control (incl. footer/close) reachable and not covered`), reach.length === 0, JSON.stringify(reach));
    const clip = await p.evaluate((id) => window.__rc.clippedText('#' + id + ' .modal-dialog'), id);
    check(T(vp, `${name}: no clipped text`), clip.length === 0, JSON.stringify(clip));
    console.log(`INFO ${T(vp, name + ' smallest target')} ${await p.evaluate((id) => window.__rc.minTarget('#' + id + ' .modal-dialog'), id)}px`);
  };
  await dlg('help', '#btn-help', 'help-modal'); await p.keyboard.press('Escape'); await sleep(300);
  await p.evaluate(() => localStorage.setItem('mobius_custom_presets', JSON.stringify(Array.from({ length: 6 }, (_, i) => ({ name: i === 0 ? 'A very long preset name that goes on and on to test wrapping inside the list row ' + 'x'.repeat(60) : 'Saved ' + i, symmetry: 8, version: '1.0' })))));
  await dlg('presets', '#btn-preset-trigger', 'preset-modal'); await p.keyboard.press('Escape'); await sleep(300);
  await p.evaluate(() => localStorage.removeItem('mobius_custom_presets'));
  await dlg('export_idle', '#btn-export-trigger', 'export-modal');
  await p.click('#tab-export-refmaster'); await sleep(250); await shot(vp, 'export_master_idle');
  const reachM = await p.evaluate(() => window.__rc.reach('#export-modal .modal-dialog')); check(T(vp, 'export (Reference Master tab): all controls reachable'), reachM.length === 0, JSON.stringify(reachM));
  // running (CPU throttled), canceled, success, failed
  const cdp = await p.createCDPSession(); await cdp.send('Emulation.setCPUThrottlingRate', { rate: 8 });
  await p.click('#btn-export-start'); await sleep(900); await shot(vp, 'export_running');
  const runFit = await p.evaluate(() => ({ r: window.__rc.reach('#export-modal .modal-dialog'), x: window.__rc.overflowX(), running: window.__app.isExporting }));
  check(T(vp, 'export running: dialog fits, Cancel reachable, no page scroll'), runFit.running && runFit.r.length === 0 && runFit.x === 0, JSON.stringify(runFit));
  await p.evaluate(() => document.getElementById('btn-export-cancel').click()); for (let i = 0; i < 60; i++) { await sleep(250); if (!(await ui()).running) break; }
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 }); await sleep(400); await shot(vp, 'export_canceled');
  const canFit = await p.evaluate(() => ({ r: window.__rc.reach('#export-modal .modal-dialog'), x: window.__rc.overflowX() })); check(T(vp, 'export canceled notice: fits & reachable'), canFit.r.length === 0 && canFit.x === 0, JSON.stringify(canFit));
  await p.click('#tab-export-standard'); await p.click('.export-res-btn[data-w="1920"]'); await p.click('.export-pass-btn[data-passes="30"]'); await p.click('#btn-export-start');
  for (let i = 0; i < 120; i++) { await sleep(250); const s = await ui(); if (s.result) break; } await sleep(300); await shot(vp, 'export_success');
  const sucFit = await p.evaluate(() => ({ r: window.__rc.reach('#export-modal .modal-dialog'), x: window.__rc.overflowX(), shown: !document.getElementById('export-result').hidden })); check(T(vp, 'export success: fits & reachable'), sucFit.shown && sucFit.r.length === 0 && sucFit.x === 0, JSON.stringify(sucFit));
  await closeExportDone();
  await p.click('#btn-export-trigger'); await sleep(350); await p.click('#tab-export-refmaster'); await p.click('.refmaster-pass-btn[data-passes="240"]'); await p.click('#btn-export-start'); await sleep(500);
  await p.evaluate(() => { window.__lc = window.__renderer.gl.getExtension('WEBGL_lose_context'); window.__lc.loseContext(); });
  for (let i = 0; i < 80; i++) { await sleep(250); const s = await ui(); if (s.notice || s.result) break; } await sleep(300); await shot(vp, 'export_failed');
  const failFit = await p.evaluate(() => ({ r: window.__rc.reach('#export-modal .modal-dialog'), x: window.__rc.overflowX(), notice: document.getElementById('export-notice').innerText.slice(0, 40) })); check(T(vp, 'export failed notice: fits & reachable'), failFit.r.length === 0 && failFit.x === 0, JSON.stringify(failFit));
  await p.evaluate(() => window.__lc.restoreContext()); await sleep(2500); await closeExportDone(); await closeAnyDialog(p);
  // ---- Hide / Show
  await p.keyboard.press('h'); await sleep(500); await shot(vp, 'hidden');
  const showIn = await p.evaluate(() => window.__rc.inViewport('#btn-show-ui')); check(T(vp, 'UI hidden: Show-UI button is inside the viewport'), showIn === '', showIn);
  await p.click('#btn-show-ui'); await sleep(450);
  await p.setViewport({ width: Math.max(360, vp[0] - 120), height: vp[1], isMobile: mobile, hasTouch: mobile }); await sleep(500);
  check(T(vp, 'live resize (-120px): no horizontal page scroll'), (await p.evaluate(() => window.__rc.overflowX())) === 0);
}
check('no uncaught page errors during responsive run', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
console.log('console:', JSON.stringify([...new Set(log.console)].slice(0, 8)));
done(); await S.browser.close();
