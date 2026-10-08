import subprocess, json, time, os, threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8779
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
benchmark_done = threading.Event()
benchmark_data = None

class UpperHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global benchmark_data
        if self.path == '/upper_done':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            benchmark_data = json.loads(body.decode('utf-8'))
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            benchmark_done.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

html_page = """<!DOCTYPE html>
<html>
<head>
<style>
body { margin: 0; background: #010307; color: #8da4c4; font-family: monospace; }
canvas { width: 1200px; height: 800px; display: block; }
#status { position: absolute; top: 10px; left: 10px; font-size: 14px; background: rgba(0,0,0,0.85); padding: 8px; border: 1px solid #224477; }
</style>
</head>
<body>
<div id="status">Starting upper matrix benchmark...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

window.onload = async function() {
  const canvas = document.getElementById('c');
  const statusEl = document.getElementById('status');
  
  const math = new MathSystem();
  const renderer = new MobiusRenderer(canvas);
  const gl = renderer.gl;
  const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');

  const particleCounts = [589824, 300000, 150000];
  const stepCounts = [16, 12, 8, 4];
  const results = [];

  let testNum = 0;
  const totalTests = particleCounts.length * stepCounts.length;

  for (const particles of particleCounts) {
    renderer.setParticleCount(particles);

    for (const steps of stepCounts) {
      testNum++;
      statusEl.innerText = `[${testNum}/${totalTests}] Testing ${particles} pts, ${steps} steps...`;
      renderer.setStepsOverride(steps);
      renderer.clearAccumulation();

      // Warmup 5 frames
      for (let w = 0; w < 5; w++) {
        math.update(0.016, renderer.zoom);
        renderer.render(math, 0.016);
      }
      gl.finish();

      const qDecay = gl.createQuery();
      const qSim = gl.createQuery();
      const qSplat = gl.createQuery();
      const qBloom = gl.createQuery();
      const qPost = gl.createQuery();

      // Measurement pass
      gl.beginQuery(ext.TIME_ELAPSED_EXT, qDecay);
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

      gl.beginQuery(ext.TIME_ELAPSED_EXT, qSim);
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
      }
      gl.endQuery(ext.TIME_ELAPSED_EXT);

      gl.beginQuery(ext.TIME_ELAPSED_EXT, qSplat);
      gl.bindFramebuffer(gl.FRAMEBUFFER, accumWriteFbo);
      gl.viewport(0, 0, renderer.accumWidth, renderer.accumHeight);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE);
      gl.useProgram(renderer.splatProg);
      gl.uniform2f(gl.getUniformLocation(renderer.splatProg, 'u_viewCenter'), renderer.viewCenter[0], renderer.viewCenter[1]);
      gl.uniform1f(gl.getUniformLocation(renderer.splatProg, 'u_zoom'), renderer.zoom);
      gl.uniform1f(gl.getUniformLocation(renderer.splatProg, 'u_aspect'), renderer.aspect);
      for (let s = 0; s < steps; s++) {
        gl.bindVertexArray(renderer.splatVaos[renderer.vboCur]);
        gl.drawArrays(gl.POINTS, 0, renderer.numParticles);
      }
      gl.disable(gl.BLEND);
      gl.endQuery(ext.TIME_ELAPSED_EXT);

      renderer.accumReadIdx = 1 - renderer.accumReadIdx;
      const accumCurrentTex = renderer.accumTextures[renderer.accumReadIdx];

      gl.beginQuery(ext.TIME_ELAPSED_EXT, qBloom);
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
      gl.endQuery(ext.TIME_ELAPSED_EXT);

      gl.beginQuery(ext.TIME_ELAPSED_EXT, qPost);
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
      gl.uniform1f(gl.getUniformLocation(renderer.postProg, 'u_bloomEnabled'), 1.0);
      gl.uniform1f(gl.getUniformLocation(renderer.postProg, 'u_viewMode'), 0.0);
      gl.bindVertexArray(renderer.quadVao);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      gl.endQuery(ext.TIME_ELAPSED_EXT);

      gl.flush();

      // Read queries with generous 250 * 15ms = 3.75s polling window
      let decayMs = 0, simMs = 0, splatMs = 0, bloomMs = 0, postMs = 0;
      for (let w = 0; w < 250; w++) {
        await new Promise(res => setTimeout(res, 15));
        if (gl.getQueryParameter(qDecay, gl.QUERY_RESULT_AVAILABLE) &&
            gl.getQueryParameter(qSim, gl.QUERY_RESULT_AVAILABLE) &&
            gl.getQueryParameter(qSplat, gl.QUERY_RESULT_AVAILABLE) &&
            gl.getQueryParameter(qBloom, gl.QUERY_RESULT_AVAILABLE) &&
            gl.getQueryParameter(qPost, gl.QUERY_RESULT_AVAILABLE)) {
          decayMs = gl.getQueryParameter(qDecay, gl.QUERY_RESULT) / 1e6;
          simMs = gl.getQueryParameter(qSim, gl.QUERY_RESULT) / 1e6;
          splatMs = gl.getQueryParameter(qSplat, gl.QUERY_RESULT) / 1e6;
          bloomMs = gl.getQueryParameter(qBloom, gl.QUERY_RESULT) / 1e6;
          postMs = gl.getQueryParameter(qPost, gl.QUERY_RESULT) / 1e6;
          break;
        }
      }
      gl.deleteQuery(qDecay);
      gl.deleteQuery(qSim);
      gl.deleteQuery(qSplat);
      gl.deleteQuery(qBloom);
      gl.deleteQuery(qPost);

      const totalGpuMs = decayMs + simMs + splatMs + bloomMs + postMs;

      // 3. Wall clock sustained FPS measurement (20 frames)
      const cpuDeltas = [];
      const frameDeltas = [];
      const tWall0 = performance.now();
      let prevT = tWall0;

      for (let f = 0; f < 20; f++) {
        const t0 = performance.now();
        math.update(0.016, renderer.zoom);
        const tMath = performance.now();
        renderer.render(math, 0.016, tMath - t0);
        const tEnd = performance.now();
        cpuDeltas.push(tEnd - t0);
        gl.flush();
        await new Promise(r => setTimeout(r, 0));
        const curT = performance.now();
        frameDeltas.push(curT - prevT);
        prevT = curT;
      }
      gl.finish();
      const totalWallMs = performance.now() - tWall0;
      const wallPerFrameMs = totalWallMs / 20;
      const avgCpuMs = cpuDeltas.reduce((a, b) => a + b, 0) / cpuDeltas.length;

      const sortedDeltas = [...frameDeltas].sort((a, b) => a - b);
      const p99Idx = Math.floor(sortedDeltas.length * 0.99);
      const p99Delta = sortedDeltas[Math.min(sortedDeltas.length - 1, p99Idx)];

      const totalFrameMs = Math.max(wallPerFrameMs, totalGpuMs);
      const avgFps = 1000 / Math.max(0.1, totalFrameMs);
      const fps1Low = 1000 / Math.max(0.1, Math.max(p99Delta, totalFrameMs * 1.15));
      const postTotalGpuMs = bloomMs + postMs;
      const drawCalls = 1 + steps * 2 + 2 + 1;

      const record = {
        particles,
        steps,
        avgFps: parseFloat(avgFps.toFixed(1)),
        fps1Low: parseFloat(fps1Low.toFixed(1)),
        avgCpuMs: parseFloat(avgCpuMs.toFixed(2)),
        avgGpuMs: parseFloat(totalGpuMs.toFixed(2)),
        simGpuMs: parseFloat(simMs.toFixed(2)),
        splatGpuMs: parseFloat(splatMs.toFixed(2)),
        decayGpuMs: parseFloat(decayMs.toFixed(2)),
        postProcessingGpuMs: parseFloat(postTotalGpuMs.toFixed(2)),
        bloomGpuMs: parseFloat(bloomMs.toFixed(2)),
        tonemapGpuMs: parseFloat(postMs.toFixed(2)),
        totalFrameMs: parseFloat(totalFrameMs.toFixed(2)),
        drawCalls,
        xfbPasses: steps,
        itersPerFrame: particles * steps
      };

      results.push(record);
    }
  }

  statusEl.innerText = "Reporting upper matrix results...";
  await fetch('/upper_done', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(results)
  });
  statusEl.innerText = "Upper matrix complete!";
};
</script>
</body>
</html>
"""

with open("upper_matrix_page.html", "w") as f:
    f.write(html_page)

def run():
    server = HTTPServer(("", PORT), UpperHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(1.0)

    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    cmd = [
        chrome_path,
        "--headless=new",
        "--no-sandbox",
        "--use-gl=angle",
        "--use-angle=d3d11",
        "--window-size=1200,800",
        f"http://localhost:{PORT}/upper_matrix_page.html"
    ]
    print("Launching Chrome for Upper Matrix Benchmark...")
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    success = benchmark_done.wait(timeout=180)
    proc.terminate()
    server.shutdown()
    elapsed = time.time() - t0

    if success and benchmark_data:
        out_file = os.path.join(DIRECTORY, "upper_matrix_data.json")
        with open(out_file, "w") as f:
            json.dump(benchmark_data, f, indent=2)
        print(f"\nSUCCESS: Upper Matrix Benchmark completed in {elapsed:.1f}s!\n")
        print(f"{'Particles':>9} | {'Steps':>5} | {'Avg FPS':>7} | {'1% Low':>7} | {'CPU ms':>7} | {'GPU ms':>7} | {'Sim ms':>7} | {'Splat ms':>8} | {'Post ms':>7} | {'Total ms':>8}")
        print("-" * 92)
        for r in benchmark_data:
            print(f"{r['particles']:>9} | {r['steps']:>5} | {r['avgFps']:>7.1f} | {r['fps1Low']:>7.1f} | {r['avgCpuMs']:>7.2f} | {r['avgGpuMs']:>7.2f} | {r['simGpuMs']:>7.2f} | {r['splatGpuMs']:>8.2f} | {r['postProcessingGpuMs']:>7.2f} | {r['totalFrameMs']:>8.2f}")
    else:
        print("ERROR: Upper matrix benchmark timed out.")

if __name__ == "__main__":
    run()
