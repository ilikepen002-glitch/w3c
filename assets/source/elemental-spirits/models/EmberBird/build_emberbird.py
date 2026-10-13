"""Original pointed-beak, two-wing fire spirit. No Phoenix asset is reused."""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['321d22','593030','962c28','c8482b','e37732','f0c377','833a2b','3c3030','cfa255','e8a548','9b3027','d15d2c','e7b357','1a171b','f4d054','ffe5a8'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='BirdBody',parent=0,pivot=[0,0,58]),dict(name='SharpBirdHead',parent=1,pivot=[10,0,75]),dict(name='WingLeft',parent=1,pivot=[-3,8,63]),dict(name='WingRight',parent=1,pivot=[-3,-8,63]),dict(name='TailBase',parent=1,pivot=[-12,0,49]),dict(name='TailTip',parent=5,pivot=[-43,0,30]),dict(name='FootLeft',parent=1,pivot=[4,5,44]),dict(name='FootRight',parent=1,pivot=[4,-5,44]),dict(name='FlameCrest',parent=2,pivot=[5,0,82])]
ellipsoid('tapered red bird torso',(-2,0,58),(16,10.5,18),3,1,n=12,k=6)
ellipsoid('gold breast',(9,0,59),(7.8,8.8,13),4,1,n=10,k=5)
tube('arched bird neck',[(5,0,66),(10,0,73),(13,0,76)],[7.2,6,5],3,2,n=9)
ellipsoid('small angular bird head',(15,0,78),(8.8,6.5,8),3,2,n=10,k=5)
# A genuine hooked wedge beak, not a rounded mammal muzzle.
v=[(19,-4,77),(19,4,77),(20,-3,73),(20,3,73),(29,-1.5,75),(29,1.5,75),(32,0,71),(28,0,70)]
f=[(0,1,5),(0,5,4),(0,4,2),(1,3,5),(2,4,6),(3,6,5),(2,6,7),(2,7,3),(3,7,6),(4,5,6),(0,2,3),(0,3,1)]
f=[(a,c,b) for a,b,c in f] # Correct outward winding; same beak geometry.
mesh('hooked golden beak',v,f,9,2,False,[9,12,9,9,8,8,7,7,7,12,9,9])
for s in [-1,1]:
 ellipsoid('thin eye mask '+str(s),(18,s*5.8,80.2),(3.4,1.1,1.8),0,2,n=8,k=3)
 ellipsoid('small flame iris '+str(s),(19,s*6.5,80.3),(1.5,.4,1.2),14,2,n=8,k=3)
 ellipsoid('black bird pupil '+str(s),(19.2,s*6.8,80.3),(.6,.14,.95),13,2,n=6,k=3)
 tube('sharp eyebrow '+str(s),[(14,s*5.7,83),(18,s*6.4,82.4),(21,s*4.8,82)],[1.2,1.1,.4],1,2,n=6)
 leaf('back cheek plume '+str(s),(10,s*4,76),(-3,s*12,73),4.2,12,2,bend=.2,normal_hint=(1,0,0))
 # Jointed spar supports a broad fan of narrow feathers on each of exactly two wings.
 bi=3 if s==1 else 4
 tube('wing spar '+str(s),[(-3,s*8,63),(-5,s*24,68),(-10,s*43,75),(-14,s*53,78)],[5,4,2.5,.35],3,bi,n=8)
 for i in range(8):
  y=s*(12+i*5.6);z=63+i*1.8;x=-3-i*1.0
  leaf('primary feather '+str(s)+' '+str(i),(x,y,z),(-28-i*1.6,s*(17+i*5.8),45+i*4.1),4.1,10 if i%3==0 else 11,bi,bend=1.3,normal_hint=(0,0,1))
 # Pale leading shoulder feather creates a clear wing edge.
 leaf('gold shoulder feather '+str(s),(-2,s*11,65),(-10,s*36,71),5.5,12,bi,bend=1,normal_hint=(0,0,1))
 # Curved talons, visibly avian rather than paws.
 fi=7 if s==1 else 8
 tube('bird leg '+str(s),[(4,s*5,45),(1,s*6,38),(8,s*6,33)],[2.6,2.,1.6],8,fi,n=7)
 for j in [-1,0,1]:tube('curved talon '+str(s)+' '+str(j),[(8,s*6,33),(14,s*6+j*2.5,32),(16,s*6+j*2.8,29)],[1.1,.85,.15],7,fi,n=6)
# A backward flame crown and three long streaming tail feathers.
for i,(s,h) in enumerate([(-1,16),(0,24),(1,18)]):
 leaf('flame crest '+str(i),(6,s*2,82),(-10-i*2,s*5,82+h),3.5,12 if s==0 else 11,9,bend=2,normal_hint=(0,1,0) if s==0 else (1,0,0))
tube('tapered tail root',[(-11,0,49),(-23,0,43),(-37,0,34)],[7,6.3,3.8],2,5,n=9)
for i,s in enumerate([-1,0,1]):
 leaf('long ember tail '+str(i),(-24,s*3,42),(-76+(5 if s else 0),s*11,16+(7 if s else 0)),5.5 if s else 6.5,11 if s else 12,6,bend=3,normal_hint=(0,0,1))

seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,lo in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);flap=math.sin(4*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait','Walk']:
    move=name=='Walk'
    if bi==0:tr[2]=2*(1-math.cos(2*math.pi*u))
    if bi==1:rot=q([0,1,0],-.10 if move else .025*w)
    if bi==2:rot=q([0,1,0],.045*w)
    if bi in [3,4]:rot=q([1,0,0],(1 if bi==3 else -1)*((.40 if move else .26)*flap+.10))
    if bi in [5,6]:rot=q([0,1,0],(.12 if bi==6 else .07)*w)
    if bi in [7,8]:rot=q([0,1,0],.14*w+(.18 if move else 0))
    if bi==9:rot=q([0,1,0],.08*w)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==0:tr=[8*k,0,1.5*k]
    if bi==1:rot=q([0,1,0],.15*k)
    if bi==2:rot=q([0,1,0],.35*k)
    if bi in [3,4]:rot=q([1,0,0],(1 if bi==3 else -1)*.48*k)
    if bi in [7,8]:rot=q([0,1,0],-.4*k)
   else:
    e=3*u*u-2*u*u*u
    if bi==0:sc=[1-.20*e]*3;tr[2]=-8*e
    if bi in [3,4]:rot=q([1,0,0],(1 if bi==3 else -1)*(-.95*e))
    if bi==2:rot=q([0,1,0],.48*e)
    if bi in [5,6]:rot=q([0,1,0],.22*e)
    if bi in [7,8]:rot=q([0,1,0],.35*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'emberbird-source.json').write_text(json.dumps(dict(name='EmberBird_Original_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))
rng=np.random.default_rng(1713);atlas=Image.new('RGB',(256,256));Y,X=np.mgrid[0:64,0:64];xx=X/63;yy=Y/63
for k,base in enumerate(colors):
 noise=Image.fromarray(rng.integers(0,255,(8,8),dtype=np.uint8)).resize((64,64),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1));grain=(np.asarray(noise).astype(float)-128)/128;light=1.13-.25*yy-.1*xx+grain*.045
 if k in [10,11,12]:light=.57+.72*(1-yy)+.15*np.exp(-((xx-.5)/.11)**2)+grain*.03
 if k>=13:light=np.ones((64,64))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if k in [2,3,4,5,6]:
  for y in [8,22,36,50]:
   for x in range(2+(y//14%2)*7,64,14):d.line([(x,y),(x+7,y+10),(x+14,y)],fill=tuple(int(v*.62) for v in base),width=1);d.line([(x+1,y),(x+7,y+8)],fill=tuple(min(255,int(v*1.14)) for v in base),width=1)
 elif k in [10,11,12]:
  d.line([(32,4),(32,60)],fill=tuple(min(255,int(v*1.35)) for v in base),width=2)
  for y in [13,25,37,49]:
   for s in [-1,1]:d.line([(32,y+5),(32+s*22,y-6)],fill=tuple(int(v*.48) for v in base),width=1);d.line([(32,y+3),(32+s*20,y-7)],fill=tuple(min(255,int(v*1.21)) for v in base),width=1)
 elif k in [8,9]:d.line([(14,6),(11,30),(16,58)],fill=tuple(min(255,int(v*1.3)) for v in base),width=2)
 atlas.paste(tile,((k%4)*64,(k//4)*64))
atlas.save(OUT/'EmberBirdAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(9):
 sz=max(1,256>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'EmberBirdAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps({'triangles':sum(len(p['faces']) for p in parts),'bones':len(bones)}))
