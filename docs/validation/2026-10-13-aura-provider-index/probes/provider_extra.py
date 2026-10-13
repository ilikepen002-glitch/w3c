from provider_compare import *
def extra(s,o):
 r=make(s);out={}
 # No provider must still publish timed effects and process their independent expiry.
 require(members(r) in (None,0),'Empty fixture has candidate')
 r.invoke('tdEnemySlowOfferTimed',1000,101,12,1,.08,3.);refresh(r,1000)
 speed=[r.units[1000]['speed']];r.now+=3.;refresh(r,1000);speed.append(r.units[1000]['speed'])
 require(speed==[239.20000000000002,260.] or all(abs(a-b)<1e-6 for a,b in zip(speed,[239.2,260.])),'Empty-source timed apply/expiry lost')
 out['empty_provider_timed_expiry']=speed
 # Equal rank and equal power are independent of insertion order.
 for t in [101,102]:set_source(r,t,'uA11',[],[(0,'iW10')])
 refresh(r,1000);before=state(r,1000)
 if 'tdAuraSetProviderCandidate' in r.functions:r.invoke('tdAuraSetProviderCandidate',101,False)
 r.invoke('tdRefreshTowerEquipmentBonuses',101,None);refresh(r,1000)
 require(before==state(r,1000),'Equal-source permutation changed numeric state');out['equal_rank_power_order']=True
 # Native external disappearance rejects immediately; bounded owner cleanup releases node.
 old=r.invoke('tdAuraTargetFor',101);r.units[101]['type']=0;refresh(r,1000)
 r.invoke('tdForgetAuraTarget',101);require(r.invoke('tdAuraTargetFor',101)==0,'Explicit retirement retained source record')
 r.units[101]['type']=rawcode('uA11');r.units[101]['inventory']={};r.invoke('tdRefreshTowerEquipmentBonuses',101,None)
 new=r.invoke('tdAuraTargetFor',101);require(new==old,'Reuse test did not actually reuse class ID')
 if members(r)!=None:require(not r.globals['TDAuraTarget_providerCandidate'][new],'Recycled class inherited membership')
 out['actual_class_id_reused']=old==new
 # Add 41 owned providers; strongest is beyond index40, must never silently cap.
 set_source(r,102,'uA11',[],[])
 for i in range(41):
  t=300+i;r.units[t]={**r.units[101],'abilities':{},'inventory':{}};set_source(r,t,'uA11',[],[(0,'iP10' if i==40 else 'iW10')])
 require(members(r) in (None,41),'Synthetic41 source membership truncated')
 refresh(r,1000);strong=r.units[1000]['speed'];require(abs(strong-208.)<1e-6,'41st strongest aura dropped')
 set_source(r,340,'uA11',[],[]);refresh(r,1000);weak=r.units[1000]['speed'];require(abs(weak-244.4)<1e-6,'Beyond40 removal fallback failed')
 for i in range(41):r.invoke('tdForgetAuraTarget',300+i)
 require(members(r) in (None,0),'Synthetic cleanup retained source nodes')
 out['synthetic41_speeds']=[strong,weak];out['synthetic_cleanup_empty']=True
 # Real trial target projection with non-provider timed origin.
 r.enter(8);t=r.target(0);r.invoke('tdEnemySlowOfferTimed',t,101,12,1,.08,3.);refresh(r,t)
 require(abs(r.units[t]['speed']-239.2)<1e-6,'Trial empty-provider timed aura lost')
 out['trial_timed_speed']=r.units[t]['speed']
 return out
if __name__=='__main__':
 data=[]
 for path in sys.argv[1:3]:
  m=Mpq(Path(path).read_bytes());s=m.extract('war3map.j').decode();o=unit_objects(m.extract('war3map.w3u'));data.append(extra(s,o))
 require(data[0]==data[1],'Extra lifecycle numeric mismatch');print(json.dumps({'status':'PASS','results':data[1]},indent=2))
