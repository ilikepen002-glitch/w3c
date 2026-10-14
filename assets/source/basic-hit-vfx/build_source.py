"""Original mesh-only short hit samples. Existing atlas bytes are reused unchanged."""
from pathlib import Path
import math,json
ROOT=Path(__file__).resolve().parent
models=[]
def new(name,color,hold):
 return dict(name=name,color=color,holdMs=hold,parts=[],texture='Textures\\TDPetVfxAtlas.blp')
def wedge(m,name,outline,z,depth,core=False):
 n=len(outline);vs=[[x,y,z-depth/2] for x,y in outline]+[[x,y,z+depth/2] for x,y in outline]
 # Outlines below are convex; fan triangulation is deterministic.
 faces=[]
 for i in range(1,n-1):faces.extend([[0,i+1,i],[n,n+i,n+i+1]])
 for i in range(n):j=(i+1)%n;faces.extend([[i,j,n+j],[i,n+j,n+i]])
 m['parts'].append(dict(name=name,vertices=vs,faces=faces,core=core))
m=new('TDPetHitGoldCrescent',[1,.67,.12],100)
# Segmented broad crescent: a physical blade, with narrow bright inner edge.
for core in [False,True]:
 for i in range(7):
  a=math.radians(-65+i*23);b=a+math.radians(23);r=80;wa=2+25*math.sin(math.pi*i/7);wb=2+25*math.sin(math.pi*(i+1)/7)
  ia=r-wa;ib=r-wb;oa=r;ob=r
  if core:oa=ia+4;ob=ib+4;ia-=1;ib-=1
  wedge(m,('edge' if core else 'blade')+str(i),[[ia*math.cos(a),ia*math.sin(a)],[oa*math.cos(a),oa*math.sin(a)],[ob*math.cos(b),ob*math.sin(b)],[ib*math.cos(b),ib*math.sin(b)]],36 if core else 35,3,core)
# Two deliberately pointed detached streaks are silhouettes, not particles.
for i,(x,y) in enumerate([(-24,-32),(-37,9)]):wedge(m,'sharp glint'+str(i),[[x-29,y-3],[x+23,y+2],[x-20,y+8]],42,2,True)
models.append(m)
m=new('TDPetHitFireCrown',[1,.19,.015],150)
# Six jagged radial flame tips surround a white-hot triangular core, with negative space.
for i in range(6):
 a=math.radians(i*60+15);rad=66 if i%2==0 else 51
 poly=[(15,-7),(rad,-4),(rad-13,7),(20,12)]
 p=[[x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)] for x,y in poly]
 wedge(m,'flame tooth'+str(i),p,30+(i%2)*7,9)
for i in range(3):
 a=math.radians(i*120);p=[(-8,-10),(40,0),(-8,10)]
 wedge(m,'white-hot core'+str(i),[[x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)] for x,y in p],43,5,True)
models.append(m)
# Crossed leaf blades and four short thorn tips, independent from active roots.
m=new('TDPetHitWoodThorns',[.12,.83,.23],200)
for i in range(4):
 a=math.radians(25+i*90);p=[(-10,-6),(56,0),(20,15),(-7,7)]
 wedge(m,'leaf blade'+str(i),[[x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)] for x,y in p],29+i*3,5)
for i in range(4):
 a=math.radians(70+i*90);p=[(27,-3),(68,0),(33,5)]
 wedge(m,'thorn'+str(i),[[x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)] for x,y in p],40,3,True)
models.append(m)
# Thin hooked ice crescent with three detached crystal shards.
m=new('TDPetHitWaterShards',[.08,.64,1],180)
for i in range(6):
 a=math.radians(-75+i*25);b=a+math.radians(25)
 wedge(m,'ice arc'+str(i),[[r*math.cos(t),r*math.sin(t)] for r,t in [(51,a),(67,a),(67,b),(51,b)]],28,6)
for i,(x,y,a) in enumerate([(-20,-30,-.4),(-40,7,.2),(-17,34,.7)]):
 p=[(-7,-8),(28,0),(-5,8)]
 wedge(m,'crystal'+str(i),[[x+u*math.cos(a)-v*math.sin(a),y+u*math.sin(a)+v*math.cos(a)] for u,v in p],40,8,True)
models.append(m)
# Low, disconnected rock slabs and mineral seams, no active-skill ridge.
m=new('TDPetHitEarthFault',[.70,.39,.09],200)
for i,(x,y,a) in enumerate([(-36,-19,-.4),(9,-15,.2),(-20,24,.4),(31,23,-.2)]):
 p=[(-20,-12),(16,-10),(23,6),(0,13),(-23,5)]
 wedge(m,'slab'+str(i),[[x+u*math.cos(a)-v*math.sin(a),y+u*math.sin(a)+v*math.cos(a)] for u,v in p],14+i*3,12)
for i in range(3):
 a=math.radians(i*120+20);p=[(3,-2),(57,-1),(28,4)]
 wedge(m,'mineral seam'+str(i),[[x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)] for x,y in p],30,2,True)
models.append(m)
for m in models:
 m['lifetimeMs']=m['holdMs']+80
 m['triangles']=sum(len(p['faces']) for p in m['parts']);assert m['triangles']<=200,m['triangles']
 (ROOT/(m['name']+'-source.json')).write_text(json.dumps(m,indent=2));print(m['name'],m['triangles'])
