#!/usr/bin/env python3
"""Bake source-art eyelid motion from original lashes and the registered closed-eye repaint."""
from pathlib import Path
import json
import cv2,numpy as np
from PIL import Image,ImageDraw
from v4_image_io import atomic_png
from v4_source_io import load_group,composite,export_ora
R=Path(__file__).resolve().parents[1];V=R/'assets/inochi/v4';O=V/'face-source-v6';O.mkdir(exist_ok=True)
src=np.array(Image.open(V/'source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];yy,xx=np.indices((H,W),dtype=np.float32);keys=np.linspace(0,1,9)
meta=json.loads((V/'face-source-v1/manifest.json').read_text())
def warp(a,mx,my):
 a=a.astype(np.float32);alpha=a[:,:,3]/255;wa=cv2.remap(alpha,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rgb=cv2.remap(a[:,:,:3]*alpha[:,:,None],mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rgb=np.divide(rgb,wa[:,:,None],out=np.zeros_like(rgb),where=wa[:,:,None]>1e-6);return np.dstack((np.clip(np.round(rgb),0,255).astype('uint8'),np.round(wa*255).astype('uint8')))
def registered(file,key):
 a=np.array(Image.open(V/'art-review-v1'/file).convert('RGBA'));M=np.array(meta['registration'][key]['affine'],np.float32);return warp(a,M[0,0]*xx+M[0,1]*yy+M[0,2],M[1,0]*xx+M[1,1]*yy+M[1,2])
closed=registered('expression-closed.png','closed');skin=registered('skin-base-unregistered.png','skin-underpaint');C=src[:,:,:3].astype(float);parts={};report={'keys':keys.tolist(),'eyes':{}}
old=load_group(V/'face-source-v5/MewNook-v4-eye-source.ora',src.shape)
for s in ('left','right'):
 p=V/'face-source-v5';region=np.array(Image.open(p/(s+'-eye-region-mask.png')))>0;opening=np.array(Image.open(p/(s+'-opening-mask.png')))>0;clip=np.array(Image.open(p/(s+'-aperture-mask.png')))>0
 sup=np.array(Image.open(p/(s+'-eye-support-full.png')).convert('RGBA'));iris=np.array(Image.open(p/(s+'-iris-full.png')).convert('RGBA'));upper=np.array(Image.open(p/(s+'-upper-lid-domain-mask.png')))>0;lower=np.array(Image.open(p/(s+'-lower-lid-domain-mask.png')))>0
 # Matte follows the real painted lash; the black pixels outside paint alpha are excluded.
 domain=cv2.dilate(region.astype('uint8'),np.ones((9,9),np.uint8)).astype(bool);dark=(closed[:,:,:3].mean(2)<150)&(closed[:,:,3]>16)&domain
 n,labels,stats,cent=cv2.connectedComponentsWithStats(dark.astype('uint8'));assert n>1;label=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);ink=labels==label;closed_domain=cv2.dilate(ink.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool);region|=closed_domain
 bbox=Image.fromarray(region).getbbox();x0,y0,x1,y1=bbox;skinpart=skin.copy();skinpart[:,:,3]=np.where(region,255,0);skinpart[~region,:3]=0
 # Match repaint skin to unaltered skin around the eye without copying old iris pixels.
 ring=region&~cv2.dilate((opening|upper|lower|ink).astype('uint8'),np.ones((9,9),np.uint8)).astype(bool)&(src[:,:,3]>200)&(skin[:,:,3]>200)&(C.mean(2)>190)
 delta=np.median(C[ring]-skin[ring,:3],axis=0) if ring.any() else np.zeros(3);skinpart[:,:,:3]=np.clip(skinpart[:,:,:3].astype(float)+delta,0,255).astype('uint8');skinpart[(skin[:,:,3]<200)&region]=src[(skin[:,:,3]<200)&region];skinpart[region,3]=255;skinpart[~region,:3]=0
 def matte(pixels,domain,core):
  domain=domain&(pixels[:,:,3]>16);core=core&domain;assert core.any();_,labs=cv2.distanceTransformWithLabels((~core).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);F=pixels[core,:3].astype(float)[np.maximum(labs-1,0)];B=skinpart[:,:,:3].astype(float);D=pixels[:,:,:3].astype(float)-B;v=F-B;a=np.clip((D*v).sum(2)/np.maximum((v*v).sum(2),1),0,1);a[~domain]=0;a[core]=1;rgb=F.astype('uint8');rgb[core]=pixels[core,:3];return np.dstack((rgb,np.round(a*255).astype('uint8')))
 lash=matte(closed,closed_domain,ink);u=matte(src,cv2.dilate(upper.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)&region,upper&(C.mean(2)<140));l=matte(src,cv2.dilate(lower.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)&region,lower&(C.mean(2)<180))
 def profile(mask,mode):
  xs=np.flatnonzero(mask.any(0));ys=[np.flatnonzero(mask[:,x]) for x in xs];v=[(np.min(a) if mode=='top' else np.max(a) if mode=='bottom' else np.mean(a)) for a in ys];return np.interp(np.arange(W),xs,v).astype('float32')
 top=profile(opening,'top');bot=profile(opening,'bottom');curve=profile(ink,'mean');base=Image.fromarray(sup);ir=iris.copy();ir[~clip,3]=0;base.alpha_composite(Image.fromarray(ir));neutral=np.array(base);neutral[~region]=0
 # Original non-eye pixels in the slot are kept exact at rest.
 neutral[region&~(sup[:,:,3]>0)]=src[region&~(sup[:,:,3]>0)];neutral[region,3]=255
 def frame(t):
  if t==0:return neutral.copy()
  nt=(1-t)*top+t*curve;nb=(1-t)*bot+t*curve;ap=(yy>=nt[None,:])&(yy<=nb[None,:])&clip
  white=sup.copy();white[:,:,3]=np.where(ap,255,0);white[~ap,:3]=0
  ir=iris.copy();ir[~ap,3]=0
  uu=warp(u,xx,yy-t*(curve-top)[None,:]);ll=warp(l,xx,yy-t*(curve-bot)[None,:]);ll[:,:,3]=np.round(ll[:,:,3]*(1-t)).astype('uint8')
  painted=warp(lash,xx,yy+(1-t)*(curve-top+2)[None,:]);uu=np.array(Image.blend(Image.fromarray(uu),Image.fromarray(painted),t));result=Image.fromarray(skinpart);result.alpha_composite(Image.fromarray(white));result.alpha_composite(Image.fromarray(ir));result.alpha_composite(Image.fromarray(ll));result.alpha_composite(Image.fromarray(uu));a=np.array(result)
  if t<.15:a=np.array(Image.blend(Image.fromarray(neutral),Image.fromarray(a),t/.15))
  a[~region]=0;return a
 frames=[]
 for t in keys:
  a=frame(float(t));frames.append(a);atomic_png(Image.fromarray(a).crop(bbox),O/(s+'-blink-'+str(round(t*1000))+'.png'))
 assert np.array_equal(frames[0],neutral);assert np.array_equal(frames[-1][:,:,3],frames[0][:,:,3]);bad=(frames[-1][:,:,:3].mean(2)<140)&(frames[-1][:,:,3]>16)&opening&~closed_domain;assert not bad.any()
 for name,a in [('skin-support',skinpart),('upper-lid',u),('lower-lid',l),('closed-lash',lash)]:atomic_png(Image.fromarray(a),O/(s+'-'+name+'-full.png'))
 parts[s]=frames;report['eyes'][s]={'slot_offset':[x0,y0],'slot_size':[x1-x0,y1-y0],'skin_rgb_offset':delta.tolist(),'closed_lash_source_pixels':int(ink.sum()),'outside_painted_lash_dark_residue':0}
fixed=[(n,a) for n,a in old if 'source iris' not in n and 'eye support' not in n];baseidx=next(i for i,(n,a) in enumerate(fixed) if n=='hidden paint and original remainder')
def layers(k):return fixed[:baseidx]+[(s+' eye slot',parts[s][k]) for s in ('right','left')]+fixed[baseidx:]
board=Image.new('RGB',(1050,450),(235,236,242));d=ImageDraw.Draw(board)
for i,k in enumerate((0,2,4,6,8)):
 a=Image.fromarray(composite(layers(k),src.shape));atomic_png(a,O/('preview-blink-'+str(k*125)+'.png'))
 tile=a.crop((470,210,680,315)).resize((210,105));board.paste(tile,(i*210,30));tile=a.crop((460,185,690,355)).resize((210,155));board.paste(tile,(i*210,210));d.text((i*210+5,5),f'closure {k/8:g}',fill='black')
atomic_png(board,O/'blink-motion-check.png');export_ora(O/'MewNook-v4-blink-source.ora',src,layers(0),'Source eyelid parts and neutral assembly');(O/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
