"""Source/assets and negative fixtures only; final packed map gate is separate."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import VerifySpiritSkillIcons as v
from BuildSpiritSkillIcons import MANIFEST,build,render
from BuildSemanticIcons import disabled_icon
from VerifyPetUIArtifact import decode_icon_blp

class SpiritSkillIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text())
        cls.result,cls.n=v.source_check()

    def test_43_identities_share_no_actual_paths(self):
        self.assertEqual(self.result['distinct_spirit_paths'],43)
        self.assertEqual(self.result['custom_pairs'],25)
        self.assertEqual(self.result['retained_native_paths'],18)

    def test_source_preview_and_equipped_paths_use_same_dispatch(self):
        source=(ROOT/'wurst/pets/TDPetObjectGen.wurst').read_text()
        self.assertIn('..setIconNormal(tdPetSkillIconPath(skill, false))',source)
        self.assertNotIn('"ReplaceableTextures\\\\CommandButtons\\\\" + tdPetSkillIconName',source)
        for i in v.skill_paths(self.n):
            self.assertEqual(v.expected_bindings(self.n)[f'Ps{i:02X}'],self.n['tdPetSkillIconPath'](i,False))

    def test_25_pairs_reproduce_and_stay_under_estimate_budget(self):
        result=build(check=True)
        self.assertLessEqual(result['zlib_estimate_bytes'],262144)
        self.assertEqual(result['raw_bytes'],605100)

    def test_actual_blp_headers_alpha_mips_and_disabled_visuals(self):
        for e in self.manifest['assets']:
            normal=render(e);disabled=disabled_icon(normal)
            self.assertEqual(normal.getchannel('A').tobytes(),disabled.getchannel('A').tobytes())
            self.assertGreater(sum(disabled.convert('L').getdata()),0)
            self.assertLess(sum(disabled.convert('L').getdata()),sum(normal.convert('L').getdata()))
            for key in ('normal','disabled'):
                data=(ROOT/'imports'/e[key].replace('\\','/')).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(),e[key+'_sha256'])
                decode_icon_blp(data,e[key])

    def test_collision_detection_is_case_insensitive_actual_path_based(self):
        self.assertEqual(len(v.collisions([{'path':'A/B.blp'},{'path':'a\\b.BLP'}])),1)
        self.assertEqual(v.collisions([{'path':'war3mapImported\\BTNX.blp'}, {'path':'ReplaceableTextures\\CommandButtons\\BTNX.blp'}]),[])

    def test_mutated_skill_collision_is_rejected(self):
        n=dict(self.n);original=n['tdPetSkillIconPath']
        n['tdPetSkillIconPath']=lambda i,d:original(8 if i==17 else i,d)
        with patch.object(v,'phase_one_catalog',return_value=n):
            with self.assertRaisesRegex(ValueError,'share an icon'):v.source_check()

    def test_retired_skills_never_gain_new_display_objects(self):
        bindings=v.expected_bindings(self.n)
        for i in (4,9,10,13,14,15):self.assertNotIn(f'Ps{i:02X}',bindings)
        self.assertEqual(len({e['normal'] for e in self.manifest['assets']}),25)

    def test_equipment_remaining_issues_are_reported_not_hidden(self):
        self.assertIn('cross_line_review_needed',v.equipment_report())

if __name__=='__main__':unittest.main()
