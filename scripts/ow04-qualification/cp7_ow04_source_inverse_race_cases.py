"""Two separately declared actual SQL-session source-inverse race proposals.

Registration/import never connects or executes SQL. The existing race harness
owns fresh disposable copies, real connection creation, exact measured lock
contention, cleanup, and restoration. No business DML, fake money/token, or
private Native hook is introduced here. Not executed by the proposal author.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import uuid

import cp7_ow04_signed_source_cases as signed
import cp7_ow04_signed_zero_difference_cases as zero

initial,native,cmd=signed.initial,signed.native,signed.cmd
ACTION='RETURN_REVERSE'
IDS=('OW04_SOURCE_RACE_SAME_UUID_RETURN_REVERSE',
     'OW04_SOURCE_RACE_DISTINCT_UUID_STALE_RETURN_REVERSE')
# Filled once from the literal declaration before any execution. This pin is
# intentionally independent from the retained signed and old-six declarations.
EXPECTED_SHA='6d1ccc9252446a2cd99b4b605fea5328e195c06cf3cb8e485bbc4544de2d8fb1'


def expected():
    raw=Path(__file__).with_name('SOURCE_RACE_EXPECTED.json').read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA,'OW04_SOURCE_RACE_DECLARATION_CHANGED'
    gold=json.loads(raw)
    assert gold['race_executed']is False and gold['native_executed']is False and gold['production_go']is False
    assert gold['case_count']==len(IDS)==2 and tuple(x['id']for x in gold['cases'])==IDS
    assert gold['required_actual_native_case_count']==63
    retained=signed.expected()
    zero.expected()
    assert gold['preserved_signed_expected_sha256']==signed.EXPECTED_SHA
    assert gold['preserved_zero_difference_expected_sha256']==zero.EXPECTED_SHA
    native_gold=next(row for row in retained['cases']if row['id']==gold['frozen_native_gold_id'])
    assert gold['before']==native_gold['before']and gold['after']==native_gold['after']
    assert native_gold['action']==ACTION and native_gold['setup_mode']=='CREDIT'
    return gold,native_gold


def assert_retained_bytes(repo):
    """Entry-point preflight; does not execute the old six races or SQL."""
    gold,_=expected()
    for path,key in (
        ('scripts/ow04-qualification/cp7_ow04_race_cases.py','preserved_old6_cases_sha256'),
        ('scripts/ow04-qualification/RACE_EXPECTED.json','preserved_old6_expected_sha256'),
    ):
        assert sha256((Path(repo)/path).read_bytes()).hexdigest()==gold[key], 'OW04_SOURCE_RACE_RETAINED_OLD6_CHANGED:'+path
    return dict(old6_cases_sha256=gold['preserved_old6_cases_sha256'],
        old6_expected_sha256=gold['preserved_old6_expected_sha256'],
        signed_expected_sha256=gold['preserved_signed_expected_sha256'],
        zero_difference_expected_sha256=gold['preserved_zero_difference_expected_sha256'])


def _sha(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def _send(cur,payload,version,request):
    cur.execute("set local lock_timeout='20s';set local statement_timeout='60s'")
    # Retained helper enters the actual authenticated SQL actor and invokes
    # ONLY public.erp_cp7_save_sale_v1, then restores the fixture admin reader.
    return cmd.command(cur,ACTION,payload,version,request)


def _prepared(tools,today,gold,native_gold):
    with tools.connect()as conn,conn.cursor()as cur:
        native.b.api.admin(cur)
        x,credit,initial_result,actual=signed._setup(cur,today,'CREDIT')
        cohort=actual['cohorts']['document'][0]['id']
        assert signed._profile(cur,x,credit,cohort)==gold['before']
        payload,version=signed._intent(cur,x,initial_result,ACTION)
        preserved=signed._preserved(cur,x,actual)
        assert zero._rows(cur,'source_operation_materializations_v1','sale_id=%s',(x['f']['sale'],))['document']==[]
        assert zero._rows(cur,'source_operation_work_v1')['document']==[]
        began=signed._business_day(cur)
        cur.execute('set constraints all immediate')
        # The worker must observe real committed setup. Do not use
        # native.isolated(): that retained Native helper always rolls back.
        conn.commit()
    return dict(x=x,credit=credit,initial_result=initial_result,actual=actual,
        payload=payload,version=version,preserved=preserved,began=began,native_gold=native_gold)


def _operation(cur,fixture,request,result,evidence,requests):
    """Exact operation/receipt counts in addition to the unchanged signed gold."""
    native.b.api.admin(cur)
    x,actual=fixture['x'],fixture['actual']
    f=x['f'];req=str(request)
    rows=cur.execute('select request_id::text,action,payload,expected_version,response from cp7_sales.requests '
        'where actor=%s and request_id=any(%s::uuid[])order by request_id',
        (signed.auth.base.OPERATOR_AUTH,list(requests))).fetchall()
    assert rows==[(req,ACTION,fixture['payload'],fixture['version'],result)],'OW04_SOURCE_RACE_DUPLICATE_OR_ORPHAN_RECEIPT'
    # A source inverse belongs to the owning sale request. It does not create
    # a second initial-settlement outer receipt under the raced UUIDs.
    assert cur.execute('select count(*)from cp7_credit.return_requests where request_id=any(%s::uuid[])',
                       (list(requests),)).fetchone()==(0,)
    operations=zero._rows(cur,'source_operation_materializations_v1','sale_id=%s',(f['sale'],))['document']
    assert len(operations)==1,'OW04_SOURCE_RACE_EXACT_ONE_OPERATION_REQUIRED'
    op=operations[0]
    assert (op['actor'],op['request_id'],op['action'],op['sale_id'],op['source_id'],
        op['expected_version'],op['payload'],str(op['operation_ordinal']),op['predecessor_operation_id'])==(
        signed.auth.base.OPERATOR_AUTH,req,ACTION,f['sale'],fixture['initial_result']['return_id'],
        fixture['version'],fixture['payload'],'1',None)
    assert isinstance(op['plan_manifest'],list)and len(op['plan_manifest'])==1
    assert op['financial_marker_id']is not None
    initial._sha(op['actual_manifest_sha256'])
    links=zero._rows(cur,'source_operation_plans_v1','operation_id=%s',(op['operation_id'],))['document']
    seals=zero._rows(cur,'source_operation_part_seals_v1','operation_id=%s',(op['operation_id'],))['document']
    completions=zero._rows(cur,'source_operation_completions_v1','operation_id=%s',(op['operation_id'],))['document']
    assert len(links)==len(seals)==len(completions)==1,'OW04_SOURCE_RACE_EXACT_SOURCE_CLOSURE_REQUIRED'
    assert links[0]['plan_id']==evidence['plan']['id']
    assert (seals[0]['plan_id'],seals[0]['component_id'],seals[0]['part_id'],seals[0]['journal_id'])==(
        evidence['plan']['id'],evidence['component']['id'],evidence['part']['id'],evidence['adjustment']['document']['header']['id'])
    initial._sha(completions[0]['final_manifest_sha256'])
    source_proof=op['actual_source_proof']
    assert (source_proof['contract_version'],source_proof['action'],source_proof['source_id'],
        source_proof['inverse_journal_id'],source_proof['additional_native_hpp_sync_effects'])==(
        'ow04.native-source-inverse-proof.v1',ACTION,fixture['initial_result']['return_id'],
        evidence['source_inverse']['document']['header']['id'],0)
    # The sealed rows above use Native's exact-decimal JSON parser. Read the
    # current snapshot through that same parser: psycopg's default JSON decoder
    # converts numeric JSON to float and cannot equal an exact-decimal snapshot.
    current_source=native._raw(cur,'select cp7_credit.source_native_snapshot_v1(%s)',
                              (f['sale'],))['document']
    # Raw events/versions/corrections must remain exact in the actual B/N/Z
    # seals AND a fresh current table read. HPP book vectors legitimately
    # change by the proven source inverse; do not compare those as unchanged.
    for key in ('hpp_versions','opening_hpp_corrections','nonpo_hpp_events','po_hpp_events',
                'opening_hpp_states','po_hpp_states','hpp_accounts','period_snapshot'):
        assert op['before_source'][key]==op['actual_source'][key]==completions[0]['final_native_source'][key]==current_source[key], (
            'OW04_SOURCE_RACE_ADDITIONAL_NATIVE_HPP_EFFECT',key)
    markers=zero._rows(cur,'financial_materializations','actor=%s and request_id=%s',
                      (signed.auth.base.OPERATOR_AUTH,request))['document']
    assert len(markers)==1 and markers[0]['id']==op['financial_marker_id']
    assert zero._rows(cur,'source_operation_work_v1')['document']==[]
    assert zero._rows(cur,'execution_context')['document']==[]
    assert native._array(cur,'cp7_sales.command_context','true',())['document']==[]
    assert result['row_version']==str(int(fixture['version'])+1)
    # Preserve all initial settlement and original-recognition facts, proven
    # also by the retained exact journal/vector/stock/payment assertions.
    cohort=actual['cohorts']['document'][0]
    assert zero._rows(cur,'consumption_events','cohort_id=%s',(cohort['id'],))['document']==[]
    return dict(operation_id=op['operation_id'],operation_count=1,completion_count=1,
        operation_plan_link_count=1,operation_part_seal_count=1,raced_request_count=1,
        operation_sha256=_sha(op),completion_sha256=_sha(completions[0]),
        source_inverse_journal_sha256=evidence['source_inverse']['sha256'],
        adjustment_journal_sha256=evidence['adjustment']['sha256'])


def _winner(cur,fixture,request,result,requests):
    signed._assert_same_business_day(cur,fixture['began'])
    signed._assert_request(cur,ACTION,fixture['payload'],fixture['version'],request,result)
    evidence=signed._assert_positive(cur,fixture['x'],fixture['credit'],fixture['initial_result'],
        fixture['actual'],fixture['native_gold'],request,result,fixture['preserved'])
    source=_operation(cur,fixture,request,result,evidence,requests)
    cur.execute('set constraints all immediate')
    return evidence,source


def _race(tools,today,kind,gold,native_gold):
    fixture=_prepared(tools,today,gold,native_gold)
    payload=deepcopy(fixture['payload']);version=fixture['version']
    first=uuid.uuid4();second=first if kind=='SAME_UUID'else uuid.uuid4()
    assert (first==second)==(kind=='SAME_UUID')
    requests=(first,second)
    def holder(cur):
        result=_send(cur,payload,version,first)
        _,proof=_winner(cur,fixture,first,result,requests)
        complete=signed._observe(cur,fixture['x'])
        return dict(result=result,proof=proof,complete_state=complete,
            holder_backend_pid=cur.execute('select pg_backend_pid()').fetchone()[0])
    held,contention,outcome=tools.two_sessions(holder,
        lambda cur:_send(cur,deepcopy(payload),version,second),True)
    assert contention==dict(kind='BLOCKED',holder_blocks_worker=True),contention
    if kind=='SAME_UUID':
        assert outcome==dict(ok=True,result=held['result']),'OW04_SOURCE_RACE_REPLAY_OUTCOME_CHANGED'
    else:
        assert outcome==dict(ok=False,sqlstate='P0001',message='CP7_SALES_REVIEW_CHANGED'),outcome
    assert payload==fixture['payload'],'OW04_SOURCE_RACE_REVIEWED_INTENT_MUTATED'
    with tools.connect()as conn,conn.cursor()as cur:
        evidence,proof=_winner(cur,fixture,first,held['result'],requests)
        after=signed._observe(cur,fixture['x'])
        assert after==held['complete_state'],'OW04_SOURCE_RACE_WORKER_ADDED_BUSINESS_OR_PRIVATE_EFFECT'
        # Demand absent loser request explicitly even though the whole-state
        # equality already covers it. Any alternate refusal is a failure.
        if kind!='SAME_UUID':
            assert cur.execute('select count(*)from cp7_sales.requests where actor=%s and request_id=%s',
                (signed.auth.base.OPERATOR_AUTH,second)).fetchone()==(0,)
            assert zero._rows(cur,'source_operation_materializations_v1','actor=%s and request_id=%s',
                (signed.auth.base.OPERATOR_AUTH,second))['document']==[]
        # A fresh actual reader sees the holder's updated version and token;
        # no new token is manufactured to make the losing request pass.
        fresh,fresh_version=cmd.review(cur,fixture['x']['f'])
        assert fresh_version==held['result']['row_version']and fresh_version!=version
        assert fresh['review_token']!=payload['review_token']
        assert signed._observe(cur,fixture['x'])==after,'OW04_SOURCE_RACE_FRESH_REVIEW_MUTATED_STATE'
        signed._assert_same_business_day(cur,fixture['began'])
        conn.rollback()
    return dict(status='PASS',classification='ACTUAL_PUBLIC_SQL_SOURCE_INVERSE_RACE_ONLY_WHEN_RUN',
        two_actual_SQL_sessions=True,authenticated_SQL_fixture_not_real_Auth=True,
        actual_holder_blocks_worker=True,holder_committed=True,kind=kind,
        holder_request_id=str(first),worker_request_id=str(second),holder_backend_pid=held['holder_backend_pid'],
        actual_outcome=held['result'],actual_worker=outcome,actual_profile=evidence['actual_profile'],
        identical_committed_replay=kind=='SAME_UUID',loser_request_absent=kind!='SAME_UUID',
        worker_additional_effects=0,complete_final_state_sha256=_sha(after),
        final_state_equals_complete_holder_state=True,exact_unchanged_signed_native_oracles=True,
        **proof,production_go=False,independent_acceptance=False)


def races(tools,today):
    """Pure registration in existing modes.run_races; SQL stays deferred."""
    gold,native_gold=expected()
    return [(IDS[0],lambda:_race(tools,today,'SAME_UUID',gold,native_gold)),
            (IDS[1],lambda:_race(tools,today,'DISTINCT_UUID',gold,native_gold))]
