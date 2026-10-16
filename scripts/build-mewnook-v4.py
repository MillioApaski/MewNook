#!/usr/bin/env python3
"""Build a source-aligned MewNook v4 INX engineering prototype.

Source: assets/inochi/v4/source/pose_reference.png (1122x1402 RGBA).
The source PNG must be committed/provided separately. v3 stays unchanged.

This stage has independently aligned facial layers and a real INX payload,
but does NOT constitute artist-redrawn, professionally rigged Inochi2D.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import struct
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets/inochi/v4/source/pose_reference.png"
OUT = ROOT / "assets/inochi/v4/rig/MewNook-v4-prototype.inx"
NULL = 4294967295
EYES = {
    "Left": {"center": (518, 278), "axes": (51, 32), "angle": -16,
             "curve": ((472, 289), (493, 268), (523, 264), (559, 270))},
    "Right": {"center": (622, 247), "axes": (49, 31), "angle": -14,
              "curve": ((580, 258), (596, 234), (634, 224), (664, 228))}
}

def elliptical(center, axes, angle, w, h, sigma=1.2):
    m = np.zeros((h,w), dtype=np.uint8)
    cv2.ellipse(m, center, axes, angle, 0, 360, 255, -1, cv2.LINE_AA)
    return cv2.GaussianBlur(m, (0,0), sigma)

def crop_rgba(rgb, mask):
    result = rgb.copy()
    result[:,:,3] = ((result[:,:,3].astype(np.uint16) *
                      mask.astype(np.uint16) + 127)//255).astype(np.uint8)
    return result

def closed_lash(curve, w, h):
    layer = Image.new("RGBA", (w,h))
    draw = ImageDraw.Draw(layer)
    points=[]
    a,b,c,d=curve
    for step in range(41):
        t=step/40
        points.append((round((1-t)**3*a[0]+3*(1-t)**2*t*b[0]+
                            3*(1-t)*t*t*c[0]+t**3*d[0]),
                       round((1-t)**3*a[1]+3*(1-t)**2*t*b[1]+
                             3*(1-t)*t*t*c[1]+t**3*d[1])))
    draw.line(points, fill=(101,69,94,238), width=4, joint="curve")
    return np.asarray(layer.filter(ImageFilter.GaussianBlur(.25))).copy()

def mouth_pose(w, h, halfwidth, opening):
    canvas=Image.new("RGBA",(w*2,h*2))
    d=ImageDraw.Draw(canvas)
    rotation=math.radians(-20)
    def pt(x,y):
        return (round(2*(574+x*math.cos(rotation)-y*math.sin(rotation))),
                round(2*(311+x*math.sin(rotation)+y*math.cos(rotation))))
    top=[];bottom=[]
    for i in range(33):
        t=i/32
        x=(2*t-1)*halfwidth
        p=math.sin(math.pi*t)**.9
        top.append(pt(x,-opening*.22*p))
        bottom.append(pt(x,opening*.72*p))
    d.polygon(top+list(reversed(bottom)),fill=(117,70,95,231))
    d.line(top,fill=(136,90,111,213),width=3,joint="curve")
    return np.asarray(canvas.resize((w,h),Image.Resampling.LANCZOS)).copy()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=SRC)
    parser.add_argument("--output", type=Path, default=OUT)
    args=parser.parse_args()
    if not args.input.exists():
        raise SystemExit(
            "The upright source image is not in the repo. Place the real "
            "1122x1402 RGBA illustration at: "+str(args.input))
    source=np.asarray(Image.open(args.input).convert("RGBA")).copy()
    h,w=source.shape[:2]
    if (w,h)!=(1122,1402):
        raise SystemExit("Expected 1122x1402, got %sx%s"%(w,h))

    # Remove detached generation artifacts, including a stray spot at right.
    alpha=source[:,:,3]
    n, labels, stats, _=cv2.connectedComponentsWithStats(
        (alpha>4).astype(np.uint8), connectivity=8)
    largest=1+int(np.argmax(stats[1:,cv2.CC_STAT_AREA]))
    source[:,:,3]=np.where(labels==largest,alpha,0)
    base=source.copy()
    eye_art={}
    combined=np.zeros((h,w),dtype=np.uint8)
    for side,data in EYES.items():
        mask=elliptical(data["center"],data["axes"],data["angle"],w,h)
        combined=np.maximum(combined,mask)
        eye_art[side]=crop_rgba(source,mask)
    # This inpaint is an approximate placeholder, NOT manual hidden-area art.
    base[:,:,:3]=cv2.inpaint(base[:,:,:3],
        cv2.dilate((combined>16).astype(np.uint8),np.ones((5,5),np.uint8))*255,
        11,cv2.INPAINT_TELEA)
    mouth_mask=elliptical((574,311),(25,12),-20,w,h,1.5)
    neutral=crop_rgba(source,mouth_mask)
    base[:,:,:3]=cv2.inpaint(base[:,:,:3],
        (mouth_mask>12).astype(np.uint8)*255,7,cv2.INPAINT_TELEA)

    layers=[("Upright Base",base,0)]
    for side,data in EYES.items():
        layers.append(("Eye "+side,eye_art[side],5 if side=="Left" else 6))
        layers.append(("Eye "+side+" Cover",
            crop_rgba(base,elliptical(data["center"],data["axes"],data["angle"],w,h)),8))
        layers.append(("Eye "+side+" Lash",closed_lash(data["curve"],w,h),10))
    layers.extend([
        ("Mouth Neutral",neutral,15),
        ("Mouth A",mouth_pose(w,h,13,7),16),
        ("Mouth B",mouth_pose(w,h,17,12),17),
        ("Mouth Sleepy",mouth_pose(w,h,10,6),18)
    ])
    textures=[]
    parts={}
    uid=30000
    def fresh():
        nonlocal uid
        uid+=1
        return uid
    for name,art,z in layers:
        ys,xs=np.nonzero(art[:,:,3]>0)
        if not len(xs):
            raise RuntimeError("Empty v4 part "+name)
        l,t,r,b=xs.min(),ys.min(),xs.max()+1,ys.max()+1
        crop=art[t:b,l:r].copy()
        # Inox2D Normal shader expects premultiplied alpha.
        crop[:,:,:3]=((crop[:,:,:3].astype(np.uint16) *
                       crop[:,:,3:4].astype(np.uint16)+127)//255).astype(np.uint8)
        buf=io.BytesIO()
        Image.fromarray(crop).save(buf,format="PNG",optimize=True)
        texid=len(textures)
        textures.append(buf.getvalue())
        width,height=r-l,b-t
        parts[name]={
          "uuid":fresh(),"name":name,"type":"Part","enabled":True,"zsort":-float(z),
          "transform":{"trans":[(l+r-w)/2,(t+b-h)/2,-1.],
                       "rot":[0,0,0],"scale":[1,1]},"lockToRoot":False,
          "mesh":{"verts":[-width/2,-height/2,-width/2,height/2,
                           width/2,-height/2,width/2,height/2],
                  "uvs":[0,0,0,1,1,0,1,1],"indices":[0,2,1,2,3,1],
                  "origin":[0,0]},
          "textures":[texid,NULL,NULL],"blend_mode":"Normal","tint":[1,1,1],
          "screenTint":[0,0,0],"emissionStrength":1,"masks":[],
          "mask_threshold":.5,"opacity":1,"psdLayerPath":name
        }

    parameters=[]
    def bind(node, values):
        return {"node":parts[node]["uuid"],"param_name":"transform.s.y",
                "values":[[float(v),float(v)] for v in values],
                "isSet":[[True,True] for v in values],
                "interpolate_mode":"Linear"}
    def param(name, bindings):
        n=len(bindings[0][1])
        parameters.append({
          "uuid":fresh(),"name":name,"is_vec2":False,
          "min":[-1,0],"max":[1,1],"defaults":[0,.5],
          "axis_points":[[i/(n-1) for i in range(n)],[0,1]],
          "merge_mode":"Additive",
          "bindings":[bind(node,values) for node,values in bindings]
        })
    for side in EYES:
        param("ParamEyeBlink"+side,
              [("Eye "+side+" Cover",[.002,.002,1.]),
               ("Eye "+side+" Lash",[.002,.002,1.])])
    param("ParamMouthOpen",
          [("Mouth Neutral",[1,1,1,.002,.002]),
           ("Mouth A",[.002,.002,.002,1,.002]),
           ("Mouth B",[.002,.002,.002,.002,1])])
    param("ParamSleepy",[("Mouth Sleepy",[.002,.002,1])])

    root={"uuid":fresh(),"name":"Root","type":"Node","enabled":True,"zsort":0,
          "transform":{"trans":[0,0,0],"rot":[0,0,0],"scale":[1,1]},
          "lockToRoot":False,"children":list(parts.values())}
    model={"meta":{"name":"MewNook v4 Upright Prototype",
                   "version":"v0.8.6","rigger":"MewNook source prototype",
                   "artist":"MewNook upright source art","rights":None,
                   "copyright":"MewNook","licenseURL":"","contact":"",
                   "reference":"","thumbnailId":NULL,"preservePixels":False},
           "physics":{"pixelsPerMeter":2000.,"gravity":9.8},
           "nodes":root,"param":parameters,
           "automation":[],"animations":[],"groups":[]}
    payload=json.dumps(model,separators=(",",":"),ensure_ascii=False).encode()
    out=bytearray(b"TRNSRTS\x00")
    out+=struct.pack(">I",len(payload))+payload+b"TEX_SECT"+struct.pack(">I",len(textures))
    for png in textures:
        out+=struct.pack(">I",len(png))+b"\x00"+png
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(out)
    print("V4 experimental rig:",len(parts),"parts",len(parameters),
          "parameters",len(textures),"textures",len(out),"bytes at",args.output)
    print("Not yet manually rigged or browser-verified; do not enable in main UI.")

if __name__=="__main__":
    main()
