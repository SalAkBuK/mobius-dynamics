import subprocess, json, time

html = """<!DOCTYPE html>
<html>
<head>
<style>
body { margin: 0; background: #000; color: #fff; font-family: monospace; }
canvas { width: 1200px; height: 800px; display: block; }
#res { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.8); padding: 10px; }
</style>
</head>
<body>
<div id="res">starting...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

const canvas = document.getElementById('c');
const math = new MathSystem();
const renderer = new MobiusRenderer(canvas);
const gl = renderer.gl;
const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');

document.getElementById('res').innerText = JSON.stringify({
    extSupported: !!ext,
    particles: renderer.numParticles,
    canvasW: canvas.width,
    canvasH: canvas.height
});
document.body.setAttribute('data-ready', 'true');
</script>
</body>
</html>
"""

with open("test_full_inst.html", "w") as f:
    f.write(html)

import http.server, socketserver, threading
PORT = 8794
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
    "--dump-dom",
    f"http://localhost:{PORT}/test_full_inst.html"
]
time.sleep(1.0)
res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
print("RESULT:")
for line in res.stdout.splitlines():
    if "extSupported" in line:
        print(line)

httpd.shutdown()
