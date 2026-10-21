"""Two frozen owning corrections; import and case registration execute no SQL."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json
import uuid

import native_consumer_cases as retained
import native_basic_cases as basic
import native_refund_cases as refund
import cp7_payment_correction_cases as correction

native,fixture = basic.native,basic.fixture
HERE = Path(__file__).resolve().parent
GOLD = json.loads((HERE/'EXPECTED.json').read_bytes())
IDS = retained.IDS+tuple(row['id']for row in GOLD['positive'])
assert len(IDS)==len(set(IDS))==GOLD['expected_count']==20


def observed(cur,pair):
    native.b.api.admin(cur)
    state = basic.observation(cur,pair)
    state['payment_correction_tables'] = {name:native._array(cur,'cp7_payment_correction.'+name,'true',())
        for name in ('requests','context','links')}
    state['payment_source_tables'] = {name:native._array(cur,'cp7_credit.'+name,'true',())
        for name in ('payment_source_context_v1','payment_source_legs_v1')}
    return state


def refusal(cur,pair,invoke,expected):
    before=observed(cur,pair)
    result=fixture.signed._refuse(cur,invoke,'P0001',expected)
    assert observed(cur,pair)==before,'PAYMENT_CORRECTION_REFUSAL_CHANGED_NATIVE_PRIVATE_CASH_DAILY_OR_AUDIT'
    return result


def last_link_failure(cur,pair,intent,version):
    before=observed(cur,pair)
    native.b.api.admin(cur)
    cur.execute('savepoint payment_source_last_link_fault')
    try:
        cur.execute("create function cp7_credit._payment_source_test_last_fault_v1()returns trigger language plpgsql as $$begin raise exception 'OW04_TEST_LAST_NATIVE_LINK_FAILURE';end $$")
        cur.execute('create trigger ow04_test_after_real_link after insert on cp7_payment_correction.links for each row execute function cp7_credit._payment_source_test_last_fault_v1()')
        try:
            correction.correct(cur,intent,version,uuid.uuid4())
        except Exception as error:
            assert 'OW04_TEST_LAST_NATIVE_LINK_FAILURE'in str(error),str(error)
        else:
            raise AssertionError('LAST_NATIVE_LINK_FAULT_DID_NOT_FIRE')
    finally:
        cur.execute('rollback to savepoint payment_source_last_link_fault')
        cur.execute('release savepoint payment_source_last_link_fault')
        native.b.api.admin(cur)
    assert observed(cur,pair)==before,'LAST_LINK_FAILURE_LEFT_COMPOUND_NATIVE_OR_CREDIT_EFFECTS'
    return dict(test_only_disposable_after_insert_trigger=True,actual_inverse_replacement_credit_and_link_reached=True,
        error='OW04_TEST_LAST_NATIVE_LINK_FAILURE',whole_state_restored=True)


def positive(cur,today,index,used_guard):
    with native.isolated(cur):
        gold=GOLD['positive'][index]
        pair=fixture.prepare(cur,today)
        if gold['action']=='APPLY':
            consumed,consumer_envelope,consumer_request=basic.apply(cur,pair,'80.00')
        else:
            consumed,consumer_envelope,consumer_request=refund.refund(cur,pair,'80.00')
        assert fixture.profiles(cur,pair)==gold['before']
        native.b.api.admin(cur)
        source=pair['source']['f'];sale=source['sale']
        original_fact=correction.payment_fact(cur,source['payment'])
        original_journal=cur.execute('select original_journal_entry_id from erp.sales_payment_posting_facts where payment_id=%s',
            (source['payment'],)).fetchone()[0]
        original_payload=cur.execute('select cp7_credit.materialized_journal_payload(%s)',(original_journal,)).fetchone()[0]
        original_consumer=native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(pair['initial_result']['credit_id'],))
        consumer_journal=native.journal(cur,consumed['journal_id'])
        physical=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(sale,)).fetchone()[0]
        intent,version=correction.payload(cur,source,amount='900.00')
        late_failure=last_link_failure(cur,pair,intent,version)
        request=uuid.uuid4()
        result=correction.correct(cur,intent,version,request)
        assert result['action']=='PAYMENT_CORRECT'and result['original_payment_status']=='REVERSED'and result['payment_status']=='POSTED'
        assert result['payment_id']!=str(source['payment'])and result['request_id']==str(request)
        after=fixture.profiles(cur,pair)
        assert after==gold['after'],(gold['id'],after,gold['after'])
        native.b.api.admin(cur)
        assert correction.payment_fact(cur,source['payment'])==original_fact
        assert cur.execute('select cp7_credit.materialized_journal_payload(%s)',(original_journal,)).fetchone()[0]==original_payload
        assert native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(pair['initial_result']['credit_id'],))==original_consumer
        assert native.journal(cur,consumed['journal_id'])==consumer_journal
        actual=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(sale,)).fetchone()[0]
        for name in ('items','allocations','returns','return_items','fg_lots','hpp_versions','stock_movements','inventory_balances',
                     'opening_hpp_states','opening_hpp_corrections','po_hpp_states','po_hpp_events','nonpo_hpp_events','hpp_journals','hpp_balances'):
            assert actual[name]==physical[name],('PAYMENT_CORRECTION_CHANGED_STOCK_OR_HPP',name)
        assert cur.execute('select count(*)from erp.sales_payments where sale_id=%s',(pair['target']['sale'],)).fetchone()[0]==0
        operation,proof=cur.execute("select operation_id,actual_source_proof from cp7_credit.source_operation_materializations_v1 where request_id=%s and sale_id=%s and action='PAYMENT_CORRECT'",(request,sale)).fetchone()
        cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(operation,))
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        before_replay=observed(cur,pair)
        assert correction.correct(cur,intent,version,request)==result
        assert observed(cur,pair)==before_replay,'COMPLETED_PAYMENT_CORRECTION_REPLAY_CREATED_EFFECTS'
        changed=deepcopy(intent);changed['replacement']['amount']='899.99'
        changed_refusal=refusal(cur,pair,lambda:correction.correct(cur,changed,version,request),'CP7_SALES_REQUEST_CHANGED')
        stale_refusal=refusal(cur,pair,lambda:correction.correct(cur,intent,version,uuid.uuid4()),'CP7_SALES_REVIEW_CHANGED')
        guard=used_guard(cur)
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        return dict(status='PASS',id=gold['id'],expected=gold['after'],observed=after,receipt=result,
            late_last_link_failure=late_failure,completed_replay_one_effect=True,changed_UUID_payload_refusal=changed_refusal,
            stale_other_UUID_refusal=stale_refusal,source_operation_id=str(operation),actual_source_proof=proof,
            original_payment_and_consumer_facts_retained=True,all_physical_HPP_facts_unchanged=True,
            actual_compound_half_cash_from_fixed_before_and_exact_inverse=(str(Decimal(gold['before']['cash'])-Decimal('1000.00'))),
            used_complete_owner_removal_guard=guard,real_Auth_HTTP_browser_races_qualified=False,production_go=False)


def cases(cur,today,used_guard):
    return retained.cases(cur,today)+[(gold['id'],lambda index=index:positive(cur,today,index,used_guard))
        for index,gold in enumerate(GOLD['positive'])]
