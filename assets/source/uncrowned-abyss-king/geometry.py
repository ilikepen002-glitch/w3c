from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
from collections import defaultdict,deque
import numpy as np
from PIL import Image,ImageDraw
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
