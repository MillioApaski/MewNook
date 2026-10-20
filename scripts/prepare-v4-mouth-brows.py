#!/usr/bin/env python3
"""Original smile, full registered mouth repaint and independently movable source brows."""
from pathlib import Path
import json
import cv2,numpy as np
from PIL import Image,ImageDraw
from v4_image_io import atomic_png
from v4_source_io import load_group,composite,export_ora
R=Path(__file__).resolve().parents[1];V=R/'assets/inochi/v4';O=V/'face-source-v7';O.mkdir(exist_ok=True)
src=np.array(Image.open(V/'source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];yy,xx=np.indices((H,W),dtype=np.float32);keys=np.linspace(0,1,9);m=json.loads((V/'face-source-v1/manifest.json').read_text())
def remap(a,mx,my):
 alpha=a[:,:,3].astype('float32')/255;wa=cv2.remap(alpha,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rgb=cv2.remap(a[:,:,:3].astype('float32')*alpha[:,:,None],mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rgb=np.divide(rgb,wa[:,:,None],out=np.zeros_like(rgb),where=wa[:,:,None]>1e-6);return np.dstack((np.clip(np.round(rgb),0,255).astype('uint8'),np.round(wa*255).astype('uint8')))
def reg(file,key):
 a=np.array(Image.open(V/'art-review-v1'/file).convert('RGBA'));M=np.array(m['registration'][key]['affine'],np.float32);return remap(a,M[0,0]*xx+M[0,1]*yy+M[0,2],M[1,0]*xx+M[1,1]*yy+M[1,2])
paint=reg('expression-talking.png','talking');skin=reg('skin-base-unregistered.png','skin-underpaint');C=paint[:,:,:3].astype(float)
# One mask encloses the entire painted mouth including the previously clipped lower rim.
region=np.zeros((H,W),np.uint8);cv2.fillPoly(region,[np.array([(560,300),(585,294),(615,295),(622,312),(616,336),(582,340),(562,328)])],255);region=region>0;box=Image.fromarray(region).getbbox()
# Colour segmentation samples the supplied mouth painting; no lip or cavity is drawn.
ink=region&(paint[:,:,3]>16)&((C.mean(2)<170)|((C[:,:,0]-C[:,:,1]>42)&(C[:,:,1]<210)))
n,labels,stats,_=cv2.connectedComponentsWithStats(ink.astype('uint8'));assert n>1;mask=labels==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA]));contours,_=cv2.findContours(mask.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);filled=np.zeros((H,W),np.uint8);cv2.drawContours(filled,contours,-1,1,cv2.FILLED);mask=filled>0;assert np.count_nonzero(mask)>350
core=cv2.erode(mask.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool);_,labs=cv2.distanceTransformWithLabels((~core).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);F=C[core][np.maximum(labs-1,0)];B=skin[:,:,:3].astype(float);D=C-B;v=F-B;a=np.clip((D*v).sum(2)/np.maximum((v*v).sum(2),1),0,1);a[~cv2.dilate(mask.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)]=0;a[mask]=1;mouth=np.dstack((F.astype('uint8'),np.round(a*255).astype('uint8')));mouth[mask,:3]=paint[mask,:3];mouth[~region,3]=0
support=skin.copy();support[:,:,3]=np.where(region,255,0);support[~region,:3]=0;neutral=src.copy();neutral[:,:,3]=np.where(region,255,0);neutral[~region,:3]=0
# Split the actual painted cavity into editable, disjoint colour materials.
highlight=mask&(C.mean(2)>220);lip=mask&((C.mean(2)<150)|((C[:,:,0]-C[:,:,1])>60));upper=lip&(yy<314);lower=lip&~upper;tongue=mask&~lip&~highlight&(yy>317);groups={'upper-lip-paint':upper,'lower-lip-paint':lower,'highlight-paint':highlight,'tongue-paint':tongue};owned=upper|lower|highlight|tongue;groups['inner-mouth-paint']=(mouth[:,:,3]>0)&~owned
check=Image.new('RGBA',(W,H))
for name,maskpart in groups.items():
 p=mouth.copy();p[~maskpart]=0;atomic_png(Image.fromarray(p),O/(name+'-full.png'));check.alpha_composite(Image.fromarray(p))
assert np.array_equal(np.array(check)[mouth[:,:,3]>0],mouth[mouth[:,:,3]>0])
frames=[];angle=np.deg2rad(-20);cx,cy=589,315;u=(xx-cx)*np.cos(angle)+(yy-cy)*np.sin(angle);v=-(xx-cx)*np.sin(angle)+(yy-cy)*np.cos(angle)
for t in keys:
 if t==0:out=neutral.copy()
 else:
  scale=.15+.85*t;mx=cx+u*np.cos(angle)-v/scale*np.sin(angle);my=cy+u*np.sin(angle)+v/scale*np.cos(angle);p=remap(mouth,mx.astype('float32'),my.astype('float32'));im=Image.fromarray(support);im.alpha_composite(Image.fromarray(p));out=np.array(im);out[~region]=0
  if t<.2:out=np.array(Image.blend(Image.fromarray(neutral),Image.fromarray(out),t/.2))
 frames.append(out);atomic_png(Image.fromarray(out).crop(box),O/('mouth-'+str(round(t*1000))+'.png'))
assert np.array_equal(frames[0][region,:3],src[region,:3]);assert all(np.array_equal(f[:,:,3],frames[0][:,:,3]) for f in frames)
old=load_group(V/'face-source-v6/MewNook-v4-blink-source.ora',src.shape);brows={};fixed=[]
for n,a in old:
 if 'brow' in n:
  for s,test in [('left',xx<565),('right',xx>=565)]:
   p=a.copy();p[~test]=0
   if s in brows:
    im=Image.fromarray(brows[s]);im.alpha_composite(Image.fromarray(p));brows[s]=np.array(im)
   else:brows[s]=p
 else:fixed.append((n,a))
assert len(brows)==2
for s,a in brows.items():atomic_png(Image.fromarray(a),O/(s+'-brow-full.png'))
idx=next(i for i,(n,a) in enumerate(fixed) if n=='hidden paint and original remainder')
def layers(k=0,bl=0,br=0,eye=0):
 ls=[]
 for n,a in fixed[:idx]:
  if 'eye slot' in n:
   s=n.split()[0];em=json.loads((V/'face-source-v6/manifest.json').read_text())['eyes'][s];p=np.array(Image.open(V/'face-source-v6'/(s+'-blink-'+str(eye*125)+'.png')));a=np.zeros_like(src);x,y=em['slot_offset'];a[y:y+p.shape[0],x:x+p.shape[1]]=p
  ls.append((n,a))
 for s,d in [('left',bl),('right',br)]:ls.insert(0,(s+' source brow',remap(brows[s],xx,yy-d)))
 return ls+[('mouth slot',frames[k])]+fixed[idx:]
board=Image.new('RGB',(1150,350),(235,236,242));d=ImageDraw.Draw(board)
for i,(name,k,l,r,e) in enumerate([('neutral',0,0,0,0),('blink',0,0,0,8),('chat',8,-1,-1,0),('sleepy',0,2,2,6),('content',0,-1,-1,8)]):
 im=Image.fromarray(composite(layers(k,l,r,e),src.shape));board.paste(im.crop((460,185,690,355)),(i*230,25));d.text((i*230+5,5),name,fill='black');atomic_png(im,O/('preview-'+name+'.png'))
for name,p in [('mouth-open',mouth),('mouth-skin-support',support)]:atomic_png(Image.fromarray(p),O/(name+'-full.png'))
atomic_png(board,O/'expression-source-check.png');export_ora(O/'MewNook-v4-mouth-brows-source.ora',src,layers(),'Source mouth materials and independent brows')
(O/'manifest.json').write_text(json.dumps({'keys':keys.tolist(),'mouth_slot_offset':list(box[:2]),'mouth_slot_size':[box[2]-box[0],box[3]-box[1]],'neutral_mouth_rgb_exact':True,'painted_mouth_pixels':int(mask.sum()),'editable_material_recomposition_exact':True,'brow_names':list(brows),'source':'Original visible smile and brows; full registered expression-talking repaint'},indent=2)+'\n');print('source mouth, brows and expression combinations generated')
