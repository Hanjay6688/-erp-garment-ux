"""Fresh 230/31/65 regression on committed AR in a separate disposable clone."""
from pathlib import Path
from datetime import date
import json
import os
import subprocess
import traceback

import psycopg

import cp6_ar_runtime as ar
import cp6_ar_trial as trial
import cp6_aq_runtime as aq
import cp6_ao_ap_installed as api
import cp6_ao_ap_maintenance as maintenance
import cp6_ao_ap_runtime as prior
import cp6_successor_scope as scope
import cp6_successor_specs as specs
import cp6_v2620al_review as historical
from cp6_ao_ap_inventory import data, platform, function_pins

OUT = Path('cp6-proof/successor')
PG, ADMIN, CONTROL = trial.PG, trial.ADMIN, trial.CONTROL
actors, base = historical.actors, historical.base


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/(name+'.json')).write_text(json.dumps(value, indent=2, default=str)+'\n')


def snapshot(cur):
    api.admin(cur)
    # Include every ERP table, migration history, both schema ACLs and Auth rows.
    return dict(erp=data(cur), platform=platform(cur),
                auth=cur.execute("select coalesce(jsonb_agg(to_jsonb(u) order by id),'[]'::jsonb) from auth.users u").fetchone()[0],
                schemas=cur.execute("select nspname,nspacl::text from pg_namespace where nspname in ('erp','public') order by nspname").fetchall())


def run_group(group, source):
    manifest = specs.pins()['groups'][group]
    result = dict(status='INCOMPLETE', runtime_generation='AR', head=source['head'], tree=source['tree'],
                  oracle_module=manifest['module'], oracle_sources=specs.pins()['oracle_sha256'],
                  historical_runtime_runner_executed=False, case_declarations_unchanged=True,
                  planned_case_ids=manifest['case_ids'], cases={}, reused_evidence={},
                  http_transport_proven=False, independent_acceptance=False, production_go=False)
    save(group.upper(), result)
    try:
        with psycopg.connect(ADMIN) as conn, conn.cursor() as cur:
            assert cur.execute('select current_database()').fetchone()[0] == 'cp6_rollback'
            result['runtime_before'] = ar.verified(cur)
            initial, catalog = snapshot(cur), function_pins(cur)
            assert initial['auth'] == [] and initial['erp']['app_users']['count'] == 0
            usage = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            result['temporary_schema_usage_grant'] = not usage
            if not usage:
                cur.execute('grant usage on schema erp to authenticated')
            api.seed(cur)
            cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
            today = cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
            if group == 'business':
                historical.prior.set_open_period(cur, date(2026, 8, 31))
            cases = specs.cases(group, today)
            for name, operation in cases:
                before = snapshot(cur)
                cur.execute("set local timezone='Asia/Jakarta'")
                cur.execute('savepoint successor_case')
                try:
                    row = operation(cur)
                except Exception as exc:
                    row = dict(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc())
                finally:
                    cur.execute('rollback to savepoint successor_case')
                    api.admin(cur)
                    cur.execute('release savepoint successor_case')
                row['full_boundary_restored'] = snapshot(cur) == before
                if not row['full_boundary_restored']:
                    row['status'] = 'INCOMPLETE'
                result['cases'][name] = row
                save(group.upper(), result)
                print(json.dumps(dict(group=group, case=name, status=row['status'], error=row.get('error'))), flush=True)
            result['functions_owner_acl_unchanged'] = function_pins(cur) == catalog
            conn.rollback()
            result['runtime_after'] = ar.verified(cur)
            result['complete_boundary_restored'] = snapshot(cur) == initial
            result['schema_usage_restored'] = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0] == usage
            conn.rollback()
        statuses = ('PASS','CONTROL_PASS','DATE_POLICY_REVIEW_REQUIRED','BUG_PROVEN','GAP_PROVEN','INCOMPLETE','FAIL')
        result['counts'] = {status:sum(row['status']==status for row in result['cases'].values()) for status in statuses}
        result['hold_case_ids'] = [name for name, row in result['cases'].items() if row['status']=='DATE_POLICY_REVIEW_REQUIRED']
        complete = list(result['cases']) == manifest['case_ids'] and result['counts'] == manifest['expected_counts']
        complete = complete and result['hold_case_ids'] == manifest['historical_hold_case_ids']
        complete = complete and all(result.get(k) for k in ('functions_owner_acl_unchanged','complete_boundary_restored','schema_usage_restored'))
        if complete:
            result['status'] = 'HOLD' if result['hold_case_ids'] else 'WRITER_PASS'
        result['execution_complete'] = complete
    except Exception as exc:
        result.update(error=str(exc), traceback=traceback.format_exc(), execution_complete=False)
    save(group.upper(), result)
    return result


def run():
    assert os.environ.get('CP6_AR_CONFIRM') == 'cp6_rollback'
    assert os.environ.get('CP6_DATABASE_CONTAINER') == 'supabase_db_cp5-local'
    source = scope.verify()
    result = dict(status='INCOMPLETE', head=source['head'], tree=source['tree'], groups={},
                  production_go=False, hosted_migration_installed=False, independent_acceptance=False,
                  global_status='CP6_HOLD', historical_full_schema_workflow='UNCHANGED_AC_CONTRACT')
    save('COMBINED', result)
    with psycopg.connect(CONTROL) as conn, conn.cursor() as cur:
        prior.verified(cur, 'AN')
        primary = snapshot(cur)
    try:
        for family in ('AO','AP'):
            maintenance.install(family=family, target_pgurl=PG,
                                maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'],
                                report_path=OUT/(family+'_INSTALL.json'))
        result['aq_install'] = aq.change('install', PG, os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        result['ar_install'] = ar.change('install', PG, os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        for group in ('business','imports','values'):
            report = run_group(group, source)
            result['groups'][group] = {key:report.get(key) for key in ('status','counts','execution_complete','hold_case_ids','error')}
            save('COMBINED', result)
        # The unchanged AR suite runs earlier in this same native workflow.
        ar_proof = json.loads(Path('cp6-proof/ar/AR_TRIAL.json').read_text())
        assert ar_proof['status'] == 'WRITER_PASS' and len(ar_proof['cases']) == 174
        assert all(row['status']=='PASS' for row in ar_proof['cases'].values())
        assert ar_proof['primary_unchanged'] and ar_proof['clone_remaining'] == 0
        result['fresh_ar174'] = dict(status=ar_proof['status'], cases=174, source_unchanged=True)
        result['fresh_case_count'] = 174 + sum(len(specs.pins()['groups'][g]['case_ids']) for g in result['groups'])
        if all(group['execution_complete'] for group in result['groups'].values()) and result['fresh_case_count']==500:
            result['status'] = 'REGRESSION_COMPLETE_WITH_12_HISTORICAL_HOLD'
    except Exception as exc:
        result.update(error=str(exc), traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin',
                        '--if-exists','--force','--maintenance-db=template1','cp6_rollback'], check=True)
        with psycopg.connect(CONTROL) as conn, conn.cursor() as cur:
            prior.verified(cur, 'AN')
            result['primary_unchanged'] = snapshot(cur) == primary
            result['clone_remaining'] = cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not result['primary_unchanged'] or result['clone_remaining'] != 0:
            result['status'] = 'INCOMPLETE'
        save('COMBINED', result)
    assert result['status'] == 'REGRESSION_COMPLETE_WITH_12_HISTORICAL_HOLD', result


if __name__ == '__main__':
    run()
