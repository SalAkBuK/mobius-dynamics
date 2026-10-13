# UI/UX Audit, Redesign Plan and Implementation Plan

**Project:** Möbius Complex Dynamics Laboratory (`SalAkBuK/mobius-dynamics`)
**Baseline audited:** `main` @ `1f14dd4` (working tree clean)
**Scope:** UI/UX only. No production file was modified, nothing was committed or pushed.
**Status:** Final record. The audit (§1-6), the redesign plan (§7), the implementation plan (§8) and the owner decisions (§9) were carried out in three phases; the results are in §10 (Phase A), §11 (Phase B) and §12 (Phase C / final). The baseline audited below is `1f14dd4`; the implementation is the history from `ui-checkpoint-1` to `ui-checkpoint-3`.

Contents

1. Method and limits of this audit
2. Current UI overview (inventory, tiers, shortcuts)
3. Screenshot index
4. Full issue list (P0 → P3)
5. Prioritized shortlist
6. Findings by audit category (A–N)
7. **Phase 2:** proposed interface structure (revised for owner decisions)
8. **Phase 3:** implementation plan (Phases A → B → C with checkpoints)
9. Owner decisions (final) and what is explicitly out of scope

---

## 1. Method and limits of this audit

**What was done.** The real `index.html` + `app.js` from `main` were served locally (`python -m http.server`) and driven in headless Microsoft Edge 155 through `puppeteer-core`. I clicked through every mode and modal, measured the DOM (bounding boxes, hit-tests, computed styles, contrast), exercised the keyboard, forced failure states, and read `index.html`, `app.js`, and the relevant parts of `math.js` / `renderer.js` / `adaptive.js`. The Vercel production URL was not used because I don't have it; the deployed site serves this same code.

**Viewports tested:** 1920×1080, 1440×900, 1366×768, 1280×720, 1024×768, 390×844 (portrait), 844×390 (landscape).

**Limits, stated plainly:**

| Limit | Consequence |
|---|---|
| No physical GPU: WebGL ran on SwiftShader (software). Auto quality fell to *Potato* (GPU EMA 24–63 ms). | Layout, DOM, interaction and copy findings are valid. Frame-rate, Auto-tier behaviour and export **timings are not representative**. I do not quote any export duration. |
| Exports finished their "develop" phase almost instantly under software GL; the time sat in the last phases (`Encoding PNG… 98%`, `Encoding 4096×4096 PNG… 99%`). | Cancel was exercised at those late stages. A mid-pass cancel and a Reference Master *success* flow were **not** observed visually. Success paths are verified from code (`app.js:1048-1054`, `1135-1141`). |
| Context loss was simulated with `WEBGL_lose_context`. | Real driver resets may differ. The messaging path is the same code. |
| No real touch device, screen reader, or ≥2560-wide display. | Mobile findings come from viewport emulation + code reading (no touch/pinch handlers exist). Contrast was computed against a fixed dark background (`#050a16`); over bright artwork the glass panels are lighter, so real contrast is **equal or worse**. |
| Existing test suites (`test_*.html` / `.py`) were **not** run (Playwright is not installed here). | I read which DOM ids/text they depend on (§8, "Constraints"). |

Items marked *(code-verified)* were confirmed in source but not reproduced visually. Everything else was reproduced.

---

## 2. Current UI overview

### 2.1 Layout as built

- Full-viewport WebGL canvas (the artwork).
- **One floating glass toolbar**, top-centre (`#controls-bar`), holding **44 buttons** (33 visible + 11 inside two dropdowns) plus 3 text labels (`Mode`, `Order n`, `Quality`).
- A **mode status pill** under the toolbar.
- **Equation readout** panel, bottom-left, 228×160 px.
- **Coefficient drawer** (4 sliders), absolutely positioned at `top: 68px`, centred.
- **Debug overlay** (17 rows, 483 px wide), top-right at `top: 68px`.
- Two modals (Export, Presets), one single-slot toast (bottom-centre), and a "press H to restore" hint that never shows (UX-02).

**Root cause of most layout trouble:** `#top-bar-container` is `left: 50%; transform: translateX(-50%)`. A shrink-to-fit box with `left: 50%` can be at most 50 % of the viewport wide, so the toolbar is capped at **vw/2** (measured: 960 @1920, 720 @1440, 683 @1366, 640 @1280, 515 @1024). A 33-control bar wrapped into that budget grows taller as the window shrinks, while the drawer and overlays use hard-coded `top: 68px`.

| Viewport | Toolbar w × h | Rows | Chrome bottom (toolbar + pill) | Share of viewport height covered |
|---|---|---|---|---|
| 1920×1080 | 960 × 66 | 2 | 100 px | 9 % |
| 1440×900 | 720 × 94 | 3 | 128 px | 14 % |
| 1366×768 | 683 × 94 | 3 | 128 px | 17 % |
| 1280×720 | 640 × 118 | 4 | 152 px | 21 % |
| 1024×768 | 515 × 150 | 5 | 184 px | 24 % |
| 390×844 | 382 × 178 | 6 | 212 px | 25 % |
| 844×390 | ≈ 515 × 145 | 4 | ≈ 185 px | ≈ 47 % (read from screenshot, not measured) |

### 2.2 Control inventory and tiering

| Control | Where | Tier | Notes |
|---|---|---|---|
| Reference / Explore | toolbar | **Primary** | 10 px label; the only mode switch |
| 🎲 Randomize + ▾ (6 families) | toolbar | **Primary** (Explore action) | ▾ is 14 px wide |
| 📷 Export 4K | toolbar | **Primary** | label hard-codes "4K" though modal offers 3 sizes |
| 💎 Reference Master | toolbar | **Primary / secondary** | filled button, same weight as Export 4K |
| 💾 Presets | toolbar | Common | |
| Order n: 3 5 8 12 16 24 32 | toolbar | Common (Explore) | 20×24 px targets |
| Palette ▾ (5) | toolbar | Common | |
| Zoom + − 1× | toolbar | Common (Explore) | |
| Pause/Resume ("Drift: Off" in Reference) | toolbar | Common (Explore) | |
| Reset | toolbar | Common | semantics differ by mode (UX-22) |
| Hide [H] | toolbar | Common utility | leaves a dead end (UX-02) |
| Quality: Auto Low Standard High Ultra Extreme Brute Force | toolbar | **Advanced** | 7 buttons; *Potato* exists internally, reachable only via Auto |
| Coeffs (drawer, 4 sliders + reset) | toolbar | Advanced | |
| Readout toggle, Bloom: ON | toolbar | Advanced | |
| Raw | toolbar | **Debug** | |
| Debug [D] (+ 17-row overlay) | toolbar | **Debug** | sits beside Hide, same styling as user controls |
| Gain | — | *no UI* | exists in renderer only |

**Count:** ~5 primary, ~17 common, ~12 advanced, 2 debug. Roughly 40 % of permanently visible controls are advanced/debug.

### 2.3 Keyboard shortcuts (from `app.js:587-623`)

`1` Reference · `2` Explore · `3` Randomize · `H` hide UI · `D` debug · `Space` pause (Explore) · `R` reset · `B` bloom · `T` raw · `O` readout · `P` coefficient drawer · `E` export · `S` presets · `X` brute-force toggle.
**Only `D` and `H` are visible on buttons.** Tooltips advertise `+` / `−` for zoom, but **no such key handler exists**. The README's key table (1–6 "morphology presets", `N`, `P` pause, `H` readout) does not match the app.

### 2.4 What already works well (keep)

- Dark glass language, blue (Reference) / violet (Explore) colour coding **plus** a text label (not colour-only).
- The pill + disabled "Drift: Off" + disabled sliders in Reference are good patterns (the lock is explained in place).
- Modals fit at 390×844 (`m3`, `m4`): no overflow.
- Export display-hold (frozen frame while exporting) and full session restore.
- Equation readout. It is the project's identity; keep it.
- Startup failure path (`role="alert"` `#graphics-error`).

---

## 3. Screenshot index

**In the repo (`docs/ui/screenshots/`, 8 representative JPEGs from the baseline audit):**

| File | State |
|---|---|
| `v_1920x1080_landing` | Baseline: Reference landing at 1920×1080 |
| `v_1366x768_landing` | Toolbar wrapped to 3 rows, "QUALITY" orphaned from its buttons |
| `a2_explore_drawer_1366` | Drawer obstruction: ΔRe(a) hidden under the mode pill |
| `v_1366x768_drawer_debug` | Drawer + Debug overlay + toolbar colliding |
| `p2_presets_long_dup_corrupt` | Preset grid overflowing the dialog; long/duplicate/corrupt entries |
| `m3_export_refmaster_390` | Narrow export modal (fits) |
| `m1_toast_overflow_390` | Long toast clipped at both edges |
| `v_390x844_landing` | Narrow layout: 25 % chrome, pill clipped |

**Full set (46 images) kept locally, outside the repo:** `..\mobius-dynamics-ui-audit-screenshots-full\` (sibling of the repo folder). File names cited in the issue list (`a1`, `b1`, `e1`, `g1`, `k1`, `q1`, `x1`–`x10`, `f1`, `r1`–`r3`, `m2`, `m4`–`m6`, `v_<size>_*`) refer to that set.

---|---|
| `01_landing_1440x900` | Reference landing, 1440×900 |
| `v_1920x1080_landing`, `v_1440x900_landing`, `v_1366x768_landing`, `v_1280x720_landing`, `v_1024x768_landing`, `v_390x844_landing` | Landing at each viewport |
| `v_<size>_drawer_debug` (all six) | Coeffs drawer + Debug overlay open in Reference |
| `a1_explore_toast`, `a2_explore_drawer_1366` | Explore mode; drawer with ΔRe(a) hidden under pill |
| `b1_randomize_menu`, `b2_randomize_toast` | Randomize menu (clipped by pill); post-randomize toast |
| `c1_palette_menu` | Palette dropdown |
| `d1_back_to_reference_toast` | Explore → Reference (state discarded) |
| `e1_dimmed_n8_click_switches_mode`, `e2_zoom_in_ref_toast` | Dimmed "locked" control that switches mode; zoom lock toast |
| `g1_ui_hidden` | UI hidden: no way back shown |
| `k1_focus_ring` | Focused button (no visible ring) |
| `p1_presets_empty`, `p2_presets_long_dup_corrupt`, `p3_saved_toast` | Presets modal states |
| `q1_bruteforce_selected` | Brute Force selected, no warning |
| `x1_export_standard`, `x2_export_refmaster` | Export modal, both tabs |
| `x3_standard_progress*`, `x4_tab_switch_during_export` | Export running; tab switched mid-run |
| `x5_after_cancel`, `x6_stale_status_after_cancel`, `x9_master_progress`, `x10_master_after_cancel` | Cancel states |
| `f1_export_failure_1366` | Failure state (stubbed 1285 OOM error) |
| `r1_context_lost_toast`, `r2_context_lost_after_toast_gone`, `r3_restored` | Context loss / recovery |
| `m1_toast_overflow_390`, `m2_drawer_390`, `m3_export_refmaster_390`, `m4_presets_390`, `m5_rand_menu_390`, `m6_landscape_844x390` | Narrow / mobile-like |

---

## 4. Full issue list

**Legend.** *Cat* = what kind of fix: **L**ayout · **H**ierarchy · **I**nteraction · **C**opy · **R**esponsive · **P**olish. *Area* = audit category A–N from the brief. *Files* = what an implementation would touch (`HTML` = index.html incl. its `<style>`, `JS` = app.js). *Engine* = does the fix risk renderer/math/export behaviour. Every proposed fix leaves the engine untouched unless stated.

### P0 — blocks a task

#### UX-01 · P0 · L/R · Area H, G · Coefficient drawer is covered by the toolbar and mode pill
- **Element:** `#coeff-drawer` (fixed `top: 68px`) vs `#top-bar-container` (z-index 10 > drawer 9). *Shots:* `a2_explore_drawer_1366`, `v_1366x768_drawer_debug`, `v_1280x720_drawer_debug`.
- **Goal:** adjust the ΔRe(a) offset; in Reference, read why sliders are locked.
- **Problem:** The toolbar + pill end at y = 128 (1440/1366), 152 (1280), 184 (1024), 212 (390), but the drawer's first slider sits at y ≈ 108. **Hit-test at 1366×768: `slider-a-re` is intercepted by `#mode-status-pill`.** ΔRe(a) cannot be grabbed at any width ≤ 1440. It clears only at ≥ 1920 (pill ends y = 100). In Reference the 🔒 "locked — switch to Explore" notice and the drawer title are hidden at the same widths, so users see sliders that don't move and are never told why.
- **Repro:** open at 1366×768 → press `2` → press `P` → try to drag the top slider.
- **Fix:** Position drawer/overlays relative to real chrome height (CSS variable `--chrome-h` set by a `ResizeObserver` on the top container) or move the drawer out of the toolbar's footprint entirely (see §7). Minimal version: a few CSS lines + ~8 lines of JS.
- **Risk:** low · **Files:** HTML, JS (tiny) · **Engine:** none.

#### UX-02 · P0 · I/H · Area I, M · "Hide [H]" leaves no way back
- **Element:** `#btn-hide`, `#hint-unhide`. *Shot:* `g1_ui_hidden`.
- **Goal:** view the artwork unobstructed, then bring controls back.
- **Problem:** `#hint-unhide` is `display:none` and the JS toggles a `.visible` class that has **no CSS rule**, so the "Press H to restore controls" hint never appears (computed display after pressing H = `none`). The whole UI is `opacity:0; pointer-events:none`. On any touch device there is no `H` key, so one tap on "Hide [H]" strands the user until reload. On desktop, nothing tells them the key.
- **Repro:** click **Hide [H]**. Nothing visible remains except the artwork (and a toast, if one is pending).
- **Fix:** make the hint visible (CSS `#hint-unhide.visible{display:block}`), fade it after ~4 s, and add a tiny persistent corner "show controls" button that works by click/tap.
- **Risk:** low · **Files:** HTML, JS (few lines) · **Engine:** none.

### P1 — major friction

#### UX-03 · P1 · L/H/R · Area A, H, L · The toolbar is one 33-control strip squeezed into half the viewport
- **Element:** `#controls-bar`. *Shots:* `01_landing_1440x900`, all `v_*_landing`.
- **Problem:** (a) width capped at vw/2 (see §2.1) so it wraps into 3–6 rows; (b) wrapping splits groups: at 1440 and 1366 the **"QUALITY" label ends row 1 while its buttons start row 2**; at 1280 "Palette" sits alone; (c) it covers 14–25 % of viewport height at ≤ 1440 wide, and the top petals of the Reference artwork sit under it at ≤ 1366; (d) everything shares one weight, so primary actions, toggles and debug are visually identical (see UX-12 for the filled-button problem).
- **Repro:** load at 1366×768 and 1280×720.
- **Fix (owner decision 1):** two steps. **Phase A, immediately:** remove the 50 % width cap (`left:0; right:0; margin:auto; width:max-content; max-width:98vw`) so the existing bar wraps at ~98 vw only. **Phase B:** the structural fix, a one-row primary bar plus a docked Controls panel with a collapsed Developer section (§7). The interim fix is not a substitute for the restructure.
- **Risk:** low (Phase A) / medium (Phase B) · **Files:** HTML, JS (selectors keep ids) · **Engine:** none.

#### UX-04 · P1 · I · Area J · No keyboard focus indicator
- **Element:** global `button { outline: none }` with no `:focus-visible` replacement. *Shot:* `k1_focus_ring`.
- **Problem:** Tab through the toolbar: the focused button has `outline: none 3px`, no box-shadow, no background change. A keyboard user cannot see where they are.
- **Fix:** `:focus-visible` ring using the existing blue (`rgba(96,165,250,.9)`), for buttons, sliders, tabs, the file label.
- **Risk:** very low · **Files:** HTML (CSS) · **Engine:** none.

#### UX-05 · P1 · I · Area I, J · Space key is hijacked, so focused buttons can't be activated with Space
- **Element:** `window keydown` handler, `app.js:600-602`.
- **Problem:** `Space` calls `preventDefault()` for every target except text/range `<input>`s, even in Reference where it does nothing. Measured: with **Bloom** focused, `Space` did not toggle it; `Enter` did. Standard button semantics are broken for keyboard users on every control.
- **Fix:** only intercept Space when the target is not a button/link/input/slider (and only in Explore).
- **Risk:** low · **Files:** JS (2 lines) · **Engine:** none.

#### UX-06 · P1 · I/C · Area J · Modals are not modal
- **Element:** `#export-modal`, `#preset-modal`. *Measured:*
  - no `role="dialog"`, `aria-modal`, or label; the toast has no `role="status"`;
  - opening a modal leaves focus on the trigger; the next `Tab` lands on **Coeffs behind the modal**;
  - **Esc and backdrop click do nothing**; only the ✕/Done/Cancel buttons close;
  - global shortcuts stay live: with the Presets modal open, `H` hid the UI and `2` switched mode behind it;
  - during an export, events whose target is inside the modal bypass the input blocker (`app.js:485-491`), so `E` (focus in modal) flips the export type mid-run.
- **Fix:** focus into the dialog on open + restore on close, trap Tab, Esc closes (blocked while exporting, with a hint), shortcuts suspended while a modal is open, ARIA roles/labels, `aria-live="polite"` on toast and export status.
- **Risk:** low–medium (lots of small edits) · **Files:** HTML, JS · **Engine:** none. *Note:* Esc must not cancel a running export silently — see UX-14.

#### UX-07 · P1 · I/C · Area B, I · Going back to Reference silently destroys the Explore session
- **Element:** `#btn-mode-reference` / key `1` / **Reset** in Reference. *Shot:* `d1_back_to_reference_toast`.
- **Problem:** `setMode('reference')` resets palette to cobalt, zoom/centre, all offsets, and clears accumulation (`app.js:322-338`). Measured: Explore after `chaotic` + Solar palette (base c.re 7.506) → click **Reference** → cobalt, c.re 6.401, and **no way back**. The toast says only "Exact Conradi artwork restored". A user peeking at Reference loses their work. Also: clicking **Reference while already in Reference**, or pressing **Reset** there, re-runs the same function (clears the settled image, re-toasts) *(code-verified)*.
- **Fix (owner decision 2, UI-state only):** keep an **in-memory Explore stash**. On leaving Explore for Reference, snapshot the Explore session; Reference then resets to the exact canonical state as today (the Reference invariant is not touched). On re-entering Explore, **resume the stash automatically**: no confirm, no restore button. A small **"Start fresh"** action (Controls → Mathematics) discards the stash and returns Explore to its canonical starting point. Full rules in §8 Phase B, commit B1. Also (audit item, not part of the owner decisions): clicking the already-active mode button or pressing its key becomes a no-op instead of clearing a settled image; the **Reset** button's behaviour is unchanged.
- **Risk:** medium · **Files:** JS (`setMode` wrapper + stash) · **Engine:** none. Math and renderer are not modified; the stash is a plain data object in `app.js`, restored through the same setters `loadPresetObject` already uses.

#### UX-08 · P1 · C/H · Area E · The UI never says Quality is *live preview only*, and never shows what Auto chose
- **Element:** toolbar **Quality** group (`.quality-btn`). *Shot:* `v_*_landing`.
- **Problem:**
  - The label is just "QUALITY". Nothing says it governs the live preview and **not** exports. Code confirms exports use fixed workloads independent of the tier: Standard 589,824 × 12, Reference Master 589,824 × 16 (`renderer.js:1621-1622, 1982-1983`). Users can reasonably believe picking *Low* lowers the Master.
  - **Auto** is lit, but the actual tier (e.g. `AUTO (POTATO)` in this run) appears only in the Debug overlay. Auto promotes/demotes silently.
  - The meaningful numbers live in hover tooltips ("Low (75k x 8)", "589k x 16, 9.44M deposits/frame") — jargon, invisible on touch.
  - 7 buttons; tiers Ultra / Extreme / Brute Force are three steps of "more", with names that are playful rather than informative.
- **Fix (copy + hierarchy, no behaviour change):** label **"Live preview quality"** with a one-line helper "Preview only — exports use their own settings"; when Auto is active, show the resolved tier as explicit read-only copy, **"Current tier: High"** (never "Now: High" or a bare tier name that could read as a selection). **Tier names, the set of tiers and their order are unchanged** (no regrouping, no "More" step in this pass). Owner-approved item: "Live preview quality" clarification.
- **Risk:** low · **Files:** HTML, JS (read `adaptive.getStatus()`, display only) · **Engine:** none (read-only).

#### UX-09 · P1 · I/H · Area B, I · "Locked" controls in Reference look enabled and do surprising things
- **Elements:** `.sym-btn` (Order n), Palette items, `#btn-zoom-in/out`, wheel on canvas, 🎲. *Shots:* `e1_dimmed_n8_click_switches_mode`, `e2_zoom_in_ref_toast`.
- **Problem:** In Reference the Order-n buttons are dimmed (opacity 0.4) and the tooltip says "Locked to n=16 in Reference mode", **but clicking `8` leaves Reference and sets n = 8** (measured: mode `explore`, n 8). Choosing any non-cobalt palette likewise silently switches to Explore. Zoom ± and the mouse wheel show a "Framing locked" toast instead, and **each wheel tick re-fires the toast**. Sliders and Pause, by contrast, are truly disabled — three different lock behaviours in one mode.
- **Fix (owner decision 5):** **Order-n and palette stay fully usable in Reference and are not dimmed or presented as disabled.** Clicking them may still enter Explore; that is made explicit with the exact helper wording **"Changing this enters Explore."** (tooltip on every Order-n and non-cobalt palette item, plus one short inline line in the Controls panel; the false "Locked to n=16" tooltip and the 0.4 opacity are removed). Randomize gets the same treatment ("Randomize enters Explore"). Zoom ± and the wheel do **not** enter Explore, so they are shown as genuinely unavailable (`aria-disabled`, tooltip "Framing is locked in Reference") with the existing toast kept, and the wheel toast is throttled to once per few seconds. No behaviour change beyond that.
- **Risk:** low · **Files:** HTML, JS · **Engine:** none.

#### UX-10 · P1 · C/H · Area B, I, K · Interaction model is undiscoverable
- **Element:** Debug overlay footer line; README.
- **Problem:** The only place that explains "Click to perturb • Drag (Right-click/Shift) to Pan • Scroll to Zoom" is the footer of the **Debug overlay**. A new user in Explore is never told that hovering warps the art, clicking injects a shock, or how to pan. 12 of 14 shortcuts have no visible hint. The README key table is out of date. There are no touch gestures at all (UX-33).
- **Fix:** a small `?` button / key `?` opening a "Controls & shortcuts" sheet; move the gesture hint into the Explore status caption ("hover to perturb · click for shock · Shift-drag to pan"); update README.
- **Risk:** low · **Files:** HTML, JS, README · **Engine:** none.

#### UX-11 · P1 · C/H · Area N, I · Context-loss / recovery messaging is transient and leaves a dead-looking app
- **Element:** `onContextLost` / `onContextRestored` toasts. *Shots:* `r1`, `r2`, `r3`.
- **Problem:** "Graphics context lost — recovering…" is a 3-second toast. After it fades, the screen shows the **normal toolbar and the normal "REFERENCE MODE" pill over a blank canvas** (`r2`). If recovery fails after 3 retries, "Graphics recovery failed after several attempts." is *also* a 3-second toast, leaving a permanent blank screen with no explanation or action. The interrupted-export message is ~100 characters in a `white-space: nowrap` toast (UX-31).
- **Fix:** a persistent status banner (`role="alert"`, same style as `#graphics-error`) shown while `contextLost`, with states *Recovering…*, *Restored* (auto-dismiss), and *Failed — Reload* with a button. Keep the existing toast strings (tests assert on "please try again").
- **Risk:** low · **Files:** HTML, JS · **Engine:** none (display only; do not touch recovery logic).

#### UX-12 · P1 · C/H · Area D · Export doesn't set expectations (cost, output, difference)
- **Element:** toolbar export buttons; export modal. *Shots:* `x1`, `x2`.
- **Problem:**
  - **Two filled buttons compete.** "📷 Export 4K" and "💎 Reference Master" are the only filled buttons, but the active-state toggles (Auto, 16, Readout, Bloom: ON, Reference) use almost the same blue fill, so export doesn't read as *the* primary outcome and "Reference Master" reads as just another toggle.
  - **No cost information.** Neither tab shows an estimate of time, memory or file size. Reference Master states workload ("589,824 particles × 16 IFS steps = 9,437,184 deposits/pass") but not that it is far heavier than Standard.
  - **120 vs 240** is "120 — High / 240 — Maximum" with no explanation of what a pass is; there is no "recommended" marker even though 120 is the default.
  - **The word "Standard" means three things:** Quality *Standard*, *Standard Export*, and the *Standard (60 passes)* option.
  - **Three words for similar ideas:** toolbar "Quality", "Pre-Export Develop Passes", "Develop Quality". The Master's start button says "Develop Reference Master" while the other says "Download PNG".
  - Neither tab says which state will be exported (current Explore state vs canonical Reference) or the file name. Master does say "canonical… zero drift".
  - Jargon in the Master card: "Starts from black • Persistence = 1.0".
- **Fix (owner decision 6, wording only, no ETA):** one primary **Export** entry (Phase B); modal summary line ("Exports: current view · 3840×2160 · PNG"); a "Heavier" note plus plain sentence on Master ("Dedicated 4096×4096 render of the canonical artwork. Much slower than a standard export and independent of Live preview quality."); label 120 "Recommended"; unify the verbs and nouns; plain-language replacement for "Starts from black • Persistence = 1.0". **No ETA and no time or size estimates**; the progress UI stays *stage + percentage*.
- **Risk:** low · **Files:** HTML, JS · **Engine:** none.

#### UX-13 · P1 · I · Area I, E · Control state goes stale after preset load
- **Element:** `.quality-btn`, `.palette-select-btn`, `#btn-bloom`. *Measured after* `loadPresetObject`:
  - Preset with `tier: 'high'` → renderer mode `high`, but the **Quality group still highlights "Auto"**.
  - Palette dropdown highlights **Solar** while the renderer palette is **cobalt**.
  - Preset with `bloom: false` → button still reads **"Bloom: ON"** and active, while bloom is off.
- **Problem:** the buttons are updated only by their own click handlers, not by state changes from presets / mode reset. The UI lies. For Quality, which the brief calls out as critical, it is directly misleading.
- **Fix:** one `syncControlState()` that derives every toggle/segmented control from current renderer/math state, called after mode change, preset load and context restore.
- **Risk:** low · **Files:** JS · **Engine:** none.

### P2 — moderate friction

#### UX-14 · P2 · I · Area D, I · Export modal stays interactive while exporting
- *Shots:* `x3`, `x4`. Measured during a running Standard export:
  - clicking **✕** does nothing and says nothing;
  - clicking the **Reference Master tab** switches the visible panel and changes the Start button text to "Develop Reference Master" while a *Standard* export is running; pressing `E` flips it back;
  - **Start** becomes disabled but its label doesn't change to "Exporting…";
  - the secondary button reads "Cancel" both when it closes the dialog and when it aborts the export.
- **Fix:** while running: disable tabs/options/✕, relabel Cancel → "Cancel export", Start → "Exporting…", set `aria-busy`.
- **Risk:** low · **Files:** JS, HTML · **Engine:** none.

#### UX-15 · P2 · C/H · Area D, N · After cancel or failure the dialog shows stale, alarming progress and raw error text
- *Shots:* `x6_stale_status_after_cancel`, `f1_export_failure_1366`.
- **Problem:** after Cancel the label says "Export canceled." but the bar stays at its last value (98 %) and the Start button is enabled — it looks nearly done. The stale status persists across tab switches. Failures print the raw exception ("Export readback failed (WebGL error 1285): GL_OUT_OF_MEMORY …") in the same blue as normal status, with an empty 0 % bar, and then repeat it in the toast.
- **Fix (owner decision 6):** **clear stale progress immediately after cancel** (hide the bar, reset to 0 %, no leftover status; the toast and the re-enabled button say it was canceled). Failures: error styling (colour **and** a word/icon), a plain-language first line with the technical text secondary (`title`/small line), bar cleared; the toast carries a short form, not a duplicate of the full text.
- **Risk:** low · **Files:** JS, HTML · **Engine:** none.

#### UX-16 · P2 · C · Area D, K · Progress copy says "4K" for every Standard export
- **Element:** `renderer.js:1550, 1692, 1751`: "Allocating 4K GPU framebuffers (3840x2160)…", "Developing 4K passes (n/N)…", "Reading 4K framebuffer…" regardless of the selected size (FHD, Current View).
- **Fix (owner decision 4, approved):** in `renderer.js`, build the three strings from the actual `width`/`height` already in scope in `exportPNG`: e.g. `Allocating ${width}×${height} GPU framebuffers...`, `Developing ${width}×${height} passes (n/N)...`, `Reading ${width}×${height} framebuffer...`. **Copy only: no change to export logic, passes, buffers or ordering.** The Reference Master strings are already accurate and are left alone. No test asserts these strings (checked by grep).
- **Risk:** very low · **Files:** `renderer.js` (3 string literals) · **Engine:** none (reporting text only).

#### UX-17 · P2 · C/I · Area D · Success is brief and unspecific
- *Code-verified:* on success the dialog **auto-closes after 700 ms**; success is a 3-second toast ("Successfully exported 3840×2160 PNG!"). No file name, no size, no "saved to your downloads" and no way to re-open the result. After a long Master render, the confirmation is easy to miss.
- **Fix (owner decision 6):** **the success state stays open until dismissed.** Show the filename and the output resolution (e.g. "Saved `mobius-reference-master-4096.png` · 4096×4096") with a single **Done** action (✕ and Esc also close). The 700 ms auto-close is removed; the toast is kept. No "Export another" button.
- **Risk:** low · **Files:** JS, HTML · **Engine:** none. *Test impact:* `test_issue14_transactions` asserts that reopening the modal cancels the completion timer, and other tests expect the modal to close after success. Update them in the same commit (§8 C3).

#### UX-18 · P2 · C/R · Area B, K · The mode pill is long, jargon-heavy, and clips on narrow screens
- Text: "REFERENCE MODE • Exact Simone Conradi 2026 Artwork (Formula Protected • Drift Paused)" and "EXPLORE MODE • Interactive Sandbox (Pointer Perturbations & Sliders Active)". "Formula Protected" and "Pointer Perturbations" mean little to a newcomer; at 390 px the 515-px pill is clipped on both sides (`x = -62`).
- **Fix:** shorten and teach: *Reference · the published artwork, locked* / *Explore · change the mathematics — hover to bend, click to shock*. Allow wrap or truncate with ellipsis at small widths. Keep the mode name explicit and the dot colours.
- **Risk:** low · **Files:** JS (`updateModeUI` text), HTML (CSS) · **Engine:** none. *Test constraint:* `test_issue13_startup` checks the pill text is *not* `REFERENCE MODE` after fatal init.

#### UX-19 · P2 · L/I · Area A, B · Randomize split-button and its menu
- *Shots:* `b1_randomize_menu`, `m5`.
- **Problems:** the ▾ hit target is **14×22 px**; the dropdown is **partly covered by the mode pill** (the second item, "Subtle", is clipped under it) and sits over the Quality row; the tooltip says "Randomize Organism (Mode 3 • Shortcut: 3)" — "Mode 3" is stale jargon (only two modes exist in the UI); clicking 🎲 in Reference silently becomes Explore (the toast says "Randomized [style]" but not that the mode changed).
- **Fix:** raise the dropdown's stacking above the pill; ≥ 24 px target; copy "Randomize (3)"; toast "Randomized … · switched to Explore".
- **Risk:** low · **Files:** HTML, JS · **Engine:** none.

#### UX-20 · P2 · I/C · Area E · Brute Force is one unguarded click away
- *Shot:* `q1_bruteforce_selected`. Adjacent to Extreme; selecting it gives no toast, no warning, and the only warning ("BRUTE FORCE • 589,824 × 16 • 9,437,184 deposits/frame") is inside the Debug overlay. Key `X` toggles it with no UI feedback other than the button highlight. On integrated GPUs this likely stalls the preview or triggers context loss — **I could not test this on real hardware; verify before deciding severity.**
- **Fix (owner decision 7):** **inline warning only.** When Brute Force is the selected tier (button, key `X`, or preset), show the line **"Maximum live GPU load — high-end hardware recommended."** beneath the quality row and as the button tooltip. **No confirmation dialog**; revisit only if physical-hardware testing shows severe lockups. The tier itself is not removed or changed.
- **Risk:** low · **Files:** HTML, JS · **Engine:** none.

#### UX-21 · P2 · I · Area B, I · Hover perturbation is window-wide in Explore
- `window` `pointermove` → `math.setPointer` (`app.js:526-531`). Moving the cursor toward the toolbar bends the artwork the whole way; there is no way to turn it off short of Reference. The pill mentions "Pointer Perturbations", but not how to stop them.
- **Fix (owner decision 3, as amended):** **canvas = interactive surface, UI = safe surface.** Hover perturbation (`math.setPointer`) runs only when the pointer is over the canvas; moving across the toolbar, panels, modals or the corner restore button never *adds* perturbation. **On canvas `pointerleave`, the pointer target is set back to neutral** (`math.setPointer(0, 0)`, Explore only), and the **existing interpolation relaxes the current influence naturally**; nothing is hard-snapped and the retained influence does not linger. **No Pointer Influence toggle.** Click shock, wheel zoom and the pan drag are already canvas-originated and unchanged. Built in **Phase A, commit A9**.
- **Risk:** low · **Files:** `app.js` (`pointermove` hover branch + one `pointerleave` listener on the canvas) · **Engine:** none. `math.setPointer`, its `0.22` scale, and the damping in `math.update` are not modified; only *when `setPointer` is called* changes.

#### UX-22 · P2 · H/C · Area G · Coefficient controls need context
- *Shot:* `a2`, `v_*_drawer_debug`.
- **Problems:**
  - Rows read "ΔRe(a)", "ΔIm(b)", "ΔRe(c)", "ΔIm(d)" under "Live Mobius Perturbation Controls" — math-fluent but unexplained, and only **4 of the 8 real/imaginary parts** are exposed (the other four are not reachable at all).
  - All four share ±0.5 / 0.01 steps although the bases differ in scale (|a| ≈ 0.8, |c| ≈ 6.4), so the same slider travel means very different things.
  - Sliders show the **offset** only; the **base** and **effective** values are visible only in the bottom-left readout, which can be toggled off, and which changes under drift.
  - No numeric entry; no per-row reset.
  - **Three different "resets":** toolbar **Reset** (title says "Reset framing and view" but in Explore it also zeroes offsets/time/shock and clears accumulation), **1×** (zoom/centre only), **Reset Coefficients** (offsets only).
- **Fix (owner decision 8):** **keep the four sliders as they are**: no eight-component editor, no numeric entry, no per-row reset in this pass. Only context is added: `base → effective` shown next to each slider, a one-line explainer ("Offsets added to the base coefficients. Edits apply live."), and consistent reset names ("Reset view", "Reset offsets"). A fuller numeric editor may be considered later as an explicitly advanced feature.
- **Risk:** low (UI) · **Files:** HTML, JS · **Engine:** none (no change to `setCoefficientOffset`).

#### UX-23 · P2 · A/L · Area A, L · Equation readout occupies fixed space on short screens
- 228×160 px at bottom-left at all sizes. At 1366×768 it spans y 584–744 (21 % of height); at 844×390 it occupies ~40 % of the height. It is also the one panel with no collapse affordance except the "Readout" toolbar toggle (which is easy to miss).
- **Fix:** compact one-line state on short viewports (expand on click); keep the equation.
- **Risk:** low · **Files:** HTML, JS · **Engine:** none.

#### UX-24 · P2 · L · Area F, H · Presets modal layout defects
- *Shots:* `p2_presets_long_dup_corrupt`, `p3_saved_toast`.
- **Problems:** the **curated grid overflows the dialog** — the right-hand column of cards extends past the dialog's right border (cards end at x = 1009, dialog at 953 at 1366 wide) because button `white-space: nowrap` defeats the `1fr 1fr` grid; "My Saved Presets" is limited to **120 px (3 rows)** with nothing hinting that it scrolls; the "Reference Artwork" curated card is mixed in with Explore presets without a mode tag.
- **Fix (approved: preset-grid overflow):** `min-width:0; white-space:normal` on cards so the grid stays inside the dialog; list `max-height` scaled to the viewport with a visible scroll affordance. The Reference/Explore tag on cards is optional polish (Phase C), not required.
- **Risk:** low · **Files:** HTML (CSS), JS (card markup) · **Engine:** none.

#### UX-25 · P2 · C/I · Area F · Preset save semantics are surprising
- **"Save & Download"** does two things (stores in this browser **and** downloads a `.mobius.json`); there is no "save in browser only".
- **"Copy JSON" ignores the name field** (typed "TypedName" → copied name "Custom Mobius Organism").
- The list is **silently capped at 20** (21st save drops the oldest; verified: kept `…P18`, dropped `P19`).
- If `localStorage` fails the toast still says "Saved preset" *(code-verified: failure is only a `console.warn`)*.
- Duplicate names allowed (two "Duplicate" rows) and no `maxlength`.
- **Fix (scoped to approved "clearer preset failure feedback"):** show an **error toast if browser storage fails** instead of "Saved"; **tell the user when the 20-preset limit drops the oldest**. **Not in this pass** (not approved, would change preset behaviour): splitting Save from Download, making Copy JSON use the name, duplicate-name handling, `maxlength`. They stay listed here for a later decision.
- **Risk:** low · **Files:** JS, HTML · **Engine:** none. *Note:* preserve existing preset validation and the delete label `✕` (commit `16ebf39`).

#### UX-26 · P2 · I/C · Area F · Preset failures are silent; delete is instant
- Loading an invalid stored preset: `loadPresetObject` throws, there is **no try/catch in the click handlers** (only in import), so **nothing happens — no toast** (measured: uncaught `Invalid preset field: symmetry.`, modal stays open). Deleting a preset has no confirmation or undo.
- **Fix (approved: preset failure feedback):** wrap the curated/user Load clicks with the same try/catch + toast the import path already uses, so an invalid preset reports "Unable to load preset: …". `validatePreset` is not touched. **Delete confirmation/undo is not in this pass** (not approved).
- **Risk:** low · **Files:** JS · **Engine:** none (validation rules untouched).

#### UX-27 · P2 · C/I · Area E, F · Presets silently change live Quality, palette and camera
- Curated presets carry `tier: 'high'` / `'ultra'` / `'standard'` and `loadPresetObject` applies it (`adaptive.setMode`). A laptop user clicking "Deep Specimen" is moved to **Ultra** (manual), leaving Auto, and the Quality row doesn't even show it (UX-13).
- **Fix (UI only):** the highlighting is fixed by `syncControlState()` (Phase A, UX-13). Whether presets *should* carry tiers is a product decision and is **not changed**. An optional one-clause addition to the existing load toast ("… · Quality: Ultra") is Phase C copy polish; no new action or toggle.
- **Risk:** low · **Files:** JS · **Engine:** none.

#### UX-28 · P2 · I · Area J, F · "Import Preset JSON" is not keyboard-reachable
- It is a `<label>` wrapping a `display:none` file input; the label has `tabindex = -1` (measured). Keyboard users can't import.
- **Fix:** make it a real `<button>` that triggers `input.click()` (or visually-hidden input instead of `display:none`).
- **Risk:** low · **Files:** HTML (+ 1 JS line) · **Engine:** none.

#### UX-29 · P2 · P/C · Area J, A · Contrast and type size
- Measured contrast (vs `#050a16`): `.control-label` **3.86:1** at 9.5 px; `.dropdown-header` **4.29:1** at 8.5 px; `.modal-section-title` / `.param-label` **4.29:1** at 10–11 px. These fail 4.5:1 for small text, and they sit on translucent glass over bright art, so reality is lower. **131 text nodes are < 11 px** (smallest 8.5 px).
- **Fix:** raise label colour to ≥ 4.5:1 (e.g. `#6f8fb8`-ish), 11 px minimum for text people must read; keep tiny sizes only for purely decorative captions.
- **Risk:** very low · **Files:** HTML (CSS) · **Engine:** none.

#### UX-30 · P2 · R/I · Area J, M · Small hit targets
- Of 33 visible toolbar controls, 13 are 22 px tall; Order-n buttons are 20×24; ▾ is 14×22; zoom buttons 21×22. WCAG 2.2 target-size minimum is 24×24 CSS px. Fine on a mouse, poor on a trackpad/touch.
- **Fix:** ≥ 24 px height and width (padding only), ≥ 36–44 px in the touch layout.
- **Risk:** low · **Files:** HTML (CSS) · **Engine:** none.

#### UX-31 · P2 · L/C · Area N, J, H · Toast is nowrap, single-slot and not announced
- `white-space: nowrap`, no max-width. The 100-character interruption message renders **512 px wide at 390 px viewport → `x = -61`, clipped on both sides** (`m1_toast_overflow_390`). Fixed 3 s regardless of length. One slot: a new toast overwrites the previous (e.g. "Export canceled" can be replaced by a mode toast). No `role="status"` / `aria-live`.
- **Fix:** `max-width: min(92vw, 520px); white-space: normal`, duration scaled by length (≈ 3 s + 40 ms/char), `role="status"`, and a `variant` (info/error) class.
- **Risk:** low · **Files:** HTML, JS · **Engine:** none. *Test constraint:* keep `showToast(message)` signature and `#toast-banner`.

#### UX-32 · P2 · H/L · Area C, H · Debug overlay mixes developer and user concerns, and collides with the drawer
- 483 px wide, 17 rows at 10.5 px mono, `top: 68px`. At 1366/1280 it overlaps the coefficient drawer by 14/57 px (`v_1366x768_drawer_debug`, `v_1280x720_drawer_debug`); at 1024 it covers the middle of the screen, and its "Engine" title is cut off by the drawer. It is toggled by a button in the same row and style as user controls, directly beside Hide.
- **Fix:** move to a "Developer" section (or a corner dock), default off, never overlapping other panels; keep every readout.
- **Risk:** low · **Files:** HTML, JS · **Engine:** none (do not change profiler). *Note:* `?debug`/`?profile` URL params keep working.

#### UX-33 · P2 · R · Area M · Narrow / touch layout
- *Shots:* `v_390x844_landing`, `m2`, `m6`. At 390 px: toolbar 178 px tall (+ pill = 25 % of the screen); the pill is clipped; the drawer's `min-width: 380px` barely fits (5–385 px of 390); at 844×390 the chrome covers ~47 % of the height and the artwork is visible only as a sliver. **There are no touch/pinch handlers**: pan needs right-click/Shift/Alt, zoom needs the wheel or the ± buttons (README advertises "pinch"). See §6 M for the classification.
- **Risk:** medium · **Files:** HTML, JS · **Engine:** none (no gesture work proposed in this pass).

#### UX-34 · P2 · R/I · Area J, M · Viewport meta blocks page zoom
- `user-scalable=no` disables pinch-zoom of the **page** for low-vision users (WCAG 1.4.4). The canvas does not use pinch anyway.
- **Fix:** drop `user-scalable=no` (keep `touch-action: none` on the canvas to prevent browser gestures there).
- **Risk:** very low · **Files:** HTML · **Engine:** none.

#### UX-35 · P2 · C/H · Area N, I · Development and Auto changes are invisible
- After load, **Reset**, switching modes, or toggling Pause, the accumulation is cleared and the artwork rebuilds from black over seconds. Nothing says "developing" vs "settled" (the profiler's "Accumulation Age" exists but is hidden in Debug). Auto's promotion/demotion events are logged only to Debug/console. During Export the dialog is clear, but the last steps (`Reading… 95 %`, `Encoding PNG… 98 %`, `Encoding 4096×4096 PNG… 99 %`) sit on a fixed percentage and may *look* hung on real hardware.
- **Fix (not scheduled this pass):** a small "developing… / settled" word and indeterminate styling for the encode phases would help, but both add UI beyond the approved scope; they are parked for a later decision. The approved export-dialog work (C3) keeps *stage + percentage*.
- **Risk:** low · **Files:** JS, HTML · **Engine:** none (read-only).

### P3 — polish

| ID | Cat | Area | Issue and fix | Files |
|---|---|---|---|---|
| UX-36 | C | K | **Palette naming is inconsistent for one palette:** menu "Cobalt (Conradi Reference)", toolbar "Palette: Simone" (first word of "Simone Conradi (Cobalt Reference)"), pill "Simone Conradi". Toolbar label truncates to first word ("Silver", "Solar"). Use one name per palette. | JS |
| UX-37 | C | K | **Misleading tooltips:** Zoom In "(+)" / Out "(−)" have no key bindings; Reset says "Reset framing and view" but resets more in Explore; Quality tooltips carry "75k x 8" jargon; Randomize says "Mode 3". | HTML |
| UX-38 | P | A | **Colour emoji (🎲 📷 💎 💾 📁)** render differently per OS, and the Windows colour set clashes with the cold-blue palette (see any toolbar shot). Replace with small monochrome SVG/line glyphs, or drop. | HTML |
| UX-39 | C | K | **Capitalisation/format drift:** `STANDARD EXPORT` (caps) vs `Reference Master`; `Bloom: ON` vs `Drift: Off`; `Debug [D]`, `Hide [H]` vs no hint elsewhere; `REFERENCE MODE` caps pill. Pick sentence case + one `ON/Off` style. | HTML, JS |
| UX-40 | L | D | **Export dialog height jumps** when changing tabs (the whole dialog re-centres by ~25 px; compare `x1` vs `x2`); the progress area pushes buttons down. Reserve the progress row or fix a min-height. | HTML |
| UX-41 | C | K | **README is out of date** (keys, "pinch", "N / Shift+N", "1–6 morphology presets") and doesn't describe Reference/Explore/Master. | README |
| UX-42 | P | A | **1920+ screens:** the toolbar reads small (10.5 px) and the bar is a thin 2-row strip; fine, but no scaling. Optional `clamp()` type scale. | HTML |
| UX-43 | L | H | **Preset-modal/export-modal width** (480/540 px) is fine on laptops; only note: at ≤ 1024 the export dialog is 90 % wide with long unbroken workload line wrapping awkwardly (`m3`). | HTML |

---

## 5. Prioritized shortlist

| Priority | IDs | One-line summary |
|---|---|---|
| **P0** | UX-01 | Coefficient drawer hidden under toolbar/pill; ΔRe(a) unreachable at ≤ 1440 wide |
| **P0** | UX-02 | Hide UI has no visible/touch way back |
| **P1** | UX-03 | Toolbar capped at 50 % viewport width, wraps to 3–6 rows, orphans "QUALITY" |
| **P1** | UX-04 | No keyboard focus ring anywhere |
| **P1** | UX-05 | Space hijacked: focused buttons can't be activated with Space |
| **P1** | UX-06 | Modals lack focus management, Esc/backdrop, ARIA; shortcuts fire behind them |
| **P1** | UX-07 | Returning to Reference silently discards the Explore session |
| **P1** | UX-08 | Quality never says "live preview only"; Auto's chosen tier is invisible |
| **P1** | UX-09 | "Locked" controls look enabled and switch mode / inconsistent lock behaviour |
| **P1** | UX-10 | Gestures and shortcuts undiscoverable (gesture help lives in Debug) |
| **P1** | UX-11 | Context-loss / failed-recovery messaging is a 3-second toast |
| **P1** | UX-12 | Export doesn't convey output, cost or difference (Standard vs Master) |
| **P1** | UX-13 | Quality / Palette / Bloom controls go stale after preset load |
| **P2** | UX-14 – UX-35 | Export dialog behaviour, error/cancel states, copy, presets, coefficients, contrast, targets, toast, debug overlay, mobile (22 items; see §4) |
| **P3** | UX-36 – UX-43 | Naming, tooltips, emoji, capitalisation, README, small layout polish |

**Phase mapping (see §8).** Phase A (no restructure): UX-01, 02, 03 (interim), 04, 05, 06, 09, 11, 13, 16, 21, 24–26 (overflow/feedback), 28, 31 (wrapping). Phase B (restructure): UX-03, 07, 08, 10, 18, 20, 22, 23, 32. Phase C (polish): UX-12, 14, 15, 17, 29, 30, 33, 34, 36, 37, 39, 41, 43. Not scheduled this pass (owner decisions, §9.2): UX-27 beyond highlighting, UX-25/26 beyond feedback, UX-38, UX-40 beyond the dialog height fix, UX-35 beyond what the dialog already shows, and ETA-related ideas.

---

## 6. Findings by audit category

**A. Visual hierarchy.** The artwork is the focus when the toolbar is closed to it, but at laptop sizes the toolbar and pill take 14–24 % of the height and sit over the Reference's top petals (UX-03). Everything inside the toolbar is the same weight: 44 buttons in one pill-in-pill container, with active/toggle states (`Auto`, `16`, `Readout`, `Bloom: ON`) as loud as the primary actions (UX-12). Debug and Hide sit in the same row as Export (UX-32). Excess borders/pill nesting (pill → group → pill → button) add noise; reduce nesting rather than add chrome.

**B. Mode clarity.** Reference/Explore is clearly two-state and colour + text coded, which is good. Weaknesses: tiny 10 px switch; a long jargon pill (UX-18); no helper copy about what *Explore changes* (it changes the mathematics; hovering bends coefficients, UX-10/21); Randomize implicitly changes mode (UX-19); controls that look locked but change mode (UX-09); returning to Reference destroys work (UX-07). **Does the UI imply Reference is editable?** Mostly no (sliders disabled, Drift: Off), except the dimmed-but-live Order n and palette (UX-09). I recommend stronger grouping of the mode switch with a one-line helper under it, **not** renaming "Reference"/"Explore".

**C. Control density / information architecture.** ~40 % of always-visible controls are advanced or debug (§2.2). Proposed hierarchy (§7): *primary* (mode, randomize, presets, export) always visible; *common* (palette, order, zoom, drift, reset) in a docked "Controls" panel; *advanced* (quality, bloom, readout) lower in that panel; *debug* (raw, debug overlay) in a collapsed "Developer" group. **No capability is removed.** Gain has no UI today and none is proposed.

**D. Export UX.** See UX-12, 14, 15, 16, 17. Summary: the machinery is sound (state preservation, display-hold, cancellation) but the dialog does not communicate cost, output, or difference; it stays interactive while running; and success/failure/cancel states are weak. Reference Master's *difference* is explained well in prose but sits beside jargon; 4096×4096 *is* clearly stated; the 120-vs-240 choice is not explained; there is a default but no "recommended".

**E. Quality UX.** Names are ordinal and readable (Low → Standard → High → Ultra → Extreme → Brute Force); I'd keep them. "Potato" isn't a user-visible button (only reachable through Auto, shown only in Debug). The issue is not the names but **what the row governs** (UX-08), the **number of equal choices** (7 in a row), the **invisibility of Auto's choice**, and **stale highlighting** (UX-13). Helper text recommended: *"Live preview only — exports use their own settings."* (Accurate: Standard export uses 589,824×12 and Master 589,824×16, independent of the tier.)

**F. Presets.** Concept is understandable ("Curated", "Save", "My Saved") but the internal model leaks: "Attractor Preset Library", "organism", "Save & Download", JSON import/copy (UX-24–28). Failures are silent (UX-26). The curated preset also changes Quality (UX-27).

**G. Coefficient / math UX.** See UX-22 and UX-01. The mathematics is correctly presented in the readout (`z → ω_k (az + b) / (cz + d)`, complex numbers `-0.755 + 0.330i`, 3 dp). Gaps: only four components are editable and not explained; offset vs base vs effective is not shown at the control.

**H. Responsive / laptop.** 1366×768 and 1280×720 are the problem sizes: drawer occluded (UX-01), 17–21 % chrome, debug overlap, readout 21 %. 1920×1080 is fine. 1024×768 is poor. Modals fit at every size tested.

**I. Interaction.** Focus (UX-04), Space (UX-05), modals (UX-06), stale state (UX-13), mid-export interactivity (UX-14), no `+`/`−` keys though tooltips say so (UX-37), no feedback on Brute Force (UX-20). Good: hover/active styles exist, disabled controls are mostly consistent, disabled Pause uses an informative "Drift: Off" label.

**J. Accessibility basics.** Actual failures: no focus indicator (UX-04); Space handling (UX-05); modal semantics, Esc, focus (UX-06); import not keyboard-reachable (UX-28); small-text contrast (UX-29); targets < 24 px (UX-30); toast/status not announced (UX-31); `user-scalable=no` (UX-34). Not found: colour-only status (modes carry text; Pause has text), 0 `aria-label`s but visible text on every button except the `✕` close buttons (which need `aria-label="Close"`).

**K. Copy / microcopy.** Jargon to soften (not to flatten): "Formula Protected", "Pointer Perturbations", "Persistence = 1.0", "Starts from black", "Develop passes", "Deep Caustics", "deposits/frame", "Mode 3", "Organism Name". Inconsistent: "Standard" ×3, "Quality"/"Develop Quality"/"Develop passes", palette names, capitalisation (UX-36–39). Misleading: "4K" in progress (UX-16), tooltips (UX-37), "Locked" (UX-09). Keep the lab voice: *"Develop"*, *"Caustics"* and the maths notation are an asset; the fix is to pair them with one plain phrase.

**L. Artwork-first verdict.** At ≥ 1920×1080 the current interface does **not** meaningfully interfere. At 1366×768 and below it genuinely does: the toolbar + pill cover the top 17–24 % of the screen where the Reference rosette's petals live, the readout takes the bottom-left, and any open panel (drawer/debug) stacks on top of the art. The conclusion is that a layout change **is justified** for laptops, but it should be *subtractive*: collapse advanced controls behind one toggle, keep one slim bar, keep `H` hide-all (made recoverable). Full-screen artwork mode already exists (Hide) once UX-02 is fixed. No new overlays are needed beyond a docked, closable panel.

**M. Mobile / touch feasibility.** Classification:

| Item | Class |
|---|---|
| Hide UI with no way back (UX-02) | **Must fix** |
| Toolbar 25 % of screen, pill/toast clipped (UX-33, 18, 31) | **Must fix** |
| Targets < 24 px (UX-30) | **Must fix** (≥ 36 px in touch layout) |
| `user-scalable=no` (UX-34) | **Must fix** (trivial) |
| Modals at narrow widths | OK today (no change needed) |
| Drawer 380 px min width | Must fix as part of drawer rework |
| No pinch/pan gestures | **Reasonable limitation** (needs input/engine-adjacent work; out of scope; ± buttons remain) |
| Hover perturbation in Explore | Desktop-first acceptable (no hover on touch; tap = shock) |
| Right-click/Shift pan | Desktop-first acceptable |
| Reference Master on mobile GPUs | Reasonable limitation (errors are surfaced; add plain-language failure copy, UX-15) |
| Debug overlay, shortcuts | Desktop-first acceptable |

**N. Performance perception.** Export dialog progress is good for the develop phase (`Developing Reference Master (n / N)`) and, per owner decision 6, stage + percentage is judged sufficient (no ETA this pass); the final phases do sit on a fixed percentage (UX-35). Reference development and Auto promotion are invisible (UX-35, UX-08). Context loss is a transient toast (UX-11). During export the frozen frame (display-hold) prevents a black flash — a good call. Cancel is visible and works at every stage tested (including 98/99 %), but the label does not change (UX-14).

---

## 7. Phase 2 — proposed interface structure (revised for owner decisions)

**Principle:** keep the existing visual language (dark glass, cold blue/violet, mono maths) and make the layout **subtractive and artwork-first**. No card grids, no dashboard, no new colour system. Every existing element id is kept (§8 constraints). This structure is built in **Phase B**, after the Phase A defect fixes are verified.

### 7.1 Top-level layout (≥ 1280 px)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│     ┌───────────────────────────────────────────────────────────────────┐    │
│     │ [● Reference │ ○ Explore]  🎲 Randomize ▾ │ Presets │ Export ▾ │ Controls │ ? │   ← ONE row, ~40 px, never wraps
│     └───────────────────────────────────────────────────────────────────┘    │
│        Reference · the published artwork, locked                             │   ← one-line caption (replaces the long pill)
│                                                                              │
│                                                          ┌────────────────┐  │
│                                                          │ Controls     ✕ │  │   ← docked right panel, closed by default,
│                  A R T W O R K                           │ ▾ View         │  │      ~300 px; opens with Controls or P
│               (full bleed, centred)                      │ ▾ Mathematics  │  │
│                                                          │ ▾ Live preview │  │
│  z → ω_k (az+b)/(cz+d) · n=16 ▸                          │   quality      │  │
│  (compact chip on short screens; click for a,b,c,d)      │ ▸ Developer    │  │   ← collapsed by default
└──────────────────────────────────────────────────────────┴────────────────┴──┘
```

### 7.2 Component decisions

| Area | Proposal | Ids kept |
|---|---|---|
| **Mode switch** | Left end of the bar, segmented, label ≥ 12 px, dots and colours unchanged. Caption below: *Reference · the published artwork, locked* / *Explore · change the mathematics — hover to bend, click to shock, Shift-drag to pan*. | `btn-mode-reference/explore`, `mode-status-pill` (becomes the caption) |
| **Primary bar** | Mode · Randomize ▾ · Presets · **Export** (the only filled button) · Controls · `?` help. Five groups instead of 33 controls. | `btn-randomize-action/toggle`, `btn-preset-trigger`, `btn-export-trigger`, `btn-coeff` (opens the panel at Mathematics) |
| **Randomize** | Stays in the bar. Tooltip **"Randomize enters Explore"** (decision 5). Menu opens above the caption (no stacking clash). | `randomize-menu`, `.rnd-style-btn` |
| **Export entry** | One **Export ▾** split button: *Image…* and *Reference Master…* (the latter keeps `btn-refmaster-trigger`). No second filled button. | `btn-export-trigger`, `btn-refmaster-trigger` |
| **Controls panel** | Right-docked, closed by default, closes with ✕ / Esc, remembers its last open section for the session. At < 900 px it is a bottom sheet (Phase C). | new container; all moved controls keep ids |
| ↳ **View** | Palette list (non-cobalt items carry **"Changing this enters Explore."** while in Reference), Zoom − 1× +, Bloom, Readout toggle, Reset view, Hide controls [H]. | `btn-palette-toggle`, `palette-select-btn`, `btn-zoom-*`, `btn-bloom`, `btn-readout`, `btn-reset`, `btn-hide` |
| ↳ **Mathematics** | **Order n** chips (always enabled; in Reference a single line **"Changing this enters Explore."**), **Drift** (existing disabled "Drift: Off" in Reference), the **four existing coefficient sliders** unchanged, each row showing `base → effective`; existing 🔒 lock notice in Reference; **Reset offsets**; **Start fresh** (Explore only). | `sym-btn`, `btn-pause`, `slider-*`, `lbl-*`, `btn-reset-coeffs`, `coeff-lock-notice` |
| ↳ **Live preview quality** | Heading **"Live preview quality"**, helper **"Preview only — exports use their own settings."**. The existing seven buttons, same names, same order. While Auto is active: read-only **"Current tier: Standard"**. When Brute Force is active: inline **"Maximum live GPU load — high-end hardware recommended."** | `quality-btn` + `data-tier` |
| ↳ **Developer** (collapsed) | Raw trajectories, Debug overlay toggle (overlay docks beside/under the panel and never overlaps it), link to the help sheet. `?debug` / `?profile` still open the overlay. | `btn-raw`, `btn-debug`, `debug-overlay`, `dbg-*` |
| **Presets** | Stays a modal. Curated cards wrap inside the dialog; failures surface as toasts. (No Save/Download split, no undo: out of scope.) | `preset-modal`, `curated-presets-list`, `user-presets-list`, `.load/.del-user-preset` |
| **Equation readout** | Bottom-left, unchanged content; collapses to a one-line chip on viewports < 800 px high or while the panel is open; click expands. | `equation-readout`, `val-*` |
| **Help (outside Debug)** | `?` in the bar (and key `?`) opens a small "Controls & shortcuts" sheet: the 14 shortcuts plus the gestures (hover to bend, click to shock, Shift/right-drag to pan, wheel to zoom). | new, null-guarded |
| **Hide / restore** | `H` or the panel's Hide control hides everything; a faint corner **show-controls button** (and a 4-second key hint) restores. Built in Phase A. | `hint-unhide` + new corner button |
| **Banner / toast** | Persistent `role="alert"` banner for context loss (Phase A); toast wraps and is announced (`role="status"`). | `toast-banner`, `showToast(msg)` |

### 7.3 Export dialog (stage + percentage only — no ETA)

```
┌ Export image ───────────────────────────────── ✕ ┐     ✕ / Esc blocked while running
│ [ Image | Reference Master ]                       │     tabs disabled while running
│ Exports: your current view · 3840×2160 · PNG       │     one-line summary of what will be produced
│ Resolution   (•) 3840×2160  ( ) 1920×1080  ( ) Current view │
│ Passes       ( ) Fast 30  (•) Standard 60  ( ) Deep 120     │
│                                                    │
│  Reference Master tab:                             │
│  Heavier. Dedicated 4096×4096 render of the        │
│  canonical artwork. Much slower than a standard    │
│  export; unaffected by Live preview quality.       │
│  Passes   (•) 120 · Recommended   ( ) 240 · Maximum │
│                                                    │
│  Developing 1920×1080 passes (24/60)…        41 %  │     running: stage + %, nothing else
│  ▓▓▓▓▓▓▓░░░░░░░░                                   │
│                    [ Cancel export ] [ Exporting… ]│
└────────────────────────────────────────────────────┘
 Cancel  → progress area cleared immediately; toast "Export canceled."; buttons re-enabled.
 Failure → "Export failed — <plain sentence>" in error style (colour + word); bar cleared; technical text secondary.
 Success → stays open: "Saved mobius-reference-master-4096.png · 4096×4096"   [ Done ]   (✕ and Esc also close)
```

### 7.4 Responsive behaviour

| Width | Behaviour |
|---|---|
| ≥ 1280 | Bar + docked right panel over the artwork's side margin; art stays centred. |
| 900–1279 | Same bar; panel opens as an overlay; readout compact if height < 800. |
| < 900 or touch | Bar becomes a bottom bar; panel becomes a bottom sheet; targets ≥ 40 px; caption truncates; modals full width; corner restore button always reachable. No pinch/pan added (reasonable limitation). |

### 7.5 Not part of this structure
No ETA, no eight-component editor, no pointer-influence toggle, no tier regrouping, no confirmation dialogs, no new colours, no new animation.

---

## 8. Phase 3 — implementation plan (revised)

**Nothing below is implemented.** Work proceeds in three phases with a verified checkpoint after each; I start a phase only when you say so. Each commit is small, independently reviewable, and leaves `main` working.

### 8.0 Rules that apply to every commit

**Protected — must not change (verified by a diff guard at each checkpoint):**
`math.js`, `adaptive.js`, `profiler.js`, `preset_validation.js` — zero diff. `renderer.js` — only the three progress-string literals in commit A6. Canonical Reference math, Reference rendering, live exposure budgets, export algorithms, Reference Master quality, WebGL recovery logic, randomizer ranges, preset validation, cancellation, background export, particle isolation: untouched. UI code only *reads* engine state or calls the same public setters the app already calls.

**Test constraints (found by reading the harnesses):**
- Keep ids/classes the tests read: `btn-mode-reference/explore`, `mode-status-pill`, `btn-pause`, `btn-zoom-in`, `btn-export-start/cancel`, `export-status-pct`, `export-display-hold`, `lbl-a-re`, `val-a`, `val-n`, `user-presets-list`, `.load-user-preset`, `.del-user-preset` (label `✕`, commit `16ebf39`), `toast-banner`, `graphics-error`.
- Test pages build **only a subset of the DOM**. Every new `app.js` reference to a new element must be null-guarded (`?.`), like the existing code.
- Keep `showToast(message[, duration])` and the strings tests assert ("please try again", "large"/"1 MB").
- Known tests that must be updated deliberately (not by accident): `test_issue14_transactions` (completion timer, C3) and any test expecting the export dialog to auto-close.

**Verification at every commit:** run the existing hardening suites (`test_modes_and_exports`, `test_export_failure_and_edge_cases`, `test_export_display_hold`, `test_issue1/5/6/9/10/11/13/15`) and compare with `HARDENING_REPORT.md`. These were not run for this audit (Playwright is not installed on this machine), so the first task of Phase A is to confirm they run here and record a **baseline** before any edit. Layout assertions use the same headless-Edge/puppeteer approach as this audit, run from outside the repo (adding a `package.json` and the script to the repo only if you want that).

---

### Phase A — fix defects without restructuring the interface

| # | Commit | Fixes | Files / exact controls | Regression risk | Screenshots / tests |
|---|---|---|---|---|---|
| **A1** | `fix(ui): toolbar width cap and overlay clearance` | UX-03 (interim), UX-01, UX-32 (clearance only) | `index.html` CSS: `#top-bar-container` → `left:0; right:0; margin:0 auto; width:max-content; max-width:98vw; transform:none`. `app.js`: a `ResizeObserver` on the top container writes `--chrome-h`; `#coeff-drawer` and `#debug-overlay` use `top: calc(var(--chrome-h) + 8px)`. | Low. The drawer/Debug overlay can still overlap *each other* at ≤ 1366 (resolved in B2 by moving them into the panel). | Hit-test `slider-a-re` and `btn-reset-coeffs` at 1920/1440/1366/1280/1024/390; screenshots equivalent to `a2`, `v_1366x768_drawer_debug`; confirm "QUALITY" label no longer wraps away from its buttons at 1440/1366. |
| **A2** | `fix(ui): visible restore path after Hide` | UX-02 | `index.html`: `#hint-unhide.visible{display:block}` (fade after ~4 s); new corner button `#btn-show-ui` (outside `#ui-container`, only shown while hidden). `app.js`: `toggleUI()` shows/hides it; click/tap restores. | Low | Hide → restore by key `H`, by click, by tap emulation; screenshot equivalent to `g1`. |
| **A3** | `fix(a11y): keyboard focus, Space and dialog behaviour` | UX-04, UX-05, UX-06, UX-28 | `index.html`: `:focus-visible` ring (buttons, sliders, tabs, import control); `role="dialog" aria-modal="true" aria-labelledby` on both modals; `aria-label="Close"` on ✕; import becomes a real `<button>` that opens the file input. `app.js` keydown: Space is not intercepted when the target is a button/link/select/input; **all shortcuts suspended while a modal is open**; **Esc closes the Presets and Export dialogs** (ignored while an export is running; the visible Cancel remains the way to stop); focus moves into the dialog on open, is trapped, and returns to the trigger on close. | Medium (many small edits; touches the keydown handler and the export input blocker's interaction with the modal). | Tab-walk of toolbar and both dialogs; Space/Enter on Bloom; Esc on each dialog; `H` and `2` pressed with a dialog open do nothing; `E` mid-export no longer flips the dialog; `test_issue5/6` still pass. |
| **A4** | `fix(ui): derive control state from app state` | UX-13 | `app.js`: one `syncControlState()` that sets active/labels for the Quality group, Palette items and toggle label, Bloom/Raw buttons, Order-n, Pause — from renderer/math state. Called from `setMode`, `loadPresetObject` (both branches), `randomize`, `onContextRestored`. | Low | Load each curated preset and compare highlights to renderer state; user preset with bloom off; Raw on → preset load. |
| **A5** | `fix(ui): honest presentation of Reference-mode controls` | UX-09, UX-19 (tooltip), decision 5 | `index.html` / `app.js` `updateModeUI`: remove the 0.4 opacity and the "Locked to n=16" tooltip; Order-n and non-cobalt palette items get the tooltip **"Changing this enters Explore."**; Randomize tooltip becomes "Randomize (3) — enters Explore" (drops "Mode 3"). Zoom ± get `aria-disabled` + tooltip "Framing is locked in Reference" (existing toast kept); wheel toast throttled to once per ~3 s. **No change to which controls enter Explore.** | Low | Reference: click `8` → Explore (as before) with tooltip visible beforehand; zoom/wheel toast behaviour; `test_issue1` / `test_modes_and_exports` pass unchanged. |
| **A6** | `fix(copy): export progress and button reflect real dimensions` | UX-16 (decision 4), part of UX-12 | `renderer.js`: **three string literals only** (lines 1550, 1692, 1751) built from `width`/`height`. `index.html`: toolbar button "📷 Export 4K" → "📷 Export", tooltip "Export image…". | Very low (renderer diff is three literals; reviewed line by line) | Standard export at 3840×2160, 1920×1080, Current View: progress text shows the real size; renderer diff shows exactly 3 changed lines. |
| **A7** | `fix(presets): grid overflow and failure feedback` | UX-24 (overflow only), UX-25 (feedback part), UX-26 (feedback part) | `index.html`/`app.js`: curated cards `min-width:0; white-space:normal`, list height scaled to viewport; try/catch + toast around curated/user Load clicks; error toast when storage fails; toast when the 20-preset limit drops the oldest. `validatePreset`, delete behaviour and the `✕` label untouched. | Low | Screenshot equivalent to `p2` (no overflow); corrupt stored preset → toast, modal stays; storage-denied simulation; 21st save notice; `test_issue10/11` pass. |
| **A8** | `fix(ui): persistent context-loss banner; wrapping toast` | UX-11, UX-31 (wrapping only) | `index.html`: `#status-banner` (`role="alert"`), toast `max-width:min(92vw,520px); white-space:normal`. `app.js`: banner shown by `onContextLost` ("Graphics context lost — recovering…"), cleared with a short "restored" message by `onContextRestored`, and set to "Graphics recovery failed — reload the page" (with a Reload button) after the last retry. **Recovery logic untouched; existing toast strings kept.** | Low–medium (`test_issue2_*`, `test_issue15` assert on toast text and timers) | Simulate loss/restore/failed recovery; screenshot equivalent to `r2` now showing the banner; 390 px long toast stays inside the viewport. |
| **A9** | `fix(input): hover perturbation only over the canvas` | UX-21 (decision 3, amended) | `app.js` only. In the window `pointermove` hover branch, call `math.setPointer` **only when `event.target === canvas`** (UI panels, modals and the corner restore button are safe surfaces; the container itself is `pointer-events:none`, so uncovered areas still reach the canvas). Add one `pointerleave` listener on the canvas: in Explore, call `math.setPointer(0, 0)` so the **target returns to neutral and the existing damping relaxes the influence**; no direct write to `pointerCurrent`, no hard snap. Pan-drag branch, click shock, wheel, and `markInteraction()` are unchanged. | Low. Reference mode is unaffected (`setPointer` already no-ops there). | Pointer over canvas bends the art as today; moving onto toolbar/drawer/modal/restore button adds no new perturbation and the existing offset eases back to zero over the normal damping time (no visible jump); re-entering the canvas resumes normally; drag-pan over the canvas still works; `test_issue5_input_isolation`, `test_issue1_reference_invariant`, `test_modes_and_exports` pass unchanged. |

#### ✅ Checkpoint 1 (gate before Phase B)
1. All A-commits reviewed; existing suites at or better than the recorded baseline.
2. Viewport sweep (1920/1440/1366/1280/1024/390): no panel occludes a control; drawer sliders all hit-testable; "QUALITY" stays with its buttons; Hide is always recoverable.
3. Diff guard: `math.js`, `adaptive.js`, `profiler.js`, `preset_validation.js` unchanged; `renderer.js` shows only the three string lines.
4. Keyboard pass: every control reachable, focus visible, Space/Enter work, Esc closes dialogs, no shortcut fires behind a dialog.
4a. Pointer pass: hovering any UI surface adds no perturbation; leaving the canvas relaxes the influence smoothly to neutral (no snap, no lingering offset).
5. Clean commit boundary (local tag `ui-checkpoint-1`). **Stop and report; do not push.**

---

### Phase B — primary bar + Controls panel (decisions 1, 2, 3, 7, 8)

| # | Commit | Fixes | Files / exact controls | Regression risk | Screenshots / tests |
|---|---|---|---|---|---|
| **B1** | `feat(ui): Explore session stash` | UX-07 (decision 2) | `app.js` only. **Stash:** when the user *leaves Explore for Reference* (mode button, key `1`, preset that loads a Reference preset), copy exactly what Reference overwrites: math `n, activeMorphology, baseA–D, userOffsetA–D, evolving, time`; renderer `zoom, targetZoom, viewCenter, targetViewCenter, activePalette`. Reference then resets as today. **Resume:** entering Explore via the mode button, key `2`, an Order-n click or a non-cobalt palette click restores the stash through the existing setters (then applies the clicked change), calls `updateRootsOfUnity/computeTransforms`, `startSymmetryTransition` if `n` changed, `clearAccumulation`, `syncControlState`. **Randomize and Explore-preset load** supply their own state: they discard the stash. The stash is never taken on context restore, export, URL start, or while exporting, and is never applied while in Reference. **Start fresh** (button added in B3) clears the stash and gives Explore the state it has today on first entry after load (canonical coefficients, zero offsets, drift off, cobalt, default framing); no confirmation. Clicking the already-active mode button/key is a no-op **at the handler level** (`setMode` itself is unchanged, so `loadPresetObject`'s authoritative `setMode('reference')` still works). | **Medium** — the Reference invariant is the thing to protect. `math.js`/`renderer.js` not touched. | `test_issue1_reference_invariant`, `test_issue5_input_isolation`, `test_modes_and_exports` must pass **unchanged**. New manual checks: Explore→tune→Reference (exact canonical state, bit-identical readout) →Explore (tuned session back); Randomize/preset discard; Order-n click from Reference with a stash; the Phase A pointer behaviour (canvas-only hover, neutral relaxation on leave) still holds after a stash resume. |
| **B2** | `feat(ui): one-row primary bar and docked Controls panel` | UX-03 (structural), UX-32 (docking), UX-23 (chip) | `index.html`: new bar (Mode, Randomize ▾, Presets, Export ▾, Controls, `?`) + caption; Controls panel (View / Mathematics / Live preview quality / Developer, Developer collapsed); existing buttons, sliders and the debug overlay **moved, not recreated, with their ids**; coefficient drawer folded into Mathematics; equation readout chip on short viewports. `app.js`: `setupUI` selectors unchanged (ids), panel open/close, `P` opens Mathematics, `?debug` opens Developer. | **Highest** — largest DOM move; tests key on ids, not layout. | Full viewport sweep; every control reachable by mouse and keyboard; `?mode=explore`, `?debug`, `?tier=…` URL params; every existing suite. Screenshots: 1920, 1366, 1280, 1024. |
| **B3** | `feat(ui): panel content — clarity and warnings` | UX-08, UX-09 (panel text), UX-20, UX-22 (decision 7, 8) | `index.html`/`app.js`: "Live preview quality" heading + "Preview only — exports use their own settings."; while Auto is active, read-only **"Current tier: <tier>"** under the quality row (from `adaptive.getStatus()`, display only; hidden when a manual tier is selected); Brute Force inline line **"Maximum live GPU load — high-end hardware recommended."** (also its tooltip, no dialog); coefficient rows show `base → effective`, one-line explainer, "Reset offsets"; **the four sliders and their ranges are unchanged**; "Changing this enters Explore." lines; **Start fresh** button. | Low | Tier switch updates the line; preset with `tier: bruteforce` shows the warning; key `X` shows it; slider values and ranges identical to today. |
| **B4** | `feat(ui): help sheet and caption copy` | UX-10, UX-18 | `index.html`/`app.js`: `?` sheet (shortcuts + gestures, outside Debug); concise mode caption text (keeps the two mode names and the dot colours); README key table corrected. | Low (`test_issue13` checks the pill text is *not* `REFERENCE MODE` after fatal init: keep that behaviour) | Open/close with mouse, `?`, Esc; copy review. |

#### ✅ Checkpoint 2 (gate before Phase C)
Same gate as Checkpoint 1, plus: Reference invariant re-verified end to end (Explore↔Reference cycles leave Reference bit-identical to the canonical state); no capability lost (checklist of all 44 original controls and 14 shortcuts mapped to their new location); artwork occupies a larger share of the viewport than today at 1366×768 and 1280×720 (measure chrome height with the panel closed). Tag `ui-checkpoint-2`; **stop and report; do not push.**

---

### Phase C — responsive, accessibility, export modal, secondary copy

| # | Commit | Fixes | Files / exact controls | Regression risk | Screenshots / tests |
|---|---|---|---|---|---|
| **C1** | `feat(ui): small-screen and touch layout` | UX-33, UX-30 (touch part), UX-18 (truncation) | `index.html` CSS media queries (`max-width: 900px`, `pointer: coarse`): bottom bar, bottom-sheet panel, ≥ 40 px targets, caption truncation, full-width modals. No gesture work. | Low (CSS) | 390×844, 844×390, 1024×768; touch-emulation pass for Hide/restore, panel, both dialogs. |
| **C2** | `fix(a11y): contrast, target size, announcements` | UX-29, UX-30, UX-31 (announce), UX-34 | CSS colour tokens ≥ 4.5:1 for small labels and a 11 px minimum for readable text; ≥ 24 px targets on desktop; `role="status"`/`aria-live` on toast and export status; drop `user-scalable=no`. | Very low | Re-measure contrast and target sizes against the audit figures. |
| **C3** | `feat(export): dialog states` | UX-12 (wording), UX-14, UX-15, UX-17 (decision 6) | `index.html`/`app.js` UI wiring in `runExport`'s catch/then paths **only**: tabs/options/✕ disabled while running; Start → "Exporting…", Cancel → "Cancel export"; **cancel clears progress immediately**; failure shown in error style with a plain sentence; **success stays open** with filename + output resolution and a single **Done** (✕/Esc close; the 700 ms auto-close removed); summary line; "Heavier" note on Master; 120 "Recommended"; consistent nouns/verbs ("Passes"); fixed dialog height to stop the vertical jump. **No ETA, no estimates; stage + percentage only.** The export algorithms, `AbortSignal` handling and session-restore `finally` blocks are not edited. | Medium — `runExport` finally-blocks restore the session; only UI lines change. Tests needing update: `test_issue14_transactions`, any test expecting auto-close. | `test_export_*`, `test_issue6/9`, Master cancel at each stage, success state with filename/resolution, failure state, tab/✕ locked while running. |
| **C4** | `chore(ui): secondary copy and docs` | UX-36, 37, 39, 41, 43, README | Palette naming (one name per palette), tooltip accuracy (no phantom `+`/`−` keys), capitalisation, preset-load toast mentions tier (one clause), optional Reference/Explore tag on curated cards. | Very low | Copy diff review. |

#### ✅ Checkpoint 3 (final)
Full suite + viewport sweep + keyboard/touch pass + diff guard; update this document's issue statuses; tag `ui-checkpoint-3`. No push without your say-so.

---

## 9. Owner decisions (final) and what is explicitly out of scope

### 9.1 Decisions as received (recorded verbatim in intent; applied above)

| # | Decision | Where applied |
|---|---|---|
| 1 | Approve bar + Controls panel; **fix the 50 % width cap immediately** as an interim step, then restructure (one-row primary bar, docked Controls panel, collapsed Developer section; artwork dominant) | UX-03; A1 then B2 |
| 2 | **In-memory Explore stash**; Reference resets to the exact canonical state; returning to Explore **auto-resumes** with no confirmation; optional small "Reset Explore / Start Fresh"; Reference invariant not weakened | UX-07; B1, B3 |
| 3 | Hover perturbation **limited to the canvas**; UI is a safe surface; no Pointer Influence toggle. **Amended:** on canvas `pointerleave` the pointer target returns to neutral and the existing interpolation relaxes it (no hard snap). **Moved to Phase A.** | UX-21; **A9** |
| 4 | "4K" progress strings in `renderer.js` become **dynamic from export dimensions**; copy only, no export-logic change | UX-16; A6 |
| 5 | Order-n and palette **stay usable** in Reference; no disabled styling; helper **"Changing this enters Explore."** | UX-09; A5, B3 |
| 6 | Export **success stays open** until dismissed with filename + resolution + Done; **stale progress cleared on cancel**; **no ETA** | UX-15, UX-17, UX-12; C3 |
| 7 | Brute Force: **inline warning only** ("Maximum live GPU load — high-end hardware recommended."), no confirm dialog | UX-20; B3 |
| 8 | **Keep four coefficient sliders**; no eight-component editor | UX-22; B3 |
| 9 | Do not commit all screenshots; keep `UI_UX_AUDIT.md`; retain **8 representative images**, full set local | §3 (done) |

Also approved and scheduled: persistent context-loss banner (A8), corner restore after Hide (A2), keyboard focus treatment (A3), Esc for dialogs (A3), modal focus management (A3), no shortcuts behind dialogs (A3), preset-grid overflow fix (A7), clearer preset failure feedback (A7), "Live preview quality" clarification (B3), clearer export output/cost wording (C3), gesture/help discoverability outside Debug (B4).

### 9.2 Explicitly out of scope for this pass

- **ETA, or any time/size estimate** (wait for a reliable estimator).
- **Eight-component coefficient editor**, numeric entry, per-row reset.
- **Pointer-influence toggle** (or any new toggle not needed to fix a real interaction problem).
- **Confirmation dialog for Brute Force** (revisit only if physical-hardware testing shows severe lockups).
- Regrouping or renaming Quality tiers.
- Preset changes beyond overflow and failure feedback: no Save/Download split, Copy-JSON-uses-name, duplicate-name handling, delete confirmation/undo.
- Replacing emoji icons, backdrop-click-to-close, "Export another", touch pinch/pan gestures, any change to canonical Reference behaviour.

### 9.3 Interpretation points, with review outcome

I applied the decisions as written. These were the implementation details I had to choose. **Review outcome (second round):**

| # | Point | Outcome |
|---|---|---|
| 1 | **Stash scope (B1):** only what Reference overwrites (coefficients, offsets, `n`, morphology, drift flag/time, camera, palette). Quality tier, bloom/raw view and transient pointer/shock state are not stashed. | **Approved as written** |
| 2 | **Re-entry paths (B1):** Order-n / palette clicks from Reference resume the stash, then apply the click; Randomize and loading an Explore preset replace the session instead of resuming. | **Approved as written** |
| 3 | **Leaving the canvas:** ~~hold the last influence~~ | **Replaced:** on canvas `pointerleave` set the pointer target to neutral and let the existing interpolation relax it; no hard snap. **Now in Phase A (A9).** |
| 4 | **No-op on the active mode (B1):** a redundant click on "Reference" no longer wipes a settled image (handler level only; `setMode` unchanged). | **Approved as written** |
| 5 | **Zoom ± in Reference (A5):** shown as unavailable (they do not enter Explore). | **Approved as written** |
| 6 | **Esc during an export (A3):** ignored; Cancel remains the explicit way to stop. | **Approved as written** |
| 7 | **Auto-tier display (B3):** read-only, shown only while Auto is active. | **Approved with copy change:** **"Current tier: High"** (explicit read-only wording), not "Now: High". |

**Status: Phase A (A1–A9, then Checkpoint 1) is ready to start on your go-ahead. Phases B and C remain gated behind Checkpoints 1 and 2.**

---

## 10. Phase A / Checkpoint 1 result (recorded after implementation)

**Branch `ui/phase-a`, tag `ui-checkpoint-1` @ `212eea5` (local only, not pushed).** Full regression suite on the tagged commit: 7,049/7,049 (identical to the untouched `1f14dd4` baseline). Guard: `math.js`, `adaptive.js`, `profiler.js`, `preset_validation.js` zero diff; `renderer.js` only the three progress-string lines.

Commits: A1 `687b908` · A2 `b990d6c` · A3 `5ccbb38` · A4 `06aff86` · A5 `8a5118d` · A6 `50bdee3` · A7 `0ea3634` · A8 `5b6d512` · A9 `012227a` · follow-up `212eea5` (hidden controls `inert`).

Deviations from §8 (all small, UI-only):
1. **Redundant-mode no-op moved from B1 to A5** (`requestMode`, handler level only), because the Checkpoint 1 list required verifying a settled Reference is not redeveloped by redundant mode clicks.
2. **Extra commit `212eea5`:** after A2, Tab could reach the hidden toolbar for a moment after Hide (the visibility change is applied lazily); `inert` fixes it.
3. **Small additions inside planned commits:** toolbar painted above the status pill so dropdown menus are not clipped (A1); Ctrl/Meta/Alt combinations no longer trigger app shortcuts, and re-importing the same preset file works (A3); the Raw button label is `Raw` / `Raw: ON` consistently (A4); dialogs get `max-height: calc(100vh - 24px)`, plus feedback on storage failure at delete and clipboard rejection (A7).
4. Evidence was captured on the real RTX 4070 (Chrome, ANGLE/D3D11); the original audit screenshots used software GL.

---

## 11. Phase B / Checkpoint 2 result (recorded after implementation)

**Branch `ui/phase-a`, tag `ui-checkpoint-2` @ `8d86281` (local only, not pushed).** Full regression suite on the tagged commit: **7,162/7,162** = 7,049 existing + 113 new Phase B assertions. Diff guard: `math.js`, `adaptive.js`, `profiler.js`, `preset_validation.js` zero diff (vs baseline and vs `ui-checkpoint-1`); `renderer.js` unchanged since Checkpoint 1 (only the three approved progress-string lines vs baseline).

Commits (after `ui-checkpoint-1` = `212eea5`): B1 `c3ea102` Explore stash · B2 `cec6d55` primary bar + Controls panel · B3 `a5a62bb` panel clarity · B4 `07a2068` help, caption copy, README · follow-up `8d86281` primary-bar height.

Artwork space (UI-covered share of the viewport, default state; chrome = bar + caption bottom edge): 1366×768 14.7 % → 5.2 % (chrome 98 → 78 px, readout 160 → 35 px); 1280×720 15.9 % → 5.9 % (98 → 78 px); 1440×900 12.4 % → 6.3 %; 1024×768 16.1 % → 7.0 %; 1920×1080 7.3 % → 3.9 % (chrome 72 → 78 px); 390×844 34.6 % → 23.0 % (212 → 112 px).

Deviations from §8: (1) extra commit `8d86281` (the new bar measured 6 px taller than needed); (2) the debug overlay docks top-left (not beside the panel); (3) the status banner intentionally layers above the debug overlay when both are shown at 1024 px; (4) `Coeffs` became a *Coefficients* disclosure inside Mathematics; (5) Esc also closes open menus before the panel; (6) no bottom-sheet / touch layout yet (Phase C), so with every panel open at 390 px the debug overlay, panel, readout and toast overlap (the default state does not); (7) `?` is the 15th shortcut.

---

## 12. Phase C / Checkpoint 3 - final record

**Branch `ui/phase-a`, tag `ui-checkpoint-3` @ `db5caa3` (local only, not merged, not pushed).** Complete regression suite on the tagged commit: **7,409 / 7,409** = 7,051 existing hardened assertions (the 7,049 from before, plus 2 from the intentional `test_issue14_transactions` update: 47 -> 49) + 113 Phase B + 245 Phase C. Issue 3 (5-minute idle) 43/43, Issue 7 (background tab) 16/16, integrated adversarial 39/39.

Phase C commits (after `ui-checkpoint-2` = `8d86281`): C1 `a3942f0` small-screen layout · C2 `e04539c` accessibility · C3 `c762b8f` export dialog states · C4 `3b04566` microcopy · fixes found during the checkpoint: `ae9e905` (readout chip hidden behind the open sheet), `db5caa3` (scrolled-to controls kept clear of the sticky header).

Diff guard: `math.js`, `adaptive.js`, `profiler.js`, `preset_validation.js` zero diff vs the hardened baseline; `renderer.js` unchanged since Checkpoint 2 (only the three approved progress-string lines). No id, id-listener, `App` method or shortcut removed vs `1f14dd4`, `212eea5` or `8d86281` (only `?` added); labels were renamed, never dropped.

Measured: UI-covered area, Checkpoint 2 -> 3: 1366x768 5.21 % -> 5.44 %, 1280x720 5.93 % -> 6.19 % (the compact readout toggle is 24 px tall now), 390x844 22.98 % -> 15.45 % (compact readout chip); chrome bottom unchanged at 78 px (112 px at 390). Accessibility audit (1366x900, all surfaces): contrast failures 21 -> 0, text under 10.5 px 22 -> 0, controls under 24 px 28 -> 0. Narrow sweep (390x844, 430x932, 768x1024 plus touch emulation): no horizontal overflow, panel fits and scrolls internally, no page scroll, every dialog fits with its close button reachable, essential controls hit-testable with everything open.

Deviations: (1) two checkpoint fixes (above); (2) the debug overlay on screens narrower than 820 px is a non-interactive strip, so with every developer surface open at once the alert banner and toast still layer above it by design; (3) Standard/Reference Master wording changed in the dialog only - the `exportType` values and `exportPNG` / `exportReferenceMaster` APIs are unchanged.
