#!/usr/bin/env python3
"""Source-based outer face-frame, painted occlusion and joint static check."""
from pathlib import Path
import json,io,zipfile,xml.etree.ElementTree as ET
import cv2,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/inochi/v4/hair-source-v3';V2=ROOT/'assets/inochi/v4/hair-source-v2';FACE=ROOT/'assets/inochi/v4/face-source-v4';PIN=ROOT/'assets/inochi/v4/hair-source-v1'
src=np.array(Image.open(ROOT/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2]
def full(root,name,offset):
    a=np.zeros_like(src);im=np.array(Image.open(root/name).convert('RGBA'));x,y=offset;a[y:y+im.shape[0],x:x+im.shape[1]]=im;return a
def registered(name):
    a=src.copy();a[35:395,420:765,:3]=np.array(Image.open(OUT/('registered-'+name+'.png')).convert('RGB').resize((345,360),Image.Resampling.LANCZOS));return a
mask=np.array(Image.open(OUT/'right-face-frame-mask.png')).astype(float)/255
clean=np.array(Image.open(FACE/'source-narrow-brow-repair.png').convert('RGBA'));pu=full(PIN,'hairpin-hidden-hair.png',[605,120]);clean[pu[:,:,3]>0,:3]=pu[pu[:,:,3]>0,:3]
eye_meta=json.loads((ROOT/'assets/inochi/v4/face-source-v2/manifest.json').read_text())
ep=next(p for p in eye_meta['working_parts'] if p['file']=='right-upper-lashes-matte.png');lashes=full(ROOT/'assets/inochi/v4/face-source-v2',ep['file'],ep['offset'])
occlusion=(cv2.dilate((lashes[:,:,3]>10).astype(np.uint8),np.ones((5,5),np.uint8))>0)&(mask>.01)
repair=registered('lash-repair');material=clean.copy();material[occlusion,:3]=repair[occlusion,:3]
# The full-head repair left tiny warm face fragments. Use the separately
# painted isolated strand only at those small stain pixels, never its outline.
paint=np.array(Image.open(OUT/'registered-frame-stain-repair.png').convert('RGBA').resize((156,224),Image.Resampling.LANCZOS))
valid=(paint[:,:,3]>220)&(paint[:,:,:3].mean(2)>225)
_,near=cv2.distanceTransformWithLabels((~valid).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
white=paint[valid,:3][np.maximum(near-1,0)]
paint_full=np.zeros_like(src);paint_full[79:303,528:684,:3]=white
stain_roi=np.zeros((H,W),bool);stain_roi[218:250,648:670]=True
rgb=material[:,:,:3].astype(int)
stain=stain_roi&(mask>.01)&(((rgb[:,:,0]-rgb[:,:,2]>4)&(rgb[:,:,0]-rgb[:,:,1]>8)&(rgb.mean(2)<230))|(rgb.mean(2)<160))
stain=cv2.dilate(stain.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&stain_roi&(mask>.01)
material[stain,:3]=paint_full[stain,:3];repair[stain,:3]=paint_full[stain,:3]
occlusion|=stain
material[:,:,3]=np.round(src[:,:,3]*mask).astype(np.uint8);material[material[:,:,3]==0,:3]=0
im=Image.fromarray(material);bounds=im.getbbox();im.crop(bounds).save(OUT/'right-face-frame-working.png')
original_core=(material[:,:,3]>250)&~occlusion&~np.any(clean[:,:,:3]!=src[:,:,:3],axis=2)
assert np.array_equal(material[original_core,:3],src[original_core,:3])
coverage=cv2.dilate(mask.astype(np.float32),np.ones((5,5),np.uint8));coverage[:145]=0
under=registered('underpaint');under[:,:,3]=np.round(coverage*255).astype(np.uint8);under[under[:,:,3]==0,:3]=0
im=Image.fromarray(under);ub=im.getbbox();im.crop(ub).save(OUT/'right-face-frame-hidden-surface.png')
base=np.array(Image.open(V2/'front-assembly-base.png').convert('RGBA'));a=coverage[:,:,None];base[:,:,:3]=np.round(base[:,:,:3]*(1-a)+under[:,:,:3]*a).astype(np.uint8)
# The old eye matte assumed skin behind its edges. Here its actual background
# is white hair: rematte this corner against the newly painted hidden hair.
C=src[:,:,:3].astype(float);B=repair[:,:,:3].astype(float)
feature=occlusion&(C.mean(2)<180)
n,labels,stats,_=cv2.connectedComponentsWithStats(feature.astype(np.uint8),8)
feature=labels==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA]))
domain=(cv2.dilate(feature.astype(np.uint8),np.ones((5,5),np.uint8))>0)&occlusion
_,nearest=cv2.distanceTransformWithLabels((~feature).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
F=C[feature][np.maximum(nearest-1,0)];v=F-B;delta=C-B
alpha=np.clip((delta*v).sum(2)/np.maximum((v*v).sum(2),1),0,1)
minimum=np.maximum(np.where(delta>0,delta/np.maximum(255-B,1),0).max(2),np.where(delta<0,-delta/np.maximum(B,1),0).max(2))
alpha=np.where(domain&(alpha>.08),np.maximum(alpha,minimum),0);alpha[feature]=1
rgb=np.divide(C-(1-alpha[:,:,None])*B,alpha[:,:,None],out=np.zeros_like(C),where=alpha[:,:,None]>0)
lashes=np.dstack([np.clip(np.round(rgb),0,255).astype(np.uint8),np.round(alpha*255).astype(np.uint8)]);lashes[lashes[:,:,3]==0,:3]=0
fm=json.loads((FACE/'manifest.json').read_text());rm=json.loads((V2/'manifest.json').read_text())
lp=next(p for p in fm['parts'] if p['file']=='front-left.png');cp=next(p for p in fm['parts'] if p['file']=='front-center.png');rp=rm['parts'][0]
parts=[('face-frame',material,145,300,.6),('right-inner',full(V2,rp['file'],rp['offset']),130,225,.65),('left',full(FACE,lp['file'],lp['offset']),155,270,.75),('center',full(FACE,cp['file'],cp['offset']),155,270,1.0),('pin',full(PIN,'hairpin-x.png',[605,120]),130,225,.65)]
brows=np.array(Image.open(FACE/'brows-working-matte.png').convert('RGBA'));yy,xx=np.indices((H,W),dtype=np.float32)
def warp(a,shift,root,tip,gain):
    alpha=a[:,:,3].astype(np.float32)/255;rgb=a[:,:,:3].astype(np.float32)*alpha[:,:,None];mx=xx-shift*gain*np.clip((yy-root)/(tip-root),0,1)
    ma=cv2.remap(alpha,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);mr=cv2.remap(rgb,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    straight=np.divide(mr,ma[:,:,None],out=np.zeros_like(mr),where=ma[:,:,None]>1e-6)
    return Image.fromarray(np.dstack([np.clip(np.round(straight),0,255).astype(np.uint8),np.round(ma*255).astype(np.uint8)]))
frames={};neutral=None
for shift in (-6,-3,0,3,6):
    frame=Image.fromarray(base)
    for name,a,root,tip,gain in parts:frame.alpha_composite(warp(a,shift,root,tip,gain))
    frame.alpha_composite(Image.fromarray(lashes));frame.alpha_composite(Image.fromarray(brows));arr=np.array(frame)
    for side in ('left','right'):
        p=next(p for p in eye_meta['working_parts'] if p['file']==side+'-iris-visible.png');iris=full(ROOT/'assets/inochi/v4/face-source-v2',p['file'],p['offset'])[:,:,3]>0
        assert np.array_equal(arr[iris,:3],src[iris,:3]),'Moving hair changed original iris'
    assert np.array_equal(arr[feature,:3],src[feature,:3]),'Moving hair changed stationary eye corner core'
    outside=np.ones((H,W),bool);outside[35:395,420:765]=False;outside&=src[:,:,3]>0
    assert np.array_equal(arr[outside],src[outside]),'Changed unrelated visible source pixels'
    if shift==0:
        neutral=frame.copy();corner_core_error=int(np.abs(arr[feature,:3].astype(int)-src[feature,:3].astype(int)).max())
        assert corner_core_error==0,'Changed original eye corner core'
    arr[:,:,3]=src[:,:,3];frames[str(shift)]=Image.fromarray(arr);frames[str(shift)].save(OUT/('face-frame-shift-'+str(shift)+'.png'))
board=Image.new('RGB',(1200,480),(236,237,242));d=ImageDraw.Draw(board)
for i,key in enumerate(('-6','0','6')):
    tile=frames[key].crop((455,90,700,350)).resize((360,382),Image.Resampling.NEAREST);board.paste(tile,(i*400+15,45),tile);d.text((i*400+15,15),'four source locks, parameter '+key,fill='black')
board.save(OUT/'face-frame-joint-motion.png')
Image.fromarray(base).save(OUT/'face-frame-assembly-base.png')
Image.fromarray(lashes).save(OUT/'stationary-eye-corner.png')
report={'stage':'outer_face_frame_painted_occlusion_static_review','source_core_rgb_exact_pixels':int(original_core.sum()),'lash_occlusion_painted_pixels':int(occlusion.sum()),'tested_parameters':[-6,-3,0,3,6],'original_iris_rgb_unchanged':True,'parts':[{'file':'right-face-frame-working.png','offset':list(bounds[:2])},{'file':'right-face-frame-hidden-surface.png','offset':list(ub[:2])}],'remaining':['Review full outline and underpaint at displacement','Crown hidden roots and ear/ahoge boundary','Outer ribbon-side flick','Side and back hair','Actual model binding']}
report['stationary_eye_corner_core_rgb_exact']=True
report['unrelated_visible_source_rgba_exact']=True
report['isolated_hair_paint_used_only_for_stain_pixels']=int(stain.sum())
report['remaining']=['Crown hidden roots and ear/ahoge boundary','Outer ribbon-side flick','Side and back hair','Actual model binding']
matte=Image.new('RGB',(800,560));d=ImageDraw.Draw(matte)
for i,color in enumerate(((245,245,249),(42,48,66))):
    tile=Image.new('RGBA',(W,H),color+(255,));tile.alpha_composite(Image.fromarray(material));tile=tile.crop((520,75,690,310)).resize((340,470),Image.Resampling.NEAREST)
    matte.paste(color,(i*400,0,(i+1)*400,560));matte.paste(tile,(i*400+20,45));d.text((i*400+20,15),'original face-frame plus hidden paint',fill='gray')
matte.save(OUT/'face-frame-matte-check.png')
# Keep a self-contained editable assembly plus separately labelled candidates.
archive=OUT/'MewNook-v4-hair-source-v3.ora';building=OUT/'MewNook-v4-hair-source-v3.building.ora'
with zipfile.ZipFile(V2/'MewNook-v4-front-assembly.ora') as old:
    tree=ET.fromstring(old.read('stack.xml'));tree.set('name','MewNook v4 outer face-frame source review')
    root=tree.find('stack')
    joint=ET.Element('stack',{'name':'FOUR LOCK ASSEMBLY CHECK — crown not separated','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'});root.insert(0,joint)
    work=ET.Element('stack',{'name':'OUTER FACE-FRAME WORKING PARTS','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'});root.insert(1,work)
    crown=ET.Element('stack',{'name':'CROWN TRACE CANDIDATE — incomplete ear and ahoge boundary','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'});root.insert(2,crown)
    trace=json.loads((OUT/'manifest.json').read_text());cap=next(p for p in trace['parts'] if p['file']=='crown-visible.png');cap_full=full(OUT,cap['file'],cap['offset'])
    entries=[(joint,'brows',brows),(joint,'stationary-eye-corner',lashes)]+[(joint,name,a) for name,a,*_ in reversed(parts)]+[(joint,'underpaint-base',base),(work,'right-face-frame',material),(work,'hidden-surface',under),(crown,'visible-source-candidate',cap_full)]
    with zipfile.ZipFile(building,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
        for item in old.infolist():
            if item.filename not in ('mimetype','stack.xml'):z.writestr(item.filename,old.read(item.filename))
        for i,(group,name,a) in enumerate(entries):
            im=Image.fromarray(a);box=im.getbbox();im=im.crop(box);buf=io.BytesIO();im.save(buf,format='PNG');path='outer-frame/'+str(i)+'-'+name+'.png';z.writestr(path,buf.getvalue())
            ET.SubElement(group,'layer',{'name':name,'src':path,'x':str(box[0]),'y':str(box[1]),'opacity':'1','visibility':'visible','composite-op':'svg:src-over'})
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
    actual=np.array(render(tree.find('stack')));vis=src[:,:,3]>0;assert np.array_equal(actual[vis],src[vis])
    joint=tree.find('stack').find('stack');actual=np.array(render(joint));expected=np.array(neutral);vis=(actual[:,:,3]>0)|(expected[:,:,3]>0)
    assert np.array_equal(actual[:,:,3],expected[:,:,3]) and np.array_equal(actual[vis],expected[vis])
    assert z.testzip() is None
    count=len(tree.findall('.//layer'));assert count==58
building.replace(archive)
report['exported_ora']={'file':archive.name,'layers':count,'default_source_visible_rgba_exact':True,'joint_assembly_visible_rgba_matches_checked_neutral':True}
(OUT/'face-frame-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
