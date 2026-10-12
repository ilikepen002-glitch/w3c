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

    def test_ground_accepts_single_craft_book_without_retired_commands(self):
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

    def test_ground_rejects_each_missing_book_command(self):
        for missing in ("A119", "Gupg"):
            with self.subTest(missing=missing):
                self.setUp()
                del self.abilities[missing]
                self.assert_rejected("VerifyGroundItemArtifact.py", f"Missing function book command {missing}")

    def test_ground_rejects_removed_damage_ghost_without_attachment(self):
        self.abilities["Dsta"] = deepcopy(self.abilities["Pcol"])
        self.assert_rejected("VerifyGroundItemArtifact.py", "Removed damage statistics ability Dsta remains as a ghost object")

    def test_ground_rejects_missing_only_craft_spell(self):
        self.change_field("Geqb", "spb1", "", 1, 1)
        self.assert_rejected("VerifyGroundItemArtifact.py", "Book must contain only A119")

    def test_ground_rejects_extra_book_spell(self):
        for extra in ("Gupg", "A109", "A119"):
            with self.subTest(extra=extra):
                self.setUp()
                self.change_field("Geqb", "spb1", "A119," + extra, 1, 1)
                self.assert_rejected("VerifyGroundItemArtifact.py", "Book must contain only A119")

    def test_ground_rejects_each_wrong_book_capacity(self):
        for field, column in [("spb3", 3), ("spb4", 4)]:
            for count in (0, 2, 3, 4, 5, 6):
                with self.subTest(field=field, count=count):
                    self.setUp()
                    self.change_field("Geqb", field, count, 1, column)
                    self.assert_rejected("VerifyGroundItemArtifact.py", "Book must contain exactly one spell")

    def test_ground_rejects_wrong_cells_and_targets(self):
        for rawcode, field, value, level, column, reason in [
                ("A119", "abpx", 1, 0, 0, "Backpack craft must occupy book cell 0,0"),
                ("Gupg", "abpx", 0, 0, 0, "Ground upgrade must occupy main bar 1,1"),
                ("Gupg", "Ncl2", 0, 1, 2, "Ground upgrade must target a point")]:
            with self.subTest(command=rawcode, field=field):
                self.setUp()
                self.change_field(rawcode, field, value, level, column)
                self.assert_rejected("VerifyGroundItemArtifact.py", reason)

    def test_ground_rejects_duplicate_assigned_hotkeys(self):
        self.abilities["A119"][1][("ahky", 0, 0)] = (3, "U")
        self.assert_rejected("VerifyGroundItemArtifact.py", "Backpack craft hotkey must remain C")

    def test_ground_corrected_fixture_satisfies_single_command_contract(self):
        from VerifyGroundItemArtifact import verify_function_book
        self.assertEqual(verify_function_book(self.abilities, self.units)[0], "uF01")

    def test_ground_rejects_each_removed_ghost_even_without_attachment(self):
        for retired in ("Phnt", "Pmas", "Pfor"):
            with self.subTest(rawcode=retired):
                self.setUp()
                self.abilities[retired] = deepcopy(self.abilities["Pcol"])
                self.assert_rejected("VerifyGroundItemArtifact.py", f"Removed capture/hunt ability {retired} remains as a ghost object")

    def test_ground_rejects_removed_parents_and_attachments(self):
        for retired in ("Phnt", "Pmas", "Pfor"):
            for target in ("parent", "farmer", "tower", "book", "requirement"):
                with self.subTest(rawcode=retired, target=target):
                    self.setUp()
                    if target == "parent":
                        self.abilities["Xret"] = (retired, {})
                        reason = f"Xret: removed {retired} remains as ability parent"
                    elif target == "book":
                        self.change_field("Geqb", "spb1", "A119,Gupg," + retired, 1, 1)
                        reason = f"Geqb: removed {retired} remains in ability field spb1"
                    elif target == "requirement":
                        self.abilities["Gupg"][1][("areq", 0, 0)] = (3, retired)
                        reason = f"Gupg: removed {retired} remains in ability field areq"
                    else:
                        unit_id = "uF01" if target == "farmer" else "uA11"
                        self.units[unit_id]["uabi"] += "," + retired
                        reason = f"{unit_id}: removed {retired} remains in unit field uabi"
                    self.assert_rejected("VerifyGroundItemArtifact.py", reason)

    def test_ground_rejects_removed_item_objects_and_fields(self):
        from VerifyGroundItemArtifact import verify_no_hunt_objects
        for retired in ("Phnt", "Pmas", "Pfor"):
            for items in ({retired: {}}, {"Iret": {"iabi": retired}}):
                with self.subTest(rawcode=retired, items=items), self.assertRaisesRegex(ValueError, "[Rr]emoved.*" + retired + ".*item"):
                    verify_no_hunt_objects(self.abilities, self.units, items)

    def test_ground_rejects_extra_book_entry(self):
        self.change_field("Geqb", "spb1", "A119,Gupg,Pcol", 1, 1)
        self.assert_rejected("VerifyGroundItemArtifact.py", "Book must contain only A119")

    def test_ground_retains_existing_channel_order_checks(self):
        shared_order = self.baseline_abilities["Pcol"][1][("Ncl6", 1, 6)][1]
        for rawcode in ("Gupg", "A109", "A133", "Pc02"):
            with self.subTest(command=rawcode):
                self.setUp()
                self.change_field(rawcode, "Ncl6", shared_order, 1, 6)
                self.assert_rejected("VerifyGroundItemArtifact.py", "Channel order")


if __name__ == "__main__":
    unittest.main(verbosity=2)
