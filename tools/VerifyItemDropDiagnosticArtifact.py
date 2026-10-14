"""Execute packaged drop-observer lifecycle using bounded native fixtures.

No retail cursor/drop timing or native placement algorithm is emulated. The
actual map JASS supplies diagnostic guards, state, callbacks and placement hooks.
Only handles/timers, coordinates/pathing, UI, and equipment classification are
fixtures. Timer callbacks are explicitly dispatched under controlled interleavings.
"""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re

from GenerateTowerTerrainMask import Mpq
from VerifyBossSpellResistanceArtifact import BossJassRuntime
from VerifyTowerUpgradeArtifact import JassScalarEvaluator

P = 'TDItemDropDiagnostic_'


def check(ok, message):
    if not ok:
        raise AssertionError(message)


class DropRuntime(BossJassRuntime):
    def __init__(self, script):
        JassScalarEvaluator.__init__(self, script)
        self.globals = {}
        declarations = script.split('globals\n', 1)[1].split('endglobals', 1)[0]
        for kind, array, name in re.findall(r'^(\w+) (array )?(\w+)', declarations, re.M):
            default = False if kind == 'boolean' else 0.0 if kind == 'real' else 0 if kind == 'integer' else None
            self.globals[name] = defaultdict(lambda value=default: value) if array else default
        self.globals.update(self.constants)
        for name, literal in re.findall(r'^\s*set (\w+) =\s*([+-]?\s*\d+(?:\.\d*)?)\s*$', script, re.M):
            if re.fullmatch(r'\w+_[A-Z][A-Z0-9_]*', name):
                literal = literal.replace(' ', '')
                self.globals[name] = float(literal) if '.' in literal else int(literal)
        for callback in ('tdDropTraceNext', 'tdDropTraceExpire'):
            self.globals['ref_function_' + callback] = callback
        self.globals['PATHING_TYPE_WALKABILITY'] = 1
        for lane in range(4):
            self.globals['TDState_tdLaneActive'][lane] = True
        self.execution_depth = self.executed_steps = 0
        self.calls = Counter()
        self.now = 50.0
        self.player = 0
        self.expired = None
        self.serial = 20000
        self.timers = {}
        self.destroyed = []
        self.messages = []
        self.moves = []
        self.units = {101: dict(owner=0, name='塔', x=-2000., y=1800.),
                      102: dict(owner=1, name='农民', x=2000., y=1800.)}
        self.items = {1001: dict(id=1, owned=True, x=-2000., y=1800.),
                      1002: dict(id=1, owned=True, x=2000., y=1800.)}

    def native(self, name, args):
        if name == 'tdItemIsEquipment': return True, args[0] == 1  # Catalog boundary only.
        if name in ('GetPlayerId', 'Player', 'GetHandleId'): return True, args[0]
        if name == 'GetTriggerPlayer': return True, self.player
        if name == 'GetOwningPlayer': return True, self.units[args[0]]['owner']
        if name in ('GetUnitName', 'GetUnitX', 'GetUnitY'):
            return True, self.units[args[0]][{'GetUnitName':'name','GetUnitX':'x','GetUnitY':'y'}[name]]
        if name in ('GetItemTypeId', 'GetItemX', 'GetItemY', 'IsItemOwned'):
            return True, self.items.get(args[0], {}).get({'GetItemTypeId':'id','GetItemX':'x','GetItemY':'y','IsItemOwned':'owned'}[name], 0)
        if name == 'SetItemPosition':
            self.moves.append(tuple(args)); self.items[args[0]].update(x=args[1], y=args[2]); return True, None
        if name == 'GetTerrainCliffLevel': return True, 1 if args[1] >= 1600 else 0
        if name == 'IsTerrainPathable': return True, False
        if name == 'TimerGetElapsed': return True, self.now
        if name == 'CreateTimer':
            self.serial += 1; self.timers[self.serial] = {}; return True, self.serial
        if name == 'DestroyTimer':
            self.destroyed.append(args[0]); self.timers.pop(args[0], None); return True, None
        if name == 'TimerStart':
            check(args[0] in self.timers, 'Starting unknown timer')
            self.timers[args[0]] = dict(delay=args[1], periodic=args[2], callback=args[3]); return True, None
        if name == 'GetExpiredTimer': return True, self.expired
        if name == 'DisplayTimedTextToPlayer': self.messages.append((args[0], args[-1])); return True, None
        if name == 'I2S': return True, str(int(args[0]))
        if name == 'R2I': return True, int(args[0])
        if name == 'SubString': return True, args[0][args[1]:args[2]]
        if name == 'ModuloInteger': return True, args[0] % args[1]
        if name not in self.functions: raise AssertionError('Unmodelled native: ' + name)
        return False, None

    def toggle(self, lane=0):
        self.player = lane; self.invoke('tdDropTraceChat')

    def drop(self, carrier=101, item=1001):
        self.invoke('tdItemDropDiagnosticDropped', carrier, item)

    def fire(self, timer, stale_callback=None):
        callback = stale_callback or self.timers[timer]['callback']
        self.expired = timer; self.invoke(callback)

    def watched(self, lane=0): return self.globals[P+'tdDropTraceItem'][lane]
    def next_timer(self, lane=0): return self.globals[P+'tdDropTraceNextTimer'][lane]


def run(script):
    passed = []
    r = DropRuntime(script); r.drop()
    check(not r.timers and not r.messages and r.watched() is None, 'Default-off drop created state/timers/output')
    passed.append('default_off_no_timers')
    r.toggle(); r.messages.clear(); r.drop(102,1002)
    check(not r.timers and not r.messages, 'Other player drop observed without opt-in')
    r.drop(); check(len(r.timers)==2 and all(not t['periodic'] for t in r.timers.values()), 'Expected two one-shot timers')
    check(sorted(t['delay'] for t in r.timers.values())==[0.0,10.0], 'Observation/expiry timer delays changed')
    check(all(p==0 for p,_ in r.messages), 'Output recipient mismatch')
    check(any('事件时(非最终)' in m and '(-2000,1800)' in m and '目标未知' in m for _,m in r.messages), 'Wrong event observation')
    r.items[1001].update(owned=False,x=-2500.,y=1400.)
    r.fire(r.next_timer())
    check('下一帧' in r.messages[-1][1] and '(-2500,1400)' in r.messages[-1][1] and '目标未知' in r.messages[-1][1], 'Deferred observation not actual post-drop position')
    check('坑道掩码=路1' in r.messages[-1][1] and 'WPM=' not in r.messages[-1][1], 'Mask report missing or invented WPM')
    passed.append('per_player_event_and_next_frame_actual_unknown_target')
    # Repeat with farmer owned by enabled player, rather than assuming tower-only.
    r.units[101]['name']='农民'; r.drop(); check('农民' in r.messages[-2][1], 'Farmer drop omitted')
    passed.append('tower_and_farmer_carriers')
    for cause in ('off','pickup','invalid','owned','leave','game_over','inactive'):
        r=DropRuntime(script);r.toggle();r.drop();timer=r.next_timer();r.items[1001]['owned']=False
        if cause=='off': r.toggle()
        elif cause=='pickup': r.invoke('tdItemDropDiagnosticPickedUp',1001)
        elif cause=='invalid': r.items[1001]['id']=0
        elif cause=='owned': r.items[1001]['owned']=True
        elif cause=='leave': r.player=0;r.invoke('tdDropTraceLeave')
        elif cause=='game_over': r.globals['TDState_tdGameOver']=True
        else:r.globals['TDState_tdLaneActive'][0]=False
        count=len(r.messages);r.fire(timer,'tdDropTraceNext')
        check(len(r.messages)==count and not r.timers and r.watched() is None, 'Cancellation failed: '+cause)
        passed.append('cancel_'+cause+'_and_stale_callback_silent')
    r=DropRuntime(script);r.toggle();r.drop();old=r.next_timer();r.drop(item=1002)
    count=len(r.messages);r.fire(old,'tdDropTraceNext')
    check(r.watched()==1002 and len(r.messages)==count and len(r.timers)==2, 'Superseded drop callback damaged new watch')
    passed.append('new_drop_supersedes_previous_watch')
    r=DropRuntime(script);r.toggle();r.drop();r.items[1001]['owned']=False;r.drop(102,1001)
    check(r.watched() is None and not r.timers, 'Other carrier retained old player watch')
    passed.append('new_carrier_clears_prior_watch_even_if_disabled')
    r=DropRuntime(script);r.toggle();r.drop();r.now+=10;r.fire(r.globals[P+'tdDropTraceExpiryTimer'][0])
    check(not r.timers and r.watched() is None, 'Expiry leaked watch/timers')
    passed.append('ten_second_expiry_cleanup')
    # Execute the actual placement function containing before/native/after hooks.
    outcomes=[]
    for enabled in (False,True):
        r=DropRuntime(script)
        if enabled:r.toggle();r.drop()
        r.items[1001].update(owned=False,x=-2300.,y=1400.)
        r.messages.clear();result=r.invoke('tdRestoreSortedItem',1001,0,-2500.,1400.)
        check(result is True and r.moves==[(1001,-2500.,1400.)], 'Observer altered native move count/request')
        outcomes.append(copy.deepcopy(r.items))
        if enabled:
            check(len(r.messages)==2 and '调用前' in r.messages[0][1] and '(-2300,1400)' in r.messages[0][1] and '调用后' in r.messages[1][1] and '(-2500,1400)' in r.messages[1][1], 'Before/after native coordinates incorrect')
        else:check(not r.messages and not r.timers, 'Disabled placement produced logs/timers')
    check(outcomes[0]==outcomes[1], 'Enabled observer changed item state')
    passed.append('packed_restore_hook_preserves_native_action_and_records_before_after')
    for _ in range(50):r.invoke('tdItemDropDiagnosticMove',1001,'test',True,-2500.,1400.)
    check(r.globals[P+'tdDropTraceMoves'][0]==32 and len(r.messages)==33,'Move log cap not enforced')
    passed.append('bounded_move_log_count')
    return passed


def mutation_guards(script):
    mutants = [
        ('disabled_drop_gate', 'tdItemDropDiagnosticDropped', '( not TDItemDropDiagnostic_tdDropTraceEnabled[lane_3])', 'false'),
        ('pickup_cleanup', 'tdItemDropDiagnosticPickedUp', 'call tdDropTraceClear(lane_3)', '// deliberately removed cleanup'),
        ('next_frame_unknown_target', 'tdDropTraceNext', '目标未知', '目标已知'),
        ('restore_before_log', 'tdRestoreSortedItem', 'call tdItemDropDiagnosticMove(itm, "整理归位", true, original_x, original_y)', '// deliberately removed before log'),
    ]
    rejected = []
    for label, function, old, new in mutants:
        start = script.index('function ' + function + ' ')
        end = script.index('endfunction', start)
        body = script[start:end]
        check(body.count(old) == 1, 'Mutation anchor changed: ' + label)
        mutant = script[:start] + body.replace(old, new) + script[end:]
        try:
            run(mutant)
        except AssertionError:
            rejected.append(label)
        else:
            raise AssertionError('Tests accepted mutation: ' + label)
    return rejected


def main():
    parser=argparse.ArgumentParser();parser.add_argument('map',type=Path);args=parser.parse_args()
    data=args.map.read_bytes();script=Mpq(data).extract('war3map.j').decode()
    passed=run(script)
    print(json.dumps({'status':'PASS','map':str(args.map.resolve()),'mapSHA256':hashlib.sha256(data).hexdigest(),'scenarios':passed,'rejectedMutations':mutation_guards(script),
      'limits':['Native coordinates/pathing/cliff levels and callback dispatch are controlled fixtures, not Warcraft 1.27a tests.','Equipment classification is a narrow fixture; diagnostic/terrain-mask/lifecycle logic executes from actual packaged JASS.','Ground restore hook executes; other movement sites are covered by source observer-only guards, not full gameplay execution.','No cursor/drop intended position is available or inferred.']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
