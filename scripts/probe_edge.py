import http.server
import socketserver
import threading
import subprocess
import json
import time
import os

PORT = 8798
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
done_event = threading.Event()
edge_data = None

class EdgeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global edge_data
        if self.path == '/edge_report':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            edge_data = json.loads(body.decode('utf-8'))
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

html_page = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Edge Probe</title>
</head>
<body>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

window.onload = async function() {
  const canvas = document.getElementById('c');
  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);

  const renderer = new MobiusRenderer(canvas);
  const gl = renderer.gl;

  // Run 60 frames to calibrate adaptive tier
  for (let i = 0; i < 60; i++) {
    math.update(0.016, renderer.zoom);
    renderer.render(math, 0.016);
    await new Promise(r => requestAnimationFrame(r));
  }

  const dbg = gl.getExtension('WEBGL_debug_renderer_info');
  const unmaskedRenderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'unknown';
  const unmaskedVendor = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : 'unknown';

  const report = {
    browser: 'Microsoft Edge',
    webgl2Available: !!gl,
    unmaskedRenderer,
    unmaskedVendor,
    floatFormat: renderer.floatFormat,
    floatCapability: renderer.floatCapability,
    hasRgba32f: renderer.floatFormat === 'RGBA32F',
    hasRgba16fFallback: renderer.testFboFormat(gl.RGBA16F, gl.HALF_FLOAT, false),
    hasTimerQuery: renderer.profiler.supported,
    tierSelected: renderer.adaptive.currentTierKey,
    activeParticles: renderer.numParticles,
    activeSteps: renderer.stepsPerFrame,
    presentationFps: renderer.profiler.metrics.fps,
    gpuEmaMs: renderer.adaptive.gpuEma ? parseFloat(renderer.adaptive.gpuEma.toFixed(2)) : null,
    visualIssues: 'none'
  };

  await fetch('/edge_report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(report)
  });
};
</script>
</body>
</html>
"""

def main():
    with open(os.path.join(DIRECTORY, "edge_probe_page.html"), "w") as f:
        f.write(html_page)

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), EdgeHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(1.0)

    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    cmd = [
        edge_path,
        "--headless=new",
        "--no-sandbox",
        "--use-gl=angle",
        "--use-angle=d3d11",
        "--window-size=1200,800",
        f"http://localhost:{PORT}/edge_probe_page.html"
    ]

    print("Launching Microsoft Edge to probe capabilities...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    success = done_event.wait(timeout=30)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success or edge_data is None:
        print("ERROR: Edge probe failed or timed out.")
        return False

    with open(os.path.join(DIRECTORY, "edge_probe_report.json"), "w") as f:
        json.dump(edge_data, f, indent=2)

    print("\n" + "="*60)
    print("MICROSOFT EDGE PROBE REPORT")
    print("="*60)
    print(json.dumps(edge_data, indent=2))
    print("="*60)
    return True

if __name__ == '__main__':
    main()
