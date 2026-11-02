from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
sql=(HERE/'valuation.sql').read_text()

expected_tables={
 'valuation_quotes_v2','valuation_contributors_v2','valuation_postings_v2','valuation_attributions_v2',
 'sale_allocation_values_v2','sale_allocation_attributions_v2','sale_allocation_components_v2',
 'sales_return_values_v2','sales_return_attributions_v2','sales_return_components_v2',
 'valuation_events_v2','component_events_v2',
}
expected_functions={
 'status_component_reverse_v2','pool_components_v2','pool_attribution_v2','pool_quote_v2','position_value_v2',
 'prepare_sale_values_v2','sale_allocation_unit_v2','prepare_return_values_v2','return_item_unit_v2',
 'prepare_valuation_v2','finalize_valuation_v2','reverse_valuation_v2',
}
for name in expected_tables:
    assert sql.count('create table cp7_sku_conversion.'+name+'(')==1,name
for name in expected_functions:
    assert sql.count('create function cp7_sku_conversion.'+name+'(')==1,name
assert sql.count('$$')==2*len(expected_functions)
assert sql.count('create trigger ')==len(expected_tables)+2
assert 'create trigger sku_component_sale_reverse_v2 after update of status on erp.sales_headers'in sql
assert 'create trigger sku_component_return_reverse_v2 after update of status on erp.sales_returns'in sql

required=(
 'component_units*v_qty/(s->>\'qty\')::numeric transfer_units',
 "select 'SOURCE'::text side,q.source_product_id product_id,c.root_lot_id,-c.transfer_units::numeric units",
 "select 'TARGET',q.target_product_id,c.root_lot_id,c.transfer_units::numeric",
 "select v.product_id,v.location_id,v.quality_grade,c.root_lot_id,-c.component_units::numeric units",
 "select v.product_id,v.location_id,v.quality_grade,c.root_lot_id,c.component_units::numeric units",
 "where source_type=v_type and source_id=v_id and phase='POST'",
 'CP7_SKU_MOVAVG_COMPONENT_POOL_QTY_NOT_CONSERVED',
 'CP7_SKU_SALE_COMPONENT_QTY_NOT_CONSERVED',
 'CP7_SKU_RETURN_COMPONENT_QTY_NOT_CONSERVED',
 'CP7_SKU_COMPONENT_STATUS_REVERSE_NOT_EXACT',
)
for token in required:assert token in sql,token
assert 'source_type in(\'SKU_CONVERSION\',\'SALE\',\'SALES_RETURN\')'in sql
assert "source_type in('SKU_CONVERSION','SALE','SALES_RETURN','RECOST')"in sql
assert '\n+'not in sql

spec=importlib.util.spec_from_file_location('moving_average_composition',HERE/'composition.py')
# Avoid importing the predecessor graph here. The exact source lists are
# checked textually; runtime catalog verification remains the actual gate.
composition=(HERE/'composition.py').read_text()
for name in expected_tables:assert repr(name)in composition,name
for name in expected_functions:assert name+'('in composition,name
assert "EXISTING_TRIGGERS={'erp.sales_headers:sku_component_sale_reverse_v2','erp.sales_returns:sku_component_return_reverse_v2'}"in composition

print({'status':'SKU_MOVAVG_COMPONENT_SOURCE_CONTRACT_PASS','tables':len(expected_tables),
       'functions':len(expected_functions),'actual_sql':0,'production_go':False})
