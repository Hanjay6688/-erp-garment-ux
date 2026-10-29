"""Source/admission sensitivity controls, no new Native or browser claim."""
from pathlib import Path
import importlib.util,json,unittest
from hashlib import sha256
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('vendor_intake_check',HERE/'check.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)


class Controls(unittest.TestCase):
    def test_client_import_tamper_refused(self):
        with self.assertRaises(AssertionError):check.verify_files({'src/productionRecovery.ts':b'changed'})
    def test_SQL_import_tamper_refused(self):
        with self.assertRaises(AssertionError):check.verify_files({'scripts/cp7_vendor_receivable/receivable.sql':b'changed'})
    def test_B_driver_tamper_refused(self):
        with self.assertRaises(AssertionError):check.verify_files({'src/nativeStagedJob.ts':b'changed'})
    def test_missing_actual_component_closed(self):
        with self.assertRaisesRegex(ValueError,'CLOSED_ACTUAL_COMBINED11'):check.admit(None,b'',b'',{},'')
    def test_old_native7_label_cannot_qualify_combined11(self):
        raw=json.dumps(dict(label='CP7_VENDOR_RECEIVABLE_NATIVE7',status='PASS',qualification_commit='UNIT_ONLY')).encode();pkg=b'{}'
        pin=dict(head='UNIT_ONLY',original=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),package=dict(bytes=len(pkg),sha256=sha256(pkg).hexdigest()))
        with self.assertRaisesRegex(ValueError,'COMPLETE_COMBINED11_REQUIRED'):check.admit(pin,raw,pkg,{},'')

    def test_missing_actual_money_browser_closed(self):
        with self.assertRaisesRegex(ValueError,'CLOSED_ACTUAL_MONEY_BROWSER2'):
            check.admit_browser(None,b'',b'','',[],{},{})
    def test_B_analysis_browser_cannot_qualify_vendor_money_browser(self):
        raw=json.dumps(dict(label='CP7_COMBINED_FINANCE_BROWSER',status='PASS',qualification_commit='UNIT_ONLY')).encode();pkg=b'{}'
        pin=dict(head='UNIT_ONLY',original=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),package=dict(bytes=len(pkg),sha256=sha256(pkg).hexdigest()))
        with self.assertRaisesRegex(ValueError,'COMPLETE_MONEY_BROWSER2_REQUIRED'):
            check.admit_browser(pin,raw,pkg,'',[],{},{})


if __name__=='__main__':unittest.main()
