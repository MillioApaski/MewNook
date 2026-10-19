#!/usr/bin/env python3
"""Refine source iris mattes and painted whites; no replacement eye graphics."""
from pathlib import Path
import json
import cv2,numpy as np
from PIL import Image,ImageDraw
from v4_image_io import atomic_png
from v4_source_io import load_group,composite,export_ora
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/face-source-v5';O.mkdir(exist_ok=True);V1=R/'assets/inochi/v4/face-source-v1';V2=R/'assets/inochi/v4/face-source-v2';H10=R/'assets/inochi/v4/hair-source-v10'
src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];C=src[:,:,:3].astype(float);yy,xx=np.indices((H,W),dtype=np.float32)
m1=json.loads((V1/'manifest.json').read_text());m2=json.loads((V2/'manifest.json').read_text())
def part(folder,manifest,key):
 entries=manifest.get('parts',manifest.get('working_parts',[]));entry=next(p for p in entries if p['file']==key+'.png');im=np.array(Image.open(folder/entry['file']).convert('RGBA'));a=np.zeros_like(src);x,y=entry['offset'];a[y:y+im.shape[0],x:x+im.shape[1]]=im;return a
old=load_group(H10/'MewNook-v4-connector-source.ora',src.shape);prior=composite(old,src.shape);oldbase=next(a for name,a in old if name=='hidden paint and original remainder');fixed=[(n,a) for n,a in old if n not in ['hidden paint and original remainder','stationary eye corner']]
# These contours are opacity mattes following the original opening, never drawings.
contours={'left':[(491,289),(494,286),(497,284),(500,282),(504,278),(508,273),(510,271),(519,268),(529,268),(538,271),(543,275),(545,280),(544,285),(541,290),(534,294),(526,299),(519,300),(511,301),(503,299),(496,294),(491,289)],'right':[(600,251),(601,245),(606,240),(612,236),(621,233),(632,233),(642,236),(650,239),(653,245),(651,251),(646,257),(639,262),(631,266),(622,269),(613,266),(607,262),(603,257)]}
parts={};reports={};all_regions=np.zeros((H,W),bool);core_masks={}
for side,points in contours.items():
 a=np.zeros((H,W),np.uint8);cv2.fillPoly(a,[np.array(points,np.int32)],255);aperture=a>0
 region=np.zeros((H,W),np.uint8);cv2.fillPoly(region,[np.array(m1['matte_contours']['eye-'+side],np.int32)],255);region=cv2.dilate(region,np.ones((7,7),np.uint8))>0;all_regions|=region
 upper=part(V1,m1,side+'-upper-lashes')[:,:,3]>0;lower=part(V1,m1,side+'-lower-lid')[:,:,3]>0
 top=np.zeros(W,np.float32);bottom=np.zeros(W,np.float32)
 for x in range(W):
  ys=np.flatnonzero(aperture[:,x]);top[x]=ys.min() if len(ys) else 0;bottom[x]=ys.max() if len(ys) else 0
 # A threshold had assigned dark iris rim stems to the lashes. Keep actual
 # upper/lower lid borders and let the iris own deep pixels inside the opening.
 valid_x=np.flatnonzero(top>0);top=np.interp(np.arange(W),valid_x,top[valid_x]);bottom=np.interp(np.arange(W),valid_x,bottom[valid_x])
 oldvisible=part(V2,m2,side+'-iris-visible')[:,:,3]>0
 neighbourhood=cv2.dilate(oldvisible.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)
 upper&=~neighbourhood|(yy<=top[None,:]+1);lower&=~neighbourhood|(yy>=bottom[None,:]-1)
 blue=(C[:,:,2]-C[:,:,0]>18)&(C[:,:,2]-C[:,:,1]>8)
 dark_iris_rim=(C.mean(2)<155)&(C[:,:,2]-C[:,:,0]>8)
 visible=(oldvisible|(neighbourhood&(blue|dark_iris_rim)&~upper&~lower))&aperture
 # The old lower-lid threshold had included pale original iris edge sectors.
 lower&=~visible;upper&=~visible
 sclera=part(V2,m2,side+'-sclera-underpaint');clearance=cv2.dilate(visible.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)&aperture&~upper&~lower
 support=src.copy();support[clearance,:3]=sclera[clearance,:3];support[:,:,3]=np.where(region,255,0).astype('uint8');support[~region,:3]=0
 # Original source RGB is exact in the iris core; only edge RGB is unmixed.
 core=cv2.erode(visible.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool);assert core.any();_,labels=cv2.distanceTransformWithLabels((~core).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);F=C[core][np.maximum(labels-1,0)];B=support[:,:,:3].astype(float);v=F-B;delta=C-B
 alpha=np.clip((delta*v).sum(2)/np.maximum((v*v).sum(2),1),0,1)
 minimum=np.maximum(np.where(delta>0,delta/np.maximum(255-B,1),0).max(2),np.where(delta<0,-delta/np.maximum(B,1),0).max(2))
 alpha=np.where(visible,np.maximum(alpha,np.maximum(minimum,.25)),0);alpha[core]=1;alpha=np.round(alpha*255)/255
 rgb=np.divide(C-(1-alpha[:,:,None])*B,alpha[:,:,None],out=np.zeros_like(C),where=alpha[:,:,None]>0);rgb=np.clip(np.round(rgb),0,255).astype('uint8')
 iris=np.dstack([rgb,np.round(alpha*255).astype('uint8')]);iris[core,:3]=src[core,:3]
 hidden=part(V2,m2,side+'-iris-underpaint')
 hidden_mask=(hidden[:,:,3]>0)&~visible&(yy<top[None,:]+2)&(yy<(282 if side=='left' else 250));iris[hidden_mask]=hidden[hidden_mask]
 clip=aperture&~upper&~lower
 # Preserve unmodified original lid/skin pixels around the painted iris hole.
 parts[side]={'support':support,'iris':iris,'clip':clip,'visible':visible,'core':core}
 core_masks[side]=core
 for name,array in [('eye-support',support),('iris',iris)]:
  atomic_png(Image.fromarray(array),O/(side+'-'+name+'-full.png'));im=Image.fromarray(array);box=im.getbbox();atomic_png(im.crop(box),O/(side+'-'+name+'-working.png'))
 atomic_png(Image.fromarray(clip.astype('uint8')*255),O/(side+'-aperture-mask.png'));atomic_png(Image.fromarray(core.astype('uint8')*255),O/(side+'-iris-core-mask.png'))
 for label,mask in [('eye-region',region),('upper-lid-domain',upper),('lower-lid-domain',lower),('iris-visible',visible),('opening',aperture)]:atomic_png(Image.fromarray(mask.astype('uint8')*255),O/(side+'-'+label+'-mask.png'))
 remaining_dark=clip&neighbourhood&(support[:,:,:3].mean(2)<155)&(support[:,:,2].astype(int)-support[:,:,0].astype(int)>8);assert not remaining_dark.any(),'Old iris rim remains in stationary eye support'
 reports[side]={'stationary_iris_rim_residue_pixels':int(remaining_dark.sum()),'source_visible_iris_pixels':int(visible.sum()),'source_core_rgb_exact_pixels':int(core.sum()),'painted_white_clearance_pixels':int(clearance.sum()),'hidden_iris_pixels':int(hidden_mask.sum())}

def moved_iris(side,dx,dy):
 p=parts[side];a=p['iris'];alpha=a[:,:,3].astype(np.float32)/255;wa=cv2.remap(alpha,xx-dx,yy-dy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);wr=cv2.remap(a[:,:,:3].astype(np.float32)*alpha[:,:,None],xx-dx,yy-dy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rgb=np.divide(wr,wa[:,:,None],out=np.zeros_like(wr),where=wa[:,:,None]>1e-6);out=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);out[~p['clip'],3]=0;return out

def layers(dx,dy):
 return fixed+[(s+' source iris',moved_iris(s,dx,dy)) for s in ('right','left')]+[(s+' eye support',parts[s]['support']) for s in ('right','left')]+[('hidden paint and original remainder',oldbase)]
neutral=composite(layers(0,0),src.shape);error={};cases=[]
for side,p in parts.items():
 assert np.array_equal(p['iris'][p['core'],:3],src[p['core'],:3]);error[side]=float(np.abs(neutral[p['visible'],:3].astype(float)-prior[p['visible'],:3]).mean())
 assert error[side]<3,'Neutral iris reconstruction changed too much'
for dx in (-2,-1,0,1,2):
 for dy in (-2,-1,0,1,2):
  frame=composite(layers(dx,dy),src.shape);relevant=(frame[:,:,3]>0)|(prior[:,:,3]>0);assert np.array_equal(frame[~all_regions&relevant],prior[~all_regions&relevant]),'Gaze modified pixels outside eye regions';cases.append([dx,dy])
atomic_png(Image.fromarray(neutral),O/'joint-neutral.png');board=Image.new('RGB',(1260,690),(235,236,242));d=ImageDraw.Draw(board)
for row,dy in enumerate((-2,0,2)):
 for col,dx in enumerate((-2,0,2)):
  frame=Image.fromarray(composite(layers(dx,dy),src.shape));tile=frame.crop((475,210,675,315)).resize((400,210),Image.Resampling.NEAREST);board.paste(tile,(col*420+10,row*230+20));d.text((col*420+10,row*230+4),'gaze '+str(dx)+', '+str(dy),fill=(30,30,35))
atomic_png(board,O/'gaze-motion-check.png');export_ora(O/'MewNook-v4-eye-source.ora',src,layers(0,0),'JOINT CHECK — source irises; lids, mouth and rig pending')
report={'stage':'source_eye_mattes_and_gaze_not_blink_or_rig','sides':reports,'neutral_visible_iris_rgb_mean_error_against_prior':error,'gaze_cases':cases,'outside_eye_regions_prior_visible_rgba_unchanged':True,'remaining':['Inspect pupil seams, white openings and gaze extremes','Natural eyelid closure and brow/face/mouth work','Upright body layers and actual binding']};(O/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
