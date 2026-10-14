"""Project-original, deterministic MDX800 active-core mesh and animation sources.
Geometry only; no bitmap edits, emitters, sounds, gameplay or runtime changes.
"""
from pathlib import Path
import json, math, struct
R = Path(__file__).resolve().parent
OUT = R / 'generated-source'
OUT.mkdir(exist_ok=True)
WHITE = 'Textures\\TDPetVfxSolidWhite.blp'

def point(r, a, z=6):
    return [r*math.cos(a), r*math.sin(a), z]

def transform(vs, a, center=(0,0,0)):
    return [[center[0]+x*math.cos(a)-y*math.sin(a), center[1]+x*math.sin(a)+y*math.cos(a), center[2]+z] for x,y,z in vs]

def signed_volume(vs, fs):
    return sum((vs[a][0]*(vs[b][1]*vs[c][2]-vs[b][2]*vs[c][1])+vs[a][1]*(vs[b][2]*vs[c][0]-vs[b][0]*vs[c][2])+vs[a][2]*(vs[b][0]*vs[c][1]-vs[b][1]*vs[c][0]))/6 for a,b,c in fs)

def surface(g, name, vs, fs, bone=0):
    # Ground polygons face the normal Warcraft camera, without TwoSided.
    if max(v[2] for v in vs)-min(v[2] for v in vs)<1e-8:
        a,b,c=(vs[i] for i in fs[0]); nz=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        if nz<0: fs=[list(reversed(f)) for f in fs]
    g['parts'].append(dict(name=name, vertices=vs, faces=fs, bone=bone, closed=False))

def prism(g, name, outline, offset, bone=0):
    n=len(outline)
    vs=[list(v) for v in outline]+[[v[k]+offset[k] for k in range(3)] for v in outline]
    fs=[]
    for i in range(1,n-1): fs.extend([[0,i+1,i], [n,n+i,n+i+1]])
    for i in range(n):
        j=(i+1)%n
        fs.extend([[i,j,n+j], [i,n+j,n+i]])
    if signed_volume(vs,fs)<0: fs=[list(reversed(f)) for f in fs]
    g['parts'].append(dict(name=name, vertices=vs, faces=fs, bone=bone, closed=True))

def solid(g,name,vs,fs,bone=0):
    if signed_volume(vs,fs)<0: fs=[list(reversed(f)) for f in fs]
    g['parts'].append(dict(name=name,vertices=vs,faces=fs,bone=bone,closed=True))

def quat_z(a): return [0,0,math.sin(a/2),math.cos(a/2)]
def quat_axis(axis,a): return [*(x*math.sin(a/2) for x in axis),math.cos(a/2)]
def track(tag, entries, interpolation=1): return dict(tag=tag, entries=entries, interpolation=interpolation)
def ga(name,mat,color,alpha): return dict(name=name, material=mat, color=color, alpha=alpha, parts=[])
def model(name,skill,radius,end,bounds): return dict(name=name,skill=skill,radius=radius,endMs=end,texture=WHITE,bounds=bounds,bones=[],geosets=[],loop=False)
def bone(m,name,pivot=(0,0,0),translation=None,scale=None,rotation=None):
    end=m['endMs']; tracks=[]
    for tag,seq,default in [('KGTR',translation,[0,0,0]),('KGSC',scale,[1,1,1]),('KGRT',rotation,[0,0,0,1])]:
        if seq is not None:
            tracks.append(track(tag,seq+[[10000,seq[-1][1]],[10001,seq[-1][1]]]))
    m['bones'].append(dict(name=name,pivot=list(pivot),tracks=tracks))
    return len(m['bones'])-1

m=model('TDPetVfxFrostPrison',29,240,1300,dict(min=[-241,-241,0],max=[241,241,280]))
bone(m,'WarningIceFloor',scale=[[0,[1,1,1]],[150,[.985,.985,1]],[350,[1,1,1]],[599,[.99,.99,1]],[600,[1,1,1]],[950,[1,1,1]],[1300,[1,1,1]]])
warning=ga('warning-floor',0,[.055,.47,.76],[[0,.62],[599,.62],[600,.82],[949,.82],[950,.75],[1160,.22],[1240,0],[1300,0]])
lines=ga('warning-runes',1,[.48,.92,1],[[0,.72],[599,.72],[600,1],[949,1],[950,1],[1150,.26],[1240,0],[1300,0]])
mirror=ga('frozen-mirrors',0,[.14,.63,.94],[[0,0],[599,0],[600,.90],[949,.90],[950,1],[1080,.60],[1220,0],[1300,0]])
shards=ga('frozen-shard-cores',1,[.74,.95,1],[[0,0],[599,0],[600,.88],[949,.88],[950,1],[1080,.65],[1220,0],[1300,0]])
# Twelve angular boundary facets. Outer radius 236 is inside actual radius 240.
for i in range(12):
    a=i*math.tau/12; b=(i+1)*math.tau/12
    surface(warning,'boundary-facet-'+str(i),[point(222,a),point(236,a),point(236,b),point(222,b)],[[0,1,2],[0,2,3]])
    mid=(a+b)/2
    surface(lines,'rim-rune-'+str(i),[point(209,mid-.022,7),point(233,mid,7),point(209,mid+.022,7)],[[0,1,2]])
for i in range(6):
    a=i*math.tau/6
    surface(warning,'frost-star-arm-'+str(i),transform([[22,-11,5],[205,-20,5],[221,0,5],[205,20,5],[22,11,5]],a),[[0,1,2],[0,2,3],[0,3,4]])
    for side in [-1,1]:
        surface(lines,'snowflake-fork-'+str(i)+'-'+str(side),transform([[92,side*3,8],[148,side*38,8],[157,side*35,8],[100,side*1,8]],a),[[0,1,2],[0,2,3]] if side==1 else [[2,1,0],[3,2,0]])
    center=point(172,a,0); axis=[-math.sin(a),math.cos(a),0]
    b=bone(m,'MirrorShard'+str(i),pivot=center,
           translation=[[0,[0,0,0]],[949,[0,0,0]],[950,[0,0,0]],[1080,[18*math.cos(a),18*math.sin(a),22]],[1220,[21*math.cos(a),21*math.sin(a),29]],[1300,[21*math.cos(a),21*math.sin(a),29]]],
           rotation=[[0,[0,0,0,1]],[949,[0,0,0,1]],[950,[0,0,0,1]],[1080,quat_axis(axis,.11)],[1220,quat_axis(axis,.17)],[1300,quat_axis(axis,.17)]])
    # Broad triangular glass pane and one narrow taller ice needle; actual closed solids.
    h=165+(i%2)*16
    outline=transform([[-8,-34,9],[-8,34,9],[-8,0,h]],a,center)
    prism(mirror,'mirror-pane-'+str(i),outline,[16*math.cos(a),16*math.sin(a),0],b)
    outline=transform([[-72,-11,10],[-72,11,10],[-72,0,224+(i%2)*8]],a,center)
    prism(shards,'ice-needle-'+str(i),outline,[9*math.cos(a),9*math.sin(a),0],b)
m['geosets']=[warning,lines,mirror,shards]
m['phaseContract']=dict(warningMs=0,freezeMs=600,fractureMs=950,fullyTransparentMs=1240,holdMs=1300)
(R/'generated-source'/ (m['name']+'.json')).write_text(json.dumps(m,separators=(',',':')))

m=model('TDPetVfxStarfall',33,240,4000,dict(min=[-241,-241,0],max=[241,241,750]))
bone(m,'WarningGround',scale=[[0,[1,1,1]],[250,[.985,.985,1]],[500,[1,1,1]],[749,[1,1,1]],[750,[1,1,1]],[4000,[1,1,1]]])
meteor_bone=bone(m,'FallingStar',translation=[[0,[0,0,520]],[50,[0,0,488]],[400,[0,0,260]],[749,[0,0,43]],[750,[0,0,42]],[4000,[0,0,42]]],rotation=[[0,quat_z(0)],[750,quat_z(1.8)],[4000,quat_z(1.8)]])
fire_bone=bone(m,'BurningGround',scale=[[0,[1,1,1]],[750,[1,1,.65]],[950,[1,1,1]],[1250,[1,1,.72]],[1750,[1,1,1]],[2250,[1,1,.76]],[2750,[1,1,1]],[3250,[1,1,.76]],[3749,[1,1,1]],[3750,[1,1,.4]],[4000,[1,1,.4]]])
impact_bone=bone(m,'ImpactBurst',scale=[[0,[.50,.50,.5]],[749,[.50,.50,.5]],[750,[.6,.6,.6]],[900,[1,1,1]],[1150,[1,1,.3]],[4000,[1,1,.3]]])
warning=ga('warning-sigil',0,[.68,.23,.015],[[0,.70],[749,.70],[750,.25],[950,0],[4000,0]])
warning_glow=ga('warning-star-lines',1,[1,.55,.06],[[0,.70],[749,.70],[750,1],[950,0],[4000,0]])
meteor=ga('falling-meteor-body',0,[.88,.20,.025],[[0,1],[749,1],[750,.50],[900,0],[4000,0]])
trail=ga('falling-meteor-core-and-tail',1,[1,.79,.26],[[0,.90],[749,.90],[750,0],[4000,0]])
burn=ga('burning-cracked-ground',0,[.43,.065,.01],[[0,0],[749,0],[750,.88],[3749,.88],[3750,.45],[4000,0]])
burn['colorKeys']=[[0,[.43,.065,.01]],[3749,[.43,.065,.01]],[3750,[.16,.13,.10]],[4000,[.16,.13,.10]]]
flames=ga('burning-flames',1,[1,.37,.03],[[0,0],[749,0],[750,.86],[3749,.86],[3750,0],[4000,0]])
impact=ga('impact-fractures',1,[1,.87,.40],[[0,0],[749,0],[750,1],[900,.65],[1150,0],[4000,0]])
for i in range(12):
    a=i*math.tau/12;b=(i+1)*math.tau/12;mid=(a+b)/2
    # Jagged star-shaped edge instead of a reskinned frost ring.
    surface(warning,'warning-tooth-'+str(i),[point(182,a,5),point(236,mid,5),point(182,b,5)],[[0,1,2]])
    if i%2==0:
        surface(warning_glow,'inward-fall-guide-'+str(i),[point(175,mid-.045,8),point(66,mid,8),point(175,mid+.045,8)],[[2,1,0]])
    surface(burn,'lava-fragment-'+str(i),[point(38,a+.018,5),point(194,a+.018,5),point(225,mid,5),point(194,b-.018,5),point(38,b-.018,5)],[[0,1,2],[0,2,3],[0,3,4]],fire_bone)
# Eight-sided uneven boulder, closed and flat shaded.
vs=[[0,0,-39],[0,0,53]]+[point(47+(i%3)*4,i*math.tau/8,3+(i%2)*5) for i in range(8)]
fs=[]
for i in range(8):j=(i+1)%8;fs.extend([[0,2+j,2+i],[1,2+i,2+j]])
solid(meteor,'falling-eight-sided-star',vs,fs,meteor_bone)
# Actual narrow pyramidal tail, attached to the same falling bone.
vs=[[0,0,167]]+[point(23,i*math.tau/6,24) for i in range(6)]+[[0,0,24]]
fs=[]
for i in range(6):j=(i+1)%6;fs.extend([[0,1+i,1+j],[7,1+j,1+i]])
solid(trail,'tapered-fall-trail',vs,fs,meteor_bone)
for i in range(6):
    a=i*math.tau/6
    surface(trail,'meteor-hot-vein-'+str(i),transform([[28,-4,-16],[52,-3,5],[29,4,33]],a),[[0,1,2]],meteor_bone)
for i in range(8):
    a=(i+.5)*math.tau/8;r=105 if i%2==0 else 171;center=point(r,a,0)
    h=73 if i%2==0 else 52
    outline=transform([[-10,-14,6],[17,11,6],[11,0,h]],a,center)
    prism(flames,'low-lava-flame-'+str(i),outline,[4*math.cos(a),4*math.sin(a),0],fire_bone)
for i in range(8):
    a=i*math.tau/8
    surface(impact,'radial-impact-scar-'+str(i),transform([[53,-7,9],[225,-3,9],[172,9,9]],a),[[0,1,2]],impact_bone)
m['geosets']=[warning,warning_glow,meteor,trail,burn,flames,impact]
m['phaseContract']=dict(warningMs=0,initialMeteorTranslationZ=520,impactMs=750,burnStartMs=750,lastDamageMs=3750,flamesTransparentMs=3750,ashTailEndMs=4000,holdMs=4000)
(OUT/(m['name']+'.json')).write_text(json.dumps(m,separators=(',',':')))

# Minimal project-original opaque white BLP1. No pre-existing texture is modified.
w=h=4;palette=bytes([255,255,255,0])+bytes(255*4);payload=[];offsets=[];sizes=[];cursor=1180
for wh in [(4,4),(2,2),(1,1)]:
    data=bytes(wh[0]*wh[1])+bytes([255])*(wh[0]*wh[1]);offsets.append(cursor);sizes.append(len(data));payload.append(data);cursor+=len(data)
header=b'BLP1'+struct.pack('<6I',1,8,w,h,5,1)+struct.pack('<16I',*(offsets+[0]*13))+struct.pack('<16I',*(sizes+[0]*13))
(R/'output').mkdir(exist_ok=True)
(R/'output'/'TDPetVfxSolidWhite.blp').write_bytes(header+palette+b''.join(payload))
for f in OUT.glob('*.json'):
    m=json.loads(f.read_text());count=sum(len(p['faces']) for g in m['geosets'] for p in g['parts']);assert count<=250,(m['name'],count); print(m['name'],count,'triangles',len(m['bones']),'bones')

# Reliable cores use semantic-neutral looping motion. They cannot imply a timed
# freeze/impact when the gameplay phase fence or a native admission is delayed.
loop_end=2000
m=model('TDPetVfxFrostDomain',29,240,loop_end,dict(min=[-241,-241,0],max=[241,241,105]));m['loop']=True
bone(m,'FrostFieldFloor',scale=[[0,[1,1,1]],[500,[.985,.985,1]],[1000,[1,1,1]],[1500,[.985,.985,1]],[2000,[1,1,1]]])
bone(m,'FloatingFrostFacets',translation=[[0,[0,0,0]],[500,[0,0,13]],[1000,[0,0,0]],[1500,[0,0,13]],[2000,[0,0,0]]],rotation=[[0,quat_z(-.035)],[500,quat_z(.035)],[1000,quat_z(-.035)],[1500,quat_z(.035)],[2000,quat_z(-.035)]])
floor=ga('cold-field-floor',0,[.055,.47,.76],[[0,.58],[500,.68],[1000,.58],[1500,.68],[2000,.58]])
runes=ga('cold-field-runes',1,[.48,.92,1],[[0,.72],[500,.86],[1000,.72],[1500,.86],[2000,.72]])
facets=ga('floating-cold-facets',0,[.22,.69,.94],[[0,.70],[500,.80],[1000,.70],[1500,.80],[2000,.70]])
for i in range(12):
    a=i*math.tau/12;b=(i+1)*math.tau/12;mid=(a+b)/2
    surface(floor,'cold-boundary-facet-'+str(i),[point(222,a),point(236,a),point(236,b),point(222,b)],[[0,1,2],[0,2,3]])
    surface(runes,'cold-rim-chevron-'+str(i),[point(207,mid-.028,8),point(233,mid,8),point(207,mid+.028,8)],[[0,1,2]])
for i in range(6):
    a=i*math.tau/6
    surface(floor,'cold-star-arm-'+str(i),transform([[22,-11,5],[205,-20,5],[221,0,5],[205,20,5],[22,11,5]],a),[[0,1,2],[0,2,3],[0,3,4]])
    for side in [-1,1]:
        surface(runes,'cold-snowflake-fork-'+str(i)+'-'+str(side),transform([[92,side*3,8],[148,side*38,8],[157,side*35,8],[100,side*1,8]],a),[[0,1,2],[0,2,3]] if side==1 else [[2,1,0],[3,2,0]])
    center=point(137,a,0)
    # Facets float over the field; no cage closes and no shard explodes.
    vs=transform([[-18,0,20],[0,-12,44],[18,0,20],[0,12,44],[0,0,76],[0,0,10]],a,center)
    fs=[[4,0,1],[4,1,2],[4,2,3],[4,3,0],[5,1,0],[5,2,1],[5,3,2],[5,0,3]]
    solid(facets,'cold-floating-facet-'+str(i),vs,fs,1)
m['geosets']=[floor,runes,facets]
m['phaseContract']=dict(neutral=True,visibleFromMs=0,automaticFreeze=False,automaticFracture=False,loopMs=2000,deathVisibleMs=0,hold='real cast lifecycle')
(OUT/(m['name']+'.json')).write_text(json.dumps(m,separators=(',',':')))

m=model('TDPetVfxStarfallDomain',33,240,loop_end,dict(min=[-241,-241,0],max=[241,241,90]));m['loop']=True
bone(m,'StarfallFieldFloor',scale=[[0,[1,1,1]],[500,[.99,.99,1]],[1000,[1,1,1]],[1500,[.99,.99,1]],[2000,[1,1,1]]])
bone(m,'HeatFieldBreath',scale=[[0,[1,1,.82]],[500,[1,1,1]],[1000,[1,1,.82]],[1500,[1,1,1]],[2000,[1,1,.82]]])
floor=ga('warm-field-star',0,[.63,.12,.012],[[0,.63],[500,.72],[1000,.63],[1500,.72],[2000,.63]])
runes=ga('warm-field-lines',1,[1,.58,.055],[[0,.78],[500,.90],[1000,.78],[1500,.90],[2000,.78]])
heat=ga('low-warm-energy-teeth',1,[1,.27,.022],[[0,.65],[500,.78],[1000,.65],[1500,.78],[2000,.65]])
for i in range(12):
    a=i*math.tau/12;b=(i+1)*math.tau/12;mid=(a+b)/2
    surface(floor,'warm-boundary-tooth-'+str(i),[point(181,a,5),point(236,mid,5),point(181,b,5)],[[0,1,2]])
    if i%2==0:
        surface(runes,'warm-inward-guide-'+str(i),[point(179,mid-.043,8),point(69,mid,8),point(179,mid+.043,8)],[[2,1,0]])
for i in range(6):
    a=i*math.tau/6
    surface(floor,'warm-broken-star-arm-'+str(i),transform([[18,-10,6],[159,-12,6],[203,0,6],[154,12,6],[18,10,6]],a),[[0,1,2],[0,2,3],[0,3,4]])
    center=point(150,a+.25,0)
    outline=transform([[-11,-13,7],[13,12,7],[9,0,61]],a,center)
    prism(heat,'warm-energy-tooth-'+str(i),outline,[5*math.cos(a),5*math.sin(a),0],1)
    # Hex-star paths, deliberately sparse with the battlefield visible between.
    surface(runes,'warm-central-star-'+str(i),transform([[19,-3,10],[76,0,10],[19,3,10]],a),[[0,1,2]])
m['geosets']=[floor,runes,heat]
m['phaseContract']=dict(neutral=True,visibleFromMs=0,automaticMeteor=False,automaticImpact=False,loopMs=2000,deathVisibleMs=0,hold='real cast lifecycle')
(OUT/(m['name']+'.json')).write_text(json.dumps(m,separators=(',',':')))
for n in ['TDPetVfxFrostDomain','TDPetVfxStarfallDomain']:
    m=json.loads((OUT/(n+'.json')).read_text());count=sum(len(p['faces']) for g in m['geosets'] for p in g['parts']);assert count<=250,(n,count);print(n,count,'triangles',len(m['bones']),'bones; neutral loop')

m=model('TDPetVfxSwordDomain',22,260,loop_end,dict(min=[-261,-261,0],max=[261,261,128]));m['loop']=True
bone(m,'SwordFormationFloor',scale=[[0,[1,1,1]],[1000,[.99,.99,1]],[2000,[1,1,1]]])
bone(m,'PoisedSwordFormation',translation=[[0,[0,0,0]],[500,[0,0,7]],[1000,[0,0,0]],[1500,[0,0,7]],[2000,[0,0,0]]])
floor=ga('sword-domain-grid',1,[1,.78,.26],[[0,.75],[500,.85],[1000,.75],[1500,.85],[2000,.75]])
blades=ga('poised-sword-blades',0,[.95,.83,.51],[[0,.88],[2000,.88]])
guards=ga('sword-crossguards',1,[1,.66,.095],[[0,.80],[1000,.95],[2000,.80]])
for i in range(8):
    a=i*math.tau/8;b=(i+1)*math.tau/8
    surface(floor,'sword-octagonal-rim-'+str(i),[point(247,a,6),point(256,a,6),point(256,b,6),point(247,b,6)],[[0,1,2],[0,2,3]])
for i in range(4):
    a=i*math.tau/4+math.pi/4
    surface(floor,'sword-compass-strip-'+str(i),transform([[31,-4,7],[243,-4,7],[243,4,7],[31,4,7]],a),[[0,1,2],[0,2,3]])
for i in range(6):
    a=i*math.tau/6;center=point(185,a,0)
    # Recognizable long blade profile and crossguard, poised rather than falling.
    outline=transform([[-3,-9,28],[-3,9,28],[-3,9,87],[-3,0,111],[-3,-9,87]],a,center)
    prism(blades,'poised-sword-'+str(i),outline,[6*math.cos(a),6*math.sin(a),0],1)
    outline=transform([[-4,-25,25],[-4,25,25],[-4,25,32],[-4,-25,32]],a,center)
    prism(guards,'gold-crossguard-'+str(i),outline,[8*math.cos(a),8*math.sin(a),0],1)
m['geosets']=[floor,blades,guards]
m['phaseContract']=dict(neutral=True,visibleFromMs=0,automaticSwordImpact=False,loopMs=2000,deathVisibleMs=0,hold='real cast lifecycle')
(OUT/(m['name']+'.json')).write_text(json.dumps(m,separators=(',',':')))

m=model('TDPetVfxVortexDomain',30,280,loop_end,dict(min=[-281,-281,0],max=[281,281,130]));m['loop']=True
bone(m,'VortexBoundary')
bone(m,'TurningWaterSpiral',rotation=[[0,quat_z(0)],[500,quat_z(math.pi/2)],[1000,quat_z(math.pi)],[1500,quat_z(3*math.pi/2)],[2000,quat_z(math.tau)]])
boundary=ga('vortex-boundary-ticks',1,[.18,.88,1],[[0,.76],[1000,.90],[2000,.76]])
spiral=ga('broad-water-spirals',0,[.035,.42,.70],[[0,.64],[1000,.74],[2000,.64]])
edge=ga('water-spiral-crests',1,[.36,.88,1],[[0,.72],[1000,.86],[2000,.72]])
for i in range(12):
    a=i*math.tau/12;mid=a+math.pi/12
    surface(boundary,'water-outer-tick-'+str(i),[point(255,a-.015,7),point(276,a-.015,7),point(276,a+.015,7),point(255,a+.015,7)],[[0,1,2],[0,2,3]])
for arm in range(3):
    base=arm*math.tau/3
    for i in range(10):
        t0=i/10;t1=(i+1)/10
        def pp(t,rdelta=0,zdelta=0):
            r=51+190*t+rdelta;a=base+2.45*t;return point(r,a,13+75*(1-t)+zdelta)
        surface(spiral,'water-ribbon-'+str(arm)+'-'+str(i),[pp(t0,-15),pp(t0,15),pp(t1,15),pp(t1,-15)],[[0,1,2],[0,2,3]],1)
        surface(edge,'water-crest-'+str(arm)+'-'+str(i),[pp(t0,13,2),pp(t0,17,2),pp(t1,17,2),pp(t1,13,2)],[[0,1,2],[0,2,3]],1)
    # A low diamond fin at each crest gives the water a solid readable silhouette.
    a=base+1.7;center=point(183,a,0)
    vs=transform([[-16,0,22],[0,-9,41],[16,0,22],[0,9,41],[0,0,74],[0,0,12]],a,center)
    fs=[[4,0,1],[4,1,2],[4,2,3],[4,3,0],[5,1,0],[5,2,1],[5,3,2],[5,0,3]]
    solid(edge,'water-crest-fin-'+str(arm),vs,fs,1)
m['geosets']=[boundary,spiral,edge]
m['phaseContract']=dict(neutral=True,visibleFromMs=0,automaticHit=False,loopMs=2000,deathVisibleMs=0,hold='real cast lifecycle')
(OUT/(m['name']+'.json')).write_text(json.dumps(m,separators=(',',':')))

m=model('TDPetVfxEarthSealDomain',37,260,loop_end,dict(min=[-261,-261,0],max=[261,261,98]));m['loop']=True
bone(m,'EarthSealFloor')
bone(m,'EarthSealRunestones',translation=[[0,[0,0,0]],[1000,[0,0,4]],[2000,[0,0,0]]])
floor=ga('earth-seal-runes',1,[1,.54,.12],[[0,.76],[1000,.92],[2000,.76]])
stones=ga('earth-seal-stones',0,[.51,.30,.10],[[0,.88],[2000,.88]])
facets=ga('earth-seal-inscriptions',1,[1,.70,.27],[[0,.73],[1000,.88],[2000,.73]])
# An inscribed square and four substantial rune stones distinguish this from water rings.
for i in range(4):
    a=i*math.tau/4;b=(i+1)*math.tau/4
    surface(floor,'earth-diamond-edge-'+str(i),[point(245,a,6),point(256,a,6),point(256,b,6),point(245,b,6)],[[0,1,2],[0,2,3]])
    for side in [-1,1]:
        surface(floor,'earth-rune-bracket-'+str(i)+'-'+str(side),transform([[34,side*35,8],[158,side*35,8],[158,side*45,8],[34,side*45,8]],a),[[0,1,2],[0,2,3]] if side==1 else [[2,1,0],[3,2,0]])
    surface(floor,'earth-center-stroke-'+str(i),transform([[15,-5,9],[151,-5,9],[151,5,9],[15,5,9]],a),[[0,1,2],[0,2,3]])
    center=point(174,a,0)
    outline=transform([[-13,-21,8],[-13,21,8],[-13,21,64],[-13,-21,64]],a,center)
    prism(stones,'earth-seal-standing-stone-'+str(i),outline,[26*math.cos(a),26*math.sin(a),0],1)
    # Thin actual solid etched glyph on the inward face, not a glow billboard.
    outline=transform([[-15,-12,19],[-15,12,19],[-15,0,54]],a,center)
    prism(facets,'earth-seal-glyph-'+str(i),outline,[-2*math.cos(a),-2*math.sin(a),0],1)
m['geosets']=[floor,stones,facets]
m['phaseContract']=dict(neutral=True,visibleFromMs=0,automaticQuake=False,loopMs=2000,deathVisibleMs=0,hold='real cast lifecycle')
(OUT/(m['name']+'.json')).write_text(json.dumps(m,separators=(',',':')))
for n in ['TDPetVfxSwordDomain','TDPetVfxVortexDomain','TDPetVfxEarthSealDomain']:
    m=json.loads((OUT/(n+'.json')).read_text());count=sum(len(p['faces']) for g in m['geosets'] for p in g['parts']);assert count<=250,(n,count);print(n,count,'triangles',len(m['bones']),'bones; neutral loop')

m=model('TDPetVfxFlowerBloomLoop',25,100,loop_end,dict(min=[-101,-101,0],max=[101,101,78]));m['loop']=True
bone(m,'SingleRealFlowerField')
bone(m,'LivingFlowerPetals',scale=[[0,[1,1,.90]],[500,[1,1,1]],[1000,[1,1,.90]],[1500,[1,1,1]],[2000,[1,1,.90]]])
leaves=ga('flower-field-leaves',0,[.035,.56,.14],[[0,.82],[1000,.88],[2000,.82]])
petals=ga('open-flower-petals',0,[.13,.76,.24],[[0,.80],[1000,.88],[2000,.80]])
light=ga('flower-veins-and-heart',1,[.67,1,.29],[[0,.73],[1000,.88],[2000,.73]])
for i in range(6):
    a=i*math.tau/6
    # All six visible petals belong to this one actual radius-100 flower point.
    outline=transform([[13,0,14],[56,-25,26],[94,0,44],[56,25,26]],a)
    prism(petals,'single-flower-petal-'+str(i),outline,[0,0,-4],1)
    surface(light,'single-flower-vein-'+str(i),transform([[20,-1,19],[89,0,45],[20,2,19]],a),[[0,1,2]],1)
    surface(leaves,'single-flower-ground-leaf-'+str(i),transform([[43,0,5],[75,-17,5],[96,0,5],[75,17,5]],a+math.pi/6),[[0,1,2],[0,2,3]])
    surface(light,'single-flower-tip-'+str(i),transform([[88,-4,7],[96,0,7],[88,4,7]],a+math.pi/6),[[0,1,2]])
vs=[[0,0,63],[0,0,13],[19,0,35],[0,19,35],[-19,0,35],[0,-19,35]]
fs=[[0,2,3],[0,3,4],[0,4,5],[0,5,2],[1,3,2],[1,4,3],[1,5,4],[1,2,5]]
solid(light,'single-flower-pollen-heart',vs,fs,1)
m['geosets']=[leaves,petals,light]
m['phaseContract']=dict(neutral=True,visibleFromMs=0,queryPoint='first actual road flower point only',automaticBloomHit=False,loopMs=2000,deathVisibleMs=0,hold='real cast lifecycle')
(OUT/(m['name']+'.json')).write_text(json.dumps(m,separators=(',',':')))

m=model('TDPetVfxLotusBurstLoop',32,230,loop_end,dict(min=[-231,-231,0],max=[231,231,125]));m['loop']=True
bone(m,'LotusCastField')
bone(m,'OpenScarletLotus',scale=[[0,[1,1,.88]],[500,[1,1,1]],[1000,[1,1,.88]],[1500,[1,1,1]],[2000,[1,1,.88]]])
petals=ga('broad-scarlet-lotus-petals',0,[.98,.035,.11],[[0,.78],[1000,.88],[2000,.78]])
core=ga('lotus-hot-inner-petals',1,[1,.47,.22],[[0,.78],[1000,.93],[2000,.78]])
field=ga('lotus-field-sparks',1,[1,.37,.09],[[0,.72],[1000,.85],[2000,.72]])
for i in range(6):
    a=i*math.tau/6
    outline=transform([[16,0,20],[90,-33,16],[205,-24,52],[225,0,87],[205,24,52],[90,33,16]],a)
    prism(petals,'scarlet-lotus-outer-petal-'+str(i),outline,[0,0,-5],1)
    outline=transform([[15,-12,22],[15,12,22],[99,0,106]],a+math.pi/6)
    prism(core,'scarlet-lotus-inner-petal-'+str(i),outline,[0,0,-5],1)
    surface(field,'lotus-range-cinder-'+str(i),transform([[211,-8,7],[226,0,7],[211,8,7]],a),[[0,1,2]])
    surface(field,'lotus-ground-ray-'+str(i),transform([[38,-3,8],[195,-3,8],[195,3,8],[38,3,8]],a+math.pi/6),[[0,1,2],[0,2,3]])
m['geosets']=[petals,core,field]
m['phaseContract']=dict(neutral=True,visibleFromMs=0,automaticRepeatedDamage=False,loopMs=2000,deathVisibleMs=0,hold='real cast lifecycle plus authorized 250ms visual dwell')
(OUT/(m['name']+'.json')).write_text(json.dumps(m,separators=(',',':')))
for n in ['TDPetVfxFlowerBloomLoop','TDPetVfxLotusBurstLoop']:
    m=json.loads((OUT/(n+'.json')).read_text());count=sum(len(p['faces']) for g in m['geosets'] for p in g['parts']);assert count<=250,(n,count);print(n,count,'triangles',len(m['bones']),'bones; loop')
