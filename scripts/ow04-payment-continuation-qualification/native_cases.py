"""Frozen Native interoperability journeys; registration executes no SQL.

Uses actual existing owning Native writers. The matching literal expectations
were frozen before any continuation fix. Imports and factory creation do no SQL.
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
EXPECTED=Path(__file__).with_name('EXPECTED_INTEROP2.json')
EXPECTED_SHA256='6fc87d306ebce7240be5beacbc97ebebea9bb93fa15af7971c9775b53f290713'


def expected():
    raw=EXPECTED.read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA256
    return json.loads(raw)


def projected_observation(cur,pair):
    actual=fixture.profiles(cur,pair)
    return dict(source_net=actual['source']['net'],source_P=actual['source']['P'],I=actual['source']['I'],
        C=actual['source']['net_consumption'],available=actual['source']['available_credit'],source_AR=actual['source']['AR'],
        target_P=actual['target']['P'],target_U=actual['target']['U'],target_AR=actual['target']['AR'],cash=actual['cash'])


def one_case(cur,today,index):
    with native.isolated(cur):
        declaration=expected();gold=declaration['cases'][index]
        pair=fixture.prepare(cur,today)
        use=basic.apply if gold['initial_action']=='APPLY'else refund.refund
        first,first_envelope,first_request=use(cur,pair,'80.00')
        source=pair['source']['f'];initial=pair['initial_result']
        original_payment_fact=correction.payment_fact(cur,source['payment'])
        first_journal=native.journal(cur,first['journal_id'])
        intent,version=correction.payload(cur,source,amount='900.00')
        request=uuid.uuid4();corrected=correction.correct(cur,intent,version,request)
        actual=projected_observation(cur,pair)
        assert {k:actual[k]for k in gold['after_correct']}==gold['after_correct']
        before=basic.observation(cur,pair)
        assert basic.command(cur,first_envelope,first_request)==first
        assert basic.observation(cur,pair)==before,'OLD_CONSUMER_REPLAY_AFTER_SOURCE_CORRECTION_CHANGED_FACTS'
        # Actual active consumers still block an ordinary return inverse.
        p,v=fixture.signed._intent(cur,pair['source'],initial,'RETURN_REVERSE')
        fixture.signed._refuse(cur,lambda:native.cmd.command(cur,'RETURN_REVERSE',p,v,uuid.uuid4()),
            'P0001','CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO')
        assert basic.observation(cur,pair)==before
        second,_,_=use(cur,pair,'20.00')
        actual=projected_observation(cur,pair)
        assert {k:actual[k]for k in gold['after_spend20']}==gold['after_spend20']
        # Actual captured headers, not a blanket ignore of version/timestamp.
        native.b.api.admin(cur)
        h=cur.execute('select before_header,after_header from cp7_credit.payment_consumer_headers_v1 where operation_id=%s',
            (second['operation_id'],)).fetchone()
        assert h is not None
        snapshot=cur.execute('select cp7_credit.source_document_snapshot_v1(%s)',(source['sale'],)).fetchone()[0]
        previous=deepcopy(snapshot);previous['sale']=h[0]
        def follows(before,after):
            return cur.execute('select cp7_credit.payment_consumer_source_continues_v1(%s,%s::jsonb,%s::jsonb)',
                (source['sale'],json.dumps(before),json.dumps(after))).fetchone()[0]
        assert follows(previous,snapshot)
        controls={}
        for key,value in [('row_version',int(h[1]['row_version'])+1),('updated_at','2000-01-01T00:00:00+00:00'),
                          ('status','POSTED'),('notes','unowned header mutation')]:
            changed=deepcopy(snapshot);changed['sale'][key]=value
            controls[key]=not follows(previous,changed)
        changed=deepcopy(snapshot);changed['payments'][0]['amount']='899.99'
        controls['native_payment_amount']=not follows(previous,changed)
        assert all(controls.values()),controls
        native.b.api.ordinary(cur)

        originals={first['consumption_event_id']:first_journal,
                   second['consumption_event_id']:native.journal(cur,second['journal_id'])}
        for event in(second,first):
            payload=basic.payload(pair,'UNDO',original=event['consumption_event_id'])
            undone=basic.command(cur,basic.review(cur,payload),uuid.uuid4())
            assert undone['restores_event_id']==event['consumption_event_id']
            assert Decimal(undone['amount'])==-Decimal(event['amount'])
        assert projected_observation(cur,pair)==declaration['after_both_named_full_undos']
        native.b.api.admin(cur)
        rows=native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(initial['credit_id'],))
        assert len(rows['document'])==4
        original_return_journal=cur.execute("select id from erp.journal_entries where source_type='SALES_RETURN'and source_id=%s and reversal_of_id is null",(initial['return_id'],)).fetchone()[0]
        original_return=native.journal(cur,original_return_journal)
        p,v=fixture.signed._intent(cur,pair['source'],initial,'RETURN_REVERSE')
        reversed_result=native.cmd.command(cur,'RETURN_REVERSE',p,v,uuid.uuid4())
        assert reversed_result['return_status']=='REVERSED'
        fixture.signed._assert_actual_inverse(cur,original_return)
        assert projected_observation(cur,pair)==declaration['final_after_actual_RETURN_REVERSE']
        native.b.api.admin(cur)
        assert native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(initial['credit_id'],))==rows
        for event_id,original in originals.items():
            journal=cur.execute('select journal_id from cp7_credit.consumption_events where id=%s',(event_id,)).fetchone()[0]
            assert native.journal(cur,journal)==original
        assert correction.payment_fact(cur,source['payment'])==original_payment_fact
        operations=cur.execute("select operation_id,action,before_financial_profile from cp7_credit.source_operation_materializations_v1 where sale_id=%s order by operation_ordinal",(source['sale'],)).fetchall()
        assert [row[1]for row in operations]==['PAYMENT_CORRECT','RETURN_REVERSE']
        assert [sum(x['object_kind']=='CONSUMPTION'for x in row[2]['actual_objects'])for row in operations]==[1,4]
        for operation,_,_ in operations:cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(operation,))
        before=basic.observation(cur,pair)
        assert correction.correct(cur,intent,version,request)==corrected
        assert basic.observation(cur,pair)==before,'OLD_CORRECTION_REPLAY_ADOPTED_LATER_SOURCE_STATE'
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        return dict(status='PASS',id=gold['id'],current_source_after_later_legal_consumers_and_source_inverse=True,
            historical_first_operation_consumers=1,historical_later_inverse_consumers=4,
            own_old_receipts_replay_without_effects=True,unowned_header_or_payment_mutations_refused=controls,expected=declaration['final_after_actual_RETURN_REVERSE'],
            observed=projected_observation(cur,pair),production_go=False)


def cases(cur,today):
    return [(gold['id'],lambda index=index:one_case(cur,today,index))for index,gold in enumerate(expected()['cases'])]
