#!/usr/bin/env python3
"""Narrow source fences for the approved all22 cosmetic ownership extension."""
from pathlib import Path
import argparse, hashlib, json, subprocess
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources, uncomment
from VerifyElementalVfxSource import assets
from VerifyEquipmentAbilityArtifact import require

ROOT = Path(__file__).resolve().parents[1]
BASE = '4567e0dd7a1decb80ea78269b57eec5c95bbab7a'
VISUAL = 'pets/TDPetActiveVisuals.wurst'
DATA = 'pets/TDPetActiveVisualData.wurst'
OWNER = 'visuals/TDCombatVisualRuntime.wurst'
CONTEXT = 'pets/TDPetCastContext.wurst'


def verify(sources, baseline):
    # Exact named cosmetic replacement allowance. No gameplay statement or
    # target loop is discarded to normalize the production mechanics.
    for path in ('pets/TDPetActiveDirect.wurst', 'pets/TDPetActivePeriodic.wurst', 'pets/TDPetActiveRuntime.wurst'):
        expected = baseline[path]
        if path.endswith('Periodic.wurst'):
            expected = expected.replace('\t\tthis.clearVisuals()\n\t\tthis.addVisual(TD_PET_VFX_SEED, point)',
                                        '\t\tthis.visualSeedSpread(point)')
        if path.endswith('Runtime.wurst'):
            expected = expected.replace('this.visualFinish()', 'this.visualFinish(now)')
        require(sources[path] == expected, 'Unnamed combat/clock/target change: '+path)
    e = SourceScalarEvaluator(sources)
    call = lambda name, *args: e.call(name, list(args))
    require('public constant real TD_PET_VISUAL_TERMINAL_DWELL = 0.25' in sources[DATA], 'Terminal dwell is not exactly .25')
    cases = 0
    for skill in (11, 12, *range(19, 39), -1, 99):
        for stage in range(8):
            for marks in (0, 1, 3, 4):
                for now, expiry, pulse in ((4.,4.,4.), (3.9,4.,3.9), (4.,4.,3.5)):
                    expected = (skill in (21,22,31,33) and stage==4) or (skill==24 and stage==6) or (skill==34 and marks>0 and stage==marks) or (skill==30 and stage>0 and now>=expiry and pulse==now) or (skill==38 and stage==4 and now>=expiry)
                    require(call('tdPetVisualTerminal', skill, stage, marks, now, expiry, pulse)==expected,
                            'Terminal whitelist accepted an abort/stale pulse '+str((skill,stage,marks,now,expiry,pulse)))
                    cases += 1
    owner = uncomment(sources[OWNER])
    require(owner.count('doPeriodically(')==1 and 'doAfter(' not in owner, 'Retention added another timer')
    for name, following in (('tdCombatVisualAdoptPetPoint', 'tdCombatVisualRetainPetLines'),
                            ('tdCombatVisualRetainPetLines', 'tdCombatVisualCreateLine')):
        body = owner[owner.index('public function '+name):owner.index('public function '+following)]
        require(all(token not in body for token in ('tdCombatVisualAcquireCast(', 'AddSpecialEffect(', 'AddLightningEx(', 'CreateUnit(', 'GetRandom')),
                'Adoption allocated new art/admission')
    require('owner.detachedCount == 0' in owner and 'owner.serial == ownerSerial' in owner and
            'owner.petSerial == petSerial' in owner and 'tdTrialContextValid(trial)' in owner,
            'Detached owner lost immutable source/trial identity or retention count')
    buff = owner[owner.index('public function tdCombatVisualStartPetBuff'):owner.index('public function tdCombatVisualHit(')]
    require(buff.index('owner.petBuff = art') < buff.index('addHitArt('), 'Optional burst precedes persistent buff ownership')
    context = uncomment(sources[CONTEXT])
    require('return visualCount + tdCombatVisualRetainedPetPointCount()' in context, 'Public live-point count hides retained ownership')
    require('if not visualLinesDetached\n\t\t\ttdCombatVisualClearLines(visualSerial)' in context,
            'Context destruction kills successfully detached final lines')
    finish = uncomment(sources[VISUAL]).split('public function TDPetCastContext.visualFinish',1)[1]
    require('this.valid() and tdPetVisualTerminal(' in finish and 'this.retainVisuals(now + TD_PET_VISUAL_TERMINAL_DWELL)' in finish and
            all(token not in finish for token in ('addVisual(', 'clearVisuals(', 'addMoving(')),
            'Completion retained invalid identity or created replacement art')
    return {'terminalScalarCases': cases, 'exactMechanicsFences': 3, 'timers': 1,
            'assetProof': assets(), 'scope': __doc__}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-commit', default=BASE)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    sources = read_sources(ROOT)
    paths = ('pets/TDPetActiveDirect.wurst','pets/TDPetActivePeriodic.wurst','pets/TDPetActiveRuntime.wurst')
    baseline = {path:subprocess.check_output(['git','show',a.baseline_commit+':wurst/'+path],cwd=ROOT,text=True) for path in paths}
    result = verify(sources, baseline)
    result['baselineCommit'] = a.baseline_commit
    rejects = []
    mutations = ((DATA,'TD_PET_VISUAL_TERMINAL_DWELL = 0.25','TD_PET_VISUAL_TERMINAL_DWELL = 0.0'),
                 (DATA,'return stage == 4','return stage >= 3'),
                 (OWNER,'owner.serial == ownerSerial','owner.serial != ownerSerial'),
                 (CONTEXT,'return visualCount + tdCombatVisualRetainedPetPointCount()','return visualCount'),
                 ('pets/TDPetActivePeriodic.wurst','this.hitPrimary(0.35)','this.hitPrimary(0.36)'))
    for path, before, after in mutations:
        changed=dict(sources)
        require(before in changed[path], 'Missing source mutation anchor '+before)
        changed[path]=changed[path].replace(before,after)
        try: verify(changed, baseline)
        except (AssertionError,ValueError): rejects.append(before)
        else: raise ValueError('Source mutation escaped '+before)
    result['mutationRejections']=rejects
    result['sourceSHA256']={path:hashlib.sha256(sources[path].encode()).hexdigest() for path in (VISUAL,DATA,OWNER,CONTEXT,*paths)}
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
