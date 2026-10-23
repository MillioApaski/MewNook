import {test} from 'node:test'
import assert from 'node:assert/strict'
import {headHitBox,isHeadHit} from '../public/inochi2d-test/headHitArea.js'

test('source head hits survive phone, desktop, zoom and cropped camera frames',()=>{
  for(const width of [390,920])for(const scale of [.1,.32,.8,1.1])for(const top of [-200,72,180]){
    const f={width,scale,top},b=headHitBox(f)
    const source=(x,y)=>[width/2+(x-561)*scale,top+y*scale]
    for(const p of [[565,212],[565,100],[440,212],[680,212]])assert.equal(isHeadHit(...source(...p),f),true)
    for(const p of [[565,500],[565,850],[100,212],[980,212],[390,65]])assert.equal(isHeadHit(...source(...p),f),false)
    assert.equal(isHeadHit(b.left,b.top,f),false,'ellipse excludes empty corner')
  }
})
test('backing-pixel camera projects to the same CSS head position at each DPR',()=>{
  for(const ratio of [1,1.25,2]){
    const cssScale=.46/ratio,height=750,cameraY=350
    const f={width:650,scale:cssScale,top:height/2+(cameraY-701)*cssScale}
    assert.equal(isHeadHit(650/2+4*cssScale,height/2+(cameraY-701+212)*cssScale,f),true)
    assert.equal(isHeadHit(650/2,height/2+(cameraY-701+850)*cssScale,f),false)
  }
})
