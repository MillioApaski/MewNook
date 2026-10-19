#!/usr/bin/env python3
"""Independent original ahoge and four-lock source assembly; no runtime edits."""
from pathlib import Path
import json,io,zipfile,xml.etree.ElementTree as ET
import numpy as np,cv2
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'assets/inochi/v4/hair-source-v5';F=R/'assets/inochi/v4/face-source-v4';V2=R/'assets/inochi/v4/hair-source-v2';V3=R/'assets/inochi/v4/hair-source-v3';A=R/'assets/inochi/v4/hair-source-v4';P=R/'assets/inochi/v4/hair-source-v1'
src=np.array(Image.open(R/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2];yy,xx=np.indices((H,W),dtype=np.float32)
def load(d,f,offset=None):
 im=np.array(Image.open(d/f).convert('RGBA'))
 if offset is None:return im
 canvas=np.zeros_like(src);x,y=offset;canvas[y:y+im.shape[0],x:x+im.shape[1]]=im;return canvas
def part(d,manifest,name,key):
 p=next(p for p in json.loads((d/manifest).read_text())[key] if p['file']==name);return load(d,name,p['offset'])
parts=[('face-frame',load(V3,'right-face-frame-working.png',[528,79]),145,300,.6),('right-inner',part(V2,'manifest.json','front-right-inner.png','parts'),130,225,.65),('left',part(F,'manifest.json','front-left.png','parts'),155,270,.75),('center',part(F,'manifest.json','front-center.png','parts'),155,270,1),('pin',load(P,'hairpin-x.png',[605,120]),130,225,.65)]
base=load(V3,'face-frame-assembly-base.png');top=load(A,'crown-without-ahoge.png');base[:110]=top[:110]
coverage=np.array(Image.open(O/'crown-mask.png'))>0
cb=load(O,'crown-hidden-base.png');base[coverage]=cb[coverage]
crown=load(O,'crown-full.png')
ahoge=load(A,'ahoge-full.png');brows=load(F,'brows-working-matte.png');corner=load(V3,'stationary-eye-corner.png')
warp_cache={}
def warp(a,shift,gain):
 key=(id(a),shift)
 if key in warp_cache:return warp_cache[key]
 alpha=a[:,:,3].astype(np.float32)/255;rgb=a[:,:,:3].astype(np.float32)*alpha[:,:,None];mx=xx-shift*gain
 ma=cv2.remap(alpha,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);mr=cv2.remap(rgb,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
 straight=np.divide(mr,ma[:,:,None],out=np.zeros_like(mr),where=ma[:,:,None]>1e-6)
 result=Image.fromarray(np.dstack([np.clip(np.round(straight),0,255).astype('uint8'),np.round(ma*255).astype('uint8')]))
 warp_cache[key]=result;return result
iris=[]
for side in ('left','right'):iris.append(part(R/'assets/inochi/v4/face-source-v2','manifest.json',side+'-iris-visible.png','working_parts')[:,:,3]>0)
frames={};capframes={};cases=[]
for hair in (-6,-3,0,3,6):
 for ah in (-6,-3,0,3,6):
  for capshift in (-3,0,3):
   frame=Image.fromarray(base)
   frame.alpha_composite(warp(crown,capshift,np.clip((105-yy)/55,0,1)))
   for name,a,root,tip,gain in parts:frame.alpha_composite(warp(a,hair,gain*np.clip((yy-root)/(tip-root),0,1)))
   frame.alpha_composite(warp(ahoge,ah,np.clip((99-yy)/90,0,1)))
   frame.alpha_composite(Image.fromarray(corner));frame.alpha_composite(Image.fromarray(brows));arr=np.array(frame)
   for mask in iris:assert np.array_equal(arr[mask,:3],src[mask,:3]),'Original iris altered'
   mask=corner[:,:,3]>250;assert np.array_equal(arr[mask,:3],src[mask,:3]),'Stationary eye core altered'
   outside=np.ones((H,W),bool);outside[:395,400:765]=False;outside&=src[:,:,3]>0;assert np.array_equal(arr[outside],src[outside]),'Unrelated original changed'
   cases.append([hair,ah,capshift]);
   if capshift==0 and hair in (-6,0,6) and ah in (-6,0,6):frames[hair,ah]=frame
   if hair==0 and ah==0:capframes[capshift]=frame
board=Image.new('RGB',(1200,1260),(65,75,95));d=ImageDraw.Draw(board)
for row,hair in enumerate((-6,0,6)):
 for col,ah in enumerate((-6,0,6)):
  tile=frames[hair,ah].crop((415,0,710,320)).resize((360,390),Image.Resampling.NEAREST);board.paste(tile,(col*400+20,row*420+25),tile);d.text((col*400+20,row*420+8),f'front {hair}; ahoge {ah}',fill='white')
board.save(O/'ahoge-front-joint-motion.png');frames[0,0].save(O/'joint-neutral.png')
Image.fromarray(base).save(O/'joint-base.png')
capboard=Image.new('RGB',(1200,460),(65,75,95));d=ImageDraw.Draw(capboard)
for i,key in enumerate((-3,0,3)):
 tile=capframes[key].crop((420,25,675,300)).resize((390,420),Image.Resampling.NEAREST);capboard.paste(tile,(i*400+5,25),tile);d.text((i*400+5,8),f'crown {key}; front 0; ahoge 0',fill='white')
capboard.save(O/'crown-joint-motion.png')
report={'stage':'static_original_crown_ahoge_plus_four_front_locks','independent_parameter_cases':cases,'original_iris_rgb_exact':True,'stationary_eye_core_rgb_exact':True,'unrelated_visible_rgba_exact':True,'crown_cap_separated':True,'full_hair_completed':False,'runtime_binding':False,'remaining':['Final crown and ear review with full side hair','Ribbon-adjacent flick','Side and back hair','Body pose','Actual rig and expression binding']}
# Minimal editable current assembly; source reference is the default visible layer.
tree=ET.Element('image',{'w':str(W),'h':str(H),'name':'Original ahoge and front locks joint review','version':'0.0.3'});root=ET.SubElement(tree,'stack');group=ET.SubElement(root,'stack',{'name':'JOINT CHECK — side and back hair incomplete','visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'})
entries=[(root,'SOURCE REFERENCE',src),(group,'stationary brows',brows),(group,'stationary eye corner',corner),(group,'original ahoge',ahoge)]+[(group,name,a) for name,a,*_ in reversed(parts)]+[(group,'source crown cap',crown),(group,'hidden paint and original remainder',base)]
archive=O/'MewNook-v4-head-joint-source.ora';building=archive.with_suffix('.building.ora')
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
 actual=np.array(render(tree.find('stack')));mask=src[:,:,3]>0;assert np.array_equal(actual[mask],src[mask])
 actual=np.array(render(tree.find('stack').find('stack')));expected=np.array(frames[0,0]);mask=expected[:,:,3]>0;assert np.array_equal(actual[:,:,3],expected[:,:,3]) and np.array_equal(actual[mask],expected[mask])
building.replace(archive);report['serialized_ora_default_and_joint_validated']=True;(O/'joint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('Checked',len(cases),'independent parameter triples and editable source')
