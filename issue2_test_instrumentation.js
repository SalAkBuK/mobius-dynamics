export const instrumentation = `<script>
window.__audit = {pending: new Map(), timers: new Set(), handlers: {}, lostGL: [], downloads: 0, glCommands: 0};
const audit = window.__audit;
const raf = window.requestAnimationFrame.bind(window), cancel = window.cancelAnimationFrame.bind(window);
window.requestAnimationFrame = fn => {
  const id = raf(t => { audit.pending.delete(id); fn(t); });
  audit.pending.set(id, fn); return id;
};
window.cancelAnimationFrame = id => { audit.pending.delete(id); cancel(id); };
const timeout = window.setTimeout.bind(window), clear = window.clearTimeout.bind(window);
window.setTimeout = (fn,ms,...args) => {
  const id = timeout(() => { audit.timers.delete(id); fn(...args); },ms);
  audit.timers.add(id); return id;
};
window.clearTimeout = id => { audit.timers.delete(id); clear(id); };
const add = EventTarget.prototype.addEventListener;
EventTarget.prototype.addEventListener = function(type, ...args) {
  if (['webglcontextlost', 'webglcontextrestored', 'resize'].includes(type))
    audit.handlers[type] = (audit.handlers[type] || 0) + 1;
  return add.call(this, type, ...args);
};
const getContext = HTMLCanvasElement.prototype.getContext;
HTMLCanvasElement.prototype.getContext = function(...args) {
  const gl = getContext.apply(this,args);
  if (args[0] === 'webgl2' && gl && !gl.__instrumented) {
    gl.__instrumented = true;
    const isLost = gl.isContextLost.bind(gl);
    const getError = gl.getError.bind(gl);
    for (const name in gl) {
      const original = gl[name];
      if (typeof original !== 'function' || ['isContextLost','getError'].includes(name)) continue;
      gl[name] = function(...values) {
        audit.glCommands++;
        if (isLost()) audit.lostGL.push(name);
        const value = original.apply(gl,values);
        if (audit.traceError && !isLost()) {
          const error = getError();
          if (error) audit.errors.push([audit.phase,name,error]);
        }
        return value;
      };
    }
  }
  return gl;
};
HTMLAnchorElement.prototype.click = function() { audit.downloads++; };
<\/script>`;
