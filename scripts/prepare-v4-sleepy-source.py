#!/usr/bin/env python3
"""Export a tiny relaxed mouth from existing painted lip/cavity material."""
from pathlib import Path
import json,hashlib
import cv2,numpy as np
from PIL import Image
from v4_image_io import atomic_png
from v4_source_io import export_ora
root=Path(__file__).resolve().parents[1];base=root/'assets/inochi/v4/face-source-v7';out=root/'assets/inochi/v4/sleepy-source-v1';out.mkdir(exist_ok=True)
paint=np.array(Image.open(base/'mouth-open-full.png').convert('RGBA'))
skin=Image.open(base/'mouth-skin-support-full.png').convert('RGBA')
h,w=paint.shape[:2];yy,xx=np.indices((h,w),dtype=np.float32)
a=np.deg2rad(-20);cx,cy=589,315
u=(xx-cx)*np.cos(a)+(yy-cy)*np.sin(a);v=-(xx-cx)*np.sin(a)+(yy-cy)*np.cos(a)
# Shrink the real painted mouth along its own axes; preserve its rounded contour.
sx,sy=.36,.22
mx=(cx+u/sx*np.cos(a)-v/sy*np.sin(a)).astype('float32');my=(cy+u/sx*np.sin(a)+v/sy*np.cos(a)).astype('float32')
alpha=paint[:,:,3].astype('float32')/255
wa=cv2.remap(alpha,mx,my,cv2.INTER_LINEAR)
rgb=cv2.remap(paint[:,:,:3].astype('float32')*alpha[:,:,None],mx,my,cv2.INTER_LINEAR)
rgb=np.divide(rgb,wa[:,:,None],out=np.zeros_like(rgb),where=wa[:,:,None]>1e-6)
small=Image.fromarray(np.dstack((np.clip(np.round(rgb),0,255).astype('uint8'),np.round(wa*255).astype('uint8'))))
slot=skin.copy();slot.alpha_composite(small)
manifest=json.loads((base/'manifest.json').read_text());x,y=manifest['mouth_slot_offset'];sw,sh=manifest['mouth_slot_size']
atomic_png(slot.crop((x,y,x+sw,y+sh)),out/'mouth-sleepy.png')
atomic_png(small,out/'mouth-material-full.png')
export_ora(out/'MewNook-v4-sleepy-mouth.ora',np.array(slot),[('tiny original painted mouth',np.array(small)),('registered skin support',np.array(skin))],'Approved sleepy expression: tiny relaxed opening')
(out/'manifest.json').write_text(json.dumps({'slot_offset':[x,y],'slot_size':[sw,sh],'source':'face-source-v7/mouth-open-full.png','source_sha256':hashlib.sha256((base/'mouth-open-full.png').read_bytes()).hexdigest(),'axis_angle_degrees':-20,'scale':[sx,sy],'visible_mouth_bounds':small.getbbox(),'design':'2026-10-22 user-approved closed eyes and tiny relaxed mouth'},indent=2)+'\n')
print('Exported tiny source-art mouth',small.getbbox())
