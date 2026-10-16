import {chromium} from 'playwright-core'
import {PNG} from 'pngjs'
import pixelmatch from 'pixelmatch'
import {mkdir} from 'node:fs/promises'

const browser=await chromium.launch({
 executablePath:'/usr/bin/google-chrome',headless:true,
 args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader','--use-angle=swiftshader','--enable-webgl']
})
const page=await browser.newPage({viewport:{width:1100,height:950},deviceScaleFactor:1})
await mkdir('/tmp/inochi-v4-shots',{recursive:true})
const params=[
 ['ParamEyeBlinkLeft',25],['ParamEyeBlinkRight',25],
 ['ParamMouthOpen',10],['ParamEarLeft',10],['ParamEarRight',10],
 ['ParamHairLeft',10],['ParamHairRight',10],['ParamTailDeform',10],
 ['ParamSleepyLeft',10],['ParamSleepyRight',10]
]
const results=[]
try{
 page.on('pageerror',e=>console.log('V4 PAGE ERROR:',e.message))
 await page.goto('http://127.0.0.1:4173/inochi2d-test/smoke.html?model=v4&probe=1')
 await page.locator('#status[data-state="ready"]').waitFor({timeout:60000})
 await page.waitForTimeout(400)
 const figure=page.locator('figure')
 async function set(name,value){
   await page.evaluate(async ([id,val])=>window.__inochiProbe.set(id,val),[name,value])
   await page.waitForTimeout(280)
 }
 const snap=async(path)=>PNG.sync.read(await figure.screenshot(path?{path}:{animations:'disabled'}))
 for(const [name,min] of params){
   await set(name,-1)
   const before=await snap('/tmp/inochi-v4-shots/'+name+'-minus.png')
   await set(name,1)
   const after=await snap('/tmp/inochi-v4-shots/'+name+'-plus.png')
   const pixels=pixelmatch(before.data,after.data,null,before.width,before.height,
     {threshold:.12,includeAA:true})
   const metric={name,pixels,minimum:min}
   results.push(metric)
   console.log('V4 REAL CHROME FRAMES:',JSON.stringify(metric))
   await set(name,0)
 }
 const failed=results.filter(x=>x.pixels<x.minimum)
 if(failed.length)throw Error('v4 parameter visual regression '+JSON.stringify(failed))
 console.log('V4 ENGINEERING RENDER SUCCESS:',results.length,'controls caused real pixel changes.')
 console.log('Artistic acceptability, hidden-area painting and Creator project not tested.')
}finally{await browser.close()}
