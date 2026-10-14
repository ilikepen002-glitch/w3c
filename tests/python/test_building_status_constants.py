"""Narrow native building-status fix: preserve inventory ranges, no runtime work."""
import configparser
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyInventoryRangeArtifact as gate

VALID = b'[Misc]\nPickupItemRange=1200.0\nDropItemRange=1200.0\nGiveItemRange=1200.0\nDisplayBuildingStatus=1\n'


class BuildingStatusConstantsTests(unittest.TestCase):
    def test_source_contains_exact_supported_constants(self):
        self.assertEqual(gate.verify_constants((ROOT / 'imports/war3mapMisc.txt').read_bytes()), gate.EXPECTED)

    def test_semantic_parsing_accepts_order_and_crlf(self):
        lines = VALID.decode().splitlines()
        data = ('\r\n'.join([lines[0]] + list(reversed(lines[1:]))) + '\r\n').encode()
        self.assertEqual(gate.verify_constants(data), gate.EXPECTED)

    def test_invalid_constants_rejected(self):
        cases = (
            VALID.replace(b'DisplayBuildingStatus=1\n', b''),
            VALID.replace(b'DisplayBuildingStatus=1', b'DisplayBuildingStatus=0'),
            VALID.replace(b'DisplayBuildingStatus', b'BuildingStatusDisplay'),
            VALID.replace(b'[Misc]', b'[Display]'),
            VALID.replace(b'GiveItemRange=1200.0', b'GiveItemRange=100.0'),
            VALID + b'DisplayBuildingStatus=0\n',
            VALID + b'FoodCeiling=1\n',
            b'[DEFAULT]\nDisplayBuildingStatus=1\n' + VALID,
        )
        for data in cases:
            with self.subTest(data=data):
                with self.assertRaises((AssertionError, configparser.Error)):
                    gate.verify_constants(data)

    def test_archive_requires_root_and_rejects_asset_prefix(self):
        class Archive:
            def __init__(self, root=True, prefixed=False):
                self.root, self.prefixed = root, prefixed
            def has(self, name):
                return self.root if name == 'war3mapMisc.txt' else self.prefixed
            def extract(self, name):
                self.assert_name = name
                return VALID
        with patch.object(gate.Path, 'read_bytes', return_value=b'fake-map'):
            for root, prefixed in ((False, False), (False, True), (True, True)):
                with patch.object(gate, 'Mpq', return_value=Archive(root, prefixed)):
                    with self.assertRaises(AssertionError):
                        gate.verify('fake.w3x')
            with patch.object(gate, 'Mpq', return_value=Archive()):
                result = gate.verify('fake.w3x')
                self.assertTrue(result['display_building_status'])
                self.assertEqual(result['pickup_drop_give_range'], 1200)


if __name__ == '__main__':
    unittest.main()
