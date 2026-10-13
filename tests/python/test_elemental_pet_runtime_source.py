"""Execute bounded actual Wurst source bodies with explicit native stubs.
This is source behavior evidence, not Wurst type/JASS/native-game evidence.
"""
import re,sys,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from VerifyPetManagerSource import source,function_body,_expression,scalar_helpers

def compile_body(text,name,n,fields=(),pyname=None):
    n.setdefault('int',int)
    args,body=function_body(text,name);out=[f'def {pyname or name}('+','.join(args)+'):']
    global_names=set(fields)-set(args)
    if global_names:out.append('    global '+','.join(sorted(global_names)))
    lines=body.splitlines();skip=False
    for i,raw in enumerate(lines):
        if skip:skip=False;continue
        line=raw.lstrip('\t');indent=1+len(raw)-len(line)
        if not line.strip() or line.startswith('//'):continue
        line=re.sub(r'\b(?:let|var|unit|TDPetQueuedAttack) (\w+) =',r'\1 =',line)
        line=re.sub(r'\bnew (\w+)\(',r'\1(',line)
        line=line.replace('this castTo int','taskToken').replace('this.', '')
        line=re.sub(r'(\([^()]*\)|\w+)\.toInt\(\)',r'int(\1)',line)
        if line.endswith('doAfter(0.0) ->'):
            callback=lines[i+1].strip();line=line[:-len('doAfter(0.0) ->')]+'doAfter(0.0, '+callback[:-2]+')';skip=True
        if line.startswith('else if '):line='elif '+_expression(line[8:])+':'
        elif line.startswith(('if ','while ')):
            keyword,expr=line.split(' ',1);line=keyword+' '+_expression(expr)+':'
        elif line=='else':line='else:'
        elif line.startswith('for '):
            match=re.fullmatch(r'for (\w+) = (.*?) to (.*)',line)
            if match:line=f'for {match[1]} in range({_expression(match[2])}, ({_expression(match[3])})+1):'
            else:line=_expression(line)+':'
        elif line.startswith('destroy '):line='destroy('+line[8:]+')'
        elif line.startswith('return '):line='return '+_expression(line[7:])
        elif line in ('return','continue','break'):pass
        elif ' = ' in line:
            left,right=line.split(' = ',1);line=left+' = '+_expression(right)
        else:line=_expression(line)
        out.append('    '*indent+line)
    exec('\n'.join(out),n);return n[pyname or name]

class List(list):
    def add(self,x):self.append(x)
    def get(self,i):return self[i]
    def isEmpty(self):return not self
    def iterator(self):return Iter(self)
class Iter:
    def __init__(self,x):self.x=x;self.i=0;self.current=None
    def hasNext(self):return self.i<len(self.x)
    def next(self):self.current=self.x[self.i];self.i+=1;return self.current
    def remove(self):self.x.remove(self.current);self.i-=1
    def close(self):pass
class Callback:
    def __init__(self,f):self.f=f;self.destroyed=False;self.calls=0
    def call(self):self.calls+=1;self.f()
class Packet:
    def __init__(self,owner,callback):self.owner=owner;self.callback=callback;self.destroyed=False
class SourceQueueTests(unittest.TestCase):
    def setUp(self):
        self.timers=[];self.trace=[];self.over=False
        def destroy(x):
            self.assertFalse(x.destroyed,'double destroy');x.destroyed=True
            if isinstance(x,Packet):destroy(x.callback)
        def after(delay,f):
            self.assertEqual(delay,0.);t=SimpleNamespace(f=f,destroyed=False);self.timers.append(t);return t
        self.n=dict(queuedAttacks=List(),tdPetPendingOriginal=0,dispatchTimer=None,dispatching=False,
            tdIsGameOver=lambda:self.over,TDPetQueuedAttack=Packet,destroy=destroy,doAfter=after,
            error=lambda text:(_ for _ in ()).throw(ValueError(text)))
        text=source('TDPetAttackQueue')
        for name in ('tdPetCancelQueuedAttacks','tdPetClearAttackQueue','dispatchQueuedAttacks','tdPetWakeIdleAttackQueue','tdPetAttackQueueBusy','tdPetQueueAttack','tdPetBeginOriginalPhase','tdPetEndOriginalPhase'):
            compile_body(text,name,self.n,('tdPetPendingOriginal','dispatchTimer','dispatching'))
    def add(self,f=None,owner=1):
        c=Callback(f or (lambda:self.trace.append('hit')));self.n['tdPetQueueAttack'](owner,c);return c
    def pump(self):
        while self.timers:
            t=self.timers.pop(0)
            if not t.destroyed:t.f();self.n['destroy'](t)
    def test_idle_without_another_original_executes_once(self):
        c=self.add();self.pump();self.pump();self.assertEqual(c.calls,1);self.assertTrue(c.destroyed)
    def test_later_original_and_early1_admission_wait_for_post(self):
        for after_wake in (False,True):
            self.setUp();c=self.add()
            if after_wake:self.n['tdPetWakeIdleAttackQueue']()
            self.n['tdPetBeginOriginalPhase']();self.pump();self.assertEqual(c.calls,0)
            self.n['tdPetEndOriginalPhase']();self.pump();self.assertEqual(c.calls,1)
    def test_nested_callbacks_owner_cancel_and_gameover_are_single_owned(self):
        self.add(lambda:self.add());self.pump();self.assertEqual(self.trace,['hit'])
        c=self.add(owner=2);self.n['tdPetCancelQueuedAttacks'](2);self.pump();self.assertEqual(c.calls,0);self.assertTrue(c.destroyed)
        c=self.add();self.over=True;self.pump();self.assertEqual(c.calls,0);self.assertTrue(c.destroyed)
    def test_match_records_wait_for_current_packet_original_post_and_effects(self):
        self.n['tdPetEffectTaskCount']=lambda:0
        idle=compile_body(source('TDPetRuntime'),'tdPetCanDestroyMatchRecords',self.n)
        seen=[];self.add(lambda:seen.append(idle()));self.pump()
        self.assertEqual(seen,[False]);self.assertTrue(idle())
        self.n['tdPetBeginOriginalPhase']();self.assertFalse(idle())
        self.n['tdPetEndOriginalPhase']();self.assertTrue(idle())
        self.n['tdPetEffectTaskCount']=lambda:1;self.assertFalse(idle())

    def test_many_admissions_share_one_pending_timer(self):
        cs=[self.add() for _ in range(20)];self.assertEqual(len(self.timers),1);self.pump();self.assertEqual(sum(c.calls for c in cs),20)

class Unit(int):
    def getPos(self):return (int(self),0.)
class CastSourceTests(unittest.TestCase):
    def test_control_table_full_cannot_create_thirteenth_orphan(self):
        n=scalar_helpers();calls=[]
        n.update(aoeValid=lambda target:True,remember=lambda target:-1,tdIsBossUnitTypeId=lambda typeId:False,
            GetUnitTypeId=lambda target:1,Orders=SimpleNamespace(entanglingroots=1,thunderbolt=2),
            tdTryEnemyControlToken=lambda *args:calls.append(args) or True,
            host=1,pet=SimpleNamespace(lane=0),taskToken=7,expiresAt=.25,getElapsedGameTime=lambda:.05,RMaxBJ=max,RMinBJ=min,
            TD_PET_BOSS_CONTROL_ID=10,TD_PET_ROOT_CONTROL_ID=11,TD_PET_FREEZE_CONTROL_ID=12,TD_PET_STAGGER_CONTROL_ID=13,
            TD_PET_BOSS_BUFF_ID=20,TD_PET_ROOT_BUFF_ID=21,TD_PET_FREEZE_BUFF_ID=22,TD_PET_STAGGER_BUFF_ID=23)
        control=compile_body(source('TDPetCastContext'),'control',n,('expiresAt',))
        self.assertFalse(control(13,2,.6));self.assertEqual(calls,[])
        n['remember']=lambda target:0;self.assertTrue(control(1,2,.6));self.assertEqual(len(calls),1)
        mutated=source('TDPetCastContext').replace('\t\tif remember(target) < 0\n\t\t\treturn false\n','')
        n['remember']=lambda target:-1
        self.assertTrue(compile_body(mutated,'control',n,('expiresAt',))(13,2,.6),'negative mutation must expose orphan')
    def test_actual_periodic_deadlines_counts_and_distinct_damage_sequences(self):
        expected={21:[(0.,.6),(.2,.6),(.4,.6),(.6,.6)],
                  22:[(1.,.45),(2.,.45),(3.,.45),(4.,.45)],
                  31:[(1.,.35),(2.,.35),(3.,.35),(4.,.35)],
                  33:[(.75,1.3),(1.75,.25),(2.75,.25),(3.75,.25)],
}
        for skill,want in expected.items():
            events=[];n=scalar_helpers()
            n.update(tdPetEffectDue=lambda now,deadline:now+.0001>=deadline,skill=skill,stage=0,createdAt=0.,nextAt=.75 if skill==33 else (0. if skill==21 else 1.),
                     expiresAt=4.,center=(0.,0.),primary=Unit(100),
                     primaryValid=lambda:True,visualPoint=lambda *args:None,visualRing=lambda *args:None,
                     TD_PET_VFX_SWORD='sword',TD_PET_VFX_GOLD='gold',TD_PET_VFX_BRAND='brand',
                     TD_PET_VFX_METEOR='meteor',TD_PET_VFX_GROUND_FIRE='embers')
            n['vec2']=lambda x,y:(x,y)
            # vec2 is only visual offset: Unit position tuple addition cannot
            # authorize any hit or target; native unit/visuals are explicit stubs.
            n['hitPrimary']=lambda power:events.append((n['clock'],power))
            n['area']=lambda point,radius,power:events.append((n['clock'],power))
            step=compile_body(source('TDPetActivePeriodic'),'TDPetCastContext.stepPeriodic',n,('stage','nextAt'),pyname='step')
            for index in range(81):
                n['clock']=index/20.
                if not step(n['clock']):break
            self.assertEqual(events,want,skill)

    def test_dead_seed_propagates_once_from_snapshot_then_two_weak_ticks(self):
        n=scalar_helpers();hits=[];art=[];points=[]
        class Group(List):
            def enumUnitsInRange(self,point,radius):points.append((point,radius))
        victims=[100,None,None,None];candidates=Group([Unit(i) for i in (201,202,203,204)])
        def remember(target):
            index=n['victimCount'];victims[index]=target;n['victimCount']+=1;return index
        n.update(stage=0,createdAt=0.,nextAt=1.,victimCount=1,primary=100,victims=victims,revisions=[0]*4,candidates=candidates,
            primaryValid=lambda:False,valid=lambda:True,aoeValid=lambda target:True,targetValid=lambda target,revision:True,
            remember=remember,lastPosition=lambda index:(19.,27.),clearVisuals=lambda:None,addVisual=lambda *args:art.append(args),
            visualPoint=lambda *args:None,hitPrimary=lambda power:hits.append(('primary',power)),hit=lambda target,power:hits.append((target,power)),
            TD_PET_VFX_SEED='seed',TD_PET_VFX_POISON='poison')
        seed=compile_body(source('TDPetActivePeriodic'),'TDPetCastContext.seed',n,('stage','nextAt','victimCount'),pyname='seed')
        seed();seed();seed();self.assertEqual(n['stage'],4);self.assertEqual(points,[((19.,27.),240.)]);self.assertEqual(hits,[])
        seed();seed();self.assertEqual(n['stage'],6);self.assertEqual(hits,[(target,.15) for _ in range(2) for target in (201,202,203)])
        self.assertEqual(len(points),1)

if __name__=='__main__':unittest.main()
