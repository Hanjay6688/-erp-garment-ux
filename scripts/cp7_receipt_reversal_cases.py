"""Receipt inverse: accepted source-time stock/journal writer, public CP7 entry.

Masters and draft payment setup are disposable. Posted effects use ordinary
writers; snapshots and journal balances are observations, not simulated money.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json,threading,time,uuid
import psycopg
import cp7_procurement_cases as receipt
import cp7_material_cases as material
import cp7_invoice_cases as invoice
import cp7_supplier_return_cases as returns
auth,b,bc=receipt.auth,receipt.b,receipt.bc

def version(cur,f):return receipt.workspace(cur,dict(purchase_id=f['receipt']['purchase_id']))['detail']['row_version']

def reverse(cur,f,key=None,expected=None,subject=None,reason='Receipt cancellation after review'):
    return receipt.command(cur,'REVERSE',dict(purchase_id=f['receipt']['purchase_id'],change_reason=reason),key,expected or version(cur,f),subject)

def net_ledger(cur):
    return cur.execute("select coalesce(jsonb_agg(jsonb_build_array(account_id,net::text) order by account_id),'[]'::jsonb) from (select account_id,sum(debit-credit) net from erp.journal_lines group by account_id having sum(debit-credit)<>0) q").fetchone()[0]

def cases(cur,today):
    def conservation(final):
        before=net_ledger(cur)
        f=invoice.fixture(cur,today,'1.123456' if final else '10','3.000001' if final else '10',final)
        v=version(cur,f);result=reverse(cur,f,expected=v)
        assert result['status']=='REVERSED' and result['row_version']!=v
        assert receipt.qty(cur,f)==(0,2),receipt.qty(cur,f)
        assert net_ledger(cur)==before
        w=receipt.workspace(cur,dict(purchase_id=f['receipt']['purchase_id']))
        assert w['detail']['stock_effect']=='REVERSED_RECEIPT' and len(w['detail']['items'])==1
        assert Decimal(w['detail']['items'][0]['qty'])==Decimal('1.123456' if final else '10')
        return dict(status='PASS',direct_final=final,exact_source_qty_preserved=True,remaining_qty=0,two_inverse_movements=True,all_account_balances_restored=True)
    def replay():
        f=invoice.fixture(cur,today);v=version(cur,f);key=str(uuid.uuid4());r=reverse(cur,f,key,v)
        assert reverse(cur,f,key,v)==r
        auth.refused(cur,lambda:reverse(cur,f,key,v,reason='Different intent'),'CP7_PROCUREMENT_REVERSE_REQUEST_CHANGED')
        auth.refused(cur,lambda:reverse(cur,f,expected=v),'STALE_VERSION')
        auth.refused(cur,lambda:reverse(cur,f),'CP7_PROCUREMENT_POSTED_RECEIPT_REQUIRED')
        assert receipt.qty(cur,f)==(0,2)
        assert cur.execute('select count(*) from cp7_procurement.reversals where request_id=%s',(key,)).fetchone()[0]==1
        return dict(status='PASS',identical_request_one_inverse=True,changed_reason_stale_and_new_inverse_refused=True)
    def invoice_return_dependencies():
        before=net_ledger(cur);f=invoice.fixture(cur,today);inv=invoice.finalize(cur,f)
        boundary=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:reverse(cur,f),'Reverse posted supplier invoices')
        assert b.boundary.snapshot(cur)==boundary
        invoice.reverse(cur,f,inv['invoice_id']);d,p=returns.save(cur,f);d=returns.post(cur,f,d)
        boundary=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:reverse(cur,f),'retur supplier POSTED')
        assert b.boundary.snapshot(cur)==boundary
        returns.reverse(cur,f,d);reverse(cur,f)
        assert receipt.qty(cur,f)==(0,4) and net_ledger(cur)==before
        return dict(status='PASS',active_invoice_and_return_block_atomic=True,inverse_after_dependencies_released=True,all_account_balances_restored=True)
    def payment_dependency():
        before=net_ledger(cur);f=invoice.fixture(cur,today,final=True)
        masters=bc.fixture(cur,today,purchase=False,zones=False)
        payment=bc.supplier_payment(cur,f['receipt']['purchase_id'],'20.00',masters['cash'],today)
        bc.internal(cur,'post_supplier_payment',payment);b.api.admin(cur)
        boundary=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:reverse(cur,f),'pembayaran supplier')
        assert b.boundary.snapshot(cur)==boundary
        bc.internal(cur,'reverse_supplier_payment',payment,'Release payment before receipt cancellation');b.api.admin(cur)
        reverse(cur,f);assert receipt.qty(cur,f)==(0,2) and net_ledger(cur)==before
        return dict(status='PASS',active_payment_blocks_atomic=True,payment_inverse_then_receipt_inverse=True,all_account_balances_restored=True)
    def historical_stock():
        before=net_ledger(cur);f=material.fixture(cur,today);d,p=material.draft(cur,f);d=material.post(cur,d)
        boundary=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:reverse(cur,f),'AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY')
        assert b.boundary.snapshot(cur)==boundary and material.balances(cur,f)=={f['location']:6,f['destination']:4}
        material.reverse(cur,d);reverse(cur,f)
        assert receipt.qty(cur,f)[0]==0 and net_ledger(cur)==before
        return dict(status='PASS',source_time_negative_prefix_refused=True,no_partial_stock_or_journal=True,transfer_inverse_then_receipt_inverse=True)
    def access():
        f=invoice.fixture(cur,today);subject,role=receipt.custom(cur,['warehouse.procurement.view','warehouse.procurement.reverse'])
        assert receipt.workspace(cur,subject=subject)['capabilities']['reverse'] is False
        auth.refused(cur,lambda:reverse(cur,f,subject=subject),'CP7_PROCUREMENT_REVERSE_DENIED')
        admin,ar=invoice.admin_actor(cur)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.view'",(ar,))
        w=receipt.workspace(cur,dict(purchase_id=f['receipt']['purchase_id']),admin)
        assert w['capabilities']['reverse'] is True and 'finance' not in w['detail']
        key=str(uuid.uuid4());v=version(cur,f);reverse(cur,f,key,v,admin)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.reverse'",(ar,))
        auth.refused(cur,lambda:reverse(cur,f,key,v,admin),'CP7_PROCUREMENT_REVERSE_DENIED')
        for principal in ('anon','authenticated','service_role','cp7_capture','cp7_procure_read','cp7_material_read','cp7_invoice_read','cp7_return_read'):
            assert not cur.execute("select has_function_privilege(%s,'cp7_procurement.reverse_receipt_locked(uuid,bigint,text)','EXECUTE')",(principal,)).fetchone()[0],principal
        for table in ('material_purchase_headers','material_stock_movements','journal_entries','journal_lines'):
            assert not cur.execute("select has_table_privilege('cp7_procure_write',%s,'SELECT,INSERT,UPDATE,DELETE')",('erp.'+table,)).fetchone()[0],table
        return dict(status='PASS',owner_admin_native_guard_preserved=True,current_permission_before_cached_outcome=True,reverse_without_money_projection=True,private_adapter_not_public=True,command_no_business_select_dml=True)
    return [('P09_RECEIPT_REVERSE_ESTIMATED',lambda:conservation(False)),('P09_RECEIPT_REVERSE_EXACT_FINAL',lambda:conservation(True)),
      ('P09_RECEIPT_REVERSE_REPLAY',replay),('P09_RECEIPT_REVERSE_INVOICE_RETURN',invoice_return_dependencies),('P09_RECEIPT_REVERSE_PAYMENT',payment_dependency),
      ('P09_RECEIPT_REVERSE_HISTORY',historical_stock),('P09_RECEIPT_REVERSE_ACCESS',access)]

def races(tools,today):
    def competing(same):
        with tools.connect() as conn,conn.cursor() as cur:
            f=invoice.fixture(cur,today);v=version(cur,f);conn.commit()
        barrier=threading.Barrier(2);key=str(uuid.uuid4())
        def send():
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait(5)
                try:r=reverse(cur,f,key if same else None,v);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(send);z=pool.submit(send);results=[a.result(20),z.result(20)]
        if same:assert isinstance(results[0],dict) and results[0]==results[1],results
        else:assert sum(isinstance(r,dict) for r in results)==1 and any('STALE_VERSION' in r for r in results if isinstance(r,str)),results
        with tools.connect() as conn,conn.cursor() as cur:assert receipt.qty(cur,f)==(0,2)
        return dict(status='PASS',same_request=same,one_receipt_inverse=True,remaining_qty=0)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f=invoice.fixture(cur,today);v=version(cur,f);admin,role=invoice.admin_actor(cur);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.material_purchase_headers where id=%s for update',(f['receipt']['purchase_id'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:reverse(cur,f,expected=v,subject=admin);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspector,inspector.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()')
                            blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                    assert blocked,'RECEIPT_REVERSE_NOT_WAITING'
                    with tools.connect() as conn,conn.cursor() as cur:
                        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.reverse'",(role,));conn.commit()
                finally:holder.rollback()
                error=future.result(20)
        assert 'CP7_PROCUREMENT_ACCESS_CHANGED' in error,error
        with tools.connect() as conn,conn.cursor() as cur:
            assert receipt.qty(cur,f)==(10,1)
            assert cur.execute('select status from erp.material_purchase_headers where id=%s',(f['receipt']['purchase_id'],)).fetchone()[0]=='POSTED'
            assert cur.execute('select count(*) from cp7_procurement.reversals').fetchone()[0]==0
        return dict(status='PASS',revoke_during_real_receipt_wait=True,no_inverse_or_cached_outcome=True)
    return [('P09_RECEIPT_REVERSE_RACE_SAME',lambda:competing(True)),('P09_RECEIPT_REVERSE_RACE_DIFFERENT',lambda:competing(False)),('P09_RECEIPT_REVERSE_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p09-reverse-owner');ops=http.login('ADMIN','p09-reverse-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=invoice.fixture(cur,today);v=version(cur,f)
            cur.execute("delete from erp.app_role_permissions where role_id=(select id from erp.app_roles where role_code='ADMIN') and permission_key='warehouse.procurement.reverse'");conn.commit()
        args=dict(p_action='REVERSE',p_payload=dict(purchase_id=f['receipt']['purchase_id'],change_reason='Reviewed HTTP inverse'),p_request=str(uuid.uuid4()),p_expected=v)
        assert http.anon_rpc('erp_cp7_save_procurement_v1',args)['status'] in (401,403,404)
        assert ops.rpc('erp_cp7_save_procurement_v1',args)['status']==403
        r=owner.rpc('erp_cp7_save_procurement_v1',args);assert r['status']==200,r
        assert r['body']['status']=='REVERSED' and owner.rpc('erp_cp7_save_procurement_v1',args)['body']==r['body']
        with http.connect() as conn,conn.cursor() as cur:
            assert receipt.qty(cur,f)==(0,2)
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_save_procurement_v1',args)['status']==403
        return dict(status='PASS',real_auth_rpc_inverse=True,one_inverse=True,current_access_before_cached_response=True)
    return [('P09_RECEIPT_REVERSE_HTTP_AUTH',flow)]
