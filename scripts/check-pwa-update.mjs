import assert from'node:assert/strict'
import{readFile,writeFile,mkdir}from'node:fs/promises'
import{spawn}from'node:child_process'
import{chromium}from'playwright-core'
const original=await readFile('dist/sw.js','utf8'),port=process.env.PWA_CHECK_PORT||'4173'
let browser,server
try{
 if(process.env.PWA_SELF_HOST==='1'){
  server=spawn(process.execPath,['node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port',port],{stdio:'ignore'})
  await new Promise(r=>setTimeout(r,600))
 }
 browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader','--enable-webgl']})
 const p=await browser.newPage(),errors=[];let navigations=0
 p.on('pageerror',e=>errors.push(e.message));p.on('framenavigated',f=>{if(f===p.mainFrame())navigations++})
 await p.goto('http://127.0.0.1:'+port+'/')
 await p.waitForFunction(()=>!!navigator.serviceWorker.controller,{},{timeout:60000})
 await p.waitForTimeout(250);assert.equal(navigations,1,'first installation must not reload the page')
 // A byte-level worker update exercises an existing controlled tab, not just
 // a fresh context that can never reproduce a stale already-open preview.
 await writeFile('dist/sw.js',original+'\n// update-regression-'+Date.now()+'\n')
 await Promise.all([
  p.waitForEvent('framenavigated',{predicate:f=>f===p.mainFrame(),timeout:45000}),
  p.evaluate(async()=>{const r=await navigator.serviceWorker.getRegistration();await r.update()})
 ])
 await p.locator('[data-composite-revision="desk-layer-v1"]').waitFor()
 await p.waitForTimeout(500);assert.equal(navigations,2,'an update must reload once without a loop');assert.deepEqual(errors,[])
 const report={firstInstallReloads:0,updateReloads:1,errors};await mkdir('/tmp/mewnook-source-room',{recursive:true});await writeFile('/tmp/mewnook-source-room/pwa-update.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report))
}finally{
 await browser?.close();server?.kill();await writeFile('dist/sw.js',original)
}
