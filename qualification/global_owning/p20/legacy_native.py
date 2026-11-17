"""P20 transaction oracles previously checked on the exact candidate's SKU replay."""

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal as D
from hashlib import sha256
import json
import re
from uuid import uuid4
from zoneinfo import ZoneInfo

import cp7_sales_draft_cases as drafts
import cp7_finance_analysis_cases as finance
from cp7_credit_correction_de import e_cases as credit

cmd = drafts.cmd
source = cmd.source
LOCATION = 'c8c20000-0000-4000-8000-000000000001'
BASE_MODEL = 'a2000000-0000-4000-8000-000000000001'


def prepare(cur):
    cur.execute("set time zone 'Asia/Jakarta'")
    cur.execute("set lock_timeout='8s'; set statement_timeout='120s'")
    drafts.auth.actor(cur)
    drafts.b.api.admin(cur)
    cur.execute("select set_config('app.change_reason','P20 Global isolated fixture',true)")
    assert cur.execute("select erp.has_permission('sales.invoice.post')").fetchone() == (True,), 'CP7_P20_NATIVE_OWNER_REQUIRED'
    cur.execute("""insert into erp.locations(id,location_code,location_name,location_type)
        values(%s,'P20-FG','P20 Warehouse','FG_WAREHOUSE') on conflict(id) do nothing""", (LOCATION,))
    cur.execute("""insert into erp.product_models(id,model_code,model_name)
        values(%s,'P20-FIXTURE','P20 Control model') on conflict(id) do nothing""", (BASE_MODEL,))


def create_series(cur, number, brand_name, slots, at):
    brand, sku, version = uuid4(), uuid4(), uuid4()
    cur.execute('insert into erp.brands(id,brand_code,brand_name) values(%s,%s,%s)',
                (brand, 'P20-' + brand.hex[:10], brand_name))
    cur.execute("insert into erp.bf_skus_v1(id,brand_id,color_name,model_id,sku) values(%s,%s,'BLACK',%s,%s)",
                (sku, brand, BASE_MODEL, number))
    cur.execute("""insert into erp.bf_sku_versions_v1(id,sku_id,effective_from,reason,request_id,revision,settings)
        values(%s,%s,%s,'P20 series identity fixture',%s,1,'{}')""", (version, sku, at-timedelta(days=2), uuid4()))
    members = []
    for size_code, size in slots:
        product = uuid4()
        cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from)
            values(%s,%s,%s,%s,'BLACK',%s,%s,%s,%s)""",
                    (product, 'P20-PHYSICAL-' + product.hex[:12], BASE_MODEL, brand, size,
                     f'P20 {number} {size_code}', product, at-timedelta(days=2)))
        bom = cur.execute("""insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes)
            values(%s,'P20-EMPTY',%s,true,'Explicit empty BOM') returning id""", (product, at-timedelta(days=2))).fetchone()[0]
        cur.execute('insert into erp.bf_sku_members_v1(product_root,version_id,bom_version_id) values(%s,%s,%s)',
                    (product, version, bom))
        receipt = source.fg.ax.post(cur, dict(source_kind='FOUND_AT_OPNAME', product_id=str(product),
            location_id=LOCATION, qty_pcs=20, physical_at=at.isoformat(), reason='P20 physical count source',
            owner_unit_value='10', owner_value_reason='Synthetic fixture unit value cross-checked in GL'))
        lot = cur.execute('select lot_id from erp.fg_unsourced_receipts_v1 where id=%s', (receipt['receipt_id'],)).fetchone()[0]
        members.append(dict(product=str(product), lot=str(lot), size=size_code))
    return members



def position(cur, member):
    row = cur.execute("""select physical_qty,reserved_qty,available_qty from cp7_fg.positions('',true)
        where lot_id=%s and product_id=%s and location_id=%s and quality_grade='GRADE_A'""",
                      (member['lot'], member['product'], LOCATION)).fetchone()
    return tuple(int(qty) for qty in row)



def positions(cur, members):
    return [position(cur, member) for member in members]



def carry(conn, cur, today):
    pair = credit.fixture.prepare(cur, today)
    start = today-timedelta(days=8)
    query = finance.query(today, **{'from': str(start), 'compare_from': str(start-timedelta(days=9)),
                                   'compare_to': str(start-timedelta(days=1))})
    before = finance.read(cur, query)['cash']
    applied, _, _ = credit.basic.apply(cur, pair, '80.00')
    original = pair['target']['sale']
    before_profile = credit.fixture.retained.profiles(cur, pair)['target']
    assert before_profile['AR'] == '420.00'
    assert finance.read(cur, query)['cash'] == before
    conn.commit()

    stale, version, _ = credit.intent(cur, pair)
    stale['credit_carry_review']['basis_sha256'] = '0' * 64
    refusal = credit.refusal(cur, pair, lambda: credit.note.correct(cur, stale, version), 'CP7_CREDIT_NOTE_CARRY_STALE_REVIEW')
    corrected, payload, version, _, key = credit.post(cur, pair)
    conn.commit()
    after_profile = credit.profile(cur, pair, original, corrected['sale_id'], '550.00', '80.00', '120.00')
    assert finance.read(cur, query)['cash'] == before
    assigned = cur.execute("""select event_id::text,root_sale_id::text,replacement_sale_id::text
        from cp7_credit_note_carry_de.assignments_v1 where replacement_sale_id=%s""", (corrected['sale_id'],)).fetchall()
    assert assigned == [(applied['consumption_event_id'], original, corrected['sale_id'])]
    after = credit.observe(cur, pair)
    assert credit.note.correct(cur, payload, version, key) == corrected
    assert credit.observe(cur, pair) == after
    return dict(status='PASS', before_AR=before_profile['AR'], after_AR=after_profile['AR'],
                replacement_net='550.00', carried_credit='80.00', cash_delta='0.00',
                complete_cash_report_unchanged=True, exact_carry_assignment=True,
                physical_and_HPP_unchanged=True, immutable_original_and_credit_journal=True,
                exact_uuid_replay=True, stale_refusal=refusal,
                original_sale_id=original, replacement_sale_id=corrected['sale_id'], cash_query=query,
                cash_digest=sha256(json.dumps(before, sort_keys=True, separators=(',', ':')).encode()).hexdigest())



def wib_dates(conn, cur, today):
    wib = ZoneInfo('Asia/Jakarta')
    midnight = datetime.combine(today, time(), wib)
    instants = [midnight-timedelta(seconds=1), midnight]
    pair = credit.fixture.prepare(cur, today)
    initial_source = pair['source']['f']
    warehouse_stock_at = midnight-timedelta(hours=5)
    results = []
    cash_docs = []
    posted_cases = []
    for slot, (instant, amount) in enumerate(zip(instants, ('1.25','2.75'))):
        cur.execute("set local time zone 'Asia/Jakarta'")
        target = credit.note.stock(cur,today,10,warehouse_stock_at)
        target['customer'] = initial_source['customer']
        target['sale_at'] = instant.isoformat() if slot == 0 else instant.astimezone(timezone.utc).isoformat()
        credit.note.posted(cur,target,'5','100')
        p = dict(pair,target=target)
        application = credit.basic.payload(p,amount='80.00')
        application['physical_at'] = (midnight+timedelta(minutes=1)).isoformat()
        credit.basic.command(cur,credit.basic.review(cur,application),uuid4())
        intent, version, basis = credit.intent(cur,p)
        cur.execute("set local time zone 'UTC'")
        second_intent, second_version, second_basis = credit.intent(cur,p)
        assert intent['review_token'] == second_intent['review_token'] and version == second_version
        assert basis['basis_sha256'] == second_basis['basis_sha256']
        result, *_ = credit.post(cur,p)
        replacement = result['sale_id']
        posted_cases.append((p,target['sale'],replacement))
        days = cur.execute("""select source_id::text,economic_date::text,transaction_date::text
            from erp.journal_entries where source_type='SALE' and source_id in(%s,%s) and reversal_of_id is null""",
                           (target['sale'],replacement)).fetchall()
        expected_day = instant.date().isoformat()
        assert set(days) == {(target['sale'],expected_day,expected_day),(replacement,expected_day,expected_day)}, days
        cash = credit.note.stock(cur,today,10,warehouse_stock_at)
        cash['sale_at'] = (instant-timedelta(minutes=30)).isoformat()
        cash['bank'] = initial_source['bank']
        credit.note.posted(cur,cash,'1','10')
        pay, pay_version = credit.native.payments.payment_payload(cur,cash,amount)
        pay['payment_date'] = target['sale_at']
        cash_docs.append((cmd.command(cur,'PAYMENT',pay,pay_version)['payment_id'],instant.date(),amount))
        results.append(dict(physical_WIB=instant.isoformat(),physical_UTC=instant.astimezone(timezone.utc).isoformat(),
                            economic_date=expected_day,book_date=expected_day,
                            review_token_and_carry_hash_equal_across_zones=True))
    conn.commit()

    for case, original, replacement in posted_cases:
        actual=credit.profile(cur,case,original,replacement,'550.00','80.00','40.00')
        assert actual['AR']=='470.00'
    for slot, (payment, day, amount) in enumerate(cash_docs):
        query=finance.query(day,entry_q=payment,entry_status='POSTED')
        reads=[]
        for zone in ('Asia/Jakarta','UTC'):
            cur.execute("select set_config('TimeZone',%s,true)", (zone,))
            reads.append(finance.read(cur,query)['cash'])
        assert reads[0] == reads[1] and reads[0]['reconciled']
        rows=reads[0]['entries']['rows']
        assert len(rows)==1 and rows[0]['source_id']==payment
        assert (rows[0]['economic_date'],rows[0]['transaction_date'])==(day.isoformat(),day.isoformat())
        assert D(rows[0]['debit'])==D(amount) and D(rows[0]['credit'])==0
        other_day=cash_docs[1-slot][1]
        other=finance.read(cur,finance.query(other_day,entry_q=payment,entry_status='POSTED'))['cash']
        assert other['entries']['rows']==[] and other['entries']['total']=='0'
        results[slot]['cash_receipt_debit']=amount
    return dict(status='PASS',midnight_sides=results,credit_carried_each='80.00',
                replacement_each_AR='470.00',native_journal_dates_match_public_cash_report=True,
                open_period=True)



def closed_carry(conn, cur, today):
    case = dict(credit.cases(cur,today))['E_CLOSED_ORIGINAL_BOOK_PAIR_REFUSES']
    out = case()
    assert out['actual_refusal']['message'] == 'CP7_CREDIT_NOTE_CARRY_REVIEW_REFUSED'
    return dict(out, closed_original_book_pair_preserved=True)



def cash_pages(conn, cur, today):
    day=today-timedelta(days=1)
    query=finance.query(day,entry_q='P20-PAGE-RECEIPT',entry_status='POSTED',entry_order='LABEL_ASC')
    base={key:D(value) for key,value in finance.read(cur,query)['cash'].items()
          if key in ('opening','closing','debit','credit')}
    assert len(base)==4
    bank=source.bc.bank_account(cur,'P20-PAGE')
    coa=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(bank,)).fetchone()[0])
    cur.execute("""insert into erp.cash_accounts(cash_account_code,cash_account_name,coa_account_id,account_kind,is_active)
        values('P20-PAGE-DUP','P20 inactive account alias',%s,'BANK',false)""",(coa,))

    def book(date, amount, source_type, debit):
        direction, counter = ('debit','credit') if debit else ('credit','debit')
        return str(finance.journal(cur,date,[{'account_id':coa,direction:amount},
            {'mapping_key':'OPENING_EQUITY',counter:amount}],source_type))

    book(day-timedelta(days=1),'100.00','P20-PAGE-OPENING',True)
    incoming=[book(day,str(D(i)+D('.25')),'P20-PAGE-RECEIPT',True) for i in range(1,36)]
    book(day,'8.50','P20-PAGE-OUT',False)
    draft=cur.execute("""insert into erp.journal_entries(journal_number,source_type,source_id,economic_date,transaction_date,description,status)
        values('JRN-999-P20-PAGE-DRAFT','P20-PAGE-RECEIPT',%s,%s,%s,'Unposted cash control','DRAFT') returning id""",(uuid4(),day,day)).fetchone()[0]
    contra=cmd.mapping(cur,'OPENING_EQUITY')
    cur.execute('insert into erp.journal_lines(journal_entry_id,account_id,debit,credit) values(%s,%s,99,0),(%s,%s,0,99)',
                (draft,coa,draft,contra))
    conn.commit()

    source_rows=cur.execute('select id::text,journal_number from erp.journal_entries where id=any(%s::uuid[])',(incoming,)).fetchall()
    def natural(label):
        return tuple(int(part) if part.isnumeric() else part.lower() for part in re.findall(r'[0-9]+|[^0-9]+',label))
    expected_order=[row[0] for row in sorted(source_rows,key=lambda row:natural(row[1]))]
    pages=[finance.read(cur,dict(query,offset=offset))['cash'] for offset in (0,25)]
    for result in pages:
        assert {name:D(result[name])-base[name] for name in ('opening','closing','debit','credit')} == dict(
            opening=D('100.00'),closing=D('730.25'),debit=D('638.75'),credit=D('8.50')) and result['reconciled']
        entries=result['entries']
        assert entries['total']=='35' and D(entries['sums']['debit'])==D('638.75') and D(entries['sums']['credit'])==0
    rows=[row['id'] for result in pages for row in result['entries']['rows']]
    assert rows==expected_order and str(draft) not in rows
    assert [len(result['entries']['rows']) for result in pages]==[25,10]
    assert [result['entries']['next_offset'] for result in pages]==[25,None]
    other=source.bc.bank_account(cur,'P20-PAGE-XFER')
    other_coa=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(other,)).fetchone()[0])
    finance.journal(cur,day,[{'account_id':coa,'credit':'20.00'},{'account_id':other_coa,'debit':'20.00'}],'P20-PAGE-TRANSFER')
    conn.commit()
    after=finance.read(cur,query)['cash']
    assert after['reconciled'] and D(after['closing'])-base['closing']==D('730.25')
    assert D(after['debit'])-base['debit']==D('658.75') and D(after['credit'])-base['credit']==D('28.50')
    assert after['entries']['sums']==pages[0]['entries']['sums']
    return dict(status='PASS',fixture_opening_delta='100.00',receipts='638.75',outflow='8.50',closing_delta='730.25',
                matched_pages=[25,10],draft_99_excluded=True,inactive_alias_not_double_counted=True,
                transfer_debit_and_credit='20.00',post_transfer_closing_delta='730.25',generated_native_labels=True)



def browser_sale_fixture(cur):
    at = source.fg.ax.r1.now(cur) - timedelta(hours=1)
    slots = []
    for index, code in enumerate(('P20-BS', 'P20-BM'), 31):
        size = cur.execute('insert into erp.sizes(size_code,sort_order) values(%s,%s) returning id',
                           (code, index)).fetchone()[0]
        cur.execute('insert into erp.product_model_sizes(model_id,size_id,sort_order) values(%s,%s,%s)',
                    (BASE_MODEL, size, index))
        slots.append((code, size))
    families = [create_series(cur, 'P20-X · Y', 'Z', slots, at), create_series(cur, 'P20-X', 'Y · Z', slots, at)]
    members = [item for group in families for item in group]
    assert positions(cur, members) == [(20, 0, 20)] * 4
    for member in members:
        member['sku'] = cur.execute('select sku from erp.products where id=%s',
                                    (member['product'],)).fetchone()[0]
    tag = 'P20-BROWSER-' + uuid4().hex[:8]
    customer = source.fg.base.create_customer(cur, tag)
    return dict(tag=tag, location=LOCATION, sale_at=(at+timedelta(minutes=15)).isoformat(),
                customer=str(customer), members=members, baseline={key:str(value) for key,value in cmd.accounts(cur).items()})


def reverse_browser_sale(conn, cur, fixture, sale):
    assert cur.execute('select sale_number from erp.sales_headers where id=%s', (sale,)).fetchone() == (fixture['tag'],)
    source.native(cur, 'select erp.reverse_sale(%s,%s)', (sale, 'P20 browser sale inverse control'))
    conn.commit()
    assert positions(cur, fixture['members']) == [(20,0,20)] * 4
    assert cmd.accounts(cur) == {key:D(value) for key,value in fixture['baseline'].items()}
