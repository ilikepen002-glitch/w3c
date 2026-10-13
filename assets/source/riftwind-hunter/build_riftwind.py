"""Project-original Riftwind Hunter: agile armored biped, swept white hair and crescent blade."""
from primitives import parts,mesh,ellipsoid,tube
import math,json,pathlib,struct
from collections import defaultdict,deque
import numpy as np
from PIL import Image,ImageDraw
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['080f17','15222d','26384a','455c70','758e9f','b5c9ce','d8e3df','182630','b7b2a7','695f58','263039','e0e8e2','77cbd5','c5f5f2','080c13','8aabae'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[]
def bone(n,p,c):bones.append(dict(name=n,parent=p,pivot=list(c)));return len(bones)-1
for n,p,c in [('Root',-1,(0,0,0)),('Pelvis',0,(0,0,64)),('Spine',1,(3,0,80)),('HunterFace',2,(13,0,109)),('LeadThigh',1,(0,-8,64)),('LeadShin',4,(20,-12,38)),('LeadBoot',5,(11,-12,9)),('TrailThigh',1,(-3,8,64)),('TrailShin',7,(-5,10,37)),('TrailBoot',8,(-25,10,9)),('BladeUpperArm',2,(9,-18,101)),('BladeForearm',10,(17,-27,84)),('BladeHand',11,(28,-24,77)),('FreeUpperArm',2,(8,18,102)),('FreeForearm',13,(-1,26,83)),('FreeHand',14,(-4,28,70)),('LeftHair',3,(5,-7,124)),('RightHair',3,(5,7,124)),('BackHair',3,(4,0,126)),('LeftHipCloth',1,(-4,-9,65)),('RightHipCloth',1,(-4,9,65)),('CrescentLongblade',12,(28,-24,77))]:bone(n,p,c)
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
def plaque(name,yz,x,depth,col,bi=2,ridge=.6):
    # Convex chiseled slab, closed front/back fan with broad hand-painted faces.
    n=len(yz);cy=sum(y for y,z in yz)/n;cz=sum(z for y,z in yz)/n
    vv=[(x,y,z) for y,z in yz]+[(x+ridge,cy,cz)]+[(x-depth,y,z) for y,z in yz]+[(x-depth,cy,cz)]
    ff=[]
    for i in range(n):
        j=(i+1)%n;ff.extend([(n,i,j),(2*n+1,n+1+j,n+1+i),(i,n+1+i,n+1+j),(i,n+1+j,j)])
    mesh(name,vv,ff,col,bi,False)
# Low, forward chest and separate leg silhouette. No long priest robe.
loft('lean black leather pelvis',[(-2,0,57,8,11),(0,0,65,10,13),(2,0,72,8,10)],12,1,1)
loft('forward tilted hunter torso',[(2,0,69,7,10),(4,0,79,9,13),(8,0,93,12,17),(10,0,102,10,17),(12,0,108,5,7)],16,2,2)
tube('neck sinew',[(12,0,105),(15,0,115)],[4.5,4.0],9,3,n=9)
# Three irregular overlapping dark-bone plates. No repeated horizontal silver ladder.
for j,(cs,widths) in enumerate([
 ([(10,-15,104),(23,-6,100),(23,5,96),(10,15,100)],[.3,4.7,5.1,.2]),
 ([(14,-13,93),(25,-4,90),(22,6,89),(12,13,94)],[.3,4.0,3.4,.14]),
 ([(14,-10,81),(22,-3,83),(22,5,85),(12,11,88)],[.15,2.5,3.6,.2])]):
 ribbon('irregular overlapping chest bone plate '+str(j),cs,widths,2,2,normal=(1,0,0),thick=1,ridge=1.6)
 if j in [0,2]:
  edge=[(x+1.7,y,z+1.5) for x,y,z in cs]
  tube('partial chest plate cut edge '+str(j),edge,[.10,.50,.50,.09],4,2,n=5)
for side in [-1,1]:
 ribbon('side hip armor '+str(side),[(2,side*11,69),(-2,side*15,60),(-4,side*16,50)],[4,5,.16],2,1,normal=(1,0,0),thick=.8,ridge=1)
 ribbon('split short hunter fauld '+str(side),[(-6,side*8,65),(-10,side*10,55),(-15,side*11,42),(-22,side*10,34)],[4,5,4,.10],7,19 if side<0 else 20,normal=(0,1,0),thick=.45,ridge=.5)
# Actual articulated upper/lower legs with layered knee and shin plates.
for label,hip,knee,ankle,ids in [('lead',(0,-8,64),(20,-12,38),(11,-12,9),(4,5,6)),('trailing',(-3,8,64),(-5,10,37),(-25,10,9),(7,8,9))]:
 a,b,c=ids
 tube(label+' muscular armored thigh',[hip,tuple((np.array(hip)+np.array(knee))*.5),knee],[6.2,5.8,4.2],1,a,n=10)
 tube(label+' narrow greave',[knee,tuple((np.array(knee)+np.array(ankle))*.5),ankle],[4.3,4.0,2.7],2,b,n=10)
 ellipsoid(label+' knee shell',(knee[0]+2,knee[1],knee[2]+1),(5.3,5.7,6),3,b,n=10,k=4)
 ribbon(label+' knife shin plate',[(knee[0]+4,knee[1],knee[2]),(ankle[0]+4.5,ankle[1],20),(ankle[0]+4,ankle[1],7)],[3.4,3.8,.3],3,b,normal=(1,0,0),thick=.7,ridge=1)
 tube(label+' bright shin ridge',[(knee[0]+5.7,knee[1],knee[2]),(ankle[0]+6,ankle[1],20),(ankle[0]+4.7,ankle[1],8)],[.55,.65,.12],5,b,n=5)
 ellipsoid(label+' grounded pointed boot',(ankle[0]+5,ankle[1],5.2),(10.7,4.6,4.5),1,c,n=10,k=4)
 ribbon(label+' armored boot toe',[(ankle[0]+1,ankle[1],8),(ankle[0]+10,ankle[1],6.5),(ankle[0]+17,ankle[1],3.4)],[3.8,4,.09],3,c,normal=(0,0,1),thick=.55,ridge=.5)
# Swept spiked pauldrons; the blade-side arm reaches forward across the body.
for side,bi in [(-1,10),(1,13)]:
 ribbon('sculpted pauldron '+str(side),[(10,side*13,102),(11,side*19,106),(6,side*25,104),(-1,side*28,98)],[3.4,5.4,4,.1],2,bi,normal=(0,0,1),thick=1,ridge=2)
 tube('pauldron raised silver lip '+str(side),[(14,side*13,103.5),(17,side*19,107),(10,side*25,105),(-1,side*28,98)],[.55,.75,.6,.08],5,bi,n=5)
 for j in range(2):
  tube('swept shoulder talon '+str(side)+' '+str(j),[(4-j*5,side*(19+j*3),106-j),(0-j*6,side*(24+j*4),116-j),(-6-j*6,side*(25+j*4),124-j*2)],[2.8,1.7,.04],2,bi,n=6)
  tube('shoulder talon light edge '+str(side)+' '+str(j),[(6-j*5,side*(19+j*3),107-j),(1.5-j*6,side*(24+j*4),117-j),(-6-j*6,side*(25+j*4),124-j*2)],[.5,.36,.03],5,bi,n=5)
for label,cs,rs,col,bi in [('blade upper',[(9,-18,101),(14,-24,93),(17,-27,84)],[4.8,4.1,3.7],1,10),('blade fore',[(17,-27,84),(23,-26,79),(28,-24,77)],[3.6,4,2.8],3,11),('free upper',[(8,18,102),(3,23,92),(-1,26,83)],[4.9,4.2,3.4],1,13),('free fore',[(-1,26,83),(-3,28,76),(-4,28,70)],[3.5,3.7,2.4],3,14)]:tube(label,cs,rs,col,bi,n=9)
ellipsoid('blade clenched grip',(29,-24,77),(3.5,4.6,4.0),3,12,n=9,k=4)
ellipsoid('free claw hand',(-3,28,68),(3.0,4.1,4.5),3,15,n=9,k=4)
for j in range(4):
 y=24.6+j*2.1
 tube('free iron claw '+str(j),[(-1,y,68),(1,y,63),(3.5,y+.2,61)],[1.1,.8,.07],5,15,n=5)
 tube('gripping finger '+str(j),[(30,-28+j*2,79),(33,-28+j*2,76),(30,-28+j*2,74)],[.95,.9,.3],4,12,n=5)
# Angular living hunter face, not the previous Boss's skull or smooth ceramic mask.
ellipsoid('silver hair crown',(12,0,122),(8.0,8.8,11.7),11,3,n=14,k=6)
rows=[(112,2.8),(114.3,5.4),(118,7.4),(122,7.5),(125,6.6),(128,4.2)]
vs=[];uv=[]
for back in [False,True]:
 for j,(z,w) in enumerate(rows):
  for u in [-1,-.67,-.33,0,.33,.67,1]:
   nose=([0,.2,2.5,.4,.1,0][j])*math.exp(-(u/.25)**2)
   cheek=(1.0 if j==2 else .20 if j==3 else 0)*math.exp(-((abs(u)-.67)/.17)**2)
   vs.append((22+2.3*(1-u*u)+nose+cheek-(2.0 if back else 0),u*w,z));uv.append([(u+1)/2,j/5])
f=[];off=42
for back in [False,True]:
 o=42 if back else 0
 for j in range(5):
  for k in range(6):a=o+j*7+k;b=a+1;c=a+7;d=b+7;f.extend([(a,c,d),(a,d,b)] if back else [(a,b,d),(a,d,c)])
edge=list(range(7))+[j*7+6 for j in range(1,6)]+list(range(40,34,-1))+[j*7 for j in range(4,0,-1)]
for i,a in enumerate(edge):b=edge[(i+1)%len(edge)];f.extend([(a,b,a+off),(b,b+off,a+off)])
mesh('sculpted sharp elven face',vs,f,8,3,False);parts[-1]['uvs']=uv
for sign in [-1,1]:
 plaque('pointed elf ear '+str(sign),[(sign*6.3,120),(sign*16,128),(sign*9,116)],19,2,8,3,ridge=.4)
 ribbon('deep slanted eye hollow '+str(sign),[(25,sign*1.3,121),(24.8,sign*3.6,121.8),(23.7,sign*5.9,123)],[.12,.72,.09],14,3,normal=(1,0,0),thick=.15,ridge=0)
 tube('icy narrow eye '+str(sign),[(25.3,sign*2.1,121.2),(25,sign*3.7,121.85),(24,sign*5.1,122.4)],[.08,.22,.035],13,3,n=5)
 ribbon('menacing heavy brow '+str(sign),[(25.4,sign*1.0,122.0),(25,sign*3.6,123.2),(23.7,sign*5.5,124.0)],[.18,.80,.12],8,3,normal=(1,0,0),thick=.40,ridge=.50)
 ribbon('cut cheek hollow '+str(sign),[(23.9,sign*6.0,119.3),(25.0,sign*4.4,117.3),(24.1,sign*3.4,114.3)],[.09,.22,.025],9,3,normal=(1,0,0),thick=.08,ridge=.04)
 tube('thin stern mouth '+str(sign),[(25.4,sign*.05,115.3),(25.1,sign*1.7,115.55),(24.7,sign*2.9,115.2)],[.11,.15,.045],10,3,n=5)
 # A backward hooked crown frames the temples rather than covering the face.
 tube('black temple crown tine '+str(sign),[(19,sign*6.3,124),(16,sign*10,131),(11,sign*12,140),(4,sign*12,145)],[2.1,1.9,1.0,.035],2,3,n=6)
 tube('crown cold steel edge '+str(sign),[(21,sign*6.3,124.6),(17.6,sign*10,131),(12,sign*12,140),(4,sign*12,145)],[.4,.48,.2,.03],5,3,n=5)
# Facial details are conformed onto the actual triangulated face.
face=next(p for p in parts if p['name']=='sculpted sharp elven face');FV=np.asarray(face['verts'][:42]);FF=face['faces'][:60]
def face_x(y,z):
 for f in FF:
  a,b,c=[FV[k] for k in f];mat=np.array([[b[1]-a[1],c[1]-a[1]],[b[2]-a[2],c[2]-a[2]]])
  if abs(np.linalg.det(mat))<1e-9:continue
  u,v=np.linalg.solve(mat,np.array([y-a[1],z-a[2]]))
  if u>=-1e-4 and v>=-1e-4 and u+v<=1.0001:return a[0]+u*(b[0]-a[0])+v*(c[0]-a[0])
 raise ValueError(('detail outside face',y,z))
for p in parts:
 if any(p['name'].startswith(n) for n in ['deep slanted eye','icy narrow eye','menacing heavy brow','cut cheek hollow','thin stern mouth']):
  old=np.asarray(p['verts']);low=old[:,0].min();span=max(.001,old[:,0].max()-low);dep=.30 if p['name'].startswith('menacing') else .10;offset=.16 if p['name'].startswith('icy') else .035
  p['verts']=[(face_x(y,z)+offset+dep*(x-low)/span,y,z) for x,y,z in old]
# Projected cheekbones, short nasal tip and lips break the old planar-mask contour.
for sign in [-1,1]:
 ellipsoid('small nostril '+str(sign),(face_x(sign*.95,117.6)+.09,sign*.95,117.6),(.18,.40,.23),14,3,n=7,k=3)
 tube('fleshy lower lip '+str(sign),[(face_x(sign*.1,114.9)+.14,sign*.1,114.9),(face_x(sign*1.4,114.9)+.13,sign*1.4,114.9),(face_x(sign*2.5,115.1)+.1,sign*2.5,115.1)],[.14,.20,.04],8,3,n=5)
# Continuous swept hair sheets with tapered thickness and smooth actual MDX normals.
for j,(y,z,bi) in enumerate([(-7,126,16),(-3.5,130,18),(1,132,18),(5,130,18),(8,125,17)]):
 cs=[];ws=[]
 A=np.array([12,y,z]);B=np.array([-5,y*1.55,z+16]);C=np.array([-21,y*1.75,z-10]);D=np.array([-33-j*1.2,y*1.35,z-34-j*1.5])
 for i in range(16):
  u=i/15;cs.append(((1-u)**3*A+3*(1-u)**2*u*B+3*(1-u)*u*u*C+u**3*D).tolist());ws.append(.06+3.2*math.sin(math.pi*(u*.90+.03))**.65*(1-u*.55))
 ribbon('continuous tapered white lock '+str(j),cs,ws,11 if j%2 else 6,bi,normal=(0,1,0),thick=.28,ridge=.65)
 parts[-1]['smooth']=True
 # Taper the final cross sections in all axes to avoid square tube ends.
 vv=np.asarray(parts[-1]['verts']);N=len(cs)
 for back in range(2):
  for q in range(N):
   factor=max(.08,1-(q/(N-1))**6)
   for k in range(3):
    idx=back*N*3+q*3+k;vv[idx]=np.array(cs[q])+(vv[idx]-np.array(cs[q]))*factor
 parts[-1]['verts']=vv.tolist()
# The crescent longblade is attached to the grip and occupies its own bold silhouette.
tube('separate dark leather sword grip',[(29,-11,78),(29,-24,78),(31,-37,82)],[1.35,1.35,1.1],7,21,n=8)
for y in [-14,-33]:tube('bright grip collar '+str(y),[(29,y,78),(29,y-1.5,78.2)],[1.8,1.8],5,21,n=7)
tube('blade hooked tang',[(31,-37,82),(40,-42,85),(48,-44,89)],[1.6,2.0,2.4],3,21,n=6)
tube('prominent crescent crossguard',[(24,-34,77),(32,-34,83),(38,-33,88)],[.08,1.7,.09],5,21,n=6)
blade=[(39,-38,112),(44,-46,102),(48,-46,90),(51,-39,76),(54,-24,65),(55,-6,63),(56,12,67),(54,22,80)]
widths=[.08,3.3,5.2,6.0,6.4,5.3,3,.08]
ribbon('great crescent hunting blade',blade,widths,3,21,normal=(1,0,0),thick=.75,ridge=1.15)
v=np.asarray(parts[-1]['verts']);N=len(blade)
for back in range(2):
 for q in [0,N-1]:
  for k in range(3):i=back*N*3+q*3+k;v[i]=np.array(blade[q])+(v[i]-np.array(blade[q]))*.15
parts[-1]['verts']=v.tolist()
edge=[]
for i,c in enumerate(blade):
 t=np.array(blade[min(len(blade)-1,i+1)])-np.array(blade[max(0,i-1)]);t=t/np.linalg.norm(t);side=np.cross(t,np.array([1.,0,0]));side/=np.linalg.norm(side)
 edge.append((np.array(c)+side*widths[i]+np.array([1.1,0,0])).tolist())
tube('continuous cutting silver edge',edge,[.03,.5,.6,.7,.75,.6,.4,.03],5,21,n=5)
for i in [2,4]:tube('restrained cyan wind inset '+str(i),[(blade[i][0]+1.9,blade[i][1]-1,blade[i][2]+1),(blade[i+1][0]+1.9,blade[i+1][1],blade[i+1][2])],[.35,.15],12,21,n=5)
# Bind-pose lean through the hips and a raised trailing heel create sprint anticipation.
angle=.21;C,S=math.cos(angle),math.sin(angle);pivot=np.array([3,0,80]);R=np.array([[C,0,S],[0,1,0],[-S,0,C]])
upper={2,3,10,11,12,13,14,15,16,17,18,21}
for p in parts:
 if p['bone'] in upper:p['verts']=[(pivot+R@(np.array(v)-pivot)).tolist() for v in p['verts']]
for i,b in enumerate(bones):
 if i in upper:b['pivot']=(pivot+R@(np.array(b['pivot'])-pivot)).tolist()
# Only the rear boot rocks about its planted toe; hip/knee structure stays continuous.
pivot=np.array([-8,10,3.4]);a=.32;R=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
for p in parts:
 if p['bone']==9:p['verts']=[(pivot+R@(np.array(v)-pivot)).tolist() for v in p['verts']]
bones[9]['pivot']=(pivot+R@(np.array(bones[9]['pivot'])-pivot)).tolist()
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
    if bi==2:tr[2]=.5*c;rot=quat([0,1,0],.012*w)
    if bi==3:rot=quat([0,0,1],.025*w)
    if bi in [10,13]:rot=quat([0,1,0],.025*w)
    if bi in [16,17,18]:rot=quat([0,1,0],.035*w)
    if bi in [19,20]:rot=quat([0,1,0],.025*w)
   elif name=='Walk':
    if bi==0:tr[2]=7*abs(w)
    if bi==2:rot=quat([0,1,0],.045*w)
    if bi in [4,7]:rot=quat([0,1,0],(.18 if bi==4 else -.18)*w)
    if bi in [5,8]:rot=quat([0,1,0],(-.24 if bi==5 else .24)*w)
    if bi in [6,9]:rot=quat([0,1,0],(.08 if bi==6 else -.08)*w)
    if bi in [10,13]:rot=quat([0,1,0],(.10 if bi==10 else -.15)*w)
    if bi in [16,17,18]:rot=quat([0,1,0],-.11*w)
    if bi in [19,20]:rot=quat([0,1,0],-.08*w)
   elif name=='Spell':
    k=math.sin(math.pi*u)
    if bi==0:tr=[7*k,0,2*k]
    if bi==2:rot=quat([0,1,0],.13*k)
    if bi==3:rot=quat([0,1,0],-.12*k)
    if bi==10:rot=quat([0,0,1],.25*k)
    if bi==11:rot=quat([0,1,0],-.2*k)
    if bi==21:rot=quat([0,0,1],-.22*k)
    if bi in [16,17,18]:rot=quat([0,1,0],.16*k)
   elif name=='Stand Hit':
    k=math.sin(math.pi*u)*math.exp(-2*u)
    if bi==2:rot=quat([0,1,0],-.18*k);tr[0]=-3*k
    if bi==3:rot=quat([0,1,0],-.15*k)
    if bi in [10,13,16,17,18]:rot=quat([0,1,0],.13*k)
   else:
    e=3*u*u-2*u*u*u
    # Rigid side-fall with folding arm and weapon, no body scale compression.
    if bi==0:rot=quat([1,0,0],-1.48*e)
    if bi==2:rot=quat([0,1,0],.10*e)
    if bi==3:rot=quat([0,1,0],.22*e)
    if bi==13:rot=quat([0,0,1],.70*e)
    if bi==14:rot=quat([1,0,0],-.65*e)
    if bi==21:rot=quat([1,0,0],-.80*e)
    if bi in [16,17,18]:rot=quat([0,1,0],.18*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
# Fit Death root height to the real skinned geometry at every key, keeping the
# entire side-fall above the floor without flattening or scaling the body.
def local_matrix(b,index):
 t=np.array(b['tracks']['KGTR'][index][1]);q=b['tracks']['KGRT'][index][1];ss=np.array(b['tracks']['KGSC'][index][1]);x,y,z,w=q
 R=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(ss)
 P=np.array(b['pivot']);M=np.eye(4);M[:3,:3]=R;M[:3,3]=t+P-R@P;return M
for i in range(21):
 index=4*21+i;mats=[]
 for b in bones:
  M=local_matrix(b,index)
  if b['parent']!=-1:M=mats[b['parent']]@M
  mats.append(M)
 low=min(float((np.asarray(p['verts'])@mats[p['bone']][:3,:3].T+mats[p['bone']][:3,3])[:,2].min()) for p in parts)
 e=3*(i/20)**2-2*(i/20)**3
 bones[0]['tracks']['KGTR'][index][1][2]=max(0,.7-low)+.12*e
(OUT/'riftwind-source.json').write_text(json.dumps(dict(name='RiftwindHunter_Original_Review_v2',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors)))
# Broad cold hand-painted diffuse planes, never dense emissive scratch patterns.
S=128;atlas=Image.new('RGB',(512,512));Y,X=np.mgrid[0:S,0:S];xx=X/127;yy=Y/127
for k,base in enumerate(colors):
 light=.58+.43*(1-yy)+.3*np.exp(-((xx-.3)/.29)**2)
 if k in [0,1,7]:light=.48+.35*(1-yy)+.32*np.exp(-((xx-.4)/.28)**2)
 if k in [6,11]:light=.48+.48*(1-yy)+.35*np.exp(-((xx-.37)/.24)**2)-.20*np.exp(-((xx-.83)/.075)**2)
 if k==8:light=.62+.43*(1-yy)+.16*np.exp(-((xx-.3)/.26)**2)
 if k in [12,13,14]:light=np.ones((S,S))
 tile=Image.fromarray(np.clip(np.array(base)[None,None,:]*light[:,:,None],0,255).astype(np.uint8));d=ImageDraw.Draw(tile)
 if k in [2,3,4,5,15]:
  hi=tuple(min(255,int(v*1.38)) for v in base);dark=tuple(int(v*.42) for v in base)
  d.line([(10,12),(115,12),(115,115)],fill=hi,width=7,joint='curve');d.line([(18,24),(104,24),(104,105)],fill=dark,width=6,joint='curve')
 if k in [6,11]:
  d.polygon([(8,10),(20,33),(16,85),(25,120),(8,120)],fill=(89,112,128));d.line([(26,12),(33,44),(27,76),(35,114)],fill=(228,240,233),width=5)
 if k==8:
  d.polygon([(9,10),(19,37),(17,94),(29,118),(8,118)],fill=(84,99,107));d.line([(24,15),(29,44),(24,93)],fill=(215,224,218),width=3)
 atlas.paste(tile,((k%4)*S,(k//4)*S))
atlas.save(OUT/'RiftwindHunterAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(10):
 sz=max(1,512>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'RiftwindHunterAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,512,512,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps(dict(triangles=sum(len(p['faces']) for p in parts),bones=len(bones),parts=len(parts))))
