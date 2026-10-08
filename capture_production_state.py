import http.server
import socketserver
import threading
import subprocess
import json
import os
import base64
import urllib.parse

PORT = 8912
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
done_event = threading.Event()

class CaptureHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/save':
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
            data_url = payload.get('dataUrl', '').split(',', 1)[1]
            img_bytes = base64.b64decode(data_url)
            
            with open(os.path.join(DIRECTORY, "verify_production_persistence_live.png"), "wb") as f:
                f.write(img_bytes)
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            done_event.set()

    def log_message(self, format, *args):
        pass

html_page = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Live Production Render</title></head>
<body style="margin:0; background:#010307; overflow:hidden;">
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

window.onload = async function() {
  const canvas = document.getElementById('c');
  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);
  math.update(0.0, 1.65);

  const renderer = new MobiusRenderer(canvas);
  renderer.adaptive.getDpr = () => 1.0;
  renderer.resize(1200, 800);
  renderer.zoom = 1.65;
  renderer.targetZoom = 1.65;
  renderer.viewCenter = [0.0, 0.0];
  renderer.targetViewCenter = [0.0, 0.0];
  renderer.bloomEnabled = true;
  renderer.viewMode = 0;

  // Render for 10 seconds (600 frames) under autonomous drift (p=0.9985)
  for (let f = 0; f < 600; f++) {
    math.update(0.016, 1.65);
    renderer.render(math, 0.016);
    if (f % 30 === 0) await new Promise(r => requestAnimationFrame(r));
  }

  // Draw to canvas and send to server
  renderer.render(math, 0.0);
  renderer.gl.finish();
  const dataUrl = canvas.toDataURL('image/png');
  await fetch('/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataUrl })
  });
};
</script>
</body>
</html>"""

def main():
    test_html = os.path.join(DIRECTORY, "capture_production_live.html")
    with open(test_html, "w", encoding="utf-8") as f:
        f.write(html_page)

    httpd = socketserver.TCPServer(("127.0.0.1", PORT), CaptureHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    chrome_cmd = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu-watchdog",
        "--use-gl=angle",
        "--use-angle=d3d11",
        "--window-size=1200,800",
        f"http://127.0.0.1:{PORT}/capture_production_live.html"
    ]

    proc = subprocess.Popen(chrome_cmd)
    done_event.wait(timeout=25)
    proc.terminate()
    httpd.shutdown()
    httpd.server_close()
    print("Saved verify_production_persistence_live.png")

if __name__ == "__main__":
    main()
