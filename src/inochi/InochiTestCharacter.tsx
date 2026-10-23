import {useEffect, useRef} from 'react'
import type {CompanionActivity} from './companionActivity'
import{sourceArtFrame}from'./sourceArtFrame'
import{chatExpression,expressionPose}from'../../public/inochi2d-test/chatExpression.js'

/** Shared room renderer for the approved original-art character and legacy fallback. */
interface SourceAction {
  blink:number; mouth:number; sleepy:number; earLeft:number; earRight:number;
  headRoll:number; headY:number; pat:number; hair:number; brow:number; done:boolean
}
interface SourceActions {
  actionDuration:Record<string,number>
  createActionMixer(): (state:SourceAction,now:number,touchRevision?:number)=>SourceAction
  sampleAction(action:string,elapsed:number):SourceAction
  sourceArtParameters(state:SourceAction,blink?:number,wind?:number):Record<string,number>
}
interface Controller {
  setRenderPolicy?(policy:{paused?:boolean;maxFps?:number}):void
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
  model: 'v3' | 'v4'
  active: boolean
  scale: number
  activity: CompanionActivity
  speechText?:string
  touches: number
  onStatus: (status:InochiTestStatus,error?:string)=>void
}

export function InochiTestCharacter({model,active,scale,activity,speechText='',touches,onStatus}:Props){
  const canvasRef=useRef<HTMLCanvasElement|null>(null)
  const controllerRef=useRef<Controller|null>(null)
  const namesRef=useRef<string[]>([])
  const firstTouchRef=useRef(touches)
  const tapUntilRef=useRef(0)
  const tapStartedRef=useRef(0)
  const actionsRef=useRef<SourceActions|null>(null)
  const actionMixerRef=useRef<ReturnType<SourceActions['createActionMixer']>|null>(null)
  const resizeRef=useRef<(()=>void)|null>(null)
  const scaleRef=useRef(scale)
  scaleRef.current=scale
  const controllerReadyRef=useRef(false)
  const loadedModelRef=useRef('')
  const manualBlinkUntil=useRef(0)
  const speechRef=useRef(speechText)
  speechRef.current=speechText
  const smoothed=useRef({smile:0,sleepy:0,mouth:0})

  useEffect(()=>{
    if(!active)return
    const canvas=canvasRef.current
    if(!canvas)return
    let disposed=false,controller:Controller|null=null,observer:ResizeObserver|null=null
    let resizeHandler:(()=>void)|null=null
    let visibilityHandler:(()=>void)|null=null
    const startedAt=performance.now()
    canvas.dataset.modelState='loading'
    onStatus('loading')
    void (async()=>{
      if(!canvas.getContext('webgl2'))throw new Error('浏览器缺少 WebGL2 支持')
      const moduleUrl=model==='v4'?'/inochi2d-test/runtime/inochi_source_bridge.js?rig=source-art-20261024-headpat':'/inochi2d-test/runtime/inochi_bridge.js'
      if(model==='v4'){
        const actionsUrl='/inochi2d-test/actions.js?rig=source-art-20261024-headpat'
        actionsRef.current=await import(/* @vite-ignore */ actionsUrl) as SourceActions
        actionMixerRef.current=actionsRef.current.createActionMixer()
      }
      const bridge=await import(/* @vite-ignore */ moduleUrl) as Bridge
      if(disposed)return
      controller=await bridge.createInochi2DController({wasmUrl:'/inochi2d-test/runtime/inochi2d_bg.wasm'})
      if(disposed){await controller.unmount();return}
      controllerRef.current=controller
      await controller.mount(canvas)
      visibilityHandler=()=>controller?.setRenderPolicy?.({paused:document.visibilityState==='hidden',maxFps:window.matchMedia('(max-width:680px)').matches?30:60})
      document.addEventListener('visibilitychange',visibilityHandler)
      visibilityHandler()
      const resize=()=>{
        if(!canvas.isConnected||!controller)return
        const bounds=(canvas.parentElement??canvas).getBoundingClientRect()
        const ratio=Math.min(window.devicePixelRatio||1,window.matchMedia('(max-width:680px)').matches?1:1.25)
        visibilityHandler?.()
        void controller.resize(Math.max(1,bounds.width),Math.max(1,bounds.height),ratio)
        const userScale=Math.min(.9,Math.max(.1,scaleRef.current))
        const source=loadedModelRef.current==='v4'
        if(source){
          const frame=sourceArtFrame(canvas.parentElement??canvas,userScale)
          // WASM camera units are backing pixels; resize uses this DPR too.
          void controller.setCameraTransform(0,frame.cameraY,frame.scale*ratio)
        }else{
          void controller.setCameraTransform(0,120,userScale)
        }
      }
      resizeRef.current=resize
      resize()
      if(typeof ResizeObserver!=='undefined'){
        observer=new ResizeObserver(resize)
        observer.observe(canvas.parentElement??canvas)
      }
      // The room art can keep its size while an ultrawide viewport changes height.
      resizeHandler=resize;window.addEventListener('resize',resizeHandler)
      await controller.setCameraTransform(0,120,scale)
      if(disposed)return
      const candidates=model==='v4' ? [
        {name:'v4',url:'/inochi2d/v4/MewNook.inx?rig=source-art-20261024-headpat'},
        {name:'v3',url:'/inochi2d-test/models/MewNook-v3.inx?rig=tilted-lid-v2-20261015'},
        {name:'v2',url:'/inochi2d-test/models/MewNook-v2.inx?rig=tilted-lid-v2-20261015'}
      ] : [
        {name:'v3',url:'/inochi2d-test/models/MewNook-v3.inx?rig=tilted-lid-v2-20261015'},
        {name:'v2',url:'/inochi2d-test/models/MewNook-v2.inx?rig=tilted-lid-v2-20261015'}
      ]
      let loadedModel=''
      let lastError:unknown
      for(const candidate of candidates){
        if(disposed)return
        try {
          await controller.loadModel(candidate.url)
          loadedModel=candidate.name
          break
        }catch(error){lastError=error}
      }
      if(!loadedModel)throw lastError ?? new Error('Inochi2D 模型加载失败')
      loadedModelRef.current=loadedModel
      canvas.dataset.modelVersion=loadedModel
      canvas.dataset.requestedModel=model
      canvas.dataset.modelRevision=loadedModel==='v4'?'source-art-20261024-headpat':'legacy'
      resize()
      if(disposed)return
      namesRef.current=controller.getAnimationNames?.()||[]
      if(namesRef.current.includes('Energetic Sway'))
        await controller.playAnimation?.('Energetic Sway',{loop:true,kind:'idle'})
      // MewNook parameters are owned by the rig, not by Aka preset names.
      controllerReadyRef.current=true
      // Keep the poster until the loaded rig has reached a browser paint.
      await new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve())))
      if(disposed)return
      canvas.dataset.modelReadyMs=(performance.now()-startedAt).toFixed(1)
      canvas.dataset.modelState='ready'
      onStatus('ready',loadedModel===model?'':model+' 无法加载，已回退 '+loadedModel)
    })().catch(e=>{
      if(!disposed){canvas.dataset.modelState='error';onStatus('error',e instanceof Error?e.message:String(e))}
    })
    return()=>{
      disposed=true
      controllerReadyRef.current=false
      loadedModelRef.current=''
      delete canvas.dataset.modelVersion
      delete canvas.dataset.requestedModel
      delete canvas.dataset.modelRevision
      delete canvas.dataset.headPat
      delete canvas.dataset.headPatWeight
      delete canvas.dataset.headPatClosure
      resizeRef.current=null
      actionsRef.current=null
      observer?.disconnect()
      if(visibilityHandler)document.removeEventListener('visibilitychange',visibilityHandler)
      if(resizeHandler)window.removeEventListener('resize',resizeHandler)
      if(controllerRef.current===controller)controllerRef.current=null
      if(controller)void Promise.resolve(controller.unmount()).catch(()=>{})
      onStatus('off')
    }
    // The renderer mounts only once; scale and activity use separate effects.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[active,model,onStatus])

  useEffect(()=>{
    resizeRef.current?.()
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
    if(!c || !controllerReadyRef.current)return
    tapStartedRef.current=Date.now()
    tapUntilRef.current=tapStartedRef.current+(loadedModelRef.current==='v4'?(actionsRef.current?.actionDuration.tap??2400):1400)
    if(loadedModelRef.current==='v4')return
    manualBlinkUntil.current=Date.now()+470
    void c.applyInteractionImpulse?.(5,-3)
    const names=namesRef.current
    if(names.includes('Yatta Celebration'))
      void c.playAnimation?.('Yatta Celebration',{restart:true,kind:'reaction'})
  },[touches])

  useEffect(()=>{
    if(!active)return
    const tick=()=>{
      const c=controllerRef.current
      if(!c || !controllerReadyRef.current)return
      if(document.visibilityState==='hidden')return
      const current=Date.now()
      const t=current/1000
      const resting=activity==='rest',focused=activity==='focus'
      const sleepy=activity==='sleepy',talking=activity==='chat'
      const interval=sleepy?6.2:focused?5.2:3.9
      const phase=t%interval
      const blink=phase<0.29 ? Math.sin(Math.PI*phase/0.29) : 0
      const blinkValue=current<manualBlinkUntil.current?1:blink
      const touched=current<tapUntilRef.current
      const v4=loadedModelRef.current==='v4'
      const state=smoothed.current
      state.smile+=((resting||talking?0.65:focused?0.10:0.22)-state.smile)*0.12
      state.sleepy+=((sleepy?0.95:focused?0.12:0)-state.sleepy)*0.12
      // Smooth new-text speech and release the mouth when the reply finishes.
      state.mouth+=((talking?(0.52+0.38*Math.abs(Math.sin(t*4.8))):0)-state.mouth)*0.25
      const set=(name:string,val:number)=>void c.setParameter?.(name,val)
      if(v4){
        if(!actionsRef.current)return
        const actions=actionsRef.current
        const response=actions.sampleAction(touched?'tap':'none',current-tapStartedRef.current)
        response.sleepy=state.sleepy
        response.mouth=state.mouth
        if(!touched){
          response.brow=talking?-.2:0
          if(talking)Object.assign(response,expressionPose(chatExpression(speechRef.current)))
        }
        const motion=focused?.4:sleepy?.3:1
        const pose=actionMixerRef.current?.(response,current,touched?tapStartedRef.current:0)??response
        const values=actions.sourceArtParameters(pose,blink,Math.sin(t*.82)*.2*motion)
        values.ParamBreath=Math.sin(t*(sleepy?1.25:2))*(focused?.42:.65)
        values.ParamTailDeform=Math.sin(t*.94+1.7)*.28*motion
        for(const [id,value] of Object.entries(values))set(id,value)
        if(canvasRef.current){
          canvasRef.current.dataset.chatExpression=talking?chatExpression(speechRef.current).kind:'neutral'
          canvasRef.current.dataset.brow=values.ParamBrowLeft.toFixed(3)
          canvasRef.current.dataset.headPat=touched?'active':'idle'
          canvasRef.current.dataset.headPatWeight=values.ParamHeadPat.toFixed(3)
          canvasRef.current.dataset.headPatClosure=pose.blink.toFixed(3)
          canvasRef.current.dataset.eyeClosure=values.ParamEyeBlinkLeft.toFixed(3)
          canvasRef.current.dataset.mouthOpen=values.ParamMouthOpen.toFixed(3)
          canvasRef.current.dataset.drowsyMouth=values.ParamDrowsyMouth.toFixed(3)
          canvasRef.current.dataset.headRoll=values.ParamHeadRoll.toFixed(3)
        }
        return
      }
      set('ParamEyeBlinkLeft',blinkValue)
      set('ParamEyeBlinkRight',blinkValue)
      set('ParamBreath',Math.sin(t*(sleepy?1.25:2.0))*(focused?.42:.65))
      set('ParamBodyY',Math.sin(t*1.0)*.16)
      set('ParamBodyZ',Math.sin(t*.7)*.12)
      // The character was painted with a tilted head. Never simulate a
      // frontal head turn by sliding only the irises.
      set('ParamHeadX',focused?-.055:Math.sin(t*.42)*.035)
      set('ParamHeadY',focused?.055:sleepy?.035:Math.sin(t*.34)*.025)
      set('ParamTailSwing',Math.sin(t*(sleepy?.65:1.3))*(focused?.35:.6))
      // Real native Inochi2D per-vertex deform. No CSS animation or
      // transform-position fallback; amplitudes remain deliberately small.
      const motion=focused?.4:sleepy?.3:1
      set('ParamHairLeft',Math.sin(t*.82)*.33*motion)
      set('ParamHairRight',Math.sin(t*.73+1.1)*.29*motion)
      set('ParamHairFront',Math.sin(t*1.07+.5)*.22*motion)
      set('ParamTailDeform',Math.sin(t*.94+1.7)*.36*motion)
      set('ParamEarLeft',touched?.95:Math.sin(t*1.8)*.17)
      set('ParamEarRight',touched?-.95:Math.sin(t*1.7+.4)*.17)
      set('ParamSmile',state.smile)
      set('ParamEmbarrassed',touched && !focused?.6:0)
      set('ParamSleepy',state.sleepy)
      set('ParamMouthOpen',state.mouth)
    }
    let clock:number|undefined
    const sync=()=>{
      window.clearInterval(clock)
      if(document.visibilityState!=='hidden'){tick();clock=window.setInterval(tick,70)}
    }
    sync();document.addEventListener('visibilitychange',sync)
    return()=>{window.clearInterval(clock);document.removeEventListener('visibilitychange',sync)}
  },[active,activity])

  return <canvas ref={canvasRef} className="inochi-demo-canvas" data-activity={activity} aria-label={model==='v4'?'正坐姿动态猫娘':'旧版动态猫娘'} />
}
