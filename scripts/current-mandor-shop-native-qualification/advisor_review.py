"""Compose the exact Afui reviewer with fifteen private Mandor INFOs.

Only the named RLS-without-policy INFO is eligible. Live metadata must first
prove the complete private table ACLs, column ACLs and exact schema leases.
Warnings, unknown objects, new grants and changed authority remain refused.
This module neither installs SQL nor changes any product privilege.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN=ROOT.parent/'qualified-afui-parent'
PARENT_PATH='scripts/cp7_accessory_nonpayable/advisor_review.py'
PARENT_PIN=dict(bytes=4173,sha256='bd1090e42a4a2519a10c5f2872599703606f9b922026d347b6f873ca368df0df')
PLAN_PATH='scripts/cp7_mandor_shop/INSTALL_PLAN.json'
PLAN_PIN=dict(bytes=13274,sha256='341f2cbd4a0e361bee275f9e66a15c5362a8cee9d3ba91e619b95f376aa7098a')
SCHEMA='cp7_mandor_shop'
TABLES=('allocation_events','allocation_states','allocations','command_context','contractor_accounts',
    'deduction_links','draft_buyers','offset_accounts','payment_work','payroll_identities','requests',
    'sales','settlement_lines','settlement_reversals','settlements')
SCHEMA_ROLES=('cp7_installment_write','cp7_mandor_shop_api','cp7_payroll_write','cp7_sales_read','cp7_sales_write')
ROLES=('anon','authenticated','service_role','cp7_alert','cp7_finance_read')+SCHEMA_ROLES
PRIVILEGES=('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER')


def require(value,message):
    if not value:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def source():
    """The local reference is source preparation, never parent acceptance."""
    raw=(ROOT/PLAN_PATH).read_bytes()
    require(pin(raw)==PLAN_PIN,'MANDOR_ADVISOR_EXACT_INSTALLATION_PLAN')
    plan=json.loads(raw)
    require(plan['tables']==[SCHEMA+'.'+name for name in TABLES],
        'MANDOR_ADVISOR_COMPLETE_EXACT_FIFTEEN_TABLES')
    require(pin((ROOT/PARENT_PATH).read_bytes())==PARENT_PIN,'MANDOR_ADVISOR_UNCHANGED_AFUI_REFERENCE')
    return dict(status='MANDOR_ADVISOR_EXACT_SOURCE_PREPARATION_NOT_RUNTIME',
        Afui_reviewer=PARENT_PIN,installation_plan=PLAN_PIN,private_tables=15,
        inherited_Afui_private_tables=3,product_grants_changed=False,
        actual_SQL_executed=0,actual_ERP_cases=0,production_go=False)


def parent():
    # This file is selected only after the owning qualifier admits its actual
    # frozen Afui parent. A local preparation cannot replace that parent here.
    source();path=FROZEN/PARENT_PATH
    require(path.is_file()and not path.is_symlink()and pin(path.read_bytes())==PARENT_PIN,
        'MANDOR_ADVISOR_EXACT_ACCEPTED_FROZEN_AFUI_REVIEWER')
    spec=importlib.util.spec_from_file_location('mandor_exact_frozen_Afui_advisor',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def require_closed(proof):
    require(type(proof)is dict and set(proof)=={'Afui','Mandor'},'MANDOR_ADVISOR_COMPLETE_PARENT_AND_CHILD_PROOF')
    parent().require_closed(proof['Afui'])
    require(type(proof['Mandor'])is dict and set(proof['Mandor'])==set(TABLES),
        'MANDOR_ADVISOR_EXACT_FIFTEEN_LIVE_AUTHORITIES')
    schema_acl=[[role,'USAGE',False]for role in SCHEMA_ROLES]
    for name,row in proof['Mandor'].items():
        expected=dict(object=[SCHEMA,name],owner='postgres',rls=True,force_rls=False,policies=[],
            schema_owner='postgres',nonowner_schema_acl=schema_acl,
            nonowner_table_acl=[],nonowner_column_acl=[],
            schema_usage={role:role in SCHEMA_ROLES for role in ROLES},
            table_privileges={role:{priv:False for priv in PRIVILEGES}for role in ROLES})
        require(json.dumps(row,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False),
            'MANDOR_ADVISOR_PRIVATE_LIVE_AUTHORITY_CHANGED:'+name)
    return proof


def capture(cur):
    source();result=dict(Afui=parent().capture(cur),Mandor={})
    schema_owner=cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(SCHEMA,)).fetchone()[0]
    schema_acl=cur.execute("select case a.grantee when 0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,"
        "a.privilege_type,a.is_grantable from pg_namespace n,lateral aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner)))a "
        "where n.nspname=%s and a.grantee<>n.nspowner order by 1,2,3",(SCHEMA,)).fetchall()
    for name in TABLES:
        qualified=SCHEMA+'.'+name
        owner,rls,force=cur.execute('select pg_get_userbyid(relowner),relrowsecurity,relforcerowsecurity '
            'from pg_class where oid=%s::regclass',(qualified,)).fetchone()
        policies=cur.execute('select polname from pg_policy where polrelid=%s::regclass order by polname',(qualified,)).fetchall()
        table_acl=cur.execute("select case a.grantee when 0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,"
            "a.privilege_type,a.is_grantable from pg_class c,lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner)))a "
            "where c.oid=%s::regclass and a.grantee<>c.relowner order by 1,2,3",(qualified,)).fetchall()
        column_acl=cur.execute("select t.attname,case a.grantee when 0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,"
            "a.privilege_type,a.is_grantable from pg_class c join pg_attribute t on t.attrelid=c.oid "
            "cross join lateral aclexplode(t.attacl)a where c.oid=%s::regclass and a.grantee<>c.relowner order by 1,2,3,4",
            (qualified,)).fetchall()
        result['Mandor'][name]=dict(object=[SCHEMA,name],owner=owner,rls=rls,force_rls=force,policies=policies,
            schema_owner=schema_owner,nonowner_schema_acl=schema_acl,nonowner_table_acl=table_acl,nonowner_column_acl=column_acl,
            schema_usage={role:cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]for role in ROLES},
            table_privileges={role:{priv:cur.execute('select has_table_privilege(%s,%s,%s)',(role,qualified,priv)).fetchone()[0]
                for priv in PRIVILEGES}for role in ROLES})
    return require_closed(result)


def review(delta,manifest,proof,predecessor_review):
    require_closed(proof)
    original=parent().review(delta,manifest,proof['Afui'],predecessor_review)
    reviewed=[];unexplained=[]
    for finding in original['unexplained']:
        meta=finding.get('metadata')or{}
        exact=(finding.get('name')=='rls_enabled_no_policy'and finding.get('level')=='INFO'
            and meta.get('type')=='table'and meta.get('schema')==SCHEMA and meta.get('name')in TABLES)
        (reviewed if exact else unexplained).append(finding)
    names=[row['metadata']['name']for row in reviewed]
    # The first disposition and complete delta stay intact. Ask the unchanged
    # parent to decide the remainder separately, after only these live-proven
    # child INFOs have been classified. A false parent gate cannot be promoted.
    reviewed_keys={json.dumps(row,sort_keys=True,allow_nan=False)for row in reviewed}
    remaining=dict(delta,added=[row for row in delta.get('added',[])
        if json.dumps(row,sort_keys=True,allow_nan=False)not in reviewed_keys])
    parent_remainder=parent().review(remaining,manifest,proof['Afui'],predecessor_review)
    identities=[(row.get('name'),row.get('level'),(row.get('metadata')or{}).get('type'),
        (row.get('metadata')or{}).get('schema'),(row.get('metadata')or{}).get('name'))for row in delta.get('added',[])]
    passed=(delta.get('status')in('NO_NEW_FINDINGS','REVIEW_REQUIRED')and not unexplained
        and len(names)==len(set(names))and set(names).issubset(TABLES)
        and len(identities)==len(set(identities))and parent_remainder['gate']is True)
    return dict(status='VERIFIED_AFUI_AND_MANDOR_PRIVATE_DEFAULT_DENY_INFO'if passed else'UNEXPLAINED_FINDINGS',
        predecessor_disposition=original,reviewed_Mandor_private_info=reviewed,current_private_authority=proof,
        unchanged_parent_remainder_disposition=parent_remainder,complete_original_delta=delta,
        unexplained=unexplained,gate=bool(passed))
