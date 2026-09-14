#!/usr/bin/env python3
"""Native AA admission refusals under isolated administrative fault injection."""
import json
import os
from pathlib import Path
import psycopg
from psycopg.conninfo import conninfo_to_dict
import cp6_x_independent_audit as audit
import cp6_v2620z_runtime as predecessor
import cp6_v2620aa_runtime as runtime
import cp6_v2620n_rollback_guards as guards

REPORT = Path('cp6-proof/CP6_V2620AA_INSTALL_QUALIFICATION.json')


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1', port='54322', dbname='postgres') or os.environ.get('CP6_AA_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('AA_INSTALL_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    source = runtime.MIGRATION.read_text()
    if source.count('\nbegin;\n') != 1 or not source.endswith('commit;\n'):
        raise AssertionError('AA_INSTALL_TRANSACTION_SHAPE')
    body = source.replace('\nbegin;\n', '\n', 1).removesuffix('commit;\n')
    result = dict(head=os.environ['GITHUB_SHA'], tree=audit.git('rev-parse', 'HEAD^{tree}'),
                  status='FAIL', production_go=False, cases={},
                  classification='DISPOSABLE_NATIVE_ATOMIC_ADMISSION_FAULT_INJECTION')
    specs = (
        ('CHECKPOINT_DEFINITION', 'alter function erp.refresh_material_cost_checkpoint(uuid,date) cost 999', 'AA_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
        ('RECALC_DEFINITION', 'alter function erp._recalculate_material_cost_core(uuid,timestamptz,boolean) cost 999', 'AA_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
        ('CHECKPOINT_ACL', 'grant execute on function erp.refresh_material_cost_checkpoint(uuid,date) to anon', 'AA_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
        ('RECALC_ACL', 'grant execute on function erp._recalculate_material_cost_core(uuid,timestamptz,boolean) to anon', 'AA_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
        ('BUSINESS_DAY_HELPER', 'alter function erp._cp3_business_date(timestamptz) cost 999', 'AA_TRUSTED_U_INPUT_OWNER_ACL_MISMATCH'),
        ('BUSINESS_DAY_HELPER_ACL', 'grant execute on function erp._cp3_business_date(timestamptz) to anon', 'AA_TRUSTED_U_INPUT_OWNER_ACL_MISMATCH'),
        ('COHERENT_Z_CAPSULE', None, 'AA_TRUSTED_Z_PREDECESSOR_PIN_MISMATCH'),
        ('MISSING_Z_MARKER', "delete from erp.schema_migrations where version='v2.6.20z'", 'AA_REQUIRES_EXACT_Z_WITHOUT_AA_RESIDUE'),
        ('Z_PLATFORM_BYTES', "update supabase_migrations.schema_migrations set statements=array['AA corrupt-Z control'] where name='erp_v2_6_20z_cp6_accounting_close_business_date'", 'AA_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH'),
        ('UNEXPECTED_SUCCESSOR', "insert into supabase_migrations.schema_migrations(version,name,statements) values('99999999999999','aa_admission_successor_probe',array['probe'])", 'AA_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH'),
        ('EXTRA_TABLE_BOUNDARY', 'create table erp.aa_admission_boundary_probe(id integer)', 'AA_FULL_ERP_BOUNDARY_CARDINALITY'),
        ('PREEXISTING_CURRENT_DAY_CLOSE', "update erp.accounting_period_control set closed_through=(current_timestamp at time zone 'Asia/Jakarta')::date where singleton_id=1", 'AA_PREEXISTING_PERIOD_CLOSE_REVIEW_REQUIRED'),
        ('PREEXISTING_MATERIAL_CHECKPOINT', "insert into erp.material_cost_checkpoints(material_id,checkpoint_date,stock_qty,moving_average_cost) values('c8c30000-0000-4000-8000-000000000002',current_date-1,0,0)", 'AA_PREEXISTING_MATERIAL_CHECKPOINT_REVIEW_REQUIRED'),
    )
    with psycopg.connect(**dict(params, user='supabase_admin')) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='240s'")
        untouched = audit.boundary(cur)
        if runtime.verified_successor(cur) or len(predecessor.verified_successor(cur)) != 1:
            raise AssertionError('AA_INSTALL_EXACT_Z_REQUIRED')
        usage = audit.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        audit.actors.claims(cur, dict(sub=audit.base.OPERATOR_AUTH, role='authenticated'))
        cur.execute("select set_config('app.change_reason','AA isolated admission faults',true)")
        audit.base.load_fixture_foundation(cur)
        for name, mutation, expected in specs:
            cur.execute('savepoint aa_admission_case')
            baseline = audit.boundary(cur)
            evidence = dict(status='FAIL', expected_error=expected)
            try:
                if mutation:
                    cur.execute(mutation, prepare=False)
                    if mutation.startswith(('update ', 'delete ', 'insert ')) and cur.rowcount != 1:
                        raise AssertionError('AA_ADMISSION_MUTATION_NOT_QUALIFIED')
                else:
                    identity, definition = cur.execute('select object_regidentity,object_definition from erp.cp6_v2620z_rollback_capsule order by object_regidentity limit 1').fetchone()
                    changed = guards.canonical_cost_tamper(definition)
                    cur.execute("update erp.cp6_v2620z_rollback_capsule set object_definition=%s,definition_sha256=encode(extensions.digest(convert_to(%s,'UTF8'),'sha256'),'hex') where object_regidentity=%s", (changed, changed, identity))
                    if cur.rowcount != 1:
                        raise AssertionError('AA_ADMISSION_COHERENT_CAPSULE_CARDINALITY')
                before_attempt = audit.boundary(cur)
                error = None
                cur.execute('savepoint aa_admission_attempt')
                try:
                    cur.execute(body, prepare=False)
                except psycopg.Error as exc:
                    error = str(exc)
                    evidence['sqlstate'] = exc.sqlstate
                finally:
                    cur.execute('rollback to savepoint aa_admission_attempt;release savepoint aa_admission_attempt')
                if not error or expected not in error:
                    raise AssertionError('AA_ADMISSION_WRONG_REFUSAL:' + str(error))
                if audit.boundary(cur) != before_attempt:
                    raise AssertionError('AA_ADMISSION_REFUSAL_CHANGED_STATE')
                if audit.one(cur, "select to_regclass('erp.cp6_v2620aa_rollback_capsule')") is not None:
                    raise AssertionError('AA_FAILED_ADMISSION_CAPSULE_RESIDUE')
                evidence.update(status='CONTROL_PASS', actual_error=error, refusal_boundary_exact=True, aa_capsule_absent=True)
            except Exception as exc:
                evidence.update(status='FAIL', error=str(exc))
            finally:
                cur.execute('rollback to savepoint aa_admission_case')
                audit.admin(cur)
                cur.execute('release savepoint aa_admission_case')
            evidence['full_boundary_restored'] = audit.boundary(cur) == baseline
            result['cases'][name] = evidence
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
            print('AA_INSTALL_CASE ' + json.dumps(dict(name=name, **evidence), default=str), flush=True)
        conn.rollback()
        result['entire_unseeded_runtime_restored'] = audit.boundary(cur) == untouched
        result['schema_usage_restored'] = audit.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')") == usage
        conn.rollback()
    if len(result['cases']) == 13 and all(c['status'] == 'CONTROL_PASS' and c['full_boundary_restored'] for c in result['cases'].values()) and result['entire_unseeded_runtime_restored'] and result['schema_usage_restored']:
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
