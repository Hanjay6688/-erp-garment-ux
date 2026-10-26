"""A real Native import and shared SKU price, with exact independent HPP math."""
from datetime import timedelta,datetime,time
from decimal import Decimal,ROUND_HALF_UP
from zoneinfo import ZoneInfo
import uuid
import cp6_bb_probe as bb
import cp6_bf_probe as bf

PRICE=Decimal('20.123456')
PERCENT=Decimal('12.3456')
PCS=10

def seed(cur,today):
    code='FRP'+uuid.uuid4().hex[:10]
    masters=bb.product_masters()
    masters['MODEL'][0]['model_name']='Finance reader percentage {C}'
    masters['BRAND'][0]['brand_name']='Finance reader percentage {C}'
    bb.production_post(cur,today,masters,code=code,cutover_days=10)
    bb.api.admin(cur)
    pid=cur.execute('select id::text from erp.products where sku=%s',(code+'P',)).fetchone()[0]
    when=datetime.combine(today-timedelta(days=9),time(12),tzinfo=ZoneInfo('Asia/Jakarta'))
    group=bf.group(cur,[pid],when,settings=dict(price=str(PRICE),bom=[],work_rates=[],laundry_rates=[]))
    result=bf.save(cur,[group],when)
    hpp=(PRICE*PERCENT/100).quantize(Decimal('.000001'),rounding=ROUND_HALF_UP)
    value=(hpp*PCS).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    rows=dict(OPENING_BALANCE_ITEM=[dict(balance_type='FINISHED_GOODS',product_sku=code+'P',
        brand_code=code,model_code=code,color_name='Blue',size_code=code,location_code=code+'G',
        qty=str(PCS),hpp_input_method='PRICE_PERCENT',hpp_percent_of_price=str(PERCENT),control_key='FG')],
        OPENING_CONTROL=[dict(control_key='FG',balance_type='FINISHED_GOODS',qty=str(PCS),amount=str(value))])
    opening=bb.production_post(cur,today,rows,code=code+'O',cutover_days=8)
    bb.api.admin(cur)
    actual=cur.execute("select i.id::text,i.opening_id::text,i.hpp_input_method,i.hpp_percent_of_price,"
        "i.reference_sell_price_snapshot,i.unit_cost_snapshot,i.qty from erp.opening_balance_items i "
        "join erp.opening_balance_headers h on h.id=i.opening_id where i.product_id=%s and h.status='POSTED'",(pid,)).fetchall()
    assert len(actual)==1 and actual[0][2:]==('PRICE_PERCENT',PERCENT,PRICE,hpp,Decimal(PCS)),actual
    item,header=actual[0][:2]
    movements=cur.execute("select qty_signed,unit_hpp_snapshot from erp.fg_stock_movements "
        "where source_type='OPENING_BALANCE_ITEM'and source_id=%s",(item,)).fetchall()
    assert movements==[(Decimal(PCS),hpp)],movements
    journal=cur.execute("select j.status,sum(l.debit-l.credit),sum(l.debit)from erp.journal_entries j "
        "join erp.journal_lines l on l.journal_entry_id=j.id where j.source_type='OPENING_BALANCE'and j.source_id=%s "
        "group by j.id,j.status",(header,)).fetchall()
    assert journal==[('POSTED',Decimal(0),value)],journal
    return dict(method='PRICE_PERCENT',price=str(PRICE),percentage=str(PERCENT),qty=PCS,
        independently_rounded_unit_hpp=str(hpp),independently_rounded_posted_value=str(value),
        masters_import=code,opening_batch=opening['batch'],opening_item=item,product=pid,
        real_Native_import_and_shared_price_writer=True,posted_stock_and_journal_exact=True,
        direct_business_DML=False,actual_Auth_HTTP_credit=False,source_change_race_qualification=False)
