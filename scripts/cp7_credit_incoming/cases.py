"""OW-04b slice C Native cases: a return on an invoice that was paid with customer credit.

Fixture: the retained OW04 consumer pair (source invoice 1000 paid, first return 200 settled as credit 200; target invoice
500 = 5 pcs x 100), then the retained consumer APPLY of 80 credit to the target. Every money document comes from the
retained writers (consumer, CP7 payment, CP7 return and settlement RPCs); masters (liability accounts) are disposable
fixtures. Changed paths are compared with the exact slice B definitions inside a rolled-back savepoint.
"""
from copy import deepcopy
from decimal import Decimal as D
from hashlib import sha256
import json
import uuid

import psycopg

import cp7_ow04_consumer_fixture as fixture
import native_basic_cases as basic
import cp7_ow04_initial_settlement_cases as initial
import cp7_sales_return_cases as returns
import cp7_sales_return_correction_cases as correction
from cp7_credit_followups import cases as followups
from cp7_credit_incoming import native_delta

native=fixture.native
signed=fixture.signed
payments=returns.payments
IDS=('OW04BC_FIRST_RETURN_QUOTES_UNCHANGED',
     'OW04BC_RETURN_ON_CREDIT_PAID_INVOICE_NO_CREDIT',
     'OW04BC_UNDO_ALLOWED_WHEN_RETURN_EMPTY',
     'OW04BC_RETURN_ON_CREDIT_PAID_INVOICE_CREDIT',
     'OW04BC_RETURN_ON_CREDIT_PAID_INVOICE_REFUND',
     'OW04BC_UNDO_REFUSED_WHEN_RETURN_DEPENDS',
     'OW04BC_PROTECTED_REFUSALS_IDENTICAL')
RACE_IDS=('OW04BC_RACE_RETURN_VS_UNDO_OF_ITS_CREDIT',)
INITIAL_FAMILY='CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED'
DEPENDS='CP7_CREDIT_CONSUMER_FAMILY_ADJUSTMENT_REVIEW_REQUIRED'
AFTER_APPLY=dict(gross='500.00',net='500.00',P='0.00',U='80.00',I='0.00',E='80.00',AR='420.00')
ORIGINALS=None  # set by the probe: the exact slice B definitions this stage replaced
AS_OWNER=None   # set by the probe: the verified predecessor role switch


def refusal(cur,operation):
    native.b.api.admin(cur);name='ow04bc_refusal_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        operation()
    except psycopg.Error as error:
        found=dict(sqlstate=error.sqlstate,message=error.diag.message_primary,detail=error.diag.message_detail or '')
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)
        return found
    cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)
    raise AssertionError('OW04BC_EXPECTED_REFUSAL_BUT_CALL_SUCCEEDED')


def original(cur,fn):
    name='ow04bc_original_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        with AS_OWNER(cur,'postgres'):
            for sig in native_delta.SIGNATURES:cur.execute(ORIGINALS[sig],prepare=False)
        native.b.api.admin(cur)
        return fn()
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)


def identical(cur,observe,operation):
    before=observe()
    new=refusal(cur,operation)
    assert observe()==before,'OW04BC_REFUSAL_CHANGED_STATE'
    old=original(cur,lambda:refusal(cur,operation))
    assert old==new,(old,new)
    return new


def was_refused(cur,observe,operation):
    before=observe()
    old=original(cur,lambda:refusal(cur,operation))
    assert observe()==before,'OW04BC_ORIGINAL_REFUSAL_CHANGED_STATE'
    return old


def setup(cur,today,pay_rest=False):
    """The consumer pair with 80 credit applied to the target; optionally the target's remaining 420 paid (slice A)."""
    pair=fixture.prepare(cur,today,'CREDIT')
    applied,_,_=basic.apply(cur,pair,'80.00')
    t=dict(pair['target'],bank=pair['source']['f']['bank']);native.b.api.admin(cur)
    t['allocations']=returns.read(cur,t)['page']['rows'];t['destination']=pair['source']['f']['destination']
    assert fixture.profiles(cur,pair)['target']==AFTER_APPLY
    if pay_rest:
        payments.pay(cur,t,'420.00');native.b.api.admin(cur)
        assert fixture.profiles(cur,pair)['target']==dict(AFTER_APPLY,P='420.00',E='500.00',AR='0.00')
    return pair,t,applied


def status(cur,sale):
    native.b.api.admin(cur)
    return cur.execute('select status from erp.sales_headers where id=%s',(sale,)).fetchone()[0]


def undo(cur,pair,applied):
    return basic.command(cur,basic.review(cur,basic.payload(pair,'UNDO',original=applied['consumption_event_id'])),uuid.uuid4())


def settle_on_target(cur,t,mode):
    """A return of 1 pcs (100) on the fully paid target through the retained quote and settle RPCs."""
    query=followups.draft_query(cur,t,'1','100.00')
    first=native.call_quote(cur,query)
    assert first['has_recognition_effect']is True and first['current_credit_amount']=='100.00',first
    assert first['readiness']['state']=='CHOICE_REQUIRED',first['readiness']
    totals=first['totals']
    assert (totals['before']['credit_applied'],totals['before']['effective_paid'],totals['after']['effective_paid'],
            totals['after']['receivable_remaining'])==('80.00','500.00','400.00','0.00'),totals
    credit=initial._credit_master(cur)
    query['settlement']=dict(mode=mode,credit_account_id=credit['id'],cash_account_id=t['bank']if mode=='REFUND'else None,
        refund_physical_at=query['return_payload']['physical_at']if mode=='REFUND'else None,
        reference='OW04b slice C refund'if mode=='REFUND'else None)
    quote=native.call_quote(cur,query)
    assert quote['readiness']==dict(state='READY',issues=[]),quote['readiness']
    envelope=initial._envelope(query,quote)
    result=initial._settle(cur,envelope,uuid.uuid4())
    assert (result['kind'],result['action'],result['return_status'],result['family_ordinal'])==(
        'COMMITTED_OUTCOME','RETURN_SETTLEMENT','POSTED','1'),result
    native.b.api.admin(cur)
    return dict(query=query,quote=quote,result=result,totals=totals)


def cases(cur,today):
    def first_quotes():
        compared={}
        for mode in('CREDIT','REFUND'):
            with native.isolated(cur):
                initial._require_installed(cur)
                gold=next(row for row in initial.expected()['cases']if row['id']=='OW04_INITIAL_1000_OPEN_'+mode)
                x=native.prepared(cur,today,'1000.00','OPEN');credit=initial._credit_master(cur)
                query=initial._input(x,gold,credit)
                new=native.call_quote(cur,query);initial._assert_quote(cur,new,query,x,gold,credit)
                old=original(cur,lambda:native.call_quote(cur,query))
                strip=lambda q:{key:value for key,value in q.items()if key!='captured_at'}
                assert strip(new)==strip(old),'OW04BC_FIRST_RETURN_QUOTE_CHANGED'
                compared[mode]=dict(quote_sha256=new['binding']['quote_sha256'],credit=new['current_credit_amount'])
        return dict(status='PASS',identical_first_return_quotes=compared)

    def ordinary_return(pair,t):
        old=was_refused(cur,lambda:basic.observation(cur,pair),lambda:returns.returned(cur,t,qty='1',refund='50.00'))
        assert (old['sqlstate'],old['message'])==('P0001',INITIAL_FAMILY),old
        returns.returned(cur,t,qty='1',refund='50.00');native.b.api.admin(cur)
        return old

    def no_credit():
        with native.isolated(cur):
            pair,t,_=setup(cur,today);before=fixture.profiles(cur,pair)
            old=ordinary_return(pair,t)
            after=fixture.profiles(cur,pair)
            assert after['target']==dict(AFTER_APPLY,net='450.00',AR='370.00'),after
            assert status(cur,t['sale'])=='PARTIAL_PAID'and after['source']==before['source'],after
            native.b.api.admin(cur)
            assert cur.execute('select count(*)from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=%s',
                               (t['sale'],)).fetchone()[0]==0
            return dict(status='PASS',predecessor_refusal=old['message'],target=after['target'],status_after='PARTIAL_PAID',no_cohort=True)

    def undo_allowed():
        with native.isolated(cur):
            pair,t,applied=setup(cur,today)
            ordinary_return(pair,t)
            done=undo(cur,pair,applied)
            assert done['amount']=='-80.00',done
            after=fixture.profiles(cur,pair)
            assert after['target']==dict(AFTER_APPLY,net='450.00',U='0.00',E='0.00',AR='450.00'),after
            assert after['source']==fixture.INITIAL['source'],after
            assert status(cur,t['sale'])=='POSTED'
            return dict(status='PASS',undo=done['operation_id'],target=after['target'],source_credit_restored=True)

    def with_credit(mode):
        def run():
            with native.isolated(cur):
                pair,t,_=setup(cur,today,pay_rest=True);before=fixture.profiles(cur,pair)
                query=followups.draft_query(cur,t,'1','100.00')
                old=was_refused(cur,lambda:basic.observation(cur,pair),lambda:native.call_quote(cur,query))
                assert (old['sqlstate'],old['message'])==('P0001',INITIAL_FAMILY),old
                assert json.loads(old['detail'])['reasons']==['CREDIT_APPLIED_TO_INVOICE'],old
                done=settle_on_target(cur,t,mode)
                after=fixture.profiles(cur,pair)
                assert {k:after['target'][k]for k in('gross','net','P','U','I','E','AR')}==dict(
                    gross='500.00',net='400.00',P='420.00',U='80.00',I='100.00',E='400.00',AR='0.00'),after
                assert status(cur,t['sale'])=='PAID'and after['source']==before['source'],after
                if mode=='REFUND':
                    assert D(after['cash'])==D(before['cash'])-D('100.00'),(before['cash'],after['cash'])
                else:
                    assert after['cash']==before['cash']
                return dict(status='PASS',predecessor_refusal=old['message'],mode=mode,credit_id=done['result']['credit_id'],
                    quote_totals=done['totals'],target=after['target'],status_after='PAID')
        return run

    def undo_refused():
        with native.isolated(cur):
            pair,t,applied=setup(cur,today,pay_rest=True)
            settle_on_target(cur,t,'CREDIT')
            state=basic.observation(cur,pair)
            found=refusal(cur,lambda:undo(cur,pair,applied))
            assert (found['sqlstate'],found['message'])==('P0001',DEPENDS),found
            assert basic.observation(cur,pair)==state,'OW04BC_REFUSED_UNDO_LEFT_AN_EFFECT'
            return dict(status='PASS',refused=found['message'],state_unchanged=True)

    def protected():
        with native.isolated(cur):
            pair,t,_=setup(cur,today)
            observe=lambda:basic.observation(cur,pair);seen={}
            f=dict(pair['source']['f'])
            p,v=correction.payload(cur,f,qty='1',refund='150.00',return_id=pair['initial_result']['return_id'])
            seen['edit_retur_on_credit_source']=identical(cur,observe,lambda:correction.correct(cur,p,v))
            n,m=native.note.edit(cur,pair['target'],price='110')
            seen['benerin_nota_on_credit_paid_target']=identical(cur,observe,lambda:native.note.correct(cur,n,m))
            # Ordinary return without a settlement choice on the paid credit source (U = 0): the P11 path is identical.
            seen['ordinary_return_on_paid_source']=identical(cur,observe,lambda:returns.returned(cur,pair['source']['f'],qty='1',refund='100.00'))
            for name,value in seen.items():
                assert value['sqlstate']=='P0001',(name,value)
            return dict(status='PASS',**seen)

    result=list(zip(IDS,(first_quotes,no_credit,undo_allowed,with_credit('CREDIT'),with_credit('REFUND'),undo_refused,protected)))
    assert tuple(key for key,_ in result)==IDS
    return result


def race(tools,today):
    """Two real sessions: a credit return on the target, and the undo of the credit it is built on (reviewed first)."""
    with tools.connect()as conn,conn.cursor()as cur:
        pair,t,applied=setup(cur,today,pay_rest=True)
        envelope_undo=basic.review(cur,basic.payload(pair,'UNDO',original=applied['consumption_event_id']))
        query=followups.draft_query(cur,t,'1','100.00')
        credit=initial._credit_master(cur)
        query['settlement']=dict(mode='CREDIT',credit_account_id=credit['id'],cash_account_id=None,refund_physical_at=None,reference=None)
        quote=native.call_quote(cur,query)
        assert quote['readiness']==dict(state='READY',issues=[]),quote['readiness']
        envelope_return=initial._envelope(query,quote)
        cur.execute('set constraints all immediate');conn.commit()
    first,second=uuid.uuid4(),uuid.uuid4()
    def holder(cur):
        cur.execute("set local timezone='UTC';set local lock_timeout='20s';set local statement_timeout='60s'")
        result=initial._settle(cur,deepcopy(envelope_return),first)
        return dict(result=result,complete=basic.observation(cur,pair),pid=cur.execute('select pg_backend_pid()').fetchone()[0])
    def worker(cur):
        cur.execute("set local timezone='UTC';set local lock_timeout='20s';set local statement_timeout='60s'")
        return basic.command(cur,deepcopy(envelope_undo),second)
    held,contention,outcome=tools.two_sessions(holder,worker,True)
    assert contention==dict(kind='BLOCKED',holder_blocks_worker=True),contention
    # Read from the consumer path: after the holder's return the worker's projection rebuilds the target's ordinal input
    # without the 80 and finds the new return's credit would change, before the stale-review comparison and any write.
    assert outcome==dict(ok=False,sqlstate='P0001',message=DEPENDS),outcome
    with tools.connect()as conn,conn.cursor()as cur:
        native.b.api.admin(cur)
        after=basic.observation(cur,pair)
        assert after==held['complete'],'OW04BC_RACE_WORKER_CHANGED_BUSINESS_OR_PRIVATE_FACTS'
        undos=cur.execute('select count(*)from cp7_credit.consumption_events where restores_event_id=%s',(applied['consumption_event_id'],)).fetchone()[0]
        cohorts=cur.execute('select count(*)from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=%s',
                            (t['sale'],)).fetchone()[0]
        worker_rows=cur.execute('select count(*)from cp7_credit.consumer_requests_v1 where request_id=%s',(second,)).fetchone()[0]
        assert (undos,cohorts,worker_rows)==(0,1,0),(undos,cohorts,worker_rows)
        target=fixture.profiles(cur,pair)['target']
        assert (target['I'],target['U'],target['E'])==('100.00','80.00','400.00'),target
        conn.rollback()
    return dict(status='PASS',two_actual_SQL_sessions=True,authenticated_SQL_fixture_not_real_Auth=True,
        actual_holder_blocks_worker=True,holder_committed=True,actual_worker=outcome,holder_outcome=held['result'],
        undo_events=undos,target_cohorts=cohorts,worker_request_rows=worker_rows,target_after=target,holder_backend_pid=held['pid'],
        final_state_sha256=sha256(json.dumps(after,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest(),
        production_go=False)


def races(tools,today):
    planned=[(RACE_IDS[0],lambda:race(tools,today))]
    assert tuple(key for key,_ in planned)==RACE_IDS
    return planned
