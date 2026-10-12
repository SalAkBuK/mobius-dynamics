import { instrumentation } from './issue2_test_instrumentation.js';
import { CONRADI_REFERENCE } from './math.js';
export const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
export async function until(fn,label,timeout=30000){const end=performance.now()+timeout;while(!fn()){if(performance.now()>end)throw Error(label);await sleep(20);}}
export async function boot(injection=''){
  const frame=document.createElement('iframe');frame.width=160;frame.height=120;
  frame.srcdoc=(await(await fetch('./index.html')).text()).replace('<head>','<head>'+instrumentation+injection);
  document.body.append(frame);await new Promise(resolve=>frame.onload=resolve);
  const w=frame.contentWindow,app=w.__app;
  if(app){app.isTabHidden=true;app.customDpr=1;app.onResize();app.renderer.profiler.enabled=false;}
  return {frame,w,app,audit:w.__audit};
}
export function seed(r){const gl=r.gl;
  for(let k=0;k<2;k++){const a=new Float32Array(r.maxParticleCapacity*4);
    for(let i=0;i<r.maxParticleCapacity;i++){const angle=(i%4096)*Math.PI/2048;
      a[i*4]=(.25+(i%97)/500)*Math.cos(angle);a[i*4+1]=(.25+(i%97)/500)*Math.sin(angle);
      a[i*4+2]=60+(i%31);a[i*4+3]=(Math.imul(i+1,1664525)+1013904223+k*97)&0xffffff;}
    gl.bindBuffer(gl.COPY_WRITE_BUFFER,r.simVbos[k]);gl.bufferSubData(gl.COPY_WRITE_BUFFER,0,a);
  }gl.bindBuffer(gl.COPY_WRITE_BUFFER,null);r.vboCur=1;
}
export function buffers(r){const gl=r.gl;return r.simVbos.map(buffer=>{const a=new Uint8Array(r.maxParticleCapacity*16);
  gl.bindBuffer(gl.COPY_READ_BUFFER,buffer);gl.getBufferSubData(gl.COPY_READ_BUFFER,0,a);gl.bindBuffer(gl.COPY_READ_BUFFER,null);return a;});}
export const equal=(a,b)=>a.length===b.length&&a.every((v,i)=>v===b[i]);
export async function hash(a){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',a))].map(v=>v.toString(16).padStart(2,'0')).join('');}
export async function png(blob){const bitmap=await createImageBitmap(blob),c=document.createElement('canvas');c.width=bitmap.width;c.height=bitmap.height;
  const ctx=c.getContext('2d');ctx.drawImage(bitmap,0,0);bitmap.close();return {width:c.width,height:c.height,hash:await hash(ctx.getImageData(0,0,c.width,c.height).data)};}
export function state(app){const r=app.renderer;return JSON.stringify({mode:app.mode,math:app.math,
  r:Object.fromEntries(['zoom','targetZoom','viewCenter','targetViewCenter','activePalette','bloomEnabled','viewMode','gain',
    'referenceDeposits','referenceSettled','referenceAutoDpp','accumReadIdx','accumulationFrames','vboCur','respawnRequested'].map(k=>[k,r[k]])),
  quality:Object.fromEntries(Object.entries(r.adaptive).filter(([k,v])=>k!=='renderer'&&typeof v!=='function'))});}
export function explore(app){app.setMode('explore');const r=app.renderer,m=app.math;m.reset();
  for(const key of ['a','b','c','d'])m['base'+key.toUpperCase()]=CONRADI_REFERENCE[key].clone();
  m.activeMorphology='lace';m.setSymmetry(11);m.setCoefficientOffset('a',.13,-.07);
  m.evolving=false;m.time=7.25;m.update(0,2.1);r.adaptive.setMode('potato');r.zoom=r.targetZoom=2.1;r.viewCenter=[.07,-.03];
  r.targetViewCenter=[.07,-.03];r.activePalette='solar';r.bloomEnabled=true;r.viewMode=0;r.gain=3;r.clearAccumulation();seed(r);}
export function reporter(){const results=[];return {results,check:(name,passed,details='')=>results.push({name,passed:!!passed,details}),
  async finish(){document.body.textContent=JSON.stringify(results,null,2);await fetch('/test_report',{method:'POST',body:JSON.stringify(results)});}};}
