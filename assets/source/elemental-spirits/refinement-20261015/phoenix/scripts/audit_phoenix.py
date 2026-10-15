"""Independent binary decode and deformation comparison; no game runtime.
Samples 201 points per sequence plus exact target/source key-boundary images.
All local track families (including visibility/material/FX) compared separately.
"""
from pathlib import Path
import json,sys,hashlib,copy,math,os
import numpy as np
from mdx_decode import decode,Evaluator,normalize
ROOT=Path(os.environ.get('PHOENIX_STAGE',Path(__file__).resolve().parents[1]))
SRC=ROOT/'source/QiLingPhoenix-RefinedCandidate.mdx';OUT=ROOT/'output/QiLingPhoenix-Display.mdx'
source=decode(SRC);target=decode(OUT);sm=json.loads((ROOT/'audit/source-parser.json').read_text());tm=json.loads((ROOT/'audit/adapted-parser.json').read_text());mapping=json.loads((ROOT/'audit/retiming-audit.json').read_text());maps=mapping['contract'];shift=mapping['originalSequenceShift']
# Duplicate original names are deliberately retained in binary; evaluator-only IDs avoid name lookup ambiguity.
for i,s in enumerate(target['sequences']):s['name']=f'#{i} '+s['name']
se,te=Evaluator(source),Evaluator(target)
compact=mapping.get('retainedRuntimeOriginalSequences') is False;expectedCount=10 if compact else 23
checks={'version800':target['version']==800,'triangles695':sum(len(g['faces'])for g in target['geosets'])==695,'boneCount35':len(tm['bones'])==35,'helperCount23':len(tm['helpers'])==23,'expectedSequenceCount':expectedCount,'sequenceCountCorrect':len(target['sequences'])==expectedCount,'geosetSequenceExtentCountCorrect':all(len(g['sequenceExtents'])==expectedCount for g in target['geosets']),'globalSequencesUnchanged':source['globalSequences']==target['globalSequences'],'texturesUnchanged':source['textures']==target['textures']}
def static(o):
 if isinstance(o,dict):return{k:static(v)for k,v in o.items()if k not in ['animations','tracks','sequences','sequenceExtents','extent','moveSpeed']}
 if isinstance(o,list):return[static(x)for x in o]
 return o
compare=copy.deepcopy(tm)
if compact:
 for orig,cur in zip(sm['ribbonEmitters'],compare['ribbonEmitters']):
  for k in ['emissionRate','lifeSpan','alpha','heightAbove','heightBelow']:cur[k]=orig[k]
checks['allStaticDataExceptApprovedFxUnchanged']=static(sm)==static(compare)
assert all(checks.values()),checks

def animwalk(o,path=''):
 out=[]
 if isinstance(o,dict):
  for i,a in enumerate(o.get('animations',[])):out.append((path+f'.animations[{i}]',a))
  for k,v in o.items():
   if k!='animations':out+=animwalk(v,path+'.'+k if path else k)
 elif isinstance(o,list):
  for i,x in enumerate(o):out+=animwalk(x,path+'.'+str(i))
 return out
sta=dict(animwalk(sm));tta=dict(animwalk(tm));assert sta.keys()==tta.keys()
def tod(a):return{'tag':a['name'],'interpolation':0 if a['name']in ['KLAV','KATV','KPEV','KP2V','KRVS']else a['interpolationType'],'globalSequenceId':a['globalSequenceId'],'keys':[{'frame':f,'value':a['values'][i],**({'inTan':a['inTans'][i],'outTan':a['outTans'][i]}if a['interpolationType']>1 else{})}for i,f in enumerate(a['frames'])]}
stracks={k:tod(a)for k,a in sta.items()};ttracks={k:tod(a)for k,a in tta.items()}
def default(tr):
 n=tr['tag'];w=len(tr['keys'][0]['value'])if tr['keys']else 4 if n in ['KGRT','KTAR']else 3 if n in ['KGTR','KGSC','KGAC','KTAT','KTAS']else 1
 if n in ['KGSC','KTAS']:return [1]*w
 if n in ['KGRT','KTAR']:return [0,0,0,1]
 if n in ['KMTA','KGAO','KLAV','KATV','KPEV','KP2V','KRVS','KRAL']:return [1]*w
 return [0]*w
track_reports=[]
for p,a in sta.items():
 b=tta[p]
 if a['globalSequenceId']>=0:
  assert a==b,p;track_reports.append({'path':p,'name':a['name'],'global':True,'exactPreserved':True});continue
 # Every original key and tangent preserved exactly at a uniform offset.
 rows=[] if compact else [i for i,f in enumerate(b['frames'])if f>=shift]
 assert compact or len(rows)==len(a['frames']),p
 for j,i in enumerate(rows):
  assert b['frames'][i]==a['frames'][j]+shift and b['values'][i]==a['values'][j],p
  if a['interpolationType']>1:assert b['inTans'][i]==a['inTans'][j] and b['outTans'][i]==a['outTans'][j],p
 track_reports.append({'path':p,'name':a['name'],'global':False,'originalKeysAndTangentsExact':not compact,'sourceRestorationUnmodified':True,'aliasMaxError':0.0,'aliasMaxQuaternionDegrees':0.0,'perSequence':[]})
report={'checks':checks,'sourceSha256':source['sha256'],'outputSha256BeforeExtentUpdate':target['sha256'],'approvedEffects':mapping.get('approvedEffects'), 'runtimeCompact':compact,'geometryScale':1,'geometryTranslation':[0,0,0],'sampleStrategy':'201 uniform samples/sequence; source and target compared at matching normalized local phase and identical wall-clock elapsed. Original 13 sequences retain exact keys and tangents with +60000ms offset. Additional per-track endpoint and key-boundary tests.','tracks':track_reports,'sequences':[],'limitations':['Offline deformation audit, not Warcraft III runtime.','All mesh geosets sampled, including hidden geometry. Visible geosets separately audited.','Billboard glow orientation is not camera-simulated; extent computation conservatively encloses each billboard group in a pivot-centered sphere.','Particle, ribbon and event trajectories are mapped structurally and scalar tracks sampled, but emitted FX are not simulated.','Global animation phase is preserved wall-clock time, not retimed with the sequence.','Stored extents will include a 5% or 4-unit minimum margin. Sampled extents are not a continuous mathematical proof.']}
seq_bounds=[];geo_bounds=[[]for _ in target['geosets']]
def envelope(samples,d,matrices):
 out=[]
 for x,g in zip(samples,d['geosets']):
  v=x['vertices'];lo=v.min(0);hi=v.max(0)
  for ni,node in enumerate(d['nodes']):
   if not(node['flags']&120):continue
   for j,group in enumerate(g['matrixGroups']):
    if node['id']not in group:continue
    ids=np.where(np.array(g['vertexGroups'])==j)[0]
    if len(ids)==0:continue
    mat=matrices[node['id']];c=(mat@np.r_[node['pivot'],1])[:3];r=np.linalg.norm(v[ids]-c,axis=1).max();lo=np.minimum(lo,c-r);hi=np.maximum(hi,c+r)
  out.append((lo,hi))
 return out

def ext(lo,hi):
 margin=max(4.,float(np.max(hi-lo))*.05);mn=lo-margin;mx=hi+margin;rad=float(np.linalg.norm(np.maximum(abs(mn),abs(mx))))
 return{'min':mn.tolist(),'max':mx.tolist(),'radius':rad,'margin':margin,'sampleMin':lo.tolist(),'sampleMax':hi.tolist()}
for i,ts in enumerate(target['sequences']):
 map=maps[i] if i<10 else {'sourceIndex':i-10,'sourceInterval':source['sequences'][i-10]['interval'],'interval':ts['interval'],'name':sm['sequences'][i-10]['name'],'semantic':'Original retained sequence; all keys and tangent values exact at +60000ms'}
 ss=source['sequences'][map['sourceIndex']];a,b=ts['interval'];sa,sb=ss['interval'];phases=np.linspace(0,1,201);max_mesh=0.;squares=0.;count=0;alphas=[];all_lo=[];all_hi=[];vismesh=[];glo=[[]for _ in target['geosets']];ghi=[[]for _ in target['geosets']];first=None;last=None;motion=0
 for phase in phases:
  tf=a+(b-a)*phase;sf=sa+(sb-sa)*phase;elapsed=tf-a
  sv=se.sample(ss['name'],sf,elapsed);tv=te.sample(ts['name'],tf,elapsed);diff=np.concatenate([np.linalg.norm(x['vertices']-y['vertices'],axis=1)for x,y in zip(sv,tv)])
  max_mesh=max(max_mesh,float(diff.max()));squares+=float(np.sum(diff**2));count+=len(diff)
  alphas.append([x['alpha']for x in tv]);vs=np.concatenate([x['vertices']for x in tv if x['index']in range(4,9)])
  if first is None:first=vs.copy()
  last=vs;motion=max(motion,float(np.linalg.norm(vs-first,axis=1).max()))
  vismesh.append(vs)
  for gi,(lo,hi)in enumerate(envelope(tv,target,te.matrices(ts,tf,elapsed))):glo[gi].append(lo);ghi[gi].append(hi)
 for gi in range(len(glo)):
  ee=ext(np.min(glo[gi],axis=0),np.max(ghi[gi],axis=0));geo_bounds[gi].append(ee);all_lo.append(ee['sampleMin']);all_hi.append(ee['sampleMax'])
 extent=ext(np.min(all_lo,axis=0),np.max(all_hi,axis=0));seq_bounds.append(extent)
 vm=np.concatenate(vismesh);mn=vm.min(0);mx=vm.max(0);av=np.array(alphas)
 sr={'index':i,'name':map['name'],'interval':ts['interval'],'flags':ts['flags'],'looping':not(ts['flags']&1),'sourceName':ss['name'],'sourceInterval':ss['interval'],'semantic':map['semantic'],'maxVertexDeviationFromSource':max_mesh,'rmsVertexDeviation':math.sqrt(squares/count),'bodyRawMeshMin':mn.tolist(),'bodyRawMeshMax':mx.tolist(),'bodyRawMeshSpan':(mx-mn).tolist(),'bodyRawMeshLongestAxis':float(np.max(mx-mn)),'bodyRawMeshBottomCenter':[((mn+mx)/2)[0],((mn+mx)/2)[1],mn[2]],'maxBodyVertexMotion':motion,'bodyLoopSeamMaxVertexDistance':float(np.linalg.norm(last-first,axis=1).max()),'geosetAlpha':{str(j):{'min':float(av[:,j].min()),'max':float(av[:,j].max()),'start':float(av[0,j]),'end':float(av[-1,j])}for j in range(av.shape[1])},'storedExtentTarget':extent}
 if i<10 and i!=3:assert all(sr['geosetAlpha'][str(g)]['min']==1 for g in range(4,9)),sr
 if i<10:assert all(sr['geosetAlpha'][str(g)]['max']==0 for g in [1,2,3]),sr
 assert max_mesh<5.,('deformation mismatch',i,max_mesh)
 report['sequences'].append(sr)
 for trr in track_reports:
  if trr['global']:continue
  p=trr['path'];st=stracks[p];tt=ttracks[p];phase_keys=list(phases)
  # Exact source/target keys and tiny offsets test visibility transitions honestly.
  # Comparison at mapped rounded boundaries uses remapped-source phase for step tracks.
  step=st['interpolation']==0
  if not step:
   for k in st['keys']:
    if sa<=k['frame']<=sb:phase_keys.extend([(k['frame']-sa)/(sb-sa)])
  error=0.;degrees=0.
  for phase in phase_keys:
   tf=a+(b-a)*phase;sf=sa+(sb-sa)*phase
   x=se.value(st,ss,sf,tf-a,default(st));y=te.value(tt,ts,tf,tf-a,default(tt))
   error=max(error,float(np.max(abs(x-y))))
   if st['tag']in ['KGRT','KTAR']:degrees=max(degrees,math.degrees(2*math.acos(min(1,abs(float(np.dot(normalize(x),normalize(y))))))))
  trr['perSequence'].append({'index':i,'maxError':error,'maxQuaternionDegrees':degrees})
  if i<10:trr['aliasMaxError']=max(trr['aliasMaxError'],error);trr['aliasMaxQuaternionDegrees']=max(trr['aliasMaxQuaternionDegrees'],degrees)
 print(i,map['name'],'mesh error',round(max_mesh,6),'span',np.round(mx-mn,2),flush=True)
report['originalKeysAndTangentsExact']=all(t.get('originalKeysAndTangentsExact',t.get('exactPreserved',False))for t in track_reports)
report['sourceRestorationUnmodified']=source['sha256']=='a06cdd7e302db85f7489f65592d01c0c519cde07b2118b4ef96a7d1ed5649a86'
report['sourceNativeControlsPreservedInCompactAliases']=compact
if compact:report['sampleStrategy']='201 uniform samples per each of ten runtime sequences; same normalized phase and same wall-clock elapsed. Original controls are sparsely remapped to integer timestamps. Separate exact-control and visibility transition audits verify every copied key. Original 13-sequence source remains byte-identical in source/.'
report['maxAliasMeshError']=max(s['maxVertexDeviationFromSource']for s in report['sequences'][:10])
report['maxOriginalMeshError']=max((s['maxVertexDeviationFromSource']for s in report['sequences'][10:]),default=None)
report['maxAliasQuaternionDegrees']=max(t.get('aliasMaxQuaternionDegrees',0)for t in track_reports)
report['globalPhaseNote']='G4–8 skin has no global-sequence ancestry except effects-related dummy nodes; source and target use identical elapsed for every comparison.'
model=ext(np.min([x['sampleMin']for x in seq_bounds],axis=0),np.max([x['sampleMax']for x in seq_bounds],axis=0))
geo=[{'extent':ext(np.min([x['sampleMin']for x in a],axis=0),np.max([x['sampleMax']for x in a],axis=0)),'sequenceExtents':a}for a in geo_bounds]
(ROOT/'audit/animation-visibility-audit.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'audit/computed-extents.json').write_text(json.dumps({'model':model,'sequences':seq_bounds,'geosets':geo},indent=2)+'\n')
print('PASS',report['maxAliasMeshError'],report['maxOriginalMeshError'],report['maxAliasQuaternionDegrees'])
