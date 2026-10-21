"""First seven frozen consumer arithmetic cases on actual Native writers.

These are a bounded subset. Source inverse/history-restatement cases8/9,
general families/corrections/HPP, real Auth/HTTP, browser and races remain open.
Importing performs no connection, fixture setup, installation or commit.
"""
from datetime import datetime,timedelta
from pathlib import Path
import json
import uuid

import cp7_ow04_consumer_fixture as fixture

native=fixture.native
GOLD=fixture.expected()
IDS=tuple(row['id']for row in GOLD['cases'][:7])
assert len(IDS)==7


def payload(pair,action='APPLY',amount='80.00',original=None):
    physical=(datetime.fromisoformat(pair['source']['physical']['returned'])+timedelta(minutes=5)).isoformat()
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


def cases(cur,today):
    return [(name,lambda index=index:one_case(cur,today,index))for index,name in enumerate(IDS)]
