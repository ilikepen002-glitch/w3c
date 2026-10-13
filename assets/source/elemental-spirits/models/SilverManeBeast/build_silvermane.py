"""Original long-bodied metal-element beast. Existing MDX schema and primitives."""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['18232a','354654','576776','9ba9b0','cbd2ce','e5e1c9','768792','4c5c68','b4bdbe','bfad78','495d6b','92a6ad','d4dace','10191f','d7b55d','fbf0bc'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='Spine',parent=0,pivot=[-2,0,29]),dict(name='NarrowWolfHead',parent=1,pivot=[29,0,36]),dict(name='TailBase',parent=1,pivot=[-32,0,31]),dict(name='TailTip',parent=3,pivot=[-57,0,37]),dict(name='FrontLeft',parent=0,pivot=[20,11,26]),dict(name='FrontRight',parent=0,pivot=[20,-11,26]),dict(name='HindLeft',parent=0,pivot=[-23,10,26]),dict(name='HindRight',parent=0,pivot=[-23,-10,26]),dict(name='EarLeft',parent=2,pivot=[36,6,45]),dict(name='EarRight',parent=2,pivot=[36,-6,45])]
ellipsoid('long silver torso',(-4,0,29),(34,13,13),3,1,n=14,k=6)
ellipsoid('dark lean underside',(-1,0,23),(28,10,8),2,1,n=12,k=4)
ellipsoid('strong shoulders',(18,0,31),(13,14,15),4,1,n=12,k=5)
ellipsoid('haunch',(-25,0,29),(13,12,13),3,1,n=10,k=5)
tube('arched neck',[(22,0,31),(29,0,37),(36,0,39)],[11,10,8],4,2,n=10)
ellipsoid('slender wedge skull',(42,0,39),(13,8.5,9.5),4,2,n=12,k=5)
tube('tapered long muzzle',[(45,0,36),(53,0,34),(63,0,33)],[6.4,5.2,3.2],4,2,n=8)
ellipsoid('lower jaw',(53,0,31),(11,4.2,3.5),3,2,n=10,k=4)
ellipsoid('dark pointed nose',(64,0,33),(3.2,3.4,2.6),0,2,n=8,k=4)
for s in [-1,1]:
 ellipsoid('narrow eye socket '+str(s),(46,s*7.8,41.4),(4,1.2,1.65),0,2,n=8,k=3)
 ellipsoid('small amber iris '+str(s),(47,s*8.7,41.5),(1.65,.40,1.12),14,2,n=8,k=3)
 ellipsoid('slit pupil '+str(s),(47.4,s*9,41.5),(.4,.15,.87),13,2,n=6,k=3)
 tube('heavy slanted brow '+str(s),[(41,s*7.2,44.3),(45,s*8.2,43.5),(49,s*6.8,43.2)],[1.6,1.4,.9],2,2,n=6)
 tube('muzzle crease '+str(s),[(62,s*2.4,31.3),(54,s*4.6,30.6),(46,s*5.5,32)],[.3,.35,.25],1,2,n=5)
 # Thin blade-like ears and backward cheek tufts make a predatory, non-round face.
 leaf('silver pointed ear '+str(s),(35,s*5.8,44),(31,s*11,63),4.2,4,9 if s==1 else 10,bend=-1)
 leaf('dark ear inset '+str(s),(35.8,s*6,47),(32,s*10.2,60),2.2,2,9 if s==1 else 10,bend=-.2)
 leaf('cheek mane '+str(s),(35,s*6,37),(24,s*15,33),5,12,2,bend=2)
 leaf('shoulder silver tuft '+str(s),(18,s*11,36),(10,s*21,30),5,12,1,bend=1)
# Narrow overlapping steel plates, not an enclosing turtle shell.
for i,x in enumerate([19,7,-5,-17]):
 leaf('dorsal steel blade '+str(i),(x+5,0,40),(x-8,0,49 if i<2 else 44),7 if i<2 else 6,11,1,bend=1)
for s in [-1,1]:
 leaf('brass cheek flash '+str(s),(38,s*7,43),(31,s*10,51),2.0,9,2,bend=0)
tube('long flowing tail base',[(-30,0,31),(-43,1,33),(-56,2,39)],[7.8,9.2,8.1],3,3,n=9)
tube('silver brush tail',[(-55,2,39),(-67,3,46),(-79,4,48),(-84,4,44)],[8.4,8.2,4,.15],4,4,n=9)
leaf('tail steel tip',(-69,3,47),(-86,4,48),4.5,11,4,bend=1)
for i,(x,y) in enumerate([(20,11),(20,-11),(-23,10),(-23,-10)]):
 s=1 if y>0 else -1;fore=x>0;bi=5+i
 tube('bent long leg '+str(i),[(x,y,26),(x+(-4 if fore else 5),y+s*2,17),(x+(0 if fore else -3),y+s*3,8)],[5.1,4.2,3.4],3,bi,n=8)
 ellipsoid('long paw '+str(i),(x+3,y+s*3,5.4),(7,4.5,3.1),4,bi,n=8,k=4)
 for j in [-1,0,1]:ellipsoid('small steel claw '+str(i)+' '+str(j),(x+8,y+s*3+j*2,4.7),(2.5,.8,1.2),9,bi,n=5,k=3)
 ellipsoid('steel wrist '+str(i),(x,y+s*3,9),(4.1,4.1,2.8),10,bi,n=8,k=3)

seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.45*(1-math.cos(2*math.pi*u));sc=[1,1,1+.014*(1-math.cos(2*math.pi*u))]
    if bi==2:rot=q([0,0,1],.035*w)
    if bi==3:rot=q([0,0,1],.08*w)
    if bi==4:rot=q([0,0,1],.13*w)
    if bi in [9,10]:rot=q([1,0,0],(.05 if bi==9 else -.05)*w)
   elif name=='Walk':
    if bi==1:tr[2]=.7*(1-math.cos(4*math.pi*u));rot=q([1,0,0],.025*w)
    if bi==2:rot=q([0,1,0],.025*w)
    if bi in [3,4]:rot=q([0,0,1],(.1 if bi==3 else .16)*w)
    if bi in [5,6,7,8]:
     p=(0,.5,.5,0)[bi-5];v=math.sin(2*math.pi*(u+p));tr=[5.2*v,0,max(0,math.cos(2*math.pi*(u+p)))*3.2];rot=q([0,1,0],-.035*v)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==1:tr=[5*k,0,1.8*k]
    if bi==2:tr=[6*k,0,0];rot=q([0,1,0],.12*k)
    if bi in [5,6]:tr=[4*k,0,1.5*k]
    if bi in [3,4]:rot=q([0,0,1],-.15*k)
   else:
    e=3*u*u-2*u*u*u
    if bi==0:tr=[0,0,-3.5*e]
    if bi==1:tr=[-2*e,0,-4.5*e];rot=q([1,0,0],.08*e)
    if bi==2:rot=q([0,1,0],.38*e)
    if bi in [5,6,7,8]:sc=[1,1,1-.13*e]
    if bi in [3,4]:rot=q([0,0,1],.20*e)
    if bi in [9,10]:rot=q([0,1,0],-.3*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'silvermane-source.json').write_text(json.dumps(dict(name='SilverManeBeast_Original_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))
# Low-resolution painted fur and steel, with a warm accent rather than gold plastic.
rng=np.random.default_rng(3913);atlas=Image.new('RGB',(256,256));Y,X=np.mgrid[0:64,0:64];xx=X/63;yy=Y/63
for k,base in enumerate(colors):
 noise=Image.fromarray(rng.integers(0,255,(8,8),dtype=np.uint8)).resize((64,64),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1));grain=(np.asarray(noise).astype(float)-128)/128;light=1.12-.22*yy-.07*xx+grain*.04
 if k in [10,11]:light=.64+.35*(1-yy)+.36*np.exp(-((xx-.28)/.13)**2)+grain*.02
 if k>=13:light=np.ones((64,64))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if k in [2,3,4,5,6,8,12]:
  for y in [7,20,33,46]:
   for x in range(6+(y//13%2)*4,59,11):
    d.line([(x,y),(x-3,y+9),(x-1,y+13)],fill=tuple(int(v*.72) for v in base),width=1);d.line([(x+2,y),(x,y+8)],fill=tuple(min(255,int(v*1.12)) for v in base),width=1)
 elif k in [9,10,11]:
  d.line([(7,10),(57,10),(57,56)],fill=tuple(int(v*.47) for v in base),width=2);d.line([(8,8),(55,8),(55,54)],fill=tuple(min(255,int(v*1.27)) for v in base),width=1)
  for x,y in [(17,21),(32,38),(43,25)]:d.line([(x,y),(x+7,y+4)],fill=tuple(int(v*.58) for v in base),width=1)
 atlas.paste(tile,((k%4)*64,(k//4)*64))
atlas.save(OUT/'SilverManeAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(9):
 sz=max(1,256>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'SilverManeAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps({'triangles':sum(len(p['faces']) for p in parts),'bones':len(bones)}))
