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
  activity: 'focus'|'rest'|'idle'
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
      await controller.loadModel('/inochi2d-test/models/MewNook-test.inx')
      if(disposed)return
      namesRef.current=controller.getAnimationNames?.()||[]
      if(namesRef.current.includes('Energetic Sway'))
        await controller.playAnimation?.('Energetic Sway',{loop:true,kind:'idle'})
      void controller.setExpressionPreset?.(activity==='focus'?'focused':activity==='rest'?'relaxed':'neutral')
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
    const expression=activity==='focus'?'focused':activity==='rest'?'relaxed':'neutral'
    void Promise.resolve(c.setExpressionPreset?.(expression)).catch(()=>{})
  },[activity])

  useEffect(()=>{
    if(touches===firstTouchRef.current)return
    firstTouchRef.current=touches
    const c=controllerRef.current
    if(!c)return
    tapUntilRef.current=Date.now()+650
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
      const t=Date.now()/1000
      const blinkPhase=t%4.1
      const blink=blinkPhase<0.16 ? Math.sin(Math.PI*blinkPhase/0.16) : 0
      void c.setParameter?.('Eye:: Left:: Blink',blink)
      void c.setParameter?.('Eye:: Right:: Blink',blink)
      void c.setParameter?.('Body:: Breath',Math.sin(t*2.2))
      void c.setParameter?.('Tail:: Sway',Math.sin(t*1.5))
      const tapped=Date.now()<tapUntilRef.current
      void c.setParameter?.('Ear:: Left:: Wiggle',tapped ? .8 : Math.sin(t*1.9)*.25)
      void c.setParameter?.('Ear:: Right:: Wiggle',tapped ? -.8 : Math.sin(t*1.8+.4)*.25)
      void c.setParameter?.('Head:: Look',activity==='focus'?-.3:Math.sin(t*.45)*.3)
    },70)
    return()=>window.clearInterval(clock)
  },[active,activity])

  return <canvas ref={canvasRef} className="inochi-demo-canvas" aria-label="Inochi2D 示例测试模型" />
}
