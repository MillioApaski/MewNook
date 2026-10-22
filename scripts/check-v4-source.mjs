import assert from'node:assert/strict'
import{spawn}from'node:child_process'
import{mkdir,writeFile}from'node:fs/promises'
import{fileURLToPath}from'node:url'
import path from'node:path'
import{createRequire}from'node:module'
const require=createRequire(import.meta.url),{chromium}=require('playwright-core'),{PNG}=require('pngjs')
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),out=process.env.V4_CHECK_OUT||path.join(root,'assets/inochi/v4/validation/source-runtime')
await mkdir(out,{recursive:true})
const server=spawn('python3',['-m','http.server','4181','--bind','127.0.0.1'],{cwd:root,stdio:'ignore'})
let browser
try{
 await new Promise(r=>setTimeout(r,350))
 browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/tmp/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader','--enable-webgl','--ignore-gpu-blocklist']})
 const p=await browser.newPage({viewport:{width:650,height:750}}),errors=[];p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error')errors.push(m.text())})
 await p.goto('http://127.0.0.1:4181/tests/fixtures/v4-source.html');await p.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);assert.equal(await p.evaluate(()=>document.body.dataset.error),undefined)
 const set=async(values)=>{await p.evaluate(v=>window.probe.set(v),values);await p.waitForTimeout(130)}
 const snapshot=async(name)=>{const bytes=await p.locator('canvas').screenshot();if(name)await writeFile(path.join(out,name+'.png'),bytes);return PNG.sync.read(bytes)}
 const clear=async()=>{await p.evaluate(()=>window.probe.action('none',0));await set({ParamBreath:0,ParamTailDeform:0})}
 const diff=(a,b,region)=>{let count=0,box=[a.width,a.height,0,0];for(let y=0;y<a.height;y++)for(let x=0;x<a.width;x++){if(region&&(x<region[0]||y<region[1]||x>=region[2]||y>=region[3]))continue;let i=(y*a.width+x)*4;let d=Math.abs(a.data[i]-b.data[i])+Math.abs(a.data[i+1]-b.data[i+1])+Math.abs(a.data[i+2]-b.data[i+2]);if(d>45){count++;box=[Math.min(box[0],x),Math.min(box[1],y),Math.max(box[2],x),Math.max(box[3],y)]}}return{count,box}}
 await clear();const baseline=await snapshot('neutral'),report={browser:await browser.version(),actions:{},parameters:{},errors}
 for(const[name,t]of[['idle',140],['chat',800],['sleep',900],['tap',650]]){
  await clear();const values=await p.evaluate(([n,t])=>window.probe.action(n,t),[name,t]);await p.waitForTimeout(150);const shot=await snapshot(name);const change=diff(baseline,shot);assert.ok(change.count>25,name+' caused no visible change');report.actions[name]={...change,values}
  await clear();const reset=diff(baseline,await snapshot());assert.ok(reset.count<12,name+' did not reset: '+JSON.stringify(reset));report.actions[name].resetChangedPixels=reset.count
 }
 for(const name of['ParamHeadRoll','ParamHairLeft','ParamHairRight','ParamHairFront','ParamEarLeft','ParamEarRight','ParamTailDeform','ParamBreath','ParamBrowLeft','ParamBrowRight']){
  await clear();await set({[name]:1});const pos=diff(baseline,await snapshot(name+'-positive'));await set({[name]:-1});const neg=diff(baseline,await snapshot(name+'-negative'));assert.ok(pos.count>2&&neg.count>2,name+' binding has no visible effect');report.parameters[name]={positive:pos,negative:neg}
 }
 // Every pair of adjacent slots gets exercised by the actual WASM renderer.
 for(const name of['ParamEyeBlinkLeft','ParamEyeBlinkRight','ParamMouthOpen','ParamDrowsyMouth']){
  await clear();const counts=[];for(let k=0;k<=16;k++){await set({[name]:k/16});counts.push(diff(baseline,await snapshot()).count)}assert.equal(counts[0],0);assert.ok(Math.max(...counts)>8);report.parameters[name]={intermediateChangedPixels:counts}
 }
 // Cross-expression switching must clear every previous action's owned parameter.
 for(const name of['chat','sleep','tap','idle','sleep','chat','tap']){await p.evaluate(n=>window.probe.action(n,650),name);await p.waitForTimeout(90)}
 await clear();report.switchReset=diff(baseline,await snapshot('reset'));assert.ok(report.switchReset.count<12)
 await p.evaluate(()=>window.probe.camera(0,350,.95));await clear();await snapshot('face-neutral');for(const[n,t]of[['idle',140],['chat',800],['sleep',900],['tap',650]]){await p.evaluate(([n,t])=>window.probe.action(n,t),[n,t]);await p.waitForTimeout(150);await snapshot('face-'+n)}
 report.debug=await p.evaluate(()=>window.probe.debug());assert.deepEqual(errors,[]);assert.equal(report.debug.canvasDataset.inochi2dTickError,undefined);await writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({actions:report.actions,parameters:Object.keys(report.parameters),switchReset:report.switchReset,errors},null,2))
}finally{await browser?.close();server.kill()}
