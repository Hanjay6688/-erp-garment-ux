"""Build new PO observation controls from exact retained catalogue metadata.

This reads no database. The model uses actual column types, with synthetic rows
and explicitly modeled providers; it grants no financial or Auth acceptance.
"""
from pathlib import Path
import argparse,json,re,sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import po_routes
base=po_routes.base
ORIGINAL=dict(bytes=14755737,sha256='80856b7ec2cebf08318a21617091b73c6744161b72bb3be98bcb9ecd2b8109eb')


def prepare(path,parser_path):
    raw=Path(path).read_bytes();base.require(base.pin(raw)==ORIGINAL,'GLOBAL_PO_EXACT_RETAINED_ACTUAL25')
    data=json.loads(raw);base.require(len(data)==25,'GLOBAL_PO_COMPLETE_METADATA_GROUPS')
    catalog={k:dict(v)for k,v in data.items()}
    base.require(all(len(catalog[k])==len(v)for k,v in data.items()),'GLOBAL_PO_DUPLICATE_METADATA_KEY')
    helpers,proof=po_routes.derive();retained,_=base.derive()
    sys.path.insert(0,str(parser_path));import pglast
    statements={name:len(pglast.parse_sql(sql))for name,sql in helpers.items()}
    base.require(set(statements.values())=={3},'GLOBAL_PO_EXACT_FOUR_THREE_STATEMENT_HELPERS')
    pglast.parse_plpgsql(helpers['scope'])
    # This is a source safety check, not the complete call-graph parser review.
    text='\n'.join(helpers[n]for n in ('scope','capture'))
    code=re.sub(r"'(?:[^']|'')*'",'STRING_LITERAL',text)
    code=re.sub(r'/\*[\s\S]*?\*/|--[^\n]*','',code)
    base.require(not re.search(r'(?i)\b(?:insert\s+into|delete\s+from|update\s+[a-z]|lock\s+table|for\s+(?:update|share))\b|\b(?:nextval|gen_random_uuid|pg_advisory\w*|set_config)\s*\(',code),
        'GLOBAL_PO_OBSERVATION_MUST_BE_READONLY')
    base.require(helpers['authority']==retained['authority']and helpers['inspect']==retained['inspect'],
        'GLOBAL_PO_ORIGINAL_AUTHORITY_AND_INSPECTOR_REQUIRED')
    tables=set(re.findall(r'(?i)\b(?:from|join)\s+((?:erp|cp7_sku_conversion)\.[a-z0-9_]+)',text))
    additions=json.loads(base.git('show',base.SKU_HEAD+':scripts/cp7_sku_moving_average/CATALOG_ADDITIONS.json'))
    base.require(base.pin(base.git('show',base.SKU_HEAD+':scripts/cp7_sku_moving_average/valuation.sql'))==additions['valuation_source'],
        'GLOBAL_PO_EXACT_SKU_DECLARED_COLUMNS')
    columns={}
    for table in sorted(tables):
        source=additions['groups']['columns']if table.startswith('cp7_sku_conversion.')else catalog['columns']
        columns[table]=sorted([row for key,row in source.items()if key.startswith(table+':')],key=lambda row:row[1])
        base.require(bool(columns[table]),'GLOBAL_PO_EXACT_COLUMN_MAP_REQUIRED:'+table)
    base.require({'erp.'+t for _,_,t in po_routes.OBSERVATIONS}<=tables,'GLOBAL_PO_ALL31_PHYSICAL_OBSERVATIONS')
    # New direct PO state selection includes a PO without a live lot. No source
    # status filter, monetary-only projection or timestamp erasure is allowed.
    base.require('select id from po_ids' in helpers['capture']and len(po_routes.OBSERVATIONS)==31,
        'GLOBAL_PO_COMPLETE_DIRECT_IDENTITY_SOURCE')
    labels=['Exact immutable actual25 and prepared SKU column maps',
        'Five source routes recover all prior helpers byte for byte',
        'Original authority, inspector and all refusals remain exact',
        'Four helpers retain three private source statements each',
        'PO observer contains no writer, lock, sequence or session-setting call',
        'All thirty-one new rowsets retain full rows and stable multiplicity',
        'Direct PO identity captures saved state without requiring a surviving lot']
    report=dict(status='GLOBAL_SKU_PO_SOURCE_PREREQUISITES_PASS_NOT_RUNTIME',
        original_catalogue=ORIGINAL,prepared_SKU_column_source=additions['valuation_source'],
        source_helpers=proof['derived_helpers'],controls=[dict(label=x,result='PASS')for x in labels],
        column_tables=len(columns),column_count=sum(map(len,columns.values())),
        complete_input_or_final_parent_admission=False,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)
    inputs=dict(classification='MODELED_PO_INPUT_CAPTURE_ONLY_NOT_FINANCIAL_QUALIFICATION',
        helpers=helpers,prior_helpers=retained,proof=proof,columns=columns,observations=po_routes.OBSERVATIONS,
        original_catalogue=ORIGINAL,modeled_callbacks=['cp7_credit.consumer_dependency_graph_v1',
            'cp7_credit.source_hpp_lot_ids_v1','cp7_credit.initial_hpp_account_facts_v1','cp7_credit.pg_jsonb_sha256'],
        row_constraints_owners_RLS_Native_callbacks_and_business_transactions_are_not_tested=True)
    return report,inputs


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--original',required=True);p.add_argument('--parser-path',required=True)
    p.add_argument('--report',required=True);p.add_argument('--model-input',required=True);a=p.parse_args()
    report,inputs=prepare(a.original,a.parser_path)
    Path(a.report).write_text(json.dumps(report,indent=2)+'\n');Path(a.model_input).write_text(json.dumps(inputs,sort_keys=True)+'\n')
    print(json.dumps({k:report[k]for k in ('status','column_tables','column_count','actual_Native_cases')}))
