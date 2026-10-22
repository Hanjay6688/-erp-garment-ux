"""Default P21 rehearsal of the source-verified current OW05 installation.

Uses the qualified restore helpers without changing financial functions. It
retains full dump/restore, all catalog/data/sequence checks, both committed
credit/refund chains, and the legacy supplier/analysis use and readback.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os,subprocess,sys,traceback,uuid

sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[1]
HERE=REPO/'scripts/ow05-p21-qualification'
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('p21_current_restore_helpers',REPO/'scripts/ow04-payment-used-restore-qualification/probe.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
import cp7_p21_ow05_adapter as adapter
import cp7_ow05_restore as ow05_restore
from cp7_contractor_correction import native_probe as native_control
import mandor_fixture

product=adapter.owner
basic,payment,restore,dump,drill=helper.basic,helper.payment,ow05_restore,helper.dump,helper.drill
database,psycopg,sql,advisors=helper.database,helper.psycopg,helper.sql,helper.advisors
previous,package,core,p09=helper.previous,helper.package,helper.core,helper.p09
prepare,differences=helper.prepare,helper.differences
profile=helper.profile
READ_OBSERVATIONS=helper.READ_OBSERVATIONS
LABEL='CP7_P21_CURRENT_OW05_REHEARSAL'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
PRE_DUMP='/tmp/p21_current_ow05_pre.dump'
USED_DUMP='/tmp/p21_current_ow05_used.dump'
LEGACY_USE={}
OW05_STEPS=('COMMITTED_OW05_MANDOR_NEW24_AND_NOTA','RESTORED_OW05_EXACT_READS_AND_FOUR_RECEIPT_REPLAYS','RESTORED_OW05_NAMED_INVERSES_NEXT_ASSIGNMENT')
P21_STEPS=('CURRENT_INSTALL_1','EXACT_PREUSE_ROLLBACK','CURRENT_REINSTALL','COMMITTED_SUPPLIER_AND_STAGED_ANALYSIS')
LEGACY_AR_CHECKS=('V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH',
    'V2620H_CUSTOMER_AR_STATUS_MISMATCH','V268_AR_GL_SUBLEDGER_MISMATCH')


def legacy_ar_checks(cur):
    return cur.execute('select check_name,severity,issue_count from erp.run_v268_financial_report_checks() '
        'where check_name=any(%s::text[])order by check_name',(list(LEGACY_AR_CHECKS),)).fetchall()


def admitted():
    predecessor=native_control.admitted()
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('OW05_P21_SOURCE_CHANGED',path)
    proof=pins['native_original'];raw=Path(os.environ['OW05_NATIVE28_ORIGINAL_REPORT']).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']=='PASS'and actual['native']['counts']=={'PASS':28}and actual['required_case_ids_pass']
    assert actual['cp6_restored']and actual['advisor_gate']
    assert actual['source_declaration']['declared_source']==predecessor['declared_source']
    raw=(HERE/'EXPECTED_P21_RESTORE.json').read_bytes()
    assert sha256(raw).hexdigest()=='643081adcec37ffd3c4d83c25e7522522da634e81cb8af551796202c16bc2cf9'
    assert pins['OW05_steps']==list(OW05_STEPS)
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE),
        'scripts/cp7_p21_current_ow05_rehearsal_probe.py','scripts/cp7_p21_full_rehearsal_probe.py',
        'scripts/cp7_ow05_restore.py','scripts/cp7_p21_ow05_adapter.py'],text=True).strip()
    return dict(actual_Native28_original=proof,Native28_actually_rerun_here=False),json.loads(raw)


def reinstall_catalog(catalog):
    result=restore.catalog._portable(catalog)
    # Each install has a newly allocated set of seven declared ERP FK trigger
    # OIDs. Both exact local census bodies are verified/executed before this
    # comparison. Only that one generated definition differs legitimately;
    # its metadata/ACL and every other catalog member remain exact.
    result['functions'][restore.catalog.GUARD][0]='<CURRENT_DECLARED_LOCAL_OID_CENSUS_VERIFIED>'
    return result


def p21_install_cycle(cur,report):
    before_catalog=restore.catalog._catalog_rows(cur);before_data=restore.catalog._data(cur)
    first=adapter.install(cur);adapter.verify(cur,first)
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    first_catalog=reinstall_catalog(first['installed_catalog'])
    first_counts={k:v[0]for k,v in first['seeded_private_rows'].items()}
    steps=report.setdefault('p21_adapter_steps',[])
    steps.append(dict(step=P21_STEPS[0],status='PASS',all22_catalog_groups_verified=True))
    removed=adapter.rollback_preuse(cur,first)
    after_catalog=restore.catalog._catalog_rows(cur);after_data=restore.catalog._data(cur)
    changed={kind:{key:dict(expected=before_catalog.get(kind,{}).get(key),
        actual=after_catalog.get(kind,{}).get(key))
        for key in sorted(set(before_catalog.get(kind,{}))|set(after_catalog.get(kind,{})))
        if before_catalog.get(kind,{}).get(key)!=after_catalog.get(kind,{}).get(key)}
        for kind in sorted(set(before_catalog)|set(after_catalog))
        if before_catalog.get(kind)!=after_catalog.get(kind)}
    report['p21_preuse_catalog_comparison']=dict(all22_groups_equal=not changed,
        changed_members=changed,before_sha256=restore.catalog.digest(before_catalog),
        after_sha256=restore.catalog.digest(after_catalog))
    report['p21_preuse_data_comparison']=dict(equal=after_data==before_data,
        changed_tables={key:dict(expected=before_data.get(key),actual=after_data.get(key))
        for key in sorted(set(before_data)|set(after_data))if before_data.get(key)!=after_data.get(key)})
    assert not changed,'P21_CURRENT_PREUSE_CATALOG_NOT_EXACT'
    assert after_data==before_data,'P21_CURRENT_PREUSE_DATA_OR_SEQUENCE_NOT_EXACT'
    steps.append(dict(step=P21_STEPS[1],status='PASS',complete_removal=removed,
        all_catalog_data_and_sequences_equal_preinstall=True))
    second=adapter.install(cur);adapter.verify(cur,second)
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    second_catalog=reinstall_catalog(second['installed_catalog'])
    reinstall_changed={kind:{key:dict(expected=first_catalog[kind].get(key),actual=second_catalog[kind].get(key))
        for key in sorted(set(first_catalog[kind])|set(second_catalog[kind]))
        if first_catalog[kind].get(key)!=second_catalog[kind].get(key)}
        for kind in first_catalog if first_catalog[kind]!=second_catalog[kind]}
    report['p21_reinstall_catalog_comparison']=dict(equal=not reinstall_changed,
        changed_members=reinstall_changed,first_sha256=restore.catalog.digest(first_catalog),
        second_sha256=restore.catalog.digest(second_catalog))
    assert not reinstall_changed,'P21_CURRENT_REINSTALL_CATALOG_CHANGED'
    assert {k:v[0]for k,v in second['seeded_private_rows'].items()}==first_counts
    steps.append(dict(step=P21_STEPS[2],status='PASS',all22_portable_catalog_groups_equal=True,
        both_exact_local_OID_censuses_verified=True,seeded_private_counts_equal=True))
    return second


def legacy_prepare(cur,today,report):
    # Preserve the two real use examples of the earlier full P21 rehearsal.
    # They use Native fixtures; this is not an Auth/browser or speed claim.
    fixture=dump.create.funded(cur,today)
    paid=dump.create.command(cur,dump.create.payload(cur,fixture,'100.00'))
    assert paid['status']=='POSTED'and paid['remaining_after']=='900.00',paid
    # This unchanged E01 builder asserts global report READY at each of its
    # Native production steps. Run those baseline assertions before adding
    # OW04 credit. Its legacy readiness detector still omits U-I; that known
    # report-adapter boundary belongs to the already-open financial checks
    # item. Preserve and compare its blocked result after actual credit use.
    dump.load.real_workload(cur,today)
    checks=legacy_ar_checks(cur)
    assert checks==[(name,'CRITICAL',0)for name in LEGACY_AR_CHECKS],checks
    LEGACY_USE.update(payment_id=paid['payment_id'],remaining_after=paid['remaining_after'])
    report['legacy_readiness_before_OW04_credit']=checks


def legacy_use(cur,today,report):
    key,first_job,done,calls=dump.staged.staged_done(cur,today)
    original,pages,shape=dump.staged.fetch(cur,done['run_id'])
    basic.native.b.api.admin(cur)
    LEGACY_USE.update(ready=True,run_id=done['run_id'])
    checks=legacy_ar_checks(cur)
    expected=[(LEGACY_AR_CHECKS[0],'CRITICAL',2),(LEGACY_AR_CHECKS[1],'CRITICAL',3),
        (LEGACY_AR_CHECKS[2],'CRITICAL',1)]
    assert checks==expected,('P21_LEGACY_READINESS_BOUNDARY_CHANGED',checks)
    report['known_remaining_report_boundary']=dict(owner_open_work='OW-08',
        reason='Legacy readiness AR checks use Native P without the verified credit U-I adjustment.',
        actual_legacy_checks=checks,expected_legacy_checks=expected,
        report_readiness_after_credit_not_claimed_READY=True,
        original_report_checks_and_E01_READY_assertions_not_changed=True)
    report['p21_adapter_steps'].append(dict(step=P21_STEPS[3],status='PASS',
        supplier_payment_created=LEGACY_USE['payment_id'],remaining_after=LEGACY_USE['remaining_after'],
        staged_request=str(key),staged_run=done['run_id'],staged_units=len(calls),
        staged_pages=shape['page_count'],staged_targets=shape['targets_total'],
        staged_identity_hash=pages['identity_hash'],committed_with_current_OW04_chains=True))


def read(cur,item,phase='FIXTURE_PREPARATION'):
    actual=helper.read(cur,item,phase)
    if LEGACY_USE.get('ready'):
        # The old Native staged helper uses ordinary fixture SQL. Its scoped
        # usage grant is always restored and is never a browser capability.
        granted=not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if granted:cur.execute('grant usage on schema erp to authenticated')
        original,pages,shape=dump.staged.fetch(cur,LEGACY_USE['run_id'])
        basic.native.b.api.admin(cur)
        if granted:cur.execute('revoke usage on schema erp from authenticated')
        actual['legacy_staged']=dict(identity_hash=pages['identity_hash'],
            pages=[(p['index'],p['sha256'])for p in pages['pages']],shape=shape,
            original_sha256=sha256(json.dumps(original,sort_keys=True,default=str).encode()).hexdigest())
        actual['legacy_supplier_payment']=cur.execute('select to_jsonb(p)from erp.supplier_payments p where id=%s',
            (LEGACY_USE['payment_id'],)).fetchone()[0]
        assert actual['legacy_supplier_payment']is not None
        actual['legacy_financial_integrity_checks']=legacy_ar_checks(cur)
    return actual


def refusal_controls(cur,backup,digest,controls,request):
    def refused(name,call,message):
        cur.execute('savepoint restore_control')
        try:call()
        except ValueError as error:
            assert str(error).startswith(message),(name,str(error));controls.append(dict(id=name,status='PASS',error=str(error).split(':',1)[0]))
        else:raise AssertionError('CURRENT_RESTORE_UNSAFE_BINDING_ACCEPTED: '+name)
        finally:cur.execute('rollback to savepoint restore_control');cur.execute('release savepoint restore_control')
    refused('WRONG_TRUSTED_HASH',lambda:restore.rebind_restored(cur,backup,'0'*64,expected_database=database.RESTORED),'OW05_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    changed=deepcopy(backup);changed['sources']['financial_product']['composition_sha256']='0'*64
    refused('CHANGED_FINANCIAL_SOURCE',lambda:restore.rebind_restored(cur,changed,restore.catalog.digest(changed),expected_database=database.RESTORED),'OW05_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    refused('WRONG_TARGET_DATABASE',lambda:restore.rebind_restored(cur,backup,digest,expected_database='cp6_rollback'),'OW05_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED')
    def metadata():
        cost=cur.execute("select procost::numeric from pg_proc where oid='cp7_credit.payment_source_historical_plan_ids_v1(jsonb)'::regprocedure").fetchone()[0]
        cur.execute(sql.SQL('alter function cp7_credit.payment_source_historical_plan_ids_v1(jsonb)cost {}').format(sql.Literal(cost+1)))
        restore.rebind_restored(cur,backup,digest,expected_database=database.RESTORED)
    refused('ACTUAL_FUNCTION_METADATA_DRIFT',metadata,'OW05_RESTORE_CATALOG_CHANGED')
    def rows():
        # A real retained receipt is business data too. Its deferred guard is
        # rolled back with this savepoint; no audited Native master UPDATE or
        # nontransactional audit sequence is used by the fault fixture.
        cur.execute("update cp7_credit.consumer_requests_v1 set response=response||'{\"restore_fault\":true}'::jsonb where actor=%s and request_id=%s",(basic.native.auth.base.OPERATOR_AUTH,request));assert cur.rowcount==1
        restore.rebind_restored(cur,backup,digest,expected_database=database.RESTORED)
    refused('ACTUAL_BUSINESS_ROW_DRIFT',rows,'OW05_RESTORE_BUSINESS_ROWS_OR_SEQUENCE_CHANGED')
    actual_data=restore.catalog._data(cur)
    residue={key:dict(expected=backup['data'].get(key),actual=actual_data.get(key))for key in set(actual_data)|set(backup['data'])if actual_data.get(key)!=backup['data'].get(key)}
    assert not residue,'RESTORE_CONTROL_ROLLBACK_DATA_OR_SEQUENCE_RESIDUE: '+json.dumps(residue,sort_keys=True)
    assert restore.catalog._portable(restore.catalog._catalog_rows(cur))==restore.catalog._portable(backup['catalog'])
    return controls

def run():
    native_binding,gold=admitted()
    report=dict(label=LABEL,status='INCOMPLETE',candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        scenario_id=gold['scenario_id'],expected_scenario_count=1,actual_Native28_binding=native_binding,
        current_financial_sources=product.sources(),administrative_restore_sources=restore.sources(),
        Native28_rerun=False,real_Auth_browser_not_claimed=True,formal_CP7C_started=False,
        qualification_only=True,hosted=False,production_go=False,feature_complete=False,steps=[],
        current_P21_adapter_sources=adapter.sources(),
        default_P21_entrypoint_exercised=Path(sys.argv[0]).name=='cp7_p21_full_rehearsal_probe.py',
        read_observations=READ_OBSERVATIONS,only_validated_workspace_observation_time_separate_from_business_comparison=True)
    before=None;before_roles=set();new_roles=set();pre_dumped=False;installed=False
    try:
        assert drill.SOURCE==database.SOURCE=='cp6_rollback'and drill.CONTAINER=='supabase_db_cp5-local'
        report['baseline_advisors']=advisors(package.boundary.PG)
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            assert conn.info.host in('127.0.0.1','localhost')and cur.execute('select current_database()').fetchone()==(database.SOURCE,)
            p09.wip.policy.bf.verified(cur);before_roles=database._roles(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions);conn.rollback()
        pre_data=drill.data_hashes(database.SOURCE);pre_profile=database._database_profile(database.SOURCE)
        dump.dump(database.SOURCE,PRE_DUMP);pre_dumped=True
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            state=p21_install_cycle(cur,report);installed=True;new_roles=database._roles(cur)-before_roles;conn.commit()
            granted,seeded=database._foundation(cur)
            today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
            legacy_prepare(cur,today,report)
            fixtures=[prepare(cur,today,index,gold)for index in range(2)]
            legacy_use(cur,today,report)
            mandor=mandor_fixture.prepare(cur,today)
            report['ow05_steps']=[dict(step=OW05_STEPS[0],status='PASS',new_wage_and_nota='24.00',old_work_retained=True)]
            cur.execute('set constraints all immediate')
            if granted:cur.execute('revoke usage on schema erp from authenticated')
            conn.commit();product.verify(cur,state)
            # Take the trusted business read baseline on the source after both
            # fixtures and their account choices exist, before dump/restore.
            for index,item in enumerate(fixtures):
                actual=read(cur,item,'SOURCE_AFTER_BOTH_COMMITTED')
                report.setdefault('source_baseline_changes',[]).append(dict(fixture=index,
                    changed_paths=differences(item['before_read'],actual)))
                assert actual['profile']==gold['before_restore_profiles'][index]
                item['before_read']=actual
            held=product.predecessor.base.private_rows(cur)
            try:product.rollback_preuse(cur,state)
            except ValueError as error:assert str(error)=='CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE'
            else:raise AssertionError('CURRENT_USED_INSTALLATION_WAS_UNINSTALLED')
            assert product.predecessor.base.private_rows(cur)==held;conn.rollback()
            report['steps'].append(dict(step=gold['required_steps'][0],status='PASS',actual_committed_business_chains=2,
                fixture_modes=gold['fixture_actions'],before_restore_profiles=gold['before_restore_profiles'],
                used_removal_refused_before_mutation=True,administrative_fixture_seeded=seeded,test_usage_grant_revoked=granted))
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            cur.execute("set local timezone='UTC'")
            mandor_before=mandor_fixture.read(cur,mandor);conn.rollback()
        used_data=drill.data_hashes(database.SOURCE);used_profile=database._database_profile(database.SOURCE)
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            backup,digest=restore.export_manifest(cur,state);dump.dump(database.SOURCE,USED_DUMP);conn.rollback()
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.with_name('PAYMENT_USED_RESTORE_MANIFEST.json').write_text(json.dumps(backup,indent=2)+'\n')
        report['trusted_backup_manifest_sha256']=digest
        restored=database._restore(USED_DUMP,database.RESTORED,used_profile)
        assert restored['only_pg_cron_errors'],restored
        assert drill.data_hashes(database.RESTORED)==used_data
        report['steps'].append(dict(step=gold['required_steps'][1],status='PASS',restore=restored,
            every_table_hash_equal=True,table_count=len(used_data),every_catalog_data_and_sequence_bound=True))
        with psycopg.connect(drill.url(database.RESTORED))as conn,conn.cursor()as cur:
            cur.execute("set local timezone='UTC';set local statement_timeout='240s';set local lock_timeout='8s'")
            cur.execute('savepoint raw_oid_guard')
            try:cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
            except psycopg.errors.RaiseException as error:
                assert error.diag.message_primary=='CP7_CREDIT_SOURCE_NATIVE_TRIGGER_CENSUS_CHANGED';cur.execute('rollback to savepoint raw_oid_guard')
            else:raise AssertionError('CURRENT_RESTORE_OLD_LOCAL_OID_SEAL_UNEXPECTEDLY_ACCEPTED')
            cur.execute('release savepoint raw_oid_guard')
            controls=refusal_controls(cur,backup,digest,report.setdefault('restore_controls',[]),fixtures[0]['consumer_requests'][0])
            report['steps'].append(dict(step=gold['required_steps'][2],status='PASS',original_raw_oid_guard_refused=True,controls=controls))
            rebound=restore.rebind_restored(cur,backup,digest,expected_database=database.RESTORED);conn.commit()
            report['steps'].append(dict(step=gold['required_steps'][3],status='PASS',binding=rebound))
            granted,_=database._foundation(cur)
            for index,item in enumerate(fixtures):
                actual=read(cur,item,'FRESH_RESTORED');wanted=item['before_read']
                changed=differences(wanted,actual)
                report.setdefault('readback_comparisons',[]).append(dict(fixture=index,
                    expected=wanted,actual=actual,changed_paths=changed))
                assert not changed,'CURRENT_RESTORE_AUTHORITATIVE_BUSINESS_READ_CHANGED: '+json.dumps(changed)
            assert mandor_fixture.read(cur,mandor)==mandor_before,'OW05_RESTORED_BUSINESS_READ_CHANGED'
            held=restore.catalog._data(cur)
            mandor_fixture.replay(cur,mandor)
            assert restore.catalog._data(cur)==held,'OW05_RESTORED_REPLAY_CHANGED_DATA_OR_SEQUENCE'
            report['ow05_steps'].append(dict(step=OW05_STEPS[1],status='PASS',all_raw_business_reads_equal=True,four_original_receipts_replayed=True,every_table_and_sequence_unchanged=True))
            for item in fixtures:
                for envelope,request,result in zip(item['consumer_envelopes'],item['consumer_requests'],item['consumers']):
                    assert basic.command(cur,envelope,request)==result
                assert payment.correct(cur,item['down'],item['down_version'],item['down_request'])==item['down_result']
                assert payment.correct(cur,item['up'],item['up_version'],item['up_request'])==item['up_result']
            assert restore.catalog._data(cur)==held
            report['steps'].append(dict(step=gold['required_steps'][4],status='PASS',exact_authoritative_reads=True,
                original_P1000_P900_facts_unchanged=True,old_and_current_eight_receipts_replayed=True,every_table_and_sequence_unchanged=True))
            results=[]
            for item in fixtures:
                pair=item['pair']
                for event in reversed(item['consumers']):
                    envelope=basic.review(cur,basic.payload(pair,'UNDO',original=event['consumption_event_id']))
                    result=basic.command(cur,envelope,uuid.uuid4());assert result['restores_event_id']==event['consumption_event_id']
                payload,version=basic.fixture.signed._intent(cur,pair['source'],pair['initial_result'],'RETURN_REVERSE');request=uuid.uuid4()
                result=basic.native.cmd.command(cur,'RETURN_REVERSE',payload,version,request);assert result['return_status']=='REVERSED'
                actual=profile(cur,pair);assert actual==gold['after_all_named_undos_and_return_inverse']
                for ident,journal in item['consumer_journals'].items():assert basic.native.journal(cur,ident)==journal
                assert payment.payment_fact(cur,pair['source']['f']['payment'])==item['before_read']['original_P1000']
                assert payment.payment_fact(cur,item['down_result']['payment_id'])==item['before_read']['original_P900']
                for op, in cur.execute('select operation_id from cp7_credit.source_operation_materializations_v1 where sale_id=%s',(pair['source']['f']['sale'],)).fetchall():
                    cur.execute('select cp7_credit.assert_source_operation_closed_v1(%s)',(op,))
                held=restore.catalog._data(cur);assert basic.native.cmd.command(cur,'RETURN_REVERSE',payload,version,request)==result
                assert restore.catalog._data(cur)==held;results.append(dict(observed=actual,expected=gold['after_all_named_undos_and_return_inverse']))
            cur.execute('set constraints all immediate')
            if granted:cur.execute('revoke usage on schema erp from authenticated')
            conn.commit()
            mandor_inverse=mandor_fixture.inverses(cur,mandor)
            cur.execute('set constraints all immediate');conn.commit()
            report['ow05_steps'].append(dict(step=OW05_STEPS[2],**mandor_inverse))
            report['steps'].append(dict(step=gold['required_steps'][5],status='PASS',both_actual_inverse_outcomes=results,
                exact_named_undos=True,source_operations_closed=True,old_payments_and_consumer_journals_retained=True,source_inverse_replay_one_effect=True))
        report['runtime_status']='PASS'
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        drill.docker('dropdb','-U','supabase_admin','--if-exists','--force',database.RESTORED,check=False)
        if installed and pre_dumped:
            try:
                restored=database._restore(PRE_DUMP,database.SOURCE,pre_profile);assert restored['only_pg_cron_errors'],restored
                assert drill.data_hashes(database.SOURCE)==pre_data
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    for role in sorted(new_roles):cur.execute(sql.SQL('drop role {}').format(sql.Identifier(role)))
                    conn.commit();assert database._roles(cur)==before_roles
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['baseline_restore']=restored
                report['baseline_advisors_equal']=advisors(package.boundary.PG)==report['baseline_advisors']
            except Exception as error:report.update(cp6_restored=False,restore_error=str(error),restore_traceback=traceback.format_exc())
        elif before is not None and pre_dumped:
            # A failed install cycle has not committed. Prove the caller's
            # transaction rollback independently, without claiming a dump was
            # restored or marking any unexecuted P21 step as passed.
            try:
                assert drill.data_hashes(database.SOURCE)==pre_data
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    assert database._roles(cur)==before_roles
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['baseline_restore']=dict(status='UNCOMMITTED_INSTALL_CYCLE_ROLLED_BACK',
                    dump_restoration_executed=False,data_and_roles_exact=True)
                report['baseline_advisors_equal']=advisors(package.boundary.PG)==report['baseline_advisors']
            except Exception as error:report.update(cp6_restored=False,restore_error=str(error),restore_traceback=traceback.format_exc())
        for path in(PRE_DUMP,USED_DUMP):drill.docker('rm','-f',path,check=False)
        required=[row['step']for row in report['steps']]==gold['required_steps']and all(row['status']=='PASS'for row in report['steps'])
        report['required_steps_pass']=required
        report['p21_adapter_steps_pass']=tuple(r['step']for r in report.get('p21_adapter_steps',[]))==P21_STEPS and all(r['status']=='PASS'for r in report.get('p21_adapter_steps',[]))
        report['ow05_steps_pass']=tuple(r['step']for r in report.get('ow05_steps',[]))==OW05_STEPS and all(r['status']=='PASS'for r in report.get('ow05_steps',[]))
        if report.get('ow05_steps_pass')and report.get('runtime_status')=='PASS'and required and report.get('cp6_restored')and report.get('baseline_advisors_equal')and not report.get('error')and report.get('p21_adapter_steps_pass')and report.get('default_P21_entrypoint_exercised'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('label','status','runtime_status','required_steps_pass','cp6_restored','baseline_advisors_equal','error','restore_error')}),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)

def main():
    admitted()
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
    return 0
