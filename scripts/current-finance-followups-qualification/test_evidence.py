from copy import deepcopy
from hashlib import sha256
import json
import unittest
import evidence


class ExactParentEvidence(unittest.TestCase):
    def setUp(self):
        ids = ['N' + str(i) for i in range(13)] + ['CRON']
        self.source = {'case_ids': ids}
        self.installation = {'product': 'unchanged'}
        self.actual = dict(status='PASS', qualification_commit='expected',
            source_declaration={'qualification': self.source, 'current_installation': self.installation},
            native={'status': 'PASS', 'counts': {'PASS': 13}, 'complete_boundary_restored': True,
                    'cases': {key: {'status': 'PASS'} for key in ids[:-1]}},
            committed={'CRON': {'status': 'PASS'}}, expected_case_count=14, observed_case_count=14,
            production_go=False, independent_acceptance=False, default_adopted=False,
            full_combined_final_qualification=False, full_parent_inverse_repeated=False,
            focused_preuse_removal={'full_parent_inverse_repeated': False},
            baseline_role_cleanup={'baseline_roles_exact': True},
            **{key: True for key in evidence.REQUIRED})
        self.package = {'gate': {key: True for key in evidence.GATES}}

    def call(self, actual=None, package=None, mutate_binding=None):
        raw = json.dumps(actual or self.actual).encode()
        package_raw = json.dumps(package or self.package).encode()
        binding = dict(status='PASS', head='expected', bytes=len(raw), sha256=sha256(raw).hexdigest(),
                       package_bytes=len(package_raw), package_sha256=sha256(package_raw).hexdigest())
        if mutate_binding:
            mutate_binding(binding)
        return evidence.accepted(binding, raw, package_raw, self.source, self.installation)

    def test_exact_parent_accepted_without_full_inverse_credit(self):
        self.assertFalse(self.call()['full_parent_inverse_repeated'])

    def test_pending_parent_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'PARENT_NOT_ACCEPTED'):
            self.call(mutate_binding=lambda b: b.update(status='RUNNING_NOT_PASS'))

    def test_every_proof_required(self):
        for key in evidence.REQUIRED:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'REQUIRED_PROOF'):
                changed = deepcopy(self.actual)
                changed[key] = False
                self.call(changed)

    def test_empty_partial_and_failed_package_gates_refused(self):
        for gates in ({}, {'installed': True}, {**self.package['gate'], 'writer_runtime': False}):
            with self.subTest(gates=gates), self.assertRaisesRegex(ValueError, 'PACKAGE_NOT_PASS'):
                self.call(package={'gate': gates})

    def test_tampered_original_and_package_bytes_refused(self):
        for key in ('bytes', 'sha256', 'package_bytes', 'package_sha256'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'ORIGINAL_CHANGED'):
                self.call(mutate_binding=lambda b: b.update({key: 'wrong'}))

    def test_missing_cron_and_incomplete_native_refused(self):
        for part in ('committed', 'native'):
            changed = deepcopy(self.actual)
            if part == 'committed':
                changed[part] = {}
            else:
                changed['native']['cases']['N0']['status'] = 'INCOMPLETE'
            with self.subTest(part=part), self.assertRaisesRegex(ValueError, 'CASES_CHANGED'):
                self.call(changed)

    def test_both_wrong_case_counts_refused(self):
        changed = deepcopy(self.actual)
        changed.update(observed_case_count=13, expected_case_count=13)
        with self.assertRaisesRegex(ValueError, 'CASE_COUNT_CHANGED'):
            self.call(changed)

    def test_changed_product_and_unrestored_roles_refused(self):
        changed = deepcopy(self.actual)
        changed['source_declaration']['current_installation']['product'] = 'different'
        with self.assertRaisesRegex(ValueError, 'SOURCE_CHANGED'):
            self.call(changed)
        changed = deepcopy(self.actual)
        changed['baseline_role_cleanup']['baseline_roles_exact'] = False
        with self.assertRaisesRegex(ValueError, 'RESTORATION_CHANGED'):
            self.call(changed)
