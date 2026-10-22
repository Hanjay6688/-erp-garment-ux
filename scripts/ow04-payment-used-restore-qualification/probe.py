"""Committed current payment/consumer chains through a full fresh DB restore."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import gzip,importlib.util,json,lzma,subprocess,sys,traceback,uuid
sys.dont_write_bytecode=True
if sys.argv[1:]:raise SystemExit('Current used-state restore accepts no arguments')
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path[:0]=[str(REPO/'scripts'),str(REPO/'scripts/cp7_customer_credit/consumer'),
 str(REPO/'scripts/ow04-payment-source-qualification')]
import source_probe as control
import native_basic_cases as basic
import native_refund_cases as refund
import cp7_payment_correction_cases as payment
import cp7_payment_source_restore as restore
import cp7_p21_full_rehearsal_probe as dump
import cp6_t3_backup_restore_drill as drill
import psycopg
from psycopg import sql
from cp6_t3_aligned_install import advisors
spec=importlib.util.spec_from_file_location('current_restore_database',HERE/'restore_database.py')
database=importlib.util.module_from_spec(spec);spec.loader.exec_module(database)
product,previous,package,core,p09=control.product,control.previous,control.package,control.core,control.p09
database.core=core
LABEL='CP7_OW04_PAYMENT_CURRENT_USED_RESTORE'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
PRE_DUMP='/tmp/ow04_payment_pre.dump'
USED_DUMP='/tmp/ow04_payment_used.dump'
EXPECTED_SHA256='643081adcec37ffd3c4d83c25e7522522da634e81cb8af551796202c16bc2cf9'
READ_OBSERVATIONS=[]


def admitted():
    declaration=json.loads((HERE/'SOURCE.json').read_bytes())
    assert declaration['base_candidate']=='272bebdde544dfe4e187e20bae661d21316c79f7'
    assert declaration['product_sources']==product.sources()
    assert declaration['restore_sources']==restore.sources()
    for path,digest in declaration['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('CURRENT_USED_RESTORE_SOURCE_CHANGED',path)
    changed=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',declaration['base_candidate'],'HEAD',
        '--','scripts','src','supabase','tests','.github/workflows'],text=True).splitlines()
    assert set(changed)<=set(declaration['files'])|{'scripts/ow04-payment-used-restore-qualification/SOURCE.json'},changed
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',
        'scripts','src','supabase','tests','.github/workflows/cp7-ow04-payment-used-restore-current.yml'],text=True).strip()
    raw=lzma.decompress((REPO/'docs/cp7/d17-14/ow04/payment-native26-527ed740-pass/CP7_OW04_PAYMENT_SOURCE_NATIVE26_POSITIVE.json.xz').read_bytes())
    assert sha256(raw).hexdigest()=='4f2e6a3ec2d325d2b10a00abc823e1177a1c4e9dbbaa0445a397966d7dddab91'
    native=json.loads(raw)
    assert native['status']=='PASS'and native['native']['counts']=={'PASS':26}
    assert native['required_case_ids_pass']and native['cp6_restored']and native['advisor_gate']
    assert native['actual_financial_sources']==product.sources()
    first_raw=gzip.decompress((REPO/'docs/cp7/d17-14/ow04/payment-used-restore-5359767b-first/CP7_OW04_PAYMENT_CURRENT_USED_RESTORE.json.gz').read_bytes())
    assert sha256(first_raw).hexdigest()=='944e3a87be886f09835a32e4d95fc51662f2461056c8e4242f447d3b5721decd'
    first=json.loads(first_raw)
    assert first['status']=='INCOMPLETE'and 'LAST_ACTIVE_OWNER_PROTECTED'in first['error']
    assert first['cp6_restored']and first['baseline_advisors_equal']
    second_raw=gzip.decompress((REPO/'docs/cp7/d17-14/ow04/payment-used-restore-c3faae84-second/CP7_OW04_PAYMENT_CURRENT_USED_RESTORE.json.gz').read_bytes())
    assert sha256(second_raw).hexdigest()=='c60c186c567b107d36354ceebed84ed804e638c0f38070533262d37e7ee416d5'
    second=json.loads(second_raw)
    assert second['status']=='INCOMPLETE'and len(second['restore_controls'])==5
    assert all(row['status']=='PASS'for row in second['restore_controls'])
    assert second['cp6_restored']and second['baseline_advisors_equal']
    third_raw=gzip.decompress((REPO/'docs/cp7/d17-14/ow04/payment-used-restore-5f9ec874-third/CP7_OW04_PAYMENT_CURRENT_USED_RESTORE.json.gz').read_bytes())
    assert sha256(third_raw).hexdigest()=='4d66f1cca47ddfa366f4b1d7d2289472ccb41fbc8d83597bf3e5cc7cc05e476f'
    third=json.loads(third_raw)
    assert third['status']=='INCOMPLETE'and len(third['steps'])==4
    assert third['steps'][-1]['step']=='VERIFIED_CURRENT_CENSUS_REBIND'
    assert third['cp6_restored']and third['baseline_advisors_equal']
    gold=(HERE/'EXPECTED.json').read_bytes();assert sha256(gold).hexdigest()==EXPECTED_SHA256
    return dict(candidate=native['candidate_commit'],raw_sha256=sha256(raw).hexdigest(),
        actual_counts=native['native']['counts'],financial_source_equal=True),json.loads(gold)


def profile(cur,pair):
    values=basic.fixture.profiles(cur,pair);s,t=values['source'],values['target']
    return dict(source_net=s['net'],source_P=s['P'],I=s['I'],C=s['net_consumption'],
        available=s['available_credit'],source_AR=s['AR'],target_P=t['P'],target_U=t['U'],target_AR=t['AR'],cash=values['cash'])


def differences(expected,actual,path=''):
    if isinstance(expected,dict)and isinstance(actual,dict):
        return [value for key in sorted(set(expected)|set(actual))for value in differences(expected.get(key),actual.get(key),path+'.'+key)]
    if isinstance(expected,(list,tuple))and isinstance(actual,(list,tuple)):
        if len(expected)!=len(actual):return [path+'.length']
        return [value for index,(a,b)in enumerate(zip(expected,actual))for value in differences(a,b,path+'['+str(index)+']')]
    return []if expected==actual else[path]


def read(cur,item,phase='FIXTURE_PREPARATION'):
    pair=item['pair'];actual_profile=profile(cur,pair)
    before=cur.execute('select statement_timestamp()').fetchone()[0]
    workspace=payment.workspace(cur,pair['source']['f'],payment_id=item['up_result']['payment_id'])
    after=cur.execute('select statement_timestamp()').fetchone()[0]
    # Native's workspace contract sets this one observation field from
    # statement_timestamp(). Validate and retain it; it is not a transaction
    # physical/economic/book clock or a stored receipt/freshness token.
    captured=workspace.pop('captured_at')
    assert isinstance(captured,str)
    parsed=datetime.fromisoformat(captured.replace('Z','+00:00'))
    assert parsed.tzinfo is not None and before<=parsed<=after
    READ_OBSERVATIONS.append(dict(phase=phase,sale_id=str(pair['source']['f']['sale']),
        captured_at=captured,database_before=before.isoformat(),database_after=after.isoformat(),
        actual_observation_clock_verified=True))
    return dict(profile=actual_profile,workspace=workspace,
        original_P1000=payment.payment_fact(cur,pair['source']['f']['payment']),
        original_P900=payment.payment_fact(cur,item['down_result']['payment_id']))

def prepare(cur,today,index,gold):
    pair=basic.fixture.prepare(cur,today);source=pair['source']['f']
    use=basic.apply if index==0 else refund.refund
    first,first_envelope,first_request=use(cur,pair,'80.00')
    down,down_version=payment.payload(cur,source,amount='900.00');down_request=uuid.uuid4()
    down_result=payment.correct(cur,down,down_version,down_request)
    second,second_envelope,second_request=use(cur,pair,'20.00')
    up,up_version=payment.payload(cur,source,amount='1000.00',payment_id=down_result['payment_id']);up_request=uuid.uuid4()
    up_result=payment.correct(cur,up,up_version,up_request)
    assert profile(cur,pair)==gold['before_restore_profiles'][index]
    basic.native.b.api.admin(cur)
    item=dict(pair=pair,consumers=[first,second],consumer_envelopes=[first_envelope,second_envelope],
        consumer_requests=[first_request,second_request],down=down,down_version=down_version,
        down_request=down_request,down_result=down_result,up=up,up_version=up_version,up_request=up_request,up_result=up_result)
    item['before_read']=read(cur,item)
    item['consumer_journals']={r['journal_id']:basic.native.journal(cur,r['journal_id'])for r in item['consumers']}
    return item


def refusal_controls(cur,backup,digest,controls,request):
    def refused(name,call,message):
        cur.execute('savepoint restore_control')
        try:call()
        except ValueError as error:
            assert str(error).startswith(message),(name,str(error));controls.append(dict(id=name,status='PASS',error=str(error).split(':',1)[0]))
        else:raise AssertionError('CURRENT_RESTORE_UNSAFE_BINDING_ACCEPTED: '+name)
        finally:cur.execute('rollback to savepoint restore_control');cur.execute('release savepoint restore_control')
    refused('WRONG_TRUSTED_HASH',lambda:restore.rebind_restored(cur,backup,'0'*64,expected_database=database.RESTORED),'PAYMENT_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    changed=deepcopy(backup);changed['sources']['financial_product']['installer_sha256']='0'*64
    refused('CHANGED_FINANCIAL_SOURCE',lambda:restore.rebind_restored(cur,changed,restore.catalog.digest(changed),expected_database=database.RESTORED),'PAYMENT_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    refused('WRONG_TARGET_DATABASE',lambda:restore.rebind_restored(cur,backup,digest,expected_database='cp6_rollback'),'PAYMENT_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED')
    def metadata():
        cost=cur.execute("select procost::numeric from pg_proc where oid='cp7_credit.payment_source_historical_plan_ids_v1(jsonb)'::regprocedure").fetchone()[0]
        cur.execute(sql.SQL('alter function cp7_credit.payment_source_historical_plan_ids_v1(jsonb)cost {}').format(sql.Literal(cost+1)))
        restore.rebind_restored(cur,backup,digest,expected_database=database.RESTORED)
    refused('ACTUAL_FUNCTION_METADATA_DRIFT',metadata,'PAYMENT_RESTORE_CATALOG_CHANGED')
    def rows():
        # A real retained receipt is business data too. Its deferred guard is
        # rolled back with this savepoint; no audited Native master UPDATE or
        # nontransactional audit sequence is used by the fault fixture.
        cur.execute("update cp7_credit.consumer_requests_v1 set response=response||'{\"restore_fault\":true}'::jsonb where actor=%s and request_id=%s",(basic.native.auth.base.OPERATOR_AUTH,request));assert cur.rowcount==1
        restore.rebind_restored(cur,backup,digest,expected_database=database.RESTORED)
    refused('ACTUAL_BUSINESS_ROW_DRIFT',rows,'PAYMENT_RESTORE_BUSINESS_ROWS_OR_SEQUENCE_CHANGED')
    actual_data=restore.catalog._data(cur)
    residue={key:dict(expected=backup['data'].get(key),actual=actual_data.get(key))for key in set(actual_data)|set(backup['data'])if actual_data.get(key)!=backup['data'].get(key)}
    assert not residue,'RESTORE_CONTROL_ROLLBACK_DATA_OR_SEQUENCE_RESIDUE: '+json.dumps(residue,sort_keys=True)
    assert restore.catalog._portable(restore.catalog._catalog_rows(cur))==restore.catalog._portable(backup['catalog'])
    return controls


def run():
    native_binding,gold=admitted()
    report=dict(label=LABEL,status='INCOMPLETE',candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        scenario_id=gold['scenario_id'],expected_scenario_count=1,actual_Native26_binding=native_binding,
        current_financial_sources=product.sources(),administrative_restore_sources=restore.sources(),
        Native26_rerun=False,real_Auth_browser_not_claimed=True,formal_CP7C_started=False,
        qualification_only=True,hosted=False,production_go=False,feature_complete=False,steps=[],
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
            state=product.install(cur);installed=True;new_roles=database._roles(cur)-before_roles;conn.commit()
            granted,seeded=database._foundation(cur)
            today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
            fixtures=[prepare(cur,today,index,gold)for index in range(2)]
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
            held=product.base.private_rows(cur)
            try:product.rollback_preuse(cur,state)
            except ValueError as error:assert str(error)==product.predecessor.USED_ERROR
            else:raise AssertionError('CURRENT_USED_INSTALLATION_WAS_UNINSTALLED')
            assert product.base.private_rows(cur)==held;conn.rollback()
            report['steps'].append(dict(step=gold['required_steps'][0],status='PASS',actual_committed_business_chains=2,
                fixture_modes=gold['fixture_actions'],before_restore_profiles=gold['before_restore_profiles'],
                used_removal_refused_before_mutation=True,administrative_fixture_seeded=seeded,test_usage_grant_revoked=granted))
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
            held=restore.catalog._data(cur)
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
        for path in(PRE_DUMP,USED_DUMP):drill.docker('rm','-f',path,check=False)
        required=[row['step']for row in report['steps']]==gold['required_steps']and all(row['status']=='PASS'for row in report['steps'])
        report['required_steps_pass']=required
        if report.get('runtime_status')=='PASS'and required and report.get('cp6_restored')and report.get('baseline_advisors_equal')and not report.get('error'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('label','status','runtime_status','required_steps_pass','cp6_restored','baseline_advisors_equal','error','restore_error')}),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
