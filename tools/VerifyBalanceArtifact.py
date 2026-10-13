"""Verify scaled combat/economy and v1.28 difficulty life carriers in a built MPQ.

This reads the candidate only; it does not compile or launch Warcraft III.
"""
from pathlib import Path
import math
import re
import sys
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, check_ability, require
from VerifyTowerPlacementArtifact import unit_objects

NORMAL_HP = [90,120,150,190,190,320,340,300,250,380,560,360,430,660,470,520,
             520,560,760,600,820,620,850,760,720,780,1050,900,980,1020,1250,1100]
SPECIAL_HP = {4:760,8:3200,12:1400,16:6800,20:2700,24:19000,28:5200,32:36000}
GUARD_HP = {8:850,16:1900,24:3600,32:6600}


def verify(path):
    mpq = Mpq(Path(path).read_bytes())
    units = unit_objects(mpq.extract('war3map.w3u'))
    abilities = ability_objects(mpq.extract('war3map.w3a'))
    script = mpq.extract('war3map.j').decode('utf-8')
    checked = 0
    for wave, old_hp in enumerate(NORMAL_HP, 1):
        require(units[f'uE{wave:02X}']['uhpm'] == old_hp * 4, f'Wave {wave}: normal HP')
        for role, hp in ((0, old_hp * 4), (1, SPECIAL_HP.get(wave, 0) * 5),
                         (2, GUARD_HP.get(wave, 0) * 5)):
            if hp == 0:
                continue
            for difficulty, tenths in ((2, 3), (3, 7), (4, 12)):
                index = (wave - 1) * 3 + difficulty - 2
                rawcode = f'D{chr(ord("h") + role)}{index:02X}'
                check_ability(abilities, rawcode, 'AIl2', 1, 'Ilif', 0,
                              lambda level, hp=hp, tenths=tenths: hp * tenths // 10)
                checked += 1
    for wave, old_hp in SPECIAL_HP.items():
        rawcode = f'uB{wave:02d}' if wave % 8 == 0 else f'uS{wave:02d}'
        require(units[rawcode]['uhpm'] == old_hp * 5, rawcode + ': special HP')
    check_ability(abilities, 'A128', 'AIat', 128, 'Iatt', 0, lambda level: level * 5)
    check_ability(abilities, 'Pbat', 'AIat', 512, 'Iatt', 0, lambda level: level * 5)
    require(units['uA11']['ua1b'] == 120 and units['uA11']['ugol'] == 500,
            'Opening archer combat/economy mismatch')
    require(units['uO6A']['ua1b'] == 1300 and units['uO6A']['ugol'] == 6400,
            'Largest tower combat/economy mismatch')
    require(units['uTrG']['uhpm'] == 5000000, 'Trial protection capacity')
    require(abilities['A130'][1][('alev', 0, 0)][1] == 935, 'Evolution exact kill levels')
    require('达到440击杀' in abilities['A130'][1][('aub1', 441, 0)][1], 'Evolution threshold')
    require(math.isclose(abilities['A112'][1][('Ocr3', 1, 3)][1], 108.0, abs_tol=.001)
            and '追加108伤害' in abilities['A112'][1][('aub1', 1, 0)][1],
            'Evolved critical-strike object/tooltip mismatch')
    create = re.search(r'function tdCreateEnemy\b.*?endfunction', script, re.S)
    max_hp = re.search(r'function unit_getMaxHP\b.*?endfunction', script, re.S)
    require(create is not None and 'tdDifficultyHealthAbilityId' in create[0]
            and 'unit_getMaxHP' in create[0] and max_hp is not None
            and 'UNIT_STATE_MAX_LIFE' in max_hp[0], 'Difficulty attach/refill absent in packaged create')
    require(create[0].index('tdDifficultyHealthAbilityId') < create[0].index('unit_getMaxHP')
            < create[0].index('tdEnemyMechanicRegister'), 'Difficulty applied after mechanics registration')
    require('function tdHandleDifficultyButton takes' in script
            and 'function tdRefreshDifficultyDialog takes' in script
            and 'function tdParseDifficultyCommand' not in script, 'Difficulty dialog entry missing or old chat parser remains')
    mapping = re.search(r'function tdTowerAttackBonusAbilityLevel\b.*?endfunction', script, re.S)
    require(mapping is not None and re.search(r'attack\s*/\s*5(?:\.0*)?', mapping[0]),
            'Packaged equipment attack mapping lost five-point scale')
    refresh = [body for body in re.findall(r'function tdRefreshTowerEquipmentBonuses\w*\b.*?endfunction', script, re.S)
               if 'TD_AURA_EQUIPMENT_ATTACK' in body or 'tdAuraPower' in body]
    require(refresh and any('tdTowerAttackBonusAbilityLevel' in body for body in refresh),
            'Actual equipment + aura runtime bypasses shared level mapping')
    print(f'PASS BALANCE: 32 normal/8 special HP tables, {checked} unique AIl2 carriers, '
          '128/512 attack levels ×5, tower cost/damage, 5m trial and 440-kill evolution.')
    print('NOT VERIFIED: live Warcraft life-carrier effect, multiplayer timing, density FPS or win rates.')


if __name__ == '__main__':
    verify(sys.argv[1])
