// Compatibility for the pinned WASM, which ignores native Part opacity bindings.
// The model opts in; ordinary models and animation opacity lanes keep their path.
export function compileParameterOpacities(model) {
 if (!model?.meta?.sourceArtOpacityBindings) return []
 const names=new Map(),defaults=new Map()
 const visit=node=>{names.set(node.uuid,node.name);defaults.set(node.uuid,node.opacity??1);for(const child of node.children||[])visit(child)}
 visit(model.nodes)
 return (model.param||[]).flatMap(parameter=>(parameter.bindings||[])
  .filter(binding=>binding.param_name==='opacity'&&names.has(binding.node))
  .map(binding=>({name:parameter.name,nodeName:names.get(binding.node),
   mode:binding.opacity_mode??'replace',baseOpacity:defaults.get(binding.node),min:parameter.min[0],max:parameter.max[0],defaultValue:parameter.defaults[0],
   points:parameter.axis_points[0],values:binding.values.map(row=>row[0])})))
}
export function evaluateParameterOpacities(bindings,values) {
 const result=new Map()
 for(const b of [...bindings.filter(b=>b.mode!=='multiply'),...bindings.filter(b=>b.mode==='multiply')]){
  const value=values.get(b.name)?.[0]??b.defaultValue
  const t=Math.max(0,Math.min(1,(value-b.min)/(b.max-b.min)))
  let index=0
  while(index<b.points.length-2&&t>b.points[index+1])index++
  const weight=Math.max(0,Math.min(1,(t-b.points[index])/(b.points[index+1]-b.points[index])))
  const opacity=b.values[index]*(1-weight)+b.values[index+1]*weight
  result.set(b.nodeName,opacity*(b.mode==='multiply'?(result.get(b.nodeName)??b.baseOpacity??1):1))
 }
 return result
}
