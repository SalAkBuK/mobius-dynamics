import subprocess, json, time, os, threading, base64
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8780
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
benchmark_done = threading.Event()
benchmark_data = None

class ProgressiveHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global benchmark_data
        if self.path == '/progressive_report':
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
<div id="status">Starting progressive accumulation benchmark...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

window.onload = async function() {
  const canvas = document.getElementById('c');
  const statusEl = document.getElementById('status');
  
  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);
  math.evolving = false; // Freeze drift for controlled long-exposure progressive accumulation

  const renderer = new MobiusRenderer(canvas);
  renderer.bloomEnabled = true;
  renderer.viewMode = 0;
  renderer.zoom = 1.65;
  renderer.targetZoom = 1.65;
  renderer.viewCenter = [0.0, 0.0];
  renderer.targetViewCenter = [0.0, 0.0];
  renderer.currentPersistence = 1.0; // Perfect photon integration

  const modes = [
    { name: 'ULTRA', particles: 589824, steps: 16 },
    { name: 'HIGH', particles: 300000, steps: 12 },
    { name: 'MEDIUM', particles: 150000, steps: 8 },
    { name: 'LOW', particles: 75000, steps: 6 },
    { name: 'POTATO', particles: 40000, steps: 4 }
  ];

  // Target durations at 60 fps: 0.5s (30 f), 1s (60 f), 3s (180 f), 5s (300 f), 10s (600 f)
  const checkpoints = [
    { timeSec: 0.5, targetFrames: 30 },
    { timeSec: 1.0, targetFrames: 60 },
    { timeSec: 3.0, targetFrames: 180 },
    { timeSec: 5.0, targetFrames: 300 },
    { timeSec: 10.0, targetFrames: 600 }
  ];

  const results = {};

  for (const mode of modes) {
    statusEl.innerText = `Testing mode ${mode.name} (${mode.particles} pts, ${mode.steps} steps)...`;
    renderer.setParticleCount(mode.particles);
    renderer.setStepsOverride(mode.steps);
    renderer.clearAccumulation();

    // Warmup 5 initial trajectory seed steps so attractor is populated
    for (let w = 0; w < 5; w++) {
      renderer.render(math, 0.016);
    }
    renderer.clearAccumulation();

    results[mode.name] = [];
    let currentFrame = 0;

    for (const cp of checkpoints) {
      statusEl.innerText = `Mode ${mode.name}: Accumulating to ${cp.timeSec}s (${cp.targetFrames} frames)...`;
      
      const framesToRun = cp.targetFrames - currentFrame;
      for (let f = 0; f < framesToRun; f++) {
        renderer.render(math, 0.016);
      }
      currentFrame = cp.targetFrames;
      renderer.gl.finish();

      // Read canvas image
      const dataUrl = canvas.toDataURL('image/png');
      results[mode.name].push({
        timeSec: cp.timeSec,
        frames: currentFrame,
        totalCumulativePhotons: mode.particles * mode.steps * currentFrame,
        dataUrl: dataUrl
      });
    }
  }

  statusEl.innerText = "Reporting progressive accumulation results...";
  await fetch('/progressive_report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(results)
  });
  statusEl.innerText = "Progressive accumulation benchmark complete!";
};
</script>
</body>
</html>
"""

with open("benchmark_progressive.html", "w") as f:
    f.write(html_page)

def run():
    server = HTTPServer(("", PORT), ProgressiveHandler)
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
        f"http://localhost:{PORT}/benchmark_progressive.html"
    ]
    print("Launching Chrome for Progressive Accumulation Quality Study...")
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    success = benchmark_done.wait(timeout=240)
    proc.terminate()
    server.shutdown()
    elapsed = time.time() - t0

    if success and benchmark_data:
        os.makedirs(os.path.join(DIRECTORY, "accum_captures"), exist_ok=True)
        meta = {}
        for mode, caps in benchmark_data.items():
            meta[mode] = []
            for cap in caps:
                fname = f"accum_{mode.lower()}_{cap['timeSec']}s.png"
                fpath = os.path.join(DIRECTORY, "accum_captures", fname)
                b64 = cap['dataUrl'].split(',')[1]
                img_data = base64.b64decode(b64)
                with open(fpath, "wb") as f:
                    f.write(img_data)
                meta[mode].append({
                    "timeSec": cap['timeSec'],
                    "frames": cap['frames'],
                    "totalPhotons": cap['totalCumulativePhotons'],
                    "file": fname,
                    "sizeBytes": len(img_data)
                })
                print(f"Saved {fname} ({len(img_data)} bytes, {cap['totalCumulativePhotons']:,} photons)")
        with open(os.path.join(DIRECTORY, "progressive_accumulation_data.json"), "w") as f:
            json.dump(meta, f, indent=2)
        print(f"\nSUCCESS: Progressive Study completed in {elapsed:.1f}s!\n")
    else:
        print("ERROR: Progressive benchmark timed out.")

if __name__ == "__main__":
    run()
