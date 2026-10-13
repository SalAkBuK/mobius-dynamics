import subprocess, json

html = """<!DOCTYPE html>
<html>
<body>
<canvas id="c" width="800" height="600"></canvas>
<div id="res">running...</div>
<script>
window.onload = async function() {
    const canvas = document.getElementById('c');
    const gl = canvas.getContext('webgl2');
    const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');
    if (!ext) {
        document.getElementById('res').innerText = JSON.stringify({ supported: false });
        return;
    }

    const query = gl.createQuery();
    gl.beginQuery(ext.TIME_ELAPSED_EXT, query);
    gl.clearColor(0.2, 0.4, 0.6, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.endQuery(ext.TIME_ELAPSED_EXT);
    gl.flush();

    // Poll for result
    let available = false;
    let disjoint = false;
    let timeElapsed = 0;
    for (let i = 0; i < 200; i++) {
        await new Promise(r => setTimeout(r, 10));
        disjoint = gl.getParameter(ext.GPU_DISJOINT_EXT);
        available = gl.getQueryParameter(query, gl.QUERY_RESULT_AVAILABLE);
        if (available) {
            timeElapsed = gl.getQueryParameter(query, gl.QUERY_RESULT);
            break;
        }
    }

    document.getElementById('res').innerText = JSON.stringify({
        supported: true,
        available: available,
        disjoint: disjoint,
        timeElapsedNs: timeElapsed,
        timeElapsedMs: timeElapsed / 1e6
    });
};
</script>
</body>
</html>
"""

with open("test_timer_query.html", "w") as f:
    f.write(html)

import http.server, socketserver, threading
PORT = 8798
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
    f"http://localhost:{PORT}/test_timer_query.html"
]
import time
time.sleep(1.0)
res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
for line in res.stdout.splitlines():
    if "timeElapsed" in line or "supported" in line:
        print(line)

httpd.shutdown()
