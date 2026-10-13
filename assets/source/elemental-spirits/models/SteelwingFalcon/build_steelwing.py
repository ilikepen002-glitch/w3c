"""Original broad-winged steel falcon, short fan tail and heavy raptor chest."""
from primitives import parts,mesh,ellipsoid,tube
from common import plate,seqs,q,save
import math,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
palette=['18232b','2c3941','455766','718a97','b8c8c8','e2ddbc','8b7770','403c39','ab8444','d6b368','6e899c','9db0b9','d6dbce','131c22','f0b52c','fff1a0']
bones=[dict(name=n,parent=p,pivot=v) for n,p,v in [('Root',-1,[0,0,0]),('RaptorChest',0,[0,0,49]),('ArmoredHead',1,[16,0,58]),('LeftWing',1,[-3,10,50]),('RightWing',1,[-3,-10,50]),('LeftWingTip',3,[-12,44,52]),('RightWingTip',4,[-12,-44,52]),('FanTail',1,[-16,0,45]),('LeftTalons',1,[6,7,35]),('RightTalons',1,[6,-7,35])]]
ellipsoid('deep raptor breast',(1,0,47),(19,13,15),2,1,n=12,k=6)
ellipsoid('pale armored breast',(12,0,47),(9,11,11),4,1,n=10,k=5)
ellipsoid('flat wide shoulders',(-3,0,54),(16,18,7),3,1,n=12,k=4)
ellipsoid('heavy falcon skull',(22,0,59),(12,9.5,9),4,2,n=10,k=5)
# Golden hooked beak terminates well below its dorsal edge.
v=[(29,-5,61),(29,5,61),(30,-3.8,55),(30,3.8,55),(40,-2,59),(40,2,59),(42,0,52),(37,0,51)];f=[(0,1,5),(0,5,4),(0,4,2),(1,3,5),(2,4,6),(3,6,5),(2,6,7),(2,7,3),(3,7,6),(4,5,6),(0,2,3),(0,3,1)];f=[(a,c,b) for a,b,c in f];mesh('thick hooked brass beak',v,f,9,2,False,[9,12,8,9,8,8,7,7,7,12,8,8])
plate('single backwards helmet ridge',(26,0,66),(4,0,72),4,3,10,2,normal=(0,0,1))
for s in [-1,1]:
 ellipsoid('dark falcon eye mask '+str(s),(26,s*8.5,61),(5,1.6,3.2),0,2,n=8,k=3)
 ellipsoid('sharp amber eye '+str(s),(28,s*9.7,61.5),(2,.35,1.5),14,2,n=8,k=3)
 ellipsoid('raptor pupil '+str(s),(28.7,s*10,61.5),(.65,.15,1.15),13,2,n=6,k=3)
 tube('angled steel brow '+str(s),[(20,s*8.4,65),(26,s*9.5,64),(30,s*6.5,63)],[1.8,1.5,.5],10,2,n=6)
 plate('cheek guard '+str(s),(24,s*9,57),(11,s*12,49),4,1.4,8,2,normal=(0,s,0))
 bi=3 if s==1 else 4;tip=5 if s==1 else 6
 tube('wide swept wing spar '+str(s),[(-4,s*11,52),(0,s*29,56),(-13,s*49,54),(-29,s*71,50)],[6,5.5,4,1.2],3,bi,n=8)
 for i in range(5):
  y=s*(14+i*7);x=-2-i*2.5;z=53+i*.4
  plate('overlap broad wing armor '+str(s)+' '+str(i),(x+4,y,z+3),(x-23,s*(18+i*7),z-5),7.2,2.2,4 if i%2 else 11,bi)
 for i in range(6):
  y=s*(35+i*6);x=-10-i*2.8;z=52-i*.4
  plate('long bladed primary '+str(s)+' '+str(i),(x,y,z),(x-21-i*2.5,s*(47+i*6.7),z-12+i*.6),4.6,1.6,10 if i%2 else 12,tip)
 for i in range(3):
  plate('leading brass rivet ridge '+str(s)+' '+str(i),(1-i*4,s*(14+i*10),57),(-8-i*4,s*(24+i*10),58),3,1.3,9,bi)
 fi=8 if s==1 else 9
 tube('thick scale leg '+str(s),[(6,s*7,36),(3,s*8,29),(11,s*8,23)],[3.4,2.6,2.3],8,fi,n=7)
 for j in [-1,0,1]:tube('strong curved talon '+str(s)+' '+str(j),[(11,s*8,23),(20,s*8+j*3.4,22),(23,s*8+j*3.5,18.5)],[1.5,1.15,.18],0,fi,n=6)
 tube('rear gripping claw '+str(s),[(8,s*8,23),(3,s*10,22),(1,s*10,19)],[1.3,.9,.15],0,fi,n=6)
for i in range(5):
 s=i-2;plate('short fanned steel tail '+str(i),(-14,s*3,44),(-42+abs(s)*4,s*9,39),5.5,1.7,11 if i%2 else 4,7)
for i in range(3):plate('layered breast plate '+str(i),(18,0,55-i*6),(19,0,46-i*6),7-i,1.5,9 if i==0 else 4,1,normal=(1,0,0))
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);f=math.sin(4*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait','Walk']:
    if bi==0:tr[2]=(1.3 if name=='Walk' else .6)*(1-math.cos(2*math.pi*u))
    if bi==1:rot=q([0,1,0],-.06 if name=='Walk' else .018*w)
    if bi==2:rot=q([0,0,1],.08*w)
    if bi in [3,4]:rot=q([1,0,0],(1 if bi==3 else -1)*(.21 if name=='Walk' else .10)*f)
    if bi in [5,6]:rot=q([1,0,0],(1 if bi==5 else -1)*.12*f)
    if bi==7:rot=q([0,1,0],.1*w)
    if bi in [8,9]:rot=q([0,1,0],.11*w)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==0:tr=[9*k,0,-3*k]
    if bi==1:rot=q([0,1,0],.22*k)
    if bi==2:rot=q([0,1,0],.19*k)
    if bi in [3,4]:rot=q([1,0,0],(1 if bi==3 else -1)*.26*k)
    if bi in [5,6]:rot=q([1,0,0],(1 if bi==5 else -1)*.2*k)
    if bi in [8,9]:rot=q([0,1,0],-.6*k)
   else:
    e=u*u*(3-2*u)
    if bi==0:tr=[-3*e,0,-5*e]
    if bi==1:rot=q([0,1,0],-.12*e)
    if bi==2:rot=q([0,1,0],.55*e)
    if bi in [3,4]:rot=q([1,0,0],(1 if bi==3 else -1)*-.30*e)
    if bi in [5,6]:rot=q([1,0,0],(1 if bi==5 else -1)*-.1*e)
    if bi in [8,9]:rot=q([0,1,0],.30*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
save(ROOT,'steelwing','SteelwingFalcon','SteelwingAtlas',bones,palette,'steel')
