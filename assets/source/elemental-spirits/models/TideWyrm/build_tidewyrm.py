"""Original finned water spirit with a continuous, multi-bone swimming body."""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['17353e','245562','387f94','59a0b4','8ec9d1','d0e3d7','285467','658b9b','90ced6','d0d6c6','487f9c','b7e1df','70b1b8','10262c','a1f0ed','f0f2d9'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
cs=[(20,0,41),(2,2,34),(-19,7,32),(-39,10,34),(-59,6,39),(-76,-3,43)];rs=[11.5,12.3,9.2,6.1,3.5,.3]
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='LongWaterHead',parent=2,pivot=[29,0,45])]
for i,c in enumerate(cs):bones.append(dict(name='SwimSpine'+str(i),parent=0 if i==0 else i+1,pivot=list(c)))
bones += [dict(name='FinLeft',parent=2,pivot=[18,9,43]),dict(name='FinRight',parent=2,pivot=[18,-9,43]),dict(name='WhiskerLeft',parent=1,pivot=[45,5,49]),dict(name='WhiskerRight',parent=1,pivot=[45,-5,49])]
# Seamless body with SD matrix groups blending adjoining bones at intermediate rings.
rings=[];rad=[];bind=[]
for j in range(len(cs)-1):
 for t in [0,.5]:rings.append((np.array(cs[j])*(1-t)+np.array(cs[j+1])*t).tolist());rad.append(rs[j]*(1-t)+rs[j+1]*t);bind.append([j+2] if t==0 else [j+2,j+3])
rings.append(cs[-1]);rad.append(rs[-1]);bind.append([7]);n=10;v=[];uv=[];vb=[]
for j,(c,r) in enumerate(zip(rings,rad)):
 t=np.array(rings[min(j+1,len(rings)-1)],dtype=float)-np.array(rings[max(j-1,0)],dtype=float);t/=np.linalg.norm(t);a=np.cross(t,[0.,0.,1.]);a/=np.linalg.norm(a);b=np.cross(t,a)
 for i in range(n):ang=2*math.pi*i/n;v.append((np.array(c)+r*(a*math.cos(ang)+b*math.sin(ang))).tolist());uv.append([j/(len(rings)-1),i/(n-1)]);vb.append(bind[j])
f=[]
for j in range(len(rings)-1):
 for i in range(n):a=j*n+i;b=j*n+(i+1)%n;f.extend([(a,b,b+n),(a,b+n,a+n)])
for i in range(1,n-1):f.extend([(0,i+1,i),((len(rings)-1)*n,(len(rings)-1)*n+i,(len(rings)-1)*n+i+1)])
mesh('continuous swimming body',v,f,2,2,True);parts[-1]['uvs']=uv;parts[-1]['vertexBones']=vb
# A pale narrow ventral stripe follows the same spine; it is a small closed tube.
for j in range(4):tube('pale throat belly '+str(j),[(cs[j][0],cs[j][1],cs[j][2]-rs[j]*.68),(cs[j+1][0],cs[j+1][1],cs[j+1][2]-rs[j+1]*.68)],[rs[j]*.39,rs[j+1]*.39],5,j+2,n=7)
ellipsoid('streamlined long skull',(37,0,49),(16,10.3,10.4),3,1,n=12,k=5)
tube('long aquatic muzzle',[(41,0,48),(50,0,45),(58,0,45)],[7,5.3,3.7],4,1,n=9)
ellipsoid('pale jaw',(48,0,41.9),(13,6,3.5),5,1,n=10,k=4)
ellipsoid('flat nose',(59,0,45),(2.4,4.3,2.5),1,1,n=8,k=3)
for s in [-1,1]:
 ellipsoid('narrow aquatic eye '+str(s),(42,s*9.0,52),(4,1.2,2.2),0,1,n=8,k=3)
 ellipsoid('icy iris '+str(s),(43,s*9.8,52.1),(2.1,.45,1.45),14,1,n=8,k=3)
 ellipsoid('vertical eye slit '+str(s),(43.2,s*10.15,52.1),(.55,.15,1.18),13,1,n=6,k=3)
 tube('low armored brow '+str(s),[(37,s*9,55),(42,s*9.7,55.1),(46,s*7.9,53.8)],[1.8,1.6,.8],4,1,n=6)
 tube('muzzle line '+str(s),[(57,s*3.4,43),(50,s*5.7,42),(44,s*7,44)],[.3,.32,.2],1,1,n=5)
 tube('swept ice horn '+str(s),[(31,s*5,57),(28,s*7,65),(20,s*8,71),(16,s*8,71)],[3.5,2.5,1.4,.1],11,1,n=7)
 leaf('webbed cheek fin '+str(s),(31,s*8,48),(16,s*24,57),7.5,8,1,bend=1)
 leaf('pectoral swimming fin '+str(s),(18,s*9,43),(-2,s*31,35),9,10,8 if s==1 else 9,bend=2)
 tube('long whisker '+str(s),[(45,s*5,49),(52,s*13,52),(57,s*20,59),(52,s*23,64)],[1.2,.9,.55,.1],11,10 if s==1 else 11,n=6)
 # Forked tail: asymmetric long lobes, far from a round animal tail.
 leaf('forked tail lobe '+str(s),(-70,0,43),(-92,s*20,43+s*14),7.5,8,7,bend=1.5)
# Dorsal fins tied to the spine, with a pale pointed leading crest.
for j in range(4):
 x,y,z=cs[j];nx,ny,nz=cs[j+1]
 leaf('dorsal flowing fin '+str(j),(x,y,z+rs[j]*.6),(nx-3,ny,nz+rs[j+1]+(11 if j<2 else 7)),7 if j<2 else 4.8,10,j+2,bend=0)

seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,lo in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait','Walk']:
    move=name=='Walk';w=math.sin(2*math.pi*u)
    if bi==0:tr[2]=1.5*(1-math.cos(2*math.pi*u))
    if bi==1:rot=q([0,1,0],.025*w)
    if 2<=bi<=7:rot=q([0,0,1],(.11 if move else .05)*math.sin(2*math.pi*u-(bi-2)*.65))
    if bi in [8,9]:rot=q([1,0,0],(1 if bi==8 else -1)*(.16 if move else .09)*w)
    if bi in [10,11]:rot=q([0,0,1],(1 if bi==10 else -1)*.07*w)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==0:tr=[7*k,0,2*k]
    if bi==1:rot=q([0,1,0],-.12*k);tr[0]=5*k
    if 2<=bi<=7:rot=q([0,0,1],.08*k*math.sin((bi-2)*.7))
    if bi in [8,9]:rot=q([0,0,1],(1 if bi==8 else -1)*.3*k)
   else:
    e=3*u*u-2*u*u*u
    if bi==0:sc=[1-.4*e]*3;tr[2]=-6*e
    if 2<=bi<=7:rot=q([0,0,1],.11*e)
    if bi==1:rot=q([0,1,0],.25*e)
    if bi in [8,9]:rot=q([1,0,0],(1 if bi==8 else -1)*.7*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'tidewyrm-source.json').write_text(json.dumps(dict(name='TideWyrm_Original_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))
rng=np.random.default_rng(8113);atlas=Image.new('RGB',(256,256));Y,X=np.mgrid[0:64,0:64];xx=X/63;yy=Y/63
for k,base in enumerate(colors):
 noise=Image.fromarray(rng.integers(0,255,(8,8),dtype=np.uint8)).resize((64,64),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1));grain=(np.asarray(noise).astype(float)-128)/128;light=1.14-.26*yy-.1*xx+grain*.05
 if k in [8,10,11]:light=.7+.45*(1-yy)+.12*np.sin(xx*16)+grain*.03
 if k>=13:light=np.ones((64,64))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if k in [2,3,4,6,12]:
  for y in range(5,62,11):
   for x in range(-3+(y//11%2)*6,64,12):
    pts=[(x,y),(x+6,y+6),(x+12,y)];d.line([(a,b+1) for a,b in pts],fill=tuple(min(255,int(v*1.22)) for v in base),width=1);d.line(pts,fill=tuple(int(v*.58) for v in base),width=1)
 elif k in [8,10,11]:
  for x in [8,20,32,44,56]:d.line([(32,60),(x,7)],fill=tuple(int(v*.57) for v in base),width=1);d.line([(33,60),(x+1,7)],fill=tuple(min(255,int(v*1.24)) for v in base),width=1)
 elif k==5:
  for y in [10,22,34,46,58]:d.arc((5,y-7,59,y+8),20,160,fill=tuple(int(v*.65) for v in base),width=1)
 atlas.paste(tile,((k%4)*64,(k//4)*64))
atlas.save(OUT/'TideWyrmAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(9):
 sz=max(1,256>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'TideWyrmAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps({'triangles':sum(len(p['faces']) for p in parts),'bones':len(bones),'continuous_blended_spine':True}))
