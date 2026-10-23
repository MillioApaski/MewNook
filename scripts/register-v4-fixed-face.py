#!/usr/bin/env python3
"""Build fixed eye underpainting while retaining the authored face contour verbatim."""
from pathlib import Path
import json,hashlib
import cv2,numpy as np
from PIL import Image
from v4_source_io import export_ora
R=Path(__file__).resolve().parents[1];V=R/'assets/inochi/v4';O=V/'face-layer-rebuild-v3';O.mkdir(exist_ok=True)
scene=json.loads((V/'scene-source-v1/manifest.json').read_text());W,H=scene['canvas'];shape=(H,W,4)
e=next(p for p in scene['parts'] if p['role']=='face');native=np.zeros(shape,np.uint8);a=np.array(Image.open(V/'scene-source-v1'/e['file']).convert('RGBA'));x,y=e['offset'];native[y:y+a.shape[0],x:x+a.shape[1]]=a
# Use the painted eyeless study only beneath the eye materials. Never resize
# the whole face or manufacture a new outer silhouette from a convex hull.
paint=np.zeros(shape,np.uint8);paint[180:356,440:704]=np.array(Image.open(V/'face-layer-rebuild-v1/inputs/eyeless-painted.png').convert('RGBA').resize((264,176),Image.Resampling.LANCZOS))
footprints={'left':[(479,278),(489,266),(496,257),(505,251),(517,248),(528,249),(535,254),(547,263),(556,273),(556,286),(546,300),(526,307),(506,307),(489,300),(478,287)],'right':[(589,243),(593,230),(602,220),(612,214),(625,211),(637,211),(645,214),(654,216),(665,219),(674,229),(671,247),(660,260),(638,269),(617,269),(599,260),(590,251)]}
mask=np.zeros((H,W),np.uint8)
for points in footprints.values():cv2.fillPoly(mask,[np.array(points,np.int32)],255)
mask=cv2.dilate(mask,np.ones((3,3),np.uint8))>0
hair=np.zeros((H,W),np.uint8)
for p in scene['parts']:
 if p['role']!='front-hair':continue
 tile=np.array(Image.open(V/'scene-source-v1'/p['file']).convert('RGBA'))[:,:,3];x,y=p['offset'];h,w=tile.shape;hair[y:y+h,x:x+w]=np.maximum(hair[y:y+h,x:x+w],tile)
guard=cv2.dilate((hair>0).astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)
 # Eye paint must be removed even beneath semitransparent hair edges.
# The independent foreground hair remains unchanged.
face=native.copy();filled=np.zeros((H,W),bool)
for side in ('left','right'):
 aperture=np.array(Image.open(V/'face-source-v5'/(side+'-opening-mask.png')))>0
 filled|=aperture&(native[:,:,3]<255)
face[filled,3]=255
# Keep every original outline/cheek/hair pixel outside the fixed eye repair.
# Match the painted study's colour to each surrounding eye ring once at export.
for side,points in footprints.items():
 local=np.zeros((H,W),np.uint8);cv2.fillPoly(local,[np.array(points,np.int32)],255);local=cv2.dilate(local,np.ones((3,3),np.uint8)).astype(bool)&mask
 ring=cv2.dilate(local.astype('uint8'),np.ones((9,9),np.uint8)).astype(bool)&~local&~guard&(native[:,:,3]>250)
 C=native[:,:,:3].astype(float);P=paint[:,:,:3].astype(float)
 ring&=(C[:,:,0]-C[:,:,2]>10)&(C.mean(2)>185)
 delta=np.median(C[ring]-P[ring],axis=0) if ring.any() else np.zeros(3)
 rgb=np.clip(P+delta,0,255)
 distance=cv2.distanceTransform(local.astype('uint8'),cv2.DIST_L2,5);weight=np.clip(distance/3,0,1)
 # One fixed underpainting, not a skin tile swapped during blinking.
 face[local,:3]=np.round(rgb[local]*weight[local,None]+C[local]*(1-weight[local,None])).astype('uint8')
for side in ('left','right'):
 aperture=np.array(Image.open(V/'face-source-v5'/(side+'-opening-mask.png')))>0
 blue=(face[:,:,2].astype(float)-face[:,:,0]>18)&(face[:,:,2].astype(float)-face[:,:,1]>8)
 assert not (blue&aperture&(face[:,:,3]>128)).any(),'Iris colour remains in fixed skin'
unchanged=~(mask|filled)
assert np.array_equal(face[unchanged],native[unchanged]),'Native face contour changed outside eye underpainting'
assert np.array_equal(face[:,:,3][~filled],native[:,:,3][~filled]),'Face alpha silhouette changed'
# Explicit regression for both user-marked lower cheek/side-hair junctions.
for x0,y0,x1,y1 in [(470,310,540,350),(625,280,680,350)]:
 assert np.array_equal(face[y0:y1,x0:x1],native[y0:y1,x0:x1]),'Side junction contour changed'
Image.fromarray(face).save(O/'face-and-neck.png');Image.fromarray(mask.astype('uint8')*255).save(O/'fixed-eye-underpaint-mask.png');Image.fromarray(filled.astype('uint8')*255).save(O/'filled-eye-hole-mask.png')
export_ora(O/'MewNook-native-contour-face.ora',face,[('Fixed eye underpainting',np.where((mask|filled)[:,:,None],face,0)),('Native face and neck',native)],'Native contour preserved with fixed eye underpainting')
report={'stage':'native outline retained; no whole-face warp/hull or hair-order change','outside_eye_repair_rgba_exact':True,'both_side_junctions_rgba_exact':True,'alpha_exact_except_original_eye_holes':True,'eye_hole_pixels_filled':int(filled.sum()),'canvas':[W,H],'source':'scene-source-v1 native face and face-layer-rebuild-v1 painted eyeless study','face_sha256':hashlib.sha256((O/'face-and-neck.png').read_bytes()).hexdigest()};(O/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
