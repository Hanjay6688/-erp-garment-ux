#!/usr/bin/env python3
"""Native paired V/W paid-scrap oracle; authenticated SQL is not HTTP/UI proof."""
import hashlib
import json
import os
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_v2620e_counterexample_regression as base
import cp6_v2620v_runtime as v_runtime
import cp6_v2620w_runtime as w_runtime
import cp6_v2620v_misc_finance_business_date_regression as shared

AUTH_SOURCE = shared.AUTH_SOURCE
MIGRATION = w_runtime.MIGRATION
DETECTOR = 'V2620W_SCRAP_BUSINESS_DATE'
CORE_ZONES = ('UTC','Asia/Jakarta','America/New_York','Asia/Tokyo')
EXTRA_CASES = ('EDGE_BEFORE','EDGE_AT','EDGE_AFTER','NOW_BEHIND','NOW_AHEAD',
    'ONE_CENT','FUTURE_POST_REFUSAL','NON_OWNER_POST_DENIED','DRAFT_DELETE_INERT',
    'POSTED_UPDATE_DENIED','POSTED_DELETE_DENIED','POST_REPLAY_REFUSAL','BLANK_REVERSE_REFUSAL',
    'REVERSE_REPLAY','ZERO_AMOUNT','QUANTITY_OVER_CAPACITY','FULL_WEIGHT_REVERSE',
    'DETECTOR_POSTED','DETECTOR_REVERSED','CLOSED_PERIOD_ECONOMIC_DATE','ACL_CONTRACT')
one,zone,identity,boundary,reports,refusal = (
    shared.one,shared.zone,shared.identity,shared.boundary,shared.reports,shared.refusal)


def draft(cur,cash,categories=None,physical='2026-09-03T00:30:00+07',amount='.03',weight='.5'):
    batch_id,transaction = uuid.uuid4(),uuid.uuid4()
    cur.execute('insert into erp.scrap_batches(id,scrap_number,weight_kg,physical_at,notes) '
        'values(%s,%s,1,%s,%s)',(batch_id,'W-SCRAP-B-'+str(batch_id),'2026-09-01T12:00:00+07','W disposable scrap fixture'))
    cur.execute('insert into erp.scrap_sales(id,sale_number,scrap_batch_id,physical_at,weight_kg,amount,cash_account_id,notes) '
        'values(%s,%s,%s,%s,%s,%s,%s,%s)',(transaction,'W-SCRAP-S-'+str(transaction),batch_id,physical,weight,amount,cash,'W canonical paid scrap date'))
    return transaction


def book(cur,transaction):
    cur.execute("select j.id,j.source_type,j.status,j.economic_date::text,j.transaction_date::text,j.reversal_of_id,"
        "(select sum(l.debit)::text from erp.journal_lines l where l.journal_entry_id=j.id),"
        "(select sum(l.credit)::text from erp.journal_lines l where l.journal_entry_id=j.id)"
        " from erp.journal_entries j where j.source_id=%s or j.reversal_of_id in"
        " (select id from erp.journal_entries where source_type='SCRAP_SALE' and source_id=%s) order by j.id",(transaction,transaction))
    return [dict(zip(('id','source_type','status','economic_date','transaction_date','reversal_of_id','debit','credit'),r,strict=True)) for r in cur.fetchall()]


def check_post(cur,transaction,expected,before,amount='.03',posting_date=None):
    after=reports(cur,tuple(before));rows=book(cur,transaction)
    if len(rows)!=1 or (rows[0]['economic_date'],rows[0]['transaction_date'])!=(expected,posting_date or expected):
        raise AssertionError('W_SCRAP_JOURNAL_DATE:'+str(rows))
    if any(Decimal(rows[0][key])!=Decimal(amount) for key in ('debit','credit')):
        raise AssertionError('W_SCRAP_EXACT_CENTS')
    deltas={}
    for day in before:
        actual=Decimal(str(after[day]['financial_position']['cash']))-Decimal(str(before[day]['financial_position']['cash']))
        wanted=Decimal(amount) if day>=(posting_date or expected) else Decimal(0)
        if actual!=wanted or after[day]['data_confidence']['status']!='READY':
            raise AssertionError('W_SCRAP_CASH_OR_CONFIDENCE:'+str((day,actual,wanted,after[day]['data_confidence'])))
        deltas[day]=dict(expected=str(wanted),actual=str(actual),confidence='READY')
    return dict(journals=rows,per_date_cash=deltas,document_cents_conserved=True)


def upgrade_probe(cur,wrong):
    before=boundary(cur);source=MIGRATION.read_text()
    if source.count('\nbegin;\n')!=1 or not source.endswith('commit;\n'):
        raise AssertionError('W_UPGRADE_TRANSACTION_SHAPE')
    body=source.replace('\nbegin;\n','\n',1).removesuffix('commit;\n')
    cur.execute('savepoint w_upgrade_probe');error=None
    try:
        cur.execute(body,prepare=False)
        if one(cur,'select count(*) from erp.cp6_v2620w_rollback_capsule')!=3:
            raise AssertionError('W_LAWFUL_HISTORY_CAPSULE_CARDINALITY')
    except psycopg.Error as exc:
        error=str(exc)
    finally:
        cur.execute('rollback to savepoint w_upgrade_probe;release savepoint w_upgrade_probe')
    if wrong!=bool(error) or (wrong and 'W_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED' not in error):
        raise AssertionError('W_UPGRADE_HISTORY_GATE:'+str(error))
    if boundary(cur)!=before:raise AssertionError('W_UPGRADE_PROBE_LEFT_RESIDUE')
    return dict(invalid_history_refused=wrong,lawful_history_accepted=not wrong,full_boundary_exact=True,error=error)


def core(cur,cash,timezone,fixed):
    physical='2026-09-03T00:30:00+07:00'
    expected=datetime.fromisoformat(physical).astimezone(ZoneInfo('Asia/Jakarta')).date().isoformat()
    zone(cur,timezone);identity(cur)
    before=reports(cur,('2026-09-02','2026-09-03'));transaction=draft(cur,cash,physical=physical)
    if reports(cur,tuple(before))!=before:raise AssertionError('W_DRAFT_CHANGED_REPORT')
    cur.execute('select erp.post_scrap_sale(%s)',(transaction,))
    if one(cur,"select current_setting('TimeZone')")!=timezone:raise AssertionError('W_CALLER_ZONE_LEAK')
    after=reports(cur,tuple(before));identity(cur,False);rows=book(cur,transaction)
    if len(rows)!=1 or rows[0]['debit']!='0.03' or rows[0]['credit']!='0.03':raise AssertionError('W_EXACT_CENTS_OR_CARDINALITY')
    wrong=rows[0]['economic_date']!=expected
    observed_date=expected if fixed else datetime.fromisoformat(physical).astimezone(ZoneInfo(timezone)).date().isoformat()
    if rows[0]['economic_date']!=observed_date or rows[0]['transaction_date']!=observed_date:
        raise AssertionError('W_PAIRED_DATE_ORACLE:'+str(rows))
    evidence={}
    for day in before:
        delta=Decimal(str(after[day]['financial_position']['cash']))-Decimal(str(before[day]['financial_position']['cash']))
        observed=Decimal('.03') if day>=observed_date else Decimal(0)
        if delta!=observed or after[day]['data_confidence']['status']!='READY':raise AssertionError('W_CORE_REPORT_ORACLE')
        evidence[day]=dict(expected_cash_delta=str(Decimal('.03') if day>=expected else Decimal(0)),actual_cash_delta=str(delta),before=before[day],after=after[day])
    result=dict(status='PASS' if fixed else 'KNOWN_V_BUG_REPRODUCED' if wrong else 'CONTROL_PASS',
        classification='SILENT_PER_DATE_CASH_MISPOSTING' if wrong else 'LAWFUL_CONTROL',
        zone=timezone,physical_at=physical,expected_date=expected,journals=rows,daily_evidence=evidence,
        identity=dict(current_user='authenticated',session_user='authenticated',app_role='OWNER'),
        draft_inert=True,document_cents_conserved=True,caller_timezone_preserved=True)
    if not fixed:result['upgrade_guard']=upgrade_probe(cur,wrong)
    return result


def extra(cur,cash,name):
    zone(cur,'Asia/Jakarta');identity(cur)
    if name.startswith(('EDGE_','NOW_')) or name=='ONE_CENT':
        physical={'EDGE_BEFORE':'2026-09-02T23:59:59.999999+07','EDGE_AT':'2026-09-03T00:00:00+07','EDGE_AFTER':'2026-09-03T00:00:00.000001+07'}.get(name,'2026-09-03T00:30:00+07')
        posting_zone='UTC'
        if name.startswith('NOW_'):
            physical=one(cur,'select current_timestamp').isoformat()
            posting_zone='Etc/GMT+12' if name.endswith('BEHIND') else 'Pacific/Kiritimati'
        expected=datetime.fromisoformat(physical).astimezone(ZoneInfo('Asia/Jakarta')).date().isoformat()
        days=((date.fromisoformat(expected)-timedelta(days=1)).isoformat(),expected)
        amount='.01' if name=='ONE_CENT' else '.03'
        zone(cur,'Asia/Tokyo');before=reports(cur,days);transaction=draft(cur,cash,physical=physical,amount=amount)
        zone(cur,posting_zone);cur.execute('select erp.post_scrap_sale(%s)',(transaction,))
        if one(cur,"select current_setting('TimeZone')")!=posting_zone:raise AssertionError('W_EDGE_ZONE_LEAK')
        identity(cur,False);return check_post(cur,transaction,expected,before,amount)
    if name=='ACL_CONTRACT':
        identity(cur,False)
        cur.execute("select p.oid::regprocedure::text,p.prosecdef,p.proconfig,pg_get_userbyid(p.proowner),"
            "has_function_privilege('anon',p.oid,'EXECUTE'),has_function_privilege('authenticated',p.oid,'EXECUTE'),"
            "has_function_privilege('service_role',p.oid,'EXECUTE'),"
            "exists(select 1 from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a where a.grantee=0 and a.privilege_type='EXECUTE')"
            " from pg_proc p where p.oid in('erp.post_scrap_sale(uuid)'::regprocedure,'erp.reverse_scrap_sale(uuid,text)'::regprocedure) order by 1")
        rows=cur.fetchall()
        if len(rows)!=2 or any(not r[1] or 'search_path=erp, public' not in r[2] or r[3:]!=('postgres',False,True,r[0]=='erp.post_scrap_sale(uuid)',False) for r in rows):raise AssertionError('W_ENTRYPOINT_SECURITY:'+str(rows))
        for role in ('anon','authenticated','service_role'):
            if one(cur,"select has_table_privilege(%s,'erp.cp6_v2620w_rollback_capsule','SELECT')",(role,)):raise AssertionError('W_PRIVATE_CAPSULE_EXPOSED')
        return dict(entrypoints=rows,private_capsule_denial=True,http_ui_reachability_proven=False)
    if name.startswith('DETECTOR_'):
        identity(cur,False)
        current=one(cur,"select pg_get_functiondef('erp.post_scrap_sale(uuid)'::regprocedure)")
        predecessor=one(cur,"select object_definition from erp.cp6_v2620w_rollback_capsule where object_regidentity='erp.post_scrap_sale(uuid)'")
        cur.execute(predecessor,prepare=False);zone(cur,'UTC');identity(cur)
        transaction=draft(cur,cash);cur.execute('select erp.post_scrap_sale(%s)',(transaction,))
        if name=='DETECTOR_REVERSED':cur.execute("select erp.reverse_scrap_sale(%s,'W controlled predecessor replay')",(transaction,))
        identity(cur,False);cur.execute(current,prepare=False)
        counts=[one(cur,'select coalesce(sum(issue_count),0) from erp.'+fn+'() where check_name=%s and severity=%s',(DETECTOR,'CRITICAL')) for fn in ('run_v267_financial_truth_checks','run_v268_financial_report_checks')]
        report=reports(cur,('2026-09-03',))['2026-09-03']['data_confidence']['status']
        if counts!=[1,1] or report!='BLOCKED':raise AssertionError('W_DETECTOR_OR_REPORT_SCOPE:'+str((counts,report)))
        return dict(counts=counts,report=report,controlled_tester_predecessor_replay=True,runtime_definition_restored=True,operator_ddl_ability_claimed=False)
    if name=='CLOSED_PERIOD_ECONOMIC_DATE':
        identity(cur,False);cur.execute("update erp.accounting_period_control set closed_through='2026-09-03'");identity(cur)
        posting=one(cur,"select ((current_timestamp at time zone 'Asia/Jakarta')::date)::text")
        before=reports(cur,('2026-09-02','2026-09-03',posting));transaction=draft(cur,cash)
        zone(cur,'UTC');cur.execute('select erp.post_scrap_sale(%s)',(transaction,));identity(cur,False)
        return check_post(cur,transaction,'2026-09-03',before,posting_date=posting)
    physical=one(cur,"select (((current_timestamp at time zone 'Asia/Jakarta')::date+1)::text||'T00:30:00+07')") if name=='FUTURE_POST_REFUSAL' else '2026-09-03T00:30:00+07'
    before_reports=reports(cur,('2026-09-02','2026-09-03'))
    transaction=draft(cur,cash,physical=physical,amount='0' if name=='ZERO_AMOUNT' else '.03',weight='1' if name=='FULL_WEIGHT_REVERSE' else '.5')
    if name in ('FUTURE_POST_REFUSAL','NON_OWNER_POST_DENIED'):
        if name=='NON_OWNER_POST_DENIED':
            cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=str(uuid.uuid4()),role='authenticated')),))
            if one(cur,'select erp.current_app_role()') is not None:raise AssertionError('W_UNMAPPED_SUBJECT_ORACLE')
        error=refusal(cur,'select erp.post_scrap_sale(%s)',(transaction,));identity(cur,False)
        if one(cur,'select status from erp.scrap_sales where id=%s',(transaction,))!='DRAFT' or book(cur,transaction):raise AssertionError('W_REFUSAL_CHANGED_LEDGER')
        return dict(refusal=error,atomic=True)
    if name=='DRAFT_DELETE_INERT':
        cur.execute('delete from erp.scrap_sales where id=%s',(transaction,))
        if reports(cur,tuple(before_reports))!=before_reports:raise AssertionError('W_DRAFT_DELETE_CHANGED_REPORT')
        identity(cur,False)
        if book(cur,transaction):raise AssertionError('W_DRAFT_DELETE_CREATED_JOURNAL')
        return dict(draft_delete_inert=True)
    cur.execute('select erp.post_scrap_sale(%s)',(transaction,))
    identity(cur,False);before=boundary(cur);identity(cur)
    if name=='QUANTITY_OVER_CAPACITY':
        second=draft(cur,cash,weight='.75')
        cur.execute('update erp.scrap_sales set scrap_batch_id=(select scrap_batch_id from erp.scrap_sales where id=%s) where id=%s',(transaction,second))
        identity(cur,False);before=boundary(cur);identity(cur)
        error=refusal(cur,'select erp.post_scrap_sale(%s)',(second,),'Scrap sale exceeds available weight')
        identity(cur,False)
        if boundary(cur)!=before:raise AssertionError('W_OVERWEIGHT_REFUSAL_NOT_ATOMIC')
        return dict(refusal=error,atomic=True)
    if name=='ZERO_AMOUNT':
        if book(cur,transaction) or reports(cur,tuple(before_reports))!=before_reports:raise AssertionError('W_ZERO_AMOUNT_CREATED_CASH')
        cur.execute("select erp.reverse_scrap_sale(%s,'W zero-value disposal reversal')",(transaction,));identity(cur,False)
        if book(cur,transaction):raise AssertionError('W_ZERO_REVERSAL_CREATED_CASH')
        return dict(no_journal_for_zero_amount=True)
    if name in ('REVERSE_REPLAY','FULL_WEIGHT_REVERSE'):
        if name=='FULL_WEIGHT_REVERSE' and one(cur,'select b.status from erp.scrap_batches b join erp.scrap_sales s on s.scrap_batch_id=b.id where s.id=%s',(transaction,))!='SOLD':raise AssertionError('W_FULL_WEIGHT_NOT_SOLD')
        zone(cur,'Etc/GMT+12');cur.execute("select erp.reverse_scrap_sale(%s,'W lawful linked inverse')",(transaction,));identity(cur,False)
        first=boundary(cur);rows=book(cur,transaction)
        if len(rows)!=2:raise AssertionError('W_INVERSE_CARDINALITY')
        original=next(r for r in rows if r['source_type']=='SCRAP_SALE');inverse=next(r for r in rows if r['source_type']=='JOURNAL_REVERSAL')
        if inverse['reversal_of_id']!=original['id'] or inverse['economic_date']<original['economic_date']:raise AssertionError('W_INVERSE_LINEAGE_CHRONOLOGY')
        delta=one(cur,'select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l where l.journal_entry_id=any(%s::uuid[]) and l.account_id=(select coa_account_id from erp.cash_accounts where id=%s)',([r['id'] for r in rows],cash))
        if delta!=Decimal(0):raise AssertionError('W_INVERSE_NOT_NET_ZERO')
        if one(cur,'select b.status from erp.scrap_batches b join erp.scrap_sales s on s.scrap_batch_id=b.id where s.id=%s',(transaction,))!='AVAILABLE':raise AssertionError('W_REVERSED_WEIGHT_NOT_AVAILABLE')
        identity(cur);zone(cur,'Pacific/Kiritimati');cur.execute("select erp.reverse_scrap_sale(%s,'W lawful linked inverse')",(transaction,));identity(cur,False)
        if boundary(cur)!=first:raise AssertionError('W_REVERSE_REPLAY_CHANGED_BOUNDARY')
        return dict(journals=rows,cash_delta=str(delta),exact_replay_inert=True,batch_available=True)
    queries={'POSTED_UPDATE_DENIED':'update erp.scrap_sales set amount=.07 where id=%s',
        'POSTED_DELETE_DENIED':'delete from erp.scrap_sales where id=%s','POST_REPLAY_REFUSAL':'select erp.post_scrap_sale(%s)',
        'BLANK_REVERSE_REFUSAL':"select erp.reverse_scrap_sale(%s,'')"}
    error=refusal(cur,queries[name],(transaction,));identity(cur,False)
    if boundary(cur)!=before:raise AssertionError('W_POSTED_REFUSAL_CHANGED_FACTS')
    return dict(refusal=error,complete_boundary_inert=True)


def run():
    params=conninfo_to_dict(os.environ.get('PGURL',''))
    if params!=dict(user='postgres',password='postgres',host='127.0.0.1',port='54322',dbname='postgres') or os.environ.get('CP6_W_DISPOSABLE_CONFIRM')!='postgres':raise AssertionError('W_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    phase=os.environ.get('CP6_W_PHASE')
    if phase not in ('BEFORE_W','AFTER_W'):raise AssertionError('W_UNKNOWN_PHASE')
    fixed=phase=='AFTER_W';result=dict(head=os.environ.get('GITHUB_SHA','LOCAL_UNBOUND'),production_go=False,
        classification='NATIVE_POSTGRESQL_REAL_AUTHENTICATED_SESSION_'+phase,phase=phase,status='FAIL',cases={},expanded_cases={},http_ui_reachability_proven=False)
    with psycopg.connect(**dict(params,user='supabase_admin'),autocommit=False) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        if not one(cur,'select rolsuper from pg_roles where rolname=current_user'):raise AssertionError('W_EXISTING_DISPOSABLE_ADMIN_REQUIRED')
        untouched=boundary(cur);v=v_runtime.verified_successor(cur);w=w_runtime.verified_successor(cur)
        if len(v)!=3 or bool(w)!=fixed or (fixed and len(w)!=3):raise AssertionError('W_RUNTIME_PHASE_MISMATCH')
        result['runtime']=dict(engine=one(cur,'select version()'),verified_v_functions=len(v),verified_w_functions=len(w),installed_function_hashes=list(w.values()))
        if AUTH_SOURCE.read_text().count('grant usage on schema public, erp to authenticated;')!=1:raise AssertionError('W_SCHEMA_ALIGNMENT_SOURCE_MISMATCH')
        result['schema_alignment_source_sha256']=hashlib.sha256(AUTH_SOURCE.read_bytes()).hexdigest()
        result['schema_usage_before_alignment']=one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
        if not result['schema_usage_before_alignment']:cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
        cur.execute("select set_config('app.change_reason','W paid scrap regression',true)");base.load_fixture_foundation(cur)
        cash=one(cur,'select id from erp.cash_accounts where is_active order by id limit 1')
        specs=[('cases',z,lambda tz=z:core(cur,cash,tz,fixed)) for z in CORE_ZONES]
        if fixed:specs += [('expanded_cases',n,lambda name=n:extra(cur,cash,name)) for n in EXTRA_CASES]
        for group,name,operation in specs:
            cur.execute('savepoint w_case');before=boundary(cur)
            try:
                evidence=operation();evidence.setdefault('status','PASS')
            except Exception as exc:
                evidence=dict(status='FAIL',error=str(exc),sqlstate=getattr(exc,'sqlstate',None))
            finally:
                cur.execute('rollback to savepoint w_case');identity(cur,False);cur.execute('release savepoint w_case')
            evidence['full_boundary_restored']=boundary(cur)==before
            if not evidence['full_boundary_restored']:raise AssertionError('W_CASE_ROLLBACK_RESIDUE:'+name)
            result[group][name]=evidence
        conn.rollback();result['entire_unseeded_runtime_restored']=boundary(cur)==untouched
        result['schema_usage_restored']=one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")==result['schema_usage_before_alignment'];conn.rollback()
    expected={'PASS'} if fixed else {'KNOWN_V_BUG_REPRODUCED','CONTROL_PASS'}
    success=len(result['cases'])==4 and all(c['status'] in expected and c['full_boundary_restored'] for c in result['cases'].values())
    if fixed:success=success and len(result['expanded_cases'])==21 and all(c['status']=='PASS' and c['full_boundary_restored'] for c in result['expanded_cases'].values())
    else:success=success and sum(c['status']=='KNOWN_V_BUG_REPRODUCED' for c in result['cases'].values())==2
    result['status']='PASS' if success and result['entire_unseeded_runtime_restored'] and result['schema_usage_restored'] else 'FAIL'
    return result


if __name__=='__main__':
    phase=os.environ.get('CP6_W_PHASE','UNKNOWN')
    report=Path('cp6-proof/CP6_V2620W_'+('V_COUNTEREXAMPLES' if phase=='BEFORE_W' else 'SCRAP_BUSINESS_DATE_REGRESSION')+'.json')
    try:result=run()
    except Exception as exc:result=dict(status='FAIL',error=str(exc),phase=phase,production_go=False)
    report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','expanded_cases')},default=str))
    raise SystemExit(0 if result['status']=='PASS' else 1)
