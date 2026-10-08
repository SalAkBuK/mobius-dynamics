import http.server, socketserver, threading, subprocess, time, os

html = """<!DOCTYPE html>
<html>
<body>
<div id="res">waiting...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script>
window.onload = function() {
  const canvas = document.getElementById('c');
  const gl = canvas.getContext('webgl2', { alpha: false, antialias: false, depth: false });
  gl.getExtension('EXT_color_buffer_float');

  const simVs = `#version 300 es
  in vec4 a_state;
  out vec4 v_state;
  uniform vec2 u_a, u_b, u_c, u_d;
  uniform float u_n, u_step;
  uint pcg(uint v) {
    uint state = v * 747796405u + 2891336453u;
    uint word = ((state >> ((state >> 28u) + 4u)) ^ state) * 277803737u;
    return (word >> 22u) ^ word;
  }
  float nextRand(inout uint seed) {
    seed = pcg(seed);
    return float(seed & 0x00FFFFFFu) / 16777216.0;
  }
  vec2 c_mul(vec2 x, vec2 y) { return vec2(x.x * y.x - x.y * y.y, x.x * y.y + x.y * y.x); }
  vec2 c_div(vec2 num, vec2 den) {
    float d = dot(den, den);
    return vec2((num.x * den.x + num.y * den.y) / d, (num.y * den.x - num.x * den.y) / d);
  }
  void main() {
    vec2 z = a_state.xy;
    float age = a_state.z;
    uint seed = uint(a_state.w) + uint(u_step * 1013904223.0) + uint(gl_VertexID * 1973);
    int n = int(u_n + 0.5);
    int k = int(nextRand(seed) * float(n)) % n;
    float ang = (6.28318530718 * float(k)) / float(n);
    vec2 omega = vec2(cos(ang), sin(ang));
    vec2 num = c_mul(u_a, z) + u_b;
    vec2 den = c_mul(u_c, z) + u_d;
    if (dot(den, den) < 1e-7 || dot(z, z) > 25.0 || age > 3500.0) {
      float r = 0.22 + nextRand(seed) * 0.40;
      float th = nextRand(seed) * 6.283185;
      z = vec2(r * cos(th), r * sin(th));
      age = 0.0;
    } else {
      z = c_mul(omega, c_div(num, den));
      age += 1.0;
    }
    v_state = vec4(z, age, float(seed & 0x00FFFFFFu));
  }
  `;

  const simFs = `#version 300 es\\nprecision highp float;\\nvoid main() {}`;

  const simV = gl.createShader(gl.VERTEX_SHADER); gl.shaderSource(simV, simVs); gl.compileShader(simV);
  const simF = gl.createShader(gl.FRAGMENT_SHADER); gl.shaderSource(simF, simFs); gl.compileShader(simF);
  const simProg = gl.createProgram();
  gl.attachShader(simProg, simV); gl.attachShader(simProg, simF);
  gl.transformFeedbackVaryings(simProg, ['v_state'], gl.SEPARATE_ATTRIBS);
  gl.linkProgram(simProg);

  const splatVs = `#version 300 es
  in vec4 a_state;
  out float v_discard;
  void main() {
    vec2 z = a_state.xy;
    float age = a_state.z;
    if (age < 20.0 || isnan(z.x) || isnan(z.y) || dot(z, z) > 25.0) {
      v_discard = 1.0;
      gl_Position = vec4(2.0, 2.0, 0.0, 1.0);
      gl_PointSize = 1.0;
      return;
    }
    v_discard = 0.0;
    gl_Position = vec4(z * 1.65, 0.0, 1.0);
    gl_PointSize = 1.0;
  }
  `;
  const splatFs = `#version 300 es\\nprecision highp float;\\nin float v_discard;\\nout vec4 o_photon;\\nvoid main() { if (v_discard > 0.5) discard; o_photon = vec4(0.0001, 0.00015, 0.00025, 1.0); }`;
  const splatV = gl.createShader(gl.VERTEX_SHADER); gl.shaderSource(splatV, splatVs); gl.compileShader(splatV);
  const splatF = gl.createShader(gl.FRAGMENT_SHADER); gl.shaderSource(splatF, splatFs); gl.compileShader(splatF);
  const splatProg = gl.createProgram();
  gl.attachShader(splatProg, splatV); gl.attachShader(splatProg, splatF);
  gl.linkProgram(splatProg);

  const count = 1048576;
  const data = new Float32Array(count * 4);
  for (let i = 0; i < count; i++) {
    const r = 0.25 + Math.random() * 0.35;
    const th = Math.random() * 6.283185;
    data[i*4+0] = r * Math.cos(th); data[i*4+1] = r * Math.sin(th);
    data[i*4+2] = 0; data[i*4+3] = (Math.random() * 0xFFFFFF) >>> 0;
  }

  const vbos = [gl.createBuffer(), gl.createBuffer()];
  const simVaos = [gl.createVertexArray(), gl.createVertexArray()];
  const splatVaos = [gl.createVertexArray(), gl.createVertexArray()];
  for (let i = 0; i < 2; i++) {
    gl.bindBuffer(gl.ARRAY_BUFFER, vbos[i]);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STREAM_COPY);
    gl.bindVertexArray(simVaos[i]);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 16, 0);
    gl.bindVertexArray(splatVaos[i]);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 16, 0);
  }

  const accumTex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, accumTex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, 1200, 800, 0, gl.RGBA, gl.FLOAT, null);
  const accumFbo = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, accumFbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, accumTex, 0);

  let cur = 0;
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.ONE, gl.ONE);
  const t0 = performance.now();
  for (let f = 0; f < 30; f++) {
    for (let s = 0; s < 6; s++) {
      // Step s
      gl.useProgram(simProg);
      gl.uniform2f(gl.getUniformLocation(simProg, 'u_a'), -0.755, 0.33);
      gl.uniform2f(gl.getUniformLocation(simProg, 'u_b'), -0.376, 0.026);
      gl.uniform2f(gl.getUniformLocation(simProg, 'u_c'), 6.401, 0.803);
      gl.uniform2f(gl.getUniformLocation(simProg, 'u_d'), 1.52, 0.84);
      gl.uniform1f(gl.getUniformLocation(simProg, 'u_n'), 16);
      gl.uniform1f(gl.getUniformLocation(simProg, 'u_step'), s);
      gl.enable(gl.RASTERIZER_DISCARD);
      gl.bindVertexArray(simVaos[cur]);
      gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, vbos[1 - cur]);
      gl.beginTransformFeedback(gl.POINTS);
      gl.drawArrays(gl.POINTS, 0, count);
      gl.endTransformFeedback();
      gl.disable(gl.RASTERIZER_DISCARD);
      gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, null);
      cur = 1 - cur;

      // Splat s
      gl.bindFramebuffer(gl.FRAMEBUFFER, accumFbo);
      gl.useProgram(splatProg);
      gl.bindVertexArray(splatVaos[cur]);
      gl.drawArrays(gl.POINTS, 0, count);
    }
  }
  gl.finish();
  const total = performance.now() - t0;
  document.getElementById('res').innerText = '30 frames (6 steps+splats each = 188M points): ' + total.toFixed(1) + ' ms (' + (total/30).toFixed(2) + ' ms/frame, ' + (1000/(total/30)).toFixed(0) + ' FPS)';
};
</script>
</body>
</html>"""

with open('bench_multi_splat.html', 'w') as f:
    f.write(html)

PORT = 8798
Handler = http.server.SimpleHTTPRequestHandler
httpd = socketserver.TCPServer(('', PORT), Handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()
cmd = [r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--no-sandbox', '--use-gl=angle', '--use-angle=d3d11', '--window-size=800,600', '--dump-dom', f'http://localhost:{PORT}/bench_multi_splat.html']
res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
for line in res.stdout.splitlines():
    if '30 frames' in line:
        print(line.strip())
httpd.shutdown()
