"""Execute actual directed-learning JASS and fixed native objects from a packed map.
Engine handles, input events, RNG and timer delivery are controlled boundaries.
No Warcraft rendering, loading-time or FPS claims are made by this offline gate.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from GenerateTowerTerrainMask import Mpq
from VerifyPetFourSlotArtifact import FourSlotRuntime
from VerifyPetManagerSource import function_body, source, verify_scalar_contracts, verify_wiring
from VerifyPetUIArtifact import verify_directed_objects, field_value, jass_function
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyGlobalRankingsArtifact import members, normalize_info
from VerifySemanticIconArtifact import parse_objects

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '3aefc083dc79de9c66a11f0e09535fd97d359e59'


def verify_source(baseline=BASELINE):
    verify_scalar_contracts()
    verify_wiring(baseline=baseline)
    state, directed, ui, session = (source(name) for name in ('TDPetState', 'TDPetCultivation', 'TDPetUI', 'TDPetUIState'))
    for name in ('tdPetBeginReroll', 'tdPetContinueReroll', 'tdPetResolveRerollVersion'):
        body = function_body(state, name)[1]
        require('TD_PET_PROPOSAL_RANDOM' in body and 'tdIsLaneFinished(lane)' in body, name + ': candidate type/finished guard missing')
    begun = function_body(directed, 'tdPetBeginDirected')[1]
    require('proposalQuality = 2' in begun and 'TD_PET_PROPOSAL_DIRECTED' in begun and 'proposalEpoch' in begun, 'Directed preview type/quality/epoch missing')
    require('GetRandom' not in begun and 'tdPetRerollStones' not in begun, 'Preview must not charge or draw RNG')
    committed = function_body(directed, 'tdPetResolveDirectedVersion')[1]
    for phrase in ('pet != expected', 'pet.proposalVersion != candidateVersion', 'pet.generation != currentGeneration', 'matchEpoch != tdPetMatchEpoch[lane]', 'pet.revision != sourceRevision', 'pet.proposalQuality != 2', 'tdPetDirectedSkillAllowed', 'tdIsLaneFinished(lane)'):
        require(phrase in committed, 'Missing directed transaction guard: ' + phrase)
    require(committed.count('tdPetRerollStones[lane] -= TD_PET_DIRECTED_COST') == 1, 'Directed payment must have one writer')
    require(committed.index('pet.setSkill') < committed.index('tdPetRerollStones[lane] -=') < committed.rindex('pet.clearProposal()') < committed.index('pet.invalidateCombat()'), 'Commit must precede native combat/presentation refresh')
    require('readyAt =' not in directed and 'GetLocalPlayer' not in directed, 'Learning resets cooldown or uses local state')
    require('tdPetResolveDirectedVersion' in function_body(ui, 'onCommand')[1] and 'current.proposalType == proposalType' in function_body(session, 'matchesPet')[1], 'New UI does not use the real transaction/snapshot')
    # These authoritative behavior bodies and unmodified subsystems are locked
    # to the approved frozen source, not a broad State-file difference whitelist.
    before = subprocess.check_output(['git', 'show', baseline + ':wurst/pets/TDPetState.wurst'], cwd=ROOT).decode()
    for name in ('skillAllowed', 'rollSkill', 'setSkill', 'invalidateCombat', 'skillPower', 'recall', 'tdPetCreditWave'):
        require(function_body(state, name)[1] == function_body(before, name)[1], 'Unrelated spirit behavior changed: ' + name)
    for filename in ('TDPetElementData', 'TDPetHeroRules', 'TDPetRuntime', 'TDPetCombat', 'TDPetEffectScheduler', 'TDPetAttackQueue'):
        frozen = subprocess.check_output(['git', 'show', baseline + ':wurst/pets/' + filename + '.wurst'], cwd=ROOT)
        require((ROOT / 'wurst/pets' / (filename + '.wurst')).read_bytes() == frozen, 'Unrelated combat/effect source changed: ' + filename)
    return {'scalar_page_cases': 2110, 'preview_cost': 0, 'commit_cost': 3, 'fixed_choice_identities': 28, 'additional_manager_commands': 10, 'unchanged_behavior_bodies': 7}


def fixture(script, species=1, lane=0, slot=0, owned_count=4):
    r = FourSlotRuntime(script)
    for name in ('init_TDPetCultivation', 'init_TDPetUIState'):
        if name in r.functions:
            r.invoke(name)
    r.invoke('tdResetState')
    for i in range(4):
        r.invoke('tdSetLaneActive', i, True)
        r.invoke('tdPetInitializeLane', i)
    p = record(r, lane, species, owned_count)
    require(r.invoke('tdPetAt', lane, slot) == p, 'Wrong fixture collection slot')
    r.int_trace.clear()
    return r, p


def record(r, lane, species, owned_count=4):
    p = r.invoke('new_TDPet', lane, species, 1)
    for i, skill in enumerate((0, 5, 6, 11)[:owned_count]):
        r.invoke('TDPet_setSkill', p, i, skill, 1)
    require(r.invoke('tdPetStore', lane, p), 'Fixture store failed')
    r.globals['TDPet_readyAt'][p] = 88.
    return p


def field(r, p, key):
    return r.globals['TDPet_' + key][p]


def balance(r, lane=0, value=None):
    array = r.globals['TDPetState_tdPetRerollStones']
    if value is not None:
        array[lane] = value
    return array[lane]


def resolve(r, p, *, lane=0, slot=0, replace=True, **overrides):
    values = dict(expected=p, version=field(r, p, 'proposalVersion'), revision=field(r, p, 'proposalRevision'), generation=field(r, p, 'generation'), epoch=r.globals['TDPetState_tdPetMatchEpoch'][lane])
    values.update(overrides)
    return r.invoke('tdPetResolveDirectedVersion', lane, slot, values['expected'], values['version'], values['revision'], values['generation'], values['epoch'], replace)


def verify_transactions(script):
    cases = []
    for stock in (0, 2, 3, 4):
        r, p = fixture(script)
        balance(r, value=stock)
        require(r.invoke('tdPetBeginDirected', 0, 0, 0, 1) and balance(r) == stock, 'Preview consumed/reserved stock')
        old_version, old_revision, old_generation = (field(r, p, key) for key in ('proposalVersion', 'revision', 'generation'))
        require(resolve(r, p) == (stock >= 3), 'Wrong material admission')
        require(balance(r) == (stock - 3 if stock >= 3 else stock), 'Wrong exact payment')
        if stock >= 3:
            require(field(r, p, 'skillCount') == 4 and field(r, p, 'level') == 1 and field(r, p, 'readyAt') == 88., 'Commit changed count/resonance/CD')
            require(field(r, p, 'revision') == old_revision + 1 and field(r, p, 'generation') == old_generation + 1, 'Commit failed to invalidate combat once')
            require(not resolve(r, p, version=old_version, revision=old_revision, generation=old_generation), 'Double confirmation charged twice')
        else:
            require(field(r, p, 'proposalSkill') == 1 and resolve(r, p, replace=False), 'Insufficient stock lost/locked candidate')
        require(not r.int_trace, 'Directed flow drew random numbers')
        cases.append({'stock': stock, 'final': balance(r)})
    r, p = fixture(script)
    balance(r, value=4)
    require(r.invoke('tdPetBeginReroll', 0, 0, 0), 'Original random flow failed')
    previous = [field(r, p, key) for key in ('proposalType', 'proposalVersion', 'proposalSkill', 'proposalQuality', 'proposalRevision')]
    calls = len(r.int_trace)
    require(not r.invoke('tdPetBeginDirected', 0, 0, 0, 1), 'Directed request overwrote paid random candidate')
    require(previous == [field(r, p, key) for key in ('proposalType', 'proposalVersion', 'proposalSkill', 'proposalQuality', 'proposalRevision')] and len(r.int_trace) == calls and balance(r) == 3, 'Rejected directed request mutated/drew/charged')
    require(r.invoke('tdPetResolveRerollVersion', 0, 0, field(r, p, 'proposalVersion'), False), 'Random keep failed')
    require(r.invoke('tdPetBeginDirected', 0, 0, 0, 1), 'Directed preview failed')
    version = field(r, p, 'proposalVersion')
    for name, args in (('tdPetResolveRerollVersion', (0, 0, version, True)), ('tdPetResolveRerollVersion', (0, 0, version, False)), ('tdPetContinueReroll', (0, 0, p, version, field(r, p, 'revision'))), ('tdPetBeginReroll', (0, 0, 0)), ('tdPetOpenSlot', (0, 0)), ('tdPetBeginRelease', (0, 0))):
        require(not r.invoke(name, *args), name + ': legacy entrance accepted directed candidate')
    require(balance(r) == 3 and field(r, p, 'proposalVersion') == version and field(r, p, 'proposalType') == 2, 'Legacy entrance cleared/charged directed candidate')
    require(resolve(r, p), 'Directed commit after legacy rejection failed')
    r, p = fixture(script)
    q = record(r, 0, 2)
    balance(r, value=3)
    require(r.invoke('tdPetBeginDirected', 0, 0, 0, 1) and r.invoke('tdPetBeginDirected', 0, 1, 0, 2), 'Two previews failed')
    require(resolve(r, p) and not resolve(r, q, slot=1) and field(r, q, 'proposalSkill') == 2, 'Shared 3-stock double spend')
    require(resolve(r, q, slot=1, replace=False), 'Second candidate cannot cancel after competition')
    for change in ('revision', 'generation', 'version', 'quality', 'slotReuse', 'reset', 'finished', 'left', 'inactive', 'defeated', 'gameover'):
        r, p = fixture(script)
        balance(r, value=3)
        require(r.invoke('tdPetBeginDirected', 0, 0, 0, 1), 'Negative fixture preview failed')
        saved = {key: field(r, p, key) for key in ('proposalVersion', 'proposalRevision', 'generation')}
        epoch = r.globals['TDPetState_tdPetMatchEpoch'][0]
        if change == 'revision': r.invoke('TDPet_setSkill', p, 1, 7, 1)
        elif change == 'generation': r.invoke('TDPet_recall', p)
        elif change == 'version': r.globals['TDPet_proposalVersion'][p] += 1
        elif change == 'quality': r.globals['TDPet_proposalQuality'][p] = 3
        elif change == 'slotReuse':
            require(r.invoke('tdPetDiscardOwned', 0, 0), 'Discard fixture failed'); record(r, 0, 1)
        elif change == 'reset':
            r.invoke('tdPetInitializeLane', 0); record(r, 0, 1); balance(r, value=3)
        elif change == 'finished': r.invoke('tdSetLaneFinished', 0, True)
        elif change == 'left': r.invoke('tdPetMarkPlayerLeft', 0)
        elif change == 'inactive': r.invoke('tdSetLaneActive', 0, False)
        elif change == 'defeated': r.invoke('tdSetLaneDefeated', 0, True)
        elif change == 'gameover': r.invoke('tdSetGameOver', True)
        require(not resolve(r, p, version=saved['proposalVersion'], revision=saved['proposalRevision'], generation=saved['generation'], epoch=epoch), change + ': stale authority committed')
        require(balance(r) == 3, change + ': stale authority charged')
    return {'stock_cases': cases, 'legacy_random_free_adoption_rejected': True, 'double_confirm_rejected': True, 'two_pet_inventory_race': True, 'lifecycle_negatives': 11, 'directed_rng_draws': 0}


def verify_pages(script, abilities):
    r, p = fixture(script)
    session = r.invoke('new_TDPetUISession', 0)
    r.globals['TDPetUIState_tdPetUISessions'][0] = session
    visited, empty = [], 0
    r.globals['TDPetUISession_directedSlot'][session] = 2
    for page in range(3):
        r.globals['TDPetUISession_directedPage'][session] = page
        require(r.invoke('TDPetUISession_open', session, 6, 0, 0, p, 0, 900 + page), 'Fixed third-slot page unavailable')
        for action, present in ((30, page > 0), (29, page < 2)):
            require((r.invoke('TDPetUISession_commandAction', session, 0, 900 + page, r.invoke('tdPetManagerCommandId', action), 1) >= 0) == present, 'First/last-page navigation mounted beyond boundary')
        for cell in range(8):
            skill = r.invoke('tdPetDirectedCandidateAt', p, 2, page * 8 + cell)
            if skill >= 0:
                visited.append(skill)
                ability = r.invoke('tdPetDirectedAbilityId', skill)
                require(r.invoke('TDPetUISession_commandAction', session, 0, 900 + page, ability, 1) == 200 + cell, 'Choice fixed cell identity rejected')
                require(r.invoke('TDPetUISession_commandAction', session, 0, 899 + page, ability, 1) == -1, 'Old unit authorized current page')
            else:
                empty += 1
                for raw, (_, fields) in abilities.items():
                    if re.fullmatch(r'Pn[0-9A-F]{2}', raw) and field_value(fields, 'abpy') * 4 + field_value(fields, 'abpx') == cell:
                        require(r.invoke('TDPetUISession_commandAction', session, 0, 900 + page, int.from_bytes(raw.encode(), 'big'), 1) == -1, 'Empty catalog cell authorized an unmounted identity')
    expected = [skill for skill in range(49) if r.invoke('tdPetDirectedSkillAllowed', p, 2, skill)]
    require(visited == expected and set(range(39, 49)).issubset(visited), 'Third-slot catalog truncates/skips legal heroes')
    require(r.invoke('tdPetBeginDirected', 0, 0, 2, 48), 'Hero preview failed')
    version = field(r, p, 'proposalVersion')
    require(r.invoke('TDPetUISession_open', session, 7, 0, 0, p, 0, 910), 'Directed preview page unavailable')
    for action in (17, 18, 21):
        require(r.invoke('TDPetUISession_admitCommand', session, 0, 910, r.invoke('tdPetManagerCommandId', action), 1) == -1, 'Directed preview admits random command')
    r.invoke('TDPetUISession_close', session)
    require(field(r, p, 'proposalVersion') == version and field(r, p, 'proposalSkill') == 48, 'Close loses unpaid candidate')
    require(r.invoke('TDPetUISession_open', session, 7, 0, 0, p, 0, 911), 'Reopened candidate unavailable')
    r.invoke('TDPet_recall', p)
    require(r.invoke('TDPetUISession_admitCommand', session, 0, 911, r.invoke('tdPetManagerCommandId', 32), 1) == -2, 'Generation change reused old confirmation')
    require(field(r, p, 'proposalSkill') == 48, 'UI snapshot expiry discarded candidate')
    small, two = fixture(script, owned_count=2)
    selection = small.invoke('new_TDPetUISession', 0)
    require(small.invoke('TDPetUISession_open', selection, 5, 0, 0, two, 0, 950), 'Two-owned-slot selector unavailable')
    for action in (24, 25, 26, 27):
        require((small.invoke('TDPetUISession_commandAction', selection, 0, 950, small.invoke('tdPetManagerCommandId', action), 1) >= 0) == (action < 26), 'Selector mounted an unowned skill slot')
    return {'two_owned_slots_hide_third_fourth': True, 'first_last_page_boundaries': True, 'third_slot_pages': 3, 'legal_choices_reached': len(visited), 'heroes_reached': 10, 'empty_cells': empty, 'close_preserves_candidate': True, 'stale_generation_consumes_only_page_authority': True}


class DirectedNativeRuntime(FourSlotRuntime):
    def __init__(self, script):
        self.spell = 0
        self.notices = []
        self.refreshes = []
        super().__init__(script)
        for name in ('init_TDPetCultivation', 'init_TDPetUIState', 'init_TDPetUIView'):
            if name in self.functions:
                self.invoke(name)

    def execute_call(self, name, args):
        if name == 'tdPetRefreshHost':
            self.refreshes.append(args[0])
        return super().execute_call(name, args)

    def native(self, name, args):
        if name == 'GetSpellAbilityId': return True, self.spell
        if name == 'GetSpellTargetUnit': return True, None
        if name == 'GetLocalPlayer': return True, -1  # Local selection is a UI boundary.
        if name in ('ClearSelection', 'SelectUnit'): return True, None
        if name == 'DisplayTimedTextToPlayer':
            self.notices.append(args[-1]); return True, None
        return super().native(name, args)


def verify_native_bridge(script):
    r = DirectedNativeRuntime(script)
    r.invoke('tdResetState')
    for lane in range(4):
        r.invoke('tdSetLaneActive', lane, True)
        r.invoke('tdPetInitializeLane', lane)
    p = record(r, 0, 1)
    r.globals['TDPet_host'][p] = 101
    r.globals['TDPet_level'][p] = 3
    session = r.invoke('new_TDPetUISession', 0)
    r.globals['TDPetUIState_tdPetUISessions'][0] = session
    balance(r, value=3)
    require(r.invoke('tdPetRenderPage', 0, 2, 0, 0, 0), 'Actual cultivate renderer failed')
    def display(): return r.globals['TDPetUIView_tdPetDisplays'][0]
    def mode(): return r.globals['TDPetUISession_mode'][session]
    def click(ability, caster=None):
        r.native_trigger = display() if caster is None else caster
        r.spell = ability
        r.invoke('onCommand')
        r.native_trigger = None
    for action, expected_mode in ((23, 5), (24, 6)):
        click(r.invoke('tdPetManagerCommandId', action))
        require(mode() == expected_mode and balance(r) == 3, 'Native navigation changed payment/state')
    click(r.invoke('tdPetDirectedAbilityId', 1))
    require(mode() == 7 and field(r, p, 'proposalType') == 2 and field(r, p, 'proposalSkill') == 1 and balance(r) == 3, 'Native option click did not preview without payment')
    require(any('当前3' in text and '确认消耗3洗练石' in text for text in r.notices), 'Native preview omitted current stock/confirmation price')
    old_display, candidate_version = display(), field(r, p, 'proposalVersion')
    r.units[202] = {**r.units[101], 'owner': 0, 'alive': True, 'abilities': {}, 'inventory': {}, 'x': 40., 'y': 0.}
    require(r.invoke('tdPetDeployAndRefresh', p, 202), 'Actual rebind failed')
    click(r.invoke('tdPetManagerCommandId', 32), old_display)
    require(display() != old_display and mode() == 7 and balance(r) == 3 and field(r, p, 'proposalVersion') == candidate_version, 'Stale bound-host generation did not refresh only page authority')
    new_display = display()
    click(r.invoke('tdPetManagerCommandId', 32))
    require(balance(r) == 0 and field(r, p, 'proposalType') == 0 and field(r, p, 'generation') >= 2 and field(r, p, 'host') == 202 and field(r, p, 'readyAt') == 88., 'Native fresh confirmation did not commit once')
    require(r.invoke('TDPet_skillAt', p, 0) == 1 and r.invoke('TDPet_qualityAt', p, 0) == 2 and 202 in r.refreshes, 'Native commit skipped skill/host aggregation')
    click(r.invoke('tdPetManagerCommandId', 32), new_display)
    require(balance(r) == 0, 'Retired native manager charged again')
    return {'actual_onCommand_navigation_preview_confirm': True, 'bound_host_generation_old_page_rejected': True, 'candidate_retained_and_new_page_commits': True, 'host_refresh': True, 'native_double_click_charged_once': True, 'preview_current_stock_and_cost': True}


def verify_delta(current, baseline):
    before, after = members(baseline), members(current)
    require(set(before) == set(after), 'Learning added/removed packaged media')
    changed = []
    for name in before:
        path, data = after[name]
        require(path == before[name][0], 'Resource name spelling changed')
        old = before[name][1]
        if data != old: changed.append(path)
        if path == 'war3map.w3i': require(normalize_info(data, expected_base_name='契灵守卫战') == normalize_info(old, expected_base_name='契灵守卫战'), 'Map info changed beyond build timestamp')
        elif path not in ('war3map.j', 'war3map.w3a', '(listfile)', '(attributes)'):
            require(data == old, 'Unrelated resource/object table changed: ' + path)
    a, b = ability_objects(after['war3map.w3a'][1]), ability_objects(before['war3map.w3a'][1])
    expected = {f'Pm{i:02X}' for i in range(15, 25)} | {f'Pn{i:02X}' for i in range(49) if i in {*range(4), *range(5, 9), 11, 12, *range(16, 19), 20, 24, 28, 32, 36, *range(39, 49)}}
    require(set(a) - set(b) == expected and not (set(b) - set(a)) and len(expected) == 38, 'Learning object delta is not exactly 38')
    verify_directed_objects(a)
    differences = {}
    for raw in b:
        require(a[raw][0] == b[raw][0], 'Old ability parent changed: ' + raw)
        fields = {key for key in set(a[raw][1]) | set(b[raw][1]) if a[raw][1].get(key) != b[raw][1].get(key)}
        if not fields: continue
        allowed = {'aub1'} if raw in ('Pc06', 'Pm0E') else set()
        require(all(key[0] in allowed for key in fields), 'Unrelated old ability changed: ' + raw + '/' + str(fields))
        differences[raw] = sorted(key[0] for key in fields)
    return {'additional_abilities': 38, 'fixed_green_choice_objects': 28, 'new_manager_commands': 10, 'per_cell_variant_library': 0, 'old_ability_field_changes': differences, 'changed_members': changed, 'all_other_members_identical': True}


def verify_mutations(script, abilities):
    reports = []
    changes = [
        ('random_free_adoption', 'tdPetResolveRerollVersion',
         lambda body: re.sub(r' or TDPet_proposalType\[[^\]]+\] != TDPetState_TD_PET_PROPOSAL_RANDOM', '', body, count=1),
         'legacy entrance accepted directed candidate'),
        ('duplicate_payment', 'tdPetResolveDirectedVersion',
         lambda body: re.sub(r'(?m)^(\s*set TDPetState_tdPetRerollStones\[[^\]]+\] = TDPetState_tdPetRerollStones\[[^\]]+\] - TDPetCultivation_TD_PET_DIRECTED_COST)$', r'\1\n\1', body, count=1),
         'Wrong exact payment'),
    ]
    for label, name, transform, expected_error in changes:
        matched = jass_function(script, name)
        body = matched.group(1)
        changed = transform(body)
        require(changed != body, 'Mutation did not reach actual packed owner: ' + label)
        mutated = script[:matched.start(1)] + changed + script[matched.end(1):]
        try:
            verify_transactions(mutated)
        except ValueError as error:
            require(expected_error in str(error), 'Mutation failed for an unrelated fixture reason: ' + str(error))
            reports.append({'mutation': label, 'rejected_by_same_transaction_oracle': str(error)})
        else:
            raise ValueError('Packed mutation was not detected: ' + label)
    from copy import deepcopy
    corrupt = deepcopy(abilities)
    fields = corrupt['Pn00'][1]
    fields['Ncl6', 2, 6] = fields['Ncl6', 1, 6]
    try:
        verify_directed_objects(corrupt)
    except ValueError as error:
        require('residual second-level fields' in str(error), 'Second-level mutation failed for unrelated reasons')
        reports.append({'mutation': 'residual_level_two', 'rejected_by_same_object_oracle': str(error)})
    else:
        raise ValueError('Residual-level mutation was not detected')
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only', action='store_true')
    parser.add_argument('--map', type=Path)
    parser.add_argument('--baseline-map', type=Path)
    parser.add_argument('--source-baseline', default=BASELINE)
    args = parser.parse_args()
    result = {'source': verify_source(args.source_baseline)}
    if not args.source_only:
        require(args.map is not None and args.baseline_map is not None, 'Packed replay requires current and frozen baseline maps')
        archive, baseline = Mpq(args.map.read_bytes()), Mpq(args.baseline_map.read_bytes())
        script = archive.extract('war3map.j').decode()
        result.update(sha256=hashlib.sha256(args.map.read_bytes()).hexdigest(), transactions=verify_transactions(script), pages=verify_pages(script, ability_objects(archive.extract('war3map.w3a'))), native_bridge=verify_native_bridge(script), delta=verify_delta(archive, baseline), mutations=verify_mutations(script, ability_objects(archive.extract('war3map.w3a'))))
    result['boundary'] = 'Actual packed production transactions/pages run; engine native handles, input/timer/RNG delivery modeled; Warcraft rendering, load time and FPS not tested.'
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
