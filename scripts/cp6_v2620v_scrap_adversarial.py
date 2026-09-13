#!/usr/bin/env python3
"""Independent paid-scrap date oracle on unchanged V, disposable native only.

Exit 1 means a qualified business counterexample, never writer PASS.
Exit 2 means fixture/oracle failure or incomplete evidence, never a qualified bug.
No business function, grant contract, or posted row is rewritten by this audit.
"""
import hashlib
import json
import os
import subprocess
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_v2620e_counterexample_regression as base
import cp6_v2620v_runtime as runtime
from cp6_v2620u_install_diagnostic import snapshot

V_HEAD = '7be634e663a61545b909cf0367d12461ae7aa798'
V_TREE = 'a29235ba5386cc905cb4fb9ee784e16db4a5ce7a'
SCRAP_SOURCE_SHA256 = '53e2b8c582b342b2b4391a3fdcf91308c0e0e0f08e021c9f800b99212f64d39c'
REPORT = Path('cp6-proof/CP6_V_SCRAP_ADVERSARIAL.json')
AUTH_SOURCE = Path('ops/supabase/uat/applied/20260831032949_erp_v2_6_13b_auth_profile_facade_tracking.sql')
ZONES = ('UTC', 'Asia/Jakarta', 'America/New_York', 'Asia/Tokyo')


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def one(cur, query, params=()):
    return base.one(cur, query, params)


def identity(cur, authenticated):
    role = 'authenticated' if authenticated else 'supabase_admin'
    cur.execute('set session authorization ' + role)
    cur.execute('select current_user,session_user')
    if cur.fetchone() != (role, role):
        raise AssertionError('SCRAP_REAL_SESSION_IDENTITY_REQUIRED')
    if authenticated and one(cur, 'select erp.current_app_role()') != 'OWNER':
        raise AssertionError('SCRAP_REAL_OWNER_ROLE_REQUIRED')


def boundary(cur):
    previous = one(cur, "select current_setting('TimeZone')")
    cur.execute("set local timezone='UTC'")
    try:
        return snapshot(cur)
    finally:
        cur.execute("select set_config('TimeZone',%s,true)", (previous,))


def reports(cur):
    return {day: one(cur, 'select erp.get_owner_financial_snapshot_v2(%s::date,%s::date,%s::date)',
        ('2026-09-01', day, day)) for day in ('2026-09-02', '2026-09-03')}


def case(cur, cash, zone):
    physical = '2026-09-03T00:30:00+07:00'
    # The expected business date is derived outside PostgreSQL, without calling
    # the implementation helper. Session cast expectation is a separate oracle.
    instant = datetime.fromisoformat(physical)
    expected = instant.astimezone(ZoneInfo('Asia/Jakarta')).date().isoformat()
    session_date = instant.astimezone(ZoneInfo(zone)).date().isoformat()
    cur.execute("select set_config('TimeZone',%s,true)", (zone,))
    identity(cur, True)
    before = reports(cur)
    batch_id, sale_id = uuid.uuid4(), uuid.uuid4()
    cur.execute('insert into erp.scrap_batches(id,scrap_number,weight_kg,physical_at,notes) '
        'values(%s,%s,1,%s,%s)', (batch_id, 'V-SCRAP-B-' + str(batch_id),
        '2026-09-01T12:00:00+07:00', 'Independent V disposable scrap fixture'))
    cur.execute('insert into erp.scrap_sales(id,sale_number,scrap_batch_id,physical_at,'
        'weight_kg,amount,cash_account_id,notes) values(%s,%s,%s,%s,.5,.03,%s,%s)',
        (sale_id, 'V-SCRAP-S-' + str(sale_id), batch_id, physical, cash,
         'Independent V canonical business-date counterexample'))
    if reports(cur) != before:
        raise AssertionError('SCRAP_DRAFT_CHANGED_AUTHORITATIVE_REPORT')
    cur.execute('select erp.post_scrap_sale(%s)', (sale_id,))
    if one(cur, "select current_setting('TimeZone')") != zone:
        raise AssertionError('SCRAP_POST_LEAKED_SESSION_TIMEZONE')
    after = reports(cur)
    sale_status = one(cur, 'select status from erp.scrap_sales where id=%s', (sale_id,))
    batch_status = one(cur, 'select status from erp.scrap_batches where id=%s', (batch_id,))
    identity(cur, False)
    cur.execute("select j.id,j.status,j.economic_date::text,j.transaction_date::text,"
        "(select sum(l.debit)::text from erp.journal_lines l where l.journal_entry_id=j.id),"
        "(select sum(l.credit)::text from erp.journal_lines l where l.journal_entry_id=j.id)"
        " from erp.journal_entries j where j.source_type='SCRAP_SALE' and j.source_id=%s", (sale_id,))
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][4:] != ('0.03', '0.03'):
        raise AssertionError('SCRAP_JOURNAL_COUNT_OR_EXACT_CENTS_WRONG:' + str(rows))
    if sale_status != 'POSTED' or batch_status != 'AVAILABLE':
        raise AssertionError('SCRAP_BUSINESS_STATE_UNEXPECTED')
    if rows[0][2:4] != (session_date, session_date):
        raise AssertionError('SCRAP_SESSION_CAST_ORACLE_NOT_OBSERVED:' + str(rows))
    evidence = {}
    for day in before:
        actual = Decimal(str(after[day]['financial_position']['cash'])) - Decimal(str(before[day]['financial_position']['cash']))
        lawful = Decimal('.03') if day >= expected else Decimal(0)
        observed = Decimal('.03') if day >= session_date else Decimal(0)
        confidence = after[day]['data_confidence']['status']
        if actual != observed or confidence != 'READY':
            raise AssertionError('SCRAP_CASH_OR_CONFIDENCE_ORACLE_NOT_OBSERVED:' + str((day, actual, observed, confidence)))
        evidence[day] = dict(expected_cash_delta=str(lawful), actual_cash_delta=str(actual),
            confidence=confidence, before=before[day], after=after[day])
    cur.execute('select * from erp.run_v267_financial_truth_checks()')
    detector_rows = cur.fetchall()
    return dict(status='NEW_V_BUG_REPRODUCED' if session_date != expected else 'CONTROL_PASS',
        classification='SILENT_PER_DATE_CASH_MISPOSTING' if session_date != expected else 'LAWFUL_CONTROL',
        zone=zone, physical_at=physical, expected_date=expected, session_date=session_date,
        identity=dict(current_user='authenticated', session_user='authenticated', app_role='OWNER'),
        payload=dict(batch_id=str(batch_id),sale_id=str(sale_id),weight_kg='0.5',amount='0.03'),
        journals=[dict(zip(('id','status','economic_date','transaction_date','debit','credit'),r,strict=True)) for r in rows],
        daily_evidence=evidence, financial_truth_checks=detector_rows, draft_inert=True,
        document_cents_conserved=True, caller_timezone_preserved=True,
        http_ui_reachability_proven=False)


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1',port='54322',dbname='postgres'):
        raise AssertionError('SCRAP_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_V_SCRAP_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('SCRAP_DISPOSABLE_CONFIRMATION_REQUIRED')
    if git('rev-parse', V_HEAD + '^{tree}') != V_TREE:
        raise AssertionError('SCRAP_FROZEN_V_TREE_MISMATCH')
    if git('diff', '--name-only', V_HEAD, 'HEAD', '--', 'supabase/migrations', 'supabase/rollbacks'):
        raise AssertionError('SCRAP_REQUIRES_UNCHANGED_V_BUSINESS_SQL')
    head = git('rev-parse', 'HEAD')
    if os.environ.get('GITHUB_SHA') != head:
        raise AssertionError('SCRAP_EXACT_NATIVE_CHECKOUT_REQUIRED')
    result = dict(format='CP6_V_SCRAP_INDEPENDENT_AUDIT_V1',head=head,
        tree=git('rev-parse', 'HEAD^{tree}'),parents=git('show','-s','--format=%P','HEAD').split(),
        audited_business_head=V_HEAD,audited_business_tree=V_TREE,
        run_id=os.environ.get('GITHUB_RUN_ID'),run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
        classification='NATIVE_POSTGRESQL_AUTHENTICATED_SQL_SESSION',
        production_go=False,http_ui_reachability_proven=False,cases=[],status='FAIL')
    with psycopg.connect(**dict(params,user='supabase_admin'),autocommit=False) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        cur.execute("select current_user,session_user,rolsuper from pg_roles where rolname=current_user")
        if cur.fetchone() != ('supabase_admin','supabase_admin',True):
            raise AssertionError('SCRAP_EXISTING_DISPOSABLE_ADMIN_REQUIRED')
        untouched = boundary(cur)
        if len(runtime.verified_successor(cur)) != 3:
            raise AssertionError('SCRAP_EXACT_V_RUNTIME_REQUIRED')
        result['engine'] = one(cur, 'select version()')
        result['sources'] = {}
        for path in (Path(__file__).resolve().relative_to(Path.cwd()),runtime.MIGRATION,AUTH_SOURCE):
            data = path.read_bytes()
            result['sources'][str(path)] = dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        result['source_definitions'] = []
        for function in ('erp.post_scrap_sale(uuid)','erp.post_journal(text,uuid,date,text,jsonb)',
                         'erp.get_owner_financial_snapshot_v2(date,date,date)'):
            cur.execute('select pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),p.proacl::text'
                ' from pg_proc p where p.oid=%s::regprocedure', (function,))
            definition,owner,acl = cur.fetchone()
            result['source_definitions'].append(dict(identity=function,definition=definition,
                sha256=hashlib.sha256(definition.encode()).hexdigest(),owner=owner,acl=acl))
        scrap_source = result['source_definitions'][0]
        if scrap_source['sha256'] != SCRAP_SOURCE_SHA256 or scrap_source['owner'] != 'postgres' or scrap_source['acl'] != '{postgres=X/postgres,authenticated=X/postgres,service_role=X/postgres}':
            raise AssertionError('SCRAP_EXACT_FROZEN_FUNCTION_OWNER_ACL_REQUIRED')
        if AUTH_SOURCE.read_text().count('grant usage on schema public, erp to authenticated;') != 1:
            raise AssertionError('SCRAP_SCHEMA_ALIGNMENT_SOURCE_MISMATCH')
        result['schema_usage_before_alignment'] = one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
        if not result['schema_usage_before_alignment']:
            # Restore only the existing published schema-USAGE contract for the
            # catalog-only fixture. No function/table privilege is added.
            cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)",
            (json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
        cur.execute("select set_config('app.change_reason','V independent scrap-date audit',true)")
        base.load_fixture_foundation(cur)
        cash = one(cur,'select id from erp.cash_accounts where is_active order by id limit 1')
        for zone in ZONES:
            cur.execute('savepoint scrap_case')
            before_case = boundary(cur)
            try:
                evidence = case(cur,cash,zone)
            except Exception as exc:
                evidence = dict(zone=zone,status='FIXTURE_OR_ORACLE_FAILURE',error=str(exc),sqlstate=getattr(exc,'sqlstate',None))
            finally:
                cur.execute('rollback to savepoint scrap_case')
                identity(cur,False)
                cur.execute('release savepoint scrap_case')
            evidence['full_boundary_restored'] = boundary(cur) == before_case
            result['cases'].append(evidence)
            print(json.dumps({k:v for k,v in evidence.items() if k in ('zone','status','error','full_boundary_restored')},default=str),flush=True)
            if not evidence['full_boundary_restored']:
                raise AssertionError('SCRAP_CASE_ROLLBACK_LEFT_RESIDUE')
        conn.rollback()
        result['entire_unseeded_runtime_restored'] = boundary(cur) == untouched
        result['schema_usage_restored'] = one(cur,"select has_schema_privilege('authenticated','erp','USAGE')") == result['schema_usage_before_alignment']
        result['boundary'] = untouched
        conn.rollback()
    result['new_bug_reproductions'] = sum(c['status']=='NEW_V_BUG_REPRODUCED' for c in result['cases'])
    result['lawful_controls'] = sum(c['status']=='CONTROL_PASS' for c in result['cases'])
    result['oracle_failures'] = sum(c['status']=='FIXTURE_OR_ORACLE_FAILURE' for c in result['cases'])
    qualified = result['new_bug_reproductions']==2 and result['lawful_controls']==2 and result['oracle_failures']==0 and result['entire_unseeded_runtime_restored'] and result['schema_usage_restored']
    result['proof_status'] = 'COUNTEREXAMPLE_QUALIFIED' if qualified else 'INCOMPLETE'
    result['candidate_verdict'] = 'FAIL' if qualified else 'INCOMPLETE'
    return result


if __name__ == '__main__':
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    try:
        result = run()
    except Exception as exc:
        result = dict(status='FAIL',proof_status='INCOMPLETE',candidate_verdict='INCOMPLETE',
            error=str(exc),sqlstate=getattr(exc,'sqlstate',None),production_go=False)
    REPORT.write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','boundary','source_definitions')},default=str))
    raise SystemExit(1 if result['proof_status']=='COUNTEREXAMPLE_QUALIFIED' else 2)
