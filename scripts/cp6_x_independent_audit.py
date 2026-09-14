#!/usr/bin/env python3
"""Independent X audit on frozen business SQL, using disposable native PostgreSQL.

Exit 1 is a qualified counterexample; exit 2 is incomplete/fixture evidence.
Synthetic JWT claims prove SQL authorization, never signed JWT or HTTP reachability.
The ordinary document calls below use a real authenticated session. Only fixture
foundation, role revocation, and full catalog observations use disposable admin.
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
import cp6_v2620f_final_runtime_regression as laundry_fixture
import cp6_v2620h_adversarial_regression as sales_fixture
import cp6_v2620w_scrap_business_date_regression as scrap
import cp6_v2620x_internal_role_regression as actors
import cp6_v2620x_runtime as runtime

HEAD_X = 'fa3f76c74b169d4869721a203650be60cd866160'
TREE_X = '582436e12e9c96f123485e8b1a062f6992269bbb'
REPORT = Path('cp6-proof/CP6_X_INDEPENDENT_AUDIT.json')
KINDS = ('CUSTOMER_RECEIVABLE', 'CONTRACTOR_RECEIVABLE', 'SUPPLIER_PAYABLE',
         'VENDOR_PAYABLE', 'CONTRACTOR_PAYABLE')
ZONES = ('UTC', 'Asia/Jakarta', 'America/New_York', 'Asia/Tokyo')
PHYSICAL = '2026-09-03T00:30:00+07:00'
one, boundary = base.one, scrap.boundary


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def zone(cur, name):
    cur.execute("select set_config('TimeZone',%s,true)", (name,))


def owner(cur):
    actors.claims(cur, dict(sub=base.OPERATOR_AUTH, role='authenticated'))
    actors.session(cur, 'authenticated')
    cur.execute('select current_user,session_user,erp.current_app_role()')
    if cur.fetchone() != ('authenticated', 'authenticated', 'OWNER'):
        raise AssertionError('INDEPENDENT_REAL_OWNER_SESSION_REQUIRED')


def admin(cur):
    actors.session(cur, 'supabase_admin')


def opening(cur, kind):
    """Ordinary draft -> posting; no synthetic posted balance or ledger writes."""
    h, item = uuid.uuid4(), uuid.uuid4()
    customer = None
    if kind == 'CUSTOMER_RECEIVABLE':
        customer = uuid.uuid4()
        cur.execute('insert into erp.customers(id,customer_code,customer_name,is_active) '
                    'values(%s,%s,%s,true)',
                    (customer, 'X-AUD-C-' + customer.hex[:16], 'Independent X customer'))
    contractor = one(cur, 'select id from erp.contractors where is_active order by id limit 1') if kind.startswith('CONTRACTOR_') else None
    cur.execute('insert into erp.opening_balance_headers(id,opening_number,opening_date,status) '
                "values(%s,%s,'2026-09-01','DRAFT')", (h, 'X-AUD-OPEN-' + str(h)))
    cur.execute('insert into erp.opening_balance_items'
                '(id,opening_id,balance_type,customer_id,supplier_id,vendor_id,contractor_id,amount) '
                'values(%s,%s,%s,%s,%s,%s,%s,.10)',
                (item, h, kind, customer,
                 'c8c30000-0000-4000-8000-000000000001' if kind == 'SUPPLIER_PAYABLE' else None,
                 base.VENDOR if kind == 'VENDOR_PAYABLE' else None, contractor))
    cur.execute('select erp.post_opening_balance(%s)', (h,))
    ident = one(cur, 'select id from erp.opening_subledger_balances where opening_item_id=%s', (item,))
    if ident is None:
        raise AssertionError('INDEPENDENT_OPENING_POST_DID_NOT_CREATE_BALANCE')
    return ident


def cash_reports(cur):
    return scrap.reports(cur, ('2026-09-02', '2026-09-03'))


def settlement_date(cur, cash, kind, posting_zone):
    zone(cur, 'Asia/Jakarta')
    owner(cur)
    balance = opening(cur, kind)
    before = cash_reports(cur)
    if any(r['data_confidence']['status'] != 'READY' for r in before.values()):
        raise AssertionError('INDEPENDENT_OPENING_FIXTURE_NOT_READY')
    ident = uuid.uuid4()
    zone(cur, 'Asia/Tokyo')
    cur.execute('insert into erp.opening_subledger_settlements'
                '(id,balance_id,settlement_number,physical_at,amount,cash_account_id,status) '
                "values(%s,%s,%s,%s,.03,%s,'DRAFT')",
                (ident, balance, 'X-AUD-SETTLE-' + str(ident), PHYSICAL, cash))
    if cash_reports(cur) != before:
        raise AssertionError('INDEPENDENT_SETTLEMENT_DRAFT_CHANGED_REPORT')
    zone(cur, posting_zone)
    cur.execute('select erp.post_opening_subledger_settlement(%s)', (ident,))
    if one(cur, "select current_setting('TimeZone')") != posting_zone:
        raise AssertionError('INDEPENDENT_SETTLEMENT_LEAKED_TIMEZONE')
    # Another timezone change after the call separates report and posting dates.
    zone(cur, 'Pacific/Kiritimati')
    after = cash_reports(cur)
    admin(cur)
    cur.execute('select s.status,b.original_amount,b.settled_amount,b.status '
                'from erp.opening_subledger_settlements s '
                'join erp.opening_subledger_balances b on b.id=s.balance_id where s.id=%s', (ident,))
    state = cur.fetchone()
    if state != ('POSTED', Decimal('.10'), Decimal('.03'), 'PARTIAL'):
        raise AssertionError('INDEPENDENT_SETTLEMENT_STATE_OR_CENTS:' + str(state))
    cur.execute("select j.id::text,j.status,j.economic_date::text,j.transaction_date::text,"
                '(select sum(l.debit)::text from erp.journal_lines l where l.journal_entry_id=j.id),'
                '(select sum(l.credit)::text from erp.journal_lines l where l.journal_entry_id=j.id) '
                "from erp.journal_entries j where j.source_type='OPENING_SUBLEDGER_SETTLEMENT' and j.source_id=%s", (ident,))
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][1] != 'POSTED' or rows[0][4:] != ('0.03', '0.03'):
        raise AssertionError('INDEPENDENT_SETTLEMENT_JOURNAL_OR_CENTS:' + str(rows))
    expected = datetime.fromisoformat(PHYSICAL).astimezone(ZoneInfo('Asia/Jakarta')).date().isoformat()
    session_day = datetime.fromisoformat(PHYSICAL).astimezone(ZoneInfo(posting_zone)).date().isoformat()
    actual_day = rows[0][2]
    if actual_day not in {expected, session_day} or rows[0][3] != actual_day:
        raise AssertionError('INDEPENDENT_UNQUALIFIED_DATE_OBSERVATION:' + str(rows))
    sign = Decimal(1) if kind.endswith('RECEIVABLE') else Decimal(-1)
    daily = {}
    for day in before:
        delta = Decimal(str(after[day]['financial_position']['cash'])) - Decimal(str(before[day]['financial_position']['cash']))
        observed = sign * Decimal('.03') if day >= actual_day else Decimal(0)
        expected_delta = sign * Decimal('.03') if day >= expected else Decimal(0)
        if delta != observed:
            raise AssertionError('INDEPENDENT_JOURNAL_REPORT_DISAGREEMENT:' + str((day, delta, observed)))
        daily[day] = dict(expected_cash_delta=str(expected_delta), actual_cash_delta=str(delta),
                          confidence=after[day]['data_confidence']['status'], before=before[day], after=after[day])
    cur.execute('select * from erp.run_v267_financial_truth_checks()')
    truth = cur.fetchall()
    return dict(status='NEW_X_BUG_REPRODUCED' if actual_day != expected else 'CONTROL_PASS',
                severity='P2' if actual_day != expected else None,
                classification='SILENT_PER_DATE_CASH_MISPOSTING' if actual_day != expected else 'LAWFUL_CONTROL',
                kind=kind, zone=posting_zone, physical_at=PHYSICAL, expected_date=expected,
                session_date=session_day, actual_date=actual_day, amount='0.03',
                identity=dict(current_user='authenticated', session_user='authenticated', app_role='OWNER'),
                balance_id=str(balance), settlement_id=str(ident), state=state, journals=rows,
                daily_evidence=daily, financial_truth_checks=truth, draft_inert=True,
                total_cents_conserved=True, caller_timezone_preserved=True,
                http_ui_reachability_proven=False)


def payment_date(cur, cash, kind, posting_zone, noon_control=False):
    """Sourced invoice fixture; the tested payment itself uses actual OWNER SQL."""
    admin(cur)
    actors.claims(cur, dict(sub=base.OPERATOR_AUTH, role='authenticated'))
    zone(cur, 'Asia/Jakarta')
    if kind == 'SALES_PAYMENT':
        parent = sales_fixture.opening_sale(cur, 'X-PAY')['sale']
        table, parent_key, function = 'sales_payments', 'sale_id', 'post_sales_payment'
        physical = '2026-09-04T12:00:00+07:00' if noon_control else '2026-09-04T00:30:00+07:00'
        days, sign = ('2026-09-03', '2026-09-04'), Decimal(1)
    else:
        fixture = base.setup_tiny_fg(cur, '9', 4)
        parent = laundry_fixture.finalize_laundry_invoice(cur, fixture['receipt_line'], Decimal('.01'))
        table, parent_key, function = 'vendor_payments', 'vendor_invoice_id', 'post_vendor_payment'
        physical = '2026-09-05T00:30:00+07:00'
        days, sign = ('2026-09-04', '2026-09-05'), Decimal(-1)
    owner(cur)
    before = scrap.reports(cur, days)
    if any(r['data_confidence']['status'] != 'READY' for r in before.values()):
        raise AssertionError('INDEPENDENT_PAYMENT_FIXTURE_NOT_READY')
    ident = uuid.uuid4()
    # Table, column and function identifiers come exclusively from the two
    # literal cases above, never external input.
    cur.execute('insert into erp.' + table + '(id,' + parent_key + ',payment_number,payment_date,amount,cash_account_id,status) '
                "values(%s,%s,%s,%s,.03,%s,'DRAFT')",
                (ident, parent, 'X-AUD-PAY-' + str(ident), physical, cash))
    if scrap.reports(cur, days) != before:
        raise AssertionError('INDEPENDENT_PAYMENT_DRAFT_CHANGED_REPORT')
    zone(cur, posting_zone)
    cur.execute('select erp.' + function + '(%s)', (ident,))
    if one(cur, "select current_setting('TimeZone')") != posting_zone:
        raise AssertionError('INDEPENDENT_PAYMENT_LEAKED_TIMEZONE')
    zone(cur, 'Pacific/Kiritimati')
    after = scrap.reports(cur, days)
    admin(cur)
    if one(cur, 'select status from erp.' + table + ' where id=%s', (ident,)) != 'POSTED':
        raise AssertionError('INDEPENDENT_PAYMENT_NOT_POSTED')
    cur.execute("select j.id::text,j.status,j.economic_date::text,j.transaction_date::text,"
                '(select sum(l.debit)::text from erp.journal_lines l where l.journal_entry_id=j.id),'
                '(select sum(l.credit)::text from erp.journal_lines l where l.journal_entry_id=j.id) '
                'from erp.journal_entries j where j.source_type=%s and j.source_id=%s', (kind, ident))
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][1] != 'POSTED' or rows[0][4:] != ('0.03', '0.03'):
        raise AssertionError('INDEPENDENT_PAYMENT_JOURNAL_OR_CENTS:' + str(rows))
    instant = datetime.fromisoformat(physical)
    expected = instant.astimezone(ZoneInfo('Asia/Jakarta')).date().isoformat()
    effective_zone = 'UTC' if kind == 'SALES_PAYMENT' else posting_zone
    legacy_day = instant.astimezone(ZoneInfo(effective_zone)).date().isoformat()
    actual_day = rows[0][2]
    if actual_day not in {expected, legacy_day} or rows[0][3] != actual_day:
        raise AssertionError('INDEPENDENT_PAYMENT_DATE_NOT_QUALIFIED:' + str(rows))
    daily = {}
    for day in days:
        actual = Decimal(str(after[day]['financial_position']['cash'])) - Decimal(str(before[day]['financial_position']['cash']))
        observed = sign * Decimal('.03') if day >= actual_day else Decimal(0)
        expected_delta = sign * Decimal('.03') if day >= expected else Decimal(0)
        if actual != observed:
            raise AssertionError('INDEPENDENT_PAYMENT_REPORT_DISAGREEMENT:' + str((day, actual, observed)))
        daily[day] = dict(expected_cash_delta=str(expected_delta), actual_cash_delta=str(actual),
                          confidence=after[day]['data_confidence']['status'], before=before[day], after=after[day])
    facts = []
    if kind == 'SALES_PAYMENT':
        cur.execute('select to_jsonb(f) from erp.sales_payment_posting_facts f where payment_id=%s', (ident,))
        facts = [r[0] for r in cur.fetchall()]
        if len(facts) != 1 or Decimal(str(facts[0]['amount'])) != Decimal('.03'):
            raise AssertionError('INDEPENDENT_PAYMENT_FACT_CARDINALITY_OR_CENTS')
    return dict(status='NEW_X_BUG_REPRODUCED' if actual_day != expected else 'CONTROL_PASS',
                severity='P2' if actual_day != expected else None,
                classification='SILENT_PER_DATE_CASH_MISPOSTING' if actual_day != expected else 'LAWFUL_CONTROL',
                kind=kind, zone=posting_zone, effective_function_timezone=effective_zone,
                physical_at=physical, expected_date=expected, actual_date=actual_day,
                payment_id=str(ident), parent_id=str(parent), journals=rows, payment_facts=facts,
                amount='0.03', daily_evidence=daily, draft_inert=True, total_cents_conserved=True,
                identity=dict(current_user='authenticated', session_user='authenticated', app_role='OWNER'),
                fixture_preparation='Existing posted opening-FG/sale or laundry receipt/invoice workflow under disposable admin',
                caller_timezone_preserved=True, http_ui_reachability_proven=False)


def revoked_actor(cur, cash, revoke_role):
    """Same JWT and draft, with permission removed before a new statement."""
    admin(cur)
    subject, expected, fixture = actors.actor(cur, 'ADMIN_CONTROL')
    if expected != 'ADMIN':
        raise AssertionError('INDEPENDENT_ADMIN_FIXTURE')
    actors.session(cur, 'authenticated')
    ident = scrap.draft(cur, cash)
    admin(cur)
    if revoke_role:
        cur.execute("update erp.app_roles set is_active=false where role_code='ADMIN'")
    else:
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (subject,))
    before = boundary(cur)
    actors.session(cur, 'authenticated')
    if one(cur, 'select erp.current_app_role()') is not None:
        raise AssertionError('INDEPENDENT_REVOCATION_NOT_EFFECTFUL')
    cur.execute('savepoint denied_call')
    error = None
    try:
        cur.execute('select erp.post_scrap_sale(%s)', (ident,))
    except psycopg.Error as exc:
        error = dict(sqlstate=exc.sqlstate, message=str(exc))
        cur.execute('rollback to savepoint denied_call')
    cur.execute('release savepoint denied_call')
    admin(cur)
    if error is None or 'Internal ERP access required' not in error['message']:
        raise AssertionError('INDEPENDENT_REVOCATION_NOT_DENIED:' + str(error))
    if boundary(cur) != before:
        raise AssertionError('INDEPENDENT_REVOCATION_REFUSAL_NOT_ATOMIC')
    if revoke_role:
        cur.execute("update erp.app_roles set is_active=true where role_code='ADMIN'")
    else:
        cur.execute('update erp.app_users set is_active=true where auth_user_id=%s', (subject,))
    actors.session(cur, 'authenticated')
    if one(cur, 'select erp.current_app_role()') != 'ADMIN':
        raise AssertionError('INDEPENDENT_REACTIVATION_NOT_EFFECTFUL')
    cur.execute('select erp.post_scrap_sale(%s)', (ident,))
    admin(cur)
    if one(cur, 'select status from erp.scrap_sales where id=%s', (ident,)) != 'POSTED':
        raise AssertionError('INDEPENDENT_REACTIVATED_CONTROL_NOT_POSTED')
    return dict(status='CONTROL_PASS', classification='ATOMIC_REFUSAL_THEN_AUTHORIZED_CONTROL',
                same_subject=str(subject), same_document=str(ident), revoked_role=revoke_role,
                refusal=error, refusal_boundary_exact=True, reactivated_posted=True,
                fixture=fixture, concurrent_revocation_proven=False)


def context_acl(cur):
    admin(cur)
    tables = ('cutting_bridge_execution_context', 'bs_resolution_execution_context', 'cp6_laundry_qc_execution_context')
    result = []
    for table in tables:
        for role in ('anon', 'authenticated'):
            for permission in ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'):
                allowed = one(cur, 'select has_table_privilege(%s,%s,%s)', (role, 'erp.' + table, permission))
                result.append(dict(table=table, role=role, privilege=permission, allowed=allowed))
                if allowed:
                    raise AssertionError('INDEPENDENT_CONTEXT_PRIVILEGE_EXPOSED:' + str(result[-1]))
    return dict(status='CONTROL_PASS', classification='CATALOG_AUTHORIZATION_CONTROL', privileges=result,
                runtime_permission_context_spoofing_proven=False)


def run(phase='X_AUDIT', extensions=None):
    global REPORT
    if phase not in ('X_AUDIT', 'BEFORE_Y', 'AFTER_Y'):
        raise AssertionError('INDEPENDENT_UNKNOWN_RUNTIME_PHASE')
    if phase != 'X_AUDIT':
        REPORT = Path('cp6-proof/CP6_V2620Y_' + ('X_COUNTEREXAMPLES' if phase == 'BEFORE_Y' else 'CASH_BUSINESS_DATE_REGRESSION') + '.json')
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1', port='54322', dbname='postgres'):
        raise AssertionError('INDEPENDENT_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_X_INDEPENDENT_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('INDEPENDENT_DISPOSABLE_CONFIRMATION_REQUIRED')
    if git('rev-parse', HEAD_X + '^{tree}') != TREE_X:
        raise AssertionError('INDEPENDENT_FROZEN_X_TREE_MISMATCH')
    changed = set(git('diff', '--name-only', HEAD_X, 'HEAD', '--', 'supabase/migrations', 'supabase/rollbacks').splitlines())
    allowed = set() if phase == 'X_AUDIT' else {
        'supabase/migrations/20260914043146_erp_v2_6_20y_cp6_cash_business_dates.sql',
        'supabase/rollbacks/20260914043146_erp_v2_6_20y_cp6_cash_business_dates.rollback.sql',
    }
    modified_history = git('diff', '--diff-filter=MDRTCUXB', '--name-only', HEAD_X, 'HEAD', '--', 'supabase/migrations', 'supabase/rollbacks')
    if changed - allowed or modified_history:
        raise AssertionError('INDEPENDENT_REQUIRES_UNCHANGED_X_BUSINESS_SQL')
    head = git('rev-parse', 'HEAD')
    if os.environ.get('GITHUB_SHA') != head:
        raise AssertionError('INDEPENDENT_EXACT_NATIVE_CHECKOUT_REQUIRED')
    result = dict(format='CP6_X_INDEPENDENT_AUDIT_V1', status='INCOMPLETE', head=head,
                  tree=git('rev-parse', 'HEAD^{tree}'), parents=git('show', '-s', '--format=%P', 'HEAD').split(),
                  audited_business_head=HEAD_X, audited_business_tree=TREE_X,
                  run_id=os.environ.get('GITHUB_RUN_ID'), run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
                  production_go=False, synthetic_jwt_context=True, http_ui_reachability_proven=False,
                  cases={}, sources={}, phase=phase, original_independent_run=34805891046)
    for name in (Path(__file__).resolve().relative_to(Path.cwd()), runtime.MIGRATION):
        data = name.read_bytes()
        result['sources'][str(name)] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    with psycopg.connect(**dict(params, user='supabase_admin'), autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        untouched = boundary(cur)
        if len(runtime.verified_successor(cur)) != 1:
            raise AssertionError('INDEPENDENT_VERIFIED_X_RUNTIME_REQUIRED')
        import cp6_v2620y_runtime as y_runtime
        successor = y_runtime.verified_successor(cur)
        if bool(successor) != (phase == 'AFTER_Y') or (successor and len(successor) != 6):
            raise AssertionError('INDEPENDENT_Y_RUNTIME_PHASE_MISMATCH')
        result['verified_y_functions'] = list(successor.values())
        result['runtime_generation'] = 'Y' if successor else 'X'
        result['engine'] = one(cur, 'select version()')
        result['runtime_before'] = untouched
        usage = one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        result['schema_usage_before_alignment'] = usage
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        actors.claims(cur, dict(sub=base.OPERATOR_AUTH, role='authenticated'))
        cur.execute("select set_config('app.change_reason','Independent disposable X audit',true)")
        base.load_fixture_foundation(cur)
        cash = one(cur, 'select id from erp.cash_accounts where is_active order by id limit 1')
        cases = [(kind + ':' + z, lambda k=kind, pz=z: settlement_date(cur, cash, k, pz))
                 for kind in KINDS for z in ZONES]
        cases += [('VENDOR_PAYMENT:' + z, lambda pz=z: payment_date(cur, cash, 'VENDOR_PAYMENT', pz)) for z in ZONES]
        cases += [('SALES_PAYMENT_EDGE:' + z, lambda pz=z: payment_date(cur, cash, 'SALES_PAYMENT', pz)) for z in ZONES]
        cases += [('SALES_PAYMENT_NOON:' + z, lambda pz=z: payment_date(cur, cash, 'SALES_PAYMENT', pz, True)) for z in ZONES]
        cases += [('USER_REVOKED_AFTER_DRAFT', lambda: revoked_actor(cur, cash, False)),
                  ('ROLE_REVOKED_AFTER_DRAFT', lambda: revoked_actor(cur, cash, True)),
                  ('PRIVATE_EXECUTION_CONTEXT_ACL', lambda: context_acl(cur))]
        if extensions:
            cases += extensions(cur, cash)
        result['expected_case_count'] = len(cases)
        for name, operation in cases:
            cur.execute('savepoint independent_case')
            before = boundary(cur)
            try:
                evidence = operation()
                if phase == 'AFTER_Y' and any(d['confidence'] != 'READY' for d in evidence.get('daily_evidence', {}).values()):
                    raise AssertionError('Y_CORRECT_CANONICAL_EVENT_FALSE_BLOCKED')
            except Exception as exc:
                evidence = dict(status='INCOMPLETE', classification='FIXTURE_OR_ORACLE_ERROR',
                                error=str(exc), sqlstate=getattr(exc, 'sqlstate', None))
            finally:
                cur.execute('rollback to savepoint independent_case')
                admin(cur)
                cur.execute('release savepoint independent_case')
            evidence['full_boundary_restored'] = boundary(cur) == before
            result['cases'][name] = evidence
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
            print(json.dumps(dict(case=name, status=evidence['status'], restored=evidence['full_boundary_restored'])), flush=True)
            if not evidence['full_boundary_restored']:
                raise AssertionError('INDEPENDENT_CASE_RESIDUE:' + name)
        conn.rollback()
        result['runtime_after'] = boundary(cur)
        result['entire_unseeded_runtime_restored'] = result['runtime_after'] == untouched
        result['schema_usage_restored'] = one(cur, "select has_schema_privilege('authenticated','erp','USAGE')") == usage
        conn.rollback()
    result['qualified_counterexamples'] = sum(c['status'] == 'NEW_X_BUG_REPRODUCED' for c in result['cases'].values())
    result['controls_passed'] = sum(c['status'] == 'CONTROL_PASS' for c in result['cases'].values())
    result['incomplete_cases'] = sum(c['status'] == 'INCOMPLETE' for c in result['cases'].values())
    complete = (len(result['cases']) == result['expected_case_count'] and result['incomplete_cases'] == 0
                and result['entire_unseeded_runtime_restored'] and result['schema_usage_restored'])
    result['status'] = ('FAIL_NEW_COUNTEREXAMPLE' if result['qualified_counterexamples'] else 'PASS_BOUNDED_AUDIT') if complete else 'INCOMPLETE'
    return result


if __name__ == '__main__':
    try:
        report = run(os.environ.get('CP6_Y_PHASE', 'X_AUDIT'))
    except Exception as exc:
        report = json.loads(REPORT.read_text()) if REPORT.exists() else {}
        report.update(status='INCOMPLETE', error=str(exc), production_go=False)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('cases', 'runtime_before', 'runtime_after')}, default=str))
    raise SystemExit(0 if report['status'] == 'PASS_BOUNDED_AUDIT' else 1 if report['status'] == 'FAIL_NEW_COUNTEREXAMPLE' else 2)
