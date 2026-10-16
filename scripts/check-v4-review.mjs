import {chromium} from 'playwright-core'
import {PNG} from 'pngjs'
import pixelmatch from 'pixelmatch'
import assert from 'node:assert/strict'
import {mkdir,writeFile} from 'node:fs/promises'
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',
 headless:true,args:JSON.parse(process.env.CHROME_ARGS||'[]').concat(['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader','--use-angle=swiftshader','--enable-webgl'])})
const dir='/tmp/inochi-v4-review';await mkdir(dir,{recursive:true})
try{
 const page=await browser.newPage({viewport:{width:1100,height:1050},deviceScaleFactor:1})
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.goto('http://127.0.0.1:4173/inochi2d-test/smoke.html?model=v4&probe=1')
 await page.locator('#status[data-state=ready]').waitFor({timeout:60000})
 let lastValues
 const snap=async(action,time)=>{
  lastValues=await page.evaluate(async([name,t])=>window.__inochiProbe.actionFrame(name,t),[action,time])
  await page.waitForTimeout(600)
  const bytes=await page.locator('figure').screenshot({path:`${dir}/${action}-${time}.png`})
  return PNG.sync.read(bytes)
 }
 const base=await snap('none',0),baseValues=lastValues
 function difference(a,b,box){
  const [x,y,w,h]=box,aa=new PNG({width:w,height:h}),bb=new PNG({width:w,height:h})
  PNG.bitblt(a,aa,x,y,w,h,0,0);PNG.bitblt(b,bb,x,y,w,h,0,0)
  return pixelmatch(aa.data,bb.data,null,w,h,{threshold:.1,includeAA:true})
 }
 const report=[]
 for(const [action,time,box,minimum] of [
  ['idle',150,[290,258,70,30],45],['chat',180,[320,283,30,22],8],
  ['sleep',800,[290,258,70,30],35],['tap',180,[245,185,140,65],35]
 ]){
  const frame=await snap(action,time),pixels=difference(base,frame,box)
  assert.ok(pixels>=minimum,`${action}: only ${pixels} changed pixels in intended region`)
  const recovered=await snap(action,6000)
  assert.deepEqual(lastValues,baseValues,`${action} left stale parameters`)
  const drift=difference(base,recovered,[0,0,base.width,base.height])
  assert.ok(drift<=base.width*base.height*.0003,`${action}: recovery drift ${drift} exceeds 0.03% GPU raster tolerance`)
  report.push({action,time,pixels,minimum})
 }
 // Save close-ups for human review; never treat changed pixels as art acceptance.
 await page.locator('#closeup').click()
 for(const [name,t] of [['none',0],['idle',150],['chat',180],['sleep',800],['tap',180],['tap',750]])await snap(name,t)
 assert.deepEqual(errors,[])
 await writeFile(`${dir}/report.json`,JSON.stringify(report,null,2))
 console.log('Localized v4 action checks and parameter recovery:',JSON.stringify(report))
 console.log('Human review of eyelid art, seams and expression quality is still required.')
}finally{await browser.close()}
