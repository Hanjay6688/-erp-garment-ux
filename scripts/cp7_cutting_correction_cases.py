"""Actual Native unpicked cutting inverse; fixed 19 separate executions."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import copy,json,threading,time,uuid
import psycopg
import cp7_cutting_source_cases as cutting
import cp7_cutting_correction_bundle as bundle
b,auth=cutting.b,cutting.auth
READ='erp_cp7_get_cutting_correction_v1'
RPC='erp_cp7_reopen_cutting_v1'
REQUIRED=dict(native=10,races=4,http=3,browser=2)
EXPECTED=sum(REQUIRED.values())
NAMES=('EXACT_STOCK_GL_DRAFT','READ_ONLY_CAPABILITIES','REPLAY','CLOSED_FIELDS',
    'STALE_SOURCE','PICKUP_DOWNSTREAM','ATOMIC_LATE_FAILURE','IMMUTABLE_HISTORY','CURRENT_AUTH','CLOSED_PERIOD')

def read(cur,f,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_cutting_correction_v1(%s)',(f['group'],)).fetchone()[0]
    b.api.admin(cur);return r
def payload(cur,f,subject=None):
    w=read(cur,f,subject)
    return dict(group_id=w['group_id'],po_id=w['po_id'],review_token=w['review_token'],
        change_reason='Potongan belum dijemput dan bahan asal sudah diperiksa'),w['row_version']
def command(cur,p,version,key=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_reopen_cutting_v1(%s,%s,%s)',(json.dumps(p),key or uuid.uuid4(),version)).fetchone()[0]
    b.api.admin(cur);return r
def private_state(cur):
    b.api.admin(cur)
    return {t:cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),'[]')::text)from "+bundle.SCHEMA+'.'+t+' x').fetchone()[0]for t in bundle.TABLES}
def facts(cur,f):
    b.api.admin(cur)
    return cur.execute("select cp7_cutting_correction.snapshot(%s)-array['movements','period','materials','journals']",(f['group'],)).fetchone()[0]
def gl(cur):
    b.api.admin(cur)
    return {str(k):v for k,v in cur.execute('select account_id,sum(debit-credit)from erp.journal_lines group by account_id').fetchall()}
def stock(cur,f):
    b.api.admin(cur)
    return cur.execute('select coalesce(sum(m.qty_signed),0)from erp.material_stock_movements m join erp.cutting_groups g on g.source_location_id=m.location_id where g.id=%s and m.roll_id=%s',(f['group'],f['roll'])).fetchone()[0]
def fixture(cur,today):
    f=cutting.posted(cur,today);w=read(cur,f);assert w['eligible']and w['blockers']==[]
    f.update(number=w['number'],version=w['row_version'],original=facts(cur,f),before_gl=gl(cur))
    f['roll'],f['qty']=cur.execute('select roll_id::text,qty_issued from erp.cutting_group_rolls where cutting_group_id=%s',(f['group'],)).fetchone()
    f['before_stock']=stock(cur,f)
    f['issue_lines']={str(k):v for k,v in cur.execute("select l.account_id,sum(l.debit-l.credit)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_type='CUTTING_MATERIAL_ISSUE'and j.source_id=%s group by l.account_id",(f['group'],)).fetchall()}
    f['original_movements']=cur.execute("select jsonb_agg(to_jsonb(m)order by m.id)from erp.material_stock_movements m where m.source_type='CUTTING_GROUP'and m.source_id=%s",(f['group'],)).fetchone()[0]
    return f
def verify_effect(cur,f,p,r,key=None):
    assert r['contract_version']=='cp7.cutting-reopen-outcome.v1'and r['kind']=='COMMITTED_OUTCOME'and r['action']=='REOPEN_POSTED'
    assert r['group_id']==f['group']and r['po_id']==f['po']and r['number']==f['number']and r['status']=='DRAFT_FOR_CORRECTION'
    if key is not None:assert r['request_id']==str(key)
    assert stock(cur,f)==f['before_stock']+f['qty']
    after=gl(cur)
    for k in after.keys()|f['before_gl'].keys():assert after.get(k,0)-f['before_gl'].get(k,0)==-f['issue_lines'].get(k,0),(k,after,f['before_gl'],f['issue_lines'])
    now=facts(cur,f);original=copy.deepcopy(f['original'])
    for key in ('material_issue_posted','material_return_posted','status','row_version','updated_at'):
        original['group'].pop(key,None);now['group'].pop(key,None)
    assert now==original,(now,original)
    assert cur.execute("select jsonb_agg(to_jsonb(m)order by m.id)from erp.material_stock_movements m where m.source_type='CUTTING_GROUP'and m.source_id=%s",(f['group'],)).fetchone()[0]==f['original_movements']
    h=cur.execute('select original_source,Native_response,reason from '+bundle.SCHEMA+'.history where request_id=%s and group_id=%s',(r['request_id'],f['group'])).fetchone()
    assert h and h[0]['group']['material_issue_posted']and h[1]==r['Native_response']and h[2]==p['change_reason']
    auth.actor(cur)
    draft=cur.execute('select public.erp_get_cutting_workspace_v2(p_selected_order_id=>%s,p_selected_draft_id=>%s)',(f['po'],f['group'])).fetchone()[0]
    b.api.admin(cur)
    assert draft['selected_draft']['cutting_group_id']==f['group']and draft['selected_draft']['po_id']==f['po']and draft['selected_draft']['editable']
    assert not read(cur,f)['eligible']
    return draft['selected_draft']
def refusal(cur,p,version,code='',key=None,subject=None):
    before=b.boundary.snapshot(cur);private=private_state(cur)
    detail=auth.refused(cur,lambda:command(cur,p,version,key,subject),code)
    assert b.boundary.snapshot(cur)==before and private_state(cur)==private
    return detail
def cases(cur,today):
    def exact():
        f=fixture(cur,today);p,v=payload(cur,f);key=uuid.uuid4();r=command(cur,p,v,key);d=verify_effect(cur,f,p,r,key)
        prod=cutting.qc.physical.b.chain.production
        payload_draft=dict(id=f['group'],action='SAVE_DRAFT',po_id=f['po'],pattern_id=d['pattern_id'],source_location_id=d['source_location_id'],cut_at=d['cut_at'],
            change_reason='Explicit following Native draft correction; no physical posting',size_slots=[{k:s[k]for k in('slot_no','size_id','drawing_no','label_override')}for s in d['size_slots']],
            rolls=[dict(roll_id=f['roll'],qty_issued=6,qty_consumed=6,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=7)])])
        saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload_draft,expected_version=int(r['row_version']));b.api.admin(cur)
        assert saved['total_pieces']==7 and not saved['material_issue_posted']and stock(cur,f)==f['before_stock']+f['qty']
        assert cur.execute('select original_source->\'yields\'from '+bundle.SCHEMA+'.history where request_id=%s',(key,)).fetchone()[0]==f['original']['yields']
        return dict(status='PASS',Native_inverse_stock_restored_and_GL_neutral=True,old_group_roll_size_clock_facts_and_original_movements_preserved=True,exact_following_Native_draft_edit7_PCS_without_second_stock_out=True)
    def readonly():
        f=fixture(cur,today);before=b.boundary.snapshot(cur);private=private_state(cur);w=read(cur,f);bundle.verify(cur)
        assert w['business_DML']is False and b.boundary.snapshot(cur)==before and private_state(cur)==private
        return dict(status='PASS',exact_source_readonly_and_closed_private_capabilities=True)
    def replay():
        f=fixture(cur,today);p,v=payload(cur,f);key=uuid.uuid4();r=command(cur,p,v,key);verify_effect(cur,f,p,r,key)
        before=b.boundary.snapshot(cur);private=private_state(cur);assert command(cur,p,v,key)==r and b.boundary.snapshot(cur)==before and private_state(cur)==private
        refusal(cur,dict(p,change_reason='A different reason must not replay'),v,'CP7_CUTTING_CORRECTION_REQUEST_CHANGED',key)
        return dict(status='PASS',same_UUID_exact_outcome_no_second_inverse_changed_payload_refused=True)
    def fields():
        f=fixture(cur,today);p,v=payload(cur,f)
        for bad in(dict(p,qty_issued=0),dict(p,group_id=4),dict(p,po_id=''),dict(p,review_token=''),dict(p,change_reason='')):refusal(cur,bad,v,'CP7_CUTTING_CORRECTION_FIELDS')
        refusal(cur,p,str(int(v)+1),'CP7_CUTTING_CORRECTION_STALE_REVIEW')
        refusal(cur,dict(p,po_id=str(uuid.uuid4())),v,'CP7_CUTTING_CORRECTION_STALE_REVIEW')
        return dict(status='PASS',closed_fields_exact_group_PO_version_and_review_token=True)
    def stale():
        f=fixture(cur,today);p,v=payload(cur,f)
        cur.execute('update erp.material_rolls set roll_number=roll_number||\'-CHANGED\'where id=%s',(f['roll'],))
        assert read(cur,f)['row_version']==v;refusal(cur,p,v,'CP7_CUTTING_CORRECTION_STALE_REVIEW')
        return dict(status='PASS',actual_roll_source_change_without_group_version_bump_retires_review=True)
    def dependency():
        f=cutting.advanced(cur,today);w=read(cur,f);assert not w['eligible']and any(b['kind']=='PICKUP'for b in w['blockers'])and any(b['kind']=='DOWNSTREAM'for b in w['blockers'])
        p,v=payload(cur,f);refusal(cur,p,v,'CP7_CUTTING_CORRECTION_DEPENDENCIES')
        return dict(status='PASS',actual_Native_pickup_sewing_QC_dependencies_named_and_no_inverse=True)
    def atomic():
        f=fixture(cur,today);p,v=payload(cur,f)
        cur.execute("create function public.cp7_cutting_late_fail()returns trigger language plpgsql as $$begin raise exception 'CP7_TEST_CUTTING_LATE_FAILURE';end$$;create trigger cp7_cutting_late_fail before insert on cp7_cutting_correction.history for each row execute function public.cp7_cutting_late_fail()",prepare=False)
        refusal(cur,p,v,'CP7_TEST_CUTTING_LATE_FAILURE');assert read(cur,f)['eligible']
        return dict(status='PASS',failure_after_Native_inverse_rolls_back_all_stock_GL_group_and_UUID_receipts=True)
    def immutable():
        f=fixture(cur,today);p,v=payload(cur,f);r=command(cur,p,v);verify_effect(cur,f,p,r)
        before=b.boundary.snapshot(cur);private=private_state(cur)
        for sql in('update '+bundle.SCHEMA+'.history set reason=reason','delete from '+bundle.SCHEMA+'.history','truncate '+bundle.SCHEMA+'.history'):
            auth.refused(cur,lambda:cur.execute(sql),'CP7_CUTTING_CORRECTION_HISTORY_IMMUTABLE')
        assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        return dict(status='PASS',whole_original_source_immutable_update_delete_truncate=True)
    def authority():
        f=fixture(cur,today);subject,_=auth.custom_actor(cur)
        role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
        cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));p,v=payload(cur,f,subject);key=uuid.uuid4();r=command(cur,p,v,key,subject);verify_effect(cur,f,p,r,key)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.cutting.post'",(role,))
        refusal(cur,p,v,'CP7_CUTTING_CORRECTION_DENIED',key,subject)
        auth.refused(cur,lambda:read(cur,f,subject),'CP7_CUTTING_CORRECTION_DENIED')
        return dict(status='PASS',current_permission_required_before_cached_outcome_and_source_metadata=True)
    def closed():
        f=fixture(cur,today);through=today-cutting.timedelta(days=1)
        b.boundary.historical.prior.set_open_period(cur,through)
        before=cur.execute('select balance_date,account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(through,)).fetchall()
        p,v=payload(cur,f);r=command(cur,p,v);verify_effect(cur,f,p,r)
        assert cur.execute('select balance_date,account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(through,)).fetchall()==before
        return dict(status='PASS',Native_current_open_inverse_preserves_closed_daily_history_and_original_cut_clock=True)
    operations=(exact,readonly,replay,fields,stale,dependency,atomic,immutable,authority,closed)
    assert len(operations)==len(NAMES)==REQUIRED['native']
    return [('CP7_CUTTING_REOPEN_'+name,operation)for name,operation in zip(NAMES,operations)]

def races(tools,today):
    def competing(same=False):
        with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p,v=payload(cur,f);conn.commit()
        barrier=threading.Barrier(2);keys=[uuid.uuid4(),uuid.uuid4()]
        if same:keys[1]=keys[0]
        def send(key):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait()
                try:r=command(cur,p,v,key);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e)
        with ThreadPoolExecutor(max_workers=2)as pool:rows=[j.result(60)for j in[pool.submit(send,key)for key in keys]]
        wins=[r for r in rows if isinstance(r,dict)];losses=[r for r in rows if isinstance(r,str)]
        if same:assert len(wins)==2 and wins[0]==wins[1],rows
        else:assert len(wins)==len(losses)==1 and'CP7_CUTTING_CORRECTION_STALE_REVIEW'in losses[0],rows
        with tools.connect()as conn,conn.cursor()as cur:
            verify_effect(cur,f,p,wins[0]);assert cur.execute('select count(*)from '+bundle.SCHEMA+'.history where group_id=%s',(f['group'],)).fetchone()[0]==1
        return dict(status='PASS',actual_two_sessions_observed_same_UUID=same,one_Native_inverse=True)
    def revoked_wait(native_wait=False):
        with tools.connect()as conn,conn.cursor()as cur:
            f=fixture(cur,today);subject,_=auth.custom_actor(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));p,v=payload(cur,f,subject);conn.commit()
        pid=[];started=threading.Event()
        with tools.connect()as holder,holder.cursor()as held:
            holder_pid=held.execute('select pg_backend_pid()').fetchone()[0]
            if native_wait:held.execute('select id from erp.material_rolls where id=%s for update',(f['roll'],))
            else:held.execute('select id from erp.cutting_groups where id=%s for update',(f['group'],))
            def send():
                with tools.connect()as conn,conn.cursor()as cur:
                    pid.append(cur.execute('select pg_backend_pid()').fetchone()[0]);started.set()
                    try:result=command(cur,p,v,subject=subject);conn.commit();return result
                    except psycopg.Error as e:conn.rollback();return str(e)
            with ThreadPoolExecutor(max_workers=1)as pool:
                job=pool.submit(send);assert started.wait(5);observed=False
                try:
                    deadline=time.monotonic()+8
                    while time.monotonic()<deadline:
                        held.execute('select pg_stat_clear_snapshot()')
                        if holder_pid in held.execute('select pg_blocking_pids(%s)',(pid[0],)).fetchone()[0]:observed=True;break
                        time.sleep(.02)
                    assert observed,'CUTTING_ACTUAL_LOCK_WAIT_NOT_OBSERVED'
                    held.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.cutting.post'",(role,))
                    b.api.admin(held);before=b.boundary.snapshot(held);private=private_state(held);holder.commit()
                finally:holder.rollback()
                result=job.result(60)
        assert isinstance(result,str)and'CP7_CUTTING_CORRECTION_DENIED'in result,result
        with tools.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        return dict(status='PASS',actual_holder_worker_lock_wait=True,current_permission_revocation_no_effect=True,wait_inside_Native_stock_path=native_wait)
    return [('CP7_CUTTING_REOPEN_RACE_SAME_UUID',lambda:competing(True)),('CP7_CUTTING_REOPEN_RACE_COMPETING',competing),
        ('CP7_CUTTING_REOPEN_RACE_GROUP_REVOKE',revoked_wait),('CP7_CUTTING_REOPEN_RACE_NATIVE_REVOKE',lambda:revoked_wait(True))]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','cutting-correction-owner')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p,v=payload(cur,f);conn.commit()
        key=uuid.uuid4();args=dict(p_payload=p,p_request=str(key),p_expected=v)
        assert http.anon_rpc(RPC,args)['status']in(401,403)and http.anon_rpc(READ,dict(p_group=f['group']))['status']in(401,403)
        reply=owner.rpc(RPC,args);assert reply['status']==200,reply
        assert owner.rpc(RPC,args)['body']==reply['body']
        with http.connect()as conn,conn.cursor()as cur:verify_effect(cur,f,p,reply['body'],key);conn.rollback()
        return dict(status='PASS',real_Auth_Native_inverse_committed_exact_UUID_stock_GL_and_following_draft=True)
    def readonly():
        owner=http.login('OWNER','cutting-correction-reader')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);before=b.boundary.snapshot(cur);private=private_state(cur);conn.commit()
        reply=owner.rpc(READ,dict(p_group=f['group']));assert reply['status']==200 and reply['body']['eligible']and reply['body']['business_DML']is False,reply
        with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before and private_state(cur)==private;conn.rollback()
        return dict(status='PASS',real_Auth_exact_group_PO_source_read_no_business_DML=True)
    def revoke():
        admin=http.login('ADMIN','cutting-correction-admin')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p,v=payload(cur,f);conn.commit()
        args=dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=v);reply=admin.rpc(RPC,args);assert reply['status']==200,reply
        with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(admin.auth_user_id,));conn.commit()
        assert admin.rpc(RPC,args)['status']==403 and admin.rpc(READ,dict(p_group=f['group']))['status']==403
        return dict(status='PASS',real_Auth_current_deactivation_denies_cached_receipt_and_metadata=True)
    return [('CP7_CUTTING_REOPEN_HTTP_COMMIT_REPLAY',flow),('CP7_CUTTING_REOPEN_HTTP_READONLY',readonly),('CP7_CUTTING_REOPEN_HTTP_CURRENT_AUTH',revoke)]
