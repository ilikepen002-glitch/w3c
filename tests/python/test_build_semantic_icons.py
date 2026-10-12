"""Source/import-only semantic icon tests; do not need or rebuild a map."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from BuildEvolutionAssets import TOWER_ICON_NAMES, remove_legacy_tower_icon, tower_icon_stem
from BuildSemanticIcons import MANIFEST, build, disabled_icon, render_icon
from VerifyPetUIArtifact import decode_icon_blp


class SemanticSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_exactly_selected_seven_sources_and_thirty_pairs(self):
        assets = self.manifest["assets"]
        self.assertEqual(len(assets), 30)
        self.assertEqual(len({a["source"] for a in assets}), 7)
        expected_sources = {
            "ranged-sheet-source.png", "arcane-sheet-source.png", "combat-sheet-source.png",
            "misc-sheet-source.png", "actions-sheet-v2-source.png",
            "critical-strike-source.png", "inventory-craft-source.png",
        }
        self.assertEqual({Path(a["source"]).name for a in assets}, expected_sources)
        self.assertEqual({p.name for p in MANIFEST.parent.glob("*.png")}, expected_sources)
        self.assertEqual(len({a["name"] for a in assets}), 30)
        for entry in assets:
            with self.subTest(icon=entry["name"]):
                self.assertEqual(hashlib.sha256((ROOT / entry["source"]).read_bytes()).hexdigest(), entry["source_sha256"])

    def test_all_new_imports_have_pinned_hashes_and_valid_blp_mips(self):
        for entry in self.manifest["assets"]:
            for key in ["normal", "disabled"]:
                with self.subTest(icon=entry["name"], state=key):
                    data = (ROOT / "imports" / entry[key].replace("\\", "/")).read_bytes()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), entry[key + "_sha256"])
                    decode_icon_blp(data, entry[key])

    def test_disabled_source_transform_preserves_alpha_and_is_nonempty(self):
        for entry in self.manifest["assets"]:
            with self.subTest(icon=entry["name"]):
                normal = render_icon(entry)
                disabled = disabled_icon(normal)
                self.assertEqual(normal.size, (64, 64))
                self.assertEqual(normal.getchannel("A").tobytes(), disabled.getchannel("A").tobytes())
                self.assertGreater(sum(disabled.convert("L").getdata()), 0)
                self.assertLess(sum(disabled.convert("L").getdata()), sum(normal.convert("L").getdata()))

    def test_tower_migrations_are_exact_byte_locked_and_old_paths_absent(self):
        records = self.manifest["towerMigrations"]
        self.assertEqual({a["name"] for a in records}, set(TOWER_ICON_NAMES))
        names = {str(p.relative_to(ROOT / "imports")).replace("/", "\\").casefold() for p in (ROOT / "imports").rglob("*") if p.is_file()}
        for entry in records:
            for key in ["normal", "disabled"]:
                with self.subTest(icon=entry["name"], state=key):
                    self.assertNotIn(entry["old_" + key].casefold(), names)
                    data = (ROOT / "imports" / entry[key].replace("\\", "/")).read_bytes()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), entry[key + "_sha256"])

    def test_thirteen_pet_ui_pairs_remain_byte_locked(self):
        self.assertEqual(len(self.manifest["preservedPetUI"]), 13)
        for entry in self.manifest["preservedPetUI"]:
            for key in ["normal", "disabled"]:
                data = (ROOT / "imports" / entry[key].replace("\\", "/")).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry[key + "_sha256"])

    def test_import_paths_are_casefold_unique_and_contain_only_blp_icon_outputs(self):
        paths = [str(p.relative_to(ROOT / "imports")).replace("/", "\\") for p in (ROOT / "imports").rglob("*") if p.is_file()]
        self.assertEqual(len(paths), len({p.casefold() for p in paths}))
        for entry in self.manifest["assets"]:
            self.assertTrue(entry["normal"].startswith("war3mapImported\\BTNTD"))
            self.assertTrue(entry["disabled"].startswith("ReplaceableTextures\\CommandButtonsDisabled\\DISBTNTD"))

    def test_full_icon_paths_use_explicit_ability_setters(self):
        item = (ROOT / "wurst/items/TDItemObjectGen.wurst").read_text()
        pets = (ROOT / "wurst/pets/TDPetObjectGen.wurst").read_text()
        for helper in ["tdFarmerCraftIconPath()", "tdFarmerGroundUpgradeIconPath()"]:
            self.assertIn("..setIconNormal(" + helper + ")", item)
            self.assertIn("..setIconResearch(" + helper + ")", item)
            self.assertNotIn("presetIcon(" + helper, item)
        self.assertIn("..setIconNormal(tdPetCaptureIconPath())..setIconResearch(tdPetCaptureIconPath())", pets)
        self.assertNotIn("presetIcon", pets)
        self.assertNotIn("TD_PET_MASTER_ABILITY_ID", pets)
        self.assertNotIn("TD_PET_FORGE_ABILITY_ID", pets)
        self.assertIn("..setInterfaceIcon(tdPetCaptureIconPath())", pets)

    def test_forty_equipment_identities_resolve_existing_assets_or_native_icon(self):
        source = (ROOT / "wurst/items/TDItemData.wurst").read_text()
        block = source.split("public function tdItemIconPath(int itemId) returns string\n", 1)[1].split("\npublic function", 1)[0]
        paths = re.findall(r'return "([^"]+)"', block)
        self.assertEqual(len(paths), 41)  # 40 approved identities plus unknown fallback.
        for path in paths[:-1]:
            if path.startswith("war3mapImported"):
                self.assertTrue((ROOT / "imports" / Path(path.replace("\\\\", "/"))).is_file(), path)
            else:
                self.assertEqual(path, "ReplaceableTextures\\\\CommandButtons\\\\BTNGlove.blp")
        self.assertNotIn(" or ", block)

    def test_actions_and_critical_strike_bind_to_approved_rawcodes(self):
        entries = {a["name"]: a["rawcodes"] for a in self.manifest["assets"]}
        for name, rawcodes in {
            "InventoryCraft": ["A119"], "GroundUpgrade": ["Gupg"], "CaptureOrb": ["Ibal", "Pcap"],
            "CriticalStrike": ["A102", "A112"],
        }.items():
            self.assertEqual(entries[name], rawcodes)

    def test_future_tower_converter_uses_td_namespace_and_rejects_unknown_sources(self):
        for name in TOWER_ICON_NAMES:
            self.assertEqual(tower_icon_stem(name), "TDTower" + name)
        with self.assertRaisesRegex(ValueError, "Unknown tower icon source"):
            tower_icon_stem("TDPetFlamePhoenix")
        with self.assertRaisesRegex(ValueError, "Unknown tower icon source"):
            remove_legacy_tower_icon("TDPetFlamePhoenix")

    def test_future_converter_cleans_case_insensitive_legacy_names_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            normal = root / "imports/war3mapImported"
            disabled = root / "imports/ReplaceableTextures/CommandButtonsDisabled"
            normal.mkdir(parents=True)
            disabled.mkdir(parents=True)
            old = normal / "BTNBloodLust.blp"
            old_disabled = disabled / "DISBTNBLOODLUST.blp"
            retained = disabled / "DISBTNTDTowerBloodlust.blp"
            unrelated = normal / "BTNTDPetEmptySlot.blp"
            for path in [old, old_disabled, retained, unrelated]:
                path.write_bytes(b"sentinel")
            with patch("BuildEvolutionAssets.ROOT", root), patch("BuildEvolutionAssets.OUT", normal):
                remove_legacy_tower_icon("Bloodlust")
            self.assertFalse(old.exists())
            self.assertFalse(old_disabled.exists())
            self.assertEqual(retained.read_bytes(), b"sentinel")
            self.assertEqual(unrelated.read_bytes(), b"sentinel")

    def test_crop_hash_and_bounds_errors_are_rejected(self):
        entry = dict(self.manifest["assets"][0])
        entry["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source hash mismatch"):
            render_icon(entry)
        entry = dict(self.manifest["assets"][0])
        entry["crop"] = [-1, 0, 512, 484]
        with self.assertRaisesRegex(ValueError, "Invalid source crop"):
            render_icon(entry)

    def test_rebuild_preflights_every_source_before_any_import_write(self):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["assets"][-1]["source_sha256"] = "0" * 64
        paths = [ROOT / "imports" / e[key].replace("\\", "/") for e in manifest["assets"] for key in ["normal", "disabled"]]
        before = {path: path.read_bytes() for path in paths}
        with tempfile.TemporaryDirectory() as folder:
            temporary_manifest = Path(folder) / "manifest.json"
            temporary_manifest.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "source hash mismatch"):
                build(temporary_manifest)
        self.assertEqual({path: path.read_bytes() for path in paths}, before)

    def test_rebuild_rejects_output_hash_before_writing(self):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["assets"][0]["normal_sha256"] = "0" * 64
        path = ROOT / "imports" / manifest["assets"][0]["normal"].replace("\\", "/")
        before = path.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            temporary_manifest = Path(folder) / "manifest.json"
            temporary_manifest.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Manifest normal hash mismatch"):
                build(temporary_manifest)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
