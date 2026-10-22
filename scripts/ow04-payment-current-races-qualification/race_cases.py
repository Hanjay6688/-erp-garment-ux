"""Retain six actual SQL races; add two positive replacement races.

Fixtures use authenticated SQL sessions, not real Auth/PostgREST. Every
financial write goes through the existing Native/public command writers.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util,json,uuid
import native_basic_cases as basic
import cp7_payment_correction_cases as correction

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
spec=importlib.util.spec_from_file_location('current_retained_payment_races',ROOT/'ow04-payment-browser-races-qualification/race_cases.py')
retained=importlib.util.module_from_spec(spec);spec.loader.exec_module(retained)
IDS=retained.IDS+('OW04_CURRENT_RACE_SAME_UUID_RESTORE1000',
 'OW04_CURRENT_RACE_DISTINCT_UUID_STALE_RESTORE1000')
EXPECTED_SHA256='f837affc7051f41a4c0e07c305e21235458bbf60a7e081791e6e9da611a64c7e'


def expected():
    raw=(HERE/'EXPECTED.json').read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA256
    gold=json.loads(raw)
    assert sha256((ROOT/'ow04-payment-browser-races-qualification/RACE_EXPECTED.json').read_bytes()).hexdigest()==gold['retained6_sha256']
    assert gold['expected_count']==len(IDS)==len(set(IDS))==8
    assert tuple(row['id']for row in gold['positive_restore_cases'])==IDS[6:]
    return gold


def positive(tools,today,index):
    gold=expected()['positive_restore_cases'][index]
    with tools.connect()as conn,conn.cursor()as cur:
        retained.timeout(cur);pair=basic.fixture.prepare(cur,today)
        basic.apply(cur,pair,'80.00')
        source=pair['source']['f']
        intent,version=correction.payload(cur,source,amount='900.00')
        lowered=correction.correct(cur,intent,version,uuid.uuid4())
        basic.apply(cur,pair,'20.00')
        up,version_up=correction.payload(cur,source,amount='1000.00',payment_id=lowered['payment_id'])
        p0=correction.payment_fact(cur,source['payment'])
        p9=correction.payment_fact(cur,lowered['payment_id'])
        cur.execute('set constraints all immediate');conn.commit()
    first=uuid.uuid4();second=first if gold['same_UUID']else uuid.uuid4()
    def send(cur,key):
        retained.timeout(cur)
        return correction.correct(cur,deepcopy(up),version_up,key)
    def holder(cur):
        result=send(cur,first)
        assert retained.observed(cur,pair)==gold['expected']
        # Complete deferred proofs must pass before the holder waits, and
        # remain active for the commit and the worker's actual replay.
        cur.execute('set constraints all immediate')
        return dict(result=result,whole=basic.observation(cur,pair))
    held,contention,outcome=tools.two_sessions(holder,lambda cur:send(cur,second),True)
    assert contention==dict(kind='BLOCKED',holder_blocks_worker=True),contention
    if gold['same_UUID']:
        assert outcome==dict(ok=True,result=held['result']),outcome
    else:
        assert outcome==dict(ok=False,sqlstate='P0001',message=gold['worker_error']),outcome
    with tools.connect()as conn,conn.cursor()as cur:
        retained.timeout(cur);basic.native.b.api.admin(cur)
        assert basic.observation(cur,pair)==held['whole'],'POSITIVE_RACE_WORKER_CREATED_ADDITIONAL_EFFECTS'
        assert correction.payment_fact(cur,source['payment'])==p0
        assert correction.payment_fact(cur,lowered['payment_id'])==p9
        requests=cur.execute('select request_id::text,response from cp7_payment_correction.requests where request_id=any(%s::uuid[])order by request_id',([first,second],)).fetchall()
        assert requests==[(str(first),held['result'])],requests
        for op, in cur.execute('select operation_id from cp7_credit.source_operation_materializations_v1 where sale_id=%s',(source['sale'],)).fetchall():
            cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(op,))
        actual=retained.observed(cur,pair);assert actual==gold['expected']
        assert correction.correct(cur,deepcopy(up),version_up,first)==held['result']
        assert basic.observation(cur,pair)==held['whole']
        cur.execute('set constraints all immediate');conn.rollback()
    return dict(status='PASS',two_actual_SQL_sessions=True,
        authenticated_SQL_fixture_not_real_Auth=True,actual_holder_blocks_worker=True,
        holder_committed=True,same_UUID=gold['same_UUID'],worker_outcome=outcome,
        one_replacement_and_one_request_only=True,worker_additional_effects=0,
        original_P1000_P900_facts_retained=True,all_source_operations_closed=True,
        expected=gold['expected'],observed=actual,production_go=False)


def races(tools,today):
    expected()
    return retained.races(tools,today)+[(key,lambda index=index:positive(tools,today,index))for index,key in enumerate(IDS[6:])]
