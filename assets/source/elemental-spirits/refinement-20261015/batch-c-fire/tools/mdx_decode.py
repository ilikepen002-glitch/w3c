"""Independent MDX800 parser and sampled animation evaluator for PhoenixV2.
No source model writes. All key values AND Hermite/Bezier tangents are retained.
Coordinates are the original Warcraft model coordinates (Z up, +X forward).
Interpolation behavior cross-checked against flowtsohg/mdx-m3-viewer sd.ts.
"""
from pathlib import Path
import struct,json,hashlib,bisect,math
import numpy as np
DEFAULT_SOURCE=Path('/workspace/shared/phoenix-reclassic-restore-20261015/source/PhoenixV2.mdx')
ROOT=Path('/workspace/shared/phoenix-reclassic-art-20261015')
def unpack(fmt,b,p):return struct.unpack_from('<'+fmt,b,p)
def u(b,p):return unpack('I',b,p)[0]
def txt(b):return b.split(b'\0')[0].decode('utf-8','replace')
def extent(b,p):
 x=unpack('7f',b,p);return {'radius':x[0],'min':list(x[1:4]),'max':list(x[4:])}
WIDTH={'KGTR':3,'KGRT':4,'KGSC':3,'KGAO':1,'KGAC':3,'KMTA':1,'KMTF':1,'KTAT':3,'KTAR':4,'KTAS':3}
def tracks(b,p,end):
 out=[]
 while p<end:
  tag=b[p:p+4].decode('ascii');n,interp,gl=unpack('IIi',b,p+4);p+=16;w=WIDTH[tag];keys=[];fmt=str(w)+('I' if tag=='KMTF' else 'f')
  for _ in range(n):
   k={'frame':u(b,p),'value':list(unpack(fmt,b,p+4))};p+=4+4*w
   if interp>1:k['inTan']=list(unpack(fmt,b,p));k['outTan']=list(unpack(fmt,b,p+4*w));p+=8*w
   keys.append(k)
  out.append({'tag':tag,'interpolation':interp,'globalSequenceId':gl,'keys':keys})
 assert p==end,(p,end)
 return out

def decode(path=DEFAULT_SOURCE):
 b=Path(path).read_bytes();assert b[:4]==b'MDLX';chunks={};i=4;inventory=[]
 while i<len(b):
  tag=b[i:i+4].decode('ascii');n=u(b,i+4);chunks[tag]=b[i+8:i+8+n];inventory.append({'tag':tag,'offset':i,'size':n});i+=n+8
 assert i==len(b)
 d={'source':str(path),'sha256':hashlib.sha256(b).hexdigest(),'version':u(chunks['VERS'],0),'chunks':inventory,'name':txt(chunks['MODL'][:80])}
 assert d['version']==800
 d['globalSequences']=list(unpack(str(len(chunks.get('GLBS',b''))//4)+'I',chunks.get('GLBS',b''),0))
 d['sequences']=[];s=chunks['SEQS']
 for p in range(0,len(s),132):
  a,e,move,flags,rarity,sync=unpack('IIfIfI',s,p+80);d['sequences'].append({'name':txt(s[p:p+80]),'interval':[a,e],'moveSpeed':move,'flags':flags,'rarity':rarity,'syncPoint':sync,'extent':extent(s,p+104)})
 d['textures']=[];s=chunks['TEXS']
 for p in range(0,len(s),268):d['textures'].append({'replaceableId':u(s,p),'path':txt(s[p+4:p+264]),'flags':u(s,p+264)})
 d['materials']=[];s=chunks['MTLS'];p=0
 while p<len(s):
  end=p+u(s,p);m={'priorityPlane':unpack('i',s,p+4)[0],'flags':u(s,p+8),'layers':[]};j=p+12;assert s[j:j+4]==b'LAYS';n=u(s,j+4);j+=8
  for _ in range(n):
   le=j+u(s,j);fm,fl,tid,ta,cid,alpha=unpack('IIIiIf',s,j+4);m['layers'].append({'filterMode':fm,'flags':fl,'textureId':tid,'textureAnimationId':ta,'coordId':cid,'alpha':alpha,'tracks':tracks(s,j+28,le)});j=le
  assert j==end;d['materials'].append(m);p=end
 d['geosets']=[];s=chunks['GEOS'];p=0
 while p<len(s):
  end=p+u(s,p);j=p+4;a={}
  for tag,sz,fmt in [('VRTX',12,'3f'),('NRMS',12,'3f'),('PTYP',4,'I'),('PCNT',4,'I'),('PVTX',2,'H'),('GNDX',1,'B'),('MTGC',4,'I'),('MATS',4,'I')]:
   assert s[j:j+4]==tag.encode();n=u(s,j+4);a[tag]=[list(v) for v in struct.iter_unpack('<'+fmt,s[j+8:j+8+n*sz])];j+=8+n*sz
  mat,sg,sf=unpack('III',s,j);j+=12;ex=extent(s,j);j+=28;n=u(s,j);j+=4;seqex=[extent(s,j+k*28)for k in range(n)];j+=28*n
  assert s[j:j+4]==b'UVAS';nu=u(s,j+4);j+=8;uv=[]
  for _ in range(nu):
   assert s[j:j+4]==b'UVBS';n=u(s,j+4);uv.append([list(v)for v in struct.iter_unpack('<2f',s[j+8:j+8+n*8])]);j+=8+n*8
  assert j==end
  groups=[];k=0
  for n in a['MTGC']:
   groups.append([v[0] for v in a['MATS'][k:k+n[0]]]);k+=n[0]
  assert k==len(a['MATS'])
  d['geosets'].append({'index':len(d['geosets']),'materialId':mat,'selectionGroup':sg,'selectionFlags':sf,'vertices':a['VRTX'],'normals':a['NRMS'],'faceTypeGroups':a['PTYP'],'faceGroups':a['PCNT'],'faces':[sum(a['PVTX'][k:k+3],[])for k in range(0,len(a['PVTX']),3)],'vertexGroups':[v[0]for v in a['GNDX']],'matrixGroups':groups,'extent':ex,'sequenceExtents':seqex,'uvSets':uv});p=end
 d['geosetAnimations']=[];s=chunks.get('GEOA',b'');p=0
 while p<len(s):
  end=p+u(s,p);alpha,flags,b0,g0,r0,gid=unpack('fI3fI',s,p+4);d['geosetAnimations'].append({'geosetId':gid,'alpha':alpha,'flags':flags,'colorBGR':[b0,g0,r0],'tracks':tracks(s,p+28,end)});p=end
 d['pivots']=[list(x)for x in struct.iter_unpack('<3f',chunks['PIVT'])];d['nodes']=[]
 for tag,extra in [('BONE',8),('HELP',0)]:
  s=chunks.get(tag,b'');p=0
  while p<len(s):
   end=p+u(s,p);oid,parent,flags=unpack('iiI',s,p+84);node={'kind':tag,'name':txt(s[p+4:p+84]),'id':oid,'parentId':parent,'flags':flags,'pivot':d['pivots'][oid],'tracks':tracks(s,p+96,end)}
   if extra:node['geosetId'],node['geosetAnimationId']=unpack('ii',s,end)
   d['nodes'].append(node);p=end+extra
 d['nodes'].sort(key=lambda n:n['id'])
 d['unrenderedChunks']=[t for t in ['ATCH','PRE2','RIBB','EVTS','CAMS','CLID'] if t in chunks]
 return d

def normalize(q):
 q=np.asarray(q,float);n=np.linalg.norm(q);return q/n if n>1e-12 else np.array([0.,0.,0.,1.])
def slerp(a,b,t):
 a=normalize(a);b=normalize(b);c=float(np.dot(a,b))
 if c<0:b=-b;c=-c
 if c>.9995:return normalize(a+(b-a)*t)
 th=math.acos(np.clip(c,-1,1));return (math.sin((1-t)*th)*a+math.sin(t*th)*b)/math.sin(th)
def qmatrix(q):
 x,y,z,w=normalize(q)
 return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
DEFAULTS={'KGTR':[0,0,0],'KGRT':[0,0,0,1],'KGSC':[1,1,1],'KGAO':[1],'KGAC':[0,0,0],'KMTA':[1],'KMTF':[0]}
class Evaluator:
 def __init__(self,d):
  self.d=d;self.nodes={n['id']:n for n in d['nodes']};self.ga={g['geosetId']:g for g in d['geosetAnimations']};self.trackCache={};self.vertexCache={}
  for g in d['geosets']:
   self.vertexCache[g['index']]=(np.c_[np.array(g['vertices']),np.ones(len(g['vertices']))],np.array(g['normals']))
 def sequence(self,name):
  return next(s for s in self.d['sequences'] if s['name'].lower()==name.lower())
 def value(self,tr,seq,frame,elapsed,default=None):
  if tr is None:return np.asarray(default,float)
  gl=tr['globalSequenceId'];lo,hi=([0,self.d['globalSequences'][gl]] if gl>=0 else seq['interval']);time=(elapsed%hi if gl>=0 and hi else frame)
  cachekey=(id(tr),lo,hi)
  if cachekey not in self.trackCache:
   ks=[k for k in tr['keys'] if lo<=k['frame']<=hi]
   if gl>=0 and not ks and tr['keys'] and tr['keys'][0]['frame']>hi:ks=tr['keys'][:1]
   self.trackCache[cachekey]=(ks,[k['frame']for k in ks])
  ks,fs=self.trackCache[cachekey]
  if not ks:return np.asarray(DEFAULTS.get(tr['tag'],default),float)
  if len(ks)==1 or time<lo:return np.array(ks[0]['value'],float)
  if time<fs[0] or time>=fs[-1]:a,b=len(ks)-1,0
  else:b=bisect.bisect_right(fs,time);a=b-1
  ta,tb=fs[a],fs[b];span=tb-ta
  if span<0:
   span+=hi-lo
   if time<ta:ta=tb
  t=0 if span==0 else (time-ta)/span
  p0=np.array(ks[a]['value'],float);p1=np.array(ks[b]['value'],float);mode=tr['interpolation']
  if mode==0:return p0
  if tr['tag'] in ['KGRT','KTAR']:
   if mode==1:return slerp(p0,p1,t)
   return slerp(slerp(p0,p1,t),slerp(ks[a]['outTan'],ks[b]['inTan'],t),2*t*(1-t))
  if mode==1:return p0*(1-t)+p1*t
  o=np.array(ks[a]['outTan']);i=np.array(ks[b]['inTan'])
  if mode==2:return (2*t**3-3*t*t+1)*p0+(t**3-2*t*t+t)*o+(-2*t**3+3*t*t)*p1+(t**3-t*t)*i
  if mode==3:return (1-t)**3*p0+3*(1-t)**2*t*o+3*(1-t)*t*t*i+t**3*p1
  raise ValueError(mode)
 def matrices(self,seq,frame,elapsed):
  mats={};visiting=set()
  def one(i):
   if i in mats:return mats[i]
   assert i not in visiting,'Hierarchy cycle';visiting.add(i);n=self.nodes[i];tr={t['tag']:t for t in n['tracks']}
   t=self.value(tr.get('KGTR'),seq,frame,elapsed,[0,0,0]);q=self.value(tr.get('KGRT'),seq,frame,elapsed,[0,0,0,1]);s=self.value(tr.get('KGSC'),seq,frame,elapsed,[1,1,1]);p=np.array(n['pivot']);m=np.eye(4);m[:3,:3]=qmatrix(q)@np.diag(s);m[:3,3]=t+p-m[:3,:3]@p
   # Only standard inheritance is present in Phoenix's mesh skin nodes.
   if n['flags']&7:raise NotImplementedError('Non-inheritance flags require separate evaluation')
   if n['parentId']>=0:m=one(n['parentId'])@m
   mats[i]=m;visiting.remove(i);return m
  for i in self.nodes:one(i)
  return mats
 def alpha_color(self,gid,seq,frame,elapsed):
  a=self.ga.get(gid)
  if not a:return 1.,np.ones(3)
  ts={t['tag']:t for t in a['tracks']};alpha=float(self.value(ts.get('KGAO'),seq,frame,elapsed,[a['alpha']])[0]);color=np.array(a['colorBGR'][::-1])
  if a['flags']&2:color=self.value(ts.get('KGAC'),seq,frame,elapsed,a['colorBGR'])[::-1]
  else:color=np.ones(3)
  return alpha,color
 def sample(self,name,frame,elapsed=0,geosets=None):
  seq=self.sequence(name);mats=self.matrices(seq,frame,elapsed);out=[]
  for g in self.d['geosets']:
   if geosets is not None and g['index'] not in geosets:continue
   vv,nn=self.vertexCache[g['index']];mg=np.array([np.mean([mats[i]for i in group],axis=0)for group in g['matrixGroups']]);vm=mg[np.array(g['vertexGroups'])];v=np.einsum('nij,nj->ni',vm,vv)[:,:3];norm=np.einsum('nij,nj->ni',vm[:,:3,:3],nn);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-15);a,c=self.alpha_color(g['index'],seq,frame,elapsed)
   out.append({'index':g['index'],'vertices':v,'normals':norm,'alpha':a,'color':c})
  return out

def audit(d):
 ev=Evaluator(d);r={'sha256':d['sha256'],'version':d['version'],'triangles':sum(len(g['faces'])for g in d['geosets']),'renderedGeosets':[4,5,6,7,8],'renderedTriangles':sum(len(d['geosets'][i]['faces'])for i in range(4,9)),'boneCount':sum(n['kind']=='BONE'for n in d['nodes']),'helperCount':sum(n['kind']=='HELP'for n in d['nodes']),'pivotCount':len(d['pivots']),'fullTracks':sum(len(n['tracks'])for n in d['nodes']),'fullKeyframes':sum(len(t['keys'])for n in d['nodes']for t in n['tracks']),'tangentKeys':sum(len(t['keys'])for n in d['nodes']for t in n['tracks']if t['interpolation']>1),'sequences':[],'limitations':['Original textures are missing; generated textures are a new artistic reinterpretation.','Geosets 0–3 retained in MDX/data but excluded from current render; native glow/teleport/egg textures are not recreated.','Particle emitters, ribbons, attachment emitters, event-driven effects and native team-color layering are not rendered.','Billboarded glow nodes belong to excluded geoset 0; billboard orientation not evaluated.','Blender preview is not a Warcraft III runtime screenshot.']}
 for seq in d['sequences']:
  st,en=seq['interval'];vis={};samples=[ev.sample(seq['name'],float(t),float(t-st))for t in np.linspace(st,en,33)]
  for gi in range(len(d['geosets'])):vals=[s[gi]['alpha']for s in samples];vis[str(gi)]={'min':min(vals),'max':max(vals),'start':vals[0],'end':vals[-1]}
  mesh=[np.concatenate([s[gi]['vertices']for gi in range(4,9)])for s in samples];bbox=np.concatenate(mesh);r['sequences'].append({'name':seq['name'],'interval':seq['interval'],'durationMs':en-st,'looping':not(seq['flags']&1),'geosetAlpha':vis,'meshBounds':[bbox.min(0).tolist(),bbox.max(0).tolist()],'maxVertexMotion':float(max(np.max(np.linalg.norm(v-mesh[0],axis=1))for v in mesh))})
 return r
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--source',default=str(DEFAULT_SOURCE));args=p.parse_args();d=decode(args.source);r=audit(d);(ROOT/'technical/full-mdx-decoded.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));(ROOT/'technical/animation-audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False,indent=2))
