# Issue 3: live Reference development and rest

Historical validation for commit `54d6ad5`. The shared exposure policy below is superseded by [Issue 3B](ISSUE3B_VALIDATION.md), which scales total preview refinement by tier and retains photons across quality changes.

Baseline: `7e93c9e88eaeba920deb5ccb3e537f63b2983b0e`. Measured before production edits on Windows, Chrome headless, ANGLE D3D11, 1200 x 800 canvas, DPR 1. Each quality mode ran alone from a fresh load for 60 real seconds. No formulas, coefficients, camera, quality definitions, shaders, photon intensity, tonemapping, resolution, or export rendering changed.

## Baseline measurements

Every sample had identical Reference math and camera state. Simulation and splat rates are equal; each simulation pass has one matching splat pass. Deposits are attempted splat vertices, including shader-discarded warmup/out-of-view points. GPU time is the existing asynchronous timer-query metric, not system GPU utilization or power. Render rate excludes screenshot-only cached presentations. Blue mean and lit coverage use the actual 8-bit final composite; lit means blue > 16/255.

Captures briefly synchronously read the final framebuffer, so the measured rates include that sampling overhead. This machine has NVIDIA RTX 4070 Laptop and Intel UHD adapters; the runs used Chrome's ANGLE D3D11 selection, without forcing a specific adapter.

| Tier | Seconds | Particles | Steps | Deposits/frame | GPU ms | Frame ms | FPS | Accumulation frames | Renders/s | Simulations/s (=splats/s) | Mean blue /255 | Lit coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| potato | 2 | 40,000 | 4 | 160,000 | 0.49 | 16.6 | 60 | 117 | 58.3 | 233.1 | 22.0 | 29.2% |
| potato | 5 | 40,000 | 4 | 160,000 | 2.97 | 16.7 | 60 | 296 | 58.4 | 233.6 | 32.8 | 38.3% |
| potato | 10 | 40,000 | 4 | 160,000 | 4.74 | 16.6 | 60 | 590 | 58.0 | 232.0 | 42.7 | 43.8% |
| potato | 20 | 40,000 | 4 | 160,000 | 3.34 | 16.6 | 60 | 1,184 | 59.0 | 236.1 | 54.4 | 49.4% |
| potato | 30 | 40,000 | 4 | 160,000 | 2.06 | 16.7 | 60 | 1,777 | 58.8 | 235.2 | 62.2 | 53.6% |
| potato | 60 | 40,000 | 4 | 160,000 | 3.35 | 16.7 | 60 | 3,568 | 59.5 | 238.1 | 77.4 | 62.7% |
| low | 2 | 75,000 | 8 | 600,000 | 3.34 | 16.6 | 60 | 121 | 59.8 | 478.4 | 38.4 | 41.6% |
| low | 5 | 75,000 | 8 | 600,000 | 3.14 | 16.6 | 60 | 295 | 56.7 | 453.9 | 53.1 | 48.8% |
| low | 10 | 75,000 | 8 | 600,000 | 2.95 | 16.9 | 59 | 589 | 57.8 | 462.5 | 66.7 | 56.2% |
| low | 20 | 75,000 | 8 | 600,000 | 3.03 | 16.6 | 60 | 1,182 | 58.9 | 471.1 | 82.6 | 66.2% |
| low | 30 | 75,000 | 8 | 600,000 | 3.53 | 16.4 | 61 | 1,774 | 58.7 | 469.9 | 92.4 | 72.6% |
| low | 60 | 75,000 | 8 | 600,000 | 3.19 | 16.6 | 60 | 3,567 | 59.6 | 476.6 | 109.4 | 83.5% |
| standard | 2 | 150,000 | 8 | 1,200,000 | 2.94 | 16.8 | 60 | 121 | 59.9 | 479.6 | 49.1 | 46.8% |
| standard | 5 | 150,000 | 8 | 1,200,000 | 6.04 | 16.8 | 60 | 295 | 56.2 | 449.2 | 66.8 | 56.2% |
| standard | 10 | 150,000 | 8 | 1,200,000 | 4.87 | 16.6 | 60 | 587 | 57.5 | 459.7 | 82.4 | 66.0% |
| standard | 20 | 150,000 | 8 | 1,200,000 | 5.28 | 16.7 | 60 | 1,179 | 58.7 | 469.7 | 99.5 | 77.4% |
| standard | 30 | 150,000 | 8 | 1,200,000 | 4.51 | 16.6 | 60 | 1,772 | 58.8 | 470.3 | 109.3 | 83.8% |
| standard | 60 | 150,000 | 8 | 1,200,000 | 3.34 | 16.7 | 60 | 3,563 | 59.5 | 476.0 | 126.2 | 92.9% |
| auto | 2 | 250,000 | 8 | 2,000,000 | 5.04 | 16.6 | 60 | 122 | 60.4 | 483.3 | 52.8 | 48.6% |
| auto | 5 | 400,000 | 10 | 4,000,000 | 8.78 | 16.8 | 60 | 296 | 56.3 | 463.6 | 77.1 | 62.6% |
| auto | 10 | 589,824 | 12 | 7,077,888 | 8.31 | 16.7 | 60 | 588 | 57.5 | 614.2 | 108.3 | 83.4% |
| auto | 20 | 589,824 | 12 | 7,077,888 | 8.61 | 16.6 | 60 | 1,179 | 58.7 | 704.5 | 135.5 | 97.0% |
| auto | 30 | 589,824 | 12 | 7,077,888 | 8.13 | 16.7 | 60 | 1,772 | 58.8 | 705.1 | 147.7 | 99.3% |
| auto | 60 | 589,824 | 12 | 7,077,888 | 8.53 | 16.8 | 60 | 3,564 | 59.6 | 714.8 | 167.1 | 100.0% |

At 60 seconds all four modes still performed full GPU work. Accumulation grew monotonically to approximately 3,560 frames. Auto reached Extreme (589,824 x 12) without changing the mathematical state.

## Visual timeline and later unlimited exposure

The bright skeleton is visible at 2 seconds. Five seconds is insufficient, particularly on Potato: thin outer filaments and internal lace continue becoming visible through 10, 20, 30, and 60 seconds. For Potato, mean blue rises from 21.98 at 2 seconds to 77.42 at 60 seconds; outer-annulus lit coverage rises from 37.41% to 98.42%. For Low, mean blue rises from 38.36 to 109.4. Changes do **not** become negligible in absolute brightness within this baseline interval.

An additional untouched production Auto session ran for 360 seconds, capturing 30/60/90/180/360 seconds. At 90 seconds it had attempted 37.11 billion deposits (38,653/pixel); at 180 seconds 75.26 billion; at 360 seconds 151.66 billion. It still executed about 720 simulation/splat passes per second. Later images brighten existing outer filaments and increasingly wash out internal lace and the central region. Unlimited integration is not a stable target image: freezing at an empirically complete finite exposure is deliberate, rather than claiming the persistence=1 renderer converges in brightness.

## Root cause and settle rule

`App.animate()` calls `MobiusRenderer.render()` on every eligible RAF. The renderer previously had no stationary completion state. Even though canonical Reference stops drift and locks the camera, persistence approaches 1.0 and the renderer continuously decays/copies the accumulation, simulates, splats, blurs bloom, composites, and measures GPU queries.

Live Reference now counts actual attempted deposits (`numParticles * stepsPerFrame`) after each complete live frame. It settles once:

```
referenceDeposits >= 16,384 * accumWidth * accumHeight
```

The crossing frame completes normally, including bloom and the final composite. Subsequent unchanged Reference renders return before profiler queries, adaptation, accumulation, transform feedback, splats, bloom, and presentation. No canvas clear occurs when settling. No new RAF chain, timer, or listener is introduced. Explore never uses this completion rule. Export loops remain independent and unmodified.

This conservative budget favors faint detail over fast completion. It is not a five-second deadline, nor a per-frame synchronous convergence readback. At 1200 x 800 and 60 FPS the approximate development times are Potato 27.3 minutes, Low 7.3 minutes, Standard 3.6 minutes; the measured Auto ladder reaches this budget in roughly 40 seconds. These times increase on slower hardware or larger targets. This latency is an explicit limitation of preserving exposure while retaining the existing low-tier workloads. The budget is not a measured universal perceptual-convergence guarantee on every display/GPU.

## Wake behavior

- Entering/resetting Reference clears accumulation and resets its live deposit count.
- Canvas/DPR/accumulation-target size, aspect, camera/target-camera, manual quality selection, tier change between frames, or particle/step override changes start a fresh exposure. Small canvas resizes also wake even when allocation hysteresis retains the textures.
- Auto promotions within a rendered frame retain accumulated work; a resulting DPR/target change still starts fresh development. No continuous adaptive polling occurs while settled.
- Context restoration constructs a clean awake renderer through the existing Issue 2 recovery lifecycle; it develops and settles again.
- Bloom, raw/final mode, palette, gain, and raw overlay changes recomposite the existing exposure once (including bloom/raw overlay where needed) and return to rest without resimulating or adding photons.
- Switching to Explore immediately removes the settled state. Reentering Reference develops fresh canonical artwork.
- Standard and Master exports neither consume nor reset the live development budget. When the export hold is removed, a settled renderer explicitly presents its cached artwork first.

## Reproduction and artifacts

```
python measure_issue3.py
python measure_issue3.py --tiers auto --times 30,60,90,180,360 --output issue3_extended
python run_issue3_regressions.py
python run_browser_regressions.py test_issue2_rebuild_retry.html test_issue2_context_loss.html test_issue1_reference_invariant.html test_modes_and_exports.html test_reference_master.html test_export_display_hold.html test_export_failure_and_edge_cases.html
```

Measurement output is written to `issue3_baseline/` and `issue3_extended/`. These captures were taken before the fix; rerunning the measurement tool on the fixed renderer measures its new behavior. Dedicated results/screenshots go to `issue3_results/`. The compositor runner requires `websocket-client` and `Pillow`; the four-tier baseline runner uses only Python standard-library modules. PNG/JSON/log artifacts follow the repository's existing ignore rules.

The dedicated suite naturally develops the production budget and then waits five real minutes, without accelerating time or lowering the threshold. It captures the actual compositor (not just a framebuffer readback) at settle, 30 seconds, and five minutes. It then runs three additional full budgets on the same accumulated image for a 4x unlimited comparison. Later wake checks seed progress near the unchanged production threshold only **after** observing fresh development, to keep the suite practical. Context recovery must naturally settle again. Standard export and both full 4096 x 4096 Master 120/240 exports count actual transform feedback and splat passes.

## Validation results

All **318 assertions passed**: dedicated Issue 3 **43/43**, established regression suites **270/270**, existing math unit checks **5/5**. Production JavaScript syntax checks, Python compilation, and `git diff --check` also pass.

| Suite | Passed |
|---|---:|
| Issue 3 live Reference settling | 43/43 |
| Issue 2 rebuild retries | 93/93 |
| Issue 2 context loss | 112/112 |
| Issue 1 Reference invariant | 9/9 |
| Modes and exports | 32/32 |
| Reference Master | 10/10 |
| Export display hold | 11/11 |
| Export failure and edge cases | 3/3 |
| Existing math unit checks | 5/5 |

The dedicated suite's natural 640 x 480 Extreme exposure reached the production budget in approximately 12 seconds, at 712 complete accumulation frames and 5,039,456,256 attempted deposits (threshold 5,033,164,800). During five real settled minutes: **zero audited GPU commands**, zero additional simulation/splat/decay/bloom/query passes, unchanged accumulation count, one RAF, no pending timers, and unchanged event handlers. This replaces continuous baseline workloads of about 238 passes/s on Potato, 476 on Low/Standard, and 715 on Auto with **zero live simulation/splat passes/s** after development.

`settled.png`, `idle30.png`, and `idle300.png` are pixel-identical actual browser compositor captures. The cached framebuffer also has zero pixel/brightness drift. The 4x unlimited capture uses the same exposure after three additional complete budgets. Visual inspection retains the main faint peripheral filament network at settle; later unlimited development brightens that network while washing out internal lace. For the outer annulus (radius 0.9-1.6, radius normalized to half the canvas height), green-channel spatial correlation between settled and 4x images is 0.9911, while mean blue increases from 97.12 to 169.24/255. Outer local-structure correlation is 0.9306 after 1-pixel Gaussian smoothing and subtraction of a 6-pixel Gaussian low-pass. These metrics support the visual assessment, rather than claiming pixel equality against a different exposure.

Reset, reentry, small/large resize, DPR, manual/Auto quality, all listed display controls, rapid switching, and actual context loss/restoration pass. Recovered Reference naturally develops and settles again. Explore remains live. Standard 7-pass export executes exactly 84 simulation/splat pairs; full 4096-square Master 120/240 execute exactly 1,920/3,840 splats and 1,981/3,901 simulations (including the existing 61 warmup steps). Requested PNG dimensions and settled live artwork/budget survive every export; display holds clean up. The existing display-hold suite also passes its full Standard 3840 x 2160 120-pass export. Export implementation from `exportPNG()` through the end of `renderer.js` matches the baseline byte-for-byte after normalizing line endings.

The first dedicated run passed its five-minute idle, visual, wake, recovery, and export assertions, but its final timer assertion ran before the existing 10-second download-URL cleanup timers expired. The test was corrected to wait for those one-shot timers to drain; the complete 43-check suite, including a second full five-minute idle window, then passed. Final lifecycle: one RAF, zero timers, one handler each for loss/restoration/resize, zero calls on lost contexts, and no WebGL errors.

Idle command auditing follows the shared Issue 2 instrumentation: it excludes cheap context-health checks (`isContextLost`) and test-only error reads (`getError`). The old GPU timer metric remains the last developed-frame measurement while settled; no fresh live timer queries are issued. No system power or thermal measurements are claimed.

## Files

- `renderer.js`: Reference exposure counter, settled early return, development/presentation change detection, and shared existing bloom pass.
- `app.js`: cached presentation before removing an export display hold from settled Reference.
- `measure_issue3.html`, `measure_issue3.py`: sequential real-time tier measurements and framebuffer captures.
- `test_issue3_reference_settle.html`: dedicated real-time, visual, wake, recovery, export, and lifecycle regression checks.
- `run_issue3_regressions.py`: isolated Chrome execution and actual compositor screenshot comparisons.
- `ISSUE3_VALIDATION.md`: baseline, rule, limitations, visual evaluation, results, and reproduction commands.
