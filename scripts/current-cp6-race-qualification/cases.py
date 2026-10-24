"""Original concurrent operations, money and lock assertions, one fresh copy each."""
from datetime import timedelta
from urllib.parse import urlparse
import traceback
import cp7_retained_cp6_fixture as fixture
CURRENT=False
import cp6_v2620af_concurrency as af
import cp6_v2620ag_concurrency as ag
import cp6_v2620ah_concurrency as ah
import cp6_v2620ai_concurrency as ai
import cp6_ai_independent_review as peer

AF=('POST_FIRST','POST_ABORT','CHILD_FIRST','DOUBLE_POST')
AG=('EDIT_FIRST','EDIT_ABORT','POST_FIRST','POST_ABORT')
AH=('ALLOCATION_MAIN_COMMIT','ALLOCATION_MAIN_ABORT','ALLOCATION_OTHER_COMMIT','ALLOCATION_OTHER_ABORT',
    'RETURN_COMMIT','RETURN_ABORT','SALE_REVERSE_COMMIT','SALE_REVERSE_ABORT')
AI=tuple(kind+'_'+ending for kind in ('HEADER_POST','POST_HEADER','CHILD_HEADER','HEADER_CHILD')for ending in ('COMMIT','ABORT'))
PEER=tuple((kind,abort)for kind in ('DOUBLE_POST','QTY_POST','POST_QTY','DELETE_POST','POST_DELETE','GROUP_TWO_POST')for abort in (False,True))
FAMILY_IDS=dict(AF=tuple('AF_'+m for m in AF),AG=tuple('AG_'+m for m in AG),AH=AH,AI=AI,
    AI_PEER=tuple('PEER_'+kind+('_ABORT'if abort else '_COMMIT')for kind,abort in PEER))
IDS=tuple(name for group in FAMILY_IDS.values()for name in group)
assert len(IDS)==len(set(IDS))==36


def races(tools,today):
    url=urlparse(tools.admin)
    assert url.hostname in ('127.0.0.1','localhost')and url.path=='/cp6_auditor_race'
    plans=[]
    plans.extend((name,'AF',mode,False,lambda m=mode:af.run_case('AF',m),2)for name,mode in zip(FAMILY_IDS['AF'],AF))
    plans.extend((name,'AG',mode,False,lambda m=mode:ag.sale_case(m),4)for name,mode in zip(FAMILY_IDS['AG'],AG))
    plans.extend((mode,'AH',mode,False,lambda m=mode:ah.run_case(m),5)for mode in AH)
    plans.extend((mode,'AI',mode,False,lambda m=mode:ai.run_case(m),5)for mode in AI)
    plans.extend((name,'AI_PEER',kind,abort,lambda k=kind,a=abort:peer.concurrent_case(k,a),5)
        for name,(kind,abort)in zip(FAMILY_IDS['AI_PEER'],PEER))
    result=[]
    for name,family,mode,abort,operation,open_days in plans:
        def run(fn=operation,f=family,m=mode,a=abort,n=name,days=open_days):
            preparation={}
            previous=af.CLONE
            af.CLONE=tools.admin
            try:
                with tools.connect()as conn,conn.cursor()as cur:
                    af.actors.admin(cur)
                    day=af.base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
                    assert day==today-timedelta(days=3),'RETAINED_RACE_BUSINESS_DAY_CHANGED'
                    af.prior.set_open_period(cur,day-timedelta(days=days))
                    fixture.prepare(cur,today,current=CURRENT,closed_through=day-timedelta(days=days),evidence=preparation)
                raw=fn()
                expected='CONTROL_PASS'if f=='AI_PEER'else 'PASS'
                assert raw['status']==expected,raw
                # Vocabulary adapter only. The original result is retained verbatim.
                return dict(status='PASS',retained_family=f,retained_case_id=n,
                    retained_mode=m,retained_first_aborted=a if f=='AI_PEER'else None,
                    original_result=raw,fixture_day=str(day),business_oracle_changed=False,
                    seed_prerequisite_preparation=preparation)
            except Exception as error:
                # The generic old race runner truncates exceptions at3000chars.
                # Retain the entire original failure and completed fixture here.
                return dict(status='INCOMPLETE',retained_case_id=n,error=str(error),
                    traceback=traceback.format_exc(),seed_prerequisite_preparation=preparation)
            finally:
                af.CLONE=previous
        result.append((name,run))
    assert tuple(name for name,_ in result)==IDS
    return result
