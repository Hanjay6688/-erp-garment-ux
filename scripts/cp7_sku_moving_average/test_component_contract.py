from pathlib import Path
import ast,importlib.util

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
expected_indexes={
 'valuation_events_original_v2','valuation_events_recost_v2',
 'component_events_original_v2','component_events_reverse_v2',
}
for name in expected_tables:
    assert sql.count('create table cp7_sku_conversion.'+name+'(')==1,name
for name in expected_functions:
    assert sql.count('create function cp7_sku_conversion.'+name+'(')==1,name
for name in expected_indexes:
    assert sql.count('create unique index '+name+' on cp7_sku_conversion.')==1,name
assert sql.count('create unique index ')==len(expected_indexes)
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
 'CP7_SKU_VALUE_STATUS_REVERSE_NOT_EXACT',
 'if not v_components and not v_values then return new;end if;',
)
for token in required:assert token in sql,token
assert "if not exists(select 1 from cp7_sku_conversion.component_events_v2 where source_type=v_type" not in sql
assert 'source_type in(\'SKU_CONVERSION\',\'SALE\',\'SALES_RETURN\')'in sql
assert "source_type in('SKU_CONVERSION','SALE','SALES_RETURN','RECOST')"in sql
assert '\n+'not in sql

spec=importlib.util.spec_from_file_location('moving_average_composition',HERE/'composition.py')
# Avoid importing the predecessor graph here. The exact source lists are
# checked textually; runtime catalog verification remains the actual gate.
composition=(HERE/'composition.py').read_text()
for name in expected_tables:assert repr(name)in composition,name
for name in expected_functions:assert name+'('in composition,name
for name in expected_indexes:assert repr(name)in composition,name
assert "or(group in('relations','indexes')and key in INDEXES)"in composition
assert "EXISTING_TRIGGERS={'erp.sales_headers:sku_component_sale_reverse_v2','erp.sales_returns:sku_component_return_reverse_v2'}"in composition
assert "READER_OWNERS={sig:'cp7_fg_read'for sig in reader_delta.SIGNATURES}"in composition
assert composition.count("with reader_handover(cur),as_owner(cur,'postgres'):")==2
assert composition.count('with reader_function_ddl(cur,signature):cur.execute(')==2
assert "raise ValueError('SKU_MOVAVG_READER_OWNER_CHANGED:'+signature)"in composition

def catalog_index_controls(source):
    # Exercise the actual transition function without importing ERP or SQL.
    # PostgreSQL reports an index in both relation and index catalog groups.
    names={'SCHEMA','TABLES','INDEXES','FUNCTIONS','EXISTING_TRIGGERS'}
    tree=ast.parse(source)
    selected=[node for node in tree.body if
        isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets)
        or isinstance(node,ast.FunctionDef) and node.name=='transition']
    namespace={}
    exec(compile(ast.Module(body=selected,type_ignores=[]),'actual_sku_catalog_transition','exec'),namespace)
    groups=('functions','relations','indexes','columns','constraints','triggers','policies')+tuple(
        'unchanged_group_'+str(i)for i in range(15))
    def catalogs(group,key):
        before={name:{}for name in groups}
        after={name:{}for name in groups}
        after['functions']={name:['declared-new-function']for name in namespace['FUNCTIONS']}
        after[group][key]=['declared-index']
        return before,after
    admitted=refused=0
    for group in('relations','indexes'):
        for key in sorted(namespace['INDEXES']):
            namespace['transition'](*catalogs(group,key),{})
            admitted+=1
    controls=[(group,'cp7_sku_conversion.component_unreviewed_v2')for group in('relations','indexes')]
    controls.extend((group,'cp7_sku_conversion.component_events_reverse_v2')for group in groups
        if group not in('relations','indexes'))
    for group,key in controls:
        try:namespace['transition'](*catalogs(group,key),{})
        except ValueError as error:
            assert str(error)=='SKU_MOVAVG_UNDECLARED_CATALOG_DELTA:'+group+':'+key,str(error)
            refused+=1
        else:raise AssertionError('UNDECLARED_INDEX_CATALOG_ADMITTED:'+group+':'+key)
    return dict(known_index_group_pairs=admitted,foreign_name_or_group_refusals=refused,actual_SQL=0)

index_controls=catalog_index_controls(composition)
print({'status':'SKU_MOVAVG_COMPONENT_SOURCE_CONTRACT_PASS','tables':len(expected_tables),
       'functions':len(expected_functions),'indexes':len(expected_indexes),
       'index_catalog_controls':index_controls,
       'actual_sql':0,'production_go':False})

