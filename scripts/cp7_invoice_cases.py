"""P09 supplier invoices through the public CP7 boundary on disposable data.

Amounts are receipt/invoice recognition, never claimed as payment outstanding.
No stock, journal, or invoice posted state is inserted by an administrative actor.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import copy,json,threading,time,uuid
import psycopg
import cp7_procurement_cases as receipt
import cp7_material_cases as material
auth,b,aa=receipt.auth,receipt.b,receipt.aa

def command(cur,action,payload,version,key=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_save_purchase_invoice_v1(%s,%s::jsonb,%s,%s)',
      (action,json.dumps(payload,default=str),key or uuid.uuid4(),version)).fetchone()[0]
    b.api.admin(cur);return r

def read(cur,purchase,offset=0,limit=25,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_purchase_invoices_v1(%s,%s,%s)',(purchase,offset,limit)).fetchone()[0]
    b.api.admin(cur);return r

def fixture(cur,today,qty='10',price='10',final=False):
    f=receipt.fixture(cur,today,qty,price,final);d=receipt.command(cur,'SAVE_DRAFT',f['payload']);f['receipt']=receipt.post(cur,d)
    f['item'],f['roll']=map(str,cur.execute('select i.id,r.id from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id where i.purchase_id=%s',(d['purchase_id'],)).fetchone())
    return f

def payload(f,qty='4',price='12.5',discount='0'):
    return dict(purchase_id=f['receipt']['purchase_id'],supplier_invoice_number=f['tag']+'-INV-'+uuid.uuid4().hex[:6],
      invoice_date=str(f['day']),received_at=aa.at(f['day']+timedelta(days=2),15).isoformat(),due_date=str(f['day']+timedelta(days=14)),
      reason='P09 actual supplier invoice received',notes='Supplier document',
      lines=[dict(purchase_item_id=f['item'],qty_invoiced=qty,final_unit_price=price,discount_amount=discount,notes='Actual invoice line')])

def finalize(cur,f,qty='4',price='12.5',key=None,subject=None,p=None):
    w=read(cur,f['receipt']['purchase_id'],subject=subject)
    p=p or payload(f,qty,price)
    return command(cur,'FINALIZE',p,w['purchase_version'],key,subject)

def reverse(cur,f,ident,key=None,subject=None):
    d=next(x for x in read(cur,f['receipt']['purchase_id'],subject=subject)['page']['rows'] if x['id']==ident)
    return command(cur,'REVERSE',dict(purchase_id=f['receipt']['purchase_id'],invoice_id=ident,reason='P09 supplier invoice correction'),d['row_version'],key,subject)

def amounts(cur,f):
    return cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s),cached_stock_qty,moving_average_cost from erp.materials where id=%s',
      (f['receipt']['purchase_id'],f['receipt']['purchase_id'],f['material'])).fetchone()

def admin_actor(cur):
    subject,_=receipt.custom(cur,[])
    role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
    cur.execute("update erp.app_users set role='ADMIN',role_id=%s where auth_user_id=%s",(role,subject))
    return subject,role

def cases(cur,today):
    def staged():
        f=fixture(cur,today);initial=read(cur,f['receipt']['purchase_id'])
        assert initial['receipt_line_count']=='1' and Decimal(initial['receipt_lines'][0]['remaining_qty'])==10
        one=finalize(cur,f);assert amounts(cur,f)==(50,60,10,11),amounts(cur,f)
        w=read(cur,f['receipt']['purchase_id']);doc=w['page']['rows'][0]
        assert one['version_subject']=='RECEIPT' and one['row_version']==w['purchase_version'] and doc['id']==one['invoice_id']
        assert doc['single_receipt'] and doc['line_count']=='1' and Decimal(doc['document_net_amount'])==50
        assert w['basis']=='INVOICE_DOCUMENTS_NOT_PAYMENT_OUTSTANDING' and Decimal(w['receipt_lines'][0]['remaining_qty'])==6
        two=finalize(cur,f,'6','7.5');assert amounts(cur,f)==(95,0,10,Decimal('9.5')),amounts(cur,f)
        rev=reverse(cur,f,two['invoice_id']);assert rev['version_subject']=='INVOICE' and rev['status']=='REVERSED' and amounts(cur,f)==(50,60,10,11)
        reverse(cur,f,one['invoice_id']);assert amounts(cur,f)==(0,100,10,10)
        return dict(status='PASS',staged_ap=[50,95],staged_grni=[60,0],staged_material_value=[110,95],reversal_value=[110,100],stock_qty_always=10)
    def exact():
        f=fixture(cur,today,'1.123456','3.000001');r=finalize(cur,f,'1.123456','3.000001')
        w=read(cur,f['receipt']['purchase_id']);l=w['page']['rows'][0]['lines'][0]
        assert l['qty']=='1.123456' and l['unit_price']=='3.000001' and Decimal(l['net_amount'])==Decimal('3.370369')
        assert amounts(cur,f)[:3]==(Decimal('3.37'),0,Decimal('1.123456')),amounts(cur,f)
        reverse(cur,f,r['invoice_id']);assert amounts(cur,f)[0]==0
        return dict(status='PASS',exact_qty='1.123456',exact_price='3.000001',document_net='3.370369',recognized_ap='3.37',reversal_ap=0)
    def discounted():
        f=fixture(cur,today);p=payload(f,discount='2.25');d=finalize(cur,f,p=p)
        w=read(cur,f['receipt']['purchase_id']);assert Decimal(w['page']['rows'][0]['document_net_amount'])==Decimal('47.75')
        assert amounts(cur,f)==(Decimal('47.75'),60,10,Decimal('10.775')),amounts(cur,f)
        reverse(cur,f,d['invoice_id']);assert amounts(cur,f)==(0,100,10,10)
        return dict(status='PASS',line_discount='2.25',document_net='47.75',recognized_ap='47.75',stock_value='107.75')
    def replay():
        f=fixture(cur,today);p=payload(f);v=read(cur,f['receipt']['purchase_id'])['purchase_version'];key=str(uuid.uuid4())
        one=command(cur,'FINALIZE',p,v,key);two=finalize(cur,f,'6','7.5')
        assert command(cur,'FINALIZE',p,v,key)==one
        assert read(cur,f['receipt']['purchase_id'])['purchase_version']!=one['row_version']
        changed=copy.deepcopy(p);changed['notes']='Different intent'
        auth.refused(cur,lambda:command(cur,'FINALIZE',changed,v,key),'different payload')
        auth.refused(cur,lambda:command(cur,'FINALIZE',p,v),'STALE_VERSION')
        key2=str(uuid.uuid4());doc=next(d for d in read(cur,f['receipt']['purchase_id'])['page']['rows'] if d['id']==two['invoice_id'])
        rp=dict(purchase_id=f['receipt']['purchase_id'],invoice_id=two['invoice_id'],reason='P09 supplier invoice correction')
        r=command(cur,'REVERSE',rp,doc['row_version'],key2);assert command(cur,'REVERSE',rp,doc['row_version'],key2)==r
        assert amounts(cur,f)==(50,60,10,11)
        assert read(cur,f['receipt']['purchase_id'])['page']['total']=='2'
        return dict(status='PASS',old_replay_is_outcome_not_current_read=True,payload_mismatch_refused=True,stale_refused=True,one_invoice_per_request=True)
    def atomic():
        f=fixture(cur,today);g=fixture(cur,today);v=read(cur,f['receipt']['purchase_id'])['purchase_version']
        before=b.boundary.snapshot(cur)
        p=payload(f,'11');auth.refused(cur,lambda:command(cur,'FINALIZE',p,v),'exceed')
        p=payload(f);p['lines'][0]['purchase_item_id']=g['item'];auth.refused(cur,lambda:command(cur,'FINALIZE',p,v),'does not belong')
        p=payload(f);p['lines'][0]['qty_invoiced']=4;auth.refused(cur,lambda:command(cur,'FINALIZE',p,v),'CP7_INVOICE_LINE')
        p=payload(f);p['received_at']=None;auth.refused(cur,lambda:command(cur,'FINALIZE',p,v),'CP7_INVOICE_FIELDS')
        assert b.boundary.snapshot(cur)==before and read(cur,f['receipt']['purchase_id'])['page']['total']=='0'
        direct=fixture(cur,today,final=True);assert read(cur,direct['receipt']['purchase_id'])['receipt_lines'][0]['remaining_qty']=='0'
        auth.refused(cur,lambda:finalize(cur,direct),'already final-invoiced')
        return dict(status='PASS',overcapacity_foreign_line_numeric_transport_null_time_atomic=True,direct_final_not_invoiced_twice=True)
    def access():
        f=fixture(cur,today);p=payload(f);v=f['receipt']['row_version']
        subject,role=receipt.custom(cur,['warehouse.procurement.view'])
        auth.refused(cur,lambda:read(cur,f['receipt']['purchase_id'],subject=subject),'CP7_INVOICE_ACCESS_DENIED')
        cur.execute("insert into erp.app_role_permissions values(%s,'finance.ap.view'),(%s,'warehouse.procurement.post'),(%s,'warehouse.procurement.reverse')",(role,role,role))
        assert read(cur,f['receipt']['purchase_id'],subject=subject)['capabilities']==dict(finalize=False,reverse=False)
        auth.refused(cur,lambda:command(cur,'FINALIZE',p,v,subject=subject),'CP7_INVOICE_FINALIZE_DENIED')
        admin,ar=admin_actor(cur);w=read(cur,f['receipt']['purchase_id'],subject=admin);assert w['capabilities']['finalize']
        d=command(cur,'FINALIZE',p,v,subject=admin)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.reverse'",(ar,))
        auth.refused(cur,lambda:reverse(cur,f,d['invoice_id'],subject=admin),'CP7_INVOICE_REVERSE_DENIED')
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(admin,))
        auth.refused(cur,lambda:read(cur,f['receipt']['purchase_id'],subject=admin),'CP7_INVOICE_ACCESS_DENIED')
        for principal in ('cp7_capture','cp7_invoice_read','cp7_procure_read'):
            assert not cur.execute("select has_function_privilege(%s,'public.erp_cp7_save_purchase_invoice_v1(text,jsonb,uuid,text)','EXECUTE')",(principal,)).fetchone()[0]
        assert not cur.execute("select has_table_privilege('cp7_invoice_write','erp.material_supplier_invoices','SELECT,INSERT,UPDATE,DELETE')").fetchone()[0]
        return dict(status='PASS',ops_no_money=True,custom_role_legacy_guard_preserved=True,current_grant_revoke=True,principals_no_dml=True)
    def multi_receipt():
        f=fixture(cur,today);g=fixture(cur,today)
        auth.actor(cur)
        p=dict(invoice_number=f['tag']+'-MULTI',supplier_id=str(aa.prior.BASE_SUPPLIER),invoice_date=str(f['day']),received_at=aa.at(f['day']+timedelta(days=2),15).isoformat(),change_reason='P09 complete legacy invoice',
          lines=[dict(purchase_item_id=x['item'],qty_invoiced='2',unit_price='12.5',discount_amount='0') for x in (f,g)])
        d=cur.execute('select erp.save_material_supplier_invoice_draft_v2(%s::jsonb,%s,null)',(json.dumps(p),uuid.uuid4())).fetchone()[0]
        cur.execute('select erp.post_material_supplier_invoice_v2(%s,%s,%s)',(d['supplier_invoice_id'],uuid.uuid4(),d['row_version']))
        b.api.admin(cur);w=read(cur,f['receipt']['purchase_id']);doc=w['page']['rows'][0]
        assert not doc['single_receipt'] and doc['line_count']=='2' and len(doc['lines'])==2 and Decimal(doc['document_net_amount'])==50
        assert {x['purchase_id'] for x in doc['lines']}=={f['receipt']['purchase_id'],g['receipt']['purchase_id']}
        auth.refused(cur,lambda:reverse(cur,f,doc['id']),'CP7_INVOICE_COMPLETE_DOCUMENT_REQUIRED')
        assert amounts(cur,f)==(25,80,10,Decimal('10.5')) and amounts(cur,g)==(25,80,10,Decimal('10.5'))
        return dict(status='PASS',multi_receipt_document_fully_read=True,bounded_reverse_refuses_unseen_receipt=True)
    def pages():
        f=fixture(cur,today,'30')
        for _ in range(27):finalize(cur,f,'1','10')
        seen=[];offset=0
        while True:
            w=read(cur,f['receipt']['purchase_id'],offset,10);assert w['page']['total']=='27';seen.extend(d['id'] for d in w['page']['rows']);offset=w['page']['next_offset']
            if offset is None:break
        assert len(seen)==len(set(seen))==27 and Decimal(w['receipt_lines'][0]['remaining_qty'])==3
        return dict(status='PASS',server_paged_invoices=27,complete_unique_documents=True,remaining_qty=3)
    def transferred():
        f=material.fixture(cur,today);f['item']=str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(f['receipt']['purchase_id'],)).fetchone()[0])
        d,_=material.draft(cur,f);d=material.post(cur,d);i=finalize(cur,f,'10','12.5')
        assert material.balances(cur,f)=={f['location']:6,f['destination']:4}
        assert sum(Decimal(r['valuation']['value']) for r in material.stock(cur,f)['page']['rows'])==125
        reverse(cur,f,i['invoice_id']);assert material.balances(cur,f)=={f['location']:6,f['destination']:4}
        assert sum(Decimal(r['valuation']['value']) for r in material.stock(cur,f)['page']['rows'])==100
        return dict(status='PASS',stock_locations_unchanged=True,before_qty=[6,4],invoice_total_value=125,reversed_total_value=100)
    return [('P09_INVOICE_STAGED_AND_REVERSE',staged),('P09_INVOICE_EXACT_DECIMAL',exact),('P09_INVOICE_DISCOUNT',discounted),
      ('P09_INVOICE_REPLAY_STALE',replay),('P09_INVOICE_ATOMIC_REFUSALS',atomic),('P09_INVOICE_ACCESS_PRINCIPALS',access),
      ('P09_INVOICE_COMPLETE_MULTI_RECEIPT',multi_receipt),('P09_INVOICE_COMPLETE_PAGES',pages),('P09_INVOICE_AFTER_TRANSFER',transferred)]

def races(tools,today):
    def competing(same):
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);p=payload(f);v=f['receipt']['row_version'];conn.commit()
        barrier=threading.Barrier(2);key=str(uuid.uuid4())
        def send():
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait(5)
                try:r=command(cur,'FINALIZE',p,v,key if same else None);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(send);z=pool.submit(send);results=[a.result(30),z.result(30)]
        if same:assert results[0]==results[1] and isinstance(results[0],dict),results
        else:assert sum(isinstance(r,dict) for r in results)==1 and any('STALE_VERSION' in r for r in results if isinstance(r,str)),results
        with tools.connect() as conn,conn.cursor() as cur:
            assert amounts(cur,f)==(50,60,10,11) and read(cur,f['receipt']['purchase_id'])['page']['total']=='1'
        return dict(status='PASS',same_request=same,recognized_ap=50,one_invoice_effect=True)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);p=payload(f);v=f['receipt']['row_version'];subject,role=admin_actor(cur);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.material_purchase_headers where id=%s for update',(f['receipt']['purchase_id'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:command(cur,'FINALIZE',p,v,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
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
                        assert blocked,'EXPECTED_REAL_RECEIPT_ROW_WAIT'
                        c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.post'",(role,))
                finally:holder.rollback()
                result=future.result(30)
        assert 'CP7_INVOICE_ACCESS_CHANGED' in result,result
        with tools.connect() as conn,conn.cursor() as cur:
            assert amounts(cur,f)==(0,100,10,10) and read(cur,f['receipt']['purchase_id'])['page']['total']=='0'
        return dict(status='PASS',current_revoke_after_real_row_wait=True,whole_invoice_and_journal_rolled_back=True)
    return [('P09_INVOICE_RACE_SAME_REQUEST',lambda:competing(True)),('P09_INVOICE_RACE_COMPETING',lambda:competing(False)),('P09_INVOICE_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p09-invoice-owner');ops=http.login('ADMIN','p09-invoice-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);p=payload(f);v=f['receipt']['row_version']
            cur.execute("delete from erp.app_role_permissions where role_id=(select id from erp.app_roles where role_code='ADMIN') and permission_key='finance.ap.view'");conn.commit()
        readargs=dict(p_purchase=f['receipt']['purchase_id'],p_offset=0,p_limit=25)
        args=dict(p_action='FINALIZE',p_payload=p,p_request=str(uuid.uuid4()),p_expected=v)
        assert http.anon_rpc('erp_cp7_get_purchase_invoices_v1',readargs)['status'] in(401,403,404)
        assert ops.rpc('erp_cp7_get_purchase_invoices_v1',readargs)['status']==403
        assert ops.rpc('erp_cp7_save_purchase_invoice_v1',args)['status']==403
        posted=owner.rpc('erp_cp7_save_purchase_invoice_v1',args);assert posted['status']==200,posted
        assert owner.rpc('erp_cp7_save_purchase_invoice_v1',args)['body']==posted['body']
        docs=owner.rpc('erp_cp7_get_purchase_invoices_v1',readargs);assert docs['status']==200 and docs['body']['page']['total']=='1',docs
        with http.connect() as conn,conn.cursor() as cur:
            assert amounts(cur,f)==(50,60,10,11)
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_save_purchase_invoice_v1',args)['status']==403
        return dict(status='PASS',real_auth_postgrest=True,ops_no_invoice_money=True,post_replay_revoke=True)
    return [('P09_INVOICE_HTTP_AUTH_REPLAY',flow)]
