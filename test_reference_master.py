import http.server
import socketserver
import threading
import subprocess
import json
import time
import os

PORT = 8795
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"

html_test = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Reference Master Validation Suite</title></head>
<body>
<div id="results">Running Reference Master tests...</div>
<canvas id="gl-canvas" width="800" height="600"></canvas>
<div id="ui-container">
  <div id="controls-bar">
    <button id="btn-mode-reference" class="active"></button>
    <button id="btn-mode-explore"></button>
    <button id="btn-randomize-action"></button>
    <button id="btn-randomize-toggle"></button>
    <button id="btn-palette-toggle"></button>
    <button id="btn-export-trigger"></button>
    <button id="btn-refmaster-trigger"></button>
    <button id="btn-preset-trigger"></button>
  </div>
  <div id="mode-status-pill"></div>
  <div id="randomize-menu"></div>
  <div id="palette-menu"></div>
  <div id="equation-readout"></div>
  <span id="val-a"></span><span id="val-b"></span><span id="val-c"></span><span id="val-d"></span><span id="val-n"></span>
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
</div>

<script>
  window.onerror = function(msg, url, line, col, err) {
    fetch('/refmaster_report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify([{ name: 'Runtime Error', passed: false, details: `${msg} at ${line}:${col} \n${err ? err.stack : ''}` }])
    });
  };
  window.addEventListener('unhandledrejection', function(e) {
    fetch('/refmaster_report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify([{ name: 'Unhandled Rejection', passed: false, details: String(e.reason ? e.reason.stack || e.reason : 'unknown') }])
    });
  });
</script>
<script type="module" src="./app.js"></script>
<script type="module">
import { App, CURATED_PRESETS } from './app.js';
import { CONRADI_REFERENCE } from './math.js';

async function runTests() {
  const tests = [];
  await new Promise(r => setTimeout(r, 200));

  let app = window.app || window.__app;
  if (!app) {
    app = new App();
    window.app = app;
  }
  const renderer = app.renderer;
  const math = app.math;
  const gl = renderer.gl;

  // Spies & Interceptors
  let uniformA = null;
  let uniformB = null;
  let uniformC = null;
  let uniformD = null;
  let uniformN = null;
  let uniformTime = null;
  let uniformZoom = null;
  let uniformAspect = null;
  let uniformCenter = null;
  let uniformPersistence = [];
  let drawParticles = [];
  let stepsPerPass = 0;
  let stepCounts = [];
  let currentPassSteps = 0;

  const origUniform2f = gl.uniform2f.bind(gl);
  const origUniform1f = gl.uniform1f.bind(gl);
  const origDrawArrays = gl.drawArrays.bind(gl);

  gl.uniform2f = function(loc, x, y) {
    if (loc && loc === renderer.simUniforms.a) uniformA = [x, y];
    if (loc && loc === renderer.simUniforms.b) uniformB = [x, y];
    if (loc && loc === renderer.simUniforms.c) uniformC = [x, y];
    if (loc && loc === renderer.simUniforms.d) uniformD = [x, y];
    if (loc && loc === renderer.splatUniforms.viewCenter) uniformCenter = [x, y];
    return origUniform2f(loc, x, y);
  };

  gl.uniform1f = function(loc, x) {
    if (loc && loc === renderer.simUniforms.n) uniformN = x;
    if (loc && loc === renderer.simUniforms.time) uniformTime = x;
    if (loc && loc === renderer.splatUniforms.zoom) uniformZoom = x;
    if (loc && loc === renderer.splatUniforms.aspect) uniformAspect = x;
    if (loc && loc === renderer.decayUniforms.persistence) uniformPersistence.push(x);
    if (loc && loc === renderer.simUniforms.step) {
      currentPassSteps++;
    }
    return origUniform1f(loc, x);
  };

  gl.drawArrays = function(mode, first, count) {
    if (mode === gl.POINTS) {
      drawParticles.push(count);
    }
    return origDrawArrays(mode, first, count);
  };

  // Track created and deleted textures/FBOs
  const createdTextures = [];
  const createdFbos = [];
  const origCreateTexture = gl.createTexture.bind(gl);
  const origCreateFramebuffer = gl.createFramebuffer.bind(gl);

  gl.createTexture = function() {
    const tex = origCreateTexture();
    createdTextures.push(tex);
    return tex;
  };
  gl.createFramebuffer = function() {
    const fbo = origCreateFramebuffer();
    createdFbos.push(fbo);
    return fbo;
  };

  // 1. Setup Explore state with heavy perturbations to test session isolation
  app.setMode('explore');
  math.setPointer(0.5, -0.4);
  math.injectShock(0.3, 0.8);
  math.setCoefficientOffset('a', 0.22, 0.11);
  math.setCoefficientOffset('b', -0.05, 0.08);
  math.setSymmetry(24);
  math.evolving = true;
  math.time = 42.5;
  renderer.zoom = 3.2;
  renderer.targetZoom = 3.2;
  renderer.viewCenter = [0.15, -0.25];
  renderer.setPalette('aurora');

  const preExportState = {
    mode: app.mode,
    mathMode: math.mode,
    n: math.n,
    evolving: math.evolving,
    time: math.time,
    offsetA: math.userOffsetA.clone(),
    offsetB: math.userOffsetB.clone(),
    zoom: renderer.zoom,
    viewCenter: [...renderer.viewCenter],
    palette: renderer.activePalette
  };

  // Track if render loop was called during export
  let concurrentRendersDuringExport = 0;
  const origRender = renderer.render.bind(renderer);
  renderer.render = function(...args) {
    if (app.isExporting) {
      concurrentRendersDuringExport++;
    }
    return origRender(...args);
  };

  // 2. Trigger Reference Master export via App (3 test passes for fast execution)
  app.setExportType('reference_master');
  app.refMasterPasses = 3;

  const exportPromise = app.startExport();
  const exportActiveCheck = app.isExporting;
  const masterBlob = await exportPromise;

  // Capture post-export session state IMMEDIATELY upon export resolution before async decoding
  const postMode = app.mode;
  const postMathMode = math.mode;
  const postN = math.n;
  const postEvolving = math.evolving;
  const postTime = math.time;
  const postOffsetA = math.userOffsetA ? math.userOffsetA.clone() : null;
  const postZoom = renderer.zoom;
  const postPalette = renderer.activePalette;

  // Unhook spies
  gl.uniform2f = origUniform2f;
  gl.uniform1f = origUniform1f;
  gl.drawArrays = origDrawArrays;
  gl.createTexture = origCreateTexture;
  gl.createFramebuffer = origCreateFramebuffer;
  renderer.render = origRender;

  // --- VERIFICATION A: Output dimensions exactly 4096 x 4096 ---
  let outW = 0, outH = 0;
  if (masterBlob instanceof Blob) {
    const bmp = await createImageBitmap(masterBlob);
    outW = bmp.width;
    outH = bmp.height;
  }
  const aPass = (outW === 4096 && outH === 4096 && masterBlob && masterBlob.type === 'image/png');
  tests.push({
    name: 'A. Output Dimensions 4096x4096',
    passed: aPass,
    details: `Exported target image verified: ${outW} × ${outH} PNG square master, size: ${(masterBlob ? masterBlob.size / (1024 * 1024) : 0).toFixed(2)} MB.`
  });

  // --- VERIFICATION B: Workload 589,824 particles x 16 IFS steps ---
  const particlesPass = drawParticles.length > 0 && drawParticles.every(p => p === 589824);
  const stepsPass = (currentPassSteps / 3) === 16;
  tests.push({
    name: 'B. True Brute Force Workload (589,824 × 16)',
    passed: particlesPass && stepsPass,
    details: `Particles drawn: ${drawParticles[0]}, IFS steps/pass: ${currentPassSteps / 3}, deposits/pass = 9,437,184`
  });

  // --- VERIFICATION C: Formula is exactly canonical Conradi n=16 ---
  const eps = 1e-4;
  const fPass = (
    uniformA && Math.abs(uniformA[0] - (-0.755)) < eps && Math.abs(uniformA[1] - 0.330) < eps &&
    uniformB && Math.abs(uniformB[0] - (-0.376)) < eps && Math.abs(uniformB[1] - 0.026) < eps &&
    uniformC && Math.abs(uniformC[0] - 6.401) < eps && Math.abs(uniformC[1] - 0.803) < eps &&
    uniformD && Math.abs(uniformD[0] - 1.520) < eps && Math.abs(uniformD[1] - 0.840) < eps &&
    uniformN === 16.0
  );
  tests.push({
    name: 'C. Canonical Conradi Formula (n=16, exact a,b,c,d)',
    passed: fPass,
    details: `a=[${uniformA}], b=[${uniformB}], c=[${uniformC}], d=[${uniformD}], n=${uniformN}`
  });

  // --- VERIFICATION D: Zero pointer, shock, offset, drift during export ---
  const dPass = (
    Math.abs(uniformA[0] - (-0.755)) < eps &&
    Math.abs(uniformA[1] - 0.330) < eps &&
    uniformCenter[0] === 0.0 && uniformCenter[1] === 0.0 &&
    uniformZoom === 1.65 &&
    uniformAspect === 1.0
  );
  tests.push({
    name: 'D. Zero Perturbation / Drift / Offset Isolation',
    passed: dPass,
    details: `center=[${uniformCenter}], zoom=${uniformZoom}, aspect=${uniformAspect}, a=[${uniformA}] (zero perturbation / offsets applied)`
  });

  // --- VERIFICATION E: Persistence strictly 1.0 ---
  const ePass = uniformPersistence.length > 0 && uniformPersistence.every(p => p === 1.0);
  tests.push({
    name: 'E. Master Accumulation Persistence = 1.0',
    passed: ePass,
    details: `All ${uniformPersistence.length} decay passes executed with persistence = 1.0 (zero decay)`
  });

  // --- VERIFICATION F: Session state 100% restored afterward ---
  const cMode = postMode === preExportState.mode;
  const cMMode = postMathMode === preExportState.mathMode;
  const cN = postN === preExportState.n;
  const cEvol = postEvolving === preExportState.evolving;
  const cTime = Math.abs(postTime - preExportState.time) < 0.05;
  const cOffA = postOffsetA && Math.abs(postOffsetA.r - preExportState.offsetA.r) < eps;
  const cZoom = Math.abs(postZoom - preExportState.zoom) < eps;
  const cPal = postPalette === preExportState.palette;
  const fRestoredPass = (cMode && cMMode && cN && cEvol && cTime && cOffA && cZoom && cPal);
  tests.push({
    name: 'F. Complete Interactive Session Restoration',
    passed: fRestoredPass,
    details: `Mode: ${postMode}, n: ${postN}, evolving: ${postEvolving}, time: ${postTime}, zoom: ${postZoom}, palette: ${postPalette}`
  });

  // --- VERIFICATION G: No accumulation collision with RAF loop ---
  const gPass = exportActiveCheck && concurrentRendersDuringExport === 0;
  tests.push({
    name: 'G. Zero RAF Collision During Export',
    passed: gPass,
    details: `isExporting set: ${exportActiveCheck}, concurrent render calls: ${concurrentRendersDuringExport}`
  });

  // --- VERIFICATION H: Temporary export resources deleted ---
  const texturesDeleted = createdTextures.every(t => !gl.isTexture(t));
  const fbosDeleted = createdFbos.every(f => !gl.isFramebuffer(f));
  tests.push({
    name: 'H. Memory Safety & Temporary GL Resource Deletion',
    passed: texturesDeleted && fbosDeleted,
    details: `Created textures (${createdTextures.length}) all deleted: ${texturesDeleted}; Created FBOs (${createdFbos.length}) all deleted: ${fbosDeleted}`
  });

  // --- VERIFICATION I: Normal 3840x2160 export still works ---
  app.setExportType('standard');
  const stdBlob = await renderer.exportPNG(math, { width: 3840, height: 2160, accumFrames: 5, filename: 'test_std_4k.png' });
  let stdW = 0, stdH = 0;
  if (stdBlob instanceof Blob) {
    const stdBmp = await createImageBitmap(stdBlob);
    stdW = stdBmp.width;
    stdH = stdBmp.height;
  }
  const iPass = (stdBlob instanceof Blob && stdBlob.size > 0 && stdW === 3840 && stdH === 2160);
  tests.push({
    name: 'I. Normal Standard Export Still Operational (3840×2160 4K)',
    passed: iPass,
    details: `Exported standard 4K image verified: ${stdW} × ${stdH}, size: ${(stdBlob ? stdBlob.size / 1024 : 0).toFixed(1)} KB, type: ${stdBlob ? stdBlob.type : ''}`
  });

  // --- VERIFICATION J: Reference / Explore / Randomize / Presets still work ---
  app.setMode('reference');
  const jRef = app.mode === 'reference' && math.n === 16;
  app.setMode('explore');
  const jExp = app.mode === 'explore';
  app.randomize('conradi-like');
  const jRnd = math.n === 16;
  const stormPreset = CURATED_PRESETS.find(p => p.name.includes('Filament Storm'));
  app.loadPresetObject(stormPreset);
  const jPreset = math.n === 24 && renderer.activePalette === 'amethyst';

  tests.push({
    name: 'J. Core Product Architecture Fully Functional',
    passed: jRef && jExp && jRnd && jPreset,
    details: `Reference Mode: ${jRef}, Explore Mode: ${jExp}, Randomize: ${jRnd}, Presets: ${jPreset}`
  });

  // Post Report
  fetch('/refmaster_report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tests)
  });
}

window.addEventListener('load', runTests);
</script>
</body>
</html>
"""

with open("test_reference_master.html", "w", encoding='utf-8') as f:
    f.write(html_test)

done_event = threading.Event()
report_results = None

class TestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global report_results
        if self.path == '/refmaster_report':
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
    f"http://localhost:{PORT}/test_reference_master.html"
]

print("Launching Chrome test runner for Reference Master Validation Suite...")
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

done = done_event.wait(timeout=40.0)
proc.terminate()
httpd.shutdown()

if done and report_results:
    all_passed = True
    print("\n=======================================================")
    print("REFERENCE MASTER TARGETED VALIDATION RESULTS")
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
