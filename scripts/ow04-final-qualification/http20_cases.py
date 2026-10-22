"""Retain real Auth18; add two distinct signed-in users racing one credit.

Both requests must be observed waiting behind the actual global writer lock
before it is released. No token is forged and no product timeout is changed.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util,json,time,uuid

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('final_retained_auth18',HERE.parent/'ow04-payment-current-qualification/http_cases.py')
retained=importlib.util.module_from_spec(spec);spec.loader.exec_module(retained)
credit=retained.credit
RETAINED_IDS=retained.IDS
NEW_IDS=('OW04_REAL_AUTH_TWO_USERS_APPLY150_ONE_EFFECT','OW04_REAL_AUTH_TWO_USERS_REFUND150_ONE_EFFECT')
IDS=RETAINED_IDS+NEW_IDS
EXPECTED_SHA256='9790794287e38363e0d8637ebea906f2fabf29a67796c0a66b3e124366dce406'


def expected():
    raw=(HERE/'EXPECTED_REAL_AUTH_RACES.json').read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA256
    value=json.loads(raw)
    assert tuple(row['id']for row in value['cases'])==NEW_IDS
    assert len(IDS)==len(set(IDS))==20
    return value


def race(http,today,index):
    gold=expected()['cases'][index];action=gold['action']
    users=[http.login('OWNER',label='race-'+action.lower()+'-'+str(i))for i in range(2)]
    assert users[0].auth_user_id!=users[1].auth_user_id
    pair=credit.prepared(http,today)
    args=[{**credit.quoted(http,u,credit.payload(pair,action,'150.00')),
        'p_request':str(uuid.uuid4())}for u in users]
    with http.connect()as conn,conn.cursor()as cur:
        credit.native.b.api.admin(cur)
        before=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',
            (pair['source']['f']['sale'],)).fetchone()[0]
        conn.rollback()
    blocked=[]
    with ThreadPoolExecutor(max_workers=2)as pool:
        with http.connect()as holder,holder.cursor()as cur:
            holder_pid=cur.execute("select pg_backend_pid(),pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))").fetchone()[0]
            futures=[pool.submit(user.rpc,credit.COMMAND,deepcopy(a))for user,a in zip(users,args)]
            try:
                deadline=time.monotonic()+20
                while True:
                    blocked=cur.execute("select pid,wait_event_type,wait_event from pg_stat_activity "
                        "where datname=current_database()and %s=any(pg_blocking_pids(pid))order by pid",
                        (holder_pid,)).fetchall()
                    if len(blocked)==2:break
                    assert time.monotonic()<deadline,('TWO_REAL_AUTH_WRITERS_NOT_OBSERVED_WAITING',blocked)
                    assert not any(f.done()for f in futures),'REAL_AUTH_WRITER_FINISHED_BEFORE_GLOBAL_LOCK_RELEASE'
                    time.sleep(.03)
                assert all(row[1:] == ('Lock','advisory')for row in blocked),blocked
            finally:
                holder.rollback()
        answers=[future.result(timeout=60)for future in futures]
    winners=[i for i,r in enumerate(answers)if r['status']==200]
    assert len(winners)==1,answers
    win=winners[0];lose=1-win
    result=credit.response(answers[win])
    credit.response(answers[lose],400,gold['loser_error'])
    assert result['request_id']==args[win]['p_request']and result['amount']=='150.00'
    actual=retained.compact(http,pair);assert actual==gold['expected'],(actual,gold)
    with http.connect()as conn,conn.cursor()as cur:
        credit.native.b.api.admin(cur)
        rows=cur.execute('select actor::text,request_id::text,response from cp7_credit.consumer_requests_v1 '
            'where request_id=any(%s::uuid[])',([a['p_request']for a in args],)).fetchall()
        assert rows==[(str(users[win].auth_user_id),args[win]['p_request'],result)],rows
        assert cur.execute('select count(*)from cp7_credit.consumption_events where cohort_id=%s',
            (pair['initial_result']['credit_id'],)).fetchone()==(1,)
        actor,request=cur.execute('select actor::text,request_id::text from cp7_credit.consumer_operations_v1 where id=%s',
            (result['operation_id'],)).fetchone()
        assert (actor,request)==(str(users[win].auth_user_id),args[win]['p_request'])
        cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)',(result['operation_id'],))
        after=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',
            (pair['source']['f']['sale'],)).fetchone()[0]
        assert {k:after[k]for k in retained.PHYSICAL}=={k:before[k]for k in retained.PHYSICAL}
        assert after['payments']==before['payments']
        conn.rollback()
    credit.replay(http,users[win],args[win],result)
    credit.refused(http,users[lose],args[lose],gold['loser_error'])
    return dict(status='PASS',two_distinct_real_Auth_users=True,actual_PostgREST_commands=True,
        both_backends_observed_waiting=blocked,global_writer_lock_released_before_results=True,
        winner_auth_id=str(users[win].auth_user_id),loser_auth_id=str(users[lose].auth_user_id),
        one_request_operation_consumption_and_journal_only=True,loser_error=gold['loser_error'],
        winner_replay_zero_effect=True,loser_replay_refused_without_effect=True,
        original_payment_stock_HPP_retained=True,expected=gold['expected'],observed=actual,
        real_Auth=True,jwt_signed_by_runtime=False,product_timeouts_unchanged=True,production_go=False)


def http_cases(http,today):
    expected()
    return retained.http_cases(http,today)+[(key,lambda index=index:race(http,today,index))
        for index,key in enumerate(NEW_IDS)]
