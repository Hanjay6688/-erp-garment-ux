"""Only the complete immutable prepared Mandor source may replace old source."""
import copy
import json
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
import unittest
import check_source as fence


class CurrentPreparedParent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = json.loads((fence.HERE / 'SOURCE.json').read_bytes())['pending_current_Mandor_preparation']
        cls.baseline = fence.entries('3fd1bdb763a6d22a5aa455f5aea3a853b9782e4d')

    def test_complete_current_prepared_parent_is_admitted_without_a_Root(self):
        result = fence.pending_mandor(self.value, self.baseline)
        self.assertEqual(len(result), 92)
        self.assertEqual(result, {name: row['after'] for name, row in self.value['files'].items()})
        self.assertIsNone(self.value['actual_Root'])

    def test_omitted_or_extra_parent_path_is_refused(self):
        for change in ('missing', 'extra'):
            value = copy.deepcopy(self.value)
            if change == 'missing':
                value['files'].pop('scripts/cp7_accessory_nonpayable/progress.py')
            else:
                value['files']['scripts/unreviewed.py'] = {}
            with self.assertRaisesRegex(ValueError, 'COMPLETE_CURRENT_MANDOR_PATHS'):
                fence.pending_mandor(value, self.baseline)

    def test_other_parent_identity_or_fabricated_Root_cannot_be_admitted(self):
        for key in ('head', 'tree', 'base_head', 'base_tree', 'actual_Root', 'actual_run', 'actual_job'):
            value = copy.deepcopy(self.value)
            value[key] = 'unqualified-model'
            with self.assertRaisesRegex(ValueError, 'ONLY_EXACT_UNQUALIFIED_CURRENT_MANDOR_SOURCE'):
                fence.pending_mandor(value, self.baseline)

    def test_forged_before_after_or_current_byte_pin_is_refused(self):
        name = 'scripts/cp7_accessory_nonpayable/qualification.py'
        for field in ('before', 'after', 'pin'):
            value = copy.deepcopy(self.value)
            value['files'][name][field]['sha256' if field == 'pin' else 'blob'] = '0' * (64 if field == 'pin' else 40)
            with self.assertRaisesRegex(ValueError, 'EXACT_BEFORE_AND_AFTER|EVERY_SOURCE_BYTE_REQUIRED'):
                fence.pending_mandor(value, self.baseline)

    def test_whole_fence_rejects_a_changed_current_parent_source_byte(self):
        target = fence.ROOT / 'scripts/cp7_accessory_nonpayable/progress.py'
        original = Path.read_bytes

        def changed(path):
            raw = original(path)
            return raw + b'\n' if path == target else raw

        with patch.object(Path, 'read_bytes', changed), self.assertRaisesRegex(
                ValueError, 'CURRENT_MANDOR_EVERY_SOURCE_BYTE_REQUIRED:scripts/cp7_accessory_nonpayable/progress.py'):
            fence.check()


    def test_runtime_runner_outputs_are_data_only(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'scripts/current-workflow-history-isolation/ARCHIVE.json'
            archive.parent.mkdir(parents=True)
            archive.write_text('{"files": []}')
            inherited = root / 'scripts/current-mandor-afui-preparation'
            inherited.mkdir()
            for name in ('check_source.py', 'routes.py'):
                (inherited / name).write_bytes((fence.ROOT / 'scripts/current-mandor-afui-preparation' / name).read_bytes())
            accepted = 'cp6-proof/t3/SKU_CURRENT_PARENT_MONEY_AUTOMATIC_MODEL.json'
            blocked = 'cp6-proof/t3/SKU_CURRENT_PARENT_MONEY_AUTOMATIC_MODEL.py'
            report = root / accepted
            report.parent.mkdir(parents=True)
            report.write_text('{}')
            (root / blocked).write_text('raise AssertionError')
            self.assertEqual(fence.runner_inputs(root, {accepted, blocked}), {accepted})
            report.chmod(0o755)
            with self.assertRaisesRegex(ValueError, 'NONEXECUTABLE_RUNNER_OUTPUT_REQUIRED'):
                fence.runner_inputs(root, {accepted})
            report.unlink()
            report.symlink_to(root / blocked)
            with self.assertRaisesRegex(ValueError, 'NONEXECUTABLE_RUNNER_OUTPUT_REQUIRED'):
                fence.runner_inputs(root, {accepted})


if __name__ == '__main__':
    unittest.main()
