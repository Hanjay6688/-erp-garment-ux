"""Prepared observation of source money; never an actual-parent admission."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIOR=ROOT/'scripts/current-global-sku-input-preparation'
spec=importlib.util.spec_from_file_location('global_money_retained_PO_routes',PRIOR/'po_routes.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
base=prior.base
TABLES={
 'cost_contributors_v3':('SKU_GROUP','group_id'),
 'sale_cost_components_v3':('SKU_SALE_ALLOCATION','sale_stock_allocation_id'),
 'return_cost_components_v3':('SKU_RETURN_ITEM','sales_return_item_id'),
 'cost_events_v3':('SKU_COST_EVENT','id'),
 'group_inverse_rebalances_v3':('SKU_GROUP','group_id'),
 'cost_source_rebalances_v3':('SKU_SOURCE_REBALANCE','id'),
 'cost_money_events_v3':('SKU_COST_MONEY_EVENT','id'),
 'base_money_events_v4':('SKU_BASE_MONEY_EVENT','id'),
 'legacy_groups_v4':('SKU_GROUP','group_id'),
}

def sources():
    reference=json.loads((HERE/'SKU_SOURCE.json').read_bytes())
    base.require(reference['actual_ERP_cases']==0 and reference['runtime_admission']is False
        and reference['production_go']is False,'GLOBAL_MONEY_SOURCE_NOT_ACCEPTANCE')
    tree=reference['tree'];own='scripts/cp7_sku_cost_components/'
    base.require(base.git('cat-file','-t',tree).strip()==b'tree','GLOBAL_MONEY_EXACT_IMMUTABLE_TREE')
    def read(path):return base.git('show',tree+':'+path)
    raw=read(own+'SOURCE.json')
    base.require(base.pin(raw)==reference['manifest'],'GLOBAL_MONEY_PRODUCT_SOURCE_MANIFEST')
    declared=json.loads(raw)
    base.require(len(declared['gates'])==12 and all(v is None for v in declared['gates'].values()),
        'GLOBAL_MONEY_UNQUALIFIED_GATES_CHANGED')
    paths=base.git('ls-tree','-r','--name-only',tree,'--',own).decode().splitlines()
    base.require(set(paths)==set(declared['files'])|{own+'SOURCE.json'},'GLOBAL_MONEY_COMPLETE_COMPONENT_FILESET')
    for path,pin in declared['files'].items():
        base.require(base.pin(read(path))==pin,'GLOBAL_MONEY_IMMUTABLE_PRODUCT_FILE:'+path)
    raw=read(own+'CATALOG_ADDITIONS.json')
    base.require(base.pin(raw)==reference['profile'],'GLOBAL_MONEY_EXACT_PREPARED_METADATA')
    profile=json.loads(raw)
    base.require(profile['actual_ERP_cases']==0 and profile['financial_functions_executed']==0
        and profile['explicit_unused_inverse_all22_exact']is True,'GLOBAL_MONEY_METADATA_NOT_NATIVE')
    tables={n for n,row in profile['groups']['relations'].items()if row[1]in('r','p')}
    base.require(tables=={'cp7_sku_conversion.'+n for n in TABLES},'GLOBAL_MONEY_ALL_NINE_RELATIONS')
    return profile,reference

def expected_authority():
    profile,reference=sources();old,known,authority=base.expected_authority()
    overlap=set(old)&set(profile['replacement_functions'])
    base.require(overlap==set(base.OVERLAP),'GLOBAL_MONEY_EXACT_TWO_AUTHORITY_TRANSITIONS')
    expected=deepcopy(old);updated=deepcopy(known)
    for signature in sorted(overlap):
        before,after=profile['replacement_before'][signature],profile['replacement_functions'][signature]
        base.require(before==old[signature]and len(after)==19 and after[1:]==before[1:],
            'GLOBAL_MONEY_EXACT_CURRENT_FULL19:'+signature)
        definition=after[0];parts=definition.split('$function$')
        base.require(len(parts)==3,'GLOBAL_MONEY_EXACT_CANONICAL_FUNCTION_BODY')
        expected[signature]=after
        updated[signature].update(prosrc_sha256=sha256(parts[1].encode()).hexdigest(),
            source_function_sha256=sha256(definition.encode()).hexdigest(),
            source='scripts/cp7_sku_cost_components/CATALOG_ADDITIONS.json',
            source_kind='EXACT_PREPARED_MONEY_SOURCE_NOT_ACTUAL_PARENT')
    return expected,updated,old,known,reference

def current_reference(catalog):
    expected,_,_,_,_=expected_authority()
    _,_,authority=base.expected_authority()
    from cp7_global_nonpo_envelope import catalogue_profile
    base.require(set(catalog)==set(catalogue_profile.queries())-set(catalogue_profile.EXTRA),
        'GLOBAL_MONEY_EXACT_ALL22_NAMES')
    for signature,row in expected.items():
        base.require(catalog['functions'].get(signature)==row,'GLOBAL_MONEY_CURRENT_FULL19_CHANGED:'+signature)
    base.require(catalog['relations'].get('erp.v_current_hpp')==authority['actual_source_profile']['view_relation'],
        'GLOBAL_MONEY_CURRENT_HPP_VIEW_CHANGED')
    return dict(status='PREPARED_SOURCE_EXPECTATIONS_ONLY',actual_ERP_cases=0,runtime_admission=False)

def derive():
    original,previous=prior.derive();result=dict(original);routes=[]
    expected,known,old,old_known,reference=expected_authority()
    def change(name,before,after,label):
        base.require(result[name].count(before)==1 and after not in result[name],'GLOBAL_MONEY_EXACT_ROUTE:'+label)
        result[name]=result[name].replace(before,after,1)
        routes.append(dict(helper=name,before=before,after=after,label=label))
    literals=list(re.finditer(r"jsonb_each\('((?:[^']|'')*)'::jsonb\)",original['authority']))
    base.require(len(literals)==2,'GLOBAL_MONEY_TWO_RETAINED_AUTHORITY_LITERALS')
    for match,before,after,label in zip(literals,(old_known,old),(known,expected),('current_money_body_hashes','current_money_full19')):
        base.require(json.loads(match[1].replace("''","'"))==before,'GLOBAL_MONEY_RETAINED_AUTHORITY_LITERAL')
        encoded=json.dumps(after,sort_keys=True,separators=(',',':')).replace("'","''")
        change('authority',match[0],"jsonb_each('"+encoded+"'::jsonb)",label)
    anchor="  select 'LOT'::text,l.id,'PRODUCT'::text,l.product_id from erp.fg_lots l\n"
    edges=(HERE/'money_edges.sql').read_text()
    base.require(edges.count('union select ')==24,'GLOBAL_MONEY_EXACT_TWENTY_FOUR_EDGES')
    change('scope',anchor,anchor+edges,'immutable_source_money_identities')
    pairs=[]
    for table,(kind,column)in TABLES.items():
        pairs.append("'SKU_MONEY_"+table+"',coalesce((select jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text collate \"C\")"
            "from cp7_sku_conversion."+table+" t where exists(select 1 from domain d "
            "cross join lateral jsonb_array_elements(d.value->'identity_keys')i "
            "where i->>'kind'='"+kind+"'and(i->>'id')::uuid=t."+column+")),'[]')")
    anchor="  'period',(select to_jsonb(c)from erp.accounting_period_control c where singleton_id=1))"
    change('capture',anchor,anchor+' || jsonb_build_object(\n  '+',\n  '.join(pairs)+'\n )',
        'nine_complete_money_rowsets_separate_argument_budget')
    recovered=dict(result)
    for route in reversed(routes):
        base.require(recovered[route['helper']].count(route['after'])==1,'GLOBAL_MONEY_INVERSE_ROUTE')
        recovered[route['helper']]=recovered[route['helper']].replace(route['after'],route['before'],1)
    base.require(recovered==original and result['inspect']==original['inspect']and len(routes)==4,
        'GLOBAL_MONEY_ORIGINAL_HELPERS_AND_REFUSALS_CHANGED')
    return result,dict(status='PREPARED_GLOBAL_MONEY_OBSERVATIONS_NOT_INSTALLED',source=reference,
        prior_helpers=previous['derived_helpers'],derived_helpers={k:base.pin(v.encode())for k,v in result.items()},
        exact_routes=routes,new_full_rowsets=len(TABLES),new_identity_edges=24,
        all_columns_timestamps_histories_and_multiplicity_retained=True,
        original_inspector_and_Native_writers_unchanged=True,actual_ERP_cases=0,
        runtime_admission=False,production_go=False,independent_acceptance=False)
