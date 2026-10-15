#!/usr/bin/env python3
"""Fail CI when Inochi2D v3 grid meshes or deform tracks regress."""
import json,struct
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
    assert len(blink['bindings'])==2 and all(b['param_name']=='transform.s.y' for b in blink['bindings'])

assert len(blob)<8_000_000
print(f'MewNook v3 validated: {len(nodes)} parts, {len(params)} params, {len(deform)} vertex-deformation tracks')
