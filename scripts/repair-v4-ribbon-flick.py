#!/usr/bin/env python3
from pathlib import Path
import json,cv2,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v6';src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2]
mask=np.array(Image.open(O/'ribbon-flick-mask.png'));ref=np.array(Image.open(O/'inputs/ribbon-flick-source.png').convert('RGBA'));paint=np.array(Image.open(O/'inputs/flick-hidden-generated.png').convert('RGBA').resize((1000,700),Image.Resampling.LANCZOS))
gate=cv2.resize(255-cv2.dilate(mask[175:245,660:760],np.ones((7,7),np.uint8)),(1000,700));gate[ref[:,:,3]<200]=0
sift=cv2.SIFT_create(contrastThreshold=.01);k1,d1=sift.detectAndCompute(cv2.cvtColor(ref[:,:,:3],cv2.COLOR_RGB2GRAY),gate);k2,d2=sift.detectAndCompute(cv2.cvtColor(paint[:,:,:3],cv2.COLOR_RGB2GRAY),None);good=[a for a,b in cv2.BFMatcher().knnMatch(d1,d2,k=2) if a.distance<.78*b.distance]
target=np.float32([k1[g.queryIdx].pt for g in good]);origin=np.float32([k2[g.trainIdx].pt for g in good]);M,inside=cv2.estimateAffinePartial2D(origin,target,method=cv2.RANSAC,ransacReprojThreshold=3)
# Feature matching is unreliable here (only four inliers after repaint).
# Use a constrained translation on preserved broad shading; do not distort the source contour.
x=cv2.resize(cv2.cvtColor(ref[:,:,:3],cv2.COLOR_RGB2GRAY).astype(np.float32)/255,(500,350));y=cv2.resize(cv2.cvtColor(paint[:,:,:3],cv2.COLOR_RGB2GRAY).astype(np.float32)/255,(500,350))
x=cv2.GaussianBlur(x,(0,0),3);y=cv2.GaussianBlur(y,(0,0),3)
ecc_gate=cv2.resize(255-cv2.dilate(mask[175:245,660:760],np.ones((11,11),np.uint8)),(500,350))
correlation,T=cv2.findTransformECC(x,y,np.eye(2,3,dtype=np.float32),cv2.MOTION_TRANSLATION,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,250,1e-6),ecc_gate,5)
assert correlation>.97 and np.linalg.norm(T[:,2])/5<1,'Hidden paint displaced from source'
M=cv2.invertAffineTransform(T);M[:,2]*=2

pa=paint[:,:,3].astype(np.float32)/255;wa=cv2.warpAffine(pa,M,(1000,700));wr=cv2.warpAffine(paint[:,:,:3].astype(np.float32)*pa[:,:,None],M,(1000,700));wr=np.divide(wr,wa[:,:,None],out=np.zeros_like(wr),where=wa[:,:,None]>1e-6);registered=np.dstack([np.clip(np.round(wr),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);Image.fromarray(registered).save(O/'registered-flick-hidden.png')
small=np.array(Image.fromarray(registered).resize((100,70),Image.Resampling.LANCZOS));patch=src.copy();patch[175:245,660:760]=small
# Paint only the footprint that must stop carrying the old white flick.
coverage=mask.astype(float)/255;base=src.copy();base[:,:,:3]=np.round(src[:,:,:3]*(1-coverage[:,:,None])+patch[:,:,:3]*coverage[:,:,None]).astype('uint8')
# The strand lies on an opaque head/ribbon, so all pixels in its native footprint remain opaque.
C=src[:,:,:3].astype(float);B=base[:,:,:3].astype(float);delta=C-B
minimum=np.maximum(np.where(delta>0,delta/np.maximum(255-B,1),0).max(2),np.where(delta<0,-delta/np.maximum(B,1),0).max(2))
alpha=np.where(mask>0,np.maximum(mask.astype(float)/255,minimum),0)
rgb=np.divide(C-(1-alpha[:,:,None])*B,alpha[:,:,None],out=np.zeros_like(C),where=alpha[:,:,None]>1e-6)
part=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(alpha*255).astype('uint8')]);part[part[:,:,3]==0,:3]=0
Image.fromarray(base).save(O/'flick-hidden-base.png');Image.fromarray(part).save(O/'ribbon-flick-full.png');im=Image.fromarray(part);box=im.getbbox();im.crop(box).save(O/'ribbon-flick-working.png')
core=mask==255;assert np.array_equal(part[core,:3],src[core,:3])
yy,xx=np.indices((H,W),dtype=np.float32);frames={}
for shift in (-4,-2,0,2,4):
 gain=np.clip((xx-695)/48,0,1)**1.5;my=yy-shift*gain;al=part[:,:,3].astype(np.float32)/255;rgb=part[:,:,:3].astype(np.float32)*al[:,:,None];aa=cv2.remap(al,xx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=cv2.remap(rgb,xx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=np.divide(rr,aa[:,:,None],out=np.zeros_like(rr),where=aa[:,:,None]>1e-6);moving=Image.fromarray(np.dstack([np.clip(np.round(rr),0,255).astype('uint8'),np.round(aa*255).astype('uint8')]))
 frame=Image.fromarray(base);frame.alpha_composite(moving);arr=np.array(frame);outside=np.ones((H,W),bool);outside[175:235,680:750]=False;outside&=src[:,:,3]>0;assert np.array_equal(arr[outside],src[outside]);frames[shift]=frame
 frames[shift].crop((660,175,760,245)).save(O/('flick-shift-'+str(shift)+'.png'))
board=Image.new('RGB',(1200,365),(65,75,95));d=ImageDraw.Draw(board)
for i,shift in enumerate((-4,0,4)):
 tile=frames[shift].crop((670,180,755,245)).resize((390,298),Image.Resampling.NEAREST);board.paste(tile,(i*400+5,25),tile);d.text((i*400+5,8),f'original flick bend {shift}',fill='white')
board.save(O/'flick-motion-check.png');matte=Image.new('RGB',(800,330));d=ImageDraw.Draw(matte)
for i,color in enumerate(((245,245,249),(35,43,63))):
 tile=Image.new('RGBA',(W,H),color+(255,));tile.alpha_composite(Image.fromarray(part));tile=tile.crop((680,175,750,230)).resize((380,299),Image.Resampling.NEAREST);matte.paste(color,(i*400,0,i*400+400,330));matte.paste(tile,(i*400+10,20));d.text((i*400+10,4),'source hair matte',fill=(130,130,140))
matte.save(O/'flick-matte-check.png');report={'stage':'source_flick_hidden_paint_static_review','registration':{'method':'preserved-shading translation ECC; feature fit rejected','ecc':float(correlation),'translation_native_pixels':(M[:,2]/10).tolist(),'matrix':M.tolist()},'source_core_rgb_exact_pixels':int(core.sum()),'part_offset':list(box[:2]),'tested_parameters':[-4,-2,0,2,4],'unrelated_visible_rgba_exact':True,'remaining':['Inspect navy contamination and old silhouette at displacement','Separate bow and diagonal fine strand','Full side and back hair','Actual rig binding']};(O/'flick-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
