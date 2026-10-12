"""Source-proven pointer remapping is strict, including stale old-line negatives."""
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from VerifyBloodlustDiagnostics import proved_diagnostic_view


class BloodlustDiagnosticProofTests(unittest.TestCase):
    def fixtures(self):
        before={'Equipment':'import A\n\nclass Cooldown\n\tint value\n'}
        current={'Equipment':'import A\nimport Preference\n\nclass Cooldown\n\tint value\n'}
        old='function alloc_Cooldown takes nothing returns nothing\ncall error("memory", "when calling error in Equipment, line 3")\nendfunction\n'
        new=old.replace('line 3','line 4')
        return old,new,before,current

    def test_source_equal_line_maps_one_exact_pointer(self):
        old,new,before,current=self.fixtures()
        view,proof=proved_diagnostic_view(new,old,current,before)
        self.assertEqual(view,old);self.assertEqual(proof[0]['before'],3);self.assertEqual(proof[0]['after'],4)

    def test_stale_old_or_unrelated_new_line_is_rejected(self):
        old,new,before,current=self.fixtures()
        for line in (3,2,5,999):
            with self.subTest(line=line),self.assertRaisesRegex(ValueError,'source-line provenance'):
                proved_diagnostic_view(new.replace('line 4','line '+str(line)),old,current,before)

    def test_changed_source_statement_cannot_be_mapped(self):
        old,new,before,current=self.fixtures();current['Equipment']=current['Equipment'].replace('class Cooldown','class Wrong')
        with self.assertRaisesRegex(ValueError,'source line is not unchanged'):
            proved_diagnostic_view(new,old,current,before)

    def test_diagnostic_count_change_is_rejected(self):
        old,new,before,current=self.fixtures()
        with self.assertRaisesRegex(ValueError,'count changed'):
            proved_diagnostic_view(new.replace('when calling error in Equipment','when calling wrong in Equipment'),old,current,before)
