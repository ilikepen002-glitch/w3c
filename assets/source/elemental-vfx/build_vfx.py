"""Deterministic original low-poly Warcraft Classic skill VFX; no third-party art."""
from pathlib import Path
import math,json,struct
from collections import defaultdict,deque
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output';OUT.mkdir(exist_ok=True)
PAL=['fcf5d9','e4bd55','9d682c','617e8a','624528','9a723b','c09c58','3c281d','408137','89c454','cbe772','183d28','726350','a18b68','e2c072','272a2b']
# Each 16-square tile carries wide authored light/dark planes, not random noise.
im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
for k,h in enumerate(PAL):
 c=tuple(bytes.fromhex(h));x=k%4*16;y=k//4*16
 for j in range(16):
  for i in range(16):
   gain=.62+.30*(1-j/15)+.20*max(0,1-abs(i-5)/7)
   im.putpixel((x+i,y+j),tuple(min(255,int(v*gain)) for v in c)+(255,))
 if k in [4,5,6,7]:
  d.line([(x+3,y+15),(x+5,y+10),(x+4,y+5),(x+6,y)],fill=tuple(int(v*.45) for v in c)+(255,),width=2)
  d.line([(x+10,y+15),(x+11,y+7),(x+9,y)],fill=tuple(min(255,int(v*1.18)) for v in c)+(255,),width=2)
 if k in [12,13]:
  d.line([(x+2,y+13),(x+7,y+9),(x+6,y+4),(x+12,y+1)],fill=(52,41,30,255),width=2)
  d.line([(x+3,y+12),(x+8,y+8),(x+7,y+3),(x+12,y+1)],fill=(187,145,66,255),width=1)
im.save(ROOT/'TDPetVfxAtlas_source.png')
pal=im.convert('RGB').quantize(colors=256,method=Image.Quantize.MEDIANCUT);colors=pal.getpalette();colors += [0]*(768-len(colors));bgra=bytes(v for i in range(256) for v in (colors[i*3+2],colors[i*3+1],colors[i*3],0));off=[];sizes=[];payload=[];cursor=1180
for level in range(7):
 sz=64>>level;mip=im.resize((sz,sz),Image.Resampling.LANCZOS);data=mip.convert('RGB').quantize(palette=pal,dither=Image.Dither.NONE).tobytes()+mip.getchannel('A').tobytes();off.append(cursor);sizes.append(len(data));payload.append(data);cursor+=len(data)
header=b'BLP1'+struct.pack('<6I',1,8,64,64,5,1)+struct.pack('<16I',*(off+[0]*9))+struct.pack('<16I',*(sizes+[0]*9));(OUT/'TDPetVfxAtlas.blp').write_bytes(header+bgra+b''.join(payload))
parts=[]
def mesh(name,verts,faces,tile,glow=False):
 v=np.array(verts,float);faces=[list(f) for f in faces]
 # Consistent manifold orientation established through shared-edge traversal.
 edge=defaultdict(list)
 for fi,f in enumerate(faces):
  for a,b in zip(f,f[1:]+f[:1]):edge[tuple(sorted((a,b)))].append((fi,a,b))
 assert all(len(e)==2 for e in edge.values()),name+' open edge'
 seen={0};q=deque([0]);flip={0:False}
 while q:
  i=q.popleft();f=faces[i]
  for a,b in zip(f,f[1:]+f[:1]):
   for j,c,e in edge[tuple(sorted((a,b)))]:
    if j==i:continue
    val=flip[i] ^ (a==c)
    if j in seen:assert flip[j]==val,name+' nonorientable'
    else:seen.add(j);flip[j]=val;q.append(j)
 assert len(seen)==len(faces)
 faces=[f[::-1] if flip[i] else f for i,f in enumerate(faces)]
 vol=sum(np.dot(v[a],np.cross(v[b],v[c])) for a,b,c in faces)/6
 if vol<0:faces=[f[::-1] for f in faces];vol=-vol
 assert vol>1e-5
 parts.append(dict(name=name,verts=v.tolist(),faces=faces,tile=tile,glow=glow,volume=float(vol)))
def prism(name,poly,depth,tile,center=(0,0,0),axes=(0,2,1),glow=False):
 # Polygon fan is valid for the deliberately convex/star-shaped outlines below.
 n=len(poly);mid=np.mean(poly,axis=0);v=[]
 for z in [-depth/2,depth/2]:
  for x,y in poly+[mid.tolist()]:
   p=list(center);p[axes[0]]+=x;p[axes[1]]+=y;p[axes[2]]+=z;v.append(p)
 f=[]
 for i in range(n):
  j=(i+1)%n;f += [(n,i,j),(2*n+1,n+1+j,n+1+i),(i,n+1+i,n+1+j),(i,n+1+j,j)]
 mesh(name,v,f,tile,glow)
def tube(name,centers,radii,tile,n=5,glow=False):
 cs=np.array(centers,float);v=[]
 for j,c in enumerate(cs):
  t=cs[min(j+1,len(cs)-1)]-cs[max(j-1,0)];t/=np.linalg.norm(t);hint=np.array([0.,0.,1.])
  if abs(t@hint)>.9:hint=np.array([0.,1.,0.])
  a=np.cross(t,hint);a/=np.linalg.norm(a);b=np.cross(t,a)
  for i in range(n):u=2*math.pi*i/n;v.append((c+radii[j]*(a*math.cos(u)+b*math.sin(u))).tolist())
 f=[]
 for j in range(len(cs)-1):
  for i in range(n):a=j*n+i;b=j*n+(i+1)%n;f += [(a,b,b+n),(a,b+n,a+n)]
 for i in range(1,n-1):f += [(0,i,i+1),((len(cs)-1)*n,(len(cs)-1)*n+i+1,(len(cs)-1)*n+i)]
 mesh(name,v,f,tile,glow)
def octa(name,c,r,tile,glow=False):
 v=[(c[0]+r[0],c[1],c[2]),(c[0]-r[0],c[1],c[2]),(c[0],c[1]+r[1],c[2]),(c[0],c[1]-r[1],c[2]),(c[0],c[1],c[2]+r[2]),(c[0],c[1],c[2]-r[2])]
 mesh(name,v,[(4,0,2),(4,2,1),(4,1,3),(4,3,0),(5,2,0),(5,1,2),(5,3,1),(5,0,3)],tile,glow)
def ring(name,r,z,thick,tile,n=18,glow=False):
 v=[]
 for i in range(n):
  a=2*math.pi*i/n
  for rr,zz in [(r-thick,z-thick),(r+thick,z-thick),(r+thick,z+thick),(r-thick,z+thick)]:v.append([rr*math.cos(a),rr*math.sin(a),zz])
 f=[]
 for i in range(n):
  for j in range(4):a=i*4+j;b=i*4+(j+1)%4;c=((i+1)%n)*4+(j+1)%4;e=((i+1)%n)*4+j;f += [(a,b,c),(a,c,e)]
 mesh(name,v,f,tile,glow)
def finish(name,label):
 tri=sum(len(p['faces']) for p in parts);assert tri<=600,(name,tri)
 src=dict(name=name,label=label,texturePath='Textures\\TDPetVfxAtlas.blp',parts=parts.copy(),sequences=[dict(name='Stand',start=0,end=1000,loop=True),dict(name='Death',start=1000,end=1600,loop=False)],triangles=tri)
 (ROOT/(name+'-source.json')).write_text(json.dumps(src,ensure_ascii=False,separators=(',',':')));print(name,tri,'triangles',len(parts),'closed components');parts.clear()
# Gold: five physical straight blades, tips down. Not lightning billboards.
for i in range(5):
 a=math.tau*i/5;x=80*math.cos(a);y=80*math.sin(a)
 before=len(parts)
 prism(f'sword{i} white metal blade',[[0,0],[-5,30],[-7,190],[-3,205],[3,205],[7,190],[5,30]],3.5,0,(x,y,0))
 prism(f'sword{i} gold guard',[[-18,212],[-14,207],[14,207],[18,212],[0,217]],5,1,(x,y,0))
 tube(f'sword{i} handle',[(x,y,217),(x,y,246)],[3,3],2,n=4)
 octa(f'sword{i} pommel',(x,y,251),(5,5,5),1)
 # Radial orientation preserves five independently readable sword silhouettes.
 for p in parts[before:]:
  for v in p['verts']:
   dx=v[0]-x;dy=v[1]-y;v[0]=x+dx*math.cos(a)-dy*math.sin(a);v[1]=y+dx*math.sin(a)+dy*math.cos(a)
ring('thin ground rune ring',80,5,1.2,1,n=18,glow=True)
for i in range(5):
 a=math.tau*(i+.5)/5;octa('short blade light'+str(i),(80*math.cos(a),80*math.sin(a),19),(2.2,2.2,15),0,True)
finish('TDPetVfxSwordArray','白金天诛剑阵')
# Wood: three long curved branching roots, full width along +X, center-origin.
for i,y in enumerate([-38,0,38]):
 cs=[(-137,y,5),(-79,y-9,40),(0,y+5,82 if i==1 else 65),(77,y-5,55),(137,y,7)]
 tube('arching bark root'+str(i),cs,[3,10,12,9,3],4+i,n=6)
 tube('forked root'+str(i),[(0,y+5,70),(36,y+19,91),(75,y+22,106)],[7,5,1.5],5,n=5)
 for j,(x,z) in enumerate([(-43,65),(40,81),(76,100)]):octa(f'leaf{i}-{j}',(x,y+18,z),(19,8,3),9 if j%2 else 8)
for y in [-57,57]:tube('low green growth arc'+str(y),[(-116,y,4),(-55,y,13),(30,y,18),(113,y,4)],[1.5,2,2,1],9,n=4,glow=True)
finish('TDPetVfxVerdantRoot','万象森罗弯根')
# Earth: six transverse rock plates across Y, progression along +X.
for i,x in enumerate([-135,-81,-27,27,81,135]):
 h=[105,133,153,143,121,99][i];w=[57,65,71,73,64,53][i]
 poly=[[-w,0],[-w+4,h*.47],[-w*.5,h*.60],[-w*.34,h],[-4,h*.86],[w*.38,h*.94],[w,h*.44],[w,0]]
 prism('transverse jagged slab'+str(i),poly,24,12+i%2,(x,0,0),(1,2,0))
 tube('gold mineral seam'+str(i),[(x+13,-w*.4,12),(x+13,-w*.15,h*.44),(x+13,-w*.34,h*.84)],[1.2,1.6,.8],14,n=3,glow=True)
for i in range(10):
 x=-149+i*33;y=(-1 if i%2 else 1)*(55+(i%3)*4);octa('scattered angular rubble'+str(i),(x,y,8+i%3*4),(9,9,8+i%3*4),13)
for y in [-73,73]:tube('low mineral dust rim'+str(y),[(-150,y,2),(-80,y,7),(0,y,9),(85,y,6),(151,y,2)],[1.5,1.8,2,1.8,1],6,n=4,glow=True)
finish('TDPetVfxFaultRidge','地脉横断岩脊')
