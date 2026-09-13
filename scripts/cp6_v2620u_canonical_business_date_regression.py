#!/usr/bin/env python3
"""Reproduce T timezone defects and prove U canonical business dates."""
import hashlib
import json
import os
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_v2620e_counterexample_regression as base
import cp6_v2620t_runtime as t_runtime
import cp6_v2620u_runtime as u_runtime


SOURCE = Path('supabase/tests/cp6_canonical_business_date.sql')
AUTH_SCHEMA_SOURCE = Path(
    'ops/supabase/uat/applied/'
    '20260831032949_erp_v2_6_13b_auth_profile_facade_tracking.sql'
)
CASES = (
    'MATERIAL_ORIGINAL_UTC',
    'MATERIAL_REVERSAL_REAL_ZONE',
    'OWNER_WIP_CUTOFF',
    'OWNER_DEFAULT_AS_OF',
    'MATERIAL_ORIGINAL_JAKARTA',
)
AFFECTED_CASES = CASES[:-1]


def replace_exact(definition: str, old: str, new: str, count: int) -> str:
    if definition.count(old) != count:
        raise AssertionError(f'U_HYPOTHETICAL_ANCHOR_MISMATCH:{old!r}')
    return definition.replace(old, new)


def hypothetical_hashes(cur: psycopg.Cursor) -> list[dict[str, object]]:
    detector_anchor = "  union all\n  select 'V2620T_JOURNAL_FUTURE_BUSINESS_DATE'"
    detector_insert = """  union all
  select 'V2620U_MATERIAL_ADJUSTMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Material adjustment journals must use the canonical Jakarta date of physical_at'
  from erp.journal_entries j
  join erp.material_adjustments h on h.id=j.source_id
  where j.source_type='MATERIAL_ADJUSTMENT' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620U_JOURNAL_REVERSAL_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Generic journal reversals must use the canonical Jakarta date of posting_at'
  from erp.journal_entries j
  where j.source_type='JOURNAL_REVERSAL' and j.status='POSTED'
    and j.economic_date is distinct from erp._cp3_business_date(j.posting_at)

""" + detector_anchor
    transforms = {
        'erp._cp3_r4_reverse_journal_internal(uuid,text)': [
            ('CURRENT_DATE', 'erp._cp3_business_date(current_timestamp)', 1),
        ],
        'erp.post_material_adjustment(uuid)': [
            ('h.physical_at::date', 'erp._cp3_business_date(h.physical_at)', 2),
        ],
        'erp.get_owner_financial_snapshot_v2(date,date,date)': [
            (
                'p_as_of date DEFAULT CURRENT_DATE',
                'p_as_of date DEFAULT erp._cp3_business_date(current_timestamp)',
                1,
            ),
            ('h.physical_at::date', 'erp._cp3_business_date(h.physical_at)', 2),
            ('w.physical_at::date', 'erp._cp3_business_date(w.physical_at)', 1),
        ],
        'erp.run_v267_financial_truth_checks()': [
            (detector_anchor, detector_insert, 1),
        ],
        'erp._v268_financial_report_checks_pre_scope()': [
            (
                "or r.check_name like 'V2620T_%'",
                "or r.check_name like 'V2620T_%' or r.check_name like 'V2620U_%'",
                1,
            ),
        ],
    }
    output = []
    for identity, replacements in transforms.items():
        definition = base.one(cur, 'select pg_get_functiondef(%s::regprocedure)', (identity,))
        transformed = definition
        for old, new, count in replacements:
            transformed = replace_exact(transformed, old, new, count)
        output.append({
            'identity': identity,
            'predecessor_sha256': hashlib.sha256(definition.encode()).hexdigest(),
            'hypothetical_installed_sha256': hashlib.sha256(
                transformed.encode()
            ).hexdigest(),
            'changed': transformed != definition,
        })
    return output


def run() -> dict[str, object]:
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    expected = dict(
        user='postgres', password='postgres', host='127.0.0.1',
        port='54322', dbname='postgres',
    )
    if params != expected:
        raise AssertionError('U_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_U_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('U_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    phase = os.environ.get('CP6_U_PHASE', 'BEFORE_U')
    if phase not in ('BEFORE_U', 'AFTER_U'):
        raise AssertionError('U_UNKNOWN_PHASE')
    fixed = phase == 'AFTER_U'
    result: dict[str, object] = {
        'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
        'production_go': False,
        'classification': 'DISPOSABLE_NATIVE_' + phase,
        'phase': phase,
        'oracle_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'cases': {},
    }
    with psycopg.connect(**params, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute(
            "set local timezone='UTC';set local statement_timeout='180s';"
            "set local lock_timeout='8s'"
        )
        t_successor = t_runtime.verified_successor(cur)
        if len(t_successor) != 6:
            raise AssertionError('U_EXACT_T_REQUIRED')
        u_successor = u_runtime.verified_successor(cur)
        if u_successor and not fixed:
            raise AssertionError('U_BEFORE_PHASE_HAS_U_RESIDUE')
        if fixed and len(u_successor) != 5:
            raise AssertionError('U_AFTER_PHASE_REQUIRES_EXACT_U')
        auth_source = AUTH_SCHEMA_SOURCE.read_text()
        auth_grant = 'grant usage on schema public, erp to authenticated;'
        if auth_source.count(auth_grant) != 1:
            raise AssertionError('U_AUTH_SCHEMA_SOURCE_CONTRACT_MISMATCH')
        cur.execute("""select
          has_schema_privilege('authenticated','erp','USAGE'),
          has_function_privilege('authenticated',
            'erp.post_material_adjustment_v2(uuid,uuid,bigint,text)','EXECUTE'),
          has_function_privilege('authenticated',
            'erp.reverse_material_adjustment_v2(uuid,text,uuid,bigint)','EXECUTE'),
          has_function_privilege('authenticated',
            'erp.get_owner_financial_snapshot_v2(date,date,date)','EXECUTE')""")
        usage_before, post_execute, reverse_execute, report_execute = cur.fetchone()
        if not all((post_execute, reverse_execute, report_execute)):
            raise AssertionError('U_AUTHENTICATED_FUNCTION_EXECUTE_CONTRACT_MISSING')
        # pg_dump/restore intentionally omits ACLs in this disposable workflow,
        # while the frozen UAT auth migration grants this exact schema usage.
        # Align only that source-owned grant inside this rollback-only transaction.
        if not usage_before:
            cur.execute('grant usage on schema erp to authenticated')
        usage_after = base.one(
            cur, "select has_schema_privilege('authenticated','erp','USAGE')"
        )
        if not usage_after:
            raise AssertionError('U_AUTHENTICATED_SCHEMA_USAGE_ALIGNMENT_FAILED')
        runtime = {
            'verified_t_functions': len(t_successor),
            'authenticated_contract': {
                'schema_usage_before_alignment': usage_before,
                'schema_usage_after_alignment': usage_after,
                'transactional_alignment_applied': not usage_before,
                'function_execute_grants': {
                    'post_material_adjustment_v2': post_execute,
                    'reverse_material_adjustment_v2': reverse_execute,
                    'get_owner_financial_snapshot_v2': report_execute,
                },
                'source_path': str(AUTH_SCHEMA_SOURCE),
                'source_sha256': hashlib.sha256(
                    AUTH_SCHEMA_SOURCE.read_bytes()
                ).hexdigest(),
            },
            'engine': base.one(cur, 'select version()'),
        }
        if fixed:
            runtime['verified_u_functions'] = len(u_successor)
            runtime['installed_function_hashes'] = [
                {
                    'identity': identity,
                    'predecessor_sha256': item['predecessor_sha256'],
                    'installed_sha256': item['installed_sha256'],
                    'observed_installed_sha256': item['observed_installed_sha256'],
                    'owner': item['owner'],
                    'acl': item['acl'],
                }
                for identity, item in sorted(u_successor.items())
            ]
        else:
            runtime['hypothetical_function_hashes'] = hypothetical_hashes(cur)
        result['runtime'] = runtime
        cur.execute("select set_config('request.jwt.claims',%s,true)", (
            json.dumps({'sub': base.OPERATOR_AUTH, 'role': 'authenticated'}),
        ))
        cur.execute("select set_config('app.change_reason',%s,true)", (
            'CP6 U independent canonical business-date audit',
        ))
        base.load_fixture_foundation(cur)
        for source in (
            Path('supabase/tests/cp6_subledger_exact_cent.sql'),
            Path('supabase/tests/cp6_supplier_cent_lifecycle.sql'),
            Path('supabase/tests/cp6_supplier_return_document_allocation.sql'),
            Path('supabase/tests/cp6_supplier_invoice_exact_quantity.sql'),
            Path('supabase/tests/cp6_material_adjustment_revaluation.sql'),
            Path('supabase/tests/cp6_independent_n_regression.sql'),
            SOURCE,
        ):
            cur.execute(source.read_text(), prepare=False)
        for name in CASES:
            cur.execute('savepoint u_case')
            try:
                case = base.one(cur, 'select pg_temp.u_case(%s,%s)', (name, fixed))
                wanted = 'PASS' if fixed else (
                    'KNOWN_T_BUG_REPRODUCED'
                    if name in AFFECTED_CASES else 'CONTROL_PASS'
                )
                if case['status'] != wanted:
                    raise AssertionError('U_ORACLE_STATUS_MISMATCH')
                result['cases'][name] = case
            except Exception as exc:
                result['cases'][name] = {
                    'status': 'FAIL',
                    'code': getattr(exc, 'sqlstate', None) or 'U_ORACLE_FAILED',
                    'message': str(exc),
                }
            finally:
                cur.execute('rollback to savepoint u_case')
                cur.execute('release savepoint u_case')
                cur.execute("select set_config('TimeZone','UTC',true)")
            if base.one(cur, 'select pg_temp.m_report()') != 'READY':
                raise AssertionError('U_CASE_RESTORE_NOT_READY')
            result['cases'][name]['rolled_back_to_ready'] = True
        conn.rollback()
    acceptable = {'PASS'} if fixed else {'CONTROL_PASS', 'KNOWN_T_BUG_REPRODUCED'}
    result['all_case_effects_rolled_back'] = True
    result['status'] = (
        'PASS'
        if all(c['status'] in acceptable for c in result['cases'].values())
        else 'FAIL'
    )
    return result


def main() -> None:
    phase = os.environ.get('CP6_U_PHASE', 'BEFORE_U')
    filename = (
        'CP6_V2620U_T_COUNTEREXAMPLES.json' if phase == 'BEFORE_U'
        else 'CP6_V2620U_CANONICAL_BUSINESS_DATE_REGRESSION.json'
    )
    report = Path('cp6-proof') / filename
    try:
        result = run()
    except Exception as exc:
        result = {
            'status': 'FAIL',
            'code': getattr(exc, 'sqlstate', None) or 'U_PREFLIGHT_FAILED',
            'message': str(exc),
            'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
            'production_go': False,
        }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({
        'status': result['status'],
        'case_count': len(result.get('cases', {})),
        'runtime': result.get('runtime'),
        'production_go': False,
    }, sort_keys=True))
    if result['status'] == 'FAIL':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
