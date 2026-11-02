"""Four new fixed catalog-helper controls on actual local Supabase17 only.

No old capability, primitive, ERP transaction, Auth or browser suite executes.
The financial parent/runtime gates stay closed. The helper lives in one new
fixed disposable database and all setup/roles/catalogs are restored and removed.
"""
from pathlib import Path
from hashlib import sha256
from urllib.parse import urlparse
import argparse,ast,importlib.util,json,os,re,subprocess,traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp7-proof'
NAME='cp7_catalog_bridge_capability'
BRANCH='refs/heads/astra-a/global-catalog-bridge-capability-20261102'
SIGNATURE='cp7_global_catalog_fence.lock_v1()'


def require(value,message):
    if not value:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def source():
    manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    require(manifest['classification']=='FIXED_PLATFORM_CATALOG_FENCE_ACTUAL17_CAPABILITY_ONLY_NOT_GLOBAL_RUNTIME','BRIDGE_FIXED_MODEL_SCOPE_REQUIRED')
    expected={str((HERE/n).relative_to(ROOT))for n in('probe.py','FENCE.sql','INVERSE.sql','BRIDGE_SOURCE_PROOF.json')}
    expected|={'.github/workflows/cp7-global-catalog-bridge-capability.yml',
        'scripts/cp7_ow04_restore_bundle.py','scripts/current-finance-combined-composition/disposable_start.py'}
    require(set(manifest['files'])==expected,'BRIDGE_EXACT_SEVEN_SOURCE_INPUTS_REQUIRED')
    for name,value in manifest['files'].items():
        p=ROOT/name;require(p.is_file()and not p.is_symlink()and pin(p.read_bytes())==value,'BRIDGE_SOURCE_CHANGED:'+name)
    proof=json.loads((HERE/'BRIDGE_SOURCE_PROOF.json').read_bytes())
    require(proof['platform_source']==pin((HERE/'FENCE.sql').read_bytes()),'BRIDGE_EXACT_PREPARED_PLATFORM_SOURCE_REQUIRED')
    require(proof['platform_helper_owner']=='supabase_admin'and proof['allowed_external_invoker']=='postgres'
        and proof['new_browser_or_service_grants']==0 and proof['postgres_catalog_DML_or_MAINTAIN_grants']==0,'BRIDGE_NO_BROAD_PERMISSION_GRANT')
    return dict(head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        tree=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD^{tree}'],text=True).strip(),
        manifest=pin((HERE/'SOURCE.json').read_bytes()),source_pins=7,actual_Native_cases=0,
        old_Afui_Mandor_catalog_and_relation_controls_NOT_rerun=True,
        actual_global_parent_installer_or_runtime_NOT_admitted=True,production_go=False,independent_acceptance=False)


def queries():
    p=ROOT/'scripts/cp7_ow04_restore_bundle.py';nodes=[]
    for n in ast.parse(p.read_bytes()).body:
        if isinstance(n,ast.FunctionDef)and n.name=='_acl':nodes.append(n)
        if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in('NAMESPACE','QUERIES')for t in n.targets):nodes.append(n)
    env={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p)+':pure-query-strings','exec'),env)
    require(len(env['QUERIES'])==22,'BRIDGE_EXACT_ORIGINAL_ALL22_REQUIRED');return env['QUERIES']


def capture(cur,sql_queries):
    value={}
    for name,sql in sql_queries.items():
        rows=cur.execute(sql).fetchall();value[name]=dict(rows)
        require(len(value[name])==len(rows),'BRIDGE_NO_DUPLICATE_CATALOG_KEY:'+name)
    return value


def roles(cur):
    return cur.execute("select(select jsonb_agg(to_jsonb(r)order by rolname)from pg_roles r),"
        "(select jsonb_agg(to_jsonb(m)order by roleid,member,grantor)from pg_auth_members m)").fetchone()


def fixed_uri():
    uri=os.environ.get('CP6_ADMISSION_CONTROL_PGURL','');p=urlparse(uri)
    require(p.scheme in('postgres','postgresql')and p.hostname=='127.0.0.1'and p.port==54322
        and p.username=='cp6_maintenance_admission'and p.path=='/template1'and not p.query and not p.fragment,
        'BRIDGE_ONLY_FIXED_LOCAL_MAINTENANCE_ALLOWED')
    return uri


def configure(cur):cur.execute("set local search_path='';set local timezone='UTC';set local statement_timeout='20s';set local lock_timeout='2s'")


def run():
    identity=source();require(os.environ.get('GITHUB_REF')==BRANCH,'BRIDGE_ONE_ISOLATED_BRANCH_REQUIRED')
    require(os.environ.get('CAPABILITY_CONFIRM')=='cp7_global_catalog_bridge_only','BRIDGE_EXPLICIT_ISOLATED_CONFIRMATION')
    import psycopg
    from psycopg import sql
    uri=fixed_uri();sql_queries=queries();created=False;roles_before=None;baseline=None
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(status='INCOMPLETE',source=identity,checks=[],raw={},
        all_base_tables_are_models=True,new_privileged_function_is_actual_fixed_prepared_source=True,
        old_completed_capability_and_catalog_and_relation_controls_NOT_rerun=True,
        actual_global_installer_or_parent_adoption=False,global_writer_or_permission_or_phantom_closure=False,
        actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
        production_go=False,independent_acceptance=False)
    try:
        with psycopg.connect(uri,autocommit=True)as admin,admin.cursor()as cur:
            require(not cur.execute('select 1 from pg_database where datname=%s',(NAME,)).fetchone(),'BRIDGE_CAPABILITY_DB_ALREADY_EXISTS_REFUSE_TO_TOUCH')
            roles_before=roles(cur);cur.execute(sql.SQL('create database {} owner postgres template template0').format(sql.Identifier(NAME)));created=True
        with psycopg.connect(uri,dbname=NAME)as conn,conn.cursor()as cur:
            configure(cur);cur.execute('set local role postgres')
            cur.execute('create schema cp7_catalog_bridge_model authorization postgres;create table cp7_catalog_bridge_model.effects(id int primary key,value text)',prepare=False)
            conn.commit()
            configure(cur);baseline=capture(cur,sql_queries)
            public_before=cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]
            cur.execute((HERE/'FENCE.sql').read_text(),prepare=False)
            installed=capture(cur,sql_queries)
            for group in baseline:
                added={'cp7_global_catalog_fence'}if group=='schemas'else{SIGNATURE}if group=='functions'else set()
                require(set(installed[group])-set(baseline[group])==added,'BRIDGE_ONLY_TWO_DECLARED_NEW_OBJECTS:'+group)
                require(all(installed[group].get(k)==v for k,v in baseline[group].items()),'BRIDGE_EXISTING_CATALOG_CHANGED:'+group)
            raw=cur.execute("select p.prosrc,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile,p.proconfig,p.proacl::text,n.nspacl::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid=%s::regprocedure",(SIGNATURE,)).fetchone()
            expected=re.search(r'create function cp7_global_catalog_fence\.lock_v1\(\).*?as \$\$(.*?)\$\$;',(HERE/'FENCE.sql').read_text(),re.S)
            require(expected is not None and raw[0]==expected[1]and raw[1:4]==('supabase_admin',True,'v')
                and set(raw[4])=={'search_path=""','TimeZone=UTC'},'BRIDGE_EXACT_PLATFORM_BODY_OWNER_AND_CONFIGURATION')
            require(cur.execute('select current_user').fetchone()[0]=='cp6_maintenance_admission','BRIDGE_BOOTSTRAP_ROLE_NOT_RESTORED')
            report['raw'].update(baseline_all22=baseline,installed_all22=installed,function_definition_body=raw[0],
                function_raw_ACL=raw[5],schema_raw_ACL=raw[6],raw_public_before=public_before)
            report['checks'].append(dict(id='DECLARED_PLATFORM_BOOTSTRAP_ADDS_ONLY_ONE_PRIVATE_SCHEMA_AND_EXACT_ZERO_ARGUMENT_FUNCTION',status='PASS'))
            conn.commit()
        # Authenticate as actual non-superuser postgres, not SET ROLE under an
        # administrator session. The definition elevates only the fixed lock.
        with psycopg.connect('postgresql://postgres:postgres@127.0.0.1:54322/'+NAME)as native,native.cursor()as cur:
            configure(cur)
            profile=cur.execute("select current_user,session_user,rolsuper,current_setting('server_version_num')::int from pg_roles where rolname=current_user").fetchone()
            require(profile==('postgres','postgres',False,170006),'BRIDGE_ACTUAL_SUPABASE17_NONSUPERUSER_SESSION_REQUIRED')
            catalogs=cur.execute('select cp7_global_catalog_fence.lock_v1()').fetchone()[0]
            held=cur.execute("select n.nspname,c.relname,l.mode,l.granted from pg_locks l join pg_class c on c.oid=l.relation join pg_namespace n on n.oid=c.relnamespace where l.pid=pg_backend_pid()and l.mode='ShareLock'and l.granted order by n.nspname collate \"C\",c.relname collate \"C\"").fetchall()
            require(len(catalogs)==64 and [[r[0],r[1]]for r in held]==[[r[0],r[1]]for r in catalogs]
                and all(r[0]=='pg_catalog'and r[2:] ==('ShareLock',True)for r in held),'BRIDGE_EXACT_ALL64_LOCKS_RETAINED_AFTER_CALL')
            require(cur.execute('select current_user,session_user').fetchone()==('postgres','postgres'),'BRIDGE_DEFINER_AUTHORITY_LEAKED_TO_CALLER')
            cur.execute("insert into cp7_catalog_bridge_model.effects values(1,'ordinary modeled DML under inherited catalog locks')")
            require(cur.execute('select count(*)from cp7_catalog_bridge_model.effects').fetchone()[0]==1,'BRIDGE_ORDINARY_DML_BLOCKED')
            report['raw'].update(actual_non_superuser_profile=list(profile),returned_catalogues=catalogs,actual_held_locks=[list(r)for r in held],actual_backend_pid=native.info.backend_pid)
            native.rollback()
            report['checks'].append(dict(id='ACTUAL_POSTGRES_CALL_RETURNS_TO_NON_SUPERUSER_WITH_ALL64_TRANSACTION_LOCKS_AND_ORDINARY_DML',status='PASS'))
        with psycopg.connect(uri,dbname=NAME)as conn,conn.cursor()as cur:
            configure(cur);denials=[]
            for role in('anon','authenticated','service_role'):
                require(cur.execute("select has_schema_privilege(%s,'cp7_global_catalog_fence','USAGE'),has_function_privilege(%s,%s,'EXECUTE')",(role,role,SIGNATURE)).fetchone()==(False,False),'BRIDGE_EXTERNAL_ROLE_AUTHORITY_EXPANDED:'+role)
                cur.execute('savepoint external_role_denial')
                cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
                error=None
                try:cur.execute('select cp7_global_catalog_fence.lock_v1()')
                except psycopg.Error as failed:error=dict(SQLSTATE=failed.sqlstate,error=failed.diag.message_primary)
                cur.execute('rollback to savepoint external_role_denial');cur.execute('release savepoint external_role_denial')
                require(error is not None and error['SQLSTATE']=='42501','BRIDGE_EXTERNAL_ROLE_CALL_NOT_REFUSED:'+role)
                denials.append(dict(role=role,**error))
            require(capture(cur,sql_queries)==installed,'BRIDGE_INVOCATION_OR_DENIAL_CHANGED_CATALOGS')
            require(cur.execute('select count(*)from cp7_catalog_bridge_model.effects').fetchone()[0]==0,'BRIDGE_MODELED_ROW_NOT_ROLLED_BACK')
            report['raw']['actual_external_role_denials']=denials
            report['checks'].append(dict(id='ANON_AUTHENTICATED_AND_SERVICE_HAVE_NO_SCHEMA_OR_FUNCTION_ACCESS_AND_ACTUAL_CALLS_REFUSE',status='PASS'))
            cur.execute((HERE/'INVERSE.sql').read_text(),prepare=False)
            final=capture(cur,sql_queries)
            require(final==baseline,'BRIDGE_EXACT_ALL22_NOT_RESTORED')
            require(cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]==public_before,'BRIDGE_PUBLIC_RAW_ACL_CHANGED')
            require(cur.execute('select current_user').fetchone()[0]=='cp6_maintenance_admission','BRIDGE_CLEANUP_ROLE_NOT_RESTORED')
            report['raw']['final_all22']=final;conn.commit()
            report['checks'].append(dict(id='EXPLICIT_NARROW_PLATFORM_REMOVAL_RESTORES_ALL22_RAW_PUBLIC_AND_ROLE_CONTEXT',status='PASS'))
        report['status']='ACTUAL_SUPABASE17_FIXED_PLATFORM_CATALOG_FENCE_FOCUSED4_PASS_NOT_GLOBAL_RUNTIME'
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error),SQLSTATE=getattr(error,'sqlstate',None))
        (OUT/'BRIDGE_FIRST_FAILURE.txt').write_text(traceback.format_exc());raise
    finally:
        try:
            if created:
                with psycopg.connect(uri,autocommit=True)as admin,admin.cursor()as cur:
                    require(cur.execute('select count(*)from pg_stat_activity where datname=%s',(NAME,)).fetchone()[0]==0,'BRIDGE_UNEXPECTED_BACKEND_REFUSE_FORCE_DROP')
                    cur.execute(sql.SQL('drop database {}').format(sql.Identifier(NAME)))
                    require(roles(cur)==roles_before,'BRIDGE_GLOBAL_ROLES_OR_MEMBERSHIPS_NOT_RESTORED')
                    report.update(capability_DB_removed=True,global_roles_and_memberships_restored=True)
        finally:
            (OUT/'PLATFORM_CATALOG_FENCE_FOCUSED4.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(dict(status=report['status'],completed_controls=len(report['checks']),actual_Native_cases=0)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();m=p.add_mutually_exclusive_group(required=True)
    m.add_argument('--check',action='store_true');m.add_argument('--run',action='store_true');m.add_argument('--start',action='store_true');a=p.parse_args()
    if a.check:print(json.dumps(source()))
    elif a.start:
        source();path=ROOT/'scripts/current-finance-combined-composition/disposable_start.py'
        spec=importlib.util.spec_from_file_location('bounded_existing_startup_no_business_calls',path)
        startup=importlib.util.module_from_spec(spec);spec.loader.exec_module(startup);startup.start(OUT/'disposable-startup-attempts')
    else:run()
