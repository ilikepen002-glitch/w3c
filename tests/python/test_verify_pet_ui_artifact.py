"""Pet UI regressions: packaged positive contract and targeted in-memory negatives.

The positive artifact tests intentionally fail on an old map until the approved
source changes are rebuilt. Negatives use a corrected copy and never edit a map.
"""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
import sys
import re
import struct
import subprocess
import tempfile
import unittest
from python_check_inputs import candidate_map
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerPlacementArtifact import unit_objects
import VerifyPetUIArtifact as verifier
from pet_artifact_fixture import correct_release_contract


class PetUIArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact = Mpq((candidate_map()).read_bytes())
        cls.abilities = ability_objects(cls.artifact.extract("war3map.w3a"))
        cls.units = unit_objects(cls.artifact.extract("war3map.w3u"))

    def test_actual_farmer_grid_is_eleven_cells_with_empty_blink_slot(self):
        verifier.verify_manager_farmer(self.abilities, self.units)

    def test_actual_twenty_three_manager_commands_match_pages(self):
        verifier.verify_manager_commands(self.abilities)
        verifier.verify_manager_list(self.abilities)
        verifier.verify_manager_preview(self.abilities)

    def test_actual_no_removed_hunt_ghost_or_attachment_remains(self):
        verifier.verify_no_hunt_objects(self.abilities, self.units)

    def test_actual_all_channel_orders_are_globally_unique(self):
        verifier.verify_global_channel_orders(self.abilities)

    def test_actual_wild_and_capture_tooltips_are_capture_only(self):
        verifier.verify_capture_only(self.abilities, self.units, current_manager=True)

    def test_actual_cultivation_command_omits_detail_release_entrance(self):
        verifier.verify_cultivation_command(self.abilities, current_manager=True)

    def test_actual_native_manager_uses_real_session_whitelists(self):
        verifier.verify_manager_jass(self.artifact.extract("war3map.j").decode("utf-8"))

    def test_actual_thirteen_displays_have_species_quality_identity(self):
        verifier.verify_manager_units(self.units)

    def test_actual_exact_legal_slots_distinguish_bright_locked_empty_and_quality_levels(self):
        verifier.verify_slot_icons(self.abilities, current_manager=True)

    def test_actual_imports_decode_and_match_source_hashes(self):
        verifier.verify_imported_icons(self.artifact, ROOT)

    def test_actual_current_ui_preserves_complete_global_startup_sequence(self):
        from VerifyStartupArtifact import verify
        result = verify(self.artifact.extract('war3map.j').decode('utf-8'))
        self.assertIn('first-wave epoch', result)
        self.assertIn('watchdog lifecycle', result)

    def test_obsolete_per_button_registration_contract_is_not_current_startup(self):
        from VerifyStartupArtifact import verify
        with self.assertRaisesRegex(ValueError, 'Pet UI startup missed handlers'):
            verify(self.artifact.extract('war3map.j').decode('utf-8'), expected_pet_registrations=515)

    def test_actual_shared_listener_registers_once_and_routes_all_buttons(self):
        from VerifyPetStartupArtifact import measure, verify_routing
        script = self.artifact.extract('war3map.j').decode('utf-8')
        self.assertEqual(measure(script)['registrations'], 2)
        count = 2433 if len(verifier.manager_species(self.abilities, self.units)) == 15 else 513
        self.assertIn(f'{count} button IDs', verify_routing(script))


class HistoricalPetUINegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = Mpq(subprocess.run(["git", "show", "b7e3d051e98c2b18caafed4ab6e036700a6ee64c:ExampleMap.w3x"], cwd=ROOT, check=True, capture_output=True).stdout)
        cls.corrected_abilities = ability_objects(artifact.extract("war3map.w3a"))
        cls.corrected_units = unit_objects(artifact.extract("war3map.w3u"))
        correct_release_contract(cls.corrected_abilities, cls.corrected_units)
        # Frozen formal predecessor; current-artifact positives above stay raw.
        cls.historical_script = artifact.extract('war3map.j').decode('utf-8')
        # Permit deterministic negative coverage before the next map rebuild.
        for rawcode, (x, y, _, _) in verifier.EXPECTED.items():
            cls.set_field(cls.corrected_abilities, rawcode, "abpx", x)
            cls.set_field(cls.corrected_abilities, rawcode, "abpy", y)
        for rawcode, stem in verifier.FARMER_ICONS.items():
            cls.set_field(cls.corrected_abilities, rawcode, "aart", verifier.icon_path(stem))
            if rawcode != "Geqb":
                cls.set_field(cls.corrected_abilities, rawcode, "arar", verifier.icon_path(stem))
        for rawcode, spec in verifier.COLLECTION_COMMANDS.items():
            for field in ("aart", "arar"):
                cls.set_field(cls.corrected_abilities, rawcode, field, verifier.icon_path(spec[4]))
        for species, (_, stem) in enumerate(verifier.SPECIES, 1):
            for field in ("uico", "ussi"):
                cls.corrected_units[f"pd0{species}"][field] = verifier.icon_path(stem)
        for slot in range(4):
            cls.set_field(cls.corrected_abilities, f"s{slot}80", "aart", verifier.icon_path("TDPetEmptySlot"))

    @staticmethod
    def set_field(abilities, rawcode, field, value, level=0):
        matches = [key for key in abilities[rawcode][1] if key[0] == field and key[1] == level]
        if matches:
            key = matches[0]
            kind = abilities[rawcode][1][key][0]
        else:
            key = (field, level, 0)
            kind = 3 if isinstance(value, str) else 0
        abilities[rawcode][1][key] = (kind, value)

    def setUp(self):
        self.abilities = deepcopy(self.corrected_abilities)
        self.units = deepcopy(self.corrected_units)

    def test_historical_dialog_overload_rename_keeps_integer_hotkey_contract(self):
        script = self.historical_script
        native = re.search(r'^function (dialog_addButton(?:_\d+)*) takes dialog \w+, string \w+, integer \w+ returns button', script, re.M)
        self.assertIsNotNone(native)
        renamed = re.sub(r'\b' + re.escape(native[1]) + r'\b', 'dialog_addButton_982', script)
        verifier.verify_dialog_hotkeys(renamed)

    def test_historical_dialog_native_hotkey_removal_is_rejected(self):
        script = self.historical_script
        native = re.search(r'^function dialog_addButton(?:_\d+)* takes dialog (\w+), string (\w+), integer (\w+) returns button', script, re.M)
        self.assertIsNotNone(native)
        old = f'DialogAddButton({native[1]}, {native[2]}, {native[3]})'
        self.assertIn(old, script)
        changed = script.replace(old, f'DialogAddButton({native[1]}, {native[2]}, 0)', 1)
        with self.assertRaisesRegex(ValueError, 'real integer hotkey'): verifier.verify_dialog_hotkeys(changed)

    def test_corrected_fixture_satisfies_all_object_contracts(self):
        verifier.verify_farmer_grid(self.abilities, self.units)
        verifier.verify_collection_commands(self.abilities)
        verifier.verify_species_identity(self.units)
        verifier.verify_slot_icons(self.abilities)
        verifier.verify_pet_core(self.abilities, self.units)

    def test_rejects_each_farmer_cell_conflict(self):
        for rawcode in verifier.EXPECTED:
            with self.subTest(command=rawcode):
                abilities = deepcopy(self.abilities)
                self.set_field(abilities, rawcode, "abpx", 0)
                self.set_field(abilities, rawcode, "abpy", 0)
                with self.assertRaisesRegex(ValueError, f"{rawcode}: farmer cell overlaps"):
                    verifier.verify_farmer_grid(abilities, self.units)

    def test_rejects_old_farmer_position(self):
        self.set_field(self.abilities, "Geqb", "abpx", 1)
        self.set_field(self.abilities, "Geqb", "abpy", 2)
        with self.assertRaisesRegex(ValueError, "farmer cell overlaps"):
            verifier.verify_farmer_grid(self.abilities, self.units)

    def test_rejects_cultivation_command_bad_name_tooltip_description_or_hotkey(self):
        cases = [("anam", 0, "培养 / 释放", "cultivation name"),
                 ("atp1", 1, "洗练 / 开栏 / 释放(C) (C)", "cultivation tooltip"),
                 ("aub1", 1, "可洗练或开栏", "cultivation description"),
                 ("ahky", 0, "V", "ahky cultivation hotkey"),
                 ("arhk", 0, "V", "arhk cultivation hotkey"),
                 ("auhk", 0, "V", "auhk cultivation hotkey")]
        for field, level, text, reason in cases:
            with self.subTest(field=field):
                abilities = deepcopy(self.abilities)
                self.set_field(abilities, "Pc06", field, text, level)
                with self.assertRaisesRegex(ValueError, reason):
                    verifier.verify_cultivation_command(abilities)

    def test_rejects_capture_tooltip_hunt_at_any_inventory_level(self):
        for level in (1, 31, 61):
            with self.subTest(level=level):
                abilities = deepcopy(self.abilities)
                self.set_field(abilities, "Pcap", "aub1", "捕获或猎杀二选一", level)
                with self.assertRaisesRegex(ValueError, f"Pcap level {level}: obsolete wild-hunt text"):
                    verifier.verify_capture_only(abilities, self.units)

    def test_rejects_hunt_on_last_wild_description(self):
        self.units["p203"]["ides"] = "捕获或主动猎杀二选一。"
        with self.assertRaisesRegex(ValueError, "p203: wild description"):
            verifier.verify_capture_only(self.abilities, self.units)

    def test_rejects_phnt_parent_or_nonmenu_reference(self):
        for target in ("parent", "requirement", "unit_attachment"):
            with self.subTest(target=target):
                abilities, units = deepcopy(self.abilities), deepcopy(self.units)
                if target == "parent":
                    abilities["Xhnt"] = ("Phnt", {})
                elif target == "requirement":
                    self.set_field(abilities, "Gupg", "areq", "Phnt")
                else:
                    units["pv03"]["uabi"] += ",Phnt"
                with self.assertRaisesRegex(ValueError, "removed Phnt remains"):
                    verifier.verify_no_hunt_objects(abilities, units)

    def test_rejects_channel_collision_outside_collection_and_at_later_level(self):
        for owner in ("A109", "A133", "Gupg"):
            with self.subTest(owner=owner):
                abilities = deepcopy(self.abilities)
                order = verifier.field_value(abilities[owner][1], "Ncl6", 1)
                self.set_field(abilities, "Pcap", "Ncl6", order, 61)
                with self.assertRaisesRegex(ValueError, "Channel order.*collides|consistent across all levels"):
                    verifier.verify_global_channel_orders(abilities)

    def test_rejects_nonchannel_object_with_colliding_channel_field(self):
        order = verifier.field_value(self.abilities["Gupg"][1], "Ncl6", 1)
        self.abilities["Xord"] = ("AOcr", {("Ncl6", 1, 6): (3, order)})
        with self.assertRaisesRegex(ValueError, "Channel order.*collides"):
            verifier.verify_global_channel_orders(self.abilities)

    def test_rejects_missing_or_bad_global_channel_order(self):
        for change in ("missing", "empty", "column", "type"):
            with self.subTest(change=change):
                abilities = deepcopy(self.abilities)
                fields = abilities["Pcap"][1]
                order = fields.pop(("Ncl6", 61, 6))
                if change == "empty":
                    fields[("Ncl6", 61, 6)] = (3, "")
                elif change == "column":
                    fields[("Ncl6", 61, 5)] = order
                elif change == "type":
                    fields[("Ncl6", 61, 6)] = (0, 1)
                with self.assertRaisesRegex(ValueError, "Channel must define|invalid Channel order|consistent across all levels"):
                    verifier.verify_global_channel_orders(abilities)

    def test_rejects_collection_same_icon(self):
        self.set_field(self.abilities, "Pc02", "aart", verifier.icon_path("TDPetPrevious"))
        with self.assertRaisesRegex(ValueError, "Collection command icons must be distinct"):
            verifier.verify_collection_commands(self.abilities)

    def test_rejects_collection_cell_conflict(self):
        self.set_field(self.abilities, "Pc02", "abpx", 1)
        with self.assertRaisesRegex(ValueError, "Pc02: collection cell overlaps Pc01"):
            verifier.verify_collection_commands(self.abilities)

    def test_rejects_collection_colliding_or_invalid_order(self):
        order = verifier.field_value(self.abilities["Pc01"][1], "Ncl6", 1)
        for changed, reason in ((order, "base orders collide"), ("", "invalid Channel order"),
                                ("unknown order!", "invalid Channel order")):
            with self.subTest(order=changed):
                abilities = deepcopy(self.abilities)
                self.set_field(abilities, "Pc02", "Ncl6", changed, 1)
                with self.assertRaisesRegex(ValueError, reason):
                    verifier.verify_collection_commands(abilities)

    def test_unique_collection_order_is_not_pinned_to_allocator_index(self):
        self.set_field(self.abilities, "Pc02", "Ncl6", "attack", 1)
        verifier.verify_collection_commands(self.abilities)

    def test_rejects_wrong_custom_path_prefix(self):
        for field in ("aart", "arar"):
            with self.subTest(field=field):
                abilities = deepcopy(self.abilities)
                self.set_field(abilities, "Pc02", field,
                               verifier.NORMAL_PREFIX + verifier.icon_path("TDPetNext"))
                with self.assertRaisesRegex(ValueError, "Pc02: .*icon path mismatch"):
                    verifier.verify_collection_commands(abilities)

    def test_rejects_species_without_portrait_or_wrong_species(self):
        for species in range(1, 4):
            for field in ("uico", "ussi"):
                with self.subTest(species=species, field=field):
                    units = deepcopy(self.units)
                    units[f"pd0{species}"][field] = verifier.icon_path("TDPetCollection")
                    with self.assertRaisesRegex(ValueError, f"pd0{species}: {field} species icon mismatch"):
                        verifier.verify_species_identity(units)

    def test_rejects_empty_locked_bright_icon_mixups(self):
        for rawcode, bad_icon, reason in [
            ("s080", verifier.skill_icon_path(64), "s080: empty slot icon mismatch"),
            ("s040", verifier.icon_path("TDPetEmptySlot"), "s040: locked skill icon mismatch"),
            ("s000", verifier.skill_icon_path(64), "s000: bright skill icon mismatch"),
            ("s044", verifier.skill_icon_path(64), "s044: locked skill icon mismatch"),
        ]:
            with self.subTest(rawcode=rawcode):
                abilities = deepcopy(self.abilities)
                self.set_field(abilities, rawcode, "aart", bad_icon)
                with self.assertRaisesRegex(ValueError, reason):
                    verifier.verify_slot_icons(abilities)

    def test_rejects_missing_locked_explanation(self):
        self.set_field(self.abilities, "s240", "aub1", "已有技能", 1)
        with self.assertRaisesRegex(ValueError, "s240: missing resonance explanation"):
            verifier.verify_slot_icons(self.abilities)

    def test_rejects_empty_label_as_locked(self):
        self.set_field(self.abilities, "s280", "atp1", "空栏 共鸣锁定", 1)
        with self.assertRaisesRegex(ValueError, "s280: empty slot must not be resonance locked"):
            verifier.verify_slot_icons(self.abilities)

    def test_rejects_wrong_locked_skill_or_quality_identity(self):
        self.set_field(self.abilities, "s240", "atp1", "|cffffffff白|r 战意 [共鸣锁定]", 1)
        with self.assertRaisesRegex(ValueError, "s240: skill/quality identity label changed"):
            verifier.verify_slot_icons(self.abilities)

    def test_rejects_locked_description_for_different_skill(self):
        self.set_field(self.abilities, "s240", "aub1", "技能已获得，尚未生效。完成本路第4波解锁。|n错误技能", 1)
        with self.assertRaisesRegex(ValueError, "s240: locked skill description mismatch"):
            verifier.verify_slot_icons(self.abilities)

    def test_rejects_passive_slot_combat_effect(self):
        self.set_field(self.abilities, "s040", "Ocr1", 25.0, 1)
        with self.assertRaisesRegex(ValueError, "s040: passive display must have no critical-strike combat effect"):
            verifier.verify_slot_icons(self.abilities)

    def test_rejects_missing_import_with_precise_path(self):
        class MissingArchive:
            def has(self, path):
                return False
        with self.assertRaisesRegex(ValueError, "Missing packaged pet UI icon: war3mapImported"):
            verifier.verify_imported_icons(MissingArchive(), ROOT)


def source_wiring_problems(pet_source, item_source):
    problems = []
    command = pet_source.split("function command(", 1)[1].split("@compiletime", 1)[0]
    if "..presetIcon(icon)" in command:
        problems.append("command helper still applies presetIcon to complete paths")
    if "..setIconNormal(icon)" not in command or "..setIconResearch(icon)" not in command:
        problems.append("command helper lacks explicit normal/research icon setters")
    if "tdPetUICommandIconPath(cmd)" not in pet_source:
        problems.append("collection commands bypass semantic icon mapping")
    if "..setIconGameInterface(tdPetSpeciesIconPath(species))" not in pet_source:
        problems.append("species displays lack explicit interface icons")
    if "..setIconScoreScreen(tdPetSpeciesIconPath(species))" not in pet_source:
        problems.append("species displays lack explicit score icons")
    if "BTNSelectHeroOn" in pet_source or "setIconNormal(tdPetSlotIconPath(variant))" not in pet_source:
        problems.append("empty/bright/locked slots bypass independent icon mapping")
    if "..setIconNormal(tdPetMenuToolsIconPath())" not in item_source:
        problems.append("function menu bypasses tools icon mapping")
    return problems


class PetUISourceTests(unittest.TestCase):
    def test_cli_rejects_obsolete_extra_game_directory_argument(self):
        with patch.object(sys, "argv", ["VerifyPetUIArtifact.py", "map.w3x", "game-directory"]), \
                self.assertRaisesRegex(ValueError, "Usage:"):
            verifier.main()

    def test_imported_icon_wiring_uses_shared_helpers_and_explicit_setters(self):
        pet = (ROOT / "wurst/pets/TDPetObjectGen.wurst").read_text(encoding="utf-8")
        item = (ROOT / "wurst/items/TDItemObjectGen.wurst").read_text(encoding="utf-8")
        self.assertEqual(source_wiring_problems(pet, item), [])


class PetUIResourceNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_data = {
            verifier.icon_path(stem, disabled):
            (ROOT / "imports" / verifier.icon_path(stem, disabled).replace("\\", "/")).read_bytes()
            for stem in verifier.ICON_STEMS for disabled in (False, True)
        }

    def setUp(self):
        self.data = dict(self.source_data)

    def verify(self, source_matches=False):
        class Archive:
            def __init__(self, data):
                self.data = data
            def has(self, path):
                return path in self.data
            def extract(self, path):
                return self.data[path]
        with redirect_stdout(io.StringIO()):
            if not source_matches:
                return verifier.verify_imported_icons(Archive(self.data), ROOT)
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for path, data in self.data.items():
                    file = root / "imports" / path.replace("\\", "/")
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes(data)
                return verifier.verify_imported_icons(Archive(self.data), root)

    def test_source_icons_satisfy_complete_resource_contract(self):
        self.verify()

    def test_rejects_missing_disabled_import(self):
        path = verifier.icon_path("TDPetMenuTools", True)
        del self.data[path]
        with self.assertRaisesRegex(ValueError, "Missing packaged pet UI icon: ReplaceableTextures"):
            self.verify()

    def test_rejects_packaged_hash_mismatch(self):
        path = verifier.icon_path("TDPetNext")
        data = bytearray(self.data[path])
        data[-1] ^= 1
        self.data[path] = bytes(data)
        with self.assertRaisesRegex(ValueError, "BTNTDPetNext.blp: packaged icon hash differs from source"):
            self.verify()

    def test_rejects_malformed_blp_or_wrong_dimensions(self):
        path = verifier.icon_path("TDPetMenuTools")
        for change, reason in [("magic", "invalid/truncated BLP1"),
                               ("size", "icon must be 64x64"),
                               ("mip", "mip 0 out of bounds or overlaps")]:
            with self.subTest(change=change):
                self.data = dict(self.source_data)
                data = bytearray(self.data[path])
                if change == "magic":
                    data[:4] = b"PNG!"
                elif change == "size":
                    struct.pack_into("<I", data, 12, 128)
                else:
                    struct.pack_into("<I", data, 28, 1179)
                self.data[path] = bytes(data)
                with self.assertRaisesRegex(ValueError, reason):
                    self.verify(source_matches=True)

    def test_rejects_duplicate_semantic_artwork(self):
        self.data[verifier.icon_path("TDPetNext")] = self.data[verifier.icon_path("TDPetPrevious")]
        with self.assertRaisesRegex(ValueError, "duplicate semantic icon artwork"):
            self.verify(source_matches=True)

    def test_rejects_colored_disabled_artwork(self):
        path = verifier.icon_path("TDPetMenuTools", True)
        data = bytearray(self.data[path])
        # Recolor every palette entry, preserving all valid format metadata.
        for index in range(256):
            value = max(20, data[156 + index * 4])
            data[156 + index * 4:159 + index * 4] = bytes((0, 0, value))
        self.data[path] = bytes(data)
        with self.assertRaisesRegex(ValueError, "disabled icon must be grayscale"):
            self.verify(source_matches=True)

    def test_rejects_disabled_artwork_without_dimming(self):
        path = verifier.icon_path("TDPetMenuTools", True)
        data = bytearray(self.data[path])
        for index in range(256):
            value = 200 + data[156 + index * 4] // 5
            data[156 + index * 4:159 + index * 4] = bytes((value, value, value))
        self.data[path] = bytes(data)
        with self.assertRaisesRegex(ValueError, "disabled icon must be visibly dimmer than normal"):
            self.verify(source_matches=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
