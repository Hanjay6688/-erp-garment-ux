"""Reject stale, incomplete and substituted physical cumulative inputs."""
from pathlib import Path
from unittest.mock import patch
import copy
import json
import unittest

import check_source as fence
import cumulative_source as current


class CumulativePhysicalSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = fence.entries('3fd1bdb763a6d22a5aa455f5aea3a853b9782e4d')
        cls.map_path = current.HERE / 'CUMULATIVE_SOURCE_MAP.json'
        cls.mapping = json.loads(cls.map_path.read_bytes())

    def evaluate(self, value=None):
        original = Path.read_bytes
        def read(path):
            return json.dumps(value).encode() if value is not None and path == self.map_path else original(path)
        with patch.object(Path, 'read_bytes', read):
            return current.check(fence, self.baseline)

    def test_complete_physical_source_uses_actual_backend_and_browser_fix(self):
        sources, evidence, proof = self.evaluate()
        self.assertEqual(proof['backend_adoption_paths'], 33)
        self.assertEqual(proof['current_backend_paths'], 111)
        self.assertEqual(len(sources), 112)
        self.assertEqual(len(evidence), 9)
        self.assertFalse(proof['runtime_admission'])
        self.assertEqual(proof['original_failed_run']['conclusion'], 'failure')
        self.assertEqual(proof['successful_paired_browser_run']['conclusion'], 'success')

    def test_missing_or_extra_adopted_path_is_refused(self):
        for mode in ('missing', 'extra'):
            value = copy.deepcopy(self.mapping)
            if mode == 'missing':
                value['backend_adoption_paths'].pop()
            else:
                value['backend_adoption_paths'].append('scripts/unreviewed.py')
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'COMPLETE_33_PATH'):
                self.evaluate(value)

    def test_incomplete_backend_or_browser_source_map_is_refused(self):
        for field in ('backend_files', 'browser_product_files'):
            value = copy.deepcopy(self.mapping)
            value[field].pop(next(iter(value[field])))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'COMPLETE_33_PATH|PRODUCT_DELTA'):
                self.evaluate(value)

    def test_old_backend_or_swapped_browser_identity_is_refused(self):
        for field in ('backend', 'browser'):
            value = copy.deepcopy(self.mapping)
            value[field] = dict(head=fence.MANDOR_HEAD, tree=fence.MANDOR_TREE)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'EXACT_SOURCE_IDENTITIES'):
                self.evaluate(value)

    def test_changed_shared_build_input_is_refused(self):
        value = copy.deepcopy(self.mapping)
        value['browser_build_inputs']['package-lock.json']['blob'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'BROWSER_BUILD_INPUT_CHANGED'):
            self.evaluate(value)

    def test_changed_backend_css_or_published_evidence_byte_is_refused(self):
        for name in ('scripts/current-mandor-shop-native-qualification/assembly.py', current.PRODUCT_CSS,
                     current.EVIDENCE_PREFIX + 'README.md'):
            original = Path.read_bytes
            def read(path):
                raw = original(path)
                return raw + b'\n' if path == fence.ROOT / name else raw
            with self.subTest(name=name), patch.object(Path, 'read_bytes', read), \
                    self.assertRaisesRegex(ValueError, 'EVERY_PHYSICAL_SOURCE_BYTE'):
                current.check(fence, self.baseline)

    def test_omitted_published_evidence_is_refused(self):
        value = copy.deepcopy(self.mapping)
        value['evidence_files'].pop(next(iter(value['evidence_files'])))
        with self.assertRaisesRegex(ValueError, 'EXACT_PUBLISHED_EVIDENCE_SET'):
            self.evaluate(value)

    def test_source_route_rejects_runtime_before_any_source_read(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('source read')):
            with self.assertRaisesRegex(ValueError, 'SOURCE_CANNOT_OPEN_RUNTIME'):
                fence.check(runtime=True, cumulative=True)
            for name in fence.assembly.admission.GATES:
                with self.subTest(name=name), patch.object(fence.assembly.admission, name, 'open'):
                    with self.assertRaisesRegex(ValueError, 'ALL_FINANCIAL_GATES_MUST_BE_CLOSED'):
                        current.check(fence, self.baseline)

    def test_full_fence_rejects_an_absent_unchanged_parent_file(self):
        missing = fence.ROOT / 'src/App.tsx'
        original = Path.is_file
        with patch.object(Path, 'is_file', lambda path: False if path == missing else original(path)):
            with self.assertRaisesRegex(ValueError, 'FULL_PARENT_MATERIALIZATION'):
                fence.check(cumulative=True)


if __name__ == '__main__':
    unittest.main()
