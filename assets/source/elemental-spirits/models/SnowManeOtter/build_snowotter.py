"""Original squat, long-bodied snow-mane water otter."""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['17303f','2b4b5b','3e6575','648e9e','95b8c4','e1e8df','487687','607e8c','bfd4d5','b2c9cb','3c7385','cae4df','d7e1db','122a35','94dbce','eff5df'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='LongOtterBody',parent=0,pivot=[-2,0,21]),dict(name='RoundOtterHead',parent=1,pivot=[23,0,26]),dict(name='ThickTailBase',parent=1,pivot=[-29,0,20]),dict(name='ThickTailTip',parent=3,pivot=[-51,1,14]),dict(name='FrontLeftPaw',parent=0,pivot=[20,10,18]),dict(name='FrontRightPaw',parent=0,pivot=[20,-10,18]),dict(name='RearLeftPaw',parent=0,pivot=[-21,10,17]),dict(name='RearRightPaw',parent=0,pivot=[-21,-10,17])]
ellipsoid('long low otter torso',(-5,0,22),(31,14,11.5),3,1,n=14,k=6)
ellipsoid('pale long belly',(-1,0,17),(27,11,6),8,1,n=12,k=4)
ellipsoid('rounded muscular haunch',(-24,0,22),(14,13,10),2,1,n=10,k=4)
ellipsoid('low thick neck',(19,0,25),(12,13,11),4,1,n=10,k=4)
# Snow mane built as eight short, backward fur clumps, no horns or armor.
for i in range(8):
 a=math.pi*2*i/8;ca=math.cos(a);sa=math.sin(a)
 tube('snow mane tuft '+str(i),[(21,11*ca,24+9*sa),(13,16*ca,24+13*sa),(6,14.5*ca,24+12*sa)],[3.8,4.8,.18],5 if i%2 else 12,1,n=6)
ellipsoid('short broad otter skull',(31,0,28),(13,12,10.2),4,2,n=12,k=5)
ellipsoid('cream cheek left',(39,5,24),(7,6.5,5),5,2,n=10,k=4)
ellipsoid('cream cheek right',(39,-5,24),(7,6.5,5),5,2,n=10,k=4)
ellipsoid('low round chin',(39,0,20.3),(8,7,2.9),8,2,n=10,k=3)
ellipsoid('small otter nose',(45,0,27),(2.5,3.7,2.2),0,2,n=8,k=3)
tube('otter mouth crease',[(44,-5,22.5),(45,0,21.7),(44,5,22.5)],[.28,.35,.28],1,2,n=5)
for s in [-1,1]:
 ellipsoid('small rounded ear '+str(s),(25,s*10,35.7),(3.6,3.4,4.2),2,2,n=8,k=4)
 ellipsoid('pale ear inner '+str(s),(27,s*10.9,36.3),(1.5,1.6,2.4),8,2,n=7,k=3)
 ellipsoid('small dark eye socket '+str(s),(36,s*10.5,31.3),(2.6,1.7,2.1),0,2,n=8,k=3)
 ellipsoid('muted teal eye '+str(s),(37,s*11.2,31.9),(1.1,.6,1.1),14,2,n=7,k=3)
 ellipsoid('dark tiny pupil '+str(s),(37.3,s*11.6,31.9),(.48,.22,.8),13,2,n=6,k=3)
 tube('lowered snowy brow '+str(s),[(31,s*10,34),(35,s*11,34.4),(39,s*9.2,33.5)],[1.7,1.4,.65],5,2,n=6)
 for j in [-1,1]:tube('cream otter whisker '+str(s)+' '+str(j),[(41,s*7,25),(40-j*2,s*14,26+j),(36-j*3,s*20,28+j*2)],[.45,.32,.07],11,2,n=5)
# Thick tapered muscular tail, very different from the water wyrm's finned tail.
tube('muscular otter tail',[(-30,0,22),(-42,1,18),(-53,2,14)],[9,8.1,5.8],2,3,n=10)
tube('thick taper tail tip',[(-52,2,14),(-63,4,11),(-75,5,9),(-81,4,10)],[6,4.2,2,.2],3,4,n=9)
for i,(x,y) in enumerate([(20,10),(20,-10),(-21,10),(-21,-10)]):
 s=1 if y>0 else -1;bi=5+i;fore=x>0
 tube('short sturdy leg '+str(i),[(x,y,18),(x-2,y+s*4,12),(x+1,y+s*6,7)],[5.9,5.4,4.2],2,bi,n=8)
 ellipsoid('broad webbed paw '+str(i),(x+5,y+s*6,5.8),(8,5.9,3.2),4,bi,n=9,k=4)
 for j in [-1,0,1]:
  ellipsoid('webbed toe '+str(i)+' '+str(j),(x+11,y+s*6+j*2.3,5.2),(2.6,1.2,1.5),8,bi,n=5,k=3)
seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,lo in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.5*(1-math.cos(2*math.pi*u));sc=[1,1,1+.018*(1-math.cos(2*math.pi*u))]
    if bi==2:rot=q([0,0,1],.045*w)
    if bi in [3,4]:rot=q([0,0,1],(.07 if bi==3 else .1)*w)
   elif name=='Walk':
    if bi==1:tr[2]=.8*(1-math.cos(4*math.pi*u));rot=q([1,0,0],.035*w)
    if bi==2:rot=q([0,1,0],.04*w)
    if bi in [3,4]:rot=q([0,0,1],(.11 if bi==3 else .16)*w)
    if bi in [5,6,7,8]:
     ph=(0,.5,.5,0)[bi-5];v=math.sin(2*math.pi*(u+ph));tr=[4*v,0,max(0,math.cos(2*math.pi*(u+ph)))*3.2];rot=q([0,1,0],-.04*v)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==1:tr=[4.5*k,0,1.6*k]
    if bi==2:tr=[4*k,0,1*k];rot=q([0,1,0],.13*k)
    if bi in [5,6]:tr=[4*k,0,2.5*k]
    if bi in [3,4]:rot=q([0,0,1],-.16*k)
   else:
    e=3*u*u-2*u*u*u
    if bi==0:tr[2]=-1.8*e
    if bi==1:tr=[-2*e,0,-3.2*e]
    if bi==2:rot=q([0,1,0],.26*e)
    if bi in [5,6,7,8]:sc=[1,1,1-.12*e]
    if bi in [3,4]:rot=q([0,0,1],.18*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'snowotter-source.json').write_text(json.dumps(dict(name='SnowManeOtter_Original_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))
rng=np.random.default_rng(9518);atlas=Image.new('RGB',(256,256));Y,X=np.mgrid[0:64,0:64];xx=X/63;yy=Y/63
for k,base in enumerate(colors):
 noise=Image.fromarray(rng.integers(0,255,(8,8),dtype=np.uint8)).resize((64,64),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1));grain=(np.asarray(noise).astype(float)-128)/128;light=1.13-.22*yy-.07*xx+grain*.045
 if k>=13:light=np.ones((64,64))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if k in [2,3,4,5,8,11,12]:
  for y in [6,18,30,42,54]:
   for x in range(5+(y//12%2)*5,61,12):
    d.line([(x,y),(x-2,y+6),(x,y+9)],fill=tuple(int(v*.77) for v in base),width=1);d.line([(x+2,y),(x+1,y+5)],fill=tuple(min(255,int(v*1.16)) for v in base),width=1)
 atlas.paste(tile,((k%4)*64,(k//4)*64))
atlas.save(OUT/'SnowOtterAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(9):
 sz=max(1,256>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'SnowOtterAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps({'triangles':sum(len(p['faces']) for p in parts),'bones':len(bones)}))
