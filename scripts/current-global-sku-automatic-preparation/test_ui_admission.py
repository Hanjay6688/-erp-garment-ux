"""Approved B display bytes do not open a general parent-source exception."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import check_source as fence


class SelectiveUIAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = json.loads((fence.HERE / 'SOURCE.json').read_bytes())['selective_B_UI']
        cls.base = fence.entries('34df5f0a23f3fc5063f8f98260d0e937010fbcaf')
        cls.approved = fence.entries(fence.UI_TREE)

    def test_exact_selected_files_and_unchanged_build_inputs_are_admitted(self):
        self.assertEqual(fence.selective_ui(self.value, self.base, self.approved),
                         {name: self.approved[name] for name in fence.UI_PATHS})

    def test_a_fourth_ui_file_or_missing_build_input_is_refused(self):
        for change in ('extra', 'missing'):
            value = copy.deepcopy(self.value)
            if change == 'extra':
                value['files']['src/unreviewed.tsx'] = {}
            else:
                value['root_build_inputs'].pop('package-lock.json')
            with self.assertRaisesRegex(ValueError, 'ONLY_THREE_SELECTIVE_UI_PATHS_AND_COMPLETE_BUILD_INPUTS'):
                fence.selective_ui(value, self.base, self.approved)

    def test_changed_before_after_and_build_blob_identities_are_refused(self):
        for section in ('before', 'after', 'build'):
            value = copy.deepcopy(self.value)
            if section == 'build':
                value['root_build_inputs']['package.json']['blob'] = '0' * 40
            else:
                value['files']['src/ConnectedPocketFabricPage.tsx'][section]['blob'] = '0' * 40
            with self.assertRaisesRegex(ValueError, 'EXACT_UI_BEFORE_AND_APPROVED_AFTER|UI_BUILD_INPUT_CHANGED'):
                fence.selective_ui(value, self.base, self.approved)

    def test_a_changed_live_ui_byte_cannot_use_the_old_approved_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in fence.UI_PATHS:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((fence.ROOT / name).read_bytes())
            target = root / 'src/ConnectedPocketFabricPage.tsx'
            target.write_bytes(target.read_bytes() + b'\n')
            with patch.object(fence, 'ROOT', root), self.assertRaisesRegex(ValueError, 'APPROVED_UI_EVERY_BYTE_REQUIRED'):
                fence.selective_ui(self.value, self.base, self.approved)

    def test_the_complete_fence_still_refuses_a_changed_fourth_parent_file(self):
        target = fence.ROOT / 'src/App.tsx'
        self.assertTrue(target.is_file())
        original = Path.read_bytes

        def changed(path):
            raw = original(path)
            return raw + b'\n' if path == target else raw

        with patch.object(Path, 'read_bytes', changed), self.assertRaisesRegex(
                ValueError, 'UNDECLARED_PARENT_CHANGE:src/App.tsx'):
            fence.check(observe_sparse=True)


if __name__ == '__main__':
    unittest.main()
