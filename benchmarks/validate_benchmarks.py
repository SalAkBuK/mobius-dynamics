import subprocess, json, time, os, threading, base64
import http.server, socketserver
import numpy as np
from PIL import Image

PORT = 8792
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
benchmark_done = threading.Event()
benchmark_data = None

class ValidationHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global benchmark_data
        if self.path == '/validation_report':
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
<div id="status">Initializing benchmark validation pass...</div>
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
  math.evolving = false; // Frozen drift for controlled deterministic integration comparison

  const renderer = new MobiusRenderer(canvas);
  renderer.bloomEnabled = true;
  renderer.viewMode = 0;
  renderer.zoom = 1.65;
  renderer.targetZoom = 1.65;
  renderer.viewCenter = [0.0, 0.0];
  renderer.targetViewCenter = [0.0, 0.0];
  renderer.currentPersistence = 1.0; // Perfect pure photon accumulation

  const modes = [
    { name: 'ULTRA', particles: 589824, steps: 16 },
    { name: 'HIGH', particles: 300000, steps: 12 },
    { name: 'MEDIUM', particles: 150000, steps: 8 },
    { name: 'LOW', particles: 75000, steps: 8 },
    { name: 'POTATO', particles: 40000, steps: 4 }
  ];

  const targetTimesSec = [0.5, 1.0, 3.0, 5.0, 10.0];
  const results = {};

  for (const mode of modes) {
    statusEl.innerText = `Preparing mode ${mode.name} (${mode.particles.toLocaleString()} pts, ${mode.steps} steps)...`;
    renderer.setParticleCount(mode.particles);
    renderer.setStepsOverride(mode.steps);
    renderer.clearAccumulation();

    // Warmup 5 initial trajectory seed steps so attractor is populated
    for (let w = 0; w < 5; w++) {
      renderer.render(math, 0.016);
    }
    renderer.clearAccumulation();
    renderer.gl.finish();

    results[mode.name] = [];

    // Run progressive accumulation driven by real wall-clock elapsed time via requestAnimationFrame
    await new Promise(resolve => {
      let frameCount = 0;
      let nextTargetIdx = 0;
      const startTime = performance.now();

      function onFrame(now) {
        // Render one full frame
        renderer.render(math, 0.016);
        frameCount++;

        const elapsedMs = performance.now() - startTime;
        const currentTargetSec = targetTimesSec[nextTargetIdx];

        if (elapsedMs >= currentTargetSec * 1000) {
          renderer.gl.finish();
          const dataUrl = canvas.toDataURL('image/png');
          const theoreticalFrames = Math.round(currentTargetSec * 60);

          results[mode.name].push({
            targetSec: currentTargetSec,
            actualElapsedMs: elapsedMs,
            completedFrames: frameCount,
            actualPhotons: mode.particles * mode.steps * frameCount,
            theoretical60FpsFrames: theoreticalFrames,
            theoretical60FpsPhotons: mode.particles * mode.steps * theoreticalFrames,
            effectiveFps: (frameCount * 1000) / elapsedMs,
            dataUrl: dataUrl
          });

          statusEl.innerText = `Mode ${mode.name}: checkpoint ${currentTargetSec}s completed (${frameCount} frames in ${(elapsedMs/1000).toFixed(2)}s)`;
          nextTargetIdx++;

          if (nextTargetIdx >= targetTimesSec.length) {
            resolve();
            return;
          }
        }

        requestAnimationFrame(onFrame);
      }

      requestAnimationFrame(onFrame);
    });
  }

  statusEl.innerText = "Reporting validation results...";
  await fetch('/validation_report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(results)
  });
  statusEl.innerText = "Validation pass complete!";
};
</script>
</body>
</html>
"""

with open("validate_benchmarks.html", "w") as f:
    f.write(html_page)

def compute_ssim(img1, img2):
    # img1, img2 are numpy float arrays [0, 255] or [0, 1]
    # Standard SSIM formulation
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    # Convert to grayscale luminance
    if img1.ndim == 3:
        im1_gray = 0.2989 * img1[:, :, 0] + 0.5870 * img1[:, :, 1] + 0.1140 * img1[:, :, 2]
        im2_gray = 0.2989 * img2[:, :, 0] + 0.5870 * img2[:, :, 1] + 0.1140 * img2[:, :, 2]
    else:
        im1_gray = img1
        im2_gray = img2

    mu1 = np.mean(im1_gray)
    mu2 = np.mean(im2_gray)
    sigma1_sq = np.var(im1_gray)
    sigma2_sq = np.var(im2_gray)
    sigma12 = np.mean((im1_gray - mu1) * (im2_gray - mu2))

    num = (2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)
    den = (mu1**2 + mu2**2 + c1) * (sigma1_sq + sigma2_sq + c2)
    return float(num / den)

def compute_psnr(img1, img2):
    mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)
    if mse == 0:
        return 100.0
    return float(20 * np.log10(255.0 / np.sqrt(mse)))

def run():
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), ValidationHandler)
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
        f"http://localhost:{PORT}/validate_benchmarks.html"
    ]
    print("Launching Chrome for Benchmark Validation Pass...")
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 5 modes * 10s = 50s + overhead -> allow 150s
    success = benchmark_done.wait(timeout=180)
    proc.terminate()
    server.shutdown()
    elapsed = time.time() - t0

    if success and benchmark_data:
        save_dir = os.path.join(DIRECTORY, "validation_captures")
        os.makedirs(save_dir, exist_ok=True)
        summary = {}

        for mode, caps in benchmark_data.items():
            summary[mode] = []
            for cap in caps:
                fname = f"valid_{mode.lower()}_{cap['targetSec']}s.png"
                fpath = os.path.join(save_dir, fname)
                b64 = cap['dataUrl'].split(',')[1]
                img_data = base64.b64decode(b64)
                with open(fpath, "wb") as f:
                    f.write(img_data)
                
                summary[mode].append({
                    "targetSec": cap['targetSec'],
                    "actualElapsedMs": round(cap['actualElapsedMs'], 1),
                    "completedFrames": cap['completedFrames'],
                    "actualPhotons": cap['actualPhotons'],
                    "theoretical60FpsFrames": cap['theoretical60FpsFrames'],
                    "theoretical60FpsPhotons": cap['theoretical60FpsPhotons'],
                    "effectiveFps": round(cap['effectiveFps'], 1),
                    "file": fname,
                    "sizeBytes": len(img_data)
                })

        with open(os.path.join(DIRECTORY, "benchmark_validation_summary.json"), "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\nBenchmark completed successfully in {elapsed:.1f}s!")
        print("\n=== PROGRESSIVE ACCUMULATION WALL-CLOCK DATA ===")
        for mode, rows in summary.items():
            print(f"\n--- {mode} ---")
            for r in rows:
                print(f"Target: {r['targetSec']}s | Elapsed: {r['actualElapsedMs']}ms | "
                      f"Completed Frames: {r['completedFrames']} (vs 60fps: {r['theoretical60FpsFrames']}) | "
                      f"Actual Photons: {r['actualPhotons']:,} (vs 60fps: {r['theoretical60FpsPhotons']:,}) | "
                      f"Effective FPS: {r['effectiveFps']}")

        # Now compute SSIM and PSNR
        # Compare all modes at each targetSec to Ultra at the same targetSec,
        # as well as to Ultra at 10.0s (the high-exposure reference)!
        print("\n=== IMAGE QUALITY METRICS (SSIM & PSNR) ===")
        target_secs = [0.5, 1.0, 3.0, 5.0, 10.0]
        ref_10s_path = os.path.join(save_dir, "valid_ultra_10.0s.png")
        ref_10s_img = np.array(Image.open(ref_10s_path))

        iq_results = {}
        for tsec in target_secs:
            iq_results[str(tsec)] = {}
            ultra_t_path = os.path.join(save_dir, f"valid_ultra_{tsec}s.png")
            ultra_t_img = np.array(Image.open(ultra_t_path))

            for mode in ["ULTRA", "HIGH", "MEDIUM", "LOW", "POTATO"]:
                m_path = os.path.join(save_dir, f"valid_{mode.lower()}_{tsec}s.png")
                m_img = np.array(Image.open(m_path))

                ssim_vs_ultra_t = compute_ssim(m_img, ultra_t_img)
                psnr_vs_ultra_t = compute_psnr(m_img, ultra_t_img)

                ssim_vs_ultra_10s = compute_ssim(m_img, ref_10s_img)
                psnr_vs_ultra_10s = compute_psnr(m_img, ref_10s_img)

                iq_results[str(tsec)][mode] = {
                    "ssim_vs_ultra_at_time": round(ssim_vs_ultra_t, 4),
                    "psnr_vs_ultra_at_time": round(psnr_vs_ultra_t, 2),
                    "ssim_vs_ultra_10s_ref": round(ssim_vs_ultra_10s, 4),
                    "psnr_vs_ultra_10s_ref": round(psnr_vs_ultra_10s, 2)
                }

        with open(os.path.join(DIRECTORY, "image_quality_metrics.json"), "w") as f:
            json.dump(iq_results, f, indent=2)

        for tsec, modes_data in iq_results.items():
            print(f"\n--- Checkpoint {tsec}s (vs Ultra at {tsec}s) ---")
            for m, vals in modes_data.items():
                print(f"  {m:7s}: SSIM = {vals['ssim_vs_ultra_at_time']:.4f}, PSNR = {vals['psnr_vs_ultra_at_time']:.2f} dB "
                      f"(vs Ultra 10s: SSIM = {vals['ssim_vs_ultra_10s_ref']:.4f})")

        # Create side-by-side comparison images
        # 1. Strip at 0.5s: Potato | Low | Medium | Ultra
        # 2. Strip at 1.0s: Potato | Low | Medium | Ultra
        # 3. Strip at 3.0s: Potato | Low | Medium | Ultra
        # 4. Strip at 5.0s: Potato | Low | Medium | Ultra
        # 5. Strip at 10.0s: Potato | Low | Medium | Ultra
        for tsec in target_secs:
            strip_modes = ["POTATO", "LOW", "MEDIUM", "ULTRA"]
            imgs = [Image.open(os.path.join(save_dir, f"valid_{m.lower()}_{tsec}s.png")) for m in strip_modes]
            # Downscale each to 600x400 for side-by-side strip
            thumb_w, thumb_h = 600, 400
            thumbs = [im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS) for im in imgs]
            strip = Image.new("RGB", (thumb_w * 4, thumb_h))
            for idx, th in enumerate(thumbs):
                strip.paste(th, (idx * thumb_w, 0))
            strip_path = os.path.join(save_dir, f"side_by_side_{tsec}s.png")
            strip.save(strip_path)
            print(f"Generated side-by-side strip: {strip_path}")

        # Also create a comprehensive 4x5 comparison grid:
        # Rows: Potato, Low, Medium, Ultra
        # Cols: 0.5s, 1.0s, 3.0s, 5.0s, 10.0s
        grid_w, grid_h = 360, 240
        grid = Image.new("RGB", (grid_w * 5, grid_h * 4))
        row_modes = ["POTATO", "LOW", "MEDIUM", "ULTRA"]
        for r_idx, m in enumerate(row_modes):
            for c_idx, tsec in enumerate(target_secs):
                im = Image.open(os.path.join(save_dir, f"valid_{m.lower()}_{tsec}s.png"))
                th = im.resize((grid_w, grid_h), Image.Resampling.LANCZOS)
                grid.paste(th, (c_idx * grid_w, r_idx * grid_h))
        grid_path = os.path.join(save_dir, "comparison_grid_4x5.png")
        grid.save(grid_path)
        print(f"Generated complete comparison grid: {grid_path}")

    else:
        print("ERROR: Benchmark failed or timed out.")

if __name__ == "__main__":
    run()
