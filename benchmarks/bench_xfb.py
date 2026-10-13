import http.server, socketserver, threading, subprocess, time, os

html = """<!DOCTYPE html>
<html>
<body>
<div id="fps">waiting...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script>
window.onload = function() {
  const canvas = document.getElementById('c');
  const gl = canvas.getContext('webgl2');

  const vsSrc = `#version 300 es
  in vec4 a_state;
  out vec4 v_state;
  uniform vec2 u_a;
  uniform vec2 u_b;
  uniform vec2 u_c;
  uniform vec2 u_d;
  uniform float u_n;
  uniform float u_step;

  uint pcg(uint v) {
    uint state = v * 747796405u + 2891336453u;
    uint word = ((state >> ((state >> 28u) + 4u)) ^ state) * 277803737u;
    return (word >> 22u) ^ word;
  }

  float nextRand(inout uint seed) {
    seed = pcg(seed);
    return float(seed & 0x00FFFFFFu) / 16777216.0;
  }

  vec2 c_mul(vec2 x, vec2 y) {
    return vec2(x.x * y.x - x.y * y.y, x.x * y.y + x.y * y.x);
  }

  vec2 c_div(vec2 num, vec2 den) {
    float d = dot(den, den);
    return vec2((num.x * den.x + num.y * den.y) / d, (num.y * den.x - num.x * den.y) / d);
  }

  void main() {
    vec2 z = a_state.xy;
    float age = a_state.z;
    uint seed = uint(a_state.w) + uint(u_step * 1013904223.0);

    int n = int(u_n + 0.5);
    int k = int(nextRand(seed) * float(n)) % n;
    float ang = (6.28318530718 * float(k)) / float(n);
    vec2 omega = vec2(cos(ang), sin(ang));

    vec2 num = c_mul(u_a, z) + u_b;
    vec2 den = c_mul(u_c, z) + u_d;
    if (dot(den, den) < 1e-7 || dot(z, z) > 25.0 || age > 3000.0) {
      float r = 0.18 + nextRand(seed) * 0.45;
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

  const fsSrc = `#version 300 es
  precision highp float;
  void main() {}
  `;

  const vs = gl.createShader(gl.VERTEX_SHADER);
  gl.shaderSource(vs, vsSrc);
  gl.compileShader(vs);

  const fs = gl.createShader(gl.FRAGMENT_SHADER);
  gl.shaderSource(fs, fsSrc);
  gl.compileShader(fs);

  const prog = gl.createProgram();
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.transformFeedbackVaryings(prog, ['v_state'], gl.SEPARATE_ATTRIBS);
  gl.linkProgram(prog);

  const count = 589824;
  const data = new Float32Array(count * 4);
  for (let i = 0; i < count; i++) {
    data[i*4+0] = 0.3;
    data[i*4+1] = 0.1;
    data[i*4+2] = 0;
    data[i*4+3] = i;
  }

  const vboA = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, vboA);
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.STREAM_COPY);

  const vboB = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, vboB);
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.STREAM_COPY);

  const vaoA = gl.createVertexArray();
  gl.bindVertexArray(vaoA);
  gl.bindBuffer(gl.ARRAY_BUFFER, vboA);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 16, 0);

  const vaoB = gl.createVertexArray();
  gl.bindVertexArray(vaoB);
  gl.bindBuffer(gl.ARRAY_BUFFER, vboB);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 16, 0);

  const t0 = performance.now();
  let curA = true;
  gl.useProgram(prog);
  gl.enable(gl.RASTERIZER_DISCARD);

  for (let s = 0; s < 100; s++) {
    gl.bindVertexArray(curA ? vaoA : vaoB);
    gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, curA ? vboB : vboA);
    gl.beginTransformFeedback(gl.POINTS);
    gl.drawArrays(gl.POINTS, 0, count);
    gl.endTransformFeedback();
    curA = !curA;
  }
  gl.disable(gl.RASTERIZER_DISCARD);
  gl.finish();
  const t1 = performance.now();
  document.getElementById('fps').innerText = 'BENCHMARK: 100 steps took ' + (t1 - t0).toFixed(2) + ' ms (' + ((t1 - t0)/100).toFixed(3) + ' ms/step for 589824 particles)';
};
</script>
</body>
</html>
"""

with open("test_xfb.html", "w") as f:
    f.write(html)

PORT = 8794
Handler = http.server.SimpleHTTPRequestHandler
httpd = socketserver.TCPServer(("", PORT), Handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--no-sandbox",
    "--use-gl=angle",
    "--use-angle=d3d11",
    "--window-size=1200,800",
    "--virtual-time-budget=2000",
    "--dump-dom",
    f"http://localhost:{PORT}/test_xfb.html"
]
res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
for line in res.stdout.splitlines():
    if "BENCHMARK" in line:
        print(line.strip())
httpd.shutdown()
