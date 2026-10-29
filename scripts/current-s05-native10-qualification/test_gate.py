"""Retained-byte and semantic counterfixtures, never new Native credit."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import gzip
import importlib.util
import json
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('s05_test_retained_gate', HERE/'gate.py')
gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)


class RetainedGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((HERE/'CONFIG.json').read_bytes())
        cls.pin = cls.config['qualified_vendor11']
        cls.raw = gzip.decompress((ROOT/cls.pin['original']['path']).read_bytes())
        cls.pkg_raw = gzip.decompress((ROOT/cls.pin['package']['path']).read_bytes())
        cls.actual, cls.pkg = json.loads(cls.raw), json.loads(cls.pkg_raw)
        cls.runtime = {p: sha256((ROOT/p).read_bytes()).hexdigest() for p in gate.RUNTIME}

    def check(self, pin=None, raw=None, pkg=None, runtime=None, digest=None):
        return gate.checked(ROOT, pin or self.pin, raw or self.raw, pkg or self.pkg_raw,
                            self.runtime if runtime is None else runtime, digest or self.config['backend3194_sha256'])

    def test_real_retained_parent_is_admitted_with_zero_fresh_S05_credit(self):
        result = self.check()
        self.assertTrue(result['retained_only'])
        self.assertFalse(result['reexecuted'])
        self.assertEqual(result['head'], '41caaaed02c0d89b122ecf1ff221f6647141c335')
        self.assertEqual(result['fresh_S05_runtime_credit'], 0)
        self.assertEqual((result['retained_Native_cases'], result['retained_races'], result['retained_Auth_HTTP']), (7, 3, 1))
        self.assertNotIn('fresh_Native', result)
        self.assertEqual(gate.retained(ROOT, self.config)['original_sha256'], self.pin['original']['sha256'])

    def test_changed_raw_bytes_or_missing_prerequisite_are_rejected(self):
        for kind in ('original', 'package'):
            with self.subTest(kind=kind), self.assertRaises((ValueError, AssertionError)):
                self.check(raw=self.raw+b'\n' if kind == 'original' else None, pkg=self.pkg_raw+b'\n' if kind == 'package' else None)
        with self.assertRaisesRegex(ValueError, 'ACTUAL_ORIGINAL_AND_PACKAGE_REQUIRED'):
            gate.checked(ROOT, None, self.raw, self.pkg_raw, self.runtime, self.config['backend3194_sha256'])

    def test_semantic_counterfixtures_cannot_be_accepted_even_with_rebound_test_hashes(self):
        # Rebinding here tests the semantic gate beyond byte mismatch. The
        # production CONFIG/Original files are never changed by this control.
        for field in ('cp6_restored', 'advisor_gate', 'baseline_full22_all_rows_all_sequences_equal', 'baseline_advisors_equal',
                      'used_guard_refused_before_DDL', 'required_case_ids_pass'):
            actual, pkg = deepcopy(self.actual), deepcopy(self.pkg)
            actual[field] = False
            self.reject_rebound(actual, pkg, field)
        actual = deepcopy(self.actual); actual['focused_preuse_removal']['used_guard_before_DDL'] = False
        self.reject_rebound(actual, self.pkg, 'preuse inverse')
        for mutate in (
            lambda d: d.update(status='INCOMPLETE'),
            lambda d: d.update(qualification_commit='0'*40),
            lambda d: d['committed']['VENDOR_RECEIVABLE_NATIVE7_RACES3_AUTH1']['fresh_native7']['native'].update(counts={'PASS': 6}),
            lambda d: d['committed']['VENDOR_RECEIVABLE_NATIVE7_RACES3_AUTH1']['followup4']['http']['auth_counts'].update(restored=False),
            lambda d: d['committed']['VENDOR_RECEIVABLE_NATIVE7_RACES3_AUTH1']['followup4']['races'].update(database_remaining=1),
            lambda d: d['committed']['VENDOR_RECEIVABLE_NATIVE7_RACES3_AUTH1']['native_to_followup_handoff'].update(all22_equal_installed_product=False),
        ):
            actual = deepcopy(self.actual); mutate(actual); self.reject_rebound(actual, self.pkg, 'parent semantic')
        for field in gate.PACKAGE_GATES:
            pkg = deepcopy(self.pkg); pkg['gate'][field] = False; self.reject_rebound(self.actual, pkg, field)
        pkg = deepcopy(self.pkg); pkg['auth_users_after'] += 1; self.reject_rebound(self.actual, pkg, 'auth restoration')

    def reject_rebound(self, actual, pkg, label):
        raw, package = json.dumps(actual).encode(), json.dumps(pkg).encode()
        pin = deepcopy(self.pin)
        for kind, value in (('original', raw), ('package', package)):
            pin[kind].update(bytes=len(value), sha256=sha256(value).hexdigest())
        with self.subTest(label=label), self.assertRaises((ValueError, AssertionError)):
            self.check(pin, raw, package)

    def test_other_vendor_runtime_or_backend_is_rejected(self):
        wrong = dict(self.runtime); wrong[next(iter(wrong))] = '0'*64
        with self.assertRaises((ValueError, AssertionError)):
            self.check(runtime=wrong)
        with self.assertRaises((ValueError, AssertionError)):
            self.check(digest='0'*64)


if __name__ == '__main__':
    unittest.main()
