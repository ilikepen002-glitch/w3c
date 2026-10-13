"""Original compact three-tailed fire fox; long flame fans define its silhouette."""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['351e1c','673121','a94c25','d97933','edaa51','edcf85','8d4229','713326','bc6130','ed8c32','6b3524','efa14a','f1d396','1e1719','f9c651','fff0b5'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='CompactSpine',parent=0,pivot=[0,0,24]),dict(name='FoxHead',parent=1,pivot=[20,0,30]),dict(name='LeftTail',parent=1,pivot=[-19,5,25]),dict(name='LeftTailTip',parent=3,pivot=[-40,22,39]),dict(name='HighTail',parent=1,pivot=[-21,0,26]),dict(name='HighTailTip',parent=5,pivot=[-45,0,51]),dict(name='RightTail',parent=1,pivot=[-19,-5,25]),dict(name='RightTailTip',parent=7,pivot=[-40,-22,39]),dict(name='FrontLeft',parent=0,pivot=[14,8,22]),dict(name='FrontRight',parent=0,pivot=[14,-8,22]),dict(name='HindLeft',parent=0,pivot=[-14,8,22]),dict(name='HindRight',parent=0,pivot=[-14,-8,22])]
ellipsoid('compact russet body',(-2,0,25),(24,11,12),2,1,n=12,k=5)
ellipsoid('warm chest',(17,0,29),(11,12,15),4,1,n=10,k=5)
ellipsoid('round haunch',(-17,0,24),(12,11,12),2,1,n=10,k=4)
leaf('long pale chest bib',(25,0,31),(17,0,14),7,5,1,bend=1,normal_hint=(1,0,0))
ellipsoid('small triangular fox skull',(29,0,35),(12,8,9),3,2,n=10,k=5)
tube('short fine muzzle',[(33,0,31),(40,0,30),(46,0,29.5)],[5.6,4.2,2.4],5,2,n=7)
ellipsoid('small black nose',(47,0,29.8),(2.5,2.7,2),0,2,n=8,k=3)
ellipsoid('pale pointed chin',(38,0,27.5),(9,3.7,2.5),5,2,n=8,k=3)
for s in [-1,1]:
 ellipsoid('narrow dark eyes '+str(s),(32,s*7.2,36),(3.4,1.05,1.5),0,2,n=8,k=3)
 ellipsoid('gold slit iris '+str(s),(33,s*8,36),(1.4,.4,1.05),14,2,n=8,k=3)
 ellipsoid('small pupil '+str(s),(33.4,s*8.3,36),(.35,.13,.85),13,2,n=6,k=3)
 tube('arched eye line '+str(s),[(28,s*7,38.5),(32,s*8,38),(35,s*6.5,37)],[1.2,1.3,.7],1,2,n=5)
 leaf('large high fox ear '+str(s),(26,s*5,41),(22,s*13,61),5.7,3,2,bend=-1,normal_hint=(1,0,0))
 leaf('ear charred inset '+str(s),(26.8,s*6.2,45),(23,s*11.6,57),2.6,1,2,bend=0,normal_hint=(1,0,0))
 leaf('pointed white cheek '+str(s),(29,s*6,31),(18,s*15,32),4.8,5,2,bend=1,normal_hint=(1,0,0))
 leaf('cheek flame tuft '+str(s),(24,s*8,37),(14,s*16,43),3.8,3,2,bend=1,normal_hint=(1,0,0))
# Three volumetric plume tails, separately rigged in two sections each.
for base,tip,s in [(3,4,1),(5,6,0),(7,8,-1)]:
 if s:
  cs=[(-19,s*5,25),(-30,s*15,30),(-42,s*25,39)];end=[(-41,s*24,38),(-54,s*38,44),(-64,s*47,43),(-69,s*50,38)]
 else:
  cs=[(-21,0,26),(-34,0,38),(-46,0,51)];end=[(-45,0,50),(-58,0,66),(-70,0,71),(-78,0,65)]
 tube('russet flame tail base '+str(s),cs,[6.7,10.2,11.4],2,base,n=9)
 tube('wide amber flame tail '+str(s),end,[11.5,13.5,8,.25],3,tip,n=10)
 # Pale tip and dark grooves are actual geometry/paint, no particle dependency.
 e=np.array(end[-1],float);m=np.array(end[-2],float);v=m+(e-m)*.35
 tube('golden flame tail tip '+str(s),[tuple(v),tuple(e)],[6,.15],12,tip,n=8)
 for dy in [-1,1]:
  a=np.array(end[1],float)+[1,dy*7,1];z=np.array(end[2],float)+[-4,dy*5,4]
  leaf('flame split tuft '+str(s)+' '+str(dy),tuple(a),tuple(z),3.0,4,tip,bend=1,normal_hint=(0,1,0))
for i,(x,y) in enumerate([(14,8),(14,-8),(-14,8),(-14,-8)]):
 s=1 if y>0 else -1;fore=x>0;bi=9+i
 tube('short bent limb '+str(i),[(x,y,22),(x+(-3 if fore else 5),y+s,14),(x+(1 if fore else -1),y+s*2,7)],[4,3.1,2.3],2,bi,n=7)
 ellipsoid('charred sock paw '+str(i),(x+3,y+s*2,5.4),(5.5,3.5,2.5),1,bi,n=8,k=3)
 tube('small paw split '+str(i),[(x+6,y+s*2,6.5),(x+7,y+s*2,4.8)],[.25,.23],0,bi,n=5)
seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.45*(1-math.cos(2*math.pi*u))
    if bi==2:rot=q([0,0,1],.04*w)
    if bi in [3,5,7]:rot=q([0,0,1],.045*math.sin(2*math.pi*u))
    if bi in [4,6,8]:rot=q([0,1,0],.055*w)
   elif name=='Walk':
    if bi==1:tr[2]=1*(1-math.cos(4*math.pi*u));rot=q([1,0,0],.025*w)
    if bi==2:rot=q([0,1,0],.04*w)
    if bi in [3,5,7]:rot=q([0,0,1],.08*w)
    if bi in [4,6,8]:rot=q([0,1,0],.10*w)
    if bi in [9,10,11,12]:
     p=(0,.5,.5,0)[bi-9];v=math.sin(2*math.pi*(u+p));tr=[4.4*v,0,max(0,math.cos(2*math.pi*(u+p)))*3];rot=q([0,1,0],-.035*v)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==1:tr=[4*k,0,3*k]
    if bi==2:tr=[4*k,0,0];rot=q([0,1,0],.1*k)
    if bi in [9,10]:tr=[4*k,0,2*k]
    if bi in [3,5,7]:rot=q([0,1,0],-.15*k)
   else:
    e=3*u*u-2*u*u*u
    if bi==0:tr=[0,0,-2.2*e]
    if bi==1:tr=[-1*e,0,-3*e]
    if bi==2:rot=q([0,1,0],.27*e)
    if bi in [9,10,11,12]:sc=[1,1,1-.1*e]
    if bi in [3,5,7]:rot=q([0,1,0],-.22*e)
    if bi in [4,6,8]:rot=q([0,1,0],-.1*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'fire_fox-source.json').write_text(json.dumps(dict(name='CinderTailFox_Original_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))
# Warm directional fur strokes and charcoal paws in an original 256 atlas.
rng=np.random.default_rng(9511);atlas=Image.new('RGB',(256,256));Y,X=np.mgrid[0:64,0:64];xx=X/63;yy=Y/63
for k,base in enumerate(colors):
 noise=Image.fromarray(rng.integers(0,255,(8,8),dtype=np.uint8)).resize((64,64),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1));grain=(np.asarray(noise).astype(float)-128)/128;light=1.16-.30*yy-.06*xx+grain*.04
 if k>=13:light=np.ones((64,64))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if 1<=k<=12:
  for y in [6,20,34,48]:
   for x in range(6+(y//14%2)*4,59,11):
    d.line([(x,y),(x-3,y+7),(x-1,y+13)],fill=tuple(int(v*.67) for v in base),width=1);d.line([(x+2,y),(x,y+8)],fill=tuple(min(255,int(v*1.16)) for v in base),width=1)
 atlas.paste(tile,((k%4)*64,(k//4)*64))
atlas.save(OUT/'CinderFoxAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(9):
 sz=max(1,256>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'CinderFoxAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps({'triangles':sum(len(p['faces']) for p in parts),'bones':len(bones)}))
