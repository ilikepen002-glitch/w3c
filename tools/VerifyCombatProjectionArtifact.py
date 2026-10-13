#!/usr/bin/env python3
"""Replay production packed projection guards. Controlled natives, never FPS evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyAuraPerfArtifact import fixture, refresh, state
from VerifyEquipmentAbilityArtifact import require
from VerifyEquipmentCombatReplay import close
from VerifyTowerUpgradeArtifact import rawcode


def verify(script):
    r = fixture(script)
    results = {}
    control = rawcode('AdPo')
    # Helper accepts any native id; presence and current rank are native boundaries.
    r.units[101]['abilities'][control] = 7
    def control_sync(level):
        before = Counter(r.calls)
        r.invoke('tdEquipmentSyncControl', 101, control, level)
        return (Counter(r.calls) - before)['SetUnitAbilityLevel']
    require(control_sync(7) == 0, 'Stable control level rewrote the native')
    require(control_sync(9) == 1 and r.units[101]['abilities'][control] == 9,
            'Externally changed control level was not repaired')
    del r.units[101]['abilities'][control]
    require(control_sync(9) == 0 and control not in r.units[101]['abilities'],
            'Missing tower control ability was invented')
    r.units[101]['abilities'][control] = 2
    require(control_sync(9) == 1, 'Re-added native ability was not repaired')
    results['control'] = ['stable no write', 'external rank repaired', 'missing stays missing', 're-added repaired']

    refresh(r, 101)
    expected_range = r.units[101]['acquireRange']
    before = Counter(r.calls); refresh(r, 101)
    require((Counter(r.calls)-before)['SetUnitAcquireRange'] == 0, 'Stable acquisition rewrote the native')
    r.units[101]['acquireRange'] = expected_range + 77.0
    before = Counter(r.calls); refresh(r, 101)
    close(r.units[101]['acquireRange'], expected_range, 'External acquisition value repair')
    require((Counter(r.calls)-before)['SetUnitAcquireRange'] == 1, 'Acquisition repair omitted native write')
    results['acquisition'] = ['stable no write', 'external value repaired', 'full projected range recomputed']

    refresh(r, 1000)
    before = Counter(r.calls); refresh(r, 1000)
    require((Counter(r.calls)-before)['SetUnitMoveSpeed'] == 0, 'Stable enemy speed rewrote the native')
    r.units[1000]['speed'] = 123.0
    before = Counter(r.calls); refresh(r, 1000)
    close(r.units[1000]['speed'], 260.0, 'External enemy speed repair')
    require((Counter(r.calls)-before)['SetUnitMoveSpeed'] == 1, 'Enemy speed repair omitted native write')
    item = 4001
    r.inventory_items[item] = rawcode('iW10'); r.units[101]['inventory'] = {0:item}
    refresh(r, 1000); slowed = r.units[1000]['speed']
    require(slowed < 260.0, 'New slow source did not change speed')
    before = Counter(r.calls); refresh(r, 1000)
    require((Counter(r.calls)-before)['SetUnitMoveSpeed'] == 0, 'Stable slow speed rewrote the native')
    r.units[101]['inventory'] = {}; refresh(r, 1000)
    close(r.units[1000]['speed'], 260.0, 'Removed slow source did not restore speed')
    results['speed'] = ['stable no write', 'external value repaired', 'source added', 'stable slow no write', 'source removed']
    require(not r.notices, 'Production aura try failed during projection checks')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('map', type=Path)
    args = parser.parse_args(); data = args.map.read_bytes()
    script = Mpq(data).extract('war3map.j').decode()
    print(json.dumps({'map_sha256': hashlib.sha256(data).hexdigest(), 'checks': verify(script),
                      'boundary': 'Production JASS executed; native actual values modeled. No engine/FPS claim.'}, indent=2))

if __name__ == '__main__': main()
