"""Complete multi-receipt invoice intent; all stock/money use accepted writers."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import copy,json,threading,time,uuid
import psycopg
import cp7_invoice_cases as invoice
import cp7_receipt_reversal_cases as reversal
receipt,auth,b=invoice.receipt,invoice.auth,invoice.b

def payload(f,g):
    p=invoice.payload(f);return dict(purchase_id=f['receipt']['purchase_id'],supplier_id=f['payload']['supplier_id'],
      invoice_number=p['supplier_invoice_number'],invoice_date=p['invoice_date'],received_at=p['received_at'],due_date=p['due_date'],
      change_reason=p['reason'],notes='Two reviewed receipts',lines=[dict(purchase_item_id=x['item'],qty_invoiced=q,unit_price=c,discount_amount='0',notes='Keep source line') for x,q,c in ((f,'4','12.5'),(g,'6','7.5'))])
def save(cur,p,version=None,key=None,subject=None):return invoice.command(cur,'SAVE_DOCUMENT',p,version,key,subject)
def detail(cur,f,ident):return next(d for d in invoice.read(cur,f['receipt']['purchase_id'])['page']['rows'] if d['id']==ident)
def intent(f,g,d):return dict(purchase_id=f['receipt']['purchase_id'],invoice_id=d['invoice_id'],reason='Reviewed complete supplier document',reviewed_purchase_ids=sorted([f['receipt']['purchase_id'],g['receipt']['purchase_id']]))
def action(cur,kind,f,g,d,key=None,subject=None):return invoice.command(cur,kind+'_DOCUMENT',intent(f,g,d),d['row_version'],key,subject)
def sources(cur,f,q='',offset=0,limit=25,subject=None):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_invoice_sources_v1(%s,%s,%s,%s)',(f['receipt']['purchase_id'],q,offset,limit)).fetchone()[0];b.api.admin(cur);return r

def cases(cur,today):
    def lifecycle():
        f,g=invoice.fixture(cur,today),invoice.fixture(cur,today);initial=reversal.net_ledger(cur);p=payload(f,g);d=save(cur,p)
        assert invoice.amounts(cur,f)==(0,100,10,10) and invoice.amounts(cur,g)==(0,100,10,10) and reversal.net_ledger(cur)==initial
        doc=detail(cur,f,d['invoice_id']);assert doc['status']=='DRAFT' and doc['line_count']=='2' and Decimal(doc['document_net_amount'])==95
        p['id']=d['invoice_id'];p['notes']='Edited complete draft';edit=save(cur,p,d['row_version']);assert edit['invoice_id']==d['invoice_id'] and int(edit['row_version'])>int(d['row_version'])
        assert detail(cur,f,d['invoice_id'])['received_at']==doc['received_at'] and reversal.net_ledger(cur)==initial
        one=action(cur,'POST',f,g,edit);assert invoice.amounts(cur,f)==(50,60,10,11) and invoice.amounts(cur,g)==(45,40,10,Decimal('8.5'))
        second=payload(f,g);second['lines'][0].update(qty_invoiced='6',unit_price='10');second['lines'][1].update(qty_invoiced='4',unit_price='10')
        two=action(cur,'POST',f,g,save(cur,second));assert invoice.amounts(cur,f)==(110,0,10,11) and invoice.amounts(cur,g)==(85,0,10,Decimal('8.5'))
        action(cur,'REVERSE',f,g,one);assert invoice.amounts(cur,f)==(60,40,10,10) and invoice.amounts(cur,g)==(40,60,10,10)
        action(cur,'REVERSE',f,g,two);assert invoice.amounts(cur,f)==(0,100,10,10) and invoice.amounts(cur,g)==(0,100,10,10) and reversal.net_ledger(cur)==initial
        return dict(status='PASS',draft_and_edit_no_money=True,first_ap=[50,45],first_grni=[60,40],first_stock_values=[110,85],complete_ap=[110,85],both_inverses_restore_all_accounts=True)
    def replay_delete():
        f,g=invoice.fixture(cur,today),invoice.fixture(cur,today);p=payload(f,g);key=str(uuid.uuid4());d=save(cur,p,key=key);assert save(cur,p,key=key)==d
        bad=copy.deepcopy(p);bad['notes']='Different';auth.refused(cur,lambda:save(cur,bad,key=key),'CP7_INVOICE_REQUEST_CHANGED')
        changed=copy.deepcopy(p);changed['id']=d['invoice_id'];edit=save(cur,changed,d['row_version'])
        auth.refused(cur,lambda:save(cur,changed,d['row_version']),'STALE_VERSION')
        k=str(uuid.uuid4());deleted=action(cur,'DELETE',f,g,edit,k);assert deleted['status']=='DELETED' and deleted['row_version'] is None
        assert action(cur,'DELETE',f,g,edit,k)==deleted and save(cur,p,key=key)==d
        assert not invoice.read(cur,f['receipt']['purchase_id'])['page']['rows'] and invoice.amounts(cur,f)==(0,100,10,10)
        return dict(status='PASS',exact_replay_and_stale_version=True,deleted_draft_old_outcome_recoverable=True,no_stock_or_money_effect=True)
    def atomic():
        f,g=invoice.fixture(cur,today),invoice.fixture(cur,today);p=payload(f,g);before=b.boundary.snapshot(cur)
        bad=copy.deepcopy(p);bad['lines'].append(copy.deepcopy(bad['lines'][0]));auth.refused(cur,lambda:save(cur,bad),'CP7_INVOICE_DUPLICATE_LINE')
        bad=copy.deepcopy(p);bad['lines'][0]['unit_price']=12.5;auth.refused(cur,lambda:save(cur,bad),'CP7_INVOICE_LINE')
        bad=copy.deepcopy(p);bad['supplier_id']=str(uuid.uuid4());auth.refused(cur,lambda:save(cur,bad),'CP7_INVOICE_SAME_SUPPLIER_POSTED_RECEIPTS_REQUIRED')
        assert b.boundary.snapshot(cur)==before
        d=save(cur,p);review=intent(f,g,d);review['reviewed_purchase_ids']=[f['receipt']['purchase_id']];before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:invoice.command(cur,'POST_DOCUMENT',review,d['row_version']),'CP7_INVOICE_COMPLETE_DOCUMENT_REQUIRED');assert b.boundary.snapshot(cur)==before
        posted=action(cur,'POST',f,g,d);review=intent(f,g,posted);review['reviewed_purchase_ids'].append(review['reviewed_purchase_ids'][0]);before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:invoice.command(cur,'REVERSE_DOCUMENT',review,posted['row_version']),'CP7_INVOICE_COMPLETE_DOCUMENT_REQUIRED');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',duplicate_numeric_foreign_supplier_atomic=True,partial_or_duplicate_review_refused=True)
    def pages():
        f,g=invoice.fixture(cur,today),invoice.fixture(cur,today);tag='COMBINED-'+uuid.uuid4().hex[:8]
        # Master setup only for the foreign supplier; its receipt uses public writers.
        supplier=str(cur.execute("insert into erp.suppliers(supplier_code,supplier_name,supplier_type) values(%s,'Combined foreign supplier','MATERIAL') returning id",(tag,)).fetchone()[0])
        foreign=receipt.fixture(cur,today);foreign['payload']['supplier_id']=supplier;foreign['payload']['purchase_number']=tag+'-FOREIGN';receipt.post(cur,receipt.command(cur,'SAVE_DRAFT',foreign['payload']))
        seen=[];offset=0
        while True:
            r=sources(cur,f,offset=offset,limit=1);seen.extend(x['id'] for x in r['page']['rows']);offset=r['page']['next_offset']
            assert all(len(x['lines'])==int(x['line_count']) for x in r['page']['rows'])
            if offset is None:break
        assert f['receipt']['purchase_id'] in seen and g['receipt']['purchase_id'] in seen and len(seen)==len(set(seen))
        assert not sources(cur,f,tag)['page']['rows']
        return dict(status='PASS',complete_paged_same_supplier_receipts=True,foreign_supplier_excluded=True)
    def access():
        f,g=invoice.fixture(cur,today),invoice.fixture(cur,today);p=payload(f,g);ops,role=receipt.custom(cur,('warehouse.procurement.view',))
        auth.refused(cur,lambda:sources(cur,f,subject=ops),'CP7_INVOICE_ACCESS_DENIED')
        cur.execute("insert into erp.app_role_permissions values(%s,'finance.ap.view'),(%s,'warehouse.procurement.post')",(role,role))
        auth.refused(cur,lambda:save(cur,p,subject=ops),'CP7_INVOICE_DOCUMENT_ACTION_DENIED')
        admin,role=invoice.admin_actor(cur);key=str(uuid.uuid4());d=save(cur,p,key=key,subject=admin)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.post'",(role,))
        auth.refused(cur,lambda:save(cur,p,key=key,subject=admin),'CP7_INVOICE_DOCUMENT_ACTION_DENIED')
        for principal in ('authenticated','anon','service_role','cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,'cp7_invoice.assert_document(uuid,uuid,jsonb)','EXECUTE')",(principal,)).fetchone()[0]
        assert not cur.execute("select has_table_privilege('cp7_invoice_write','erp.material_supplier_invoices','SELECT,INSERT,UPDATE,DELETE')").fetchone()[0]
        return dict(status='PASS',current_access_before_cached_outcome=True,legacy_role_and_finance_required=True,no_private_execute_or_business_dml=True)
    def capacity():
        f,g=invoice.fixture(cur,today),invoice.fixture(cur,today,final=True);p=payload(f,g);d=save(cur,p);before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:action(cur,'POST',f,g,d),'already final-invoiced');assert b.boundary.snapshot(cur)==before
        h=invoice.fixture(cur,today);p=payload(f,h);p['lines'][1]['qty_invoiced']='11';d=save(cur,p);before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:action(cur,'POST',f,h,d),'exceed');assert b.boundary.snapshot(cur)==before and invoice.amounts(cur,f)==(0,100,10,10)
        return dict(status='PASS',direct_final_and_overcapacity_preserve_whole_transaction=True)
    return [('P09_COMBINED_INVOICE_LIFECYCLE',lifecycle),('P09_COMBINED_INVOICE_REPLAY_DELETE',replay_delete),('P09_COMBINED_INVOICE_ATOMIC',atomic),
      ('P09_COMBINED_INVOICE_SOURCES',pages),('P09_COMBINED_INVOICE_ACCESS',access),('P09_COMBINED_INVOICE_CAPACITY',capacity)]

def races(tools,today):
    def compete(same):
        with tools.connect() as conn,conn.cursor() as cur:
            f,g=invoice.fixture(cur,today),invoice.fixture(cur,today);p=payload(f,g)
            for line in p['lines']:line.update(qty_invoiced='7',unit_price='10')
            first=save(cur,p);p['invoice_number']+='-TWO';second=first if same else save(cur,p);conn.commit()
        barrier=threading.Barrier(2);key=str(uuid.uuid4())
        def send(d):
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait(5)
                try:r=action(cur,'POST',f,g,d,key if same else None);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(send,d) for d in (first,second)];results=[x.result(30) for x in jobs]
        if same:assert results[0]==results[1] and isinstance(results[0],dict),results
        else:assert sum(isinstance(x,dict) for x in results)==1 and any('exceed' in x for x in results if isinstance(x,str)),results
        with tools.connect() as conn,conn.cursor() as cur:assert invoice.amounts(cur,f)==(70,30,10,10) and invoice.amounts(cur,g)==(70,30,10,10)
        return dict(status='PASS',same_request=same,one_posted_document=True,both_receipts_ap=70,both_receipts_grni=30)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:f,g=invoice.fixture(cur,today),invoice.fixture(cur,today);d=save(cur,payload(f,g));subject,role=invoice.admin_actor(cur);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.material_purchase_headers where id=%s for update',(f['receipt']['purchase_id'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:action(cur,'POST',f,g,d,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                task=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                        assert blocked,'EXPECTED_RECEIPT_ROW_WAIT';c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.post'",(role,))
                finally:holder.rollback()
                result=task.result(30)
        assert 'ACCESS_CHANGED' in result,result
        with tools.connect() as conn,conn.cursor() as cur:assert invoice.amounts(cur,f)==(0,100,10,10) and invoice.amounts(cur,g)==(0,100,10,10)
        return dict(status='PASS',revocation_at_receipt_wait_rolls_back_all_receipts=True)
    return [('P09_COMBINED_INVOICE_RACE_SAME',lambda:compete(True)),('P09_COMBINED_INVOICE_RACE_CAPACITY',lambda:compete(False)),('P09_COMBINED_INVOICE_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p09-combined-owner')
        with http.connect() as conn,conn.cursor() as cur:f,g=invoice.fixture(cur,today),invoice.fixture(cur,today);p=payload(f,g);conn.commit()
        args=dict(p_action='SAVE_DOCUMENT',p_payload=p,p_request=str(uuid.uuid4()),p_expected=None)
        assert http.anon_rpc('erp_cp7_save_purchase_invoice_v1',args)['status'] in(401,403,404)
        saved=owner.rpc('erp_cp7_save_purchase_invoice_v1',args);assert saved['status']==200,saved
        assert owner.rpc('erp_cp7_save_purchase_invoice_v1',args)['body']==saved['body']
        d=saved['body'];args=dict(p_action='POST_DOCUMENT',p_payload=intent(f,g,d),p_request=str(uuid.uuid4()),p_expected=d['row_version'])
        posted=owner.rpc('erp_cp7_save_purchase_invoice_v1',args);assert posted['status']==200,posted
        assert owner.rpc('erp_cp7_save_purchase_invoice_v1',args)['body']==posted['body']
        with http.connect() as conn,conn.cursor() as cur:
            assert invoice.amounts(cur,f)==(50,60,10,11) and invoice.amounts(cur,g)==(45,40,10,Decimal('8.5'));cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_save_purchase_invoice_v1',args)['status']==403
        return dict(status='PASS',real_auth_draft_post_replay=True,current_revocation_before_cache=True,both_receipt_amounts=True)
    return [('P09_COMBINED_INVOICE_HTTP',flow)]
