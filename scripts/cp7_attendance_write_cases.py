"""P12 native attendance commands. No connected attendance-entry UI claim."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import json,threading,time,uuid
import psycopg
import cp7_roster_cases as roster
import cp7_settlement_read_cases as review
a,s,auth,b,n,source=roster.a,roster.s,roster.auth,roster.b,roster.n,roster.source
PERMS=('finance.attendance.view','finance.attendance.create','finance.attendance.edit_draft','finance.attendance.post','finance.attendance.reverse')

def fixture(cur,today,two=False):
    f=source.repair(cur,today);cur.execute('update erp.contractors set attendance_required=true where id=%s',(f['contractor'],));f['workers']=[a.worker(cur,f,today,rate='100.123456')[0]]
    if two:f['workers'].append(a.worker(cur,f,today,rate='50.000000',name='P12 second source worker')[0])
    return f

def document(f,today,**changes):
    d=dict(contractor_id=f['contractor'],period_number='P12-SOURCE-'+uuid.uuid4().hex[:10],period_start=str(today),period_end=str(today),pay_date=str(today),reason='P12 deliberate daily marks',attendance=[dict(worker_id=wid,attendance_date=str(today),status='PRESENT' if i==0 else 'HALF_DAY',paid_fraction='1.0000' if i==0 else '0.5000') for i,wid in enumerate(f['workers'])]);d.update(changes);return d

def scope(cur,f,start,end=None,subject=None):return a.read(cur,'PERIODS',subject=subject,**a.scope(f,start,end))
def envelope(cur,f,start,doc,end=None,subject=None):return roster.envelope(scope(cur,f,start,end,subject),doc)
def command(cur,action,p,version=None,key=None,subject=None):
    auth.actor(cur,subject)
    if action=='PREVIEW':r=cur.execute('select public.erp_cp7_preview_attendance_v1(%s,%s)',(json.dumps(p),version)).fetchone()[0]
    else:r=cur.execute('select public.erp_cp7_save_attendance_v1(%s,%s,%s,%s)',(action,json.dumps(p),key or uuid.uuid4(),version)).fetchone()[0]
    b.api.admin(cur);return r

def save(cur,f,today,d=None,version=None,subject=None):return command(cur,'SAVE',envelope(cur,f,today,d or document(f,today),subject=subject),version,subject=subject)
def period(cur,f,today,pid,subject=None):return next(x for x in scope(cur,f,today,subject=subject)['page']['rows'] if x['id']==pid)
def act(cur,action,f,today,pid,subject=None,key=None):
    h=period(cur,f,today,pid,subject);return command(cur,action,envelope(cur,f,today,dict(period_id=pid,reason='P12 reviewed attendance lifecycle'),subject=subject),h['row_version'],key,subject)
def records(cur,pid):return cur.execute('select id::text,worker_id::text,attendance_date,status,paid_fraction::text,record_lifecycle from erp.attendance_records where attendance_period_id=%s order by worker_id,attendance_date',(pid,)).fetchall()
def correction(cur,f,today,pid):
    rows=records(cur,pid);return document(f,today,correction_of_period_id=pid,attendance=[dict(worker_id=x[1],attendance_date=str(x[2]),status='ABSENT',paid_fraction='0.0000',supersedes_attendance_record_id=x[0]) for x in rows])

def entry(cur,f,start,end=None,pid=None,offset=0,limit=100):
    auth.actor(cur);r=cur.execute('select public.erp_cp7_get_attendance_entry_v1(%s)',(json.dumps(dict(a.scope(f,start,end),period_id=pid,offset=offset,limit=limit)),)).fetchone()[0];b.api.admin(cur);return r

def cases(cur,today):
    def lifecycle():
        f=fixture(cur,today,True);doc=document(f,today);p=envelope(cur,f,today,doc);before=b.boundary.snapshot(cur);financial=n.facts(cur)
        preview=command(cur,'PREVIEW',p);assert preview['kind']=='READ_ONLY_PREVIEW' and preview['line_count']=='2' and D(preview['paid_day_equivalent'])==D('1.5') and D(preview['estimated_amount'])==D('125.123456')
        assert b.boundary.snapshot(cur)==before and cur.execute('select count(*) from cp7_attendance.command_context').fetchone()[0]==0
        key=uuid.uuid4();draft=command(cur,'SAVE',p,key=key);assert command(cur,'SAVE',p,key=key)==draft;pid=draft['period_id'];assert all(r[5]=='DRAFT' for r in records(cur,pid));assert n.facts(cur)==financial
        h=period(cur,f,today,pid);p=envelope(cur,f,today,dict(period_id=pid,reason='P12 complete period posting'));key=uuid.uuid4();posted=command(cur,'POST',p,h['row_version'],key);assert command(cur,'POST',p,h['row_version'],key)==posted and posted['status']=='POSTED'
        assert all(r[5]=='POSTED' for r in records(cur,pid)) and n.facts(cur)==financial
        act(cur,'REVERSE',f,today,pid);assert all(r[5]=='REVERSED' for r in records(cur,pid)) and n.facts(cur)==financial
        return dict(status='PASS',native_preview_no_business_write=True,exact_preview='125.123456',paid_days='1.5',save_post_reverse_exact_replay=True,draft_not_payroll_cost=True,no_stock_hpp_gl_effect=True)
    def blanks():
        f=fixture(cur,today,True);doc=document(f,today);draft=save(cur,f,today,doc);pid=draft['period_id'];frozen=b.boundary.snapshot(cur);auth.refused(cur,lambda:save(cur,f,today,document(f,today)),'Active attendance periods for one contractor cannot overlap');assert b.boundary.snapshot(cur)==frozen;h=period(cur,f,today,pid);doc.update(period_id=pid,attendance=doc['attendance'][:1]);save(cur,f,today,doc,h['row_version']);assert len(records(cur,pid))==1
        before=b.boundary.snapshot(cur);auth.refused(cur,lambda:act(cur,'POST',f,today,pid),'unrecorded eligible worker/day cells');assert b.boundary.snapshot(cur)==before and period(cur,f,today,pid)['status']=='DRAFT'
        doc['attendance']=document(f,today)['attendance'];h=period(cur,f,today,pid);save(cur,f,today,doc,h['row_version']);act(cur,'POST',f,today,pid);assert len(records(cur,pid))==2
        return dict(status='PASS',omitted_draft_cell_deleted_to_unrecorded=True,blank_not_absent_or_off=True,incomplete_post_atomic=True,complete_native_matrix_posts=True)
    def dated_rates():
        f=fixture(cur,today);a.rate(cur,f['workers'][0],'200.654321',today+timedelta(days=1));old=command(cur,'PREVIEW',envelope(cur,f,today,document(f,today)));future=today+timedelta(days=1);new=command(cur,'PREVIEW',envelope(cur,f,future,document(f,future)))
        assert D(old['estimated_amount'])==D('100.123456') and D(new['estimated_amount'])==D('200.654321')
        assert cur.execute('select count(*) from erp.attendance_periods where contractor_id=%s',(f['contractor'],)).fetchone()[0]==0
        return dict(status='PASS',native_dated_rate_not_roster_cache=True,old='100.123456',future='200.654321',preview_no_period_or_payroll=True)
    def correction_lineage():
        f=fixture(cur,today,True);original=save(cur,f,today)['period_id'];act(cur,'POST',f,today,original);doc=correction(cur,f,today,original);before=b.boundary.snapshot(cur)
        bad=dict(doc,attendance=doc['attendance'][:1]);auth.refused(cur,lambda:save(cur,f,today,bad),'explicitly supersede every source attendance row');assert b.boundary.snapshot(cur)==before
        new=save(cur,f,today,doc)['period_id'];act(cur,'POST',f,today,new);assert period(cur,f,today,original)['status']=='CORRECTED' and all(r[5]=='CORRECTED' for r in records(cur,original))
        act(cur,'REVERSE',f,today,new);assert period(cur,f,today,original)['status']=='POSTED' and all(r[5]=='POSTED' for r in records(cur,original));assert all(r[5]=='REVERSED' for r in records(cur,new))
        return dict(status='PASS',every_source_row_explicitly_superseded=True,original_preserved_corrected=True,reverse_correction_restores_original=True)
    def consumed():
        f=review.fixture(cur,today);cur.execute('update erp.contractors set attendance_required=true where id=%s',(f['contractor'],));f['workers']=[a.worker(cur,f,today,rate='100.000000')[0]]
        pid=save(cur,f,today)['period_id'];act(cur,'POST',f,today,pid);before=n.facts(cur);s.act(cur,'PREPARE',s.doc(cur,f['payroll']));assert s.doc(cur,f['payroll'])['attendance_total']=='100.00'
        frozen=b.boundary.snapshot(cur);auth.refused(cur,lambda:act(cur,'REVERSE',f,today,pid),'consuming payroll to be reversed first');auth.refused(cur,lambda:save(cur,f,today,correction(cur,f,today,pid)),'consuming payroll to be reversed first');assert b.boundary.snapshot(cur)==frozen
        s.act(cur,'CANCEL',s.doc(cur,f['payroll']));act(cur,'REVERSE',f,today,pid);assert n.facts(cur)==before
        return dict(status='PASS',ordinary_attendance_feeds_prepared_payroll='100.00',active_payroll_blocks_correction_and_reverse=True,cancel_payroll_then_reverse_attendance=True,no_early_gl_or_physical_effect=True)
    def access():
        f=fixture(cur,today);subject,role=source.procurement.custom(cur,PERMS);p=envelope(cur,f,today,document(f,today),subject=subject);key=uuid.uuid4();draft=command(cur,'SAVE',p,key=key,subject=subject);pid=draft['period_id'];act(cur,'POST',f,today,pid,subject)
        auth.refused(cur,lambda:act(cur,'REVERSE',f,today,pid,subject),'CP7_ATTENDANCE_OWNER_ADMIN_REQUIRED');auth.refused(cur,lambda:save(cur,f,today,correction(cur,f,today,pid),subject=subject),'CP7_ATTENDANCE_OWNER_ADMIN_REQUIRED')
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.attendance.create'",(role,));auth.refused(cur,lambda:command(cur,'SAVE',p,key=key,subject=subject),'CP7_ATTENDANCE_WRITE_DENIED')
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_attendance_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        for who in ('anon','authenticated','service_role','cp7_capture','cp7_attendance_read','cp7_roster_write'):
            assert not cur.execute("select has_table_privilege(%s,'cp7_attendance.command_context','SELECT,INSERT,UPDATE,DELETE')",(who,)).fetchone()[0]
            assert not cur.execute("select has_function_privilege(%s,'cp7_attendance.apply_command(text,jsonb,uuid,text)','EXECUTE')",(who,)).fetchone()[0]
        assert cur.execute('select count(*) from cp7_attendance.command_context').fetchone()[0]==0
        return dict(status='PASS',custom_authorized_create_post=True,correction_reverse_keep_native_owner_admin=True,revoked_cached_replay_denied=True,private_context_not_forgeable=True,no_generic_business_table_access=True)
    def stale():
        f=fixture(cur,today);draft=save(cur,f,today);pid=draft['period_id'];h=period(cur,f,today,pid);doc=document(f,today,period_id=pid);p=envelope(cur,f,today,doc)
        cur.execute('update erp.attendance_periods set notes=%s where id=%s',('P12 ordinary source change',pid));before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,'SAVE',p,h['row_version']),'CP7_ATTENDANCE_VERSION_CHANGED');assert b.boundary.snapshot(cur)==before
        h=period(cur,f,today,pid);p=envelope(cur,f,today,doc);a.rate(cur,f['workers'][0],'200.123456',today+timedelta(days=1));before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,'SAVE',p,h['row_version']),'CP7_ATTENDANCE_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',exact_period_version_required=True,full_native_source_revision_required=True,no_partial_draft_edit=True)
    def fields_intent():
        f=fixture(cur,today);doc=document(f,today);p=envelope(cur,f,today,doc);before=b.boundary.snapshot(cur)
        for line in ({k:v for k,v in doc['attendance'][0].items() if k!='status'},dict(doc['attendance'][0],paid_fraction=1),dict(doc['attendance'][0],extra='forged')):
            auth.refused(cur,lambda line=line:command(cur,'SAVE',dict(p,document=dict(doc,attendance=[line]))),'CP7_ATTENDANCE_LINE_FIELDS')
        for line in (dict(doc['attendance'][0],status='HALF_DAY',paid_fraction='0.7500'),dict(doc['attendance'][0],status='ABSENT',paid_fraction='1.0000')):
            auth.refused(cur,lambda line=line:command(cur,'SAVE',dict(p,document=dict(doc,attendance=[line]))),'CP7_ATTENDANCE_LINE_FRACTION')
        assert b.boundary.snapshot(cur)==before
        key=uuid.uuid4();command(cur,'SAVE',p,key=key);before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,'SAVE',dict(p,document=dict(doc,reason='Changed request meaning')),key=key),'CP7_ATTENDANCE_REQUEST_CHANGED');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',missing_mark_not_default_present=True,string_exact_fraction_required=True,half_day_and_absence_meaning_explicit=True,same_uuid_changed_intent_refused=True)
    def matrix_pages():
        f=source.repair(cur,today);cur.execute('update erp.contractors set attendance_required=true where id=%s',(f['contractor'],));start=today-timedelta(days=2);wid,wp=a.worker(cur,f,start);a.rate(cur,wid,'200.654321',today-timedelta(days=1));a.stop(cur,wid,wp,today-timedelta(days=1));other,_=a.worker(cur,f,today,rate='50.000000',name='P12 current matrix worker');before=b.boundary.snapshot(cur)
        pages=[entry(cur,f,start,today,offset=i,limit=1) for i in range(3)];assert all(p['page']['total']=='3' for p in pages);assert len({p['source_token'] for p in pages})==1
        rows=[p['page']['rows'][0] for p in pages];assert [r['daily_rate'] for r in rows]==['100.123456','200.654321','50.000000'];assert [r['date'] for r in rows]==[str(start),str(today-timedelta(days=1)),str(today)];assert all(r['eligible'] and r['required'] and r['record'] is None for r in rows)
        assert pages[0]['page']['next_offset']==1 and pages[1]['page']['next_offset']==2 and pages[2]['page']['next_offset'] is None
        zone=cur.execute('show timezone').fetchone()[0];cur.execute("select set_config('TimeZone','America/Los_Angeles',true)");assert entry(cur,f,start,today,limit=1)==pages[0];cur.execute("select set_config('TimeZone',%s,true)",(zone,));assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',three_eligible_historical_cells_paged_completely=True,inactive_current_status_not_history_filter=True,exact_daily_rates=['100.123456','200.654321','50.000000'],unrecorded_cells_null=True,timezone_independent_calendar_days=True,no_read_effect=True)
    def matrix_period():
        f=fixture(cur,today,True);doc=document(f,today);doc['attendance']=doc['attendance'][:1];pid=save(cur,f,today,doc)['period_id'];before=b.boundary.snapshot(cur);m=entry(cur,f,today,pid=pid);assert m['page']['total']=='2' and m['period']['record_count']=='1';rows=m['page']['rows'];assert sum(r['record'] is None for r in rows)==1
        recorded=next(r for r in rows if r['record']);assert recorded['record']['mark']=='PRESENT' and recorded['record']['paid_fraction']=='1.0000' and recorded['record']['lifecycle']=='DRAFT'
        other=source.repair(cur,today);frozen=b.boundary.snapshot(cur);auth.refused(cur,lambda:entry(cur,other,today,pid=pid),'CP7_ATTENDANCE_ENTRY_PARENT');auth.refused(cur,lambda:entry(cur,f,today,pid=pid,limit=101),'CP7_ATTENDANCE_ENTRY_QUERY');assert b.boundary.snapshot(cur)==frozen
        return dict(status='PASS',existing_draft_line_and_missing_cell_distinct=True,exact_parent_period_and_dates=True,closed_page_bounds=True,no_mutation_on_invalid_query=True)
    return [('P12_ATTENDANCE_WRITE_'+key,fn) for key,fn in [('LIFECYCLE',lifecycle),('BLANKS',blanks),('DATED_RATES',dated_rates),('CORRECTION',correction_lineage),('CONSUMED',consumed),('ACCESS',access),('STALE',stale),('FIELDS_INTENT',fields_intent),('MATRIX_PAGES',matrix_pages),('MATRIX_PERIOD',matrix_period)]]

def races(tools,today):
    def compete(kind):
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);p=envelope(cur,f,today,document(f,today));version=None;pid=None;payloads=[]
            if kind=='POST_VERSION':
                pid=save(cur,f,today)['period_id'];h=period(cur,f,today,pid);version=h['row_version'];p=envelope(cur,f,today,dict(period_id=pid,reason='P12 concurrent complete posting'))
            if kind=='TWO_PERIODS':
                q=dict(p,document=dict(p['document'],period_number='P12-COMPETE-'+uuid.uuid4().hex[:10]));payloads=[(p,None),(q,None)]
            conn.commit()
        gate=threading.Barrier(2);key=uuid.uuid4()
        def send(i):
            with tools.connect() as conn,conn.cursor() as cur:
                gate.wait()
                try:
                    doc,v=payloads[i] if payloads else (p,version);r=command(cur,'POST' if kind=='POST_VERSION' else 'SAVE',doc,v,key if kind=='SAVE_REPLAY' else uuid.uuid4());conn.commit();return ('PASS',r)
                except psycopg.Error as e:conn.rollback();return ('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(send,range(2)))
        if kind=='SAVE_REPLAY':assert rows[0]==rows[1] and rows[0][0]=='PASS',rows
        else:assert sorted(x[0] for x in rows)==['PASS','REFUSED'],rows
        with tools.connect() as conn,conn.cursor() as cur:
            if kind!='POST_VERSION':assert cur.execute('select count(*) from erp.attendance_periods where contractor_id=%s',(f['contractor'],)).fetchone()[0]==1
            else:assert cur.execute("select count(*) from erp.attendance_records where contractor_id=%s and record_lifecycle='POSTED'",(f['contractor'],)).fetchone()[0]==1
        return dict(status='PASS',scenario=kind,one_native_fact_or_exact_replay=True)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);subject,role=source.procurement.custom(cur,PERMS);pid=save(cur,f,today,subject=subject)['period_id'];hdoc=period(cur,f,today,pid,subject);p=envelope(cur,f,today,dict(period_id=pid,reason='P12 current access after wait'),subject=subject);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.attendance_periods where id=%s for update',(pid,));holder_pid=h.execute('select pg_backend_pid()').fetchone()[0];ready=threading.Event();sender=[]
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    sender.append(cur.execute('select pg_backend_pid()').fetchone()[0]);ready.set()
                    try:command(cur,'POST',p,hdoc['row_version'],subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);blocked=False
                try:
                    assert ready.wait(5),'ATTENDANCE_SENDER_NOT_STARTED';deadline=time.monotonic()+8
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and pid=%s and wait_event_type='Lock' and %s=any(pg_blocking_pids(pid)))",(sender[0],holder_pid)).fetchone()[0]
                            if blocked or future.done():break
                            time.sleep(.03)
                        assert blocked,('EXPECTED_ATTENDANCE_ROW_WAIT',future.result() if future.done() else 'sender pending')
                        c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.attendance.post'",(role,))
                finally:holder.rollback()
                result=future.result(30)
        assert 'CP7_ATTENDANCE_WRITE_DENIED' in result,result
        with tools.connect() as conn,conn.cursor() as cur:assert period(cur,f,today,pid)['status']=='DRAFT' and all(r[5]=='DRAFT' for r in records(cur,pid))
        return dict(status='PASS',permission_revoked_after_observed_actual_period_wait=True,no_partial_post=True)
    return [('P12_ATTENDANCE_RACE_'+kind,lambda kind=kind:compete(kind)) for kind in ('SAVE_REPLAY','POST_VERSION','TWO_PERIODS')]+[('P12_ATTENDANCE_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        user=http.login('ADMIN','p12-attendance-command')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today,True);_,role=source.procurement.custom(cur,PERMS);cur.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(role,user.auth_user_id));facts=n.facts(cur);conn.commit()
        def read():
            r=user.rpc('erp_cp7_get_attendance_workspace_v1',dict(p_section='PERIODS',p_query=a.scope(f,today)));assert r['status']==200,r;return r['body']
        p=roster.envelope(read(),document(f,today));preview=user.rpc('erp_cp7_preview_attendance_v1',dict(p_payload=p,p_expected=None));assert preview['status']==200 and D(preview['body']['estimated_amount'])==D('125.123456'),preview
        args=dict(p_action='SAVE',p_payload=p,p_request=str(uuid.uuid4()),p_expected=None);assert http.anon_rpc('erp_cp7_save_attendance_v1',args)['status'] in(401,403)
        saved=user.rpc('erp_cp7_save_attendance_v1',args);assert saved['status']==200,saved;assert user.rpc('erp_cp7_save_attendance_v1',args)['body']==saved['body']
        w=read();h=w['page']['rows'][0];args=dict(p_action='POST',p_payload=roster.envelope(w,dict(period_id=h['id'],reason='P12 actual custom-role HTTP posting')),p_request=str(uuid.uuid4()),p_expected=h['row_version']);posted=user.rpc('erp_cp7_save_attendance_v1',args);assert posted['status']==200 and posted['body']['status']=='POSTED',posted;assert user.rpc('erp_cp7_save_attendance_v1',args)['body']==posted['body']
        with http.connect() as conn,conn.cursor() as cur:assert n.facts(cur)==facts;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));conn.commit()
        assert user.rpc('erp_cp7_save_attendance_v1',args)['status']==403
        return dict(status='PASS',real_auth_custom_role_preview_save_post=True,preview='125.123456',exact_http_replay=True,anonymous_deactivated_denied=True,no_stock_hpp_gl_effect=True,no_attendance_entry_browser_claim=True)
    return [('P12_ATTENDANCE_WRITE_HTTP',flow)]
