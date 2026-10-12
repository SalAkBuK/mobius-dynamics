# Functionality hardening, Issues 5–15

Starting origin/main: `7078f94d59f5c988070e677ff08d80957d290619`.
Each issue is reproduced/audited before its production changes, tested and pushed separately.
This report is updated as the ordered pass proceeds. No UI redesign or artwork changes.

## Issue 5 — export snapshot versus live input

Reproduced: yes. Before production changes, a seeded 96 x 64, 30-pass Standard control was compared with interference at each of three chunk progress callbacks. Fourteen of fifteen initial mutators changed decoded pixels: mode, randomize, symmetry, coefficients, palette, camera, bloom, view, gain, clear, reset, pause, keyboard and DOM mode controls. Quality alone left export pixels equal but changed live quality. Reproduction: `test_issue5_input_isolation.html?baseline=1` on the starting main with the test additions only (16/16 classification assertions).

Root cause: export read mutable live math and display settings after asynchronous yields, and clear/reset could clear its temporary targets. Fix: immutable mathematical/pixel inputs, prototype-preserving complete math/session snapshots restored in `finally`, protection of clear/transition entry points, and an export input guard for application commands and DOM events. Direct math/renderer/adaptive field interference is independently covered, so correctness does not rely on disabled controls. Inputs attempted during export are discarded; the transaction restores the start session. Geometry resources and live VBO isolation retain the existing architecture.

Files: `renderer.js`, `app.js`, `hardening_test_helpers.js`, `test_issue5_input_isolation.html`, this report. New checks cover sixteen mutators, Master control/interference decoded pixel equality, full session restoration and ordinary failure. Previous Issue 4 output hashes/VBO continuation, Issue 2 loss during develop/encoding, Master and mode/export checks pass. Reference/tier/rebuild retry checks pass before commit; 389 relevant assertions pass in total (the final 19-assertion Issue 5 run supersedes its earlier 16-assertion run). Commit and origin confirmation are recorded in the final table.

## Commit and verification ledger

The final consolidated ledger and integrated totals will be filled after all issues complete.

## Issue 6 — cooperative cancellation

Reproduced: yes. The existing Cancel control was disabled throughout a long Standard export; clicking it did not stop rendering or download (1/1 baseline assertion). Fix: optional AbortSignal per renderer export, checked at safe progress/draw boundaries, and abort-aware asynchronous waits which detach their listener and reject once. The existing App Cancel button now aborts its controller. AbortError produces canceled status, no success toast/download, restores the complete session/VBOs, clears flags/token/waiter and removes display hold. Context loss retains precedence over ordinary abort and Issue 2 owns reconstruction.

Files: `renderer.js`, `app.js`, `hardening_test_helpers.js`, `test_issue6_cancellation.html`, this report. Tests cover Standard and full Master 120/240, each canceled at initialization, early development, 25%, 50%, 90%, and PNG encoding; late encoder callbacks, full VBO equality, session equality, all temporary GPU resource types, actual Cancel control, and immediate successful next export. Previous Issues 4/5, context loss, display hold and Master are rerun. Final assertion count and commit are entered in the ledger.

Issue 5 pushed and confirmed at origin/main: `b7974f5f5eed3a1fee93a7bfc1c0ccf5055fac75`.

## Issue 7 — real background-tab progress

Reproduced: yes, with actual Chrome tabs and `document.hidden=true`, not only a visibility mock. Standard progress stayed at 29% from one to four seconds hidden; Master stayed at 9%. Bringing the original tab forward resumed both. Fix: the two export cooperative yields now use cancelable zero-delay timer tasks, leaving foreground App RAF and tab visibility rendering policy unchanged. Native hidden-tab timer throttling can still slow progress, and browser/OS suspension cannot be overcome by a page scheduler.

After the fix, observed hidden progress advanced Standard 66% -> 85% and Master 18% -> 22% across the same interval, with decoded outputs identical to foreground controls. The expanded real-tab fixture additionally checks cancellation and actual context loss/recovery while hidden. Files: `renderer.js`, `test_issue7_background.html`, `run_issue7_background.py`, this report. Cancellation, snapshot isolation, full VBO equality and context recovery suites are rerun.

Issue 6 pushed and confirmed at origin/main: `827fbed17deedb663902baa3b284042d8e25a5ba` (77 new cancellation assertions, 289 relevant assertions total).

## Issue 8 ? allocation failure safety

Reproduced ten unsafe paths across Standard/Master: ignored texture/viewport limits, partial texture/FBO leaks, ignored texture allocation errors, and a failed second Master backup buffer that still downloaded and corrupted live VBO state. Baseline fixture classified 25/25 cases. Fix: validate requested dimensions against real texture and viewport limits, track every temporary handle at creation (including partial array allocations), check actual GL allocation/readback errors and backup buffer sizes, and reject unavailable 2D canvas contexts. Cleanup restores healthy live resources before releasing the export allocation scope; context loss still belongs to Issue 2. No VRAM estimate or resolution/pass reduction.

Files: renderer.js, test_issue8_allocations.html, this report. Forced failures at twelve stages per export path now reject clearly with exact session/VBO restoration and zero temporary handles/downloads. A final successful export proves continued usability (25/25). Previous cancellation, snapshot, VBO, Master and context/rebuild suites pass.

Issue 7 pushed and confirmed: `26902b7eb294c781f3a22a0a8122481a8131fcf0` (16 real-tab assertions; 284 relevant assertions total).

## Issue 9 ? PNG encoding audit

Already protected; no production change required and no dedicated commit, as requested. New test_issue9_encoding.html exercises actual App Standard/Master failures for null callback, zero-byte Blob, encoder throw and actual context loss, including late callbacks. All 26 assertions pass: no 100%, success toast or download; flags/waiters clear, healthy context restores full session/VBOs, lost context recovers Explore without auto-restarting export. Relevant allocation/cancel/context suites also pass (240 assertions total). Coverage is retained in the final test/report commit.

Issue 8 pushed and confirmed: `2a99087aa21c017ee6317c5630c1647c221c5bb8` (496 relevant assertions).

## Issue 10 ? hostile preset validation

Reproduced: 41 unsafe payloads were accepted, mutated state or reached unsafe roots generation. The baseline test stops invalid n before actually allocating a billion roots; it records reaching that loop, not an intentional machine hang. Root cause: unvalidated deserialization and visual-field assignment, boolean coercion and unbounded import size. Fix: shared small validator runs before any mutation in App loading and direct MathSystem.fromJSON. Supported imported Explore symmetry is integer 1?64; complex components ?1000; finite drift time 0?1e9; zoom 0.3?500; center components ?1e6; boolean/coordinate structure, palette/tier/view whitelists and metadata types/lengths checked. Missing optional fields and valid partial/legacy presets remain supported. Unknown metadata is ignored by the loaders, never merged into runtime objects. Reference ignores imported math/framing/palette and resets canonically, while applied rendering fields still validate. File imports above 1 MiB are rejected before reading and error messages identify the invalid field.

Files: preset_validation.js, math.js, app.js, test_issue10_presets.html, this report. Fifty focused assertions plus Reference invariant, modes/exports, input isolation and context recovery pass (222 total).
