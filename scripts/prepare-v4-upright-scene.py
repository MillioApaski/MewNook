#!/usr/bin/env python3
"""Assemble original-art head/hair with the uncrossed seated pose; export editable parts."""
from pathlib import Path
import json
import cv2,numpy as np
from PIL import Image,ImageDraw
from v4_image_io import atomic_png
from v4_source_io import load_group,composite,export_ora
R=Path(__file__).resolve().parents[1];V=R/'assets/inochi/v4';O=V/'scene-source-v1';O.mkdir(exist_ok=True);src=np.array(Image.open(V/'source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];yy,xx=np.indices((H,W));old=load_group(V/'face-source-v7/MewNook-v4-mouth-brows-source.ora',src.shape);base=next(a for n,a in old if n=='hidden paint and original remainder').copy();pose=np.array(Image.open(V/'pose-source-v1/upright-candidate.png').convert('RGBA'));base[863:]=pose[863:]
def polygon(points):
 a=np.zeros((H,W),np.uint8);cv2.fillPoly(a,[np.array(points,np.int32)],1);return a>0
def masked(a,m):
 p=a.copy();p[~m]=0;return p
# Replace the lower pose's generated hair pixels with prior hidden chair paint.
C=base[:,:,:3].astype(float);cool=(C[:,:,2]>C[:,:,0]-5)&(C[:,:,2]>C[:,:,1]-2)&(C.mean(2)>155);legscope=polygon([(462,865),(692,865),(707,1050),(673,1195),(673,1315),(613,1337),(550,1320),(540,1205),(514,1070),(477,996)])
oldbase=np.array(Image.open(V/'hair-source-v9/outer-hidden-base.png').convert('RGBA'));remove=(yy>=863)&(yy<1030)&cool&~cv2.dilate(legscope.astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);base[remove]=oldbase[remove]
# Semantic leg selection separates light stockings from the pink chair and navy hem.
rect=polygon([(450,863),(720,863),(720,1350),(500,1350)]);gc=np.where(rect,cv2.GC_PR_BGD,cv2.GC_BGD).astype('uint8');white=(C.mean(2)>185)&(C[:,:,2]>C[:,:,1]-7)&(C[:,:,0]-C[:,:,2]<24)&legscope;gc[white]=cv2.GC_PR_FGD;gc[white&(yy>1000)&(C.mean(2)>220)]=cv2.GC_FGD;cv2.setRNGSeed(0);cv2.grabCut(base[:,:,:3],gc,None,np.zeros((1,65)),np.zeros((1,65)),5,cv2.GC_INIT_WITH_MASK);legs=np.isin(gc,[cv2.GC_FGD,cv2.GC_PR_FGD])&rect&(yy>=863)&(base[:,:,3]>0)
bodymask=np.array(Image.open(V/'hair-source-v9/foreground-body-occlusion-mask.png'))>0;bodymask&=yy>=375;bodymask&=yy<863
# Retain original pale costume edge coverage while keeping surrounding cool hair behind.
warm=(C[:,:,0]-C[:,:,2]>4)&(C.mean(2)>100);edge=cv2.dilate((bodymask&warm).astype('uint8'),np.ones((5,5),np.uint8)).astype(bool);bodymask|=edge&(yy>=395)&(yy<863)
head=((yy<375)|((yy<435)&(C[:,:,2]>=C[:,:,0]-8)))&(xx>280)&(xx<875)&(base[:,:,3]>0);neck=(yy>=375)&(yy<430)&(C[:,:,0]-C[:,:,2]>10)&(xx>510)&(xx<650);head|=neck
facewarm=(C[:,:,0]-C[:,:,2]>12)&(C[:,:,0]>150)&head;n,labs,stats,_=cv2.connectedComponentsWithStats(facewarm.astype('uint8'));label=labs[320,580];assert label>0;mask=(labs==label).astype('uint8');cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);face=np.zeros((H,W),np.uint8);cv2.drawContours(face,cs,-1,1,cv2.FILLED);face=face.astype(bool)&head
scaffold=masked(base,head&~face);facepart=masked(base,face);fade=np.clip((425-yy)/30,0,1);facepart[:,:,3]=np.round(facepart[:,:,3]*fade).astype('uint8');necksupport=masked(base,neck&(yy>=385))
# Ear roots stay overlapped and pinned; only the visible tips deform.
ears={};earspec={'left':{'polygon':[(354,88),(410,90),(451,112),(427,142),(404,174),(394,207),(374,179),(360,131)],'pivot':[410,185]},'right':{'polygon':[(577,72),(624,33),(670,6),(686,44),(701,114),(701,149),(684,174),(661,151),(622,127)],'pivot':[667,151]}}
for s,m in earspec.items():
 p=polygon(m['polygon']);ears[s]=masked(scaffold,p);distance=(-57*(yy-112)-95*(xx-451))/110.8 if s=='left' else (102*(xx-577)-107*(yy-72))/147.8;scaffold[p&(distance>8)]=0
# Original tail is extracted once from the original source, never duplicated in the chair.
tailmask=np.array(Image.open(V/'hair-source-v9/original-cat-tail-protection-mask.png'))>0;tail=masked(src,tailmask);bg=base.copy();bg[head|bodymask|legs|cv2.dilate(tailmask.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)]=0
# Remove detached paint flecks using the upright pose silhouette.
n,labs,stats,_=cv2.connectedComponentsWithStats((pose[:,:,3]>8).astype('uint8'));sil=cv2.dilate((labs==1+np.argmax(stats[1:,cv2.CC_STAT_AREA])).astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);bg[~sil]=0
layers=[];metadata=[]
def add(name,a,role,head_child=False):
 if not a[:,:,3].any():return
 layers.append((name,a));im=Image.fromarray(a);box=im.getbbox();file='part-'+str(len(metadata))+'.png';atomic_png(im.crop(box),O/file);metadata.append({'name':name,'file':file,'offset':list(box[:2]),'size':[box[2]-box[0],box[3]-box[1]],'role':role,'head_child':head_child,'front_order':len(metadata)})
for n,a in old:
 if n=='hidden paint and original remainder' or 'connector' in n or 'outer' in n:continue
 role='eye' if 'eye slot' in n else 'mouth' if n=='mouth slot' else 'brow' if 'brow' in n else 'front-hair';add(n,a,role,True)
add('torso clothing and hands',masked(base,bodymask),'body');add('left resting leg',masked(base,legs&(xx<595)),'leg');add('right resting leg',masked(base,legs&(xx>=595)),'leg');add('face and neck',facepart,'face',True)
for s in ('right','left'):add(s+' original outer hair',np.array(Image.open(V/'hair-source-v9'/(s+'-outer-full.png')).convert('RGBA')),'back-hair')
for s in ('right','left'):add(s+' source connector',np.array(Image.open(V/'hair-source-v10'/(s+'-connector-full.png')).convert('RGBA')),'connector',True)
for s in ('right','left'):add(s+' original ear',ears[s],'ear',True)
add('rear head scaffold',scaffold,'head-rear',True);add('neck overlap support',necksupport,'neck-support');add('original cat tail',tail,'tail');add('chair and background',bg,'background')
neutral=composite(layers,src.shape);atomic_png(Image.fromarray(neutral),O/'upright-assembled.png');export_ora(O/'MewNook-v4-upright-assembly.ora',pose,layers,'Upright source assembly — runtime validation pending');(O/'manifest.json').write_text(json.dumps({'canvas':[W,H],'head_pivot':[588,370],'ears':earspec,'parts':metadata,'status':'source assembly, actual rig validation pending'},indent=2)+'\n');print(len(metadata),'editable scene parts')
