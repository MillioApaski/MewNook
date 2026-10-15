import {useEffect, useRef} from 'react'

/**
 * Inochi2D WebGL2 runtime. The browser JS/WASM is third-party licensed;
 * MewNook-test.inx is our own minimal, procedurally rigged catgirl model,
 * generated from existing artwork. An older Aka test model remains attributed.
 */
interface Controller {
  mount(canvas: HTMLCanvasElement): Promise<void> | void
  loadModel(url:string): Promise<void>
  getAnimationNames?(): string[]
  playAnimation?(name:string, options?:{loop?:boolean;restart?:boolean;kind?:'idle'|'reaction'|'manual'}):Promise<void>|void
  applyInteractionImpulse?(x:number,y:number):Promise<void>|void
  setExpressionPreset?(name:string):Promise<void>|void
  setParameter?(id:string,value:number):Promise<void>|void
  setCameraTransform(x:number,y:number,scale:number):Promise<void>|void
  resize(width:number,height:number,ratio:number):Promise<void>|void
  unmount():Promise<void>|void
}
type Bridge = {createInochi2DController(opts:{wasmUrl:string;debug?:boolean}):Promise<Controller>}
export type InochiTestStatus = 'off'|'loading'|'ready'|'error'

interface Props {
  active: boolean
  scale: number
  activity: 'focus'|'rest'|'idle'|'chat'|'sleepy'
  touches: number
  onStatus: (status:InochiTestStatus,error?:string)=>void
}

export function InochiTestCharacter({active,scale,activity,touches,onStatus}:Props){
  const canvasRef=useRef<HTMLCanvasElement|null>(null)
  const controllerRef=useRef<Controller|null>(null)
  const namesRef=useRef<string[]>([])
  const firstTouchRef=useRef(touches)
  const tapUntilRef=useRef(0)
  const controllerReadyRef=useRef(false)
  const manualBlinkUntil=useRef(0)
  const smoothed=useRef({smile:0,sleepy:0,mouth:0})

  useEffect(()=>{
    if(!active)return
    const canvas=canvasRef.current
    if(!canvas)return
    let disposed=false,controller:Controller|null=null,observer:ResizeObserver|null=null
    let resizeHandler:(()=>void)|null=null
    onStatus('loading')
    void (async()=>{
      if(!canvas.getContext('webgl2'))throw new Error('浏览器缺少 WebGL2 支持')
      const moduleUrl='/inochi2d-test/runtime/inochi_bridge.js'
      const bridge=await import(/* @vite-ignore */ moduleUrl) as Bridge
      if(disposed)return
      controller=await bridge.createInochi2DController({wasmUrl:'/inochi2d-test/runtime/inochi2d_bg.wasm'})
      if(disposed){await controller.unmount();return}
      controllerRef.current=controller
      await controller.mount(canvas)
      const resize=()=>{
        if(!canvas.isConnected||!controller)return
        const bounds=canvas.getBoundingClientRect()
        const ratio=Math.min(window.devicePixelRatio||1,1.25)
        void controller.resize(Math.max(1,bounds.width),Math.max(1,bounds.height),ratio)
      }
      resize()
      if(typeof ResizeObserver!=='undefined'){
        observer=new ResizeObserver(resize)
        observer.observe(canvas)
      }else{resizeHandler=resize;window.addEventListener('resize',resizeHandler)}
      await controller.setCameraTransform(0,120,scale)
      if(disposed)return
      await controller.loadModel('/inochi2d-test/models/MewNook-v3.inx')
      if(disposed)return
      namesRef.current=controller.getAnimationNames?.()||[]
      if(namesRef.current.includes('Energetic Sway'))
        await controller.playAnimation?.('Energetic Sway',{loop:true,kind:'idle'})
      // Expression parameters are owned by the MewNook v2 rig, not by
      // third-party preset names from the older Aka test runtime.
      controllerReadyRef.current=true
      onStatus('ready')
    })().catch(e=>{
      if(!disposed)onStatus('error',e instanceof Error?e.message:String(e))
    })
    return()=>{
      disposed=true
      controllerReadyRef.current=false
      observer?.disconnect()
      if(resizeHandler)window.removeEventListener('resize',resizeHandler)
      if(controllerRef.current===controller)controllerRef.current=null
      if(controller)void Promise.resolve(controller.unmount()).catch(()=>{})
      onStatus('off')
    }
    // The renderer mounts only once; scale and activity use separate effects.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[active,onStatus])

  useEffect(()=>{
    const c=controllerRef.current
    if(c)void c.setCameraTransform(0,120,Math.min(.9,Math.max(.1,scale)))
  },[scale])

  useEffect(()=>{
    const c=controllerRef.current
    if(!c)return
    // Changed activity is applied on the next 70 ms animation tick.
    void c.setParameter?.('ParamSmile',activity==='rest'||activity==='chat'?0.75:0)
  },[activity])

  useEffect(()=>{
    if(touches===firstTouchRef.current)return
    firstTouchRef.current=touches
    const c=controllerRef.current
    if(!c)return
    tapUntilRef.current=Date.now()+650
    manualBlinkUntil.current=Date.now()+230
    void c.applyInteractionImpulse?.(5,-3)
    const names=namesRef.current
    if(names.includes('Yatta Celebration'))
      void c.playAnimation?.('Yatta Celebration',{restart:true,kind:'reaction'})
  },[touches])

  useEffect(()=>{
    if(!active)return
    const clock=window.setInterval(()=>{
      const c=controllerRef.current
      if(!c || !controllerReadyRef.current)return
      if(document.visibilityState==='hidden')return
      const current=Date.now()
      const t=current/1000
      const resting=activity==='rest',focused=activity==='focus'
      const sleepy=activity==='sleepy',talking=activity==='chat'
      const interval=sleepy?6.2:focused?5.2:3.9
      const phase=t%interval
      const blink=phase<0.18 ? Math.sin(Math.PI*phase/0.18) : 0
      const blinkValue=current<manualBlinkUntil.current?1:blink
      const touched=current<tapUntilRef.current
      const state=smoothed.current
      state.smile+=((resting||talking?0.65:focused?0.10:0.22)-state.smile)*0.12
      state.sleepy+=((sleepy?0.85:focused?0.16:0)-state.sleepy)*0.12
      state.mouth+=((talking?Math.abs(Math.sin(t*8)):0)-state.mouth)*0.38
      const set=(name:string,val:number)=>void c.setParameter?.(name,val)
      set('ParamEyeBlinkLeft',blinkValue)
      set('ParamEyeBlinkRight',blinkValue)
      set('ParamBreath',Math.sin(t*(sleepy?1.25:2.0))*(focused?.42:.65))
      set('ParamBodyY',Math.sin(t*1.0)*.16)
      set('ParamBodyZ',Math.sin(t*.7)*.12)
      set('ParamHeadX',focused?-.3:Math.sin(t*.42)*.18)
      set('ParamHeadY',focused?.33:sleepy?.17:Math.sin(t*.34)*.13)
      set('ParamTailSwing',Math.sin(t*(sleepy?.65:1.3))*(focused?.35:.28))
      set('ParamTailDeform',Math.sin(t*(sleepy?.72:1.18))*(focused?.22:.55))
      set('ParamHairLeft',Math.sin(t*.96)*.38)
      set('ParamHairRight',Math.sin(t*.88+.7)*.35)
      set('ParamHairFront',Math.sin(t*1.11+.35)*.28)
      set('ParamLidCurveLeft',blinkValue*.35)
      set('ParamLidCurveRight',blinkValue*.35)
      set('ParamEyeDeformLeft',Math.sin(t*.5)*.18)
      set('ParamEyeDeformRight',Math.sin(t*.5)*.18)
      set('ParamEarLeft',touched?.8:Math.sin(t*1.8)*.25)
      set('ParamEarRight',touched?-.8:Math.sin(t*1.7+.4)*.25)
      set('ParamSmile',state.smile)
      set('ParamSleepy',state.sleepy)
      set('ParamMouthOpen',state.mouth)
      set('ParamEmbarrassed',touched && !focused?.6:0)
    },70)
    return()=>window.clearInterval(clock)
  },[active,activity])

  return <canvas ref={canvasRef} className="inochi-demo-canvas" aria-label="MewNook Inochi2D v3 多顶点模型" />
}
