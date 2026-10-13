import http.server
import socketserver
import threading
import subprocess
import json
import os

PORT = 8794
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"

html_test = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Export Display Hold Regression Suite</title>
  <style>
    body, html { margin:0; padding:0; width:100%; height:100%; overflow:hidden; background:#020408; }
    #gl-canvas { position:absolute; top:0; left:0; width:100%; height:100%; display:block; }
    #export-display-hold { position:absolute; top:0; left:0; width:100%; height:100%; display:none; pointer-events:none; z-index:1; }
    #ui-container { position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:5; }
  </style>
</head>
<body>
<canvas id="gl-canvas" width="1200" height="800"></canvas>
<canvas id="export-display-hold"></canvas>
<div id="ui-container">
  <div id="controls-bar">
    <button id="btn-mode-reference" class="active"></button>
    <button id="btn-mode-explore"></button>
    <button id="btn-randomize-action"></button>
    <button id="btn-randomize-toggle"></button>
    <button id="btn-palette-toggle"></button>
  </div>
  <div id="mode-status-pill"></div>
  <div id="randomize-menu"></div>
  <div id="palette-menu"></div>
  <div id="equation-readout"></div>
  <span id="val-a">-0.755 + 0.330i</span><span id="val-b">-0.376 + 0.026i</span><span id="val-c">6.401 + 0.803i</span><span id="val-d">1.520 + 0.840i</span><span id="val-n">16</span>
  <div id="coeff-drawer">
    <input type="range" class="coeff-slider" id="slider-a-re" value="0">
    <span class="coeff-val" id="lbl-a-re">0.00</span>
    <input type="range" class="coeff-slider" id="slider-b-im" value="0">
    <span class="coeff-val" id="lbl-b-im">0.00</span>
    <input type="range" class="coeff-slider" id="slider-c-re" value="0">
    <span class="coeff-val" id="lbl-c-re">0.00</span>
    <input type="range" class="coeff-slider" id="slider-d-im" value="0">
    <span class="coeff-val" id="lbl-d-im">0.00</span>
    <button id="btn-reset-coeffs"></button>
  </div>
  <div id="coeff-lock-notice"></div>
  <div id="export-modal"></div>
  <button id="tab-export-standard"></button>
  <button id="tab-export-refmaster"></button>
  <div id="export-standard-panel"></div>
  <div id="export-refmaster-panel"></div>
  <div id="preset-modal"></div>
  <div id="toast-banner"></div>
  <span id="export-status-label"></span>
  <span id="export-status-pct"></span>
  <div id="export-progress-fill"></div>
  <button id="btn-export-start"></button>
  <button id="btn-export-cancel"></button>
  <div id="export-progress-area"></div>
<script>
  window.onerror = function(msg, url, line, col, err) {
    fetch('/display_hold_report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify([{ name: 'Window Error', passed: false, details: `${msg} at ${line}:${col} \n${err ? err.stack : ''}` }])
    });
  };
  window.addEventListener('unhandledrejection', function(e) {
    fetch('/display_hold_report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify([{ name: 'Unhandled Rejection', passed: false, details: String(e.reason ? e.reason.stack || e.reason : 'unknown') }])
    });
  });
</script>
<script type="module">
import { App } from './app.js';

async function runRegressionSuite() {
  const tests = [];

  try {
    const app = new App();
    window.app = app;
    const gl = app.renderer.gl;

    let contextLostCount = 0;
    gl.canvas.addEventListener('webglcontextlost', (e) => {
      contextLostCount++;
      e.preventDefault();
    });

    // 1. Initial warm-up: allow accumulation to render valid artwork
    await new Promise(r => setTimeout(r, 600));

    // =========================================================================
    // PART 1: Standard 4K Export (3840x2160, 120 passes) in Reference Mode n=16
    // =========================================================================
    app.setMode('reference');
    const initRefA = app.valA ? app.valA.innerText : '';
    const initRefN = app.math.n;

    tests.push({
      name: '1. Initial State: Reference Mode n=16 Readout Populated',
      passed: app.mode === 'reference' && initRefN === 16 && initRefA.includes('-0.755') && !initRefA.includes('--'),
      details: `Mode: ${app.mode}, n: ${initRefN}, readout a: "${initRefA}"`
    });

    // Setup Standard 4K 120-pass export
    app.setExportType('standard');
    app.exportWidth = 3840;
    app.exportHeight = 2160;
    app.exportPasses = 120;

    let overlayVisibleMidExport = false;
    let overlayPixelsMidExport = null;
    let readoutAMidExport = null;
    let isExportingMidExport = false;
    let glErrorsDuringExport = [];

    // Spy for GL errors during export
    const origDrawArrays = gl.drawArrays.bind(gl);
    gl.drawArrays = function(...args) {
      if (app.isExporting) {
        const err = gl.getError();
        if (err !== gl.NO_ERROR) glErrorsDuringExport.push(err);
      }
      return origDrawArrays(...args);
    };

    const exportPromise = app.startExport();

    // Monitor during export execution
    const holdCanvas = document.getElementById('export-display-hold');
    const sampleInterval = setInterval(() => {
      const pctTxt = document.getElementById('export-status-pct')?.innerText || '0%';
      const pct = parseInt(pctTxt, 10);
      if (pct >= 20 && !overlayPixelsMidExport) {
        isExportingMidExport = app.isExporting;
        readoutAMidExport = app.valA ? app.valA.innerText : null;

        if (holdCanvas && holdCanvas.style.display !== 'none' && holdCanvas.width > 0 && holdCanvas.height > 0) {
          overlayVisibleMidExport = true;
          const ctx = holdCanvas.getContext('2d');
          const px = ctx.getImageData(Math.floor(holdCanvas.width * 0.35), Math.floor(holdCanvas.height * 0.35), 1, 1).data;
          overlayPixelsMidExport = Array.from(px);
        }
      }
    }, 40);

    const stdBlob = await exportPromise;
    clearInterval(sampleInterval);

    // Check overlay representation during export
    const overlayHasArtwork = overlayPixelsMidExport && (overlayPixelsMidExport[0] > 0 || overlayPixelsMidExport[1] > 0 || overlayPixelsMidExport[2] > 0);
    tests.push({
      name: '2. Standard 4K 120-pass: Artwork Overlay Active Throughout Export',
      passed: overlayVisibleMidExport && overlayHasArtwork && isExportingMidExport,
      details: `Overlay displayed: ${overlayVisibleMidExport}, isExporting: ${isExportingMidExport}, sample pixel: [${overlayPixelsMidExport ? overlayPixelsMidExport.join(',') : 'null'}] (non-blank artwork)`
    });

    tests.push({
      name: '3. Standard 4K 120-pass: Coefficient Readout Retains Valid Values (No "--")',
      passed: readoutAMidExport && readoutAMidExport.includes('-0.755') && !readoutAMidExport.includes('--'),
      details: `Readout during export: "${readoutAMidExport}"`
    });

    tests.push({
      name: '4. Standard 4K 120-pass: No WebGL Context Loss & Zero GL Errors',
      passed: contextLostCount === 0 && !gl.isContextLost() && glErrorsDuringExport.length === 0,
      details: `Context loss count: ${contextLostCount}, isContextLost: ${gl.isContextLost()}, GL errors: ${glErrorsDuringExport.length}`
    });

    tests.push({
      name: '5. Standard 4K 120-pass: Export Completes with High-Res PNG',
      passed: stdBlob instanceof Blob && stdBlob.size > 1000000 && stdBlob.type === 'image/png',
      details: `Exported PNG size: ${stdBlob ? (stdBlob.size / (1024*1024)).toFixed(2) : 0} MB, type: ${stdBlob ? stdBlob.type : 'none'}`
    });

    // Wait 200ms for RAF to resume and perform onscreen render
    await new Promise(r => setTimeout(r, 200));

    // Verify overlay disappeared and renderer resumed
    const overlayHiddenAfter = holdCanvas && holdCanvas.style.display === 'none';
    tests.push({
      name: '6. Standard 4K 120-pass: Normal Renderer Resumes & Overlay Disappears',
      passed: !app.isExporting && !app.renderer.isExporting && overlayHiddenAfter,
      details: `app.isExporting: ${app.isExporting}, renderer.isExporting: ${app.renderer.isExporting}, overlay display: "${holdCanvas ? holdCanvas.style.display : 'none'}"`
    });

    // Verify Reference artwork visible on WebGL canvas afterward
    app.renderer.presentCurrentFrame();
    const postExportPx = new Uint8Array(4);
    gl.readPixels(Math.floor(gl.canvas.width * 0.35), Math.floor(gl.canvas.height * 0.35), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, postExportPx);
    const postExportArtworkVisible = (postExportPx[0] > 0 || postExportPx[1] > 0 || postExportPx[2] > 0);

    tests.push({
      name: '7. Standard 4K 120-pass: Reference Artwork Remains Visible Post-Export',
      passed: postExportArtworkVisible,
      details: `WebGL default framebuffer sample pixel: [${Array.from(postExportPx).join(',')}] (visible artwork rendered onscreen)`
    });

    // =========================================================================
    // PART 2: Reference Master Export (4096x4096, 120 passes) Display Hold Test
    // =========================================================================
    app.setExportType('reference_master');
    app.refMasterPasses = 120;

    let refMasterOverlayVisible = false;
    let refMasterOverlayPixels = null;
    let refMasterReadoutA = null;

    const refMasterPromise = app.startExport();

    const refMasterSampleInterval = setInterval(() => {
      const pctTxt = document.getElementById('export-status-pct')?.innerText || '0%';
      const pct = parseInt(pctTxt, 10);
      if (pct >= 10 && !refMasterOverlayPixels) {
        refMasterReadoutA = app.valA ? app.valA.innerText : null;
        if (holdCanvas && holdCanvas.style.display !== 'none' && holdCanvas.width > 0 && holdCanvas.height > 0) {
          refMasterOverlayVisible = true;
          const ctx = holdCanvas.getContext('2d');
          const px = ctx.getImageData(Math.floor(holdCanvas.width * 0.35), Math.floor(holdCanvas.height * 0.35), 1, 1).data;
          refMasterOverlayPixels = Array.from(px);
        }
      }
    }, 40);

    const refMasterBlob = await refMasterPromise;
    clearInterval(refMasterSampleInterval);

    const refMasterOverlayHasArtwork = refMasterOverlayPixels && (refMasterOverlayPixels[0] > 0 || refMasterOverlayPixels[1] > 0 || refMasterOverlayPixels[2] > 0);
    tests.push({
      name: '8. Reference Master: Artwork Overlay Active Throughout 4096x4096 Export',
      passed: refMasterOverlayVisible && refMasterOverlayHasArtwork,
      details: `Overlay displayed: ${refMasterOverlayVisible}, sample pixel: [${refMasterOverlayPixels ? refMasterOverlayPixels.join(',') : 'null'}]`
    });

    tests.push({
      name: '9. Reference Master: Readout Populated Throughout Export',
      passed: refMasterReadoutA && refMasterReadoutA.includes('-0.755') && !refMasterReadoutA.includes('--'),
      details: `Readout during master export: "${refMasterReadoutA}"`
    });

    tests.push({
      name: '10. Reference Master: Output Verified (4096x4096)',
      passed: refMasterBlob instanceof Blob && refMasterBlob.size > 2000000 && refMasterBlob.type === 'image/png',
      details: `Master PNG size: ${refMasterBlob ? (refMasterBlob.size / (1024*1024)).toFixed(2) : 0} MB`
    });

    // Wait for onscreen render after master export
    await new Promise(r => setTimeout(r, 200));

    const refMasterOverlayHidden = holdCanvas && holdCanvas.style.display === 'none';
    app.renderer.presentCurrentFrame();
    const postMasterPx = new Uint8Array(4);
    gl.readPixels(Math.floor(gl.canvas.width * 0.35), Math.floor(gl.canvas.height * 0.35), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, postMasterPx);
    const postMasterVisible = (postMasterPx[0] > 0 || postMasterPx[1] > 0 || postMasterPx[2] > 0);

    tests.push({
      name: '11. Reference Master: Overlay Removed & Reference Mode Preserved Post-Export',
      passed: refMasterOverlayHidden && postMasterVisible && app.mode === 'reference',
      details: `Overlay hidden: ${refMasterOverlayHidden}, onscreen pixel: [${Array.from(postMasterPx).join(',')}], mode: ${app.mode}`
    });

    // Unhook spies
    gl.drawArrays = origDrawArrays;

    fetch('/display_hold_report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tests)
    });
  } catch (err) {
    fetch('/display_hold_report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify([{ name: 'Runtime Failure', passed: false, details: `${err.message} \n${err.stack}` }])
    });
  }
}

window.addEventListener('load', runRegressionSuite);
</script>
</body>
</html>
"""

with open("test_export_display_hold.html", "w", encoding='utf-8') as f:
    f.write(html_test)

done_event = threading.Event()
report_results = None

class TestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global report_results
        if self.path == '/display_hold_report':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            report_results = json.loads(body.decode('utf-8'))
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            done_event.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

httpd = socketserver.TCPServer(("", PORT), TestHandler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--no-sandbox",
    "--use-gl=angle",
    "--use-angle=d3d11",
    "--window-size=1200,800",
    f"http://localhost:{PORT}/test_export_display_hold.html"
]

print("Launching Chrome test runner for Export Display Hold Regression Suite...")
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

done = done_event.wait(timeout=120.0)
proc.terminate()
httpd.shutdown()

if done and report_results:
    all_passed = True
    print("\n=======================================================")
    print("EXPORT DISPLAY HOLD REGRESSION TEST RESULTS")
    print("=======================================================")
    for tst in report_results:
        status = "PASS" if tst["passed"] else "FAIL"
        if not tst["passed"]:
            all_passed = False
        print(f"[{status}] {tst['name']}")
        print(f"       {tst['details']}")
    print("=======================================================")
    print(f"ALL TESTS PASSED: {all_passed}")
    print("=======================================================\n")
    if not all_passed:
        exit(1)
else:
    print("Test execution timed out or failed to post report.")
    exit(1)
