"""Offline verifier regression tests against the existing packaged map.

Run from the repository root:
    python3 -m unittest discover -s tests/python -v

Negative cases mutate deep copies of parsed objects, never the map file.
Ground negatives correct only the approved release contract in memory first;
actual-artifact positives deliberately fail until the new map is rebuilt.
"""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
ARTIFACT = ROOT / "ExampleMap.w3x"
sys.path.insert(0, str(TOOLS))

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerPlacementArtifact import unit_objects
from pet_artifact_fixture import correct_release_contract


class BaselineArtifactTests(unittest.TestCase):
    def assert_verifier_passes(self, script):
        result = subprocess.run(
            [sys.executable, str(TOOLS / script), str(ARTIFACT)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_evolution_accepts_complete_inherited_skill_bars(self):
        self.assert_verifier_passes("VerifyEvolutionArtifact.py")

    def test_ground_accepts_exact_five_command_book_without_hunt(self):
        self.assert_verifier_passes("VerifyGroundItemArtifact.py")


class ParsedObjectNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = Mpq(ARTIFACT.read_bytes())
        cls.baseline_abilities = ability_objects(artifact.extract("war3map.w3a"))
        cls.baseline_units = unit_objects(artifact.extract("war3map.w3u"))
        correct_release_contract(cls.baseline_abilities, cls.baseline_units)

    def setUp(self):
        self.abilities = deepcopy(self.baseline_abilities)
        self.units = deepcopy(self.baseline_units)

    def assert_rejected(self, script, reason):
        with patch("sys.argv", [script, str(ARTIFACT)]), \
                patch("VerifyEquipmentAbilityArtifact.ability_objects", return_value=self.abilities), \
                patch("VerifyTowerPlacementArtifact.unit_objects", return_value=self.units), \
                redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(ValueError, re.escape(reason)):
            runpy.run_path(str(TOOLS / script), run_name="__main__")

    def change_field(self, rawcode, field, value, level=0, column=0):
        fields = self.abilities[rawcode][1]
        kind, _ = fields[(field, level, column)]
        fields[(field, level, column)] = (kind, value)

    def test_evolution_rejects_each_missing_display(self):
        for uid, missing in [("uO15", "A139"), ("uD15", "A135"),
                             ("uD6B", "A141"), ("uG15", "A137"),
                             ("uG6A", "A137")]:
            with self.subTest(unit=uid, missing=missing):
                self.units = deepcopy(self.baseline_units)
                skills = self.units[uid]["uabi"].split(",")
                skills.remove(missing)
                self.units[uid]["uabi"] = ",".join(skills)
                self.assert_rejected("VerifyEvolutionArtifact.py", f"{uid}: complete skill bar mismatch")

    def test_evolution_rejects_missing_branch_skill(self):
        for family in "A O H D G".split():
            for branch in "AB":
                uid = f"u{family}6{branch}"
                with self.subTest(unit=uid):
                    self.units = deepcopy(self.baseline_units)
                    skills = self.units[uid]["uabi"].split(",")
                    self.units[uid]["uabi"] = ",".join(skills[1:])
                    self.assert_rejected("VerifyEvolutionArtifact.py", f"{uid}: complete skill bar mismatch")

    def test_evolution_rejects_reordered_branch_skill_bars(self):
        for family in "A O H D G".split():
            for branch in "AB":
                uid = f"u{family}6{branch}"
                with self.subTest(unit=uid):
                    self.units = deepcopy(self.baseline_units)
                    skills = self.units[uid]["uabi"].split(",")
                    skills[0], skills[1] = skills[1], skills[0]
                    self.units[uid]["uabi"] = ",".join(skills)
                    self.assert_rejected("VerifyEvolutionArtifact.py", f"{uid}: complete skill bar mismatch")

    def test_ground_rejects_each_missing_pet_command(self):
        for missing in ("Pmas", "Pfor"):
            with self.subTest(missing=missing):
                self.abilities = deepcopy(self.baseline_abilities)
                spells = self.abilities["Geqb"][1][("spb1", 1, 1)][1].split(",")
                spells.remove(missing)
                self.change_field("Geqb", "spb1", ",".join(spells), 1, 1)
                self.assert_rejected("VerifyGroundItemArtifact.py", "Unexpected book spell list")

    def test_ground_rejects_reordered_book(self):
        spells = self.abilities["Geqb"][1][("spb1", 1, 1)][1].split(",")
        spells[-1], spells[-2] = spells[-2], spells[-1]
        self.change_field("Geqb", "spb1", ",".join(spells), 1, 1)
        self.assert_rejected("VerifyGroundItemArtifact.py", "Unexpected book spell list")

    def test_ground_rejects_each_wrong_book_capacity(self):
        for field, column in [("spb3", 3), ("spb4", 4)]:
            for count in (3, 6, 7):
                with self.subTest(field=field, count=count):
                    self.abilities = deepcopy(self.baseline_abilities)
                    self.change_field("Geqb", field, count, 1, column)
                    self.assert_rejected("VerifyGroundItemArtifact.py", "Book must contain exactly five spells")

    def test_ground_rejects_each_pet_command_wrong_parent(self):
        for rawcode in ("Pmas", "Pfor"):
            with self.subTest(command=rawcode):
                self.abilities = deepcopy(self.baseline_abilities)
                _, fields = self.abilities[rawcode]
                self.abilities[rawcode] = ("Aspb", fields)
                self.assert_rejected("VerifyGroundItemArtifact.py", f"{rawcode}: function command must inherit Channel")

    def test_ground_rejects_each_pet_command_wrong_cell(self):
        for rawcode in ("Pmas", "Pfor"):
            with self.subTest(command=rawcode):
                self.abilities = deepcopy(self.baseline_abilities)
                self.change_field(rawcode, "abpy", 2)
                self.assert_rejected("VerifyGroundItemArtifact.py", f"{rawcode}: wrong function book cell")

    def test_ground_rejects_each_pet_command_wrong_hotkey(self):
        for rawcode in ("Pmas", "Pfor"):
            with self.subTest(command=rawcode):
                self.abilities = deepcopy(self.baseline_abilities)
                self.change_field(rawcode, "ahky", "Z")
                self.assert_rejected("VerifyGroundItemArtifact.py", f"{rawcode}: wrong function book hotkey")

    def test_ground_rejects_each_pet_command_wrong_target(self):
        for rawcode, wrong_target in [("Pmas", 0), ("Pfor", 1)]:
            with self.subTest(command=rawcode):
                self.abilities = deepcopy(self.baseline_abilities)
                self.change_field(rawcode, "Ncl2", wrong_target, 1, 2)
                self.assert_rejected("VerifyGroundItemArtifact.py", f"{rawcode}: wrong function command target")

    def test_ground_rejects_overlapping_book_cells(self):
        self.change_field("Pfor", "abpx", 0)
        self.assert_rejected("VerifyGroundItemArtifact.py", "Function book command cells overlap: Pmas and Pfor")

    def test_ground_rejects_duplicate_book_hotkeys(self):
        self.change_field("Pfor", "ahky", "M")
        self.assert_rejected("VerifyGroundItemArtifact.py", "Function book command hotkeys overlap: Pmas and Pfor")

    def test_ground_corrected_fixture_satisfies_five_command_contract(self):
        from VerifyGroundItemArtifact import verify_function_book
        self.assertEqual(verify_function_book(self.abilities, self.units)[0], "uF01")

    def test_ground_rejects_ghost_hunt_even_without_any_attachment(self):
        self.abilities["Phnt"] = deepcopy(self.abilities["Pmas"])
        self.assert_rejected("VerifyGroundItemArtifact.py", "Removed hunt ability Phnt remains as a ghost object")

    def test_ground_rejects_hunt_attachment_on_unrelated_units_and_books(self):
        for target in ("farmer", "tower", "book"):
            with self.subTest(target=target):
                self.setUp()
                if target == "book":
                    spells = self.abilities["Geqb"][1][("spb1", 1, 1)][1]
                    self.change_field("Geqb", "spb1", spells + ",Phnt", 1, 1)
                    reason = "Geqb: removed Phnt remains in ability field spb1"
                else:
                    unit_id = "uF01" if target == "farmer" else "uA11"
                    self.units[unit_id]["uabi"] += ",Phnt"
                    reason = f"{unit_id}: removed Phnt remains in unit field uabi"
                self.assert_rejected("VerifyGroundItemArtifact.py", reason)

    def test_ground_rejects_six_entry_book_even_without_hunt_object(self):
        spells = self.abilities["Geqb"][1][("spb1", 1, 1)][1]
        self.change_field("Geqb", "spb1", spells + ",Pcol", 1, 1)
        self.assert_rejected("VerifyGroundItemArtifact.py", "Unexpected book spell list")

    def test_ground_rejects_old_five_to_one_cell(self):
        self.change_field("Pfor", "abpx", 2)
        self.assert_rejected("VerifyGroundItemArtifact.py", "Pfor: wrong function book cell")

    def test_ground_retains_existing_channel_order_checks(self):
        for rawcode in ("Dsta", "Gupg", "A109", "A133", "Pc02"):
            reason = "Channel order"
            with self.subTest(command=rawcode):
                self.abilities = deepcopy(self.baseline_abilities)
                shared_order = self.abilities["Pmas"][1][("Ncl6", 1, 6)][1]
                self.change_field(rawcode, "Ncl6", shared_order, 1, 6)
                self.assert_rejected("VerifyGroundItemArtifact.py", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
