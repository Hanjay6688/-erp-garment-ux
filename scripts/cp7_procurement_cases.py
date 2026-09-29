"""P09 receipts: real accepted posting writers behind the new permission boundary.

Master rows are disposable setup. Quantities, stock and journals under test are
created by public P09 commands, never administrative stock inserts.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import copy,json,threading,time,uuid
import psycopg
import cp7_snapshot_cases as auth
import cp6_aa_invoice_partial_audit as aa
import cp6_bc_probe as bc
b=auth.b

def fixture(cur,today,qty='10',price='10',final=False):
    b.api.admin(cur);aa.zone(cur,'Asia/Jakarta')
    material=aa.prior.clone_material(cur,'cp7-p09');day=today-timedelta(days=3)
    aa.prior.set_open_period(cur,day-timedelta(days=1));loc=str(uuid.uuid4());tag='P09-'+uuid.uuid4().hex[:12]
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,%s,'RAW_MATERIAL_WAREHOUSE',true)",(loc,tag,tag))
    payload=dict(purchase_number=tag,supplier_id=str(aa.prior.BASE_SUPPLIER),location_id=loc,
      physical_at=aa.at(day,10).isoformat(),change_reason='P09 declared receipt',
      lines=[dict(material_id=str(material),qty=qty,unit_price=price,price_state='FINAL' if final else 'ESTIMATED',
       price_source='SUPPLIER_INVOICE' if final else 'MANUAL_ESTIMATE',rolls=[dict(roll_number=tag+'-R',qty=qty)])])
    return dict(material=str(material),location=loc,payload=payload,day=day,tag=tag)

def command(cur,action,payload,key=None,version=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_save_procurement_v1(%s,%s::jsonb,%s,%s)',
      (action,json.dumps(payload,default=str),key or uuid.uuid4(),version)).fetchone()[0]
    b.api.admin(cur);return r

def workspace(cur,query=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_procurement_v1(%s::jsonb)',(json.dumps(query or {}),)).fetchone()[0]
    b.api.admin(cur);return r

def options(cur,kind,q='',offset=0,limit=100,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_procurement_options_v1(%s,%s,%s,%s)',(kind,q,offset,limit)).fetchone()[0]
    b.api.admin(cur);return r

def post(cur,draft,key=None,subject=None):
    return command(cur,'POST',dict(purchase_id=draft['purchase_id'],change_reason='P09 post exact receipt'),key,draft['row_version'],subject)

def qty(cur,f):
    return cur.execute('select coalesce(sum(qty_signed),0),count(*) from erp.material_stock_movements where material_id=%s',(f['material'],)).fetchone()

def custom(cur,permissions):
    subject,role=auth.custom_actor(cur)
    cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
    for key in permissions:cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
    return subject,role

OPS=('warehouse.procurement.view','warehouse.procurement.create','warehouse.procurement.post')

def smoke(cur,today):
    def first():
        f=fixture(cur,today);d=command(cur,'SAVE_DRAFT',f['payload']);assert qty(cur,f)==(0,0)
        p=post(cur,d);assert p['status']=='POSTED' and qty(cur,f)==(10,1)
        w=workspace(cur,dict(purchase_id=p['purchase_id']));assert w['detail']['stock_effect']=='POSTED_RECEIPT'
        return dict(status='PASS',public_draft_post_read=True,qty=10,movements=1)
    return [('P09_RECEIPT_SMOKE',first)]

def cases(cur,today):
    def estimated():
        f=fixture(cur,today);d=command(cur,'SAVE_DRAFT',f['payload'])
        w=workspace(cur,dict(purchase_id=d['purchase_id']));assert w['detail']['stock_effect']=='NOT_POSTED' and qty(cur,f)==(0,0)
        assert w['detail']['items'][0]['rolls'][0]['receipt_qty']=='10.000000'
        p=post(cur,d);assert qty(cur,f)==(10,1)
        ap,grni=cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)',(p['purchase_id'],p['purchase_id'])).fetchone()
        assert (ap,grni)==(0,100),(ap,grni)
        w=workspace(cur,dict(purchase_id=p['purchase_id']));assert w['detail']['row_version']==p['row_version']
        assert w['detail']['quantity_basis']=='RECEIPT_DOCUMENT_NOT_CURRENT_ON_HAND'
        return dict(status='PASS',draft_stock=0,posted_qty=10,final_ap=0,estimated_grni=100,reloaded_version=True)
    def final_exact():
        f=fixture(cur,today,qty='1.123456',price='3.000001',final=True)
        d=command(cur,'SAVE_DRAFT',f['payload']);p=post(cur,d);assert qty(cur,f)==(Decimal('1.123456'),1)
        w=workspace(cur,dict(purchase_id=p['purchase_id']));i=w['detail']['items'][0]
        assert i['qty']=='1.123456' and i['finance']['unit_price']=='3.000001'
        assert i['finance']['line_total']=='3.370369',i
        ap,grni=cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)',(p['purchase_id'],p['purchase_id'])).fetchone()
        assert (round(ap,2),grni)==(Decimal('3.37'),0),(ap,grni)
        return dict(status='PASS',qty='1.123456',unit_price='3.000001',receipt_value='3.370369',rounded_ap='3.37',grni=0)
    def idempotency():
        f=fixture(cur,today);k=str(uuid.uuid4());d=command(cur,'SAVE_DRAFT',f['payload'],k)
        assert command(cur,'SAVE_DRAFT',f['payload'],k)==d
        changed=dict(f['payload'],notes='different')
        auth.refused(cur,lambda:command(cur,'SAVE_DRAFT',changed,k),'different payload')
        edited=command(cur,'SAVE_DRAFT',dict(f['payload'],id=d['purchase_id'],notes='reviewed'),version=d['row_version'])
        auth.refused(cur,lambda:post(cur,d),'STALE_VERSION')
        pk=str(uuid.uuid4());p=post(cur,edited,pk);assert post(cur,edited,pk)==p and qty(cur,f)==(10,1)
        assert workspace(cur,dict(purchase_id=d['purchase_id']))['detail']['row_version']==p['row_version']
        assert command(cur,'SAVE_DRAFT',f['payload'],k)==d
        return dict(status='PASS',same_request_one_effect=True,changed_payload_refused=True,stale_refused=True,cached_outcome_not_live_workspace=True)
    def redaction():
        f=fixture(cur,today);d=command(cur,'SAVE_DRAFT',f['payload']);post(cur,d)
        subject,role=custom(cur,OPS);w=workspace(cur,dict(purchase_id=d['purchase_id']),subject)
        text=json.dumps(w)
        for key in ('"finance"','unit_price','line_total','receipt_value','price_state','price_source','benchmark_price_version','payment_status'):assert key not in text,key
        assert w['capabilities']['view_value'] is False
        auth.refused(cur,lambda:command(cur,'SAVE_DRAFT',f['payload'],subject=subject),'CP7_PROCUREMENT_VALUE_DENIED')
        cur.execute("insert into erp.app_role_permissions values(%s,'finance.ap.view')",(role,))
        assert workspace(cur,dict(purchase_id=d['purchase_id']),subject)['detail']['items'][0]['finance']['unit_price']=='10.000000'
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.view'",(role,))
        assert 'finance' not in workspace(cur,dict(purchase_id=d['purchase_id']),subject)['detail']
        return dict(status='PASS',server_money_projection=True,current_grant_revoke=True,manual_price_requires_existing_finance_scope=True)
    def benchmark():
        f=fixture(cur,today);subject,role=custom(cur,OPS)
        cur.execute("insert into erp.fabric_benchmark_price_versions(material_id,benchmark_price_per_base_uom,base_uom_code_snapshot,effective_from,change_reason) select id,7,unit_code,%s,'P09 disposable master' from erp.materials where id=%s",(aa.at(f['day']-timedelta(days=1),0),f['material']))
        p=copy.deepcopy(f['payload']);p['lines'][0].pop('unit_price');p['lines'][0]['price_source']='BENCHMARK'
        d=command(cur,'SAVE_DRAFT',p,subject=subject);r=post(cur,d,subject=subject)
        assert qty(cur,f)==(10,1)
        assert cur.execute('select unit_price,price_state,price_source from erp.material_purchase_items where purchase_id=%s',(r['purchase_id'],)).fetchone()==(7,'ESTIMATED','BENCHMARK')
        assert 'finance' not in workspace(cur,dict(purchase_id=r['purchase_id']),subject)['detail']
        return dict(status='PASS',operations_benchmark_receipt_without_money_payload=True,authoritative_benchmark=7,grni_not_final_price=True)
    def permissions():
        f=fixture(cur,today);subject,role=custom(cur,['warehouse.procurement.view']);workspace(cur,subject=subject)
        auth.refused(cur,lambda:command(cur,'SAVE_DRAFT',f['payload'],subject=subject),'CP7_PROCUREMENT_CREATE_DENIED')
        for key in OPS[1:]+('finance.ap.view',):cur.execute('insert into erp.app_role_permissions values(%s,%s)',(role,key))
        k=str(uuid.uuid4());d=command(cur,'SAVE_DRAFT',f['payload'],k,subject=subject)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.create'",(role,))
        auth.refused(cur,lambda:command(cur,'SAVE_DRAFT',f['payload'],k,subject=subject),'CP7_PROCUREMENT_CREATE_DENIED')
        cur.execute('update erp.app_roles set is_active=false where id=%s',(role,))
        auth.refused(cur,lambda:post(cur,d,subject=subject),'CP7_PROCUREMENT_ACCESS_DENIED')
        assert qty(cur,f)==(0,0)
        for principal in ('cp7_capture','cp7_procure_read'):
            assert not cur.execute("select has_function_privilege(%s,'public.erp_cp7_save_procurement_v1(text,jsonb,uuid,text)','EXECUTE')",(principal,)).fetchone()[0]
            assert not cur.execute("select has_function_privilege(%s,'erp.post_material_purchase_v2(uuid,uuid,bigint,text)','EXECUTE')",(principal,)).fetchone()[0]
        assert not cur.execute("select has_table_privilege('cp7_procure_write','erp.material_purchase_headers','INSERT,UPDATE,DELETE')").fetchone()[0]
        assert cur.execute('select count(*) from cp7_procurement.execution_context').fetchone()[0]==0
        def forge():
            auth.actor(cur,subject)
            cur.execute("insert into cp7_procurement.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),'POST','warehouse.procurement.post')")
        auth.refused(cur,forge,'permission denied')
        return dict(status='PASS',granular_current_permission=True,revoked_replay_denied=True,read_compute_cannot_post=True)
    def paging():
        f=fixture(cur,today)
        cur.execute("insert into erp.material_purchase_headers(purchase_number,supplier_id,location_id,physical_at,status) select %s||'-'||i,%s,%s,%s,'DRAFT' from generate_series(1,105) i",(f['tag'],f['payload']['supplier_id'],f['location'],f['payload']['physical_at']))
        seen=[];offset=0
        while True:
            w=workspace(cur,dict(q=f['tag'],limit=40,offset=offset));assert w['page']['total']=='105'
            seen.extend(r['id'] for r in w['page']['rows']);offset=w['page']['next_offset']
            if offset is None:break
        assert len(seen)==len(set(seen))==105
        assert workspace(cur,dict(q=f['tag'],status='POSTED'))['page']['total']=='0'
        assert options(cur,'LOCATION',f['tag'])['rows'][0]['id']==f['location']
        cur.execute('update erp.locations set is_active=false where id=%s',(f['location'],))
        assert options(cur,'LOCATION',f['tag'])['rows']==[]
        return dict(status='PASS',all_server_pages=105,no_local_first_page_filter=True,inactive_options_hidden=True)
    def invalid_atomic():
        f=fixture(cur,today);bad=copy.deepcopy(f['payload']);bad['lines'][0]['qty']=10
        auth.refused(cur,lambda:command(cur,'SAVE_DRAFT',bad),'CP7_PROCUREMENT_FIELDS')
        bad=copy.deepcopy(f['payload']);bad['lines'][0]['rolls'][0]['qty']='9'
        auth.refused(cur,lambda:command(cur,'SAVE_DRAFT',bad),'does not equal roll total')
        assert not cur.execute('select exists(select 1 from erp.material_purchase_headers where purchase_number=%s)',(f['tag'],)).fetchone()[0]
        d=command(cur,'SAVE_DRAFT',f['payload']);cur.execute('update erp.locations set is_active=false where id=%s',(f['location'],))
        auth.refused(cur,lambda:post(cur,d),'active raw-material warehouse')
        assert qty(cur,f)==(0,0) and workspace(cur,dict(purchase_id=d['purchase_id']))['detail']['status']=='DRAFT'
        auth.refused(cur,lambda:workspace(cur,dict(limit=101)),'CP7_PROCUREMENT_QUERY')
        auth.refused(cur,lambda:workspace(cur,dict(hpp=True)),'CP7_PROCUREMENT_FIELDS')
        return dict(status='PASS',exact_transport=True,roll_mismatch_atomic=True,inactive_location_post_refused=True,no_partial_stock=True)
    def zones():
        f=fixture(cur,today)
        # Ordinary location update must work; registered zone identity and stock
        # guards must survive the OLD.id correction.
        cur.execute('update erp.locations set location_name=location_name||%s where id=%s',(' renamed',f['location']))
        z=bc.svc(cur,'REGISTER_ZONE',dict(zone_kind='SERVICE_POST',location_code=f['tag']+'-ZONE',location_name='P09 service zone',reason='P09 guard control'))['location_id']
        b.api.admin(cur)
        auth.refused(cur,lambda:cur.execute("update erp.locations set location_type='FG_WAREHOUSE' where id=%s",(z,)),'BC_ZONE_IMMUTABLE')
        auth.refused(cur,lambda:cur.execute("update erp.bc_accessory_zones_v1 set zone_kind='INSPECTION' where location_id=%s",(z,)),'BC_ZONE_IMMUTABLE')
        auth.refused(cur,lambda:cur.execute('delete from erp.bc_accessory_zones_v1 where location_id=%s',(z,)),'BC_ZONE_IMMUTABLE')
        p=copy.deepcopy(f['payload']);p['location_id']=str(z)
        d=command(cur,'SAVE_DRAFT',p)
        auth.refused(cur,lambda:post(cur,d),'BC_ZONE_ACCESSORY_ONLY')
        assert qty(cur,f)==(0,0)
        accessory=bc.fixture(cur,today,zones=False);accessory['SERVICE_POST']=z
        bc.fill(cur,accessory,10,today-timedelta(days=1));b.api.admin(cur)
        auth.refused(cur,lambda:cur.execute('update erp.locations set is_active=false where id=%s',(z,)),'BC_ZONE_IMMUTABLE')
        assert cur.execute('select sum(qty_signed) from erp.material_stock_movements where location_id=%s and material_id=%s',(z,accessory['material'])).fetchone()[0]==10
        assert all(r['id']!=str(z) for r in options(cur,'LOCATION',f['tag'])['rows'])
        return dict(status='PASS',ordinary_location_edit=True,zone_type_immutable=True,zone_delete_refused=True,fabric_zone_refused=True,ordinary_accessory_fill=10,nonempty_zone_deactivate_refused=True)
    return [('P09_DRAFT_ESTIMATED_GRNI',estimated),('P09_FINAL_EXACT_VALUE',final_exact),('P09_REPLAY_STALE',idempotency),
      ('P09_OPS_FINANCE_REDACTION',redaction),('P09_OPS_BENCHMARK',benchmark),('P09_PERMISSION_PRINCIPALS',permissions),
      ('P09_COMPLETE_PAGES_OPTIONS',paging),('P09_INVALID_ATOMIC',invalid_atomic),('P09_ZONE_GUARD_REGRESSION',zones)]

def races(tools,today):
    def competing(same):
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);d=command(cur,'SAVE_DRAFT',f['payload']);conn.commit()
        barrier=threading.Barrier(2);key=str(uuid.uuid4())
        def send():
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait(5)
                try:r=post(cur,d,key if same else None);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(send);z=pool.submit(send);results=[a.result(20),z.result(20)]
        if same:assert results[0]==results[1] and isinstance(results[0],dict),results
        else:assert sum(isinstance(r,dict) for r in results)==1 and any('Purchase must be DRAFT' in r for r in results if isinstance(r,str)),results
        with tools.connect() as conn,conn.cursor() as cur:assert qty(cur,f)==(10,1)
        return dict(status='PASS',same_request=same,posted_qty=10,movements=1,one_stock_effect=True)
    def revoke_wait():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);d=command(cur,'SAVE_DRAFT',f['payload']);subject,role=custom(cur,OPS);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.material_purchase_headers where id=%s for update',(d['purchase_id'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:post(cur,d,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()')
                            blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                    assert blocked,'PROCUREMENT_NOT_WAITING'
                    with tools.connect() as conn,conn.cursor() as cur:
                        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.post'",(role,));conn.commit()
                finally:holder.rollback()
                error=future.result(20)
        assert 'CP7_PROCUREMENT_ACCESS_CHANGED' in error or 'Internal ERP access required' in error,error
        with tools.connect() as conn,conn.cursor() as cur:
            assert qty(cur,f)==(0,0)
            assert cur.execute('select status from erp.material_purchase_headers where id=%s',(d['purchase_id'],)).fetchone()[0]=='DRAFT'
        return dict(status='PASS',current_revoke_after_real_row_wait=True,whole_post_rolled_back=True)
    return [('P09_RACE_SAME_REQUEST',lambda:competing(True)),('P09_RACE_COMPETING_POST',lambda:competing(False)),('P09_RACE_REVOKE_WAIT',revoke_wait)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p09-owner');ops=http.login('ADMIN','p09-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today)
            cur.execute("delete from erp.app_role_permissions where role_id=(select id from erp.app_roles where role_code='ADMIN') and permission_key in ('finance.ap.view','warehouse.procurement.post')")
            conn.commit()
        args=dict(p_action='SAVE_DRAFT',p_payload=f['payload'],p_request=str(uuid.uuid4()),p_expected=None)
        assert http.anon_rpc('erp_cp7_save_procurement_v1',args)['status'] in (401,403,404)
        r=owner.rpc('erp_cp7_save_procurement_v1',args);assert r['status']==200,r
        d=r['body'];assert owner.rpc('erp_cp7_save_procurement_v1',args)['body']==d
        read=ops.rpc('erp_cp7_get_procurement_v1',dict(p_query=dict(purchase_id=d['purchase_id'])));assert read['status']==200,read
        assert 'finance' not in read['body']['detail']
        args=dict(p_action='POST',p_payload=dict(purchase_id=d['purchase_id'],change_reason='P09 real HTTP post'),p_request=str(uuid.uuid4()),p_expected=d['row_version'])
        assert ops.rpc('erp_cp7_save_procurement_v1',args)['status']==403
        p=owner.rpc('erp_cp7_save_procurement_v1',args);assert p['status']==200,p
        assert owner.rpc('erp_cp7_save_procurement_v1',args)['body']==p['body']
        with http.connect() as conn,conn.cursor() as cur:
            assert qty(cur,f)==(10,1)
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_save_procurement_v1',args)['status']==403
        return dict(status='PASS',real_auth_postgrest=True,one_stock_effect=True,replay_and_revoke=True,ops_money_redacted=True)
    return [('P09_HTTP_RECEIPT_REPLAY_AUTH',flow)]
