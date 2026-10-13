# Release-Candidate Report — Möbius Complex Dynamics Laboratory

> **Layout note:** this report was written against the flat repository root. After publication the repository was organized into folders without changing any production file: runners and suites are now under `tests/`, and the path map is in [`REPO_LAYOUT.md`](REPO_LAYOUT.md). `release_checks/` did not move.

Audit date: 2026-10-12. Scope: find any user-facing defect that should block a public release. This was not a redesign, refactor, feature or optimization pass, and **no production file was changed** by this audit.

Summary at the original audit (build `3d334ab`): 0 blockers, 0 major issues, 12 minor issues (§21). Verdict in §24.

**Update after owner review:** the owner chose three of the twelve minors (M-1, M-4, M-5) to fix before publication. They are fixed in three separate commits on top of the audited build (§20), re-verified with the full regression (7,618 / 7,618) and live in real Chrome. **Remaining: 0 blockers, 0 major, 9 minor.** The original audit text below is preserved; the fix pass is recorded in §2, §18, §20, §21, §23 and §24.

---

## 1. Production URL

https://mobius-dynamics.vercel.app/

## 2. Exact final origin/main SHA

Audited build: `3d334abc947f5ffa718cda02a5a5391b3103219a` (`fix(presets): preserve entered name when copying json`), `main` == `origin/main`, working tree clean at start.

The original audit added only a report/test-only commit on top of it (this file and `release_checks/`, `b5f1b09`).

**Fix pass (after owner review):** three fix commits were then added: `4873f6b` (M-1), `fa48f71` (M-4), `fe65a89` (M-5). `fe65a89513ad3b2af3b18752eedf6135a3610a6b` was `origin/main` and the deployed build when the fix pass was verified. This report update is a docs-only commit on top; its SHA is in the hand-off message. Production files changed by the fix pass: `app.js` and `index.html` only. Zero diff in `math.js`, `adaptive.js`, `profiler.js`, `preset_validation.js`, `renderer.js` versus `b5f1b09`. Its SHA, and the deployed SHA after pushing it, are reported in the hand-off message because a file cannot contain its own commit hash. Zero diff in `app.js`, `index.html`, `renderer.js`, `math.js`, `adaptive.js`, `profiler.js`, `preset_validation.js` versus `3d334ab`.

## 3. Exact deployed revision verified

Vercel exposes no revision header, so the evidence is content equality. Live files fetched from production and compared (CRs stripped) with `git show origin/main:<file>`:

| File | md5 (live == main) |
|---|---|
| index.html | b88f8af4eabe126bfc89c4666decbd9a |
| app.js | cf1085f137f3cd9b61a0b5ecc8ecb562 |
| renderer.js | 8a91f5071cf7ae8ee3388ae243e7b207 |
| math.js | 9cd902a1fc235e5fbfa59defce6c9670 |
| adaptive.js | 1d5fa83a70e1fe37974f1115860a129d |
| profiler.js | 4e7e41535f6e9a6a5330d7c46532b63c |
| preset_validation.js | 4bbc83153efbdbdc1c927d6cfb11b3a5 |

All seven MATCH. Response headers: `ETag W/"b88f8af4…"` (= index.html md5), `Last-Modified Mon, 12 Oct 2026 19:06:34 GMT`, `X-Vercel-Cache: HIT`, `X-Vercel-Id iad1::2qlsg-…`. Production was current, so testing proceeded.

## 4. OS / hardware

Windows 11 Home 10.0.26200 (64-bit) · Intel Core i9-14900HX · 31.7 GB RAM · NVIDIA GeForce RTX 4070 Laptop GPU (driver 32.0.15.6094) plus Intel UHD Graphics. Chrome/Edge both rendered on `ANGLE (NVIDIA RTX 4070 Laptop, Direct3D11)`, WebGL 2.0.

## 5. Browser/version matrix

| Browser | Version | Result |
|---|---|---|
| Google Chrome | 154.0.8037.98 | verified (real, headful) |
| Microsoft Edge | 155.0.4283.45 | verified (real, headful) |
| Firefox | not installed | **UNVERIFIED** (not fabricated) |
| Safari / macOS | not available | **UNVERIFIED** |
| iOS Safari | not available | **UNVERIFIED** |

No Safari-specific hacks were attempted.

## 6. Real vs headless distinction

* The existing 7,441-assertion suite runs in **headless** Chrome, inside a 160×120 iframe, with `HTMLAnchorElement.click`, clipboard, file input, `customDpr` and tab-visibility stubbed or forced (§15).
* The release checks in `release_checks/` run **headful** Chrome and Edge against the **live URL**, with trusted mouse/keyboard/touch input (Chrome DevTools Protocol input events), a real downloads directory whose files were opened and parsed (PNG signature, IHDR dimensions, IDAT inflate, IEND; JSON parse), a real clipboard (read-back and a real Ctrl+V), and a real file chooser.
* Honest limits: these are automation-driven, not a human at the keyboard. "Normal profile" means a brand-new profile directory with only a download-folder preference and default content settings (Chrome's default download protections active), not the owner's everyday profile. Touch and HiDPI are emulated on a desktop, not real phones.

## 7. Viewport/device matrix

Real-browser checks at 1920×1080, 1440×900, 1366×768, 1280×720, 1024×768, 768×1024, 430×932, 390×844 (touch emulation for the last two), in both browsers. At each: default artwork, toast, context-loss banner, Controls open with every section and Coefficients, Help, Presets (6 saved items incl. a very long name), Export (idle, Reference Master tab, running, canceled, success, failed), Hide/Show, and a live resize. Asserted: no horizontal page overflow, no overlapping primary controls, nothing outside the viewport, every control reachable and not covered by a sticky header (hit-tested), no clipped text, readout never overlaps the panel, dialogs fit. **209/209 in Chrome, 209/209 in Edge.** Also DPR 1.25 / 2 / 3, touch tap/drag, window resized four times during an export.

Informational measurements: UI boxes cover about 4–7 % of the artwork area on desktop and 16–18 % on phones; smallest control is 24 px on desktop, 38 px (primary bar) and 28 px (panel) on phone layouts (see minor M-9).

## 8. Complete user-flow matrix

| Area | Covered (real browser) | Script | Chrome | Edge |
|---|---|---|---|---|
| Reference | fresh load, canonical state, development→settled, Auto tier line, Brute Force warning, hide/restore, Controls, Help, readout, Reference→Explore→Reference, redundant clicks, canvas input ignored, context loss/recovery | rc_ref, rc_flows2, rc_kbd, rc_resp | pass | pass |
| Explore | enter, stash restore, Start Fresh, hover bend, relax on leave, shock+decay, pan, wheel zoom (0.3–500 hammering), zoom buttons, pause/resume, four sliders at extremes, Reset view/offsets, Order n, palette, 40 rapid mode toggles, 90 s drift soak | rc_explore, rc_ref | 24/24 | 24/24 |
| Randomize | all 6 families ×2, 20 rapid, then generate→interact→Reference→return→re-randomize for each family | rc_ref, rc_flows2 | pass | pass |
| Presets | save/download, Copy JSON, import (real chooser, same file twice), load, delete, 6 curated, duplicate, 600-char, Unicode, markup, path chars, blank, corrupt/malformed/oversized/NaN/huge-n/prototype JSON, real clipboard denial, real storage exhaustion, unreadable storage, corrupt storage, reload persistence, 20-preset cap, two tabs | rc_stage1, rc_presets, rc_quota, rc_extra | pass (2 minors) | pass (2 minors) |
| Export | Current View, 1080p, 4K/120, Master 120 and 240, 60/30 passes, twice in a row, after Explore interaction, after preset load, after settle, cancel at ~40 ms / mid-development / ≥90 % / during PNG encoding, retry after each cancel, after context loss, hidden tab, resize and DPR changes, reload mid-export, double-click Start | rc_stage1, rc_export, rc_flows2, rc_extra | pass | pass |
| Input rules | Tab/Shift+Tab traps, Esc ladder, shortcut isolation behind dialogs, active-export Esc, Hide never strands, tab sweep, controls/backdrops never reach the artwork | rc_kbd, rc_export, rc_flows2 | 43/43 | 43/43 |

## 9. Native download tests

Real files on disk, opened and validated (non-zero, valid PNG, dimensions, extension, duplicates renamed by the browser, no `.crdownload` leftovers).

| Export | Result (both browsers) |
|---|---|
| 1920×1080, 30 passes | valid 1920×1080 PNG (≈2.7 MB, 0.6–0.7 s) |
| second immediate 1920×1080 | valid PNG saved as `…1920x1080 (1).png`; first file untouched |
| 3840×2160, 120 passes | valid 3840×2160 PNG (≈10.7 MB, 1.4 s) |
| Reference Master 4096², 120 passes | valid 4096×4096 PNG (≈27 MB, 2.3 s) |
| Reference Master 240 | valid 4096×4096 PNG |
| Current View at DPR 1.25 / 2 / 3 | valid; size announced in the dialog equals the file |
| Preset Save & Download | real `*.mobius.json`, parses, typed name preserved |

Canceled / failed exports: "Export canceled / failed" shown, **no file, no zero-byte file, no stale progress, app still usable**, retry succeeds. Across the whole audit every one-click action produced exactly one file (60/60 in the repeated cycle).

## 10. Native clipboard tests

* Copy JSON writes the real clipboard: valid JSON, **typed name preserved**, Unicode/markup/quote names literal, blank name falls back to `Preset <time>` identical to Save & Download (same 5-second window).
* Fresh profile with **no** permission overrides: success toast, and a real Ctrl+V paste yields the JSON.
* Real permission denial (CDP `clipboard-write`/`clipboard-read` denied): app says "Could not copy to the clipboard." — no false success.
* Clipboard API missing / rejecting: honest failure messages.

## 11. Native file-picker/import tests

Imports through the real file chooser: saved `.mobius.json` loads under its name; JSON from Copy JSON keeps its name; the same file twice in a row loads both times (input is reset); rejected with a message and session untouched: non-JSON, empty, array, NaN coefficient, n=99999, 1.2 MB file ("too large", rejected before parsing).

## 12. Fresh-profile results

Empty storage, no cache, default download protections, default (ungranted) clipboard permissions: loads in canonical Reference with zero console/page errors, 8 requests / 78,863 bytes, all same-origin HTTPS, no periodic traffic over 20 s, no CSP violations, WebGL healthy with no GL error. Downloads, Copy JSON (real paste), import, exports all work. Both browsers.

## 13. Used-profile results

Same profile relaunched with warm HTTP cache (304 revalidation), a preset saved in the previous session, and existing downloads: starts in canonical Reference, preset still listed, an export whose name collides with an earlier file is renamed rather than overwritten, no errors. No dependence on development residue found. Both browsers.

## 14. Console/network audit

Across all runs: **0 uncaught exceptions/unhandled rejections, 0 failed requests, 0 HTTP ≥ 400, 0 CSP violations, 0 GL errors, 0 console errors/warnings** from normal use. Explained, expected messages: (a) `console.error "Reference Master Export error"` when the check itself forced a WebGL context loss mid-export; (b) the app's own `console.log` "[Adaptive Tier Change] …" informational lines (not errors). Headers: HSTS preload present; `Cache-Control: public, max-age=0, must-revalidate`; no `X-Content-Type-Options` (M-12). Favicon 200.

## 15. Mock/stub blind-spot audit

Classes: **A** covered by a separate real-browser test · **B** low-risk, inherently synthetic · **C** needs a real check (now supplied). No useful mocked test was deleted.

| Boundary replaced in the existing suite | Where | Could it pass while the real operation fails? | Class → coverage |
|---|---|---|---|
| `HTMLAnchorElement.prototype.click` counter | `issue2_test_instrumentation.js`, injected by all `boot()` pages (22) and 5 direct pages | **Yes — this hid the real download bug** | C → real downloads: rc_stage1, rc_export, rc_soak_full (A) |
| `navigator.clipboard` fake | test_preset_copy_name | yes | C → real read-back, real denial, real paste: rc_stage1, rc_presets, rc_flows2 (A) |
| Import calls `importPresetFile(new File)` directly, skipping `<input type=file>` | test_issue10/11, copy_name | yes (input reset, same-file re-import, real change event) | C → real chooser: rc_stage1, rc_presets, rc_soak_full (A) |
| `canvas.toBlob` replaced to hold/fail encoding | 8 pages | for cancel/failure logic: no; for real encoding: yes | B for failure injection; real encoding A via real exports |
| `URL.createObjectURL` pass-through wrapper | issue15, copy_name | no | B |
| Synthetic `.click()` / `dispatchEvent` (untrusted) and synthetic KeyboardEvent | 14 pages | partly (the export guard treats untrusted events specially) | C → trusted input: rc_kbd, rc_export, rc_flows2 (A) |
| localStorage patched/failed | integrated, issue11, copy_name | partly | B + real exhaustion: rc_quota (A) |
| WebGL context loss via `WEBGL_lose_context` | 12 pages | same event path as a real loss; a driver reset is not reproducible | B + live rc_ref/rc_export/rc_extra |
| Harness forces tiny 160×120 iframe, `isTabHidden=true`, `customDpr=1`, profiler off, srcdoc origin | `boot()` | layout, DPR, permission semantics differ from production | C → rc_resp, rc_extra, rc_perf, rc_net on the live origin (A) |
| Headless regression runner sets `--disable-background-timer-throttling --disable-renderer-backgrounding` | `run_browser_regressions.py` | background throttling not exercised there | A: Issue 7 uses real hidden tabs; real hidden-tab export in rc_export, rc_soak_full |
| rAF/setTimeout/addEventListener wrappers | instrumentation | no (pass-through accounting) | B |

## 16. Reference invariant results

Checked against `CONRADI_REFERENCE` after every path: n=16; a=−0.755+0.330i, b=−0.376+0.026i, c=6.401+0.803i, d=1.520+0.840i (base and active); offsets, pointer target/current and shock zero; pointer/shock disabled; drift off; time 0; zoom 1.65, centre (0,0); cobalt palette; both mode flags `reference`.

Paths verified (all pass, both browsers, ≥35 invariant assertions in rc_ref alone plus the rest): mode button · keyboard 1/2 · canvas hover/click/wheel/Shift-drag while in Reference · R/B/T/O/D/P keys · Randomize (6 families ×2, 20 rapid) · Order-n click · palette click · Explore stash resume · Start Fresh · 6 curated presets · 7 malformed/oversized imports · completed export · export canceled at four stages · Reference Master from Explore · WebGL context loss and recovery (from Reference and from Explore) · Brute Force tier · reload · DPR changes · touch · window resized during export · hide/show.

No path poisoned Reference. Settled Reference also verified: develops on its own in ≈43 s on this hardware, then does **zero draw calls, zero timer queries, zero new accumulation frames** over 4 s; opening Controls/Help does not wake it; Explore wakes it and it re-settles in ≈41 s.

## 17. Repeated-use/soak results

Measured, not assumed (CDP post-GC heap, DOM nodes, JS listeners, live GL objects).

* **Full release-spec cycle** (Reference→Explore→interact→Randomize→2 exports→Save→Copy JSON→real Import→load→Reference→restore Explore→4K export→canceled export→retry→Hide/Show→resize→background/foreground→Reference/Explore) ×12 per browser: 0 problems; **60/60 downloads delivered for 60 clicks** (no duplicates); heap 2.30→2.41 MB, nodes 1,301→1,397, listeners 118→134, GL objects constant; one key press runs one handler; one toast element; mode-toggle handler time 0.4→0.5 ms.
* 40-cycle variant (Save/load/exports incl. Reference Master every 5th) per browser: heap 2.26→2.38 MB, nodes plateau at ≈1,490, listeners at 150, exactly one WebGL context.
* 90 s drift + pointer + shock soak in chaotic Explore: finite state, no GL error.
* Test-harness correction (not an app defect): an earlier soak showed DOM/listener growth that was caused by un-disposed Puppeteer element handles; with real-mouse clicks the same loop shows zero growth.

Performance (RTX 4070): Auto, Low, Standard, High, Ultra, Extreme and Brute Force all select correctly and hold ≈60 fps (p50 16.7 ms, p95 ≤ 18.3 ms) in Reference and chaotic Explore in both browsers, with isolated single-frame spikes at most 28.7 ms (Chrome) / 50.8 ms (Edge, Brute Force). Brute Force shows exactly "Maximum live GPU load — high-end hardware recommended." No crash or context loss in ordinary use. Quality budgets and Reference Master 120/240 untouched.

## 18. Automated regression total

**Original audit: 7,441 / 7,441** — unchanged from baseline because the audit itself added no assertions to the HTML suites; the new real-browser checks are a separate gate.

**After the fix pass: 7,618 / 7,618** (7,441 + 13 + 146 + 18): `test_preset_name_limit.html` 13, `test_url_param_validation.html` 146, `test_space_after_randomize.html` 18. Browser suites 7,520 + Issue 7 background-tab 16 + integrated adversarial 39 + Issue 3 five-minute Reference idle 43; every runner exit 0, zero FAIL lines. Each new test was run against the previous code and fails there (M-1 1 failure, M-4 many, M-5 3 failures).

| Runner | Assertions | Exit |
|---|---|---|
| run_browser_regressions.py (30 pages) | 7,343 | 0 |
| run_issue7_background.py (real hidden tabs) | 16 | 0 |
| run_integrated_hardening.py (adversarial campaign) | 39 | 0 |
| run_issue3_regressions.py (5-minute Reference idle campaign) | 43 | 0 |

Also: `node --check` on every production and test JS file and on every inline `<script>` (57 blocks) — 0 errors; `py_compile` of the four runners OK; `git diff --check` clean.

Real-browser production battery (new, `release_checks/`): per browser 530 assertions pass (Chrome 530, Edge 530), plus 2 reproduced known-minor rows each:
stage1 16 · reference/explore/randomize/malformed/context/export-paths 78 · presets 28 (+2 known) · export lifecycle 21 · keyboard 43 · explore 24 · responsive 209 · network/profiles 15 · extra (HiDPI/touch/resize/no-WebGL/tabs) 23 · flows2 34 · quota 7 · tiers 16 · soak 7 · full-spec soak 9. Two harness-expectation mistakes (Chrome's `name.mobius (1).json` rename pattern; `..` file name) and one under-filled quota test were corrected in the scripts; none was an app defect.

## 19. Issues found

No blocker and no major issue. Twelve minor issues (§21). Items examined and **not** defects: Space shortcut after a button focus is a deliberate accessibility rule (M-5 notes the trade-off); exports finishing in 1–2 s; the downloaded name differing from the dialog name when the browser renames a duplicate.

## 20. Fix commit for each issue

Original audit: none. No blocker/major was found, and no minor was fixed during the audit; the only commit was the report/test-only commit described in §2.

Fix pass (owner-selected minors, one defect per commit, each with a regression test, no protected file touched):

| Finding | Commit | Change | Regression test |
|---|---|---|---|
| M-1 | `4873f6b` `fix(presets): align preset name input with schema limit` | `maxlength="512"` on `#preset-name-input` (UTF-16 code units, the unit the validator counts). Schema untouched | `test_preset_name_limit.html` (13) |
| M-4 | `fa48f71` `fix(url): reject malformed runtime parameters` | `sanitizeRuntimeUrl()` in `app.js` runs before any engine module is built. Invalid `mode`, `n`, `particles`, `steps`, `dpr`, `zoom`, `cx`, `cy` are dropped (strict decimal parsing; `n` reuses the preset schema's own integer 1..64 domain; no new caps) and the address bar is cleaned with `history.replaceState`, because `renderer.js`, `adaptive.js` and `profiler.js` also read `location.search` themselves. Valid benchmark URLs are unchanged | `test_url_param_validation.html` (146) |
| M-5 | `fe65a89` `fix(input): prevent pointer randomize focus from stealing space shortcut` | a pointer click (`event.detail > 0`) on the Randomize button releases focus after the action; keyboard activation (`detail 0`) keeps normal focus; no global blur. A real-Chrome probe showed only this button was affected (style-menu items leave focus on the body; the ▾ toggle only toggles its menu) | `test_space_after_randomize.html` (18) |

M-4 URL hook inventory (every parameter read): `mode` (reference|explore), `n` (integer 1..64), `particles` and `steps` (integer ≥ 1), `dpr` and `zoom` (finite > 0), `cx` and `cy` (finite), plus enum/flag hooks that were already safe (`tier` and `palette` ignore unknown values, `morph`, `randomize`, `view`, `bruteforce`/`brute`, `raw`, `nobloom`, `debug`, `profile`, `notimer`/`noquery`, `capture`). Benchmark/test values found in the repo (n=8/16/24, zoom up to 130, dpr=0.5, decimal cx/cy, `tier=potato&dpr=0.5`) are all accepted unchanged and asserted.

## 21. Remaining MINOR issues (for owner review)

Status after the fix pass: **M-1, M-4 and M-5 are RESOLVED** (commits in §20) and are kept in the table below as audit history; **9 minors remain** (M-2, M-3, M-6, M-7, M-8, M-9, M-10, M-11, M-12), all accepted or deferred by the owner.

| # | Issue | Repro / evidence | Suggested remedy (not applied) |
|---|---|---|---|
| M-1 ✅ resolved `4873f6b` | A preset name longer than 512 characters can be saved, but its own file is then rejected on import | type 600 chars → Save; import that file → "Invalid preset field: name." (validator caps at 512; the field has no `maxlength`) | `maxlength="512"` on `#preset-name-input` |
| M-2 | A non-object entry in the stored list (`mobius_custom_presets`) stops the Presets dialog opening at all (uncaught TypeError, app.js:1772) until site data is cleared | set the key to `[null,{…}]`, reload, click Presets. Only reachable by tampering/corruption; the app itself never writes such data | filter to plain objects in `getUserPresets()` |
| M-3 | Any JSON object that passes the legacy-permissive schema loads as a "preset" — e.g. `{"name":"x"}` or an unrelated `package.json` — switching to Explore and discarding the saved Explore session | import `{"name":"x"}` → "Loaded preset: x" | requires a stricter schema (`preset_validation.js` is protected; owner decision) |
| M-4 ✅ resolved `fa48f71` | Undocumented URL hooks accept unvalidated values: `?n=abc` blank canvas "n=NaN"; `n=0/-5/1000000`; `dpr=-1` (300×150 canvas) / `dpr=64` (87,424×49,152 request); `particles=-1/0`; `steps=0/-1`; `?mode=zzz`; `steps=500` ≈ 23 fps | 33 cases tried in Chrome: no crash, hang, XSS or page error; Reference button or removing the parameter recovers | clamp/ignore in app.js, or restrict to a debug flag |
| M-5 ✅ resolved `fe65a89` | After mouse-clicking a toolbar button, Space re-activates that button instead of pausing drift (click the canvas first). Deliberate accessibility behaviour, but a change from the pre-redesign baseline where Space always paused | click Randomize, press Space → randomizes again | blur toolbar buttons after pointer activation |
| M-6 | Export success reads "✓ Export complete — Your browser saves the PNG to its downloads location." A browser cannot confirm the OS saved the file (Save-As prompt cancelled, rename) and the dialog shows the requested name, not a browser-renamed `(1)` name | browser limitation; the wording is already hedged | none needed; optional copy tweak |
| M-7 | Preset names that sanitize to nothing/dots produce odd file names (`..` → `mobius.json`) | cosmetic | none |
| M-8 | Duplicate preset names are allowed; Delete has no confirmation or undo | previously recorded in the UX audit | owner decision |
| M-9 | Touch target sizes on phone layouts: primary bar ≥ 38 px, panel controls ≥ 28 px (below the common 44 px guidance; meets WCAG 2.2 AA 24 px) | rc_resp 430×932, 390×844 | optional enlargement |
| M-10 | Clicking a dialog's backdrop does not dismiss it (Esc and ✕ work) — consistent across all three dialogs | rc_kbd | none |
| M-11 | On narrow screens a toast can overlap the export dialog footer for ~3 s (it is `pointer-events:none`, so taps pass through) | rc_resp 390×844 export-failed screenshot | none |
| M-12 | Hosting sends no `X-Content-Type-Options: nosniff` (HSTS and cache headers are fine) | response headers | add a Vercel header |

Observation, not reproduced: `importPresetFile` has no `FileReader.onerror`; a hard read failure would be silent.

## 22. Unsupported/unverified platforms

* Firefox (any OS) — not installed — **UNVERIFIED**
* Safari / macOS — **UNVERIFIED**
* iOS Safari — **UNVERIFIED**
* Android Chrome and real phones/tablets — touch and small-viewport behaviour verified only by emulation
* Chrome/Edge on macOS or Linux; Chrome/Edge older than the versions above
* GPUs other than the NVIDIA RTX 4070 laptop part; integrated, low-end and mobile GPUs (performance and graphics-memory limits unmeasured; the failure path was verified with a forced context loss and with WebGL disabled, where a clear alert is shown)

## 23. Known browser/platform limitations

* **Extreme but valid URL values are not capped** (deliberately, because benchmarks rely on unusual valid settings): a very large finite `?particles=`, `?steps=` or `?zoom=` can still make a tab slow or run out of GPU memory for whoever opens such a link. Only structurally impossible values are rejected (§20). This was documented rather than silently changed; a hostile-link resource cap would be a separate owner decision. Not tested at extreme upper values (`particles=5000000` and `steps=500` were tried in the audit: slower, no crash).
* A preset name at the 512-character limit produces a file name of about 525 characters; the browser shortens it (Chrome saved it as a 76-character `….json`, dropping `.mobius`). The file content is complete and imports correctly. This is the same browser-owned file-naming effect as M-7.

* No browser API tells a page whether a download finished or where it landed; the app does not claim to.
* Chrome renames duplicate downloads (`name (1).png`) and may prompt on multiple automatic downloads depending on the user's content settings; behaviour with "ask where to save" enabled was not exercised.
* WebGL2 is required; without it the app shows "Unable to initialize graphics…" and no controls work (verified, no uncaught errors).
* Real GPU-driver resets cannot be reproduced; context loss was exercised through `WEBGL_lose_context`.
* The app reads and writes only same-origin localStorage; clearing site data removes saved presets (Save also downloads a file).

## 24. Explicit final verdict

All core flows — Reference fidelity, Explore, Randomize, presets, real downloads, real clipboard, real import, export lifecycle, keyboard/focus/modal rules, responsive layouts, fresh and used profiles, repeated-use stability — work on the live production build in Chrome 154 and Edge 155 on real hardware, and the regression suite passes (7,441 / 7,441 at the original audit; 7,618 / 7,618 after the three owner-selected fixes, which were also re-verified live in real Chrome: 512-character name stops at 512, saves, and re-imports from the real downloaded file; `?n=abc`, `?n=-1`, `?dpr=-1`, `?mode=zzz` render the artwork with no console error; mouse-click Randomize then Space pauses instead of re-randomizing; one normal export still lands as a valid PNG). Firefox, Safari and iOS Safari were not available and are not claimed.

RELEASE READY

- Known blockers: 0
- Known major issues: 0
- Remaining minor issues: 9 (of the original 12, M-1, M-4 and M-5 were fixed before publication, §20)
- Unverified platforms: Firefox, Safari/macOS, iOS Safari (plus real Android/iOS devices, non-NVIDIA GPUs, and Chrome/Edge on macOS/Linux)
