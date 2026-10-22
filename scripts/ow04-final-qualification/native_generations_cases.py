"""Two literal four-generation journeys; no new cohort support is claimed."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,uuid

import native_basic_cases as basic
import native_refund_cases as refund
import cp7_payment_correction_cases as correction

EXPECTED_SHA256='8c7ef442fb93eeb3de1392408c4d764acc7b707e4957d713921ddd01ffc7574c'


def expected():
    raw=Path(__file__).with_name('EXPECTED_GENERATIONS.json').read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA256
    return json.loads(raw)


IDS=tuple(row['id']for row in expected()['cases'])


def money(cur,pair):
    a=basic.fixture.profiles(cur,pair);s,t=a['source'],a['target']
    return dict(source_net=s['net'],source_P=s['P'],I=s['I'],C=s['net_consumption'],available=s['available_credit'],
        source_AR=s['AR'],target_P=t['P'],target_U=t['U'],target_AR=t['AR'],cash=a['cash'])


def one_case(cur,today,index):
    with basic.native.isolated(cur):
        gold=expected()['cases'][index]
        pair=basic.fixture.prepare(cur,today);source=pair['source']['f']
        use=basic.apply if gold['mode']=='APPLY'else refund.refund
        first,_,_=use(cur,pair,'80.00');consumers=[first]
        original_journals={first['journal_id']:basic.native.journal(cur,first['journal_id'])}
        physical=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(source['sale'],)).fetchone()[0]
        current=str(source['payment']);records=[];facts={};observations=[]
        for generation,amount in enumerate(expected()['correction_amounts']):
            if generation==1:
                second,_,_=use(cur,pair,'20.00');consumers.append(second)
                original_journals[second['journal_id']]=basic.native.journal(cur,second['journal_id'])
            p,version=correction.payload(cur,source,amount=amount,payment_id=current);request=uuid.uuid4()
            answer=correction.correct(cur,p,version,request)
            cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
            assert answer['original_payment_id']==current and answer['payment_id']!=current
            facts[current]=correction.payment_fact(cur,current)
            records.append((deepcopy(p),version,request,answer));current=answer['payment_id']
            actual=money(cur,pair)
            selected=dict(P=actual['source_P'],I=actual['I'],C=actual['C'],available=actual['available'])
            assert selected==gold['after_each'][generation],(generation,selected,gold['after_each'][generation])
            observations.append(dict(generation=generation+1,expected=gold['after_each'][generation],observed=selected))
            basic.native.b.api.admin(cur)
            snapshot=cur.execute('select cp7_credit.source_native_snapshot_v1(%s)',(source['sale'],)).fetchone()[0]
            for key in ('items','allocations','returns','return_items','fg_lots','hpp_versions','stock_movements',
                        'inventory_balances','opening_hpp_states','opening_hpp_corrections','po_hpp_states','po_hpp_events',
                        'nonpo_hpp_events','hpp_journals','hpp_balances'):
                assert snapshot[key]==physical[key],('CORRECTION_GENERATION_CHANGED_STOCK_HPP',generation,key)
            for payment,original in facts.items():assert correction.payment_fact(cur,payment)==original
        before=basic.observation(cur,pair)
        for p,version,request,answer in records:assert correction.correct(cur,p,version,request)==answer
        assert basic.observation(cur,pair)==before,'FOUR_GENERATION_REPLAY_CREATED_EXTRA_EFFECT'
        for consumer in reversed(consumers):
            p=basic.payload(pair,'UNDO',original=consumer['consumption_event_id'])
            inverse=basic.command(cur,basic.review(cur,p),uuid.uuid4())
            assert inverse['restores_event_id']==consumer['consumption_event_id']
        p,version=basic.fixture.signed._intent(cur,pair['source'],pair['initial_result'],'RETURN_REVERSE')
        basic.native.cmd.command(cur,'RETURN_REVERSE',p,version,uuid.uuid4())
        cur.execute('set constraints all immediate')
        observed=money(cur,pair)
        assert observed==gold['final_after_named_undos_and_return_inverse'],(observed,gold)
        for journal,original in original_journals.items():assert basic.native.journal(cur,journal)==original
        for payment,original in facts.items():assert correction.payment_fact(cur,payment)==original
        return dict(status='PASS',id=gold['id'],correction_generations=4,source_cohort_count=1,
            correction_generation_observations=observations,
            four_original_receipts_replayed_once=True,original_payment_and_consumer_journals_retained=True,
            stock_HPP_unchanged_by_each_payment_correction=True,observed=observed,
            multiple_distinct_return_cohorts_qualified=False,production_go=False)


def cases(cur,today):return [(key,lambda index=index:one_case(cur,today,index))for index,key in enumerate(IDS)]
