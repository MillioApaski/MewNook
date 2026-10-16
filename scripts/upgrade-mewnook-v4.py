#!/usr/bin/env python3
"""Extend the upright MewNook v4 INX with native hair, tail and ear motion.

Requires the *new upright* 1122x1402 RGBA illustration, and the base
prototype produced by build-mewnook-v4.py. This is a reproducible
engineering rig from flattened art, not an artist-authored Inochi Creator
project; movement behind cut-out parts still needs overpainting.
"""
from __future__ import annotations
import argparse, copy, io, json, math, struct
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
NULL=4294967295
REGIONS={
 'Ear Left': ([(346,91),(389,74),(461,174),(455,201),(377,207),(347,158)],3,5,8,'ParamEarLeft',6),
 'Ear Right': ([(566,56),(641,4),(703,138),(679,188),(596,151)],3,5,8,'ParamEarRight',-6),
 'Hair Left Outer': ([(205,496),(325,480),(365,648),(278,1006),(152,1028),(106,849)],4,7,9,'ParamHairLeft',10),
 'Hair Right Outer': ([(754,450),(853,521),(1006,844),(963,1027),(810,994),(745,728)],4,7,9,'ParamHairRight',-10),
 'Tail': ([(889,462),(965,442),(1053,496),(1103,592),(1075,802),(994,877),(942,846),(997,765),(1018,613),(923,546)],5,7,9,'ParamTailDeform',15)
}
def load_inx(path):
    blob=path.read_bytes();assert blob[:8]==b'TRNSRTS\0'
    n=struct.unpack('>I',blob[8:12])[0]
    model=json.loads(blob[12:12+n]);pos=12+n
    assert blob[pos:pos+8]==b'TEX_SECT';pos+=8
    count=struct.unpack('>I',blob[pos:pos+4])[0];pos+=4
    textures=[]
    for _ in range(count):
        size=struct.unpack('>I',blob[pos:pos+4])[0];assert blob[pos+4]==0
        textures.append(blob[pos+5:pos+5+size]);pos+=5+size
    assert pos==len(blob)
    return model,textures
def save_inx(path,model,textures):
    payload=json.dumps(model,separators=(',',':'),ensure_ascii=False).encode()
    blob=bytearray(b'TRNSRTS\0')+struct.pack('>I',len(payload))+payload+b'TEX_SECT'+struct.pack('>I',len(textures))
    for tex in textures:blob+=struct.pack('>I',len(tex))+b'\0'+tex
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    picture=np.asarray(Image.open(args.source).convert('RGBA')).copy()
    H,W=picture.shape[:2]
    assert (W,H)==(1122,1402), 'v4 requires new 1122x1402 upright art'
    model,textures=load_inx(args.input)
    parts=model['nodes']['children'];params=model['param']
    byname={p['name']:p for p in parts}
    uid=max(v['uuid'] for v in parts+params)+1
    def fresh():
        nonlocal uid
        uid+=1;return uid
    def binding(part,key,values):
        return {'node':part['uuid'],'param_name':key,'values':values,
            'isSet':[[True,True] for _ in values],'interpolate_mode':'Linear'}
    def scalar(part,key,values):
        return binding(part,key,[[float(v),float(v)] for v in values])
    def param(name,bindings):
        assert name not in {p['name'] for p in params},name
        params.append({'uuid':fresh(),'name':name,'is_vec2':False,
            'min':[-1,0],'max':[1,1],'defaults':[0,.5],
            'axis_points':[[0,.5,1],[0,1]],'merge_mode':'Additive',
            'bindings':bindings})
    def add(name,mask,z):
        rgba=picture.copy()
        rgba[:,:,3]=((rgba[:,:,3].astype(np.uint16)*mask.astype(np.uint16)+127)//255).astype(np.uint8)
        yy,xx=np.nonzero(rgba[:,:,3]>3)
        assert len(xx)>10,name
        l,t,r,b=xx.min(),yy.min(),xx.max()+1,yy.max()+1
        rgba=rgba[t:b,l:r]
        rgba[:,:,:3]=((rgba[:,:,:3].astype(np.uint16)*rgba[:,:,3:4].astype(np.uint16)+127)//255).astype(np.uint8)
        out=io.BytesIO();Image.fromarray(rgba).save(out,'PNG',optimize=True)
        texid=len(textures);textures.append(out.getvalue())
        width,height=r-l,b-t
        node={'uuid':fresh(),'name':name,'type':'Part','enabled':True,'zsort':-float(z),
             'transform':{'trans':[(l+r-W)/2,(t+b-H)/2,-1.],'rot':[0,0,0],'scale':[1,1]},
             'lockToRoot':False,'mesh':{},'textures':[texid,NULL,NULL],
             'blend_mode':'Normal','tint':[1,1,1],'screenTint':[0,0,0],
             'emissionStrength':1,'masks':[],'mask_threshold':.5,
             'opacity':1.,'psdLayerPath':name}
        parts.append(node);return node,width,height
    def mesh_grid(part,width,height,cols,rows):
        verts=[];uvs=[];indices=[]
        for row in range(rows):
            v=row/(rows-1)
            for col in range(cols):
                u=col/(cols-1)
                verts.extend([width*(u-.5),height*(v-.5)]);uvs.extend([u,v])
        for row in range(rows-1):
            for col in range(cols-1):
                a=row*cols+col
                indices.extend([a,a+1,a+cols,a+1,a+cols+1,a+cols])
        part['mesh']={'verts':verts,'uvs':uvs,'indices':indices,'origin':[0,0]}
    def deform_keys(cols,rows,amplitude):
        all_keys=[]
        for sign in (-1.,0.,1.):
            offsets=[]
            for y in range(rows):
                fy=y/(rows-1)
                for x in range(cols):
                    fx=x/(cols-1)
                    sway=fy**1.7*(.85+.15*math.sin(fx*math.pi))
                    offsets.append([round(sign*amplitude*sway,4),
                         round(sign*amplitude*.06*fy*fx,4)])
            all_keys.append([offsets,offsets])
        return all_keys
    for name,(poly,z,cols,rows,param_name,amp) in REGIONS.items():
        mask=Image.new('L',(W,H),0)
        ImageDraw.Draw(mask).polygon(poly,fill=255)
        mask=np.asarray(mask.filter(ImageFilter.GaussianBlur(2.5)))
        part,width,height=add(name,mask,z)
        mesh_grid(part,width,height,cols,rows)
        param(param_name,[binding(part,'deform',deform_keys(cols,rows,amp))])
        if name.startswith('Ear'):
            param('Param'+name.replace(' ','')+'Tilt',
                  [scalar(part,'transform.r.z',[-.055,0,.055])])
    for side in ('Left','Right'):
        lid=byname['Eye '+side+' Cover']
        # Blink is the full closed-eye cover and its closed lash. The old
        # ParamSleepy bound these exact same transform fields and overwrote
        # blink on every Inox2D evaluation frame.
        blink=next(p for p in params if p['name']=='ParamEyeBlink'+side)
        blink['bindings'].append(scalar(lid,'transform.t.y',[-20,-20,0]))
        original=Image.open(io.BytesIO(textures[lid['textures'][0]])).convert('RGBA')
        layer=np.asarray(original).copy()
        h,w=layer.shape[:2]
        yy,xx=np.meshgrid(np.arange(h),np.arange(w),indexing='ij')
        slope=-.16 if side=='Left' else -.14
        # Only the iris's upper arc is concealed for drowsiness; the second
        # part is an independent tinted layer, not a scale on the blink iris.
        limit=.52*h+slope*(xx-w/2)
        blend=np.clip((limit-yy)/max(2,h*.085),0,1)
        layer=np.uint8(np.round(layer.astype(np.float32)*blend[:,:,None]))
        encoded=io.BytesIO()
        Image.fromarray(layer,'RGBA').save(encoded,'PNG',optimize=True)
        texid=len(textures);textures.append(encoded.getvalue())
        drowsy=copy.deepcopy(lid)
        drowsy['uuid']=fresh()
        drowsy['name']='Eye '+side+' Drowsy Cover'
        drowsy['psdLayerPath']=drowsy['name']
        drowsy['zsort']=-9.0
        drowsy['textures']=[texid,NULL,NULL]
        parts.append(drowsy)
        # Sleepy now owns only the new part. It cannot overwrite the blink
        # cover, so open, half-closed and fully-closed states are independent.
        param('ParamSleepy'+side,[
            scalar(drowsy,'transform.s.y',[.002,.002,1.]),
            scalar(drowsy,'transform.t.y',[-12,-12,0])
        ])
    param('ParamBreath',[scalar(byname['Upright Base'],
              'transform.s.y',[.997,1.,1.003])])
    model['meta']['name']='MewNook v4 Upright Motion Prototype'
    save_inx(args.output,model,textures)
    report={'status':'engineering_prototype_not_manual_rig','part_count':len(parts),
        'texture_count':len(textures),'parameter_count':len(params),
        'mesh_parts':list(REGIONS),
        'warning':'Source-flat overlays and no painted hidden surfaces; v3 stays default.'}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
