"""Frozen consumer arithmetic cases on actual Native writer entry points.

These are a bounded subset. Case9 is an actual bound unsafe-correction refusal
preflight, not a successful general correction adapter. General families/
corrections/HPP, real Auth/HTTP, browser and races remain open.
Importing performs no connection, fixture setup, installation or commit.
"""
from datetime import datetime,timedelta
from pathlib import Path
import json
import uuid

import cp7_ow04_consumer_fixture as fixture

native=fixture.native
GOLD=fixture.expected()
IDS=tuple(row['id']for row in GOLD['cases'])
assert len(IDS)==9


def payload(pair,action='APPLY',amount='80.00',original=None):
    physical=(datetime.fromisoformat(pair['source']['physical']['returned'])+timedelta(minutes=5)).isoformat()
    if action=='UNDO'and original is not None and str(original)==str(pair['initial_result'].get('refund_event_id')):
        physical=(datetime.fromisoformat(pair['initial_refund_physical_at'])+timedelta(minutes=5)).isoformat()
    return dict(action=action,cohort_id=pair['initial_result']['credit_id']if action!='UNDO'else None,
        target_sale_id=str(pair['target']['sale'])if action=='APPLY'else None,cash_account_id=None,
        restores_event_id=str(original)if original is not None else None,amount=amount if action!='UNDO'else None,
        physical_at=physical,reason='Pemakaian kredit pelanggan sesuai tinjauan',reference=None)


def review(cur,p):
    native.auth.actor(cur)
    q=cur.execute('select public.erp_cp7_get_customer_credit_review_v1(%s::jsonb)',(json.dumps(p),)).fetchone()[0]
    native.b.api.admin(cur)
    assert q['contract_version']=='cp7.customer-credit-review.v1'and q['read_only']is True
    assert isinstance(q['quote_sha256'],str)and len(q['quote_sha256'])==64
    return dict(payload={**p,'quote_sha256':q['quote_sha256']},versions=q['expected_versions'])


def command(cur,envelope,request):
    native.auth.actor(cur)
    result=cur.execute('select public.erp_cp7_customer_credit_command_v1(%s::jsonb,%s::uuid,%s::jsonb)',
        (json.dumps(envelope['payload']),request,json.dumps(envelope['versions']))).fetchone()[0]
    native.b.api.admin(cur)
    assert result['kind']=='COMMITTED_OUTCOME'and result['request_id']==str(request)
    cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
    return result


def apply(cur,pair,amount):
    envelope=review(cur,payload(pair,amount=amount));request=uuid.uuid4()
    return command(cur,envelope,request),envelope,request


def observation(cur,pair):
    # Complete Native boundary + every actual private table, journals, daily,
    # audit and source payment state. Native helper preserves raw JSON bytes.
    return fixture.signed._observe(cur,pair['source'])


def refused_unchanged(cur,pair,envelope,request,expected_error):
    before=observation(cur,pair)
    cur.execute('savepoint consumer_expected_refusal')
    try:
        command(cur,envelope,request)
    except Exception as error:
        message=str(error)
        cur.execute('rollback to savepoint consumer_expected_refusal')
        native.b.api.admin(cur)
        assert expected_error in message,(expected_error,message)
    else:
        raise AssertionError('OW04_CONSUMER_EXPECTED_ATOMIC_REFUSAL')
    finally:
        cur.execute('release savepoint consumer_expected_refusal')
    assert observation(cur,pair)==before,'OW04_CONSUMER_REFUSAL_CHANGED_REAL_NATIVE_OR_PRIVATE_STATE'


def one_case(cur,today,index):
    with native.isolated(cur):
        pair=fixture.prepare(cur,today)
        row=GOLD['cases'][index]
        first,envelope,request=apply(cur,pair,'80.00')
        original=native.journal(cur,first['journal_id'])
        if index in(1,2,3,5,6):
            second,_,_=apply(cur,pair,'120.00')
            assert second['operation_id']!=first['operation_id']
        if index==2:
            # Exact frozen one cent overdraw, using a real earlier envelope as
            # an attempted stale save. No fabricated successful quote is used.
            over={**envelope,'payload':{**envelope['payload'],'amount':'0.01'}}
            refused_unchanged(cur,pair,over,uuid.uuid4(),'INSUFFICIENT_DATED_SOURCE_CAPACITY')
        if index in(3,5,6):
            undo_envelope=review(cur,payload(pair,'UNDO',original=first['consumption_event_id']))
            undo_request=uuid.uuid4();undone=command(cur,undo_envelope,undo_request)
            assert undone['amount']=='-80.00'and undone['restores_event_id']==first['consumption_event_id']
            if index==5:
                before=observation(cur,pair)
                assert command(cur,undo_envelope,undo_request)==undone
                assert observation(cur,pair)==before,'UNDO_REPLAY_CREATED_ANOTHER_EFFECT'
            if index==6:
                refused_unchanged(cur,pair,undo_envelope,uuid.uuid4(),'ORIGINAL_ALREADY_UNDONE')
        if index==4:
            before=observation(cur,pair)
            assert command(cur,envelope,request)==first
            assert observation(cur,pair)==before,'APPLY_REPLAY_CREATED_ANOTHER_EFFECT'
        assert fixture.profiles(cur,pair)==row['expected'],(row['id'],fixture.profiles(cur,pair),row['expected'])
        native.b.api.admin(cur)
        assert native.journal(cur,first['journal_id'])==original,'NAMED_UNDO_MUTATED_ORIGINAL_CONSUMPTION_JOURNAL'
        assert native.payment_snapshot(cur,pair['source']['f']['payment'])==pair['source']['payment_before']
        assert cur.execute('select count(*)from erp.sales_payments where sale_id=%s',(pair['target']['sale'],)).fetchone()[0]==0
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        return dict(status='PASS',id=row['id'],expected=row['expected'],observed=fixture.profiles(cur,pair),
            original_journal_retained=True,Native_payment_fact_retained=True,
            full_consumer_feature_complete=False,production_go=False)


def source_inverse_after_all_undone(cur,today):
    with native.isolated(cur):
        pair=fixture.prepare(cur,today);gold=GOLD['cases'][7]
        first,_,_=apply(cur,pair,'80.00');second,_,_=apply(cur,pair,'120.00')
        p,v=fixture.signed._intent(cur,pair['source'],pair['initial_result'],'RETURN_REVERSE')
        before=observation(cur,pair)
        fixture.signed._refuse(cur,lambda:native.cmd.command(cur,'RETURN_REVERSE',p,v,uuid.uuid4()),
                              'P0001','CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO')
        assert observation(cur,pair)==before,'ACTIVE_CONSUMER_SOURCE_REFUSAL_CHANGED_STATE'
        for original in (first,second):
            e=review(cur,payload(pair,'UNDO',original=original['consumption_event_id']))
            command(cur,e,uuid.uuid4())
        native.b.api.admin(cur)
        cohort=pair['initial_result']['credit_id']
        history=native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(cohort,))
        assert len(history['document'])==4
        journals={str(e['journal_id']):native.journal(cur,e['journal_id'])for e in history['document']}
        original_return_id=pair['initial_result']['return_id']
        old_return=cur.execute("select id from erp.journal_entries where source_type='SALES_RETURN'and source_id=%s and reversal_of_id is null",
                               (original_return_id,)).fetchone()[0]
        original_return=native.journal(cur,old_return)
        p,v=fixture.signed._intent(cur,pair['source'],pair['initial_result'],'RETURN_REVERSE');request=uuid.uuid4()
        result=native.cmd.command(cur,'RETURN_REVERSE',p,v,request)
        fixture.signed._assert_request(cur,'RETURN_REVERSE',p,v,request,result)
        assert result['return_status']=='REVERSED'
        inverse=fixture.signed._assert_actual_inverse(cur,original_return)
        observed=fixture.profiles(cur,pair)
        assert observed==gold['expected'],(gold['id'],observed,gold['expected'])
        assert native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(cohort,))==history
        for ident,old in journals.items():assert native.journal(cur,ident)==old,'SOURCE_INVERSE_CHANGED_CONSUMER_JOURNAL'
        assert native.payment_snapshot(cur,pair['source']['f']['payment'])==pair['source']['payment_before']
        plans=cur.execute("select plan_kind,net_amount from cp7_credit.recognition_plans where cohort_id=%s order by plan_kind",(cohort,)).fetchall()
        from decimal import Decimal
        assert plans==[('ADJUSTMENT',Decimal('-200.00')),('INITIAL',Decimal('200.00'))],plans
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        before=observation(cur,pair)
        assert native.cmd.command(cur,'RETURN_REVERSE',p,v,request)==result
        assert observation(cur,pair)==before,'SOURCE_INVERSE_REPLAY_CREATED_ANOTHER_EFFECT'
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        return dict(status='PASS',id=gold['id'],expected=gold['expected'],observed=observed,
            signed_consumption_history_retained=True,actual_Native_inverse=inverse,
            exact_named_undo_required=True,original_consumer_journals_retained=True,
            recognition=gold['recognition'],same_source_request_replay_one_effect=True,
            full_consumer_feature_complete=False,production_go=False)


def cases(cur,today):
    return [(name,lambda index=index:one_case(cur,today,index))for index,name in enumerate(IDS[:7])]+[
        (IDS[7],lambda:source_inverse_after_all_undone(cur,today)),
        (IDS[8],lambda:historical_restatement_refuses(cur,today))]


def historical_restatement_refuses(cur,today):
    from decimal import Decimal
    import cp7_payment_correction_cases as correction
    with native.isolated(cur):
        pair=fixture.prepare(cur,today);gold=GOLD['cases'][8]
        applied,_,_=apply(cur,pair,'200.00')
        p=payload(pair,'UNDO',original=applied['consumption_event_id'])
        p['physical_at']=pair['source']['dates']['D3']+'T00:00:00.123456+07:00'
        command(cur,review(cur,p),uuid.uuid4())
        native.b.api.admin(cur)
        cohort=pair['initial_result']['credit_id'];d2=pair['source']['dates']['D2'];d3=pair['source']['dates']['D3']
        events=cur.execute('select id,amount,economic_date::text,transaction_date::text,source_sha256 from cp7_credit.consumption_events where cohort_id=%s order by amount',
                           (cohort,)).fetchall()
        assert [(r[1],r[2],r[3])for r in events]==[(Decimal('-200.00'),d3,d3),(Decimal('200.00'),d2,d2)]
        assert fixture.profiles(cur,pair)==fixture.INITIAL
        intent,version=correction.payload(cur,pair['source']['f'],amount='800.00');request=uuid.uuid4()
        def snapshot():
            state=observation(cur,pair)
            state['actual_correction_private']={name:native._array(cur,'cp7_payment_correction.'+name,'true',())
                                                for name in('requests','context','links')}
            return state
        before=snapshot()
        refusal=fixture.signed._refuse(cur,lambda:correction.correct(cur,intent,version,request),
            'P0001','CP7_CREDIT_RESTATEMENT_HISTORICAL_CAPACITY_NEGATIVE')
        assert snapshot()==before,'HISTORICAL_RESTATEMENT_REFUSAL_CHANGED_NATIVE_PRIVATE_OR_CASH_FACTS'
        detail=json.loads(refusal['detail'],parse_float=Decimal)
        assert detail['actual_pending_native_correction']is True and detail['request_id']==str(request)
        assert detail['original_amount']=='1000.00'and detail['replacement_amount']=='800.00'
        family=detail['family'];capacity=family['target_full_prefix_capacity']
        assert capacity['source_prefixes_nonnegative']is False and Decimal(capacity['minimum_available'])==Decimal('-200.00')
        assert dict(economic_date=d2,transaction_date=d2)in capacity['limiting_pairs']
        actual_c=detail['actual_signed_consumptions']
        assert sorted((e['id'],Decimal(e['amount']),e['economic_date'],e['transaction_date'],e['source_sha256'])for e in actual_c)==sorted(
            ('consumption:'+str(e[0]),e[1],e[2],e[3],e[4])for e in events)
        i_at_d2=sum((Decimal(e['amount'])for e in family['source_target']['components']if e['economic_date']<=d2 and e['transaction_date']<=d2),Decimal(0))
        c_at_d2=sum((Decimal(e['amount'])for e in actual_c if e['economic_date']<=d2 and e['transaction_date']<=d2),Decimal(0))
        observed=dict(recognition=format(i_at_d2,'.2f'),consumption=format(c_at_d2,'.2f'),balance=format(i_at_d2-c_at_d2,'.2f'))
        assert observed==gold['expected_at_joint_D2']
        assert sum((Decimal(e['amount'])for e in actual_c),Decimal(0))==0
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        return dict(status='PASS',id=gold['id'],expected_at_joint_D2=gold['expected_at_joint_D2'],observed_at_joint_D2=observed,
            actual_pending_Native_payment_correction_refused=True,complete_refusal=refusal,
            net_consumption_zero_does_not_remove_history=True,full_boundary_unchanged_on_refusal=True,
            successful_correction_adapter_qualified=False,full_consumer_feature_complete=False,production_go=False)
