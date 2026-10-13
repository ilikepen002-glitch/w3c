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
        'EXECUTE': '主目标生命不高于50%时，普攻追加{}%',
        'POISON': '每秒{}伤害', 'CONTROL_POWER': '眩晕时间提高{}%（上限60%）',
        'DROP_BONUS': '额外抽取{}次',
        'BOSS_DAMAGE': '普攻对首领或金币试炼主目标追加{}%',
    }
    percent = {'ATTACK_SPEED', 'COOLDOWN', 'EXECUTE', 'CONTROL_POWER', 'BOSS_DAMAGE'}
    aura = {'ATTACK': '增加基础攻击的{}%', 'ATTACK_SPEED': '攻速光环：攻击速度 +{}%与装备攻速合计上限120%',
            'COOLDOWN': '冷却光环：嗜血、剑刃风暴及精灵主动冷却缩短{}%；合计上限40%，不重置进行中的冷却',
            'ARMOR_ON_HIT': '普攻主目标破甲{}', 'ENEMY_SLOW': '本路敌人移动速度降低{}%；合计上限75%'}
    specials = {
        'ARCHER_ARROW': '额外增加1支副箭',
        'WAR_INTENT': '同目标4次普攻命中；攻速 +20%持续3秒，期间不叠层、不续时；换目标或停攻3秒清除层数',
        'CORPSE_BURST': '每6次普攻命中，对目标周围180范围内最多4名敌人，造成本次普攻伤害的50%；副箭、毒伤不计次数',
        'POISON_BURST': '每3次普攻命中，对目标周围220范围内最多4名敌人，造成本次普攻伤害的50%；副箭、毒伤不计次数；须同一目标，换目标或停攻3秒清除次数',
        'SHIELD_SPREAD': '目标周围200范围内最多2名非首领；首领只受破甲4，持续3秒，不受额外眩晕',
    }
    result = {}
    for entry in catalog():
        parts = []
        for kind, value in ((entry.primary, entry.primary_value), (entry.secondary, entry.secondary_value)):
            if kind != 'NONE':
                parts.append(grammar[kind].format(int(value * (100 if kind in percent else 1) + .5)))
                if kind in ('EXECUTE', 'BOSS_DAMAGE'):
                    parts.append('仅主目标普攻；半血与首领追加比例相加。法术、副箭、精灵伤害不触发；普攻击杀不追加。')
        if entry.aura != 'NONE':
            parts.append(aura[entry.aura].format(int(entry.aura_value * (1 if entry.aura == 'ARMOR_ON_HIT' else 100) + .5)))
            parts.append(f'光环范围{entry.aura_radius:g}，不受装备射程影响；同名取最高等级，异名可叠加。')
            if entry.aura != 'ENEMY_SLOW':
                parts.append('仅本路己方塔，含自身。')
        if entry.specialization != 'NONE':
            parts.append(specials[entry.specialization])
        parts.append('塔可装备；同塔同名限1件。' + ('紫装不能合成。' if entry.quality == 4 else '三件同品质可由工人合成。'))
        result[entry.rawcode] = {'unam': entry.name, 'utub': '|n'.join(parts), 'ides': '|n'.join(parts)}
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
            items[entry.rawcode]['ides'] = changed
            with self.subTest(uid=entry.rawcode), self.assertRaisesRegex(ValueError, entry.rawcode):
                verify_current_items(items)

    def test_each_aura_value_radius_and_shared_cap_are_checked(self):
        for uid, old, new in (('iP07', '增加基础攻击的12%', '增加基础攻击的13%'),
                             ('iP10', '光环范围550', '光环范围500'),
                             ('iP10', '合计上限75%', '合计上限85%'),
                             ('iP08', '合计上限40%', '合计上限50%')):
            self.assertEqual(self.items[uid]['utub'].count(old), 1)
            items = deepcopy(self.items); items[uid]['utub'] = items[uid]['utub'].replace(old, new, 1)
            items[uid]['ides'] = items[uid]['utub']
            with self.subTest(uid=uid, mutation=new), self.assertRaisesRegex(ValueError, uid):
                verify_current_items(items)

    def test_wrong_name_and_old_duplicate_or_crafting_phrase_are_checked(self):
        items = deepcopy(self.items); items['iP02']['unam'] = '旧武器'
        with self.assertRaisesRegex(ValueError, 'iP02: config name mismatch'):
            verify_current_items(items)
        for phrase in ('同塔同名限1件', '紫装不能合成'):
            items = deepcopy(self.items); items['iP02']['utub'] = items['iP02']['utub'].replace(phrase, '', 1)
            items['iP02']['ides'] = items['iP02']['utub']
            with self.subTest(phrase=phrase), self.assertRaisesRegex(ValueError, 'crafting/admission rule missing'):
                verify_current_items(items)

    def test_selected_ground_item_cannot_keep_quality_only_description(self):
        for description in ('白装装备', '', '白装', None):
            items = deepcopy(self.items)
            items['iW08']['ides'] = description
            with self.subTest(description=description), self.assertRaisesRegex(ValueError, 'ground selection description'):
                verify_current_items(items)

    def test_selected_and_hover_fields_cannot_drift(self):
        items = deepcopy(self.items)
        items['iW08']['ides'] += '过时说明'
        with self.assertRaisesRegex(ValueError, 'ground selection description'):
            verify_current_items(items)

    def test_both_fields_reject_developer_copy_and_wrong_poison_value(self):
        for old, new in (('每秒6伤害', '每秒7伤害'), ('每秒6伤害', '每秒6伤害，原生百分比')):
            items = deepcopy(self.items)
            text = items['iW08']['utub'].replace(old, new)
            items['iW08'].update(utub=text, ides=text)
            with self.subTest(new=new), self.assertRaisesRegex(ValueError, 'iW08'):
                verify_current_items(items)


def current_validate(*args):
    return validate(*args, shared_active_cooldown=True, current_pet_ui=True)


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
        cls.count = current_validate(cls.a, cls.u, cls.i)

    def mutate_text(self, uid, level, old, new, reason):
        a = deepcopy(self.a)
        text = a[uid][1]['aub1', level, 0][1]
        self.assertEqual(text.count(old), 1, uid + ': nonunique/missing actual-MPQ mutation needle')
        a[uid][1]['aub1', level, 0] = 3, text.replace(old, new, 1)
        with self.assertRaisesRegex(ValueError, reason):
            current_validate(a, self.u, self.i)

    def test_actual_shared_active_text_rejects_retired_whitelist_and_omitted_pet(self):
        items = deepcopy(self.i)
        original = items['iP08']['utub']
        self.assertIn('主动技能冷却缩短18%（包括附身精灵的主动技能）', original)
        for changed in (original.replace('主动技能冷却缩短18%（包括附身精灵的主动技能）', '嗜血、剑刃风暴与精灵主动技能冷却缩短18%', 1),
                        original.replace('（包括附身精灵的主动技能）', '', 1)):
            items['iP08']['utub'] = changed
            with self.subTest(text=changed), self.assertRaisesRegex(ValueError, 'iP08'):
                current_validate(self.a, self.u, items)

    def test_actual_split_ui_preserves_cost_risk_and_purple_release_rejects_mutation(self):
        for uid, old in (('Pm02', '保留旧技能也会消耗洗练石'), ('Pm06', '1开栏石'),
                         ('Pm07', '紫色精灵必得1开栏石'), ('Pm07', '先解绑'),
                         ('Pm0B', '无法撤销'), ('Pm09', '洗练石不返还')):
            self.mutate_text(uid, 1, old, '省略', uid)

    def test_historical_default_still_requires_combined_cultivation_contract(self):
        with self.assertRaisesRegex(ValueError, 'cultivation risk/cost missing'):
            validate(self.a, self.u, self.i, shared_active_cooldown=True)

    def test_actual_packaged_current40_all_tooltips(self):
        self.assertGreater(self.count, 900)

    def test_actual_last_control_poison_level_cannot_restore_native_move_or_stale_text(self):
        a = deepcopy(self.a); a['A106'][1]['Spo2', 61, 2] = 2, .352
        with self.assertRaisesRegex(ValueError, 'A106/61: native poison move double application'):
            current_validate(a, self.u, self.i)
        self.mutate_text('A106', 61, '35.2%', '22%', 'A106/61')

    def test_actual_last_bash_proc_and_shared_window_remain_checked(self):
        a = deepcopy(self.a); a['A113'][1]['Hbh1', 61, 1] = 2, 26.4
        with self.assertRaisesRegex(ValueError, 'A113/61: disabled native bash Hbh1'):
            current_validate(a, self.u, self.i)
        self.mutate_text('A113', 61, '26.4%', '22%', 'A113/61')
        self.mutate_text('A104', 61, '普通敌人眩晕0.9秒', '普通敌人眩晕1秒', 'A104/61')
        self.mutate_text('A104', 61, '保护期间不受任何塔的盾击', '独立窗口', 'shared shield window')

    def test_actual_last_equipment_cooldown_stays_checked(self):
        self.mutate_text('A131', 41, '7.2秒', '12秒', 'A131/41')

    def test_actual_pet_host_only_and_85_nominal_75_total_slow_are_checked(self):
        self.mutate_text('s010', 1, '仅附身塔', '全队所有塔', 's010')
        self.mutate_text('s03F', 1, '降低85%', '降低75%', 's03F')
        self.mutate_text('s03F', 1, '总上限75%', '总上限85%', 'pet slow total cap')

    def test_actual_missing_current_item_and_wrong_trial_percent_are_checked(self):
        items = deepcopy(self.i); del items['iP10']
        with self.assertRaisesRegex(ValueError, 'equipment identity set mismatch'):
            current_validate(self.a, self.u, items)
        items = deepcopy(self.i)
        old = '首领或金币试炼主目标普攻 +25%'
        self.assertEqual(items['iP02']['utub'].count(old), 1)
        items['iP02']['utub'] = items['iP02']['utub'].replace(old, old.replace('25%', '45%'), 1)
        items['iP02']['ides'] = items['iP02']['utub']
        with self.assertRaisesRegex(ValueError, 'iP02'):
            current_validate(self.a, self.u, items)
        items = deepcopy(self.i)
        old = '主目标生命不高于50%时，普攻追加20%'
        self.assertEqual(items['iB02']['utub'].count(old), 1)
        items['iB02']['utub'] = items['iB02']['utub'].replace(old, '普攻对首领或金币试炼主目标追加25%', 1)
        items['iB02']['ides'] = items['iB02']['utub']
        with self.assertRaisesRegex(ValueError, 'iB02'):
            current_validate(self.a, self.u, items)

    def test_actual_map_cannot_enter_legacy72_profile(self):
        from trial_formal72_fixture import Formal72SourceFixture
        frozen = Formal72SourceFixture(); self.addCleanup(frozen.cleanup)
        with self.assertRaisesRegex(ValueError, 'expected 28 gear texts'):
            validate(self.a, self.u, self.i, profile='legacy72', source_root=frozen.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
