import subprocess, time, http.server, socketserver, threading, json, os

PORT = 8788
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
benchmark_done = threading.Event()
benchmark_data = None

class TestHandler(http.server.SimpleHTTPRequestHandler):
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
<head><title>rAF Test</title></head>
<body>
<div id="status">Starting...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

window.onload = async function() {
  const canvas = document.getElementById('c');
  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);
  math.evolving = false;

  const renderer = new MobiusRenderer(canvas);
  renderer.bloomEnabled = true;
  renderer.viewMode = 0;
  renderer.zoom = 1.65;
  renderer.currentPersistence = 1.0;

  // Let's test ULTRA (589824 x 16) and POTATO (40000 x 4) in rAF for 2 seconds each
  const modes = [
    { name: 'POTATO', particles: 40000, steps: 4 },
    { name: 'ULTRA', particles: 589824, steps: 16 }
  ];

  const results = {};

  for (const mode of modes) {
    renderer.setParticleCount(mode.particles);
    renderer.setStepsOverride(mode.steps);
    renderer.clearAccumulation();

    for (let w = 0; w < 5; w++) renderer.render(math, 0.016);
    renderer.clearAccumulation();

    // Run in requestAnimationFrame for 2.0 seconds of wall-clock time
    const res = await new Promise(resolve => {
      let frameCount = 0;
      let startWall = performance.now();
      function onFrame(now) {
        frameCount++;
        math.update(0.016, renderer.zoom);
        renderer.render(math, 0.016);
        const elapsed = now - startWall;
        if (elapsed >= 2000) {
          resolve({
            frames: frameCount,
            elapsedMs: elapsed,
            fps: (frameCount * 1000) / elapsed
          });
          return;
        }
        requestAnimationFrame(onFrame);
      }
      requestAnimationFrame(onFrame);
    });

    results[mode.name] = res;
  }

  await fetch('/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(results)
  });
};
</script>
</body>
</html>
"""

with open("test_raf_bench.html", "w") as f:
    f.write(html_page)

def run():
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), TestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    cmd = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--no-sandbox",
        "--use-gl=angle",
        "--use-angle=d3d11",
        "--window-size=1200,800",
        f"http://localhost:{PORT}/test_raf_bench.html"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    success = benchmark_done.wait(timeout=30)
    proc.terminate()
    server.shutdown()

    if success:
        print("RESULTS:", json.dumps(benchmark_data, indent=2))
    else:
        print("FAILED / TIMEOUT")

if __name__ == "__main__":
    run()
