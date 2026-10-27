"""Exercise actual measure() rollback/error handling without connecting a DB.

These controlled tests are not Native or timing evidence. The retained actual
25006 trace establishes the PostgreSQL failure; CI must run the corrected path.
"""
import ast
from contextlib import nullcontext
from hashlib import sha256
import json
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
import unittest
from urllib.parse import urlparse

HERE=Path(__file__).resolve().parent
TREE=ast.parse((HERE/'runner.py').read_text())

class DatabaseError(Exception):
    def __init__(self,code):
        self.sqlstate=code
        self.diag=SimpleNamespace(message_primary='controlled '+code,context='test')

class Connection:
    def __init__(self,error=None,needs_lock=True):
        self.error=error;self.needs_lock=needs_lock;self.readonly=False;self.calls=[];self.rollbacks=0
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def cursor(self):return self
    def execute(self,sql,args=None,**kw):
        self.calls.append((sql,args))
        if sql=='set local transaction read only':self.readonly=True
        if sql=='MEASURE':
            if self.error:raise DatabaseError(self.error)
            if self.readonly and self.needs_lock:raise DatabaseError('25006')
        return self
    def fetchone(self):return ({'server_ms':12,'rows':{},'report':{'snapshot':{'basis':{}}}},)
    def rollback(self):self.rollbacks+=1

def exercise(readonly,error=None,name='OFFICIAL_FINANCE_REPORT_UNIT',limit=30000):
    conn=Connection(error,needs_lock=name=='OFFICIAL_FINANCE_REPORT_UNIT')
    ns=dict(urlparse=urlparse,sha256=sha256,json=json,monotonic=monotonic,
            functions=lambda c:{},difference=lambda a,b:[],
            finance=SimpleNamespace(finance=SimpleNamespace(as_capture=lambda c:nullcontext())),
            psycopg=SimpleNamespace(connect=lambda _:conn,Error=DatabaseError))
    fn=next(n for n in TREE.body if isinstance(n,ast.FunctionDef)and n.name=='measure')
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(HERE/'runner.py'),'exec'),ns)
    result=ns['measure']('postgresql://localhost:54322/cp6_rollback',name,'MEASURE',(),limit_ms=limit,read_only=readonly)
    assert conn.rollbacks==1
    assert ('rollback to savepoint measured_call',None)in conn.calls
    assert ('release savepoint measured_call',None)in conn.calls
    assert ("select set_config('statement_timeout',%s,true)",(str(limit),))in conn.calls
    assert ("set local lock_timeout='2s'",None)in conn.calls
    assert result['all_measured_effects_rolled_back']and result['retries']==0
    return result

class TransactionModes(unittest.TestCase):
    def test_retained_readonly_failure_stays_error(self):
        row=exercise(True)
        self.assertEqual((row['status'],row['sqlstate']),('ERROR_DIAGNOSTIC','25006'))
    def test_official_calculation_rolls_back_in_readwrite(self):
        row=exercise(False)
        self.assertEqual(row['status'],'COMPLETED_DIAGNOSTIC')
        self.assertEqual(row['server_report_ms'],12)
    def test_status_keeps_8s_readonly_policy(self):
        fn=next(n for n in TREE.body if isinstance(n,ast.FunctionDef)and n.name=='exercise')
        calls=next(n.value for n in ast.walk(fn)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='calls'for t in n.targets))
        self.assertEqual([(ast.literal_eval(n.elts[0]),ast.literal_eval(n.elts[-1]))for n in calls.elts],
                         [('FIRST_OPERATIONAL_UNIT',False),('OFFICIAL_FINANCE_REPORT_UNIT',False),('SMALL_STATUS_READ',True)])
        self.assertEqual(ast.literal_eval(calls.elts[-1].elts[-2]),8000)
        row=exercise(True,name='SMALL_STATUS_READ',limit=8000)
        self.assertTrue(row['read_only'])
        self.assertEqual(row['status'],'COMPLETED_DIAGNOSTIC')
    def test_timeout_and_unexpected_error_remain_distinct(self):
        for code,status in [('57014','CANCELED_DIAGNOSTIC'),('22012','ERROR_DIAGNOSTIC')]:
            with self.subTest(code=code):
                row=exercise(False,code)
                self.assertEqual((row['status'],row['sqlstate']),(status,code))

if __name__=='__main__':unittest.main()
