"""Offline source/serialization controls only; no simulated policy acceptance."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import ast
import importlib.util
import json
import shutil
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('s03_rights_unit_' + name, HERE / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


class ReadFailure(Exception):
    pass


class ReadCursor:
    """Serialization boundary double; never supplies access or business outcomes."""
    def __init__(self, timezone, fail=None):
        self.timezone, self.fail, self.failed = timezone, fail, False
        self.events, self.reads = [], 0
        self.connection = self

    @contextmanager
    def transaction(self):
        old = self.timezone; self.events.append(('savepoint', old))
        try:
            yield
        except BaseException:
            self.failed = False; self.timezone = old
            self.events.append(('rollback_savepoint', old)); raise
        else:
            self.events.append(('release_savepoint', self.timezone))

    def execute(self, sql, params=None):
        if self.failed:
            raise AssertionError('restore attempted before failed read savepoint rollback')
        if sql == "select set_config('TimeZone','UTC',true)":
            self.timezone = 'UTC'
        elif sql == "select set_config('TimeZone',%s,true)":
            self.timezone = params[0]
        else:
            raise AssertionError('unexpected query in serialization-only double: ' + sql)
        self.events.append(('timezone', self.timezone))


class ReadFixture:
    def __init__(self):
        self.rows = [[{'every_original_column': ['UNCHANGED', 7], 'created_at': 'RAW_UTC'}],
            [{'debit': '1000.03', 'arbitrary_other_column': None}],
            [{'changed_at': 'RAW_UTC', 'old_data': {'nested_field': 'UNCHANGED'}}]]

    @staticmethod
    def admin(cur):
        cur.events.append(('admin', cur.timezone))

    def one(self, cur, sql, params=None):
        if sql == "select current_setting('TimeZone')":
            return cur.timezone
        if 'jsonb_agg(to_jsonb(' not in sql or params != ('LOCAL_READ_ONLY_ID',):
            raise AssertionError('unexpected raw-row query')
        if cur.timezone != 'UTC':
            raise AssertionError('raw serialization was not scoped UTC')
        cur.reads += 1; cur.events.append(('raw_read', cur.reads, cur.timezone))
        if cur.fail == cur.reads:
            cur.failed = True; raise ReadFailure('LOCAL_READ_FAILURE_' + str(cur.reads))
        return self.rows[cur.reads - 1]


class CurrentRightsControls(unittest.TestCase):
    def test_original_and_reread_use_same_utc_without_changing_any_row(self):
        fixture = load('fixture'); outcomes = []
        for timezone in ('Asia/Jakarta', 'UTC', 'America/Los_Angeles'):
            cur, f = ReadCursor(timezone), ReadFixture()
            result = fixture.source_rows(cur, 'LOCAL_READ_ONLY_ID', f)
            self.assertEqual(cur.timezone, timezone)
            self.assertEqual(cur.reads, 3)
            self.assertIs(result['headers'], f.rows[0]); self.assertIs(result['lines'], f.rows[1])
            self.assertIs(result['approval_audit'], f.rows[2])
            self.assertEqual(cur.events[-1], ('timezone', timezone)); outcomes.append(result)
        self.assertEqual(outcomes[0], outcomes[1]); self.assertEqual(outcomes[1], outcomes[2])

    def test_query_failure_rolls_back_savepoint_then_restores_original_timezone(self):
        fixture = load('fixture')
        for failure in (1, 2, 3):
            cur = ReadCursor('Asia/Jakarta', failure)
            with self.subTest(query=failure), self.assertRaisesRegex(ReadFailure, 'LOCAL_READ_FAILURE_' + str(failure)):
                fixture.source_rows(cur, 'LOCAL_READ_ONLY_ID', ReadFixture())
            self.assertEqual(cur.timezone, 'Asia/Jakarta'); self.assertFalse(cur.failed)
            self.assertEqual(cur.events[-2:], [('rollback_savepoint', 'Asia/Jakarta'), ('timezone', 'Asia/Jakarta')])

    def test_all_three_original_raw_sql_queries_and_full_equality_oracles_are_exact(self):
        def queries(path):
            tree = ast.parse(path.read_text()); method = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'source_rows')
            return [node.value for node in ast.walk(method) if isinstance(node, ast.Constant)
                and isinstance(node.value, str) and 'jsonb_agg(to_jsonb(' in node.value]
        before = queries(HERE / 'retained-4d968/fixture.py'); after = queries(HERE / 'fixture.py')
        self.assertEqual(len(before), 3); self.assertEqual(before, after)
        source = (HERE / 'fixture.py').read_text()
        self.assertIn("source_rows(cur, fixture['payroll'], f) != fixture['original_accrual']", source)
        self.assertIn("source_rows(cur, fixture[prefix + '_payroll'], f) != fixture[prefix + '_original_accrual']", source)

    def test_actual_policy_bytes_are_bound_and_any_policy_mutation_is_refused(self):
        delta = load('rights_delta'); actual = delta.policy()
        self.assertEqual(set(actual), delta.SIGNATURES)
        self.assertIn("when r.is_protected and r.role_code='OWNER' then true", actual['erp.has_permission(text)'])
        self.assertIn("a->'profile'->>'role_code'is distinct from'OWNER'", actual['cp7_attendance_choice.access_v1(boolean)'])
        with TemporaryDirectory() as temporary:
            target = Path(temporary); (target / 'retained-4d968').mkdir()
            for signature in sorted(actual):
                value = json.loads((HERE / 'retained-4d968/POLICY_FUNCTIONS.json').read_bytes())
                value['functions'][signature][0] += '\n-- LOCAL_MUTATION'
                (target / 'retained-4d968/POLICY_FUNCTIONS.json').write_text(json.dumps(value))
                with self.subTest(signature=signature), self.assertRaisesRegex(ValueError, 'ACTUAL_POLICY_SOURCE_CHANGED'):
                    delta.policy(target)

    def test_counted_delta_refuses_changed_bytes_counts_hashes_and_anchors(self):
        delta = load('rights_delta'); proof = delta.verify()
        self.assertEqual(proof['whole_financial_callbacks'], 3)
        self.assertEqual(proof['actual_browser_credit'], 0)
        with TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(HERE / 'retained-4d968', target / 'retained-4d968')
            shutil.copytree(HERE / 'retained-ae837', target / 'retained-ae837')
            shutil.copytree(HERE / 'retained-30ee', target / 'retained-30ee')
            for name in ('history_delta.py', 'CANCELLED_HISTORY_DELTA.json'):
                shutil.copyfile(HERE / name, target / name)
            ordinary = load('ordinary_snapshot_delta')
            for name in (*ordinary.FILES, *ordinary.UNCHANGED, 'ORDINARY_SNAPSHOT_DELTA.json'):
                (target / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(HERE / name, target / name)
            original = json.loads((HERE / 'CURRENT_RIGHTS_DELTA.json').read_bytes())
            for mutation in ('count', 'hash', 'anchor', 'before_bytes', 'policy'):
                plan = deepcopy(original)
                if mutation == 'count': plan['counted_changes'] += 1
                elif mutation == 'hash': plan['files'][0]['after']['sha256'] = '0' * 64
                elif mutation == 'anchor': plan['files'][0]['changes'][0]['count'] = 2
                elif mutation == 'before_bytes': plan['files'][0]['before']['bytes'] += 1
                else: plan['policy_sha256'] = '0' * 64
                (target / 'CURRENT_RIGHTS_DELTA.json').write_text(json.dumps(plan))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    delta.verify(ROOT, target)

    def test_financial_and_delayed_controls_are_not_covered_by_a_new_blanket_hash(self):
        delta = load('rights_delta'); old = (HERE / 'retained-4d968/cases.mjs').read_text()
        current = (HERE / 'cases.mjs').read_text()
        for before, after in (("100003n", "100004n"),
                ("await y.expect(y.choice()).toHaveCount(0)", "await y.expect(y.choice()).toHaveCount(1)")):
            self.assertIn(before, current)
            with self.subTest(mutation=before), self.assertRaises(ValueError):
                delta.callbacks(old, current.replace(before, after, 1))

    def test_authorized_public_transition_precedes_actual_save_boundary(self):
        source = (HERE / 'cases.mjs').read_text()
        self.assertNotIn("fixture('manage_off'", source); self.assertNotIn("fixture('manage_on'", source)
        self.assertIn("backupOwner.rpc('erp_save_app_user_v3',args)", source)
        self.assertIn('p_expected_version:before.subject.row_version', source)
        self.assertIn("await currentRole(x,backupOwner,'ADMIN');deniedBoundary=x.state('BEFORE_CURRENT_RIGHTS_SAVE');const actual=await route.fetch()", source)
        self.assertIn("equalCensus(deniedBoundary.census,x.state('AFTER_CURRENT_RIGHTS_DENIAL').census)", source)
        self.assertIn('Owner_viewonly:{representable:false,actual_credit:0', source)

    def test_transition_oracle_refuses_third_role_or_changed_protected_authority(self):
        fixture = load('fixture')
        # Rejection-only oracle inputs. They are not SQL/Auth fixtures or policy outcomes.
        before = dict(subject={'role': 'UNDECLARED_UNIT_ROLE'}, backup_owner={'id': 'UNIT_BACKUP'},
            roles=[{'role_code': 'ADMIN', 'is_active': True}], permissions=[], assignments=[],
            policy_signatures=['UNIT_SOURCE_ONLY'])
        after = deepcopy(before)
        with self.assertRaisesRegex(ValueError, 'EXACT_OWNER_ADMIN_TRANSITION_REQUIRED'):
            fixture.assert_access_transition(before, after, {'role': 'ADMIN'})
        for key in ('backup_owner', 'roles', 'permissions', 'assignments', 'policy_signatures'):
            changed = deepcopy(after); changed[key] = ['UNIT_UNAUTHORIZED_CHANGE']
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'PROTECTED_AUTHORITY_CHANGED'):
                fixture.assert_access_transition(before, changed, {'role': 'ADMIN'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
