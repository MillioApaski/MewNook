/** Shared framing for the source-art poster and the live WASM camera. */
export function sourceArtFrame(container:HTMLElement,userScale:number){
  const bounds=container.getBoundingClientRect()
  const mobile=window.matchMedia('(max-width:680px)').matches
  const visibleHeight=Math.min(bounds.height,window.innerHeight)
  const zoom=Math.min(.9,Math.max(.1,userScale))/.32
  const scale=visibleHeight/(mobile?1000:1240)*zoom
  const foreground=container.closest('.art-stage')?.querySelector<HTMLElement>('.art-foreground')
  let top=Math.max(
    (bounds.height-visibleHeight)/2+visibleHeight*(mobile?.10:.06),
    (mobile?112:72)-bounds.top
  )+(foreground?.offsetTop??0)
  const stage=container.closest<HTMLElement>('.art-stage')
  if(stage?.classList.contains('art-day')){
    const room=stage.getBoundingClientRect()
    const handX=bounds.x+bounds.width/2+39*scale
    const sourceX=(handX-room.x)/room.width*1672
    const deskY=room.y+(686+.0345*sourceX)/941*room.height
    // On very wide windows the room's desk moves down as the art is cropped.
    // Keep the lap near it so the chair cannot appear above the desktop.
    top+=Math.max(0,deskY-24-(bounds.y+top+863*scale))
  }
  return{bounds,scale,top,cameraY:701+(top-bounds.height/2)/scale}
}
