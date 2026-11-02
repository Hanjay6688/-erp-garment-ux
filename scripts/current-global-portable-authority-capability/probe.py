"""Three new portable-authority controls; MODELED metadata, no ERP business.

The only product SQL executed is the new pure metadata projection. Nineteen
functions, four helper identities and one view are explicitly modeled. Old
catalogue, lock, Native financial, Auth and browser controls are not rerun.
"""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,os,subprocess,traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp7-proof'
NAME='cp7_portable_authority_capability'
BRANCH='refs/heads/astra-a/global-portable-authority-capability-20261102'
SIG='cp7_global_nonpo_envelope.semantic_authority_v1(jsonb)'
SPEC=importlib.util.spec_from_file_location('retained_inert_capability_utilities',ROOT/'scripts/current-global-catalog-bridge-capability/probe.py')
base=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(base)
require,pin=base.require,base.pin
EXCLUDED=('session_user','current_user','runtime_entry','required_final_parent','actual_Native_qualification_credit','production_go')


def source():
    m=json.loads((HERE/'SOURCE.json').read_bytes())
    require(m['classification']=='PURE_PORTABLE_AUTHORITY_ACTUAL17_MODELED_METADATA_ONLY','PORTABLE_MODEL_ONLY_SCOPE')
    expected={str((HERE/n).relative_to(ROOT))for n in('probe.py','SEMANTIC.sql','PRODUCT_SOURCE_PROOF.json')}
    expected|={'.github/workflows/cp7-global-portable-authority-capability.yml',
        'scripts/current-global-catalog-bridge-capability/probe.py','scripts/cp7_ow04_restore_bundle.py',
        'scripts/current-finance-combined-composition/disposable_start.py'}
    require(set(m['files'])==expected,'PORTABLE_EXACT_SEVEN_INPUTS')
    for name,value in m['files'].items():require(pin((ROOT/name).read_bytes())==value,'PORTABLE_SOURCE_CHANGED:'+name)
    require(json.loads((HERE/'PRODUCT_SOURCE_PROOF.json').read_bytes())['semantic_helper']==pin((HERE/'SEMANTIC.sql').read_bytes()),'PORTABLE_EXACT_PRODUCT_SQL')
    return dict(head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        tree=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD^{tree}'],text=True).strip(),source_pins=7,
        modeled_functions=19,modeled_private_helpers=4,modeled_views=1,actual_Native_cases=0)


def function_sql(name,value=1):
    return 'create function cp7_portable_model.'+name+"()returns int language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$select "+str(value)+'$$;'


def independent(value):
    result=copy.deepcopy(value)
    for name in EXCLUDED:result.pop(name,None)
    for field in('functions','new_private_functions'):
        for row in result[field]:del row['oid']
    del result['view']['oid']
    return result


def project(cur,value):
    from psycopg.types.json import Jsonb
    row=cur.execute('select '+SIG.split('(')[0]+'(%s::jsonb)',(Jsonb(value),)).fetchone()[0]
    expected=independent(value);require(row==expected,'PORTABLE_PURE_PROJECTION_DIFFERS_FROM_INDEPENDENT_ALL_FIELDS')
    preimage=cur.execute('select %s::jsonb::text',(Jsonb(row),)).fetchone()[0]
    return dict(projected=row,canonical_DB_jsonb_preimage=preimage,sha256=hashlib.sha256(preimage.encode()).hexdigest())


def observe(cur,queries):
    catalogue=base.capture(cur,queries)
    functions=[];private=[]
    for i in range(23):
        name=('fn_'if i<19 else'helper_')+str(i if i<19 else i-19).zfill(2)
        sig='cp7_portable_model.'+name+'()'
        raw=cur.execute('select p.oid::bigint,p.proacl::text,pg_get_userbyid(p.proowner),p.proconfig,p.provolatile::text,p.prosecdef from pg_proc p where p.oid=%s::regprocedure',(sig,)).fetchone()
        row=dict(signature=sig,oid=raw[0],raw_acl=raw[1],owner=raw[2],proconfig=raw[3],volatility=raw[4],security_definer=raw[5])
        if i<19:row.update(actual_catalog_row=catalogue['functions'][sig],exact_known_source=True,exact_captured_profile=True);functions.append(row)
        else:private.append(row)
    view=cur.execute("select c.oid::bigint,c.relacl::text,pg_get_userbyid(c.relowner),pg_get_viewdef(c.oid,false)from pg_class c where c.oid='cp7_portable_model.model_view'::regclass").fetchone()
    return dict(known_function_count=19,known_functions_exact=True,functions=functions,new_private_functions=private,
        new_private_acl_closed=True,view=dict(oid=view[0],raw_acl=view[1],owner=view[2],definition=view[3],
            actual_catalog_row=catalogue['relations']['cp7_portable_model.model_view'],exact_known_source=True),
        session_user='postgres',current_user='postgres',runtime_entry=None,required_final_parent=None,
        actual_Native_qualification_credit=0,production_go=False,
        sentinel_nested_identity=dict(oid=42,business_reference='MUST_REMAIN_EXACT'))


def run():
    identity=source();require(os.environ.get('GITHUB_REF')==BRANCH,'PORTABLE_ONE_ISOLATED_BRANCH')
    require(os.environ.get('CAPABILITY_CONFIRM')=='cp7_global_portable_authority_only','PORTABLE_EXPLICIT_MODEL_CONFIRMATION')
    import psycopg
    from psycopg import sql
    from psycopg.types.json import Jsonb
    uri=base.fixed_uri();queries=base.queries();created=False;roles_before=None
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(status='INCOMPLETE',source=identity,checks=[],raw={},all_application_objects_are_models=True,
        actual_product_SQL_is_pure_semantic_helper_only=True,actual_parent_gate_NEVER_opened=True,
        old_completed_controls_NOT_rerun=True,global_writer_or_permission_or_phantom_closure=False,
        actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)
    try:
        with psycopg.connect(uri,autocommit=True)as conn,conn.cursor()as cur:
            require(not cur.execute('select 1 from pg_database where datname=%s',(NAME,)).fetchone(),'PORTABLE_EXISTING_DATABASE_REFUSED')
            roles_before=base.roles(cur);cur.execute(sql.SQL('create database {} owner postgres template template0').format(sql.Identifier(NAME)));created=True
        with psycopg.connect('postgresql://postgres:postgres@127.0.0.1:54322/'+NAME)as conn,conn.cursor()as cur:
            base.configure(cur)
            session=cur.execute("select current_user,session_user,rolsuper,current_setting('server_version_num')::int from pg_roles where rolname=current_user").fetchone()
            require(session==('postgres','postgres',False,170006),'PORTABLE_ACTUAL_NONSUPERUSER_SESSION')
            cur.execute('create schema cp7_global_nonpo_envelope authorization postgres;revoke all on schema cp7_global_nonpo_envelope from public,anon,authenticated,service_role;create schema cp7_portable_model authorization postgres;',prepare=False)
            for i in range(23):
                name=('fn_'if i<19 else'helper_')+str(i if i<19 else i-19).zfill(2)
                cur.execute(function_sql(name),prepare=False)
                cur.execute('revoke all on function cp7_portable_model.'+name+'()from public,anon,authenticated,service_role')
            cur.execute('create view cp7_portable_model.model_view with(security_invoker=true)as select 1 as value')
            before=base.capture(cur,queries);cur.execute((HERE/'SEMANTIC.sql').read_text(),prepare=False)
            installed=base.capture(cur,queries)
            for group,rows in before.items():
                require(set(installed[group])-set(rows)==({SIG}if group=='functions'else set()),'PORTABLE_ONLY_ONE_DECLARED_NEW_FUNCTION:'+group)
                require(all(installed[group].get(k)==v for k,v in rows.items()),'PORTABLE_EXISTING_CATALOG_CHANGED:'+group)
            fn=installed['functions'][SIG]
            require(fn[1:10]==['postgres','plpgsql','f',False,False,False,False,'i','u']and fn[18]==[['postgres','postgres','EXECUTE',False]],'PORTABLE_PRIVATE_IMMUTABLE_INVOKER_METADATA')
            original=observe(cur,queries);first=project(cur,original)
            for name in('fn_00','helper_00'):
                cur.execute('drop function cp7_portable_model.'+name+'()');cur.execute(function_sql(name),prepare=False)
                cur.execute('revoke all on function cp7_portable_model.'+name+'()from public,anon,authenticated,service_role')
            cur.execute('drop view cp7_portable_model.model_view;create view cp7_portable_model.model_view with(security_invoker=true)as select 1 as value',prepare=False)
            recreated=observe(cur,queries);second=project(cur,recreated)
            require(first==second and original!=recreated,'PORTABLE_ACTUAL_OID_RECREATION_MUST_PRESERVE_ONLY_SEMANTICS')
            require(original['functions'][0]['oid']!=recreated['functions'][0]['oid']and original['new_private_functions'][0]['oid']!=recreated['new_private_functions'][0]['oid']and original['view']['oid']!=recreated['view']['oid'],'PORTABLE_THREE_ACTUAL_OID_PATHS_MUST_CHANGE')
            report['raw'].update(actual_non_superuser_session=list(session),baseline_all22=before,installed_all22=installed,
                original_model_authority=original,after_actual_recreation=recreated,independent_projection_before=first,independent_projection_after=second)
            report['checks'].append(dict(id='ACTUAL_NONSUPERUSER_PRIVATE_PURE_HELPER_AND_REAL_THREE_OID_RECREATIONS_PRESERVE_EXACT_OTHER_FIELDS',status='PASS'))
            controls=[]
            mutations=[('body',"create or replace function cp7_portable_model.fn_00()returns int language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$select 2$$;"),
                ('native_function_ACL','grant execute on function cp7_portable_model.fn_00()to authenticated;'),
                ('private_helper_ACL','grant execute on function cp7_portable_model.helper_00()to authenticated;'),
                ('configuration',"alter function cp7_portable_model.fn_00()set TimeZone='Asia/Jakarta';"),
                ('view_definition','create or replace view cp7_portable_model.model_view with(security_invoker=true)as select 2 as value;'),
                ('view_ACL','grant select on cp7_portable_model.model_view to authenticated;'),
                ('view_options','alter view cp7_portable_model.model_view set(security_invoker=false);')]
            for label,statement in mutations:
                cur.execute('savepoint sensitivity');cur.execute(statement,prepare=False)
                actual=observe(cur,queries);changed=project(cur,actual)
                require(changed['sha256']!=first['sha256'],'PORTABLE_REAL_METADATA_MUTATION_HIDDEN:'+label)
                controls.append(dict(kind='ACTUAL_MODELED_DDL',field=label,authority=actual,projection=changed))
                cur.execute('rollback to savepoint sensitivity');cur.execute('release savepoint sensitivity')
            # Independent field sentinels cover every complete19 function cell;
            # these are JSON sensitivity controls, never actual Native DDL claims.
            for i in range(19):
                actual=copy.deepcopy(recreated);actual['functions'][0]['actual_catalog_row'][i]={'sentinel_cell':i}
                changed=project(cur,actual);require(changed['sha256']!=first['sha256'],'PORTABLE_COMPLETE19_CELL_HIDDEN:'+str(i))
                controls.append(dict(kind='SYNTHETIC_JSON_FIELD_SENTINEL',function_catalogue_cell=i,sha256=changed['sha256']))
            actual=copy.deepcopy(recreated);actual['sentinel_nested_identity']['oid']=43
            require(project(cur,actual)['sha256']!=first['sha256'],'PORTABLE_UNRELATED_NESTED_OID_WAS_STRIPPED')
            report['raw']['sensitivity_controls']=controls
            report['checks'].append(dict(id='SEVEN_REAL_MODELED_DDL_MUTATIONS_AND_EVERY_COMPLETE19_JSON_CELL_REMAIN_SENSITIVE',status='PASS'))
            malformed=[]
            for label,mutate in[
                ('missing_function_oid',lambda x:x['functions'][0].pop('oid')),
                ('short_function_row',lambda x:x['functions'][0]['actual_catalog_row'].pop()),
                ('duplicate_signature',lambda x:x['functions'][1].update(signature=x['functions'][0]['signature'])),
                ('missing_helper_oid',lambda x:x['new_private_functions'][0].pop('oid')),
                ('short_view_row',lambda x:x['view']['actual_catalog_row'].pop()),
                ('missing_view_oid',lambda x:x['view'].pop('oid')),
                ('missing_function',lambda x:x['functions'].pop()),
                ('wrong_function_array_type',lambda x:x.update(functions={}))]:
                actual=copy.deepcopy(recreated);mutate(actual);cur.execute('savepoint malformed');failed=None
                try:cur.execute('select '+SIG.split('(')[0]+'(%s::jsonb)',(Jsonb(actual),))
                except psycopg.Error as error:failed=dict(SQLSTATE=error.sqlstate,message=error.diag.message_primary)
                cur.execute('rollback to savepoint malformed');cur.execute('release savepoint malformed')
                require(failed is not None and failed['SQLSTATE']=='P0001'and failed['message']=='CP7_GLOBAL_COMPLETE_TYPED_AUTHORITY_REQUIRED','PORTABLE_MALFORMED_NOT_EXPLICITLY_REFUSED:'+label)
                malformed.append(dict(label=label,**failed))
            denials=[]
            for role in('anon','authenticated','service_role'):
                require(cur.execute('select has_schema_privilege(%s,\'cp7_global_nonpo_envelope\',\'USAGE\'),has_function_privilege(%s,%s,\'EXECUTE\')',(role,role,SIG)).fetchone()==(False,False),'PORTABLE_EXTERNAL_ACCESS_EXPANDED:'+role)
                # Nonsuperuser postgres has these existing SET memberships.
                cur.execute('savepoint external_denial');cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)));failed=None
                try:cur.execute('select '+SIG.split('(')[0]+'(%s::jsonb)',(Jsonb(recreated),))
                except psycopg.Error as error:failed=dict(SQLSTATE=error.sqlstate,message=error.diag.message_primary)
                cur.execute('rollback to savepoint external_denial');cur.execute('release savepoint external_denial')
                require(failed is not None and failed['SQLSTATE']=='42501','PORTABLE_EXTERNAL_CALL_NOT_REFUSED:'+role);denials.append(dict(role=role,**failed))
            require(observe(cur,queries)==recreated,'PORTABLE_SENSITIVITY_OR_REFUSAL_DID_NOT_RESTORE_MODEL_AUTHORITY')
            cur.execute('drop function '+SIG);final=base.capture(cur,queries)
            require(final==before,'PORTABLE_NARROW_UNUSED_INVERSE_DID_NOT_RESTORE_ALL22')
            report['raw'].update(malformed_refusals=malformed,external_role_denials=denials,final_all22=final)
            report['checks'].append(dict(id='EIGHT_TYPED_REFUSALS_THREE_EXTERNAL_DENIALS_AND_UNUSED_NARROW_INVERSE_ALL22',status='PASS'));conn.commit()
        report['status']='ACTUAL_SUPABASE17_PORTABLE_AUTHORITY_MODEL3_PASS_NOT_GLOBAL_RUNTIME'
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error),SQLSTATE=getattr(error,'sqlstate',None));(OUT/'PORTABLE_FIRST_FAILURE.txt').write_text(traceback.format_exc());raise
    finally:
        try:
            if created:
                with psycopg.connect(uri,autocommit=True)as conn,conn.cursor()as cur:
                    require(cur.execute('select count(*)from pg_stat_activity where datname=%s',(NAME,)).fetchone()[0]==0,'PORTABLE_UNEXPECTED_BACKEND_REFUSE_FORCE_DROP')
                    cur.execute(sql.SQL('drop database {}').format(sql.Identifier(NAME)));require(base.roles(cur)==roles_before,'PORTABLE_GLOBAL_ROLES_CHANGED')
                    report.update(capability_DB_removed=True,global_roles_and_memberships_restored=True)
        finally:
            (OUT/'PORTABLE_AUTHORITY_MODEL3.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],completed_controls=len(report['checks']),actual_Native_cases=0)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();m=parser.add_mutually_exclusive_group(required=True)
    m.add_argument('--check',action='store_true');m.add_argument('--start',action='store_true');m.add_argument('--run',action='store_true');args=parser.parse_args()
    if args.check:print(json.dumps(source()))
    elif args.start:
        source();s=importlib.util.spec_from_file_location('retained_bounded_startup',ROOT/'scripts/current-finance-combined-composition/disposable_start.py')
        module=importlib.util.module_from_spec(s);s.loader.exec_module(module);module.start(OUT/'disposable-startup-attempts')
    else:run()
