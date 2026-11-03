"""Observe all direct Mandor caller prerequisites before the first callback.

No actor is created or promoted. The original seeded OWNER helper runs in a
savepoint and must use the ordinary authenticated database identity. Complete
before/after catalogues, data and sequences remain separate original files.
"""
from datetime import date
from pathlib import Path
import json

FUNCTIONS=(
 'public.erp_cp7_correct_note_v1(jsonb,uuid,text)',
 'public.erp_cp7_get_mandor_shop_buyers_v1(text,text,uuid,integer)',
 'public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid)',
 'public.erp_cp7_get_payroll_installments_v1(jsonb)',
 'public.erp_cp7_get_payroll_workspace_v1(text,jsonb)',
 'public.erp_cp7_get_sales_returns_v1(jsonb)',
 'public.erp_cp7_get_sales_v1(jsonb)',
 'public.erp_cp7_save_mandor_shop_allocation_v1(text,jsonb,uuid)',
 'public.erp_cp7_save_mandor_shop_sale_v1(text,jsonb,uuid,text)',
 'public.erp_cp7_save_payroll_installment_v1(text,jsonb,uuid,text)',
 'public.erp_cp7_save_payroll_v1(text,jsonb,uuid,text)',
 'public.erp_cp7_save_sale_v1(text,jsonb,uuid,text)',
)
PERMISSIONS=('finance.ar.view','finance.hpp.view','finance.payroll.view','finance.payroll.approve','finance.payroll.pay',
 'sales.invoice.view','sales.invoice.create','sales.invoice.edit_draft','sales.invoice.post','sales.invoice.reverse',
 'sales.return.view','sales.return.create','sales.return.post','sales.return.reverse')
MAPPINGS=('CONTRACTOR_PAYABLE','AR_CUSTOMER','SALES_REVENUE','FG_INVENTORY','COGS','WIP','MATERIAL_INVENTORY','OPENING_EQUITY')


def check(cur,today,native):
    native.admin(cur);before=native.boundary(cur);errors=[]
    day=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    if type(day)is not date or day!=today:errors.append('GENUINE_WIB_DAY_CHANGED')
    available={sig:cur.execute('select to_regprocedure(%s)is not null',(sig,)).fetchone()[0]for sig in FUNCTIONS}
    errors.extend('MISSING_DIRECT_CALL:'+sig for sig,value in available.items()if value is not True)
    mappings={key:cur.execute('select a.is_active,a.is_postable from erp.accounting_account_mappings m '
        'left join erp.chart_accounts a on a.id=m.account_id where m.mapping_key=%s',(key,)).fetchall()for key in MAPPINGS}
    errors.extend('ACTIVE_POSTABLE_ACCOUNT_MAPPING:'+key for key,value in mappings.items()if value!=[(True,True)])
    location=cur.execute('select is_active,location_type from erp.locations where id=%s',
        (native.modules.bd.chain.base.LOCATION,)).fetchone()
    if location!=(True,'FG_WAREHOUSE'):errors.append('ACTIVE_FG_WAREHOUSE_REQUIRED')
    pcs=cur.execute("select unit_code from erp.uom_definitions where upper(unit_code)='PCS'and dimension='COUNT'and is_active").fetchall()
    if len(pcs)!=1:errors.append('ONE_ACTIVE_COUNT_PCS_REQUIRED')
    period=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchall()
    if len(period)!=1 or(period[0][0]is not None and period[0][0]>=today):errors.append('CURRENT_POSTING_DAY_NOT_OPEN')
    actor={}
    cur.execute('savepoint mandor_native_prerequisite_actor')
    try:
        # Calling master.role_actor() would INSERT an actor and advance audit
        # sequences even after rollback. Inspect the unchanged seeded actor.
        native.sales.auth.actor(cur,None)
        actor['identity']=list(cur.execute('select current_user,session_user,erp.current_app_role()::text').fetchone())
        if actor['identity']!=['authenticated','authenticated','OWNER']:
            errors.append('ORDINARY_AUTHENTICATED_OWNER_REQUIRED')
        actor['permissions']={key:cur.execute('select erp.has_permission(%s)',(key,)).fetchone()[0]for key in PERMISSIONS}
        errors.extend('OWNER_PERMISSION:'+key for key,value in actor['permissions'].items()if value is not True)
        actor['direct_call_capabilities']={sig:bool(available[sig])and cur.execute(
            "select has_schema_privilege(current_user,'public','USAGE')and has_function_privilege(current_user,%s,'EXECUTE')",
            (sig,)).fetchone()[0]for sig in FUNCTIONS}
        errors.extend('OWNER_DIRECT_CALL:'+sig for sig,value in actor['direct_call_capabilities'].items()if value is not True)
    except Exception as error:
        actor.update(status='REFUSED',error_type=type(error).__name__,sqlstate=getattr(error,'sqlstate',None),error=str(error))
        errors.append('ORIGINAL_OWNER_HELPER_OR_PERMISSION_QUERY_REFUSED')
    finally:
        cur.execute('rollback to savepoint mandor_native_prerequisite_actor')
        cur.execute('release savepoint mandor_native_prerequisite_actor')
        native.admin(cur)
    after=native.boundary(cur)
    if after!=before:errors.append('READ_ONLY_PREREQUISITES_CHANGED_CATALOGUE_ROWS_OR_SEQUENCES')
    originals=dict(before_original=native.original('REFUSAL_BEFORE',before),
        after_original=native.original('REFUSAL_AFTER',after))
    return dict(status='PASS'if not errors else'REFUSED',errors=errors,functions=available,owner_actor=actor,
        account_mappings=mappings,location=location,active_PCS=pcs,open_period=period,
        business_day=str(today),observed_WIB_day=str(day),read_only_originals=originals,
        active_parent_domain_fixture_and_complete_catalogue='REQUIRED_UNCHANGED_OWNING_PARENT',
        additional_actors_created=0,roles_promoted=0,product_permissions_added=0,actual_Native_cases=0,
        actual_Auth_HTTP_cases=0,actual_browser_cases=0,production_go=False)


def validate(value):
    """Packet readers check exact coverage and raw identity, not just PASS."""
    def require(ok,message):
        if not ok:raise ValueError('MANDOR_PREREQUISITE_'+message)
    require(value['status']=='PASS'and value['errors']==[],'COMPLETE_PASS_REQUIRED')
    require(set(value['functions'])==set(FUNCTIONS)and all(v is True for v in value['functions'].values()),'ALL_DIRECT_FUNCTIONS_REQUIRED')
    actor=value['owner_actor'];require(actor['identity']==['authenticated','authenticated','OWNER'],'ORDINARY_OWNER_REQUIRED')
    for key,expected in (('permissions',PERMISSIONS),('direct_call_capabilities',FUNCTIONS)):
        require(set(actor[key])==set(expected)and all(v is True for v in actor[key].values()),'EXACT_OWNER_'+key.upper())
    require(set(value['account_mappings'])==set(MAPPINGS)and all(len(v)==1 and len(v[0])==2
        and all(flag is True for flag in v[0])for v in value['account_mappings'].values()),'EXACT_ACTIVE_MAPPINGS')
    location=value['location'];pcs=value['active_PCS']
    require(len(location)==2 and location[0]is True and location[1]=='FG_WAREHOUSE'
        and len(pcs)==1 and len(pcs[0])==1 and type(pcs[0][0])is str and pcs[0][0].upper()=='PCS','WAREHOUSE_AND_PCS')
    day=value['business_day']
    require(type(day)is str and date.fromisoformat(day).isoformat()==day
        and day==value['observed_WIB_day'],'GENUINE_WIB_DAY')
    period=value['open_period']
    require(len(period)==1 and len(period[0])==1,'ONE_POSTING_PERIOD')
    cutoff=period[0][0]
    require(cutoff is None or date.fromisoformat(str(cutoff))<date.fromisoformat(day),'OPEN_POSTING_DAY')
    require(value['active_parent_domain_fixture_and_complete_catalogue']=='REQUIRED_UNCHANGED_OWNING_PARENT','ORIGINAL_PARENT_REQUIRED')
    require(set(value['read_only_originals'])=={'before_original','after_original'},'COMPLETE_READ_ONLY_ORIGINALS_REQUIRED')
    for key in('additional_actors_created','roles_promoted','product_permissions_added','actual_Native_cases','actual_Auth_HTTP_cases','actual_browser_cases'):
        require(type(value[key])is int and value[key]==0,'SOURCE_OR_PREREQUISITE_NOT_BUSINESS_CREDIT')
    require(value['production_go']is False,'NO_PRODUCTION_ACCEPTANCE')
    return dict(status='EXACT_MANDOR_DIRECT_CALLER_PREREQUISITES',functions=len(FUNCTIONS),permissions=len(PERMISSIONS),
        account_mappings=len(MAPPINGS),actual_Native_cases=0)


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x')as output:json.dump(value,output,sort_keys=True,indent=2,default=str);output.write('\n')
