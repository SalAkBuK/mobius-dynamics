import subprocess, json, time, os, threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8788
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
benchmark_done = threading.Event()
benchmark_data = None

class BenchmarkHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global benchmark_data
        if self.path == '/report':
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
<div id="status">Starting 5x4 matrix benchmark...</div>
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
  const profiler = renderer.profiler;

  const particleCounts = [589824, 300000, 150000, 75000, 40000];
  const stepCounts = [16, 12, 8, 4];
  const matrixResults = [];

  for (const particles of particleCounts) {
    for (const steps of stepCounts) {
      statusEl.innerText = `Benchmarking: ${particles} particles, ${steps} steps... (${matrixResults.length + 1}/20)`;
      renderer.setParticleCount(particles);
      renderer.setStepsOverride(steps);
      renderer.clearAccumulation();

      // Warmup frames (25 frames to eliminate initial allocation / cache noise)
      for (let w = 0; w < 25; w++) {
        math.update(0.016, renderer.zoom);
        renderer.render(math, 0.016);
      }
      gl.finish();

      // Measurement frames (50 frames)
      const cpuTimes = [];
      const tStartMeasurement = performance.now();

      for (let f = 0; f < 50; f++) {
        const t0 = performance.now();
        math.update(0.016, renderer.zoom);
        const tMath = performance.now();
        const jsTime = tMath - t0;

        renderer.render(math, 0.016, jsTime);
        const tEnd = performance.now();
        cpuTimes.push(tEnd - t0);
      }
      gl.finish();
      const tEndMeasurement = performance.now();
      const totalWallTime = tEndMeasurement - tStartMeasurement;
      const wallPerFrame = totalWallTime / 50;

      // Poll GPU queries
      for (let p = 0; p < 20; p++) {
        profiler.pollOldQueries();
        if (profiler.metrics.gpuMs > 0) break;
        await new Promise(r => setTimeout(r, 10));
      }

      // Calculate statistics
      const avgCpu = cpuTimes.reduce((a, b) => a + b, 0) / cpuTimes.length;
      const sortedCpu = [...cpuTimes].sort((a, b) => a - b);
      const p99Idx = Math.floor(sortedCpu.length * 0.99);
      const p99Cpu = sortedCpu[Math.min(sortedCpu.length - 1, p99Idx)];
      
      const gpuMs = profiler.metrics.gpuMs;
      const simGpuMs = profiler.metrics.simGpuMs;
      const splatGpuMs = profiler.metrics.splatGpuMs;
      const decayGpuMs = profiler.metrics.decayGpuMs;
      const bloomGpuMs = profiler.metrics.bloomGpuMs;
      const postGpuMs = profiler.metrics.postGpuMs;
      const postTotalMs = parseFloat((bloomGpuMs + postGpuMs).toFixed(2));
      
      const effectiveFrameMs = Math.max(wallPerFrame, Math.max(avgCpu, gpuMs));
      const p99FrameMs = Math.max(wallPerFrame * 1.15, Math.max(p99Cpu, gpuMs));
      const avgFps = 1000 / Math.max(0.1, effectiveFrameMs);
      const fps1Low = 1000 / Math.max(0.1, p99FrameMs);

      const entry = {
        particles,
        steps,
        avgFps: parseFloat(avgFps.toFixed(1)),
        fps1Low: parseFloat(fps1Low.toFixed(1)),
        avgCpuMs: parseFloat(avgCpu.toFixed(2)),
        avgGpuMs: parseFloat(gpuMs.toFixed(2)),
        simGpuMs: parseFloat(simGpuMs.toFixed(2)),
        splatGpuMs: parseFloat(splatGpuMs.toFixed(2)),
        decayGpuMs: parseFloat(decayGpuMs.toFixed(2)),
        postProcessingGpuMs: postTotalMs,
        bloomGpuMs: parseFloat(bloomGpuMs.toFixed(2)),
        tonemapGpuMs: parseFloat(postGpuMs.toFixed(2)),
        totalFrameMs: parseFloat(effectiveFrameMs.toFixed(2)),
        drawCalls: profiler.metrics.drawCalls,
        xfbPasses: steps,
        itersPerFrame: particles * steps
      };

      matrixResults.push(entry);
    }
  }

  statusEl.innerText = "Reporting benchmark data...";
  await fetch('/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(matrixResults)
  });
  statusEl.innerText = "Benchmark complete!";
};
</script>
</body>
</html>
"""

with open("benchmark_matrix.html", "w") as f:
    f.write(html_page)

def run_benchmark():
    server = HTTPServer(("", PORT), BenchmarkHandler)
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
        f"http://localhost:{PORT}/benchmark_matrix.html"
    ]
    print("Launching Chrome for 5x4 matrix benchmark...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for benchmark to report
    success = benchmark_done.wait(timeout=120)
    proc.terminate()
    server.shutdown()

    if success and benchmark_data:
        out_file = os.path.join(DIRECTORY, "matrix_benchmark_data.json")
        with open(out_file, "w") as f:
            json.dump(benchmark_data, f, indent=2)
        print(f"\nSUCCESS: Benchmark completed with {len(benchmark_data)} configurations.\n")
        print(f"{'Particles':>9} | {'Steps':>5} | {'Avg FPS':>7} | {'1% Low':>7} | {'CPU ms':>7} | {'GPU ms':>7} | {'Sim ms':>7} | {'Splat ms':>8} | {'Post ms':>7} | {'Total ms':>8}")
        print("-" * 90)
        for r in benchmark_data:
            print(f"{r['particles']:>9} | {r['steps']:>5} | {r['avgFps']:>7.1f} | {r['fps1Low']:>7.1f} | {r['avgCpuMs']:>7.2f} | {r['avgGpuMs']:>7.2f} | {r['simGpuMs']:>7.2f} | {r['splatGpuMs']:>8.2f} | {r['postProcessingGpuMs']:>7.2f} | {r['totalFrameMs']:>8.2f}")
    else:
        print("ERROR: Benchmark timed out or failed to report data.")

if __name__ == "__main__":
    run_benchmark()
