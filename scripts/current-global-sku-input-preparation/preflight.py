"""Source, syntax and model input preparation. Never adopts a final parent.

The accepted SKU27 original supplies real column types and metadata. The SKU
successor is unqualified source, not a substitute original. Row constraints,
owners, RLS, Native callbacks and business transactions remain unmodeled here.
"""
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
import argparse,ast,importlib.util,json,re,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(HERE))
import routes


def prepare(original,parser_path):
    reference=json.loads((HERE/'SKU_CONSUMER_REFERENCE.json').read_bytes())
    expected_pin=reference['SKU']['base_original']['originals']['CP7_SKU_MANAGED_RECOVERY_NATIVE27.json']
    raw=Path(original).read_bytes();routes.require(routes.pin(raw)==expected_pin,'GLOBAL_SKU_EXACT_ACCEPTED_COLUMN_ORIGINAL')
    catalog=json.loads(raw)['committed']['SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4']['Native_to_copy_handoff']['raw_current_catalog']
    for signature,row in reference['functions'].items():
        routes.require(catalog['functions'].get(signature)==row,'GLOBAL_SKU_REFERENCE_NOT_ACTUAL_ORIGINAL:'+signature)
    helpers,proof=routes.derive();expected,_,authority=routes.expected_authority()
    candidate=deepcopy(catalog)
    candidate['functions'].update(expected)
    controls=[]
    def refused(label,changed,error):
        try:routes.current_reference(changed)
        except ValueError as exc:routes.require(str(exc).startswith(error),label+':unexpected refusal')
        else:raise ValueError(label+':not refused')
        controls.append(dict(label=label,result='REFUSED_AS_REQUIRED'))
    routes.current_reference(candidate)
    controls.append(dict(label='Complete source-derived nineteen rows and exact view match; no final-parent admission',result='PASS'))
    refused('Old SKU authority is not accepted as current',catalog,'GLOBAL_SKU_CURRENT_FULL19_CHANGED:')
    target=routes.OVERLAP[0]
    for label,index,value in [('Changed owner',1,'service_role'),('Changed SECURITY DEFINER',4,False),
            ('Changed raw ACL',18,None),('Changed function configuration',12,[])]:
        changed=deepcopy(candidate);changed['functions'][target][index]=value
        refused(label,changed,'GLOBAL_SKU_CURRENT_FULL19_CHANGED:')
    changed=deepcopy(candidate);del changed['functions'][target]
    refused('Missing authority function',changed,'GLOBAL_SKU_CURRENT_FULL19_CHANGED:')
    changed=deepcopy(candidate);changed['relations']['erp.v_current_hpp'][0]='service_role'
    refused('Changed current HPP view owner',changed,'GLOBAL_SKU_CURRENT_VIEW_CHANGED')
    changed=deepcopy(candidate);changed['not_the_roles_group']=changed.pop('roles')
    refused('Twenty-two names must be the actual original groups',changed,'GLOBAL_SKU_COMPLETE_CURRENT_ALL22_REQUIRED')

    from cp7_mandor_shop import native_payment_routes,command_guard_routes,native_sales_routes
    from cp7_global_nonpo_envelope import native_hooks,admission,readonly_graph
    readonly_graph.source()
    mandor=set(native_payment_routes.CHANGED)|set(command_guard_routes.ROUTES)|{native_sales_routes.SIGNATURE}
    routes.require(len(mandor)==13 and not mandor & (set(expected)|set(native_hooks.originals())),
        'GLOBAL_SKU_MANDOR_NATIVE_SIGNATURE_OVERLAP_REQUIRES_REVIEW')
    routes.require(admission.RUNTIME_ENTRY is None and admission.PARENT_ROOT_RECEIPT is None,
        'GLOBAL_SKU_PREPARATION_MUST_KEEP_ADMISSION_CLOSED')
    sys.path.insert(0,str(parser_path));import pglast
    statements={name:len(pglast.parse_sql(sql))for name,sql in helpers.items()}
    text='\n'.join(helpers.values())
    code=re.sub(r"'(?:[^']|'')*'",'STRING_LITERAL',text)
    code=re.sub(r'/\*[\s\S]*?\*/|--[^\n]*','',code)
    routes.require(not re.search(r'(?i)\b(?:insert\s+into|delete\s+from|update\s+[a-z]|lock\s+table|for\s+(?:update|share))\b|\b(?:nextval|gen_random_uuid|pg_advisory\w*|set_config)\s*\(',code),
        'GLOBAL_SKU_GRAPH_MUST_STAY_READONLY')
    forbidden={n.split('(')[0]for n,r in authority['known_functions'].items()if r['inspection_only_never_called']}
    routes.require(not any(re.search(r'\b'+re.escape(n)+r'\s*\(',code)for n in forbidden),
        'GLOBAL_SKU_INSPECTION_MUST_NOT_CALL_FINANCIAL_WRITERS')

    sku_profile=json.loads(routes.git('show',routes.SKU_HEAD+':scripts/cp7_sku_moving_average/CATALOG_ADDITIONS.json'))
    valuation=routes.git('show',routes.SKU_HEAD+':scripts/cp7_sku_moving_average/valuation.sql')
    routes.require(routes.pin(valuation)==sku_profile['valuation_source'],'GLOBAL_SKU_EXACT_DECLARED_NEW_COLUMN_SOURCE')
    # PostgreSQL tests consume the exact derived helpers. The old relation column
    # maps are actual accepted metadata; the new maps are unqualified SKU DDL.
    tables=set(re.findall(r'(?i)\b(?:from|join)\s+((?:erp|cp7_sku_conversion)\.[a-z0-9_]+)',helpers['scope']+'\n'+helpers['capture']))
    columns={}
    for table in sorted(tables):
        source=sku_profile['groups']['columns']if table.startswith('cp7_sku_conversion.')else catalog['columns']
        columns[table]=sorted([row for key,row in source.items()if key.startswith(table+':')],key=lambda row:row[1])
        routes.require(bool(columns[table]),'GLOBAL_SKU_ACTUAL_COLUMN_MAP_MISSING:'+table)
    edges=(HERE/'sku_edges.sql').read_text()
    for line in edges.splitlines():
        match=re.search(r'from (cp7_sku_conversion\.[a-z0-9_]+) (\w+)$',line)
        if not match:continue
        table,alias=match.groups();names={row[0]for row in columns[table]}
        routes.require(set(re.findall(r'\b'+alias+r'\.([a-z0-9_]+)',line))<=names,
            'GLOBAL_SKU_EDGE_COLUMN_DOES_NOT_EXIST:'+table)
    routes.require(set(tables)&{'cp7_sku_conversion.'+t for t in routes.TABLES}=={'cp7_sku_conversion.'+t for t in routes.TABLES},
        'GLOBAL_SKU_COMPLETE_TWELVE_RELATIONS')
    enums={}
    for key,label in catalog['enums'].items():
        name,position=key.rsplit(':',1);enums.setdefault(name,[]).append((float(position),label))
    types={row[2]for rows in columns.values()for row in rows}
    enums={name:[label for _,label in sorted(values)]for name,values in enums.items()if name in types}
    report=dict(status='GLOBAL_SKU_NEW_SOURCE_PREREQUISITES_PASS_NOT_RUNTIME',
        SKU_head=routes.SKU_HEAD,SKU_tree=routes.SKU_TREE,controls=controls,
        parsed_statements=statements,readonly_helpers=4,reversible_source_routes=5,
        unchanged_Mandor_Native_adapters=13,overlap_with_Global_reference_or_owning_functions=[],
        column_tables=len(columns),column_count=sum(map(len,columns.values())),
        column_original=expected_pin,new_SKU_column_source=sku_profile['valuation_source'],
        actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
        parent_gate_opened=False,production_go=False,independent_acceptance=False)
    inputs=dict(classification='MODELED_GRAPH_AND_CAPTURE_ONLY_NOT_ERP_QUALIFICATION',helpers=helpers,
        columns=columns,enums=enums,sku_tables=routes.TABLES,proof=proof,
        modeled_callbacks=['cp7_credit.consumer_dependency_graph_v1','cp7_credit.source_hpp_lot_ids_v1',
            'cp7_credit.initial_hpp_account_facts_v1','cp7_credit.pg_jsonb_sha256'],
        row_constraints_owners_RLS_Native_callbacks_and_business_transactions_are_not_tested=True)
    return report,inputs


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--original',required=True);parser.add_argument('--parser-path',required=True)
    parser.add_argument('--report',required=True);parser.add_argument('--model-input',required=True);args=parser.parse_args()
    report,inputs=prepare(args.original,args.parser_path)
    Path(args.report).write_text(json.dumps(report,indent=2)+'\n')
    Path(args.model_input).write_text(json.dumps(inputs,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in('controls','column_original','new_SKU_column_source')}))
