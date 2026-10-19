#!/usr/bin/env python3
"""Source-pixel fringe selections and narrow, registered eyebrow repairs.

Paths select existing artwork; they never render substitute hair shapes.
"""
from pathlib import Path
import io,json,zipfile,xml.etree.ElementTree as ET,cv2,numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/inochi/v4/face-source-v4'
SRC=ROOT/'assets/inochi/v4/source/pose_reference.png'
src=np.array(Image.open(SRC).convert('RGBA'));H,W=src.shape[:2]
original=src[:,:,:3].astype(np.float32)
registered=np.array(Image.open(OUT/'registered-no-brows.png').convert('RGB').resize((300,300),Image.Resampling.LANCZOS))
repair=original.copy();repair[70:370,420:720]=registered

def path_mask(segments):
    points=[];p=np.array(segments[0],float)
    points.append(p.copy())
    for c1,c2,end in segments[1:]:
        a,b,e=map(lambda v:np.array(v,float),(c1,c2,end))
        for t in np.linspace(0,1,80)[1:]:
            points.append((1-t)**3*p+3*(1-t)**2*t*a+3*(1-t)*t*t*b+t**3*e)
        p=e
    scale=4;im=Image.new('L',(W*scale,H*scale));d=ImageDraw.Draw(im)
    d.polygon([tuple(q*scale) for q in points],fill=255)
    return np.array(im.resize((W,H),Image.Resampling.LANCZOS))/255.

warp_errors=[]
def warp_rgba(layer,map_x,map_y):
    # Interpolate premultiplied colors, then return straight-alpha PNG pixels.
    # Interpolating straight RGB pulls black from transparent padding into hair
    # edges and alpha-compositing multiplies that darkened edge a second time.
    a=layer[:,:,3].astype(np.float32)/255
    premul=layer[:,:,:3].astype(np.float32)*a[:,:,None]
    moved_a=cv2.remap(a,map_x,map_y,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    moved_rgb=cv2.remap(premul,map_x,map_y,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    rgb=np.divide(moved_rgb,moved_a[:,:,None],out=np.zeros_like(moved_rgb),where=moved_a[:,:,None]>1e-6)
    result=np.dstack([np.clip(np.round(rgb),0,255).astype(np.uint8),np.round(moved_a*255).astype(np.uint8)])
    result[result[:,:,3]==0,:3]=0
    reconstructed=result[:,:,:3].astype(np.float32)*(result[:,:,3:4]/255)
    error=float(np.abs(reconstructed-moved_rgb).max())
    assert error<=1.01,'Warp changed premultiplied color beyond PNG rounding'
    warp_errors.append(error)
    return result

# Observer-left front lock and crossing central locks, hand traced from source.
contours={
 'front-left':[(520,98),((488,100),(469,144),(467,194)),((464,235),(471,265),(484,283)),((490,271),(494,250),(493,225)),((491,205),(494,185),(497,160)),((499,130),(507,110),(520,98))],
 'front-center':[(530,98),((509,99),(494,132),(496,182)),((499,216),(518,245),(544,262)),((555,269),(566,271),(575,267)),((566,264),(557,258),(550,252)),((564,260),(578,266),(590,263)),((580,260),(571,254),(565,249)),((578,253),(588,253),(596,248)),((590,248),(586,245),(583,242)),((592,220),(592,192),(585,170)),((575,142),(550,110),(530,98))],
}

# Repair only the narrow source eyebrow bands, with a feather under one pixel.
brows={
 'left':[(474,259),((489,239),(513,228),(533,228))],
 'right':[(584,214),((599,198),(628,194),(647,204))],
}
brow_band=np.zeros((H,W),np.uint8)
for name,path in brows.items():
    p=np.array(path[0],float);c1,c2,e=map(lambda v:np.array(v,float),path[1]);ts=np.linspace(0,1,150)
    pts=np.array([(1-t)**3*p+3*(1-t)**2*t*c1+3*(1-t)*t*t*c2+t**3*e for t in ts])
    cv2.polylines(brow_band,[np.round(pts*4).astype(np.int32)],False,255,5,cv2.LINE_AA,shift=2)
band=cv2.GaussianBlur(brow_band.astype(float)/255,(0,0),.45)
clean=np.round(original*(1-band[:,:,None])+repair*band[:,:,None]).astype(np.uint8)
assert np.array_equal(clean[band==0],src[band==0,:3])
Image.fromarray(np.dstack([clean,src[:,:,3]])).save(OUT/'source-narrow-brow-repair.png')

# Derive separate stationary brow mattes from ORIGINAL vs eyebrow-free surface.
# The alpha/RGB decomposition is estimated; it is not unmodified source RGBA.
brow_delta=original-clean.astype(float)
strength=np.maximum(-brow_delta.mean(2),0)
delta_ok=(strength>1.5)&(brow_band>0)
brow_core=delta_ok&(strength>10)
_,idx=cv2.distanceTransformWithLabels((~brow_core).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
F=original[brow_core][np.maximum(idx-1,0)]
v=F-clean
a=np.clip((brow_delta*v).sum(2)/np.maximum((v*v).sum(2),1),0,1)*delta_ok
brow=np.dstack([np.round(F).astype(np.uint8),np.round(a*255).astype(np.uint8)])
brow[brow[:,:,3]==0,:3]=0
Image.fromarray(brow).save(OUT/'brows-stationary-matte.png')
# Complete hidden brow intersections from the isolated painted eyebrow asset.
# Align the two actual raster strokes by their source reference bounding boxes.
# Do not draw replacement lines or consume the generated face as a whole.
asset=np.array(Image.open(OUT/'inputs/eyebrows-isolated-generated.png').convert('RGBA'))
ch=asset[:,:,:3].astype(np.int16)
body=(asset[:,:,3]>16)&(ch[:,:,2]>ch[:,:,0])&(ch[:,:,0]<225)
n,labels,stats,_=cv2.connectedComponentsWithStats(body.astype(np.uint8),8)
ids=sorted(range(1,n),key=lambda i:stats[i,cv2.CC_STAT_AREA],reverse=True)[:2]
assert len(ids)==2
ids.sort(key=lambda i:stats[i,cv2.CC_STAT_LEFT])
complete=np.zeros_like(src);completion_meta=[]
for ident,box in zip(ids,[(474,227,535,261),(583,196,648,216)]):
    x,y,w,h,area=stats[ident];selected=asset[y:y+h,x:x+w].copy()
    selected[:,:,3]=np.where(labels[y:y+h,x:x+w]==ident,selected[:,:,3],0)
    target=Image.fromarray(selected).resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
    tile=np.array(target)
    reference=brow[box[1]:box[3],box[0]:box[2]]
    trusted=(reference[:,:,3]>160)&(reference[:,:,2]>reference[:,:,0])
    painted_core=tile[:,:,3]>160
    assert trusted.sum()>5 and painted_core.sum()>10
    # Match the pale, already blended gray of the actual reference strokes.
    # The isolated paint was too blue/dark to place over the original bangs.
    delta=np.median(reference[trusted,:3],axis=0)-np.median(tile[painted_core,:3],axis=0)
    tile[:,:,:3]=np.clip(tile[:,:,:3].astype(float)+delta,0,255).astype(np.uint8)
    complete[box[1]:box[3],box[0]:box[2]]=tile
    completion_meta.append({'generated_box':[int(x),int(y),int(x+w),int(y+h)],'source_box':list(box)})
complete[complete[:,:,3]==0,:3]=0
Image.fromarray(complete).save(OUT/'brows-completion-matte.png')
brow_original=brow.copy();brow=complete.copy()
gray_core=(brow_original[:,:,0].astype(int)-brow_original[:,:,1].astype(int)<22)&(brow_original[:,:,2]>brow_original[:,:,0])
original_core=(brow_original[:,:,3]>100)&(complete[:,:,3]>180)&gray_core
brow[original_core]=brow_original[original_core];brow[brow[:,:,3]==0,:3]=0
Image.fromarray(brow).save(OUT/'brows-working-matte.png')

meta=[];union=np.zeros((H,W),float)
for name,contour in contours.items():
    mask=path_mask(contour)
    # The lower pink triangle at (548,275) is skin/cast shadow, not another
    # white hair tip. It must not become an opaque part of the hair layer.
    union=np.maximum(union,mask)
    layer=np.dstack([clean,np.round(mask*src[:,:,3]).astype(np.uint8)])
    layer[layer[:,:,3]==0,:3]=0
    im=Image.fromarray(layer);box=im.getbbox();im.crop(box).save(OUT/(name+'.png'))
    meta.append({'file':name+'.png','offset':list(box[:2]),'selection':'hand-traced source silhouette','repair':'only registered narrow eyebrow bands; original RGB elsewhere'})

Image.fromarray(np.round(union*255).astype(np.uint8)).save(OUT/'fringe-selection-mask.png')
# Make the skin underlayer eyebrow-free as well. Only the two eyebrow boxes
# consume the registered skin edit; all remaining prior underpainting is kept.
skin=np.array(Image.open(ROOT/'assets/inochi/v4/face-source-v2/forehead-underpaint.png').convert('RGBA'))
paint=np.array(Image.open(OUT/'registered-forehead-no-brows.png').convert('RGB').resize((210,202),Image.Resampling.LANCZOS))
skin_gate=np.zeros((H,W),np.uint8)
cv2.rectangle(skin_gate,(469,215),(538,258),255,-1)
cv2.rectangle(skin_gate,(575,188),(653,222),255,-1)
skin_gate=cv2.GaussianBlur(skin_gate.astype(float)/255,(0,0),1.2)[109:311,449:659]
skin[:,:,:3]=np.round(skin[:,:,:3]*(1-skin_gate[:,:,None])+paint*skin_gate[:,:,None]).astype(np.uint8)
Image.fromarray(skin).save(OUT/'forehead-no-brows.png')
fullskin=src.copy();fullskin[109:311,449:659]=skin
coverage=cv2.dilate(union.astype(np.float32),np.ones((5,5),np.uint8));coverage[:155]=0
base=clean.astype(float)*(1-coverage[:,:,None])+fullskin[:,:,:3]*coverage[:,:,None]
base=np.dstack([np.round(base).astype(np.uint8),src[:,:,3]])
Image.fromarray(base).save(OUT/'assembly-base.png')
yy,xx=np.indices((H,W),dtype=np.float32)
weight=np.clip((yy-155)/115,0,1)
frames={};neutral_error=None
for shift in (-6,-2,0,2,6):
    canvas=Image.fromarray(base)
    for part in meta:
        layer=np.zeros_like(src);im=np.array(Image.open(OUT/part['file']).convert('RGBA'));x,y=part['offset'];layer[y:y+im.shape[0],x:x+im.shape[1]]=im
        moved=warp_rgba(layer,xx-shift*weight,yy)
        canvas.alpha_composite(Image.fromarray(moved))
    canvas.alpha_composite(Image.fromarray(brow))
    arr=np.array(canvas);arr[:,:,3]=src[:,:,3]
    canvas=Image.fromarray(arr);canvas.save(OUT/('fringe-shift-'+str(shift)+'.png'));frames[str(shift)]=canvas
    if shift==0:neutral_error=float(np.abs(arr[:,:,:3].astype(float)-original)[union>.01].mean())
board=Image.new('RGB',(1200,420),(236,237,242));d=ImageDraw.Draw(board)
for i,key in enumerate(('-2','0','2')):
    im=frames[key]
    tile=im.crop((455,160,650,295)).resize((390,270),Image.Resampling.NEAREST)
    board.paste(tile,(i*400+5,50),tile);d.text((i*400+8,20),'fringe shift '+key+' px; stationary brows',fill='black')
board.save(OUT/'fringe-motion-check.png')
stress=Image.new('RGB',(1200,420),(236,237,242));d=ImageDraw.Draw(stress)
for i,key in enumerate(('-6','0','6')):
    tile=frames[key].crop((455,160,650,295)).resize((390,270),Image.Resampling.NEAREST)
    stress.paste(tile,(i*400+5,50),tile);d.text((i*400+8,20),'stress fringe shift '+key+' px',fill='black')
stress.save(OUT/'fringe-motion-stress.png')
compare=Image.new('RGB',(800,420),(236,237,242));d=ImageDraw.Draw(compare)
for i,(label,im) in enumerate([('original',Image.fromarray(src)),('working neutral',frames['0'])]):
    tile=im.crop((455,160,650,295)).resize((390,270),Image.Resampling.NEAREST);compare.paste(tile,(i*400+5,50),tile);d.text((i*400+8,20),label,fill='black')
compare.save(OUT/'neutral-vs-source.png')
report={'stage':'existing_fringe_edge_defects_repaired_not_a_finished_rig','canvas':[W,H],'parts':meta,'source_rgb_outside_brow_band_exact':True,'brow_band_pixels':int((band>0).sum()),'contours':contours,'remaining':['Complete remaining front hair and crown selections','Final brow positioning, thickness and opacity review in task 5','Actual head motion and mesh binding','Full front/side/back hair separation remains pending']}
report['neutral_fringe_rgb_mean_abs_error']=neutral_error
report['brow_completion_registration']=completion_meta
report['brow_original_core_pixels_retained']=int(original_core.sum())
report['warp_validation']={'method':'premultiplied RGB interpolation, straight alpha export','tested_shifts':[-6,-2,0,2,6],'max_premultiplied_rgb_rounding_error':max(warp_errors),'skin_shadow_triangle_removed_from_hair':True}
# Preserve an editable checkpoint with every new working part hidden by
# default. Verify the archive itself rather than a pre-export in-memory image.
with zipfile.ZipFile(ROOT/'assets/inochi/v4/face-source-v3/MewNook-v4-face-source-v3.ora') as old:
    tree=ET.fromstring(old.read('stack.xml'));tree.set('name','MewNook v4 forehead fringe repair')
    group=ET.Element('stack',{'name':'v4 WORKING PARTS — inspect separately; not accepted','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'})
    tree.find('stack').insert(0,group)
    entries=meta+[{'file':'brows-working-matte.png','offset':[0,0]},{'file':'forehead-no-brows.png','offset':[449,109]}]
    with zipfile.ZipFile(OUT/'MewNook-v4-fringe-repair.ora','w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
        for item in old.infolist():
            if item.filename not in ('mimetype','stack.xml'):z.writestr(item.filename,old.read(item.filename))
        for entry in entries:
            name=entry['file'];path='fringe-repair/'+name;z.writestr(path,(OUT/name).read_bytes())
            ET.SubElement(group,'layer',{'name':name[:-4],'src':path,'x':str(entry['offset'][0]),'y':str(entry['offset'][1]),'opacity':'1','visibility':'visible','composite-op':'svg:src-over'})
        z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True))
with zipfile.ZipFile(OUT/'MewNook-v4-fringe-repair.ora') as z:
    exported=ET.fromstring(z.read('stack.xml'))
    def render(node):
        canvas=Image.new('RGBA',(W,H))
        for child in reversed(list(node)):
            if child.get('visibility','visible')=='hidden':continue
            if child.tag=='stack':canvas.alpha_composite(render(child))
            elif child.tag=='layer':canvas.alpha_composite(Image.open(io.BytesIO(z.read(child.get('src')))).convert('RGBA'),(int(child.get('x','0')),int(child.get('y','0'))))
        return canvas
    actual=np.array(render(exported.find('stack')));visible=src[:,:,3]>0
    assert np.array_equal(src[visible],actual[visible]),'Export changed original reference'
    layer_count=len(exported.findall('.//layer'));assert layer_count==37
report['exported_ora']={'file':'MewNook-v4-fringe-repair.ora','layers':layer_count,'default_visible_rgba_source_exact':True}
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('source_rgb_outside_brow_band_exact','brow_band_pixels')}))
