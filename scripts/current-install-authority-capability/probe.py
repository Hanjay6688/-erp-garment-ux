"""Only installation capabilities on the actual local Supabase PostgreSQL17.

ERP tables, Auth providers and private business entrypoints are explicit models.
No parent is admitted, financial suite run, invoice posted or release approved.
The six-hour policy of the original Afui financial workflow is unchanged.
"""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
from urllib.parse import urlparse
import argparse,importlib.util,json,os,subprocess,traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp7-proof'
ORIGINAL=ROOT/'scripts/cp7_accessory_nonpayable/function_acl_capability.py'
BRANCH='refs/heads/astra-a/install-authority-capability-20261102'
MANDOR_DB='cp7_mandor_facade_capability'
BEFORE='''    from cp7_accessory_nonpayable import admission,settings_stage,source
    admission.parent_receipt();source.preflight()'''
AFTER='''    from cp7_accessory_nonpayable import settings_stage
    capability_source_only()'''


def require(value,message):
    if not value:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def source():
    manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    require(manifest['classification']=='ISOLATED_ACTUAL_SUPABASE17_INSTALL_AUTHORITY_CAPABILITIES_NOT_ERP','CAPABILITY_EXACT_MODEL_SCOPE')
    for name,expected in manifest['files'].items():
        path=ROOT/name;require(path.is_file()and not path.is_symlink(),'CAPABILITY_REGULAR_PINNED_INPUT_REQUIRED')
        require(pin(path.read_bytes())==expected,'CAPABILITY_SOURCE_CHANGED:'+name)
    return dict(head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        tree=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD^{tree}'],text=True).strip(),
        manifest=pin((HERE/'SOURCE.json').read_bytes()),actual_ERP_cases=0,actual_Native_cases=0,
        complete_parent_or_financial_runtime_NOT_admitted=True,production_go=False,independent_acceptance=False)


def module():
    raw=ORIGINAL.read_bytes();text=raw.decode();require(text.count(BEFORE)==1,'CAPABILITY_ONE_DECLARED_MODEL_ENTRY_ROUTE')
    derived=text.replace(BEFORE,AFTER,1)
    require(derived.replace(AFTER,BEFORE,1).encode()==raw,'CAPABILITY_ENTIRE_ORIGINAL_RECOVERED')
    value=ModuleType('exact_local_supabase17_schema_capability_ONLY');value.__file__=str(ORIGINAL)
    value.__dict__['capability_source_only']=source
    exec(compile(derived,str(ORIGINAL)+':model-entry-only', 'exec'),value.__dict__)
    return value,dict(before=pin(raw),derived=pin(derived.encode()),exact_reversible_routes=1,
        only_parent_and_complete_product_admission_replaced_by_pinned_model_source_gate=True,
        original_fixed_local_DB_guard_SQL_catalogue_checks_and_cleanup_unchanged=True,
        financial_runtime_or_qualification_NOT_opened=True)


def maintenance_uri():
    uri=os.environ.get('CP6_ADMISSION_CONTROL_PGURL','');p=urlparse(uri)
    require(p.scheme in('postgres','postgresql')and p.hostname=='127.0.0.1'and p.port==54322
        and p.username=='cp6_maintenance_admission'and p.path=='/template1'and not p.query and not p.fragment,
        'CAPABILITY_ONLY_FIXED_LOCAL_MAINTENANCE_TEMPLATE1_ALLOWED')
    return uri


def mandor(cap):
    import psycopg
    from psycopg import sql
    uri=maintenance_uri();created=False;roles_before=None
    result=dict(status='INCOMPLETE',actual_Native_cases=0,models_not_business_functions=True)
    try:
        with psycopg.connect(uri,autocommit=True)as admin,admin.cursor()as cur:
            require(not cur.execute('select 1 from pg_database where datname=%s',(MANDOR_DB,)).fetchone(),'CAPABILITY_MANDOR_DB_ALREADY_EXISTS_REFUSE_TO_TOUCH')
            roles_before=cap.global_roles(cur)
            cur.execute(sql.SQL('create database {} owner postgres template template0').format(sql.Identifier(MANDOR_DB)));created=True
        with psycopg.connect(uri,dbname=MANDOR_DB)as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='20s';set local lock_timeout='2s'")
            for role in('cp7_sales_read','cp7_procure_read'):
                if not cur.execute('select 1 from pg_roles where rolname=%s',(role,)).fetchone():
                    cur.execute(sql.SQL('create role {} nologin noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls').format(sql.Identifier(role)))
            cur.execute('set session authorization postgres')
            identity=cur.execute("select current_user,session_user,rolsuper,rolcreaterole,current_setting('server_version_num')::int from pg_roles where rolname=current_user").fetchone()
            require(identity[:4]==('postgres','postgres',False,True)and 170000<=identity[4]<180000,'CAPABILITY_MANDOR_ACTUAL_NONSUPERUSER17_REQUIRED')
            cur.execute((HERE/'MANDOR_MODEL_BASE.sql').read_text(),prepare=False)
            reference=json.loads((HERE/'MANDOR_ACTUAL_CREATOR_ACL_REFERENCE.json').read_bytes())
            for grantee,grantor,privilege,option in reference['public_function_defaults']:
                require(grantor=='postgres'and privilege=='EXECUTE'and option is False,'CAPABILITY_EXACT_SAVED_FUNCTION_DEFAULT_REQUIRED')
                cur.execute(sql.SQL('alter default privileges for role postgres in schema public grant execute on functions to {}').format(sql.Identifier(grantee)))
            queries=cap.catalog_queries();before=cap.capture(cur,queries)
            raw_public=cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]
            cur.execute((HERE/'MANDOR_COMPOSED.sql').read_text(),prepare=False)
            expected=json.loads((HERE/'MANDOR_EXPECTED_BODIES.json').read_bytes())
            for signature,body in expected.items():
                row=cur.execute('select prosrc,pg_get_userbyid(proowner),prosecdef from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()
                require(row==(body['body'],'cp7_mandor_shop_api'if signature.startswith('public.')else'postgres',True),'CAPABILITY_MANDOR_EXACT_BODY_OWNER:'+signature)
                if signature.startswith('public.'):
                    for role in('anon','authenticated','service_role','cp7_procure_read','cp7_sales_read','cp7_mandor_shop_api'):
                        allowed=cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,signature)).fetchone()[0]
                        require(allowed==(role in('authenticated','cp7_mandor_shop_api')),'CAPABILITY_MANDOR_EXACT_EXECUTE:'+signature+':'+role)
            require(not cur.execute("select has_schema_privilege('cp7_mandor_shop_api','public','CREATE')").fetchone()[0],'CAPABILITY_MANDOR_TEMP_CREATE_NOT_REMOVED')
            require(not cur.execute("select 1 from pg_auth_members where roleid='cp7_mandor_shop_api'::regrole and(inherit_option or set_option)").fetchone(),'CAPABILITY_MANDOR_TEMP_SET_NOT_REMOVED')
            require(cap.capture(cur,queries)['default_privileges']==before['default_privileges'],'CAPABILITY_MANDOR_DEFAULTS_CHANGED')
            cur.execute((HERE/'MANDOR_INVERSE.sql').read_text(),prepare=False)
            require(cur.execute('select current_user,session_user').fetchone()==('postgres','postgres'),'CAPABILITY_MANDOR_INVERSE_CREATOR_CHANGED')
            require(cap.capture(cur,queries)==before,'CAPABILITY_MANDOR_PREUSE_ALL22_NOT_RESTORED')
            require(cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]==raw_public,'CAPABILITY_MANDOR_RAW_PUBLIC_NOT_RESTORED')
            conn.rollback()
            result.update(status='ACTUAL_SUPABASE17_MANDOR_NINE_FUNCTION_AUTHORITY_AND_PREUSE_ALL22_PASS_NOT_ERP',creator=list(identity),all_synthetic_DDL_rolled_back=True)
    finally:
        if created:
            with psycopg.connect(uri,autocommit=True)as admin,admin.cursor()as cur:
                require(cur.execute('select count(*)from pg_stat_activity where datname=%s',(MANDOR_DB,)).fetchone()[0]==0,'CAPABILITY_MANDOR_UNEXPECTED_BACKEND_REFUSE_FORCE_DROP')
                cur.execute(sql.SQL('drop database {}').format(sql.Identifier(MANDOR_DB)))
                require(cap.global_roles(cur)==roles_before,'CAPABILITY_MANDOR_GLOBAL_ROLES_NOT_RESTORED')
                result.update(capability_DB_removed=True,global_roles_and_memberships_restored=True)
    return result


def catalog_authority():
    """Observe actual creator ability; unsupported means runtime remains closed."""
    import psycopg
    from psycopg import sql
    result=dict(status='INCOMPLETE',actual_Native_cases=0,global_runtime_installed=False,global_writer_closure=False)
    with psycopg.connect('postgresql://postgres:postgres@127.0.0.1:54322/postgres')as conn,conn.cursor()as cur:
        identity=cur.execute("select current_user,session_user,rolsuper,current_setting('server_version_num')::int from pg_roles where rolname=current_user").fetchone()
        require(identity[:3]==('postgres','postgres',False)and 170000<=identity[3]<180000,'CAPABILITY_CATALOG_EXACT_NONSUPERUSER17_REQUIRED')
        rows=cur.execute("select c.oid,n.nspname,c.relname,pg_get_userbyid(c.relowner),c.relacl::text,has_table_privilege(current_user,c.oid,'MAINTAIN,UPDATE,DELETE,TRUNCATE')from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='pg_catalog'and c.relkind in('r','p')order by c.relname collate \"C\"").fetchall()
        result.update(creator=list(identity),catalogue_rows=[list(r)for r in rows],catalogue_count=len(rows))
        cur.execute("set local lock_timeout='2s';set local statement_timeout='20s'")
        try:
            cur.execute(sql.SQL('lock table {} in share mode nowait').format(sql.SQL(',').join(sql.Identifier(r[1],r[2])for r in rows)))
            held=cur.execute("select c.relname from pg_locks l join pg_class c on c.oid=l.relation join pg_namespace n on n.oid=c.relnamespace where n.nspname='pg_catalog'and l.pid=pg_backend_pid()and l.mode='ShareLock'and l.granted order by c.relname collate \"C\"").fetchall()
            require([r[0]for r in held]==[r[2]for r in rows],'CAPABILITY_CATALOG_EXACT_ALL_LOCKS_NOT_OBSERVED')
            result.update(status='ACTUAL_SUPABASE17_NONSUPERUSER_ALL_CATALOG_SHARE_CAPABILITY_OBSERVED_NOT_GLOBAL_CLOSURE',all_catalogue_SHARE_locks_observed=True)
        except psycopg.Error as error:
            require(error.sqlstate in('42501','55P03'),'CAPABILITY_UNEXPECTED_CATALOG_SQLSTATE:'+str(error.sqlstate))
            result.update(status='ACTUAL_SUPABASE17_CATALOG_CAPABILITY_UNAVAILABLE_RUNTIME_MUST_REMAIN_CLOSED',SQLSTATE=error.sqlstate,error=error.diag.message_primary,all_catalogue_SHARE_locks_observed=False)
        conn.rollback();result['transaction_rolled_back']=True
    return result


def run():
    identity=source();require(os.environ.get('GITHUB_REF')==BRANCH,'CAPABILITY_ONE_DECLARED_ISOLATED_BRANCH_REQUIRED')
    require(os.environ.get('CAPABILITY_CONFIRM')=='cp7_install_authority_only','CAPABILITY_EXPLICIT_MODEL_CONFIRMATION_REQUIRED')
    maintenance_uri();cap,derivation=module();OUT.mkdir(parents=True,exist_ok=True)
    report=dict(status='INCOMPLETE',source=identity,entry_derivation=derivation,results={},
        synthetic_schema_Auth_and_private_entrypoints=True,old_business_API_financial_and_browser_cases_NOT_rerun=True,
        six_hour_original_financial_workflow_policy_unchanged=True,actual_ERP_cases=0,actual_Native_cases=0,
        actual_Auth_HTTP_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)
    retained=json.loads((HERE/'RETAINED_MANDOR_AND_CATALOG_OBSERVATIONS.json').read_bytes())
    require(retained['retained_completed_observations_NOT_rerun']is True and retained['original_failed_run_NOT_relabelled_PASS']is True,'CAPABILITY_EXACT_RETAINED_FIRST_RESULT_REQUIRED')
    require(retained['run_id']==41437248634 and retained['job_id']==125250039172,'CAPABILITY_ONLY_EXACT_FIRST_OWNING_OBSERVATIONS')
    require(retained['results']['MANDOR']['status']=='ACTUAL_SUPABASE17_MANDOR_NINE_FUNCTION_AUTHORITY_AND_PREUSE_ALL22_PASS_NOT_ERP','CAPABILITY_RETAINED_MANDOR_FIRST_PASS_REQUIRED')
    require(retained['results']['GLOBAL_CATALOG_AUTHORITY']['SQLSTATE']=='42501','CAPABILITY_RETAINED_UNSUPPORTED_CATALOG_MUST_NOT_BECOME_PASS')
    report['retained_observations']=retained
    report['retained_Mandor_and_Global_NOT_rerun']=True
    report['all_three_fresh_one_attempt']=False
    failures=[]
    for name,call in(('AFUI',cap.run),):
        try:report['results'][name]=call()
        except BaseException as error:
            report['results'][name]=dict(status='FAILED_CAPABILITY_NOT_ERP',error_type=type(error).__name__,error=str(error),SQLSTATE=getattr(error,'sqlstate',None))
            failures.append(name);(OUT/(name+'_FIRST_FAILURE.txt')).write_text(traceback.format_exc())
        finally:
            (OUT/'INSTALL_AUTHORITY_CAPABILITIES.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(dict(capability=name,status=report['results'][name]['status'],actual_Native_cases=0)),flush=True)
    report.update(status='ACTUAL_SUPABASE17_SCHEMA_CAPABILITIES_REPORTED_NOT_ERP'if not failures else'INCOMPLETE',failed_capabilities=failures,
        all_runtime_capabilities_available=False,global_catalog_capability_unsupported=True)
    (OUT/'INSTALL_AUTHORITY_CAPABILITIES.json').write_text(json.dumps(report,indent=2)+'\n')
    require(not failures,'CAPABILITY_FIRST_FAILURES_PRESERVED:'+','.join(failures))


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    parser=argparse.ArgumentParser();modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check',action='store_true');modes.add_argument('--run',action='store_true');modes.add_argument('--start',action='store_true');args=parser.parse_args()
    if args.check:print(json.dumps(source()))
    elif args.start:
        source();p=ROOT/'scripts/current-finance-combined-composition/disposable_start.py'
        spec=importlib.util.spec_from_file_location('existing_bounded_disposable_image_startup_ONLY',p)
        startup=importlib.util.module_from_spec(spec);spec.loader.exec_module(startup)
        startup.start(OUT/'disposable-startup-attempts')
    else:run()
