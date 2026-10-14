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
from VerifyTowerUpgradeArtifact import validate_upgrade_artifact, validate_evolution_jass, EXPECTED_TOWERS, HIDDEN, check_command_conflicts, field_value
from VerifySlowAbilityArtifact import validate_slow_abilities

def validate_branch_displays(units, abilities):
    for aid in ['A100', 'A116']:
        parent, fields = abilities[aid]
        require(parent == 'AOcr', f'{aid}: display carrier must inherit neutral critical strike')
        levels = 3 if aid == 'A116' else 2
        require(fields.get(('alev', 0, 0)) == (0, levels), f'{aid}: expected normal/evolved display levels')
        for level in range(1, levels + 1):
            for field, column, expected in [('Ocr1', 1, 0.0), ('Ocr2', 2, 1.0), ('Ocr3', 3, 0.0), ('Ocr5', 5, 0)]:
                require(fields.get((field, level, column), (None, None))[1] == expected, f'{aid}/{level}: display carrier has combat effect')
    split = abilities['A100'][1]
    require('7' in split[('aub1', 1, 0)][1], 'Normal split display must describe six-tier seven targets')
    require(all(word in split[('aub1', 2, 0)][1] for word in ['7', '20%', '额外', '主箭', '不变']), 'Evolved split display does not match extra-arrow-only gain')
    require('180' in abilities['A116'][1][('aub1', 1, 0)][1], 'Normal corpse display must describe 180 damage')
    require('324' in abilities['A116'][1][('aub1', 2, 0)][1], 'Evolved corpse display must describe 324 damage')
    require('270' in abilities['A116'][1][('aub1', 3, 0)][1], 'Blood corpse display must describe 270 damage')
    for level, damage in [(1, '180'), (2, '324'), (3, '270')]:
        text = abilities['A116'][1][('aub1', level, 0)][1]
        require(text == '普攻击杀敌人时，若其攻击前生命值|n不高于25%，触发尸爆。|n对周围220范围内其他本路敌人|n造成' + damage + '伤害。',
                f'A116/{level}: current corpse effect/condition/line breaks mismatch')
    for uid in ['uA6A', 'uA6B']:
        require('7' in units[uid].get('utub', '') + units[uid].get('uube', ''), f'{uid}: final split tooltip does not describe seven targets')


def validate_evolution_action_commands(abilities):
    require('AeEC' in abilities, 'Evolution chooser object missing')
    chooser_fields = abilities['AeEC'][1]
    require(chooser_fields.get(('alev',0,0)) == (0,1), 'Evolution chooser must have exactly one physical level')
    require(all(level in (0,1) for field,level,column in chooser_fields),
            'Evolution chooser has residual fields above its declared level')
    require(field_value(abilities, 'AeEC', 'ahky') == 'R', 'Evolution chooser must not conflict with E combat skill')
    order = field_value(abilities, 'AeEC', 'Ncl6', 1, 6)
    require(order and all(order != field_value(abilities, aid, 'Ncl6', 1, 6) for aid in ('A133', 'Pdep')),
            'Evolution chooser must use a distinct native Channel order')
    require(field_value(abilities, 'AeEC', 'Ncl2', 1, 2) == 0, 'Evolution chooser must be an own-tower instant action')
    for uid, attached in EXPECTED_TOWERS.items():
        if uid[2] != '6':
            continue
        commands = [("native stop", (1, 0), "S"), ("native attack", (3, 0), "A")]
        # Qualified, unevolved terminal cards show the action instead of AeEV.
        for aid in attached + ['AeEC']:
            if aid not in HIDDEN:
                commands.append((aid, (field_value(abilities, aid, 'abpx'), field_value(abilities, aid, 'abpy')),
                                 field_value(abilities, aid, 'ahky', default='')))
        check_command_conflicts(uid, commands)


def validate_tower_aura_carriers(abilities):
    # The frozen third-batch map uses script routing, then exactly one self
    # carrier per identity/rank. The visible source cannot range-double-apply.
    for code, parent, bonus in [('A101', 'AEar', 'Ear1'), ('A111', 'AEar', 'Ear1'),
                                ('A105', 'AIcd', 'Cac1'), ('AeCM', 'AIcd', 'Cac1')]:
        actual_parent, fields = abilities[code]
        require(actual_parent == parent, code + ': aura source parent changed')
        require(fields['alev', 0, 0] == (0, 1), code + ': aura source levels changed')
        require(fields['atar', 1, 0] == (3, 'self') and fields['abuf', 1, 0] == (3, ''),
                code + ': aura source may double-apply')
        require(fields['aare', 1, 0] == (2, 900.0) and fields[bonus, 1, 1] == (2, 0.0),
                code + ': aura source radius/native power changed')
    for label, rank, parent, bonus, values, buff in [
            ('白虎', 1, 'AEar', 'Ear1', (.18, .20), 'BM01'),
            ('白虎', 2, 'AEar', 'Ear1', (.216, .24), 'BM02'),
            ('统帅', 1, 'AIcd', 'Cac1', (.16, .18), 'BM03'),
            ('统帅', 2, 'AIcd', 'Cac1', (.192, .216), 'BM04')]:
        matches = [(code, p, f) for code, (p, f) in abilities.items()
                   if f.get(('anam', 0, 0)) == (3, label + '百分比载体 ' + str(rank))]
        require(len(matches) == 1, label + ': missing/duplicate rank carrier')
        code, actual_parent, fields = matches[0]
        require(actual_parent == parent and fields['alev', 0, 0] == (0, 2), code + ': rank carrier identity changed')
        require(fields['abpx', 0, 0] == (0, 0) and fields['abpy', 0, 0] == (0, -11), code + ': rank carrier must stay hidden')
        for level, value in enumerate(values, 1):
            require(fields['atar', level, 0] == (3, 'self') and fields['abuf', level, 0] == (3, buff),
                    code + ': rank carrier target/Buff changed')
            require(fields['aare', level, 0] == (2, 0.0), code + ': rank carrier radius changed')
            kind, actual = fields[bonus, level, 1]
            require(kind == 2 and math.isclose(actual, value, rel_tol=1e-6, abs_tol=1e-7),
                    code + ': rank carrier percentage changed')


def validate_production_script_boundary(script):
    for forbidden in ['tdHandleTowerRefineCast', 'tdStartPerfectUpgradeAvatarRefresher',
                      'TDNativeSplitArrowProfileProbe', 'PET-SKILLS', 'SPLIT queued=']:
        require(forbidden not in script, f'Normal map contains retired mechanism/probe {forbidden}')
    # TDNativeActiveCooldown is the real production CDR class, not a probe.
    require(not re.search(r'\b\w*TDNative\w*Probe\w*\b', script),
            'Normal map contains native diagnostic probe')


def validate_evolution_artifact(units, abilities, artifact):
    validate_upgrade_artifact(units, abilities, artifact)
    validate_slow_abilities(abilities)
    catalog = (ROOT/'wurst/towers/TDTowerCatalogData.wurst').read_text(encoding='utf-8')
    ids = re.findall(r"public constant int TD_(?:ARCHER|ORC|FOOT|DRYAD|GHOUL)_LEVEL_[A-Z0-9_]+_ID = '(.{4})'", catalog)
    require(len(set(ids)) == 35, 'Expected 35 tower types')
    for uid in ids:
        attached = units[uid]['uabi'].split(',')
        require(attached.count('A130') == 1, f'{uid}: evolution progress must be attached once')
        require('A133' in attached, f'{uid}: sale missing')
    # Wave table provides the exact theoretical upper bound (no extra summons).
    max_kills = 934
    for aid, levels, icon, x in [
        ('A130', max_kills + 1, 'BTNMarkOfFire', 2),
        ('AeEV', 4, 'BTNMetamorphosis', 3),
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
    for kills in [0,439,440,441,max_kills]:
        require(progress[('atp1',kills+1,0)][1] == f'累计击杀：{kills}', f'Exact count missing: {kills}')
        require(f'本塔累计击杀：{kills}。' in progress[('aub1',kills+1,0)][1], f'Exact hover count missing: {kills}')
        require('击杀仅作统计' in progress[('aub1',kills+1,0)][1] and '440' not in progress[('aub1',kills+1,0)][1].split('。', 1)[1], 'Kill count still unlocks evolution')
    status = abilities['AeEV'][1]
    require('第24波' in status[('atp1',1,0)][1], 'Wave-24 locked state missing')
    require('等待完成6阶' in status[('atp1',2,0)][1], 'Waiting state missing')
    require('已进化' in status[('atp1',3,0)][1], 'Evolved state missing')
    require('本路名额已用' in status[('atp1',4,0)][1], 'Lane spent state missing')
    parent, choose = abilities['AeEC']
    require(parent == 'ANcl', 'Evolution chooser must be a dedicated Channel action')
    require(choose[('abpx',0,0)][1] == 3 and choose[('abpy',0,0)][1] == 2, 'Evolution chooser must share exclusive status slot')
    require(choose[('acdn',1,0)][1] == 0.0 and '本路第24波' in choose[('aub1',1,0)][1], 'Evolution action contract changed')
    for uid in ids:
        require('AeEV' not in units[uid]['uabi'].split(','), f'{uid}: evolution status must be runtime-owned')
    for aid in ['A102','A112']:
        require(math.isclose(abilities[aid][1][('Ocr1',1,1)][1],25.0,rel_tol=1e-5), f'{aid}: critical probability uses wrong units')
    validate_tower_aura_carriers(abilities)
    crit = abilities['A112'][1]
    require(math.isclose(crit[('Ocr2',1,2)][1],2.64,rel_tol=1e-5), 'Evolved crit multiplier not +20%')
    require(math.isclose(crit[('Ocr3',1,3)][1],108.0,rel_tol=1e-5), 'Evolved crit bonus not +20%')
    require(math.isclose(abilities['A115'][1][('Isx1',1,1)][1],.504,rel_tol=1e-5), 'Evolved frenzy not +20%')
    require('AeSL' in abilities, 'Missing evolved slow branch')
    for level in range(1,62):
        value = abilities['AeSL'][1][('Slo1',level,1)][1]
        require(value == 0.0, f'AeSL{level}: native slow duplicates shared runtime control')
    validate_branch_displays(units, abilities)
    validate_evolution_action_commands(abilities)
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
        if aid in ['A100','A101','A102','A103','A104','A105','A106','A107','A110','A116','A111','A112','A113','A114','A115','A131','A132','AeCM','AeSL','A140','A141']:
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
    validate_evolution_jass(script, units, abilities)
    validate_production_script_boundary(script)


def main():
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    units = unit_objects(artifact.extract('war3map.w3u'))
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    validate_evolution_artifact(units, abilities, artifact)
    print('PASS: 35 tower progress attachments; exact935-level statistics and four-state lane evolution with exclusive chooser; 900-range zero-effect aura sources and exact self/rank percentage carriers; 35 inherited skill bars and ten Jass evolution sets; branch-only scalar multipliers; two-level zero-effect displays; BTN/DISBTN and wing resources; no retired runtime/native probes.')
    print('NOT TESTED: native aura benefit, evolution dialog interaction, wings attachment/occlusion, FPS, balance or exit dialog in game.')

if __name__ == '__main__':
    main()
