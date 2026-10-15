"""Deterministic stage-only image_gen atlas conversion and TEXS path adapter.
No artist raster pixels are painted here: only RGB conversion, resizing,
palette/mipmap conversion and independent readback. Original mesh/UV/animation
chunks are preserved byte-for-byte. Paths are relative to this staged bundle.
"""
from pathlib import Path
import hashlib,json,struct,sys
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'tools'));from mdx_decode import decode,Evaluator
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encode(im):
 im=im.convert('RGB').resize((256,256),Image.Resampling.LANCZOS)
 q=im.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=q.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
 for i in range(9):
  n=max(1,256>>i);idx=im.resize((n,n),Image.Resampling.BOX).quantize(palette=q,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
 raw=b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[3*i+2],pal[3*i+1],pal[3*i],255])for i in range(256))+b''.join(blobs)
 return im,raw
def readback(b):
 assert b[:4]==b'BLP1';c,a,w,h,typ,mip=struct.unpack_from('<6I',b,4);assert(c,a,w,h)==(1,0,256,256)
 offsets=struct.unpack_from('<16I',b,28);sizes=struct.unpack_from('<16I',b,92)
 for i in range(9):assert sizes[i]==max(1,w>>i)*max(1,h>>i)and offsets[i]+sizes[i]<=len(b)
 pal=b[156:1180];idx=b[offsets[0]:offsets[0]+w*h];return Image.frombytes('RGBA',(w,h),bytes(v for n in idx for v in (pal[4*n+2],pal[4*n+1],pal[4*n],255)))
def patch_texs(raw,path):
 b=bytearray(raw);p=4;changed=[]
 while p<len(b):
  tag=b[p:p+4];n=struct.unpack_from('<I',b,p+4)[0]
  if tag==b'TEXS':
   assert n==268 and struct.unpack_from('<I',b,p+8)[0]==0
   bb=path.encode('ascii');assert len(bb)<260;b[p+12:p+272]=bb.ljust(260,b'\0');changed.append('TEXS')
  p+=8+n
 assert changed==['TEXS'];return bytes(b)
entries=[]
for folder,model,atlas,artfile in [('fox','CinderTailFox','CinderFoxAtlas','CinderFoxAtlas-imagegen-v1.png'),('salamander','MoltenHornSalamander','MoltenHornAtlas','MoltenHornAtlas-imagegen-v1.png')]:
 s=R/folder;pin=json.loads((s/'source/source-pin.json').read_text());base=s/'source'/pin['sourceModel'];assert sha(base)==pin['sourceModelSha256'];assert sha(s/'source'/pin['sourceBlp'])==pin['sourceBlpSha256']
 art=s/'art'/artfile;im,blp=encode(Image.open(art));name=atlas+'Refined.blp';texpath='Textures\\'+name
 (s/'output').mkdir(exist_ok=True);(s/'output'/name).write_bytes(blp);im.save(s/'art'/f'{atlas}-refined-256.png');readback(blp).save(s/'output'/f'{atlas}-blp-readback.png')
 target=s/'output'/f'{model}.mdx';target.write_bytes(patch_texs(base.read_bytes(),texpath));a,b=decode(base),decode(target)
 assert a['geosets']==b['geosets']and a['nodes']==b['nodes']and a['materials']==b['materials']and a['sequences']==b['sequences']
 expected=['Stand','Walk','Attack','Death','Portrait','Display Float','Display Jump','Display Spin','Display Sleep','Display Cast'];assert [x['name']for x in b['sequences']]==expected
 ev=Evaluator(b);anim=[]
 for seq in b['sequences']:
  st,en=seq['interval'];poses=[np.concatenate([x['vertices']for x in ev.sample(seq['name'],t,t-st)])for t in np.linspace(st,en,65)]
  assert all(np.isfinite(v).all()for v in poses);bb=np.concatenate(poses);motion=float(max(np.max(abs(v-poses[0]))for v in poses));assert motion>.01
  anim.append({'name':seq['name'],'samples':65,'maxCoordinateMotion':motion,'boundsMin':bb.min(0).tolist(),'boundsMax':bb.max(0).tolist(),'loopEndpointDifference':float(np.max(abs(poses[-1]-poses[0])))})
 rgba=np.array(readback(blp));rgb=np.array(im);mae=float(np.mean(np.abs(rgba[:,:,:3].astype(int)-rgb.astype(int))))
 out={'speciesId':12 if folder=='fox'else 11,'model':model,'sourceModelSha256':pin['sourceModelSha256'],'finalModel':str(target),'modelSha256':sha(target),'modelBytes':target.stat().st_size,'textureImportPath':texpath,'textureFile':str(s/'output'/name),'textureSha256':sha(s/'output'/name),'textureBytes':len(blp),'textureSize':[256,256],'mipLevels':9,'alphaBits':0,'triangles':sum(len(g['faces'])for g in b['geosets']),'bones':sum(n['kind']=='BONE'for n in b['nodes']),'changedChunks':['TEXS'],'geometryUvsSkinTracksMaterialsAllUnchanged':True,'imagegenSource':str(art),'imagegenSha256':sha(art),'prompt':str(s/'art/imagegen-prompt.txt'),'rgbMeanAbsoluteQuantizationError':mae,'animations':anim,'gameTested':False,'productionTouched':False}
 (s/'audit/asset-verification.json').write_text(json.dumps(out,indent=2));entries.append(out)
(R/'fire-texture-output-manifest.json').write_text(json.dumps(entries,indent=2));print(json.dumps([{k:v for k,v in e.items()if k!='animations'}for e in entries],indent=2))
