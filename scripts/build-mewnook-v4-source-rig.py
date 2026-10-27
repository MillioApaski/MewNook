#!/usr/bin/env python3
"""Build an INX solely from committed original-art scene parts and painted expression slots."""
from pathlib import Path
import argparse,io,json,struct,math
import numpy as np
from PIL import Image,ImageFilter
R=Path(__file__).resolve().parents[1];V=R/'assets/inochi/v4';S=V/'scene-source-v1';m=json.loads((S/'manifest.json').read_text());W,H=m['canvas'];pivot=np.array(m['head_pivot']);NULL=4294967295;uid=0;textures=[];params=[];nodes=[];sourceparts=[]
def fresh():
 global uid
 uid+=1;return uid
def node(name,trans=(0,0),children=None):return {'uuid':fresh(),'name':name,'type':'Node','enabled':True,'zsort':0,'transform':{'trans':[float(trans[0]),float(trans[1]),0.],'rot':[0.,0.,0.],'scale':[1.,1.]},'lockToRoot':False,'children':children or []}
parser=argparse.ArgumentParser();parser.add_argument('--foreground',action='store_true');parser.add_argument('--output',type=Path);args=parser.parse_args()
root=node('Root');breath=node('Head breath');head=node('Head root',pivot-np.array([W/2,H/2]));root['children'].append(breath);breath['children'].append(head)
def part(name,im,offset,z,parent,role,side=None):
 a=np.array(im.convert('RGBA'));h,w=a.shape[:2];a[:,:,:3]=((a[:,:,:3].astype('uint16')*a[:,:,3:4].astype('uint16')+127)//255).astype('uint8');buf=io.BytesIO();Image.fromarray(a).save(buf,format='PNG');tex=len(textures);textures.append(buf.getvalue());nx=26 if role=='work-hands' else 18 if role in ['eye-lash','eye-lid'] else 10 if role in ['ear','back-hair','connector','front-hair','body','neck-support','tail'] else 2;ny=24 if role=='work-hands' else 4 if role in ['eye-lash','eye-lid'] else 12 if nx>2 else 2
 verts=[];uv=[];indices=[];coords=[]
 for j in range(ny):
  for i in range(nx):
   x=i/(nx-1)*w;y=j/(ny-1)*h;verts.extend([x-w/2,y-h/2]);uv.extend([i/(nx-1),j/(ny-1)]);coords.append([x+offset[0],y+offset[1]])
 for j in range(ny-1):
  for i in range(nx-1):
   k=j*nx+i;indices.extend([k,k+1,k+nx,k+1,k+nx+1,k+nx])
 origin=pivot if parent is head else np.array([W/2,H/2]);center=np.array(offset)+[w/2,h/2]-origin;p={'uuid':fresh(),'name':name,'type':'Part','enabled':True,'zsort':float(z),'transform':{'trans':[float(center[0]),float(center[1]),-1.],'rot':[0.,0.,0.],'scale':[1.,1.]},'lockToRoot':False,'mesh':{'verts':verts,'uvs':uv,'indices':indices,'origin':[0,0]},'textures':[tex,NULL,NULL],'blend_mode':'Normal','tint':[1,1,1],'screenTint':[0,0,0],'emissionStrength':1,'masks':[],'mask_threshold':.5,'opacity':1,'psdLayerPath':name};parent['children'].append(p);sourceparts.append((p,role,np.array(coords),side));return p

def bind(p,key,values):return {'node':p['uuid'],'param_name':key,'values':[[v,v] for v in values],'isSet':[[True,True] for _ in values],'interpolate_mode':'Linear'}
def param(name,bindings,lo=-1,hi=1,n=3,default=0):
 params.append({'uuid':fresh(),'name':name,'is_vec2':False,'min':[lo,0],'max':[hi,1],'defaults':[default,.5],'axis_points':[[i/(n-1) for i in range(n)],[0,1]],'merge_mode':'Additive','bindings':bindings})
# Fixed face and true moving eyelids. Eye textures contain no skin backing.
F=V/'face-layer-rebuild-v1'
def imagepart(name,path,z,parent,role,side=None):
 im=Image.open(path).convert('RGBA');bb=im.getbbox();assert bb
 return part(name,im.crop(bb),bb[:2],z,parent,role,side)
def sourcexy(p):return next(xy for q,role,xy,side in sourceparts if q is p)
def profile(mask,mode):
 xs=np.flatnonzero(mask.any(0));ys=[np.flatnonzero(mask[:,x]) for x in xs]
 return np.interp(np.arange(W),xs,[np.min(a) if mode=='top' else np.max(a) if mode=='bottom' else np.mean(a) for a in ys])
def eye(side,z):
 opening=np.array(Image.open(V/'face-source-v5'/(side+'-opening-mask.png')))>0
 closed=np.array(Image.open(F/(side+'-closed-lash.png')).convert('RGBA'))
 top=profile(opening,'top');bottom=profile(opening,'bottom');curve=profile(closed[:,:,3]>128,'mean')
 bindings=[]
 # One source pixel of inset absorbs bilinear filtering at the aperture edge.
 eyeball_mask=np.array(Image.fromarray(opening.astype('uint8')*255).filter(ImageFilter.MinFilter(3)))>0
 # Keep the static eyeball inside the native aperture. Hidden iris underpaint
 # must not require a rectangular skin cover extending onto the cheek/hair.
 for label in ('sclera','iris'):
  im=np.array(Image.open(F/(side+'-'+label+'.png')).convert('RGBA'))
  im[:,:,3]=np.where(eyeball_mask,im[:,:,3],0)
  im=Image.fromarray(im);bb=im.getbbox();assert bb
  part(side+' independent '+label,im.crop(bb),bb[:2],z-5 if label=='iris' else z-4,head,'eye',side)
 skin=np.array(Image.open(V/'face-layer-rebuild-v3/face-and-neck.png').convert('RGBA'))
 xs=np.flatnonzero(opening.any(0));x0,x1=int(xs.min()),int(xs.max())+1
 y0,y1=int(top[xs].min())-1,int(bottom[xs].max())+2
 # Every column has an anchored aperture boundary. UVs sample the final clean
 # skin inside that aperture; no surrounding face/hair pixels move with a lid.
 for upper in (True,False):
  lid=skin[y0:y1,x0:x1].copy();lid[:,:,3]=255
  q=part(side+(' upper' if upper else ' lower')+' moving eyelid skin',Image.fromarray(lid),(x0,y0),z-6,head,'eye-lid',side)
  nx=x1-x0+1;ny=4;initial=[];target=[];uv=[];indices=[]
  offset=np.array([x0+(x1-x0)/2,y0+(y1-y0)/2])
  for j in range(ny):
   f=j/(ny-1)
   for i in range(nx):
    x=x0+i;xi=min(x,x1-1)
    hi=top[xi]-.5;lo=bottom[xi]+.5
    closed_y=float(np.clip(curve[xi],hi,lo))
    edge=hi if upper else lo
    end=min(lo,closed_y+1.5) if upper else max(hi,closed_y-1.5)
    initial.append([x,edge]);target.append([x,edge+(end-edge)*f])
    uv.extend([i/(nx-1),(edge+(end-edge)*f-y0)/(y1-y0)])
  for j in range(ny-1):
   for i in range(nx-1):
    k=j*nx+i;indices.extend([k,k+1,k+nx,k+1,k+nx+1,k+nx])
  initial=np.array(initial,dtype=float);target=np.array(target,dtype=float)
  q['mesh'].update(verts=(initial-offset).reshape(-1).tolist(),uvs=uv,indices=indices)
  delta=target-initial;bindings.append(bind(q,'deform',[np.zeros_like(delta).tolist(),delta.tolist()]))
 for label in ('upper-lash','lower-lash'):
  q=imagepart(side+' independent '+label,F/(side+'-'+label+'.png'),z-8,head,'eye-lash',side)
  xy=sourcexy(q);d=np.zeros_like(xy)
  for i,(x,y) in enumerate(xy):
   xi=int(np.clip(round(x),0,W-1));d[i,1]=curve[xi]-(top[xi] if label=='upper-lash' else bottom[xi])
  bindings.append(bind(q,'deform',[np.zeros_like(d).tolist(),d.tolist()]))
  bindings.append(bind(q,'opacity',[1.]*8+[0.]))
 # Full closure retains the approved painted lash shape; blend only lashes.
 q=imagepart(side+' approved closed lash',F/(side+'-closed-lash.png'),z-9,head,'eye',side);q['opacity']=0
 # Supply consistent three knots for opacity and deformation bindings.
 expanded=[]
 for b in bindings:
  if len(b['values'])==2:
   v0,v1=[v[0] for v in b['values']];v0=np.array(v0);v1=np.array(v1)
   b['values']=[[(v0+(v1-v0)*t).tolist(),(v0+(v1-v0)*t).tolist()] for t in np.linspace(0,1,9)];b['isSet']=[[True,True]]*9
  expanded.append(b)
 expanded.append(bind(q,'opacity',[0.]*8+[1.]))
 param('ParamEyeBlink'+side.title(),expanded,0,1,9)

for e in ([] if args.foreground else m['parts']):
 parent=head if e['head_child'] else root;z=100*(e['front_order']-len(m['parts']));s='left' if 'left' in e['name'].lower() else 'right' if 'right' in e['name'].lower() else None
 if e['role']=='eye':
  eye(s,z);continue
 if e['role']=='mouth':
  m2=json.loads((V/'face-source-v7/manifest.json').read_text());folder=V/'face-source-v7';offset=m2['mouth_slot_offset'];prefix='mouth-';parameter='ParamMouthOpen'
  bindings=[];keys=m2['keys']
  for k,t in enumerate(keys):
   p=part(e['name']+' '+str(round(t*1000)),Image.open(folder/(prefix+str(round(t*1000))+'.png')),offset,z-k,parent,e['role'],s)
   # Progressive opaque covers: preceding key stays opaque under the next key's ramp.
   values=[1. if k==0 or j>=k else 0. for j in range(len(keys))];bindings.append(bind(p,'opacity',values))
  param(parameter,bindings,0,1,len(keys))
  if e['role']=='mouth':
   sleepy=part('Original painted tiny sleepy mouth',Image.open(V/'sleepy-source-v1/mouth-sleepy.png'),offset,z-len(keys),parent,'mouth',s)
   sleepy['opacity']=0
   param('ParamDrowsyMouth',[bind(sleepy,'opacity',[0.,1.])],0,1,2)
 elif e['role']=='body':
  q=part(e['name'],Image.open(S/e['file']),e['offset'],z,parent,'body',s)
  param('ParamFocus',[bind(q,'opacity',[1.,0.])],0,1,2)
  for pose in ('typing','reading'):
   q=imagepart(pose+' focus torso',V/'focus-source-v1'/(pose+'-body.png'),z-1,parent,'body',None);q['opacity']=0
   param('ParamFocus'+pose.title(),[bind(q,'opacity',[0.,1.])],0,1,2)
 elif e['role']=='face':
  imagepart('Fixed clean face and original neck',V/'face-layer-rebuild-v3/face-and-neck.png',z,parent,'face',None)
 else:part(e['name'],Image.open(S/e['file']),e['offset'],z,parent,e['role'],s)
if args.foreground:
 enter=[];work={'Left':[],'Right':[]}
 for pose in ('typing','reading'):
  q=imagepart(pose+' foreground forearms and '+('keyboard' if pose=='typing' else 'book'),V/'focus-source-v1'/(pose+'-hands.png'),-100,root,'work-hands',None);q['opacity']=0
  param('ParamFocus'+pose.title(),[bind(q,'opacity',[0.,1.])],0,1,2)
  xy=sourcexy(q);x,y=xy.T;zero=np.zeros_like(xy);down=zero.copy();down[:,1]=30*np.clip((y-695)/200,0,1)
  enter.append(bind(q,'deform',[down.tolist(),zero.tolist()]))
  for side in ('Left','Right'):
   d=zero.copy();weight=np.clip(1-np.abs(y-875)/60,0,1)*np.clip(((585-x) if side=='Left' else (x-565))/65,0,1)
   d[:,1]=weight*(1.4 if pose=='typing' else .2);work[side].append(bind(q,'deform',[(-d).tolist(),zero.tolist(),d.tolist()]))
 param('ParamFocus',enter,0,1,2)
 for side in ('Left','Right'):param('ParamWork'+side,work[side])
# Independently painted pitch pose; never scale/squash the original head.
# Visibility envelopes multiply existing blink/mouth opacities.
old_head=[q for q in head['children'] if q.get('type')=='Part']
look=[]
for q in old_head:
 b=bind(q,'opacity',[1.,0.]);b['opacity_mode']='multiply';look.append(b)
if not args.foreground:
 FOCUS=V/'focus-head-v2'
 q=imagepart('Painted studying head',FOCUS/'head.png',-10000,head,'focus-head');q['opacity']=0
 look.append(bind(q,'opacity',[0.,1.]))
 for side in ('left','right'):
  q=imagepart(side+' studying blink',FOCUS/(side+'-blink.png'),-10001,head,'focus-lid',side);q['opacity']=0
  xy=sourcexy(q);d=np.zeros_like(xy);d[:,1]=xy[:,1].min()-xy[:,1]
  p=next(p for p in params if p['name']=='ParamEyeBlink'+side.title())
  p['bindings'].append(bind(q,'deform',[(d*(1-t)).tolist() for t in np.linspace(0,1,9)]))
  p['bindings'].append(bind(q,'opacity',[0.]+[1.]*8))
  b=bind(q,'opacity',[0.,1.]);b['opacity_mode']='multiply';look.append(b)
 q=imagepart('Studying speaking mouth',FOCUS/'mouth-open.png',-10002,head,'focus-mouth');q['opacity']=0
 p=next(p for p in params if p['name']=='ParamMouthOpen')
 p['bindings'].append(bind(q,'opacity',np.linspace(0,1,len(p['axis_points'][0])).tolist()))
 b=bind(q,'opacity',[0.,1.]);b['opacity_mode']='multiply';look.append(b)
param('ParamWorkLookDown',look,0,1,2)
# Separate touch-only weight makes the bow visible without amplifying idle/chat.
param('ParamHeadPat',[bind(head,'transform.t.y',[0.,7.]),bind(head,'transform.r.z',[0.,.025])],0,1,2)
param('ParamHeadRoll',[bind(head,'transform.r.z',[-.055,0,.055])]);param('ParamHeadX',[bind(head,'transform.t.x',[-3.,0.,3.])]);param('ParamHeadY',[bind(head,'transform.t.y',[-3.,0.,3.])])
hair={'left':[],'right':[],'front':[]};ear={'left':[],'right':[]};brow={'left':[],'right':[]};breathing=[bind(breath,'transform.t.y',[1.5,0.,-1.5])];tail=[]
for p,role,xy,s in sourceparts:
 x,y=xy.T;zero=np.zeros_like(xy);d=zero.copy()
 if role in ['back-hair','connector'] or (role=='front-hair' and 'chest' in p['name']):
  amplitude=10 if role=='back-hair' else 2.5;d[:,0]=np.clip((y-(320 if role=='back-hair' else 210))/ (650 if role=='back-hair' else 300),0,1)*amplitude;hair[s or 'front'].append(bind(p,'deform',[(-d).tolist(),zero.tolist(),d.tolist()]))
 elif role=='front-hair':
  d[:,0]=np.clip((y-80)/260,0,1)*1.5;hair['front'].append(bind(p,'deform',[(-d).tolist(),zero.tolist(),d.tolist()]))
 elif role=='ear':
  distance=(-57*(y-112)-95*(x-451))/110.8 if s=='left' else (102*(x-577)-107*(y-72))/147.8;weight=np.clip((distance-8)/90,0,1);center=np.array(m['ears'][s]['pivot']);v=xy-center;d[:,0]=-v[:,1]*.08*weight;d[:,1]=v[:,0]*.08*weight;ear[s].append(bind(p,'deform',[(-d).tolist(),zero.tolist(),d.tolist()]))
 elif role=='brow':brow[s].append(bind(p,'transform.t.y',[-2.,0.,2.]))
 elif role in ['body','neck-support','work-hands']:
  d[:,1]=-1.5*np.clip((863-y)/480,0,1);breathing.append(bind(p,'deform',[(-d).tolist(),zero.tolist(),d.tolist()]))
 elif role=='tail':
  d[:,0]=10*np.clip((865-y)/430,0,1)**2;d[:,1]=3*np.clip((865-y)/430,0,1);tail.append(bind(p,'deform',[(-d).tolist(),zero.tolist(),d.tolist()]))
for s in ('left','right'):
 param('ParamHair'+s.title(),hair[s]);param('ParamEar'+s.title(),ear[s]);param('ParamBrow'+s.title(),brow[s])
param('ParamHairFront',hair['front']);param('ParamBreath',breathing);param('ParamTailDeform',tail)
for name in ['ParamSmile','ParamSleepy','ParamSleepyLeft','ParamSleepyRight','ParamEmbarrassed','ParamEyeDeformLeft','ParamLidCurveLeft','ParamBodyZ','ParamTailSwing']:param(name,[])
model={'meta':{'name':'MewNook v4 Source Art Review','version':'v0.9.0','rigger':'MewNook','artist':'Original MewNook art and registered hidden/pose repaint','rights':None,'copyright':'MewNook','licenseURL':'','contact':'','reference':'','thumbnailId':NULL,'preservePixels':False,'sourceArtOpacityBindings':True},'physics':{'pixelsPerMeter':2000.,'gravity':9.8},'nodes':root,'param':params,'automation':[],'animations':[],'groups':[]}
args.output=args.output or (V/('rig/MewNook-v4-hands.inx' if args.foreground else 'rig/MewNook-v4-source-rig.inx'));payload=json.dumps(model,separators=(',',':'),ensure_ascii=False).encode();blob=bytearray(b'TRNSRTS\0')+struct.pack('>I',len(payload))+payload+b'TEX_SECT'+struct.pack('>I',len(textures))
for tex in textures:blob+=struct.pack('>I',len(tex))+b'\0'+tex
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(blob);print(len(sourceparts),'parts',len(params),'parameters',len(blob),'bytes',args.output)
