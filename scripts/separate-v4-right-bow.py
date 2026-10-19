#!/usr/bin/env python3
from pathlib import Path
import json,cv2,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v6';src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2]
C=src[:,:,:3].astype(float);roi=np.zeros((H,W),bool);roi[135:322,689:820]=True
seed=roi&(C[:,:,2]-C[:,:,0]>20)&(C[:,:,2]-C[:,:,1]>8)&(C[:,:,0]<110)&(src[:,:,3]>100)
n,labels,stats,_=cv2.connectedComponentsWithStats(seed.astype('uint8'),8);valid=np.flatnonzero(stats[:,cv2.CC_STAT_AREA]>15);valid=valid[valid!=0];seed=np.isin(labels,valid)
ref=np.array(Image.open(O/'inputs/right-bow-source.png').convert('RGBA'));paint=np.array(Image.open(O/'inputs/bow-and-flick-hidden-generated.png').convert('RGBA').resize((800,1025),Image.Resampling.LANCZOS))
gate=cv2.resize((~cv2.dilate(seed.astype('uint8'),np.ones((9,9),np.uint8)).astype(bool))[130:335,660:820].astype('uint8')*255,(800,1025));gate[ref[:,:,3]<200]=0
sift=cv2.SIFT_create(contrastThreshold=.01)
def fit(target_image,origin_image,target_gate):
 k1,d1=sift.detectAndCompute(cv2.cvtColor(target_image[:,:,:3],cv2.COLOR_RGB2GRAY),target_gate);k2,d2=sift.detectAndCompute(cv2.cvtColor(origin_image[:,:,:3],cv2.COLOR_RGB2GRAY),None)
 good=[a for a,b in cv2.BFMatcher().knnMatch(d1,d2,k=2) if a.distance<.75*b.distance];target=np.float32([k1[g.queryIdx].pt for g in good]);origin=np.float32([k2[g.trainIdx].pt for g in good]);M,inside=cv2.estimateAffinePartial2D(origin,target,method=cv2.RANSAC,ransacReprojThreshold=2)
 assert M is not None and inside.sum()>25,'Bow hidden paint registration needs review'
 err=np.linalg.norm(cv2.transform(origin[:,None],M)[:,0]-target,axis=1)[inside.ravel()>0]/5
 return M,{'inliers':int(inside.sum()),'matches':len(good),'median_native_error':float(np.median(err)),'p95_native_error':float(np.percentile(err,95))}
# A second local edit has too few direct source matches. Register through its
# first painted parent, validating both fits rather than relaxing the threshold.
parent=np.array(Image.open(O/'inputs/bow-hidden-generated.png').convert('RGBA').resize((800,1025),Image.Resampling.LANCZOS))
M1,stage1=fit(ref,parent,gate)
parent_gate=(parent[:,:,3]>200).astype('uint8')*255;parent_gate[350:520]=0
M2,stage2=fit(parent,paint,parent_gate)
M=(np.vstack([M1,[0,0,1]])@np.vstack([M2,[0,0,1]]))[:2]

pa=paint[:,:,3].astype(np.float32)/255;wa=cv2.warpAffine(pa,M,(800,1025));wr=cv2.warpAffine(paint[:,:,:3].astype(np.float32)*pa[:,:,None],M,(800,1025));wr=np.divide(wr,wa[:,:,None],out=np.zeros_like(wr),where=wa[:,:,None]>1e-6);reg=np.dstack([np.clip(np.round(wr),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);Image.fromarray(reg).save(O/'registered-bow-hidden.png');small=np.array(Image.fromarray(reg).resize((160,205),Image.Resampling.LANCZOS));paintfull=src.copy();paintfull[130:335,660:820]=small
# Keep separate foreground white hairs out of the blue material.
domain=cv2.dilate(seed.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)&roi&(C[:,:,2]-C[:,:,0]>7)
B=paintfull[:,:,:3].astype(float);_,nearest=cv2.distanceTransformWithLabels((~seed).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);F=C[seed][np.maximum(nearest-1,0)];v=F-B;delta=C-B
alpha=np.clip((delta*v).sum(2)/np.maximum((v*v).sum(2),1),0,1)
minimum=np.maximum(np.where(delta>0,delta/np.maximum(255-B,1),0).max(2),np.where(delta<0,-delta/np.maximum(B,1),0).max(2))
alpha=np.where(domain,alpha,0);alpha[seed]=1
# Outside the original opaque silhouette use original alpha and RGB directly.
edge=domain&(src[:,:,3]<250);alpha[edge]=src[edge,3]/255
rgb=F.copy();rgb[seed]=C[seed];rgb[edge&(C[:,:,0]<110)]=C[edge&(C[:,:,0]<110)]
part=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(alpha*255).astype('uint8')]);part[part[:,:,3]==0,:3]=0
# Complete the blue material hidden by the original white flick, only where the registered paint is blue.
fm=np.array(Image.open(O/'ribbon-flick-mask.png')).astype(float)/255
fp=np.array(Image.open(O/'registered-flick-hidden.png').convert('RGBA').resize((100,70),Image.Resampling.LANCZOS));fill=np.zeros_like(src);fill[175:245,660:760]=fp
fr=fill[:,:,:3].astype(int);hidden=(fm>.01)&(fr[:,:,2]-fr[:,:,0]>20)&(fr[:,:,0]<130)&(C.mean(2)>160)
fill[:,:,3]=np.where(hidden,np.round(fm*255),0).astype('uint8')
complete=Image.fromarray(part);complete.alpha_composite(Image.fromarray(fill));part=np.array(complete)
Image.fromarray(fill).save(O/'bow-under-flick-painted.png')
Image.fromarray(part).save(O/'right-bow-full.png');im=Image.fromarray(part);bounds=im.getbbox();im.crop(bounds).save(O/'right-bow-working.png');assert np.array_equal(part[seed&~edge,:3],src[seed&~edge,:3])
base=src.copy();coverage=domain|(np.array(Image.open(O/'ribbon-flick-mask.png'))>0);base[coverage]=paintfull[coverage];Image.fromarray(base).save(O/'bow-hidden-base.png');Image.fromarray(domain.astype('uint8')*255).save(O/'bow-domain.png')
yy,xx=np.indices((H,W),dtype=np.float32);frames={}
for shift in (-4,0,4):
 gain=np.clip((yy-145)/170,0,1);mx=xx-shift*gain;al=part[:,:,3].astype(np.float32)/255;pr=part[:,:,:3].astype(np.float32)*al[:,:,None];aa=cv2.remap(al,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=cv2.remap(pr,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=np.divide(rr,aa[:,:,None],out=np.zeros_like(rr),where=aa[:,:,None]>1e-6);moving=Image.fromarray(np.dstack([np.clip(np.round(rr),0,255).astype('uint8'),np.round(aa*255).astype('uint8')]))
 frame=Image.fromarray(base);frame.alpha_composite(moving);frames[shift]=frame
board=Image.new('RGB',(1050,650),(65,75,95));d=ImageDraw.Draw(board)
for i,shift in enumerate((-4,0,4)):
 tile=frames[shift].crop((670,130,825,340)).resize((330,447),Image.Resampling.NEAREST);board.paste(tile,(i*350+10,25),tile);d.text((i*350+10,8),f'right bow sway {shift}',fill='white')
board.save(O/'right-bow-motion-candidate.png');matte=Image.new('RGB',(700,500));d=ImageDraw.Draw(matte)
for i,color in enumerate(((245,245,249),(35,43,63))):
 tile=Image.new('RGBA',(W,H),color+(255,));tile.alpha_composite(Image.fromarray(part));tile=tile.crop((685,130,825,325)).resize((330,460),Image.Resampling.NEAREST);matte.paste(color,(i*350,0,i*350+350,500));matte.paste(tile,(i*350+10,25));d.text((i*350+10,5),'source navy matte',fill=(130,130,140))
matte.save(O/'right-bow-matte-check.png');report={'stage':'right_bow_source_matte_candidate_foreground_occlusion_pending','registration':{'method':'validated two-stage source-to-parent and parent-to-local-edit','source_parent':stage1,'parent_local_edit':stage2,'matrix':M.tolist()},'source_navy_core_rgb_exact_pixels':int((seed&~edge).sum()),'offset':list(bounds[:2]),'remaining':['Separate original fine white strand and preserve foreground occlusion','Joint bow and flick motion','Side/back hair repaint and grouping','Rig binding']};(O/'bow-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
