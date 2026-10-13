import http.server, socketserver, threading, subprocess, time, os

html = """<!DOCTYPE html>
<html>
<body>
<div id="log">waiting...</div>
<canvas id="c" width="800" height="600"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

try {
  const canvas = document.getElementById('c');
  const math = new MathSystem();
  const renderer = new MobiusRenderer(canvas);
  math.setMorphology('lace');

  for (let i = 0; i < 30; i++) {
    math.update(0.016, renderer.zoom);
    renderer.render(math, 0.016);
  }

  const gl = renderer.gl;
  const pixels = new Uint8Array(800 * 600 * 4);
  gl.readPixels(0, 0, 800, 600, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
  let maxR = 0, maxG = 0, maxB = 0, nonZero = 0;
  for (let i = 0; i < pixels.length; i += 4) {
    if (pixels[i] > maxR) maxR = pixels[i];
    if (pixels[i+1] > maxG) maxG = pixels[i+1];
    if (pixels[i+2] > maxB) maxB = pixels[i+2];
    if (pixels[i] > 0 || pixels[i+1] > 0 || pixels[i+2] > 0) nonZero++;
  }
  const dUrl = canvas.toDataURL();
  document.getElementById('log').innerText = JSON.stringify({ maxR, maxG, maxB, nonZero, total: 800*600, dataUrlLen: dUrl.length, err: gl.getError() });
} catch (e) {
  document.getElementById('log').innerText = 'ERROR: ' + e.message + '\\n' + e.stack;
}
</script>
</body>
</html>"""

with open('test_canvas_read.html', 'w') as f:
    f.write(html)

PORT = 8792
Handler = http.server.SimpleHTTPRequestHandler
httpd = socketserver.TCPServer(('', PORT), Handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

cmd = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    '--headless=new',
    '--no-sandbox',
    '--use-gl=angle',
    '--use-angle=d3d11',
    '--dump-dom',
    f'http://localhost:{PORT}/test_canvas_read.html'
]
res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
for line in res.stdout.splitlines():
    if 'maxR' in line or 'ERROR' in line:
        print(line)

httpd.shutdown()
