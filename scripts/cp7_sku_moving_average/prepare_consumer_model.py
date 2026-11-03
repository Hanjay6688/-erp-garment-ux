"""Derive early SQL controls from exact retained source, never Native credit."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import sys

HERE = Path(__file__).resolve().parent


def prepare():
    path = Path(os.environ['CP7_SKU_PARENT_ORIGINALS']) / 'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json'
    raw = path.read_bytes()
    assert len(raw) == 30376182
    assert sha256(raw).hexdigest() == '5e22077e71e34add6fd0627c89e9d21a2235f463818e45b233c7619bcfb0d48f'
    catalog = json.loads(raw)['committed'][
        'SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4'][
        'Native_to_copy_handoff']['raw_current_catalog']
    spec = importlib.util.spec_from_file_location('early_consumer_delta', HERE / 'consumer_delta.py')
    delta = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(delta)
    definitions = delta.patched({sig: catalog['functions'][sig][0] for sig in delta.SIGNATURES})
    tables = (
        'erp.products', 'erp.locations', 'erp.production_orders', 'erp.fg_lots',
        'erp.hpp_versions', 'erp.fg_stock_movements', 'erp.sale_stock_allocations',
        'erp.sales_items', 'erp.sales_headers', 'erp.sales_returns', 'erp.sales_return_items',
        'erp.product_conversions', 'erp.product_conversion_allocations',
        'erp.opening_lot_hpp_gl_state', 'erp.opening_hpp_corrections',
        'erp.fg_adjustment_items', 'erp.fg_adjustments', 'erp.audit_logs',
        'erp.non_po_hpp_gl_sync_events_v2620f', 'erp.be_conversion_sources_v1',
        'erp.journal_entries', 'cp7_sku_conversion.groups_v1',
        'cp7_sku_conversion.members_v1',
        'erp.fg_inventory_balances', 'erp.sales_payments',
    )
    columns = {table: sorted([v for k, v in catalog['columns'].items()
                             if k.startswith(table + ':')], key=lambda v: v[1])
               for table in tables}
    assert all(columns.values())
    return dict(classification='MODELED_EXACT_CONSUMER_SQL_NOT_NATIVE_ERP',
                parent_sha256=sha256(raw).hexdigest(), columns=columns,
                definitions=definitions,
                old_opening_sync=catalog['functions']['erp.sync_opening_lot_hpp_to_gl(uuid,date)'][0],
                native_return_helpers={sig: catalog['functions'][sig][0] for sig in (
                    'erp.sale_net_total(uuid)',
                    'erp.post_fg_movement(uuid,uuid,uuid,text,text,integer,numeric,uuid,text,uuid,timestamp with time zone,text,boolean)',
                    'erp.assert_fg_chronological_nonnegative(uuid,uuid,uuid,text)',
                )},
                inventory_unique=catalog['indexes']['erp.fg_inventory_balances_product_id_location_id_quality_grade_key'][0],
                transaction_uniques=[catalog['indexes'][name][0] for name in (
                    'erp.sale_stock_allocations_sale_item_id_lot_id_location_id_key',
                    'erp.uq_sales_return_item_allocation',
                )],
                assert_nonpo=catalog['functions']['erp.assert_non_po_product_hpp_target_book_v2620f(uuid)'][0],
                actual_Native_cases=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    out = prepare()
    Path(sys.argv[1]).write_text(json.dumps(out, sort_keys=True) + '\n')
    print(json.dumps(dict(status='EXACT_CONSUMER_MODEL_INPUTS_PREPARED',
                          tables=len(out['columns']), actual_Native_cases=0)))
