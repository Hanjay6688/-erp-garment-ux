"""OW-04b slice B Native cases: second and later returns on a paid invoice.

Fixture: the retained OW04 consumer pair (source invoice 1000 paid 1000, first return 200 settled as credit 200; target
invoice 500). Every later return goes through the retained public quote and settle RPCs with an explicit settlement
choice and a fresh disposable liability master; every money document comes from the retained writers. Changed paths
are compared with the exact predecessor definitions (slice A / followups) inside a rolled-back savepoint.
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
from cp7_credit_multi import native_delta

native=fixture.native
signed=fixture.signed
IDS=('OW04BB_FIRST_RETURN_QUOTES_UNCHANGED',
     'OW04BB_SECOND_RETURN_CREDIT',
     'OW04BB_SECOND_RETURN_REFUND',
     'OW04BB_THIRD_RETURN',
     'OW04BB_SECOND_RETURN_AFTER_CREDIT_USED',
     'OW04BB_PROTECTED_REFUSALS_IDENTICAL')
RACE_IDS=('OW04BB_RACE_TWO_FIRST_RETURNS_STALE_INVOICE',)
INITIAL_FAMILY='CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED'
STALE='CP7_SALES_REVIEW_CHANGED'
ORIGINALS=None  # set by the probe: the exact predecessor definitions this stage replaced
AS_OWNER=None   # set by the probe: the verified predecessor role switch


def refusal(cur,operation):
    native.b.api.admin(cur);name='ow04bb_refusal_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        operation()
    except psycopg.Error as error:
        found=dict(sqlstate=error.sqlstate,message=error.diag.message_primary,detail=error.diag.message_detail or '')
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)
        return found
    cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)
    raise AssertionError('OW04BB_EXPECTED_REFUSAL_BUT_CALL_SUCCEEDED')


def original(cur,fn):
    name='ow04bb_original_'+uuid.uuid4().hex
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
    assert observe()==before,'OW04BB_REFUSAL_CHANGED_STATE'
    old=original(cur,lambda:refusal(cur,operation))
    assert old==new,(old,new)
    return new


def source_profile(cur,pair):
    return fixture.profiles(cur,pair)['source']


def later_return(cur,pair,qty,refund,mode,expected_k,ordinal):
    """One more return on the paid source invoice through the retained quote and settle RPCs."""
    f=pair['source']['f']
    query=followups.draft_query(cur,f,qty,refund)
    first=native.call_quote(cur,query)
    assert first['has_recognition_effect']is True and first['current_credit_amount']==expected_k,first
    assert first['readiness']['state']=='CHOICE_REQUIRED',first['readiness']
    credit=initial._credit_master(cur)
    physical=query['return_payload']['physical_at']if mode=='REFUND'else None
    query['settlement']=dict(mode=mode,credit_account_id=credit['id'],cash_account_id=f['bank']if mode=='REFUND'else None,
        refund_physical_at=physical,reference='OW04b slice B refund'if mode=='REFUND'else None)
    quote=native.call_quote(cur,query)
    assert quote['readiness']==dict(state='READY',issues=[]),quote['readiness']
    assert quote['current_credit_amount']==expected_k,quote
    envelope=initial._envelope(query,quote);request=uuid.uuid4()
    result=initial._settle(cur,envelope,request)
    assert (result['kind'],result['action'],result['return_status'],result['family_ordinal'])==(
        'COMMITTED_OUTCOME','RETURN_SETTLEMENT','POSTED',str(ordinal)),result
    if mode=='REFUND':assert result['refund_event_id'],result
    native.b.api.admin(cur)
    return dict(query=query,quote=quote,result=result,request=str(request),credit=credit)


def cohort_components(cur,sale):
    native.b.api.admin(cur)
    return cur.execute("""select f.family_ordinal,coalesce(jsonb_agg(cc.kernel_component order by cc.ordinal),'[]')
     from cp7_credit.return_families f join cp7_credit.cohorts c on c.family_id=f.id join cp7_credit.recognition_plans p on p.id=c.initial_plan_id
     join cp7_credit.recognition_components cc on cc.plan_id=p.id where f.family_root_sale_id=%s group by f.family_ordinal order by 1""",(sale,)).fetchall()


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
                assert strip(new)==strip(old),'OW04BB_FIRST_RETURN_QUOTE_CHANGED'
                compared[mode]=dict(quote_sha256=new['binding']['quote_sha256'],credit=new['current_credit_amount'])
        return dict(status='PASS',identical_first_return_quotes=compared)

    def second_credit():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');sale=pair['source']['f']['sale']
            before=fixture.profiles(cur,pair);first_components=cohort_components(cur,sale)
            query=followups.draft_query(cur,pair['source']['f'],'1','100.00')
            old=original(cur,lambda:refusal(cur,lambda:native.call_quote(cur,query)))
            assert (old['sqlstate'],old['message'])==('P0001',INITIAL_FAMILY),old
            done=later_return(cur,pair,'1','100.00','CREDIT','100.00',2)
            totals=done['quote']['totals']
            assert (totals['before']['credit_recognized'],totals['before']['effective_paid'],totals['after']['credit_recognized'],
                    totals['after']['effective_paid'],totals['after']['receivable_remaining'])==('200.00','800.00','300.00','700.00','0.00'),totals
            after=fixture.profiles(cur,pair)
            assert {k:after['source'][k]for k in('gross','net','P','U','I','E','AR')}==dict(
                gross='1000.00',net='700.00',P='1000.00',U='0.00',I='300.00',E='700.00',AR='0.00'),after
            assert after['target']==before['target']and after['cash']==before['cash'],after
            components=cohort_components(cur,sale)
            assert components[0]==first_components[0]and len(components)==2,components
            return dict(status='PASS',predecessor_refusal=old['message'],family_ordinal=2,credit_2='100.00',
                source=after['source'],first_family_components_unchanged=True)

    def second_refund():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');before=fixture.profiles(cur,pair)
            done=later_return(cur,pair,'1','100.00','REFUND','100.00',2)
            after=fixture.profiles(cur,pair)
            assert (after['source']['I'],after['source']['E'],after['source']['AR'])==('300.00','700.00','0.00'),after
            assert D(after['cash'])==D(before['cash'])-D('100.00'),(before['cash'],after['cash'])
            return dict(status='PASS',refund_event=done['result']['refund_event_id'],cash_before=before['cash'],cash_after=after['cash'])

    def third():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT')
            later_return(cur,pair,'1','100.00','CREDIT','100.00',2)
            later_return(cur,pair,'1','100.00','CREDIT','100.00',3)
            after=fixture.profiles(cur,pair)['source']
            assert (after['net'],after['I'],after['E'],after['AR'])==('600.00','400.00','600.00','0.00'),after
            return dict(status='PASS',families=3,source=after)

    def after_credit_used():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');sale=pair['source']['f']['sale']
            applied,_,_=basic.apply(cur,pair,'80.00');first_components=cohort_components(cur,sale)
            later_return(cur,pair,'1','100.00','CREDIT','100.00',2)
            after=fixture.profiles(cur,pair)
            assert (after['source']['I'],after['source']['E'])==('300.00','700.00')and after['target']['U']=='80.00',after
            assert cohort_components(cur,sale)[0]==first_components[0]
            return dict(status='PASS',applied=applied['consumption_event_id'],source=after['source'],first_family_unchanged=True)

    def protected():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');basic.apply(cur,pair,'80.00')
            observe=lambda:basic.observation(cur,pair);seen={}
            t=pair['target'];native.b.api.admin(cur)
            t['allocations']=returns.read(cur,t)['page']['rows'];t['destination']=pair['source']['f']['destination']
            query=followups.draft_query(cur,t,'1','50.00')
            seen['return_on_credit_paid_invoice']=identical(cur,observe,lambda:native.call_quote(cur,query))
            f=dict(pair['source']['f'])
            p,v=correction.payload(cur,f,qty='1',refund='150.00',return_id=pair['initial_result']['return_id'])
            seen['edit_retur_on_credit_source']=identical(cur,observe,lambda:correction.correct(cur,p,v))
            n,m=native.note.edit(cur,pair['target'],price='110')
            seen['benerin_nota_on_credit_paid_target']=identical(cur,observe,lambda:native.note.correct(cur,n,m))
            for name,value in seen.items():
                assert value['sqlstate']=='P0001'and value['message'].startswith('CP7_'),(name,value)
            # A return WITHOUT a settlement choice on the paid invoice (P11) stays refused with no effect; its first
            # refusal may differ, because the quote no longer refuses an earlier credit return before Native decides.
            state=observe()
            now=refusal(cur,lambda:returns.returned(cur,pair['source']['f'],qty='1',refund='100.00'))
            assert observe()==state
            was=original(cur,lambda:refusal(cur,lambda:returns.returned(cur,pair['source']['f'],qty='1',refund='100.00')))
            assert observe()==state
            seen['ordinary_return_without_choice']=dict(now=now,predecessor=was,still_refused_no_effect=True)
            return dict(status='PASS',**seen)

    result=list(zip(IDS,(first_quotes,second_credit,second_refund,third,after_credit_used,protected)))
    assert tuple(key for key,_ in result)==IDS
    return result


def stale_race(tools,today):
    """Two real sessions settle a FIRST return on the same invoice from the same quote, distinct requests."""
    with tools.connect()as conn,conn.cursor()as cur:
        gold=next(row for row in initial.expected()['cases']if row['id']=='OW04_INITIAL_1000_OPEN_CREDIT')
        x=native.prepared(cur,today,'1000.00','OPEN');credit=initial._credit_master(cur)
        query=initial._input(x,gold,credit);quote=native.call_quote(cur,query)
        assert quote['readiness']==dict(state='READY',issues=[]),quote['readiness']
        envelope=initial._envelope(query,quote)
        cur.execute('set constraints all immediate');conn.commit()
    first,second=uuid.uuid4(),uuid.uuid4();frozen=deepcopy(envelope)
    def send(cur,request):
        cur.execute("set local timezone='UTC';set local lock_timeout='20s';set local statement_timeout='60s'")
        return initial._settle(cur,deepcopy(envelope),request)
    def holder(cur):
        result=send(cur,first)
        cur.execute('set constraints all immediate')
        return dict(result=result,complete=signed._observe(cur,x),pid=cur.execute('select pg_backend_pid()').fetchone()[0])
    held,contention,outcome=tools.two_sessions(holder,lambda cur:send(cur,second),True)
    assert contention==dict(kind='BLOCKED',holder_blocks_worker=True),contention
    # Read from the settle path: after the holder's return the worker passes the (now multi-family) family check and
    # is refused by the retained invoice-state binding (row version / review token over the returns) before any write.
    assert outcome==dict(ok=False,sqlstate='P0001',message=STALE),outcome
    assert envelope==frozen
    with tools.connect()as conn,conn.cursor()as cur:
        native.b.api.admin(cur)
        after=signed._observe(cur,x)
        assert after==held['complete'],'OW04BB_RACE_WORKER_CHANGED_BUSINESS_OR_PRIVATE_FACTS'
        sale=x['f']['sale']
        posted=cur.execute("select count(*)from erp.sales_returns where sale_id=%s and status<>'DRAFT'",(sale,)).fetchone()[0]
        cohorts=cur.execute('select count(*)from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=%s',(sale,)).fetchone()[0]
        worker=cur.execute('select count(*)from cp7_credit.return_requests where request_id=%s',(second,)).fetchone()[0]
        assert (posted,cohorts,worker)==(1,1,0),(posted,cohorts,worker)
        conn.rollback()
    return dict(status='PASS',two_actual_SQL_sessions=True,authenticated_SQL_fixture_not_real_Auth=True,
        actual_holder_blocks_worker=True,holder_committed=True,actual_worker=outcome,holder_outcome=held['result'],
        posted_returns=posted,cohorts=cohorts,worker_request_rows=worker,holder_backend_pid=held['pid'],
        final_state_sha256=sha256(json.dumps(after,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest(),
        production_go=False)


def races(tools,today):
    planned=[(RACE_IDS[0],lambda:stale_race(tools,today))]
    assert tuple(key for key,_ in planned)==RACE_IDS
    return planned
