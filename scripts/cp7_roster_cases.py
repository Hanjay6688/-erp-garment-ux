"""P12 roster/rate native oracles. No connected source editor UI claim."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json,threading,time,uuid
import psycopg
import cp7_attendance_read_cases as a
s,auth,b,n,source=a.s,a.auth,a.b,a.n,a.source
PERMS=('finance.attendance.view','finance.attendance.create','finance.attendance.edit_draft')
def view(cur,f,start,end=None,subject=None):return a.read(cur,'WORKERS',subject=subject,**a.scope(f,start,end))
def envelope(w,document):return dict(contractor_id=w['contractor']['id'],date_from=w['date_from'],date_to=w['date_to'],source_token=w['source_token'],document=document)
def initial(f,start,**changes):return dict(contractor_id=f['contractor'],worker_name='P12 roster source',job_description='Jahit',pay_scheme='DAILY',joined_at=str(start),is_active=True,initial_daily_rate='100.123456',rate_effective_from=str(start),reason='P12 deliberate worker source',**changes)
def command(cur,action,p,version=None,key=None,subject=None):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_save_roster_v1(%s,%s,%s,%s)',(action,json.dumps(p),key or uuid.uuid4(),version)).fetchone()[0];b.api.admin(cur);return r
def current(cur,f,start,end=None,subject=None):return view(cur,f,start,end,subject)['page']['rows'][0]
def save(cur,action,f,start,document,version=None,key=None,subject=None,end=None):return command(cur,action,envelope(view(cur,f,start,end,subject),document),version,key,subject)
def admin_actor(cur):
    subject=str(uuid.uuid4());role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
    cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
    for perm in PERMS:cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,perm))
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) values(%s,%s,'P12 roster admin','ADMIN',%s,true)",(uuid.uuid4(),subject,role))
    return subject,role

def cases(cur,today):
    def lifecycle():
        f=source.repair(cur,today);start=today-timedelta(days=6);before=n.facts(cur);code='P12-'+uuid.uuid4().hex[:8];doc=initial(f,start,worker_code=code);p=envelope(view(cur,f,start,today),doc);key=uuid.uuid4()
        created=command(cur,'CREATE_WORKER',p,key=key);assert command(cur,'CREATE_WORKER',p,key=key)==created;wid=created['worker_id'];w=current(cur,f,start,today)
        assert created['status']=='ACTIVE' and created['row_version']==w['row_version'] and w['daily_rate_at_date']=='100.123456'
        rate=dict(worker_id=wid,daily_rate='200.654321',effective_from=str(today-timedelta(days=4)),reason='P12 dated immutable rate')
        save(cur,'SET_RATE',f,start,rate,w['row_version'],end=today)
        old=a.read(cur,'RATES',worker_id=wid,**a.scope(f,start,start));new=a.read(cur,'RATES',worker_id=wid,**a.scope(f,today));assert old['page']['rows'][0]['daily_rate']=='100.123456' and new['page']['rows'][0]['daily_rate']=='200.654321'
        edit={k:v for k,v in doc.items() if k not in('initial_daily_rate','rate_effective_from','worker_code')};edit.update(worker_id=wid,is_active=False,left_at=str(today-timedelta(days=2)),reason='P12 stop employment episode');w=current(cur,f,start,today)
        stopped=save(cur,'UPDATE_WORKER',f,start,edit,w['row_version'],end=today);assert stopped['status']=='INACTIVE'
        edit.update(is_active=True,left_at=None,reactivated_at=str(today),reason='P12 restart with preserved gap');w=current(cur,f,start,today);save(cur,'UPDATE_WORKER',f,start,edit,w['row_version'],end=today)
        # An ordinary edit never erases the worker code the native writer would otherwise null.
        assert cur.execute('select worker_code from erp.contractor_workers where id=%s',(wid,)).fetchone()[0]==code
        episodes=a.read(cur,'EMPLOYMENT',worker_id=wid,**a.scope(f,start,today))['page']['rows'];assert len(episodes)==2 and episodes[0]['date_to']==str(today-timedelta(days=2)) and episodes[1]['date_from']==str(today)
        assert view(cur,f,today-timedelta(days=1))['page']['total']=='0' and n.facts(cur)==before
        return dict(status='PASS',ordinary_native_create_and_exact_replay=True,worker_code_kept_after_update=True,earlier_rate='100.123456',later_rate='200.654321',stop_reactivate_preserves_gap=True,no_stock_hpp_gl_effect=True)
    def history_guard():
        f=source.repair(cur,today);created=save(cur,'CREATE_WORKER',f,today,initial(f,today));wid=created['worker_id']
        period=s.native(cur,'select public.erp_save_attendance_period_v1(%s::jsonb,%s,null,false)',(json.dumps(dict(contractor_id=f['contractor'],period_number='P12-ROSTER-'+uuid.uuid4().hex[:8],period_start=str(today),period_end=str(today),pay_date=str(today),reason='P12 ordinary attendance chronology',attendance=[dict(worker_id=wid,attendance_date=str(today),status='PRESENT')])),uuid.uuid4()))
        s.native(cur,'select public.erp_post_attendance_period_v1(%s,%s,%s,%s)',(s.bc.awp.find(period,'period_id'),'P12 chronology control',uuid.uuid4(),s.bc.awp.find(period,'row_version')))
        before=b.boundary.snapshot(cur);auth.refused(cur,lambda:save(cur,'CREATE_WORKER',f,today,initial(f,today)),'overlap posted attendance history')
        w=current(cur,f,today);edit={k:v for k,v in initial(f,today).items() if k not in('initial_daily_rate','rate_effective_from')};edit.update(worker_id=wid,joined_at=str(today-timedelta(days=1)))
        auth.refused(cur,lambda:save(cur,'UPDATE_WORKER',f,today,edit,w['row_version']),'Original worker start date is immutable');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',posted_attendance_guard_preserved=True,original_start_immutable=True,no_partial_worker_rate_or_episode=True)
    def fields():
        f=source.repair(cur,today);v=view(cur,f,today);doc=initial(f,today);before=b.boundary.snapshot(cur)
        for bad in ({k:x for k,x in doc.items() if k!='initial_daily_rate'},dict(doc,initial_daily_rate=100),dict(doc,initial_daily_rate='-1'),dict(doc,rate_override='1')):
            auth.refused(cur,lambda bad=bad:command(cur,'CREATE_WORKER',envelope(v,bad)),'CP7_ROSTER_FIELDS')
        assert b.boundary.snapshot(cur)==before
        zero=dict(doc,initial_daily_rate='0.000000');save(cur,'CREATE_WORKER',f,today,zero);assert current(cur,f,today)['daily_rate_at_date']=='0.000000'
        return dict(status='PASS',missing_rate_not_defaulted_to_zero=True,numeric_json_refused_preserves_transport_precision=True,negative_or_unknown_fields_atomic=True,explicit_native_zero_distinct=True)
    def stale():
        f=source.repair(cur,today);save(cur,'CREATE_WORKER',f,today,initial(f,today));v=view(cur,f,today);w=v['page']['rows'][0];doc=dict(worker_id=w['id'],daily_rate='200.000001',effective_from=str(today+timedelta(days=1)),reason='P12 next date rate');p=envelope(v,doc)
        # An ordinary native write occurs after the displayed source snapshot.
        a.rate(cur,w['id'],'150.000001',today+timedelta(days=2));before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:command(cur,'SET_RATE',p,w['row_version']),'CP7_ROSTER_VERSION_CHANGED')
        auth.refused(cur,lambda:command(cur,'SET_RATE',p,str(a.version(cur,w['id']))),'CP7_ROSTER_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',native_source_change_after_review=True,exact_worker_version_and_full_source_token_required=True,no_rate_write_on_stale_input=True)
    def access():
        f=source.repair(cur,today);subject,role=admin_actor(cur);p=envelope(view(cur,f,today,subject=subject),initial(f,today));key=uuid.uuid4();r=command(cur,'CREATE_WORKER',p,key=key,subject=subject)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.attendance.create'",(role,));auth.refused(cur,lambda:command(cur,'CREATE_WORKER',p,key=key,subject=subject),'CP7_ROSTER_WRITE_DENIED')
        custom,_=source.procurement.custom(cur,PERMS);auth.refused(cur,lambda:command(cur,'CREATE_WORKER',p,subject=custom),'CP7_ROSTER_OWNER_ADMIN_REQUIRED')
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_roster_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        for who in ('anon','authenticated','service_role','cp7_capture','cp7_attendance_read'):
            assert not cur.execute("select has_table_privilege(%s,'cp7_attendance.roster_requests','SELECT,INSERT,UPDATE,DELETE')",(who,)).fetchone()[0]
            assert not cur.execute("select has_function_privilege(%s,'cp7_attendance.apply_roster(text,jsonb,uuid,text)','EXECUTE')",(who,)).fetchone()[0]
        return dict(status='PASS',native_owner_admin_authority_preserved=True,create_edit_view_permissions_current=True,permission_revoked_cached_replay_denied=True,no_generic_business_dml_or_private_metadata=True)
    def changed_intent():
        f=source.repair(cur,today);p=envelope(view(cur,f,today),initial(f,today));key=uuid.uuid4();command(cur,'CREATE_WORKER',p,key=key);before=b.boundary.snapshot(cur)
        q=dict(p,document=dict(p['document'],worker_name='Changed duplicate intent'));auth.refused(cur,lambda:command(cur,'CREATE_WORKER',q,key=key),'CP7_ROSTER_REQUEST_CHANGED');assert b.boundary.snapshot(cur)==before
        assert cur.execute('select count(*) from erp.contractor_workers where contractor_id=%s',(f['contractor'],)).fetchone()[0]==1
        return dict(status='PASS',same_uuid_changed_intent_refused=True,one_worker_rate_and_employment_source=True)
    return [('P12_ROSTER_'+k,fn) for k,fn in [('LIFECYCLE',lifecycle),('POSTED_HISTORY',history_guard),('FIELDS',fields),('STALE',stale),('ACCESS',access),('CHANGED_INTENT',changed_intent)]]

def races(tools,today):
    def compete(replay):
        with tools.connect() as conn,conn.cursor() as cur:
            f=source.repair(cur,today)
            if not replay:save(cur,'CREATE_WORKER',f,today,initial(f,today))
            v=view(cur,f,today);p=envelope(v,initial(f,today));version=None
            if not replay:
                w=v['page']['rows'][0];version=w['row_version'];p=envelope(v,dict(worker_id=w['id'],daily_rate='200.000001',effective_from=str(today+timedelta(days=1)),reason='P12 competing worker rate'))
            conn.commit()
        gate=threading.Barrier(2);key=uuid.uuid4()
        def send(i):
            with tools.connect() as conn,conn.cursor() as cur:
                gate.wait()
                try:
                    q=p if replay or i==0 else dict(p,document=dict(p['document'],daily_rate='300.000001'));r=command(cur,'CREATE_WORKER' if replay else 'SET_RATE',q,version,key if replay else uuid.uuid4());conn.commit();return ('PASS',r)
                except psycopg.Error as e:conn.rollback();return ('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(send,range(2)))
        if replay:assert rows[0]==rows[1] and rows[0][0]=='PASS',rows
        else:assert sorted(x[0] for x in rows)==['PASS','REFUSED'],rows
        with tools.connect() as conn,conn.cursor() as cur:
            count=cur.execute('select count(*) from erp.worker_daily_rate_versions r join erp.contractor_workers w on w.id=r.worker_id where w.contractor_id=%s',(f['contractor'],)).fetchone()[0];assert count==(1 if replay else 2)
        return dict(status='PASS',same_create_uuid=replay,one_native_source_change=True,exact_replay_or_one_version_winner=True)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f=source.repair(cur,today);save(cur,'CREATE_WORKER',f,today,initial(f,today));subject,role=admin_actor(cur);v=view(cur,f,today,subject=subject);w=v['page']['rows'][0];p=envelope(v,dict(worker_id=w['id'],daily_rate='200.123456',effective_from=str(today+timedelta(days=1)),reason='P12 authorization after wait'));conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.contractor_workers where id=%s for update',(w['id'],))
            holder_pid=h.execute('select pg_backend_pid()').fetchone()[0];ready=threading.Event();sender_pid=[]
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    sender_pid.append(cur.execute('select pg_backend_pid()').fetchone()[0]);ready.set()
                    try:command(cur,'SET_RATE',p,w['row_version'],subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    assert ready.wait(5),'ROSTER_SENDER_NOT_STARTED'
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()')
                            blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and pid=%s and wait_event_type='Lock' and %s=any(pg_blocking_pids(pid)))",(sender_pid[0],holder_pid)).fetchone()[0]
                            if blocked or future.done():break
                            time.sleep(.03)
                    assert blocked,('EXPECTED_ROSTER_ROW_WAIT',future.result() if future.done() else 'sender pending')
                    with tools.connect() as writer,writer.cursor() as c:c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.attendance.edit_draft'",(role,));writer.commit()
                finally:holder.rollback()
                result=future.result(30)
        assert 'CP7_ROSTER_WRITE_DENIED' in result,result
        with tools.connect() as conn,conn.cursor() as cur:assert str(a.version(cur,w['id']))==w['row_version']
        return dict(status='PASS',permission_revoked_during_actual_worker_row_wait=True,no_partial_rate_change=True)
    return [('P12_ROSTER_RACE_CREATE_REPLAY',lambda:compete(True)),('P12_ROSTER_RACE_RATE_VERSION',lambda:compete(False)),('P12_ROSTER_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        user=http.login('ADMIN','p12-roster-source')
        with http.connect() as conn,conn.cursor() as cur:f=source.repair(cur,today);admin_actor(cur);before=n.facts(cur);conn.commit()
        def read():
            r=user.rpc('erp_cp7_get_attendance_workspace_v1',dict(p_section='WORKERS',p_query=a.scope(f,today)));assert r['status']==200,r;return r['body']
        v=read();p=dict(p_action='CREATE_WORKER',p_payload=envelope(v,initial(f,today)),p_request=str(uuid.uuid4()),p_expected=None)
        assert http.anon_rpc('erp_cp7_save_roster_v1',p)['status'] in(401,403)
        created=user.rpc('erp_cp7_save_roster_v1',p);assert created['status']==200,created;assert user.rpc('erp_cp7_save_roster_v1',p)['body']==created['body']
        v=read();w=v['page']['rows'][0];assert w['daily_rate_at_date']=='100.123456'
        p=dict(p_action='SET_RATE',p_payload=envelope(v,dict(worker_id=w['id'],daily_rate='200.654321',effective_from=str(today+timedelta(days=1)),reason='P12 HTTP future rate source')),p_request=str(uuid.uuid4()),p_expected=w['row_version'])
        changed=user.rpc('erp_cp7_save_roster_v1',p);assert changed['status']==200,changed;assert user.rpc('erp_cp7_save_roster_v1',p)['body']==changed['body'];assert read()['page']['rows'][0]['daily_rate_at_date']=='100.123456'
        with http.connect() as conn,conn.cursor() as cur:assert n.facts(cur)==before;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));conn.commit()
        assert user.rpc('erp_cp7_save_roster_v1',p)['status']==403
        return dict(status='PASS',real_auth_admin_create_and_rate=True,exact_http_replay=True,earlier_rate_preserved='100.123456',future_rate='200.654321',anonymous_and_deactivated_denied=True,no_financial_effect=True,no_roster_browser_claim=True)
    return [('P12_ROSTER_HTTP',flow)]
