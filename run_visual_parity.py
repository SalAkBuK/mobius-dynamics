import http.server
import socketserver
import threading
import subprocess
import json
import time
import os
import base64
import urllib.parse
import numpy as np
from PIL import Image

PORT = 8794
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
out_dir = os.path.join(DIRECTORY, "parity_captures")
os.makedirs(out_dir, exist_ok=True)
done_event = threading.Event()
received_images = {}
final_meta = None

class ParityHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global received_images, final_meta
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/save_image':
            params = urllib.parse.parse_qs(parsed.query)
            img_name = params.get('name', ['unknown'])[0]
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            
            # Decode base64 if it's a data URL
            data_str = body.decode('utf-8')
            if ',' in data_str:
                data_str = data_str.split(',', 1)[1]
            img_bytes = base64.b64decode(data_str)
            
            file_path = os.path.join(out_dir, f"{img_name}.png")
            with open(file_path, "wb") as f:
                f.write(img_bytes)
            received_images[img_name] = file_path
            print(f"Received and saved: {img_name}.png ({len(img_bytes)//1024} KB)")

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")

        elif parsed.path == '/finish':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            final_meta = json.loads(body.decode('utf-8'))
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
<title>Visual Parity Validation Suite</title>
<style>
  body { margin: 0; background: #010307; color: #8da4c4; font-family: monospace; }
  canvas { width: 1200px; height: 800px; display: block; }
  #status { position: absolute; top: 10px; left: 10px; font-size: 14px; background: rgba(0,0,0,0.85); padding: 8px 12px; border: 1px solid #224477; border-radius: 4px; }
</style>
</head>
<body>
<div id="status">Initializing visual parity suite...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

function nextFrame() {
  return new Promise(r => requestAnimationFrame(r));
}

async function uploadCanvas(name) {
  const canvas = document.getElementById('c');
  const dataUrl = canvas.toDataURL('image/png');
  await fetch(`/save_image?name=${name}`, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: dataUrl
  });
}

window.onload = async function() {
  const canvas = document.getElementById('c');
  const statusEl = document.getElementById('status');

  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);
  math.evolving = false; // Freeze temporal drift for pixel-perfect deterministic comparison

  const renderer = new MobiusRenderer(canvas);
  renderer.bloomEnabled = true;
  renderer.viewMode = 0;

  const testZooms = [
    { label: 'A_full', name: 'Full Organism (1.0x)', zoom: 1.65, cx: 0.0, cy: 0.0 },
    { label: 'B_zoom_4_5x', name: 'Zoom 4.5x', zoom: 1.65 * 4.5, cx: 0.1422, cy: 0.0894 },
    { label: 'C_zoom_14x', name: 'Zoom 14x', zoom: 1.65 * 14.0, cx: 0.1422, cy: 0.0894 },
    { label: 'D_zoom_45x', name: 'Zoom 45x', zoom: 1.65 * 45.0, cx: 0.1422, cy: 0.0894 },
    { label: 'E_zoom_130x', name: 'Zoom 130x', zoom: 1.65 * 130.0, cx: 0.1422, cy: 0.0894 }
  ];

  const meta = {};

  for (const tz of testZooms) {
    meta[tz.label] = {};

    // 1. OLD BRUTE FORCE: 589,824 particles x 16 steps
    statusEl.innerText = `[${tz.label}] Rendering Old Brute Force (589k x 16)...`;
    renderer.zoom = tz.zoom;
    renderer.targetZoom = tz.zoom;
    renderer.viewCenter = [tz.cx, tz.cy];
    renderer.targetViewCenter = [tz.cx, tz.cy];
    renderer.adaptive.setMode('extreme');
    renderer.setParticleCount(589824);
    renderer.setStepsOverride(16);
    renderer.clearAccumulation();

    // Accumulate for 70 frames (~1.2s of 589k x 16 = 660M photon deposits)
    for (let f = 0; f < 69; f++) {
      math.update(0.016, renderer.zoom);
      renderer.render(math, 0.016);
      await nextFrame();
    }
    math.update(0.016, renderer.zoom);
    renderer.render(math, 0.016);
    statusEl.innerText = `[${tz.label}] Saving Brute Force image...`;
    await uploadCanvas(`${tz.label}_brute`);
    meta[tz.label].brute = {
      particles: renderer.numParticles,
      steps: renderer.stepsPerFrame,
      deposits: renderer.numParticles * renderer.stepsPerFrame,
      accumFrames: renderer.accumulationFrames
    };

    // 2. NEW ADAPTIVE: Standard tier with progressive accumulation
    statusEl.innerText = `[${tz.label}] Rendering New Adaptive (Auto/Standard progressive)...`;
    renderer.clearOverrides();
    renderer.adaptive.setMode('standard');
    renderer.clearAccumulation();

    // Progressive accumulation for 130 frames (~2.2s)
    for (let f = 0; f < 129; f++) {
      math.update(0.016, renderer.zoom);
      renderer.render(math, 0.016);
      await nextFrame();
    }
    math.update(0.016, renderer.zoom);
    renderer.render(math, 0.016);
    statusEl.innerText = `[${tz.label}] Saving Adaptive image...`;
    await uploadCanvas(`${tz.label}_adaptive`);
    meta[tz.label].adaptive = {
      tier: renderer.adaptive.currentTierKey,
      particles: renderer.numParticles,
      steps: renderer.stepsPerFrame,
      deposits: renderer.numParticles * renderer.stepsPerFrame,
      accumFrames: renderer.accumulationFrames
    };
  }

  statusEl.innerText = "Finishing parity suite...";
  await fetch('/finish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(meta)
  });
  statusEl.innerText = "Parity suite complete!";
};
</script>
</body>
</html>
"""

def compute_ssim(img1, img2):
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    im1_gray = 0.2989 * img1[:, :, 0] + 0.5870 * img1[:, :, 1] + 0.1140 * img1[:, :, 2]
    im2_gray = 0.2989 * img2[:, :, 0] + 0.5870 * img2[:, :, 1] + 0.1140 * img2[:, :, 2]
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

def main():
    html_path = os.path.join(DIRECTORY, "parity_test.html")
    with open(html_path, "w") as f:
        f.write(html_page)

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), ParityHandler)
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
        f"http://localhost:{PORT}/parity_test.html"
    ]

    print("Launching Chrome for Visual Parity Suite...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    success = done_event.wait(timeout=120)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success or final_meta is None:
        print("ERROR: Parity test failed or timed out.")
        return False

    metrics_report = {}
    print("\nProcessing captured frames & generating side-by-side comparisons...")
    for label, meta in final_meta.items():
        b_file = os.path.join(out_dir, f"{label}_brute.png")
        a_file = os.path.join(out_dir, f"{label}_adaptive.png")
        side_file = os.path.join(out_dir, f"{label}_side_by_side.png")

        if not os.path.exists(b_file) or not os.path.exists(a_file):
            print(f"Missing file for {label}")
            continue

        img_b = Image.open(b_file).convert('RGB')
        img_a = Image.open(a_file).convert('RGB')

        arr_b = np.array(img_b)
        arr_a = np.array(img_a)

        ssim_val = compute_ssim(arr_b, arr_a)
        psnr_val = compute_psnr(arr_b, arr_a)

        # Create side-by-side composite
        w, h = img_b.size
        side = Image.new('RGB', (w * 2, h))
        side.paste(img_b, (0, 0))
        side.paste(img_a, (w, 0))
        side.save(side_file)

        metrics_report[label] = {
            'ssim': round(ssim_val, 4),
            'psnr_db': round(psnr_val, 2),
            'brute_particles': meta['brute']['particles'],
            'brute_steps': meta['brute']['steps'],
            'brute_deposits_per_frame': meta['brute']['deposits'],
            'brute_accum_frames': meta['brute']['accumFrames'],
            'adaptive_particles': meta['adaptive']['particles'],
            'adaptive_steps': meta['adaptive']['steps'],
            'adaptive_deposits_per_frame': meta['adaptive']['deposits'],
            'adaptive_accum_frames': meta['adaptive']['accumFrames'],
            'adaptive_tier': meta['adaptive']['tier'],
            'side_by_side_path': side_file
        }
        print(f"[{label}] SSIM: {ssim_val:.4f}, PSNR: {psnr_val:.2f} dB | Brute: {meta['brute']['deposits']:,} dep/f vs Adaptive: {meta['adaptive']['deposits']:,} dep/f")

    rep_path = os.path.join(DIRECTORY, "parity_metrics_report.json")
    with open(rep_path, "w") as f:
        json.dump(metrics_report, f, indent=2)

    print(f"\nVisual Parity captures saved to {out_dir}")
    print(f"Parity metrics saved to {rep_path}")
    return True

if __name__ == '__main__':
    main()
