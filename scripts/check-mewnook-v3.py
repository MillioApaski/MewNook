#!/usr/bin/env python3
"""Fail CI when Inochi2D v3 grid meshes or deform tracks regress."""
import json,struct,io
import numpy as np
from PIL import Image
from pathlib import Path
root=Path(__file__).resolve().parents[1]
blob=(root/'public/inochi2d-test/models/MewNook-v3.inx').read_bytes()
assert blob[:8]==b'TRNSRTS\x00'
jlen=struct.unpack('>I',blob[8:12])[0]
puppet=json.loads(blob[12:12+jlen])
nodes=puppet['nodes']['children']
node_by_id={n['uuid']:n for n in nodes}
params=puppet['param']
deform=[p for p in params for b in p['bindings'] if b['param_name']=='deform']
expected={'ParamHairLeft','ParamHairRight','ParamHairFront','ParamTailDeform'}
assert {p['name'] for p in deform}==expected
for p in deform:
    b=next(b for b in p['bindings'] if b['param_name']=='deform')
    node=node_by_id[b['node']]
    count=len(node['mesh']['verts'])//2
    assert count>=15 and len(node['mesh']['indices'])>=18,(p['name'],count)
    assert len(node['mesh']['uvs'])==count*2
    assert len(b['values'])==3
    assert len(p['bindings'])==1, (p['name'],'fallback transform must not mask failed mesh deform')
    for row in b['values']:
        assert len(row)==2
        for cell in row:
            assert len(cell)==count, (p['name'],len(cell),count)
    middle=b['values'][1][0]
    assert all(abs(x)<1e-5 for xy in middle for x in xy)
    assert any(abs(x)>.5 for cell in b['values'][2] for xy in cell for x in xy)
assert len(nodes)>=12 and len(params)>=18
assert all(x['zsort']<0 for x in nodes if x['name'].startswith('Hair '))
byname={part['name']:part for part in nodes}
for side in ('Left','Right'):
    for label in (f'Eye {side} Iris',f'Eye {side} Closed Lash'):
        assert len(byname[label]['mesh']['verts'])==8, (label, 'unexpected eye geometry')
    blink=next(p for p in params if p['name']==f'ParamEyeBlink{side}')
    assert len(blink['bindings'])==3
    assert all(binding['node']!=byname[f'Eye {side} Iris']['uuid'] for binding in blink['bindings'])
    assert any(binding['node']==byname[f'Eye {side} Upper Lid']['uuid'] for binding in blink['bindings'])

assert len(blob)<8_000_000
# Each v3 art texture must also respect the premultiplied alpha contract.
pos=12+jlen
assert blob[pos:pos+8]==b'TEX_SECT'
texcount=struct.unpack('>I',blob[pos+8:pos+12])[0]
pos+=12
for n in range(texcount):
    size=struct.unpack('>I',blob[pos:pos+4])[0]
    tex=np.asarray(Image.open(io.BytesIO(blob[pos+5:pos+5+size])).convert('RGBA')).astype(np.uint16)
    assert (tex[:,:,:3]<=tex[:,:,3:4]+1).all(),f'texture {n} violates premultiplied alpha'
    pos+=5+size
assert pos==len(blob)

print(f'MewNook v3 validated: {len(nodes)} parts, {len(params)} params, {len(deform)} vertex-deformation tracks')
