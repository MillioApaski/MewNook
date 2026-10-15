#!/usr/bin/env python3
"""Contract checks for a generated Inochi2D .inx, prior to WebGL smoke."""
import io
import json
import struct
from pathlib import Path
from PIL import Image

root=Path(__file__).resolve().parents[1]
path=root/'public/inochi2d-test/models/MewNook-v2.inx'
b=path.read_bytes()
assert b.startswith(b'TRNSRTS\x00'), 'Not an Inochi2D INX file'
json_size=struct.unpack('>I',b[8:12])[0]
assert 500 < json_size < 300000, 'Abnormal puppet JSON'
puppet=json.loads(b[12:12+json_size])
nodes=puppet['nodes']['children']
parts={x['name']:x for x in nodes}
params={x['name']:x for x in puppet['param']}
required=[
 'ParamEyeBlinkLeft','ParamEyeBlinkRight','ParamMouthOpen','ParamBreath',
 'ParamHeadX','ParamHeadY','ParamBodyY','ParamBodyZ',
 'ParamEarLeft','ParamEarRight','ParamTailSwing',
 'ParamSmile','ParamSleepy','ParamEmbarrassed'
]
assert all(name in params for name in required), set(required)-params.keys()
assert len(parts) >= 10 and len(set(x['uuid'] for x in nodes))==len(nodes)
# Inox2D draws high zsort first. The eye overlays must render in front.
assert parts['Retouched body and face']['zsort']==0
for side in ('Left','Right'):
    assert parts[f'Eye {side} Iris']['zsort'] < 0
    assert parts[f'Eye {side} Closed Lash']['zsort'] < parts[f'Eye {side} Iris']['zsort']
section=12+json_size
assert b[section:section+8]==b'TEX_SECT', 'Missing texture section'
count=struct.unpack('>I',b[section+8:section+12])[0]
assert count == len(nodes),'Every drawable should have a texture'
pos=section+12
textures=[]
for index in range(count):
    n=struct.unpack('>I',b[pos:pos+4])[0]
    png=b[pos+5:pos+5+n]
    assert png.startswith(b'\x89PNG'),f'Texture {index} is not PNG'
    im=Image.open(io.BytesIO(png)).convert('RGBA')
    # All generated textures must be premultiplied (Inox2D GL blend ONE).
    from numpy import array
    pixels=array(im,dtype='uint16')
    assert (pixels[:,:,:3] <= pixels[:,:,3:4]+1).all(),f'Texture {index} has non-premultiplied color'
    textures.append(im)
    pos+=5+n
assert pos==len(b),'Trailing or missing texture data'
for eye in ['Left','Right']:
    opened=parts[f'Eye {eye} Iris']
    closed=parts[f'Eye {eye} Closed Lash']
    oi=textures[opened['textures'][0]].getchannel('A')
    ci=textures[closed['textures'][0]].getchannel('A')
    assert oi.getextrema()[1]>=235
    assert oi.getpixel((0,0)) < 30 and oi.getpixel((oi.width-1,0)) < 30, 'Eye must have a non-rectangular alpha'
    assert ci.getbbox() and ci.width>20 and ci.height>3, 'Closed eyelid art missing'
    blink=params[f'ParamEyeBlink{eye}']['bindings']
    assert {entry['node'] for entry in blink}=={opened['uuid'],closed['uuid']}
    assert all(entry['param_name']=='transform.s.y' for entry in blink)
assert 250000 < len(b) < 9000000, 'Unexpected file size'
print('MewNook Inochi2D v2: valid header,',len(parts),'parts,',
      len(params),'parameters,',len(textures),'PNG textures, bytes:',len(b))
