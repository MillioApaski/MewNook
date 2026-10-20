import test from'node:test'
import assert from'node:assert/strict'
import {compileParameterOpacities,evaluateParameterOpacities}from'../public/inochi2d-test/runtime/parameter_opacity.js'
const model={meta:{sourceArtOpacityBindings:true},nodes:{uuid:1,name:'root',children:[{uuid:2,name:'slot'}]},param:[{name:'blink',min:[0,0],max:[1,1],defaults:[0,0],axis_points:[[0,.5,1],[0,1]],bindings:[{node:2,param_name:'opacity',values:[[0,0],[0,0],[1,1]]}]}]}
test('native opacity fallback follows parameter knots and defaults',()=>{
 const b=compileParameterOpacities(model)
 for(const[value,want]of[[0,0],[.5,0],[.75,.5],[1,1],[2,1],[-1,0]])assert.equal(evaluateParameterOpacities(b,new Map([['blink',[value,0]]])).get('slot'),want)
 assert.equal(evaluateParameterOpacities(b,new Map()).get('slot'),0)
 assert.deepEqual(compileParameterOpacities({...model,meta:{}}),[])
})
test('opacity lookup follows nested head hierarchy',()=>{
 assert.equal(compileParameterOpacities({...model,nodes:{uuid:4,name:'head',children:[model.nodes]}})[0].nodeName,'slot')
})
