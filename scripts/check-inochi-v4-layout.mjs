#!/usr/bin/env node
// Check the v4 structure contract only. This is not a model-validation pass.
import {readFile} from 'node:fs/promises'
const root=new URL('../',import.meta.url)
const read=async p=>readFile(new URL(p,root),'utf8')
const dir='assets/inochi/v4'
const data=JSON.parse(await read(dir+'/manifest.json'))
if(!['directory_scaffold_only','prototype_generator_ready_reference_upload_pending','motion_generator_ready_reference_upload_pending','v4_source_committed_candidate_in_CI'].includes(data.stage))throw Error('Unexpected project stage')
if(data.reference.width!==1122||data.reference.height!==1402)throw Error('Wrong reference canvas')
const ids=new Set(),paths=new Set(),groups=new Set()
for(const p of data.required_parts){
 if(ids.has(p.id)||paths.has(p.path))throw Error('Duplicate part '+p.id)
 if(p.path!==`parts/${p.group}/${p.id}.png`)throw Error('Bad part path '+p.path)
 ids.add(p.id);paths.add(p.path);groups.add(p.group)
}
for(const group of groups)await read(`${dir}/parts/${group}/README.md`)
for(const name of ['source','expressions','motions','rig','validation'])await read(`${dir}/${name}/README.md`)
await read('public/inochi2d/v4/README.md')
console.log('v4 layout OK:',ids.size,'planned parts; no source layers or completed model claimed.')
