# Functionality hardening, Issues 5–15

> **Layout note:** file names in this report (`run_browser_regressions.py`, `test_issue*.html`, `hardening_test_helpers.js` …) are the original flat-root names. The repository was later organized into folders; see [`REPO_LAYOUT.md`](REPO_LAYOUT.md) for where each file lives now. Run the whole gate with `python tests/run_all.py`.

Starting origin/main: `7078f94d59f5c988070e677ff08d80957d290619`.
Each issue is reproduced/audited before its production changes, tested and pushed separately.
The ordered pass is complete. No UI redesign, canonical math, Master quality, export resolution or tier-exposure policy changes.

## Issue 5 — export snapshot versus live input

Reproduced: yes. Before production changes, a seeded 96 x 64, 30-pass Standard control was compared with interference at each of three chunk progress callbacks. Fourteen of fifteen initial mutators changed decoded pixels: mode, randomize, symmetry, coefficients, palette, camera, bloom, view, gain, clear, reset, pause, keyboard and DOM mode controls. Quality alone left export pixels equal but changed live quality. Reproduction: `test_issue5_input_isolation.html?baseline=1` on the starting main with the test additions only (16/16 classification assertions).

Root cause: export read mutable live math and display settings after asynchronous yields, and clear/reset could clear its temporary targets. Fix: immutable mathematical/pixel inputs, prototype-preserving complete math/session snapshots restored in `finally`, protection of clear/transition entry points, and an export input guard for application commands and DOM events. Direct math/renderer/adaptive field interference is independently covered, so correctness does not rely on disabled controls. Inputs attempted during export are discarded; the transaction restores the start session. Geometry resources and live VBO isolation retain the existing architecture.

Files: `renderer.js`, `app.js`, `hardening_test_helpers.js`, `test_issue5_input_isolation.html`, this report. New checks cover sixteen mutators, Master control/interference decoded pixel equality, full session restoration and ordinary failure. Previous Issue 4 output hashes/VBO continuation, Issue 2 loss during develop/encoding, Master and mode/export checks pass. Reference/tier/rebuild retry checks pass before commit; 389 relevant assertions pass in total (the final 19-assertion Issue 5 run supersedes its earlier 16-assertion run). Commit and origin confirmation are recorded in the final table.

## Commit and verification ledger

Each listed commit was pushed and matched origin/main before continuing; all are ancestors of the final verification commit.

| Issue | Reproduced? | Result | Pushed commit SHA |
|---|---|---|---|
| 5 | Yes | Snapshot/input isolation | `b7974f5f5eed3a1fee93a7bfc1c0ccf5055fac75` |
| 6 | Yes | Cooperative cancellation | `827fbed17deedb663902baa3b284042d8e25a5ba` |
| 7 | Yes | Export timer yields while hidden | `26902b7eb294c781f3a22a0a8122481a8131fcf0` |
| 8 | Yes | Allocation checks and complete partial cleanup | `2a99087aa21c017ee6317c5630c1647c221c5bb8` |
| 9 | No | Already protected; coverage only | No production commit |
| 10 | Yes | Atomic preset validation | `9dc300b8c6f31d445a747f79223d267e6bf295b2` |
| 11 | Yes | Untrusted metadata rendered as text | `aad0528c2d88b28faecbc16df8be5fb92264a47d` |
| 12 | No | 6000-state GPU stress coverage; ranges unchanged | `7717876c3cf4bfeff1ae51228d15f8db36db45ea` |
| 13 | Yes | Explained startup failure and allocation checks | `6ab434e90be964e4284c0637e9868c91e109400c` |
| 14 | Yes | Completion timer ownership and Reference API guard | `9581598eec676414289fd8d199b5aeaef4224c59` |
| 15 | No | Bounded lifecycle/resource counts; coverage only | No production commit |

Issue 11 follow-up `16ebf391afab4802b391df56f10542661be85c98` restores the original Delete glyph after a command-pipe encoding mistake and adds a literal-label assertion (6 focused assertions now). It was pushed and origin-confirmed after 65 relevant checks passed. Final test/report commit retains Issues 9/15 and integrated coverage; its SHA is supplied in the handoff.

## Issue 6 — cooperative cancellation

Reproduced: yes. The existing Cancel control was disabled throughout a long Standard export; clicking it did not stop rendering or download (1/1 baseline assertion). Fix: optional AbortSignal per renderer export, checked at safe progress/draw boundaries, and abort-aware asynchronous waits which detach their listener and reject once. The existing App Cancel button now aborts its controller. AbortError produces canceled status, no success toast/download, restores the complete session/VBOs, clears flags/token/waiter and removes display hold. Context loss retains precedence over ordinary abort and Issue 2 owns reconstruction.

Files: `renderer.js`, `app.js`, `hardening_test_helpers.js`, `test_issue6_cancellation.html`, this report. Tests cover Standard and full Master 120/240, each canceled at initialization, early development, 25%, 50%, 90%, and PNG encoding; late encoder callbacks, full VBO equality, session equality, all temporary GPU resource types, actual Cancel control, and immediate successful next export. Previous Issues 4/5, context loss, display hold and Master are rerun. Final assertion count and commit are entered in the ledger.

Issue 5 pushed and confirmed at origin/main: `b7974f5f5eed3a1fee93a7bfc1c0ccf5055fac75`.

## Issue 7 — real background-tab progress

Reproduced: yes, with actual Chrome tabs and `document.hidden=true`, not only a visibility mock. Standard progress stayed at 29% from one to four seconds hidden; Master stayed at 9%. Bringing the original tab forward resumed both. Fix: the two export cooperative yields now use cancelable zero-delay timer tasks, leaving foreground App RAF and tab visibility rendering policy unchanged. Native hidden-tab timer throttling can still slow progress, and browser/OS suspension cannot be overcome by a page scheduler.

After the fix, observed hidden progress advanced Standard 66% -> 85% and Master 18% -> 22% across the same interval, with decoded outputs identical to foreground controls. The expanded real-tab fixture additionally checks cancellation and actual context loss/recovery while hidden. Files: `renderer.js`, `test_issue7_background.html`, `run_issue7_background.py`, this report. Cancellation, snapshot isolation, full VBO equality and context recovery suites are rerun.

Issue 6 pushed and confirmed at origin/main: `827fbed17deedb663902baa3b284042d8e25a5ba` (77 new cancellation assertions, 289 relevant assertions total).

## Issue 8 - allocation failure safety

Reproduced ten unsafe paths across Standard/Master: ignored texture/viewport limits, partial texture/FBO leaks, ignored texture allocation errors, and a failed second Master backup buffer that still downloaded and corrupted live VBO state. Baseline fixture classified 25/25 cases. Fix: validate requested dimensions against real texture and viewport limits, track every temporary handle at creation (including partial array allocations), check actual GL allocation/readback errors and backup buffer sizes, and reject unavailable 2D canvas contexts. Cleanup restores healthy live resources before releasing the export allocation scope; context loss still belongs to Issue 2. No VRAM estimate or resolution/pass reduction.

Files: renderer.js, test_issue8_allocations.html, this report. Forced failures at twelve stages per export path now reject clearly with exact session/VBO restoration and zero temporary handles/downloads. A final successful export proves continued usability (25/25). Previous cancellation, snapshot, VBO, Master and context/rebuild suites pass.

Issue 7 pushed and confirmed: `26902b7eb294c781f3a22a0a8122481a8131fcf0` (16 real-tab assertions; 284 relevant assertions total).

## Issue 9 - PNG encoding audit

Already protected; no production change required and no dedicated commit, as requested. New test_issue9_encoding.html exercises actual App Standard/Master failures for null callback, zero-byte Blob, encoder throw and actual context loss, including late callbacks. All 26 assertions pass: no 100%, success toast or download; flags/waiters clear, healthy context restores full session/VBOs, lost context recovers Explore without auto-restarting export. Relevant allocation/cancel/context suites also pass (240 assertions total). Coverage is retained in the final test/report commit.

Issue 8 pushed and confirmed: `2a99087aa21c017ee6317c5630c1647c221c5bb8` (496 relevant assertions).

## Issue 10 - hostile preset validation

Reproduced: 41 unsafe payloads were accepted, mutated state or reached unsafe roots generation. The baseline test stops invalid n before actually allocating a billion roots; it records reaching that loop, not an intentional machine hang. Root cause: unvalidated deserialization and visual-field assignment, boolean coercion and unbounded import size. Fix: shared small validator runs before any mutation in App loading and direct MathSystem.fromJSON. Supported imported Explore symmetry is integer 1-64; complex components -1000 to 1000; finite drift time 0-1e9; zoom 0.3-500; center components -1e6 to 1e6; boolean/coordinate structure, palette/tier/view whitelists and metadata types/lengths checked. Missing optional fields and valid partial/legacy presets remain supported. Unknown metadata is ignored by the loaders, never merged into runtime objects. Reference ignores imported math/framing/palette and resets canonically, while applied rendering fields still validate. File imports above 1 MiB are rejected before reading and error messages identify the invalid field.

Files: preset_validation.js, math.js, app.js, test_issue10_presets.html, this report. Fifty focused assertions plus Reference invariant, modes/exports, input isolation and context recovery pass (222 total).

## Issue 11 - preset markup injection

Reproduced: harmless image onerror payloads executed from user preset names and stored symmetry labels. Root cause: user-controlled values interpolated into row.innerHTML. Fix: create row elements and assign name/symmetry through textContent, retaining existing styling and Load/Delete behavior. Descriptions are not rendered in user rows; curated descriptions are static internal markup. Imported names, errors and toast messages use innerText; filenames only become download attributes, never HTML.

Files: app.js, test_issue11_metadata.html, this report. Baseline 1/1; post-fix 5/5 including literal text, no image/SVG execution, imports/toasts and existing handlers. Previous preset validation, Reference invariant and modes/export tests pass (96 total).

Issue 10 pushed and confirmed: `9dc300b8c6f31d445a747f79223d267e6bf295b2`.

## Issue 12 - stochastic randomizer stability

No functional instability reproduced; production ranges unchanged. test_issue12_randomizer.html uses fixed PRNG seed 0x12adbeef, 1000 consecutive generations per family (including cumulative subtle mutations). Every state checks integer supported symmetry, finite roots/base/effective/inverse/second-iterate transforms, finite CPU orbit evaluation and math.update, determinant range, real GPU simulation/deposits, finite particle readback, GL errors and zero new handles. Each case uses 1024 particles, four 16-step frames at 64-square display, with accumulation reset and particle seed reset; this is a broad transform stress sample, not a full-tier performance benchmark.

6006 assertions pass, zero blank or near-all-white cases, observed determinant magnitude 0.22889-1.81838. Initial isolated run, per-family end-sample metrics (divergence >radius5; respawn proxy age<50; out-of-view based on camera clip bounds):

| Family | Divergence rate | Age<50 rate | Out of view | Max case CPU + GPU readback ms |
|---|---:|---:|---:|---:|
| conradi-like | 0.00004590 | 0.00177930 | 0.00402344 | 127.9 |
| subtle | 0.00001660 | 0.00054590 | 0.00081348 | 10.3 |
| organic | 0.00007129 | 0.00218066 | 0.00534473 | 12.9 |
| dense lace | 0.00004102 | 0.00293066 | 0.00341699 | 11.6 |
| symmetric | 0.00003418 | 0.00302832 | 0.00419922 | 10.5 |
| chaotic | 0.00008594 | 0.00523535 | 0.00688574 | 10.2 |

No cases exceeded 250 ms. Timings include synchronous readback and are not isolated GPU timer measurements. No JS heap/VRAM stability claim. Reference transition is canonical after every family. Previous math, Reference, modes/export, preset validation and metadata suites pass: 6107 assertions total. Files: test_issue12_randomizer.html, test_math_reporting.html (report adapter for existing unchanged five math tests), this report.

Issue 11 pushed and confirmed: `aad0528c2d88b28faecbc16df8be5fb92264a47d`.

## Issue 13 - startup/capability failures

Reproduced six unsafe startup paths. Missing WebGL2, shader compile, program link, FBO creation and incomplete FBO left an uncaught exception with no explanation. Injected particle storage failure was accepted with a running RAF and unusable buffers. Existing float-extension absence uses RGBA8; missing float blend uses RGBA16F; missing linear/timer-query extensions are already safe.

Fix: bootstrap catches initialization failure once, keeps HTML present, shows a readable role=alert error and marks graphics unavailable instead of a false Reference status. Renderer validates actual initial particle allocation errors and buffer size before VAO use; constructor cleanup releases failed partial initialization. No alternate renderer/reload/retry loop. Files: app.js, renderer.js, test_issue13_startup.html, this report. Six fatal faults and four fallback cases pass (16 assertions), with no uncaught exceptions, no partial RAF, and zero residual tracked handles on fatal paths. Context loss/rebuild retry, canonical Reference, Master and allocation regressions pass (265 total).

Issue 12 pushed and confirmed: `7717876c3cf4bfeff1ae51228d15f8db36db45ea`.

## Issue 14 - application transactions

Reproduced two defects: an earlier successful export's delayed 700 ms callback re-enabled Start during a subsequent export; direct App.togglePause enabled the evolving flag in Reference despite UI guards. Fix: own/cancel the completion timer when starting/reopening export or losing context, and enforce Reference pause protection in the API itself. Files: app.js, test_issue14_transactions.html, this report. Baselines 1/1 each; focused final 47/47; relevant cancellation, isolation, PNG, display hold, preset, Reference and loss/retry regressions pass (444 total).

Intentional transaction boundaries:

- Healthy export success/failure/cancel restores start math (all own fields), camera/aspect, presentation, quality/adaptive state, overrides, both full VBOs/index, accumulation handles/pixels/counters and Reference exposure. App export flags/token/waiter clear. Successful download/progress is intentional; display hold leaves after frame/fallback, cancellation removes it immediately. Attempted live input during export is discarded.
- Context loss retains the JavaScript mathematical/session choices and quality mode, interrupts export without auto-restart, and replaces every GL resource. Accumulation/particle bytes, exposure progress and adaptive timing measurements intentionally restart. Reference is re-canonicalized; Explore math is preserved. One RAF and the existing handlers survive.
- Preset loading intentionally applies validated fields; missing fields keep existing legacy behavior. Mode switch to Reference establishes all canonical math/framing/palette; Explore enables disturbances. Reset in Explore clears time/offset/pointer/shock and smoothly targets canonical framing, retaining the selected base organism and mode. Reset in Reference performs the canonical reset.

The snapshot suite checks both modes and both export types through success, failure, cancel and actual context loss, including full particle bytes and accumulation hash when healthy, plus UI mode/readout, aspect, persistence, overrides and exposure keys.

Issue 13 pushed and confirmed: `6ab434e90be964e4284c0637e9868c91e109400c`.

## Issue 15 - long lifecycle/resource counts

No resource leak reproduced; no production change or dedicated Issue 15 commit required. test_issue15_lifecycle.html runs 32 cycles, each with natural Reference settle/idle, protected Reference inputs, Explore randomization, Standard success/cancel, Master cancel/success, preset/mode transitions, resize/quality changes and actual context loss with one or two forced failed clean rebuilds. Full Master image size is retained; successful Master stress exports use one pass to bound repeated test cost, while Master cancellation uses the 120-pass path and separate suites cover full 120/240 exports.

290/290 assertions pass; 48 failed reconstruction attempts recover. Every cycle returns to identical live handle counts: 4 buffers, 4 textures, 4 FBOs, 6 VAOs, 6 programs, 12 attached shaders and 268 profiler queries. Browser context loss releases its old GL generation; failed healthy reconstruction and temporary export resources are explicitly deleted. Canvas count stabilizes at two (artwork plus reused hidden display hold), handlers unchanged, one pending App RAF, no export waiter or retry timer after recovery, zero GL calls while lost. At cycle boundaries in the final full run, the highest observed active timer count was 13 and object URL count was 12 during intentional delayed revocation; after the 10-second grace interval both drain to zero. No monotonic tracked-handle growth. JS heap and driver GPU memory were not measured. Files: test_issue15_lifecycle.html, this report (included in final verification commit).

## Integrated adversarial sequence

39/39 assertions pass in one session: partial Reference development, quality change and settle, Standard export, Explore/randomize, long Standard input interference/cancel, immediate successful retry, hostile presets and markup, actual hidden-tab Master export, context loss, a forced failed renderer rebuild and clean retry while hidden, visible resume without export restart, 24 rapid mode/quality/resize/preset/reset transitions, final canonical Reference and explicit successful export. One RAF and unchanged handlers throughout. The test waits for the asynchronous context-loss event before checking App.contextLost. Files: test_integrated_hardening.html, run_integrated_hardening.py.

Issue 14 pushed and confirmed: `9581598eec676414289fd8d199b5aeaef4224c59`.

## Verification limits and legacy diagnostic

Validation uses Windows Chrome with ANGLE/D3D11. No claim of cross-device/browser coverage, JS heap stability or driver VRAM measurement. Randomizer timing includes readback; repeated lifecycle exports use bounded test workloads as stated above. Actual 4096-square dimensions, Master 120/240 workload, output hashes and full live particle isolation are independently covered. Hidden-tab timers may be throttled; OS/browser page suspension pauses execution. Existing rebuild retry remains bounded and cannot guarantee recovery from persistent hardware/allocation failure.

The unchanged test_adaptive.html was also rerun as an observational diagnostic. All 43 boolean observations match the pre-pass baseline. Five obsolete Standard-only expectations remain false at healthy higher tiers: settled.workloadBounded, interaction.duringInteraction.reducedLoad, interaction.afterInteraction.returnedToSettled, deepZoom.noWorkloadExplosion and deepZoom.preservedTier. afterInteraction.isInteracting=false is expected. Current tier-aware budget/promotion tests pass. The diagnostic emits an object rather than assertion results; its one adapter-completion record is excluded from the regression assertion total. No production tier policy was changed to satisfy outdated expectations.

## Final full regression

**7049 / 7049 assertions passed**, including all current Issues 1-15 regression coverage and the integrated sequence. Counts exclude baseline classification runs, intermediate/repeated runs and the legacy adaptive diagnostic completion record.

| Suite | Passed assertions |
|---|---:|
| test_issue1_reference_invariant.html | 9 |
| test_issue2_context_loss.html | 112 |
| test_issue2_rebuild_retry.html | 93 |
| test_issue3b_tier_budgets.html | 54 |
| test_issue4_particle_isolation.html | 60 |
| test_issue5_input_isolation.html | 19 |
| test_issue6_cancellation.html | 77 |
| test_issue8_allocations.html | 25 |
| test_issue9_encoding.html | 26 |
| test_issue10_presets.html | 50 |
| test_issue11_metadata.html | 6 |
| test_issue12_randomizer.html | 6006 |
| test_issue13_startup.html | 16 |
| test_issue14_transactions.html | 47 |
| test_issue15_lifecycle.html | 290 |
| test_math_reporting.html | 5 |
| test_modes_and_exports.html | 32 |
| test_reference_master.html | 10 |
| test_export_display_hold.html | 11 |
| test_export_failure_and_edge_cases.html | 3 |
| Issue 3 | 43 |
| Issue 7 real background | 16 |
| integrated hardening | 39 |
| **Total** | **7049** |

The Issue 3 five-real-minute idle test confirms pixel-identical compositor output and zero expensive GPU work, with one RAF, unchanged handlers and no timers. Full Master 120/240 exports still execute every requested pass at 4096-square resolution.

Final syntax/compile checks pass for all six production JS modules, three JS fixture helpers, thirteen new HTML module scripts and all 84 root Python files. git diff --check and staged diff checks pass. Validation output is retained locally in final_regressions.log, final_reference_idle.log, final_background.log, final_integrated.log, final_adaptive.log and final_syntax.log (ignored test artifacts). Re-run browser fixtures through run_browser_regressions.py; Issue 3, real background tabs and integrated sequence use run_issue3_regressions.py, run_issue7_background.py and run_integrated_hardening.py respectively.

All production changes were pushed separately as recorded above. Final coverage/report is committed after passing verification; the final origin/main SHA and clean working-tree confirmation are in the handoff. No further product/UI work is started.
