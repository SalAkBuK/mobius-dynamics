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
