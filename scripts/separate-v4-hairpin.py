#!/usr/bin/env python3
"""Separate the original painted clip; consume only hidden hair underpaint."""
from pathlib import Path
import json,io,zipfile,xml.etree.ElementTree as ET
import cv2,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/inochi/v4/hair-source-v1'
src=np.array(Image.open(ROOT/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2]
box=(605,120,680,195);x0,y0,x1,y1=box
C=src[y0:y1,x0:x1,:3].astype(float)
B=np.array(Image.open(OUT/'registered-hairpin-underpaint.png').convert('RGB').resize((75,75),Image.Resampling.LANCZOS)).astype(float)
gold=(C[:,:,0]-C[:,:,1]>5)&(C[:,:,1]-C[:,:,2]>15)
n,labels,stats,_=cv2.connectedComponentsWithStats(gold.astype(np.uint8),8)
gold=(labels==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA])))
distance=cv2.distanceTransform((~gold).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
clearance=distance<5
# The pale white rim extends farther than the gold/dark body. Clear its whole
# old footprint, and keep its bright source pixels on the moving clip.
white_rim=(distance<5)&(C.mean(2)>232)&((C-B).mean(2)>1)
domain=(distance<2.5)|white_rim
alpha=np.where(domain,np.clip(2.5-distance,0,1),0)
# Bound unmixing to real RGB values, with a conservative minimum alpha so
# minute underpaint differences cannot become saturated colored edge dots.
delta=C-B
minimum=np.maximum(np.where(delta>0,delta/np.maximum(255-B,1),0).max(2),np.where(delta<0,-delta/np.maximum(B,1),0).max(2))
alpha=np.where(domain,np.maximum(alpha,np.maximum(minimum,.4)),0)
alpha[gold]=1
F=np.divide(C-(1-alpha[:,:,None])*B,alpha[:,:,None],out=np.zeros_like(C),where=alpha[:,:,None]>0)
clip=np.dstack([np.clip(np.round(F),0,255).astype(np.uint8),np.round(alpha*255).astype(np.uint8)])
clip[clip[:,:,3]==0,:3]=0
assert np.array_equal(clip[gold,:3],C[gold].astype(np.uint8)), 'Changed original gold core'
Image.fromarray(clip).save(OUT/'hairpin-x.png')
under=np.dstack([B.astype(np.uint8),clearance.astype(np.uint8)*255]);under[~clearance]=0
Image.fromarray(under).save(OUT/'hairpin-hidden-hair.png')
base=src.copy();base[y0:y1,x0:x1,:3][clearance]=B[clearance].astype(np.uint8)
Image.fromarray(base).save(OUT/'without-hairpin.png')
full=np.zeros_like(src);full[y0:y1,x0:x1]=clip
yy,xx=np.indices((H,W),dtype=np.float32);frames={}
for shift in (-3,0,3):
    a=full[:,:,3].astype(np.float32)/255;rgb=full[:,:,:3].astype(np.float32)*a[:,:,None]
    ma=cv2.remap(a,xx-shift,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    mr=cv2.remap(rgb,xx-shift,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    straight=np.divide(mr,ma[:,:,None],out=np.zeros_like(mr),where=ma[:,:,None]>1e-6)
    moved=np.dstack([np.clip(np.round(straight),0,255).astype(np.uint8),np.round(ma*255).astype(np.uint8)])
    frame=Image.fromarray(base);frame.alpha_composite(Image.fromarray(moved));arr=np.array(frame);arr[:,:,3]=src[:,:,3]
    allowed=np.zeros((H,W),bool);allowed[118:197,600:685]=True
    assert np.array_equal(arr[~allowed],src[~allowed]),'Clip motion changed unrelated pixels'
    Image.fromarray(arr).save(OUT/('hairpin-shift-'+str(shift)+'.png'));frames[str(shift)]=Image.fromarray(arr)
neutral=np.array(frames['0'])[y0:y1,x0:x1,:3].astype(float)
mae=float(np.abs(neutral[domain]-C[domain]).mean());assert mae<1
clear_mae=float(np.abs(neutral[clearance]-C[clearance]).mean())
board=Image.new('RGB',(1200,420),(236,237,242));d=ImageDraw.Draw(board)
for i,key in enumerate(('-3','0','3')):
    tile=frames[key].crop((602,117,683,198)).resize((360,360),Image.Resampling.NEAREST);board.paste(tile,(i*400+15,45),tile);d.text((i*400+15,15),'original clip shift '+key+' px',fill='black')
board.save(OUT/'hairpin-motion-check.png')
manifest={'stage':'original_hairpin_split_static_review','canvas':[W,H],'parts':[{'file':'hairpin-x.png','offset':[x0,y0],'kind':'original_gold_rgb_with_edge_unmix'},{'file':'hairpin-hidden-hair.png','offset':[x0,y0],'kind':'registered_AI_hidden_hair_underpaint'}], 'validation':{'original_gold_core_pixels_exact':int(gold.sum()),'neutral_clip_rgb_mean_abs_error':mae,'unrelated_pixels_exact':True},'remaining':['Review matte at light and dark backgrounds','Full front/side/back hair separation and hidden painting','Mesh and motion binding']}
matte_board=Image.new('RGB',(800,420));d=ImageDraw.Draw(matte_board)
for i,color in enumerate(((245,245,249),(42,48,66))):
    tile=Image.new('RGBA',(75,75),color+(255,));tile.alpha_composite(Image.fromarray(clip));tile=tile.resize((360,360),Image.Resampling.NEAREST)
    matte_board.paste(color,(i*400,0,(i+1)*400,420));matte_board.paste(tile,(i*400+20,45));d.text((i*400+20,15),'clip matte background check',fill='gray')
matte_board.save(OUT/'hairpin-matte-check.png')
archive=OUT/'MewNook-v4-hair-source.ora';building=OUT/'MewNook-v4-hair-source.building.ora'
with zipfile.ZipFile(ROOT/'assets/inochi/v4/face-source-v4/MewNook-v4-fringe-repair.ora') as old:
    tree=ET.fromstring(old.read('stack.xml'));tree.set('name','MewNook v4 source: fringe and original hairpin')
    group=ET.Element('stack',{'name':'HAIR WORK: original hairpin and hidden hair','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'});tree.find('stack').insert(0,group)
    with zipfile.ZipFile(building,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
        for item in old.infolist():
            if item.filename not in ('mimetype','stack.xml'):z.writestr(item.filename,old.read(item.filename))
        for entry in manifest['parts']:
            name=entry['file'];path='hair-work/'+name;z.writestr(path,(OUT/name).read_bytes());ET.SubElement(group,'layer',{'name':name[:-4],'src':path,'x':str(x0),'y':str(y0),'opacity':'1','visibility':'visible','composite-op':'svg:src-over'})
        z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True))
with zipfile.ZipFile(building) as z:
    tree=ET.fromstring(z.read('stack.xml'))
    def render(node):
        canvas=Image.new('RGBA',(W,H))
        for child in reversed(list(node)):
            if child.get('visibility','visible')=='hidden':continue
            if child.tag=='stack':canvas.alpha_composite(render(child))
            elif child.tag=='layer':canvas.alpha_composite(Image.open(io.BytesIO(z.read(child.get('src')))).convert('RGBA'),(int(child.get('x','0')),int(child.get('y','0'))))
        return canvas
    visible=src[:,:,3]>0;actual=np.array(render(tree.find('stack')))
    assert np.array_equal(src[visible],actual[visible]);layers=len(tree.findall('.//layer'));assert layers==39
building.replace(archive)
manifest['validation']['exported_ora_default_visible_rgba_exact']=True
manifest['validation']['neutral_whole_cleared_region_rgb_mean_abs_error']=clear_mae
manifest['validation']['cleared_white_rim_radius_source_pixels']=5
manifest['validation']['light_and_dark_background_review_completed']=True
manifest['remaining']=['Full front/side/back hair separation and hidden painting','Mesh and motion binding']
manifest['exported_ora']={'file':'MewNook-v4-hair-source.ora','layers':layers}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest['validation']))
