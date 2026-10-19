#!/usr/bin/env python3
"""Original front long locks and costume hidden underpainting, no runtime edits."""
from pathlib import Path
import json,io,zipfile,xml.etree.ElementTree as ET
import numpy as np,cv2
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v8';P=R/'assets/inochi/v4/hair-source-v7';src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];yy,xx=np.indices((H,W),dtype=np.float32);C=src[:,:,:3].astype(float)
masks={side:np.array(Image.open(O/(side+'-hair-mask.png'))) for side in ('left','right')};union=np.maximum(masks['left'],masks['right']);ref=np.array(Image.open(O/'inputs/chest-source.png').convert('RGBA'));paint=np.array(Image.open(O/'inputs/costume-hidden-generated.png').convert('RGBA').resize((1035,1050),Image.Resampling.LANCZOS));assert paint[:,:,3].min()>250,'Costume underpainting must cover the full opaque crop'
gate=cv2.resize(255-cv2.dilate(union[325:675,420:765],np.ones((13,13),np.uint8)),(1035,1050));gate[ref[:,:,3]<250]=0
sift=cv2.SIFT_create(contrastThreshold=.01);k1,d1=sift.detectAndCompute(cv2.cvtColor(ref[:,:,:3],cv2.COLOR_RGB2GRAY),gate);k2,d2=sift.detectAndCompute(cv2.cvtColor(paint[:,:,:3],cv2.COLOR_RGB2GRAY),None);good=[a for a,b in cv2.BFMatcher().knnMatch(d1,d2,k=2) if a.distance<.75*b.distance];target=np.float32([k1[g.queryIdx].pt for g in good]);origin=np.float32([k2[g.trainIdx].pt for g in good]);M,inside=cv2.estimateAffinePartial2D(origin,target,method=cv2.RANSAC,ransacReprojThreshold=2)
assert M is not None and int(inside.sum())>=20 and np.ptp(target[inside.ravel()>0,0])>300,'Costume hidden paint alignment requires review'
err=np.linalg.norm(cv2.transform(origin[:,None],M)[:,0]-target,axis=1)[inside.ravel()>0]/3;assert np.percentile(err,95)<.7
pa=paint[:,:,3].astype(np.float32)/255;wa=cv2.warpAffine(pa,M,(1035,1050));wr=cv2.warpAffine(paint[:,:,:3].astype(np.float32)*pa[:,:,None],M,(1035,1050));wr=np.divide(wr,wa[:,:,None],out=np.zeros_like(wr),where=wa[:,:,None]>1e-6);reg=np.dstack([np.clip(np.round(wr),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);Image.fromarray(reg).save(O/'registered-costume-hidden.png');under=src.copy();under[325:675,420:765]=np.array(Image.fromarray(reg).resize((345,350),Image.Resampling.LANCZOS))
# Preserve original visible navy cloth in the holes between white curls.
roi=np.zeros((H,W),bool);roi[325:675,420:765]=True;visible_blue=roi&(C[:,:,2]-C[:,:,0]>20)&(C[:,:,2]-C[:,:,1]>8)&(C[:,:,0]<130)&(src[:,:,3]>250)
# Preserve true visible cloth cores, not the old hair/cloth mixed fringe.
visible_blue=cv2.erode(visible_blue.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)
with zipfile.ZipFile(P/'MewNook-v4-both-bows-source.ora') as z:
 tree=ET.fromstring(z.read('stack.xml'));group=tree.find('stack').find('stack');old=[]
 for node in group:
  im=np.array(Image.open(io.BytesIO(z.read(node.get('src')))).convert('RGBA'));a=np.zeros_like(src);x,y=int(node.get('x')),int(node.get('y'));a[y:y+im.shape[0],x:x+im.shape[1]]=im;old.append((node.get('name'),a))
base=next(a.copy() for name,a in old if name=='hidden paint and original remainder');clearance=cv2.dilate((union>0).astype('uint8'),np.ones((5,5),np.uint8)).astype(bool);base[clearance]=under[clearance];base[visible_blue]=src[visible_blue]
# Refine cloth-facing alpha from ORIGINAL nearby navy and ORIGINAL white hair.
# The fine curls are only a few native pixels wide and must not be cut halfway.
navy_seed=roi&(C[:,:,2]-C[:,:,0]>30)&(C[:,:,2]-C[:,:,1]>18)&(C[:,:,0]<130)
navy_seed=cv2.erode(navy_seed.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)
navy_halo=cv2.dilate(navy_seed.astype('uint8'),np.ones((9,9),np.uint8)).astype(bool)
_,near_blue=cv2.distanceTransformWithLabels((~navy_seed).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);original_blue=C[navy_seed][np.maximum(near_blue-1,0)]
parts=[];counts={};effective_masks=[]
for side,mask in masks.items():
 raw=np.array(Image.open(O/(side+'-contour-mask.png')))
 candidate=raw>0
 extra=np.zeros((H,W),bool)
 if side=='left':extra[522:589,563:584]=True
 else:extra[493:548,645:680]=True
 candidate|=extra&navy_halo
 # Main body keeps original paint; navy-facing edges use original color matting.
 a=raw.astype(float)/255;a[extra&navy_halo]=1
 white=(candidate&(C.mean(2)>220)&(C[:,:,2]-C[:,:,0]>-2)&~navy_seed)
 _,near_white=cv2.distanceTransformWithLabels((~white).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);F=C[white][np.maximum(near_white-1,0)]
 v=F-original_blue;delta=C-original_blue;projection=np.clip((delta*v).sum(2)/np.maximum((v*v).sum(2),1),0,1)
 cloth_facing=candidate&navy_halo
 a[cloth_facing]=projection[cloth_facing];a[navy_seed]=0
 rgb=C.copy();rgb[cloth_facing]=F[cloth_facing]
 core=((raw==255)&~navy_halo)|(white&(raw==255))
 a[core]=1;rgb[core]=C[core]
 n,labels,stats,_=cv2.connectedComponentsWithStats((a>.06).astype('uint8'),8)
 largest=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);keep=cv2.dilate((labels==largest).astype('uint8'),np.ones((3,3),np.uint8)).astype(bool);a[~keep]=0;core&=keep
 part=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(a*255).astype('uint8')]);part[part[:,:,3]==0,:3]=0;assert np.array_equal(part[core,:3],src[core,:3])
 pc=part[:,:,:3].astype(int);cloth_blue=(part[:,:,3]>128)&(pc[:,:,0]<150)&(pc[:,:,1]-pc[:,:,0]>5)&(pc[:,:,2]-pc[:,:,1]>15)
 assert not cloth_blue.any(),'Navy cloth was carried into the hair material'
 effective_masks.append(part[:,:,3]);Image.fromarray(part).save(O/(side+'-lock-full.png'));im=Image.fromarray(part);bounds=im.getbbox();im.crop(bounds).save(O/(side+'-lock-working.png'));parts.append((side,part,bounds[:2]));counts[side]=int(core.sum())
# Clear the complete original white-hair footprint, then retain source navy
# where it was genuinely visible. This removes old half-curl outlines.
coverage=cv2.dilate((np.maximum.reduce(effective_masks)>0).astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)
base[coverage]=under[coverage];base[visible_blue]=src[visible_blue];clearance|=coverage
Image.fromarray(base).save(O/'chest-hidden-base.png');matte=Image.new('RGB',(1200,700));d=ImageDraw.Draw(matte)
for i,(side,part,offset) in enumerate(parts):
 for j,color in enumerate(((245,245,249),(35,43,63))):
  tile=Image.new('RGBA',(W,H),color+(255,));tile.alpha_composite(Image.fromarray(part));tile=tile.crop((475,325,590,655) if side=='left' else (640,325,730,675));scale=min(250/tile.width,620/tile.height);tile=tile.resize((round(tile.width*scale),round(tile.height*scale)),Image.Resampling.NEAREST);x=(i*2+j)*300;matte.paste(color,(x,0,x+300,700));matte.paste(tile,(x+20,35));d.text((x+20,10),side+' original long lock',fill=(130,130,140))
matte.save(O/'chest-lock-matte-check.png')
cache={}
def warp(a,shift):
 key=(id(a),shift)
 if key in cache:return cache[key]
 gain=np.clip((yy-345)/300,0,1);mx=xx-shift*gain;al=a[:,:,3].astype(np.float32)/255;rgb=a[:,:,:3].astype(np.float32)*al[:,:,None];aa=cv2.remap(al,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=cv2.remap(rgb,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=np.divide(rr,aa[:,:,None],out=np.zeros_like(rr),where=aa[:,:,None]>1e-6);im=Image.fromarray(np.dstack([np.clip(np.round(rr),0,255).astype('uint8'),np.round(aa*255).astype('uint8')]));cache[key]=im;return im
previous=np.array(Image.open(P/'joint-neutral.png').convert('RGBA'));outside=~clearance;outside[320:680,470:735]=False;outside&=previous[:,:,3]>0
frames={};cases=[]
for left in (-6,-3,0,3,6):
 for right in (-6,-3,0,3,6):
  frame=Image.fromarray(base)
  for name,a in reversed(old):
   if name!='hidden paint and original remainder':frame.alpha_composite(Image.fromarray(a))
  current=[]
  for (side,a,_),shift in zip(parts,(left,right)):
   moving=warp(a,shift);current.append(np.array(moving)[:,:,3]);frame.alpha_composite(moving)
  arr=np.array(frame);assert np.array_equal(arr[outside],previous[outside]),'Long hair changed unrelated prior work'
  cloth=visible_blue&(np.maximum.reduce(current)==0);assert np.array_equal(arr[cloth,:3],src[cloth,:3]),'Changed unoccluded original navy cloth'
  cases.append([left,right]);
  if left in (-6,0,6) and right in (-6,0,6):frames[left,right]=frame
board=Image.new('RGB',(1080,1080),(65,75,95));d=ImageDraw.Draw(board)
for row,left in enumerate((-6,0,6)):
 for col,right in enumerate((-6,0,6)):
  tile=frames[left,right].crop((420,325,765,675)).resize((340,345),Image.Resampling.NEAREST);board.paste(tile,(col*360+10,row*360+15),tile);d.text((col*360+10,row*360+2),f'left {left}; right {right}',fill='white')
board.save(O/'chest-lock-joint-motion.png');frames[0,0].save(O/'joint-neutral.png')
entries=[(side+' source chest lock',a) for side,a,_ in reversed(parts)]+[(name,a) for name,a in old if name!='hidden paint and original remainder']+[('hidden paint and original remainder',base)]
tree=ET.Element('image',{'w':str(W),'h':str(H),'name':'MewNook original chest hair source review','version':'0.0.3'});root=ET.SubElement(tree,'stack');group=ET.SubElement(root,'stack',{'name':'JOINT CHECK — outer side and back hair incomplete','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'});archive=O/'MewNook-v4-chest-hair-source.ora';building=archive.with_suffix('.building.ora')
with zipfile.ZipFile(building,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
 for i,(parent,name,a) in enumerate([(root,'SOURCE REFERENCE',src)]+[(group,n,a) for n,a in entries]):
  im=Image.fromarray(a);b=im.getbbox();buf=io.BytesIO();im.crop(b).save(buf,format='PNG');path=f'data/{i}.png';z.writestr(path,buf.getvalue());ET.SubElement(parent,'layer',{'name':name,'src':path,'x':str(b[0]),'y':str(b[1]),'visibility':'visible','opacity':'1','composite-op':'svg:src-over'})
 z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True));buf=io.BytesIO();Image.fromarray(src).save(buf,format='PNG');z.writestr('mergedimage.png',buf.getvalue())
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
building.replace(archive);report={'stage':'two_main_front_long_locks_source_static_review','registration':{'inliers':int(inside.sum()),'matches':len(good),'median_native_error':float(np.median(err)),'p95_native_error':float(np.percentile(err,95)),'matrix':M.tolist()},'source_core_rgb_exact_pixels':counts,'opaque_navy_cloth_contamination_pixels':0,'full_rectangular_opaque_underpaint_verified':True,'working_parts':[{'file':side+'-lock-working.png','offset':list(offset)} for side,a,offset in parts],'left_right_parameter_cases':cases,'unoccluded_original_navy_cloth_core_rgb_exact':True,'unrelated_prior_working_visible_rgba_exact':True,'ora_default_and_joint_validated':True,'remaining':['Review edges and all original fine curls','Outer long side/back hair and shoulder occlusion','Full hair root/ear review','Face, upright pose and actual rig binding']};(O/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
