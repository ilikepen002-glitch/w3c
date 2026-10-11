"""Verify packaged evolution/aura objects, AI art, and ordinary-build boundaries.
Usage: python tools/VerifyEvolutionArtifact.py ExampleMap.w3x
This proves object/assets output, not gameplay or UI rendering.
"""
from pathlib import Path
import math
import re
import struct
import sys
from GenerateTowerTerrainMask import Mpq, ROOT
from VerifyTowerPlacementArtifact import unit_objects
from VerifyEquipmentAbilityArtifact import ability_objects, require

def main():
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    units = unit_objects(artifact.extract('war3map.w3u'))
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    catalog = (ROOT/'wurst/towers/TDTowerCatalogData.wurst').read_text(encoding='utf-8')
    ids = re.findall(r"public constant int TD_(?:ARCHER|ORC|FOOT|DRYAD|GHOUL)_LEVEL_[A-Z0-9_]+_ID = '(.{4})'", catalog)
    require(len(set(ids)) == 35, 'Expected 35 tower types')
    for uid in ids:
        attached = units[uid]['uabi'].split(',')
        require(attached.count('A130') == 1, f'{uid}: evolution progress must be attached once')
        require('A133' in attached, f'{uid}: sale missing')
    identities = {
        'A': ('Units\\NightElf\\HeroMoonPriestess\\HeroMoonPriestess.mdx', 'BTNHeroMoonPriestess', ['A100,A101','A100','A101']),
        'O': ('Units\\Orc\\HeroBladeMaster\\HeroBladeMaster.mdx', 'BTNHeroBlademaster', ['A102,A103','A102,A131','A102,A132']),
        'H': ('Units\\Human\\HeroPaladin\\HeroPaladin.mdx', 'BTNHeroPaladin', ['A104,A105','A104','A105']),
        'D': ('Units\\NightElf\\HeroKeeperOfTheGrove\\HeroKeeperoftheGrove.mdx', 'BTNKeeperOfTheGrove', ['A106,A110','A106','A110']),
        'G': ('Units\\Undead\\Abomination\\Abomination.mdx', 'BTNAbomination', ['A107,A116','A107','A116']),
    }
    for family, (model,icon,skills) in identities.items():
        for index, suffix in enumerate(['15','6A','6B']):
            uid = 'u'+family+suffix
            fields = units[uid]
            require(fields['umdl'] == model, f'{uid}: hero model mismatch')
            require(fields['uico'] == 'ReplaceableTextures\\CommandButtons\\'+icon+'.blp', f'{uid}: unit icon mismatch')
            require(fields['uabi'].split(',') == skills[index].split(',')+['A118','A133','A130'], f'{uid}: complete skill bar mismatch {fields["uabi"]}')
            require(fields.get('uupt','') == ('u'+family+'6A,u'+family+'6B' if index == 0 else ''), f'{uid}: upgrade chain mismatch')
    # Wave table provides the exact theoretical upper bound (no extra summons).
    max_kills = 538
    for aid, levels, icon, x in [
        ('A130', max_kills + 1, 'BTNMarkOfFire', 2),
        ('AeEV', 3, 'BTNMetamorphosis', 3),
    ]:
        parent, fields = abilities[aid]
        require(parent == 'AOcr', f'{aid}: passive carrier required')
        require(fields[('alev',0,0)] == (0,levels), f'{aid}: wrong level count')
        for field in ['aart','arar']:
            require(fields[(field,0,0)][1] == 'ReplaceableTextures\\CommandButtons\\'+icon+'.blp', f'{aid}: icon mismatch')
        require(fields[('abpx',0,0)][1] == x and fields[('abpy',0,0)][1] == 2, f'{aid}: button slot mismatch')
        for level in range(1,levels+1):
            for field, column, expected in [('Ocr1',1,0.0),('Ocr2',2,1.0),('Ocr3',3,0.0),('Ocr5',5,0)]:
                require(fields[(field,level,column)][1] == expected, f'{aid}/{level}: passive carrier has combat effect')
    progress = abilities['A130'][1]
    for kills in [0,249,250,251,max_kills]:
        require(progress[('atp1',kills+1,0)][1] == f'累计击杀：{kills}', f'Exact count missing: {kills}')
        require(f'本塔累计击杀：{kills}。' in progress[('aub1',kills+1,0)][1], f'Exact hover count missing: {kills}')
        require('达到250击杀' in progress[('aub1',kills+1,0)][1], 'Wrong evolution threshold')
    status = abilities['AeEV'][1]
    require('等待完成6阶' in status[('atp1',1,0)][1], 'Waiting state missing')
    require('已进化' in status[('atp1',2,0)][1], 'Evolved state missing')
    require('名额已用' in status[('atp1',3,0)][1], 'Spent state missing')
    for uid in ids:
        require('AeEV' not in units[uid]['uabi'].split(','), f'{uid}: evolution status appears before kills')
    for aid in ['A102','A112']:
        require(math.isclose(abilities[aid][1][('Ocr1',1,1)][1],25.0,rel_tol=1e-5), f'{aid}: critical probability uses wrong units')
    for aid, expected in [('A101',.18), ('A105',.16), ('A111',.216), ('AeCM',.192)]:
        require(aid in abilities, f'Missing aura {aid}')
        parent, fields = abilities[aid]
        targets = fields[('atar',1,0)][1].split(',')
        require({'friend','structure','invulnerable','vulnerable'} <= set(targets), f'{aid}: aura excludes invulnerable towers')
        require(fields[('alev',0,0)] == (0,1), f'{aid}: implicit hero levels')
        require(fields[('aare',1,0)] == (2,900.0), f'{aid}: wrong aura radius')
        field = 'Ear1' if parent == 'AEar' else 'Cac1'
        value = fields[(field,1,1)][1]
        require(math.isclose(value,expected,rel_tol=1e-5), f'{aid}: wrong aura damage {value}')
    crit = abilities['A112'][1]
    require(math.isclose(crit[('Ocr2',1,2)][1],2.64,rel_tol=1e-5), 'Evolved crit multiplier not +20%')
    require(math.isclose(crit[('Ocr3',1,3)][1],21.6,rel_tol=1e-5), 'Evolved crit bonus not +20%')
    require(math.isclose(abilities['A115'][1][('Isx1',1,1)][1],.504,rel_tol=1e-5), 'Evolved frenzy not +20%')
    require('AeSL' in abilities, 'Missing evolved slow branch')
    for level in range(1,62):
        value = abilities['AeSL'][1][('Slo1',level,1)][1]
        require(math.isclose(value, -min(.70,.216*(1+(level-1)/100)),rel_tol=1e-5), f'AeSL{level}: wrong evolved reduction')
    expected = {'uA6A':'A100','uA6B':'A101','uH6A':'A104','uH6B':'A105','uD6A':'A106','uD6B':'A110','uG6A':'A107','uG6B':'A116'}
    for uid, aid in expected.items():
        require(aid in units[uid]['uabi'].split(','), f'{uid}: branch original missing')
    for path in (ROOT/'imports/war3mapImported').glob('*.blp'):
        require(artifact.extract('war3mapImported\\'+path.name) == path.read_bytes(), f'{path.name}: packaged BLP differs')
    for path in (ROOT/'imports/ReplaceableTextures/CommandButtonsDisabled').glob('DISBTN*.blp'):
        name = 'ReplaceableTextures\\CommandButtonsDisabled\\'+path.name
        require(artifact.extract(name) == path.read_bytes(), f'{path.name}: disabled BLP missing')
    for choice in range(1,6):
        name = f'war3mapImported\\TDEvolutionWings{choice}.mdx'
        data = artifact.extract(name)
        require(data == (ROOT/'imports/war3mapImported'/f'TDEvolutionWings{choice}.mdx').read_bytes(), 'MDX packaging differs')
        require(data[:4] == b'MDLX', 'Invalid MDX magic')
        offset = 4
        texture = None
        while offset < len(data):
            tag, size = data[offset:offset+4], struct.unpack_from('<I',data,offset+4)[0]
            if tag == b'TEXS':
                require(size == 268, 'Expected one wing texture')
                texture = data[offset+12:offset+272].split(b'\0',1)[0].decode('ascii')
            offset += 8+size
        require(texture == 'war3mapImported\\TDEvolutionWings.blp', f'Invalid exact wing texture path {texture!r}')
        require(artifact.extract(texture) == (ROOT/'imports/war3mapImported/TDEvolutionWings.blp').read_bytes(), 'Referenced wing texture missing')
        require(b'Stand' in data, 'Wing Stand animation missing')
    for aid, (parent, fields) in abilities.items():
        if aid in ['A100','A101','A102','A103','A104','A105','A106','A107','A110','A116','A111','A112','A113','A114','A115','A131','A132','AeCM','AeSL']:
            icon = fields.get(('aart',0,0),(None,''))[1]
            require(icon.startswith('war3mapImported\\BTN') and artifact.has(icon), f'{aid}: missing generated icon {icon}')
    for aid in ['A131','A132']:
        off = abilities[aid][1][('auar',0,0)][1]
        require(off.startswith('war3mapImported\\BTN') and artifact.has(off), f'{aid}: autocast off icon missing')
    for aid, (parent, fields) in abilities.items():
        for (field, level, column), (kind, value) in fields.items():
            if field in ['aart','arar','auar'] and isinstance(value,str) and 'war3mapImported' in value:
                require(value.startswith('war3mapImported\\'), f'{aid}/{field}: prefixed custom icon {value}')
                require(artifact.has(value), f'{aid}/{field}: icon cannot be extracted {value}')
                require(artifact.extract(value), f'{aid}/{field}: empty resource')
    script = artifact.extract('war3map.j').decode('utf-8')
    for forbidden in ['tdHandleTowerRefineCast','tdStartPerfectUpgradeAvatarRefresher','TDNativeSplitArrowProfileProbe','PET-SKILLS','SPLIT queued=','TDNative']:
        require(forbidden not in script, f'Normal map contains retired mechanism/probe {forbidden}')
    print('PASS: 35 tower progress attachments; exact539-level statistics and separate3-state evolution; invulnerable900-range auras; branch objects; 11 BTN/DISBTN and wing resources; no retired runtime/native probes.')
    print('NOT TESTED: native aura benefit, automatic evolution, wings attachment/occlusion, FPS, balance or exit dialog in game.')

if __name__ == '__main__':
    main()
