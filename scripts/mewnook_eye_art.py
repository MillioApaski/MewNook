"""Non-symmetric, face-tilt-aware partial eyelid art for MewNook.

Build a thin eyelid confined to the iris rather than squashing a whole
skin-colored oval over the eye. Coordinates are authored independently
for the left and right eyes on the original tilted 1086 x 1448 portrait.
"""
from __future__ import annotations

import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def make_drowsy_eye_art(eye: dict, portrait: np.ndarray, dimensions: tuple[int,int]):
    """Return (part_alpha, transparent eyelash PNG array) in canvas coords.

    In particular the cover does not extend into forehead/hair and its
    leading edge is softly feathered. The darker contour follows each
    eye's actual angled pupil, not the horizontal canvas axes.
    """
    w,h=dimensions
    xscale=w/1086
    yscale=h/1448
    cx,cy=eye["cx"]*xscale,eye["cy"]*yscale
    # Iris apertures are narrower than the entire eye-white ellipse.
    rx=(39 if eye["name"]=="Left" else 42)*xscale
    ry=27*yscale
    theta=math.radians(eye["angle"])
    co,si=math.cos(theta),math.sin(theta)
    margin=max(3,round(10*xscale))
    left=max(0,int(cx-rx-ry-margin))
    right=min(w,int(cx+rx+ry+margin)+1)
    top=max(0,int(cy-rx-ry-margin))
    bottom=min(h,int(cy+rx+ry+margin)+1)
    xx,yy=np.meshgrid(np.arange(left,right,dtype=np.float32),
                      np.arange(top,bottom,dtype=np.float32))
    dx,dy=xx-cx,yy-cy
    u=dx*co+dy*si
    v=-dx*si+dy*co
    # An anti-aliased aperture and a curved lower eyelid edge, using
    # separate perspective-correct spans for near/far eyes.
    ellipse=(u/rx)**2+(v/ry)**2
    edge=(.17+.12*(u/rx)**2)*ry
    feather=max(0.8,1.6*yscale)
    aperture=np.clip((1-ellipse)*9,0,1)
    top_fade=np.clip((v+ry*.70)/(ry*.65),0,1)
    lower_cut=np.clip((edge-v)/feather,0,1)
    alpha=np.zeros((h,w),np.uint8)
    alpha[top:bottom,left:right]=np.uint8(np.round(255*aperture*top_fade*lower_cut))

    eyelash=Image.new("RGBA",(w,h),(0,0,0,0))
    stroke=ImageDraw.Draw(eyelash)
    points=[]
    # Do not connect endpoints all the way to the eye corners: retain the
    # original upper lashes and avoid a stray floating eyebrow-like bar.
    for step in range(41):
        t=.10+.80*step/40
        U=(t*2-1)*rx
        V=(.17+.12*(U/rx)**2)*ry
        points.append((round(cx+U*co-V*si),round(cy+U*si+V*co)))
    stroke.line(points,fill=(112,77,109,185),
                width=max(1,round(1.8*xscale)),joint="curve")
    eyelash=eyelash.filter(ImageFilter.GaussianBlur(max(.20,.40*xscale)))
    return alpha,np.asarray(eyelash).copy()
