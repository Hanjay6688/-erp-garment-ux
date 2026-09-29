"""P12 date-based native attendance reader oracles; source writers are controls."""
from datetime import timedelta
import json,uuid
import cp7_settlement_cases as s
auth,b,n,source=s.auth,s.b,s.n,s.source
PERM='finance.attendance.view'

def read(cur,section='CONTRACTORS',subject=None,**query):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_attendance_workspace_v1(%s,%s)',(section,json.dumps(query))).fetchone()[0];b.api.admin(cur);return r
def scope(f,start,end=None):return dict(contractor_id=f['contractor'],date_from=str(start),date_to=str(end or start))
def worker(cur,f,start,rate='100.123456',name='P12 dated worker'):
    payload=dict(contractor_id=f['contractor'],worker_name=name,job_description='Jahit',pay_scheme='DAILY',initial_daily_rate=rate,rate_effective_from=str(start),joined_at=str(start),is_active=True,reason='P12 ordinary roster source')
    r=s.native(cur,'select public.erp_save_worker_roster_v1(%s::jsonb,%s,null)',(json.dumps(payload),uuid.uuid4()))
    return str(s.bc.awp.find(r,'worker_id')),payload
def version(cur,wid):return cur.execute('select row_version from erp.contractor_workers where id=%s',(wid,)).fetchone()[0]
def rate(cur,wid,value,day):return s.native(cur,'select public.erp_set_worker_daily_rate_v1(%s,%s,%s,%s,%s,%s)',(wid,value,day,'P12 ordinary dated rate',uuid.uuid4(),version(cur,wid)))
def stop(cur,wid,payload,day):return s.native(cur,'select public.erp_save_worker_roster_v1(%s::jsonb,%s,%s)',(json.dumps(dict(payload,worker_id=wid,is_active=False,left_at=str(day),reason='P12 ordinary historical stop')),uuid.uuid4(),version(cur,wid)))

def cases(cur,today):
    def history():
        f=source.repair(cur,today);start=today-timedelta(days=6);wid,p=worker(cur,f,start);rate(cur,wid,'200.654321',today-timedelta(days=2));stop(cur,wid,p,today-timedelta(days=1));before=b.boundary.snapshot(cur)
        old=read(cur,'WORKERS',**scope(f,start,start+timedelta(days=1)));w=old['page']['rows'][0]
        assert old['page']['total']=='1' and not w['active_now'] and w['employed_at_date'] and w['daily_rate_at_date']=='100.123456' and w['rate_at']==str(start)
        rates=read(cur,'RATES',worker_id=wid,**scope(f,start,start+timedelta(days=1)))
        assert rates['source_token']==old['source_token'] and rates['worker']==w and len(rates['page']['rows'])==1 and rates['page']['rows'][0]['daily_rate']=='100.123456'
        newer=read(cur,'RATES',worker_id=wid,**scope(f,today-timedelta(days=2),today));assert newer['page']['rows'][0]['daily_rate']=='200.654321'
        assert read(cur,'WORKERS',**scope(f,today))['page']['total']=='0'
        episodes=read(cur,'EMPLOYMENT',worker_id=wid,**scope(f,start,today));assert episodes['page']['rows'][0]['date_from']==str(start) and episodes['page']['rows'][0]['date_to']==str(today-timedelta(days=1))
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',ordinary_dated_rate_and_stop_controls=True,inactive_now_visible_in_own_history=True,historical_rate='100.123456',later_rate='200.654321',later_rate_excluded_from_earlier_window=True,no_read_effect=True)
    def pages():
        f=source.repair(cur,today);ids=[worker(cur,f,today,name='P12 worker '+str(i))[0] for i in range(3)];before=b.boundary.snapshot(cur)
        pages=[read(cur,'WORKERS',**scope(f,today),limit=1,offset=i) for i in range(3)]
        assert len({r['source_token'] for r in pages})==1 and all(r['page']['total']=='3' for r in pages) and [r['page']['next_offset'] for r in pages]==[1,2,None]
        assert {r['page']['rows'][0]['id'] for r in pages}==set(ids) and all(isinstance(r['page']['rows'][0]['row_version'],str) for r in pages)
        d=read(cur,'WORKERS',**scope(f,today-timedelta(days=1),today))['page']['rows'][0];assert d['daily_rate_at_date'] is None and not d['employed_at_date']
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',complete_native_worker_paging=True,exact_version_and_six_decimal_rate_strings=True,before_employment_rate_is_null_not_zero=True,no_read_effect=True)
    def periods():
        f=s.review.fixture(cur,today);s.attendance(cur,f,today);w=read(cur,'PERIODS',**scope(f,today));p=w['page']['rows'][0]
        assert p['status']=='POSTED' and p['record_count']=='1' and p['consuming_payroll_count']=='0'
        rec=read(cur,'RECORDS',period_id=p['id'],**scope(f,today));assert rec['period']==p and rec['source_token']==w['source_token'];r=rec['page']['rows'][0]
        assert r['mark']=='PRESENT' and r['paid_fraction']=='1.0000' and r['lifecycle']=='POSTED' and r['period_id']==p['id']
        s.act(cur,'PREPARE',s.doc(cur,f['payroll']));prepared=read(cur,'RECORDS',period_id=p['id'],**scope(f,today));assert prepared['period']['consuming_payroll_count']=='1' and prepared['source_token']!=rec['source_token']
        s.act(cur,'CANCEL',s.doc(cur,f['payroll']));released=read(cur,'RECORDS',period_id=p['id'],**scope(f,today));assert released['period']['consuming_payroll_count']=='0' and released['page']['rows']==rec['page']['rows']
        return dict(status='PASS',ordinary_posted_attendance=True,record_lifecycle_and_parent_exact=True,active_payroll_consumption_visible_then_released=True,read_does_not_post_or_recalculate=True)
    def token_timezone():
        f=source.repair(cur,today);wid,p=worker(cur,f,today-timedelta(days=3));q=scope(f,today-timedelta(days=3),today);zone=cur.execute('show timezone').fetchone()[0];reads=[]
        for tz in ('Asia/Jakarta','UTC','America/Los_Angeles'):
            cur.execute("select set_config('TimeZone',%s,true)",(tz,));reads.append(read(cur,'WORKERS',**q))
        cur.execute("select set_config('TimeZone',%s,true)",(zone,));assert reads[0]==reads[1]==reads[2]
        rate(cur,wid,'150.987654',today);after=read(cur,'WORKERS',**q);assert after['source_token']!=reads[0]['source_token'] and after['page']['rows'][0]['daily_rate_at_date']=='100.123456'
        return dict(status='PASS',identical_dated_data_and_token_in_three_timezones=True,source_change_invalidates_token_without_rewriting_historical_rate=True)
    def access():
        f=source.repair(cur,today);worker(cur,f,today);subject,role=source.procurement.custom(cur,(PERM,));before=n.facts(cur)
        assert read(cur,'WORKERS',subject=subject,**scope(f,today))['page']['total']=='1'
        cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));auth.refused(cur,lambda:read(cur,'WORKERS',subject=subject,**scope(f,today)),'CP7_ATTENDANCE_ACCESS_DENIED')
        ops,_=source.procurement.custom(cur,('production.fg_handoff.view',));auth.refused(cur,lambda:read(cur,subject=ops),'CP7_ATTENDANCE_ACCESS_DENIED')
        payroll,_=source.procurement.custom(cur,('finance.payroll.view',));auth.refused(cur,lambda:read(cur,subject=payroll),'CP7_ATTENDANCE_ACCESS_DENIED')
        assert n.facts(cur)==before
        return dict(status='PASS',custom_attendance_view_only=True,payroll_view_alone_not_attendance_permission=True,ops_denied_current_revoke=True,no_financial_effect=True)
    def validation():
        f=source.repair(cur,today);other=source.repair(cur,today);wid,_=worker(cur,other,today);before=b.boundary.snapshot(cur)
        for section,q,code in [('UNKNOWN',{},'CP7_ATTENDANCE_QUERY'),('CONTRACTORS',dict(limit=101),'CP7_ATTENDANCE_QUERY'),('WORKERS',dict(scope(f,today),extra='forged'),'CP7_ATTENDANCE_QUERY'),('WORKERS',dict(contractor_id=f['contractor']),'CP7_ATTENDANCE_QUERY'),('RATES',dict(scope(f,today),worker_id=wid),'CP7_ATTENDANCE_WORKER_PARENT'),('RECORDS',dict(scope(f,today),period_id=str(uuid.uuid4())),'CP7_ATTENDANCE_PERIOD_PARENT')]:
            auth.refused(cur,lambda section=section,q=q:read(cur,section,**q),code)
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',closed_queries_bounds_required_dates=True,wrong_worker_parent_and_missing_period_refused=True,no_partial_data_or_effect=True)
    return [('P12_ATTENDANCE_READ_'+k,fn) for k,fn in [('HISTORY',history),('PAGES',pages),('PERIODS',periods),('TIMEZONE_TOKEN',token_timezone),('ACCESS',access),('VALIDATION',validation)]]

def http_cases(http,today):
    def flow():
        user=http.login('ADMIN','p12-attendance-read')
        with http.connect() as conn,conn.cursor() as cur:
            f=source.repair(cur,today);worker(cur,f,today);_,role=source.procurement.custom(cur,(PERM,));cur.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(role,user.auth_user_id));before=n.facts(cur);conn.commit()
        args=dict(p_section='WORKERS',p_query=scope(f,today));r=user.rpc('erp_cp7_get_attendance_workspace_v1',args)
        assert r['status']==200 and r['body']['page']['rows'][0]['daily_rate_at_date']=='100.123456',r
        assert http.anon_rpc('erp_cp7_get_attendance_workspace_v1',args)['status'] in (401,403)
        with http.connect() as conn,conn.cursor() as cur:
            assert n.facts(cur)==before;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));conn.commit()
        assert user.rpc('erp_cp7_get_attendance_workspace_v1',args)['status']==403
        return dict(status='PASS',real_auth_custom_role=True,native_rate='100.123456',anonymous_and_deactivated_denied=True,no_source_writer_or_browser_claim=True)
    return [('P12_ATTENDANCE_READ_HTTP',flow)]
