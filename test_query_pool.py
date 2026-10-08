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
    
    // Test multiple queries in sequence
    const q1 = gl.createQuery();
    const q2 = gl.createQuery();
    
    gl.beginQuery(ext.TIME_ELAPSED_EXT, q1);
    gl.clearColor(0.1, 0.2, 0.3, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.endQuery(ext.TIME_ELAPSED_EXT);
    
    gl.beginQuery(ext.TIME_ELAPSED_EXT, q2);
    gl.clearColor(0.4, 0.5, 0.6, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.endQuery(ext.TIME_ELAPSED_EXT);
    
    gl.flush();
    
    let res1 = 0, res2 = 0;
    for (let i = 0; i < 200; i++) {
        await new Promise(r => setTimeout(r, 10));
        if (gl.getQueryParameter(q1, gl.QUERY_RESULT_AVAILABLE) &&
            gl.getQueryParameter(q2, gl.QUERY_RESULT_AVAILABLE)) {
            res1 = gl.getQueryParameter(q1, gl.QUERY_RESULT);
            res2 = gl.getQueryParameter(q2, gl.QUERY_RESULT);
            break;
        }
    }
    
    document.getElementById('res').innerText = JSON.stringify({
        q1_ns: res1,
        q2_ns: res2,
        q1_ms: res1 / 1e6,
        q2_ms: res2 / 1e6
    });
};
</script>
</body>
</html>
"""

with open("test_query_pool.html", "w") as f:
    f.write(html)

import http.server, socketserver, threading
PORT = 8797
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
    f"http://localhost:{PORT}/test_query_pool.html"
]
import time
time.sleep(1.0)
res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
print("FULL STDOUT:")
print(res.stdout)

httpd.shutdown()
