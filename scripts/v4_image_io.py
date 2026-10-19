"""Validate complete PNG bytes before atomically publishing source-art artifacts."""
from pathlib import Path
import io,os,tempfile
from PIL import Image
_original_save=Image.Image.save

def atomic_png(image,path,**params):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    buffer=io.BytesIO();_original_save(image,buffer,format='PNG',**params);payload=buffer.getvalue()
    with Image.open(io.BytesIO(payload)) as check:check.load()
    descriptor,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.building',dir=path.parent)
    try:
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(payload);stream.flush();os.fsync(stream.fileno())
        written=Path(tmp).read_bytes()
        if written!=payload:raise OSError('Incomplete PNG write: '+str(path))
        with Image.open(io.BytesIO(written)) as check:check.load()
        os.replace(tmp,path)
    finally:
        if Path(tmp).exists():Path(tmp).unlink()

def install_atomic_png_saves():
    def save(image,fp,format=None,**params):
        if isinstance(fp,(str,os.PathLike)) and (format=='PNG' or Path(fp).suffix.lower()=='.png'):
            return atomic_png(image,fp,**params)
        return _original_save(image,fp,format=format,**params)
    Image.Image.save=save
