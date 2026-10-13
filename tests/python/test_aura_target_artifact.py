"""Actual packaged aura routing plus fail-closed UI-carrier regression fixtures.

Synthetic object mutations below are in memory only. They test the verifier;
they do not produce a map or stand in for a rebuilt candidate or live Warcraft.
"""
from copy import deepcopy
from pathlib import Path
import re
import sys
import unittest
from python_check_inputs import candidate_map

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyPetUIArtifact import jass_function
from VerifySemanticIconArtifact import Field, parse_objects
from VerifyPureBossArtifact import source_function
import VerifyAuraTargetArtifact as gate


def replace_body(script, name, old, new):
    match = jass_function(script, name)
    body = match.group(1)
    if old not in body:
        raise AssertionError('Mutation must match actual packaged code: ' + old)
    return script[:match.start(1)] + body.replace(old, new) + script[match.end(1):]


class AuraTargetArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = Mpq(candidate_map().read_bytes())
        cls.script = artifact.extract('war3map.j').decode('utf-8')
        cls.objects = parse_objects(artifact.extract('war3map.w3a'), True)

    def test_actual_equipment_tower_pet_matrix_and_wind_application(self):
        result = gate.verify(self.script)
        self.assertEqual(result['equipment_target_cases'], 112)
        self.assertEqual(result['tower_target_cases'], 35)
        self.assertEqual(result['pet_target_cases'], 6)
        self.assertEqual(result['wind_application']['own_towers_A129_level'], 4)

    def test_rejects_lost_same_player_guard(self):
        body = jass_function(self.script, 'tdAuraOfferSource').group(1)
        guard = re.search(r'if (\w+ != targetLane)(?: or [^\n]+)? then', body)
        self.assertIsNotNone(guard, 'Actual same-lane source guard must be present')
        script = replace_body(self.script, 'tdAuraOfferSource',
                              guard.group(1), 'false')
        with self.assertRaisesRegex(ValueError, 'ally tower'):
            gate.verify_equipment_targets(script)

    def test_rejects_friendly_equipment_given_to_enemy(self):
        script = replace_body(self.script, 'tdAuraOfferSource',
                              'elseif kind != TDItemCatalogSchema_TD_ITEM_AURA_ENEMY_SLOW then',
                              'elseif false then')
        with self.assertRaisesRegex(ValueError, 'lane enemy boundary'):
            gate.verify_equipment_targets(script)

    def test_rejects_pet_host_only_rule_removed(self):
        if 'function tdPetApplyAttackDebuffs ' in self.script:
            body = jass_function(self.script, 'tdAuraOfferSource').group(1)
            initialization = re.search(r'set slot(?:_\d+)? = 0', body)
            self.assertIsNotNone(initialization, 'Actual equipment slot loop must be present')
            script = replace_body(self.script, 'tdAuraOfferSource', initialization.group(),
                                  'call dispatch_TDAuraAggregate_TDAuraAggregate_offer(aggregate, 8, 2, 0.12, true, "retired-aura negative fixture")\n' + initialization.group())
            with self.assertRaisesRegex(ValueError, 'Retired pet aura target 101'):
                gate.verify_pet_targets(script)
            return
        script = replace_body(self.script, 'tdAuraOfferSource',
                              'source_6 == target_3', 'true')
        with self.assertRaisesRegex(ValueError, 'Pet aura target 103'):
            gate.verify_pet_targets(script)

    def test_source_hides_only_the_two_percentage_carrier_families(self):
        source = (ROOT / 'wurst/auras/TDAuraObjectGen.wurst').read_text()
        body = source_function(source, 'tdGenerateAuraPercentageCarriers')
        for variable in ('whiteTiger', 'commander'):
            self.assertEqual(body.count(variable + '.setButtonPositionNormalX(0)'), 1)
            self.assertEqual(body.count(variable + '.setButtonPositionNormalY(-11)'), 1)
            self.assertIn(variable + '.setTargetsAllowed(1, "self")', body)
            self.assertIn(variable + '.setBuffs(1, tdAuraBuff(', body)
        self.assertNotIn('Blz', source)
        self.assertNotIn('SetPlayerAbilityAvailable', source)

    def corrected_objects(self):
        objects = deepcopy(self.objects)
        for label in ('白虎', '统帅'):
            for rank in (1, 2):
                _, obj = gate.named(objects, label + '百分比载体 ' + str(rank))
                for name, value in (('abpx', 0), ('abpy', -11)):
                    key = name, 0, 0
                    obj.fields[key] = Field(key, 0, value, b'')
        return objects

    def test_hidden_carrier_gate_accepts_correct_field_fixture(self):
        self.assertEqual(len(gate.verify_hidden_carriers(self.corrected_objects())), 4)

    def test_hidden_carrier_gate_rejects_each_visible_carrier(self):
        for code in gate.verify_hidden_carriers(self.corrected_objects()):
            with self.subTest(carrier=code):
                objects = self.corrected_objects()
                del objects[code].fields['abpy', 0, 0]
                with self.assertRaisesRegex(ValueError, 'button is not hidden'):
                    gate.verify_hidden_carriers(objects)

    def test_hidden_carrier_gate_rejects_hiding_actual_source(self):
        for code in ('A101', 'A111', 'A105', 'AeCM'):
            with self.subTest(source=code):
                objects = self.corrected_objects()
                key = 'abpy', 0, 0
                objects[code].fields[key] = Field(key, 0, -11, b'')
                with self.assertRaisesRegex(ValueError, 'source button must remain visible'):
                    gate.verify_hidden_carriers(objects)


if __name__ == '__main__':
    unittest.main()
