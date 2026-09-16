#!/usr/bin/env python3
"""Independent CP6 calendar and raw-staging observations. No business patch.

Fixture builders provide ordinary documents only. Expected quantities and
money below are arithmetic, never the writer's PASS or an ERP cost function.
Every case has a savepoint and persists before the next case, including failures.
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import uuid

sys.path.insert(0, str(Path.cwd() / 'scripts'))
import psycopg
import cp6_ah_independent_review as fixtures
import cp6_v2620ai_runtime as runtime
from cp6_v2620n_rollback_guards import function_catalog

HEAD = '25fa4736329e5148dfdb3572bc169952cba23251'
TREE = 'a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d'
URL = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
REPORT = Path('cp6-proof/final-audit/INDEPENDENT_NATIVE_GAPS.json')
actors, base, production, peer = fixtures.actors, fixtures.base, fixtures.production, fixtures.peer


def save(report):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, default=str) + '\n')


def months_before(day, months):
    year, month = divmod(day.year * 12 + day.month - 1 - months, 12)
    return date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))


def cent(value):
    return Decimal(value).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def accounting_mismatches(observed, material, ap, grni):
    # No wage in this fixture. Ten units of material + ten real washes at 7.
    # Five pieces remain WIP; three are on hand and two sold.
    cost = Decimal(material) + 70
    # The conversion boundary posts the rounded cost of five completed pieces;
    # WIP holds the exact remaining cents, not a second rounded half.
    completed_cost = cent(cost / 2)
    expected = {
        'WIP': cent(cost) - completed_cost, 'FG_INVENTORY': cent(cost * Decimal('.3')),
        'COGS': cent(cost * Decimal('.2')), 'MATERIAL_INVENTORY': Decimal(0),
        'AP_SUPPLIER': -Decimal(ap), 'GRNI_MATERIAL': -Decimal(grni),
    }
    errors = {}
    for key, wanted in expected.items():
        actual = Decimal(str(observed['ledger_delta'][key]))
        report = Decimal(str(observed['report_delta'][key]))
        report_wanted = -wanted if key in ('AP_SUPPLIER', 'GRNI_MATERIAL') else wanted
        if actual != wanted or report != report_wanted:
            errors[key] = dict(expected=wanted, ledger=actual, expected_report=report_wanted, report=report)
    if observed['raw_qty'] != 0 or observed['production']['fg_qty'] != 3:
        errors['physical_stock'] = observed['production']
    if observed['custody'] != dict(sent=10, received=8, sold=2):
        errors['custody'] = observed['custody']
    if observed['confidence']['status'] != 'READY':
        errors['confidence'] = observed['confidence']
    return errors, expected


def calendar_case(cur, today, purchased, received, zone, closed):
    # Observe the same complete accounting period for baseline and outcome.
    # The old short-delay helper starts at today-3 and would exclude old COGS.
    original_reports = production.reports
    def period_reports(cursor, through):
        production.owner(cursor)
        return {str(day): production.one(cursor,
                'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',
                (purchased, day, day))
                for day in (through-timedelta(days=1), through)}
    production.reports = period_reports
    try:
        return calendar_case_body(cur, today, purchased, received, zone, closed)
    finally:
        production.reports = original_reports


def calendar_case_body(cur, today, purchased, received, zone, closed):
    baseline_ledger, baseline_report = production.ledger(cur), production.reports(cur, today)
    f = production.estimated_receipt(cur, purchased + timedelta(days=3))
    assert f['purchase_day'] == purchased
    # The fixture's source/draft writes predate every physical posting.
    class OrdinaryDraftCursor:
        def __getattr__(self, name): return getattr(cur, name)
        def execute(self, query, params=None, **kwargs):
            if 'insert into erp.work_completion_events(' in str(query) or 'insert into erp.work_completion_lines(' in str(query):
                peer.ordinary(cur)
            return cur.execute(query, params, **kwargs)
    production.partial_production(OrdinaryDraftCursor(), f)
    f.update(ledger_baseline=baseline_ledger, report_baseline=baseline_report)
    before = production.observe(cur, f, today)
    errors, expected = accounting_mismatches(before, 100, 0, 100)
    if errors:
        return dict(status='INCOMPLETE', stage='FIXTURE_QUALIFICATION', mismatches=errors, state=before)
    history_day = received-timedelta(days=1)
    def historical_report():
        production.owner(cur)
        value = production.one(cur, 'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',
                               (purchased, history_day, history_day))
        return {key:value[key] for key in ('financial_position','performance')}
    historical_before = historical_report()
    if closed:
        peer.ordinary(cur)
        cur.execute('select erp.close_accounting_through(%s,%s)',
                    (purchased, 'Independent calendar invoice closed receipt date'))
    observations, remaining, ap = [], 10, Decimal(0)
    for amount, rate in [(3, Decimal('8.25')), (7, Decimal('11.75'))]:
        actors.admin(cur)
        version = cur.execute('select row_version from erp.material_purchase_headers where id=%s', (f['purchase'],)).fetchone()[0]
        payload = dict(purchase_id=f['purchase'], supplier_invoice_number='CAL-' + uuid.uuid4().hex,
                       invoice_date=purchased, received_at=production.at(received, 15),
                       reason='Three calendar month delayed invoice after physical production and sale',
                       lines=[dict(purchase_item_id=f['item'], qty_invoiced=amount, final_unit_price=rate)])
        cur.execute("select set_config('TimeZone',%s,true)", (zone,))
        request = uuid.uuid4()
        response = production.rpc(cur, 'erp.finalize_material_purchase_invoice_v2', payload, request, int(version))
        actors.admin(cur)
        replay_boundary = actors.boundary(cur)
        replay = production.rpc(cur, 'erp.finalize_material_purchase_invoice_v2', payload, request, int(version))
        actors.admin(cur)
        exact = replay == response and actors.boundary(cur) == replay_boundary
        peer.ordinary(cur)
        cur.execute('select erp.process_cost_recalc_queue(100)')
        remaining -= amount
        ap += amount * rate
        state = production.observe(cur, f, today)
        mismatches, expected = accounting_mismatches(state, ap + remaining * 10, ap, remaining * 10)
        historical_after = historical_report()
        # An open accounting period is not an immutable filed snapshot.
        # Preserve differing historical positions for contract review; only a
        # qualified closed-period change may use the immutable-history oracle.
        if closed and historical_after != historical_before:
            mismatches['report_before_invoice_receipt_changed'] = dict(
                as_of=history_day,before=historical_before,after=historical_after)
        if not exact:
            mismatches['same_request_replay'] = 'Response or data changed'
        if any(row[1] != 'DONE' for row in state['queue']):
            mismatches['queue'] = state['queue']
        observations.append(dict(qty=amount, rate=rate, expected=expected, state=state,
                                 replay_exact=exact, historical_report_day=history_day,
                                 historical_report_unchanged=historical_after==historical_before,
                                 historical_report_before=historical_before,
                                 historical_report_after=historical_after,
                                 mismatches=mismatches))
    historical_review=not closed and any(not x['historical_report_unchanged'] for x in observations)
    return dict(status='BUG_PROVEN' if any(x['mismatches'] for x in observations) else
                'DATE_POLICY_REVIEW_REQUIRED' if historical_review else 'PASS',
                purchase_date=purchased, invoice_received=received, elapsed_days=(received-purchased).days,
                session_zone=zone, receipt_day_closed=closed, invoice_number_count=2,
                stage='ORDINARY_INVOICE_LIFECYCLE', current_totals_reconciled=not any(x['mismatches'] for x in observations),
                open_period_history_review_required=historical_review,observations=observations)


def raw_batch(cur, today, variant):
    actors.admin(cur)
    batch, row_id, location = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    material = fixtures.prior.clone_material(cur, 'raw-import')
    # ACCESSORY needs a category; OTHER can exercise the anonymous opening path.
    cur.execute("update erp.materials set material_type='OTHER' where id=%s", (material,))
    sku = cur.execute('select material_sku from erp.materials where id=%s', (material,)).fetchone()[0]
    loc = 'RAW-IMPORT-' + location.hex[:16]
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'Independent raw staging','RAW_MATERIAL_WAREHOUSE',true)", (location,loc))
    cur.execute("insert into erp.migration_batches(id,batch_code,cutover_at,status) values(%s,%s,%s,'DRAFT')", (batch,'RAW-'+batch.hex[:16],production.at(today-timedelta(days=1),0)))
    payload = dict(balance_type='MATERIAL', material_sku=sku, location_code=loc, qty='10', unit_cost='1.25')
    if variant == 'NONNUMERIC_QTY': payload['qty'] = 'ten'
    if variant == 'MISSING_COST': payload.pop('unit_cost')
    if variant == 'MISSING_LOCATION': payload.pop('location_code')
    if variant == 'NEGATIVE_QTY': payload['qty'] = '-1'
    for n in range(2 if variant == 'DUPLICATE_SOURCE' else 1):
        cur.execute("insert into erp.migration_staging_rows(id,batch_id,entity_type,source_row_no,legacy_key,source_payload,normalized_payload,validation_status) values(%s,%s,'OPENING_BALANCE_ITEM',%s,'original-row',%s::jsonb,%s::jsonb,'PENDING')", (row_id if n==0 else uuid.uuid4(),batch,n+1,json.dumps(payload),json.dumps(payload)))
    return batch, material


def import_case(cur, today, variant):
    batch, material = raw_batch(cur, today, variant)
    actors.admin(cur)
    balance_before = production.ledger(cur)
    cur.execute('savepoint validate_raw')
    validation_error = None
    try:
        actors.owner(cur)
        summary = cur.execute('select * from erp.validate_migration_batch(%s)', (batch,)).fetchall()
    except psycopg.Error as exc:
        validation_error = dict(sqlstate=exc.sqlstate, message=exc.diag.message_primary)
        cur.execute('rollback to savepoint validate_raw')
        summary = None
    cur.execute('release savepoint validate_raw')
    actors.admin(cur)
    rows = cur.execute('select source_row_no,validation_status,validation_errors from erp.migration_staging_rows where batch_id=%s order by source_row_no', (batch,)).fetchall()
    result = dict(status='INCOMPLETE', variant=variant, start_status='PENDING', parser_or_csv_upload_tested=False,
                  summary=summary, validation_error=validation_error, row_results=rows,
                  validation_ledger_unchanged=production.ledger(cur)==balance_before)
    assert result['validation_ledger_unchanged'], 'Validation changed authoritative ledger'
    if variant != 'VALID':
        result['status'] = 'PASS' if validation_error is None and all(r[1]=='ERROR' and r[2] for r in rows) else 'GAP_PROVEN'
        result['requirement'] = 'Owner master section21.1: row-level errors for import validation'
        # Separately distinguish missing row diagnostics from bad data being
        # admitted. A batch-wide exception alone is not proof of bad posting.
        cur.execute('savepoint prepare_invalid')
        refused = None
        try:
            actors.owner(cur)
            cur.execute('select erp.prepare_migration_opening_balance(%s,%s)',
                        (batch,'INVALID-'+uuid.uuid4().hex[:16])).fetchone()
        except psycopg.Error as exc:
            refused = dict(sqlstate=exc.sqlstate,message=exc.diag.message_primary)
        finally:
            cur.execute('rollback to savepoint prepare_invalid')
            cur.execute('release savepoint prepare_invalid')
        actors.admin(cur)
        result['invalid_prepare_refusal'] = refused
        result['invalid_prepare_ledger_unchanged'] = production.ledger(cur)==balance_before
        if refused is None or not result['invalid_prepare_ledger_unchanged']:
            result['status'] = 'BUG_PROVEN'
        return result
    assert validation_error is None and summary == [(1,1,0)] and rows[0][1]=='VALID', result
    actors.owner(cur)
    opening = cur.execute('select erp.prepare_migration_opening_balance(%s,%s)', (batch,'IMP-'+uuid.uuid4().hex[:16])).fetchone()[0]
    replay = cur.execute('select erp.prepare_migration_opening_balance(%s,%s)', (batch,None)).fetchone()[0]
    actors.admin(cur)
    assert replay == opening and production.ledger(cur)==balance_before
    actors.owner(cur)
    cur.execute('select erp.post_opening_balance(%s)', (opening,))
    cur.execute('select erp.finalize_migration_batch(%s)', (batch,))
    actors.admin(cur)
    actual = cur.execute("select coalesce(sum(qty_signed),0),coalesce(sum(qty_signed*unit_cost_snapshot),0) from erp.material_stock_movements where material_id=%s", (material,)).fetchone()
    result.update(status='PASS' if actual == (10,Decimal('12.50')) else 'BUG_PROVEN', expected_totals=[10,Decimal('12.50')], actual_totals=actual, prepare_replay_same_id=replay==opening)
    return result


def run():
    assert os.environ.get('PGURL') == URL and os.environ.get('CP6_AI_INDEPENDENT_CONFIRM') == 'postgres'
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() == HEAD
    assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip() == TREE
    report=dict(status='INCOMPLETE',backend_head=HEAD,backend_tree=TREE,harness_head=os.environ['CP6_AUDIT_HARNESS_HEAD'],
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases={},production_go=False,
                invoice_ui_tested=False,csv_parser_tested=False,synthetic_jwt_sql=True)
    save(report)
    with psycopg.connect(URL.replace('postgres:postgres@','supabase_admin:postgres@')) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='180s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur)) == 690
        baseline, catalog = actors.boundary(cur), function_catalog(cur)
        usage = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not usage: cur.execute('grant usage on schema erp to authenticated')
        actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'))
        base.load_fixture_foundation(cur)
        actors.admin(cur)
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        received=today-timedelta(days=1)
        dates=[(months_before(received,m),received,f'{m}_CALENDAR_MONTHS') for m in (1,2,3)]
        dates += [(date(2026,1,31),date(2026,4,30),'JAN31_APR30'),(date(2026,2,28),date(2026,5,28),'FEB28_MAY28'),(date(2026,5,31),date(2026,8,31),'MAY31_AUG31')]
        specs=[]
        for start,end,label in dates:
            assert end <= received
            for zone in ('UTC','Pacific/Kiritimati'):
                for closed in (False,True):
                    specs.append((f'INVOICE:{label}:{zone}:closed={closed}',lambda cur,start=start,end=end,zone=zone,closed=closed:calendar_case(cur,today,start,end,zone,closed)))
        for variant in ('VALID','MISSING_LOCATION','NEGATIVE_QTY','DUPLICATE_SOURCE','NONNUMERIC_QTY','MISSING_COST'):
            specs.append(('IMPORT:'+variant,lambda cur,variant=variant:import_case(cur,today,variant)))
        report['planned_case_ids']=[name for name,_ in specs]
        save(report)
        for name,operation in specs:
            actors.admin(cur)
            before=actors.boundary(cur)
            cur.execute('savepoint gap_case')
            try: row=operation(cur)
            except Exception as exc: row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint gap_case')
                actors.admin(cur)
                cur.execute('release savepoint gap_case')
            row['full_boundary_restored']=actors.boundary(cur)==before
            if not row['full_boundary_restored']: row['status']='INCOMPLETE'
            report['cases'][name]=row
            save(report)
            print(json.dumps(dict(case=name,status=row['status'],error=row.get('error'))),flush=True)
        report['catalog_unchanged']=function_catalog(cur)==catalog
        conn.rollback()
        report['boundary_restored']=actors.boundary(cur)==baseline
        report['schema_usage_restored']=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==usage
        conn.rollback()
    report['counts']={s:sum(c['status']==s for c in report['cases'].values()) for s in ('PASS','BUG_PROVEN','GAP_PROVEN','DATE_POLICY_REVIEW_REQUIRED','INCOMPLETE')}
    if len(report['cases'])==len(report['planned_case_ids']) and all(report[x] for x in ('catalog_unchanged','boundary_restored','schema_usage_restored')):
        report['status']='INCOMPLETE' if report['counts']['INCOMPLETE'] else 'HOLD' if any(
            report['counts'][s] for s in ('BUG_PROVEN','GAP_PROVEN','DATE_POLICY_REVIEW_REQUIRED')) else 'PASS_REVIEWED_SCOPE'
    save(report)
    return report


if __name__=='__main__':
    try: report=run()
    except Exception as exc:
        report=json.loads(REPORT.read_text()) if REPORT.exists() else {}
        report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc(),production_go=False)
        save(report)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},default=str))
    raise SystemExit(0 if report['status']=='PASS_REVIEWED_SCOPE' else 1)
