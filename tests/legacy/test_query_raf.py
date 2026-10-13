import subprocess, json, time

html = """<!DOCTYPE html>
<html>
<body>
<canvas id="c" width="800" height="600"></canvas>
<div id="res">waiting...</div>
<script>
window.onload = function() {
    const canvas = document.getElementById('c');
    const gl = canvas.getContext('webgl2');
    const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');

    const q1 = gl.createQuery();
    const q2 = gl.createQuery();
    let frame = 0;
    let queryIssued = false;

    function render() {
        if (!queryIssued) {
            gl.beginQuery(ext.TIME_ELAPSED_EXT, q1);
            gl.clearColor(0.1, 0.2, 0.3, 1.0);
            gl.clear(gl.COLOR_BUFFER_BIT);
            gl.endQuery(ext.TIME_ELAPSED_EXT);

            gl.beginQuery(ext.TIME_ELAPSED_EXT, q2);
            gl.clearColor(0.4, 0.5, 0.6, 1.0);
            gl.clear(gl.COLOR_BUFFER_BIT);
            gl.endQuery(ext.TIME_ELAPSED_EXT);
            gl.flush();
            queryIssued = true;
        } else {
            const avail1 = gl.getQueryParameter(q1, gl.QUERY_RESULT_AVAILABLE);
            const avail2 = gl.getQueryParameter(q2, gl.QUERY_RESULT_AVAILABLE);
            if (avail1 && avail2) {
                const ns1 = gl.getQueryParameter(q1, gl.QUERY_RESULT);
                const ns2 = gl.getQueryParameter(q2, gl.QUERY_RESULT);
                document.getElementById('res').innerText = JSON.stringify({
                    frame: frame,
                    q1_ms: ns1 / 1e6,
                    q2_ms: ns2 / 1e6
                });
                document.body.setAttribute('data-done', 'true');
                return;
            }
        }
        frame++;
        if (frame < 60) {
            requestAnimationFrame(render);
        } else {
            document.getElementById('res').innerText = "timeout";
            document.body.setAttribute('data-done', 'true');
        }
    }
    requestAnimationFrame(render);
};
</script>
</body>
</html>
"""

with open("test_query_raf.html", "w") as f:
    f.write(html)

import http.server, socketserver, threading
PORT = 8795
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
    "--virtual-time-budget=2000",
    "--dump-dom",
    f"http://localhost:{PORT}/test_query_raf.html"
]
time.sleep(1.0)
res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
print("RESULT:")
for line in res.stdout.splitlines():
    if "q1_ms" in line or "timeout" in line:
        print(line)

httpd.shutdown()
