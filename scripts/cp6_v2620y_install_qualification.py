#!/usr/bin/env python3
"""Ten atomic Y admission refusals on the exact unmodified X runtime."""
import json
import os
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_x_independent_audit as audit
import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620n_rollback_guards as n_guards
import cp6_v2620y_runtime as runtime

REPORT = Path('cp6-proof/CP6_V2620Y_INSTALL_QUALIFICATION.json')


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1', port='54322', dbname='postgres') or os.environ.get('CP6_X_INDEPENDENT_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('Y_INSTALL_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    source = runtime.MIGRATION.read_text()
    if source.count('\nbegin;\n') != 1 or not source.endswith('commit;\n'):
        raise AssertionError('Y_INSTALL_TRANSACTION_SHAPE')
    body = source.replace('\nbegin;\n', '\n', 1).removesuffix('commit;\n')
    result = dict(head=os.environ['GITHUB_SHA'], tree=audit.git('rev-parse', 'HEAD^{tree}'),
                  status='FAIL', production_go=False, cases={}, classification='DISPOSABLE_NATIVE_ATOMIC_ADMISSION_REFUSALS')
    with psycopg.connect(**dict(params, user='supabase_admin')) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='240s'")
        untouched = audit.boundary(cur)
        usage = audit.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        if runtime.verified_successor(cur) or len(audit.runtime.verified_successor(cur)) != 1:
            raise AssertionError('Y_INSTALL_EXACT_X_REQUIRED')
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        audit.actors.claims(cur, dict(sub=audit.base.OPERATOR_AUTH, role='authenticated'))
        cur.execute("select set_config('app.change_reason','Y disposable admission qualifications',true)")
        audit.base.load_fixture_foundation(cur)
        cash = audit.one(cur, 'select id from erp.cash_accounts where is_active order by id limit 1')
        specs = [('FUNCTION_DRIFT:' + p['identity'], p['identity']) for p in maintenance.TRUSTED_FUNCTIONS['Y']]
        specs += [('COHERENT_X_CAPSULE', None), ('OPENING_PREEXISTING_DATE', None),
                  ('VENDOR_PREEXISTING_DATE', None), ('SALES_PREEXISTING_DATE', None)]
        for name, identity in specs:
            cur.execute('savepoint y_install_case')
            baseline = audit.boundary(cur)
            evidence = dict(status='FAIL')
            try:
                if identity:
                    cur.execute('alter function ' + identity + ' cost 999')
                    expected = 'FUNCTION_OWNER_ACL_MISMATCH'
                elif name == 'COHERENT_X_CAPSULE':
                    cur.execute('select object_definition from erp.cp6_v2620x_rollback_capsule')
                    definition = n_guards.canonical_cost_tamper(cur.fetchone()[0])
                    cur.execute("update erp.cp6_v2620x_rollback_capsule set object_definition=%s,definition_sha256=encode(extensions.digest(convert_to(%s,'UTF8'),'sha256'),'hex')", (definition, definition))
                    expected = 'Y_TRUSTED_X_CAPSULE_MISMATCH'
                else:
                    if name.startswith('OPENING'):
                        counter = audit.settlement_date(cur, cash, 'CUSTOMER_RECEIVABLE', 'UTC')
                    else:
                        counter = audit.payment_date(cur, cash, 'VENDOR_PAYMENT' if name.startswith('VENDOR') else 'SALES_PAYMENT', 'UTC')
                    if counter['status'] != 'NEW_X_BUG_REPRODUCED':
                        raise AssertionError('Y_INSTALL_REQUIRES_REPRODUCED_X_DATE_BUG')
                    evidence['preexisting_counterexample'] = counter
                    audit.admin(cur)
                    expected = 'Y_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED'
                before_attempt = audit.boundary(cur)
                cur.execute('savepoint y_admission_attempt')
                error = None
                try:
                    cur.execute(body, prepare=False)
                except psycopg.Error as exc:
                    error = str(exc)
                    evidence['sqlstate'] = exc.sqlstate
                finally:
                    cur.execute('rollback to savepoint y_admission_attempt;release savepoint y_admission_attempt')
                if not error or expected not in error:
                    raise AssertionError('Y_ADMISSION_WRONG_REFUSAL:' + str(error))
                after_attempt = audit.boundary(cur)
                if before_attempt != after_attempt or audit.one(cur, "select to_regclass('erp.cp6_v2620y_rollback_capsule')") is not None:
                    raise AssertionError('Y_FAILED_INSTALL_RESIDUE')
                evidence.update(status='CONTROL_PASS', expected_error=expected, actual_error=error,
                                refusal_boundary_exact=True, y_capsule_absent=True)
            except Exception as exc:
                evidence.update(status='FAIL', error=str(exc))
            finally:
                cur.execute('rollback to savepoint y_install_case')
                audit.admin(cur)
                cur.execute('release savepoint y_install_case')
            evidence['full_boundary_restored'] = audit.boundary(cur) == baseline
            result['cases'][name] = evidence
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
            print(json.dumps(dict(case=name, status=evidence['status'], restored=evidence['full_boundary_restored'])), flush=True)
        conn.rollback()
        result['entire_unseeded_runtime_restored'] = audit.boundary(cur) == untouched
        result['schema_usage_restored'] = audit.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')") == usage
        conn.rollback()
    if len(result['cases']) == 10 and all(c['status'] == 'CONTROL_PASS' and c['full_boundary_restored'] for c in result['cases'].values()) and result['entire_unseeded_runtime_restored'] and result['schema_usage_restored']:
        result['status'] = 'PASS'
    return result


if __name__ == '__main__':
    try:
        result = run()
    except Exception as exc:
        result = json.loads(REPORT.read_text()) if REPORT.exists() else {}
        result.update(status='FAIL', error=str(exc), production_go=False)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'cases'}, default=str))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
