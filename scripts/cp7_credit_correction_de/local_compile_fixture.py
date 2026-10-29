"""DECLARED STRUCTURAL STAND-INS, never Native money-flow evidence.

Uses columns from an existing actual CP6 schema dump plus retained private-table
DDL. Strips defaults/constraints only for function compilation. The financial
coordinator is not exercised by this check. Actual Native qualifies in root CI.
"""
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[2]
SQL=('ledger/01_immutable_facts.proposal.sql','readers/02_materialized_profile.proposal.sql',
 'coordinator/01_coordinator_facts.sql','coordinator/03_opening_return_hpp.sql','consumer/02_operation_facts.sql')

def fields(text):
    result=[];start=0;level=0;quote=False;i=0
    while i<len(text):
        c=text[i]
        if c=="'":
            if quote and i+1<len(text)and text[i+1]=="'":i+=2;continue
            quote=not quote
        if not quote:
            level+=int(c=='(')-int(c==')')
            if c==','and level==0:result.append(text[start:i]);start=i+1
        i+=1
    result.append(text[start:]);return result

def tables(text):
    text=re.sub(r'--[^\n]*','',text)
    result={}
    for match in re.finditer(r'create table ([\w.]+)\s*\(',text,re.I):
        if not match[1].startswith(('erp.','cp7_credit.','cp7_sales_return_correction.','cp7_sales.')):continue
        i=match.end();level=1;quote=False;end=i
        while level and end<len(text):
            c=text[end]
            if c=="'":quote=not quote
            if not quote:level+=int(c=='(')-int(c==')')
            end+=1
        columns=[]
        for field in fields(text[i:end-1]):
            field=field.strip()
            if not re.match(r'\w+\s+',field)or field.split()[0].lower()in('constraint','unique','check','foreign','primary','exclude'):continue
            typ=re.split(r'\s+(?:default|not null|primary|unique|references|check|generated|constraint|collate)\b',field,flags=re.I)[0]
            typ=typ.replace('cp7_credit.cent_amount','numeric')
            columns.append(typ)
        result[match[1]]='create table '+match[1]+'('+','.join(columns)+');'
    return result

def build(dump):
    result=tables(Path(dump).read_text())
    credit=ROOT/'scripts/cp7_customer_credit'
    for file in SQL:result.update(tables((credit/file).read_text()))
    for file in ('scripts/cp7-src/sales/return-correction.sql','scripts/cp7-src/sales/write.sql'):
        path=ROOT/file
        if path.exists():result.update(tables(path.read_text()))
    # No table stand-in is a source/profile proof; these only permit type checking.
    result.setdefault('cp7_sales.command_context','create table cp7_sales.command_context(backend_pid int,transaction_id bigint,actor uuid,sale_id uuid,action text);')
    result['cp7_credit.consumption_events']=result['cp7_credit.consumption_events']
    return 'create role anon;create role authenticated;create role service_role;create schema auth;create schema erp;create schema cp7_credit;create schema cp7_sales;create schema cp7_sales_return_correction;create schema ow04_source_proposal;'+''.join(result.values())+'''
create function auth.uid()returns uuid language sql stable as $$select null::uuid$$;
create function cp7_credit.consumer_active_events_v1(uuid)returns jsonb language sql stable as $$select '[]'::jsonb$$;
create function cp7_credit.account_by_mapping_v1(text)returns uuid language sql stable as $$select null::uuid$$;
create function cp7_credit.cent_text(numeric)returns text language sql immutable as $$select round($1,2)::text$$;
create function cp7_credit.materialized_journal_payload(uuid)returns jsonb language sql stable as $$select '{}'::jsonb$$;
create function cp7_credit.native_lines_sha256(jsonb)returns text language sql immutable as $$select repeat('a',64)$$;
create function ow04_source_proposal.sha(jsonb)returns text language sql immutable as $$select repeat('a',64)$$;
create function ow04_source_proposal.financial_journal_payload(uuid,uuid)returns jsonb language sql stable as $$select '{}'::jsonb$$;
'''
if __name__=='__main__':print(build(sys.argv[1]))
