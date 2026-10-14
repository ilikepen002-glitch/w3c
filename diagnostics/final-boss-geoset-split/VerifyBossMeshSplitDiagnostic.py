import sys,json,re,hashlib,subprocess
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path(sys.argv[3]) if len(sys.argv)>3 else Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyGlobalRankingsArtifact import members
from VerifyMapBrandingArtifact import parse_info
from VerifyBossSpellResistanceArtifact import BossJassRuntime, canonical_function
from VerifyTowerUpgradeArtifact import JassScalarEvaluator
class Replay(BossJassRuntime):
 def __init__(self,s):
  JassScalarEvaluator.__init__(self,s);self.globals={}
  for kind,array,name in re.findall(r'^(\w+) (array )?(\w+)',s.split('globals\n',1)[1].split('endglobals',1)[0],re.M):
   default=False if kind=='boolean' else 0 if kind in ('integer','real') else None
   self.globals[name]=defaultdict(lambda value=default:value) if array else default
  self.globals.update(self.constants);self.execution_depth=self.executed_steps=0;self.calls=Counter()
  self.units={};self.seq=1000;self.text='';self.events=[];self.globals['PLAYER_NEUTRAL_PASSIVE']=15
 def native(self,n,a):
  if n in ('Player','I2S'):return True,a[0] if n=='Player' else str(a[0])
  if n=='GetLocalPlayer':return True,0
  if n=='GetEventPlayerChatString':return True,self.text
  if n=='CreateUnit':
   self.seq+=1;self.units[self.seq]={'id':a[1],'x':a[2],'y':a[3],'facing':a[4]};self.events.append((n,*a));return True,self.seq
  if n=='RemoveUnit':self.units.pop(a[0]);self.events.append((n,*a));return True,None
  if n in ('GetUnitX','GetUnitY','GetUnitFacing'):return True,self.units[a[0]][{'GetUnitX':'x','GetUnitY':'y','GetUnitFacing':'facing'}[n]]
  if n=='SetUnitFacing':self.units[a[0]]['facing']=a[1];self.events.append((n,*a));return True,None
  if n in ('SetUnitInvulnerable','SetUnitPathing','SetUnitAnimationByIndex','IssueImmediateOrder','IssuePointOrder','PanCameraToTimed','DisplayTimedTextToPlayer'):
   self.events.append((n,*a));return True,True if n.startswith('Issue') else None
  if n not in self.functions:raise AssertionError('Unexpected native '+n)
  return False,None
 def chat(self,text):self.text=text;self.invoke('bossMeshCommand')
def main():
 path=Path(sys.argv[1]);m=Mpq(path.read_bytes());base=Mpq(subprocess.check_output(['git','show','15204026:ExampleMap.w3x'],cwd=ROOT));before,after=members(base),members(m);assert before.keys()==after.keys();changed=[k for k in before if before[k][1]!=after[k][1]];allowed={'war3map.j','war3map.w3i','war3mapimported\\eclipsespellweaver.mdx','war3mapimported\\uncrownedabyssking.mdx','(attributes)'};assert set(changed)<=allowed,changed
 script=m.extract('war3map.j').decode();old=base.extract('war3map.j').decode();names=lambda s:set(re.findall(r'^function (\w+) takes',s,re.M));oldn,newn=names(old),names(script);deleted=oldn-newn;assert not deleted,deleted
 delta=[]
 blocks=lambda s:{m[1]:m[0] for m in re.finditer(r'^function (\w+) takes [^\n]+\n.*?^endfunction',s,re.M|re.S)}
 oldblocks,newblocks=blocks(old),blocks(script)
 for n in oldn:
  if canonical_function(oldblocks[n],n)!=canonical_function(newblocks[n],n):delta.append(n)
 new=sorted(newn-oldn)
 assert new==sorted(['bossMeshAnimation','bossMeshClear','bossMeshCommand','bossMeshCreate','bossMeshFocus','bossMeshReport','init_TDBossMeshSplitDiagnostic'])
 assert set(delta)=={'config','initGlobals','main'}
 canon=lambda blocks,n:canonical_function(blocks[n],n)[2]
 assert canon(newblocks,'config').replace('SetMapName("BossMeshSplitTest网格诊断")','SetMapName("契灵守卫战")')==canon(oldblocks,'config')
 added=['set ref_function_bossMeshCommand = function bossMeshCommand','set ref_function_init_TDBossMeshSplitDiagnostic = function init_TDBossMeshSplitDiagnostic']
 assert '\n'.join(line for line in canon(newblocks,'initGlobals').splitlines() if line not in added)==canon(oldblocks,'initGlobals')
 initblock='call TriggerAddCondition(v0, Condition(ref_function_init_TDBossMeshSplitDiagnostic))\nif not TriggerEvaluate(v0) then\ncall error("Could not initialize package TDBossMeshSplitDiagnostic.", "debug")\nendif\ncall TriggerClearConditions(v0)\n'
 assert canon(newblocks,'main').replace(initblock,'')==canon(oldblocks,'main')
 glob=lambda s:s.split('globals\n',1)[1].split('endglobals',1)[0].splitlines()
 addedglobals={'unit TDBossMeshSplitDiagnostic_bossMeshFixture=null','boolean TDBossMeshSplitDiagnostic_bossMeshMoveRight=false','code ref_function_bossMeshCommand=null','code ref_function_init_TDBossMeshSplitDiagnostic=null'}
 assert [l for l in glob(script) if l not in addedglobals]==glob(old)
 def info_normalized(data):
  fields,spans=parse_info(data)
  for key in sorted(['name','title','subtitle','loading_text'],key=lambda k:spans[k][0],reverse=True):
   start,end=spans[key];data=data[:start]+b'DIAGNOSTIC-LABEL\0'+data[end:]
  return data
 assert info_normalized(base.extract('war3map.w3i'))==info_normalized(m.extract('war3map.w3i'))
 fields,_=parse_info(m.extract('war3map.w3i'));assert fields['name'].startswith('BossMeshSplitTest网格诊断 ') and fields['title']==fields['name'];assert '未验证' in fields['subtitle']
 for name,digest in [('EclipseSpellweaver','5f10d5a9f9568c7da35e7eba39cd1dbe5e5e1ecd7b01ecf94e8790335e1022e6'),('UncrownedAbyssKing','9ace10f09e7fe0a4c3c800f51070c130a51ce6f032a1391ab0be0d666c29ad56')]:
  assert hashlib.sha256(m.extract('war3mapImported\\'+name+'.mdx')).hexdigest()==digest

 r=Replay(script);r.chat('-boss clear');assert not r.units;r.chat('-boss24');assert len(r.units)==1;assert list(r.units.values())[0]['id']==int.from_bytes(b'uB24','big')
 for cmd,index in [('stand',0),('walk',1),('attack',2),('spell',2),('hit',3),('death',4),('portrait',5)]:
  r.chat('-boss '+cmd);assert [e for e in r.events if e[0]=='SetUnitAnimationByIndex'][-1][2]==index
 r.chat('-boss move');r.chat('-boss move');assert [e[3] for e in r.events if e[0]=='IssuePointOrder']==[-1648.0,-2448.0]
 r.chat('-boss turn');assert list(r.units.values())[0]['facing']==360
 r.chat('-boss32');assert len(r.units)==1;assert list(r.units.values())[0]['id']==int.from_bytes(b'uB32','big')
 for cmd in ['stand','walk','attack','hit','death','portrait']:r.chat('-boss '+cmd)
 r.chat('-boss focus');r.chat('-boss clear');r.chat('-boss clear');assert not r.units;r.chat('-boss attack');assert not r.units
 assert 'TriggerRegisterPlayerChatEvent(chat, Player(0), "-boss", false)' in script
 report={'mapSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'base':'15204026','memberCount':len(after),'changedMembers':changed,'newFunctions':new,'changedInheritedFunctions':sorted(delta),'replay':'PASS create/replace/animations/movement/turn/focus/idempotent clear/null guards','nativeEngineTested':False}
 print(json.dumps(report,indent=2));Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
