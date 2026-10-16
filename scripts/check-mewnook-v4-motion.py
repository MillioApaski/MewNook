#!/usr/bin/env python3
"""Strict structural/texture checks for the v4 upright motion proof-of-concept.

Passing this checker does not imply artistic acceptance or real-browser motion.
"""
from __future__ import annotations
import io, json, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image
path=Path(sys.argv[1] if len(sys.argv)>1 else 'assets/inochi/v4/rig/MewNook-v4-motion.inx')
blob=path.read_bytes()
assert blob[:8]==b'TRNSRTS\0'
size=struct.unpack('>I',blob[8:12])[0]
model=json.loads(blob[12:12+size])
parts={part['name']:part for part in model['nodes']['children']}
params={p['name']:p for p in model['param']}
assert len(parts)==18 and len(params)==14,(len(parts),len(params))
for name in ('ParamEarLeft','ParamEarRight','ParamHairLeft',
             'ParamHairRight','ParamTailDeform'):
    bindings=params[name]['bindings']
    assert len(bindings)==1 and bindings[0]['param_name']=='deform'
    assert len(bindings[0]['values'])==3
    mesh_part=next(part for part in parts.values() if part['uuid']==bindings[0]['node'])
    total=len(mesh_part['mesh']['verts'])//2
    assert total>=25 and len(mesh_part['mesh']['indices'])>=72,name
    for value in bindings[0]['values']:
        assert len(value)==2
        assert all(len(v)==total and all(len(p)==2 for p in v) for v in value)
for side in ('Left','Right'):
    blink=params['ParamEyeBlink'+side]['bindings']
    assert len(blink)==3
    assert any(b['param_name']=='transform.t.y' for b in blink)
    sleepy=params['ParamSleepy'+side]['bindings']
    assert len(sleepy)==2
    drowsy=parts['Eye '+side+' Drowsy Cover']
    assert all(item['node']==drowsy['uuid'] for item in sleepy)
    assert all(item['node']!=parts['Eye '+side+' Cover']['uuid'] for item in sleepy)
for name in ('ParamMouthOpen','ParamSleepy','ParamBreath'):
    assert name in params
pos=12+size
assert blob[pos:pos+8]==b'TEX_SECT'
pos+=8
count=struct.unpack('>I',blob[pos:pos+4])[0];pos+=4
assert count==len(parts)
for i in range(count):
    n=struct.unpack('>I',blob[pos:pos+4])[0]
    assert blob[pos+4]==0
    texture=np.asarray(Image.open(io.BytesIO(blob[pos+5:pos+5+n])).convert('RGBA')).astype(np.uint16)
    assert (texture[:,:,:3]<=texture[:,:,3:4]+1).all(),f'texture {i} not premultiplied'
    pos+=5+n
assert pos==len(blob)
print(f'v4 motion prototype structure verified: {len(parts)} parts, {len(params)} params, {count} premultiplied textures.')
print('No real-browser visual or hand-painted hidden-surface acceptance claimed.')
