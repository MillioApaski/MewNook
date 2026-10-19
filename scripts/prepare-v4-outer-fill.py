#!/usr/bin/env python3
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from v4_image_io import atomic_png
O=Path(__file__).resolve().parents[1]/'assets/inochi/v4/hair-source-v9'
left=Image.open(O/'left-outer-full.png').convert('RGBA');left.alpha_composite(Image.open(O/'right-outer-full.png').convert('RGBA'));a=np.array(left);body=np.array(Image.open(O/'foreground-body-occlusion-mask.png'))>0;a[body]=0
union=np.maximum(np.array(Image.open(O/'left-outer-mask.png')),np.array(Image.open(O/'right-outer-mask.png')))>0
hidden=cv2.dilate(union.astype('uint8'),np.ones((21,21),np.uint8)).astype(bool)&body
atomic_png(Image.fromarray(hidden.astype('uint8')*255),O/'hair-under-body-fill-mask.png')
atomic_png(Image.fromarray(a).crop((120,330,1010,1010)).resize((1068,816)),O/'inputs/outer-hair-materials.png')
guide=a.copy();guide[hidden]=[235,35,160,255];atomic_png(Image.fromarray(guide).crop((120,330,1010,1010)).resize((1068,816)),O/'inputs/hidden-hair-fill-guide.png')
print('Hidden hair target pixels',int(hidden.sum()))

wide=cv2.dilate(union.astype('uint8'),np.ones((81,81),np.uint8)).astype(bool)&body
guide=a.copy();guide[wide]=[235,35,160,255];atomic_png(Image.fromarray(guide).crop((120,330,1010,1010)).resize((1068,816)),O/'inputs/wide-hidden-hair-guide.png')
