/**
 * Application Controller & Interactive Laboratory
 * Orchestrates authentic Mobius complex dynamics, GPU simulation,
 * interactive perturbations, deep zoom navigation, and live readouts.
 */

import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

class App {
  constructor() {
    this.canvas = document.getElementById('gl-canvas');
    this.math = new MathSystem();
    this.renderer = new MobiusRenderer(this.canvas);

    // UI elements
    this.uiContainer = document.getElementById('ui-container');
    this.readoutEl = document.getElementById('equation-readout');
    this.valA = document.getElementById('val-a');
    this.valB = document.getElementById('val-b');
    this.valC = document.getElementById('val-c');
    this.valD = document.getElementById('val-d');
    this.valN = document.getElementById('val-n');
    this.debugOverlay = document.getElementById('debug-overlay');
    this.coeffDrawer = document.getElementById('coeff-drawer');

    // Debug fields
    this.dbgTier = document.getElementById('dbg-tier');
    this.dbgBudget = document.getElementById('dbg-budget');
    this.dbgHeadroom = document.getElementById('dbg-headroom');
    this.dbgFormat = document.getElementById('dbg-format');
    this.dbgPath = document.getElementById('dbg-path');
    this.dbgEvent = document.getElementById('dbg-event');
    this.dbgFps = document.getElementById('dbg-fps');
    this.dbgFrameTime = document.getElementById('dbg-frametime');
    this.dbgCpu = document.getElementById('dbg-cpu');
    this.dbgGpu = document.getElementById('dbg-gpu');
    this.dbgGpuSim = document.getElementById('dbg-gpusim');
    this.dbgGpuSplat = document.getElementById('dbg-gpusplat');
    this.dbgGpuPost = document.getElementById('dbg-gpupost');
    this.dbgParticles = document.getElementById('dbg-particles');
    this.dbgSteps = document.getElementById('dbg-steps');
    this.dbgIters = document.getElementById('dbg-iters');
    this.dbgDpr = document.getElementById('dbg-dpr');
    this.dbgZoom = document.getElementById('dbg-zoom');
    this.dbgAccum = document.getElementById('dbg-accum');
    this.dbgDraws = document.getElementById('dbg-draws');
    this.dbgRes = document.getElementById('dbg-res');

    this.debugMode = false;
    this.uiHidden = false;
    this.readoutVisible = true;
    this.coeffDrawerVisible = false;

    // Power & display throttling state
    this.isTabHidden = false;
    this.lastSimTime = performance.now();

    // Display refresh rate detection (Requirement 14)
    this.refreshRate = 60;
    this.rafDeltas = [];
    this.isHighRefresh = false;
    this.lastRafTimestamp = 0;

    // Parse URL parameters for automated testing & direct linking
    const params = new URLSearchParams(window.location.search);
    if (params.has('tier')) {
      this.renderer.adaptive.setMode(params.get('tier'));
    }
    if (params.has('morph')) {
      this.math.setMorphology(params.get('morph'));
    }
    if (params.has('n')) {
      this.math.setSymmetry(parseInt(params.get('n'), 10));
    }
    if (params.has('particles')) {
      this.renderer.setParticleCount(parseInt(params.get('particles'), 10));
    }
    if (params.has('steps')) {
      this.renderer.setStepsOverride(parseInt(params.get('steps'), 10));
    }
    if (params.has('dpr')) {
      this.customDpr = parseFloat(params.get('dpr'));
    }
    if (params.has('zoom')) {
      const z = parseFloat(params.get('zoom'));
      this.renderer.zoom = 1.65 * z;
      this.renderer.targetZoom = 1.65 * z;
      const cx = params.has('cx') ? parseFloat(params.get('cx')) : 0.0;
      const cy = params.has('cy') ? parseFloat(params.get('cy')) : 0.0;
      this.renderer.viewCenter = [cx, cy];
      this.renderer.targetViewCenter = [cx, cy];
    }
    if (params.has('view')) {
      const v = params.get('view');
      if (v === 'raw') {
        this.renderer.viewMode = 2;
      } else if (v === 'nobloom') {
        this.renderer.viewMode = 1;
        this.renderer.bloomEnabled = false;
      } else {
        this.renderer.viewMode = 0;
        this.renderer.bloomEnabled = true;
      }
    } else {
      if (params.has('raw')) {
        this.renderer.viewMode = 2;
      }
      if (params.has('nobloom')) {
        this.renderer.viewMode = 1;
        this.renderer.bloomEnabled = false;
      }
    }
    if (params.has('debug') || params.has('profile')) {
      this.debugMode = true;
      this.debugOverlay.classList.add('visible');
      document.getElementById('btn-debug')?.classList.add('active');
    }

    // Expose global handles for testing harness
    window.__app = this;
    window.__renderer = this.renderer;
    window.__math = this.math;
    window.__profiler = this.renderer.profiler;

    // Interaction state
    this.isDragging = false;
    this.dragStart = [0, 0];
    this.dragCenterStart = [0, 0];

    this.setupEvents();
    this.setupUI();
    this.onResize();

    this.lastTime = performance.now();
    this.animate = this.animate.bind(this);
    if (window.location.search.includes('capture=1')) {
      this.animate(performance.now());
    } else {
      requestAnimationFrame(this.animate);
    }
  }

  setupEvents() {
    window.addEventListener('resize', () => this.onResize());

    // Tab visibility handling: pause/throttle simulation loop when hidden to conserve GPU/battery
    document.addEventListener('visibilitychange', () => {
      this.isTabHidden = document.hidden;
      if (!this.isTabHidden) {
        this.lastTime = performance.now();
        this.lastSimTime = performance.now();
      }
    });

    // Pointer move: subtle continuous mathematical coefficient perturbation
    window.addEventListener('pointermove', (e) => {
      this.renderer.adaptive.markInteraction();
      if (this.isDragging) {
        const dx = (e.clientX - this.dragStart[0]) / (this.canvas.width * 0.5);
        const dy = (e.clientY - this.dragStart[1]) / (this.canvas.height * 0.5);
        const aspect = this.canvas.width / this.canvas.height;
        const scale = 2.0 / (this.renderer.zoom * 2.0);

        this.renderer.targetViewCenter[0] = this.dragCenterStart[0] - dx * scale * aspect;
        this.renderer.targetViewCenter[1] = this.dragCenterStart[1] + dy * scale;
      } else {
        const normX = (e.clientX / window.innerWidth) * 2 - 1;
        const normY = 1 - (e.clientY / window.innerHeight) * 2;
        this.math.setPointer(normX, normY);
      }
    });

    // Pointer down: click disturbance shock or drag navigation
    this.canvas.addEventListener('pointerdown', (e) => {
      this.renderer.adaptive.markInteraction();
      if (e.button === 2 || e.shiftKey || e.altKey) {
        // Pan
        this.isDragging = true;
        this.dragStart = [e.clientX, e.clientY];
        this.dragCenterStart = [...this.renderer.targetViewCenter];
      } else if (e.button === 0) {
        // Shock disturbance to transformation mathematics
        const normX = (e.clientX / window.innerWidth) * 2 - 1;
        const normY = 1 - (e.clientY / window.innerHeight) * 2;
        this.math.injectShock(normX, normY);
      }
    });

    window.addEventListener('pointerup', () => {
      this.isDragging = false;
    });

    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());

    // Smooth Deep Zoom with mouse wheel
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.renderer.adaptive.markInteraction();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
      const newZoom = Math.max(0.3, Math.min(500.0, this.renderer.targetZoom * zoomFactor));

      const mouseX = (e.clientX / window.innerWidth) * 2 - 1;
      const mouseY = 1 - (e.clientY / window.innerHeight) * 2;
      const aspect = this.canvas.width / this.canvas.height;
      const cx = (mouseX * aspect) / this.renderer.zoom + this.renderer.viewCenter[0];
      const cy = mouseY / this.renderer.zoom + this.renderer.viewCenter[1];

      // Shift view center towards cursor when zooming in
      if (zoomFactor > 1.0) {
        this.renderer.targetViewCenter[0] += (cx - this.renderer.targetViewCenter[0]) * 0.15;
        this.renderer.targetViewCenter[1] += (cy - this.renderer.targetViewCenter[1]) * 0.15;
      }

      this.renderer.targetZoom = newZoom;
    }, { passive: false });

    // Keyboard shortcuts
    window.addEventListener('keydown', (e) => {
      const key = e.key.toLowerCase();
      if (key === 'h') {
        this.toggleUI();
      } else if (key === 'd') {
        this.toggleDebug();
      } else if (key === ' ') {
        e.preventDefault();
        this.togglePause();
      } else if (key === 'r') {
        this.resetView();
      } else if (key === 'b') {
        this.toggleBloom();
      } else if (key === 't') {
        this.toggleRawTrajectories();
      } else if (key === 'o') {
        this.toggleReadout();
      } else if (key === 'p') {
        this.toggleCoeffDrawer();
      }
    });
  }

  setupUI() {
    // Adaptive Quality Selector buttons
    const qualityBtns = document.querySelectorAll('.quality-btn');
    qualityBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const tier = btn.dataset.tier;
        this.renderer.adaptive.setMode(tier);
        qualityBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        this.onResize();
      });
    });

    // Sync active button on startup
    const currentMode = this.renderer.adaptive.mode;
    qualityBtns.forEach((b) => {
      b.classList.toggle('active', b.dataset.tier === currentMode);
    });

    // Symmetry selector buttons
    const symmetryBtns = document.querySelectorAll('.sym-btn');
    symmetryBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const n = parseInt(btn.dataset.n, 10);
        this.math.setSymmetry(n);
        symmetryBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        // Graceful symmetry transition without black flash
        this.renderer.startSymmetryTransition();
        this.renderer.adaptive.markInteraction();
      });
    });

    // Zoom buttons
    document.getElementById('btn-zoom-in').addEventListener('click', () => {
      this.renderer.adaptive.markInteraction();
      this.renderer.targetZoom = Math.min(500.0, this.renderer.targetZoom * 1.5);
    });
    document.getElementById('btn-zoom-out').addEventListener('click', () => {
      this.renderer.adaptive.markInteraction();
      this.renderer.targetZoom = Math.max(0.3, this.renderer.targetZoom / 1.5);
    });
    document.getElementById('btn-zoom-reset').addEventListener('click', () => {
      this.renderer.adaptive.markInteraction();
      this.renderer.targetZoom = 1.65;
      this.renderer.targetViewCenter = [0.0, 0.0];
    });

    // Main Control buttons
    document.getElementById('btn-pause').addEventListener('click', () => this.togglePause());
    document.getElementById('btn-reset').addEventListener('click', () => this.resetView());
    document.getElementById('btn-debug').addEventListener('click', () => this.toggleDebug());
    document.getElementById('btn-hide').addEventListener('click', () => this.toggleUI());
    document.getElementById('btn-bloom').addEventListener('click', () => this.toggleBloom());
    document.getElementById('btn-raw').addEventListener('click', () => this.toggleRawTrajectories());
    document.getElementById('btn-readout').addEventListener('click', () => this.toggleReadout());
    document.getElementById('btn-coeff').addEventListener('click', () => this.toggleCoeffDrawer());

    // Coefficient Sliders
    const sliderARe = document.getElementById('slider-a-re');
    const sliderBIm = document.getElementById('slider-b-im');
    const sliderCRe = document.getElementById('slider-c-re');
    const sliderDIm = document.getElementById('slider-d-im');

    sliderARe.addEventListener('input', (e) => {
      this.renderer.adaptive.markInteraction();
      const v = parseFloat(e.target.value);
      document.getElementById('lbl-a-re').innerText = v.toFixed(2);
      this.math.setCoefficientOffset('a', v, 0);
    });
    sliderBIm.addEventListener('input', (e) => {
      this.renderer.adaptive.markInteraction();
      const v = parseFloat(e.target.value);
      document.getElementById('lbl-b-im').innerText = v.toFixed(2);
      this.math.setCoefficientOffset('b', 0, v);
    });
    sliderCRe.addEventListener('input', (e) => {
      this.renderer.adaptive.markInteraction();
      const v = parseFloat(e.target.value);
      document.getElementById('lbl-c-re').innerText = v.toFixed(2);
      this.math.setCoefficientOffset('c', v, 0);
    });
    sliderDIm.addEventListener('input', (e) => {
      this.renderer.adaptive.markInteraction();
      const v = parseFloat(e.target.value);
      document.getElementById('lbl-d-im').innerText = v.toFixed(2);
      this.math.setCoefficientOffset('d', 0, v);
    });

    document.getElementById('btn-reset-coeffs').addEventListener('click', () => {
      this.renderer.adaptive.markInteraction();
      sliderARe.value = 0; document.getElementById('lbl-a-re').innerText = '0.00';
      sliderBIm.value = 0; document.getElementById('lbl-b-im').innerText = '0.00';
      sliderCRe.value = 0; document.getElementById('lbl-c-re').innerText = '0.00';
      sliderDIm.value = 0; document.getElementById('lbl-d-im').innerText = '0.00';
      this.math.setCoefficientOffset('a', 0, 0);
      this.math.setCoefficientOffset('b', 0, 0);
      this.math.setCoefficientOffset('c', 0, 0);
      this.math.setCoefficientOffset('d', 0, 0);
    });
  }

  togglePause() {
    this.math.evolving = !this.math.evolving;
    const btn = document.getElementById('btn-pause');
    btn.innerText = this.math.evolving ? 'Pause' : 'Resume';
    btn.classList.toggle('active', !this.math.evolving);
  }

  resetView() {
    this.math.reset();
    this.renderer.targetZoom = 1.65;
    this.renderer.targetViewCenter = [0.0, 0.0];
    this.renderer.clearAccumulation();

    // Reset sliders
    document.getElementById('slider-a-re').value = 0; document.getElementById('lbl-a-re').innerText = '0.00';
    document.getElementById('slider-b-im').value = 0; document.getElementById('lbl-b-im').innerText = '0.00';
    document.getElementById('slider-c-re').value = 0; document.getElementById('lbl-c-re').innerText = '0.00';
    document.getElementById('slider-d-im').value = 0; document.getElementById('lbl-d-im').innerText = '0.00';
  }

  toggleUI() {
    this.uiHidden = !this.uiHidden;
    this.uiContainer.classList.toggle('hidden', this.uiHidden);
    document.getElementById('hint-unhide').classList.toggle('visible', this.uiHidden);
  }

  toggleReadout() {
    this.readoutVisible = !this.readoutVisible;
    this.readoutEl.classList.toggle('collapsed', !this.readoutVisible);
    document.getElementById('btn-readout').classList.toggle('active', this.readoutVisible);
  }

  toggleCoeffDrawer() {
    this.coeffDrawerVisible = !this.coeffDrawerVisible;
    this.coeffDrawer.classList.toggle('visible', this.coeffDrawerVisible);
    document.getElementById('btn-coeff').classList.toggle('active', this.coeffDrawerVisible);
  }

  toggleDebug() {
    this.debugMode = !this.debugMode;
    this.debugOverlay.classList.toggle('visible', this.debugMode);
    document.getElementById('btn-debug').classList.toggle('active', this.debugMode);
  }

  toggleBloom() {
    this.renderer.bloomEnabled = !this.renderer.bloomEnabled;
    if (this.renderer.bloomEnabled) {
      this.renderer.viewMode = 0;
    } else {
      this.renderer.viewMode = 1;
    }
    const btn = document.getElementById('btn-bloom');
    btn.innerText = `Bloom: ${this.renderer.bloomEnabled ? 'ON' : 'OFF'}`;
    btn.classList.toggle('active', this.renderer.bloomEnabled);
    const rawBtn = document.getElementById('btn-raw');
    rawBtn.classList.remove('active');
  }

  toggleRawTrajectories() {
    if (this.renderer.viewMode === 2) {
      this.renderer.viewMode = this.renderer.bloomEnabled ? 0 : 1;
    } else {
      this.renderer.viewMode = 2;
    }
    const btn = document.getElementById('btn-raw');
    btn.innerText = `Raw: ${this.renderer.viewMode === 2 ? 'ON' : 'OFF'}`;
    btn.classList.toggle('active', this.renderer.viewMode === 2);
  }

  onResize() {
    if (typeof window === 'undefined' || window.innerWidth <= 0 || window.innerHeight <= 0) return;
    const dpr = this.customDpr || this.renderer.adaptive.getDpr();
    const w = Math.floor(window.innerWidth * dpr);
    const h = Math.floor(window.innerHeight * dpr);
    this.renderer.resize(w, h);
  }

  animate(currentTime) {
    requestAnimationFrame(this.animate);

    // Visibility throttling: stop simulation loop when document is hidden to conserve GPU/battery
    if (this.isTabHidden) {
      this.lastTime = currentTime;
      return;
    }

    // Refresh rate estimation (Requirement 14):
    // Collect rolling RAF intervals to detect actual monitor refresh behavior (60, 75, 90, 120, 144, 240 Hz)
    if (this.lastRafTimestamp > 0) {
      const delta = currentTime - this.lastRafTimestamp;
      if (delta > 2.0 && delta < 100.0) {
        this.rafDeltas.push(delta);
        if (this.rafDeltas.length > 45) this.rafDeltas.shift();
        if (this.rafDeltas.length >= 15) {
          const sorted = [...this.rafDeltas].sort((a, b) => a - b);
          const median = sorted[Math.floor(sorted.length / 2)];
          this.refreshRate = Math.round(1000 / median);
          this.isHighRefresh = this.refreshRate >= 75;
        }
      }
    }
    this.lastRafTimestamp = currentTime;

    // High-refresh display power efficiency (Requirement 14):
    // On high-refresh displays (>65 Hz), cap heavy simulation updates to ~60 Hz (sim interval >= 15.0ms)
    // On native 60 Hz displays, NEVER drop frames due to minor scheduling jitter!
    const isCapture = typeof window !== 'undefined' && window.location.search.includes('capture=1');
    if (!isCapture && this.isHighRefresh) {
      const simDt = currentTime - this.lastSimTime;
      if (simDt < 15.0) {
        return;
      }
    }
    this.lastSimTime = currentTime;

    const dt = Math.min(0.05, (currentTime - this.lastTime) / 1000);
    this.lastTime = currentTime;

    // Check if dynamic DPR adaptation requires resizing
    const currentTargetDpr = this.customDpr || this.renderer.adaptive.getDpr();
    const targetW = Math.floor(window.innerWidth * currentTargetDpr);
    const targetH = Math.floor(window.innerHeight * currentTargetDpr);
    if (Math.abs(this.canvas.width - targetW) > 4 || Math.abs(this.canvas.height - targetH) > 4) {
      this.renderer.resize(targetW, targetH);
    }

    // Update mathematical coefficients
    const tMath0 = performance.now();
    this.math.update(dt, this.renderer.zoom);
    const jsTime = performance.now() - tMath0;

    // Render WebGL2 frame
    this.renderer.render(this.math, dt, jsTime);

    // Update Live Equation Readout
    this.valA.innerText = this.math.a.format(3);
    this.valB.innerText = this.math.b.format(3);
    this.valC.innerText = this.math.c.format(3);
    this.valD.innerText = this.math.d.format(3);
    this.valN.innerText = this.math.n;

    // Update Diagnostic Debug / Profiler Overlay (if visible)
    if (this.debugMode) {
      const m = this.renderer.profiler.metrics;
      const status = this.renderer.adaptive.getStatus();

      if (this.dbgTier) this.dbgTier.innerText = status.tierDisplay;
      if (this.dbgParticles) this.dbgParticles.innerText = `${this.renderer.numParticles.toLocaleString()} trajectories`;
      if (this.dbgSteps) this.dbgSteps.innerText = `${this.renderer.stepsPerFrame}`;
      if (this.dbgIters) this.dbgIters.innerText = `${(this.renderer.numParticles * this.renderer.stepsPerFrame).toLocaleString()}`;
      if (this.dbgBudget) this.dbgBudget.innerText = `${status.targetBudgetMs.toFixed(1)} ms`;
      if (this.dbgHeadroom) this.dbgHeadroom.innerText = status.headroomPercent !== null ? `${status.headroomPercent}%` : '--%';
      if (this.dbgFps) this.dbgFps.innerText = `${m.fps} FPS (${m.fps1Low} 1% low) [${this.refreshRate}Hz display]`;
      if (this.dbgFrameTime) this.dbgFrameTime.innerText = `${m.frameMs.toFixed(1)} ms`;
      if (this.dbgCpu) this.dbgCpu.innerText = `${m.cpuMs.toFixed(2)} ms (JS: ${m.jsUpdateMs.toFixed(2)}ms)`;

      if (status.gpuEma !== null) {
        if (this.dbgGpu) this.dbgGpu.innerText = `${status.gpuEma.toFixed(2)} ms (EMA)`;
      } else if (m.gpuSupported && m.gpuMs !== null) {
        if (this.dbgGpu) this.dbgGpu.innerText = `${m.gpuMs.toFixed(2)} ms`;
      } else {
        if (this.dbgGpu) this.dbgGpu.innerText = `N/A (timer query unavail)`;
      }

      if (this.dbgDpr) this.dbgDpr.innerText = `${currentTargetDpr.toFixed(2)}`;
      if (this.dbgAccum) this.dbgAccum.innerText = `${status.accumulationAgeSec}s (${this.renderer.accumulationFrames} frames)`;
      if (this.dbgFormat) this.dbgFormat.innerText = this.renderer.floatFormat;
      if (this.dbgPath) this.dbgPath.innerText = this.renderer.floatCapability;
      if (this.dbgEvent) this.dbgEvent.innerText = status.lastEvent;
      if (this.dbgZoom) this.dbgZoom.innerText = `${this.renderer.zoom.toFixed(2)}x`;
      if (this.dbgRes) this.dbgRes.innerText = `${this.canvas.width} x ${this.canvas.height}`;
    }

    document.body.setAttribute('data-frames', this.renderer.accumulationFrames);

    // Capture hook for automated test harness
    if (window.location.search.includes('capture=1') && !window._captured) {
      window._captured = true;
      const params = new URLSearchParams(window.location.search);
      if (params.has('morph')) {
        this.math.setMorphology(params.get('morph'));
      }
      if (params.has('n')) {
        this.math.setSymmetry(parseInt(params.get('n'), 10));
      }
      if (params.has('zoom')) {
        const z = parseFloat(params.get('zoom'));
        this.renderer.zoom = 1.65 * z;
        this.renderer.targetZoom = 1.65 * z;
        const cx = params.has('cx') ? parseFloat(params.get('cx')) : 0.0;
        const cy = params.has('cy') ? parseFloat(params.get('cy')) : 0.0;
        this.renderer.viewCenter = [cx, cy];
        this.renderer.targetViewCenter = [cx, cy];
      }
      if (params.has('view')) {
        const v = params.get('view');
        if (v === 'raw') {
          this.renderer.viewMode = 2;
        } else if (v === 'nobloom') {
          this.renderer.viewMode = 1;
          this.renderer.bloomEnabled = false;
        } else {
          this.renderer.viewMode = 0;
          this.renderer.bloomEnabled = true;
        }
      } else {
        if (params.has('raw')) {
          this.renderer.viewMode = 2;
        }
        if (params.has('nobloom')) {
          this.renderer.viewMode = 1;
          this.renderer.bloomEnabled = false;
        }
      }
      if (params.has('debug')) {
        this.debugMode = true;
        this.debugOverlay.classList.add('visible');
        document.getElementById('btn-debug').classList.add('active');
      }

      // Pre-accumulate frames synchronously for high-quality test captures
      const zFactor = params.has('zoom') ? parseFloat(params.get('zoom')) : 1.0;
      const numFrames = params.has('raw') ? 25 : (zFactor > 50.0 ? 120 : (zFactor > 10.0 ? 90 : 60));
      // Freeze drift during capture accumulation so progressive accumulation forms crystal-clear caustics
      this.math.evolving = false;
      for (let i = 0; i < numFrames; i++) {
        this.math.update(0.016, this.renderer.zoom);
        this.renderer.render(this.math, 0.016);
      }
      const dataUrl = this.canvas.toDataURL('image/png');
      const cap = document.getElementById('capture-container');
      if (cap) {
        cap.innerText = dataUrl;
        document.body.setAttribute('data-ready', 'true');
        document.body.setAttribute('data-frames', this.renderer.accumulationFrames);
      }
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
