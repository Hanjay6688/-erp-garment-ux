"""Literal cash REFUND/UNDO expectations on actual owning Native paths.

Declarations/imports perform no SQL or connections. Only the strict disposable
Native harness calls each isolated case; a declaration is not a passing case.
The original frozen arithmetic9 remain unchanged and not fully qualified.
"""
from hashlib import sha256
from pathlib import Path
import json
import uuid

import native_basic_cases as basic

fixture,native=basic.fixture,basic.native
EXPECTED=fixture.EXPECTED.with_name('PREDECLARED_REFUND_ARITHMETIC.json')
EXPECTED_SHA256='eed6e700cfabc301f76a74819fc5b614b6b20da16af6d8f97f05ee9d10d7b762'


def expected():
    raw=EXPECTED.read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA256,'OW04_CONSUMER_FROZEN_REFUND_ARITHMETIC_CHANGED'
    value=json.loads(raw)
    assert value['classification']=='PREIMPLEMENTATION_LITERAL_REFUND_EXPECTATIONS_NOT_NATIVE_OR_INDEPENDENT_ACCEPTANCE'
    assert value['frozen_original_nine_sha256']==fixture.EXPECTED_SHA256
    assert value['expected_numeric_case_count']==len(value['cases'])==9
    return value


GOLD=expected()
IDS=tuple(row['id']for row in GOLD['cases'])


def refund(cur,pair,amount):
    p=basic.payload(pair,'REFUND',amount)
    p['cash_account_id']=str(pair['source']['f']['bank'])
    envelope=basic.review(cur,p);request=uuid.uuid4()
    return basic.command(cur,envelope,request),envelope,request


def one_case(cur,today,index):
    with native.isolated(cur):
        pair=fixture.prepare(cur,today,'REFUND'if index>=7 else'CREDIT');gold=GOLD['cases'][index]
        if index<7:
            first,envelope,request=refund(cur,pair,'80.00')
            original_id=first['consumption_event_id'];journal_id=first['journal_id']
        else:
            original_id=pair['initial_result']['refund_event_id']
            native.b.api.admin(cur)
            journal_id=cur.execute('select journal_id from cp7_credit.consumption_events where id=%s',(original_id,)).fetchone()[0]
        original_journal=native.journal(cur,journal_id)
        if index in(1,2,3,5,6):refund(cur,pair,'120.00')
        if index==2:
            over={**envelope,'payload':{**envelope['payload'],'amount':'0.01'}}
            basic.refused_unchanged(cur,pair,over,uuid.uuid4(),'INSUFFICIENT_DATED_SOURCE_CAPACITY')
        if index in(3,5,6,7,8):
            undo_envelope=basic.review(cur,basic.payload(pair,'UNDO',original=original_id))
            undo_request=uuid.uuid4();undone=basic.command(cur,undo_envelope,undo_request)
            assert undone['amount']==('-200.00'if index>=7 else'-80.00')
            assert undone['restores_event_id']==str(original_id)
            if index==5:
                before=basic.observation(cur,pair)
                assert basic.command(cur,undo_envelope,undo_request)==undone
                assert basic.observation(cur,pair)==before,'REFUND_UNDO_REPLAY_CREATED_ANOTHER_CASH_EFFECT'
            if index==6:
                basic.refused_unchanged(cur,pair,undo_envelope,uuid.uuid4(),'ORIGINAL_ALREADY_UNDONE')
        if index==4:
            before=basic.observation(cur,pair)
            assert basic.command(cur,envelope,request)==first
            assert basic.observation(cur,pair)==before,'REFUND_REPLAY_CREATED_ANOTHER_CASH_EFFECT'
        if index==8:
            native.b.api.admin(cur)
            cohort=pair['initial_result']['credit_id']
            history=native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(cohort,))
            assert len(history['document'])==2
            journals={str(e['journal_id']):native.journal(cur,e['journal_id'])for e in history['document']}
            old_return_id=cur.execute("select id from erp.journal_entries where source_type='SALES_RETURN'and source_id=%s and reversal_of_id is null",
                                      (pair['initial_result']['return_id'],)).fetchone()[0]
            old_return=native.journal(cur,old_return_id)
            p,v=fixture.signed._intent(cur,pair['source'],pair['initial_result'],'RETURN_REVERSE')
            result=native.cmd.command(cur,'RETURN_REVERSE',p,v,uuid.uuid4())
            assert result['return_status']=='REVERSED'
            fixture.signed._assert_actual_inverse(cur,old_return)
            assert native._array(cur,'cp7_credit.consumption_events','cohort_id=%s',(cohort,))==history
            for ident,old in journals.items():assert native.journal(cur,ident)==old,'SOURCE_INVERSE_CHANGED_REFUND_OR_UNDO_JOURNAL'
        observed=fixture.profiles(cur,pair)
        assert observed==gold['expected'],(gold['id'],observed,gold['expected'])
        native.b.api.admin(cur)
        assert native.journal(cur,journal_id)==original_journal,'REFUND_UNDO_OR_SOURCE_INVERSE_CHANGED_ORIGINAL_CASH_JOURNAL'
        assert native.payment_snapshot(cur,pair['source']['f']['payment'])==pair['source']['payment_before']
        assert cur.execute('select count(*)from erp.sales_payments where sale_id=%s',(pair['target']['sale'],)).fetchone()[0]==0
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        return dict(status='PASS',id=gold['id'],expected=gold['expected'],observed=observed,
            actual_cash_native_writes=True,original_refund_journal_retained=True,
            Native_payment_fact_retained=True,full_consumer_feature_complete=False,production_go=False)


def cases(cur,today):
    return [(name,lambda index=index:one_case(cur,today,index))for index,name in enumerate(IDS)]
