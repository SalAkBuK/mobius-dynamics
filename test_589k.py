import subprocess

html = """<!DOCTYPE html>
<html>
<body>
<canvas id="c" width="1200" height="800"></canvas>
<div id="res">running...</div>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

window.onerror = (e) => { document.getElementById('res').innerText = 'ERROR: ' + e; };

try {
  const c = document.getElementById('c');
  const m = new MathSystem();
  const r = new MobiusRenderer(c);
  r.setParticleCount(589824);
  r.setStepsOverride(16);
  r.render(m, 0.016);
  document.getElementById('res').innerText = JSON.stringify({
    success: true,
    particles: r.numParticles,
    steps: r.stepsPerFrame,
    draws: r.profiler.drawCallCount
  });
} catch (err) {
  document.getElementById('res').innerText = 'CATCH: ' + err.message + ' ' + err.stack;
}
</script>
</body>
</html>
"""

with open("test_589k.html", "w") as f:
    f.write(html)

import http.server, socketserver, threading
PORT = 8785
socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--no-sandbox",
    "--use-gl=angle",
    "--use-angle=d3d11",
    "--window-size=1200,800",
    "--virtual-time-budget=2000",
    "--dump-dom",
    f"http://localhost:{PORT}/test_589k.html"
]
import time
time.sleep(1.0)
res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
import re
m = re.search(r'<div id="res">(.*?)</div>', res.stdout)
if m:
    print("OUTPUT:", m.group(1))
else:
    print("STDOUT:", res.stdout[:500])

httpd.shutdown()
