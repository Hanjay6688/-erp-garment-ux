"""Synthetic parent protocol controls only; no accepted parent or ERP execution."""
from pathlib import Path
from hashlib import sha256
from unittest.mock import patch
import ast,copy,importlib.util,json,subprocess,unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('permanent_focused_parent_protocol',HERE/'persistent_financial.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def sample():
    return dict(status='ROOT_VERIFIED_CURRENT_JOIN_RETAINED35_FRESH_S05_BROWSER2_ALL5',head=module.PARENT_HEAD,
        tree=module.PARENT_TREE,run_id=module.PARENT_RUN,job_id=module.PARENT_JOB,complete37_qualified=True,
        package_all_five=True,actual_Native_cases=0,actual_browser_cases=2,fresh_cases=2,retained_Native_cases=31,
        retained_S03_browser_cases=4,retained_cases=35,retained_cases_are_not_fresh=True,
        qualified_candidate_Native_coverage=31,qualified_candidate_browser_coverage=6,candidate_case_coverage=37,
        fresh37_one_attempt=False,prior_runs_aggregated=True,source_invariant_reuse=True,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        production_go=False,independent_acceptance=False,synthetic_receipt_not_an_actual_qualification=True)

def check(value):
    raw=json.dumps(value,sort_keys=True).encode()
    with patch.object(module,'PARENT_RECEIPT',dict(bytes=len(raw),sha256=sha256(raw).hexdigest())):
        return module.qualified_receipt(raw)

class FocusedParentProtocol(unittest.TestCase):
    def test_unarmed_parent_still_refuses_before_any_receipt_or_ERP_import(self):
        self.assertIsNone(module.PARENT_RECEIPT)
        with self.assertRaisesRegex(ValueError,'TERMINAL_JOIN37_INTAKE_PENDING'):module.qualified_receipt(b'{}')

    def test_synthetic_retained35_plus_fresh2_keeps_truthful_counts(self):
        value=sample();self.assertEqual(check(value),value)
        self.assertEqual(value['actual_Native_cases'],0);self.assertFalse(value['fresh37_one_attempt'])

    def test_old_protocol_false_fresh_counts_wrong_identity_or_missing_invariance_refuses(self):
        for key,value in [('status','ROOT_VERIFIED_CURRENT_JOIN_NATIVE31_BROWSER6_ALL5'),('actual_Native_cases',31),
            ('actual_Native_cases',False),('actual_browser_cases',6),('retained_cases_are_not_fresh',False),
            ('prior_runs_aggregated',False),('source_invariant_reuse',False),('failed_run_relabelled_PASS',True),
            ('job_id',module.PARENT_JOB+1),('candidate_case_coverage',36)]:
            example=sample();example[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):check(example)
        example=sample();example.pop('source_invariant_reuse')
        with self.assertRaises(ValueError):check(example)

    def test_all_financial_and_fixture_functions_except_receipt_parser_are_unchanged(self):
        before=subprocess.check_output(['git','-C',str(ROOT),'show',
            '92a70c1fbe51208f098e82a27088649add4befd4:scripts/current-final-s03-sku-s05-preparation/persistent_financial.py'])
        functions=lambda raw:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(raw).body
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        old=functions(before);new=functions((HERE/'persistent_financial.py').read_bytes())
        self.assertEqual(set(old),set(new));self.assertEqual([name for name in old if old[name]!=new[name]],['qualified_receipt'])

if __name__=='__main__':unittest.main()
