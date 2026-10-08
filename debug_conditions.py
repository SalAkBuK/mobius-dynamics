import subprocess, json, time, os, threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8778
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
benchmark_done = threading.Event()
benchmark_data = None

class DebugConditionsHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global benchmark_data
        if self.path == '/log':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            print("BROWSER LOG:", body.decode('utf-8'))
            self.send_response(200)
            self.end_headers()
        elif self.path == '/report_conditions':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            benchmark_data = json.loads(body.decode('utf-8'))
            self.send_response(200)
            self.end_headers()
            benchmark_done.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

html_page = """<!DOCTYPE html>
<html>
<body>
<canvas id="c" width="1200" height="800"></canvas>
<div id="status">Starting debug condition benchmark...</div>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

async function log(msg) {
  console.log(msg);
  await fetch('/log', { method: 'POST', body: msg });
}

window.onerror = async function(msg, url, line) {
  await log(`ERROR: ${msg} at line ${line}`);
};

window.onload = async function() {
  await log("window.onload started");
  const canvas = document.getElementById('c');
  const math = new MathSystem();
  const renderer = new MobiusRenderer(canvas);
  const gl = renderer.gl;
  const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');

  const results = {};

  async function measureCondition(label, setupFn, actionFn = null) {
    await log(`Starting: ${label}`);
    setupFn();
    renderer.clearAccumulation();

    for (let w = 0; w < 10; w++) {
      math.update(0.016, renderer.zoom);
      renderer.render(math, 0.016);
    }
    gl.finish();

    const qDecay = gl.createQuery();
    const qSim = gl.createQuery();
    const qSplat = gl.createQuery();
    const qBloom = gl.createQuery();
    const qPost = gl.createQuery();

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

    const steps = renderer.stepsPerFrame;
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

    const hasBloom = renderer.bloomEnabled && renderer.viewMode === 0;
    if (hasBloom) {
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
    }

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
    gl.uniform1f(gl.getUniformLocation(renderer.postProg, 'u_bloomEnabled'), renderer.bloomEnabled ? 1.0 : 0.0);
    gl.uniform1f(gl.getUniformLocation(renderer.postProg, 'u_viewMode'), renderer.viewMode);
    gl.bindVertexArray(renderer.quadVao);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.endQuery(ext.TIME_ELAPSED_EXT);

    gl.flush();

    let decayMs = 0, simMs = 0, splatMs = 0, bloomMs = 0, postMs = 0;
    for (let w = 0; w < 100; w++) {
      await new Promise(res => setTimeout(res, 10));
      const qDecayOk = gl.getQueryParameter(qDecay, gl.QUERY_RESULT_AVAILABLE);
      const qSimOk = gl.getQueryParameter(qSim, gl.QUERY_RESULT_AVAILABLE);
      const qSplatOk = gl.getQueryParameter(qSplat, gl.QUERY_RESULT_AVAILABLE);
      const qPostOk = gl.getQueryParameter(qPost, gl.QUERY_RESULT_AVAILABLE);
      const qBloomOk = !hasBloom || gl.getQueryParameter(qBloom, gl.QUERY_RESULT_AVAILABLE);
      if (qDecayOk && qSimOk && qSplatOk && qPostOk && qBloomOk) {
        decayMs = gl.getQueryParameter(qDecay, gl.QUERY_RESULT) / 1e6;
        simMs = gl.getQueryParameter(qSim, gl.QUERY_RESULT) / 1e6;
        splatMs = gl.getQueryParameter(qSplat, gl.QUERY_RESULT) / 1e6;
        bloomMs = hasBloom ? gl.getQueryParameter(qBloom, gl.QUERY_RESULT) / 1e6 : 0.0;
        postMs = gl.getQueryParameter(qPost, gl.QUERY_RESULT) / 1e6;
        break;
      }
    }
    gl.deleteQuery(qDecay);
    gl.deleteQuery(qSim);
    gl.deleteQuery(qSplat);
    gl.deleteQuery(qBloom);
    gl.deleteQuery(qPost);

    const gpuMs = decayMs + simMs + splatMs + bloomMs + postMs;

    // 15 sustained frames
    const cpuTimes = [];
    const t0 = performance.now();
    for (let f = 0; f < 15; f++) {
      if (actionFn) actionFn(f);
      const tStart = performance.now();
      math.update(0.016, renderer.zoom);
      const tMath = performance.now();
      renderer.render(math, 0.016, tMath - tStart);
      const tEnd = performance.now();
      cpuTimes.push(tEnd - tStart);
      gl.flush();
      await new Promise(r => setTimeout(r, 0));
    }
    gl.finish();
    const totalWall = performance.now() - t0;
    const wallPerFrame = totalWall / 15;
    const avgCpu = cpuTimes.reduce((a, b) => a + b, 0) / cpuTimes.length;
    const effectiveFrameMs = Math.max(wallPerFrame, gpuMs);
    const avgFps = 1000 / Math.max(0.1, effectiveFrameMs);

    await log(`Done: ${label} -> GPU: ${gpuMs.toFixed(2)}ms, FPS: ${avgFps.toFixed(1)}`);

    return {
      condition: label,
      avgFps: parseFloat(avgFps.toFixed(1)),
      avgCpuMs: parseFloat(avgCpu.toFixed(2)),
      avgGpuMs: parseFloat(gpuMs.toFixed(2)),
      simGpuMs: parseFloat(simMs.toFixed(2)),
      splatGpuMs: parseFloat(splatMs.toFixed(2)),
      bloomGpuMs: parseFloat(bloomMs.toFixed(2)),
      postGpuMs: parseFloat(postMs.toFixed(2)),
      totalFrameMs: parseFloat(effectiveFrameMs.toFixed(2)),
      drawCalls: 1 + steps * 2 + (hasBloom ? 2 : 0) + 1,
      resolution: `${renderer.canvas.width}x${renderer.canvas.height}`
    };
  }

  // 1. ZOOM LEVELS (tested at 300,000 particles and fixed 12 steps)
  renderer.setParticleCount(300000);
  renderer.setStepsOverride(12);
  renderer.bloomEnabled = true;
  renderer.viewMode = 0;

  results.zoom = [];
  results.zoom.push(await measureCondition("A. Normal View (1.0x / 1.65)", () => {
    renderer.zoom = 1.65; renderer.targetZoom = 1.65;
    renderer.viewCenter = [0, 0]; renderer.targetViewCenter = [0, 0];
  }));

  results.zoom.push(await measureCondition("B. 4.5x Zoom", () => {
    renderer.zoom = 1.65 * 4.5; renderer.targetZoom = 1.65 * 4.5;
    renderer.viewCenter = [0.18, 0.08]; renderer.targetViewCenter = [0.18, 0.08];
  }));

  results.zoom.push(await measureCondition("C. 14x Zoom", () => {
    renderer.zoom = 1.65 * 14.0; renderer.targetZoom = 1.65 * 14.0;
    renderer.viewCenter = [0.16, 0.085]; renderer.targetViewCenter = [0.16, 0.085];
  }));

  results.zoom.push(await measureCondition("D. 45x Zoom", () => {
    renderer.zoom = 1.65 * 45.0; renderer.targetZoom = 1.65 * 45.0;
    renderer.viewCenter = [0.148, 0.088]; renderer.targetViewCenter = [0.148, 0.088];
  }));

  results.zoom.push(await measureCondition("E. 130x Deep Zoom", () => {
    renderer.zoom = 1.65 * 130.0; renderer.targetZoom = 1.65 * 130.0;
    renderer.viewCenter = [0.1422, 0.0894]; renderer.targetViewCenter = [0.1422, 0.0894];
  }));

  // Reset zoom
  renderer.zoom = 1.65; renderer.targetZoom = 1.65;
  renderer.viewCenter = [0, 0]; renderer.targetViewCenter = [0, 0];

  // 2. BLOOM ON vs OFF
  results.bloom = [];
  results.bloom.push(await measureCondition("Bloom ON", () => {
    renderer.bloomEnabled = true;
    renderer.viewMode = 0;
  }));
  results.bloom.push(await measureCondition("Bloom OFF", () => {
    renderer.bloomEnabled = false;
    renderer.viewMode = 1;
  }));

  // Restore bloom
  renderer.bloomEnabled = true;
  renderer.viewMode = 0;

  // 3. DPR COMPARISON (1.0 vs 1.5 vs 2.0)
  results.dpr = [];
  results.dpr.push(await measureCondition("DPR 1.0 (1200x800)", () => {
    renderer.resize(1200, 800);
  }));
  results.dpr.push(await measureCondition("DPR 1.5 (1800x1200)", () => {
    renderer.resize(1800, 1200);
  }));
  results.dpr.push(await measureCondition("DPR 2.0 (2048x1600)", () => {
    renderer.resize(2048, 1600);
  }));

  // Restore DPR 1.0
  renderer.resize(1200, 800);

  // 4. MOTION & INTERACTION
  results.interaction = [];
  results.interaction.push(await measureCondition("System Completely Idle", () => {
    math.evolving = true;
    math.setPointer(0, 0);
  }));

  results.interaction.push(await measureCondition("Moving Pointer Continuously", () => {
    math.evolving = true;
  }, (f) => {
    const ang = f * 0.2;
    math.setPointer(Math.cos(ang) * 0.7, Math.sin(ang) * 0.7);
  }));

  results.interaction.push(await measureCondition("Rapid Zoom Pulsing", () => {
    math.evolving = true;
  }, (f) => {
    renderer.zoom = 1.65 * (1.0 + Math.sin(f * 0.3) * 0.5);
  }));

  results.interaction.push(await measureCondition("Click Shock Perturbation", () => {
    math.evolving = true;
  }, (f) => {
    if (f % 5 === 0) math.injectShock(0.5, 0.5);
  }));

  results.interaction.push(await measureCondition("Rapid Symmetry Switching", () => {
    math.evolving = true;
  }, (f) => {
    if (f % 5 === 0) {
      const syms = [8, 12, 16, 24];
      math.setSymmetry(syms[(f / 5) % syms.length]);
      renderer.startSymmetryTransition();
    }
  }));

  // 5. DRIFT ACTIVE vs PAUSED
  results.drift = [];
  results.drift.push(await measureCondition("Coefficient Drift Active", () => {
    math.evolving = true;
  }));
  results.drift.push(await measureCondition("Coefficient Drift Paused", () => {
    math.evolving = false;
  }));

  await log("Reporting condition results...");
  await fetch('/report_conditions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(results)
  });
  await log("Conditions benchmark complete!");
};
</script>
</body>
</html>
"""

with open("debug_conditions.html", "w") as f:
    f.write(html_page)

def run():
    server = HTTPServer(("", PORT), DebugConditionsHandler)
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
        f"http://localhost:{PORT}/debug_conditions.html"
    ]
    print("Launching Chrome for Debug Conditions Benchmark...", flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    success = benchmark_done.wait(timeout=120)
    proc.terminate()
    server.shutdown()

    if success and benchmark_data:
        out_file = os.path.join(DIRECTORY, "conditions_benchmark_data.json")
        with open(out_file, "w") as f:
            json.dump(benchmark_data, f, indent=2)
        print(f"\nSUCCESS: Conditions benchmark saved to conditions_benchmark_data.json\n", flush=True)
        for cat, items in benchmark_data.items():
            print(f"\n=== {cat.upper()} ===")
            for it in items:
                print(f"{it['condition']:<32} | {it['avgFps']:>5.1f} FPS | GPU: {it['avgGpuMs']:>5.2f}ms (Sim:{it['simGpuMs']:>5.2f} Splat:{it['splatGpuMs']:>5.2f}) | Total: {it['totalFrameMs']:>5.2f}ms")
    else:
        print("ERROR: Conditions benchmark timed out.", flush=True)

if __name__ == "__main__":
    run()
