import {useEffect, useRef} from 'react'

/**
 * Experimental Inochi2D WEBGL2 runtime. The compiled JS/WASM and the Aka
 * .inx file are pinned, license-attributed test assets; NOT a MewNook model.
 */
interface Controller {
  mount(canvas: HTMLCanvasElement): Promise<void> | void
  loadModel(url:string): Promise<void>
  getAnimationNames?(): string[]
  playAnimation?(name:string, options?:{loop?:boolean;restart?:boolean;kind?:'idle'|'reaction'|'manual'}):Promise<void>|void
  applyInteractionImpulse?(x:number,y:number):Promise<void>|void
  setExpressionPreset?(name:string):Promise<void>|void
  setCameraTransform(x:number,y:number,scale:number):Promise<void>|void
  resize(width:number,height:number,ratio:number):Promise<void>|void
  unmount():Promise<void>|void
}
type Bridge = {createInochi2DController(opts:{wasmUrl:string;debug?:boolean}):Promise<Controller>}
export type InochiTestStatus = 'off'|'loading'|'ready'|'error'

interface Props {
  active: boolean
  scale: number
  activity: 'focus'|'rest'|'idle'
  touches: number
  onStatus: (status:InochiTestStatus,error?:string)=>void
}

export function InochiTestCharacter({active,scale,activity,touches,onStatus}:Props){
  const canvasRef=useRef<HTMLCanvasElement|null>(null)
  const controllerRef=useRef<Controller|null>(null)
  const namesRef=useRef<string[]>([])
  const firstTouchRef=useRef(touches)

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
      await controller.setCameraTransform(0,1450,scale)
      if(disposed)return
      await controller.loadModel('/inochi2d-test/models/Aka.inx')
      if(disposed)return
      namesRef.current=controller.getAnimationNames?.()||[]
      if(namesRef.current.includes('Energetic Sway'))
        await controller.playAnimation?.('Energetic Sway',{loop:true,kind:'idle'})
      void controller.setExpressionPreset?.(activity==='focus'?'focused':activity==='rest'?'relaxed':'neutral')
      onStatus('ready')
    })().catch(e=>{
      if(!disposed)onStatus('error',e instanceof Error?e.message:String(e))
    })
    return()=>{
      disposed=true
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
    if(c)void c.setCameraTransform(0,1450,Math.min(.9,Math.max(.1,scale)))
  },[scale])

  useEffect(()=>{
    const c=controllerRef.current
    if(!c)return
    const expression=activity==='focus'?'focused':activity==='rest'?'relaxed':'neutral'
    void Promise.resolve(c.setExpressionPreset?.(expression)).catch(()=>{})
  },[activity])

  useEffect(()=>{
    if(touches===firstTouchRef.current)return
    firstTouchRef.current=touches
    const c=controllerRef.current
    if(!c)return
    void c.applyInteractionImpulse?.(5,-3)
    const names=namesRef.current
    if(names.includes('Yatta Celebration'))
      void c.playAnimation?.('Yatta Celebration',{restart:true,kind:'reaction'})
  },[touches])

  return <canvas ref={canvasRef} className="inochi-demo-canvas" aria-label="Inochi2D 示例测试模型" />
}
