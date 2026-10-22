"""Two rollback-only, single-session Native timing observations.

pg_stat_xact_user_functions excludes other sessions/background reads and is
read immediately around each actual reviewed command plus deferred closure.
The observations do not qualify browser latency or change product budgets.
"""
from copy import deepcopy
from pathlib import Path
import json,time,uuid
import native_basic_cases as basic
import cp7_payment_correction_cases as payment

IDS=('OW04_CURRENT_ISOLATED_TIMING_DEFAULT_JIT','OW04_CURRENT_ISOLATED_TIMING_JIT_OFF')
GOLD=json.loads((Path(__file__).resolve().parents[1]/'ow04-payment-browser-races-qualification/RACE_EXPECTED.json').read_bytes())['cases'][3]['final_expected']


def counters(cur):
    return {name:dict(calls=calls,total_ms=total,self_ms=own)for name,calls,total,own in cur.execute(
        "select f.funcid::regprocedure::text,f.calls,f.total_time,f.self_time "
        "from pg_stat_xact_user_functions f join pg_proc p on p.oid=f.funcid "
        "join pg_namespace n on n.oid=p.pronamespace "
        "where n.nspname='erp'or n.nspname like 'cp7_%'or n.nspname like 'ow04_%'").fetchall()}


def measured(cur,label,operation):
    before=counters(cur);started=time.perf_counter();result=operation()
    elapsed=(time.perf_counter()-started)*1000;after=counters(cur)
    rows=[]
    for name,row in after.items():
        previous=before.get(name,dict(calls=0,total_ms=0,self_ms=0))
        delta=dict(name=name,**{k:row[k]-previous[k]for k in row})
        if delta['calls']:rows.append(delta)
    return result,dict(label=label,elapsed_ms=elapsed,functions=rows,
        top_self=sorted(rows,key=lambda r:r['self_ms'],reverse=True)[:30],
        top_total=sorted(rows,key=lambda r:r['total_ms'],reverse=True)[:30],
        exact_single_SQL_session_transaction_counters=True,
        includes_concurrent_background_sessions=False,performance_acceptance=False)


def one_case(cur,today,index):
    with basic.native.isolated(cur):
        assert cur.execute('show track_functions').fetchone()[0]=='all'
        original_jit=cur.execute('show jit').fetchone()[0]
        if index:cur.execute('set local jit=off')
        pair=basic.fixture.prepare(cur,today);basic.apply(cur,pair,'80.00')
        down,version=payment.payload(cur,pair['source']['f'],amount='900.00')
        def correct():
            answer=payment.correct(cur,down,version,uuid.uuid4())
            cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
            return answer
        _,correction=measured(cur,'CORRECTION900_CLOSED_COMMAND',correct)
        envelope,quote=measured(cur,'CONSUMER20_QUOTE',lambda:basic.review(cur,basic.payload(pair,amount='20.00')))
        _,consumer=measured(cur,'CONSUMER20_CLOSED_COMMAND',lambda:basic.command(cur,deepcopy(envelope),uuid.uuid4()))
        values=basic.fixture.profiles(cur,pair);s,t=values['source'],values['target']
        actual=dict(source_net=s['net'],source_P=s['P'],I=s['I'],C=s['net_consumption'],available=s['available_credit'],
            source_AR=s['AR'],target_P=t['P'],target_U=t['U'],target_AR=t['AR'],cash=values['cash'])
        assert actual==GOLD
        cur.execute('set constraints all immediate')
        return dict(status='PASS',diagnostic_observation_only=True,
            original_jit=original_jit,observed_jit=cur.execute('show jit').fetchone()[0],
            timings=[correction,quote,consumer],expected=GOLD,observed=actual,
            actual_Native_writers=True,real_Auth_or_browser_latency=False,
            application_8s_budget_unchanged=True,production_go=False)


def cases(cur,today):
    return [(key,lambda index=index:one_case(cur,today,index))for index,key in enumerate(IDS)]
