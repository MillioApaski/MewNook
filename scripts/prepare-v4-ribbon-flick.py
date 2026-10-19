#!/usr/bin/env python3
from pathlib import Path
import json,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v6';(O/'inputs').mkdir(parents=True,exist_ok=True)
s=Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA');W,H=s.size
curves=[(687,182),((691,181),(697,180),(701,180)),((704,199),(716,215),(734,218)),((739,219),(742,217),(744,215)),((741,223),(730,223),(716,220)),((704,218),(694,213),(689,205)),((687,198),(687,188),(687,182))]
points=[np.array(curves[0],float)];p=points[0]
for c1,c2,end in curves[1:]:
 a,b,e=map(lambda z:np.array(z,float),(c1,c2,end))
 for t in np.linspace(0,1,100)[1:]:points.append((1-t)**3*p+3*(1-t)**2*t*a+3*(1-t)*t*t*b+t**3*e)
 p=e
m=Image.new('L',(W*8,H*8));ImageDraw.Draw(m).polygon([tuple(p*8) for p in points],fill=255);m=m.resize((W,H),Image.Resampling.LANCZOS);m.save(O/'ribbon-flick-mask.png')
a=np.array(s);mask=np.array(m)>128;guide=a.copy();guide[mask,:3]=np.round(a[mask,:3]*.5+np.array([235,35,160])*.5).astype('uint8')
s.crop((660,175,760,245)).resize((1000,700)).save(O/'inputs/ribbon-flick-source.png');Image.fromarray(guide).crop((660,175,760,245)).resize((1000,700)).save(O/'inputs/ribbon-flick-guide.png')
a[:,:,3]=np.round(a[:,:,3].astype(float)*np.array(m)/255).astype('uint8');a[a[:,:,3]==0,:3]=0;im=Image.fromarray(a);box=im.getbbox();im.crop(box).save(O/'ribbon-flick-source.png');(O/'manifest.json').write_text(json.dumps({'canvas':[W,H],'parts':[{'file':'ribbon-flick-source.png','offset':list(box[:2]),'stage':'source_selection_pending_underpaint'}]},indent=2)+'\n');print(box)
# Wider original crop and annotation for the separate right-bow hidden repaint.
a=np.array(s);rgb=a[:,:,:3].astype(int);roi=np.zeros((H,W),bool);roi[135:322,689:820]=True
navy=roi&(rgb[:,:,2]-rgb[:,:,0]>20)&(rgb[:,:,2]-rgb[:,:,1]>8)&(rgb[:,:,0]<150)&(a[:,:,3]>100)
guide=a.copy();guide[navy,:3]=np.round(guide[navy,:3]*.4+np.array([235,35,160])*.6).astype('uint8')
s.crop((660,130,820,335)).resize((800,1025)).save(O/'inputs/right-bow-source.png');Image.fromarray(guide).crop((660,130,820,335)).resize((800,1025)).save(O/'inputs/right-bow-guide.png')
