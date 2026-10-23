import assert from 'node:assert/strict'
import {mkdir,writeFile,readFile} from 'node:fs/promises'
import {createServer} from 'node:http'
import {chromium} from 'playwright-core'
const origin=process.env.ROOM_TEST_ORIGIN||'http://127.0.0.1:4173'
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader','--enable-webgl']})
const report={environment:'Headless Chromium / software WebGL, local Vite server; timings are not real-phone benchmarks',expressions:[],errors:[]}
const streamServer=createServer((req,res)=>{
 res.setHeader('Access-Control-Allow-Origin','*');res.setHeader('Access-Control-Allow-Headers','*')
 if(req.method==='OPTIONS'){res.writeHead(204);res.end();return}
 res.writeHead(200,{'Content-Type':'text/event-stream'})
 res.write('data: '+JSON.stringify({choices:[{delta:{content:'太好了，今天的任务完成了！'}}]})+'\n\n')
})
await new Promise(resolve=>streamServer.listen(0,'127.0.0.1',resolve))
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:2})
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message))
 await page.addInitScript(()=>{
  if(!localStorage.getItem('mewnook:settings'))localStorage.setItem('mewnook:settings',JSON.stringify({scene:'day',city:'',aiUrl:'https://expression.invalid/v1',aiModel:'test',aiStreaming:false}))
 })
 let answer='太好了，任务完成了！',failure=false
 await page.route('https://expression.invalid/**',route=>route.fulfill({status:failure?500:200,contentType:'application/json',body:JSON.stringify({choices:[{message:{content:answer}}]})}))
 await page.goto(origin);await page.locator('canvas[data-model-state=ready]').waitFor({timeout:60000})
 report.cold=await page.locator('canvas').evaluate(c=>({readyMs:Number(c.dataset.modelReadyMs),frames:Number(c.dataset.renderedFrames),maxFps:c.dataset.renderMaxFps,resources:performance.getEntriesByType('resource').filter(r=>/inochi/.test(r.name)).map(r=>({path:new URL(r.name).pathname,duration:r.duration,bytes:r.encodedBodySize}))}))
 await page.getByRole('button',{name:'与猫娘聊天',exact:true}).click()
 for(const [text,kind,sign] of [['太好了，今天的任务终于完成了！可以放松一下，喝口水，再一起整理接下来的安排。','happy',-1],['别担心，慢慢来。','caring',1],['要不要喝点水？','curious',-1]]){
  answer=text
  await page.getByRole('textbox',{name:'和猫娘说话',exact:true}).fill('测试')
  await page.getByRole('button',{name:'发送消息',exact:true}).click()
  await page.waitForFunction(kind=>document.querySelector('canvas')?.dataset.chatExpression===kind,kind)
  await page.waitForFunction(sign=>sign*Number(document.querySelector('canvas').dataset.brow)>.04,sign)
  report.expressions.push({kind,brow:Number(await page.locator('canvas').getAttribute('data-brow'))})
  if(kind==='happy'){
   await page.waitForFunction(()=>Number(document.querySelector('canvas').dataset.mouthOpen)>.3)
   // Pointer hit testing is covered by the room suite. Dispatch this click
   // while the reply is active, without an actionability wait using its time.
   const before=await page.locator('.source-head-target').evaluate(button=>{
    const d=document.querySelector('canvas').dataset,state={activity:d.activity,kind:d.chatExpression,mouth:Number(d.mouthOpen)}
    button.click();return state
   })
   assert.equal(before.activity,'chat');assert.equal(before.kind,'happy');assert.ok(before.mouth>.3)
   await page.waitForFunction(()=>Number(document.querySelector('canvas').dataset.headPatWeight)>.6,{},{timeout:5000})
   assert.ok(Number(await page.locator('canvas').getAttribute('data-mouth-open'))>.3)
   assert.equal(await page.locator('canvas').getAttribute('data-activity'),'chat')
   assert.equal(await page.locator('canvas').getAttribute('data-chat-expression'),'happy')
   report.headPatDuringSpeech=true
  }
  await page.waitForFunction(()=>document.querySelector('canvas').dataset.chatExpression==='neutral'&&Number(document.querySelector('canvas').dataset.mouthOpen)<.015&&Math.abs(Number(document.querySelector('canvas').dataset.brow))<.002)
 }
 // Reopening history must not replay the last expression.
 await page.getByRole('button',{name:'与猫娘聊天',exact:true}).click()
 await page.getByRole('button',{name:'与猫娘聊天',exact:true}).click()
 assert.equal(await page.locator('canvas').getAttribute('data-chat-expression'),'neutral')
 failure=true
 await page.getByRole('textbox',{name:'和猫娘说话',exact:true}).fill('测试错误')
 await page.getByRole('button',{name:'发送消息',exact:true}).click()
 await page.waitForTimeout(350)
 assert.equal(await page.locator('canvas').getAttribute('data-chat-expression'),'neutral')
 // Streaming content changes expression; cancel must release it and ignore stale text.
 await page.evaluate(port=>{
  const settings=JSON.parse(localStorage.getItem('mewnook:settings'))
  localStorage.setItem('mewnook:settings',JSON.stringify({...settings,aiUrl:'http://127.0.0.1:'+port+'/v1',aiStreaming:true}))
 },streamServer.address().port)
 await page.reload();await page.locator('canvas[data-model-state=ready]').waitFor({timeout:60000})
 await page.getByRole('button',{name:'与猫娘聊天',exact:true}).click()
 await page.getByRole('textbox',{name:'和猫娘说话',exact:true}).fill('流式取消')
 await page.getByRole('button',{name:'发送消息',exact:true}).click()
 await page.waitForFunction(()=>document.querySelector('canvas').dataset.chatExpression==='happy')
 await page.getByRole('button',{name:'停止生成',exact:true}).click()
 await page.waitForFunction(()=>document.querySelector('canvas').dataset.chatExpression==='neutral'&&Number(document.querySelector('canvas').dataset.mouthOpen)<.015)
 report.streamingCancel=true
 // On-demand cache: initial install excludes the unvisited test page and other scenes.
 await page.waitForFunction(()=>!!navigator.serviceWorker.controller)
 const cacheKeys=await page.evaluate(async()=>{const keys=[];for(const name of await caches.keys()){for(const request of await(await caches.open(name)).keys())keys.push(new URL(request.url).pathname)}return keys})
 assert.ok(!cacheKeys.includes('/inochi2d-test/smoke.html'))
 assert.ok(!cacheKeys.includes('/assets/rooms/night/background.webp'))
 await page.reload();await page.locator('canvas[data-model-state=ready]').waitFor({timeout:60000})
 await page.waitForTimeout(500)
 report.warmReadyMs=Number(await page.locator('canvas').getAttribute('data-model-ready-ms'))
 await context.setOffline(true)
 await page.reload();await page.locator('canvas[data-model-state=ready]').waitFor({timeout:60000})
 report.offlineReadyMs=Number(await page.locator('canvas').getAttribute('data-model-ready-ms'))
 report.offlineRepeat=true
 await context.setOffline(false)
 await page.setViewportSize({width:390,height:844});await page.waitForTimeout(250)
 report.mobile=await page.locator('canvas').evaluate(c=>({dpr:Number(c.dataset.inochi2dDevicePixelRatio),maxFps:Number(c.dataset.renderMaxFps),width:c.width,height:c.height}))
 assert.equal(report.mobile.dpr,1);assert.equal(report.mobile.maxFps,30)
 const before=Number(await page.locator('canvas').getAttribute('data-rendered-frames'))
 await page.waitForTimeout(1000)
 report.mobile.framesInSecond=Number(await page.locator('canvas').getAttribute('data-rendered-frames'))-before
 assert.ok(report.mobile.framesInSecond<=34)
 await page.evaluate(()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'hidden'});document.dispatchEvent(new Event('visibilitychange'))})
 assert.equal(await page.locator('canvas').getAttribute('data-render-paused'),'true')
 const paused=await page.locator('canvas').getAttribute('data-rendered-frames')
 await page.waitForTimeout(350);assert.equal(await page.locator('canvas').getAttribute('data-rendered-frames'),paused)
 await page.evaluate(()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'visible'});document.dispatchEvent(new Event('visibilitychange'))})
 await page.waitForFunction(n=>Number(document.querySelector('canvas').dataset.renderedFrames)>Number(n),paused)
 report.backgroundPauseResume=true
 await page.screenshot({path:'/tmp/chat-performance-mobile.png'})
 const sw=await readFile('dist/sw.js','utf8')
 assert.ok(!sw.includes('smoke.html'));assert.ok(!sw.includes('poster.png'))
 assert.deepEqual(report.errors,[])
 await context.close()
 await mkdir('assets/inochi/v4/validation',{recursive:true})
 await writeFile('assets/inochi/v4/validation/chat-performance-report.json',JSON.stringify(report,null,2))
 console.log(JSON.stringify(report))
}finally{streamServer.closeAllConnections();streamServer.close();await browser.close()}
