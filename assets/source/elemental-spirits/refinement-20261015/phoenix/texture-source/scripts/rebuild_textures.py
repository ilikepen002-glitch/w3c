"""Convert locked image_gen PNGs into the approved BLP1 pair. No raster art is authored here.
Run with Python + Pillow + numpy. Outputs only this directory's rebuilt/ and technical/.
"""
from pathlib import Path
import struct,json,hashlib
import numpy as np
from PIL import Image
import PIL
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'rebuilt'
OUT.mkdir(parents=True,exist_ok=True)
(ROOT/'technical').mkdir(parents=True,exist_ok=True)
def blp1_write(image,path,alpha=True):
    im=Image.open(image).convert('RGBA')
    palette_image=im.convert('RGB').quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    rgb=palette_image.getpalette()[:768]
    rgb += [0]*(768-len(rgb))
    palette=b''.join(bytes((rgb[i+2],rgb[i+1],rgb[i],0)) for i in range(0,768,3))
    levels=[]
    w,h=im.size
    while True:
        mip=im.resize((w,h),Image.Resampling.LANCZOS)
        idx=mip.convert('RGB').quantize(palette=palette_image,dither=Image.Dither.NONE).tobytes()
        data=idx + (mip.getchannel('A').tobytes() if alpha else b'')
        levels.append((w,h,data,mip))
        if w==h==1: break
        w=max(1,w//2);h=max(1,h//2)
    offsets=[];sizes=[];offset=156+1024
    for w,h,data,mip in levels:
        offsets.append(offset);sizes.append(len(data));offset+=len(data)
    offsets += [0]*(16-len(offsets));sizes += [0]*(16-len(sizes))
    header=struct.pack('<4s6I16I16I',b'BLP1',1,8 if alpha else 0,*im.size,4 if alpha else 5,1,*offsets,*sizes)
    assert len(header)==156
    path.write_bytes(header+palette+b''.join(x[2] for x in levels))
    # Independent readback validates every mip, offset and independent alpha plane.
    raw=path.read_bytes();hdr=struct.unpack_from('<4s6I16I16I',raw)
    pal=np.frombuffer(raw[156:1180],np.uint8).reshape(256,4)[:,[2,1,0]]
    checks=[]
    for i,(w,h,data,original) in enumerate(levels):
        off=hdr[7+i];size=hdr[23+i]; n=w*h
        assert size==n*(2 if alpha else 1)
        index=np.frombuffer(raw[off:off+n],np.uint8).reshape(h,w)
        rgb_back=pal[index]
        a=np.frombuffer(raw[off+n:off+2*n],np.uint8).reshape(h,w) if alpha else np.full((h,w),255,np.uint8)
        expected=np.asarray(original)
        assert np.array_equal(a,expected[:,:,3])
        visible=expected[:,:,3]>128
        mae=float(np.abs(rgb_back.astype(float)-expected[:,:,:3].astype(float))[visible].mean()) if visible.any() else 0
        checks.append({'level':i,'size':[w,h],'offset':off,'bytes':size,'alphaExact':True,'visibleRgbMAE':round(mae,3)})
        if i==0:
            Image.fromarray(np.dstack([rgb_back,a]),'RGBA').save(ROOT/'technical'/(path.stem+'-blp1-roundtrip.png'))
    assert offsets[len(levels)-1]+sizes[len(levels)-1]==len(raw)
    return {'file':str(path.relative_to(OUT)),'dimensions':list(im.size),'bytes':len(raw),'format':'BLP1 palette + 8-bit alpha' if alpha else 'BLP1 palette RGB','paletteEntries':256,'mips':checks,'sha256':hashlib.sha256(raw).hexdigest()}

expected={'PhoenixBody.blp':'d5a9f8ee5bb4c666b88692e81ca0c17e33e394041771dedf136f06bcc5850c1b','PhoenixHead.blp':'3631ae3bbd1c299fea419f9468278f9ebfd0eba5bd90805262bc7eb1ea4412c0'}
items=[]
for src,base,size,alpha in [('phoenix-body-imagegen-v4.png','PhoenixBody',512,True),('phoenix-head-imagegen-v1.png','PhoenixHead',256,False)]:
    im=Image.open(ROOT/'art'/src).convert('RGBA' if alpha else 'RGB').resize((size,size),Image.Resampling.LANCZOS)
    locked=Image.open(ROOT/'art'/(base+'.png')).convert(im.mode)
    assert np.array_equal(np.asarray(im),np.asarray(locked)), 'Resized pixels differ from locked pre-quantization PNG'
    path=OUT/(base+'.png');im.save(path)
    item=blp1_write(path,OUT/(base+'.blp'),alpha)
    assert item['sha256']==expected[base+'.blp'], 'BLP output differs; check Pillow version'
    items.append(item)
report={'pass':True,'pillowVersion':PIL.__version__,'numpyVersion':np.__version__,'rasterEdits':'None: source PNG resize, palette encoding and mip generation only.','textures':items}
(ROOT/'technical/texture-rebuild-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
