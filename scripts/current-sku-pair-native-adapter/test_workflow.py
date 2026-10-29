"""Cheap checks on the one actual caller and mandatory cleanup boundaries."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]


class WorkflowBoundaries(unittest.TestCase):
    def test_exact_qualification_branch_and_single_native_entrypoint(self):
        value = yaml.safe_load((ROOT / '.github/workflows/cp7-sku-pair-native.yml').read_text())
        branch = 'astra-a/sku-pair-native-successor-20261029'
        self.assertEqual(value['on']['push']['branches'], [branch])
        self.assertEqual(set(value['jobs']), {'p21'})
        job = value['jobs']['p21']
        self.assertEqual(job['if'], "github.ref == 'refs/heads/" + branch + "'")
        calls = [s for s in job['steps'] if 'current-sku-pair-native-adapter/probe.py' in s.get('run', '')]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['working-directory'], 'writer')
        self.assertFalse(any('current-ow08-source-browser/probe.py' in s.get('run', '') for s in job['steps']))

    def test_source_admission_precedes_database_and_all_cleanup_runs_after_failure(self):
        value = yaml.safe_load((ROOT / '.github/workflows/cp7-sku-pair-native.yml').read_text())
        steps = value['jobs']['p21']['steps']
        admission = [i for i, s in enumerate(steps) if 'current-sku-pair-native-adapter/check.py' in s.get('run', '')]
        database = [i for i, s in enumerate(steps) if s.get('name') == 'Start disposable database']
        self.assertEqual(len(admission), 1)
        self.assertEqual(len(database), 1)
        self.assertLess(admission[0], database[0])
        for name in ('Remove disposable database', 'Preserve exact original JSON report bytes in a bounded compressed log receipt'):
            self.assertEqual(next(s for s in steps if s.get('name') == name)['if'], 'always()')
        upload = [s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@')]
        self.assertEqual(len(upload), 1)
        self.assertEqual(upload[0]['if'], 'always()')
        self.assertEqual(value['jobs']['p21']['env']['PGURL'], 'postgresql://postgres:postgres@127.0.0.1:54322/postgres')


if __name__ == '__main__':
    unittest.main()
