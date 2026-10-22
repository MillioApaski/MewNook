#!/usr/bin/env python3
"""Build an INX solely from committed original-art scene parts and painted expression slots."""
from pathlib import Path
import argparse,io,json,struct,math
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];V=R/'assets/inochi/v4';S=V/'scene-source-v1';m=json.loads((S/'manifest.json').read_text());W,H=m['canvas'];pivot=np.array(m['head_pivot']);NULL=4294967295;uid=0;textures=[];params=[];nodes=[];sourceparts=[]
def fresh():
 global uid
 uid+=1;return uid
def node(name,trans=(0,0),children=None):return {'uuid':fresh(),'name':name,'type':'Node','enabled':True,'zsort':0,'transform':{'trans':[float(trans[0]),float(trans[1]),0.],'rot':[0.,0.,0.],'scale':[1.,1.]},'lockToRoot':False,'children':children or []}
root=node('Root');breath=node('Head breath');head=node('Head root',pivot-np.array([W/2,H/2]));root['children'].append(breath);breath['children'].append(head)
def part(name,im,offset,z,parent,role,side=None):
 a=np.array(im.convert('RGBA'));h,w=a.shape[:2];a[:,:,:3]=((a[:,:,:3].astype('uint16')*a[:,:,3:4].astype('uint16')+127)//255).astype('uint8');buf=io.BytesIO();Image.fromarray(a).save(buf,format='PNG');tex=len(textures);textures.append(buf.getvalue());nx=10 if role in ['ear','back-hair','connector','front-hair','body','neck-support','tail'] else 2;ny=12 if nx>2 else 2
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
for e in m['parts']:
 parent=head if e['head_child'] else root;z=100*(e['front_order']-len(m['parts']));s='left' if 'left' in e['name'].lower() else 'right' if 'right' in e['name'].lower() else None
 if e['role'] in ['eye','mouth']:
  if e['role']=='eye':m2=json.loads((V/'face-source-v10/manifest.json').read_text());folder=V/'face-source-v10';offset=m2['eyes'][s]['slot_offset'];prefix=s+'-blink-';parameter='ParamEyeBlink'+s.title()
  else:m2=json.loads((V/'face-source-v7/manifest.json').read_text());folder=V/'face-source-v7';offset=m2['mouth_slot_offset'];prefix='mouth-';parameter='ParamMouthOpen'
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
 else:part(e['name'],Image.open(S/e['file']),e['offset'],z,parent,e['role'],s)
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
 elif role in ['body','neck-support']:
  d[:,1]=-1.5*np.clip((863-y)/480,0,1);breathing.append(bind(p,'deform',[(-d).tolist(),zero.tolist(),d.tolist()]))
 elif role=='tail':
  d[:,0]=10*np.clip((865-y)/430,0,1)**2;d[:,1]=3*np.clip((865-y)/430,0,1);tail.append(bind(p,'deform',[(-d).tolist(),zero.tolist(),d.tolist()]))
for s in ('left','right'):
 param('ParamHair'+s.title(),hair[s]);param('ParamEar'+s.title(),ear[s]);param('ParamBrow'+s.title(),brow[s])
param('ParamHairFront',hair['front']);param('ParamBreath',breathing);param('ParamTailDeform',tail)
for name in ['ParamSmile','ParamSleepy','ParamSleepyLeft','ParamSleepyRight','ParamEmbarrassed','ParamEyeDeformLeft','ParamLidCurveLeft','ParamBodyZ','ParamTailSwing']:param(name,[])
model={'meta':{'name':'MewNook v4 Source Art Review','version':'v0.8.6','rigger':'MewNook','artist':'Original MewNook art and registered hidden/pose repaint','rights':None,'copyright':'MewNook','licenseURL':'','contact':'','reference':'','thumbnailId':NULL,'preservePixels':False,'sourceArtOpacityBindings':True},'physics':{'pixelsPerMeter':2000.,'gravity':9.8},'nodes':root,'param':params,'automation':[],'animations':[],'groups':[]}
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=V/'rig/MewNook-v4-source-rig.inx');args=parser.parse_args();payload=json.dumps(model,separators=(',',':'),ensure_ascii=False).encode();blob=bytearray(b'TRNSRTS\0')+struct.pack('>I',len(payload))+payload+b'TEX_SECT'+struct.pack('>I',len(textures))
for tex in textures:blob+=struct.pack('>I',len(tex))+b'\0'+tex
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(blob);print(len(sourceparts),'parts',len(params),'parameters',len(blob),'bytes',args.output)
