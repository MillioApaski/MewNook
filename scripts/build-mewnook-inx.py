#!/usr/bin/env python3
"""Build a genuine, deliberately minimal Inochi2D INX puppet.

Uses original MewNook day-character artwork that is already in the repo.
Output contains real textured Part meshes and editable parameter bindings.
This is a prototype rig, not a hand-painted professional model.
"""
from __future__ import annotations
import io, json, math, struct, copy
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'public/assets/rooms/day/character.webp'
TARGET=ROOT/'public/inochi2d-test/models/MewNook-test.inx'
BASE=ROOT/'public/inochi2d-test/models'
IMG=Image.open(SOURCE).convert('RGBA')
W,H=IMG.size
TRANSPARENT=4294967295
parts=[]
params=[]
blobs=[]
seed=10000
def uid():
    global seed
    seed += 1
    return seed

# All masks are proportions of the *existing* original MewNook asset.
# The unmasked remainder is the body and back hair.
regions={
    'Tail':[(.83,.35),(.94,.32),(.99,.37),(.98,.65),(.92,.77),(.85,.66)],
    'Left Ear':[(.25,.04),(.31,.0),(.41,.13),(.38,.20),(.28,.17)],
    'Right Ear':[(.56,.1),(.68,.00),(.74,.03),(.74,.19),(.65,.20)],
    'Left Eye':[(.37,.225),(.48,.225),(.49,.31),(.37,.32)],
    'Right Eye':[(.52,.218),(.64,.215),(.65,.31),(.52,.31)],
    'Mouth':[(.47,.31),(.56,.31),(.56,.355),(.47,.355)],
    'Chest Bow':[(.41,.37),(.63,.37),(.63,.60),(.41,.60)]
}
layer_masks={}
for name,polygon in regions.items():
    m=Image.new('L',(W,H),0)
    d=ImageDraw.Draw(m)
    d.polygon([(round(x*W),round(y*H)) for x,y in polygon],fill=255)
    layer_masks[name]=m
# Assign each pixel to exactly one layer: no doubling and identical rest pose.
already=Image.new('L',(W,H),0)
for name in reversed(list(layer_masks)):
    from PIL import ImageChops
    layer_masks[name]=ImageChops.subtract(layer_masks[name],already)
    already=ImageChops.lighter(already,layer_masks[name])
from PIL import ImageChops
layer_masks['Body + Hair']=ImageChops.invert(already)

def texture_part(name,mask,z):
    a=IMG.copy()
    channel=ImageChops.multiply(IMG.getchannel('A'),mask)
    a.putalpha(channel)
    bbox=a.getbbox()
    if bbox is None:return None
    crop=a.crop(bbox)
    # Avoid colored fringes and PNG size bloat in discarded pixels.
    px=crop.load()
    for y in range(crop.height):
        for x in range(crop.width):
            if px[x,y][3]==0: px[x,y]=(0,0,0,0)
    buf=io.BytesIO()
    crop.save(buf,'PNG',optimize=True)
    texid=len(blobs);blobs.append(buf.getvalue())
    x0,y0,x1,y1=bbox
    width=x1-x0;height=y1-y0
    node={
      'uuid':uid(),'name':name,'type':'Part','enabled':True,'zsort':z,
      'transform':{'trans':[(x0+x1)/2-W/2,(y0+y1)/2-H/2,-1.0],
                   'rot':[0,0,0],'scale':[1,1]},
      'lockToRoot':False,
      'mesh':{'verts':[-width/2,-height/2,-width/2,height/2,width/2,-height/2,width/2,height/2],
              'uvs':[0,0,0,1,1,0,1,1], 'indices':[0,2,1,2,3,1],
              'origin':[0,0]},
      'textures':[texid,TRANSPARENT,TRANSPARENT],
      'blend_mode':'Normal','tint':[1,1,1],'screenTint':[0,0,0],
      'emissionStrength':1,'masks':[],'mask_threshold':0.5,'opacity':1,
      'psdLayerPath':name
    }
    parts.append(node)
    return node

# Back to front; leave a single full-body base for fast smoke tests.
b=texture_part('Body + Hair',layer_masks['Body + Hair'],0.0)
tail=texture_part('Tail',layer_masks['Tail'],0.1)
lEar=texture_part('Left Ear',layer_masks['Left Ear'],0.2)
rEar=texture_part('Right Ear',layer_masks['Right Ear'],0.3)
lEye=texture_part('Left Eye',layer_masks['Left Eye'],0.4)
rEye=texture_part('Right Eye',layer_masks['Right Eye'],0.5)
mouth=texture_part('Mouth',layer_masks['Mouth'],0.6)
bow=texture_part('Chest Bow',layer_masks['Chest Bow'],0.7)

def add_param(name,node,prop,points,minimum=-1.0,maximum=1.0,default=0.0):
    # Same schema used by the 0.8.x Inochi Creator exported Aka example.
    values=[[float(v),float(v)] for v in points]
    params.append({
      'uuid':uid(),'name':name,'is_vec2':False,
      'min':[minimum,0],'max':[maximum,1],'defaults':[default,0.5],
      'axis_points':[[0,.5,1],[0,1]],'merge_mode':'Additive',
      'bindings':[{'node':node['uuid'],'param_name':prop,'values':values,
                   'isSet':[[True,True]]*3,'interpolate_mode':'Linear'}]
    })
add_param('Eye:: Left:: Blink',lEye,'transform.s.y',[1,1,.03])
add_param('Eye:: Right:: Blink',rEye,'transform.s.y',[1,1,.03])
add_param('Ear:: Left:: Wiggle',lEar,'transform.r.z',[-.075,0,.075])
add_param('Ear:: Right:: Wiggle',rEar,'transform.r.z',[.075,0,-.075])
add_param('Tail:: Sway',tail,'transform.r.z',[-.10,0,.10])
add_param('Body:: Breath',b,'transform.s.y',[.992,1,1.008])
add_param('Head:: Look',lEye,'transform.t.x',[-5,0,5])
add_param('Mouth:: Talk',mouth,'transform.s.y',[.8,1,1.15])
root={'uuid':uid(),'name':'Root','type':'Node','enabled':True,'zsort':0,
      'transform':{'trans':[0,0,0],'rot':[0,0,0],'scale':[1,1]},
      'lockToRoot':False,'children':parts}
puppet={
 'meta':{'name':'MewNook Prototype','version':'v0.8.6','rigger':'MewNook experimental generator',
         'artist':'Original MewNook artwork','rights':None,'copyright':'MewNook',
         'licenseURL':'','contact':'','reference':'','thumbnailId':TRANSPARENT,
         'preservePixels':False},
 'physics':{},'nodes':root,'param':params,'automation':[],'animations':[],
 'groups':[]
}
payload=json.dumps(puppet,separators=(',',':'),ensure_ascii=False).encode('utf-8')
buf=bytearray(b'TRNSRTS\x00')
buf+=struct.pack('>I',len(payload))+payload+b'TEX_SECT'+struct.pack('>I',len(blobs))
for png in blobs:
    buf+=struct.pack('>I',len(png))+b'\x00'+png
TARGET.parent.mkdir(parents=True,exist_ok=True)
TARGET.write_bytes(buf)
print('Original simplified Inochi2D rig:',TARGET,'parts',len(parts),'params',len(params),'textures',len(blobs),'bytes',len(buf))
