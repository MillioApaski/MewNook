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
    cover=parts[f'Eye {eye} Upper Lid']
    sleepy=parts[f'Eye {eye} Drowsy Lid']
    assert {entry['node'] for entry in blink}=={cover['uuid'],closed['uuid']}
    assert opened['uuid'] not in {entry['node'] for entry in blink}, 'Iris must stay fixed'
    assert [entry['param_name'] for entry in blink]==['transform.s.y','transform.t.y','transform.s.y']
    assert any(entry['node']==sleepy['uuid'] for entry in params['ParamSleepy']['bindings'])
    # Unlike a large skin oval, the drowsy mask stays inside its iris.
    drowsy_alpha=textures[sleepy['textures'][0]].getchannel('A')
    drowsy_lash=parts[f'Eye {eye} Drowsy Lash']
    assert textures[drowsy_lash['textures'][0]].getchannel('A').getbbox()
    assert drowsy_alpha.width < oi.width*.85,(eye,'drowsy skin patch too wide')
    assert drowsy_alpha.height < oi.height*.88,(eye,'drowsy skin patch too tall')
    assert drowsy_alpha.getbbox(),(eye,'drowsy eyelid missing')

# The neutral mouth must be recovered from source artwork, not recreated as
# a horizontal ellipse. A and B mouth variants use five pose keys in an
# angled local frame, whereas all other channels still have three.
names=('Neutral Smile','Talking Mouth A','Talking Mouth B','Sleepy Mouth')
assert all(n in parts for n in names)
mouth=params['ParamMouthOpen']
assert len(mouth['axis_points'][0])==5
assert len(mouth['bindings'])==3
assert all(len(item['values'])==5 for item in mouth['bindings'])
assert {item['node'] for item in mouth['bindings']}=={parts[n]['uuid'] for n in names[:3]}
assert any(item['node']==parts['Sleepy Mouth']['uuid'] for item in params['ParamSleepy']['bindings'])
from numpy import asarray, nonzero, cov
for name in names:
    part=parts[name]
    cx=1086/2+part['transform']['trans'][0]
    cy=1448/2+part['transform']['trans'][1]
    assert abs(cx-525)<12 and abs(cy-540)<13,(name,cx,cy)
    pixels=asarray(textures[part['textures'][0]].getchannel('A'))
    yy,xx=nonzero(pixels>110)
    assert len(xx)>10,name
    # Each mouth follows the face's rising-to-the-right direction, rather
    # than the old front-facing circular crop.
    if name!='Sleepy Mouth':
        assert cov(xx,yy)[0,1]<0,(name,'wrong mouth angle')

assert 250000 < len(b) < 9000000, 'Unexpected file size'
print('MewNook Inochi2D v2: valid header,',len(parts),'parts,',
      len(params),'parameters,',len(textures),'PNG textures, bytes:',len(b))
