#!/usr/bin/env python3
"""Register painted skin to the authored face silhouette, with hidden hair underlap."""
from pathlib import Path
import json,hashlib,sys
import cv2,numpy as np
from PIL import Image,ImageDraw
from v4_source_io import export_ora
R=Path(__file__).resolve().parents[1];V=R/'assets/inochi/v4';O=V/'face-layer-rebuild-v2';O.mkdir(exist_ok=True)
scene=json.loads((V/'scene-source-v1/manifest.json').read_text());W,H=scene['canvas'];shape=(H,W,4)
e=next(p for p in scene['parts'] if p['role']=='face');native=np.zeros(shape,np.uint8);tile=np.array(Image.open(V/'scene-source-v1'/e['file']).convert('RGBA'));x,y=e['offset'];native[y:y+tile.shape[0],x:x+tile.shape[1]]=tile
paint=np.array(Image.open(V/'face-layer-rebuild-v1/face-skin-fixed.png').convert('RGBA'));old=paint.copy()
# The painted head and authored head have different silhouettes. Register
# the entire fixed texture row to row, instead of extending nearest colours.
opaque=paint[:,:,3]>250
inside=cv2.distanceTransform(opaque.astype('uint8'),cv2.DIST_L2,5)
core=inside>3
rgb=paint[:,:,:3].copy()
# Native cutouts follow individual strands. They are not a face silhouette:
# restore a continuous backing beneath them, then put authored hair above it.
domain=(native[:,:,3]>16).astype('uint8');domain[:155]=0;domain[350:]=0
points=cv2.findNonZero(domain);hull=cv2.convexHull(points)
large=np.zeros((H*4,W*4),np.uint8);cv2.fillConvexPoly(large,hull*4,255)
alpha=np.array(Image.fromarray(large).resize((W,H),Image.Resampling.LANCZOS))
alpha=np.maximum(alpha,native[:,:,3])
for side in ('left','right'):
 region=np.array(Image.open(V/'face-source-v5'/(side+'-eye-region-mask.png')))>0
 alpha[region]=255
hair=np.zeros((H,W),np.uint8)
for p in scene['parts']:
 if p['role'] not in ('front-hair','connector'):continue
 a=np.array(Image.open(V/'scene-source-v1'/p['file']).convert('RGBA'))[:,:,3];x,y=p['offset'];h,w=a.shape
 hair[y:y+h,x:x+w]=np.maximum(hair[y:y+h,x:x+w],a)
# Add only hidden overlap beneath hair; keep the visible silhouette unexpanded.
expanded=cv2.dilate(alpha,np.ones((9,9),np.uint8));under=(hair>0)&(expanded>0)
alpha[under]=np.maximum(alpha[under],expanded[under])
mapx,mapy=np.meshgrid(np.arange(W,dtype=np.float32),np.arange(H,dtype=np.float32))
available=np.flatnonzero(core.sum(1)>1)
for row in range(180,350):
 sy=int(available[np.argmin(abs(available-row))]);source=np.flatnonzero(core[sy]);target=np.flatnonzero(alpha[row]>128)
 mapy[row]=sy
 assert len(source)>1 and len(target)>1
 sl,sr=source[0],source[-1];tl,tr=target[0],target[-1]
 mapx[row]=np.clip(sl+(np.arange(W)-tl)*(sr-sl)/max(1,tr-tl),sl,sr)
rgb=cv2.remap(rgb,mapx,mapy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
fixed=np.dstack([rgb,alpha]);fixed[:180]=0;fixed[350:]=0
original= native.copy();original[180:330]=0
ramp=np.clip((350-np.arange(H))/20,0,1);fixed[:,:,3]=np.round(fixed[:,:,3]*ramp[:,None]).astype('uint8')
face=Image.fromarray(original);face.alpha_composite(Image.fromarray(fixed));face=np.array(face)
coverage=(native[:,:,3]>200);coverage[:180]=False;coverage[330:]=False
before=int((coverage&(old[:,:,3]<200)).sum());after=int((coverage&(face[:,:,3]<200)).sum());assert after==0
# Changed alpha must stay in the authored face / hidden underlap area.
assert np.array_equal(face[350:],native[350:]),'Original jaw/neck changed'
for n,a in [('registered-skin',fixed),('face-and-neck',face),('native-face-alpha',native[:,:,3]),('hidden-hair-underlap',under.astype('uint8')*255)]:Image.fromarray(a).save(O/(n+'.png'))
export_ora(O/'MewNook-registered-face.ora',face,[('Registered fixed skin',fixed),('Original neck and jaw',original)],'Fixed face registered to original silhouette')
# The chest-lock crop also carried a narrow strip of the old cheek at its
# top. Remove only those skin-colour spill pixels; retain the actual hair RGB.
lock=next(p for p in scene['parts'] if p['name']=='left source chest lock')
lock_image=np.array(Image.open(V/'scene-source-v1'/lock['file']).convert('RGBA'))
f=lock_image[:12,:,:3].astype(float);spill=(f[:,:,0]-f[:,:,2]>18)&(f[:,:,0]-f[:,:,1]>8)&(f.mean(2)>180)
lock_image[:12,:,3][spill]=0
Image.fromarray(lock_image).save(O/'left-chest-lock.png')
report={'stage':'continuous fixed face backing; whole-face silhouette registration; no blur','original_face_uncovered_pixels_before':before,'original_face_uncovered_pixels_after':after,'jaw_and_neck_unchanged_from_y':350,'hidden_underlap_pixels':int(under.sum()),'old_cheek_spill_removed_from_hair_pixels':int(spill.sum()),'canvas':[W,H],'source':'face-layer-rebuild-v1/face-skin-fixed.png','face_sha256':hashlib.sha256((O/'face-and-neck.png').read_bytes()).hexdigest()};(O/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
