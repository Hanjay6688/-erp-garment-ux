from pathlib import Path
import importlib.util,json,zipfile

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE.parents[2]/'evidence'/'current39'/'sku-actual-native-before'
spec=importlib.util.spec_from_file_location('moving_average_consumer_delta',HERE/'consumer_delta.py')
delta=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta)
paths={
 delta.SIGNATURES[0]:EVIDENCE/'erp.post_sale(uuid).sql',
 delta.SIGNATURES[1]:EVIDENCE/'erp.post_sales_return(uuid).sql',
 delta.SIGNATURES[2]:EVIDENCE/'erp.compute_non_po_product_hpp_targets_v2620f(uuid).sql',
}
originals={sig:path.read_text()for sig,path in paths.items()}
archive=HERE.parents[2]/'evidence'/'DE_6E615_SUCCESS_FULL_CANONICAL.zip'
with zipfile.ZipFile(archive)as z:
    raw=json.loads(z.read('DE_GLOBAL_BEFORE_NATIVE30/CALLER_RAW_BOUNDARY_OBSERVATION.json'))
for sig in delta.SIGNATURES[3:]:
    originals[sig]=raw['before']['actual_all22']['functions'][sig][0]
patched=delta.patched(originals)
assert set(patched)==set(delta.SIGNATURES)
assert 'prepare_sale_values_v2(h.id)'in patched[delta.SIGNATURES[0]]
assert 'sale_allocation_unit_v2(a.id,a.lot_id)'in patched[delta.SIGNATURES[0]]
assert 'prepare_return_values_v2(h.id)'in patched[delta.SIGNATURES[1]]
assert 'return_item_unit_v2(r.id,r.lot_id,v_original_hpp)'in patched[delta.SIGNATURES[1]]
target=patched[delta.SIGNATURES[2]]
assert 'sale_allocation_components_v2'in target and 'sales_return_components_v2'in target
assert 'component_events_v2'in target and 'conversion_adjustment'in target
assert "root.po_id is null"in target and '(hpp-fg-cogs)::numeric'in target
po=patched[delta.SIGNATURES[3]]
assert 'sale_allocation_components_v2'in po and 'sales_return_components_v2'in po
assert 'component_events_v2'in po and 'root.po_id=p_po_id'in po
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
print({'status':'SKU_MOVAVG_NATIVE_CONSUMER_SIX_EXACT_SUBSTITUTIONS',
       'actual_sql':0,'po_consumer_source_bound':True,'production_go':False})
