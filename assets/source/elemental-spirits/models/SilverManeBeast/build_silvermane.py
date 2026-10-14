"""Original long-bodied metal-element beast. Existing MDX schema and primitives."""
from primitives import parts,mesh,ellipsoid,tube,leaf
import math,json,pathlib,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'original';OUT.mkdir(exist_ok=True)
PAL=['152039','30285a','444294','eea52f','f0e4c5','f2dfae','d67825','292951','ffd161','dba137','414ea2','e8ab34','f4e9ce','101629','f4bc35','fff0b4'];colors=[tuple(bytes.fromhex(s)) for s in PAL]
bones=[dict(name='Root',parent=-1,pivot=[0,0,0]),dict(name='Spine',parent=0,pivot=[-2,0,29]),dict(name='NarrowWolfHead',parent=1,pivot=[29,0,36]),dict(name='TailBase',parent=1,pivot=[-32,0,31]),dict(name='TailTip',parent=3,pivot=[-57,0,37]),dict(name='FrontLeft',parent=0,pivot=[20,11,26]),dict(name='FrontRight',parent=0,pivot=[20,-11,26]),dict(name='HindLeft',parent=0,pivot=[-23,10,26]),dict(name='HindRight',parent=0,pivot=[-23,-10,26]),dict(name='EarLeft',parent=2,pivot=[36,6,45]),dict(name='EarRight',parent=2,pivot=[36,-6,45])]
ellipsoid('long silver torso',(-4,0,29),(34,13,13),3,1,n=14,k=6)
ellipsoid('dark lean underside',(-1,0,23),(28,10,8),2,1,n=12,k=4)
ellipsoid('strong shoulders',(18,0,31),(13,15,16),4,1,n=12,k=5)
ellipsoid('haunch',(-25,0,29),(13,12,13),3,1,n=10,k=5)
tube('arched neck',[(22,0,31),(29,0,37),(36,0,39)],[11,10,8],4,2,n=10)
ellipsoid('slender wedge skull',(42,0,39),(13,9.5,10),8,2,n=12,k=5)
tube('tapered long muzzle',[(45,0,36),(53,0,34),(63,0,33)],[6.4,5.2,3.2],4,2,n=8)
ellipsoid('lower jaw',(53,0,31),(11,4.2,3.5),3,2,n=10,k=4)
ellipsoid('dark pointed nose',(64,0,33),(3.2,3.4,2.6),0,2,n=8,k=4)
for s in [-1,1]:
 ellipsoid('narrow eye socket '+str(s),(46,s*7.8,41.4),(4.4,1.2,2),0,2,n=8,k=3)
 ellipsoid('small amber iris '+str(s),(47,s*8.7,41.5),(2.1,.40,1.5),14,2,n=8,k=3)
 ellipsoid('slit pupil '+str(s),(47.4,s*9,41.5),(.4,.15,.87),13,2,n=6,k=3)
 tube('heavy slanted brow '+str(s),[(41,s*7.2,44.3),(45,s*8.2,43.5),(49,s*6.8,43.2)],[1.6,1.4,.9],2,2,n=6)
 tube('muzzle crease '+str(s),[(62,s*2.4,31.3),(54,s*4.6,30.6),(46,s*5.5,32)],[.3,.35,.25],1,2,n=5)
 # Thin blade-like ears and backward cheek tufts make a predatory, non-round face.
 leaf('silver pointed ear '+str(s),(35,s*5.8,44),(31,s*11,57),4.6,8,9 if s==1 else 10,bend=-1)
 leaf('dark ear inset '+str(s),(35.8,s*6,47),(32,s*10.2,55),2.2,2,9 if s==1 else 10,bend=-.2)
 leaf('cheek mane '+str(s),(35,s*6,37),(22,s*17,32),6,12,2,bend=2)
 leaf('shoulder silver tuft '+str(s),(18,s*11,36),(8,s*22,29),6,12,1,bend=1)
# Narrow overlapping steel plates, not an enclosing turtle shell.
for i,x in enumerate([19,7,-5,-17]):
 leaf('dorsal steel blade '+str(i),(x+5,0,40),(x-8,0,49 if i<2 else 44),7 if i<2 else 6,11,1,bend=1)
for s in [-1,1]:
 leaf('brass cheek flash '+str(s),(38,s*7,43),(31,s*10,51),2.0,9,2,bend=0)
tube('long flowing tail base',[(-30,0,31),(-43,1,33),(-56,2,39)],[7.8,9.2,8.1],3,3,n=9)
tube('silver brush tail',[(-55,2,39),(-67,3,46),(-79,4,48),(-84,4,44)],[8.4,8.2,4,.15],8,4,n=9)
leaf('tail steel tip',(-69,3,47),(-86,4,48),4.5,11,4,bend=1)
for i,(x,y) in enumerate([(20,11),(20,-11),(-23,10),(-23,-10)]):
 s=1 if y>0 else -1;fore=x>0;bi=5+i
 tube('bent long leg '+str(i),[(x,y,26),(x+(-4 if fore else 5),y+s*2,17),(x+(0 if fore else -3),y+s*3,8)],[5.1,4.2,3.4],3,bi,n=8)
 ellipsoid('long paw '+str(i),(x+3,y+s*3,5.4),(7.5,5,3.1),4,bi,n=8,k=4)
 for j in [-1,0,1]:ellipsoid('small steel claw '+str(i)+' '+str(j),(x+8,y+s*3+j*2,4.7),(2.5,.8,1.2),9,bi,n=5,k=3)
 ellipsoid('steel wrist '+str(i),(x,y+s*3,9),(4.1,4.1,2.8),10,bi,n=8,k=3)

seqs=[('Stand',0,2000,True),('Walk',2100,3100,True),('Attack',3200,3900,False),('Death',4000,5400,False),('Portrait',5500,7500,True)]
def q(axis,a):s=math.sin(a/2);return [axis[0]*s,axis[1]*s,axis[2]*s,math.cos(a/2)]
for bi,b in enumerate(bones):
 tracks={'KGTR':[],'KGRT':[],'KGSC':[]}
 for name,a,z,loop in seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name in ['Stand','Portrait']:
    if bi==1:tr[2]=.45*(1-math.cos(2*math.pi*u));sc=[1,1,1+.014*(1-math.cos(2*math.pi*u))]
    if bi==2:rot=q([0,0,1],.035*w)
    if bi==3:rot=q([0,0,1],.08*w)
    if bi==4:rot=q([0,0,1],.13*w)
    if bi in [9,10]:rot=q([1,0,0],(.05 if bi==9 else -.05)*w)
   elif name=='Walk':
    if bi==1:tr[2]=.7*(1-math.cos(4*math.pi*u));rot=q([1,0,0],.025*w)
    if bi==2:rot=q([0,1,0],.025*w)
    if bi in [3,4]:rot=q([0,0,1],(.1 if bi==3 else .16)*w)
    if bi in [5,6,7,8]:
     p=(0,.5,.5,0)[bi-5];v=math.sin(2*math.pi*(u+p));tr=[5.2*v,0,max(0,math.cos(2*math.pi*(u+p)))*3.2];rot=q([0,1,0],-.035*v)
   elif name=='Attack':
    k=math.sin(math.pi*u)
    if bi==1:tr=[5*k,0,1.8*k]
    if bi==2:tr=[6*k,0,0];rot=q([0,1,0],.12*k)
    if bi in [5,6]:tr=[4*k,0,1.5*k]
    if bi in [3,4]:rot=q([0,0,1],-.15*k)
   else:
    e=3*u*u-2*u*u*u
    if bi==0:tr=[0,0,-3.5*e]
    if bi==1:tr=[-2*e,0,-4.5*e];rot=q([1,0,0],.08*e)
    if bi==2:rot=q([0,1,0],.38*e)
    if bi in [5,6,7,8]:sc=[1,1,1-.13*e]
    if bi in [3,4]:rot=q([0,0,1],.20*e)
    if bi in [9,10]:rot=q([0,1,0],-.3*e)
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:tracks[tag].append([t,val])
 b['tracks']=tracks
# Display-only animations append keys after all five original intervals.
# Original 85 keys per track stay byte-identical after Float32 encoding.
display_seqs=[('Display Float',8000,10000,True),('Display Jump',10100,10900,False),('Display Spin',11000,12200,False),('Display Sleep',12300,15300,True),('Display Cast',15400,16600,False)]
for bi,b in enumerate(bones):
 for name,a,z,loop in display_seqs:
  for i in range(17):
   u=i/16;t=round(a+(z-a)*u);w=math.sin(2*math.pi*u);pulse=math.sin(math.pi*u)
   tr=[0,0,0];rot=[0,0,0,1];sc=[1,1,1]
   if name=='Display Float':
    if bi==0:tr[2]=4+2.5*w
    if bi==1:rot=q([1,0,0],.025*w)
    if bi in [3,4]:rot=q([0,0,1],(.10 if bi==3 else .18)*w)
    if bi in [5,6,7,8]:rot=q([0,1,0],.10)
   elif name=='Display Jump':
    if bi==0:tr[2]=22*pulse
    if bi==1:rot=q([0,1,0],-.12*math.sin(2*math.pi*u))
    if bi in [5,6,7,8]:tr[2]=5*pulse;rot=q([0,1,0],(.18 if bi<7 else -.18)*pulse)
    if bi in [3,4]:rot=q([0,1,0],-.18*pulse)
   elif name=='Display Spin':
    if bi==0:rot=q([0,0,1],2*math.pi*u);tr[2]=3*pulse
    if bi in [3,4]:rot=q([0,0,1],-.28*pulse)
   elif name=='Display Sleep':
    if bi==0:tr[2]=-2
    if bi==1:tr[2]=-8+.45*w
    if bi==2:rot=q([0,1,0],.32+.025*w)
    if bi in [5,6,7,8]:sc=[1,1,.70];rot=q([0,1,0],(.15 if bi<7 else -.15))
    if bi in [3,4]:rot=q([0,0,1],.35+.035*w)
    if bi in [9,10]:rot=q([0,1,0],-.25)
   elif name=='Display Cast':
    if bi==0:tr[2]=4*pulse
    if bi==1:rot=q([0,1,0],-.16*pulse)
    if bi==2:rot=q([0,1,0],-.20*pulse)
    if bi in [5,6]:tr[2]=6*pulse;rot=q([0,1,0],-.22*pulse)
    if bi in [3,4]:rot=q([0,0,1],(.15 if bi==3 else .25)*math.sin(4*math.pi*u))
   for tag,val in [('KGTR',tr),('KGRT',rot),('KGSC',sc)]:b['tracks'][tag].append([t,val])
seqs+=display_seqs
attachments=[dict(name='Origin Ref',parent=0,pivot=[0,0,0],attachmentId=0),dict(name='Head Ref',parent=2,pivot=[43,0,49],attachmentId=1)]
(OUT/'silvermane-source.json').write_text(json.dumps(dict(name='SilverManeBeast_Cartoon_v2',version=800,parts=parts,bones=bones,sequences=[dict(name=n,start=a,end=z,loop=lo) for n,a,z,lo in seqs],palette=colors,attachments=attachments)))
# Approved vivid cartoon direction. Imagegen-authored 4x4 atlas, resized only;
# existing padded tile UVs remain valid and preserve the single-texture budget.
atlas=Image.open(ROOT/'SilverManeAtlas_painted.png').convert('RGB').resize((256,256),Image.Resampling.LANCZOS)
atlas.save(OUT/'SilverManeAtlas_source.png');quant=atlas.quantize(colors=256,method=Image.Quantize.MEDIANCUT);pal=quant.getpalette();offsets=[0]*16;sizes=[0]*16;blobs=[];off=1180
for i in range(9):
 sz=max(1,256>>i);idx=atlas.resize((sz,sz),Image.Resampling.BOX).quantize(palette=quant,dither=Image.Dither.NONE).tobytes();offsets[i]=off;sizes[i]=len(idx);off+=len(idx);blobs.append(idx)
(OUT/'SilverManeAtlas.blp').write_bytes(b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],255]) for i in range(256))+b''.join(blobs))
print(json.dumps({'triangles':sum(len(p['faces']) for p in parts),'bones':len(bones)}))
