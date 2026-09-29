"""P09 physical source returns and their accepted portable supplier credit.

Only master setup is administrative. Receipts, transfers, invoices, returns and
credit allocations under proof call their normal public/native boundaries.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import copy,json,threading,time,uuid
import psycopg
from psycopg.types.json import Jsonb
import cp7_procurement_cases as receipt
import cp7_material_cases as material
import cp7_invoice_cases as invoice
import cp6_bf_supplier_probe as credit
auth,b,aa=receipt.auth,receipt.b,receipt.aa
PERMS=('warehouse.procurement.view','warehouse.procurement.create','warehouse.procurement.reverse')

def command(cur,action,payload,version=None,key=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_save_supplier_return_v1(%s,%s::jsonb,%s,%s)',(action,json.dumps(payload,default=str),key or uuid.uuid4(),version)).fetchone()[0]
    b.api.admin(cur);return r

def read(cur,f,location=None,offset=0,limit=25,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_supplier_returns_v1(%s,%s,%s,%s)',(f['receipt']['purchase_id'],location,offset,limit)).fetchone()[0]
    b.api.admin(cur);return r

def fixture(cur,today,final=False,accessory=False,qty='10',price='10'):
    if not accessory:return invoice.fixture(cur,today,qty,price,final)
    f=receipt.fixture(cur,today,qty,price,final)
    a=receipt.bc.fixture(cur,today,purchase=False,zones=False)
    f.update(material=a['material']);f['payload']['lines']=[dict(material_id=a['material'],qty=qty,unit_price=price,price_state='FINAL' if final else 'ESTIMATED',price_source='SUPPLIER_INVOICE' if final else 'MANUAL_ESTIMATE',rolls=[])]
    d=receipt.command(cur,'SAVE_DRAFT',f['payload']);f['receipt']=receipt.post(cur,d)
    f['item']=str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(d['purchase_id'],)).fetchone()[0]);f['roll']=None
    return f

def payload(f,qty='2',location=None,at=None):
    return dict(purchase_id=f['receipt']['purchase_id'],return_number=f['tag']+'-RETURN-'+uuid.uuid4().hex[:6],supplier_id=f['payload']['supplier_id'],
      location_id=location or f['location'],physical_at=at or aa.at(f['day']+timedelta(days=2),16).isoformat(),change_reason='Supplier source return review',reason='Supplier responsible for returned material',
      items=[dict(purchase_item_id=f['item'],material_id=f['material'],roll_id=f['roll'],qty=qty,notes='Physical goods returned')])

def save(cur,f,qty='2',subject=None,**kw):
    p=payload(f,qty,**kw);return command(cur,'SAVE',p,subject=subject),p

def post(cur,f,d,key=None,subject=None):
    return command(cur,'POST',dict(purchase_id=f['receipt']['purchase_id'],return_id=d['return_id'],change_reason='Physical return checked'),d['row_version'],key,subject)

def reverse(cur,f,d,key=None,subject=None):
    return command(cur,'REVERSE',dict(purchase_id=f['receipt']['purchase_id'],return_id=d['return_id'],change_reason='Undo source return after review'),d['row_version'],key,subject)

def amounts(cur,f):return invoice.amounts(cur,f)

def smoke(cur,today):
    def run():
        f=fixture(cur,today);d,p=save(cur,f);assert amounts(cur,f)==(0,100,10,10)
        d=post(cur,f,d);assert amounts(cur,f)==(0,80,8,10)
        w=read(cur,f,f['location']);assert w['page']['rows'][0]['status']=='POSTED' and Decimal(w['source_lines'][0]['rolls'][0]['location_qty'])==8
        reverse(cur,f,d);assert amounts(cur,f)==(0,100,10,10)
        return dict(status='PASS',ordinary_public_return_and_inverse=True)
    return [('P09_RETURN_SMOKE',run)]

def cases(cur,today):
    def transferred():
        f=material.fixture(cur,today);f['item']=str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(f['receipt']['purchase_id'],)).fetchone()[0])
        t,_=material.draft(cur,f);material.post(cur,t)
        d,p=save(cur,f,'3',location=f['destination']);assert material.balances(cur,f)=={f['location']:6,f['destination']:4}
        d=post(cur,f,d);assert amounts(cur,f)==(0,70,7,10) and material.balances(cur,f)=={f['location']:6,f['destination']:1}
        w=read(cur,f,f['destination']);doc=w['page']['rows'][0];assert Decimal(doc['finance']['ap_relief_amount'])==0 and Decimal(doc['finance']['grni_relief_amount'])==30
        assert Decimal(w['source_lines'][0]['unreturned_qty'])==7
        reverse(cur,f,d);assert amounts(cur,f)==(0,100,10,10) and material.balances(cur,f)=={f['location']:6,f['destination']:4}
        return dict(status='PASS',draft_no_effect=True,transferred_source_qty=[6,1],return_grni=30,restored=[6,4],stock_value=[70,100])
    def portable(accessory):
        f=fixture(cur,today,True,accessory);g=fixture(cur,today,True,accessory)
        d,p=save(cur,f);d=post(cur,f,d);before=credit.state(cur,dict(material=f['material'],purchases=[f['receipt']['purchase_id'],g['receipt']['purchase_id']]))
        assert before['ap']==['80.00','100.00']
        cf=dict(ret=d['return_id'],purchases=[f['receipt']['purchase_id'],g['receipt']['purchase_id']])
        move=credit.payload(cur,cf,[(g['receipt']['purchase_id'],'20.00')]);key=str(uuid.uuid4())
        one=credit.call(cur,move,key);again=credit.call(cur,move,key)
        after=credit.state(cur,dict(material=f['material'],purchases=cf['purchases']))
        assert after['ap']==['100.00','80.00'] and after['ledger']==before['ledger'] and after['values']==before['values'] and again['replayed'] and again['version']==one['version']
        auth.refused(cur,lambda:reverse(cur,f,d),'BF_CREDIT_RETURN_IN_USE')
        credit.call(cur,credit.payload(cur,cf,[]));restored=credit.state(cur,dict(material=f['material'],purchases=cf['purchases']));assert restored==before
        reverse(cur,f,d);assert amounts(cur,f)==(100,0,10,10)
        return dict(status='PASS',accessory=accessory,credit_original=[80,100],moved=[100,80],restored=[80,100],no_double_ap_or_stock=True,return_reversal_dependency=True)
    def partial():
        f=fixture(cur,today);invoice.finalize(cur,f)
        d,p=save(cur,f,'6');assert amounts(cur,f)==(50,60,10,11)
        d=post(cur,f,d);doc=read(cur,f,f['location'])['page']['rows'][0];l=doc['lines'][0]['finance']
        assert tuple(Decimal(l[k]) for k in ('credit_unit_price','ap_relief_qty','grni_relief_qty','ap_relief_amount','grni_relief_amount'))==(11,4,2,44,20),l
        assert amounts(cur,f)==(6,40,4,Decimal('11.25')),amounts(cur,f)
        reverse(cur,f,d);assert amounts(cur,f)==(50,60,10,11)
        return dict(status='PASS',snapshot_credit_unit_price=11,ap_relief=44,grni_relief=20,remaining_ap=6,remaining_grni=40,remaining_qty=4,remaining_unit_cost='11.25',inverse_restores_source=True)
    def exact():
        f=fixture(cur,today,True,qty='1.123456',price='3.000001');d,p=save(cur,f,'0.123456');d=post(cur,f,d)
        doc=read(cur,f,f['location'])['page']['rows'][0];assert doc['lines'][0]['qty']=='0.123456' and doc['lines'][0]['finance']['ap_relief_amount']=='0.370368'
        assert amounts(cur,f)[2]==1 and round(amounts(cur,f)[0],2)==Decimal('3.00')
        posted_credit=cur.execute('select erp.bf_supplier_credit_source_v1(%s,%s)',(d['return_id'],f['receipt']['purchase_id'])).fetchone()[0];assert posted_credit==Decimal('.37'),posted_credit
        reverse(cur,f,d);assert amounts(cur,f)[2]==Decimal('1.123456') and round(amounts(cur,f)[0],2)==Decimal('3.37')
        return dict(status='PASS',exact_qty='0.123456',source_relief='0.370368',portable_booked_credit='0.37',reversal_restores_stock=True)
    def replay():
        f=fixture(cur,today);p=payload(f);key=str(uuid.uuid4());d=command(cur,'SAVE',p,key=key)
        edited=command(cur,'SAVE',dict(p,id=d['return_id'],reason='Updated draft'),d['row_version'])
        assert command(cur,'SAVE',p,key=key)==d
        auth.refused(cur,lambda:command(cur,'SAVE',dict(p,reason='Altered old intent'),key=key),'CP7_RETURN_REQUEST_PAYLOAD_CHANGED')
        auth.refused(cur,lambda:post(cur,f,d),'STALE_VERSION')
        pk=str(uuid.uuid4());posted=post(cur,f,edited,pk);rk=str(uuid.uuid4());rev=reverse(cur,f,posted,rk)
        assert post(cur,f,edited,pk)==posted and reverse(cur,f,posted,rk)==rev and command(cur,'SAVE',p,key=key)==d
        assert read(cur,f)['page']['rows'][0]['status']=='REVERSED' and amounts(cur,f)==(0,100,10,10)
        # An accepted external writer may later reassign a DRAFT's source.
        # An old request is still an outcome, not a new claim on that draft.
        g=fixture(cur,today);p2=payload(f);k2=str(uuid.uuid4());d2=command(cur,'SAVE',p2,key=k2)
        replacement=payload(g);replacement['id']=d2['return_id']
        receipt.bc.internal(cur,'save_material_supplier_return_draft_v2',Jsonb({k:v for k,v in replacement.items() if k!='purchase_id'}),str(uuid.uuid4()),int(d2['row_version']))
        assert command(cur,'SAVE',p2,key=k2)==d2 and read(cur,g)['page']['rows'][0]['id']==d2['return_id']
        return dict(status='PASS',cached_outcomes_survive_later_changes=True,stale_and_changed_payload_refused=True,source_corrected_by_other_writer_replay_preserved=True)
    def atomic():
        f=fixture(cur,today);g=fixture(cur,today);before=b.boundary.snapshot(cur)
        for field,val in [('roll_id',g['roll']),('purchase_item_id',g['item']),('qty',2),('supplier_credit_unit_price','0')]:
            p=payload(f);p['items'][0][field]=val
            auth.refused(cur,lambda p=p:command(cur,'SAVE',p),'CP7_RETURN_')
        assert b.boundary.snapshot(cur)==before and read(cur,f)['page']['total']=='0'
        d,p=save(cur,f);cur.execute('update erp.locations set is_active=false where id=%s',(f['location'],))
        auth.refused(cur,lambda:post(cur,f,d),'CP7_RETURN_ACTIVE_WAREHOUSE_REQUIRED')
        cur.execute('update erp.locations set is_active=true where id=%s',(f['location'],));cur.execute('update erp.materials set is_active=false where id=%s',(f['material'],))
        auth.refused(cur,lambda:post(cur,f,d),'CP7_RETURN_ACTIVE_MATERIAL_REQUIRED');assert amounts(cur,f)==(0,100,10,10)
        return dict(status='PASS',foreign_source_and_fabric_roll_refused=True,caller_credit_price_forbidden=True,exact_string_transport=True,inactive_post_atomic=True)
    def historical():
        f=material.fixture(cur,today);f['item']=str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(f['receipt']['purchase_id'],)).fetchone()[0])
        t,_=material.draft(cur,f);material.post(cur,t)
        d,p=save(cur,f,'2',location=f['destination'],at=aa.at(f['day'],12).isoformat())
        auth.refused(cur,lambda:post(cur,f,d),'AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY')
        assert amounts(cur,f)==(0,100,10,10) and read(cur,f)['page']['rows'][0]['status']=='DRAFT'
        assert cur.execute('select count(*) from erp.material_stock_movements where source_id in(select id from erp.material_supplier_return_items where return_id=%s)',(d['return_id'],)).fetchone()[0]==0
        return dict(status='PASS',historical_destination_prefix_refused=True,zero_partial_movement_or_ap=True)
    def access():
        f=fixture(cur,today,True);subject,role=receipt.custom(cur,PERMS);d,p=save(cur,f,subject=subject);key=str(uuid.uuid4());d=post(cur,f,d,key,subject)
        w=read(cur,f,f['location'],subject=subject);encoded=json.dumps(w)
        assert w['financial_captured'] is False and all(k not in encoded for k in ('"finance"','credit_unit_price','ap_relief_amount','grni_relief_amount'))
        auth.refused(cur,lambda:reverse(cur,f,d,subject=subject),'CP7_RETURN_ACTION_DENIED')
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.reverse'",(role,))
        auth.refused(cur,lambda:post(cur,f,d,key,subject),'CP7_RETURN_ACTION_DENIED')
        for principal in ('cp7_capture','cp7_return_read','cp7_procure_read'):
            assert not cur.execute("select has_function_privilege(%s,'public.erp_cp7_save_supplier_return_v1(text,jsonb,uuid,text)','EXECUTE')",(principal,)).fetchone()[0]
        assert not cur.execute("select has_table_privilege('cp7_return_write','erp.material_supplier_returns','SELECT,INSERT,UPDATE,DELETE')").fetchone()[0]
        def forge():
            auth.actor(cur,subject);cur.execute("insert into cp7_supplier_return.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),'POST','warehouse.procurement.reverse')")
        auth.refused(cur,forge,'permission denied');assert cur.execute('select count(*) from cp7_supplier_return.execution_context').fetchone()[0]==0
        return dict(status='PASS',ops_can_save_post_without_money=True,legacy_reverse_owner_admin=True,current_permission_before_cached_outcome=True,private_context_no_forge=True,writer_no_business_select_dml=True)
    def complete():
        f=fixture(cur,today,qty='30');g=fixture(cur,today);p=payload(f);p['items']+=payload(g)['items']
        native={k:v for k,v in p.items() if k!='purchase_id'}
        d=receipt.bc.internal(cur,'save_material_supplier_return_draft_v2',Jsonb(native),str(uuid.uuid4()),None)
        w=read(cur,f);doc=w['page']['rows'][0];assert doc['line_count']=='2' and len(doc['lines'])==2 and not doc['single_receipt']
        auth.refused(cur,lambda:command(cur,'POST',dict(purchase_id=f['receipt']['purchase_id'],return_id=d['material_supplier_return_id'],change_reason='Cannot post partial document'),str(d['row_version'])),'CP7_RETURN_COMPLETE_SOURCE_DOCUMENT_REQUIRED')
        for _ in range(26):save(cur,f,'1')
        pages=[read(cur,f,offset=i,limit=10)['page'] for i in (0,10,20)]
        assert [len(p['rows']) for p in pages]==[10,10,7] and len({d['id'] for p in pages for d in p['rows']})==27
        return dict(status='PASS',multi_receipt_document_fully_read=True,bounded_command_refuses_mixed_source=True,complete_pages=27)
    return [('P09_RETURN_TRANSFERRED_GRNI',transferred),('P09_RETURN_FABRIC_PORTABLE_CREDIT',lambda:portable(False)),('P09_RETURN_ACCESSORY_PORTABLE_CREDIT',lambda:portable(True)),
      ('P09_RETURN_PARTIAL_AP_GRNI',partial),('P09_RETURN_EXACT_CENTS',exact),('P09_RETURN_REPLAY_STALE_SOURCE',replay),('P09_RETURN_ATOMIC_LINEAGE',atomic),
      ('P09_RETURN_HISTORICAL_PREFIX',historical),('P09_RETURN_ACCESS_PRINCIPALS',access),('P09_RETURN_COMPLETE_DOCUMENT_PAGES',complete)]

def races(tools,today):
    def competing(same):
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);a,_=save(cur,f,'7');z=a if same else save(cur,f,'7')[0];conn.commit()
        barrier=threading.Barrier(2);key=str(uuid.uuid4())
        def send(d):
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait(5)
                try:r=post(cur,f,d,key if same else None);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            x=pool.submit(send,a);y=pool.submit(send,z);results=[x.result(30),y.result(30)]
        if same:assert isinstance(results[0],dict) and results[0]==results[1],results
        else:assert sum(isinstance(r,dict) for r in results)==1,results
        with tools.connect() as conn,conn.cursor() as cur:
            assert amounts(cur,f)==(0,30,3,10) and cur.execute("select count(*) from erp.material_supplier_returns where id=any(%s::uuid[]) and status='POSTED'",([a['return_id'],z['return_id']],)).fetchone()[0]==1
        return dict(status='PASS',same_request=same,one_return_effect=True,remaining_qty=3,grni=30)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);subject,role=receipt.custom(cur,PERMS);d,p=save(cur,f,subject=subject);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.material_supplier_returns where id=%s for update',(d['return_id'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:post(cur,f,d,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);deadline=time.monotonic()+8;blocked=False
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                        assert blocked,'EXPECTED_ACTUAL_RETURN_ROW_WAIT'
                        c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.reverse'",(role,))
                finally:holder.rollback()
                result=future.result(30)
        assert 'CP7_RETURN_ACCESS_CHANGED' in result or 'Internal ERP access required' in result,result
        with tools.connect() as conn,conn.cursor() as cur:
            assert amounts(cur,f)==(0,100,10,10) and read(cur,f)['page']['rows'][0]['status']=='DRAFT'
            assert cur.execute('select count(*) from cp7_supplier_return.execution_context').fetchone()[0]==0
        return dict(status='PASS',revoke_during_real_wait=True,whole_return_and_journal_rolled_back=True)
    return [('P09_RETURN_RACE_SAME_REQUEST',lambda:competing(True)),('P09_RETURN_RACE_SOURCE_CAPACITY',lambda:competing(False)),('P09_RETURN_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p09-return-owner');ops=http.login('ADMIN','p09-return-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today,True);p=payload(f);cur.execute("delete from erp.app_role_permissions where role_id=(select id from erp.app_roles where role_code='ADMIN') and permission_key='finance.ap.view'");conn.commit()
        args=dict(p_action='SAVE',p_payload=p,p_request=str(uuid.uuid4()),p_expected=None)
        d=owner.rpc('erp_cp7_save_supplier_return_v1',args);assert d['status']==200,d
        postargs=dict(p_action='POST',p_payload=dict(purchase_id=f['receipt']['purchase_id'],return_id=d['body']['return_id'],change_reason='HTTP return reviewed'),p_request=str(uuid.uuid4()),p_expected=d['body']['row_version'])
        one=owner.rpc('erp_cp7_save_supplier_return_v1',postargs);assert one['status']==200,one
        assert owner.rpc('erp_cp7_save_supplier_return_v1',postargs)['body']==one['body']
        readargs=dict(p_purchase=f['receipt']['purchase_id'],p_location=f['location'],p_offset=0,p_limit=25)
        visible=owner.rpc('erp_cp7_get_supplier_returns_v1',readargs);redacted=ops.rpc('erp_cp7_get_supplier_returns_v1',readargs)
        assert visible['status']==200 and redacted['status']==200 and redacted['body']['financial_captured'] is False and '"finance"' not in json.dumps(redacted['body'])
        assert http.anon_rpc('erp_cp7_get_supplier_returns_v1',readargs)['status'] in (401,403,404)
        with http.connect() as conn,conn.cursor() as cur:
            assert amounts(cur,f)==(80,0,8,10);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_save_supplier_return_v1',postargs)['status']==403
        return dict(status='PASS',real_auth_postgrest=True,one_physical_effect=True,ops_value_redacted=True,current_access_before_replay=True)
    return [('P09_RETURN_HTTP_AUTH_REPLAY',flow)]
