import http.server
import socketserver
import threading
import subprocess
import json

PORT = 8796
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"

done_event = threading.Event()
report_results = None

class TestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global report_results
        if self.path == '/edge_cases_report':
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

runner_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<iframe id="test-frame" src="http://localhost:{PORT}/index.html" style="width:1200px; height:800px; border:none;"></iframe>
<script>
const frame = document.getElementById('test-frame');
frame.onload = async () => {{
  const frameWin = frame.contentWindow;
  const frameDoc = frame.contentDocument;
  const tests = [];

  try {{
    let app = frameWin.__app;
    for (let i = 0; i < 50 && !app; i++) {{
      await new Promise(r => setTimeout(r, 100));
      app = frameWin.__app;
    }}

    await new Promise(r => setTimeout(r, 600));
    const holdCanvas = frameDoc.getElementById('export-display-hold');

    // TEST 1: Simulate Export Error Mid-Pass
    const origExportPNG = app.renderer.exportPNG.bind(app.renderer);
    app.renderer.exportPNG = async function() {{
      // Simulate failure mid-export
      throw new Error("Simulated GPU Out-Of-Memory During Export");
    }};

    app.setExportType('standard');
    try {{
      await app.startExport();
    }} catch (e) {{
      // Handled internally in startExport
    }}

    // Check overlay removal and state restore on export failure
    await new Promise(r => setTimeout(r, 300));

    const overlayRemovedOnFailure = holdCanvas && holdCanvas.style.display === 'none';
    tests.push({{
      name: '1. Export Failure Recovery: Overlay Removed Safely & State Restored',
      passed: !app.isExporting && !app.renderer.isExporting && overlayRemovedOnFailure,
      details: `app.isExporting: ${{app.isExporting}}, overlay display: "${{holdCanvas ? holdCanvas.style.display : 'none'}}"`
    }});

    // Restore real exportPNG
    app.renderer.exportPNG = origExportPNG;

    // TEST 2: Rapid consecutive export calls without delay
    // Test that display hold activation resets _pendingHoldRemoval and properly handles consecutive invocations
    app.showExportDisplayHold();
    const holdVisible1 = holdCanvas.style.display === 'block';
    const pendingFlagReset = (app._pendingHoldRemoval === false);
    app.scheduleDisplayHoldRemoval();
    // Immediately re-trigger show before removal timeout
    app.showExportDisplayHold();
    const holdVisible2 = holdCanvas.style.display === 'block';
    const pendingFlagReset2 = (app._pendingHoldRemoval === false);
    app.hideExportDisplayHold();
    const holdHidden = holdCanvas.style.display === 'none';

    tests.push({{
      name: '2. Rapid Export Display Hold State Transitions & Race Isolation',
      passed: holdVisible1 && pendingFlagReset && holdVisible2 && pendingFlagReset2 && holdHidden,
      details: `holdVisible1: ${{holdVisible1}}, pendingReset: ${{pendingFlagReset}}, holdVisible2: ${{holdVisible2}}, pendingReset2: ${{pendingFlagReset2}}, holdHidden: ${{holdHidden}}`
    }});

    // TEST 3: Window resize during display hold does not cause crash or buffer corruption
    app.showExportDisplayHold();
    // Simulate window resize event while hold is active
    app.onResize();
    const holdAfterResize = holdCanvas.style.display === 'block';
    app.scheduleDisplayHoldRemoval();
    await new Promise(r => setTimeout(r, 200));
    const holdRemovedAfterResize = holdCanvas.style.display === 'none';

    tests.push({{
      name: '3. Resize During Export Display Hold Handled Gracefully',
      passed: holdAfterResize && holdRemovedAfterResize,
      details: `holdAfterResize: ${{holdAfterResize}}, holdRemoved: ${{holdRemovedAfterResize}}`
    }});

    fetch('/edge_cases_report', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(tests)
    }});
  }} catch (err) {{
    fetch('/edge_cases_report', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify([{{ name: 'Edge Case Test Error', passed: false, details: `${{err.message}} \n${{err.stack}}` }}])
    }});
  }}
}};
</script>
</body>
</html>
"""

with open("test_export_failure_and_edge_cases.html", "w", encoding='utf-8') as f:
    f.write(runner_html)

cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--no-sandbox",
    "--use-gl=angle",
    "--use-angle=d3d11",
    "--window-size=1200,800",
    f"http://localhost:{PORT}/test_export_failure_and_edge_cases.html"
]

print("Launching Chrome test runner for Edge Cases & Failure Recovery...")
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

done = done_event.wait(timeout=30.0)
proc.terminate()
httpd.shutdown()

if done and report_results:
    all_passed = True
    print("\n=======================================================")
    print("EXPORT FAILURE & EDGE CASES TEST RESULTS")
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
