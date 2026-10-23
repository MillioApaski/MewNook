export type ChatExpression={kind:'neutral'|'happy'|'caring'|'curious'|'calm';strength:number}
export function chatExpression(text:string):ChatExpression
export function expressionPose(expression:ChatExpression):Partial<Record<'brow'|'earLeft'|'earRight'|'headRoll'|'headY'|'sleepy',number>>
