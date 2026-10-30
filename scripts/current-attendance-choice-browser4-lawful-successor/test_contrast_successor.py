"""Explicit source/failure-shape controls; no DB, Auth or browser credit."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import json
import subprocess
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('s03_contrast_' + name, HERE / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


class ContrastSuccessor(unittest.TestCase):
    def test_exact_css_public_successor_and_mutations(self):
        delta = load('ui_delta'); proof = delta.verify(ROOT, HERE)
        self.assertEqual(proof['actual_browser_credit'], 0)
        original = subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'show', delta.PARENT + ':' + delta.PATH])
        plan = json.loads((HERE / 'UI_CONTRAST_DELTA.json').read_bytes())
        with TemporaryDirectory() as temporary:
            target = Path(temporary)
            for key in ('parent', 'public_commit', 'public_tree', 'before', 'after', 'changes'):
                bad = deepcopy(plan)
                if key in ('before', 'after'): bad[key]['sha256'] = '0' * 64
                elif key == 'changes': bad[key][0]['after'] += '/* unexpected rule */'
                else: bad[key] = '0' * 40
                (target / 'UI_CONTRAST_DELTA.json').write_text(json.dumps(bad))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    delta.expected(ROOT, target, delta.PATH, original)

    def test_three_financial_callbacks_exact_and_access_explicit_reversible_successor(self):
        old = subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'show',
            '84a9a09bf372caeeea4cc9eee4a91c51b43d3d93:' + str(HERE.relative_to(ROOT) / 'cases.mjs')]).decode()
        retained = (HERE / 'retained-4d968/cases.mjs').read_text()
        self.assertEqual(retained.replace(' let f=null,serial=0', ' let f,serial=0', 1), old)
        current = (HERE / 'cases.mjs').read_text()
        proof = load('rights_delta').verify()
        self.assertEqual(proof['whole_financial_callbacks'], 3)
        self.assertTrue(proof['all_4d_bytes_restored'])
        self.assertTrue(proof['delayed_period_logout_fresh_actor_exact'])
        self.assertEqual(proof['actual_browser_credit'], 0)
        self.assertIn('fixture:f', current)

    def test_null_fixture_failure_is_preserved_and_missing_field_refused(self):
        output = load('output_admission')
        name = 'cp6-proof/t3/S03_B4_MOBILE390_' + 'a' * 32 + '_FIRST_FAILURE.json'
        with TemporaryDirectory() as temporary:
            root = Path(temporary); path = root / name; path.parent.mkdir(parents=True)
            value = dict(error='EXPLICIT_LOCAL_PREPARE_FAILURE_DOUBLE', progress={}, calls=[], observed=[], fixture=None, pool_history={})
            path.write_text(json.dumps(value))
            self.assertTrue(output.evidence(root, HERE, name))
            value.pop('fixture'); path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'FIRST_FAILURE_SHAPE'):
                output.evidence(root, HERE, name)


if __name__ == '__main__': unittest.main(verbosity=2)
