"""Oracle negative guards only; no Native/database coverage claimed here."""
import ast
from pathlib import Path
import unittest

tree=ast.parse(Path(__file__).with_name('cases.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='worker_lock')
namespace={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'cases.py','exec'),namespace)
worker_lock=namespace['worker_lock']

class Cursor:
    def __init__(self,own,foreign):self.value=(own,foreign)
    def execute(self,sql,args):
        assert args==('capture-under-test',)
        assert 'pg_backend_pid()'in sql and 'classid::bigint<<32' in sql
        return self
    def fetchone(self):return self.value

class LockOracle(unittest.TestCase):
    def test_no_worker_requires_no_lock(self):
        self.assertEqual(worker_lock(Cursor(0,0),'capture-under-test',False),'NO_LOCK_OBSERVED')
    def test_executed_step_requires_exact_own_lock(self):
        self.assertEqual(worker_lock(Cursor(1,0),'capture-under-test',True),'LOCK_HELD')
    def test_unexpected_own_lock_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,'NATIVE_TRANSACTION_LOCK_MISMATCH'):
            worker_lock(Cursor(1,0),'capture-under-test',False)
    def test_missing_lock_after_step_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,'NATIVE_TRANSACTION_LOCK_MISMATCH'):
            worker_lock(Cursor(0,0),'capture-under-test',True)
    def test_foreign_worker_is_rejected(self):
        for own in (0,1):
            with self.subTest(own=own),self.assertRaisesRegex(AssertionError,'UNEXPECTED_CONCURRENT_WORKER'):
                worker_lock(Cursor(own,1),'capture-under-test',bool(own))

if __name__=='__main__':unittest.main()
