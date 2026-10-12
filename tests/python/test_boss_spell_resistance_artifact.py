"""Boss resistance verifier regressions and optional final-MPQ integration.

The independent fixture extends the repository's packaged baseline JASS with
explicit test-only resistance functions. It tests the validator, not a new map.
Set BOSS_RESISTANCE_MAP to execute final artifacts. Baselines are read from the
fixed Git commit by default; BOSS_RESISTANCE_BASELINE and
BOSS_RESISTANCE_BASELINE_SOURCE can explicitly override map/source paths.
Without a newly built map those integration tests are explicitly skipped.
"""
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import shutil
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyTowerUpgradeArtifact import function_body
import VerifyBossSpellResistanceArtifact as verifier

BASELINE_COMMIT = '0330fd12de4d66c4a1ca4980e10b771f0903fbfc'
BASELINE_MAP_SHA256 = '10a6eb992b4a9fb0edf2aa81db8700e5b78042462e5d5a130b71a2747907bb0f'
BASELINE_SOURCE_SHA256 = '6f03a91f98a34c436b500b25b2bcfc50d668accb23a13390e9288c7544ad26d7'


def source_digest(root):
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob('*.wurst')):
        verifier.require(not path.is_symlink(), 'Baseline source cannot contain symlinks')
        digest.update(path.relative_to(root).as_posix().encode('utf-8'))
        digest.update(b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


class BaselineFixture:
    """Pinned read-only Git inputs, materialized only in TemporaryDirectory."""
    def __init__(self, repository=ROOT, environment=None, git_reader=None):
        environment = os.environ if environment is None else environment
        self.directory = tempfile.TemporaryDirectory(prefix='boss-resistance-baseline-')
        self.root = Path(self.directory.name)
        self.map, self.source = self.root / 'ExampleMap.w3x', self.root / 'wurst'
        read_git = git_reader or (lambda args: subprocess.check_output(
            ['git', *args], cwd=repository, stderr=subprocess.PIPE))
        try:
            map_override = environment.get('BOSS_RESISTANCE_BASELINE')
            data = Path(map_override).read_bytes() if map_override else read_git(
                ['show', BASELINE_COMMIT + ':ExampleMap.w3x'])
            verifier.require(hashlib.sha256(data).hexdigest() == BASELINE_MAP_SHA256,
                             'Pinned baseline map SHA-256 mismatch')
            self.map.write_bytes(data)
            source_override = environment.get('BOSS_RESISTANCE_BASELINE_SOURCE')
            if source_override:
                original = Path(source_override)
                verifier.require(original.is_dir() and not original.is_symlink(), 'Invalid baseline source directory')
                self.source.mkdir()
                for path in original.rglob('*'):
                    verifier.require(not path.is_symlink(), 'Baseline source cannot contain symlinks')
                    if path.is_file() and path.suffix == '.wurst':
                        target = self.source / path.relative_to(original)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(path.read_bytes())
            else:
                archive = read_git(['archive', BASELINE_COMMIT, 'wurst'])
                with tarfile.open(fileobj=io.BytesIO(archive)) as entries:
                    for entry in entries:
                        relative = Path(entry.name)
                        verifier.require(not relative.is_absolute() and '..' not in relative.parts and
                                         relative.parts[0] == 'wurst' and (entry.isfile() or entry.isdir()),
                                         'Unsafe baseline Git archive entry')
                        target = self.root / relative
                        if entry.isdir():
                            target.mkdir(parents=True, exist_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_bytes(entries.extractfile(entry).read())
            verifier.require(source_digest(self.source) == BASELINE_SOURCE_SHA256,
                             'Pinned baseline source SHA-256 mismatch')
        except (subprocess.CalledProcessError, FileNotFoundError) as error:
            self.close()
            raise unittest.SkipTest('Baseline inputs unavailable. Fetch Git history containing ' +
                                    BASELINE_COMMIT + ' or set BOSS_RESISTANCE_BASELINE and '
                                    'BOSS_RESISTANCE_BASELINE_SOURCE to the pinned pre-fix inputs.') from error
        except Exception:
            self.close()
            raise

    def close(self): self.directory.cleanup()
    def __enter__(self): return self
    def __exit__(self, *_): self.close()


_baseline = None


def baseline_fixture():
    global _baseline
    if _baseline is None:
        _baseline = BaselineFixture()
    return _baseline


def replace_body(script, name, body):
    match = re.search(r'^function ' + re.escape(name) + r' takes[^\n]*\n(.*?)^endfunction', script, re.M | re.S)
    if match is None: raise ValueError('Missing mutation function ' + name)
    return script[:match.start(1)] + body + script[match.end(1):]


def fixture_script():
    """Test-only generated-function stand-ins; dependency engine remains real."""
    baseline = baseline_fixture().map
    script = Mpq(baseline.read_bytes()).extract('war3map.j').decode('utf-8')
    if 'function tdEnemyMechanicScaleSpellDamage takes' in script:
        raise ValueError('Synthetic fixture requires the unchanged pre-fix map')
    script = script.replace('endglobals', 'boolean ' + verifier.ONCE + '=false\nboolean array DamageInstance_unreduced\nendglobals', 1)
    ctor = function_body(script, 'construct_DamageInstance')
    script = replace_body(script, 'construct_DamageInstance', ctor + '\tset DamageInstance_unreduced[this_1] = true\n')
    setup = '''\tlocal integer clVar
\tif MagicFunctions_compiletime then
\t\treturn
\tendif
\tset TDEnemyMechanicRuntime_tdEnemyMechanicsReady = true
\tif not TDEnemyMechanicRuntime_tdEnemySpellResistanceListenerReady then
\t\tset TDEnemyMechanicRuntime_tdEnemySpellResistanceListenerReady = true
\t\tset clVar = alloc_DamageListener_addUnreducedListener_TDEnemyMechanicRuntime("test fixture")
\t\tcall construct_DamageListener(clVar)
\t\tcall DamageEvent_addUnreducedListener(2, clVar)
\tendif
'''
    script = replace_body(script, 'tdSetupEnemyMechanics', setup)
    alloc = function_body(script, 'alloc_DamageListener_addUnreducedListener_TDDamageRuntime')
    alloc = alloc.replace('692', '999')
    dispatcher = function_body(script, 'dispatch_DamageListener_DamageListener_onEvent')
    script = replace_body(script, 'dispatch_DamageListener_DamageListener_onEvent',
                         '\tif DamageListener_typeId[this_1] == 999 then\n\t\tcall tdEnemyMechanicScaleNativeSpellDamage()\n\t\treturn\n\tendif\n' + dispatcher)
    script += '''
function tdWaveBossSpellDamageTakenFactor takes integer wave returns real
    if wave == 32 then
        return 0.58
    elseif wave == 24 then
        return 0.68
    elseif wave == 16 then
        return 0.82
    endif
    return 1.00
endfunction
function TDEnemyMechanicState_scaledSpellAmount takes integer this_1, real amount returns real
    if not TDEnemyMechanicState_active[this_1] or TDEnemyMechanicState_role[this_1] != TDEnemyMechanicData_TD_ENEMY_ROLE_BOSS or not tdEnemyGuardArmorEnabled(TDEnemyGuardLink_wave[TDEnemyMechanicState_link[this_1]]) or amount <= 0.0 then
        return amount
    endif
    return amount * tdWaveBossSpellDamageTakenFactor(TDEnemyGuardLink_wave[TDEnemyMechanicState_link[this_1]])
endfunction
function tdEnemyMechanicScaleSpellDamage takes unit target, real amount returns real
    local integer record
    if not TDEnemyMechanicRuntime_tdEnemyMechanicsReady or amount <= 0.0 then
        return amount
    endif
    set record = tdEnemyMechanicRecordFor(target, "test fixture")
    if record == 0 or not tdEnemyMechanicRecordValid(record, "test fixture") then
        return amount
    endif
    return TDEnemyMechanicState_scaledSpellAmount(TDEnemyMechanicRecord_state[record], amount)
endfunction
function tdEnemyMechanicNativeSpellEligible takes boolean spellDamage, boolean codeDamage returns boolean
    return spellDamage and not codeDamage
endfunction
function DamageInstance_setAmount takes integer this_1, real amount returns nothing
    set DamageInstance_amount[this_1] = amount
    if DamageInstance_unreduced[this_1] then
        set DamageInstance_unreducedAmount[this_1] = amount
    endif
endfunction
function DamageEvent_setAmount takes real amount returns nothing
    call DamageInstance_setAmount(DamageInstance_current, amount)
endfunction
function tdEnemyMechanicScaleNativeSpellDamage takes nothing returns nothing
    if not TDEnemyMechanicRuntime_tdEnemyMechanicsReady or not tdEnemyMechanicNativeSpellEligible(DamageEvent_isSpell(), DamageEvent_isCode()) then
        return
    endif
    call DamageEvent_setAmount(tdEnemyMechanicScaleSpellDamage(DamageEvent_getTarget(), DamageEvent_getAmount()))
endfunction
function spellDamage takes integer pet_2, unit host_1, integer generation_3, unit target_3, real amount_2 returns nothing
    call damage(pet_2, host_1, generation_3, target_3, tdEnemyMechanicScaleSpellDamage(target_3, amount_2))
endfunction
'''
    script += 'function alloc_DamageListener_addUnreducedListener_TDEnemyMechanicRuntime takes string w__wurst_stackPos returns integer\n' + alloc + 'endfunction\n'
    # Mutate only the fixture's selected submitted amounts and pet spell routes.
    for name, old, new in [
        ('tdPulseOrcBladestorm', 'victim_1, damagePerTick)', 'victim_1, tdEnemyMechanicScaleSpellDamage(victim_1, damagePerTick))'),
        ('call_doAfter_TDEquipmentCombat_1', 'target_1[this_1], amount[this_1])', 'target_1[this_1], tdEnemyMechanicScaleSpellDamage(target_1[this_1], amount[this_1]))'),
        ('call_doPeriodicallyCounted_TDPetCombat', 'call damage(', 'call spellDamage('),
        ('resolveActive', 'call damage(', 'call spellDamage('),
    ]:
        script = replace_body(script, name, function_body(script, name).replace(old, new))
    body = function_body(script, 'tdHandleGhoulCorpseExplosionDamage')
    body = body.replace('victim_1, tdGhoulCorpseExplosionDamageForBranch(',
                        'victim_1, tdEnemyMechanicScaleSpellDamage(victim_1, tdGhoulCorpseExplosionDamageForBranch(')
    body = body.replace('line 487")))', 'line 487"))))')
    script = replace_body(script, 'tdHandleGhoulCorpseExplosionDamage', body)
    return script


@contextmanager
def formal_boss_source():
    """Keep the original strict Boss-only source delta on its formal snapshot."""
    with tempfile.TemporaryDirectory(prefix='formal-boss-source-') as name:
        root = Path(name)
        archive = subprocess.check_output(['git', 'archive',
            '0384ccddcfdbaa868f773573c1f7403fe809d3e2', 'wurst'], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as entries:
            for entry in entries:
                relative = Path(entry.name)
                verifier.require(not relative.is_absolute() and '..' not in relative.parts and
                                 relative.parts[0] == 'wurst' and (entry.isfile() or entry.isdir()),
                                 'Unsafe formal Boss source archive entry')
                target = root / relative
                if entry.isdir(): target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(entries.extractfile(entry).read())
        verifier.require(source_digest(root / 'wurst') ==
            'e17e5a8f6a99003c9ac1979e4b8b7807f084fc3a98b3544bd0e6f329d34c7994',
            'Pinned formal Boss source SHA-256 mismatch')
        yield root / 'wurst'


class BossResistanceVerifierUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.script = fixture_script()

    def test_fixture_executes_state_runtime_and_all_invalid_guards(self):
        self.assertEqual(verifier.verify_pure_and_runtime(self.script), 2160)

    def test_fixture_executes_real_dependency_classification_hp_and_accounting(self):
        self.assertEqual(verifier.verify_engine_and_accounting(self.script), 48)

    def test_zero_actual_engine_event_does_not_capture_or_contaminate_next_hit(self):
        self.assertEqual(verifier.verify_zero_engine_event(self.script), 2)

    def test_fixture_executes_setup_shutdown_setup_and_unregistration(self):
        verifier.verify_setup_lifecycle(self.script)

    def test_fixture_executes_all_tagged_spell_and_derived_paths(self):
        results = verifier.verify_scripted_damage(self.script)
        self.assertEqual(results['pet active 13'], 43.5)
        self.assertEqual(results['pet derived attack'], 75.0)
        self.assertEqual(len(results), 11)

    def test_wrong_factor_is_rejected_by_independent_published_oracle(self):
        body = function_body(self.script, 'tdWaveBossSpellDamageTakenFactor')
        bad = replace_body(self.script, 'tdWaveBossSpellDamageTakenFactor', body.replace('0.58', '0.60'))
        with self.assertRaisesRegex(ValueError, 'state helper'):
            verifier.verify_pure_and_runtime(bad)

    def test_invalid_wave_guard_removal_is_rejected(self):
        body = function_body(self.script, 'TDEnemyMechanicState_scaledSpellAmount')
        bad = body.replace('not tdEnemyGuardArmorEnabled(TDEnemyGuardLink_wave[TDEnemyMechanicState_link[this_1]]) or ', '')
        self.assertNotEqual(body, bad)
        # A missing guard is observable when an invalid wave's factor changes.
        script = replace_body(self.script, 'TDEnemyMechanicState_scaledSpellAmount', bad)
        factor = function_body(script, 'tdWaveBossSpellDamageTakenFactor')
        factor = factor.replace('return 1.00', 'if wave == 31 then\n return 0.50\n endif\n return 1.00')
        with self.assertRaises(ValueError):
            verifier.verify_pure_and_runtime(replace_body(script, 'tdWaveBossSpellDamageTakenFactor', factor))

    def test_each_pure_guard_removal_is_rejected(self):
        body = function_body(self.script, 'TDEnemyMechanicState_scaledSpellAmount')
        for condition in ('not TDEnemyMechanicState_active[this_1] or ',
                          'TDEnemyMechanicState_role[this_1] != TDEnemyMechanicData_TD_ENEMY_ROLE_BOSS or ',
                          ' or amount <= 0.0'):
            with self.subTest(guard=condition):
                bad = replace_body(self.script, 'TDEnemyMechanicState_scaledSpellAmount', body.replace(condition, ''))
                with self.assertRaisesRegex(ValueError, 'state helper'):
                    verifier.verify_pure_and_runtime(bad)

    def test_native_code_damage_misclassification_is_rejected(self):
        bad = replace_body(self.script, 'tdEnemyMechanicNativeSpellEligible', 'return spellDamage\n')
        with self.assertRaisesRegex(ValueError, 'truth table'):
            verifier.verify_pure_and_runtime(bad)

    def test_actual_engine_code_flag_regression_is_rejected(self):
        body = function_body(self.script, 'DamageEvent_onUnreducedDamage')
        bad = replace_body(self.script, 'DamageEvent_onUnreducedDamage', body.replace('set isCode = true', 'set isCode = false'))
        with self.assertRaisesRegex(ValueError, 'Code flag|amount'):
            verifier.verify_engine_and_accounting(bad)

    def test_early_unreduced_amount_write_is_required(self):
        body = function_body(self.script, 'DamageInstance_setAmount')
        bad = replace_body(self.script, 'DamageInstance_setAmount', body.replace('set DamageInstance_unreducedAmount[this_1] = amount', ''))
        with self.assertRaisesRegex(ValueError, 'unreduced amount'):
            verifier.verify_engine_and_accounting(bad)

    def test_actual_engine_hp_snapshot_must_use_final_amount(self):
        body = function_body(self.script, 'DamageEvent_onUnreducedDamage')
        bad = replace_body(self.script, 'DamageEvent_onUnreducedDamage',
                           re.sub(r'prevLife - DamageInstance_amount\[\w+\]', 'prevLife - amount_2', body))
        with self.assertRaisesRegex(ValueError, 'HP settlement|HP snapshot'):
            verifier.verify_engine_and_accounting(bad)

    def test_reset_once_flag_is_rejected(self):
        body = function_body(self.script, 'tdEnemyMechanicsShutdown')
        bad = replace_body(self.script, 'tdEnemyMechanicsShutdown', body + 'set ' + verifier.ONCE + ' = false\n')
        with self.assertRaisesRegex(ValueError, 'listener flag'):
            verifier.verify_setup_lifecycle(bad)

    def test_duplicate_setup_listener_is_rejected(self):
        body = function_body(self.script, 'tdSetupEnemyMechanics')
        bad = replace_body(self.script, 'tdSetupEnemyMechanics', body.replace('if not ' + verifier.ONCE + ' then', 'if true then'))
        with self.assertRaisesRegex(ValueError, 'duplicated listener'):
            verifier.verify_setup_lifecycle(bad)

    def test_wrong_priority_is_rejected(self):
        body = function_body(self.script, 'tdSetupEnemyMechanics')
        bad = replace_body(self.script, 'tdSetupEnemyMechanics', body.replace('DamageEvent_addUnreducedListener(2,', 'DamageEvent_addUnreducedListener(5,'))
        with self.assertRaisesRegex(ValueError, 'priority-2'):
            verifier.verify_setup_lifecycle(bad)

    def test_compiletime_registration_is_rejected(self):
        body = function_body(self.script, 'tdSetupEnemyMechanics')
        bad = replace_body(self.script, 'tdSetupEnemyMechanics', body.replace('if MagicFunctions_compiletime then', 'if false then'))
        with self.assertRaisesRegex(ValueError, 'Compiletime'):
            verifier.verify_setup_lifecycle(bad)

    def test_double_pet_scaling_is_rejected(self):
        body = function_body(self.script, 'damage')
        bad = replace_body(self.script, 'damage', body.replace('target_3, amount_2)', 'target_3, tdEnemyMechanicScaleSpellDamage(target_3, amount_2))'))
        with self.assertRaisesRegex(ValueError, 'submitted amount|scaling count'):
            verifier.verify_scripted_damage(bad)

    def test_pet_missing_spell_wrapper_is_rejected(self):
        body = function_body(self.script, 'resolveActive')
        bad = replace_body(self.script, 'resolveActive', body.replace('call spellDamage(', 'call damage('))
        with self.assertRaisesRegex(ValueError, 'active skill 13'):
            verifier.verify_scripted_damage(bad)

    def test_original_native_damage_metadata_is_enforced(self):
        body = function_body(self.script, 'unit_damageTarget_1')
        bad = replace_body(self.script, 'unit_damageTarget_1', body.replace('false, false', 'true, true'))
        with self.assertRaisesRegex(ValueError, 'native damage parameters'):
            verifier.verify_scripted_damage(bad)

    def test_each_spell_site_scaler_deletion_is_rejected(self):
        # Each production spell path executes from its compiled body, so a
        # six-call count cannot conceal a missing resistance amount wrapper.
        deletions = [
            ('tdPulseOrcBladestorm', 'tdEnemyMechanicScaleSpellDamage(victim_1, damagePerTick)', 'damagePerTick'),
            ('call_doAfter_TDEquipmentCombat_1', 'tdEnemyMechanicScaleSpellDamage(target_1[this_1], amount[this_1])', 'amount[this_1]'),
            ('call_doPeriodicallyCounted_TDPetCombat', 'call spellDamage(', 'call damage('),
            ('resolveActive', 'call spellDamage(', 'call damage('),
        ]
        for name, old, new in deletions:
            with self.subTest(site=name):
                body = function_body(self.script, name)
                self.assertIn(old, body)
                changed = replace_body(self.script, name, body.replace(old, new))
                with self.assertRaisesRegex(ValueError, 'count/scaling|skill|amount|scaling count|call_do'):
                    verifier.verify_scripted_damage(changed)
        body = function_body(self.script, 'tdHandleGhoulCorpseExplosionDamage')
        changed = body.replace('tdEnemyMechanicScaleSpellDamage(victim_1, tdGhoulCorpseExplosionDamageForBranch(',
                               'tdGhoulCorpseExplosionDamageForBranch(').replace('line 487"))))', 'line 487")))')
        self.assertNotEqual(body, changed)
        with self.assertRaisesRegex(ValueError, 'corpse damage count/scaling'):
            verifier.verify_scripted_damage(replace_body(self.script, 'tdHandleGhoulCorpseExplosionDamage', changed))

    def test_wrongly_scaled_eadd_is_rejected(self):
        body = function_body(self.script, 'call_doAfter_TDEquipmentCombat')
        old = 'target[this_1], additional[this_1])'
        self.assertIn(old, body)
        changed = body.replace(old, 'target[this_1], tdEnemyMechanicScaleSpellDamage(target[this_1], additional[this_1]))')
        with self.assertRaisesRegex(ValueError, 'call_doAfter_TDEquipmentCombat'):
            verifier.verify_scripted_damage(replace_body(self.script, 'call_doAfter_TDEquipmentCombat', changed))

    def test_wrongly_scaled_derived_pdam_is_rejected(self):
        body = function_body(self.script, 'call_doAfter_TDPetCombat')
        self.assertIn('call damage(', body)
        with self.assertRaisesRegex(ValueError, 'call_doAfter_TDPetCombat'):
            verifier.verify_scripted_damage(replace_body(self.script, 'call_doAfter_TDPetCombat',
                                                        body.replace('call damage(', 'call spellDamage(')))

    def test_double_factor_multiply_is_rejected(self):
        body = function_body(self.script, 'TDEnemyMechanicState_scaledSpellAmount')
        changed = re.sub(r'(return amount \* tdWaveBossSpellDamageTakenFactor\([^\n]+\))', r'\1 * 0.58', body)
        self.assertNotEqual(body, changed)
        with self.assertRaisesRegex(ValueError, 'state helper'):
            verifier.verify_pure_and_runtime(replace_body(self.script, 'TDEnemyMechanicState_scaledSpellAmount', changed))

    def test_swapping_early_listener_to_late_is_rejected(self):
        body = function_body(self.script, 'tdSetupEnemyMechanics')
        self.assertIn('DamageEvent_addUnreducedListener(', body)
        with self.assertRaisesRegex(ValueError, 'priority-2'):
            verifier.verify_setup_lifecycle(replace_body(self.script, 'tdSetupEnemyMechanics',
                body.replace('DamageEvent_addUnreducedListener(', 'DamageEvent_addListener(')))

    def test_shutdown_callback_ready_guard_is_required(self):
        body = function_body(self.script, verifier.CALLBACK)
        self.assertIn('not TDEnemyMechanicRuntime_tdEnemyMechanicsReady or ', body)
        with self.assertRaisesRegex(ValueError, 'Shutdown native callback'):
            verifier.verify_pure_and_runtime(replace_body(self.script, verifier.CALLBACK,
                body.replace('not TDEnemyMechanicRuntime_tdEnemyMechanicsReady or ', '')))

    def test_real_unregister_table_removal_is_required(self):
        body = function_body(self.script, 'tdEnemyMechanicRetireRecord')
        changed = '\n'.join(line for line in body.splitlines() if 'dispatch_Table_Table_removeInt(' not in line) + '\n'
        self.assertNotEqual(body, changed)
        with self.assertRaisesRegex(ValueError, 'Shutdown left records'):
            verifier.verify_setup_lifecycle(replace_body(self.script, 'tdEnemyMechanicRetireRecord', changed))

    def test_each_tower_code_marker_removal_is_rejected(self):
        for name in ('tdPulseOrcBladestorm', 'tdHandleGhoulCorpseExplosionDamage'):
            with self.subTest(site=name):
                body = function_body(self.script, name)
                self.assertIn('call DamageEvent_setNextDamageFromCode()', body)
                changed = body.replace('call DamageEvent_setNextDamageFromCode()', '')
                with self.assertRaisesRegex(ValueError, 'code marker/ID'):
                    verifier.verify_scripted_damage(replace_body(self.script, name, changed))

    def test_direct_pet_code_marker_removal_is_rejected(self):
        body = function_body(self.script, 'damage')
        changed = body.replace('call DamageEvent_setNextDamageFromCode()', '')
        with self.assertRaisesRegex(ValueError, 'code marker changed'):
            verifier.verify_scripted_damage(replace_body(self.script, 'damage', changed))

    def test_full_baseline_comparison_is_executable(self):
        baseline = baseline_fixture().map
        artifact = Mpq(baseline.read_bytes())
        script = artifact.extract('war3map.j').decode('utf-8')
        objects, functions = verifier.verify_baseline(script, artifact, script, artifact)
        self.assertIn('war3map.w3u', objects)
        self.assertGreaterEqual(functions, 30)

    def test_exhaustive_source_inventory_and_protected_baseline(self):
        baseline = baseline_fixture().source
        with formal_boss_source() as source:
            self.assertEqual(verifier.verify_source_contract(source, baseline), 6)

    def test_unexpected_call_and_mixed_boolean_fail_closed(self):
        runtime = verifier.BossJassRuntime(self.script)
        with self.assertRaisesRegex(ValueError, 'Missing packaged'):
            runtime.call('unrecognized_external_mutation', [])
        with self.assertRaisesRegex(ValueError, 'precedence parser'):
            runtime.expression('(true or false) and true', {})
        self.assertTrue(runtime.expression('true or unrecognized_external_mutation()', {}))

    def test_packaged_recursive_function_is_bounded_and_fail_closed(self):
        script = self.script + '\nfunction runawayFixture takes nothing returns nothing\ncall runawayFixture()\nendfunction\n'
        with self.assertRaisesRegex(ValueError, 'call depth exceeded'):
            verifier.BossJassRuntime(script).invoke('runawayFixture')

    def test_object_data_byte_change_cannot_validate_itself(self):
        class Artifact:
            def __init__(self, changed=None): self.changed = changed
            def has(self, name): return name in verifier.OBJECT_FILES
            def extract(self, name): return b'changed' if name == self.changed else b'baseline'
        for member in verifier.OBJECT_FILES:
            with self.subTest(member=member):
                with self.assertRaisesRegex(ValueError, 'Full object data changed'):
                    verifier.verify_baseline(self.script, Artifact(member), self.script, Artifact())

    def test_compiled_inventory_and_shared_wrapper_legacy_compatibility(self):
        from VerifyEquipmentAbilityArtifact import ability_objects
        from VerifyTowerPlacementArtifact import unit_objects
        from VerifyTowerUpgradeArtifact import validate_evolution_jass
        baseline = baseline_fixture().map
        artifact = Mpq(baseline.read_bytes())
        self.assertEqual(verifier.verify_compiled_structure(self.script), 6)
        validate_evolution_jass(self.script, unit_objects(artifact.extract('war3map.w3u')),
                                ability_objects(artifact.extract('war3map.w3a')))

    def test_hidden_hp_compensation_any_spell_caller_is_rejected(self):
        baseline = baseline_fixture().source
        for relative in ('towers/TDTowerRuntime.wurst', 'items/TDEquipmentCombat.wurst', 'pets/TDPetCombat.wurst'):
            with self.subTest(source=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / 'wurst'
                shutil.copytree(ROOT / 'wurst', root)
                path = root / relative
                path.write_text(path.read_text(encoding='utf-8') + '\nfunction hiddenCompensation(unit target)\n\ttarget.setLife(1000.0)\n', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'Forbidden HP/abort/type/element compensation'):
                    verifier.verify_source_contract(root, baseline)

    def test_new_packaged_hp_compensation_outside_engine_is_rejected(self):
        baseline = baseline_fixture().map
        artifact = Mpq(baseline.read_bytes())
        script = artifact.extract('war3map.j').decode('utf-8')
        body = function_body(script, 'tdPulseOrcBladestorm')
        changed = replace_body(script, 'tdPulseOrcBladestorm', body + '\tcall widget_setLife(tower_2, 1000.0)\n')
        with self.assertRaisesRegex(ValueError, 'Forbidden new packaged'):
            verifier.verify_baseline(changed, artifact, script, artifact)

    def test_protected_victory_function_mutation_is_rejected(self):
        baseline = baseline_fixture().map
        artifact = Mpq(baseline.read_bytes())
        script = artifact.extract('war3map.j').decode('utf-8')
        body = function_body(script, 'tdHandleGameResolved')
        changed = replace_body(script, 'tdHandleGameResolved', body + '\tcall unrelatedVictoryMutation()\n')
        with self.assertRaisesRegex(ValueError, 'Protected economy/victory/wave'):
            verifier.verify_baseline(changed, artifact, script, artifact)


class BossBaselineResolverTests(unittest.TestCase):
    def test_clean_clone_without_sibling_baseline_uses_only_git_objects(self):
        with tempfile.TemporaryDirectory(prefix='boss-clean-checkout-') as directory:
            checkout = Path(directory) / 'checkout'
            subprocess.run(['git', 'clone', '--shared', '--no-checkout', str(ROOT), str(checkout)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertFalse((checkout.parent / 'boss-resistance-baseline-20261012').exists())
            with BaselineFixture(repository=checkout, environment={}) as baseline:
                generated = baseline.root
                self.assertEqual(hashlib.sha256(baseline.map.read_bytes()).hexdigest(), BASELINE_MAP_SHA256)
                self.assertEqual(source_digest(baseline.source), BASELINE_SOURCE_SHA256)
                with formal_boss_source() as source:
                    self.assertEqual(verifier.verify_source_contract(source, baseline.source), 6)
                self.assertFalse((checkout / 'ExampleMap.w3x').exists())
            self.assertFalse(generated.exists())

    def test_explicit_map_and_source_overrides_need_no_git_access(self):
        fixture = baseline_fixture()
        def denied(_): raise AssertionError('Explicit pinned inputs must not call Git')
        with BaselineFixture(environment={'BOSS_RESISTANCE_BASELINE': str(fixture.map),
                                          'BOSS_RESISTANCE_BASELINE_SOURCE': str(fixture.source)},
                             git_reader=denied) as baseline:
            self.assertEqual(source_digest(baseline.source), BASELINE_SOURCE_SHA256)

    def test_wrong_override_map_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / 'wrong.w3x'
            bad.write_bytes(b'wrong baseline')
            with self.assertRaisesRegex(ValueError, 'baseline map SHA-256'):
                BaselineFixture(environment={'BOSS_RESISTANCE_BASELINE': str(bad)})

    def test_wrong_override_source_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / 'wurst'
            bad.mkdir()
            (bad / 'Changed.wurst').write_text('package Changed\n')
            with self.assertRaisesRegex(ValueError, 'baseline source SHA-256'):
                BaselineFixture(environment={'BOSS_RESISTANCE_BASELINE': str(baseline_fixture().map),
                                             'BOSS_RESISTANCE_BASELINE_SOURCE': str(bad)})

    def test_missing_history_reports_exact_prerequisites(self):
        def missing(args): raise subprocess.CalledProcessError(128, ['git', *args])
        with self.assertRaisesRegex(unittest.SkipTest, 'Fetch Git history containing ' + BASELINE_COMMIT):
            BaselineFixture(environment={}, git_reader=missing)


class BossResistanceHistoricalReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Guard-link resistance is the immutable original Boss-stage contract.
        # Pure Boss production has a different, separately executed state oracle.
        commit = '0384ccddcfdbaa868f773573c1f7403fe809d3e2'
        cls.directory = tempfile.TemporaryDirectory(prefix='formal-boss-stage-')
        cls.addClassCleanup(cls.directory.cleanup)
        cls.source_root = Path(cls.directory.name)
        map_path = cls.source_root / 'ExampleMap.w3x'
        data = subprocess.check_output(['git', 'show', commit + ':ExampleMap.w3x'], cwd=ROOT)
        verifier.require(hashlib.sha256(data).hexdigest() == '1b2b9671d3ce7b05837811dbfbb8efa0815fe4bcea840f53f8dde4789761f96e',
                         'Immutable original Boss release map differs')
        map_path.write_bytes(data)
        paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit, 'wurst'], cwd=ROOT).decode().splitlines()
        for relative in paths:
            target = cls.source_root / relative; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=ROOT))
        cls.artifact = Mpq(map_path.read_bytes())
        cls.script = cls.artifact.extract('war3map.j').decode('utf-8')
        if 'function tdEnemyMechanicScaleSpellDamage takes' not in cls.script:
            raise unittest.SkipTest('No newly built Boss-resistance map; real final-MPQ invocation pending')
        cls.map_path = map_path
        cls.baseline = baseline_fixture()

    def test_final_mpq_pure_runtime(self): verifier.verify_pure_and_runtime(self.script)
    def test_final_mpq_engine_accounting(self): verifier.verify_engine_and_accounting(self.script)
    def test_final_mpq_zero_engine_event(self): verifier.verify_zero_engine_event(self.script)
    def test_final_mpq_setup_shutdown(self): verifier.verify_setup_lifecycle(self.script)
    def test_final_mpq_scripted_paths(self): verifier.verify_scripted_damage(self.script)
    def test_pinned_formal_boss_release_full_objects_economy_victory(self):
        # This strict Boss-only predecessor delta must not be weakened for later
        # independently authorized object removals such as ordinary-only capture.
        data = subprocess.check_output(['git', 'show',
            '0384ccddcfdbaa868f773573c1f7403fe809d3e2:ExampleMap.w3x'], cwd=ROOT)
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         '1b2b9671d3ce7b05837811dbfbb8efa0815fe4bcea840f53f8dde4789761f96e')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'formal-boss-release.w3x'
            path.write_bytes(data)
            archive = subprocess.check_output(['git', 'archive',
                '0384ccddcfdbaa868f773573c1f7403fe809d3e2', 'wurst'], cwd=ROOT)
            root = Path(directory)
            with tarfile.open(fileobj=io.BytesIO(archive)) as entries:
                for entry in entries:
                    relative = Path(entry.name)
                    verifier.require(not relative.is_absolute() and '..' not in relative.parts and
                                     relative.parts[0] == 'wurst' and (entry.isfile() or entry.isdir()),
                                     'Unsafe formal Boss Git archive entry')
                    target = root / relative
                    if entry.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(entries.extractfile(entry).read())
            self.assertEqual(source_digest(root / 'wurst'),
                             'e17e5a8f6a99003c9ac1979e4b8b7807f084fc3a98b3544bd0e6f329d34c7994')
            verifier.verify_artifact(path, self.baseline.map, root / 'wurst', self.baseline.source)

    def test_current_source_and_compiled_boss_contract(self):
        verifier.verify_source_contract(self.source_root / 'wurst')
        verifier.verify_compiled_structure(self.script)


if __name__ == '__main__': unittest.main(verbosity=2)
