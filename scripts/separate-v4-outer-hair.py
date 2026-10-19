#!/usr/bin/env python3
from pathlib import Path
import json,io,zipfile,xml.etree.ElementTree as ET
import cv2,numpy as np
from PIL import Image,ImageDraw
from v4_image_io import install_atomic_png_saves
install_atomic_png_saves()
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v9';P=R/'assets/inochi/v4/hair-source-v8';src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];C=src[:,:,:3].astype(float);yy,xx=np.indices((H,W),dtype=np.float32)
masks={s:np.array(Image.open(O/(s+'-outer-mask.png')))>0 for s in ('left','right')};union=masks['left']|masks['right']
ref=np.array(Image.open(O/'inputs/outer-body-source.png').convert('RGBA'));paint=np.array(Image.open(O/'inputs/outer-hidden-generated.png').convert('RGBA').resize((1068,816),Image.Resampling.LANCZOS))
# Ignore detached generated background specks while preserving the connected subject and tail.
n,labels,stats,_=cv2.connectedComponentsWithStats((paint[:,:,3]>16).astype('uint8'),8);largest=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);keep=cv2.dilate((labels==largest).astype('uint8'),np.ones((3,3),np.uint8)).astype(bool);paint[~keep]=0
excluded=cv2.dilate(union.astype('uint8'),np.ones((15,15),np.uint8)).astype(bool);gate=cv2.resize((~excluded[330:1010,120:1010]).astype('uint8')*255,(1068,816));gate[ref[:,:,3]<245]=0
sift=cv2.SIFT_create(contrastThreshold=.01);k1,d1=sift.detectAndCompute(cv2.cvtColor(ref[:,:,:3],cv2.COLOR_RGB2GRAY),gate);k2,d2=sift.detectAndCompute(cv2.cvtColor(paint[:,:,:3],cv2.COLOR_RGB2GRAY),(paint[:,:,3]>245).astype('uint8')*255);good=[a for a,b in cv2.BFMatcher().knnMatch(d1,d2,k=2) if a.distance<.75*b.distance];t=np.float32([k1[g.queryIdx].pt for g in good]);s=np.float32([k2[g.trainIdx].pt for g in good]);M,inside=cv2.estimateAffinePartial2D(s,t,method=cv2.RANSAC,ransacReprojThreshold=2)
assert M is not None and int(inside.sum())>=30 and np.ptp(t[inside.ravel()>0,0])>300,'Outer hair hidden background registration requires review'
err=np.linalg.norm(cv2.transform(s[:,None],M)[:,0]-t,axis=1)[inside.ravel()>0]/1.2
pa=paint[:,:,3].astype(np.float32)/255;wa=cv2.warpAffine(pa,M,(1068,816));wr=cv2.warpAffine(paint[:,:,:3].astype(np.float32)*pa[:,:,None],M,(1068,816));wr=np.divide(wr,wa[:,:,None],out=np.zeros_like(wr),where=wa[:,:,None]>1e-6);reg=np.dstack([np.clip(np.round(wr),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);Image.fromarray(reg).save(O/'registered-outer-hidden.png');under=src.copy();under[330:1010,120:1010]=np.array(Image.fromarray(reg).resize((890,680),Image.Resampling.LANCZOS))
# Existing visible outfit is a foreground occluder; the chair and cat tail stay behind hair.
body_points=[(445,330),(720,330),(777,393),(792,416),(785,452),(772,500),(772,550),(780,601),(779,653),(772,703),(768,744),(783,768),(809,789),(809,818),(827,849),(843,873),(828,905),(799,928),(752,946),(755,1010),(380,1010),(446,949),(387,937),(341,919),(318,894),(335,876),(363,843),(388,818),(404,790),(364,804),(373,762),(393,741),(424,713),(429,682),(420,630),(417,574),(411,520),(405,467),(399,425),(415,396),(445,377)]
im=Image.new('L',(W,H));ImageDraw.Draw(im).polygon(body_points,fill=255);body=(np.array(im)>0)&~union&(src[:,:,3]>240)
navy=(yy>450)&(yy<960)&(xx>300)&(xx<850)&(C[:,:,0]<140)&(C[:,:,2]-C[:,:,0]>.25*np.maximum(C[:,:,2],1))&(src[:,:,3]>240);body|=navy
Image.fromarray(body.astype('uint8')*255).save(O/'foreground-body-occlusion-mask.png')
# Recover the preceding editable source rather than rebuilding old layers from screenshots.
with zipfile.ZipFile(P/'MewNook-v4-chest-hair-source.ora') as z:
 tree=ET.fromstring(z.read('stack.xml'));group=tree.find('stack').find('stack');old=[]
 for node in group:
  im=np.array(Image.open(io.BytesIO(z.read(node.get('src')))).convert('RGBA'));a=np.zeros_like(src);x,y=int(node.get('x')),int(node.get('y'));a[y:y+im.shape[0],x:x+im.shape[1]]=im;old.append((node.get('name'),a))
oldbase=next(a for name,a in old if name=='hidden paint and original remainder');base=oldbase.copy();clearance=cv2.dilate(union.astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);base[clearance]=under[clearance];base[body]=oldbase[body]
# Retain visible original tail pixels; only genuinely hidden portions use paint.
source_tail=np.array(Image.open(O/'original-cat-tail-protection-mask.png'))>0
tail=source_tail&~union;tail=cv2.erode(tail.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool);base[tail]=oldbase[tail]
# The visible hair alone has sleeve/bow notches. Consume separately painted
# ORIGINAL-style hair only in the hidden body-facing strip, never outside it.
fill_maps={};fill_reports={}
fill_path=O/'inputs/inner-hair-hidden-generated.png'
if fill_path.exists():
 target=np.array(Image.open(O/'inputs/outer-hair-materials.png').convert('RGBA'));paint_hair=np.array(Image.open(fill_path).convert('RGBA').resize((1068,816),Image.Resampling.LANCZOS))
 target_fill=np.array(Image.open(O/'hair-under-body-fill-mask.png'))>0
 for side in ('left','right'):
  for side_input in ([O/'inputs/inner-hair-extra-margin-generated.png'] if side=='left' else [fill_path])+[O/'inputs/insufficient-inner-hair-hidden.png']:
   paint_hair=np.array(Image.open(side_input).convert('RGBA').resize((1068,816),Image.Resampling.LANCZOS))
   gate=(target[:,:,3]>240).astype('uint8')*255
   if side=='left':gate[:,600:]=0
   else:gate[:,:600]=0
   origin_gate=(paint_hair[:,:,3]>240).astype('uint8')*255
   if side=='left':origin_gate[:,600:]=0
   else:origin_gate[:,:600]=0
   k1,d1=sift.detectAndCompute(cv2.cvtColor(target[:,:,:3],cv2.COLOR_RGB2GRAY),gate);k2,d2=sift.detectAndCompute(cv2.cvtColor(paint_hair[:,:,:3],cv2.COLOR_RGB2GRAY),origin_gate);matches=[a for a,b in cv2.BFMatcher().knnMatch(d1,d2,k=2) if a.distance<.75*b.distance];pt=np.float32([k1[g.queryIdx].pt for g in matches]);ps=np.float32([k2[g.trainIdx].pt for g in matches]);matrix,fit=cv2.estimateAffinePartial2D(ps,pt,method=cv2.RANSAC,ransacReprojThreshold=1.2)
   fit_error=np.linalg.norm(cv2.transform(ps[:,None],matrix)[:,0]-pt,axis=1)[fit.ravel()>0]/1.2 if matrix is not None else np.array([100])
   supported=pt[fit.ravel()>0] if fit is not None else np.empty((0,2))
   feature_accepted=matrix is not None and int(fit.sum())>=8 and len(np.unique(np.round(supported,1),axis=0))>=7 and np.ptp(supported[:,1])>400 and np.ptp(supported[:,0])>100 and np.percentile(fit_error,95)<1.0 and .94<matrix[0,0]<1.06 and abs(matrix[0,1])<.03
   alpha_report={}
   if not feature_accepted:
    # Match preserved outer silhouettes, excluding all newly filled inner strips.
    body_sheet=cv2.resize(body[330:1010,120:1010].astype('uint8'),(1068,816))
    alpha_gate=cv2.dilate((target[:,:,3]>32).astype('uint8'),np.ones((21,21),np.uint8))
    alpha_gate[cv2.dilate(body_sheet,np.ones((11,11),np.uint8))>0]=0
    # Only match the preserved OUTER side; broad new inner hair must not
    # influence alignment, including new fill over formerly empty curl gaps.
    outer_side=np.zeros_like(alpha_gate,bool)
    for row in range(816):
     xs=np.flatnonzero((target[row,:,3]>32)&((np.arange(1068)<600) if side=='left' else (np.arange(1068)>=600)))
     if len(xs):outer_side[row]=(np.arange(1068)<xs.max()-42) if side=='left' else (np.arange(1068)>xs.min()+42)
    alpha_gate[~outer_side]=0
    if side=='left':alpha_gate[:,600:]=0
    else:alpha_gate[:,:600]=0
    ta=cv2.GaussianBlur(target[:,:,3].astype(np.float32)/255,(0,0),2);ga=cv2.GaussianBlur(paint_hair[:,:,3].astype(np.float32)/255,(0,0),2)
    initial=cv2.invertAffineTransform(matrix).astype(np.float32) if matrix is not None else np.eye(2,3,dtype=np.float32)
    cc,transform=cv2.findTransformECC(ta,ga,initial,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,250,1e-6),alpha_gate*255,5)
    assert cc>.94,'Preserved outer hair silhouette changed too much'
    matrix=cv2.invertAffineTransform(transform);assert .94<matrix[0,0]<1.06 and .94<matrix[1,1]<1.06 and abs(matrix[0,1])<.04 and abs(matrix[1,0])<.04
    alpha_report={'method':'preserved outer alpha affine ECC; edited inner strip excluded','ecc':float(cc),'feature_fit_inliers':int(fit.sum()) if fit is not None else 0,'feature_fit_not_accepted':True}

   error=np.linalg.norm(cv2.transform(ps[:,None],matrix)[:,0]-pt,axis=1)[fit.ravel()>0]/1.2
   pa=paint_hair[:,:,3].astype(np.float32)/255;wa=cv2.warpAffine(pa,matrix,(1068,816));wr=cv2.warpAffine(paint_hair[:,:,:3].astype(np.float32)*pa[:,:,None],matrix,(1068,816));wr=np.divide(wr,wa[:,:,None],out=np.zeros_like(wr),where=wa[:,:,None]>1e-6);reg=np.dstack([np.clip(np.round(wr),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);Image.fromarray(reg).save(O/('registered-'+side+'-'+side_input.stem+'.png'));full=np.zeros_like(src);full[330:1010,120:1010]=np.array(Image.fromarray(reg).resize((890,680),Image.Resampling.LANCZOS));fill_maps.setdefault(side,[]).append(full)
   candidate_report=({'method':'preserved-region similarity SIFT','inliers':int(fit.sum()),'matches':len(matches),'median_native_error':float(np.median(error)),'p95_native_error':float(np.percentile(error,95))} if feature_accepted else alpha_report);candidate_report['matrix']=matrix.tolist();candidate_report['input']=str(side_input.relative_to(O));fill_reports.setdefault(side,{'candidates':[]})['candidates'].append(candidate_report)
# A local repaint closes the small skirt-tip gaps without replacing visible hair.
lower_input=O/'inputs/lower-hair-clearance-generated.png'
if lower_input.exists():
 # This fully opaque plate supplies texture only in still-missing hidden pixels.
 # It defines no silhouette and replaces no source-visible contour; do not fit
 # its newly painted texture as if it were an unchanged source feature.
 lower=np.array(Image.open(lower_input).convert('RGBA').resize((700,280),Image.Resampling.LANCZOS))
 assert lower[:,:,3].min()>250,'Local hidden texture plate must be fully opaque'
 assert lower[:,:,:3].mean(2).min()>130,'Hidden texture plate contains a dark background'
 full=np.zeros_like(src);full[780:1060,270:970]=lower
 for side in ('left','right'):
  fill_maps[side].append(full)
  fill_reports[side]['candidates'].append({'input':str(lower_input.relative_to(O)),'method':'opaque hidden texture plate at fixed source crop; no silhouette replacement','source_crop':[270,780,970,1060],'only_fills_pixels_missing_from_prior_hidden_paints':True})

parts=[];counts={};core_masks={}
for side,mask in masks.items():
 near=cv2.dilate(mask.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool);solid=cv2.erode(mask.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)
 cool_white=mask&(C.mean(2)>210)&(C[:,:,2]-C[:,:,0]>=0)&(src[:,:,3]>250);core=(solid&(src[:,:,3]>240))|cool_white
 _,labels=cv2.distanceTransformWithLabels((~core).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);F=C[core][np.maximum(labels-1,0)]
 B=under[:,:,:3].astype(float);v=F-B;delta=C-B;projection=np.clip((delta*v).sum(2)/np.maximum((v*v).sum(2),1),0,1)
 a=np.where(near,projection,0);rgb=F.copy()
 exterior=near&(under[:,:,3]<32);a[exterior]=src[exterior,3]/255;rgb[exterior]=C[exterior]
 a[core]=1;rgb[core]=C[core];a[body|source_tail]=0;core&=~(body|source_tail)
 # Keep original outer alpha; an isolated background noise pixel is not a strand.
 a[(src[:,:,3]<16)&exterior]=0
 grown=cv2.dilate((a>.06).astype('uint8'),np.ones((7,7),np.uint8));n,lab,stats,_=cv2.connectedComponentsWithStats(grown,8);largest=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);keep=lab==largest;a[~keep]=0;core&=keep
 part=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(a*255).astype('uint8')]);part[part[:,:,3]==0,:3]=0;assert np.array_equal(part[core,:3],src[core,:3]);Image.fromarray(part).save(O/(side+'-outer-full.png'));im=Image.fromarray(part);box=im.getbbox();im.crop(box).save(O/(side+'-outer-working.png'));parts.append((side,part,box[:2]));counts[side]=int(core.sum());core_masks[side]=core
# Preserve source cores while adding newly painted hair behind the outfit.
if fill_maps:
 updated=[]
 for side,part,offset in parts:
  hidden=target_fill&((xx<600) if side=='left' else (xx>=600))
  paint=np.zeros_like(src);valid=np.zeros((H,W),bool)
  for candidate in fill_maps[side]:
   p=candidate[:,:,:3].astype(int);candidate_valid=(candidate[:,:,3]>128)&(p.mean(2)>140)&(p[:,:,0]-p[:,:,1]<80)
   take=candidate_valid&~valid;paint[take]=candidate[take];valid|=candidate_valid
  required=np.zeros((H,W),bool)
  for shift in (-8,8):
   destination_x=xx+shift*np.clip((yy-410)/550,0,1)
   destination_body=cv2.remap(body.astype('uint8'),destination_x,yy,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT)>0
   required|=hidden&~destination_body
  covered=required&valid
  Image.fromarray((required&~valid).astype('uint8')*255).save(O/(side+'-missing-hidden-fill-mask.png'))
  ratio=float(covered.sum()/max(required.sum(),1));fill_reports[side]['required_hidden_pixels']=int(required.sum());fill_reports[side]['required_hidden_opaque_coverage']=ratio
  print('hidden coverage',side,ratio,'needed',int(required.sum()),fill_reports[side]);assert ratio>.9,'Hidden hair paint does not cover enough displacement clearance'
  patch=paint.copy();patch[:,:,3]=np.where(hidden&valid,paint[:,:,3],0).astype('uint8');complete=Image.fromarray(part);complete.alpha_composite(Image.fromarray(patch));part=np.array(complete)
  assert np.array_equal(part[core_masks[side],:3],src[core_masks[side],:3]);Image.fromarray(part).save(O/(side+'-outer-full.png'));im=Image.fromarray(part);box=im.getbbox();im.crop(box).save(O/(side+'-outer-working.png'));Image.fromarray(patch).save(O/(side+'-hidden-hair-fill.png'));updated.append((side,part,box[:2]))
 parts=updated

Image.fromarray(base).save(O/'outer-hidden-base.png')
matte=Image.new('RGB',(1200,850));d=ImageDraw.Draw(matte)
for i,(side,a,_) in enumerate(parts):
 for j,color in enumerate(((245,245,249),(35,43,63))):
  tile=Image.new('RGBA',(W,H),color+(255,));tile.alpha_composite(Image.fromarray(a));tile=tile.crop((125,365,450,1005) if side=='left' else (740,325,1010,1008));scale=min(280/tile.width,800/tile.height);tile=tile.resize((round(tile.width*scale),round(tile.height*scale)),Image.Resampling.NEAREST);x=(i*2+j)*300;matte.paste(color,(x,0,x+300,850));matte.paste(tile,(x+10,30));d.text((x+10,8),side+' original back hair',fill=(130,130,140))
matte.save(O/'outer-hair-matte-check.png')
cache={}
def warp(a,shift):
 key=(id(a),shift)
 if key in cache:return cache[key]
 gain=np.clip((yy-410)/550,0,1);mx=xx-shift*gain;al=a[:,:,3].astype(np.float32)/255;rgb=a[:,:,:3].astype(np.float32)*al[:,:,None];aa=cv2.remap(al,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=cv2.remap(rgb,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=np.divide(rr,aa[:,:,None],out=np.zeros_like(rr),where=aa[:,:,None]>1e-6);aa[body]=0;im=Image.fromarray(np.dstack([np.clip(np.round(rr),0,255).astype('uint8'),np.round(aa*255).astype('uint8')]));cache[key]=im;return im
prior_frame=Image.fromarray(oldbase)
for name,a in reversed(old):
 if name!='hidden paint and original remainder':prior_frame.alpha_composite(Image.fromarray(a))
previous=np.array(prior_frame);frames={};cases=[];scope=np.zeros((H,W),bool);scope[325:1010,120:1025]=True;outside=~scope&(previous[:,:,3]>0)
for left in (-8,-4,0,4,8):
 for right in (-8,-4,0,4,8):
  frame=Image.fromarray(base)
  for (side,a,_),shift in zip(parts,(left,right)):frame.alpha_composite(warp(a,shift))
  for name,a in reversed(old):
   if name!='hidden paint and original remainder':frame.alpha_composite(Image.fromarray(a))
  arr=np.array(frame)
  bad=outside&np.any(arr!=previous,axis=2)
  if bad.any():
   by,bx=np.where(bad);print('outside diff bbox',int(bx.min()),int(by.min()),int(bx.max()),int(by.max()),'count',len(bx))
  assert np.array_equal(arr[outside],previous[outside]),'Changed unrelated prior work';assert np.array_equal(arr[body,:3],previous[body,:3]),'Back hair moved over foreground outfit or hands'
  cases.append([left,right]);
  if left in (-8,0,8) and right in (-8,0,8):frames[left,right]=frame
board=Image.new('RGB',(1350,1065),(65,75,95));d=ImageDraw.Draw(board)
for row,left in enumerate((-8,0,8)):
 for col,right in enumerate((-8,0,8)):
  tile=frames[left,right].crop((120,330,1010,1010)).resize((440,336),Image.Resampling.NEAREST);board.paste(tile,(450*col+5,355*row+18),tile);d.text((450*col+5,355*row+3),f'left back {left}; right back {right}',fill='white')
board.save(O/'outer-hair-joint-motion.png');frames[0,0].save(O/'joint-neutral.png')
# Source layers are clipped at neutral; dynamic binding must reuse the body mask.
entries=[(name,a) for name,a in old if name!='hidden paint and original remainder']+[(side+' source outer hair',np.array(warp(a,0))) for side,a,_ in reversed(parts)]+[('hidden paint and original remainder',base)]
tree=ET.Element('image',{'w':str(W),'h':str(H),'name':'MewNook outer back hair source review','version':'0.0.3'});root=ET.SubElement(tree,'stack');group=ET.SubElement(root,'stack',{'name':'JOINT CHECK — source hair not rigged; root review pending','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'});archive=O/'MewNook-v4-outer-hair-source.ora';building=archive.with_suffix('.building.ora')
with zipfile.ZipFile(building,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
 for i,(parent,name,a) in enumerate([(root,'SOURCE REFERENCE',src)]+[(group,n,a) for n,a in entries]):
  im=Image.fromarray(a);b=im.getbbox();buf=io.BytesIO();im.crop(b).save(buf,format='PNG');path=f'data/{i}.png';z.writestr(path,buf.getvalue());ET.SubElement(parent,'layer',{'name':name,'src':path,'x':str(b[0]),'y':str(b[1]),'visibility':'visible','opacity':'1','composite-op':'svg:src-over'})
 z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True));buf=io.BytesIO();Image.fromarray(src).save(buf,format='PNG');z.writestr('mergedimage.png',buf.getvalue());z.writestr('foreground-body-occlusion-mask.png',(O/'foreground-body-occlusion-mask.png').read_bytes())
with zipfile.ZipFile(building) as z:
 assert z.testzip() is None;tree=ET.fromstring(z.read('stack.xml'))
 def render(node):
  canvas=Image.new('RGBA',(W,H))
  for child in reversed(list(node)):
   if child.get('visibility')=='hidden':continue
   if child.tag=='stack':canvas.alpha_composite(render(child))
   else:canvas.alpha_composite(Image.open(io.BytesIO(z.read(child.get('src')))).convert('RGBA'),(int(child.get('x')),int(child.get('y'))))
  return canvas
 actual=np.array(render(tree.find('stack')));vis=src[:,:,3]>0;assert np.array_equal(actual[vis],src[vis]);actual=np.array(render(tree.find('stack').find('stack')));expected=np.array(frames[0,0]);vis=expected[:,:,3]>0;assert np.array_equal(actual[:,:,3],expected[:,:,3]) and np.array_equal(actual[vis],expected[vis])
building.replace(archive);report={'stage':'outer_hair_source_static_review_not_complete_head','registration':{'inliers':int(inside.sum()),'matches':len(good),'median_native_error':float(np.median(err)),'p95_native_error':float(np.percentile(err,95)),'matrix':M.tolist()},'source_core_rgb_exact_pixels':counts,'inner_hidden_hair_paint':fill_reports,'hidden_motion_clearance_complete':bool(fill_reports) and all(v['required_hidden_opaque_coverage']>=.999 for v in fill_reports.values()),'working_parts':[{'file':side+'-outer-working.png','offset':list(offset)} for side,a,offset in parts],'left_right_parameter_cases':cases,'foreground_body_rgb_unchanged_in_all_cases':True,'unrelated_prior_working_visible_rgba_exact':True,'default_reference_and_serialized_ora_joint_validated':True,'remaining':['Review hidden texture continuity and complete hair matte; coverage is not full art approval','Separate ear-under/head-side to shoulder connector hair panels','Inspect matte contours and chair/cat-tail boundaries','Review full hair root and ear overlaps together','Consolidate remaining fine curls','Face, upright pose and actual rig/physics']};(O/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
