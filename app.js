/**
 * Application Controller & Mode Architecture
 * 
 * PRODUCT ARCHITECTURE:
 * 1. MODE 1 — REFERENCE:
 *    - Faithful reproduction of published Simone Conradi 2026 Mobius attractor
 *    - Symmetry n = 16, exact Conradi coefficients (a = -0.755+0.330i, b = -0.376+0.026i, c = 6.401+0.803i, d = 1.520+0.840i)
 *    - User offsets & disturbances strictly reset to 0
 *    - Autonomous micro-drift paused (stationary integration)
 *    - Mouse movement does NOT alter formula
 *    - Preserves camera framing intended for reference piece (zoom 1.65, center [0,0])
 *    - Allows Brute Force for maximum fidelity
 * 
 * 2. MODE 2 — EXPLORE:
 *    - Interactive mathematical sandbox
 *    - Pointer-based coefficient perturbation & click shocks enabled
 *    - Coefficient sliders & symmetry order selection enabled
 *    - Drift toggle, zoom & pan navigation enabled
 *    - Curated color grading palettes
 * 
 * 3. MODE 3 — RANDOMIZE:
 *    - Curated morphology families: subtle, organic, dense lace, symmetric, chaotic, conradi-like
 * 
 * 4. EXPORT & PRESETS:
 *    - High-resolution offscreen PNG export (3840 x 2160 4K UHD)
 *    - Pre-export accumulation/develop pass with progress indicator
 *    - Preserves session state and screen accumulation
 *    - Full JSON preset library (save, load, copy, import)
 */

import { MathSystem, CONRADI_REFERENCE } from './math.js';
import { MobiusRenderer, PALETTES } from './renderer.js';

export const CURATED_PRESETS = [
  {
    name: 'Simone Conradi (Reference Artwork)',
    description: 'Exact published 2026 Mobius attractor with 16-fold rosette',
    mode: 'reference',
    symmetry: 16,
    coefficients: {
      a: { r: -0.755, i: 0.330 },
      b: { r: -0.376, i: 0.026 },
      c: { r: 6.401, i: 0.803 },
      d: { r: 1.520, i: 0.840 }
    },
    userOffsets: { a: { r: 0, i: 0 }, b: { r: 0, i: 0 }, c: { r: 0, i: 0 }, d: { r: 0, i: 0 } },
    camera: { zoom: 1.65, center: [0.0, 0.0] },
    palette: 'cobalt',
    drift: { evolving: false, time: 0 },
    rendering: { bloom: true, viewMode: 0, tier: 'auto' }
  },
  {
    name: 'Caustic Crown (16-fold)',
    description: 'Strong inner orbital boundary, complex interference outside',
    mode: 'explore',
    symmetry: 16,
    coefficients: {
      a: { r: -0.785, i: 0.315 },
      b: { r: -0.410, i: 0.010 },
      c: { r: 6.650, i: 0.650 },
      d: { r: 1.580, i: 0.920 }
    },
    userOffsets: { a: { r: 0, i: 0 }, b: { r: 0, i: 0 }, c: { r: 0, i: 0 }, d: { r: 0, i: 0 } },
    camera: { zoom: 1.65, center: [0.0, 0.0] },
    palette: 'cobalt',
    drift: { evolving: true, time: 0 },
    rendering: { bloom: true, viewMode: 0, tier: 'high' }
  },
  {
    name: 'Filament Storm (24-fold)',
    description: 'Interlocking braided secondary orbits with counter-rotating wave crests',
    mode: 'explore',
    symmetry: 24,
    coefficients: {
      a: { r: -0.710, i: 0.420 },
      b: { r: -0.395, i: 0.010 },
      c: { r: 7.350, i: 0.650 },
      d: { r: 1.650, i: 0.820 }
    },
    userOffsets: { a: { r: 0, i: 0 }, b: { r: 0, i: 0 }, c: { r: 0, i: 0 }, d: { r: 0, i: 0 } },
    camera: { zoom: 1.65, center: [0.0, 0.0] },
    palette: 'amethyst',
    drift: { evolving: true, time: 0 },
    rendering: { bloom: true, viewMode: 0, tier: 'high' }
  },
  {
    name: 'Organic Knot (8-fold)',
    description: 'Chambered recursive curls with pinched intersections',
    mode: 'explore',
    symmetry: 8,
    coefficients: {
      a: { r: -0.755, i: 0.330 },
      b: { r: -0.376, i: 0.026 },
      c: { r: 6.401, i: 0.803 },
      d: { r: 1.520, i: 0.840 }
    },
    userOffsets: { a: { r: 0, i: 0 }, b: { r: 0, i: 0 }, c: { r: 0, i: 0 }, d: { r: 0, i: 0 } },
    camera: { zoom: 1.65, center: [0.0, 0.0] },
    palette: 'aurora',
    drift: { evolving: true, time: 0 },
    rendering: { bloom: true, viewMode: 0, tier: 'standard' }
  },
  {
    name: 'Deep Specimen (12-fold)',
    description: 'Nested concentric levels of micro-caustics across scales',
    mode: 'explore',
    symmetry: 12,
    coefficients: {
      a: { r: -0.755, i: 0.330 },
      b: { r: -0.376, i: 0.026 },
      c: { r: 6.401, i: 0.803 },
      d: { r: 1.520, i: 0.840 }
    },
    userOffsets: { a: { r: 0, i: 0 }, b: { r: 0, i: 0 }, c: { r: 0, i: 0 }, d: { r: 0, i: 0 } },
    camera: { zoom: 1.65, center: [0.0, 0.0] },
    palette: 'solar',
    drift: { evolving: true, time: 0 },
    rendering: { bloom: true, viewMode: 0, tier: 'ultra' }
  },
  {
    name: 'Gossamer Lace (32-fold)',
    description: 'High-density web filigree with brilliant harmonic ring',
    mode: 'explore',
    symmetry: 32,
    coefficients: {
      a: { r: -0.745, i: 0.335 },
      b: { r: -0.372, i: 0.024 },
      c: { r: 6.480, i: 0.810 },
      d: { r: 1.530, i: 0.845 }
    },
    userOffsets: { a: { r: 0, i: 0 }, b: { r: 0, i: 0 }, c: { r: 0, i: 0 }, d: { r: 0, i: 0 } },
    camera: { zoom: 1.65, center: [0.0, 0.0] },
    palette: 'monochrome',
    drift: { evolving: true, time: 0 },
    rendering: { bloom: true, viewMode: 0, tier: 'high' }
  }
];

export class App {
  constructor() {
    this.canvas = document.getElementById('gl-canvas');
    this.math = new MathSystem('explore');
    this.renderer = new MobiusRenderer(this.canvas);
    this.contextLost = false;
    this._exportTask = null;
    // These belong to App, not the replaceable renderer. Install exactly once.
    this.canvas.addEventListener('webglcontextlost', event => this.onContextLost(event));
    this.canvas.addEventListener('webglcontextrestored', () => this.onContextRestored());

    // Primary mode state: 'reference' (default faithful art) | 'explore' (interactive sandbox)
    this.mode = 'reference';

    // UI elements
    this.uiContainer = document.getElementById('ui-container');
    this.controlsBar = document.getElementById('controls-bar');
    this.modeStatusPill = document.getElementById('mode-status-pill');
    this.readoutEl = document.getElementById('equation-readout');
    this.valA = document.getElementById('val-a');
    this.valB = document.getElementById('val-b');
    this.valC = document.getElementById('val-c');
    this.valD = document.getElementById('val-d');
    this.valN = document.getElementById('val-n');
    this.debugOverlay = document.getElementById('debug-overlay');
    this.coeffDrawer = document.getElementById('coeff-drawer');
    this.coeffLockNotice = document.getElementById('coeff-lock-notice');
    this.btnModeRef = document.getElementById('btn-mode-reference');
    this.btnModeExp = document.getElementById('btn-mode-explore');
    this.randomizeMenu = document.getElementById('randomize-menu');
    this.paletteMenu = document.getElementById('palette-menu');
    this.btnPaletteToggle = document.getElementById('btn-palette-toggle');
    this.exportModal = document.getElementById('export-modal');
    this.presetModal = document.getElementById('preset-modal');
    this.toastBanner = document.getElementById('toast-banner');

    // Debug fields
    this.dbgMode = document.getElementById('dbg-mode');
    this.dbgBruteBanner = document.getElementById('dbg-brute-banner');
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
    this.dbgParticles = document.getElementById('dbg-particles');
    this.dbgSteps = document.getElementById('dbg-steps');
    this.dbgIters = document.getElementById('dbg-iters');
    this.dbgDpr = document.getElementById('dbg-dpr');
    this.dbgZoom = document.getElementById('dbg-zoom');
    this.dbgAccum = document.getElementById('dbg-accum');
    this.dbgRes = document.getElementById('dbg-res');

    this.debugMode = false;
    this.uiHidden = false;
    this.readoutVisible = true;
    this.coeffDrawerVisible = false;

    // Power & display throttling state
    this.isTabHidden = false;
    this.lastSimTime = performance.now();
    this.refreshRate = 60;
    this.rafDeltas = [];
    this.isHighRefresh = false;
    this.lastRafTimestamp = 0;

    // Interaction state
    this.isDragging = false;
    this.dragStart = [0, 0];
    this.dragCenterStart = [0, 0];

    // Export state
    this.isExporting = false;
    this.displayHoldActive = false;
    this._pendingHoldRemoval = false;
    this.exportType = 'standard'; // 'standard' | 'reference_master'
    this.exportWidth = 3840;
    this.exportHeight = 2160;
    this.exportPasses = 60;
    this.refMasterPasses = 120;

    // Parse URL parameters for automated testing & direct linking
    const params = new URLSearchParams(window.location.search);
    let startMode = 'reference';
    if (params.has('mode')) {
      startMode = params.get('mode');
    }
    if (params.has('bruteforce') || params.has('brute')) {
      this.renderer.adaptive.setMode('bruteforce');
    } else if (params.has('tier')) {
      this.renderer.adaptive.setMode(params.get('tier'));
    }
    if (params.has('morph')) {
      this.math.setMorphology(params.get('morph'));
      startMode = 'explore';
    }
    if (params.has('n')) {
      this.math.setSymmetry(parseInt(params.get('n'), 10));
      startMode = 'explore';
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
    if (params.has('palette')) {
      this.renderer.setPalette(params.get('palette'));
    }
    if (params.has('randomize')) {
      this.math.randomize(params.get('randomize'));
      startMode = 'explore';
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
      if (params.has('raw')) this.renderer.viewMode = 2;
      if (params.has('nobloom')) {
        this.renderer.viewMode = 1;
        this.renderer.bloomEnabled = false;
      }
    }
    if (params.has('debug') || params.has('profile')) {
      this.debugMode = true;
      this.debugOverlay?.classList.add('visible');
      document.getElementById('btn-debug')?.classList.add('active');
    }

    // Expose global handles for testing harness
    window.__app = this;
    window.__renderer = this.renderer;
    window.__math = this.math;
    window.__profiler = this.renderer.profiler;

    this.setupEvents();
    this.setupUI();
    this.setMode(startMode);
    this.updateReadout();
    this.onResize();

    this.lastTime = performance.now();
    this.animate = this.animate.bind(this);
    if (window.location.search.includes('capture=1')) {
      this.animate(performance.now());
    } else {
      requestAnimationFrame(this.animate);
    }
  }

  setMode(mode) {
    this.mode = mode;
    this.math.setMode(mode);

    if (mode === 'reference') {
      // MODE 1 — REFERENCE:
      // Exact Conradi coefficients, n = 16, drift paused, offsets & perturbations reset
      this.renderer.zoom = 1.65;
      this.renderer.targetZoom = 1.65;
      this.renderer.viewCenter = [0.0, 0.0];
      this.renderer.targetViewCenter = [0.0, 0.0];
      this.renderer.setPalette('cobalt');
      this.renderer.clearAccumulation();

      // Sliders reset to 0.00
      this.resetSliderDisplay();
      this.showToast('Reference Mode activated • Exact Conradi artwork restored');
    } else {
      // MODE 2 — EXPLORE:
      this.showToast('Explore Mode activated • Interactive sandbox unlocked');
    }

    this.updateModeUI();
    this.updateReadout();
  }

  updateModeUI() {
    const isRef = (this.mode === 'reference');

    // Update Mode Switcher buttons
    if (this.btnModeRef) this.btnModeRef.classList.toggle('active', isRef);
    if (this.btnModeExp) this.btnModeExp.classList.toggle('active', !isRef);

    // Update Mode Status Pill
    if (this.modeStatusPill) {
      if (isRef) {
        this.modeStatusPill.className = 'pill-reference';
        this.modeStatusPill.innerHTML = `
          <span class="mode-dot ref-dot"></span>
          <strong>REFERENCE MODE</strong> &bull; Exact Simone Conradi 2026 Artwork (Formula Protected &bull; Drift Paused)
        `;
      } else {
        this.modeStatusPill.className = 'pill-explore';
        this.modeStatusPill.innerHTML = `
          <span class="mode-dot exp-dot"></span>
          <strong>EXPLORE MODE</strong> &bull; Interactive Sandbox (Pointer Perturbations &amp; Sliders Active)
        `;
      }
    }

    // Lock indicator in slider drawer
    if (this.coeffLockNotice) {
      this.coeffLockNotice.style.display = isRef ? 'block' : 'none';
    }

    // Disable/lock sliders in Reference mode
    const sliders = document.querySelectorAll('.coeff-slider');
    sliders.forEach(s => s.disabled = isRef);
    const resetCoeffBtn = document.getElementById('btn-reset-coeffs');
    if (resetCoeffBtn) resetCoeffBtn.disabled = isRef;

    // Symmetry buttons: in Reference mode, locked to 16
    const symBtns = document.querySelectorAll('.sym-btn');
    symBtns.forEach(btn => {
      const n = parseInt(btn.dataset.n, 10);
      btn.classList.toggle('active', isRef ? n === 16 : n === this.math.n);
      btn.style.opacity = isRef && n !== 16 ? '0.4' : '1.0';
      btn.title = isRef ? 'Locked to n=16 in Reference mode' : `Order n = ${n}`;
    });

    // Pause/Resume button
    const btnPause = document.getElementById('btn-pause');
    if (btnPause) {
      if (isRef) {
        btnPause.innerText = 'Drift: Off';
        btnPause.classList.remove('active');
        btnPause.disabled = true;
        btnPause.title = 'Drift is paused in Reference mode';
      } else {
        btnPause.disabled = false;
        btnPause.innerText = this.math.evolving ? 'Pause' : 'Resume';
        btnPause.classList.toggle('active', !this.math.evolving);
        btnPause.title = 'Toggle autonomous coefficient drift';
      }
    }

    // Palette button: update active item
    if (this.btnPaletteToggle) {
      const curPal = PALETTES[this.renderer.activePalette] || PALETTES.cobalt;
      this.btnPaletteToggle.innerText = `Palette: ${curPal.name.split(' ')[0]} ▾`;
    }
  }

  updateSliderInputs() {
    const sA = document.getElementById('slider-a-re');
    const sB = document.getElementById('slider-b-im');
    const sC = document.getElementById('slider-c-re');
    const sD = document.getElementById('slider-d-im');
    const lA = document.getElementById('lbl-a-re');
    const lB = document.getElementById('lbl-b-im');
    const lC = document.getElementById('lbl-c-re');
    const lD = document.getElementById('lbl-d-im');

    const offA = this.math.userOffsetA ? this.math.userOffsetA.r : 0;
    const offB = this.math.userOffsetB ? this.math.userOffsetB.i : 0;
    const offC = this.math.userOffsetC ? this.math.userOffsetC.r : 0;
    const offD = this.math.userOffsetD ? this.math.userOffsetD.i : 0;

    if (sA) sA.value = offA;
    if (sB) sB.value = offB;
    if (sC) sC.value = offC;
    if (sD) sD.value = offD;
    if (lA) lA.innerText = offA.toFixed(2);
    if (lB) lB.innerText = offB.toFixed(2);
    if (lC) lC.innerText = offC.toFixed(2);
    if (lD) lD.innerText = offD.toFixed(2);
  }

  resetSliderDisplay() {
    if (this.math) {
      this.math.userOffsetA = new (this.math.userOffsetA.constructor)(0, 0);
      this.math.userOffsetB = new (this.math.userOffsetB.constructor)(0, 0);
      this.math.userOffsetC = new (this.math.userOffsetC.constructor)(0, 0);
      this.math.userOffsetD = new (this.math.userOffsetD.constructor)(0, 0);
    }
    this.updateSliderInputs();
  }

  updateReadout() {
    if (this.valA) this.valA.innerText = this.math.a.format(3);
    if (this.valB) this.valB.innerText = this.math.b.format(3);
    if (this.valC) this.valC.innerText = this.math.c.format(3);
    if (this.valD) this.valD.innerText = this.math.d.format(3);
    if (this.valN) this.valN.innerText = this.math.n;
  }

  randomize(style = null) {
    // Mode 3: Randomize switches to explore sandbox mode
    this.mode = 'explore';
    const res = this.math.randomize(style);
    this.renderer.clearAccumulation();

    this.updateSliderInputs();
    this.updateModeUI();
    this.closeDropdowns();

    this.showToast(`Randomized [${res.style}]: ${res.name}`);
  }

  showToast(message, duration = 3000) {
    if (!this.toastBanner) return;
    this.toastBanner.innerText = message;
    this.toastBanner.classList.add('show');
    clearTimeout(this._toastTimeout);
    this._toastTimeout = setTimeout(() => {
      this.toastBanner?.classList.remove('show');
    }, duration);
  }

  closeDropdowns() {
    if (this.randomizeMenu) this.randomizeMenu.classList.remove('visible');
    if (this.paletteMenu) this.paletteMenu.classList.remove('visible');
  }

  setupEvents() {
    window.addEventListener('resize', () => this.onResize());

    // Tab visibility handling
    document.addEventListener('visibilitychange', () => {
      this.isTabHidden = document.hidden;
      if (!this.isTabHidden) {
        this.lastTime = performance.now();
        this.lastSimTime = performance.now();
      }
    });

    // Close dropdowns on outside click
    window.addEventListener('click', (e) => {
      if (!e.target.closest('.dropdown-container')) {
        this.closeDropdowns();
      }
    });

    // Pointer move:
    // IMPORTANT UX RULE: In Reference mode, ordinary mouse movement must NOT alter the formula!
    window.addEventListener('pointermove', (e) => {
      this.renderer.adaptive.markInteraction();
      if (this.isDragging) {
        if (this.mode === 'explore') {
          const dx = (e.clientX - this.dragStart[0]) / (this.canvas.width * 0.5);
          const dy = (e.clientY - this.dragStart[1]) / (this.canvas.height * 0.5);
          const aspect = this.canvas.width / this.canvas.height;
          const scale = 2.0 / (this.renderer.zoom * 2.0);

          this.renderer.targetViewCenter[0] = this.dragCenterStart[0] - dx * scale * aspect;
          this.renderer.targetViewCenter[1] = this.dragCenterStart[1] + dy * scale;
        }
      } else {
        if (this.mode === 'explore') {
          const normX = (e.clientX / window.innerWidth) * 2 - 1;
          const normY = 1 - (e.clientY / window.innerHeight) * 2;
          this.math.setPointer(normX, normY);
        }
      }
    });

    // Pointer down:
    // In Reference mode, click shock disturbance is strictly locked out!
    this.canvas.addEventListener('pointerdown', (e) => {
      this.renderer.adaptive.markInteraction();
      if (e.button === 2 || e.shiftKey || e.altKey) {
        if (this.mode === 'explore') {
          this.isDragging = true;
          this.dragStart = [e.clientX, e.clientY];
          this.dragCenterStart = [...this.renderer.targetViewCenter];
        }
      } else if (e.button === 0) {
        if (this.mode === 'explore') {
          const normX = (e.clientX / window.innerWidth) * 2 - 1;
          const normY = 1 - (e.clientY / window.innerHeight) * 2;
          this.math.injectShock(normX, normY);
        }
      }
    });

    window.addEventListener('pointerup', () => {
      this.isDragging = false;
    });

    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());

    // Wheel zoom: in Reference mode, framing is strictly preserved
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.renderer.adaptive.markInteraction();
      if (this.mode === 'reference') {
        this.showToast('Framing locked in Reference Mode. Switch to Explore to zoom.');
        return;
      }

      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
      const newZoom = Math.max(0.3, Math.min(500.0, this.renderer.targetZoom * zoomFactor));

      const mouseX = (e.clientX / window.innerWidth) * 2 - 1;
      const mouseY = 1 - (e.clientY / window.innerHeight) * 2;
      const aspect = this.canvas.width / this.canvas.height;
      const cx = (mouseX * aspect) / this.renderer.zoom + this.renderer.viewCenter[0];
      const cy = mouseY / this.renderer.zoom + this.renderer.viewCenter[1];

      if (zoomFactor > 1.0) {
        this.renderer.targetViewCenter[0] += (cx - this.renderer.targetViewCenter[0]) * 0.15;
        this.renderer.targetViewCenter[1] += (cy - this.renderer.targetViewCenter[1]) * 0.15;
      }

      this.renderer.targetZoom = newZoom;
    }, { passive: false });

    // Keyboard shortcuts
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT') return;
      const key = e.key.toLowerCase();
      if (key === '1') {
        this.setMode('reference');
      } else if (key === '2') {
        this.setMode('explore');
      } else if (key === '3') {
        this.randomize();
      } else if (key === 'h') {
        this.toggleUI();
      } else if (key === 'd') {
        this.toggleDebug();
      } else if (key === ' ') {
        e.preventDefault();
        if (this.mode === 'explore') this.togglePause();
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
      } else if (key === 'e') {
        this.openExportModal();
      } else if (key === 's') {
        this.openPresetModal();
      } else if (key === 'x') {
        const next = this.renderer.adaptive.mode === 'bruteforce' ? 'auto' : 'bruteforce';
        this.renderer.adaptive.setMode(next);
        const qualityBtns = document.querySelectorAll('.quality-btn');
        qualityBtns.forEach((b) => b.classList.toggle('active', b.dataset.tier === next));
        this.onResize();
      }
    });
  }

  setupUI() {
    // Mode Switcher buttons
    this.btnModeRef?.addEventListener('click', () => this.setMode('reference'));
    this.btnModeExp?.addEventListener('click', () => this.setMode('explore'));

    // Randomize direct button & dropdown toggle & styles
    document.getElementById('btn-randomize-action')?.addEventListener('click', () => this.randomize());

    const btnRandToggle = document.getElementById('btn-randomize-toggle');
    btnRandToggle?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.randomizeMenu?.classList.toggle('visible');
      if (this.paletteMenu) this.paletteMenu.classList.remove('visible');
    });

    document.querySelectorAll('.rnd-style-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const style = btn.dataset.style;
        this.randomize(style);
      });
    });

    // Palette dropdown toggle & selectors
    this.btnPaletteToggle?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.paletteMenu?.classList.toggle('visible');
      if (this.randomizeMenu) this.randomizeMenu.classList.remove('visible');
    });

    document.querySelectorAll('.palette-select-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const palKey = btn.dataset.pal;
        if (this.mode === 'reference' && palKey !== 'cobalt') {
          this.setMode('explore');
        }
        this.renderer.setPalette(palKey);
        document.querySelectorAll('.palette-select-btn').forEach(b => b.classList.toggle('active', b.dataset.pal === palKey));
        this.updateModeUI();
        this.closeDropdowns();
        this.showToast(`Palette: ${PALETTES[palKey]?.name || palKey}`);
      });
    });

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

    // Symmetry selector buttons
    const symmetryBtns = document.querySelectorAll('.sym-btn');
    symmetryBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const n = parseInt(btn.dataset.n, 10);
        if (this.mode === 'reference') {
          if (n === 16) return;
          this.setMode('explore');
        }
        this.math.setSymmetry(n);
        symmetryBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        this.renderer.startSymmetryTransition();
        this.renderer.adaptive.markInteraction();
      });
    });

    // Zoom buttons: locked in Reference mode to preserve camera framing intended for reference piece
    document.getElementById('btn-zoom-in')?.addEventListener('click', () => {
      if (this.mode === 'reference') {
        this.showToast('Framing locked in Reference Mode. Switch to Explore to zoom.');
        return;
      }
      this.renderer.adaptive.markInteraction();
      this.renderer.targetZoom = Math.min(500.0, this.renderer.targetZoom * 1.5);
    });
    document.getElementById('btn-zoom-out')?.addEventListener('click', () => {
      if (this.mode === 'reference') {
        this.showToast('Framing locked in Reference Mode. Switch to Explore to zoom.');
        return;
      }
      this.renderer.adaptive.markInteraction();
      this.renderer.targetZoom = Math.max(0.3, this.renderer.targetZoom / 1.5);
    });
    document.getElementById('btn-zoom-reset')?.addEventListener('click', () => {
      this.renderer.adaptive.markInteraction();
      this.renderer.targetZoom = 1.65;
      this.renderer.targetViewCenter = [0.0, 0.0];
    });

    // Main Control buttons
    document.getElementById('btn-pause')?.addEventListener('click', () => {
      if (this.mode === 'explore') this.togglePause();
    });
    document.getElementById('btn-reset')?.addEventListener('click', () => this.resetView());
    document.getElementById('btn-debug')?.addEventListener('click', () => this.toggleDebug());
    document.getElementById('btn-hide')?.addEventListener('click', () => this.toggleUI());
    document.getElementById('btn-bloom')?.addEventListener('click', () => this.toggleBloom());
    document.getElementById('btn-raw')?.addEventListener('click', () => this.toggleRawTrajectories());
    document.getElementById('btn-readout')?.addEventListener('click', () => this.toggleReadout());
    document.getElementById('btn-coeff')?.addEventListener('click', () => this.toggleCoeffDrawer());

    // Export & Presets Triggers
    document.getElementById('btn-export-trigger')?.addEventListener('click', () => this.openExportModal('standard'));
    document.getElementById('btn-refmaster-trigger')?.addEventListener('click', () => this.openExportModal('reference_master'));
    document.getElementById('btn-preset-trigger')?.addEventListener('click', () => this.openPresetModal());

    // Export Modal Controls
    document.getElementById('btn-export-close')?.addEventListener('click', () => this.closeExportModal());
    document.getElementById('btn-export-cancel')?.addEventListener('click', () => this.closeExportModal());
    document.getElementById('btn-export-start')?.addEventListener('click', () => this.startExport());

    document.getElementById('tab-export-standard')?.addEventListener('click', () => this.setExportType('standard'));
    document.getElementById('tab-export-refmaster')?.addEventListener('click', () => this.setExportType('reference_master'));

    document.querySelectorAll('.export-res-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.export-res-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const w = btn.dataset.w;
        const h = btn.dataset.h;
        if (w === 'viewport') {
          this.exportWidth = this.canvas.width;
          this.exportHeight = this.canvas.height;
        } else {
          this.exportWidth = parseInt(w, 10);
          this.exportHeight = parseInt(h, 10);
        }
      });
    });

    document.querySelectorAll('.export-pass-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.export-pass-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.exportPasses = parseInt(btn.dataset.passes, 10);
      });
    });

    document.querySelectorAll('.refmaster-pass-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.refmaster-pass-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.refMasterPasses = parseInt(btn.dataset.passes, 10);
      });
    });

    // Presets Modal Controls
    document.getElementById('btn-preset-close')?.addEventListener('click', () => this.closePresetModal());
    document.getElementById('btn-preset-done')?.addEventListener('click', () => this.closePresetModal());
    document.getElementById('btn-preset-save')?.addEventListener('click', () => this.saveUserPreset());
    document.getElementById('btn-preset-copy')?.addEventListener('click', () => this.copyPresetJSON());

    const fileInput = document.getElementById('preset-file-input');
    fileInput?.addEventListener('change', (e) => {
      const file = e.target.files?.[0];
      if (file) this.importPresetFile(file);
    });

    // Coefficient Sliders
    const sliderARe = document.getElementById('slider-a-re');
    const sliderBIm = document.getElementById('slider-b-im');
    const sliderCRe = document.getElementById('slider-c-re');
    const sliderDIm = document.getElementById('slider-d-im');

    sliderARe?.addEventListener('input', (e) => {
      if (this.mode === 'reference') return;
      this.renderer.adaptive.markInteraction();
      const v = parseFloat(e.target.value);
      document.getElementById('lbl-a-re').innerText = v.toFixed(2);
      this.math.setCoefficientOffset('a', v, 0);
    });
    sliderBIm?.addEventListener('input', (e) => {
      if (this.mode === 'reference') return;
      this.renderer.adaptive.markInteraction();
      const v = parseFloat(e.target.value);
      document.getElementById('lbl-b-im').innerText = v.toFixed(2);
      this.math.setCoefficientOffset('b', 0, v);
    });
    sliderCRe?.addEventListener('input', (e) => {
      if (this.mode === 'reference') return;
      this.renderer.adaptive.markInteraction();
      const v = parseFloat(e.target.value);
      document.getElementById('lbl-c-re').innerText = v.toFixed(2);
      this.math.setCoefficientOffset('c', v, 0);
    });
    sliderDIm?.addEventListener('input', (e) => {
      if (this.mode === 'reference') return;
      this.renderer.adaptive.markInteraction();
      const v = parseFloat(e.target.value);
      document.getElementById('lbl-d-im').innerText = v.toFixed(2);
      this.math.setCoefficientOffset('d', 0, v);
    });

    document.getElementById('btn-reset-coeffs')?.addEventListener('click', () => {
      if (this.mode === 'reference') return;
      this.renderer.adaptive.markInteraction();
      this.resetSliderDisplay();
      this.math.setCoefficientOffset('a', 0, 0);
      this.math.setCoefficientOffset('b', 0, 0);
      this.math.setCoefficientOffset('c', 0, 0);
      this.math.setCoefficientOffset('d', 0, 0);
    });
  }

  // --- Export Features ---
  openExportModal(type = 'standard') {
    this.setExportType(type);
    if (this.exportModal) this.exportModal.classList.add('visible');
  }

  setExportType(type) {
    this.exportType = type;
    const tabStd = document.getElementById('tab-export-standard');
    const tabRef = document.getElementById('tab-export-refmaster');
    const panelStd = document.getElementById('export-standard-panel');
    const panelRef = document.getElementById('export-refmaster-panel');
    const btnStart = document.getElementById('btn-export-start');

    if (type === 'reference_master') {
      if (tabStd) tabStd.classList.remove('active');
      if (tabRef) tabRef.classList.add('active');
      if (panelStd) panelStd.style.display = 'none';
      if (panelRef) panelRef.style.display = 'block';
      if (btnStart) btnStart.innerText = 'Develop Reference Master';
    } else {
      if (tabStd) tabStd.classList.add('active');
      if (tabRef) tabRef.classList.remove('active');
      if (panelStd) panelStd.style.display = 'block';
      if (panelRef) panelRef.style.display = 'none';
      if (btnStart) btnStart.innerText = 'Download PNG';
    }
  }

  closeExportModal() {
    if (this.isExporting) return;
    if (this.exportModal) this.exportModal.classList.remove('visible');
    const progArea = document.getElementById('export-progress-area');
    if (progArea) progArea.style.display = 'none';
  }

  showExportDisplayHold() {
    clearTimeout(this._holdRemovalTimeout);
    this._holdRemovalTimeout = null;
    this._pendingHoldRemoval = false;
    try {
      if (this.renderer && typeof this.renderer.presentCurrentFrame === 'function') {
        this.renderer.presentCurrentFrame();
      }
      let holdCanvas = document.getElementById('export-display-hold');
      if (!holdCanvas && this.canvas && this.canvas.parentElement) {
        holdCanvas = document.createElement('canvas');
        holdCanvas.id = 'export-display-hold';
        holdCanvas.style.cssText = 'position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:1; display:none;';
        this.canvas.parentElement.insertBefore(holdCanvas, this.canvas.nextSibling);
      }
      if (holdCanvas && this.canvas && this.canvas.width > 0 && this.canvas.height > 0) {
        holdCanvas.width = this.canvas.width;
        holdCanvas.height = this.canvas.height;
        const ctx = holdCanvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(this.canvas, 0, 0);
          holdCanvas.style.display = 'block';
        }
      }
      this.displayHoldActive = true;
    } catch (err) {
      console.warn('Failed to activate export display hold:', err);
    }
  }

  scheduleDisplayHoldRemoval() {
    if (this.contextLost || this.renderer.isContextUnavailable()) {
      this.hideExportDisplayHold();
      return;
    }
    this._pendingHoldRemoval = true;
    clearTimeout(this._holdRemovalTimeout);
    this._holdRemovalTimeout = setTimeout(() => {
      if (this.displayHoldActive) {
        this.hideExportDisplayHold();
      }
    }, 500);
  }

  hideExportDisplayHold() {
    clearTimeout(this._holdRemovalTimeout);
    this._holdRemovalTimeout = null;
    const holdCanvas = document.getElementById('export-display-hold');
    if (holdCanvas) {
      holdCanvas.style.display = 'none';
      const ctx = holdCanvas.getContext('2d');
      if (ctx) {
        ctx.clearRect(0, 0, holdCanvas.width, holdCanvas.height);
      }
    }
    this.displayHoldActive = false;
    this._pendingHoldRemoval = false;
  }

  async startExport() {
    if (this.isExporting || this.contextLost || this.renderer.isContextUnavailable()) return;
    this._exportTask = this.runExport();
    return this._exportTask;
  }

  async runExport() {
    this.isExporting = true;

    // Ensure coefficient readout remains populated with last valid values during export
    this.updateReadout();

    // 1. Capture current visible artwork and display as temporary visual overlay over WebGL canvas
    this.showExportDisplayHold();

    const progArea = document.getElementById('export-progress-area');
    const statusLbl = document.getElementById('export-status-label');
    const statusPct = document.getElementById('export-status-pct');
    const progFill = document.getElementById('export-progress-fill');
    const btnStart = document.getElementById('btn-export-start');
    const btnCancel = document.getElementById('btn-export-cancel');

    if (progArea) progArea.style.display = 'block';
    if (statusLbl) statusLbl.innerText = 'Initializing...';
    if (statusPct) statusPct.innerText = '0%';
    if (progFill) progFill.style.width = '0%';
    if (btnStart) btnStart.disabled = true;
    if (btnCancel) btnCancel.disabled = true;

    // REFERENCE MASTER EXPORT BRANCH
    if (this.exportType === 'reference_master') {
      // 1. Snapshot complete session state to guarantee 100% preservation
      const sessionState = {
        mode: this.mode,
        mathMode: this.math.mode,
        n: this.math.n,
        activeMorphology: this.math.activeMorphology,
        evolving: this.math.evolving,
        time: this.math.time,
        baseA: this.math.baseA.clone(),
        baseB: this.math.baseB.clone(),
        baseC: this.math.baseC.clone(),
        baseD: this.math.baseD.clone(),
        userOffsetA: this.math.userOffsetA.clone(),
        userOffsetB: this.math.userOffsetB.clone(),
        userOffsetC: this.math.userOffsetC.clone(),
        userOffsetD: this.math.userOffsetD.clone(),
        pointerTarget: this.math.pointerTarget.clone(),
        pointerCurrent: this.math.pointerCurrent.clone(),
        shockMag: this.math.shockMag,
        shockPhase: this.math.shockPhase,
        pointerPerturbationEnabled: this.math.pointerPerturbationEnabled,
        shockEnabled: this.math.shockEnabled,
        a: this.math.a.clone(),
        b: this.math.b.clone(),
        c: this.math.c.clone(),
        d: this.math.d.clone(),
        zoom: this.renderer.zoom,
        targetZoom: this.renderer.targetZoom,
        viewCenter: [...this.renderer.viewCenter],
        targetViewCenter: [...this.renderer.targetViewCenter],
        activePalette: this.renderer.activePalette,
        viewMode: this.renderer.viewMode,
        gain: this.renderer.gain,
        bloomEnabled: this.renderer.bloomEnabled,
        tier: this.renderer.adaptive.currentTier,
        manualTier: this.renderer.adaptive.manualTier
      };

      // Explicitly enforce canonical reference math on active math system prior to export
      this.math.pointerTarget.r = 0; this.math.pointerTarget.i = 0;
      this.math.pointerCurrent.r = 0; this.math.pointerCurrent.i = 0;
      this.math.shockMag = 0.0;
      this.math.shockPhase = 0.0;
      this.math.userOffsetA.r = 0; this.math.userOffsetA.i = 0;
      this.math.userOffsetB.r = 0; this.math.userOffsetB.i = 0;
      this.math.userOffsetC.r = 0; this.math.userOffsetC.i = 0;
      this.math.userOffsetD.r = 0; this.math.userOffsetD.i = 0;
      this.math.evolving = false;
      this.math.time = 0.0;
      this.math.mode = 'reference';
      this.math.n = 16;
      this.math.baseA.r = -0.755; this.math.baseA.i = 0.330;
      this.math.baseB.r = -0.376; this.math.baseB.i = 0.026;
      this.math.baseC.r = 6.401; this.math.baseC.i = 0.803;
      this.math.baseD.r = 1.520; this.math.baseD.i = 0.840;
      this.math.a.r = -0.755; this.math.a.i = 0.330;
      this.math.b.r = -0.376; this.math.b.i = 0.026;
      this.math.c.r = 6.401; this.math.c.i = 0.803;
      this.math.d.r = 1.520; this.math.d.i = 0.840;
      this.math.updateRootsOfUnity();
      this.math.computeTransforms();

      const passes = this.refMasterPasses || 120;
      const filename = 'mobius-reference-master-4096.png';

      try {
        const blob = await this.renderer.exportReferenceMaster(this.math, {
          accumPasses: passes,
          filename,
          onProgress: (pct, msg) => {
            if (statusLbl) statusLbl.innerText = msg;
            if (statusPct) statusPct.innerText = `${pct}%`;
            if (progFill) progFill.style.width = `${pct}%`;
          }
        });
        this.showToast('Reference Master 4096×4096 exported successfully!');
        setTimeout(() => {
          if (btnStart) btnStart.disabled = false;
          if (btnCancel) btnCancel.disabled = false;
          this.closeExportModal();
        }, 700);
        return blob;
      } catch (err) {
        console.error('Reference Master Export error:', err);
        if (err?.name === 'WebGLContextLostError') this._exportInterrupted = true;
        const errMsg = err?.message || 'Export failed';
        if (statusLbl) statusLbl.innerText = 'Export failed: ' + errMsg;
        this.showToast('Reference Master Export failed: ' + errMsg);
        if (btnStart) btnStart.disabled = false;
        if (btnCancel) btnCancel.disabled = false;
      } finally {
        // Complete session state restoration
        this.mode = sessionState.mode;
        this.math.mode = sessionState.mathMode;
        this.math.n = sessionState.n;
        this.math.activeMorphology = sessionState.activeMorphology;
        this.math.evolving = sessionState.evolving;
        this.math.time = sessionState.time;
        this.math.baseA = sessionState.baseA;
        this.math.baseB = sessionState.baseB;
        this.math.baseC = sessionState.baseC;
        this.math.baseD = sessionState.baseD;
        this.math.userOffsetA = sessionState.userOffsetA;
        this.math.userOffsetB = sessionState.userOffsetB;
        this.math.userOffsetC = sessionState.userOffsetC;
        this.math.userOffsetD = sessionState.userOffsetD;
        this.math.pointerTarget = sessionState.pointerTarget;
        this.math.pointerCurrent = sessionState.pointerCurrent;
        this.math.shockMag = sessionState.shockMag;
        this.math.shockPhase = sessionState.shockPhase;
        this.math.pointerPerturbationEnabled = sessionState.pointerPerturbationEnabled;
        this.math.shockEnabled = sessionState.shockEnabled;
        this.math.a = sessionState.a;
        this.math.b = sessionState.b;
        this.math.c = sessionState.c;
        this.math.d = sessionState.d;
        this.math.updateRootsOfUnity();
        this.math.computeTransforms();

        this.renderer.zoom = sessionState.zoom;
        this.renderer.targetZoom = sessionState.targetZoom;
        this.renderer.viewCenter = sessionState.viewCenter;
        this.renderer.targetViewCenter = sessionState.targetViewCenter;
        this.renderer.activePalette = sessionState.activePalette;
        this.renderer.viewMode = sessionState.viewMode;
        this.renderer.gain = sessionState.gain;
        this.renderer.bloomEnabled = sessionState.bloomEnabled;
        this.renderer.adaptive.manualTier = sessionState.manualTier;
        this.renderer.adaptive.currentTier = sessionState.tier;

        this.updateModeUI();
        this.updateReadout();
        this.updateSliderInputs();
        this.isExporting = false;
        this.scheduleDisplayHoldRemoval();
      }
      return;
    }

    // STANDARD EXPORT BRANCH
    const width = this.exportWidth || 3840;
    const height = this.exportHeight || 2160;
    const passes = this.exportPasses || 60;
    const modeTag = this.mode === 'reference' ? 'simone_conradi_reference' : 'mobius_explore';
    const filename = `${modeTag}_${width}x${height}.png`;

    try {
      const blob = await this.renderer.exportPNG(this.math, {
        width,
        height,
        accumFrames: passes,
        filename,
        onProgress: (pct, msg) => {
          if (statusLbl) statusLbl.innerText = msg;
          if (statusPct) statusPct.innerText = `${pct}%`;
          if (progFill) progFill.style.width = `${pct}%`;
        }
      });
      this.showToast(`Successfully exported ${width}×${height} PNG!`);
      setTimeout(() => {
        if (btnStart) btnStart.disabled = false;
        if (btnCancel) btnCancel.disabled = false;
        this.closeExportModal();
      }, 700);
      return blob;
    } catch (err) {
      console.error('Export error:', err);
      if (err?.name === 'WebGLContextLostError') this._exportInterrupted = true;
      const errMsg = err?.message || 'Export failed';
      if (statusLbl) statusLbl.innerText = 'Export failed: ' + errMsg;
      this.showToast('Export failed: ' + errMsg);
      if (btnStart) btnStart.disabled = false;
      if (btnCancel) btnCancel.disabled = false;
    } finally {
      this.updateReadout();
      this.isExporting = false;
      this.scheduleDisplayHoldRemoval();
    }
  }

  // --- Preset Features ---
  openPresetModal() {
    this.populateCuratedPresets();
    this.renderUserPresets();
    if (this.presetModal) this.presetModal.classList.add('visible');
  }

  closePresetModal() {
    if (this.presetModal) this.presetModal.classList.remove('visible');
  }

  populateCuratedPresets() {
    const list = document.getElementById('curated-presets-list');
    if (!list) return;
    list.innerHTML = '';
    CURATED_PRESETS.forEach(p => {
      const btn = document.createElement('button');
      btn.style.cssText = 'display:flex; flex-direction:column; align-items:flex-start; padding:6px 10px; background:rgba(20,40,80,0.5); border:1px solid rgba(40,90,160,0.3); border-radius:6px;';
      btn.innerHTML = `
        <div style="font-weight:600; color:#e2f0ff; font-size:10.5px;">${p.name}</div>
        <div style="font-size:9px; color:#6482a8; margin-top:2px;">${p.description}</div>
      `;
      btn.addEventListener('click', () => {
        this.loadPresetObject(p);
        this.closePresetModal();
      });
      list.appendChild(btn);
    });
  }

  getUserPresets() {
    try {
      const saved = localStorage.getItem('mobius_custom_presets');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  }

  renderUserPresets() {
    const list = document.getElementById('user-presets-list');
    if (!list) return;
    const presets = this.getUserPresets();
    if (presets.length === 0) {
      list.innerHTML = '<div style="font-size:10px; color:#5577a3; padding:4px;">No custom presets saved yet.</div>';
      return;
    }
    list.innerHTML = '';
    presets.forEach((p, idx) => {
      const row = document.createElement('div');
      row.style.cssText = 'display:flex; justify-content:space-between; align-items:center; background:rgba(10,24,48,0.5); border:1px solid rgba(40,80,140,0.25); border-radius:6px; padding:4px 8px;';
      row.innerHTML = `
        <div style="font-size:10.5px; color:#c0daf8;">${p.name || 'Unnamed Preset'} <span style="font-size:9px; color:#5577a3;">(n=${p.symmetry})</span></div>
        <div style="display:flex; gap:4px;">
          <button class="load-user-preset" style="padding:2px 8px; font-size:9.5px; background:rgba(30,120,255,0.3);">Load</button>
          <button class="del-user-preset" style="padding:2px 6px; font-size:9.5px; color:#f87171;">✕</button>
        </div>
      `;
      row.querySelector('.load-user-preset')?.addEventListener('click', () => {
        this.loadPresetObject(p);
        this.closePresetModal();
      });
      row.querySelector('.del-user-preset')?.addEventListener('click', () => {
        this.deleteUserPreset(idx);
      });
      list.appendChild(row);
    });
  }

  saveUserPreset() {
    const input = document.getElementById('preset-name-input');
    const name = input?.value.trim() || `Preset ${new Date().toLocaleTimeString()}`;
    const preset = this.getPresetObject(name);

    // Save to localStorage
    const existing = this.getUserPresets();
    existing.unshift(preset);
    try {
      localStorage.setItem('mobius_custom_presets', JSON.stringify(existing.slice(0, 20)));
    } catch (e) {
      console.warn('LocalStorage save error:', e);
    }
    this.renderUserPresets();

    // Also download JSON
    const jsonStr = JSON.stringify(preset, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name.replace(/\s+/g, '_').toLowerCase()}.mobius.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 5000);

    if (input) input.value = '';
    this.showToast(`Saved preset: "${name}"`);
  }

  deleteUserPreset(idx) {
    const existing = this.getUserPresets();
    existing.splice(idx, 1);
    try {
      localStorage.setItem('mobius_custom_presets', JSON.stringify(existing));
    } catch (e) {}
    this.renderUserPresets();
  }

  getPresetObject(name = 'Custom Mobius Organism') {
    return {
      name,
      timestamp: Date.now(),
      version: '1.0',
      mode: this.mode,
      symmetry: this.math.n,
      coefficients: {
        a: { r: this.math.baseA.r, i: this.math.baseA.i },
        b: { r: this.math.baseB.r, i: this.math.baseB.i },
        c: { r: this.math.baseC.r, i: this.math.baseC.i },
        d: { r: this.math.baseD.r, i: this.math.baseD.i }
      },
      userOffsets: {
        a: { r: this.math.userOffsetA.r, i: this.math.userOffsetA.i },
        b: { r: this.math.userOffsetB.r, i: this.math.userOffsetB.i },
        c: { r: this.math.userOffsetC.r, i: this.math.userOffsetC.i },
        d: { r: this.math.userOffsetD.r, i: this.math.userOffsetD.i }
      },
      camera: {
        zoom: this.renderer.zoom,
        center: [...this.renderer.viewCenter]
      },
      palette: this.renderer.activePalette,
      drift: {
        evolving: this.math.evolving,
        time: this.math.time
      },
      rendering: {
        bloom: this.renderer.bloomEnabled,
        viewMode: this.renderer.viewMode,
        tier: this.renderer.adaptive.mode
      }
    };
  }

  loadPresetObject(preset) {
    if (!preset) return;
    const targetMode = preset.mode === 'reference' ? 'reference' : 'explore';

    if (targetMode === 'reference') {
      // Reference Mode wins: canonical parameters are inviolable.
      // Load non-mathematical safe visual state if present
      if (preset.rendering) {
        if (preset.rendering.bloom !== undefined) this.renderer.bloomEnabled = !!preset.rendering.bloom;
        if (preset.rendering.viewMode !== undefined) this.renderer.viewMode = preset.rendering.viewMode;
        if (preset.rendering.tier) this.renderer.adaptive.setMode(preset.rendering.tier);
      }
      // Authoritative Reference reset establishes canonical math, framing, palette, sliders, and UI state LAST
      this.setMode('reference');
      this.showToast(`Loaded preset: ${preset.name || 'Simone Conradi (Reference Artwork)'}`);
      return;
    }

    // MODE: EXPLORE
    this.setMode('explore');

    // Restore mathematical parameters (coefficients, symmetry, offsets, drift)
    this.math.fromJSON(preset);

    // If preset specified symmetry, ensure roots of unity & transition
    if (preset.symmetry || preset.n) {
      const sym = preset.symmetry || preset.n;
      this.math.setSymmetry(sym);
      this.renderer.startSymmetryTransition();
    }

    // Explicitly restore drift state if provided
    if (preset.drift && preset.drift.evolving !== undefined) {
      this.math.evolving = !!preset.drift.evolving;
    }

    if (preset.palette) {
      this.renderer.setPalette(preset.palette);
    }
    if (preset.camera) {
      this.renderer.zoom = preset.camera.zoom !== undefined ? preset.camera.zoom : 1.65;
      this.renderer.targetZoom = this.renderer.zoom;
      this.renderer.viewCenter = preset.camera.center ? [...preset.camera.center] : [0, 0];
      this.renderer.targetViewCenter = [...this.renderer.viewCenter];
    }
    if (preset.rendering) {
      if (preset.rendering.bloom !== undefined) this.renderer.bloomEnabled = !!preset.rendering.bloom;
      if (preset.rendering.viewMode !== undefined) this.renderer.viewMode = preset.rendering.viewMode;
      if (preset.rendering.tier) this.renderer.adaptive.setMode(preset.rendering.tier);
    }

    // Update UI sliders to reflect restored user offsets
    this.updateSliderInputs();

    this.renderer.clearAccumulation();
    this.updateModeUI();
    this.updateReadout();
    this.showToast(`Loaded preset: ${preset.name || 'Unnamed'}`);
  }

  copyPresetJSON() {
    const preset = this.getPresetObject();
    const str = JSON.stringify(preset, null, 2);
    if (navigator.clipboard) {
      navigator.clipboard.writeText(str).then(() => {
        this.showToast('Preset JSON copied to clipboard!');
      });
    } else {
      this.showToast('Clipboard access unavailable.');
    }
  }

  importPresetFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        this.loadPresetObject(data);
        this.closePresetModal();
      } catch (err) {
        this.showToast('Failed to parse preset JSON file.');
      }
    };
    reader.readAsText(file);
  }

  togglePause() {
    this.math.evolving = !this.math.evolving;
    const btn = document.getElementById('btn-pause');
    if (btn) {
      btn.innerText = this.math.evolving ? 'Pause' : 'Resume';
      btn.classList.toggle('active', !this.math.evolving);
    }
    if (!this.math.evolving) {
      this.renderer.clearAccumulation();
    }
  }

  resetView() {
    if (this.mode === 'reference') {
      this.setMode('reference');
    } else {
      this.math.reset();
      this.renderer.targetZoom = 1.65;
      this.renderer.targetViewCenter = [0.0, 0.0];
      this.renderer.clearAccumulation();
      this.resetSliderDisplay();
    }
  }

  toggleUI() {
    this.uiHidden = !this.uiHidden;
    this.uiContainer?.classList.toggle('hidden', this.uiHidden);
    document.getElementById('hint-unhide')?.classList.toggle('visible', this.uiHidden);
  }

  toggleReadout() {
    this.readoutVisible = !this.readoutVisible;
    this.readoutEl?.classList.toggle('collapsed', !this.readoutVisible);
    document.getElementById('btn-readout')?.classList.toggle('active', this.readoutVisible);
  }

  toggleCoeffDrawer() {
    this.coeffDrawerVisible = !this.coeffDrawerVisible;
    this.coeffDrawer?.classList.toggle('visible', this.coeffDrawerVisible);
    document.getElementById('btn-coeff')?.classList.toggle('active', this.coeffDrawerVisible);
  }

  toggleDebug() {
    this.debugMode = !this.debugMode;
    this.debugOverlay?.classList.toggle('visible', this.debugMode);
    document.getElementById('btn-debug')?.classList.toggle('active', this.debugMode);
  }

  toggleBloom() {
    this.renderer.bloomEnabled = !this.renderer.bloomEnabled;
    this.renderer.viewMode = this.renderer.bloomEnabled ? 0 : 1;
    const btn = document.getElementById('btn-bloom');
    if (btn) {
      btn.innerText = `Bloom: ${this.renderer.bloomEnabled ? 'ON' : 'OFF'}`;
      btn.classList.toggle('active', this.renderer.bloomEnabled);
    }
    document.getElementById('btn-raw')?.classList.remove('active');
  }

  toggleRawTrajectories() {
    if (this.renderer.viewMode === 2) {
      this.renderer.viewMode = this.renderer.bloomEnabled ? 0 : 1;
    } else {
      this.renderer.viewMode = 2;
    }
    const btn = document.getElementById('btn-raw');
    if (btn) {
      btn.innerText = `Raw: ${this.renderer.viewMode === 2 ? 'ON' : 'OFF'}`;
      btn.classList.toggle('active', this.renderer.viewMode === 2);
    }
  }

  onContextLost(event) {
    event.preventDefault();
    if (this.contextLost) return;
    this.contextLost = true;
    this._exportInterrupted = this._exportInterrupted || this.isExporting;
    this.renderer.handleContextLoss();
    this.hideExportDisplayHold();
    this.showToast('Graphics context lost — recovering…');
  }

  async onContextRestored() {
    if (!this.contextLost || this._restoringContext) return;
    this._restoringContext = true;
    try {
      // Export finally blocks restore the JS session (especially Master from Explore).
      // Let them finish before reading state or replacing the retired renderer.
      await this._exportTask;
      const old = this.renderer;
      if (old.gl.isContextLost()) return;
      const state = {};
      for (const key of ['zoom', 'targetZoom', 'viewCenter', 'targetViewCenter',
        'activePalette', 'bloomEnabled', 'viewMode', 'gain', 'showRawTrajectories',
        'particlesOverride', 'stepsOverride', 'numParticles', 'stepsPerFrame',
        'persistence', 'currentPersistence']) {
        state[key] = Array.isArray(old[key]) ? [...old[key]] : old[key];
      }
      // Constructor recreates shaders, buffers, VAOs, FBOs, textures and query pool.
      // Never copy GL handles, timing measurements or accumulation from the old instance.
      const rebuilt = new MobiusRenderer(this.canvas);
      rebuilt.setParticleCount(state.numParticles);
      Object.assign(rebuilt, state);
      rebuilt.adaptive.setMode(old.adaptive.mode);
      rebuilt.adaptive.currentTierKey = old.adaptive.currentTierKey;
      rebuilt.adaptive.currentTier = old.adaptive.currentTier;
      rebuilt.adaptive.manualTier = old.adaptive.manualTier;
      this.renderer = rebuilt;
      window.__renderer = rebuilt;
      window.__profiler = rebuilt.profiler;
      if (this.mode === 'reference') this.setMode('reference');
      this.contextLost = false;
      this.lastTime = this.lastSimTime = performance.now();
      this.lastRafTimestamp = 0;
      this.rafDeltas = [];
      this.onResize();
      rebuilt.clearAccumulation();
      this.hideExportDisplayHold();
      this.showToast(this._exportInterrupted
        ? 'Export interrupted because the graphics context was lost. The renderer recovered; please try again.'
        : 'Graphics context restored.');
      this._exportInterrupted = false;
      this._exportTask = null;
      // animate() already owns the single recursive RAF chain. Do not start another.
    } catch (error) {
      console.error('Graphics recovery failed:', error);
      this.contextLost = true;
      this.showToast('Graphics recovery failed. Waiting for graphics context restoration.');
    } finally {
      this._restoringContext = false;
    }
  }

  onResize() {
    if (this.contextLost) return;
    if (typeof window === 'undefined' || window.innerWidth <= 0 || window.innerHeight <= 0) return;
    const dpr = this.customDpr || this.renderer.adaptive.getDpr();
    const w = Math.floor(window.innerWidth * dpr);
    const h = Math.floor(window.innerHeight * dpr);
    this.renderer.resize(w, h);
  }

  animate(currentTime) {
    requestAnimationFrame(this.animate);

    if (this.contextLost || this.renderer.isContextUnavailable() || this.isTabHidden || this.isExporting) {
      this.lastTime = currentTime;
      return;
    }

    // Refresh rate tracking
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

    // High-refresh display power capping (~60 Hz)
    const isCapture = typeof window !== 'undefined' && window.location.search.includes('capture=1');
    if (!isCapture && this.isHighRefresh) {
      const simDt = currentTime - this.lastSimTime;
      if (simDt < 15.0) return;
    }
    this.lastSimTime = currentTime;

    const dt = Math.min(0.05, (currentTime - this.lastTime) / 1000);
    this.lastTime = currentTime;

    // Check dynamic DPR resize
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

    // If display hold was active during export, remove it after the first valid onscreen render
    if (this._pendingHoldRemoval) {
      this._pendingHoldRemoval = false;
      this.hideExportDisplayHold();
    }

    // Update Live Equation Readout
    if (this.valA) this.valA.innerText = this.math.a.format(3);
    if (this.valB) this.valB.innerText = this.math.b.format(3);
    if (this.valC) this.valC.innerText = this.math.c.format(3);
    if (this.valD) this.valD.innerText = this.math.d.format(3);
    if (this.valN) this.valN.innerText = this.math.n;

    // Update Profiler Overlay
    if (this.debugMode) {
      const m = this.renderer.profiler.metrics;
      const status = this.renderer.adaptive.getStatus();
      const isBrute = status.mode === 'bruteforce' || status.tierKey === 'BRUTEFORCE';

      if (this.dbgBruteBanner) this.dbgBruteBanner.style.display = isBrute ? 'block' : 'none';
      if (this.dbgMode) this.dbgMode.innerText = status.modeDisplay;
      if (this.dbgTier) {
        this.dbgTier.innerHTML = isBrute
          ? '<span style="color:#ff5577;font-weight:bold;">BRUTE FORCE</span>'
          : status.tierDisplay;
      }
      if (this.dbgParticles) {
        this.dbgParticles.innerText = isBrute ? '589,824' : `${this.renderer.numParticles.toLocaleString()}`;
      }
      if (this.dbgSteps) this.dbgSteps.innerText = `${this.renderer.stepsPerFrame}`;
      if (this.dbgIters) {
        const deposits = this.renderer.numParticles * this.renderer.stepsPerFrame;
        this.dbgIters.innerText = isBrute ? '9,437,184 deposits/frame' : `${deposits.toLocaleString()} deposits/frame`;
      }
      if (this.dbgBudget) this.dbgBudget.innerText = isBrute ? 'Enthusiast (Unbounded)' : `${status.targetBudgetMs.toFixed(1)} ms`;
      if (this.dbgHeadroom) this.dbgHeadroom.innerText = status.headroomPercent !== null ? `${status.headroomPercent}%` : '--%';
      if (this.dbgFps) this.dbgFps.innerText = `${m.fps} FPS (${m.fps1Low} 1% low) [${this.refreshRate}Hz display]`;
      if (this.dbgFrameTime) this.dbgFrameTime.innerText = `${m.frameMs.toFixed(1)} ms`;
      if (this.dbgCpu) this.dbgCpu.innerText = `${m.cpuMs.toFixed(2)} ms (JS: ${m.jsUpdateMs.toFixed(2)}ms)`;

      if (this.dbgGpu) {
        if (status.timerQueryState === 'disjoint') {
          this.dbgGpu.innerText = `${status.gpuEma ? status.gpuEma.toFixed(2) + ' ms' : '-- ms'} (disjoint discarded)`;
        } else if (status.timerQueryState === 'unavailable') {
          this.dbgGpu.innerText = `${status.gpuEma ? status.gpuEma.toFixed(2) + ' ms' : '-- ms'} (CPU fallback)`;
        } else if (status.timerQueryState === 'pending') {
          this.dbgGpu.innerText = `Calibrating queries...`;
        } else if (status.gpuEma !== null) {
          this.dbgGpu.innerText = `${status.gpuEma.toFixed(2)} ms (EMA)`;
        } else if (m.gpuSupported && m.gpuMs !== null) {
          this.dbgGpu.innerText = `${m.gpuMs.toFixed(2)} ms`;
        } else {
          this.dbgGpu.innerText = `N/A (timer query unavail)`;
        }
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
    document.body.setAttribute('data-mode', this.mode);

    // Capture hook for automated test harness
    if (window.location.search.includes('capture=1') && !window._captured) {
      window._captured = true;
      const params = new URLSearchParams(window.location.search);
      const zFactor = params.has('zoom') ? parseFloat(params.get('zoom')) : 1.0;
      const numFrames = params.has('raw') ? 25 : (zFactor > 50.0 ? 120 : (zFactor > 10.0 ? 90 : 60));
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

if (document.readyState === 'loading') {
  window.addEventListener('DOMContentLoaded', () => {
    if (!window.app) window.app = new App();
  });
} else {
  if (!window.app) window.app = new App();
}
