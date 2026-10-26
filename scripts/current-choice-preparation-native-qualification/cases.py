"""Six focused full-composition cases; old B factory/Native6 routes unchanged."""
from contextlib import contextmanager
from datetime import timedelta
from copy import deepcopy
from pathlib import Path
from time import monotonic
import importlib.util,json,uuid
import cp7_current_choice_preparation.installation as product
import cp7_ow12b_choice_preparation_cases as B
import cp7_p21_current_chain_rehearsal_probe as chain

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qualified_choice_public_finance',ROOT/'scripts/current-frozen-public-native-qualification/public_finance_cases.py')
finance=importlib.util.module_from_spec(spec);spec.loader.exec_module(finance)
parent,plan,reader=B.parent,B.plan,B.reader
IDS=('CURRENT_CHOICE_REGISTRY_FULL22_INVERSE_GUARDS',
     'CURRENT_CHOICE_COLD_PREPARE_READ_SAVE_REPLAY',
     'CURRENT_CHOICE_CURRENT_ACCESS_AND_CHANGED_SOURCE',
     'CURRENT_CHOICE_ATOMIC_SAVE_RETENTION_RECEIPT_USED_GUARD',
     'CURRENT_CHOICE_CANCELLATION_RECOVERY_AND_UNKNOWN_FAILURE',
     'CURRENT_CHOICE_EXISTING_K4_AND_OFFICIAL_FINANCE')
STATE=CHECKER=None

@contextmanager
def installed(state,checker):
    global STATE,CHECKER
    old=STATE,CHECKER;STATE,CHECKER=state,checker
    try:yield dict(focused_case_ids=list(IDS),B_original_routes_unchanged=True,
        previous_failures_remain_INCOMPLETE=True,factory_qualification=False,
        B_fixtures_exact=True,official_finance_formulas_unchanged=True,production_go=False)
    finally:STATE,CHECKER=old

def claims(cur):
    return cur.execute("select current_setting('request.jwt.claims',true),current_setting('request.jwt.claim.sub',true),current_setting('request.jwt.claim',true)").fetchone()

def used_refused(cur):
    plan.b.api.admin(cur)
    with chain.helper.control.product_catalog(cur):
        before,data=product.catalog._catalog_rows(cur),product.catalog._data(cur)
        try:product.rollback_preuse(cur,STATE)
        except ValueError as error:assert str(error)==product.USED_ERROR
        else:raise AssertionError('USED_FULL_COMPOSITION_INVERSE_ACCEPTED')
        assert product.catalog._catalog_rows(cur)==before and product.catalog._data(cur)==data

def pre_step_cancellation(cur,today,f,observed):
    """Inject only SQL57014 at the retained access entry; restore exact definition.

    This exercises the real composed K4 and real work row on PostgreSQL. It is
    fault injection, not a wall-clock timeout or process-loss measurement.
    """
    current=parent.fresh(cur,today,f,observed);reader.purge(cur,current);B.call(cur,'request',current,observed)
    plan.b.api.admin(cur);before=B.work(cur,current)
    sig='cp7_schedule_native.access_now(boolean)'
    original=cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]
    assert original.count('\nbegin\n')==1
    faulted=original.replace('\nbegin\n',"\nbegin\n if current_setting('cp7_choice_probe.access_cancel',true)='true'then raise exception using errcode='57014',message='INJECTED_PRESTEP_CANCEL';end if;\n",1)
    held=product.catalog._catalog_rows(cur);prior=cur.execute('show statement_timeout').fetchone()[0]
    prior_fault=cur.execute("select current_setting('cp7_choice_probe.access_cancel',true)").fetchone()[0]
    cur.execute("set local statement_timeout='8s'");cur.execute(faulted);ticks=[]
    def tick():
        plan.b.api.admin(cur);old_claims=claims(cur);start=monotonic()
        answer=cur.execute('select cp7_ops.analysis_tick()').fetchone()[0]
        elapsed=round((monotonic()-start)*1000,3)
        assert elapsed<8000 and claims(cur)==old_claims
        assert answer['family']=='CHOICE_PREPARATION'
        ticks.append(dict(state=answer['state'],millis=elapsed))
        return answer
    try:
        cur.execute("select set_config('cp7_choice_probe.access_cancel','true',true)")
        assert tick()['state']=='QUEUED'
        after=B.work(cur,current)
        assert after['job_id']==before['job_id']and after['created_at']==before['created_at']
        assert after['attempts']==1 and after['payload']is None
        cur.execute("select set_config('cp7_choice_probe.access_cancel','false',true)")
        assert tick()['state']=='READY'
        after=B.work(cur,current)
        assert after['attempts']==1 and after['payload']['inputs']==current['expected']
        terminal=parent.fresh(cur,today,f,observed);reader.purge(cur,terminal);B.call(cur,'request',terminal,observed)
        identity=B.work(cur,terminal)
        cur.execute("select set_config('cp7_choice_probe.access_cancel','true',true)")
        for attempt in range(1,4):
            answer=tick();work=B.work(cur,terminal)
            assert answer['state']==('QUEUED'if attempt<3 else'FAILED')
            assert work['attempts']==attempt and work['payload']is None
            assert work['job_id']==identity['job_id']and work['created_at']==identity['created_at']
        assert work['failure_code']=='CP7_CHOICE_PREPARATION_TIME_LIMIT'and work['failure_sqlstate']=='57014'
        cur.execute("select set_config('cp7_choice_probe.access_cancel','false',true)")
        assert B.call(cur,'get',terminal,observed)['state']=='FAILED'
    finally:
        if cur.connection.info.transaction_status!=finance.finance.TransactionStatus.INERROR:
            plan.b.api.admin(cur);cur.execute(original)
            cur.execute("select set_config('cp7_choice_probe.access_cancel',%s,true)",(prior_fault or '',))
            cur.execute("select set_config('statement_timeout',%s,true)",(prior,))
    assert product.catalog._catalog_rows(cur)==held
    return dict(actual_composed_K4_ticks=ticks,prestep_cancel_attempts_bounded=True,
        same_work_recovers=True,third_cancel_terminal=True,claims_restored_every_tick=True,
        injected_SQL57014_not_wall_clock_timeout=True,exact_access_definition_restored=True)

def cases(cur,today):
    observed={}
    def catalog():
        CHECKER(cur)
        assert len(product.PUBLIC)==5
        for sig in product.PUBLIC:
            assert {role:cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(role,sig)).fetchone()[0]
                for role in ('anon','authenticated','service_role','cp7_alert')}==dict(anon=False,authenticated=True,service_role=False,cp7_alert=False)
        cur.execute('create view public.current_choice_inverse_guard as select public.erp_cp7_get_frozen_choice_preparation_v1(null,null)value')
        with chain.helper.control.product_catalog(cur):
            before,data=product.catalog._catalog_rows(cur),product.catalog._data(cur)
            try:product.rollback_preuse(cur,STATE)
            except ValueError as error:assert str(error)=='CURRENT_CHOICE_ACTUAL_FULL22_CHANGED'
            else:raise AssertionError('EXTERNAL_VIEW_INVERSE_ACCEPTED')
            assert product.catalog._catalog_rows(cur)==before and product.catalog._data(cur)==data
        cur.execute('drop view public.current_choice_inverse_guard');CHECKER(cur)
        return dict(status='PASS',public_registry_exact=5,authenticated_only=True,external_dependency_refused_before_DDL=True,full22=True)

    def lifecycle():
        f=parent.prepare(cur,today,observed);reader.purge(cur,f)
        money=plan.monetary_state(cur);metadata=B.choice.metadata(cur)
        plan.refused(cur,lambda:reader.call(cur,f,f['target'],observed),'CP7_CHOICE_PREPARATION_REQUIRED')
        plan.refused(cur,lambda:parent.save(cur,f),'CP7_CHOICE_PREPARATION_REQUIRED')
        assert B.choice.metadata(cur)==metadata and plan.monetary_state(cur)==money
        B.ready(cur,f,observed);before=B.work(cur,f)
        reader.call(cur,f,f['target'],observed);key=str(uuid.uuid4());payload=parent.payload(f)
        result=parent.save(cur,f,payload,key,observed)
        assert parent.save(cur,f,payload,key,observed)==result and B.work(cur,f)==before
        assert plan.monetary_state(cur)==money
        return dict(status='PASS',cold_read_and_SAVE_refuse_without_prepare=True,prepared_inputs_match_original_compiler=True,
            same_source_request_deduplicated=True,READY_did_not_save_choice=True,exact_UUID_payload_replay=True,no_money_stock_HPP_change=True)

    def access():
        f=parent.prepare(cur,today,observed);B.ready(cur,f,observed)
        other=B.native.native.policy.master.role_actor(cur,'OWNER');epoch=reader.reader.epoch(cur,other)
        for verb in ('request','get','step'):
            plan.refused(cur,lambda:B.call(cur,verb,f,observed,actor=other,epoch=epoch),'CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE','42501')
            plan.refused(cur,lambda:B.call(cur,verb,f,observed,epoch='0'*64),'CP7_ANALYSIS_ACCESS_CHANGED','42501')
        plan.found_fg(cur,f['x'],'1');money=plan.monetary_state(cur);metadata=B.choice.metadata(cur)
        reader.call(cur,f,f['target'],observed)
        plan.refused(cur,lambda:parent.save(cur,f),'CP7_ANALOG_CHOICE_SOURCE_CHANGED','40001')
        assert B.choice.metadata(cur)==metadata and plan.monetary_state(cur)==money
        plan.b.api.admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(f['subject'],))
        for verb in ('request','get','step'):assert plan.refusal(cur,lambda:B.call(cur,verb,f,observed))[0]=='42501'
        return dict(status='PASS',foreign_actor_and_wrong_epoch_refused=True,current_revocation_refused=True,
            old_analysis_does_not_authorize_new_SAVE=True,real_post_changes_source=True)

    def atomic_retention():
        f=parent.prepare(cur,today,observed);B.ready(cur,f,observed);plan.b.api.admin(cur)
        cur.execute("create function pg_temp.current_choice_last_fault()returns trigger language plpgsql as $$begin raise exception 'CURRENT_CHOICE_LAST_TABLE_FAULT';end$$")
        cur.execute('create trigger current_choice_last_fault before insert on cp7_product_analog_choice.commands for each row execute function pg_temp.current_choice_last_fault()')
        metadata=B.choice.metadata(cur);money=plan.monetary_state(cur)
        plan.refused(cur,lambda:parent.save(cur,f),'CURRENT_CHOICE_LAST_TABLE_FAULT')
        assert B.choice.metadata(cur)==metadata and plan.monetary_state(cur)==money
        plan.b.api.admin(cur);cur.execute('drop trigger current_choice_last_fault on cp7_product_analog_choice.commands')
        key=str(uuid.uuid4());payload=parent.payload(f);saved=parent.save(cur,f,payload,key)
        used_refused(cur)
        plan.b.api.admin(cur);parent.bounded.retention.age(cur,f['done']['run_id'],timedelta(days=8))
        plan.refused(cur,lambda:B.call(cur,'get',f,observed),parent.bounded.retention.EXPIRED)
        assert parent.save(cur,f,payload,key)==saved
        plan.b.api.admin(cur);retained=cur.execute('select cp7_ops.retention_tick()').fetchone()[0]
        assert retained['choice_preparation_payloads']==1
        work=B.work(cur,f);assert work['payload']is None and work['state']=='EXPIRED'
        assert work['source_request']==f['key']and work['job_id']==f['row']['id']
        assert parent.save(cur,f,payload,key)==saved
        assert cur.execute('select cp7_ops.retention_tick()').fetchone()[0]['choice_preparation_payloads']==0
        used_refused(cur)
        return dict(status='PASS',last_table_fault_atomic=True,used_inverse_refused_before_DDL=True,
            actual_retention_hook_cleared_only_expired_payload=True,work_identity_and_receipt_survive=True,repeated_retention_no_effect=True)

    def cancellation():
        f=parent.prepare(cur,today,observed);reader.purge(cur,f);B.call(cur,'request',f,observed);plan.b.api.admin(cur)
        cur.execute("create function pg_temp.current_choice_cancel()returns trigger language plpgsql as $$begin if new.state='READY'then raise exception using errcode='57014',message='INJECTED_CANCEL';end if;return new;end$$")
        trigger='create trigger current_choice_cancel before update on cp7_frozen_choice_preparation.work for each row execute function pg_temp.current_choice_cancel()'
        cur.execute(trigger);first=B.call(cur,'step',f,observed)
        assert first['state']=='QUEUED'and first['unit_attempts']==1 and B.work(cur,f)['payload']is None
        plan.b.api.admin(cur);cur.execute('drop trigger current_choice_cancel on cp7_frozen_choice_preparation.work')
        assert B.call(cur,'step',f,observed)['state']=='READY'
        new=parent.fresh(cur,today,f,observed);reader.purge(cur,new);B.call(cur,'request',new,observed);plan.b.api.admin(cur);cur.execute(trigger)
        for n in range(1,4):
            result=B.call(cur,'step',new,observed)
            assert result['unit_attempts']==n and result['units_done']==0 and B.work(cur,new)['payload']is None
            assert result['state']==('QUEUED'if n<3 else'FAILED')
        assert B.call(cur,'step',new,observed)==result
        plan.b.api.admin(cur);cur.execute('drop trigger current_choice_cancel on cp7_frozen_choice_preparation.work')
        third=parent.fresh(cur,today,f,observed);reader.purge(cur,third);B.call(cur,'request',third,observed);plan.b.api.admin(cur)
        cur.execute("create function pg_temp.current_choice_unknown()returns trigger language plpgsql as $$begin if new.state='READY'then raise exception using errcode='22012',message='PRIVATE_UNKNOWN_DETAIL';end if;return new;end$$")
        cur.execute('create trigger current_choice_unknown before update on cp7_frozen_choice_preparation.work for each row execute function pg_temp.current_choice_unknown()')
        unknown=B.call(cur,'step',third,observed)
        assert unknown['state']=='FAILED'and unknown['unit_attempts']==1 and unknown['failure_sqlstate']=='22012'
        assert unknown['failure_code']=='CP7_CHOICE_PREPARATION_FAILED'and 'PRIVATE_UNKNOWN_DETAIL'not in json.dumps(unknown)
        plan.b.api.admin(cur);cur.execute('drop trigger current_choice_unknown on cp7_frozen_choice_preparation.work')
        before_compiler=pre_step_cancellation(cur,today,f,observed)
        return dict(status='PASS',injected_SQL57014_not_wall_clock_timeout=True,same_work_recovers_after_one_cancel=True,
            third_cancel_is_terminal=True,unknown_error_fails_without_timeout_reclassification=True,partial_payload_never_published=True,
            before_compiler_runner=before_compiler)

    def runner_finance():
        f=parent.prepare(cur,today,observed);reader.purge(cur,f);B.call(cur,'request',f,observed)
        key=uuid.uuid4();initial=finance.request(cur,today,key,subject=f['subject']);cid=finance.sidecar(initial,key,'RUNNING')['capture']['capture_id']
        money=plan.monetary_state(cur);plan.b.api.admin(cur);ticks=[]
        prior_limit=cur.execute('show statement_timeout').fetchone()[0];cur.execute("set local statement_timeout='8s'")
        try:
            for _ in range(500):
                plan.b.api.admin(cur);before_claims=claims(cur);start=monotonic();tick=cur.execute('select cp7_ops.analysis_tick()').fetchone()[0]
                elapsed=round((monotonic()-start)*1000,3);assert elapsed<8000 and claims(cur)==before_claims
                ticks.append(dict(family=tick.get('family'),outcome=tick.get('outcome'),state=tick.get('state'),millis=elapsed))
                if len(ticks)==1:assert tick['family']=='CHOICE_PREPARATION'and tick['state']=='READY'
                status=finance.staged.status(cur,key,f['subject'])
                if status['state']=='DONE'and status['finance_capture']['state']=='READY':break
                assert status['state']!='FAILED'and status['finance_capture']['state']!='FAILED'
                assert tick['ran']is True,'PENDING_WORK_NOT_ADVANCED'
            else:raise AssertionError('SMALL_NATIVE_RUNNER_DID_NOT_FINISH')
        finally:
            if cur.connection.info.transaction_status!=finance.finance.TransactionStatus.INERROR:
                plan.b.api.admin(cur);cur.execute("select set_config('statement_timeout',%s,true)",(prior_limit,))
        assert any(t['family']=='FINANCE'for t in ticks)
        assert B.work(cur,f)['payload']['inputs']==f['expected']and plan.monetary_state(cur)==money
        result=finance.sidecar(status,key,'READY')['result']
        source=finance.finance.call(cur,'select cp7_finance_capture.result(%s)',(cid,),f['subject'])
        signature,counts=finance.finance.independent_signature(cur,source['dates']['as_of'])
        assert signature==source['book_signature']and counts=={k:source['capture']['plan'][k]['rows']for k in finance.finance.FAMILIES}
        finance.staged.auth.actor(cur,f['subject'])
        official=cur.execute('select public.erp_cp7_get_finance_report_v1(%s)',(json.dumps(source['dates']),)).fetchone()[0]
        plan.b.api.admin(cur)
        for part in ('performance','financial_position','basis','data_confidence'):assert source['report']['snapshot'][part]==official['snapshot'][part]
        wanted,readiness=finance.finance.metrics(cur,source)
        assert len(wanted)==24 and {m['metric_id']:m['value']for m in result['metrics']}==wanted and result['readiness']==readiness
        assert all('value'not in v for v in wanted.values()if v['state']=='UNKNOWN')
        return dict(status='PASS',actual_private_K4_ticks=ticks,actual_minute_cron_claim=False,
            oldest_preparation_selected_then_existing_finance_completed=True,caller_claims_restored=True,
            official_metrics_exact=24,independent_book_signature=True,unknown_never_zero=True,
            no_money_stock_HPP_change=True,large_factory_acceptance=False)

    def measured(fn):
        def run():
            observed.clear();start=monotonic();result=fn()
            return dict(result,observations=deepcopy(observed),whole_case_millis=round((monotonic()-start)*1000,3),total8s_gate=False,production_go=False)
        return run
    return list(zip(IDS,map(measured,(catalog,lifecycle,access,atomic_retention,cancellation,runner_finance))))
