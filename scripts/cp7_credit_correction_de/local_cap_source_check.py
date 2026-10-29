"""Source/fixture controls only: no connection, Native money or Auth proof."""
import ast
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
for relative in ('scripts', 'scripts/cp7_customer_credit/consumer',
                 'scripts/cp7_customer_credit/reconciliation/native',
                 'scripts/cp7_customer_credit/native', 'scripts/cp7_customer_credit/initial-settlement'):
    sys.path.insert(0, str(ROOT/relative))
with patch('psycopg.connect', side_effect=AssertionError('LOCAL_SOURCE_CHECK_FORBIDS_DB')):
    from cp7_credit_correction_de import native_fixture as fixture, cases

PARENT = 'a99463ca3ea2f1a71b22f0354df83f1b5a42b71b'


def old(path):
    return subprocess.check_output(['git', 'show', PARENT + ':' + path], cwd=ROOT)


def function(text, name):
    start = text.index('create function ' + name + '(')
    end = text.index('$$;', text.index('$$', start) + 2) + 3
    return text[start:end]


class Controls(unittest.TestCase):
    def test_exact_five_functions_ten_reversible_substitutions_all_assertions(self):
        rows = fixture.derived_sources()
        self.assertEqual(len(rows), 5)
        self.assertEqual(sum(r['substitutions'] for r in rows.values()), 10)
        self.assertEqual(sum(r['original_assertions'] for r in rows.values()), 70)
        self.assertEqual(sum(r['derived_assertions'] for r in rows.values()), 73)
        self.assertEqual(rows['consumer.prepare']['before'], rows['consumer.prepare']['after'])

    def test_globals_route_privately_without_patching_any_import(self):
        modules = (fixture.native, fixture.retained.signed.initial, fixture.retained.signed, fixture.retained)
        before = [dict(vars(module)) for module in modules]
        rows = fixture.derived_sources()
        n = fixture._private_module(modules[0], 'native', rows)
        i = fixture._private_module(modules[1], 'initial', rows, native=n)
        s = fixture._private_module(modules[2], 'signed', rows, native=n, initial=i)
        c = fixture._private_module(modules[3], 'consumer', rows, native=n, signed=s)
        self.assertIs(c.prepare.__globals__['signed'], s)
        self.assertIs(s._setup.__globals__['initial'], i)
        self.assertIs(i._assert_actual.__globals__['native'], n)
        self.assertIs(i._assert_quote.__globals__['native'], n)
        self.assertIsNot(n.assert_first_settlement_gl, modules[0].assert_first_settlement_gl)
        for module, expected in zip(modules, before):
            self.assertEqual(set(vars(module)), set(expected))
            self.assertTrue(all(vars(module)[key] is value for key, value in expected.items()))

    def test_cached_import_of_different_source_bytes_refuses(self):
        forged = SimpleNamespace(__file__=__file__)
        with self.assertRaisesRegex(ValueError, 'D1_FIXTURE_IMPORTED_GLOBALS_SOURCE_CHANGED:native'):
            fixture._private_module(forged, 'native', fixture.derived_sources())

    def test_source_or_anchor_drift_cannot_silently_change_the_fixture(self):
        sources = dict(fixture.SOURCES)
        sources['native'] = (sources['native'][0], '0' * 64)
        with patch.object(fixture, 'SOURCES', sources):
            with self.assertRaisesRegex(ValueError, 'D1_FIXTURE_RETAINED_SOURCE_CHANGED'):
                fixture.derived_sources()
        changes = dict(fixture.TRANSFORMS)
        changes[('initial', '_assert_quote')] = (('absent exact source anchor', 'replacement'),)
        with patch.object(fixture, 'TRANSFORMS', changes):
            with self.assertRaisesRegex(ValueError, 'D1_FIXTURE_EXACT_ANCHOR_CHANGED'):
                fixture.derived_sources()

    def test_all_four_frozen_fixture_files_and_eight_other_business_leaves_exact(self):
        for path, digest in fixture.SOURCES.values():
            self.assertEqual((ROOT/path).read_bytes(), old(path))
            self.assertEqual(hashlib.sha256(old(path)).hexdigest(), digest)
        for name in ('review.sql', 'facts.sql', 'proof.sql', 'posting.sql', 'materialize.sql',
                     'closure.sql', 'native_delta.py', 'composition.py'):
            path = 'scripts/cp7_credit_correction_de/' + name
            self.assertEqual((ROOT/path).read_bytes(), old(path), name)

    def test_only_quote_changes_inside_owning_sql(self):
        path = 'scripts/cp7_credit_correction_de/owning.sql'
        before = old(path).decode()
        after = (ROOT/path).read_text()
        name = 'cp7_credit_correction_de.quote_v1'
        self.assertEqual(before.replace(function(before, name), ''), after.replace(function(after, name), ''))
        self.assertIn('max_refund numeric(24,6)', function(after, name))
        self.assertIn('max_refund+0.01', function(after, name))
        self.assertIn("'refund_cap_basis',cap_inputs", function(after, name))

    def test_exact_thirteen_ids_register_without_any_database_operation(self):
        class NoSQL:
            def __getattr__(self, name):
                raise AssertionError('NO_SQL_DURING_REGISTRATION:' + name)
        callbacks = cases.cases(NoSQL(), None)
        before = ast.parse(old('scripts/cp7_credit_correction_de/cases.py').decode())
        ids = next(ast.literal_eval(n.value) for n in before.body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
        self.assertEqual(cases.IDS, ids)
        self.assertEqual(tuple(name for name, _ in callbacks), ids)
        self.assertEqual(len(callbacks), 13)

    def test_legacy_quote_keeps_all_old_payloads_money_and_refusal_assertions_exact(self):
        path = 'scripts/cp7_credit_correction_de/local_quote_check.mjs'
        before = old(path).decode()
        after = (ROOT/path).read_text()
        anchor = ' const p={sale_id:sale,return_id:ret,'
        self.assertEqual(before[before.index(anchor):], after[after.index(anchor):])
        self.assertEqual([line for line in before.splitlines() if re.search(r'\bassert(?:\.|\()', line)],
                         [line for line in after.splitlines() if re.search(r'\bassert(?:\.|\()', line)])

    def test_failure_hook_is_only_private_after_actual_journal_and_has_bound_proof(self):
        text = (ROOT/'scripts/cp7_credit_correction_de/cases.py').read_text()
        tree = ast.parse(text)
        sql = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
               and 'create function cp7_credit_correction_de.test_part_failure()' in n.value]
        self.assertEqual(len(sql), 1)
        self.assertIn('after insert on cp7_credit_correction_de.parts_v1', sql[0])
        self.assertNotIn('on erp.journal_entries', sql[0])
        self.assertIn('perform cp7_credit.assert_source_native_trigger_census_v1()', sql[0])
        self.assertIn('perform cp7_credit_correction_de.assert_plan_set_v1(w.operation_id)', sql[0])
        self.assertIn("'actual_Native_credit_journal_inserted',true", sql[0])
        self.assertIn("'old_recognition_immutable',true", sql[0])
        self.assertIn('failure_AFTER_actual_Native_journal_insert_before_private_completion=True', text)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(status='PASS' if result.wasSuccessful() else 'FAIL', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), Native_execution=False,
        actual_Native_case_credit=0, fixture=fixture.inventory()), indent=2))
    sys.exit(not result.wasSuccessful())
