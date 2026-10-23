export interface HeadFrame {width:number;scale:number;top:number}
export const HEAD_AREA:Readonly<{cx:number;cy:number;rx:number;ry:number}>
export function headHitBox(frame:HeadFrame):{left:number;top:number;width:number;height:number}
export function isHeadHit(x:number,y:number,frame:HeadFrame):boolean
