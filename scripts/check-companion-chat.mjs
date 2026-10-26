import assert from 'node:assert/strict'
import {chromium} from 'playwright-core'

const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', headless:true,
  args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader','--use-angle=swiftshader','--enable-webgl']
})
try {
  for (const [phase,running,scene,base] of [
    ['focus',false,'day','idle'], ['focus',true,'day','focus'],
    ['short',false,'day','rest'], ['focus',false,'night','sleepy']
  ]) {
    const page = await browser.newPage()
    await page.addInitScript(({phase,running,scene})=>{
      localStorage.setItem('mewnook:settings',JSON.stringify({inochiTestMode:true,inochiModel:'v4',scene}))
      localStorage.setItem('mewnook:timer',JSON.stringify({phase,running,remaining:1500,endsAt:running?Date.now()+1500000:null}))
    },{phase,running,scene})
    await page.goto('http://127.0.0.1:4173/')
    await page.locator('.art-character.inochi-ready').waitFor({timeout:60000})
    const canvas=page.locator('canvas.inochi-demo-canvas')
    const expectActivity=async expected=>{
      await page.waitForFunction(value=>document.querySelector('canvas.inochi-demo-canvas')?.dataset.activity===value,expected)
      assert.equal(await canvas.getAttribute('data-activity'),expected)
    }
    await page.getByRole('button',{name:'与猫娘聊天',exact:true}).click()
    await expectActivity(base)
    await page.getByRole('textbox',{name:'和猫娘说话',exact:true}).fill('你好')
    await page.getByRole('button',{name:'发送消息',exact:true}).click()
    await expectActivity('chat')
    await expectActivity(base)
    assert.ok(await page.locator('.vn-dialogue.expanded').count(),'chat stays open after mouth stops')
    await page.close()
    console.log('Companion reply/history state passed:',base)
  }
  const page=await browser.newPage()
  await page.addInitScript(()=>localStorage.setItem('mewnook:settings',JSON.stringify({
    inochiTestMode:true,inochiModel:'v4',scene:'day',aiUrl:'https://companion.invalid/v1',aiModel:'test'
  })))
  let release
  const pending=new Promise(resolve=>{release=resolve})
  await page.route('https://companion.invalid/**',async route=>{
    await pending
    await route.fulfill({contentType:'application/json',body:JSON.stringify({choices:[{message:{content:'迟到的回复'}}]})}).catch(()=>{})
  })
  await page.goto('http://127.0.0.1:4173/')
  await page.getByRole('button',{name:'与猫娘聊天',exact:true}).click()
  await page.getByRole('textbox',{name:'和猫娘说话',exact:true}).fill('测试等待与取消')
  await page.getByRole('button',{name:'发送消息',exact:true}).click()
  await page.getByRole('button',{name:'停止生成',exact:true}).waitFor()
  assert.equal(await page.locator('canvas.inochi-demo-canvas').getAttribute('data-activity'),'idle','waiting does not open mouth')
  await page.getByRole('button',{name:'停止生成',exact:true}).click()
  release()
  await page.getByText('已停止生成，可以重试。',{exact:true}).waitFor()
  assert.equal(await page.locator('canvas.inochi-demo-canvas').getAttribute('data-activity'),'idle')
  assert.equal(await page.getByText('迟到的回复',{exact:true}).count(),0)
  console.log('Companion pending request / cancel passed')
} finally {
  await browser.close()
}
