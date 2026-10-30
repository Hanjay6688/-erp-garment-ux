"""Offline transaction boundary controls, not actual Native or browser credit."""
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch
import importlib.util
import io
import json
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


class Cursor:
    def __init__(self): self.calls = []; self.isolation = None; self.answer = None
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql):
        if sql.startswith('set transaction isolation level '):
            if self.calls: raise AssertionError('ISOLATION_SET_AFTER_FIRST_QUERY')
            self.isolation = sql.rsplit(' level ', 1)[1]
        else:
            if self.isolation is None: raise AssertionError('FIRST_QUERY_BEFORE_ISOLATION')
            self.answer = True if 'has_schema_privilege' in sql else '{authenticated=U/postgres}'
        self.calls.append(sql); return self
    def fetchone(self): return (self.answer,)


class Connection:
    def __init__(self): self.cur = Cursor(); self.end = None
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def cursor(self): return self.cur
    def commit(self): self.end = 'commit'
    def rollback(self): self.end = 'rollback'


class IsolationControls(unittest.TestCase):
    def invoke(self, module, operation):
        conn = Connection(); events = []
        def admin(cur):
            if not cur.calls: raise AssertionError('ADMIN_BEFORE_ISOLATION')
            events.append(('admin', cur.isolation))
        def setup(cur, today):
            events.append(('opening', cur.isolation))
            # Counter reproduces the captured Native contract; no DB is run.
            if cur.isolation != 'read committed': raise ValueError('AR_OPENING_REQUIRES_READ_COMMITTED')
        def state(cur, native, catalog):
            self.assertEqual(cur.isolation, 'repeatable read')
            events.append(('state', cur.isolation)); return {'offline': True}
        def limited(cur, *args):
            if cur.isolation != 'read committed': raise ValueError('CP7_FRESH_ACCESS_REQUIRED')
            events.append(('read', cur.isolation))
            return dict(actor_scope_id='00000000-0000-0000-0000-000000000001',run_id='00000000-0000-0000-0000-000000000002',request_id='request',identity_hash='identity',totals={})
        native = SimpleNamespace(setup=setup, staged=SimpleNamespace(b=SimpleNamespace(api=SimpleNamespace(admin=admin)),
            query=lambda today: dict(day=today.isoformat()), limited=limited,
            fetch=lambda *args: (dict(financial_source=None),dict(run_id='00000000-0000-0000-0000-000000000002',request_id='request',identity_hash='identity',totals={}),{})))
        driver = ModuleType('psycopg'); driver.connect = lambda *args: conn
        payload = dict(today='2026-10-30',actor='00000000-0000-0000-0000-000000000001',run='00000000-0000-0000-0000-000000000002',targets=[])
        with patch.dict(sys.modules, psycopg=driver), patch.object(module, 'load_helpers', return_value=(native,object(),{})), \
             patch.object(module, 'state', side_effect=state), patch.object(sys, 'argv', ['fixture.py', operation]), \
             patch.object(sys, 'stdin', io.StringIO(json.dumps(payload))), \
             patch.dict('os.environ', AUDITOR_BROWSER_DB_URL='postgresql://localhost/cp6_auditor_browser'), redirect_stdout(io.StringIO()):
            module.main()
        return conn, events

    def test_original_prepare_refuses_but_successor_enters_supported_native_boundary(self):
        old = load('sku27_original_staged_fixture', ROOT/'scripts/current-staged-ai-browser-qualification/fixture.py')
        new = load('sku27_successor_staged_fixture', HERE/'staged_ai_fixture.py')
        with self.assertRaisesRegex(ValueError, 'AR_OPENING_REQUIRES_READ_COMMITTED'): self.invoke(old,'prepare')
        conn, events = self.invoke(new,'prepare')
        self.assertIn(('opening','read committed'), events); self.assertEqual(conn.end,'commit')
        self.assertEqual(conn.cur.calls[0], 'set transaction isolation level read committed')

    def test_state_keeps_complete_repeatable_read_transaction(self):
        new = load('sku27_successor_staged_fixture_reads', HERE/'staged_ai_fixture.py')
        conn, events = self.invoke(new,'state')
        self.assertIn(('state','repeatable read'),events); self.assertEqual(conn.end,'rollback')
        self.assertNotIn(('opening','read committed'),events)

    def test_retained_0938_read_refuses_fresh_access_but_successor_checks_current_access(self):
        old = ModuleType('retained_0938_staged_fixture'); old.__file__ = str(HERE/'staged_ai_fixture.py')
        exec(compile((HERE/'retained_0938/staged_ai_fixture.py.txt').read_text(),old.__file__,'exec'),old.__dict__)
        with self.assertRaisesRegex(ValueError,'CP7_FRESH_ACCESS_REQUIRED'):self.invoke(old,'read')
        new = load('sku27_successor_current_access_read', HERE/'staged_ai_fixture.py')
        conn, events = self.invoke(new,'read')
        self.assertEqual(conn.cur.calls[0],'set transaction isolation level read committed')
        self.assertIn(('read','read committed'),events); self.assertEqual(conn.end,'rollback')
        self.assertNotIn(('opening','read committed'),events)

    def test_unknown_operations_cannot_create_native_fixture(self):
        new = load('sku27_successor_staged_fixture_unknown', HERE/'staged_ai_fixture.py')
        with self.assertRaisesRegex(ValueError,'UNKNOWN_STAGED_AI_BROWSER_CONTROL'): self.invoke(new,'unknown')


if __name__ == '__main__': unittest.main()
