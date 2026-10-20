#!/usr/bin/env python3
"""Select original side-head/neck connector hair not owned by earlier parts."""
from pathlib import Path
import io,json,zipfile,xml.etree.ElementTree as ET
import cv2,numpy as np
from PIL import Image,ImageDraw
from v4_image_io import atomic_png
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v10';O.mkdir(exist_ok=True);(O/'inputs').mkdir(exist_ok=True)
src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];C=src[:,:,:3].astype(int);occupied=np.zeros((H,W),bool);occluders=np.zeros((H,W),bool)
with zipfile.ZipFile(R/'assets/inochi/v4/hair-source-v9/MewNook-v4-outer-hair-source.ora') as z:
 for n in ET.fromstring(z.read('stack.xml')).find('stack').find('stack'):
  if n.get('name')=='hidden paint and original remainder':continue
  a=np.array(Image.open(io.BytesIO(z.read(n.get('src')))).convert('RGBA'));x,y=int(n.get('x')),int(n.get('y'));occupied[y:y+a.shape[0],x:x+a.shape[1]]|=a[:,:,3]>32
  if n.get('name') not in ['stationary brows','stationary eye corner']:occluders[y:y+a.shape[0],x:x+a.shape[1]]|=a[:,:,3]>220
garments=Image.new('L',(W,H));draw=ImageDraw.Draw(garments)
draw.polygon([(445,377),(474,377),(485,393),(474,425),(430,450),(401,450),(409,427),(418,404),(430,388)],fill=255)
draw.polygon([(704,390),(724,381),(745,387),(769,407),(792,430),(815,450),(700,450)],fill=255)
draw.rectangle((625,386,662,450),fill=255);garments=np.array(garments)>0
polys={'left':[(411,202),(435,202),(443,235),(457,267),(462,298),(476,317),(491,331),(501,361),(486,387),(474,417),(441,433),(411,438),(394,423),(389,396),(396,371),(396,339),(399,305),(396,274),(401,238)],'right':[(700,181),(736,187),(751,231),(764,273),(773,309),(795,353),(811,397),(797,434),(756,431),(723,424),(689,410),(673,393),(640,399),(630,383),(634,354),(641,325),(663,299),(681,276),(690,238)]}
yy,xx=np.indices((H,W));skin=(C[:,:,0]-C[:,:,2]>10)&(C[:,:,0]-C[:,:,1]>5)&(src[:,:,3]>220)&(xx>445)&(xx<690)&(yy>200)&(yy<430)
foreground=skin|(garments&(src[:,:,3]>220));atomic_png(Image.fromarray(foreground.astype('uint8')*255),O/'face-clothing-occlusion-mask.png')
union=np.zeros((H,W),bool);counts={}
for side,poly in polys.items():
 im=Image.new('L',(W,H));ImageDraw.Draw(im).polygon(poly,fill=255);scope=np.array(im)>0
 mask=scope&~occupied&~garments&(src[:,:,3]>32)&(C[:,:,2]-C[:,:,0]>=-10)&(C[:,:,2]-C[:,:,1]>=-5)&(C.mean(2)>100)
 outlines,_=cv2.findContours(mask.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);filled=np.zeros((H,W),np.uint8);cv2.drawContours(filled,outlines,-1,1,-1);mask=filled.astype(bool)&scope&~occupied&~foreground&(src[:,:,3]>32)
 n,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype('uint8'),8);ids=np.flatnonzero(stats[:,cv2.CC_STAT_AREA]>=12);mask=np.isin(labels,ids[ids!=0]);union|=mask
 atomic_png(Image.fromarray(mask.astype('uint8')*255),O/(side+'-connector-mask.png'));atomic_png(Image.fromarray(scope.astype('uint8')*255),O/(side+'-scope.png'));counts[side]=int(mask.sum())
 guide=src.copy();guide[mask]=[235,35,160,255];atomic_png(Image.fromarray(guide).crop((350,175,815,450)).resize((1116,660)),O/('inputs/'+side+'-connector-guide.png'))
atomic_png(Image.fromarray(occupied.astype('uint8')*255),O/'prior-visible-part-mask.png')
hidden=cv2.dilate(union.astype('uint8'),np.ones((11,11),np.uint8)).astype(bool)&occluders&~union
atomic_png(Image.fromarray(hidden.astype('uint8')*255),O/'connector-hidden-margin-mask.png');atomic_png(Image.fromarray(occluders.astype('uint8')*255),O/'prior-hair-occluder-mask.png')
material=src.copy();material[~union]=0;atomic_png(Image.fromarray(material).crop((350,175,815,450)).resize((1116,660)),O/'inputs/connector-materials.png');material[hidden]=[235,35,160,255];atomic_png(Image.fromarray(material).crop((350,175,815,450)).resize((1116,660)),O/'inputs/hidden-connector-guide.png')
atomic_png(Image.fromarray(union.astype('uint8')*255),O/'connector-union-mask.png');atomic_png(Image.fromarray(src).crop((350,175,815,450)).resize((1116,660)),O/'inputs/connector-source.png')
report={'source_crop':[350,175,815,450],'sheet_size':[1116,660],'visible_selected_pixels':counts,'selection':'source colour and traced scope, excluding previous working part footprints','remaining':'Review selection before consuming hidden paint; source only, not rigged'};(O/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
