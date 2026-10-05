"""Declared byte/ZIP stand-ins for read-only proof retention; zero Native credit."""
import hashlib
import copy
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from cp7_native_artifact_projection import retain_requested_images, verify_declared_case_counts


class ExactImageBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name)
        self.name = 'P17_MANUAL_PROVIDER_OFFLINE_MOBILE.png'
        # Header-shaped bytes only: this is never a rendered/visual proof.
        self.raw = b'\x89PNG\r\n\x1a\nDECLARED_BYTE_STANDIN'
        self.receipt = {'all_zip_members': {self.name: {
            'bytes': len(self.raw), 'sha256': hashlib.sha256(self.raw).hexdigest()}}}

    def copy(self, requested, raw=None):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr(self.name, self.raw if raw is None else raw)
        with zipfile.ZipFile(buffer) as archive:
            return retain_requested_images(archive, self.receipt, requested, self.destination)

    def test_exact_bytes_and_digest_preserved_without_visual_credit(self):
        result = self.copy([self.name])
        self.assertEqual((self.destination/'images'/self.name).read_bytes(), self.raw)
        self.assertEqual(result[self.name]['sha256'], self.receipt['all_zip_members'][self.name]['sha256'])
        self.assertEqual(result[self.name]['visual_review'], 'NOT_AUTOMATICALLY_QUALIFIED')

    def test_empty_request_never_creates_an_image(self):
        self.assertEqual(self.copy([]), {})
        self.assertFalse((self.destination/'images').exists())

    def test_nonlist_and_duplicate_requests_refused(self):
        for request in (self.name, None, [self.name, self.name]):
            with self.subTest(request=request), self.assertRaises(AssertionError):
                self.copy(request)

    def test_paths_extensions_and_nonstring_members_refused(self):
        for name in ('../'+self.name, '/tmp/'+self.name, 'source.json', None, 12):
            with self.subTest(name=name), self.assertRaises(AssertionError):
                self.copy([name])
        self.assertFalse((self.destination/'images').exists())

    def test_missing_original_member_refused(self):
        with self.assertRaises(KeyError):
            self.copy(['missing.png'])

    def test_tampered_archive_byte_refused(self):
        with self.assertRaises(AssertionError):
            self.copy([self.name], self.raw[:-1]+b'X')
        self.assertFalse((self.destination/'images').exists())

    def test_wrong_receipt_length_refused(self):
        self.receipt['all_zip_members'][self.name]['bytes'] += 1
        with self.assertRaises(AssertionError):
            self.copy([self.name])

    def test_more_than_eight_images_and_over_2MiB_refused(self):
        with self.assertRaises(AssertionError):
            self.copy([str(i)+'.png' for i in range(9)])
        self.receipt['all_zip_members'][self.name]['bytes'] = 2*1024*1024+1
        with self.assertRaises(AssertionError):
            self.copy([self.name])
        self.assertFalse((self.destination/'images').exists())

    def test_matching_digest_does_not_allow_non_PNG_bytes(self):
        raw = b'NOT_PNG_SOURCE_BYTES'
        self.receipt['all_zip_members'][self.name] = {
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        with self.assertRaises(AssertionError):
            self.copy([self.name], raw)
        self.assertFalse((self.destination/'images').exists())


class IncompleteFixedAnalysisCounts(unittest.TestCase):
    def setUp(self):
        self.manifest = {'expected_status': 'INCOMPLETE',
                         'required_case_counts': {'native': 2, 'races': 1, 'http': 1, 'browser': 2},
                         'incomplete_case_counts': {'native': {'PASS': 2}, 'races': {'PASS': 1},
                                                   'http': {'PASS': 1}, 'browser': {'PASS': 1, 'INCOMPLETE': 1}}}
        self.report = {'status': 'INCOMPLETE'}
        for group, counts in self.manifest['incomplete_case_counts'].items():
            cases = {f'{status}-{i}': {'status': status}
                     for status, number in counts.items() for i in range(number)}
            self.report[group] = {'counts': copy.deepcopy(counts),
                                  'races' if group == 'races' else 'cases': cases}

    def test_exact_incomplete_original_admitted_without_modification(self):
        before = copy.deepcopy(self.report)
        verify_declared_case_counts(self.report, self.manifest)
        self.assertEqual(self.report, before)

    def test_failure_cannot_be_relabelled_pass(self):
        self.manifest['expected_status'] = 'PASS'
        with self.assertRaises(AssertionError):
            verify_declared_case_counts(self.report, self.manifest)

    def test_explicit_incomplete_counts_required(self):
        del self.manifest['incomplete_case_counts']
        with self.assertRaises(KeyError):
            verify_declared_case_counts(self.report, self.manifest)

    def test_changed_group_budget_or_missing_failure_refused(self):
        for change in ('budget', 'missing'):
            manifest = copy.deepcopy(self.manifest)
            if change == 'budget':
                manifest['required_case_counts']['browser'] += 1
            else:
                del manifest['incomplete_case_counts']['browser']
            with self.subTest(change=change), self.assertRaises(AssertionError):
                verify_declared_case_counts(self.report, manifest)

    def test_case_counts_cannot_hide_changed_or_missing_executions(self):
        for change in ('status', 'missing', 'extra'):
            report = copy.deepcopy(self.report)
            cases = report['browser']['cases']
            if change == 'status':
                cases['INCOMPLETE-0']['status'] = 'PASS'
            elif change == 'missing':
                del cases['INCOMPLETE-0']
            else:
                cases['extra'] = {'status': 'PASS'}
            with self.subTest(change=change), self.assertRaises(AssertionError):
                verify_declared_case_counts(report, self.manifest)

    def test_legacy_qualified_and_declared_budgets_keep_existing_admission(self):
        manifest = copy.deepcopy(self.manifest)
        manifest['expected_status'] = 'PASS'
        report = copy.deepcopy(self.report)
        for group, number in manifest['required_case_counts'].items():
            report[group]['counts'] = {'PASS': number}
        verify_declared_case_counts(report, manifest)
        report['required_case_counts'] = copy.deepcopy(manifest['required_case_counts'])
        verify_declared_case_counts(report, manifest)
        report['required_case_counts']['native'] += 1
        with self.assertRaises(AssertionError):
            verify_declared_case_counts(report, manifest)


if __name__ == '__main__':
    unittest.main()
