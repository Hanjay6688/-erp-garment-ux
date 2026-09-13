#!/usr/bin/env python3
"""Native before/after V oracle using real disposable authenticated SQL sessions."""
import hashlib
import json
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_v2620e_counterexample_regression as base
import cp6_v2620u_runtime as u_runtime
import cp6_v2620v_runtime as v_runtime
from cp6_v2620u_install_diagnostic import snapshot

AUTH_SOURCE = Path('ops/supabase/uat/applied/20260831032949_erp_v2_6_13b_auth_profile_facade_tracking.sql')
MIGRATION = v_runtime.MIGRATION
DETECTOR = 'V2620V_MISC_FINANCE_BUSINESS_DATE'
CORE_ZONES = ('UTC', 'Asia/Jakarta', 'America/New_York', 'Asia/Tokyo')
CONTROLS = ('FUTURE_POST_REFUSAL', 'POSTED_UPDATE_DENIED', 'POSTED_DELETE_DENIED',
    'POST_REPLAY_REFUSAL', 'REVERSE_REPLAY_INCOME', 'REVERSE_REPLAY_EXPENSE',
    'BLANK_REVERSE_REFUSAL', 'DRAFT_DELETE_INERT', 'NON_OWNER_POST_DENIED')
EXTRA_CASES = tuple('EDGE_' + k + '_' + e for k in ('INCOME','EXPENSE') for e in ('BEFORE','AT')) + tuple(
    'NOW_' + k + '_' + z for k in ('INCOME','EXPENSE') for z in ('BEHIND','AHEAD')) + CONTROLS + (
    'DETECTOR_POSTED', 'DETECTOR_REVERSED', 'CLOSED_PERIOD_ECONOMIC_DATE', 'ACL_CONTRACT')


def one(cur, query, params=()):
    return base.one(cur, query, params)


def zone(cur, value):
    cur.execute("select set_config('TimeZone',%s,true)", (value,))


def identity(cur, authenticated=True):
    cur.execute('set session authorization authenticated' if authenticated else 'set session authorization supabase_admin')
    cur.execute('select current_user,session_user')
    wanted = 'authenticated' if authenticated else 'supabase_admin'
    if cur.fetchone() != (wanted, wanted):
        raise AssertionError('V_REAL_SESSION_IDENTITY_MISMATCH')
    if authenticated and one(cur, 'select erp.current_app_role()') != 'OWNER':
        raise AssertionError('V_REAL_OWNER_SESSION_REQUIRED')


def boundary(cur):
    previous = one(cur, "select current_setting('TimeZone')")
    zone(cur, 'UTC')
    try:
        return snapshot(cur)
    finally:
        zone(cur, previous)


def reports(cur, days):
    return {day: one(cur, 'select erp.get_owner_financial_snapshot_v2(%s::date,%s::date,%s::date)',
        (day[:7] + '-01', day, day)) for day in days}


def draft(cur, cash, categories, kind='OTHER_INCOME', physical='2026-09-03T00:30:00+07'):
    transaction = uuid.uuid4()
    cur.execute('insert into erp.misc_finance_transactions(id,transaction_number,transaction_type,'
        'category_id,physical_at,amount,cash_account_id,notes) values(%s,%s,%s,%s,%s,.03,%s,%s)',
        (transaction, 'V-PROOF-' + str(transaction), kind, categories[kind], physical, cash,
         'V canonical cash business-date proof'))
    return transaction


def book(cur, transaction):
    cur.execute("select j.id,j.source_type,j.status,j.economic_date::text,j.transaction_date::text,j.reversal_of_id,"
        "(select sum(l.debit)::text from erp.journal_lines l where l.journal_entry_id=j.id),"
        "(select sum(l.credit)::text from erp.journal_lines l where l.journal_entry_id=j.id)"
        " from erp.journal_entries j where j.source_id=%s or j.reversal_of_id in"
        " (select id from erp.journal_entries where source_type='MISC_FINANCE' and source_id=%s) order by j.id",
        (transaction, transaction))
    return [dict(zip(('id','source_type','status','economic_date','transaction_date','reversal_of_id','debit','credit'),
        r, strict=True)) for r in cur.fetchall()]


def refusal(cur, query, params=(), expected_text=None):
    cur.execute('savepoint expected_refusal')
    error = None
    try:
        cur.execute(query, params)
    except psycopg.Error as exc:
        error = dict(sqlstate=exc.sqlstate, message=str(exc))
    finally:
        cur.execute('rollback to savepoint expected_refusal;release savepoint expected_refusal')
    if error is None or (expected_text and expected_text not in error['message']):
        raise AssertionError('V_WRONG_OR_MISSING_REFUSAL:' + str(error))
    return error


def check_post(cur, transaction, expected, before, kind, posting_date=None):
    after = reports(cur, tuple(before))
    rows = book(cur, transaction)
    if len(rows) != 1 or (rows[0]['economic_date'], rows[0]['transaction_date']) != (expected, posting_date or expected):
        raise AssertionError('V_MISC_JOURNAL_BUSINESS_DATE_MISMATCH:' + str(rows))
    if rows[0]['debit'] != '0.03' or rows[0]['credit'] != '0.03':
        raise AssertionError('V_MISC_EXACT_CENTS_MISMATCH')
    signed = Decimal('.03') if kind == 'OTHER_INCOME' else Decimal('-.03')
    deltas = {}
    for day in before:
        actual = Decimal(str(after[day]['financial_position']['cash'])) - Decimal(str(before[day]['financial_position']['cash']))
        wanted = signed if day >= (posting_date or expected) else Decimal(0)
        if actual != wanted or after[day]['data_confidence']['status'] != 'READY':
            raise AssertionError('V_MISC_PER_DATE_CASH_OR_CONFIDENCE_MISMATCH:' + str((day, actual, wanted, after[day]['data_confidence'])))
        deltas[day] = dict(expected=str(wanted), actual=str(actual), confidence='READY')
    return dict(journals=rows, per_date_cash=deltas, document_cents_conserved=True)


def upgrade_probe(cur, wrong):
    before = boundary(cur)
    source = MIGRATION.read_text()
    if source.count('\nbegin;\n') != 1 or not source.endswith('commit;\n'):
        raise AssertionError('V_UPGRADE_SOURCE_TRANSACTION_SHAPE')
    body = source.replace('\nbegin;\n', '\n', 1).removesuffix('commit;\n')
    cur.execute('savepoint v_upgrade_probe')
    error = None
    try:
        cur.execute(body, prepare=False)
        if one(cur, 'select count(*) from erp.cp6_v2620v_rollback_capsule') != 3:
            raise AssertionError('V_LAWFUL_HISTORY_CAPSULE_CARDINALITY')
    except psycopg.Error as exc:
        error = str(exc)
    finally:
        cur.execute('rollback to savepoint v_upgrade_probe;release savepoint v_upgrade_probe')
    if wrong != bool(error) or (wrong and 'V_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED' not in error):
        raise AssertionError('V_UPGRADE_HISTORY_GATE_MISMATCH:' + str(error))
    if boundary(cur) != before:
        raise AssertionError('V_UPGRADE_PROBE_LEFT_RESIDUE')
    return dict(invalid_history_refused=wrong, lawful_history_accepted=not wrong,
        full_boundary_exact=True, error=error)


def core(cur, cash, categories, kind, timezone, fixed):
    zone(cur, timezone)
    identity(cur)
    before = reports(cur, ('2026-09-02', '2026-09-03'))
    transaction = draft(cur, cash, categories, kind)
    if reports(cur, tuple(before)) != before:
        raise AssertionError('V_DRAFT_CHANGED_AUTHORITATIVE_REPORT')
    cur.execute('select erp.post_misc_finance(%s)', (transaction,))
    if one(cur, "select current_setting('TimeZone')") != timezone:
        raise AssertionError('V_FUNCTION_LEAKED_SESSION_TIMEZONE')
    after = reports(cur, tuple(before))
    identity(cur, False)
    rows = book(cur, transaction)
    if len(rows) != 1 or rows[0]['debit'] != '0.03' or rows[0]['credit'] != '0.03':
        raise AssertionError('V_DOCUMENT_CENTS_OR_COUNT')
    wrong = rows[0]['economic_date'] != '2026-09-03'
    expected_wrong = not fixed and timezone in ('UTC', 'America/New_York')
    if wrong != expected_wrong or rows[0]['transaction_date'] != rows[0]['economic_date']:
        raise AssertionError('V_BEFORE_AFTER_DATE_ORACLE_MISMATCH')
    signed = Decimal('.03') if kind == 'OTHER_INCOME' else Decimal('-.03')
    evidence = {}
    for day in before:
        delta = Decimal(str(after[day]['financial_position']['cash'])) - Decimal(str(before[day]['financial_position']['cash']))
        observed = signed if day >= rows[0]['economic_date'] else Decimal(0)
        if delta != observed or after[day]['data_confidence']['status'] != 'READY':
            raise AssertionError('V_CORE_CASH_OR_CONFIDENCE_MISMATCH')
        evidence[day] = dict(expected_cash_delta=str(signed if day >= '2026-09-03' else Decimal(0)),
            actual_cash_delta=str(delta), before=before[day], after=after[day])
    result = dict(status='PASS' if fixed else 'KNOWN_U_BUG_REPRODUCED' if wrong else 'CONTROL_PASS',
        classification='SILENT_PER_DATE_MISPOSTING' if wrong else 'LAWFUL_CONTROL',
        kind=kind, zone=timezone, physical_at='2026-09-03T00:30:00+07', expected_date='2026-09-03',
        identity=dict(current_user='authenticated',session_user='authenticated',app_role='OWNER'),
        journals=rows, daily_evidence=evidence, draft_inert=True, document_cents_conserved=True)
    if not fixed:
        result['upgrade_guard'] = upgrade_probe(cur, wrong)
    return result


def extra(cur, cash, categories, name):
    zone(cur, 'Asia/Jakarta')
    identity(cur)
    if name.startswith(('EDGE_', 'NOW_')):
        kind = 'OTHER_EXPENSE' if 'EXPENSE' in name else 'OTHER_INCOME'
        if name.startswith('EDGE_'):
            physical = '2026-09-02T23:59:59.999999+07' if name.endswith('BEFORE') else '2026-09-03T00:00:00+07'
            expected = physical[:10]
            posting_zone = 'UTC'
        else:
            physical, expected = cur.execute("select current_timestamp,((current_timestamp at time zone 'Asia/Jakarta')::date)::text").fetchone()
            posting_zone = 'Etc/GMT+12' if name.endswith('BEHIND') else 'Pacific/Kiritimati'
        days = ((date.fromisoformat(expected)-timedelta(days=1)).isoformat(), expected)
        zone(cur, 'Asia/Tokyo')
        before = reports(cur, days)
        transaction = draft(cur, cash, categories, kind, physical)
        zone(cur, posting_zone)
        cur.execute('select erp.post_misc_finance(%s)', (transaction,))
        zone(cur, 'America/New_York')
        identity(cur, False)
        return check_post(cur, transaction, expected, before, kind)
    if name == 'ACL_CONTRACT':
        identity(cur, False)
        cur.execute("select p.oid::regprocedure::text,p.prosecdef,p.proconfig,pg_get_userbyid(p.proowner),"
            "has_function_privilege('anon',p.oid,'EXECUTE'),has_function_privilege('authenticated',p.oid,'EXECUTE'),"
            "has_function_privilege('service_role',p.oid,'EXECUTE'),"
            "exists(select 1 from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a where a.grantee=0 and a.privilege_type='EXECUTE')"
            " from pg_proc p where p.oid in('erp.post_misc_finance(uuid)'::regprocedure,'erp.reverse_misc_finance(uuid,text)'::regprocedure) order by 1")
        rows = cur.fetchall()
        if len(rows) != 2 or any(not r[1] or 'search_path=erp, public' not in r[2] or r[3:] != ('postgres',False,True,r[0]=='erp.post_misc_finance(uuid)',False) for r in rows):
            raise AssertionError('V_MISC_ENTRYPOINT_SECURITY_CONTRACT:' + str(rows))
        for role in ('anon','authenticated','service_role'):
            if one(cur, "select has_table_privilege(%s,'erp.cp6_v2620v_rollback_capsule','SELECT')", (role,)):
                raise AssertionError('V_PRIVATE_CAPSULE_EXPOSED')
        return dict(entrypoints=rows, private_capsule_denial=True, http_ui_reachability_proven=False)
    if name.startswith('DETECTOR_'):
        identity(cur, False)
        current = one(cur, "select pg_get_functiondef('erp.post_misc_finance(uuid)'::regprocedure)")
        predecessor = one(cur, "select object_definition from erp.cp6_v2620v_rollback_capsule where object_regidentity='erp.post_misc_finance(uuid)'")
        cur.execute(predecessor, prepare=False)
        zone(cur, 'UTC');identity(cur)
        transaction = draft(cur, cash, categories)
        cur.execute('select erp.post_misc_finance(%s)', (transaction,))
        if name == 'DETECTOR_REVERSED':
            cur.execute("select erp.reverse_misc_finance(%s,'V controlled predecessor replay')", (transaction,))
        identity(cur, False);cur.execute(current, prepare=False)
        counts = [one(cur, 'select coalesce(sum(issue_count),0) from erp.' + function + '() where check_name=%s and severity=%s',
            (DETECTOR, 'CRITICAL')) for function in ('run_v267_financial_truth_checks','run_v268_financial_report_checks')]
        report = reports(cur, ('2026-09-03',))['2026-09-03']['data_confidence']['status']
        if counts != [1,1] or report != 'BLOCKED':
            raise AssertionError('V_DATE_DETECTOR_OR_REPORT_SCOPE_MISSING')
        return dict(counts=counts, report=report, controlled_tester_predecessor_replay=True,
            runtime_definition_restored=True, operator_ddl_ability_claimed=False)
    if name == 'CLOSED_PERIOD_ECONOMIC_DATE':
        identity(cur, False)
        cur.execute("update erp.accounting_period_control set closed_through='2026-09-03'")
        identity(cur)
        posting = one(cur,"select ((current_timestamp at time zone 'Asia/Jakarta')::date)::text")
        before = reports(cur, ('2026-09-02', '2026-09-03', posting))
        transaction = draft(cur, cash, categories)
        zone(cur, 'UTC');cur.execute('select erp.post_misc_finance(%s)', (transaction,))
        identity(cur, False)
        # Preserve economic_date; the accounting report follows the lawful posting date in the open period.
        return check_post(cur, transaction, '2026-09-03', before, 'OTHER_INCOME', posting_date=posting)
    kind = 'OTHER_EXPENSE' if name == 'REVERSE_REPLAY_EXPENSE' else 'OTHER_INCOME'
    physical = one(cur, "select (((current_timestamp at time zone 'Asia/Jakarta')::date+1)::text||'T00:30:00+07')") if name == 'FUTURE_POST_REFUSAL' else '2026-09-03T00:30:00+07'
    transaction = draft(cur, cash, categories, kind, physical)
    if name in ('FUTURE_POST_REFUSAL','NON_OWNER_POST_DENIED'):
        if name == 'NON_OWNER_POST_DENIED':
            cur.execute("select set_config('request.jwt.claims',%s,true)", (json.dumps(dict(sub=str(uuid.uuid4()),role='authenticated')),))
        error = refusal(cur, 'select erp.post_misc_finance(%s)', (transaction,))
        identity(cur, False)
        if one(cur, 'select status from erp.misc_finance_transactions where id=%s', (transaction,)) != 'DRAFT' or book(cur, transaction):
            raise AssertionError('V_REFUSAL_CHANGED_DRAFT_OR_LEDGER')
        return dict(refusal=error, atomic=True)
    if name == 'DRAFT_DELETE_INERT':
        cur.execute('delete from erp.misc_finance_transactions where id=%s', (transaction,))
        identity(cur, False)
        if one(cur, 'select count(*) from erp.misc_finance_transactions where id=%s', (transaction,)) or book(cur, transaction):
            raise AssertionError('V_DRAFT_DELETE_MUTATED_LEDGER')
        return dict(draft_delete_inert=True)
    cur.execute('select erp.post_misc_finance(%s)', (transaction,))
    identity(cur, False);before = boundary(cur);identity(cur)
    if name.startswith('REVERSE_REPLAY_'):
        zone(cur, 'Etc/GMT+12')
        cur.execute("select erp.reverse_misc_finance(%s,'V lawful append-only inverse')", (transaction,))
        identity(cur, False)
        first = boundary(cur);rows = book(cur, transaction)
        if len(rows) != 2:
            raise AssertionError('V_INVERSE_CARDINALITY')
        original = next(r for r in rows if r['source_type']=='MISC_FINANCE')
        inverse = next(r for r in rows if r['source_type']=='JOURNAL_REVERSAL')
        if inverse['reversal_of_id'] != original['id'] or inverse['economic_date'] < original['economic_date']:
            raise AssertionError('V_INVERSE_LINEAGE_OR_CHRONOLOGY')
        cash_delta = one(cur, 'select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l where l.journal_entry_id=any(%s::uuid[]) and l.account_id=(select coa_account_id from erp.cash_accounts where id=%s)',
            ([r['id'] for r in rows],cash))
        if cash_delta != Decimal(0):
            raise AssertionError('V_INVERSE_CASH_NOT_ZERO')
        identity(cur);zone(cur, 'Pacific/Kiritimati')
        cur.execute("select erp.reverse_misc_finance(%s,'V lawful append-only inverse')", (transaction,))
        identity(cur, False)
        if boundary(cur) != first:
            raise AssertionError('V_INVERSE_REPLAY_CHANGED_FACTS')
        return dict(journals=rows, cash_delta=str(cash_delta), exact_replay_inert=True)
    queries = {
        'POSTED_UPDATE_DENIED':'update erp.misc_finance_transactions set amount=.07 where id=%s',
        'POSTED_DELETE_DENIED':'delete from erp.misc_finance_transactions where id=%s',
        'POST_REPLAY_REFUSAL':'select erp.post_misc_finance(%s)',
        'BLANK_REVERSE_REFUSAL':"select erp.reverse_misc_finance(%s,'')",
    }
    error = refusal(cur, queries[name], (transaction,))
    identity(cur, False)
    if boundary(cur) != before:
        raise AssertionError('V_REFUSAL_CHANGED_POSTED_FACTS')
    return dict(refusal=error, complete_boundary_inert=True)


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres',password='postgres',host='127.0.0.1',port='54322',dbname='postgres') or os.environ.get('CP6_V_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('V_CANONICAL_DISPOSABLE_ENDPOINT_REQUIRED')
    phase = os.environ.get('CP6_V_PHASE')
    if phase not in ('BEFORE_V','AFTER_V'):
        raise AssertionError('V_UNKNOWN_PHASE')
    fixed = phase == 'AFTER_V'
    result = dict(head=os.environ.get('GITHUB_SHA','LOCAL_UNBOUND'), production_go=False,
        classification='NATIVE_POSTGRESQL_REAL_AUTHENTICATED_SESSION_' + phase,
        phase=phase, status='FAIL', cases={}, expanded_cases={}, http_ui_reachability_proven=False)
    with psycopg.connect(**dict(params,user='supabase_admin'), autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        if not one(cur, 'select rolsuper from pg_roles where rolname=current_user'):
            raise AssertionError('V_EXISTING_DISPOSABLE_BOOTSTRAP_ADMIN_REQUIRED')
        untouched = boundary(cur)
        u = u_runtime.verified_successor(cur);v = v_runtime.verified_successor(cur)
        if len(u) != 7 or bool(v) != fixed or (fixed and len(v) != 3):
            raise AssertionError('V_RUNTIME_PHASE_MISMATCH')
        result['runtime'] = dict(engine=one(cur,'select version()'), verified_u_functions=len(u),
            verified_v_functions=len(v), installed_function_hashes=list(v.values()))
        if AUTH_SOURCE.read_text().count('grant usage on schema public, erp to authenticated;') != 1:
            raise AssertionError('V_SCHEMA_ALIGNMENT_SOURCE_MISMATCH')
        result['schema_alignment_source_sha256'] = hashlib.sha256(AUTH_SOURCE.read_bytes()).hexdigest()
        result['schema_usage_before_alignment'] = one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
        if not result['schema_usage_before_alignment']:
            cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)", (json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
        cur.execute("select set_config('app.change_reason','V date regression',true)")
        base.load_fixture_foundation(cur)
        cash = one(cur, 'select id from erp.cash_accounts where is_active order by id limit 1')
        cur.execute('select category_type,id from erp.misc_finance_categories where is_active');categories = dict(cur.fetchall())
        specs = [('cases',kind + '/' + z,lambda k=kind,tz=z:core(cur,cash,categories,k,tz,fixed))
            for kind in ('OTHER_INCOME','OTHER_EXPENSE') for z in CORE_ZONES]
        if fixed:
            specs += [('expanded_cases',name,lambda n=name:extra(cur,cash,categories,n)) for name in EXTRA_CASES]
        for group,name,operation in specs:
            cur.execute('savepoint v_case');before = boundary(cur)
            try:
                case = operation();case.setdefault('status','PASS')
            except Exception as exc:
                case = dict(status='FAIL',error=str(exc),sqlstate=getattr(exc,'sqlstate',None))
            finally:
                cur.execute('rollback to savepoint v_case');identity(cur,False)
                cur.execute('release savepoint v_case')
            case['full_boundary_restored'] = boundary(cur) == before
            if not case['full_boundary_restored']:
                raise AssertionError('V_CASE_ROLLBACK_RESIDUE:' + name)
            result[group][name] = case
        conn.rollback();result['entire_unseeded_runtime_restored'] = boundary(cur) == untouched;conn.rollback()
    expected = {'PASS'} if fixed else {'KNOWN_U_BUG_REPRODUCED','CONTROL_PASS'}
    success = all(c['status'] in expected and c['full_boundary_restored'] for c in result['cases'].values())
    success = success and all(c['status']=='PASS' and c['full_boundary_restored'] for c in result['expanded_cases'].values())
    if not fixed:
        success = success and sum(c['status']=='KNOWN_U_BUG_REPRODUCED' for c in result['cases'].values()) == 4
    result['status'] = 'PASS' if success and result['entire_unseeded_runtime_restored'] else 'FAIL'
    return result


if __name__ == '__main__':
    phase = os.environ.get('CP6_V_PHASE','UNKNOWN')
    report = Path('cp6-proof/CP6_V2620V_' + ('U_COUNTEREXAMPLES' if phase=='BEFORE_V' else 'MISC_FINANCE_BUSINESS_DATE_REGRESSION') + '.json')
    try:
        result = run()
    except Exception as exc:
        result = dict(status='FAIL',error=str(exc),phase=phase,production_go=False)
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','expanded_cases','runtime')},default=str))
    raise SystemExit(0 if result['status']=='PASS' else 1)
