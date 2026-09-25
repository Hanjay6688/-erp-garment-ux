"""BB T1_FAMILY probe: the open cutover states of ALL (owner decision 25 Sep 2026, every ALL state built and tested in CP6),
before and after, starting with the financial part (ALL-P02/S01/S03/A03/Y01 and the opening settlement facade).

Label T1_FAMILY: targeted family evidence on the disposable chain AN -> AU -> AV -> AW..AZ -> BA (+ BB in phase 'after'),
never release evidence. Oracles come from the contract and the auditor's ALL binding (out/gpt_all_round8_binding.md,
audit branch a96bcaa: "Import invoice 100 less historical receipts 30; collect 25 and reverse; reconcile AR 70 to 45 to 70
with no duplicated revenue/stock", "Original invoice 100, historically paid 35: import 65 only; settle 20 and inverse; prove
payable 45 then 65 without historical receipt/invoice/cash journals", "Recognized old wages 80 plus reimburse 20, paid 40:
open/pay remaining 60 with no second wage/reimburse accrual", "historical settled amounts produce no cash event", "Separate
two fixtures: pending physical return from old invoice; already-received return with unpaid refund"), never from observed
behaviour. Outcomes:
  NO_ROUTE       phase 'before' only: the state has no adapter before BB; the request is refused by the router or the stager
                 as unknown (the gap of the handoff §29.6 inventory), nothing changes.
  COUNTEREXAMPLE phase 'before' only: a defect BB fixes shows its harm (a settlement dated before cutover or in the
                 future, a dated negative balance).
  PASS / FAIL    the oracle holds / does not hold. A refusal with another code, or a wrong NO_ROUTE, is INCOMPLETE.
Each case runs inside the group's rolled-back savepoint; nothing is committed to the clone.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,traceback,uuid
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_ay_probe as ayp
import cp6_az_probe as azp
import cp6_ba_probe as bap
import cp6_bb_build as bb
import cp6_run_identity as run_identity
import cp6_initial_import_receipt_trial as receipt_trial
r1,api,boundary,prior,chain=awp.r1,awp.api,awp.boundary,awp.prior,awp.chain

OUT=AUDITOR/'cp6-proof/bb'
BB_SQL=AUDITOR/'supabase/dev/cp6_bb_t1_family.sql'
LABEL='T1_FAMILY'
D=Decimal
NO_ROUTE_MESSAGES=('Aksi impor tidak dikenal','Jenis file impor tidak didukung','Unsupported migration entity_type',
                   'nama kolom atau tipe data tidak valid')


def dev_source(signature):
    """The body of one BB function exactly as the committed dev file defines it (the last definition wins)."""
    name=signature.split('(')[0]
    text=BB_SQL.read_text()
    heads=[m.start() for m in re.finditer(r'(?i)create or replace function '+re.escape(name)+r'\(',text)]
    assert heads,('BB_T1_FUNCTION_NOT_IN_DEV_FILE',signature)
    start=re.compile(r'(?i)\bas \$function\$').search(text,heads[-1]).end();end=text.index('$function$',start)
    return text[start:end]


def bb_installed(cur):
    return cur.execute('select count(*) from erp.schema_migrations where version=%s',(bb.VERSION,)).fetchone()[0]==1


def bb_functions():
    return tuple(bb.REPLACED)+tuple(dict.fromkeys(bb.new_functions()))


def bb_verified(cur):
    base=bap.ba_verified(cur)
    assert bb_installed(cur),'BB_T1_MARKER'
    for name in bb_functions():
        rows=cur.execute("select p.oid::regprocedure::text,p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.proname=%s",
                         tuple(name.split('(')[0].split('.'))).fetchall()
        assert len(rows)==1,('BB_T1_FUNCTION_NOT_UNIQUE',name,[r[0] for r in rows])
        assert rows[0][1]==dev_source(name),('BB_T1_FUNCTION_NOT_CURRENT',name)
    for table in bb.NEW_TABLES:
        assert cur.execute('select to_regclass(%s) is not null',('erp.'+table,)).fetchone()[0],('BB_T1_TABLE_MISSING',table)
    return dict(base,stage='AV_PLUS_AW_AX_AY_AZ_BA_BB_T1',bb_sql_sha256=hashlib.sha256(BB_SQL.read_bytes()).hexdigest(),
                bb_functions=list(bb_functions()))


def install_bb():
    with psycopg.connect(boundary.PG,autocommit=True) as conn,conn.cursor() as cur:cur.execute(BB_SQL.read_text(),prepare=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        result=bb_verified(cur);conn.rollback()
    return result


# ---------------------------------------------------------------- outcome rules

code_of=bap.code_of


def no_route(cur,operation,**evidence):
    """Phase 'before' of a new adapter: the first request must be refused as unknown, atomically."""
    result,error=r1.peer.attempt(cur,operation)
    message=(error or {}).get('message') or ''
    status='NO_ROUTE' if error is not None and any(m in message for m in NO_ROUTE_MESSAGES) else 'INCOMPLETE'
    return dict(evidence,status=status,refusal=error,result=result)


def refused(cur,operation,code):
    """A refusal after BB: must carry the exact code (r1.peer.attempt proves it changed nothing)."""
    result,error=r1.peer.attempt(cur,operation)
    return dict(code=code,refusal=error,result=result,ok=error is not None and code_of(error)==code)


def verdict(checks,**evidence):
    """After BB: every oracle check holds (PASS) or one does not (FAIL)."""
    failed=[k for k,v in checks.items() if v is not True]
    return dict(evidence,checks=checks,failed=failed,status='PASS' if not failed else 'FAIL')


def gl(cur):
    return bap.gl(cur)


def moved(before,after):
    return bap.moved(before,after)


def account(cur,mapping):
    api.admin(cur);return str(cur.execute('select erp.account_id(%s)',(mapping,)).fetchone()[0])


def journal_types(cur,since):
    api.admin(cur)
    return sorted({r[0] for r in cur.execute('select source_type from erp.journal_entries where created_at>=%s',(since,)).fetchall()})


def now(cur):
    return cur.execute('select clock_timestamp()').fetchone()[0]


def revision(cur,batch):
    return api.read(cur,batch)['batch']['revision']


def act(cur,action,batch,key=None,**payload):
    """One BB action through the public import RPC with the batch's current revision."""
    return api.call(cur,action,dict(batch_id=batch,expected_revision=revision(cur,batch),**payload),key)


def ws(cur,batch):
    return api.read(cur,batch)['batch']


# ---------------------------------------------------------------- fixture: one posted import with the financial states

def post_batch(cur,today,rows,cutover_days=10,prefix='BB'):
    """Create, upload, validate and finalize one import; returns (batch, code, cutover). Rows is {entity: [payloads]}; the
    string {C} in any value is replaced by the batch code."""
    cutover=today-timedelta(days=cutover_days)
    boundary.historical.prior.set_open_period(cur,cutover-timedelta(days=1))
    code=prefix+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(cutover)))['batch_id']
    fill=lambda v:v.replace('{C}',code) if isinstance(v,str) else v
    for entity,payloads in rows.items():
        api.upload(cur,batch,entity,[{k:fill(v) for k,v in p.items()} for p in payloads])
    checked=api.invoke(cur,'VALIDATE',batch)
    if checked.get('error_rows')!=0:
        api.admin(cur)
        errors=cur.execute("select entity_type,validation_errors::text from erp.migration_staging_rows where batch_id=%s and validation_status='ERROR'",(batch,)).fetchall()
        raise AssertionError(('BB_FIXTURE_REFUSED',checked,errors))
    posted=api.invoke(cur,'FINALIZE',batch)
    assert posted.get('status')=='POSTED',('BB_FIXTURE_NOT_POSTED',posted)
    return batch,code,cutover


def masters(**extra):
    rows={'CHART_ACCOUNT':[dict(account_code='{C}B',account_name='BB bank',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT'),
                           dict(account_code='{C}K',account_name='BB kredit pelanggan',account_type='LIABILITY',report_group='CURRENT_LIABILITIES',normal_balance='CREDIT')],
          'CASH_ACCOUNT':[dict(cash_account_code='{C}',cash_account_name='BB bank',coa_account_code='{C}B',account_kind='BANK')],
          'CUSTOMER':[dict(customer_code='{C}',customer_name='BB pelanggan')],
          'SUPPLIER':[dict(supplier_code='{C}',supplier_name='BB supplier',supplier_type='MATERIAL')],
          'LAUNDRY_VENDOR':[dict(vendor_code='{C}',vendor_name='BB laundry')],
          'CONTRACTOR':[dict(contractor_code='{C}',contractor_name='BB mandor',contractor_type='MANDOR')]}
    rows.update(extra);return rows


def document(balance_type,code_field,number,original,settled,days_before=40):
    amount=D(original)-D(settled)
    return {'balance_type':balance_type,code_field:'{C}','amount':str(amount),'control_key':balance_type,'document_number':number,
            'original_amount':original,'settled_before_cutover':settled,'_days':days_before}


def financial_fixture(cur,today,documents=(),bank='100.00',legacy=(),credits=(),rights=(),extra=None,cutover_days=10):
    """Masters, a bank of `bank` and the requested opening documents (balance_type, number, original, settled)."""
    items=[dict(balance_type='CASH_BANK',cash_account_code='{C}',amount=bank,control_key='CASH_BANK')]
    fields={'CUSTOMER_RECEIVABLE':'customer_code','SUPPLIER_PAYABLE':'supplier_code','VENDOR_PAYABLE':'vendor_code',
            'CONTRACTOR_PAYABLE':'contractor_code','CONTRACTOR_RECEIVABLE':'contractor_code'}
    cutover=today-timedelta(days=cutover_days)
    for kind,number,original,settled,*rest in documents:
        row=document(kind,fields[kind],number,original,settled);row.pop('_days')
        row['document_date']=str(cutover-timedelta(days=40))
        if rest:row['source_kind']=rest[0]
        items.append(row)
    totals={}
    for i in items:totals[i['control_key']]=totals.get(i['control_key'],D(0))+D(i['amount'])
    rows=masters(**(extra or {}))
    rows['OPENING_BALANCE_ITEM']=items
    rows['OPENING_CONTROL']=[dict(control_key=k,balance_type=k,amount=str(v)) for k,v in totals.items()]
    if legacy:rows['LEGACY_DOCUMENT']=[dict(balance_type=k,party_code='{C}',document_number=n,document_date=str(cutover-timedelta(days=60)),
                                            original_amount=o,settled_before_cutover=o) for k,n,o in legacy]
    if credits:rows['OPENING_CUSTOMER_CREDIT']=[dict(customer_code='{C}',coa_account_code='{C}K',document_number=n,
                                                     document_date=str(cutover-timedelta(days=5)),original_amount=o,settled_before_cutover=s,
                                                     amount=str(D(o)-D(s))) for n,o,s in credits]
    if rights:rows['OPENING_SALE_RETURN']=[dict(customer_code='{C}',return_number=n,invoice_document_number=inv,product_sku='{C}P',
                                                brand_code='{C}',size_code='{C}',model_code='{C}',color_name='Blue',qty=q,
                                                credit_unit_price=p,unit_cost=c,credit_coa_account_code='{C}K') for n,inv,q,p,c in rights]
    batch,code,cutover=post_batch(cur,today,rows,cutover_days=cutover_days)
    api.admin(cur)
    cash=cur.execute('select id from erp.cash_accounts where cash_account_code=%s',(code,)).fetchone()[0]
    balances={r[0]:str(r[1]) for r in cur.execute('''select f.document_number,b.id from erp.initial_import_financial_sources f
        join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id where f.batch_id=%s''',(batch,)).fetchall()}
    return dict(batch=batch,code=code,cutover=cutover,cash=str(cash),balances=balances)


def product_masters():
    return dict(MODEL=[dict(model_code='{C}',model_name='BB model')],SIZE=[dict(size_code='{C}')],
                BRAND=[dict(brand_code='{C}',brand_name='BB brand')],
                PRODUCT=[dict(sku='{C}P',product_name='BB produk',model_code='{C}',brand_code='{C}',color_name='Blue',size_code='{C}')],
                LOCATION=[dict(location_code='{C}G',location_name='BB gudang FG',location_type='FG_WAREHOUSE')])


def bank(cur,fx):
    api.admin(cur)
    return cur.execute("""select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
      join erp.cash_accounts c on c.coa_account_id=l.account_id where c.id=%s and j.status in('POSTED','REVERSED')""",(fx['cash'],)).fetchone()[0]


def balance_row(cur,fx,number):
    api.admin(cur)
    return cur.execute('select original_amount,settled_amount,original_amount-settled_amount from erp.opening_subledger_balances where id=%s',
                       (fx['balances'][number],)).fetchone()


def party_gl(cur,mapping,column,party):
    api.admin(cur)
    return cur.execute(f"""select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
      where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id(%s) and l.{column}=%s""",(mapping,party)).fetchone()[0]


def truth(cur):
    """The existing financial detectors on the subledger, payments and business dates stay at zero."""
    api.admin(cur)
    names=['V2620M_OPENING_SUBLEDGER_STATE','V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH','V2620M_ORPHAN_PAYMENT_JOURNAL',
           'V2620U_JOURNAL_REVERSAL_BUSINESS_DATE','V2620Y_OPENING_SETTLEMENT_BUSINESS_DATE']
    rows=dict(cur.execute('select check_name,issue_count from erp.run_v267_financial_truth_checks() where check_name=any(%s)',(names,)).fetchall())
    return {k:rows.get(k) for k in names}


def truth_clean(cur):
    t=truth(cur);return all(v==0 for v in t.values()),t


# ---------------------------------------------------------------- P02/S01: settle and reverse through the facade

def settle_cycle(cur,today,kind):
    """P02 (supplier invoice 100, paid 35 before cutover) and S01 (customer invoice 100, received 30): settle 20/25 on the
    day after cutover, then reverse; the balance, bank and party account move exactly and only OSS journals exist."""
    number='INV-'+kind[:4]
    original,settled,pay={'SUPPLIER_PAYABLE':('100.00','35.00','20.00'),'CUSTOMER_RECEIVABLE':('100.00','30.00','25.00'),
                          'VENDOR_PAYABLE':('100.00','40.00','10.00')}[kind]
    fx=financial_fixture(cur,today,documents=[(kind,number,original,settled)])
    start=now(cur)
    payload=dict(operation='SETTLE',balance_id=fx['balances'][number],amount=pay,effective_date=str(fx['cutover']+timedelta(days=1)),
                 cash_account_id=fx['cash'],reason='BB probe settlement')
    if not bb_installed(cur):
        return no_route(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload),kind=kind)
    opening=D(original)-D(settled);before_bank=bank(cur,fx)
    key=uuid.uuid4()
    body=dict(batch_id=fx['batch'],expected_revision=revision(cur,fx['batch']),**payload)
    first=api.call(cur,'OPENING_SETTLEMENT',body,key)
    replay=api.call(cur,'OPENING_SETTLEMENT',body,key)
    other=refused(cur,lambda:api.call(cur,'OPENING_SETTLEMENT',dict(body,amount='1.00'),key),'IDEMPOTENCY')
    after_settle=balance_row(cur,fx,number);bank_settled=bank(cur,fx)
    sign=-1 if kind!='CUSTOMER_RECEIVABLE' else 1
    reverse=act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='REVERSE',settlement_id=first['settlement_id'],reason='BB probe reversal')
    after_reverse=balance_row(cur,fx,number);bank_reversed=bank(cur,fx)
    types=journal_types(cur,start);clean,detectors=truth_clean(cur)
    settlements=cur.execute('select count(*) from erp.opening_subledger_settlements where balance_id=%s',(fx['balances'][number],)).fetchone()[0]
    return verdict(dict(
        remaining_after_settle=after_settle[2]==opening-D(pay),
        bank_after_settle=bank_settled==before_bank+sign*D(pay),
        replay_same_result=replay==first,
        same_key_other_payload_refused=other['refusal'] is not None,
        one_settlement_row=settlements==1,
        remaining_after_reverse=after_reverse[2]==opening,
        bank_after_reverse=bank_reversed==before_bank,
        only_settlement_journals=set(types)<= {'OPENING_SUBLEDGER_SETTLEMENT','JOURNAL_REVERSAL'},
        detectors_zero=clean),
        kind=kind,opening=str(opening),settled=pay,after_settle=[str(x) for x in after_settle],after_reverse=[str(x) for x in after_reverse],
        bank=[str(before_bank),str(bank_settled),str(bank_reversed)],journals=types,detectors=detectors,reverse=reverse)


def settle_refusal(cur,today,case):
    """Over the remaining amount, before cutover, and in the future: refused with the exact code, nothing changes."""
    fx=financial_fixture(cur,today,documents=[('SUPPLIER_PAYABLE','INV-R','100.00','35.00')])
    amount,day,code={'OVER':('65.01',fx['cutover']+timedelta(days=1),'BB_OSS_EXCEEDS_AVAILABLE'),
                     'BEFORE_CUTOVER':('10.00',fx['cutover']-timedelta(days=1),'BB_OSS_DATE_OUT_OF_RANGE'),
                     'FUTURE':('10.00',today+timedelta(days=1),'BB_OSS_DATE_OUT_OF_RANGE')}[case]
    payload=dict(operation='SETTLE',balance_id=fx['balances']['INV-R'],amount=amount,effective_date=str(day),cash_account_id=fx['cash'],reason='BB probe refusal')
    if not bb_installed(cur):
        return no_route(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload),variant=case)
    r=refused(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload),code)
    return verdict(dict(refused_with_code=r['ok']),variant=case,refusal=r['refusal'])


def direct_settlement(cur,fx,number,amount,day):
    """A DRAFT settlement posted through the existing function, as an owner may call it directly (before and after BB)."""
    api.admin(cur)
    sid=cur.execute("""insert into erp.opening_subledger_settlements(settlement_number,balance_id,amount,cash_account_id,physical_at,status,created_by)
      values(%s,%s,%s,%s,%s,'DRAFT',null) returning id""",('BB-DIRECT-'+uuid.uuid4().hex,fx['balances'][number],amount,fx['cash'],
                                                          str(day)+'T10:00:00+07:00')).fetchone()[0]
    return sid,r1.peer.attempt(cur,lambda:bap.api.ordinary(cur) or cur.execute('select erp.post_opening_subledger_settlement(%s)',(sid,)).fetchone())


def direct_date_finding(cur,today,case):
    """The bug found while designing BB: post_opening_subledger_settlement checked dates only for cash advances, so an
    ordinary settlement could be dated before cutover. Before BB it posts (COUNTEREXAMPLE); after BB it is refused
    BB_OSS_DATE_OUT_OF_RANGE for every caller. A future date was already refused before BB by post_journal (local BB probe,
    phase before: "Transaksi/jurnal tidak boleh dipost ke tanggal masa depan"), so FUTURE is a regression control refused in
    both phases (after BB with the BB code, before the journal is written)."""
    fx=financial_fixture(cur,today,documents=[('CUSTOMER_RECEIVABLE','INV-D','100.00','30.00')])
    day=fx['cutover']-timedelta(days=3) if case=='BEFORE_CUTOVER' else today+timedelta(days=2)
    api.admin(cur);cur.execute('grant usage on schema erp to authenticated')
    sid,(result,error)=direct_settlement(cur,fx,'INV-D','10.00',day)
    api.admin(cur)
    status=cur.execute('select status from erp.opening_subledger_settlements where id=%s',(sid,)).fetchone()[0]
    evidence=dict(variant=case,settlement_date=str(day),cutover=str(fx['cutover']),settlement_status=status,refusal=error)
    if bb_installed(cur):
        return dict(evidence,status='PASS' if error is not None and code_of(error)=='BB_OSS_DATE_OUT_OF_RANGE' else ('FAIL' if error is None else 'INCOMPLETE'))
    if case=='FUTURE':
        return dict(evidence,status='PASS' if error is not None and status=='DRAFT' else ('FAIL' if error is None else 'INCOMPLETE'))
    return dict(evidence,status='COUNTEREXAMPLE' if error is None and status=='POSTED' else 'INCOMPLETE')


def dated_capacity(cur,today,back):
    """D02 on opening balances: 65 open, settled in full the day after cutover, the opening corrected 65 -> 75 three days
    later. A settlement of 10 dated before the correction takes money that did not exist yet (dated balance -10)."""
    fx=financial_fixture(cur,today,documents=[('SUPPLIER_PAYABLE','INV-C','100.00','35.00')])
    c=fx['cutover'];api.admin(cur);cur.execute('grant usage on schema erp to authenticated')
    full,(r0,e0)=direct_settlement(cur,fx,'INV-C','65.00',c+timedelta(days=1))
    assert e0 is None,('BB_CAPACITY_FIXTURE_FULL_SETTLEMENT',e0)
    item=cur.execute('select opening_item_id from erp.opening_subledger_balances where id=%s',(fx['balances']['INV-C'],)).fetchone()[0]
    bap.api.ordinary(cur);cur.execute('select erp.post_opening_financial_correction(%s,%s,%s,%s)',(item,'75.00','BB probe correction',c+timedelta(days=4)))
    api.admin(cur)
    day=c+timedelta(days=2) if back else c+timedelta(days=4)
    if bb_installed(cur):
        payload=dict(operation='SETTLE',balance_id=fx['balances']['INV-C'],amount='10.00',effective_date=str(day),cash_account_id=fx['cash'],reason='BB probe capacity')
        if back:
            r=refused(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload),'BB_OSS_DATED_CAPACITY')
            return verdict(dict(refused_with_code=r['ok']),settlement_date=str(day),refusal=r['refusal'])
        res,err=r1.peer.attempt(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload))
        return verdict(dict(posted=err is None,remaining_zero=balance_row(cur,fx,'INV-C')[2]==0),settlement_date=str(day),refusal=err)
    sid,(result,error)=direct_settlement(cur,fx,'INV-C','10.00',day)
    api.admin(cur)
    posted=cur.execute('select status from erp.opening_subledger_settlements where id=%s',(sid,)).fetchone()[0]=='POSTED'
    if back:return dict(status='COUNTEREXAMPLE' if error is None and posted else 'INCOMPLETE',settlement_date=str(day),refusal=error,
                        dated_balance_on_settlement_day=str(D('65.00')-D('65.00')-D('10.00')))
    return dict(status='PASS' if error is None and posted else 'INCOMPLETE',settlement_date=str(day),refusal=error)


# ---------------------------------------------------------------- P02/S01: credit notes and allowances

def allowance(cur,today,kind):
    number={'CUSTOMER_ALLOWANCE':'INV-CA','SUPPLIER_ALLOWANCE':'INV-SA','VENDOR_ALLOWANCE':'INV-VA'}[kind]
    balance={'CUSTOMER_ALLOWANCE':'CUSTOMER_RECEIVABLE','SUPPLIER_ALLOWANCE':'SUPPLIER_PAYABLE','VENDOR_ALLOWANCE':'VENDOR_PAYABLE'}[kind]
    fx=financial_fixture(cur,today,documents=[(balance,number,'100.00','30.00')])
    payload=dict(operation='CREDIT',balance_id=fx['balances'][number],amount='10.00',effective_date=str(fx['cutover']+timedelta(days=2)),
                 credit_kind=kind,credit_note_number='CN-'+fx['code'],reason='BB probe allowance')
    if not bb_installed(cur):
        return no_route(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload),kind=kind)
    before=gl(cur);before_bank=bank(cur,fx)
    posted=act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload)
    delta=moved(before,gl(cur))
    dup=refused(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],**dict(payload,amount='1.00')),'BB_CREDIT_NOTE_DUPLICATE')
    expected={'CUSTOMER_ALLOWANCE':{account(cur,'SALES_REVENUE'):'10.00',account(cur,'AR_CUSTOMER'):'-10.00'},
              'SUPPLIER_ALLOWANCE':{account(cur,'AP_SUPPLIER'):'10.00',account(cur,'MATERIAL_PURCHASE_VARIANCE'):'-10.00'},
              'VENDOR_ALLOWANCE':{account(cur,'AP_VENDOR'):'10.00',account(cur,'OTHER_INCOME'):'-10.00'}}[kind]
    remaining=balance_row(cur,fx,number)[2]
    reverse=act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='REVERSE',settlement_id=posted['settlement_id'],reason='BB probe allowance reversal')
    clean,detectors=truth_clean(cur)
    return verdict(dict(ledger_exact=delta==expected,remaining_60=remaining==D('60.00'),bank_unchanged=bank(cur,fx)==before_bank,
                        duplicate_note_refused=dup['ok'],reversed_to_70=balance_row(cur,fx,number)[2]==D('70.00'),
                        ledger_restored=moved(before,gl(cur))=={},detectors_zero=clean),
                   kind=kind,ledger_delta=delta,expected=expected,detectors=detectors)


# ---------------------------------------------------------------- A03: fully settled legacy documents

def legacy_document(cur,today,case):
    """ALL-A03: a document fully settled before cutover is provenance only (no journal, balance or cash) and its number
    cannot come back as an open document of the same party."""
    rows=masters(LEGACY_DOCUMENT=[dict(balance_type='CUSTOMER_RECEIVABLE',party_code='{C}',document_number='LEG-1',
        document_date=str(today-timedelta(days=90)),original_amount='100.00',settled_before_cutover='100.00' if case!='NOT_SETTLED' else '90.00')],
        OPENING_BALANCE_ITEM=[dict(balance_type='CASH_BANK',cash_account_code='{C}',amount='100.00',control_key='CASH_BANK')],
        OPENING_CONTROL=[dict(control_key='CASH_BANK',balance_type='CASH_BANK',amount='100.00')])
    if case=='SAME_BATCH_OPEN':
        rows['OPENING_BALANCE_ITEM'].append(dict(balance_type='CUSTOMER_RECEIVABLE',customer_code='{C}',amount='10.00',control_key='AR',
            document_number='leg-1',document_date=str(today-timedelta(days=90)),original_amount='10.00',settled_before_cutover='0.00'))
        rows['OPENING_CONTROL'].append(dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='10.00'))
    if not bb_installed(cur):
        code='BB'+uuid.uuid4().hex[:12]
        batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=10))))['batch_id']
        return no_route(cur,lambda:api.upload(cur,batch,'LEGACY_DOCUMENT',[{k:v.replace('{C}',code) for k,v in rows['LEGACY_DOCUMENT'][0].items()}]),variant=case)
    if case in('NOT_SETTLED','SAME_BATCH_OPEN'):
        try:post_batch(cur,today,rows);return dict(status="FAIL",variant=case,note="posted")
        except AssertionError as exc:
            text=str(exc);ok='BB_LEGACY_DOCUMENT_NOT_SETTLED' in text if case=='NOT_SETTLED' else 'BB_LEGACY_DOCUMENT_DUPLICATE' in text
            return verdict(dict(refused_at_validation=ok),variant=case,errors=text[:1500])
    start=now(cur);before=gl(cur)
    batch,code,cutover=post_batch(cur,today,rows)
    api.admin(cur)
    legacy=cur.execute('select count(*) from erp.bb_legacy_documents_v1 where batch_id=%s',(batch,)).fetchone()[0]
    balances=cur.execute('select count(*) from erp.initial_import_financial_sources where batch_id=%s',(batch,)).fetchone()[0]
    types=journal_types(cur,start)
    checks=dict(one_legacy_row=legacy==1,no_financial_source=balances==0,only_cash_opening_journal=set(types)<={'OPENING_BALANCE'},
                bank_100=D(list(moved(before,gl(cur)).values())[0] if moved(before,gl(cur)) else 0).copy_abs()==D('100.00'))
    if case=='LATER_BATCH_OPEN':
        later={'OPENING_BALANCE_ITEM':[dict(balance_type='CUSTOMER_RECEIVABLE',customer_code=code,amount='10.00',control_key='AR',
                   document_number='LEG-1',document_date=str(today-timedelta(days=90)),original_amount='10.00',settled_before_cutover='0.00')],
               'OPENING_CONTROL':[dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='10.00')]}
        try:post_batch(cur,today,later,cutover_days=5);checks['later_open_refused']=False
        except AssertionError as exc:checks['later_open_refused']='BB_LEGACY_DOCUMENT_DUPLICATE' in str(exc)
        except psycopg.Error as exc:checks['later_open_refused']='BB_LEGACY_DOCUMENT_DUPLICATE' in str(exc)
    return verdict(checks,variant=case,journals=types)


# ---------------------------------------------------------------- S03: customer credits and returns of old sales

def imported_credit(cur,today):
    """(b) A return received before cutover with its refund still open: credit 25 (40 less 15 refunded). Refund 15 leaves
    10, a second refund of 15 is refused, reversing the refund restores 25; stock and revenue never move."""
    fx=financial_fixture(cur,today,credits=[('RC-1','40.00','15.00')]) if bb_installed(cur) else None
    if not bb_installed(cur):
        code='BB'+uuid.uuid4().hex[:12]
        batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=10))))['batch_id']
        return no_route(cur,lambda:api.upload(cur,batch,'OPENING_CUSTOMER_CREDIT',[dict(customer_code=code,coa_account_code=code,
            document_number='RC-1',document_date=str(today-timedelta(days=15)),original_amount='40.00',settled_before_cutover='15.00',amount='25.00')]))
    credit=ws(cur,fx['batch'])['customer_credits'][0]
    before=gl(cur);before_bank=bank(cur,fx)
    refund=act(cur,'CUSTOMER_CREDIT',fx['batch'],operation='REFUND',credit_id=credit['credit_id'],amount='15.00',
               effective_date=str(fx['cutover']+timedelta(days=1)),cash_account_id=fx['cash'],reason='BB probe refund')
    after=ws(cur,fx['batch'])['customer_credits'][0]
    again=refused(cur,lambda:act(cur,'CUSTOMER_CREDIT',fx['batch'],operation='REFUND',credit_id=credit['credit_id'],amount='15.00',
               effective_date=str(fx['cutover']+timedelta(days=2)),cash_account_id=fx['cash'],reason='BB probe refund again'),'BB_RETURN_CREDIT_EXCEEDS_REMAINING')
    bank_after=bank(cur,fx)
    act(cur,'CUSTOMER_CREDIT',fx['batch'],operation='REVERSE_EVENT',event_id=refund['event_id'],reason='BB probe refund reversal')
    final=ws(cur,fx['batch'])['customer_credits'][0]
    touched={k for k in moved(before,gl(cur))}
    clean,detectors=truth_clean(cur)
    return verdict(dict(credit_25=credit['remaining_amount']=='25.00',after_refund_10=after['remaining_amount']=='10.00',
                        bank_minus_15=bank_after==before_bank-15,second_refund_refused=again['ok'],restored_25=final['remaining_amount']=='25.00',
                        ledger_restored=not touched,no_revenue_or_stock=account(cur,'SALES_REVENUE') not in moved(before,gl(cur)),
                        detectors_zero=clean),credit=credit,after=after,final=final,detectors=detectors)


def credit_apply(cur,today):
    """A customer credit applied to an open imported receivable of the same customer: AR 70 -> 50, credit 25 -> 5, then
    the application is reversed through the credit and both return."""
    if not bb_installed(cur):
        return imported_credit(cur,today)
    fx=financial_fixture(cur,today,documents=[('CUSTOMER_RECEIVABLE','INV-A','100.00','30.00')],credits=[('RC-2','25.00','0.00')])
    credit=ws(cur,fx['batch'])['customer_credits'][0]
    before=gl(cur)
    applied=act(cur,'CUSTOMER_CREDIT',fx['batch'],operation='APPLY_OPENING_AR',credit_id=credit['credit_id'],balance_id=fx['balances']['INV-A'],
                amount='20.00',effective_date=str(fx['cutover']+timedelta(days=1)),reason='BB probe apply')
    ar=balance_row(cur,fx,'INV-A')[2];mid=ws(cur,fx['batch'])['customer_credits'][0]
    direct=refused(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='REVERSE',settlement_id=applied['event_id'],reason='x'),'BB_OSS_USE_SOURCE_REVERSAL')
    act(cur,'CUSTOMER_CREDIT',fx['batch'],operation='REVERSE_EVENT',event_id=applied['event_id'],reason='BB probe apply reversal')
    final=ws(cur,fx['batch'])['customer_credits'][0]
    clean,detectors=truth_clean(cur)
    return verdict(dict(ar_50=ar==D('50.00'),credit_5=mid['remaining_amount']=='5.00',direct_reverse_refused=direct['ok'],
                        ar_back_70=balance_row(cur,fx,'INV-A')[2]==D('70.00'),credit_back_25=final['remaining_amount']=='25.00',
                        ledger_restored=moved(before,gl(cur))=={},detectors_zero=clean),detectors=detectors)


def return_right(cur,today,invoice):
    """(a) A pending return of 3 pcs from an old invoice (open receivable 70, or a fully settled legacy invoice), credit
    10/pcs and cost 6/pcs: receiving 3 books FG 3 pcs at 18 against COGS and a credit of 30 against revenue once; a 4th
    pcs is refused; the credit settles the receivable or is refunded; a used credit blocks the receipt reversal."""
    rights=[('RR-1','INV-S' if invoice=='OPEN' else 'LEG-S','3','10.00','6.00')]
    documents=[('CUSTOMER_RECEIVABLE','INV-S','100.00','30.00')] if invoice=='OPEN' else []
    legacy=[('CUSTOMER_RECEIVABLE','LEG-S','100.00')] if invoice!='OPEN' else []
    if not bb_installed(cur):
        code='BB'+uuid.uuid4().hex[:12]
        batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=10))))['batch_id']
        return no_route(cur,lambda:api.upload(cur,batch,'OPENING_SALE_RETURN',[dict(customer_code=code,return_number='RR-1',
            invoice_document_number='INV-S',product_sku=code,qty='3',credit_unit_price='10.00',unit_cost='6.00',credit_coa_account_code=code)]),invoice=invoice)
    fx=financial_fixture(cur,today,documents=documents,legacy=legacy,rights=rights,extra=product_masters())
    w=ws(cur,fx['batch']);right=w['sale_return_rights'][0]
    api.admin(cur);location=str(cur.execute('select id from erp.locations where location_code=%s',(fx['code']+'G',)).fetchone()[0])
    before=gl(cur);day=str(fx['cutover']+timedelta(days=2))
    received=act(cur,'OPENING_RETURN',fx['batch'],operation='RECEIVE',right_id=right['id'],qty='3',location_id=location,effective_date=day,reason='BB probe receive')
    delta=moved(before,gl(cur))
    more=refused(cur,lambda:act(cur,'OPENING_RETURN',fx['batch'],operation='RECEIVE',right_id=right['id'],qty='1',location_id=location,
                                  effective_date=day,reason='BB probe fourth'),'BB_RETURN_EXCEEDS_RIGHT')
    api.admin(cur)
    stock=cur.execute('select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(received['lot_id'],)).fetchone()[0]
    credit_account=str(cur.execute('select id from erp.chart_accounts where account_code=%s',(fx['code']+'K',)).fetchone()[0])
    expected={account(cur,'FG_INVENTORY'):'18.00',account(cur,'COGS'):'-18.00',account(cur,'SALES_REVENUE'):'30.00',credit_account:'-30.00'}
    checks=dict(stock_3=stock==3,ledger_exact=delta==expected,fourth_refused=more['ok'])
    if invoice=='OPEN':
        use=act(cur,'CUSTOMER_CREDIT',fx['batch'],operation='APPLY_OPENING_AR',credit_id=received['credit_id'],balance_id=fx['balances']['INV-S'],
                amount='30.00',effective_date=day,reason='BB probe credit to invoice')
        checks['ar_40']=balance_row(cur,fx,'INV-S')[2]==D('40.00')
    else:
        before_bank=bank(cur,fx)
        use=act(cur,'CUSTOMER_CREDIT',fx['batch'],operation='REFUND',credit_id=received['credit_id'],amount='30.00',effective_date=day,
                cash_account_id=fx['cash'],reason='BB probe refund of return')
        checks['bank_minus_30']=bank(cur,fx)==before_bank-30
    blocked=refused(cur,lambda:act(cur,'OPENING_RETURN',fx['batch'],operation='REVERSE_RECEIPT',receipt_id=received['receipt_id'],reason='x'),'BB_RETURN_CREDIT_USED')
    act(cur,'CUSTOMER_CREDIT',fx['batch'],operation='REVERSE_EVENT',event_id=use['event_id'],reason='BB probe undo credit use')
    act(cur,'OPENING_RETURN',fx['batch'],operation='REVERSE_RECEIPT',receipt_id=received['receipt_id'],reason='BB probe undo receipt')
    api.admin(cur)
    stock_after=cur.execute('select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(received['lot_id'],)).fetchone()[0]
    clean,detectors=truth_clean(cur)
    checks.update(reverse_blocked_while_credit_used=blocked['ok'],stock_back_0=stock_after==0,ledger_restored=moved(before,gl(cur))=={},
                  detectors_zero=clean)
    if invoice=='OPEN':checks['ar_back_70']=balance_row(cur,fx,'INV-S')[2]==D('70.00')
    return verdict(checks,invoice=invoice,ledger_delta=delta,expected=expected,detectors=detectors)


def return_without_invoice(cur,today):
    if not bb_installed(cur):
        return return_right(cur,today,'OPEN')
    try:
        financial_fixture(cur,today,rights=[('RR-X','INV-NONE','1','10.00','6.00')],extra=product_masters())
        return dict(status='FAIL',note='posted')
    except AssertionError as exc:
        return verdict(dict(refused_at_validation='BB_RETURN_INVOICE_REQUIRED' in str(exc)),errors=str(exc)[:1200])


# ---------------------------------------------------------------- Y01: imported contractor payables through payroll

def y01_payroll(cur,today):
    """Old wages 80 with 40 paid before cutover (40 open) and reimbursement 20, plus a cash advance of 30: one payroll
    pays both opening lines and deducts the advance; approval accrues nothing for the opening lines; the bank moves the
    net 30 only; settling the reserved balance in cash is refused; reversing the payroll restores every balance."""
    documents=[('CONTRACTOR_PAYABLE','UPAH-OLD','80.00','40.00'),('CONTRACTOR_PAYABLE','REIMB-OLD','20.00','0.00'),
               ('CONTRACTOR_RECEIVABLE','KASBON-OLD','30.00','0.00','CONTRACTOR_CASH_ADVANCE')]
    fx=financial_fixture(cur,today,documents=documents,bank='200.00')
    api.admin(cur)
    contractor=cur.execute('select id from erp.contractors where contractor_code=%s',(fx['code'],)).fetchone()[0]
    p=cur.execute("""insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date,
        payment_cash_account_id) values(%s,%s,%s,%s,0,%s,%s) returning id""",('BBY-'+uuid.uuid4().hex,contractor,today,today,today,fx['cash'])).fetchone()[0]
    version=lambda:str(cur.execute('select row_version from erp.payroll_settlements where id=%s',(p,)).fetchone()[0])
    if not bb_installed(cur):
        return no_route(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='ALLOCATE_PAYROLL',balance_id=fx['balances']['UPAH-OLD'],
                                       payroll_id=str(p),amount='40.00',expected_payroll_version=version()))
    before=gl(cur);before_bank=bank(cur,fx);start=now(cur)
    for number,amount in (('UPAH-OLD','40.00'),('REIMB-OLD','20.00')):
        act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='ALLOCATE_PAYROLL',balance_id=fx['balances'][number],payroll_id=str(p),amount=amount,
            expected_payroll_version=version())
    api.call(cur,'ALLOCATE_CASH_ADVANCE',dict(batch_id=fx['batch'],expected_revision=revision(cur,fx['batch']),balance_id=fx['balances']['KASBON-OLD'],
             payroll_id=str(p),amount='30.00',expected_payroll_version=version()))
    over=refused(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='SETTLE',balance_id=fx['balances']['UPAH-OLD'],amount='1.00',
                                effective_date=str(today),cash_account_id=fx['cash'],reason='BB probe reserved'),'BB_OSS_EXCEEDS_AVAILABLE')
    api.admin(cur);cur.execute('grant usage on schema erp to authenticated')
    bap.api.ordinary(cur);cur.execute('select erp.approve_payroll(%s)',(p,));api.admin(cur)
    accruals=cur.execute("select count(*) from erp.journal_entries where source_id=%s and source_type='PAYROLL_EXTRA_ACCRUAL'",(p,)).fetchone()[0]
    cur.execute('grant usage on schema erp to authenticated');bap.api.ordinary(cur)
    cur.execute('select erp.post_payroll_payment(%s)',(p,));api.admin(cur)
    paid=dict(bank=bank(cur,fx)-before_bank,upah=balance_row(cur,fx,'UPAH-OLD')[2],reimb=balance_row(cur,fx,'REIMB-OLD')[2],
              kasbon=balance_row(cur,fx,'KASBON-OLD')[2])
    net=cur.execute('select net_payable from erp.payroll_settlements where id=%s',(p,)).fetchone()[0]
    cur.execute('grant usage on schema erp to authenticated');bap.api.ordinary(cur)
    cur.execute('select erp.reverse_paid_payroll(%s,%s)',(p,'BB probe payroll reversal'));api.admin(cur)
    restored=dict(bank=bank(cur,fx)-before_bank,upah=balance_row(cur,fx,'UPAH-OLD')[2],reimb=balance_row(cur,fx,'REIMB-OLD')[2],
                  kasbon=balance_row(cur,fx,'KASBON-OLD')[2])
    clean,detectors=truth_clean(cur)
    return verdict(dict(net_30=net==D('30.00'),no_second_accrual=accruals==0,bank_minus_30=paid['bank']==D('-30.00'),
                        payables_settled=paid['upah']==0 and paid['reimb']==0,advance_settled=paid['kasbon']==0,
                        reserved_cash_settle_refused=over['ok'],
                        restored=restored==dict(bank=D(0),upah=D('40.00'),reimb=D('20.00'),kasbon=D('30.00')),
                        ledger_restored=moved(before,gl(cur))=={},detectors_zero=clean),
                   paid={k:str(v) for k,v in paid.items()},restored={k:str(v) for k,v in restored.items()},net=str(net),detectors=detectors,
                   journals=journal_types(cur,start))


def y01_over(cur,today):
    fx=financial_fixture(cur,today,documents=[('CONTRACTOR_PAYABLE','UPAH-X','80.00','40.00')])
    api.admin(cur)
    contractor=cur.execute('select id from erp.contractors where contractor_code=%s',(fx['code'],)).fetchone()[0]
    p=cur.execute("""insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date,
        payment_cash_account_id) values(%s,%s,%s,%s,0,%s,%s) returning id""",('BBY-'+uuid.uuid4().hex,contractor,today,today,today,fx['cash'])).fetchone()[0]
    v=str(cur.execute('select row_version from erp.payroll_settlements where id=%s',(p,)).fetchone()[0])
    payload=dict(operation='ALLOCATE_PAYROLL',balance_id=fx['balances']['UPAH-X'],payroll_id=str(p),amount='40.01',expected_payroll_version=v)
    if not bb_installed(cur):
        return no_route(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload))
    r=refused(cur,lambda:act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload),'BB_OPENING_PAYABLE_EXCEEDS_AVAILABLE')
    return verdict(dict(refused_with_code=r['ok']),refusal=r['refusal'])


# ---------------------------------------------------------------- P03: one receipt, part invoiced before cutover

def p03_rows(cutover,variant='OK'):
    """Receipt RCV of 10 units: 4 invoiced before cutover on INV (4 x 2.50 = 10.00, 3.00 paid before cutover, 7.00 open),
    6 unbilled at the estimate 2.00. All 10 on hand at the blended cost (6 x 2.00 + 10.00) / 10 = 2.20; bank 100."""
    stock_qty='9' if variant=='EQUATION' else '10'
    stock_cost='2.00' if variant=='NOT_BLENDED' else '2.2'
    document='INV-{C}' if variant!='NO_DOCUMENT' else 'INV-MISSING'
    return {'CHART_ACCOUNT':[dict(account_code='{C}B',account_name='BB P03 bank',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT')],
            'CASH_ACCOUNT':[dict(cash_account_code='{C}',cash_account_name='BB P03 bank',coa_account_code='{C}B',account_kind='BANK')],
            'SUPPLIER':[dict(supplier_code='{C}',supplier_name='BB P03 supplier',supplier_type='MATERIAL')],
            'LOCATION':[dict(location_code='{C}',location_name='BB P03 gudang',location_type='RAW_MATERIAL_WAREHOUSE')],
            'MATERIAL':[dict(material_sku='{C}',material_name='BB P03 benang',material_type='OTHER',unit_code='PCS')],
            'OPENING_BALANCE_ITEM':[
                dict(balance_type='MATERIAL',material_sku='{C}',location_code='{C}',qty=stock_qty,unit_cost=stock_cost,opening_source_key='STOCK',control_key='STOCK'),
                dict(balance_type='SUPPLIER_PAYABLE',supplier_code='{C}',amount='7.00',control_key='AP',document_number='INV-{C}',
                     document_date=str(cutover-timedelta(days=15)),original_amount='10.00',settled_before_cutover='3.00'),
                dict(balance_type='CASH_BANK',cash_account_code='{C}',amount='100.00',control_key='CASH')],
            'UNINVOICED_RECEIPT':[dict(receipt_number='RCV-{C}',receipt_line_number='001',receipt_date=str(cutover-timedelta(days=20)),
                                       supplier_code='{C}',material_sku='{C}',location_code='{C}',qty='6',unit_cost='2',opening_source_key='STOCK',
                                       control_key='GRNI',invoiced_qty='4',invoice_document_number=document)],
            'OPENING_CONTROL':[dict(control_key='STOCK',balance_type='MATERIAL',qty=stock_qty,amount=str(D(stock_qty)*D(stock_cost))),
                               dict(control_key='GRNI',balance_type='GRNI_MATERIAL',qty='6',amount='12.00'),
                               dict(control_key='AP',balance_type='SUPPLIER_PAYABLE',amount='7.00'),
                               dict(control_key='CASH',balance_type='CASH_BANK',amount='100.00')]}


def p03_state(cur,item):
    api.admin(cur)
    row=cur.execute("""select i.qty,erp.material_purchase_posted_invoice_qty(i.id),i.invoice_match_state,
        erp.material_purchase_current_unit_cost(i.id),erp.material_purchase_grni_total(i.purchase_id),erp.material_purchase_final_ap_total(i.purchase_id)
        from erp.material_purchase_items i where i.id=%s""",(item,)).fetchone()
    return dict(qty=row[0],posted=row[1],match=row[2],unit_cost=D(row[3]).quantize(D('.000001')),grni=D(row[4]).quantize(D('.01')),
                native_ap=D(row[5]).quantize(D('.01')))


def detectors_ok(cur):
    try:receipt_trial.truth(cur);return True
    except AssertionError as exc:return str(exc)[:600]


def p03_split(cur,today):
    """ALL-P03 (auditor: "One receipt of 10 with 4 already invoiced and 6 unbilled: derive the two nonoverlapping obligations,
    physical/origin quantities and payments, then prove the combined controls without duplicate AP/GRNI")."""
    cutover=today-timedelta(days=10);rows=p03_rows(cutover)
    if not bb_installed(cur):
        code='BB'+uuid.uuid4().hex[:12]
        batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(cutover)))['batch_id']
        receipt={k:(v.replace('{C}',code) if isinstance(v,str) else v) for k,v in rows['UNINVOICED_RECEIPT'][0].items()}
        return no_route(cur,lambda:api.upload(cur,batch,'UNINVOICED_RECEIPT',[receipt]))
    before=gl(cur)
    batch,code,cutover=post_batch(cur,today,rows)
    api.admin(cur)
    supplier,cash=cur.execute('select s.id,c.id from erp.suppliers s cross join erp.cash_accounts c where s.supplier_code=%s and c.cash_account_code=%s',
                              (code,code)).fetchone()
    item=cur.execute("""select l.purchase_item_id from erp.initial_import_receipt_lines l join erp.initial_import_receipt_headers h
        on h.purchase_id=l.purchase_id where h.batch_id=%s""",(batch,)).fetchone()[0]
    balance=cur.execute("""select b.id from erp.initial_import_financial_sources f join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
        where f.batch_id=%s and f.balance_type='SUPPLIER_PAYABLE'""",(batch,)).fetchone()[0]
    imported=p03_state(cur,item);import_delta=moved(before,gl(cur))
    documents=cur.execute("""select (select count(*) from erp.material_supplier_invoices where supplier_id=%s),
        (select count(*) from erp.supplier_payments p join erp.material_purchase_headers h on h.id=p.purchase_id where h.supplier_id=%s)""",
        (supplier,supplier)).fetchone()
    detectors_import=detectors_ok(cur)
    row=dict(supplier_id=str(supplier),purchase_item_id=str(item))
    # Invoice capacity is enforced when an invoice posts (a draft may be saved first): 7 of the 6 unbilled units is refused.
    over=refused(cur,lambda:receipt_trial.post_invoice(api,cur,receipt_trial.invoice(api,cur,today,row,'7','2.25',date=today-timedelta(days=2))),'ANY')
    draft=receipt_trial.invoice(api,cur,today,row,'6','2.25',date=today-timedelta(days=2))
    posted=receipt_trial.post_invoice(api,cur,draft)
    invoiced=p03_state(cur,item)
    act(cur,'OPENING_SETTLEMENT',batch,operation='SETTLE',balance_id=str(balance),amount='7.00',effective_date=str(cutover+timedelta(days=1)),
        cash_account_id=str(cash),reason='BB P03 pay the part invoiced before cutover')
    api.admin(cur)
    ap_doc=cur.execute('select original_amount-settled_amount from erp.opening_subledger_balances where id=%s',(balance,)).fetchone()[0]
    detectors_invoiced=detectors_ok(cur)
    receipt_trial.rpc(api,cur,'reverse_material_supplier_invoice_v2',posted['supplier_invoice_id'],'BB P03 reverse final invoice',uuid.uuid4(),posted['row_version'])
    reversed_state=p03_state(cur,item);detectors_reversed=detectors_ok(cur)
    inventory=account(cur,'MATERIAL_INVENTORY');grni_account=account(cur,'GRNI_MATERIAL');ap_account=account(cur,'AP_SUPPLIER')
    return verdict(dict(
        one_item_full_qty=imported['qty']==10,invoiced_part_matched=imported['posted']==4 and imported['match']=='PARTIAL',
        blended_cost=imported['unit_cost']==D('2.200000'),grni_only_unbilled=imported['grni']==D('12.00'),no_native_ap=imported['native_ap']==0,
        opening_ledger=import_delta.get(grni_account)=='-12.00' and import_delta.get(ap_account)=='-7.00' and import_delta.get(inventory)=='22.00',
        no_old_invoice_or_payment=documents==(0,0),detectors_after_import=detectors_import is True,
        over_capacity_invoice_refused=over['refusal'] is not None,
        final_invoice_closes_grni=invoiced['grni']==0 and invoiced['native_ap']==D('13.50') and invoiced['match']=='MATCHED',
        final_cost=invoiced['unit_cost']==D('2.350000'),invoiced_part_paid_once=ap_doc==0,
        detectors_after_invoice_and_payment=detectors_invoiced is True,
        reversal_restores=reversed_state['grni']==D('12.00') and reversed_state['unit_cost']==D('2.200000') and reversed_state['match']=='PARTIAL',
        detectors_after_reversal=detectors_reversed is True),
        imported={k:str(v) for k,v in imported.items()},invoiced={k:str(v) for k,v in invoiced.items()},
        reversed={k:str(v) for k,v in reversed_state.items()},import_delta=import_delta,
        detectors=[detectors_import,detectors_invoiced,detectors_reversed],over=over['refusal'])


def p03_refusal(cur,today,variant):
    cutover=today-timedelta(days=10);rows=p03_rows(cutover,variant)
    expected={'NO_DOCUMENT':'P03_INVOICE_DOC_REQUIRED','NOT_BLENDED':'biaya per satuan 2.200000','EQUATION':'jumlah belum ditagih harus tepat sama'}[variant]
    if not bb_installed(cur):
        return p03_split(cur,today)
    try:
        post_batch(cur,today,rows);return dict(status='FAIL',variant=variant,note='posted')
    except AssertionError as exc:
        return verdict(dict(refused_at_validation=expected in str(exc)),variant=variant,errors=str(exc)[:1500])


# ---------------------------------------------------------------- registration

PLAN=[('F:P02_SETTLE_AND_REVERSE','NO_ROUTE',lambda c,t:settle_cycle(c,t,'SUPPLIER_PAYABLE')),
      ('F:S01_SETTLE_AND_REVERSE','NO_ROUTE',lambda c,t:settle_cycle(c,t,'CUSTOMER_RECEIVABLE')),
      ('F:W05_VENDOR_PAYABLE_SETTLE_AND_REVERSE','NO_ROUTE',lambda c,t:settle_cycle(c,t,'VENDOR_PAYABLE')),
      ('F:OSS_OVER_REMAINING_REFUSED','NO_ROUTE',lambda c,t:settle_refusal(c,t,'OVER')),
      ('F:OSS_BEFORE_CUTOVER_REFUSED','NO_ROUTE',lambda c,t:settle_refusal(c,t,'BEFORE_CUTOVER')),
      ('F:OSS_FUTURE_REFUSED','NO_ROUTE',lambda c,t:settle_refusal(c,t,'FUTURE')),
      ('F:OSS_DIRECT_BEFORE_CUTOVER','COUNTEREXAMPLE',lambda c,t:direct_date_finding(c,t,'BEFORE_CUTOVER')),
      ('F:OSS_DIRECT_FUTURE_CONTROL','PASS',lambda c,t:direct_date_finding(c,t,'FUTURE')),
      ('F:OSS_DATED_CAPACITY','COUNTEREXAMPLE',lambda c,t:dated_capacity(c,t,True)),
      ('F:OSS_DATED_CAPACITY_ORDERED_CONTROL','PASS',lambda c,t:dated_capacity(c,t,False)),
      ('F:S01_CUSTOMER_ALLOWANCE','NO_ROUTE',lambda c,t:allowance(c,t,'CUSTOMER_ALLOWANCE')),
      ('F:P02_SUPPLIER_ALLOWANCE','NO_ROUTE',lambda c,t:allowance(c,t,'SUPPLIER_ALLOWANCE')),
      ('F:W05_VENDOR_ALLOWANCE','NO_ROUTE',lambda c,t:allowance(c,t,'VENDOR_ALLOWANCE')),
      ('F:A03_LEGACY_DOCUMENT_NO_LEDGER','NO_ROUTE',lambda c,t:legacy_document(c,t,'POSTED')),
      ('F:A03_LEGACY_THEN_OPEN_LATER_BATCH_REFUSED','NO_ROUTE',lambda c,t:legacy_document(c,t,'LATER_BATCH_OPEN')),
      ('F:A03_LEGACY_AND_OPEN_SAME_BATCH_REFUSED','NO_ROUTE',lambda c,t:legacy_document(c,t,'SAME_BATCH_OPEN')),
      ('F:A03_LEGACY_NOT_SETTLED_REFUSED','NO_ROUTE',lambda c,t:legacy_document(c,t,'NOT_SETTLED')),
      ('F:S03_IMPORTED_CREDIT_REFUND_CYCLE','NO_ROUTE',imported_credit),
      ('F:S03_CREDIT_APPLIED_TO_OPENING_AR','NO_ROUTE',credit_apply),
      ('F:S03_RETURN_RIGHT_OPEN_INVOICE','NO_ROUTE',lambda c,t:return_right(c,t,'OPEN')),
      ('F:S03_RETURN_RIGHT_LEGACY_INVOICE','NO_ROUTE',lambda c,t:return_right(c,t,'LEGACY')),
      ('F:S03_RETURN_WITHOUT_INVOICE_REFUSED','NO_ROUTE',return_without_invoice),
      ('F:Y01_OPENING_PAYABLE_THROUGH_PAYROLL','NO_ROUTE',y01_payroll),
      ('F:Y01_OVER_AVAILABLE_REFUSED','NO_ROUTE',y01_over),
      ('P:P03_RECEIPT_PART_INVOICED','NO_ROUTE',p03_split),
      ('P:P03_INVOICE_DOCUMENT_REQUIRED','NO_ROUTE',lambda c,t:p03_refusal(c,t,'NO_DOCUMENT')),
      ('P:P03_STOCK_COST_NOT_BLENDED_REFUSED','NO_ROUTE',lambda c,t:p03_refusal(c,t,'NOT_BLENDED')),
      ('P:P03_QUANTITY_EQUATION_REFUSED','NO_ROUTE',lambda c,t:p03_refusal(c,t,'EQUATION'))]
assert len({k for k,_,_ in PLAN})==len(PLAN),'BB_DUPLICATE_CASE_ID'


def cases(cur,today):
    return [(key,lambda f=fn:f(cur,today)) for key,_,fn in PLAN]


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    r1.OUT=OUT
    planned={k:(e if isinstance(e,tuple) else (e,)) if phase=='before' else ('PASS',) for k,e,_ in PLAN}
    report=dict(status='INCOMPLETE',label=LABEL,phase=phase,source=r1.source(),production_go=False,independent_acceptance=False,release_evidence=False,
                planned={k:list(v) for k,v in planned.items()})
    report['run_identity']=run_identity.announce(LABEL,phase=phase)
    r1.save('RESULT_'+phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
        report['au_install']=awp.au_runtime.change('install',boundary.PG,control_url)['status']
        report['av_install']=awp.av_runtime.change('install',boundary.PG,control_url)['status']
        report['aw_install']=awp.install_aw();report['ax_install']=axp.install_ax();report['ay_install']=ayp.install_ay()
        report['az_install']=azp.install_az();report['ba_install']=bap.install_ba();verify=bap.ba_verified
        if phase=='after':report['bb_install']=install_bb();verify=bb_verified
        r1.save('RESULT_'+phase.upper(),report)
        print(json.dumps(dict(bb_probe_setup={k:report.get(k) for k in ('au_install','av_install','ba_install','bb_install')}),default=str),flush=True)
        group=r1.group('BB_CASES_'+phase.upper(),cases,verify)
        report['bb_cases']={k:group[k] for k in ('status','counts')}
        final={k:v['status'] for k,v in group['cases'].items()}
        report['final']=final
        report['expectation_mismatch']={k:dict(planned=list(e),final=final.get(k)) for k,e in planned.items() if final.get(k) not in e}
        report['status']='REVIEW_COMPLETE' if group['status']!='INCOMPLETE' and not report['expectation_mismatch'] else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_'+phase.upper(),report)
    print(json.dumps(dict(bb_probe_phase=phase,**{k:v for k,v in report.items() if k!='source'}),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error') or ('BB_PROBE_EXPECTATION_MISMATCH',report.get('expectation_mismatch'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('before','after'),required=True)
    run(parser.parse_args().phase)
