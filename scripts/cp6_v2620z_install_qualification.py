#!/usr/bin/env python3
"""Native Z admission refusals under isolated administrative fault injection."""
import json
import os
from pathlib import Path
import psycopg
from psycopg.conninfo import conninfo_to_dict
import cp6_x_independent_audit as audit
import cp6_v2620y_runtime as predecessor
import cp6_v2620z_runtime as runtime
import cp6_v2620n_rollback_guards as guards

REPORT = Path('cp6-proof/CP6_V2620Z_INSTALL_QUALIFICATION.json')


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1', port='54322', dbname='postgres') or os.environ.get('CP6_Z_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('Z_INSTALL_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    source = runtime.MIGRATION.read_text()
    if source.count('\nbegin;\n') != 1 or not source.endswith('commit;\n'):
        raise AssertionError('Z_INSTALL_TRANSACTION_SHAPE')
    body = source.replace('\nbegin;\n', '\n', 1).removesuffix('commit;\n')
    result = dict(head=os.environ['GITHUB_SHA'], tree=audit.git('rev-parse', 'HEAD^{tree}'),
                  status='FAIL', production_go=False, cases={},
                  classification='DISPOSABLE_NATIVE_ATOMIC_ADMISSION_FAULT_INJECTION')
    specs = (
        ('CLOSE_DEFINITION', 'alter function erp.close_accounting_through(date,text) cost 999', 'Z_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
        ('CLOSE_ACL', 'grant execute on function erp.close_accounting_through(date,text) to anon', 'Z_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
        ('BUSINESS_DAY_HELPER', 'alter function erp._cp3_business_date(timestamptz) cost 999', 'Z_TRUSTED_U_INPUT_OWNER_ACL_MISMATCH'),
        ('BUSINESS_DAY_HELPER_ACL', 'grant execute on function erp._cp3_business_date(timestamptz) to anon', 'Z_TRUSTED_U_INPUT_OWNER_ACL_MISMATCH'),
        ('COHERENT_Y_CAPSULE', None, 'Z_TRUSTED_Y_PREDECESSOR_PIN_MISMATCH'),
        ('MISSING_Y_MARKER', "delete from erp.schema_migrations where version='v2.6.20y'", 'Z_REQUIRES_EXACT_Y_WITHOUT_Z_RESIDUE'),
        ('Y_PLATFORM_BYTES', "update supabase_migrations.schema_migrations set statements=array['Z corrupt-Y control'] where name='erp_v2_6_20y_cp6_cash_business_dates'", 'Z_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH'),
        ('UNEXPECTED_SUCCESSOR', "insert into supabase_migrations.schema_migrations(version,name,statements) values('99999999999999','z_admission_successor_probe',array['probe'])", 'Z_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH'),
        ('EXTRA_TABLE_BOUNDARY', 'create table erp.z_admission_boundary_probe(id integer)', 'Z_FULL_ERP_BOUNDARY_CARDINALITY'),
        ('PREEXISTING_CURRENT_DAY_CLOSE', "update erp.accounting_period_control set closed_through=(current_timestamp at time zone 'Asia/Jakarta')::date where singleton_id=1", 'Z_PREEXISTING_PERIOD_CLOSE_REVIEW_REQUIRED'),
    )
    with psycopg.connect(**dict(params, user='supabase_admin')) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='240s'")
        untouched = audit.boundary(cur)
        if runtime.verified_successor(cur) or len(predecessor.verified_successor(cur)) != 6:
            raise AssertionError('Z_INSTALL_EXACT_Y_REQUIRED')
        usage = audit.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        audit.actors.claims(cur, dict(sub=audit.base.OPERATOR_AUTH, role='authenticated'))
        cur.execute("select set_config('app.change_reason','Z isolated admission faults',true)")
        audit.base.load_fixture_foundation(cur)
        for name, mutation, expected in specs:
            cur.execute('savepoint z_admission_case')
            baseline = audit.boundary(cur)
            evidence = dict(status='FAIL', expected_error=expected)
            try:
                if mutation:
                    cur.execute(mutation, prepare=False)
                    if mutation.startswith(('update ', 'delete ', 'insert ')) and cur.rowcount != 1:
                        raise AssertionError('Z_ADMISSION_MUTATION_NOT_QUALIFIED')
                else:
                    identity, definition = cur.execute('select object_regidentity,object_definition from erp.cp6_v2620y_rollback_capsule order by object_regidentity limit 1').fetchone()
                    changed = guards.canonical_cost_tamper(definition)
                    cur.execute("update erp.cp6_v2620y_rollback_capsule set object_definition=%s,definition_sha256=encode(extensions.digest(convert_to(%s,'UTF8'),'sha256'),'hex') where object_regidentity=%s", (changed, changed, identity))
                    if cur.rowcount != 1:
                        raise AssertionError('Z_ADMISSION_COHERENT_CAPSULE_CARDINALITY')
                before_attempt = audit.boundary(cur)
                error = None
                cur.execute('savepoint z_admission_attempt')
                try:
                    cur.execute(body, prepare=False)
                except psycopg.Error as exc:
                    error = str(exc)
                    evidence['sqlstate'] = exc.sqlstate
                finally:
                    cur.execute('rollback to savepoint z_admission_attempt;release savepoint z_admission_attempt')
                if not error or expected not in error:
                    raise AssertionError('Z_ADMISSION_WRONG_REFUSAL:' + str(error))
                if audit.boundary(cur) != before_attempt:
                    raise AssertionError('Z_ADMISSION_REFUSAL_CHANGED_STATE')
                if audit.one(cur, "select to_regclass('erp.cp6_v2620z_rollback_capsule')") is not None:
                    raise AssertionError('Z_FAILED_ADMISSION_CAPSULE_RESIDUE')
                evidence.update(status='CONTROL_PASS', actual_error=error, refusal_boundary_exact=True, z_capsule_absent=True)
            except Exception as exc:
                evidence.update(status='FAIL', error=str(exc))
            finally:
                cur.execute('rollback to savepoint z_admission_case')
                audit.admin(cur)
                cur.execute('release savepoint z_admission_case')
            evidence['full_boundary_restored'] = audit.boundary(cur) == baseline
            result['cases'][name] = evidence
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
            print('Z_INSTALL_CASE ' + json.dumps(dict(name=name, **evidence), default=str), flush=True)
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
