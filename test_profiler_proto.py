import subprocess, json, time

html = """<!DOCTYPE html>
<html>
<body>
<canvas id="c" width="1200" height="800"></canvas>
<div id="res">starting...</div>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

class Profiler {
  constructor(renderer) {
    this.renderer = renderer;
    this.gl = renderer.gl;
    this.ext = this.gl.getExtension('EXT_disjoint_timer_query_webgl2');
    this.enabled = !!this.ext;
    this.ringSize = 4;
    this.ring = [];
    this.ringIdx = 0;
    this.maxSteps = 32;

    if (this.enabled) {
      for (let i = 0; i < this.ringSize; i++) {
        const slot = {
          decay: this.gl.createQuery(),
          sim: [],
          splat: [],
          bloom: this.gl.createQuery(),
          post: this.gl.createQuery(),
          active: false,
          steps: 0,
          bloomActive: false,
          cpuTimes: {}
        };
        for (let s = 0; s < this.maxSteps; s++) {
          slot.sim.push(this.gl.createQuery());
          slot.splat.push(this.gl.createQuery());
        }
        this.ring.push(slot);
      }
    }

    this.lastGpu = {
      decayMs: 0,
      simMs: 0,
      splatMs: 0,
      bloomMs: 0,
      postMs: 0,
      totalGpuMs: 0
    };
  }

  beginSlot(steps, bloomActive, cpuTimes) {
    if (!this.enabled) return;
    this.pollOldQueries();
    const slot = this.ring[this.ringIdx];
    slot.active = true;
    slot.steps = steps;
    slot.bloomActive = bloomActive;
    slot.cpuTimes = cpuTimes;
  }

  endSlot() {
    if (!this.enabled) return;
    this.ringIdx = (this.ringIdx + 1) % this.ringSize;
  }

  pollOldQueries() {
    const gl = this.gl;
    const ext = this.ext;
    for (let i = 0; i < this.ringSize; i++) {
      const slot = this.ring[i];
      if (!slot.active) continue;

      // Check post query as sentinel
      const available = gl.getQueryParameter(slot.post, gl.QUERY_RESULT_AVAILABLE);
      if (!available) continue;

      const disjoint = gl.getParameter(ext.GPU_DISJOINT_EXT);
      if (disjoint) {
        slot.active = false;
        continue;
      }

      let decayNs = gl.getQueryParameter(slot.decay, gl.QUERY_RESULT);
      let simNs = 0;
      let splatNs = 0;
      for (let s = 0; s < slot.steps; s++) {
        if (gl.getQueryParameter(slot.sim[s], gl.QUERY_RESULT_AVAILABLE)) {
          simNs += gl.getQueryParameter(slot.sim[s], gl.QUERY_RESULT);
        }
        if (gl.getQueryParameter(slot.splat[s], gl.QUERY_RESULT_AVAILABLE)) {
          splatNs += gl.getQueryParameter(slot.splat[s], gl.QUERY_RESULT);
        }
      }
      let bloomNs = 0;
      if (slot.bloomActive && gl.getQueryParameter(slot.bloom, gl.QUERY_RESULT_AVAILABLE)) {
        bloomNs = gl.getQueryParameter(slot.bloom, gl.QUERY_RESULT);
      }
      let postNs = gl.getQueryParameter(slot.post, gl.QUERY_RESULT);

      this.lastGpu = {
        decayMs: decayNs / 1e6,
        simMs: simNs / 1e6,
        splatMs: splatNs / 1e6,
        bloomMs: bloomNs / 1e6,
        postMs: postNs / 1e6,
        totalGpuMs: (decayNs + simNs + splatNs + bloomNs + postNs) / 1e6,
        cpuTimes: slot.cpuTimes
      };
      slot.active = false;
    }
  }
}

window.onload = async function() {
  const canvas = document.getElementById('c');
  const math = new MathSystem();
  const renderer = new MobiusRenderer(canvas);
  const profiler = new Profiler(renderer);
  const gl = renderer.gl;
  const ext = profiler.ext;

  // Let's run 60 frames and collect profiler results
  for (let f = 0; f < 60; f++) {
    const tCpu0 = performance.now();
    math.update(0.016, renderer.zoom);
    const tMath = performance.now();

    const slot = profiler.ring[profiler.ringIdx];
    const steps = renderer.stepsPerFrame;
    profiler.beginSlot(steps, renderer.bloomEnabled, {});

    // Decay pass
    gl.beginQuery(ext.TIME_ELAPSED_EXT, slot.decay);
    const accumReadTex = renderer.accumTextures[renderer.accumReadIdx];
    const accumWriteFbo = renderer.accumFbos[1 - renderer.accumReadIdx];
    gl.bindFramebuffer(gl.FRAMEBUFFER, accumWriteFbo);
    gl.viewport(0, 0, renderer.accumWidth, renderer.accumHeight);
    gl.useProgram(renderer.decayProg);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, accumReadTex);
    gl.uniform1i(gl.getUniformLocation(renderer.decayProg, 'u_accumTex'), 0);
    gl.uniform1f(gl.getUniformLocation(renderer.decayProg, 'u_persistence'), renderer.currentPersistence);
    gl.bindVertexArray(renderer.quadVao);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.endQuery(ext.TIME_ELAPSED_EXT);

    // Multi-step Sim & Splat
    gl.bindFramebuffer(gl.FRAMEBUFFER, accumWriteFbo);
    gl.viewport(0, 0, renderer.accumWidth, renderer.accumHeight);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE);

    gl.useProgram(renderer.splatProg);
    gl.uniform2f(gl.getUniformLocation(renderer.splatProg, 'u_viewCenter'), renderer.viewCenter[0], renderer.viewCenter[1]);
    gl.uniform1f(gl.getUniformLocation(renderer.splatProg, 'u_zoom'), renderer.zoom);
    gl.uniform1f(gl.getUniformLocation(renderer.splatProg, 'u_aspect'), renderer.aspect);

    gl.useProgram(renderer.simProg);
    gl.uniform2f(gl.getUniformLocation(renderer.simProg, 'u_a'), math.a.r, math.a.i);
    gl.uniform2f(gl.getUniformLocation(renderer.simProg, 'u_b'), math.b.r, math.b.i);
    gl.uniform2f(gl.getUniformLocation(renderer.simProg, 'u_c'), math.c.r, math.c.i);
    gl.uniform2f(gl.getUniformLocation(renderer.simProg, 'u_d'), math.d.r, math.d.i);
    gl.uniform1f(gl.getUniformLocation(renderer.simProg, 'u_n'), math.n);
    gl.uniform1f(gl.getUniformLocation(renderer.simProg, 'u_time'), math.time);
    gl.uniform2f(gl.getUniformLocation(renderer.simProg, 'u_viewCenter'), renderer.viewCenter[0], renderer.viewCenter[1]);
    gl.uniform1f(gl.getUniformLocation(renderer.simProg, 'u_zoom'), renderer.zoom);
    gl.uniform1f(gl.getUniformLocation(renderer.simProg, 'u_respawnAll'), 0.0);

    const uStepLoc = gl.getUniformLocation(renderer.simProg, 'u_step');
    for (let s = 0; s < steps; s++) {
      gl.beginQuery(ext.TIME_ELAPSED_EXT, slot.sim[s]);
      gl.useProgram(renderer.simProg);
      gl.uniform1f(uStepLoc, s);
      gl.enable(gl.RASTERIZER_DISCARD);
      gl.bindVertexArray(renderer.simVaos[renderer.vboCur]);
      gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, renderer.simVbos[1 - renderer.vboCur]);
      gl.beginTransformFeedback(gl.POINTS);
      gl.drawArrays(gl.POINTS, 0, renderer.numParticles);
      gl.endTransformFeedback();
      gl.disable(gl.RASTERIZER_DISCARD);
      gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, null);
      renderer.vboCur = 1 - renderer.vboCur;
      gl.endQuery(ext.TIME_ELAPSED_EXT);

      gl.beginQuery(ext.TIME_ELAPSED_EXT, slot.splat[s]);
      gl.useProgram(renderer.splatProg);
      gl.bindVertexArray(renderer.splatVaos[renderer.vboCur]);
      gl.drawArrays(gl.POINTS, 0, renderer.numParticles);
      gl.endQuery(ext.TIME_ELAPSED_EXT);
    }
    gl.disable(gl.BLEND);

    renderer.accumReadIdx = 1 - renderer.accumReadIdx;
    const accumCurrentTex = renderer.accumTextures[renderer.accumReadIdx];

    // Bloom Pass
    gl.beginQuery(ext.TIME_ELAPSED_EXT, slot.bloom);
    if (renderer.bloomEnabled) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, renderer.bloomFbos[0]);
      gl.viewport(0, 0, renderer.bloomWidth, renderer.bloomHeight);
      gl.useProgram(renderer.blurProg);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, accumCurrentTex);
      gl.uniform1i(gl.getUniformLocation(renderer.blurProg, 'u_image'), 0);
      gl.uniform2f(gl.getUniformLocation(renderer.blurProg, 'u_dir'), 1.5 / renderer.bloomWidth, 0.0);
      gl.bindVertexArray(renderer.quadVao);
      gl.drawArrays(gl.TRIANGLES, 0, 6);

      gl.bindFramebuffer(gl.FRAMEBUFFER, renderer.bloomFbos[1]);
      gl.bindTexture(gl.TEXTURE_2D, renderer.bloomTextures[0]);
      gl.uniform2f(gl.getUniformLocation(renderer.blurProg, 'u_dir'), 0.0, 1.5 / renderer.bloomHeight);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    }
    gl.endQuery(ext.TIME_ELAPSED_EXT);

    // Post Pass
    gl.beginQuery(ext.TIME_ELAPSED_EXT, slot.post);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.useProgram(renderer.postProg);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, accumCurrentTex);
    gl.uniform1i(gl.getUniformLocation(renderer.postProg, 'u_accumTex'), 0);
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, renderer.bloomTextures[1]);
    gl.uniform1i(gl.getUniformLocation(renderer.postProg, 'u_bloomTex'), 1);
    gl.uniform1f(gl.getUniformLocation(renderer.postProg, 'u_gain'), renderer.gain);
    gl.uniform1f(gl.getUniformLocation(renderer.postProg, 'u_bloomEnabled'), renderer.bloomEnabled ? 1.0 : 0.0);
    gl.uniform1f(gl.getUniformLocation(renderer.postProg, 'u_viewMode'), renderer.viewMode);
    gl.bindVertexArray(renderer.quadVao);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.endQuery(ext.TIME_ELAPSED_EXT);

    profiler.endSlot();
    gl.flush();
    await new Promise(r => setTimeout(r, 16));
  }

  // Poll until final query available
  for (let w = 0; w < 50; w++) {
    profiler.pollOldQueries();
    if (profiler.lastGpu.totalGpuMs > 0) break;
    await new Promise(r => setTimeout(r, 20));
  }

  document.getElementById('res').innerText = JSON.stringify(profiler.lastGpu);
  document.body.setAttribute('data-ready', 'true');
};
</script>
</body>
</html>
"""

with open("test_profiler_proto.html", "w") as f:
    f.write(html)

import http.server, socketserver, threading
PORT = 8793
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
    "--virtual-time-budget=10000",
    "--dump-dom",
    f"http://localhost:{PORT}/test_profiler_proto.html"
]
time.sleep(2.5) # allow frames to render
res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
import re
m = re.search(r'<div id="res">(.*?)</div>', res.stdout)
if m:
    print("OUTPUT:", m.group(1))
else:
    print("STDOUT len:", len(res.stdout))

httpd.shutdown()
