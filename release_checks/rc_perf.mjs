// Performance sanity per quality tier + soak/repeatability of the long real-use cycle, on LIVE production, real browser.
// Usage: node rc_perf.mjs <url> <root> <browser> <tiers|soak> [cycles]
import fs from 'fs';
import path from 'path';
import { launch, reporter, sleep, invariant, appState, files, inspectPng, randomizeStyle, openSection, closeAnyDialog } from './rc_lib.mjs';
const [url, root, which = 'chrome', mode = 'tiers', cyclesArg = '40'] = process.argv.slice(2);
const { check, done } = reporter(`rc_perf ${mode} ${which}`);
const glCount = () => {
  // live GL object accounting (created - deleted) installed before any app code runs
  const proto = WebGL2RenderingContext.prototype; const live = window.__gl = { texture: 0, buffer: 0, framebuffer: 0, program: 0, renderbuffer: 0, vertexArray: 0, transformFeedback: 0, shader: 0, contexts: 0 };
  const map = { Texture: 'texture', Buffer: 'buffer', Framebuffer: 'framebuffer', Program: 'program', Renderbuffer: 'renderbuffer', VertexArray: 'vertexArray', TransformFeedback: 'transformFeedback', Shader: 'shader' };
  for (const [k, v] of Object.entries(map)) {
    const c = proto['create' + k], d = proto['delete' + k]; if (!c || !d) continue;
    proto['create' + k] = function (...a) { const o = c.apply(this, a); if (o) live[v]++; return o; };
    proto['delete' + k] = function (o) { if (o) live[v]--; return d.call(this, o); };
  }
  const gc = HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext = function (t, ...a) { const g = gc.call(this, t, ...a); if (t === 'webgl2' && g && !g.__c) { g.__c = 1; live.contexts++; } return g; };
};
const S = await launch({ url, root, which, init: glCount });
const { p, dl, log } = S;
console.log(`== ${which} ${S.version} ${url} mode=${mode}`);
const cdp = await p.createCDPSession(); await cdp.send('Performance.enable');
const metrics = async () => { await cdp.send('HeapProfiler.collectGarbage'); await cdp.send('HeapProfiler.collectGarbage'); await sleep(300); const m = Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(x => [x.name, x.value])); const dom = await cdp.send('Memory.getDOMCounters'); const gl = await p.evaluate(() => ({ ...window.__gl })); return { heapMB: +(m.JSHeapUsedSize / 1048576).toFixed(2), nodes: dom.nodes, listeners: dom.jsEventListeners, docs: dom.documents, gl }; };

if (mode === 'tiers') {
  await openSection(p, 'quality');
  const fpsProbe = (ms) => p.evaluate((ms) => new Promise(res => { const t = []; let last = performance.now(); const end = last + ms; const f = now => { t.push(now - last); last = now; if (now < end) requestAnimationFrame(f); else { t.shift(); t.sort((a, b) => a - b); const avg = t.reduce((a, b) => a + b, 0) / t.length; res({ frames: t.length, fps: +(1000 / avg).toFixed(1), p50: +t[Math.floor(t.length * .5)].toFixed(1), p95: +t[Math.floor(t.length * .95)].toFixed(1), max: +t.at(-1).toFixed(1) }); } }; requestAnimationFrame(f); }), ms);
  const results = {};
  for (const scenario of ['reference', 'explore-chaotic']) {
    if (scenario === 'reference') { await p.click('#btn-mode-reference'); } else { await p.click('#btn-randomize-toggle'); await sleep(100); await p.click('.rnd-style-btn[data-style="chaotic"]'); }
    await sleep(600);
    for (const tier of ['auto', 'low', 'standard', 'high', 'ultra', 'extreme', 'bruteforce']) {
      await openSection(p, 'quality');
      await p.click(`.quality-btn[data-tier="${tier}"]`); await sleep(tier === 'auto' ? 9000 : 3500);
      const r = await fpsProbe(4000); const cur = await p.evaluate(() => ({ line: document.getElementById('quality-current-tier')?.innerText, tierEff: window.__renderer.adaptive.currentTier, mode: window.__renderer.adaptive.mode }));
      results[`${scenario}/${tier}`] = { ...r, ...cur };
      check(`${scenario} / ${tier}: renders (frames>0) at a usable rate`, r.frames > 30 && r.fps >= 20, JSON.stringify({ ...r, ...cur }));
      console.log(`INFO ${scenario} ${tier}: ${r.fps} fps (p50 ${r.p50} ms, p95 ${r.p95} ms, max ${r.max} ms) tier=${cur.tierEff} | ${String(cur.line).replace(/\n/g, ' ')}`);
    }
    await p.click('.quality-btn[data-tier="auto"]'); await sleep(500);
  }
  const bad = await invariant(p); await p.click('#btn-mode-reference'); await sleep(400);
  check('Reference invariant intact after tier sweep', (await invariant(p)).length === 0);
  check('no uncaught page errors', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
  console.log('console:', JSON.stringify([...new Set(log.console)].slice(0, 8)));
  fs.writeFileSync(path.join(root, 'tiers.json'), JSON.stringify(results, null, 1));
} else {
  const cycles = +cyclesArg; const STY = ['conradi-like', 'subtle', 'organic', 'dense lace', 'symmetric', 'chaotic']; const NS = [3, 5, 8, 12, 24, 32, 16]; const PALS = ['solar', 'aurora', 'amethyst', 'monochrome', 'cobalt'];
  const samples = []; const t0 = Date.now(); let exportsDone = 0, presetsSaved = 0, errors = 0, step = '';
  const wait = async (fn, ms = 60000) => { const t = Date.now(); while (Date.now() - t < ms) { if (await fn()) return true; await sleep(150); } return false; };
  samples.push({ cycle: 0, ...(await metrics()) });
  for (let c = 1; c <= cycles; c++) {
    try {
      step = 'mode explore';
      await p.click('#btn-mode-explore'); await sleep(120);
      step = 'randomize'; await randomizeStyle(p, STY[c % STY.length]);
      step = 'order-n'; await openSection(p, 'math'); await p.click(`.sym-btn[data-n="${NS[c % NS.length]}"]`); await sleep(120);
      step = 'palette'; await openSection(p, 'view'); await p.click('#btn-palette-toggle'); await sleep(80); await p.click(`.palette-select-btn[data-pal="${PALS[c % PALS.length]}"]`); await sleep(100);
      step = 'canvas'; await p.mouse.move(400 + (c % 5) * 40, 300, { steps: 4 }); await p.mouse.click(600, 400); await sleep(80);
      await p.keyboard.press('Escape'); // close panel
      // preset: save (download) every cycle, load it back
      step = 'save preset'; await p.click('#btn-preset-trigger'); await sleep(250); await p.$eval('#preset-name-input', e => e.value = ''); await p.type('#preset-name-input', 'Soak ' + c); await p.click('#btn-preset-save'); await sleep(350); presetsSaved++;
      step = 'load preset'; const pt = await p.evaluate(() => { const b = document.querySelector('#user-presets-list .load-user-preset'); if (!b) return null; const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }); if (pt) { await p.mouse.click(pt[0], pt[1]); await sleep(250); await p.mouse.move(3, 3); } else await closeAnyDialog(p);
      await closeAnyDialog(p);
      step = 'help keys'; for (const k of ['?', 'Escape']) { await p.keyboard.press(k); await sleep(150); }
      // export: alternate 1080p/30 standard and (every 5th) Reference Master 120
      step = 'export'; const before = new Set(files(dl));
      await p.click('#btn-export-trigger'); await sleep(250);
      if (c % 5 === 0) { await p.click('#tab-export-refmaster'); await p.click('.refmaster-pass-btn[data-passes="120"]'); } else { await p.click('#tab-export-standard'); await p.click('.export-res-btn[data-w="1920"]'); await p.click('.export-pass-btn[data-passes="30"]'); }
      await p.click('#btn-export-start');
      const ok = await wait(() => p.evaluate(() => !document.getElementById('export-result').hidden || !document.getElementById('export-notice').hidden));
      await sleep(350); const added = files(dl).filter(f => !before.has(f)); const insp = added[0] ? inspectPng(dl, added[0]) : null;
      if (!(ok && added.length === 1 && insp?.ok)) { errors++; console.log('CYCLE', c, 'export problem', JSON.stringify({ ok, added, insp })); } else exportsDone++;
      await p.click('#btn-export-cancel'); await sleep(250);
      // clean Downloads to keep disk bounded
      for (const f of files(dl)) { try { fs.unlinkSync(path.join(dl, f)); } catch (e) { } }
      await p.click('#btn-mode-reference'); await sleep(250);
      const bad = await invariant(p); if (bad.length) { errors++; console.log('CYCLE', c, 'invariant broke', bad.join()); }
    } catch (e) { errors++; console.log('CYCLE', c, 'EXCEPTION at step', step, ':', e.message.slice(0, 160)); await closeAnyDialog(p); await p.keyboard.press('Escape'); }
    if (c % 8 === 0 || c === cycles) { const m = await metrics(); samples.push({ cycle: c, ...m }); console.log(`INFO cycle ${c} (${((Date.now() - t0) / 60000).toFixed(1)} min): heap ${m.heapMB} MB, nodes ${m.nodes}, listeners ${m.listeners}, GL ${JSON.stringify(m.gl)}`); }
  }
  const first = samples[1] ?? samples[0], last = samples.at(-1);
  check(`soak: ${cycles} full cycles completed with ${errors} problems`, errors === 0, `exports ok ${exportsDone}, presets saved ${presetsSaved}`);
  check('soak: JS heap (after GC) bounded: last sample within +25% of the first warmed-up sample', last.heapMB <= first.heapMB * 1.25 + 2, `${first.heapMB} -> ${last.heapMB} MB`);
  check('soak: DOM nodes bounded (<= +10% vs first warmed sample)', last.nodes <= first.nodes * 1.1 + 50, `${first.nodes} -> ${last.nodes}`);
  check('soak: JS event listeners bounded (<= +10% vs first warmed sample)', last.listeners <= first.listeners * 1.1 + 20, `${first.listeners} -> ${last.listeners}`);
  const glDelta = Object.fromEntries(Object.keys(last.gl).map(k => [k, last.gl[k] - first.gl[k]]));
  check('soak: live GL objects do not grow cycle over cycle (textures/buffers/framebuffers/programs)', ['texture', 'buffer', 'framebuffer', 'program', 'renderbuffer', 'vertexArray', 'transformFeedback'].every(k => glDelta[k] <= 2), JSON.stringify(glDelta));
  check('soak: exactly one WebGL context ever created', last.gl.contexts === 1, String(last.gl.contexts));
  check('no uncaught page errors', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
  console.log('samples:', JSON.stringify(samples.map(s => ({ c: s.cycle, heap: s.heapMB, nodes: s.nodes, lis: s.listeners }))));
  console.log('console:', JSON.stringify([...new Set(log.console)].slice(0, 8)));
}
done(); await S.browser.close();
