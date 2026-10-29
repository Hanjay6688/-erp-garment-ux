"""Meaningful closed-scope controls; no product runtime or DB import."""
from pathlib import Path
import importlib.util,unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('phase_source_control',HERE/'check.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


class Controls(unittest.TestCase):
    def test_exact_four_changes_and_other_two_function_bodies(self):
        before=(HERE/'evidence/BEFORE_materialize.sql').read_bytes()
        self.assertEqual(c.derivation(before,(c.ROOT/c.MAT).read_bytes())['substitutions'],4)
    def test_original_unfixed_or_business_or_finish_change_cannot_be_admitted(self):
        before=(HERE/'evidence/BEFORE_materialize.sql').read_bytes();after=(c.ROOT/c.MAT).read_bytes()
        for bad in (before,after.replace(b"phase='POSTED'",b"phase='RECONCILING'",1),after.replace(b'CP7_CREDIT_DE_FINAL_RECEIPT_OR_SCOPE_CHANGED',b'WEAKENED',1)):
            with self.assertRaises(ValueError):c.derivation(before,bad)
    def test_wrong_original_source_cannot_be_rebound(self):
        before=(HERE/'evidence/BEFORE_materialize.sql').read_bytes()
        with self.assertRaisesRegex(ValueError,'EXACT_D902'):c.derivation(before+b'\n',(c.ROOT/c.MAT).read_bytes())
    def test_exact_source_raw_receipts_and_local_complete_path(self):
        result=c.checked();self.assertEqual(result['local_typed_runtime_controls'],5);self.assertEqual(result['new_actual_Native_cases'],0)


if __name__=='__main__':unittest.main()
