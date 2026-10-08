/**
 * Production Adaptive Quality & Measured GPU Headroom Workload Manager
 *
 * Implements measured multi-tier adaptive rendering:
 * - POTATO:     40,000 particles x 4 IFS steps (~160k deposits/frame)
 * - LOW:        75,000 particles x 8 IFS steps (~600k deposits/frame)
 * - STANDARD:  150,000 particles x 8 IFS steps (~1.20M deposits/frame)
 * - HIGH:      250,000 particles x 8 IFS steps (~2.00M deposits/frame)
 * - ULTRA:     400,000 particles x 10 IFS steps (~4.00M deposits/frame)
 * - EXTREME:   589,824 particles x 12 IFS steps (~7.08M deposits/frame)
 * - BRUTEFORCE: 589,824 particles x 16 IFS steps (~9.44M deposits/frame) [Manual enthusiast only]
 *
 * Key architecture:
 * 1. Low-end safety preserved: Iris Xe retains conservative startup, interaction throttling,
 *    deep-zoom limits, and thermal downgrade protection.
 * 2. Measured GPU Headroom is the authority: driven by asynchronous WebGL2 timer queries.
 * 3. Calibration ceiling fixed: valid timer queries of 1-2 ms represent true headroom.
 * 4. Empirical Promotion Ladder: STANDARD -> HIGH -> ULTRA -> EXTREME with 90-120 frame debounce.
 * 5. Validated Promotions: 1-2 second observation window post-promotion with immediate rollback
 *    and anti-oscillation hysteresis if safe budget or FPS degrades.
 * 6. Smooth 60 FPS AUTO target: preserves presentation headroom below 16.67ms.
 * 7. Separate Manual BRUTE FORCE mode: 589,824 x 16 IFS steps (9.44M deposits/frame) without AUTO reduction.
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
    targetBudgetMs: 11.5
  },
  ULTRA: {
    id: 'ultra',
    name: 'ULTRA',
    label: 'Ultra',
    particles: 400000,
    steps: 10,
    depositBudget: 4000000,
    maxDpr: 1.5,
    targetBudgetMs: 12.0
  },
  EXTREME: {
    id: 'extreme',
    name: 'EXTREME',
    label: 'Extreme',
    particles: 589824,
    steps: 12,
    depositBudget: 7077888,
    maxDpr: 1.5,
    targetBudgetMs: 13.0
  },
  BRUTEFORCE: {
    id: 'bruteforce',
    name: 'BRUTE FORCE',
    label: 'Brute Force',
    particles: 589824,
    steps: 16,
    depositBudget: 9437184,
    maxDpr: 1.5,
    targetBudgetMs: 50.0
  }
};

export class AdaptiveManager {
  constructor(renderer) {
    this.renderer = renderer;

    // Operating mode: 'auto' (default), 'low', 'standard', 'high', 'ultra', 'extreme', 'bruteforce', 'potato'
    this.mode = 'auto';

    // Settled tier (current active tier)
    this.currentTierKey = 'LOW';
    this.currentTier = QUALITY_TIERS.LOW;

    // Adaptive state machine: 'calibrating', 'settled'
    this.state = 'calibrating';
    this.calibrationFrames = 0;
    this.calibrationTargetFrames = 45; // ~0.75s initial invisible calibration

    // Timing & EMA metrics
    this.gpuEma = 0.0;
    this.gpuEmaAlpha = 0.08; // Smooth exponential moving average
    this.hasMeasuredGpu = false;
    this.effectiveFpsEma = 60.0;

    // Empirical promotion & hysteresis parameters (Requirements 4, 5)
    this.sustainedHeadroomFrames = 0;
    this.promotionFramesTarget = 95; // ~1.5s stable simulation frames debounce
    this.overBudgetFrames = 0;
    this.severeOverBudgetFrames = 0;
    this.cooldownFrames = 0;
    this.minCooldown = 90; // ~1.5s cooldown between promotions

    // Hysteresis blacklist for tiers that failed post-promotion validation
    this.blockedTiers = {};

    // Post-promotion validation state machine (Requirement 5)
    this.validationState = {
      active: false,
      framesRemaining: 0,
      promotedFrom: null,
      promotedTo: null,
      overBudgetFrames: 0,
      fpsDegradeFrames: 0
    };

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
    if (params.has('bruteforce') || params.has('brute')) {
      this.setMode('bruteforce');
      return;
    }
    if (params.has('tier')) {
      const t = params.get('tier').toUpperCase();
      if (t === 'BRUTE' || t === 'BRUTEFORCE' || t === 'BRUTE_FORCE') {
        this.setMode('bruteforce');
      } else if (QUALITY_TIERS[t]) {
        this.setMode(t.toLowerCase());
      }
    }
  }

  setMode(modeStr) {
    const m = modeStr.toLowerCase();
    if (m === 'auto') {
      const oldTier = this.currentTierKey;
      this.mode = 'auto';
      this.state = 'calibrating';
      this.calibrationFrames = 0;
      this.currentTierKey = 'LOW';
      this.currentTier = QUALITY_TIERS.LOW;
      this.blockedTiers = {};
      this.validationState.active = false;
      this.lastEvent = 'Auto mode active: re-calibrating';
      this.logTierTransition(oldTier, 'LOW', 'Switched to Auto mode');
      return;
    }

    if (m === 'bruteforce' || m === 'brute' || m === 'brute_force') {
      const oldTier = this.currentTierKey;
      this.mode = 'bruteforce';
      this.currentTierKey = 'BRUTEFORCE';
      this.currentTier = QUALITY_TIERS.BRUTEFORCE;
      this.state = 'settled';
      this.validationState.active = false;
      this.lastEvent = 'Manual BRUTE FORCE active (589,824 x 16)';
      this.logTierTransition(oldTier, 'BRUTE FORCE', 'Manual Brute Force mode enabled (589,824 x 16)');
      return;
    }

    const key = m.toUpperCase();
    if (QUALITY_TIERS[key]) {
      const oldTier = this.currentTierKey;
      this.mode = m;
      this.currentTierKey = key;
      this.currentTier = QUALITY_TIERS[key];
      this.state = 'settled';
      this.validationState.active = false;
      this.lastEvent = `Forced tier: ${this.currentTier.label}`;
      this.logTierTransition(oldTier, key, `Manual tier selection: ${this.currentTier.label}`);
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

    // In manual mode (including BRUTE FORCE), do not auto-adapt
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

    // Use measured GPU timing to choose initial settled tier.
    // Valid timer query (even 1-2 ms) is interpreted as true GPU headroom (>1.5ms arbitrary requirement removed).
    if (this.hasMeasuredGpu && this.gpuEma > 0) {
      if (this.gpuEma < 11.5) {
        this.setTier('STANDARD', `Calibrated to Standard: GPU EMA ${this.gpuEma.toFixed(1)}ms < 11.5ms budget`);
      } else if (this.gpuEma < 15.5) {
        this.setTier('LOW', `Calibrated to Low: GPU EMA ${this.gpuEma.toFixed(1)}ms maintains target`);
      } else {
        this.setTier('POTATO', `Calibrated to Potato: GPU EMA ${this.gpuEma.toFixed(1)}ms constrained`);
      }
    } else {
      // Fallback: promote to STANDARD on modern systems if timer queries unavailable
      this.setTier('STANDARD', 'Calibrated to Standard (timer query fallback)');
    }
  }

  evaluateAdaptation() {
    if (!this.hasMeasuredGpu || this.gpuEma <= 0) return;

    const gpu = this.gpuEma;
    const current = this.currentTierKey;
    const fps = (this.renderer && this.renderer.profiler) ? this.renderer.profiler.metrics.fps : 60;

    // 1. Post-Promotion Validation Check (Requirement 5: observe new tier for ~1-2 seconds)
    if (this.validationState.active) {
      this.validationState.framesRemaining--;

      // Check if measured GPU time exceeds safe presentation budget (13.8ms safe for 60Hz)
      if (gpu > 13.8) {
        this.validationState.overBudgetFrames++;
      } else {
        this.validationState.overBudgetFrames = Math.max(0, this.validationState.overBudgetFrames - 1);
      }

      // Check if sustained presentation FPS degrades (<54 FPS)
      if (fps < 54) {
        this.validationState.fpsDegradeFrames++;
      } else {
        this.validationState.fpsDegradeFrames = Math.max(0, this.validationState.fpsDegradeFrames - 1);
      }

      // Rollback trigger: sustained over-budget (15 frames) OR severe frame spike (>20ms) OR sustained FPS drop (20 frames)
      if (this.validationState.overBudgetFrames >= 15 || gpu > 20.0 || this.validationState.fpsDegradeFrames >= 20) {
        const rollbackFrom = this.validationState.promotedTo;
        const rollbackTo = this.validationState.promotedFrom;
        this.validationState.active = false;
        this.blockedTiers[rollbackFrom] = true; // Hysteresis: block tier so AUTO does not oscillate
        const reason = `Validation rollback: GPU ${gpu.toFixed(1)}ms > 13.8ms budget or FPS (${fps}) degraded`;
        this.logTierTransition(rollbackFrom, rollbackTo, reason);
        this.setTier(rollbackTo, reason);
        this.cooldownFrames = this.minCooldown;
        return;
      }

      // If validation period concludes cleanly, confirm promotion!
      if (this.validationState.framesRemaining <= 0) {
        this.validationState.active = false;
        this.cooldownFrames = 30; // Brief stabilization cooldown before next promotion check
        console.log(`[Adaptive] Promotion to ${current} validated successfully! Measured GPU EMA: ${gpu.toFixed(2)}ms, FPS: ${fps}`);
        return;
      }

      // While validating, do not trigger further upgrades
      return;
    }

    // 2. Fast Downgrade Checks (runtime safety)
    // Severe over budget (>22ms / ~45 FPS drop)
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

    // Sustained over budget (>17.0ms for 60 frames / ~1.0s debounce)
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

    // 3. Empirical Promotion Ladder (Requirements 4, 5, 6)
    // Only promote after sustained measured headroom below safe presentation budget (60 Hz target)
    if (this.cooldownFrames === 0 && !this.isInteracting) {
      // POTATO -> LOW
      if (current === 'POTATO' && !this.blockedTiers['LOW'] && gpu < 6.5) {
        this.sustainedHeadroomFrames++;
        if (this.sustainedHeadroomFrames >= this.promotionFramesTarget) {
          this.sustainedHeadroomFrames = 0;
          this.promoteTier('LOW', `Upgraded to Low: sustained headroom (${gpu.toFixed(1)}ms < 6.5ms)`);
          return;
        }
      }
      // LOW -> STANDARD
      else if (current === 'LOW' && !this.blockedTiers['STANDARD'] && gpu < 6.5) {
        this.sustainedHeadroomFrames++;
        if (this.sustainedHeadroomFrames >= this.promotionFramesTarget) {
          this.sustainedHeadroomFrames = 0;
          this.promoteTier('STANDARD', `Upgraded to Standard: sustained headroom (${gpu.toFixed(1)}ms < 6.5ms)`);
          return;
        }
      }
      // STANDARD -> HIGH (Requirement 4: 90-120 frames, gpu < 7.0ms)
      else if (current === 'STANDARD' && !this.blockedTiers['HIGH'] && gpu < 7.0) {
        this.sustainedHeadroomFrames++;
        if (this.sustainedHeadroomFrames >= this.promotionFramesTarget) {
          this.sustainedHeadroomFrames = 0;
          this.promoteTier('HIGH', `Upgraded to High: sustained headroom (${gpu.toFixed(1)}ms < 7.0ms)`);
          return;
        }
      }
      // HIGH -> ULTRA (Requirement 4: 90-120 frames, gpu < 6.0ms)
      else if (current === 'HIGH' && !this.blockedTiers['ULTRA'] && gpu < 6.0) {
        this.sustainedHeadroomFrames++;
        if (this.sustainedHeadroomFrames >= this.promotionFramesTarget) {
          this.sustainedHeadroomFrames = 0;
          this.promoteTier('ULTRA', `Upgraded to Ultra: sustained headroom (${gpu.toFixed(1)}ms < 6.0ms)`);
          return;
        }
      }
      // ULTRA -> EXTREME (Requirement 4: 90-120 frames, gpu < 6.8ms)
      else if (current === 'ULTRA' && !this.blockedTiers['EXTREME'] && gpu < 6.8) {
        this.sustainedHeadroomFrames++;
        if (this.sustainedHeadroomFrames >= this.promotionFramesTarget) {
          this.sustainedHeadroomFrames = 0;
          this.promoteTier('EXTREME', `Upgraded to Extreme: sustained headroom (${gpu.toFixed(1)}ms < 6.8ms)`);
          return;
        }
      } else {
        this.sustainedHeadroomFrames = Math.max(0, this.sustainedHeadroomFrames - 1);
      }
    }
  }

  promoteTier(tierKey, reasonMsg) {
    const oldTier = this.currentTierKey;
    this.logTierTransition(oldTier, tierKey, reasonMsg);
    this.setTier(tierKey, reasonMsg);
    // Initialize 90-frame (~1.5s) post-promotion validation (Requirement 5)
    this.validationState = {
      active: true,
      framesRemaining: 90,
      promotedFrom: oldTier,
      promotedTo: tierKey,
      overBudgetFrames: 0,
      fpsDegradeFrames: 0
    };
  }

  setTier(tierKey, eventMsg) {
    if (this.currentTierKey === tierKey) return;
    this.currentTierKey = tierKey;
    this.currentTier = QUALITY_TIERS[tierKey];
    this.cooldownFrames = this.minCooldown;
    this.lastEvent = eventMsg;
  }

  downgradeTier(reasonMsg) {
    const oldTier = this.currentTierKey;
    let nextTier = 'POTATO';
    if (oldTier === 'EXTREME') nextTier = 'ULTRA';
    else if (oldTier === 'ULTRA') nextTier = 'HIGH';
    else if (oldTier === 'HIGH') nextTier = 'STANDARD';
    else if (oldTier === 'STANDARD') nextTier = 'LOW';
    else if (oldTier === 'LOW') nextTier = 'POTATO';

    // Prevent immediate oscillation back up
    this.blockedTiers[oldTier] = true;
    this.logTierTransition(oldTier, nextTier, reasonMsg);
    this.setTier(nextTier, reasonMsg);
  }

  logTierTransition(oldTier, newTier, reason) {
    const gpuStr = this.gpuEma > 0 ? `${this.gpuEma.toFixed(2)}ms` : 'N/A';
    console.log(`[Adaptive Tier Change] ${oldTier} -> ${newTier} | Measured GPU EMA: ${gpuStr} | Reason: ${reason}`);
  }

  /**
   * Computes bounded active particle count & IFS steps for the given zoom level.
   * Total deposits (particles x steps) is strictly bounded by tier.depositBudget.
   */
  getWorkload(zoom = 1.65) {
    // Manual BRUTE FORCE mode (Requirements 7, 8):
    // Bypass ALL AUTO particle/step tier reductions!
    // Strictly runs 589,824 particles x 16 steps = 9,437,184 deposits per frame
    if (this.mode === 'bruteforce' || this.currentTierKey === 'BRUTEFORCE') {
      return {
        particles: 589824,
        steps: 16,
        deposits: 9437184,
        dpr: this.getDpr(),
        tierKey: 'BRUTEFORCE',
        tierName: 'BRUTE FORCE'
      };
    }

    const tier = this.currentTier;
    const baseParticles = tier.particles;
    let baseSteps = tier.steps;
    const budget = tier.depositBudget;

    // Interaction mode: temporarily reduce load by ~25-35% for ultra-snappy 60 FPS interaction
    let loadScale = 1.0;
    if (this.isInteracting) {
      if (this.currentTierKey === 'STANDARD') {
        loadScale = 0.65; // ~100k x 7 = 700k deposits
      } else if (this.currentTierKey === 'LOW') {
        loadScale = 0.70; // ~55k x 7 = 385k deposits
      } else if (this.currentTierKey === 'HIGH') {
        loadScale = 0.75;
      } else if (this.currentTierKey === 'ULTRA') {
        loadScale = 0.75;
      } else if (this.currentTierKey === 'EXTREME') {
        loadScale = 0.80;
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
    } else if (this.currentTierKey === 'ULTRA') {
      steps = Math.min(14, Math.round(baseSteps + zoomLog * 0.60));
    } else if (this.currentTierKey === 'EXTREME') {
      steps = Math.min(16, Math.round(baseSteps + zoomLog * 0.80));
    }

    if (this.isInteracting) {
      steps = Math.max(4, steps - 1);
    }

    // Trajectory / deposit budget scaling:
    // Preserves stable, bounded GPU frame cost without overflowing frame budget
    const stepRatio = baseSteps / steps;
    const scaledBudget = Math.round(budget * Math.pow(stepRatio, 0.70));
    const activeBudget = Math.round(scaledBudget * loadScale);

    // Inversely compute active particles to keep deposits bounded within activeBudget
    let particles = Math.min(baseParticles, Math.round(activeBudget / steps));
    if (this.renderer && this.renderer.maxParticleCapacity) {
      particles = Math.min(particles, this.renderer.maxParticleCapacity);
    }
    // Round to nearest 500 for clean GPU draw alignment when scaled down below base
    if (particles < baseParticles) {
      particles = Math.max(10000, Math.round(particles / 500) * 500);
    }

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
    const isBrute = this.mode === 'bruteforce' || this.currentTierKey === 'BRUTEFORCE';
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
    let modeDisplay = 'MANUAL';
    if (this.mode === 'auto') {
      modeDisplay = 'AUTO';
      tierDisplay = `AUTO (${this.currentTier.name})`;
    } else if (isBrute) {
      modeDisplay = 'BRUTE FORCE';
      tierDisplay = 'BRUTE FORCE (MANUAL)';
    } else {
      modeDisplay = 'MANUAL';
      tierDisplay = `MANUAL (${this.currentTier.name})`;
    }

    return {
      mode: this.mode,
      modeDisplay,
      tierKey: this.currentTierKey,
      tierName: this.currentTier.name,
      tierDisplay,
      particles: isBrute ? 589824 : this.currentTier.particles,
      steps: isBrute ? 16 : this.currentTier.steps,
      deposits: isBrute ? 9437184 : (this.currentTier.particles * this.currentTier.steps),
      gpuEma: gpu,
      targetBudgetMs: target,
      headroomPercent: targetHeadroom,
      frameHeadroom60Hz,
      lastEvent: this.lastEvent,
      isInteracting: this.isInteracting,
      state: this.state,
      isValidating: this.validationState.active,
      accumulationAgeSec: parseFloat((this.stationaryFrames / 60.0).toFixed(1)),
      stationaryFrames: this.stationaryFrames
    };
  }
}
