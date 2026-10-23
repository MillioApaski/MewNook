// Conservative local cues from the newly delivered assistant text only.
export function chatExpression(text){
 const line=String(text??'').slice(-1200)
 if(!line.trim())return {kind:'neutral',strength:0}
 if(/别担心|没关系|慢慢来|辛苦|陪着|难过|抱抱|休息一下/.test(line))return {kind:'caring',strength:.65}
 if(/太棒|真棒|做到了|完成了|恭喜|开心|好耶|太好了|喜欢/.test(line))return {kind:'happy',strength:.7}
 if(/[?？]|好奇|要不要|想不想/.test(line))return {kind:'curious',strength:.5}
 return {kind:'calm',strength:.35}
}
export function expressionPose(expression){
 const poses={neutral:{},happy:{brow:-.4,earLeft:.2,earRight:-.16,headRoll:.12},caring:{brow:.32,headRoll:-.12,sleepy:.12},curious:{brow:-.5,earLeft:.24,earRight:-.2,headY:.16},calm:{brow:.08}}
 const kind=Object.hasOwn(poses,expression?.kind)?expression.kind:'neutral'
 const strength=Number.isFinite(expression?.strength)?Math.max(0,Math.min(1,expression.strength)):0
 return Object.fromEntries(Object.entries(poses[kind]).map(([key,value])=>[key,value*strength]))
}
