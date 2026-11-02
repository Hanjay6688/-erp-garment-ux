"""New complete-stage MODEL composition and Native owner/dispatch capability.

The accepted-parent gate is deliberately never patched or opened. Tables are
45 modeled Native row maps; only eleven Native function definitions/metadata
are reproduced exactly. Twelve callbacks, Auth and domain/Native constraints
are modeled. No invoice, payroll, stock, HPP or financial command executes.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,subprocess,sys,traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp7-proof'
NAME='cp7_mandor_install_plan_capability'
BRANCH='refs/heads/astra-a/mandor-install-plan-capability-20261102'
MODULE='scripts/cp7_mandor_shop/'
sys.path.insert(0,str(ROOT/'scripts'))
from cp7_mandor_shop import composition as product,native_dispatch
spec=importlib.util.spec_from_file_location('retained_inert_startup_utilities',ROOT/'scripts/current-global-catalog-bridge-capability/probe.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
require,pin=base.require,base.pin


def source():
    m=json.loads((HERE/'SOURCE.json').read_bytes())
    require(m['classification']=='COMPLETE_MANDOR_STAGE_MODEL_CAPABILITY_ONLY_NOT_NATIVE_BUSINESS','MANDOR_MODEL_ONLY_SCOPE')
    for name,value in m['files'].items():require(pin((ROOT/name).read_bytes())==value,'MANDOR_CAP_SOURCE_CHANGED:'+name)
    module=product.sources();require(module['actual_final_parent_admission']is None and module['runtime_entry']is None,
        'MANDOR_CAP_MUST_NOT_OPEN_ACTUAL_PARENT_OR_RUNTIME_GATE')
    fixture=json.loads((HERE/'TYPED_MODEL_PARENT.json').read_bytes())
    require(len(fixture['table_column_types'])==45 and len(fixture['original_functions'])==11 and len(fixture['mocked_helpers'])==12,
        'MANDOR_CAP_EXACT_MODEL_BOUNDARIES')
    return dict(head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        tree=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD^{tree}'],text=True).strip(),
        source_pins=len(m['files']),module=module,actual_Native_cases=0,old_completed_controls_NOT_rerun=True,
        production_go=False,independent_acceptance=False)


def setup(cur,fixture):
    from psycopg import sql
    created=[]
    for role,row in sorted(fixture['fixture_roles'].items()):
        if cur.execute('select 1 from pg_roles where rolname=%s',(role,)).fetchone():continue
        require(role.startswith('cp7_'),'MANDOR_CAP_ONLY_DECLARED_MODEL_ROLES_MAY_BE_CREATED:'+role)
        cur.execute(sql.SQL('create role {} nologin nosuperuser nocreatedb nocreaterole noreplication {} {}').format(
            sql.Identifier(role),sql.SQL('inherit'if row[1]else'noinherit'),sql.SQL('bypassrls'if row[6]else'nobypassrls')))
        created.append(role)
    for schema,owner in sorted(fixture['schema_owners'].items()):
        if schema=='public':
            cur.execute(sql.SQL('alter schema public owner to {}').format(sql.Identifier(owner)))
        else:
            require(not cur.execute('select 1 from pg_namespace where nspname=%s',(schema,)).fetchone(),
                'MANDOR_CAP_EXISTING_MODEL_SCHEMA_REFUSED:'+schema)
            cur.execute(sql.SQL('create schema {} authorization {}').format(sql.Identifier(schema),sql.Identifier(owner)))
        # Reproduce the reviewed Native ACL, including USAGE for the function
        # owner's row-type schema. CREATE alone does not provide type lookup.
        with product.as_role(cur,owner,{owner}):
            cur.execute(sql.SQL('revoke all on schema {} from public,{}').format(sql.Identifier(schema),sql.Identifier(owner)))
            for grantee,grantor,privilege,option in fixture['schema_acl'].get(schema,[]):
                require(grantor==owner and privilege in('USAGE','CREATE'),'MANDOR_CAP_REVIEWED_SCHEMA_GRANT_FORM:'+schema)
                cur.execute(sql.SQL('grant {} on schema {} to {}{}').format(sql.SQL(privilege),sql.Identifier(schema),
                    sql.SQL('PUBLIC')if grantee=='PUBLIC'else sql.Identifier(grantee),sql.SQL(' with grant option'if option else'')))
    # Initial model-row construction leases CREATE only for setup, then removes
    # it before any module capability observation.
    schema_leases=[]
    for schema in sorted(fixture['schema_owners']):
        if cur.execute("select has_schema_privilege('postgres',%s,'CREATE')",(schema,)).fetchone()[0]:continue
        cur.execute(sql.SQL('grant create on schema {} to postgres').format(sql.Identifier(schema)));schema_leases.append(schema)
    with product.as_role(cur,'postgres',{'postgres'}):
        cur.execute('create domain cp7_credit.cent_amount as numeric')
        cur.execute('create extension pgcrypto with schema extensions')
        for table,columns in sorted(fixture['table_column_types'].items()):
            schema,name=table.split('.')
            defs=[]
            for key,typename in columns.items():
                column=key.split(':',1)[1]
                defs.append(sql.SQL('{} {}').format(sql.Identifier(column),sql.SQL(typename)))
            if any(k.endswith(':id')for k in columns):defs.append(sql.SQL('primary key(id)'))
            cur.execute(sql.SQL('create table {}({})').format(sql.Identifier(schema,name),sql.SQL(',').join(defs)))
        # Compound referenced keys are setup facts, never Native constraints
        # claimed as reproduced or a financial validation oracle.
        unique=set()
        for name in product.ORDER:
            for table,columns in re.findall(r'references\s+((?:erp|cp7_[a-z_]+)\.[a-z_]+)\s*\(([^)]+)\)',(product.HERE/name).read_text(),re.I):
                if table.startswith('cp7_mandor_shop.'):continue
                names=tuple(c.strip()for c in columns.split(','))
                if names!=('id',):unique.add((table,names))
        for i,(table,columns)in enumerate(sorted(unique)):
            schema,name=table.split('.')
            cur.execute(sql.SQL('create unique index {} on {}({})').format(sql.Identifier('mandor_model_unique_'+str(i)),
                sql.Identifier(schema,name),sql.SQL(',').join(map(sql.Identifier,columns))))
        cur.execute("""create function auth.uid()returns uuid language sql stable as $$select null::uuid$$;
          create function auth.jwt()returns jsonb language sql stable as $$select '{}'::jsonb$$;""",prepare=False)
        for sig,row in sorted(fixture['mocked_helpers'].items()):
            result=row[16];body='begin return;end'if row[7]or result=='void'else'begin return null;end'
            statement='create function '+sig.split('(')[0]+'('+row[15]+')returns '+result+" language plpgsql security definer set search_path=''as $$"+body+'$$;'
            cur.execute(statement,prepare=False)
    for schema in schema_leases:
        cur.execute(sql.SQL('revoke create on schema {} from postgres').format(sql.Identifier(schema)))
    # Existing Native11 definitions run as their actual role owners. Each ACL
    # is normalized and restored from the actual original full19 projection.
    ordered=sorted(fixture['original_functions'],key=lambda s:s.startswith('public.'))
    for sig in ordered:
        row=fixture['original_functions'][sig];owner=row[1];schema=sig.split('.',1)[0]
        can_create=cur.execute('select has_schema_privilege(%s,%s,\'CREATE\')',(owner,schema)).fetchone()[0]
        if not can_create:cur.execute(sql.SQL('grant create on schema {} to {}').format(sql.Identifier(schema),sql.Identifier(owner)))
        with product.as_role(cur,owner,{owner}):
            cur.execute(row[0],prepare=False)
            cur.execute(sql.SQL('revoke all on function {} from public').format(sql.SQL(sig)))
            for grantee,grantor,privilege,option in row[18]:
                require(grantor==owner and privilege=='EXECUTE'and option is False,'MANDOR_CAP_ORIGINAL_ACL_FORM_MUST_BE_REVIEWED:'+sig)
                cur.execute(sql.SQL('grant execute on function {} to {}').format(sql.SQL(sig),sql.SQL('PUBLIC')if grantee=='PUBLIC'else sql.Identifier(grantee)))
        if not can_create:cur.execute(sql.SQL('revoke create on schema {} from {}').format(sql.Identifier(schema),sql.Identifier(owner)))
    return created


def run():
    source_identity=source();require(os.environ.get('GITHUB_REF')==BRANCH,'MANDOR_CAP_ONE_ISOLATED_BRANCH')
    require(os.environ.get('CAPABILITY_CONFIRM')=='cp7_mandor_install_plan_model_only','MANDOR_CAP_EXPLICIT_MODEL_CONFIRMATION')
    import psycopg
    from psycopg import sql
    fixture=json.loads((HERE/'TYPED_MODEL_PARENT.json').read_bytes());uri=base.fixed_uri()
    OUT.mkdir(parents=True,exist_ok=True);created=False;model_roles=[];roles_before=None
    report=dict(status='INCOMPLETE',source=source_identity,checks=[],raw={},model_parent_tables=45,
        exact_Native_source_definitions_reproduced_in_MODEL=11,mocked_helpers=12,
        Native_table_constraints_defaults_generated_RLS_Auth_and_domain_constraints_NOT_reproduced=True,
        actual_parent_gate_NEVER_opened=True,actual_global_or_Mandor_final_parent_adoption=False,
        old_158_SQL_40_client_and_all_previous_capability_controls_NOT_rerun=True,
        actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)
    try:
        with psycopg.connect(uri,autocommit=True)as conn,conn.cursor()as cur:
            require(not cur.execute('select 1 from pg_database where datname=%s',(NAME,)).fetchone(),'MANDOR_CAP_EXISTING_DATABASE_REFUSED')
            roles_before=base.roles(cur);cur.execute(sql.SQL('create database {} owner postgres template template0').format(sql.Identifier(NAME)));created=True
        with psycopg.connect(uri,dbname=NAME)as conn,conn.cursor()as cur:
            base.configure(cur);model_roles=setup(cur,fixture);conn.commit()
            baseline=product.capture(cur)
            for sig,row in fixture['original_functions'].items():require(baseline['functions'][sig]==row,'MANDOR_CAP_ACTUAL_MODEL_ALL19_DOES_NOT_MATCH_ORIGINAL:'+sig)
            gate=None
            try:product.install(cur,b'{}')
            except ValueError as failed:gate=str(failed)
            require(gate=='CP7_MANDOR_SHOP_ACTUAL_FINAL_ACCEPTED_PARENT_PENDING','MANDOR_CAP_REAL_INSTALLER_GATE_MUST_STAY_CLOSED')
            plan=json.loads((product.HERE/'INSTALL_PLAN.json').read_bytes());definitions=product.native_payment_routes.derive(baseline['functions'])[0]|product.native_sales_routes.derive(baseline['functions'])[0]
            facades,dispatch=product.native_dispatch.derive(baseline['functions']);identity=product.native_identity(cur,definitions)
            public_acl=cur.execute("select nspacl::text from pg_namespace where nspname='public'").fetchone()[0]
            with product.atomic(cur),product.metadata_context(cur):
                product.trusted_installer(cur)
                with product.as_role(cur,'postgres',{'postgres'}):
                    for name in product.ORDER:cur.execute((product.HERE/name).read_text(),prepare=False)
                    cur.execute(facades,prepare=False)
                product.normalize_private(cur,plan);product.replace_native(cur,definitions,identity)
                after=product.capture(cur);product.transition(baseline,after,definitions,plan)
                state=dict(contract=product.CONTRACT,sources=product.sources(),parent={'MODEL_ONLY':True,'accepted_parent':False},
                    before=baseline,after=after,originals={s:baseline['functions'][s][0]for s in definitions},definitions=definitions,
                    native_identity=identity,raw_public_schema_acl=public_acl,dispatch_proof=dispatch,plan=plan)
                state['sha256']=product.digest(state);verified=product.verify(cur,state)
            report['raw'].update(before_all22=baseline,installed_all22=after,original_Native_model_identity=identity,
                original_public_raw_ACL=public_acl,gate_refusal=gate,verified=verified,
                actual_API_memberships={k:v for k,v in after['memberships'].items()if k.split(':')[0]==product.ROLE})
            conn.commit();report['checks'].append(dict(id='COMPLETE_MODEL_STAGE40_FUNCTIONS27_TRIGGERS9_OWNER_ADAPTERS_AND_CLOSED_REAL_GATE',status='PASS'))
            # Change only this model command body temporarily. The exact old
            # Native public facade is unmodified and delegates as its owner.
            command=native_dispatch.COMMAND;command_identity=product.native_identity(cur,[command]);original=fixture['original_functions'][command][0]
            match=re.search(r'AS \$function\$(.*?)\$function\$',original,re.S|re.I);require(match is not None,'MANDOR_CAP_NATIVE_BODY_DELIMITER')
            role_probe=original[:match.start(1)]+"begin return jsonb_build_object('owner',current_user,'session',session_user);end "+original[match.end(1):]
            product.replace_native(cur,{command:role_probe},command_identity);conn.commit()
        with psycopg.connect('postgresql://postgres:postgres@127.0.0.1:54322/'+NAME)as native,native.cursor()as cur:
            base.configure(cur);profile=cur.execute("select current_user,session_user,rolsuper,current_setting('server_version_num')::int from pg_roles where rolname=current_user").fetchone()
            require(profile==('postgres','postgres',False,170006),'MANDOR_CAP_ACTUAL_NONSUPERUSER_POSTGRES_REQUIRED')
            denied=None
            try:cur.execute("select cp7_sales.command('CREATE','{}'::jsonb,null,null)")
            except psycopg.Error as failed:denied=dict(SQLSTATE=failed.sqlstate,error=failed.diag.message_primary)
            native.rollback();require(denied and denied['SQLSTATE']=='42501','MANDOR_CAP_DIRECT_PRIVATE_COMMAND_SHOULD_BE_DENIED')
            base.configure(cur);response=cur.execute("select public.erp_cp7_save_sale_v1('CREATE','{}'::jsonb,null,null)").fetchone()[0]
            require(response==dict(owner='cp7_sales_write',session='postgres'),'MANDOR_CAP_EXISTING_NATIVE_PUBLIC_FACADE_WRONG_OWNER')
            require(cur.execute('select current_user,session_user').fetchone()==('postgres','postgres'),'MANDOR_CAP_FACADE_OWNER_LEAKED_TO_CALLER')
            report['raw'].update(actual_non_superuser_profile=list(profile),direct_private_command_denial=denied,
                authorized_existing_facade_modeled_response=response);native.rollback()
        with psycopg.connect(uri,dbname=NAME)as conn,conn.cursor()as cur:
            product.replace_native(cur,{command:original},command_identity);conn.commit()
            require(product.capture(cur)==after,'MANDOR_CAP_NATIVE_ROLE_PROBE_INVERSE_NOT_EXACT')
            report['checks'].append(dict(id='UNCHANGED_NATIVE_PUBLIC_SALES_FACADE_DELEGATES_WITHOUT_NEW_EXECUTE_GRANTS_OR_ROLE_LEAK',status='PASS'))
            cur.execute('savepoint model_pending_context')
            cur.execute("""insert into cp7_mandor_shop.command_context values(pg_backend_pid(),txid_current(),
              '11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222','MODEL_PENDING_CONTEXT',repeat('a',64))""")
            refused=None
            try:product.rollback_preuse(cur,state)
            except ValueError as failed:refused=str(failed)
            require(refused=='MANDOR_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE:cp7_mandor_shop.command_context','MANDOR_CAP_PENDING_CONTEXT_REMOVAL_NOT_REFUSED')
            cur.execute('rollback to savepoint model_pending_context');cur.execute('release savepoint model_pending_context')
            inverse=product.rollback_preuse(cur,state);final=product.capture(cur);require(final==baseline,'MANDOR_CAP_FULL_STAGE_PREUSE_INVERSE_NOT_EXACT')
            report['raw'].update(modeled_pending_context_refusal=refused,preuse_inverse=inverse,final_all22=final,
                final_Native_model_identity=product.native_identity(cur,definitions))
            conn.commit();report['checks'].append(dict(id='PENDING_MODEL_CONTEXT_REFUSED_THEN_EXPLICIT_UNUSED_FULL_STAGE_INVERSE_RESTORES_ALL22_AND_RAW_AUTHORITY',status='PASS'))
        report['status']='ACTUAL_SUPABASE17_COMPLETE_MANDOR_MODEL_INSTALL_PLAN_NEW3_PASS_NOT_NATIVE_BUSINESS'
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error),SQLSTATE=getattr(error,'sqlstate',None))
        (OUT/'MANDOR_INSTALL_PLAN_FIRST_FAILURE.txt').write_text(traceback.format_exc());raise
    finally:
        try:
            if created:
                with psycopg.connect(uri,autocommit=True)as conn,conn.cursor()as cur:
                    require(cur.execute('select count(*)from pg_stat_activity where datname=%s',(NAME,)).fetchone()[0]==0,'MANDOR_CAP_UNEXPECTED_BACKEND_NO_FORCE_DROP')
                    cur.execute(sql.SQL('drop database {}').format(sql.Identifier(NAME)));report['capability_DB_removed']=True
            if roles_before is not None:
                with psycopg.connect(uri,autocommit=True)as conn,conn.cursor()as cur:
                    for role in reversed(model_roles):cur.execute(sql.SQL('drop role {}').format(sql.Identifier(role)))
                    require(base.roles(cur)==roles_before,'MANDOR_CAP_GLOBAL_ROLES_NOT_RESTORED')
                    report['model_roles_removed_and_global_roles_restored']=True
        finally:
            (OUT/'MANDOR_COMPLETE_INSTALL_PLAN_NEW3.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(dict(status=report['status'],new_completed_controls=len(report['checks']),actual_Native_cases=0)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();m=p.add_mutually_exclusive_group(required=True)
    m.add_argument('--check',action='store_true');m.add_argument('--run',action='store_true');m.add_argument('--start',action='store_true');a=p.parse_args()
    if a.check:print(json.dumps(source()))
    elif a.start:
        source();path=ROOT/'scripts/current-finance-combined-composition/disposable_start.py'
        spec=importlib.util.spec_from_file_location('retained_disposable_start',path);startup=importlib.util.module_from_spec(spec);spec.loader.exec_module(startup);startup.start(OUT/'disposable-startup-attempts')
    else:run()
