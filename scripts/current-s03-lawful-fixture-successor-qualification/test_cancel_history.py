"""Failure-first oracle counters: no Native product defect or execution claimed."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as Box
from datetime import date
from unittest import TestCase,main
from unittest.mock import patch
import importlib.util
import inspect

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('s03_cancel_history_counter_inputs',HERE/'test_lawful.py')
inputs=importlib.util.module_from_spec(spec);spec.loader.exec_module(inputs)
f=inputs.f


def scenario():
    before,allocated=inputs.raw_facts()
    post=dict(id='post',status='POSTED',source_type='ATTENDANCE_HPP_POOL',source_id='pool',economic_date='2026-10-02',transaction_date='2026-10-02')
    inverse=dict(id='inverse',status='POSTED',source_type='JOURNAL_REVERSAL',source_id='post',reversal_of_id='post',economic_date='2026-10-10',transaction_date='2026-10-10')
    dims=dict(account_id='WIP',customer_id=None,vendor_id=None,contractor_id='cid',po_id='po',product_id=None)
    lines=[dict(dims,id='post_debit',journal_entry_id='post',debit='1000.03',credit='0',description='Original allocation'),
        dict(dims,id='post_credit',journal_entry_id='post',po_id=None,debit='0',credit='1000.03',description='Original source')]
    inverses=[dict(row,id='inverse_'+row['id'],journal_entry_id='inverse',debit=row['credit'],credit=row['debit'],description='Reversal: '+row['description'])for row in lines]
    allocated['journal_headers'].append(post);allocated['journal_lines'].extend(deepcopy(lines))
    after=deepcopy(before);restored=dict(before['current_HPP'][0],id='restored_hpp')
    after['current_HPP']=[restored]
    after['HPP_history']=[dict(row,is_current=False)for row in allocated['HPP_history']]+[restored]
    after['HPP_components']=deepcopy(allocated['HPP_components'])+[dict(id='restored_component',hpp_version_id='restored_hpp',total_cost='100.00')]
    after['journal_headers']+= [dict(post,status='REVERSED'),inverse]
    after['journal_lines']+=deepcopy(lines)+inverses
    return before,allocated,after,post


def invoke(before,allocated,after,post):
    def one(cur,sql,args=()):
        if 'statement_timestamp()'in sql:return date(2026,10,10)
        if 'resolve_accounting_transaction_date'in sql:return date(2026,10,10)
        if 'journal_entries'in sql:return next(r for r in after['journal_headers']if r['id']==args[0])
        if 'journal_lines'in sql:return [r for r in after['journal_lines']if r.get('journal_entry_id')==args[0]]
        raise AssertionError(sql)
    kwargs=dict(core=Box(f=Box(one=one)),evidence={},made=dict(pool_id='pool'),
        cancelled=dict(native_result=dict(reversal_journal_entry_id='inverse')),oracle=dict(journal=post))
    # Compatibility is ONLY for preserving the old7bd first-red counter. The
    # fixed runtime API must require after_allocation, with no default/fallback.
    if 'after_allocation'in inspect.signature(f.assert_cancelled).parameters:
        kwargs['after_allocation']=allocated
    with patch.object(f,'finished_facts',return_value=after):
        return f.assert_cancelled(None,{},before,**kwargs)


class CancelHistory(TestCase):
    def test_fixed_runtime_API_requires_pre_cancel_snapshot_without_a_fallback(self):
        param=inspect.signature(f.assert_cancelled).parameters['after_allocation']
        self.assertIs(param.default,inspect.Parameter.empty)

    def test_legitimate_cancel_preserves_all_intermediate_versions_and_full_posted_lines(self):
        invoke(*scenario())

    def test_symmetric_post_and_inverse_mutation_cannot_hide_behind_restored_balance(self):
        before,allocated,after,post=scenario()
        for row in after['journal_lines']:
            if row['id']=='post_debit':row['debit']='1000.04'
            if row['id']=='post_credit':row['credit']='1000.04'
            if row['id']=='inverse_post_debit':row['credit']='1000.04'
            if row['id']=='inverse_post_credit':row['debit']='1000.04'
        with self.assertRaises(AssertionError):invoke(before,allocated,after,post)

    def test_deleting_intermediate_allocation_HPP_version_is_not_a_legitimate_cancel(self):
        before,allocated,after,post=scenario()
        after['HPP_history']=[r for r in after['HPP_history']if r['id']!='new_hpp']
        with self.assertRaises(AssertionError):invoke(before,allocated,after,post)

    def test_intermediate_HPP_component_rewrite_or_removal_refuses(self):
        for remove in (True,False):
            before,allocated,after,post=scenario()
            if remove:after['HPP_components']=[r for r in after['HPP_components']if r['id']!='allocation_component']
            else:next(r for r in after['HPP_components']if r['id']=='allocation_component')['total_cost']='0'
            with self.assertRaises(AssertionError):invoke(before,allocated,after,post)


if __name__=='__main__':main(verbosity=2)
