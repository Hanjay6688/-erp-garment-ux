from copy import deepcopy
from pathlib import Path
import unittest
import yaml
import derive_workflow as w


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.raw = (Path(__file__).parent / 'original-workflow.yml.txt').read_bytes()

    def test_all_old_steps_and_settings_remain_identical(self):
        original = yaml.safe_load(self.raw)
        text, report = w.derive(self.raw)
        value = yaml.safe_load(text)
        steps = value['jobs']['p21']['steps']
        pos = next(i for i,s in enumerate(steps) if s.get('name') == w.BOUNDARY_NAME)
        self.assertEqual(steps[pos-1]['name'], 'Persist diagnostic checkpoint before long runtime')
        self.assertEqual(steps[pos-2]['name'], 'Write diagnostic source checkpoint before Native25')
        # Both saves finish BEFORE DB start, not merely before the final native command.
        del steps[pos-2:pos]
        self.assertEqual(value, original)
        self.assertFalse(report['activation_permitted'])

    def test_diagnostic_cannot_replace_canonical_archive(self):
        text, _ = w.derive(self.raw)
        value = yaml.safe_load(text)
        uploads = [s['with'] for s in value['jobs']['p21']['steps'] if 'upload-artifact@' in s.get('uses', '')]
        self.assertEqual(len(uploads), 2)
        self.assertNotEqual(uploads[0]['name'], uploads[1]['name'])
        self.assertEqual(uploads[1]['path'], 'auditor/cp6-proof/t3')
        self.assertEqual(uploads[1]['name'], 'cp7-sku-current-parent-money-automatic-native25-${{ github.run_attempt }}')
        self.assertTrue(uploads[0]['path'].endswith('CP7_DIAGNOSTIC_CHECKPOINT.json'))

    def test_stale_workflow_or_relaxed_recovery_refused(self):
        for mutation in (self.raw+b'\n', self.raw.replace(b'if: always()',b'if: success()',1)):
            with self.assertRaisesRegex(ValueError, 'EXACT_6AEB'):
                w.derive(mutation)


if __name__ == '__main__':
    unittest.main(verbosity=2)
