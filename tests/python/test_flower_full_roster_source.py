"""Execute actual Wurst skill-25 bodies; group/native/visuals are controlled stubs.
No compiled JASS, native Warcraft or measured-FPS claim.
"""
import subprocess
import unittest
from types import SimpleNamespace
from test_elemental_pet_runtime_source import compile_body, Unit
from VerifyPetManagerSource import source, ROOT

BASE = '38189ec7bc629ef1801563be0b0fb2edf3192527'
PATH = 'wurst/pets/TDPetActivePeriodic.wurst'
BEFORE = '\t\t\t\tif not this.valid()\n\t\t\t\t\tbreak\n\t\t\t\tthis.candidates.enumUnitsInRange(this.road.pointAt(flower), 100.0)'
AFTER = BEFORE.replace('if not this.valid()', 'if not this.valid() or this.victimCount >= 12')


def historical(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT, text=True)


def replay(text, scenario, cancel_at=None, cancel_hit=None):
    hits, contacts, visits, finished, enumerations, clocks = [], [], [], [], [], []
    state = dict(now=0., cancelled=False)
    n = dict(skill=25, stage=0, createdAt=0., nextAt=0., expiresAt=4.,
             victimCount=0, victims={}, revisions={}, targetPositions={},
             valid=lambda: not state['cancelled'],
             tdPetEffectDue=lambda now, deadline: now + .0001 >= deadline,
             road=SimpleNamespace(pointAt=lambda index: index),
             revisionFor=lambda target: 1, setLastPosition=lambda *args: None,
             tdPetCaptureEffectTarget=lambda *args: object(),
             aoeValid=lambda target: target not in scenario(state['now'], 'invalid'),
             visualFlowerContact=lambda flower: contacts.append((state['now'], flower)),
             visualTick=lambda now: visits.append(now), visualFinish=lambda: finished.append(state['now']),
             pet=1, host=2, generation=3, damageBase=100.)

    class Candidates(list):
        def enumUnitsInRange(self, point, radius):
            assert radius == 100.
            enumerations.append((state['now'], point))
            self[:] = [Unit(target) for target in scenario(state['now'], point)]
    n['candidates'] = Candidates()

    def damage(pet, host, generation, target, amount):
        hits.append((state['now'], target, amount, pet, host, generation))
        if cancel_hit is not None and len(hits) == cancel_hit:
            state['cancelled'] = True
    n['tdPetSpellDamage'] = damage
    context = source('TDPetCastContext')
    for name in ('victimIndex', 'remember', 'hit'):
        compile_body(context, name, n, ('victimCount',))
    compile_body(text, 'TDPetCastContext.stepPeriodic', n, ('stage', 'nextAt', 'victimCount'), 'stepPeriodic')
    # Only declaration syntax is adapted; the complete actual dispatch body runs.
    runtime = source('TDPetActiveRuntime').replace('override function runEffect', 'function runEffect')
    runtime = runtime.replace('\t\tboolean continuing\n', '\t\tlet continuing = false\n')
    run = compile_body(runtime, 'runEffect', n)
    for tick in range(82):
        state['now'] = tick / 20.
        if cancel_at is not None and state['now'] >= cancel_at:
            state['cancelled'] = True
        continuing = run(state['now'])
        clocks.append((state['now'], continuing, n['stage'], n['nextAt'], n['victimCount']))
        if not continuing:
            break
    return dict(hits=hits, contacts=contacts, visits=visits, finished=finished,
                clocks=clocks, victims=n['victims'], enumerations=enumerations)


def scenario(kind):
    def targets(now, point):
        if point == 'invalid':
            return list(range(1, 13)) if kind == 'dead_or_left' and now >= .25 else []
        if kind == 'never_full':
            return [2 * point + 1, 2 * point + 2]
        if kind in ('first_full', 'dead_or_left'):
            if kind == 'dead_or_left' and now >= .25:
                return [13, 14, 15]
            return list(range(1, 13)) if point == 0 else []
        if kind == 'one_by_one':
            return [min(int(now * 4 + .0001), 11) + 1] if point == 0 else []
        if kind == 'gradually_full':
            pulse = min(int(now * 4 + .0001), 3)
            return list(range(pulse * 3 + 1, pulse * 3 + 4)) if point == 0 else []
        raise AssertionError(kind)
    return targets


class FlowerFullRosterSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = historical(PATH)
        cls.after = source('TDPetActivePeriodic')

    def equal_trace(self, kind, enums, **kwargs):
        old = replay(self.before, scenario(kind), **kwargs)
        new = replay(self.after, scenario(kind), **kwargs)
        self.assertEqual(len(new['enumerations']), enums)
        self.assertLessEqual(len(new['enumerations']), len(old['enumerations']))
        old_enums = len(old.pop('enumerations'))
        new.pop('enumerations')
        self.assertEqual(new, old, 'Hit identity/order/damage, clock, visual and completion trace changed')
        return old_enums, new

    def test_one_guard_is_the_entire_production_change(self):
        self.assertEqual(self.before.count(BEFORE), 1)
        self.assertEqual(self.after, self.before.replace(BEFORE, AFTER, 1))
        # Lifecycle, visual dispatch, CD/fence/source and scheduler remain verbatim.
        for name in ('TDPetCastContext', 'TDPetActiveRuntime', 'TDPetActiveVisuals',
                     'TDPetCombat', 'TDPetEffectScheduler', 'TDPetAttackQueue'):
            self.assertEqual(source(name), historical('wurst/pets/' + name + '.wurst'))
        self.assertNotIn('random', AFTER.lower())

    def test_never_full_preserves_all_48_enumerations(self):
        count, result = self.equal_trace('never_full', 48)
        self.assertEqual(count, 48)
        self.assertEqual(len(result['hits']), 6)
        self.assertEqual(result['clocks'][-1], (4., False, 16, 4., 6))
        self.assertEqual(result['finished'], [4.])

    def test_first_flower_full_reduces_48_to_one_without_early_finish(self):
        count, result = self.equal_trace('first_full', 1)
        self.assertEqual(count, 48)
        self.assertEqual(len(result['hits']), 12)
        self.assertEqual(result['clocks'][-1], (4., False, 16, 4., 12))
        self.assertEqual(len(result['visits']), 81)
        self.assertEqual(result['finished'], [4.])

    def test_gradual_full_reduces_48_to_ten(self):
        count, result = self.equal_trace('gradually_full', 10)
        self.assertEqual(count, 48)
        self.assertEqual([hit[1] for hit in result['hits']], list(range(1, 13)))

    def test_dead_or_left_targets_do_not_reopen_unique_roster(self):
        count, result = self.equal_trace('dead_or_left', 1)
        self.assertEqual(count, 48)
        self.assertEqual(set(result['victims'].values()), set(range(1, 13)))
        self.assertFalse(any(hit[1] >= 13 for hit in result['hits']))

    def test_cancel_before_start_after_full_and_during_damage(self):
        self.equal_trace('first_full', 0, cancel_at=0.)
        self.equal_trace('first_full', 1, cancel_at=.30)
        _, result = self.equal_trace('first_full', 1, cancel_hit=5)
        self.assertEqual(len(result['hits']), 5)
        self.assertEqual(result['clocks'][-1][0], .05)
        self.assertEqual(result['finished'], [])

    def test_cap_11_and_early_finish_mutations_change_actual_trace(self):
        expected = replay(self.after, scenario('first_full'))
        threshold = self.after.replace('or this.victimCount >= 12', 'or this.victimCount >= 11', 1)
        # Twelve targets in one native enumeration still finish that group;
        # use gradual arrival to expose an erroneously shortened roster.
        self.assertNotEqual(replay(threshold, scenario('one_by_one')),
                            replay(self.after, scenario('one_by_one')))
        early = self.after.replace('if not this.valid() or this.victimCount >= 12\n\t\t\t\t\tbreak',
                                  'if not this.valid() or this.victimCount >= 12\n\t\t\t\t\treturn false', 1)
        self.assertNotEqual(replay(early, scenario('first_full'))['clocks'], expected['clocks'])
        self.assertEqual(replay(early, scenario('first_full'))['finished'], [0.])

    def test_removed_guard_restores_wasted_enum_work(self):
        removed = self.after.replace(AFTER, BEFORE, 1)
        self.assertEqual(len(replay(removed, scenario('first_full'))['enumerations']), 48)
        self.assertEqual(len(replay(self.after, scenario('first_full'))['enumerations']), 1)


if __name__ == '__main__':
    unittest.main()
