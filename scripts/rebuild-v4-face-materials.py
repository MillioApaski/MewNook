#!/usr/bin/env python3
"""Author fixed skin + independent eye/hair materials; never bake skin into blink frames."""
from pathlib import Path
import json,hashlib,sys,io,zipfile,xml.etree.ElementTree as ET
import numpy as np,cv2
from PIL import Image,ImageDraw
from v4_source_io import png_bytes
R=Path(__file__).resolve().parents[1];V=R/'assets/inochi/v4';O=V/'face-layer-rebuild-v1';O.mkdir(exist_ok=True)
S=np.array(Image.open(V/'source/pose_reference.png').convert('RGBA'));H,W=S.shape[:2];box=(440,180,704,356);cw,ch=264,176;shape=S.shape
Y,X=np.indices((H,W),dtype=np.float32)
scene=json.loads((V/'scene-source-v1/manifest.json').read_text());old=V/'face-source-v10';m=json.loads((old/'manifest.json').read_text())
def load(p):return np.array(Image.open(p).convert('RGBA'))
def placed(tile,x=440,y=180):
 a=np.zeros_like(S);a[y:y+tile.shape[0],x:x+tile.shape[1]]=tile;return a
def crop(a):return Image.fromarray(a).crop(box)
def over(layers):
 im=Image.new('RGBA',(W,H))
 for n,a in reversed(layers):im.alpha_composite(Image.fromarray(a))
 return np.array(im)
def save(n,a):
 Image.fromarray(a).save(O/(n+'.png'));return {'file':n+'.png','offset':[0,0],'size':[W,H],'sha256':hashlib.sha256((O/(n+'.png')).read_bytes()).hexdigest()}
def maskfile(p):return np.array(Image.open(p))>0
hair=[]
for e in scene['parts']:
 if e['role']!='front-hair':continue
 tile=load(V/'scene-source-v1'/e['file']);a=placed(tile,*e['offset']);hair.append((e['name'],a))
# Native hair is exported unchanged, with all antialiasing. Keep its authored ordering.
hairfull=over(hair);hairalpha=hairfull[:,:,3]/255
# Pure skin-only painted plate. Widen the underlap beneath hair; never copy
# RGB from the original eye/hair footprint into this layer.
base=placed(np.array(Image.open(O/'inputs/skin-only-painted.png').convert('RGBA').resize((286,ch),Image.Resampling.LANCZOS)),429,180)
clip=np.zeros((H,W),bool);clip[180:356,440:704]=True
base[~clip]=0;hairfull[~clip]=0
materials=[('hair-foreground',hairfull)];eyes={}
for side in ('left','right'):
 opening=maskfile(V/'face-source-v5'/(side+'-opening-mask.png'))
 aperture=maskfile(V/'face-source-v5'/(side+'-aperture-mask.png'))
 sup=load(V/'face-source-v5'/(side+'-eye-support-full.png'));sclera=sup.copy();sclera[~aperture]=0
 iris=load(V/'face-source-v5'/(side+'-iris-full.png'))
 upper=load(old/(side+'-upper-lid-full.png'));lower=load(old/(side+'-lower-lid-full.png'));closed=load(old/(side+'-closed-lash-full.png'))
 # Transparent painted lid skin is a separate material, sampled from the SAME fixed plate.
 region=maskfile(V/'face-source-v5'/(side+'-eye-region-mask.png'))
 lids=base.copy();lids[~region]=0
 ys,xs=np.nonzero(opening);split=float(ys.mean())
 upper_skin=lids.copy();upper_skin[Y>split]=0
 lower_skin=lids.copy();lower_skin[Y<=split]=0
 materials.extend([(side+'-upper-lid-skin',upper_skin),(side+'-lower-lid-skin',lower_skin)])
 eyes[side]={'opening':opening,'aperture':aperture,'sclera':sclera,'iris':iris,'upper':upper,'lower':lower,'closed':closed,'skin':lids}
 for label,a in [('sclera',sclera),('iris',iris),('upper-lash',upper),('lower-lash',lower),('closed-lash',closed),('lid-skin',lids)]:materials.append((side+'-'+label,a))
materials.append(('face-skin-fixed',base))
for index,(name,a) in enumerate(hair):
 a=a.copy();a[~clip]=0
 if a[:,:,3].any():materials.append(('hair-part-'+str(index),a))
# Independent brows are retained from native source, without touching fixed skin.
sys.path.insert(0,str(R/'scripts'));from v4_source_io import load_group
native=load_group(V/'face-source-v5/MewNook-v4-eye-source.ora',shape)
brows=next(a for n,a in native if n=='stationary brows').copy();brows[~clip]=0
materials.insert(1,('brows',brows))
def warp(a,mx,my):
 f=a.astype(np.float32);alpha=f[:,:,3]/255;aa=cv2.remap(alpha,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rgb=cv2.remap(f[:,:,:3]*alpha[:,:,None],mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);rgb=np.divide(rgb,aa[:,:,None],out=np.zeros_like(rgb),where=aa[:,:,None]>1e-6);return np.dstack([np.clip(np.round(rgb),0,255).astype('uint8'),np.clip(np.round(aa*255),0,255).astype('uint8')])
def profile(mask,kind):
 xs=np.flatnonzero(mask.any(0));ys=[np.flatnonzero(mask[:,x]) for x in xs];return np.interp(np.arange(W),xs,[np.min(a) if kind=='top' else np.max(a) if kind=='bottom' else np.mean(a) for a in ys]).astype('float32')
def pose(t):
 layers=[('hair',hairfull),('brows',brows)]
 for side,e in eyes.items():
  top=profile(e['opening'],'top');bottom=profile(e['opening'],'bottom');curve=profile(e['closed'][:,:,3]>128,'mean')
  ap=(Y>=((1-t)*top+t*curve)[None,:])&(Y<=((1-t)*bottom+t*curve)[None,:])&e['aperture'] if t<1 else np.zeros((H,W),bool)
  iris=e['iris'].copy();iris[~ap]=0;sclera=e['sclera'].copy();sclera[~ap]=0
  if t==1:up=e['closed'].copy();lo=np.zeros_like(S)
  else:up=warp(e['upper'],X,Y-t*(curve-top)[None,:]);lo=warp(e['lower'],X,Y-t*(curve-bottom)[None,:]);lo[:,:,3]=np.round(lo[:,:,3]*(1-t)).astype('uint8')
  lid=e['skin'].copy();lid[ap]=0
  layers.extend([(side+' upper lash',up),(side+' lower lash',lo),(side+' eyelid skin',lid),(side+' iris',iris),(side+' sclera',sclera)])
 layers.append(('fixed skin',base));return layers
metadata={'canvas':[W,H],'review_crop':list(box),'stage':'materials only; production rig unchanged','skin_policy':'one immutable painted base across all poses; no skin baked in eye textures','generated_inputs':['inputs/eyeless-painted.png','inputs/skin-only-painted.png'],'materials':{n:save(n,a) for n,a in materials}}
# Save reference assemblies, never use these flattened PNGs as runtime eye slots.
frames=[]
for t in (0,.5,1):
 layers=pose(t);a=over(layers);name='assembly-'+str(round(t*100));save(name,a);frames.append(a)
# Real layered OpenRaster: visible source layers, separate materials hidden for edit.
root=ET.Element('image',{'w':str(W),'h':str(H),'version':'0.0.3','name':'Fixed skin and independent eye materials'})
stack=ET.SubElement(root,'stack');payload=io.BytesIO()
with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
 for groupname,visibility,layers in [('Open assembly','visible',pose(0)),('All source materials','hidden',materials)]:
  g=ET.SubElement(stack,'stack',{'name':groupname,'visibility':visibility,'opacity':'1','composite-op':'svg:src-over','isolation':'isolate'})
  for i,(n,a) in enumerate(layers):
   im=Image.fromarray(a);bb=im.getbbox()
   if not bb:continue
   f=f'data/{groupname.replace(" ","-")}-{i}.png';z.writestr(f,png_bytes(im.crop(bb)));ET.SubElement(g,'layer',{'name':n,'src':f,'x':str(bb[0]),'y':str(bb[1]),'opacity':'1','visibility':'visible','composite-op':'svg:src-over'})
 z.writestr('stack.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True));z.writestr('mergedimage.png',png_bytes(Image.fromarray(frames[0])))
(O/'MewNook-face-materials.ora').write_bytes(payload.getvalue())
board=Image.new('RGB',(1584,1140),(235,236,242));d=ImageDraw.Draw(board)
for i,(label,a) in enumerate([('FIXED SKIN / no eyes, brows or hair',base),('INDEPENDENT EYES / open',frames[0]),('INDEPENDENT EYES / half',frames[1]),('INDEPENDENT EYES / closed',frames[2])]):
 im=crop(a);bg=Image.new('RGBA',im.size,(235,236,242,255));bg.alpha_composite(im);tile=bg.convert('RGB').resize((792,528),Image.Resampling.NEAREST)
 # Show each crop at a readable size without changing its source registration.
 x=(i%2)*792;y=(i//2)*570;board.paste(tile,(x,y+24));d.text((x+10,y+6),label,fill=(30,30,40))
board.save(O/'material-review.png')
# Validate invariants, transparency and the exported ORA rather than counting loads.
assert all(np.array_equal(layers[-1][1],base) for layers in [pose(t) for t in (0,.25,.5,.75,1)])
assert all(np.array_equal(pose(t)[0][1],hairfull) for t in (0,.25,.5,.75,1))
for side,e in eyes.items():
 assert not e['sclera'][~e['aperture'],3].any()
 for n,a in pose(1):
  if n.endswith(' sclera') or n.endswith(' iris'):assert not a[:,:,3].any()
for n,a in materials:
 if n.endswith(('sclera','iris','upper-lash','lower-lash','closed-lash')):
  bb=Image.fromarray(a).getbbox();assert bb is not None
  x0,y0,x1,y1=bb;assert np.any(a[y0:y1,x0:x1,3]==0),n+' has an opaque skin rectangle'
with zipfile.ZipFile(O/'MewNook-face-materials.ora') as z:assert z.testzip() is None
metadata['validation']={'fixed_skin_identical_all_five_poses':True,'hair_material_identical_all_five_poses':True,'closed_eye_white_and_iris_hidden':True,'ora_integrity':True,'visual_acceptance':'pending','production_model_modified':False}
(O/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(metadata['validation']))
