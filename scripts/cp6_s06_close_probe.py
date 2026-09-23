"""AUD-S06 probe: accounting close versus unresolved cost-recalculation blockers.

Observation only, on the frozen AU runtime (ca7f095) installed on a disposable
clone exactly like the AU-R1 probe. No function is patched. The owner contract
(HANDOFF_UTAMA 8.10, master S06) requires one authoritative preflight and an
atomic recheck of every blocker before a period is closed; the report layer
must not show READY while recost is pending. Queue rows are administrative
fixtures (labelled), the close itself is the ordinary owner RPC.
"""
from collections import Counter
from datetime import date,timedelta
from pathlib import Path
import json,os,subprocess,sys,traceback

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import psycopg
import cp6_au_r1_probe as r1
import cp6_au_runtime as runtime
import cp6_ao_ap_installed as api
import cp6_ao_ap_runtime as prior
import cp6_successor_regression as boundary

r1.OUT=AUDITOR/'cp6-proof/s06'
QUEUE={'PENDING':('PENDING',0),'RUNNING':('RUNNING',1),'FAILED_RETRYABLE':('FAILED',1),'FAILED_EXHAUSTED':('FAILED',3)}


def find(value,key):
    if isinstance(value,dict):
        if key in value:return value[key]
        for v in value.values():
            r=find(v,key)
            if r is not None:return r
    return None


def snapshot(cur,day):
    api.ordinary(cur)
    snap=cur.execute('select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',(day,day,day)).fetchone()[0]
    api.admin(cur)
    return dict(status=find(snap,'status'),pending_cost_recalc_count=find(snap,'pending_cost_recalc_count'),
                critical_issue_count=find(snap,'critical_issue_count'),
                failed_checks=[c.get('check_name') for c in (find(snap,'failed_checks') or [])])


def close_case(cur,today,variant):
    api.admin(cur)
    target=today-timedelta(days=1)
    open_rows=cur.execute("""select status,attempt_count,count(*) from erp.cost_recalc_queue
        where status in('PENDING','RUNNING','FAILED') group by 1,2 order by 1,2""").fetchall()
    fixture=None
    if variant!='AS_IS':
        status,attempts=QUEUE[variant]
        po=cur.execute('select id from erp.production_orders order by created_at,id limit 1').fetchone()[0]
        qid=cur.execute("""insert into erp.cost_recalc_queue(entity_type,entity_id,recalc_from,reason)
            values('PO',%s,statement_timestamp(),'S06 fixture: unresolved recost before close') returning id""",(po,)).fetchone()[0]
        cur.execute('update erp.cost_recalc_queue set status=%s,attempt_count=%s where id=%s',(status,attempts,qid))
        fixture=dict(queue_id=qid,po=po,status=status,attempt_count=attempts,administrative_fixture=True)
    report_before=snapshot(cur,target)
    control_before=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
    def operation():
        api.ordinary(cur)
        cur.execute('select erp.close_accounting_through(%s,%s)',(target,'S06 close with unresolved blockers'))
        return 'CLOSED'
    result,error=r1.peer.attempt(cur,operation)
    control_after=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
    report_after=snapshot(cur,target)
    blocked=bool(report_before['status'] and report_before['status']!='READY')
    row=dict(variant=variant,target_closed_through=target,queue_open_rows_before_fixture=open_rows,fixture=fixture,
             report_before_close=report_before,close_result=result,close_refusal=error,
             closed_through_before=control_before,closed_through_after=control_after,report_after_close=report_after,
             ordinary_owner_rpc=True)
    if variant=='AS_IS':
        row['expected']='Observation of the unmodified clone: close is permitted only when no blocker is reported'
        row['status']='COUNTEREXAMPLE' if (result and blocked) else 'CONTROL_PASS'
    else:
        row['expected']='Refuse close while recost is unresolved (contract: preflight + atomic recheck); report must not be READY'
        if result:row['status']='COUNTEREXAMPLE'
        else:row['status']='PASS' if 'recost' in (error or {}).get('message','').lower() or 'recalc' in (error or {}).get('message','').lower() else 'REFUSED_OTHER_REASON'
        row['false_ready_report']=report_before['status']=='READY'
    return row


def cases(cur,today):
    return [('S06:'+v,lambda v=v:close_case(cur,today,v)) for v in ('AS_IS',*QUEUE)]


def run():
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    report=dict(status='INCOMPLETE',source=r1.source(),installed_functions_patched_for_testing=False,production_go=False,independent_acceptance=False)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        report['au_install']=runtime.change('install',boundary.PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        g=r1.group('S06_CLOSE',cases,runtime.verified)
        report['s06']={k:g[k] for k in ('status','counts')}
        report['status']='REVIEW_COMPLETE' if g['status']!='INCOMPLETE' else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_S06',report)
    print(json.dumps(dict(phase='s06',**{k:v for k,v in report.items() if k!='au_install'}),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error','S06_INCOMPLETE')


if __name__=='__main__':run()
