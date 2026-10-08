import http.server
import socketserver
import threading
import subprocess
import json
import time
import os

PORT = 8795
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
OUT_DIR = os.path.join(DIRECTORY, "visual_detail_audit")
done_event = threading.Event()
gpu_results = None

class GpuHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global gpu_results
        if self.path == '/gpu_results':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            gpu_results = json.loads(body.decode('utf-8'))
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            done_event.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

html_page = """<!DOCTYPE html>
<html>
<body>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

function nextFrame() {
  return new Promise(r => requestAnimationFrame(r));
}

window.onload = async function() {
  const c = document.getElementById('c');
  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);
  math.evolving = false;

  const renderer = new MobiusRenderer(c);
  renderer.adaptive.getDpr = () => 1.0;
  renderer.resize(1200, 800);
  renderer.zoom = 1.65;
  renderer.currentPersistence = 1.0;
  renderer.profiler.enabled = false; // Disable profiler internal timer queries to avoid overlap

  const gl = renderer.gl;
  const ext = renderer.profiler.ext;

  const workloads = [
    { name: 'brute_589k_16', particles: 589824, steps: 16 },
    { name: 'adaptive_150k_8', particles: 150000, steps: 8 },
    { name: 'exp_180k_8', particles: 180000, steps: 8 },
    { name: 'exp_150k_10', particles: 150000, steps: 10 }
  ];

  const results = {};

  for (const w of workloads) {
    renderer.setParticleCount(w.particles);
    renderer.setStepsOverride(w.steps);
    renderer.clearAccumulation();

    // Warmup 10 frames
    for (let i = 0; i < 10; i++) {
      math.update(0.016, renderer.zoom);
      renderer.render(math, 0.016);
      await nextFrame();
    }
    gl.finish();

    // Single pass-isolated timing queries
    const qDecay = gl.createQuery();
    const qSim = gl.createQuery();
    const qSplat = gl.createQuery();
    const qBloom = gl.createQuery();
    const qPost = gl.createQuery();

    // Measure Pass 1: Decay
    gl.beginQuery(ext.TIME_ELAPSED_EXT, qDecay);
    const accumReadTex = renderer.accumTextures[renderer.accumReadIdx];
    const accumWriteFbo = renderer.accumFbos[1 - renderer.accumReadIdx];
    gl.bindFramebuffer(gl.FRAMEBUFFER, accumWriteFbo);
    gl.viewport(0, 0, renderer.accumWidth, renderer.accumHeight);
    gl.useProgram(renderer.decayProg);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, accumReadTex);
    gl.uniform1i(renderer.decayUniforms.accumTex, 0);
    gl.uniform1f(renderer.decayUniforms.persistence, renderer.currentPersistence);
    gl.bindVertexArray(renderer.quadVao);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.endQuery(ext.TIME_ELAPSED_EXT);

    // Measure Pass 2: Sim
    gl.beginQuery(ext.TIME_ELAPSED_EXT, qSim);
    gl.useProgram(renderer.simProg);
    gl.uniform2f(renderer.simUniforms.a, math.a.r, math.a.i);
    gl.uniform2f(renderer.simUniforms.b, math.b.r, math.b.i);
    gl.uniform2f(renderer.simUniforms.c, math.c.r, math.c.i);
    gl.uniform2f(renderer.simUniforms.d, math.d.r, math.d.i);
    gl.uniform1f(renderer.simUniforms.n, math.n);
    gl.uniform1f(renderer.simUniforms.time, math.time);
    gl.uniform2f(renderer.simUniforms.viewCenter, renderer.viewCenter[0], renderer.viewCenter[1]);
    gl.uniform1f(renderer.simUniforms.zoom, renderer.zoom);
    gl.uniform1f(renderer.simUniforms.respawnAll, 0.0);
    const uStepLoc = renderer.simUniforms.step;
    for (let s = 0; s < w.steps; s++) {
      gl.uniform1f(uStepLoc, s);
      gl.enable(gl.RASTERIZER_DISCARD);
      gl.bindVertexArray(renderer.simVaos[renderer.vboCur]);
      gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, renderer.simVbos[1 - renderer.vboCur]);
      gl.beginTransformFeedback(gl.POINTS);
      gl.drawArrays(gl.POINTS, 0, w.particles);
      gl.endTransformFeedback();
      gl.disable(gl.RASTERIZER_DISCARD);
      gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, null);
      renderer.vboCur = 1 - renderer.vboCur;
    }
    gl.endQuery(ext.TIME_ELAPSED_EXT);

    // Measure Pass 3: Splat
    gl.beginQuery(ext.TIME_ELAPSED_EXT, qSplat);
    gl.bindFramebuffer(gl.FRAMEBUFFER, accumWriteFbo);
    gl.viewport(0, 0, renderer.accumWidth, renderer.accumHeight);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE);
    gl.useProgram(renderer.splatProg);
    gl.uniform2f(renderer.splatUniforms.viewCenter, renderer.viewCenter[0], renderer.viewCenter[1]);
    gl.uniform1f(renderer.splatUniforms.zoom, renderer.zoom);
    gl.uniform1f(renderer.splatUniforms.aspect, renderer.aspect);
    gl.uniform1f(renderer.splatUniforms.photonScale, 1.0);
    for (let s = 0; s < w.steps; s++) {
      gl.bindVertexArray(renderer.splatVaos[renderer.vboCur]);
      gl.drawArrays(gl.POINTS, 0, w.particles);
    }
    gl.disable(gl.BLEND);
    gl.endQuery(ext.TIME_ELAPSED_EXT);

    renderer.accumReadIdx = 1 - renderer.accumReadIdx;
    const accumCurrentTex = renderer.accumTextures[renderer.accumReadIdx];

    // Measure Pass 4: Bloom
    gl.beginQuery(ext.TIME_ELAPSED_EXT, qBloom);
    gl.bindFramebuffer(gl.FRAMEBUFFER, renderer.bloomFbos[0]);
    gl.viewport(0, 0, renderer.bloomWidth, renderer.bloomHeight);
    gl.useProgram(renderer.blurProg);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, accumCurrentTex);
    gl.uniform1i(renderer.blurUniforms.image, 0);
    gl.uniform2f(renderer.blurUniforms.dir, 1.5 / renderer.bloomWidth, 0.0);
    gl.bindVertexArray(renderer.quadVao);
    gl.drawArrays(gl.TRIANGLES, 0, 6);

    gl.bindFramebuffer(gl.FRAMEBUFFER, renderer.bloomFbos[1]);
    gl.bindTexture(gl.TEXTURE_2D, renderer.bloomTextures[0]);
    gl.uniform2f(renderer.blurUniforms.dir, 0.0, 1.5 / renderer.bloomHeight);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.endQuery(ext.TIME_ELAPSED_EXT);

    // Measure Pass 5: Post / Tonemap
    gl.beginQuery(ext.TIME_ELAPSED_EXT, qPost);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, c.width, c.height);
    gl.useProgram(renderer.postProg);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, accumCurrentTex);
    gl.uniform1i(renderer.postUniforms.accumTex, 0);
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, renderer.bloomTextures[1]);
    gl.uniform1i(renderer.postUniforms.bloomTex, 1);
    gl.uniform1f(renderer.postUniforms.gain, renderer.gain);
    gl.uniform1i(renderer.postUniforms.bloomEnabled, 1);
    gl.uniform1i(renderer.postUniforms.viewMode, 0);
    gl.uniform1f(renderer.postUniforms.photonScale, 1.0);
    gl.bindVertexArray(renderer.quadVao);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.endQuery(ext.TIME_ELAPSED_EXT);

    gl.flush();

    // Poll all query results
    async function getQueryResult(q) {
      for (let p = 0; p < 250; p++) {
        await new Promise(r => setTimeout(r, 5));
        if (gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE)) {
          return gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6;
        }
      }
      return null;
    }

    const tDecay = await getQueryResult(qDecay);
    const tSim = await getQueryResult(qSim);
    const tSplat = await getQueryResult(qSplat);
    const tBloom = await getQueryResult(qBloom);
    const tPost = await getQueryResult(qPost);

    gl.deleteQuery(qDecay);
    gl.deleteQuery(qSim);
    gl.deleteQuery(qSplat);
    gl.deleteQuery(qBloom);
    gl.deleteQuery(qPost);

    const totalGpu = (tDecay || 0) + (tSim || 0) + (tSplat || 0) + (tBloom || 0) + (tPost || 0);

    results[w.name] = {
      particles: w.particles,
      steps: w.steps,
      deposits: w.particles * w.steps,
      decayMs: tDecay ? Math.round(tDecay * 100) / 100 : null,
      simMs: tSim ? Math.round(tSim * 100) / 100 : null,
      splatMs: tSplat ? Math.round(tSplat * 100) / 100 : null,
      bloomMs: tBloom ? Math.round(tBloom * 100) / 100 : null,
      postMs: tPost ? Math.round(tPost * 100) / 100 : null,
      totalGpuMs: Math.round(totalGpu * 100) / 100
    };
  }

  await fetch('/gpu_results', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(results)
  });
};
</script>
</body>
</html>
"""

def main():
    with open("gpu_bench_harness.html", "w") as f:
        f.write(html_page)

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), GpuHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(1.0)

    cmd = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--no-sandbox",
        "--use-gl=angle",
        "--use-angle=d3d11",
        "--window-size=1200,800",
        f"http://localhost:{PORT}/gpu_bench_harness.html"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    success = done_event.wait(timeout=45)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if success and gpu_results:
        print("[GPU BREAKDOWN RESULTS]:")
        print(json.dumps(gpu_results, indent=2))
        with open(os.path.join(OUT_DIR, "gpu_bench_breakdown.json"), "w") as f:
            json.dump(gpu_results, f, indent=2)
    else:
        print("[ERROR]: GPU bench timed out or failed")

if __name__ == '__main__':
    main()
