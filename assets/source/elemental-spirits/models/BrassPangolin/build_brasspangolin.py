"""Original low brass pangolin: pointed snout, staggered dorsal scales, long armored tail."""
from primitives import parts,mesh,ellipsoid,tube
from common import plate,seqs,q,save
import math,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
palette=['26282b','46332b','6b4931','96734c','b59a69','d4bc88','6d806f','514733','927341','c8a153','795738','ad874b','dcc793','151e1b','66c4aa','d0fff1']
bones=[dict(name=n,parent=p,pivot=v) for n,p,v in [('Root',-1,[0,0,0]),('LowBack',0,[-6,0,23]),('LongNose',1,[25,0,22]),('TailBase',1,[-34,0,23]),('TailTip',3,[-65,0,16]),('DiggingArmLeft',0,[20,12,18]),('DiggingArmRight',0,[20,-12,18]),('HindLeft',0,[-24,12,18]),('HindRight',0,[-24,-12,18])]]
ellipsoid('long low pangolin torso',(-7,0,23),(36,15,12),2,1,n=14,k=5)
ellipsoid('dark low belly',(-4,0,18),(30,12,7),7,1,n=10,k=4)
ellipsoid('sloping shoulders',(20,0,22),(15,12.5,10),3,1,n=10,k=4)
tube('low conical skull',[(25,0,23),(35,0,24),(45,0,22),(54,0,18.5)],[10,8,4.4,1.8],3,2,n=10)
ellipsoid('small blunt snout tip',(55,0,18.5),(2.8,2.1,1.8),0,2,n=8,k=3)
for s in [-1,1]:
 ellipsoid('small recessed pangolin eye '+str(s),(38,s*6.7,25),(2.5,.9,1.6),0,2,n=8,k=3)
 ellipsoid('jade eye '+str(s),(39,s*7.5,25.2),(1.15,.26,1.0),14,2,n=8,k=3)
 ellipsoid('small pupil '+str(s),(39.25,s*7.72,25.2),(.4,.12,.8),13,2,n=6,k=3)
 plate('slanted brow scale '+str(s),(32,s*6.5,28),(42,s*4.8,27),2.6,1.5,9,2,normal=(0,s*.4,1))
 tube('snout line '+str(s),[(53,s*1.9,17.5),(46,s*3.8,18.2),(40,s*5.8,20)],[.25,.3,.2],1,2,n=5)
 # Small ear folded into the side, not large mammalian ears.
 plate('small ear flap '+str(s),(28,s*8.8,27),(25,s*11.8,31),2.3,1,6,2,normal=(0,s,0))
# A field of individual overlapping scales follows an elongated back; there is no enclosing dome.
for row,x in enumerate([25,14,3,-8,-19,-30]):
 for j,y in enumerate([-12,-6,0,6,12]):
  z=24+10*math.sqrt(max(.05,1-(y/16)**2))-(max(0,abs(x+4)-25)*.20)
  shift=2 if j%2 else 0
  plate('back overlapping scale '+str(row)+' '+str(j),(x+7+shift,y,z),(x-9+shift,y*.98,z-2),5.4,2.0,9 if (row+j)%3==0 else 4,1,normal=(0,y/23,1))
for s in [-1,1]:
 for i,x in enumerate([22,8,-6,-20,-31]):
  plate('side hanging scale '+str(s)+' '+str(i),(x+5,s*12,29),(x-8,s*16,18),5,1.6,3 if i%2 else 8,1,normal=(0,s,0))
# Long tapering, slightly curved tail with independent middle and end motion.
tube('long heavy tail base',[(-34,0,23),(-49,0,21),(-65,1,16)],[11,9,6],2,3,n=10)
tube('pointed armored tail',[(-64,1,16),(-80,3,12),(-94,6,11),(-102,8,13)],[6.2,4.6,2.5,.3],3,4,n=9)
for i,(x,y,z,w) in enumerate([(-39,0,32,8),(-51,.3,29,7),(-63,1,24,5.8),(-74,2.3,19,4.8),(-84,4,16,3.7),(-94,6,15,2.5)]):
 plate('tail shingle '+str(i),(x+8,y,z),(x-9,y+1.5,z-2),w,1.8,9 if i%2==0 else 4,3 if i<2 else 4)
 for s in [-1,1]:plate('tail side shingle '+str(i)+' '+str(s),(x+6,y+s*w*.65,z-3),(x-9,y+s*w*.6,z-6),w*.55,1,8,3 if i<2 else 4,normal=(0,s*.5,1))
for i,(x,y) in enumerate([(20,12),(20,-12),(-24,12),(-24,-12)]):
 bi=5+i;s=1 if y>0 else -1;fore=i<2
 tube('short bent digging leg '+str(i),[(x,y,19),(x+(-3 if fore else 4),y+s*5,11),(x+4,y+s*6,6)],[5.6,4.5,3.9],2,bi,n=8)
 ellipsoid('broad digging palm '+str(i),(x+6,y+s*6,5.1),(7,5,3),3,bi,n=8,k=3)
 plate('wrist copper plate '+str(i),(x-2,y+s*4,14),(x+7,y+s*6,8),4.5,1.4,9,bi)
 for j in [-1,0,1]:tube('elongated digging claw '+str(i)+' '+str(j),[(x+9,y+s*6+j*2.8,5),(x+15,y+s*6+j*3,4.7),(x+17,y+s*6+j*3,3.5)],[1.45,1.05,.12],12,bi,n=6)
# Three narrow forehead scales point toward the long nose.
for i in range(3):plate('forehead scale '+str(i),(26+i*7,0,31-i*1.8),(37+i*6,0,28-i*2.8),4.4-i,1.5,4,2)
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.35*(1-math.cos(2*math.pi*u))
    if bi==2:rot=q([0,0,1],.05*w)
    if bi in [3,4]:rot=q([0,0,1],(.05 if bi==3 else .1)*w)
   elif name=='Walk':
    if bi==1:tr[2]=.45*(1-math.cos(4*math.pi*u));rot=q([1,0,0],.024*w)
    if bi==2:rot=q([0,1,0],.045*w)
    if bi in [3,4]:rot=q([0,0,1],(.08 if bi==3 else .14)*w)
    if bi in [5,6,7,8]:
     p=[0,.5,.5,0][bi-5];v=math.sin(2*math.pi*(u+p));tr=[3.5*v,0,max(0,math.cos(2*math.pi*(u+p)))*2.2];rot=q([0,1,0],-.025*v)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==1:tr=[3*k,0,.7*k]
    if bi==2:rot=q([0,1,0],.14*k)
    if bi in [5,6]:tr=[5*k,0,2.2*k];rot=q([0,1,0],-.1*k)
    if bi in [3,4]:rot=q([0,0,1],(.13 if bi==3 else .2)*k)
   else:
    e=u*u*(3-2*u)
    if bi==0:tr=[0,0,-1.3*e]
    if bi==1:tr=[-2*e,0,-2*e];rot=q([1,0,0],.04*e)
    if bi==2:rot=q([0,1,0],.18*e)
    if bi in [3,4]:rot=q([0,0,1],(.24 if bi==3 else .35)*e)
    if bi in [5,6,7,8]:sc=[1,1,1-.1*e]
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
save(ROOT,'brasspangolin','BrassPangolin','BrassPangolinAtlas',bones,palette,'brass')
