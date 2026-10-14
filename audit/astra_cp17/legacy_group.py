"""Preserve historical oracle/status while adding per-case boundary and leak proof.

Copied lifecycle of cp6_av_trial.group, adapted ONLY to an already-installed
P21 FULL runtime, public catalog/locks/sessions/date guards and early plan save.
No expected outcome, case operation or original result vocabulary is changed.
"""
from collections import Counter
from datetime import date
import json,traceback
import psycopg
import cp6_auditor_runner as native
import cp6_auditor_business_day as day
import cp6_av_trial as avt
from cp6_ao_ap_inventory import function_pins
import full_stack

def group(name,factory):
    report=dict(status='INCOMPLETE',stage='CP17_FULL_COMPOSITION',cases={},production_go=False,
                independent_acceptance=False,oracle_origin='FROZEN_LEGACY_UNCHANGED',
                fixture_origin='CANDIDATE_T2_REVIEWED_ADAPTER',**full_stack.identity())
    avt.save(name,report)
    with psycopg.connect(avt.ADMIN) as conn,conn.cursor() as cur:
        report['runtime_before']=full_stack.composition.verify(cur)
        initial=avt.predecessor.snapshot(cur);catalog=function_pins(cur);public_initial=native.public_state(cur)
        if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:
            cur.execute('grant usage on schema erp to authenticated')
        if not initial['erp']['app_users']['count']:avt.api.seed(cur)
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        today=day.wib_day(cur)
        avt.predecessor.historical.prior.set_open_period(cur,date(2026,8,31))
        cases=factory(cur,today);planned=[k for k,_ in cases]
        report['planned_case_ids']=planned
        assert not native.duplicate_ids(planned),('CP17_DUPLICATE_CASE_IDS',planned)
        avt.save(name,report)  # Manifest BEFORE the first operation.
        for key,operation in cases:
            before=avt.predecessor.snapshot(cur);public_before=native.public_state(cur)
            sessions=native.session_state(cur);before_day=day.wib_day(cur)
            actor_before=cur.execute("select current_user,current_setting('request.jwt.claims',true)").fetchone()
            cur.execute('savepoint av_case')
            ended=None
            try:
                row=operation()
                assert isinstance(row,dict),'CP17_LEGACY_RESULT_NOT_A_DICT'
                raw_status=row.get('status')
            except Exception as exc:
                row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                raw_status='INCOMPLETE'
            finally:
                try:
                    cur.execute('rollback to savepoint av_case');avt.api.admin(cur);cur.execute('release savepoint av_case')
                except psycopg.Error as exc:
                    ended=str(exc);conn.rollback()
            row['original_case_status']=raw_status
            row['session_at_case_start']=actor_before
            if ended:
                row.update(status='INCOMPLETE',harness_error='CASE_ENDED_GROUP_TRANSACTION',detail=ended)
                report['cases'][key]=row;report['error']='CASE_ENDED_GROUP_TRANSACTION';avt.save(name,report)
                print(json.dumps(dict(group=name,case=key,**row),default=str),flush=True)
                break
            row['full_boundary_restored']=avt.predecessor.snapshot(cur)==before
            row['public_schema_unchanged']=native.public_state(cur)==public_before
            row['session_leaks']=native.leaks(cur,sessions)
            clean=row['full_boundary_restored'] and row['public_schema_unchanged'] and not (
                row['session_leaks']['advisory_locks'] or row['session_leaks']['other_sessions'])
            if not clean:
                row.update(status='INCOMPLETE',harness_check_failed=True)
            day.guard(row,today,before_day,day.wib_day(cur))
            report['cases'][key]=row;avt.save(name,report)
            print(json.dumps(dict(group=name,case=key,**row),default=str),flush=True)
        report['missing']=[k for k in planned if k not in report['cases']]
        report['function_owner_acl_restored']=function_pins(cur)==catalog
        conn.rollback();report['runtime_after']=full_stack.composition.verify(cur)
        report['complete_boundary_restored']=avt.predecessor.snapshot(cur)==initial
        report['public_schema_complete_restored']=native.public_state(cur)==public_initial
        conn.rollback()
    report['counts']=dict(Counter(r['status'] for r in report['cases'].values()))
    bad=any(report['counts'].get(s) for s in ('INCOMPLETE','BUG_PROVEN','GAP_PROVEN','FAIL'))
    restored=all(report.get(k) is True for k in (
        'complete_boundary_restored','public_schema_complete_restored','function_owner_acl_restored'))
    report['status']='INCOMPLETE' if bad or not restored or report['missing'] else (
        'COUNTEREXAMPLE' if report['counts'].get('COUNTEREXAMPLE') else 'WRITER_PASS')
    avt.save(name,report)
    return report

