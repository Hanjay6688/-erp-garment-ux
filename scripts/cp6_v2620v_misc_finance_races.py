#!/usr/bin/env python3
"""Real misc-cash document locks, duplicate post and writer-abort qualification."""
import json
import os
import threading
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_v2620e_counterexample_regression as base
import cp6_v2620h_maintenance_rollback_matrix as matrix
import cp6_v2620v_runtime as runtime
import cp6_v2620v_misc_finance_business_date_regression as proof

ROOT = Path('cp6-proof/V_MISC_FINANCE_NATIVE_RACES')
CASES = ('POST_THEN_REVERSE', 'POST_THEN_POST', 'POST_ABORT_THEN_POST')
SOURCE_GENERATION = 'V'


def session(name):
    params = conninfo_to_dict(matrix.CLONE)
    if params != dict(user='postgres',password='postgres',host='127.0.0.1',port='54322',dbname='cp6_rollback'):
        raise AssertionError('V_RACE_CANONICAL_CLONE_REQUIRED')
    conn = psycopg.connect(**dict(params,user='supabase_admin'),application_name='cp6-v-'+name)
    with conn.cursor() as cur:
        cur.execute("set timezone='UTC';set statement_timeout='30s';set lock_timeout='20s'")
        if not proof.one(cur,'select rolsuper from pg_roles where rolname=current_user'):
            raise AssertionError('V_RACE_EXISTING_DISPOSABLE_ADMIN_REQUIRED')
    conn.commit()
    return conn


def operator(cur, timezone):
    cur.execute("select set_config('request.jwt.claims',%s,true)", (json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
    cur.execute("select set_config('app.change_reason','V real-session cash race',true)")
    proof.zone(cur,timezone)
    proof.identity(cur)


def run_case(name, folder):
    matrix.command(['bash','scripts/clone-cp6-disposable-database.sh',matrix.SOURCE,matrix.MAINTENANCE,
        matrix.CLONE,'cp6_rollback',matrix.CONTAINER,str(folder/'PHYSICAL_BOUNDARY')],folder/'clone.log')
    matrix.verify_setup_source(SOURCE_GENERATION)
    with session('fixture') as conn, conn.cursor() as cur:
        if len(runtime.verified_successor(cur)) != 3:
            raise AssertionError('V_RACE_EXACT_RUNTIME_REQUIRED')
        if proof.AUTH_SOURCE.read_text().count('grant usage on schema public, erp to authenticated;') != 1:
            raise AssertionError('V_RACE_SCHEMA_ALIGNMENT_SOURCE_REQUIRED')
        if not proof.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')"):
            cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)", (json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
        cur.execute("select set_config('app.change_reason','V race fixture',true)")
        base.load_fixture_foundation(cur)
        cash=proof.one(cur,'select id from erp.cash_accounts where is_active order by id limit 1')
        cur.execute('select category_type,id from erp.misc_finance_categories where is_active');categories=dict(cur.fetchall())
        operator(cur,'Asia/Tokyo')
        transaction=proof.draft(cur,cash,categories)
        today=proof.one(cur,"select ((current_timestamp at time zone 'Asia/Jakarta')::date)::text")
        before=proof.reports(cur,('2026-09-02','2026-09-03',today))
        conn.commit()
    first=session('first');second=session('second');thread=None;outcome={}
    reverse=name=='POST_THEN_REVERSE';abort=name=='POST_ABORT_THEN_POST'
    query="select erp.reverse_misc_finance(%s,'V serialized linked inverse')" if reverse else 'select erp.post_misc_finance(%s)'
    try:
        with first.cursor() as cur:
            operator(cur,'UTC');cur.execute('select erp.post_misc_finance(%s)',(transaction,))
        # The actual function has completed and retains its natural document row lock.
        # There is no manual prelock, patched function, trigger or artificial sleep.
        def contender():
            try:
                with second.cursor() as cur:
                    operator(cur,'America/New_York');cur.execute(query,(transaction,))
                second.commit();outcome.update(status='COMMITTED')
            except psycopg.Error as exc:
                second.rollback();outcome.update(status='REJECTED',sqlstate=exc.sqlstate,message=exc.diag.message_primary)
            except Exception as exc:
                second.rollback();outcome.update(status='FAIL',error_type=type(exc).__name__)
        thread=threading.Thread(target=contender,daemon=True);thread.start()
        with session('observer') as observer:
            def observation():
                row=observer.execute('select pid,state,wait_event_type,wait_event,pg_blocking_pids(pid),query '
                    'from pg_stat_activity where pid=%s',(second.info.backend_pid,)).fetchone()
                observer.commit()
                function='erp.reverse_misc_finance' if reverse else 'erp.post_misc_finance'
                if row and first.info.backend_pid in row[4] and row[1]=='active' and row[2]=='Lock':
                    return dict(pid=row[0],state=row[1],wait_event_type=row[2],wait_event=row[3],
                        blocking_pids=row[4],real_business_query_observed=function in row[5])
                return None
            blocked=matrix.wait_for(observation,12)
            if not blocked['real_business_query_observed'] or outcome:
                raise AssertionError('V_RACE_NOT_INSIDE_REAL_DOCUMENT_CALL')
        if abort:first.rollback()
        else:first.commit()
        thread.join(25)
        if thread.is_alive():raise AssertionError('V_RACE_CONTENDER_DID_NOT_FINISH')
        expected_outcome={'status':'REJECTED','sqlstate':'P0001','message':'Misc finance transaction must be DRAFT'} if name=='POST_THEN_POST' else {'status':'COMMITTED'}
        if outcome!=expected_outcome:raise AssertionError('V_RACE_WRITER_OR_ABORT_ORACLE:'+str(outcome))
        with session('reconcile') as conn,conn.cursor() as cur:
            operator(cur,'Pacific/Kiritimati');after=proof.reports(cur,tuple(before));proof.identity(cur,False)
            rows=proof.book(cur,transaction)
            state=proof.one(cur,'select status from erp.misc_finance_transactions where id=%s',(transaction,))
            if state!=('REVERSED' if reverse else 'POSTED') or len(rows)!=(2 if reverse else 1):
                raise AssertionError('V_RACE_DOCUMENT_OR_JOURNAL_CARDINALITY')
            original=next(r for r in rows if r['source_type']=='MISC_FINANCE')
            if original['economic_date']!='2026-09-03' or original['transaction_date']!='2026-09-03':
                raise AssertionError('V_RACE_POST_DATE_WRONG')
            if any(r['debit']!='0.03' or r['credit']!='0.03' for r in rows):
                raise AssertionError('V_RACE_EXACT_CENTS_WRONG')
            if reverse:
                inverse=next(r for r in rows if r['source_type']=='JOURNAL_REVERSAL')
                if inverse['reversal_of_id']!=original['id'] or inverse['economic_date']!=today:
                    raise AssertionError('V_RACE_LINKED_INVERSE_OR_DATE')
            deltas={}
            for day in before:
                actual=Decimal(str(after[day]['financial_position']['cash']))-Decimal(str(before[day]['financial_position']['cash']))
                expected=Decimal(0) if day=='2026-09-02' or (reverse and day==today) else Decimal('.03')
                if actual!=expected or after[day]['data_confidence']['status']!='READY':
                    raise AssertionError('V_RACE_CASH_DATE_OR_REPORT_CONFIDENCE')
                deltas[day]=dict(expected=str(expected),actual=str(actual))
        return dict(case=name,status='PASS',first_pid=first.info.backend_pid,second_pid=second.info.backend_pid,
            blocking_observation=blocked,first_real_function_completed_before_commit=True,
            authority='REAL_AUTHENTICATED_SESSION_OWNER',manual_prelock_count=0,retry_count=0,
            first_aborted=abort,contender=outcome,document_status=state,journals=rows,per_date_cash=deltas,
            report='READY',http_ui_reachability_proven=False)
    finally:
        first.rollback();first.close()
        if thread is not None and thread.is_alive():second.cancel();thread.join(5)
        second.close()


def main():
    expected=(matrix.SOURCE,matrix.MAINTENANCE,matrix.CLONE,matrix.CONTAINER,'cp6_rollback')
    if tuple(os.environ.get(k) for k in ('PGURL','CP6_MAINTENANCE_PGURL','CP6_ROLLBACK_RACE_PGURL',
        'CP6_DATABASE_CONTAINER','CP6_MAINTENANCE_CONFIRM_DATABASE'))!=expected:
        raise SystemExit('V_RACE_DISPOSABLE_ENDPOINT_CONFIRMATION_REQUIRED')
    ROOT.mkdir(parents=True,exist_ok=True)
    report=dict(head=os.environ.get('GITHUB_SHA','LOCAL_UNBOUND'),production_go=False,
        classification='NATIVE_POSTGRESQL_REAL_MISC_FINANCE_DOCUMENT_LOCKS',source_generation=SOURCE_GENERATION,cases=[])
    for name in CASES:
        folder=ROOT/name;folder.mkdir()
        try:result=run_case(name,folder)
        except Exception as exc:result=dict(case=name,status='FAIL',error=str(exc),error_type=type(exc).__name__,sqlstate=getattr(exc,'sqlstate',None))
        finally:matrix.legacy.drop_clone()
        result['remaining_clone_databases']=0
        (folder/'result.json').write_text(json.dumps(result,indent=2,default=str)+'\n');report['cases'].append(result)
    report['status']='PASS' if len(report['cases'])==3 and all(c['status']=='PASS' for c in report['cases']) else 'FAIL'
    (ROOT/'manifest.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(dict(status=report['status'],case_count=len(report['cases']),production_go=False)))
    raise SystemExit(0 if report['status']=='PASS' else 1)


if __name__=='__main__':main()
