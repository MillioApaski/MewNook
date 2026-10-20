import {chromium} from 'playwright-core'
import {PNG} from 'pngjs'
import pixelmatch from 'pixelmatch'
import {mkdir,writeFile} from 'node:fs/promises'

const browser=await chromium.launch({
 executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',headless:true,
 args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader','--use-angle=swiftshader','--enable-webgl']
})
const page=await browser.newPage({viewport:{width:1100,height:950},deviceScaleFactor:1})
await mkdir('/tmp/inochi-v4-shots',{recursive:true})
const params=[
 ['ParamEyeBlinkLeft',25],['ParamEyeBlinkRight',25],
 ['ParamMouthOpen',10],['ParamEarLeft',10],['ParamEarRight',10],
 ['ParamHairLeft',10],['ParamHairRight',10],['ParamTailDeform',10],
 ['ParamBrowLeft',3],['ParamBrowRight',3],['ParamHeadRoll',50]
]
const results=[]
try{
 page.on('pageerror',e=>console.log('V4 PAGE ERROR:',e.message))
 await page.goto('http://127.0.0.1:4173/inochi2d-test/smoke?model=v4&probe=1')
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
 await writeFile('/tmp/inochi-v4-shots/report.json',JSON.stringify(results,null,2))

 // Test the user-facing buttons. Pixel-only parameter checks missed several
 // no-op reactions in the earlier tilted rig.
 await page.goto('http://127.0.0.1:4173/inochi2d-test/smoke?model=v4')
 await page.locator('#status[data-state=ready]').waitFor({timeout:60000})
 for(const [button,label,delay] of [
   ['tap','摸头回应中',300],
   ['idle','上眼皮闭合中',160],
   ['chat','正在说话',450],
   ['sleep','困倦半睁眼',450]
 ]){
   await page.locator('#'+button).click()
   await page.getByText(label,{exact:true}).waitFor()
   await page.waitForTimeout(delay)
   await page.locator('figure').screenshot({path:'/tmp/inochi-v4-shots/button-'+button+'.png'})
   console.log('V4 UI BUTTON CHECK:',button)
 }

 // Keep production v3 unchanged, but verify v4 works in the actual MewNook
 // React room when the user explicitly selects the upright experiment.
 await page.addInitScript(()=>{
   const old=JSON.parse(localStorage.getItem('mewnook:settings')||'{}')
   localStorage.setItem('mewnook:settings',JSON.stringify({
     ...old,inochiTestMode:true,inochiModel:'v4',inochiScale:0.32,scene:'day'
   }))
 })
 await page.goto('http://127.0.0.1:4173/')
 await page.locator('canvas.inochi-demo-canvas[data-model-version="v4"]').waitFor({timeout:60000})
 await page.locator('.art-character.inochi-ready').waitFor({timeout:60000})
 const roomStatus=await page.locator('canvas.inochi-demo-canvas').getAttribute('data-inochi2d-model-status')
 if(roomStatus!=='loaded')throw Error('v4 not loaded in real room: '+roomStatus)
 await page.locator('.art-stage').screenshot({path:'/tmp/inochi-v4-shots/mewnook-upright-room.png'})
 console.log('V4 REAL ROOM INTEGRATION: passed. v4 explicitly selected and loaded.')
 console.log('Artistic acceptability, hidden-area painting and Creator project not tested.')
}finally{await browser.close()}
