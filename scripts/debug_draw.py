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
  renderer.resize(800, 600);
  math.setMorphology('lace');

  // Check splatVs compilation / uniforms
  const gl = renderer.gl;

  // Render 60 frames
  for (let i = 0; i < 60; i++) {
    math.update(0.016, renderer.zoom);
    renderer.render(math, 0.016);
  }

  // Check VBO age
  gl.bindBuffer(gl.ARRAY_BUFFER, renderer.simVbos[renderer.vboCur]);
  const vbo = new Float32Array(40);
  gl.getBufferSubData(gl.ARRAY_BUFFER, 0, vbo);

  // Check readPixels from canvas
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  const screen = new Uint8Array(800 * 600 * 4);
  gl.readPixels(0, 0, 800, 600, gl.RGBA, gl.UNSIGNED_BYTE, screen);

  let maxR = 0, maxG = 0, maxB = 0, nonZero = 0;
  for (let i = 0; i < screen.length; i += 4) {
    if (screen[i] > maxR) maxR = screen[i];
    if (screen[i+1] > maxG) maxG = screen[i+1];
    if (screen[i+2] > maxB) maxB = screen[i+2];
    if (screen[i] > 0 || screen[i+1] > 0 || screen[i+2] > 0) nonZero++;
  }

  document.getElementById('log').innerText = JSON.stringify({
    ages: [vbo[2], vbo[6], vbo[10], vbo[14], vbo[18]],
    pos0: [vbo[0], vbo[1]],
    maxR, maxG, maxB, nonZero,
    total: 800*600,
    glErr: gl.getError()
  });
} catch (e) {
  document.getElementById('log').innerText = 'ERROR: ' + e.message + '\\n' + e.stack;
}
</script>
</body>
</html>"""

with open('test_debug_draw.html', 'w') as f:
    f.write(html)

PORT = 8797
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
    f'http://localhost:{PORT}/test_debug_draw.html'
]
res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
for line in res.stdout.splitlines():
    if 'ages' in line or 'ERROR' in line:
        print(line)

httpd.shutdown()
