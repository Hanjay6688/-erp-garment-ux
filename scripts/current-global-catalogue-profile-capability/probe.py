"""New fixed25 fingerprint controls only; no prior ERP/capability test reruns."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,subprocess,traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp7-proof'
NAME='cp7_catalogue_profile_capability'
BRANCH='refs/heads/astra-a/global-catalogue-profile-capability-20261102'
SIG='cp7_global_nonpo_envelope.catalogue_fingerprint_v1()'
spec=importlib.util.spec_from_file_location('retained_inert_capability_utilities',
    ROOT/'scripts/current-global-catalog-bridge-capability/probe.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
require,pin=base.require,base.pin


def source():
    m=json.loads((HERE/'SOURCE.json').read_bytes())
    require(m['classification']=='FIXED25_CATALOGUE_FINGERPRINT_ACTUAL17_MODEL_ONLY','CATALOGUE_MODEL_ONLY_SCOPE')
    required={str((HERE/n).relative_to(ROOT))for n in('probe.py','FINGERPRINT.sql','QUERIES25.json','SOURCE_PROOF.json','INVERSE.sql')}
    required|={'.github/workflows/cp7-global-catalogue-profile-capability.yml',
        'scripts/current-global-catalog-bridge-capability/probe.py','scripts/cp7_ow04_restore_bundle.py',
        'scripts/current-finance-combined-composition/disposable_start.py'}
    require(set(m['files'])==required,'CATALOGUE_EXACT_NINE_SOURCE_INPUTS')
    for n,v in m['files'].items():require(pin((ROOT/n).read_bytes())==v,'CATALOGUE_SOURCE_CHANGED:'+n)
    p=json.loads((HERE/'SOURCE_PROOF.json').read_bytes())
    require(p['generated_source']==pin((HERE/'FINGERPRINT.sql').read_bytes())and p['total_groups']==25,
        'CATALOGUE_EXACT_GENERATED_SQL')
    queries=json.loads((HERE/'QUERIES25.json').read_bytes())
    require(len(queries)==25 and set(queries)-set(base.queries())=={'operators','casts','languages'},'CATALOGUE_ORIGINAL22_PLUS_ONLY_THREE')
    require(all(queries[k]==v for k,v in base.queries().items()),'CATALOGUE_ALL_ORIGINAL_QUERY_STRINGS_EXACT')
    return dict(head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        tree=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD^{tree}'],text=True).strip(),
        source_pins=9,old_completed_controls_NOT_rerun=True,actual_Native_cases=0,production_go=False,independent_acceptance=False)


def capture(cur,queries):
    result={}
    for key,query in sorted(queries.items()):
        rows=cur.execute('select k,v from('+query+')q(k,v)order by k collate "C",v::text collate "C"').fetchall()
        result[key]=[list(r)for r in rows]
    return result


def observed(cur,queries):
    from psycopg.types.json import Jsonb
    rows=capture(cur,queries)
    preimage=cur.execute('select %s::jsonb::text',(Jsonb(rows),)).fetchone()[0]
    actual=cur.execute('select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()').fetchone()[0]
    expected=dict(contract='cp7.global-catalogue-fingerprint.v1',groups=25,
        sha256=hashlib.sha256(preimage.encode()).hexdigest(),counts={k:len(v)for k,v in rows.items()})
    require(actual==expected,'CATALOGUE_HELPER_DIFFERS_FROM_INDEPENDENT_FULL25_QUERY_OBSERVATION')
    return dict(catalogues=rows,canonical_DB_jsonb_preimage=preimage,helper_fingerprint=actual)


def run():
    identity=source();require(os.environ.get('GITHUB_REF')==BRANCH,'CATALOGUE_ONE_ISOLATED_BRANCH')
    require(os.environ.get('CAPABILITY_CONFIRM')=='cp7_global_catalogue_profile_only','CATALOGUE_ISOLATED_CONFIRMATION')
    import psycopg
    from psycopg import sql
    queries=json.loads((HERE/'QUERIES25.json').read_bytes());uri=base.fixed_uri();created=False;roles_before=None
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(status='INCOMPLETE',source=identity,checks=[],raw={},all_application_objects_are_models=True,
        old_catalog_relation_Afui_Mandor_and_financial_controls_NOT_rerun=True,
        actual_global_installer_or_parent_adoption=False,global_writer_or_permission_or_phantom_closure=False,
        actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)
    try:
        with psycopg.connect(uri,autocommit=True)as admin,admin.cursor()as cur:
            require(not cur.execute('select 1 from pg_database where datname=%s',(NAME,)).fetchone(),'CATALOGUE_EXISTING_DB_REFUSE_TO_TOUCH')
            roles_before=base.roles(cur);cur.execute(sql.SQL('create database {} owner postgres template template0').format(sql.Identifier(NAME)));created=True
        with psycopg.connect(uri,dbname=NAME)as conn,conn.cursor()as cur:
            base.configure(cur);cur.execute('set local role postgres')
            cur.execute("""create schema cp7_global_nonpo_envelope authorization postgres;
              revoke all on schema cp7_global_nonpo_envelope from public,anon,authenticated,service_role;
              create schema cp7_catalogue_model authorization postgres;
              create table cp7_catalogue_model.effects(id int primary key,value int);
              create sequence cp7_catalogue_model.model_seq;
              create type cp7_catalogue_model.box as(value int);
              create function cp7_catalogue_model.to_int(cp7_catalogue_model.box)returns int language sql immutable as $$select ($1).value$$;
              create function cp7_catalogue_model.add_v1(int,int)returns int language sql immutable as $$select $1+$2$$;
              reset role;""",prepare=False)
            conn.commit();base.configure(cur);baseline=capture(cur,queries)
            cur.execute('set local role postgres');cur.execute((HERE/'FINGERPRINT.sql').read_text(),prepare=False);cur.execute('reset role')
            installed=observed(cur,queries)
            for group,rows in baseline.items():
                before=dict(rows);after=dict(installed['catalogues'][group])
                require(set(after)-set(before)==({SIG}if group=='functions'else set()),'CATALOGUE_ONLY_ONE_NEW_FUNCTION:'+group)
                require(all(after.get(k)==v for k,v in before.items()),'CATALOGUE_EXISTING_METADATA_CHANGED:'+group)
            row=cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile,proconfig,proacl::text from pg_proc where oid=%s::regprocedure",(SIG,)).fetchone()
            require(row[:3]==('postgres',True,'s')and set(row[3])=={'search_path=""','TimeZone=UTC'},'CATALOGUE_FIXED_PRIVATE_STABLE_AUTHORITY')
            require(set(row[4][1:-1].split(','))=={'postgres=X/postgres'},'CATALOGUE_PRIVATE_OWNER_ONLY_RAW_ACL')
            report['raw'].update(baseline_catalogues=baseline,installed=installed,function_raw_ACL=row[4]);conn.commit()
            report['checks'].append(dict(id='FIXED25_EXACT_SOURCE_PRIVATE_STABLE_HELPER_MATCHES_INDEPENDENT_QUERY_PREIMAGE',status='PASS'))
        native_uri='postgresql://postgres:postgres@127.0.0.1:54322/'+NAME
        with psycopg.connect(native_uri)as native,native.cursor()as cur:
            base.configure(cur)
            profile=cur.execute("select current_user,session_user,rolsuper,current_setting('server_version_num')::int from pg_roles where rolname=current_user").fetchone()
            require(profile==('postgres','postgres',False,170006),'CATALOGUE_REAL_NONSUPERUSER_SUPABASE17_SESSION')
            cur.execute("insert into cp7_catalogue_model.effects values(1,42);select nextval('cp7_catalogue_model.model_seq')",prepare=False)
            value=observed(cur,queries);require(value==installed,'CATALOGUE_DATA_OR_SEQUENCE_POSITION_POLLUTED_METADATA_FINGERPRINT')
            native.rollback();base.configure(cur)
            # Model sequence positions do not roll back in PostgreSQL. Restore
            # this one explicitly instead of claiming transaction rollback did.
            cur.execute("select setval('cp7_catalogue_model.model_seq',1,false)");native.commit()
            report['raw'].update(actual_non_superuser_profile=list(profile),after_model_data_and_nextval=value,
                model_sequence_reset_explicit=True,model_row_rolled_back=True)
            report['checks'].append(dict(id='MODEL_ROW_AND_NEXTVAL_LEAVE_ALL25_FINGERPRINT_UNCHANGED_SEQUENCE_EXPLICITLY_RESET',status='PASS'))
        mutations=[
          ('operators','set local role postgres;create operator cp7_catalogue_model.##(leftarg=int,rightarg=int,function=cp7_catalogue_model.add_v1);reset role;',
            'set local role postgres;drop operator cp7_catalogue_model.##(int,int);reset role;'),
          ('casts','set local role postgres;create cast(cp7_catalogue_model.box as int)with function cp7_catalogue_model.to_int(cp7_catalogue_model.box)as assignment;reset role;',
            'set local role postgres;drop cast(cp7_catalogue_model.box as int);reset role;'),
          ('languages','create trusted procedural language cp7_catalogue_model_lang handler pg_catalog.plpgsql_call_handler inline pg_catalog.plpgsql_inline_handler validator pg_catalog.plpgsql_validator;',
            'drop procedural language cp7_catalogue_model_lang;')]
        dispatch=[]
        for group,forward,inverse in mutations:
            with psycopg.connect(uri,dbname=NAME)as conn,conn.cursor()as cur:
                base.configure(cur);cur.execute(forward,prepare=False);conn.commit();base.configure(cur)
                changed=observed(cur,queries)
                require(changed['helper_fingerprint']['sha256']!=installed['helper_fingerprint']['sha256'],'CATALOGUE_DISPATCH_CHANGE_NOT_DETECTED:'+group)
                for key,rows in installed['catalogues'].items():
                    if key==group:require(len(changed['catalogues'][key])==len(rows)+1,'CATALOGUE_ONE_DISPATCH_ROW_REQUIRED:'+group)
                    else:require(changed['catalogues'][key]==rows,'CATALOGUE_UNDECLARED_DISPATCH_CHANGE:'+key)
                cur.execute(inverse,prepare=False);conn.commit();base.configure(cur)
                require(observed(cur,queries)==installed,'CATALOGUE_DISPATCH_NARROW_INVERSE_NOT_EXACT:'+group)
                dispatch.append(dict(group=group,changed=changed,narrow_inverse_all25_equal=True));conn.commit()
        with psycopg.connect(uri,dbname=NAME)as conn,conn.cursor()as cur:
            base.configure(cur)
            require(cur.execute('select count(*)from cp7_catalogue_model.effects').fetchone()[0]==0,'CATALOGUE_MODELED_ROW_NOT_RESTORED')
            require(cur.execute('select last_value,is_called from cp7_catalogue_model.model_seq').fetchone()==(1,False),'CATALOGUE_MODELED_SEQUENCE_NOT_EXPLICITLY_RESTORED')
            cur.execute((HERE/'INVERSE.sql').read_text(),prepare=False)
            final=capture(cur,queries);require(final==baseline,'CATALOGUE_ALL25_FINAL_NOT_EXACTLY_RESTORED')
            report['raw'].update(dispatch_mutations=dispatch,final_catalogues=final);conn.commit()
            report['checks'].append(dict(id='OPERATOR_CAST_LANGUAGE_CHANGES_EACH_DETECTED_AND_NARROW_INVERSES_RESTORE_ALL25',status='PASS'))
        report['status']='ACTUAL_SUPABASE17_FIXED25_CATALOGUE_FINGERPRINT_NEW3_PASS_NOT_GLOBAL_RUNTIME'
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error),SQLSTATE=getattr(error,'sqlstate',None))
        (OUT/'CATALOGUE_FIRST_FAILURE.txt').write_text(traceback.format_exc());raise
    finally:
        try:
            if created:
                with psycopg.connect(uri,autocommit=True)as admin,admin.cursor()as cur:
                    require(cur.execute('select count(*)from pg_stat_activity where datname=%s',(NAME,)).fetchone()[0]==0,'CATALOGUE_UNEXPECTED_BACKEND_NO_FORCE_DROP')
                    cur.execute(sql.SQL('drop database {}').format(sql.Identifier(NAME)))
                    require(base.roles(cur)==roles_before,'CATALOGUE_GLOBAL_ROLES_OR_MEMBERSHIPS_CHANGED')
                    report.update(capability_DB_removed=True,global_roles_and_memberships_restored=True)
        finally:
            (OUT/'CATALOGUE_FINGERPRINT_NEW3.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(dict(status=report['status'],new_completed_controls=len(report['checks']),actual_Native_cases=0)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();m=p.add_mutually_exclusive_group(required=True)
    m.add_argument('--check',action='store_true');m.add_argument('--run',action='store_true');m.add_argument('--start',action='store_true');a=p.parse_args()
    if a.check:print(json.dumps(source()))
    elif a.start:
        source();path=ROOT/'scripts/current-finance-combined-composition/disposable_start.py'
        spec=importlib.util.spec_from_file_location('retained_disposable_start',path);startup=importlib.util.module_from_spec(spec);spec.loader.exec_module(startup);startup.start(OUT/'disposable-startup-attempts')
    else:run()
