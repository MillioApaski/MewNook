import assert from'node:assert/strict'
import{chromium}from'playwright-core'
import{mkdir,writeFile}from'node:fs/promises'
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader','--use-angle=swiftshader','--enable-webgl']})
const out=process.env.ROOM_CHECK_OUT||'/tmp/mewnook-source-room';await mkdir(out,{recursive:true});const report=[]
try{
 const fresh=await browser.newPage({viewport:{width:1440,height:1000}})
 const errors=[];fresh.on('pageerror',e=>errors.push(e.message))
 let releaseModel;const held=new Promise(resolve=>{releaseModel=resolve})
 await fresh.route('**/inochi2d/v4/MewNook.inx*',async route=>{await held;await route.continue()})
 let oldPortraitRequested=false;fresh.on('request',r=>{if(/\/assets\/(rooms\/[^/]+\/character|companion\/)/.test(r.url()))oldPortraitRequested=true})
 await fresh.goto('http://127.0.0.1:4173/',{waitUntil:'domcontentloaded'})
 await fresh.waitForFunction(()=>{const p=document.querySelector('.source-character-poster');return p?.complete&&p.naturalWidth>0})
 assert.equal(await fresh.locator('canvas').getAttribute('data-model-state'),'loading')
 assert.equal(await fresh.locator('.source-character-poster').evaluate(p=>getComputedStyle(p).visibility),'visible')
 assert.equal(await fresh.locator('.art-character img').evaluate(p=>getComputedStyle(p).visibility),'hidden')
 assert.equal(await fresh.locator('canvas').evaluate(c=>getComputedStyle(c).visibility),'hidden')
 assert.equal(await fresh.locator('.inochi-demo-layer').evaluate(p=>getComputedStyle(p).opacity),'1')
 await fresh.screenshot({path:out+'/loading-poster.png'})
 await fresh.setViewportSize({width:390,height:844});await fresh.waitForTimeout(100)
 await fresh.screenshot({path:out+'/loading-poster-mobile.png'})
 await fresh.setViewportSize({width:1440,height:1000});releaseModel()

 await fresh.locator('canvas[data-model-revision="source-art-20261020"]').waitFor({timeout:60000})
 await fresh.locator('.art-character.inochi-ready').waitFor();await fresh.waitForTimeout(350);await fresh.screenshot({path:out+'/fresh-install.png'})
 assert.equal(await fresh.locator('canvas').getAttribute('data-model-version'),'v4')
 assert.equal(oldPortraitRequested,false,'loading must not fetch the old portrait')
 assert.equal(await fresh.locator('.source-character-poster').evaluate(p=>getComputedStyle(p).visibility),'hidden')
 assert.equal(await fresh.locator('canvas').evaluate(c=>getComputedStyle(c).visibility),'visible')
 const handover=await fresh.evaluate(()=>{
  const p=document.querySelector('.source-character-poster').getBoundingClientRect(),c=document.querySelector('canvas'),b=c.getBoundingClientRect(),d=c.dataset
  const scale=Number(d.inochi2dCameraScale)/Number(d.inochi2dDevicePixelRatio)
  return{posterScale:p.width/1122,liveScale:scale,posterTop:p.y,liveTop:b.y+b.height/2+(Number(d.inochi2dCameraY)-701)*scale}
 })
 assert.ok(Math.abs(handover.posterScale-handover.liveScale)<.001)
 assert.ok(Math.abs(handover.posterTop-handover.liveTop)<1,'poster and live rig must use the same frame')

 await fresh.close()
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message))
 let modelRequested=false;page.on('request',r=>{if(r.url().includes('/inochi2d/v4/MewNook.inx'))modelRequested=true})
 await page.addInitScript(()=>{
  if(!localStorage.getItem('mewnook:settings'))localStorage.setItem('mewnook:settings',JSON.stringify({inochiTestMode:false,inochiModel:'v3',scene:'day',city:'',nickname:'keep-me'}))
 })
 await page.goto('http://127.0.0.1:4173/');await page.locator('canvas[data-model-revision="source-art-20261020"]').waitFor({timeout:60000});await page.locator('.art-character.inochi-ready').waitFor();assert.ok(modelRequested)
 const migrated=await page.evaluate(()=>JSON.parse(localStorage.getItem('mewnook:settings')));assert.equal(migrated.nickname,'keep-me');assert.equal(migrated.inochiTestMode,true);assert.equal(migrated.inochiModel,'v4');assert.equal(migrated.inochiModelRevision,1)
 await page.waitForTimeout(350);await page.screenshot({path:out+'/day.png'})
 await page.locator('.art-character').click({position:{x:160,y:170}})
 await page.waitForFunction(()=>Math.abs(Number(document.querySelector('canvas').dataset.headRoll))>.3)
 assert.equal(await page.locator('canvas').getAttribute('data-head-pat'),'active');await page.screenshot({path:out+'/head-pat.png'})
 await page.waitForFunction(()=>document.querySelector('canvas').dataset.headPat==='idle');assert.equal(Number(await page.locator('canvas').getAttribute('data-head-roll')),0)
 await page.waitForFunction(()=>document.querySelector('canvas').dataset.activity!=='chat')
 await page.getByRole('button',{name:'与猫娘聊天',exact:true}).click();await page.getByRole('textbox',{name:'和猫娘说话',exact:true}).fill('你好');await page.getByRole('button',{name:'发送消息',exact:true}).click()
 await page.waitForFunction(()=>Number(document.querySelector('canvas').dataset.mouthOpen)>.3);await page.screenshot({path:out+'/chat.png'})
 await page.waitForFunction(()=>document.querySelector('canvas').dataset.activity==='idle'&&Number(document.querySelector('canvas').dataset.mouthOpen)<.015)
 // Persisted opt-out and re-enable must work after the one-time upgrade.
 await page.getByRole('button',{name:'设置',exact:true}).click();const toggle=page.locator('.inochi-test-settings input[type=checkbox]');await toggle.uncheck();await page.reload();assert.equal(await page.locator('canvas.inochi-demo-canvas').count(),0)
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.locator('.inochi-test-settings input[type=checkbox]').check();await page.locator('canvas[data-model-revision="source-art-20261020"]').waitFor({timeout:60000})
 await page.getByRole('button',{name:'关闭面板',exact:true}).click()
 for(const scene of['rain','sunset','night']){
  await page.evaluate(scene=>{const s=JSON.parse(localStorage.getItem('mewnook:settings'));localStorage.setItem('mewnook:settings',JSON.stringify({...s,scene}))},scene)
  await page.reload();await page.locator('.art-character.inochi-ready').waitFor({timeout:60000});if(scene==='night'){await page.waitForFunction(()=>Number(document.querySelector('canvas').dataset.eyeClosure)>.65);assert.ok(Number(await page.locator('canvas').getAttribute('data-mouth-open'))<.015)}
  await page.waitForTimeout(350);await page.screenshot({path:out+'/'+scene+'.png'})
 }
 await page.setViewportSize({width:390,height:844});await page.waitForTimeout(350);const mobileBounds=await page.locator('canvas').boundingBox();console.log('MOBILE BOUNDS',JSON.stringify(mobileBounds));await page.screenshot({path:out+'/mobile.png'});assert.ok(mobileBounds.x>=-1&&mobileBounds.x+mobileBounds.width<=391,'source character canvas must fit mobile viewport')
 // Check composition in source coordinates, including the actual foreground
 // alpha edge. A ready canvas alone missed the former full-body/stool framing.
 const framing=[]
 for(const [width,height,deviceScaleFactor,scene]of[[2048,1074,1,'day'],[2048,1074,1.25,'day'],[2560,1080,2,'day'],[390,844,2,'day'],[1440,1000,1,'rain'],[1440,1000,1,'sunset'],[1440,1000,1,'night']]){
  const framed=await browser.newPage({viewport:{width,height},deviceScaleFactor})
  await framed.addInitScript(scene=>localStorage.setItem('mewnook:settings',JSON.stringify({scene,city:''})),scene)
  await framed.goto('http://127.0.0.1:4173/');await framed.locator('.art-character.inochi-ready').waitFor({timeout:60000});await framed.waitForTimeout(350)
  const geometry=await framed.evaluate(()=>{
   const canvas=document.querySelector('canvas'),b=canvas.getBoundingClientRect(),d=canvas.dataset
   const scale=Number(d.inochi2dCameraScale)/Number(d.inochi2dDevicePixelRatio),cy=Number(d.inochi2dCameraY)
   const point=(x,y)=>({x:b.x+b.width/2+(x-561)*scale,y:b.y+b.height/2+(y-701+cy)*scale})
   const image=document.querySelector('.art-foreground'),r=image.getBoundingClientRect(),probe=document.createElement('canvas');probe.width=image.naturalWidth;probe.height=image.naturalHeight
   const ctx=probe.getContext('2d');ctx.drawImage(image,0,0);const pixels=ctx.getImageData(0,0,probe.width,probe.height).data
   const column=Math.max(0,Math.min(probe.width-1,Math.round((point(600,1000).x-r.x)/r.width*probe.width)))
   let edge=0;while(edge<probe.height&&pixels[(edge*probe.width+column)*4+3]<240)edge++
   const timer=document.querySelector('.scene-focus-chip').getBoundingClientRect()
   return{ear:point(670,10),earRight:point(700,100),hands:point(600,830),seat:point(600,1000),faceWidth:346*scale,desk:r.y+edge/probe.height*r.height,timer:{left:timer.left,bottom:timer.bottom},scale}
  })
  assert.ok(geometry.ear.y>=60&&geometry.ear.y<height*.32,'ears must remain visible below the top bar')
  assert.ok(geometry.faceWidth>(width<=680?width*.4:height*.2),'room portrait must stay close to the desk')
  assert.ok(geometry.seat.y>=geometry.desk,'the model stool must be occluded by the desk')
  assert.ok(Math.abs(geometry.hands.y-geometry.desk)<height*.14,'hands must sit near the desk edge')
  assert.ok(width<=680?geometry.ear.y>geometry.timer.bottom:geometry.earRight.x<geometry.timer.left,'timer must not cover the ears')
  await framed.screenshot({path:out+`/framing-${scene}-${width}-${deviceScaleFactor}.png`});framing.push({scene,width,height,deviceScaleFactor,...geometry})
  if(width===2560){
   const before=await framed.locator('canvas').getAttribute('data-inochi2d-camera-scale')
   await framed.setViewportSize({width,height:900})
   await framed.waitForFunction(before=>document.querySelector('canvas').dataset.inochi2dCameraScale!==before,before)
  }
  await framed.close()
 }
 assert.ok(Math.abs(framing[0].scale-framing[1].scale)<.001,'DPR must not change the CSS size of the model')
 await writeFile(out+'/framing.json',JSON.stringify(framing,null,2))
 // A source-model download failure must keep the legacy model's old frame.
 const legacy=await browser.newPage({viewport:{width:1440,height:1000}})
 await legacy.route('**/inochi2d/v4/MewNook.inx*',route=>route.abort());await legacy.goto('http://127.0.0.1:4173/')
 await legacy.locator('canvas[data-model-version="v3"]').waitFor({timeout:60000})
 const legacyFrame=await legacy.locator('canvas').evaluate(c=>({scale:Number(c.dataset.inochi2dCameraScale),width:c.getBoundingClientRect().width/c.closest('.art-stage').getBoundingClientRect().width}))
 assert.equal(legacyFrame.scale,.32);assert.ok(Math.abs(legacyFrame.width-.377)<.001);await legacy.close()
 // Blocking both dynamic fallbacks must expose the original PNG instead of an empty room.
 const fallback=await browser.newPage();await fallback.route('**/*.inx*',route=>route.abort());await fallback.goto('http://127.0.0.1:4173/');await fallback.waitForFunction(()=>document.querySelector('canvas')?.dataset.modelState==='error');assert.equal(await fallback.locator('.art-character.inochi-ready').count(),0);assert.equal(await fallback.locator('.source-character-poster').evaluate(p=>getComputedStyle(p).visibility),'visible');assert.equal(await fallback.locator('.art-character img').evaluate(p=>getComputedStyle(p).visibility),'hidden');await fallback.close()
 assert.deepEqual(errors,[]);report.push({freshDefault:'v4 source art',loadingPoster:true,noOldPortraitRequest:!oldPortraitRequested,handover,legacyMigration:true,headPat:true,chatAndReset:true,nightEyelids:true,optOutPersists:true,pngFallback:true,productionModelRequested:modelRequested,framing,errors});await writeFile(out+'/report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report))
}finally{await browser.close()}
