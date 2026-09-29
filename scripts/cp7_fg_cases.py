"""Fixed-quantity P10 read oracles through accepted native stock/sale commands."""
from datetime import timedelta
from decimal import Decimal
import json,uuid
import cp6_ax_probe as ax
import cp7_wip_source_cases as cut
import cp7_snapshot_cases as p02
b=cut.b;base=cut.base

def fixture(cur,today,qty=10):
    product,_=ax.owner_only_model_product(cur)
    at=ax.r1.now(cur)-timedelta(minutes=50)
    posted=ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=base.LOCATION,qty_pcs=qty,physical_at=at.isoformat(),reason='P10 known physical stock oracle',owner_unit_value='10',owner_value_reason='P10 explicit independently supplied value'))
    sku=b.one(cur,'select sku from erp.products where id=%s',product)
    lot=b.one(cur,'select lot_id::text from erp.fg_unsourced_receipts_v1 where id=%s',posted['receipt_id'])
    return dict(product=str(product),lot=lot,sku=sku,location=base.LOCATION,at=at.isoformat(),receipt=posted['receipt_id'])

def workspace(cur,f,subject=None,**query):
    p02.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_fg_v1(%s::jsonb)',(json.dumps(dict({'purpose':'SUMMARY','q':f['sku']},**query)),)).fetchone()[0];b.api.admin(cur);return r

def ledger(cur,f,subject=None,**query):
    p02.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_fg_ledger_v1(%s::jsonb)',(json.dumps(dict(product_id=f['product'],lot_id=f['lot'],location_id=f['location'],quality_grade='GRADE_A',**query)),)).fetchone()[0];b.api.admin(cur);return r

def qty(r):return [int(r['totals'][key]) for key in ('physical_qty','reserved_qty','available_qty')]

def draft(cur,f,amount=4):
    customer=base.create_customer(cur,'P10'+uuid.uuid4().hex[:6])
    return b.chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number='P10-'+uuid.uuid4().hex[:10],customer_id=customer,source_location_id=f['location'],sale_date=(ax.r1.now(cur)-timedelta(minutes=10)).isoformat(),reason='P10 reservation is not physical outflow',items=[dict(product_id=f['product'],qty_pcs=amount,unit_price_snapshot='20',discount_amount=0)]),uuid.uuid4(),None)

def cancel(cur,d):
    b.chain.production.owner(cur);r=cur.execute('select erp.cancel_sale_draft_v2(%s,%s,%s,%s)',(d['sale_id'],'P10 reservation cancelled',uuid.uuid4(),int(d['row_version']))).fetchone()[0];b.api.admin(cur);return r

def post_sale(cur,d):
    b.chain.production.owner(cur);r=cur.execute('select erp.post_sale_v2(%s,%s,%s)',(d['sale_id'],uuid.uuid4(),int(d['row_version']))).fetchone()[0];b.api.admin(cur);return r

def cases(cur,today):
    def actual():
        f=fixture(cur,today);before=b.boundary.snapshot(cur);w=workspace(cur,f);row=w['page']['rows'][0]
        assert qty(w)==[10,0,10] and len(w['page']['rows'])==1 and row['quality']=='KNOWN',w
        assert row['valuation']['state']=='KNOWN' and Decimal(row['valuation']['unit_cost'])==10 and Decimal(row['valuation']['value'])==100,row
        l=ledger(cur,f);assert len(l['page']['rows'])==1 and l['page']['rows'][0]['physical_balance']=='10',l
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',ordinary_found_receipt=True,expected_actual=[10,0,10],unit_cost='10',value='100',reader_no_business_write=True)
    def reservations():
        f=fixture(cur,today);d=draft(cur,f);assert qty(workspace(cur,f))==[10,4,6]
        page=ledger(cur,f,offset=1,limit=1);m=page['page']['rows'][0]
        assert [m['physical_delta'],m['physical_balance'],m['reserved_balance'],m['available_balance']]==['0','10','4','6'],page
        cancel(cur,d);assert qty(workspace(cur,f))==[10,0,10]
        old=ledger(cur,f);assert old['balances']['physical_qty']=='10' and old['page']['rows'][-1]['reserved_balance']=='0'
        d=draft(cur,f);post_sale(cur,d);assert qty(workspace(cur,f))==[6,0,6]
        l=ledger(cur,f);assert l['balances']['physical_qty']=='6' and l['balances']['reserved_qty']=='0'
        return dict(status='PASS',draft=[10,4,6],cancel=[10,0,10],posted=[6,0,6],page_retains_full_prefix=True,post_does_not_deduct_twice=True)
    def zero_and_reverse():
        f=fixture(cur,today);ax.reverse(cur,f['receipt'],'P10 undo unused stock')
        assert workspace(cur,f)['page']['rows']==[]
        w=workspace(cur,f,show_zero=True);assert qty(w)==[0,0,0] and len(w['page']['rows'])==1,w
        l=ledger(cur,f);assert len(l['page']['rows'])==2 and l['page']['rows'][1]['reversal_of_id']==l['page']['rows'][0]['id']
        assert l['page']['rows'][1]['physical_balance']=='0'
        return dict(status='PASS',ordinary_inverse_pair=True,zero_positions_explicit=True)
    def unknown():
        f=cut.fixture(cur,today);sku=b.one(cur,'select sku from erp.products where id=%s',f['product']);w=workspace(cur,dict(sku=sku))
        assert qty(w)==[15,0,15] and w['page']['rows'][0]['valuation']['state']=='UNKNOWN',w
        r=w['page']['rows'][0];v=r['valuation'];assert v['unit_cost'] is None and v['value'] is None
        l=ledger(cur,dict(product=f['product'],lot=r['lot_id'],location=r['location_id']))
        assert all(x['valuation']['state']=='UNKNOWN' and x['valuation']['unit_cost'] is None for x in l['page']['rows']),l
        return dict(status='PASS',ordinary_deferred_laundry_quantity=15,unknown_cost_not_zero=True)
    def access():
        f=fixture(cur,today);subject,role=p02.custom_actor(cur)
        cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'warehouse.fg.view')",(role,))
        w=workspace(cur,f,subject);assert w['financial_captured'] is False and not w['capabilities']['card'] and 'valuation' not in w['page']['rows'][0]
        p02.refused(cur,lambda:ledger(cur,f,subject),'CP7_FG_ACCESS_DENIED')
        p02.refused(cur,lambda:workspace(cur,f,subject,purpose='MOVEMENTS'),'CP7_FG_ACCESS_DENIED')
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'warehouse.stock.view')",(role,));l=ledger(cur,f,subject)
        assert l['financial_captured'] is False and 'valuation' not in l['page']['rows'][0]
        cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));p02.refused(cur,lambda:workspace(cur,f,subject),'CP7_FG_ACCESS_DENIED')
        for who in ('anon','authenticated','service_role'):
            assert not cur.execute("select has_schema_privilege(%s,'cp7_fg','USAGE')",(who,)).fetchone()[0]
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_fg_read',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        return dict(status='PASS',purpose_permissions_separate=True,server_money_redaction=True,current_revocation=True,private_no_business_writes=True)
    def pages():
        f=fixture(cur,today,1)
        for i in range(25):ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=f['product'],location_id=f['location'],qty_pcs=1,physical_at=f['at'],reason='P10 complete page '+str(i),owner_unit_value='10',owner_value_reason='P10 physical count source'))
        a=workspace(cur,f,limit=25);z=workspace(cur,f,limit=25,offset=25)
        assert a['page']['total']==z['page']['total']=='26' and len(a['page']['rows'])==25 and len(z['page']['rows'])==1
        assert a['page']['next_offset']==25 and z['page']['next_offset'] is None and qty(a)==qty(z)==[26,0,26]
        assert len({x['lot_id'] for x in a['page']['rows']+z['page']['rows']})==26
        p02.refused(cur,lambda:workspace(cur,f,limit=101),'CP7_FG_QUERY')
        return dict(status='PASS',ordinary_26_distinct_lots=True,totals_not_page_subtotal=True,complete_pages=True)
    def prefix_filters():
        f=fixture(cur,today);d=draft(cur,f);l=ledger(cur,f,q='SALE_RESERVE')
        assert l['page']['rows'] and all(m['physical_balance']=='10' and m['available_balance']=='6' for m in l['page']['rows']),l
        from_at=(ax.r1.now(cur)-timedelta(minutes=20)).isoformat();l=ledger(cur,f,**{'from':from_at})
        assert len(l['page']['rows'])==1 and l['page']['rows'][0]['physical_balance']=='10' and l['balances']['physical_qty']=='10',l
        cur.execute('update erp.fg_stock_movements set book_order=-1000000000+book_order where lot_id=%s',(f['lot'],))
        assert ledger(cur,f)['balances']==l['balances']
        return dict(status='PASS',search_and_date_do_not_reset_prefix=True,presentation_book_order_not_stock_order=True,administrative_book_order_control=True,signed_presentation_rank_preserved=True)
    return [('P10_FG_'+k,fn) for k,fn in [('NATIVE_SOURCE',actual),('RESERVE_CANCEL_POST',reservations),('INVERSE_ZERO',zero_and_reverse),('DEFERRED_UNKNOWN',unknown),('AUTH_PRIVATE',access),('FULL_PAGES',pages),('FILTERED_PREFIX',prefix_filters)]]

def http_cases(http,today):
    def auth():
        owner=http.login('OWNER','p10-fg-owner')
        with http.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);conn.commit()
        args=dict(p_query=dict(purpose='SUMMARY',q=f['sku'],offset=0,limit=25));r=owner.rpc('erp_cp7_get_fg_v1',args)
        assert r['status']==200 and qty(r['body'])==[10,0,10],r
        l=owner.rpc('erp_cp7_get_fg_ledger_v1',dict(p_query=dict(product_id=f['product'],lot_id=f['lot'],location_id=f['location'],quality_grade='GRADE_A')))
        assert l['status']==200 and l['body']['balances']['physical_qty']=='10',l
        with http.connect() as conn,conn.cursor() as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_get_fg_v1',args)['status']==403
        assert http.anon_rpc('erp_cp7_get_fg_v1',args)['status'] in (401,403)
        return dict(status='PASS',real_auth_http=True,current_revocation=True,quantity=[10,0,10])
    return [('P10_FG_HTTP_CURRENT_AUTH',auth)]
