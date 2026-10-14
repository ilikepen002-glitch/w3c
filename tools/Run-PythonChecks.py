#!/usr/bin/env python3
"""Local unittest selection and timing. Does not compile, build or publish maps."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import importlib
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / 'tests/python'

# Reviewed classes, not filename heuristics. Regression includes historical maps,
# controlled/synthetic negatives and tool tests; none is current-map acceptance.
# New classes are unclassified until their inputs have been reviewed.
CLASS_GROUPS = {
    'source': '''
        test_upgrade_refund_artifact.UpgradeRefundSourceTests
        test_ambient_critter_source.AmbientCritterTests
        test_inventory_range_source.InventoryRangeSourceTests
        test_spirit_skill_icons.SpiritSkillIconTests
        test_equipment_icon_refresh.EquipmentIconRefreshTests
        test_resource_retirement.ResourceRetirementTests
        test_tower_target_priority_artifact.TowerTargetPrioritySourceTests
        test_tower_pet_detail_source.TowerPetDetailTests
        test_background_music_source.BackgroundMusicSourceTests
        test_combined_visual_text_artifact.CombinedSourceTextTests
        test_ground_upgrade_sort_source.GroundUpgradeSortSourceTests
        test_ground_upgrade_sort_source.GroundUpgradeEntryOwnerMutationTests
        test_ground_upgrade_sort_source.GroundUpgradeCooldownOwnerTests
        test_player_selected_item_description.SelectedItemDescriptionSourceTests
        test_active_cooldown_contract.ActiveSourceContractTests
        test_active_cooldown_contract.ProductionNativeStateTests
        test_build_semantic_icons.SemanticSourceTests
        test_build_trial_assets.TrialAssetTests
        test_capture_chance_65_source.CaptureChance65SourceTests
        test_capture_removal_artifact.CaptureRemovalSourceTests
        test_capture_removal_artifact.CaptureRemovalCurrentManagerTests
        test_equipment_inheritance_source.CurrentEquipmentInheritanceTests
        test_equipment_phase_a.EquipmentPhaseATests
        test_equipment_phase_b.EquipmentPhaseB
        test_equipment_phase_c.EquipmentPhaseC
        test_equipment_trial_integration.EquipmentTrialIntegration
        test_global_rankings_artifact.SourceTests
        test_map_branding_artifact.BrandingAssets
        test_pet_ui_workflow.CurrentSourceWorkflowTests
        test_pet_ui_workflow.AtomicContinueSourceTests
        test_purple_pet_release.PurpleReleaseSourceTests
        test_runtime_hotpath_replay.HotpathSourceContracts
        test_trial_delta.TrialCurrentManagerTests
        test_trial_static_contracts.TrialStaticContracts
        test_verify_bloodlust_autocast_artifact.BloodlustStaticSourceTests
        test_verify_builder_construction_artifact.BuilderConstructionSourceTests
        test_verify_builder_control_artifact.BuilderControlSourceTests
        test_verify_pet_ui_artifact.PetUISourceTests
    '''.split(),
    'regression': '''
        test_building_status_constants.BuildingStatusConstantsTests
        test_flower_full_roster_source.FlowerFullRosterSourceTests
        test_boss_pair_artifact.BossPairDeltaTests
        test_boss_pair_artifact.BossPairFrozenFormatTests
        test_eclipse_boss_artifact.EclipseVisualDeltaTests
        test_eclipse_boss_artifact.EclipseFrozenFormatTests
        test_pet_attack_phase_one.PetAttackPhaseOneSourceTests
        test_king_leoric_assets.AssetTests
        test_active_cooldown_contract.SyntheticPackagedObjectMutationTests
        test_active_cooldown_contract.SyntheticCompiledMutationTests
        test_python_checks.PythonChecksTests
        test_pet_manager_contracts.RealSourceContractTests
        test_boss_spell_resistance_artifact.BossResistanceVerifierUnitTests
        test_boss_spell_resistance_artifact.BossBaselineResolverTests
        test_boss_spell_resistance_artifact.BossResistanceHistoricalReleaseTests
        test_branch_icon_separation.BranchIconSeparationTests
        test_capture_removal_artifact.CaptureRemovalObjectTests
        test_capture_removal_artifact.CaptureRemovalMemberTests
        test_capture_removal_artifact.CaptureRemovalConditionTests
        test_capture_removal_artifact.CaptureRemovalHistoricalRuntimeTests
        test_equipment_ability_current_contract.EquipmentAbilityContractTests
        test_equipment_tooltip_current_contract.ControlledCurrentItemsTests
        test_global_rankings_artifact.ScalarTests
        test_global_rankings_artifact.DeltaTests
        test_global_rankings_artifact.ArchiveTests
        test_global_rankings_artifact.AliasProofTests
        test_map_branding_artifact.BrandingClosedDelta
        test_pet_deployment_artifact.ScalarSubsetTests
        test_pet_dialog_hotkeys.CompiledHotkeyContractTests
        test_pet_manager_contracts.CurrentArtifactVerifierMutationTests
        test_pet_skill_fits_artifact.PetSkillFitsMutationTests
        test_pet_ui_workflow.SharedOrderContractTests
        test_player_tooltip_artifact.PlayerTooltipArtifactTests
        test_trial_artifact.TrialArtifactTests
        test_trial_delta.TrialDeltaTests
        test_trial_replay.TrialProductionGateTests
        test_verify_bloodlust_autocast_artifact.BloodlustNativeInvariantTests
        test_verify_bloodlust_delta.BloodlustClosedDeltaTests
        test_verify_bloodlust_diagnostics.BloodlustDiagnosticProofTests
        test_verify_builder_construction_artifact.BuilderConstructionNegativeTests
        test_verify_builder_construction_artifact.BuilderConstructionDeltaNegativeTests
        test_verify_builder_control_artifact.BuilderControlNegativeTests
        test_verify_builder_control_artifact.BuilderControlRawObjectNegativeTests
        test_verify_builder_control_delta.BuilderControlDeltaTests
        test_verify_map_artifacts.ParsedObjectNegativeTests
        test_verify_pet_manager_delta.ManagerInheritanceTests
        test_verify_pet_ui_artifact.HistoricalPetUINegativeTests
        test_verify_pet_ui_artifact.PetUIResourceNegativeTests
        test_verify_pet_wild_pathing_artifact.WildPathingArtifactTests
        test_verify_pure_boss_artifact.PureBossInterpreterControlFlowTests
        test_verify_pure_boss_artifact.PureBossSourceTests
        test_verify_pure_boss_artifact.PureBossFormalArtifactTests
        test_verify_semantic_icon_artifact.ObjectDeltaTests
        test_verify_semantic_icon_artifact.PackedPathTests
        test_verify_semantic_icon_artifact.BlpTests
        test_verify_semantic_icon_artifact.ResourceContractTests
        test_wurst_linux.LinuxFailureTests
        test_wurst_linux.JavaProbeTests
    '''.split(),
    'map': '''
        test_upgrade_refund_artifact.UpgradeRefundActualArtifactTests
        test_tower_target_priority_artifact.TowerTargetPriorityPackedTests
        test_pet_attack_phase_one.FinalPetAttackArtifactTests
        test_aura_target_artifact.AuraTargetArtifactTests
        test_combined_visual_text_artifact.ActualCombinedFieldTests
        test_equipment_combat_replay.EquipmentPackedReplayTests
        test_equipment_tooltip_current_contract.ActualCurrentTooltipTests
        test_global_rankings_artifact.ActualArtifactTests
        test_ground_upgrade_artifact.GroundUpgradeArtifactTests
        test_leak_life_artifact.LeakLifeArtifactTests
        test_pet_compiled_rule_guards.PetCompiledRuleGuardTests
        test_pet_deployment_artifact.ActualDeploymentGateTests
        test_pet_skill_fits_artifact.PetSkillFitsArtifactTests
        test_runtime_hotpath_replay.HotpathPackedReplay
        test_verify_bloodlust_autocast_artifact.BloodlustActualNewArtifactTests
        test_verify_builder_construction_artifact.BuilderConstructionActualArtifactTests
        test_verify_builder_control_artifact.BuilderControlActualNewArtifactTests
        test_verify_map_artifacts.BaselineArtifactTests
        test_verify_pet_ui_artifact.PetUIArtifactTests
        test_verify_pure_boss_artifact.PureBossActualCompiledTests
        test_verify_tower_upgrade_artifact.TowerUpgradeArtifactTests
    '''.split(),
}

# Mixed classes need method-level exceptions; formal72 remains historical.
METHOD_GROUPS = {
    'test_verify_bloodlust_autocast_artifact.BloodlustStaticSourceTests.test_bladestorm_native_effects_and_evolution_remain_preserved': 'map',
    'test_trial_artifact.TrialArtifactTests.test_current_packaged_trial_bonus_text_and_percent_mutations': 'map',
    **{'test_trial_replay.TrialProductionGateTests.' + name: 'map' for name in (
        'test_actual_trial_map_when_authorized_build_available',
        'test_actual_production_native_timer_identity_mutation_rejected',
        'test_actual_production_refill_amount_mutation_rejected',
        'test_actual_current_capture_and_refund_mutation_rejected')},
}
MAP_ENV = ('PYTHON_CANDIDATE_MAP', 'TRIAL_CANDIDATE_MAP', 'EQUIPMENT_CANDIDATE_MAP',
           'HOTPATH_CANDIDATE_MAP', 'PURE_BOSS_CANDIDATE_MAP', 'W3C_ACTIVE_COOLDOWN_MAP', 'COMBINED_CANDIDATE_MAP')
CLASS_MAP_INPUTS = {
    'test_combined_visual_text_artifact.ActualCombinedFieldTests': ('COMBINED_PARENT_MAP',),
}
PURE_BOSS_INPUTS = {
    'test_actual_closed_reviewed_combined_artifact': (
        'PURE_BOSS_REVIEWED_JASS_TEMPLATES', 'PURE_BOSS_CANDIDATE_SOURCE', 'PURE_BOSS_BASELINE_SOURCE'),
    'test_actual_same_source_compiled_hook_harness': ('PURE_BOSS_HOOK_HARNESS_MAP',),
}


def group_for(test):
    identifier = test.id()
    if identifier in METHOD_GROUPS:
        return METHOD_GROUPS[identifier]
    owner = identifier.rsplit('.', 1)[0]
    return next((group for group, owners in CLASS_GROUPS.items() if owner in owners), 'unclassified')


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def resolve_selector(value):
    """Accept a test module, repository-relative file, or dotted unittest ID."""
    if value.endswith('.py') or '/' in value or '\\' in value:
        path = Path(value).resolve()
        if not path.is_file() or path.parent != TEST_DIR.resolve() or not path.name.startswith('test_'):
            raise ValueError('Select a test_*.py file directly in ' + str(TEST_DIR))
        return path.stem, ''
    value = value.removeprefix('tests.python.')
    module, _, member = value.partition('.')
    if not module.startswith('test_') or not (TEST_DIR / (module + '.py')).is_file():
        raise ValueError('Unknown test module: ' + module)
    return module, member


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TimedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings = []
        self.passed = set()
        self.outcome = 'PASS'

    def startTest(self, test):
        super().startTest(test)
        self.started = time.perf_counter()
        self.outcome = 'PASS'

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.add(test.id())

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcome = 'FAIL'

    def addError(self, test, err):
        super().addError(test, err)
        self.outcome = 'ERROR'

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcome = 'SKIP'
        self.stream.writeln('SKIP ' + test.id() + ': ' + reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.outcome = 'EXPECTED_FAILURE'

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.outcome = 'UNEXPECTED_SUCCESS'

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.outcome = 'FAIL' if issubclass(err[0], test.failureException) else 'ERROR'

    def stopTest(self, test):
        elapsed = time.perf_counter() - self.started
        self.timings.append((elapsed, test.id()))
        self.stream.writeln(f'TEST {elapsed:.6f}s {self.outcome} [{group_for(test)}] {test.id()}')
        super().stopTest(test)


def time_fixtures(tests, stack, timings):
    """Measure shared setup/teardown without changing unittest fixture semantics."""
    def timed(original, label):
        def call(*args, **kwargs):
            started = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                timings.append((time.perf_counter() - started, label))
        return call
    for cls in dict.fromkeys(type(test) for test in tests):
        for name in ('setUpClass', 'tearDownClass'):
            original = getattr(cls, name, None)
            if original is not None:
                # Capture the already-bound inherited method, preserving its class.
                stack.enter_context(patch.object(cls, name, staticmethod(timed(original, cls.__module__ + '.' + cls.__name__ + '.' + name))))
    for module in dict.fromkeys(sys.modules[type(test).__module__] for test in tests):
        for name in ('setUpModule', 'tearDownModule'):
            if hasattr(module, name):
                stack.enter_context(patch.object(module, name, timed(getattr(module, name), module.__name__ + '.' + name)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selectors', nargs='*', help='test_module, tests/python/test_file.py, or module.Class.test')
    parser.add_argument('--all', action='store_true', help='select every test_*.py module')
    parser.add_argument('--group', action='append', choices=('source', 'regression', 'map'), help='restrict reviewed classes/methods (repeatable)')
    parser.add_argument('--list', action='store_true', help='list selected IDs and categories without running fixtures/tests')
    parser.add_argument('--candidate-map', type=Path, help='explicit current-map input; never inferred from the root map/environment')
    parser.add_argument('--candidate-sha256', help='optional independently frozen expected SHA-256')
    args = parser.parse_args(argv)
    if args.all == bool(args.selectors):
        parser.error('choose either explicit selectors or --all')
    if args.candidate_sha256 and not args.candidate_map:
        parser.error('--candidate-sha256 requires --candidate-map')
    stream = sys.stdout
    started = time.perf_counter()
    phases = []
    failures = []
    candidate = None
    candidate_sha = None
    try:
        if args.candidate_map:
            candidate = args.candidate_map.resolve(strict=True)
            if not candidate.is_file():
                raise ValueError('Candidate map must be a file')
            candidate_sha = digest(candidate)
            if args.candidate_sha256 and args.candidate_sha256.lower() != candidate_sha:
                raise ValueError('Candidate SHA-256 mismatch')
            print(f'CANDIDATE {candidate}\nSHA256 {candidate_sha}', file=stream)
        phases.append((time.perf_counter() - started, 'candidate input'))
        selectors = [(p.stem, '') for p in sorted(TEST_DIR.glob('test_*.py'))] if args.all else [resolve_selector(v) for v in args.selectors]
    except (OSError, ValueError) as error:
        print('INPUT ERROR: ' + str(error), file=stream)
        return 2
    # All supported current-map interfaces receive one exact explicit path.
    # Historical/baseline/source parameters remain untouched.
    environment = {name: str(candidate) if candidate else '' for name in MAP_ENV}
    environment['TRIAL_CANDIDATE_MAP_SHA256'] = candidate_sha or ''
    sys.path.insert(0, str(TEST_DIR))
    try:
        with patch.dict(os.environ, environment), ExitStack() as stack:
            chosen = {}
            loader = unittest.TestLoader()
            for module_name, member in selectors:
                before = time.perf_counter()
                try:
                    module = importlib.import_module(module_name)
                    suite = loader.loadTestsFromName(member, module) if member else loader.loadTestsFromModule(module)
                    for test in flatten(suite):
                        chosen.setdefault(test.id(), test)
                except Exception as error:
                    failures.append(f'{module_name}: {type(error).__name__}: {error}')
                finally:
                    phases.append((time.perf_counter() - before, 'import/discovery ' + module_name))
            selected = [test for test in chosen.values() if not args.group or group_for(test) in args.group or group_for(test) == 'unclassified']
            print('SELECTED ' + ', '.join(f'{key}={value}' for key, value in sorted(Counter(group_for(t) for t in selected).items())), file=stream)
            if args.list:
                for test in selected:
                    print(f'[{group_for(test)}] {test.id()}', file=stream)
                for failure in failures + loader.errors:
                    print('DISCOVERY ERROR: ' + failure, file=stream)
                return 2 if failures or loader.errors else 0
            executable, uncovered = [], []
            for test in selected:
                group = group_for(test)
                reason = None
                if isinstance(test, unittest.loader._FailedTest):
                    # Let unittest emit the real missing-member/import error.
                    executable.append(test)
                    continue
                if group == 'unclassified':
                    reason = 'unclassified input contract; register it before execution'
                elif group == 'map' and candidate is None:
                    reason = 'actual map requires explicit --candidate-map'
                elif group == 'map':
                    needed = CLASS_MAP_INPUTS.get(test.id().rsplit('.', 1)[0], ())
                    if type(test).__name__ == 'PureBossActualCompiledTests':
                        needed += PURE_BOSS_INPUTS.get(test._testMethodName, ())
                    missing = [key for key in needed if not os.environ.get(key)]
                    if missing:
                        reason = 'missing additional evidence: ' + ', '.join(missing)
                if reason:
                    uncovered.append(test.id())
                    print(f'NOT COVERED [{group}] {test.id()}: {reason}', file=stream)
                else:
                    executable.append(test)
            if not selected:
                failures.append('Selection contains no tests')
            fixture_timings = []
            time_fixtures(executable, stack, fixture_timings)
            result = unittest.TextTestRunner(stream=stream, verbosity=0, resultclass=TimedResult).run(unittest.TestSuite(executable))
            for failure in failures:
                print('DISCOVERY ERROR: ' + failure, file=stream)
            if candidate:
                try:
                    if digest(candidate) != candidate_sha:
                        raise ValueError('Candidate bytes changed during tests')
                except (OSError, ValueError) as error:
                    failures.append(str(error))
                    print('INPUT ERROR: ' + failures[-1], file=stream)
            map_ids = {t.id() for t in selected if group_for(t) == 'map'}
            map_passed = len(map_ids & result.passed)
            print(f'MAP COVERAGE passed={map_passed} selected={len(map_ids)}; ' + ('NOT REQUESTED' if not map_ids else 'explicit candidate only; historical/fixture tests are not map acceptance'), file=stream)
            for elapsed, label in phases:
                print(f'PREP {elapsed:.6f}s {label}', file=stream)
            for elapsed, label in fixture_timings:
                print(f'FIXTURE {elapsed:.6f}s {label}', file=stream)
            print('SLOWEST 10 (tests and preparation/fixtures):', file=stream)
            for elapsed, label in sorted(result.timings + phases + fixture_timings, reverse=True)[:10]:
                print(f'  {elapsed:.6f}s {label}', file=stream)
            print(f'SUMMARY selected={len(selected)} run={result.testsRun} passed={len(result.passed)} failures={len(result.failures)} errors={len(result.errors) + len(failures)} skipped={len(result.skipped)} expected_failures={len(result.expectedFailures)} unexpected_successes={len(result.unexpectedSuccesses)} not_covered={len(uncovered)} total={time.perf_counter() - started:.6f}s', file=stream)
            if not result.wasSuccessful() or failures:
                print('STATUS FAILED', file=stream)
                return 1
            if uncovered or map_passed != len(map_ids):
                print('STATUS INCOMPLETE (selected checks not fully covered)', file=stream)
                return 2
            print('STATUS PASSED_SELECTED (no build or gameplay claim)', file=stream)
            return 0
    finally:
        sys.path.remove(str(TEST_DIR))


if __name__ == '__main__':
    raise SystemExit(main())
