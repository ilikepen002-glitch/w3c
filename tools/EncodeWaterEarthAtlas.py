"""Deterministic resize and BLP1/mipmap conversion of imagegen-authored pixels only."""
from PIL import Image
import struct
def encode(source,png,blp):
 atlas=Image.open(source).convert('RGB').resize((256,256),Image.Resampling.LANCZOS)
 atlas.save(png)
 quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT); pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
 for i in range(9):
  sz=max(1,256>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
 blp.write_bytes(b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
