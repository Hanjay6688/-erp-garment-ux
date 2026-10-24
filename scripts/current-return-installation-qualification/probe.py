"""Committed sibling-return delta, full fresh restore, and next Native operation."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os,subprocess,sys,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
spec=importlib.util.spec_from_file_location('draft_isolation_predecessor',REPO/'scripts/draft-return-isolation-qualification/probe.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
import cp7_current_return_recovery as recovery
import cp7_current_return_installation as composed
a=prior.chain
delta,installation,business=prior.delta,prior.installation,prior.business
old=business.old
catalog=delta.catalog
database,drill,dump,package=a.database,a.drill,a.dump,a.package
psycopg,sql=a.psycopg,a.sql
LABEL='CP7_CURRENT_RETURN_INSTALLATION_RESTORE'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
PRE_DUMP='/tmp/current_return_pre.dump'
USED_DUMP='/tmp/current_return_used.dump'
STEPS=('EXACT_INSTALL_AND_PREUSE_INVERSE','COMMITTED_VALID_RETURN_WITH_MALFORMED_DRAFT',
       'USED_INVERSE_REFUSED_BEFORE_DDL','FULL_USED_BACKUP_RESTORED',
       'RESTORE_NEGATIVE_CONTROLS','FULL_RESTORE_AFTER_NEGATIVE_WRITE','ONLY_LOCAL_NATIVE_OID_SEAL',
       'EXACT_FINANCIAL_READS_AND_NEXT_VALID_RETURN')


def admitted():
    predecessor=prior.admitted()
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('DRAFT_RESTORE_SOURCE_CHANGED',path)
    assert pins['required_steps']==list(STEPS)
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE)],text=True).strip()
    observations=[]
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw)
        assert actual['status']=='PASS'and actual['cp6_restored']and actual['baseline_advisors_equal']
        files=actual['source_declaration']['qualification']['files']
        for path in ('scripts/cp7_current_installation.py','scripts/cp7_draft_return_isolation.py'):
            assert files[path]==sha256((REPO/path).read_bytes()).hexdigest()
        if variable=='DRAFT_RETURN_CLOSURE_ORIGINAL_REPORT':
            assert actual['native']['counts']=={'PASS':32}and actual['baseline_all22_rows_sequences_exact']and actual['advisor_gate']
        else:
            assert actual['required_steps_pass']and len(actual['steps'])==8
            assert actual['source_declaration']['recovery']==recovery.recovery.sources()
        observations.append(dict(variable=variable,sha256=proof['sha256'],status='PASS'))
    return dict(predecessor=predecessor,qualification=pins,recovery=recovery.sources(),
        current_installation=composed.sources(),actual_qualifications_verified=observations)


def controls(cur,backup,digest,rid,customer):
    results=[]
    def refused(name,fn,prefix):
        cur.execute('savepoint restore_fault')
        try:fn()
        except ValueError as error:
            assert str(error).startswith(prefix),(name,str(error))
            results.append(dict(id=name,status='PASS',refusal=str(error).split(':',1)[0]))
        else:raise AssertionError('DRAFT_RESTORE_UNSAFE_BINDING_ACCEPTED: '+name)
        finally:
            cur.execute('rollback to savepoint restore_fault');cur.execute('release savepoint restore_fault')
        actual=catalog._data(cur)
        changes={k:dict(before=backup['product_backup']['data'].get(k),after=actual.get(k))for k in set(actual)|set(backup['product_backup']['data'])if actual.get(k)!=backup['product_backup']['data'].get(k)}
        if name=='DRAFT_ROW_DRIFT':
            # Native audit sequences are nontransactional. This intentional
            # write fault is isolated by a second full restore, never setval.
            assert all(k.startswith('sequence:')for k in changes),('NEGATIVE_WRITE_PERSISTED_ROWS',changes)
            results[-1]['savepoint_sequence_changes']=changes
            results[-1]['requires_full_restore_before_binding']=True
        else:assert not changes,(name,changes)
        assert catalog._portable(catalog._catalog_rows(cur))==catalog._portable(backup['product_backup']['catalog'])
    def bind(b=backup,h=digest,db=database.RESTORED):
        return recovery.rebind_restored(cur,b,h,expected_database=db)
    refused('WRONG_TRUSTED_HASH',lambda:bind(h='0'*64),'CURRENT_RETURN_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    changed=deepcopy(backup);changed['sources']['current_installation']['entrypoint_sha256']='0'*64
    refused('CHANGED_COMPOSED_ENTRYPOINT_SOURCE',lambda:bind(changed,catalog.digest(changed)),'CURRENT_RETURN_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    refused('WRONG_DATABASE',lambda:bind(db=database.SOURCE),'DRAFT_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED')
    wrong_inner=deepcopy(backup);wrong_inner['product_backup_sha256']='0'*64
    refused('WRONG_INNER_BACKUP_HASH',lambda:bind(wrong_inner,catalog.digest(wrong_inner)),'DRAFT_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    missing=deepcopy(backup);del missing['product_backup']['catalog']['sequence_ownership']
    missing['product_backup_sha256']=catalog.digest(missing['product_backup'])
    refused('MISSING_CATALOG_GROUP',lambda:bind(missing,catalog.digest(missing)),'DRAFT_RESTORE_CATALOG_CHANGED')
    def metadata():
        cost=cur.execute('select procost::numeric from pg_proc where oid=%s::regprocedure',(delta.SIGNATURE,)).fetchone()[0]
        cur.execute(sql.SQL('alter function '+delta.SIGNATURE+' cost {}').format(sql.Literal(cost+1)))
        held=catalog._catalog_rows(cur);data=catalog._data(cur)
        try:bind()
        finally:assert catalog._catalog_rows(cur)==held and catalog._data(cur)==data
    refused('DELTA_FUNCTION_METADATA_DRIFT',metadata,'DRAFT_RESTORE_CATALOG_CHANGED')
    def row():
        cur.execute('update erp.sales_returns set customer_id=%s where id=%s',(customer,rid));assert cur.rowcount==1
        held=catalog._catalog_rows(cur);data=catalog._data(cur)
        try:bind()
        finally:assert catalog._catalog_rows(cur)==held and catalog._data(cur)==data
    refused('DRAFT_ROW_DRIFT',row,'DRAFT_RESTORE_BUSINESS_ROWS_OR_SEQUENCE_CHANGED')
    return results


def run():
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        candidate_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        required_steps=list(STEPS),steps=[],production_go=False,independent_acceptance=False,hosted=False,
        original_legacy_results_relabelled=False,new_business_case_credit=0)
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
            state=composed.install(cur);composed.verify(cur,state)
            inverse=composed.rollback_preuse(cur,state)
            state=composed.install(cur);patch=state['delta'];composed.verify(cur,state)
            new_roles=database._roles(cur)-before_roles;conn.commit();installed=True
            step(STEPS[0],inverse=inverse,composed=composed.verify(cur,state))
            granted,seeded=database._foundation(cur)
            today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
            day=today-timedelta(days=3);fixture={}
            old.fixture.prepare(cur,today,current=True,closed_through=day-timedelta(days=5),evidence=fixture)
            business.PATCHED=True
            f,rid,bad_draft=business.malformed(cur,day)
            refused=business.customer_refusal(cur,rid)
            good=old.positive_return(cur,day,f)
            old.actors.admin(cur)
            source_before=business.source(cur,f['sale']['sale_id'])
            assert cur.execute('select to_jsonb(r)from erp.sales_returns r where id=%s',(rid,)).fetchone()[0]==bad_draft
            cur.execute('set constraints all immediate')
            if granted:cur.execute('revoke usage on schema erp from authenticated')
            conn.commit();composed.verify(cur,state)
            step(STEPS[1],fixture=fixture,foundation_seeded=seeded,malformed_draft=bad_draft,
                invalid_selected_return=refused,legitimate_sibling=good,source_before=source_before)
            report['quiesce_used']=a.quiesce(cur);assert report['quiesce_used']['clear']
            held=catalog._data(cur);held_catalog=catalog._catalog_rows(cur)
            try:composed.rollback_preuse(cur,state)
            except ValueError as error:assert str(error)==delta.USED_ERROR
            else:raise AssertionError('USED_DELTA_REMOVED')
            assert catalog._data(cur)==held and catalog._catalog_rows(cur)==held_catalog
            conn.rollback();step(STEPS[2],all_rows_sequences_and_full22_unchanged=True)
        used_data=drill.data_hashes(database.SOURCE);used_profile=database._database_profile(database.SOURCE)
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            backup,digest=recovery.export_manifest(cur,state)
            dump.dump(database.SOURCE,USED_DUMP);conn.rollback()
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.with_name('DRAFT_RETURN_USED_RESTORE_MANIFEST.json').write_text(json.dumps(backup,indent=2)+'\n')
        restored=database._restore(USED_DUMP,database.RESTORED,used_profile)
        assert restored['only_pg_cron_errors']and drill.data_hashes(database.RESTORED)==used_data
        step(STEPS[3],all_table_hashes_equal=True,trusted_manifest_sha256=digest,restore=restored)
        with psycopg.connect(drill.url(database.RESTORED))as conn,conn.cursor()as cur:
            cur.execute("set local timezone='UTC';set local statement_timeout='240s';set local lock_timeout='8s'")
            cur.execute('savepoint old_census')
            try:cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
            except psycopg.errors.RaiseException as error:
                assert error.diag.message_primary=='CP7_CREDIT_SOURCE_NATIVE_TRIGGER_CENSUS_CHANGED'
                cur.execute('rollback to savepoint old_census')
            else:raise AssertionError('OLD_LOCAL_OID_CENSUS_ACCEPTED')
            cur.execute('release savepoint old_census')
            step(STEPS[4],old_census_refused=True,controls=controls(cur,backup,digest,rid,f['customers'][0]))
            conn.rollback()
        # Drop the negative-test clone and restore the complete trusted used
        # backup again. No local sequence reset or projected state is allowed.
        restored_after_fault=database._restore(USED_DUMP,database.RESTORED,used_profile)
        assert restored_after_fault['only_pg_cron_errors']and drill.data_hashes(database.RESTORED)==used_data
        step(STEPS[5],all_table_hashes_equal=True,restore=restored_after_fault)
        with psycopg.connect(drill.url(database.RESTORED))as conn,conn.cursor()as cur:
            cur.execute("set local timezone='UTC';set local statement_timeout='240s';set local lock_timeout='8s'")
            assert catalog._data(cur)==backup['product_backup']['data'],'SECOND_RESTORE_ROWS_OR_SEQUENCES_CHANGED'
            assert catalog._portable(catalog._catalog_rows(cur))==catalog._portable(backup['product_backup']['catalog']),'SECOND_RESTORE_FULL22_CHANGED'
            rebound=recovery.rebind_restored(cur,backup,digest,expected_database=database.RESTORED)
            sealed_catalog=catalog._catalog_rows(cur)
            conn.commit();step(STEPS[6],receipt=rebound)
            granted,_=database._foundation(cur)
            after=business.source(cur,f['sale']['sale_id'])
            assert after==source_before,'RESTORED_SOURCE_FINANCIAL_OR_DEPENDENCY_STATE_CHANGED'
            assert cur.execute('select to_jsonb(r)from erp.sales_returns r where id=%s',(rid,)).fetchone()[0]==bad_draft
            refused_after=business.customer_refusal(cur,rid)
            second=old.positive_return(cur,day,f);old.actors.admin(cur)
            assert cur.execute('select to_jsonb(r)from erp.sales_returns r where id=%s',(rid,)).fetchone()[0]==bad_draft
            totals=cur.execute("select count(*),sum(i.qty_pcs),sum(i.refund_amount)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=%s and r.status='POSTED'",(f['sale']['sale_id'],)).fetchone()
            assert totals==(2,2,Decimal('40.00')),totals
            cur.execute('set constraints all immediate')
            if granted:cur.execute('revoke usage on schema erp from authenticated')
            assert catalog._catalog_rows(cur)==sealed_catalog
            conn.commit();step(STEPS[7],exact_full_source_state=True,malformed_draft_unchanged=True,
                invalid_selected_return=refused_after,next_valid_return=second,posted_count_qty_refund=totals,
                all_catalog_and_permissions_unchanged=True)
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
    return dict(status=report['status'],production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
