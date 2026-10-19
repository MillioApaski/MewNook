"""Small validated OpenRaster helpers for original-art source checkpoints."""
from pathlib import Path
import io,os,tempfile,zipfile,xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

def load_group(path,shape):
    layers=[]
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        group=ET.fromstring(archive.read('stack.xml')).find('stack').find('stack')
        for node in group:
            with Image.open(io.BytesIO(archive.read(node.get('src')))) as image:
                data=np.array(image.convert('RGBA'))
            full=np.zeros(shape,np.uint8);x,y=int(node.get('x','0')),int(node.get('y','0'))
            full[y:y+data.shape[0],x:x+data.shape[1]]=data
            layers.append((node.get('name'),full))
    return layers

def composite(layers,shape):
    result=Image.new('RGBA',(shape[1],shape[0]))
    for name,data in reversed(layers):result.alpha_composite(Image.fromarray(data))
    return np.array(result)

def png_bytes(image):
    buf=io.BytesIO();image.save(buf,format='PNG');data=buf.getvalue()
    with Image.open(io.BytesIO(data)) as test:test.load()
    return data

def export_ora(path,source,layers,working_name):
    path=Path(path);height,width=source.shape[:2]
    root=ET.Element('image',{'w':str(width),'h':str(height),'version':'0.0.3','name':working_name})
    stack=ET.SubElement(root,'stack');group=ET.SubElement(stack,'stack',{'name':working_name,'visibility':'hidden','opacity':'1','composite-op':'svg:src-over','isolation':'isolate'})
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
        for i,(name,array) in enumerate(layers):
            image=Image.fromarray(array);box=image.getbbox()
            if box is None:continue
            file='data/layer-'+str(i)+'.png';archive.writestr(file,png_bytes(image.crop(box)))
            ET.SubElement(group,'layer',{'name':name,'src':file,'x':str(box[0]),'y':str(box[1]),'opacity':'1','visibility':'visible','composite-op':'svg:src-over'})
        archive.writestr('data/reference.png',png_bytes(Image.fromarray(source)))
        ET.SubElement(stack,'layer',{'name':'Original reference','src':'data/reference.png','x':'0','y':'0','opacity':'1','visibility':'visible','composite-op':'svg:src-over'})
        archive.writestr('stack.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True));archive.writestr('mergedimage.png',png_bytes(Image.fromarray(source)))
    data=payload.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        restored=[]
        for node in ET.fromstring(archive.read('stack.xml')).find('stack').find('stack'):
            im=np.array(Image.open(io.BytesIO(archive.read(node.get('src')))).convert('RGBA'));full=np.zeros_like(source);x,y=int(node.get('x')),int(node.get('y'));full[y:y+im.shape[0],x:x+im.shape[1]]=im;restored.append((node.get('name'),full))
        expected=composite(layers,source.shape);actual=composite(restored,source.shape);visible=expected[:,:,3]>0;assert np.array_equal(expected[visible],actual[visible])
        assert np.array_equal(np.array(Image.open(io.BytesIO(archive.read('mergedimage.png'))).convert('RGBA')),source)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        assert Path(tmp).read_bytes()==data
        os.replace(tmp,path)
    finally:
        if Path(tmp).exists():Path(tmp).unlink()
