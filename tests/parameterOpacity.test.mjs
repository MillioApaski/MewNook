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

test('head visibility multiplies active expressions and preserves hidden defaults',()=>{
 const m=structuredClone(model);m.nodes.children.push({uuid:3,name:'hidden',opacity:0});
 m.param.push({name:'focus',min:[0,0],max:[1,1],defaults:[0,0],axis_points:[[0,1],[0,1]],bindings:[2,3].map(node=>({node,param_name:'opacity',opacity_mode:'multiply',values:[[1,1],[0,0]]}))});
 const b=compileParameterOpacities(m);
 for(const [blink,focus,want]of[[0,0,0],[1,0,1],[1,.5,.5],[1,1,0]]){
  const v=evaluateParameterOpacities(b,new Map([['blink',[blink]],['focus',[focus]]]));assert.equal(v.get('slot'),want);assert.equal(v.get('hidden'),0)
 }
})
