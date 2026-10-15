"""Original upright rock gibbon, broad boulder forearms and small inset eyes."""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['292723','494138','75654e','9a8565','b3a080','d1c19b','73664e','625840','aa9066','ad873d','605e4b','91846a','c2b48c','1a1e1b','d3a749','fff0b8'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='HeavyTorso',parent=0,pivot=[0,0,31]),dict(name='RockMaskHead',parent=1,pivot=[7,0,57]),dict(name='LeftArm',parent=1,pivot=[0,18,47]),dict(name='RightArm',parent=1,pivot=[0,-18,47]),dict(name='LeftHand',parent=3,pivot=[11,30,20]),dict(name='RightHand',parent=4,pivot=[11,-30,20]),dict(name='LeftLeg',parent=0,pivot=[-3,10,24]),dict(name='RightLeg',parent=0,pivot=[-3,-10,24])]
ellipsoid('barrel earth fur torso',(-2,0,36),(18,20,25),2,1,n=12,k=6)
ellipsoid('broad shoulder yoke',(0,0,49),(17,26,13),3,1,n=12,k=5)
ellipsoid('lighter heavy chest',(10,0,41),(10,15,19),4,1,n=10,k=5)
ellipsoid('short stocky waist',(-1,0,22),(12,15,11),2,1,n=10,k=4)
ellipsoid('angular big cranial mass',(8,0,62),(14,14,15),3,2,n=10,k=5)
ellipsoid('flat dark mask',(18,0,61),(6,12,10),1,2,n=10,k=4)
ellipsoid('square short muzzle',(23,0,55),(8,9,6),4,2,n=8,k=4)
ellipsoid('wide flat dark nose',(29,0,59),(2.6,6.5,3.2),0,2,n=8,k=3)
tube('heavy continuous muzzle seam',[(27,-7,53),(30,0,52),(27,7,53)],[.5,.6,.5],0,2,n=5)
for s in [-1,1]:
 ellipsoid('small inset eye '+str(s),(23,s*7.8,65),(2.5,2.1,1.5),0,2,n=8,k=3)
 ellipsoid('amber narrow iris '+str(s),(24.5,s*8,65),(.85,1.6,1.05),14,2,n=6,k=3)
 ellipsoid('obsidian pupil '+str(s),(25.2,s*8,65.1),(.3,.7,.8),13,2,n=6,k=3)
 ellipsoid('gold eye catchlight '+str(s),(25.48,s*8.2,65.55),(.18,.3,.3),15,2,n=6,k=3)
 tube('great crag brow '+str(s),[(22,s*2,69),(23,s*7,69),(18,s*12,67)],[3.2,3.6,2.4],3,2,n=6)
 ellipsoid('small round earth ear '+str(s),(8,s*13,63),(4,3.5,5),2,2,n=8,k=3)
 leaf('low crown stone '+str(s),(8,s*6,73),(2,s*10,80),4,10,2,bend=0,normal_hint=(1,0,0))
 leaf('angular jaw mane '+str(s),(13,s*11,59),(3,s*16,51),6,2,2,bend=1,normal_hint=(1,0,0))
 bi=3 if s==1 else 4;hand=5 if s==1 else 6
 tube('long bowed upper arm '+str(s),[(0,s*19,48),(-5,s*28,37),(5,s*31,24)],[9,8,9],2,bi,n=9)
 ellipsoid('great rounded stone forearm '+str(s),(9,s*31,25),(11,10,16),10,bi,n=10,k=5)
 ellipsoid('large broad fist '+str(s),(15,s*31,14),(11,10,8),3,hand,n=10,k=4)
 for j in [-1,0,1]:
  ellipsoid('rounded knuckle '+str(s)+' '+str(j),(23,s*31+j*4.4,13),(4.4,3.2,5),4,hand,n=6,k=3)
 tube('inward stone thumb '+str(s),[(12,s*23,18),(19,s*23,15),(21,s*25,10)],[3.6,3,1.8],3,hand,n=6)
 leaf('shoulder stone lip '+str(s),(-5,s*20,54),(-11,s*29,57),6.5,10,bi,bend=1,normal_hint=(0,0,1))
 leg=7 if s==1 else 8
 tube('short bowed leg '+str(s),[(-3,s*10,25),(-7,s*14,15),(1,s*15,7)],[7.6,6.6,4.8],2,leg,n=8)
 ellipsoid('broad primate foot '+str(s),(6,s*15,5.2),(10,6.5,3),3,leg,n=8,k=4)
 for j in [-1,0,1]:ellipsoid('short toe '+str(s)+' '+str(j),(13,s*15+j*3.7,4.7),(3.3,1.8,2.3),4,leg,n=5,k=3)
seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.45*(1-math.cos(2*math.pi*u));sc=[1+.008*(1-math.cos(2*math.pi*u)),1,1]
    if bi==2:rot=q([0,0,1],.035*w)
    if bi in [3,4]:rot=q([0,1,0],.025*w)
   elif name=='Walk':
    if bi==1:tr[2]=.55*(1-math.cos(4*math.pi*u));rot=q([1,0,0],.028*w)
    if bi==2:rot=q([0,0,1],-.028*w)
    if bi in [3,4]:rot=q([0,1,0],(.14 if bi==3 else -.14)*w)
    if bi in [7,8]:
     p=0 if bi==7 else .5;v=math.sin(2*math.pi*(u+p));tr=[4*v,0,max(0,math.cos(2*math.pi*(u+p)))*3.5];rot=q([0,1,0],-.04*v)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==1:tr=[1*k,0,1*k]
    if bi==2:rot=q([0,1,0],.10*k)
    if bi in [3,4]:rot=q([0,1,0],-.75*k)
    if bi in [5,6]:rot=q([0,1,0],-.10*k)
   else:
    e=3*u*u-2*u*u*u
    if bi==1:tr=[-2*e,0,-4*e]
    if bi==2:rot=q([0,1,0],.4*e)
    if bi in [3,4]:rot=q([0,1,0],-.06*e)
    if bi in [7,8]:sc=[1,1,1-.15*e]
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'earth_gibbon-source.json').write_text(json.dumps(dict(name='BoulderArmGibbon_Original_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))

# Refined atlas is the persisted built-in imagegen output. Resize/BLP encoding only.
import runpy
runpy.run_path(str(ROOT.parents[4]/'tools/EncodeWaterEarthAtlas.py'))['encode'](OUT/'atlas-refined-imagegen.png',OUT/'BoulderArmAtlas_source.png',OUT/'BoulderArmAtlas.blp')
