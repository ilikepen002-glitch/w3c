#!/usr/bin/env python3
"""Conservative packaged-resource inventory, with an explicit retired-icon proof.

All non-image/audio MPQ payloads (JASS, object data, MDX TEXS, MDL, SLK,
FDF, TOC and unrecognized formats) are roots: treating even orphan models as
roots avoids deleting a texture whose model was not recognized. Import/list
metadata is inventory, not usage. Wurst source adds dynamic string-family
prefix evidence; unresolved assets are reported and retained, never deleted.
Only the reviewed three retired portrait families are deletion-authorized.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects

ROOT = Path(__file__).resolve().parents[1]
RETIRED_STEMS = ('TDPetFlamePhoenix', 'TDPetStormFaerieDragon', 'TDPetGhostWisp')
MEDIA = {'.blp', '.tga', '.png', '.jpg', '.jpeg', '.mp3', '.wav', '.ogg'}
METADATA = {'(listfile)', '(attributes)', 'war3map.imp'}


def normalize(data):
    return re.sub(rb'\\+', rb'\\', data.lower().replace(b'/', b'\\'))


def retired_names():
    suffixes = ['', *(f'Q{q}' for q in range(1, 5)),
                *(f'Q{q}N{n}' for q in range(1, 5) for n in range(1, 5))]
    return {prefix + stem + suffix + '.blp' for stem in RETIRED_STEMS
            for suffix in suffixes for prefix in
            ('war3mapImported\\BTN', 'ReplaceableTextures\\CommandButtonsDisabled\\DISBTN')}


def audit(path, root=ROOT, require_retired_absent=False):
    data = Path(path).read_bytes()
    mpq = Mpq(data)
    names = mpq.extract('(listfile)').decode().splitlines()
    imports = {p.relative_to(root / 'imports').as_posix().replace('/', '\\')
               for p in (root / 'imports').rglob('*') if p.is_file()}
    resources = sorted(set(names) - METADATA)
    roots = {name: normalize(mpq.extract(name)) for name in resources
             if Path(name).suffix.lower() not in MEDIA}
    source = b'\n'.join(p.read_bytes() for p in (root / 'wurst').rglob('*.wurst'))
    roots['Wurst source including dynamic string fragments'] = normalize(source)
    # Double-quoted literals are conservative dynamic prefix roots, not proofs
    # of usage. A short fragment deliberately cannot justify deletion.
    literals = [v for v in re.findall(rb'"([^"\r\n]*)"', normalize(source)) if len(v) >= 6]
    reached, unresolved = [], []
    for name in resources:
        if name not in imports and Path(name).suffix.lower() not in MEDIA:
            continue
        canonical = normalize(name.encode())
        normal = canonical.replace(b'commandbuttonsdisabled\\disbtn', b'commandbuttons\\btn')
        # Imported BTN files also have implicit DISBTN siblings.
        imported = b'war3mapimported\\' + normal.rsplit(b'\\', 1)[-1]
        basename = normal.rsplit(b'\\', 1)[-1]
        evidence = [owner for owner, payload in roots.items()
                    if owner != name and any(key in payload for key in (canonical, normal, imported, basename))]
        if not evidence:
            evidence = ['conservative dynamic literal prefix' for value in literals
                        if value in canonical or value in normal or value in imported]
        record = {'path': name, 'packed_bytes': mpq.blocks[mpq.block_index(name)][1],
                  'raw_bytes': len(mpq.extract(name))}
        if evidence:
            record['evidence'] = sorted(set(evidence)); reached.append(record)
        else:
            unresolved.append(record)
    allowed = retired_names()
    # Stronger proof for the explicit deletion set: no legacy family token
    # may occur in any root, including dynamic fragments and all model data.
    for stem in RETIRED_STEMS:
        for owner, payload in roots.items():
            if stem.lower().encode() in payload:
                raise ValueError(f'Retired family {stem} still referenced by {owner}')
    present = sorted(allowed & set(names))
    if require_retired_absent and present:
        raise ValueError(f'{len(present)} retired portrait resources still packaged')
    abilities = ability_objects(mpq.extract('war3map.w3a'))
    retired_ids = (4, 9, 10, 13, 14, 15)
    for position in range(2):
        for skill in retired_ids:
            if f'Ps{position * 49 + skill:02X}' in abilities:
                raise ValueError('Retired skill preview object still present')
    for slot in range(4):
        for skill in retired_ids:
            for variant in (skill, skill + 49):
                if f's{slot}{variant:02X}' in abilities:
                    raise ValueError('Retired skill slot object still present')
    return {'map_sha256': hashlib.sha256(data).hexdigest(), 'map_bytes': len(data),
            'listed_members': len(names), 'conservative_root_count': len(roots),
            'retired_icon_members': len(present),
            'retired_icon_packed_bytes': sum(mpq.blocks[mpq.block_index(n)][1] for n in present),
            'retired_icon_raw_bytes': sum(len(mpq.extract(n)) for n in present),
            'retired_preview_objects': 0, 'new_object_savings': 0,
            'retained_with_reference_or_dynamic_evidence': reached,
            'unresolved_retained_except_explicit_retired_allowlist': unresolved,
            'authorized_retired_paths': sorted(allowed),
            'scope': 'Conservative roots include every model and unknown non-media payload; unresolved resources remain. Native game dependencies are not bundled-resource deletions.'}


def verify_tooltip_delta(old, new):
    before = ability_objects(old.extract('war3map.w3a'))
    after = ability_objects(new.extract('war3map.w3a'))
    if before.keys() != after.keys():
        raise ValueError('Ability identities changed during resource retirement')
    changes = []
    for raw, (parent, fields) in before.items():
        new_parent, new_fields = after[raw]
        if parent != new_parent or fields.keys() != new_fields.keys():
            raise ValueError('Ability structure changed: ' + raw)
        for field, value in fields.items():
            if value == new_fields[field]:
                continue
            if raw not in ('Ps30', 'Ps61', 's230', 's261') or field[0] != 'aub1' or field[1] not in (1, 2, 3, 4):
                raise ValueError('Unexpected ability field change: ' + raw + str(field))
            expected = (45, 72, 99, 126)[field[1] - 1]
            original, current = value[1], new_fields[field][1]
            pattern = r'各受[0-9.]+法术伤害'
            if f'各受{expected}法术伤害' not in current or re.sub(pattern, '各受#法术伤害', original) != re.sub(pattern, '各受#法术伤害', current):
                raise ValueError('Unexpected epidemic description change: ' + raw)
            changes.append({'rawcode': raw, 'field': field, 'damage': expected})
    if len(changes) != 16:
        raise ValueError('Expected exactly 16 epidemic quality tooltip fields')
    for name in ('war3map.w3u', 'war3map.w3t', 'war3map.w3h', 'war3map.w3e', 'war3map.wpm', 'war3map.doo', 'war3mapUnits.doo'):
        if old.has(name) != new.has(name) or (old.has(name) and old.extract(name) != new.extract(name)):
            raise ValueError('Unrelated object/terrain member changed: ' + name)
    return {'ability_count': len(before), 'ability_ids_unchanged': True,
            'changed_tooltip_fields': changes, 'other_ability_fields_identical': True,
            'unit_item_buff_terrain_pathing_bytes_identical': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path)
    p.add_argument('--require-retired-absent', action='store_true')
    p.add_argument('--output', type=Path)
    p.add_argument('--baseline', type=Path, help='Verify every retained media/model payload is byte-identical')
    args = p.parse_args()
    report = audit(args.map, require_retired_absent=args.require_retired_absent)
    if args.baseline:
        old = Mpq(args.baseline.read_bytes())
        new = Mpq(args.map.read_bytes())
        before = set(old.extract('(listfile)').decode().splitlines())
        after = set(new.extract('(listfile)').decode().splitlines())
        removed = before - after
        if removed != retired_names() or after - before:
            raise ValueError('Archive member delta is not exactly the 126 retired icons')
        protected = [n for n in after if Path(n).suffix.lower() in MEDIA | {'.mdx', '.mdl', '.fdf', '.toc', '.slk'}]
        for name in protected:
            if old.extract(name) != new.extract(name):
                raise ValueError('Retained resource bytes changed: ' + name)
        report['object_delta'] = verify_tooltip_delta(old, new)
        report['retained_payloads_byte_identical'] = len(protected)
        report['net_map_bytes_saved'] = args.baseline.stat().st_size - args.map.stat().st_size
    result = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(result)
    print(json.dumps({k: v for k, v in report.items() if not isinstance(v, list)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
