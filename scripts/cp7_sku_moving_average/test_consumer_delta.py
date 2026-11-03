from pathlib import Path
import importlib.util,json,os

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('moving_average_consumer_delta',HERE/'consumer_delta.py')
delta=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta)
parent=Path(os.environ['CP7_SKU_PARENT_ORIGINALS'])/'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json'
raw=json.loads(parent.read_bytes())
functions=raw['committed']['SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4'][
    'Native_to_copy_handoff']['raw_current_catalog']['functions']
originals={sig:functions[sig][0]for sig in delta.SIGNATURES}
patched=delta.patched(originals)
assert set(patched)==set(delta.SIGNATURES)
# PostgreSQL's pg_get_functiondef terminates the closing dollar quote with
# one newline. Keep the two full replacements canonical without relaxing
# the installer's byte-exact definition/owner/ACL comparison.
for sig in delta.SIGNATURES:
    assert patched[sig].endswith('$function$\n'),sig
    assert not patched[sig].endswith('$function$\n\n'),sig
assert 'prepare_sale_values_v2(h.id)'in patched[delta.SIGNATURES[0]]
assert 'sale_allocation_unit_v2(a.id,a.lot_id)'in patched[delta.SIGNATURES[0]]
assert 'prepare_return_values_v2(h.id)'in patched[delta.SIGNATURES[1]]
assert 'return_item_unit_v2(r.id,r.lot_id,v_original_hpp)'in patched[delta.SIGNATURES[1]]
target=patched[delta.SIGNATURES[2]]
assert 'sale_allocation_components_v2'in target and 'sales_return_components_v2'in target
assert 'component_events_v2'in target and 'conversion_adjustment'in target
assert "root.po_id is null"in target and '(hpp-fg-cogs)::numeric'in target
assert 'cp7_sku_conversion.owned_scope_value_v2(p_product_id,null)'in target
po=patched[delta.SIGNATURES[3]]
assert 'sale_allocation_components_v2'in po and 'sales_return_components_v2'in po
assert 'cp7_sku_conversion.owned_scope_value_v2(null,p_po_id)'in po and 'root.po_id=p_po_id'in po
assert '(hpp-fg-cogs)::numeric'in po
sale=patched[delta.SIGNATURES[0]]
assert sale.index('prepare_sale_values_v2(h.id)')<sale.index('assert_non_po_product_hpp_target_book_v2620f')
assert sale.count('sale_allocation_attributions_v2')==5
returned=patched[delta.SIGNATURES[1]]
assert returned.index('prepare_return_values_v2(h.id)')<returned.index('assert_non_po_product_hpp_target_book_v2620f')
assert returned.count('sales_return_attributions_v2')==5
nonpo_sync=patched[delta.SIGNATURES[4]]
assert "cp7.sku_nonpo_sync_expanding"in nonpo_sync and 'root.product_id=p_product_id'in nonpo_sync
assert 'perform erp.sync_po_hpp_to_gl(v_scope.po_id,p_effective_date)'in nonpo_sync
po_sync=patched[delta.SIGNATURES[5]]
assert "cp7.sku_po_sync_expanding"in po_sync and 'related_sales as'in po_sync and 'related_returns as'in po_sync
assert "perform erp.sync_non_po_product_hpp_to_gl_v2620f(v_scope.product_id"in po_sync
print({'status':'SKU_MOVAVG_NATIVE_CONSUMER_EIGHT_EXACT_SUBSTITUTIONS',
       'actual_sql':0,'po_consumer_source_bound':True,'production_go':False})

opening=patched[delta.SIGNATURES[6]]
assert opening.index('for v_scope in')<opening.index('update erp.hpp_versions set is_current=false')
assert "and not exists(select 1 from cp7_sku_conversion.sales_return_values_v2"in returned
sync_opening=patched[delta.SIGNATURES[7]]
assert "v_source_delta is distinct from v_expected_delta"in sync_opening
assert sync_opening.count("e.root_lot_id=l.id and e.source_type='SKU_CONVERSION'")==2
assert "v_source_delta:=v_source_delta+v_scope_delta"in sync_opening
assert "legacy_sold as("in target and "legacy_returned as("in target
assert "legacy_sold as("in po and "legacy_returned as("in po
