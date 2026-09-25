"""BB T1_FAMILY probe: the open cutover states of ALL (owner decision 25 Sep 2026, every ALL state built and tested in CP6),
before and after: the financial part (ALL-P02/S01/S03/A03/Y01 and the opening settlement facade), the purchase and labour
parts (ALL-P03/P04/Y02) and the production part (ALL-W02/W04/W06).

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
import argparse,hashlib,json,os,re,subprocess,sys,tempfile,traceback,uuid
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
                   'nama kolom atau tipe data tidak valid','Aksi hasil WIP tidak dikenal','Hasil kerja mandor wajib terkait Potongan')


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
    # A function a later T1 family replaced (cp6_layers) is verified by that family, not against BB's text.
    later=awp.layers.superseded(cur,after=bb.VERSION)
    later_names={s.split('(')[0] for s in later}   # BB lists its own new functions by name, a later family by signature
    for name in bb_functions():
        if name.split('(')[0] in later_names:continue
        rows=cur.execute("select p.oid::regprocedure::text,p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.proname=%s",
                         tuple(name.split('(')[0].split('.'))).fetchall()
        assert len(rows)==1,('BB_T1_FUNCTION_NOT_UNIQUE',name,[r[0] for r in rows])
        assert rows[0][1]==dev_source(name),('BB_T1_FUNCTION_NOT_CURRENT',name)
    for table in bb.NEW_TABLES:
        assert cur.execute('select to_regclass(%s) is not null',('erp.'+table,)).fetchone()[0],('BB_T1_TABLE_MISSING',table)
    result=dict(base,stage='AV_PLUS_AW_AX_AY_AZ_BA_BB_T1',bb_sql_sha256=hashlib.sha256(BB_SQL.read_bytes()).hexdigest(),
                bb_functions=list(bb_functions()))
    replaced=sorted(n for n in bb_functions() if n.split('(')[0] in later_names)
    if replaced:result['bb_replaced_by_later_family']=replaced
    return result


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
    paid_clean,paid_detectors=truth_clean(cur)
    cur.execute('grant usage on schema erp to authenticated');bap.api.ordinary(cur)
    cur.execute('select erp.reverse_paid_payroll(%s,%s)',(p,'BB probe payroll reversal'));api.admin(cur)
    restored=dict(bank=bank(cur,fx)-before_bank,upah=balance_row(cur,fx,'UPAH-OLD')[2],reimb=balance_row(cur,fx,'REIMB-OLD')[2],
                  kasbon=balance_row(cur,fx,'KASBON-OLD')[2])
    clean,detectors=truth_clean(cur)
    return verdict(dict(net_30=net==D('30.00'),no_second_accrual=accruals==0,bank_minus_30=paid['bank']==D('-30.00'),
                        payables_settled=paid['upah']==0 and paid['reimb']==0,advance_settled=paid['kasbon']==0,
                        reserved_cash_settle_refused=over['ok'],detectors_zero_when_paid=paid_clean,
                        restored=restored==dict(bank=D(0),upah=D('40.00'),reimb=D('20.00'),kasbon=D('30.00')),
                        ledger_restored=moved(before,gl(cur))=={},detectors_zero=clean),
                   paid={k:str(v) for k,v in paid.items()},restored={k:str(v) for k,v in restored.items()},net=str(net),detectors=[paid_detectors,detectors],
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


# ---------------------------------------------------------------- P04: purchase orders open at cutover

def p04_rows(cutover,ordered='10',received='0',cancelled='0',remaining='10'):
    return {'SUPPLIER':[dict(supplier_code='{C}',supplier_name='BB P04 supplier',supplier_type='MATERIAL')],
            'LOCATION':[dict(location_code='{C}',location_name='BB P04 gudang',location_type='RAW_MATERIAL_WAREHOUSE')],
            'MATERIAL':[dict(material_sku='{C}',material_name='BB P04 benang',material_type='OTHER',unit_code='PCS')],
            'OPEN_PURCHASE_ORDER':[dict(po_number='PO-{C}',po_line_number='1',po_date=str(cutover-timedelta(days=5)),supplier_code='{C}',
                                        location_code='{C}',material_sku='{C}',ordered_qty=ordered,received_before_cutover_qty=received,
                                        cancelled_before_cutover_qty=cancelled,remaining_qty=remaining,unit_price='3')]}


def p04_draft(cur,batch):
    commitment=ws(cur,batch)['purchase_commitments'][0]
    drafts=[d for d in commitment['drafts'] if d['status']=='DRAFT']
    return commitment,(drafts[0] if drafts else None)


def p04_save(cur,draft,material,supplier,location,qty,at):
    payload=dict(id=draft['purchase_id'],purchase_number=draft['purchase_number'],supplier_id=supplier,physical_at=at,location_id=location,
                 change_reason='BB P04 real receipt',lines=[dict(material_id=material,qty=str(qty),unit_price='3')])
    return receipt_trial.rpc(api,cur,'save_material_purchase_draft_v2',json.dumps(payload,default=str),uuid.uuid4(),int(draft['row_version']))


def p04_post(cur,purchase):
    api.admin(cur)
    version=cur.execute('select row_version from erp.material_purchase_headers where id=%s',(purchase,)).fetchone()[0]
    return receipt_trial.rpc(api,cur,'post_material_purchase_v2',purchase,uuid.uuid4(),version,'BB P04 post receipt')


def p04_cycle(cur,today):
    """ALL-P04 (auditor: "Define an unreceived purchase order and a partially received draft at cutover; map remaining quantity,
    original identity, approval and cancellation without receiving stock again")."""
    cutover=today-timedelta(days=10);rows=p04_rows(cutover)
    if not bb_installed(cur):
        code='BB'+uuid.uuid4().hex[:12]
        batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(cutover)))['batch_id']
        line={k:(v.replace('{C}',code) if isinstance(v,str) else v) for k,v in rows['OPEN_PURCHASE_ORDER'][0].items()}
        return no_route(cur,lambda:api.upload(cur,batch,'OPEN_PURCHASE_ORDER',[line]))
    before=gl(cur)
    batch,code,cutover=post_batch(cur,today,rows)
    api.admin(cur)
    supplier,material,location=[str(x) for x in cur.execute('''select s.id,m.id,l.id from erp.suppliers s,erp.materials m,erp.locations l
        where s.supplier_code=%s and m.material_sku=%s and l.location_code=%s''',(code,code,code)).fetchone()]
    stock=lambda:cur.execute('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s',(material,)).fetchone()[0]
    import_delta=moved(before,gl(cur));stock_import=stock()
    commitment,draft=p04_draft(cur,batch)
    draft_qty=cur.execute('select sum(qty) from erp.material_purchase_items where purchase_id=%s',(draft['purchase_id'],)).fetchone()[0]
    now_at=str(now(cur))
    p04_save(cur,draft,material,supplier,location,6,now_at);p04_post(cur,draft['purchase_id'])
    api.admin(cur);after_first=moved(before,gl(cur));stock_first=stock()
    remaining_first=p04_draft(cur,batch)[0]['lines'][0]['remaining_qty']
    act(cur,'PURCHASE_COMMITMENT',batch,operation='REOPEN_REMAINDER',commitment_id=commitment['id'],reason='BB P04 remainder')
    _,reopened=p04_draft(cur,batch)
    reopened_qty=cur.execute('select sum(qty) from erp.material_purchase_items where purchase_id=%s',(reopened['purchase_id'],)).fetchone()[0]
    p04_save(cur,reopened,material,supplier,location,5,now_at);_,reopened=p04_draft(cur,batch)
    over=refused(cur,lambda:p04_post(cur,reopened['purchase_id']),'P04_EXCEEDS_REMAINING')
    p04_save(cur,reopened,material,supplier,location,4,str(cutover-timedelta(days=1))+'T10:00:00+07:00');_,reopened=p04_draft(cur,batch)
    early=refused(cur,lambda:p04_post(cur,reopened['purchase_id']),'P04_BEFORE_CUTOVER')
    act(cur,'PURCHASE_COMMITMENT',batch,operation='CANCEL',commitment_id=commitment['id'],line_id=commitment['lines'][0]['id'],qty='4',
        effective_date=str(today),reason='BB P04 supplier cannot deliver the rest')
    p04_save(cur,reopened,material,supplier,location,4,now_at);_,reopened=p04_draft(cur,batch)
    after_cancel=refused(cur,lambda:p04_post(cur,reopened['purchase_id']),'P04_EXCEEDS_REMAINING')
    delete=refused(cur,lambda:(api.admin(cur),cur.execute('delete from erp.material_purchase_headers where id=%s',(reopened['purchase_id'],))),'P04_DELETE_USE_CANCEL')
    receipt_trial.rpc(api,cur,'reverse_material_purchase',draft['purchase_id'],'BB P04 reverse the receipt')
    remaining_reversed=p04_draft(cur,batch)[0]['lines'][0]['remaining_qty']
    api.admin(cur);stock_reversed=stock();detectors=detectors_ok(cur)
    grni=account(cur,'GRNI_MATERIAL');inventory=account(cur,'MATERIAL_INVENTORY')
    return verdict(dict(nothing_posted_at_import=import_delta=={} and stock_import==0,draft_for_remaining=draft_qty==10,
                        receive_six=stock_first==6 and after_first.get(grni)=='-18.00' and after_first.get(inventory)=='18.00',
                        remaining_four=D(remaining_first)==4,reopened_four=reopened_qty==4,over_remaining_refused=over['ok'],
                        before_cutover_refused=early['ok'],after_cancel_refused=after_cancel['ok'],delete_refused=delete['ok'],
                        reversal_restores_remaining=D(remaining_reversed)==6 and stock_reversed==0,detectors_zero=detectors is True),
                   import_delta=import_delta,after_first=after_first,remaining=[remaining_first,remaining_reversed],detectors=detectors,
                   refusals=[over['refusal'],early['refusal'],after_cancel['refusal'],delete['refusal']])


def p04_refusal(cur,today,variant):
    cutover=today-timedelta(days=10)
    if not bb_installed(cur):return p04_cycle(cur,today)
    if variant=='EQUATION':
        try:post_batch(cur,today,p04_rows(cutover,ordered='10',received='3',remaining='8'));return dict(status='FAIL',note='posted')
        except AssertionError as exc:return verdict(dict(refused_at_validation='P04_REMAINING_EQUATION' in str(exc)),errors=str(exc)[:1200])
    batch,code,cutover=post_batch(cur,today,p04_rows(cutover))
    second={'OPEN_PURCHASE_ORDER':[dict(po_number='PO-'+code,po_line_number='1',po_date=str(cutover-timedelta(days=5)),supplier_code=code,
                                         location_code=code,material_sku=code,ordered_qty='2',received_before_cutover_qty='0',
                                         cancelled_before_cutover_qty='0',remaining_qty='2',unit_price='3')]}
    try:post_batch(cur,today,second,cutover_days=5);return dict(status='FAIL',note='posted twice')
    except AssertionError as exc:return verdict(dict(refused_at_validation='P04_DUPLICATE_PO' in str(exc)),errors=str(exc)[:1200])


# ---------------------------------------------------------------- S02: sales drafts open at cutover

def s02_rows(cutover,drafts=(('SD-{C}','3'),),stock='10',draft_date=None):
    """Opening finished goods of `stock` pcs of product {C}P in warehouse {C}G at 6.00 and one OPEN_SALES_DRAFT line per
    (draft number, pcs) at 10.00/pcs for customer {C}, drafted before cutover."""
    rows=product_masters()
    rows['CUSTOMER']=[dict(customer_code='{C}',customer_name='BB pelanggan draf')]
    rows['OPENING_BALANCE_ITEM']=[dict(balance_type='FINISHED_GOODS',product_sku='{C}P',brand_code='{C}',model_code='{C}',color_name='Blue',
                                       size_code='{C}',location_code='{C}G',qty=stock,unit_cost='6.00',control_key='FG')]
    rows['OPENING_CONTROL']=[dict(control_key='FG',balance_type='FINISHED_GOODS',qty=stock,amount=str(D(stock)*6)+'.00')]
    day=str(draft_date or cutover-timedelta(days=3))
    rows['OPEN_SALES_DRAFT']=[dict(draft_number=n,line_number='1',draft_date=day,customer_code='{C}',location_code='{C}G',
                                   product_sku='{C}P',qty_pcs=q,unit_price='10.00') for n,q in drafts]
    return rows


def s02_free(cur,code):
    """Pieces of {C}P in {C}G not held by anything: the official stock ledger after reservations (M:3821)."""
    api.admin(cur)
    return cur.execute("""select coalesce(sum(m.qty_signed),0)::integer from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
      join erp.locations l on l.id=m.location_id where p.sku=%s and l.location_code=%s""",(code+'P',code+'G')).fetchone()[0]


def s02_sale(cur,code,number=None):
    api.admin(cur)
    return cur.execute("""select h.id,h.status,h.row_version,h.sale_date,h.customer_id,h.source_location_id from erp.sales_headers h
      where h.sale_number=%s""",(number or 'SD-'+code,)).fetchone()


def s02_reserves(cur,sale):
    api.admin(cur)
    return cur.execute("""select count(*),coalesce(-sum(m.qty_signed),0)::integer from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
      where i.sale_id=%s and m.movement_type='SALE_RESERVE' and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)""",
      (sale,)).fetchone()


def s02_save(cur,sale,code,qty,sale_date,customer=None):
    """The native draft edit (erp.save_sale_draft_v2) by the owner with the draft's current version."""
    h=s02_sale(cur,code);api.admin(cur)
    product=cur.execute('select id from erp.products where sku=%s',(code+'P',)).fetchone()[0]
    payload=dict(sale_id=str(sale),sale_number='SD-'+code,customer_id=str(customer or h[4]),source_location_id=str(h[5]),sale_date=sale_date,
                 reason='BB S02 edit of the carried draft',items=[dict(product_id=str(product),qty_pcs=qty,unit_price_snapshot=10,discount_amount=0)])
    chain.production.owner(cur)
    return cur.execute('select erp.save_sale_draft_v2(%s::jsonb,%s,%s)',(json.dumps(payload),uuid.uuid4(),h[2])).fetchone()[0]


def s02_cycle(cur,today):
    """ALL-S02 (auditor r9: "physical finished goods 10 PCS with an existing official reservation of 3 PCS against one identified
    sales draft. After cutover edit reservation from 3 to 2 ... availability = 10-3 = 7 ... edit 3->2 releases exactly 1 ...
    posting removes actual fulfilled qty exactly once"; Fable S02: reserve once (M:3821), no false physical date).
    Oracle: the import makes one native DRAFT numbered SD-{C} for customer {C}, dated at cutover (not the old draft date),
    reserving 3 once (free 7), no journal from the draft; the native edit to 2 dated today leaves free 8 with one active
    reservation of 2; the native POST keeps free 8 (no second stock-out) and books receivable/revenue 20.00 and cost 12.00
    once; a date before cutover or another customer is refused on the carried draft; deleting it is refused."""
    cutover=today-timedelta(days=10);rows=s02_rows(cutover)
    if not bb_installed(cur):
        code='BB'+uuid.uuid4().hex[:12]
        batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(cutover)))['batch_id']
        line={k:(v.replace('{C}',code) if isinstance(v,str) else v) for k,v in rows['OPEN_SALES_DRAFT'][0].items()}
        return no_route(cur,lambda:api.upload(cur,batch,'OPEN_SALES_DRAFT',[line]))
    batch,code,cutover=post_batch(cur,today,rows)
    api.admin(cur)
    sale,status,version,sale_date,customer,location=s02_sale(cur,code)
    cutover_at=cur.execute('select cutover_at from erp.migration_batches where id=%s',(batch,)).fetchone()[0]
    draft_journals=cur.execute("""select count(*) from erp.journal_entries j where j.source_id=%s or j.source_id in(select id from erp.sales_items where sale_id=%s)""",
                               (sale,sale)).fetchone()[0]
    registry=cur.execute('select draft_number,draft_date from erp.bb_open_sales_drafts_v1 where sale_id=%s',(sale,)).fetchone()
    imported=dict(status=status,free=s02_free(cur,code),reserves=s02_reserves(cur,sale),sale_date_is_cutover=sale_date==cutover_at,
                  registry=[str(x) for x in registry] if registry else None,journals=draft_journals)
    ws=[d for d in api.read(cur,batch)['batch'].get('open_sales_drafts',[]) if d['sale_id']==str(sale)]
    early=refused(cur,lambda:s02_save(cur,sale,code,2,str(cutover-timedelta(days=1))+'T10:00:00+07:00'),'BB_S02_DATE_BEFORE_CUTOVER')
    api.admin(cur);other=cur.execute("insert into erp.customers(customer_code,customer_name,is_active) values(%s,'BB lain',true) returning id",(code+'X',)).fetchone()[0]
    identity=refused(cur,lambda:s02_save(cur,sale,code,2,str(now(cur).isoformat()),customer=other),'BB_S02_IDENTITY')
    delete=refused(cur,lambda:(api.admin(cur),cur.execute('delete from erp.sales_headers where id=%s',(sale,))),'BB_S02_DRAFT_KEPT')
    edited=s02_save(cur,sale,code,2,now(cur).isoformat())
    after_edit=dict(free=s02_free(cur,code),reserves=s02_reserves(cur,sale))
    before=gl(cur)
    h=s02_sale(cur,code);chain.production.owner(cur)
    cur.execute('select erp.post_sale_v2(%s,%s,%s)',(sale,uuid.uuid4(),h[2]))
    api.admin(cur);posted=moved(before,gl(cur))
    after_post=dict(status=s02_sale(cur,code)[1],free=s02_free(cur,code),reserves=s02_reserves(cur,sale))
    detectors=detectors_ok(cur)
    ar,revenue,cogs,fg=[account(cur,k) for k in ('AR_CUSTOMER','SALES_REVENUE','COGS','FG_INVENTORY')]
    return verdict(dict(one_native_draft=imported['status']=='DRAFT',reserved_once=imported['reserves']==(1,3) and imported['free']==7,
                        dated_at_cutover=imported['sale_date_is_cutover'],provenance_kept=registry is not None and str(registry[1])==str(cutover-timedelta(days=3)),
                        nothing_journaled=imported['journals']==0,workspace_lists_it=len(ws)==1 and ws[0]['reserved_qty_pcs']==3,
                        date_before_cutover_refused=early['ok'],identity_refused=identity['ok'],delete_refused=delete['ok'],
                        edit_releases_one=after_edit['free']==8 and after_edit['reserves']==(1,2),
                        post_once=after_post['status']=='POSTED' and after_post['free']==8,
                        post_books_once=posted.get(ar)=='20.00' and posted.get(revenue)=='-20.00' and posted.get(cogs)=='12.00' and posted.get(fg)=='-12.00',
                        detectors_zero=detectors is True),
                   imported=imported,after_edit=after_edit,after_post=after_post,posted=posted,edited=edited,detectors=detectors,
                   refusals=[early['refusal'],identity['refusal'],delete['refusal']])


def s02_cancel(cur,today):
    """The native cancel of a carried draft releases its reservation only: free back to 10, status CANCELLED, no journal."""
    cutover=today-timedelta(days=10)
    if not bb_installed(cur):return s02_cycle(cur,today)
    batch,code,cutover=post_batch(cur,today,s02_rows(cutover))
    sale,_,version,*_=s02_sale(cur,code)
    before=gl(cur);chain.production.owner(cur)
    cur.execute('select erp.cancel_sale_draft_v2(%s,%s,%s,%s)',(sale,'BB S02 customer withdrew',uuid.uuid4(),version))
    api.admin(cur)
    return verdict(dict(released=s02_free(cur,code)==10 and s02_reserves(cur,sale)==(0,0),cancelled=s02_sale(cur,code)[1]=='CANCELLED',
                        no_journal=moved(before,gl(cur))=={}))


def s02_refusal(cur,today,variant):
    """Refused at import: two drafts reserving 6 + 5 of 10 (aggregate over the stock; the whole import rolls back), a draft
    dated after cutover, and a draft number already used by a sale."""
    cutover=today-timedelta(days=10)
    if not bb_installed(cur):return s02_cycle(cur,today)
    if variant=='OVER_STOCK':
        api.admin(cur);headers=cur.execute('select count(*) from erp.sales_headers').fetchone()[0]
        result,error=r1.peer.attempt(cur,lambda:post_batch(cur,today,s02_rows(cutover,drafts=(('SD-{C}','6'),('SE-{C}','5'))),prefix='BBS'))
        if error is None:return dict(status='FAIL',note='posted',result=str(result)[:300])
        api.admin(cur)
        return verdict(dict(refused=code_of(error)=='BB_S02_RESERVATION_REFUSED',
                            no_sale_left=cur.execute('select count(*) from erp.sales_headers').fetchone()[0]==headers),refusal=error)
    if variant=='DRAFT_AFTER_CUTOVER':
        try:post_batch(cur,today,s02_rows(cutover,draft_date=cutover+timedelta(days=1)));return dict(status='FAIL',note='posted')
        except AssertionError as exc:return verdict(dict(refused_at_validation='draf harus dibuat sebelum saldo awal' in str(exc)),errors=str(exc)[:900])
    batch,code,cutover=post_batch(cur,today,s02_rows(cutover))
    again={'OPEN_SALES_DRAFT':[dict(draft_number='SD-'+code,line_number='1',draft_date=str(cutover-timedelta(days=4)),customer_code=code,
                                    location_code=code+'G',product_sku=code+'P',qty_pcs='1',unit_price='10.00')]}
    try:post_batch(cur,today,again,cutover_days=5);return dict(status='FAIL',note='posted twice')
    except AssertionError as exc:return verdict(dict(refused_at_validation='BB_S02_DUPLICATE_DRAFT' in str(exc)),errors=str(exc)[:900])


# ---------------------------------------------------------------- Y02: earned but unapproved work before cutover

def y02_rows(cutover,attendance='true',doc_amount='134.00'):
    """Mandor Epi: sewing earned 40, paid 10, carried 4 at 2.50 (65.00 open); attendance 5.5 days x 20 less 50 paid (60.00);
    GOOD/BOM reimbursement 12 x 0.75 (9.00). One CONTRACTOR_PAYABLE document NJ-{C} of 134.00 carries the money."""
    day=str(cutover-timedelta(days=12))
    return {'CHART_ACCOUNT':[dict(account_code='{C}B',account_name='BB Y02 bank',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT')],
            'CASH_ACCOUNT':[dict(cash_account_code='{C}',cash_account_name='BB Y02 bank',coa_account_code='{C}B',account_kind='BANK')],
            'CONTRACTOR':[dict(contractor_code='{C}',contractor_name='BB Epi',contractor_type='MANDOR',attendance_required=attendance)],
            'OPENING_BALANCE_ITEM':[dict(balance_type='CONTRACTOR_PAYABLE',contractor_code='{C}',amount=doc_amount,control_key='CP',document_number='NJ-{C}',
                                         document_date=day,original_amount=str(D(doc_amount)+75),settled_before_cutover='75.00'),
                                    dict(balance_type='CASH_BANK',cash_account_code='{C}',amount='1000.00',control_key='CASH')],
            'OPENING_CONTROL':[dict(control_key='CP',balance_type='CONTRACTOR_PAYABLE',amount=doc_amount),dict(control_key='CASH',balance_type='CASH_BANK',amount='1000.00')],
            'OPENING_PAYROLL_ENTITLEMENT':[
                dict(kind='SEWING_WORK',contractor_code='{C}',document_number='NJ-{C}',line_number='1',document_date=day,rate='2.50',
                     work_component_code='{C}J',earned_qty='40',paid_before_qty='10',carry_qty='4'),
                dict(kind='ATTENDANCE',contractor_code='{C}',document_number='NJ-{C}',line_number='2',document_date=day,rate='20',
                     worker_name='Epi A',period_start=str(cutover-timedelta(days=20)),period_end=str(cutover-timedelta(days=14)),days='5.5',paid_before_amount='50'),
                dict(kind='ACCESSORY_REIMBURSEMENT',contractor_code='{C}',document_number='NJ-{C}',line_number='3',document_date=day,rate='0.75',
                     category_code='ACC',good_qty='12',paid_before_amount='0')]}


def y02_post(cur,today,**kw):
    """The Y02 fixture with its work component (a master the import does not create)."""
    cutover=today-timedelta(days=10);code='BB'+uuid.uuid4().hex[:12]
    api.admin(cur);cur.execute("insert into erp.work_components(component_code,component_name,component_category,is_active) values(%s,%s,'LABOR',true)",
                               (code+'J','BB Y02 jahit'))
    rows=y02_rows(cutover,**kw)
    boundary.historical.prior.set_open_period(cur,cutover-timedelta(days=1))
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(cutover)))['batch_id']
    for entity,payloads in rows.items():
        api.upload(cur,batch,entity,[{k:(v.replace('{C}',code) if isinstance(v,str) else v) for k,v in p.items()} for p in payloads])
    checked=api.invoke(cur,'VALIDATE',batch)
    if checked.get('error_rows')!=0:
        api.admin(cur)
        errors=cur.execute("select entity_type,validation_errors::text from erp.migration_staging_rows where batch_id=%s and validation_status='ERROR'",(batch,)).fetchall()
        raise AssertionError(('BB_FIXTURE_REFUSED',checked,errors))
    assert api.invoke(cur,'FINALIZE',batch).get('status')=='POSTED'
    api.admin(cur)
    contractor,cash=cur.execute('select c.id,k.id from erp.contractors c,erp.cash_accounts k where c.contractor_code=%s and k.cash_account_code=%s',(code,code)).fetchone()
    balance=cur.execute('''select b.id from erp.initial_import_financial_sources f join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
        where f.batch_id=%s and f.balance_type='CONTRACTOR_PAYABLE' ''',(batch,)).fetchone()[0]
    return dict(batch=batch,code=code,cutover=cutover,contractor=contractor,cash=str(cash),balances={'NJ':str(balance)})


def payroll_of(cur,fx,today,back=0):
    """A one-day payroll period `back` days before today (periods of one contractor never overlap), paid today."""
    api.admin(cur);day=today-timedelta(days=back)
    return str(cur.execute("""insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date,
        payment_cash_account_id) values(%s,%s,%s,%s,0,%s,%s) returning id""",('BBY2-'+uuid.uuid4().hex,fx['contractor'],day,day,today,fx['cash'])).fetchone()[0])


def payroll_version(cur,p):
    api.admin(cur);return str(cur.execute('select row_version from erp.payroll_settlements where id=%s',(p,)).fetchone()[0])


def payroll_call(cur,name,*args):
    api.admin(cur);cur.execute('grant usage on schema erp to authenticated');bap.api.ordinary(cur)
    cur.execute('select erp.'+name+'('+','.join(['%s']*len(args))+')',args);api.admin(cur)


def y02_cycle(cur,today):
    """ALL-Y02 (auditor: "retain unique source entitlement, partial payment and carry state, approve/pay/inverse with no synthetic
    historical production")."""
    if not bb_installed(cur):
        code='BB'+uuid.uuid4().hex[:12]
        batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=10))))['batch_id']
        return no_route(cur,lambda:api.upload(cur,batch,'OPENING_PAYROLL_ENTITLEMENT',[dict(kind='SEWING_WORK',contractor_code=code,
            document_number='NJ',line_number='1',document_date=str(today-timedelta(days=20)),rate='2.50')]))
    api.admin(cur)
    native=lambda:cur.execute('''select (select count(*) from erp.work_completion_events),(select count(*) from erp.attendance_records),
        (select count(*) from erp.contractor_accessory_reimbursement_entitlements),(select count(*) from erp.sewing_terminal_events)''').fetchone()
    native_before=native();before=gl(cur)
    fx=y02_post(cur,today)
    native_after=native();import_delta=moved(before,gl(cur))
    entitlements=ws(cur,fx['batch'])['payroll_entitlements']
    sewing=[e for e in entitlements if e['kind']=='SEWING_WORK'][0]
    bank0=bank(cur,fx)
    p1=payroll_of(cur,fx,today,2)
    act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='ALLOCATE_PAYROLL',balance_id=fx['balances']['NJ'],payroll_id=p1,amount='99.00',
        expected_payroll_version=payroll_version(cur,p1))
    payroll_call(cur,'approve_payroll',p1)
    accrual1=cur.execute("select count(*) from erp.journal_entries where source_id=%s and source_type='PAYROLL_EXTRA_ACCRUAL'",(p1,)).fetchone()[0]
    payroll_call(cur,'post_payroll_payment',p1)
    bank1=bank(cur,fx);left1=balance_row(cur,fx,'NJ')[2]
    p2=payroll_of(cur,fx,today,1)
    act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='ALLOCATE_PAYROLL',balance_id=fx['balances']['NJ'],payroll_id=p2,amount='35.00',
        expected_payroll_version=payroll_version(cur,p2))
    act(cur,'PAYROLL_ENTITLEMENT',fx['batch'],operation='ALLOCATE_CARRY',entitlement_id=sewing['id'],payroll_id=p2,qty='4',
        expected_payroll_version=payroll_version(cur,p2))
    labor=account(cur,'LABOR_COST');before_p2=gl(cur)
    payroll_call(cur,'approve_payroll',p2);payroll_call(cur,'post_payroll_payment',p2)
    p2_delta=moved(before_p2,gl(cur));bank2=bank(cur,fx);left2=balance_row(cur,fx,'NJ')[2]
    carry2=[e for e in ws(cur,fx['batch'])['payroll_entitlements'] if e['kind']=='SEWING_WORK'][0]['carry_remaining']
    p3=payroll_of(cur,fx,today)
    more=refused(cur,lambda:act(cur,'PAYROLL_ENTITLEMENT',fx['batch'],operation='ALLOCATE_CARRY',entitlement_id=sewing['id'],payroll_id=p3,qty='1',
        expected_payroll_version=payroll_version(cur,p3)),'Y02_CARRY_EXCEEDS')
    payroll_call(cur,'reverse_paid_payroll',p2,'BB Y02 reverse second payroll')
    carry3=[e for e in ws(cur,fx['batch'])['payroll_entitlements'] if e['kind']=='SEWING_WORK'][0]['carry_remaining']
    bank3=bank(cur,fx);left3=balance_row(cur,fx,'NJ')[2]
    clean,detectors=truth_clean(cur)
    payable=account(cur,'CONTRACTOR_PAYABLE')
    return verdict(dict(no_native_history=native_after==native_before,payable_134=import_delta.get(payable)=='-134.00',
                        three_entitlements=len(entitlements)==3 and D(sewing['amount'])==D('65.00') and D(sewing['carry_qty'])==4,
                        first_payroll_no_accrual=accrual1==0,first_payroll_bank=bank1==bank0-99 and left1==D('35.00'),
                        carry_recognized_at_approval=p2_delta.get(labor)=='10.00',second_payroll_bank=bank2==bank1-45 and left2==0,
                        carry_used=D(carry2)==0,carry_over_refused=more['ok'],
                        reversal_restores=D(carry3)==4 and bank3==bank1 and left3==D('35.00'),detectors_zero=clean),
                   import_delta=import_delta,p2_delta=p2_delta,bank=[str(bank0),str(bank1),str(bank2),str(bank3)],
                   remaining=[str(left1),str(left2),str(left3)],carry=[carry2,carry3],detectors=detectors,native=[native_before,native_after])


def y02_refusal(cur,today,variant):
    if not bb_installed(cur):return y02_cycle(cur,today)
    kw=dict(attendance='false') if variant=='NO_ATTENDANCE' else dict(doc_amount='130.00')
    expected='Y02_ATTENDANCE_NOT_REQUIRED' if variant=='NO_ATTENDANCE' else 'Y02_EQUATION'
    try:y02_post(cur,today,**kw);return dict(status='FAIL',variant=variant,note='posted')
    except AssertionError as exc:return verdict(dict(refused_at_validation=expected in str(exc)),variant=variant,errors=str(exc)[:1500])


# ---------------------------------------------------------------- W02/W04/W06: opening production states

PRODUCTION_STAGE_REFUSAL='stage: WIP memakai SEWING/LAUNDRY'


def production_rows(stage='SEWING',po_mandor=True,holder='{C}',bs=None,reworks=(),components=()):
    """PO {C} of model {C}: an opening WIP of 8 pcs worth 40.00 (5.00 a piece) of product {C}P at `stage` (CUTTING: waiting
    for pickup at location {C}C; otherwise held by `holder`); optionally an opening BS row `bs` (qty, holder field, holder code,
    amount) and open reworks. Masters: mandors {C} and {C}X, laundry {C}, FG warehouse {C}G, cutting location {C}C."""
    wip=dict(balance_type='WIP',po_number='{C}',model_code='{C}',size_code='{C}',stage=stage,qty='8',unit_cost='5',amount='40.00',
             opening_source_key='WIP',control_key='WIP',accessory_cost_included='true',product_sku='{C}P',brand_code='{C}',color_name='Blue')
    if stage=='CUTTING':wip['location_code']='{C}C'
    if holder and stage!='CUTTING':wip['contractor_code' if stage=='SEWING' else 'vendor_code']=holder
    if holder and stage=='CUTTING':wip['contractor_code']=holder
    po=dict(po_number='{C}',model_code='{C}',target_qty_pcs='12',status='CUTTING' if stage=='CUTTING' else stage,current_stage=stage)
    if po_mandor:po['contractor_code']='{C}'
    rows=product_masters()
    rows['LOCATION'].append(dict(location_code='{C}C',location_name='BB meja potong',location_type='CUTTING_WIP'))
    rows.update(CONTRACTOR=[dict(contractor_code='{C}',contractor_name='BB mandor W',contractor_type='MANDOR'),
                            dict(contractor_code='{C}X',contractor_name='BB mandor lain',contractor_type='MANDOR')],
                LAUNDRY_VENDOR=[dict(vendor_code='{C}',vendor_name='BB laundry W')],OPEN_PO=[po])
    items=[wip];controls=[dict(control_key='WIP',balance_type='WIP',qty='8',amount='40.00')]
    if bs:
        qty,field,code,amount=bs
        items.append({'balance_type':'BS','po_number':'{C}','model_code':'{C}','size_code':'{C}','stage':'QC','qty':qty,'amount':amount,
                      'opening_source_key':'BS','control_key':'BS','accessory_cost_included':'true','product_sku':'{C}P','brand_code':'{C}',
                      'color_name':'Blue',field:code})
        controls.append(dict(control_key='BS',balance_type='BS',qty=qty,amount=amount))
    rows.update(OPENING_BALANCE_ITEM=items,OPENING_CONTROL=controls)
    if reworks:rows['OPENING_REWORK']=list(reworks)
    if components:rows['OPENING_REWORK_COMPONENT']=list(components)
    return rows


def production_post(cur,today,rows,code=None,cutover_days=10,expect=None):
    """post_batch for a fixed code (masters prepared before the import can name it); `expect` returns the VALIDATE errors."""
    cutover=today-timedelta(days=cutover_days)
    boundary.historical.prior.set_open_period(cur,cutover-timedelta(days=1))
    code=code or 'BW'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(cutover)))['batch_id']
    fill=lambda v:v.replace('{C}',code) if isinstance(v,str) else v
    for entity,payloads in rows.items():
        api.upload(cur,batch,entity,[{k:fill(v) for k,v in p.items()} for p in payloads])
    checked=api.invoke(cur,'VALIDATE',batch)
    api.admin(cur)
    errors=cur.execute("select entity_type,validation_errors::text from erp.migration_staging_rows where batch_id=%s and validation_status='ERROR'",(batch,)).fetchall()
    if expect is not None:return dict(batch=batch,code=code,errors=[list(e) for e in errors])
    if checked.get('error_rows')!=0:raise AssertionError(('BB_FIXTURE_REFUSED',checked,errors))
    posted=api.invoke(cur,'FINALIZE',batch)
    assert posted.get('status')=='POSTED',('BB_FIXTURE_NOT_POSTED',posted)
    api.admin(cur)
    po,fg=cur.execute("""select (select id from erp.production_orders where po_number=%s),(select id from erp.locations where location_code=%s)""",
                      (code,code+'G')).fetchone()
    return dict(batch=batch,code=code,cutover=cutover,po=str(po) if po else None,fg=str(fg) if fg else None)


def source_of(cur,fx,kind='WIP'):
    return [s for s in ws(cur,fx['batch'])['production_sources'] if s['balance_type']==kind][0]


def wip_op(cur,fx,operation,**kw):
    s=source_of(cur,fx)
    return api.call(cur,'WIP_OUTPUT',dict(batch_id=fx['batch'],opening_item_id=s['opening_item_id'],expected_remaining=str(s['remaining_qty_pcs']),
                                          operation=operation,reason='BB W probe '+operation.lower(),**kw))


def complete(cur,fx,day,qty):
    return wip_op(cur,fx,'COMPLETE',qty_pcs=str(qty),product_sku=fx['code']+'P',brand_code=fx['code'],location_code=fx['code']+'G',date=str(day))


def split(cur,fx,day,qty):
    return wip_op(cur,fx,'SPLIT_BS',qty_pcs=str(qty),product_sku=fx['code']+'P',brand_code=fx['code'],date=str(day))


def stage_minimum(cur,po,stage):
    """The auditor's SI-02 oracle per stage: pieces in `stage` after every physical event of the PO (physical time, then creation)."""
    api.admin(cur)
    return cur.execute("""with e as (select id,physical_at,created_at,case when stage_to=%s then qty_pcs else 0 end-case when stage_from=%s then qty_pcs else 0 end delta
        from erp.wip_stage_events where po_id=%s)
      select coalesce(min(s),0) from (select sum(delta) over(order by physical_at,created_at,id) s from e) x""",(stage,stage,po)).fetchone()[0]


def production_clean(cur):
    """Every financial report check (WIP source conservation, PO HPP book, opening lineage ...) and every BS/rework integrity
    check is zero; the purchase/payment truth checks too."""
    api.admin(cur)
    report=[list(r) for r in cur.execute('select check_name,issue_count from erp.run_v268_financial_report_checks() where issue_count<>0').fetchall()]
    rework=[list(r[:3]) for r in cur.execute('select * from erp.run_v263c_bs_rework_integrity_checks() where issue_count<>0').fetchall()]
    purchase=detectors_ok(cur)
    return (not report and not rework and purchase is True),dict(report=report,rework=rework,purchase=purchase)


def lot_cost(cur,lot):
    api.admin(cur)
    return cur.execute('select total_cost from erp.hpp_versions where lot_id=%s and is_current',(lot,)).fetchone()[0]


def ledger(cur,mapping,po):
    api.admin(cur)
    return cur.execute("""select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
      where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id(%s) and l.po_id=%s""",(mapping,po)).fetchone()[0]


def bs_act(cur,action,payload,version):
    api.ordinary(cur)
    r=cur.execute('select public.erp_save_bs_resolution_action_v1(%s,%s::jsonb,%s,%s)',(action,json.dumps(payload,default=str),uuid.uuid4(),version)).fetchone()[0]
    api.admin(cur);return r['result']


def bs_version(cur,case):
    api.admin(cur);return cur.execute('select row_version from erp.bs_cases where id=%s',(case,)).fetchone()[0]


def empty_accessory_bom(cur,code,day):
    api.admin(cur)
    cur.execute("""insert into erp.accessory_bom_versions(product_id,effective_from,notes) select p.identity_root_id,%s,'BB W probe: explicit empty BOM'
      from erp.products p where p.sku=%s""",(chain.production.at(day,0),code+'P'))


def production_before(cur,today,stage='CUTTING'):
    """Phase 'before' of W04: a WIP waiting for pickup (stage CUTTING) is refused by the production validator as an unknown
    stage, so nothing can be imported (the §29.6 NO_ADAPTER state)."""
    out=production_post(cur,today,production_rows(stage=stage,po_mandor=False,holder=None),expect=True)
    hit=any(PRODUCTION_STAGE_REFUSAL in e[1] for e in out['errors'])
    return dict(status='NO_ROUTE' if hit else 'INCOMPLETE',errors=out['errors'])


def w04_cycle(cur,today):
    """ALL-W04 (auditor: cut pieces waiting for pickup at cutover). Oracle: the 8 cut pieces are opening WIP at the cutting
    location without a mandor; nothing is completed or split before a pickup (not even dated before it); the pickup hands
    them to one mandor (the PO takes it), the output after it carries the per-piece opening value 5.00; no stage goes
    negative on any day; the pickup cannot be undone while an output exists and, once undone, the pieces wait again and the
    PO's mandor is released; every report check stays zero."""
    if not bb_installed(cur):return production_before(cur,today)
    fx=production_post(cur,today,production_rows(stage='CUTTING',po_mandor=False,holder=None))
    s0=source_of(cur,fx);c=fx['cutover']
    early=refused(cur,lambda:complete(cur,fx,c+timedelta(days=1),3),'BB_WIP_NOT_PICKED_UP')
    early_split=refused(cur,lambda:split(cur,fx,c+timedelta(days=1),1),'BB_WIP_NOT_PICKED_UP')
    wip_op(cur,fx,'PICKUP',contractor_code=fx['code'],date=str(c+timedelta(days=2)))
    api.admin(cur);po_mandor=cur.execute('select c.contractor_code from erp.production_orders p join erp.contractors c on c.id=p.contractor_id where p.id=%s',(fx['po'],)).fetchone()
    s1=source_of(cur,fx)
    before_pickup=refused(cur,lambda:complete(cur,fx,c+timedelta(days=1),3),'BB_WIP_NOT_PICKED_UP')
    out=complete(cur,fx,c+timedelta(days=3),5)
    cost=lot_cost(cur,out['lot_id']);clean1,d1=production_clean(cur)
    minima=dict(cutting=stage_minimum(cur,fx['po'],'CUTTING'),sewing=stage_minimum(cur,fx['po'],'SEWING'))
    blocked=refused(cur,lambda:wip_op(cur,fx,'REVERSE_PICKUP'),'BB_WIP_PICKUP_HAS_DOWNSTREAM')
    wip_op(cur,fx,'REVERSE',output_id=out['output_id'])
    undo=wip_op(cur,fx,'REVERSE_PICKUP')
    s2=source_of(cur,fx)
    api.admin(cur);po_after=cur.execute('select contractor_id from erp.production_orders where id=%s',(fx['po'],)).fetchone()[0]
    again=refused(cur,lambda:wip_op(cur,fx,'PICKUP',contractor_code=fx['code'],date=str(c+timedelta(days=2))),'BB_WIP_PICKUP_DATE')
    minima_end=dict(cutting=stage_minimum(cur,fx['po'],'CUTTING'),sewing=stage_minimum(cur,fx['po'],'SEWING'))
    clean2,d2=production_clean(cur)
    return verdict(dict(
        imported_waiting=s0['stage']=='CUTTING' and s0['current_stage']=='CUTTING' and s0['remaining_qty_pcs']==8 and s0['contractor_name'] is None
          and s0['location_code']==fx['code']+'C',
        nothing_before_pickup=early['ok'] and early_split['ok'],pickup_to_mandor=s1['current_stage']=='SEWING' and s1['contractor_name']=='BB mandor W'
          and po_mandor==(fx['code'],),no_output_dated_before_pickup=before_pickup['ok'],output_value=D(cost)==D('25.00'),
        stages_never_negative=min(minima.values())>=0 and min(minima_end.values())>=0,pickup_locked_by_output=blocked['ok'],
        undo_waits_again=s2['current_stage']=='CUTTING' and s2['remaining_qty_pcs']==8 and undo.get('po_contractor_released') is True and po_after is None,
        repickup_not_before_return=again['ok'],reports_zero=clean1 and clean2),
        sources=[s0,s1,s2],minima=[minima,minima_end],lot_cost=str(cost),detectors=[d1,d2],refusals=[early,early_split,before_pickup,blocked,again])


def w04_other_mandor(cur,today):
    """A PO that already has mandor {C}: pickup by another mandor is refused (as a native pickup, the PO's mandor owns cost
    and payroll); the PO's own mandor may pick up."""
    if not bb_installed(cur):return production_before(cur,today)
    fx=production_post(cur,today,production_rows(stage='CUTTING',po_mandor=True,holder=None))
    other=refused(cur,lambda:wip_op(cur,fx,'PICKUP',contractor_code=fx['code']+'X',date=str(fx['cutover']+timedelta(days=1))),'BB_WIP_PO_OTHER_MANDOR')
    own=wip_op(cur,fx,'PICKUP',contractor_code=fx['code'],date=str(fx['cutover']+timedelta(days=1)))
    return verdict(dict(other_refused=other['ok'],own_allowed=own.get('po_contractor_assigned') is False),refusal=other['refusal'],pickup=own)


def w04_holder_refused(cur,today):
    """A cutting WIP row naming a mandor is refused at validation (pieces waiting for pickup are held by nobody yet)."""
    if not bb_installed(cur):return production_before(cur,today)
    out=production_post(cur,today,production_rows(stage='CUTTING',po_mandor=False,holder='{C}'),expect=True)
    return verdict(dict(refused=any('BB_CUTTING_WIP_HOLDER' in e[1] for e in out['errors'])),errors=out['errors'])


def w02_split_dispose(cur,today):
    """ALL-W02 (auditor: BS from opening WIP). Oracle: 2 of 8 opening SEWING pieces split off as a native BS case (LEGACY,
    cause UNKNOWN, traced to the split, holder recorded) leave 6 to complete; their 10.00 stays in WIP until the native
    DISPOSE_BS scraps them (WIP -10.00, OTHER_EXPENSE +10.00 on the PO); reversing the disposition restores it; the split can
    be undone only once the case has no resolution; stages never negative; every report check stays zero."""
    if not bb_installed(cur):
        fx=production_post(cur,today,production_rows())
        return no_route(cur,lambda:split(cur,fx,fx['cutover']+timedelta(days=2),2))
    fx=production_post(cur,today,production_rows());c=fx['cutover']
    wip0=ledger(cur,'WIP',fx['po']);exp0=ledger(cur,'OTHER_EXPENSE',fx['po'])
    made=split(cur,fx,c+timedelta(days=2),2)
    s1=source_of(cur,fx);sp=s1['bb']['splits'][0]
    api.admin(cur)
    case=cur.execute('''select id,untracked_type,cause_source,legacy_reference,detected_at_stage,qty_pcs,status,
        (select contractor_code from erp.contractors where id=responsible_contractor_id) from erp.bs_cases where id=%s''',(sp['bs_case_id'],)).fetchone()
    clean1,d1=production_clean(cur)
    disposed=bs_act(cur,'DISPOSE_BS',dict(bs_case_id=sp['bs_case_id'],resolution_type='SCRAP',qty_pcs=2,physical_at=chain.production.at(c+timedelta(days=3),10),
                                         change_reason='BB W02 scrap split BS'),bs_version(cur,sp['bs_case_id']))
    wip1=ledger(cur,'WIP',fx['po']);exp1=ledger(cur,'OTHER_EXPENSE',fx['po']);clean2,d2=production_clean(cur)
    locked=refused(cur,lambda:wip_op(cur,fx,'REVERSE_SPLIT',split_id=sp['id']),'BB_WIP_SPLIT_HAS_DOWNSTREAM')
    bs_act(cur,'REVERSE_DISPOSITION',dict(resolution_id=disposed['bs_resolution_id'],change_reason='BB W02 undo scrap'),bs_version(cur,sp['bs_case_id']))
    wip2=ledger(cur,'WIP',fx['po']);exp2=ledger(cur,'OTHER_EXPENSE',fx['po'])
    wip_op(cur,fx,'REVERSE_SPLIT',split_id=sp['id'])
    s2=source_of(cur,fx)
    api.admin(cur);status=cur.execute('select status from erp.bs_cases where id=%s',(sp['bs_case_id'],)).fetchone()[0]
    minimum=min(stage_minimum(cur,fx['po'],'SEWING'),stage_minimum(cur,fx['po'],'QC'))
    clean3,d3=production_clean(cur)
    return verdict(dict(
        split_case_native=case[1:7]==('LEGACY','UNKNOWN','OPENING_SPLIT:'+made['output_id'],'QC',2,'OPEN') and case[7]==fx['code'],
        remaining_six=s1['remaining_qty_pcs']==6 and s1['bb']['split_qty_pcs']==2,value_stays_in_wip=wip0==D('40.00'),
        scrap_moves_value=wip1==wip0-10 and exp1==exp0+10,undo_disposition_restores=wip2==wip0 and exp2==exp0,split_locked_by_resolution=locked['ok'],
        split_undone=s2['remaining_qty_pcs']==8 and status=='CANCELLED',stages_never_negative=minimum>=0,reports_zero=clean1 and clean2 and clean3),
        bs_case=[str(v) for v in case],ledger=[str(v) for v in (wip0,exp0,wip1,exp1,wip2,exp2)],detectors=[d1,d2,d3],split=sp)


def w02_split_rework(cur,today):
    """A split BS reworked GOOD through native laundry rework: the GOOD lot carries the opening per-piece value (2 x 5.00),
    WIP gives it up to FG; reversing the rework completion restores both; every report check stays zero."""
    if not bb_installed(cur):
        fx=production_post(cur,today,production_rows())
        return no_route(cur,lambda:split(cur,fx,fx['cutover']+timedelta(days=2),2))
    fx=production_post(cur,today,production_rows());c=fx['cutover']
    empty_accessory_bom(cur,fx['code'],c)
    split(cur,fx,c+timedelta(days=2),2)
    sp=source_of(cur,fx)['bb']['splits'][0]
    api.admin(cur);vendor=str(cur.execute('select id from erp.laundry_vendors where vendor_code=%s',(fx['code'],)).fetchone()[0])
    wip0=ledger(cur,'WIP',fx['po']);fg0=ledger(cur,'FG_INVENTORY',fx['po'])
    order=bs_act(cur,'SAVE_REWORK',dict(rework_number='BBW-'+uuid.uuid4().hex,bs_case_id=sp['bs_case_id'],destination_type='LAUNDRY',vendor_id=vendor,
        qty_sent=2,physical_sent_at=chain.production.at(c+timedelta(days=3),10),return_fg_location_id=fx['fg'],accessory_bom_item_ids=[],
        change_reason='BB W02 rework split BS'),None)
    done=bs_act(cur,'COMPLETE_REWORK',dict(rework_order_id=order['rework_order_id'],qty_good=2,qty_bs=0,completed_at=chain.production.at(c+timedelta(days=4),10),
        return_fg_location_id=fx['fg'],change_reason='BB W02 rework good'),order['row_version'])
    api.admin(cur);lot=cur.execute('select good_fg_lot_id from erp.rework_orders where id=%s',(order['rework_order_id'],)).fetchone()[0]
    cost=lot_cost(cur,lot);wip1=ledger(cur,'WIP',fx['po']);fg1=ledger(cur,'FG_INVENTORY',fx['po']);clean1,d1=production_clean(cur)
    bs_act(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=order['rework_order_id'],change_reason='BB W02 undo rework'),done['row_version'])
    wip2=ledger(cur,'WIP',fx['po']);fg2=ledger(cur,'FG_INVENTORY',fx['po']);clean2,d2=production_clean(cur)
    return verdict(dict(good_lot_value=D(cost)==D('10.00'),wip_to_fg=wip1==wip0-10 and fg1==fg0+10,reverse_restores=wip2==wip0 and fg2==fg0,
                        reports_zero=clean1 and clean2),lot_cost=str(cost),ledger=[str(v) for v in (wip0,fg0,wip1,fg1,wip2,fg2)],detectors=[d1,d2])


def w02_split_dated(cur,today):
    """A3 applied to splits: 3 pieces split on cutover+2 and the split undone today; a completion of all 8 dated cutover+3
    would use pieces that came back only today (refused BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING); the same completion dated
    today fits (control)."""
    if not bb_installed(cur):
        fx=production_post(cur,today,production_rows())
        return no_route(cur,lambda:split(cur,fx,fx['cutover']+timedelta(days=2),3))
    fx=production_post(cur,today,production_rows());c=fx['cutover']
    split(cur,fx,c+timedelta(days=2),3)
    sp=source_of(cur,fx)['bb']['splits'][0]
    wip_op(cur,fx,'REVERSE_SPLIT',split_id=sp['id'])
    early=refused(cur,lambda:complete(cur,fx,c+timedelta(days=3),8),'BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING')
    late=complete(cur,fx,today,8)
    minimum=stage_minimum(cur,fx['po'],'SEWING');clean,d=production_clean(cur)
    return verdict(dict(backdated_refused=early['ok'],today_fits=bool(late.get('lot_id')),sewing_never_negative=minimum>=0,reports_zero=clean),
                   refusal=early['refusal'],detectors=d)


def work_setup(cur,fx,rate='1.00'):
    """Privileged fixture: the model's work BOM (component {C}J at `rate`) and the PO's rate snapshot (no facade writes them)."""
    api.admin(cur);c=fx['cutover']
    model=cur.execute('select model_id from erp.production_orders where id=%s',(fx['po'],)).fetchone()[0]
    component=cur.execute("insert into erp.work_components(component_code,component_name,component_category,is_active) values(%s,'BB W jahit','LABOR',true) returning id",
                          (fx['code']+'J',)).fetchone()[0]
    bom=cur.execute("insert into erp.work_bom_versions(model_id,version_no,effective_from,is_active) values(%s,1,%s,true) returning id",
                    (model,chain.production.at(c-timedelta(days=30),0))).fetchone()[0]
    cur.execute('insert into erp.work_bom_items(bom_version_id,work_component_id,sequence_no,default_rate) values(%s,%s,1,%s)',(bom,component,D(rate)))
    cur.execute('select erp.ensure_po_work_component_snapshots(%s,%s)',(fx['po'],chain.production.at(c,1)))
    return component


def opening_work(cur,fx,component,qty,day,link=True):
    """One work completion of `qty` pcs of the component on `day` by the PO's mandor, posted by the native poster (the event
    and its line are inserted directly as other clients do; with BB its source is the opening WIP)."""
    api.admin(cur)
    contractor=cur.execute('select contractor_id from erp.production_orders where id=%s',(fx['po'],)).fetchone()[0]
    item=source_of(cur,fx)['opening_item_id'];api.admin(cur)
    cols,vals=('completion_number,po_id,contractor_id,physical_at',[ 'BBW-'+uuid.uuid4().hex[:12],fx['po'],contractor,chain.production.at(day,10)])
    if link:cols+=',bb_opening_item_id';vals.append(item)
    event=cur.execute('insert into erp.work_completion_events(%s) values(%s) returning id'%(cols,','.join(['%s']*len(vals))),vals).fetchone()[0]
    snap=cur.execute('select id from erp.po_work_component_snapshots where po_id=%s and work_component_id=%s',(fx['po'],component)).fetchone()[0]
    cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,%s,%s,0)',
                (event,snap,component,qty,qty))
    cur.execute('select erp.post_work_completion(%s)',(event,))
    return str(event)


def wage_rows():
    rows=production_rows()
    rows.update(CHART_ACCOUNT=[dict(account_code='{C}B',account_name='BB W bank',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT')],
                CASH_ACCOUNT=[dict(cash_account_code='{C}',cash_account_name='BB W bank',coa_account_code='{C}B',account_kind='BANK')])
    rows['OPENING_BALANCE_ITEM'].append(dict(balance_type='CASH_BANK',cash_account_code='{C}',amount='100.00',control_key='CASH'))
    rows['OPENING_CONTROL'].append(dict(control_key='CASH',balance_type='CASH_BANK',amount='100.00'))
    return rows


def w02_wages(cur,today):
    """ALL-W02 wages after cutover (auditor: "upah sesudah cutover" on opening WIP). Before BB a native work completion needs a
    Potongan, which an opening WIP never has (refused: no route). Oracle after BB: the mandor's work on the opening SEWING
    pieces (component J at 1.00 for 8 pcs) posts with the opening WIP as its source (WIP +8.00, contractor payable 8.00), the
    opening output then carries 40.00 + 8.00, and the wage is paid by the ordinary payroll (draft, approve, pay: one work line
    of 8.00, bank -8.00); every report check stays zero."""
    fx=production_post(cur,today,wage_rows());c=fx['cutover']
    component=work_setup(cur,fx)
    if not bb_installed(cur):
        return no_route(cur,lambda:opening_work(cur,fx,component,8,c+timedelta(days=2),link=False))
    wip0=ledger(cur,'WIP',fx['po']);pay0=ledger(cur,'CONTRACTOR_PAYABLE',fx['po'])
    opening_work(cur,fx,component,8,c+timedelta(days=2))
    wip1=ledger(cur,'WIP',fx['po']);pay1=ledger(cur,'CONTRACTOR_PAYABLE',fx['po'])
    out=complete(cur,fx,c+timedelta(days=3),8)
    cost=lot_cost(cur,out['lot_id']);clean1,d1=production_clean(cur)
    api.admin(cur)
    contractor,cash=cur.execute('select p.contractor_id,k.id from erp.production_orders p,erp.cash_accounts k where p.id=%s and k.cash_account_code=%s',
                                (fx['po'],fx['code'])).fetchone()
    pfx=dict(contractor=contractor,cash=str(cash))
    bank0=bank(cur,pfx)
    payroll=payroll_of(cur,pfx,today)
    cur.execute('select erp.populate_payroll_draft(%s)',(payroll,));cur.execute('select erp.recalculate_payroll(%s)',(payroll,))
    items=cur.execute('select count(*),coalesce(sum(amount),0) from erp.payroll_work_items where payroll_id=%s',(payroll,)).fetchone()
    payroll_call(cur,'approve_payroll',payroll);payroll_call(cur,'post_payroll_payment',payroll)
    bank1=bank(cur,pfx);clean2,d2=production_clean(cur)
    return verdict(dict(wage_accrued=wip1==wip0+8 and pay1==pay0-8,output_carries_wage=D(cost)==D('48.00'),
                        payroll_pays_once=items[0]==1 and D(items[1])==8 and bank1==bank0-8,reports_zero=clean1 and clean2),
                   lot_cost=str(cost),ledger=[str(v) for v in (wip0,pay0,wip1,pay1)],payroll_items=[str(v) for v in items],
                   bank=[str(bank0),str(bank1)],detectors=[d1,d2])


def w02_wage_refusals(cur,today):
    """Opening WIP work beyond its pieces (9 of 8 for one component) or dated before cutover is refused; another mandor's
    work is refused by the native contractor check."""
    fx=production_post(cur,today,production_rows());c=fx['cutover']
    component=work_setup(cur,fx)
    if not bb_installed(cur):
        return no_route(cur,lambda:opening_work(cur,fx,component,8,c+timedelta(days=2),link=False))
    over=refused(cur,lambda:opening_work(cur,fx,component,9,c+timedelta(days=2)),'BB_WORK_OPENING_EXCEEDS')
    early=refused(cur,lambda:opening_work(cur,fx,component,2,c-timedelta(days=1)),'BB_WORK_OPENING_DATE')
    opening_work(cur,fx,component,5,c+timedelta(days=2))
    rest=refused(cur,lambda:opening_work(cur,fx,component,4,c+timedelta(days=3)),'BB_WORK_OPENING_EXCEEDS')
    fits=opening_work(cur,fx,component,3,c+timedelta(days=3))
    return verdict(dict(over_refused=over['ok'],before_cutover_refused=early['ok'],cumulative_over_refused=rest['ok'],remainder_fits=bool(fits)),
                   refusals=[over['refusal'],early['refusal'],rest['refusal']])


def rework_masters(cur,today,rate='1.50'):
    """Masters prepared before the rework import (the import cannot create rates or accessory BOMs): an import of masters only,
    then mandor {C}'s rate for component {C}J on model {C} and an explicit empty accessory BOM for {C}P."""
    code='BW'+uuid.uuid4().hex[:12];c=today-timedelta(days=10)
    rows=product_masters()
    rows.update(CONTRACTOR=[dict(contractor_code='{C}',contractor_name='BB mandor rework',contractor_type='MANDOR'),
                            dict(contractor_code='{C}X',contractor_name='BB mandor lain',contractor_type='MANDOR')],
                LAUNDRY_VENDOR=[dict(vendor_code='{C}',vendor_name='BB laundry rework')])
    production_post(cur,today,rows,code=code)
    api.admin(cur)
    component=cur.execute("insert into erp.work_components(component_code,component_name,component_category,is_active) values(%s,'BB W06 obras','LABOR',true) returning id",
                          (code+'J',)).fetchone()[0]
    cur.execute("""insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from)
      select c.id,m.id,%s,%s,%s from erp.contractors c,erp.product_models m where c.contractor_code=%s and m.model_code=%s""",
                (component,D(rate),chain.production.at(c-timedelta(days=30),0),code,code))
    empty_accessory_bom(cur,code,c-timedelta(days=30))
    return code


def rework_import_rows(open_qty='4',rate='1.50',holder_ok=True,destination='CONTRACTOR'):
    """Opening BS of 4 pcs worth 20.00 held by mandor {C} (or laundry {C}); rework RW sent 5 before cutover, 1 back, 4 open."""
    field='contractor_code' if destination=='CONTRACTOR' else 'vendor_code'
    rows=production_rows(bs=('4',field,'{C}','20.00'))
    for k in list(rows):
        if k in('MODEL','SIZE','BRAND','PRODUCT','LOCATION','CONTRACTOR','LAUNDRY_VENDOR'):rows.pop(k)
    rw={'rework_number':'RW','bs_source_key':'BS','destination_type':destination,'sent_date':'{D}','qty_sent_original':'5',
        'qty_returned_before_cutover':'1','qty_open':open_qty,field:'{C}' if holder_ok else '{C}X'}
    rows['OPENING_REWORK']=[rw]
    if destination=='CONTRACTOR':
        rows['OPENING_REWORK_COMPONENT']=[dict(rework_number='RW',work_component_code='{C}J',completed_before_bs_qty='0',qty_performed='4',rate_per_pcs=rate)]
    return rows


def rework_post(cur,today,code,rows,expect=None):
    day=str(today-timedelta(days=15))
    rows={k:[{f:(v.replace('{D}',day) if isinstance(v,str) else v) for f,v in p.items()} for p in ps] for k,ps in rows.items()}
    return _rework_post(cur,today,code,rows,expect)


def _rework_post(cur,today,code,rows,expect):
    """The rework import names the masters of `code`; its own batch code differs (batch codes are unique)."""
    cutover=today-timedelta(days=10)
    boundary.historical.prior.set_open_period(cur,cutover-timedelta(days=1))
    batch=api.call(cur,'CREATE',dict(batch_code=code+'I',cutover_date=str(cutover)))['batch_id']
    fill=lambda v:v.replace('{C}',code) if isinstance(v,str) else v
    for entity,payloads in rows.items():
        api.upload(cur,batch,entity,[{k:fill(v) for k,v in p.items()} for p in payloads])
    checked=api.invoke(cur,'VALIDATE',batch)
    api.admin(cur)
    errors=cur.execute("select entity_type,validation_errors::text from erp.migration_staging_rows where batch_id=%s and validation_status='ERROR'",(batch,)).fetchall()
    if expect is not None:return dict(batch=batch,code=code,errors=[list(e) for e in errors])
    if checked.get('error_rows')!=0:raise AssertionError(('BB_FIXTURE_REFUSED',checked,errors))
    posted=api.invoke(cur,'FINALIZE',batch)
    assert posted.get('status')=='POSTED',('BB_FIXTURE_NOT_POSTED',posted)
    api.admin(cur)
    po,fg=cur.execute('select p.id,(select id from erp.locations where location_code=%s) from erp.production_orders p where p.po_number=%s',(code+'G',code)).fetchone()
    return dict(batch=batch,code=code,cutover=cutover,po=str(po),fg=str(fg))


def w06_before(cur,today):
    code='BW'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=10))))['batch_id']
    return no_route(cur,lambda:api.upload(cur,batch,'OPENING_REWORK',[dict(rework_number='RW',bs_source_key='BS',destination_type='CONTRACTOR',
        sent_date=str(today-timedelta(days=15)),qty_sent_original='5',qty_returned_before_cutover='1',qty_open='4')]))


def w06_contractor(cur,today):
    """ALL-W06 (auditor: rework sent before cutover, partly returned, components unpaid). Oracle: the 4 pieces still at mandor
    {C} become one native rework order IN_PROGRESS of 4 on the opening BS case, its component line priced by the mandor's
    rate 1.50 (4 newly payable), nothing journaled at import and no history invented (sent 5 / returned 1 kept on the import
    record only); the native COMPLETE_REWORK (3 GOOD, 1 BS) accrues 6.00 of rework wage and gives a GOOD lot of 3 x 5.00
    opening value + 6.00 x 3/4 = 19.50; reversing it restores the ledger; every report check stays zero."""
    if not bb_installed(cur):return w06_before(cur,today)
    code=rework_masters(cur,today)
    before=gl(cur)
    fx=rework_post(cur,today,code,rework_import_rows())
    import_delta=moved(before,gl(cur))
    record=ws(cur,fx['batch'])['opening_reworks'][0]
    api.admin(cur)
    order=cur.execute('''select ro.id,ro.status,ro.qty_sent,ro.destination_type,ro.row_version,b.status,l.rate_snapshot,l.qty_newly_payable,l.rate_basis
      from erp.rework_orders ro join erp.bs_cases b on b.id=ro.bs_case_id join erp.rework_component_lines l on l.rework_order_id=ro.id where ro.id=%s''',
                      (record['rework_order_id'],)).fetchone()
    clean1,d1=production_clean(cur)
    wip0=ledger(cur,'WIP',fx['po']);pay0=ledger(cur,'CONTRACTOR_PAYABLE',fx['po'])
    done=bs_act(cur,'COMPLETE_REWORK',dict(rework_order_id=str(order[0]),qty_good=3,qty_bs=1,completed_at=chain.production.at(fx['cutover']+timedelta(days=3),10),
        return_fg_location_id=fx['fg'],change_reason='BB W06 rework back'),order[4])
    api.admin(cur);lot=cur.execute('select good_fg_lot_id from erp.rework_orders where id=%s',(order[0],)).fetchone()[0]
    cost=lot_cost(cur,lot);pay1=ledger(cur,'CONTRACTOR_PAYABLE',fx['po']);clean2,d2=production_clean(cur)
    bs_act(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=str(order[0]),change_reason='BB W06 undo'),done['row_version'])
    wip2=ledger(cur,'WIP',fx['po']);pay2=ledger(cur,'CONTRACTOR_PAYABLE',fx['po']);clean3,d3=production_clean(cur)
    wip_account=account(cur,'WIP')
    return verdict(dict(
        native_open_order=order[1]=='IN_PROGRESS' and order[2]==4 and order[3]=='CONTRACTOR' and order[5]=='IN_REWORK',
        rate_and_payable=D(order[6])==D('1.50') and order[7]==4 and order[8]=='CONTRACTOR_RATE',
        history_on_record_only=record['qty_sent_original']==5 and record['qty_returned_before_cutover']==1 and record['qty_open']==4,
        import_ledger_only_opening_bs=import_delta.get(wip_account)=='60.00',
        completion_wage=pay1==pay0-6,good_lot_value=D(cost)==D('19.50'),reverse_restores=wip2==wip0 and pay2==pay0,
        reports_zero=clean1 and clean2 and clean3),
        order=[str(v) for v in order],record=record,import_delta=import_delta,lot_cost=str(cost),
        ledger=[str(v) for v in (wip0,pay0,pay1,wip2,pay2)],detectors=[d1,d2,d3])


def w06_laundry(cur,today):
    """An open laundry rework (BS held by laundry {C}): a native LAUNDRY rework of 4 without wage components; 4 GOOD back
    give a lot of 4 x 5.00."""
    if not bb_installed(cur):return w06_before(cur,today)
    code=rework_masters(cur,today)
    fx=rework_post(cur,today,code,rework_import_rows(destination='LAUNDRY'))
    record=ws(cur,fx['batch'])['opening_reworks'][0]
    api.admin(cur);version=cur.execute('select row_version from erp.rework_orders where id=%s',(record['rework_order_id'],)).fetchone()[0]
    bs_act(cur,'COMPLETE_REWORK',dict(rework_order_id=record['rework_order_id'],qty_good=4,qty_bs=0,completed_at=chain.production.at(fx['cutover']+timedelta(days=3),10),
        return_fg_location_id=fx['fg'],change_reason='BB W06 laundry back'),version)
    api.admin(cur);lot=cur.execute('select good_fg_lot_id from erp.rework_orders where id=%s',(record['rework_order_id'],)).fetchone()[0]
    cost=lot_cost(cur,lot);clean,d=production_clean(cur)
    return verdict(dict(laundry_order=record['destination_type']=='LAUNDRY' and record['components']==[],good_lot_value=D(cost)==D('20.00'),reports_zero=clean),
                   record=record,lot_cost=str(cost),detectors=d)


def w06_refusal(cur,today,variant):
    if not bb_installed(cur):return w06_before(cur,today)
    code=rework_masters(cur,today)
    kw={'OPEN_QTY':dict(open_qty='3'),'RATE':dict(rate='2.00'),'HOLDER':dict(holder_ok=False)}[variant]
    expected={'OPEN_QTY':'BB_REWORK_OPEN_QTY_MISMATCH','RATE':'BB_REWORK_RATE_MISMATCH','HOLDER':'BB_REWORK_HOLDER_MISMATCH'}[variant]
    out=rework_post(cur,today,code,rework_import_rows(**kw),expect=True)
    return verdict(dict(refused_at_validation=any(expected in e[1] for e in out['errors'])),variant=variant,errors=out['errors'])


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
      ('P:P03_QUANTITY_EQUATION_REFUSED','NO_ROUTE',lambda c,t:p03_refusal(c,t,'EQUATION')),
      ('P:P04_OPEN_ORDER_RECEIVE_REOPEN_CANCEL','NO_ROUTE',p04_cycle),
      ('P:P04_REMAINING_EQUATION_REFUSED','NO_ROUTE',lambda c,t:p04_refusal(c,t,'EQUATION')),
      ('P:P04_SAME_ORDER_LATER_BATCH_REFUSED','NO_ROUTE',lambda c,t:p04_refusal(c,t,'DUPLICATE')),
      ('P:S02_DRAFT_RESERVES_ONCE_EDIT_POST','NO_ROUTE',s02_cycle),
      ('P:S02_CANCEL_RELEASES_RESERVATION','NO_ROUTE',s02_cancel),
      ('P:S02_RESERVATIONS_OVER_STOCK_REFUSED','NO_ROUTE',lambda c,t:s02_refusal(c,t,'OVER_STOCK')),
      ('P:S02_DRAFT_AFTER_CUTOVER_REFUSED','NO_ROUTE',lambda c,t:s02_refusal(c,t,'DRAFT_AFTER_CUTOVER')),
      ('P:S02_DRAFT_NUMBER_REUSED_REFUSED','NO_ROUTE',lambda c,t:s02_refusal(c,t,'DUPLICATE')),
      ('P:Y02_ENTITLEMENTS_PAYROLL_AND_CARRY','NO_ROUTE',y02_cycle),
      ('P:Y02_ATTENDANCE_WITHOUT_ATTENDANCE_REFUSED','NO_ROUTE',lambda c,t:y02_refusal(c,t,'NO_ATTENDANCE')),
      ('P:Y02_ENTITLEMENTS_NOT_EQUAL_DOCUMENT_REFUSED','NO_ROUTE',lambda c,t:y02_refusal(c,t,'EQUATION')),
      ('W:W04_CUTTING_PICKUP_COMPLETE_REVERSE','NO_ROUTE',w04_cycle),
      ('W:W04_PICKUP_OTHER_MANDOR_REFUSED','NO_ROUTE',w04_other_mandor),
      ('W:W04_CUTTING_ROW_WITH_HOLDER_REFUSED','NO_ROUTE',w04_holder_refused),
      ('W:W02_SPLIT_BS_DISPOSE_AND_UNDO','NO_ROUTE',w02_split_dispose),
      ('W:W02_SPLIT_BS_REWORK_GOOD','NO_ROUTE',w02_split_rework),
      ('W:W02_SPLIT_DATED_REMAINING','NO_ROUTE',w02_split_dated),
      ('W:W02_WAGES_AFTER_CUTOVER_THROUGH_PAYROLL','NO_ROUTE',w02_wages),
      ('W:W02_WAGES_OVER_PIECES_OR_BEFORE_CUTOVER_REFUSED','NO_ROUTE',w02_wage_refusals),
      ('W:W06_OPEN_REWORK_CONTRACTOR','NO_ROUTE',w06_contractor),
      ('W:W06_OPEN_REWORK_LAUNDRY','NO_ROUTE',w06_laundry),
      ('W:W06_OPEN_QTY_MISMATCH_REFUSED','NO_ROUTE',lambda c,t:w06_refusal(c,t,'OPEN_QTY')),
      ('W:W06_RATE_MISMATCH_REFUSED','NO_ROUTE',lambda c,t:w06_refusal(c,t,'RATE')),
      ('W:W06_HOLDER_MISMATCH_REFUSED','NO_ROUTE',lambda c,t:w06_refusal(c,t,'HOLDER'))]
assert len({k for k,_,_ in PLAN})==len(PLAN),'BB_DUPLICATE_CASE_ID'


# Every batch workspace a case reads (and the last state of each batch it touched) is saved and run through the import
# page's own parser after the group (scripts/cp6_bb_workspace_parse.mjs): the page hides a batch it cannot parse.
WS=dict(dir=None,case=None,n=0,batches=set(),errors=[])
_READ=api.read


def recording_read(cur,batch=None):
    result=_READ(cur,batch)
    if WS['dir'] is not None and batch is not None and isinstance(result,dict) and result.get('batch'):
        WS['n']+=1;WS['batches'].add(str(batch))
        name='%s_%03d.json'%(re.sub(r'[^A-Za-z0-9]+','_',WS['case'] or 'SETUP'),WS['n'])
        (WS['dir']/name).write_text(json.dumps(result,default=str))
    return result


def final_reads(cur):
    for batch in sorted(WS['batches']):
        try:cur.execute('savepoint bb_ws_final')
        except psycopg.Error:return   # the case ended on the aborted transaction of a refusal it expected
        api.admin(cur)
        if not cur.execute('select exists(select 1 from erp.migration_batches where id=%s)',(batch,)).fetchone()[0]:
            cur.execute('release savepoint bb_ws_final');continue   # made inside a refusal the case rolled back
        try:api.read(cur,batch);cur.execute('release savepoint bb_ws_final')
        except psycopg.Error as exc:
            cur.execute('rollback to savepoint bb_ws_final');api.admin(cur)
            WS['errors'].append(dict(case=WS['case'],batch=batch,error=str(exc)[:300]))


def cases(cur,today):
    def one(key,fn):
        WS.update(case=key,n=0,batches=set())
        result=fn(cur,today)
        if WS['dir'] is not None:final_reads(cur)
        return result
    return [(key,lambda k=key,f=fn:one(k,f)) for key,_,fn in PLAN]


def workspace_parse(phase):
    """Run the page parser over the saved workspaces; refused files are kept in the proof directory."""
    run=subprocess.run(['node',str(AUDITOR/'scripts/cp6_bb_workspace_parse.mjs'),str(WS['dir'])],capture_output=True,text=True,cwd=AUDITOR)
    lines=run.stdout.strip().splitlines()
    try:parsed=json.loads(lines[-1])
    except (IndexError,ValueError):parsed=dict(files=None,refused=None,error=(run.stderr or run.stdout)[-1500:])
    kept=OUT/('WORKSPACE_REFUSED_'+phase.upper());kept.mkdir(parents=True,exist_ok=True)
    for item in parsed.get('refused') or []:(kept/item['file']).write_text((WS['dir']/item['file']).read_text())
    ok=run.returncode==0 and parsed.get('refused')==[] and (parsed.get('files') or 0)>0 and not WS['errors']
    return dict(status='PASS' if ok else 'FAIL',files=parsed.get('files'),refused=parsed.get('refused'),read_errors=WS['errors'],
                error=parsed.get('error'),exit=run.returncode)


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
        WS['dir']=Path(tempfile.mkdtemp(prefix='cp6-bb-ws-'));api.read=recording_read
        group=r1.group('BB_CASES_'+phase.upper(),cases,verify)
        api.read=_READ
        report['bb_cases']={k:group[k] for k in ('status','counts')}
        report['workspace_parse']=workspace_parse(phase)
        print(json.dumps(dict(bb_workspace_parse=report['workspace_parse']),default=str),flush=True)
        final={k:v['status'] for k,v in group['cases'].items()}
        report['final']=final
        report['expectation_mismatch']={k:dict(planned=list(e),final=final.get(k)) for k,e in planned.items() if final.get(k) not in e}
        report['status']='REVIEW_COMPLETE' if group['status']!='INCOMPLETE' and not report['expectation_mismatch'] and report['workspace_parse']['status']=='PASS' else 'INCOMPLETE'
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
