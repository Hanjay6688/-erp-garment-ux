"""Offline pager refusals using declared RPC stand-ins; zero Native credit."""
import ast
import copy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


source = ast.parse(Path(__file__).with_name('cp7_note_correction_cases.py').read_text())
function = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == 'complete_actual_http_history')
year_function = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == 'year_committed_actual_http')
namespace = {'D': Decimal, 'time': time}
exec(compile(ast.Module(body=[function,year_function], type_ignores=[]), '<actual-http-helper-only>', 'exec'), namespace)
read_all = namespace['complete_actual_http_history']


class ActualHTTPHistoryPagerControls(unittest.TestCase):
    def setUp(self):
        self.fixture = dict(sku='DECLARED-STANDIN-SKU', product='product', lot='lot', location='location')
        self.observations = []

    def owner(self, pages):
        calls = []
        class Owner:
            def rpc(self, name, args):
                calls.append((name, args))
                return copy.deepcopy(pages[len(calls)-1])
        return Owner(), calls

    def page(self, offset, ids, total, next_offset=None):
        return {'status': 200, 'body': {'page': {'offset': offset, 'limit': 100, 'total': total,
                'next_offset': next_offset, 'rows': [{'id': ident} for ident in ids]}}}

    def test_complete366_book_pages_keep_exact_query_and_offsets(self):
        pages = [self.page(offset, list(map(str, range(offset, min(offset+100, 366)))), 366,
                           offset+100 if offset+100<366 else None) for offset in [0, 100, 200, 300]]
        owner, calls = self.owner(pages)
        result = read_all(owner, self.fixture, 'BOOK', 'AFTER_COMMIT', self.observations)
        self.assertEqual(len(result), 366)
        self.assertEqual([args['p_query']['offset'] for _,args in calls], [0,100,200,300])
        self.assertTrue(all(name=='erp_cp7_get_fg_book_v2' and args['p_query']['q']==self.fixture['sku'] for name,args in calls))
        self.assertEqual([row['rows'] for row in self.observations], [100,100,100,66])

    def test_lot_uses_exact_original_product_lot_location_grade(self):
        owner,calls = self.owner([self.page(0,['one'],1)])
        read_all(owner,self.fixture,'LOT','BEFORE_COMMIT',self.observations)
        self.assertEqual(calls,[('erp_cp7_get_fg_ledger_v2', {'p_query': {
            'product_id':'product','lot_id':'lot','location_id':'location','quality_grade':'GRADE_A',
            'purpose':'CARD','limit':100,'offset':0}})])

    def test_refusal_never_becomes_empty(self):
        owner,calls=self.owner([{'status':403,'body':{}}])
        with self.assertRaises(AssertionError):read_all(owner,self.fixture,'BOOK','AFTER_COMMIT',self.observations)
        self.assertEqual(len(calls),1)

    def test_truncated_final_page_refused(self):
        owner,_=self.owner([self.page(0,['one'],366)])
        with self.assertRaises(AssertionError):read_all(owner,self.fixture,'BOOK','AFTER_COMMIT',self.observations)

    def test_duplicate_between_pages_refused(self):
        owner,_=self.owner([self.page(0,['one'],2,1),self.page(1,['one'],2)])
        with self.assertRaises(AssertionError):read_all(owner,self.fixture,'BOOK','AFTER_COMMIT',self.observations)

    def test_nonadvancing_offset_refused(self):
        owner,_=self.owner([self.page(0,['one'],2,0)])
        with self.assertRaises(AssertionError):read_all(owner,self.fixture,'BOOK','AFTER_COMMIT',self.observations)

    def test_skipped_offset_refused(self):
        owner,_=self.owner([self.page(0,['one'],3,2)])
        with self.assertRaises(AssertionError):read_all(owner,self.fixture,'BOOK','AFTER_COMMIT',self.observations)

    def test_changed_total_between_pages_refused(self):
        owner,_=self.owner([self.page(0,['one'],2,1),self.page(1,['two'],3)])
        with self.assertRaises(AssertionError):read_all(owner,self.fixture,'BOOK','AFTER_COMMIT',self.observations)

    def test_wrong_returned_offset_refused(self):
        owner,_=self.owner([self.page(1,['one'],1)])
        with self.assertRaises(AssertionError):read_all(owner,self.fixture,'BOOK','AFTER_COMMIT',self.observations)

    def test_fractional_total_refused(self):
        owner,_=self.owner([self.page(0,['one'],'1.5')])
        with self.assertRaises(AssertionError):read_all(owner,self.fixture,'BOOK','AFTER_COMMIT',self.observations)

    def test_empty_continuation_refused(self):
        owner,_=self.owner([self.page(0,[],1,1)])
        with self.assertRaises(AssertionError):read_all(owner,self.fixture,'BOOK','AFTER_COMMIT',self.observations)

    def test_unknown_reader_refused_without_call(self):
        owner,calls=self.owner([])
        with self.assertRaises(AssertionError):read_all(owner,self.fixture,'UNKNOWN','AFTER_COMMIT',self.observations)
        self.assertEqual(calls,[])

    def declared_failure_run(self, changed_snapshot=False, failure_body={'code':'57014'}):
        from datetime import timedelta
        import uuid
        class Cursor:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def execute(self,*args):return self
            def fetchone(self):return ('declared-later-movement',)
        class Connection:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def cursor(self):return Cursor()
            def commit(self):pass
            def rollback(self):pass
        calls=[]
        class Owner:
            def rpc(self,name,args):
                calls.append((name,args))
                return {'status':500,'body':copy.deepcopy(failure_body)}
        fixture=dict(self.fixture,tag='DECLARED-STANDIN-NOTE',sale='original')
        stock=lambda *args,**kwargs:copy.deepcopy(fixture)
        def posted(cur,f,*args):f['sale']='original';return f
        snapshots=iter(['BEFORE','CHANGED'if changed_snapshot else'BEFORE'])
        source=SimpleNamespace(fg=SimpleNamespace(ax=SimpleNamespace(r1=SimpleNamespace(now=lambda cur:datetime(2026,10,3,tzinfo=timezone.utc)))),
                               read=lambda *args:{'detail':{'items':[{'id':'original-line'}]}})
        stubs=dict(timedelta=timedelta,uuid=uuid,source=source,stock=stock,posted=posted,
                   unchanged_facts=lambda *args:{'original':24},
                   ownership=SimpleNamespace(verify=lambda cur:{'definition':'unchanged'}),
                   snapshot=lambda cur:next(snapshots),edit=lambda *args:({'sale_id':'original'},'1'),
                   complete_actual_http_history=lambda *args:{str(i):{'id':str(i)}for i in range(366)})
        with patch.dict(namespace,stubs):
            result=namespace['year_committed_actual_http'](SimpleNamespace(connect=Connection),Owner(),None)
        return result,calls

    def test_actual_command_timeout_is_incomplete_and_never_retried_with_declared_standins(self):
        result,calls=self.declared_failure_run()
        self.assertEqual(result['status'],'INCOMPLETE')
        self.assertEqual(result['sqlstate'],'57014')
        self.assertTrue(result['actual_full_Native_and_private_rollback'])
        self.assertEqual(result['command_attempts'],1)
        self.assertEqual([name for name,_ in calls],['erp_cp7_correct_note_v1'])

    def test_changed_failure_snapshot_cannot_claim_atomic_rollback_with_declared_standins(self):
        result,calls=self.declared_failure_run(True)
        self.assertEqual(result['status'],'INCOMPLETE')
        self.assertFalse(result['actual_full_Native_and_private_rollback'])
        self.assertEqual(len(calls),1)

    def test_non_json_command_failure_remains_incomplete_without_retry_with_declared_standins(self):
        result,calls=self.declared_failure_run(failure_body=None)
        self.assertEqual(result['status'],'INCOMPLETE')
        self.assertEqual(result['HTTP_status'],500)
        self.assertIsNone(result['sqlstate'])
        self.assertTrue(result['actual_full_Native_and_private_rollback'])
        self.assertEqual(len(calls),1)


if __name__=='__main__':
    unittest.main()
