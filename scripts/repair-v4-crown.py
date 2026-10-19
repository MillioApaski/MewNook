#!/usr/bin/env python3
from pathlib import Path
import json
import cv2,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v5';A=R/'assets/inochi/v4/hair-source-v4'
src=np.array(Image.open(A/'crown-without-ahoge.png').convert('RGBA'));H,W=src.shape[:2]
ref=np.array(Image.open(O/'inputs/head-no-ahoge.png').convert('RGBA'));paint=np.array(Image.open(O/'inputs/crown-hidden-generated.png').convert('RGBA').resize((1300,880),Image.Resampling.LANCZOS))
mask=np.array(Image.open(O/'crown-mask.png'));gate=255-cv2.dilate(mask[25:245,400:725],np.ones((13,13),np.uint8));gate=cv2.resize(gate,(1300,880));gate[ref[:,:,3]<200]=0
sift=cv2.SIFT_create(contrastThreshold=.01);k1,d1=sift.detectAndCompute(cv2.cvtColor(ref[:,:,:3],cv2.COLOR_RGB2GRAY),gate);k2,d2=sift.detectAndCompute(cv2.cvtColor(paint[:,:,:3],cv2.COLOR_RGB2GRAY),None)
good=[a for a,b in cv2.BFMatcher().knnMatch(d1,d2,k=2) if a.distance<.75*b.distance]
target=np.float32([k1[g.queryIdx].pt for g in good]);origin=np.float32([k2[g.trainIdx].pt for g in good]);M,inside=cv2.estimateAffinePartial2D(origin,target,method=cv2.RANSAC,ransacReprojThreshold=2)
assert M is not None and inside.sum()>25
err=np.linalg.norm(cv2.transform(origin[:,None],M)[:,0]-target,axis=1)[inside.ravel()>0]/4
pa=paint[:,:,3].astype(np.float32)/255;wa=cv2.warpAffine(pa,M,(1300,880));wr=cv2.warpAffine(paint[:,:,:3].astype(np.float32)*pa[:,:,None],M,(1300,880));wr=np.divide(wr,wa[:,:,None],out=np.zeros_like(wr),where=wa[:,:,None]>1e-6)
registered=np.dstack([np.clip(np.round(wr),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);Image.fromarray(registered).save(O/'registered-crown-hidden.png');small=np.array(Image.fromarray(registered).resize((325,220),Image.Resampling.LANCZOS));patch=src.copy();patch[25:245,400:725]=small
# Only consume repaint in the selected crown cap and a tiny motion clearance.
coverage=mask.astype(float)/255
# Keep the originally visible ear side of the hand-traced boundary unchanged.
weight=coverage[:,:,None];sa=src[:,:,3].astype(float)/255;pa=patch[:,:,3].astype(float)/255;ba=sa*(1-coverage)+pa*coverage
br=src[:,:,:3]*sa[:,:,None]*(1-weight)+patch[:,:,:3]*pa[:,:,None]*weight;br=np.divide(br,ba[:,:,None],out=np.zeros_like(br),where=ba[:,:,None]>1e-6)
base=np.dstack([np.clip(np.round(br),0,255).astype('uint8'),np.round(ba*255).astype('uint8')]);base[coverage==0]=src[coverage==0]
Image.fromarray(base).save(O/'crown-hidden-base.png')
cap=src.copy();alpha=src[:,:,3].astype(float)/255*mask/255
# Rematte the fractional selection edge against its real repainted background.
# Merely placing a soft source selection over a soft repair creates a second line.
C=src[:,:,:3].astype(float);B=base[:,:,:3].astype(float);delta=C-B
minimum=np.maximum(np.where(delta>0,delta/np.maximum(255-B,1),0).max(2),np.where(delta<0,-delta/np.maximum(B,1),0).max(2))
interior=(src[:,:,3]>250)&(mask>0)
alpha=np.where(interior,np.maximum(mask.astype(float)/255,minimum),alpha)
rgb=np.divide(C-(1-alpha[:,:,None])*B,alpha[:,:,None],out=np.zeros_like(C),where=alpha[:,:,None]>1e-6)
rgb[~interior]=C[~interior]
cap=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(alpha*255).astype('uint8')]);cap[cap[:,:,3]==0,:3]=0;Image.fromarray(cap).save(O/'crown-full.png')
yy,xx=np.indices((H,W),dtype=np.float32);frames={}
for shift in (-3,0,3):
 gain=np.clip((105-yy)/55,0,1);mx=xx-shift*gain;alpha=cap[:,:,3].astype(np.float32)/255;rgb=cap[:,:,:3].astype(np.float32)*alpha[:,:,None];aa=cv2.remap(alpha,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=cv2.remap(rgb,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=np.divide(rr,aa[:,:,None],out=np.zeros_like(rr),where=aa[:,:,None]>1e-6);moving=Image.fromarray(np.dstack([np.clip(np.round(rr),0,255).astype('uint8'),np.round(aa*255).astype('uint8')]))
 frame=Image.fromarray(base);frame.alpha_composite(moving);frames[shift]=frame
board=Image.new('RGB',(1200,510),(70,80,100));d=ImageDraw.Draw(board)
for i,shift in enumerate((-3,0,3)):
 tile=frames[shift].crop((425,35,625,205)).resize((390,332),Image.Resampling.NEAREST);board.paste(tile,(i*400+5,25),tile);d.text((i*400+5,8),f'crown bend {shift}',fill='white')
board.save(O/'crown-motion-check.png')
report={'stage':'crown_hidden_repaint_static_candidate','registration':{'inliers':int(inside.sum()),'matches':len(good),'median_native_error':float(np.median(err)),'p95_native_error':float(np.percentile(err,95)),'matrix':M.tolist()},'tested_parameters':[-3,0,3],'remaining':['Ear seam and root overlap joint review','Full side and back hair','Actual mesh binding']};(O/'crown-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
