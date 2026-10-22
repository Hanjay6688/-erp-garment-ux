"""Six frozen scheduling controls using actual Native consumer commands.

Privileged corruption is explicit and rolled back. The queue is pending work,
never a proof cache. Imports do not connect, install, seed or execute SQL.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import uuid

import native_basic_cases as basic

EXPECTED_SHA256='29baa7ae2ebf4a72e798614ec71ddebcd37176935e43770771826179722d0e1c'
QUEUE='cp7_credit.consumer_validation_queue_v1'
DRAIN='cp7_credit.drain_consumer_closed_v1()'


def expected():
    raw=Path(__file__).with_name('EXPECTED.json').read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA256
    return json.loads(raw)


IDS=tuple(row['id']for row in expected()['cases'])


def pending(cur):
    return cur.execute('select queue_id,backend_pid,transaction_id,actor,request_id from '+QUEUE+' order by queue_id').fetchall()


def drains(cur):
    return cur.execute('select coalesce((select calls from pg_stat_xact_user_functions where funcid=%s::regprocedure),0)',(DRAIN,)).fetchone()[0]


def access(cur):
    for role in ('anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write','cp7_credit_write'):
        assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,QUEUE)).fetchone()[0]
        assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,DRAIN)).fetchone()[0]
    assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity,relforcerowsecurity from pg_class where oid=%s::regclass',(QUEUE,)).fetchone()==('postgres',True,False)


def send(cur,envelope,request):
    basic.native.auth.actor(cur)
    answer=cur.execute('select public.erp_cp7_customer_credit_command_v1(%s::jsonb,%s::uuid,%s::jsonb)',
        (json.dumps(envelope['payload']),request,json.dumps(envelope['versions']))).fetchone()[0]
    basic.native.b.api.admin(cur)
    assert answer['kind']=='COMMITTED_OUTCOME'and answer['request_id']==str(request)
    return answer


def money(cur,pair):
    a=basic.fixture.profiles(cur,pair);s,t=a['source'],a['target']
    return dict(source_net=s['net'],source_P=s['P'],I=s['I'],C=s['net_consumption'],available=s['available_credit'],
        source_AR=s['AR'],target_P=t['P'],target_U=t['U'],target_AR=t['AR'],cash=a['cash'])


def close(cur):
    cur.execute('set constraints all immediate')
    assert pending(cur)==[]
    cur.execute('set constraints all deferred')


def refused(cur,pair,work,message):
    before=basic.observation(cur,pair)
    cur.execute('savepoint consumer_queue_expected_refusal')
    try:
        work()
    except Exception as error:
        code=error.sqlstate;observed=error.diag.message_primary
        cur.execute('rollback to savepoint consumer_queue_expected_refusal')
        basic.native.b.api.admin(cur)
        assert (code,observed)==('P0001',message),(code,observed,message)
    else:
        raise AssertionError('EXPECTED_ACTUAL_QUEUE_ATOMIC_REFUSAL')
    finally:
        cur.execute('release savepoint consumer_queue_expected_refusal')
    assert basic.observation(cur,pair)==before,'QUEUE_REFUSAL_CHANGED_NATIVE_OR_PRIVATE_FACTS'
    assert pending(cur)==[]
    return dict(sqlstate=code,error=observed,whole_transaction_effects_rolled_back=True)


def one_case(cur,today,index):
    with basic.native.isolated(cur):
        cur.execute("set local track_functions='all'")
        gold=expected()['cases'][index]
        pair=basic.fixture.prepare(cur,today)
        close(cur);access(cur)
        envelope=basic.review(cur,basic.payload(pair,amount='80.00'));request=uuid.uuid4()
        baseline=drains(cur);details={}
        if index in (2,3,5):
            def fault():
                send(cur,deepcopy(envelope),request)
                rows=pending(cur);assert len(rows)==1
                if index==2:
                    cur.execute('delete from '+QUEUE+' where queue_id=%s',(rows[0][0],))
                elif index==3:
                    cur.execute('update '+QUEUE+' set request_id=%s where queue_id=%s',(uuid.uuid4(),rows[0][0]))
                else:
                    cur.execute("update cp7_credit.consumer_requests_v1 set response=response||'{\"late_fault\":true}'::jsonb where actor=%s and request_id=%s",(rows[0][3],request))
                close(cur)
            details['actual_privileged_fault']=refused(cur,pair,fault,gold['error'])
            observed=money(cur,pair)
            assert observed==gold['expected_after_refused'],(observed,gold)
        else:
            answer=send(cur,deepcopy(envelope),request)
            first=pending(cur);assert len(first)==1
            assert first[0][1:]==(cur.execute('select pg_backend_pid()').fetchone()[0],
                cur.execute('select txid_current()').fetchone()[0],uuid.UUID(str(basic.native.auth.base.OPERATOR_AUTH)),request)
            assert send(cur,deepcopy(envelope),request)==answer
            assert pending(cur)==first,'EXACT_REPLAY_REQUEUED_OR_REPLACED_PENDING_WORK'
            if index==1:
                second=basic.review(cur,basic.payload(pair,amount='20.00'))
                send(cur,second,uuid.uuid4())
            if index in (0,1):
                assert len(pending(cur))==gold['pending_before']
            close(cur)
            if index==4:
                assert len(pending(cur))==gold['pending_after_first_drain']
                before=basic.observation(cur,pair)
                cur.execute('update cp7_credit.consumer_requests_v1 set response=response where actor=%s and request_id=%s',(first[0][3],request))
                again=pending(cur)
                assert len(again)==gold['pending_after_actual_request_update']
                assert again[0][0]!=first[0][0]and again[0][1:]==first[0][1:]
                details['fresh_queue_identity_after_prior_drain']=True
                close(cur)
                assert basic.observation(cur,pair)==before,'NOOP_REVALIDATION_CHANGED_FINANCIAL_FACTS'
            details['actual_deferred_drains']=drains(cur)-baseline
            assert details['actual_deferred_drains']==gold['drains'],details
            observed=money(cur,pair)
            assert observed==gold['expected'],(observed,gold)
        access(cur);assert pending(cur)==[]
        return dict(status='PASS',id=gold['id'],expected=gold,observed=observed,details=details,
            actual_Native_writers=True,ordinary_roles_cannot_access_queue_or_drain=True,
            queued_work_not_cached_proof=True,production_go=False)


def cases(cur,today):
    return [(key,lambda index=index:one_case(cur,today,index))for index,key in enumerate(IDS)]
