#!/usr/bin/env python3
"""Original left bow and white foreground curl; hidden paint stays local."""
from pathlib import Path
import json,cv2,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v7';src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];C=src[:,:,:3].astype(float)
roi=np.zeros((H,W),bool);roi[200:390,330:415]=True;seed=roi&(C[:,:,2]-C[:,:,0]>20)&(C[:,:,2]-C[:,:,1]>8)&(C[:,:,0]<110)&(src[:,:,3]>100)
n,labels,stats,_=cv2.connectedComponentsWithStats(seed.astype('uint8'),8);valid=np.flatnonzero(stats[:,cv2.CC_STAT_AREA]>15);seed=np.isin(labels,valid[valid!=0])
ref=np.array(Image.open(O/'inputs/left-bow-source.png').convert('RGBA'));curlmask=np.array(Image.open(O/'white-curl-mask.png')).astype(float)/255
reports={}
def register(name,excluded):
 paint=np.array(Image.open(O/('inputs/'+name+'-generated.png')).convert('RGBA').resize((650,1075),Image.Resampling.LANCZOS))
 gate=cv2.resize((~cv2.dilate(excluded.astype('uint8'),np.ones((9,9),np.uint8)).astype(bool))[185:400,320:450].astype('uint8')*255,(650,1075));gate[ref[:,:,3]<200]=0
 sift=cv2.SIFT_create(contrastThreshold=.01);k1,d1=sift.detectAndCompute(cv2.cvtColor(ref[:,:,:3],cv2.COLOR_RGB2GRAY),gate);k2,d2=sift.detectAndCompute(cv2.cvtColor(paint[:,:,:3],cv2.COLOR_RGB2GRAY),None)
 good=[a for a,b in cv2.BFMatcher().knnMatch(d1,d2,k=2) if a.distance<.75*b.distance];t=np.float32([k1[g.queryIdx].pt for g in good]);s=np.float32([k2[g.trainIdx].pt for g in good]);M,inside=cv2.estimateAffinePartial2D(s,t,method=cv2.RANSAC,ransacReprojThreshold=2)
 fit_error=np.linalg.norm(cv2.transform(s[:,None],M)[:,0]-t,axis=1)[inside.ravel()>0]/5 if M is not None else np.array([100])
 accepted=M is not None and int(inside.sum())>=10 and len(np.unique(np.round(t[inside.ravel()>0],1),axis=0))>=9 and np.percentile(fit_error,95)<.4 and np.ptp(t[inside.ravel()>0,1])>500 and .97<M[0,0]<1.03 and abs(M[0,1])<.03
 if accepted:
  err=np.linalg.norm(cv2.transform(s[:,None],M)[:,0]-t,axis=1)[inside.ravel()>0]/5;report={'method':'preserved-region similarity SIFT','inliers':int(inside.sum()),'matches':len(good),'median_native_error':float(np.median(err)),'p95_native_error':float(np.percentile(err,95))}
 else:
  x=cv2.resize(cv2.cvtColor(ref[:,:,:3],cv2.COLOR_RGB2GRAY).astype(np.float32)/255,(325,538));y=cv2.resize(cv2.cvtColor(paint[:,:,:3],cv2.COLOR_RGB2GRAY).astype(np.float32)/255,(325,538));x=cv2.GaussianBlur(x,(0,0),2);y=cv2.GaussianBlur(y,(0,0),2)
  cc,T=cv2.findTransformECC(x,y,np.eye(2,3,dtype=np.float32),cv2.MOTION_TRANSLATION,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,200,1e-6),cv2.resize(gate,(325,538)),5)
  assert cc>.96 and np.linalg.norm(T[:,2])/2.5<1.5,'Hidden paint alignment requires review'
  M=cv2.invertAffineTransform(T);M[:,2]*=2;report={'method':'preserved-region constrained translation ECC','ecc':float(cc),'feature_fit_rejected':True,'translation_native_pixels':(M[:,2]/5).tolist()}
 report['matrix']=M.tolist();reports[name]=report
 a=paint[:,:,3].astype(np.float32)/255;wa=cv2.warpAffine(a,M,(650,1075));wr=cv2.warpAffine(paint[:,:,:3].astype(np.float32)*a[:,:,None],M,(650,1075));wr=np.divide(wr,wa[:,:,None],out=np.zeros_like(wr),where=wa[:,:,None]>1e-6);reg=np.dstack([np.clip(np.round(wr),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);Image.fromarray(reg).save(O/('registered-'+name+'.png'));small=np.array(Image.fromarray(reg).resize((130,215),Image.Resampling.LANCZOS));full=src.copy();full[185:400,320:450]=small;return full
under=register('bow-hidden',seed);bluepaint=register('curl-hidden',curlmask>.01)
domain=cv2.dilate(seed.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)&roi&(C[:,:,2]-C[:,:,0]>7)
# Include the full visible blue antialias footprint, including disconnected
# faint edge pixels that a seed dilation misses when the bow moves away.
blue_edge=roi&(src[:,:,3]>0)&(C[:,:,2]-C[:,:,0]>7)&(C[:,:,2]-C[:,:,1]>5)&((C[:,:,0]<160)|(src[:,:,3]<200))
domain|=blue_edge
B=under[:,:,:3].astype(float);_,near=cv2.distanceTransformWithLabels((~seed).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);F=C[seed][np.maximum(near-1,0)];v=F-B;delta=C-B;alpha=np.clip((delta*v).sum(2)/np.maximum((v*v).sum(2),1),0,1);alpha=np.where(domain,alpha,0);alpha[seed]=1
edge=domain&(src[:,:,3]<250);alpha[edge]=src[edge,3]/255;rgb=F.copy();rgb[seed]=C[seed];rgb[edge&(C[:,:,0]<110)]=C[edge&(C[:,:,0]<110)]
bow=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(alpha*255).astype('uint8')]);bow[bow[:,:,3]==0,:3]=0
# Registered hidden blue cloth fills only the white curl's occluded footprint.
bp=bluepaint[:,:,:3].astype(int);fillmask=cv2.dilate(np.round(curlmask*255).astype('uint8'),np.ones((5,5),np.uint8)).astype(float)/255;hidden=(fillmask>.01)&(bp[:,:,2]-bp[:,:,0]>20)&(bp[:,:,0]<130)&(C.mean(2)>140);fill=bluepaint.copy();fill[:,:,3]=np.where(hidden,np.round(fillmask*255),0).astype('uint8');complete=Image.fromarray(bow);complete.alpha_composite(Image.fromarray(fill));bow=np.array(complete)
assert np.array_equal(bow[seed&~edge,:3],src[seed&~edge,:3])
# Foreground white curl, rematted against original neighboring navy cloth.
core=(curlmask>.99)&(C.mean(2)>210)&(src[:,:,3]>250);_,near=cv2.distanceTransformWithLabels((~core).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);white=C[core][np.maximum(near-1,0)];navy=F;v=white-navy;delta=C-navy;alpha=np.clip((delta*v).sum(2)/np.maximum((v*v).sum(2),1),0,1)*curlmask;alpha[core]=1;rgb=white.copy();rgb[core]=C[core];exterior=(src[:,:,3]<250)&(curlmask>0);alpha[exterior]=src[exterior,3]/255*curlmask[exterior];rgb[exterior]=C[exterior]
curl=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(alpha*255).astype('uint8')]);curl[curl[:,:,3]==0,:3]=0;assert np.array_equal(curl[core,:3],src[core,:3])
clearance=cv2.dilate(domain.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)
base=src.copy();base[clearance]=under[clearance]
original_blue=roi&(C[:,:,2]-C[:,:,0]>20)&(C[:,:,0]<150)&(src[:,:,3]>100)
bc=base[:,:,:3].astype(int);old_blue=original_blue&(bc[:,:,2]-bc[:,:,0]>20)&(bc[:,:,0]<130)&(base[:,:,3]>64)
assert not old_blue.any(),'Old blue bow remained in hidden base'
for name,a in [('left-bow',bow),('white-curl',curl),('bow-hidden-base',base),('hidden-blue-under-curl',fill)]:Image.fromarray(a).save(O/(name+'-full.png'))
Image.fromarray(clearance.astype('uint8')*255).save(O/'bow-domain.png');Image.fromarray(core.astype('uint8')*255).save(O/'white-curl-core.png')
parts=[]
for name,a in [('left-bow',bow),('white-curl',curl)]:
 im=Image.fromarray(a);box=im.getbbox();im.crop(box).save(O/(name+'-working.png'));parts.append({'file':name+'-working.png','offset':list(box[:2])})
# Deep/light backgrounds reveal unwanted cloth/white fringes separately from movement.
board=Image.new('RGB',(1000,600));d=ImageDraw.Draw(board)
for row,(name,a) in enumerate([('source navy bow',bow),('source white curl',curl)]):
 for col,color in enumerate(((245,245,249),(35,43,63))):
  tile=Image.new('RGBA',(W,H),color+(255,));tile.alpha_composite(Image.fromarray(a));crop=(325,195,425,395) if row==0 else (385,205,425,310);tile=tile.crop(crop);tile.thumbnail((230,550));tile=tile.resize((230,460 if row==0 else 550),Image.Resampling.NEAREST);x=(row*2+col)*250;board.paste(color,(x,0,x+250,600));board.paste(tile,(x+10,30));d.text((x+10,8),name,fill=(130,130,140))
board.save(O/'left-bow-and-curl-matte-check.png');report={'stage':'left_bow_and_stationary_white_curl_source_materials','registration':reports,'old_visible_navy_pixels_remaining_in_original_bow_footprint':int(old_blue.sum()),'original_navy_core_rgb_exact_pixels':int((seed&~edge).sum()),'original_white_curl_core_rgb_exact_pixels':int(core.sum()),'working_parts':parts,'remaining':['Joint movement and source export verification','Long side/back hair and complete hair occlusion','Face, upright pose and actual rig']};(O/'materials-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
