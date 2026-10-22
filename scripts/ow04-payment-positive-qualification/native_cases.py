"""Pre-execution existing-cohort positive correction journeys; no import SQL.

Literal four-case oracle was frozen before implementation. This is not a PASS.
Retained22 must also execute on any changed financial source.
"""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json
import uuid

import native_basic_cases as basic
import native_refund_cases as refund
import cp7_payment_correction_cases as correction

native,fixture=basic.native,basic.fixture
EXPECTED_SHA256='6e0791fc821da214832a8f488f247a2f8f5ca12900d00c8cd32560e9f431fe13'
PHYSICAL=('items','allocations','returns','return_items','fg_lots','hpp_versions','stock_movements',
 'inventory_balances','opening_hpp_states','opening_hpp_corrections','po_hpp_states','po_hpp_events',
 'nonpo_hpp_events','hpp_journals','hpp_balances')


def expected():
    raw=Path(__file__).with_name('EXPECTED.json').read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA256
    return json.loads(raw)


def observation(cur,pair):
    a=fixture.profiles(cur,pair)
    return dict(source_net=a['source']['net'],source_P=a['source']['P'],I=a['source']['I'],
        C=a['source']['net_consumption'],available=a['source']['available_credit'],source_AR=a['source']['AR'],
        target_P=a['target']['P'],target_U=a['target']['U'],target_AR=a['target']['AR'],cash=a['cash'])


def one_case(cur,today,index,last_link_failure):
    with native.isolated(cur):
        declaration=expected();gold=declaration['cases'][index]
        pair=fixture.prepare(cur,today);source=pair['source']['f'];initial=pair['initial_result']
        use=basic.apply if gold['action']=='APPLY'else refund.refund
        first,envelope,consumer_request=use(cur,pair,'80.00')
        consumers=[first];originals={first['consumption_event_id']:native.journal(cur,first['journal_id'])}
        original_fact=correction.payment_fact(cur,source['payment'])
        physical=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(source['sale'],)).fetchone()[0]
        down,version_down=correction.payload(cur,source,amount='900.00');request_down=uuid.uuid4()
        lowered=correction.correct(cur,down,version_down,request_down)
        lower_fact=correction.payment_fact(cur,lowered['payment_id'])
        if gold['spend_second20']:
            second,_,_=use(cur,pair,'20.00');consumers.append(second)
            originals[second['consumption_event_id']]=native.journal(cur,second['journal_id'])
        workspace=correction.workspace(cur,source,payment_id=lowered['payment_id'])
        assert workspace['contract_version']=='cp7.sales-payment-correction-workspace.v2'
        assert workspace['replacement_capacity']==dict(maximum_amount='1000.00',basis='EXISTING_RETURN_COHORT',
            source_sale_id=str(source['sale']),payment_id=lowered['payment_id'],row_version=workspace['row_version'])
        up,version_up=correction.payload(cur,source,amount='1000.00',payment_id=lowered['payment_id'])
        before=basic.observation(cur,pair)
        over=deepcopy(up);over['replacement']['amount']='1000.01'
        fixture.signed._refuse(cur,lambda:correction.correct(cur,over,version_up,uuid.uuid4()),
            'P0001','CP7_CREDIT_PAYMENT_GROSS_RECEIPT_LIMIT')
        assert basic.observation(cur,pair)==before,'POSITIVE_ONE_CENT_OVER_GROSS_REFUSAL_CHANGED_FACTS'
        late_failure=last_link_failure(cur,pair,up,version_up)if index==0 else None
        request_up=uuid.uuid4();restored=correction.correct(cur,up,version_up,request_up)
        assert restored['original_payment_id']==lowered['payment_id']
        assert restored['payment_id']not in(lowered['payment_id'],str(source['payment']))
        assert observation(cur,pair)==gold['after_restore'],(observation(cur,pair),gold['after_restore'])
        native.b.api.admin(cur)
        actual=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(source['sale'],)).fetchone()[0]
        for name in PHYSICAL:assert actual[name]==physical[name],('POSITIVE_CORRECTION_CHANGED_STOCK_HPP',name)
        assert correction.payment_fact(cur,source['payment'])==original_fact
        assert correction.payment_fact(cur,lowered['payment_id'])==lower_fact
        rows=native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(initial['credit_id'],))
        assert len(rows['document'])==len(consumers)
        before=basic.observation(cur,pair)
        assert basic.command(cur,envelope,consumer_request)==first
        assert correction.correct(cur,down,version_down,request_down)==lowered
        assert correction.correct(cur,up,version_up,request_up)==restored
        assert basic.observation(cur,pair)==before,'POSITIVE_CORRECTION_OLD_OR_CURRENT_REPLAY_CREATED_EFFECTS'
        changed=deepcopy(up);changed['replacement']['amount']='999.99'
        fixture.signed._refuse(cur,lambda:correction.correct(cur,changed,version_up,request_up),
            'P0001','CP7_SALES_REQUEST_CHANGED')
        fixture.signed._refuse(cur,lambda:correction.correct(cur,up,version_up,uuid.uuid4()),
            'P0001','CP7_SALES_REVIEW_CHANGED')
        assert basic.observation(cur,pair)==before,'POSITIVE_CHANGED_UUID_OR_STALE_REVIEW_CHANGED_FACTS'
        # Ordinary source inverse still refuses while a named C is active.
        p,v=fixture.signed._intent(cur,pair['source'],initial,'RETURN_REVERSE')
        fixture.signed._refuse(cur,lambda:native.cmd.command(cur,'RETURN_REVERSE',p,v,uuid.uuid4()),
            'P0001','CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO')
        assert basic.observation(cur,pair)==before
        for event in reversed(consumers):
            p=basic.payload(pair,'UNDO',original=event['consumption_event_id'])
            undo=basic.command(cur,basic.review(cur,p),uuid.uuid4())
            assert undo['restores_event_id']==event['consumption_event_id']
            assert Decimal(undo['amount'])==-Decimal(event['amount'])
        native.b.api.admin(cur)
        all_consumers=native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(initial['credit_id'],))
        assert len(all_consumers['document'])==2*len(consumers)
        return_journal=cur.execute("select id from erp.journal_entries where source_type='SALES_RETURN'and source_id=%s and reversal_of_id is null",(initial['return_id'],)).fetchone()[0]
        return_fact=native.journal(cur,return_journal)
        p,v=fixture.signed._intent(cur,pair['source'],initial,'RETURN_REVERSE')
        inverse=native.cmd.command(cur,'RETURN_REVERSE',p,v,uuid.uuid4());assert inverse['return_status']=='REVERSED'
        fixture.signed._assert_actual_inverse(cur,return_fact)
        assert observation(cur,pair)==declaration['final_after_actual_named_undos_and_return_inverse']
        native.b.api.admin(cur)
        assert native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(initial['credit_id'],))==all_consumers
        assert correction.payment_fact(cur,source['payment'])==original_fact
        assert correction.payment_fact(cur,lowered['payment_id'])==lower_fact
        for event_id,original in originals.items():
            journal=cur.execute('select journal_id from cp7_credit.consumption_events where id=%s',(event_id,)).fetchone()[0]
            assert native.journal(cur,journal)==original
        operations=cur.execute("select operation_id,action,before_financial_profile from cp7_credit.source_operation_materializations_v1 where sale_id=%s order by operation_ordinal",(source['sale'],)).fetchall()
        assert [r[1]for r in operations]==gold['source_operation_actions']
        assert [sum(o['object_kind']=='CONSUMPTION'for o in r[2]['actual_objects'])for r in operations]==gold['historical_consumer_counts']
        for operation,_,_ in operations:cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(operation,))
        before=basic.observation(cur,pair)
        assert correction.correct(cur,down,version_down,request_down)==lowered
        assert correction.correct(cur,up,version_up,request_up)==restored
        assert basic.observation(cur,pair)==before,'POSITIVE_CORRECTION_HISTORICAL_REPLAY_ADOPTED_LATER_STATE'
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        return dict(status='PASS',id=gold['id'],expected=declaration['final_after_actual_named_undos_and_return_inverse'],
            observed=observation(cur,pair),after_restore=gold['after_restore'],both_original_payments_and_consumers_retained=True,
            all_named_undos_and_actual_RETURN_REVERSE=True,full_source_operation_chain_closed=True,
            old_and_current_UUID_replays_zero_effect=True,one_cent_over_gross_zero_effect_refusal=True,
            changed_UUID_and_stale_review_zero_effect_refusal=True,late_last_link_failure=late_failure,
            new_cohort_policy_inferred=False,production_go=False)


def cases(cur,today,last_link_failure):
    return [(row['id'],lambda index=index:one_case(cur,today,index,last_link_failure))for index,row in enumerate(expected()['cases'])]
