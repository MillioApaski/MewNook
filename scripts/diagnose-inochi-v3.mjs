import { chromium } from 'playwright-core'
import { PNG } from 'pngjs'
import pixelmatch from 'pixelmatch'
import {mkdir,writeFile} from 'node:fs/promises'

const browser=await chromium.launch({
  executablePath:'/usr/bin/google-chrome',headless:true,
  args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader',
    '--use-angle=swiftshader','--enable-webgl','--disable-gpu-sandbox']
})
const page=await browser.newPage({viewport:{width:1100,height:950},deviceScaleFactor:1})
const results=[]
await mkdir('/tmp/inochi-v3-shots',{recursive:true})
try{
  page.on('pageerror',err=>console.log('PAGE ERROR:',err.message))
  page.on('console',msg=>{
    if(msg.type()==='error'||msg.type()==='warn')console.log('BROWSER:',msg.text().slice(0,400))
  })
  await page.goto('http://127.0.0.1:4173/inochi2d-test/smoke.html?model=v2&probe=1',{waitUntil:'load'})
  await page.locator('#status[data-state=ready]').waitFor({timeout:60000})
  await page.waitForTimeout(750)
  const figure=page.locator('figure')
  async function set(name,value){
    await page.evaluate(async ([id,val])=>window.__inochiProbe.set(id,val),[name,value])
    await page.waitForTimeout(340)
  }
  async function shot(){
    return PNG.sync.read(await figure.screenshot({animations:'disabled'}))
  }
  for(const name of ['ParamEyeBlinkLeft']){
    await set(name,-1)
    const a=await shot()
    await set(name,1)
    const b=await shot()
    const pixels=pixelmatch(a.data,b.data,null,a.width,a.height,{threshold:0.1,includeAA:true})
    const metric={param:name,pixels,dimensions:`${a.width}x${a.height}`}
    results.push(metric)
    console.log('REAL FRAME COMPARISON:',JSON.stringify(metric))
    // Report first; compare v2 control to v3 in the next diagnostic run.
    // Visual deformation assertions remain temporarily disabled during control calibration.
    if(name==='ParamEyeBlinkLeft'||name==='ParamHairLeft'){
      await writeFile('/tmp/inochi-v3-shots/'+name+'-minus.png',PNG.sync.write(a))
      await writeFile('/tmp/inochi-v3-shots/'+name+'-plus.png',PNG.sync.write(b))
    }
    await set(name,0)
  }
  console.log('PROBE DEBUG:',JSON.stringify(await page.evaluate(()=>window.__inochiProbe.debug())).slice(0,2800))
  await writeFile('/tmp/inochi-v3-shots/report.json',JSON.stringify(results,null,2))
} finally{
  await browser.close()
}
