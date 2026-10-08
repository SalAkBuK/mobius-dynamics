import http.server
import socketserver
import threading
import subprocess
import json
import time
import os
import urllib.parse

PORT = 8799
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
done_event = threading.Event()
sustained_data = None

class SustainedHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global sustained_data
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/log_sample':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            sample = json.loads(body.decode('utf-8'))
            print(f"[{sample['elapsedSec']:>4}s] Tier: {sample['tier']:<8} | Part: {sample['particles']:,} | Steps: {sample['steps']} | GPU EMA: {sample['gpuEma']}ms | FPS: {sample['fps']} | Heap: {sample.get('jsHeapUsedMb', 0):.1f}MB")
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        elif parsed.path == '/finish_sustained':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            sustained_data = json.loads(body.decode('utf-8'))
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
<title>10-Minute Sustained Thermal & Memory & Hysteresis Test</title>
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
  renderer.adaptive.setMode('auto'); // Pure Auto mode for true hysteresis & adaptation

  // Tracking metrics
  const tierChanges = [];
  let previousTier = renderer.adaptive.currentTierKey;

  // Count tier transitions categorized by state:
  let tierChanges5MinIdle = 0;
  let tierChangesInteraction = 0;
  let tierChangesZoom = 0;

  const samples30s = [];
  const startTime = performance.now();
  const totalDurationMs = 600 * 1000; // 10 minutes = 600 seconds
  let lastSampleTime = startTime;
  let frameCount = 0;

  // Initial memory check
  const startMemory = performance.memory ? {
    usedJSHeapSize: performance.memory.usedJSHeapSize,
    totalJSHeapSize: performance.memory.totalJSHeapSize,
    jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
  } : null;

  while (performance.now() - startTime < totalDurationMs) {
    const now = performance.now();
    const elapsedSec = (now - startTime) / 1000;
    frameCount++;

    // Phase schedule:
    // 0 - 300s (First 5 minutes): Pure IDLE stationary accumulation
    // 300s - 420s (2 minutes): Repeated pointer interactions every 5 seconds
    // 420s - 540s (2 minutes): Repeated zoom transitions (in and out) every 8 seconds
    // 540s - 600s (Final 1 minute): Settled recovery & final thermal observation

    let isInteractingNow = false;
    let isZoomingNow = false;

    if (elapsedSec >= 300 && elapsedSec < 420) {
      // Periodic interaction
      if (Math.floor(elapsedSec) % 5 === 0 && Math.floor(elapsedSec * 10) % 10 < 3) {
        renderer.adaptive.markInteraction();
        math.setPointer(Math.sin(elapsedSec), Math.cos(elapsedSec));
        isInteractingNow = true;
      }
    } else if (elapsedSec >= 420 && elapsedSec < 540) {
      // Periodic zoom
      const zoomPhase = (elapsedSec - 420) / 8;
      const targetZ = 1.65 * (1.0 + 15.0 * Math.abs(Math.sin(zoomPhase)));
      renderer.targetZoom = targetZ;
      isZoomingNow = true;
    } else {
      // Stationary default
      renderer.targetZoom = 1.65;
    }

    math.update(0.016, renderer.zoom);
    renderer.render(math, 0.016);

    // Detect tier changes
    const curTier = renderer.adaptive.currentTierKey;
    if (curTier !== previousTier) {
      const changeEvent = {
        elapsedSec: parseFloat(elapsedSec.toFixed(1)),
        fromTier: previousTier,
        toTier: curTier,
        reason: renderer.adaptive.lastEvent,
        gpuEma: parseFloat(renderer.adaptive.gpuEma.toFixed(2))
      };
      tierChanges.push(changeEvent);

      if (elapsedSec < 300) {
        tierChanges5MinIdle++;
      } else if (isInteractingNow) {
        tierChangesInteraction++;
      } else if (isZoomingNow) {
        tierChangesZoom++;
      }
      previousTier = curTier;
    }

    // Sample every 30 seconds
    if (now - lastSampleTime >= 30000) {
      lastSampleTime = now;
      const curHeapMb = performance.memory ? performance.memory.usedJSHeapSize / (1024 * 1024) : null;
      const status = renderer.adaptive.getStatus();
      const sample = {
        elapsedSec: Math.round(elapsedSec),
        gpuEma: status.gpuEma ? parseFloat(status.gpuEma.toFixed(2)) : null,
        targetBudgetMs: status.targetBudgetMs,
        headroomPercent: status.headroomPercent,
        fps: renderer.profiler.metrics.fps,
        particles: renderer.numParticles,
        steps: renderer.stepsPerFrame,
        deposits: renderer.numParticles * renderer.stepsPerFrame,
        tier: curTier,
        dpr: renderer.adaptive.getDpr(),
        zoom: parseFloat(renderer.zoom.toFixed(2)),
        jsHeapUsedMb: curHeapMb ? parseFloat(curHeapMb.toFixed(2)) : null,
        totalFrames: frameCount
      };
      samples30s.push(sample);

      // Transmit sample to Python server
      await fetch('/log_sample', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sample)
      });
    }

    await nextFrame();
  }

  // End memory check
  const endMemory = performance.memory ? {
    usedJSHeapSize: performance.memory.usedJSHeapSize,
    totalJSHeapSize: performance.memory.totalJSHeapSize,
    jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
  } : null;

  const finalReport = {
    totalFramesRendered: frameCount,
    durationSec: Math.round((performance.now() - startTime) / 1000),
    tierChanges5MinIdle,
    tierChangesInteraction,
    tierChangesZoom,
    totalTierChanges: tierChanges.length,
    tierEvents: tierChanges,
    samples30s,
    memory: {
      startHeapMb: startMemory ? parseFloat((startMemory.usedJSHeapSize / (1024 * 1024)).toFixed(2)) : null,
      endHeapMb: endMemory ? parseFloat((endMemory.usedJSHeapSize / (1024 * 1024)).toFixed(2)) : null,
      heapGrowthMb: (startMemory && endMemory) ? parseFloat(((endMemory.usedJSHeapSize - startMemory.usedJSHeapSize) / (1024 * 1024)).toFixed(2)) : null
    }
  };

  await fetch('/finish_sustained', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(finalReport)
  });
};
</script>
</body>
</html>
"""

def main():
    with open(os.path.join(DIRECTORY, "sustained_test.html"), "w") as f:
        f.write(html_page)

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), SustainedHandler)
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
        f"http://localhost:{PORT}/sustained_test.html"
    ]

    print("Launching 10-Minute Sustained Thermal, Memory, and Hysteresis Validation...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # 600 seconds test + 60 seconds buffer = 660 seconds timeout
    success = done_event.wait(timeout=660)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success or sustained_data is None:
        print("ERROR: Sustained 10-minute test failed or timed out.")
        return False

    out_file = os.path.join(DIRECTORY, "sustained_10min_report.json")
    with open(out_file, "w") as f:
        json.dump(sustained_data, f, indent=2)

    print("\n" + "="*70)
    print("10-MINUTE SUSTAINED THERMAL & MEMORY VALIDATION SUMMARY")
    print("="*70)
    print(f"Total Frames Rendered: {sustained_data['totalFramesRendered']}")
    print(f"Tier changes during 5 min idle: {sustained_data['tierChanges5MinIdle']}")
    print(f"Tier changes during interaction: {sustained_data['tierChangesInteraction']}")
    print(f"Tier changes during zoom: {sustained_data['tierChangesZoom']}")
    print(f"Memory: Start Heap={sustained_data['memory']['startHeapMb']}MB -> End Heap={sustained_data['memory']['endHeapMb']}MB (Growth={sustained_data['memory']['heapGrowthMb']}MB)")
    print("="*70)
    return True

if __name__ == '__main__':
    main()
