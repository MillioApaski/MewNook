import test from 'node:test'
import assert from 'node:assert/strict'
import {sampleAction,actionDuration} from '../public/inochi2d-test/actions.js'

test('each standalone action finishes and clears all expression parameters',()=>{
 for(const name of Object.keys(actionDuration)){
  const end=sampleAction(name,actionDuration[name])
  assert.equal(end.done,true)
  for(const key of ['blink','mouth','sleepy','earLeft','earRight'])assert.equal(end[key],0)
 }
})
test('blink closes then opens; sleepy does not open a second mouth',()=>{
 assert.equal(sampleAction('idle',120).blink,1)
 assert.ok(sampleAction('idle',270).blink<1)
 assert.equal(sampleAction('sleep',800).sleepy,.95)
 assert.equal(sampleAction('sleep',800).mouth,0)
})
test('touch makes the ears visibly reverse direction instead of holding a tiny offset',()=>{
 const frames=Array.from({length:20},(_,i)=>sampleAction('tap',i*80).earLeft)
 assert.ok(Math.max(...frames)>.7)
 assert.ok(Math.min(...frames)<-.4)
})

test('head pat coordinates head, hair and ears and releases every channel',()=>{
 const mid=sampleAction('tap',650)
 assert.ok(Math.abs(mid.headRoll)>.4)
 assert.ok(Math.abs(mid.hair)>.05)
 assert.ok(mid.blink>0)
 for(const [key,value]of Object.entries(sampleAction('tap',actionDuration.tap)))if(key!=='done')assert.equal(value,0,key)
})
test('changing source expressions assigns a single eyelid and mouth owner',async()=>{
 const{sourceArtParameters}=await import('../public/inochi2d-test/actions.js')
 const sleepy=sourceArtParameters(sampleAction('sleep',900),1)
 assert.equal(sleepy.ParamEyeBlinkLeft,1)
 assert.equal(sleepy.ParamMouthOpen,0)
 assert.equal(sleepy.ParamSleepyLeft,0)
 const chat=sourceArtParameters(sampleAction('chat',800))
 assert.equal(chat.ParamEyeBlinkLeft,0)
 assert.equal(chat.ParamHeadRoll,0)
 for(const v of Object.values(sourceArtParameters(sampleAction('none',0))))assert.equal(Math.abs(v),0)
})
