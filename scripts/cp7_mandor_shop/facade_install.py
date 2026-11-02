"""Compose the six facades under a non-superuser creator; no SQL execution.

Historical models retain their exact original inputs. The final installer must
use this composition instead of executing facade/display/sales SQL separately.
The final accepted-parent gate remains closed.
"""
from pathlib import Path
from hashlib import sha256
import json,re

HERE=Path(__file__).resolve().parent
INPUTS={'facade.sql': {'bytes': 2963, 'sha256': '6881ccf3e14420a1779cc2f37811d1885a0d69223fc121f3c212d5bac94227d4'}, 'facade_display.sql': {'bytes': 1187, 'sha256': '7432b03b1d62c7697dd7e9150499cb4f32e1e9a84b096ab1c8de86031eabed19'}, 'sales_commands.sql': {'bytes': 7153, 'sha256': 'cb9da2234fa1834b83ccb2e552f0c1ed3f1595d24c04d97428ca67c1c5df2f3d'}, 'facade_privileges.sql': {'bytes': 2895, 'sha256': 'f5d614819deae1af4229e5c94f644d8954d3da931eba4fb7ea4e5e5593a86efe'}}
PUBLIC=(
 'public.erp_cp7_get_mandor_shop_buyers_v1(text,text,uuid,integer)',
 'public.erp_cp7_prepare_mandor_shop_buyer_v1(jsonb,uuid)',
 'public.erp_cp7_get_mandor_shop_payroll_v1(uuid,uuid)',
 'public.erp_cp7_save_mandor_shop_allocation_v1(text,jsonb,uuid)',
 'public.erp_cp7_get_mandor_shop_customer_buyer_v1(text,uuid)',
 'public.erp_cp7_save_mandor_shop_sale_v1(text,jsonb,uuid,text)')
PRIVATE=('cp7_mandor_shop.is_mandor_customer(uuid)',
 'cp7_mandor_shop.customer_buyer(text,uuid)',
 'cp7_mandor_shop.save_sale(text,jsonb,uuid,text)')
PATTERN=r'(?m)^create (?:or replace )?function ([a-z0-9_.]+)\(([^)]*)\)(.*?)as \$\$(.*?)\$\$;'


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def functions(text):
    result={}
    for match in re.finditer(PATTERN,text,re.S):
        name,arguments,header,body=match.groups()
        signature=name+'('+','.join(a.strip().split()[1]for a in arguments.split(',')if a.strip())+')'
        if signature in result:raise ValueError('MANDOR_FACADE_DUPLICATE_FUNCTION:'+signature)
        result[signature]=dict(statement=match[0],body=body,header=header)
    return result


def derive():
    sources={name:(HERE/name).read_bytes()for name in INPUTS}
    if len(sources)!=4:raise ValueError('MANDOR_FACADE_EXACT_FOUR_INPUTS_REQUIRED')
    for name,raw in sources.items():
        if pin(raw)!=INPUTS[name]:raise ValueError('MANDOR_FACADE_ORIGINAL_INPUT_CHANGED:'+name)
    texts={n:r.decode()for n,r in sources.items()};routes=[]
    for name in('facade.sql','sales_commands.sql'):
        text=texts[name];start=text.index('alter function public.')
        end=text.index('to authenticated;',start)+len('to authenticated;')
        before=text[start:end]
        if text.count(before)!=1:raise ValueError('MANDOR_FACADE_ONE_OWNER_BLOCK_REQUIRED')
        texts[name]=text.replace(before,'',1)
        routes.append(dict(file=name,before=before,after='',count=1,offset=start))
    key=PUBLIC[2];original=functions(texts['facade.sql'])[key]['statement']
    display=functions(texts['facade_display.sql'])[key]['statement']
    replacement=display.replace('create or replace function ','create function ',1)
    if texts['facade.sql'].count(original)!=1:raise ValueError('MANDOR_FACADE_ONE_DISPLAY_ROUTE_REQUIRED')
    texts['facade.sql']=texts['facade.sql'].replace(original,replacement,1)
    routes.append(dict(file='facade.sql',before=original,after=replacement,count=1))
    for name in('facade.sql','sales_commands.sql'):
        restored=texts[name]
        for change in reversed([r for r in routes if r['file']==name]):
            if change['after']:
                if restored.count(change['after'])!=1:raise ValueError('MANDOR_FACADE_DISPLAY_REVERSE_REQUIRED')
                restored=restored.replace(change['after'],change['before'],1)
            else:
                at=change['offset'];restored=restored[:at]+change['before']+restored[at:]
        if restored.encode()!=sources[name]:raise ValueError('MANDOR_FACADE_COMPLETE_ORIGINAL_NOT_RECOVERED:'+name)
    sql=texts['facade.sql']+'\n'+texts['sales_commands.sql']+'\n'+texts['facade_privileges.sql']
    expected=functions(sources['facade.sql'].decode());expected[key]=functions(replacement)[key]
    expected.update(functions(sources['sales_commands.sql'].decode()))
    actual=functions(sql)
    if set(actual)!=set(PUBLIC+PRIVATE)or actual!=expected:
        raise ValueError('MANDOR_FACADE_EXACT_NINE_REVIEWED_BODIES_REQUIRED')
    if sql.count('create role cp7_mandor_shop_api ')!=1:raise ValueError('MANDOR_FACADE_ONE_ORIGINAL_ROLE_REQUIRED')
    return sql,dict(status='EXACT_MANDOR_NON_SUPERUSER_FACADE_COMPOSITION_SOURCE_NOT_NATIVE',
        source_inputs=INPUTS,source_routes=routes,original_files_recovered=True,
        public_functions=6,private_sales_functions=3,all_nine_function_bodies_unchanged=True,
        payroll_display_body_from_exact_existing_projection=True,
        derived_SQL=pin(sql.encode()),actual_SQL_executed=0,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)


def inverse_sql():
    """Pre-use facade-only inverse; owning Native routes must be restored first."""
    return ('grant cp7_mandor_shop_api to postgres with admin false,inherit false,set true;\n'
        'set local role cp7_mandor_shop_api;\ndrop function '+','.join(PUBLIC)+';\n'
        'reset role;\n'
        'drop function '+','.join(PRIVATE)+';\n'
        'revoke usage on schema public,cp7_mandor_shop from cp7_mandor_shop_api;\n'
        'revoke execute on function cp7_mandor_shop.buyer_options(text,text,uuid,integer),'
        'cp7_mandor_shop.buyer_command(jsonb,uuid),cp7_mandor_shop.workspace(uuid,uuid),'
        'cp7_mandor_shop.allocation_command(text,jsonb,uuid)from cp7_mandor_shop_api;\n'
        'revoke usage on schema cp7_mandor_shop from cp7_sales_read;\n'
        'drop role cp7_mandor_shop_api;\n')


if __name__=='__main__':print(json.dumps(derive()[1],indent=2))
