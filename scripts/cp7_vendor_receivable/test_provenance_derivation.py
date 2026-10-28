"""The declared successor may only add the precise orphan-vendor predicate."""
from pathlib import Path
import importlib.util,subprocess,unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('vendor_provenance_admission',ROOT/'scripts/current-vendor-receivable-qualification/admission.py')
admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
PATH='scripts/cp7_vendor_receivable/receivable.sql'


class ExactGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=subprocess.check_output(['git','-C',str(ROOT),'show','f30ffc8d7386d6b202c91e9f1b55e672af58c720:'+PATH])
        cls.after=(ROOT/PATH).read_bytes()

    def test_declared_predicate_only(self):
        self.assertEqual(admission.exact_provenance_guard(self.before,self.after)['scope'],'ONLY_PRIVATE_PROVE_OBSERVED_VENDOR_PREDICATE')

    def test_no_extra_sql_accepted(self):
        with self.assertRaisesRegex(ValueError,'EXACT_GUARD'):admission.exact_provenance_guard(self.before,self.after+b'\nselect 1;')

    def test_wrong_vendor_predicate_refused(self):
        with self.assertRaisesRegex(ValueError,'EXACT_GUARD'):admission.exact_provenance_guard(self.before,self.after.replace(b'owner_source.vendor_id=l.vendor_id',b'owner_source.vendor_id=p_vendor'))

    def test_duplicate_preimage_refused(self):
        with self.assertRaisesRegex(ValueError,'EXACT_GUARD'):admission.exact_provenance_guard(self.before+self.before,self.after)


if __name__=='__main__':unittest.main()
