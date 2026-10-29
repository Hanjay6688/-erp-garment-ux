"""Local synthetic contract/source controls only; no Native operation is invoked."""
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from hashlib import sha256
import ast
import importlib.util
import json
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
factory=load('unit_d1_cap_native_factory',HERE/'factory.py')
guard=factory.guard
source=json.loads((HERE/'SOURCE.json').read_bytes())
IDS=tuple(source['original_Native13_ids'])


class Contract(unittest.TestCase):
    def test_pins_and_exact_api_argument_bodies_admit_no_native_credit(self):
        value,api=guard.admit()
        self.assertFalse(value['Native_executed']);self.assertEqual(len(api['modules']),14)
        self.assertEqual(len(api['functions']),31)
        self.assertEqual(len(IDS),13)

    def test_changed_api_body_or_argument_refuses(self):
        raw=b'def example(cur,today):\n    return 1\n'
        n=ast.parse(raw).body[0]
        pin={'parameters':ast.dump(n.args),'function_sha256':sha256(ast.get_source_segment(raw.decode(),n).encode()).hexdigest()}
        guard.api_signatures(raw,{'example':pin})
        for changed in(raw.replace(b'today',b'other'),raw.replace(b'return 1',b'return 2')):
            with self.assertRaisesRegex(ValueError,'API_CHANGED'):guard.api_signatures(changed,{'example':pin})

    def test_explicit_product_selection_is_not_uuid_order(self):
        rows=[dict(product_id='B',allocation_id='uuid-first',allocated_qty='1'),dict(product_id='A',allocation_id='uuid-last',allocated_qty='5')]
        self.assertEqual(guard.allocation(rows,'A',5)['allocation_id'],'uuid-last')
        for bad in([],rows[:1],rows+[deepcopy(rows[1])],[dict(rows[1],allocated_qty='4')],[dict(rows[1],allocation_id=None)]):
            with self.assertRaisesRegex(ValueError,'EXACT_PRODUCT_ALLOCATION'):guard.allocation(bad,'A',5)

    def test_wrapper_only_multi_changes_identity_and_original_runs_after_preludes(self):
        events=[]
        callbacks=[(name,lambda name=name:events.append(name)or dict(status='PASS',old_assertions='PRESERVED',id=name))for name in IDS]
        wrapped=factory.wrap(callbacks,IDS,lambda:events.append('PRELUDES')or dict(SYNTHETIC_LOCAL_ONLY=True))
        self.assertEqual([key for key,_ in wrapped],list(IDS))
        for (key,original),(_,actual)in zip(callbacks,wrapped):
            self.assertEqual(actual is original,key!=factory.TARGET)
        result=dict(wrapped)[factory.TARGET]()
        self.assertEqual(events,['PRELUDES',factory.TARGET])
        self.assertEqual(result['old_assertions'],'PRESERVED')
        self.assertEqual(result['product_cap_native_augmentation'],dict(SYNTHETIC_LOCAL_ONLY=True))

    def test_prelude_failure_does_not_run_original_or_return_pass(self):
        seen=[];callbacks=[(key,lambda:seen.append('old'))for key in IDS]
        def failure():raise ValueError('SYNTHETIC_PRELUDE_FAILED')
        wrapped=factory.wrap(callbacks,IDS,failure)
        with self.assertRaisesRegex(ValueError,'PRELUDE_FAILED'):dict(wrapped)[factory.TARGET]()
        self.assertEqual(seen,[])

    def test_incomplete_reordered_or_duplicate_ids_fail(self):
        callbacks=[(key,lambda:None)for key in IDS]
        for bad in(callbacks[:-1],list(reversed(callbacks)),callbacks+[callbacks[0]]):
            with self.assertRaisesRegex(ValueError,'EXACT13'):factory.wrap(bad,IDS,lambda:None)

    def test_private_proxy_changes_only_cases_never_supplied_module_attributes(self):
        callbacks=[(key,lambda:dict(status='PASS'))for key in IDS]
        marker=object()
        # Explicit business stub tests adapter identity, never a Native outcome.
        fake=SimpleNamespace(__file__=str(ROOT/'scripts/cp7_credit_correction_de/cases.py'),IDS=IDS,
            cases=lambda *_:callbacks,native=marker,fixture=marker,profile=marker,post=marker)
        before=dict(vars(fake));proxy=factory.business(fake)
        self.assertEqual(set(vars(proxy)),set(before))
        for key,value in before.items():
            if key!='cases':self.assertIs(getattr(proxy,key),value)
        self.assertEqual(vars(fake),before)
        with patch.object(factory.prelude,'run',side_effect=AssertionError('NO_NATIVE_DURING_REGISTRATION')):
            planned=proxy.cases(object(),object())
        self.assertEqual([key for key,_ in planned],list(IDS))
        for (key,a),(_,b)in zip(callbacks,planned):
            if key!=factory.TARGET:self.assertIs(a,b)

    def test_inner_positive_sequence_prefix_is_recorded_and_other_changes_fail(self):
        before=dict(catalog={'LOCAL_ONLY':{}},all_rows={'table':[]},identity=('LOCAL','LOCAL','LOCAL'),advisory_locks=[],
            data_and_sequences={'table':[0,'hash'],'sequence:counter':['1',False]})
        after=deepcopy(before);after['data_and_sequences']['sequence:counter']=['3',True]
        prefix=factory.prelude.check_rollback(before,after)
        self.assertEqual(set(prefix),{'sequence:counter'})
        for field,value in(('catalog',{'CHANGED':{}}),('all_rows',{'table':[1]}),('identity',('OTHER',)),('advisory_locks',[1])):
            changed=deepcopy(after);changed[field]=value
            with self.assertRaises(AssertionError):factory.prelude.check_rollback(before,changed)
        changed=deepcopy(after);changed['data_and_sequences']['table']=[1,'changed']
        with self.assertRaises(AssertionError):factory.prelude.check_rollback(before,changed)

    def test_2000_financial_and_stale_boundary_math_are_independent(self):
        for issued,net in(('800.00','1200.00'),('1000.00','1000.00'),('800.01','1199.99')):
            self.assertEqual(D('2000')-D(issued),D(net))
        self.assertEqual(D('800.01')+D('250')-D('200'),D('850.01'))
        self.assertLessEqual(D('600.01')+D('250'),D('1000'))
        self.assertGreater(D('600.01')+D('400'),D('1000'))

    def test_native_writes_use_retained_apis_not_direct_business_dml_or_1000_prepared(self):
        text=(HERE/'prelude.py').read_text();tree=ast.parse(text)
        constants=[n.value.lower().lstrip()for n in ast.walk(tree)if isinstance(n,ast.Constant)and isinstance(n.value,str)]
        self.assertFalse(any(c.startswith(('insert ','update ','delete ','alter table ','create trigger ','setval('))for c in constants))
        self.assertNotIn('.prepared(',text)
        self.assertNotIn('.observe(',text);self.assertNotIn('.refusal(',text)
        for term in("d.drafts.create(cur,a,p)","d.command.command(cur,'POST'","payment['payment_date']=at['payment'].isoformat()",
                     'd.initial._settle(cur,envelope,key)',"'CP7_CREDIT_DE_STALE_REVIEW'","'CP7_CREDIT_DE_REVIEW_REFUSED'",
                     'assert after==before','data_and_sequences','complete_sequence_restore_requires_outer_full_database_backup_restore'):
            self.assertIn(term,text)


if __name__=='__main__':unittest.main()
