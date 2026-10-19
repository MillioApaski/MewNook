#!/usr/bin/env python3
"""Source-pixel facial separation and registration of AI-painted expression patches.

No procedural replacement eyes, mouth, lashes, or skin drawing. Polygon mattes
only select source pixels. Missing facial paint is supplied as an image edit.
"""
import argparse,io,json,hashlib,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--skin',type=Path,required=True)
a=parser.parse_args()
source_path=ROOT/'assets/inochi/v4/source/pose_reference.png'
out=ROOT/'assets/inochi/v4/face-source-v1';out.mkdir(parents=True,exist_ok=True)
source=np.asarray(Image.open(source_path).convert('RGBA'));H,W=source.shape[:2]
# Selection contours surround source features, not synthetic replacement art.
contours={
 'eye-left':[(478,278),(484,267),(498,258),(516,256),(536,261),(552,273),(550,284),(538,296),(522,303),(503,302),(488,295),(478,286)],
 'eye-right':[(586,246),(590,233),(601,224),(619,216),(639,218),(658,228),(666,234),(660,248),(649,263),(634,271),(615,270),(597,260)],
 'brow-left':[(489,247),(500,238),(516,231),(531,226),(536,230),(522,235),(506,241),(494,251)],
 'brow-right':[(583,213),(597,203),(612,198),(629,197),(636,201),(621,202),(605,207),(590,217)],
 'mouth-neutral':[(568,306),(583,304),(600,300),(610,307),(607,316),(595,323),(578,325),(569,319)]
}
def polygon(points):
 m=np.zeros((H,W),np.uint8);cv2.fillPoly(m,[np.array(points,np.int32)],255);return m>0
masks={k:polygon(v) for k,v in contours.items()}
union=np.logical_or.reduce(list(masks.values()))
# Register using unchanged body, hair and silhouette, excluding facial edits.
registration_mask=(source[:,:,3]>245).astype(np.uint8)*255
registration_mask[170:365,450:690]=0
src_gray=cv2.cvtColor(source[:,:,:3],cv2.COLOR_RGB2GRAY).astype(np.float32)/255
registrations={}
def register(path,label):
 im=np.asarray(Image.open(path).convert('RGBA'))
 assert im.shape==source.shape,(label,im.shape)
 warp=np.eye(2,3,dtype=np.float32)
 gray=cv2.cvtColor(im[:,:,:3],cv2.COLOR_RGB2GRAY).astype(np.float32)/255
 score,warp=cv2.findTransformECC(src_gray,gray,warp,cv2.MOTION_AFFINE,
   (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,100,1e-6),registration_mask,5)
 aligned=cv2.warpAffine(im,warp,(W,H),flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_CONSTANT)
 registrations[label]={'correlation':float(score),'affine':warp.tolist()}
 return aligned
skin=register(a.skin,'skin-underpaint')
variants={name:register(ROOT/'assets/inochi/v4/art-review-v1'/('expression-'+name+'.png'),name)
 for name in ('closed','talking','sleepy')}
# Separate iris and lashes from the original eye pixels, not regenerated cutouts.
# Everything not confidently classified stays in the eye surround layer.
hsv=cv2.cvtColor(source[:,:,:3],cv2.COLOR_RGB2HSV)
blue=(hsv[:,:,0]>=95)&(hsv[:,:,0]<=135)&(hsv[:,:,1]>65)&(hsv[:,:,2]>80)
gray=cv2.cvtColor(source[:,:,:3],cv2.COLOR_RGB2GRAY)
layer_masks={}
for side,cy in [('left',279),('right',246)]:
 m=masks['eye-'+side];iris=(blue&m).astype(np.uint8)
 n,labels,stats,_=cv2.connectedComponentsWithStats(iris,8)
 if n>1:
  label=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);iris=(labels==label).astype(np.uint8)
  cs,_=cv2.findContours(iris,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
  cv2.drawContours(iris,cs,-1,1,-1)
 iris=iris.astype(bool)&m
 # Connected dark source pixels form eyelashes and lower lid accents.
 dark=(gray<145)&m&~iris
 yy,xx=np.indices((H,W));axis=cy-.28*(xx-(518 if side=='left' else 624))
 upper=dark&(yy<axis+2);lower=dark&~upper
 layer_masks[side+'-eye-surround']=m&~(iris|upper|lower)
 layer_masks[side+'-iris']=iris
 layer_masks[side+'-upper-lashes']=upper
 layer_masks[side+'-lower-lid']=lower
for key in ('brow-left','brow-right','mouth-neutral'):layer_masks[key]=masks[key]
# Regions are disjoint: every original pixel belongs to exactly one source layer.
occupancy=np.zeros((H,W),np.uint8)
for m in layer_masks.values():occupancy+=m
assert occupancy.max()==1,'overlapping original layer mattes'
assert np.array_equal(occupancy>0,union)

def cut(pixels,mask):
 arr=pixels.copy();arr[:,:,3]=np.where(mask,arr[:,:,3],0)
 arr[arr[:,:,3]==0,:3]=0
 return Image.fromarray(arr)
layers={name:cut(source,m) for name,m in layer_masks.items()}
remainder=cut(source,~union)
underpaint=cut(skin,union)
# Cropped PNGs retain source-canvas placement via explicit offsets.
manifest={'canvas':[W,H],'status':'facial_source_prototype_not_a_finished_full_character_rig',
 'source_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),
 'matte_contours':contours,'registration':registrations,'parts':[],
 'notes':['Source RGB pixels are copied unchanged; selection alpha partitions the facial regions.',
 'Eye-surround layers contain original sclera plus skin transition pixels, not a fully repainted independent sclera.',
 'Occluded iris/eyelash regions and individually separated front hair still need repainting.',
 'Body, hair, ears, clothes, chair and tail remain together in the original remainder layer.',
 'Generative variants are sampled only inside specified facial mattes; all exterior pixels stay original.']}
def save_layer(name,image,kind):
 box=image.getbbox();assert box,name
 path=out/(name+'.png');image.crop(box).save(path)
 manifest['parts'].append({'file':path.name,'offset':[box[0],box[1]],'size':[box[2]-box[0],box[3]-box[1]],'kind':kind})
save_layer('original-remainder',remainder,'original_pixels')
save_layer('skin-underpaint',underpaint,'image_edited_missing_skin')
for name,image in layers.items():save_layer(name,image,'original_pixels')
# Expression patches intentionally include matching surrounding paint, clipped
# to the selected region, while hair/outside pixels are preserved from source.
expression_masks={'closed':masks['eye-left']|masks['eye-right'],
 'sleepy':masks['eye-left']|masks['eye-right'],'talking':masks['mouth-neutral']}
rendered={'original':Image.fromarray(source)}
patches={}
for name,pixels in variants.items():
 m=expression_masks[name];patches[name]=cut(pixels,m)
 save_layer('paint-'+name,patches[name],'registered_image_edit_patch')
 composed=source.copy();composed[m]=pixels[m]
 assert np.array_equal(composed[~m],source[~m])
 rendered[name]=Image.fromarray(composed)
 rendered[name].save(out/('preview-'+name+'.png'))
# Neutral rebuild has to match original visible RGBA exactly, not just look close.
neutral=Image.new('RGBA',(W,H));neutral.alpha_composite(remainder)
for image in layers.values():neutral.alpha_composite(image)
n=np.array(neutral);visible=source[:,:,3]>0
assert np.array_equal(n[visible],source[visible]),'neutral rebuild changed source pixels'
manifest['validation']={'neutral_visible_rgba_exact':True,'part_count':len(manifest['parts']),
 'expression_exterior_rgba_exact':True,'visible_source_pixels':int(visible.sum())}
neutral.save(out/'neutral-rebuilt.png')
# Editable OpenRaster; separate source layers plus hidden expression groups.
stack=ET.Element('image',{'w':str(W),'h':str(H),'name':'MewNook v4 facial source v1','version':'0.0.3'})
root=ET.SubElement(stack,'stack')
ora=out/'MewNook-v4-face-source-v1.ora'
ora_bytes=io.BytesIO()
with zipfile.ZipFile(ora_bytes,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
 def ora_layer(parent,name,image,visible=True):
  box=image.getbbox();path='data/'+name+'.png';b=io.BytesIO();image.crop(box).save(b,'PNG');z.writestr(path,b.getvalue())
  ET.SubElement(parent,'layer',{'name':name,'src':path,'x':str(box[0]),'y':str(box[1]),'opacity':'1.0',
   'visibility':'visible' if visible else 'hidden','composite-op':'svg:src-over'})
 for name in ('closed','sleepy','talking'):ora_layer(root,'paint-'+name,patches[name],False)
 for name,image in reversed(list(layers.items())):ora_layer(root,name,image)
 ora_layer(root,'original-remainder',remainder)
 ora_layer(root,'skin-underpaint',underpaint,False)
 z.writestr('stack.xml',ET.tostring(stack,encoding='utf-8',xml_declaration=True))
 b=io.BytesIO();neutral.save(b,'PNG');z.writestr('mergedimage.png',b.getvalue())
 thumb=neutral.copy();thumb.thumbnail((256,256));b=io.BytesIO();thumb.save(b,'PNG');z.writestr('Thumbnails/thumbnail.png',b.getvalue())
ora.write_bytes(ora_bytes.getvalue())
# Inspection board is a layout of image crops, never newly drawn facial art.
board=Image.new('RGB',(1200,270),(233,234,240));d=ImageDraw.Draw(board)
for i,(name,image) in enumerate(rendered.items()):
 crop=image.crop((455,195,685,350));crop.thumbnail((280,330))
 crop=crop.resize((280,189),Image.Resampling.NEAREST)
 board.paste(crop,(i*300+10,55),crop)
 d.text((i*300+12,20),name,fill=(30,30,40))
board.save(out/'face-comparison.png')
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest['validation']))
print(ora)
