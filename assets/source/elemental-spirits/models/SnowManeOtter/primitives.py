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
 perimeter=[j*3 for j in range(N)]+[j*3+2 for j in range(N-1,-1,-1)]
 for i,aa in enumerate(perimeter):bb=perimeter[(i+1)%len(perimeter)];f.extend([(aa,aa+21,bb+21),(aa,bb+21,bb)]);fc.extend([10,10])
 mesh(name,v,f,col,bone,False,fc)
 parts[-1]['uvs']=[[(u+1)/2,j/(N-1)] for back in [False,True] for j in range(N) for u in [-1,0,1]]

