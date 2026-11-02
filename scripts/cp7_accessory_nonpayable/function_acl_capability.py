"""Fast PostgreSQL17 role/ACL capability check before the full ERP install.

Uses one new fixed disposable DB, synthetic base tables, the exact settings SQL,
and a transaction rolled back in full. No Native business or Auth case credit.
"""
from pathlib import Path
from hashlib import sha256
from urllib.parse import urlparse
import ast,json,os,re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NAME='cp7_good_date_acl_capability'
OUT=ROOT/'cp6-proof/t3/AFUI_FUNCTION_ACL_CAPABILITY.json'
SIGS=('cp7_accessory_nonpayable.settings_access_v1(boolean)',
 'cp7_accessory_nonpayable.settings_event_v1(uuid)',
 'cp7_accessory_nonpayable.settings_workspace_v1(jsonb)',
 'cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean)',
 'public.erp_cp7_get_good_policy_dates_v1(jsonb)',
 'public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean)')


def setup_sql():
    text=(HERE/'test_settings.mjs').read_text()
    match=re.search(r'await db\.exec\(`(create role anon[\s\S]*?)`\)',text)
    if not match or '${'in match[1]or '\\'in match[1]:raise ValueError('AFUI_ACL_EXACT_LITERAL_MODEL_SETUP_REQUIRED')
    sql=match[1]
    for role in('anon','authenticated','service_role'):
        before='create role '+role+' nologin;'
        if sql.count(before)!=1:raise ValueError('AFUI_ACL_EXACT_PREEXISTING_BROWSER_ROLE_REQUIRED')
        sql=sql.replace(before,'',1)
    return sql


def catalog_queries():
    path=ROOT/'scripts/cp7_ow04_restore_bundle.py';nodes=[]
    for node in ast.parse(path.read_bytes()).body:
        if isinstance(node,ast.FunctionDef)and node.name=='_acl':nodes.append(node)
        if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id in('NAMESPACE','QUERIES')for t in node.targets):nodes.append(node)
    env={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path)+':pure-query-strings','exec'),env)
    if len(env['QUERIES'])!=22:raise ValueError('AFUI_ACL_EXACT_ALL22_QUERIES_REQUIRED')
    return env['QUERIES']


def capture(cur,queries):
    result={}
    for group,query in queries.items():
        rows=cur.execute(query).fetchall();result[group]=dict(rows)
        if len(result[group])!=len(rows):raise ValueError('AFUI_ACL_DUPLICATE_CATALOG_KEY:'+group)
    return result


def global_roles(cur):
    return cur.execute("select (select jsonb_agg(to_jsonb(r)order by rolname)from pg_roles r),"
        "(select jsonb_agg(to_jsonb(m)order by roleid,member,grantor)from pg_auth_members m)").fetchone()


def run():
    from cp7_accessory_nonpayable import admission,settings_stage,source
    admission.parent_receipt();source.preflight()
    if os.environ.get('AFUI_CONFIRM')!='cp6_rollback':raise ValueError('AFUI_ACL_DISPOSABLE_CONFIRMATION_REQUIRED')
    uri=os.environ.get('CP6_ADMISSION_CONTROL_PGURL','');parsed=urlparse(uri)
    if(parsed.scheme not in('postgres','postgresql')or parsed.hostname!='127.0.0.1'
       or parsed.port!=54322 or parsed.path!='/template1'or parsed.username!='cp6_maintenance_admission'
       or parsed.query or parsed.fragment):
        raise ValueError('AFUI_ACL_FIXED_LOCAL_MAINTENANCE_AUTHORITY_REQUIRED')
    import psycopg
    from psycopg import sql
    report=dict(status='INCOMPLETE',actual_ERP_Native_cases=0,actual_Auth_HTTP_cases=0,
        prior_settings_API_and_financial_cases_NOT_rerun=True,synthetic_base_tables_and_Auth_providers=True,
        production_go=False,independent_acceptance=False)
    created=False;roles_before=None
    try:
        with psycopg.connect(uri,autocommit=True,connect_timeout=10)as admin,admin.cursor()as cur:
            if cur.execute('select 1 from pg_database where datname=%s',(NAME,)).fetchone():
                raise ValueError('AFUI_ACL_CAPABILITY_DB_ALREADY_EXISTS_REFUSE_TO_TOUCH')
            roles_before=global_roles(cur)
            cur.execute(sql.SQL('create database {} owner postgres template template0').format(sql.Identifier(NAME)))
            created=True
        with psycopg.connect(uri,dbname=NAME,connect_timeout=10)as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='20s';set local lock_timeout='2s'")
            exists=cur.execute("select 1 from pg_roles where rolname='cp7_procure_read'").fetchone()
            if not exists:cur.execute('create role cp7_procure_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls')
            cur.execute('set session authorization postgres')
            creator=cur.execute("select current_user,session_user,rolsuper,rolcreaterole,pg_get_userbyid(10),current_setting('server_version_num')::int from pg_roles where rolname=current_user").fetchone()
            if creator[:5]!=('postgres','postgres',False,True,'supabase_admin')or not 170000<=creator[5]<180000:
                raise ValueError('AFUI_ACL_ACTUAL_NON_SUPERUSER_POSTGRES17_PROFILE_REQUIRED')
            report['actual_creator_profile']=list(creator)
            cur.execute(setup_sql(),prepare=False)
            # Native schema-specific defaults add to the global PUBLIC default.
            reference=json.loads((HERE/'ACTUAL_FUNCTION_DEFAULT_ACL_REFERENCE.json').read_bytes())
            defaults=reference['defaults']['postgres:public:f']
            for grantee,grantor,privilege,option in defaults:
                if grantor!='postgres'or privilege!='EXECUTE'or option is not False:
                    raise ValueError('AFUI_ACL_EXACT_ACTUAL_PUBLIC_EXECUTE_DEFAULT_REQUIRED')
                cur.execute(sql.SQL('alter default privileges for role postgres in schema public grant execute on functions to {}').format(sql.Identifier(grantee)))
            for name in('policy.sql','basis.sql'):cur.execute((HERE/name).read_text(),prepare=False)
            queries=catalog_queries();before=capture(cur,queries)
            raw_public=cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]
            cur.execute((HERE/'settings.sql').read_text(),prepare=False)
            after=capture(cur,queries);settings_stage.transition(before,after);settings_stage.authority(cur)
            public_acl=cur.execute("select oid::regprocedure::text,proacl::text from pg_proc where oid=any(%s::regprocedure[])order by oid::regprocedure::text",(list(SIGS),)).fetchall()
            if cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]!=raw_public:
                raise ValueError('AFUI_ACL_RAW_PUBLIC_SCHEMA_CHANGED')
            report.update(exact_all22_transition=True,exact_six_bodies_and_role_exposure=True,
                raw_public_schema_restored=True,actual_six_function_ACLs=[list(r)for r in public_acl],
                actual_default_function_privileges_unchanged=before['default_privileges']==after['default_privileges'])
            cur.execute(settings_stage.inverse_sql(),prepare=False)
            if capture(cur,queries)!=before:raise ValueError('AFUI_ACL_EXACT_PREUSE_ALL22_NOT_RESTORED')
            report['exact_preuse_all22_restored']=True
            conn.rollback()
            report['all_synthetic_DDL_rolled_back']=True
        report['status']='ACTUAL_POSTGRES17_NON_SUPERUSER_SIX_FUNCTION_ACL_CAPABILITY_PASS_NOT_ERP'
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error))
        raise
    finally:
        if created:
            with psycopg.connect(uri,autocommit=True,connect_timeout=10)as admin,admin.cursor()as cur:
                if cur.execute('select count(*)from pg_stat_activity where datname=%s',(NAME,)).fetchone()[0]:
                    raise ValueError('AFUI_ACL_UNEXPECTED_CAPABILITY_DB_BACKEND_REFUSE_FORCE_DROP')
                cur.execute(sql.SQL('drop database {}').format(sql.Identifier(NAME)))
                report['capability_DB_removed']=True
                if global_roles(cur)!=roles_before:raise ValueError('AFUI_ACL_GLOBAL_ROLES_OR_MEMBERSHIPS_NOT_RESTORED')
                report['global_roles_and_memberships_restored']=True
        report['source_sha256']={name:sha256((HERE/name).read_bytes()).hexdigest()for name in(
            'function_acl_capability.py','settings.sql','settings_stage.py','ACTUAL_FUNCTION_DEFAULT_ACL_REFERENCE.json')}
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(status=report['status'],actual_ERP_Native_cases=0,capability_DB_removed=report.get('capability_DB_removed',False))),flush=True)
    return report
