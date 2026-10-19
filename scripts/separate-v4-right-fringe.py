#!/usr/bin/env python3
"""Trace the original inner right fringe; keep clip and eyebrow independent."""
from pathlib import Path
import io,json,zipfile,xml.etree.ElementTree as ET
import cv2,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/inochi/v4/hair-source-v2';OUT.mkdir(exist_ok=True)
src=np.array(Image.open(ROOT/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2]
face=ROOT/'assets/inochi/v4/face-source-v4';hair=ROOT/'assets/inochi/v4/hair-source-v1'
clean=np.array(Image.open(face/'source-narrow-brow-repair.png').convert('RGBA'))
pin_under=np.array(Image.open(hair/'hairpin-hidden-hair.png').convert('RGBA'));pm=pin_under[:,:,3]>0
clean[120:195,605:680,:3][pm]=pin_under[pm,:3]

contour=[(530,98),((552,96),(584,109),(606,134)),((631,157),(646,191),(650,225)),((630,213),(604,187),(586,164)),((570,137),(550,109),(530,98))]
points=[np.array(contour[0],float)];p=points[0]
for c1,c2,end in contour[1:]:
    a,b,e=map(lambda x:np.array(x,float),(c1,c2,end))
    for t in np.linspace(0,1,100)[1:]:points.append((1-t)**3*p+3*(1-t)**2*t*a+3*(1-t)*t*t*b+t**3*e)
    p=e
# Follow the actual lavender strand outline, rather than cutting several
# pixels inside it. The path is a search guide; source pixels define the edge.
upper=np.array(points[:199]);tangent=np.gradient(upper,axis=0)
normal=np.stack([-tangent[:,1],tangent[:,0]],axis=1);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-6)
offsets=np.linspace(-7,3,81)
samples=upper[:,None,:]+normal[:,None,:]*offsets[None,:,None]
gray=clean[:,:,:3].mean(2).astype(np.float32)
values=cv2.remap(gray,samples[:,:,0].astype(np.float32),samples[:,:,1].astype(np.float32),cv2.INTER_LINEAR)
score=values+.6*offsets[None,:]**2
best=offsets[np.argmin(score,axis=1)]-.75
best=cv2.GaussianBlur(best[None,:].astype(np.float32),(0,0),3).ravel()
anchor=np.clip((upper[:,1]-103)/12,0,1)*np.clip((225-upper[:,1])/7,0,1)
upper+=normal*(best*anchor)[:,None]
points[:199]=list(upper)
mask=Image.new('L',(W*4,H*4));ImageDraw.Draw(mask).polygon([tuple(p*4) for p in points],fill=255)
mask=np.array(mask.resize((W,H),Image.Resampling.LANCZOS))/255
layer=clean.copy();layer[:,:,3]=np.round(src[:,:,3]*mask).astype(np.uint8);layer[layer[:,:,3]==0,:3]=0
im=Image.fromarray(layer);bounds=im.getbbox();im.crop(bounds).save(OUT/'front-right-inner.png')
Image.fromarray(np.round(mask*255).astype(np.uint8)).save(OUT/'front-right-inner-mask.png')
gold=(layer[:,:,0].astype(int)-layer[:,:,1].astype(int)>5)&(layer[:,:,1].astype(int)-layer[:,:,2].astype(int)>15)
pin_box=np.zeros((H,W),bool);pin_box[120:195,605:680]=True
assert not np.any((layer[:,:,3]>128)&gold&pin_box),'Original clip leaked into hair layer'
# Preserve original RGB everywhere except the already documented small brow
# and hidden-under-clip patches. No generated hairstyle is consumed.
exceptions=np.any(clean[:,:,:3]!=src[:,:,:3],axis=2)
core=(layer[:,:,3]>250)&~exceptions
assert np.array_equal(layer[core,:3],src[core,:3])
skin=clean.copy()
# Use the earlier registered exposed-forehead paint as fallback where the
# smaller forehead patch is transparent. Transparent RGB is never background.
fallback=np.array(Image.open(face/'registered-brows-completed.png').convert('RGB').resize((300,300),Image.Resampling.LANCZOS))
skin[70:370,420:720,:3]=fallback
patch=np.array(Image.open(face/'forehead-no-brows.png').convert('RGBA'));pa=patch[:,:,3:4].astype(float)/255
skin[109:311,449:659,:3]=np.round(patch[:,:,:3]*pa+skin[109:311,449:659,:3]*(1-pa)).astype(np.uint8)
coverage=cv2.dilate(mask.astype(np.float32),np.ones((5,5),np.uint8));coverage[:155]=0
base=clean.copy();base[:,:,:3]=np.round(clean[:,:,:3]*(1-coverage[:,:,None])+skin[:,:,:3]*coverage[:,:,None]).astype(np.uint8)
assert not np.any(np.all(base[:,:,:3]==0,axis=2)&(coverage>0)), 'Transparent underpaint became a black surface'
under=skin.copy();under[:,:,3]=np.round(coverage*255).astype(np.uint8);under[under[:,:,3]==0,:3]=0
u=Image.fromarray(under);ub=u.getbbox();u.crop(ub).save(OUT/'right-fringe-hidden-surface.png')
brows=Image.open(face/'brows-working-matte.png').convert('RGBA')
pin=np.zeros_like(src);pin[120:195,605:680]=np.array(Image.open(hair/'hairpin-x.png').convert('RGBA'))
yy,xx=np.indices((H,W),dtype=np.float32);weight=np.clip((yy-130)/95,0,1)
def warp(a,shift):
    alpha=a[:,:,3].astype(np.float32)/255;premul=a[:,:,:3].astype(np.float32)*alpha[:,:,None]
    ma=cv2.remap(alpha,xx-shift*weight,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    mr=cv2.remap(premul,xx-shift*weight,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    rgb=np.divide(mr,ma[:,:,None],out=np.zeros_like(mr),where=ma[:,:,None]>1e-6)
    return Image.fromarray(np.dstack([np.clip(np.round(rgb),0,255).astype(np.uint8),np.round(ma*255).astype(np.uint8)]))
frames={}
for shift in (-4,0,4):
    frame=Image.fromarray(base);frame.alpha_composite(warp(layer,shift));frame.alpha_composite(warp(pin,shift));frame.alpha_composite(brows)
    a=np.array(frame);a[:,:,3]=src[:,:,3]
    neighborhood=cv2.dilate(((layer[:,:,3]>0)|(pin[:,:,3]>0)).astype(np.uint8),np.ones((11,11),np.uint8))>0
    allowed=exceptions|(coverage>0)|neighborhood|(np.array(brows)[:,:,3]>0)
    assert np.array_equal(a[~allowed],src[~allowed]),'Changed unrelated source pixels'
    frames[str(shift)]=Image.fromarray(a);frames[str(shift)].save(OUT/('right-fringe-shift-'+str(shift)+'.png'))
board=Image.new('RGB',(1200,480),(236,237,242));d=ImageDraw.Draw(board)
for i,key in enumerate(('-4','0','4')):
    tile=frames[key].crop((525,85,690,265)).resize((360,393),Image.Resampling.NEAREST);board.paste(tile,(i*400+15,45),tile);d.text((i*400+15,15),'inner right fringe '+key+' px',fill='black')
board.save(OUT/'right-fringe-motion-check.png')
outline=src.copy();cs,_=cv2.findContours((mask>.5).astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);cv2.drawContours(outline,cs,-1,(0,160,100,255),1)
Image.fromarray(outline).crop((515,85,675,240)).resize((800,775),Image.Resampling.NEAREST).save(OUT/'right-fringe-source-contour.png')
manifest={'stage':'inner_right_fringe_working_selection','canvas':[W,H],'parts':[{'file':'front-right-inner.png','offset':list(bounds[:2])},{'file':'right-fringe-hidden-surface.png','offset':list(ub[:2])}],'contour':contour,'validation':{'unrepainted_core_source_rgb_exact_pixels':int(core.sum()),'no_gold_clip_pixels_in_hair_layer':True},'scope':'Inner forehead lock only; crown and broad outer right lock remain separate pending work. Clip is a separate original raster layer.','remaining':['Inspect traced outline and exposed surface under movement','Separate crown and outer right lock','Full side/back hair and hidden painting','Mesh binding']}
manifest['validation'].update({'transparent_underpaint_not_read_as_black':True,'unrelated_source_rgba_exact':True,'tested_horizontal_shifts':[-4,0,4]})
manifest['edge_selection']='Manual guide snapped to the original lavender line, not a generated hair silhouette.'
manifest['hidden_surface_sources']=['face-source-v4/forehead-no-brows.png where alpha is nonzero','face-source-v4/registered-brows-completed.png exposed-forehead paint for uncovered hidden pixels only']
matte=Image.new('RGB',(800,420));d=ImageDraw.Draw(matte)
for i,color in enumerate(((245,245,249),(42,48,66))):
    tile=Image.new('RGBA',(W,H),color+(255,));tile.alpha_composite(Image.fromarray(layer));tile=tile.crop((520,90,660,235)).resize((350,362),Image.Resampling.NEAREST)
    matte.paste(color,(i*400,0,(i+1)*400,420));matte.paste(tile,(i*400+20,45));d.text((i*400+20,15),'original inner fringe matte',fill='gray')
matte.save(OUT/'right-fringe-matte-check.png')
with zipfile.ZipFile(hair/'MewNook-v4-hair-source.ora') as old:
    tree=ET.fromstring(old.read('stack.xml'));tree.set('name','MewNook v4 original inner right fringe')
    group=ET.Element('stack',{'name':'HAIR WORK: inner right fringe — not complete head','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'});tree.find('stack').insert(0,group)
    with zipfile.ZipFile(OUT/'MewNook-v4-hair-source-v2.ora','w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
        for item in old.infolist():
            if item.filename not in ('mimetype','stack.xml'):z.writestr(item.filename,old.read(item.filename))
        for entry in manifest['parts']:
            name=entry['file'];path='right-fringe/'+name;z.writestr(path,(OUT/name).read_bytes());x,y=entry['offset']
            ET.SubElement(group,'layer',{'name':name[:-4],'src':path,'x':str(x),'y':str(y),'opacity':'1','visibility':'visible','composite-op':'svg:src-over'})
        z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True))
with zipfile.ZipFile(OUT/'MewNook-v4-hair-source-v2.ora') as z:
    tree=ET.fromstring(z.read('stack.xml'))
    def render(node):
        canvas=Image.new('RGBA',(W,H))
        for child in reversed(list(node)):
            if child.get('visibility','visible')=='hidden':continue
            if child.tag=='stack':canvas.alpha_composite(render(child))
            elif child.tag=='layer':canvas.alpha_composite(Image.open(io.BytesIO(z.read(child.get('src')))).convert('RGBA'),(int(child.get('x','0')),int(child.get('y','0'))))
        return canvas
    visible=src[:,:,3]>0;actual=np.array(render(tree.find('stack')))
    assert np.array_equal(src[visible],actual[visible]);count=len(tree.findall('.//layer'));assert count==41
manifest['exported_ora']={'file':'MewNook-v4-hair-source-v2.ora','layers':count,'default_visible_rgba_source_exact':True}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest['validation']))
