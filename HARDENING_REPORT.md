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
