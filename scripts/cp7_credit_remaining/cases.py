"""OW-04b slice A Native cases: pay the remaining balance of an invoice that received customer credit.

Fixture: the retained OW04 consumer pair (source invoice 1000 paid, return 200 -> credit 200; target invoice 500 unpaid),
then the retained consumer APPLY of 80 credit to the target. Every money document comes from the retained OW04/CP7
writers. Admitted payments are compared with the exact followups definitions (side by side, inside a rolled-back
savepoint), which refuse them; refusals that remain are identical in SQLSTATE, message and detail under both.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal as D
from hashlib import sha256
import json
import uuid

import psycopg

import cp7_ow04_consumer_fixture as fixture
import native_basic_cases as basic
import cp7_sales_return_cases as returns
from cp7_credit_remaining import native_delta

native=fixture.native
payments=returns.payments
cmd=payments.cmd
IDS=('OW04BA_PAY_REMAINING_IN_TWO_PARTS_PAID',
     'OW04BA_ONE_CENT_OVER_REFUSED_NO_EFFECT_THEN_EXACT_PAID',
     'OW04BA_REVERSE_REMAINING_PAYMENT_KEEPS_CREDIT',
     'OW04BA_UNDO_CREDIT_AFTER_REMAINING_PAID',
     'OW04BA_BACKDATED_PAYMENT_OVERFUNDING_A_DATE_PAIR_REFUSED',
     'OW04BA_PROTECTED_REFUSALS_IDENTICAL')
RACE_IDS=('OW04BA_RACE_TWO_PAYMENTS_SAME_REVIEW_DISTINCT_UUID',
          'OW04BA_RACE_TWO_PAYMENTS_SAME_UUID')
REGISTERED='CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION'
CONTRACT='cp7.credit-followups.refusal.v1'
AFTER_APPLY=dict(gross='500.00',net='500.00',P='0.00',U='80.00',I='0.00',E='80.00',AR='420.00')
OVERFUNDING={('22023','BASE_OVERFLOW_NONZERO'),('P0001','CP7_CREDIT_HISTORICAL_BASE_OVERFUNDING')}
ORIGINALS=None  # set by the probe: the exact followups definitions this stage replaced
AS_OWNER=None   # set by the probe: the verified predecessor role switch


def detail(action,reasons):
    return dict(contract=CONTRACT,refusal='REGISTERED_SOURCE_MUTATION',action=action,reasons=list(reasons),source_blockers=[])


def refusal(cur,operation):
    """The refusal of one call, rolled back; a call that succeeds fails the case."""
    native.b.api.admin(cur);name='ow04ba_refusal_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        operation()
    except psycopg.Error as error:
        found=dict(sqlstate=error.sqlstate,message=error.diag.message_primary,detail=error.diag.message_detail or '')
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)
        return found
    cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)
    raise AssertionError('OW04BA_EXPECTED_REFUSAL_BUT_CALL_SUCCEEDED')


def original(cur,fn):
    """The same call through the exact replaced followups definitions, then restored."""
    name='ow04ba_original_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        with AS_OWNER(cur,'postgres'):
            for sig in native_delta.SIGNATURES:cur.execute(ORIGINALS[sig],prepare=False)
        native.b.api.admin(cur)
        return fn()
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)


def identical(cur,observe,operation):
    """A refusal that must not change: same SQLSTATE, message and detail under both definitions, no state change."""
    before=observe()
    new=refusal(cur,operation)
    assert observe()==before,'OW04BA_REFUSAL_CHANGED_STATE'
    old=original(cur,lambda:refusal(cur,operation))
    assert old==new,(old,new)
    assert observe()==before,'OW04BA_ORIGINAL_REFUSAL_CHANGED_STATE'
    return new


def was_refused(cur,observe,operation):
    """An admitted call is refused by the followups definitions, without effect."""
    before=observe()
    old=original(cur,lambda:refusal(cur,operation))
    assert observe()==before,'OW04BA_ORIGINAL_REFUSAL_CHANGED_STATE'
    return old


def setup(cur,today):
    pair=fixture.prepare(cur,today,'CREDIT')
    applied,_,_=basic.apply(cur,pair,'80.00')
    t=dict(pair['target'],bank=pair['source']['f']['bank'])
    profiles=fixture.profiles(cur,pair)
    assert profiles['target']==AFTER_APPLY,profiles
    return pair,t,applied,profiles


def status(cur,t):
    native.b.api.admin(cur)
    value=cur.execute('select status from erp.sales_headers where id=%s',(t['sale'],)).fetchone()[0]
    assert native.source.read(cur,t)['detail']['status']==value;native.b.api.admin(cur)
    return value


def target(cur,pair,**changed):
    profile=fixture.profiles(cur,pair)['target']
    assert profile==dict(AFTER_APPLY,**changed),(profile,changed)
    return profile


def no_credit_objects(cur,pair):
    native.b.api.admin(cur)
    sale=pair['target']['sale']
    assert cur.execute('select count(*)from cp7_credit.return_families where family_root_sale_id=%s',(sale,)).fetchone()[0]==0
    assert cur.execute('select count(*)from cp7_credit.cohorts where source_sale_id=%s',(sale,)).fetchone()[0]==0
    return True


def pay(cur,t,amount,when=None):
    p,v=payments.payment_payload(cur,t,amount)
    if when is not None:p['payment_date']=when
    return p,v


def cases(cur,today):
    def two_parts():
        with native.isolated(cur):
            pair,t,_,before=setup(cur,today)
            p,v=pay(cur,t,'200.00')
            old=was_refused(cur,lambda:basic.observation(cur,pair),lambda:cmd.command(cur,'PAYMENT',p,v))
            assert (old['sqlstate'],old['message'])==('P0001',REGISTERED)and json.loads(old['detail'])==detail('PAYMENT',['CREDIT_APPLIED_TO_INVOICE']),old
            first=cmd.command(cur,'PAYMENT',p,v)
            assert status(cur,t)=='PARTIAL_PAID'
            target(cur,pair,P='200.00',E='280.00',AR='220.00')
            second=payments.pay(cur,t,'220.00')
            assert status(cur,t)=='PAID'
            after=fixture.profiles(cur,pair)
            assert after['target']==dict(AFTER_APPLY,P='420.00',E='500.00',AR='0.00'),after
            assert after['source']==before['source'],'OW04BA_SOURCE_CREDIT_CHANGED_BY_TARGET_PAYMENT'
            assert after['cash']==format(D(before['cash'])+D('420.00'),'.2f'),(before['cash'],after['cash'])
            return dict(status='PASS',predecessor_refusal=old,payments=[first['payment_id'],second['payment_id']],
                statuses=['PARTIAL_PAID','PAID'],target=after['target'],source_unchanged=True,no_credit_objects=no_credit_objects(cur,pair))

    def cent_over():
        with native.isolated(cur):
            pair,t,_,before=setup(cur,today)
            p,v=pay(cur,t,'420.01')
            state=basic.observation(cur,pair)
            over=refusal(cur,lambda:cmd.command(cur,'PAYMENT',p,v))
            assert over['sqlstate']=='P0001'and over['message'].startswith(
                'Customer payment exceeds exact remaining receivable. Net sale 500.00, already paid 80.00, requested 420.01'),over
            assert basic.observation(cur,pair)==state,'OW04BA_OVERPAYMENT_LEFT_AN_EFFECT'
            exact=payments.pay(cur,t,'420.00')
            assert status(cur,t)=='PAID'
            target(cur,pair,P='420.00',E='500.00',AR='0.00')
            return dict(status='PASS',refused=over,exact_payment=exact['payment_id'],status_after='PAID',
                no_credit_objects=no_credit_objects(cur,pair))

    def reverse():
        with native.isolated(cur):
            pair,t,_,before=setup(cur,today)
            paid=payments.pay(cur,t,'420.00')
            assert status(cur,t)=='PAID'
            p,v=cmd.review(cur,t);p['payment_id']=paid['payment_id']
            old=was_refused(cur,lambda:basic.observation(cur,pair),lambda:cmd.command(cur,'PAYMENT_REVERSE',p,v))
            assert old['message'].startswith('CP7_CREDIT_'),old
            payments.inverse(cur,t,paid['payment_id'])
            assert status(cur,t)=='PARTIAL_PAID'
            target(cur,pair)
            after=fixture.profiles(cur,pair)
            assert after['source']==before['source']and after['cash']==before['cash'],after
            return dict(status='PASS',predecessor_refusal=old,status_after='PARTIAL_PAID',target=after['target'],
                credit_kept_U='80.00',no_credit_objects=no_credit_objects(cur,pair))

    def undo_after_paid():
        with native.isolated(cur):
            pair,t,applied,before=setup(cur,today)
            payments.pay(cur,t,'420.00')
            assert status(cur,t)=='PAID'
            envelope=basic.review(cur,basic.payload(pair,'UNDO',original=applied['consumption_event_id']))
            undone=basic.command(cur,envelope,uuid.uuid4())
            assert undone['amount']=='-80.00',undone
            assert status(cur,t)=='PARTIAL_PAID'
            after=fixture.profiles(cur,pair)
            assert after['target']==dict(AFTER_APPLY,P='420.00',U='0.00',E='420.00',AR='80.00'),after
            assert after['source']==fixture.INITIAL['source'],after
            return dict(status='PASS',undo=undone['operation_id'],status_after='PARTIAL_PAID',target=after['target'],
                source_credit_restored=True)

    def backdated():
        with native.isolated(cur):
            pair,t,_,before=setup(cur,today)
            early=(datetime.fromisoformat(pair['target']['sale_at'])+timedelta(minutes=30)).isoformat()
            p,v=pay(cur,t,'420.00',early)
            first=cmd.command(cur,'PAYMENT',p,v)
            assert status(cur,t)=='PAID'
            payments.inverse(cur,t,first['payment_id'])
            assert status(cur,t)=='PARTIAL_PAID'
            # Today the invoice owes 420 again, but on the earlier dates the first payment still counts until its
            # reversal date: a second 420 on that early date would overfund those date pairs (420+420+80 > 500).
            p,v=pay(cur,t,'420.00',early)
            state=basic.observation(cur,pair)
            over=refusal(cur,lambda:cmd.command(cur,'PAYMENT',p,v))
            assert (over['sqlstate'],over['message'])in OVERFUNDING,over
            assert basic.observation(cur,pair)==state,'OW04BA_OVERFUNDING_LEFT_AN_EFFECT'
            today_paid=payments.pay(cur,t,'420.00')
            assert status(cur,t)=='PAID'
            target(cur,pair,P='420.00',E='500.00',AR='0.00')
            return dict(status='PASS',early_payment_date=early,refused=over,today_payment=today_paid['payment_id'],status_after='PAID')

    def protected():
        with native.isolated(cur):
            pair,t,_,before=setup(cur,today)
            observe=lambda:basic.observation(cur,pair)
            source=pair['source']['f']
            seen={}
            p,v=pay(cur,source,'10.00')
            seen['payment_on_credit_source']=identical(cur,observe,lambda:cmd.command(cur,'PAYMENT',p,v))
            q,w=cmd.review(cur,source);q['payment_id']=source['payment']
            seen['reverse_source_payment_while_credit_used']=identical(cur,observe,lambda:cmd.command(cur,'PAYMENT_REVERSE',q,w))
            n,m=native.note.edit(cur,pair['target'],price='110')
            seen['benerin_nota_on_credit_paid_target']=identical(cur,observe,lambda:native.note.correct(cur,n,m))
            new=seen['benerin_nota_on_credit_paid_target']
            assert (new['sqlstate'],new['message'])==('P0001',REGISTERED)and json.loads(new['detail'])==detail('SALE_REVERSE',['CREDIT_APPLIED_TO_INVOICE']),new
            # After a remaining payment, Benerin nota still refuses with the same message and no effect. Its first
            # step (the payment inverse) is now admitted, so the detail names the next unsupported step, SALE_REVERSE.
            payments.pay(cur,t,'420.00')
            n,m=native.note.edit(cur,pair['target'],price='110')
            state=observe()
            now=refusal(cur,lambda:native.note.correct(cur,n,m))
            assert observe()==state
            was=original(cur,lambda:refusal(cur,lambda:native.note.correct(cur,n,m)))
            assert observe()==state
            assert (now['sqlstate'],now['message'])==(was['sqlstate'],was['message'])==('P0001',REGISTERED),(now,was)
            assert json.loads(was['detail'])==detail('PAYMENT_REVERSE',['CREDIT_APPLIED_TO_INVOICE']),was
            assert json.loads(now['detail'])==detail('SALE_REVERSE',['CREDIT_APPLIED_TO_INVOICE']),now
            seen['benerin_nota_after_remaining_payment']=dict(now=now,predecessor=was,same_message_no_effect=True,
                detail_names_next_unsupported_step=True)
            return dict(status='PASS',**seen)

    result=list(zip(IDS,(two_parts,cent_over,reverse,undo_after_paid,backdated,protected)))
    assert tuple(key for key,_ in result)==IDS
    return result


def send(cur,p,v,request):
    cur.execute("set local timezone='UTC';set local lock_timeout='20s';set local statement_timeout='60s'")
    return cmd.command(cur,'PAYMENT',deepcopy(p),v,request)


def payment_race(tools,today,same_uuid):
    """Two real sessions pay 300 each on the remaining 420, both reviewed before either commits."""
    with tools.connect()as conn,conn.cursor()as cur:
        pair,t,_,before=setup(cur,today)
        p,v=pay(cur,t,'300.00')
        cur.execute('set constraints all immediate');conn.commit()
    first=uuid.uuid4();second=first if same_uuid else uuid.uuid4()
    worker_payload=p if same_uuid else dict(p,payment_number=p['payment_number']+'-2')
    def holder(cur):
        result=send(cur,p,v,first)
        return dict(result=result,pid=cur.execute('select pg_backend_pid()').fetchone()[0])
    held,contention,outcome=tools.two_sessions(holder,lambda cur:send(cur,worker_payload,v,second),True)
    assert contention==dict(kind='BLOCKED',holder_blocks_worker=True),contention
    if same_uuid:
        assert outcome==dict(ok=True,result=held['result']),outcome
    else:
        assert outcome==dict(ok=False,sqlstate='P0001',message='CP7_SALES_REVIEW_CHANGED'),outcome
    with tools.connect()as conn,conn.cursor()as cur:
        native.b.api.admin(cur)
        count=cur.execute("select count(*)from erp.sales_payments where sale_id=%s and status='POSTED'",(t['sale'],)).fetchone()[0]
        assert count==1,count
        after=fixture.profiles(cur,pair)
        assert after['target']==dict(AFTER_APPLY,P='300.00',E='380.00',AR='120.00'),after
        assert after['source']==before['source'],after
        state=cur.execute('select status from erp.sales_headers where id=%s',(t['sale'],)).fetchone()[0]
        assert state=='PARTIAL_PAID',state
        conn.rollback()
    return dict(status='PASS',two_actual_SQL_sessions=True,authenticated_SQL_fixture_not_real_Auth=True,
        actual_holder_blocks_worker=True,holder_committed=True,same_UUID=same_uuid,holder_backend_pid=held['pid'],
        actual_worker=outcome,actual_outcome=held['result'],posted_payments=count,target_after=after['target'],
        final_sha256=sha256(json.dumps(after,sort_keys=True).encode()).hexdigest(),production_go=False)


def races(tools,today):
    planned=[(RACE_IDS[0],lambda:payment_race(tools,today,False)),
             (RACE_IDS[1],lambda:payment_race(tools,today,True))]
    assert tuple(key for key,_ in planned)==RACE_IDS
    return planned
