"""Two actual SQL-session consumer races; declarations are not execution.

The generic closed race harness owns real connections, observed blocking,
commits and fresh template copies. SQL authenticated fixtures are explicitly
distinct from real Auth/PostgREST evidence. No direct financial DML is used.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import uuid

import native_basic_cases as basic

fixture,native=basic.fixture,basic.native
IDS=('OW04_CONSUMER_RACE_SAME_UUID_APPLY','OW04_CONSUMER_RACE_DISTINCT_UUID_STALE_APPLY')
EXPECTED_SHA256='84239b6828a8f60617edb65fdb25fc83e8882699b39f62453922dcfabc69308e'


def expected():
    raw=Path(__file__).with_name('RACE_EXPECTED.json').read_bytes()
    assert EXPECTED_SHA256 is not None and sha256(raw).hexdigest()==EXPECTED_SHA256
    value=json.loads(raw)
    assert value['classification']=='PREDECLARED_SQL_CONSUMER_RACES_NOT_EXECUTED_NOT_REAL_AUTH'
    assert value['expected_count']==len(IDS)==2 and tuple(r['id']for r in value['cases'])==IDS
    assert value['original_consumer_nine_sha256']==fixture.EXPECTED_SHA256
    assert value['expected_after']==basic.GOLD['cases'][0]['expected']
    return value


def send(cur,envelope,request):
    cur.execute("set local timezone='UTC';set local lock_timeout='20s';set local statement_timeout='60s'")
    return basic.command(cur,deepcopy(envelope),request)


def observe(cur,pair):
    cur.execute("set local timezone='UTC'")
    return basic.observation(cur,pair)


def race(tools,today,same_uuid):
    gold=expected()
    with tools.connect()as conn,conn.cursor()as cur:
        pair=fixture.prepare(cur,today)
        envelope=basic.review(cur,basic.payload(pair))
        cur.execute('set constraints all immediate');conn.commit()
    original=deepcopy(envelope);first=uuid.uuid4();second=first if same_uuid else uuid.uuid4()
    def holder(cur):
        result=send(cur,envelope,first)
        assert fixture.profiles(cur,pair)==gold['expected_after']
        complete=observe(cur,pair)
        return dict(result=result,complete=complete,pid=cur.execute('select pg_backend_pid()').fetchone()[0])
    held,contention,outcome=tools.two_sessions(holder,lambda cur:send(cur,envelope,second),True)
    assert contention==dict(kind='BLOCKED',holder_blocks_worker=True),contention
    if same_uuid:
        assert outcome==dict(ok=True,result=held['result']),outcome
    else:
        assert outcome==dict(ok=False,sqlstate='P0001',message='CP7_CREDIT_CONSUMER_REVIEW_CHANGED'),outcome
    assert envelope==original,'RACE_CHANGED_ORIGINAL_REVIEWED_ENVELOPE'
    with tools.connect()as conn,conn.cursor()as cur:
        native.b.api.admin(cur)
        after=observe(cur,pair)
        assert after==held['complete'],'RACE_WORKER_CHANGED_BUSINESS_OR_PRIVATE_FACTS'
        actor=native.auth.base.OPERATOR_AUTH
        requests=cur.execute('select request_id::text,response from cp7_credit.consumer_requests_v1 where actor=%s and request_id=any(%s::uuid[])order by request_id',
                             (actor,[first,second])).fetchall()
        assert requests==[(str(first),held['result'])],requests
        operations=cur.execute('select id,request_id::text from cp7_credit.consumer_operations_v1 where actor=%s and request_id=any(%s::uuid[])',
                               (actor,[first,second])).fetchall()
        assert operations==[(uuid.UUID(held['result']['operation_id']),str(first))],operations
        assert cur.execute('select count(*)from cp7_credit.consumption_events where cohort_id=%s',(pair['initial_result']['credit_id'],)).fetchone()==(1,)
        cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)',(held['result']['operation_id'],))
        actual=fixture.profiles(cur,pair);assert actual==gold['expected_after']
        fresh=basic.review(cur,basic.payload(pair))
        assert fresh['versions']==held['result']['invoice_versions']and fresh['versions']!=envelope['versions']
        assert fresh['payload']['quote_sha256']!=envelope['payload']['quote_sha256']
        assert observe(cur,pair)==after,'FRESH_REVIEW_AFTER_RACE_CHANGED_STATE'
        conn.rollback()
    return dict(status='PASS',two_actual_SQL_sessions=True,authenticated_SQL_fixture_not_real_Auth=True,
        actual_holder_blocks_worker=True,holder_committed=True,same_UUID=same_uuid,
        holder_request_id=str(first),worker_request_id=str(second),holder_backend_pid=held['pid'],
        actual_worker=outcome,actual_outcome=held['result'],expected=gold['expected_after'],observed=actual,
        complete_holder_state_equals_final=True,worker_additional_effects=0,
        final_state_sha256=sha256(json.dumps(after,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest(),
        production_go=False,independent_acceptance=False)


def races(tools,today):
    expected()
    return [(IDS[0],lambda:race(tools,today,True)),(IDS[1],lambda:race(tools,today,False))]
