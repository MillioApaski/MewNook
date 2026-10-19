#!/usr/bin/env python3
"""Source side-head panels, masked hidden overlap and joint source-art review."""
from pathlib import Path
import json
import cv2,numpy as np
from PIL import Image,ImageDraw
from v4_image_io import atomic_png
from v4_source_io import load_group,composite,export_ora
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v10';P=R/'assets/inochi/v4/hair-source-v9'
src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];C=src[:,:,:3].astype(float);yy,xx=np.indices((H,W),dtype=np.float32)
masks={s:np.array(Image.open(O/(s+'-connector-mask.png')))>0 for s in ('left','right')};union=masks['left']|masks['right'];occupied=np.array(Image.open(O/'prior-visible-part-mask.png'))>0;occluder=np.array(Image.open(O/'prior-hair-occluder-mask.png'))>0;foreground=np.array(Image.open(O/'face-clothing-occlusion-mask.png'))>0
old=load_group(P/'MewNook-v4-outer-hair-source.ora',src.shape);prior=composite(old,src.shape);oldbase=next(a for name,a in old if name=='hidden paint and original remainder')
ref=np.array(Image.open(O/'inputs/connector-source.png').convert('RGBA'));paint=np.array(Image.open(O/'inputs/connector-hidden-generated.png').convert('RGBA').resize((1116,660),Image.Resampling.LANCZOS))
excluded=cv2.dilate(union.astype('uint8'),np.ones((9,9),np.uint8)).astype(bool);gate=cv2.resize((~excluded[175:450,350:815]).astype('uint8')*255,(1116,660));gate[ref[:,:,3]<245]=0
sift=cv2.SIFT_create(contrastThreshold=.01);k1,d1=sift.detectAndCompute(cv2.cvtColor(ref[:,:,:3],cv2.COLOR_RGB2GRAY),gate);k2,d2=sift.detectAndCompute(cv2.cvtColor(paint[:,:,:3],cv2.COLOR_RGB2GRAY),(paint[:,:,3]>245).astype('uint8')*255);matches=[a for a,b in cv2.BFMatcher().knnMatch(d1,d2,k=2) if a.distance<.75*b.distance];p=np.float32([k1[m.queryIdx].pt for m in matches]);q=np.float32([k2[m.trainIdx].pt for m in matches]);M,fit=cv2.estimateAffinePartial2D(q,p,method=cv2.RANSAC,ransacReprojThreshold=2)
assert M is not None and int(fit.sum())>=30 and .94<M[0,0]<1.06 and abs(M[0,1])<.03,'Connector background must align to preserved source features'
err=np.linalg.norm(cv2.transform(q[:,None],M)[:,0]-p,axis=1)[fit.ravel()>0]/2.4;assert np.percentile(err,95)<1
alpha=paint[:,:,3].astype(np.float32)/255;wa=cv2.warpAffine(alpha,M,(1116,660));wr=cv2.warpAffine(paint[:,:,:3].astype(np.float32)*alpha[:,:,None],M,(1116,660));rgb=np.divide(wr,wa[:,:,None],out=np.zeros_like(wr),where=wa[:,:,None]>1e-6);reg=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);atomic_png(Image.fromarray(reg),O/'registered-connector-hidden.png');under=src.copy();under[175:450,350:815]=np.array(Image.fromarray(reg).resize((465,275),Image.Resampling.LANCZOS))
texture=np.array(Image.open(O/'inputs/connector-overlap-generated.png').convert('RGBA').resize((465,275),Image.Resampling.LANCZOS));assert texture[:,:,3].min()>250 and texture[:,:,:3].mean(2).min()>130;hidden_paint=np.zeros_like(src);hidden_paint[175:450,350:815]=texture
clearance=cv2.dilate(union.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)&~occupied&~foreground;base=oldbase.copy();base[clearance]=under[clearance];atomic_png(Image.fromarray(base),O/'connector-hidden-base.png')
parts={};counts={};core_masks={};hidden_masks={}
for side,mask in masks.items():
 core=cv2.erode(mask.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)&(src[:,:,3]>240);assert core.any()
 _,labels=cv2.distanceTransformWithLabels((~core).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);F=C[core][np.maximum(labels-1,0)];B=under[:,:,:3].astype(float);v=F-B;delta=C-B;a=np.clip((delta*v).sum(2)/np.maximum((v*v).sum(2),1),0,1);domain=cv2.dilate(mask.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)&~occupied&~foreground;a[~domain]=0;a[core]=1;rgb=F.copy();rgb[core]=C[core]
 exterior=domain&(under[:,:,3]<32);a[exterior]=src[exterior,3]/255;rgb[exterior]=C[exterior]
 part=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(a*255).astype('uint8')]);part[part[:,:,3]==0,:3]=0
 hidden=cv2.dilate(mask.astype('uint8'),np.ones((11,11),np.uint8)).astype(bool)&occluder&~mask&~foreground;hidden_masks[side]=hidden
 patch=hidden_paint.copy();patch[:,:,3]=np.where(hidden,patch[:,:,3],0);complete=Image.fromarray(part);complete.alpha_composite(Image.fromarray(patch));part=np.array(complete);assert np.array_equal(part[core,:3],src[core,:3]);core_masks[side]=core;counts[side]=int(core.sum());parts[side]=part
 atomic_png(Image.fromarray(part),O/(side+'-connector-full.png'));image=Image.fromarray(part);box=image.getbbox();atomic_png(image.crop(box),O/(side+'-connector-working.png'));atomic_png(Image.fromarray(hidden.astype('uint8')*255),O/(side+'-hidden-margin-mask.png'))
# All interpolation uses premultiplied alpha; front face/clothing clips per frame.
def warp(a,shift,gain,clip=False):
 alpha=a[:,:,3].astype(np.float32)/255;ma=cv2.remap(alpha,xx-shift*gain,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);mr=cv2.remap(a[:,:,:3].astype(np.float32)*alpha[:,:,None],xx-shift*gain,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rgb=np.divide(mr,ma[:,:,None],out=np.zeros_like(mr),where=ma[:,:,None]>1e-6);out=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(ma*255).astype('uint8')]);out[foreground,3]=0 if clip else out[foreground,3];return out
connector_gain=np.clip((yy-210)/150,0,1);front_gain=np.clip((yy-100)/180,0,1);moving={'original ahoge','pin','center','left','right-inner','face-frame','source crown cap','white source flick','bow','original left bow'}
fixed=[(n,a) for n,a in old if n!='hidden paint and original remainder'];cache={};front_cache={};connector_cache={}
def frame(front,left,right):
 key=(front,left,right)
 if key not in cache:
  if front not in front_cache:front_cache[front]=[(n,warp(a,front,front_gain) if n in moving and front else a) for n,a in fixed]
  new=[]
  for side,value in [('right',right),('left',left)]:
   if (side,value) not in connector_cache:connector_cache[side,value]=warp(parts[side],value,connector_gain,True)
   new.append((side+' connector',connector_cache[side,value]))
  layers=front_cache[front]+new+[('hidden paint and original remainder',base)];result=composite(layers,src.shape)
  if front==0 and left in (-4,0,4) and right in (-4,0,4):cache[key]=result
  return result
 return cache[key]
allowed=np.zeros((H,W),bool);allowed[170:455,380:820]=True
protected=np.zeros((H,W),bool);protected[270:289,514:535]=True;protected[238:259,613:634]=True;protected[306:322,575:608]=True
cases=[]
for front in (-2,0,2):
 for left in (-4,-2,0,2,4):
  for right in (-4,-2,0,2,4):
   a=frame(front,left,right);assert np.array_equal(a[protected,:3],prior[protected,:3]),'Connector or front wind changed iris/mouth core'
   if front==0:
    relevant=(a[:,:,3]>0)|(prior[:,:,3]>0);assert np.array_equal(a[~allowed&relevant],prior[~allowed&relevant]),'Connector escaped intended source scope'
   cases.append([front,left,right])
neutral=frame(0,0,0);atomic_png(Image.fromarray(neutral),O/'joint-neutral.png')
# Check actual foreground pixels for connector-only motion, independent of rig claims.
for left in (-4,0,4):
 for right in (-4,0,4):assert np.array_equal(frame(0,left,right)[foreground,:3],prior[foreground,:3])
board=Image.new('RGB',(1350,1020),(40,47,65));d=ImageDraw.Draw(board)
for row,l in enumerate((-4,0,4)):
 for col,r in enumerate((-4,0,4)):
  tile=Image.fromarray(frame(0,l,r)).crop((370,175,820,455)).resize((450,280),Image.Resampling.NEAREST);board.paste(tile,(col*450,row*340+32),tile);d.text((col*450+8,row*340+8),'left '+str(l)+' / right '+str(r),fill='white')
atomic_png(board,O/'connector-motion-check.png')
matte=Image.new('RGB',(1120,650));d=ImageDraw.Draw(matte)
for i,(side,part) in enumerate(parts.items()):
 for j,color in enumerate(((245,245,249),(35,43,63))):
  tile=Image.new('RGBA',(W,H),color+(255,));tile.alpha_composite(Image.fromarray(part));tile=tile.crop((385,180,505,440) if side=='left' else (625,175,815,440));scale=min(265/tile.width,580/tile.height);tile=tile.resize((round(tile.width*scale),round(tile.height*scale)),Image.Resampling.NEAREST);x=(i*2+j)*280;matte.paste(color,(x,0,x+280,650));matte.paste(tile,(x+5,35));d.text((x+8,8),side+' source connector',fill=(130,130,140))
atomic_png(matte,O/'connector-matte-check.png')
layers=fixed+[(side+' source connector',warp(parts[side],0,connector_gain,True)) for side in ('right','left')]+[('hidden paint and original remainder',base)];export_ora(O/'MewNook-v4-connector-source.ora',src,layers,'JOINT CHECK — source panels; full hair art review and rig pending')
report={'stage':'source_connectors_static_review_not_rigged','registration':{'matches':len(matches),'inliers':int(fit.sum()),'median_native_error':float(np.median(err)),'p95_native_error':float(np.percentile(err,95)),'matrix':M.tolist()},'source_core_rgb_exact_pixels':counts,'hidden_overlap_pixels':{s:int(a.sum()) for s,a in hidden_masks.items()},'head_front_left_right_cases':cases,'iris_and_mouth_cores_unchanged':True,'connector_only_face_and_clothes_foreground_rgb_unchanged':True,'unrelated_prior_working_rgba_unchanged_when_front_fixed':True,'remaining':['Inspect new matte, hidden paint and neutral seams','Complete ear/root and fine-curl full-hair art review','Face, upright body layers and actual rig']};(O/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
