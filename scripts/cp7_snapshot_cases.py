"""P02 predeclared oracles: isolated native, concurrent, and real Auth/HTTP cases."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json,time,uuid,threading
import psycopg
import cp6_bf_probe as bf

b,base=bf.b,bf.b.chain.base
PERMS=('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view')

def actor(cur,subject=None,role='authenticated'):
    b.api.admin(cur)
    cur.execute("select set_config('request.jwt.claim.sub','',true)")
    cur.execute("select set_config('request.jwt.claims',%s,true)",
        (json.dumps(dict(sub=subject or base.OPERATOR_AUTH,role=role)),))
    cur.execute('set local session authorization authenticated')

def create(cur,root,key=None,subject=None,role='authenticated'):
    actor(cur,subject,role)
    value=cur.execute('select public.erp_cp7_capture_snapshot_v1(%s,%s)',(root,key or uuid.uuid4())).fetchone()[0]
    b.api.admin(cur);return value

def read(cur,run,domain='physical',cursor=None,limit=100,subject=None):
    actor(cur,subject)
    value=cur.execute('select public.erp_cp7_read_snapshot_v1(%s,%s,%s,%s)',(run,domain,cursor,limit)).fetchone()[0]
    b.api.admin(cur);return value

def refused(cur,op,code):
    b.api.admin(cur);cur.execute('savepoint p02_refusal')
    try:op()
    except psycopg.Error as e:
        ok=code in str(e); detail=str(e).splitlines()[0]
        cur.execute('rollback to savepoint p02_refusal');b.api.admin(cur)
        assert ok,(code,detail)
        cur.execute('release savepoint p02_refusal');return detail
    cur.execute('rollback to savepoint p02_refusal');b.api.admin(cur)
    raise AssertionError('EXPECTED_REFUSAL:'+code)

def custom_actor(cur,finance=False):
    b.api.admin(cur);role,subject=uuid.uuid4(),str(uuid.uuid4())
    cur.execute("insert into erp.app_roles(id,role_code,role_name,is_system,is_protected,is_active) values(%s,%s,'CP7 fixture',false,false,true)",
                (role,'P02_'+role.hex[:12]))
    for key in PERMS+(('finance.hpp.view',) if finance else ()):
        cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) values(%s,%s,'P02 actor','STAFF',%s,true)",
                (uuid.uuid4(),subject,role))
    return subject,role

def fixture(cur,today,cutting=False):
    b.api.admin(cur)
    (root,size),=bf.products(cur,('31',),tag='P02-'+uuid.uuid4().hex[:8])
    groups=[]
    if cutting:
        for qty in (6,7):
            f=b.two_size_fixture(cur,b.case_day(today),'P02-'+str(qty),size_quantities=[(size,qty),(base.SIZE,10-qty)])
            groups.append(f['group'])
    b.api.admin(cur);now=cur.execute('select clock_timestamp()').fetchone()[0]
    customer=base.create_customer(cur,'P02-'+uuid.uuid4().hex[:8])
    lot,sale,movement=map(lambda _:str(uuid.uuid4()),range(3))
    # Explicit administrative source fixture, not normal posting acceptance.
    cur.execute('set local session_replication_role=replica')
    cur.execute("insert into erp.fg_lots(id,lot_number,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,lot_origin) values(%s,%s,%s,9,9,%s,'OTHER')",
        (lot,'P02-'+lot,root,now-timedelta(minutes=4)))
    cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,
     qty_signed,unit_hpp_snapshot,source_type,source_id,physical_at,system_created_at)
     values(%s,%s,%s,%s,'GRADE_A','ADJUSTMENT',9,0,'P02_FIXTURE',%s,%s,%s)""",
        (movement,root,lot,base.LOCATION,uuid.uuid4(),now-timedelta(minutes=3),now-timedelta(minutes=2)))
    cur.execute("insert into erp.sales_headers(id,sale_number,customer_id,sale_date,status,source_location_id,created_at) values(%s,%s,%s,%s,'DRAFT',%s,%s)",
        (sale,'P02-'+sale,customer,now-timedelta(minutes=2),base.LOCATION,now-timedelta(minutes=2)))
    cur.execute('insert into erp.sales_items(sale_id,product_id,qty_pcs,unit_price_snapshot) values(%s,%s,2,10000)',(sale,root))
    cur.execute('set local session_replication_role=origin')
    return dict(root=root,size=size,lot=lot,sale=sale,movement=movement,groups=groups)

def stored(cur,run):
    b.api.admin(cur)
    return cur.execute('select payload from cp7_private.analysis_runs where id=%s',(run,)).fetchone()[0]

def pair(payload):
    return (int(payload['sources']['stock_movements'][0]['qty_signed_pcs']),
            int(payload['sources']['sales_lines'][0]['qty_pcs']))

def mutate(cur,f,qty):
    b.api.admin(cur);cur.execute('set local session_replication_role=replica')
    cur.execute('update erp.fg_stock_movements set qty_signed=%s where id=%s',(qty+7,f['movement']))
    cur.execute('update erp.sales_items set qty_pcs=%s where sale_id=%s',(qty,f['sale']))
    cur.execute('set local session_replication_role=origin')

def cases(cur,today):
    def snapshot():
        f=fixture(cur,today,True);before=b.boundary.snapshot(cur)
        r=create(cur,f['root']);p=stored(cur,r['run_id'])
        assert pair(p)==(9,2)
        assert sorted(int(x['cut_qty_pcs']) for x in p['sources']['cutting_candidates'] if x['cutting_group_id'] in f['groups'])==[6,7]
        assert p['sources']['lot_cost'][0]['valuation']==dict(state='UNKNOWN',reason='PENDING_COST_OR_NO_HPP')
        assert b.boundary.snapshot(cur)==before
        assert cur.execute('select count(*) from jsonb_object_keys((select dependencies->\'domains\' from cp7_private.analysis_runs where id=%s))',(r['run_id'],)).fetchone()[0]==6
        return dict(status='PASS',pair=[9,2],cutting=[6,7],cost='UNKNOWN',business_boundary_unchanged=True)
    def replay():
        f=fixture(cur,today);key=uuid.uuid4();r=create(cur,f['root'],key);p=stored(cur,r['run_id'])
        assert create(cur,f['root'],key)['run_id']==r['run_id']
        refused(cur,lambda:create(cur,uuid.uuid4(),key),'CP7_REQUEST_REUSED')
        refused(cur,lambda:create(cur,uuid.uuid4()),'CP7_SOURCE_INCOMPLETE')
        mutate(cur,f,5)
        replay=create(cur,f['root'],key)
        assert replay['source_state']=='ARCHIVED_STALE' and stored(cur,r['run_id'])==p
        assert cur.execute('select count(*) from cp7_private.analysis_runs').fetchone()[0]==1
        return dict(status='PASS',replay_stable=True,stale_after_atomic_correction=True)
    def projection():
        f=fixture(cur,today);subject,role=custom_actor(cur)
        r=create(cur,f['root'],subject=subject);p=stored(cur,r['run_id'])
        assert 'lot_cost' not in p['sources'] and 'lot_cost' not in r['counts']
        refused(cur,lambda:read(cur,r['run_id'],'lot_cost',subject=subject),'CP7_FINANCIAL_ACCESS_DENIED')
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.hpp.view')",(role,))
        refused(cur,lambda:read(cur,r['run_id'],'lot_cost',subject=subject),'CP7_FINANCIAL_NOT_CAPTURED')
        r2=create(cur,f['root'],subject=subject)
        assert read(cur,r2['run_id'],'lot_cost',subject=subject)['page']['rows'][0]['valuation']['state']=='UNKNOWN'
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'",(role,))
        redacted=read(cur,r2['run_id'],subject=subject)
        assert 'lot_cost' not in redacted['counts'] and not redacted['financial_captured']
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,))
        refused(cur,lambda:read(cur,r2['run_id'],subject=subject),'CP7_ACCESS_DENIED')
        return dict(status='PASS',server_redaction=True,grant_requires_new_capture=True,revoke_denied=True)
    def auth():
        f=fixture(cur,today)
        for subject,role in ((str(uuid.uuid4()),'authenticated'),(base.OPERATOR_AUTH,'service_role')):
            refused(cur,lambda:create(cur,f['root'],subject=subject,role=role),'CP7_ACCESS_DENIED')
        subject,role=custom_actor(cur);r=create(cur,f['root'])
        refused(cur,lambda:read(cur,r['run_id'],subject=subject),'CP7_RUN_UNAVAILABLE')
        own=create(cur,f['root'],subject=subject)
        cur.execute('update erp.app_roles set is_active=false where id=%s',(role,))
        refused(cur,lambda:read(cur,own['run_id'],subject=subject),'CP7_ACCESS_DENIED')
        return dict(status='PASS',unmapped_denied=True,service_role_denied=True,other_actor_denied=True,inactive_role_denied=True)
    def pagination():
        f=fixture(cur,today);b.api.admin(cur)
        cur.execute('set local session_replication_role=replica')
        cur.execute('insert into erp.sales_items(sale_id,product_id,qty_pcs,unit_price_snapshot) values(%s,%s,3,7)',(f['sale'],f['root']))
        cur.execute('set local session_replication_role=origin')
        r=create(cur,f['root']);a=read(cur,r['run_id'],'sales_lines',limit=1)
        c=a['page']['next_cursor'];assert c and a['page']['total']==2
        mutate(cur,f,5)
        z=read(cur,r['run_id'],'sales_lines',c,1)
        assert a['page']['rows'][0]['source_key']!=z['page']['rows'][0]['source_key']
        assert sorted([a['page']['rows'][0]['qty_pcs'],z['page']['rows'][0]['qty_pcs']])==['2','3']
        assert z['page']['next_cursor'] is None and z['source_state']=='ARCHIVED_STALE'
        refused(cur,lambda:read(cur,r['run_id'],'stock_movements',c),'CP7_CURSOR_INVALID')
        refused(cur,lambda:read(cur,r['run_id'],'sales_lines',limit=101),'CP7_PAGE_INVALID')
        return dict(status='PASS',immutable_page_values=[2,3],cursor_bound_to_run_domain=True)
    def incomplete():
        f=fixture(cur,today);b.api.admin(cur);cur.execute('set local session_replication_role=replica')
        cur.execute('insert into erp.sales_items(sale_id,product_id,qty_pcs,unit_price_snapshot) select %s,%s,1,1 from generate_series(1,500)',(f['sale'],f['root']))
        cur.execute('set local session_replication_role=origin')
        refused(cur,lambda:create(cur,f['root']),'CP7_SOURCE_INCOMPLETE')
        assert cur.execute('select count(*) from cp7_private.analysis_runs').fetchone()[0]==0
        return dict(status='PASS',source_rows=501,partial_run_rows=0)
    def immutable():
        f=fixture(cur,today);r=create(cur,f['root'])
        refused(cur,lambda:cur.execute('update cp7_private.analysis_runs set root_id=%s where id=%s',(f['root'],r['run_id'])),'CP7_RUN_IMMUTABLE')
        refused(cur,lambda:cur.execute('delete from cp7_private.analysis_runs where id=%s',(r['run_id'],)),'CP7_RUN_IMMUTABLE')
        assert not cur.execute("select has_function_privilege('cp7_capture','public.erp_save_sku_action_v1(text,jsonb,uuid)','EXECUTE')").fetchone()[0]
        assert not cur.execute("select has_table_privilege('cp7_capture','erp.fg_stock_movements','INSERT,UPDATE,DELETE')").fetchone()[0]
        assert not cur.execute("select has_schema_privilege('authenticated','cp7_private','USAGE')").fetchone()[0]
        return dict(status='PASS',immutable=True,compute_mutator_denied=True,private_data_api_denied=True)
    return [('P02_CAPTURE_FACTS_BOUNDARY',snapshot),('P02_REPLAY_STALE_REQUEST_CONFLICT',replay),
        ('P02_SERVER_PROJECTION_REVOKE',projection),('P02_ACTOR_SCOPE',auth),
        ('P02_IMMUTABLE_CURSOR',pagination),('P02_INCOMPLETE_REFUSED',incomplete),('P02_COMPUTE_PRIVILEGES_IMMUTABLE',immutable)]

def races(tools,today):
    def coherent():
        with tools.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);conn.commit()
        active=threading.Event();done=threading.Event();count=[0]
        def writer():
            with tools.connect() as conn,conn.cursor() as cur:
                active.set()
                for i in range(30):
                    mutate(cur,f,5 if i%2==0 else 2);conn.commit();count[0]+=1;time.sleep(.02)
            done.set()
        values=[];overlap=0
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(writer);assert active.wait(5)
            with tools.connect() as conn,conn.cursor() as cur:
                for _ in range(12):
                    r=create(cur,f['root']);values.append(pair(stored(cur,r['run_id'])));conn.commit()
                    if not done.is_set():overlap+=1
            future.result(timeout=20)
        assert all(x in ((9,2),(12,5)) for x in values) and overlap>0 and count[0]==30,(values,overlap,count)
        return dict(status='PASS',captures=len(values),committed_updates=count[0],captures_while_writer_active=overlap,observed_pairs=sorted(set(values)))
    def revoked():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);subject,role=custom_actor(cur);conn.commit()
        key=str(uuid.uuid4())
        with tools.connect() as holder,holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7_CAPTURE:'||%s||':'||%s,0))",(subject,key))
            def waiting():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:create(cur,f['root'],key,subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(waiting);deadline=time.monotonic()+10;blocked=False
                with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                    while time.monotonic()<deadline:
                        c.execute('select pg_stat_clear_snapshot()')
                        blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event='advisory' and pid<>pg_backend_pid())").fetchone()[0]
                        if blocked:break
                        time.sleep(.03)
                assert blocked,'CAPTURE_NOT_WAITING_ON_REAL_REQUEST_LOCK'
                with tools.connect() as revoke,revoke.cursor() as c:
                    c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,));revoke.commit()
                holder.commit();error=future.result(timeout=15)
        assert 'CP7_ACCESS_DENIED' in error or 'CP7_ACCESS_CHANGED' in error,error
        with tools.connect() as conn,conn.cursor() as cur:
            assert cur.execute('select count(*) from cp7_private.analysis_runs').fetchone()[0]==0
        return dict(status='PASS',revoked_while_capture_waited=True,refusal=error,partial_run_rows=0)
    def duplicate():
        with tools.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);conn.commit()
        key=uuid.uuid4();start=threading.Barrier(2)
        def attempt():
            with tools.connect() as conn,conn.cursor() as cur:
                start.wait(timeout=5);r=create(cur,f['root'],key);conn.commit();return r['run_id']
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(attempt);z=pool.submit(attempt);ids=[a.result(timeout=20),z.result(timeout=20)]
        assert ids[0]==ids[1],ids
        with tools.connect() as conn,conn.cursor() as cur:assert cur.execute('select count(*) from cp7_private.analysis_runs').fetchone()[0]==1
        return dict(status='PASS',same_run=True,persisted_runs=1)
    return [('P02_CONCURRENT_COHERENCE',coherent),('P02_REVOCATION_DURING_CAPTURE',revoked),('P02_CONCURRENT_REQUEST_REPLAY',duplicate)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p02-owner');other=http.login('OWNER','p02-other')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);before=b.boundary.snapshot(cur);conn.commit()
        key=str(uuid.uuid4());args=dict(p_root=f['root'],p_request=key)
        created=owner.rpc('erp_cp7_capture_snapshot_v1',args)
        assert created['status']==200,created
        run=created['body']['run_id']
        page=owner.rpc('erp_cp7_read_snapshot_v1',dict(p_run=run,p_domain='lot_cost'))
        assert page['status']==200 and page['body']['page']['rows'][0]['valuation']['state']=='UNKNOWN',page
        assert other.rpc('erp_cp7_read_snapshot_v1',dict(p_run=run))['status']==403
        assert http.anon_rpc('erp_cp7_read_snapshot_v1',dict(p_run=run))['status'] in (401,403,404)
        assert owner.rpc('erp_cp7_capture_snapshot_v1',args)['body']['run_id']==run
        with http.connect() as conn,conn.cursor() as cur:
            assert b.boundary.snapshot(cur)==before
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        denied=owner.rpc('erp_cp7_capture_snapshot_v1',args)
        assert denied['status']==403 and 'CP7_ACCESS_DENIED' in json.dumps(denied['body']),denied
        return dict(status='PASS',real_auth=True,owner_capture_cost=True,other_actor_denied=True,anonymous_denied=True,same_token_revoked=True,business_boundary_unchanged=True)
    def operations():
        user=http.login('ADMIN','p02-operations')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today)
            role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
            for key in PERMS:cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
            conn.commit()
        r=user.rpc('erp_cp7_capture_snapshot_v1',dict(p_root=f['root'],p_request=str(uuid.uuid4())))
        assert r['status']==200 and 'lot_cost' not in r['body']['counts'],r
        blocked=user.rpc('erp_cp7_read_snapshot_v1',dict(p_run=r['body']['run_id'],p_domain='lot_cost'))
        assert blocked['status']==403,blocked
        return dict(status='PASS',real_auth=True,financial_domain_absent=True,financial_read_denied=True)
    return [('P02_HTTP_REAL_AUTH_REPLAY_REVOKE',flow),('P02_HTTP_OPERATIONS_REDACTION',operations)]
