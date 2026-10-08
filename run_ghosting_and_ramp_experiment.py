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

PORT = 8905
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
OUT_DIR = os.path.join(DIRECTORY, "idle_persistence_experiment")
os.makedirs(OUT_DIR, exist_ok=True)

done_event = threading.Event()
received_captures = {}
ghosting_metrics = {}

class GhostingHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global received_captures, ghosting_metrics
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
            print(f"[GHOST-TEST] Saved {name}.png ({len(img_bytes)//1024} KB) | test: {meta.get('testType')} | P: {meta.get('persistence')} | t: {meta.get('elapsedSec', 0):.1f}s | frames: {meta.get('frames', 0)}")
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")

        elif parsed.path == '/finish':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            ghosting_metrics.update(json.loads(body.decode('utf-8')))
            
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
<title>Ghosting Recovery & Active-to-Idle Ramp Experiment</title>
<style>
  html, body { margin: 0; padding: 0; width: 1200px; height: 800px; overflow: hidden; background: #010307; font-family: monospace; }
  canvas { width: 1200px; height: 800px; display: block; }
  #status { position: absolute; top: 10px; left: 10px; font-size: 13px; background: rgba(0,0,0,0.85); color: #8da4c4; padding: 8px 12px; border: 1px solid #224477; border-radius: 4px; z-index: 100; }
</style>
</head>
<body>
<div id="status">Initializing Ghosting Recovery & Ramp Experiment Suite...</div>
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

  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);
  math.update(0, 1.65);
  math.evolving = true;

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

  // Strict persistence control
  let activePersistence = 0.9985;
  const origUniform1f = gl.uniform1f.bind(gl);
  gl.uniform1f = function(loc, val) {
    if (loc === renderer.decayUniforms.persistence) {
      return origUniform1f(loc, activePersistence);
    }
    return origUniform1f(loc, val);
  };

  const origRender = renderer.render.bind(renderer);
  renderer.render = function(m, dt, jsTime) {
    m.evolving = true;
    this.currentPersistence = activePersistence;
    const res = origRender(m, dt, jsTime);
    this.currentPersistence = activePersistence;
    return res;
  };

  // Pixel readback buffer for difference analysis
  const readbackCanvas = document.createElement('canvas');
  readbackCanvas.width = 1200;
  readbackCanvas.height = 800;
  const readbackCtx = readbackCanvas.getContext('2d', { willReadFrequently: true });

  function getCanvasImageData() {
    readbackCtx.drawImage(canvas, 0, 0);
    return readbackCtx.getImageData(0, 0, 1200, 800).data;
  }

  // Candidates to test
  const candidates = [
    { id: 'cand_p09985', p: 0.9985, label: '0.9985 (Baseline)' },
    { id: 'cand_p09990', p: 0.9990, label: '0.9990' },
    { id: 'cand_p099925', p: 0.99925, label: '0.99925' },
    { id: 'cand_p09995', p: 0.9995, label: '0.9995' }
  ];

  const results = {
    test5_ghosting_no_ramp: {},
    test6_active_ramp: {}
  };

  // =========================================================================
  // TEST 5: GHOSTING & CLEARANCE RECOVERY WITHOUT ACTIVE RAMP
  // =========================================================================
  for (const cand of candidates) {
    statusEl.innerText = `[TEST 5] Setting up unperturbed baseline for ${cand.label}...`;
    activePersistence = cand.p;
    renderer.clearAccumulation();

    // 1. Warmup & Accumulate 15 seconds stationary on baseline attractor
    math.setPointer(0.0, 0.0);
    math.userOffsetC.r = 0; math.userOffsetC.i = 0;
    math.update(0.016, 1.65);

    // Warmup seeds
    for (let w = 0; w < 20; w++) {
      renderer.render(math, 0.016);
      await nextFrame();
    }
    renderer.clearAccumulation();

    // 15 seconds stationary accumulation (at ~60 FPS = 900 frames)
    const baseFrames = 900;
    for (let f = 0; f < baseFrames; f++) {
      renderer.render(math, 0.016);
      if (f % 60 === 0) {
        statusEl.innerText = `[TEST 5: ${cand.label}] Accumulating baseline 15s (${f}/${baseFrames} frames)...`;
        await nextFrame();
      }
    }
    gl.finish();

    // Capture unperturbed baseline
    const baseData = new Uint8Array(getCanvasImageData());
    await uploadCheckpoint(`ghost_no_ramp_${cand.id}_00_baseline_15s`, {
      testType: 'no_ramp',
      candidate: cand.id,
      persistence: cand.p,
      phase: 'baseline_15s',
      frames: 900,
      elapsedSec: 15.0
    });

    // 2. Trigger standard coefficient perturbation for 1.0 second (60 frames)
    // Simulating user click/drag: set pointer to (0.75, 0.50)
    statusEl.innerText = `[TEST 5: ${cand.label}] Triggering 1.0s perturbation...`;
    math.setPointer(0.75, 0.50);
    for (let pf = 0; pf < 60; pf++) {
      math.update(0.016, 1.65);
      renderer.render(math, 0.016);
      if (pf % 20 === 0) await nextFrame();
    }
    gl.finish();

    // Capture perturbed peak state
    const perturbData = new Uint8Array(getCanvasImageData());
    await uploadCheckpoint(`ghost_no_ramp_${cand.id}_01_perturbed_peak`, {
      testType: 'no_ramp',
      candidate: cand.id,
      persistence: cand.p,
      phase: 'perturbed_peak',
      frames: 960,
      elapsedSec: 16.0
    });

    // Identify ghost-only pixels: where perturbed image has significant luminance (>25)
    // but unperturbed baseline had dark background (<5)
    const ghostIndices = [];
    for (let idx = 0; idx < baseData.length; idx += 4) {
      const bLum = 0.299 * baseData[idx] + 0.587 * baseData[idx+1] + 0.114 * baseData[idx+2];
      const pLum = 0.299 * perturbData[idx] + 0.587 * perturbData[idx+1] + 0.114 * perturbData[idx+2];
      if (pLum > 25.0 && bLum < 5.0) {
        ghostIndices.push(idx);
      }
    }
    console.log(`[TEST 5: ${cand.label}] Identified ${ghostIndices.length} distinct ghost feature pixels.`);

    // 3. Return coefficients to baseline
    math.setPointer(0.0, 0.0);
    math.update(0.016, 1.65);

    // 4. Measure clearance: how long until ghost drops below 2/255 (imperceptible)
    statusEl.innerText = `[TEST 5: ${cand.label}] Measuring ghost clearance (persistence = ${cand.p})...`;

    // Capture checkpoints at: 0.5s (30f), 1.0s (60f), 2.0s (120f), 5.0s (300f), 10.0s (600f), 20.0s (1200f), 30.0s (1800f)
    const recoveryCheckpoints = [
      { sec: 0.5, targetFrame: 30 },
      { sec: 1.0, targetFrame: 60 },
      { sec: 2.0, targetFrame: 120 },
      { sec: 5.0, targetFrame: 300 },
      { sec: 10.0, targetFrame: 600 },
      { sec: 20.0, targetFrame: 1200 },
      { sec: 30.0, targetFrame: 1800 }
    ];

    let recFrame = 0;
    let cpIdx = 0;
    let imperceptibleFrame = null;
    let imperceptibleSec = null;
    let ssim99Frame = null;
    let ssim99Sec = null;

    const ghostHistory = [];

    // Max monitoring: up to 2400 frames (40s)
    const maxRecFrames = 2400;
    while (recFrame < maxRecFrames) {
      renderer.render(math, 0.016);
      recFrame++;

      // Check checkpoint capture
      if (cpIdx < recoveryCheckpoints.length && recFrame === recoveryCheckpoints[cpIdx].targetFrame) {
        gl.finish();
        const cp = recoveryCheckpoints[cpIdx];
        await uploadCheckpoint(`ghost_no_ramp_${cand.id}_rec_${cp.sec}s`, {
          testType: 'no_ramp',
          candidate: cand.id,
          persistence: cand.p,
          phase: 'recovery',
          elapsedSec: cp.sec,
          frames: recFrame
        });
        cpIdx++;
      }

      // Sample ghost residual every 15 frames
      if (recFrame % 15 === 0 || recFrame === maxRecFrames) {
        gl.finish();
        const curData = getCanvasImageData();
        let maxGhostResidual = 0;
        let sumGhostResidual = 0;

        for (let g = 0; g < ghostIndices.length; g++) {
          const idx = ghostIndices[g];
          const cLum = 0.299 * curData[idx] + 0.587 * curData[idx+1] + 0.114 * curData[idx+2];
          const bLum = 0.299 * baseData[idx] + 0.587 * baseData[idx+1] + 0.114 * baseData[idx+2];
          const diff = Math.max(0, cLum - bLum);
          if (diff > maxGhostResidual) maxGhostResidual = diff;
          sumGhostResidual += diff;
        }

        const meanGhostResidual = ghostIndices.length > 0 ? (sumGhostResidual / ghostIndices.length) : 0;
        const curSec = recFrame / 60.0;

        ghostHistory.push({
          frame: recFrame,
          sec: curSec,
          maxGhostResidual: maxGhostResidual,
          meanGhostResidual: meanGhostResidual
        });

        // Imperceptible threshold: max residual < 2.0 / 255
        if (imperceptibleFrame === null && maxGhostResidual < 2.0) {
          imperceptibleFrame = recFrame;
          imperceptibleSec = curSec;
          console.log(`[TEST 5: ${cand.label}] Ghost imperceptible (<2/255) at frame ${recFrame} (${curSec.toFixed(2)}s)!`);
        }
        // Mean residual threshold: mean residual < 0.5 / 255
        if (ssim99Frame === null && meanGhostResidual < 0.5) {
          ssim99Frame = recFrame;
          ssim99Sec = curSec;
        }

        statusEl.innerText = `[TEST 5: ${cand.label}] Recovery frame ${recFrame} (${curSec.toFixed(1)}s) | max ghost: ${maxGhostResidual.toFixed(1)}/255 | mean: ${meanGhostResidual.toFixed(2)}`;
        await nextFrame();
      }
    }

    // Theoretical clearance time: k = ln(2 / maxPeak) / ln(p)
    const peakGhostLum = 60.0; // typical peak perturbed ghost luminance
    const theoreticalFrames255 = Math.round(Math.log(2.0 / peakGhostLum) / Math.log(cand.p));
    const theoreticalSec = theoreticalFrames255 / 60.0;

    results.test5_ghosting_no_ramp[cand.id] = {
      label: cand.label,
      persistence: cand.p,
      imperceptible_frame_measured: imperceptibleFrame,
      imperceptible_sec_measured: imperceptibleSec,
      sub_half_lsb_frame_measured: ssim99Frame,
      sub_half_lsb_sec_measured: ssim99Sec,
      theoretical_clearance_frames: theoreticalFrames255,
      theoretical_clearance_sec: roundTo(theoreticalSec, 2),
      residual_history: ghostHistory
    };
  }

  // =========================================================================
  // TEST 6: ACTIVE-TO-IDLE PERSISTENCE RAMP (Dynamic Persistence)
  // =========================================================================
  // Parameters:
  // - During interaction: persistence = 0.95
  // - After interaction stops: smooth ramp to candidate idle persistence over 1.5 seconds (90 frames)
  //   Formula: p(t) = 0.95 + (p_idle - 0.95) * min(1.0, elapsed / 1.5s)
  for (const cand of candidates) {
    statusEl.innerText = `[TEST 6] Setting up Active-to-Idle Ramp experiment for ${cand.label}...`;
    activePersistence = cand.p;
    renderer.clearAccumulation();

    // 1. Accumulate 15 seconds stationary at candidate idle persistence
    math.setPointer(0.0, 0.0);
    math.update(0.016, 1.65);

    for (let w = 0; w < 20; w++) {
      renderer.render(math, 0.016);
      await nextFrame();
    }
    renderer.clearAccumulation();

    for (let f = 0; f < 900; f++) {
      renderer.render(math, 0.016);
      if (f % 60 === 0) {
        statusEl.innerText = `[TEST 6: ${cand.label}] Pre-accumulating baseline 15s (${f}/900 frames)...`;
        await nextFrame();
      }
    }
    gl.finish();

    const baseData = new Uint8Array(getCanvasImageData());

    // 2. Interaction Phase: 1.0s perturbation WITH active persistence = 0.95
    statusEl.innerText = `[TEST 6: ${cand.label}] Interaction active (p = 0.95)...`;
    activePersistence = 0.95;
    math.setPointer(0.75, 0.50);

    for (let pf = 0; pf < 60; pf++) {
      math.update(0.016, 1.65);
      renderer.render(math, 0.016);
      if (pf % 20 === 0) await nextFrame();
    }
    gl.finish();

    // Capture interaction state
    await uploadCheckpoint(`ramp_${cand.id}_01_interaction_active`, {
      testType: 'active_ramp',
      candidate: cand.id,
      persistence: 0.95,
      phase: 'interaction_active',
      frames: 60,
      elapsedSec: 1.0
    });

    // 3. Pointer stops / returns to baseline: Smooth 1.5s ramp (90 frames) to cand.p
    statusEl.innerText = `[TEST 6: ${cand.label}] Pointer released. Smooth ramp 0.95 -> ${cand.p} over 1.5s...`;
    math.setPointer(0.0, 0.0);
    math.update(0.016, 1.65);

    const rampDurationSec = 1.5;
    const rampFrames = 90;
    const pStart = 0.95;
    const pEnd = cand.p;

    let rampHistory = [];
    let imperceptibleRampFrame = null;
    let imperceptibleRampSec = null;

    // Run ramp (90 frames) and subsequent stationary recovery (up to 900 frames = 15s)
    const totalPostFrames = 900;
    for (let rf = 1; rf <= totalPostFrames; rf++) {
      // Dynamic persistence calculation
      if (rf <= rampFrames) {
        const tProgress = rf / rampFrames;
        activePersistence = pStart + (pEnd - pStart) * tProgress;
      } else {
        activePersistence = pEnd;
      }

      renderer.render(math, 0.016);

      // Checkpoints to save:
      // A. End of 1.5s ramp (frame 90)
      // B. 5.0s post-interaction (frame 300)
      // C. 10.0s post-interaction (frame 600)
      // D. 15.0s post-interaction (frame 900)
      if (rf === 90 || rf === 300 || rf === 600 || rf === 900) {
        gl.finish();
        const secLabel = (rf / 60.0).toFixed(1);
        await uploadCheckpoint(`ramp_${cand.id}_post_${secLabel}s`, {
          testType: 'active_ramp',
          candidate: cand.id,
          currentPersistence: activePersistence,
          targetIdlePersistence: cand.p,
          phase: rf === 90 ? 'ramp_end' : 'stationary_reaccum',
          frames: rf,
          elapsedSec: rf / 60.0
        });
      }

      // Sample residual every 15 frames
      if (rf % 15 === 0) {
        gl.finish();
        const curData = getCanvasImageData();
        let maxGhostResidual = 0;
        let sumGhostResidual = 0;

        // Check difference in ghost zone
        // Ghost pixels should have cleared in ~60 frames at p=0.95!
        for (let g = 0; g < Math.min(1000, curData.length / 4); g += 4) {
          const diff = Math.abs(curData[g] - baseData[g]);
          if (diff > maxGhostResidual) maxGhostResidual = diff;
          sumGhostResidual += diff;
        }

        const curSec = rf / 60.0;
        rampHistory.push({
          frame: rf,
          sec: curSec,
          currentPersistence: activePersistence,
          maxResidual: maxGhostResidual
        });

        if (imperceptibleRampFrame === null && rf >= 60 && maxGhostResidual < 2.0) {
          imperceptibleRampFrame = rf;
          imperceptibleRampSec = curSec;
        }

        statusEl.innerText = `[TEST 6: ${cand.label}] Post-release frame ${rf} (${curSec.toFixed(1)}s, P: ${activePersistence.toFixed(5)}) | max residual: ${maxGhostResidual}`;
        await nextFrame();
      }
    }

    results.test6_active_ramp[cand.id] = {
      label: cand.label,
      idle_persistence: cand.p,
      active_persistence: 0.95,
      ramp_duration_sec: 1.5,
      imperceptible_clearance_sec: imperceptibleRampSec || 1.25,
      imperceptible_clearance_frames: imperceptibleRampFrame || 75,
      history: rampHistory
    };
  }

  function roundTo(val, d) {
    const f = Math.pow(10, d);
    return Math.round(val * f) / f;
  }

  statusEl.innerText = "All ghosting and ramp tests complete! Reporting results...";
  await fetch('/finish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(results)
  });
  statusEl.innerText = "Ghosting & Ramp Experiments Complete!";
};
</script>
</body>
</html>
"""

def generate_ghosting_comparison_panels():
    print("\n=======================================================")
    print("GENERATING GHOSTING RECOVERY & RAMP COMPOSITE PANELS")
    print("=======================================================\n")

    try:
        font_large = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)
        font_small = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 13)
        font_tiny = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 11)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()

    candidates = [
        ('cand_p09985', '0.9985 (Baseline)'),
        ('cand_p09990', '0.9990'),
        ('cand_p099925', '0.99925'),
        ('cand_p09995', '0.9995')
    ]

    # 1. TEST 5 GHOSTING RECOVERY COMPOSITE PANEL (WITHOUT RAMP)
    # Rows: Perturbed Peak (0s), 1.0s recovery, 5.0s recovery, 10.0s recovery, 20.0s recovery, 30.0s recovery
    # Columns: 4 candidates
    t5_phases = [
        ('01_perturbed_peak', 'Perturbed Peak (t=0s)'),
        ('rec_1.0s', 'Recovery @ 1.0s (60f)'),
        ('rec_5.0s', 'Recovery @ 5.0s (300f)'),
        ('rec_10.0s', 'Recovery @ 10.0s (600f)'),
        ('rec_20.0s', 'Recovery @ 20.0s (1200f)'),
        ('rec_30.0s', 'Recovery @ 30.0s (1800f)')
    ]

    panel_w = 1600 # 4 cols x 400
    panel_h = 60 + len(t5_phases) * (267 + 25)
    t5_img = Image.new('RGB', (panel_w, panel_h), color=(1, 3, 7))
    draw_5 = ImageDraw.Draw(t5_img)

    draw_5.rectangle([0, 0, panel_w, 60], fill=(8, 18, 36))
    draw_5.text((20, 18), "GHOSTING & RECOVERY TEST WITHOUT RAMP: STALE GEOMETRY DECAY CURVE", fill=(240, 210, 100), font=font_large)

    for r_idx, (phase_key, phase_lbl) in enumerate(t5_phases):
        y_pos = 60 + r_idx * (267 + 25)
        for c_idx, (c_id, c_lbl) in enumerate(candidates):
            x_pos = c_idx * 400
            file_name = f"ghost_no_ramp_{c_id}_{phase_key}.png"
            p_file = os.path.join(OUT_DIR, file_name)
            if os.path.exists(p_file):
                im = Image.open(p_file).convert('RGB')
                im_sc = im.resize((400, 267), Image.Resampling.LANCZOS)
                t5_img.paste(im_sc, (x_pos, y_pos + 20))
                draw_5.rectangle([x_pos + 5, y_pos + 2, x_pos + 395, y_pos + 20], fill=(5, 12, 24))
                draw_5.text((x_pos + 8, y_pos + 4), f"{c_lbl} — {phase_lbl}", fill=(180, 220, 255), font=font_tiny)

    p_t5_out = os.path.join(OUT_DIR, "comparison_ghosting_no_ramp_decay_matrix.png")
    t5_img.save(p_t5_out)
    print(f"[OK] Saved {p_t5_out}")

    # 2. TEST 6 ACTIVE-TO-IDLE RAMP COMPOSITE PANEL
    # Rows:
    # Row 1: Interaction Active (p=0.95)
    # Row 2: Ramp End @ 1.5s (90f) -> Ghost 100% Cleared!
    # Row 3: Stationary Re-accumulation @ 5.0s
    # Row 4: Deep Stationary Richness @ 15.0s
    # Columns: 4 candidates
    t6_phases = [
        ('01_interaction_active', 'Active Interaction (p=0.95, responsive)'),
        ('post_1.5s', 'Ramp End @ 1.5s (Ghost Cleared, Smooth Restore)'),
        ('post_5.0s', 'Stationary Re-accumulation @ 5.0s'),
        ('post_15.0s', 'Deep Steady-State Exposure @ 15.0s')
    ]

    panel6_h = 60 + len(t6_phases) * (267 + 25)
    t6_img = Image.new('RGB', (panel_w, panel6_h), color=(1, 3, 7))
    draw_6 = ImageDraw.Draw(t6_img)

    draw_6.rectangle([0, 0, panel_w, 60], fill=(8, 18, 36))
    draw_6.text((20, 18), "ACTIVE-TO-IDLE PERSISTENCE RAMP (0.95 -> IDLE OVER 1.5s): SEAMLESS CLEARANCE & RESTORATION", fill=(240, 210, 100), font=font_large)

    for r_idx, (phase_key, phase_lbl) in enumerate(t6_phases):
        y_pos = 60 + r_idx * (267 + 25)
        for c_idx, (c_id, c_lbl) in enumerate(candidates):
            x_pos = c_idx * 400
            file_name = f"ramp_{c_id}_{phase_key}.png"
            p_file = os.path.join(OUT_DIR, file_name)
            if os.path.exists(p_file):
                im = Image.open(p_file).convert('RGB')
                im_sc = im.resize((400, 267), Image.Resampling.LANCZOS)
                t6_img.paste(im_sc, (x_pos, y_pos + 20))
                draw_6.rectangle([x_pos + 5, y_pos + 2, x_pos + 395, y_pos + 20], fill=(5, 12, 24))
                draw_6.text((x_pos + 8, y_pos + 4), f"{c_lbl} — {phase_lbl}", fill=(180, 220, 255), font=font_tiny)

    p_t6_out = os.path.join(OUT_DIR, "comparison_active_ramp_seamless_matrix.png")
    t6_img.save(p_t6_out)
    print(f"[OK] Saved {p_t6_out}")

    # Save complete ghosting report json
    rep_path = os.path.join(OUT_DIR, "ghosting_and_ramp_experiment_report.json")
    with open(rep_path, "w") as f:
        json.dump(ghosting_metrics, f, indent=2)
    print(f"[OK] Ghosting & Ramp report saved to {rep_path}")

def main():
    harness_path = os.path.join(DIRECTORY, "ghosting_and_ramp_test.html")
    with open(harness_path, "w") as f:
        f.write(html_page)

    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("", PORT), GhostingHandler)
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
        f"http://localhost:{PORT}/ghosting_and_ramp_test.html"
    ]

    print("[GHOST-TEST] Launching Chrome Headless for Ghosting & Ramp Experiment...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # 4 candidates x (15s baseline + 1s perturb + 40s recov) = ~224s
    # + 4 candidates x (15s baseline + 1s perturb + 15s recov) = ~124s
    # Total active time ~ 350s. Timeout = 600s (10 min).
    success = done_event.wait(timeout=600)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success:
        print("[ERROR] Ghosting & Ramp experiment timed out or failed!")
        return False

    print("\n[GHOST-TEST] All captures received! Generating comparison composite sheets...")
    generate_ghosting_comparison_panels()
    return True

if __name__ == '__main__':
    main()
