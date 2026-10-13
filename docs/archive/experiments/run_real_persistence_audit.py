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

PORT = 8895
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
OUT_DIR = os.path.join(DIRECTORY, "persistence_audit")
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
            p_val = meta.get('currentPersistence', 0.9985)
            print(f"[AUDIT] Saved {name}.png ({len(img_bytes)//1024} KB) | P: {p_val:.4f} | frames: {meta.get('completedFrames')} | active: {meta.get('activeElapsedMs', 0):.0f}ms | fps: {meta.get('effectiveFps', 0):.1f} | GPU: {meta.get('measuredGpuMs', 0):.2f}ms")
            
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
<title>Real Production Detail Audit (Persistence = 0.9985)</title>
<style>
  html, body { margin: 0; padding: 0; width: 1200px; height: 800px; overflow: hidden; background: #010307; font-family: monospace; }
  canvas { width: 1200px; height: 800px; display: block; }
  #status { position: absolute; top: 10px; left: 10px; font-size: 13px; background: rgba(0,0,0,0.85); color: #8da4c4; padding: 8px 12px; border: 1px solid #224477; border-radius: 4px; z-index: 100; }
</style>
</head>
<body>
<div id="status">Initializing Real Production Detail Audit Suite...</div>
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

  // 1. SETUP MATH SYSTEM WITH FROZEN TEMPORAL DRIFT BUT LIVE/EVOLVING PERSISTENCE STATE
  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);
  math.update(0, 1.65); // Initialize static attractor parameters at t = 0
  
  // Freeze coefficient drift completely: math.time stays at 0, no temporal drift
  math.update = function() {};
  // Crucial: math.evolving remains true so renderer.js line 842 does NOT trigger persistence=1.0 override!
  math.evolving = true;

  const renderer = new MobiusRenderer(canvas);
  // Force fixed DPR 1.0 on 1200x800 for exact pixel parity across runs
  renderer.adaptive.getDpr = () => 1.0;
  renderer.resize(1200, 800);
  renderer.zoom = 1.65;
  renderer.targetZoom = 1.65;
  renderer.viewCenter = [0.0, 0.0];
  renderer.targetViewCenter = [0.0, 0.0];
  renderer.bloomEnabled = true;
  renderer.viewMode = 0; // Standard tonemapping view

  // 2. CONFIRM AND ENFORCE REAL PRODUCTION IDLE PERSISTENCE = 0.9985
  const prodPersistence = renderer.currentPersistence;
  console.log("MobiusRenderer instantiated with currentPersistence:", prodPersistence);
  renderer.persistence = 0.9985;
  renderer.currentPersistence = 0.9985;

  // Wrap render to guarantee persistence = 0.9985 on EVERY single frame
  const origRender = renderer.render.bind(renderer);
  renderer.render = function(m, dt, jsTime) {
    m.evolving = true;
    this.currentPersistence = 0.9985;
    const res = origRender(m, dt, jsTime);
    this.currentPersistence = 0.9985;
    return res;
  };

  const gl = renderer.gl;
  const extTimer = renderer.profiler.ext;

  // Workloads:
  // A. Brute Force Reference: 589,824 x 16
  // B. Current Production: 150,000 x 8
  // C. Intermediate Experiments: 155,000 x 8, 160,000 x 8, 165,000 x 8
  const runs = [
    {
      id: 'brute_force',
      label: 'BRUTE FORCE (589,824 x 16)',
      particles: 589824,
      steps: 16,
      checkpoints: [1, 3, 5, 10, 20, 30]
    },
    {
      id: 'prod_150k_8',
      label: 'CURRENT PRODUCTION (150,000 x 8)',
      particles: 150000,
      steps: 8,
      checkpoints: [1, 3, 5, 10, 20, 30]
    },
    {
      id: 'exp_155k_8',
      label: 'INTERMEDIATE (155,000 x 8)',
      particles: 155000,
      steps: 8,
      checkpoints: [1, 3, 5, 10, 20, 30]
    },
    {
      id: 'exp_160k_8',
      label: 'INTERMEDIATE (160,000 x 8)',
      particles: 160000,
      steps: 8,
      checkpoints: [1, 3, 5, 10, 20, 30]
    },
    {
      id: 'exp_165k_8',
      label: 'INTERMEDIATE (165,000 x 8)',
      particles: 165000,
      steps: 8,
      checkpoints: [1, 3, 5, 10, 20, 30]
    }
  ];

  const summaryMetrics = {};

  for (const run of runs) {
    statusEl.innerText = `Preparing workload: ${run.label}...`;
    renderer.setParticleCount(run.particles);
    renderer.setStepsOverride(run.steps);
    renderer.currentPersistence = 0.9985;
    renderer.clearAccumulation();

    // Attractor Warmup: 20 simulation frames so random seeds converge to attractor manifold
    for (let w = 0; w < 20; w++) {
      renderer.render(math, 0.016);
      await nextFrame();
    }
    renderer.clearAccumulation();
    gl.finish();

    // Measure GPU frame time with timer query over 5 frames
    let measuredGpuMs = null;
    if (extTimer) {
      const qTimes = [];
      for (let qf = 0; qf < 5; qf++) {
        const q = gl.createQuery();
        gl.beginQuery(extTimer.TIME_ELAPSED_EXT, q);
        renderer.render(math, 0.016);
        gl.endQuery(extTimer.TIME_ELAPSED_EXT);
        gl.flush();

        for (let poll = 0; poll < 150; poll++) {
          await new Promise(r => setTimeout(r, 5));
          if (gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE)) {
            qTimes.push(gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6);
            break;
          }
        }
        gl.deleteQuery(q);
      }
      if (qTimes.length > 0) {
        measuredGpuMs = qTimes.reduce((a, b) => a + b, 0) / qTimes.length;
      }
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
      persistence: 0.9985,
      checkpoints: {}
    };

    // Real wall-clock elapsed timing loop with paused duration deduction during PNG upload
    await new Promise(resolve => {
      let frameCount = 0;
      let targetIdx = 0;
      let pausedDuration = 0;
      const startTime = performance.now();

      async function onFrame(now) {
        renderer.render(math, 0.016);
        frameCount++;

        const currentNow = performance.now();
        const activeElapsedMs = (currentNow - startTime) - pausedDuration;
        const targetSec = run.checkpoints[targetIdx];

        if (activeElapsedMs >= targetSec * 1000) {
          gl.finish();
          const pauseStart = performance.now();

          const effectiveFps = (frameCount * 1000) / activeElapsedMs;
          const currentGpuMs = (renderer.profiler && renderer.profiler.metrics && renderer.profiler.metrics.gpuMs > 0)
            ? renderer.profiler.metrics.gpuMs
            : measuredGpuMs;

          const meta = {
            workloadId: run.id,
            label: run.label,
            targetSec: targetSec,
            activeElapsedMs: activeElapsedMs,
            completedFrames: frameCount,
            effectiveFps: effectiveFps,
            particles: run.particles,
            steps: run.steps,
            depositsPerFrame: run.particles * run.steps,
            currentPersistence: renderer.currentPersistence,
            measuredGpuMs: measuredGpuMs,
            profilerGpuMs: currentGpuMs
          };

          summaryMetrics[run.id].checkpoints[targetSec] = meta;
          statusEl.innerText = `[${run.id}] Captured ${targetSec}s (${frameCount} frames in ${(activeElapsedMs/1000).toFixed(2)}s, ${effectiveFps.toFixed(1)} FPS)...`;

          const imgName = `${run.id}_${targetSec}s_full`;
          await uploadCheckpoint(imgName, meta);

          const pauseEnd = performance.now();
          pausedDuration += (pauseEnd - pauseStart);

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
  statusEl.innerText = "Real Production Detail Audit Complete!";
};
</script>
</body>
</html>
"""

def compute_gradient_mag(gray):
    gx = (
        -1.0 * gray[:-2, :-2] + 1.0 * gray[:-2, 2:] +
        -2.0 * gray[1:-1, :-2] + 2.0 * gray[1:-1, 2:] +
        -1.0 * gray[2:, :-2] + 1.0 * gray[2:, 2:]
    ) * (1.0 / 8.0)
    gy = (
        -1.0 * gray[:-2, :-2] - 2.0 * gray[:-2, 1:-1] - 1.0 * gray[:-2, 2:] +
         1.0 * gray[2:, :-2] + 2.0 * gray[2:, 1:-1] + 1.0 * gray[2:, 2:]
    ) * (1.0 / 8.0)
    mag = np.hypot(gx, gy)
    return mag

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
    print("PROCESSING REAL AUDIT IMAGES & GENERATING COMPOSITES")
    print("=======================================================\n")
    
    # 4 distinct evaluation views:
    # 1. Full organism: 1200 x 800
    # 2. Medium crop: [550, 150, 950, 550] (400x400)
    # 3. Fine filament crop: [750, 200, 1050, 500] (300x300)
    # 4. Faint outer-envelope crop: [850, 80, 1150, 380] (300x300)
    CROP_MEDIUM_BOX = (550, 150, 950, 550)
    CROP_FILAMENT_BOX = (750, 200, 1050, 500)
    CROP_ENVELOPE_BOX = (850, 80, 1150, 380)
    CAUSTIC_ZONE_BOX = (550, 250, 750, 450)
    
    full_images = {}
    medium_crops = {}
    filament_crops = {}
    envelope_crops = {}

    try:
        font_large = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)
        font_small = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 13)
        font_tiny = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 11)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()

    # 1. Save and catalogue all crops
    for name, item in received_captures.items():
        img_path = item['path']
        img = Image.open(img_path).convert('RGB')
        full_images[name] = img
        
        # Medium
        m_img = img.crop(CROP_MEDIUM_BOX)
        m_name = name.replace('_full', '_crop_medium')
        m_img.save(os.path.join(OUT_DIR, f"{m_name}.png"))
        medium_crops[m_name] = m_img
        
        # Filament
        f_img = img.crop(CROP_FILAMENT_BOX)
        f_name = name.replace('_full', '_crop_filament')
        f_img.save(os.path.join(OUT_DIR, f"{f_name}.png"))
        filament_crops[f_name] = f_img
        
        # Envelope
        e_img = img.crop(CROP_ENVELOPE_BOX)
        e_name = name.replace('_full', '_crop_envelope')
        e_img.save(os.path.join(OUT_DIR, f"{e_name}.png"))
        envelope_crops[e_name] = e_img

    print(f"Catalogue complete: {len(full_images)} full, {len(medium_crops)} medium, {len(filament_crops)} filament, {len(envelope_crops)} envelope crops.")

    workloads = [
        ('brute_force', 'BRUTE FORCE (589k x 16)'),
        ('prod_150k_8', 'PROD STD (150k x 8)'),
        ('exp_155k_8', 'INTERMED (155k x 8)'),
        ('exp_160k_8', 'INTERMED (160k x 8)'),
        ('exp_165k_8', 'INTERMED (165k x 8)')
    ]
    
    checkpoints = [1, 3, 5, 10, 20, 30]
    comparison_times = [10, 20, 30]

    # 2. Build side-by-side screenshots at 10s, 20s, and 30s
    for t_val in comparison_times:
        t_str = f"{t_val}s"
        
        # A. Full Organism Side-by-Side (5 columns, 600x400 each => 3000 x 480)
        full_sbs = Image.new('RGB', (3000, 480), color=(1, 3, 7))
        draw_f = ImageDraw.Draw(full_sbs)
        
        for w_idx, (w_id, w_lbl) in enumerate(workloads):
            key = f"{w_id}_{t_str}_full"
            if key in full_images:
                f_scaled = full_images[key].resize((600, 400), Image.Resampling.LANCZOS)
                x_off = w_idx * 600
                full_sbs.paste(f_scaled, (x_off, 60))
                # Text header
                draw_f.rectangle([x_off, 0, x_off + 600, 60], fill=(5, 12, 24))
                draw_f.text((x_off + 15, 12), f"{w_lbl} @ {t_str}", fill=(180, 220, 255), font=font_large)
                # Metadata sublabel
                meta = received_captures[key]['meta']
                fps_txt = f"{meta.get('effectiveFps', 0):.1f} FPS | GPU: {meta.get('measuredGpuMs', 0):.2f}ms | Frames: {meta.get('completedFrames', 0)}"
                draw_f.text((x_off + 15, 36), fps_txt, fill=(120, 160, 200), font=font_small)
        
        p_full = os.path.join(OUT_DIR, f"comparison_{t_str}_full_organism.png")
        full_sbs.save(p_full)
        print(f"[OK] Saved {p_full}")

        # B. Medium Crop Side-by-Side (5 columns x 400px => 2000 x 470)
        med_sbs = Image.new('RGB', (2000, 470), color=(1, 3, 7))
        draw_m = ImageDraw.Draw(med_sbs)
        for w_idx, (w_id, w_lbl) in enumerate(workloads):
            key = f"{w_id}_{t_str}_crop_medium"
            if key in medium_crops:
                x_off = w_idx * 400
                med_sbs.paste(medium_crops[key], (x_off, 60))
                draw_m.rectangle([x_off, 0, x_off + 400, 60], fill=(5, 12, 24))
                draw_m.text((x_off + 10, 12), f"{w_lbl}", fill=(180, 220, 255), font=font_small)
                draw_m.text((x_off + 10, 36), f"Medium Crop (400x400) @ {t_str}", fill=(120, 160, 200), font=font_tiny)
        p_med = os.path.join(OUT_DIR, f"comparison_{t_str}_medium_crop.png")
        med_sbs.save(p_med)
        print(f"[OK] Saved {p_med}")

        # C. Fine Filament Crop Side-by-Side (5 columns x 300px => 1500 x 370)
        fil_sbs = Image.new('RGB', (1500, 370), color=(1, 3, 7))
        draw_fil = ImageDraw.Draw(fil_sbs)
        for w_idx, (w_id, w_lbl) in enumerate(workloads):
            key = f"{w_id}_{t_str}_crop_filament"
            if key in filament_crops:
                x_off = w_idx * 300
                fil_sbs.paste(filament_crops[key], (x_off, 60))
                draw_fil.rectangle([x_off, 0, x_off + 300, 60], fill=(5, 12, 24))
                draw_fil.text((x_off + 10, 12), f"{w_lbl}", fill=(180, 220, 255), font=font_small)
                draw_fil.text((x_off + 10, 36), f"Filament Crop @ {t_str}", fill=(120, 160, 200), font=font_tiny)
        p_fil = os.path.join(OUT_DIR, f"comparison_{t_str}_fine_filament_crop.png")
        fil_sbs.save(p_fil)
        print(f"[OK] Saved {p_fil}")

        # D. Faint Outer-Envelope Crop Side-by-Side (5 columns x 300px => 1500 x 370)
        env_sbs = Image.new('RGB', (1500, 370), color=(1, 3, 7))
        draw_env = ImageDraw.Draw(env_sbs)
        for w_idx, (w_id, w_lbl) in enumerate(workloads):
            key = f"{w_id}_{t_str}_crop_envelope"
            if key in envelope_crops:
                x_off = w_idx * 300
                env_sbs.paste(envelope_crops[key], (x_off, 60))
                draw_env.rectangle([x_off, 0, x_off + 300, 60], fill=(5, 12, 24))
                draw_env.text((x_off + 10, 12), f"{w_lbl}", fill=(180, 220, 255), font=font_small)
                draw_env.text((x_off + 10, 36), f"Outer Envelope @ {t_str}", fill=(120, 160, 200), font=font_tiny)
        p_env = os.path.join(OUT_DIR, f"comparison_{t_str}_faint_envelope_crop.png")
        env_sbs.save(p_env)
        print(f"[OK] Saved {p_env}")

        # E. Master 4-View Panel for this Checkpoint (Width: 2000, Height: 400 + 400 + 300 + 300 + 120 = 1520)
        # Row 1: Full Organism (5 cols x 400x267 scaled)
        # Row 2: Medium Crop (5 cols x 400x400 native)
        # Row 3: Fine Filament (5 cols x 300x300 native, centered in 400px col)
        # Row 4: Faint Envelope (5 cols x 300x300 native, centered in 400px col)
        panel_w = 2000
        panel_h = 60 + 267 + 30 + 400 + 30 + 300 + 30 + 300 + 20
        panel_img = Image.new('RGB', (panel_w, panel_h), color=(1, 3, 7))
        draw_p = ImageDraw.Draw(panel_img)

        # Header
        draw_p.rectangle([0, 0, panel_w, 60], fill=(8, 18, 36))
        draw_p.text((20, 18), f"REAL PRODUCTION DETAIL AUDIT MASTER 4-VIEW COMPARISON @ {t_str} (PERSISTENCE = 0.9985)", fill=(240, 210, 100), font=font_large)

        for w_idx, (w_id, w_lbl) in enumerate(workloads):
            x_col = w_idx * 400
            # Column header
            meta = received_captures[f"{w_id}_{t_str}_full"]['meta']
            col_lbl = f"{w_lbl}\n{meta.get('effectiveFps', 0):.1f} FPS | {meta.get('measuredGpuMs', 0):.2f}ms"
            
            # Row 1: Full (scaled to 400x267)
            y_r1 = 60
            f_img_sc = full_images[f"{w_id}_{t_str}_full"].resize((400, 267), Image.Resampling.LANCZOS)
            panel_img.paste(f_img_sc, (x_col, y_r1 + 25))
            draw_p.text((x_col + 8, y_r1 + 5), f"{w_lbl} (Full)", fill=(180, 210, 245), font=font_tiny)

            # Row 2: Medium
            y_r2 = y_r1 + 267 + 30
            panel_img.paste(medium_crops[f"{w_id}_{t_str}_crop_medium"], (x_col, y_r2 + 25))
            draw_p.text((x_col + 8, y_r2 + 5), "Medium Lobe Crop (400x400)", fill=(180, 210, 245), font=font_tiny)

            # Row 3: Filament
            y_r3 = y_r2 + 400 + 30
            panel_img.paste(filament_crops[f"{w_id}_{t_str}_crop_filament"], (x_col + 50, y_r3 + 25))
            draw_p.text((x_col + 8, y_r3 + 5), "Fine Filament Crop (300x300)", fill=(180, 210, 245), font=font_tiny)

            # Row 4: Envelope
            y_r4 = y_r3 + 300 + 30
            panel_img.paste(envelope_crops[f"{w_id}_{t_str}_crop_envelope"], (x_col + 50, y_r4 + 25))
            draw_p.text((x_col + 8, y_r4 + 5), "Faint Outer Envelope Crop (300x300)", fill=(180, 210, 245), font=font_tiny)

        p_panel = os.path.join(OUT_DIR, f"comparison_{t_str}_master_4view_panel.png")
        panel_img.save(p_panel)
        print(f"[OK] Saved {p_panel}")

    # 3. Master Temporal Evolution Sheet (6 rows: 1s, 3s, 5s, 10s, 20s, 30s x 5 cols)
    # Rows: 1s, 3s, 5s, 10s, 20s, 30s
    temp_w = 2000
    temp_h = 60 + 6 * 267 + 20
    temp_img = Image.new('RGB', (temp_w, temp_h), color=(1, 3, 7))
    draw_t = ImageDraw.Draw(temp_img)
    draw_t.rectangle([0, 0, temp_w, 60], fill=(8, 18, 36))
    draw_t.text((20, 18), "TEMPORAL DETAIL EVOLUTION MATRIX (1s -> 3s -> 5s -> 10s -> 20s -> 30s @ PERSISTENCE=0.9985)", fill=(240, 210, 100), font=font_large)

    for r_idx, t_val in enumerate(checkpoints):
        y_pos = 60 + r_idx * 267
        t_str = f"{t_val}s"
        for c_idx, (w_id, w_lbl) in enumerate(workloads):
            key = f"{w_id}_{t_str}_full"
            if key in full_images:
                x_pos = c_idx * 400
                f_sc = full_images[key].resize((400, 267), Image.Resampling.LANCZOS)
                temp_img.paste(f_sc, (x_pos, y_pos))
                draw_t.rectangle([x_pos + 5, y_pos + 5, x_pos + 120, y_pos + 25], fill=(0, 0, 0))
                draw_t.text((x_pos + 8, y_pos + 8), f"{w_id} @ {t_str}", fill=(255, 220, 100), font=font_tiny)
    
    p_temp = os.path.join(OUT_DIR, "master_temporal_matrix_6x5.png")
    temp_img.save(p_temp)
    print(f"[OK] Saved {p_temp}")

    # 4. Compute all Quantitative Metrics per Workload per Checkpoint
    metrics_by_workload = {}
    for w_id, w_lbl in workloads:
        metrics_by_workload[w_id] = {
            'label': w_lbl,
            'checkpoints': {}
        }

    for w_id, w_lbl in workloads:
        for t_val in checkpoints:
            t_str = f"{t_val}s"
            key = f"{w_id}_{t_str}_full"
            if key not in full_images:
                continue

            full_arr = np.array(full_images[key], dtype=float)
            gray_full = 0.2989 * full_arr[:,:,0] + 0.5870 * full_arr[:,:,1] + 0.1140 * full_arr[:,:,2]
            
            # Visible feature pixels
            feat_pixels_gt5 = int(np.sum(gray_full > 5.0))
            feat_pixels_gt2 = int(np.sum(gray_full > 2.0))
            feat_pixel_pct = float(feat_pixels_gt5 / gray_full.size * 100.0)

            # Sobel Gradient & Edge count
            gmag = compute_gradient_mag(gray_full)
            hard_edge_count = int(np.sum(gmag > 15.0))
            soft_edge_count = int(np.sum(gmag > 5.0))
            mean_edge_gradient = float(np.mean(gmag))

            # Mean filament luminance
            fil_patch = gray_full[200:500, 750:1050]
            mean_filament_luminance = float(np.mean(fil_patch))

            # Faint outer-envelope luminance
            env_patch = gray_full[80:380, 850:1150]
            faint_envelope_luminance = float(np.mean(env_patch))

            # Caustic ridge luminance (top 2% in caustic zone)
            caustic_patch = gray_full[250:450, 550:750]
            caustic_sorted = np.sort(caustic_patch.ravel())
            top2_idx = int(0.02 * caustic_patch.size)
            caustic_ridge_luminance = float(np.mean(caustic_sorted[-top2_idx:]))
            caustic_max_luminance = float(np.max(caustic_patch))

            # Mean organism luminance (where gray > 5.0)
            org_pixels = gray_full[gray_full > 5.0]
            mean_org_luminance = float(np.mean(org_pixels)) if len(org_pixels) > 0 else 0.0

            # Timing metadata
            meta = received_captures[key]['meta']
            gpu_ms = meta.get('measuredGpuMs', 0.0)
            fps = meta.get('effectiveFps', 0.0)
            completed_frames = meta.get('completedFrames', 0)
            deposits_per_frame = meta.get('depositsPerFrame', 0)

            # Theoretical geometric accumulation: D * (1 - p^N) / (1 - p) with p = 0.9985
            # Decay factor (1 - p) = 0.0015
            p = 0.9985
            p_n = p ** completed_frames
            geom_multiplier = (1.0 - p_n) / (1.0 - p)
            accumulated_photons = deposits_per_frame * geom_multiplier
            equilibrium_fraction = (1.0 - p_n) * 100.0 # percentage of asymptotic steady-state reached

            # Cross-correlation with Brute Force baseline at the same checkpoint
            b_key = f"brute_force_{t_str}_full"
            ssim_val = None
            psnr_val = None
            if b_key in full_images:
                b_arr = np.array(full_images[b_key], dtype=float)
                b_gray = 0.2989 * b_arr[:,:,0] + 0.5870 * b_arr[:,:,1] + 0.1140 * b_arr[:,:,2]
                ssim_val = round(compute_ssim(b_gray, gray_full), 4)
                psnr_val = round(compute_psnr(b_gray, gray_full), 2)

            metrics_by_workload[w_id]['checkpoints'][t_str] = {
                'active_elapsed_ms': round(meta.get('activeElapsedMs', 0), 1),
                'completed_frames': completed_frames,
                'presentation_fps': round(fps, 1),
                'gpu_frame_time_ms': round(gpu_ms, 2) if gpu_ms else None,
                'visible_feature_pixels_gt5': feat_pixels_gt5,
                'visible_feature_pixels_gt2': feat_pixels_gt2,
                'feature_pixel_pct': round(feat_pixel_pct, 2),
                'hard_edge_count_gt15': hard_edge_count,
                'soft_edge_count_gt5': soft_edge_count,
                'mean_edge_gradient': round(mean_edge_gradient, 3),
                'mean_filament_luminance': round(mean_filament_luminance, 2),
                'faint_envelope_luminance': round(faint_envelope_luminance, 2),
                'caustic_ridge_luminance': round(caustic_ridge_luminance, 2),
                'caustic_max_luminance': round(caustic_max_luminance, 2),
                'mean_organism_luminance': round(mean_org_luminance, 2),
                'effective_accumulated_photons': int(accumulated_photons),
                'steady_state_equilibrium_pct': round(equilibrium_fraction, 2),
                'ssim_vs_brute': ssim_val,
                'psnr_vs_brute': psnr_val
            }

    # Steady-state saturation delta analysis for 150k x 8
    # Compare growth from 10s to 20s, and 20s to 30s
    p150_10 = metrics_by_workload['prod_150k_8']['checkpoints']['10s']
    p150_20 = metrics_by_workload['prod_150k_8']['checkpoints']['20s']
    p150_30 = metrics_by_workload['prod_150k_8']['checkpoints']['30s']

    steady_state_analysis = {
        'prod_150k_growth_10_to_20s': {
            'filament_lum_delta': round(p150_20['mean_filament_luminance'] - p150_10['mean_filament_luminance'], 2),
            'envelope_lum_delta': round(p150_20['faint_envelope_luminance'] - p150_10['faint_envelope_luminance'], 2),
            'hard_edge_delta': p150_20['hard_edge_count_gt15'] - p150_10['hard_edge_count_gt15'],
            'feature_pixel_delta': p150_20['visible_feature_pixels_gt5'] - p150_10['visible_feature_pixels_gt5'],
            'equilibrium_pct_at_10s': p150_10['steady_state_equilibrium_pct'],
            'equilibrium_pct_at_20s': p150_20['steady_state_equilibrium_pct']
        },
        'prod_150k_growth_20_to_30s': {
            'filament_lum_delta': round(p150_30['mean_filament_luminance'] - p150_20['mean_filament_luminance'], 2),
            'envelope_lum_delta': round(p150_30['faint_envelope_luminance'] - p150_20['faint_envelope_luminance'], 2),
            'hard_edge_delta': p150_30['hard_edge_count_gt15'] - p150_20['hard_edge_count_gt15'],
            'feature_pixel_delta': p150_30['visible_feature_pixels_gt5'] - p150_20['visible_feature_pixels_gt5'],
            'equilibrium_pct_at_20s': p150_20['steady_state_equilibrium_pct'],
            'equilibrium_pct_at_30s': p150_30['steady_state_equilibrium_pct']
        }
    }

    final_report = {
        'audit_configuration': {
            'canvas_size': '1200x800',
            'fixed_dpr': 1.0,
            'persistence': 0.9985,
            'decay_factor_per_frame': 0.0015,
            'asymptotic_decay_multiplier': round(1.0 / 0.0015, 2),
            'morphology': 'lace',
            'symmetry': 16,
            'temporal_drift': 'frozen (t=0)'
        },
        'workload_measurements': metrics_by_workload,
        'steady_state_saturation_analysis': steady_state_analysis
    }

    report_path = os.path.join(OUT_DIR, "real_persistence_audit_report.json")
    with open(report_path, "w") as f:
        json.dump(final_report, f, indent=2)

    print(f"\n[OK] Real Production Detail Audit Report saved to {report_path}")
    return final_report

def main():
    harness_path = os.path.join(DIRECTORY, "real_persistence_audit.html")
    with open(harness_path, "w") as f:
        f.write(html_page)

    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("", PORT), AuditHandler)
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
        f"http://localhost:{PORT}/real_persistence_audit.html"
    ]

    print("[AUDIT] Launching Chrome Headless for Real Production Detail Audit Suite...")
    print("[AUDIT] Workloads: Brute Force (589k x 16), 150k x 8, 155k x 8, 160k x 8, 165k x 8")
    print("[AUDIT] Persistence strictly maintained at 0.9985 for all workloads")
    print("[AUDIT] Checkpoints: 1s, 3s, 5s, 10s, 20s, 30s active wall-clock time")
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Total active wall clock time: 5 workloads x 30s = 150s + warmup ~10s = ~160s
    # Set timeout to 300s (5 minutes)
    success = done_event.wait(timeout=300)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success:
        print("[ERROR] Real visual detail audit timed out or failed!")
        return False

    print("\n[AUDIT] All browser captures successfully received! Now computing metrics & composites...")
    process_audit_images()
    return True

if __name__ == '__main__':
    main()
