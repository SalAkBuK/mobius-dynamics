/**
 * WebGL2 Real-Time Generative Engine
 * Simulates over 580,000 mathematical trajectories on GPU via Transform Feedback
 * Emerges genuinely from discrete iterated complex Mobius transformations and roots of unity (IFS)
 * Accumulates into 32-bit floating point render target (RGBA32F)
 */

import { Profiler } from './profiler.js';
import { AdaptiveManager, QUALITY_TIERS } from './adaptive.js';

export class MobiusRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext('webgl2', {
      alpha: false,
      antialias: false,
      depth: false,
      stencil: false,
      powerPreference: 'high-performance'
    });

    if (!this.gl) {
      throw new Error('WebGL2 is not supported by this browser.');
    }

    const gl = this.gl;
    this.extFloat = gl.getExtension('EXT_color_buffer_float');
    this.extFloatBlend = gl.getExtension('EXT_float_blend');
    this.extLinear = gl.getExtension('OES_texture_float_linear');

    // Robust floating-point format detection (RGBA32F native -> RGBA16F fallback -> RGBA8 fallback)
    this.floatCap = this.detectFloatCapability();
    this.floatFormat = this.floatCap.name;
    this.floatCapability = this.floatCap.label;

    // Parse URL overrides if any
    const params = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
    this.particlesOverride = params && params.has('particles') ? parseInt(params.get('particles'), 10) : null;
    this.stepsOverride = params && params.has('steps') ? parseInt(params.get('steps'), 10) : null;

    // Adaptive Quality Manager
    this.adaptive = new AdaptiveManager(this);

    // Conservative production startup: starts at 75,000 particles x 8 steps (or Low tier)
    // Preallocate maximum practical VBO capacity once to eliminate per-frame memory churn & black flashes
    const initialParticles = this.particlesOverride !== null ? this.particlesOverride : 75000;
    this.maxParticleCapacity = Math.max(600000, initialParticles);
    this.numParticles = initialParticles;
    this.stepsPerFrame = this.stepsOverride !== null ? this.stepsOverride : 8;

    // View state: zoom 1.65 displays full organism with calm central void and margins
    this.zoom = 1.65;
    this.targetZoom = 1.65;
    this.viewCenter = [0.0, 0.0];
    this.targetViewCenter = [0.0, 0.0];
    this.aspect = 1.0;

    // Accumulation & Progressive Refinement settings
    this.accumulationFrames = 0;
    this.persistence = 0.9985;
    this.currentPersistence = 0.9985;
    this.gain = 4.0;
    this.bloomEnabled = true;
    this.viewMode = 0; // 0: Final HDR, 1: No-Bloom, 2: Raw Trajectories
    this.showRawTrajectories = false;
    this.respawnRequested = false;

    // Frame statistics
    this.fps = 60;
    this.frameCount = 0;
    this.lastTime = performance.now();
    this.fpsUpdateTime = performance.now();

    this.initShaders();
    this.initBuffers();
    this.initTextures();

    // Development & diagnostic profiler
    this.profiler = new Profiler(this);
  }

  detectFloatCapability() {
    const gl = this.gl;
    // 1. Preferred path: Native RGBA32F with 32-bit floating-point blending
    // WebGL2 specification: EXT_color_buffer_float enables 32F renderability, while EXT_float_blend guarantees 32F blending
    const has32fBlend = !!this.extFloatBlend;
    if (this.extFloat && has32fBlend && this.testFboFormat(gl.RGBA32F, gl.FLOAT, true)) {
      return {
        internalFormat: gl.RGBA32F,
        format: gl.RGBA,
        type: gl.FLOAT,
        name: 'RGBA32F',
        label: 'Native RGBA32F Float Blending',
        photonScale: 1.0
      };
    }
    // 2. High-performance fallback: RGBA16F half-float (Safari, iOS, mobile WebGL2 implementations)
    // EXT_color_buffer_float guarantees blending support for 16F render targets in WebGL2
    if (this.extFloat && this.testFboFormat(gl.RGBA16F, gl.HALF_FLOAT, false)) {
      return {
        internalFormat: gl.RGBA16F,
        format: gl.RGBA,
        type: gl.HALF_FLOAT,
        name: 'RGBA16F',
        label: 'RGBA16F Half-Float Blending Fallback',
        photonScale: 8.0
      };
    }
    // 3. Emergency reduced-capability fallback: RGBA8 (calibrated photon scale avoids black canvas)
    return {
      internalFormat: gl.RGBA8,
      format: gl.RGBA,
      type: gl.UNSIGNED_BYTE,
      name: 'RGBA8',
      label: 'Reduced Precision RGBA8 Fallback',
      photonScale: 25.0
    };
  }

  testFboFormat(internalFormat, type, requireFloatBlend = false) {
    const gl = this.gl;
    try {
      if (requireFloatBlend && !this.extFloatBlend) {
        return false;
      }
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, internalFormat, 4, 4, 0, gl.RGBA, type, null);
      const fbo = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.deleteFramebuffer(fbo);
      gl.deleteTexture(tex);
      return status === gl.FRAMEBUFFER_COMPLETE;
    } catch (e) {
      return false;
    }
  }

  setParticleCount(count, preserveAccumulation = true) {
    this.particlesOverride = count;
    if (this.numParticles === count) return;

    const gl = this.gl;
    // Only reallocate GPU memory if count exceeds preallocated capacity
    if (count > this.maxParticleCapacity) {
      this.maxParticleCapacity = count;
      const initData = new Float32Array(this.maxParticleCapacity * 4);
      for (let i = 0; i < this.maxParticleCapacity; i++) {
        const r = 0.22 + Math.random() * 0.38;
        const th = Math.random() * 2 * Math.PI;
        initData[i * 4 + 0] = r * Math.cos(th);
        initData[i * 4 + 1] = r * Math.sin(th);
        initData[i * 4 + 2] = 0.0;
        initData[i * 4 + 3] = (Math.random() * 0xFFFFFF) >>> 0;
      }
      for (let i = 0; i < 2; i++) {
        gl.bindBuffer(gl.ARRAY_BUFFER, this.simVbos[i]);
        gl.bufferData(gl.ARRAY_BUFFER, initData, gl.STREAM_COPY);
      }
      gl.bindBuffer(gl.ARRAY_BUFFER, null);
    }

    this.numParticles = count;
    if (!preserveAccumulation) {
      this.clearAccumulation();
    }
  }

  setStepsOverride(steps) {
    this.stepsOverride = steps;
    if (steps !== null) {
      this.stepsPerFrame = steps;
    }
  }

  clearOverrides() {
    this.particlesOverride = null;
    this.stepsOverride = null;
  }

  initShaders() {
    const gl = this.gl;

    // 1. GPU Transform Feedback Simulation Shader (Discrete Mobius IFS Iteration)
    const simVs = `#version 300 es
      in vec4 a_state; // (z.x, z.y, age, seed)
      out vec4 v_state;

      uniform vec2 u_a;
      uniform vec2 u_b;
      uniform vec2 u_c;
      uniform vec2 u_d;
      uniform float u_n;
      uniform float u_step;
      uniform float u_time;
      uniform vec2 u_viewCenter;
      uniform float u_zoom;
      uniform float u_respawnAll;

      #define PI 3.14159265358979323846

      // Complex multiplication
      vec2 c_mul(vec2 x, vec2 y) {
        return vec2(x.x * y.x - x.y * y.y, x.x * y.y + x.y * y.x);
      }

      // Complex division
      vec2 c_div(vec2 num, vec2 den) {
        float den_mag_sq = dot(den, den);
        return vec2(
          (num.x * den.x + num.y * den.y) / den_mag_sq,
          (num.y * den.x - num.x * den.y) / den_mag_sq
        );
      }

      // High-performance PCG random integer hash
      uint pcg(uint v) {
        uint state = v * 747796405u + 2891336453u;
        uint word = ((state >> ((state >> 28u) + 4u)) ^ state) * 277803737u;
        return (word >> 22u) ^ word;
      }

      float nextRand(inout uint seed) {
        seed = pcg(seed);
        return float(seed & 0x00FFFFFFu) / 16777216.0;
      }

      void main() {
        vec2 z = a_state.xy;
        float age = a_state.z;
        uint seed = uint(abs(a_state.w)) + uint(u_step * 1013904223.0) + uint(gl_VertexID * 1973);

        // Respawn conditions: out-of-bounds, NaN, or aged out
        float r2 = dot(z, z);
        bool needsRespawn = (u_respawnAll > 0.5) || 
                            isnan(z.x) || isnan(z.y) || 
                            (r2 > 25.0) || (age > 3500.0) ||
                            (age == 0.0 && r2 < 0.04);

        if (needsRespawn) {
          float r1 = nextRand(seed);
          float r2_rnd = nextRand(seed);
          // Seed directly along the active attractor annulus outside the central void
          float r = 0.22 + r1 * 0.40;
          float theta = r2_rnd * 2.0 * PI;
          z = vec2(r * cos(theta), r * sin(theta));
          age = 0.0;
          v_state = vec4(z, age, float(seed & 0x00FFFFFFu));
          return;
        }

        // Discrete IFS step:
        // z_{t+1} = omega_k * (a*z_t + b) / (c*z_t + d)
        int n = int(u_n + 0.5);
        float rnd = nextRand(seed);
        int k = int(rnd * float(n)) % n;

        float ang = (2.0 * PI * float(k)) / float(n);
        vec2 omega = vec2(cos(ang), sin(ang));

        vec2 num = c_mul(u_a, z) + u_b;
        vec2 den = c_mul(u_c, z) + u_d;
        float den_sq = dot(den, den);

        if (den_sq < 1e-7) {
          float r1 = nextRand(seed);
          float theta = r1 * 2.0 * PI;
          z = vec2(0.35 * cos(theta), 0.35 * sin(theta));
          age = 0.0;
        } else {
          vec2 m = c_div(num, den);
          z = c_mul(omega, m);
          age += 1.0;
        }

        v_state = vec4(z, age, float(seed & 0x00FFFFFFu));
      }
    `;

    const simFs = `#version 300 es
      precision highp float;
      void main() {}
    `;

    // 2. Trajectory Point Splatting Shader (Renders points into Accumulation FBO)
    const splatVs = `#version 300 es
      in vec4 a_state;
      uniform vec2 u_viewCenter;
      uniform float u_zoom;
      uniform float u_aspect;

      out float v_discard;

      void main() {
        vec2 z = a_state.xy;
        float age = a_state.z;

        // Discard transient warmup steps and divergent/NaN points
        float r2 = dot(z, z);
        if (age < 25.0 || isnan(z.x) || isnan(z.y) || r2 > 36.0) {
          v_discard = 1.0;
          gl_Position = vec4(2.0, 2.0, 0.0, 1.0);
          gl_PointSize = 1.0;
          return;
        }
        v_discard = 0.0;

        vec2 clip = (z - u_viewCenter) * u_zoom;
        if (u_aspect > 1.0) {
          clip.x /= u_aspect;
        } else {
          clip.y *= u_aspect;
        }

        gl_Position = vec4(clip, 0.0, 1.0);
        // Razor-sharp subpixel point across all scales preserves fine filamentary separation
        gl_PointSize = 1.0;
      }
    `;

    const splatFs = `#version 300 es
      precision highp float;
      in float v_discard;
      out vec4 o_photon;
      uniform float u_photonScale;

      void main() {
        if (v_discard > 0.5) discard;
        // Fine photon deposit preserves filament detail across millions of cumulative hits
        float photon = 0.00010 * u_photonScale;
        o_photon = vec4(photon * 0.9, photon * 1.3, photon * 2.2, 1.0);
      }
    `;

    // 3. Accumulation Decay & Persistence Shader
    const quadVs = `#version 300 es
      in vec2 a_pos;
      out vec2 v_uv;
      void main() {
        v_uv = a_pos * 0.5 + 0.5;
        gl_Position = vec4(a_pos, 0.0, 1.0);
      }
    `;

    const decayFs = `#version 300 es
      precision highp float;
      in vec2 v_uv;
      out vec4 o_color;
      uniform sampler2D u_accumTex;
      uniform float u_persistence;

      void main() {
        vec4 val = texture(u_accumTex, v_uv);
        o_color = val * u_persistence;
      }
    `;

    // 4. Color Grading, Extended Dynamic Range HDR Tonemapping & Palette Composite
    const postFs = `#version 300 es
      precision highp float;
      in vec2 v_uv;
      out vec4 o_final;

      uniform sampler2D u_accumTex;
      uniform sampler2D u_bloomTex;
      uniform float u_gain;
      uniform float u_viewMode; // 0.0: Final HDR, 1.0: No-Bloom, 2.0: Raw Trajectories
      uniform float u_bloomEnabled;
      uniform float u_photonScale;

      void main() {
        vec4 accum = texture(u_accumTex, v_uv);
        float density = (accum.b / max(0.001, u_photonScale)) * u_gain;

        // Scientific comparison view mode: RAW TRAJECTORIES
        if (u_viewMode > 1.5) {
          float rawVal = clamp(density * 0.45, 0.0, 1.0);
          o_final = vec4(vec3(rawVal), 1.0);
          return;
        }

        // Extended dynamic range photographic logarithmic tonemapper
        // Retains filament striations even at massive density, prevents clipping to solid white bands
        float alpha = 0.65;
        float logD = log(1.0 + density * alpha);
        float norm = logD / (1.0 + logD * 0.24);
        norm = clamp(norm * 0.42, 0.0, 1.15);

        // Required Color Hierarchy from reference:
        // Background: pitch black with subtle blue-black bias (#010307)
        vec3 col_bg = vec3(0.004, 0.010, 0.022);
        // Deep midnight cobalt for outer atmosphere (#05112a)
        vec3 col_midnight = vec3(0.020, 0.068, 0.170);
        // Cerulean / electric blue for mid filaments (#1468d6)
        vec3 col_electric = vec3(0.078, 0.408, 0.839);
        // Delicate icy blue (#92d8ff)
        vec3 col_icy = vec3(0.573, 0.847, 1.000);
        // Brilliant caustic white (#ffffff)
        vec3 col_white = vec3(1.0, 1.0, 1.0);

        vec3 c = col_bg;
        if (norm < 0.12) {
          float t = norm / 0.12;
          // Smooth linear fade into midnight cobalt reveals the faint outer atmosphere
          c = mix(col_bg, col_midnight, t);
        } else if (norm < 0.46) {
          float t = (norm - 0.12) / 0.34;
          c = mix(col_midnight, col_electric, smoothstep(0.0, 1.0, t));
        } else if (norm < 0.82) {
          float t = (norm - 0.46) / 0.36;
          c = mix(col_electric, col_icy, smoothstep(0.0, 1.0, t));
        } else {
          // Soft asymptotic shoulder: dense regions remain intricate instead of clipping into solid white
          float t = clamp((norm - 0.82) / 0.33, 0.0, 1.0);
          t = t * t * (3.0 - 2.0 * t);
          c = mix(col_icy, col_white, t * 0.85); // Retain icy filament linework at peak
        }

        // Secondary Ethereal Bloom (Mode 0 only)
        if (u_viewMode < 0.5 && u_bloomEnabled > 0.5) {
          vec4 bloom = texture(u_bloomTex, v_uv);
          float bVal = (bloom.b / max(0.001, u_photonScale)) * 1.5;
          float bNorm = bVal / (1.0 + bVal * 0.9);
          vec3 bCol = mix(col_midnight, col_electric, clamp(bNorm * 1.5, 0.0, 1.0));
          c += bCol * 0.045 * clamp(bNorm, 0.0, 1.0);
        }

        // Extremely subtle photographic vignette (leaves outer field atmosphere intact)
        vec2 uvMid = v_uv - 0.5;
        float vig = 1.0 - dot(uvMid, uvMid) * 0.25;
        c *= max(0.0, vig);

        o_final = vec4(c, 1.0);
      }
    `;

    // 5. Raw Trajectory Orbits Shader (Debug Verification Mode)
    const rawVs = `#version 300 es
      in vec2 a_pos;
      in float a_alpha;
      uniform vec2 u_viewCenter;
      uniform float u_zoom;
      uniform float u_aspect;
      out float v_alpha;

      void main() {
        v_alpha = a_alpha;
        vec2 clip = (a_pos - u_viewCenter) * u_zoom;
        if (u_aspect > 1.0) {
          clip.x /= u_aspect;
        } else {
          clip.y *= u_aspect;
        }
        gl_Position = vec4(clip, 0.0, 1.0);
        gl_PointSize = clamp(3.0 * a_alpha, 1.5, 4.0);
      }
    `;

    const rawFs = `#version 300 es
      precision highp float;
      in float v_alpha;
      out vec4 o_color;

      void main() {
        vec2 c = gl_PointCoord - vec2(0.5);
        if (dot(c, c) > 0.25) discard;
        o_color = vec4(0.25, 0.85, 1.0, 0.9 * v_alpha);
      }
    `;

    // 6. Blur / Bloom Pass Shader (High-pass thresholded so only dense caustic knots emit bloom)
    const blurVs = quadVs;
    const blurFs = `#version 300 es
      precision highp float;
      in vec2 v_uv;
      out vec4 o_color;
      uniform sampler2D u_image;
      uniform vec2 u_dir;

      vec4 sampleThresh(vec2 uv) {
        vec4 val = texture(u_image, uv);
        float caustic = max(0.0, val.b - 0.75);
        return vec4(caustic);
      }

      void main() {
        vec2 off = u_dir;
        vec4 sum = vec4(0.0);
        sum += sampleThresh(v_uv - off * 3.0) * 0.06;
        sum += sampleThresh(v_uv - off * 2.0) * 0.12;
        sum += sampleThresh(v_uv - off * 1.0) * 0.20;
        sum += sampleThresh(v_uv) * 0.24;
        sum += sampleThresh(v_uv + off * 1.0) * 0.20;
        sum += sampleThresh(v_uv + off * 2.0) * 0.12;
        sum += sampleThresh(v_uv + off * 3.0) * 0.06;
        o_color = sum;
      }
    `;

    // Compile & link Transform Feedback program
    const simV = this.createShader(gl.VERTEX_SHADER, simVs);
    const simF = this.createShader(gl.FRAGMENT_SHADER, simFs);
    this.simProg = gl.createProgram();
    gl.attachShader(this.simProg, simV);
    gl.attachShader(this.simProg, simF);
    gl.transformFeedbackVaryings(this.simProg, ['v_state'], gl.SEPARATE_ATTRIBS);
    gl.linkProgram(this.simProg);
    if (!gl.getProgramParameter(this.simProg, gl.LINK_STATUS)) {
      throw new Error('Sim program link error: ' + gl.getProgramInfoLog(this.simProg));
    }

    this.splatProg = this.createProgram(splatVs, splatFs);
    this.decayProg = this.createProgram(quadVs, decayFs);
    this.postProg = this.createProgram(quadVs, postFs);
    this.rawProg = this.createProgram(rawVs, rawFs);
    this.blurProg = this.createProgram(blurVs, blurFs);

    // Cache uniform locations at initialization to avoid per-frame string hash lookups
    this.simUniforms = {
      a: gl.getUniformLocation(this.simProg, 'u_a'),
      b: gl.getUniformLocation(this.simProg, 'u_b'),
      c: gl.getUniformLocation(this.simProg, 'u_c'),
      d: gl.getUniformLocation(this.simProg, 'u_d'),
      n: gl.getUniformLocation(this.simProg, 'u_n'),
      time: gl.getUniformLocation(this.simProg, 'u_time'),
      viewCenter: gl.getUniformLocation(this.simProg, 'u_viewCenter'),
      zoom: gl.getUniformLocation(this.simProg, 'u_zoom'),
      respawnAll: gl.getUniformLocation(this.simProg, 'u_respawnAll'),
      step: gl.getUniformLocation(this.simProg, 'u_step')
    };
    this.splatUniforms = {
      viewCenter: gl.getUniformLocation(this.splatProg, 'u_viewCenter'),
      zoom: gl.getUniformLocation(this.splatProg, 'u_zoom'),
      aspect: gl.getUniformLocation(this.splatProg, 'u_aspect'),
      photonScale: gl.getUniformLocation(this.splatProg, 'u_photonScale')
    };
    this.decayUniforms = {
      accumTex: gl.getUniformLocation(this.decayProg, 'u_accumTex'),
      persistence: gl.getUniformLocation(this.decayProg, 'u_persistence')
    };
    this.blurUniforms = {
      image: gl.getUniformLocation(this.blurProg, 'u_image'),
      dir: gl.getUniformLocation(this.blurProg, 'u_dir')
    };
    this.postUniforms = {
      accumTex: gl.getUniformLocation(this.postProg, 'u_accumTex'),
      bloomTex: gl.getUniformLocation(this.postProg, 'u_bloomTex'),
      gain: gl.getUniformLocation(this.postProg, 'u_gain'),
      bloomEnabled: gl.getUniformLocation(this.postProg, 'u_bloomEnabled'),
      viewMode: gl.getUniformLocation(this.postProg, 'u_viewMode'),
      photonScale: gl.getUniformLocation(this.postProg, 'u_photonScale')
    };
    this.rawUniforms = {
      viewCenter: gl.getUniformLocation(this.rawProg, 'u_viewCenter'),
      zoom: gl.getUniformLocation(this.rawProg, 'u_zoom'),
      aspect: gl.getUniformLocation(this.rawProg, 'u_aspect')
    };
  }

  createShader(type, src) {
    const gl = this.gl;
    const shader = gl.createShader(type);
    gl.shaderSource(shader, src);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const err = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error('Shader compile error: ' + err);
    }
    return shader;
  }

  createProgram(vsSrc, fsSrc) {
    const gl = this.gl;
    const vs = this.createShader(gl.VERTEX_SHADER, vsSrc);
    const fs = this.createShader(gl.FRAGMENT_SHADER, fsSrc);
    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      const err = gl.getProgramInfoLog(prog);
      gl.deleteProgram(prog);
      throw new Error('Program link error: ' + err);
    }
    return prog;
  }

  initBuffers() {
    const gl = this.gl;

    // Fullscreen quad
    const quadVerts = new Float32Array([
      -1, -1,
       1, -1,
      -1,  1,
      -1,  1,
       1, -1,
       1,  1
    ]);

    this.quadVao = gl.createVertexArray();
    gl.bindVertexArray(this.quadVao);
    const quadVbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, quadVbo);
    gl.bufferData(gl.ARRAY_BUFFER, quadVerts, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);

    // Preallocate Ping-pong Transform Feedback VBOs once up to maxParticleCapacity: vec4(z.x, z.y, age, seed)
    const initData = new Float32Array(this.maxParticleCapacity * 4);
    for (let i = 0; i < this.maxParticleCapacity; i++) {
      const r = 0.22 + Math.random() * 0.38;
      const th = Math.random() * 2 * Math.PI;
      initData[i * 4 + 0] = r * Math.cos(th);
      initData[i * 4 + 1] = r * Math.sin(th);
      initData[i * 4 + 2] = 0.0;
      initData[i * 4 + 3] = (Math.random() * 0xFFFFFF) >>> 0;
    }

    this.simVbos = [gl.createBuffer(), gl.createBuffer()];
    this.simVaos = [gl.createVertexArray(), gl.createVertexArray()];
    this.splatVaos = [gl.createVertexArray(), gl.createVertexArray()];

    for (let i = 0; i < 2; i++) {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.simVbos[i]);
      gl.bufferData(gl.ARRAY_BUFFER, initData, gl.STREAM_COPY);

      // Simulation VAO
      gl.bindVertexArray(this.simVaos[i]);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 16, 0);

      // Splat VAO (reads the exact same buffer directly as vertex attributes)
      gl.bindVertexArray(this.splatVaos[i]);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 16, 0);
    }
    gl.bindVertexArray(null);
    this.vboCur = 0;

    // Raw trajectories buffer (32 discrete chains * 64 hops)
    this.numRawCurves = 32;
    this.rawCurveSteps = 64;
    this.rawVerts = new Float32Array(this.numRawCurves * this.rawCurveSteps * 3);

    this.rawVao = gl.createVertexArray();
    gl.bindVertexArray(this.rawVao);
    this.rawVbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.rawVbo);
    gl.bufferData(gl.ARRAY_BUFFER, this.rawVerts.byteLength, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 12, 0);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 1, gl.FLOAT, false, 12, 8);
    gl.bindVertexArray(null);
  }

  initTextures() {
    const gl = this.gl;

    // Accumulation Ping-Pong FBOs with controlled adaptive DPR (max 1.5)
    const initialDpr = this.adaptive ? this.adaptive.getDpr() : Math.min(1.5, (typeof window !== 'undefined' && window.devicePixelRatio) || 1.0);
    const winW = (typeof window !== 'undefined' && window.innerWidth) ? window.innerWidth : 1200;
    const winH = (typeof window !== 'undefined' && window.innerHeight) ? window.innerHeight : 800;
    this.accumWidth = Math.max(1, Math.min(2048, Math.floor(winW * initialDpr)));
    this.accumHeight = Math.max(1, Math.min(2048, Math.floor(winH * initialDpr)));

    this.accumTextures = [
      this.createFloatTexture(this.accumWidth, this.accumHeight, null),
      this.createFloatTexture(this.accumWidth, this.accumHeight, null)
    ];
    this.accumFbos = [
      this.createFbo(this.accumTextures[0]),
      this.createFbo(this.accumTextures[1])
    ];
    this.accumReadIdx = 0;

    for (const fbo of this.accumFbos) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    // Bloom downsample FBOs (1/4 size)
    this.bloomWidth = Math.max(1, Math.floor(this.accumWidth / 4));
    this.bloomHeight = Math.max(1, Math.floor(this.accumHeight / 4));
    this.bloomTextures = [
      this.createFloatTexture(this.bloomWidth, this.bloomHeight, null),
      this.createFloatTexture(this.bloomWidth, this.bloomHeight, null)
    ];
    this.bloomFbos = [
      this.createFbo(this.bloomTextures[0]),
      this.createFbo(this.bloomTextures[1])
    ];
  }

  createFloatTexture(width, height, data) {
    const gl = this.gl;
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(
      gl.TEXTURE_2D, 0,
      this.floatCap.internalFormat,
      width, height, 0,
      this.floatCap.format, this.floatCap.type,
      data
    );
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return tex;
  }

  createFbo(tex) {
    const gl = this.gl;
    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
    if (status !== gl.FRAMEBUFFER_COMPLETE) {
      throw new Error('Framebuffer incomplete: ' + status);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return fbo;
  }

  resize(width, height) {
    if (width <= 0 || height <= 0) return;
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
      this.aspect = width / height;

      const newW = Math.min(2048, width);
      const newH = Math.min(2048, height);
      if (Math.abs(newW - this.accumWidth) > 64 || Math.abs(newH - this.accumHeight) > 64) {
        this.accumWidth = newW;
        this.accumHeight = newH;
        const gl = this.gl;
        for (let i = 0; i < 2; i++) {
          gl.deleteTexture(this.accumTextures[i]);
          gl.deleteFramebuffer(this.accumFbos[i]);
          this.accumTextures[i] = this.createFloatTexture(this.accumWidth, this.accumHeight, null);
          this.accumFbos[i] = this.createFbo(this.accumTextures[i]);
          gl.bindFramebuffer(gl.FRAMEBUFFER, this.accumFbos[i]);
          gl.clearColor(0, 0, 0, 0);
          gl.clear(gl.COLOR_BUFFER_BIT);
        }
        this.bloomWidth = Math.max(1, Math.floor(this.accumWidth / 4));
        this.bloomHeight = Math.max(1, Math.floor(this.accumHeight / 4));
        for (let i = 0; i < 2; i++) {
          gl.deleteTexture(this.bloomTextures[i]);
          gl.deleteFramebuffer(this.bloomFbos[i]);
          this.bloomTextures[i] = this.createFloatTexture(this.bloomWidth, this.bloomHeight, null);
          this.bloomFbos[i] = this.createFbo(this.bloomTextures[i]);
        }
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        this.accumulationFrames = 0;
      }
    }
  }

  clearAccumulation() {
    const gl = this.gl;
    for (const fbo of this.accumFbos) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    this.accumulationFrames = 0;
  }

  startSymmetryTransition() {
    // Graceful continuous transition instead of harsh black flash
    this.currentPersistence = 0.90;
    this.accumulationFrames = 0;
  }

  render(mathSys, dt, jsTime = 0) {
    const gl = this.gl;
    if (this.profiler) {
      this.profiler.beginFrame(jsTime);
    }

    // Smooth camera interpolation
    const camLerp = Math.min(1.0, dt * 8.0);
    const prevZoom = this.zoom;
    const prevCenter0 = this.viewCenter[0];
    const prevCenter1 = this.viewCenter[1];

    this.zoom += (this.targetZoom - this.zoom) * camLerp;
    this.viewCenter[0] += (this.targetViewCenter[0] - this.viewCenter[0]) * camLerp;
    this.viewCenter[1] += (this.targetViewCenter[1] - this.viewCenter[1]) * camLerp;

    // Detect active camera movement
    const isCameraMoving = Math.abs(this.zoom - prevZoom) > 0.001 ||
                           Math.hypot(this.viewCenter[0] - prevCenter0, this.viewCenter[1] - prevCenter1) > 0.0005;

    // Detect if mathematical state is actively disturbed (pointer damping or shock relaxation)
    const isMathDisturbed = Math.hypot(mathSys.pointerTarget.r - mathSys.pointerCurrent.r, mathSys.pointerTarget.i - mathSys.pointerCurrent.i) > 0.005 ||
                            mathSys.shockMag > 0.05;

    // Feed measured GPU frame time from timer queries into adaptive manager BEFORE updating adaptive state
    if (this.profiler && this.profiler.metrics.gpuSupported && this.profiler.metrics.gpuMs !== null && this.profiler.metrics.gpuMs > 0) {
      this.adaptive.recordGpuTime(this.profiler.metrics.gpuMs);
    } else if (this.profiler) {
      this.adaptive.recordCpuFallbackTime(this.profiler.metrics.cpuMs);
    }

    // Update adaptive quality manager
    this.adaptive.update(dt, isCameraMoving);

    // Bounded Adaptive Workload Determination:
    if (this.particlesOverride !== null) {
      this.numParticles = this.particlesOverride;
    }
    if (this.stepsOverride !== null) {
      this.stepsPerFrame = this.stepsOverride;
    }
    if (this.particlesOverride === null || this.stepsOverride === null) {
      const workload = this.adaptive.getWorkload(this.zoom);
      if (this.particlesOverride === null) {
        this.numParticles = workload.particles;
      }
      if (this.stepsOverride === null) {
        this.stepsPerFrame = workload.steps;
      }
    }

    // Drift-Aware Dynamic Progressive Refinement Persistence:
    let targetPersistence;
    if (isCameraMoving || isMathDisturbed || this.adaptive.isInteracting) {
      // 1. Active interaction (pointer movement, drag/pan, zoom, or shock disturbance):
      targetPersistence = 0.97;
    } else if (!mathSys.evolving) {
      // 2. Stationary idle (drift paused or static coefficients):
      targetPersistence = 0.99925;
    } else {
      // 3. Autonomous coefficient drift active:
      targetPersistence = 0.9985;
    }
    this.currentPersistence += (targetPersistence - this.currentPersistence) * Math.min(1.0, dt * 4.0);

    // Track FPS
    this.frameCount++;
    const now = performance.now();
    if (now - this.fpsUpdateTime > 500) {
      this.fps = Math.round((this.frameCount * 1000) / (now - this.fpsUpdateTime));
      this.frameCount = 0;
      this.fpsUpdateTime = now;
    }

    // -------------------------------------------------------------
    // PASS 1: Accumulation Decay & Persistence
    // -------------------------------------------------------------
    if (this.profiler) this.profiler.beginPass('decay');
    const accumReadTex = this.accumTextures[this.accumReadIdx];
    const accumWriteFbo = this.accumFbos[1 - this.accumReadIdx];

    gl.bindFramebuffer(gl.FRAMEBUFFER, accumWriteFbo);
    gl.viewport(0, 0, this.accumWidth, this.accumHeight);

    gl.useProgram(this.decayProg);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, accumReadTex);
    gl.uniform1i(this.decayUniforms.accumTex, 0);
    gl.uniform1f(this.decayUniforms.persistence, this.currentPersistence);

    gl.bindVertexArray(this.quadVao);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    if (this.profiler) {
      this.profiler.recordDrawCall();
      this.profiler.endPass('decay');
    }

    // -------------------------------------------------------------
    // PASS 2 & 3: Multi-Step Simulation & Direct Splatting
    // -------------------------------------------------------------
    // Interleave Transform Feedback simulation and splatting so 100% of generated trajectory
    // points deposit photons into the accumulation buffer (zero discarded steps!)
    gl.bindFramebuffer(gl.FRAMEBUFFER, accumWriteFbo);
    gl.viewport(0, 0, this.accumWidth, this.accumHeight);

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE);

    gl.useProgram(this.splatProg);
    gl.uniform2f(this.splatUniforms.viewCenter, this.viewCenter[0], this.viewCenter[1]);
    gl.uniform1f(this.splatUniforms.zoom, this.zoom);
    gl.uniform1f(this.splatUniforms.aspect, this.aspect);
    gl.uniform1f(this.splatUniforms.photonScale, this.floatCap.photonScale || 1.0);

    gl.useProgram(this.simProg);
    gl.uniform2f(this.simUniforms.a, mathSys.a.r, mathSys.a.i);
    gl.uniform2f(this.simUniforms.b, mathSys.b.r, mathSys.b.i);
    gl.uniform2f(this.simUniforms.c, mathSys.c.r, mathSys.c.i);
    gl.uniform2f(this.simUniforms.d, mathSys.d.r, mathSys.d.i);
    gl.uniform1f(this.simUniforms.n, mathSys.n);
    gl.uniform1f(this.simUniforms.time, mathSys.time);
    gl.uniform2f(this.simUniforms.viewCenter, this.viewCenter[0], this.viewCenter[1]);
    gl.uniform1f(this.simUniforms.zoom, this.zoom);
    gl.uniform1f(this.simUniforms.respawnAll, this.respawnRequested ? 1.0 : 0.0);
    this.respawnRequested = false;

    const uStepLoc = this.simUniforms.step;
    const steps = this.stepsPerFrame;

    for (let s = 0; s < steps; s++) {
      // 1. GPU Transform feedback simulation step
      if (this.profiler) this.profiler.beginPass('sim', s);
      gl.useProgram(this.simProg);
      gl.uniform1f(uStepLoc, s);
      gl.enable(gl.RASTERIZER_DISCARD);
      gl.bindVertexArray(this.simVaos[this.vboCur]);
      gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, this.simVbos[1 - this.vboCur]);
      gl.beginTransformFeedback(gl.POINTS);
      gl.drawArrays(gl.POINTS, 0, this.numParticles);
      gl.endTransformFeedback();
      gl.disable(gl.RASTERIZER_DISCARD);
      gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, null);
      this.vboCur = 1 - this.vboCur;
      if (this.profiler) {
        this.profiler.recordDrawCall();
        this.profiler.endPass('sim', s);
      }

      // 2. Splat newly evolved trajectory positions into floating-point accumulation buffer
      if (this.profiler) this.profiler.beginPass('splat', s);
      gl.useProgram(this.splatProg);
      gl.bindVertexArray(this.splatVaos[this.vboCur]);
      gl.drawArrays(gl.POINTS, 0, this.numParticles);
      if (this.profiler) {
        this.profiler.recordDrawCall();
        this.profiler.endPass('splat', s);
      }
    }

    gl.disable(gl.BLEND);

    // Accumulation ping-pong swap
    this.accumReadIdx = 1 - this.accumReadIdx;
    const accumCurrentTex = this.accumTextures[this.accumReadIdx];
    this.accumulationFrames++;

    // -------------------------------------------------------------
    // PASS 4: Bloom Downsample & Separable Blur
    // -------------------------------------------------------------
    if (this.profiler) this.profiler.beginPass('bloom');
    if (this.bloomEnabled) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, this.bloomFbos[0]);
      gl.viewport(0, 0, this.bloomWidth, this.bloomHeight);
      gl.useProgram(this.blurProg);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, accumCurrentTex);
      gl.uniform1i(this.blurUniforms.image, 0);
      gl.uniform2f(this.blurUniforms.dir, 1.5 / this.bloomWidth, 0.0);
      gl.bindVertexArray(this.quadVao);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      if (this.profiler) this.profiler.recordDrawCall();

      gl.bindFramebuffer(gl.FRAMEBUFFER, this.bloomFbos[1]);
      gl.bindTexture(gl.TEXTURE_2D, this.bloomTextures[0]);
      gl.uniform2f(this.blurUniforms.dir, 0.0, 1.5 / this.bloomHeight);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      if (this.profiler) this.profiler.recordDrawCall();
    }
    if (this.profiler) this.profiler.endPass('bloom');

    // -------------------------------------------------------------
    // PASS 5: Screen Tonemapping & Palette Composite
    // -------------------------------------------------------------
    if (this.profiler) this.profiler.beginPass('post');
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);

    gl.useProgram(this.postProg);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, accumCurrentTex);
    gl.uniform1i(this.postUniforms.accumTex, 0);

    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, this.bloomTextures[1]);
    gl.uniform1i(this.postUniforms.bloomTex, 1);

    const zoomMag = Math.max(1.0, this.zoom / 1.65);
    const adaptiveGain = this.gain * (1.0 + Math.pow(zoomMag - 1.0, 0.85) * 2.8);
    gl.uniform1f(this.postUniforms.gain, adaptiveGain);
    gl.uniform1f(this.postUniforms.bloomEnabled, this.bloomEnabled ? 1.0 : 0.0);
    gl.uniform1f(this.postUniforms.viewMode, this.viewMode);
    gl.uniform1f(this.postUniforms.photonScale, this.floatCap.photonScale || 1.0);

    gl.bindVertexArray(this.quadVao);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    if (this.profiler) {
      this.profiler.recordDrawCall();
      this.profiler.endPass('post');
    }

    // -------------------------------------------------------------
    // PASS 6: Raw Trajectories Overlay (Debug Verification Mode)
    // -------------------------------------------------------------
    if (this.showRawTrajectories) {
      this.renderRawTrajectories(mathSys);
      if (this.profiler) this.profiler.recordDrawCall();
    }

    if (this.profiler) {
      this.profiler.endFrame(dt);
    }
    gl.flush();
  }

  renderRawTrajectories(mathSys) {
    const gl = this.gl;
    this.evalRawIFS(mathSys);

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE);

    gl.useProgram(this.rawProg);
    gl.uniform2f(this.rawUniforms.viewCenter, this.viewCenter[0], this.viewCenter[1]);
    gl.uniform1f(this.rawUniforms.zoom, this.zoom);
    gl.uniform1f(this.rawUniforms.aspect, this.aspect);

    gl.bindVertexArray(this.rawVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.rawVbo);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, this.rawVerts);

    // Draw individual discrete orbit beads/dots on the attractor
    const totalPoints = this.numRawCurves * this.rawCurveSteps;
    gl.drawArrays(gl.POINTS, 0, totalPoints);

    gl.disable(gl.BLEND);
  }

  evalRawIFS(mathSys) {
    const numCurves = this.numRawCurves;
    const steps = this.rawCurveSteps;
    let ptr = 0;
    const omegas = mathSys.omegas;
    const n = mathSys.n;

    for (let c = 0; c < numCurves; c++) {
      const th = (2 * Math.PI * c) / numCurves;
      let zr = 0.32 * Math.cos(th);
      let zi = 0.32 * Math.sin(th);

      // Warmup 30 steps to converge strictly onto attractor
      for (let w = 0; w < 30; w++) {
        const k = (c * 7 + w * 11) % n;
        const res = this.evalMobiusCpu(mathSys.a, mathSys.b, mathSys.c, mathSys.d, zr, zi, omegas[k]);
        zr = res[0]; zi = res[1];
      }

      // Record subsequent discrete orbit hops
      for (let s = 0; s < steps; s++) {
        this.rawVerts[ptr++] = zr;
        this.rawVerts[ptr++] = zi;
        this.rawVerts[ptr++] = 1.0 - (s / steps) * 0.70;

        const k = (c * 13 + s * 7) % n;
        const res = this.evalMobiusCpu(mathSys.a, mathSys.b, mathSys.c, mathSys.d, zr, zi, omegas[k]);
        zr = res[0]; zi = res[1];
        if (Math.hypot(zr, zi) > 5.0) {
          zr = 0.32 * Math.cos(th);
          zi = 0.32 * Math.sin(th);
        }
      }
    }
  }

  evalMobiusCpu(A, B, C, D, zr, zi, omega) {
    // num = A * z + B
    const num_r = A.r * zr - A.i * zi + B.r;
    const num_i = A.r * zi + A.i * zr + B.i;

    // den = C * z + D
    const den_r = C.r * zr - C.i * zi + D.r;
    const den_i = C.r * zi + C.i * zr + D.i;

    const den_sq = Math.max(1e-7, den_r * den_r + den_i * den_i);
    const inv_r = den_r / den_sq;
    const inv_i = -den_i / den_sq;

    // m = num / den
    const mr = num_r * inv_r - num_i * inv_i;
    const mi = num_r * inv_i + num_i * inv_r;

    // omega * m
    return [
      omega.r * mr - omega.i * mi,
      omega.r * mi + omega.i * mr
    ];
  }
}
