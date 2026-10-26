"""Native opening against labelled synthetic legacy price, then current Native price.

Historical price is disposable fixture data, not evidence of a Native historical
price writer. No guard is disabled. All measured report calls happen afterwards.
"""
from datetime import timedelta,datetime,time
from decimal import Decimal,ROUND_HALF_UP
from zoneinfo import ZoneInfo
import uuid
import cp6_bb_probe as bb
import cp6_bf_probe as bf

PRICE=Decimal('20.123456')
CURRENT_PRICE=Decimal('25.99')
PERCENT=Decimal('12.3456')
PCS=10

def seed(cur,today):
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    code='FRP'+uuid.uuid4().hex[:10]
    masters=bb.product_masters()
    masters['MODEL'][0]['model_name']='Finance reader percentage {C}'
    masters['BRAND'][0]['brand_name']='Finance reader percentage {C}'
    bb.production_post(cur,today,masters,code=code,cutover_days=10)
    bb.api.admin(cur)
    pid=cur.execute('select id::text from erp.products where sku=%s',(code+'P',)).fetchone()[0]
    historical_at=datetime.combine(today-timedelta(days=9),time(12),tzinfo=ZoneInfo('Asia/Jakarta'))
    # A new shared SKU cannot be backdated. Seed only the otherwise absent legacy
    # price before it has any stock/financial history or shared membership.
    legacy=cur.execute("insert into erp.product_price_versions(product_id,price,effective_from,change_note) "
        "values(%s,%s,%s,'SYNTHETIC DISPOSABLE legacy price fixture; not Native writer evidence') returning id::text",
        (pid,PRICE,historical_at)).fetchone()[0]
    when=cur.execute('select clock_timestamp()').fetchone()[0]
    group=bf.group(cur,[pid],when,settings=dict(price=str(CURRENT_PRICE),bom=[],work_rates=[],laundry_rates=[]))
    result=bf.save(cur,[group],when)
    versions=cur.execute('select id::text,price,effective_from,effective_to from erp.product_price_versions '
        'where product_id=%s order by effective_from,id',(pid,)).fetchall()
    assert len(versions)==2 and versions[0]==(legacy,PRICE,historical_at,when),versions
    assert versions[1][1:]==(CURRENT_PRICE,when,None),versions
    cutover=today-timedelta(days=8)
    physical=cur.execute('select erp.product_opening_physical_at(%s,%s)',(pid,cutover)).fetchone()[0]
    assert historical_at<=physical<when,('FIXTURE_PRICE_TIME_ORDER',historical_at,physical,when)
    resolved=cur.execute('select erp.resolve_product_price_at(%s,%s),erp.resolve_product_price_at(%s,%s)',
        (pid,physical,pid,when)).fetchone()
    assert resolved==(PRICE,CURRENT_PRICE),resolved
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
        fixture_contract='SYNTHETIC_LEGACY_PRICE_NATIVE_CURRENT_AND_OPENING_V2',
        historical_price_fixture=dict(id=legacy,effective_from=historical_at.isoformat(),synthetic=True,
            direct_insert_rows=1,guards_disabled=False,native_historical_price_writer_credit=False),
        current_price=str(CURRENT_PRICE),current_price_effective_from=when.isoformat(),
        current_price_native_version_id=result['groups'][0]['version_id'],
        opening_physical_at=physical.isoformat(),historical_price_selected_over_current=True,
        direct_business_DML=True,direct_DML_scope='ONE_LEGACY_PRICE_FIXTURE_ROW_BEFORE_MEASUREMENTS',
        actual_Auth_HTTP_credit=False,source_change_race_qualification=False)
