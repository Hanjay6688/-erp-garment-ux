"""Six actual Native controls for immutable scoped history, separate from models."""
from time import monotonic
import json
import uuid
import cp7_model_history_runtime as stage
import cp7_ow11_model_history_scope_cases as source
from cp7_ow04_restore_bundle import _catalog_rows

plan,history,work=source.plan,source.history,source.work
CONTRACT='cp7.ow11.model-history-runtime-native.v1'
IDS=dict(native=['OW11_MODEL_HISTORY_RUNTIME_CATALOG22_COMPOSED_INVERSE',
 'OW11_MODEL_HISTORY_RUNTIME_ACTUAL_CAPTURE_REPLAY_IMMUTABLE',
 'OW11_MODEL_HISTORY_RUNTIME_ACTUAL_POST_RETIRES_ARCHIVE',
 'OW11_MODEL_HISTORY_RUNTIME_CURRENT_ACCESS_AND_FOREIGN_READ',
 'OW11_MODEL_HISTORY_RUNTIME_DENSE2000_SINGLE_TARGET',
 'OW11_MODEL_HISTORY_RUNTIME_ENGINE_AND_FINAL_FAULT'])
REQUIRED=dict(native=6)
EXPECTED=DECLARED=6
FUNCTIONS=(*source.FUNCTIONS,'erp_cp7_capture_model_history_v1','erp_cp7_read_model_history_v1')
SCHEDULES=source.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def install(cur):
    source.PARENT_CHECKER=PARENT_CHECKER
    parent=source.install(cur)
    current=stage.install_delta(cur,lambda c:source.stage.verify(c,parent))
    return parent,current


def query(cur,f,today):return dict(history.query(today),target_key=source.target(cur,f['product']))


def call(cur,name,args,subject=None):
    start=monotonic();answer=plan.rpc(cur,name,args,subject);elapsed=(monotonic()-start)*1000
    assert elapsed<8000,('MODEL_HISTORY_RUNTIME_OVER8S',name,elapsed)
    return answer


def capture(cur,q,request=None,subject=None):
    return call(cur,'erp_cp7_capture_model_history_v1',(json.dumps(q),request or uuid.uuid4()),subject)


def read(cur,run,subject=None):return call(cur,'erp_cp7_read_model_history_v1',(run,),subject)


def stored(cur,run):
    plan.b.api.admin(cur)
    return cur.execute('select to_jsonb(r)from cp7_model_history_runtime.runs r where id=%s',(run,)).fetchone()[0]


def count(cur):
    plan.b.api.admin(cur)
    return cur.execute('select count(*)from cp7_model_history_runtime.runs').fetchone()[0]


def same_archive(a,b):
    assert {k:v for k,v in a.items()if k!='current_guard'}=={k:v for k,v in b.items()if k!='current_guard'}


def cases(cur,today):
    def catalog():
        before=_catalog_rows(cur);parents,current=install(cur)
        v=stage.verify(cur,current)
        assert(v['private_functions'],v['public_rpcs'],v['new_tables'],v['existing_replacements'])==(5,2,1,0)
        installed=_catalog_rows(cur)
        cur.execute('create view public.ow11_history_runtime_inverse_guard as select id from cp7_model_history_runtime.runs')
        guarded=_catalog_rows(cur)
        try:stage.rollback_preuse(cur,current)
        except Exception as e:assert getattr(e,'sqlstate',None)=='2BP01',str(e)
        else:raise AssertionError('SCOPED_HISTORY_RUNTIME_DEPENDENT_VIEW_REMOVED')
        assert _catalog_rows(cur)==guarded
        cur.execute('drop view public.ow11_history_runtime_inverse_guard');assert _catalog_rows(cur)==installed
        try:source.stage.rollback_preuse(cur,parents)
        except ValueError as e:assert str(e)=='MODEL_HISTORY_SCOPE_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE'
        else:raise AssertionError('SCOPED_HISTORY_SOURCE_REMOVED_BELOW_RUNTIME')
        stage.rollback_preuse(cur,current);source.stage.rollback_preuse(cur,parents)
        assert _catalog_rows(cur)==before;PARENT_CHECKER(cur)
        return dict(status='PASS',exact_catalog22_composed_inverse=True,private5_public2_table1_replacement0=True,
          partial_inverse_restored=True,source_parent_cannot_be_removed_below_runtime=True,source_sha256=stage.sources())

    def replay():
        parents,current=install(cur);f=history.fixture(cur,today);q=query(cur,f,today);request=uuid.uuid4()
        physical=plan.monetary_state(cur);one=capture(cur,q,request);frozen=stored(cur,one['run_id'])
        assert one['current_guard']['source_state']=='UNCHANGED'and one['history']['scope']=='SINGLE_CURRENT_PHYSICAL_ROOT'
        assert one['history']['history']['rows'][0]['gross_observed_pcs']=='0'
        assert one['history']['current_stock'][0]['native_available_pcs']=='76'
        assert one['history']['training_known_at']==one['captured_at']
        actual,_=source.capture(cur,q['target_key'],{k:v for k,v in q.items()if k!='target_key'})
        assert one['history']['history']['rows']==actual['result']['history']['rows']
        same_archive(one,capture(cur,q,request));same_archive(one,read(cur,one['run_id']))
        refused=plan.refusal(cur,lambda:capture(cur,dict(q,group_mode='RESTATED'),request))
        assert refused[0:2]==('P0001','CP7_MODEL_HISTORY_REQUEST_CHANGED')
        for sql in('update cp7_model_history_runtime.runs set query=query','delete from cp7_model_history_runtime.runs'):
            assert plan.refusal(cur,lambda:cur.execute(sql))[0:2]==('55000','CP7_RUN_IMMUTABLE')
        assert stored(cur,one['run_id'])==frozen and count(cur)==1 and plan.monetary_state(cur)==physical
        try:stage.rollback_preuse(cur,current)
        except ValueError as e:assert str(e)=='MODEL_HISTORY_RUNTIME_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE'
        else:raise AssertionError('SCOPED_HISTORY_USED_INVERSE_ALLOWED')
        return dict(status='PASS',actual_public_capture_and_replay=True,one_UUID_one_immutable_row=True,
          actual_Native_draft_available76=True,exact_private_source_history_parity=True,
          no_backfilled_training_knowledge=True,after_use_inverse_refused_before_DDL=True,no_stock_money_HPP_change=True)

    def posted():
        install(cur);f=history.fixture(cur,today);q=query(cur,f,today);one=capture(cur,q);frozen=stored(cur,one['run_id'])
        history.sales.fg.post_sale(cur,f['draft']);physical=plan.monetary_state(cur)
        old=read(cur,one['run_id']);assert old['current_guard']['source_state']=='ARCHIVED_STALE'
        assert old['current_guard']['reason']=='CURRENT_SCOPED_SOURCE_CHANGED';same_archive(one,old)
        same_archive(one,capture(cur,q,one['request_id']))
        fresh=capture(cur,q);assert fresh['current_guard']['source_state']=='UNCHANGED'
        assert fresh['history']['history']['rows'][0]['gross_observed_pcs']=='24'
        assert fresh['history']['current_stock'][0]['native_available_pcs']=='76'
        assert stored(cur,one['run_id'])==frozen and plan.monetary_state(cur)==physical
        return dict(status='PASS',actual_Native_post_retires_old_archive=True,original_draft_history_immutable=True,
          fresh_posted_gross24_available76=True,no_second_stock_subtraction=True)

    def access():
        install(cur);f=history.fixture(cur,today);q=query(cur,f,today);actor,role=history.auth.custom_actor(cur)
        one=capture(cur,q,subject=actor);frozen=stored(cur,one['run_id'])
        other,_=history.auth.custom_actor(cur)
        assert plan.refusal(cur,lambda:read(cur,one['run_id'],other))[0:2]==('42501','CP7_MODEL_HISTORY_RUN_UNAVAILABLE')
        plan.b.api.admin(cur);cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,))
        assert plan.refusal(cur,lambda:read(cur,one['run_id'],actor))[0]=='42501'
        assert plan.refusal(cur,lambda:capture(cur,q,one['request_id'],actor))[0]=='42501'
        assert count(cur)==1 and stored(cur,one['run_id'])==frozen
        return dict(status='PASS',actual_four_operational_permissions=True,foreign_UUID_denied=True,
          current_revocation_before_read_and_committed_replay=True,no_denied_capture_effect=True,actual_Auth_HTTP_credit=False)

    def dense():
        install(cur);f=history.fixture(cur,today);q=query(cur,f,today);one=capture(cur,q)
        size=work.dense.seed(cur);physical=plan.monetary_state(cur)
        start=monotonic();fresh=capture(cur,q);ms=(monotonic()-start)*1000
        assert ms<8000 and fresh['source_hash']==one['source_hash']
        assert fresh['current_guard']['source_state']=='UNCHANGED'and len(fresh['history']['history']['rows'])==1
        assert fresh['history']['history']['rows']==one['history']['history']['rows']
        cur.execute('set local role cp7_capture');whole=cur.execute('select cp7_planning.history_source()').fetchone()[0];plan.b.api.admin(cur)
        assert whole['status']=='INCOMPLETE'and plan.monetary_state(cur)==physical
        return dict(status='PASS',label='SYNTHETIC_VOLUME_ACTUAL_PUBLIC_SCOPED_CAPTURE',**size,
          original_global_bound_unchanged=True,single_target_complete=True,millis=round(ms,3),wall_limit_ms=8000,
          factory_SLA_claim=False,model_caller_integrated=False)

    def engine_fault():
        install(cur);f=history.fixture(cur,today);q=query(cur,f,today);one=capture(cur,q);frozen=stored(cur,one['run_id'])
        plan.b.api.admin(cur)
        cur.execute('create function cp7_model_history_runtime.fixture_engine_revision()returns boolean language sql as $$select true$$')
        stale=read(cur,one['run_id']);assert stale['current_guard']['reason']=='HISTORY_RUNTIME_ENGINE_CHANGED';same_archive(one,stale)
        cur.execute("create function cp7_model_history_runtime.fixture_last_fault()returns trigger language plpgsql as $$begin raise exception 'SCOPED_HISTORY_FINAL_ROW_FAULT';end$$")
        cur.execute('create trigger fixture_last_fault before insert on cp7_model_history_runtime.runs for each row execute function cp7_model_history_runtime.fixture_last_fault()')
        assert plan.refusal(cur,lambda:capture(cur,q))[0:2]==('P0001','SCOPED_HISTORY_FINAL_ROW_FAULT')
        assert count(cur)==1 and stored(cur,one['run_id'])==frozen
        return dict(status='PASS',controlled_engine_change_retires_actual_archive=True,
          injected_final_insert_fault_no_orphan=True,original_row_immutable=True)

    return list(zip(IDS['native'],(catalog,replay,posted,access,dense,engine_fault)))


def races(tools,today):return []
def http_cases(http,today):return []
