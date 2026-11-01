"""Closed CSS source admission controls, with zero ERP case credit."""
from pathlib import Path
import importlib.util,subprocess,unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('reviewed_S05_css',HERE/'ui_layout.py')
layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)

class LayoutAdmission(unittest.TestCase):
    def test_exact_original_and_reversible_four_hunks(self):
        original=subprocess.check_output(['git','-C',str(ROOT),'show','b25eaae55a144aa03cc05f8f77109f5d0b02fbfb:'+layout.PATH])
        derived,proof=layout.derive(original)
        self.assertEqual(derived,(ROOT/layout.PATH).read_bytes())
        self.assertEqual(proof['counted_changes'],4)
        self.assertTrue(proof['complete_original_recovered'])
        self.assertFalse(proof['backend_or_reader_oracle_changed'])

    def test_changed_or_already_derived_original_refuses(self):
        original=subprocess.check_output(['git','-C',str(ROOT),'show','b25eaae55a144aa03cc05f8f77109f5d0b02fbfb:'+layout.PATH])
        for raw in (original+b'\n',(ROOT/layout.PATH).read_bytes(),original.replace(b'120px',b'121px')):
            with self.subTest(raw=raw[:20]),self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_CSS_REQUIRED'):
                layout.derive(raw)

if __name__=='__main__':unittest.main()
