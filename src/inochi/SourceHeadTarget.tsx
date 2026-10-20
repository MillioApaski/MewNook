import {useLayoutEffect,useRef} from 'react'
import {sourceArtFrame} from './sourceArtFrame'
import {headHitBox} from '../../public/inochi2d-test/headHitArea.js'

export function SourceHeadTarget({scale,onPat}:{scale:number;onPat:()=>void}){
  const ref=useRef<HTMLButtonElement>(null)
  useLayoutEffect(()=>{
    const button=ref.current,container=button?.parentElement
    if(!button||!container)return
    const resize=()=>{
      const frame=sourceArtFrame(container,scale)
      const box=headHitBox({width:frame.bounds.width,scale:frame.scale,top:frame.top})
      for(const [key,value] of Object.entries(box))button.style.setProperty(key,value+'px')
    }
    resize()
    const observer=new ResizeObserver(resize)
    observer.observe(container)
    window.addEventListener('resize',resize)
    return()=>{observer.disconnect();window.removeEventListener('resize',resize)}
  },[scale])
  return <button ref={ref} type="button" className="source-head-target" aria-label="摸摸猫娘的头" onClick={onPat}/>
}
