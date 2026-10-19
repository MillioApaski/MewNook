from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v5';(O/'inputs').mkdir(parents=True,exist_ok=True)
s=Image.open(R/'assets/inochi/v4/hair-source-v4/crown-without-ahoge.png').convert('RGBA');w,h=s.size
curves=[(443,99),((464,70),(503,53),(535,51)),((558,50),(579,53),(596,58)),((590,64),(585,70),(580,76)),((566,71),(550,70),(539,82)),((535,87),(532,92),(530,98)),((515,88),(497,92),(484,102)),((468,113),(451,137),(440,160)),((437,140),(438,118),(443,99))]
points=[np.array(curves[0],float)];p=points[0]
for c1,c2,end in curves[1:]:
 a,b,e=map(lambda z:np.array(z,float),(c1,c2,end))
 for t in np.linspace(0,1,100)[1:]:points.append((1-t)**3*p+3*(1-t)**2*t*a+3*(1-t)*t*t*b+t**3*e)
 p=e
m=Image.new('L',(w*4,h*4));ImageDraw.Draw(m).polygon([tuple(p*4) for p in points],fill=255);m=m.resize((w,h),Image.Resampling.LANCZOS);m.save(O/'crown-mask.png')
a=np.array(s);mask=np.array(m)>128;guide=a.copy();guide[mask,:3]=np.round(a[mask,:3]*.5+np.array([230,35,160])*.5).astype('uint8')
s.crop((400,25,725,245)).resize((1300,880)).save(O/'inputs/head-no-ahoge.png');Image.fromarray(guide).crop((400,25,725,245)).resize((1300,880)).save(O/'inputs/crown-guide.png')
a[:,:,3]=np.round(a[:,:,3].astype(float)*np.array(m)/255).astype('uint8');im=Image.fromarray(a);box=im.getbbox();im.crop(box).save(O/'crown-source.png');print('Crown offset',box[:2])
