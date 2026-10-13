"""Original walking woodland mushroom spirit with a fluted cap and root feet."""
from primitives import parts,mesh,ellipsoid,tube
from common import plate,seqs,q,save
import math,pathlib,numpy as np
ROOT=pathlib.Path(__file__).resolve().parent
palette=['213127','463c2c','846448','6c8545','9aa862','d4c293','536836','594432','a28d58','b67e43','6e743d','a2ab60','dfd3a7','19231b','bdcd72','f2edb8']
bones=[dict(name=n,parent=p,pivot=v) for n,p,v in [('Root',-1,[0,0,0]),('StemBody',0,[0,0,26]),('WideMushroomCap',1,[-2,0,45]),('VineArmLeft',1,[0,9,31]),('VineArmRight',1,[0,-9,31]),('RootFootLeft',0,[0,6,15]),('RootFootRight',0,[0,-6,15]),('CapLeaf',2,[-9,14,58])]]
ellipsoid('tapered woody mushroom stem',(0,0,27),(10,8.7,20),5,1,n=12,k=6)
ellipsoid('rough stem lower trunk',(-1,0,18),(11,10,10),2,1,n=10,k=4)
# One closed, faceted mushroom cap with a scalloped rim and a pale undersurface.
N=20;v=[(-2,0,68)];rings=[(9,66),(21,61),(31,51),(34,46),(31.5,43),(8,44)]
for r,z in rings:
 for i in range(N):
  a=2*math.pi*i/N;wave=1.2*math.cos(5*a) if r>28 else 0
  v.append((-2+(r+wave)*math.cos(a),(r+wave)*.86*math.sin(a),z+.7*math.cos(5*a)))
v.append((-2,0,44));f=[];fc=[]
for i in range(N):f.append((0,1+i,1+(i+1)%N));fc.append(9 if i%3 else 8)
for j in range(len(rings)-1):
 for i in range(N):
  a=1+j*N+i;b=1+j*N+(i+1)%N;f.extend([(a,a+N,b+N),(a,b+N,b)]);fc.extend(([9 if (i+j)%3 else 8]*2) if j<3 else ([12 if i%2 else 8]*2))
for i in range(N):f.append((len(v)-1,1+(len(rings)-1)*N+(i+1)%N,1+(len(rings)-1)*N+i));fc.append(12)
mesh('single scalloped woodland cap',v,f,9,2,False,fc)
for i in range(16):
 a=2*math.pi*i/16
 tube('radial underside gill '+str(i),[(-2+8*math.cos(a),8*.86*math.sin(a),43.7),(-2+29*math.cos(a),29*.86*math.sin(a),43.4)],[.6,.4],1,2,n=4)
# Pale irregular spore patches sit on the cap rather than forming eyes or decorative horns.
for i,(x,y,z,rx,ry) in enumerate([(4,-11,63,4,3),(-14,-9,63,4.5,3.5),(16,6,60,3.7,2.7),(-10,16,59,4.7,3.2),(21,-11,54,3.2,2.6),(-24,3,57,3.4,3.0)]):
 ellipsoid('painted cap spore patch '+str(i),(x,y,z),(rx,ry,.7),12,2,n=7,k=3)
for s in [-1,1]:
 ellipsoid('shadowed stem eye '+str(s),(9.1,s*4,35.2),(1.2,2.1,1.7),0,1,n=8,k=3)
 ellipsoid('small sap glow '+str(s),(10.1,s*4,35.2),(.35,1.15,.95),14,1,n=8,k=3)
 ellipsoid('tiny dark pupil '+str(s),(10.42,s*4,35.1),(.13,.35,.72),13,1,n=6,k=3)
 tube('wooden brow '+str(s),[(8.5,s*2,38),(10,s*4,38),(8.5,s*6,37)],[.8,.9,.5],2,1,n=5)
 ai=3 if s==1 else 4
 tube('crooked vine arm '+str(s),[(0,s*9,32),(-2,s*19,25),(7,s*23,20)],[3.3,2.7,2.1],7,ai,n=7)
 ellipsoid('root hand '+str(s),(8,s*23,19),(3.5,3.3,3.4),2,ai,n=8,k=3)
 for j in [-1,0,1]:tube('root finger '+str(s)+' '+str(j),[(9,s*23+j*1.6,19),(14,s*23+j*2.0,16),(13,s*23+j*2.1,13.7)],[.9,.65,.1],8,ai,n=5)
 plate('arm leaf '+str(s),(-1,s*17,26),(5,s*29,26),4.2,1.4,11,ai,normal=(0,0,1))
 fi=5 if s==1 else 6
 tube('stout root leg '+str(s),[(0,s*6,16),(-3,s*9,9),(4,s*10,5.3)],[4.5,3.5,3.2],7,fi,n=8)
 ellipsoid('broad root foot '+str(s),(6,s*10,4.5),(7,4.5,2.7),2,fi,n=8,k=3)
 for j in [-1,0,1]:tube('ground root toe '+str(s)+' '+str(j),[(9,s*10+j*2,4),(15,s*10+j*3,3.4),(17,s*10+j*3,2.8)],[1.2,.85,.1],8,fi,n=5)
# Three rooted leaves grow from one edge of the cap; asymmetric silhouette, no crown of horns.
tube('cap sprout stem',[(-11,13,60),(-15,18,68),(-13,21,75)],[1.2,.9,.12],6,7,n=6)
plate('large cap sprout leaf',(-14,18,68),(-27,26,74),5.5,1.3,3,7)
plate('small cap sprout leaf',(-14,20,72),(-3,27,80),4.2,1.1,11,7)
plate('lower moss lapel',(7,0,28),(12,0,16),6,1.7,3,1,normal=(1,0,0))
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.6*(1-math.cos(2*math.pi*u));rot=q([1,0,0],.035*w)
    if bi==2:rot=q([0,1,0],.035*w)
    if bi in [3,4]:rot=q([1,0,0],(.08 if bi==3 else -.08)*w)
    if bi==7:rot=q([1,0,0],.15*w)
   elif name=='Walk':
    if bi==1:tr[2]=.8*(1-math.cos(4*math.pi*u));rot=q([1,0,0],.075*w)
    if bi==2:rot=q([1,0,0],-.035*w)
    if bi in [3,4]:rot=q([0,1,0],(.22 if bi==3 else -.22)*w)
    if bi in [5,6]:
     p=0 if bi==5 else .5;v=math.sin(2*math.pi*(u+p));tr=[3.5*v,0,max(0,math.cos(2*math.pi*(u+p)))*2.8]
    if bi==7:rot=q([0,1,0],.12*w)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==1:tr=[3*k,0,.4*k];rot=q([0,1,0],.10*k)
    if bi==2:rot=q([0,1,0],.14*k)
    if bi in [3,4]:rot=q([0,1,0],-.6*k);tr=[3*k,0,0]
    if bi==7:rot=q([0,1,0],-.15*k)
   else:
    e=u*u*(3-2*u)
    if bi==0:tr=[0,0,-1.3*e]
    if bi==1:tr=[-2*e,0,-3*e];rot=q([0,1,0],-.15*e)
    if bi==2:rot=q([0,1,0],.3*e)
    if bi in [3,4]:rot=q([1,0,0],(.2 if bi==3 else -.2)*e)
    if bi in [5,6]:sc=[1,1,1-.1*e]
    if bi==7:rot=q([0,1,0],.35*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
save(ROOT,'mosscap','MosscapSprite','MosscapAtlas',bones,palette,'wood')
