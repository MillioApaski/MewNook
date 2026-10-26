#!/usr/bin/env python3
"""Register painted focus torsos; split the forearms at the same source seam."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
from v4_source_io import export_ora
R=Path(__file__).resolve().parents[1];V=R/'assets/inochi/v4';O=V/'focus-source-v1';W,H=1122,1402
native=np.array(Image.open(V/'scene-source-v1/part-19.png').convert('RGBA'))
clean=np.array(Image.open(O/'inputs/clean-body-painted.png').convert('RGBA').resize((481,488),Image.Resampling.LANCZOS))
report={'canvas':[W,H],'offset':[345,375],'split_source_y':695,'poses':{}}
for pose in ('typing','reading'):
 a=np.array(Image.open(O/'inputs'/(pose+'-painted.png')).convert('RGBA').resize((481,650),Image.Resampling.LANCZOS))
 # Lock original neck, collar and shoulders. The painted arm study is used
 # only below the original upper torso; the character's face is never edited.
 n=np.zeros_like(a);n[:native.shape[0]]=native
 weight=np.clip((np.arange(650)-190)/90,0,1)[:,None,None]
 a=np.round(n*(1-weight)+a*weight).astype('uint8')
 assert np.array_equal(a[:190],native[:190])
 back=a.copy();front=a.copy();back[320:]=0;back[320:488]=clean[320:488];front[:320]=0
 for label,tile in [('body',back),('hands',front)]:
  full=Image.new('RGBA',(W,H));full.alpha_composite(Image.fromarray(tile),(345,375));full.save(O/(pose+'-'+label+'.png'))
 full_body=np.array(Image.open(O/(pose+'-body.png')));full_hands=np.array(Image.open(O/(pose+'-hands.png')));composite=Image.alpha_composite(Image.fromarray(full_body),Image.fromarray(full_hands))
 export_ora(O/(pose+'-focus.ora'),np.array(composite),[('Foreground forearms and prop',full_hands),('Behind-desk torso backing',full_body)],pose+' focus source layers')
 report['poses'][pose]={'original_upper_torso_exact':True,'body_sha256':hashlib.sha256((O/(pose+'-body.png')).read_bytes()).hexdigest(),'hands_sha256':hashlib.sha256((O/(pose+'-hands.png')).read_bytes()).hexdigest()}
report['desk_patches']={}
for scene,box in {'day':(190,730,770,900),'rain':(200,730,825,910),'sunset':(180,735,815,910),'night':(250,695,945,905)}.items():
 painted=np.array(Image.open(O/'inputs'/(scene+'-desk-painted.png')).convert('RGBA').resize((1672,941),Image.Resampling.LANCZOS))
 yy,xx=np.mgrid[:941,:1672];x0,y0,x1,y1=box
 alpha=np.clip(np.minimum.reduce([(xx-x0)/12,(x1-xx)/12,(yy-y0)/12,(y1-yy)/12,np.ones_like(xx)]),0,1)
 original=np.array(Image.open(R/'public/assets/rooms'/scene/('background.webp' if scene=='day' else 'foreground.webp')).convert('RGBA'))
 painted[:,:,3]=np.where(original[:,:,3]>128,np.round(alpha*255),0).astype('uint8');painted[painted[:,:,3]==0]=0
 output=R/'public/inochi2d/v4'/('focus-desk-'+scene+'.png');Image.fromarray(painted).save(output)
 report['desk_patches'][scene]={'native_box':list(box),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'outside_box_transparent':True}
(O/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
