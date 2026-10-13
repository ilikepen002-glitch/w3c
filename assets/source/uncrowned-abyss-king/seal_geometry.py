from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
from collections import defaultdict,deque
import numpy as np
from PIL import Image,ImageDraw
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

