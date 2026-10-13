"""Original Eclipse Spellweaver: sculpted mask, layered robes, posed hands and broken moon.
Art is original, no imported model data.  Classic MDX800 source schema only.
"""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
from collections import defaultdict,deque
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['060911','1e142c','3f234c','502b5b','6c4175','1a273d','2c3d54','ac7f2d','c9bc8e','695638','e5ba55','1a283e','6025a5','d9b8ff','03040b','f2e5b5'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[]
def bone(name,parent,pivot):bones.append(dict(name=name,parent=parent,pivot=list(pivot)));return len(bones)-1
bone('Root',-1,(0,0,0));bone('Torso',0,(0,0,62));bone('PorcelainMask',1,(5,0,88))
bone('RaisedUpperArm',1,(0,16,81));bone('RaisedForearm',3,(4,28,91));bone('RaisedPalm',4,(17,32,111))
bone('ExtendedUpperArm',1,(0,-16,81));bone('ExtendedForearm',6,(8,-29,72));bone('ExtendedPalm',7,(23,-35,81))
bone('RobeLeft',1,(-1,8,65));bone('RobeRight',1,(-1,-8,65));bone('RobeBack',1,(-9,0,66))
bone('IndependentMoon',0,(-9,0,101));bone('MoonUpperShard',12,(-9,22,124));bone('MoonLowerShard',12,(-9,-30,95))
# Closed horizontal-ring loft used for clothing and the sculptural waist/shoulders.
def loft(name,rings,n,col,bi,pleat=0):
 v=[];uv=[]
 for j,(cx,cy,z,rx,ry) in enumerate(rings):
  for i in range(n):
   a=2*math.pi*i/n;rr=1+pleat*math.cos(a*6+j*.17);zz=z+(2.3*math.sin(a*5) if j==0 else 0)
   v.append((cx+rx*math.cos(a)*rr,cy+ry*math.sin(a)*rr,zz));uv.append([i/n,j/(len(rings)-1)])
 f=[]
 for j in range(len(rings)-1):
  for i in range(n):a=j*n+i;b=j*n+(i+1)%n;f.extend([(a,b,b+n),(a,b+n,a+n)])
 for i in range(1,n-1):f.extend([(0,i+1,i),((len(rings)-1)*n,(len(rings)-1)*n+i,(len(rings)-1)*n+i+1)])
 mesh(name,v,f,col,bi,True);parts[-1]['uvs']=uv
# Curved, tapered cloth/metal ribbons are actual closed meshes, with a center ridge.
def ribbon(name,cs,widths,col,bi,normal=(1,0,0),thick=.55,ridge=.7):
 vv=[];uv=[];N=len(cs);nor=np.array(normal,float);nor/=np.linalg.norm(nor)
 for back in [False,True]:
  for j,c in enumerate(cs):
   t=np.array(cs[min(N-1,j+1)],float)-np.array(cs[max(0,j-1)],float);t/=np.linalg.norm(t);side=np.cross(t,nor);side/=np.linalg.norm(side);nn=np.cross(side,t);nn/=np.linalg.norm(nn)
   for u in [-1,0,1]:
    vv.append((np.array(c)+side*widths[j]*u+nn*((-thick if back else thick)+(0 if back else ridge*(1-abs(u))))).tolist());uv.append([(u+1)/2,j/(N-1)])
 f=[];fc=[];off=N*3
 for back in [False,True]:
  o=off if back else 0
  for j in range(N-1):
   for k in range(2):
    a=o+j*3+k;b=a+1;c=a+3;d=b+3;f.extend([(a,c,d),(a,d,b)] if back else [(a,b,d),(a,d,c)]);fc.extend([col,col])
 edge=[j*3 for j in range(N)]+[(N-1)*3+1,(N-1)*3+2]+[j*3+2 for j in range(N-2,-1,-1)]+[1]
 for i,a in enumerate(edge):b=edge[(i+1)%len(edge)];f.extend([(a,b+off,a+off),(a,b,b+off)]);fc.extend([col,col])
 mesh(name,vv,f,col,bi,False,fc);parts[-1]['uvs']=uv
# Long continuous robe, a narrow waist, sculpted upper torso and a flowing hem.
loft('continuous deep purple robe',[(0,0,14,17,21),(-3,0,29,17,19),(-2,0,47,12,14),(0,0,61,9,11),(3,0,74,11,15),(1,0,83,10,18),(3,0,89,6,8)],24,2,1,.065)
loft('waisted dark cuirass',[(3,0,59,9,11),(7,0,66,10,12),(8,0,76,10,14),(5,0,84,8,13)],14,5,1,.025)
ellipsoid('hooded angular head',(7,0,99),(9,10,14),1,2,n=16,k=7)
# Long cloak strips make a controlled asymmetric hanging silhouette.
for i,(ang,length,width) in enumerate([(-2.6,51,7),(-1.9,55,7),(-1.15,48,6),(-.5,50,5),(.45,54,5),(1.1,48,6),(1.9,55,7),(2.6,50,7)]):
 bi=9 if math.sin(ang)>0 else 10
 if math.cos(ang)<-.5:bi=11
 cs=[];ws=[]
 for j in range(8):
  u=j/7;rad=9+13*u;cs.append((rad*math.cos(ang)-4*u+3*math.sin(math.pi*u),rad*math.sin(ang),65-length*u+1.3*math.sin(3*u)));ws.append(max(.6,width*(.6+.5*u)*(1 if j<7 else .17)))
 ribbon('layered pointed robe panel '+str(i),cs,ws,3 if i%3 else 4,bi,normal=(math.cos(ang),math.sin(ang),0),thick=.38,ridge=.65)
# Front split ceremonial stole, its metal edge and engraved moon clasp.
for s in [-1,1]:
 cs=[(16,s*7,81),(17,s*6,68),(14,s*5,55),(16,s*7,39),(17,s*10,22),(19,s*12,12)]
 ribbon('front long priest stole '+str(s),cs,[3.3,3,3.2,4.5,5,.3],1,9 if s==1 else 10,normal=(1,0,0),thick=.50,ridge=.4)
 tube('stole pale metal edge '+str(s),[(x+.7,y+s*2.6,z) for x,y,z in cs[:-1]],[.45,.42,.40,.35,.20],7,9 if s==1 else 10,n=5)
# A genuinely three-dimensional broken-bone face. The eyes and mouth are recessed
# between separate solid brow, cheek, forehead and jaw meshes, never a flat mask.
def plaque(name,yz,x,depth,col,bi=2,ridge=.6):
    # Convex chiseled slab, closed front/back fan with broad hand-painted faces.
    n=len(yz);cy=sum(y for y,z in yz)/n;cz=sum(z for y,z in yz)/n
    vv=[(x,y,z) for y,z in yz]+[(x+ridge,cy,cz)]+[(x-depth,y,z) for y,z in yz]+[(x-depth,cy,cz)]
    ff=[]
    for i in range(n):
        j=(i+1)%n;ff.extend([(n,i,j),(2*n+1,n+1+j,n+1+i),(i,n+1+i,n+1+j),(i,n+1+j,j)])
    mesh(name,vv,ff,col,bi,False)
# Angular broken forehead with the skull's temples tucked beneath a dark hood.
plaque('fractured cranial forehead',[(-7.8,105),(-7.5,109),(-4,113),(0,114),(4,112),(7.3,108),(7.0,105),(0,103.3)],16.3,5,8,ridge=2.2)
for sign in [-1,1]:
    # Pure dark actual recessed eye socket. Brow and cheekbone sit in front of it.
    yz=[(sign*y,z) for y,z in [(1.1,102.6),(2.5,105),(6.8,106.6),(8,104.5),(6.8,101),(3.0,99.8)]]
    plaque('deep hollow eye socket '+str(sign),yz,17.7,.8,14,ridge=.0)
    ribbon('heavy pointed skeletal brow '+str(sign),[(20.8,sign*.8,103.4),(21.5,sign*3.7,105.4),(19.8,sign*7.5,107.2),(15.0,sign*9,105.4)],[.42,1.35,1.3,.16],8,2,normal=(1,0,0),thick=.8,ridge=1.0)
    # A long needle of purple in the darkness, not a round pet eye.
    tube('narrow violet eye glare '+str(sign),[(18.7,sign*2.6,102.6),(18.65,sign*4.1,103.2),(18.2,sign*6,104)],[.13,.34,.05],13,2,n=5)
    ribbon('razor cheek arch '+str(sign),[(18.8,sign*7.7,102.4),(21.0,sign*7.7,99.0),(20.2,sign*5.8,96.8),(19,sign*4.9,93.8)],[.6,1.6,1.15,.2],8,2,normal=(1,0,0),thick=.65,ridge=.9)
    ribbon('shadowed skull temple '+str(sign),[(13.8,sign*9,107),(13.5,sign*10,101),(14.9,sign*8,96.5)],[1.2,1.65,.30],9,2,normal=(1,0,0),thick=.9,ridge=.5)
# Skeletal nose: a dark triangular nasal cavity with two small broken bone edges.
plaque('dark nasal cavity',[(-1.6,97),(0,102.2),(1.6,97),(0,95.8)],20.15,1,14,ridge=.05)
for sign in [-1,1]:
    tube('broken nasal bone edge '+str(sign),[(21,sign*.35,103),(21.4,sign*.8,100.8),(21.6,sign*1.7,97.5)],[.6,.58,.13],8,2,n=5)
# A dark mouth volume visible through the separated, uneven teeth.
ellipsoid('hollow mouth cavity',(17.7,0,93.2),(2.3,5.5,4.0),14,2,n=10,k=4)
ribbon('thick broken mandible',[(16.8,-6,96),(19.8,-5.5,91.0),(21.0,-2.0,88.3),(21.0,2,88.7),(19.8,5.5,91.5),(16.8,6,96)],[.40,1.2,1.55,1.4,1.2,.3],8,2,normal=(1,0,0),thick=.9,ridge=.8)
for j,y in enumerate([-4.15,-2.5,-.85,.85,2.5,4.15]):
    top=96.5-abs(y)*.11;length=[2.2,3.4,2.6,2.5,3.0,1.45][j]
    plaque('irregular exposed upper tooth '+str(j),[(y-.69,top),(y+.69,top-.1),(y+.44,top-length),(y-.50,top-length+.13)],21.0,1.5,8,ridge=.27)
for sign in [-1,1]:
    plaque('short lower fang '+str(sign),[(sign*2.1-.6,89.8),(sign*2.1+.6,89.8),(sign*2.1+.16,92.5)],21.3,1.5,15,ridge=.23)
# A cracked black-iron horn diadem, offset from the independent crescent back ring.
for sign in [-1,1]:
    tube('swept horn diadem '+str(sign),[(5,sign*8,109),(1,sign*12,115),(-1,sign*12.5,122),(1,sign*10.5,126)],[2.4,2.0,1.15,.045],5,2,n=6)
    tube('gold horn diadem edge '+str(sign),[(7.1,sign*8,109),(2.7,sign*12,115),(.2,sign*12.5,122),(1.05,sign*10.5,126)],[.50,.43,.20,.03],10,2,n=5)
    ribbon('bone forehead fracture '+str(sign),[(18.6,sign*1.0,112),(18.0,sign*2.2,109.8),(19.1,sign*1.7,108),(18.6,sign*3,106.4)],[.09,.12,.12,.025],9,2,normal=(1,0,0),thick=.025,ridge=0)
# Swept armored ribs follow chest curvature, highlighting the narrow silhouette.
for s in [-1,1]:
 for j in range(4):
  z=79-j*5;cs=[(15,s*2,z-2),(17,s*7,z),(12,s*12,z+3), (6,s*15,z+5)]
  ribbon('curved silver chest rib '+str(s)+' '+str(j),cs,[.5,1.5,1.5,.2],7 if j in [0,3] else 6,1,normal=(1,0,0),thick=.40,ridge=.55)
 tube('upper chest silver rim '+str(s),[(14,s*1,86),(15,s*8,86),(8,s*15,88)],[.75,.65,.25],7,1,n=6)
 # High sweeping collar and organic crescent pauldrons.
 ribbon('upturned cathedral collar '+str(s),[(0,s*10,85),(-2,s*13,96),(-5,s*15,107),(-9,s*17,111)],[4,4.2,3,.15],5,1,normal=(1,0,0),thick=.7,ridge=1)
 ribbon('beveled curved shoulder armor '+str(s),[(7,s*14,85),(8,s*19,88),(5,s*25,85),(0,s*29,80)],[3.3,5.5,4,.22],6,3 if s==1 else 6,normal=(0,0,1),thick=.95,ridge=1.4)
 ribbon('lower layered shoulder blade '+str(s),[(8,s*17,81),(9,s*22,81),(5,s*27,76)],[2.6,3.9,.2],5,3 if s==1 else 6,normal=(0,0,1),thick=.7,ridge=1.0)
 # Distinct bevel lips and an outward thorn establish sharp Warcraft-scale armor.
 for side in [-1,1]:
  tube('gold pauldron bevel '+str(s)+' '+str(side),[(7+side*3.2,s*14,86),(8+side*5.2,s*19,89),(5+side*3.7,s*25,86),(0,s*29,80.7)],[.65,.75,.60,.16],10,3 if s==1 else 6,n=5)
 tube('angular pauldron thorn '+str(s),[(2,s*25,85),(0,s*31,93),(-2,s*35,100)],[2.8,1.6,.045],5,3 if s==1 else 6,n=6)
 tube('pauldron thorn gold edge '+str(s),[(4.3,s*25,86),(1.3,s*31,93.5),(-2,s*35,100)],[.52,.4,.035],10,3 if s==1 else 6,n=5)
 for z in [82,86]:
  ellipsoid('pauldron gold rivet '+str(s)+' '+str(z),(11,s*20,z),(1.1,1.0,1.0),10,3 if s==1 else 6,n=6,k=3)
 # Hanging sleeve panels frame the arms but don't create blocky elbows.
 cs=[(-2,s*18,80),(-4,s*22,67),(-7,s*25,55),(-8,s*28,43)]
 ribbon('torn floating sleeve '+str(s),cs,[5.5,6.5,5.2,.3],2,3 if s==1 else 6,normal=(1,0,0),thick=.40,ridge=.7)
# Asymmetric raised and outstretched arm poses.
tube('raised slender upper arm',[(0,16,81),(2,23,86),(4,28,91)],[4.2,3.4,3.0],5,3,n=9)
tube('raised forearm gauntlet',[(4,28,91),(10,32,101),(17,32,111)],[3.1,3.3,2.2],6,4,n=9)
tube('outstretched upper arm',[(0,-16,81),(3,-23,75),(8,-29,72)],[4.2,3.5,3.0],5,6,n=9)
tube('outstretched forearm',[(8,-29,72),(15,-34,76),(23,-35,81)],[3.2,3.3,2.0],6,7,n=9)
ellipsoid('raised angular palm',(18,32,113),(2.2,4.4,5.5),5,5,n=9,k=4)
ellipsoid('extended open palm',(26,-35,82),(5.0,4.1,2.1),5,8,n=9,k=4)
finger_meta=[]
for hand in ['raised','extended']:
 for j in range(5):
  if hand=='raised':
   y=27+j*2.2;z=114+(1 if j in [1,2,3] else -2);start=(18,y,z);end=(19.5+j*.35,y+(j-2)*1.4,z+10.5-abs(j-2)*1.8);cs=[start,(20,y+(j-2)*.8,z+6),end];par=5
  else:
   y=-40+j*2.1;start=(28,y,82);end=(37.5-abs(j-2)*1.0,y+(j-2)*1.3,78.2);cs=[start,(35,y+(j-2)*.6,83),(38,y+(j-2),81),end];par=8
  bi=bone(hand+' articulated finger '+str(j),par,start);finger_meta.append((bi,hand,j))
  tube(hand+' long gauntlet finger '+str(j),cs,[1.05,.9,.10] if len(cs)==3 else [1.05,.95,.70,.10],7,bi,n=6)
# Independent broken crescent halo: closed 3D annular sectors and detached shards.
def crescent(name,a0,a1,outer,inner,bi,n=20):
 v=[];uv=[]
 for front in [-1,1]:
  for i in range(n+1):
   a=math.radians(a0+(a1-a0)*i/n)
   u=i/n;center=(inner+outer)/2;width=(outer-inner)*(.10+.90*math.sin(math.pi*u)**.42)
   if 'detached' in name:width=(outer-inner)*max(.025,(1-u)*1.10)
   for side,r in enumerate([center-width/2,center+width/2]):v.append((-9+front*(.55+.50*math.sin(math.pi*u)),r*math.cos(a),101+r*math.sin(a)));uv.append([side,u])
 o=(n+1)*2;f=[];fc=[]
 for i in range(n):
  a=i*2;b=a+1;c=a+2;d=a+3;f.extend([(a,c,d),(a,d,b),(a+o,d+o,c+o),(a+o,b+o,d+o)]);fc.extend([11,11,5,5])
  f.extend([(a,a+o,c+o),(a,c+o,c),(b,d+o,b+o),(b,d,d+o)]);fc.extend([7,7,5,5])
 f.extend([(0,1,o+1),(0,o+1,o),(2*n,2*n+o+1,2*n+1),(2*n,2*n+o,2*n+o+1)]);fc.extend([7]*4)
 mesh(name,v,f,11,bi,False,fc);parts[-1]['uvs']=uv
crescent('great upper broken crescent',30,164,37,31,12,n=18)
crescent('great lower broken crescent',181,317,37,31,12,n=18)
crescent('detached crescent tip high',2,18,39,34,13,n=4)
crescent('detached crescent left fragment',328,348,38,33,14,n=4)
for ang in [50,83,122,147,201,236,278,303]:
 a=math.radians(ang);tube('moon rune spoke '+str(ang),[(-7.85,31*math.cos(a),101+31*math.sin(a)),(-7.82,36*math.cos(a+.02),101+36*math.sin(a+.02))],[.36,.28],7,12,n=5)
# Gold rims follow the crescent curvature, never straight detached blocks.
for a0,a1 in [(30,164),(181,317)]:
 for side in [-1,1]:
  cs=[]
  for i in range(19):
   u=i/18;a=math.radians(a0+(a1-a0)*u);width=6*(.10+.90*math.sin(math.pi*u)**.42);r=34+side*width/2
   cs.append((-7.7,r*math.cos(a),101+r*math.sin(a)))
  tube('crescent gold curved rim '+str(a0)+' '+str(side),cs,[.14]+[.40]*17+[.14],7,12,n=5)
# Hanging moon pendants and gem keep magic readable without a cloud of particles.
ellipsoid('chest violet gem',(19,0,75),(2,2.6,4),12,1,n=8,k=4)
tube('front silver chain',[(18,-5,82),(20,-3,75),(20,0,70),(20,3,75),(18,5,82)],[.35]*5,10,1,n=5)

# Consistent outward winding validation for every closed original component.
for p in parts:
 edges=defaultdict(list)
 for fi,face in enumerate(p['faces']):
  for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))].append((fi,a,b))
 assert all(len(e)==2 for e in edges.values()),('unsealed component',p['name'])
 links=defaultdict(list)
 for e in edges.values():
  (i,a,b),(j,c,d)=e;same=(a==c);links[i].append((j,same));links[j].append((i,same))
 flip={}
 for initial in range(len(p['faces'])):
  if initial in flip:continue
  flip[initial]=False;q=deque([initial])
  while q:
   i=q.popleft()
   for j,same in links[i]:
    want=flip[i]^same
    if j in flip:assert flip[j]==want,('non-orientable',p['name'])
    else:flip[j]=want;q.append(j)
 p['faces']=[(f[0],f[2],f[1]) if flip[i] else tuple(f) for i,f in enumerate(p['faces'])]
 v=np.asarray(p['verts']);f=np.asarray(p['faces']);vol=np.sum(np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])))/6
 if vol<0:p['faces']=[(a,c,b) for a,b,c in p['faces']]
 assert abs(vol)>1e-6,(p['name'],'zero volume')

seqs=[('Stand',0,2400,True),('Walk',2500,3700,True),('Spell',3800,5300,False),('Stand Hit',5400,6000,False),('Death',6100,8100,False),('Portrait',8200,10600,True)]
def quat(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(21):
   u=i/20;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);c=1-math.cos(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.65*c
    if bi==2:rot=quat([0,0,1],.026*w)
    if bi in [3,6]:rot=quat([1,0,0],(.023 if bi==3 else -.020)*w)
    if bi in [4,7]:rot=quat([0,1,0],.025*w)
    if bi in [5,8]:rot=quat([0,0,1],.045*w)
    if bi in [9,10,11]:rot=quat([1,0,0],(.026 if bi==9 else -.023)*w)
    if bi==12:tr[2]=.8*c;rot=quat([1,0,0],.02*w)
    if bi in [13,14]:rot=quat([1,0,0],(.07 if bi==13 else -.065)*w)
    if bi>=15:rot=quat([0,1,0],.025*w)
   elif name=='Walk':
    if bi==1:tr=[1*w,0,1.3*c];rot=quat([0,1,0],.025*w)
    if bi==2:rot=quat([0,1,0],-.022*w)
    if bi in [3,6]:rot=quat([0,1,0],.04*w)
    if bi in [4,7,5,8]:rot=quat([1,0,0],.035*w)
    if bi in [9,10,11]:rot=quat([0,1,0],-.07*w);tr[0]=-1.5*c
    if bi==12:tr=[-.6*w,0,1.2*c];rot=quat([1,0,0],.035*w)
    if bi in [13,14]:rot=quat([1,0,0],.085*w)
    if bi>=15:rot=quat([0,1,0],.035*w)
   elif name=='Spell':
    k=math.sin(math.pi*u)
    if bi==1:tr=[2*k,0,2.8*k]
    if bi==2:rot=quat([0,1,0],-.12*k)
    if bi==3:rot=quat([0,0,1],-.15*k)
    if bi==4:rot=quat([1,0,0],-.18*k)
    if bi==5:rot=quat([0,1,0],-.23*k)
    if bi==6:rot=quat([1,0,0],-.28*k)
    if bi==7:rot=quat([0,1,0],-.26*k)
    if bi==8:rot=quat([0,0,1],-.17*k)
    if bi in [9,10,11]:rot=quat([0,1,0],-.09*k)
    if bi==12:rot=quat([1,0,0],.13*k);sc=[1,1+.025*k,1+.025*k]
    if bi in [13,14]:rot=quat([1,0,0],(.15 if bi==13 else -.15)*k)
    if bi>=15:rot=quat([0,1,0],.20*k)
   elif name=='Stand Hit':
    k=math.sin(math.pi*u)*math.exp(-2*u)
    if bi==1:tr=[-5*k,0,0];rot=quat([0,1,0],-.14*k)
    if bi==2:rot=quat([0,1,0],-.20*k)
    if bi in [3,4,6,7]:rot=quat([0,1,0],.12*k)
    if bi in [9,10,11]:rot=quat([0,1,0],.10*k)
    if bi==12:tr=[-2*k,0,1*k]
   else:
    e=3*u*u-2*u*u*u
    if bi==1:tr=[-3*e,0,-39*e];sc=[1,1,1-.72*e]
    if bi==2:rot=quat([0,1,0],.52*e)
    if bi in [3,6]:rot=quat([0,1,0],.3*e)
    if bi in [4,7]:rot=quat([0,1,0],.5*e)
    if bi in [5,8]:rot=quat([1,0,0],.3*e)
    if bi in [9,10,11]:sc=[1,1,1-.25*e]
    if bi==12:tr=[-5*e,0,-76*e];rot=quat([0,1,0],1.40*e);sc=[1,.83,1]
    if bi in [13,14]:rot=quat([1,0,0],(.4 if bi==13 else -.4)*e)
    if bi>=15:rot=quat([0,1,0],.28*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
(OUT/'eclipse-source.json').write_text(json.dumps(dict(name='EclipseSpellweaver_Original_Review_v3',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))
# Original Warcraft-style diffuse atlas. Deliberate broad highlight/shadow shapes,
# edge wear and engraved marks are carried by BLP pixels, without grain or PBR maps.
S=128;atlas=Image.new('RGB',(512,512));Y,X=np.mgrid[0:S,0:S];xx=X/(S-1);yy=Y/(S-1)
def stroke(draw,points,dark,lit,width=3):
 draw.line(points,fill=dark,width=width+3,joint='curve')
 draw.line([(x-1,y-2) for x,y in points],fill=lit,width=width,joint='curve')
for k,base in enumerate(colors):
 light=.70+.42*(1-yy)
 if k in [1,2,3,4]:
  fold=np.exp(-((xx-.43)/.28)**2)
  light=.46+.60*fold+.18*(1-yy)-.18*np.exp(-((xx-.90)/.065)**2)
 elif k in [5,6,11]:
  light=.58+.46*(1-yy)+.48*np.exp(-((xx-.32)/.29)**2)
 elif k in [7,10]:
  light=.66+.36*(1-yy)+.26*np.exp(-((xx-.34)/.27)**2)
 elif k in [8,15]:
  light=.50+.69*(1-yy)+.23*np.exp(-((xx-.23)/.21)**2)
 elif k==9:light=.45+.52*(1-yy)
 elif k in [12,13,14]:light=np.ones((S,S))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if k in [1,2,3,4]:
  # Broad value planes, a single worn hem and two painted crease shadows.
  # No embroidered line grid and no all-over luminous scratches.
  dark=tuple(int(v*.42) for v in base);hi=tuple(int(v*.90) for v in base)
  d.polygon([(7,12),(16,35),(12,73),(18,115),(7,118)],fill=dark)
  d.polygon([(109,12),(103,36),(109,84),(105,116),(118,119),(118,12)],fill=dark)
  d.polygon([(15,110),(112,110),(116,119),(13,119)],fill=hi)
 elif k in [5,6,11]:
  # Broad cold iron midtones and a continuous bevel, not black silhouettes.
  d.line([(10,12),(115,12),(115,115)],fill=(112,137,163),width=7,joint='curve')
  d.line([(17,23),(104,23),(104,105)],fill=(27,40,58),width=7,joint='curve')
  d.line([(24,32),(94,32)],fill=(68,91,118),width=4)
 elif k in [7,10]:
  # Continuous warm gilt shading. The true mesh carries the armor outline.
  d.line([(10,12),(115,12),(115,115)],fill=(255,224,133),width=7,joint='curve')
  d.line([(17,23),(104,23),(104,105)],fill=(121,78,22),width=5,joint='curve')
 elif k in [8,15]:
  # Large brown recesses, pale cut edge and broken bone seams.
  d.polygon([(8,12),(20,26),(18,72),(26,112),(10,119)],fill=(93,76,44))
  d.line([(22,16),(26,43),(22,74),(30,112)],fill=(250,237,184),width=3)
  d.line([(112,14),(107,43),(112,67),(103,107)],fill=(85,67,39),width=3)
  d.line([(109,14),(104,43),(109,67),(100,107)],fill=(231,214,158),width=1)
  for pts in [[(44,10),(53,30),(49,47),(65,58)],[(96,116),(88,93),(95,81),(82,67)]]:
   d.line(pts,fill=(71,53,29),width=2);d.line([(x-2,y) for x,y in pts],fill=(239,224,174),width=1)
 elif k==12:
  d.polygon([(64,7),(111,42),(83,112),(34,102),(11,35)],fill=(120,53,186));d.polygon([(64,7),(66,57),(11,35)],fill=(225,173,255));d.polygon([(66,57),(83,112),(111,42)],fill=(52,9,98))
 atlas.paste(tile,((k%4)*S,(k//4)*S))
atlas.save(OUT/'EclipseSpellweaverAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(10):
 sz=max(1,512>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'EclipseSpellweaverAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,512,512,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps(dict(triangles=sum(len(p['faces']) for p in parts),bones=len(bones),parts=len(parts))))
