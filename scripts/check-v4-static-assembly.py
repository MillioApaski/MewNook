#!/usr/bin/env python3
"""Static source-material assembly proofs; not runtime/model acceptance."""
from pathlib import Path
import io,json,zipfile,xml.etree.ElementTree as ET,copy
import numpy as np,cv2
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];V1=ROOT/'assets/inochi/v4/face-source-v1';V2=ROOT/'assets/inochi/v4/face-source-v2';OUT=ROOT/'assets/inochi/v4/face-source-v3';OUT.mkdir(parents=True,exist_ok=True)
src=np.array(Image.open(ROOT/'assets/inochi/v4/source/pose_reference.png').convert('RGBA'));H,W=src.shape[:2]
m1=json.loads((V1/'manifest.json').read_text());m2=json.loads((V2/'manifest.json').read_text())
def load_full(name,version=2):
 root=V2 if version==2 else V1;items=m2['working_parts'] if version==2 else m1['parts'];meta=next(p for p in items if p['file']==name+'.png')
 im=np.array(Image.open(root/meta['file']).convert('RGBA'));a=np.zeros_like(src);x,y=meta['offset'];a[y:y+im.shape[0],x:x+im.shape[1]]=im;return a

def polygon(points):
 a=np.zeros((H,W),np.uint8);cv2.fillPoly(a,[np.array(points,np.int32)],255);return a>0
regions={k:polygon(p) for k,p in m1['matte_contours'].items()}
parts={};meta=[]
def save(name,a,kind,notes):
 a=a.copy();a[a[:,:,3]==0,:3]=0;im=Image.fromarray(a);box=im.getbbox();assert box,name
 im.crop(box).save(OUT/(name+'.png'));parts[name]=im
 meta.append({'file':name+'.png','offset':list(box[:2]),'size':[box[2]-box[0],box[3]-box[1]],'kind':kind,'notes':notes})

def masked(a,m):
 a=a.copy();a[:,:,3]=np.where(m,a[:,:,3],0);return a
# Use already registered hidden-forehead painting. Limit extraction to strands
# crossing the face, NOT the whole crown or side hair.
bgpatch=load_full('forehead-underpaint');B=src[:,:,:3].astype(np.float32);bm=bgpatch[:,:,3]>0;B[bm]=bgpatch[:,:,:3][bm]
C=src[:,:,:3].astype(np.float32)
roi=polygon([(470,139),(511,126),(551,143),(598,174),(633,210),(624,240),(590,264),(553,279),(522,281),(493,273),(469,278),(455,249),(455,199)])
roi&=~(regions['eye-left']|regions['eye-right'])
chroma=C[:,:,2]-C[:,:,0];bgskin=B[:,:,0]-B[:,:,2]
delta=np.linalg.norm(C-B,axis=2)
hairseed=roi&(chroma>-16)&(delta>8)&((bgskin>12)|(C.mean(2)-B.mean(2)>12))
# Reject isolated edit noise; preserve actual thin source strands connected to
# the primary fringe, instead of turning every color difference into a layer.
n,labels,stats,_=cv2.connectedComponentsWithStats(hairseed.astype(np.uint8),8)
seed=np.zeros((H,W),np.uint8)
for i in range(1,n):
 if stats[i,cv2.CC_STAT_AREA]>14:seed[labels==i]=1
core=cv2.erode(seed,np.ones((3,3),np.uint8)).astype(bool)
domain=cv2.dilate(seed,np.ones((3,3),np.uint8),iterations=1).astype(bool)&roi
assert core.sum()>200
_,indices=cv2.distanceTransformWithLabels((~core).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
F=C[core][np.maximum(indices-1,0)]
v=F-B;alpha=np.clip(((C-B)*v).sum(2)/np.maximum((v*v).sum(2),1),0,1)
# Conservative edge colors come from the nearest confident SOURCE hair core.
# Exact inverse-color unmix amplified tiny edit differences into colored dots
# under motion. Keep source RGB in cores and reject low-confidence edge alpha.
alpha=np.where(domain&(alpha>.15),alpha,0);alpha[core]=1
F[core]=C[core]
fg=np.zeros_like(src);fg[:,:,:3]=np.round(F).astype(np.uint8);fg[:,:,3]=np.round(alpha*255).astype(np.uint8)
save('fringe-over-face-matte',fg,'source_core_rgb_with_derived_edge_alpha',
 'Forehead-crossing source strands only. Crown, clip, side hair and eye-overlap pixels are excluded; not a complete front-hair layer.')
# Background is only replaced where the selected fringe currently lies.
domain=fg[:,:,3]>0;background=src.copy();background[domain,:3]=np.round(B[domain]).astype(np.uint8)
save('fringe-hidden-skin-patch',masked(background,domain),'registered_image_edit_under_source_strands',
 'Only the hidden skin field needed for this selected fringe fragment.')
source_fringe=masked(src,domain);source_remainder=masked(src,~domain)
save('fringe-original-selection',source_fringe,'unmodified_source_pixels','Reference partition, not antialiased working matte.')
save('fringe-original-remainder',source_remainder,'unmodified_source_pixels','Reference complement: together reconstruct original source exactly.')
rebuild=Image.new('RGBA',(W,H));rebuild.alpha_composite(Image.fromarray(source_remainder));rebuild.alpha_composite(Image.fromarray(source_fringe))
visible=src[:,:,3]>0;assert np.array_equal(np.array(rebuild)[visible],src[visible])
# Independently derive eye apertures from the painted sclera, not a geometric
# ellipse. These alpha gates clip moving iris pixels beneath the eyelids.
eyes={};metrics={}
for side in ('left','right'):
 white=load_full(side+'-sclera-underpaint');rgb=white[:,:,:3].astype(np.int16);hsv=cv2.cvtColor(white[:,:,:3],cv2.COLOR_RGB2HSV)
 candidate=regions['eye-'+side]&(rgb[:,:,2]-rgb[:,:,0]>-12)&(rgb[:,:,0]-rgb[:,:,1]<20)&(hsv[:,:,1]<70)&(rgb.mean(2)>145)
 n,l,st,_=cv2.connectedComponentsWithStats(candidate.astype(np.uint8),8)
 assert n>1
 selected=(l==(1+np.argmax(st[1:,cv2.CC_STAT_AREA]))).astype(np.uint8)
 # Fill interior gaps but do not expand across source lash boundaries.
 cs,_=cv2.findContours(selected,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(selected,cs,-1,1,-1)
 aperture=selected.astype(bool)&regions['eye-'+side]
 gate=np.zeros_like(src);gate[:,:,:3]=255;gate[:,:,3]=aperture*255
 save(side+'-aperture-mask',gate,'painted_sclera_segmentation_mask','Binary inspection gate; final antialias/eyelid matte remains to be polished.')
 eyes[side]={'white':white,'iris':load_full(side+'-iris-underpaint'),'aperture':aperture}
 metrics[side]={'aperture_pixels':int(aperture.sum())}
# Assembly uses source eyelids over painted whites and original-visible iris.
frames={}
for shift in (-2,0,2):
 frame=src.copy()
 for side,e in eyes.items():
  m=e['aperture'];frame[m]=e['white'][m]
  moved=np.array(Image.fromarray(e['iris']).transform((W,H),Image.Transform.AFFINE,(1,0,-shift,0,1,0),resample=Image.Resampling.NEAREST))
  moved[:,:,3]=np.where(m,moved[:,:,3],0)
  assert not np.any(moved[~m,3]),'iris leaked outside eye opening'
  base=Image.fromarray(frame);base.alpha_composite(Image.fromarray(moved));frame=np.array(base)
  # Reference upper/lower source fragments keep eyelid corners stationary.
  # Use clean mattes; deliberately do NOT move a flattened original eye patch.
  for feature in ('upper-lashes','lower-lid'):
   base=Image.fromarray(frame);base.alpha_composite(Image.fromarray(load_full(side+'-'+feature+'-matte')));frame=np.array(base)
 eye_region=regions['eye-left']|regions['eye-right']
 assert np.array_equal(frame[~eye_region],src[~eye_region]),'eye assembly changed unrelated source region'
 name='gaze-'+str(shift);Image.fromarray(frame).save(OUT/(name+'.png'));frames[name]=Image.fromarray(frame)
# Fringe follows a conservative warp anchored at the top; it is a diagnostic,
# not permission for larger motion in a model.
yy,xx=np.indices((H,W),dtype=np.float32);weight=np.clip((yy-157)/110,0,1)
fringe_frames={};neutral_mae=None
for shift in (-2,0,2):
 moved=cv2.remap(fg,xx-shift*weight,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
 base=Image.fromarray(background);base.alpha_composite(Image.fromarray(moved));a=np.array(base)
 # Inspect colors with original canvas opacity; do not claim unchanged alpha
 # for an assembled generative working surface.
 a[:,:,3]=src[:,:,3]
 if shift==0:neutral_mae=float(np.abs(a[domain,:3].astype(float)-src[domain,:3].astype(float)).mean())
 name='fringe-'+str(shift);Image.fromarray(a).save(OUT/(name+'.png'));fringe_frames[name]=Image.fromarray(a)
# View crop boards at identical scale. No face features are drawn by the layout.
def board_for(images,path,crop):
 board=Image.new('RGB',(1200,400),(235,236,241));d=ImageDraw.Draw(board)
 for i,(name,im) in enumerate(images.items()):
  tile=im.crop(crop);tile.thumbnail((380,330));tile=tile.resize((380,round(tile.height*380/tile.width)),Image.Resampling.NEAREST)
  board.paste(tile,(i*400+10,45),tile);d.text((i*400+12,15),name,fill=(20,20,30))
 board.save(OUT/path)
board_for(frames,'gaze-contact-sheet.png',(460,195,680,350))
board_for(fringe_frames,'fringe-contact-sheet.png',(445,120,680,330))
# Add hidden diagnostic layers to the real editable ORA; reference remains exact.
with zipfile.ZipFile(V2/'MewNook-v4-face-source-v2.ora') as old:
 tree=ET.fromstring(old.read('stack.xml'));tree.set('name','MewNook v4 source v3 static assembly');root=tree.find('stack')
 group=ET.Element('stack',{'name':'v3 STATIC ASSEMBLY MATERIALS','visibility':'hidden','opacity':'1.0','composite-op':'svg:src-over','isolation':'isolate'});root.insert(0,group)
 data=io.BytesIO()
 with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
  for item in old.infolist():
   if item.filename not in ('mimetype','stack.xml'):z.writestr(item.filename,old.read(item.filename))
  for entry in reversed(meta):
   name=entry['file'];p='assembly/'+name;z.writestr(p,(OUT/name).read_bytes())
   ET.SubElement(group,'layer',{'name':name[:-4],'src':p,'x':str(entry['offset'][0]),'y':str(entry['offset'][1]),'visibility':'visible','opacity':'1','composite-op':'svg:src-over'})
  z.writestr('stack.xml',ET.tostring(tree,encoding='utf-8',xml_declaration=True))
 (OUT/'MewNook-v4-face-source-v3.ora').write_bytes(data.getvalue())
# Validate the actual exported archive, including nested group visibility.
with zipfile.ZipFile(OUT/'MewNook-v4-face-source-v3.ora') as z:
 exported=ET.fromstring(z.read('stack.xml'))
 def render(node):
  canvas=Image.new('RGBA',(W,H))
  for child in reversed(list(node)):
   if child.get('visibility','visible')=='hidden':continue
   if child.tag=='stack':canvas.alpha_composite(render(child))
   elif child.tag=='layer':
    im=Image.open(io.BytesIO(z.read(child.get('src')))).convert('RGBA')
    canvas.alpha_composite(im,(int(child.get('x','0')),int(child.get('y','0'))))
  return canvas
 actual=np.array(render(exported.find('stack')))
 assert np.array_equal(actual[visible],src[visible]),'Exported ORA default changed source'
 layer_count=len(exported.findall('.//layer'));assert layer_count==33
manifest={'stage':'static_assembly_diagnostics_not_approved_rig','canvas':[W,H],'layer_count':layer_count,'working_parts':meta,'eye_metrics':metrics,
 'validation':{'source_fringe_partition_exact':True,'gaze_iris_spill_outside_aperture':0,'gaze_exterior_rgba_exact':True,'fringe_neutral_rgb_mean_abs_error':neutral_mae},
 'exported_ora_default_visible_rgba_exact':True,
 'fringe_motion_artistic_status':'NOT PASSED: discontinuous outline / residual source at brow and strand intersections',
 'gaze_status':'Three static horizontal positions only; clipping verified, artistic acceptance pending',
 'fringe_scope':'Forehead-crossing strands only, not the entire front-hair/crown/clip layer.',
 'remaining':['Artistic assessment of static gaze frames','Final eye aperture alpha and iris edge cleanup','Hair strand extraction at brow/eye intersections','Complete front/side/back hair split and hidden paint','Actual mesh and motion curves','Full-character source separation']}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest['validation']));print('Selected fringe pixels:',int(domain.sum()))
