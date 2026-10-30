"""Exact source/read-scope controls; no Native, Auth or browser execution."""
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import ast
import importlib.util
import json
import shutil
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('s03_ordinary_unit_' + name, HERE / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def actual_prepare_excerpt():
    tree = ast.parse((HERE / 'fixture.py').read_text())
    prepare = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'prepare')
    native_setup = next(node for node in prepare.body if isinstance(node, ast.With))
    mobile = native_setup.body[0]
    start = next(i for i, node in enumerate(mobile.body) if isinstance(node, ast.With)
        and ast.unparse(node.items[0].context_expr) == 'snapshot_utc(cur, f)')
    # Two reads surround the original activation and admin call. Execute these
    # exact AST nodes with serialization-only doubles, never a business model.
    nodes = mobile.body[start:start + 4]
    if len(nodes) != 4 or not isinstance(nodes[-1], ast.With):
        raise AssertionError('expected exact two-read/one-activation source excerpt')
    return nodes


class ScopeOnlyFixture:
    def __init__(self, cur, fail):
        self.cur, self.fail, self.events = cur, fail, []
        self.REASON = 'UNIT_SOURCE_SCOPE_ONLY'
        self.before = dict(FG=[{'all_original_fields': True}], HPP_history=[{'all_history': True}],
            HPP_components=[{'all_components': True}], journal_headers=[{'all_headers': True}],
            journal_lines=[{'all_lines': True}], current_HPP=[{'all_hpp': True}], GL={'all_money': True})
        self.journal = {'all_original_columns': True, 'created_at': 'UNIT_RAW_UTC', 'posting_at': 'UNIT_RAW_UTC'}

    def one(self, cur, sql, params=None):
        if sql == "select current_setting('TimeZone')":
            return cur.timezone
        if not sql.startswith('select to_jsonb(j)from erp.journal_entries j join erp.attendance_hpp_pools'):
            raise AssertionError('unexpected query in read-scope-only test')
        self.events.append(('journal_read', cur.timezone)); assert cur.timezone == 'UTC'
        if self.fail == 'journal':
            cur.failed = True; raise ValueError('LOCAL_JOURNAL_READ_FAILURE')
        return self.journal

    def finished(self, cur, fixture, *, core):
        self.events.append(('finished_facts_read', cur.timezone)); assert cur.timezone == 'UTC'
        if self.fail == 'finished':
            cur.failed = True; raise ValueError('LOCAL_FINISHED_READ_FAILURE')
        return self.before

    def native(self, cur, sql, params):
        assert sql == 'select erp.activate_attendance_hpp_pool_v1(%s,%s,%s,%s)'
        self.events.append(('business_call_not_executed', cur.timezone))

    def admin(self, cur):
        self.events.append(('admin', cur.timezone))


class OrdinarySnapshotControls(unittest.TestCase):
    def run_excerpt(self, timezone, failure=None):
        rights_test = load('test_current_rights'); fixture = load('fixture')
        cur = rights_test.ReadCursor(timezone); f = ScopeOnlyFixture(cur, failure)
        scope = dict(cur=cur, f=f, r={'lawful': SimpleNamespace(finished_facts=f.finished)},
            core=object(), g=object(), normal={'pool_id': 'UNIT_POOL', 'row_version': 1},
            uuid=SimpleNamespace(uuid4=lambda: 'UNIT_REQUEST'), snapshot_utc=fixture.snapshot_utc)
        excerpt = ast.Module(body=actual_prepare_excerpt(), type_ignores=[])
        return cur, f, scope, compile(excerpt, 'actual_prepare_read_scope_excerpt', 'exec')

    def test_only_two_reads_get_utc_and_intervening_business_timezone_stays_original(self):
        for timezone in ('Asia/Jakarta', 'UTC', 'America/Los_Angeles'):
            cur, f, scope, code = self.run_excerpt(timezone)
            with self.subTest(timezone=timezone):
                exec(code, scope)
                self.assertEqual(f.events, [('finished_facts_read', 'UTC'),
                    ('business_call_not_executed', timezone), ('admin', timezone), ('journal_read', 'UTC')])
                self.assertEqual(cur.timezone, timezone)
                self.assertIs(scope['ordinary_before_native'], f.before)
                self.assertIs(scope['ordinary_journal'], f.journal)

    def test_each_read_failure_restores_caller_timezone_without_continuing_business(self):
        for failure in ('finished', 'journal'):
            cur, f, scope, code = self.run_excerpt('Asia/Jakarta', failure)
            with self.subTest(failure=failure), self.assertRaisesRegex(ValueError, 'LOCAL_.*_READ_FAILURE'):
                exec(code, scope)
            self.assertEqual(cur.timezone, 'Asia/Jakarta'); self.assertFalse(cur.failed)
            self.assertEqual(cur.events[-2:], [('rollback_savepoint', 'Asia/Jakarta'), ('timezone', 'Asia/Jakarta')])
            self.assertEqual(sum(event[0] == 'business_call_not_executed' for event in f.events), int(failure == 'journal'))

    def test_exact_two_read_delta_recovers_whole_parent_fixture_and_callbacks(self):
        delta = load('ordinary_snapshot_delta'); proof = delta.verify()
        self.assertEqual(proof['fixture_read_scopes'], 2); self.assertTrue(proof['all_four_callbacks_exact'])
        self.assertEqual(delta.parent_fixture(), (HERE / 'retained-ae837/fixture.py').read_bytes())
        scopes = [node for node in actual_prepare_excerpt() if isinstance(node, ast.With)]
        self.assertEqual(len(scopes), 2)
        for scope in scopes:
            self.assertEqual(len(scope.body), 1); self.assertIsInstance(scope.body[0], ast.Assign)
            self.assertNotIn('.native(', ast.unparse(scope)); self.assertNotIn('activate_', ast.unparse(scope))

    def test_next_delta_rejects_an_extra_timezone_write_or_changed_financial_callback(self):
        delta = load('ordinary_snapshot_delta')
        with TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(HERE / 'retained-ae837', target / 'retained-ae837')
            for name in (*delta.FILES, *delta.UNCHANGED, 'ORDINARY_SNAPSHOT_DELTA.json'):
                (target / name).parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(HERE / name, target / name)
            for name, before, after in (('fixture.py', 'with snapshot_utc(cur, f):', 'cur.execute("select set_config(\'TimeZone\',\'UTC\',true)")\n    with snapshot_utc(cur, f):'),
                    ('cases.mjs', '100003n', '100004n')):
                path = target / name; original = path.read_text(); path.write_text(original.replace(before, after, 1))
                with self.subTest(name=name), self.assertRaises(ValueError):
                    delta.verify(ROOT, target)
                path.write_text(original)

    def test_actual_scan_retains_economic_changes_and_every_field_difference(self):
        scan = json.loads((HERE / 'evidence/ORDINARY_SNAPSHOT_ACTUAL4D_SCAN.json').read_bytes())
        groups = scan['groups']
        expected = dict(FG=(2, 4, 1), current_HPP=(1, 1, 1), HPP_history=(2, 2, 1),
            HPP_components=(18, 18, 0), journal_headers=(4, 8, 0), journal_lines=(10, 0, 0),
            ordinary_pool_journal=(1, 2, 0))
        for name, (rows, time_changes, economic_changes) in expected.items():
            actual = groups[name]
            self.assertEqual((actual['compared_rows'], actual['time_representation_differences'],
                len(actual['non_time_differences'])), (rows, time_changes, economic_changes))
            self.assertEqual(actual['compared_fields'], actual['equal_value_fields'] + len(actual['raw_differences']))
        self.assertEqual(groups['FG']['non_time_differences'][0]['column'], 'unit_hpp_snapshot')
        self.assertFalse(scan['legitimate_ordinary_activation']['full_FG_or_HPP_equality_claim'])
        self.assertEqual(scan['actual_new_browser_credit'], 0); self.assertEqual(scan['dropped_columns'], [])
        self.assertEqual(groups['journal_lines']['raw_differences'], [])
        self.assertFalse(groups['journal_lines']['serialized_row_bytes_equal'])
        representations = groups['journal_lines']['equal_numeric_values_with_different_JSON_representation']
        self.assertEqual(len(representations), 20)
        self.assertTrue(all(row['equal_numeric_value'] for row in representations))


if __name__ == '__main__':
    unittest.main(verbosity=2)
