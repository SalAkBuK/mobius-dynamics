# Real-browser release checks

The HTML suites in the repository root run inside an instrumented iframe in headless Chrome. That
harness deliberately **stubs** several browser boundaries (`HTMLAnchorElement.prototype.click`,
`navigator.clipboard`, `URL.createObjectURL`, `canvas.toBlob`, file input, tab visibility, a 160×120 frame,
`customDpr = 1`). A stubbed download click is exactly why an export once never reached disk without any test
failing. These scripts exercise those boundaries for real, against a **deployed URL**, in a **headful** browser
with a normal-style profile (real downloads directory, real clipboard, real file chooser, real keyboard/mouse/touch).

They are not part of the "complete regression" assertion total; they are a separate release gate.

## Run

```
cd release_checks
npm install                      # puppeteer-core only (uses the Chrome/Edge you already have)
# optional: set CHROME_PATH / EDGE_PATH if the browsers are not in their default Windows locations
node rc_stage1.mjs   https://mobius-dynamics.vercel.app/ ./out/stage1 chrome   # downloads, clipboard, file chooser
node rc_ref.mjs      https://mobius-dynamics.vercel.app/ ./out/ref    chrome   # Reference invariant through every path
node rc_presets.mjs  https://mobius-dynamics.vercel.app/ ./out/pre    chrome   # preset edge cases + storage failure
node rc_export.mjs   https://mobius-dynamics.vercel.app/ ./out/exp    chrome   # export lifecycle (cancel, retry, hidden tab, context loss)
node rc_kbd.mjs      https://mobius-dynamics.vercel.app/ ./out/kbd    chrome   # keyboard / focus / modal audit
node rc_explore.mjs  https://mobius-dynamics.vercel.app/ ./out/exr    chrome   # Explore interactions + 90 s drift soak
node rc_resp.mjs     https://mobius-dynamics.vercel.app/ ./out/resp   chrome   # 8 viewports x release surfaces (~30 min)
node rc_net.mjs      https://mobius-dynamics.vercel.app/ ./out/net    chrome   # console/network, fresh + used profile
node rc_extra.mjs    https://mobius-dynamics.vercel.app/ ./out/extra  chrome   # HiDPI, touch, resize during export, no WebGL, two tabs
node rc_perf.mjs     https://mobius-dynamics.vercel.app/ ./out/tiers  chrome tiers    # every quality tier
node rc_perf.mjs     https://mobius-dynamics.vercel.app/ ./out/soak   chrome soak 40  # repeat the long use cycle, measure memory
node rc_flows2.mjs    https://mobius-dynamics.vercel.app/ ./out/flows2 chrome   # settle, every Randomize family, export cancel at each stage, input isolation
node rc_quota.mjs     https://mobius-dynamics.vercel.app/ ./out/quota  chrome   # real localStorage exhaustion
node rc_soak_full.mjs https://mobius-dynamics.vercel.app/ ./out/soakf  chrome 12 # the full release-spec use cycle, repeated
node rc_urlparams.mjs https://mobius-dynamics.vercel.app/ ./out/url   chrome   # malformed/extreme URL hooks (informational)
```

Use `edge` instead of `chrome` for Edge. The first argument is the URL under test; the second is a scratch
directory (deleted and recreated; it holds the profile and the Downloads folder). Exit code is non-zero if any
check FAILs. `KNOWN-MINOR` lines are recorded minor findings (see `docs/RELEASE_CANDIDATE_REPORT.md`); they print
`PASS` if the finding stops reproducing.

> These scripts really download PNG/JSON files. They write them to the scratch directory you pass as the second
> argument (a throwaway profile), **not** to your own Downloads folder. Delete that directory afterwards. You do not need
> to run all of them: `rc_stage1.mjs` (downloads, clipboard, file chooser) and `rc_ref.mjs` are the quick functional pair.

## Test-harness pitfalls found while writing these (do not reintroduce)

* Always pass an **absolute** download directory to the browser profile (the scripts do this); a relative one silently
  drops every download.
* `page.$$()` / `ElementHandle.click()` keep the clicked element alive in the page until the handle is disposed. In a long
  soak this looks like a DOM/listener leak that the application does not have. Use `page.click(selector)` or mouse
  coordinates, and `dispose()` any handle you create.
* CDP `Browser.setPermission` takes W3C names (`clipboard-write`, `clipboard-read`), not the `clipboardReadWrite` style names.
* A keyboard test that presses Space while a dialog button is focused activates that button (native behaviour); focus the
  dialog container first when you want to prove that shortcut keys do nothing behind a dialog.
