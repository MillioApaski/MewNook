#!/usr/bin/env python3
"""Joint static check of source-derived fringe parts, not runtime acceptance."""
from pathlib import Path
import json,io,zipfile,xml.etree.ElementTree as ET
import numpy as np,cv2
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/inochi/v4/hair-source-v2'
FACE=ROOT/'assets/inochi/v4/face-source-v4';PIN=ROOT/'assets/inochi/v4/hair-source-v1'
src=np.array(Image.open(ROOT/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2]
def full(root,name,offset):
    im=np.array(Image.open(root/name).convert('RGBA'));a=np.zeros_like(src);x,y=offset;a[y:y+im.shape[0],x:x+im.shape[1]]=im;return a
fm=json.loads((FACE/'manifest.json').read_text());rm=json.loads((OUT/'manifest.json').read_text())
left=next(p for p in fm['parts'] if p['file']=='front-left.png');center=next(p for p in fm['parts'] if p['file']=='front-center.png');right=rm['parts'][0]
parts=[('right-inner',full(OUT,right['file'],right['offset']),130,225,.65),('left',full(FACE,left['file'],left['offset']),155,270,.75),('center',full(FACE,center['file'],center['offset']),155,270,1.0),('pin',full(PIN,'hairpin-x.png',[605,120]),130,225,.65)]
base=np.array(Image.open(FACE/'assembly-base.png').convert('RGBA'))
under=full(OUT,rm['parts'][1]['file'],rm['parts'][1]['offset']);ua=under[:,:,3:4].astype(float)/255
base[:,:,:3]=np.round(base[:,:,:3]*(1-ua)+under[:,:,:3]*ua).astype(np.uint8)
pin_under=full(PIN,'hairpin-hidden-hair.png',[605,120]);pm=pin_under[:,:,3]>0;base[pm,:3]=pin_under[pm,:3]
Image.fromarray(base).save(OUT/'front-assembly-base.png')
brows=np.array(Image.open(FACE/'brows-working-matte.png').convert('RGBA'))
yy,xx=np.indices((H,W),dtype=np.float32)
def moved(a,shift,root,tip,gain):
    weight=np.clip((yy-root)/(tip-root),0,1);mx=xx-shift*gain*weight
    alpha=a[:,:,3].astype(np.float32)/255;premul=a[:,:,:3].astype(np.float32)*alpha[:,:,None]
    ma=cv2.remap(alpha,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);mr=cv2.remap(premul,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    rgb=np.divide(mr,ma[:,:,None],out=np.zeros_like(mr),where=ma[:,:,None]>1e-6)
    return Image.fromarray(np.dstack([np.clip(np.round(rgb),0,255).astype(np.uint8),np.round(ma*255).astype(np.uint8)]))
iris=np.zeros((H,W),bool);imeta=json.loads((ROOT/'assets/inochi/v4/face-source-v2/manifest.json').read_text())
for side in ('left','right'):
    p=next(p for p in imeta['working_parts'] if p['file']==side+'-iris-visible.png');iris|=full(ROOT/'assets/inochi/v4/face-source-v2',p['file'],p['offset'])[:,:,3]>0
frames={};neutral=None
for shift in (-6,-3,0,3,6):
    canvas=Image.fromarray(base)
    for name,a,root,tip,gain in parts:canvas.alpha_composite(moved(a,shift,root,tip,gain))
    canvas.alpha_composite(Image.fromarray(brows));arr=np.array(canvas)
    assert np.array_equal(arr[iris,:3],src[iris,:3]),'Front hair changed source iris pixels'
    outside=np.ones((H,W),bool);outside[80:295,455:685]=False
    # Source eyebrow cleanup extends beyond the three locks. Include precisely
    # those documented edited pixels rather than declaring a whole face free.
    outside&=~np.any(base[:,:,:3]!=src[:,:,:3],axis=2);outside&=~(brows[:,:,3]>0)
    assert np.array_equal(arr[outside,:3],src[outside,:3]),'Assembly changed unrelated source RGB'
    if shift==0:neutral=canvas.copy()
    arr[:,:,3]=src[:,:,3];frames[str(shift)]=Image.fromarray(arr);frames[str(shift)].save(OUT/('front-assembly-shift-'+str(shift)+'.png'))
for label,keys in [('front-assembly-motion',('-6','0','6')),('front-assembly-small-motion',('-3','0','3'))]:
    board=Image.new('RGB',(1200,480),(236,237,242));d=ImageDraw.Draw(board)
    for i,key in enumerate(keys):
        tile=frames[key].crop((455,90,690,350)).resize((360,398),Image.Resampling.NEAREST);board.paste(tile,(i*400+15,45),tile);d.text((i*400+15,15),'joint fringe shift '+key,fill='black')
    board.save(OUT/(label+'.png'))
# A single hidden assembly group is reviewable without enabling overlapping
# alternative-material collections from older source iterations.
with zipfile.ZipFile(OUT/'MewNook-v4-hair-source-v2.ora') as old:
    tree=ET.fromstring(old.read('stack.xml'));group=ET.Element('stack',{'name':'JOINT FRONT ASSEMBLY CHECK — incomplete head','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'});tree.find('stack').insert(0,group)
    entries=[('brows',brows)]+[(name,a) for name,a,*_ in reversed(parts)]+[('underpaint-base',base)]
    with zipfile.ZipFile(OUT/'MewNook-v4-front-assembly.ora','w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
        for item in old.infolist():
            if item.filename not in ('mimetype','stack.xml'):z.writestr(item.filename,old.read(item.filename))
        for name,a in entries:
            im=Image.fromarray(a);box=im.getbbox();im=im.crop(box);buf=io.BytesIO();im.save(buf,format='PNG');path='joint-front/'+name+'.png';z.writestr(path,buf.getvalue())
            ET.SubElement(group,'layer',{'name':name,'src':path,'x':str(box[0]),'y':str(box[1]),'opacity':'1','visibility':'visible','composite-op':'svg:src-over'})
        z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True))
with zipfile.ZipFile(OUT/'MewNook-v4-front-assembly.ora') as z:
    tree=ET.fromstring(z.read('stack.xml'))
    def render(node,include_hidden=False):
        canvas=Image.new('RGBA',(W,H))
        for child in reversed(list(node)):
            if child.get('visibility','visible')=='hidden' and not include_hidden:continue
            if child.tag=='stack':canvas.alpha_composite(render(child))
            elif child.tag=='layer':canvas.alpha_composite(Image.open(io.BytesIO(z.read(child.get('src')))).convert('RGBA'),(int(child.get('x','0')),int(child.get('y','0'))))
        return canvas
    actual=np.array(render(tree.find('stack')));visible=src[:,:,3]>0;assert np.array_equal(actual[visible],src[visible])
    group=tree.find('stack').find('stack');joint=np.array(render(group));neutral_arr=np.array(neutral);joint_visible=(joint[:,:,3]>0)|(neutral_arr[:,:,3]>0)
    assert np.array_equal(joint[:,:,3],neutral_arr[:,:,3]) and np.array_equal(joint[joint_visible],neutral_arr[joint_visible]), 'ORA assembly differs from checked visible neutral frame'
    count=len(tree.findall('.//layer'));assert count==47
report={'stage':'joint_source_front_fringe_static_check_not_runtime','horizontal_shifts':[-6,-3,0,3,6],'validation':{'source_iris_rgb_exact':True,'unrelated_source_rgb_exact':True,'exported_ora_reference_visible_rgba_exact':True,'exported_joint_assembly_visible_rgba_matches_neutral':True},'exported_ora':{'file':'MewNook-v4-front-assembly.ora','layers':count},'remaining':['Crown and outer right lock','Side/back hair and all hidden sections','Final brow review','Actual rig and actions']}
(OUT/'assembly-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['validation']))
