"""Original mesh, rig, palette and keyframes. No imported artistic assets."""
import json, math, pathlib, struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

ROOT=pathlib.Path(__file__).resolve().parent
(ROOT/'original').mkdir(exist_ok=True)
OUT=ROOT/'original'
PAL=['24322c','35443b','57664a','73835a','97a774','bdba8c','65765c','7b6c4c','c0ae7f','8c9974','80632f','b5964d','dac38a','142020','e4ad35','f2efd2']
colors=[tuple(bytes.fromhex(x)) for x in PAL]
parts=[]
def mesh(name,verts,faces,col,bone,smooth=False,facecols=None):
    parts.append(dict(name=name,verts=verts,faces=faces,color=col,bone=bone,smooth=smooth,facecols=facecols))
def ellipsoid(name,c,r,col,bone,n=10,k=5):
    v=[(c[0],c[1],c[2]-r[2])]
    for j in range(1,k):
        p=-math.pi/2+j*math.pi/k
        for i in range(n):
            a=2*math.pi*i/n
            v.append((c[0]+r[0]*math.cos(p)*math.cos(a),c[1]+r[1]*math.cos(p)*math.sin(a),c[2]+r[2]*math.sin(p)))
    v.append((c[0],c[1],c[2]+r[2])); f=[]
    for i in range(n): f.append((0,1+(i+1)%n,1+i))
    for j in range(k-2):
        for i in range(n):
            a=1+j*n+i;b=1+j*n+(i+1)%n;c1=a+n;d=b+n
            f.extend([(a,b,d),(a,d,c1)])
    top=len(v)-1
    for i in range(n): f.append((top,1+(k-2)*n+i,1+(k-2)*n+(i+1)%n))
    mesh(name,v,f,col,bone,True)
def tube(name,centers,radii,col,bone,n=8):
    v=[]
    for j,(c,r) in enumerate(zip(centers,radii)):
        t=np.array(centers[min(j+1,len(centers)-1)])-np.array(centers[max(j-1,0)])
        t=t/np.linalg.norm(t); axis=np.array([0.,1.,0.])
        if abs(np.dot(axis,t))>.9: axis=np.array([1.,0.,0.])
        a=np.cross(t,axis);a/=np.linalg.norm(a);b=np.cross(t,a)
        for i in range(n):
            ang=2*math.pi*i/n;v.append((np.array(c)+r*(a*math.cos(ang)+b*math.sin(ang))).tolist())
    f=[]
    for j in range(len(centers)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;f.extend([(a,b,b+n),(a,b+n,a+n)])
    for i in range(1,n-1):f.extend([(0,i+1,i),((len(centers)-1)*n,(len(centers)-1)*n+i,(len(centers)-1)*n+i+1)])
    mesh(name,v,f,col,bone,True)
def crystal(name,c,r,h,tilt,col=10):
    n=5;v=[]
    for z,rr,off in [(0,r,0),(h*.62,r*.82,tilt*.62)]:
        for i in range(n):
            a=2*math.pi*i/n+.2;v.append((c[0]+rr*math.cos(a)+off,c[1]+rr*math.sin(a),c[2]+z))
    v.append((c[0]+tilt,c[1],c[2]+h));f=[];fc=[]
    for i in range(n):
        j=(i+1)%n;f.extend([(i,j,j+n),(i,j+n,i+n),(i+n,j+n,2*n)]);fc.extend([col+(i%2),col+(i%2),11+(i%2)])
    for i in range(1,n-1):f.append((0,i+1,i));fc.append(col)
    mesh(name,v,f,col,1,False,fc)

# Rig nodes use fixed rest-pose pivots; all animation keys are exported into MDX.
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='Body',parent=0,pivot=[0,0,24]),dict(name='Head',parent=1,pivot=[31,0,24]),dict(name='Tail',parent=1,pivot=[-33,0,18])]
for name,x,y in [('FrontLeft',23,20),('FrontRight',23,-20),('BackLeft',-24,19),('BackRight',-24,-19)]:bones.append(dict(name=name,parent=0,pivot=[x,y,23]))

ellipsoid('soft undershell',(-1,0,23),(35,25,14),2,1,n=12,k=5)
ellipsoid('ochre plastron',(0,0,13),(31,24,5),7,1,n=12,k=4)
# Continuous domed shell, not boxes.
v=[];n=16;rings=[(1.,23),(.97,30),(.78,43),(.43,51),(.05,54)]
for rr,z in rings:
    for i in range(n):
        a=2*math.pi*i/n;v.append((39*rr*math.cos(a),30*rr*math.sin(a),z))
f=[]
for j in range(len(rings)-1):
    for i in range(n):a=j*n+i;b=j*n+(i+1)%n;f.extend([(a,b,b+n),(a,b+n,a+n)])
# Seal the two shell ring openings without moving any existing vertex.
for i in range(1,n-1):f.extend([(0,i+1,i),((len(rings)-1)*n,(len(rings)-1)*n+i,(len(rings)-1)*n+i+1)])
mesh('arched continuous dark shell',v,f,1,1)
def zshell(x,y):return 24+29*math.sqrt(max(.02,1-(x/40)**2-(y/31)**2))
def scute(name,cx,cy,rx,ry,col):
    points=[(cx+rx*math.cos(a),cy+ry*math.sin(a)) for a in [math.pi*i/3 for i in range(6)]]
    v=[(x,y,zshell(x,y)+.35) for x,y in points]
    v += [(cx+(x-cx)*.81,cy+(y-cy)*.81,zshell(cx+(x-cx)*.81,cy+(y-cy)*.81)+1.9) for x,y in points]
    v.append((cx,cy,zshell(cx,cy)+2.8));f=[];fc=[]
    for i in range(6):j=(i+1)%6;f.extend([(i,j,j+6),(i,j+6,i+6),(i+6,j+6,12)]);fc.extend([1,3,col])
    for i in range(1,5):f.append((0,i+1,i));fc.append(1)
    mesh(name,v,f,col,1,False,fc)
for i,x in enumerate([-22,0,22]):scute('central stone scute '+str(i),x,0,11.7,12,6 if i%2 else 9)
for side in [-1,1]:
    for i,x in enumerate([-25,-9,9,25]):scute('side stone scute '+str(side)+' '+str(i),x,side*(16 if abs(x)>20 else 19),8.1,8.1,6 if i%2 else 9)
# Rim overlaps gracefully and reads as broad turtle shell silhouette.
for i in range(16):
    a=2*math.pi*i/16;b=2*math.pi*(i+1)/16
    verts=[(39*math.cos(a),30*math.sin(a),23),(39*math.cos(b),30*math.sin(b),23),(38*math.cos(b),29*math.sin(b),28),(38*math.cos(a),29*math.sin(a),28)]
    mesh('shell rim '+str(i),verts,[(0,1,2),(0,2,3)],7+(i%2),1)
crystal('rear amber spine',(-22,0,51),5,13,-3)
crystal('central amber spine',(-2,0,57),6.5,21,-3)
crystal('front amber spine',(19,0,54),4.8,14,-2)

# Short supple neck, blunt muzzle, small beak, expressive eyes and brow.
ellipsoid('neck',(34,0,23),(14,10,10),2,2,n=10,k=4)
ellipsoid('head',(46,0,25),(13,11,11),4,2,n=12,k=6)
ellipsoid('muzzle',(55,0,22),(7,8,5.8),5,2,n=10,k=4)
ellipsoid('nose beak',(60,0,22.5),(2.4,4.8,3.4),7,2,n=8,k=4)
for side in [-1,1]:
    ellipsoid('eye socket '+str(side),(49,side*9.25,29.2),(4.3,1.9,4.1),0,2,n=8,k=4)
    ellipsoid('amber iris '+str(side),(50.25,side*10.5,29.4),(2.8,.85,2.75),14,2,n=8,k=4)
    ellipsoid('pupil '+str(side),(51.1,side*11.08,29.7),(1.15,.35,2.15),13,2,n=8,k=3)
    ellipsoid('eye glint '+str(side),(51.2,side*11.38,30.8),(.6,.2,.65),15,2,n=6,k=3)
    tube('brow '+str(side),[(44.5,side*8.6,33),(49,side*10.4,33.4),(53.8,side*8,32.5)],[1.6,2.,1.4],3,2,n=6)
    tube('mouth crease '+str(side),[(60,side*1.1,20.7),(57,side*6.5,19.8),(51.5,side*8.4,20.5)],[.4,.45,.35],1,2,n=5)
    ellipsoid('nostril '+str(side),(61.9,side*2,24),(.7,.7,.5),1,2,n=6,k=3)

# Splayed, bent, short thick legs; each has real animation tracks.
for i,(x,y) in enumerate([(23,20),(23,-20),(-24,19),(-24,-19)]):
    s=1 if y>0 else -1;fore=x>0;bone=i+4
    centers=[(x,y,23),(x+(4 if fore else -4),y+8*s,16),(x+(0 if fore else -2),y+12*s,9)]
    tube('bent leg '+str(i),centers,[6.2,7.0,6.3],2,bone,n=8)
    ellipsoid('broad padded foot '+str(i),(x+3,y+12*s,6.5),(9,7,5),3,bone,n=8,k=4)
    for j,off in enumerate([-4,0,4]):
        ellipsoid('toe claw '+str(i)+' '+str(j),(x+10,y+12*s+off,5.2),(3.6,1.6,2),8,bone,n=6,k=3)
    # Pebble-like knee cap, not a cube.
    ellipsoid('leg scale '+str(i),(x+1,y+14*s,12.2),(5.5,2.3,3.6),4,bone,n=8,k=3)
tube('tapered tail',[(-32,0,19),(-41,0,16),(-50,1,12),(-54,2,13)],[5,3.6,1.9,.15],3,3,n=8)

# Style calibration only: preserve topology and skeleton; exaggerate face and claws.
for p in parts:
    if p['bone']==2:
        p['verts']=[(39+(v[0]-39)*1.10,v[1]*1.10,24+(v[2]-24)*1.10) for v in p['verts']]
    if p['name'].startswith('toe claw'):
        c=np.array(p['verts']).mean(0);p['verts']=[(c+(np.array(v)-c)*[1.35,1.10,1.15]).tolist() for v in p['verts']]

seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def qaxis(axis,ang):
    s=math.sin(ang/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(ang/2)]
for bi,b in enumerate(bones):
    tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
    for name,a,z,loop in seqs:
        count=16 if name=='Walk' else 12
        for i in range(count+1):
            u=i/count;t=round(a+(z-a)*u);wave=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
            if name in ['Stand','Portrait']:
                if bi==1:tr[2]=.55*(1-math.cos(2*math.pi*u));sc=[1,1,1+.018*(1-math.cos(2*math.pi*u))]
                if bi==2:rot=qaxis([0,1,0],.035*wave);tr[0]=.3*wave
                if bi==3:rot=qaxis([0,0,1],.07*wave)
            elif name=='Walk':
                if bi==1:tr[2]=.7*(1-math.cos(4*math.pi*u));rot=qaxis([1,0,0],.025*wave)
                if bi==2:rot=qaxis([0,1,0],.06*wave)
                if bi==3:rot=qaxis([0,0,1],.14*wave)
                if bi>=4:
                    phase=(0,.5,.5,0)[bi-4];v=math.sin(2*math.pi*(u+phase));tr=[4.8*v,0,max(0,math.cos(2*math.pi*(u+phase)))*3.5];rot=qaxis([0,1,0],-.08*v)
            elif name=='Attack':
                kick=math.sin(math.pi*min(1,max(0,(u-.18)/.7)))
                if bi==1:tr=[2.5*kick,0,-1.2*kick]
                if bi==2:tr=[7*kick,0,1.5*kick];rot=qaxis([0,1,0],-.16*kick)
                if bi>=4:rot=qaxis([0,1,0],.08*kick)
            elif name=='Death':
                e=3*u*u-2*u*u*u
                if bi==0:tr=[0,0,12*e];rot=qaxis([1,0,0],.43*e)
                if bi==2:tr=[-5*e,0,-2*e];rot=qaxis([0,1,0],.17*e)
                if bi==3:rot=qaxis([0,0,1],.2*e)
                if bi>=4:tr=[(-4 if bi<6 else 4)*e,(-3 if bi%2==0 else 3)*e,2*e];rot=qaxis([0,1,0],(-.25 if bi<6 else .25)*e)
            tracks['KGTR'].append([t,tr]);tracks['KGRT'].append([t,rot]);tracks['KGSC'].append([t,sc])
    b['tracks']=tracks

data=dict(name='RockShellTurtle_Original_v2',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=b,loop=loop) for n,a,b,loop in seqs],palette=colors)
(OUT/'rockturtle-source.json').write_text(json.dumps(data))

# Refined atlas is the persisted built-in imagegen output. Resize/BLP encoding only.
import runpy
runpy.run_path(str(ROOT.parents[4]/'tools/EncodeWaterEarthAtlas.py'))['encode'](OUT/'atlas-refined-imagegen.png',OUT/'RockTurtlePalette_source.png',OUT/'RockTurtlePalette.blp')
