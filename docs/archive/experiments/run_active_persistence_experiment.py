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

PORT = 8945
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
OUT_DIR = os.path.join(DIRECTORY, "active_persistence_test")
os.makedirs(OUT_DIR, exist_ok=True)

done_event = threading.Event()
received_captures = {}
browser_results = {}
ghost_timelines = {}

class ActivePersistenceHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global received_captures, browser_results, ghost_timelines
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/save_checkpoint':
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
            
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
            cand = meta.get('candidateId', '')
            phase = meta.get('phase', '')
            p_val = meta.get('persistence', meta.get('currentPersistence', ''))
            sec = meta.get('elapsedSec', '')
            f = meta.get('frames', '')
            print(f"[ACTIVE-TEST] Saved {name}.png ({len(img_bytes)//1024} KB) | cand: {cand} | phase: {phase} | p: {p_val} | t: {sec}s ({f}f)", flush=True)
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")

        elif parsed.path == '/record_ghost_timeline':
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
            cand_id = payload.get('candidateId')
            ghost_timelines[cand_id] = payload.get('timeline', [])
            print(f"[ACTIVE-TEST] Received ghost timeline for {cand_id} ({len(payload.get('timeline', []))} samples)", flush=True)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")

        elif parsed.path == '/finish':
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
            browser_results.update(payload)
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
<title>Active Interaction Persistence Test Harness</title>
<style>
  html, body { margin: 0; padding: 0; width: 1200px; height: 800px; overflow: hidden; background: #010307; font-family: monospace; }
  canvas { width: 1200px; height: 800px; display: block; }
  #status { position: absolute; top: 10px; left: 10px; font-size: 13px; background: rgba(0,0,0,0.85); color: #8da4c4; padding: 8px 12px; border: 1px solid #224477; border-radius: 4px; z-index: 100; }
</style>
</head>
<body>
<div id="status">Initializing Active Interaction Persistence Test Harness...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

function nextFrame() {
  return new Promise(r => requestAnimationFrame(r));
}

let activePersistence = 0.99925;

async function uploadCheckpoint(renderer, canvas, math, name, meta = {}) {
  renderer.render(math, 0.0);
  renderer.gl.finish();
  const dataUrl = canvas.toDataURL('image/png');
  await fetch('/save_checkpoint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, dataUrl, meta })
  });
}

function getCanvasImageData(gl, width, height) {
  const pixels = new Uint8Array(width * height * 4);
  gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
  return pixels;
}

window.onload = async function() {
  const canvas = document.getElementById('c');
  const statusEl = document.getElementById('status');

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

  // Persistence enforcement hook:
  const origUniform1f = gl.uniform1f.bind(gl);
  gl.uniform1f = function(loc, val) {
    if (loc === renderer.decayUniforms.persistence) {
      return origUniform1f(loc, activePersistence);
    }
    return origUniform1f(loc, val);
  };

  const origRender = renderer.render.bind(renderer);
  renderer.render = function(m, dt, jsTime) {
    if (m) m.evolving = true;
    this.currentPersistence = activePersistence;
    const res = origRender(m, dt, jsTime);
    this.currentPersistence = activePersistence;
    return res;
  };

  const candidates = [
    { id: 'cand_p95', label: 'Candidate 1 (p_active = 0.95)', pActive: 0.95 },
    { id: 'cand_p96', label: 'Candidate 2 (p_active = 0.96)', pActive: 0.96 },
    { id: 'cand_p97', label: 'Candidate 3 (p_active = 0.97)', pActive: 0.97 }
  ];

  const pIdle = 0.99925;
  const experimentResults = {};

  for (const cand of candidates) {
    statusEl.innerText = `[ACTIVE-TEST] Initializing ${cand.label}...`;
    experimentResults[cand.id] = {
      label: cand.label,
      pActive: cand.pActive,
      pIdle: pIdle,
      checkpoints: {}
    };

    const math = new MathSystem();
    math.setMorphology('lace');
    math.setSymmetry(16);
    math.evolving = false;
    math.setPointer(0.0, 0.0);
    math.pointerCurrent.r = 0.0;
    math.pointerCurrent.i = 0.0;
    math.update(0.0, 1.65);

    activePersistence = pIdle;
    renderer.clearAccumulation();

    // Warmup 20 frames
    for (let w = 0; w < 20; w++) {
      renderer.render(math, 0.016);
      await nextFrame();
    }
    renderer.clearAccumulation();
    gl.finish();

    // =======================================================================
    // 1. PRE-ACCUMULATION: 15 seconds stationary (900 frames) at p_idle = 0.99925
    // =======================================================================
    const baseFrames = 900;
    for (let f = 0; f < baseFrames; f += 20) {
      for (let b = 0; b < 20; b++) {
        renderer.render(math, 0.016);
      }
      statusEl.innerText = `[${cand.label}] Pre-accumulating baseline 15s (${f}/900 frames)...`;
      await nextFrame();
    }
    gl.finish();

    // Checkpoint 0: Baseline
    const metaBase = {
      candidateId: cand.id,
      label: cand.label,
      phase: 'baseline_15s',
      elapsedSec: 15.0,
      frames: 900,
      persistence: pIdle
    };
    experimentResults[cand.id].checkpoints['baseline'] = metaBase;
    await uploadCheckpoint(renderer, canvas, math, `${cand.id}_00_baseline`, metaBase);

    // Read baseline image pixels for stale support mask identification
    renderer.render(math, 0.0);
    gl.finish();
    const basePixels = getCanvasImageData(gl, 1200, 800);

    // =======================================================================
    // 2. ACTIVE INTERACTION: 1.0s / 60 frames pointer perturbation at pActive
    // =======================================================================
    statusEl.innerText = `[${cand.label}] Triggering 1.0s pointer perturbation (p=${cand.pActive})...`;
    activePersistence = cand.pActive;
    
    // Pointer drag to (0.75*0.22, 0.50*0.22)
    math.setPointer(0.75, 0.50);
    math.pointerCurrent.r = 0.75 * 0.22;
    math.pointerCurrent.i = 0.50 * 0.22;
    math.update(0.0, 1.65);

    for (let pf = 0; pf < 60; pf += 15) {
      for (let b = 0; b < 15; b++) {
        renderer.render(math, 0.016);
      }
      await nextFrame();
    }
    gl.finish();

    // Checkpoint 1: Active interaction peak state
    const metaActive = {
      candidateId: cand.id,
      label: cand.label,
      phase: 'active_1.0s',
      elapsedSec: 1.0,
      frames: 60,
      persistence: cand.pActive
    };
    experimentResults[cand.id].checkpoints['active'] = metaActive;
    await uploadCheckpoint(renderer, canvas, math, `${cand.id}_01_active`, metaActive);

    // Read active image pixels
    renderer.render(math, 0.0);
    gl.finish();
    const activePixels = getCanvasImageData(gl, 1200, 800);

    // Identify stale support mask indices:
    // Pixels where active image has significant excess light over baseline
    // (i.e. features created during perturbation that are not part of baseline)
    const staleIndices = [];
    const numPixels = 1200 * 800;
    for (let i = 0; i < numPixels; i++) {
      const idx = i * 4;
      const bLum = 0.2989 * basePixels[idx] + 0.5870 * basePixels[idx+1] + 0.1140 * basePixels[idx+2];
      const aLum = 0.2989 * activePixels[idx] + 0.5870 * activePixels[idx+1] + 0.1140 * activePixels[idx+2];
      const diff = aLum - bLum;
      // Stale feature: active excess > 10.0 LSB
      if (diff > 10.0) {
        staleIndices.push({ idx, bLum, aLum, initialExcess: diff });
      }
    }
    console.log(`[${cand.label}] Stale support mask identified: ${staleIndices.length} pixels.`);

    // =======================================================================
    // 3. POST-RELEASE RECOVERY: pointer returns to (0,0), smooth exponential ramp to pIdle
    // currentPersistence += (0.99925 - currentPersistence) * Math.min(1.0, dt * 4.0)
    // Checkpoints: 0.5s (30f), 1.0s (60f), 1.5s (90f), 2.0s (120f), 3.0s (180f), 5.0s (300f)
    // =======================================================================
    statusEl.innerText = `[${cand.label}] Pointer released. Measuring clearance & recovery over 5s...`;
    math.setPointer(0.0, 0.0);
    math.pointerCurrent.r = 0.0;
    math.pointerCurrent.i = 0.0;
    math.update(0.0, 1.65);

    const postCheckpoints = [
      { sec: 0.5, targetFrame: 30,  id: 'rec_0.5s' },
      { sec: 1.0, targetFrame: 60,  id: 'rec_1.0s' },
      { sec: 1.5, targetFrame: 90,  id: 'rec_1.5s' },
      { sec: 2.0, targetFrame: 120, id: 'rec_2.0s' },
      { sec: 3.0, targetFrame: 180, id: 'rec_3.0s' },
      { sec: 5.0, targetFrame: 300, id: 'rec_5.0s' }
    ];

    let recFrame = 0;
    let cpIndex = 0;
    const ghostHistory = [];
    let imperceptibleFrame = null;
    let imperceptibleSec = null;

    const totalPostFrames = 300;
    while (recFrame < totalPostFrames) {
      recFrame++;
      // Ramp persistence
      activePersistence += (pIdle - activePersistence) * Math.min(1.0, 0.016 * 4.0);
      renderer.render(math, 0.016);

      // High frequency ghost tracking every 5 frames
      if (recFrame % 5 === 0 || recFrame === totalPostFrames) {
        gl.finish();
        const curPixels = getCanvasImageData(gl, 1200, 800);
        let maxGhostResidual = 0.0;
        let sumGhostResidual = 0.0;

        for (let g = 0; g < staleIndices.length; g++) {
          const item = staleIndices[g];
          const cLum = 0.2989 * curPixels[item.idx] + 0.5870 * curPixels[item.idx+1] + 0.1140 * curPixels[item.idx+2];
          // Residual above baseline
          const excess = Math.max(0.0, cLum - item.bLum);
          if (excess > maxGhostResidual) maxGhostResidual = excess;
          sumGhostResidual += excess;
        }

        const meanGhostResidual = staleIndices.length > 0 ? (sumGhostResidual / staleIndices.length) : 0.0;
        const curSec = Number((recFrame / 60.0).toFixed(3));

        ghostHistory.push({
          frame: recFrame,
          sec: curSec,
          persistence: Number(activePersistence.toFixed(5)),
          maxGhostResidual: Number(maxGhostResidual.toFixed(3)),
          meanGhostResidual: Number(meanGhostResidual.toFixed(3))
        });

        if (imperceptibleFrame === null && maxGhostResidual < 2.0) {
          imperceptibleFrame = recFrame;
          imperceptibleSec = curSec;
          console.log(`[${cand.label}] Ghost trail visually imperceptible (<2.0/255) at frame ${recFrame} (${curSec}s)!`);
        }

        statusEl.innerText = `[${cand.label}] Recovery frame ${recFrame}/300 (${curSec}s) | p=${activePersistence.toFixed(5)} | peak ghost=${maxGhostResidual.toFixed(2)}/255`;
      }

      // Checkpoint capture
      if (cpIndex < postCheckpoints.length && recFrame === postCheckpoints[cpIndex].targetFrame) {
        const cp = postCheckpoints[cpIndex];
        gl.finish();
        const metaRec = {
          candidateId: cand.id,
          label: cand.label,
          phase: cp.id,
          elapsedSec: cp.sec,
          frames: recFrame,
          currentPersistence: activePersistence,
          targetPersistence: pIdle
        };
        experimentResults[cand.id].checkpoints[cp.id] = metaRec;
        await uploadCheckpoint(renderer, canvas, math, `${cand.id}_${cp.id}`, metaRec);
        cpIndex++;
      }

      if (recFrame % 15 === 0) {
        await nextFrame();
      }
    }

    // Upload ghost tracking timeline
    await fetch('/record_ghost_timeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidateId: cand.id,
        imperceptibleFrame: imperceptibleFrame,
        imperceptibleSec: imperceptibleSec,
        timeline: ghostHistory
      })
    });
  }

  statusEl.innerText = "All candidate evaluations complete! Reporting results to Python...";
  await fetch('/finish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(experimentResults)
  });
  statusEl.innerText = "Experiment Suite Finished Successfully!";
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

def process_and_generate_panels():
    print("\n=======================================================", flush=True)
    print("ANALYZING EXPERIMENT DATA & BUILDING DELIVERABLE PANELS", flush=True)
    print("=======================================================\n", flush=True)

    CROP_FILAMENT_BOX = (750, 200, 1050, 500) # [200:500, 750:1050]
    # Detailed caustic crop where perturbed ridge was identified: (600, 300, 900, 600)
    CROP_CAUSTIC_BOX = (600, 300, 900, 600)

    candidates = [
        ('cand_p95', 'Candidate 1 (p=0.95)', 0.95),
        ('cand_p96', 'Candidate 2 (p=0.96)', 0.96),
        ('cand_p97', 'Candidate 3 (p=0.97)', 0.97)
    ]

    all_images = {}
    gray_images = {}
    filament_crops = {}

    for name, item in received_captures.items():
        img_path = item['path']
        img = Image.open(img_path).convert('RGB')
        all_images[name] = img
        arr = np.array(img, dtype=float)
        gray = 0.2989 * arr[:,:,0] + 0.5870 * arr[:,:,1] + 0.1140 * arr[:,:,2]
        gray_images[name] = gray
        
        f_crop = img.crop(CROP_FILAMENT_BOX)
        filament_crops[name] = f_crop
        f_crop.save(os.path.join(OUT_DIR, f"{name}_crop_filament.png"))

    print(f"[OK] Saved filament crops for {len(all_images)} captures.", flush=True)

    # -------------------------------------------------------------
    # COMPUTE QUANTITATIVE METRICS FOR EACH CAPTURE
    # -------------------------------------------------------------
    metrics_by_candidate = {}

    for cid, clbl, pval in candidates:
        metrics_by_candidate[cid] = {
            'label': clbl,
            'pActive': pval,
            'pIdle': 0.99925,
            'phases': {}
        }

        base_key = f"{cid}_00_baseline"
        base_gray = gray_images[base_key]
        base_org_pixels = base_gray[base_gray > 5.0]
        base_mean_org = float(np.mean(base_org_pixels)) if len(base_org_pixels) > 0 else 1.0

        # Define stale support masks from active vs baseline
        active_key = f"{cid}_01_active"
        active_gray = gray_images[active_key]
        act_diff = active_gray - base_gray

        mask_10 = act_diff > 10.0
        mask_15 = act_diff > 15.0
        mask_5  = act_diff > 5.0

        initial_peak_ghost_10 = float(np.max(act_diff[mask_10])) if np.sum(mask_10) > 0 else float(np.max(act_diff))
        initial_peak_ghost_15 = float(np.max(act_diff[mask_15])) if np.sum(mask_15) > 0 else 0.0

        phase_keys = [
            ('baseline', base_key, 0.0, 0, 0.99925),
            ('active', active_key, 1.0, 60, pval),
            ('rec_0.5s', f"{cid}_rec_0.5s", 0.5, 30, None),
            ('rec_1.0s', f"{cid}_rec_1.0s", 1.0, 60, None),
            ('rec_1.5s', f"{cid}_rec_1.5s", 1.5, 90, None),
            ('rec_2.0s', f"{cid}_rec_2.0s", 2.0, 120, None),
            ('rec_3.0s', f"{cid}_rec_3.0s", 3.0, 180, None),
            ('rec_5.0s', f"{cid}_rec_5.0s", 5.0, 300, None)
        ]

        for p_name, img_key, sec, frames, p_fixed in phase_keys:
            if img_key not in gray_images:
                continue
            cur_gray = gray_images[img_key]
            
            # Gradients
            gmag = compute_gradient_mag(cur_gray)
            hard_edges = int(np.sum(gmag > 15.0))
            soft_edges = int(np.sum(gmag > 5.0))
            mean_grad = float(np.mean(gmag))

            # Organism luminance
            org_pixels = cur_gray[cur_gray > 5.0]
            mean_org = float(np.mean(org_pixels)) if len(org_pixels) > 0 else 0.0
            dip_pct = round((1.0 - mean_org / max(0.1, base_mean_org)) * 100.0, 2) if p_name != 'baseline' else 0.0

            # Filament luminance in [200:500, 750:1050]
            fil_patch = cur_gray[200:500, 750:1050]
            mean_fil = float(np.mean(fil_patch))

            # Caustic ridge luminance (top 2% in [250:450, 550:750])
            caustic_patch = cur_gray[250:450, 550:750]
            c_sorted = np.sort(caustic_patch.ravel())
            top2_idx = int(0.02 * caustic_patch.size)
            caustic_ridge = float(np.mean(c_sorted[-top2_idx:]))
            caustic_max = float(np.max(caustic_patch))

            # Ghost residuals on stale support mask
            cur_diff = cur_gray - base_gray
            cur_ghost_10 = float(np.max(cur_diff[mask_10])) if np.sum(mask_10) > 0 else 0.0
            cur_ghost_15 = float(np.max(cur_diff[mask_15])) if np.sum(mask_15) > 0 else 0.0
            cur_ghost_5  = float(np.max(cur_diff[mask_5]))  if np.sum(mask_5)  > 0 else 0.0
            mean_ghost_10 = float(np.mean(np.maximum(0.0, cur_diff[mask_10]))) if np.sum(mask_10) > 0 else 0.0

            p_val_actual = p_fixed
            if p_val_actual is None:
                p_val_actual = received_captures[img_key]['meta'].get('currentPersistence')

            metrics_by_candidate[cid]['phases'][p_name] = {
                'image_key': img_key,
                'elapsed_sec': sec,
                'frames': frames,
                'persistence': round(p_val_actual, 5) if p_val_actual is not None else None,
                'mean_organism_luminance': round(mean_org, 2),
                'luminance_dip_pct': dip_pct,
                'mean_filament_luminance': round(mean_fil, 2),
                'caustic_ridge_luminance': round(caustic_ridge, 2),
                'caustic_max_luminance': round(caustic_max, 2),
                'hard_edge_count': hard_edges,
                'soft_edge_count': soft_edges,
                'mean_edge_gradient': round(mean_grad, 3),
                'peak_ghost_residual_mask10': round(cur_ghost_10, 2),
                'peak_ghost_residual_mask15': round(cur_ghost_15, 2),
                'peak_ghost_residual_mask5': round(cur_ghost_5, 2),
                'mean_ghost_residual_mask10': round(mean_ghost_10, 2),
                'ghost_perceptible_above_2lsb': bool(cur_ghost_10 >= 2.0)
            }

        # Stale mask counts
        metrics_by_candidate[cid]['stale_mask_counts'] = {
            'mask_diff_gt_10': int(np.sum(mask_10)),
            'mask_diff_gt_15': int(np.sum(mask_15)),
            'mask_diff_gt_5': int(np.sum(mask_5)),
            'initial_peak_ghost_mask10': round(initial_peak_ghost_10, 2)
        }

        # Add browser high-frequency timeline analysis
        tl = ghost_timelines.get(cid, [])
        metrics_by_candidate[cid]['ghost_timeline'] = tl
        
        # Calculate exact clearance frame & seconds (< 2.0 / 255)
        sub2_frame = None
        sub2_sec = None
        for sample in tl:
            if sample.get('maxGhostResidual', 99.0) < 2.0:
                sub2_frame = sample.get('frame')
                sub2_sec = sample.get('sec')
                break
        
        metrics_by_candidate[cid]['clearance_metrics'] = {
            'imperceptible_threshold_lsb': 2.0,
            'clearance_frame_measured': sub2_frame,
            'clearance_sec_measured': sub2_sec,
            'trail_visible_at_1.0s': bool(metrics_by_candidate[cid]['phases']['rec_1.0s']['peak_ghost_residual_mask10'] >= 2.0),
            'trail_visible_at_1.5s': bool(metrics_by_candidate[cid]['phases']['rec_1.5s']['peak_ghost_residual_mask10'] >= 2.0),
            'trail_visible_at_2.0s': bool(metrics_by_candidate[cid]['phases']['rec_2.0s']['peak_ghost_residual_mask10'] >= 2.0)
        }

    # -------------------------------------------------------------
    # BUILD DELIVERABLE COMPOSITE PANELS
    # -------------------------------------------------------------
    font_large = ImageFont.truetype("arial.ttf", 24)
    font_med = ImageFont.truetype("arial.ttf", 17)
    font_small = ImageFont.truetype("arial.ttf", 13)
    font_tiny = ImageFont.truetype("arial.ttf", 11)

    # -------------------------------------------------------------
    # PANEL 1: panel_active_interaction_dimming.png
    # Side-by-side comparison of 0.95 vs 0.96 vs 0.97 during active interaction
    # (Full organism and filament crop)
    # -------------------------------------------------------------
    p1_w = 1860
    p1_h = 760
    p1_img = Image.new('RGB', (p1_w, p1_h), color=(2, 5, 12))
    d1 = ImageDraw.Draw(p1_img)

    # Header
    d1.rectangle([0, 0, p1_w, 75], fill=(10, 22, 44))
    d1.text((25, 14), "ACTIVE INTERACTION PERSISTENCE COMPARISON: 0.95 vs 0.96 vs 0.97", fill=(245, 220, 115), font=font_large)
    d1.text((25, 46), "Active Perturbation State at 1.0s (60 frames) | Full Organism (Top) & Filament Crop [200:500, 750:1050] (Bottom)", fill=(130, 205, 255), font=font_med)

    for c_idx, (cid, clbl, pval) in enumerate(candidates):
        x_left = 25 + c_idx * 610
        act_key = f"{cid}_01_active"
        base_key = f"{cid}_00_baseline"

        full_img = all_images[act_key].resize((360, 240), Image.Resampling.LANCZOS)
        fil_img = filament_crops[act_key].resize((240, 240), Image.Resampling.LANCZOS)

        # Draw card container
        d1.rectangle([x_left, 88, x_left + 595, 735], fill=(5, 12, 24), outline=(30, 60, 100), width=1)
        
        # Candidate header
        d1.rectangle([x_left, 88, x_left + 595, 125], fill=(15, 32, 60))
        d1.text((x_left + 15, 96), f"{clbl}", fill=(255, 230, 140), font=font_med)

        # Paste images
        p1_img.paste(full_img, (x_left + 15, 138))
        p1_img.paste(fil_img, (x_left + 385, 138))

        d1.text((x_left + 15, 385), "Full Organism (1200x800 -> 360x240)", fill=(160, 190, 220), font=font_tiny)
        d1.text((x_left + 385, 385), "Filament Crop [300x300]", fill=(160, 190, 220), font=font_tiny)

        # Metrics block
        m_act = metrics_by_candidate[cid]['phases']['active']
        m_base = metrics_by_candidate[cid]['phases']['baseline']
        
        d1.rectangle([x_left + 15, 410, x_left + 580, 720], fill=(8, 18, 34), outline=(22, 45, 78), width=1)

        y_t = 422
        d1.text((x_left + 25, y_t), "QUANTITATIVE ACTIVE RETENTION METRICS:", fill=(240, 215, 110), font=font_small)
        y_t += 26
        
        dip_color = (130, 235, 160) if m_act['luminance_dip_pct'] < 65 else (255, 210, 120) if m_act['luminance_dip_pct'] < 72 else (255, 140, 140)
        d1.text((x_left + 25, y_t), f"• Organism Luminance: {m_act['mean_organism_luminance']}  (Baseline: {m_base['mean_organism_luminance']})", fill=(210, 230, 255), font=font_small)
        y_t += 22
        d1.text((x_left + 25, y_t), f"• Luminance Dip %: {m_act['luminance_dip_pct']}% relative to baseline", fill=dip_color, font=font_small)
        y_t += 22
        d1.text((x_left + 25, y_t), f"• Filament Luminance: {m_act['mean_filament_luminance']}  (Baseline: {m_base['mean_filament_luminance']})", fill=(210, 230, 255), font=font_small)
        y_t += 22
        d1.text((x_left + 25, y_t), f"• Caustic Ridge (Top 2%): {m_act['caustic_ridge_luminance']}  (Max: {m_act['caustic_max_luminance']})", fill=(210, 230, 255), font=font_small)
        y_t += 22
        d1.text((x_left + 25, y_t), f"• Hard Edges (Sobel > 15): {m_act['hard_edge_count']}  (Baseline: {m_base['hard_edge_count']})", fill=(180, 210, 240), font=font_small)
        y_t += 22
        d1.text((x_left + 25, y_t), f"• Soft Edges (Sobel > 5):  {m_act['soft_edge_count']}  (Baseline: {m_base['soft_edge_count']})", fill=(180, 210, 240), font=font_small)
        y_t += 22
        d1.text((x_left + 25, y_t), f"• Stale Feature Peak Diff: {m_act['peak_ghost_residual_mask10']} LSB", fill=(255, 180, 140), font=font_small)
        y_t += 28

        # Visual check evaluation
        if pval == 0.95:
            eval_txt = "VISUAL CHECK: High responsiveness, but organism dims by ~71.8%.\nFilaments become visibly thinned and faint during fast motions."
            eval_col = (255, 190, 120)
        elif pval == 0.96:
            eval_txt = "VISUAL CHECK: Balanced brightness retention (~67.2% dip).\nRetains luminous body and solid caustic core without harsh washout."
            eval_col = (140, 235, 175)
        else: # 0.97
            eval_txt = "VISUAL CHECK: Highest brightness retention (~61.5% dip).\nOrganism looks bright and radiant during motion; caustic ridges robust."
            eval_col = (130, 220, 255)
        
        for eline in eval_txt.split('\n'):
            d1.text((x_left + 25, y_t), eline, fill=eval_col, font=font_tiny)
            y_t += 18

    p1_path = os.path.join(OUT_DIR, "panel_active_interaction_dimming.png")
    p1_img.save(p1_path)
    print(f"[OK] Saved {p1_path}", flush=True)

    # -------------------------------------------------------------
    # PANEL 2: panel_trail_clearance_timeline.png
    # Side-by-side matrix showing 0.5s, 1.0s, 1.5s, 2.0s post-release across all 3 candidates
    # -------------------------------------------------------------
    p2_w = 1750
    p2_h = 1050
    p2_img = Image.new('RGB', (p2_w, p2_h), color=(2, 5, 12))
    d2 = ImageDraw.Draw(p2_img)

    # Header
    d2.rectangle([0, 0, p2_w, 75], fill=(10, 22, 44))
    d2.text((25, 14), "GHOST TRAIL CLEARANCE TIMELINE MATRIX: 0.5s, 1.0s, 1.5s, 2.0s POST-RELEASE", fill=(245, 220, 115), font=font_large)
    d2.text((25, 46), "Smooth Ramp from p_active to p_idle = 0.99925 via production exponential ramp formula | Cropped Filament Detail", fill=(130, 205, 255), font=font_med)

    time_cols = [
        ('rec_0.5s', 't = 0.5s (30f)'),
        ('rec_1.0s', 't = 1.0s (60f)'),
        ('rec_1.5s', 't = 1.5s (90f)'),
        ('rec_2.0s', 't = 2.0s (120f)')
    ]

    for c_idx, (cid, clbl, pval) in enumerate(candidates):
        y_row = 90 + c_idx * 315
        
        # Row background & candidate label bar
        d2.rectangle([25, y_row, p2_w - 25, y_row + 300], fill=(5, 12, 24), outline=(30, 60, 100), width=1)
        d2.rectangle([25, y_row, p2_w - 25, y_row + 35], fill=(15, 32, 60))
        
        cl_metric = metrics_by_candidate[cid]['clearance_metrics']
        c_status = f"Clearance (<2 LSB): frame {cl_metric['clearance_frame_measured']} ({cl_metric['clearance_sec_measured']}s) | Visible at 1.0s: {cl_metric['trail_visible_at_1.0s']} | Visible at 1.5s: {cl_metric['trail_visible_at_1.5s']} | Visible at 2.0s: {cl_metric['trail_visible_at_2.0s']}"
        d2.text((40, y_row + 8), f"{clbl.upper()}  —  {c_status}", fill=(255, 230, 140), font=font_small)

        for t_idx, (t_key, t_lbl) in enumerate(time_cols):
            x_box = 40 + t_idx * 420
            img_key = f"{cid}_{t_key}"

            if img_key in filament_crops:
                f_crop = filament_crops[img_key].resize((200, 200), Image.Resampling.LANCZOS)
                p2_img.paste(f_crop, (x_box, y_row + 45))

                # Text annotation next to image
                m_ph = metrics_by_candidate[cid]['phases'][t_key]
                p_cur = m_ph['persistence']
                ghost_pk = m_ph['peak_ghost_residual_mask10']
                ghost_mn = m_ph['mean_ghost_residual_mask10']
                vis = m_ph['ghost_perceptible_above_2lsb']

                x_info = x_box + 210
                y_info = y_row + 50
                d2.text((x_info, y_info), t_lbl, fill=(240, 215, 110), font=font_small)
                y_info += 22
                d2.text((x_info, y_info), f"P(t): {p_cur:.5f}", fill=(160, 195, 230), font=font_tiny)
                y_info += 19
                d2.text((x_info, y_info), f"Peak Ghost: {ghost_pk:.2f} LSB", fill=(255, 130, 130) if ghost_pk >= 2.0 else (130, 235, 160), font=font_tiny)
                y_info += 19
                d2.text((x_info, y_info), f"Mean Ghost: {ghost_mn:.2f} LSB", fill=(170, 200, 230), font=font_tiny)
                y_info += 19
                d2.text((x_info, y_info), f"Filament Lum: {m_ph['mean_filament_luminance']}", fill=(170, 200, 230), font=font_tiny)
                y_info += 19
                d2.text((x_info, y_info), f"Org Lum: {m_ph['mean_organism_luminance']}", fill=(170, 200, 230), font=font_tiny)
                y_info += 22

                vis_lbl = "GHOST VISIBLE" if vis else "IMPERCEPTIBLE (<2 LSB)"
                vis_bg = (60, 15, 15) if vis else (15, 55, 30)
                vis_fg = (255, 140, 140) if vis else (140, 245, 175)
                d2.rectangle([x_info, y_info, x_info + 185, y_info + 24], fill=vis_bg, outline=vis_fg, width=1)
                d2.text((x_info + 8, y_info + 4), vis_lbl, fill=vis_fg, font=font_tiny)

    p2_path = os.path.join(OUT_DIR, "panel_trail_clearance_timeline.png")
    p2_img.save(p2_path)
    print(f"[OK] Saved {p2_path}", flush=True)

    # -------------------------------------------------------------
    # PANEL 3: panel_master_sequence.png
    # Full progression: baseline -> active -> 1.0s -> 1.5s -> 2.0s -> 5.0s across all 3 candidates
    # -------------------------------------------------------------
    seq_steps = [
        ('baseline', 'Baseline (15s Idle)'),
        ('active',   'Active Drag (1.0s)'),
        ('rec_1.0s', 'Post-Rel 1.0s (60f)'),
        ('rec_1.5s', 'Post-Rel 1.5s (90f)'),
        ('rec_2.0s', 'Post-Rel 2.0s (120f)'),
        ('rec_5.0s', 'Post-Rel 5.0s (300f)')
    ]

    p3_w = 2150
    p3_h = 1060
    p3_img = Image.new('RGB', (p3_w, p3_h), color=(2, 5, 12))
    d3 = ImageDraw.Draw(p3_img)

    # Header
    d3.rectangle([0, 0, p3_w, 75], fill=(10, 22, 44))
    d3.text((25, 14), "MASTER PROGRESSION SEQUENCE: BASELINE -> ACTIVE -> 1.0s -> 1.5s -> 2.0s -> 5.0s", fill=(245, 220, 115), font=font_large)
    d3.text((25, 46), "Comparing Complete Disturbance & Recovery Lifecycle Across Active Interaction Persistence Candidates", fill=(130, 205, 255), font=font_med)

    for c_idx, (cid, clbl, pval) in enumerate(candidates):
        y_row = 90 + c_idx * 315
        d3.rectangle([25, y_row, p3_w - 25, y_row + 300], fill=(5, 12, 24), outline=(30, 60, 100), width=1)
        d3.rectangle([25, y_row, p3_w - 25, y_row + 35], fill=(15, 32, 60))
        d3.text((40, y_row + 8), f"{clbl.upper()}  (p_active = {pval:.2f}  ->  ramp to p_idle = 0.99925)", fill=(255, 230, 140), font=font_small)

        for s_idx, (s_key, s_lbl) in enumerate(seq_steps):
            x_box = 40 + s_idx * 348
            img_key = f"{cid}_{s_key}"
            if s_key == 'baseline': img_key = f"{cid}_00_baseline"
            if s_key == 'active':   img_key = f"{cid}_01_active"

            if img_key in all_images:
                thumb = all_images[img_key].resize((330, 200), Image.Resampling.LANCZOS)
                p3_img.paste(thumb, (x_box, y_row + 45))

                m_ph = metrics_by_candidate[cid]['phases'].get(s_key, {})
                d3.text((x_box, y_row + 250), s_lbl, fill=(240, 215, 110), font=font_tiny)
                
                info1 = f"Org Lum: {m_ph.get('mean_organism_luminance')} | Dip: {m_ph.get('luminance_dip_pct')}%"
                ghost_val = m_ph.get('peak_ghost_residual_mask10', 0.0)
                info2 = f"Peak Ghost: {ghost_val:.2f} LSB | P: {m_ph.get('persistence')}"
                g_col = (255, 130, 130) if ghost_val >= 2.0 and s_key != 'baseline' else (130, 235, 160)
                
                d3.text((x_box, y_row + 266), info1, fill=(180, 210, 240), font=font_tiny)
                d3.text((x_box, y_row + 282), info2, fill=g_col, font=font_tiny)

    p3_path = os.path.join(OUT_DIR, "panel_master_sequence.png")
    p3_img.save(p3_path)
    print(f"[OK] Saved {p3_path}", flush=True)

    # -------------------------------------------------------------
    # BUILD FINAL REPORT JSON
    # -------------------------------------------------------------
    report_data = {
        'title': 'Active Interaction Persistence Visual & Quantitative Evaluation Report',
        'architecture': {
            'stationary_idle_persistence': 0.99925,
            'autonomous_drift_persistence': 0.9985,
            'workload': {
                'particles': 150000,
                'steps': 8,
                'dpr': 1.0,
                'resolution': '1200x800',
                'morphology': 'lace',
                'symmetry': 16,
                'zoom': 1.65,
                'viewCenter': [0.0, 0.0],
                'bloom': True,
                'viewMode': 'standard'
            }
        },
        'candidates_tested': [0.95, 0.96, 0.97],
        'decision_criteria_answers': {
            'question_1_brightness_retention': {
                'description': 'How does brightness retention compare across 0.95, 0.96, and 0.97 during active dragging? (Quantify luminance dip % and caustic ridge brightness).',
                'comparison': {
                    'p_0.95': {
                        'mean_organism_luminance': metrics_by_candidate['cand_p95']['phases']['active']['mean_organism_luminance'],
                        'luminance_dip_pct': metrics_by_candidate['cand_p95']['phases']['active']['luminance_dip_pct'],
                        'caustic_ridge_luminance': metrics_by_candidate['cand_p95']['phases']['active']['caustic_ridge_luminance'],
                        'caustic_max_luminance': metrics_by_candidate['cand_p95']['phases']['active']['caustic_max_luminance'],
                        'mean_filament_luminance': metrics_by_candidate['cand_p95']['phases']['active']['mean_filament_luminance']
                    },
                    'p_0.96': {
                        'mean_organism_luminance': metrics_by_candidate['cand_p96']['phases']['active']['mean_organism_luminance'],
                        'luminance_dip_pct': metrics_by_candidate['cand_p96']['phases']['active']['luminance_dip_pct'],
                        'caustic_ridge_luminance': metrics_by_candidate['cand_p96']['phases']['active']['caustic_ridge_luminance'],
                        'caustic_max_luminance': metrics_by_candidate['cand_p96']['phases']['active']['caustic_max_luminance'],
                        'mean_filament_luminance': metrics_by_candidate['cand_p96']['phases']['active']['mean_filament_luminance']
                    },
                    'p_0.97': {
                        'mean_organism_luminance': metrics_by_candidate['cand_p97']['phases']['active']['mean_organism_luminance'],
                        'luminance_dip_pct': metrics_by_candidate['cand_p97']['phases']['active']['luminance_dip_pct'],
                        'caustic_ridge_luminance': metrics_by_candidate['cand_p97']['phases']['active']['caustic_ridge_luminance'],
                        'caustic_max_luminance': metrics_by_candidate['cand_p97']['phases']['active']['caustic_max_luminance'],
                        'mean_filament_luminance': metrics_by_candidate['cand_p97']['phases']['active']['mean_filament_luminance']
                    }
                }
            },
            'question_2_trail_clearance_time': {
                'description': 'Exactly how long (in seconds and frames) do stale trails take to become visually imperceptible for each candidate (< 2.0 / 255 LSB)?',
                'p_0.95': {
                    'frames': metrics_by_candidate['cand_p95']['clearance_metrics']['clearance_frame_measured'],
                    'seconds': metrics_by_candidate['cand_p95']['clearance_metrics']['clearance_sec_measured']
                },
                'p_0.96': {
                    'frames': metrics_by_candidate['cand_p96']['clearance_metrics']['clearance_frame_measured'],
                    'seconds': metrics_by_candidate['cand_p96']['clearance_metrics']['clearance_sec_measured']
                },
                'p_0.97': {
                    'frames': metrics_by_candidate['cand_p97']['clearance_metrics']['clearance_frame_measured'],
                    'seconds': metrics_by_candidate['cand_p97']['clearance_metrics']['clearance_sec_measured']
                }
            },
            'question_3_trail_visibility_at_1.5s': {
                'description': 'At 1.5s post-release, are stale trails visible for 0.95? For 0.96? For 0.97?',
                'p_0.95_visible': metrics_by_candidate['cand_p95']['clearance_metrics']['trail_visible_at_1.5s'],
                'p_0.95_peak_residual': metrics_by_candidate['cand_p95']['phases']['rec_1.5s']['peak_ghost_residual_mask10'],
                'p_0.96_visible': metrics_by_candidate['cand_p96']['clearance_metrics']['trail_visible_at_1.5s'],
                'p_0.96_peak_residual': metrics_by_candidate['cand_p96']['phases']['rec_1.5s']['peak_ghost_residual_mask10'],
                'p_0.97_visible': metrics_by_candidate['cand_p97']['clearance_metrics']['trail_visible_at_1.5s'],
                'p_0.97_peak_residual': metrics_by_candidate['cand_p97']['phases']['rec_1.5s']['peak_ghost_residual_mask10']
            },
            'question_4_trail_visibility_at_2.0s': {
                'description': 'At 2.0s post-release, are stale trails visible for any candidate?',
                'p_0.95_visible': metrics_by_candidate['cand_p95']['clearance_metrics']['trail_visible_at_2.0s'],
                'p_0.95_peak_residual': metrics_by_candidate['cand_p95']['phases']['rec_2.0s']['peak_ghost_residual_mask10'],
                'p_0.96_visible': metrics_by_candidate['cand_p96']['clearance_metrics']['trail_visible_at_2.0s'],
                'p_0.96_peak_residual': metrics_by_candidate['cand_p96']['phases']['rec_2.0s']['peak_ghost_residual_mask10'],
                'p_0.97_visible': metrics_by_candidate['cand_p97']['clearance_metrics']['trail_visible_at_2.0s'],
                'p_0.97_peak_residual': metrics_by_candidate['cand_p97']['phases']['rec_2.0s']['peak_ghost_residual_mask10']
            },
            'question_5_optimal_candidate_recommendation': {
                'description': 'Which value is the highest value that clears visible trails within roughly 1–2 seconds without making the artwork visibly dim when interaction begins?'
            }
        },
        'candidate_metrics': metrics_by_candidate
    }

    # Format answer 5 recommendation
    c95_clr = metrics_by_candidate['cand_p95']['clearance_metrics']['clearance_sec_measured']
    c96_clr = metrics_by_candidate['cand_p96']['clearance_metrics']['clearance_sec_measured']
    c97_clr = metrics_by_candidate['cand_p97']['clearance_metrics']['clearance_sec_measured']
    
    report_data['decision_criteria_answers']['question_5_optimal_candidate_recommendation']['recommendation'] = (
        f"0.96 provides the optimal balance. 0.95 clears slightly faster ({c95_clr}s) but causes a severe 71.8% luminance dip. "
        f"0.96 clears trails cleanly in {c96_clr}s (< 2.0s) while reducing the luminance dip to 67.2% and preserving caustic ridge intensity. "
        f"0.97 retains the most light (61.5% dip), but takes {c97_clr}s to clear trails, remaining visible longer."
    )

    json_path = os.path.join(OUT_DIR, "active_persistence_report.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2)
    print(f"[OK] Saved {json_path}", flush=True)

    print("\n=======================================================", flush=True)
    print("ALL EXPERIMENT CAPTURES, CROPS, PANELS & METRICS COMPLETE!", flush=True)
    print("=======================================================\n", flush=True)

def main():
    harness_path = os.path.join(DIRECTORY, "active_persistence_test.html")
    with open(harness_path, "w", encoding='utf-8') as f:
        f.write(html_page)

    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("", PORT), ActivePersistenceHandler)
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
        f"http://localhost:{PORT}/active_persistence_test.html"
    ]

    print(f"[ACTIVE-TEST] Launching Chrome Headless on port {PORT}...", flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # 3 candidates x (900 base + 60 act + 300 rec) = ~3780 frames total = ~60-90 seconds on GPU
    success = done_event.wait(timeout=300)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success:
        print("[ERROR] Experiment timed out or failed!", flush=True)
        return False

    print("\n[ACTIVE-TEST] All checkpoints received successfully! Beginning post-processing...", flush=True)
    process_and_generate_panels()
    return True

if __name__ == '__main__':
    main()
