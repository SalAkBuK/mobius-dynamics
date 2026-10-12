// Shared, atomic validation for imported presets and direct math deserialization.
// Optional fields preserve legacy presets. Unknown fields are ignored by the loaders.
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const fail = field => { throw new Error(`Invalid preset field: ${field}.`); };
const object = (value, field) => { if (!value || typeof value !== 'object' || Array.isArray(value)) fail(field); };
const number = (value, field, min, max) => { if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) fail(field); };
const boolean = (value, field) => { if (typeof value !== 'boolean') fail(field); };
const oneOf = (value, field, values) => { if (!values.includes(value)) fail(field); };
export const MAX_PRESET_BYTES = 1024 * 1024;

export function validateMathPreset(data, currentMode = 'explore') {
  object(data, 'preset');
  if (own(data, 'mode')) oneOf(data.mode, 'mode', ['reference', 'explore']);
  const mode = data.mode ?? currentMode;
  if (mode === 'reference') return; // Canonical reset ignores all imported mathematics.
  for (const key of ['n', 'symmetry']) if (own(data, key)) {
    number(data[key], key, 1, 64);
    if (!Number.isInteger(data[key])) fail(key);
  }
  if (own(data, 'n') && own(data, 'symmetry') && data.n !== data.symmetry) fail('n/symmetry');
  for (const key of ['coefficients', 'offsets', 'userOffsets']) if (own(data, key)) {
    object(data[key], key);
    for (const component of ['a', 'b', 'c', 'd']) if (own(data[key], component)) {
      const value = data[key][component]; object(value, `${key}.${component}`);
      for (const part of ['r', 'i']) number(value[part], `${key}.${component}.${part}`, -1000, 1000);
    }
  }
  if (own(data, 'evolving')) boolean(data.evolving, 'evolving');
  if (own(data, 'time')) number(data.time, 'time', 0, 1e9);
  if (own(data, 'drift')) {
    object(data.drift, 'drift');
    if (own(data.drift, 'evolving')) boolean(data.drift.evolving, 'drift.evolving');
    if (own(data.drift, 'time')) number(data.drift.time, 'drift.time', 0, 1e9);
  }
}

export function validatePreset(data) {
  validateMathPreset(data);
  for (const [key, limit] of [['name', 512], ['description', 4096], ['version', 64]]) if (own(data, key)) {
    if (typeof data[key] !== 'string' || data[key].length > limit) fail(key);
  }
  if (own(data, 'timestamp')) number(data.timestamp, 'timestamp', 0, Number.MAX_SAFE_INTEGER);
  // Reference framing/palette are ignored and established canonically by setMode.
  if (data.mode !== 'reference') {
    if (own(data, 'palette')) oneOf(data.palette, 'palette', ['cobalt', 'solar', 'aurora', 'amethyst', 'monochrome']);
    if (own(data, 'camera')) {
      object(data.camera, 'camera');
      if (own(data.camera, 'zoom')) number(data.camera.zoom, 'camera.zoom', .3, 500);
      if (own(data.camera, 'center')) {
        const center = data.camera.center;
        if (!Array.isArray(center) || center.length !== 2) fail('camera.center');
        center.forEach(v => number(v, 'camera.center', -1e6, 1e6));
      }
    }
  }
  if (own(data, 'rendering')) {
    object(data.rendering, 'rendering');
    if (own(data.rendering, 'bloom')) boolean(data.rendering.bloom, 'rendering.bloom');
    if (own(data.rendering, 'viewMode')) oneOf(data.rendering.viewMode, 'rendering.viewMode', [0, 1, 2]);
    if (own(data.rendering, 'tier')) {
      const tier = data.rendering.tier;
      if (typeof tier !== 'string') fail('rendering.tier');
      oneOf(tier.toLowerCase(), 'rendering.tier', ['auto', 'potato', 'low', 'standard', 'high', 'ultra', 'extreme', 'brute', 'bruteforce', 'brute_force']);
    }
  }
}
