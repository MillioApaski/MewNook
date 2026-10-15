#!/usr/bin/env python3
"""Generate MewNook v2, a source-driven, editable Inochi2D rig.

Unlike v1, eyes are isolated using feathered elliptical alpha masks, the
face under them is reconstructed, and eyelid curves are separate meshes.
Bindings operate on named parts, not rectangular skin cut-outs.

This is a reproducible *engineering rig* from one flattened original scene
illustration. A professional model still needs painted occluded areas and
manual mesh topology in Inochi Creator.
"""
from __future__ import annotations

import io
import json
import math
import struct
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'public/assets/rooms/day/character.webp'
MODEL = ROOT / 'public/inochi2d-test/models/MewNook-v2.inx'
DEBUG = ROOT / 'public/inochi2d-test/models/debug'
NULL = 4294967295
source = np.asarray(Image.open(SOURCE).convert('RGBA')).copy()
H, W = source.shape[:2]

# All coordinate anchors below describe the 1086×1448 day-character artwork.
def xy(x, y):
    return round(x * W / 1086), round(y * H / 1448)

# Remove detached PNG pixels and the outer 2-pixel white matte.
alpha = source[:, :, 3].copy()
count, labels, stats, _ = cv2.connectedComponentsWithStats(
    (alpha > 24).astype(np.uint8), connectivity=8)
keep = np.zeros_like(alpha)
for idx in range(1, count):
    if stats[idx, cv2.CC_STAT_AREA] >= max(30, W * H // 15000):
        keep[labels == idx] = alpha[labels == idx]
alpha = cv2.erode(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=2)
alpha = cv2.GaussianBlur(alpha, (0, 0), 0.45)
source[:, :, 3] = alpha

# Bleed opaque pixel colors into fully transparent neighbors to avoid
# bilinear sampling picking white/black from uninitialized texels.
rgb = source[:, :, :3].copy()
opaque = alpha > 230
if np.any(opaque):
    _, indices = cv2.distanceTransformWithLabels(
        (~opaque).astype(np.uint8), cv2.DIST_L2, 3,
        labelType=cv2.DIST_LABEL_PIXEL)
    # Inpainting a 12-pixel edge band is cheap and avoids hard RGB discontinuity.
    fringe = cv2.dilate(opaque.astype(np.uint8), np.ones((25, 25), np.uint8))
    fringe = np.where((fringe > 0) & ~opaque, 255, 0).astype(np.uint8)
    rgb = cv2.inpaint(rgb, fringe, 3, cv2.INPAINT_TELEA)
source[:, :, :3] = rgb

def rotated_ellipse(cx, cy, rx, ry, angle, blur=1.3):
    mask = np.zeros((H, W), np.uint8)
    poly = cv2.ellipse2Poly(xy(cx, cy), xy(rx, ry), angle, 0, 360, 3)
    cv2.fillConvexPoly(mask, poly, 255, cv2.LINE_AA)
    return cv2.GaussianBlur(mask, (0, 0), blur)

eyes = [
    {'name': 'Left', 'cx': 392, 'cy': 500, 'rx': 62, 'ry': 36, 'angle': -20,
     'stroke': ((348, 518), (367, 504), (416, 486), (445, 481))},
    {'name': 'Right', 'cx': 535, 'cy': 409, 'rx': 61, 'ry': 36, 'angle': -20,
     'stroke': ((496, 428), (522, 415), (559, 393), (583, 387))}
]

# Repair face under eye art. Both open-eye sprites are cut from the untouched
# pixels with smooth oval alpha, not from an opaque rectangular skin patch.
removal = np.zeros((H, W), np.uint8)
for eye in eyes:
    eye['mask'] = rotated_ellipse(
        eye['cx'], eye['cy'], eye['rx'], eye['ry'], eye['angle'])
    removal = np.maximum(removal, (eye['mask'] > 5).astype(np.uint8) * 255)
removal = cv2.dilate(removal, cv2.getStructuringElement(
    cv2.MORPH_ELLIPSE, (13, 13)))
body = source.copy()
body[:, :, :3] = cv2.inpaint(source[:, :, :3], removal, 18, cv2.INPAINT_TELEA)

# A cheek-colored eyelid replaces the blue iris as the open eye contracts.
# Only the dark curved eyelash line is painted, with transparent surroundings.
def lash_sprite(eye):
    mask = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(mask)
    p0, p1, p2, p3 = eye['stroke']
    points = []
    for step in range(41):
        t = step / 40
        x = ((1 - t)**3 * p0[0] + 3 * (1 - t)**2 * t * p1[0]
             + 3 * (1 - t) * t*t * p2[0] + t**3 * p3[0])
        y = ((1 - t)**3 * p0[1] + 3 * (1 - t)**2 * t * p1[1]
             + 3 * (1 - t) * t*t * p2[1] + t**3 * p3[1])
        points.append(xy(x, y))
    width = max(2, round(W / 1086 * 4))
    d.line(points, fill=(85, 60, 89, 240), width=width, joint='curve')
    # Small outer lash, attached to the closed eyelid rather than a box.
    tip = points[-1]
    d.line((tip, xy(p3[0]+5, p3[1]-9)),
           fill=(85, 60, 89, 200), width=max(2, width-1))
    return np.asarray(mask.filter(ImageFilter.GaussianBlur(.22))).copy()

def tint_mask(mask, color):
    out = np.zeros((H, W, 4), np.uint8)
    out[:, :, :3] = color[:3]
    out[:, :, 3] = (mask.astype(np.float32) * color[3]/255).astype(np.uint8)
    return out

# Transparent, hand-authored mouth and shy blush shapes.
mouth_image = Image.new('RGBA', (W, H), (0,0,0,0))
draw = ImageDraw.Draw(mouth_image)
draw.ellipse((*xy(497, 527), *xy(529, 544)), fill=(119, 56, 91, 240))
draw.arc((*xy(499, 531), *xy(527, 544)), 5, 175, fill=(250, 159, 180, 235),
         width=max(2, round(W / 500)))
blush_image = Image.new('RGBA',(W,H),(0,0,0,0))
draw = ImageDraw.Draw(blush_image)
for center in [(345, 546),(586, 468)]:
    x,y=xy(*center)
    draw.ellipse((x-19,y-9,x+19,y+9), fill=(245, 125, 152, 65))
blush_image = blush_image.filter(ImageFilter.GaussianBlur(max(1,W/180)))

def polygon(points, blur=1.9):
    img = Image.new('L',(W,H),0)
    d = ImageDraw.Draw(img)
    d.polygon([xy(*p) for p in points], fill=255)
    return np.asarray(img.filter(ImageFilter.GaussianBlur(blur)))

# Keep triangles small/independent. Ear/tail masks have soft edges and have
# their overlap painted into the reconstructed base to avoid visible holes.
ears = {
  'Left': polygon([(72,332),(179,295),(260,393),(247,459),(173,449),(80,386)]),
  'Right': polygon([(383,177),(484,4),(603,164),(574,222),(462,231)])
}
tail = polygon([(816,632),(886,581),(976,591),(1060,630),(1086,699),
                (1044,850),(985,941),(929,1045),(870,1013),(927,877),
                (979,740),(897,699),(841,712)])
# We cannot reliably reconstruct covered hair/chair from a flattened source.
# For these secondary parts, retain the original rest-pose pixels in base,
# and do subtle low-amplitude transforms only.
texture_nodes = []
textures = []
parameters = []
node_id = 20000
def next_id():
    global node_id
    node_id += 1
    return node_id

def add_part(name, picture, mask=None, z=0):
    rgba = np.asarray(picture).copy()
    if mask is not None:
        rgba[:, :, 3] = np.round(rgba[:, :, 3].astype(np.float32)
                                  * mask.astype(np.float32) / 255).astype(np.uint8)
    # alpha is a real organic mask; not the full rectangle.
    if rgba[:, :, 3].max() == 0: raise ValueError(name+' is empty')
    bbox = Image.fromarray(rgba).getbbox()
    l,t,r,b = bbox
    crop = Image.fromarray(rgba[t:b,l:r]).convert('RGBA')
    data = io.BytesIO()
    crop.save(data,format='PNG',optimize=True)
    textures.append(data.getvalue())
    width,height = r-l,b-t
    item = {
      'uuid':next_id(), 'name':name,'type':'Part','enabled':True,
      'zsort':-float(z), 'transform':{
        'trans':[(l+r-W)/2,(t+b-H)/2,-1.0],
        'rot':[0.,0.,0.],'scale':[1.,1.]},
      'lockToRoot':False,
      'mesh':{'verts':[-width/2,-height/2,-width/2,height/2,
                       width/2,-height/2,width/2,height/2],
              'uvs':[0,0,0,1,1,0,1,1],
              'indices':[0,2,1,2,3,1],'origin':[0,0]},
      'textures':[len(textures)-1,NULL,NULL],'blend_mode':'Normal',
      'tint':[1.,1.,1.],'screenTint':[0.,0.,0.],'emissionStrength':1.,
      'masks':[],'mask_threshold':0.5,'opacity':1.,'psdLayerPath':name
    }
    # Inox2D renders from higher zsort to lower; negative values are FRONT.
    texture_nodes.append(item)
    return item

base = add_part('Retouched body and face', body, z=0)
# These independent mesh parts are deliberately modest in range while the
# artwork's underlying occluded surfaces are unfinished.
earL = add_part('Left Cat Ear', source,ears['Left'],1)
earR = add_part('Right Cat Ear',source,ears['Right'],2)
tailPart = add_part('Cat Tail',source,tail,3)
eye_parts = {}
for i,eye in enumerate(eyes):
    eye_mask = eye['mask']
    eye_open = add_part('Eye '+eye['name']+' Iris', source,eye_mask,6+i*3)
    lid = add_part('Eye '+eye['name']+' Closed Lash',lash_sprite(eye),z=7+i*3)
    eye_parts[eye['name']] = (eye_open,lid)
mouth = add_part('Talking Mouth',np.asarray(mouth_image),z=15)
blush = add_part('Shy Blush',np.asarray(blush_image),z=16)

def param(name, bindings, limits=(-1,1), initial=0):
    # Scalar control with 3 horizontal keyforms. Use neutral 0 for idle.
    mn,mx=limits
    params=[]
    for node,property_name,keys in bindings:
        params.append({
          'node':node['uuid'],'param_name':property_name,
          'values':[[float(v),float(v)] for v in keys],
          'isSet':[[True,True] for _ in keys],
          'interpolate_mode':'Linear'})
    parameters.append({
      'uuid':next_id(),'name':name,'is_vec2':False,
      'min':[float(mn),0.],'max':[float(mx),1.],
      'defaults':[float(initial),.5],
      'axis_points':[[0.,.5,1.],[0.,1.]],
      'merge_mode':'Additive','bindings':params
    })
def bind(node,kind,values): return (node,kind,values)

for name,(eye,lid) in eye_parts.items():
    param('ParamEyeBlink'+name,[
        bind(eye,'transform.s.y',[1.0,1.0,.03]),
        bind(lid,'transform.s.y',[.002,.002,1.0])
    ],limits=(-1,1),initial=0)
param('ParamEarLeft',[bind(earL,'transform.r.z',[-.045,0,.045])])
param('ParamEarRight',[bind(earR,'transform.r.z',[.045,0,-.045])])
param('ParamTailSwing',[bind(tailPart,'transform.r.z',[-.045,0,.045])])
param('ParamBreath',[bind(base,'transform.s.y',[.995,1.,1.005])])
param('ParamBodyY',[bind(base,'transform.t.y',[-2.,0.,2.])])
param('ParamBodyZ',[bind(base,'transform.r.z',[-.002,0.,.002])])
param('ParamHeadX',[bind(eye,'transform.t.x',[-2,0,2])
                   for eye,_ in eye_parts.values()])
param('ParamHeadY',[bind(eye,'transform.t.y',[-2,0,2])
                   for eye,_ in eye_parts.values()])
param('ParamMouthOpen',[bind(mouth,'transform.s.y',[.003,.003,1.])])
param('ParamSmile',[bind(mouth,'transform.t.y',[0,0,1.])])
param('ParamSleepy',[bind(lid,'transform.s.y',[.002,.002,.45])
                     for _,lid in eye_parts.values()])
param('ParamEmbarrassed',[bind(blush,'transform.s.y',[.002,.002,1.])])

root={'uuid':next_id(),'name':'Root','type':'Node','enabled':True,
      'zsort':0.,'transform':{'trans':[0.,0.,0.],
                             'rot':[0.,0.,0.],'scale':[1.,1.]},
      'lockToRoot':False,'children':texture_nodes}
puppet={
  'meta':{'name':'MewNook Rig v2','version':'v0.8.6',
          'rigger':'MewNook rig tooling','artist':'MewNook scene illustration',
          'rights':None,'copyright':'MewNook','licenseURL':'','contact':'',
          'reference':'','thumbnailId':NULL,'preservePixels':False},
  'physics':{'pixelsPerMeter':2000.,'gravity':9.8},'nodes':root,
  'param':parameters,'automation':[],'animations':[],'groups':[]
}
payload=json.dumps(puppet,separators=(',',':'),ensure_ascii=False).encode()
binary=bytearray(b'TRNSRTS\x00')
binary+=struct.pack('>I',len(payload))+payload+b'TEX_SECT'
binary+=struct.pack('>I',len(textures))
for tex in textures:
    binary+=struct.pack('>I',len(tex))+b'\x00'+tex
MODEL.parent.mkdir(parents=True,exist_ok=True)
MODEL.write_bytes(binary)
DEBUG.mkdir(parents=True,exist_ok=True)
Image.fromarray(source).save(DEBUG/'source-alpha-clean.png')
Image.fromarray(body).save(DEBUG/'face-retouched.png')
for eye in eyes:
    Image.fromarray(eye['mask']).save(DEBUG/('eye-'+eye['name'].lower()+'-alpha.png'))
(DEBUG/'rig-report.json').write_text(json.dumps({
  'source':str(SOURCE.relative_to(ROOT)),'parts':[p['name'] for p in texture_nodes],
  'parameters':[p['name'] for p in parameters],'textureCount':len(textures),
  'modelBytes':len(binary),'notes':'Source-driven, not manually painted; eye crops are nonrectangular.',
},indent=2))
print('Created',MODEL,'bytes',len(binary),
      'parts',len(texture_nodes),'parameters',len(parameters))
