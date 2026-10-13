"""Original wide diamond-winged frost manta. Classic SD fin skinning."""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['153243','244e66','346b88','4e8bad','72b9ce','d7e9e7','27465e','72a2b4','aadbdc','9bbbc1','35789c','b9e1e1','729fac','102737','82f2e9','eff9ed'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='MantaBody',parent=0,pivot=[0,0,34]),dict(name='FinLeft',parent=1,pivot=[0,9,33]),dict(name='FinLeftTip',parent=2,pivot=[-5,34,31]),dict(name='FinRight',parent=1,pivot=[0,-9,33]),dict(name='FinRightTip',parent=4,pivot=[-5,-34,31]),dict(name='TailBase',parent=1,pivot=[-22,0,32]),dict(name='TailWhip',parent=6,pivot=[-49,0,30]),dict(name='MantaHead',parent=1,pivot=[18,0,35])]
ellipsoid('flattened manta body',(-1,0,34),(30,15,6.8),3,1,n=14,k=5)
ellipsoid('pale flat belly',(-1,0,30),(27,13,4.5),5,1,n=12,k=4)
# Closed broad diamond fins, with a ridge, painted edge and adjacent SD bone groups.
for s,root,tip in [(1,2,3),(-1,4,5)]:
 ys=[8,20,35,49,61];centers=[1,-1,-7,-16,-26];halves=[24,28,23,12,.35];zs=[34,34,33,36,40];xs=[-1,-.68,0,.68,1];v=[];uv=[];vb=[]
 for lower in [False,True]:
  for j,(y,c,h,z) in enumerate(zip(ys,centers,halves,zs)):
   for a in xs:
    v.append([c+h*a,s*y,z+(-1.2 if lower else 1.2+3*(1-a*a)*(1-j/5))]);uv.append([(a+1)/2,j/4]);vb.append([1,root] if j==0 else [root] if j==1 else [root,tip] if j==2 else [tip])
 f=[];fc=[]
 for lower in [False,True]:
  o=25 if lower else 0
  for j in range(4):
   for k in range(4):
    a=o+j*5+k;b=a+1;c=a+5;d=c+1;tri=[(a,b,d),(a,d,c)]
    # x-y orientation is mirrored for the opposite wing.
    if (lower and s==1) or (not lower and s==-1):tri=[tuple(reversed(t)) for t in tri]
    f+=tri;fc += [5 if lower else (8 if k==3 else 2 if k==0 else 10 if k==1 else 3)]*2
 per=[j*5 for j in range(5)]+[21,22,23,24]+[j*5+4 for j in range(3,-1,-1)]+[3,2,1]
 for k,a in enumerate(per):
  b=per[(k+1)%len(per)];tri=[(a,a+25,b+25),(a,b+25,b)]
  if s==1:tri=[tuple(reversed(t)) for t in tri]
  f+=tri;fc += [8,8]
 mesh('broad diamond fin '+str(s),v,f,3,root,False,fc);parts[-1]['uvs']=uv;parts[-1]['vertexBones']=vb
 # A slim raised leading rib joins the wing's long sweep.
 for j in range(4):
  tube('frost leading rib '+str(s)+' '+str(j),[(centers[j]+halves[j]-.5,s*ys[j],zs[j]+1.4),(centers[j+1]+halves[j+1]-.5,s*ys[j+1],zs[j+1]+1.4)],[1.1,.5],11,root if j<2 else tip,n=5)
 # Smaller rear stabilizers preserve the manta's wide, low silhouette.
 leaf('rear split stabilizer '+str(s),(-22,s*7,33),(-43,s*19,32),4.5,4,6,bend=.2)
ellipsoid('wide low head',(23,0,36),(13,13,6.8),4,8,n=12,k=5)
ellipsoid('pale blunt mouth',(30,0,32),(8,9,2.9),5,8,n=10,k=4)
tube('mouth crease',[(35,-6,33),(36,0,32),(35,6,33)],[.35,.45,.35],0,8,n=5)
for s in [-1,1]:
 ellipsoid('raised eye socket '+str(s),(25,s*9.5,41),(4.1,3.5,2.3),0,8,n=8,k=3)
 ellipsoid('turquoise eye '+str(s),(27,s*10.5,42),(2.1,1.75,1.2),14,8,n=8,k=3)
 ellipsoid('narrow eye pupil '+str(s),(27.5,s*10.8,42.9),(.65,.95,.4),13,8,n=6,k=3)
 tube('ice brow '+str(s),[(20,s*10,43),(24,s*11,44),(29,s*9,43)],[1.4,1.5,.7],11,8,n=6)
 tube('curled cephalic lobe '+str(s),[(28,s*9,35),(37,s*11,35),(43,s*8,37),(42,s*5,38)],[3.6,3,1.9,.5],4,8,n=7)
 for j in range(3):tube('gill slit '+str(s)+' '+str(j),[(11-j*5,s*13.5,32),(8-j*5,s*14,34)],[.45,.3],1,1,n=5)
# Thin, conspicuously long tail contrasting with both water wyrm and otter.
tube('thin tail base',[(-24,0,33),(-38,0,31),(-52,2,31)],[3.7,2.8,1.9],2,6,n=8)
tube('long curved whip',[(-51,2,31),(-66,4,32),(-83,7,35),(-96,6,40)],[2,1.3,.8,.12],4,7,n=7)
leaf('ice arrow tail',(-82,7,35),(-98,6,41),3,11,7,bend=.5)
leaf('small dorsal ice crest',(5,0,39),(-11,0,50),5,11,1,bend=.4)
seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,lo in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait','Walk']:
    moving=name=='Walk'
    if bi==0:tr[2]=1.3*(1-math.cos(2*math.pi*u))
    if bi in [2,4]:rot=q([1,0,0],(1 if bi==2 else -1)*(.19 if moving else .11)*w)
    if bi in [3,5]:rot=q([1,0,0],(1 if bi==3 else -1)*(.23 if moving else .13)*math.sin(2*math.pi*u-.5))
    if bi in [6,7]:rot=q([0,0,1],(.09 if bi==6 else .14)*math.sin(2*math.pi*u-.6))
    if bi==8:rot=q([0,1,0],.025*w)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==0:tr=[11*k,0,2.5*k]
    if bi in [2,4]:rot=q([1,0,0],(1 if bi==2 else -1)*-.20*k)
    if bi in [3,5]:rot=q([1,0,0],(1 if bi==3 else -1)*.36*k)
    if bi in [6,7]:rot=q([0,0,1],.2*k)
    if bi==8:rot=q([0,1,0],-.08*k)
   else:
    e=3*u*u-2*u*u*u
    if bi==0:tr[2]=-15*e;sc=[1-.1*e]*3
    if bi in [2,4]:rot=q([1,0,0],(1 if bi==2 else -1)*.20*e)
    if bi in [3,5]:rot=q([1,0,0],(1 if bi==3 else -1)*-.17*e)
    if bi in [6,7]:rot=q([0,0,1],.3*e)
    if bi==8:rot=q([0,1,0],.2*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'frostmanta-source.json').write_text(json.dumps(dict(name='FrostFinManta_Original_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))
# Painted fin rays and restrained icy mottling, 16 authored UV tiles.
rng=np.random.default_rng(8407);atlas=Image.new('RGB',(256,256));Y,X=np.mgrid[0:64,0:64];xx=X/63;yy=Y/63
for k,base in enumerate(colors):
 noise=Image.fromarray(rng.integers(0,255,(8,8),dtype=np.uint8)).resize((64,64),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1));grain=(np.asarray(noise).astype(float)-128)/128;light=1.13-.25*yy-.08*xx+grain*.05
 if k in [8,10,11]:light=.78+.35*(1-yy)+.08*np.sin(xx*12)+grain*.03
 if k>=13:light=np.ones((64,64))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if k in [2,3,4,8,10,11]:
  for x in [6,17,29,41,53]:
   d.line([(31,2),(x,57)],fill=tuple(int(v*.67) for v in base),width=1);d.line([(32,2),(x+1,57)],fill=tuple(min(255,int(v*1.18)) for v in base),width=1)
  if k in [3,4]:
   for x,y in [(11,20),(38,27),(24,44),(48,48)]:d.ellipse((x,y,x+3,y+2),fill=tuple(min(255,int(v*1.24)) for v in base))
 atlas.paste(tile,((k%4)*64,(k//4)*64))
atlas.save(OUT/'FrostMantaAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(9):
 sz=max(1,256>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'FrostMantaAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps({'triangles':sum(len(p['faces']) for p in parts),'bones':len(bones),'continuous_blended_fins':True}))
