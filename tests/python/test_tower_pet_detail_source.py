"""Actual-source behavior and object wiring; no native Warcraft claim."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from test_elemental_pet_runtime_source import compile_body, source
import VerifyTowerUpgradeArtifact as towers

ROOT = Path(__file__).resolve().parents[2]


class TowerPetDetailTests(unittest.TestCase):
    def setUp(self):
        self.pages, self.notices, self.pets = [], [], {}
        self.owner, self.active, self.trigger = 0, True, None
        self.n = dict(
            GetUnitTypeId=lambda tower: tower.type,
            GetOwningPlayer=lambda tower: tower.owner,
            GetPlayerId=lambda owner: owner,
            GetTriggerPlayer=lambda: self.owner,
            GetTriggerUnit=lambda: self.trigger,
            tdTowerChoiceForUnitTypeId=lambda type_id: int(type_id in towers.EXPECTED_TOWERS),
            tdIsLanePlayer=lambda lane: 0 <= lane < 4,
            tdPetLaneCanManage=lambda lane: self.active,
            TD_PET_COLLECTION_LIMIT=20, TD_PET_UI_DETAIL=1,
            tdPetAt=lambda lane, slot: self.pets.get((lane, slot)),
            showPage=lambda *args: self.pages.append(args),
            tdPetNotice=lambda *args: self.notices.append(args))
        for name in ('tdPetShowTowerDetail', 'onDeploy'):
            compile_body(source('TDPetUI'), name, self.n)

    def tower(self, type_id='uA11', owner=0):
        return SimpleNamespace(type=type_id, owner=owner)

    def bind(self, host, slot, lane=0, released=False):
        self.pets[lane, slot] = SimpleNamespace(host=host, lane=lane, released=released)

    def click(self, tower):
        self.trigger = tower
        self.assertFalse(self.n['onDeploy']())

    def test_all_35_nodes_empty_and_last_page_bound(self):
        self.assertEqual(len(towers.EXPECTED_TOWERS), 35)
        for type_id in towers.EXPECTED_TOWERS:
            with self.subTest(type_id=type_id):
                self.setUp()
                tower = self.tower(type_id)
                self.click(tower)
                self.assertEqual(self.notices, [(0, '没有精灵')])
                self.assertEqual(self.pages, [])
                self.bind(tower, 19)
                self.click(tower)
                self.assertEqual(self.pages, [(0, 1, 1, 19, 0)])

    def test_other_tower_and_last_selected_pet_never_open(self):
        clicked, other = self.tower(), self.tower('uO11')
        self.bind(other, 0)
        self.click(clicked)
        self.assertEqual(self.pages, [])
        self.bind(clicked, 13)
        self.click(clicked)
        self.assertEqual(self.pages, [(0, 1, 1, 13, 0)])
        self.pets[0, 13].host = other
        self.click(clicked)
        self.assertEqual(self.notices, [(0, '没有精灵'), (0, '没有精灵')])

    def test_foreign_owner_non_tower_null_and_inactive_are_ignored(self):
        for invalid in (None, self.tower('uF01'), self.tower(owner=1)):
            self.click(invalid)
        self.active = False
        self.click(self.tower())
        self.assertEqual(self.pages, [])
        self.assertEqual(self.notices, [])

    def test_released_or_mismatched_lane_record_is_not_shown(self):
        tower = self.tower()
        self.bind(tower, 0, released=True)
        self.pets[0, 1] = SimpleNamespace(host=tower, lane=1, released=False)
        self.click(tower)
        self.assertEqual(self.pages, [])
        self.assertEqual(self.notices, [(0, '没有精灵')])

    def test_shared_object_generator_mounts_all_towers_not_farmer(self):
        from VerifyPetManagerSource import function_body
        text = (ROOT / 'wurst/towers/TDTowerObjectGen.wurst').read_text().replace('@compiletime ', '')
        farmer = function_body(text, 'tdGenerateBuilderObjects')[1]
        self.assertNotIn('TD_PET_DEPLOY_ABILITY_ID', farmer)
        for command in ('TD_PET_CAPTURE_ABILITY_ID', 'TD_PET_COLLECTION_ABILITY_ID'):
            self.assertIn(command, farmer)
        shared = text.split('function BuildingDefinition.tdApplyTowerBuildingStats', 1)[1].split('\nfunction ', 1)[0]
        self.assertEqual(shared.count('TD_PET_DEPLOY_ABILITY_ID'), 1)
        self.assertIn('..tdApplyTowerBuildingStats', function_body(text, 'tdGenerateTowerLevelObject')[1])
        self.assertIn('"精灵绑定详情", "D", 0, 0, Targettype.NONE', source('TDPetObjectGen'))
        for skills in towers.EXPECTED_TOWERS.values():
            self.assertEqual(skills.count('Pdep'), 1)
