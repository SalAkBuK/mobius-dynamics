# Issue 2: WebGL context loss recovery

Scope: context loss/restoration only. Baseline: `563ac2ff48df3a41db04eac13a29f3aa0cfd5f7e`.

## Failure reproduced before implementation

Ran the production `index.html` in isolated headless Chrome/ANGLE D3D11, using
`WEBGL_lose_context.loseContext()` followed by `restoreContext()`. The connected
browser was unavailable, so the runner follows the repository's headless Chrome
approach. Baseline reproduction source: `reproduce_issue2_context_loss.html`.

| State | Loss event / prevented | Render attempts after loss | Export result | Restore |
| --- | --- | ---: | --- | --- |
| Reference idle | fired / no | 197 | n/a | failed |
| Explore, custom math/camera/palette | fired / no | 202 | n/a | failed |
| Standard 3840×2160, 20 test passes | fired / no | 167 | falsely reported success | failed |
| Reference Master 4096×4096, 4 test passes | fired / no | 179 | falsely reported success | failed |

RAF continued in every state, including the explicit RAF probe. All old shader
programs tested invalid. Both exports settled and cleared their flags in these
runs; neither remained stuck. Neither context restored, and all four canvases
required a reload. Counts are observations from that baseline run, not thresholds.

Root cause: production did not prevent the loss event's default behavior or handle
restoration. RAF and exports lacked context guards; exports could read invalid
framebuffers and encode an apparently successful PNG. Their original `return
new Promise(...)` also ran GL cleanup before asynchronous encoding completed.

## Recovery architecture

App owns one permanent listener for each context event. Loss is intercepted with
`preventDefault()`, retires the renderer, rejects an outstanding export wait, hides
the display hold, and shows a recovery toast. The existing RAF chain continues
scheduling but skips math updates, resizing and rendering while unavailable.
Renderer entry points independently guard against loss, including the interval
before the browser dispatches the event.

Restoration waits for the App export task's `finally` blocks before reading session
state. A new `MobiusRenderer` on the same canvas runs the constructor's clean shader,
buffer, VAO, texture, FBO and profiler/query initialization. Only explicit JS display
and quality settings transfer. No old GL handles, accumulation, particle buffers,
timing samples or query pool transfer. Resize handles an unchanged canvas backing
size, so the reconstructed viewport aspect and targets are correct. Accumulation
starts clear and particles start from fresh seeds.

Explore retains the same MathSystem object, preserving coefficients/base
coefficients, symmetry, offsets, drift/time and disturbance state. Camera current
and target values, palette, bloom, view mode, gain, overrides, and adaptive/manual
selection transfer explicitly. An interrupted Master export first restores its
pre-export Explore snapshot using the existing session restoration path.

Reference reuses `setMode('reference')` to enforce Issue 1: both modes Reference,
n=16, exact canonical a/b/c/d, zero offsets/pointer/shock, drift false/time zero,
canonical camera and cobalt palette. Mathematical formulas and rendering shaders
are unchanged.

Both exports check context validity during develop work and around progress
callbacks. RAF yields and PNG encoding have interruptible waits. Context loss
rejects with `WebGLContextLostError`; late encoder callbacks cannot report success
or download. Encoding is awaited inside the cleanup scope and null/empty blobs
fail. `finally` restores JS state and flags; GL cleanup runs only while resources
remain valid. The browser releases lost-context resources. Exports never restart
automatically. The app reports interruption and invites an explicit retry.

No recovery path starts RAF, reinstalls UI handlers, reloads the page, adds a render
engine, enables preserveDrawingBuffer, or changes quality tiers/export dimensions,
120/240 pass choices, formula or Reference styling.

## Files changed

- `app.js`: lifecycle listeners, renderer replacement, session reconnection, RAF
  pause guards, export task tracking and interruption UI/display-hold cleanup.
- `renderer.js`: loss guards, retired renderer state, interruptible export waits,
  safe encoding/cleanup, and resizing freshly rebuilt targets.
- `test_issue2_context_loss.html`: production-page regression suite, including GL,
  RAF, listener, timer and download instrumentation.
- `reproduce_issue2_context_loss.html`: pre-fix production failure probe.
- `run_browser_regressions.py`: isolated Chrome runner for new and existing HTML
  suites, portable workspace root and temporary profiles; maps legacy localhost
  iframe ports to the test server while serving HTML.
- `ISSUE2_WEBGL_RECOVERY.md`: reproduction, design and validation handoff.

## Validation

Run:

```powershell
python run_browser_regressions.py test_issue2_context_loss.html test_issue1_reference_invariant.html test_modes_and_exports.html test_reference_master.html test_export_display_hold.html test_export_failure_and_edge_cases.html --timeout 240
node --check app.js
node --check renderer.js
git diff --check
```

The new suite exercises nine actual loss/restore pairs: Reference idle, custom
Explore, Standard and Master from both modes, asynchronous PNG encoding, and two
further consecutive cycles. It checks fresh resources/seeds, canonical Reference,
preserved Explore state, deterministic export failures, cleared flags/overlays,
late/null encoding, explicit retry, rendered pixel variation, resize, manual/auto
selection, and no commands during loss. Each cycle retains exactly one pending
App RAF, unchanged event registrations, at most one toast timer, no hold timer,
and no export waiter on the retired renderer.

Final combined run: **177/177 checks passed**.

| Suite | Passed |
| --- | ---: |
| Issue 2 context loss | 112/112 |
| Issue 1 Reference invariant | 9/9 |
| Modes and exports | 32/32 |
| Reference Master | 10/10 |
| Export display hold | 11/11 |
| Export failure and edge cases | 3/3 |

JavaScript syntax checks and `git diff --check` also passed. Across the nine recovery
cycles: zero GL commands during loss, zero traced recovery/resumed-rendering GL
errors, one RAF chain, unchanged listeners, and no accumulating timers/waiters.

Hardware/OS-induced GPU resets were not separately simulated; this suite uses the
browser's actual context loss/restoration extension on the production page.
