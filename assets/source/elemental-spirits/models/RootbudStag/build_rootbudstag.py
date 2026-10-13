"""Original thin-legged sapling stag with real branch antlers and sparse spring leaves."""
from primitives import parts,mesh,ellipsoid,tube
from common import plate,seqs,q,save
import math,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
palette=['172c24','3a3c2a','765333','69934f','91b765','d8c89b','445f38','4c3828','b59760','ac7544','426e3c','76a75a','c0d087','13241c','e1b55b','faf1c6']
bones=[dict(name=n,parent=p,pivot=v) for n,p,v in [('Root',-1,[0,0,0]),('SlimTrunk',0,[-3,0,37]),('AlertDeerHead',1,[23,0,49]),('LeafTail',1,[-29,0,39]),('FrontLeft',0,[17,7,31]),('FrontRight',0,[17,-7,31]),('RearLeft',0,[-20,8,32]),('RearRight',0,[-20,-8,32]),('LeftEar',2,[27,5,60]),('RightEar',2,[27,-5,60])]]
ellipsoid('slim long deer torso',(-4,0,37),(27,9.7,10.5),2,1,n=12,k=5)
ellipsoid('pale slender underbelly',(-1,0,33),(20,7.8,6),8,1,n=10,k=4)
ellipsoid('narrow chest',(16,0,39),(10,9,12),2,1,n=10,k=5)
tube('tall sloping neck',[(17,0,38),(22,0,47),(26,0,55)],[7.5,6.4,5],2,2,n=9)
ellipsoid('deer wedge skull',(30,0,58),(8.5,5.5,6.3),8,2,n=10,k=4)
tube('slender deer muzzle',[(33,0,56),(39,0,53),(44,0,52)],[4.6,3.5,2.4],8,2,n=8)
ellipsoid('small deer nose',(45,0,52),(2,2.5,1.7),0,2,n=8,k=3)
for s in [-1,1]:
 ellipsoid('deep gentle eye '+str(s),(33,s*5,59),(2.7,.75,1.5),0,2,n=8,k=3)
 ellipsoid('amber deer iris '+str(s),(34,s*5.65,59),(1.15,.24,1),14,2,n=8,k=3)
 ellipsoid('deer pupil '+str(s),(34.2,s*5.84,59),(.35,.12,.75),13,2,n=6,k=3)
 ei=8 if s==1 else 9
 plate('long deer ear '+str(s),(27,s*4.7,60),(24,s*16,66),3.8,1.3,8,ei,normal=(1,0,0))
 plate('green ear inset '+str(s),(26.5,s*7,61),(24,s*14,65),2.1,.8,3,ei,normal=(1,0,0))
 # Branches fork at three heights and terminate in actual buds.
 tube('sapling main antler '+str(s),[(25,s*3,63),(22,s*7,73),(16,s*11,85),(12,s*14,95)],[2.5,2,1.2,.18],9,2,n=6)
 tube('front fork antler '+str(s),[(22,s*7,73),(30,s*9,80),(32,s*10,88)],[1.7,1,.15],9,2,n=6)
 tube('outer fork antler '+str(s),[(17,s*10,82),(9,s*19,86),(6,s*23,91)],[1.3,.8,.13],9,2,n=6)
 tube('inner antler twig '+str(s),[(15,s*12,89),(21,s*14,94)],[.9,.1],9,2,n=5)
 for j,(a,b,w) in enumerate([((12,s*14,94),(5,s*17,100),3),((31,s*10,86),(37,s*15,91),3.3),((7,s*21,89),(0,s*26,92),3)]):plate('antler sprout '+str(s)+' '+str(j),a,b,w,1,4 if j%2 else 11,2)
 for j in range(3):plate('chest hanging leaf '+str(s)+' '+str(j),(20-j*4,s*5,43),(13-j*4,s*11,31),3.5,1.2,3 if j%2 else 11,1,normal=(0,s,1))
# Saddle of sparse leaves leaves visible lean wooden flanks.
for i,x in enumerate([13,3,-7,-17]):
 plate('leaf saddle '+str(i),(x+6,0,47),(x-9,0,47),6,1.6,4 if i%2 else 11,1)
for i,(x,y) in enumerate([(17,7),(17,-7),(-20,8),(-20,-8)]):
 bi=4+i;s=1 if y>0 else -1;fore=i<2
 tube('long slim ungulate leg '+str(i),[(x,y,33),(x+(-3 if fore else 5),y+s*1.5,20),(x+2,y+s*2,5)],[3.4,2.2,1.75],7,bi,n=7)
 ellipsoid('small cloven hoof '+str(i),(x+2,y+s*2,4),(3.5,2.6,2.6),1,bi,n=8,k=3)
 tube('hoof dividing line '+str(i),[(x+4.7,y+s*2,2.5),(x+5.1,y+s*2,4.5)],[.2,.16],0,bi,n=4)
plate('short raised leaf tail',(-28,0,39),(-40,0,48),4.5,1.2,11,3,normal=(0,0,1))
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.4*(1-math.cos(2*math.pi*u))
    if bi==2:rot=q([0,0,1],.045*w)
    if bi==3:rot=q([0,0,1],.12*w)
    if bi in [8,9]:rot=q([1,0,0],(.08 if bi==8 else -.08)*w)
   elif name=='Walk':
    if bi==1:tr[2]=.65*(1-math.cos(4*math.pi*u))
    if bi==2:rot=q([0,1,0],.035*w)
    if bi==3:rot=q([0,0,1],.12*w)
    if bi in [4,5,6,7]:
     p=[0,.5,.5,0][bi-4];v=math.sin(2*math.pi*(u+p));tr=[5*v,0,max(0,math.cos(2*math.pi*(u+p)))*3];rot=q([0,1,0],-.045*v)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==1:tr=[5*k,0,-1*k]
    if bi==2:rot=q([0,1,0],.53*k)
    if bi in [4,5]:tr=[3*k,0,1.5*k]
   else:
    e=u*u*(3-2*u)
    if bi==0:tr=[0,0,-1*e]
    if bi==1:tr=[-2*e,0,-6*e];rot=q([1,0,0],.06*e)
    if bi==2:rot=q([0,1,0],.55*e)
    if bi in [4,5,6,7]:sc=[1,1,1-.12*e]
    if bi==3:rot=q([0,1,0],-.3*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
save(ROOT,'rootbudstag','RootbudStag','RootbudAtlas',bones,palette,'wood')
