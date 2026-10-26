import assert from 'node:assert/strict'
import {mkdir,writeFile,readFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import {chromium} from 'playwright-core'
import {PNG} from 'pngjs'
const origin=process.env.ROOM_TEST_ORIGIN||'http://127.0.0.1:4173',out='assets/inochi/v4/validation/focus-working'
await mkdir(out,{recursive:true})
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader','--enable-webgl']})
const report={cases:[],errors:[]}
const changed=(a,b,box)=>{let count=0;for(let y=box[1];y<box[3];y++)for(let x=box[0];x<box[2];x++){const i=(y*a.width+x)*4;if(Math.abs(a.data[i]-b.data[i])+Math.abs(a.data[i+1]-b.data[i+1])+Math.abs(a.data[i+2]-b.data[i+2])>35)count++}return count}
try{
 for(const [scene,width,height]of[['day',1440,1000],['day',2560,1080],['rain',1440,1000],['sunset',1440,1000],['night',1440,1000],['day',390,844]]){
  const p=await browser.newPage({viewport:{width,height}}),requests=[]
  p.on('pageerror',e=>report.errors.push(e.message));p.on('request',r=>{if(r.url().includes('MewNook-hands.inx'))requests.push(r.url())})
  await p.addInitScript(scene=>{localStorage.setItem('mewnook:settings',JSON.stringify({scene,city:''}));localStorage.setItem('mewnook:focusPose',JSON.stringify('reading'))},scene)
  await p.goto(origin);await p.locator('.inochi-demo-canvas[data-model-state=ready]').waitFor({timeout:60000})
  assert.equal(requests.length,0,'Idle must not load a second model')
  await p.getByRole('button',{name:'开始或继续计时',exact:true}).click()
  await p.waitForFunction(()=>Number(document.querySelector('.inochi-demo-canvas').dataset.focusBlend)>.999,null,{timeout:30000})
  await p.addStyleTag({content:'.vn-dialogue{visibility:hidden!important}'})
  const layers=await p.locator('.art-stage').evaluate(e=>[...e.children].map(c=>[c.dataset.roomLayer,Number(getComputedStyle(c).zIndex)]))
  assert.deepEqual(layers,[['background',0],['character',2],['desk',3],['hands',4]])
  const geometry=await p.evaluate(()=>{
   const body=document.querySelector('.inochi-demo-canvas'),hands=document.querySelector('.source-hands-canvas'),b=body.getBoundingClientRect(),d=body.dataset
   const scale=Number(d.inochi2dCameraScale)/Number(d.inochi2dDevicePixelRatio),top=b.y+b.height/2+(Number(d.inochi2dCameraY)-701)*scale
   const x=v=>b.x+b.width/2+(v-561)*scale,y=v=>top+v*scale
   return{scale,frontScale:Number(hands.dataset.sourceScale),top,frontTop:Number(hands.dataset.sourceTop),region:[Math.max(0,Math.floor(x(400))),Math.max(0,Math.floor(y(940))),Math.min(innerWidth,Math.ceil(x(800))),Math.min(innerHeight,Math.ceil(y(1020)))]}
  })
  assert.ok(Math.abs(geometry.scale-geometry.frontScale)<.001);assert.ok(Math.abs(geometry.top-geometry.frontTop)<1)
  assert.ok(geometry.region[3]>geometry.region[1]&&geometry.region[2]>geometry.region[0],'Hands fell outside the viewport')
  await p.screenshot({path:out+`/${scene}-${width}-reading.png`})
  const front=PNG.sync.read(await p.screenshot())
  await p.locator('.source-hands-frame').evaluate(e=>e.style.visibility='hidden')
  const noHands=PNG.sync.read(await p.screenshot())
  const visibleHandPixels=changed(front,noHands,geometry.region);assert.ok(visibleHandPixels>100,'No actual hands/book pixels on the table')
  await p.locator('.source-hands-frame').evaluate(e=>e.style.visibility='')
  await p.locator('.source-hands-layer').evaluate(e=>e.style.zIndex='1')
  const behind=PNG.sync.read(await p.screenshot()),foregroundPixels=changed(front,behind,geometry.region)
  assert.ok(foregroundPixels>100,'Desktop did not occlude the lowered hand layer: '+JSON.stringify({scene,width,foregroundPixels,geometry}))
  await p.locator('.source-hands-layer').evaluate(e=>e.style.zIndex='4')
  await p.getByRole('button',{name:'番茄钟',exact:true}).click()
  await p.getByRole('combobox',{name:'专注时猫娘的动作',exact:true}).selectOption('typing')
  await p.getByRole('button',{name:'关闭面板',exact:true}).click()
  await p.waitForFunction(()=>document.querySelector('.inochi-demo-canvas').dataset.focusPose==='typing')
  await p.waitForTimeout(1600)
  assert.equal(requests.length,1,'Switching poses must reuse the foreground renderer')
  await p.screenshot({path:out+`/${scene}-${width}-typing.png`})
  await p.locator('.source-head-target').click()
  await p.waitForFunction(()=>document.querySelector('.inochi-demo-canvas').dataset.headPat==='active')
  assert.equal(await p.locator('.inochi-demo-canvas').getAttribute('data-focus-pose'),'typing')
  if(scene==='day'&&width===1440){
   await p.getByRole('button',{name:'设置',exact:true}).click()
   await p.getByRole('combobox',{name:'场景',exact:true}).selectOption('rain')
   await p.getByRole('button',{name:'关闭面板',exact:true}).click()
   await p.waitForFunction(()=>document.querySelector('.art-rain')&&Number(document.querySelector('.inochi-demo-canvas')?.dataset.focusBlend)>.999,null,{timeout:30000})
   assert.equal(await p.locator('.inochi-demo-canvas').getAttribute('data-focus-pose'),'typing')
   report.sceneSwitchDuringFocus=true
  }
  await p.getByRole('button',{name:'暂停计时',exact:true}).click()
  await p.waitForFunction(()=>Number(document.querySelector('.inochi-demo-canvas').dataset.focusBlend)===0)
  assert.equal(await p.locator('.source-hands-canvas').getAttribute('data-render-paused'),'true')
  report.cases.push({scene,width,height,layers,geometry,foregroundPixels,visibleHandPixels,poseSwitch:true,headPatKeepsWorking:true,pauseRestoresIdle:true})
  if(scene==='day'&&width===1440){
   await p.waitForFunction(()=>!!navigator.serviceWorker.controller)
   await p.reload();await p.locator('.inochi-demo-canvas[data-model-state=ready]').waitFor({timeout:60000})
   await p.getByRole('button',{name:'开始或继续计时',exact:true}).click()
   await p.waitForFunction(()=>Number(document.querySelector('.inochi-demo-canvas').dataset.focusBlend)>.999,null,{timeout:30000})
   await p.getByRole('button',{name:'暂停计时',exact:true}).click()
   await p.waitForFunction(()=>Number(document.querySelector('.inochi-demo-canvas').dataset.focusBlend)===0)
   await p.context().setOffline(true);await p.reload();await p.locator('.inochi-demo-canvas[data-model-state=ready]').waitFor({timeout:60000})
   await p.getByRole('button',{name:'开始或继续计时',exact:true}).click()
   await p.waitForFunction(()=>Number(document.querySelector('.inochi-demo-canvas').dataset.focusBlend)>.999,null,{timeout:30000})
   report.cachedFocusOffline=true;await p.context().setOffline(false)
  }
  await p.close()
 }
 const failed=await browser.newPage({serviceWorkers:'block'})
 await failed.addInitScript(()=>localStorage.setItem('mewnook:settings',JSON.stringify({scene:'day',city:''})))
 await failed.route('**/MewNook-hands.inx*',route=>route.abort());await failed.goto(origin)
 await failed.locator('.inochi-demo-canvas[data-model-state=ready]').waitFor({timeout:60000})
 await failed.getByRole('button',{name:'开始或继续计时',exact:true}).click()
 await failed.locator('[data-hands-state=error]').waitFor({state:'attached'})
 assert.equal(await failed.locator('.inochi-demo-canvas').getAttribute('data-focus-blend'),'0.000')
 report.handsLoadFailureKeepsBody=true;await failed.close()
 assert.deepEqual(report.errors,[])
 report.bodySha256=createHash('sha256').update(await readFile('public/inochi2d/v4/MewNook.inx')).digest('hex')
 report.handsSha256=createHash('sha256').update(await readFile('public/inochi2d/v4/MewNook-hands.inx')).digest('hex')
 await writeFile(out+'/report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report))
}finally{await browser.close()}
