#!/usr/bin/env python3
"""Trace original right face-framing hair and crown; no substitute graphics."""
from pathlib import Path
import json,cv2,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/inochi/v4/hair-source-v3';OUT.mkdir(exist_ok=True)
src=np.array(Image.open(ROOT/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2]
face=ROOT/'assets/inochi/v4/face-source-v4';pin=ROOT/'assets/inochi/v4/hair-source-v1'
clean=np.array(Image.open(face/'source-narrow-brow-repair.png').convert('RGBA'))
p=np.array(Image.open(pin/'hairpin-hidden-hair.png').convert('RGBA'));pm=p[:,:,3]>0;clean[120:195,605:680,:3][pm]=p[pm,:3]
contours={
'right-face-frame':[(530,98),((552,96),(584,109),(606,134)),((631,157),(646,191),(650,225)),((660,245),(658,275),(633,300)),((660,296),(679,280),(681,261)),((684,237),(675,206),(654,177)),((632,139),(595,105),(553,82)),((542,83),(535,89),(530,98))],
'crown-visible':[(442,100),((463,65),(500,50),(535,51)),((565,50),(590,59),(612,76)),((590,68),(572,65),(554,71)),((542,77),(533,88),(530,98)),((512,88),(497,92),(484,102)),((468,113),(451,137),(440,160)),((437,140),(438,118),(442,100))],
}
def mask_for(contour):
    points=[np.array(contour[0],float)];p=points[0]
    for c1,c2,e in contour[1:]:
        a,b,end=map(lambda x:np.array(x,float),(c1,c2,e))
        for t in np.linspace(0,1,120)[1:]:points.append((1-t)**3*p+3*(1-t)**2*t*a+3*(1-t)*t*t*b+t**3*end)
        p=end
    m=Image.new('L',(W*4,H*4));ImageDraw.Draw(m).polygon([tuple(p*4) for p in points],fill=255)
    return np.array(m.resize((W,H),Image.Resampling.LANCZOS))
parts=[]
for name,contour in contours.items():
    mask=mask_for(contour);a=clean.copy();a[:,:,3]=np.round(mask.astype(float)*src[:,:,3]/255).astype(np.uint8);a[a[:,:,3]==0,:3]=0
    im=Image.fromarray(a);box=im.getbbox();im.crop(box).save(OUT/(name+'.png'));Image.fromarray(mask).save(OUT/(name+'-mask.png'))
    outline=src.copy();cs,_=cv2.findContours((mask>128).astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);cv2.drawContours(outline,cs,-1,(0,160,100,255),1)
    Image.fromarray(outline).crop((420,35,765,395)).resize((1035,1080),Image.Resampling.NEAREST).save(OUT/(name+'-source-contour.png'))
    parts.append({'file':name+'.png','offset':list(box[:2]),'contour':contour,'stage':'source_selection_needs_occlusion_review'})
    if name=='right-face-frame':
        guide=src.copy();selected=mask>128;guide[selected,:3]=np.round(.55*src[selected,:3]+.45*np.array([230,35,160])).astype(np.uint8)
        Image.fromarray(guide).crop((420,35,765,395)).resize((1035,1080),Image.Resampling.LANCZOS).save(OUT/'inputs/right-face-frame-guide.png')
(OUT/'manifest.json').write_text(json.dumps({'stage':'source_trace_candidates_not_finished_hair','canvas':[W,H],'parts':parts,'remaining':['Refine crown boundary at ear overlap','Hidden surface painting for right face-framing hair','Outer flick beside ribbon','Side and back hair']},ensure_ascii=False,indent=2)+'\n')
print('Traced source selections:',[p['file'] for p in parts])
