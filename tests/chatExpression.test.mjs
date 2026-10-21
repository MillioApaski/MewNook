import {test} from 'node:test'
import assert from 'node:assert/strict'
import {chatExpression,expressionPose} from '../public/inochi2d-test/chatExpression.js'
import {createActionMixer,sampleAction,sourceArtParameters} from '../public/inochi2d-test/actions.js'

test('new lines map conservatively to original-art expressions',()=>{
 for(const [line,kind] of [['太好了，任务完成了！','happy'],['别担心，慢慢来，我陪着你','caring'],['要不要喝点水？','curious'],['今天一起专注吧','calm'],['','neutral']])assert.equal(chatExpression(line).kind,kind)
 assert.equal(chatExpression('不开心也没关系，慢慢来').kind,'caring')
})
test('expression types and intensity are restricted; no extra mouth or eyelid owner',()=>{
 assert.deepEqual(expressionPose({kind:'untrusted',strength:100}),{})
 for(const value of Object.values(expressionPose({kind:'happy',strength:Infinity})))assert.equal(Math.abs(value),0)
 for(const kind of ['happy','caring','curious','calm']){
  const pose=expressionPose({kind,strength:100})
  assert.ok(!('mouth' in pose)&&!('blink' in pose))
  for(const value of Object.values(pose))assert.ok(Number.isFinite(value)&&Math.abs(value)<=.5)
 }
})
test('expression release after text ends clears every original-art channel',()=>{
 const mix=createActionMixer()
 mix({...sampleAction('none',0),...expressionPose(chatExpression('太好了'))},0)
 let state
 for(let t=70;t<=2100;t+=70)state=mix(sampleAction('none',0),t)
 for(const value of Object.values(sourceArtParameters(state)))assert.equal(Math.abs(value),0)
})
