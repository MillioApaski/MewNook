#!/usr/bin/env python3
"""Refine original-pixel selections and isolate registered painted under-surfaces.
Does not draw replacement eye/mouth graphics or modify the runtime rig.
"""
import io,json,zipfile,hashlib,copy,xml.etree.ElementTree as ET
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
V1=ROOT/'assets/inochi/v4/face-source-v1';OUT=ROOT/'assets/inochi/v4/face-source-v2';OUT.mkdir(parents=True,exist_ok=True)
manifest1=json.loads((V1/'manifest.json').read_text())
source=np.array(Image.open(ROOT/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=source.shape[:2]
sourcef=source[:,:,:3].astype(np.float32)
def full(name):
 part=next(p for p in manifest1['parts'] if p['file']==name+'.png')
 im=np.array(Image.open(V1/part['file']).convert('RGBA'));a=np.zeros_like(source)
 x,y=part['offset'];a[y:y+im.shape[0],x:x+im.shape[1]]=im;return a

def polygon(points):
 a=np.zeros((H,W),np.uint8);cv2.fillPoly(a,[np.array(points,np.int32)],255);return a>0
regions={k:polygon(v) for k,v in manifest1['matte_contours'].items()}
registermask=(source[:,:,3]>245).astype(np.uint8)*255;registermask[80:365,430:690]=0
gray=cv2.cvtColor(source[:,:,:3],cv2.COLOR_RGB2GRAY).astype(np.float32)/255
registrations={}
def register(path,label):
 a=np.array(Image.open(path).convert('RGBA'));assert a.shape==source.shape
 warp=np.eye(2,3,dtype=np.float32)
 score,warp=cv2.findTransformECC(gray,cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY).astype(np.float32)/255,warp,
   cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,100,1e-6),registermask,5)
 registrations[label]={'correlation':float(score),'affine':warp.tolist()}
 return cv2.warpAffine(a,warp,(W,H),flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP)
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--sclera',type=Path,required=True);ap.add_argument('--forehead',type=Path,required=True);ap.add_argument('--left-iris',type=Path);ap.add_argument('--right-iris',type=Path);args=ap.parse_args()
sclera=register(args.sclera,'sclera');forehead=register(args.forehead,'forehead')
(OUT/'preview-forehead.png').unlink(missing_ok=True)
parts={};info=[]
def save(name,a,kind,notes):
 a=a.copy();a[a[:,:,3]==0,:3]=0
 im=Image.fromarray(a);box=im.getbbox();assert box,name
 im.crop(box).save(OUT/(name+'.png'));parts[name]=im
 info.append({'file':name+'.png','offset':list(box[:2]),'size':[box[2]-box[0],box[3]-box[1]],'kind':kind,'notes':notes})

def masked(pixels,m):
 a=pixels.copy();a[:,:,3]=np.where(m,a[:,:,3],0);return a
skin=sourcef.copy();a=full('skin-underpaint');m=a[:,:,3]>0;skin[m]=a[:,:,:3][m]
matte_stats={};newiris={}
for side in ('left','right'):
 # Trace the visible iris boundary on the original enlarged pixel view.
 # These contours select original pixels, including pale lower sectors.
 old=full(side+'-iris')[:,:,3]>0
 trace=([(509,271),(514,268),(521,267),(529,268),(536,270),(541,275),(543,280),(543,284),(540,289),(535,293),(529,297),(525,298),(520,296),(515,291),(511,285),(509,278)] if side=='left' else
        [(610,239),(614,235),(621,234),(629,235),(635,238),(638,242),(640,247),(641,250),(640,254),(638,258),(634,262),(629,265),(622,267),(617,266),(612,261),(609,255),(608,247)])
 iris=polygon(trace)&regions['eye-'+side]
 iris&=~(full(side+'-upper-lashes')[:,:,3]>0)
 hsv_source=cv2.cvtColor(source[:,:,:3],cv2.COLOR_RGB2HSV)
 rim=iris&~cv2.erode(iris.astype(np.uint8),np.ones((3,3),np.uint8),iterations=2).astype(bool)
 yy,xx=np.indices((H,W))
 white=(hsv_source[:,:,1]<25)&(source[:,:,:3].mean(2)>225)&(yy<(288 if side=='left' else 257))
 skin_edge=(source[:,:,0].astype(int)-source[:,:,1].astype(int)>10)&(source[:,:,:3].mean(2)>190)
 iris&=~(rim&(white|skin_edge))
 newiris[side]=iris
 save(side+'-iris-visible',masked(source,iris),'original_rgb_corrected_selection',
      'Manual source-boundary selection restores pale lower iris sectors. Upper occluded iris is still NOT invented or completed.')
 isolated=args.left_iris if side=='left' else args.right_iris
 if isolated:
  paint=Image.open(isolated).convert('RGBA');paint=paint.crop(paint.getchannel('A').point(lambda a:255 if a>32 else 0).getbbox())
  box=(508,262,546,301) if side=='left' else (606,229,645,270)
  l,t,r,b=box;paint=paint.resize((r-l,b-t),Image.Resampling.LANCZOS)
  pixels=np.zeros_like(source);pixels[t:b,l:r]=np.array(paint)
  pixels[iris]=source[iris]
  save(side+'-iris-underpaint',pixels,'original_visible_rgb_plus_painted_hidden_region',
       'Hidden arc supplied by an isolated image-edit iris, scaled to source iris bounds; original visible selection copied unchanged. Art alignment is still subject to review.')
  assert np.array_equal(pixels[iris],source[iris])
 matte_stats[side+'-iris']={'v1_pixels':int(old.sum()),'v2_pixels':int(iris.sum()),'restored_light_pixels':int((iris&~old).sum())}
 for feature in ('upper-lashes','lower-lid'):
  raw=full(side+'-'+feature);original=raw[:,:,3]>0
  blue_residue=(source[:,:,2].astype(int)-source[:,:,0].astype(int))>18
  core=original&(cv2.cvtColor(source[:,:,:3],cv2.COLOR_RGB2GRAY)<105)&~iris&~blue_residue
  if core.sum()<2:core=original&~iris&~blue_residue
  assert core.sum()>0
  # Propagate original dark-core color to the antialiased fringe, then solve
  # C = alpha*F + (1-alpha)*B, removing baked skin from edge colors.
  _,labels=cv2.distanceTransformWithLabels((~core).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
  colors=sourcef[core];F=colors[np.maximum(0,labels-1)]
  B=skin;v=F-B;delta=sourcef-B
  alpha=np.clip((delta*v).sum(2)/np.maximum(1,(v*v).sum(2)),0,1)
  domain=cv2.dilate(original.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&regions['eye-'+side]&~iris&~blue_residue
  alpha=np.where(domain&(alpha>.08),alpha,0)
  alpha[core]=1
  unmix=np.clip((sourcef-(1-alpha[:,:,None])*B)/np.maximum(alpha[:,:,None],.001),0,255)
  out=np.zeros_like(source);out[:,:,:3]=np.round(unmix).astype(np.uint8)
  out[:,:,3]=np.round(alpha*source[:,:,3]).astype(np.uint8)
  save(side+'-'+feature+'-matte',out,'derived_alpha_unmix_from_original',
       'RGB at alpha edges is unblended against painted skin estimate. Compare on dark/light backgrounds; not raw-source RGB at those edges.')
  matte_stats[side+'-'+feature]={'core_pixels':int(core.sum()),'soft_alpha_pixels':int(((out[:,:,3]>0)&(out[:,:,3]<240)).sum())}
 # Painted whites are a separately editable back surface. Preserve painted
 # upper-eyelid shadow, but do not pretend this is the original sclera.
 save(side+'-sclera-underpaint',masked(sclera,regions['eye-'+side]),'registered_image_edit',
      'Painted eye-white under-surface; includes surrounding skin/eyelid at its edge, still needs final mask refinement.')
# Restrict the new forehead/back-eye painting to a source-aligned patch.
forehead_region=polygon([(466,129),(515,109),(574,129),(622,165),(658,203),(657,239),(640,260),(602,279),(551,295),(503,310),(469,286),(450,248),(449,195)])
save('forehead-underpaint',masked(forehead,forehead_region),'registered_image_edit',
     'Hidden forehead and brow/eye completion, patch only; not yet composited beneath a finished extracted original fringe.')
# Full-body previews change ONLY the intended local areas.
for name,pixels,m in [('sclera',sclera,regions['eye-left']|regions['eye-right']),('forehead',forehead,forehead_region)]:
 a=source.copy();a[m]=pixels[m];assert np.array_equal(a[~m],source[~m]);Image.fromarray(a).save(OUT/(('preview-'+name+'.png' if name=='sclera' else 'forehead-patch-extent.png')))
# Preserve v1 reference layers unchanged, and put all v2 work in a hidden group.
with zipfile.ZipFile(V1/'MewNook-v4-face-source-v1.ora') as old:
 tree=ET.fromstring(old.read('stack.xml'));tree.set('name','MewNook v4 facial source v2');root=tree.find('stack')
 reference=ET.Element('stack',{'name':'v1 SOURCE REFERENCE','visibility':'visible','opacity':'1.0','composite-op':'svg:src-over','isolation':'isolate'})
 for element in list(root):root.remove(element);reference.append(element)
 root.append(reference)
 group=ET.Element('stack',{'name':'v2 WORKING MATERIALS — hidden by default','visibility':'hidden','opacity':'1.0','composite-op':'svg:src-over','isolation':'isolate'})
 root.insert(0,group);data=io.BytesIO()
 with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
  for entry in old.infolist():
   if entry.filename not in ('mimetype','stack.xml'):z.writestr(entry.filename,old.read(entry.filename))
  for part in reversed(info):
   name=part['file'];image=Image.open(OUT/name);buf=io.BytesIO();image.save(buf,'PNG');path='working/'+name;z.writestr(path,buf.getvalue())
   ET.SubElement(group,'layer',{'name':name[:-4],'src':path,'x':str(part['offset'][0]),'y':str(part['offset'][1]),'visibility':'visible','opacity':'1.0','composite-op':'svg:src-over'})
  z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True))
 (OUT/'MewNook-v4-face-source-v2.ora').write_bytes(data.getvalue())
# Dark/light diagnostic layouts; scale is identical within each pair.
board=Image.new('RGB',(1120,650),(234,235,239));d=ImageDraw.Draw(board)
for col,side in enumerate(('left','right')):
 for row,feature in enumerate(('iris','upper-lashes','lower-lid')):
  old=Image.fromarray(full(side+'-'+feature));new=parts[side+('-iris-visible' if feature=='iris' else '-'+feature+'-matte')]
  box=old.getbbox();nb=new.getbbox();box=(min(box[0],nb[0]),min(box[1],nb[1]),max(box[2],nb[2]),max(box[3],nb[3]))
  for i,(label,image) in enumerate([('v1',old),('v2',new)]):
   tile=Image.new('RGB',(260,175),(38,43,57));crop=image.crop(box);crop=crop.resize((crop.width*3,crop.height*3),Image.Resampling.NEAREST)
   tile.paste(crop,(10,30),crop);ImageDraw.Draw(tile).text((10,8),side+' '+feature+' '+label,fill='white')
   board.paste(tile,(col*560+i*275+5,row*210+10))
board.save(OUT/'matte-comparison.png')
# Inspect same cleaned layers on a light field as well.
light=Image.new('RGB',(1120,440),(255,255,255));dl=ImageDraw.Draw(light)
checked=[(n,im) for n,im in parts.items() if '-matte' in n or '-iris-visible' in n]
for i,(name,image) in enumerate(checked):
 box=image.getbbox();crop=image.crop(box);crop=crop.resize((crop.width*3,crop.height*3),Image.Resampling.NEAREST)
 x=(i%4)*275+10;y=(i//4)*210+10;light.paste(crop,(x,y+25),crop);dl.text((x,y),name,fill=(25,25,25))
light.save(OUT/'light-background-check.png')
# Validate actual exported ORA, including its group visibility.
def composite_stack(node,z):
 result=Image.new('RGBA',(W,H))
 for e in reversed(list(node)):
  if e.get('visibility','visible')=='hidden':continue
  if e.tag=='stack':result.alpha_composite(composite_stack(e,z))
  else:
   im=Image.open(io.BytesIO(z.read(e.get('src')))).convert('RGBA');result.alpha_composite(im,(int(e.get('x','0')),int(e.get('y','0'))))
 return result
with zipfile.ZipFile(OUT/'MewNook-v4-face-source-v2.ora') as z:
 assert z.testzip() is None
 t=ET.fromstring(z.read('stack.xml'));render=np.array(composite_stack(t.find('stack'),z));visible=source[:,:,3]>0
 assert np.array_equal(render[visible],source[visible])
manifest={'stage':'source_refinement_no_runtime_integration','source_sha256':hashlib.sha256((ROOT/'assets/inochi/v4/source/pose_reference.png').read_bytes()).hexdigest(),
 'canvas':[W,H],'working_parts':info,'registration':registrations,'matte_stats':matte_stats,
 'validation':{'reference_visible_rgba_exact':True,'reference_layer_count':16,'working_layer_count':len(info),'preview_exterior_rgba_exact':True,'iris_visible_rgba_preserved':bool(args.left_iris and args.right_iris)},
 'remaining':['Painted iris underpaint needs final eyelid/overlap acceptance; it is not automatically a finished moving eye.','Sclera and forehead are painted candidate surfaces, not final production mattes.','Original fringe/occlusion still needs precise alpha extraction.','Matte unmix uses an estimated skin background and needs visual approval.','Working group is a material collection, not an assembled replacement face or rig.']}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest['validation']));print(json.dumps(matte_stats))
