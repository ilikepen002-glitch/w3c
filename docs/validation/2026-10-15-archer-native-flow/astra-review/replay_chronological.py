import json,sys,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/workspace/shared/w3c-archer-native-flow');sys.path.insert(0,str(root/'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyTowerTargetPriorityArtifact import TowerTargetRuntime,register_actual_split_listener
m=Path('/workspace/shared/archer-native-recovery-20261015/archer-native-candidate.w3x')
s=Mpq(m.read_bytes()).extract('war3map.j').decode()
class Timed(TowerTargetRuntime):
 def __init__(self):
  self.deadlines={};self.timed_expiries=0
  super().__init__(s,'uA6B')
  self.deadlines.clear();self.scheduled.clear()
 def native(self,name,args):
  ans=super().native(name,args)
  if name=='doAfter': self.deadlines[self.timer_serial]=(self.now+args[0],args[1])
  return ans
 def advance(self,t):
  while True:
   due=[(d,k,cb) for k,(d,cb) in self.deadlines.items() if d<=t and not self.timers[k]['destroyed']]
   if not due:break
   d,k,cb=min(due);del self.deadlines[k];self.now=d;self.executed_steps=0;self.run_timer(cb);self.timed_expiries+=1
  self.now=t;self.executed_steps=0
 def queue(self):return list(self.lists[self.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']])
def replay(changing):
 r=Timed();register_actual_split_listener(r)
 for h in (102,103):r.enemy(h,life=1e6,x=220.)
 events=[];rows={};peak=0
 for i in range(20):
  target=(102,103,102)[i%3] if changing else 102
  victims=[300+i*2,301+i*2]
  for h in victims:r.enemy(h,life=1e6,x=220.)
  events += [(i*.07,0,i,target,victims),(i*.07+.25,1,i,target,victims)]
 for t,kind,i,target,victims in sorted(events):
  r.advance(t)
  if kind==0:
   r.visible_units=[target,*victims];before=len(r.split_visual_launches);r.attack(target)
   v=r.queue()[-1];shots=r.globals['TDArcherSplitArrowVolley_extraShots'][v]
   chosen=[r.globals['TDArcherSplitArrowShot_target'][x] for x in r.lists[shots]]
   assert chosen==victims,(i,chosen,victims)
   assert len(r.split_visual_launches)-before==2
   rows[i]={'shot':i+1,'start':round(t,6),'primary':target,'victims':victims,'amount':11.+i,'visuals':2}
   peak=max(peak,len(r.queue()))
  else:
   before=len(r.native_damage);r.emit(11.+i,target=target);r.flush();actual=r.native_damage[before:]
   assert [(h[0],h[1],h[2]) for h in actual]==[(101,h,11.+i) for h in victims],(i,actual,victims)
   rows[i].update(hit=round(t,6),damage_segments=len(actual))
 assert not r.queue(),r.queue()
 r.advance(max(e[0] for e in events)+1.)
 assert sum(value != 0 for value in r.globals['TDArcherSplitArrowVolley_typeId'].values())==0
 assert not r.script_orders and not r.stop_orders and r.calls['tdTargetPriorityBest']==0
 assert r.calls['tdTargetPriorityAcceptAttack']==0
 assert not r.acquisition
 return {'changing_primary':changing,'rows':list(rows.values()),'peak_pending_volleys':peak,'side_damage_segments':len(r.native_damage),'expiry_callbacks':r.timed_expiries,'final_live_volleys':sum(value != 0 for value in r.globals['TDArcherSplitArrowVolley_typeId'].values()),'scripted_orders':0,'acquisition_writes':0}
out={'map_sha256':hashlib.sha256(m.read_bytes()).hexdigest(),'status':'PASS','boundary':'Actual packed registration/queue/consume/damage/expiry. Native clock/order/render delivery is controlled. Main arrival 0.25s is an assumed input within unchanged .55s expiry, not a Warcraft attack-point measurement. 0.07s start spacing deliberately stresses overlapping shots.','cases':[replay(False),replay(True)]}
print(json.dumps(out,indent=2))
