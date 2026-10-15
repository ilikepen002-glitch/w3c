"""Original tall spiral-shell companion with flexible low foot and articulated eye stalks."""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['353025','66513a','977344','b89861','c6af79','e3d4a2','877d50','6b6543','ab9863','c69b53','786a47','d3b878','e5ce91','181e19','ddaf48','fff0b8'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='SoftFoot',parent=0,pivot=[0,0,10]),dict(name='SpiralShell',parent=1,pivot=[-7,0,24]),dict(name='SlugHead',parent=1,pivot=[25,0,15]),dict(name='LeftEyeStalk',parent=3,pivot=[40,6,23]),dict(name='RightEyeStalk',parent=3,pivot=[40,-6,23]),dict(name='LowTail',parent=1,pivot=[-27,0,10])]
ellipsoid('low long ochre foot',(2,0,8.5),(40,13,6.3),6,1,n=14,k=4)
ellipsoid('pale crawling sole',(6,0,5.9),(36,13.5,3),5,1,n=14,k=3)
tube('broad rising neck',[(22,0,10),(31,0,14),(38,0,19)],[10,11,10],6,3,n=10)
ellipsoid('rounded blunt snail head',(41,0,19),(13,12,9),6,3,n=12,k=4)
ellipsoid('pale short snail muzzle',(49,0,16.5),(7.5,8,5),4,3,n=10,k=3)
tube('short quiet mouth',[(51,-6,15),(54,0,14),(51,6,15)],[.45,.5,.45],0,3,n=5)
tube('tapering soft tail',[(-27,0,10),(-41,0,8),(-50,0,5.5)],[9,6,.25],6,6,n=9)
# Upright full shell and two real raised spiral ridges; no billboard or fake painted-only coil.
ellipsoid('tall nautilus sandstone shell',(-8,0,35),(24,16.7,27),2,2,n=16,k=7)
for s in [-1,1]:
 cs=[];rs=[]
 for i in range(53):
  u=i/52;a=5*math.pi*u;r=23*(1-u)+1.3
  x=-8+r*math.cos(a);z=35+r*math.sin(a)
  y=s*(16.7*math.sqrt(max(.04,1-((x+8)/25)**2-((z-35)/28)**2))+.55)
  cs.append((x,y,z));rs.append(1.85-.85*u)
 tube('raised spiral shell ridge '+str(s),cs,rs,11,2,n=5)
 # Separate eye stalks have a small dark end-cap, no large mammal eyes.
 bi=4 if s==1 else 5
 tube('long curved eye stalk '+str(s),[(40,s*6,23),(42,s*9,33),(40,s*12,44)],[2.8,2.25,1.7],6,bi,n=7)
 ellipsoid('small dark eye tip '+str(s),(40,s*12,45),(3.2,3.3,3.8),0,bi,n=8,k=4)
 ellipsoid('small amber eye glint '+str(s),(42.8,s*12,45.6),(1.05,1.8,1.9),14,bi,n=6,k=3)
 ellipsoid('obsidian eye pupil '+str(s),(43.7,s*12,45.7),(.25,.75,1.1),13,bi,n=6,k=3)
 ellipsoid('gold eye catchlight '+str(s),(43.95,s*12.3,46.35),(.15,.32,.36),15,bi,n=6,k=3)
 tube('short feeler '+str(s),[(46,s*7,18),(54,s*12,20),(57,s*15,21)],[1.3,.9,.12],6,3,n=6)
 for x in [-18,-4,10,24]:
  # A scalloped soft foot edge makes the crawling silhouette clear.
  ellipsoid('soft foot scallop '+str(s)+' '+str(x),(x,s*11.8,7),(8,2.7,2.6),4,1,n=7,k=3)
seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:sc=[1,1+.009*(1-math.cos(2*math.pi*u)),1]
    if bi==2:rot=q([1,0,0],.012*w)
    if bi==3:rot=q([0,0,1],.035*w)
    if bi in [4,5]:rot=q([1,0,0],(.07 if bi==4 else -.07)*w)
    if bi==6:rot=q([0,0,1],.04*w)
   elif name=='Walk':
    if bi==1:sc=[1+.035*w,1,1];tr[2]=.28*(1-math.cos(4*math.pi*u))
    if bi==2:rot=q([1,0,0],.022*w)
    if bi==3:tr=[1.3*w,0,0];rot=q([0,0,1],.035*w)
    if bi in [4,5]:rot=q([0,1,0],.06*w)
    if bi==6:rot=q([0,0,1],.055*w)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==3:tr=[5*k,0,1*k];rot=q([0,1,0],-.09*k)
    if bi in [4,5]:rot=q([0,1,0],.22*k)
    if bi==2:rot=q([0,1,0],-.045*k)
   else:
    e=3*u*u-2*u*u*u
    if bi==1:sc=[1,1,1-.17*e]
    if bi==2:rot=q([1,0,0],.09*e)
    if bi==3:tr=[-7*e,0,-1.5*e];sc=[1-.20*e,1,1]
    if bi in [4,5]:rot=q([0,1,0],-.7*e);sc=[1,1,1-.30*e]
    if bi==6:sc=[1-.17*e,1,1]
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'earth_snail-source.json').write_text(json.dumps(dict(name='SandSpiralSnail_Original_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))

# Refined atlas is the persisted built-in imagegen output. Resize/BLP encoding only.
import runpy
runpy.run_path(str(ROOT.parents[4]/'tools/EncodeWaterEarthAtlas.py'))['encode'](OUT/'atlas-refined-imagegen.png',OUT/'SandSpiralAtlas_source.png',OUT/'SandSpiralAtlas.blp')
