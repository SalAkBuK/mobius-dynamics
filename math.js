/**
 * Core Mathematics for Mobius Complex Dynamics Laboratory
 * 
 * Mobius Transformation: f(z) = (az + b) / (cz + d)
 * Roots of Unity: omega_k = e^(2*pi*i*k / n)
 */

export class Complex {
  constructor(r = 0, i = 0) {
    this.r = r;
    this.i = i;
  }

  static fromAngle(theta, r = 1) {
    return new Complex(r * Math.cos(theta), r * Math.sin(theta));
  }

  clone() {
    return new Complex(this.r, this.i);
  }

  add(c) {
    return new Complex(this.r + c.r, this.i + c.i);
  }

  sub(c) {
    return new Complex(this.r - c.r, this.i - c.i);
  }

  mul(c) {
    return new Complex(
      this.r * c.r - this.i * c.i,
      this.r * c.i + this.i * c.r
    );
  }

  scale(s) {
    return new Complex(this.r * s, this.i * s);
  }

  div(c) {
    const d = c.r * c.r + c.i * c.i;
    if (d === 0) return new Complex(0, 0);
    return new Complex(
      (this.r * c.r + this.i * c.i) / d,
      (this.i * c.r - this.r * c.i) / d
    );
  }

  conj() {
    return new Complex(this.r, -this.i);
  }

  abs() {
    return Math.hypot(this.r, this.i);
  }

  absSq() {
    return this.r * this.r + this.i * this.i;
  }

  phase() {
    return Math.atan2(this.i, this.r);
  }

  format(digits = 3) {
    const rStr = this.r.toFixed(digits);
    const iSign = this.i >= 0 ? '+' : '-';
    const iStr = Math.abs(this.i).toFixed(digits);
    return `${rStr} ${iSign} ${iStr}i`;
  }
}

/**
 * Mobius Transformation: M(z) = (az + b) / (cz + d)
 */
export class MobiusTransform {
  constructor(a, b, c, d) {
    this.a = a;
    this.b = b;
    this.c = c;
    this.d = d;
  }

  eval(z) {
    const num = this.a.mul(z).add(this.b);
    const den = this.c.mul(z).add(this.d);
    return num.div(den);
  }

  inverse() {
    return new MobiusTransform(
      this.d.clone(),
      this.b.scale(-1),
      this.c.scale(-1),
      this.a.clone()
    );
  }

  compose(other) {
    // M1(M2(z)): [a1, b1; c1, d1] * [a2, b2; c2, d2]
    const a = this.a.mul(other.a).add(this.b.mul(other.c));
    const b = this.a.mul(other.b).add(this.b.mul(other.d));
    const c = this.c.mul(other.a).add(this.d.mul(other.c));
    const d = this.c.mul(other.b).add(this.d.mul(other.d));
    return new MobiusTransform(a, b, c, d);
  }

  det() {
    return this.a.mul(this.d).sub(this.b.mul(this.c));
  }

  normalize() {
    const d = this.det();
    const mag = Math.sqrt(d.abs());
    if (mag > 1e-12) {
      const halfAng = d.phase() * 0.5;
      const sq = Complex.fromAngle(halfAng, mag);
      this.a = this.a.div(sq);
      this.b = this.b.div(sq);
      this.c = this.c.div(sq);
      this.d = this.d.div(sq);
    }
    return this;
  }
}

export const CONRADI_REFERENCE = {
  name: 'Simone Conradi Reference (Orbital Lace)',
  description: 'Exact published Simone Conradi 2026 Mobius IFS attractor (16-fold rosette)',
  n: 16,
  a: new Complex(-0.755, 0.330),
  b: new Complex(-0.376, 0.026),
  c: new Complex(6.401, 0.803),
  d: new Complex(1.520, 0.840),
  zoom: 1.65,
  center: [0.0, 0.0]
};

export const RANDOM_STYLES = [
  'conradi-like',
  'subtle',
  'organic',
  'dense lace',
  'symmetric',
  'chaotic'
];

export const MORPHOLOGIES = {
  lace: {
    key: 'lace',
    name: 'Simone Conradi (Orbital Lace)',
    description: 'Exact Simone Conradi 2026 Mobius attractor with pristine 16-fold rosette',
    n: 16,
    a: new Complex(-0.755, 0.330),
    b: new Complex(-0.376, 0.026),
    c: new Complex(6.401, 0.803),
    d: new Complex(1.520, 0.840)
  },
  knot: {
    key: 'knot',
    name: 'Organic Knot',
    description: 'Less perfect radial structure, large chambers, pinched intersections, recursive curls',
    n: 8,
    a: new Complex(-0.755, 0.330),
    b: new Complex(-0.376, 0.026),
    c: new Complex(6.401, 0.803),
    d: new Complex(1.520, 0.840)
  },
  crown: {
    key: 'crown',
    name: 'Caustic Crown',
    description: 'Strong inner orbital boundary, complex interference outside it',
    n: 16,
    a: new Complex(-0.785, 0.315),
    b: new Complex(-0.410, 0.010),
    c: new Complex(6.650, 0.650),
    d: new Complex(1.580, 0.920)
  },
  storm: {
    key: 'storm',
    name: 'Filament Storm',
    description: 'Interlocking braided secondary orbit families with counter-rotating wave crests',
    n: 24,
    a: new Complex(-0.710, 0.420),
    b: new Complex(-0.395, 0.010),
    c: new Complex(7.350, 0.650),
    d: new Complex(1.650, 0.820)
  },
  specimen: {
    key: 'specimen',
    name: 'Deep-Recursion Specimen',
    description: 'Concentric levels of nested structure with micro-caustics across scales',
    n: 12,
    a: new Complex(-0.755, 0.330),
    b: new Complex(-0.376, 0.026),
    c: new Complex(6.401, 0.803),
    d: new Complex(1.520, 0.840)
  }
};

/**
 * Mathematical System Controller
 * Governs the authentic Mobius parameters, autonomous micro-drift,
 * pointer perturbations, click shocks, mode architecture, and multiscale iterated transforms.
 */
export class MathSystem {
  constructor(initialMode = 'explore') {
    this.mode = initialMode; // 'reference' | 'explore'
    this.pointerPerturbationEnabled = (initialMode === 'explore');
    this.shockEnabled = (initialMode === 'explore');

    this.n = 16;
    this.activeMorphology = 'lace';

    // Mathematical base coefficients generating authentic Mobius IFS attractor (Simone Conradi, 2026):
    this.baseA = CONRADI_REFERENCE.a.clone();
    this.baseB = CONRADI_REFERENCE.b.clone();
    this.baseC = CONRADI_REFERENCE.c.clone();
    this.baseD = CONRADI_REFERENCE.d.clone();

    // User manual adjustment offsets (via optional coefficient controls)
    this.userOffsetA = new Complex(0, 0);
    this.userOffsetB = new Complex(0, 0);
    this.userOffsetC = new Complex(0, 0);
    this.userOffsetD = new Complex(0, 0);

    // Active coefficients
    this.a = this.baseA.clone();
    this.b = this.baseB.clone();
    this.c = this.baseC.clone();
    this.d = this.baseD.clone();

    // Derived transforms: M_inv and M^2
    this.invA = this.d.clone();
    this.invB = this.b.scale(-1);
    this.invC = this.c.scale(-1);
    this.invD = this.a.clone();

    this.a2 = new Complex(1, 0);
    this.b2 = new Complex(0, 0);
    this.c2 = new Complex(0, 0);
    this.d2 = new Complex(1, 0);

    // Evolution state
    this.time = 0;
    this.evolving = (initialMode === 'explore');
    this.driftFreqs = [0.034, 0.055, 0.021, 0.043];

    // Pointer perturbation
    this.pointerTarget = new Complex(0, 0);
    this.pointerCurrent = new Complex(0, 0);

    // Shock / click disturbance
    this.shockMag = 0.0;
    this.shockPhase = 0.0;

    this.updateRootsOfUnity();
    this.computeTransforms();
  }

  setMode(mode) {
    if (mode === 'reference') {
      this.mode = 'reference';
      this.pointerPerturbationEnabled = false;
      this.shockEnabled = false;
      this.evolving = false;
      this.time = 0;

      // Reset to exact authentic Simone Conradi coefficients & symmetry
      this.n = CONRADI_REFERENCE.n;
      this.activeMorphology = 'lace';
      this.baseA = CONRADI_REFERENCE.a.clone();
      this.baseB = CONRADI_REFERENCE.b.clone();
      this.baseC = CONRADI_REFERENCE.c.clone();
      this.baseD = CONRADI_REFERENCE.d.clone();

      this.userOffsetA = new Complex(0, 0);
      this.userOffsetB = new Complex(0, 0);
      this.userOffsetC = new Complex(0, 0);
      this.userOffsetD = new Complex(0, 0);

      this.pointerTarget = new Complex(0, 0);
      this.pointerCurrent = new Complex(0, 0);
      this.shockMag = 0.0;
      this.shockPhase = 0.0;

      this.a = this.baseA.clone();
      this.b = this.baseB.clone();
      this.c = this.baseC.clone();
      this.d = this.baseD.clone();

      this.updateRootsOfUnity();
      this.computeTransforms();
    } else if (mode === 'explore') {
      this.mode = 'explore';
      this.pointerPerturbationEnabled = true;
      this.shockEnabled = true;
    }
  }

  setMorphology(key) {
    if (this.mode === 'reference' && key !== 'lace') {
      this.mode = 'explore';
      this.pointerPerturbationEnabled = true;
      this.shockEnabled = true;
    }
    const morph = MORPHOLOGIES[key];
    if (!morph) return;
    this.activeMorphology = key;
    this.n = morph.n;
    this.baseA = morph.a.clone();
    this.baseB = morph.b.clone();
    this.baseC = morph.c.clone();
    this.baseD = morph.d.clone();
    this.updateRootsOfUnity();
    this.computeTransforms();
  }

  setSymmetry(n) {
    if (this.mode === 'reference') {
      // In Reference mode symmetry is strictly locked to n=16
      return;
    }
    this.n = n;
    this.updateRootsOfUnity();
    this.computeTransforms();
  }

  updateRootsOfUnity() {
    this.omegas = [];
    for (let k = 0; k < this.n; k++) {
      const angle = (2 * Math.PI * k) / this.n;
      this.omegas.push(Complex.fromAngle(angle));
    }
  }

  setPointer(normX, normY) {
    // In Reference mode, ordinary mouse movement must NOT alter the formula!
    if (this.mode === 'reference' || !this.pointerPerturbationEnabled) {
      return;
    }
    this.pointerTarget.r = normX * 0.22;
    this.pointerTarget.i = normY * 0.22;
  }

  injectShock(normX, normY) {
    // In Reference mode, click shock disturbance is strictly prohibited!
    if (this.mode === 'reference' || !this.shockEnabled) {
      return;
    }
    this.shockMag = 1.0;
    this.shockPhase = Math.atan2(normY, normX);
  }

  setCoefficientOffset(param, re, im) {
    // In Reference mode, user coefficient offsets are disabled
    if (this.mode === 'reference') {
      return;
    }
    if (param === 'a') this.userOffsetA = new Complex(re, im);
    if (param === 'b') this.userOffsetB = new Complex(re, im);
    if (param === 'c') this.userOffsetC = new Complex(re, im);
    if (param === 'd') this.userOffsetD = new Complex(re, im);
  }

  update(dt, zoom = 1.65) {
    // REFERENCE MODE: Formula is invariant, pristine, and unperturbed
    if (this.mode === 'reference') {
      this.pointerCurrent.r = 0.0;
      this.pointerCurrent.i = 0.0;
      this.pointerTarget.r = 0.0;
      this.pointerTarget.i = 0.0;
      this.shockMag = 0.0;
      this.a.r = this.baseA.r;
      this.a.i = this.baseA.i;
      this.b.r = this.baseB.r;
      this.b.i = this.baseB.i;
      this.c.r = this.baseC.r;
      this.c.i = this.baseC.i;
      this.d.r = this.baseD.r;
      this.d.i = this.baseD.i;
      this.computeTransforms();
      return;
    }

    if (this.evolving) {
      this.time += dt;
    }

    // Smooth pointer damping
    const lerp = Math.min(1.0, dt * 6.0);
    this.pointerCurrent.r += (this.pointerTarget.r - this.pointerCurrent.r) * lerp;
    this.pointerCurrent.i += (this.pointerTarget.i - this.pointerCurrent.i) * lerp;

    // Shock relaxation
    this.shockMag *= Math.exp(-dt * 1.8);

    // Autonomous multi-frequency drift (subtle topological evolution)
    const zoomDamp = 1.0 / (1.0 + 0.40 * Math.log2(Math.max(1.0, zoom / 1.65)));
    const driftScale = this.evolving ? zoomDamp : 0.0;
    const t = this.time;
    const f = this.driftFreqs;

    const driftAr = 0.015 * Math.sin(t * f[0]) * driftScale;
    const driftAi = 0.015 * Math.sin(t * f[1]) * driftScale;
    const driftBr = 0.010 * Math.sin(t * f[2]) * driftScale;
    const driftBi = 0.010 * Math.sin(t * f[0] * 1.3) * driftScale;
    const driftCr = 0.065 * Math.sin(t * f[3]) * driftScale;
    const driftCi = 0.065 * Math.sin(t * f[2] * 0.9) * driftScale;
    const driftDr = 0.022 * Math.sin(t * f[1] * 1.1) * driftScale;
    const driftDi = 0.022 * Math.sin(t * f[3]) * driftScale;

    // Shock disturbance vector
    const shockR = Math.cos(this.shockPhase) * this.shockMag * 0.16;
    const shockI = Math.sin(this.shockPhase) * this.shockMag * 0.16;

    const ptrR = this.pointerPerturbationEnabled ? this.pointerCurrent.r : 0.0;
    const ptrI = this.pointerPerturbationEnabled ? this.pointerCurrent.i : 0.0;

    // Sum base + drift + pointer perturbation + shock disturbance + user offsets without temporary object allocations
    this.a.r = this.baseA.r + driftAr + this.userOffsetA.r + ptrR * 0.045 + shockR * 0.35;
    this.a.i = this.baseA.i + driftAi + this.userOffsetA.i + ptrI * 0.045 + shockI * 0.35;

    this.b.r = this.baseB.r + driftBr + this.userOffsetB.r + ptrR * 0.035 + shockR * 0.25;
    this.b.i = this.baseB.i + driftBi + this.userOffsetB.i - ptrI * 0.025 + shockI * 0.25;

    this.c.r = this.baseC.r + driftCr + this.userOffsetC.r - ptrR * 0.30 - shockR * 1.4;
    this.c.i = this.baseC.i + driftCi + this.userOffsetC.i + ptrI * 0.30 - shockI * 1.4;

    this.d.r = this.baseD.r + driftDr + this.userOffsetD.r + ptrR * 0.06 + shockR * 0.45;
    this.d.i = this.baseD.i + driftDi + this.userOffsetD.i - ptrI * 0.05 + shockI * 0.45;

    this.computeTransforms();
  }

  computeTransforms() {
    // 1. Primary Mobius M (preserves exact base coefficients without normalized scaling)
    const m = new MobiusTransform(this.a.clone(), this.b.clone(), this.c.clone(), this.d.clone());

    // 2. Inverse Mobius M_inv = [d, -b; -c, a]
    this.invA = this.d.clone();
    this.invB = this.b.scale(-1);
    this.invC = this.c.scale(-1);
    this.invD = this.a.clone();

    // 3. Second iterate M^2 = M o M
    const m2 = m.compose(m);
    this.a2 = m2.a;
    this.b2 = m2.b;
    this.c2 = m2.c;
    this.d2 = m2.d;
  }

  reset() {
    this.time = 0;
    this.pointerTarget = new Complex(0, 0);
    this.pointerCurrent = new Complex(0, 0);
    this.shockMag = 0;
    this.userOffsetA = new Complex(0, 0);
    this.userOffsetB = new Complex(0, 0);
    this.userOffsetC = new Complex(0, 0);
    this.userOffsetD = new Complex(0, 0);
    this.a = this.baseA.clone();
    this.b = this.baseB.clone();
    this.c = this.baseC.clone();
    this.d = this.baseD.clone();
    this.computeTransforms();
  }

  /**
   * Curated Randomization Generator
   * Generates aesthetically useful mathematical organisms sampled from curated
   * coefficient families, harmonic mutations, and morphology classes.
   * Styles: 'subtle', 'organic', 'dense lace', 'symmetric', 'chaotic', 'conradi-like'
   */
  randomize(style = null) {
    // If no style provided or 'random', pick one from available styles
    if (!style || style === 'random') {
      const available = ['conradi-like', 'organic', 'dense lace', 'symmetric', 'chaotic', 'subtle'];
      style = available[Math.floor(Math.random() * available.length)];
    }

    // Randomization switches to explore mode
    this.mode = 'explore';
    this.pointerPerturbationEnabled = true;
    this.shockEnabled = true;

    // Reset user offsets and disturbances
    this.userOffsetA = new Complex(0, 0);
    this.userOffsetB = new Complex(0, 0);
    this.userOffsetC = new Complex(0, 0);
    this.userOffsetD = new Complex(0, 0);
    this.pointerTarget = new Complex(0, 0);
    this.pointerCurrent = new Complex(0, 0);
    this.shockMag = 0.0;
    this.shockPhase = 0.0;

    const rnd = (min, max) => min + Math.random() * (max - min);
    const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

    const rawStyle = (style || 'conradi-like').toLowerCase().trim();
    const normalizedStyle = rawStyle.replace('-', ' ');
    let result = {
      style: rawStyle,
      name: '',
      description: ''
    };

    if (normalizedStyle === 'subtle') {
      result.name = 'Subtle Micro-Variation';
      result.description = 'Harmonic perturbation preserving global attractor topology';
      this.baseA = new Complex(this.baseA.r + rnd(-0.015, 0.015), this.baseA.i + rnd(-0.015, 0.015));
      this.baseB = new Complex(this.baseB.r + rnd(-0.010, 0.010), this.baseB.i + rnd(-0.008, 0.008));
      this.baseC = new Complex(this.baseC.r + rnd(-0.080, 0.080), this.baseC.i + rnd(-0.050, 0.050));
      this.baseD = new Complex(this.baseD.r + rnd(-0.030, 0.030), this.baseD.i + rnd(-0.030, 0.030));
    } else if (normalizedStyle === 'organic') {
      result.name = 'Organic Knotting Organism';
      result.description = 'Flowing radial geometry with interlocking chambers, curls, and pinched intersections';
      const organicFamilies = [
        { n: 8,  a: [-0.755, 0.330], b: [-0.376, 0.026], c: [6.401, 0.803], d: [1.520, 0.840] },
        { n: 6,  a: [-0.720, 0.360], b: [-0.340, 0.035], c: [5.800, 0.720], d: [1.440, 0.790] },
        { n: 10, a: [-0.770, 0.310], b: [-0.410, 0.015], c: [6.800, 0.850], d: [1.590, 0.890] },
        { n: 7,  a: [-0.740, 0.340], b: [-0.360, 0.020], c: [6.200, 0.780], d: [1.510, 0.820] },
        { n: 12, a: [-0.765, 0.320], b: [-0.385, 0.022], c: [6.500, 0.820], d: [1.530, 0.860] }
      ];
      const fam = pick(organicFamilies);
      this.n = fam.n;
      this.baseA = new Complex(fam.a[0] + rnd(-0.020, 0.020), fam.a[1] + rnd(-0.020, 0.020));
      this.baseB = new Complex(fam.b[0] + rnd(-0.015, 0.015), fam.b[1] + rnd(-0.010, 0.010));
      this.baseC = new Complex(fam.c[0] + rnd(-0.150, 0.150), fam.c[1] + rnd(-0.080, 0.080));
      this.baseD = new Complex(fam.d[0] + rnd(-0.040, 0.040), fam.d[1] + rnd(-0.040, 0.040));
    } else if (normalizedStyle === 'dense lace') {
      result.name = 'Dense Gossamer Lace';
      result.description = 'Hyper-intricate filament web with multi-tiered caustic rosettes and gossamer threads';
      this.n = pick([16, 24, 32]);
      this.baseA = new Complex(-0.750 + rnd(-0.020, 0.020), 0.335 + rnd(-0.015, 0.015));
      this.baseB = new Complex(-0.375 + rnd(-0.010, 0.010), 0.025 + rnd(-0.008, 0.008));
      this.baseC = new Complex(6.500 + rnd(-0.180, 0.180), 0.810 + rnd(-0.060, 0.060));
      this.baseD = new Complex(1.530 + rnd(-0.030, 0.030), 0.845 + rnd(-0.030, 0.030));
    } else if (normalizedStyle === 'symmetric') {
      result.name = 'Harmonic Rotational Rosette';
      result.description = 'Pristine harmonic rotational symmetry with razor-sharp radial caustic boundaries';
      this.n = pick([12, 16, 20, 24, 32]);
      const angle = rnd(0, 2 * Math.PI);
      const mag = rnd(0.005, 0.018);
      this.baseA = new Complex(-0.755 + mag * Math.cos(angle), 0.330 + mag * Math.sin(angle));
      this.baseB = new Complex(-0.376 + rnd(-0.008, 0.008), 0.026 + rnd(-0.005, 0.005));
      this.baseC = new Complex(6.401 + rnd(-0.100, 0.100), 0.803 + rnd(-0.040, 0.040));
      this.baseD = new Complex(1.520 + rnd(-0.020, 0.020), 0.840 + rnd(-0.020, 0.020));
    } else if (normalizedStyle === 'chaotic') {
      result.name = 'Filament Storm (High-Energy)';
      result.description = 'Turbulent braided loops with counter-rotating wave crests and deep secondary orbits';
      this.n = pick([16, 24, 28]);
      this.baseA = new Complex(-0.705 + rnd(-0.030, 0.030), 0.420 + rnd(-0.030, 0.030));
      this.baseB = new Complex(-0.395 + rnd(-0.020, 0.020), 0.010 + rnd(-0.008, 0.015));
      this.baseC = new Complex(7.350 + rnd(-0.250, 0.250), 0.650 + rnd(-0.100, 0.100));
      this.baseD = new Complex(1.650 + rnd(-0.060, 0.060), 0.820 + rnd(-0.060, 0.060));
    } else { // default 'conradi-like'
      result.name = 'Conradi Attractor Basin Variant';
      result.description = 'Faithfully curated variation within Simone Conradi 2026 basin';
      this.n = 16;
      this.baseA = new Complex(-0.755 + rnd(-0.025, 0.025), 0.330 + rnd(-0.020, 0.020));
      this.baseB = new Complex(-0.376 + rnd(-0.012, 0.012), 0.026 + rnd(-0.008, 0.008));
      this.baseC = new Complex(6.401 + rnd(-0.160, 0.160), 0.803 + rnd(-0.070, 0.070));
      this.baseD = new Complex(1.520 + rnd(-0.040, 0.040), 0.840 + rnd(-0.035, 0.035));
    }

    this.a = this.baseA.clone();
    this.b = this.baseB.clone();
    this.c = this.baseC.clone();
    this.d = this.baseD.clone();

    this.updateRootsOfUnity();
    this.computeTransforms();

    result.n = this.n;
    result.a = this.a.format(3);
    result.b = this.b.format(3);
    result.c = this.c.format(3);
    result.d = this.d.format(3);

    return result;
  }

  toJSON() {
    return {
      n: this.n,
      symmetry: this.n,
      mode: this.mode,
      evolving: this.evolving,
      time: this.time,
      coefficients: {
        a: { r: this.baseA.r, i: this.baseA.i },
        b: { r: this.baseB.r, i: this.baseB.i },
        c: { r: this.baseC.r, i: this.baseC.i },
        d: { r: this.baseD.r, i: this.baseD.i }
      },
      offsets: {
        a: { r: this.userOffsetA.r, i: this.userOffsetA.i },
        b: { r: this.userOffsetB.r, i: this.userOffsetB.i },
        c: { r: this.userOffsetC.r, i: this.userOffsetC.i },
        d: { r: this.userOffsetD.r, i: this.userOffsetD.i }
      },
      userOffsets: {
        a: { r: this.userOffsetA.r, i: this.userOffsetA.i },
        b: { r: this.userOffsetB.r, i: this.userOffsetB.i },
        c: { r: this.userOffsetC.r, i: this.userOffsetC.i },
        d: { r: this.userOffsetD.r, i: this.userOffsetD.i }
      },
      drift: {
        evolving: this.evolving,
        time: this.time
      }
    };
  }

  fromJSON(data) {
    if (!data) return;
    const sym = data.symmetry !== undefined ? data.symmetry : data.n;
    if (sym !== undefined) this.n = sym;
    if (data.mode) this.mode = data.mode;

    const evolving = data.evolving !== undefined ? data.evolving : (data.drift ? data.drift.evolving : undefined);
    if (evolving !== undefined) this.evolving = !!evolving;

    const time = data.time !== undefined ? data.time : (data.drift ? data.drift.time : undefined);
    if (time !== undefined) this.time = time;

    if (data.coefficients) {
      if (data.coefficients.a) this.baseA = new Complex(data.coefficients.a.r, data.coefficients.a.i);
      if (data.coefficients.b) this.baseB = new Complex(data.coefficients.b.r, data.coefficients.b.i);
      if (data.coefficients.c) this.baseC = new Complex(data.coefficients.c.r, data.coefficients.c.i);
      if (data.coefficients.d) this.baseD = new Complex(data.coefficients.d.r, data.coefficients.d.i);
    }
    const offsets = data.userOffsets || data.offsets;
    if (offsets) {
      if (offsets.a) this.userOffsetA = new Complex(offsets.a.r, offsets.a.i);
      if (offsets.b) this.userOffsetB = new Complex(offsets.b.r, offsets.b.i);
      if (offsets.c) this.userOffsetC = new Complex(offsets.c.r, offsets.c.i);
      if (offsets.d) this.userOffsetD = new Complex(offsets.d.r, offsets.d.i);
    }
    this.a = this.baseA.clone();
    this.b = this.baseB.clone();
    this.c = this.baseC.clone();
    this.d = this.baseD.clone();
    this.pointerTarget = new Complex(0, 0);
    this.pointerCurrent = new Complex(0, 0);
    this.shockMag = 0.0;
    this.updateRootsOfUnity();
    this.computeTransforms();
  }
}
