import http from 'node:http'
import {createHash} from 'node:crypto'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import {readFile,mkdir,writeFile} from 'node:fs/promises'
import assert from 'node:assert/strict'
import {chromium} from 'playwright-core'
import {PNG} from 'pngjs'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),out=path.join(root,'assets/inochi/v4/validation/fixed-face')
await mkdir(out,{recursive:true})
const withoutEyeballs=bytes=>{
 const length=bytes.readUInt32BE(8),model=JSON.parse(bytes.subarray(12,12+length).toString())
 const visit=node=>{if(/ independent (iris|sclera)$/.test(node.name))node.opacity=0;for(const child of node.children||[])visit(child)};visit(model.nodes)
 const json=Buffer.from(JSON.stringify(model)),header=Buffer.alloc(12);bytes.copy(header,0,0,8);header.writeUInt32BE(json.length,8)
 return Buffer.concat([header,json,bytes.subarray(12+length)])
}
const server=http.createServer(async(req,res)=>{try{const f=path.join(root,req.url.split('?')[0]);res.setHeader('Content-Type',f.endsWith('.js')?'text/javascript':f.endsWith('.wasm')?'application/wasm':f.endsWith('.html')?'text/html':'application/octet-stream');const bytes=await readFile(f);res.end(req.url.includes('without-eyeballs')&&f.endsWith('.inx')?withoutEyeballs(bytes):bytes)}catch{res.statusCode=404;res.end()}})
await new Promise(r=>server.listen(4199,'127.0.0.1',r));let b
try{
 b=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/tmp/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader','--enable-webgl']})
 const p=await b.newPage({viewport:{width:650,height:750}}),errors=[];p.on('pageerror',e=>errors.push(e.message))
 await p.goto('http://127.0.0.1:4199/tests/fixtures/v4-source.html');await p.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);assert.equal(await p.evaluate(()=>document.body.dataset.error),undefined)
 await p.evaluate(()=>window.probe.camera(0,350,1.5))
 const capture=async(name)=>{await p.waitForTimeout(120);const bytes=await p.locator('canvas').screenshot();await writeFile(path.join(out,name+'.png'),bytes);return PNG.sync.read(bytes)}
 const difference=(a,b,region)=>{let n=0;for(let y=region[1];y<region[3];y++)for(let x=region[0];x<region[2];x++){let i=(y*a.width+x)*4;if(Math.abs(a.data[i]-b.data[i])+Math.abs(a.data[i+1]-b.data[i+1])+Math.abs(a.data[i+2]-b.data[i+2])>12)n++}return n}
 await p.evaluate(()=>window.probe.action('none',0));const original=await capture('open'),report={eyes:[],errors}
 for(const t of [.25,.5,.75,1]){
  await p.evaluate(t=>window.probe.set({ParamEyeBlinkLeft:t,ParamEyeBlinkRight:t}),t);const frame=await capture('closure-'+Math.round(t*100))
  const protectedChanges=difference(original,frame,[0,0,650,145]);assert.equal(protectedChanges,0,'Blink changed foreground crown hair')
  const cheekChanges=difference(original,frame,[195,316,255,350]);assert.equal(cheekChanges,0,'Blink dragged the outer eye/cheek contour')
  const eyeChanges=difference(original,frame,[180,190,490,330]);assert.ok(eyeChanges>50,'Eyelid mesh did not move')
  let exposedBluePixels=0
  if(t===1){for(const region of [[215,230,310,325],[385,170,475,265]])for(let y=region[1];y<region[3];y++)for(let x=region[0];x<region[2];x++){const i=(y*frame.width+x)*4;if(frame.data[i+2]-frame.data[i]>45&&frame.data[i+2]-frame.data[i+1]>20&&frame.data[i]<150)exposedBluePixels++}assert.ok(exposedBluePixels<6,'Iris leaked through closed upper lid: '+exposedBluePixels)}
  if(t===1){
   const hidden=await b.newPage({viewport:{width:650,height:750}})
   await hidden.goto('http://127.0.0.1:4199/tests/fixtures/v4-source.html?without-eyeballs');await hidden.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);assert.equal(await hidden.evaluate(()=>document.body.dataset.error),undefined)
   await hidden.evaluate(async()=>{await window.probe.camera(0,350,1.5);await window.probe.action('none',0);await window.probe.set({ParamEyeBlinkLeft:1,ParamEyeBlinkRight:1})});await hidden.waitForTimeout(120)
   const masked=PNG.sync.read(await hidden.locator('canvas').screenshot());report.closedEyeballContributionPixels=difference(frame,masked,[0,0,650,750]);assert.equal(report.closedEyeballContributionPixels,0,'Eyeball still contributes pixels through closed lids');await hidden.close()
  }
  report.eyes.push({closure:t,protectedCheekChanges:cheekChanges,protectedHairChanges:protectedChanges,eyeChangedPixels:eyeChanges,...(t===1?{exposedBluePixels}:{})})
 }
 await p.evaluate(()=>window.probe.set({ParamDrowsyMouth:1}));const sleepy=await capture('sleepy');assert.ok(difference(original,sleepy,[310,310,410,360])>2,'Tiny sleepy mouth missing')
 await p.evaluate(()=>window.probe.action('none',0));const reset=await capture('reset');report.resetChangedPixels=difference(original,reset,[0,0,650,750]);assert.ok(report.resetChangedPixels<12);assert.deepEqual(errors,[])
 for(const direction of [-1,1]){
  await p.evaluate(direction=>window.probe.set({ParamHairFront:direction,ParamHairLeft:direction,ParamEyeBlinkLeft:1,ParamEyeBlinkRight:1}),direction)
  await capture('hair-wind-'+(direction>0?'positive':'negative'))
 }
 await p.evaluate(()=>window.probe.action('none',0));const finalReset=await capture('reset');report.hairWindResetChangedPixels=difference(original,finalReset,[0,0,650,750]);assert.equal(report.hairWindResetChangedPixels,0)
 for(const direction of [-1,1]){
  await p.evaluate(direction=>window.probe.set({ParamHeadRoll:direction,ParamEyeBlinkLeft:1,ParamEyeBlinkRight:1}),direction)
  await capture('head-roll-'+(direction>0?'positive':'negative'))
 }
 await p.evaluate(()=>window.probe.action('none',0));const headReset=await capture('reset');report.headRollResetChangedPixels=difference(original,headReset,[0,0,650,750]);assert.equal(report.headRollResetChangedPixels,0)
 report.modelSha256=createHash('sha256').update(await readFile(path.join(root,'assets/inochi/v4/rig/MewNook-v4-source-rig.inx'))).digest('hex');report.browser=await b.version();report.fixedFace='single static texture; separate eyeball, moving upper/lower lid meshes and hair';await writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report))
}finally{await b?.close();server.close()}
