"""Actual two-session payment/cash-credit races; no DB work on import."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,uuid
import native_basic_cases as basic
import cp7_payment_correction_cases as correction
import consumer_race_cases as retained
native,fixture=basic.native,basic.fixture
IDS=retained.IDS+('OW04_PAYMENT_RACE_SAME_UUID_CORRECT900','OW04_PAYMENT_RACE_DISTINCT_UUID_STALE_CORRECT900',
 'OW04_PAYMENT_RACE_CONSUMER20_HOLDS_CORRECTION_STALE','OW04_PAYMENT_RACE_CORRECTION_HOLDS_CONSUMER20_STALE')


def observed(cur,pair):
    d=fixture.profiles(cur,pair);s,t=d['source'],d['target']
    return dict(source_net=s['net'],source_P=s['P'],I=s['I'],C=s['net_consumption'],available=s['available_credit'],
        source_AR=s['AR'],target_P=t['P'],target_U=t['U'],target_AR=t['AR'],cash=d['cash'])


def timeout(cur):cur.execute("set local timezone='UTC';set local lock_timeout='20s';set local statement_timeout='120s'")


def one_case(tools,today,kind):
    declaration=json.loads(Path(__file__).with_name('RACE_EXPECTED.json').read_bytes())
    gold=declaration['cases'][kind]
    with tools.connect()as conn,conn.cursor()as cur:
        timeout(cur);pair=fixture.prepare(cur,today)
        basic.apply(cur,pair,'80.00')
        intent,version=correction.payload(cur,pair['source']['f'],amount='900.00')
        envelope=basic.review(cur,basic.payload(pair,amount='20.00'))
        original_fact=correction.payment_fact(cur,pair['source']['f']['payment'])
        cur.execute('set constraints all immediate');conn.commit()
    first=uuid.uuid4();second=first if kind==0 else uuid.uuid4()
    def correct(cur,key):timeout(cur);return correction.correct(cur,deepcopy(intent),version,key)
    def consume(cur,key):timeout(cur);return basic.command(cur,deepcopy(envelope),key)
    def holder(cur):
        outcome=consume(cur,first)if kind==2 else correct(cur,first)
        actual=observed(cur,pair)
        assert actual==gold['holder_expected'],(actual,gold)
        return dict(outcome=outcome,whole=basic.observation(cur,pair))
    def worker(cur):return consume(cur,second)if kind==3 else correct(cur,second)
    held,contention,outcome=tools.two_sessions(holder,worker,True)
    assert contention==dict(kind='BLOCKED',holder_blocks_worker=True),contention
    if kind==0:assert outcome==dict(ok=True,result=held['outcome']),outcome
    else:assert outcome==dict(ok=False,sqlstate='P0001',message=gold['worker_error']),outcome
    with tools.connect()as conn,conn.cursor()as cur:
        timeout(cur);native.b.api.admin(cur)
        assert basic.observation(cur,pair)==held['whole'],'BLOCKED_WORKER_CREATED_FINANCIAL_OR_PRIVATE_EFFECTS'
        assert correction.payment_fact(cur,pair['source']['f']['payment'])==original_fact
        if kind==2:
            fresh,new_version=correction.payload(cur,pair['source']['f'],amount='900.00')
            correction.correct(cur,fresh,new_version,uuid.uuid4())
        elif kind==3:basic.apply(cur,pair,'20.00')
        actual=observed(cur,pair);assert actual==gold['final_expected'],(actual,gold)
        native.b.api.admin(cur)
        if kind in(1,2):
            assert cur.execute('select count(*)from cp7_payment_correction.requests where request_id=%s',(second,)).fetchone()[0]==0
        elif kind==3:
            assert cur.execute('select count(*)from cp7_credit.consumer_requests_v1 where request_id=%s',(second,)).fetchone()[0]==0
        for op, in cur.execute("select operation_id from cp7_credit.source_operation_materializations_v1 where sale_id=%s",(pair['source']['f']['sale'],)).fetchall():
            cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(op,))
        cur.execute('set constraints all immediate');conn.commit()
    return dict(status='PASS',two_actual_SQL_sessions=True,actual_holder_blocks_worker=True,
        authenticated_SQL_fixture_not_real_Auth=True,worker_outcome=outcome,worker_additional_effects=0,
        expected=gold['final_expected'],observed=actual,fresh_review_required_after_stale=kind in(2,3),production_go=False)


def races(tools,today):
    gold=json.loads(Path(__file__).with_name('RACE_EXPECTED.json').read_bytes())
    assert tuple(c['id']for c in gold['cases'])==IDS[2:]
    return retained.races(tools,today)+[(case['id'],lambda k=k:one_case(tools,today,k))for k,case in enumerate(gold['cases'])]
