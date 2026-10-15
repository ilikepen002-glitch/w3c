#!/usr/bin/env python3
"""Local unittest selection and timing. Does not compile, build or publish maps."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / 'tests/python'

# Reviewed classes, not filename heuristics. Regression includes historical maps,
# controlled/synthetic negatives and tool tests; none is current-map acceptance.
# New classes are unclassified until their inputs have been reviewed.
CLASS_GROUPS = {
    'source': '''
        test_ground_upgrade_runtime_source.GroundUpgradeRuntimeSourceTests
        test_inventory_craft_runtime_source.InventoryCraftRuntimeSourceTests
        test_inventory_craft_runtime_source.InventoryCraftSourceMutationTests
        test_upgrade_refund_artifact.UpgradeRefundSourceTests
        test_ambient_critter_source.AmbientCritterTests
        test_pet_hero_feedback.HeroFeedbackTests
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
        test_inventory_craft_native_models.InventoryCraftNativeModelTests
        test_python_check_results.PythonCheckResultTests
        test_inventory_craft_control_flow.InventoryCraftControlFlowTests
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
        test_inventory_craft_artifact.InventoryCraftArtifactTests
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


def verification_manifest():
    """Freeze Python verifier/test inputs; production and maps are separate."""
    return {prefix + '/' + path.relative_to(home).as_posix(): digest(path)
            for prefix, home in (('tools', ROOT / 'tools'), ('tests/python', TEST_DIR))
            for path in sorted(home.rglob('*.py')) if '__pycache__' not in path.parts}


def write_results_json(path, document):
    """Atomic writes leave an explicit nonterminal report while tests run."""
    path = path.resolve()
    if path.suffix != '.json':
        raise ValueError('--results-json must have a .json suffix')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name + '.', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(document, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def method_record(test, outcome='NOT_RUN', reason=None):
    return dict(id=test.id(), group=group_for(test), outcome=outcome, executed=False,
                duration_seconds=None, reason=reason, exceptions=[], subtests=[])


def exception_record(result, test, err):
    return dict(type=err[0].__module__ + '.' + err[0].__qualname__,
                message=str(err[1]), traceback=result._exc_info_to_string(err, test))


class TimedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings = []
        self.passed = set()
        self.outcome = 'PASS'
        self.methods = {}
        self.fixtures = []

    def startTest(self, test):
        super().startTest(test)
        self.started = time.perf_counter()
        self.outcome = 'PASS'
        self.methods[test.id()] = method_record(test, 'RUNNING')
        self.methods[test.id()]['executed'] = True
        self.stream.writeln(f'START [{group_for(test)}] {test.id()}')
        self.stream.flush()

    def record_event(self, test, outcome, err=None, reason=None):
        parent = getattr(test, 'test_case', test)
        event = dict(id=test.id(), outcome=outcome, reason=reason,
                     exception=exception_record(self, test, err) if err else None)
        if parent.id() not in self.methods:
            self.fixtures.append(event)
            return
        record = self.methods[parent.id()]
        if parent is not test:
            record['subtests'].append(event)
        if err:
            record['exceptions'].append(event['exception'])
        if reason:
            record['reason'] = reason
        # A later failing subtest must not erase a preceding ERROR.
        if record['outcome'] != 'ERROR' or outcome == 'ERROR':
            record['outcome'] = outcome

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.add(test.id())
        self.record_event(test, 'PASS')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcome = 'FAIL'
        self.record_event(test, 'FAIL', err)

    def addError(self, test, err):
        super().addError(test, err)
        self.outcome = 'ERROR'
        self.record_event(test, 'ERROR', err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcome = 'SKIP'
        self.record_event(test, 'SKIP', reason=reason)
        self.stream.writeln('SKIP ' + test.id() + ': ' + reason)
        self.stream.flush()

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.outcome = 'EXPECTED_FAILURE'
        self.record_event(test, 'EXPECTED_FAILURE', err)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.outcome = 'UNEXPECTED_SUCCESS'
        self.record_event(test, 'UNEXPECTED_SUCCESS')

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.outcome = 'FAIL' if issubclass(err[0], test.failureException) else 'ERROR'
            self.record_event(subtest, self.outcome, err)

    def stopTest(self, test):
        elapsed = time.perf_counter() - self.started
        self.timings.append((elapsed, test.id()))
        self.methods[test.id()]['duration_seconds'] = elapsed
        self.stream.writeln(f'TEST {elapsed:.6f}s {self.outcome} [{group_for(test)}] {test.id()}')
        self.stream.flush()
        super().stopTest(test)


def time_fixtures(tests, stack, timings):
    """Measure shared setup/teardown without changing unittest fixture semantics."""
    def timed(original, label):
        def call(*args, **kwargs):
            started = time.perf_counter()
            print('FIXTURE START ' + label, flush=True)
            try:
                return original(*args, **kwargs)
            finally:
                timings.append((time.perf_counter() - started, label))
                print('FIXTURE END ' + label, flush=True)
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
    parser.add_argument('--results-json', type=Path, help='atomic per-method result report, including failures and uncovered methods')
    parser.add_argument('--run-label', choices=('baseline', 'candidate', 'unlabelled'), default='unlabelled',
                        help='explicit artifact role for later comparison; does not grant map/build authorization')
    args = parser.parse_args(argv)
    if args.all == bool(args.selectors):
        parser.error('choose either explicit selectors or --all')
    if args.candidate_sha256 and not args.candidate_map:
        parser.error('--candidate-sha256 requires --candidate-map')
    stream = sys.stdout
    started = time.perf_counter()
    document = dict(schema='python-check-results-v1', terminal=False, exit_code=None, status='RUNNING',
                    run_label=args.run_label, started_at=datetime.now(timezone.utc).isoformat(),
                    python_version=sys.version, artifact=dict(path=None, sha256=None),
                    selection=dict(requested=dict(all=args.all, selectors=args.selectors,
                                                  groups=sorted(set(args.group or []))), methods=[]),
                    verification_manifest={}, methods=[], fixtures=[], issues=[], discovery_errors=[], summary={})
    if args.results_json:
        try:
            if args.candidate_map and args.results_json.resolve() == args.candidate_map.resolve():
                raise ValueError('Results must not overwrite the artifact input')
            document['verification_manifest'] = verification_manifest()
            keys = {key for values in CLASS_MAP_INPUTS.values() for key in values}
            keys.update(key for values in PURE_BOSS_INPUTS.values() for key in values)
            document['auxiliary_inputs'] = {}
            for key in sorted(keys):
                value = os.environ.get(key, '')
                path = Path(value) if value else None
                document['auxiliary_inputs'][key] = dict(value=value, sha256=digest(path) if path and path.is_file() else None)
            write_results_json(args.results_json, document)
        except (OSError, ValueError) as error:
            print('RESULTS ERROR: ' + str(error), file=stream, flush=True)
            return 1
    def finish(code, status):
        if not document['summary']:
            document['summary'] = dict(selected=len(document['methods']), run=0, passed=0, failures=0,
                                       errors=len(document['issues']), skipped=0, expected_failures=0,
                                       unexpected_successes=0, not_covered=0, map_selected=0, map_passed=0)
        document.update(terminal=True, exit_code=code, status=status,
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        elapsed_seconds=time.perf_counter() - started)
        if args.results_json:
            try:
                write_results_json(args.results_json, document)
                print('RESULTS JSON ' + str(args.results_json.resolve()), file=stream, flush=True)
            except (OSError, ValueError) as error:
                print('RESULTS ERROR: ' + str(error), file=stream, flush=True)
                print('STATUS FAILED (results recording error)', file=stream, flush=True)
                return 1
        return code
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
            document['artifact'] = dict(path=str(candidate), sha256=candidate_sha)
            if args.candidate_sha256 and args.candidate_sha256.lower() != candidate_sha:
                raise ValueError('Candidate SHA-256 mismatch')
            print(f'CANDIDATE {candidate}\nSHA256 {candidate_sha}', file=stream, flush=True)
        phases.append((time.perf_counter() - started, 'candidate input'))
        selectors = [(p.stem, '') for p in sorted(TEST_DIR.glob('test_*.py'))] if args.all else [resolve_selector(v) for v in args.selectors]
        document['selection']['requested']['selectors'] = sorted(set(module + ('.' + member if member else '') for module, member in selectors))
    except (OSError, ValueError) as error:
        print('INPUT ERROR: ' + str(error), file=stream, flush=True)
        document['issues'].append(str(error))
        return finish(2, 'INPUT_ERROR')
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
                    document['discovery_errors'].append(dict(module=module_name, type=type(error).__name__,
                                                             message=str(error), traceback=traceback.format_exc()))
                finally:
                    phases.append((time.perf_counter() - before, 'import/discovery ' + module_name))
            selected = [test for test in chosen.values() if not args.group or group_for(test) in args.group or group_for(test) == 'unclassified']
            document['selection']['methods'] = [dict(id=test.id(), group=group_for(test)) for test in selected]
            document['methods'] = [method_record(test) for test in selected]
            print('SELECTED ' + ', '.join(f'{key}={value}' for key, value in sorted(Counter(group_for(t) for t in selected).items())), file=stream, flush=True)
            if args.list:
                for test in selected:
                    print(f'[{group_for(test)}] {test.id()}', file=stream, flush=True)
                for failure in failures + loader.errors:
                    print('DISCOVERY ERROR: ' + failure, file=stream, flush=True)
                document['issues'] = failures + loader.errors
                return finish(2 if failures or loader.errors else 0, 'LISTED')
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
                    document['methods'][selected.index(test)].update(outcome='NOT_COVERED', reason=reason)
                    print(f'NOT COVERED [{group}] {test.id()}: {reason}', file=stream, flush=True)
                else:
                    executable.append(test)
            if not selected:
                failures.append('Selection contains no tests')
            fixture_timings = []
            time_fixtures(executable, stack, fixture_timings)
            result = unittest.TextTestRunner(stream=stream, verbosity=0, resultclass=TimedResult).run(unittest.TestSuite(executable))
            document['fixtures'] = result.fixtures
            for index, test in enumerate(selected):
                if test.id() in result.methods:
                    document['methods'][index] = result.methods[test.id()]
                elif test in executable:
                    owner = test.id().rsplit('.', 1)[0]
                    blocked = [event for event in result.fixtures if
                               event['id'].startswith(('setUpClass (', 'setUpModule (')) and
                               (owner == event['id'].split('(', 1)[1].rstrip(')') or
                                owner.startswith(event['id'].split('(', 1)[1].rstrip(')') + '.'))]
                    if blocked:
                        row = document['methods'][index]
                        row.update(outcome='FIXTURE_ERROR' if any(event['outcome'] != 'SKIP' for event in blocked) else 'FIXTURE_SKIP',
                                   reason='; '.join(event['id'] + ': ' + (event['reason'] or event['outcome']) for event in blocked),
                                   exceptions=[event['exception'] for event in blocked if event['exception']])
                    else:
                        failures.append('No terminal unittest outcome for ' + test.id())
            for failure in failures:
                print('DISCOVERY ERROR: ' + failure, file=stream, flush=True)
            if candidate:
                try:
                    if digest(candidate) != candidate_sha:
                        raise ValueError('Candidate bytes changed during tests')
                except (OSError, ValueError) as error:
                    failures.append(str(error))
                    print('INPUT ERROR: ' + failures[-1], file=stream, flush=True)
            if args.results_json:
                final_manifest = verification_manifest()
                if final_manifest != document['verification_manifest']:
                    failures.append('Python verifier/test inputs changed during tests')
                    document['verification_manifest_after'] = final_manifest
                    print('INPUT ERROR: ' + failures[-1], file=stream, flush=True)
            map_ids = {t.id() for t in selected if group_for(t) == 'map'}
            map_passed = len(map_ids & result.passed)
            print(f'MAP COVERAGE passed={map_passed} selected={len(map_ids)}; ' + ('NOT REQUESTED' if not map_ids else 'explicit candidate only; historical/fixture tests are not map acceptance'), file=stream, flush=True)
            for elapsed, label in phases:
                print(f'PREP {elapsed:.6f}s {label}', file=stream, flush=True)
            for elapsed, label in fixture_timings:
                print(f'FIXTURE {elapsed:.6f}s {label}', file=stream, flush=True)
            print('SLOWEST 10 (tests and preparation/fixtures):', file=stream, flush=True)
            for elapsed, label in sorted(result.timings + phases + fixture_timings, reverse=True)[:10]:
                print(f'  {elapsed:.6f}s {label}', file=stream, flush=True)
            print(f'SUMMARY selected={len(selected)} run={result.testsRun} passed={len(result.passed)} failures={len(result.failures)} errors={len(result.errors) + len(failures)} skipped={len(result.skipped)} expected_failures={len(result.expectedFailures)} unexpected_successes={len(result.unexpectedSuccesses)} not_covered={len(uncovered)} total={time.perf_counter() - started:.6f}s', file=stream, flush=True)
            document['issues'] = failures
            document['summary'] = dict(selected=len(selected), run=result.testsRun, passed=len(result.passed),
                                       failures=len(result.failures), errors=len(result.errors) + len(failures),
                                       skipped=len(result.skipped), expected_failures=len(result.expectedFailures),
                                       unexpected_successes=len(result.unexpectedSuccesses), not_covered=len(uncovered),
                                       map_selected=len(map_ids), map_passed=map_passed)
            if not result.wasSuccessful() or failures:
                print('STATUS FAILED', file=stream, flush=True)
                return finish(1, 'FAILED')
            if uncovered or map_passed != len(map_ids):
                print('STATUS INCOMPLETE (selected checks not fully covered)', file=stream, flush=True)
                return finish(2, 'INCOMPLETE')
            print('STATUS PASSED_SELECTED (no build or gameplay claim)', file=stream, flush=True)
            return finish(0, 'PASSED_SELECTED')
    finally:
        sys.path.remove(str(TEST_DIR))


if __name__ == '__main__':
    raise SystemExit(main())
