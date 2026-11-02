"""Synthetic paired-stage and complete sequence-witness protocol controls."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from . import assembly,case_boundary as boundary

def sample(*,gap=False):
    groups={k:{}for k in('aggregates','columns','constraints','database_authority','default_privileges','enums',
        'event_triggers','extensions','functions','indexes','inheritance','memberships','policies','relations','roles',
        'rules','schemas','sequence_ownership','sequences','triggers','type_implementation','types')}
    for name,(table,column,kind)in boundary.OWNED.items():groups['sequence_ownership'][name]=[kind,table,column]
    for name in boundary.WITNESSES:groups['sequences'][name]=deepcopy(boundary.SEQUENCE_DEFINITION)
    groups['columns']['erp.fg_stock_movements:book_order']=["nextval('erp.fg_stock_book_order_seq'::regclass)"]
    data={'erp.audit_logs':[1,'original'],'erp.sales_headers':[1,'original-sale']}
    data.update({'sequence:'+n:['10',True]for n in boundary.WITNESSES})
    data['sequence:auth.refresh_tokens_id_seq']=['1',False]
    before=dict(actual_all22=groups,full_data_and_sequences=data);after=deepcopy(before)
    sequences={k:deepcopy(v)for k,v in data.items()if k.startswith('sequence:')}
    sequences['sequence:erp.audit_logs_id_seq']=['12',True]
    sequences['sequence:'+boundary.FG]=['12'if gap else'11',True]
    rows={name:[]for name in boundary.WITNESSES}
    rows['erp.audit_logs_id_seq']=[dict(id=11,action='POST'),dict(id=12,action='POST')]
    rows[boundary.FG]=[dict(id='fg-native',book_order=11)]
    after['full_data_and_sequences'].update(deepcopy(sequences))
    value=dict(before=before,after=after,after_operation=dict(sequences=sequences,generated_rows=rows))
    result={};case='NONPAYABLE_NATIVE_POSITIVE_HPP_ZERO_REIMBURSEMENT_FROZEN_HISTORY_AND_REPLAY'
    if gap:
        failed_before=deepcopy(before);failed_after=deepcopy(before)
        failed_before['full_data_and_sequences']['sequence:'+boundary.FG]=['11',True]
        failed_after['full_data_and_sequences']['sequence:'+boundary.FG]=['12',True]
        result=dict(actual_error=deepcopy(boundary.MISSING_ERROR),before=failed_before,after=failed_after,
            actual_sequence_allocations={'sequence:'+boundary.FG:dict(before=['11',True],after=['12',True])})
        case=boundary.MISSING
    return value,case,result

class QualificationPreparationControls(unittest.TestCase):
    def test_every_generated_native_sequence_value_has_an_actual_surviving_row(self):
        value,case,result=sample();proof=boundary.validate(value,case_id=case,result=result)
        self.assertEqual(proof['accounted_sequences']['erp.audit_logs_id_seq']['actual_allocations'],2)
        self.assertTrue(proof['all_table_rows_restored']);self.assertFalse(proof['case_sequence_reset_performed'])

    def test_exact_failed_good_gap_is_retained_without_claiming_savepoint_sequence_restore(self):
        value,case,result=sample(gap=True);proof=boundary.validate(value,case_id=case,result=result)
        self.assertEqual(proof['accounted_sequences'][boundary.FG]['declared_failed_posting_gaps'],['12'])
        self.assertTrue(proof['complete_outer_backup_ALL_sequence_restore_required'])
        with self.assertRaisesRegex(ValueError,'EXACT_DECLARED_NATIVE_GOOD_REFUSAL'):
            boundary.validate(value,case_id='ANOTHER_CASE',result=result)

    def test_unwitnessed_gap_counterfeit_refusal_or_changed_row_refuses(self):
        for mode in('missing_row','extra_row','wrong_error','changed_failed_row','outside_gap'):
            value,case,result=sample(gap=True)
            if mode=='missing_row':value['after_operation']['generated_rows']['erp.audit_logs_id_seq'].pop()
            elif mode=='extra_row':value['after_operation']['generated_rows'][boundary.FG].append(dict(book_order=12))
            elif mode=='wrong_error':result['actual_error']['message']='OTHER_ERROR'
            elif mode=='changed_failed_row':result['after']['full_data_and_sequences']['erp.sales_headers']=[2,'changed']
            else:
                result['before']['full_data_and_sequences']['sequence:'+boundary.FG]=['12',True]
                result['after']['full_data_and_sequences']['sequence:'+boundary.FG]=['13',True]
                result['actual_sequence_allocations']['sequence:'+boundary.FG]=dict(before=['12',True],after=['13',True])
            with self.subTest(mode=mode),self.assertRaises(ValueError):boundary.validate(value,case_id=case,result=result)

    def test_other_sequence_change_reset_omission_or_authority_change_refuses(self):
        for mode in('other_sequence','reset','missing_sequence','rows','catalog','ownership','cache'):
            value,case,result=sample()
            if mode=='other_sequence':
                value['after']['full_data_and_sequences']['sequence:auth.refresh_tokens_id_seq']=['2',True]
                value['after_operation']['sequences']['sequence:auth.refresh_tokens_id_seq']=['2',True]
            elif mode=='reset':value['after']['full_data_and_sequences']['sequence:erp.audit_logs_id_seq']=['10',True]
            elif mode=='missing_sequence':value['after_operation']['sequences'].pop('sequence:auth.refresh_tokens_id_seq')
            elif mode=='rows':value['after']['full_data_and_sequences']['erp.sales_headers']=[2,'changed']
            elif mode=='catalog':value['after']['actual_all22']['roles']['extra']=['new-grant']
            elif mode=='ownership':
                value['before']['actual_all22']['sequence_ownership']['erp.audit_logs_id_seq']=['a','erp.other','id']
                value['after']['actual_all22']=deepcopy(value['before']['actual_all22'])
            else:
                value['before']['actual_all22']['sequences']['erp.audit_logs_id_seq'][-2]='2'
                value['after']['actual_all22']=deepcopy(value['before']['actual_all22'])
            with self.subTest(mode=mode),self.assertRaises(ValueError):boundary.validate(value,case_id=case,result=result)

    def test_assembly_closed_parent_precedes_any_runtime_or_cursor(self):
        with patch.object(assembly,'runtime',side_effect=AssertionError('RUNTIME_BEFORE_PARENT')):
            for operation,args in((assembly.install_delta,(object(),{})),(assembly.rollback_delta_preuse,(object(),{}))):
                with self.subTest(operation=operation.__name__),self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
                    operation(*args)

    def test_pair_installs_money_then_settings_and_used_settings_refuses_before_money_inverse(self):
        events=[]
        @contextmanager
        def atomic(cur):
            events.append('atomic-enter')
            try:yield
            finally:events.append('atomic-exit')
        fin=SimpleNamespace(qualification=lambda:None,
            install_delta=lambda cur,parent:(events.append('money-install')or{'money':'state'}),
            rollback_delta_preuse=lambda cur,state:(events.append('money-inverse')or{'used_guard_before_DDL':True}))
        def denied(cur,state):events.append('settings-used-refusal');raise ValueError('MODEL_USED')
        settings=SimpleNamespace(install_delta=lambda cur,state:(events.append('settings-install')or{'parent':state}),
            rollback_delta_preuse=denied)
        with patch.object(assembly,'financial',fin),patch.object(assembly,'settings',settings),patch.object(assembly,'runtime',return_value=(None,None,None,SimpleNamespace(atomic=atomic),None)):
            self.assertEqual(assembly.install_delta(object(),{}),{'parent':{'money':'state'}})
            self.assertEqual(events,['atomic-enter','money-install','settings-install','atomic-exit']);events.clear()
            with self.assertRaisesRegex(ValueError,'MODEL_USED'):assembly.rollback_delta_preuse(object(),{'parent':{}})
            self.assertEqual(events,['atomic-enter','settings-used-refusal','atomic-exit'])

if __name__=='__main__':unittest.main()
