import assert from'node:assert/strict'
import{chromium}from'playwright-core'
import{mkdir,writeFile}from'node:fs/promises'
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader','--use-angle=swiftshader','--enable-webgl']})
const out=process.env.ROOM_CHECK_OUT||'/tmp/mewnook-source-room';await mkdir(out,{recursive:true});const report=[]
try{
 const fresh=await browser.newPage({viewport:{width:1440,height:1000}})
 const errors=[];fresh.on('pageerror',e=>errors.push(e.message))
 await fresh.goto('http://127.0.0.1:4173/')
 await fresh.locator('canvas[data-model-revision="source-art-20261020"]').waitFor({timeout:60000})
 await fresh.locator('.art-character.inochi-ready').waitFor();await fresh.waitForTimeout(350);await fresh.screenshot({path:out+'/fresh-install.png'})
 assert.equal(await fresh.locator('canvas').getAttribute('data-model-version'),'v4')
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
 // Blocking both dynamic fallbacks must expose the original PNG instead of an empty room.
 const fallback=await browser.newPage();await fallback.route('**/*.inx*',route=>route.abort());await fallback.goto('http://127.0.0.1:4173/');await fallback.waitForFunction(()=>document.querySelector('canvas')?.dataset.modelState==='error');assert.equal(await fallback.locator('.art-character.inochi-ready').count(),0);await fallback.close()
 assert.deepEqual(errors,[]);report.push({freshDefault:'v4 source art',legacyMigration:true,headPat:true,chatAndReset:true,nightEyelids:true,optOutPersists:true,pngFallback:true,productionModelRequested:modelRequested,errors});await writeFile(out+'/report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report))
}finally{await browser.close()}
