#!/usr/bin/env python3
"""Register an independently painted looking-down pose with uniform scaling."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import numpy as np,json
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/focus-head-v2';W,H=1122,1402
base=Image.open(O/'head-painted.png').convert('RGBA');base_size=base.size
# All registration is uniform. No head, face, or iris squeeze/deformation.
scale=1122/base.width*.78;anchor=(611*base.width/1122,500*base.height/700);target=(598,430)
size=tuple(round(x*scale) for x in base.size);offset=tuple(round(target[i]-anchor[i]*scale) for i in (0,1))
def register(im):
 out=Image.new('RGBA',(W,H));out.alpha_composite(im.resize(size,Image.Resampling.LANCZOS),offset);return out
full=register(base);full.save(O/'head.png')
def aligned(name):
 im=Image.open(O/name).convert('RGBA').resize(base.size,Image.Resampling.LANCZOS)
 a=np.array(base);b=np.array(im);best=(float('inf'),0,0)
 # Register unchanged crown/hair, excluding edited eye and mouth regions.
 for dy in range(-8,9):
  for dx in range(-24,25):
   aa=a[100:430:4,500:1050:4];bb=b[100-dy:430-dy:4,500-dx:1050-dx:4]
   mask=(aa[:,:,3]>250)&(bb[:,:,3]>250)
   score=np.abs(aa[:,:,:3].astype(float)-bb[:,:,:3]).mean(2)[mask].mean()
   if score<best[0]:best=(score,dx,dy)
 out=Image.new('RGBA',im.size);out.alpha_composite(im,(best[1],best[2]));return out,best[1:]
closed,blink_offset=aligned('blink-painted.png');mouth,mouth_offset=aligned('mouth-painted.png')
regions={'left':[(638,503),(675,499),(727,515),(760,533),(763,563),(715,574),(671,560),(643,542)],'right':[(834,480),(860,454),(920,443),(949,448),(952,492),(927,525),(883,537),(843,519)]}
for name,points in regions.items():
 mask=Image.new('L',base.size);ImageDraw.Draw(mask).polygon(points,fill=255)
 # Match unchanged skin at the perimeter before blending the tiny edge.
 # This never filters the surrounding face/hair or the eyelash drawing.
 a=np.array(base);c=np.array(closed);band=(np.array(mask.filter(ImageFilter.MaxFilter(11)))>0)&(np.array(mask.filter(ImageFilter.MinFilter(11)))==0)
 skin=band&(a[:,:,0]>180)&(a[:,:,0]>a[:,:,2]+4)&(c[:,:,0]>180)&(c[:,:,0]>c[:,:,2]+4)
 if skin.any():
  delta=np.median(a[:,:,:3].astype(float)[skin]-c[:,:,:3].astype(float)[skin],axis=0)
  c[:,:,:3]=np.clip(c[:,:,:3].astype(float)+delta,0,255).astype('uint8')
 patch=Image.fromarray(c);patch.putalpha(mask.filter(ImageFilter.GaussianBlur(2)));register(patch).save(O/(name+'-blink.png'))
mask=Image.new('L',base.size);ImageDraw.Draw(mask).ellipse((790,586,842,620),fill=255);mouth.putalpha(mask);register(mouth).save(O/'mouth-open.png')
(O/'manifest.json').write_text(json.dumps({'registration':{'scale':scale,'offset':offset,'uniform':True,'neck_anchor':target},'blink_input_offset':blink_offset,'mouth_input_offset':mouth_offset,'protected_head_proportions':True,'head_scale_parameter':False},indent=2)+'\n')
print(size,offset,blink_offset,mouth_offset)
