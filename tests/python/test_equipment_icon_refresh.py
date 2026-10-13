"""Source/import-only checks; actual packed closure is a separate CLI gate."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import VerifyEquipmentIconRefresh as v
from BuildEquipmentIconRefresh import MANIFEST
from BuildSpiritSkillIcons import build
from ReadEquipmentCatalog import icon_paths
from VerifySemanticIconArtifact import decode_blp

class EquipmentIconRefreshTests(unittest.TestCase):
    def test_source_has_five_selected_pairs_and_zero_cross_line_conflicts(self):
        self.assertEqual(v.source_check()['pairs'],5)
        self.assertEqual(v.spirit.equipment_report()['cross_line_review_needed'],[])

    def test_equipment_icons_rebuild_and_all_mips_decode(self):
        manifest=json.loads(MANIFEST.read_text())
        self.assertEqual(len(manifest['assets']),5)
        for e in manifest['assets']:
            for key in ('normal','disabled'):
                data=(ROOT/'imports'/e[key].replace('\\','/')).read_bytes()
                self.assertEqual(len(decode_blp(data,e[key])),7)
        self.assertLessEqual(build(MANIFEST,check=True,expected_pairs=5)['zlib_estimate_bytes'],61440)

    def test_semantic_telescope_and_axe_use_existing_same_line_art(self):
        p=icon_paths();self.assertEqual(p[1,3],p[1,2]);self.assertEqual(p[2,3],p[2,1])

    def test_cross_line_regression_fails(self):
        paths=icon_paths();paths[9,1]=paths[6,4]
        with patch.object(v,'icon_paths',return_value=paths):
            with self.assertRaisesRegex(ValueError,'Wrong equipment mapping'):v.source_check()

    def test_open_slot_command_differs_from_reroll_same_screen(self):
        from VerifyPetUIArtifact import MANAGER_COMMANDS
        self.assertEqual(MANAGER_COMMANDS['Pm06'][-1],'TDPetEmptySlot')
        for raw in ['Pm02','Pm03','Pm04','Pm05']:
            self.assertNotEqual(MANAGER_COMMANDS[raw][-1],MANAGER_COMMANDS['Pm06'][-1])

if __name__=='__main__':unittest.main()
