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
from PIL import Image, ImageDraw, ImageFont

PORT = 8796
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
OUT_DIR = os.path.join(DIRECTORY, "visual_detail_audit")
os.makedirs(OUT_DIR, exist_ok=True)

done_event = threading.Event()
received_captures = {}
workload_metrics = {}

class AuditHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global received_captures, workload_metrics
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/save_checkpoint':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            payload = json.loads(body.decode('utf-8'))
            
            name = payload.get('name', 'unknown')
            data_url = payload.get('dataUrl', '')
            meta = payload.get('meta', {})
            
            if ',' in data_url:
                data_url = data_url.split(',', 1)[1]
            img_bytes = base64.b64decode(data_url)
            
            file_path = os.path.join(OUT_DIR, f"{name}.png")
            with open(file_path, "wb") as f:
                f.write(img_bytes)
            
            received_captures[name] = {
                'path': file_path,
                'meta': meta
            }
            print(f"[AUDIT] Saved {name}.png ({len(img_bytes)//1024} KB) - frames: {meta.get('completedFrames')}, elapsed: {meta.get('actualElapsedMs', 0):.1f}ms, fps: {meta.get('effectiveFps', 0):.1f}")
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")

        elif parsed.path == '/finish':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            workload_metrics.update(json.loads(body.decode('utf-8')))
            
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
<title>Controlled Visual Detail Audit</title>
<style>
  html, body { margin: 0; padding: 0; width: 1200px; height: 800px; overflow: hidden; background: #010307; font-family: monospace; }
  canvas { width: 1200px; height: 800px; display: block; }
  #status { position: absolute; top: 10px; left: 10px; font-size: 13px; background: rgba(0,0,0,0.85); color: #8da4c4; padding: 8px 12px; border: 1px solid #224477; border-radius: 4px; z-index: 100; }
</style>
</head>
<body>
<div id="status">Initializing Controlled Visual Detail Audit Suite...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

function nextFrame() {
  return new Promise(r => requestAnimationFrame(r));
}

async function uploadCheckpoint(name, meta = {}) {
  const canvas = document.getElementById('c');
  const dataUrl = canvas.toDataURL('image/png');
  await fetch('/save_checkpoint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, dataUrl, meta })
  });
}

window.onload = async function() {
  const canvas = document.getElementById('c');
  const statusEl = document.getElementById('status');

  // 1. FREEZE EVERYTHING
  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);
  math.evolving = false; // Freeze temporal drift

  const renderer = new MobiusRenderer(canvas);
  // Force fixed DPR 1.0 on 1200x800 for exact pixel parity
  renderer.adaptive.getDpr = () => 1.0;
  renderer.resize(1200, 800);
  renderer.zoom = 1.65;
  renderer.targetZoom = 1.65;
  renderer.viewCenter = [0.0, 0.0];
  renderer.targetViewCenter = [0.0, 0.0];
  renderer.bloomEnabled = true;
  renderer.viewMode = 0; // Standard tonemapping view
  renderer.currentPersistence = 1.0; // Deterministic pure photon accumulation

  const gl = renderer.gl;
  const extTimer = renderer.profiler.ext;

  // Measurement definition
  // Baseline run: Brute Force (589k x 16) vs Standard Adaptive (150k x 8) at 1s, 3s, 5s, 10s, 20s
  // Experimental run: 180k x 8 and 150k x 10 at 3s, 5s, 10s
  const runs = [
    {
      id: 'brute_force',
      label: 'OLD BRUTE FORCE (589,824 x 16)',
      particles: 589824,
      steps: 16,
      checkpoints: [1.0, 3.0, 5.0, 10.0, 20.0]
    },
    {
      id: 'adaptive_std',
      label: 'CURRENT ADAPTIVE STD (150,000 x 8)',
      particles: 150000,
      steps: 8,
      checkpoints: [1.0, 3.0, 5.0, 10.0, 20.0]
    },
    {
      id: 'exp_180k_8',
      label: 'EXPERIMENTAL A (180,000 x 8)',
      particles: 180000,
      steps: 8,
      checkpoints: [3.0, 5.0, 10.0]
    },
    {
      id: 'exp_150k_10',
      label: 'EXPERIMENTAL B (150,000 x 10)',
      particles: 150000,
      steps: 10,
      checkpoints: [3.0, 5.0, 10.0]
    }
  ];

  const summaryMetrics = {};

  for (const run of runs) {
    statusEl.innerText = `Preparing workload: ${run.label}...`;
    renderer.setParticleCount(run.particles);
    renderer.setStepsOverride(run.steps);
    renderer.currentPersistence = 1.0;
    renderer.clearAccumulation();

    // Attractor Warmup: run 15 simulation steps so initial seeds converge to attractor without accumulation
    for (let w = 0; w < 15; w++) {
      math.update(0.016, renderer.zoom);
      renderer.render(math, 0.016);
      await nextFrame();
    }
    renderer.clearAccumulation();
    gl.finish();

    // Measure GPU frame time with timer query
    let measuredGpuMs = null;
    if (extTimer) {
      const q = gl.createQuery();
      gl.beginQuery(extTimer.TIME_ELAPSED_EXT, q);
      renderer.render(math, 0.016);
      gl.endQuery(extTimer.TIME_ELAPSED_EXT);
      gl.flush();

      for (let poll = 0; poll < 150; poll++) {
        await new Promise(r => setTimeout(r, 10));
        if (gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE)) {
          measuredGpuMs = gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6;
          break;
        }
      }
      gl.deleteQuery(q);
    }
    renderer.clearAccumulation();
    gl.finish();

    statusEl.innerText = `Running wall-clock capture for ${run.label} (GPU: ${measuredGpuMs ? measuredGpuMs.toFixed(2) + 'ms' : 'N/A'})...`;

    summaryMetrics[run.id] = {
      label: run.label,
      particles: run.particles,
      steps: run.steps,
      depositsPerFrame: run.particles * run.steps,
      measuredGpuMs: measuredGpuMs,
      checkpoints: {}
    };

    // Run progressive accumulation strictly driven by performance.now() elapsed wall-clock time
    await new Promise(resolve => {
      let frameCount = 0;
      let targetIdx = 0;
      const startTime = performance.now();

      async function onFrame(now) {
        math.update(0.016, renderer.zoom);
        renderer.render(math, 0.016);
        frameCount++;

        const elapsedMs = performance.now() - startTime;
        const targetSec = run.checkpoints[targetIdx];

        if (elapsedMs >= targetSec * 1000) {
          gl.finish();
          const effectiveFps = (frameCount * 1000) / elapsedMs;
          const meta = {
            workloadId: run.id,
            label: run.label,
            targetSec: targetSec,
            actualElapsedMs: elapsedMs,
            completedFrames: frameCount,
            effectiveFps: effectiveFps,
            particles: run.particles,
            steps: run.steps,
            depositsPerFrame: run.particles * run.steps,
            totalDeposits: frameCount * run.particles * run.steps,
            measuredGpuMs: measuredGpuMs
          };

          summaryMetrics[run.id].checkpoints[targetSec] = meta;
          statusEl.innerText = `[${run.id}] Captured ${targetSec}s (${frameCount} frames in ${(elapsedMs/1000).toFixed(2)}s, ${effectiveFps.toFixed(1)} FPS)...`;

          const imgName = `${run.id}_${targetSec}s_full`;
          await uploadCheckpoint(imgName, meta);

          targetIdx++;
          if (targetIdx >= run.checkpoints.length) {
            resolve();
            return;
          }
        }

        requestAnimationFrame(onFrame);
      }

      requestAnimationFrame(onFrame);
    });
  }

  statusEl.innerText = "All workloads captured. Reporting metrics to server...";
  await fetch('/finish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(summaryMetrics)
  });
  statusEl.innerText = "Controlled Visual Detail Audit Complete!";
};
</script>
</body>
</html>
"""

def compute_gradient_mag(gray):
    # Sobel gradient magnitude
    # 3x3 Sobel kernel x
    # [-1, 0, 1]
    # [-2, 0, 2]
    # [-1, 0, 1]
    gx = (
        -1.0 * gray[:-2, :-2] + 1.0 * gray[:-2, 2:] +
        -2.0 * gray[1:-1, :-2] + 2.0 * gray[1:-1, 2:] +
        -1.0 * gray[2:, :-2] + 1.0 * gray[2:, 2:]
    ) * (1.0 / 8.0)
    # 3x3 Sobel kernel y
    # [-1, -2, -1]
    # [ 0,  0,  0]
    # [ 1,  2,  1]
    gy = (
        -1.0 * gray[:-2, :-2] - 2.0 * gray[:-2, 1:-1] - 1.0 * gray[:-2, 2:] +
         1.0 * gray[2:, :-2] + 2.0 * gray[2:, 1:-1] + 1.0 * gray[2:, 2:]
    ) * (1.0 / 8.0)
    mag = np.hypot(gx, gy)
    return mag

def compute_local_contrast(gray, patch_size=16):
    h, w = gray.shape
    stds = []
    for r in range(0, h - patch_size + 1, patch_size):
        for c in range(0, w - patch_size + 1, patch_size):
            patch = gray[r:r+patch_size, c:c+patch_size]
            # only compute contrast in regions with features (mean > 5)
            if np.mean(patch) > 5.0:
                stds.append(np.std(patch))
    return float(np.mean(stds)) if stds else 0.0

def compute_ssim(img1, img2):
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu1 = np.mean(img1)
    mu2 = np.mean(img2)
    s1_sq = np.var(img1)
    s2_sq = np.var(img2)
    s12 = np.mean((img1 - mu1) * (img2 - mu2))
    num = (2 * mu1 * mu2 + c1) * (2 * s12 + c2)
    den = (mu1**2 + mu2**2 + c1) * (s1_sq + s2_sq + c2)
    return float(num / den)

def compute_psnr(img1, img2):
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return 100.0
    return float(20 * np.log10(255.0 / np.sqrt(mse)))

def process_audit_images():
    print("\n=======================================================")
    print("PROCESSING AUDIT IMAGES & GENERATING REQUIRED ARTIFACTS")
    print("=======================================================\n")
    
    # Crop definitions on 1200x800 canvas:
    # B. Medium close crop (400x400): [550, 150, 950, 550]
    #    Contains: bright caustic ridge, smaller loops, thin outer filaments
    CROP_MEDIUM_BOX = (550, 150, 950, 550)
    # C. Fine-detail crop (300x300): [750, 200, 1050, 500]
    #    Contains: hairline trajectories, nested loops, faint strands, low-density structure
    CROP_DETAIL_BOX = (750, 200, 1050, 500)
    
    full_images = {}
    medium_crops = {}
    detail_crops = {}
    
    # 1. Generate Crops for all captured full images
    for name, item in received_captures.items():
        img_path = item['path']
        img = Image.open(img_path).convert('RGB')
        
        # Save full
        full_images[name] = img
        
        # Medium crop B
        med_img = img.crop(CROP_MEDIUM_BOX)
        med_name = name.replace('_full', '_crop_medium')
        med_path = os.path.join(OUT_DIR, f"{med_name}.png")
        med_img.save(med_path)
        medium_crops[med_name] = med_img
        
        # Detail crop C
        det_img = img.crop(CROP_DETAIL_BOX)
        det_name = name.replace('_full', '_crop_detail')
        det_path = os.path.join(OUT_DIR, f"{det_name}.png")
        det_img.save(det_path)
        detail_crops[det_name] = det_img

    print(f"Generated medium crops: {len(medium_crops)}, detail crops: {len(detail_crops)}")

    # 2. Build Side-by-Side Composites for Checkpoints:
    # Requirements: OLD BRUTE FORCE | CURRENT ADAPTIVE
    # For 1s, 3s, 5s, 10s, 20s
    checkpoints = [1.0, 3.0, 5.0, 10.0, 20.0]
    side_by_side_reports = {}

    for t_val in checkpoints:
        t_str = f"{t_val}s"
        b_full_key = f"brute_force_{t_val}s_full"
        a_full_key = f"adaptive_std_{t_val}s_full"
        b_med_key = f"brute_force_{t_val}s_crop_medium"
        a_med_key = f"adaptive_std_{t_val}s_crop_medium"
        b_det_key = f"brute_force_{t_val}s_crop_detail"
        a_det_key = f"adaptive_std_{t_val}s_crop_detail"

        if b_full_key not in full_images or a_full_key not in full_images:
            print(f"Skipping {t_str} - missing full image")
            continue

        img_b_full = full_images[b_full_key]
        img_a_full = full_images[a_full_key]
        img_b_med = medium_crops[b_med_key]
        img_a_med = medium_crops[a_med_key]
        img_b_det = detail_crops[b_det_key]
        img_a_det = detail_crops[a_det_key]

        # Full side-by-side (2400 x 800)
        sbs_full = Image.new('RGB', (2400, 800))
        sbs_full.paste(img_b_full, (0, 0))
        sbs_full.paste(img_a_full, (1200, 0))
        sbs_full_path = os.path.join(OUT_DIR, f"comparison_{t_str}_full_side_by_side.png")
        sbs_full.save(sbs_full_path)

        # Medium crop side-by-side (800 x 400)
        sbs_med = Image.new('RGB', (800, 400))
        sbs_med.paste(img_b_med, (0, 0))
        sbs_med.paste(img_a_med, (400, 0))
        sbs_med_path = os.path.join(OUT_DIR, f"comparison_{t_str}_medium_crop_side_by_side.png")
        sbs_med.save(sbs_med_path)

        # Detail crop side-by-side (600 x 300)
        sbs_det = Image.new('RGB', (600, 300))
        sbs_det.paste(img_b_det, (0, 0))
        sbs_det.paste(img_a_det, (300, 0))
        sbs_det_path = os.path.join(OUT_DIR, f"comparison_{t_str}_detail_crop_side_by_side.png")
        sbs_det.save(sbs_det_path)

        # Combined 3-view composite for this checkpoint (1200 x 1100)
        # Top: side-by-side full scaled to 600x400 each (1200x400)
        # Bottom Left: side-by-side medium crops (800x400 -> scaled to 600x300)
        # Bottom Right: side-by-side detail crops (600x300)
        # Or clean vertical stack of Full (scaled to 1200x400), Medium (800x400), Detail (600x300)
        print(f"[OK] Generated Side-by-Side comparisons for {t_str}")

    # 3. BUILD LARGE COMPARISON GRID SHEET (Section 5 requirement)
    # Rows: 1s, 3s, 5s, 10s, 20s
    # Columns: Brute Full | Adaptive Full | Brute Detail | Adaptive Detail
    # Dimensions: 5 rows x 4 columns
    # Let's scale Full images to 600x400, Detail crops to 400x400 (scaled up from 300x300 with high quality)
    # Column widths: 600, 600, 400, 400 => Total width = 2000 px
    # Row height: 400 px => Total height for 5 rows = 2000 px (+ 60px header = 2060 px)
    grid_w = 2000
    grid_h = 2060
    grid_img = Image.new('RGB', (grid_w, grid_h), color=(1, 3, 7))
    draw = ImageDraw.Draw(grid_img)
    
    # Header
    col_x = [0, 600, 1200, 1600]
    col_titles = [
        "OLD BRUTE FORCE (589k x 16) - FULL VIEW",
        "CURRENT ADAPTIVE (150k x 8) - FULL VIEW",
        "BRUTE FORCE - DETAIL CROP",
        "ADAPTIVE - DETAIL CROP"
    ]
    
    # Simple labels at top
    for i, title in enumerate(col_titles):
        draw.text((col_x[i] + 15, 20), title, fill=(180, 210, 245))

    for r_idx, t_val in enumerate(checkpoints):
        y_pos = 60 + r_idx * 400
        t_str = f"{t_val}s"

        b_full = full_images[f"brute_force_{t_val}s_full"].resize((600, 400), Image.Resampling.LANCZOS)
        a_full = full_images[f"adaptive_std_{t_val}s_full"].resize((600, 400), Image.Resampling.LANCZOS)
        b_det = detail_crops[f"brute_force_{t_val}s_crop_detail"].resize((400, 400), Image.Resampling.NEAREST)
        a_det = detail_crops[f"adaptive_std_{t_val}s_crop_detail"].resize((400, 400), Image.Resampling.NEAREST)

        grid_img.paste(b_full, (0, y_pos))
        grid_img.paste(a_full, (600, y_pos))
        grid_img.paste(b_det, (1200, y_pos))
        grid_img.paste(a_det, (1600, y_pos))

        # Row timestamp watermark
        draw.rectangle([5, y_pos + 5, 85, y_pos + 30], fill=(0, 0, 0))
        draw.text((10, y_pos + 10), f"TIME: {t_str}", fill=(255, 220, 100))

    grid_path = os.path.join(OUT_DIR, "large_comparison_grid_5x4.png")
    grid_img.save(grid_path)
    print(f"[OK] Saved large comparison grid sheet to {grid_path}")

    # 4. Experimental Workloads 3-Way Comparisons (at 3s, 5s, 10s)
    # 150k x 8 vs 180k x 8 vs 150k x 10
    exp_times = [3.0, 5.0, 10.0]
    for t_val in exp_times:
        t_str = f"{t_val}s"
        std_full = full_images[f"adaptive_std_{t_val}s_full"].resize((600, 400), Image.Resampling.LANCZOS)
        e180_full = full_images[f"exp_180k_8_{t_val}s_full"].resize((600, 400), Image.Resampling.LANCZOS)
        e150_full = full_images[f"exp_150k_10_{t_val}s_full"].resize((600, 400), Image.Resampling.LANCZOS)

        # 3-way full (1800 x 400)
        exp_full_strip = Image.new('RGB', (1800, 450), color=(1, 3, 7))
        exp_full_strip.paste(std_full, (0, 50))
        exp_full_strip.paste(e180_full, (600, 50))
        exp_full_strip.paste(e150_full, (1200, 50))
        d_strip = ImageDraw.Draw(exp_full_strip)
        d_strip.text((20, 15), f"STANDARD (150k x 8) @ {t_str}", fill=(180, 210, 245))
        d_strip.text((620, 15), f"EXPERIMENTAL A (180k x 8) @ {t_str}", fill=(180, 210, 245))
        d_strip.text((1220, 15), f"EXPERIMENTAL B (150k x 10) @ {t_str}", fill=(180, 210, 245))
        exp_full_path = os.path.join(OUT_DIR, f"experimental_comparison_{t_str}_full.png")
        exp_full_strip.save(exp_full_path)

        # 3-way detail crops (900 x 300)
        std_det = detail_crops[f"adaptive_std_{t_val}s_crop_detail"]
        e180_det = detail_crops[f"exp_180k_8_{t_val}s_crop_detail"]
        e150_det = detail_crops[f"exp_150k_10_{t_val}s_crop_detail"]

        exp_det_strip = Image.new('RGB', (900, 340), color=(1, 3, 7))
        exp_det_strip.paste(std_det, (0, 40))
        exp_det_strip.paste(e180_det, (300, 40))
        exp_det_strip.paste(e150_det, (600, 40))
        d_det = ImageDraw.Draw(exp_det_strip)
        d_det.text((10, 10), f"150k x 8 ({t_str})", fill=(180, 210, 245))
        d_det.text((310, 10), f"180k x 8 ({t_str})", fill=(180, 210, 245))
        d_det.text((610, 10), f"150k x 10 ({t_str})", fill=(180, 210, 245))
        exp_det_path = os.path.join(OUT_DIR, f"experimental_comparison_{t_str}_detail.png")
        exp_det_strip.save(exp_det_path)

    # 5. Compute Quantitative Metrics for all views
    quantitative_results = {}

    all_views_to_measure = [
        ('full', full_images),
        ('medium', medium_crops),
        ('detail', detail_crops)
    ]

    for view_type, img_dict in all_views_to_measure:
        quantitative_results[view_type] = {}
        for name, img in img_dict.items():
            arr = np.array(img, dtype=float)
            gray = 0.2989 * arr[:,:,0] + 0.5870 * arr[:,:,1] + 0.1140 * arr[:,:,2]
            
            # Non-background feature count (> 5.0)
            feat_pixels = int(np.sum(gray > 5.0))
            feat_pct = float(feat_pixels / gray.size * 100.0)
            
            # Max intensity, mean intensity
            max_val = float(np.max(gray))
            mean_val = float(np.mean(gray))
            
            # Sobel Gradient & Edge Density
            gmag = compute_gradient_mag(gray)
            edge_soft = int(np.sum(gmag > 5.0))
            edge_hard = int(np.sum(gmag > 15.0))
            edge_soft_pct = float(edge_soft / gmag.size * 100.0)
            edge_hard_pct = float(edge_hard / gmag.size * 100.0)
            mean_edge = float(np.mean(gmag))
            
            # Local contrast
            loc_contrast = compute_local_contrast(gray, patch_size=16)

            quantitative_results[view_type][name] = {
                'dimensions': list(img.size),
                'mean_intensity': round(mean_val, 2),
                'max_intensity': round(max_val, 2),
                'feature_pixels': feat_pixels,
                'feature_pixel_pct': round(feat_pct, 2),
                'edges_soft_gt5': edge_soft,
                'edges_soft_pct': round(edge_soft_pct, 2),
                'edges_hard_gt15': edge_hard,
                'edges_hard_pct': round(edge_hard_pct, 2),
                'mean_edge_gradient': round(mean_edge, 3),
                'local_contrast_std': round(loc_contrast, 2)
            }

    # Cross-comparison metrics between Brute and Adaptive
    correlations = {}
    for t_val in checkpoints:
        t_str = f"{t_val}s"
        correlations[t_str] = {}
        for v_type in ['full', 'crop_medium', 'crop_detail']:
            b_name = f"brute_force_{t_val}s_{v_type}"
            a_name = f"adaptive_std_{t_val}s_{v_type}"
            
            dict_ref = full_images if v_type == 'full' else (medium_crops if 'medium' in v_type else detail_crops)
            if b_name not in dict_ref or a_name not in dict_ref:
                continue

            b_arr = np.array(dict_ref[b_name], dtype=float)
            a_arr = np.array(dict_ref[a_name], dtype=float)

            b_gray = 0.2989 * b_arr[:,:,0] + 0.5870 * b_arr[:,:,1] + 0.1140 * b_arr[:,:,2]
            a_gray = 0.2989 * a_arr[:,:,0] + 0.5870 * a_arr[:,:,1] + 0.1140 * a_arr[:,:,2]

            # Intensity Pearson correlation
            r_int = float(np.corrcoef(b_gray.ravel(), a_gray.ravel())[0, 1])

            # Sobel Edge Pearson correlation
            b_gmag = compute_gradient_mag(b_gray)
            a_gmag = compute_gradient_mag(a_gray)
            r_edge = float(np.corrcoef(b_gmag.ravel(), a_gmag.ravel())[0, 1])

            # SSIM and PSNR
            ssim_val = compute_ssim(b_gray, a_gray)
            psnr_val = compute_psnr(b_gray, a_gray)

            correlations[t_str][v_type] = {
                'intensity_correlation': round(r_int, 4),
                'sobel_edge_correlation': round(r_edge, 4),
                'ssim': round(ssim_val, 4),
                'psnr_db': round(psnr_val, 2)
            }

    final_report = {
        'workload_metrics': workload_metrics,
        'quantitative_metrics': quantitative_results,
        'cross_correlations': correlations
    }

    report_path = os.path.join(OUT_DIR, "visual_detail_audit_report.json")
    with open(report_path, "w") as f:
        json.dump(final_report, f, indent=2)

    print(f"\n[OK] Full Visual Detail Audit Report saved to {report_path}")
    return final_report

def main():
    harness_path = os.path.join(DIRECTORY, "detail_audit_harness.html")
    with open(harness_path, "w") as f:
        f.write(html_page)

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), AuditHandler)
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
        f"http://localhost:{PORT}/detail_audit_harness.html"
    ]

    print("[AUDIT] Launching Chrome Headless for Controlled Visual Detail Audit Suite...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Brute: 20s, Adaptive: 20s, ExpA: 10s, ExpB: 10s = ~60s total test time
    # Allow 180s timeout
    success = done_event.wait(timeout=180)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success:
        print("[ERROR] Visual detail audit timed out or failed!")
        return False

    print("\n[AUDIT] All browser captures successfully received! Now computing metrics & composites...")
    process_audit_images()
    return True

if __name__ == '__main__':
    main()
