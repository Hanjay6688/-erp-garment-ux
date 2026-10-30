"""Declared local API/oracle doubles; actual Native/Auth/browser credit is zero."""
from copy import deepcopy
from datetime import date
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace as Box
from unittest import TestCase,main
from unittest.mock import patch
import ast
import importlib.util
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


b=load('s03_lawful_test_lossless_business',HERE/'business.py')
f=load('s03_lawful_test_fixture_oracles',HERE/'lawful_fixture.py')


def raw_facts():
    common={key:None for key in f.FG_FIELDS}
    common.update(product_id='product',lot_id='lot',location_id='warehouse',quality_grade='GOOD',
        customer_id=None,source_type='LOCAL_SQL_DOUBLE',source_id='source',physical_at='2026-10-01T01:00:00Z',
        system_created_at='2026-10-01T01:00:01Z',created_by='owner',reversal_of_id=None,notes='retained',book_order=1)
    receiving=dict(common,id='qc',movement_type='QC_GOOD',qty_signed=10,unit_hpp_snapshot='10.00')
    sale=dict(common,id='sale',movement_type='SALE',qty_signed=-4,unit_hpp_snapshot='10.00',book_order=2,customer_id='customer')
    hpp=dict(id='old_hpp',lot_id='lot',is_current=True,qty_basis_pcs=10,total_cost='100.00',hpp_per_pcs='10.00')
    before=dict(FG=[receiving,sale],current_HPP=[hpp],HPP_history=[deepcopy(hpp)],HPP_components=[dict(id='base_component',hpp_version_id='old_hpp',total_cost='100.00')],
        journal_headers=[dict(id='old_journal',status='POSTED',amount='100')],
        journal_lines=[dict(id='old_line',journal_entry_id='old_journal',debit='100',credit='0')],GL=dict(WIP=D(0),FG_INVENTORY=D(60),COGS=D(40)))
    after=deepcopy(before);after['FG'][0]['unit_hpp_snapshot']='110.003'
    new=dict(hpp,id='new_hpp',total_cost='1100.03',hpp_per_pcs='110.003')
    after['current_HPP']=[new];after['HPP_history'][0]['is_current']=False;after['HPP_history'].append(new)
    after['HPP_components'].append(dict(id='allocation_component',hpp_version_id='new_hpp',total_cost='1100.03'))
    after['GL']=dict(WIP=D(0),FG_INVENTORY=D('660.02'),COGS=D('440.01'))
    return before,after


class Derivations(TestCase):
    def test_three_case_anchors_reverse_to_exact15fe_and_eight_callbacks_and_helpers_stay_exact(self):
        raw=(ROOT/b.ORIGINAL).read_bytes();value,proof=b.derive(raw)
        self.assertEqual(proof['counted_changes'],3)
        self.assertFalse(proof['original_eleven_runtime_callbacks_byte_exact'])
        pairs=json.loads((HERE/'CALLBACK_CHANGES.json').read_bytes())['changes']
        for row in reversed(pairs):value=value.replace(row['after'],row['before'],1)
        self.assertEqual(value.encode(),raw)
        self.assertTrue(proof['original_eight_callbacks_unchanged'])
        self.assertTrue(proof['original_helpers_and_committed_witness_unchanged'])

    def test_rogue_original_or_duplicate_anchor_fails_closed(self):
        raw=(ROOT/b.ORIGINAL).read_bytes()
        with self.assertRaisesRegex(ValueError,'ORIGINAL15FE'):b.derive(raw+b'\n')
        with self.assertRaisesRegex(ValueError,'ONE_EXACT_PRIVATE_ANCHOR'):b.substitute(b'needle needle',[('needle','next')])

    def test_all_original_financial_and_cancel_assertions_survive_except_named_cache_predicate(self):
        value,proof=b.derive((ROOT/b.ORIGINAL).read_bytes())
        for text in ("oracle['denominator']==20",'[50001,50002]',"expected*D(4)/10", "'WIP':D(0)",
            "D(c.po_hpp(cur,g['po'])[0])==before_cost and gl()==before_gl",
            "assert physical()==original_physical and c.po_wip_balance(cur,g['po'])==0",
            "'CP7_S03_ALLOCATION_BEFORE_WIP_AVAILABLE'","'CP7_S03_PERIOD_CLOSED'",
            "assert accrued(cur,s)==original"):
            self.assertIn(text,value)
        self.assertIn('LAWFUL.reopen_source(cur,s,core=CORE,evidence=evidence)',value)
        self.assertEqual(value.count('LAWFUL.earned('),1)

    def test_Reader3_has_one_explicit_API_anchor_all_other_bytes_reverse_exact(self):
        raw=(ROOT/b.READER).read_bytes();value,proof=b.substitute(raw,[(b.READER_BEFORE,b.READER_AFTER)])
        self.assertEqual(proof['counted_changes'],1)
        self.assertEqual(value.replace(b.READER_AFTER,b.READER_BEFORE).encode(),raw)
        self.assertIn('core=original();f=core.f',value)

    def test_native_runner_preserves_fresh11_then_reader_before_same_committed_witness(self):
        helper=load('s03_lawful_test_private_runner',HERE/'derive.py')
        raw=(ROOT/'scripts/current-attendance-period-choice-native11-qualification/native_runner.py').read_bytes()
        value,proof=helper.native(raw)
        self.assertEqual(proof['parent']['counted_changes'],5)
        self.assertFalse(proof['parent']['original11_factory_counts_assertions_and_callbacks_unchanged'])
        self.assertEqual(proof['explicit_private_business_binding']['counted_changes'],1)
        self.assertLess(value.index('COMPLETE_ELEVEN_PASS_REQUIRED'),value.index('run_actual_reader3('))
        self.assertLess(value.index('run_actual_reader3('),value.index('business.allocate(cursor, fixture, output)'))
        original=ast.parse(raw);derived=ast.parse(value)
        names=('require_local','retain_originals','sequence_prefix')
        funcs=lambda t:{n.name:ast.dump(n,include_attributes=False)for n in t.body if isinstance(n,ast.FunctionDef)}
        for name in names:self.assertEqual(funcs(original)[name],funcs(derived)[name])


class Valuation(TestCase):
    def check(self,before,after):
        return f.assert_valuation(before,after,D('1000.03'),lot='lot',baseline_cost=D('100'),
            before_gl=before['GL'],after_gl=after['GL'])

    def test_exact_Native_cache_positive_old_fullrow_false_negative_and_all_SALE_rows_unchanged(self):
        before,after=raw_facts();self.assertNotEqual(after['FG'],before['FG'])
        result=self.check(before,after)
        self.assertFalse(result['old_full_row_predicate']);self.assertTrue(result['all_16_non_cost_fields_equal'])
        self.assertEqual(before['FG'][1],after['FG'][1])

    def test_every_other_physical_field_is_checked_not_a_small_projection(self):
        for field in f.FG_FIELDS-{'unit_hpp_snapshot'}:
            with self.subTest(field=field):
                before,after=raw_facts();after['FG'][0][field]='ROGUE_CHANGE'
                with self.assertRaises((AssertionError,KeyError,ValueError)):self.check(before,after)

    def test_unknown_field_or_rowset_or_SALE_cache_cannot_be_excluded(self):
        changes=(lambda d:d['FG'][0].update(rogue_field='unknown'),lambda d:d['FG'].pop(),
            lambda d:d['FG'][1].update(unit_hpp_snapshot='110.003'))
        for change in changes:
            before,after=raw_facts();change(after)
            with self.assertRaises(AssertionError):self.check(before,after)

    def test_cache_must_equal_current_Native_HPP_and_own_allocation_arithmetic(self):
        for change in (lambda d:d['FG'][0].update(unit_hpp_snapshot='111'),
            lambda d:d['current_HPP'][0].update(total_cost='1100.04'),
            lambda d:d['current_HPP'][0].update(qty_basis_pcs=11)):
            before,after=raw_facts();change(after)
            with self.assertRaises(AssertionError):self.check(before,after)

    def test_baseline_posted_journal_and_HPP_fact_mutation_refused(self):
        for change in (lambda d:d['journal_headers'][0].update(status='REVERSED'),
            lambda d:d['journal_lines'][0].update(debit='0'),
            lambda d:d['HPP_history'][0].update(total_cost='0')):
            before,after=raw_facts();change(after)
            with self.assertRaises(AssertionError):self.check(before,after)


class WorkerAPI(TestCase):
    def test_exact_keyset_unknown_or_missing_worker_refuses_without_any_writer(self):
        for known,eligible in ((['known'],['known','unknown']),(['known'],[]),([],[]),(['a','b'],['a','b'])):
            calls=[]
            class Cursor:
                def execute(self,sql,args):calls.append(sql);return self
                def fetchall(self):return [(v,)for v in (known if len(calls)==1 else eligible)]
            core=Box(f=Box(admin=lambda c:None))
            with self.assertRaisesRegex(ValueError,'KNOWN_P1_WORKER|UNKNOWN_ELIGIBLE'):
                f.known_worker(Cursor(),dict(payroll='p',contractor='cid'),date(2026,10,2),core=core)
            self.assertTrue(all(sql.lstrip().startswith('select')for sql in calls))

    def test_one_known_worker_is_reused_through_fresh_rate_and_explicit_PRESENT(self):
        calls=[];source=dict(day=date(2026,10,1),contractor='cid',payroll='p1',owner='owner')
        worker='worker';row=dict(contractor_id='cid',pay_scheme='DAILY',row_version=17)
        class Cursor:
            def execute(self,sql,args):
                calls.append(('SQL',sql,args));self.sql=sql;return self
            def fetchall(self):return [(worker,)]
        def one(cur,sql,args=()):
            calls.append(('one',sql,args))
            if 'to_jsonb(w)'in sql:return row
            if 'insert into erp.payroll_settlements'in sql:return 'p2'
            if 'payroll_attendance_items'in sql:return [dict(worker_id=worker,amount='20.02',daily_rate_snapshot='20.02')]
            raise AssertionError(sql)
        def native(cur,sql,args):
            calls.append(('Native',sql,args));self.assertIn('set_worker_daily_rate_v1',sql)
            self.assertEqual(args[:3],(worker,D('20.02'),date(2026,10,2)));self.assertEqual(args[-1],17)
            return dict(worker_id=worker,daily_rate='20.02',effective_from='2026-10-02')
        def attendance(cur,sql,args):
            calls.append(('attendance',sql,args))
            if 'save_attendance'in sql:
                payload=json.loads(args[0]);self.assertEqual(payload['attendance'],[dict(worker_id=worker,attendance_date='2026-10-02',status='PRESENT')])
                return dict(period_id='period',row_version=9)
            self.assertIn('post_attendance',sql);return dict(status='POSTED')
        s=Box(native=attendance,doc=lambda cur,p:dict(attendance_total='20.02'),act=lambda cur,a,doc:calls.append(('act',a,doc)))
        cp=Box(s=s,bc=Box(awp=Box(find=lambda v,k:v[k])))
        core=Box(f=Box(admin=lambda c:None,one=one,native=native,REASON='Owner reviewed',hp=Box(cp17=lambda:cp)))
        evidence={}
        with patch.object(f,'source_facts',return_value={'immutable_P1':'LOCAL_API_DOUBLE'}):
            result=f.earned(Cursor(),source,date(2026,10,2),core=core,evidence=evidence)
        self.assertEqual(result,'p2');self.assertEqual([r[1]for r in calls if r[0]=='act'],['PREPARE','APPROVE'])
        self.assertTrue(all('save_worker_roster'not in str(call)for call in calls))
        self.assertEqual(evidence['lawful_fixture_successor']['P2_known_worker'][0]['exact_eligible_worker_ids'],[worker])

    def test_invalid_period_or_amount_refuses_before_fixtures(self):
        for output,amount in ((date(2026,10,1),D('20.02')),(date(2026,10,2),D(0)),(date(2026,10,2),D('20.021'))):
            with self.assertRaisesRegex(ValueError,'LATER_EXACT_DAILY_CENTS'):
                f.earned(None,dict(day=date(2026,10,1)),output,amount,core=None)


class OwningLifecycle(TestCase):
    def test_closed_REVERSE_negative_then_real_owner_fresh_review_REOPEN_no_admin_reset(self):
        calls=[];source=dict(day=date(2026,10,1),owner='owner',payroll='p1',contractor='cid')
        class Cursor:
            connection=Box(info=Box(transaction_status=Box(name='IDLE')))
        def one(cur,sql,args=()):
            calls.append((sql,args))
            if 'statement_timestamp()'in sql:return date(2026,10,10)
            if 'accounting_close_filings_v1'in sql:return [dict(id='immutable_filing')]
            if 'get_period_control'in sql:return dict(through='2026-10-10',review_token='a'*32,control=dict(closed_through='2026-10-08'))
            if 'save_period_control'in sql:
                action,payload,key=args;body=json.loads(payload)
                self.assertEqual(action,'REOPEN');self.assertEqual(body['through'],'2026-09-30')
                self.assertEqual(body['review_token'],'a'*32);self.assertTrue(body['reason'])
                return dict(action='REOPEN',closed_through='2026-09-30',request_id=key)
            raise AssertionError(sql)
        def refused(cur,fn,code):calls.append(('CLOSED_FULL_CENSUS_NEGATIVE',code))
        core=Box(f=Box(admin=lambda c:None,one=one,refused=refused,REASON='Owner reviewed',
            hp=Box(auth=Box(actor=lambda c,s:calls.append(('OWNER',s))))))
        evidence={}
        with patch.object(f,'source_facts',return_value={'P1':'IMMUTABLE_LOCAL_DOUBLE'}):
            result=f.reopen_source(Cursor(),source,core=core,evidence=evidence)
        self.assertEqual(result['action'],'REOPEN');self.assertEqual(calls[0][0],'CLOSED_FULL_CENSUS_NEGATIVE')
        self.assertTrue(any(r[0]=='OWNER'for r in calls));self.assertFalse(any('update erp.accounting_period_control'in r[0]for r in calls))
        self.assertFalse(evidence['lawful_fixture_successor']['OWNER_REOPEN'][0]['administrative_control_reset_used'])

    def test_cancel_requires_full_FG_HPP_GL_and_exact_linked_inverse_with_both_dates(self):
        before,_=raw_facts();after=deepcopy(before)
        after['current_HPP'][0]['id']='restored_hpp';after['HPP_history'][0]['is_current']=False
        after['HPP_history'].append(deepcopy(after['current_HPP'][0]))
        original=dict(id='post',status='POSTED',source_type='ATTENDANCE_HPP_POOL',source_id='pool',economic_date='2026-10-02',transaction_date='2026-10-02')
        inverse=dict(id='inverse',status='POSTED',source_type='JOURNAL_REVERSAL',source_id='post',reversal_of_id='post',economic_date='2026-10-10',transaction_date='2026-10-10')
        dims=dict(account_id='WIP',customer_id=None,vendor_id=None,contractor_id='cid',po_id='po',product_id=None)
        lines=[dict(dims,id='debit',journal_entry_id='post',debit='1000.03',credit='0',description='Original allocation')]
        inverses=[dict(lines[0],id='credit',journal_entry_id='inverse',debit='0',credit='1000.03',description='Reversal: Original allocation')]
        def one(cur,sql,args=()):
            if 'statement_timestamp()'in sql:return date(2026,10,10)
            if 'resolve_accounting_transaction_date'in sql:return date(2026,10,10)
            if 'journal_entries'in sql:return dict(original,status='REVERSED')if args[0]=='post'else inverse
            if 'journal_lines'in sql:return lines if args[0]=='post'else inverses
            raise AssertionError(sql)
        core=Box(f=Box(one=one));evidence={}
        allocated=deepcopy(before);allocated['journal_headers'].append(original);allocated['journal_lines'].extend(deepcopy(lines))
        after['journal_headers'].extend([dict(original,status='REVERSED'),inverse]);after['journal_lines'].extend(lines+inverses)
        kwargs=dict(after_allocation=allocated,core=core,evidence=evidence,made=dict(pool_id='pool'),cancelled=dict(native_result=dict(reversal_journal_entry_id='inverse')),oracle=dict(journal=original))
        with patch.object(f,'finished_facts',return_value=after):
            f.assert_cancelled(None,{},before,**kwargs)
            inverses[0]['credit']='1000.04'
            with self.assertRaisesRegex(AssertionError,'EXACT_DIMENSION_AMOUNT_INVERSE'):
                f.assert_cancelled(None,{},before,**kwargs)
            inverses[0]['credit']='1000.03';after['FG'][0]['notes']='unknown mutation'
            with self.assertRaisesRegex(AssertionError,'FULL_FG_ROWS_NOT_EXACT'):
                f.assert_cancelled(None,{},before,**kwargs)
        self.assertTrue(evidence['lawful_fixture_successor']['Native_finished_cancel'][0]['linked_inverse_signs_dimensions_both_dates_exact'])


if __name__=='__main__':main(verbosity=2)
