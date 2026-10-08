import http.server
import socketserver
import threading
import subprocess
import json
import time
import os

PORT = 8796
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
done_event = threading.Event()
flush_data = None

class FlushHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global flush_data
        if self.path == '/flush_report':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            flush_data = json.loads(body.decode('utf-8'))
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
<head>
<meta charset="UTF-8">
<title>gl.flush() Impact Benchmark</title>
</head>
<body>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

function nextFrame() {
  return new Promise(r => requestAnimationFrame(r));
}

window.onload = async function() {
  const canvas = document.getElementById('c');
  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);

  const renderer = new MobiusRenderer(canvas);
  renderer.adaptive.setMode('standard');
  const gl = renderer.gl;

  // Function to benchmark a mode (with or without gl.flush)
  async function benchmarkFlush(useFlush, numWarmup = 30, numSamples = 120) {
    // Monkey patch gl.flush
    const originalFlush = gl.flush.bind(gl);
    let flushCalls = 0;
    if (!useFlush) {
      gl.flush = function() {}; // No-op
    } else {
      gl.flush = function() {
        flushCalls++;
        originalFlush();
      };
    }

    // Warmup
    for (let i = 0; i < numWarmup; i++) {
      math.update(0.016, renderer.zoom);
      renderer.render(math, 0.016);
      await nextFrame();
    }

    const gpuTimes = [];
    const cpuTimes = [];
    const frameTimes = [];

    for (let i = 0; i < numSamples; i++) {
      const t0 = performance.now();
      math.update(0.016, renderer.zoom);
      const tMath = performance.now();
      renderer.render(math, 0.016, tMath - t0);
      const tEnd = performance.now();

      cpuTimes.push(tEnd - t0);
      if (renderer.profiler && renderer.profiler.metrics.gpuMs > 0) {
        gpuTimes.push(renderer.profiler.metrics.gpuMs);
      }
      frameTimes.push(renderer.profiler.metrics.frameMs);
      await nextFrame();
    }

    // Restore gl.flush
    gl.flush = originalFlush;

    const avg = arr => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
    const std = (arr, m) => arr.length ? Math.sqrt(arr.reduce((a, b) => a + Math.pow(b - m, 2), 0) / arr.length) : 0;

    const avgGpu = avg(gpuTimes);
    const stdGpu = std(gpuTimes, avgGpu);
    const avgCpu = avg(cpuTimes);
    const stdCpu = std(cpuTimes, avgCpu);

    return {
      useFlush,
      flushCalls,
      sampleCount: gpuTimes.length,
      avgGpuMs: parseFloat(avgGpu.toFixed(2)),
      stdGpuMs: parseFloat(stdGpu.toFixed(2)),
      minGpuMs: gpuTimes.length ? parseFloat(Math.min(...gpuTimes).toFixed(2)) : 0,
      maxGpuMs: gpuTimes.length ? parseFloat(Math.max(...gpuTimes).toFixed(2)) : 0,
      avgCpuMs: parseFloat(avgCpu.toFixed(2)),
      stdCpuMs: parseFloat(stdCpu.toFixed(2)),
      fps: renderer.profiler.metrics.fps
    };
  }

  // Run Test 1: WITH gl.flush()
  const withFlush = await benchmarkFlush(true);

  // Run Test 2: WITHOUT gl.flush()
  const withoutFlush = await benchmarkFlush(false);

  await fetch('/flush_report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ withFlush, withoutFlush })
  });
};
</script>
</body>
</html>
"""

def main():
    with open(os.path.join(DIRECTORY, "flush_test.html"), "w") as f:
        f.write(html_page)

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), FlushHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(1.0)

    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    cmd = [
        chrome,
        "--headless=new",
        "--no-sandbox",
        "--use-gl=angle",
        "--use-angle=d3d11",
        "--window-size=1200,800",
        f"http://localhost:{PORT}/flush_test.html"
    ]

    print("Launching Chrome for gl.flush() benchmark...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    success = done_event.wait(timeout=45)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success or flush_data is None:
        print("ERROR: gl.flush test failed or timed out.")
        return False

    rep_path = os.path.join(DIRECTORY, "flush_benchmark_report.json")
    with open(rep_path, "w") as f:
        json.dump(flush_data, f, indent=2)

    print("\n" + "="*60)
    print("GL.FLUSH() BENCHMARK COMPARISON REPORT")
    print("="*60)
    print(json.dumps(flush_data, indent=2))
    print("="*60)
    return True

if __name__ == '__main__':
    main()
