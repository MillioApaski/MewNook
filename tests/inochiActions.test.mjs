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
 assert.equal(sampleAction('sleep',1200).sleepy,.95)
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
 const sleepy=sourceArtParameters(sampleAction('sleep',1200),1)
 assert.equal(sleepy.ParamEyeBlinkLeft,1)
 assert.equal(sleepy.ParamMouthOpen,0)
 assert.equal(sleepy.ParamDrowsyMouth,1)
 assert.equal(sleepy.ParamSleepyLeft,0)
 const chat=sourceArtParameters(sampleAction('chat',800))
 assert.equal(chat.ParamEyeBlinkLeft,0)
 assert.equal(chat.ParamHeadRoll,0)
 for(const v of Object.values(sourceArtParameters(sampleAction('none',0))))assert.equal(Math.abs(v),0)
})

test('approved sleepy face closes gently with a dedicated tiny painted mouth; blink and speech retain control',async()=>{
 const {sourceArtParameters}=await import('../public/inochi2d-test/actions.js')
 const state=sampleAction('sleep',1200),face=sourceArtParameters(state)
 assert.equal(face.ParamEyeBlinkLeft,1)
 assert.equal(face.ParamMouthOpen,0)
 assert.equal(face.ParamDrowsyMouth,1)
 assert.ok(face.ParamBrowLeft<.35)
 assert.equal(sourceArtParameters(state,1).ParamEyeBlinkLeft,1)
 assert.equal(sourceArtParameters({...state,mouth:.7}).ParamMouthOpen,.7)
 assert.equal(sourceArtParameters({...state,mouth:.7}).ParamDrowsyMouth,0)
 for(const value of Object.values(sourceArtParameters(sampleAction('sleep',5000))))assert.equal(Math.abs(value),0)
})

test('head pat has an early bow and relaxed closure, then releases back to speech or sleep',async()=>{
 const {sourceArtParameters}=await import('../public/inochi2d-test/actions.js')
 const start=sampleAction('tap',240),hold=sampleAction('tap',450),end=sampleAction('tap',2400)
 assert.ok(start.pat>.8,'touch must produce an early visible bow')
 assert.equal(hold.blink,1)
 assert.equal(end.pat,0)
 const talking=sourceArtParameters({...hold,mouth:.7})
 assert.equal(talking.ParamMouthOpen,.7);assert.equal(talking.ParamDrowsyMouth,0)
 const sleepy=sourceArtParameters({...end,sleepy:.95})
 assert.equal(sleepy.ParamEyeBlinkLeft,1);assert.equal(sleepy.ParamDrowsyMouth,1);assert.equal(sleepy.ParamHeadPat,0)
})
