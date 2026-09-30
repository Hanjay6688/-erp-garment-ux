"""E20/E14: complete FG pages bind public invoice capacity and current access.

Independent worksheet: thirty actual one-piece lots at10, invoice27 at20.
Draft=physical30/reserved27/available3; posted=3/0/3, COGS270, AR540.
"""
import json
import uuid
from decimal import Decimal as D
import cp7_sales_draft_cases as draft
import cp7_f03_x04_cases as x04

cmd, source, auth, b = draft.cmd, draft.source, draft.auth, draft.b
fg = source.fg


def fixture(cur, today):
    f = draft.fixture(cur, today, 1)
    for i in range(29):
        fg.ax.post(cur, dict(source_kind='FOUND_AT_OPNAME', product_id=f['product'],
            location_id=f['location'], qty_pcs=1, physical_at=f['at'],
            reason='E20 distinct physical lot '+str(i+2), owner_unit_value='10',
            owner_value_reason='E20 exact supplied value10 per one-piece lot'))
    f['lots'] = [r[0] for r in cur.execute('select id::text from erp.fg_lots where product_id=%s order by id', (f['product'],)).fetchall()]
    assert len(f['lots']) == 30
    f['today'] = str(today)
    return f


def observe(cur, f):
    # The native available ledger includes reservation; physical adds only its
    # unreversed SALE_RESERVE. POST changes that source to SALE, no new outflow.
    available, reserved = cur.execute("""select coalesce(sum(m.qty_signed),0),
        coalesce(sum(abs(m.qty_signed)) filter(where m.movement_type='SALE_RESERVE'
        and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)),0)
        from erp.fg_stock_movements m where m.product_id=%s and m.location_id=%s and m.quality_grade='GRADE_A'""",
        (f['product'], f['location'])).fetchone()
    value = cur.execute("""select coalesce(sum(m.qty_signed*h.hpp_per_pcs),0)
        from erp.fg_stock_movements m join erp.v_current_hpp h on h.lot_id=m.lot_id
        where m.product_id=%s and m.location_id=%s and m.quality_grade='GRADE_A'""",
        (f['product'], f['location'])).fetchone()[0]
    found = cur.execute('select id::text from erp.sales_headers where sale_number=%s', (f['tag'],)).fetchone()
    sf = dict(f, sale=found[0]) if found else None
    return dict(qty=[int(available+reserved), int(reserved), int(available)],
        available_value=str(value), accounts={k:str(v) for k,v in cmd.accounts(cur).items()},
        document=source.read(cur, sf)['detail'] if sf else None,
        allocations=cur.execute("""select to_jsonb(a) from erp.sale_stock_allocations a
            join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s order by a.id""",
            (sf['sale'],)).fetchall() if sf else [],
        report=x04.finance.read(cur, f['today'])['snapshot'])


def page_pair(cur, f, subject=None):
    pages = [fg.workspace(cur, f, subject, show_zero=True, offset=o, limit=25) for o in (0,25)]
    assert [len(p['page']['rows']) for p in pages] == [25,5]
    assert [p['page']['next_offset'] for p in pages] == [25,None]
    assert all(p['page']['total']=='30' for p in pages)
    ids = [r['lot_id'] for p in pages for r in p['page']['rows']]
    assert len(set(ids))==30 and set(ids)==set(f['lots'])
    expected = observe(cur,f)['qty']
    assert all(fg.qty(p)==expected for p in pages)
    return pages


def no_money(value):
    if isinstance(value,dict):
        assert not set(value)&{'valuation','unit_cost','value','unit_price','unit_hpp_snapshot','financial'}, value
        for child in value.values(): no_money(child)
    elif isinstance(value,list):
        for child in value: no_money(child)


def assert_posted(cur, f, before):
    after = observe(cur,f)
    assert after['qty']==[3,0,3] and D(after['available_value'])==30
    assert after['document']['status']=='POSTED' and D(after['document']['financial']['gross_total'])==540
    assert len(after['allocations'])==27
    allocations = [r[0] for r in after['allocations']]
    assert len({r['lot_id'] for r in allocations})==27 and all(D(str(r['qty_pcs']))==1 for r in allocations)
    actual = cmd.delta({k:D(v) for k,v in before['accounts'].items()}, cmd.accounts(cur))
    expected = {cmd.mapping(cur,'AR_CUSTOMER'):D(540),cmd.mapping(cur,'SALES_REVENUE'):D(-540),
        cmd.mapping(cur,'FG_INVENTORY'):D(-270),cmd.mapping(cur,'COGS'):D(270)}
    assert actual == expected, (actual,expected)
    for section,key,amount in [('financial_position','customer_ar',540),('financial_position','fg_inventory',-270),
        ('performance','sales_revenue_gl',540),('performance','cogs_gl',270),('performance','gross_profit',270)]:
        assert D(after['report'][section][key])-D(before['report'][section][key])==amount, (section,key)
    return after


def stock_option(cur, f, subject=None):
    options = draft.options(cur,'STOCK',f['sale_at'],subject,q=f['sku'])
    assert options['total']=='1' and len(options['rows'])==1
    row=options['rows'][0]
    assert row['product_id']==f['product'] and row['location_id']==f['location']
    return row


def cases(cur, today):
    def capacity():
        f=fixture(cur,today);before=observe(cur,f);pages=page_pair(cur,f)
        assert before['qty']==[30,0,30] and D(before['available_value'])==300
        assert stock_option(cur,f)['available_qty']=='30'
        boundary=b.boundary.snapshot(cur)
        refused=auth.refused(cur,lambda:draft.create(cur,f,draft.payload(f,'31')),'Insufficient FG stock')
        assert b.boundary.snapshot(cur)==boundary
        created=draft.create(cur,f,draft.payload(f,'27'))
        reserved=observe(cur,f);assert reserved['qty']==[30,27,3] and reserved['accounts']==before['accounts']
        assert stock_option(cur,f)['available_qty']=='3';page_pair(cur,f)
        payload,version=cmd.review(cur,f);key=uuid.uuid4()
        posted=cmd.command(cur,'POST',payload,version,key)
        after=assert_posted(cur,f,before);page_pair(cur,f)
        assert cmd.command(cur,'POST',payload,version,key)==posted
        assert observe(cur,f)['allocations']==after['allocations']
        payload,version=cmd.review(cur,f)
        cmd.command(cur,'SALE_REVERSE',payload,version)
        final=observe(cur,f);assert final['qty']==[30,0,30] and final['accounts']==before['accounts']
        assert D(final['available_value'])==300
        for section in ('financial_position','performance'): assert final['report'][section]==before['report'][section]
        page_pair(cur,f)
        return dict(status='PASS',physical_lots=30,pages=[25,5],not_a_page_subtotal=True,
            invoice_qty=27,reserved=[30,27,3],posted=[3,0,3],AR='540.00',COGS='270.00',
            FG_value='30.00',allocation_lots=27,exact_post_replay=True,public_inverse_restores30_and_accounts=True,
            over_capacity_refused_atomic=refused,first_page_lot_ids=[r['lot_id'] for r in pages[0]['page']['rows']])

    def access():
        f=fixture(cur,today);before=observe(cur,f)
        subject,role=auth.custom_actor(cur)
        cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
        for key in ('warehouse.fg.view','warehouse.stock.view'):
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
        pages=page_pair(cur,f,subject)
        for page in pages: assert page['financial_captured'] is False;no_money(page)
        f['lot']=pages[1]['page']['rows'][-1]['lot_id']
        card=fg.ledger(cur,f,subject,limit=100)
        assert card['financial_captured'] is False and card['balances']['physical_qty']=='1';no_money(card)
        draft.create(cur,f,draft.payload(f,'27'));reserved=observe(cur,f)
        pages=page_pair(cur,f,subject)
        for page in pages: no_money(page)
        payload,version=cmd.review(cur,f)
        auth.refused(cur,lambda:cmd.command(cur,'POST',payload,version,subject=subject),'CP7_SALES_WRITE_DENIED')
        assert observe(cur,f)['accounts']==before['accounts'] and observe(cur,f)['qty']==[30,27,3]
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.fg.view'",(role,))
        auth.refused(cur,lambda:fg.workspace(cur,f,subject,offset=25),'CP7_FG_ACCESS_DENIED')
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.stock.view'",(role,))
        auth.refused(cur,lambda:fg.ledger(cur,f,subject),'CP7_FG_ACCESS_DENIED')
        assert observe(cur,f)['qty']==reserved['qty'] and cmd.accounts(cur)=={k:D(v) for k,v in before['accounts'].items()}
        return dict(status='PASS',both_pages_and_last_page_card_redacted=True,physical_lots=30,
            real_public_draft27_preserved=True,operations_post_refused_before_effect=True,
            current_page_and_card_permission_revocation=True,not_a_planner_gap_engine_claim=True)

    return [('F03_E20_CAPACITY_30_LOTS_TO_27_SALE_INVERSE',capacity),
        ('F03_E14_OPERATIONS_BOTH_PAGES_CARD_AND_WRITE',access)]


def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','capacity-owner');ops=http.login('GUDANG','capacity-operations')
        with http.connect() as conn,conn.cursor() as cur:
            had=b.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
            acl=b.one(cur,"select nspacl::text from pg_namespace where nspname='erp'")
            if not had: cur.execute('grant usage on schema erp to authenticated')
            f=fixture(cur,today);before=observe(cur,f)
            role=b.one(cur,'select role_id from erp.app_users where auth_user_id=%s',ops.auth_user_id)
            cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
            for key in ('warehouse.fg.view','warehouse.stock.view'):
                cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
            b.api.admin(cur)
            if not had: cur.execute('revoke usage on schema erp from authenticated')
            assert b.one(cur,"select nspacl::text from pg_namespace where nspname='erp'")==acl
            conn.commit()
        pages=[]
        for offset in (0,25):
            args=dict(p_query=dict(purpose='SUMMARY',q=f['sku'],offset=offset,limit=25))
            for user in (owner,ops):
                page=user.rpc('erp_cp7_get_fg_v1',args);assert page['status']==200,page
                assert fg.qty(page['body'])==[30,0,30] and page['body']['page']['total']=='30'
                if user is ops: assert page['body']['financial_captured'] is False;no_money(page['body'])
                else: pages.append(page['body'])
        assert [len(p['page']['rows']) for p in pages]==[25,5]
        assert set(r['lot_id'] for p in pages for r in p['page']['rows'])==set(f['lots'])
        card=ops.rpc('erp_cp7_get_fg_ledger_v1',dict(p_query=dict(product_id=f['product'],
            lot_id=pages[1]['page']['rows'][-1]['lot_id'],location_id=f['location'],quality_grade='GRADE_A')))
        assert card['status']==200;no_money(card['body'])
        args=dict(p_action='CREATE',p_payload=draft.payload(f,'27'),p_request=str(uuid.uuid4()),p_expected=None)
        assert http.anon_rpc('erp_cp7_save_sale_v1',args)['status'] in (401,403)
        assert ops.rpc('erp_cp7_save_sale_v1',args)['status'] in (401,403)
        created=owner.rpc('erp_cp7_save_sale_v1',args);assert created['status']==200,created
        assert owner.rpc('erp_cp7_save_sale_v1',args)==created
        with http.connect() as conn,conn.cursor() as cur:
            after=observe(cur,f);assert after['qty']==[30,27,3] and after['accounts']==before['accounts']
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,))
            cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));conn.commit()
        assert owner.rpc('erp_cp7_save_sale_v1',args)['status']==403
        assert ops.rpc('erp_cp7_get_fg_v1',dict(p_query=dict(q=f['sku'],offset=25)))['status']==403
        assert ops.rpc('erp_cp7_get_fg_ledger_v1',dict(p_query=dict(product_id=f['product'],
            lot_id=f['lot'],location_id=f['location'],quality_grade='GRADE_A')))['status']==403
        with http.connect() as conn,conn.cursor() as cur:
            assert observe(cur,f)['qty']==[30,27,3] and cmd.accounts(cur)=={k:D(v) for k,v in before['accounts'].items()};conn.rollback()
        return dict(status='PASS',real_Auth_HTTP=True,pages=[25,5],complete30_lot_capacity=True,
            operations_page_card_and_write_boundaries=True,exact_create27_replay=True,
            deactivated_owner_refused_before_cached_outcome=True,current_ops_revocation=True,
            unchanged_GL=True,fixture_ERP_schema_grant_absent_during_HTTP=True)
    return [('F03_E20_E14_HTTP_COMPLETE_SOURCE_CURRENT_AUTH',flow)]
