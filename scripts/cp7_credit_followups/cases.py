"""OW-04b Native cases (retest 23 Oct 2026, OW-04 parts 3 and 4).

Part 3: each retained refusal now names its reason in a DETAIL. The original OW04 definitions are reinstalled side by
side inside a rolled-back savepoint: same SQLSTATE and message, no detail, and the refused call changes nothing.
Part 4: a cash refund (initial settlement REFUND and later consumer REFUND) is refused without any effect when the bank
is short on that date, and passes with exactly the needed capital dated on that day; two sessions undo the same credit
use at once and exactly one undo exists afterwards. Every money/stock document comes from the retained OW04/CP7 writers;
the only administrative fixtures are masters (accounts, banks) and owner capital (cp7_cash_funding).
"""
from copy import deepcopy
from datetime import date
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
import cp7_cash_funding as funding
from cp7_credit_followups import native_delta

native=fixture.native
signed=fixture.signed
payments=returns.payments
IDS=('OW04B_FIRST_RETURN_QUOTES_UNCHANGED',
     'OW04B_SECOND_RETURN_NAMES_PRIOR_CREDIT_RETURN',
     'OW04B_RETURN_ON_CREDIT_PAID_INVOICE_NAMES_REASON',
     'OW04B_EDIT_RETUR_ON_CREDIT_INVOICE_NAMES_REASON',
     'OW04B_PAYMENT_ON_CREDIT_PAID_INVOICE_NAMES_REASON',
     'OW04B_REFUND_EMPTY_BANK_REFUSED_NO_EFFECT_THEN_FUNDED',
     'OW04B_REFUND_BANK_FUNDED_AFTER_REFUND_DATE_REFUSED',
     'OW04B_CONSUMER_REFUND_EMPTY_BANK_REFUSED_NO_EFFECT_THEN_FUNDED')
RACE_IDS=('OW04B_RACE_TWO_UNDO_APPLY_DISTINCT_UUID',
          'OW04B_RACE_TWO_UNDO_APPLY_SAME_UUID',
          'OW04B_RACE_TWO_UNDO_INITIAL_REFUND_DISTINCT_UUID')
CONTRACT='cp7.credit-followups.refusal.v1'
INITIAL_FAMILY='CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED'
REGISTERED='CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION'
ORIGINALS=None  # set by the probe: the exact OW04 definitions this stage replaced
AS_OWNER=None   # set by the probe: the verified predecessor role switch (replace as postgres, the verified owner)


def detail(refusal,action,reasons):
    return dict(contract=CONTRACT,refusal=refusal,action=action,reasons=list(reasons),source_blockers=[])


def refusal(cur,operation):
    """The refusal of one call, rolled back; a call that succeeds fails the case."""
    native.b.api.admin(cur);name='ow04b_refusal_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        operation()
    except psycopg.Error as error:
        found=dict(sqlstate=error.sqlstate,message=error.diag.message_primary,detail=error.diag.message_detail or '')
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)
        return found
    cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)
    raise AssertionError('OW04B_EXPECTED_REFUSAL_BUT_CALL_SUCCEEDED')


def original(cur,fn):
    """The same call through the exact replaced OW04 definitions, then restored."""
    name='ow04b_original_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        with AS_OWNER(cur,'postgres'):
            for sig in native_delta.SIGNATURES:cur.execute(ORIGINALS[sig],prepare=False)
        native.b.api.admin(cur)
        return fn()
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);native.b.api.admin(cur)


def side_by_side(cur,observe,operation,message,expected):
    """Patched: same message plus the expected detail; original: same message, no detail; neither changes state."""
    before=observe()
    new=refusal(cur,operation)
    assert (new['sqlstate'],new['message'])==('P0001',message),new
    assert json.loads(new['detail'])==expected,new
    assert observe()==before,'OW04B_REFUSAL_CHANGED_STATE'
    old=original(cur,lambda:refusal(cur,operation))
    assert old==dict(new,detail=''),(old,new)
    assert observe()==before,'OW04B_ORIGINAL_REFUSAL_CHANGED_STATE'
    return dict(patched=new,original=old)


def draft_query(cur,f,qty,refund):
    """A complete settlement-quote input for one more return on invoice f, exactly as the screen sends it."""
    p,v=returns.payload(cur,f,qty=qty,refund=refund)
    draft={key:p[key]for key in('return_number','physical_at','notes','items','change_reason')}
    for line in draft['items']:line['refund_amount']=format(D(line['refund_amount']),'.2f')
    return dict(sale_id=p['sale_id'],expected_version=v,review_token=p['review_token'],return_payload=draft,
        settlement=dict(mode=None,credit_account_id=None,cash_account_id=None,refund_physical_at=None,reference=None))


def empty_bank(cur):
    """ADMINISTRATIVE_DISPOSABLE_MASTER_FIXTURE: a new bank with no journal line (owner D14-3: never funded silently)."""
    bank=str(native.source.bc.bank_account(cur,'OW04B-'+uuid.uuid4().hex[:10]));native.b.api.admin(cur)
    coa,code=cur.execute('select coa_account_id::text,cash_account_code from erp.cash_accounts where id=%s',(bank,)).fetchone()
    assert cur.execute('select count(*)from erp.journal_lines where account_id=%s',(coa,)).fetchone()[0]==0
    return bank,coa,code


def balance(cur,coa):
    native.b.api.admin(cur)
    return format(cur.execute('select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=%s',(coa,)).fetchone()[0],'.2f')


def cash_refusal(found,code,minus,day):
    """The retained dated cash guard (cp7_guard.check_cash) refuses on the economic date of the refund, naming the bank,
    the exact shortfall and the date (owner D14-3: kas/bank tidak boleh minus)."""
    assert found['sqlstate']=='P0001'and found['message'].startswith('CP7_CASH_NEGATIVE: '),found
    assert '('+code+') menjadi minus '+minus+' pada tanggal '+day+' atau sesudahnya (tanggal ekonomi)'in found['message'],found
    return found['message']


def refund_setup(cur,today):
    gold=next(row for row in initial.expected()['cases']if row['id']=='OW04_INITIAL_1000_OPEN_REFUND')
    x=native.prepared(cur,today,'1000.00','OPEN');credit=initial._credit_master(cur)
    bank,coa,code=empty_bank(cur)
    query=initial._input(x,gold,credit);query['settlement']['cash_account_id']=bank
    return x,credit,query,bank,coa,code


def quoted(cur,query,bank):
    q=native.call_quote(cur,query)
    assert q['readiness']==dict(state='READY',issues=[])and q['cash_account']['id']==bank,q['readiness']
    assert q['current_credit_amount']=='200.00'and q['refund_projection']['amount']=='200.00',q
    return q


def cases(cur,today):
    def first_quotes():
        # Same answer on the path that is NOT refused: the full first-return quote (READY, one component, totals,
        # bindings) is identical with the replaced and the original builder, for CREDIT and REFUND.
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
                assert strip(new)==strip(old),'OW04B_FIRST_RETURN_QUOTE_CHANGED'
                compared[mode]=dict(quote_sha256=new['binding']['quote_sha256'],credit=new['current_credit_amount'],
                    components=len(new['components']),refund=(new['refund_projection']or{}).get('amount'))
        assert compared['CREDIT']['credit']==compared['REFUND']['refund']=='200.00'
        return dict(status='PASS',compared=compared,identical_except_captured_at=True)

    def second_return():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');f=pair['source']['f']
            query=draft_query(cur,f,'1','100.00')
            seen=side_by_side(cur,lambda:basic.observation(cur,pair),lambda:native.call_quote(cur,query),INITIAL_FAMILY,
                detail('INITIAL_SOURCE_FAMILY',None,['PRIOR_CREDIT_RETURN']))
            return dict(status='PASS',screen_code=INITIAL_FAMILY,reasons=['PRIOR_CREDIT_RETURN'],**seen)

    def credit_paid_invoice_return():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');applied,_,_=basic.apply(cur,pair,'80.00')
            t=pair['target'];native.b.api.admin(cur)
            t['allocations']=returns.read(cur,t)['page']['rows'];t['destination']=pair['source']['f']['destination']
            assert fixture.profiles(cur,pair)['target']['U']=='80.00'
            query=draft_query(cur,t,'1','50.00')
            seen=side_by_side(cur,lambda:basic.observation(cur,pair),lambda:native.call_quote(cur,query),INITIAL_FAMILY,
                detail('INITIAL_SOURCE_FAMILY',None,['CREDIT_APPLIED_TO_INVOICE']))
            return dict(status='PASS',applied=applied['consumption_event_id'],reasons=['CREDIT_APPLIED_TO_INVOICE'],**seen)

    def edit_retur():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');f=dict(pair['source']['f'])
            p,v=correction.payload(cur,f,qty='1',refund='150.00',return_id=pair['initial_result']['return_id'])
            seen=side_by_side(cur,lambda:basic.observation(cur,pair),lambda:correction.correct(cur,p,v),REGISTERED,
                detail('REGISTERED_SOURCE_MUTATION','RETURN_REVERSE',['PRIOR_CREDIT_RETURN']))
            return dict(status='PASS',screen='Edit retur',action='RETURN_REVERSE',reasons=['PRIOR_CREDIT_RETURN'],**seen)

    def payment_on_credit_paid_invoice():
        # Not a new limit: the retained OW04 hook already refuses an ordinary payment on an invoice that received
        # credit. This case proves the refusal is now named; the limit itself stays open (docs OW04B.md).
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');basic.apply(cur,pair,'80.00')
            t=dict(pair['target'],bank=pair['source']['f']['bank'])
            seen=side_by_side(cur,lambda:basic.observation(cur,pair),lambda:payments.pay(cur,t,'100.00'),REGISTERED,
                detail('REGISTERED_SOURCE_MUTATION','PAYMENT',['CREDIT_APPLIED_TO_INVOICE']))
            return dict(status='PASS',action='PAYMENT',reasons=['CREDIT_APPLIED_TO_INVOICE'],open_limit_named=True,**seen)

    def refund_empty_bank():
        with native.isolated(cur):
            x,credit,query,bank,coa,code=refund_setup(cur,today);d2=x['dates']['D2']
            q=quoted(cur,query,bank);envelope=initial._envelope(query,q);request=uuid.uuid4()
            before=signed._observe(cur,x)
            message=cash_refusal(refusal(cur,lambda:initial._settle(cur,envelope,request)),code,'-200.00',d2)
            assert signed._observe(cur,x)==before,'OW04B_REFUSED_REFUND_LEFT_AN_EFFECT'
            native.b.api.admin(cur)
            assert cur.execute('select count(*)from erp.sales_returns where sale_id=%s and status<>%s',(x['f']['sale'],'DRAFT')).fetchone()[0]==0
            assert cur.execute('select count(*)from cp7_credit.return_requests where request_id=%s',(request,)).fetchone()[0]==0
            assert balance(cur,coa)=='0.00'
            # Positive control: exactly the refund amount as owner capital on the refund's own day; same request UUID.
            capital=funding.fund(cur,bank,'200.00',date.fromisoformat(d2));native.b.api.admin(cur)
            q2=quoted(cur,query,bank);envelope2=initial._envelope(query,q2)
            result=initial._settle(cur,envelope2,request)
            initial._assert_outcome(result,request,envelope2,q2,'REFUND')
            native.b.api.admin(cur)
            events=cur.execute('select event_kind,amount,cash_account_id::text,economic_date::text from cp7_credit.consumption_events where cohort_id=%s',
                (result['credit_id'],)).fetchall()
            assert events==[('REFUND',D('200.00'),bank,d2)],events
            assert balance(cur,coa)=='0.00','OW04B_REFUND_NOT_EXACTLY_ONCE'
            cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
            return dict(status='PASS',refused=message,state_unchanged=True,capital_journal=str(capital),
                same_request_after_funding=result['refund_event_id'],bank_after='0.00',refund_events=1)

    def refund_funded_later():
        with native.isolated(cur):
            x,credit,query,bank,coa,code=refund_setup(cur,today);d2,d3=x['dates']['D2'],x['dates']['D3']
            assert d3>d2
            capital=funding.fund(cur,bank,'200.00',date.fromisoformat(d3));native.b.api.admin(cur)
            q=quoted(cur,query,bank);envelope=initial._envelope(query,q);request=uuid.uuid4()
            before=signed._observe(cur,x)
            message=cash_refusal(refusal(cur,lambda:initial._settle(cur,envelope,request)),code,'-200.00',d2)
            assert signed._observe(cur,x)==before,'OW04B_REFUSED_REFUND_LEFT_AN_EFFECT'
            assert balance(cur,coa)=='200.00'
            return dict(status='PASS',refused=message,capital_day=d3,refund_day=d2,capital_journal=str(capital),
                state_unchanged=True,bank_after='200.00')

    def consumer_refund_empty_bank():
        with native.isolated(cur):
            pair=fixture.prepare(cur,today,'CREDIT');bank,coa,code=empty_bank(cur)
            p=basic.payload(pair,'REFUND','80.00');p['cash_account_id']=bank
            day=pair['source']['dates']['D2']
            assert p['physical_at'][:10]==day
            envelope=basic.review(cur,p);request=uuid.uuid4()
            before=basic.observation(cur,pair)
            message=cash_refusal(refusal(cur,lambda:basic.command(cur,envelope,request)),code,'-80.00',day)
            assert basic.observation(cur,pair)==before,'OW04B_REFUSED_CONSUMER_REFUND_LEFT_AN_EFFECT'
            assert fixture.profiles(cur,pair)==fixture.INITIAL
            capital=funding.fund(cur,bank,'80.00',date.fromisoformat(day));native.b.api.admin(cur)
            result=basic.command(cur,basic.review(cur,p),request)
            assert result['amount']=='80.00',result
            assert fixture.profiles(cur,pair)['source']['available_credit']=='120.00'
            assert balance(cur,coa)=='0.00','OW04B_CONSUMER_REFUND_NOT_EXACTLY_ONCE'
            return dict(status='PASS',refused=message,state_unchanged=True,capital_journal=str(capital),
                same_request_after_funding=result['operation_id'],bank_after='0.00',available_credit_after='120.00')

    result=list(zip(IDS,(first_quotes,second_return,credit_paid_invoice_return,edit_retur,payment_on_credit_paid_invoice,
                         refund_empty_bank,refund_funded_later,consumer_refund_empty_bank)))
    assert tuple(key for key,_ in result)==IDS
    return result


def send(cur,envelope,request):
    cur.execute("set local timezone='UTC';set local lock_timeout='20s';set local statement_timeout='60s'")
    return basic.command(cur,deepcopy(envelope),request)


def observe(cur,pair):
    cur.execute("set local timezone='UTC'")
    return basic.observation(cur,pair)


def undo_race(tools,today,mode,same_uuid):
    """Two real sessions send UNDO of the same credit use; both were reviewed before either commits."""
    with tools.connect()as conn,conn.cursor()as cur:
        pair=fixture.prepare(cur,today,mode)
        if mode=='CREDIT':
            applied,_,_=basic.apply(cur,pair,'80.00');original_event=applied['consumption_event_id']
        else:
            original_event=pair['initial_result']['refund_event_id']
        envelope=basic.review(cur,basic.payload(pair,'UNDO',original=original_event))
        cur.execute('set constraints all immediate');conn.commit()
    frozen=deepcopy(envelope);first=uuid.uuid4();second=first if same_uuid else uuid.uuid4()
    def holder(cur):
        result=send(cur,envelope,first)
        return dict(result=result,complete=observe(cur,pair),pid=cur.execute('select pg_backend_pid()').fetchone()[0])
    held,contention,outcome=tools.two_sessions(holder,lambda cur:send(cur,envelope,second),True)
    assert contention==dict(kind='BLOCKED',holder_blocks_worker=True),contention
    if same_uuid:
        assert outcome==dict(ok=True,result=held['result']),outcome
    else:
        assert outcome==dict(ok=False,sqlstate='P0001',message='CP7_CREDIT_CONSUMER_ORIGINAL_ALREADY_UNDONE'),outcome
    assert envelope==frozen,'OW04B_RACE_CHANGED_REVIEWED_ENVELOPE'
    assert held['result']['amount']==('-80.00'if mode=='CREDIT'else'-200.00')and held['result']['restores_event_id']==str(original_event)
    with tools.connect()as conn,conn.cursor()as cur:
        native.b.api.admin(cur)
        after=observe(cur,pair)
        assert after==held['complete'],'OW04B_RACE_WORKER_CHANGED_BUSINESS_OR_PRIVATE_FACTS'
        actor=native.auth.base.OPERATOR_AUTH
        requests=cur.execute('select request_id::text,response from cp7_credit.consumer_requests_v1 where actor=%s and request_id=any(%s::uuid[])order by request_id',
            (actor,[first,second])).fetchall()
        assert requests==[(str(first),held['result'])],requests
        undos=cur.execute('select count(*)from cp7_credit.consumption_events where restores_event_id=%s',(original_event,)).fetchone()[0]
        assert undos==1,undos
        cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)',(held['result']['operation_id'],))
        profiles=fixture.profiles(cur,pair)
        assert profiles==fixture.INITIAL,(profiles,fixture.INITIAL)
        conn.rollback()
    return dict(status='PASS',two_actual_SQL_sessions=True,authenticated_SQL_fixture_not_real_Auth=True,
        actual_holder_blocks_worker=True,holder_committed=True,mode=mode,same_UUID=same_uuid,
        holder_request_id=str(first),worker_request_id=str(second),holder_backend_pid=held['pid'],
        actual_worker=outcome,actual_outcome=held['result'],undo_events=undos,profiles_after=profiles,
        final_state_sha256=sha256(json.dumps(after,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest(),
        production_go=False,independent_acceptance=False)


def races(tools,today):
    planned=[(RACE_IDS[0],lambda:undo_race(tools,today,'CREDIT',False)),
             (RACE_IDS[1],lambda:undo_race(tools,today,'CREDIT',True)),
             (RACE_IDS[2],lambda:undo_race(tools,today,'REFUND',False))]
    assert tuple(key for key,_ in planned)==RACE_IDS
    return planned
