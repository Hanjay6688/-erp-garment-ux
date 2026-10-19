"""Copied fixture preparation only from frozen writer r5; oracle is Astra. No writer expected/result is reused."""

from datetime import timedelta
import uuid,json
import cp6_bd_probe as bd
import cp6_be_pocket_probe as pocket

def reader_fixtures(cur,today):
        """Rows the CP17 books lack for three readers, built inside the caller's savepoint (BB and BE probe paths)."""
        bbp=bd.bbp
        fx=bbp.financial_fixture(cur,today,documents=[('CUSTOMER_RECEIVABLE','R5-CA','100.00','30.00'),('SUPPLIER_PAYABLE','R5-SA','100.00','30.00'),
                                                      ('VENDOR_PAYABLE','R5-VA','100.00','30.00')],credits=[('R5-RC','25.00','0.00')])
        effective=str(fx['cutover']+timedelta(days=2))
        for number,kind in (('R5-CA','CUSTOMER_ALLOWANCE'),('R5-SA','SUPPLIER_ALLOWANCE'),('R5-VA','VENDOR_ALLOWANCE')):
            bbp.act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='CREDIT',balance_id=fx['balances'][number],amount='10.00',effective_date=effective,
                    credit_kind=kind,credit_note_number='CN-'+number+'-'+fx['code'],reason='CP17 R5-02 reader input')
        credit=bbp.ws(cur,fx['batch'])['customer_credits'][0]
        bbp.act(cur,'CUSTOMER_CREDIT',fx['batch'],operation='APPLY_OPENING_AR',credit_id=credit['credit_id'],balance_id=fx['balances']['R5-CA'],
                amount='20.00',effective_date=effective,reason='CP17 R5-02 reader input')
        cut=today-timedelta(days=10)
        f=bbp.production_post(cur,today,pocket.active_unit(cur,pocket.rows(cut)))
        p=pocket.preview(cur,cut-timedelta(days=1),cut)
        pool=pocket.call(cur,'POST_PERIOD',dict(period_start=p['period_start'],period_end=p['period_end'],expected_revision=p['revision'],
                                                reason='CP17 R5-02 reader input'))['id']
        lot,product,location=bd.q(cur,"""select m.lot_id::text,l.product_id::text,m.location_id::text from erp.be_pocket_sewing_v1 s
            join erp.fg_stock_movements m on m.source_type='OPENING_BALANCE_ITEM' and m.source_id=s.opening_item_id and m.movement_type='OPENING'
            join erp.fg_lots l on l.id=m.lot_id where s.batch_id=%s and s.target_kind='FINISHED_GOODS'""",f['batch'])[0]
        customer=bd.chain.base.create_customer(cur,'R5-02-'+uuid.uuid4().hex[:8]);bd.chain.production.owner(cur)
        made=bd.one(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s::uuid,null)',json.dumps(dict(sale_number='R5-02-'+uuid.uuid4().hex[:10],
            customer_id=customer,source_location_id=location,sale_date=bd.iso(bd.chain.production.at(cut+timedelta(days=1),17)),
            reason='CP17 R5-02 reader input',items=[dict(product_id=product,qty_pcs=1,unit_price_snapshot='20000',discount_amount=0)])),str(uuid.uuid4()))
        sale=made['sale_id'];version=bd.one(cur,'select row_version from erp.sales_headers where id=%s',sale)
        bd.chain.production.owner(cur);cur.execute('select erp.post_sale_v2(%s,%s,%s)',(sale,uuid.uuid4(),version));bd.api.admin(cur)
        sale_return=pocket.return_sale(cur,sale,cut+timedelta(days=3));bd.api.admin(cur)
        return dict(opening_batch=str(fx['batch']),pocket_period=str(pool),sale=str(sale),sale_return=str(sale_return))

def reader_inputs(cur,today):
        bd.api.admin(cur)
        ids=lambda sql:[(r[0],) for r in cur.execute(sql).fetchall()]
        windows=[(today-timedelta(days=d),today,today) for d in (0,30,400)]
        return {
            'erp.bb_opening_credit_account_v1(uuid)':ids('select settlement_id from erp.bb_opening_credits_v1'
                ' union select id from(select id from erp.opening_subledger_settlements order by id limit 20)s order by 1 limit 300'),
            'erp.compute_non_po_product_hpp_book_v2620f(uuid)':ids('select id from erp.products order by id limit 300'),
            'erp.compute_po_hpp_gl_book_v2620e(uuid)':ids('select id from erp.production_orders order by id limit 300'),
            'erp.get_owner_financial_snapshot_v2(date,date,date)':windows,
            'erp.pocket_period_book_v1(uuid)':ids('select id from erp.pocket_periods order by id limit 300'),
            # Every Sale lifecycle journal with each PO on its lines and two other POs (the reader answers 0 or null for those).
            'erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)':[tuple(r) for r in cur.execute(
                """select distinct e.id,x.po_id from erp.journal_entries e left join erp.journal_entries o on o.id=e.reversal_of_id
                   cross join lateral(select l.po_id from erp.journal_lines l where l.journal_entry_id=e.id and l.po_id is not null
                     union select id from(select id from erp.production_orders order by id limit 2)p) x(po_id)
                   where e.source_type in('SALE','SALES_RETURN') or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
                   order by 1,2 limit 300""").fetchall()]}
