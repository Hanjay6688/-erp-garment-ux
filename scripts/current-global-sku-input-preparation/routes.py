"""Closed source preparation for Global's current SKU graph and observations.

No installation, database connection or final-parent acceptance exists here.
All original four helper files stay byte-exact. Every addition is reversible.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import ast,json,os,re,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
GLOBAL=ROOT/'scripts/cp7_global_nonpo_envelope'
SKU_HEAD='fea75841e26645f1892d880905231625b47e3065'
SKU_TREE='13c9608a14cf5d137feb84c8bac99954c0c7af50'
OVERLAP=('erp.compute_non_po_product_hpp_targets_v2620f(uuid)',
    'erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)')
TABLES={
 'valuation_quotes_v2':('SKU_GROUP','group_id'),
 'valuation_contributors_v2':('SKU_GROUP','group_id'),
 'valuation_postings_v2':('SKU_GROUP','group_id'),
 'valuation_attributions_v2':('SKU_GROUP','group_id'),
 'sale_allocation_values_v2':('SKU_SALE_ALLOCATION','sale_stock_allocation_id'),
 'sale_allocation_attributions_v2':('SKU_SALE_ALLOCATION','sale_stock_allocation_id'),
 'sale_allocation_components_v2':('SKU_SALE_ALLOCATION','sale_stock_allocation_id'),
 'sales_return_values_v2':('SKU_RETURN_ITEM','sales_return_item_id'),
 'sales_return_attributions_v2':('SKU_RETURN_ITEM','sales_return_item_id'),
 'sales_return_components_v2':('SKU_RETURN_ITEM','sales_return_item_id'),
 'valuation_events_v2':('SKU_VALUE_EVENT','id'),
 'component_events_v2':('SKU_COMPONENT_EVENT','id'),
}


def require(value,message):
    if not value:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))


def expected_authority():
    reference=json.loads((HERE/'SKU_CONSUMER_REFERENCE.json').read_bytes())
    require(reference['contract']=='cp7.global-sku-source-prerequisite.v1'
        and reference['status']=='PREPARED_UNQUALIFIED'and reference['actual_Native_cases']==0,
        'GLOBAL_SKU_PREPARATION_NOT_ACCEPTANCE')
    require(reference['SKU']['head']==SKU_HEAD and reference['SKU']['tree']==SKU_TREE
        and git('rev-parse',SKU_HEAD+'^{tree}').decode().strip()==SKU_TREE,'GLOBAL_SKU_EXACT_SOURCE_TREE')
    actual=reference['functions'];derived={};origins={}
    for key,count in (('consumer_source',8),('credit_source',4)):
        source=reference['SKU'][key];raw=git('show',SKU_HEAD+':'+source['path'])
        require(pin(raw)=={k:source[k]for k in('bytes','sha256')},'GLOBAL_SKU_EXACT_DERIVATION_SOURCE:'+key)
        parsed=ast.parse(raw)
        imports=[n for n in ast.walk(parsed)if isinstance(n,(ast.Import,ast.ImportFrom))]
        require((not imports if key=='consumer_source'else len(imports)==1 and
            isinstance(imports[0],ast.ImportFrom)and imports[0].module=='hashlib'and imports[0].level==0 and
            len(imports[0].names)==1 and imports[0].names[0].name=='sha256'and imports[0].names[0].asname is None),
            'GLOBAL_SKU_ONLY_CLOSED_DERIVATION_MODULE:'+key)
        module=ModuleType('global_exact_SKU_'+key);exec(compile(parsed,source['path'],'exec'),module.__dict__)
        signatures=set(module.SIGNATURES)
        require(len(signatures)==count and signatures<=set(actual)and not signatures&set(derived),
            'GLOBAL_SKU_COMPLETE_EIGHT_CONSUMER_FOUR_CREDIT_ORIGINALS')
        require(all(len(actual[s])==19 for s in signatures),'GLOBAL_SKU_ALL_ORIGINAL_ATTRIBUTES_REQUIRED')
        derived.update(module.patched({s:actual[s][0]for s in signatures}));origins.update({s:source for s in signatures})
    require(set(actual)==set(derived),'GLOBAL_SKU_EXACT_TWELVE_ORIGINALS')
    authority=json.loads((GLOBAL/'graph_helpers/AUTHORITY.json').read_bytes())
    retained=authority['actual_source_profile']['functions']
    require(set(actual)&set(retained)==set(OVERLAP),'GLOBAL_SKU_EXACT_TWO_REFERENCED_CHANGES')
    expected=deepcopy(retained);known=deepcopy(authority['known_functions'])
    for signature in OVERLAP:
        require(actual[signature]==retained[signature]and len(actual[signature])==19,
            'GLOBAL_SKU_EXACT_ORIGINAL_FULL19_FUNCTION:'+signature)
        definition=derived[signature];require(definition.endswith('$function$\n'),'GLOBAL_SKU_CANONICAL_DEFINITION')
        body=definition.split('$function$')[1]
        require(len(definition.split('$function$'))==3,'GLOBAL_SKU_UNAMBIGUOUS_BODY')
        expected[signature][0]=definition
        known[signature].update(prosrc_sha256=sha256(body.encode()).hexdigest(),
            source_function_sha256=sha256(definition.encode()).hexdigest(),source=origins[signature]['path'],
            source_kind='EXACT_PREPARED_SKU_DERIVATION_NOT_FINAL_PARENT')
    return expected,known,authority


def current_reference(catalog):
    expected,_,authority=expected_authority()
    from cp7_global_nonpo_envelope import catalogue_profile
    groups=set(catalogue_profile.queries())-set(catalogue_profile.EXTRA)
    require(set(catalog)==groups,'GLOBAL_SKU_COMPLETE_CURRENT_ALL22_REQUIRED')
    for signature,row in expected.items():
        require(catalog['functions'].get(signature)==row,'GLOBAL_SKU_CURRENT_FULL19_CHANGED:'+signature)
    require(catalog['relations'].get('erp.v_current_hpp')==authority['actual_source_profile']['view_relation'],
        'GLOBAL_SKU_CURRENT_VIEW_CHANGED')
    return dict(status='SOURCE_EXPECTATION_MATCH_ONLY_NOT_FINAL_PARENT_ADMISSION',actual_Native_cases=0)


def facts_sql():
    return ''.join("  'SKU_"+table+"',coalesce((select jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text collate \"C\")"
        "from cp7_sku_conversion."+table+" t where exists(select 1 from domain d "
        "cross join lateral jsonb_array_elements(d.value->'identity_keys')i "
        "where i->>'kind'='"+kind+"'and(i->>'id')::uuid=t."+column+")),'[]'),\n"
        for table,(kind,column)in TABLES.items())


def derive():
    expected,known,authority=expected_authority()
    originals={name:(GLOBAL/'graph_helpers'/(name+'.sql')).read_text()for name in('authority','scope','capture','inspect')}
    origin=json.loads((GLOBAL/'READONLY_GRAPH_ORIGIN.json').read_bytes())
    for name,raw in originals.items():require(pin(raw.encode())=={k:origin['files'][name+'.sql'][k]for k in('bytes','sha256')},
        'GLOBAL_SKU_ORIGINAL_HELPER_CHANGED:'+name)
    result=dict(originals);routes=[]
    def change(name,before,after,label):
        require(result[name].count(before)==1 and after not in result[name],'GLOBAL_SKU_EXACT_SOURCE_ROUTE:'+label)
        result[name]=result[name].replace(before,after,1);routes.append(dict(helper=name,before=before,after=after,label=label))
    literals=list(re.finditer(r"jsonb_each\('((?:[^']|'')*)'::jsonb\)",originals['authority']))
    require(len(literals)==2,'GLOBAL_SKU_EXACT_TWO_AUTHORITY_LITERALS')
    for match,before,after,label in zip(literals,
            (authority['known_functions'],authority['actual_source_profile']['functions']),
            (known,expected),('known_body_metadata','complete19_catalog_rows')):
        require(json.loads(match[1].replace("''","'"))==before,'GLOBAL_SKU_ORIGINAL_AUTHORITY_LITERAL')
        encoded=json.dumps(after,sort_keys=True,separators=(',',':')).replace("'","''")
        change('authority',match[0],"jsonb_each('"+encoded+"'::jsonb)",label)
    anchor="  union select 'PRODUCT',i.product_id from erp.sales_items i where i.sale_id=any(sales)\n"
    change('scope',anchor,anchor+"  union select 'SALE',id from unnest(sales)id\n",'seed_actual_financial_sale_identities')
    anchor="  select 'LOT'::text,l.id,'PRODUCT'::text,l.product_id from erp.fg_lots l\n"
    edges=(HERE/'sku_edges.sql').read_text();require(edges.count('union select ')==31,'GLOBAL_SKU_EXACT31_ECONOMIC_EDGES')
    change('scope',anchor,anchor+edges,'append_immutable_economic_identity_edges')
    anchor="  'hpp_accounts',cp7_credit.initial_hpp_account_facts_v1(),\n"
    change('capture',anchor,facts_sql()+anchor,'complete_twelve_scoped_SKU_rowsets')
    recovered=dict(result)
    for route in reversed(routes):
        name=route['helper'];require(recovered[name].count(route['after'])==1,'GLOBAL_SKU_EXACT_INVERSE_ROUTE')
        recovered[name]=recovered[name].replace(route['after'],route['before'],1)
    require(recovered==originals and result['inspect']==originals['inspect'],'GLOBAL_SKU_ORIGINAL_FOUR_HELPERS_NOT_RECOVERED')
    require(len(routes)==5,'GLOBAL_SKU_EXACT_FIVE_ROUTES')
    return result,dict(status='GLOBAL_SKU_GRAPH_PREPARED_NOT_INSTALLED',SKU_head=SKU_HEAD,SKU_tree=SKU_TREE,
        exact_routes=routes,retained_originals={k:pin(v.encode())for k,v in originals.items()},
        derived_helpers={k:pin(v.encode())for k,v in result.items()},
        changed_Native_reference_rows=2,complete_Native_reference_rows=19,attributes_per_function=19,
        new_identity_edges=31,new_full_rowset_observations=12,
        required_additional_profile_relations=['cp7_sku_conversion.'+n for n in TABLES],
        original_inspector_and_all_refusals_unchanged=True,original_four_helpers_recovered=True,
        runtime_admission=False,actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    print(json.dumps(derive()[1],sort_keys=True))
