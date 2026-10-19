#!/usr/bin/env python3
from pathlib import Path
import json,io,zipfile,xml.etree.ElementTree as ET
import cv2,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v7';P=R/'assets/inochi/v4/hair-source-v6';src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];yy,xx=np.indices((H,W),dtype=np.float32)
with zipfile.ZipFile(P/'MewNook-v4-ribbon-joint-source.ora') as z:
 tree=ET.fromstring(z.read('stack.xml'));oldgroup=tree.find('stack').find('stack');layers={}
 for node in oldgroup:
  im=np.array(Image.open(io.BytesIO(z.read(node.get('src')))).convert('RGBA'));a=np.zeros_like(src);x,y=int(node.get('x')),int(node.get('y'));a[y:y+im.shape[0],x:x+im.shape[1]]=im;layers[node.get('name')]=a
left=np.array(Image.open(O/'left-bow-full.png').convert('RGBA'));curl=np.array(Image.open(O/'white-curl-full.png').convert('RGBA'));hidden=np.array(Image.open(O/'bow-hidden-base-full.png').convert('RGBA'));domain=np.array(Image.open(O/'bow-domain.png'))>0;core=np.array(Image.open(O/'white-curl-core.png'))>0;base=layers['hidden paint and original remainder'].copy();base[domain]=hidden[domain];right=layers['bow']
previous=np.array(Image.open(P/'joint-neutral.png').convert('RGBA'));outside=np.ones((H,W),bool);outside[195:398,325:425]=False;outside[130:340,680:830]=False;outside&=previous[:,:,3]>0
iris=[];fd=R/'assets/inochi/v4/face-source-v2';meta=json.loads((fd/'manifest.json').read_text())
for side in ('left','right'):
 p=next(p for p in meta['working_parts'] if p['file']==side+'-iris-visible.png');a=np.zeros_like(src);im=np.array(Image.open(fd/p['file']).convert('RGBA'));x,y=p['offset'];a[y:y+im.shape[0],x:x+im.shape[1]]=im;iris.append(a[:,:,3]>0)
cache={}
def bowwarp(a,shift,root,tip):
 key=(id(a),shift)
 if key in cache:return cache[key]
 gain=np.clip((yy-root)/(tip-root),0,1);mx=xx-shift*gain;al=a[:,:,3].astype(np.float32)/255;pr=a[:,:,:3].astype(np.float32)*al[:,:,None];aa=cv2.remap(al,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=cv2.remap(pr,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rr=np.divide(rr,aa[:,:,None],out=np.zeros_like(rr),where=aa[:,:,None]>1e-6);im=Image.fromarray(np.dstack([np.clip(np.round(rr),0,255).astype('uint8'),np.round(aa*255).astype('uint8')]));cache[key]=im;return im
frames={};cases=[]
for ls in (-5,-2,0,2,5):
 for rs in (-4,-2,0,2,4):
  frame=Image.fromarray(base);frame.alpha_composite(bowwarp(left,ls,210,380))
  for name,a in reversed(list(layers.items())):
   if name=='hidden paint and original remainder':continue
   frame.alpha_composite(bowwarp(a,rs,145,315) if name=='bow' else Image.fromarray(a))
  frame.alpha_composite(Image.fromarray(curl));arr=np.array(frame)
  for mask in iris:assert np.array_equal(arr[mask,:3],src[mask,:3]),'Bow changed original iris'
  assert np.array_equal(arr[core,:3],src[core,:3]),'Left bow covered foreground source curl'
  fine=layers['stationary original fine strand'];mask=(np.array(Image.open(P/'fine-strand-mask.png'))>252)&(src[:,:,:3].mean(2)>210)&(src[:,:,3]>250)&(yy>=230);assert np.array_equal(arr[mask,:3],src[mask,:3]),'Right bow covered original fine strand'
  assert np.array_equal(arr[outside],previous[outside]),'Changed unrelated prior working layers'
  cases.append([ls,rs]);
  if ls in (-5,0,5) and rs in (-4,0,4):frames[ls,rs]=frame
board=Image.new('RGB',(1050,780),(65,75,95));d=ImageDraw.Draw(board)
for row,ls in enumerate((-5,0,5)):
 for col,rs in enumerate((-4,0,4)):
  # One panel shows both original bows with the same head crop.
  tile=frames[ls,rs].crop((320,130,835,400)).resize((340,178),Image.Resampling.NEAREST);board.paste(tile,(350*col+5,260*row+25),tile);d.text((350*col+5,260*row+8),f'left {ls}; right {rs}',fill='white')
board.save(O/'both-bows-joint-motion.png');detail=Image.new('RGB',(1050,560),(65,75,95));d=ImageDraw.Draw(detail)
for i,ls in enumerate((-5,0,5)):
 tile=frames[ls,0].crop((325,195,430,395)).resize((275,524),Image.Resampling.NEAREST);detail.paste(tile,(350*i+30,25),tile);d.text((350*i+30,8),f'original left bow {ls}',fill='white')
detail.save(O/'left-bow-motion-check.png');frames[0,0].save(O/'joint-neutral.png')
# Source-material fringe checks complement the pixel invariants above.
L=left[:,:,:3].astype(int);C=curl[:,:,:3].astype(int);light_on_bow=(left[:,:,3]>128)&(L.mean(2)>180);blue_on_curl=(curl[:,:,3]>128)&(C[:,:,0]<150)&(C[:,:,2]-C[:,:,0]>20);assert not light_on_bow.any();assert not blue_on_curl.any()
entries=[('stationary original left white curl',curl)]+[(name,a) for name,a in layers.items() if name!='hidden paint and original remainder']+[('original left bow',left),('hidden paint and original remainder',base)]
tree=ET.Element('image',{'w':str(W),'h':str(H),'name':'Original both bows and front hair source review','version':'0.0.3'});root=ET.SubElement(tree,'stack');group=ET.SubElement(root,'stack',{'name':'JOINT CHECK — long side and back hair incomplete','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'})
archive=O/'MewNook-v4-both-bows-source.ora';building=archive.with_suffix('.building.ora')
with zipfile.ZipFile(building,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
 for i,(parent,name,a) in enumerate([(root,'SOURCE REFERENCE',src)]+[(group,n,a) for n,a in entries]):
  im=Image.fromarray(a);box=im.getbbox();buf=io.BytesIO();im.crop(box).save(buf,format='PNG');path=f'data/{i}.png';z.writestr(path,buf.getvalue());ET.SubElement(parent,'layer',{'name':name,'src':path,'x':str(box[0]),'y':str(box[1]),'visibility':'visible','opacity':'1','composite-op':'svg:src-over'})
 z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True));buf=io.BytesIO();Image.fromarray(src).save(buf,format='PNG');z.writestr('mergedimage.png',buf.getvalue())
with zipfile.ZipFile(building) as z:
 assert z.testzip() is None;tree=ET.fromstring(z.read('stack.xml'))
 def render(node):
  canvas=Image.new('RGBA',(W,H))
  for child in reversed(list(node)):
   if child.get('visibility')=='hidden':continue
   if child.tag=='stack':canvas.alpha_composite(render(child))
   else:canvas.alpha_composite(Image.open(io.BytesIO(z.read(child.get('src')))).convert('RGBA'),(int(child.get('x')),int(child.get('y'))))
  return canvas
 actual=np.array(render(tree.find('stack')));mask=src[:,:,3]>0;assert np.array_equal(actual[mask],src[mask]);actual=np.array(render(tree.find('stack').find('stack')));expected=np.array(frames[0,0]);mask=expected[:,:,3]>0;assert np.array_equal(actual[:,:,3],expected[:,:,3]) and np.array_equal(actual[mask],expected[mask])
building.replace(archive);report={'stage':'original_both_bows_and_static_foreground_hair_source_review','left_right_bow_parameter_cases':cases,'left_white_curl_core_rgb_exact_pixels':int(core.sum()),'iris_rgb_exact':True,'right_fine_strand_visible_core_rgb_exact':True,'unrelated_prior_working_visible_rgba_exact':True,'opaque_white_contamination_on_left_bow':int(light_on_bow.sum()),'opaque_navy_contamination_on_white_curl':int(blue_on_curl.sum()),'ora_crc_and_default_source_and_serialized_joint_validated':True,'remaining':['Long side/back hair silhouettes and hidden repaint','Final full-hair root and ear overlap','Face, upright pose and actual rig binding']};(O/'joint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('Validated',len(cases),'independent bow pairs; original left curl core',int(core.sum()))
