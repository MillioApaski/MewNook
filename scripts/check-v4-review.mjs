import {createRequire}from'node:module'
const require=createRequire(import.meta.url),{chromium}=require('playwright-core'),{PNG}=require('pngjs')
import assert from'node:assert/strict'
import {mkdir,writeFile}from'node:fs/promises'
import {spawn}from'node:child_process'
const server=process.env.V4_SELF_HOST?spawn(process.execPath,['node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','4173'],{stdio:'ignore'}):null
let browser
const dir=process.env.V4_REVIEW_OUT||'/tmp/inochi-v4-review';await mkdir(dir,{recursive:true})
try{
 for(let i=0;i<40;i++){try{await fetch('http://127.0.0.1:4173');break}catch{await new Promise(r=>setTimeout(r,200))}}
 browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader','--use-angle=swiftshader','--enable-webgl']})
 const page=await browser.newPage({viewport:{width:1100,height:1050},deviceScaleFactor:1}),errors=[];page.on('pageerror',e=>errors.push(e.message))
 // Verify the canonical extensionless route itself, including its new default model.
 const response=await page.goto('http://127.0.0.1:4173/inochi2d-test/smoke?probe=1');assert.equal(response.status(),200);await page.locator('#status[data-state=ready]').waitFor({timeout:60000});assert.match(await page.locator('#status').textContent(),/v4 原画/)
 const snap=async(action,time)=>{
  const values=await page.evaluate(([n,t])=>window.__inochiProbe.actionFrame(n,t),[action,time]);await page.waitForTimeout(180);const bytes=await page.locator('figure').screenshot({path:`${dir}/${action}-${time}.png`});return{values,png:PNG.sync.read(bytes)}
 }
 const base=await snap('none',0)
 const difference=(a,b,region)=>{let count=0,outside=0;for(let y=0;y<a.height;y++)for(let x=0;x<a.width;x++){const i=(y*a.width+x)*4;const d=Math.abs(a.data[i]-b.data[i])+Math.abs(a.data[i+1]-b.data[i+1])+Math.abs(a.data[i+2]-b.data[i+2]);if(d>45){if(!region||(x>=region[0]&&y>=region[1]&&x<region[2]&&y<region[3]))count++;else outside++}}return{count,outside}}
 const report=[]
 for(const[action,id,t,region,min]of[['idle','idle',140,[275,120,380,210],70],['chat','chat',800,[270,105,390,230],15],['sleep','sleep',900,[270,105,390,230],70],['tap','tap',650,[200,10,490,400],500]]){
  await page.locator('#'+id).click();const frame=await snap(action,t);const d=difference(base.png,frame.png,region);assert.ok(d.count>=min,action+' no localized change '+JSON.stringify(d));if(action!=='tap')assert.equal(d.outside,0,action+' leaked outside the face')
  await page.locator('#reset').click();const reset=await snap('none',0);assert.deepEqual(reset.values,base.values,action+' stale parameters');const resetDiff=difference(base.png,reset.png);assert.ok(resetDiff.count<12,action+' failed to recover '+JSON.stringify(resetDiff));report.push({action,changedPixels:d.count,resetChangedPixels:resetDiff.count})
  const ended=await snap(action,6000);assert.deepEqual(ended.values,base.values,action+' automatic completion stale state')
 }
 await page.locator('#closeup').click();for(const[name,t]of[['none',0],['idle',140],['chat',800],['sleep',900],['tap',650]])await snap(name,t)
 assert.deepEqual(errors,[]);await writeFile(`${dir}/report.json`,JSON.stringify({canonicalRoute:'/inochi2d-test/smoke',report,errors},null,2)+'\n');console.log('Canonical smoke buttons, localized changes and recovery:',JSON.stringify(report))
}finally{await browser?.close();server?.kill()}
