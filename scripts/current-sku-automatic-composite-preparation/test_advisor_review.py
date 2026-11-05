"""Review exact PG17 authority originals and fail-closed finding composition."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import json
import os
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('automatic_private_authority_control_subject', HERE / 'advisor_review.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class Forbidden:
    def __getattribute__(self, name):
        raise AssertionError('Unaccepted authority binding inspected caller: ' + name)


class PrivateAuthority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = subject.source()
        cls.originals = json.loads(Path(os.environ['CP7_SKU_AUTHORITY_ORIGINALS']).read_bytes())

    def setUp(self):
        self.calls = []
        def closed(proof):
            if proof != {'retained': 'exact'}:
                raise ValueError('PARENT_AUTHORITY_CHANGED')
        def review(delta, manifest, proof, predecessor):
            closed(proof)
            self.calls.append(deepcopy(delta))
            return dict(unexplained=delta.get('added', []), gate=not delta.get('added') and delta.get('parent_ok', True))
        parent = SimpleNamespace(require_closed=closed, review=review)
        self.reviewer = subject.compose(parent, self.expected)
        self.proof = dict(parent={'retained': 'exact'}, SKU=deepcopy(self.expected['tables']))

    def finding(self, qualified):
        schema, name = qualified.split('.')
        return dict(name='rls_enabled_no_policy', level='INFO', metadata=dict(type='table', schema=schema, name=name))

    def test_real_PG17_catalogue_originals_accept_baseline_and_refuse_every_unsafe_change(self):
        self.assertTrue(self.originals['version'].startswith('PostgreSQL 17.'))
        self.assertEqual(len(self.originals['snapshots']), 18)
        for snapshot in self.originals['snapshots']:
            proof = dict(parent=self.proof['parent'], SKU=snapshot['authority'])
            with self.subTest(snapshot=snapshot['name']):
                if snapshot['must_refuse']:
                    with self.assertRaises(ValueError):
                        self.reviewer.require_closed(proof)
                else:
                    self.assertEqual(self.reviewer.require_closed(proof), proof)

    def test_exact_eleven_INFOs_retain_original_delta_and_parent_remainder(self):
        delta = dict(status='REVIEW_REQUIRED', added=[self.finding(n) for n in self.expected['eligible']], removed=[])
        before = deepcopy(delta)
        report = self.reviewer.review(delta, {}, self.proof, None)
        self.assertTrue(report['gate'])
        self.assertEqual(len(report['reviewed_SKU_private_info']), 11)
        self.assertEqual(report['complete_original_delta'], before)
        self.assertEqual(delta, before)
        self.assertEqual(self.calls, [before, dict(before, added=[])])
        for item in report['reviewed_SKU_private_info']:
            self.assertIn(item, report['predecessor_disposition']['unexplained'])

    def test_unknown_object_warning_duplicate_and_false_parent_are_never_promoted(self):
        good = self.finding(self.expected['eligible'][0])
        unsafe = [dict(good, level='WARN'), dict(good, name='security_definer_view'),
                  self.finding('erp.unrelated'), self.finding(next(n for n in self.expected['tables'] if n not in self.expected['eligible']))]
        for finding in unsafe:
            with self.subTest(finding=finding):
                self.assertFalse(self.reviewer.review(dict(status='REVIEW_REQUIRED', added=[finding]), {}, self.proof, None)['gate'])
        self.assertFalse(self.reviewer.review(dict(status='REVIEW_REQUIRED', added=[good, deepcopy(good)]), {}, self.proof, None)['gate'])
        self.assertFalse(self.reviewer.review(dict(status='REVIEW_REQUIRED', parent_ok=False, added=[good]), {}, self.proof, None)['gate'])
        bad = deepcopy(self.proof)
        bad['parent'] = {'retained': 'forged'}
        with self.assertRaisesRegex(ValueError, 'PARENT_AUTHORITY_CHANGED'):
            self.reviewer.require_closed(bad)

    def test_no_accepted_parent_gate_inspects_any_caller_or_cursor(self):
        with self.assertRaisesRegex(ValueError, 'CURRENT_PARENT_AND_FULL_NATIVE_LIFECYCLE_PENDING'):
            subject.bind(Forbidden(), Forbidden())
        for table in self.expected['tables']:
            bad = deepcopy(self.proof)
            bad['SKU'].pop(table)
            with self.subTest(missing=table), self.assertRaises(ValueError):
                self.reviewer.require_closed(bad)


if __name__ == '__main__':
    unittest.main()
