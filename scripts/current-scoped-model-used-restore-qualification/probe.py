"""Committed current A/B analog metadata, return, full fresh restore and next operations."""
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
sys.path.insert(0,str(HERE))
import fixture as native_fixture
import finance_fixture
import model_fixture
import target_fixture
import history_fixture
import scoped_model_fixture
spec=importlib.util.spec_from_file_location('draft_isolation_predecessor',REPO/'scripts/current-return-installation-qualification/probe.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
import cp7_current_scoped_model_recovery as recovery
import cp7_ow11_analog_choice_cases as analog
import cp7_current_scoped_model_installation as composed
history_composed=composed.predecessor
target_composed=history_composed.predecessor
from cp6_t3_aligned_install import advisor_delta
a=prior.a
delta,installation,business=prior.delta,prior.installation,prior.business
old=business.old
catalog=delta.catalog
choice=target_composed.predecessor.predecessor.predecessor.choice
database,drill,dump,package=a.database,a.drill,a.dump,a.package
psycopg,sql=a.psycopg,a.sql
LABEL='CP7_CURRENT_SCOPED_MODEL_USED_RESTORE8'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
PRE_DUMP='/tmp/current_scoped_model_pre.dump'
USED_DUMP='/tmp/current_scoped_model_used.dump'
STEPS=('EXACT_INSTALL_AND_PREUSE_INVERSE','COMMITTED_RETURN_AND_ANALOG_CHOICE',
       'USED_INVERSE_REFUSED_BEFORE_DDL','FULL_USED_BACKUP_RESTORED',
       'RESTORE_NEGATIVE_CONTROLS','FULL_RESTORE_AFTER_NEGATIVE_WRITE','ONLY_LOCAL_NATIVE_OID_SEAL',
       'EXACT_READS_REPLAY_CLEAR_AND_NEXT_RETURN')


def admitted():
    spec=importlib.util.spec_from_file_location('current_finance_model_used_restore_admission',HERE/'admission.py')
    admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
    return admission.admitted(REPO,HERE,STEPS,composed,recovery)


def acquire_boundary(cur):
    # Qualifier-owned bounded wait. The product's SHARE NOWAIT guard is unchanged.
    names=cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind in('r','p')and "+catalog.NAMESPACE+" order by n.nspname collate \"C\",c.relname collate \"C\"").fetchall()
    timeout=cur.execute('show lock_timeout').fetchone()[0]
    cur.execute("set local lock_timeout='45s'")
    cur.execute(sql.SQL('lock table {} in share mode').format(sql.SQL(',').join(sql.Identifier(*n)for n in names)))
    cur.execute("select set_config('lock_timeout',%s,true)",(timeout,))
    return dict(table_count=len(names),product_NOWAIT_unchanged=True,cancelled_backends=0)


def choice_snapshot(cur):
    old.actors.admin(cur)
    zone=cur.execute('show TimeZone').fetchone()[0]
    cur.execute("set local TimeZone='UTC'")
    try:
        return {table:cur.execute('select to_jsonb(t)from '+table+' t order by '+('id'if table.endswith('.choices')else'actor,request_id')).fetchall()for table in choice.TABLES}
    finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))


def draft_rows(cur,rid):
    old.actors.admin(cur)
    zone=cur.execute('show TimeZone').fetchone()[0]
    cur.execute("set local TimeZone='UTC'")
    try:
        return dict(header=cur.execute('select to_jsonb(r)from erp.sales_returns r where id=%s',(rid,)).fetchone()[0],
            items=cur.execute('select to_jsonb(i)from erp.sales_return_items i where return_id=%s order by id',(rid,)).fetchall())
    finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))


def unchanged_draft(cur,rid,expected,report,label):
    old.actors.admin(cur)
    zone=cur.execute('show TimeZone').fetchone()[0]
    raw=cur.execute('select to_jsonb(r)from erp.sales_returns r where id=%s',(rid,)).fetchone()[0]
    actual=draft_rows(cur,rid)
    entry=dict(label=label,session_timezone=zone,raw_header_in_session_timezone=raw,
        actual_UTC=actual,expected_UTC=expected,all_header_and_item_fields_equal=actual==expected)
    report.setdefault('DRAFT_snapshot_checks',[]).append(entry)
    assert actual==expected,('MALFORMED_DRAFT_HEADER_OR_ITEMS_CHANGED',label,entry)
    return entry


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
        changes={k:dict(before=backup['data'].get(k),after=actual.get(k))for k in set(actual)|set(backup['data'])if actual.get(k)!=backup['data'].get(k)}
        if name=='DRAFT_ROW_DRIFT':
            # Native audit sequences are nontransactional. This intentional
            # write fault is isolated by a second full restore, never setval.
            assert all(k.startswith('sequence:')for k in changes),('NEGATIVE_WRITE_PERSISTED_ROWS',changes)
            results[-1]['savepoint_sequence_changes']=changes
            results[-1]['requires_full_restore_before_binding']=True
        else:assert not changes,(name,changes)
        assert catalog._portable(catalog._catalog_rows(cur))==catalog._portable(backup['catalog'])
    def bind(b=backup,h=digest,db=database.RESTORED):
        return recovery.rebind_restored(cur,b,h,expected_database=db)
    refused('WRONG_TRUSTED_HASH',lambda:bind(h='0'*64),'SCOPED_MODEL_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    changed=deepcopy(backup);changed['sources']['current_installation']['entrypoint_sha256']='0'*64
    refused('CHANGED_COMPOSED_ENTRYPOINT_SOURCE',lambda:bind(changed,catalog.digest(changed)),'SCOPED_MODEL_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    refused('WRONG_DATABASE',lambda:bind(db=database.SOURCE),'SCOPED_MODEL_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED')
    changed_choice=deepcopy(backup);changed_choice['sources']['current_installation']['predecessor']['predecessor']['predecessor']['predecessor']['predecessor']['predecessor']['stages']['ANALOG_CHOICE']['choice.sql']='0'*64
    refused('CHANGED_ANALOG_CHOICE_SOURCE',lambda:bind(changed_choice,catalog.digest(changed_choice)),'SCOPED_MODEL_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    missing=deepcopy(backup);del missing['catalog']['sequence_ownership']
    refused('MISSING_CATALOG_GROUP',lambda:bind(missing,catalog.digest(missing)),'SCOPED_MODEL_RESTORE_CATALOG_CHANGED')
    def metadata():
        cost=cur.execute('select procost::numeric from pg_proc where oid=%s::regprocedure',(delta.SIGNATURE,)).fetchone()[0]
        cur.execute(sql.SQL('alter function '+delta.SIGNATURE+' cost {}').format(sql.Literal(cost+1)))
        held=catalog._catalog_rows(cur);data=catalog._data(cur)
        try:bind()
        finally:assert catalog._catalog_rows(cur)==held and catalog._data(cur)==data
    refused('DELTA_FUNCTION_METADATA_DRIFT',metadata,'SCOPED_MODEL_RESTORE_CATALOG_CHANGED')
    def finance_metadata():
        signature=target_composed.predecessor.predecessor.finance.render.PUBLIC
        cost=cur.execute('select procost::numeric from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()[0]
        cur.execute(sql.SQL('alter function '+signature+' cost {}').format(sql.Literal(cost+1)))
        held=catalog._catalog_rows(cur);data=catalog._data(cur)
        try:bind()
        finally:assert catalog._catalog_rows(cur)==held and catalog._data(cur)==data
    refused('FINANCE_FACADE_AUTHORITY_METADATA_DRIFT',finance_metadata,'SCOPED_MODEL_RESTORE_CATALOG_CHANGED')
    changed_model=deepcopy(backup)
    model_sources=changed_model['sources']['current_installation']['predecessor']['predecessor']['predecessor']['stages']['MODEL_EVALUATION_V2']
    model_sources[next(iter(model_sources))]='0'*64
    refused('CHANGED_MODEL_V2_SOURCE',lambda:bind(changed_model,catalog.digest(changed_model)),'SCOPED_MODEL_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    def model_metadata(signature):
        cost=cur.execute('select procost::numeric from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()[0]
        cur.execute(sql.SQL('alter function '+signature+' cost {}').format(sql.Literal(cost+1)))
        held=catalog._catalog_rows(cur);data=catalog._data(cur)
        try:bind()
        finally:assert catalog._catalog_rows(cur)==held and catalog._data(cur)==data
    refused('MODEL_POLICY_AUTHORITY_METADATA_DRIFT',lambda:model_metadata(target_composed.predecessor.policy.PUBLIC[1]),'SCOPED_MODEL_RESTORE_CATALOG_CHANGED')
    refused('MODEL_V2_AUTHORITY_METADATA_DRIFT',lambda:model_metadata(target_composed.predecessor.evaluation.PUBLIC[0]),'SCOPED_MODEL_RESTORE_CATALOG_CHANGED')
    changed_target=deepcopy(backup)
    target_sources=changed_target['sources']['current_installation']['predecessor']['predecessor']['stages']['DATED_MODEL_TARGET']
    target_sources[next(iter(target_sources))]='0'*64
    refused('CHANGED_DATED_TARGET_SOURCE',lambda:bind(changed_target,catalog.digest(changed_target)),'SCOPED_MODEL_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    refused('DATED_TIMELINE_METADATA_DRIFT',lambda:model_metadata('cp7_netting_native.timeline(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)'),'SCOPED_MODEL_RESTORE_CATALOG_CHANGED')
    refused('RAW_OPERATIONAL_COMPILER_METADATA_DRIFT',lambda:model_metadata('cp7_analysis_native.build_operational(jsonb,jsonb,uuid,jsonb)'),'SCOPED_MODEL_RESTORE_CATALOG_CHANGED')
    for name,stage in [('CHANGED_SCOPED_HISTORY_SOURCE','SCOPED_HISTORY_SOURCE'),('CHANGED_IMMUTABLE_HISTORY_RUNTIME_SOURCE','IMMUTABLE_HISTORY_RUNTIME')]:
        altered=deepcopy(backup)
        pins=altered['sources']['current_installation']['predecessor']['stages'][stage]
        pins[next(iter(pins))]='0'*64
        refused(name,lambda b=altered:bind(b,catalog.digest(b)),'SCOPED_MODEL_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    refused('IMMUTABLE_HISTORY_FUNCTION_METADATA_DRIFT',lambda:model_metadata(history_composed.runtime.PUBLIC[0]),'SCOPED_MODEL_RESTORE_CATALOG_CHANGED')
    for name,stage in [('CHANGED_SCOPED_MODEL_DATASET','SCOPED_MODEL_DATASET'),('CHANGED_SCOPED_MODEL_V3_RUNTIME','IMMUTABLE_SCOPED_MODEL_V3')]:
        altered=deepcopy(backup)
        pins=altered['sources']['current_installation']['stages'][stage]
        pins[next(iter(pins))]='0'*64
        refused(name,lambda b=altered:bind(b,catalog.digest(b)),'SCOPED_MODEL_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    refused('SCOPED_MODEL_V3_AUTHORITY_METADATA_DRIFT',lambda:model_metadata(composed.runtime.PUBLIC[0]),'SCOPED_MODEL_RESTORE_CATALOG_CHANGED')
    def extra_scoped_model_capture():
        q,actor=cur.execute('select payload,actor from cp7_model_scoped_evaluation.runs order by id limit 1').fetchone()
        scoped_model_fixture.native.capture(cur,q,str(actor))
        held=catalog._catalog_rows(cur);data=catalog._data(cur)
        try:bind()
        finally:assert catalog._catalog_rows(cur)==held and catalog._data(cur)==data
    refused('NEW_SCOPED_MODEL_V3_CAPTURE_DRIFT',extra_scoped_model_capture,'SCOPED_MODEL_RESTORE_ROWS_OR_SEQUENCES_CHANGED')
    def extra_history_capture():
        q=cur.execute('select query from cp7_model_history_runtime.runs order by id limit 1').fetchone()[0]
        history_fixture.native.capture(cur,q)
        held=catalog._catalog_rows(cur);data=catalog._data(cur)
        try:bind()
        finally:assert catalog._catalog_rows(cur)==held and catalog._data(cur)==data
    refused('NEW_HISTORY_CAPTURE_DRIFT',extra_history_capture,'SCOPED_MODEL_RESTORE_ROWS_OR_SEQUENCES_CHANGED')
    def row():
        cur.execute('update erp.sales_returns set customer_id=%s where id=%s',(customer,rid));assert cur.rowcount==1
        held=catalog._catalog_rows(cur);data=catalog._data(cur)
        try:bind()
        finally:assert catalog._catalog_rows(cur)==held and catalog._data(cur)==data
    refused('DRAFT_ROW_DRIFT',row,'SCOPED_MODEL_RESTORE_ROWS_OR_SEQUENCES_CHANGED')
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
            baseline_catalog=catalog._portable(catalog._catalog_rows(cur));baseline_data=catalog._data(cur)
            before=a.previous.restore_state.capture(cur,package.boundary.snapshot,a.core.predecessor.public_state,a.p09.functions)
            conn.rollback()
        pre_data=drill.data_hashes(database.SOURCE);pre_profile=database._database_profile(database.SOURCE)
        dump.dump(database.SOURCE,PRE_DUMP);pre_dumped=True
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            report['initial_boundary_lock']=acquire_boundary(cur)
            state=composed.install(cur);composed.verify(cur,state)
            inverse=composed.rollback_preuse(cur,state)
            state=composed.install(cur);composed.verify(cur,state)
            new_roles=database._roles(cur)-before_roles;conn.commit();installed=True
            report['advisors_with_cp7']=a.advisors(package.boundary.PG)
            report['verified_predecessor_info_manifest']=a.core.predecessor_info_manifest(cur)
            step(STEPS[0],inverse=inverse,composed=composed.verify(cur,state))
            granted,seeded=database._foundation(cur)
            today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
            day=today-timedelta(days=3);fixture={}
            old.fixture.prepare(cur,today,current=True,closed_through=day-timedelta(days=5),evidence=fixture)
            business.PATCHED=True
            f,rid,original_raw_draft=business.malformed(cur,day)
            draft_before=draft_rows(cur,rid);bad_draft=draft_before['header']
            report['initial_DRAFT_snapshot']=dict(session_timezone=cur.execute('show TimeZone').fetchone()[0],
                original_raw_header=original_raw_draft,exact_UTC=draft_before)
            refused=business.customer_refusal(cur,rid)
            good=old.positive_return(cur,day,f)
            old.actors.admin(cur)
            # Native opening precedes the three complete query days. The real
            # bounded job must reach DONE before the reviewed choice is consumed.
            report['timezone_before_analog_fixture']=cur.execute('show TimeZone').fetchone()[0]
            report['Native_analog_fixture']={}
            comparison=native_fixture.prepare(cur,today,report['Native_analog_fixture'])
            report['timezone_after_analog_fixture']=cur.execute('show TimeZone').fetchone()[0]
            before_choice_read=analog.reader.call(cur,comparison,comparison['target'])[0]
            assert before_choice_read['target_demand']['basis']=='UNKNOWN'
            physical_before=analog.plan.monetary_state(cur)
            choice_key=str(__import__('uuid').uuid4())
            first_choice,choice_ms=analog.save(cur,comparison['payload'],choice_key)
            assert first_choice['revision']=='1'and first_choice['state']=='CONFIRMED_ASSUMPTION'
            assert first_choice['evidence']['available_total_pcs']=='1'and first_choice['forecast_applied']is False
            assert analog.save(cur,comparison['payload'],choice_key)[0]==first_choice
            assert analog.plan.monetary_state(cur)==physical_before
            consumed=native_fixture.assert_fresh(cur,today,comparison,first_choice,report)
            assert analog.reader.call(cur,comparison,comparison['target'])[0]==before_choice_read
            old.actors.admin(cur)
            choice_rows=choice_snapshot(cur)
            source_before=business.source(cur,f['sale']['sale_id'])
            unchanged_draft(cur,rid,draft_before,report,'AFTER_ANALOG_PREPARATION_AND_CHOICE')
            report['READY_after_committed_choice']=native_fixture.ready(cur,day)
            report['bounded_finance_committed_fixture']={}
            held_finance=finance_fixture.prepare(cur,comparison['row']['query'],report)
            held_model=model_fixture.prepare(cur,today,comparison['row']['query'],comparison['source'],report)
            held_target=target_fixture.prepare(cur,comparison['row']['query'],comparison['target'],report)
            held_history=history_fixture.prepare(cur,today,comparison['target'],f['products'][0],report)
            held_scoped_model=scoped_model_fixture.prepare(cur,held_history,report)
            cur.execute('set constraints all immediate')
            if granted:cur.execute('revoke usage on schema erp from authenticated')
            conn.commit();composed.verify(cur,state)
            step(STEPS[1],fixture=fixture,foundation_seeded=seeded,malformed_draft=bad_draft,
                invalid_selected_return=refused,legitimate_sibling=good,source_before=source_before,
                actual_choice=first_choice,choice_ms=choice_ms,real_bounded_DONE=comparison['done'],
                choice_money_stock_HPP_unchanged=True)
            report['quiesce_used']=a.quiesce(cur);assert report['quiesce_used']['clear']
            report['used_guard_boundary_lock']=acquire_boundary(cur)
            held=catalog._data(cur);held_catalog=catalog._catalog_rows(cur)
            try:composed.rollback_preuse(cur,state)
            except ValueError as error:assert str(error)==composed.USED_ERROR
            else:raise AssertionError('USED_DELTA_REMOVED')
            assert catalog._data(cur)==held and catalog._catalog_rows(cur)==held_catalog
            conn.rollback();step(STEPS[2],all_rows_sequences_and_full22_unchanged=True)
        used_data=drill.data_hashes(database.SOURCE);used_profile=database._database_profile(database.SOURCE)
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            report['export_boundary_lock']=acquire_boundary(cur)
            backup,digest=recovery.export_manifest(cur,state)
            dump.dump(database.SOURCE,USED_DUMP);conn.rollback()
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.with_name('CURRENT_SCOPED_MODEL_USED_RESTORE_MANIFEST.json').write_text(json.dumps(backup,indent=2)+'\n')
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
            assert catalog._data(cur)==backup['data'],'SECOND_RESTORE_ROWS_OR_SEQUENCES_CHANGED'
            assert catalog._portable(catalog._catalog_rows(cur))==catalog._portable(backup['catalog']),'SECOND_RESTORE_FULL22_CHANGED'
            rebound=recovery.rebind_restored(cur,backup,digest,expected_database=database.RESTORED)
            sealed_catalog=catalog._catalog_rows(cur)
            conn.commit();step(STEPS[6],receipt=rebound)
            granted,_=database._foundation(cur)
            finance_fixture.assert_restored(cur,held_finance,report,'BEFORE_RESTORED_CLEAR')
            model_fixture.assert_restored(cur,held_model,report,'BEFORE_RESTORED_CLEAR')
            target_fixture.assert_restored(cur,held_target,report,'BEFORE_RESTORED_CLEAR',source_changed=False)
            history_fixture.assert_restored(cur,held_history,report,'BEFORE_RESTORED_CLEAR',native_return_changed=False)
            scoped_model_fixture.assert_restored(cur,held_scoped_model,report,'BEFORE_RESTORED_CLEAR',native_return_changed=False,policy_changed=False)
            assert choice_snapshot(cur)==choice_rows,'RESTORED_ANALOG_CHOICES_OR_RECEIPTS_CHANGED'
            assert analog.save(cur,comparison['payload'],choice_key)[0]==first_choice
            clear=dict(comparison['payload'],action='CLEAR',expected_revision='1',source_request=None,
                source_hash=None,source_key=None,scale_factor=None,reason='Explicit restored test withdrawal')
            assert analog.reader.call(cur,consumed,consumed['target'])[0]==report['consumed_public_reader']
            physical_before_clear=analog.plan.monetary_state(cur)
            cleared,_=analog.save(cur,clear)
            assert cleared['revision']=='2'and cleared['state']=='CLEARED'
            assert analog.get(cur,comparison['target'])['rows'][0]['state']=='CLEARED'
            assert analog.save(cur,comparison['payload'],choice_key)[0]==first_choice
            assert analog.plan.monetary_state(cur)==physical_before_clear
            native_fixture.assert_clear(cur,today,consumed,report)
            assert analog.reader.call(cur,consumed,consumed['target'])[0]==report['consumed_public_reader']
            old.actors.admin(cur)
            after=business.source(cur,f['sale']['sale_id'])
            assert after==source_before,'RESTORED_SOURCE_FINANCIAL_OR_DEPENDENCY_STATE_CHANGED'
            unchanged_draft(cur,rid,draft_before,report,'AFTER_FULL_RESTORE_AND_CLEAR')
            report['READY_after_full_restore_and_clear']=native_fixture.ready(cur,day)
            model_fixture.assert_restored(cur,held_model,report,'AFTER_RESTORED_CLEAR')
            target_fixture.assert_restored(cur,held_target,report,'AFTER_RESTORED_CLEAR',source_changed=True)
            history_fixture.assert_restored(cur,held_history,report,'AFTER_RESTORED_CLEAR',native_return_changed=False)
            scoped_model_fixture.assert_restored(cur,held_scoped_model,report,'AFTER_RESTORED_CLEAR',native_return_changed=False,policy_changed=False)
            model_fixture.suspend(cur,held_model,report)
            model_fixture.assert_restored(cur,held_model,report,'AFTER_POLICY_WITHDRAWAL',policy_changed=True)
            target_fixture.assert_restored(cur,held_target,report,'AFTER_POLICY_WITHDRAWAL',source_changed=True)
            history_fixture.assert_restored(cur,held_history,report,'AFTER_POLICY_WITHDRAWAL',native_return_changed=False)
            scoped_model_fixture.assert_restored(cur,held_scoped_model,report,'AFTER_POLICY_WITHDRAWAL',native_return_changed=False,policy_changed=True)
            refused_after=business.customer_refusal(cur,rid)
            second=old.positive_return(cur,day,f);old.actors.admin(cur)
            unchanged_draft(cur,rid,draft_before,report,'AFTER_NEXT_VALID_RETURN')
            totals=cur.execute("select count(*),sum(i.qty_pcs),sum(i.refund_amount)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=%s and r.status='POSTED'",(f['sale']['sale_id'],)).fetchone()
            assert totals==(2,2,Decimal('40.00')),totals
            finance_fixture.assert_restored(cur,held_finance,report,'AFTER_NEXT_NATIVE_RETURN')
            model_fixture.assert_restored(cur,held_model,report,'AFTER_NEXT_NATIVE_RETURN',source_changed=True,policy_changed=True)
            target_fixture.assert_restored(cur,held_target,report,'AFTER_NEXT_NATIVE_RETURN',source_changed=True)
            history_fixture.assert_restored(cur,held_history,report,'AFTER_NEXT_NATIVE_RETURN',native_return_changed=True)
            scoped_model_fixture.assert_restored(cur,held_scoped_model,report,'AFTER_NEXT_NATIVE_RETURN',native_return_changed=True,policy_changed=True)
            cur.execute('set constraints all immediate')
            if granted:cur.execute('revoke usage on schema erp from authenticated')
            assert catalog._catalog_rows(cur)==sealed_catalog
            conn.commit();step(STEPS[7],exact_full_source_state=True,malformed_draft_unchanged=True,
                invalid_selected_return=refused_after,next_valid_return=second,posted_count_qty_refund=totals,
                all_catalog_and_permissions_unchanged=True,exact_choice_rows_and_command_receipts_preserved=True,
                real_choice_replay_after_restore_and_after_clear=True,restored_clear=cleared,
                choice_clear_money_stock_HPP_unchanged=True)
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
                    assert catalog._portable(catalog._catalog_rows(cur))==baseline_catalog
                    assert catalog._data(cur)==baseline_data
                    report['baseline_full22_all_rows_all_sequences_equal']=True
                    report['cp6_restored']=a.previous.restore_state.prove(cur,before,package.boundary.snapshot,a.core.predecessor.public_state,a.p09.functions,report)
                    conn.rollback();a.p09.wip.policy.bf.verified(cur);conn.rollback()
                report['baseline_advisors_equal']=a.advisors(package.boundary.PG)==report['baseline_advisors']
                if 'advisors_with_cp7'in report:
                    report['advisor_delta']=advisor_delta(a.advisors(package.boundary.PG),report['advisors_with_cp7'])
                    report['advisor_disposition']=a.core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                    report['advisor_gate']=report['advisor_disposition']['gate']and report['baseline_advisors_equal']
                else:report['advisor_gate']=report['baseline_advisors_equal']
            except Exception as error:report.update(cp6_restored=False,restore_error=str(error),restore_traceback=traceback.format_exc())
        for path in(PRE_DUMP,USED_DUMP):drill.docker('rm','-f',path,check=False)
        report['required_steps_pass']=tuple(row['step']for row in report['steps'])==STEPS and all(row['status']=='PASS'for row in report['steps'])
        if report.get('runtime_status')=='PASS'and report['required_steps_pass']and report.get('cp6_restored')and report.get('baseline_advisors_equal')and report.get('baseline_full22_all_rows_all_sequences_equal')and report.get('advisor_gate')and not report.get('error'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('label','status','required_steps_pass','cp6_restored','baseline_advisors_equal','error','restore_error')}),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
