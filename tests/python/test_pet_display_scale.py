"""Narrow attached-scale regressions; no Grill/native rendering."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from VerifyPetDisplayScale import verify

class PetDisplayScaleTests(unittest.TestCase):
    def test_fifteen_float_and_gesture_envelopes_and_source_isolation(self):
        result=verify()
        self.assertEqual(len(result['models']),15)
        self.assertTrue(result['heightFormulaUnchanged'])
        self.assertEqual(result['wildScaleUnchanged'],2.55)

    def check_bad_text(self, old, new, message):
        original=Path.read_text
        def changed(path,*args,**kwargs):
            return original(path,*args,**kwargs).replace(old,new)
        with patch.object(Path,'read_text',changed):
            with self.assertRaisesRegex(AssertionError,message): verify()

    def test_overscale_rejected(self):
        self.check_bad_text('return 0.78','return 2.25','Unsafe attached scale')

    def test_wild_scale_change_rejected(self):
        self.check_bad_text('setScalingValue(2.55)','setScalingValue(4.25)','non-attached object')

    def test_height_change_rejected(self):
        self.check_bad_text('+ 24.0','+ 48.0','Height/animation')

    def test_normalization_loss_rejected(self):
        self.check_bad_text('return 0.78','return 1.20','Float silhouette')

if __name__=='__main__': unittest.main()
