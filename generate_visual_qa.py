import http.server
import socketserver
import threading
import subprocess
import json
import time
import os
import base64
import numpy as np
from PIL import Image

PORT = 8796
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"

html_qa = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Reference Master Visual QA Generator</title></head>
<body>
<div id="status">Initializing WebGL renderer...</div>
<canvas id="c" width="800" height="800"></canvas>
<script type="module">
import { MobiusRenderer } from './renderer.js';
import { MathSystem } from './math.js';

async function runQA() {
  const canvas = document.getElementById('c');
  const math = new MathSystem();
  const renderer = new MobiusRenderer(canvas);
  const statusEl = document.getElementById('status');

  async function renderMasterPasses(passes, label) {
    statusEl.innerText = `Rendering ${label} (${passes} passes)...`;
    console.log(`Starting ${label} (${passes} passes)...`);
    const t0 = performance.now();
    const blob = await renderer.exportReferenceMaster(math, {
      accumPasses: passes,
      filename: `ref_master_${passes}.png`,
      onProgress: (pct, msg) => {
        statusEl.innerText = `${label}: ${pct}% - ${msg}`;
      }
    });
    const elapsed = ((performance.now() - t0) / 1000).toFixed(1);
    console.log(`Completed ${label} in ${elapsed}s, blob size: ${blob.size}`);

    // Convert blob to base64
    const reader = new FileReader();
    return new Promise((resolve) => {
      reader.onloadend = () => {
        resolve({
          passes,
          label,
          elapsedSec: parseFloat(elapsed),
          blobSize: blob.size,
          dataUrl: reader.result
        });
      };
      reader.readAsDataURL(blob);
    });
  }

  try {
    // 1. Generate 120 passes
    const res120 = await renderMasterPasses(120, 'Reference Master 120');

    // 2. Generate 240 passes
    const res240 = await renderMasterPasses(240, 'Reference Master 240');

    // Send data to python server
    await fetch('/qa_upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ res120, res240 })
    });
    statusEl.innerText = 'QA Complete!';
  } catch (err) {
    console.error('QA Error:', err);
    await fetch('/qa_upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: err.message, stack: err.stack })
    });
  }
}

window.addEventListener('load', runQA);
</script>
</body>
</html>
"""

with open("generate_visual_qa.html", "w", encoding='utf-8') as f:
    f.write(html_qa)

done_event = threading.Event()
qa_data = None

class QAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global qa_data
        if self.path == '/qa_upload':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            qa_data = json.loads(body.decode('utf-8'))
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

httpd = socketserver.TCPServer(("", PORT), QAHandler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--no-sandbox",
    "--use-gl=angle",
    "--use-angle=d3d11",
    "--window-size=1200,900",
    f"http://localhost:{PORT}/generate_visual_qa.html"
]

print("Launching Chrome for Reference Master Visual QA (120 & 240 passes)...")
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Allow up to 180 seconds for both 4096x4096 brute force renders to finish
done = done_event.wait(timeout=180.0)
proc.terminate()
httpd.shutdown()

if not done or not qa_data:
    print("Visual QA generation timed out or failed.")
    exit(1)

if "error" in qa_data:
    print("Visual QA error in browser:", qa_data["error"])
    print(qa_data.get("stack", ""))
    exit(1)

print("\n--- SAVING REFERENCE MASTER QA RENDERS ---")
res120 = qa_data["res120"]
res240 = qa_data["res240"]

def save_b64_image(data_url, filepath):
    header, b64_str = data_url.split(",", 1)
    img_bytes = base64.b64decode(b64_str)
    with open(filepath, "wb") as f:
        f.write(img_bytes)
    im = Image.open(filepath)
    print(f"Saved: {filepath} ({im.size[0]}x{im.size[1]}, {len(img_bytes)/(1024*1024):.2f} MB)")
    return im

path_120 = os.path.join(DIRECTORY, "mobius-reference-master-120.png")
path_240 = os.path.join(DIRECTORY, "mobius-reference-master-240.png")
im_120 = save_b64_image(res120["dataUrl"], path_120)
im_240 = save_b64_image(res240["dataUrl"], path_240)

print(f"Render time 120 passes: {res120['elapsedSec']}s")
print(f"Render time 240 passes: {res240['elapsedSec']}s")

# Load Ground Truth
gt_path = os.path.join(DIRECTORY, "ground_truth_python_simone.png")
gt_im = Image.open(gt_path)
print(f"Loaded Reference Ground Truth: {gt_path} ({gt_im.size[0]}x{gt_im.size[1]})")

# Create Side-by-Side Overview Image
thumb_size = 1024
gt_thumb = gt_im.resize((thumb_size, thumb_size), Image.Resampling.LANCZOS)
m120_thumb = im_120.resize((thumb_size, thumb_size), Image.Resampling.LANCZOS)
m240_thumb = im_240.resize((thumb_size, thumb_size), Image.Resampling.LANCZOS)

overview = Image.new("RGB", (thumb_size * 3, thumb_size))
overview.paste(gt_thumb, (0, 0))
overview.paste(m120_thumb, (thumb_size, 0))
overview.paste(m240_thumb, (thumb_size * 2, 0))
overview_path = os.path.join(DIRECTORY, "qa_side_by_side_simone_vs_master120_master240.png")
overview.save(overview_path)
print(f"Saved Overview Comparison: {overview_path}")

# Create High-Magnification Inspection Crops
# In 4096x4096 space:
# Center void crop: [1792:2304, 1792:2304] (512x512 around center 2048,2048)
# Inner caustics crop: around radius 0.28 (e.g. [1200:1800, 1900:2500])
# Secondary loops crop: around outer lobes (e.g. [700:1300, 1800:2400])
# Outer gossamer web crop: corner / outer rim (e.g. [300:900, 300:900])

def make_crop_comparison(crop_box_4k, crop_box_gt, filename, title):
    # crop_box_4k: (x0, y0, x1, y1) in 4096 space
    # crop_box_gt: (x0, y0, x1, y1) in 1024 space
    c_gt = gt_im.crop(crop_box_gt).resize((512, 512), Image.Resampling.LANCZOS)
    c_120 = im_120.crop(crop_box_4k).resize((512, 512), Image.Resampling.LANCZOS)
    c_240 = im_240.crop(crop_box_4k).resize((512, 512), Image.Resampling.LANCZOS)
    
    strip = Image.new("RGB", (512 * 3, 512))
    strip.paste(c_gt, (0, 0))
    strip.paste(c_120, (512, 0))
    strip.paste(c_240, (1024, 0))
    
    out_path = os.path.join(DIRECTORY, filename)
    strip.save(out_path)
    print(f"Saved Inspection Crop [{title}]: {out_path}")

# 1. Center Void Behavior
make_crop_comparison(
    (2048 - 384, 2048 - 384, 2048 + 384, 2048 + 384),
    (512 - 96, 512 - 96, 512 + 96, 512 + 96),
    "qa_crop_center_void.png",
    "Center Void"
)

# 2. Inner White/Cyan Caustics
make_crop_comparison(
    (2048 - 300, 1200, 2048 + 300, 1800),
    (512 - 75, 300, 512 + 75, 450),
    "qa_crop_inner_caustics.png",
    "Inner Caustics"
)

# 3. Microscopic Filament Continuity & Nested Secondary Loops
make_crop_comparison(
    (1800, 700, 2300, 1200),
    (450, 175, 575, 300),
    "qa_crop_secondary_loops.png",
    "Nested Secondary Loops & Filaments"
)

# 4. Faint Outer Gossamer Web
make_crop_comparison(
    (500, 500, 1200, 1200),
    (125, 125, 300, 300),
    "qa_crop_outer_gossamer_web.png",
    "Outer Gossamer Web"
)

# Compute Numerical Metrics
gt_arr = np.array(gt_thumb.convert("RGB")).astype(float)
m120_arr = np.array(m120_thumb.convert("RGB")).astype(float)
m240_arr = np.array(m240_thumb.convert("RGB")).astype(float)

def compute_psnr(a, b):
    mse = np.mean((a - b) ** 2)
    if mse == 0: return 100.0
    return float(20 * np.log10(255.0 / np.sqrt(mse)))

def compute_ssim(img1, img2):
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    im1_gray = 0.2989 * img1[:, :, 0] + 0.5870 * img1[:, :, 1] + 0.1140 * img1[:, :, 2]
    im2_gray = 0.2989 * img2[:, :, 0] + 0.5870 * img2[:, :, 1] + 0.1140 * img2[:, :, 2]
    mu1, mu2 = np.mean(im1_gray), np.mean(im2_gray)
    sigma1_sq, sigma2_sq = np.var(im1_gray), np.var(im2_gray)
    sigma12 = np.mean((im1_gray - mu1) * (im2_gray - mu2))
    return float(((2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)) / ((mu1**2 + mu2**2 + c1) * (sigma1_sq + sigma2_sq + c2)))

metrics = {
    "dimensions_120": im_120.size,
    "dimensions_240": im_240.size,
    "elapsed_120_sec": res120["elapsedSec"],
    "elapsed_240_sec": res240["elapsedSec"],
    "psnr_120_vs_gt": round(compute_psnr(m120_arr, gt_arr), 2),
    "ssim_120_vs_gt": round(compute_ssim(m120_arr, gt_arr), 4),
    "psnr_240_vs_gt": round(compute_psnr(m240_arr, gt_arr), 2),
    "ssim_240_vs_gt": round(compute_ssim(m240_arr, gt_arr), 4),
    "psnr_240_vs_120": round(compute_psnr(m240_arr, m120_arr), 2),
    "ssim_240_vs_120": round(compute_ssim(m240_arr, m120_arr), 4),
    "max_lum_120": float(np.max(m120_arr)),
    "max_lum_240": float(np.max(m240_arr)),
    "non_zero_pct_120": round(float(np.mean(np.any(m120_arr > 5, axis=-1))) * 100, 2),
    "non_zero_pct_240": round(float(np.mean(np.any(m240_arr > 5, axis=-1))) * 100, 2)
}

with open(os.path.join(DIRECTORY, "reference_master_qa_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

print("\n=======================================================")
print("REFERENCE MASTER VISUAL QA METRICS")
print("=======================================================")
print(json.dumps(metrics, indent=2))
print("=======================================================\n")
