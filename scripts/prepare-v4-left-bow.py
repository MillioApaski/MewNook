#!/usr/bin/env python3
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v7';(O/'inputs').mkdir(parents=True,exist_ok=True)
im=Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA');a=np.array(im);H,W=a.shape[:2];C=a[:,:,:3].astype(int);roi=np.zeros((H,W),bool);roi[200:390,330:415]=True
navy=roi&(C[:,:,2]-C[:,:,0]>20)&(C[:,:,2]-C[:,:,1]>8)&(C[:,:,0]<150)&(a[:,:,3]>100)
g=a.copy();g[navy,:3]=np.round(g[navy,:3]*.4+np.array([235,35,160])*.6).astype('uint8')
im.crop((320,185,450,400)).resize((650,1075)).save(O/'inputs/left-bow-source.png');Image.fromarray(g).crop((320,185,450,400)).resize((650,1075)).save(O/'inputs/left-bow-guide.png')
curves=[(407,214),((407,230),(400,247),(396,266)),((393,279),(400,293),(418,304)),((419,302),(418,300),(416,298)),((403,289),(397,278),(400,266)),((402,248),(412,230),(412,215)),((410,214),(409,214),(407,214))]
points=[np.array(curves[0],float)];p=points[0]
for c1,c2,end in curves[1:]:
 b,c,d=map(lambda q:np.array(q,float),(c1,c2,end))
 for t in np.linspace(0,1,100)[1:]:points.append((1-t)**3*p+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d)
 p=d
m=Image.new('L',(W*4,H*4));ImageDraw.Draw(m).polygon([tuple(p*4) for p in points],fill=255);m=m.resize((W,H),Image.Resampling.LANCZOS);m.save(O/'white-curl-mask.png');sel=(np.array(m)>128)&(C.mean(2)>140);g=a.copy();g[sel,:3]=np.round(g[sel,:3]*.5+np.array([235,35,160])*.5).astype('uint8');Image.fromarray(g).crop((320,185,450,400)).resize((650,1075)).save(O/'inputs/white-curl-guide.png')
