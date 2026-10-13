import subprocess, time

html = """<!DOCTYPE html>
<html>
<body>
<canvas id="c" width="1200" height="800"></canvas>
<div id="res">running...</div>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

window.onload = async function() {
  const c = document.getElementById('c');
  const m = new MathSystem();
  const r = new MobiusRenderer(c);
  r.setParticleCount(589824);
  r.setStepsOverride(16);

  // Warmup 5 frames
  for (let i = 0; i < 5; i++) {
    r.render(m, 0.016);
  }
  r.gl.finish();

  const t0 = performance.now();
  for (let i = 0; i < 30; i++) {
    r.render(m, 0.016);
  }
  r.gl.finish();
  const t1 = performance.now();

  const total = t1 - t0;
  const perFrame = total / 30;

  // Poll profiler
  for (let w = 0; w < 30; w++) {
    r.profiler.pollOldQueries();
    if (r.profiler.metrics.gpuMs > 0) break;
    await new Promise(res => setTimeout(res, 20));
  }

  document.getElementById('res').innerText = JSON.stringify({
    totalMs: total,
    perFrameMs: perFrame,
    metrics: r.profiler.metrics
  });
};
</script>
</body>
</html>
"""

with open("test_bench_timing.html", "w") as f:
    f.write(html)

import http.server, socketserver, threading
PORT = 8784
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
    "--virtual-time-budget=10000",
    "--dump-dom",
    f"http://localhost:{PORT}/test_bench_timing.html"
]
time.sleep(1.0)
res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
import re
m = re.search(r'<div id="res">(.*?)</div>', res.stdout)
if m:
    print("OUTPUT:", m.group(1))
else:
    print("STDOUT:", res.stdout[:500])

httpd.shutdown()
