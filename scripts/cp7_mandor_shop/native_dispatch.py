"""One reversible route through the existing authorized Native Sales facade.

The original source/models stay exact. postgres cannot directly execute the
private invoker command owned by cp7_sales_write. Its existing public SECURITY
DEFINER facade already grants postgres EXECUTE and preserves the Native actor,
request, expected version and complete command body without a new grant.
"""
from pathlib import Path
from hashlib import sha256
import json
from . import facade_install

HERE=Path(__file__).resolve().parent
COMMAND='cp7_sales.command(text,jsonb,uuid,text)'
FACADE='public.erp_cp7_save_sale_v1(text,jsonb,uuid,text)'
BEFORE=' result_:=cp7_sales.command(p_action,native_,p_request,p_expected);'
AFTER=' result_:=public.erp_cp7_save_sale_v1(p_action,native_,p_request,p_expected);'


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def derive(functions):
    reference=json.loads((HERE/'NATIVE_SALES_COMMAND_REFERENCE.json').read_bytes())
    for sig in(COMMAND,FACADE):
        if functions.get(sig)!=reference['functions'][sig]:
            raise ValueError('MANDOR_NATIVE_SALES_DISPATCH_EXACT_CURRENT_ALL19_REQUIRED:'+sig)
    command,facade=functions[COMMAND],functions[FACADE]
    if command[1]!='cp7_sales_write'or command[4]is not False or facade[1]!=command[1]or facade[4]is not True:
        raise ValueError('MANDOR_NATIVE_SALES_DISPATCH_OWNER_AND_DEFINER_REQUIRED')
    if not any(row[0]=='postgres'and row[2]=='EXECUTE'for row in facade[18]):
        raise ValueError('MANDOR_NATIVE_SALES_FACADE_EXISTING_POSTGRES_EXECUTE_REQUIRED')
    sql,previous=facade_install.derive()
    if sql.count(BEFORE)!=1 or AFTER in sql:raise ValueError('MANDOR_ONE_NATIVE_SALES_DISPATCH_SITE_REQUIRED')
    derived=sql.replace(BEFORE,AFTER,1)
    if derived.replace(AFTER,BEFORE,1)!=sql:raise ValueError('MANDOR_COMPLETE_ORIGINAL_FACADE_COMPOSITION_NOT_RECOVERED')
    return derived,dict(status='ONE_EXISTING_AUTHORIZED_NATIVE_SALES_FACADE_DISPATCH_SOURCE_NOT_NATIVE',
        original_composition=previous['derived_SQL'],derived_composition=pin(derived.encode()),
        route=dict(before=BEFORE,after=AFTER,count=1),complete_original_composition_recovered=True,
        current_Native_command_all19=pin(json.dumps(command,separators=(',',':')).encode()),
        current_Native_facade_all19=pin(json.dumps(facade,separators=(',',':')).encode()),
        Native_command_and_facade_bodies_and_ACLs_unchanged=True,new_EXECUTE_or_role_grants=0,
        only_new_private_save_sale_dispatch_changed=True,actual_SQL_executed=0,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)
