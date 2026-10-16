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
