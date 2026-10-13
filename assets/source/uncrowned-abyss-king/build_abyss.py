"""Original Uncrowned Abyss King. Closed layered armor, fragment crown, greatsword, torn cloak.
No imported mesh, reference pixels or third-party texture data.
"""
from primitives import parts,mesh,ellipsoid,tube,leaf
from geometry import loft,ribbon,plaque
import math,json,pathlib,struct
from collections import defaultdict,deque
import numpy as np
from PIL import Image,ImageDraw
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['060b13','171725','292636','3d384d','8c99a7','233245','3f5369','a08b59','b3bec5','536071','bcc8cb','34475b','315b73','a3dbe9','02050a','d9e1df'];colors=[tuple(bytes.fromhex(x)) for x in PAL]
bones=[]
def bone(n,p,v):bones.append(dict(name=n,parent=p,pivot=list(v)));return len(bones)-1
bone('Root',-1,(0,0,0));bone('HeavyTorso',0,(0,0,76));bone('AbyssFace',1,(3,0,115))
bone('SwordUpperArm',1,(0,-24,104));bone('SwordForearm',3,(4,-34,83));bone('SwordFist',4,(14,-38,68));bone('Greatsword',5,(15,-38,70))
bone('FreeUpperArm',1,(0,24,104));bone('FreeForearm',7,(4,32,83));bone('ClawPalm',8,(14,34,60))
bone('LeftThigh',0,(0,12,61));bone('LeftShin',10,(3,14,36));bone('RightThigh',0,(0,-12,61));bone('RightShin',12,(0,-14,36))
bone('CloakUpper',1,(-13,0,106));bone('CloakLower',14,(-29,0,60));bone('CloakLeftTatter',14,(-21,25,78));bone('CloakRightTatter',14,(-21,-25,78))
bone('BrokenCrown',2,(-2,0,141));bone('CrownLooseShard',18,(-2,-17,145));bone('HairLeft',2,(-2,8,130));bone('HairRight',2,(-2,-8,130))
# A wide, waisted armored torso, a visible pelvis and two distinct armored legs.
loft('waisted black steel body',[(0,0,58,10,14),(1,0,70,13,17),(2,0,88,16,24),(1,0,105,14,24),(-1,0,112,10,17)],16,5,1)
loft('dark armored pelvis',[(0,0,53,11,15),(0,0,60,12,18),(0,0,69,12,16)],12,5,1)
# Deep convex breast plates provide large readable highlights, avoiding a flat chest shield.
for s in [-1,1]:
 plaque('broad forged pectoral '+str(s),[(s*y,z) for y,z in [(1,90),(4,108),(17,111),(25,102),(24,91),(12,84)]],17.5,7,6,1,ridge=4)
 tube('continuous bronze breast rim '+str(s),[(19,s*1,91),(21,s*4,107),(19,s*17,110),(15,s*25,101),(17,s*24,92)],[.62,.85,.75,.72,.35],7,1,n=5)
 for j in range(3):
  z=86-j*7
  ribbon('overlapping abdomen plate '+str(s)+' '+str(j),[(17,s*1,z),(19,s*8,z+2),(16,s*17,z+3)],[1.7,3.2,1.0],6 if j%2==0 else 5,1,normal=(1,0,0),thick=.9,ridge=1.4)
  tube('abdomen forged lip '+str(s)+' '+str(j),[(18,s*1,z-1),(20,s*8,z+1),(16.5,s*17,z+2)],[.35,.45,.2],10,1,n=5)
# Central chest rune is one cold crack set into a small faceted iron socket.
plaque('sternum iron inset',[(-3,94),(0,104),(3,94),(0,86)],23,2.3,5,1,ridge=1.1)
tube('single sternum cold fissure',[(24.5,0,102),(25.3,-.8,98),(25.2,.4,94),(24.5,-.2,89)],[.3,.22,.28,.06],13,1,n=5)
loft('high gorget',[(0,0,106,8,11),(0,0,114,8.7,10),(1,0,118,7.5,9)],12,5,1)
for s in [-1,1]:
 # Collar blades frame the neck; the crown remains a separate broken hovering object.
 ribbon('upstanding collar blade '+str(s),[(0,s*13,109),(-5,s*15,117),(-8,s*17,123)],[4.6,4.2,.25],5,1,normal=(1,0,0),thick=1.0,ridge=1.4)
 tube('collar edge '+str(s),[(3.8,s*13,109),(-1.2,s*15,117),(-8,s*17,123)],[.6,.48,.06],7,1,n=5)
# Wide three-tier pauldrons with swept points, substantial thickness and continuous edging.
for s,bi in [(-1,3),(1,7)]:
 ribbon('massive main pauldron '+str(s),[(0,s*19,109),(1,s*29,115),(-1,s*39,111),(-5,s*46,102)],[8,12,10,.8],6,bi,normal=(0,0,1),thick=2,ridge=3)
 for side in [-1,1]:
  tube('pauldron continuous rim '+str(s)+' '+str(side),[(side*7.5,s*19,111),(1+side*11,s*29,117),(-1+side*9,s*39,113),(-5,s*46,103)],[.72,.92,.77,.12],7,bi,n=5)
 for j in range(2):
  ribbon('lower pauldron lames '+str(s)+' '+str(j),[(2,s*(26+j*4),106-j*5),(4,s*(34+j*4),105-j*5),(1,s*(43+j*3),98-j*5)],[7,8,1],5 if j else 6,bi,normal=(0,0,1),thick=1.4,ridge=2)
 for j,(yy,z) in enumerate([(28,116),(38,113)]):
  tube('short swept shoulder spike '+str(s)+' '+str(j),[(-3,s*yy,z),(-8,s*(yy+4),z+9),(-14,s*(yy+6),z+13)],[2.9,1.5,.08],5,bi,n=6)
  tube('shoulder spike bright ridge '+str(s)+' '+str(j),[(-.7,s*yy,z+1),(-6.6,s*(yy+4),z+9.4),(-14,s*(yy+6),z+13)],[.5,.32,.035],10,bi,n=5)
 ellipsoid('pauldron heavy rivet '+str(s),(11,s*30,111),(1.4,1.4,1.4),7,bi,n=7,k=3)
# Fully armored arms: bicep socket, elbow point, broad gauntlet and protected knuckles.
for s,upper,fore,hand in [(-1,3,4,5),(1,7,8,9)]:
 tube('arm understructure '+str(s),[(0,s*25,102),(1,s*30,91),(4,s*34,83)],[6.5,5.2,4.7],5,upper,n=9)
 ellipsoid('angular elbow joint '+str(s),(4,s*34,83),(5.2,5.7,5.5),11,fore,n=8,k=4)
 endz=68 if s==-1 else 60;endy=38 if s==-1 else 34
 tube('tapered iron vambrace '+str(s),[(4,s*34,84),(9,s*37,76),(14,s*endy,endz)],[5.5,6,3.8],6,fore,n=9)
 ribbon('vambrace front carapace '+str(s),[(9,s*35,84),(15,s*38,76),(17,s*endy,endz)],[4.5,5.3,2.6],5,fore,normal=(1,0,0),thick=.9,ridge=1.5)
 tube('vambrace bronze bevel '+str(s),[(12,s*31,83),(18,s*33,76),(20,s*(endy-2),endz)],[.55,.62,.24],7,fore,n=5)
 ellipsoid('heavy gauntlet palm '+str(s),(15,s*endy,endz-2),(4.8,5.4,6),5,hand,n=9,k=4)
 if s==-1:
  for j in range(4):
   y=-42+j*2.5;tube('closed sword gripping finger '+str(j),[(17,y,70),(20,y,68),(19,y,65),(15,y,65)],[1.0,1.3,1.1,.65],10,hand,n=5)
  tube('clasped sword thumb',[(13,-33,69),(19,-33,68),(19,-36,70)],[1.6,1.3,.5],7,hand,n=6)
 else:
  for j in range(5):
   y=29+j*2.3;bi=bone('ClawFinger'+str(j),hand,(16,y,58))
   tube('separate curled claw '+str(j),[(16,y,58),(19,y+(.3*j),53),(21,y+(.3*j),48+abs(j-2)),(19,y+.2*j,46+abs(j-2))],[1.25,1.1,.85,.15],10,bi,n=5)
# Broad belt and one pointed plated tabard instead of a robe hiding all the legs.
loft('thick hip girdle',[(0,0,58,12,17),(0,0,64,13,18),(0,0,68,12,17)],12,11,1)
plaque('waist clasp diamond',[(-5,62),(0,68),(5,62),(0,57)],15,3,7,1,ridge=2)
for s in [-1,1]:
 ribbon('segmented hip skirt '+str(s),[(7,s*13,63),(9,s*20,55),(9,s*24,43),(7,s*26,35)],[7.5,9,7,.4],5,10 if s==1 else 12,normal=(1,0,0),thick=1.3,ridge=2)
 tube('hip skirt unbroken edge '+str(s),[(13,s*13,64),(16,s*20,55),(15,s*24,43),(7,s*26,35)],[.7,.66,.5,.1],7,10 if s==1 else 12,n=5)
for s,thigh,shin in [(1,10,11),(-1,12,13)]:
 x=3 if s==1 else 0
 tube('heavy thigh armor '+str(s),[(0,s*12,61),(x,s*14,49),(x,s*14,37)],[7.3,7.6,5.3],6,thigh,n=10)
 ribbon('long thigh front plate '+str(s),[(8,s*12,59),(11,s*14,49),(10,s*14,39)],[5.3,6,3.5],5,thigh,normal=(1,0,0),thick=1.2,ridge=1.6)
 ellipsoid('kneecap underjoint '+str(s),(x+2,s*14,36),(6,6.5,5),5,shin,n=9,k=4)
 plaque('pointed kneecap '+str(s),[(s*14-5,37),(s*14,44),(s*14+5,37),(s*14+3,31),(s*14-3,31)],x+9,3,6,shin,ridge=2.0)
 tube('armored lower leg '+str(s),[(x,s*14,35),(x-1,s*15,22),(x+1,s*16,10)],[5.2,6,4.3],5,shin,n=10)
 ribbon('ridged broad greave '+str(s),[(x+6,s*14,34),(x+8,s*15,23),(x+7,s*16,10)],[4.8,5.8,3.7],6,shin,normal=(1,0,0),thick=1.3,ridge=2)
 for edge in [-1,1]:tube('greave bronze edge '+str(s)+' '+str(edge),[(x+6,s*14+edge*4.7,34),(x+7,s*15+edge*5.7,23),(x+7,s*16+edge*3.5,10)],[.48,.60,.25],7,shin,n=5)
 # A compact pointed boot, connected to the shin and resting above the floor.
 loft('solid sabaton '+str(s),[(x+5,s*16,3.3,9,6),(x+5,s*16,6,10,6.5),(x+3,s*16,11,7,5)],10,5,shin)
 ribbon('sabaton top plates '+str(s),[(x+14,s*16,5),(x+10,s*16,9),(x+2,s*16,11)],[4,5.5,4],6,shin,normal=(0,0,1),thick=.6,ridge=.9)
# One large continuous closed cape with a genuinely irregular torn hem and broad cloth folds.
R=8;C=15;v=[];uv=[]
for back in [False,True]:
 for j in range(R):
  u=j/(R-1)
  for i in range(C):
   t=-1+2*i/(C-1);width=28+27*u
   x=-15-27*u-5*math.sin(math.pi*u)+(2.4+u*2)*math.cos(t*math.pi*3)
   z=108-92*u+(0 if j<R-1 else [7,1,8,0,10,3,9,0,8,2,12,1,9,0,8][i])
   if abs(t)>.85:z+=u*8
   v.append((x+(.55 if back else -.55),t*width,z));uv.append([i/(C-1),u])
f=[];fc=[];off=R*C
for back in [False,True]:
 o=off if back else 0
 for j in range(R-1):
  for i in range(C-1):
   a=o+j*C+i;b=a+1;c=a+C;d=c+1
   f.extend([(a,c,d),(a,d,b)] if back else [(a,b,d),(a,d,c)]);fc.extend([2 if i%4 in [0,1] else 1]*2)
edge=list(range(C))+[j*C+C-1 for j in range(1,R)]+list(range((R-1)*C+C-2,(R-1)*C-1,-1))+[j*C for j in range(R-2,0,-1)]
for i,a in enumerate(edge):b=edge[(i+1)%len(edge)];f.extend([(a,b+off,a+off),(a,b,b+off)]);fc.extend([1,1])
mesh('continuous great tattered cloak',v,f,2,14,True,fc);parts[-1]['uvs']=uv
weights=[]
for back in [False,True]:
 for j in range(R):
  for i in range(C):
   if j==0:ids=[1]
   elif j<3:ids=[14]
   elif i<2:ids=[17]
   elif i>C-3:ids=[16]
   elif j==3:ids=[14,15]
   else:ids=[15]
   weights.append(ids)
parts[-1]['vertexBones']=weights
# Two detached-looking side streamers remain attached at the shoulders and widen the silhouette.
for s,bi in [(-1,17),(1,16)]:
 ribbon('outer torn cape streamer '+str(s),[(-13,s*28,107),(-23,s*39,87),(-34,s*53,61),(-46,s*61,33),(-52,s*57,19)],[5,7,8,6,.25],1,bi,normal=(1,0,0),thick=.5,ridge=1.8)
# Long ashen hair, tucked behind temples and over the back, with discrete chiseled locks.
ellipsoid('dark rear skull',(1,0,127),(9.7,10,14),0,2,n=12,k=5)
for s,bi in [(-1,21),(1,20)]:
 for j in range(4):
  y=s*(7+j*1.6);x=2-j*2
  ribbon('swept silver hair lock '+str(s)+' '+str(j),[(x,y,137),(x-3,s*(11+j),129),(x-6,s*(12+j*1.6),118),(x-9,s*(10+j*2.3),108-j*2)],[1.6,2.5,2.1,.12],4 if j%2==0 else 9,bi,normal=(1,0,0),thick=.7,ridge=1.3)
# Layered, dimensional deathly face, not a printed flat mask: cheek arches frame recessed sockets.
plaque('broad ashen forehead',[(-8,132),(-7.5,137),(-4,142),(1,143),(6,140),(8,136),(7.5,132),(0,131)],15.5,6,8,2,ridge=3)
for s in [-1,1]:
 plaque('recessed abyss eye '+str(s),[(s*y,z) for y,z in [(1,128.5),(2.2,132),(6.8,132.9),(8.4,130.5),(6.5,127),(2.8,126)]],18.4,1.1,14,2,ridge=.1)
 ribbon('cruel angular brow '+str(s),[(22,s*.9,129.8),(22.7,s*4,132),(20.7,s*7.8,134),(16,s*9.5,132.5)],[.55,1.5,1.45,.3],8,2,normal=(1,0,0),thick=1,ridge=1.25)
 tube('slender icy eye '+str(s),[(19.5,s*2.2,128.4),(19.7,s*4.2,129.2),(19.1,s*6.6,130.1)],[.13,.38,.055],13,2,n=5)
 ribbon('pronounced cheek bone '+str(s),[(19.8,s*8.5,129),(22,s*8.3,125.7),(22,s*6,123),(20.3,s*5.4,120)],[.6,1.9,1.1,.35],8,2,normal=(1,0,0),thick=1,ridge=1.0)
 plaque('sunken cheek shadow '+str(s),[(s*y,z) for y,z in [(5,124),(8,126),(8,119),(5,116),(3.8,119)]],18.5,2.5,9,2,ridge=.3)
 # Iron temple guards have sharper material value than the pallid face.
 ribbon('blade helmet temple '+str(s),[(11,s*9,139),(13,s*11.3,132),(14,s*11,122),(17,s*9,117)],[2.0,2.8,2.4,.2],5,2,normal=(1,0,0),thick=1.2,ridge=1.5)
 tube('temple bright edge '+str(s),[(13,s*7.7,139),(15,s*9.2,132),(16,s*9.3,124),(17,s*9,117)],[.45,.55,.35,.06],7,2,n=5)
# Real angular nose bridge and nostrils project several units from the eye cavities.
plaque('angular nose bridge',[(-1.4,130.5),(0,133),(1.4,130.5),(2.2,123.7),(0,121.5),(-2.2,123.7)],23,3.8,8,2,ridge=2.2)
for s in [-1,1]:plaque('dark nostril '+str(s),[(s*2.2-.65,123.6),(s*2.2+.65,123.3),(s*2.2,122.2)],24.9,.5,14,2,ridge=.03)
ellipsoid('deep snarling mouth',(18.8,0,117.5),(3,5.5,3.3),14,2,n=10,k=4)
ribbon('strong squared mandible',[(17,-7.5,122),(20.8,-6.4,117),(23,-3.4,113.3),(23,3.4,113.3),(20.8,6.4,117),(17,7.5,122)],[.4,1.5,1.8,1.8,1.5,.4],8,2,normal=(1,0,0),thick=1.2,ridge=1.1)
for j,y in enumerate([-4,-2.3,-.75,.75,2.3,4]):
 top=120.2-abs(y)*.10;length=2.3 if j not in [0,5] else 3.5
 plaque('uneven bared tooth '+str(j),[(y-.64,top),(y+.64,top),(y+.45,top-length),(y-.4,top-length)],22,1.3,15,2,ridge=.25)
# Central scalp plate and two short broken edges bind the face to the crown silhouette.
ribbon('split scalp iron plate',[(9,0,140),(14,0,142),(17,0,138),(19,0,135)],[3.8,4.4,3,.2],5,2,normal=(1,0,0),thick=1,ridge=1.1)
# Crown remnants are spaced 3D annular sectors, never a copied full crescent halo.
def crown_arc(name,a0,a1,z,r,bi):
 n=4;v=[]
 for zz in [z-.8,z+1.2]:
  for i in range(n+1):
   a=math.radians(a0+(a1-a0)*i/n)
   for rr in [r-1.4,r+1.4]:v.append((-2+rr*math.cos(a),rr*math.sin(a),zz+.5*math.sin(a)))
 o=(n+1)*2;f=[]
 for i in range(n):
  a=i*2;b=a+1;c=a+2;d=a+3;f.extend([(a,c,d),(a,d,b),(a+o,d+o,c+o),(a+o,b+o,d+o),(a,a+o,c+o),(a,c+o,c),(b,d+o,b+o),(b,d,d+o)])
 f.extend([(0,1,o+1),(0,o+1,o),(2*n,2*n+o+1,2*n+1),(2*n,2*n+o,2*n+o+1)])
 mesh(name,v,f,7,bi,False)
for j,(a0,a1,z) in enumerate([(8,43,146),(61,96,147),(119,159,146),(181,216,146),(238,273,147),(300,335,146)]):
 bi=19 if j==4 else 18;crown_arc('floating broken crown sector '+str(j),a0,a1,z,16.3,bi)
 a=math.radians((a0+a1)/2);x=-2+16.3*math.cos(a);y=16.3*math.sin(a)
 tube('ragged crown spike '+str(j),[(x,y,z),(x-1,y*1.1,z+5),(x-3,y*1.08,z+9+(j%2)*3)],[1.75,1.2,.05],5,bi,n=5)
# A substantial closed tapered broadsword hangs from the right fist.
# Local blade front points towards +X; the lower tip remains above the ground.
def sword_blade():
 v=[];zs=[59,51,18,5];ws=[6.3,7.2,5.5,.12]
 for z,w in zip(zs,ws):v.extend([(15,-38-w,z),(18,-38,z),(15,-38+w,z),(12,-38,z)])
 f=[]
 for j in range(3):
  for i in range(4):a=j*4+i;b=j*4+(i+1)%4;f.extend([(a,b,b+4),(a,b+4,a+4)])
 f.extend([(0,2,1),(0,3,2),(12,13,14),(12,14,15)]);mesh('monolithic ridged greatsword blade',v,f,6,6,False)
 parts[-1]['facecols']=[6 if i%4<2 else 11 for i in range(len(f))]
sword_blade()
tube('greatsword grip',[(15,-38,61),(15,-38,74),(15,-38,80)],[1.9,1.8,1.7],1,6,n=8)
ellipsoid('greatsword pommel',(15,-38,81.5),(3,3,4),7,6,n=8,k=4)
for s in [-1,1]:
 tube('swept sword crossguard '+str(s),[(15,-38,59),(15,-38+s*9,62),(14,-38+s*14,60),(13,-38+s*17,55)],[2.5,2.8,1.9,.13],7,6,n=6)
 tube('sword bevel edge '+str(s),[(15.7,-38+s*6.1,58),(15.7,-38+s*7.0,51),(15.6,-38+s*5.3,18),(15,-38,5)],[.4,.5,.36,.025],10,6,n=5)
plaque('crossguard iron jewel',[(-41,59),(-38,65),(-35,59),(-38,55)],19,3,5,6,ridge=1.5)
tube('one cold greatsword fissure',[(18.2,-37.9,49),(18.4,-38.7,43),(18.4,-37.5,34),(18.2,-38.3,28),(18.1,-38,21)],[.2,.28,.24,.2,.04],13,6,n=5)
# Small shoulder fissure, leaving the large majority of armor unlit.
tube('shoulder restrained cold fissure',[(9,-28,116),(9.8,-31,115),(8,-34,114),(8.5,-36,112)],[.16,.2,.16,.04],12,3,n=5)
# Validate all components and set a consistent outward winding before export.
exec((ROOT/'seal_geometry.py').read_text())
seqs=[('Stand',0,2400,True),('Walk',2500,3700,True),('Attack',3800,5300,False),('Stand Hit',5400,6000,False),('Death',6100,8100,False),('Portrait',8200,10600,True)]
def quat(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(21):
   u=i/20;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);c=1-math.cos(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.38*c
    if bi==2:rot=quat([0,0,1],.021*w)
    if bi in [3,7]:rot=quat([1,0,0],(.008 if bi==3 else -.012)*w)
    if bi in [8,9]:rot=quat([0,1,0],.025*w)
    if bi in [14,15]:rot=quat([0,1,0],(.018 if bi==14 else .032)*w)
    if bi in [16,17]:rot=quat([1,0,0],(.045 if bi==16 else -.045)*w)
    if bi in [18,19]:tr[2]=.35*c;rot=quat([0,0,1],(.028 if bi==18 else -.025)*w)
    if bi in [20,21]:rot=quat([1,0,0],.025*w)
    if bi>=22:rot=quat([0,1,0],.035*w)
   elif name=='Walk':
    if bi==1:tr[2]=1.0*c;rot=quat([1,0,0],.022*w)
    if bi in [10,12]:
     phase=1 if bi==10 else -1;tr=[4.8*w*phase,0,max(0,phase*math.cos(2*math.pi*u))*2.1];rot=quat([0,1,0],-.07*w*phase)
    if bi in [11,13]:rot=quat([0,1,0],.035*w*(1 if bi==11 else -1))
    if bi in [3,7]:rot=quat([0,1,0],.035*w*(1 if bi==3 else -1))
    if bi==6:rot=quat([0,1,0],-.02*w)
    if bi in [14,15,16,17]:rot=quat([0,1,0],-.04*w)
    if bi in [20,21]:rot=quat([0,1,0],.05*w)
    if bi in [18,19]:tr[2]=.4*c
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==1:rot=quat([0,0,1],-.13*k);tr=[3*k,0,.8*k]
    if bi==2:rot=quat([0,0,1],.1*k)
    if bi==3:rot=quat([0,1,0],-.65*k)
    if bi==4:rot=quat([0,1,0],-.5*k)
    if bi==6:rot=quat([0,1,0],-.25*k)
    if bi in [7,8]:rot=quat([0,1,0],.15*k)
    if bi in [14,15,16,17]:rot=quat([0,1,0],-.045*k)
    if bi>=22:rot=quat([0,1,0],.10*k)
   elif name=='Stand Hit':
    k=math.sin(math.pi*u)*math.exp(-2*u)
    if bi==1:tr=[-4*k,0,0];rot=quat([0,1,0],-.08*k)
    if bi==2:rot=quat([0,1,0],-.14*k)
    if bi in [14,15,16,17]:rot=quat([0,1,0],.055*k)
   else:
    e=u*u*(3-2*u)
    if bi==1:tr=[-4*e,0,-20*e];sc=[1,1,1-.35*e]
    if bi==2:rot=quat([0,1,0],.42*e)
    if bi in [3,7]:rot=quat([0,1,0],.14*e)
    if bi in [4,8]:rot=quat([0,1,0],.2*e)
    if bi==6:rot=quat([0,1,0],-.15*e);tr[2]=16*e
    if bi in [10,12]:sc=[1,1,1-.16*e];tr[2]=-1*e
    if bi in [14,15,16,17]:sc=[1,1,1-.30*e]
    if bi in [18,19]:tr[2]=-3*e;rot=quat([1,0,0],.15*e)
    if bi in [20,21]:rot=quat([0,1,0],.12*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'abyss-source.json').write_text(json.dumps(dict(name='UncrownedAbyssKing_Original_Review_v1',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))
# Broad original diffuse value painting. No copied texture pixels, no noise/clay PBR.
S=128;atlas=Image.new('RGB',(512,512));Y,X=np.mgrid[0:S,0:S];xx=X/(S-1);yy=Y/(S-1)
for k,base in enumerate(colors):
 light=.72+.40*(1-yy)
 if k in [1,2,3]:light=.40+.64*np.exp(-((xx-.40)/.26)**2)+.17*(1-yy)-.10*np.exp(-((xx-.90)/.07)**2)
 elif k in [5,6,11]:light=.62+.40*(1-yy)+.45*np.exp(-((xx-.30)/.24)**2)
 elif k in [7,10]:light=.60+.32*(1-yy)+.29*np.exp(-((xx-.32)/.22)**2)
 elif k in [4,8,9,15]:light=.56+.46*(1-yy)+.24*np.exp(-((xx-.25)/.26)**2)
 elif k in [0,12,13,14]:light=np.ones((S,S))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if k in [1,2,3]:
  d.polygon([(5,6),(17,32),(12,72),(20,119),(7,120)],fill=tuple(int(v*.48) for v in base));d.polygon([(110,6),(102,43),(110,85),(106,119),(120,120),(120,6)],fill=tuple(int(v*.4) for v in base))
  d.line([(14,114),(110,114)],fill=tuple(int(v*.83) for v in base),width=3)
 elif k in [5,6,11]:
  d.line([(9,12),(115,12),(115,116)],fill=(100,120,143),width=6,joint='curve');d.line([(17,22),(104,22),(104,106)],fill=(23,34,48),width=7,joint='curve');d.line([(24,31),(95,31)],fill=(63,82,104),width=4)
 elif k in [7,10]:
  d.line([(10,12),(115,12),(115,115)],fill=tuple(min(255,int(v*1.32)) for v in base),width=6,joint='curve');d.line([(18,24),(104,24),(104,107)],fill=tuple(int(v*.49) for v in base),width=5,joint='curve')
 elif k in [4,8,9,15]:
  d.polygon([(8,9),(19,23),(16,78),(24,117),(9,120)],fill=tuple(int(v*.50) for v in base));d.line([(22,15),(26,46),(23,82),(29,112)],fill=tuple(min(255,int(v*1.22)) for v in base),width=3)
  if k in [8,15]:
   d.line([(101,14),(95,43),(103,71),(96,109)],fill=(63,77,87),width=2)
  if k==4:
   for x in [37,58,82,100]:d.line([(x,8),(x-3,48),(x+1,88),(x-4,120)],fill=(61,74,88),width=2)
 atlas.paste(tile,((k%4)*S,(k//4)*S))
atlas.save(OUT/'UncrownedAbyssKingAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(10):
 sz=max(1,512>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'UncrownedAbyssKingAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,512,512,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps({'triangles':sum(len(p['faces']) for p in parts),'bones':len(bones),'parts':len(parts)}))
