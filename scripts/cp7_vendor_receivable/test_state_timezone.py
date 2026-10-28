"""Test the actual observer's GUC handling; not a Native business qualification.

The real SQL serialization difference is separately reproduced with PGlite;
the Native successor retains all original money/history assertions.
"""
import ast
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo


class Cursor:
    def __init__(self, zone):
        self.zone=zone;self.calls=[];self.timestamp=datetime(2026,10,24,5,tzinfo=timezone.utc)
        self.fail=False

    def execute(self, sql, args=()):
        self.calls.append((sql,args,self.zone))
        if sql=='show timezone':self.row=(self.zone,)
        elif sql.startswith("select set_config('TimeZone'"):
            self.zone=args[0]if args else 'UTC';self.row=(self.zone,)
        elif sql.startswith('select h.status'):
            if self.fail:raise RuntimeError('observer read failed')
            self.row=('PAID','70000.00',[dict(id='payment',payment_date=self.timestamp.astimezone(ZoneInfo(self.zone)).isoformat(),notes='preserved')])
        else:self.row=('3000.00',)
        return self

    def fetchone(self):return self.row


def actual_observer():
    source=Path(__file__).with_name('cases.py').read_text()
    tree=ast.parse(source)
    definitions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ('one','state')]
    scope=dict(bd=SimpleNamespace(api=SimpleNamespace(admin=lambda cur:None),ap=lambda cur,vendor:'0.00'),
               funding=SimpleNamespace(coa=lambda cur,cash:'bank-coa'))
    exec(compile(ast.Module(body=definitions,type_ignores=[]),'cases.py','exec'),scope)
    return scope['state']


class MetadataObserver(unittest.TestCase):
    def setUp(self):
        self.state=actual_observer();self.fixture=dict(invoice='invoice',ar='ar',vendor='vendor',cash='bank')

    def test_identical_complete_history_across_boundary_timezone_change(self):
        cur=Cursor('Asia/Jakarta');before=self.state(cur,self.fixture)
        self.assertEqual(cur.zone,'Asia/Jakarta')
        cur.zone='UTC';after=self.state(cur,self.fixture)
        self.assertEqual(before,after);self.assertEqual(cur.zone,'UTC')
        self.assertEqual(before['origin'][2][0]['payment_date'],'2026-10-24T05:00:00+00:00')
        queries=[sql for sql,args,zone in cur.calls if sql.startswith('select h.status')]
        self.assertTrue(all('jsonb_agg(to_jsonb(p)order by p.id)'in sql for sql in queries))

    def test_real_payment_timestamp_change_still_detected(self):
        cur=Cursor('Asia/Jakarta');before=self.state(cur,self.fixture)
        cur.timestamp=datetime(2026,10,24,6,tzinfo=timezone.utc)
        self.assertNotEqual(before['origin'],self.state(cur,self.fixture)['origin'])

    def test_read_error_remains_visible_and_original_guc_is_restored(self):
        cur=Cursor('Asia/Jakarta');cur.fail=True
        with self.assertRaisesRegex(RuntimeError,'observer read failed'):self.state(cur,self.fixture)
        self.assertEqual(cur.zone,'Asia/Jakarta')


if __name__=='__main__':unittest.main()
