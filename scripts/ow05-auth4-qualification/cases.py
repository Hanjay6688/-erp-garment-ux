"""Retain Auth2 plus actual rights changes and contention with the sewing writer."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import importlib.util
import json
import time
import uuid

from cp7_contractor_correction import native_cases as n

source=Path(__file__).resolve().parents[1]/'ow05-auth-qualification/cases.py'
spec=importlib.util.spec_from_file_location('ow05_retained_auth2_cases',source)
retained=importlib.util.module_from_spec(spec);spec.loader.exec_module(retained)
IDS=retained.IDS+('OW05_REAL_AUTH_RIGHT_REVOKED_AFTER_WAIT_AND_BEFORE_REPLAY',
                  'OW05_REAL_SEWING_FLOW_AND_PO_ROW_CONTENTION_REFUSED_ATOMICALLY')

def waiting(cur,holder,futures,count):
    until=time.monotonic()+7
    while True:
        cur.execute('select pg_stat_clear_snapshot()')
        rows=cur.execute('select pid,wait_event_type,wait_event from pg_stat_activity '
            'where datname=current_database()and %s=any(pg_blocking_pids(pid))order by pid',(holder,)).fetchall()
        if len(rows)==count:
            assert all(r[1:]==('Lock','advisory')for r in rows),rows
            return rows
        assert time.monotonic()<until,('OW05_ACTUAL_NATIVE_WAIT_NOT_OBSERVED',rows)
        assert not any(f.done()for f in futures),[f.result()if f.done()else'pending'for f in futures]
        time.sleep(.025)

def permission(http,role,restore=None):
    with http.connect()as conn,conn.cursor()as cur:
        n.auth.b.api.admin(cur)
        if restore is None:
            row=cur.execute("delete from erp.app_role_permissions p where role_id=%s and permission_key='production.distribution.create'returning to_jsonb(p)",(role,)).fetchone()
            assert row is not None;result=row[0]
        else:
            cur.execute('insert into erp.app_role_permissions select *from jsonb_populate_record(null::erp.app_role_permissions,%s::jsonb)',(json.dumps(restore,default=str),))
            result=None
        conn.commit();return result

def rights(http,today):
    user=http.login('ADMIN',label='ow05-rights');g=retained.prepare(http,today,True)
    args=retained.command_args(retained.quote(user,g),g);before=retained.fp(http,g);removed=None
    with http.connect()as conn,conn.cursor()as cur:
        role=n.one(cur,'select role_id from erp.app_users where auth_user_id=%s',(user.auth_user_id,));conn.rollback()
    try:
        with ThreadPoolExecutor(max_workers=1)as pool:
            with http.connect()as holder,holder.cursor()as cur:
                pid=cur.execute("select pg_backend_pid(),pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))").fetchone()[0]
                future=pool.submit(user.rpc,'erp_cp7_correct_mandor_v1',args)
                try:
                    observed=waiting(cur,pid,[future],1)
                    removed=permission(http,role)
                finally:holder.rollback()
            reply=future.result(timeout=30)
        assert reply['status']==403 and 'CP7_MANDOR_CORRECTION_DENIED'in str(reply['body']),reply
        assert retained.fp(http,g)==before
        permission(http,role,removed);removed=None
        result=retained.body(user.rpc('erp_cp7_correct_mandor_v1',args))
        after=retained.fp(http,g);assert after==before
        removed=permission(http,role)
        replay=user.rpc('erp_cp7_correct_mandor_v1',args)
        assert replay['status']==403 and 'CP7_MANDOR_CORRECTION_DENIED'in str(replay['body']),replay
        assert retained.fp(http,g)==after
        permission(http,role,removed);removed=None
        assert retained.body(user.rpc('erp_cp7_correct_mandor_v1',args))==result
        with http.connect()as conn,conn.cursor()as cur:
            assert n.one(cur,'select count(*)from cp7_contractor_correction.history_v1 where po_id=%s',(g['po'],))==1
            assert n.one(cur,"select count(*)from cp7_contractor_correction.requests_v1 where payload->>'po_id'=%s",(g['po'],))==1
            conn.rollback()
        return dict(status='PASS',actual_wait=observed,seventh_permission='production.distribution.create',
            revoked_after_wait_refused=True,cached_reply_refused_while_revoked=True,
            restored_right_same_UUID_one_effect=True,stock_HPP_unchanged=True,production_go=False)
    finally:
        if removed is not None:permission(http,role,removed)

def contention(http,today):
    user=http.login('OWNER',label='ow05-sewing-contention');g=retained.prepare(http,today,True)
    args=retained.command_args(retained.quote(user,g),g)
    w=retained.body(user.rpc('erp_cp7_get_sewing_completion_v1',dict(p_group=g['group'])))
    sewing_args=dict(p_payload=dict(action='RECORD',group_id=g['group'],qty_pcs='4',physical_at=g['at'](10).isoformat(),
        review_token=w['review_token'],change_reason='OW05 actual sewing writer contention'),p_request=str(uuid.uuid4()),p_expected=w['group_version'])
    with ThreadPoolExecutor(max_workers=2)as pool:
        with http.connect()as holder,holder.cursor()as cur:
            n.auth.b.api.admin(cur)
            pid=n.one(cur,'select pg_backend_pid()')
            locks=cur.execute('select distinct %s::text||po.contractor_id::text||\':\'||po.model_id::text||\':\'||s.work_component_id::text '
                'from erp.po_work_component_snapshots s join erp.production_orders po on po.id=s.po_id where s.po_id=%s order by 1',('WRATE:',g['po'])).fetchall()
            assert locks
            for(key,)in locks:cur.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',(key,))
            sew=pool.submit(user.rpc,'erp_cp7_save_sewing_completion_v1',sewing_args)
            try:
                observed=waiting(cur,pid,[sew],1)
                started=time.monotonic();correction=pool.submit(user.rpc,'erp_cp7_correct_mandor_v1',args).result(timeout=7)
                elapsed=time.monotonic()-started
                assert correction['status']==500 and correction['body'].get('code')=='55P03'and 'CP7_MANDOR_CORRECTION_BUSY'in str(correction['body']),correction
                assert not sew.done()
            finally:holder.rollback()
        posted=retained.body(sew.result(timeout=30));assert str(posted['result']['wage_amount'])=='16.00'
    stale=user.rpc('erp_cp7_correct_mandor_v1',args)
    assert stale['status']==400 and 'CP7_MANDOR_CORRECTION_STALE_REVIEW'in str(stale['body']),stale
    w=retained.body(user.rpc('erp_cp7_get_sewing_completion_v1',dict(p_group=g['group'])))
    with http.connect()as conn,conn.cursor()as cur:
        event=n.one(cur,"select id::text from erp.sewing_terminal_events e where po_id=%s and event_kind='SELESAI_DIJAHIT'and not exists(select 1 from erp.sewing_terminal_events r where r.reversal_of_id=e.id)",(g['po'],));conn.rollback()
    retained.body(user.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=dict(action='REVERSE',group_id=g['group'],event_id=event,
        review_token=w['review_token'],change_reason='OW05 named inverse after concurrent sewing'),p_request=str(uuid.uuid4()),p_expected=w['group_version'])))
    fresh=retained.command_args(retained.quote(user,g),g);before=retained.fp(http,g)
    with http.connect()as holder,holder.cursor()as cur:
        cur.execute('select id from erp.production_orders where id=%s for update',(g['po'],))
        with ThreadPoolExecutor(max_workers=1)as pool:
            reply=pool.submit(user.rpc,'erp_cp7_correct_mandor_v1',fresh).result(timeout=7)
            assert reply['status']==500 and reply['body'].get('code')=='55P03',reply
        holder.rollback()
    assert retained.fp(http,g)==before
    result=retained.body(user.rpc('erp_cp7_correct_mandor_v1',fresh))
    assert result['status']=='PICKUPS_REPLACED'and retained.fp(http,g)==before
    with http.connect()as conn,conn.cursor()as cur:
        assert n.one(cur,'select count(*)from cp7_contractor_correction.history_v1 where po_id=%s',(g['po'],))==1
        assert n.one(cur,'select count(*)from cp7_contractor_correction.context_v1')==0
        conn.rollback()
    return dict(status='PASS',actual_existing_sewing_writer_wait=observed,correction_busy_elapsed_seconds=round(elapsed,3),
        actual_sewing_completes_after_busy_refusal=True,stale_review_refused=True,
        PO_row_nowait_refusal=True,fresh_same_UUID_retry_one_effect=True,
        all_failed_attempts_atomic=True,private_contexts=0,production_go=False)

def http_cases(http,today):
    return retained.http_cases(http,today)+[(IDS[2],lambda:rights(http,today)),(IDS[3],lambda:contention(http,today))]
