"""Source/controlled-text regression gates; no claim of native UI rendering."""
from pathlib import Path
import re
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from ReadEquipmentCatalog import catalog


class SelectedItemDescriptionSourceTests(unittest.TestCase):
    def test_ground_and_hover_use_one_effect_formatter_for_all_forty_items(self):
        text = (ROOT / 'wurst/items/TDItemObjectGen.wurst').read_text()
        body = text.split('function tdGenerateEquipmentItem(int itemId)', 1)[1].split('@compiletime', 1)[0]
        self.assertIn('..setTooltipExtended(tdItemTooltip(itemId))', body)
        self.assertIn('..setDescription(tdItemTooltip(itemId))', body)
        self.assertNotIn('setDescription(tdItemQualityName', body)
        self.assertEqual(len(catalog()), 40)
        self.assertIn('for index = 1 to tdItemDefinitionCount()', text)
        self.assertIn('tdGenerateEquipmentItem(tdItemIdForCatalogIndex(index))', text)

    def test_poison_catalog_and_formatter_keep_damage_duration_and_stacking(self):
        entry = next(x for x in catalog() if x.name == '毒囊')
        self.assertEqual((entry.rawcode, entry.primary, entry.primary_value), ('iW08', 'POISON', 6))
        text = (ROOT / 'wurst/items/TDItemData.wurst').read_text()
        body = text.split('if effectKind == TD_ITEM_EFFECT_POISON', 1)[1].split('if effectKind', 1)[0]
        for token in ('value', '每秒', '伤害，持续3秒', '装备毒伤取最强'):
            self.assertIn(token, body)

    def test_navigation_is_not_a_rule_dump(self):
        text = (ROOT / 'wurst/items/TDItemObjectGen.wurst').read_text()
        body = text.split('function tdGenerateGroundEquipmentCommands()', 1)[1]
        description = re.search(r'setTooltipNormalExtended\(1, "([^"]+)"\)', body)[1]
        self.assertEqual(description, '打开背包合成。')

    def test_player_effect_formatters_do_not_restore_implementation_language(self):
        scopes = (
            ('items/TDItemData.wurst', 'function tdItemEffectText(', 'public function tdItemLevel('),
            ('auras/TDAuraMetadata.wurst', 'public function tdAuraStateTooltip(', 'public function tdAuraIcon('),
            ('pets/TDPetRules.wurst', 'public function tdPetSkillDescriptionById(', None),
            ('items/TDEquipmentSpecialRules.wurst', 'public function tdWarStageTooltip(', None),
            ('items/TDItemObjectGen.wurst', 'function tdGenerateCraftAbility(', None),
        )
        banned = ('静态基础', '原生百分比', '载体', '回灌', '圈内快照', '同身份', '合法塔', '标称', '本击事件')
        for file, start, end in scopes:
            text = (ROOT / 'wurst' / file).read_text().split(start, 1)[1]
            if end:
                text = text.split(end, 1)[0]
            # Only quoted player strings; comments and diagnostic code remain valid.
            strings = '\n'.join(re.findall(r'"((?:\\.|[^"\\])*)"', text))
            for token in banned:
                with self.subTest(file=file, token=token):
                    self.assertNotIn(token, strings)


if __name__ == '__main__':
    unittest.main()
