import http.server
import socketserver
import threading
import subprocess
import json
import time

PORT = 8795
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"

done_event = threading.Event()
report_results = None

class TestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global report_results
        if self.path == '/live_index_report':
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

# We inject a test harness into index.html via query param or test runner
runner_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<iframe id="test-frame" src="http://localhost:{PORT}/index.html" style="width:1200px; height:800px; border:none;"></iframe>
<script>
window.onerror = function(msg, url, line, col, err) {{
  fetch('/live_index_report', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify([{{ name: 'Runner Error', passed: false, details: `${{msg}} at ${{line}}:${{col}}` }}])
  }});
}};

const frame = document.getElementById('test-frame');
frame.onload = async () => {{
  const frameWin = frame.contentWindow;
  const frameDoc = frame.contentDocument;
  const tests = [];

  try {{
    // Wait for App to initialize
    let app = frameWin.__app;
    for (let i = 0; i < 50 && !app; i++) {{
      await new Promise(r => setTimeout(r, 100));
      app = frameWin.__app;
    }}
    if (!app) throw new Error("window.__app not available in index.html");

    // 1. Initial State Check
    await new Promise(r => setTimeout(r, 800)); // allow initial render
    const valA = frameDoc.getElementById('val-a')?.innerText || '';
    const valN = frameDoc.getElementById('val-n')?.innerText || '';
    tests.push({{
      name: '1. Live index.html Fresh Load: Reference Mode n=16 Readout Populated',
      passed: app.mode === 'reference' && app.math.n === 16 && valA.includes('-0.755') && !valA.includes('--') && valN === '16',
      details: `mode: ${{app.mode}}, n: ${{app.math.n}}, val-a: "${{valA}}", val-n: "${{valN}}"`
    }});

    const gl = app.renderer.gl;
    let contextLostCount = 0;
    gl.canvas.addEventListener('webglcontextlost', (e) => {{
      contextLostCount++;
      e.preventDefault();
    }});

    // 2. Start Standard 4K Export with 120 passes
    app.setExportType('standard');
    app.exportWidth = 3840;
    app.exportHeight = 2160;
    app.exportPasses = 120;

    let overlayVisibleDuring = false;
    let overlayHasPixelsDuring = false;
    let readoutADuring = null;
    let isExportingDuring = false;

    const exportPromise = app.startExport();

    const holdCanvas = frameDoc.getElementById('export-display-hold');
    const interval = setInterval(() => {{
      const pctTxt = frameDoc.getElementById('export-status-pct')?.innerText || '0%';
      const pct = parseInt(pctTxt, 10);
      if (pct >= 15 && !overlayHasPixelsDuring) {{
        isExportingDuring = app.isExporting;
        readoutADuring = frameDoc.getElementById('val-a')?.innerText;
        if (holdCanvas && holdCanvas.style.display !== 'none' && holdCanvas.width > 0 && holdCanvas.height > 0) {{
          overlayVisibleDuring = true;
          const ctx = holdCanvas.getContext('2d');
          const px = ctx.getImageData(Math.floor(holdCanvas.width * 0.4), Math.floor(holdCanvas.height * 0.4), 1, 1).data;
          if (px[0] > 0 || px[1] > 0 || px[2] > 0) {{
            overlayHasPixelsDuring = true;
          }}
        }}
      }}
    }}, 40);

    const blob = await exportPromise;
    clearInterval(interval);

    tests.push({{
      name: '2. Live index.html Standard 4K 120-pass: Artwork Overlay Active Throughout Export',
      passed: overlayVisibleDuring && overlayHasPixelsDuring && isExportingDuring,
      details: `Overlay displayed: ${{overlayVisibleDuring}}, has pixels: ${{overlayHasPixelsDuring}}, isExporting: ${{isExportingDuring}}`
    }});

    tests.push({{
      name: '3. Live index.html Standard 4K 120-pass: Readout Retains Valid Values',
      passed: readoutADuring && readoutADuring.includes('-0.755') && !readoutADuring.includes('--'),
      details: `Readout during export: "${{readoutADuring}}"`
    }});

    tests.push({{
      name: '4. Live index.html Standard 4K 120-pass: No WebGL Context Loss',
      passed: contextLostCount === 0 && !gl.isContextLost(),
      details: `contextLostCount: ${{contextLostCount}}, isContextLost: ${{gl.isContextLost()}}`
    }});

    tests.push({{
      name: '5. Live index.html Standard 4K 120-pass: High-Res PNG Blob Generated',
      passed: (blob instanceof frameWin.Blob || blob instanceof Blob) && blob.size > 1000000 && blob.type === 'image/png',
      details: `Blob size: ${{blob ? (blob.size / (1024*1024)).toFixed(2) : 0}} MB, type: ${{blob ? blob.type : 'none'}}`
    }});

    // Wait for onscreen RAF resume
    await new Promise(r => setTimeout(r, 200));

    const overlayHiddenAfter = holdCanvas && holdCanvas.style.display === 'none';
    tests.push({{
      name: '6. Live index.html Standard 4K 120-pass: Overlay Removed & RAF Resumes',
      passed: !app.isExporting && overlayHiddenAfter,
      details: `app.isExporting: ${{app.isExporting}}, overlay display: "${{holdCanvas ? holdCanvas.style.display : 'none'}}"`
    }});

    // 7. Verify Reference Master Export in live index.html
    app.setExportType('reference_master');
    app.refMasterPasses = 120;

    let refOverlayVisibleDuring = false;
    let refOverlayHasPixelsDuring = false;
    let refReadoutADuring = null;

    const refPromise = app.startExport();

    const refInterval = setInterval(() => {{
      const pctTxt = frameDoc.getElementById('export-status-pct')?.innerText || '0%';
      const pct = parseInt(pctTxt, 10);
      if (pct >= 15 && !refOverlayHasPixelsDuring) {{
        refReadoutADuring = frameDoc.getElementById('val-a')?.innerText;
        if (holdCanvas && holdCanvas.style.display !== 'none' && holdCanvas.width > 0 && holdCanvas.height > 0) {{
          refOverlayVisibleDuring = true;
          const ctx = holdCanvas.getContext('2d');
          const px = ctx.getImageData(Math.floor(holdCanvas.width * 0.4), Math.floor(holdCanvas.height * 0.4), 1, 1).data;
          if (px[0] > 0 || px[1] > 0 || px[2] > 0) {{
            refOverlayHasPixelsDuring = true;
          }}
        }}
      }}
    }}, 40);

    const refBlob = await refPromise;
    clearInterval(refInterval);

    tests.push({{
      name: '7. Live index.html Reference Master 120-pass: Artwork Overlay Active Throughout',
      passed: refOverlayVisibleDuring && refOverlayHasPixelsDuring,
      details: `Overlay displayed: ${{refOverlayVisibleDuring}}, has pixels: ${{refOverlayHasPixelsDuring}}`
    }});

    tests.push({{
      name: '8. Live index.html Reference Master: Readout Populated Throughout',
      passed: refReadoutADuring && refReadoutADuring.includes('-0.755') && !refReadoutADuring.includes('--'),
      details: `Readout during master export: "${{refReadoutADuring}}"`
    }});

    tests.push({{
      name: '9. Live index.html Reference Master: Output PNG Verified',
      passed: (refBlob instanceof frameWin.Blob || refBlob instanceof Blob) && refBlob.size > 2000000 && refBlob.type === 'image/png',
      details: `Master PNG size: ${{refBlob ? (refBlob.size / (1024*1024)).toFixed(2) : 0}} MB`
    }});

    await new Promise(r => setTimeout(r, 200));

    tests.push({{
      name: '10. Live index.html Reference Master: Overlay Removed & Reference Preserved',
      passed: holdCanvas && holdCanvas.style.display === 'none' && app.mode === 'reference',
      details: `Overlay display: "${{holdCanvas ? holdCanvas.style.display : 'none'}}", mode: ${{app.mode}}`
    }});

    fetch('/live_index_report', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(tests)
    }});
  }} catch (err) {{
    fetch('/live_index_report', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify([{{ name: 'Live Harness Error', passed: false, details: `${{err.message}} \n${{err.stack}}` }}])
    }});
  }}
}};
</script>
</body>
</html>
"""

with open("test_live_index.html", "w", encoding='utf-8') as f:
    f.write(runner_html)

cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--no-sandbox",
    "--use-gl=angle",
    "--use-angle=d3d11",
    "--window-size=1200,800",
    f"http://localhost:{PORT}/test_live_index.html"
]

print("Launching Chrome test runner for Live index.html verification...")
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

done = done_event.wait(timeout=120.0)
proc.terminate()
httpd.shutdown()

if done and report_results:
    all_passed = True
    print("\n=======================================================")
    print("LIVE INDEX.HTML DEPLOYMENT REGRESSION TEST RESULTS")
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
