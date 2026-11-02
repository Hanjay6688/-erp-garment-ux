"""Only new sealed-profile relation capability controls, actual Supabase17.

Existing catalog-fence, primitive, Afui, Mandor and business tests are retained,
not rerun. Existing fixed catalog-helper source is setup for the new composition.
Every application table and the sealed profile in this probe is explicitly a
MODEL. This is not installation on an accepted ERP parent or financial evidence.
"""
from pathlib import Path
from hashlib import sha256
import argparse,importlib.util,json,os,re,subprocess,traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp7-proof'
NAME='cp7_relation_bridge_capability'
MODEL_OWNER='cp7_relation_model_owner'
BRANCH='refs/heads/astra-a/global-relation-bridge-capability-20261102'
SIGNATURE='cp7_global_catalog_fence.lock_relations_v1(text)'
BASE_SIGNATURE='cp7_global_catalog_fence.lock_v1()'
PROFILE='a'*64

# Import inert utilities only. None of the earlier source check/run/start paths
# is called; the original test source and evidence remain unchanged.
spec=importlib.util.spec_from_file_location('retained_catalog_probe_utilities',
    ROOT/'scripts/current-global-catalog-bridge-capability/probe.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
require,pin=base.require,base.pin
capture,queries,roles,configure,fixed_uri=base.capture,base.queries,base.roles,base.configure,base.fixed_uri


def source():
    manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    require(manifest['classification']=='SEALED_PROFILE_RELATION_FENCE_ACTUAL17_MODEL_CAPABILITY_ONLY',
        'RELATION_CAPABILITY_ONLY_SCOPE_REQUIRED')
    expected={str((HERE/n).relative_to(ROOT))for n in
        ('probe.py','BASE_FENCE.sql','RELATION_FENCE.sql','PROFILE_SCHEMA.sql','INVERSE.sql','SOURCE_PROOF.json','RETAINED_FIRST_CONTROL.json')}
    expected|={'.github/workflows/cp7-global-relation-bridge-capability.yml',
        'scripts/current-global-catalog-bridge-capability/probe.py',
        'scripts/cp7_ow04_restore_bundle.py','scripts/current-finance-combined-composition/disposable_start.py'}
    require(set(manifest['files'])==expected,'RELATION_EXACT_ELEVEN_SOURCE_INPUTS_REQUIRED')
    for name,value in manifest['files'].items():
        p=ROOT/name
        require(p.is_file()and not p.is_symlink()and pin(p.read_bytes())==value,'RELATION_SOURCE_CHANGED:'+name)
    proof=json.loads((HERE/'SOURCE_PROOF.json').read_bytes())
    require(proof['new_relation_source']==pin((HERE/'RELATION_FENCE.sql').read_bytes())
        and proof['retained_catalog_source']==pin((HERE/'BASE_FENCE.sql').read_bytes())
        and proof['actual_profile_schema']==pin((HERE/'PROFILE_SCHEMA.sql').read_bytes()),'RELATION_EXACT_PREPARED_SQL_REQUIRED')
    retained=json.loads((HERE/'RETAINED_FIRST_CONTROL.json').read_bytes())
    require(retained['head']=='358626fcc7be18041bda524d7f978b18129d1367'and retained['retained_controls']==1
        and retained['first_attempt_remains_failure']is True,'RELATION_EXACT_FIRST_CONTROL_RETENTION_REQUIRED')
    return dict(head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        tree=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD^{tree}'],text=True).strip(),
        source_pins=11,manifest=pin((HERE/'SOURCE.json').read_bytes()),all_profile_and_application_data_are_models=True,
        old_completed_controls_NOT_rerun=True,actual_Native_cases=0,production_go=False,independent_acceptance=False)


def relation_metadata(cur):
    return cur.execute("""select jsonb_agg(jsonb_build_array(n.nspname,c.relname,c.relkind::text,c.relpersistence::text,
      pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,
      case when c.relacl is null then null else to_jsonb(array(select a::text from unnest(c.relacl)a order by a::text collate "C"))end)
      order by n.nspname collate "C",c.relname collate "C")
      from pg_class c join pg_namespace n on n.oid=c.relnamespace
      where n.nspname='cp7_relation_modeldata'and c.relkind='r'""").fetchone()[0]


def catalog_metadata(cur):
    return cur.execute("""select jsonb_agg(jsonb_build_array(n.nspname,c.relname,c.relkind::text,c.relpersistence::text,
      pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,
      case when c.relacl is null then null else to_jsonb(array(select a::text from unnest(c.relacl)a order by a::text collate "C"))end)
      order by n.nspname collate "C",c.relname collate "C")
      from pg_class c join pg_namespace n on n.oid=c.relnamespace
      where n.nspname='pg_catalog'and c.relkind in('r','p')""").fetchone()[0]


def insert_model_profile(cur,profile,relations,catalogs):
    from psycopg.types.json import Jsonb
    cur.execute("""insert into cp7_global_nonpo_envelope.profiles
      (id,parent_head,parent_tree,actual_parent_root_receipt,expected_catalogs,expected_relations,native_authority_sha256)
      values(%s,%s,%s,%s,%s,%s,%s)""",
      (profile,'b'*40,'c'*40,Jsonb({'MODEL_ONLY':True,'accepted_ERP_parent':False}),Jsonb(catalogs),Jsonb(relations),'d'*64))


def error_at_savepoint(cur,statement,params=None):
    import psycopg
    cur.execute('savepoint expected_refusal')
    error=None
    try:cur.execute(statement,params)
    except psycopg.Error as failed:error=dict(SQLSTATE=failed.sqlstate,error=failed.diag.message_primary)
    cur.execute('rollback to savepoint expected_refusal');cur.execute('release savepoint expected_refusal')
    require(error is not None,'RELATION_EXPECTED_REFUSAL_DID_NOT_OCCUR')
    return error


def run():
    identity=source()
    require(os.environ.get('GITHUB_REF')==BRANCH,'RELATION_ONE_ISOLATED_BRANCH_REQUIRED')
    require(os.environ.get('CAPABILITY_CONFIRM')=='cp7_global_relation_bridge_only','RELATION_EXPLICIT_ISOLATED_CONFIRMATION')
    import psycopg
    from psycopg import sql
    uri=fixed_uri();all_queries=queries();created=False;model_role_created=False;roles_before=None
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(status='INCOMPLETE',source=identity,checks=[],raw={},
        retained_control_families=1,retained_first_control=json.loads((HERE/'RETAINED_FIRST_CONTROL.json').read_bytes()),
        first_attempt_remains_failure=True,all_four_are_NOT_fresh_in_one_attempt=True,
        model_profile_is_NOT_accepted_final_ERP_parent=True,all_42_application_tables_are_models=True,
        old_completed_catalog_Afui_Mandor_primitive_controls_NOT_rerun=True,
        actual_global_installer_or_parent_adoption=False,global_writer_or_permission_or_phantom_closure=False,
        actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
        production_go=False,independent_acceptance=False)
    try:
        with psycopg.connect(uri,autocommit=True)as admin,admin.cursor()as cur:
            require(not cur.execute('select 1 from pg_database where datname=%s',(NAME,)).fetchone(),
                'RELATION_CAPABILITY_DB_EXISTS_REFUSE_TO_TOUCH')
            require(not cur.execute('select 1 from pg_roles where rolname=%s',(MODEL_OWNER,)).fetchone(),
                'RELATION_MODEL_ROLE_EXISTS_REFUSE_TO_TOUCH')
            roles_before=roles(cur)
            cur.execute(sql.SQL('create role {} nologin nosuperuser noinherit nocreatedb nocreaterole noreplication').format(sql.Identifier(MODEL_OWNER)))
            model_role_created=True
            cur.execute(sql.SQL('create database {} owner postgres template template0').format(sql.Identifier(NAME)));created=True
        with psycopg.connect(uri,dbname=NAME)as conn,conn.cursor()as cur:
            configure(cur)
            cur.execute(sql.SQL('create schema cp7_relation_modeldata authorization {}').format(sql.Identifier(MODEL_OWNER)))
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(MODEL_OWNER)))
            for i in range(42):
                target=sql.Identifier('cp7_relation_modeldata',f't_{i:03}')
                cur.execute(sql.SQL('create table {}(id int primary key,value text)').format(target))
                cur.execute(sql.SQL('revoke all on table {} from public,anon,authenticated,service_role,postgres').format(target))
            cur.execute("""create function cp7_relation_modeldata.owner_write_v1()returns int
              language plpgsql volatile security definer set search_path=''as $$
              begin insert into cp7_relation_modeldata.t_000 values(1,'MODEL owner writer under delegated lock');return 1;end $$;
              revoke all on function cp7_relation_modeldata.owner_write_v1()from public,anon,authenticated,service_role;
              grant usage on schema cp7_relation_modeldata to postgres;
              grant execute on function cp7_relation_modeldata.owner_write_v1()to postgres;reset role;""",prepare=False)
            cur.execute('set local role postgres');cur.execute((HERE/'PROFILE_SCHEMA.sql').read_text(),prepare=False)
            cur.execute('reset role');cur.execute((HERE/'BASE_FENCE.sql').read_text(),prepare=False)
            targets=relation_metadata(cur);catalogs=catalog_metadata(cur)
            require(len(targets)==42 and all(r[4]==MODEL_OWNER for r in targets),'RELATION_EXACT_42_OTHER_OWNER_TARGETS_REQUIRED')
            cur.execute('set local role postgres');insert_model_profile(cur,PROFILE,targets,catalogs);cur.execute('reset role')
            conn.commit()
            configure(cur);baseline=capture(cur,all_queries)
            public_before=cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]
            base_function_before=cur.execute('select pg_get_functiondef(%s::regprocedure)',(BASE_SIGNATURE,)).fetchone()[0]
            cur.execute((HERE/'RELATION_FENCE.sql').read_text(),prepare=False)
            installed=capture(cur,all_queries)
            report['raw'].update(baseline_all22=baseline,installed_all22=installed,
                raw_public_before=public_before,actual_model_targets=targets,retained_catalog_function_before=base_function_before)
            conn.commit()
            # Installation/ACL control is retained from the first canonical
            # attempt. This successor runs only remaining control families 2-4.

        native_uri='postgresql://postgres:postgres@127.0.0.1:54322/'+NAME
        with psycopg.connect(native_uri)as native,native.cursor()as cur:
            configure(cur)
            profile=cur.execute("select current_user,session_user,rolsuper,current_setting('server_version_num')::int from pg_roles where rolname=current_user").fetchone()
            require(profile==('postgres','postgres',False,170006),'RELATION_ACTUAL_NONSUPERUSER_SUPABASE17_SESSION_REQUIRED')
            direct_lock=error_at_savepoint(cur,'lock table cp7_relation_modeldata.t_000 in exclusive mode nowait')
            require(direct_lock['SQLSTATE']=='42501','RELATION_CALLER_ALREADY_HAS_DIRECT_LOCK_AUTHORITY')
            native.rollback();configure(cur)
            cur.execute('select cp7_global_catalog_fence.lock_v1()')
            actual=cur.execute('select cp7_global_catalog_fence.lock_relations_v1(%s)',(PROFILE,)).fetchone()[0]
            require(actual==targets,'RELATION_RETURNED_FRESH_ACTUAL_PROFILE_DIFFERENT')
            held=cur.execute("""select n.nspname,c.relname,l.mode,l.granted from pg_locks l
              join pg_class c on c.oid=l.relation join pg_namespace n on n.oid=c.relnamespace
              where l.pid=pg_backend_pid()and l.mode='ExclusiveLock'and l.granted
              and n.nspname in('cp7_relation_modeldata','cp7_global_nonpo_envelope')
              order by n.nspname collate "C",c.relname collate "C"
              """
            ).fetchall()
            expected_locks=[['cp7_global_nonpo_envelope','profiles','ExclusiveLock',True]]+[r[:2]+['ExclusiveLock',True]for r in targets]
            require([list(r)for r in held]==expected_locks,'RELATION_EXACT_43_TRANSACTION_LOCKS_NOT_RETAINED')
            require(cur.execute('select current_user,session_user').fetchone()==('postgres','postgres'),'RELATION_DEFINER_ROLE_LEAKED')
            direct_dml=error_at_savepoint(cur,"insert into cp7_relation_modeldata.t_001 values(1,'FORBIDDEN')")
            require(direct_dml['SQLSTATE']=='42501','RELATION_DELEGATION_EXPANDED_DIRECT_DML')
            require(cur.execute('select cp7_relation_modeldata.owner_write_v1()').fetchone()[0]==1,'RELATION_MODELED_OWNER_WRITER_BLOCKED')
            report['raw'].update(actual_non_superuser_profile=list(profile),direct_lock_denial=direct_lock,direct_DML_denial=direct_dml,
                actual_returned_relations=actual,actual_held_application_locks=[list(r)for r in held],actual_backend_pid=native.info.backend_pid)
            native.rollback()
            report['checks'].append(dict(id='ACTUAL_NON_SUPERUSER_RETAINS_43_DECLARED_LOCKS_AND_CALLS_OWNER_WRITER_WITHOUT_DIRECT_DML',status='PASS'))

            # These refusal cases exercise this new profile-bound function only.
            # No earlier catalog fence or general lock primitive test is repeated.
            refusals=[];configure(cur)
            missing=error_at_savepoint(cur,'select cp7_global_catalog_fence.lock_relations_v1(%s)',(PROFILE,))
            require(missing['error']=='CP7_GLOBAL_COMPLETE_CATALOG_FENCE_REQUIRED_FIRST','RELATION_MISSING_FENCE_NOT_REFUSED')
            refusals.append(dict(case='missing_catalog_fence',**missing));native.rollback();configure(cur)
            with psycopg.connect(uri,dbname=NAME)as other,other.cursor()as rival:
                rival.execute('select pg_current_xact_id()')
                cur.execute('select cp7_global_catalog_fence.lock_v1()')
                old_xid=error_at_savepoint(cur,'select cp7_global_catalog_fence.lock_relations_v1(%s)',(PROFILE,))
                require(old_xid['SQLSTATE']=='55P03'and old_xid['error']=='CP7_GLOBAL_PREEXISTING_TRANSACTION_REVIEW_AGAIN',
                    'RELATION_PREEXISTING_XID_NOT_REFUSED')
                refusals.append(dict(case='preexisting_permanent_XID',**old_xid));native.rollback();other.rollback()
            configure(cur)
            cur.execute('select cp7_global_catalog_fence.lock_v1()')
            wrong=error_at_savepoint(cur,'select cp7_global_catalog_fence.lock_relations_v1(%s)',('e'*64,))
            require(wrong['error']=='CP7_GLOBAL_COMPLETE_EXACT_RELATION_PROFILE_REQUIRED','RELATION_WRONG_PROFILE_NOT_REFUSED')
            refusals.append(dict(case='wrong_profile',**wrong));native.rollback();configure(cur)
            insert_model_profile(cur,'f'*64,targets,catalogs)
            cur.execute('select cp7_global_catalog_fence.lock_v1()')
            duplicate=error_at_savepoint(cur,'select cp7_global_catalog_fence.lock_relations_v1(%s)',(PROFILE,))
            require(duplicate['error']=='CP7_GLOBAL_ONE_ACTUAL_FINAL_PARENT_PROFILE_REQUIRED','RELATION_SECOND_PROFILE_NOT_REFUSED')
            refusals.append(dict(case='second_profile',**duplicate));native.rollback()

            # Change a real fixture ACL, commit it, then require a fresh-metadata
            # refusal. Explicit baseline ACLs permit byte-exact reversal.
            with psycopg.connect(uri,dbname=NAME)as fixture,fixture.cursor()as f:
                f.execute('grant select on cp7_relation_modeldata.t_001 to anon');fixture.commit()
            configure(cur);cur.execute('select cp7_global_catalog_fence.lock_v1()')
            changed=error_at_savepoint(cur,'select cp7_global_catalog_fence.lock_relations_v1(%s)',(PROFILE,))
            require(changed['error']=='CP7_GLOBAL_RELATION_IDENTITY_OR_AUTHORITY_CHANGED','RELATION_STALE_ACL_NOT_REFUSED')
            refusals.append(dict(case='changed_target_ACL',**changed));native.rollback()
            with psycopg.connect(uri,dbname=NAME)as fixture,fixture.cursor()as f:
                f.execute('revoke select on cp7_relation_modeldata.t_001 from anon');fixture.commit()

            configure(cur);cur.execute('select cp7_global_catalog_fence.lock_v1()')
            cur.execute('select cp7_global_catalog_fence.lock_relations_v1(%s)',(PROFILE,))
            with psycopg.connect(uri,dbname=NAME)as other,other.cursor()as rival:
                rival.execute("set local lock_timeout='150ms';set local statement_timeout='2s'")
                contention=error_at_savepoint(rival,'select cp7_relation_modeldata.owner_write_v1()')
                require(contention['SQLSTATE']=='55P03','RELATION_OTHER_OWNER_WRITER_WAS_NOT_BLOCKED')
                other.rollback()
            refusals.append(dict(case='other_backend_owner_writer',**contention));native.rollback()
            report['raw']['new_relation_refusals']=refusals
            report['checks'].append(dict(id='PROFILE_FENCE_DUPLICATE_CHANGED_AUTHORITY_AND_SECOND_BACKEND_REFUSALS',status='PASS'))
        with psycopg.connect(uri,dbname=NAME)as conn,conn.cursor()as cur:
            configure(cur)
            denials=[]
            for role in('anon','authenticated','service_role'):
                require(cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(role,SIGNATURE)).fetchone()==(False,),
                    'RELATION_EXTERNAL_ROLE_EXECUTE_EXPANDED:'+role)
                cur.execute('savepoint denied_external_role')
                cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
                denial=error_at_savepoint(cur,'select cp7_global_catalog_fence.lock_relations_v1(%s)',(PROFILE,))
                cur.execute('rollback to savepoint denied_external_role');cur.execute('release savepoint denied_external_role')
                require(denial['SQLSTATE']=='42501','RELATION_EXTERNAL_CALL_NOT_REFUSED:'+role)
                denials.append(dict(role=role,**denial))
            report['raw']['actual_new_function_external_role_denials']=denials
            require(capture(cur,all_queries)==installed,'RELATION_CALLS_CHANGED_INSTALLED_CATALOGS')
            require(cur.execute('select count(*)from cp7_relation_modeldata.t_000').fetchone()[0]==0,'RELATION_MODELED_WRITE_NOT_ROLLED_BACK')
            cur.execute((HERE/'INVERSE.sql').read_text(),prepare=False)
            final=capture(cur,all_queries)
            require(final==baseline,'RELATION_ALL22_NOT_EXACTLY_RESTORED')
            require(cur.execute('select pg_get_functiondef(%s::regprocedure)',(BASE_SIGNATURE,)).fetchone()[0]==base_function_before,
                'RELATION_RETAINED_CATALOG_HELPER_CHANGED')
            require(cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]==public_before,'RELATION_RAW_PUBLIC_ACL_CHANGED')
            require(cur.execute('select current_user').fetchone()[0]=='cp6_maintenance_admission','RELATION_CLEANUP_ROLE_NOT_RESET')
            report['raw']['final_all22']=final;conn.commit()
            report['checks'].append(dict(id='DROP_ONLY_NEW_FUNCTION_RESTORES_ALL22_PUBLIC_AND_RETAINED_CATALOG_HELPER',status='PASS'))
        report['status']='ACTUAL_SUPABASE17_SEALED_PROFILE_RELATION_FENCE_RETAIN1_FRESH3_PASS_NOT_GLOBAL_RUNTIME'
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error),SQLSTATE=getattr(error,'sqlstate',None))
        (OUT/'RELATION_BRIDGE_FIRST_FAILURE.txt').write_text(traceback.format_exc());raise
    finally:
        try:
            if created:
                with psycopg.connect(uri,autocommit=True)as admin,admin.cursor()as cur:
                    require(cur.execute('select count(*)from pg_stat_activity where datname=%s',(NAME,)).fetchone()[0]==0,
                        'RELATION_UNEXPECTED_BACKEND_REFUSE_FORCE_DROP')
                    cur.execute(sql.SQL('drop database {}').format(sql.Identifier(NAME)));report['capability_DB_removed']=True
            if model_role_created:
                with psycopg.connect(uri,autocommit=True)as admin,admin.cursor()as cur:
                    cur.execute(sql.SQL('drop role {}').format(sql.Identifier(MODEL_OWNER)))
                    require(roles(cur)==roles_before,'RELATION_GLOBAL_ROLES_OR_MEMBERSHIPS_NOT_RESTORED')
                    report['global_roles_and_memberships_restored']=True
        finally:
            (OUT/'PLATFORM_RELATION_FENCE_NEW4.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(dict(status=report['status'],fresh_completed_controls=len(report['checks']),retained_controls=1,actual_Native_cases=0)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();m=p.add_mutually_exclusive_group(required=True)
    m.add_argument('--check',action='store_true');m.add_argument('--run',action='store_true');m.add_argument('--start',action='store_true');a=p.parse_args()
    if a.check:print(json.dumps(source()))
    elif a.start:
        source();path=ROOT/'scripts/current-finance-combined-composition/disposable_start.py'
        spec=importlib.util.spec_from_file_location('retained_bounded_disposable_startup',path)
        startup=importlib.util.module_from_spec(spec);spec.loader.exec_module(startup);startup.start(OUT/'disposable-startup-attempts')
    else:run()
