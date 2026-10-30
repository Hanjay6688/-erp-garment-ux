"""Two real-session preparations, administrative actors, no real Auth claim.

Each fixture commits on the existing disposable race copy. The caller must
use the retained full dump/copy restore for EACH callback; no DELETE/setval.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic,sleep
import importlib.util
from pathlib import Path
import psycopg
import cp7_snapshot_cases as auth

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('sku27_prepared_recovery_fixture',HERE/'recovery_cases.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
IDS=('SKU30_RECOVERY_CACHE_REPLAY_PERMISSION_WITHDRAWN_DURING_REAL_REQUEST_WAIT',
     'SKU30_RECOVERY_FG_TRY_LOCK_BUSY_BEFORE_ANY_EFFECT')

def local(conn,cur):
    assert conn.info.host in('localhost','127.0.0.1')and conn.info.port==54322
    assert cur.execute('select current_database()').fetchone()==('cp6_auditor_race',)

def exercise(tools,today,n,*,cache,busy='FG'):
    assert busy in('FG','MATERIAL_NONE')and(not cache or busy=='FG')
    permission='finance.hpp.manage'
    with tools.connect()as conn,conn.cursor()as cur:
        local(conn,cur);f=fixture.prepared(cur,today,n,'20.01')
        if busy=='MATERIAL_NONE':
            # Lawful current Native SET_POLICY, never an authoritative UPDATE.
            n.bc.policy(cur,'ACC_DEC03',dict(credit_account_id=n.bc.account(cur,'4100'),unit_value_cap='NONE'))
        policy=cur.execute("select value->>'unit_value_cap',version::text from erp.bc_policy_settings_v1 where policy_key='ACC_DEC03'").fetchone()
        assert policy[0]==('NONE'if busy=='MATERIAL_NONE'else'MOVING_AVERAGE'),policy
        material=n.f.one(cur,'select material_id::text from erp.bc_return_lots_v1 where id=%s',f['lot'])
        assert material==f['accessory']['material'],('SKU27_EXACT_VALUATION_MATERIAL_REQUIRED',material)
        subject,_=auth.custom_actor(cur)
        role=n.f.one(cur,"select id from erp.app_roles where role_code='ADMIN'")
        assert role is not None and n.f.one(cur,'select exists(select 1 from erp.app_role_permissions where role_id=%s and permission_key=%s)',role,permission)
        cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));assert cur.rowcount==1
        if cache:
            response=n.bc.svc(cur,'VALUE_CUSTODY',f['payload'],key=f['request'],auth=subject)
            assert response['status']=='POSTED'and n.values(cur,f['parts'])==(fixture.D('0.01'),fixture.D('40.04'))
        conn.commit()
    started=Event();backends=[]
    def send():
        with tools.connect()as conn,conn.cursor()as cur:
            local(conn,cur);cur.execute("set local lock_timeout='12s';set local statement_timeout='20s'")
            backends.append(n.f.one(cur,'select pg_backend_pid()'));started.set()
            try:
                result=n.bc.svc(cur,'VALUE_CUSTODY',f['payload'],key=f['request'],auth=subject);conn.commit()
                return dict(ok=True,result=result)
            except psycopg.Error as error:
                result=dict(ok=False,sqlstate=error.sqlstate,message=error.diag.message_primary);conn.rollback();return result
    with tools.connect()as holder,holder.cursor()as held,ThreadPoolExecutor(max_workers=1)as pool:
        local(holder,held)
        if cache:
            rows=held.execute("select actor_key from erp.idempotency_requests where operation_name='save_accessory_service_action_v1'and client_request_id=%s for update",(f['request'],)).fetchall()
            assert len(rows)==1,('SKU27_ACTUAL_COMPLETED_CUSTODY_REQUEST_REQUIRED',rows)
        elif busy=='FG':held.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        else:
            rows=held.execute('select id::text from erp.materials where id=%s for update',(material,)).fetchall()
            assert rows==[(material,)],('SKU27_EXACT_MATERIAL_ROW_HOLDER_REQUIRED',rows)
            # SELECT FOR UPDATE takes ROW SHARE, compatible with the worker's
            # SRE barrier. This exposes the old NONE downstream row/FK wait.
            assert n.f.one(held,"select exists(select 1 from pg_locks where pid=pg_backend_pid()and relation='erp.materials'::regclass and mode='RowShareLock'and granted)")
        holder_pid=n.f.one(held,'select pg_backend_pid()')
        if not cache:before=n.capture(held)
        job=pool.submit(send);assert started.wait(5)
        assert backends[0]!=holder_pid,'SKU27_TWO_DISTINCT_BACKENDS_REQUIRED'
        if cache:
            observed=False;deadline=monotonic()+5
            while monotonic()<deadline:
                held.execute('select pg_stat_clear_snapshot()')
                if n.f.one(held,'select %s=any(pg_blocking_pids(%s))',holder_pid,backends[0]):observed=True;break
                sleep(.025)
            assert observed,'SKU27_REAL_CUSTODY_REQUEST_WAIT_REQUIRED'
            held.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,permission));assert held.rowcount==1
            before=n.capture(held);holder.commit();answer=job.result(timeout=25)
        else:
            # Refuse while the FG key or exact material row is STILL held.
            # Timeout or eventual success after release proves no such guard.
            answer=job.result(timeout=5)
            assert holder.info.transaction_status==psycopg.pq.TransactionStatus.INTRANS
            assert not n.f.one(held,'select %s=any(pg_blocking_pids(%s))',holder_pid,backends[0]),'SKU27_BUSY_WAS_BLOCKING'
            holder.rollback();observed=False
    assert answer.get('ok')is False,answer
    if cache:assert answer['sqlstate']=='42501'and permission in(answer['message']or''),answer
    else:assert answer['sqlstate']=='P0001'and(answer['message']or'').startswith('CP7_SKU_RECOVERY_BUSY:'),answer
    with tools.connect()as conn,conn.cursor()as cur:
        local(conn,cur);proof=n.unchanged(cur,before,'RECOVERY_CACHE_PERMISSION_WAIT'if cache else'RECOVERY_NONBLOCKING_'+busy+'_BUSY');conn.rollback()
    return dict(status='PASS',two_actual_backends=True,holder_backend=holder_pid,worker_backend=backends[0],
      completed_UUID_replay=cache,actual_request_row_blocking_observed=observed,
      nonblocking_busy_refused_while_holder_still_held=not cache,busy_holder=None if cache else busy,
      actual_policy=dict(cap=policy[0],version=policy[1]),valuation_material=material,return_lot=f['lot'],
      actor_fixture='NEW_USER_EXISTING_ADMIN_NOT_OWNER',
      administrative_actor_not_real_Auth_or_admin_UI=True,answer=answer,complete_noeffect_after_fixture_or_permission_commit=proof,
      full_copy_restore_required=True,actual_Auth_HTTP_cases=0)

def busy_case(tools,today,n):
    # Both attempts belong to ONE declared case. Each commits its own Native
    # fixture/policy before its own full-census no-effect snapshot, then rolls
    # back its holder. The retained full copy restore runs after this callback.
    fg=exercise(tools,today,n,cache=False,busy='FG')
    material=exercise(tools,today,n,cache=False,busy='MATERIAL_NONE')
    return dict(status='PASS',declared_cases=1,distinct_busy_attempts=2,
      attempts=[fg,material],complete_noeffect_each_attempt=True,
      full_copy_restore_required=True,actual_Auth_HTTP_cases=0)

def cases(tools,today,*,native_fixture):
    return[(IDS[0],lambda:exercise(tools,today,native_fixture,cache=True)),
           (IDS[1],lambda:busy_case(tools,today,native_fixture))]
