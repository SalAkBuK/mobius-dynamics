// Keyboard / focus / modal audit with REAL key events on LIVE production.
import { launch, reporter, sleep, invariant, appState, openPanel, closeAnyDialog } from './rc_lib.mjs';
const url = process.argv[2], root = process.argv[3], which = process.argv[4] || 'chrome';
const { check, done } = reporter(`rc_kbd ${which}`);
const S = await launch({ url, root, which });
const { p, log } = S;
console.log(`== ${which} ${S.version} ${url}`);
const snap = () => p.evaluate(() => { const a = window.__app, r = window.__renderer, m = window.__math; return JSON.stringify({ mode: a.mode, n: m.n, drift: m.evolving, pal: r.activePalette, bloom: r.bloomEnabled, debug: a.debugMode, uiHidden: a.uiHidden, readout: a.readoutVisible, coeff: a.coeffDrawerVisible, tier: r.adaptive.mode, panel: a.panelOpen, raw: r.viewMode, zoom: r.targetZoom, paused: m.evolving }); });
const active = () => p.evaluate(() => { const e = document.activeElement; return { id: e?.id || '', tag: e?.tagName, cls: (e?.className || '').toString().slice(0, 40), inModal: !!e?.closest?.('.modal-overlay, [role="dialog"], #export-modal, #help-modal, #preset-modal'), text: (e?.innerText || e?.value || '').slice(0, 24) }; });
const modalOpenId = () => p.evaluate(() => ['export-modal', 'help-modal', 'preset-modal'].find(id => document.getElementById(id).classList.contains('visible')) || null);

const dialogs = [
  { name: 'Help', key: '?', trigger: '#btn-help', id: 'help-modal', keyOpen: async () => { await p.keyboard.press('?'); } },
  { name: 'Presets', key: 's', trigger: '#btn-preset-trigger', id: 'preset-modal' },
  { name: 'Export', key: 'e', trigger: '#btn-export-trigger', id: 'export-modal' },
];
for (const d of dialogs) {
  // --- open by keyboard shortcut
  await p.evaluate(() => document.activeElement?.blur?.());
  if (d.keyOpen) await d.keyOpen(); else await p.keyboard.press(d.key);
  await sleep(450);
  let open = await modalOpenId(); let a = await active();
  check(`${d.name}: opens from its keyboard shortcut and focus moves into the dialog`, open === d.id && a.inModal, JSON.stringify({ open, a }));
  // Tab trap: 40 forward + 10 backward tabs, focus never leaves
  let leaked = 0; for (let i = 0; i < 40; i++) { await p.keyboard.press('Tab'); if (!(await active()).inModal) leaked++; }
  await p.keyboard.down('Shift'); for (let i = 0; i < 12; i++) { await p.keyboard.press('Tab'); if (!(await active()).inModal) leaked++; } await p.keyboard.up('Shift');
  check(`${d.name}: Tab / Shift+Tab stay trapped inside the dialog (52 presses)`, leaked === 0, 'leaks=' + leaked);
  // shortcuts do not mutate session
  await p.evaluate(() => ['export-modal','help-modal','preset-modal'].map(i => document.getElementById(i)).find(e => e.classList.contains('visible'))?.querySelector('.modal-dialog')?.focus?.());
  const before = await snap();
  for (const k of ['1', '2', '3', 'h', 'b', 'x', 'r', 'd', 't', 'o', 'p', ' ']) { if (d.id === 'preset-modal' && false) continue; await p.keyboard.press(k); await sleep(40); }
  // typing in the preset name input is legitimate there; ensure focus wasn't in input for this check
  const after = await snap();
  check(`${d.name}: no shortcut key mutates the session behind the open dialog`, before === after, before === after ? '' : before + '\n' + after);
  // Esc closes
  await p.keyboard.press('Escape'); await sleep(400);
  open = await modalOpenId(); a = await active();
  check(`${d.name}: Esc closes it`, open === null);
  check(`${d.name}: focus returns to a sensible element (trigger or body) — not lost inside the hidden dialog`, !a.inModal, JSON.stringify(a));
  // --- open by trigger button with the keyboard (focus the button, press Enter)
  await p.focus(d.trigger); await p.keyboard.press('Enter'); await sleep(450);
  open = await modalOpenId(); check(`${d.name}: trigger button + Enter opens it`, open === d.id);
  await p.keyboard.press('Escape'); await sleep(350); a = await active();
  check(`${d.name}: after Esc, focus is back on the trigger that opened it`, a.id === d.trigger.slice(1), JSON.stringify(a));
  // --- open by mouse click, close by its Close button
  await p.click(d.trigger); await sleep(400); open = await modalOpenId();
  const closeSel = { 'help-modal': '#btn-help-close', 'preset-modal': '#btn-preset-close', 'export-modal': '#btn-export-close' }[d.id];
  await p.click(closeSel); await sleep(350);
  check(`${d.name}: opens by click and closes with its ✕ button`, open === d.id && (await modalOpenId()) === null);
  // --- clicking the backdrop closes (non-export) / is harmless
  await p.click(d.trigger); await sleep(350); await p.mouse.click(6, 6); await sleep(350);
  console.log(`INFO ${d.name}: backdrop click ->`, (await modalOpenId()) === null ? 'closed' : 'stays open'); await closeAnyDialog(p);
}
// Nested: shortcut for another dialog while one is open does nothing
await p.keyboard.press('s'); await sleep(300); await p.keyboard.press('e'); await sleep(300); await p.keyboard.press('?'); await sleep(300);
check('with Presets open, e / ? do not open a second dialog', (await modalOpenId()) === 'preset-modal' || (await p.evaluate(() => document.querySelectorAll('.modal-overlay.visible').length)) <= 1);
await closeAnyDialog(p);

// ---- typing in the preset name field must not trigger shortcuts
await p.keyboard.press('s'); await sleep(350); await p.click('#preset-name-input'); const b4 = await snap();
await p.keyboard.type('12 3hbxrdtop e?s ', { delay: 20 }); const typed = await p.$eval('#preset-name-input', e => e.value);
check('typing digits/letters/space in the preset name field enters text and fires no shortcut', typed === '12 3hbxrdtop e?s ' && (await snap()) === b4, typed);
await p.keyboard.press('Escape'); await sleep(300); await p.$eval('#preset-name-input', e => e.value = '');
await closeAnyDialog(p);

// ---- dropdown + panel Esc ladder
await p.click('#btn-randomize-toggle'); await sleep(200);
const menuOpen = await p.evaluate(() => document.getElementById('randomize-menu').classList.contains('visible'));
await p.keyboard.press('Escape'); await sleep(200);
const menuAfter = await p.evaluate(() => document.getElementById('randomize-menu').classList.contains('visible'));
check('Esc closes an open dropdown (Randomize menu)', menuOpen && !menuAfter);
await p.click('#btn-export-toggle'); await sleep(200); const exMenu = await p.evaluate(() => document.getElementById('export-menu').classList.contains('visible')); await p.keyboard.press('Escape'); await sleep(200);
check('Esc closes the Export menu', exMenu && !(await p.evaluate(() => document.getElementById('export-menu').classList.contains('visible'))));
await p.click('#btn-controls'); await sleep(400); const pOpen = await p.evaluate(() => window.__app.panelOpen);
await p.keyboard.press('Escape'); await sleep(350); const pClosed = !(await p.evaluate(() => window.__app.panelOpen)); const fa = await active();
check('Esc closes the Controls panel; focus returns to the Controls button', pOpen && pClosed && fa.id === 'btn-controls', JSON.stringify(fa));
// panel open + dropdown open: Esc closes dropdown first
await p.click('#btn-controls'); await sleep(300); await p.click('#btn-randomize-toggle'); await sleep(200); await p.keyboard.press('Escape'); await sleep(250);
check('Esc with panel+dropdown open closes the dropdown first, panel remains', !(await p.evaluate(() => document.getElementById('randomize-menu').classList.contains('visible'))) && (await p.evaluate(() => window.__app.panelOpen)));
await p.keyboard.press('Escape'); await sleep(300);

// ---- Hide UI never strands
await p.keyboard.press('h'); await sleep(500);
const hidden = await p.evaluate(() => ({ hid: window.__app.uiHidden, showBtn: (() => { const b = document.getElementById('btn-show-ui'); const r = b.getBoundingClientRect(); const cs = getComputedStyle(b); return { w: r.width, h: r.height, vis: cs.visibility, op: cs.opacity, disp: cs.display }; })(), inert: document.getElementById('ui-container').inert }));
check('H hides the UI; the Show-UI button is visible and focusable', hidden.hid && hidden.showBtn.w > 10 && hidden.showBtn.vis === 'visible' && hidden.showBtn.disp !== 'none' && hidden.inert, JSON.stringify(hidden));
let leakedHidden = 0; for (let i = 0; i < 12; i++) { await p.keyboard.press('Tab'); const ae = await p.evaluate(() => document.activeElement?.id || document.activeElement?.tagName); if (!['btn-show-ui', 'BODY', 'HTML'].includes(ae)) leakedHidden++; }
check('while hidden, Tab reaches only the Show-UI button (no invisible controls)', leakedHidden === 0, 'leaks=' + leakedHidden);
await p.click('#btn-show-ui'); await sleep(500);
check('clicking Show UI restores everything', !(await p.evaluate(() => window.__app.uiHidden)) && !(await p.evaluate(() => document.getElementById('ui-container').inert)));
await p.keyboard.press('h'); await sleep(400); await p.keyboard.press('h'); await sleep(400);
check('H toggles hide/show by keyboard (round trip)', !(await p.evaluate(() => window.__app.uiHidden)));
// Hide button inside the panel
await p.click('#btn-controls'); await sleep(300); await p.evaluate(() => document.getElementById('panel-section-view').getAttribute('aria-expanded') === 'true' || document.getElementById('panel-section-view').click()); await sleep(200);
await p.click('#btn-hide'); await sleep(450); const h2 = await p.evaluate(() => window.__app.uiHidden); await p.click('#btn-show-ui'); await sleep(400);
check('panel "Hide" button hides and the corner button brings it back', h2 && !(await p.evaluate(() => window.__app.uiHidden)));
await p.keyboard.press('Escape'); await sleep(250);
// Hide with a modal open: H must not hide
await p.keyboard.press('e'); await sleep(350); await p.keyboard.press('h'); await sleep(250);
check('H with a dialog open does not hide the UI behind it', !(await p.evaluate(() => window.__app.uiHidden))); await closeAnyDialog(p);

// ---- Tab order sweep: every focus stop is visible
await p.evaluate(() => document.activeElement?.blur?.()); const stops = [];
for (let i = 0; i < 45; i++) { await p.keyboard.press('Tab'); stops.push(await p.evaluate(() => { const e = document.activeElement; if (!e || e === document.body) return null; const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); const vis = r.width > 0 && r.height > 0 && cs.visibility === 'visible' && cs.display !== 'none' && !e.closest('[inert]') && !e.closest('[hidden]'); const onscreen = r.bottom > 0 && r.right > 0 && r.left < innerWidth && r.top < innerHeight; const ring = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0 || cs.boxShadow !== 'none'; return { id: e.id || e.className?.toString().slice(0, 24) || e.tagName, vis, onscreen, ring }; })); }
const invisibleStops = stops.filter(s => s && (!s.vis || !s.onscreen)); const noRing = stops.filter(s => s && !s.ring);
check('Tab sweep (45 stops): every stop is a visible, on-screen element', invisibleStops.length === 0, JSON.stringify(invisibleStops));
check('Tab sweep: every stop shows a focus indicator (outline or ring)', noRing.length === 0, JSON.stringify(noRing.map(x => x.id)));
// Enter/Space natively activate buttons
await p.focus('#btn-mode-explore'); await p.keyboard.press('Enter'); await sleep(300); const m1 = (await appState(p)).mode;
await p.focus('#btn-mode-reference'); await p.keyboard.press('Space'); await sleep(300); const m2 = (await appState(p)).mode;
check('Enter on focused Explore button -> Explore; Space on focused Reference button -> Reference', m1 === 'explore' && m2 === 'reference', m1 + '/' + m2);
await p.focus('#btn-randomize-toggle'); await p.keyboard.press('Space'); await sleep(250); const spaceOpen = await p.evaluate(() => document.getElementById('randomize-menu').classList.contains('visible')); await p.keyboard.press('Escape');
check('Space on the focused Randomize toggle opens its menu (Space is not stolen as Pause)', spaceOpen);
// Reference remains canonical through all of that
const bad = await invariant(p); check('Reference invariant intact after the whole keyboard audit', bad.length === 0, bad.join());
check('no uncaught page errors', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
check('no failed requests / HTTP >= 400', log.failed.length === 0 && log.http.length === 0, JSON.stringify([log.failed, log.http]));
console.log('console:', JSON.stringify(log.console.slice(0, 10)));
done(); await S.browser.close();
