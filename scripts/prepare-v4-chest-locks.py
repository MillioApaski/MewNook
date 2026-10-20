#!/usr/bin/env python3
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v8';(O/'inputs').mkdir(parents=True,exist_ok=True)
s=Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA');a=np.array(s);H,W=a.shape[:2];C=a[:,:,:3].astype(int)
# Original contour points in the 3x local chest crop (420,325)-(765,675).
contours={
'left':[(220,0),(300,0),(350,90),(382,175),(402,250),(397,305),(370,348),(354,380),(351,446),(369,489),(414,546),(452,596),(479,657),(479,708),(462,751),(425,785),(407,827),(407,868),(433,900),(477,925),(448,941),(402,943),(359,930),(324,906),(299,875),(277,835),(276,786),(292,729),(292,677),(277,635),(250,602),(225,571),(209,528),(202,478),(211,432),(214,388),(205,345),(225,295),(251,249),(265,205),(266,155),(251,101),(233,55)],
'right':[(697,0),(797,0),(811,75),(830,150),(849,221),(873,295),(887,365),(891,426),(869,486),(831,529),(793,565),(771,604),(780,650),(821,693),(862,736),(885,779),(882,816),(854,850),(811,874),(767,890),(728,915),(700,948),(708,977),(743,997),(782,979),(753,1011),(715,1025),(682,1018),(661,995),(652,964),(657,934),(674,901),(693,866),(707,829),(710,795),(697,752),(682,711),(681,669),(695,626),(716,589),(739,552),(759,517),(774,478),(785,430),(788,379),(776,326),(756,278),(733,231),(714,182),(703,129),(697,68)]}
for side,points in contours.items():
 m=Image.new('L',(W*4,H*4));d=ImageDraw.Draw(m);d.polygon([((420+x/3)*4,(325+y/3)*4) for x,y in points],fill=255);m=m.resize((W,H),Image.Resampling.LANCZOS)
 mask=np.array(m);Image.fromarray(mask).save(O/(side+'-contour-mask.png'))
 # Remove clearly navy cloth from the hair selection, including holes between fine curls.
 navy=(C[:,:,2]-C[:,:,0]>20)&(C[:,:,2]-C[:,:,1]>8)&(C[:,:,0]<160)
 mask[navy]=0;Image.fromarray(mask).save(O/(side+'-hair-mask.png'))
 guide=a.copy();sel=mask>128;guide[sel,:3]=np.round(guide[sel,:3]*.5+np.array([235,35,160])*.5).astype('uint8');Image.fromarray(guide).crop((420,325,765,675)).resize((1035,1050)).save(O/('inputs/'+side+'-lock-guide.png'))
s.crop((420,325,765,675)).resize((1035,1050)).save(O/'inputs/chest-source.png')
