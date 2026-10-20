import{useLayoutEffect,useRef}from'react'
import{sourceArtFrame}from'./sourceArtFrame'

/** Show the same original-art pose while the larger live rig is loading. */
export function SourceCharacterPoster({scale}:{scale:number}){
  const ref=useRef<HTMLImageElement>(null)
  useLayoutEffect(()=>{
    const image=ref.current,container=image?.parentElement
    if(!image||!container)return
    const resize=()=>{
      const frame=sourceArtFrame(container,scale)
      image.style.width=1122*frame.scale+'px'
      image.style.height=1402*frame.scale+'px'
      image.style.top=frame.top+'px'
    }
    resize()
    const observer=typeof ResizeObserver==='undefined'?null:new ResizeObserver(resize)
    observer?.observe(container)
    window.addEventListener('resize',resize)
    return()=>{observer?.disconnect();window.removeEventListener('resize',resize)}
  },[scale])
  return <img ref={ref} className="source-character-poster" src="/inochi2d/v4/poster.png" alt="" width={1122} height={1402} fetchPriority="high" draggable={false}/>
}
