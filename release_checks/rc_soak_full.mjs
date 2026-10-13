// Stage 10: the full repeated real-use sequence from the release spec, N cycles in ONE browser session on LIVE production.
// Reference -> Explore -> hover/interact -> Randomize -> Export -> Export again -> Save preset -> Copy JSON -> Import -> load preset -> Reference
//  -> restore Explore -> 4K export -> cancel another export -> successful retry -> Hide -> Show -> resize -> background -> foreground -> Reference -> Explore
import fs from 'fs';
import path from 'path';
import { launch, reporter, sleep, invariant, appState, files, inspectPng, openSection, closeAnyDialog, randomizeStyle } from './rc_lib.mjs';
const [url, root, which = 'chrome', cyclesArg = '12'] = process.argv.slice(2); const N = +cyclesArg;
const { check, done } = reporter(`rc_soak_full ${which}`);
const S = await launch({
  url, root, which, init: () => {
    const live = window.__gl = { texture: 0, buffer: 0, framebuffer: 0, program: 0, vertexArray: 0, contexts: 0 }; const proto = WebGL2RenderingContext.prototype;
    for (const [k, v] of Object.entries({ Texture: 'texture', Buffer: 'buffer', Framebuffer: 'framebuffer', Program: 'program', VertexArray: 'vertexArray' })) { const c = proto['create' + k], d = proto['delete' + k]; proto['create' + k] = function (...a) { const o = c.apply(this, a); if (o) live[v]++; return o; }; proto['delete' + k] = function (o) { if (o) live[v]--; return d.call(this, o); }; }
  }
});
const { p, dl, log, browser } = S; const cdp = await p.createCDPSession(); await cdp.send('Performance.enable');
console.log(`== ${which} ${S.version} ${url} cycles=${N}`);
const metrics = async () => { await cdp.send('HeapProfiler.collectGarbage'); await cdp.send('HeapProfiler.collectGarbage'); await sleep(300); const m = Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(x => [x.name, x.value])); const d = await cdp.send('Memory.getDOMCounters'); return { heapMB: +(m.JSHeapUsedSize / 1048576).toFixed(2), nodes: d.nodes, listeners: d.jsEventListeners, gl: await p.evaluate(() => ({ ...window.__gl })) }; };
const ui = () => p.evaluate(() => ({ running: window.__app.isExporting, result: !document.getElementById('export-result').hidden, notice: !document.getElementById('export-notice').hidden ? document.getElementById('export-notice').innerText.replace(/\n/g, ' ') : '', pctTxt: document.getElementById('export-status-pct').innerText, label: document.getElementById('export-status-label').innerText }));
const waitEnd = async (ms = 120000) => { const t = Date.now(); while (Date.now() - t < ms) { const s = await ui(); if (s.result || s.notice) return s; await sleep(120); } return await ui(); };
const tmp = path.join(root, 'tmp'); fs.mkdirSync(tmp, { recursive: true });
const problems = []; const flag = (c, cond, msg) => { if (!cond) { problems.push(`cycle ${c}: ${msg}`); console.log('PROBLEM', `cycle ${c}: ${msg}`); } };
const clearDl = () => { for (const f of files(dl)) { try { fs.unlinkSync(path.join(dl, f)); } catch (e) { } } };
const exportStd = async (res, passes) => { const before = new Set(files(dl)); await p.click('#btn-export-trigger'); await sleep(250); await p.click('#tab-export-standard'); await p.click(`.export-res-btn[data-w="${res}"]`); await p.click(`.export-pass-btn[data-passes="${passes}"]`); await p.click('#btn-export-start'); const s = await waitEnd(); await sleep(900); const added = files(dl).filter(f => !before.has(f)); await p.click('#btn-export-cancel'); await sleep(250); return { s, added }; };
// instrumentation for handler duplication: count calls per single key press / single click
await p.evaluate(() => { const a = window.__app; window.__cnt = { randomize: 0, toggleUI: 0, openExport: 0 }; for (const k of ['randomize', 'toggleUI', 'openExportModal']) { const o = a[k].bind(a); const key = k === 'openExportModal' ? 'openExport' : k; a[k] = (...x) => { window.__cnt[key]++; return o(...x); }; } });
const latency = [];
const samples = []; samples.push({ c: 0, ...(await metrics()) });
const t0 = Date.now(); let dlExpected = 0, dlSeen = 0;
for (let c = 1; c <= N; c++) {
  try {
    // Reference -> Explore -> hover/interact -> Randomize
    await p.click('#btn-mode-reference'); await sleep(150);
    const lat = await p.evaluate(() => { const t = performance.now(); document.getElementById('btn-mode-explore').click(); const a = performance.now() - t; document.getElementById('btn-mode-reference').click(); const b = performance.now() - t - a; return [a, b]; }); latency.push(lat[0] + lat[1]);
    await p.click('#btn-mode-explore'); await sleep(150); await p.mouse.move(400, 300); await p.mouse.move(900, 500, { steps: 6 }); await p.mouse.click(700, 450); await sleep(100);
    const c0 = await p.evaluate(() => window.__cnt.randomize); await p.keyboard.press('3'); await sleep(200); const c1 = await p.evaluate(() => window.__cnt.randomize); flag(c, c1 - c0 === 1, `one '3' key press ran randomize ${c1 - c0} times (keyboard handler duplication)`);
    await randomizeStyle(p, ['conradi-like', 'subtle', 'organic', 'dense lace', 'symmetric', 'chaotic'][c % 6]);
    // Export, Export again
    const e1 = await exportStd('1920', '30'); dlExpected++; dlSeen += e1.added.length; flag(c, e1.s.result && e1.added.length === 1 && inspectPng(dl, e1.added[0]).ok, `export #1 ${JSON.stringify(e1.added)} ${e1.s.notice}`);
    const e2 = await exportStd('1920', '30'); dlExpected++; dlSeen += e2.added.length; flag(c, e2.s.result && e2.added.length === 1 && inspectPng(dl, e2.added[0]).ok, `export #2 ${JSON.stringify(e2.added)}`);
    // Save preset, Copy JSON, Import, load preset
    let before = new Set(files(dl)); await p.click('#btn-preset-trigger'); await sleep(250); await p.$eval('#preset-name-input', e => e.value = ''); await p.type('#preset-name-input', 'Cycle ' + c); await p.click('#btn-preset-save'); await sleep(700); dlExpected++; const sv = files(dl).filter(f => !before.has(f)); dlSeen += sv.length; flag(c, sv.length === 1, `Save produced ${sv.length} files for one click`);
    await p.$eval('#preset-name-input', e => e.value = ''); await p.type('#preset-name-input', 'Copied ' + c); await p.click('#btn-preset-copy'); await sleep(500);
    const clip = await p.evaluate(() => navigator.clipboard.readText()); let cj = null; try { cj = JSON.parse(clip); } catch (e) { } flag(c, cj?.name === 'Copied ' + c, `clipboard name ${cj?.name}`);
    const f = path.join(tmp, `c${c}.json`); fs.writeFileSync(f, clip); const [ch] = await Promise.all([p.waitForFileChooser(), p.click('#btn-preset-import')]); await ch.accept([f]); await sleep(700);
    const t1 = await p.evaluate(() => document.getElementById('toast-banner').innerText); flag(c, new RegExp('Loaded preset: Copied ' + c).test(t1), `import toast: ${t1}`);
    const stillOpen = await p.evaluate(() => window.__app.isModalOpen()); flag(c, !stillOpen, 'preset dialog stuck open after import');
    await p.click('#btn-preset-trigger'); await sleep(250); const pt = await p.evaluate(() => { const b = document.querySelector('#user-presets-list .load-user-preset'); if (!b) return null; const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }); if (pt) { await p.mouse.click(pt[0], pt[1]); await sleep(300); await p.mouse.move(3, 3); } else await closeAnyDialog(p);
    flag(c, !(await p.evaluate(() => window.__app.isModalOpen())), 'dialog stuck after load');
    // Reference -> restore Explore
    const nExp = (await appState(p)).n; await p.click('#btn-mode-reference'); await sleep(250); flag(c, (await invariant(p)).length === 0, 'Reference not canonical after preset load -> Reference');
    await p.click('#btn-mode-explore'); await sleep(250); flag(c, (await appState(p)).n === nExp, `Explore session not restored (n ${nExp} -> ${(await appState(p)).n})`);
    // 4K export
    const e3 = await exportStd('3840', '120'); dlExpected++; dlSeen += e3.added.length; flag(c, e3.s.result && e3.added.length === 1 && inspectPng(dl, e3.added[0]).w === 3840, `4K ${JSON.stringify(e3.added)}`);
    // cancel another export, then retry successfully
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 8 }); before = new Set(files(dl)); await p.click('#btn-export-trigger'); await sleep(250); await p.click('#tab-export-refmaster'); await p.click('.refmaster-pass-btn[data-passes="240"]'); await p.click('#btn-export-start'); await sleep(900); await p.click('#btn-export-cancel'); const ce = await waitEnd(60000); await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 }); await sleep(1500);
    flag(c, /canceled/i.test(ce.notice) && files(dl).filter(f => !before.has(f)).length === 0, `cancel: ${ce.notice} files=${files(dl).filter(f => !before.has(f))}`);
    const st = await ui(); flag(c, st.pctTxt === '' && st.label === '', 'stale progress after cancel');
    await p.click('#btn-export-cancel'); await sleep(250);
    const e4 = await exportStd('1920', '30'); dlExpected++; dlSeen += e4.added.length; flag(c, e4.s.result && e4.added.length === 1, `retry ${JSON.stringify(e4.added)}`);
    // Hide -> Show (single press toggles exactly once)
    const h0 = await p.evaluate(() => window.__cnt.toggleUI); await p.keyboard.press('h'); await sleep(350); const hid = await p.evaluate(() => window.__app.uiHidden); await p.keyboard.press('h'); await sleep(350); const h1 = await p.evaluate(() => window.__cnt.toggleUI); flag(c, hid === true && h1 - h0 === 2 && !(await p.evaluate(() => window.__app.uiHidden)), `Hide/Show toggles ${h1 - h0}, hidden=${hid}`);
    // resize
    await p.setViewport({ width: 1000, height: 700 }); await sleep(300); await p.setViewport({ width: 1366, height: 768 }); await sleep(300);
    // background -> foreground
    const other = await browser.newPage(); await other.goto('about:blank'); await other.bringToFront(); await sleep(1500); await p.bringToFront(); await sleep(400); await other.close();
    // Controls still works; toasts not duplicated
    await p.click('#btn-controls'); await sleep(350); flag(c, await p.evaluate(() => window.__app.panelOpen), 'Controls did not open'); await p.keyboard.press('Escape'); await sleep(250);
    flag(c, (await p.evaluate(() => document.querySelectorAll('#toast-banner').length)) === 1, 'toast element duplicated');
    const ox = await p.evaluate(() => window.__cnt.openExport); await p.keyboard.press('e'); await sleep(300); const ox1 = await p.evaluate(() => window.__cnt.openExport); await closeAnyDialog(p); flag(c, ox1 - ox === 1, `one 'e' press opened export ${ox1 - ox}x`);
    // Reference -> Explore (end of cycle) and back
    await p.click('#btn-mode-reference'); await sleep(250); flag(c, (await invariant(p)).length === 0, 'Reference not canonical at cycle end'); await p.click('#btn-mode-explore'); await sleep(200);
    flag(c, !(await p.evaluate(() => window.__app.isModalOpen())) && !(await p.evaluate(() => window.__app.isExporting)), 'stuck modal / export flag at cycle end');
    clearDl();
  } catch (e) { problems.push(`cycle ${c}: EXCEPTION ${e.message.slice(0, 150)}`); console.log('PROBLEM', `cycle ${c}: EXCEPTION ${e.message.slice(0, 150)}`); await closeAnyDialog(p); await p.setViewport({ width: 1366, height: 768 }).catch(() => { }); }
  if (c % 4 === 0 || c === N) { const m = await metrics(); samples.push({ c, ...m }); console.log(`INFO cycle ${c} (${((Date.now() - t0) / 60000).toFixed(1)} min): heap ${m.heapMB} MB, nodes ${m.nodes}, listeners ${m.listeners}, GL ${JSON.stringify(m.gl)}`); }
}
await p.click('#btn-mode-reference'); await sleep(300);
const first = samples[1] ?? samples[0], last = samples.at(-1); const med = a => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];
const lat0 = med(latency.slice(0, 3)), lat1 = med(latency.slice(-3));
check(`${N} full-spec cycles completed with zero problems`, problems.length === 0, problems.slice(0, 6).join(' || '));
check('no duplicate downloads: files delivered == files expected (one per click)', dlSeen === dlExpected, `${dlSeen}/${dlExpected}`);
check('JS heap bounded after warm-up (<= +25%)', last.heapMB <= first.heapMB * 1.25 + 2, `${first.heapMB} -> ${last.heapMB} MB`);
check('DOM nodes and event listeners bounded (<= +10% vs first warmed sample)', last.nodes <= first.nodes * 1.1 + 60 && last.listeners <= first.listeners * 1.1 + 25, `nodes ${first.nodes}->${last.nodes}, listeners ${first.listeners}->${last.listeners}`);
check('live GL objects constant across cycles', ['texture', 'buffer', 'framebuffer', 'program', 'vertexArray'].every(k => last.gl[k] - first.gl[k] <= 2) && last.gl.contexts <= 1, JSON.stringify([first.gl, last.gl]));
check('UI not progressively slower (mode-toggle handler time, last 3 cycles vs first 3)', lat1 <= Math.max(lat0 * 2.5, 15), `${lat0.toFixed(2)} ms -> ${lat1.toFixed(2)} ms`);
check('Reference canonical at the very end', (await invariant(p)).length === 0);
check('no uncaught page errors', log.pageErrors.length === 0, JSON.stringify(log.pageErrors));
const cons = log.console.filter(m => !/Export error|Reference Master Export/.test(m)); check('no unexpected console errors/warnings', cons.length === 0, JSON.stringify(cons.slice(0, 5)));
console.log('samples:', JSON.stringify(samples.map(s => ({ c: s.c, heap: s.heapMB, nodes: s.nodes, lis: s.listeners })))); console.log('latency ms per cycle:', latency.map(x => x.toFixed(1)).join(' '));
done(); await S.browser.close();
