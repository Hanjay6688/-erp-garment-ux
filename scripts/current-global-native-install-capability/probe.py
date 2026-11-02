"""Fresh Global full-stage DDL on the actual accepted FREE predecessor schema.

No old financial scenario is dispatched. The frozen DDL bootstrap and accepted
parent installer construct the disposable schema once. The complete Global
runtime/parent/input gate stays closed, zero profiles are seeded, and the new
stage is rolled back through its actual transaction/savepoint. This does not
qualify the runtime seal, explicit preuse inverse or any financial operation.
"""
from pathlib import Path
from hashlib import sha256
import argparse,gzip,json,os,subprocess,sys,traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp6-proof/t3'
BRANCH='refs/heads/astra-a/global-native-install-capability-20261102'
sys.path.insert(0,str(ROOT/'scripts'))
from cp7_global_nonpo_envelope import composition as product,native_hooks,readonly_graph


def require(value,message):
    if not value:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def source():
    value=json.loads((HERE/'SOURCE.json').read_bytes())
    require(value['classification']=='ACTUAL_NATIVE_PARENT_GLOBAL_STAGE_DDL_ONLY_NOT_RUNTIME_OR_BUSINESS','GLOBAL_NATIVE_DDL_ONLY_SCOPE')
    for name,expected in value['files'].items():require(pin((ROOT/name).read_bytes())==expected,'GLOBAL_NATIVE_SOURCE_CHANGED:'+name)
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0')
    def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],env=env)
    require(git('rev-parse',value['parent_head']+'^{tree}').decode().strip()==value['parent_tree'],'GLOBAL_NATIVE_COMPLETE_SOURCE_PARENT_TREE')
    def entries(ref):return{line.split(b'\t',1)[1]:line.split(b'\t',1)[0]for line in git('ls-tree','-rz',ref).split(b'\0')if line}
    before,after=entries(value['parent_head']),entries('HEAD')
    require(all(after.get(n)==v for n,v in before.items()),'GLOBAL_NATIVE_ORIGINAL_PARENT_BLOB_OR_MODE_CHANGED')
    prepared=product.sources();require(prepared['final_parent_head']is None and prepared['complete_input_profile_pin']is None and prepared['runtime_entry']is None,'GLOBAL_NATIVE_MUST_KEEP_REAL_ADMISSION_CLOSED')
    try:product.install(None,b'{}',b'{}')
    except ValueError as error:require(str(error)=='CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING','GLOBAL_NATIVE_WRONG_CLOSED_GATE')
    else:raise ValueError('GLOBAL_NATIVE_REAL_INSTALLER_WAS_ARMED')
    return dict(head=git('rev-parse','HEAD').decode().strip(),tree=git('rev-parse','HEAD^{tree}').decode().strip(),
        source_pins=len(value['files']),unchanged_parent_blobs=len(before),product=prepared,
        old_financial_cases_NOT_dispatched=True,actual_business_cases=0)


def admitted_parent():
    from cp7_accessory_nonpayable import admission
    receipt=admission.parent_receipt()
    with admission.parent_scope():
        from cp7_current_de_free_date import composition as parent
        graph=parent.sources();exact=admission.qualified_parent_sources(receipt,graph)
        import cp6_t3_release_package as release
        import inspect
        require(pin(Path(release.__file__).read_bytes())==pin((ROOT/'scripts/cp6_t3_release_package.py').read_bytes()),'GLOBAL_NATIVE_EXACT_RELEASE_BOOTSTRAP_SOURCE_BEFORE_DB')
        require(pin((release.RELEASE/'MANIFEST.json').read_bytes())==pin((ROOT/'supabase/release/cp6-t3/MANIFEST.json').read_bytes()),'GLOBAL_NATIVE_EXACT_RELEASE_MANIFEST_BEFORE_DB')
        inspect.signature(release.install).bind(OUT/'GLOBAL_NATIVE_COMMITTED_RELEASE_DDL.json')
    return parent,admission,dict(head=receipt['head'],tree=receipt['tree'],run_id=receipt['run_id'],job_id=receipt['job_id'],
        accepted_original=pin((ROOT/'scripts/cp7_accessory_nonpayable/FREE3_PARENT_ROOT_ACTUAL_INTAKE.json').read_bytes()),
        exact_entire_parent_sources=exact,retained_cases_rerun=False)


def save(name,value):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),default=str)+'\n').encode()
    packed=gzip.compress(raw,mtime=0);p=OUT/(name+'.json.gz')
    require(not p.exists(),'GLOBAL_NATIVE_FIRST_ORIGINAL_MUST_NOT_BE_OVERWRITTEN:'+name)
    p.write_bytes(packed);return dict(name=p.name,raw=pin(raw),compressed=pin(packed))


def run():
    identity=source();require(os.environ.get('GITHUB_REF')==BRANCH,'GLOBAL_NATIVE_ONE_ISOLATED_BRANCH')
    require(os.environ.get('GLOBAL_NATIVE_CONFIRM')=='cp6_rollback_metadata_only','GLOBAL_NATIVE_EXPLICIT_DDL_ONLY_CONFIRMATION')
    parent,scope,parent_receipt=admitted_parent()
    import psycopg
    from urllib.parse import urlparse
    uri=os.environ.get('CP6_ADMISSION_CONTROL_PGURL','');p=urlparse(uri)
    require(p.hostname=='127.0.0.1'and p.port==54322 and p.path=='/template1'and p.username=='cp6_maintenance_admission'and not p.query and not p.fragment,'GLOBAL_NATIVE_FIXED_DISPOSABLE_MAINTENANCE_ONLY')
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(status='INCOMPLETE',source=identity,accepted_predecessor=parent_receipt,checks=[],raw={},
        actual_ERP_schema_constructed_by_unchanged_accepted_parent_installer=True,
        no_Native_table_or_callback_models=True,real_Global_runtime_gate_NEVER_opened=True,
        profile_rows_seeded=0,old_DE30_FREE3_permanent_and_capability_scenarios_NOT_dispatched=True,
        actual_Native_business_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_cases=0,actual_browser_cases=0,
        runtime_profile_and_explicit_unused_inverse_and_financial_qualification_pending=True,
        global_writer_or_permission_or_phantom_closure=False,production_go=False,independent_acceptance=False)
    try:
        # The AB clone lacks BC..BF Native functions required by CP7. Use the
        # existing committed release DDL installer first, exactly as the owning
        # package does. Its hash/closed-admission checks remain intact; none of
        # the old package financial scenario runners is dispatched here.
        with scope.parent_scope():
            import cp6_t3_release_package as release
            require(pin(Path(release.__file__).read_bytes())==pin((ROOT/'scripts/cp6_t3_release_package.py').read_bytes()),'GLOBAL_NATIVE_EXACT_COMMITTED_RELEASE_INSTALLER_REQUIRED')
            require(release.CLONE=='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback','GLOBAL_NATIVE_RELEASE_ONLY_DISPOSABLE_CLONE')
            bootstrap=release.install(OUT/'GLOBAL_NATIVE_COMMITTED_RELEASE_DDL.json')
            require(bootstrap.get('status')=='ALL_FILES_INSTALLED'and len(bootstrap.get('files',[]))==30,'GLOBAL_NATIVE_COMPLETE_COMMITTED_RELEASE_DDL_REQUIRED')
            report['committed_release_DDL_bootstrap']=dict(status=bootstrap['status'],files=len(bootstrap['files']),
                module=pin(Path(release.__file__).read_bytes()),manifest=pin((release.RELEASE/'MANIFEST.json').read_bytes()),old_business_scenarios_dispatched=0)
        with scope.parent_scope(),psycopg.connect(uri,dbname='cp6_rollback')as conn,conn.cursor()as cur:
            product.trusted_installer(cur)
            require(cur.execute('select current_database(),current_setting(\'server_version_num\')::int').fetchone()==('cp6_rollback',170006),'GLOBAL_NATIVE_EXACT_SUPABASE17_DATABASE')
            require(os.environ.get('CP6_FIXTURE_SCHEMA_PROFILE')=='HOSTED_USAGE'
                and cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()==(True,),
                'GLOBAL_NATIVE_EXISTING_HOSTED_SCHEMA_USAGE_MUST_BE_PRESERVED')
            before_parent=product.capture(cur)
            with product.as_role(cur,'supabase_admin'):
                inherited=parent.install(cur)
            before=product.capture(cur);current=product.all22(before);readonly_graph.compare_current(current)
            originals=native_hooks.originals();definitions,routes=native_hooks.derive({sig:current['functions'].get(sig)for sig in originals})
            raw_identity=product.native_identity(cur,definitions)
            for columns in json.loads((product.HERE/'NATIVE_SCOPE_WORK_REFERENCE.json').read_bytes())['columns'].values():
                for key,row in columns.items():require(current['columns'].get(key)==row,'GLOBAL_NATIVE_REAL_WORK_COLUMN_CHANGED:'+key)
            report['raw']['actual_accepted_parent25']=save('GLOBAL_ACTUAL_ACCEPTED_PARENT25',before)
            report['raw']['original_eight_native_raw_authorities']=raw_identity
            report['checks'].append(dict(id='ACTUAL_ACCEPTED_FREE_SCHEMA_FULL25_AND_ALL19_REFERENCES_EIGHT_OWNERS_AND73_WORK_COLUMNS',status='PASS'))
            cur.execute('savepoint cp7_global_native_capability_stage')
            plan=json.loads((product.HERE/'INSTALL_PLAN.json').read_bytes());texts=product.sql_sources()
            try:
                with product.as_role(cur,'postgres'):
                    cur.execute('create schema cp7_global_nonpo_native_graph authorization postgres')
                    for name in product.CORE_ORDER:
                        report['compiling_source_file']=name;cur.execute(texts[name],prepare=False)
                for name in product.PLATFORM_ORDER:
                    report['compiling_source_file']=name
                    with product.as_role(cur,'supabase_admin'):cur.execute(texts[name],prepare=False)
                report.pop('compiling_source_file',None)
                product.normalize_private(cur,plan);product.replace_native(cur,definitions,raw_identity)
                after=product.capture(cur);report['raw']['compiled_global25']=save('GLOBAL_COMPILED_ON_NATIVE_PARENT25',after)
                product.transition(before,after,definitions,plan);compiled=product.verify_objects(cur,after,plan)
                require(product.native_identity(cur,definitions)==raw_identity,'GLOBAL_NATIVE_OID_RAW_AUTHORITY_CHANGED')
                with product.as_role(cur,'postgres'):
                    authority=cur.execute('select cp7_global_nonpo_native_graph.authority_v1()').fetchone()[0]
                    require(authority.get('known_functions_exact')is True and authority.get('new_private_acl_closed')is True and authority.get('view',{}).get('exact_known_source')is True,'GLOBAL_NATIVE_REAL_READONLY_AUTHORITY_MUST_STAY_EXACT')
                    require(cur.execute('select count(*)from cp7_global_nonpo_envelope.profiles').fetchone()==(0,),'GLOBAL_NATIVE_CAPABILITY_MUST_NOT_SEED_ANY_PROFILE')
                report['raw'].update(compiled_source_authority=compiled,actual_readonly_authority=authority,
                    eight_counted_routes=routes,after_eight_native_raw_authorities=product.native_identity(cur,definitions))
                report['checks'].append(dict(id='ALL16_FUNCTIONS_THREE_TABLES_SEVEN_TRIGGERS_EIGHT_NATIVE_ADAPTERS_COMPILE_ON_ACTUAL_PARENT_WITH_EXACT_ACLS',status='PASS'))
            finally:
                cur.execute('rollback to savepoint cp7_global_native_capability_stage');cur.execute('release savepoint cp7_global_native_capability_stage')
            restored=product.capture(cur);require(restored==before,'GLOBAL_NATIVE_STAGE_TRANSACTION_DID_NOT_RESTORE_FULL25')
            require(product.native_identity(cur,definitions)==raw_identity,'GLOBAL_NATIVE_STAGE_ROLLBACK_LOST_NATIVE_RAW_AUTHORITY')
            report['raw']['restored_accepted_parent25']=save('GLOBAL_RESTORED_ACCEPTED_PARENT25',restored)
            conn.rollback();after_parent=product.capture(cur)
            require(after_parent==before_parent,'GLOBAL_NATIVE_PARENT_DDL_TRANSACTION_DID_NOT_RESTORE_BASELINE25')
            report['raw'].update(before_parent25=save('GLOBAL_BEFORE_PARENT25',before_parent),after_parent25=save('GLOBAL_AFTER_PARENT_ROLLBACK25',after_parent))
            report['checks'].append(dict(id='GLOBAL_SAVEPOINT_RESTORES_FULL25_AND_ORIGINAL_EIGHT_RAW_IDENTITIES_PARENT_DDL_TRANSACTION_RESTORES_BASELINE25',status='PASS'))
            conn.rollback()
        report['status']='ACTUAL_SUPABASE17_GLOBAL_FULL_STAGE_DDL_ON_ACCEPTED_NATIVE_PARENT3_PASS_NOT_RUNTIME_OR_FINANCE'
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error),SQLSTATE=getattr(error,'sqlstate',None))
        (OUT/'GLOBAL_NATIVE_INSTALL_FIRST_FAILURE.txt').write_text(traceback.format_exc());raise
    finally:
        (OUT/'GLOBAL_NATIVE_INSTALL_CAPABILITY3.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps(dict(status=report['status'],completed_controls=len(report['checks']),actual_business_cases=0,error=report.get('error'))),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true');mode.add_argument('--run',action='store_true');args=parser.parse_args()
    if args.check:
        static=source();_,_,parent=admitted_parent();print(json.dumps(dict(source=static,accepted_parent=parent,actual_SQL_executed=0)))
    else:run()
