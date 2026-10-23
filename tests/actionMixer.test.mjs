import test from 'node:test'
import assert from 'node:assert/strict'
import {createActionMixer,sampleAction,sourceArtParameters} from '../public/inochi2d-test/actions.js'

test('retriggered head pat preserves pose at the interruption and settles to neutral',()=>{
 const mix=createActionMixer(),current=mix(sampleAction('tap',650),1000)
 const restarted=mix(sampleAction('tap',0),1000)
 for(const key of ['headRoll','headY','pat','blink','earLeft','earRight','hair','brow'])assert.equal(restarted[key],current[key])
 let end
 for(let t=1070;t<=3000;t+=70)end=mix(sampleAction('none',0),t)
 for(const [key,value]of Object.entries(sourceArtParameters(end)))assert.equal(Math.abs(value),0,key)
})
test('chat, pat, sleepy and reset stay bounded and return to the current activity',()=>{
 const mix=createActionMixer();mix(sampleAction('chat',800),0)
 let now=0,previous=null
 for(const action of ['tap','sleep','chat','none']){
   for(let elapsed=0;elapsed<2000;elapsed+=33){
     now+=33;const state=mix(sampleAction(action,elapsed),now)
     for(const key of ['mouth','sleepy','blink','earLeft','earRight','headRoll','headY','pat','hair','brow']){
       assert.ok(Number.isFinite(state[key])&&Math.abs(state[key])<=1)
       if(previous)assert.ok(Math.abs(state[key]-previous[key])<.5,key)
     }
     previous=state
   }
 }
 for(const value of Object.values(sourceArtParameters(previous)))assert.equal(Math.abs(value),0)
})
test('blink is immediate while sleepy brow transitions smoothly, including background resume',()=>{
 const mix=createActionMixer();mix(sampleAction('sleep',900),0)
 const next=mix({...sampleAction('none',0),blink:1},70)
 assert.equal(next.blink,1);assert.ok(next.sleepy>0&&next.sleepy<.95)
 const resumed=mix(sampleAction('none',0),60000)
 assert.ok(resumed.sleepy>0,'background gap must not snap pose')
})

test('repeated touch blends from the displayed pose without reopening closed eyes',()=>{
 const mix=createActionMixer();mix(sampleAction('tap',450),1000,1)
 const held=mix(sampleAction('tap',0),1000,2)
 assert.equal(held.blink,1)
 const early=mix(sampleAction('tap',80),1080,2)
 assert.ok(early.blink>.8)
 assert.ok(Math.abs(early.headRoll-held.headRoll)<.15)
 const settled=mix(sampleAction('tap',400),1400,2)
 assert.equal(settled.blink,1)
})
