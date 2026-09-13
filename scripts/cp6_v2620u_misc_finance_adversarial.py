#!/usr/bin/env python3
"""Independent cash-date oracle on exact disposable U; preserves failing evidence."""
import hashlib
import json
import os
import subprocess
import uuid
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_v2620e_counterexample_regression as base
import cp6_v2620u_runtime as runtime
from cp6_v2620u_install_diagnostic import snapshot

REPORT = Path('cp6-proof/CP6_U_MISC_FINANCE_ADVERSARIAL.json')
AUTH_SOURCE = Path('ops/supabase/uat/applied/20260831032949_erp_v2_6_13b_auth_profile_facade_tracking.sql')
U_HEAD = '61ae2c98ca1ddfc4957dfe34bbd6a4f201c701bc'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def reports(cur):
    return {day: base.one(cur,
        "select erp.get_owner_financial_snapshot_v2('2026-09-01',%s::date,%s::date)",
        (day, day)) for day in ('2026-09-02', '2026-09-03')}


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1',
                      port='54322', dbname='postgres'):
        raise AssertionError('MISC_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_U_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('MISC_DISPOSABLE_CONFIRMATION_REQUIRED')
    changed_sql = subprocess.check_output(['git', 'diff', '--name-only', U_HEAD,
        'HEAD', '--', 'supabase/migrations', 'supabase/rollbacks'], text=True)
    if changed_sql.strip():
        raise AssertionError('MISC_AUDIT_REQUIRES_UNCHANGED_U_SQL')
    result = dict(head=os.environ.get('GITHUB_SHA'), audited_business_head=U_HEAD,
        classification='NATIVE_POSTGRESQL_AUTHENTICATED_SESSION_U_ADVERSARIAL',
        production_go=False, cases=[], status='FAIL', http_ui_reachability_proven=False)
    # Supabase's postgres role is not a superuser. Use the existing local
    # bootstrap administrator solely to establish real authenticated sessions.
    # No role attributes, grants, schema, or hosted credentials are changed.
    audit_params = dict(params, user='supabase_admin')
    with psycopg.connect(**audit_params, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        cur.execute("select current_user,session_user,rolsuper from pg_roles where rolname=current_user")
        if cur.fetchone() != ('supabase_admin','supabase_admin',True):
            raise AssertionError('MISC_EXISTING_DISPOSABLE_ADMIN_REQUIRED')
        untouched = snapshot(cur)
        if len(runtime.verified_successor(cur)) != 7:
            raise AssertionError('MISC_EXACT_U_RUNTIME_REQUIRED')
        result['engine'] = base.one(cur, 'select version()')
        if AUTH_SOURCE.read_text().count('grant usage on schema public, erp to authenticated;') != 1:
            raise AssertionError('MISC_SCHEMA_ALIGNMENT_SOURCE_MISMATCH')
        result['schema_usage_before_alignment'] = base.one(cur,
            "select has_schema_privilege('authenticated','erp','USAGE')")
        if not result['schema_usage_before_alignment']:
            cur.execute('grant usage on schema erp to authenticated')
        result['schema_alignment_source_sha256'] = hashlib.sha256(AUTH_SOURCE.read_bytes()).hexdigest()
        result['source_definitions'] = []
        for identity in ('erp.post_misc_finance(uuid)', 'erp.reverse_misc_finance(uuid,text)',
                         'erp.get_owner_financial_snapshot_v2(date,date,date)'):
            cur.execute("select pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),p.proacl::text"
                " from pg_proc p where p.oid=%s::regprocedure", (identity,))
            definition, owner, acl = cur.fetchone()
            result['source_definitions'].append(dict(identity=identity, definition=definition,
                sha256=hashlib.sha256(definition.encode()).hexdigest(), owner=owner, acl=acl))
        cur.execute("select set_config('request.jwt.claims',%s,true)",
            (json.dumps(dict(sub=base.OPERATOR_AUTH, role='authenticated')),))
        cur.execute("select set_config('app.change_reason','U adversarial cash-date probe',true)")
        base.load_fixture_foundation(cur)
        cash = base.one(cur, 'select id from erp.cash_accounts where is_active order by id limit 1')
        cur.execute('select category_type,id from erp.misc_finance_categories where is_active')
        categories = dict(cur.fetchall())
        for kind in ('OTHER_INCOME', 'OTHER_EXPENSE'):
            for zone in ('UTC', 'Asia/Jakarta', 'America/New_York', 'Asia/Tokyo'):
                cur.execute('savepoint misc_case')
                before_case = snapshot(cur)
                case = dict(kind=kind, zone=zone, amount='0.03',
                    physical_at='2026-09-03T00:30:00+07', expected_date='2026-09-03')
                try:
                    cur.execute("select set_config('TimeZone',%s,true)", (zone,))
                    cur.execute('set session authorization authenticated')
                    cur.execute('select current_user,session_user,erp.current_app_role()')
                    case['identity'] = dict(zip(('current_user', 'session_user', 'app_role'), cur.fetchone(), strict=True))
                    if case['identity'] != dict(current_user='authenticated', session_user='authenticated', app_role='OWNER'):
                        raise AssertionError('MISC_REAL_OWNER_SESSION_NOT_ESTABLISHED')
                    before = reports(cur)
                    transaction = uuid.uuid4()
                    cur.execute("insert into erp.misc_finance_transactions(id,transaction_number,transaction_type,"
                        "category_id,physical_at,amount,cash_account_id,notes) values(%s,%s,%s,%s,%s,.03,%s,%s)",
                        (transaction, 'U-AUDIT-' + str(transaction), kind, categories[kind], case['physical_at'], cash,
                         'U real-session cash-date counterexample'))
                    if reports(cur) != before:
                        raise AssertionError('MISC_DRAFT_CHANGED_AUTHORITATIVE_REPORT')
                    cur.execute('select erp.post_misc_finance(%s)', (transaction,))
                    after = reports(cur)
                    cur.execute('set session authorization supabase_admin')
                    cur.execute('select current_user,session_user')
                    if cur.fetchone() != ('supabase_admin','supabase_admin'):
                        raise AssertionError('MISC_MEASUREMENT_IDENTITY_NOT_RESTORED')
                    cur.execute("select j.id,j.economic_date::text,j.transaction_date::text,"
                        "(select sum(l.debit)::text from erp.journal_lines l where l.journal_entry_id=j.id),"
                        "(select sum(l.credit)::text from erp.journal_lines l where l.journal_entry_id=j.id)"
                        " from erp.journal_entries j where j.source_type='MISC_FINANCE' and j.source_id=%s", (transaction,))
                    rows = cur.fetchall()
                    if len(rows) != 1 or rows[0][3:] != ('0.03', '0.03'):
                        raise AssertionError('MISC_DOCUMENT_CENTS_OR_JOURNAL_COUNT_WRONG')
                    case['journals'] = [dict(zip(('id','economic_date','transaction_date','debit','credit'), r, strict=True)) for r in rows]
                    wrong_day = any(r[1:3] != (case['expected_date'], case['expected_date']) for r in rows)
                    signed = Decimal('.03') if kind == 'OTHER_INCOME' else Decimal('-.03')
                    case['daily_evidence'] = {}
                    for day in before:
                        delta = Decimal(str(after[day]['financial_position']['cash'])) - Decimal(str(before[day]['financial_position']['cash']))
                        expected = signed if day == case['expected_date'] else Decimal(0)
                        observed = signed if day >= rows[0][1] else Decimal(0)
                        if delta != observed or after[day]['data_confidence']['status'] != 'READY':
                            raise AssertionError('MISC_EXPECTED_REPORT_COUNTEREXAMPLE_NOT_OBSERVED')
                        case['daily_evidence'][day] = dict(expected_cash_delta=str(expected), actual_cash_delta=str(delta),
                            before=before[day], after=after[day])
                    case.update(status='NEW_U_BUG_REPRODUCED' if wrong_day else 'CONTROL_PASS',
                        classification='SILENT_PER_DATE_MISPOSTING' if wrong_day else 'LAWFUL_CONTROL',
                        draft_inert=True, document_cents_conserved=True)
                except Exception as exc:
                    case.update(status='FIXTURE_OR_ORACLE_FAILURE', error=str(exc), sqlstate=getattr(exc,'sqlstate',None))
                finally:
                    # Roll back the failed subtransaction before RESET if SQL errored.
                    cur.execute('rollback to savepoint misc_case')
                    cur.execute('set session authorization supabase_admin')
                    cur.execute('release savepoint misc_case')
                case['full_boundary_restored'] = snapshot(cur) == before_case
                result['cases'].append(case)
                if not case['full_boundary_restored']:
                    raise AssertionError('MISC_CASE_ROLLBACK_LEFT_RESIDUE')
        conn.rollback()
        result['entire_unseeded_runtime_restored'] = snapshot(cur) == untouched
        result['boundary_counts'] = {k: len(v) for k,v in untouched.items() if isinstance(v,list)}
        conn.rollback()
    result['new_bug_reproductions'] = sum(c['status']=='NEW_U_BUG_REPRODUCED' for c in result['cases'])
    result['lawful_controls'] = sum(c['status']=='CONTROL_PASS' for c in result['cases'])
    result['oracle_failures'] = sum(c['status']=='FIXTURE_OR_ORACLE_FAILURE' for c in result['cases'])
    result['candidate_verdict'] = 'FAIL'
    result['proof_status'] = 'COUNTEREXAMPLE_QUALIFIED' if (
        result['new_bug_reproductions']==4 and result['lawful_controls']==4 and
        result['oracle_failures']==0 and result['entire_unseeded_runtime_restored']) else 'INCOMPLETE'
    return result


if __name__ == '__main__':
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run()
    except Exception as exc:
        result = dict(status='FAIL', proof_status='INCOMPLETE', error=str(exc), production_go=False)
    REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','source_definitions')}, default=str))
    # A reproduced financial defect must make the audit job fail.
    raise SystemExit(1)
