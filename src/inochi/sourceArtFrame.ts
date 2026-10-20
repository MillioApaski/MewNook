/** Shared framing for the source-art poster and the live WASM camera. */
export function sourceArtFrame(container:HTMLElement,userScale:number){
  const bounds=container.getBoundingClientRect()
  const mobile=window.matchMedia('(max-width:680px)').matches
  const visibleHeight=Math.min(bounds.height,window.innerHeight)
  const zoom=Math.min(.9,Math.max(.1,userScale))/.32
  const scale=visibleHeight/(mobile?1000:1240)*zoom
  const foreground=container.closest('.art-stage')?.querySelector<HTMLElement>('.art-foreground')
  const top=Math.max(
    (bounds.height-visibleHeight)/2+visibleHeight*(mobile?.10:.06),
    (mobile?112:72)-bounds.top
  )+(foreground?.offsetTop??0)
  return{bounds,scale,top,cameraY:701+(top-bounds.height/2)/scale}
}
