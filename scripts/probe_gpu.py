import subprocess, re, json

html = """<!DOCTYPE html>
<html>
<body>
<canvas id="c"></canvas>
<div id="info"></div>
<script>
window.onload = function() {
    const gl = document.getElementById("c").getContext("webgl2");
    const dbg = gl.getExtension("WEBGL_debug_renderer_info");
    const renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : "unknown";
    const vendor = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : "unknown";
    const timerExt = gl.getExtension("EXT_disjoint_timer_query_webgl2");
    const exts = gl.getSupportedExtensions();
    document.getElementById("info").innerText = JSON.stringify({
        renderer: renderer,
        vendor: vendor,
        timerExt: !!timerExt,
        extensions: exts
    });
};
</script>
</body>
</html>
"""

with open("probe_page.html", "w") as f:
    f.write(html)

import http.server, socketserver, threading
PORT = 8799
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
    f"http://localhost:{PORT}/probe_page.html"
]
res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
for line in res.stdout.splitlines():
    if "renderer" in line:
        print(line)

httpd.shutdown()
