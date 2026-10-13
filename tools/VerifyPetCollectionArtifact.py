#!/usr/bin/env python3
"""Verify quality-only collection assets/rules; optionally replay an actual map.
No build, native Warcraft, load-time or FPS claims are made by this verifier.
"""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import tarfile
from BuildElementalPetUiAssets import verify as verify_ui_assets
from VerifyPetManagerSource import scalar_helpers, compile_source_helper, source, function_body, verify_scalar_contracts
from VerifyEquipmentAbilityArtifact import require, ability_objects
from VerifyPetUIArtifact import verify_manager_list, verify_elemental_resources
from VerifyGroundItemArtifact import verify_list_channel_families
from GenerateTowerTerrainMask import Mpq

ROOT = Path(__file__).resolve().parents[1]


def source_contract():
    n = scalar_helpers()
    verify_scalar_contracts(n)
    for name, arity in [('tdPetReleaseGetsSlotStone', 2), ('tdPetQualityForRoll', 1), ('tdPetSkillCountForRoll', 1)]:
        compile_source_helper(source('TDPetRules'), name, n, arity)
    for count, roll in itertools.product(range(1, 5), range(0, 102)):
        require(n['tdPetReleaseGetsSlotStone'](roll, count) == (1 <= roll <= (5 if count == 3 else 2)), 'Release chance boundary changed')
    for roll in range(1, 101):
        require(n['tdPetQualityForRoll'](roll) == (1 if roll <= 45 else 2 if roll <= 75 else 3 if roll <= 95 else 4), 'Per-slot quality distribution changed')
        require(n['tdPetSkillCountForRoll'](roll) == (2 if roll <= 55 else 3 if roll <= 90 else 4), 'Capture count distribution changed')
    ids = set()
    for cell in range(10):
        ids.add(n['tdPetListAbilityId'](cell, 0, 0, 0))
        for species, quality in itertools.product(range(1, 16), range(1, 5)):
            variants = {n['tdPetListAbilityId'](cell, species, quality, count) for count in range(1, 5)}
            require(len(variants) == 1, 'Skill count still changes the collection object')
            ids.update(variants)
    require(len(ids) == 610, 'Expected exactly 610 collection objects')
    objects, session, state = source('TDPetObjectGen'), source('TDPetUIState'), source('TDPetState')
    require('tdPetSpeciesQualityIconPath(species, quality)' in objects and 'tdPetSpeciesCountIconPath' not in objects, 'Collection references count badge')
    require('current.skillCount == listOwnedCounts[cell]' in session, 'Removed count stale guard')
    require('"技能 · 共鸣Lv"' in state, 'Count missing from pet detail summary')
    release = function_body(state, 'tdPetConfirmRelease')[1]
    require('var extra = pet.quality() == 4' in release and 'tdPetReleaseGetsSlotStone(GetRandomInt(1, 100), pet.skillCount)' in release, 'Release must use live composite quality and owned count')
    require(release.index('tdPetCancelRelease(lane)') < release.index('var extra') < release.index('tdPetDiscardOwned(lane, slot)') < release.index('tdPetRerollStones[lane] += 1'), 'Release atomic order changed')
    verify_ui_assets()
    archive_dir = ROOT / 'assets/source/elemental-spirits/archive'
    archived = json.loads((archive_dir / 'count-ui-manifest.json').read_text())['assets']
    require(len(archived) == 240, 'Missing archived count portraits')
    paths = {a[key]: a[key+'Sha256'] for a in archived for key in ('normal', 'disabled')}
    with tarfile.open(archive_dir / 'count-ui-imports.tar.xz') as archive:
        require(set(archive.getnames()) == set(paths), 'Archive does not preserve exact 480 retired files')
        for path, digest in paths.items():
            require(not (ROOT / path).exists(), 'Retired icon still in imports: ' + path)
            require(hashlib.sha256(archive.extractfile(path).read()).hexdigest() == digest, 'Retired archive SHA differs: ' + path)
    for q, count in itertools.product(range(1, 5), range(1, 5)):
        require((ROOT / f'assets/source/pet-ui/TDPetFlamePhoenixQ{q}N{count}.svg').is_file(), 'Lost original count/frame template')
    print('PASS COLLECTION SOURCE: 610 stable sparse objects; 1,280 quality cases; 408 reward boundaries; 150 live + 480 archived BLPs')


def owned(r, count, quality=1):
    p = r.invoke('new_TDPet', 0, 1, 1)
    for slot, skill in enumerate((0, 5, 6, 11)[:count]):
        r.invoke('TDPet_setSkill', p, slot, skill, quality)
    require(r.invoke('tdPetStore', 0, p), 'Fixture record was not stored')
    return p


def replay(script):
    from VerifyPetFourSlotArtifact import FourSlotRuntime
    # Actual compiled helpers, not reimplemented runtime state.
    r = FourSlotRuntime(script)
    # Match setup excludes inactive lanes in the harness; initialize this owner explicitly.
    r.invoke('tdPetInitializeLane', 0)
    for count, qualities in itertools.product(range(5), itertools.product(range(1, 5), repeat=4)):
        r.executed_steps = 0
        expected = max((4 if count == 4 else 3 if count == 3 else 1, *qualities[:count]))
        require(r.invoke('tdPetOwnedQuality', count, *qualities) == expected, 'Packed composite quality mismatch')
    for count, quality, roll in itertools.product((1, 2, 3, 4), (1, 4), (1, 2, 3, 5, 6, 100)):
        r.executed_steps = 0
        p = owned(r, count, quality)
        r.globals['TDPetState_tdPetRerollStones'][0] = 0
        r.globals['TDPetState_tdPetSlotStones'][0] = 0
        r.int_trace.clear()
        purple = count == 4 or quality == 4
        r.roll_queue = [] if purple else [roll]
        nonce = r.invoke('tdPetBeginRelease', 0, 0)
        require(nonce > 0 and r.invoke('tdPetConfirmRelease', 0, nonce), 'Valid release rejected')
        expected = purple or roll <= (5 if count == 3 else 2)
        require(r.globals['TDPetState_tdPetRerollStones'][0] == 1 and r.globals['TDPetState_tdPetSlotStones'][0] == int(expected), 'Packed reward differs')
        trace = r.int_trace.copy()
        require(len(trace) == (0 if purple else 1) and not r.roll_queue, 'Guaranteed release drew RNG or random release drew twice')
        require(not r.invoke('tdPetConfirmRelease', 0, nonce), 'Duplicate nonce accepted')
        require(r.globals['TDPetState_tdPetRerollStones'][0] == 1 and r.globals['TDPetState_tdPetSlotStones'][0] == int(expected) and trace == r.int_trace, 'Duplicate release paid or rolled again')
    # Capture, opening, candidate keep/adopt and resonance locking use live quality.
    for count_roll, count in ((1, 2), (56, 3), (91, 4)):
        r.executed_steps = 0
        p = r.invoke('new_TDPet', 0, 1, 1)
        r.roll_queue = [count_roll, 1, 0, 1, 0] + ([1, 1, 0] if count >= 3 else []) + ([1, 51] if count == 4 else [])
        require(r.invoke('TDPet_rollCaptureSkills', p), 'Capture failed')
        require(r.invoke('TDPet_quality', p) == (1 if count == 2 else count), 'Initial capture quality mismatch')
        require(all(r.invoke('TDPet_qualityAt', p, i) == 1 for i in range(count)), 'Composite quality changed slot strengths')
        r.invoke('dispatch_TDPet_destroyTDPet', p)
    p = owned(r, 2)
    r.globals['TDPetState_tdPetSlotStones'][0] = 2
    for draws, quality in (([1, 1, 0], 3), ([1, 51], 4)):
        r.executed_steps = 0
        r.roll_queue = draws.copy()
        require(r.invoke('tdPetOpenSlot', 0, 0) and r.invoke('TDPet_quality', p) == quality, 'Opening failed to update composite quality')
    require(r.globals['TDPet_level'][p] == 1 and r.globals['TDPetState_tdPetSlotStones'][0] == 0, 'Opening changed locked resonance or charged incorrectly')
    require(not r.invoke('tdPetOpenSlot', 0, 0), 'Full record consumed another stone')
    r.invoke('tdPetDiscardOwned', 0, 0)
    p = owned(r, 3)
    r.globals['TDPetState_tdPetRerollStones'][0] = 2
    for adopt in (False, True):
        r.executed_steps = 0
        r.roll_queue = [96, 0]
        require(r.invoke('tdPetBeginReroll', 0, 0, 0), 'Reroll failed')
        require(r.invoke('TDPet_quality', p) == 3, 'Unconfirmed candidate changed composite quality')
        version = r.globals['TDPet_proposalVersion'][p]
        require(r.invoke('tdPetResolveRerollVersion', 0, 0, version, adopt), 'Candidate resolution failed')
        require(r.invoke('TDPet_quality', p) == (4 if adopt else 3), 'Confirmed/kept quality mismatch')
    print('PASS COLLECTION REPLAY: 1,280 quality cases; 48 reward cases; duplicate nonces; capture/open/keep/adopt with locked skills')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', nargs='?', type=Path)
    args = parser.parse_args()
    source_contract()
    if args.map:
        artifact = Mpq(args.map.read_bytes())
        abilities = ability_objects(artifact.extract('war3map.w3a'))
        verify_manager_list(abilities)
        require(len(verify_list_channel_families(abilities)) == 610, 'Wrong packed list object budget')
        verify_elemental_resources(artifact)
        replay(artifact.extract('war3map.j').decode('utf-8'))
        print('MAP SHA256:', hashlib.sha256(args.map.read_bytes()).hexdigest())
    else:
        print('NOT RUN: Wurst checks/build, packed-map replay, native Warcraft or timing measurements')


if __name__ == '__main__':
    main()
