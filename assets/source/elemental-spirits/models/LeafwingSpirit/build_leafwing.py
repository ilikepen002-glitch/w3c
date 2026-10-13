"""Original wood-element companion. Reuses the established mesh/rig schema."""
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['183428','344835','547b42','789e50','a7be65','ded092','846143','5f472e','b19c69','e9b985','4c7d3c','73a347','bace73','17291f','ecc264','f9efd0']
colors=[tuple(bytes.fromhex(x)) for x in PAL];parts=[]
def mesh(name,v,f,col,bone,smooth=False,facecols=None):parts.append(dict(name=name,verts=v,faces=f,color=col,bone=bone,smooth=smooth,facecols=facecols))
def ellipsoid(name,c,r,col,bone,n=10,k=5):
 v=[(c[0],c[1],c[2]-r[2])]
 for j in range(1,k):
  p=-math.pi/2+j*math.pi/k
  for i in range(n):
   a=2*math.pi*i/n;v.append((c[0]+r[0]*math.cos(p)*math.cos(a),c[1]+r[1]*math.cos(p)*math.sin(a),c[2]+r[2]*math.sin(p)))
 v.append((c[0],c[1],c[2]+r[2]));f=[]
 for i in range(n):f.append((0,1+(i+1)%n,1+i))
 for j in range(k-2):
  for i in range(n):a=1+j*n+i;b=1+j*n+(i+1)%n;f.extend([(a,b,b+n),(a,b+n,a+n)])
 for i in range(n):f.append((len(v)-1,1+(k-2)*n+i,1+(k-2)*n+(i+1)%n))
 mesh(name,v,f,col,bone,True)
def tube(name,cs,rs,col,bone,n=7):
 v=[]
 for j,(c,r) in enumerate(zip(cs,rs)):
  t=np.array(cs[min(j+1,len(cs)-1)])-np.array(cs[max(j-1,0)]);t=t/np.linalg.norm(t);axis=np.array([0.,1.,0.])
  if abs(np.dot(axis,t))>.9:axis=np.array([1.,0.,0.])
  a=np.cross(t,axis);a/=np.linalg.norm(a);b=np.cross(t,a)
  for i in range(n):u=2*math.pi*i/n;v.append((np.array(c)+r*(a*math.cos(u)+b*math.sin(u))).tolist())
 f=[]
 for j in range(len(cs)-1):
  for i in range(n):a=j*n+i;b=j*n+(i+1)%n;f.extend([(a,b,b+n),(a,b+n,a+n)])
 for i in range(1,n-1):f.extend([(0,i+1,i),((len(cs)-1)*n,(len(cs)-1)*n+i,(len(cs)-1)*n+i+1)])
 mesh(name,v,f,col,bone,True)
def leaf(name,start,end,width,col,bone,bend=0):
 # Closed 3D lanceolate leaf, a pronounced center ridge and tapered tips, not a billboard.
 a=np.array(start,float);b=np.array(end,float);d=b-a;tangent=d/np.linalg.norm(d)
 normal=np.array([1.,0.,0.]);side=np.cross(tangent,normal);side/=np.linalg.norm(side)
 normal=np.cross(side,tangent);normal/=np.linalg.norm(normal)
 v=[];N=7
 for back in [False,True]:
  for j in range(N):
   t=j/(N-1);center=a+d*t+normal*bend*math.sin(math.pi*t)
   w=max(.20,width*math.sin(math.pi*t)**.8)
   for u in [-1,0,1]:
    ridge=(1-abs(u))*2.0*math.sin(math.pi*t);offset=(-.7 if back else .7)+(0 if back else ridge)
    v.append((center+side*w*u+normal*offset).tolist())
 f=[];fc=[]
 for back in [False,True]:
  off=21 if back else 0
  for j in range(N-1):
   for k in range(2):
    aa=off+j*3+k;bb=aa+1;cc=aa+3;dd=bb+3
    f.extend([(aa,cc,dd),(aa,dd,bb)] if back else [(aa,bb,dd),(aa,dd,cc)]);fc.extend([col,col])
 perimeter=[j*3 for j in range(N)]+[(N-1)*3+1,(N-1)*3+2]+[j*3+2 for j in range(N-2,-1,-1)]+[1]
 for i,aa in enumerate(perimeter):bb=perimeter[(i+1)%len(perimeter)];f.extend([(aa,bb+21,aa+21),(aa,bb,bb+21)]);fc.extend([10,10])
 mesh(name,v,f,col,bone,False,fc)
 parts[-1]['uvs']=[[(u+1)/2,j/(N-1)] for back in [False,True] for j in range(N) for u in [-1,0,1]]

bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='SeedBody',parent=0,pivot=[0,0,48]),dict(name='LeafFace',parent=1,pivot=[6,0,65]),dict(name='ArmLeft',parent=1,pivot=[4,11,53]),dict(name='ArmRight',parent=1,pivot=[4,-11,53]),dict(name='RootLeft',parent=1,pivot=[1,5,35]),dict(name='RootRight',parent=1,pivot=[1,-5,35]),dict(name='LeafUpperLeft',parent=1,pivot=[-4,8,59]),dict(name='LeafUpperRight',parent=1,pivot=[-4,-8,59]),dict(name='LeafLowerLeft',parent=1,pivot=[-6,8,49]),dict(name='LeafLowerRight',parent=1,pivot=[-6,-8,49])]
ellipsoid('seed husk torso',(-1,0,47),(12,13,21),6,1,n=12,k=6)
ellipsoid('warm seed chest',(8,0,50),(6,10,15),8,1,n=10,k=5)
ellipsoid('neck',(5,0,64),(7,8,9),3,2,n=10,k=4)
ellipsoid('round leaf mask',(8,0,74),(12,12,12),4,2,n=12,k=6)
ellipsoid('small seed muzzle',(17,0,70),(5.7,7,4.8),5,2,n=10,k=4)
ellipsoid('wood nose',(21.5,0,71.4),(2,2.7,2.1),7,2,n=8,k=3)
for s in [-1,1]:
 ellipsoid('dark eye socket '+str(s),(17.2,s*7.4,77),(2.3,3.8,4),0,2,n=8,k=4)
 ellipsoid('amber eye '+str(s),(19.2,s*7.7,77.2),(1.1,2.4,2.7),14,2,n=8,k=4)
 ellipsoid('pupil '+str(s),(20,s*7.7,77.4),(.45,1.1,2),13,2,n=8,k=3)
 ellipsoid('eye highlight '+str(s),(20.35,s*7.9,78.5),(.2,.55,.55),15,2,n=6,k=3)
 tube('leaf brow '+str(s),[(15,s*4,81.5),(17,s*8,81.8),(14,s*11,79.5)],[1.1,1.4,.9],2,2,n=6)
 tube('smile '+str(s),[(21,s*.5,68.2),(19,s*4,67.7),(17,s*6,68.7)],[.35,.35,.25],1,2,n=5)
 # Curved vines and little bud-like hands.
 bi=3 if s==1 else 4
 tube('curved vine arm '+str(s),[(4,s*11,53),(10,s*17,49),(16,s*17,44)],[3.4,2.9,2.2],3,bi,n=7)
 ellipsoid('bud palm '+str(s),(17,s*17,43),(3.2,3.5,4),4,bi,n=8,k=4)
 for j in range(2):tube('leaf finger '+str(s)+' '+str(j),[(19,s*(15+j*3),44),(22,s*(15+j*3),43),(22.5,s*(15+j*3),41)],[1.0,.9,.4],5,bi,n=5)
 bi=5 if s==1 else 6
 tube('dangling root leg '+str(s),[(1,s*5,35),(3,s*7,29),(8,s*8,25),(12,s*8,26)],[3.8,3.2,2.6,.35],7,bi,n=7)
 # Upper and lower leaves are independent articulated wing bones.
 leaf('upper leaf wing '+str(s),(-4,s*8,59),(-19,s*50,105),12,11,7 if s==1 else 8,bend=4)
 leaf('lower leaf wing '+str(s),(-6,s*8,49),(-17,s*42,34),11,10,9 if s==1 else 10,bend=3)
 leaf('collar leaf '+str(s),(6,s*5,61),(12,s*16,49),6,12,1,bend=1)
# A distinct three-leaf crown and stem, readable from above.
leaf('central crown leaf',(5,0,82),(4,0,101),7,12,2,bend=3)
leaf('left crown leaf',(3,5,81),(-3,17,93),6,11,2,bend=1)
leaf('right crown leaf',(3,-5,81),(-3,-17,93),6,11,2,bend=1)
tube('rear twining stem',[(-10,0,49),(-17,0,41),(-18,2,32),(-13,4,30)],[2.2,1.7,1.,.25],2,1,n=7)

seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);flap=math.sin(4*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait','Walk']:
    fly=name=='Walk'
    if bi==0:tr=[0,0,2.0*(1-math.cos(2*math.pi*u))]
    if bi==1:rot=q([0,1,0],-.14 if fly else .025*w)
    if bi==2:rot=q([0,1,0],.035*w)
    if bi in [3,4]:rot=q([0,1,0],.09*w+(.22 if fly else 0))
    if bi in [5,6]:rot=q([0,1,0],.10*w+(.3 if fly else 0))
    if bi>=7:
     side=1 if bi in [7,9] else -1;low=bi>=9
     rot=q([0,0,1],side*((.60 if fly else .35)*flap*(.8 if low else 1)+(.10 if low else -.08)))
   elif name=='Attack':
    kick=math.sin(math.pi*u)
    if bi==0:tr=[7*kick,0,1.3*kick]
    if bi==1:rot=q([0,1,0],-.20*kick)
    if bi in [3,4]:rot=q([0,1,0],-.7*kick)
    if bi>=7:rot=q([0,0,1],(1 if bi in [7,9] else -1)*(-.35*kick))
   else:
    e=3*u*u-2*u*u*u
    if bi==0:tr=[0,0,-14*e];rot=q([0,1,0],.17*e)
    if bi==1:sc=[1-.20*e,1-.20*e,1-.20*e]
    if bi==2:rot=q([0,1,0],.25*e)
    if bi in [3,4,5,6]:rot=q([0,1,0],.4*e)
    if bi>=7:rot=q([0,0,1],(1 if bi in [7,9] else -1)*1.2*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
data=dict(name='LeafwingSpirit_Original_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=loop) for n,a,z,loop in seqs],palette=colors)
(OUT/'leafwing-source.json').write_text(json.dumps(data))

# Paint a usable 4x4 material atlas. Leaf tiles carry a center vein and paired veins.
rng=np.random.default_rng(67103);atlas=Image.new('RGB',(256,256));Y,X=np.mgrid[0:64,0:64];xx=X/63;yy=Y/63
for k,base in enumerate(colors):
 noise=Image.fromarray(rng.integers(0,255,(8,8),dtype=np.uint8)).resize((64,64),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1));grain=(np.asarray(noise).astype(float)-128)/128
 light=1.14-.26*yy-.1*xx+grain*.05
 if k in [10,11,12]:light=.72+.35*(1-yy)+.22*np.exp(-((xx-.5)/.13)**2)+grain*.03
 if k>=13:light=np.ones((64,64))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if k in [10,11,12]:
  d.line([(32,3),(31,32),(32,61)],fill=tuple(min(255,int(v*1.35)) for v in base),width=2)
  for y in [14,27,40,52]:
   for s in [-1,1]:
    pts=[(32,y+4),(32+s*12,y-1),(32+s*24,y-10)]
    d.line([(x,y+1) for x,y in pts],fill=tuple(int(v*.58) for v in base),width=2);d.line(pts,fill=tuple(min(255,int(v*1.20)) for v in base),width=1)
 elif k in [6,7,8]:
  for x in [9,20,35,48,57]:d.line([(x,5),(x-3,21),(x+2,39),(x-1,59)],fill=tuple(int(v*.60) for v in base),width=1);d.line([(x+1,5),(x-2,21),(x+3,39)],fill=tuple(min(255,int(v*1.15)) for v in base),width=1)
 elif k in [2,3,4,5]:
  for y in [15,32,48]:d.arc((7,y,55,y+14),20,160,fill=tuple(int(v*.80) for v in base),width=1)
 atlas.paste(tile,((k%4)*64,(k//4)*64))
atlas.save(OUT/'LeafwingAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(9):
 sz=max(1,256>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
header=b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)
palette=b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))
(OUT/'LeafwingAtlas.blp').write_bytes(header+palette+b''.join(blobs))
print(json.dumps({'triangles':sum(len(p['faces']) for p in parts),'bones':len(bones),'parts':len(parts)}))
