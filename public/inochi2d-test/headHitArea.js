// Original 1122 × 1402 source coordinates: hair crown through chin.
export const HEAD_AREA = Object.freeze({cx:565,cy:212,rx:180,ry:156})
export function headHitBox({width,scale,top}) {
  const {cx,cy,rx,ry}=HEAD_AREA
  return {left:width/2+(cx-561-rx)*scale,top:top+(cy-ry)*scale,width:2*rx*scale,height:2*ry*scale}
}
export function isHeadHit(x,y,frame){
  const b=headHitBox(frame)
  return ((x-b.left-b.width/2)/(b.width/2))**2+((y-b.top-b.height/2)/(b.height/2))**2<=1
}
