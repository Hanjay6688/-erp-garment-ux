"""Six Native prospective policy controls; no model activation or Auth HTTP credit."""
from copy import deepcopy
from time import monotonic
import json
import uuid
import cp7_model_policy_stage as stage
import cp7_ow13c_bounded_stage_cases as bounded
from cp7_ow04_restore_bundle import _catalog_rows

plan=bounded.plan
master=bounded.work.base.retained.master
CONTRACT='cp7.ow11.model-policy-native.v1'
IDS=dict(native=['OW11_MODEL_POLICY_CATALOG22_PREUSE_DEPENDENCY',
 'OW11_MODEL_POLICY_EXPLICIT_APPEND_SUSPEND_REACTIVATE_REPLAY',
 'OW11_MODEL_POLICY_PROSPECTIVE_CLOCK_AND_IMMUTABLE_HISTORY',
 'OW11_MODEL_POLICY_CURRENT_ACCESS_OWNER_ADMIN_AND_REPLAY',
 'OW11_MODEL_POLICY_EXPLICIT_VALIDATION_CAS_TEMPLATE',
 'OW11_MODEL_POLICY_ATOMIC_REGISTRY_POLICY_COMMAND'])
REQUIRED=dict(native=6)
EXPECTED=DECLARED=6
FUNCTIONS=(*bounded.FUNCTIONS,'erp_cp7_get_model_activation_policy_v1','erp_cp7_save_model_activation_policy_v1')
SCHEDULES=bounded.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
# Explicit test fixture, never defaults or owner policy inferred from technical proposals.
CONFIG=dict(minimum_training_days='20',maximum_horizon_days='90',allowed_methods=['NAIVE'],
 promotion=dict(minimum_complete_folds='3',minimum_mae_improvement='0',maximum_bias_worsening='0',maximum_tail_worsening='0',season_lag='7'))


def install(cur):
    plan.b.api.admin(cur)
    return stage.install_delta(cur,PARENT_CHECKER)


def get(cur,subject):
    return plan.rpc(cur,'erp_cp7_get_model_activation_policy_v1',(),subject)


def payload(cur,subject):
    w=get(cur,subject)
    return dict(contract_version='cp7.model-activation-policy-command.v1',action='SET',config=deepcopy(CONFIG),
     template_hash=w['model_template']['hash'],reason='Explicit SYNTHETIC Native policy fixture; no factory default',
     reviewed=True,expected_revision=w['revision'],access_epoch=w['access_epoch'])


def save(cur,p,subject,key=None):
    start=monotonic();r=plan.rpc(cur,'erp_cp7_save_model_activation_policy_v1',(json.dumps(p),key or uuid.uuid4()),subject)
    ms=(monotonic()-start)*1000;assert ms<8000,('MODEL_POLICY_WRITE_OVER8S',ms)
    return r


def state(cur):
    plan.b.api.admin(cur)
    return {t:cur.execute('select md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),\'[]\')::text)from '+t+' x').fetchone()[0]
     for t in(*stage.TABLES,'cp7_model_native.registry')}


def cases(cur,today):
    def catalog():
        before=_catalog_rows(cur);s=install(cur);v=stage.verify(cur,s)
        assert(v['private_functions'],v['public_rpcs'],v['new_tables'],v['old_replacements'])==(7,2,2,0)
        snap=_catalog_rows(cur)
        cur.execute('create view public.ow11_model_policy_inverse_guard as select id from cp7_model_policy.policies')
        guarded=_catalog_rows(cur)
        try:stage.rollback_preuse(cur,s)
        except Exception as e:assert getattr(e,'sqlstate',None)=='2BP01',str(e)
        else:raise AssertionError('MODEL_POLICY_DEPENDENT_VIEW_REMOVED')
        assert _catalog_rows(cur)==guarded
        cur.execute('drop view public.ow11_model_policy_inverse_guard');assert _catalog_rows(cur)==snap
        stage.rollback_preuse(cur,s);assert _catalog_rows(cur)==before
        return dict(status='PASS',source_sha256=stage.verify_sources(),exact_catalog22_inverse=True,
         private7_public2_tables2_replacements0=True,dependent_view_failure_restores_partial_DDL=True)

    def lifecycle():
        s=install(cur);subject=master.role_actor(cur,'OWNER');physical=plan.monetary_state(cur)
        w=get(cur,subject);assert w['current']is None and w['revision']=='0'and w['state']=='UNREVIEWED'
        assert set(w['model_template']['models'])=={'baseline','challengers'}
        p=payload(cur,subject);key=str(uuid.uuid4());first=save(cur,p,subject,key)
        assert first['policy']['config']==CONFIG and first['policy']['revision']=='1'and first['forecast_applied']is False
        assert save(cur,p,subject,key)==first
        assert plan.refusal(cur,lambda:save(cur,dict(p,reason='different'),subject,key))[1]=='CP7_MODEL_POLICY_REQUEST_CHANGED'
        q=payload(cur,subject);q.update(action='SUSPEND',config=None,template_hash=None,reason='Explicit withdrawal')
        second=save(cur,q,subject);assert second['policy']['revision']=='2'and second['policy']['state']=='SUSPENDED'
        assert second['policy']['config']==first['policy']['config']and get(cur,subject)['state']=='SUSPENDED'
        q=payload(cur,subject);q['config']['minimum_training_days']='30';third=save(cur,q,subject)
        assert third['policy']['revision']=='3'and third['policy']['registry_id']!=first['policy']['registry_id']
        assert save(cur,p,subject,key)==first and plan.monetary_state(cur)==physical
        plan.b.api.admin(cur)
        try:stage.rollback_preuse(cur,s)
        except ValueError as e:assert str(e)=='MODEL_POLICY_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE'
        else:raise AssertionError('MODEL_POLICY_AFTER_USE_INVERSE_ALLOWED')
        return dict(status='PASS',actual_public_metadata_lifecycle=True,no_default_threshold=True,old_UUID_exact=True,
         append_suspend_and_new_reactivation=True,no_physical_stock_money_HPP_change=True,forecast_applied=False)

    def clocks():
        install(cur);subject=master.role_actor(cur,'OWNER');r=save(cur,payload(cur,subject),subject);p=r['policy']
        assert cur.execute("select cp7_model_policy.source_at(%s::timestamptz-interval'1 microsecond')",(p['recorded_at'],)).fetchone()[0]is None
        assert cur.execute('select cp7_model_policy.source_at(%s::timestamptz)',(p['recorded_at'],)).fetchone()[0]['policy']==p
        rr=cur.execute('select registered_at=%s::timestamptz,configuration from cp7_model_native.registry where id=%s',(p['recorded_at'],p['registry_id'])).fetchone()
        assert rr[0]and rr[1]['meaning']=='EXPLICIT_OWNER_ACTIVATION_POLICY'
        assert rr[1]['activation_policy']=={k:p[k]for k in('id','revision','recorded_at')}
        before=state(cur)
        for sql in('update cp7_model_policy.policies set reason=reason','delete from cp7_model_policy.commands',
                    "delete from cp7_model_native.registry where id like 'cp7.owner-model-policy.%'"):
            assert plan.refusal(cur,lambda:cur.execute(sql))[1]=='CP7_RUN_IMMUTABLE'
        assert state(cur)==before
        return dict(status='PASS',actual_recorded_registry_policy_clock_equal=True,no_backdated_policy=True,
         microsecond_cutoff_exact=True,policy_command_and_registry_immutable=True)

    def access():
        install(cur);subject=master.role_actor(cur,'OWNER');backup=master.role_actor(cur,'OWNER')
        p=payload(cur,subject);key=str(uuid.uuid4());save(cur,p,subject,key)
        admin=master.role_actor(cur,'ADMIN');assert get(cur,admin)['can_write']is True
        save(cur,payload(cur,admin),admin)
        auditor=master.role_actor(cur,'AUDITOR_VIEW_ONLY');before=state(cur)
        assert plan.refusal(cur,lambda:save(cur,p,auditor))[0]=='42501'
        plan.b.api.admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
        assert subject!=backup
        assert plan.refusal(cur,lambda:save(cur,p,subject,key))[0]=='42501'
        assert plan.refusal(cur,lambda:get(cur,subject))[0]=='42501'and state(cur)==before
        return dict(status='PASS',actual_Native_permissions=True,OWNER_ADMIN_only_write=True,
         revoked_access_precedes_saved_UUID_replay=True,last_owner_protection_kept=True,actual_Auth_HTTP_credit=False)

    def invalid():
        install(cur);subject=master.role_actor(cur,'OWNER');p=payload(cur,subject);before=state(cur)
        bad=[dict(p,reviewed=False),dict(p,reason=' '),dict(p,expected_revision='1'),dict(p,template_hash='0'*64),
             dict(p,access_epoch='0'*64),dict(p,extra=True),dict(p,action='SUSPEND',config=None,template_hash=None)]
        for field,value in(('minimum_training_days','0'),('maximum_horizon_days','91'),('allowed_methods',['MEAN']),('allowed_methods',['NAIVE','NAIVE'])):
            q=deepcopy(p);q['config'][field]=value;bad.append(q)
        for q in bad:plan.refusal(cur,lambda:save(cur,q,subject))
        assert state(cur)==before
        return dict(status='PASS',invalid_cases=len(bad),no_implicit_thresholds=True,no_orphan_policy_or_registry=True)

    def atomic():
        install(cur);subject=master.role_actor(cur,'OWNER');p=payload(cur,subject);before=state(cur)
        cur.execute("create function public.ow11_policy_last_fault()returns trigger language plpgsql as $$begin raise exception 'OW11_POLICY_LAST_TABLE_FAULT';end$$")
        cur.execute('create trigger ow11_policy_last_fault before insert on cp7_model_policy.commands for each row execute function public.ow11_policy_last_fault()')
        assert plan.refusal(cur,lambda:save(cur,p,subject))[1]=='OW11_POLICY_LAST_TABLE_FAULT'
        assert state(cur)==before
        return dict(status='PASS',last_command_table_fault=True,registry_policy_command_atomic=True)

    return list(zip(IDS['native'],[catalog,lifecycle,clocks,access,invalid,atomic]))
