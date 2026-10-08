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
 * pointer perturbations, click shocks, and multiscale iterated transforms.
 */
export class MathSystem {
  constructor() {
    this.n = 16;
    this.activeMorphology = 'lace';

    // Mathematical base coefficients generating authentic Mobius IFS attractor (Simone Conradi, 2026):
    this.baseA = new Complex(-0.755, 0.330);
    this.baseB = new Complex(-0.376, 0.026);
    this.baseC = new Complex(6.401, 0.803);
    this.baseD = new Complex(1.520, 0.840);

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
    this.evolving = true;
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

  setMorphology(key) {
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
    this.pointerTarget.r = normX * 0.22;
    this.pointerTarget.i = normY * 0.22;
  }

  injectShock(normX, normY) {
    this.shockMag = 1.0;
    this.shockPhase = Math.atan2(normY, normX);
  }

  setCoefficientOffset(param, re, im) {
    if (param === 'a') this.userOffsetA = new Complex(re, im);
    if (param === 'b') this.userOffsetB = new Complex(re, im);
    if (param === 'c') this.userOffsetC = new Complex(re, im);
    if (param === 'd') this.userOffsetD = new Complex(re, im);
  }

  update(dt, zoom = 1.65) {
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
    // At deep zoom, damp drift so microscopic trajectory caustics remain crisp rather than motion-blurred
    // When paused (evolving == false), drift scale is strictly 0.0 so autonomous motion blur is eliminated
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

    const ptrR = this.pointerCurrent.r;
    const ptrI = this.pointerCurrent.i;

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
    // 1. Primary Mobius M
    const m = new MobiusTransform(this.a.clone(), this.b.clone(), this.c.clone(), this.d.clone());
    m.normalize();
    this.a = m.a;
    this.b = m.b;
    this.c = m.c;
    this.d = m.d;

    // 2. Inverse Mobius M_inv = [d, -b; -c, a]
    this.invA = this.d.clone();
    this.invB = this.b.scale(-1);
    this.invC = this.c.scale(-1);
    this.invD = this.a.clone();

    // 3. Second iterate M^2 = M o M
    const m2 = m.compose(m);
    m2.normalize();
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
}
