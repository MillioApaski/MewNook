#!/usr/bin/env python3
"""Structural/texture validation for the *experimental* MewNook v4 INX."""
import io,json,struct,sys
from pathlib import Path
import numpy as np
from PIL import Image

path=Path(sys.argv[1] if len(sys.argv)>1 else "assets/inochi/v4/rig/MewNook-v4-prototype.inx")
raw=path.read_bytes()
assert raw[:8]==b"TRNSRTS\x00", "Bad INX header"
length=struct.unpack(">I",raw[8:12])[0]
puppet=json.loads(raw[12:12+length])
nodes=puppet["nodes"]["children"]
params={p["name"]:p for p in puppet["param"]}
for name in ("ParamEyeBlinkLeft","ParamEyeBlinkRight","ParamMouthOpen","ParamSleepy"):
    assert name in params,name
assert all(len(params["ParamEyeBlink"+s]["bindings"])==2 for s in ("Left","Right"))
assert len(params["ParamMouthOpen"]["bindings"])==3
cursor=12+length
assert raw[cursor:cursor+8]==b"TEX_SECT"
cursor+=8
count=struct.unpack(">I",raw[cursor:cursor+4])[0];cursor+=4
assert count==len(nodes)
for index in range(count):
    n=struct.unpack(">I",raw[cursor:cursor+4])[0]
    assert raw[cursor+4]==0
    pixels=np.asarray(Image.open(io.BytesIO(raw[cursor+5:cursor+5+n])).convert("RGBA")).astype(np.uint16)
    assert (pixels[:,:,:3] <= pixels[:,:,3:4]+1).all(),f"Texture {index} not premultiplied"
    cursor+=5+n
assert cursor==len(raw)
assert all(x["zsort"] <= 0 for x in nodes)
print(f"Experimental v4 INX validated: {len(nodes)} parts, {len(params)} parameters, {count} textures")
print("NOTE: file format validation is NOT a browser visual acceptance test.")
