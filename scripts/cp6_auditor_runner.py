"""Strict case group of the auditor runtime (independent audit B1 / CP6-10, 25 Sep 2026).

The shared probe group (scripts/cp6_au_r1_probe.py group) let a scenario overwrite a result with a duplicate case id,
turned a status outside the vocabulary into a green group, and could not see a commit to the public schema through a
second connection or an advisory lock left behind. The auditor runtime therefore runs its savepoint cases through this
group instead (the writer's own probes keep theirs):
  * duplicate case ids refuse the whole group before any case runs;
  * a case status must be PASS, FAIL, COUNTEREXAMPLE or INCOMPLETE (anything else, or a result that is not a dict, is
    INCOMPLETE with the original value recorded);
  * after each case (savepoint rolled back): the ERP/platform/Auth/schema-ACL boundary as before, plus the data and
    catalog of the public schema, no advisory lock of the runner's session and no other client session on the clone
    that was not there before the case; a leak makes the case INCOMPLETE (the lock is released and the leaked session
    ended so later cases start clean);
  * the planned case ids and the final status of each are printed at the end, and every planned id must have one.
The rest is the shared group unchanged (seed, schema usage grant, open period 2026-08-31, function/ACL pins).
"""
from collections import Counter
from datetime import date
import json,time,traceback
import psycopg
from psycopg import sql

import cp6_aw_probe as awp
from cp6_ao_ap_inventory import function_pins

r1,api,boundary=awp.r1,awp.api,awp.boundary
VOCABULARY=('PASS','FAIL','COUNTEREXAMPLE','INCOMPLETE')

PUBLIC_STATE="""select jsonb_build_object(
  'relations',(select coalesce(jsonb_agg(jsonb_build_array(c.relname,c.relkind) order by c.relname),'[]'::jsonb)
    from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind in('r','p','v','m','S','f')),
  'functions',(select coalesce(jsonb_agg(jsonb_build_array(p.oid::regprocedure::text,md5(pg_get_functiondef(p.oid))) order by 1),'[]'::jsonb)
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prokind in('f','p')))"""


def duplicate_ids(ids):
    counts=Counter(ids)
    return sorted(k for k,n in counts.items() if n>1)


def public_state(cur):
    """Catalog of the public schema and a hash of every public table's rows (read inside the runner's transaction; a
    commit by another connection is visible to the next statement)."""
    state=cur.execute(PUBLIC_STATE).fetchone()[0]
    rows={}
    for (name,) in cur.execute("""select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
        where n.nspname='public' and c.relkind in('r','p') order by 1""").fetchall():
        rows[name]=cur.execute(sql.SQL("select count(*)::text||':'||md5(coalesce(string_agg(md5(t::text),',' order by md5(t::text)),'')) from public.{} t")
                               .format(sql.Identifier(name))).fetchone()[0]
    state['rows']=rows
    return state


ADVISORY="""select coalesce(jsonb_agg(jsonb_build_array(classid::text,objid::text,objsubid,mode) order by classid,objid,objsubid,mode),'[]'::jsonb)
  from pg_locks where locktype='advisory' and pid=pg_backend_pid() and granted"""


def other_sessions(cur):
    # pg_stat_activity is read once per transaction and cached; the runner's cases share one transaction, so the cache is
    # cleared before every read.
    cur.execute('select pg_stat_clear_snapshot()')
    return cur.execute("""select pid,usename,application_name,state from pg_stat_activity
        where datname=current_database() and pid<>pg_backend_pid() and backend_type='client backend' order by pid""").fetchall()


def session_state(cur):
    """Advisory locks the runner's session holds and the other client sessions, read before a case. The runner's own
    transaction keeps the transaction-level locks its setup took; a case's own transaction-level locks go with the
    savepoint rollback, so a lock that is new after the case is a session-level lock the case left behind."""
    return dict(advisory=cur.execute(ADVISORY).fetchone()[0],sessions=[r[0] for r in other_sessions(cur)])


def leaks(cur,before):
    """Advisory locks and other client sessions that are new since before the case; both are cleared after being
    recorded. A connection a case closed can stay listed for a moment while its backend exits, so the list is re-read
    for up to 2 s before a session counts as left open."""
    locks=[l for l in cur.execute(ADVISORY).fetchone()[0] if l not in before['advisory']]
    def new_sessions():return [o for o in other_sessions(cur) if o[0] not in before['sessions']]
    others=new_sessions()
    for _ in range(20):
        if not others:break
        time.sleep(0.1);others=new_sessions()
    if locks:cur.execute('select pg_advisory_unlock_all()')
    for pid,*_ in others:cur.execute('select pg_terminate_backend(%s)',(pid,))
    return dict(advisory_locks=len(locks),advisory_lock_keys=locks,other_sessions=[list(map(str,o)) for o in others])


def strict_group(name,factory,verify):
    report=dict(status='INCOMPLETE',cases={},production_go=False,independent_acceptance=False,runner='cp6_auditor_runner.strict_group')
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        report['runtime_before']=verify(cur)
        initial=boundary.snapshot(cur);catalog=function_pins(cur);public_initial=public_state(cur)
        if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:cur.execute('grant usage on schema erp to authenticated')
        if not initial['erp']['app_users']['count']:api.seed(cur)
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        boundary.historical.prior.set_open_period(cur,date(2026,8,31))
        cases=factory(cur,today)
        planned=[k for k,_ in cases]
        report['planned_case_ids']=planned
        duplicates=duplicate_ids(planned)
        if duplicates:
            report.update(error='AUDITOR_DUPLICATE_CASE_IDS',duplicate_case_ids=duplicates)
            print(json.dumps(dict(group=name,refused='AUDITOR_DUPLICATE_CASE_IDS',duplicates=duplicates)),flush=True)
            conn.rollback();r1.save(name,report);return report
        report['session_at_start']=session_state(cur)
        for key,operation in cases:
            before=boundary.snapshot(cur);public_before=public_state(cur);session_before=session_state(cur)
            cur.execute('savepoint auditor_case')
            ended=None
            try:
                row=operation()
                if not isinstance(row,dict):row=dict(status='INCOMPLETE',error='AUDITOR_CASE_RESULT_NOT_A_DICT',result=repr(row)[:500])
            except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:
                # Round 9, W4: a case that commits or rolls back the group transaction removes the savepoint; the group
                # records that case as a structured INCOMPLETE and stops (what it committed cannot be undone here), instead
                # of crashing on the missing savepoint.
                try:
                    cur.execute('rollback to savepoint auditor_case');api.admin(cur);cur.execute('release savepoint auditor_case')
                except psycopg.Error as exc:
                    ended=str(exc).splitlines()[0][:300];conn.rollback()
            if ended is not None:
                row=dict(status='INCOMPLETE',error='AUDITOR_CASE_ENDED_GROUP_TRANSACTION',detail=ended,case_status=row.get('status'))
                report['cases'][key]=row;report['error']='AUDITOR_CASE_ENDED_GROUP_TRANSACTION';r1.save(name,report)
                print(json.dumps(dict(group=name,case=key,**row),default=str),flush=True)
                break
            if row.get('status') not in VOCABULARY:
                row['status_outside_vocabulary']=row.get('status');row['status']='INCOMPLETE'
            row['full_boundary_restored']=boundary.snapshot(cur)==before
            row['public_schema_unchanged']=public_state(cur)==public_before
            row['session_leaks']=leaks(cur,session_before)
            clean=not row['session_leaks']['advisory_locks'] and not row['session_leaks']['other_sessions']
            if not (row['full_boundary_restored'] and row['public_schema_unchanged'] and clean):row['status']='INCOMPLETE'
            report['cases'][key]=row;r1.save(name,report)
            print(json.dumps(dict(group=name,case=key,**row),default=str),flush=True)
        if report.get('error')!='AUDITOR_CASE_ENDED_GROUP_TRANSACTION':
            assert function_pins(cur)==catalog,'AUDITOR_CASE_FUNCTION_OR_ACL_MUTATION'
        else:report['catalog_unchanged']=function_pins(cur)==catalog
        conn.rollback();report['runtime_after']=verify(cur)
        report['complete_boundary_restored']=boundary.snapshot(cur)==initial and public_state(cur)==public_initial
        conn.rollback()
    final={k:v['status'] for k,v in report['cases'].items()}
    report['final']=final
    report['counts']=dict(Counter(final.values()))
    missing=[k for k in planned if k not in final]
    report['missing']=missing
    bad=report['counts'].get('INCOMPLETE') or report['counts'].get('FAIL') or missing or not report['complete_boundary_restored'] or report.get('error')
    report['status']='INCOMPLETE' if bad else 'COUNTEREXAMPLE' if report['counts'].get('COUNTEREXAMPLE') else 'PASS'
    print(json.dumps(dict(group=name,planned=planned,final=final,missing=missing,status=report['status'])),flush=True)
    r1.save(name,report);return report
