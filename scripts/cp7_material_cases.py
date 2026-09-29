"""P09 material proof through actual receipt/transfer writers; no stock inserts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import copy,json,threading,time,uuid
import psycopg
import cp7_procurement_cases as receipt
auth,b,aa=receipt.auth,receipt.b,receipt.aa

def rpc(cur,name,args,subject=None):
    auth.actor(cur,subject)
    placeholders=','.join(['%s']*len(args))
    assert name in ('erp_cp7_get_materials_v1','erp_cp7_get_material_ledger_v1','erp_cp7_get_material_transfers_v1','erp_cp7_get_material_locations_v1','erp_cp7_save_materials_v1')
    r=cur.execute('select public.'+name+'('+placeholders+')',args).fetchone()[0]
    b.api.admin(cur);return r

def stock(cur,f,zero=False,subject=None,**query):
    return rpc(cur,'erp_cp7_get_materials_v1',[json.dumps(dict(material_id=f['material'],show_zero=zero,**query))],subject)

def ledger(cur,f,loc,offset=0,limit=100,subject=None):
    return rpc(cur,'erp_cp7_get_material_ledger_v1',[f['material'],f['roll'],loc,offset,limit],subject)

def command(cur,action,payload,version=None,key=None,subject=None):
    return rpc(cur,'erp_cp7_save_materials_v1',[action,json.dumps(payload,default=str),key or uuid.uuid4(),version],subject)

def read_transfer(cur,ident,subject=None):
    return rpc(cur,'erp_cp7_get_material_transfers_v1',[json.dumps(dict(transfer_id=ident))],subject)

def fixture(cur,today,post=True):
    f=receipt.fixture(cur,today);d=receipt.command(cur,'SAVE_DRAFT',f['payload']);f['receipt']=receipt.post(cur,d) if post else d
    f['roll']=str(cur.execute('select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s',(d['purchase_id'],)).fetchone()[0])
    f['destination']=str(uuid.uuid4())
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,%s,'RAW_MATERIAL_WAREHOUSE',true)",(f['destination'],f['tag']+'-TO',f['tag']+' destination'))
    return f

def draft(cur,f,qty='4',source=None,dest=None,at=None,subject=None):
    p=dict(transfer_number=f['tag']+'-T-'+uuid.uuid4().hex[:6],from_location_id=source or f['location'],to_location_id=dest or f['destination'],
      physical_at=at or aa.at(f['day']+timedelta(days=1),10).isoformat(),change_reason='P09 ordinary warehouse transfer',
      items=[dict(material_id=f['material'],roll_id=f['roll'],qty=qty)])
    d=command(cur,'SAVE_TRANSFER',p,subject=subject);return d,p

def post(cur,d,key=None,subject=None):
    return command(cur,'POST_TRANSFER',dict(transfer_id=d['transfer_id'],change_reason='P09 transfer checked'),d['row_version'],key,subject)

def reverse(cur,d,key=None,subject=None):
    return command(cur,'REVERSE_TRANSFER',dict(transfer_id=d['transfer_id'],change_reason='P09 reverse transfer'),d['row_version'],key,subject)

def balances(cur,f):
    return {r['location_id']:Decimal(r['qty']) for r in stock(cur,f,True)['page']['rows']}

PERMS=('warehouse.material.view','warehouse.stock.adjust')
def smoke(cur,today):
    def run():
        f=fixture(cur,today);w=stock(cur,f);assert w['page']['total']=='1' and Decimal(w['page']['rows'][0]['qty'])==10
        d,p=draft(cur,f);post(cur,d);assert balances(cur,f)=={f['location']:6,f['destination']:4}
        return dict(status='PASS',ordinary_receipt_transfer=True,source=6,destination=4)
    return [('P09_MATERIAL_SMOKE',run)]

def cases(cur,today):
    def draft_not_stock():
        f=fixture(cur,today,False)
        assert cur.execute('select cached_qty from erp.material_rolls where id=%s',(f['roll'],)).fetchone()[0]==10
        assert stock(cur,f,True)['page']['rows']==[] and ledger(cur,f,f['location'])['page']['total']=='0'
        receipt.post(cur,f['receipt']);assert balances(cur,f)=={f['location']:10}
        return dict(status='PASS',draft_cached_qty=10,draft_on_hand=0,posted_on_hand=10)
    def conserve():
        f=fixture(cur,today);d,p=draft(cur,f);assert balances(cur,f)=={f['location']:10}
        d=post(cur,d);w=stock(cur,f,True);assert balances(cur,f)=={f['location']:6,f['destination']:4}
        assert sum(Decimal(r['valuation']['value']) for r in w['page']['rows'])==100
        assert all(Decimal(r['valuation']['unit_cost'])==10 for r in w['page']['rows'])
        moves=cur.execute("select sum(qty_signed),sum(qty_signed*unit_cost_snapshot),count(*) from erp.material_stock_movements where source_type='MATERIAL_TRANSFER' and source_id=%s",(d['transfer_id'],)).fetchone();assert moves==(0,0,2),moves
        page=ledger(cur,f,f['location'],0,1)['page'];assert page['total']=='2' and page['next_offset']==1 and Decimal(page['rows'][0]['running_qty'])==6
        old=ledger(cur,f,f['location'],1,1)['page'];assert Decimal(old['rows'][0]['running_qty'])==10 and old['next_offset'] is None
        rev=reverse(cur,d);assert rev['status']=='REVERSED' and balances(cur,f)=={f['location']:10,f['destination']:0}
        assert cur.execute('select count(*) from erp.material_stock_movements where reversal_of_id is not null and source_id=%s',(d['transfer_id'],)).fetchone()[0]==2
        return dict(status='PASS',total_qty=10,total_value=100,transfer_net_qty=0,transfer_net_value=0,paged_prefix=[6,10],reversal_pairs=2)
    def historical():
        f=fixture(cur,today);d,p=draft(cur,f,at=aa.at(f['day']-timedelta(days=1),10).isoformat())
        message=auth.refused(cur,lambda:post(cur,d),'negative')
        assert balances(cur,f)=={f['location']:10} and read_transfer(cur,d['transfer_id'])['detail']['status']=='DRAFT'
        assert cur.execute('select count(*) from erp.material_stock_movements where source_id=%s',(d['transfer_id'],)).fetchone()[0]==0
        return dict(status='PASS',backdated_negative_prefix_refused=True,zero_partial_effects=True,refusal=message)
    def location_and_roll():
        f=fixture(cur,today);d,p=draft(cur,f);cur.execute('update erp.locations set is_active=false where id=%s',(f['destination'],))
        auth.refused(cur,lambda:post(cur,d),'active raw-material warehouses');assert balances(cur,f)=={f['location']:10}
        assert rpc(cur,'erp_cp7_get_material_locations_v1',[f['tag']+'-TO',0,25])['rows']==[]
        cur.execute('update erp.locations set is_active=true where id=%s',(f['destination'],))
        g=fixture(cur,today);bad=copy.deepcopy(p);bad['items'][0]['roll_id']=g['roll']
        auth.refused(cur,lambda:command(cur,'SAVE_TRANSFER',bad),'CP7_MATERIAL_FABRIC_ROLL_REQUIRED')
        bad=copy.deepcopy(p);bad['items'][0]['qty']=4
        auth.refused(cur,lambda:command(cur,'SAVE_TRANSFER',bad),'CP7_MATERIAL_EXACT_LINE')
        cur.execute('update erp.materials set is_active=false where id=%s',(f['material'],))
        auth.refused(cur,lambda:post(cur,d),'AM_TRANSFER_REQUIRES_EVERY_MATERIAL_ACTIVE')
        assert stock(cur,f)['page']['rows'][0]['availability']=='MATERIAL_INACTIVE'
        return dict(status='PASS',inactive_location_atomic=True,cross_material_roll_refused=True,inexact_transport_refused=True,inactive_material_visible_unavailable=True)
    def redaction():
        f=fixture(cur,today);subject,role=receipt.custom(cur,PERMS)
        w=stock(cur,f,subject=subject);l=ledger(cur,f,f['location'],subject=subject)
        for value in (w,l):
            assert value['financial_captured'] is False
            for key in ('valuation','unit_cost','value','movement_value'):assert '"'+key+'"' not in json.dumps(value)
        assert w['capabilities']==dict(transfer=True,reverse_transfer=False)
        d,p=draft(cur,f,subject=subject);d=post(cur,d,subject=subject)
        auth.refused(cur,lambda:reverse(cur,d,subject=subject),'CP7_MATERIAL_REVERSE_DENIED')
        cur.execute("insert into erp.app_role_permissions values(%s,'finance.hpp.view')",(role,))
        assert stock(cur,f,subject=subject)['financial_captured'] is True
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.material.view'",(role,))
        auth.refused(cur,lambda:stock(cur,f,subject=subject),'CP7_MATERIAL_ACCESS_DENIED')
        return dict(status='PASS',ops_no_money=True,custom_role_transfer=True,legacy_reverse_guard_preserved=True,current_grant_revoke=True)
    def replay():
        f=fixture(cur,today);d,p=draft(cur,f);key=str(uuid.uuid4());out=post(cur,d,key);assert post(cur,d,key)==out
        auth.refused(cur,lambda:post(cur,d),'STALE_VERSION')
        key2=str(uuid.uuid4());r=reverse(cur,out,key2);assert reverse(cur,out,key2)==r
        assert balances(cur,f)=={f['location']:10,f['destination']:0}
        assert cur.execute('select count(*) from erp.material_stock_movements where source_id=%s',(d['transfer_id'],)).fetchone()[0]==4
        return dict(status='PASS',post_and_reverse_replay_one_effect=True,stale_refused=True)
    def consumed_destination():
        f=fixture(cur,today);d,p=draft(cur,f);d=post(cur,d)
        # A normal second transfer consumes destination stock; reversal may not
        # manufacture it back. Restore it by normal reverse, then reverse first.
        second,p=draft(cur,f,qty='1',source=f['destination'],dest=f['location'],at=aa.at(f['day']+timedelta(days=2),10).isoformat());second=post(cur,second)
        auth.refused(cur,lambda:reverse(cur,d),'negative');assert balances(cur,f)=={f['location']:7,f['destination']:3}
        assert read_transfer(cur,d['transfer_id'])['detail']['status']=='POSTED'
        reverse(cur,second);reverse(cur,d);assert balances(cur,f)=={f['location']:10,f['destination']:0}
        return dict(status='PASS',consumed_destination_reversal_refused=True,dependency_restored_then_reverse=True)
    def pages_units():
        f=receipt.fixture(cur,today,qty='105');f['payload']['lines'][0]['rolls']=[dict(roll_number=f['tag']+f'-R{i:03}',qty='1') for i in range(105)]
        d=receipt.command(cur,'SAVE_DRAFT',f['payload']);receipt.post(cur,d)
        seen=[];off=0
        while True:
            w=stock(cur,f,offset=off,limit=40);assert w['page']['total']=='105';seen.extend(x['roll_id'] for x in w['page']['rows']);off=w['page']['next_offset']
            if off is None:break
        assert len(seen)==len(set(seen))==105
        assert len(stock(cur,f,q='R104')['page']['rows'])==1
        g=receipt.fixture(cur,today,qty='2');cur.execute("update erp.materials set unit_code='M' where id=%s",(g['material'],))
        # Master setup only; both units acquire stock through ordinary posting.
        p=receipt.command(cur,'SAVE_DRAFT',g['payload']);receipt.post(cur,p)
        allrows=rpc(cur,'erp_cp7_get_materials_v1',[json.dumps(dict(q='Z isolated cp7-p09 material'))])
        units={x['unit_code'] for x in allrows['totals_by_unit']};assert 'M' in units and 'yd' in units,units
        return dict(status='PASS',complete_server_pages=105,last_page_search=True,units_not_summed_together=True)
    def principals():
        f=fixture(cur,today);subject,role=receipt.custom(cur,['warehouse.material.view']);d,p=draft(cur,f)
        auth.refused(cur,lambda:post(cur,d,subject=subject),'CP7_MATERIAL_ADJUST_DENIED')
        for principal in ('cp7_capture','cp7_material_read','cp7_procure_read'):
            assert not cur.execute("select has_function_privilege(%s,'public.erp_cp7_save_materials_v1(text,jsonb,uuid,text)','EXECUTE')",(principal,)).fetchone()[0]
        assert not cur.execute("select has_table_privilege('cp7_material_write','erp.material_transfers','INSERT,UPDATE,DELETE')").fetchone()[0]
        assert cur.execute('select count(*) from cp7_material.execution_context').fetchone()[0]==0
        def forge():
            auth.actor(cur,subject);cur.execute("insert into cp7_material.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),'POST_TRANSFER','warehouse.stock.adjust')")
        auth.refused(cur,forge,'permission denied')
        return dict(status='PASS',view_only_cannot_transfer=True,compute_read_no_writer=True,no_context_forge=True)
    return [('P09_MATERIAL_DRAFT_NOT_STOCK',draft_not_stock),('P09_TRANSFER_CONSERVATION',conserve),('P09_TRANSFER_HISTORICAL_PREFIX',historical),
      ('P09_TRANSFER_LOCATIONS_LINEAGE',location_and_roll),('P09_MATERIAL_REDACTION_ACCESS',redaction),('P09_TRANSFER_REPLAY_STALE',replay),
      ('P09_TRANSFER_CONSUMED_REVERSE',consumed_destination),('P09_MATERIAL_COMPLETE_PAGES_UNITS',pages_units),('P09_MATERIAL_PRINCIPALS',principals)]

def races(tools,today):
    def compete():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);one,_=draft(cur,f,qty='7');two,_=draft(cur,f,qty='7');conn.commit()
        barrier=threading.Barrier(2)
        def send(d):
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait(5)
                try:r=post(cur,d);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(send,d) for d in (one,two)];results=[f.result(30) for f in futures]
        assert sum(isinstance(r,dict) for r in results)==1 and any('negative' in r.lower() for r in results if isinstance(r,str)),results
        with tools.connect() as conn,conn.cursor() as cur:assert balances(cur,f)=={f['location']:3,f['destination']:7}
        return dict(status='PASS',two_documents_compete_for_same_roll=True,one_commit=True,source=3,destination=7)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);d,_=draft(cur,f);subject,role=receipt.custom(cur,PERMS);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.material_transfers where id=%s for update',(d['transfer_id'],))
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
                        assert blocked,'EXPECTED_REAL_ROW_WAIT'
                        c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.stock.adjust'",(role,))
                finally:holder.rollback()
                result=future.result(30)
        assert 'CP7_MATERIAL_ACCESS_CHANGED' in result or 'Internal ERP access required' in result,result
        with tools.connect() as conn,conn.cursor() as cur:assert balances(cur,f)=={f['location']:10}
        return dict(status='PASS',current_revoke_after_real_row_wait=True,whole_transfer_rolled_back=True)
    return [('P09_TRANSFER_RACE_SHARED_ROLL',compete),('P09_TRANSFER_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p09-material-owner');ops=http.login('ADMIN','p09-material-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);d,p=draft(cur,f)
            role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key in('finance.hpp.view','warehouse.stock.adjust')",(role,));conn.commit()
        read=ops.rpc('erp_cp7_get_materials_v1',dict(p_query=dict(material_id=f['material'])));assert read['status']==200,read
        assert 'valuation' not in json.dumps(read['body'])
        args=dict(p_action='POST_TRANSFER',p_payload=dict(transfer_id=d['transfer_id'],change_reason='P09 real transfer HTTP'),p_request=str(uuid.uuid4()),p_expected=d['row_version'])
        assert http.anon_rpc('erp_cp7_save_materials_v1',args)['status'] in(401,403,404)
        assert ops.rpc('erp_cp7_save_materials_v1',args)['status']==403
        posted=owner.rpc('erp_cp7_save_materials_v1',args);assert posted['status']==200,posted
        assert owner.rpc('erp_cp7_save_materials_v1',args)['body']==posted['body']
        with http.connect() as conn,conn.cursor() as cur:
            assert balances(cur,f)=={f['location']:6,f['destination']:4}
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_save_materials_v1',args)['status']==403
        return dict(status='PASS',real_auth_postgrest=True,ops_money_redacted=True,post_replay_revoke=True)
    return [('P09_MATERIAL_HTTP_TRANSFER_AUTH',flow)]
