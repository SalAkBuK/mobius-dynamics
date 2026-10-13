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

PORT = 8935
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
OUT_DIR = os.path.join(DIRECTORY, "drift_aware_persistence_experiment")
os.makedirs(OUT_DIR, exist_ok=True)

done_event = threading.Event()
received_captures = {}
browser_metrics = {}

class DriftAwareHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global received_captures, browser_metrics
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
            print(f"[DRIFT-TEST] Saved {name}.png ({len(img_bytes)//1024} KB) | suite: {meta.get('suite')} | P: {meta.get('persistence')} | t: {meta.get('targetSec', meta.get('elapsedSec', 0))}s | frames: {meta.get('frames', 0)}", flush=True)
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")

        elif parsed.path == '/finish':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            browser_metrics.update(json.loads(body.decode('utf-8')))
            
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
<title>Drift-Aware Persistence Experiment Harness</title>
<style>
  html, body { margin: 0; padding: 0; width: 1200px; height: 800px; overflow: hidden; background: #010307; font-family: monospace; }
  canvas { width: 1200px; height: 800px; display: block; }
  #status { position: absolute; top: 10px; left: 10px; font-size: 13px; background: rgba(0,0,0,0.85); color: #8da4c4; padding: 8px 12px; border: 1px solid #224477; border-radius: 4px; z-index: 100; }
</style>
</head>
<body>
<div id="status">Initializing Drift-Aware Persistence Experiment Suite...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

function nextFrame() {
  return new Promise(r => requestAnimationFrame(r));
}

let activePersistence = 0.9990;

async function uploadCheckpoint(renderer, canvas, math, name, meta = {}) {
  // Synchronously draw current accumulation state to canvas default FBO
  renderer.render(math, 0.0);
  renderer.gl.finish();
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

  // CRITICAL: Request WebGL2 context with preserveDrawingBuffer: true BEFORE MobiusRenderer initialization
  const rawGl = canvas.getContext('webgl2', {
    preserveDrawingBuffer: true,
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    powerPreference: 'high-performance'
  });

  const renderer = new MobiusRenderer(canvas);
  renderer.adaptive.getDpr = () => 1.0;
  renderer.resize(1200, 800);
  renderer.zoom = 1.65;
  renderer.targetZoom = 1.65;
  renderer.viewCenter = [0.0, 0.0];
  renderer.targetViewCenter = [0.0, 0.0];
  renderer.bloomEnabled = true;
  renderer.viewMode = 0;
  renderer.setParticleCount(150000);
  renderer.setStepsOverride(8);

  const gl = renderer.gl;
  const extTimer = renderer.profiler.ext;

  // STRICT PERSISTENCE ENFORCEMENT HOOK:
  const origUniform1f = gl.uniform1f.bind(gl);
  gl.uniform1f = function(loc, val) {
    if (loc === renderer.decayUniforms.persistence) {
      return origUniform1f(loc, activePersistence);
    }
    return origUniform1f(loc, val);
  };

  const origRender = renderer.render.bind(renderer);
  renderer.render = function(m, dt, jsTime) {
    if (m) m.evolving = true; // Prevent renderer.js line 842 from forcing targetPersistence = 1.0
    this.currentPersistence = activePersistence;
    const res = origRender(m, dt, jsTime);
    this.currentPersistence = activePersistence;
    return res;
  };

  // Measure GPU frame time via WebGL2 disjoint timer queries
  async function measureGpuFrameTime(math) {
    let measuredGpuMs = null;
    if (extTimer) {
      const qTimes = [];
      for (let qf = 0; qf < 6; qf++) {
        const q = gl.createQuery();
        gl.beginQuery(extTimer.TIME_ELAPSED_EXT, q);
        renderer.render(math, 0.016);
        gl.endQuery(extTimer.TIME_ELAPSED_EXT);
        gl.flush();

        for (let poll = 0; poll < 100; poll++) {
          await new Promise(r => setTimeout(r, 4));
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
    return measuredGpuMs;
  }

  const experimentResults = {
    stationary: {},
    drift: {},
    interaction: {}
  };

  // =========================================================================
  // SUITE 1: TRULY STATIONARY STATE (Temporal Drift Frozen, t = 0)
  // Candidate B (p = 0.9990) vs Candidate C (p = 0.99925)
  // Checkpoints: 10s (600f), 20s (1200f), 30s (1800f)
  // =========================================================================
  const statRuns = [
    { id: 'stat_cand_B', label: 'Candidate B (p=0.9990 Stationary)', p: 0.9990 },
    { id: 'stat_cand_C', label: 'Candidate C (p=0.99925 Stationary)', p: 0.99925 }
  ];

  for (const run of statRuns) {
    statusEl.innerText = `[SUITE 1] Preparing Stationary Workload: ${run.label}...`;
    activePersistence = run.p;

    const math = new MathSystem();
    math.setMorphology('lace');
    math.setSymmetry(16);
    math.update(0.0, 1.65);
    math.evolving = false;
    math.update = function() {}; // Freeze temporal drift completely

    renderer.clearAccumulation();

    // Warmup 20 frames
    for (let w = 0; w < 20; w++) {
      renderer.render(math, 0.016);
      await nextFrame();
    }
    renderer.clearAccumulation();
    gl.finish();

    const measuredGpuMs = await measureGpuFrameTime(math);
    renderer.clearAccumulation();
    gl.finish();

    experimentResults.stationary[run.id] = {
      label: run.label,
      targetPersistence: run.p,
      measuredGpuMs: measuredGpuMs,
      checkpoints: {}
    };

    const checkpoints = [10, 20, 30];
    let frame = 0;

    for (const sec of checkpoints) {
      const targetFrames = sec * 60;
      while (frame < targetFrames) {
        const batch = Math.min(15, targetFrames - frame);
        for (let b = 0; b < batch; b++) {
          renderer.render(math, 0.016);
        }
        frame += batch;
        statusEl.innerText = `[SUITE 1: ${run.label}] Accumulating frame ${frame}/${targetFrames}...`;
        await nextFrame();
      }
      gl.finish();

      const meta = {
        suite: 'stationary',
        runId: run.id,
        label: run.label,
        targetSec: sec,
        frames: frame,
        persistence: run.p,
        measuredGpuMs: measuredGpuMs,
        presentationFps: 60.0
      };
      experimentResults.stationary[run.id].checkpoints[sec] = meta;
      await uploadCheckpoint(renderer, canvas, math, `${run.id}_${sec}s_full`, meta);
    }
  }

  // =========================================================================
  // SUITE 2: AUTONOMOUS DRIFT ACTIVE (math.evolving = true)
  // Comparing:
  // - Candidate B (p = 0.9990)
  // - Candidate C1 (Drift-Aware, Drift = 0.9985)
  // - Candidate C2 (Drift-Aware, Drift = 0.9990)
  // - Unmitigated Candidate C (p = 0.99925)
  // Checkpoints: 10s (600f), 20s (1200f), 30s (1800f)
  // =========================================================================
  const driftRuns = [
    { id: 'drift_cand_B', label: 'Candidate B (Drift p=0.9990)', p: 0.9990 },
    { id: 'drift_cand_C1', label: 'Candidate C1 (Drift-Aware p=0.9985)', p: 0.9985 },
    { id: 'drift_cand_C2', label: 'Candidate C2 (Drift-Aware p=0.9990)', p: 0.9990 },
    { id: 'drift_unmitigated_C', label: 'Unmitigated C (Drift p=0.99925)', p: 0.99925 }
  ];

  for (const run of driftRuns) {
    statusEl.innerText = `[SUITE 2] Preparing Autonomous Drift Workload: ${run.label}...`;
    activePersistence = run.p;

    const math = new MathSystem();
    math.setMorphology('lace');
    math.setSymmetry(16);
    math.evolving = true;
    math.time = 0.0;
    math.update(0.0, 1.65);

    renderer.clearAccumulation();

    // Warmup 20 frames at t=0
    for (let w = 0; w < 20; w++) {
      renderer.render(math, 0.016);
      await nextFrame();
    }
    renderer.clearAccumulation();
    math.time = 0.0;
    gl.finish();

    const measuredGpuMs = await measureGpuFrameTime(math);
    renderer.clearAccumulation();
    math.time = 0.0;
    gl.finish();

    experimentResults.drift[run.id] = {
      label: run.label,
      driftPersistence: run.p,
      measuredGpuMs: measuredGpuMs,
      checkpoints: {}
    };

    const checkpoints = [10, 20, 30];
    let frame = 0;

    for (const sec of checkpoints) {
      const targetFrames = sec * 60;
      while (frame < targetFrames) {
        const batch = Math.min(15, targetFrames - frame);
        for (let b = 0; b < batch; b++) {
          math.update(0.016, 1.65);
          renderer.render(math, 0.016);
        }
        frame += batch;
        statusEl.innerText = `[SUITE 2: ${run.label}] Drifting frame ${frame}/${targetFrames} (t=${(math.time).toFixed(1)}s)...`;
        await nextFrame();
      }
      gl.finish();

      const meta = {
        suite: 'drift',
        runId: run.id,
        label: run.label,
        targetSec: sec,
        frames: frame,
        simulatedSec: math.time,
        persistence: run.p,
        measuredGpuMs: measuredGpuMs,
        presentationFps: 60.0
      };
      experimentResults.drift[run.id].checkpoints[sec] = meta;
      await uploadCheckpoint(renderer, canvas, math, `${run.id}_${sec}s_full`, meta);
    }
  }

  // =========================================================================
  // SUITE 3: USER INTERACTION ACTIVE, DIMMING & POST-RELEASE RECOVERY
  // Paths:
  // 1. Candidate B: p_active = 0.93 -> ramp to 0.9990
  // 2. Candidate B (alt): p_active = 0.95 -> ramp to 0.9990
  // 3. Candidate C (C1/C2): p_active = 0.93 -> ramp to 0.99925
  // 4. Candidate C (alt): p_active = 0.95 -> ramp to 0.99925
  // =========================================================================
  const interactRuns = [
    { id: 'interact_cand_B_p93', label: 'Candidate B (Active p=0.93 -> Idle 0.9990)', pActive: 0.93, pIdle: 0.9990 },
    { id: 'interact_cand_B_p95', label: 'Candidate B (Active p=0.95 -> Idle 0.9990)', pActive: 0.95, pIdle: 0.9990 },
    { id: 'interact_cand_C_p93', label: 'Candidate C (Active p=0.93 -> Idle 0.99925)', pActive: 0.93, pIdle: 0.99925 },
    { id: 'interact_cand_C_p95', label: 'Candidate C (Active p=0.95 -> Idle 0.99925)', pActive: 0.95, pIdle: 0.99925 }
  ];

  for (const run of interactRuns) {
    statusEl.innerText = `[SUITE 3] Preparing Interaction Workload: ${run.label}...`;

    const math = new MathSystem();
    math.setMorphology('lace');
    math.setSymmetry(16);
    math.setPointer(0.0, 0.0);
    math.update(0.0, 1.65);
    math.evolving = false;
    math.update = function() {}; // static pre-accumulation

    activePersistence = run.pIdle;
    renderer.clearAccumulation();

    // 1. Pre-accumulate 15 seconds stationary (900 frames) at idle persistence
    const baseFrames = 900;
    for (let f = 0; f < baseFrames; f += 20) {
      for (let b = 0; b < 20; b++) {
        renderer.render(math, 0.016);
      }
      statusEl.innerText = `[SUITE 3: ${run.label}] Pre-accumulating baseline 15s (${f}/900 frames)...`;
      await nextFrame();
    }
    gl.finish();

    // Checkpoint 0: Pre-interaction baseline
    const metaBase = {
      suite: 'interaction',
      runId: run.id,
      label: run.label,
      phase: 'baseline_15s',
      elapsedSec: 15.0,
      frames: 900,
      persistence: run.pIdle
    };
    await uploadCheckpoint(renderer, canvas, math, `${run.id}_00_baseline`, metaBase);

    // 2. Active Interaction Phase: 1.0s (60 frames) perturbation with pActive
    statusEl.innerText = `[SUITE 3: ${run.label}] Simulating user interaction disturbance (p=${run.pActive})...`;
    activePersistence = run.pActive;
    
    // Disturbance: pointer drag to (0.75, 0.50)
    math.pointerCurrent.r = 0.75 * 0.22;
    math.pointerCurrent.i = 0.50 * 0.22;
    math.pointerTarget.r = 0.75 * 0.22;
    math.pointerTarget.i = 0.50 * 0.22;
    math.computeTransforms();

    for (let pf = 0; pf < 60; pf += 15) {
      for (let b = 0; b < 15; b++) {
        renderer.render(math, 0.016);
      }
      await nextFrame();
    }
    gl.finish();

    // Checkpoint 1: Active interaction peak dimming (immediately before release)
    const metaActive = {
      suite: 'interaction',
      runId: run.id,
      label: run.label,
      phase: 'interaction_active',
      elapsedSec: 1.0,
      frames: 60,
      persistence: run.pActive
    };
    await uploadCheckpoint(renderer, canvas, math, `${run.id}_01_active`, metaActive);

    // 3. User Release: pointer returns to (0,0), smooth exponential ramp to pIdle
    // Formula from renderer.js L847:
    // currentPersistence += (targetPersistence - currentPersistence) * Math.min(1.0, dt * 4.0)
    statusEl.innerText = `[SUITE 3: ${run.label}] Pointer released. Measuring recovery over 15s...`;
    math.pointerCurrent.r = 0.0;
    math.pointerCurrent.i = 0.0;
    math.pointerTarget.r = 0.0;
    math.pointerTarget.i = 0.0;
    math.computeTransforms();

    const postCheckpoints = [
      { sec: 1.0, targetFrame: 60, id: 'rec_1s' },
      { sec: 5.0, targetFrame: 300, id: 'rec_5s' },
      { sec: 15.0, targetFrame: 900, id: 'rec_15s' }
    ];

    let recFrame = 0;
    for (const cp of postCheckpoints) {
      while (recFrame < cp.targetFrame) {
        const batch = Math.min(15, cp.targetFrame - recFrame);
        for (let b = 0; b < batch; b++) {
          activePersistence += (run.pIdle - activePersistence) * Math.min(1.0, 0.016 * 4.0);
          renderer.render(math, 0.016);
        }
        recFrame += batch;
        statusEl.innerText = `[SUITE 3: ${run.label}] Recovery frame ${recFrame}/${cp.targetFrame} (p=${activePersistence.toFixed(5)})...`;
        await nextFrame();
      }
      gl.finish();

      const metaRec = {
        suite: 'interaction',
        runId: run.id,
        label: run.label,
        phase: cp.id,
        elapsedSec: cp.sec,
        frames: recFrame,
        currentPersistence: activePersistence,
        targetPersistence: run.pIdle
      };
      await uploadCheckpoint(renderer, canvas, math, `${run.id}_${cp.id}`, metaRec);
    }
  }

  statusEl.innerText = "All experiment workloads captured! Reporting completion to Python...";
  await fetch('/finish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(experimentResults)
  });
  statusEl.innerText = "Drift-Aware Persistence Experiment Complete!";
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
    return np.hypot(gx, gy)

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

def process_and_analyze():
    print("\n=======================================================", flush=True)
    print("PROCESSING CAPTURES, EXTRACTING CROPS & COMPUTING METRICS", flush=True)
    print("=======================================================\n", flush=True)

    CROP_FILAMENT_BOX = (750, 200, 1050, 500)    # 300x300: [200:500, 750:1050]
    CROP_ENVELOPE_BOX = (850, 80, 1150, 380)     # 300x300: [80:380, 850:1150]
    CROP_MEDIUM_BOX   = (550, 150, 950, 550)     # 400x400: [150:550, 550:950]

    all_images = {}
    filament_crops = {}
    envelope_crops = {}
    medium_crops = {}

    for name, item in received_captures.items():
        img_path = item['path']
        img = Image.open(img_path).convert('RGB')
        all_images[name] = img

        f_crop = img.crop(CROP_FILAMENT_BOX)
        f_name = f"{name}_crop_filament.png"
        f_crop.save(os.path.join(OUT_DIR, f_name))
        filament_crops[name] = f_crop

        e_crop = img.crop(CROP_ENVELOPE_BOX)
        e_name = f"{name}_crop_envelope.png"
        e_crop.save(os.path.join(OUT_DIR, e_name))
        envelope_crops[name] = e_crop

        m_crop = img.crop(CROP_MEDIUM_BOX)
        m_name = f"{name}_crop_medium.png"
        m_crop.save(os.path.join(OUT_DIR, m_name))
        medium_crops[name] = m_crop

    print(f"[OK] Generated filament, envelope, and medium crops for {len(all_images)} captures.", flush=True)

    # Load Brute Force 30s reference image for SSIM
    bf_path = os.path.join(DIRECTORY, "idle_persistence_experiment", "brute_force_30s_full.png")
    bf_img = Image.open(bf_path).convert('RGB')
    bf_arr = np.array(bf_img, dtype=float)
    bf_gray = 0.2989 * bf_arr[:,:,0] + 0.5870 * bf_arr[:,:,1] + 0.1140 * bf_arr[:,:,2]

    metrics_report = {
        'stationary': {},
        'drift': {},
        'interaction': {}
    }

    for name, img in all_images.items():
        meta = received_captures[name]['meta']
        suite = meta.get('suite', 'unknown')
        
        arr = np.array(img, dtype=float)
        gray = 0.2989 * arr[:,:,0] + 0.5870 * arr[:,:,1] + 0.1140 * arr[:,:,2]
        
        gmag = compute_gradient_mag(gray)
        hard_edges = int(np.sum(gmag > 15.0))
        soft_edges = int(np.sum(gmag > 5.0))
        mean_edge_grad = float(np.mean(gmag))

        fil_patch = gray[200:500, 750:1050]
        mean_fil_lum = float(np.mean(fil_patch))

        env_patch = gray[80:380, 850:1150]
        mean_env_lum = float(np.mean(env_patch))

        caustic_patch = gray[250:450, 550:750]
        caustic_sorted = np.sort(caustic_patch.ravel())
        top2_idx = int(0.02 * caustic_patch.size)
        caustic_ridge_lum = float(np.mean(caustic_sorted[-top2_idx:]))
        caustic_max_lum = float(np.max(caustic_patch))

        org_pixels = gray[gray > 5.0]
        mean_org_lum = float(np.mean(org_pixels)) if len(org_pixels) > 0 else 0.0

        # Void darkness in central void [350:450, 550:650]
        void_patch = gray[350:450, 550:650]
        mean_void_lum = float(np.mean(void_patch))

        ssim_val = round(compute_ssim(bf_gray, gray), 4)
        psnr_val = round(compute_psnr(bf_gray, gray), 2)

        data = {
            'image_name': name,
            'meta': meta,
            'hard_edge_count': hard_edges,
            'soft_edge_count': soft_edges,
            'mean_edge_gradient': round(mean_edge_grad, 3),
            'mean_filament_luminance': round(mean_fil_lum, 2),
            'faint_envelope_luminance': round(mean_env_lum, 2),
            'caustic_ridge_luminance': round(caustic_ridge_lum, 2),
            'caustic_max_luminance': round(caustic_max_lum, 2),
            'mean_organism_luminance': round(mean_org_lum, 2),
            'mean_void_luminance': round(mean_void_lum, 2),
            'ssim_vs_30s_brute_force': ssim_val,
            'psnr_vs_30s_brute_force': psnr_val
        }

        if suite not in metrics_report:
            metrics_report[suite] = {}
        metrics_report[suite][name] = data

    # Save metrics report JSON
    json_path = os.path.join(OUT_DIR, "drift_aware_experiment_report.json")
    with open(json_path, "w") as f:
        json.dump(metrics_report, f, indent=2)
    print(f"[OK] Master metrics JSON written to {json_path}", flush=True)

    # =========================================================================
    # GENERATE COMPOSITE COMPARISON PANELS
    # =========================================================================
    try:
        font_large = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)
        font_med   = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 14)
        font_small = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 12)
        font_tiny  = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 10)
    except:
        font_large = ImageFont.load_default()
        font_med   = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny  = ImageFont.load_default()

    # -------------------------------------------------------------------------
    # PANEL 1: TRULY STATIONARY COMPARISON (10s, 20s, 30s)
    # Candidate B (p=0.9990) vs Candidate C (p=0.99925)
    # -------------------------------------------------------------------------
    times = [10, 20, 30]
    row_h = 360
    p1_h = 70 + len(times) * row_h
    panel1 = Image.new('RGB', (1850, p1_h), color=(1, 3, 7))
    d1 = ImageDraw.Draw(panel1)
    d1.rectangle([0, 0, 1850, 60], fill=(8, 18, 36))
    d1.text((25, 18), "PANEL 1: TRULY STATIONARY COMPARISON — CANDIDATE B (p=0.9990) VS CANDIDATE C (p=0.99925)", fill=(240, 215, 110), font=font_large)

    for r_idx, t_sec in enumerate(times):
        y_top = 70 + r_idx * row_h
        d1.rectangle([0, y_top - 5, 1850, y_top + 18], fill=(4, 10, 20))
        d1.text((25, y_top - 2), f"EXPOSURE DURATION: {t_sec} SECONDS IDLE ACCUMULATION", fill=(100, 200, 255), font=font_med)

        # Candidate B
        b_key = f"stat_cand_B_{t_sec}s_full"
        if b_key in all_images:
            b_full = all_images[b_key].resize((450, 300), Image.Resampling.LANCZOS)
            b_fil = filament_crops[b_key]
            b_env = envelope_crops[b_key]
            panel1.paste(b_full, (25, y_top + 25))
            panel1.paste(b_fil, (490, y_top + 25))
            panel1.paste(b_env, (800, y_top + 25))
            
            m_b = metrics_report['stationary'].get(b_key, {})
            lbl_b = f"Candidate B (p=0.9990) @ {t_sec}s | HardEdges: {m_b.get('hard_edge_count')} | FilLum: {m_b.get('mean_filament_luminance')} | EnvLum: {m_b.get('faint_envelope_luminance')} | SSIM: {m_b.get('ssim_vs_30s_brute_force')}"
            d1.text((25, y_top + 330), lbl_b, fill=(170, 210, 250), font=font_tiny)

        # Candidate C
        c_key = f"stat_cand_C_{t_sec}s_full"
        if c_key in all_images:
            c_full = all_images[c_key].resize((450, 300), Image.Resampling.LANCZOS)
            c_fil = filament_crops[c_key]
            c_env = envelope_crops[c_key]
            panel1.paste(c_full, (950, y_top + 25))
            panel1.paste(c_fil, (1415, y_top + 25))
            panel1.paste(c_env, (1725, y_top + 25))

            m_c = metrics_report['stationary'].get(c_key, {})
            lbl_c = f"Candidate C (p=0.99925) @ {t_sec}s | HardEdges: {m_c.get('hard_edge_count')} | FilLum: {m_c.get('mean_filament_luminance')} | EnvLum: {m_c.get('faint_envelope_luminance')} | SSIM: {m_c.get('ssim_vs_30s_brute_force')}"
            d1.text((950, y_top + 330), lbl_c, fill=(170, 250, 210), font=font_tiny)

    p1_path = os.path.join(OUT_DIR, "panel_1_stationary_comparison_10s_20s_30s.png")
    panel1.save(p1_path)
    print(f"[OK] Saved {p1_path}", flush=True)

    # -------------------------------------------------------------------------
    # PANEL 2: AUTONOMOUS DRIFT COMPARISON
    # Comparing Candidate B (0.9990) vs C1 (0.9985) vs C2 (0.9990) vs Unmitigated C (0.99925)
    # -------------------------------------------------------------------------
    drift_cands = [
        ('drift_cand_B', 'Candidate B (p=0.9990 Fixed)', (180, 210, 255)),
        ('drift_cand_C1', 'Candidate C1 (Drift p=0.9985)', (140, 230, 255)),
        ('drift_cand_C2', 'Candidate C2 (Drift p=0.9990)', (140, 255, 190)),
        ('drift_unmitigated_C', 'Unmitigated C (Drift p=0.99925)', (255, 170, 160))
    ]
    p2_w = 2100
    p2_row_h = 340
    p2_h = 70 + len(times) * p2_row_h
    panel2 = Image.new('RGB', (p2_w, p2_h), color=(1, 3, 7))
    d2 = ImageDraw.Draw(panel2)
    d2.rectangle([0, 0, p2_w, 60], fill=(8, 18, 36))
    d2.text((25, 18), "PANEL 2: AUTONOMOUS DRIFT IN PROGRESS — MOTION HAZE & BLUR COMPARISON ACROSS PERSISTENCE RULES", fill=(240, 215, 110), font=font_large)

    for r_idx, t_sec in enumerate(times):
        y_top = 70 + r_idx * p2_row_h
        d2.rectangle([0, y_top - 5, p2_w, y_top + 18], fill=(4, 10, 20))
        d2.text((25, y_top - 2), f"AUTONOMOUS DRIFT DURATION: {t_sec} SECONDS CONTINUOUS TEMPORAL EVOLUTION", fill=(100, 200, 255), font=font_med)

        for c_idx, (cid, clbl, ccolor) in enumerate(drift_cands):
            x_col = 25 + c_idx * 515
            key = f"{cid}_{t_sec}s_full"
            if key in all_images:
                f_img = all_images[key].resize((300, 200), Image.Resampling.LANCZOS)
                c_fil = filament_crops[key].resize((200, 200), Image.Resampling.LANCZOS)
                
                panel2.paste(f_img, (x_col, y_top + 25))
                panel2.paste(c_fil, (x_col + 305, y_top + 25))

                m_d = metrics_report['drift'].get(key, {})
                d2.text((x_col, y_top + 232), clbl, fill=ccolor, font=font_small)
                txt_m1 = f"Hard Edges: {m_d.get('hard_edge_count')} | Soft Edges: {m_d.get('soft_edge_count')}"
                txt_m2 = f"Filament Lum: {m_d.get('mean_filament_luminance')} | Void Haze: {m_d.get('mean_void_luminance')}"
                txt_m3 = f"Mean Edge Grad: {m_d.get('mean_edge_gradient')} | SSIM: {m_d.get('ssim_vs_30s_brute_force')}"
                d2.text((x_col, y_top + 250), txt_m1, fill=(160, 190, 220), font=font_tiny)
                d2.text((x_col, y_top + 266), txt_m2, fill=(160, 190, 220), font=font_tiny)
                d2.text((x_col, y_top + 282), txt_m3, fill=(160, 190, 220), font=font_tiny)

    p2_path = os.path.join(OUT_DIR, "panel_2_autonomous_drift_comparison.png")
    panel2.save(p2_path)
    print(f"[OK] Saved {p2_path}", flush=True)

    # -------------------------------------------------------------------------
    # PANELS 3, 4, 5, 6: INTERACTION DIMMING & RECOVERY (0s, 1s, 5s, 15s)
    # -------------------------------------------------------------------------
    int_cases = [
        ('interact_cand_B_p93', 'Candidate B: Active p=0.93 -> Idle 0.9990'),
        ('interact_cand_B_p95', 'Candidate B: Active p=0.95 -> Idle 0.9990'),
        ('interact_cand_C_p93', 'Candidate C: Active p=0.93 -> Idle 0.99925'),
        ('interact_cand_C_p95', 'Candidate C: Active p=0.95 -> Idle 0.99925')
    ]

    recovery_phases = [
        ('01_active', 'panel_3_interaction_dimming_immediate.png', 'PANEL 3: INTERACTION DIMMING LEVEL (DURING ACTIVE DRAG / 0s RELEASE)', 'Active Interaction State (End of 1.0s Perturbation)'),
        ('rec_1s', 'panel_4_recovery_1s_post_release.png', 'PANEL 4: POST-INTERACTION RECOVERY @ 1.0 SECOND (60 FRAMES POST-RELEASE)', 'Recovery @ 1.0s Post-Release (Ramp Progression)'),
        ('rec_5s', 'panel_5_recovery_5s_post_release.png', 'PANEL 5: POST-INTERACTION RECOVERY @ 5.0 SECONDS (300 FRAMES POST-RELEASE)', 'Recovery @ 5.0s Post-Release (Re-accumulation)'),
        ('rec_15s', 'panel_6_recovery_15s_post_release.png', 'PANEL 6: POST-INTERACTION RECOVERY @ 15.0 SECONDS (DEEP IDLE EQUILIBRIUM)', 'Recovery @ 15.0s Post-Release (Full Photographic Restoration)')
    ]

    for phase_key, panel_filename, panel_title, phase_desc in recovery_phases:
        pan_w = 2100
        pan_h = 440
        pan_img = Image.new('RGB', (pan_w, pan_h), color=(1, 3, 7))
        d_pan = ImageDraw.Draw(pan_img)
        d_pan.rectangle([0, 0, pan_w, 60], fill=(8, 18, 36))
        d_pan.text((25, 18), panel_title, fill=(240, 215, 110), font=font_large)

        d_pan.rectangle([0, 65, pan_w, 90], fill=(4, 10, 20))
        d_pan.text((25, 70), phase_desc, fill=(100, 200, 255), font=font_med)

        for c_idx, (cid, clbl) in enumerate(int_cases):
            x_col = 25 + c_idx * 515
            key = f"{cid}_{phase_key}"
            base_key = f"{cid}_00_baseline"

            if key in all_images:
                f_img = all_images[key].resize((300, 200), Image.Resampling.LANCZOS)
                c_fil = filament_crops[key].resize((200, 200), Image.Resampling.LANCZOS)
                
                pan_img.paste(f_img, (x_col, 100))
                pan_img.paste(c_fil, (x_col + 305, 100))

                m_cur = metrics_report['interaction'].get(key, {})
                m_base = metrics_report['interaction'].get(base_key, {})
                
                cur_lum = m_cur.get('mean_organism_luminance', 0.0)
                base_lum = m_base.get('mean_organism_luminance', 1.0)
                dim_dip_pct = round((1.0 - cur_lum / max(0.1, base_lum)) * 100.0, 1)

                d_pan.text((x_col, 310), clbl, fill=(200, 230, 255), font=font_small)
                t1 = f"Org Lum: {cur_lum} (Baseline: {base_lum}) | Dim Dip: {dim_dip_pct}%"
                t2 = f"Filament Lum: {m_cur.get('mean_filament_luminance')} | Caustic Ridge: {m_cur.get('caustic_ridge_luminance')}"
                t3 = f"Hard Edges: {m_cur.get('hard_edge_count')} | Soft Edges: {m_cur.get('soft_edge_count')}"
                t4 = f"P(t): {m_cur.get('meta', {}).get('currentPersistence', m_cur.get('meta', {}).get('persistence'))}"
                d_pan.text((x_col, 332), t1, fill=(255, 210, 130) if dim_dip_pct > 30 else (160, 220, 180), font=font_tiny)
                d_pan.text((x_col, 350), t2, fill=(160, 190, 220), font=font_tiny)
                d_pan.text((x_col, 368), t3, fill=(160, 190, 220), font=font_tiny)
                d_pan.text((x_col, 386), t4, fill=(140, 170, 200), font=font_tiny)

        out_pan_path = os.path.join(OUT_DIR, panel_filename)
        pan_img.save(out_pan_path)
        print(f"[OK] Saved {out_pan_path}", flush=True)

    print("\n=======================================================", flush=True)
    print("ALL EXPERIMENT CAPTURES, CROPS, PANELS & METRICS COMPLETE!", flush=True)
    print("=======================================================\n", flush=True)

def main():
    harness_path = os.path.join(DIRECTORY, "drift_aware_test.html")
    with open(harness_path, "w", encoding='utf-8') as f:
        f.write(html_page)

    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("", PORT), DriftAwareHandler)
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
        "--disable-frame-rate-limit",
        "--disable-gpu-vsync",
        "--window-size=1200,800",
        f"http://localhost:{PORT}/drift_aware_test.html"
    ]

    print(f"[DRIFT-TEST] Launching Chrome Headless on port {PORT}...", flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    success = done_event.wait(timeout=600)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success:
        print("[ERROR] Experiment timed out or failed!", flush=True)
        return False

    print("\n[DRIFT-TEST] All checkpoints received successfully! Beginning post-processing...", flush=True)
    process_and_analyze()
    return True

if __name__ == '__main__':
    main()
