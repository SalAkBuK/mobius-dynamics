/**
 * Temporary Development-Only Performance Profiling & Diagnostic Instrumentation
 * 
 * Measures:
 * - Real GPU time via EXT_disjoint_timer_query_webgl2 (zero-stall asynchronous ring buffer)
 * - Fine-grained GPU breakdown: Decay, Simulation (Transform Feedback), Splatting, Bloom, Tonemapping/Post
 * - CPU frame time, JS math update time, WebGL command submission time
 * - 1% low FPS, draw calls, memory footprints, iteration workloads
 */

export class Profiler {
  constructor(renderer) {
    this.renderer = renderer;
    this.gl = renderer.gl;
    const params = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
    const forceNoQuery = params && (params.has('notimer') || params.has('noquery'));
    this.ext = forceNoQuery ? null : this.gl.getExtension('EXT_disjoint_timer_query_webgl2');
    this.supported = !!this.ext;
    this.enabled = true; // Can be toggled on/off

    this.ringSize = 4;
    this.ring = [];
    this.ringIdx = 0;
    this.maxSteps = 32;

    if (this.supported) {
      for (let i = 0; i < this.ringSize; i++) {
        const slot = {
          decay: this.gl.createQuery(),
          sim: [],
          splat: [],
          bloom: this.gl.createQuery(),
          post: this.gl.createQuery(),
          active: false,
          steps: 0,
          bloomActive: false,
          cpuTimes: {},
          metrics: {}
        };
        for (let s = 0; s < this.maxSteps; s++) {
          slot.sim.push(this.gl.createQuery());
          slot.splat.push(this.gl.createQuery());
        }
        this.ring.push(slot);
      }
    }

    // CPU timers
    this.frameStartTime = 0;
    this.jsUpdateTime = 0;
    this.decayCpuMs = 0;
    this.simCpuMs = 0;
    this.splatCpuMs = 0;
    this.bloomCpuMs = 0;
    this.postCpuMs = 0;
    this.totalCpuMs = 0;
    this.totalFrameMs = 16.67;

    // Rolling frame history for 1% low and stable averages (last 120 frames)
    this.historyCapacity = 120;
    this.frameTimeHistory = [];
    this.gpuTimeHistory = [];
    this.cpuTimeHistory = [];

    // Current averaged or latest metrics
    this.metrics = {
      fps: 60,
      fps1Low: 60,
      frameMs: 16.67,
      cpuMs: 0,
      gpuMs: this.supported ? 0 : null,
      gpuSupported: this.supported,
      jsUpdateMs: 0,
      simGpuMs: this.supported ? 0 : null,
      splatGpuMs: this.supported ? 0 : null,
      decayGpuMs: this.supported ? 0 : null,
      bloomGpuMs: this.supported ? 0 : null,
      postGpuMs: this.supported ? 0 : null,
      simCpuMs: 0,
      splatCpuMs: 0,
      decayCpuMs: 0,
      bloomCpuMs: 0,
      postCpuMs: 0,
      numParticles: renderer.numParticles,
      stepsPerFrame: renderer.stepsPerFrame,
      iterationsPerFrame: renderer.numParticles * renderer.stepsPerFrame,
      iterationsPerSec: 0,
      dpr: window.devicePixelRatio || 1,
      zoom: renderer.zoom,
      accumulationFrames: 0,
      drawCalls: 0,
      xfbPasses: renderer.stepsPerFrame,
      renderWidth: renderer.canvas.width,
      renderHeight: renderer.canvas.height
    };

    // Current frame tracking
    this.curSlot = null;
    this.curPass = null;
    this.curPassCpuStart = 0;
    this.drawCallCount = 0;
  }

  beginFrame(jsTime = 0) {
    this.frameStartTime = performance.now();
    this.jsUpdateTime = jsTime;
    this.drawCallCount = 0;
    this.decayCpuMs = 0;
    this.simCpuMs = 0;
    this.splatCpuMs = 0;
    this.bloomCpuMs = 0;
    this.postCpuMs = 0;

    if (!this.enabled || !this.supported) return;

    this.pollOldQueries();

    this.curSlot = this.ring[this.ringIdx];
    this.curSlot.active = true;
    this.curSlot.steps = Math.min(this.maxSteps, this.renderer.stepsPerFrame);
    this.curSlot.bloomActive = this.renderer.bloomEnabled && this.renderer.viewMode === 0;
    this.curSlot.metrics = {
      numParticles: this.renderer.numParticles,
      stepsPerFrame: this.renderer.stepsPerFrame,
      zoom: this.renderer.zoom,
      accumFrames: this.renderer.accumulationFrames,
      renderWidth: this.renderer.canvas.width,
      renderHeight: this.renderer.canvas.height
    };
  }

  beginPass(name, step = 0) {
    this.curPass = name;
    this.curPassCpuStart = performance.now();

    if (!this.enabled || !this.supported || !this.curSlot) return;

    const gl = this.gl;
    const ext = this.ext;

    if (name === 'decay') {
      gl.beginQuery(ext.TIME_ELAPSED_EXT, this.curSlot.decay);
    } else if (name === 'sim') {
      if (step < this.maxSteps) {
        gl.beginQuery(ext.TIME_ELAPSED_EXT, this.curSlot.sim[step]);
      }
    } else if (name === 'splat') {
      if (step < this.maxSteps) {
        gl.beginQuery(ext.TIME_ELAPSED_EXT, this.curSlot.splat[step]);
      }
    } else if (name === 'bloom') {
      if (this.curSlot.bloomActive) {
        gl.beginQuery(ext.TIME_ELAPSED_EXT, this.curSlot.bloom);
      }
    } else if (name === 'post') {
      gl.beginQuery(ext.TIME_ELAPSED_EXT, this.curSlot.post);
    }
  }

  recordDrawCall() {
    this.drawCallCount++;
  }

  endPass(name, step = 0) {
    const elapsed = performance.now() - this.curPassCpuStart;
    if (name === 'decay') this.decayCpuMs += elapsed;
    else if (name === 'sim') this.simCpuMs += elapsed;
    else if (name === 'splat') this.splatCpuMs += elapsed;
    else if (name === 'bloom') this.bloomCpuMs += elapsed;
    else if (name === 'post') this.postCpuMs += elapsed;

    if (!this.enabled || !this.supported || !this.curSlot) return;

    const gl = this.gl;
    const ext = this.ext;

    if (name === 'decay') {
      gl.endQuery(ext.TIME_ELAPSED_EXT);
    } else if (name === 'sim') {
      if (step < this.maxSteps) gl.endQuery(ext.TIME_ELAPSED_EXT);
    } else if (name === 'splat') {
      if (step < this.maxSteps) gl.endQuery(ext.TIME_ELAPSED_EXT);
    } else if (name === 'bloom') {
      if (this.curSlot.bloomActive) gl.endQuery(ext.TIME_ELAPSED_EXT);
    } else if (name === 'post') {
      gl.endQuery(ext.TIME_ELAPSED_EXT);
    }
  }

  endFrame(dt = 0.016) {
    const now = performance.now();
    this.totalCpuMs = (now - this.frameStartTime) + this.jsUpdateTime;
    this.totalFrameMs = Math.max(0.1, dt * 1000);

    if (this.curSlot) {
      this.curSlot.cpuTimes = {
        totalCpuMs: this.totalCpuMs,
        jsUpdateMs: this.jsUpdateTime,
        decayCpuMs: this.decayCpuMs,
        simCpuMs: this.simCpuMs,
        splatCpuMs: this.splatCpuMs,
        bloomCpuMs: this.bloomCpuMs,
        postCpuMs: this.postCpuMs,
        drawCalls: this.drawCallCount
      };
      this.ringIdx = (this.ringIdx + 1) % this.ringSize;
      this.curSlot = null;
    }

    // Determine true effective frame time based on bottleneck (GPU execution vs CPU frame)
    const effectiveFrameMs = (this.supported && this.metrics.gpuMs !== null && this.metrics.gpuMs > 0)
      ? Math.max(this.totalFrameMs, this.metrics.gpuMs)
      : this.totalFrameMs;

    // Keep rolling history of effective frame times for true 1% low and throughput statistics
    this.frameTimeHistory.push(effectiveFrameMs);
    this.cpuTimeHistory.push(this.totalCpuMs);
    if (this.frameTimeHistory.length > this.historyCapacity) {
      this.frameTimeHistory.shift();
      this.cpuTimeHistory.shift();
    }

    // Calculate throughput FPS and 1% low from effective frame times
    let throughputFps = Math.max(1, Math.round(1000 / Math.max(1, effectiveFrameMs)));
    let fps1Low = throughputFps;
    if (this.frameTimeHistory.length >= 10) {
      const sorted = [...this.frameTimeHistory].sort((a, b) => a - b);
      const p99Idx = Math.floor(sorted.length * 0.99);
      const p99Ms = sorted[Math.min(sorted.length - 1, p99Idx)];
      fps1Low = p99Ms > 0 ? parseFloat((1000 / p99Ms).toFixed(1)) : throughputFps;
    }

    const itersPerFrame = this.renderer.numParticles * this.renderer.stepsPerFrame;

    // Update metrics every frame so HUD and profiling APIs always reflect real state
    this.metrics.fps = throughputFps;
    this.metrics.fps1Low = fps1Low;
    this.metrics.frameMs = parseFloat(effectiveFrameMs.toFixed(2));
    this.metrics.cpuMs = parseFloat(this.totalCpuMs.toFixed(2));
    this.metrics.jsUpdateMs = parseFloat(this.jsUpdateTime.toFixed(2));
    this.metrics.simCpuMs = parseFloat(this.simCpuMs.toFixed(2));
    this.metrics.splatCpuMs = parseFloat(this.splatCpuMs.toFixed(2));
    this.metrics.decayCpuMs = parseFloat(this.decayCpuMs.toFixed(2));
    this.metrics.bloomCpuMs = parseFloat(this.bloomCpuMs.toFixed(2));
    this.metrics.postCpuMs = parseFloat(this.postCpuMs.toFixed(2));
    this.metrics.numParticles = this.renderer.numParticles;
    this.metrics.stepsPerFrame = this.renderer.stepsPerFrame;
    this.metrics.iterationsPerFrame = itersPerFrame;
    this.metrics.iterationsPerSec = Math.round(itersPerFrame * throughputFps);
    this.metrics.dpr = window.devicePixelRatio || 1;
    this.metrics.zoom = parseFloat(this.renderer.zoom.toFixed(2));
    this.metrics.accumulationFrames = this.renderer.accumulationFrames;
    this.metrics.drawCalls = this.drawCallCount;
    this.metrics.xfbPasses = this.renderer.stepsPerFrame;
    this.metrics.renderWidth = this.renderer.canvas.width;
    this.metrics.renderHeight = this.renderer.canvas.height;
  }

  pollOldQueries() {
    if (!this.supported) return;

    const gl = this.gl;
    const ext = this.ext;

    for (let i = 0; i < this.ringSize; i++) {
      const slot = this.ring[i];
      if (!slot.active) continue;

      // Check post query availability as sentinel
      const available = gl.getQueryParameter(slot.post, gl.QUERY_RESULT_AVAILABLE);
      if (!available) continue;

      const disjoint = gl.getParameter(ext.GPU_DISJOINT_EXT);
      if (disjoint) {
        for (const s of this.ring) s.active = false;
        break;
      }

      const decayNs = gl.getQueryParameter(slot.decay, gl.QUERY_RESULT);
      let simNs = 0;
      let splatNs = 0;
      for (let s = 0; s < slot.steps; s++) {
        if (gl.getQueryParameter(slot.sim[s], gl.QUERY_RESULT_AVAILABLE)) {
          simNs += gl.getQueryParameter(slot.sim[s], gl.QUERY_RESULT);
        }
        if (gl.getQueryParameter(slot.splat[s], gl.QUERY_RESULT_AVAILABLE)) {
          splatNs += gl.getQueryParameter(slot.splat[s], gl.QUERY_RESULT);
        }
      }

      let bloomNs = 0;
      if (slot.bloomActive && gl.getQueryParameter(slot.bloom, gl.QUERY_RESULT_AVAILABLE)) {
        bloomNs = gl.getQueryParameter(slot.bloom, gl.QUERY_RESULT);
      }
      const postNs = gl.getQueryParameter(slot.post, gl.QUERY_RESULT);
      const totalGpuNs = decayNs + simNs + splatNs + bloomNs + postNs;

      const gpuMs = totalGpuNs / 1e6;
      this.gpuTimeHistory.push(gpuMs);
      if (this.gpuTimeHistory.length > this.historyCapacity) {
        this.gpuTimeHistory.shift();
      }

      this.metrics.gpuSupported = true;
      this.metrics.gpuMs = parseFloat(gpuMs.toFixed(2));
      this.metrics.simGpuMs = parseFloat((simNs / 1e6).toFixed(2));
      this.metrics.splatGpuMs = parseFloat((splatNs / 1e6).toFixed(2));
      this.metrics.decayGpuMs = parseFloat((decayNs / 1e6).toFixed(2));
      this.metrics.bloomGpuMs = parseFloat((bloomNs / 1e6).toFixed(2));
      this.metrics.postGpuMs = parseFloat((postNs / 1e6).toFixed(2));

      slot.active = false;
    }
  }

  /**
   * Run a controlled synchronous benchmark for specified particleCount and steps
   */
  async benchmarkWorkload(numParticles, steps, options = {}) {
    const warmupFrames = options.warmupFrames || 30;
    const testFrames = options.testFrames || 60;
    const renderer = this.renderer;
    const mathSys = options.mathSys;
    const gl = this.gl;

    renderer.setParticleCount(numParticles);
    renderer.setStepsOverride(steps);
    renderer.clearAccumulation();

    // Warmup frames
    for (let i = 0; i < warmupFrames; i++) {
      mathSys.update(0.016, renderer.zoom);
      renderer.render(mathSys, 0.016);
    }

    // Measurement frames
    const frameTimes = [];
    const cpuTimes = [];
    const gpuResults = [];

    for (let i = 0; i < testFrames; i++) {
      const t0 = performance.now();
      mathSys.update(0.016, renderer.zoom);
      const tMath = performance.now();
      const jsTime = tMath - t0;

      renderer.render(mathSys, 0.016, jsTime);
      const tEnd = performance.now();
      const totalCpu = tEnd - t0;

      frameTimes.push(totalCpu);
      cpuTimes.push(totalCpu);

      await new Promise(r => setTimeout(r, 0));
    }

    // Drain GPU pipeline
    gl.finish();
    for (let w = 0; w < 30; w++) {
      this.pollOldQueries();
      if (this.gpuTimeHistory.length > 0) break;
      await new Promise(r => setTimeout(r, 10));
    }

    // Compute statistics
    const avgCpu = cpuTimes.reduce((a, b) => a + b, 0) / cpuTimes.length;
    const sorted = [...frameTimes].sort((a, b) => a - b);
    const p99Idx = Math.floor(sorted.length * 0.99);
    const p99Ms = sorted[p99Idx];
    const avgFps = 1000 / avgCpu;
    const fps1Low = 1000 / Math.max(1, p99Ms);

    return {
      numParticles,
      steps,
      avgFps: parseFloat(avgFps.toFixed(1)),
      fps1Low: parseFloat(fps1Low.toFixed(1)),
      avgCpuMs: parseFloat(avgCpu.toFixed(2)),
      avgGpuMs: this.metrics.gpuMs,
      simGpuMs: this.metrics.simGpuMs,
      splatGpuMs: this.metrics.splatGpuMs,
      decayGpuMs: this.metrics.decayGpuMs,
      bloomGpuMs: this.metrics.bloomGpuMs,
      postGpuMs: this.metrics.postGpuMs,
      totalFrameMs: parseFloat(avgCpu.toFixed(2)),
      drawCalls: this.metrics.drawCalls,
      iterationsPerFrame: numParticles * steps
    };
  }
}
