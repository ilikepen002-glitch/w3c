#!/usr/bin/env python3
"""Inspect actual packaged tower objects/pathing, not only Wurst constants.
Usage: python3 tools/VerifyTowerPlacementArtifact.py ExampleMap.w3x
"""
import re
import struct
import sys
from pathlib import Path
from GenerateTowerTerrainMask import Mpq, ROOT, MAP_PATH, TGA_PATH


def unit_objects(data):
    version, = struct.unpack_from('<I', data)
    assert version == 2, f'Unsupported W3U version {version}'
    offset = 4
    objects = {}
    for _ in range(2):
        count, = struct.unpack_from('<I', data, offset)
        offset += 4
        for _ in range(count):
            parent, new_id = data[offset:offset+4], data[offset+4:offset+8]
            fields_count, = struct.unpack_from('<I', data, offset + 8)
            offset += 12
            fields = {}
            for _ in range(fields_count):
                key = data[offset:offset+4].decode('ascii')
                kind, = struct.unpack_from('<I', data, offset + 4)
                offset += 8
                if kind == 3:
                    end = data.index(0, offset)
                    value = data[offset:end].decode('utf-8')
                    offset = end + 1
                else:
                    assert kind in (0, 1, 2)
                    value, = struct.unpack_from('<i' if kind == 0 else '<f', data, offset)
                    offset += 4
                offset += 4  # End marker rawcode.
                fields[key] = value
            objects[(new_id if new_id != b'\0'*4 else parent).decode('ascii')] = fields
    assert offset == len(data)
    return objects


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    source = Mpq((ROOT / MAP_PATH).read_bytes())
    for name in ('war3map.w3e', 'war3map.wpm'):
        assert artifact.extract(name) == source.extract(name), f'Packaged {name} changed'
    texture = artifact.extract('war3mapImported\\TDTower192.tga')
    assert texture == (ROOT / TGA_PATH).read_bytes()
    assert len(texture) == 126 and texture[2] == 2
    assert struct.unpack_from('<HHB', texture, 12) == (6, 6, 24)
    assert texture[18:] == bytes((255, 0, 255)) * 36
    catalog = (ROOT / 'wurst/towers/TDTowerCatalogData.wurst').read_text()
    ids = re.findall(r"public constant int TD_(?:ARCHER|ORC|FOOT|DRYAD|GHOUL)_LEVEL_[A-Z0-9_]+_ID = '(.{4})'", catalog)
    assert len(ids) == 35 and len(set(ids)) == 35
    objects = unit_objects(artifact.extract('war3map.w3u'))
    for tower in ids:
        obj = objects[tower]
        assert obj['ubdg'] == 1, (tower, 'not explicitly a building')
        assert obj['upat'] == 'war3mapImported\\TDTower192.tga', (tower, 'wrong pathing')
        # Actual 1.27a Units/UnitMetaData.slk: upap=preventPlace,
        # upar=requirePlace. The pre1.29 Wurst wrapper names are reversed.
        assert obj['upap'] == 'unbuildable,unwalkable,water', (tower, 'wrong placement filter (upap/preventPlace)')
        assert obj['upar'] == '', (tower, 'unexpected required terrain (upar/requirePlace)')
        assert obj['ucol'] == 96.0, (tower, 'wrong collision')
        assert obj['ufoo'] == 1, (tower, 'wrong population cost')
    farmer = objects['uF01']
    assert farmer['umvt'] == 'fly', 'Worker access regressed'
    base_ids = [f'u{family}11' for family in 'AOH DG'.replace(' ', '')]
    assert set(farmer['ubui'].split(',')) == set(base_ids), 'Build menu changed'
    jass = artifact.extract('war3map.j').decode('utf-8')
    assert 'TD_TOWER_FOOTPRINT_SIZE' in jass and 'tdTerrainCellBuildable' in jass
    assert 'toTileCenter' not in jass, 'Unexpected 128-unit placement snapping remains'
    assert 'tdBuildPlotClaims' not in jass and 'tdTowerBuildPlotSlots' not in jass
    assert re.search(r'set\s+TDConfig_TD_ENEMY_PLAYER_ID\s*=\s*4\b', jass), 'Enemy-owner fix missing'
    for hook in ('EVENT_PLAYER_UNIT_CONSTRUCT_START', 'EVENT_PLAYER_UNIT_CONSTRUCT_CANCEL', 'EVENT_PLAYER_UNIT_UPGRADE_FINISH'):
        assert hook in jass, f'{hook} not wired'
    print('PASS: 35/35 tower variants: explicit building, 192 footprint, collision96, placement filters, food1.')
    print('PASS: actual 6x6 magenta TGA, identical source W3E/WPM, five-entry flying-worker build menu.')
    print('PASS: packaged static mask and construction/cancel/upgrade hooks; no obsolete plot claims or128 snapping; enemy owner4 retained.')
    print('NOT TESTED: Warcraft native preview, construction/refund/population lifecycle and playability.')


if __name__ == '__main__':
    main()
