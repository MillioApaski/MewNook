// Timeline values shared by the standalone page and deterministic frame tests.
export const actionDuration={idle:360,tap:2400,chat:5000,sleep:5000}
export function sampleAction(action,elapsed){
 const t=Math.max(0,elapsed),done=t>=(actionDuration[action]||0)
 const result={blink:0,mouth:0,sleepy:0,earLeft:0,earRight:0,headRoll:0,headY:0,hair:0,brow:0,done}
 if(done)return result
 if(action==='idle')result.blink=t<120?t/120:t<180?1:1-(t-180)/180
 if(action==='tap'){
   const fade=Math.min(1,t/180,(2400-t)/450)
   const envelope=(.25+.75*Math.exp(-t/1100))*fade
   result.earLeft=Math.sin(t/170+.8)*envelope
   result.earRight=-Math.sin(t/170+1.25)*envelope
   result.headRoll=Math.sin(t/430)*.75*fade
   result.headY=Math.sin(Math.PI*Math.min(t/900,1))*.65*fade
   result.hair=Math.sin(t/240+.7)*.55*fade
   result.brow=-.35*fade
   result.blink=t<900?Math.sin(Math.PI*t/900)*.9:0
 }
 if(action==='chat'){
   const envelope=Math.min(1,t/160,(5000-t)/250)
   result.mouth=(.5+.5*Math.sin(t/115))*.85*envelope
   result.brow=-.2*envelope
 }
 if(action==='sleep'){
   const phase=Math.min(1,t/1000,(5000-t)/800)
   result.sleepy=phase*phase*(3-2*phase)*.95
 }
 return result
}
export function sourceArtParameters(state,blink=0,wind=0){
 const drowsy=Math.max(0,Math.min(1,(state.sleepy-.2)/.75))
 const closure=Math.max(blink,state.blink,drowsy)
 return {ParamEyeBlinkLeft:closure,ParamEyeBlinkRight:closure,
  ParamMouthOpen:state.mouth,ParamDrowsyMouth:drowsy*(1-Math.min(1,state.mouth/.2)),ParamHeadRoll:state.headRoll,ParamHeadY:state.headY,
  ParamHeadX:0,ParamBrowLeft:state.brow,ParamBrowRight:state.brow,
  ParamEarLeft:state.earLeft,ParamEarRight:state.earRight,
  ParamHairLeft:wind+state.hair,ParamHairRight:wind*.85-state.hair,
  ParamHairFront:wind*.65+state.hair*.7,ParamSleepy:0,ParamSleepyLeft:0,ParamSleepyRight:0}
}

// Retain the displayed pose across interruptions and activity changes.
// Blink stays direct so a quick closure does not turn into a slow squint.
export function createActionMixer(){
 let pose=null,last=null
 const keys=['mouth','sleepy','earLeft','earRight','headRoll','headY','hair','brow']
 return (target,now)=>{
   if(!pose){pose={...target};last=now;return {...pose}}
   const dt=Math.min(100,Math.max(0,now-last));last=now
   const weight=1-Math.exp(-dt/85)
   for(const key of keys){
     const next=pose[key]+(target[key]-pose[key])*weight
     pose[key]=Math.abs(next-target[key])<.001?target[key]:next
   }
   pose.blink=target.blink;pose.done=target.done
   return {...pose}
 }
}
