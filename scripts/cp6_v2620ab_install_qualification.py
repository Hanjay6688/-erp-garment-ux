#!/usr/bin/env python3
"""AB atomic admission, including affected-history review and a lawful control."""
import json
import os
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_x_independent_audit as audit
import cp6_aa_invoice_partial_audit as invoice
import cp6_v2620w_scrap_business_date_regression as scrap
import cp6_v2620aa_runtime as predecessor
import cp6_v2620ab_runtime as runtime
import cp6_v2620n_rollback_guards as guards
import cp6_preuse_rollback_maintenance as maintenance

REPORT = Path('cp6-proof/CP6_V2620AB_INSTALL_QUALIFICATION.json')


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1', port='54322', dbname='postgres') or os.environ.get('CP6_AB_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('AB_INSTALL_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    source = runtime.MIGRATION.read_text()
    if source.count('\nbegin;\n') != 1 or not source.endswith('commit;\n'):
        raise AssertionError('AB_INSTALL_TRANSACTION_SHAPE')
    body = source.replace('\nbegin;\n', '\n', 1).removesuffix('commit;\n')
    result = dict(head=os.environ['GITHUB_SHA'], tree=audit.git('rev-parse', 'HEAD^{tree}'),
                  status='FAIL', production_go=False, cases={},
                  classification='DISPOSABLE_NATIVE_ATOMIC_ADMISSION_AND_HISTORY_REVIEW')
    specs = []
    for item in maintenance.TRUSTED_FUNCTIONS['AB']:
        identity = item['identity']
        for label, statement in (
            ('DEFINITION', 'alter function ' + identity + ' cost 999'),
            ('ACL', 'grant execute on function ' + identity + ' to anon'),
            ('OWNER', 'alter function ' + identity + ' owner to service_role'),
        ):
            specs.append((label + ':' + identity, statement, 'AB_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'))
    specs += [
        ('BUSINESS_DAY_HELPER', 'alter function erp._cp3_business_date(timestamptz) cost 999', 'AB_TRUSTED_U_INPUT_OWNER_ACL_MISMATCH'),
        ('BUSINESS_DAY_HELPER_ACL', 'grant execute on function erp._cp3_business_date(timestamptz) to anon', 'AB_TRUSTED_U_INPUT_OWNER_ACL_MISMATCH'),
        ('COHERENT_AA_CAPSULE', None, 'AB_TRUSTED_AA_PREDECESSOR_PIN_MISMATCH'),
        ('MISSING_AA_MARKER', "delete from erp.schema_migrations where version='v2.6.20aa'", 'AB_REQUIRES_EXACT_AA_WITHOUT_AB_RESIDUE'),
        ('AA_PLATFORM_BYTES', "update supabase_migrations.schema_migrations set statements=array['AB corrupt-AA control'] where name='erp_v2_6_20aa_cp6_material_cost_business_day'", 'AB_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH'),
        ('UNEXPECTED_SUCCESSOR', "insert into supabase_migrations.schema_migrations(version,name,statements) values('99999999999999','ab_admission_successor_probe',array['probe'])", 'AB_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH'),
        ('EXTRA_TABLE_BOUNDARY', 'create table erp.ab_admission_boundary_probe(id integer)', 'AB_FULL_ERP_BOUNDARY_CARDINALITY'),
        ('PREEXISTING_CURRENT_DAY_CLOSE', "update erp.accounting_period_control set closed_through=(current_timestamp at time zone 'Asia/Jakarta')::date where singleton_id=1", 'AB_PREEXISTING_PERIOD_CLOSE_REVIEW_REQUIRED'),
        ('PREEXISTING_MATERIAL_RECOST', None, 'AB_PREEXISTING_MATERIAL_RECOST_REVIEW_REQUIRED'),
        ('PREEXISTING_JOURNAL_REVERSAL', None, 'AB_PREEXISTING_JOURNAL_REVERSAL_REVIEW_REQUIRED'),
        ('LAWFUL_CHECKPOINT_HISTORY_ACCEPTED', None, None),
    ]
    result['expected_cases'] = len(specs)
    with psycopg.connect(**dict(params, user='supabase_admin')) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='240s'")
        untouched = invoice.boundary(cur)
        if runtime.verified_successor(cur) or len(predecessor.verified_successor(cur)) != 2:
            raise AssertionError('AB_INSTALL_EXACT_AA_REQUIRED')
        usage = audit.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        audit.actors.claims(cur, dict(sub=audit.base.OPERATOR_AUTH, role='authenticated'))
        cur.execute("select set_config('app.change_reason','AB isolated admission controls',true)")
        audit.base.load_fixture_foundation(cur)
        today = audit.one(cur, "select (clock_timestamp() at time zone 'Asia/Jakarta')::date")
        for name, mutation, expected in specs:
            invoice.admin(cur)
            cur.execute('savepoint ab_admission_case')
            baseline = invoice.boundary(cur)
            evidence = dict(status='FAIL', expected_error=expected)
            try:
                if mutation:
                    cur.execute(mutation, prepare=False)
                    if mutation.startswith(('update ', 'delete ', 'insert ')) and cur.rowcount != 1:
                        raise AssertionError('AB_ADMISSION_MUTATION_NOT_QUALIFIED')
                elif name == 'COHERENT_AA_CAPSULE':
                    identity, definition = cur.execute('select object_regidentity,object_definition from erp.cp6_v2620aa_rollback_capsule order by object_regidentity limit 1').fetchone()
                    changed = guards.canonical_cost_tamper(definition)
                    cur.execute("update erp.cp6_v2620aa_rollback_capsule set object_definition=%s,definition_sha256=encode(extensions.digest(convert_to(%s,'UTF8'),'sha256'),'hex') where object_regidentity=%s", (changed, changed, identity))
                    if cur.rowcount != 1:
                        raise AssertionError('AB_ADMISSION_COHERENT_CAPSULE_CARDINALITY')
                elif name == 'PREEXISTING_MATERIAL_RECOST':
                    observation = invoice.invoice_case(cur, 'Asia/Jakarta', today, True, '20.003')
                    if observation['status'] != 'CONTROL_PASS':
                        raise AssertionError('AB_ADMISSION_ORDINARY_RECOST_FIXTURE:' + str(observation.get('mismatches')))
                    invoice.admin(cur)
                    count = audit.one(cur, 'select count(*) from erp.material_cost_revaluation_events')
                    if not count:
                        raise AssertionError('AB_ADMISSION_RECOST_HISTORY_MISSING')
                    evidence['qualified_history_rows'] = count
                elif name == 'PREEXISTING_JOURNAL_REVERSAL':
                    invoice.zone(cur, 'Asia/Jakarta')
                    invoice.owner(cur)
                    cash = audit.one(cur, 'select id from erp.cash_accounts where is_active order by id limit 1')
                    transaction = scrap.draft(cur, cash, physical=invoice.at(today, 0).isoformat())
                    cur.execute('select erp.post_scrap_sale(%s)', (transaction,))
                    cur.execute('select erp.reverse_scrap_sale(%s,%s)', (transaction, 'AB ordinary reversal history review'))
                    invoice.admin(cur)
                    count = audit.one(cur, "select count(*) from erp.journal_entries where source_type='JOURNAL_REVERSAL'")
                    if not count:
                        raise AssertionError('AB_ADMISSION_REVERSAL_HISTORY_MISSING')
                    evidence['qualified_history_rows'] = count
                elif name == 'LAWFUL_CHECKPOINT_HISTORY_ACCEPTED':
                    fixture = invoice.estimated_receipt(cur, today)
                    invoice.owner(cur)
                    cur.execute('select erp.close_accounting_through(%s,%s)', (fixture['purchase_day'], 'AB lawful AA checkpoint admission control'))
                    invoice.admin(cur)
                    count = audit.one(cur, 'select count(*) from erp.material_cost_checkpoints')
                    if not count:
                        raise AssertionError('AB_ADMISSION_LAWFUL_CHECKPOINT_MISSING')
                    evidence['qualified_history_rows'] = count
                else:
                    raise AssertionError('AB_ADMISSION_UNKNOWN_CASE')
                invoice.admin(cur)
                before_attempt = invoice.boundary(cur)
                error = None
                cur.execute('savepoint ab_admission_attempt')
                try:
                    cur.execute(body, prepare=False)
                    if expected is None:
                        pins = maintenance._capsule_snapshot(conn, 'AB', maintenance.TARGETS['AB'])
                        if len(pins) != 5:
                            raise AssertionError('AB_ADMISSION_LAWFUL_INSTALL_PINS')
                        evidence['installed_five_functions_owner_acl_exact'] = True
                except psycopg.Error as exc:
                    error = str(exc)
                    evidence['sqlstate'] = exc.sqlstate
                finally:
                    cur.execute('rollback to savepoint ab_admission_attempt;release savepoint ab_admission_attempt')
                if (expected is None and error is not None) or (expected is not None and (error is None or expected not in error)):
                    raise AssertionError('AB_ADMISSION_WRONG_RESULT:' + str(error))
                if invoice.boundary(cur) != before_attempt:
                    raise AssertionError('AB_ADMISSION_ATTEMPT_CHANGED_STATE')
                if audit.one(cur, "select to_regclass('erp.cp6_v2620ab_rollback_capsule')") is not None:
                    raise AssertionError('AB_ADMISSION_CAPSULE_RESIDUE')
                evidence.update(status='CONTROL_PASS', actual_error=error, attempt_boundary_exact=True,
                                refused=expected is not None, lawful_history_accepted=expected is None, ab_capsule_absent=True)
            except Exception as exc:
                evidence.update(status='FAIL', error=str(exc))
            finally:
                cur.execute('rollback to savepoint ab_admission_case')
                invoice.admin(cur)
                cur.execute('release savepoint ab_admission_case')
            evidence['full_boundary_restored'] = invoice.boundary(cur) == baseline
            result['cases'][name] = evidence
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
            print('AB_INSTALL_CASE ' + json.dumps(dict(name=name, **evidence), default=str), flush=True)
        conn.rollback()
        result['entire_unseeded_runtime_restored'] = invoice.boundary(cur) == untouched
        result['schema_usage_restored'] = audit.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')") == usage
        conn.rollback()
    if len(result['cases']) == result['expected_cases'] == 26 and all(c['status'] == 'CONTROL_PASS' and c['full_boundary_restored'] for c in result['cases'].values()) and result['entire_unseeded_runtime_restored'] and result['schema_usage_restored']:
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
