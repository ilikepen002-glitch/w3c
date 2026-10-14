"""Upgrade-only refund policy; engine money timing is an explicit test boundary."""
from pathlib import Path
import sys
import unittest
from python_check_inputs import candidate_map

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyUpgradeRefundArtifact as verifier
from GenerateTowerTerrainMask import Mpq
from VerifyTowerPlacementArtifact import unit_objects


class UpgradeRefundSourceTests(unittest.TestCase):
    def test_upgrade_only_source_and_no_script_compensation(self):
        verifier.validate_source()

    def test_rejects_missing_partial_or_misspelled_native_refund(self):
        text = (ROOT / 'imports/war3mapMisc.txt').read_text()
        for replacement in ('UpgradeRefundRate=0.8', 'UpgradeRefundRate=0.75',
                            'UpgradeRefundRate=0.0', 'UpgradeRefund=1.0', ''):
            with self.subTest(replacement=replacement), self.assertRaisesRegex(ValueError, '100%'):
                verifier.validate_misc(text.replace('UpgradeRefundRate=1.0', replacement))

    def test_rejects_changes_to_other_refund_types_or_gameplay_constants(self):
        text = (ROOT / 'imports/war3mapMisc.txt').read_text()
        for addition in ('ConstructionRefundRate=1.0', 'ResearchRefundRate=0.8',
                         'TrainRefundRate=0.8', 'RelativeUpgradeCost=0'):
            with self.subTest(addition=addition), self.assertRaisesRegex(ValueError, 'Unrelated'):
                verifier.validate_misc(text + addition + '\n')


class UpgradeRefundActualArtifactTests(unittest.TestCase):
    def test_packed_upgrade_only_constant_and_lifecycle_no_double_credit(self):
        verifier.validate_artifact(candidate_map())

    def test_rejects_script_compensation_on_top_of_native_refund(self):
        archive = Mpq(candidate_map().read_bytes())
        script = archive.extract('war3map.j').decode()
        # Mutate the actual packed cancel body, not a reimplemented policy.
        start = script.index('function tdHandleTowerUpgradeCancelled takes ')
        end = script.index('endfunction', start)
        mutant = script[:end] + 'call tdGainGold(0, 1)\n' + script[end:]
        with self.assertRaisesRegex(ValueError, 'native refund'):
            verifier.replay(mutant, unit_objects(archive.extract('war3map.w3u')))
