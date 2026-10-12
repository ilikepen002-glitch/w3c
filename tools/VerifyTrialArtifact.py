#!/usr/bin/env python3
"""Read-only checks of the actual packaged trial unit and icon bytes.

Native installation data is optional and reported separately. Wurst asset
constants are never treated as proof that a target installation has a model.
This does not compile, alter an MPQ, or launch Warcraft III.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifySemanticIconArtifact import parse_objects, decode_blp

UNIT = 'uTrG'
MODEL = r'Units\Creeps\GolemStatue\GolemStatue.mdx'
ICON = r'war3mapImported\BTNTDTrialGoldGolem.blp'
DISABLED = r'ReplaceableTextures\CommandButtonsDisabled\DISBTNTDTrialGoldGolem.blp'
ICONS = {ICON: '5095926333d0e730aa9195cc25a5ee13800abb885ca96c0a8eb0a2813cc2be4f',
         DISABLED: '5acaa9f091a83f87b91e83b6b101191955167f1b7de3b39d9b2497c07e43f911'}
# Object editor setters supply all inherited gameplay-sensitive overrides.
EXPECTED = {'unam': '金币试炼魔像', 'umdl': MODEL, 'uico': ICON, 'ussi': ICON,
            'uclr': 255, 'uclg': 220, 'uclb': 120, 'uhpm': 1000000,
            'udef': 0, 'udup': 0, 'udty': 'normal', 'uabi': '', 'udaa': '',
            'utyp': '', 'utar': 'ground', 'upgr': '', 'umvs': 260,
            'umis': 1, 'umas': 260, 'umvt': 'foot', 'uaen': 0,
            'uacq': 0.0, 'ucol': 0.0, 'ubba': 0, 'ubdi': 0, 'ubsi': 0,
            'ulba': 0, 'ulbd': 0, 'ulbs': 0, 'upoi': 0, 'udea': 0,
            'uhpr': 0.0, 'uhrt': 'none', 'ufle': 0, 'usle': 0, 'ufoo': 0}

def sha(data): return hashlib.sha256(data).hexdigest()

def verify_unit(objects):
    require(UNIT in objects, 'Packaged trial unit is missing')
    obj = objects[UNIT]
    require(obj.table == 1 and obj.identity == b'narguTrG', 'Trial must be a custom non-hero Battle Golem')
    for name, expected in EXPECTED.items():
        field = obj.fields.get((name, 0, 0))
        require(field is not None, 'Trial inherited override missing: ' + name)
        require(field.value == expected, 'Trial exact field mismatch: ' + name)
        kind = 3 if isinstance(expected, str) else 2 if isinstance(expected, float) else 0
        require(field.kind == kind, 'Trial field kind mismatch: ' + name)
    require(not any(key[0] in {'uhab', 'uhhd', 'uhst', 'uhag', 'uhin'} for key in obj.fields), 'Trial acquired hero properties')
    return {key: obj.fields[(key, 0, 0)].value for key in EXPECTED}

def verify_icons(mpq):
    result = {}
    for path, expected in ICONS.items():
        require(mpq.has(path), 'Trial exact icon path missing: ' + path)
        data = mpq.extract(path)
        require(sha(data) == expected, 'Trial independent approved icon bytes differ: ' + path)
        require(data[:4] == b'BLP1', 'Trial icon is not BLP1')
        compression, alpha, width, height = struct.unpack_from('<4I', data, 4)
        require((compression, alpha, width, height) == (1, 8, 64, 64), 'Trial icon must be 64px palette alpha8')
        offsets = struct.unpack_from('<16I', data, 28)
        sizes = struct.unpack_from('<16I', data, 92)
        end = 1180
        for level, size in enumerate((64, 32, 16, 8, 4, 2, 1)):
            require(offsets[level] == end and sizes[level] == size * size * 2, 'Trial exact complete mip layout differs')
            end += sizes[level]
        require(not any(offsets[7:]) and not any(sizes[7:]) and end == len(data), 'Trial trailing or missing mip data')
        decoded = decode_blp(data, path)
        require(len(decoded) == 7 and decoded[0].size == (64, 64), 'Trial icon decode dimensions differ')
        result[path] = {'sha256': sha(data), 'mips': [64, 32, 16, 8, 4, 2, 1]}
    return result

def verify_equipment_tooltips(mpq, *, profile='current40', source_root=None):
    from VerifyTowerPlacementArtifact import unit_objects
    from VerifyEquipmentAbilityArtifact import ability_objects
    from VerifyPlayerTooltipArtifact import validate, ROOT
    require(profile in ('legacy009', 'current40'), 'Unknown trial tooltip profile')
    items = unit_objects(mpq.extract('war3map.w3t'))
    result = {}
    if profile == 'legacy009':
        rules = (('iB02', 25, '首领或金币试炼'), ('iP02', 45, '首领或金币试炼'))
    else:
        from ReadEquipmentCatalog import catalog
        root = ROOT if source_root is None else Path(source_root)
        definitions = {entry.rawcode: entry for entry in catalog(root)}
        import re
        require({code for code in items if re.fullmatch(r'i[WGBP]\d\d', code)} == set(definitions),
                'current40 equipment identity set mismatch')
        blue, purple = definitions['iB02'], definitions['iP02']
        require((blue.secondary, blue.secondary_value) == ('EXECUTE', .20),
                'Current trial blue equipment source must be half-life 20%')
        require((purple.secondary, purple.secondary_value) == ('BOSS_DAMAGE', .25),
                'Current trial purple equipment source must be Boss/trial 25%')
        rules = (('iB02', 20, '生命值不高于50%的'), ('iP02', 25, '首领或金币试炼'))
    for code, percent, target in rules:
        require(code in items, 'Trial bonus equipment item missing: ' + code)
        expected = '普攻命中' + target + '主目标时，追加本次普攻伤害的' + str(percent) + '%'
        text = items[code].get('utub', '')
        require(text.count(expected) == 1, 'Trial exact tooltip/value mismatch: ' + code)
        require('法术、分裂箭和精灵伤害不生效。普攻击杀时不再追加。' in text,
                'Trial equipment tooltip lost attack eligibility constraints: ' + code)
        if profile == 'current40' and code == 'iB02':
            require('普攻命中首领或金币试炼主目标' not in text,
                    'Trial blue equipment acquired forbidden Boss/trial damage')
        else:
            require('与半血追加比例相加' in text, 'Trial Boss/trial addition rule missing: ' + code)
        result[code] = {'percent': percent, 'required_text': expected}
    # Always validate the real objects. Historical source and map are supplied
    # together; no old-item view, prefix waiver, or auto-detected fallback.
    checked = validate(ability_objects(mpq.extract('war3map.w3a')),
                       unit_objects(mpq.extract('war3map.w3u')), items,
                       profile=profile, source_root=source_root)
    return {'profile': profile, 'equipment_bonus_texts': result,
            'player_tooltip_numeric_cases': checked,
            'view': 'Actual packed objects checked against the explicit matching source profile'}

def verify_installation(archives):
    if not archives:
        return {'status': 'NOT_VERIFIED', 'reason': 'No actual target 1.28 installation archives supplied',
                'model': MODEL, 'attack_type_table': 'NOT_VERIFIED'}
    found, evidence = {}, []
    for path in archives:
        data = Path(path).read_bytes(); archive = Mpq(data)
        evidence.append({'path': str(Path(path).resolve()), 'sha256': sha(data)})
        for resource in (MODEL, r'Units\MiscData.txt'):
            if archive.has(resource): found[resource] = archive.extract(resource)
    require(MODEL in found and len(found[MODEL]) > 4 and found[MODEL][:4] == b'MDLX', 'Actual installation native model missing/invalid')
    require(r'Units\MiscData.txt' in found, 'Actual installation attack type table missing')
    table = found[r'Units\MiscData.txt'].decode('utf-8-sig')
    rows = {}
    for line in table.splitlines():
        if line.startswith('DamageBonus') and '=' in line:
            name, values = line.split('=', 1)
            try: rows[name] = [float(value.strip()) for value in values.split(',')]
            except ValueError: raise ValueError('Invalid actual attack type table row ' + name)
    require(rows and all(len(values) == 8 for values in rows.values()), 'Actual attack type table incomplete')
    require(all(0 <= value <= 2 for values in rows.values() for value in values), 'Actual attack type multiplier exceeds bounded source assumption')
    return {'status': 'PASS', 'archives': evidence, 'model_sha256': sha(found[MODEL]),
            'misc_data_sha256': sha(found[r'Units\MiscData.txt']), 'attack_type_rows': rows,
            'version_boundary': 'Archive identity/version must be externally confirmed as the target 1.28 installation'}

def verify(path, archives=(), *, profile='current40', source_root=None):
    data = Path(path).read_bytes(); mpq = Mpq(data)
    return {'status': 'PASS', 'map': str(Path(path).resolve()), 'map_sha256': sha(data),
            'jass_sha256': sha(mpq.extract('war3map.j')),
            'unit': verify_unit(parse_objects(mpq.extract('war3map.w3u'), False)),
            'icons': verify_icons(mpq), 'equipment_tooltips': verify_equipment_tooltips(mpq, profile=profile, source_root=source_root), 'native_installation': verify_installation(archives),
            'boundary': 'No native gameplay, visuals, FPS, or arbitrary future equipment damage guarantee'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map'); parser.add_argument('--installation-archive', action='append', default=[])
    parser.add_argument('--output')
    parser.add_argument('--profile', choices=('legacy009', 'current40'), default='current40')
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args(); result = verify(args.map, args.installation_archive, profile=args.profile, source_root=args.source_root)
    result['command'] = __import__('sys').argv
    if args.output: Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__ == '__main__': main()
