#!/usr/bin/env python3
"""Prepare an uncrossed seated repaint candidate; preserve original upper pixels."""
from pathlib import Path
import json,io,zipfile,xml.etree.ElementTree as ET
import cv2,numpy as np
from PIL import Image
from v4_image_io import atomic_png
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/pose-source-v1';O.mkdir(exist_ok=True)
src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2]
paint=np.array(Image.open(O/'inputs/upright-generated.png').convert('RGBA').resize((W,H),Image.Resampling.LANCZOS))
gate=np.zeros((H,W),np.uint8);gate[180:850,380:790]=255;sift=cv2.SIFT_create(contrastThreshold=.01)
k1,d1=sift.detectAndCompute(cv2.cvtColor(src[:,:,:3],cv2.COLOR_RGB2GRAY),gate);k2,d2=sift.detectAndCompute(cv2.cvtColor(paint[:,:,:3],cv2.COLOR_RGB2GRAY),gate)
matches=[a for a,b in cv2.BFMatcher().knnMatch(d1,d2,k=2) if a.distance<.75*b.distance];p=np.float32([k1[m.queryIdx].pt for m in matches]);q=np.float32([k2[m.trainIdx].pt for m in matches]);M,fit=cv2.estimateAffinePartial2D(q,p,method=cv2.RANSAC,ransacReprojThreshold=2)
assert M is not None and int(fit.sum())>=50 and .98<M[0,0]<1.02 and abs(M[0,1])<.01
err=np.linalg.norm(cv2.transform(q[:,None],M)[:,0]-p,axis=1)[fit.ravel()>0];assert np.percentile(err,95)<2
# Remove detached generation specks, keeping the connected character/stool.
n,labels,stats,_=cv2.connectedComponentsWithStats((paint[:,:,3]>16).astype('uint8'),8);largest=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);keep=cv2.dilate((labels==largest).astype('uint8'),np.ones((3,3),np.uint8)).astype(bool);paint[~keep]=0
alpha=paint[:,:,3].astype(np.float32)/255;wa=cv2.warpAffine(alpha,M,(W,H));rgb=cv2.warpAffine(paint[:,:,:3].astype(np.float32)*alpha[:,:,None],M,(W,H));rgb=np.divide(rgb,wa[:,:,None],out=np.zeros_like(rgb),where=wa[:,:,None]>1e-6);reg=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);atomic_png(Image.fromarray(reg),O/'registered-upright.png')
yy=np.indices((H,W))[0];blend=np.clip((yy-862)/16,0,1).astype(np.float32)
sa=src[:,:,3].astype(np.float32)/255;ga=reg[:,:,3].astype(np.float32)/255;oa=sa*(1-blend)+ga*blend;premul=src[:,:,:3]*sa[:,:,None]*(1-blend[:,:,None])+reg[:,:,:3]*ga[:,:,None]*blend[:,:,None];out=np.dstack([np.clip(np.round(np.divide(premul,oa[:,:,None],out=np.zeros_like(premul),where=oa[:,:,None]>1e-6)),0,255).astype('uint8'),np.round(oa*255).astype('uint8')]);out[:863]=src[:863];atomic_png(Image.fromarray(out),O/'upright-candidate.png');assert np.array_equal(out[:863],src[:863])
# Keep a simple editable source file; this candidate is not a bound puppet.
upper=src.copy();upper[863:]=0;lower=out.copy();lower[:863]=0
atomic_png(Image.fromarray(upper),O/'original-upper.png');atomic_png(Image.fromarray(lower),O/'upright-lower.png')
root=ET.Element('image',{'w':str(W),'h':str(H),'version':'0.0.3','name':'upright sitting source candidate, not rigged'});stack=ET.SubElement(root,'stack');ET.SubElement(stack,'layer',{'name':'Original upper body through row 862','src':'data/upper.png','opacity':'1','visibility':'visible','composite-op':'svg:src-over','x':'0','y':'0'});ET.SubElement(stack,'layer',{'name':'Repainted uncrossed lower body with baked seam','src':'data/lower.png','opacity':'1','visibility':'visible','composite-op':'svg:src-over','x':'0','y':'0'})
check=Image.fromarray(lower);check.alpha_composite(Image.fromarray(upper));actual=np.array(check);visible=out[:,:,3]>0;assert np.array_equal(actual[visible],out[visible])
archive=O/'MewNook-v4-upright-candidate.ora';tmp=archive.with_suffix('.building.ora')
with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('mimetype','image/openraster');z.writestr('stack.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True))
 for name,a in [('upper',upper),('lower',lower),('candidate',out)]:
  buf=io.BytesIO();Image.fromarray(a).save(buf,format='PNG');z.writestr('data/'+name+'.png',buf.getvalue())
 z.writestr('mergedimage.png',(O/'upright-candidate.png').read_bytes())
with zipfile.ZipFile(tmp) as z:
 assert z.testzip() is None
 for name in z.namelist():
  if name.endswith('.png'):
   with Image.open(io.BytesIO(z.read(name))) as im:im.load()
tmp.replace(archive)
report={'stage':'upright_uncrossed_source_candidate_not_rigged','canvas':[W,H],'registration':{'matches':len(matches),'inliers':int(fit.sum()),'median_native_error':float(np.median(err)),'p95_native_error':float(np.percentile(err,95)),'matrix':M.tolist()},'original_upper_rgba_exact_through_row':862,'seam_rows':[863,877],'remaining':['Review skirt and seat seam at full scale','Restore original lower hair in complete layer assembly','Separate hips, skirt, legs and stool with hidden overlap','Bind upright body and validate actual motions']};(O/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
