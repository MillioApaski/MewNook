#!/usr/bin/env python3
from pathlib import Path
import json,cv2,numpy as np
from PIL import Image,ImageDraw
from v4_image_io import install_atomic_png_saves
install_atomic_png_saves()
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v9';(O/'inputs').mkdir(parents=True,exist_ok=True)
s=Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA');src=np.array(s);H,W=src.shape[:2];C=src[:,:,:3].astype(int);yy,xx=np.indices((H,W));cv2.setRNGSeed(0)
contours={
'left':[(120,375),(405,375),(420,410),(410,455),(408,500),(414,548),(418,600),(426,650),(428,695),(407,728),(382,753),(370,780),(371,812),(352,837),(331,863),(321,888),(339,911),(336,935),(316,960),(288,991),(120,1000)],
'right':[(755,335),(1010,335),(1010,1005),(815,1005),(800,901),(821,875),(826,846),(809,819),(797,783),(773,753),(772,711),(778,667),(779,607),(773,548),(763,500),(758,430)]}
meta=[]
for side,points in contours.items():
 im=Image.new('L',(W,H));ImageDraw.Draw(im).polygon(points,fill=255);candidate=np.array(im)>0
 navy=(C[:,:,0]<150)&(C[:,:,2]-C[:,:,0]>.25*np.maximum(C[:,:,2],1))&(C[:,:,2]-C[:,:,1]>8)
 cream=(C[:,:,0]-C[:,:,2]>9)&(C[:,:,1]-C[:,:,2]>5)&((xx>375) if side=='left' else (xx<835))
 stool=(C[:,:,0]-C[:,:,2]>25)&(C[:,:,0]-C[:,:,1]>20)
 tail=np.zeros((H,W),bool)
 if side=='right':
  warm=(xx>918)&(yy>440)&(yy<880)&(C[:,:,0]-C[:,:,2]>3)&(src[:,:,3]>200)
  n,tail_labels=cv2.connectedComponents(warm.astype('uint8'),8);ids={int(tail_labels[y,x]) for x,y in [(1000,500),(980,580),(1000,720)]};ids.discard(0);tail=np.isin(tail_labels,list(ids))
  Image.fromarray(tail.astype('uint8')*255).save(O/'original-cat-tail-protection-mask.png')
 bg=(src[:,:,3]<32)|navy|cream|stool|tail
 inner=cv2.erode(candidate.astype('uint8'),np.ones((7,7),np.uint8)).astype(bool)
 fg=inner&(src[:,:,3]>240)&(C[:,:,2]-C[:,:,0]>=0)&(C[:,:,2]-C[:,:,1]>=0)&~bg
 labels=np.where(candidate,cv2.GC_PR_FGD,cv2.GC_BGD).astype('uint8');labels[bg]=cv2.GC_BGD;labels[fg]=cv2.GC_FGD
 bmodel=np.zeros((1,65),np.float64);fmodel=np.zeros((1,65),np.float64);cv2.grabCut(src[:,:,:3].copy(),labels,None,bmodel,fmodel,4,cv2.GC_INIT_WITH_MASK)
 selected=((labels==cv2.GC_FGD)|(labels==cv2.GC_PR_FGD))&candidate
 # These are source-pixel selections, not replacement painted silhouettes.
 Image.fromarray(selected.astype('uint8')*255).save(O/(side+'-outer-mask.png'));Image.fromarray(candidate.astype('uint8')*255).save(O/(side+'-scope.png'))
 a=src.copy();a[:,:,3]=np.where(selected,src[:,:,3],0);a[a[:,:,3]==0,:3]=0;im=Image.fromarray(a);box=im.getbbox();im.crop(box).save(O/(side+'-outer-source.png'))
 guide=src.copy();guide[selected,:3]=np.round(guide[selected,:3]*.5+np.array([235,35,160])*.5).astype('uint8');Image.fromarray(guide).crop((120,330,1010,1010)).resize((1068,816)).save(O/('inputs/'+side+'-outer-guide.png'))
 meta.append({'file':side+'-outer-source.png','offset':list(box[:2]),'visible_pixels':int(selected.sum()),'stage':'source_selection_requires_occlusion_review'})
s.crop((120,330,1010,1010)).resize((1068,816)).save(O/'inputs/outer-body-source.png');(O/'manifest.json').write_text(json.dumps({'canvas':[W,H],'stage':'outer_hair_source_selections','parts':meta},indent=2)+'\n');print(meta)
