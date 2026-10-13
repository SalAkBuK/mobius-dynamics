import subprocess

html = """<!DOCTYPE html>
<html>
<body>
<canvas id="c" width="1200" height="800"></canvas>
<div id="res">running...</div>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

window.onerror = function(msg, url, line, col, err) {
  document.getElementById('res').innerText = 'ERROR: ' + msg + ' at line ' + line + ' ' + (err ? err.stack : '');
};

try {
  const c = document.getElementById('c');
  const m = new MathSystem();
  const r = new MobiusRenderer(c);
  for (let i = 0; i < 10; i++) {
    r.render(m, 0.016);
  }
  document.getElementById('res').innerText = 'SUCCESS render 10, accum: ' + r.accumulationFrames;
} catch (e) {
  document.getElementById('res').innerText = 'TRY-CATCH: ' + e.message + ' ' + e.stack;
}
</script>
</body>
</html>
"""

with open("test_render_err.html", "w") as f:
    f.write(html)

import http.server, socketserver, threading
PORT = 8783
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
    "--dump-dom",
    f"http://localhost:{PORT}/test_render_err.html"
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
