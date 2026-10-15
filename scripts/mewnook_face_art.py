"""Tilt-aware facial art for the original MewNook day-room companion.

The neutral smile is recovered from the painted illustration. Speech and
drowsy mouths use the same slanted local facial frame.
"""
from __future__ import annotations
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw

MOUTH_CENTER = (525.0, 540.0)
MOUTH_ANGLE = -29.0
MOUTH_RADIUS = (31.0, 13.0)

def _canvas_xy(x:float,y:float,w:int,h:int)->tuple[int,int]:
    return round(x*w/1086),round(y*h/1448)

def _ellipse_mask(w:int,h:int,rx:float,ry:float,feather:float)->np.ndarray:
    center=_canvas_xy(*MOUTH_CENTER,w,h)
    axes=_canvas_xy(rx,ry,w,h)
    mask=np.zeros((h,w),np.uint8)
    cv2.ellipse(mask,center,axes,MOUTH_ANGLE,0,360,255,-1,cv2.LINE_AA)
    if feather:mask=cv2.GaussianBlur(mask,(0,0),feather*w/1086)
    return mask

def _rotated_point(u:float,v:float,w:int,h:int,scale:int=1)->tuple[int,int]:
    theta=math.radians(MOUTH_ANGLE)
    x=MOUTH_CENTER[0]+u*math.cos(theta)-v*math.sin(theta)
    y=MOUTH_CENTER[1]+u*math.sin(theta)+v*math.cos(theta)
    x,y=_canvas_xy(x,y,w,h)
    return x*scale,y*scale

def _draw_open(w:int,h:int,halfwidth:float,opening:float,
               sleepy:bool=False,reference:np.ndarray|None=None)->np.ndarray:
    aa=3
    image=Image.new('RGBA',(w*aa,h*aa),(0,0,0,0))
    draw=ImageDraw.Draw(image)
    upper=[];lower=[]
    for i in range(33):
        t=i/32;u=(t*2-1)*halfwidth
        bump=math.sin(math.pi*t)**0.8
        upper.append(_rotated_point(u,-opening*.25*bump,w,h,aa))
        lower.append(_rotated_point(u,opening*.70*bump,w,h,aa))
    draw.polygon(upper+list(reversed(lower)),fill=(117,65,86,243))
    inner=[]
    for i in range(25):
        t=.10+.8*i/24;u=(t*2-1)*halfwidth
        bump=math.sin(math.pi*t)**.9
        inner.append(_rotated_point(u,opening*.36*bump,w,h,aa))
    if len(inner)>1 and not sleepy:
        draw.line(inner,fill=(211,123,145,227),width=aa*2,joint='curve')
    draw.line(upper,fill=(129,76,98,218),width=aa*2,joint='curve')
    if sleepy:
        draw.line(lower[9:24],fill=(212,127,153,180),width=aa*2,joint='curve')
    art=np.asarray(image.resize((w,h),Image.Resampling.LANCZOS)).copy()
    if reference is not None and not sleepy:
        # Retain the original author's small upward smile stroke as the
        # *upper lip* of the opening. The earlier solid ellipse looked pasted
        # on because it had no linework from the existing tilted face.
        original_mask=_ellipse_mask(w,h,*MOUTH_RADIUS,0)
        green=reference[:,:,1].astype(np.float32)
        ink=np.clip((215-green)/95,0,1)
        lip=reference.copy()
        lip[:,:,3]=np.round(reference[:,:,3].astype(np.float32)
                     *original_mask.astype(np.float32)/255*ink).astype(np.uint8)
        art=np.asarray(Image.alpha_composite(Image.fromarray(art,'RGBA'),
                           Image.fromarray(lip,'RGBA'))).copy()
    return art

def build_face_mouth_art(original:np.ndarray,base:np.ndarray)->tuple[np.ndarray,dict[str,np.ndarray],dict]:
    """Return corrected base, transparent local-space poses, and pose metadata."""
    h,w=original.shape[:2]
    removal=_ellipse_mask(w,h,MOUTH_RADIUS[0]+2,MOUTH_RADIUS[1]+3,0)
    cleaned=base.copy()
    cleaned[:,:,:3]=cv2.inpaint(base[:,:,:3],removal,8,cv2.INPAINT_TELEA)
    neutral_mask=_ellipse_mask(w,h,MOUTH_RADIUS[0],MOUTH_RADIUS[1],2.0)
    neutral=original.copy()
    neutral[:,:,3]=np.round(original[:,:,3].astype(np.float32)
                           *neutral_mask.astype(np.float32)/255).astype(np.uint8)
    art={'Neutral Smile':neutral,
         'Talking Mouth A':_draw_open(w,h,15,8,reference=original),
         'Talking Mouth B':_draw_open(w,h,17,14,reference=original),
         'Sleepy Mouth':_draw_open(w,h,11,6,True)}
    return cleaned,art,{'center':MOUTH_CENTER,'angle_deg':MOUTH_ANGLE,
           'radius':MOUTH_RADIUS,'original_neutral':True}
