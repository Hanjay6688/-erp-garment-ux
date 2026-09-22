"""Independent AR counterexamples and controls; ordinary RPCs, disposable only.

This probe does not replace historical oracles or change installed functions.
Every case is rolled back and the complete ERP/Auth/catalog boundary checked.
"""
from datetime import date, timedelta
from pathlib import Path
import hashlib
import json
import os
import subprocess
import traceback
import uuid

import psycopg
import cp6_aa_invoice_partial_audit as invoice
import cp6_initial_import_production_trial as production
import cp6_ao_ap_installed as api
import cp6_ao_ap_maintenance as maintenance
import cp6_ao_ap_runtime as prior
import cp6_aq_runtime as aq
import cp6_ar_runtime as ar
import cp6_successor_regression as predecessor
from cp6_ao_ap_inventory import function_pins

OUT = Path('cp6-proof/as-probe')
BASE = '7a64c5ffe48d8debe7f02b6df019031c61abd078'
ALLOWED = {'.github/workflows/cp6-as-audit.yml', 'scripts/cp6_as_probe.py'}


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (name + '.json')).write_text(json.dumps(value, indent=2, default=str) + '\n')


def invoice_dates(cur, today, zone, closed, partial, cost):
    """Independent date oracle alongside the inherited physical-money oracle."""
    ledger = invoice.ledger(cur)
    reports = invoice.reports(cur, today)
    f = invoice.estimated_receipt(cur, today)
    f.update(ledger_baseline=ledger, report_baseline=reports)
    if partial:
        invoice.partial_production(cur, f)
    if closed:
        invoice.owner(cur)
        cur.execute('select erp.close_accounting_through(%s,%s)',
                    (f['purchase_day'], 'AS independent closed-date boundary'))
    before = invoice.observe(cur, f, today)
    assert not invoice.differences(before, 10, partial, False), before
    api.admin(cur)
    journals = {r[0] for r in cur.execute('select id from erp.journal_entries')}
    version = cur.execute('select row_version from erp.material_purchase_headers where id=%s', (f['purchase'],)).fetchone()[0]
    key = uuid.uuid4()
    payload = dict(purchase_id=f['purchase'], supplier_invoice_number='AS-' + str(key),
                   invoice_date=f['purchase_day'], received_at=invoice.at(today - timedelta(days=1), 15),
                   reason='AS independently observed economic and recognition dates',
                   lines=[dict(purchase_item_id=f['item'], qty_invoiced=10, final_unit_price=cost)])
    invoice.zone(cur, zone)
    response = invoice.rpc(cur, 'erp.finalize_material_purchase_invoice_v2', payload, key, version)
    api.admin(cur)
    replay_before = predecessor.snapshot(cur)
    assert invoice.rpc(cur, 'erp.finalize_material_purchase_invoice_v2', payload, key, version) == response
    assert predecessor.snapshot(cur) == replay_before, 'AS_REPLAY_MUTATED_DATA'
    after = invoice.observe(cur, f, today)
    errors = invoice.differences(after, cost, partial, True)
    expected = today if closed else f['purchase_day']
    observed = {}
    if partial:
        for kind in ('revaluation_events', 'hpp_events'):
            ids = {r[0] for r in before[kind]}
            added = [r for r in after[kind] if r[0] not in ids]
            observed[kind] = added
            if not added or any(r[1] != expected for r in added):
                errors[kind] = dict(expected=expected, actual=added)
    api.admin(cur)
    observed['journals'] = [r for r in cur.execute(
        'select id,source_type,economic_date,transaction_date,status from erp.journal_entries order by id') if r[0] not in journals]
    if not observed['journals'] or any(r[3] != expected for r in observed['journals']):
        errors['journal_posting_date'] = dict(expected=expected, actual=observed['journals'])
    if closed:
        previous = str(today - timedelta(days=1))
        for section, field in [('financial_position', v) for v in invoice.REPORT_KEYS.values()] + [('performance', 'cogs_gl')]:
            if before['reports_by_day'][previous][section][field] != after['reports_by_day'][previous][section][field]:
                errors['historical_report.' + field] = dict(before=before['reports_by_day'][previous][section][field], after=after['reports_by_day'][previous][section][field])
    assert cur.execute('select count(*) from erp.invoice_recost_execution_context').fetchone()[0] == 0
    return dict(status='COUNTEREXAMPLE' if errors else 'PASS', closed=closed, partial=partial,
                cost=cost, caller_zone=zone, invoice_date=f['purchase_day'], recognition_date=expected,
                observations=observed, mismatches=errors, replay_exact=True, context_cleared=True)


def wip_identity(cur, today, variant):
    f = production.fixture(api, cur, today)
    _, sources = production.finalize(api, cur, f)
    original = cur.execute('select id,brand_id,model_id,size_id from erp.products where sku=%s', (f['code'],)).fetchone()
    second = None
    if variant != 'UNIQUE':
        tag = 'AS-' + uuid.uuid4().hex[:20]
        brand = cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id', (tag, tag)).fetchone()[0]
        second = cur.execute('''insert into erp.products(sku,product_name,model_id,brand_id,size_id,color_name,is_active,effective_from)
            values(%s,'AS same SKU other brand',%s,%s,%s,'Blue',true,%s) returning id''',
            (f['code'], original[2], brand, original[3], invoice.at(today - timedelta(days=6), 8))).fetchone()[0]
    s = sources['WIP']
    payload = dict(batch_id=f['batch'], opening_item_id=s['opening_item_id'], expected_remaining='8',
                   operation='COMPLETE', qty_pcs='4', product_sku=f['code'], location_code=f['code']+'F',
                   date=str(today-timedelta(days=3)), reason='AS exact cross-brand WIP output probe')
    if variant == 'EXPLICIT_SECOND':
        payload['product_id'] = str(second)
    before = predecessor.snapshot(cur)
    cur.execute('savepoint identity_rpc')
    refusal = None
    result = None
    try:
        result = api.call(cur, 'WIP_OUTPUT', payload)
    except psycopg.Error as exc:
        refusal = dict(sqlstate=exc.sqlstate, message=exc.diag.message_primary)
        cur.execute('rollback to savepoint identity_rpc')
    api.admin(cur)
    cur.execute('release savepoint identity_rpc')
    if refusal:
        assert predecessor.snapshot(cur) == before, 'AS_REFUSAL_NOT_ATOMIC'
    chosen = cur.execute('select product_id from erp.fg_lots where id=%s', (result['lot_id'],)).fetchone()[0] if result else None
    errors = {}
    if variant == 'AMBIGUOUS':
        if not refusal:
            errors['ambiguous_sku_posted'] = dict(candidate_ids=[original[0], second], actual_product_id=chosen)
    elif refusal or chosen != (second if variant == 'EXPLICIT_SECOND' else original[0]):
        errors['exact_product_identity'] = dict(expected=second or original[0], chosen=chosen, refusal=refusal)
    if result:
        production.truth(cur)
    return dict(status='COUNTEREXAMPLE' if errors else 'PASS', variant=variant, ordinary_authenticated_rpc=True,
                mismatches=errors, refusal=refusal, result=result, selected_product=chosen,
                ledger_truth_passed=bool(result), refused_atomically=bool(refusal))


def run():
    assert os.environ.get('CP6_AR_CONFIRM') == 'cp6_rollback'
    assert os.environ.get('CP6_DATABASE_CONTAINER') == 'supabase_db_cp5-local'
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    changed = set(subprocess.check_output(['git', 'diff', '--name-only', BASE, head], text=True).splitlines())
    assert changed == ALLOWED, ('AS_PROBE_SOURCE_SCOPE', changed)
    report = dict(status='INCOMPLETE', head=head, predecessor=BASE, cases={}, production_go=False,
                  source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sorted(ALLOWED)},
                  independent_acceptance=False, installed_functions_patched_for_testing=False)
    save('PROBE', report)
    primary = None
    try:
        with psycopg.connect(predecessor.PRIMARY_ADMIN) as conn, conn.cursor() as cur:
            prior.verified(cur, 'AN')
            primary = predecessor.snapshot(cur)
        for family in ('AO', 'AP'):
            maintenance.install(family=family, target_pgurl=predecessor.PG,
                                maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'], report_path=OUT/(family+'_INSTALL.json'))
        aq.change('install', predecessor.PG, os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        ar.change('install', predecessor.PG, os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        with psycopg.connect(predecessor.ADMIN) as conn, conn.cursor() as cur:
            report['runtime_before'] = ar.verified(cur)
            initial = predecessor.snapshot(cur)
            catalog = function_pins(cur)
            assert initial['auth'] == [] and initial['erp']['app_users']['count'] == 0
            if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:
                cur.execute('grant usage on schema erp to authenticated')
            api.seed(cur)
            cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
            today = cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
            predecessor.historical.prior.set_open_period(cur, date(2026, 8, 31))
            cases = []
            for closed in (False, True):
                for zone in ('Asia/Jakarta', 'UTC', 'Etc/GMT+12', 'Pacific/Kiritimati'):
                    for partial, cost in ((False, '20.003'), (True, '20'), (True, '20.003')):
                        cases.append((f'DATE:{closed}:{zone}:{partial}:{cost}', lambda c=closed,z=zone,p=partial,v=cost:invoice_dates(cur,today,z,c,p,v)))
            for variant in ('UNIQUE', 'AMBIGUOUS', 'EXPLICIT_SECOND'):
                cases.append(('WIP_IDENTITY:'+variant, lambda v=variant:wip_identity(cur,today,v)))
            report['planned_case_ids'] = [name for name,_ in cases]
            for name, operation in cases:
                api.admin(cur)
                before = predecessor.snapshot(cur)
                cur.execute('savepoint audit_case')
                try:
                    row = operation()
                except Exception as exc:
                    row = dict(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc())
                finally:
                    cur.execute('rollback to savepoint audit_case')
                    api.admin(cur)
                    cur.execute('release savepoint audit_case')
                row['full_boundary_restored'] = predecessor.snapshot(cur) == before
                if not row['full_boundary_restored']:
                    row['status'] = 'INCOMPLETE'
                report['cases'][name] = row
                save('PROBE', report)
                print(json.dumps(dict(case=name, **row), default=str), flush=True)
            assert function_pins(cur) == catalog
            conn.rollback()
            report['runtime_after'] = ar.verified(cur)
            report['full_boundary_restored'] = predecessor.snapshot(cur) == initial
            conn.rollback()
        report['counts'] = {s:sum(r['status']==s for r in report['cases'].values()) for s in ('PASS','COUNTEREXAMPLE','INCOMPLETE')}
        if report['counts']['INCOMPLETE'] == 0 and report['full_boundary_restored'] and len(report['cases']) == 27:
            report['status'] = 'AUDIT_COMPLETE_WITH_FINDINGS' if report['counts']['COUNTEREXAMPLE'] else 'AUDIT_COMPLETE'
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin', '--if-exists','--force','--maintenance-db=template1','cp6_rollback'], check=True)
        with psycopg.connect(predecessor.PRIMARY_ADMIN) as conn, conn.cursor() as cur:
            prior.verified(cur, 'AN')
            report['primary_unchanged'] = primary is not None and predecessor.snapshot(cur) == primary
            report['clone_remaining'] = cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:
            report['status'] = 'INCOMPLETE'
        save('PROBE', report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases',)}, default=str), flush=True)
    assert report['status'].startswith('AUDIT_COMPLETE'), report.get('error','AS_PROBE_INCOMPLETE')


if __name__ == '__main__':
    run()
