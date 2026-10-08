/**
 * Production Adaptive Quality & Power-Efficient Workload Manager
 *
 * Implements measured multi-tier adaptive rendering:
 * - POTATO:    40,000 particles x 4 IFS steps (~160k deposits/frame)
 * - LOW:       75,000 particles x 8 IFS steps (~600k deposits/frame)
 * - STANDARD: 150,000 particles x 8 IFS steps (~1.20M deposits/frame)
 * - HIGH:     250,000 particles x 8 IFS steps (~2.00M deposits/frame)
 * - EXTREME:  589,824 particles x 12-16 steps (Manual/Screenshot/Debug only)
 *
 * Key behaviors:
 * 1. Conservative startup (starts at Low: 75k x 8, invisible calibration).
 * 2. Real GPU frame time EMA driven by EXT_disjoint_timer_query_webgl2.
 * 3. Hysteresis (slow upgrade with sustained headroom, fast downgrade).
 * 4. Interaction mode (temporarily reduced workload during pan/zoom/click).
 * 5. Bounded deep zoom deposit budget (particles scale down as steps scale up).
 * 6. Controlled DPR (maximum 1.5, saving GPU fillrate).
 * 7. Power efficiency (maintains 20-30% GPU headroom, avoids GPU saturation).
 */

export const QUALITY_TIERS = {
  POTATO: {
    id: 'potato',
    name: 'POTATO',
    label: 'Potato',
    particles: 40000,
    steps: 4,
    depositBudget: 160000,
    maxDpr: 1.0,
    targetBudgetMs: 12.0
  },
  LOW: {
    id: 'low',
    name: 'LOW',
    label: 'Low',
    particles: 75000,
    steps: 8,
    depositBudget: 600000,
    maxDpr: 1.25,
    targetBudgetMs: 12.0
  },
  STANDARD: {
    id: 'standard',
    name: 'STANDARD',
    label: 'Standard',
    particles: 150000,
    steps: 8,
    depositBudget: 1200000,
    maxDpr: 1.5,
    targetBudgetMs: 12.0
  },
  HIGH: {
    id: 'high',
    name: 'HIGH',
    label: 'High',
    particles: 250000,
    steps: 8,
    depositBudget: 2000000,
    maxDpr: 1.5,
    targetBudgetMs: 11.0
  },
  EXTREME: {
    id: 'extreme',
    name: 'EXTREME',
    label: 'Extreme',
    particles: 589824,
    steps: 12,
    depositBudget: 7077888,
    maxDpr: 1.5,
    targetBudgetMs: 16.0
  }
};

export class AdaptiveManager {
  constructor(renderer) {
    this.renderer = renderer;

    // Operating mode: 'auto' (default), 'low', 'standard', 'high', 'potato', 'extreme'
    this.mode = 'auto';

    // Settled tier (current active tier)
    this.currentTierKey = 'LOW';
    this.currentTier = QUALITY_TIERS.LOW;

    // Adaptive state machine: 'calibrating', 'settled', 'cooldown'
    this.state = 'calibrating';
    this.calibrationFrames = 0;
    this.calibrationTargetFrames = 45; // ~0.75s initial invisible calibration

    // Timing & EMA metrics
    this.gpuEma = 0.0;
    this.gpuEmaAlpha = 0.08; // Smooth exponential moving average
    this.hasMeasuredGpu = false;
    this.effectiveFpsEma = 60.0;

    // Hysteresis counters
    this.sustainedHeadroomFrames = 0;
    this.overBudgetFrames = 0;
    this.severeOverBudgetFrames = 0;
    this.cooldownFrames = 0;
    this.minCooldown = 120; // 2.0s cooldown between upgrades

    // Interaction tracking
    this.lastInteractionTime = 0;
    this.isInteracting = false;
    this.interactionCooldownMs = 350;

    // Accumulation stationary tracking
    this.stationaryFrames = 0;
    this.lastMoveTime = performance.now();

    // Event log
    this.lastEvent = 'Starting conservative calibration (75k x 8)';

    // Manual overrides from URL if any
    this.parseUrlOverrides();
  }

  parseUrlOverrides() {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    if (params.has('tier')) {
      const t = params.get('tier').toUpperCase();
      if (QUALITY_TIERS[t]) {
        this.setMode(t.toLowerCase());
      }
    }
  }

  setMode(modeStr) {
    const m = modeStr.toLowerCase();
    if (m === 'auto') {
      this.mode = 'auto';
      this.state = 'calibrating';
      this.calibrationFrames = 0;
      this.currentTierKey = 'LOW';
      this.currentTier = QUALITY_TIERS.LOW;
      this.lastEvent = 'Auto mode active: re-calibrating';
      return;
    }

    const key = m.toUpperCase();
    if (QUALITY_TIERS[key]) {
      this.mode = m;
      this.currentTierKey = key;
      this.currentTier = QUALITY_TIERS[key];
      this.state = 'settled';
      this.lastEvent = `Forced tier: ${this.currentTier.label}`;
    }
  }

  markInteraction() {
    this.lastInteractionTime = performance.now();
    this.isInteracting = true;
  }

  recordGpuTime(gpuMs) {
    if (gpuMs === null || gpuMs === undefined || isNaN(gpuMs) || gpuMs <= 0) return;
    // Clamp timer query anomalies to prevent driver query spikes from poisoning EMA
    const cleanGpuMs = Math.min(100.0, Math.max(0.1, gpuMs));
    this.hasMeasuredGpu = true;
    if (this.gpuEma === 0.0) {
      this.gpuEma = cleanGpuMs;
    } else {
      this.gpuEma = (1.0 - this.gpuEmaAlpha) * this.gpuEma + this.gpuEmaAlpha * cleanGpuMs;
    }
  }

  recordCpuFallbackTime(cpuMs) {
    // If GPU timer queries are unavailable, use CPU frame time as proxy
    if (!this.hasMeasuredGpu && cpuMs > 0) {
      if (this.gpuEma === 0.0) {
        this.gpuEma = cpuMs;
      } else {
        this.gpuEma = (1.0 - this.gpuEmaAlpha) * this.gpuEma + this.gpuEmaAlpha * cpuMs;
      }
    }
  }

  update(dt, isCameraMoving = false) {
    const now = performance.now();

    // If camera is actively moving or interpolating, maintain interaction responsiveness
    if (isCameraMoving) {
      this.lastInteractionTime = now;
      this.isInteracting = true;
    } else if (now - this.lastInteractionTime > this.interactionCooldownMs) {
      this.isInteracting = false;
    }

    // Update stationary accumulation duration
    if (isCameraMoving || this.isInteracting) {
      this.stationaryFrames = 0;
      this.lastMoveTime = now;
    } else {
      this.stationaryFrames++;
    }

    if (this.cooldownFrames > 0) {
      this.cooldownFrames--;
    }

    // In manual mode, do not auto-adapt
    if (this.mode !== 'auto') {
      return;
    }

    // Calibration phase on initial startup
    if (this.state === 'calibrating') {
      this.calibrationFrames++;
      // Wait for stable timing: require at least calibrationTargetFrames AND (hasMeasuredGpu OR fallback after 80 frames)
      if (this.calibrationFrames >= this.calibrationTargetFrames) {
        if (this.hasMeasuredGpu || this.calibrationFrames >= 80) {
          this.completeCalibration();
        }
      }
      return;
    }

    // Settled adaptive phase
    this.evaluateAdaptation();
  }

  completeCalibration() {
    this.state = 'settled';
    this.cooldownFrames = this.minCooldown;

    // Use measured GPU timing to choose initial settled tier
    if (this.hasMeasuredGpu && this.gpuEma > 1.5) {
      if (this.gpuEma < 11.5) {
        this.setTier('STANDARD', `Calibrated to Standard: GPU EMA ${this.gpuEma.toFixed(1)}ms < 11.5ms budget`);
      } else if (this.gpuEma < 15.5) {
        this.setTier('LOW', `Calibrated to Low: GPU EMA ${this.gpuEma.toFixed(1)}ms maintains target`);
      } else {
        this.setTier('POTATO', `Calibrated to Potato: GPU EMA ${this.gpuEma.toFixed(1)}ms constrained`);
      }
    } else {
      // Fallback: promote to STANDARD on modern systems
      this.setTier('STANDARD', 'Calibrated to Standard (timer query fallback)');
    }
  }

  evaluateAdaptation() {
    if (!this.hasMeasuredGpu || this.gpuEma <= 0) return;

    const gpu = this.gpuEma;
    const current = this.currentTierKey;

    // Fast Downgrade Checks
    // 1. Severe over budget (>22ms / ~45 FPS drop)
    if (gpu > 22.0) {
      this.severeOverBudgetFrames++;
      if (this.severeOverBudgetFrames >= 10) {
        this.severeOverBudgetFrames = 0;
        this.overBudgetFrames = 0;
        this.sustainedHeadroomFrames = 0;
        this.downgradeTier(`Fast downgrade: severe GPU load (${gpu.toFixed(1)}ms > 22ms)`);
        return;
      }
    } else {
      this.severeOverBudgetFrames = 0;
    }

    // 2. Sustained over budget (>17.0ms for 60 frames / ~1.0s debounce)
    if (gpu > 17.0) {
      this.overBudgetFrames++;
      this.sustainedHeadroomFrames = 0;
      if (this.overBudgetFrames >= 60) {
        this.overBudgetFrames = 0;
        this.downgradeTier(`Downgraded: GPU over budget (${gpu.toFixed(1)}ms > 17.0ms)`);
        return;
      }
    } else {
      this.overBudgetFrames = 0;
    }

    // Hysteresis Upgrade Checks (requires sustained headroom and cooled down)
    // Upgrades require headroom margin significantly below downgrade threshold minus the 2x step size
    if (this.cooldownFrames === 0) {
      // Potato -> Low upgrade: requires GPU < 7.5ms for 120 frames (~2.0s)
      if (current === 'POTATO' && gpu < 7.5) {
        this.sustainedHeadroomFrames++;
        if (this.sustainedHeadroomFrames >= 120) {
          this.sustainedHeadroomFrames = 0;
          this.setTier('LOW', `Upgraded to Low: sustained headroom (${gpu.toFixed(1)}ms < 7.5ms)`);
          return;
        }
      }
      // Low -> Standard upgrade: requires GPU < 8.0ms for 180 frames (~3.0s)
      // Because Standard workload is 2x Low (~6ms higher), Low must run < 8.0ms to prevent jumping > 17ms
      else if (current === 'LOW' && gpu < 8.0) {
        this.sustainedHeadroomFrames++;
        if (this.sustainedHeadroomFrames >= 180) {
          this.sustainedHeadroomFrames = 0;
          this.setTier('STANDARD', `Upgraded to Standard: sustained headroom (${gpu.toFixed(1)}ms < 8.0ms)`);
          return;
        }
      }
      // Standard -> High upgrade: ONLY on dedicated GPUs with huge headroom (GPU < 5.5ms for 300 frames)
      else if (current === 'STANDARD' && gpu < 5.5) {
        this.sustainedHeadroomFrames++;
        if (this.sustainedHeadroomFrames >= 300) {
          this.sustainedHeadroomFrames = 0;
          this.setTier('HIGH', `Upgraded to High: discrete GPU headroom confirmed (${gpu.toFixed(1)}ms < 5.5ms)`);
          return;
        }
      } else {
        this.sustainedHeadroomFrames = Math.max(0, this.sustainedHeadroomFrames - 1);
      }
    }
  }

  setTier(tierKey, eventMsg) {
    if (this.currentTierKey === tierKey) return;
    this.currentTierKey = tierKey;
    this.currentTier = QUALITY_TIERS[tierKey];
    this.cooldownFrames = this.minCooldown;
    this.lastEvent = eventMsg;
  }

  downgradeTier(reasonMsg) {
    if (this.currentTierKey === 'HIGH') {
      this.setTier('STANDARD', reasonMsg);
    } else if (this.currentTierKey === 'STANDARD') {
      this.setTier('LOW', reasonMsg);
    } else if (this.currentTierKey === 'LOW') {
      this.setTier('POTATO', reasonMsg);
    }
  }

  /**
   * Computes bounded active particle count & IFS steps for the given zoom level.
   * Total deposits (particles x steps) is strictly bounded by tier.depositBudget.
   */
  getWorkload(zoom = 1.65) {
    const tier = this.currentTier;
    const baseParticles = tier.particles;
    let baseSteps = tier.steps;
    const budget = tier.depositBudget;

    // Interaction mode: temporarily reduce load by ~35-40% for ultra-snappy 60 FPS interaction
    let loadScale = 1.0;
    if (this.isInteracting) {
      if (this.currentTierKey === 'STANDARD') {
        loadScale = 0.65; // ~100k x 7 = 700k deposits
      } else if (this.currentTierKey === 'LOW') {
        loadScale = 0.70; // ~55k x 7 = 385k deposits
      } else if (this.currentTierKey === 'HIGH') {
        loadScale = 0.75;
      }
    }

    // Deep zoom IFS step scaling:
    // As zoom deepens (1x to 130x+), steps modestly increase to resolve microscopic geometry,
    // but particle count scales down inversely so active deposits NEVER explode!
    const zoomFactor = Math.max(1.0, zoom / 1.65);
    const zoomLog = Math.log2(zoomFactor);

    let steps = baseSteps;
    if (this.currentTierKey === 'POTATO') {
      steps = 4;
    } else if (this.currentTierKey === 'LOW') {
      steps = Math.min(10, Math.round(baseSteps + zoomLog * 0.35));
    } else if (this.currentTierKey === 'STANDARD') {
      steps = Math.min(12, Math.round(baseSteps + zoomLog * 0.60));
    } else if (this.currentTierKey === 'HIGH') {
      steps = Math.min(12, Math.round(baseSteps + zoomLog * 0.60));
    } else if (this.currentTierKey === 'EXTREME') {
      steps = Math.min(16, Math.round(baseSteps + zoomLog * 0.80));
    }

    if (this.isInteracting) {
      steps = Math.max(4, steps - 1);
    }

    // Trajectory / deposit budget scaling (Requirement 9):
    // As IFS steps escalate from 8 to 10 to 12, additional draw calls and rasterizer overhead occur.
    // Scaling deposit budget proportionally (e.g. 150k x 8 = 1.2M -> 100k x 10 = 1.0M -> 75k x 12 = 900k)
    // preserves stable, bounded GPU frame cost (~10-12ms) without overflowing frame budget or mode flipping.
    const stepRatio = baseSteps / steps;
    const scaledBudget = Math.round(budget * Math.pow(stepRatio, 0.70));
    const activeBudget = Math.round(scaledBudget * loadScale);

    // Inversely compute active particles to keep deposits bounded within activeBudget
    let particles = Math.min(baseParticles, Math.round(activeBudget / steps));
    if (this.renderer && this.renderer.maxParticleCapacity) {
      particles = Math.min(particles, this.renderer.maxParticleCapacity);
    }
    // Round to nearest 500 for clean GPU draw alignment
    particles = Math.max(10000, Math.round(particles / 500) * 500);

    return {
      particles,
      steps,
      deposits: particles * steps,
      dpr: this.getDpr(),
      tierKey: this.currentTierKey,
      tierName: tier.name
    };
  }

  getDpr() {
    const rawDpr = (typeof window !== 'undefined' && window.devicePixelRatio) ? window.devicePixelRatio : 1.0;
    return Math.min(this.currentTier.maxDpr, rawDpr);
  }

  getStatus() {
    const target = this.currentTier.targetBudgetMs;
    const gpu = this.gpuEma > 0 ? this.gpuEma : null;
    // Calculate headroom directly against target GPU budget
    const targetHeadroom = (gpu !== null && target > 0)
      ? Math.max(0, Math.round(((target - gpu) / target) * 100))
      : null;
    // Frame headroom relative to 60Hz presentation budget (16.67ms)
    const frameHeadroom60Hz = gpu !== null
      ? Math.max(0, Math.round(((16.67 - gpu) / 16.67) * 100))
      : null;

    let tierDisplay = this.currentTier.name;
    if (this.mode === 'auto') {
      tierDisplay = `AUTO (${this.currentTier.name})`;
    } else {
      tierDisplay = `FORCED (${this.currentTier.name})`;
    }

    return {
      mode: this.mode,
      tierKey: this.currentTierKey,
      tierDisplay,
      gpuEma: gpu,
      targetBudgetMs: target,
      headroomPercent: targetHeadroom,
      frameHeadroom60Hz,
      lastEvent: this.lastEvent,
      isInteracting: this.isInteracting,
      state: this.state,
      accumulationAgeSec: parseFloat((this.stationaryFrames / 60.0).toFixed(1)),
      stationaryFrames: this.stationaryFrames
    };
  }
}
