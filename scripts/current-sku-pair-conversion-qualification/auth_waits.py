"""Prepared real wait/revocation callbacks; no current runtime PASS claim.

Auth rows are an explicit administrative fixture. The actor is a newly minted
user assigned the existing ADMIN role, never the protected OWNER. This does
not claim to test the user-admin UI or a real Auth/PostgREST login.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from time import monotonic,sleep
import importlib.util,json,uuid
import psycopg
import cp7_snapshot_cases as auth
from cp7_sku_pair_conversion import composition as product

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('sku29_auth_wait_fixture',HERE/'fixture.py')
f=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(f)
IDS=(
 'SKU29_PAIR_ADVISORY_PERMISSION_WITHDRAWAL',
 'SKU29_PAIR_REPLAY_ADVISORY_PERMISSION_WITHDRAWAL',
 'SKU29_PAIR_ROW_PERMISSION_WITHDRAWAL',
 'SKU29_PAIR_ROW_ACTOR_DEMOTION',
 'SKU29_CONVERSION_FG_PERMISSION_WITHDRAWAL',
 'SKU29_CONVERSION_REPLAY_IDEMPOTENCY_PERMISSION_WITHDRAWAL',
)

def local(conn,cur):
    assert conn.info.host in('localhost','127.0.0.1')and conn.info.port==54322
    assert cur.execute('select current_database()').fetchone()in(('cp6_rollback',),('cp6_auditor_race',))

def exercise(tools,today,kind):
    pair=kind.startswith('PAIR');replay='REPLAY'in kind;row_wait='_ROW_'in kind;demote=kind.endswith('DEMOTION')
    permission='master.product.manage'if pair else'warehouse.brand_conversion.post'
    _,_,_,_,catalog=product.runtime()
    with tools.connect()as conn,conn.cursor()as cur:
        local(conn,cur);fixture=f.nonpo(cur,today);subject,_=auth.custom_actor(cur)
        role=f.one(cur,"select id from erp.app_roles where role_code='ADMIN'")
        assert role is not None and f.one(cur,"select exists(select 1 from erp.app_role_permissions where role_id=%s and permission_key=%s)",role,permission)
        cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));assert cur.rowcount==1
        request=str(uuid.uuid4())
        if pair:
            payload=dict(source_group_id=fixture['groups'][0]['id'],target_group_id=fixture['groups'][1]['id'],
                expected_version=f.one(cur,'select cp7_sku_conversion.pair_revision_v1()'),reason='SKU29 real pair permission wait')
            rpc='erp_save_sku_action_v1';action='SAVE_PAIR'
        else:payload,_=f.review(cur,fixture['payload']);rpc='erp_save_product_conversion_action_v1';action='POST'
        if replay:f.public_as(cur,subject,rpc,action,json.dumps(payload),request)
        conn.commit()
    backends=[];started=Event()
    def send():
        with tools.connect()as conn,conn.cursor()as cur:
            local(conn,cur);cur.execute("set local lock_timeout='12s';set local statement_timeout='20s'")
            backends.append(f.one(cur,'select pg_backend_pid()'));started.set()
            try:
                value=f.public_as(cur,subject,rpc,action,json.dumps(payload),request);conn.commit()
                return dict(ok=True,result=value)
            except psycopg.Error as error:
                conn.rollback();return dict(ok=False,sqlstate=error.sqlstate,message=error.diag.message_primary)
    with tools.connect()as holder,holder.cursor()as held,ThreadPoolExecutor(max_workers=1)as pool:
        local(holder,held)
        if pair and row_wait:
            held.execute('select 1 from erp.bf_skus_v1 where id=%s for update',(payload['source_group_id'],))
        elif pair:held.execute("select pg_advisory_xact_lock(hashtextextended('CP7_SKU_PAIR_MASTER_V1',0))")
        elif replay:
            rows=held.execute("select actor_key from erp.idempotency_requests where operation_name='cp7_sku_conversion_v1'and client_request_id=%s for update",(request,)).fetchall()
            assert len(rows)==1,('SKU29_COMPLETED_REQUEST_REQUIRED',rows)
        else:held.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        holder_pid=f.one(held,'select pg_backend_pid()');job=pool.submit(send);assert started.wait(5)
        observed=False
        try:
            deadline=monotonic()+5
            while monotonic()<deadline:
                held.execute('select pg_stat_clear_snapshot()')
                if f.one(held,'select %s=any(pg_blocking_pids(%s))',holder_pid,backends[0]):observed=True;break
                sleep(.025)
            assert observed,('SKU29_REAL_AUTH_WAIT_REQUIRED',kind)
            if demote:
                staff=f.one(held,"select id from erp.app_roles where role_code='STAFF'")
                held.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(staff,subject));assert held.rowcount==1
                assert f.one(held,'select r.role_code from erp.app_users u join erp.app_roles r on r.id=u.role_id where u.auth_user_id=%s',subject)=='STAFF'
            else:
                held.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,permission));assert held.rowcount==1
            f.admin(held);expected=catalog._data(held);before=catalog._catalog_rows(held);holder.commit()
        finally:holder.rollback()
        answer=job.result(timeout=25)
    assert answer.get('ok')is False,answer
    if demote:assert answer['sqlstate']=='P0001'and 'OWNER or ADMIN access required'in(answer['message']or''),answer
    else:assert answer['sqlstate']=='42501'and permission in(answer['message']or''),answer
    with tools.connect()as conn,conn.cursor()as cur:
        local(conn,cur);assert catalog._data(cur)==expected and catalog._catalog_rows(cur)==before
        conn.rollback()
    return dict(status='PASS',kind=kind,two_actual_backends=True,actual_holder_blocks_worker_observed=True,
      actor_fixture='NEW_USER_EXISTING_ADMIN_NOT_OWNER',administrative_auth_fixture_not_admin_UI=True,
      permission_or_role_withdrawn_after_wait=True,completed_UUID_replay=replay,answer=answer,
      all22_rows_and_sequences_unchanged_after_authorization_change=True,full_restore_required_by_caller=True)

def cases(tools,today):
    kinds=('PAIR_ADVISORY_PERMISSION','PAIR_REPLAY_ADVISORY_PERMISSION','PAIR_ROW_PERMISSION','PAIR_ROW_DEMOTION',
      'CONVERSION_FG_PERMISSION','CONVERSION_REPLAY_IDEMPOTENCY_PERMISSION')
    return [(name,lambda kind=kind:exercise(tools,today,kind))for name,kind in zip(IDS,kinds)]
