#!/usr/bin/env python3
"""Exact formal72 -> trial source, MPQ, object and generated JASS delta.

A proposed contract can be captured for review, but it is never accepted by
verification until its SHA is embedded in this tool after independent review.
No diagnostics, callbacks, globals, aliases or compiler adaptations are erased.
Every changed function has exact before/after hashes and full text in the
reviewed contract; untouched functions and MPQ resources are byte-preserved.
The older pure-Boss oracle is deliberately not imported or widened here.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyDamageRankingJass import functions
from VerifySemanticIconArtifact import parse_objects
from VerifyGlobalRankingsArtifact import members, normalize_info, OBJECTS
from VerifyTrialArtifact import UNIT, ICONS, verify_unit, verify_icons

ROOT = Path(__file__).resolve().parents[1]
BASE = '72b2c9c3406868d33969c087dd5e6015abc3ac7b'
BASE_MAP_SHA = 'be13ef7b9f7c2144a7feedbef88c79802b4c3e034e8336933e8f808735937d80'
# Astra independent exact-template approval 2026-10-12; no semantic self-approval.
REVIEWED_CONTRACT_SHA = '144aab9d9c31f08f1eea33d90f4f3ce64b71ae2a13bbaf36292057097492f1cf'
SOURCE_OWNERS = {'TDInit.wurst', 'TDHud.wurst', 'TDSpawn.wurst',
    'damage/TDDamageRuntime.wurst', 'items/TDEquipmentCombat.wurst', 'items/TDItemData.wurst',
    'pets/TDPetRuntime.wurst', 'pets/TDPetCombat.wurst', 'pets/TDPetState.wurst', 'towers/TDTowerRuntime.wurst'}
TRIAL_OWNERS = {f'trial/TDTrial{name}.wurst' for name in
    ('Rules', 'Score', 'State', 'Targets', 'LifeRules', 'RouteRules', 'ObjectGen', 'Identity', 'Runtime', 'Hook', 'Hud')}


def sha(data): return hashlib.sha256(data).hexdigest()
def digest_text(text): return sha(text.encode('utf-8'))
def git_blob(path): return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)

def formal_sources():
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, '--', 'wurst'], cwd=ROOT).decode().splitlines()
    return {name.removeprefix('wurst/'): git_blob(name) for name in names if name.endswith('.wurst') and '/_tests/' not in name}

def current_sources(path):
    path = Path(path); path = path / 'wurst' if (path / 'wurst').is_dir() else path
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in sorted(path.rglob('*.wurst')) if '_tests' not in p.relative_to(path).parts}

def source_delta(current, before):
    require(not set(before) - set(current), 'Formal source deleted')
    added = set(current) - set(before)
    require(added <= TRIAL_OWNERS, 'Unexpected new production owner: ' + repr(sorted(added - TRIAL_OWNERS)))
    changed = {name for name in before if current[name] != before[name]}
    require(changed <= SOURCE_OWNERS, 'Uncontrolled existing production owner: ' + repr(sorted(changed - SOURCE_OWNERS)))
    require({'trial/TDTrialHook.wurst', 'trial/TDTrialRuntime.wurst', 'trial/TDTrialIdentity.wurst'} <= added, 'Production trial owner missing')
    return {'added': {name: sha(current[name]) for name in sorted(added)},
            'changed': {name: {'before_sha256': sha(before[name]), 'after_sha256': sha(current[name]),
                             'before': before[name].decode(), 'after': current[name].decode()} for name in sorted(changed)},
            'preserved': {name: sha(before[name]) for name in sorted(set(before) - changed)}}

def object_delta(current, before):
    result = {}
    for filename, extended in OBJECTS.items():
        require(current.has(filename) == before.has(filename), 'Object archive presence changed: ' + filename)
        if not current.has(filename): continue
        old = parse_objects(before.extract(filename), extended)
        new = parse_objects(current.extract(filename), extended)
        added, deleted = set(new) - set(old), set(old) - set(new)
        require(not deleted and added == ({UNIT} if filename == 'war3map.w3u' else set()), 'Uncontrolled object identity set: ' + filename)
        require([code for code in new if code not in added] == list(old), 'Inherited object order changed: ' + filename)
        changed = {}
        for code in old:
            a, b = new[code], old[code]
            require((a.table, a.identity, list(a.fields)) == (b.table, b.identity, list(b.fields)), 'Inherited object structure changed: ' + code)
            fields = {repr(key): {'before_raw': b.fields[key].raw.hex(), 'after_raw': a.fields[key].raw.hex(),
                                'before_value': b.fields[key].value, 'after_value': a.fields[key].value}
                      for key in b.fields if b.fields[key] != a.fields[key]}
            if fields:
                # Item tooltip-only changes require a separately frozen rawcode
                # and exact field byte contract. Any other object delta fails.
                require(filename == 'war3map.w3t' and all(key[0] in {'utip', 'utub'} for key in b.fields if b.fields[key] != a.fields[key]), 'Unrelated object field changed: ' + code)
                changed[code] = fields
        if added: verify_unit(new)
        result[filename] = {'added': {code: sha(new[code].encoded()) for code in sorted(added)},
                            'changed': changed, 'preserved_count': len(old) - len(changed)}
    return result

def archive_delta(current, before):
    a, b = members(current), members(before)
    added, deleted = set(a) - set(b), set(b) - set(a)
    require(not deleted and added == {path.casefold() for path in ICONS}, 'Uncontrolled MPQ membership delta')
    permitted = {'war3map.j', 'war3map.w3u', 'war3map.w3t', 'war3map.w3i', 'war3map.imp', '(listfile)', '(attributes)'}
    changed = {}
    for name in sorted(set(a) & set(b)):
        if a[name][1] == b[name][1]: continue
        require(name in permitted, 'Uncontrolled MPQ resource change: ' + name)
        if name == 'war3map.w3i': require(normalize_info(a[name][1]) == normalize_info(b[name][1]), 'Map info changed outside published timestamp')
        changed[name] = {'before_sha256': sha(b[name][1]), 'after_sha256': sha(a[name][1])}
    verify_icons(current)
    return {'added': {name: sha(a[name][1]) for name in sorted(added)}, 'changed': changed,
            'preserved': {name: sha(b[name][1]) for name in sorted(set(b) - set(changed))}}

def jass_delta(current, before):
    a, b = functions(current), functions(before)
    require(len(a) == len(__import__('re').findall(r'^function ', current, __import__('re').M)), 'Duplicate candidate JASS function')
    added, deleted = set(a) - set(b), set(b) - set(a)
    changed = {name for name in set(a) & set(b) if a[name][0] != b[name][0]}
    # Changed inherited compiler dispatches are reviewed as exact templates,
    # never masked by owner prefixes or broad diagnostic/type normalization.
    return {'added': {name: {'sha256': digest_text(a[name][0]), 'text': a[name][0]} for name in sorted(added)},
            'deleted': {name: {'sha256': digest_text(b[name][0]), 'text': b[name][0]} for name in sorted(deleted)},
            'changed': {name: {'before_sha256': digest_text(b[name][0]), 'after_sha256': digest_text(a[name][0]),
                              'before': b[name][0], 'after': a[name][0]} for name in sorted(changed)},
            'preserved': {name: digest_text(b[name][0]) for name in sorted(set(b) - changed - deleted)},
            'before_complete_sha256': digest_text(before), 'after_complete_sha256': digest_text(current)}

def verify_current_manager(source):
    """Current manager checks survive the separately frozen historical oracle.

    Only the old wild-byte scope delegates to this gate's exact source proof;
    scalar identity, transactions, authority, cooldown and asset checks run on
    the current trial source. Manager packages not listed in SOURCE_OWNERS are
    additionally byte-identical to immutable formal72.
    """
    import contextlib
    import io
    import VerifyPetManagerSource as manager
    root = Path(source).resolve()
    if root.name == 'wurst': root = root.parent
    require(root == ROOT, 'Current manager proof requires this repository source root')
    with contextlib.redirect_stdout(io.StringIO()) as capture:
        manager.verify_scalar_contracts()
        manager.verify_wiring(verify_legacy_wild_scope=False)
        manager.verify_assets()
    return {'status': 'PASS', 'checks': capture.getvalue().splitlines(),
            'wild_scope': 'Exact full formal72 -> trial source contract; no old wild oracle widening'}


def build_contract(map_path, source):
    data = Path(map_path).read_bytes(); old_data = git_blob('ExampleMap.w3x')
    require(sha(old_data) == BASE_MAP_SHA, 'Formal72 baseline map bytes differ')
    current, before = Mpq(data), Mpq(old_data)
    script, old_script = current.extract('war3map.j').decode(), before.extract('war3map.j').decode()
    return {'schema': 'formal72-trial-exact-v1', 'baseline_commit': BASE, 'baseline_map_sha256': BASE_MAP_SHA,
            'candidate_map_sha256': sha(data), 'source': source_delta(current_sources(source), formal_sources()),
            'archive': archive_delta(current, before), 'objects': object_delta(current, before),
            'jass': jass_delta(script, old_script), 'current_manager': verify_current_manager(source)}

def verify_contract(actual, reviewed):
    require(actual == reviewed, 'Exact independently reviewed trial contract differs')
    return {'status': 'PASS', 'baseline_commit': BASE, 'map_sha256': actual['candidate_map_sha256'],
            'source_owners': sorted(set(actual['source']['added']) | set(actual['source']['changed'])),
            'jass_added': len(actual['jass']['added']), 'jass_changed': len(actual['jass']['changed']),
            'jass_deleted': len(actual['jass']['deleted']), 'jass_preserved': len(actual['jass']['preserved']),
            'objects': actual['objects'], 'archive_changed': sorted(actual['archive']['changed']),
            'boundary': 'Exact approved bytes; gameplay semantics require separate production replay and Astra review'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map'); parser.add_argument('--source', default=ROOT / 'wurst')
    parser.add_argument('--reviewed-contract'); parser.add_argument('--capture-proposed-contract'); parser.add_argument('--output')
    args = parser.parse_args(); actual = build_contract(args.map, args.source)
    if args.capture_proposed_contract:
        require(not args.reviewed_contract and not args.output, 'Capture is separate from verification')
        data = (json.dumps(actual, ensure_ascii=False, indent=2) + '\n').encode()
        Path(args.capture_proposed_contract).write_bytes(data)
        print(json.dumps({'status': 'PROPOSED_ONLY_NOT_PASS', 'contract_sha256': sha(data), 'path': args.capture_proposed_contract})); return
    require(args.reviewed_contract, 'An independently reviewed exact trial contract is required')
    data = Path(args.reviewed_contract).read_bytes()
    require(sha(data) == REVIEWED_CONTRACT_SHA, 'Contract lacks pinned independent review approval')
    result = verify_contract(actual, json.loads(data)); result['command'] = __import__('sys').argv
    result['tool_sha256'] = sha(Path(__file__).read_bytes()); result['contract_sha256'] = sha(data)
    if args.output: Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__ == '__main__': main()
