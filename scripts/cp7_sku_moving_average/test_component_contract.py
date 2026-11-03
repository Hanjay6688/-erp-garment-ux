from pathlib import Path
import ast,importlib.util
from copy import deepcopy

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
assert 'key.startswith(' not in composition
assert 'catalog_additions.expected()' in composition
assert "EXISTING_TRIGGERS={'erp.sales_headers:sku_component_sale_reverse_v2','erp.sales_returns:sku_component_return_reverse_v2'}"in composition
assert "READER_OWNERS={sig:'cp7_fg_read'for sig in reader_delta.SIGNATURES}"in composition
assert composition.count("with reader_handover(cur),as_owner(cur,'postgres'):")==2
assert composition.count('with reader_function_ddl(cur,signature):cur.execute(')==2
assert "raise ValueError('SKU_MOVAVG_READER_OWNER_CHANGED:'+signature)"in composition

def catalog_controls(source):
    # Execute the actual installer boundary without importing ERP or SQL.
    # The full 639-object profile includes implicit PK/UNIQUE indexes, row
    # and array types, member keys with colons, and parent-side RI triggers.
    spec=importlib.util.spec_from_file_location('sku_exact_catalog_additions',HERE/'catalog_additions.py')
    profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
    names={'SCHEMA','TABLES','INDEXES','FUNCTIONS','EXISTING_TRIGGERS'}
    tree=ast.parse(source)
    selected=[node for node in tree.body if
        isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets)
        or isinstance(node,ast.FunctionDef) and node.name=='transition']
    namespace={'catalog_additions':profile}
    exec(compile(ast.Module(body=selected,type_ignores=[]),'actual_sku_catalog_transition','exec'),namespace)
    transition=namespace['transition'];additions=profile.expected()
    before={name:{}for name in profile.GROUPS}
    existing='erp.existing_private_command(uuid)'
    before['functions'][existing]=['original body','existing owner',True,'same ACL']
    before['relations']['erp.existing_table']=['existing metadata']
    definitions={existing:'exact derived body'}
    after=deepcopy(additions)
    after['functions'][existing]=[definitions[existing],*before['functions'][existing][1:]]
    after['relations'].update(before['relations'])
    transition(before,after,definitions)

    def refused(candidate,expected_prefix,baseline=before,derived=definitions):
        try:transition(baseline,candidate,derived)
        except ValueError as error:
            assert str(error).startswith(expected_prefix),(expected_prefix,str(error))
        else:raise AssertionError('UNDECLARED_OR_INCOMPLETE_CATALOG_ADMITTED')

    missing=metadata=unknown=0
    for group,rows in additions.items():
        for key in rows:
            candidate={name:dict(values)for name,values in after.items()}
            del candidate[group][key]
            refused(candidate,'SKU_MOVAVG_MISSING_CATALOG_ADDITION:'+group+':'+key)
            missing+=1
            candidate[group][key]=['tampered authority or definition',*rows[key][1:]]
            refused(candidate,'SKU_MOVAVG_UNDECLARED_CATALOG_DELTA:'+group+':'+key)
            metadata+=1
        candidate={name:dict(values)for name,values in after.items()}
        candidate[group]['cp7_sku_conversion.valuation_unreviewed_v2']=['unreviewed']
        refused(candidate,'SKU_MOVAVG_UNDECLARED_CATALOG_DELTA:'+group+':')
        unknown+=1

    candidate=deepcopy(after);candidate['functions'][existing][1]='new owner'
    refused(candidate,'SKU_MOVAVG_UNDECLARED_CATALOG_DELTA:functions:'+existing)
    candidate=deepcopy(after);candidate['functions'][existing][0]='different derived body'
    refused(candidate,'SKU_MOVAVG_UNDECLARED_CATALOG_DELTA:functions:'+existing)
    candidate=deepcopy(after);del candidate['relations']['erp.existing_table']
    refused(candidate,'SKU_MOVAVG_UNDECLARED_CATALOG_DELTA:relations:erp.existing_table')
    candidate=deepcopy(after);candidate['relations']['erp.existing_table']=['changed metadata']
    refused(candidate,'SKU_MOVAVG_UNDECLARED_CATALOG_DELTA:relations:erp.existing_table')
    candidate=deepcopy(after);candidate['foreign_group']=candidate.pop('schemas')
    refused(candidate,'SKU_MOVAVG_ALL22_REQUIRED')
    assert (missing,metadata,unknown)==(639,639,22)
    return dict(complete_profile_admitted=True,missing_object_refusals=missing,
        altered_metadata_refusals=metadata,unknown_group_object_refusals=unknown,
        existing_authority_body_removal_refusals=4,wrong_22_group_refusals=1,actual_SQL=0)

catalog_result=catalog_controls(composition)
print({'status':'SKU_MOVAVG_COMPONENT_SOURCE_CONTRACT_PASS','tables':len(expected_tables),
       'functions':len(expected_functions),'indexes':len(expected_indexes),
       'exact_catalog_controls':catalog_result,
       'actual_sql':0,'production_go':False})
