import {useEffect,useRef,useState,type RefObject} from 'react'
import {createPortal} from 'react-dom'
import {sourceArtFrame} from './sourceArtFrame'

interface HandsController {
  mount(canvas:HTMLCanvasElement):Promise<void>|void
  loadModel(url:string):Promise<void>
  setParameter(id:string,value:number):Promise<void>|void
  setCameraTransform(x:number,y:number,scale:number):Promise<void>|void
  resize(width:number,height:number,ratio:number):Promise<void>|void
  setRenderPolicy(policy:{paused:boolean;maxFps:number}):void
  unmount():Promise<void>|void
}

/** Forearms share source coordinates with the body, but paint above the desk. */
export function useFocusHands({active,requested,host,body,scale}:{active:boolean;requested:boolean;host:HTMLDivElement|null;body:RefObject<HTMLCanvasElement|null>;scale:number}){
  const canvas=useRef<HTMLCanvasElement|null>(null),controller=useRef<HandsController|null>(null)
  const [loaded,setLoaded]=useState(false),[needed,setNeeded]=useState(false),[failed,setFailed]=useState(false)
  const scaleRef=useRef(scale);scaleRef.current=scale
  const resizeRef=useRef<(()=>void)|null>(null)
  useEffect(()=>{if(requested)setNeeded(true)},[requested])
  useEffect(()=>{resizeRef.current?.()},[scale])
  useEffect(()=>{
    if(!active||!needed||!host||!host.isConnected||!canvas.current)return
    let disposed=false,c:HandsController|null=null,observer:ResizeObserver|null=null
    const element=canvas.current
    setFailed(false)
    void(async()=>{
      const bridgeUrl='/inochi2d-test/runtime/inochi_source_bridge.js?rig=source-art-20261026-focus'
      const bridge=await import(/* @vite-ignore */ bridgeUrl)
      if(disposed)return
      c=await bridge.createInochi2DController({wasmUrl:'/inochi2d-test/runtime/inochi2d_bg.wasm'}) as HandsController
      if(disposed){await c.unmount();return}
      await c.mount(element)
      const resize=()=>{
        const parent=body.current?.parentElement,front=element.parentElement
        if(!parent||!front||!c)return
        const frame=sourceArtFrame(parent,scaleRef.current),bounds=front.getBoundingClientRect()
        const ratio=Math.min(window.devicePixelRatio||1,window.matchMedia('(max-width:680px)').matches?1:1.25)
        void c.resize(Math.max(1,bounds.width),Math.max(1,bounds.height),ratio)
        const x=(frame.bounds.x+frame.bounds.width/2-bounds.x-bounds.width/2)/frame.scale
        const top=frame.bounds.y+frame.top-bounds.y
        void c.setCameraTransform(x,701+(top-bounds.height/2)/frame.scale,frame.scale*ratio)
        element.dataset.sourceScale=frame.scale.toFixed(5)
        element.dataset.sourceTop=(frame.bounds.y+frame.top).toFixed(3)
      }
      resizeRef.current=resize
      observer=new ResizeObserver(resize)
      observer.observe(element.parentElement!)
      if(body.current?.parentElement)observer.observe(body.current.parentElement)
      window.addEventListener('resize',resize)
      await c.loadModel('/inochi2d/v4/MewNook-hands.inx?rig=source-art-20261026-focus')
      if(disposed)return
      resize();c.setRenderPolicy({paused:true,maxFps:30});controller.current=c;setLoaded(true)
    })().catch(async()=>{controller.current=null;if(c){await c.unmount();c=null}if(!disposed)setFailed(true)})
    return()=>{
      disposed=true;controller.current=null;setLoaded(false);observer?.disconnect()
      if(resizeRef.current)window.removeEventListener('resize',resizeRef.current)
      resizeRef.current=null
      if(c)void c.unmount()
    }
  },[active,needed,host,body])
  return {controller,portal:active&&host?createPortal(<div className="source-hands-frame" data-hands-state={failed?'error':loaded?'ready':needed?'loading':'idle'}><canvas ref={canvas} className="source-hands-canvas" aria-label="桌面前方的专注手部"/></div>,host):null}
}
