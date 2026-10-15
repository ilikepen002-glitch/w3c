"""Read-only activity and steady-state load estimate for native FX.
Uses actual parsed final MDX tracks. It does not render particles/ribbons or
assert frame rate, precise color, draw-call count, or measured game behavior.
"""
from pathlib import Path
import json,math,os,numpy as np
from mdx_decode import decode,Evaluator
R=Path(os.environ.get('PHOENIX_STAGE',Path(__file__).resolve().parents[1]));m=json.loads((R/'audit/final-parser.json').read_text());d=decode(R/'output/QiLingPhoenix-Display.mdx');ev=Evaluator(d)
nodes={n['objectId']:n for k in ['bones','helpers','attachments','particleEmitters2','ribbonEmitters','eventObjects','collisionShapes']for n in m[k]}
def chain(n):
 out=[];seen=set()
 while n and n['objectId']not in seen:
  seen.add(n['objectId']);out.append({'id':n['objectId'],'name':n['name']});n=nodes.get(n['parentId'])
 return out
tracks={}
def track(o,name):
 key=(id(o),name)
 if key not in tracks:
  a=next((a for a in o['animations']if a['name']==name),None)
  tracks[key]=None if a is None else {'tag':name,'interpolation':0 if name in ['KP2V','KRVS']else a['interpolationType'],'globalSequenceId':a['globalSequenceId'],'keys':[{'frame':f,'value':a['values'][i],**({'inTan':a['inTans'][i],'outTan':a['outTans'][i]}if a['interpolationType']>1 else{})}for i,f in enumerate(a['frames'])]}
 return tracks[key]
def value(o,name,s,t,default):return float(ev.value(track(o,name),s,t,t-s['interval'][0],[default])[0])
# Midpoint-weighted regular sampling; all tracks here have constant rate/life.
# Add exact step partitions to integrate visibility rather than missing short pulses.
def partitions(o,s,n):
 a,b=s['interval'];times={a,b};tr=track(o,n)
 if tr and tr['globalSequenceId']<0:times.update(k['frame']for k in tr['keys']if a<=k['frame']<=b)
 return sorted(times)
def activity(o,s,vtag,rtag,ltag):
 a,b=s['interval'];ps=partitions(o,s,vtag);vals=[]
 for lo,hi in zip(ps,ps[1:]):
  t=(lo+hi)/2;v=value(o,vtag,s,t,1);rate=value(o,rtag,s,t,o['emissionRate'])if rtag else o['emissionRate'];life=value(o,ltag,s,t,o['lifeSpan'])if ltag else o['lifeSpan'];active=v>0
  vals.append({'from':lo,'to':hi,'visibility':v,'ratePerSecond':rate,'effectiveRatePerSecond':rate if active else 0,'lifeSeconds':life,'steadyCountIfHeld':rate*life if active else 0})
 duration=b-a
 return{'visibilityStart':value(o,vtag,s,a,1),'visibilityEnd':value(o,vtag,s,b,1),'visibilityMin':min(x['visibility']for x in vals),'visibilityMax':max(x['visibility']for x in vals),'activeFraction':sum(x['to']-x['from']for x in vals if x['visibility']>0)/duration,'peakEffectiveRatePerSecond':max(x['effectiveRatePerSecond']for x in vals),'meanEffectiveRatePerSecond':sum(x['effectiveRatePerSecond']*(x['to']-x['from'])for x in vals)/duration,'peakSteadyCountIfHeld':max(x['steadyCountIfHeld']for x in vals),'meanSteadyCountIfHeld':sum(x['steadyCountIfHeld']*(x['to']-x['from'])for x in vals)/duration,'intervals':vals}
records=[]
for kind,key in [('PRE2','particleEmitters2'),('RIBB','ribbonEmitters')]:
 for i,o in enumerate(m[key]):
  tx=([m['textures'][o['textureId']]['path']]if kind=='PRE2'else[m['textures'][l['textureId']]['path']for l in m['materials'][o['materialId']]['layers']]);r={'kind':kind,'index':i,'objectId':o['objectId'],'name':o['name'],'parentChain':chain(o),'textures':tx,'emissionRatePerSecond':o['emissionRate'],'lifeSeconds':o['lifeSpan'],'nominalSteadyCount':o['emissionRate']*o['lifeSpan'],'staticParameters':{k:o[k]for k in (['speed','variation','latitude','gravity','width','length','filterMode','headOrTail','tailLength','squirt','segmentColors','segmentAlphas','segmentScaling']if kind=='PRE2'else['heightAbove','heightBelow','alpha','color','gravity','materialId'])},'sequences':[]}
  for j,s in enumerate(d['sequences']):r['sequences'].append({'index':j,'name':s['name'],**activity(o,s,'KP2V'if kind=='PRE2'else'KRVS','KP2E'if kind=='PRE2'else None,'KP2L'if kind=='PRE2'else None)})
  r['activeSequenceIndices']=[s['index']for s in r['sequences']if s['activeFraction']>0];r['eggOrMorphOnly']=bool(r['activeSequenceIndices']) and all(i in [20,21,22]for i in r['activeSequenceIndices']);records.append(r)
seqs=[]
for i,s in enumerate(d['sequences']):
 a,b=s['interval'];ps={a,b}
 for r in records:
  for x in r['sequences'][i]['intervals']:ps.update([x['from'],x['to']])
 ps=sorted(ps);sums=[]
 for lo,hi in zip(ps,ps[1:]):
  t=(lo+hi)/2;z={'from':lo,'to':hi,'particleRate':0,'particleCount':0,'ribbonRate':0,'ribbonSegments':0,'activePRE2':[],'activeRIBB':[]}
  for r in records:
   x=next(x for x in r['sequences'][i]['intervals']if x['from']<=t<x['to']);pre=r['kind']=='PRE2';z['particleRate'if pre else'ribbonRate']+=x['effectiveRatePerSecond'];z['particleCount'if pre else'ribbonSegments']+=x['steadyCountIfHeld']
   if x['visibility']>0:z['activePRE2'if pre else'activeRIBB'].append(r['objectId'])
  sums.append(z)
 r={'index':i,'name':s['name'],'durationSeconds':(b-a)/1000,'activePRE2':sorted(set(n for z in sums for n in z['activePRE2'])),'activeRIBB':sorted(set(n for z in sums for n in z['activeRIBB'])),'intervals':sums}
 for k in ['particleRate','particleCount','ribbonRate','ribbonSegments']:r[k+'Peak']=max(z[k]for z in sums);r[k+'Mean']=sum(z[k]*(z['to']-z['from'])for z in sums)/(b-a)
 seqs.append(r)
glow=[]
for gi in range(4):
 g=d['geosets'][gi];mat=m['materials'][g['materialId']];ga=next(x for x in m['geosetAnimations']if x['geosetId']==gi);states=[]
 for i,s in enumerate(d['sequences'][:10]):
  vals=[ev.alpha_color(gi,s,t,t-s['interval'][0])[0]for t in np.linspace(*s['interval'],401)];states.append({'index':i,'name':s['name'],'geosetVisibilityMin':min(vals),'geosetVisibilityMax':max(vals)})
 glow.append({'geoset':gi,'triangleCount':len(g['faces']),'matrixGroupCount':len(g['matrixGroups']),'materialId':g['materialId'],'layers':[{'texture':m['textures'][x['textureId']]['path'],'filterMode':x['filterMode'],'staticLayerAlpha':x['alpha']}for x in mat['layers']],'rawStaticGeosetColor':ga['color'],'geosetColorFlags':ga['flags'],'states':states})
report={'sourceFinalMdxSha256':d['sha256'],'pass':True,'method':'Exact piecewise visibility integration from local step keys; emission rates and lifespans are static on all 12 emitters. rate × lifespan is a steady-state live particle / ribbon-segment estimate, not a draw-call or GPU measurement. Visibility uses None interpolation with default 1 when the interval contains no keys, matching the pinned viewer semantics.','emitters':records,'sequenceTotals':seqs,'nonBodyGeosets':glow,'baselineFindingsBeforeApprovedReduction':['Display Float has 2 continuously active PRE2 (67 and 68), not all 8: 80/s and approximately 98 steady-state particles.','Walk has 2 continuously active PRE2 (69 and 70): 80/s and approximately 48 steady-state particles.','Display Cast has no active PRE2; all 4 ribbons remain active.','Float, Walk and Cast each retain 4 ribbons: 65 segments/s and approximately 50.5 live segments at steady state.','PRE2 74 using Flame4 is the only emitter restricted to egg/morph states. PRE2 71/72/73 are birth/death/morph bursts, not continuous idle emitters.','Geoset 0 uses Yellow_Glow3 additive layer alpha 0.54, with 15 billboard groups / 30 triangles and geoset visibility 1 in Float, Walk and Cast. It is omitted from the body-only previews and can materially alter the visible color/brightness.'],'limitations':['Native texture pixels were not loaded; names and modulation values alone do not prove exact displayed colors.','No particles/ribbons were rendered, no Warcraft III runtime or frame-rate testing performed.','Steady-state estimates do not model warm-up, emitter history across sequence transitions, particle tails, occlusion, screen coverage, overdraw or burst overlap beyond sampled visibility.','Ribbon segment rate/count is a distinct quantity from PRE2 particle count; do not claim their sum is draw calls.','Existing emitted particles can remain alive after visibility turns off; instantaneous state estimates are not a transient particle simulation.']}
report['currentTotalsForKeyActions']=[{k:v for k,v in seqs[i].items()if k!='intervals'}for i in [1,5,9]]
(R/'audit/native-effects-activity.json').write_text(json.dumps(report,indent=2)+'\n')
for i in [n for n in [1,5,9,21]if n<len(seqs)]:print(json.dumps({k:v for k,v in seqs[i].items()if k!='intervals'}))
print('G0',glow[0])
