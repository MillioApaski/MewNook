from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parents[1];o=r/'assets/inochi/v4/hair-source-v4';o.mkdir(exist_ok=True)
s=Image.open(r/'assets/inochi/v4/source/pose_reference.png').convert('RGBA');w,h=s.size
# Selection follows the original loop's lower edge and its stem, not a replacement strand.
p=[(420,0),(550,0),(550,49),(539,51),(539,67),(535,83),(528,96),(530,83),(530,70),(527,59),(523,52),(520,53),(505,57),(485,66),(466,77),(452,87),(442,91),(427,88),(420,80)]
m=Image.new('L',(w*4,h*4));ImageDraw.Draw(m).polygon([(x*4,y*4) for x,y in p],fill=255);m=m.resize((w,h),Image.Resampling.LANCZOS);m.save(o/'ahoge-selection-mask.png')
a=np.array(s);a[:,:,3]=np.round(a[:,:,3].astype(float)*np.array(m)/255).astype('uint8');a[a[:,:,3]==0,:3]=0
im=Image.fromarray(a);b=im.getbbox();im.crop(b).save(o/'ahoge-source-candidate.png')
board=Image.new('RGBA',s.size,(70,80,100,255));board.alpha_composite(im);board.crop((410,0,570,115)).resize((960,690)).save(o/'ahoge-source-matte-check.png')
print(b)
import cv2,json,io,zipfile,xml.etree.ElementTree as ET
source=np.array(s);mask=np.array(m).astype(float)/255
ref=np.array(Image.open(o/'inputs/crown-ahoge-source.png').convert('RGBA'))
paint=np.array(Image.open(o/'inputs/crown-underpaint-generated.png').convert('RGBA').resize((1100,800),Image.Resampling.LANCZOS))
sift=cv2.SIFT_create(contrastThreshold=.01);gate=np.zeros(ref.shape[:2],np.uint8);gate[510:]=255;gate[300:,950:]=255
k1,d1=sift.detectAndCompute(cv2.cvtColor(ref[:,:,:3],cv2.COLOR_RGB2GRAY),gate)
k2,d2=sift.detectAndCompute(cv2.cvtColor(paint[:,:,:3],cv2.COLOR_RGB2GRAY),None)
pairs=cv2.BFMatcher().knnMatch(d1,d2,k=2);good=[a for a,b in pairs if a.distance<.8*b.distance]
target=np.float32([k1[g.queryIdx].pt for g in good]);origin=np.float32([k2[g.trainIdx].pt for g in good])
M,inliers=cv2.estimateAffinePartial2D(origin,target,method=cv2.RANSAC,ransacReprojThreshold=2)
assert M is not None and inliers.sum()>=12,'Registration not reliable'
assert .98<M[0,0]<1.02 and abs(M[0,1])<.02 and np.ptp(target[inliers.ravel()>0,0])>700,'Insufficient spatial support'
err=np.linalg.norm(cv2.transform(origin[:,None],M)[:,0]-target,axis=1)[inliers.ravel()>0]/5
pa=paint[:,:,3].astype(np.float32)/255
wa=cv2.warpAffine(pa,M,(1100,800));wr=cv2.warpAffine(paint[:,:,:3].astype(np.float32)*pa[:,:,None],M,(1100,800))
wr=np.divide(wr,wa[:,:,None],out=np.zeros_like(wr),where=wa[:,:,None]>1e-6)
registered=np.dstack([np.clip(np.round(wr),0,255).astype('uint8'),np.round(wa*255).astype('uint8')]);Image.fromarray(registered).save(o/'registered-crown-underpaint.png')
small=np.array(Image.fromarray(registered).resize((220,160),Image.Resampling.LANCZOS));patch=source.copy();patch[0:160,400:620]=small
# Clear original loop plus a narrow rim; consume generated art only in this local footprint.
footprint=(mask>.01)&(source[:,:,3]>0)
clear=cv2.dilate(footprint.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)
# Feather the crown-root repair into unchanged original paint to avoid a rectangular seam.
root_mask=np.zeros((h,w),np.uint8);root_mask[45:103,510:551]=255
root_weight=cv2.GaussianBlur(root_mask.astype(np.float32)/255,(0,0),3)
weight=np.maximum(clear.astype(np.float32),root_weight);clear=weight>1e-5
sa=source[:,:,3].astype(float)/255;pa=patch[:,:,3].astype(float)/255
ba=sa*(1-weight)+pa*weight
br=source[:,:,:3]*sa[:,:,None]*(1-weight[:,:,None])+patch[:,:,:3]*pa[:,:,None]*weight[:,:,None]
br=np.divide(br,ba[:,:,None],out=np.zeros_like(br),where=ba[:,:,None]>1e-6)
base=np.dstack([np.clip(np.round(br),0,255).astype('uint8'),np.round(ba*255).astype('uint8')])
base[~clear]=source[~clear]
# Crown to the right of the strand was already visible; keep its original edge.
keep=np.indices((h,w))[1]>=540
keep &= np.indices((h,w))[0]<60
base[keep]=source[keep]
# Avoid consuming the generated new crown silhouette at the free loop: crown starts below its original lower boundary.
# It is meaningful to retain newly exposed crown where it lies behind the source stem.
Image.fromarray(base).save(o/'crown-without-ahoge.png')
part=Image.fromarray(a);part.save(o/'ahoge-full.png');yy,xx=np.indices((h,w),dtype=np.float32)
frames={}
for shift in (-6,-3,0,3,6):
    # Root remains anchored; increasing bend toward the top. Premultiplied interpolation.
    gain=np.clip((99-yy)/90,0,1);mx=xx-shift*gain
    al=a[:,:,3].astype(np.float32)/255;rgb=a[:,:,:3].astype(np.float32)*al[:,:,None]
    aa=cv2.remap(al,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=cv2.remap(rgb,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    rr=np.divide(rr,aa[:,:,None],out=np.zeros_like(rr),where=aa[:,:,None]>1e-6)
    moving=Image.fromarray(np.dstack([np.clip(np.round(rr),0,255).astype('uint8'),np.round(aa*255).astype('uint8')]))
    frame=Image.fromarray(base);frame.alpha_composite(moving);arr=np.array(frame)
    outside=~clear & (a[:,:,3]==0);outside[:110,410:560]=False
    visible=outside&(source[:,:,3]>0);assert np.array_equal(arr[visible],source[visible])
    frame.save(o/('ahoge-shift-'+str(shift)+'.png'));frames[shift]=frame
board=Image.new('RGB',(1200,420),(72,80,100));draw=ImageDraw.Draw(board)
for i,key in enumerate((-6,0,6)):
    tile=frames[key].crop((410,0,570,155)).resize((384,372),Image.Resampling.NEAREST);board.paste(tile,(400*i+8,35),tile);draw.text((400*i+8,12),'source ahoge bend '+str(key),fill='white')
board.save(o/'ahoge-motion-check.png')
report={'stage':'source_ahoge_and_crown_root_static_candidate','registration':{'inliers':int(inliers.sum()),'matches':len(good),'median_native_error':float(np.median(err)),'p95_native_error':float(np.percentile(err,95)),'matrix':M.tolist()},'source_part_offset':list(b[:2]),'tested_parameters':[-6,-3,0,3,6],'unrelated_visible_source_rgba_exact':True,'remaining':['Inspect exposed crown contour and neutral seam','Full crown and ear boundary','Joint assembly with four front locks','Side and back hair','Actual rig binding']}
(o/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
core=(a[:,:,3]>250)&(np.array(m)>250)
assert np.array_equal(a[core,:3],source[core,:3])
report['original_ahoge_core_rgb_exact_pixels']=int(core.sum())
report['remaining'][0]='Final crown outline review with full crown separation'
report['root_seam_fix']='Preserve originally visible crown edge to right of stem; feather hidden root paint in premultiplied alpha'
(o/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
# Small independent editable review. Reference remains default; working group is hidden.
archive=o/'MewNook-v4-ahoge-source.ora';building=archive.with_suffix('.building.ora')
tree=ET.Element('image',{'w':str(w),'h':str(h),'name':'MewNook v4 original ahoge and crown-root review','version':'0.0.3'});stack=ET.SubElement(tree,'stack')
def layer(parent,name,path,visibility='visible'):
    return ET.SubElement(parent,'layer',{'name':name,'src':path,'x':'0','y':'0','opacity':'1','visibility':visibility,'composite-op':'svg:src-over'})
layer(stack,'SOURCE REFERENCE — original default','data/source.png')
group=ET.SubElement(stack,'stack',{'name':'AHOGE STATIC CHECK — full crown incomplete','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'})
layer(group,'Original source ahoge','data/ahoge.png');layer(group,'Crown root hidden paint and original remainder','data/base.png')
def png(im):
    buf=io.BytesIO();im.save(buf,format='PNG');return buf.getvalue()
with zipfile.ZipFile(building,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED);z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True))
    z.writestr('data/source.png',png(s));z.writestr('data/ahoge.png',png(part));z.writestr('data/base.png',png(Image.fromarray(base)));z.writestr('mergedimage.png',png(s));z.writestr('Thumbnails/thumbnail.png',png(s.copy().resize((205,256))))
with zipfile.ZipFile(building) as z:
    assert z.testzip() is None
    assert np.array_equal(np.array(Image.open(io.BytesIO(z.read('data/source.png')))),source)
    actual=Image.open(io.BytesIO(z.read('data/base.png'))).convert('RGBA');actual.alpha_composite(Image.open(io.BytesIO(z.read('data/ahoge.png'))).convert('RGBA'))
    expected=np.array(frames[0]);got=np.array(actual);visible=expected[:,:,3]>0
    assert np.array_equal(expected[:,:,3],got[:,:,3]) and np.array_equal(expected[visible],got[visible])
building.replace(archive)
print('Editable source validated:',archive.name,'original core pixels',int(core.sum()))
