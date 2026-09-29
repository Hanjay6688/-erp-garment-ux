"""Independent F01 boundary probes. Administrative fixtures are isolated, not posting acceptance.

Reuse the accepted installer and fixture constructors only. WRITER_RERUN cases
retain their original assertions; AUD_F01 cases below are independently authored.
"""
from pathlib import Path
import sys,json,uuid,time,threading
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import cp7_p02_facade_probe as runner
import cp7_snapshot_cases as w
import cp6_auditor_modes as modes
import psycopg


def cost(cur,f,value):
    w.b.api.admin(cur)
    cur.execute('set local session_replication_role=replica')
    cur.execute("insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,calculation_reason) values(%s,1,'ADJUSTED',9,%s,true,'Independent F01 source fixture')",(f['lot'],value))
    cur.execute('set local session_replication_role=origin')


def cases(cur,today):
    def revoked_money():
        f=w.fixture(cur,today);subject,role=w.custom_actor(cur,True)
        r=w.create(cur,f['root'],subject=subject);archive=w.stored(cur,r['run_id'])
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'",(role,))
        before=w.read(cur,r['run_id'],subject=subject)
        cost(cur,f,'321.123456')
        after=w.read(cur,r['run_id'],subject=subject)
        assert before==after,(before,after)
        assert after['source_state']=='CURRENT' and not after['financial_captured']
        assert 'lot_cost' not in json.dumps(after)
        assert w.stored(cur,r['run_id'])==archive
        return dict(status='PASS',revoked_finance_archive_redacted=True,cost_only_change_has_no_visible_signal=True)
    def cost_reader_denied():
        f=w.fixture(cur,today);subject,_=w.custom_actor(cur)
        cur.execute('revoke execute on function erp.bd_lot_laundry_unknown_v1(uuid),erp.get_hpp_completeness(uuid) from cp7_capture')
        r=w.create(cur,f['root'],subject=subject)
        assert 'lot_cost' not in w.stored(cur,r['run_id'])['sources']
        assert 'lot_cost' not in cur.execute('select dependencies from cp7_private.analysis_runs where id=%s',(r['run_id'],)).fetchone()[0]['domains']
        w.refused(cur,lambda:w.create(cur,f['root']),'permission denied')
        return dict(status='PASS',operations_does_not_execute_finance_helpers=True,finance_source_error_refuses_capture=True)
    def decimals():
        vals=[]
        for value in ('0.000000','21474836.480001','999999999.123456'):
            f=w.fixture(cur,today);cost(cur,f,value)
            r=w.create(cur,f['root']);v=w.read(cur,r['run_id'],'lot_cost')['page']['rows'][0]['valuation']
            assert v==dict(state='KNOWN',value=value,unit='IDR'),v
            vals.append(v)
        return dict(status='PASS',exact_values=vals,zero_distinct_from_unknown=True,scope='source facts; not BD FREE policy acceptance')
    def empty_and_cursor():
        f=w.fixture(cur,today)
        cur.execute('set local session_replication_role=replica')
        cur.execute('delete from erp.sales_items where sale_id=%s',(f['sale'],))
        cur.execute('set local session_replication_role=origin')
        r=w.create(cur,f['root']);z=w.create(cur,f['root'])
        empty=w.read(cur,r['run_id'],'sales_lines')['page']
        assert empty==dict(domain='sales_lines',total=0,rows=[],next_cursor=None),empty
        n=0
        for cursor in (z['run_id']+':physical:0',r['run_id']+':sales_lines:0',r['run_id']+':physical:-1',r['run_id']+':physical:01',r['run_id']+':physical:2',r['run_id']+':physical:99999','garbage'):
            w.refused(cur,lambda:w.read(cur,r['run_id'],cursor=cursor),'CP7_CURSOR_INVALID');n+=1
        for limit in (None,0,-1,101):
            w.refused(cur,lambda:w.read(cur,r['run_id'],limit=limit),'CP7_PAGE_INVALID');n+=1
        for domain in (None,'unknown'):
            w.refused(cur,lambda:w.read(cur,r['run_id'],domain=domain),'CP7_PAGE_INVALID');n+=1
        assert w.read(cur,r['run_id'],cursor=r['run_id']+':physical:1')['page']['rows']==[]
        return dict(status='PASS',empty_domain_complete=True,invalid_parameters_refused=n,end_cursor_empty=True)
    def hundred():
        f=w.fixture(cur,today)
        cur.execute('set local session_replication_role=replica')
        cur.execute('insert into erp.sales_items(sale_id,product_id,qty_pcs,unit_price_snapshot) select %s,%s,3,1 from generate_series(1,99)',(f['sale'],f['root']))
        cur.execute('set local session_replication_role=origin')
        r=w.create(cur,f['root']);p=w.read(cur,r['run_id'],'sales_lines')['page']
        assert p['total']==len(p['rows'])==len({x['source_key'] for x in p['rows']})==100
        assert p['next_cursor'] is None and sum(int(x['qty_pcs']) for x in p['rows'])==299
        return dict(status='PASS',rows=100,pcs=299,no_unnecessary_next_page=True)
    def lot_cap():
        f=w.fixture(cur,today);subject,_=w.custom_actor(cur)
        cur.execute('set local session_replication_role=replica')
        cur.execute("insert into erp.fg_lots(id,lot_number,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,lot_origin) select gen_random_uuid(),'AUD-F01-'||gen_random_uuid(),%s,1,1,clock_timestamp()-interval '1 minute','OTHER' from generate_series(1,500)",(f['root'],))
        cur.execute('set local session_replication_role=origin')
        w.refused(cur,lambda:w.create(cur,f['root']),'CP7_SOURCE_INCOMPLETE')
        assert cur.execute('select count(*) from cp7_private.analysis_runs').fetchone()[0]==0
        r=w.create(cur,f['root'],subject=subject)
        assert 'lot_cost' not in r['counts'] and r['source_state']=='CURRENT'
        return dict(status='PASS',financial_rows=501,financial_capture_refused=True,operations_not_influenced_by_financial_limit=True)
    def stock_cap():
        f=w.fixture(cur,today)
        cur.execute('set local session_replication_role=replica')
        cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,source_id,physical_at,system_created_at)
          select gen_random_uuid(),product_id,lot_id,location_id,quality_grade,movement_type,1,0,'AUD_F01',gen_random_uuid(),physical_at,system_created_at from erp.fg_stock_movements cross join generate_series(1,500) where id=%s""",(f['movement'],))
        cur.execute('set local session_replication_role=origin')
        w.refused(cur,lambda:w.create(cur,f['root']),'CP7_SOURCE_INCOMPLETE')
        assert cur.execute('select count(*) from cp7_private.analysis_runs').fetchone()[0]==0
        return dict(status='PASS',stock_rows=501,no_partial_run=True)
    def missing_after_capture():
        f=w.fixture(cur,today);r=w.create(cur,f['root']);old=w.stored(cur,r['run_id'])
        cur.execute('set local session_replication_role=replica')
        cur.execute("update erp.products set effective_from=clock_timestamp()+interval '1 day' where id=%s",(f['root'],))
        cur.execute('set local session_replication_role=origin')
        v=w.read(cur,r['run_id']);assert v['source_state']=='SOURCE_UNAVAILABLE',v
        assert v['page']['rows']==old['sources']['physical'] and w.stored(cur,r['run_id'])==old
        w.refused(cur,lambda:w.create(cur,f['root']),'CP7_SOURCE_INCOMPLETE')
        return dict(status='PASS',unavailable_live_root_does_not_rewrite_archive=True,fresh_capture_refused=True)
    def privileges():
        business=cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in ('r','p','v') and has_table_privilege('cp7_capture',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')").fetchall()
        assert not business,business
        funcs=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('erp','public') and has_function_privilege('cp7_capture',p.oid,'EXECUTE') order by 1").fetchall()
        expected={'erp.get_my_access_v1()','erp.has_permission(text)','erp.bd_lot_laundry_unknown_v1(uuid)','erp.get_hpp_completeness(uuid)','erp_cp7_capture_snapshot_v1(uuid,uuid)','erp_cp7_read_snapshot_v1(uuid,text,text,integer)'}
        unexpected=[x[0] for x in funcs if x[0] not in expected]
        assert not unexpected,unexpected
        private=[]
        for role in ('anon','authenticated','service_role'):
            assert not cur.execute("select has_schema_privilege(%s,'cp7_private','USAGE')",(role,)).fetchone()[0]
            private+=cur.execute("select %s,p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_private' and has_function_privilege(%s,p.oid,'EXECUTE')",(role,role)).fetchall()
        assert not private,private
        return dict(status='PASS',business_write_grants=business,allowed_functions=[x[0] for x in funcs],private_helper_grants=private)
    def permission_matrix():
        f=w.fixture(cur,today);subject,role=w.custom_actor(cur,True);key=uuid.uuid4();r=w.create(cur,f['root'],key,subject)
        denied=[]
        for perm in w.PERMS:
            cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,perm))
            w.refused(cur,lambda:w.create(cur,f['root'],key,subject),'CP7_ACCESS_DENIED')
            w.refused(cur,lambda:w.read(cur,r['run_id'],subject=subject),'CP7_ACCESS_DENIED')
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,perm));denied.append(perm)
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
        w.refused(cur,lambda:w.read(cur,r['run_id'],subject=subject),'CP7_ACCESS_DENIED')
        def anonymous_claim():
            w.b.api.admin(cur);cur.execute("select set_config('request.jwt.claim.sub','',true)")
            cur.execute("select set_config('request.jwt.claims','{}',true)");cur.execute('set local session authorization authenticated')
            cur.execute('select public.erp_cp7_capture_snapshot_v1(%s,%s)',(f['root'],uuid.uuid4()))
        w.refused(cur,anonymous_claim,'CP7_ACCESS_DENIED')
        return dict(status='PASS',required_permissions_individually_enforced=denied,inactive_user_and_null_actor_denied=True)
    own=[('REVOKED_FINANCE_NO_SIDE_CHANNEL',revoked_money),('OPS_NO_FINANCE_EXECUTION',cost_reader_denied),('ZERO_AND_EXACT_DECIMALS',decimals),('EMPTY_CURSOR_MALFORMED',empty_and_cursor),('EXACT_PAGE_BOUNDARY',hundred),('LOT_COST_CAP_ISOLATION',lot_cap),('STOCK_CAP',stock_cap),('ARCHIVE_SOURCE_UNAVAILABLE',missing_after_capture),('FULL_EFFECTIVE_ACL',privileges),('EACH_PERMISSION_REPLAY',permission_matrix)]
    return [('AUD_F01_'+k,fn) for k,fn in own]+[('WRITER_RERUN_'+k,fn) for k,fn in w.cases(cur,today)]


def races(tools,today):
    def wait_change(finance=False,existing=False):
        with tools.connect() as conn,conn.cursor() as cur:
            f=w.fixture(cur,today);subject,role=w.custom_actor(cur,True);key=str(uuid.uuid4())
            if existing:w.create(cur,f['root'],key,subject)
            conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7_CAPTURE:'||%s||':'||%s,0))",(subject,key))
            def waiting():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:w.create(cur,f['root'],key,subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(waiting)
                try:
                    with tools.connect(autocommit=True) as conn,conn.cursor() as cur:
                        deadline=time.monotonic()+10;blocked=False
                        while time.monotonic()<deadline:
                            cur.execute('select pg_stat_clear_snapshot()')
                            blocked=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event='advisory' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                        assert blocked,'REAL_REQUEST_LOCK_NOT_OBSERVED'
                    with tools.connect() as conn,conn.cursor() as cur:
                        perm='finance.hpp.view' if finance else 'warehouse.stock.view'
                        cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,perm));conn.commit()
                finally:holder.rollback()
                result=future.result(timeout=20)
        assert 'CP7_ACCESS_CHANGED' in result or 'CP7_ACCESS_DENIED' in result,result
        with tools.connect() as conn,conn.cursor() as cur:
            count=cur.execute('select count(*) from cp7_private.analysis_runs').fetchone()[0]
            assert count==(1 if existing else 0),count
        return dict(status='PASS',existing_replay=existing,finance_only_revocation=finance,result=result,persisted_runs=count)
    def isolation():
        with tools.connect() as conn,conn.cursor() as cur:f=w.fixture(cur,today);conn.commit()
        results=[]
        for level in ('repeatable read','serializable'):
            with tools.connect() as conn,conn.cursor() as cur:
                cur.execute('set transaction isolation level '+level)
                try:w.create(cur,f['root']);raise AssertionError('STALE_ISOLATION_ACCEPTED')
                except psycopg.Error as e:
                    assert 'CP7_FRESH_ACCESS_TRANSACTION_REQUIRED' in str(e);results.append(level);conn.rollback()
        return dict(status='PASS',refused_isolation_levels=results)
    return [('AUD_F01_FINANCE_REVOKED_WHILE_WAITING',lambda:wait_change(True)),('AUD_F01_EXISTING_REPLAY_REVOKED_WHILE_WAITING',lambda:wait_change(existing=True)),('AUD_F01_STALE_ISOLATION',isolation)]+[('WRITER_RERUN_'+k,fn) for k,fn in w.races(tools,today)]


def http_cases(http,today):
    def private_api():
        owner=http.login('OWNER','f01-private')
        results=[]
        for token in (None,owner._token):
            headers={'apikey':http._anon,'Authorization':'Bearer '+(token or http._anon)}
            for path,method,body,profile in (('/analysis_runs?select=*','GET',None,None),('/analysis_runs?select=*','GET',None,'cp7_private'),('/rpc/access_now','POST',{},None),('/rpc/capture_sources','POST',dict(p_root=str(uuid.uuid4()),p_financial=True),'cp7_private')):
                h=dict(headers)
                if profile:h['Accept-Profile' if method=='GET' else 'Content-Profile']=profile
                r=modes._call(modes.REST_URL+path,body,h,method)
                assert r['status'] in (400,401,403,404,406),dict(path=path,status=r['status'],body=r['body'])
                results.append(dict(actor='authenticated' if token else 'anonymous',path=path,profile=profile,status=r['status']))
        return dict(status='PASS',direct_private_rest_attempts=results)
    def current_permissions():
        actor=http.login('ADMIN','f01-permission')
        with http.connect() as conn,conn.cursor() as cur:
            f=w.fixture(cur,today);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
            for perm in w.PERMS:cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,perm))
            conn.commit()
        args=dict(p_root=f['root'],p_request=str(uuid.uuid4()));r=actor.rpc('erp_cp7_capture_snapshot_v1',args)
        assert r['status']==200,r;run=r['body']['run_id'];statuses=[]
        for perm in w.PERMS:
            with http.connect() as conn,conn.cursor() as cur:
                cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,perm));conn.commit()
            a=actor.rpc('erp_cp7_capture_snapshot_v1',args);b=actor.rpc('erp_cp7_read_snapshot_v1',dict(p_run=run))
            assert a['status']==b['status']==403,(perm,a,b)
            statuses.append(dict(permission=perm,replay=a['status'],page=b['status']))
            with http.connect() as conn,conn.cursor() as cur:
                cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,perm));conn.commit()
        assert actor.rpc('erp_cp7_capture_snapshot_v1',args)['body']['run_id']==run
        return dict(status='PASS',same_real_auth_token=True,revocations=statuses,restored_permission_replay_same_run=True)
    return [('AUD_F01_DIRECT_PRIVATE_REST',private_api),('AUD_F01_HTTP_EACH_PERMISSION_REVOKED',current_permissions)]+[('WRITER_RERUN_'+k,fn) for k,fn in w.http_cases(http,today)]


if __name__=='__main__':
    runner.cases=sys.modules[__name__]
    runner.OUT=ROOT/'cp6-proof/t3/CP7_F01_INDEPENDENT.json'
    runner.package._writer_runtime=lambda browser_mode=False:runner.run()
    runner.package.run('install')
