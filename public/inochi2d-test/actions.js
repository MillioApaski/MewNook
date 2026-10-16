// Timeline values shared by the standalone page and deterministic frame tests.
export const actionDuration={idle:360,tap:2000,chat:5000,sleep:5000}
export function sampleAction(action,elapsed){
 const t=Math.max(0,elapsed),done=t>=(actionDuration[action]||0)
 const result={blink:0,mouth:0,sleepy:0,earLeft:0,earRight:0,done}
 if(done)return result
 if(action==='idle')result.blink=t<120?t/120:t<180?1:1-(t-180)/180
 if(action==='tap'){
   const envelope=(.25+.75*Math.exp(-t/1100))*Math.min(1,(2000-t)/300)
   result.earLeft=Math.sin(t/170+.8)*envelope
   result.earRight=-Math.sin(t/170+1.25)*envelope
   result.blink=t<400?Math.sin(Math.PI*t/400)*.75:0
 }
 if(action==='chat')result.mouth=(.5+.5*Math.sin(t/115))*.85
 if(action==='sleep')result.sleepy=Math.min(1,t/450,(5000-t)/450)*.95
 return result
}
