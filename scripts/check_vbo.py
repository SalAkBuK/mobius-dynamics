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

  // Render 1 frame
  math.update(0.016, renderer.zoom);
  renderer.render(math, 0.016);

  const gl = renderer.gl;

  // Read back simVbo
  gl.bindBuffer(gl.ARRAY_BUFFER, renderer.simVbos[renderer.vboCur]);
  const vboData = new Float32Array(16);
  gl.getBufferSubData(gl.ARRAY_BUFFER, 0, vboData);

  document.getElementById('log').innerText = JSON.stringify({
    p0: Array.from(vboData.slice(0, 4)),
    p1: Array.from(vboData.slice(4, 8)),
    p2: Array.from(vboData.slice(8, 12)),
    p3: Array.from(vboData.slice(12, 16)),
    err: gl.getError()
  });
} catch (e) {
  document.getElementById('log').innerText = 'ERROR: ' + e.message + '\\n' + e.stack;
}
</script>
</body>
</html>"""

with open('test_read_vbo.html', 'w') as f:
    f.write(html)

PORT = 8795
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
    f'http://localhost:{PORT}/test_read_vbo.html'
]
res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
for line in res.stdout.splitlines():
    if 'p0' in line or 'ERROR' in line:
        print(line)

httpd.shutdown()
