# Issue 4: Standard export particle isolation

Baseline main: `7c0141ae271b8a04c9886ac6777971c3d0394f04`. Scope is Issue 4 only.

## Exact reproduction before production edits

`test_issue4_particle_isolation.html?baseline=1` ran against unchanged production code. The real App ran in a 160 x 120 iframe, with its live RAF temporarily held via `isTabHidden` so the comparison includes only export work. Explore used symmetry 11, custom coefficient offsets, time 7.25, camera zoom 2.1, center (0.07, -0.03), and the Solar palette. Reference used its canonical state, with either partial development or natural completion at its existing Potato target. Both entire particle buffers were seeded deterministically, with `vboCur=1` and `respawnRequested=true`.

Before and after each 96 x 64, three-pass Standard export, `gl.getBufferSubData()` read **every byte of both 9,600,000-byte VBOs**, including unused capacity. The fixture also captured both live accumulation textures, both bloom textures, their handles, sim/splat VAO handles, read index, accumulation age, Reference exposure/settled/Auto state, camera, palette, bloom/view settings, the full serializable MathSystem, the adaptive quality state and app mode. Live framebuffer pixels were compared independently.

| Scenario | Changed bytes in VBO 0 | Changed bytes in VBO 1 | Other captured state |
|---|---:|---:|---|
| Explore paused | 7,127,665 | 7,127,561 | Unchanged |
| Explore evolving | 7,127,665 | 7,127,561 | Unchanged |
| Reference developing | 7,115,700 | 7,115,465 | Unchanged |
| Reference settled | 7,115,700 | 7,115,465 | Unchanged |

The pre-fix fixture passed all initial reproduction assertions; the final expanded fixture also passes 30/30 expected-mutation assertions against an isolated archive of baseline main. `vboCur` stayed at 1 because three passes perform 36 transform steps, an even count. Both buffers nevertheless advanced. The visually restored accumulation concealed the changed particle trajectory. No production file was modified until this result and deterministic PNG hashes had been captured and reported.

## Selected isolation and memory cost

Standard Export now saves `vboCur`, allocates two temporary GPU buffers, and copies both entire live VBOs with `copyBufferSubData()` before development. The existing export uses its original buffers, uniforms, particle count and trajectory. On success or an ordinary exception, `finally` copies both backups back, deletes the backups and restores `vboCur` alongside the existing display state restoration.

This follows Reference Master's GPU backup/restore architecture without changing Master or extracting shared production helpers. A failed buffer creation or insufficient backup storage aborts before export can modify particles; already-created backups are cleaned up. Backup restoration is enabled only after both copies have completed.

Temporary GPU storage is `2 * maxParticleCapacity * 16` bytes: **19,200,000 bytes (18.31 MiB)** at the existing 600,000-particle capacity. There are two additional buffer handles during export, four full GPU copies on success (38.4 MB transferred), and no production CPU particle readback. The buffers are deleted after every normal completion/failure. On real context loss, both restore and delete calls are skipped; the browser releases lost resources and Issue 2 retires/rebuilds the renderer.

## State, continuation and output evidence

Post-fix, both full VBOs compare byte-for-byte equal in all four scenarios: **zero changed bytes**. All captured metadata, GPU handles, live accumulation/bloom texture contents and cached live pixels remain identical. Drift is observed frozen inside export, with no time advancement; evolving Explore resumes with its original evolution flag. Reference partial development retains the same deposited work and read index; settled Reference remains settled without consuming live exposure.

For paused Explore, the test renders one live frame from a captured initial state to form a no-export control. It then rolls both full buffers, both accumulation/bloom texture pairs and renderer/quality metadata back to that exact initial state, verifies the rollback, runs Standard Export, and renders exactly one live frame with the same `dt`. Both resulting VBOs, accumulation textures, bloom textures and final framebuffer pixels match the control **exactly**, with no tolerance. Respawn is disabled for this continuation test so it exercises continuation of existing trajectories.

All four exported PNGs decode successfully to 96 x 64 RGBA, contain visible pixels, and execute exactly 36 transform-feedback steps and 36 splat passes. Their decoded pixel SHA-256 values match those captured before the production change:

| Mode | Decoded RGBA SHA-256 |
|---|---|
| Explore paused/evolving | `ae3a3e93b7f3fbaf45fa4c2287faf4b628c998e43fa0ff2261dd96d5beaa515d` |
| Reference developing/settled | `8dd9080dd65bd2d30b7e80de43a08c48f76766aefe3d50ab2d5509d2a03afc09` |

The seeded GPU input, frozen math, dimensions, pass count, bloom, palette and tonemap are controlled. Hashes describe decoded pixels rather than PNG container bytes. They were measured on Windows Chrome / ANGLE D3D11; GPU arithmetic on a different backend may require a separate reviewed golden capture. Full-buffer preservation and the same-session continuation comparison do not depend on those golden hashes.

## Failures, recovery and Reference Master

The suite injects an ordinary error after the export has advanced all 36 simulation steps, a null PNG encoder result after rendering, failure of the second backup handle allocation, and failure to allocate backup storage. All reject with the full live particle/math/display state restored and no temporary Buffer/Texture/Framebuffer/VertexArray leaks.

Real `WEBGL_lose_context` is triggered both after development and during asynchronous PNG encoding. Exports reject with `WebGLContextLostError`; no audited GL call touches lost resources. Normal Issue 2 reconstruction creates clean buffers, keeps the evolving custom Explore session, and permits another export that preserves its new live VBOs. A late encoder callback cannot revive the old renderer or export. The browser restoration is requested after a short test-only loss interval, matching the established recovery fixtures.

The new suite also checks Reference Master directly: full VBO equality/index restoration, live exposure/camera/palette/accumulation preservation, a valid 4096-square PNG, and its unchanged 61 warmup steps plus 16 simulation/splat steps for one develop pass. The existing suites additionally exercise full 120/240 Master exports, Standard 4K export, display hold, failures, Reference invariants and recovery retry behavior. `exportReferenceMaster()` and all renderer code before `exportPNG()` are byte-identical to baseline main.

## Regression results

**432/432 regression assertions pass**: 60 new Issue 4 assertions, 270 established Issue 1/2 and export assertions, 54 Issue 3B assertions, 43 Issue 3 assertions and five math assertions. The final reproduction fixture also passes its 30 expected-mutation assertions against an isolated archive of unchanged baseline main; these are excluded from the post-fix regression total.

The five-minute compositor captures are pixel-identical, with zero live simulation/splat/bloom/query work. Full 4096-square Master 120/240 exports retain all requested work: 1,920/3,840 splats and 1,981/3,901 simulation steps including the existing 61 warmup steps. The legacy adaptive diagnostic completes with the same boolean results as its recorded baseline. Its five stale Standard-only expectation fields remain false, along with the expected `isInteracting=false` after cooldown; these diagnostic fields are not counted as passing assertions.

The Issue 4 suite audits every GL error, live RAF count, handler counts, one-shot timer drainage and temporary GPU resource balance. Existing Issue 3 covers five real minutes of zero live GPU work with pixel-identical compositor screenshots; Issue 3B covers all exposure budgets, quality transitions and bounded Auto. Canonical math, quality/exposure policy, camera, bloom, tonemapping, export resolution/pass counts, Master, UI, Explore interactions and recovery architecture remain unchanged.

## Files changed and reproduction

- `renderer.js`: Standard Export backup/restore and allocation checks only (33 added lines).
- `test_issue4_particle_isolation.html`: exact GPU state, continuation, output, failure, recovery and resource regression coverage, plus the pre-fix reproduction mode.
- `issue4_export_fixtures.js`: the pre-fix deterministic decoded PNG hashes.
- `ISSUE4_VALIDATION.md`: this evidence and handoff.

```powershell
# Before production edits, on baseline main with only the test/fixture additions:
python -u run_browser_regressions.py 'test_issue4_particle_isolation.html?baseline=1' --timeout 300
# On the fixed renderer:
python -u run_browser_regressions.py test_issue4_particle_isolation.html --timeout 300
python -u run_issue3_regressions.py
python -u run_browser_regressions.py test_issue2_rebuild_retry.html test_issue2_context_loss.html test_issue1_reference_invariant.html test_modes_and_exports.html test_reference_master.html test_export_display_hold.html test_export_failure_and_edge_cases.html test_issue3b_tier_budgets.html --timeout 600
```

The five math results in `test_math_units.html` are POSTed through a temporary iframe adapter to the same runner, then the adapter is removed. The legacy object-reporting `test_adaptive.html` diagnostic is also run separately; its historical Standard-only expectations are reported against baseline rather than counted as passing regression assertions. Syntax checks include the production renderer, fixture module and embedded test module, plus `git diff --check`.
