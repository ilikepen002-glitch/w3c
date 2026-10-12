"""Explicit current40 verifier shapes plus opt-in real candidate MPQ mutations.

Controlled items test checker semantics only. Actual objects are never synthesized
for a packaging claim; EQUIPMENT_CANDIDATE_MAP enables the actual-MPQ group.
"""
from copy import deepcopy
from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from ReadEquipmentCatalog import catalog
from VerifyPlayerTooltipArtifact import verify_current_items, validate
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerPlacementArtifact import unit_objects
from GenerateTowerTerrainMask import Mpq


def controlled_items():
    grammar = {
        'ATTACK': '攻击 +{}', 'RANGE': '射程 +{}（上限500）',
        'ATTACK_SPEED': '攻速 +{}%', 'COOLDOWN': '冷却时间缩短{}%',
        'KILL_GOLD': '击杀金币 +{}', 'ARMOR_SHRED': '护甲降低{}',
        'EXECUTE': '普攻命中生命值不高于50%的主目标时，追加本次普攻伤害的{}%',
        'POISON': '每秒{}伤害', 'CONTROL_POWER': '眩晕时间提高{}%（上限60%）',
        'DROP_BONUS': '额外抽取{}次',
        'BOSS_DAMAGE': '普攻命中首领或金币试炼主目标时，追加本次普攻伤害的{}%',
    }
    percent = {'ATTACK_SPEED', 'COOLDOWN', 'EXECUTE', 'CONTROL_POWER', 'BOSS_DAMAGE'}
    aura = {'ATTACK': '静态基础攻击的{}%', 'ATTACK_SPEED': '攻速光环：标称攻击速度 +{}%载体上限120%',
            'COOLDOWN': '冷却光环：嗜血、剑刃风暴与精灵主动技能冷却缩短{}%；合计上限40%，不刷新已开始的冷却',
            'ARMOR_ON_HIT': '普攻主目标破甲{}', 'ENEMY_SLOW': '敌方移动减速光环：标称减速{}%；总上限75%'}
    specials = {
        'ARCHER_ARROW': '额外增加1支副箭',
        'WAR_INTENT': '4次主普攻击中；攻速 +20%持续3秒，爆发中不叠层不续时',
        'CORPSE_BURST': '每6次有效主普攻击中触发本击事件伤害50%的范围伤害，范围180，最多4个活目标；每目标法抗只计算一次，副箭与毒伤不回灌',
        'POISON_BURST': '每3次有效主普攻击中触发本击事件伤害50%的范围伤害，范围220，最多4个活目标；每目标法抗只计算一次，副箭与毒伤不回灌',
        'SHIELD_SPREAD': '以主目标为中心200范围内额外扩散最多2名非首领；首领不额外硬控，仅装备破甲4',
    }
    result = {}
    for entry in catalog():
        parts = []
        for kind, value in ((entry.primary, entry.primary_value), (entry.secondary, entry.secondary_value)):
            if kind != 'NONE':
                parts.append(grammar[kind].format(int(value * (100 if kind in percent else 1) + .5)))
                if kind in ('EXECUTE', 'BOSS_DAMAGE'):
                    parts.append('与半血追加比例相加；法术、分裂箭和精灵伤害不生效。普攻击杀时不再追加。')
        if entry.aura != 'NONE':
            parts.append(aura[entry.aura].format(int(entry.aura_value * (1 if entry.aura == 'ARMOR_ON_HIT' else 100) + .5)))
            parts.append(f'光环范围{entry.aura_radius:g}，不受装备射程影响；同光环仅最高等级生效，异名光环可叠加。')
            if entry.aura != 'ENEMY_SLOW':
                parts.append('作用于本玩家本路合法塔，包含自己。')
        if entry.specialization != 'NONE':
            parts.append(specials[entry.specialization])
        parts.append('同塔不能重复装备同名物品；前3格三件同品质装备，同名确定下一阶，混名随机下一品质，紫装不能合成。')
        result[entry.rawcode] = {'unam': entry.name, 'utub': '|n'.join(parts)}
    return result


class ControlledCurrentItemsTests(unittest.TestCase):
    def setUp(self):
        self.items = controlled_items()
        self.assertEqual(verify_current_items(self.items), 40)

    def test_all_forty_numeric_aura_and_admission_rules_pass_controlled_shape(self):
        self.assertEqual(len(self.items), 40)

    def test_missing_or_wrong_last_identity_is_rejected(self):
        for uid in ('iW10', 'iP10'):
            items = deepcopy(self.items); del items[uid]
            with self.subTest(uid=uid), self.assertRaisesRegex(ValueError, 'equipment identity set mismatch'):
                verify_current_items(items)
        items = deepcopy(self.items); items['iP11'] = items.pop('iP10')
        with self.assertRaisesRegex(ValueError, 'equipment identity set mismatch'):
            verify_current_items(items)

    def test_each_personal_numeric_field_is_checked(self):
        for entry in catalog():
            if entry.primary == 'NONE' and entry.secondary == 'NONE':
                continue
            items = deepcopy(self.items)
            # Change the first primary/secondary numeric token, preserving the
            # complete identity matrix and all unrelated admission phrases.
            import re
            text = items[entry.rawcode]['utub']
            changed = re.sub(r'\d+', lambda m: str(int(m[0]) + 1), text, count=1)
            self.assertNotEqual(changed, text)
            items[entry.rawcode]['utub'] = changed
            with self.subTest(uid=entry.rawcode), self.assertRaisesRegex(ValueError, entry.rawcode):
                verify_current_items(items)

    def test_each_aura_value_radius_and_shared_cap_are_checked(self):
        for uid, old, new in (('iP07', '静态基础攻击的12%', '静态基础攻击的13%'),
                             ('iP10', '光环范围550', '光环范围500'),
                             ('iP10', '总上限75%', '总上限85%'),
                             ('iP08', '合计上限40%', '合计上限50%')):
            self.assertEqual(self.items[uid]['utub'].count(old), 1)
            items = deepcopy(self.items); items[uid]['utub'] = items[uid]['utub'].replace(old, new, 1)
            with self.subTest(uid=uid, mutation=new), self.assertRaisesRegex(ValueError, uid):
                verify_current_items(items)

    def test_wrong_name_and_old_duplicate_or_crafting_phrase_are_checked(self):
        items = deepcopy(self.items); items['iP02']['unam'] = '旧武器'
        with self.assertRaisesRegex(ValueError, 'iP02: config name mismatch'):
            verify_current_items(items)
        for phrase in ('同塔不能重复装备同名物品', '同名确定下一阶', '混名随机下一品质'):
            items = deepcopy(self.items); items['iP02']['utub'] = items['iP02']['utub'].replace(phrase, '', 1)
            with self.subTest(phrase=phrase), self.assertRaisesRegex(ValueError, 'crafting/admission rule missing'):
                verify_current_items(items)


class ActualCurrentTooltipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get('EQUIPMENT_CANDIDATE_MAP')
        if not path:
            raise unittest.SkipTest('EQUIPMENT_CANDIDATE_MAP is required for current40 actual-MPQ proof')
        cls.map = Mpq(Path(path).read_bytes())
        cls.a = ability_objects(cls.map.extract('war3map.w3a'))
        cls.u = unit_objects(cls.map.extract('war3map.w3u'))
        cls.i = unit_objects(cls.map.extract('war3map.w3t'))
        cls.count = validate(cls.a, cls.u, cls.i)

    def mutate_text(self, uid, level, old, new, reason):
        a = deepcopy(self.a)
        text = a[uid][1]['aub1', level, 0][1]
        self.assertEqual(text.count(old), 1, uid + ': nonunique/missing actual-MPQ mutation needle')
        a[uid][1]['aub1', level, 0] = 3, text.replace(old, new, 1)
        with self.assertRaisesRegex(ValueError, reason):
            validate(a, self.u, self.i)

    def test_actual_packaged_current40_all_tooltips(self):
        self.assertGreater(self.count, 900)

    def test_actual_last_control_poison_level_cannot_restore_native_move_or_stale_text(self):
        a = deepcopy(self.a); a['A106'][1]['Spo2', 61, 2] = 2, .352
        with self.assertRaisesRegex(ValueError, 'A106/61: native poison move double application'):
            validate(a, self.u, self.i)
        self.mutate_text('A106', 61, '35.2%', '22%', 'A106/61')

    def test_actual_last_bash_proc_and_shared_window_remain_checked(self):
        a = deepcopy(self.a); a['A113'][1]['Hbh1', 61, 1] = 2, 26.4
        with self.assertRaisesRegex(ValueError, 'A113/61: disabled native bash Hbh1'):
            validate(a, self.u, self.i)
        self.mutate_text('A113', 61, '26.4%', '22%', 'A113/61')
        self.mutate_text('A104', 61, '普通敌人眩晕0.9秒', '普通敌人眩晕1秒', 'A104/61')
        self.mutate_text('A104', 61, '不同塔共享每名敌人的盾击窗口', '独立窗口', 'shared shield window')

    def test_actual_last_equipment_cooldown_stays_checked(self):
        self.mutate_text('A131', 41, '7.2秒', '12秒', 'A131/41')

    def test_actual_pet_host_only_and_85_nominal_75_total_slow_are_checked(self):
        self.mutate_text('s010', 1, '仅附身宿主', '全队所有塔', 's010')
        self.mutate_text('s03F', 1, '降低85%', '降低75%', 's03F')
        self.mutate_text('s03F', 1, '总上限75%', '总上限85%', 'pet slow total cap')

    def test_actual_missing_current_item_and_wrong_trial_percent_are_checked(self):
        items = deepcopy(self.i); del items['iP10']
        with self.assertRaisesRegex(ValueError, 'equipment identity set mismatch'):
            validate(self.a, self.u, items)
        items = deepcopy(self.i)
        old = '普攻命中首领或金币试炼主目标时，追加本次普攻伤害的25%'
        self.assertEqual(items['iP02']['utub'].count(old), 1)
        items['iP02']['utub'] = items['iP02']['utub'].replace(old, old.replace('25%', '45%'), 1)
        with self.assertRaisesRegex(ValueError, 'iP02'):
            validate(self.a, self.u, items)
        items = deepcopy(self.i)
        old = '普攻命中生命值不高于50%的主目标时，追加本次普攻伤害的20%'
        self.assertEqual(items['iB02']['utub'].count(old), 1)
        items['iB02']['utub'] = items['iB02']['utub'].replace(old, '普攻命中首领或金币试炼主目标时，追加本次普攻伤害的25%', 1)
        with self.assertRaisesRegex(ValueError, 'iB02'):
            validate(self.a, self.u, items)

    def test_actual_map_cannot_enter_legacy72_profile(self):
        from trial_formal72_fixture import Formal72SourceFixture
        frozen = Formal72SourceFixture(); self.addCleanup(frozen.cleanup)
        with self.assertRaisesRegex(ValueError, 'expected 28 gear texts'):
            validate(self.a, self.u, self.i, profile='legacy72', source_root=frozen.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
