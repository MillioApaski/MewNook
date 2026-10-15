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
from mewnook_face_art import build_face_mouth_art

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

# Mouth correction is authored from the actual tilted original artwork,
# not a front-facing ellipse positioned by screen-space guesses.
body,mouth_art,mouth_frame=build_face_mouth_art(source,body)

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
    width = max(4, round(W / 1086 * 6))
    d.line(points, fill=(79, 54, 85, 255), width=width, joint='curve')
    # Closed lashes must remain visible when the iris is entirely covered.
    d.line(points[5:36], fill=(118, 81, 113, 240),
           width=max(2,width//2),joint='curve')
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

# Neutral smile is recovered from source pixels; new A/B/yawn mouths use the
# same slanted facial coordinate system (see mewnook_face_art.py).
blush_image = Image.new('RGBA',(W,H),(0,0,0,0))
draw = ImageDraw.Draw(blush_image)
for center in [(345, 546),(586, 468)]:
    x,y=xy(*center)
    draw.ellipse((x-22,y-10,x+22,y+10), fill=(242, 122, 152, 148))
    for dx in (-13,0,13):
        draw.line((x+dx-5,y+4,x+dx+3,y-5),fill=(229,107,140,120),
                  width=max(2,round(W/600)))
blush_image = blush_image.filter(ImageFilter.GaussianBlur(max(.7,W/700)))

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
    # Inox2D Normal blend uses GL_ONE, GL_ONE_MINUS_SRC_ALPHA.
    # Store premultiplied RGB. Without this, alpha=0 pixels still contribute
    # their white source color and create rectangular opaque ghost patches.
    sub = rgba[t:b,l:r].copy()
    sub[:, :, :3] = ((sub[:, :, :3].astype(np.uint16)
        * sub[:, :, 3:4].astype(np.uint16) + 127) // 255).astype(np.uint8)
    crop = Image.fromarray(sub,'RGBA')
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

# The base no longer keeps an unmoving full-strength duplicate of each ear.
# Preserve ~10% at edges to avoid pinholes during rotation. The ear art
# remains real textured parts with a clearly visible, separate reaction.
for ear_mask in ears.values():
    factor=ear_mask.astype(np.float32)/255
    body[:,:,3]=np.clip(body[:,:,3].astype(np.float32)*(1-.93*factor),0,255).astype(np.uint8)

base = add_part('Retouched body and face', body, z=0)
# These independent mesh parts are deliberately modest in range while the
# artwork's underlying occluded surfaces are unfinished.
earL = add_part('Left Cat Ear', source,ears['Left'],1)
earR = add_part('Right Cat Ear',source,ears['Right'],2)
tailPart = add_part('Cat Tail',source,tail,3)
eye_parts = {}
for i,eye in enumerate(eyes):
    iris=add_part('Eye '+eye['name']+' Iris',source,eye['mask'],z=6+i*5)
    # Skin-colored upper eyelid closes OVER the fixed iris. The eye itself is
    # never squeezed in the Y axis; this fixes the "eye disappears vertically"
    # regression. The cover contains the reconstructed face under the iris.
    cover=add_part('Eye '+eye['name']+' Upper Lid',body,eye['mask'],z=7+i*5)
    # A separate half-closed upper lid gives drowsy mode a persistent pose.
    drowsy=add_part('Eye '+eye['name']+' Drowsy Lid',body,eye['mask'],z=8+i*6)
    sleepy_lash=add_part('Eye '+eye['name']+' Drowsy Lash',lash_sprite(eye),z=9+i*6)
    lash=add_part('Eye '+eye['name']+' Closed Lash',lash_sprite(eye),z=10+i*6)
    eye_parts[eye['name']]=(iris,cover,drowsy,sleepy_lash,lash)
neutral=add_part('Neutral Smile',mouth_art['Neutral Smile'],z=20)
mouth_a=add_part('Talking Mouth A',mouth_art['Talking Mouth A'],z=21)
mouth_b=add_part('Talking Mouth B',mouth_art['Talking Mouth B'],z=22)
sleepy_mouth=add_part('Sleepy Mouth',mouth_art['Sleepy Mouth'],z=23)
blush=add_part('Shy Blush',np.asarray(blush_image),z=24)

def param(name, bindings, limits=(-1,1), initial=0):
    # Scalar control with 3 horizontal keyforms. Use neutral 0 for idle.
    mn,mx=limits
    params=[]
    steps=len(bindings[0][2])
    if steps<3 or any(len(keys)!=steps for _,_,keys in bindings):
        raise ValueError('Parameter bindings must have matching 3+ keyforms: '+name)
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
      'axis_points':[[i/(steps-1) for i in range(steps)],[0.,1.]],
      'merge_mode':'Additive','bindings':params
    })
def bind(node,kind,values): return (node,kind,values)

for name,(iris,cover,drowsy,sleepy_lash,lash) in eye_parts.items():
    # -1 and 0: open. +1: fully covered by skin + closed eyelash.
    # Translate the eyelid from above the eye to its final centered position
    # while expanding downwards. This is occlusion, not iris compression.
    param('ParamEyeBlink'+name,[
        bind(cover,'transform.s.y',[.008,.008,1.]),
        bind(cover,'transform.t.y',[-28,-28,0]),
        bind(lash,'transform.s.y',[.002,.002,1.])
    ])
param('ParamEarLeft',[bind(earL,'transform.r.z',[-.27,0,.27])])
param('ParamEarRight',[bind(earR,'transform.r.z',[.27,0,-.27])])
param('ParamTailSwing',[bind(tailPart,'transform.r.z',[-.085,0,.085])])
param('ParamBreath',[bind(base,'transform.s.y',[.995,1.,1.005])])
param('ParamBodyY',[bind(base,'transform.t.y',[-2.,0.,2.])])
param('ParamBodyZ',[bind(base,'transform.r.z',[-.002,0.,.002])])
param('ParamHeadX',[bind(iris,'transform.t.x',[-2,0,2])
                   for iris,_,_,_,_ in eye_parts.values()])
param('ParamHeadY',[bind(iris,'transform.t.y',[-2,0,2])
                   for iris,_,_,_,_ in eye_parts.values()])
# At 0 show the EXACT original tilted smile. Between 0.5 and 1 show
# locally oriented speech poses A and B. No unrotated open ellipse.
param('ParamMouthOpen',[
    bind(neutral,'transform.s.y',[1.,1.,1.,.003,.003]),
    bind(mouth_a,'transform.s.y',[.003,.003,.003,1.,.003]),
    bind(mouth_b,'transform.s.y',[.003,.003,.003,.003,1.])
])
param('ParamSmile',[bind(neutral,'transform.t.y',[.5,0.,-.5])])
param('ParamSleepy',[
    binding
    for _,(_,_,drowsy,sleepy_lash,_) in eye_parts.items()
    for binding in (
        bind(drowsy,'transform.s.y',[.008,.008,.56]),
        bind(drowsy,'transform.t.y',[-26,-26,-11]),
        bind(sleepy_lash,'transform.s.y',[.002,.002,.74])
    )
] + [
    bind(neutral,'transform.s.x',[1.,1.,.003]),
    bind(sleepy_mouth,'transform.s.y',[.003,.003,1.])
])
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
  'modelBytes':len(binary),'faceFrame':mouth_frame,
  'notes':'Source-derived original angled mouth, A/B speech, separate drowsy mouth; eye crops remain nonrectangular.',
},indent=2))
print('Created',MODEL,'bytes',len(binary),
      'parts',len(texture_nodes),'parameters',len(parameters))
