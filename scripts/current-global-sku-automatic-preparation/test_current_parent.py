"""Only the complete immutable prepared SKU source may replace old source."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import unittest
import check_source as fence


class CurrentPreparedParent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = json.loads((fence.HERE / 'SOURCE.json').read_bytes())['pending_current_SKU_preparation']
        cls.baseline = fence.entries('34df5f0a23f3fc5063f8f98260d0e937010fbcaf')

    def test_complete_current_prepared_parent_is_admitted_without_a_Root(self):
        result = fence.pending_sku(self.value, self.baseline)
        self.assertEqual(len(result), 148)
        self.assertEqual(result, {name: row['after'] for name, row in self.value['files'].items()})
        self.assertIsNone(self.value['actual_Root'])

    def test_omitted_or_extra_parent_path_is_refused(self):
        for change in ('missing', 'extra'):
            value = copy.deepcopy(self.value)
            if change == 'missing':
                value['files'].pop('scripts/cp7_accessory_nonpayable/progress.py')
            else:
                value['files']['scripts/unreviewed.py'] = {}
            with self.assertRaisesRegex(ValueError, 'COMPLETE_ONE_HUNDRED_FORTY_EIGHT_CURRENT_SKU_PATHS'):
                fence.pending_sku(value, self.baseline)

    def test_other_parent_identity_or_fabricated_Root_cannot_be_admitted(self):
        for key in ('head', 'tree', 'base_head', 'base_tree', 'actual_Root', 'actual_run', 'actual_job'):
            value = copy.deepcopy(self.value)
            value[key] = 'unqualified-model'
            with self.assertRaisesRegex(ValueError, 'ONLY_EXACT_UNQUALIFIED_CURRENT_SKU_SOURCE'):
                fence.pending_sku(value, self.baseline)

    def test_forged_before_after_or_current_byte_pin_is_refused(self):
        name = 'scripts/cp7_accessory_nonpayable/qualification.py'
        for field in ('before', 'after', 'pin'):
            value = copy.deepcopy(self.value)
            value['files'][name][field]['sha256' if field == 'pin' else 'blob'] = '0' * (64 if field == 'pin' else 40)
            with self.assertRaisesRegex(ValueError, 'EXACT_BEFORE_AND_AFTER|EVERY_SOURCE_BYTE_REQUIRED'):
                fence.pending_sku(value, self.baseline)

    def test_whole_fence_rejects_a_changed_current_parent_source_byte(self):
        target = fence.ROOT / 'scripts/cp7_accessory_nonpayable/progress.py'
        original = Path.read_bytes

        def changed(path):
            raw = original(path)
            return raw + b'\n' if path == target else raw

        with patch.object(Path, 'read_bytes', changed), self.assertRaisesRegex(
                ValueError, 'CURRENT_SKU_EVERY_SOURCE_BYTE_REQUIRED:scripts/cp7_accessory_nonpayable/progress.py'):
            fence.check(observe_sparse=True)


if __name__ == '__main__':
    unittest.main()
