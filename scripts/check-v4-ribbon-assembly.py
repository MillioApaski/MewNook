#!/usr/bin/env python3
"""Original right bow, white flick and fine foreground strand joint review."""
from pathlib import Path
import json,io,zipfile,xml.etree.ElementTree as ET
import cv2,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v6';V5=R/'assets/inochi/v4/hair-source-v5';src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];yy,xx=np.indices((H,W),dtype=np.float32)
def load(name):return np.array(Image.open(O/name).convert('RGBA'))
curves=[(741,214),((754,234),(775,276),(783,305)),((789,326),(783,341),(776,348)),((773,348),(771,345),(771,343)),((782,337),(784,324),(779,306)),((772,280),(750,240),(738,220)),((739,218),(740,215),(741,214))]
points=[np.array(curves[0],float)];p=points[0]
for c1,c2,end in curves[1:]:
 a,b,e=map(lambda z:np.array(z,float),(c1,c2,end))
 for t in np.linspace(0,1,100)[1:]:points.append((1-t)**3*p+3*(1-t)**2*t*a+3*(1-t)*t*t*b+t**3*e)
 p=e
m=Image.new('L',(W*4,H*4));ImageDraw.Draw(m).polygon([tuple(p*4) for p in points],fill=255);m=m.resize((W,H),Image.Resampling.LANCZOS);mask=np.array(m).astype(float)/255;m.save(O/'fine-strand-mask.png')
C=src[:,:,:3].astype(float);core=(mask>.99)&(C.mean(2)>210)&(src[:,:,3]>250);navy=(load('right-bow-full.png')[:,:,3]>250)&(C[:,:,0]<110)
_,labels=cv2.distanceTransformWithLabels((~navy).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);B=C[navy][np.maximum(labels-1,0)]
_,labels=cv2.distanceTransformWithLabels((~core).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);F=C[core][np.maximum(labels-1,0)];v=F-B;delta=C-B;alpha=np.clip((delta*v).sum(2)/np.maximum((v*v).sum(2),1),0,1)*mask
alpha[core]=1;rgb=F.copy();rgb[core]=C[core]
exterior=(src[:,:,3]<250)&(mask>0);alpha[exterior]=src[exterior,3]/255*mask[exterior];rgb[exterior]=C[exterior]
fine=np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.round(alpha*255).astype('uint8')]);fine[fine[:,:,3]==0,:3]=0;assert np.array_equal(fine[core,:3],src[core,:3]);Image.fromarray(fine).save(O/'fine-strand-full.png')
im=Image.fromarray(fine);bounds=im.getbbox();im.crop(bounds).save(O/'fine-strand-working.png')
# Load the actual serialized prior working group rather than a flattened screenshot.
with zipfile.ZipFile(V5/'MewNook-v4-head-joint-source.ora') as z:
 tree=ET.fromstring(z.read('stack.xml'));group=tree.find('stack').find('stack');layers={}
 for node in group:
  a=np.zeros_like(src);im=np.array(Image.open(io.BytesIO(z.read(node.get('src')))).convert('RGBA'));x,y=int(node.get('x')),int(node.get('y'));a[y:y+im.shape[0],x:x+im.shape[1]]=im;layers[node.get('name')]=a
base=layers['hidden paint and original remainder'].copy();hidden=load('bow-hidden-base.png');domain=np.array(Image.open(O/'bow-domain.png'))>0;fm=np.array(Image.open(O/'ribbon-flick-mask.png'))>0;coverage=domain|fm;base[coverage]=hidden[coverage]
bow=load('right-bow-full.png');flick=load('ribbon-flick-full.png')
fc=flick[:,:,:3].astype(int);bc=bow[:,:,:3].astype(int)
navy_on_flick=(flick[:,:,3]>128)&(fc[:,:,0]<150)&(fc[:,:,2]-fc[:,:,0]>20)
white_on_bow=(bow[:,:,3]>128)&(bc.mean(2)>180)
assert not navy_on_flick.any(),'Blue cloth was carried into the white hair material'
assert not white_on_bow.any(),'White hair was carried into the blue cloth material'
brows=layers['stationary brows'];corner=layers['stationary eye corner']
# Draw source fine hair above the moving bow; white flick is independently above it.
parts=[('bow',bow,145,315,1),('source crown cap',layers['source crown cap'],105,50,.5),('face-frame',layers['face-frame'],145,300,.6),('right-inner',layers['right-inner'],130,225,.65),('left',layers['left'],155,270,.75),('center',layers['center'],155,270,1),('pin',layers['pin'],130,225,.65),('original ahoge',layers['original ahoge'],99,9,1)]
cache={}
def warp(a,shift,gain,vertical=False):
 key=(id(a),shift,vertical)
 if key in cache:return cache[key]
 al=a[:,:,3].astype(np.float32)/255;rgb=a[:,:,:3].astype(np.float32)*al[:,:,None];mx=xx if vertical else xx-shift*gain;my=yy-shift*gain if vertical else yy
 aa=cv2.remap(al,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=cv2.remap(rgb,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=np.divide(rr,aa[:,:,None],out=np.zeros_like(rr),where=aa[:,:,None]>1e-6);im=Image.fromarray(np.dstack([np.clip(np.round(rr),0,255).astype('uint8'),np.round(aa*255).astype('uint8')]));cache[key]=im;return im
iris=[];fd=R/'assets/inochi/v4/face-source-v2';meta=json.loads((fd/'manifest.json').read_text())
for side in ('left','right'):
 p=next(p for p in meta['working_parts'] if p['file']==side+'-iris-visible.png');a=np.zeros_like(src);im=np.array(Image.open(fd/p['file']).convert('RGBA'));x,y=p['offset'];a[y:y+im.shape[0],x:x+im.shape[1]]=im;iris.append(a[:,:,3]>0)
frames={};cases=[]
for head in (-6,0,6):
 for bs in (-4,0,4):
  for fs in (-4,0,4):
   frame=Image.fromarray(base)
   for name,a,root,tip,gain in parts:
    shift=bs if name=='bow' else head
    frame.alpha_composite(warp(a,shift,gain*np.clip((yy-root)/(tip-root),0,1)))
   frame.alpha_composite(Image.fromarray(fine));frame.alpha_composite(warp(flick,fs,np.clip((xx-695)/48,0,1)**1.5,True));frame.alpha_composite(Image.fromarray(corner));frame.alpha_composite(Image.fromarray(brows));arr=np.array(frame)
   for mask in iris:assert np.array_equal(arr[mask,:3],src[mask,:3])
   mask=corner[:,:,3]>250;assert np.array_equal(arr[mask,:3],src[mask,:3]);assert np.array_equal(arr[core&(yy>=230),:3],src[core&(yy>=230),:3]),'Moving bow covered original fine strand'
   outside=np.ones((H,W),bool);outside[:395,400:830]=False;outside&=src[:,:,3]>0;assert np.array_equal(arr[outside],src[outside])
   cases.append([head,bs,fs]);
   if head==0:frames[bs,fs]=frame
board=Image.new('RGB',(1200,1050),(65,75,95));d=ImageDraw.Draw(board)
for row,bs in enumerate((-4,0,4)):
 for col,fs in enumerate((-4,0,4)):
  tile=frames[bs,fs].crop((678,175,825,300)).resize((390,332),Image.Resampling.NEAREST);board.paste(tile,(col*400+5,row*350+18),tile);d.text((col*400+5,row*350+4),f'bow {bs}; flick {fs}',fill='white')
board.save(O/'bow-flick-joint-motion.png');frames[0,0].save(O/'joint-neutral.png')
matte=Image.new('RGB',(700,500))
for i,color in enumerate(((245,245,249),(35,43,63))):
 tile=Image.new('RGBA',(W,H),color+(255,));tile.alpha_composite(Image.fromarray(fine));tile=tile.crop((732,210,795,352)).resize((200,450),Image.Resampling.NEAREST);matte.paste(color,(350*i,0,350*i+350,500));matte.paste(tile,(350*i+75,25))
matte.save(O/'fine-strand-matte-check.png')
# Export a self-contained current working group, retaining exact original reference by default.
tree=ET.Element('image',{'w':str(W),'h':str(H),'name':'MewNook original hair and right bow review','version':'0.0.3'});root=ET.SubElement(tree,'stack');group=ET.SubElement(root,'stack',{'name':'JOINT CHECK — long side and back hair incomplete','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'})
entries=[(root,'SOURCE REFERENCE',src),(group,'stationary brows',brows),(group,'stationary eye corner',corner),(group,'white source flick',flick),(group,'stationary original fine strand',fine)]+[(group,name,a) for name,a,*_ in reversed(parts)]+[(group,'hidden paint and original remainder',base)]
archive=O/'MewNook-v4-ribbon-joint-source.ora';building=archive.with_suffix('.building.ora')
with zipfile.ZipFile(building,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
 for i,(parent,name,a) in enumerate(entries):
  im=Image.fromarray(a);b=im.getbbox();buf=io.BytesIO();im.crop(b).save(buf,format='PNG');path=f'data/{i}.png';z.writestr(path,buf.getvalue());ET.SubElement(parent,'layer',{'name':name,'src':path,'x':str(b[0]),'y':str(b[1]),'visibility':'visible','opacity':'1','composite-op':'svg:src-over'})
 z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True));buf=io.BytesIO();Image.fromarray(src).save(buf,format='PNG');z.writestr('mergedimage.png',buf.getvalue())
with zipfile.ZipFile(building) as z:
 assert z.testzip() is None
 tree=ET.fromstring(z.read('stack.xml'))
 def render(node):
  canvas=Image.new('RGBA',(W,H))
  for child in reversed(list(node)):
   if child.get('visibility')=='hidden':continue
   if child.tag=='stack':canvas.alpha_composite(render(child))
   else:canvas.alpha_composite(Image.open(io.BytesIO(z.read(child.get('src')))).convert('RGBA'),(int(child.get('x')),int(child.get('y'))))
  return canvas
 actual=np.array(render(tree.find('stack')));vis=src[:,:,3]>0;assert np.array_equal(actual[vis],src[vis]);actual=np.array(render(tree.find('stack').find('stack')));expected=np.array(frames[0,0]);vis=expected[:,:,3]>0;assert np.array_equal(actual[:,:,3],expected[:,:,3]) and np.array_equal(actual[vis],expected[vis])
building.replace(archive);report={'stage':'original_right_bow_flick_and_fine_strand_joint_static_review','head_bow_flick_cases':cases,'original_iris_and_eye_corner_core_rgb_exact':True,'original_fine_strand_core_rgb_exact_pixels':int(core.sum()),'protected_visible_fine_strand_core_pixels':int((core&(yy>=230)).sum()),'fine_strand_root_may_be_occluded_by_moving_flick':True,'unrelated_visible_source_rgba_exact':True,'flick_opaque_navy_contamination_pixels':int(navy_on_flick.sum()),'bow_opaque_white_contamination_pixels':int(white_on_bow.sum()),'editable_source_validated':archive.name,'fine_strand_offset':list(bounds[:2]),'remaining':['Final side/back hair silhouettes and repaint','Left bow decomposition','Full hair occlusion review','Upright pose, face work and actual rig binding']};(O/'joint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('Validated',len(cases),'joint parameter triples; stationary white core pixels',int(core.sum()))

meta=json.loads((O/'manifest.json').read_text());meta['stage']='source_materials_joint_static_review_not_complete_hair';meta['working_parts']=[{'file':name,'offset':list(Image.open(O/full).getbbox()[:2])} for name,full in [('ribbon-flick-working.png','ribbon-flick-full.png'),('right-bow-working.png','right-bow-full.png'),('fine-strand-working.png','fine-strand-full.png')]];(O/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
