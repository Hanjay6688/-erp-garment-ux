"""Mandatory complete B-extension composition/restore preflight, not Native286.

Real committed A supplier payment and B six-decimal fabric policy, complete
preuse inverse, used-state refusal before DDL, full dump/restore, exact replay.
No hosted connection, browser, schedule or production admission is claimed.
"""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json,subprocess,sys,traceback,uuid

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import cp7_p21_current_chain_rehearsal_probe as a
from cp7_ab_quote_chain import composition as product,recovery
import cp7_ow14b_rule_cases as fabric

catalog=product.catalog
database,drill,dump,package=a.database,a.drill,a.dump,a.package
psycopg,sql=a.psycopg,a.sql
LABEL='CP7_AB_QUOTE_CHAIN_RESTORE'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
PRE_DUMP='/tmp/AB_quote_pre.dump'
USED_DUMP='/tmp/AB_quote_used.dump'
STEPS=('INSTALL_ALL22','PREUSE_EXACT_RESTORE','REINSTALL_ALL22',
       'COMMITTED_A_PAYMENT_B_FABRIC','GLOBAL_USED_GUARD_BEFORE_DDL',
       'FULL_USED_BACKUP_RESTORED','RESTORE_NEGATIVE_CONTROLS',
       'LOCAL_OID_BINDING_ONLY','EXACT_A_B_READS_AND_UUID_REPLAY')


def admitted():
    predecessor,_=a.admitted()
    guard_path=REPO/'scripts/cp7_customer_credit/integration/source_triggers/trigger_guard.py'
    import importlib.util
    spec=importlib.util.spec_from_file_location('ow15_preflight_trigger_source_guard',guard_path)
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    guard.declarations(REPO)  # Fail before DB if a pinned predecessor harness moved.
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('PRODUCTION_CHAIN_SOURCE_CHANGED',path)
    assert pins['required_steps']==list(STEPS)
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE),
        'scripts/cp7_ab_quote_chain'],text=True).strip()
    return dict(A_source_binding=predecessor,production_stage=product.predecessor.predecessor.stage.verify_sources(),
        qualification=pins,Native286_rerun_here=False)


def controls(cur,backup,digest,material):
    results=[]
    def refused(name,action,prefix):
        cur.execute('savepoint production_restore_fault')
        try:action()
        except ValueError as error:
            assert str(error).startswith(prefix),(name,str(error))
            results.append(dict(id=name,status='PASS',refusal=str(error).split(':',1)[0]))
        else:raise AssertionError('PRODUCTION_CHAIN_UNSAFE_RESTORE_ACCEPTED: '+name)
        finally:
            cur.execute('rollback to savepoint production_restore_fault')
            cur.execute('release savepoint production_restore_fault')
    refused('WRONG_TRUSTED_HASH',lambda:recovery.rebind_restored(cur,backup,'0'*64,
        expected_database=database.RESTORED),'CHAIN_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    changed=deepcopy(backup);changed['sources']['financial_product']['composition_sha256']='0'*64
    refused('CHANGED_COMPOSED_SOURCE',lambda:recovery.rebind_restored(cur,changed,catalog.digest(changed),
        expected_database=database.RESTORED),'CHAIN_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    refused('WRONG_DATABASE',lambda:recovery.rebind_restored(cur,backup,digest,
        expected_database=database.SOURCE),'CHAIN_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED')
    def metadata():
        sig='cp7_stock_formula.save_material(jsonb,uuid)'
        cost=cur.execute('select procost::numeric from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()[0]
        cur.execute(sql.SQL('alter function cp7_stock_formula.save_material(jsonb,uuid) cost {}').format(sql.Literal(cost+1)))
        recovery.rebind_restored(cur,backup,digest,expected_database=database.RESTORED)
    refused('B_FUNCTION_METADATA_DRIFT',metadata,'CHAIN_RESTORE_CATALOG_CHANGED')
    def row():
        cur.execute('update cp7_stock_formula.material_evaluations set point=point+1 where material_id=%s',(material,))
        assert cur.rowcount==1
        recovery.rebind_restored(cur,backup,digest,expected_database=database.RESTORED)
    refused('B_EVALUATION_ROW_DRIFT',row,'CHAIN_RESTORE_BUSINESS_ROWS_OR_SEQUENCE_CHANGED')
    assert catalog._data(cur)==backup['data']
    assert catalog._portable(catalog._catalog_rows(cur))==catalog._portable(backup['catalog'])
    return results


def run():
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        required_steps=list(STEPS),steps=[],mandatory_preflight_only=True,Native286_rerun=False,
        declared_B_stages_installed=True,all_owner_scope_completed=False,full_AB_chain_qualified=False,real_Auth_browser_claim=False,
        production_go=False,independent_acceptance=False,hosted=False)
    before=None;before_roles=set();new_roles=set();pre_dumped=False;installed=False
    def step(name,**values):report['steps'].append(dict(step=name,status='PASS',**values))
    try:
        assert drill.SOURCE==database.SOURCE=='cp6_rollback'and drill.CONTAINER=='supabase_db_cp5-local'
        report['baseline_advisors']=a.advisors(package.boundary.PG)
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            assert conn.info.host in('127.0.0.1','localhost')and cur.execute('select current_database()').fetchone()==(database.SOURCE,)
            a.p09.wip.policy.bf.verified(cur);before_roles=database._roles(cur)
            before=a.previous.restore_state.capture(cur,package.boundary.snapshot,a.core.predecessor.public_state,a.p09.functions)
            conn.rollback()
        pre_data=drill.data_hashes(database.SOURCE);pre_profile=database._database_profile(database.SOURCE)
        dump.dump(database.SOURCE,PRE_DUMP);pre_dumped=True
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            before_catalog=catalog._catalog_rows(cur);before_rows=catalog._data(cur)
            state=product.install(cur);step(STEPS[0],proof=product.verify(cur,state),quote_truth_table=state['truth_table'])
            report['quiesce_preuse']=a.quiesce(cur);assert report['quiesce_preuse']['clear']
            removed=product.rollback_preuse(cur,state)
            assert catalog._catalog_rows(cur)==before_catalog and catalog._data(cur)==before_rows
            step(STEPS[1],all22_catalog_data_sequences_exact=True,receipt=removed)
            state=product.install(cur);product.verify(cur,state)
            new_roles=database._roles(cur)-before_roles;conn.commit();installed=True
            step(STEPS[2],all22_verified=True)
            granted,seeded=database._foundation(cur)
            today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
            f=dump.create.funded(cur,today);payload=dump.create.payload(cur,f,'100.00');key=uuid.uuid4()
            payment=dump.create.command(cur,payload,key)
            assert payment['status']=='POSTED'and payment['remaining_after']=='900.00'
            g=fabric.factory(cur,today,history=False,minimum='500.123456')
            owner=fabric.master.role_actor(cur,'OWNER');policy=fabric.payload(g,rule='LEGACY_MINIMUM',reference='500.123456');policy_key=uuid.uuid4()
            business=fabric.formula.business(cur);saved=fabric.save(cur,policy,policy_key,owner)
            assert saved['revision']==1 and saved['evaluation']['fabric_rule']=='LEGACY_MINIMUM'
            assert Decimal(str(saved['evaluation']['point']))==Decimal('500.123456')
            assert fabric.formula.business(cur)==business,'B_POLICY_CHANGED_NATIVE_FINANCE_OR_STOCK'
            payment_before=dump.create.state(cur,f);policy_before=fabric.formula.material_evaluation(cur,g['material'])
            cur.execute('set constraints all immediate')
            if granted:cur.execute('revoke usage on schema erp from authenticated')
            conn.commit();product.verify(cur,state)
            step(STEPS[3],supplier_paid='100.00',supplier_remaining='900.00',fabric_rule='LEGACY_MINIMUM',
                exact_point='500.123456',B_policy_no_ERP_business_DML=True,foundation_fixture=seeded)
            report['quiesce_used']=a.quiesce(cur);assert report['quiesce_used']['clear']
            held=catalog._data(cur);held_catalog=catalog._catalog_rows(cur)
            try:product.rollback_preuse(cur,state)
            except ValueError as error:assert str(error)==product.USED_ERROR
            else:raise AssertionError('PRODUCTION_CHAIN_USED_INSTALLATION_REMOVED')
            assert catalog._data(cur)==held and catalog._catalog_rows(cur)==held_catalog
            conn.rollback();step(STEPS[4],all_rows_sequences_and_all22_unchanged=True)
        used_data=drill.data_hashes(database.SOURCE);used_profile=database._database_profile(database.SOURCE)
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            backup,digest=recovery.export_manifest(cur,state);dump.dump(database.SOURCE,USED_DUMP);conn.rollback()
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.with_name('AB_QUOTE_USED_RESTORE_MANIFEST.json').write_text(json.dumps(backup,indent=2)+'\n')
        restored=database._restore(USED_DUMP,database.RESTORED,used_profile)
        assert restored['only_pg_cron_errors']and drill.data_hashes(database.RESTORED)==used_data
        step(STEPS[5],all_table_hashes_equal=True,trusted_manifest_sha256=digest,restore=restored)
        with psycopg.connect(drill.url(database.RESTORED))as conn,conn.cursor()as cur:
            cur.execute("set local timezone='UTC';set local statement_timeout='240s';set local lock_timeout='8s'")
            cur.execute('savepoint old_census')
            try:cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
            except psycopg.errors.RaiseException as error:
                assert error.diag.message_primary=='CP7_CREDIT_SOURCE_NATIVE_TRIGGER_CENSUS_CHANGED'
                cur.execute('rollback to savepoint old_census')
            else:raise AssertionError('OLD_LOCAL_OID_CENSUS_ACCEPTED')
            cur.execute('release savepoint old_census')
            step(STEPS[6],old_census_refused=True,controls=controls(cur,backup,digest,g['material']))
            rebound=recovery.rebind_restored(cur,backup,digest,expected_database=database.RESTORED)
            product.predecessor.checked.verify(cur,state['predecessor']['stages'][-1]['state'])
            assert catalog._catalog_rows(cur)['functions'][product.quote.SIGNATURE]==state['after']['functions'][product.quote.SIGNATURE]
            conn.commit();step(STEPS[7],receipt=rebound,quote_definition_metadata_exact=True)
            granted,_=database._foundation(cur)
            assert dump.create.state(cur,f)==payment_before
            assert fabric.formula.material_evaluation(cur,g['material'])==policy_before
            held=catalog._data(cur)
            assert dump.create.command(cur,payload,key)==payment
            assert fabric.save(cur,policy,policy_key,owner)==dict(replay=True,material_id=g['material'],revision=1)
            assert catalog._data(cur)==held
            assert fabric.formula.refused(cur,lambda:fabric.save(cur,dict(policy,fabric_rule='FORMULA'),policy_key,owner))==('22023','CP7_FORMULA_REQUEST_REUSED')
            assert catalog._data(cur)==held
            if granted:cur.execute('revoke usage on schema erp from authenticated')
            conn.commit();step(STEPS[8],A_and_B_authoritative_reads_exact=True,same_UUID_no_second_effect=True,changed_policy_payload_refused=True)
        report['runtime_status']='PASS'
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        drill.docker('dropdb','-U','supabase_admin','--if-exists','--force',database.RESTORED,check=False)
        if before is not None and pre_dumped:
            try:
                if installed:
                    restored=database._restore(PRE_DUMP,database.SOURCE,pre_profile);assert restored['only_pg_cron_errors']
                    report['baseline_restore']=restored
                assert drill.data_hashes(database.SOURCE)==pre_data
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    for role in sorted(new_roles):cur.execute(sql.SQL('drop role {}').format(sql.Identifier(role)))
                    conn.commit();assert database._roles(cur)==before_roles
                    report['cp6_restored']=a.previous.restore_state.prove(cur,before,package.boundary.snapshot,a.core.predecessor.public_state,a.p09.functions,report)
                    conn.rollback();a.p09.wip.policy.bf.verified(cur);conn.rollback()
                report['baseline_advisors_equal']=a.advisors(package.boundary.PG)==report['baseline_advisors']
            except Exception as error:report.update(cp6_restored=False,restore_error=str(error),restore_traceback=traceback.format_exc())
        for path in(PRE_DUMP,USED_DUMP):drill.docker('rm','-f',path,check=False)
        report['required_steps_pass']=tuple(row['step']for row in report['steps'])==STEPS and all(row['status']=='PASS'for row in report['steps'])
        if report.get('runtime_status')=='PASS'and report['required_steps_pass']and report.get('cp6_restored')and report.get('baseline_advisors_equal')and not report.get('error'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('label','status','required_steps_pass','cp6_restored','baseline_advisors_equal','error','restore_error')}),flush=True)
    return dict(status=report['status'],production_go=False,full_AB_chain_qualified=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
