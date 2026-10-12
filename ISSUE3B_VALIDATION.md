# Issue 3B: tier-aware live Reference exposure

Baseline: `54d6ad522f8705a6c1abd9fcd2063268221ea6ed`. Scope is Issue 3B only.

## Measurement before changing production

All 56 combinations (seven tiers, eight candidate budgets) were captured from actual live RAF rendering before changing `renderer.js`. [Full measurements](ISSUE3B_MEASUREMENTS.md) include actual wall time, accumulation frames, attempted deposits, brightness, lit/ring/peripheral-web coverage, and whole/web/central local correlation against each tier's own 16,384 dpp image. [Screenshot comparison](ISSUE3B_MEASUREMENTS.jpg) contains all 56 unadjusted thumbnails. Full 1200 x 800 PNGs and raw JSON remain locally in `issue3b_potato/` and `issue3b_candidates/`; these follow the repository's ignored-artifact convention.

Chrome headless, ANGLE D3D11, 1200 x 800, DPR 1, approximately 60 actual renders/s. Potato ran alongside the other sequential tier measurements in an isolated Chrome session. Times include screenshot overhead. These are observed wall times, not estimates or accelerated RAF runs. No power or thermal measurements were taken; deposit counts establish the reduction in total live work.

The existing Issue 3 timeline showed essentially the same structure at matching elapsed exposures: Potato at 30 seconds is near the 256 dpp candidate, and Low at 60 seconds is just beyond 2048 dpp. The previous 16,384 dpp policy required Potato 1639.89 seconds and Low 438.27 seconds in this new measurement. Standard required 219.5 seconds. A project's existing `preview.png` was inspected as a qualitative framing/structure reference; it is not an independently authenticated Simone target and was not used for numeric correlation.

## Visual choice

Potato at 256 dpp exposes the major pattern but has substantially less peripheral sampling (17.78% web coverage). At 512 dpp the 16-fold structure, central lace, and recognizable outer web are clear; ring coverage reaches 97.69% and web coverage 33.56%. Moving Potato to 1024 dpp doubles its development to 102.78 seconds for 52.18% web coverage. The 512 dpp choice deliberately retains less microscopic peripheral detail while producing a usable inexpensive preview in about 51 seconds.

Low at 2048 dpp gives 100% ring coverage and 72.75% peripheral-web coverage, with web local correlation 0.8113 and central correlation 0.7960 against its 16,384 dpp result. At 4096 dpp the web is denser (87.76%) but development doubles to 109.92 seconds. The lower target preserves the major geometry, outer web and internal lace while meeting the lightweight preview goal.

The lower exposures are both darker and less densely sampled in the faintest filaments. They are not equivalent images with only brightness changed. Potato mean luma is 35.18 versus 104.63 at 16,384 dpp; Low is 58.14 versus 105.50. The high exposure also brightens/clips the core, which lowers some central local correlations even when the same lace geometry remains visible. Brightness, coverage, correlation and visual inspection are therefore reported separately. No gain normalization was needed or applied.

Standard 4096, High 8192, and Ultra 12288 progressively retain more faint detail; Extreme and Brute Force keep the existing maximum exposure. At equal exposure, the screenshots across tiers show the same large-scale structure. Quality remains a refinement tradeoff, with Reference Master providing the archival path.

## Final policy and measured production completion

Target deposits are deposits-per-pixel times the actual accumulation area, with at most one live frame of overshoot. Workloads per frame and resolution policies are unchanged.

| Quality | Target dpp | Actual settle seconds, 1200 x 800 / DPR 1 |
|---|---:|---:|
| Potato | 512 | 51.32 |
| Low | 2048 | 54.59 |
| Standard | 4096 | 54.61 |
| High | 8192 | 65.52 |
| Ultra | 12288 | 49.15 |
| Extreme | 16384 | 41.32 |
| Brute Force | 16384 | verified naturally in the 320 x 240 regression |
| Auto | 512 through 16384, validated high-water mark | 41.90 (16384 dpp earned) |

Final manual samples are in `issue3b_verified/measurements.json`; standalone Auto is in `issue3b_auto_verified/measurements.json`. Manual timing overlapped the regression rerun: render rates were about 60/s except Extreme at 53.79/s during concurrent full-resolution export work. Auto was rerun alone after those exports and reached Extreme exposure naturally. The first concurrent Auto measurement correctly settled below the helper's requested 16,384 dpp candidate; that helper rejected the unmet candidate rather than fabricating a time. The new `--settled` option captures the actual adaptive completion target and avoids assuming that Auto always earns the maximum under load.

Potato now settles in 51.32 seconds instead of 1639.89 seconds (27.33 minutes); Low in 54.59 seconds instead of 438.27 seconds (7.30 minutes). Potato performs 1/32 of the former target work (96.875% less), and Low 1/8 (87.5% less). Standard performs 1/4, High 1/2, and Ultra 3/4. Actual overshoot is recorded in the measurement JSON. Wall times vary with hardware, browser scheduling and accumulation dimensions; these are finite work budgets, not a universal time guarantee.

## Quality changes and Auto

Quality and workload changes no longer invalidate accumulated photons. Low settled -> High resumes until the higher target is satisfied. High settled -> Low retains the better image and stays idle. Changes during development keep the existing accumulation and count toward the new target. Camera/dimension changes, explicit Reference reset and context reconstruction still start a fresh exposure when resources or geometry require it.

Auto starts at 512 dpp during calibration. The target increases monotonically to the highest validated tier for the current exposure, capped at 16,384. A provisional promotion uses its previously validated tier until validation completes; a failed trial cannot permanently assign a weak device the trial tier's budget. Weak Auto can settle at Potato/Low exposure. Calibration or active validation finishes before idling unless the maximum exposure has already been reached. Even repeated promotion/demotion cannot extend development beyond that maximum. A fresh exposure resets the high-water mark. A manual quality selection uses its own target while retaining photons; returning to Auto restores its earned high-water mark for that exposure.

The tier regression exposed an existing profiler metadata mismatch on an initial downshift: `beginFrame()` remembered the earlier workload's step count before adaptive workload selection. It then queried unsubmitted timers and raised `INVALID_OPERATION`. The renderer now updates that frame's query count to the actual selected steps before submitting passes. Timing architecture and rendering work are otherwise unchanged.

## Regression evidence

Final results: **372/372 regression assertions pass**: 270 established Issue 1/2 and export assertions, five math assertions, 43 Issue 3 assertions, and 54 new tier-budget assertions. All run against the final production renderer. The five-minute compositor captures are pixel-identical; all individually traced GL calls in the tier suite produce zero errors. Reference Master 120/240 exports execute 1,920/3,840 splats and 1,981/3,901 simulation passes (including the existing 61 warmup steps), preserving requested 4096-square PNG dimensions, the settled live exposure and display-hold cleanup.

The new tier suite naturally reaches all seven manual budgets, independently counts actual splat deposits, checks zero GL commands and identical pixels at rest, verifies retained photons during quality changes, exercises natural and adversarial Auto promotion, performs real context loss/restoration followed by fresh Low development, and validates a settled Low Standard export. It audits canonical Reference state, one RAF chain, handler/timer cleanup and every GL error after individual calls.

The Issue 3 suite includes five actual minutes of idle compositor screenshots with pixel identity, zero draws/queries/simulation/bloom work, unlimited-exposure comparison, genuine geometry wakes, cached presentation updates, Explore transitions, context restoration, Standard export and full 4096 x 4096 Reference Master exports at 120 and 240 passes. Master executes all requested work regardless of the live exposure budget. The established Issue 1/2, mode/export, Master, display-hold and failure suites are rerun, together with the five math assertions.

The Standard and Reference Master export implementations are byte-identical to baseline main. `app.js`, canonical math, camera, palette, bloom, gain, tonemapping, quality definitions, Explore rendering, recovery architecture and UI were not changed. Node syntax, Python compilation, HTML module syntax and `git diff --check` are also checked.

The older object-reporting `test_adaptive.html` diagnostic was also executed, both against the final code and an isolated archive of baseline main. Its boolean results match baseline exactly. Five historical expectations remain false in both: the former Standard-only workload ceiling, interaction reduction below Standard, return specifically to Standard, the old deep-zoom ceiling, and preservation specifically of Standard. These predate the existing High/Ultra/Extreme promotion ladder and are not treated as new passing assertions. Actual tier deposit budgets, manual tiers, promotion/rollback, calibration ceiling, full ladder and query distinction report success. The diagnostic's completion marker is excluded from the regression assertion total.

## Reproduction

The complete pre-change candidate capture requires baseline main's 16,384 dpp policy. Apply only the measurement helper changes to that baseline; the finished production policy correctly stops before larger candidate budgets on lower tiers.

```powershell
python -u measure_issue3.py --tiers potato --budgets 256,512,1024,2048,4096,8192,12288,16384 --output issue3b_potato
python -u measure_issue3.py --tiers low,standard,high,ultra,extreme,auto --budgets 256,512,1024,2048,4096,8192,12288,16384 --output issue3b_candidates
python analyze_issue3b.py issue3b_potato issue3b_candidates
python -u measure_issue3.py --tiers potato,low,standard,high,ultra,extreme,auto --settled --output issue3b_verified
python -u run_browser_regressions.py test_issue3b_tier_budgets.html --timeout 600
python -u run_issue3_regressions.py
python -u run_browser_regressions.py test_issue2_rebuild_retry.html test_issue2_context_loss.html test_issue1_reference_invariant.html test_modes_and_exports.html test_reference_master.html test_export_display_hold.html test_export_failure_and_edge_cases.html
```

`test_math_units.html` exposes its five results via `window._testsCompleted` rather than HTTP POST. It was run through a temporary iframe adapter that POSTed its unchanged JSON results to the same browser runner; the adapter was removed afterward. Python measurement analysis requires Pillow and NumPy; the Issue 3 compositor runner also requires websocket-client.
