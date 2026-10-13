"""Original low-slung salamander, curved lava horns, splayed toes and heavy tail."""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['201b1c','3b292a','654036','a85532','d1783f','e29b50','704639','482e2a','af693d','b63820','5c3730','e5752b','f0b356','130f13','f4ba3c','ffdf91'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='LowSpine',parent=0,pivot=[-3,0,21]),dict(name='BroadHead',parent=1,pivot=[27,0,23]),dict(name='TailBase',parent=1,pivot=[-31,0,20]),dict(name='TailTip',parent=3,pivot=[-58,3,16]),dict(name='FrontLeft',parent=0,pivot=[19,12,19]),dict(name='FrontRight',parent=0,pivot=[19,-12,19]),dict(name='HindLeft',parent=0,pivot=[-22,13,18]),dict(name='HindRight',parent=0,pivot=[-22,-13,18])]
ellipsoid('low flattened obsidian trunk',(-4,0,20),(35,20,12),2,1,n=14,k=5)
ellipsoid('warm low underside',(-1,0,14),(29,16,6),4,1,n=12,k=4)
ellipsoid('broad neck',(27,0,21),(16,17,10),2,2,n=12,k=4)
ellipsoid('wide blunt reptile skull',(42,0,22),(18,18,10),2,2,n=12,k=5)
ellipsoid('wide wedge jaw',(48,0,17),(15,15,5),3,2,n=10,k=4)
ellipsoid('blunt snout cap',(56,0,22),(7,12,6),1,2,n=10,k=4)
for s in [-1,1]:
 ellipsoid('small recessed socket '+str(s),(43,s*15.4,26),(4.5,1.6,2.2),0,2,n=8,k=3)
 ellipsoid('molten slit eye '+str(s),(44,s*16.7,26),(2.3,.55,1.25),14,2,n=8,k=3)
 ellipsoid('vertical pupil '+str(s),(44.6,s*17.1,26),(.5,.15,1),13,2,n=6,k=3)
 tube('thick reptile brow '+str(s),[(37,s*14,29),(42,s*16,29.2),(47,s*14,28.6)],[2.7,2.8,1.8],1,2,n=6)
 tube('long jaw seam '+str(s),[(59,s*9,18),(53,s*13,17),(39,s*15,17.5)],[.5,.55,.3],0,2,n=5)
 ellipsoid('nostril '+str(s),(59,s*6.2,25),(1.7,1.1,.55),0,2,n=6,k=3)
 # Horns curve backwards and upwards, stone bases become hot ember tips.
 tube('curved volcanic horn '+str(s),[(31,s*12,29),(27,s*16,38),(19,s*19,43),(12,s*18,44)],[5.5,4.5,2.8,.25],1,2,n=8)
 tube('ember horn crest '+str(s),[(23,s*17.5,41),(17,s*19,43.5),(11,s*18,44.5)],[2.8,1.8,.15],11,2,n=7)
 for x in [-19,-4,11]:
  # Small angular heat vents along flanks, not a dome shell.
  leaf('volcanic side vent '+str(s)+' '+str(x),(x+4,s*15,26),(x-7,s*21,30),3.3,10,1,bend=.6,normal_hint=(0,0,1))
for i,x in enumerate([15,1,-13,-27]):
 leaf('low volcanic dorsal spike '+str(i),(x+4,0,30),(x-8,0,42-1.5*i),4.6,9,1,bend=1,normal_hint=(0,1,0))
 tube('molten dorsal fissure '+str(i),[(x+2,-.7,31),(x-2,-.7,35),(x-7,-.7,39-1.5*i)],[.6,.7,.25],11,1,n=5)
tube('heavy dragging tail',[(-29,0,20),(-44,1,17),(-59,3,15)],[12,10,7.5],2,3,n=10)
tube('long low curving tail tip',[(-57,3,15),(-72,8,12),(-82,16,10),(-88,25,11)],[7.9,5.5,3,.25],2,4,n=10)
tube('ember tail ridge',[(-60,3,21),(-73,8,17),(-82,16,13),(-88,25,11.2)],[1.5,1.4,1,.15],11,4,n=6)
for i,(x,y) in enumerate([(19,12),(19,-12),(-22,13),(-22,-13)]):
 s=1 if y>0 else -1;bi=5+i;front=x>0
 tube('splayed bent limb '+str(i),[(x,y,19),(x+(-5 if front else 6),s*26,12),(x+(3 if front else -3),s*31,6.8)],[5.8,4.8,3.1],2,bi,n=8)
 ellipsoid('flat reptile foot '+str(i),(x+5,s*32,5.8),(7,5,2.5),3,bi,n=8,k=3)
 for j in [-1,0,1]:
  tube('spread hooked digit '+str(i)+' '+str(j),[(x+7,s*32+j*3,6),(x+13,s*32+j*4,4.5),(x+15,s*32+j*4,4.9)],[1.35,1,.12],5,bi,n=5)

seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.30*(1-math.cos(2*math.pi*u));sc=[1,1+.013*(1-math.cos(2*math.pi*u)),1]
    if bi==2:rot=q([0,0,1],.032*w)
    if bi in [3,4]:rot=q([0,0,1],(.055 if bi==3 else .08)*w)
   elif name=='Walk':
    if bi==1:tr[2]=.4*(1-math.cos(4*math.pi*u));rot=q([0,0,1],.045*w)
    if bi==2:rot=q([0,0,1],-.04*w)
    if bi in [3,4]:rot=q([0,0,1],(.12 if bi==3 else .18)*w)
    if bi in [5,6,7,8]:
     p=(0,.5,.5,0)[bi-5];v=math.sin(2*math.pi*(u+p));tr=[4*v,0,max(0,math.cos(2*math.pi*(u+p)))*2.7];rot=q([0,0,1],(.045 if bi in [5,7] else -.045)*v)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==1:tr=[4*k,0,1.2*k]
    if bi==2:tr=[4*k,0,1*k];rot=q([0,1,0],-.12*k)
    if bi in [5,6]:tr=[4*k,0,1.5*k]
    if bi in [3,4]:rot=q([0,0,1],-.12*k)
   else:
    e=3*u*u-2*u*u*u
    if bi==0:tr=[0,0,-2.3*e]
    if bi==1:tr=[-1*e,0,-3*e]
    if bi==2:rot=q([0,1,0],.13*e)
    if bi in [5,6,7,8]:sc=[1,1,1-.07*e]
    if bi in [3,4]:rot=q([0,0,1],.14*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'fire_salamander-source.json').write_text(json.dumps(dict(name='MoltenHornSalamander_Original_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))
# Painted dark lava stone with cracks confined to the actual UV atlas tiles.
rng=np.random.default_rng(7921);atlas=Image.new('RGB',(256,256));Y,X=np.mgrid[0:64,0:64];xx=X/63;yy=Y/63
for k,base in enumerate(colors):
 noise=Image.fromarray(rng.integers(0,255,(8,8),dtype=np.uint8)).resize((64,64),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1));grain=(np.asarray(noise).astype(float)-128)/128;light=1.19-.36*yy-.09*xx+grain*.07
 if k>=13:light=np.ones((64,64))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if k in [1,2,6,7,10]:
  for points in [[(7,10),(22,15),(28,30),(46,36),(54,52)],[(8,45),(24,34),(28,30)],[(46,36),(51,17)]]:
   d.line(points,fill=(31,20,21),width=4);d.line([(x+1,y-1) for x,y in points],fill=(175,76,34),width=1)
  for x,y in [(16,23),(39,13),(16,53)]:d.line([(x,y),(x+10,y+4)],fill=tuple(min(255,int(v*1.30)) for v in base),width=2)
 elif k in [3,4,5,8]:
  for y in range(10,60,12):
   for x in range(5+(y//12%2)*6,61,13):d.arc((x,y,x+12,y+10),0,180,fill=tuple(int(v*.62) for v in base),width=1)
 elif k in [9,11,12]:
  for x in [13,30,48]:d.line([(x,59),(x-3,43),(x+2,30),(x-2,8)],fill=(247,158,55),width=2)
 atlas.paste(tile,((k%4)*64,(k//4)*64))
atlas.save(OUT/'MoltenHornAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(9):
 sz=max(1,256>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'MoltenHornAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps({'triangles':sum(len(p['faces']) for p in parts),'bones':len(bones)}))
