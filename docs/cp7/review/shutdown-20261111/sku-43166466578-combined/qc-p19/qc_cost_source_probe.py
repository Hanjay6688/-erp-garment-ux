"""Use ordinary predecessor ERP postings to validate the QC financial fixture."""

from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from inspect import getsource
import json
from pathlib import Path
from uuid import uuid4

import cp6_aa_invoice_partial_audit as retained
from psycopg import connect

from loopback_postgres import cluster
from restore_fixture_erp import original, restore


ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'aac0f1648806a108805591c40cb09ed4a1a78d4c16b5bdb93422d41582724578'
FINAL = 'erp.finalize_material_purchase_invoice_v2'
PERIOD = 'Asia/Jakarta'


def change(text, before, after, count=1):
    assert text.count(before) == count, before
    return text.replace(before, after)


def adapted_fixture():
    assert sha256(Path(retained.__file__).read_bytes()).hexdigest() == SOURCE
    # The original posts every movement through the ERP writers. Use an
    # eight-piece input and stop just before the existing partial QC posting.
    receipt = getsource(retained.estimated_receipt)
    receipt = change(receipt, "'qty': 10", "'qty': 8", 2)
    receipt = change(receipt, "'unit_price': 10", "'unit_price': 29")
    receipt = change(receipt, 'm.qty_signed=10', 'm.qty_signed=8')
    build = getsource(retained.partial_production)
    marker = "    gv = base.group_version(cur, str(group))\n    owner(cur)\n    final = "
    assert build.count(marker) == 1
    build = build.split(marker)[0]
    for before, after, count in (
        ("values(%s,%s,%s,10,'CUTTING'", "values(%s,%s,%s,8,'CUTTING'", 1),
        ('qty_issued=10, qty_consumed=10', 'qty_issued=8, qty_consumed=8', 1),
        ('qty_pcs=10', 'qty_pcs=8', 4),
        ('values(%s,%s,%s,10,10,0)', 'values(%s,%s,%s,8,8,0)', 1),
        ('qty_sent_pcs=10', 'qty_sent_pcs=8', 1),
    ):
        build = change(build, before, after, count)
    build += ("    fixture.update(po=po, group=group, product=product, day=day, receipt=receipt['receipt_id'],"
              " receipt_line=receipt_line, receipt_size=receipt_size)\n")
    env = dict(vars(retained))
    exec(compile(receipt + '\n' + build, str(Path(retained.__file__)) + '::qc-eight', 'exec'), env)
    return env['estimated_receipt'], env['partial_production']


def setup(conn, catalogue):
    definitions = dict(catalogue['functions'])
    conn.execute('create role supabase_admin superuser; grant usage on schema erp,auth to authenticated',
                 prepare=False)
    for name in ('public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)',
                 'public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)',
                 'public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'):
        conn.execute(definitions[name][0])
    # Recreate the predecessor's public route using the original migration.
    migration = Path('supabase/migrations/20260902043000_erp_v2_6_16_cp4_hpp_route_auth_boundary.sql').read_text()
    marker = 'create function public.erp_record_sewing_terminal_v1('
    assert migration.count(marker) == 1
    start = migration.index(marker)
    end = migration.index('$function$;', start) + len('$function$;')
    conn.execute(migration[start:end])


def observe(cur, fixture, through):
    retained.admin(cur)
    mappings = dict(cur.execute("""
        select m.mapping_key, bool_and(a.is_active and a.is_postable)
        from erp.accounting_account_mappings m join erp.chart_accounts a on a.id=m.account_id
        where m.mapping_key in('WIP','FG_INVENTORY','COGS') group by m.mapping_key having count(*)=1
    """).fetchall())
    assert mappings == dict(WIP=True, FG_INVENTORY=True, COGS=True)
    ledger = dict(cur.execute("""
        select a.mapping_key, coalesce(sum(l.debit-l.credit),0)
        from erp.accounting_account_mappings a left join
          (erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
              and j.status in('POSTED','REVERSED') and j.transaction_date<=%s)
          on l.account_id=a.account_id and l.po_id=%s
        where a.mapping_key in('WIP','FG_INVENTORY','COGS')
        group by a.mapping_key
    """, (through, fixture['po'])).fetchall())
    progress = cur.execute('select effective_qty_pcs,qc_good_qty_pcs,remaining_qc_qty_pcs '
                           'from erp.v_fg_partial_completion_progress where cutting_group_id=%s',
                           (fixture['group'],)).fetchone()
    hpp = cur.execute("""
        select f.initial_qty_pcs,h.hpp_per_pcs,h.total_cost
        from erp.fg_lots f join erp.hpp_versions h on h.lot_id=f.id and h.is_current
        where f.po_id=%s and f.product_id=%s and f.lot_origin='PRODUCTION'
    """, (fixture['po'], fixture['product'])).fetchall()
    retained.owner(cur)
    snapshot = cur.execute('select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',
                           (fixture['day'], through, through)).fetchone()[0]
    position = snapshot['financial_position']
    result = dict(WIP=Decimal(str(position['wip_inventory'])), FG_INVENTORY=Decimal(str(position['fg_inventory'])),
                  COGS=Decimal(str(snapshot['performance']['cogs_gl'])))
    return dict(ledger=ledger, progress=progress, owner_report=result, confidence=snapshot['data_confidence']['status'],
                active_postable_account_mappings=mappings, current_hpp=hpp)


def case(conn, actuals=None):
    estimated, build = adapted_fixture()
    with conn.cursor() as cur:
        retained.base.load_fixture_foundation(cur)
        today = cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        fixture = estimated(cur, today)
        retained.admin(cur)
        version = cur.execute('select row_version from erp.material_purchase_headers where id=%s',
                              (fixture['purchase'],)).fetchone()[0]
        payload = dict(purchase_id=fixture['purchase'], supplier_invoice_number='QC-8-' + str(uuid4()),
                       invoice_date=fixture['purchase_day'], received_at=retained.at(fixture['purchase_day'],23,45),
                       reason='Confirm the purchase amount before issuing material',
                       lines=[dict(purchase_item_id=fixture['item'], qty_invoiced=8, final_unit_price=29)])
        retained.rpc(cur, FINAL, payload, uuid4(), int(version))
        build(cur, fixture)
        before = observe(cur, fixture, today)
        if actuals is not None:
            before['report_actuals'] = actuals(cur, fixture, today)
        retained.admin(cur)
        gv = retained.base.group_version(cur, str(fixture['group']))
        retained.owner(cur)
        receipt = retained.base.action(cur, 'POST_FINAL_SKU', dict(
            cutting_group_id=str(fixture['group']), destination_location_id=retained.base.LOCATION,
            physical_at=retained.at(fixture['day'],13).isoformat(), reason='Partial QC of three from eight units',
            good_qty_pcs=3, completion_mode='PARTIAL_SELECTION',
            lines=[dict(final_product_id=fixture['product'], qty_good_pcs=3, qty_bs_pcs=0,
                        source_laundry_receipt_line_id=str(fixture['receipt_line']),
                        source_laundry_receipt_batch_size_line_id=str(fixture['receipt_size']))]), gv)
        after = observe(cur, fixture, today)
        if actuals is not None:
            after['report_actuals'] = actuals(cur, fixture, today)
        expected_before = dict(WIP=Decimal('288'), FG_INVENTORY=Decimal('0'), COGS=Decimal('0'))
        expected_after = dict(WIP=Decimal('180'), FG_INVENTORY=Decimal('108'), COGS=Decimal('0'))
        delta = {key: after['owner_report'][key] - before['owner_report'][key] for key in expected_after}
        assert (before['ledger'], after['ledger']) == (expected_before, expected_after)
        assert delta == {key: expected_after[key] - expected_before[key] for key in expected_after}
        assert (before['progress'], after['progress']) == ((8, 0, 8), (8, 3, 5))
        assert before['confidence'] == after['confidence'] == 'READY'
        assert before['current_hpp'] == [] and after['current_hpp'] == [(3, Decimal('36'), Decimal('108'))]
        assert receipt['committed'] is True and receipt['fg_stock_in_qty_pcs'] == 3
        return dict(status='AB_ACTUAL_QC_BOOK_AND_OWNER_REPORT_VALUES_MATCH', before=before, after=after,
                    owner_report_delta=delta, purchase_qty=8, actual_invoice_unit=29,
                    existing_laundry_unit=7, report_period=dict(from_date=fixture['day'], through_date=today, as_of=today),
                    actual_current_combined_candidate_cases=0)


def main():
    archive = ROOT / 'cp7-intake/SKU_43132617378_ORIGINAL_FAILURE.zip'
    raw, catalogue = original(archive)
    with cluster(ROOT / 'cp7-pg17/package/native/bin') as ci, connect(**ci) as conn:
        restore(conn, raw, catalogue)
        setup(conn, catalogue)
        value = case(conn)
        conn.rollback()
        assert conn.execute("select to_regnamespace('erp')").fetchone() == (None,)
    value['rollback_restored']=True
    print(json.dumps(value, default=str, indent=2))


if __name__ == '__main__':
    main()
