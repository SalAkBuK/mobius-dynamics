import subprocess, time

html = """<!DOCTYPE html>
<html>
<body>
<canvas id="c" width="1200" height="800"></canvas>
<div id="res">running...</div>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

window.onload = async function() {
  const c = document.getElementById('c');
  const m = new MathSystem();
  const r = new MobiusRenderer(c);
  r.setParticleCount(589824);
  r.setStepsOverride(16);

  const gl = r.gl;
  const ext = r.profiler.ext;

  // Let's test single-query-at-a-time pattern
  const qDecay = gl.createQuery();
  const qSim = gl.createQuery();
  const qSplat = gl.createQuery();
  const qBloom = gl.createQuery();
  const qPost = gl.createQuery();

  // Warmup 5 frames
  for (let w = 0; w < 5; w++) {
    r.render(m, 0.016);
  }
  gl.finish();

  // Measure 1 clean frame with GPU queries
  // 1. Decay
  gl.beginQuery(ext.TIME_ELAPSED_EXT, qDecay);
  const accumReadTex = r.accumTextures[r.accumReadIdx];
  const accumWriteFbo = r.accumFbos[1 - r.accumReadIdx];
  gl.bindFramebuffer(gl.FRAMEBUFFER, accumWriteFbo);
  gl.viewport(0, 0, r.accumWidth, r.accumHeight);
  gl.useProgram(r.decayProg);
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, accumReadTex);
  gl.uniform1i(gl.getUniformLocation(r.decayProg, 'u_accumTex'), 0);
  gl.uniform1f(gl.getUniformLocation(r.decayProg, 'u_persistence'), r.currentPersistence);
  gl.bindVertexArray(r.quadVao);
  gl.drawArrays(gl.TRIANGLES, 0, 6);
  gl.endQuery(ext.TIME_ELAPSED_EXT);

  // 2. Sim (16 steps)
  gl.beginQuery(ext.TIME_ELAPSED_EXT, qSim);
  gl.useProgram(r.simProg);
  gl.uniform2f(gl.getUniformLocation(r.simProg, 'u_a'), m.a.r, m.a.i);
  gl.uniform2f(gl.getUniformLocation(r.simProg, 'u_b'), m.b.r, m.b.i);
  gl.uniform2f(gl.getUniformLocation(r.simProg, 'u_c'), m.c.r, m.c.i);
  gl.uniform2f(gl.getUniformLocation(r.simProg, 'u_d'), m.d.r, m.d.i);
  gl.uniform1f(gl.getUniformLocation(r.simProg, 'u_n'), m.n);
  gl.uniform1f(gl.getUniformLocation(r.simProg, 'u_time'), m.time);
  gl.uniform2f(gl.getUniformLocation(r.simProg, 'u_viewCenter'), r.viewCenter[0], r.viewCenter[1]);
  gl.uniform1f(gl.getUniformLocation(r.simProg, 'u_zoom'), r.zoom);
  gl.uniform1f(gl.getUniformLocation(r.simProg, 'u_respawnAll'), 0.0);
  const uStepLoc = gl.getUniformLocation(r.simProg, 'u_step');

  for (let s = 0; s < 16; s++) {
    gl.uniform1f(uStepLoc, s);
    gl.enable(gl.RASTERIZER_DISCARD);
    gl.bindVertexArray(r.simVaos[r.vboCur]);
    gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, r.simVbos[1 - r.vboCur]);
    gl.beginTransformFeedback(gl.POINTS);
    gl.drawArrays(gl.POINTS, 0, r.numParticles);
    gl.endTransformFeedback();
    gl.disable(gl.RASTERIZER_DISCARD);
    gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, null);
    r.vboCur = 1 - r.vboCur;
  }
  gl.endQuery(ext.TIME_ELAPSED_EXT);

  // 3. Splat (16 steps)
  gl.beginQuery(ext.TIME_ELAPSED_EXT, qSplat);
  gl.bindFramebuffer(gl.FRAMEBUFFER, accumWriteFbo);
  gl.viewport(0, 0, r.accumWidth, r.accumHeight);
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.ONE, gl.ONE);
  gl.useProgram(r.splatProg);
  gl.uniform2f(gl.getUniformLocation(r.splatProg, 'u_viewCenter'), r.viewCenter[0], r.viewCenter[1]);
  gl.uniform1f(gl.getUniformLocation(r.splatProg, 'u_zoom'), r.zoom);
  gl.uniform1f(gl.getUniformLocation(r.splatProg, 'u_aspect'), r.aspect);
  for (let s = 0; s < 16; s++) {
    gl.bindVertexArray(r.splatVaos[r.vboCur]);
    gl.drawArrays(gl.POINTS, 0, r.numParticles);
  }
  gl.disable(gl.BLEND);
  gl.endQuery(ext.TIME_ELAPSED_EXT);

  r.accumReadIdx = 1 - r.accumReadIdx;
  const accumCurrentTex = r.accumTextures[r.accumReadIdx];

  // 4. Bloom
  gl.beginQuery(ext.TIME_ELAPSED_EXT, qBloom);
  gl.bindFramebuffer(gl.FRAMEBUFFER, r.bloomFbos[0]);
  gl.viewport(0, 0, r.bloomWidth, r.bloomHeight);
  gl.useProgram(r.blurProg);
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, accumCurrentTex);
  gl.uniform1i(gl.getUniformLocation(r.blurProg, 'u_image'), 0);
  gl.uniform2f(gl.getUniformLocation(r.blurProg, 'u_dir'), 1.5 / r.bloomWidth, 0.0);
  gl.bindVertexArray(r.quadVao);
  gl.drawArrays(gl.TRIANGLES, 0, 6);

  gl.bindFramebuffer(gl.FRAMEBUFFER, r.bloomFbos[1]);
  gl.bindTexture(gl.TEXTURE_2D, r.bloomTextures[0]);
  gl.uniform2f(gl.getUniformLocation(r.blurProg, 'u_dir'), 0.0, 1.5 / r.bloomHeight);
  gl.drawArrays(gl.TRIANGLES, 0, 6);
  gl.endQuery(ext.TIME_ELAPSED_EXT);

  // 5. Post
  gl.beginQuery(ext.TIME_ELAPSED_EXT, qPost);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  gl.viewport(0, 0, c.width, c.height);
  gl.useProgram(r.postProg);
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, accumCurrentTex);
  gl.uniform1i(gl.getUniformLocation(r.postProg, 'u_accumTex'), 0);
  gl.activeTexture(gl.TEXTURE1);
  gl.bindTexture(gl.TEXTURE_2D, r.bloomTextures[1]);
  gl.uniform1i(gl.getUniformLocation(r.postProg, 'u_bloomTex'), 1);
  gl.uniform1f(gl.getUniformLocation(r.postProg, 'u_gain'), r.gain);
  gl.uniform1f(gl.getUniformLocation(r.postProg, 'u_bloomEnabled'), 1.0);
  gl.uniform1f(gl.getUniformLocation(r.postProg, 'u_viewMode'), 0.0);
  gl.bindVertexArray(r.quadVao);
  gl.drawArrays(gl.TRIANGLES, 0, 6);
  gl.endQuery(ext.TIME_ELAPSED_EXT);

  gl.flush();

  // Wait for results
  let decayMs = 0, simMs = 0, splatMs = 0, bloomMs = 0, postMs = 0;
  for (let w = 0; w < 100; w++) {
    await new Promise(res => setTimeout(res, 20));
    const a1 = gl.getQueryParameter(qDecay, gl.QUERY_RESULT_AVAILABLE);
    const a2 = gl.getQueryParameter(qSim, gl.QUERY_RESULT_AVAILABLE);
    const a3 = gl.getQueryParameter(qSplat, gl.QUERY_RESULT_AVAILABLE);
    const a4 = gl.getQueryParameter(qBloom, gl.QUERY_RESULT_AVAILABLE);
    const a5 = gl.getQueryParameter(qPost, gl.QUERY_RESULT_AVAILABLE);
    if (a1 && a2 && a3 && a4 && a5) {
      decayMs = gl.getQueryParameter(qDecay, gl.QUERY_RESULT) / 1e6;
      simMs = gl.getQueryParameter(qSim, gl.QUERY_RESULT) / 1e6;
      splatMs = gl.getQueryParameter(qSplat, gl.QUERY_RESULT) / 1e6;
      bloomMs = gl.getQueryParameter(qBloom, gl.QUERY_RESULT) / 1e6;
      postMs = gl.getQueryParameter(qPost, gl.QUERY_RESULT) / 1e6;
      break;
    }
  }

  const totalGpuMs = decayMs + simMs + splatMs + bloomMs + postMs;
  document.getElementById('res').innerText = JSON.stringify({
    particles: 589824,
    steps: 16,
    decayMs,
    simMs,
    splatMs,
    bloomMs,
    postMs,
    totalGpuMs,
    glError: gl.getError()
  });
};
</script>
</body>
</html>
"""

with open("test_query_safety.html", "w") as f:
    f.write(html)

import http.server, socketserver, threading
PORT = 8782
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
    "--window-size=1200,800",
    "--virtual-time-budget=5000",
    "--dump-dom",
    f"http://localhost:{PORT}/test_query_safety.html"
]
time.sleep(1.0)
res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
import re
m = re.search(r'<div id="res">(.*?)</div>', res.stdout)
if m:
    print("OUTPUT:", m.group(1))
else:
    print("STDOUT:", res.stdout[:500])

httpd.shutdown()
