import subprocess, time, http.server, socketserver, threading, os

html = """<!DOCTYPE html>
<html>
<body>
<div id="res">running</div>
<script>
let frames = 0;
const t0 = performance.now();
function loop(now) {
  frames++;
  if (now - t0 >= 1000) {
    document.getElementById('res').innerText = JSON.stringify({frames: frames, elapsed: now - t0});
    return;
  }
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
</script>
</body>
</html>
"""

with open("test_raf.html", "w") as f:
    f.write(html)

PORT = 8785
httpd = socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

time.sleep(1.0)
cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--no-sandbox",
    "--use-gl=angle",
    "--use-angle=d3d11",
    "--dump-dom",
    f"http://localhost:{PORT}/test_raf.html"
]

t0 = time.time()
while time.time() - t0 < 5:
    res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    for line in res.stdout.splitlines():
        if '"frames"' in line:
            print("FOUND:", line)
            httpd.shutdown()
            exit(0)
    time.sleep(0.5)

httpd.shutdown()
print("TIMEOUT")
