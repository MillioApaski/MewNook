#!/usr/bin/env python3
"""Isolated smoke-page revision. Never overwrites the room's v4 model."""
import argparse, importlib.util, io, math
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

spec=importlib.util.spec_from_file_location('rig',Path(__file__).with_name('upgrade-mewnook-v4.py'))
rig=importlib.util.module_from_spec(spec);spec.loader.exec_module(rig)
parser=argparse.ArgumentParser()
parser.add_argument('--input',type=Path,default=Path('public/inochi2d-test/models/MewNook-v4.inx'))
parser.add_argument('--output',type=Path,default=Path('public/inochi2d-test/models/MewNook-v4-review.inx'))
args=parser.parse_args()
model,textures=rig.load_inx(args.input)
parts=model['nodes']['children'];byname={p['name']:p for p in parts}
params={p['name']:p for p in model['param']}
source=Image.open('assets/inochi/v4/source/pose_reference.png').convert('RGBA');W,H=source.size

def encode(image):
    a=np.asarray(image).copy()
    a[:,:,:3]=((a[:,:,:3].astype(np.uint16)*a[:,:,3:4].astype(np.uint16)+127)//255).astype(np.uint8)
    out=io.BytesIO();Image.fromarray(a).save(out,'PNG');return out.getvalue()

def art(part,image,cols=2,rows=2,pivot=None):
    box=image.getbbox();assert box,part['name']
    l,t,r,b=box;w,h=r-l,b-t
    px,py=pivot or ((l+r)/2,(t+b)/2)
    part['transform']['trans']=[px-W/2,py-H/2,-1]
    part['textures'][0]=len(textures);textures.append(encode(image.crop(box)))
    verts=[];uv=[];indices=[]
    for y in range(rows):
        for x in range(cols):
            u=x/(cols-1);v=y/(rows-1)
            verts.extend([l+w*u-px,t+h*v-py]);uv.extend([u,v])
    for y in range(rows-1):
        for x in range(cols-1):
            a=y*cols+x;indices.extend([a,a+1,a+cols,a+1,a+cols+1,a+cols])
    part['mesh']={'verts':verts,'uvs':uv,'indices':indices,'origin':[0,0]}

def bind(part,key,values):
    return {'node':part['uuid'],'param_name':key,'values':[[v,v] for v in values],
            'isSet':[[True,True] for _ in values],'interpolate_mode':'Linear'}

# Extract the actual ears and remove their original pixels. Earlier overlays
# deformed above a complete stationary copy of each ear in the base texture.
base=byname['Upright Base'];base_image=Image.open(io.BytesIO(textures[base['textures'][0]])).convert('RGBA')
verts=base['mesh']['verts'];bw=max(verts[::2])-min(verts[::2]);bh=max(verts[1::2])-min(verts[1::2])
bl=round(base['transform']['trans'][0]+W/2-bw/2);bt=round(base['transform']['trans'][1]+H/2-bh/2)
for side,poly,pivot in [
 ('Left',[(354,88),(410,90),(451,112),(427,142),(404,174),(394,207),(374,179),(360,131)],(410,185)),
 ('Right',[(577,72),(624,33),(670,6),(686,44),(701,114),(701,149),(684,174),(661,151),(622,127)],(667,151))
]:
    mask=Image.new('L',(W,H));ImageDraw.Draw(mask).polygon(poly,fill=255)
    cut=source.copy();cut.putalpha(Image.composite(source.getchannel('A'),Image.new('L',(W,H)),mask))
    part=byname['Ear '+side];art(part,cut,5,8,pivot)
    # base_image is already premultiplied: erase all RGBA together.
    a=np.asarray(base_image).copy();m=np.asarray(mask.crop((bl,bt,bl+base_image.width,bt+base_image.height)))
    a[m>0]=0;base_image=Image.fromarray(a)
    keys=[]
    for sign in (-1,0,1):
        angle=sign*.38;co=math.cos(angle);si=math.sin(angle);offset=[]
        for x,y in zip(part['mesh']['verts'][::2],part['mesh']['verts'][1::2]):
            # Root stays put. Ear tip makes a visible ~25px arc in source space.
            # Attachment follows the sloping hair/ear seam, not a horizontal
            # row. Pin that entire edge to avoid opening a triangular hole.
            sx,sy=x+pivot[0],y+pivot[1]
            distance=((-57*(sy-112)-95*(sx-451))/110.8 if side=='Left'
                      else (102*(sx-577)-107*(sy-72))/147.8)
            weight=max(0,min(1,distance/100))
            offset.append([(x*co-y*si-x)*weight,(x*si+y*co-y)*weight])
        keys.append([offset,offset])
    params['ParamEar'+side]['bindings'][0]['values']=keys
out=io.BytesIO();base_image.save(out,'PNG');textures[base['textures'][0]]=out.getvalue()

# Remove the old smile's remaining right edge and preserve the original smile
# as the sole neutral mouth. Face pixels here are fully opaque.
a=np.asarray(base_image).copy();mask=np.zeros(a.shape[:2],np.uint8)
cv2.ellipse(mask,(589-bl,315-bt),(26,13),-20,0,360,255,-1)
a[:,:,:3]=cv2.inpaint(a[:,:,:3],mask,7,cv2.INPAINT_TELEA)
out=io.BytesIO();Image.fromarray(a).save(out,'PNG');textures[base['textures'][0]]=out.getvalue()
neutral=source.copy();mouth_mask=Image.new('L',(W,H))
cv_mask=np.zeros((H,W),np.uint8);cv2.ellipse(cv_mask,(589,315),(26,13),-20,0,360,255,-1)
neutral.putalpha(Image.fromarray(cv_mask));art(byname['Mouth Neutral'],neutral)

# Mouth is aligned to the reference smile at (589,315), not (574,311).
# Supersampled curved cavity, upper teeth and tongue replace a flat dark slit.
for name,width,height in [('Mouth A',14,13),('Mouth B',19,18)]:
    image=Image.new('RGBA',(W*3,H*3));d=ImageDraw.Draw(image)
    def xy(x,y):
        angle=math.radians(-20)
        return (round(3*(589+x*math.cos(angle)-y*math.sin(angle))),round(3*(315+x*math.sin(angle)+y*math.cos(angle))))
    top=[];bottom=[]
    for i in range(49):
        u=i/48;x=(u*2-1)*width;s=math.sin(math.pi*u)
        top.append(xy(x,-height*.17*s));bottom.append(xy(x,height*.8*s))
    d.polygon(top+bottom[::-1],fill=(105,53,75,255))
    tongue=[xy((u*2-1)*width*.65,height*(.50+.19*math.sin(math.pi*u))) for u in np.linspace(0,1,25)]
    d.line(tongue,fill=(220,134,151,255),width=6)
    teeth=[xy((u*2-1)*width*.64,height*.04) for u in np.linspace(0,1,20)]
    d.line(teeth,fill=(255,236,228,255),width=4)
    d.line(top,fill=(142,81,99,255),width=3)
    art(byname[name],image.resize((W,H),Image.Resampling.LANCZOS))

# Inox2D's native opacity binding is not implemented by this pinned WASM.
# Gate BOTH mesh axes instead of leaving a flattened one-axis mouth sliver.
p=params['ParamMouthOpen']
extra=[]
for binding in p['bindings']:
    binding['param_name']='transform.s.y'
    binding['values']=[[.00001 if v[0]<.01 else 1]*2 for v in binding['values']]
    import copy
    twin=copy.deepcopy(binding);twin['param_name']='transform.s.x';extra.append(twin)
p['bindings'].extend(extra)
params['ParamSleepy']['bindings']=[bind(byname['Mouth Sleepy'],'transform.s.x',[.00001]*3),bind(byname['Mouth Sleepy'],'transform.s.y',[.00001]*3)]

# Keep covers anchored to the top edge instead of expanding a skin oval around
# the middle of the eye. Move the closed lash with the descending eyelid.
for side,slope in [('Left',-.16),('Right',-.14)]:
    cover=byname['Eye '+side+' Cover'];lash=byname['Eye '+side+' Lash']
    covertex=Image.open(io.BytesIO(textures[cover['textures'][0]]))
    h=covertex.height
    blink=params['ParamEyeBlink'+side]
    blink['bindings']=[bind(cover,'transform.s.y',[.002,.002,1]),
                       bind(cover,'transform.t.y',[-h/2,-h/2,0]),
                       bind(lash,'transform.s.x',[.00001,.00001,1]),
                       bind(lash,'transform.s.y',[.00001,.00001,1]),
                       bind(lash,'transform.t.y',[-h/2,-h/2,0])]
    # Independent drowsy cover keeps its original size, with a drawn lash along
    # the lower edge. It fades in; it does not squash skin over the iris.
    sleepy=byname['Eye '+side+' Drowsy Cover']
    params['ParamSleepy'+side]['bindings']=[bind(sleepy,'transform.s.x',[.00001,.00001,1])]
    image=Image.open(io.BytesIO(textures[sleepy['textures'][0]])).convert('RGBA')
    d=ImageDraw.Draw(image)
    w,h=image.size
    line=[]
    for x in range(6,w-6):
        y=.52*h+slope*(x-w/2)-max(2,h*.085)
        line.append((x,round(y)))
    d.line(line,fill=(107,73,95,235),width=2)
    # Existing texture is premultiplied, newly drawn line also needs it.
    a=np.asarray(image).copy();old=np.asarray(Image.open(io.BytesIO(textures[sleepy['textures'][0]])).convert('RGBA'))
    changed=np.any(a!=old,axis=2)
    a[changed,:3]=((a[changed,:3].astype(np.uint16)*a[changed,3:4].astype(np.uint16)+127)//255).astype(np.uint8)
    out=io.BytesIO();Image.fromarray(a).save(out,'PNG');textures[sleepy['textures'][0]]=out.getvalue()

model['meta']['name']='MewNook v4 isolated visual revision 1'
rig.save_inx(args.output,model,textures)
print('Wrote isolated visual candidate:',args.output)
