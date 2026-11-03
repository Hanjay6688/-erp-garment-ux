"""Exact source and typed observation inputs; no ERP or installer execution."""
from copy import deepcopy
from pathlib import Path
import argparse
import importlib.util
import json
import re
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('global_money_scoped_routes',HERE/'routes.py')
routes=importlib.util.module_from_spec(spec);spec.loader.exec_module(routes)
base=routes.base
ORIGINAL=dict(bytes=14755737,sha256='80856b7ec2cebf08318a21617091b73c6744161b72bb3be98bcb9ecd2b8109eb')

def prepare(original,parser_path):
    raw=Path(original).read_bytes();base.require(base.pin(raw)==ORIGINAL,'GLOBAL_MONEY_EXACT_ACTUAL25')
    data=json.loads(raw);base.require(len(data)==25,'GLOBAL_MONEY_FULL25_REQUIRED')
    actual={k:dict(v)for k,v in data.items()}
    base.require(all(len(actual[k])==len(v)for k,v in data.items()),'GLOBAL_MONEY_DUPLICATE_METADATA')
    helpers,proof=routes.derive();retained,_=routes.prior.derive();profile,source=routes.sources()
    from cp7_global_nonpo_envelope import catalogue_profile,admission
    base.require(all(getattr(admission,name)is None for name in('PARENT_HEAD','PARENT_TREE','PARENT_ROOT_RECEIPT',
        'PARENT_RUN','PARENT_JOB','PARENT_ROOT_CONTRACT','INPUT_PROFILE_PIN','RUNTIME_ENTRY')),
        'GLOBAL_MONEY_MUST_KEEP_ALL_EIGHT_GATES_CLOSED')
    groups=set(catalogue_profile.queries())-set(catalogue_profile.EXTRA)
    expected,_,old,_,_=routes.expected_authority()
    candidate={k:deepcopy(actual[k])for k in groups};candidate['functions'].update(expected)
    routes.current_reference(candidate);controls=[]
    def refused(label,changed):
        try:routes.current_reference(changed)
        except ValueError as error:controls.append(dict(label=label,result='REFUSED_AS_REQUIRED',error=str(error)))
        else:raise ValueError('GLOBAL_MONEY_NEGATIVE_CONTROL_NOT_REFUSED:'+label)
    stale=deepcopy(candidate);stale['functions'].update(old);refused('Former moving-average monetary authority',stale)
    for signature in base.OVERLAP:
        for index in range(19):
            changed=deepcopy(candidate);changed['functions'][signature][index]={'unreviewed_attribute':index}
            refused(signature+': attribute '+str(index),changed)
    changed=deepcopy(candidate);changed['unknown_group']=changed.pop('roles');refused('Wrong group name with unchanged count',changed)
    changed=deepcopy(candidate);changed['relations']['erp.v_current_hpp'][0]='service_role';refused('Changed HPP view owner',changed)
    sys.path.insert(0,str(parser_path));import pglast
    statements={key:len(pglast.parse_sql(text))for key,text in helpers.items()}
    base.require(set(statements.values())=={3},'GLOBAL_MONEY_FOUR_PRIVATE_THREE_STATEMENT_HELPERS')
    pglast.parse_plpgsql(helpers['scope'])
    text=helpers['scope']+'\n'+helpers['capture']
    code=re.sub(r"'(?:[^']|'')*'",'STRING_LITERAL',text)
    code=re.sub(r'/\*[\s\S]*?\*/|--[^\n]*','',code)
    base.require(not re.search(r'(?i)\b(?:insert\s+into|delete\s+from|update\s+[a-z]|lock\s+table|for\s+(?:update|share))\b|\b(?:nextval|gen_random_uuid|pg_advisory\w*|set_config)\s*\(',code),
        'GLOBAL_MONEY_READONLY_OBSERVATIONS_REQUIRED')
    tables=set(re.findall(r'(?i)\b(?:from|join)\s+((?:erp|cp7_sku_conversion)\.[a-z0-9_]+)',text))
    moving=json.loads(base.git('show',source['tree']+':scripts/cp7_sku_moving_average/CATALOG_ADDITIONS.json'))
    base.require(not set(moving['groups']['columns'])&set(profile['groups']['columns']),'GLOBAL_MONEY_DISJOINT_NEW_COLUMN_GROUPS')
    available=dict(actual['columns']);available.update(moving['groups']['columns']);available.update(profile['groups']['columns'])
    columns={table:sorted([row for key,row in available.items()if key.startswith(table+':')],key=lambda row:row[1])for table in sorted(tables)}
    base.require(all(columns.values()),'GLOBAL_MONEY_EVERY_TABLE_HAS_DECLARED_COLUMN_TYPES')
    base.require({'cp7_sku_conversion.'+name for name in routes.TABLES}<=tables,'GLOBAL_MONEY_ALL_NINE_TABLES_OBSERVED')
    for line in(HERE/'money_edges.sql').read_text().splitlines():
        match=re.search(r'from ((?:erp|cp7_sku_conversion)\.[a-z0-9_]+) (\w+)$',line)
        if match:
            table,alias=match.groups()
            base.require(set(re.findall(r'\b'+alias+r'\.([a-z0-9_]+)',line))<={r[0]for r in columns[table]},
                'GLOBAL_MONEY_UNKNOWN_EDGE_COLUMN:'+table)
    base.require(len(columns)==80 and sum(map(len,columns.values()))==813,'GLOBAL_MONEY_EXACT_TYPED_EIGHTY_TABLES')
    report=dict(status='GLOBAL_MONEY_SOURCE_PREREQUISITES_PASS_NOT_RUNTIME',source=source,
        original_catalogue=ORIGINAL,source_helpers=proof['derived_helpers'],negative_controls=controls,
        parsed_statements=statements,column_tables=len(columns),column_count=sum(map(len,columns.values())),
        new_full_rowsets=9,new_identity_edges=24,all_original_eight_admission_gates_unset=True,
        complete_actual_input_profile=False,actual_ERP_cases=0,production_go=False,independent_acceptance=False)
    inputs=dict(classification='MODELED_MONEY_GRAPH_CAPTURE_ONLY_NOT_ERP',helpers=helpers,prior_helpers=retained,
        proof=proof,columns=columns,money_tables=routes.TABLES,original_catalogue=ORIGINAL,
        modeled_callbacks=['cp7_credit.consumer_dependency_graph_v1','cp7_credit.source_hpp_lot_ids_v1',
            'cp7_credit.initial_hpp_account_facts_v1','cp7_credit.pg_jsonb_sha256'],
        row_constraints_owners_RLS_Native_callbacks_and_business_transactions_are_not_tested=True)
    return report,inputs

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--original',required=True);parser.add_argument('--parser-path',required=True)
    parser.add_argument('--report',required=True);parser.add_argument('--model-input',required=True);args=parser.parse_args()
    report,inputs=prepare(args.original,args.parser_path)
    Path(args.report).write_text(json.dumps(report,indent=2)+'\n');Path(args.model_input).write_text(json.dumps(inputs,sort_keys=True)+'\n')
    print(json.dumps({k:report[k]for k in('status','column_tables','column_count','actual_ERP_cases')}))
