#!/usr/bin/env python3
"""Additional independent partial-invoice observations on unmodified AI-R2.

The source fixture provides ordinary production operations, not the oracle.
All numbers below come from ten physical pieces and two explicit invoices.
Every case rolls back, including qualified failures and incomplete fixtures.
"""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import hashlib
import json
import os
import sys
import traceback
import uuid

sys.path.insert(0, str(Path.cwd() / 'scripts'))
import psycopg
import cp6_ah_independent_review as fixture
import cp6_v2620ai_runtime as runtime
from cp6_v2620n_rollback_guards import function_catalog

HEAD = '25fa4736329e5148dfdb3572bc169952cba23251'
TREE = 'a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d'
ROOT = Path('cp6-proof/final-audit')
URL = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
ADMIN = URL.replace('postgres:postgres@', 'supabase_admin:postgres@')
actors, base, prior, peer = fixture.actors, fixture.base, fixture.prior, fixture.peer
production = fixture.production


def save(value):
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'NEW_CROSSFLOW.json').write_text(json.dumps(value, indent=2, default=str) + '\n')


def cents(value):
    return Decimal(value).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def production_with_wages(cur, today):
    before_ledger, before_report = production.ledger(cur), production.reports(cur, today)
    f = production.estimated_receipt(cur, today)
    f.update(ledger_baseline=before_ledger, report_baseline=before_report)
    class RateCursor:
        def __getattr__(self, name):
            return getattr(cur, name)
        def execute(self, query, params=None, **kwargs):
            text = str(query)
            if 'insert into erp.po_work_component_snapshots(' in text:
                assert 'values(%s,%s,%s,1,0,%s)' in text
                query = text.replace('values(%s,%s,%s,1,0,%s)', 'values(%s,%s,%s,1,%s,%s)')
                params = (*params[:3], Decimal('1.27'), params[3])
            if 'insert into erp.work_completion_events(' in text or 'insert into erp.work_completion_lines(' in text:
                peer.ordinary(cur)
            return cur.execute(query, params, **kwargs)
    production.partial_production(RateCursor(), f)
    return f


def compare(state, material_value, ap, grni):
    # Ten consumed raw units + 12.70 earned wages + 70 genuine laundry cost.
    # Of ten pieces: five still WIP, three FG on hand, two sold.
    value = Decimal(material_value) + Decimal('82.70')
    hpp, fg, cogs = cents(value / 2), cents(value * Decimal('.3')), cents(value * Decimal('.2'))
    expected_po = dict(base_output=5, hpp_total=hpp, fg_qty=3, fg_value=fg,
                       cogs_value=cogs, other_value=hpp-fg-cogs, wip_value=cents(value)-hpp)
    expected_ledger = dict(MATERIAL_INVENTORY=0, WIP=cents(value)-hpp,
                           FG_INVENTORY=fg, COGS=cogs, AP_SUPPLIER=-Decimal(ap),
                           GRNI_MATERIAL=-Decimal(grni))
    differences = {}
    for group, expected in [('production', expected_po), ('ledger_delta', expected_ledger),
                            ('report_delta', {k: -v if k in ('AP_SUPPLIER', 'GRNI_MATERIAL') else v
                                              for k, v in expected_ledger.items()})]:
        for key, value in expected.items():
            actual = state.get(group, {}).get(key)
            if actual is None or Decimal(str(actual)) != value:
                differences[group + '.' + key] = dict(expected=value, actual=actual)
    if state['custody'] != dict(sent=10, received=8, sold=2) or state['raw_qty'] != 0:
        differences['physical'] = dict(expected='raw=0,sent=10,received=8,sold=2',
                                       actual=dict(raw=state['raw_qty'], custody=state['custody']))
    if state['confidence']['status'] != 'READY':
        differences['report_readiness'] = state['confidence']
    return differences


def case(cur, today, zone, first_qty, close_day):
    f = production_with_wages(cur, today)
    before = production.observe(cur, f, today)
    errors = compare(before, 100, 0, 100)
    if errors:
        return dict(status='INCOMPLETE', stage='FIXTURE_QUALIFICATION', mismatches=errors)
    if close_day:
        peer.ordinary(cur)
        cur.execute('select erp.close_accounting_through(%s,%s)',
                    (f['purchase_day'], 'Final CP6 independent closed receipt day'))
    observations = []
    invoice_total = Decimal(0)
    remaining = 10
    for index, (qty, price) in enumerate(((first_qty, Decimal('12.50')), (10-first_qty, Decimal('7.50'))), 1):
        actors.admin(cur)
        version = cur.execute('select row_version from erp.material_purchase_headers where id=%s',
                              (f['purchase'],)).fetchone()[0]
        cur.execute('select set_config(\'TimeZone\',%s,true)', (zone,))
        payload = dict(purchase_id=f['purchase'], supplier_invoice_number='FINAL-AUDIT-' + uuid.uuid4().hex,
                       invoice_date=f['purchase_day'], received_at=production.at(today-timedelta(days=1), 15),
                       reason='Independent staged invoice after wages, partial FG and sale',
                       lines=[dict(purchase_item_id=f['item'], qty_invoiced=qty, final_unit_price=price)])
        key = uuid.uuid4()
        response = production.rpc(cur, 'erp.finalize_material_purchase_invoice_v2', payload, key, int(version))
        actors.admin(cur)
        replay_before = actors.boundary(cur)
        repeated = production.rpc(cur, 'erp.finalize_material_purchase_invoice_v2', payload, key, int(version))
        actors.admin(cur)
        replay_exact = repeated == response and actors.boundary(cur) == replay_before
        peer.ordinary(cur)
        cur.execute('select erp.process_cost_recalc_queue(100)')
        invoice_total += qty * price
        remaining -= qty
        state = production.observe(cur, f, today)
        differences = compare(state, invoice_total + remaining * 10, invoice_total, remaining * 10)
        if not replay_exact:
            differences['idempotency'] = 'Replay changed response or data'
        if any(row[1] != 'DONE' for row in state['queue']):
            differences['recalc_queue'] = state['queue']
        if close_day:
            old = before['reports_by_day'][str(today-timedelta(days=1))]
            new = state['reports_by_day'][str(today-timedelta(days=1))]
            for section, keys in [('financial_position', production.REPORT_KEYS.values()), ('performance', ['cogs_gl'])]:
                for field in keys:
                    if old[section][field] != new[section][field]:
                        differences['historic_report.'+field] = dict(before=old[section][field], after=new[section][field])
        observations.append(dict(stage=index, quantity=qty, price=price, replay_exact=replay_exact,
                                 expected_material_total=invoice_total+remaining*10,
                                 expected_ap=invoice_total, expected_grni=remaining*10,
                                 state=state, mismatches=differences))
        if differences:
            return dict(status='BUG_PROVEN', stage='NORMAL_STAGED_INVOICE', observations=observations,
                        oracle='Independent physical and monetary conservation; original installed candidate')
    return dict(status='CONTROL_PASS', observations=observations)


def run():
    import subprocess
    assert os.environ.get('PGURL') == URL and os.environ.get('CP6_AI_INDEPENDENT_CONFIRM') == 'postgres'
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() == HEAD
    assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip() == TREE
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],text=True).strip()
    result = dict(status='INCOMPLETE', candidate_head=HEAD, candidate_tree=TREE,
                  harness_head=os.environ['CP6_AUDIT_HARNESS_HEAD'], expected_cases=16, cases={},
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), production_go=False)
    with psycopg.connect(ADMIN) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='180s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur)) == 690
        baseline, catalog = actors.boundary(cur), function_catalog(cur)
        usage = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        result['temporary_schema_usage'] = not usage
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        actors.actors.claims(cur, {'sub': base.OPERATOR_AUTH, 'role': 'authenticated'})
        base.load_fixture_foundation(cur)
        actors.admin(cur)
        today = cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        for zone in ('UTC','Asia/Jakarta','Pacific/Kiritimati','America/Los_Angeles'):
            for qty in (4, 7):
                for closed in (False, True):
                    name = f'STAGED:{zone}:{qty}+{10-qty}:closed={closed}'
                    actors.admin(cur)
                    prior_boundary = actors.boundary(cur)
                    cur.execute('savepoint final_case')
                    try:
                        row = case(cur,today,zone,qty,closed)
                    except Exception as exc:
                        row = dict(status='INCOMPLETE',stage='OPERATION_OR_FIXTURE',error=str(exc),traceback=traceback.format_exc())
                    finally:
                        cur.execute('rollback to savepoint final_case')
                        actors.admin(cur)
                        cur.execute('release savepoint final_case')
                    row['full_boundary_restored'] = actors.boundary(cur) == prior_boundary
                    if not row['full_boundary_restored']:
                        row['status'] = 'INCOMPLETE'
                    result['cases'][name] = row
                    save(result)
                    print(json.dumps(dict(case=name,status=row['status'],stage=row.get('stage'))),flush=True)
        actors.admin(cur)
        result['catalog_unchanged'] = function_catalog(cur) == catalog
        conn.rollback()
        cur.execute("set local timezone='Asia/Jakarta'")
        result['unseeded_boundary_restored'] = actors.boundary(cur) == baseline
        result['schema_usage_restored'] = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0] == usage
        result['auth_users'],result['app_users'] = cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
        conn.rollback()
    for key, value in [('passed','CONTROL_PASS'),('bugs','BUG_PROVEN'),('incomplete','INCOMPLETE')]:
        result[key] = sum(c['status'] == value for c in result['cases'].values())
    if len(result['cases']) == 16 and result['incomplete'] == 0 and result['auth_users'] == result['app_users'] == 0 and all(result[k] for k in ('catalog_unchanged','unseeded_boundary_restored','schema_usage_restored')):
        result['status'] = 'BUG_PROVEN' if result['bugs'] else 'PASS_REVIEWED_SCOPE'
    save(result)
    return result


if __name__ == '__main__':
    try:
        result = run()
    except Exception as exc:
        result = dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc(),production_go=False)
        save(result)
    print(json.dumps({k:v for k,v in result.items() if k != 'cases'},default=str))
    raise SystemExit(0 if result['status'] == 'PASS_REVIEWED_SCOPE' else 1)
