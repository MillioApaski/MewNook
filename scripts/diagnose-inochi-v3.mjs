import {chromium} from 'playwright-core'
import {PNG} from 'pngjs'
import pixelmatch from 'pixelmatch'
import {mkdir,writeFile} from 'node:fs/promises'
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',
  headless:true,args:['--no-sandbox','--disable-dev-shm-usage',
    '--enable-unsafe-swiftshader','--use-angle=swiftshader','--enable-webgl']})
const page=await browser.newPage({viewport:{width:1100,height:950},deviceScaleFactor:1})
await mkdir('/tmp/inochi-v3-shots',{recursive:true})
const results=[]
page.on('pageerror',e=>console.log('PAGE ERROR',e.message))
try{
 for(const model of ['v2','v3']){
   await page.goto('http://127.0.0.1:4173/inochi2d-test/smoke.html?model='+model+'&probe=1')
   await page.locator('#status[data-state=ready]').waitFor({timeout:60000})
   await page.waitForTimeout(450)
   const figure=page.locator('figure')
   const names=model==='v2'?['ParamEyeBlinkLeft']:['ParamEyeBlinkLeft','ParamHairLeft','ParamHairRight','ParamHairFront','ParamTailDeform',
    'ParamEarLeft','ParamEarRight','ParamSleepy','ParamMouthOpen','ParamEmbarrassed']
   for(const name of names){
     const set=async value=>{
       await page.evaluate(async ([id,val])=>window.__inochiProbe.set(id,val),[name,value])
       await page.waitForTimeout(300)
     }
     await set(-1)
     const first=PNG.sync.read(await figure.screenshot())
     await set(1)
     const second=PNG.sync.read(await figure.screenshot())
     const pixels=pixelmatch(first.data,second.data,null,first.width,first.height,{threshold:0.1,includeAA:true})
     // A correct speaking mouth must stay on the tilted face, not float
    // near the chin or deform a big rectangle around the character.
    if(model==='v3' && name==='ParamMouthOpen'){
      let minX=first.width,minY=first.height,maxX=0,maxY=0,count=0
      for(let y=0;y<first.height;y++)for(let x=0;x<first.width;x++){
        const ix=(y*first.width+x)*4
        const delta=Math.abs(first.data[ix]-second.data[ix])
          +Math.abs(first.data[ix+1]-second.data[ix+1])
          +Math.abs(first.data[ix+2]-second.data[ix+2])
        if(delta>55){minX=Math.min(minX,x);maxX=Math.max(maxX,x);
          minY=Math.min(minY,y);maxY=Math.max(maxY,y);count++}
      }
      console.log('TILTED MOUTH REGION:',JSON.stringify({minX,minY,maxX,maxY,count}))
      if(count<10 || minX<275 || maxX>370 || minY<270 || maxY>380)
        throw Error('Mouth is absent or outside the tilted face')
      await set(0)
      await figure.screenshot({path:'/tmp/inochi-v3-shots/mouth-neutral.png'})
      await set(.5)
      await figure.screenshot({path:'/tmp/inochi-v3-shots/mouth-small-open.png'})
      await set(1)
      await figure.screenshot({path:'/tmp/inochi-v3-shots/mouth-wide-open.png'})
    }
    const item={model,param:name,pixels}
     results.push(item)
     console.log('REAL FRAME COMPARISON:',JSON.stringify(item))
     if(name==='ParamEyeBlinkLeft'||name==='ParamHairLeft'||name==='ParamTailDeform'||name==='ParamEarLeft'||name==='ParamSleepy'||name==='ParamMouthOpen'){
       await writeFile('/tmp/inochi-v3-shots/'+model+'-'+name+'-minus.png',PNG.sync.write(first))
       await writeFile('/tmp/inochi-v3-shots/'+model+'-'+name+'-plus.png',PNG.sync.write(second))
     }
     await set(0)
   }
 }
 // Capture the three eye states in a stable browser scene with no idle tick.
 await page.goto('http://127.0.0.1:4173/inochi2d-test/smoke.html?model=v3&probe=1')
 await page.locator('#status[data-state=ready]').waitFor({timeout:60000})
 const eyes=page.locator('figure')
 const setEye=async (name,value)=>{
   await page.evaluate(async ([id,val])=>window.__inochiProbe.set(id,val),[name,value])
   await page.waitForTimeout(250)
 }
 await setEye('ParamEyeBlinkLeft',0)
 await setEye('ParamEyeBlinkRight',0)
 await setEye('ParamSleepy',0)
 const wideOpen=PNG.sync.read(await eyes.screenshot({path:'/tmp/inochi-v3-shots/eyes-open.png'}))
 await setEye('ParamSleepy',1)
 const halfClosed=PNG.sync.read(await eyes.screenshot({path:'/tmp/inochi-v3-shots/eyes-drowsy.png'}))
 await setEye('ParamSleepy',0)
 await setEye('ParamEyeBlinkLeft',1)
 await setEye('ParamEyeBlinkRight',1)
 const fullyClosed=PNG.sync.read(await eyes.screenshot({path:'/tmp/inochi-v3-shots/eyes-closed.png'}))
 const sleepyDelta=pixelmatch(wideOpen.data,halfClosed.data,null,wideOpen.width,wideOpen.height,{threshold:.1,includeAA:true})
 const blinkDelta=pixelmatch(wideOpen.data,fullyClosed.data,null,wideOpen.width,wideOpen.height,{threshold:.1,includeAA:true})
 console.log('EYE STATE REVIEW:',JSON.stringify({sleepyDelta,blinkDelta}))
 if(sleepyDelta<70||blinkDelta<70)throw Error('Eyes do not react to drowsy / blink states')
 // Check the actual smoke-page buttons, not just direct parameter writes.
 await page.goto('http://127.0.0.1:4173/inochi2d-test/smoke.html?model=v3')
 await page.locator('#status[data-state=ready]').waitFor({timeout:60000})
 for(const [button,text] of [
  ['#tap','猫耳抖动中'],['#idle','上眼皮闭合中'],
  ['#chat','正在说话'],['#sleep','困倦半睁眼']
 ]){
   await page.locator(button).click()
   await page.getByText(text,{exact:true}).waitFor()
   const filename='/tmp/inochi-v3-shots/button-'+button.slice(1)+'.png'
   await page.waitForTimeout(button==='#idle'?160:450)
   await page.locator('figure').screenshot({path:filename})
   console.log('UI BUTTON TEST:',button,text)
 }
 // Integration test: same v3 rig must load inside the actual MewNook React scene.
 await page.addInitScript(()=>{
   localStorage.setItem('mewnook:settings',JSON.stringify({
     inochiTestMode:true,inochiScale:0.32,scene:'day',city:''
   }))
 })
 await page.goto('http://127.0.0.1:4173/')
 await page.locator('.art-character.inochi-ready').waitFor({timeout:60000})
 const status=await page.locator('.inochi-demo-canvas').getAttribute('data-inochi2d-model-status')
 if(status!=='loaded')throw Error('MewNook React failed to load v3: '+status)
 await page.locator('.art-stage').screenshot({path:'/tmp/inochi-v3-shots/mewnook-main-v3.png'})
 console.log('MEWNOOK APP INTEGRATION: v3 canvas loaded')
 await writeFile('/tmp/inochi-v3-shots/report.json',JSON.stringify(results,null,2))
}finally{await browser.close()}
if(results.find(x=>x.model==='v2'&&x.param==='ParamEyeBlinkLeft')?.pixels<40)
 throw Error('V2 eye overlays are still behind base or not visible')
if(results.find(x=>x.model==='v3'&&x.param==='ParamEyeBlinkLeft')?.pixels<40)
 throw Error('V3 eye blink has no visible effect')
if(results.filter(x=>x.model==='v3'&&['ParamHairLeft','ParamHairRight','ParamTailDeform'].includes(x.param)).some(x=>x.pixels<80))
 throw Error('V3 hair/tail params have insufficient visible pixel changes')
for(const [name,min] of [
  ['ParamEarLeft',30],['ParamEarRight',30],['ParamSleepy',40],
  ['ParamMouthOpen',20],['ParamEmbarrassed',5]
 ]){
 const match=results.find(x=>x.model==='v3'&&x.param===name)
 if(!match || match.pixels<min)throw Error('V3 face or ear motion missing: '+name+' changed '+(match?.pixels||0)+' pixels')
}
