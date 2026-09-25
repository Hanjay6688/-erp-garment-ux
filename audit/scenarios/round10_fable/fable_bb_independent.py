"""rev3: P03 journal-type check accepts OPENING_UNINVOICED_RECEIPT (the opening GRNI obligation journal of M:831; rev2 FAIL was the auditor check). Pinned to the BB final head.
rev2: P03 case query fixed (supplier invoices/payments looked up by supplier; run 36132268786 INCOMPLETE was the auditor SQL, 38/38 other cases PASS).
Fable BB T1 independent rerun on the exact writer head (round 10). Label T1_FAMILY / AUDITOR_SCENARIO, never release evidence.

Runs the writer's own BB PLAN unchanged (exact head, before and after) and appends Fable cases with oracles from the contract
and Fable's pre-code ALL oracles (out/fable_all22_oracles_pre_code.md), written without reading the writer's BB SQL:
  FAB:S01_OPENING_AR_DIRECTION      M:934-938: opening AR 70 (invoice 100, received 30) = Dr AR 70 / Cr OPENING_EQUITY; bank 100 Dr;
                                    only OPENING_BALANCE journals; no sale/receipt/revenue history minted.
  FAB:P02_SETTLE_EXACT_THEN_CENT    M:934-938 + fail-closed: settle exactly the remaining 65 -> 0; a further 0.01 refused
                                    BB_OSS_EXCEEDS_AVAILABLE atomically; reverse restores 65 and the bank.
  FAB:S01_TWO_PARTIALS_REVERSE_FIRST two settlements 25 + 45 exhaust AR 70; reversing the FIRST (not the last) restores 25 and
                                    bank -25 only; the second stays; reversing the second restores 70.
  FAB:OSS_BALANCE_OF_OTHER_BATCH_REFUSED a settlement naming a balance of another batch is refused, nothing changes (source identity).
  FAB:P03_NO_DUPLICATE_OBLIGATION   P03 import only: inventory 22 = GRNI 12 (6 x 2) + invoiced 10 (7 open + 3 paid historically);
                                    native AP 0; only OPENING_BALANCE journals (no old invoice/payment minted).
Phase before: settlement cases are NO_ROUTE (no adapter); S01 direction and P03 import may already PASS on BA (documented).
This script changes no product, SQL or writer checkout file.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import argparse,sys,uuid
import psycopg
sys.path.insert(0,str((Path.cwd().parent/'auditor'/'scripts').resolve()))
import cp6_bb_probe as bb
D=Decimal
api=bb.api

def _delta_str(cur,before):
    return {k:str(D(v).quantize(D('0.01'))) for k,v in bb.moved(before,bb.gl(cur)).items()}

def s01_direction(cur,today):
    before=bb.gl(cur);start=bb.now(cur)
    fx=bb.financial_fixture(cur,today,documents=[('CUSTOMER_RECEIVABLE','FAB-S01','100.00','30.00')],bank='100.00')
    delta=_delta_str(cur,before)
    ar=bb.account(cur,'AR_CUSTOMER');eq=bb.account(cur,'OPENING_EQUITY')
    bank_acc=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(fx['cash'],)).fetchone()[0])
    types=bb.journal_types(cur,start)
    checks=dict(ar_debit_70=delta.get(ar)=='70.00',bank_debit_100=delta.get(bank_acc)=='100.00',equity_credit_170=delta.get(eq)=='-170.00',
                no_other_accounts=set(delta)=={ar,eq,bank_acc},only_opening_journal=set(types)<={'OPENING_BALANCE'},
                subledger_70=bb.balance_row(cur,fx,'FAB-S01')[2]==D('70.00'))
    return bb.verdict(checks,delta=delta,journals=types,oracle='M:934-938 / Fable ALL-S01 pre-code oracle: Dr AR 70, Cr OPENING_EQUITY, no minted history')

def p02_exact_then_cent(cur,today):
    fx=bb.financial_fixture(cur,today,documents=[('SUPPLIER_PAYABLE','FAB-P02','100.00','35.00')])
    day=str(fx['cutover']+timedelta(days=1));bal=fx['balances']['FAB-P02']
    payload=dict(operation='SETTLE',balance_id=bal,amount='65.00',effective_date=day,cash_account_id=fx['cash'],reason='FAB exact settlement')
    if not bb.bb_installed(cur):return bb.no_route(cur,lambda:bb.act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload))
    bank0=bb.bank(cur,fx)
    first=bb.act(cur,'OPENING_SETTLEMENT',fx['batch'],**payload)
    after=bb.balance_row(cur,fx,'FAB-P02');bank1=bb.bank(cur,fx)
    cent=bb.refused(cur,lambda:bb.act(cur,'OPENING_SETTLEMENT',fx['batch'],**dict(payload,amount='0.01',reason='FAB one cent over')),'BB_OSS_EXCEEDS_AVAILABLE')
    after_cent=bb.balance_row(cur,fx,'FAB-P02');bank2=bb.bank(cur,fx)
    bb.act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='REVERSE',settlement_id=first['settlement_id'],reason='FAB reverse exact')
    after_rev=bb.balance_row(cur,fx,'FAB-P02');bank3=bb.bank(cur,fx)
    checks=dict(remaining_zero=after[2]==0,bank_minus_65=bank1==bank0-D('65.00'),cent_refused_with_code=cent['ok'],
                nothing_moved_on_refusal=after_cent[2]==0 and bank2==bank1,reverse_restores_65=after_rev[2]==D('65.00'),bank_restored=bank3==bank0)
    return bb.verdict(checks,bank=[str(bank0),str(bank1),str(bank2),str(bank3)],refusal=cent['refusal'])

def s01_two_partials(cur,today):
    fx=bb.financial_fixture(cur,today,documents=[('CUSTOMER_RECEIVABLE','FAB-S01B','100.00','30.00')])
    day=str(fx['cutover']+timedelta(days=1));bal=fx['balances']['FAB-S01B']
    mk=lambda amt,why:dict(operation='SETTLE',balance_id=bal,amount=amt,effective_date=day,cash_account_id=fx['cash'],reason=why)
    if not bb.bb_installed(cur):return bb.no_route(cur,lambda:bb.act(cur,'OPENING_SETTLEMENT',fx['batch'],**mk('25.00','FAB first')))
    bank0=bb.bank(cur,fx)
    first=bb.act(cur,'OPENING_SETTLEMENT',fx['batch'],**mk('25.00','FAB first partial'))
    second=bb.act(cur,'OPENING_SETTLEMENT',fx['batch'],**mk('45.00','FAB second partial'))
    r2=bb.balance_row(cur,fx,'FAB-S01B');bank2=bb.bank(cur,fx)
    bb.act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='REVERSE',settlement_id=first['settlement_id'],reason='FAB reverse the first, not the last')
    r3=bb.balance_row(cur,fx,'FAB-S01B');bank3=bb.bank(cur,fx)
    again=bb.refused(cur,lambda:bb.act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='REVERSE',settlement_id=first['settlement_id'],reason='FAB double reverse'),'ANY')
    bb.act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='REVERSE',settlement_id=second['settlement_id'],reason='FAB reverse the second')
    r4=bb.balance_row(cur,fx,'FAB-S01B');bank4=bb.bank(cur,fx)
    api.admin(cur)
    posted=cur.execute("select count(*) from erp.opening_subledger_settlements where balance_id=%s and status='POSTED'",(bal,)).fetchone()[0]
    checks=dict(exhausted_after_two=r2[2]==0 and bank2==bank0+D('70.00'),first_reversed_only=r3[2]==D('25.00') and bank3==bank0+D('45.00'),
                double_reverse_refused=again['refusal'] is not None,all_reversed=r4[2]==D('70.00') and bank4==bank0,no_posted_settlement_left=posted==0)
    return bb.verdict(checks,bank=[str(bank0),str(bank2),str(bank3),str(bank4)],double_reverse=again['refusal'])

def other_batch_balance(cur,today):
    a=bb.financial_fixture(cur,today,documents=[('SUPPLIER_PAYABLE','FAB-A','100.00','35.00')])
    b=bb.financial_fixture(cur,today,documents=[('SUPPLIER_PAYABLE','FAB-B','50.00','0.00')],cutover_days=9)
    payload=dict(operation='SETTLE',balance_id=a['balances']['FAB-A'],amount='10.00',effective_date=str(today-timedelta(days=1)),cash_account_id=b['cash'],reason='FAB cross-batch')
    if not bb.bb_installed(cur):return bb.no_route(cur,lambda:bb.act(cur,'OPENING_SETTLEMENT',b['batch'],**payload))
    bank_a=bb.bank(cur,a);bank_b=bb.bank(cur,b)
    r=bb.refused(cur,lambda:bb.act(cur,'OPENING_SETTLEMENT',b['batch'],**payload),'ANY')
    checks=dict(refused=r['refusal'] is not None,balance_a_unchanged=bb.balance_row(cur,a,'FAB-A')[2]==D('65.00'),banks_unchanged=bb.bank(cur,a)==bank_a and bb.bank(cur,b)==bank_b)
    return bb.verdict(checks,refusal=r['refusal'])

def p03_no_duplicate(cur,today):
    cutover=today-timedelta(days=10);rows=bb.p03_rows(cutover)
    if not bb.bb_installed(cur):
        code='FAB'+uuid.uuid4().hex[:10]
        batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(cutover)))['batch_id']
        receipt={k:(v.replace('{C}',code) if isinstance(v,str) else v) for k,v in rows['UNINVOICED_RECEIPT'][0].items()}
        return bb.no_route(cur,lambda:api.upload(cur,batch,'UNINVOICED_RECEIPT',[receipt]))
    before=bb.gl(cur);start=bb.now(cur)
    batch,code,cutover=bb.post_batch(cur,today,rows)
    delta=_delta_str(cur,before);types=bb.journal_types(cur,start)
    inv=bb.account(cur,'MATERIAL_INVENTORY');grni=bb.account(cur,'GRNI_MATERIAL');ap=bb.account(cur,'AP_SUPPLIER')
    api.admin(cur)
    item=cur.execute("select l.purchase_item_id from erp.initial_import_receipt_lines l join erp.initial_import_receipt_headers h on h.purchase_id=l.purchase_id where h.batch_id=%s",(batch,)).fetchone()[0]
    st=bb.p03_state(cur,item)
    supplier=cur.execute('select id from erp.suppliers where supplier_code=%s',(code,)).fetchone()[0]
    old_docs=cur.execute("select (select count(*) from erp.material_supplier_invoices where supplier_id=%s),(select count(*) from erp.supplier_payments p join erp.material_purchase_headers h on h.id=p.purchase_id where h.supplier_id=%s)",(supplier,supplier)).fetchone()
    checks=dict(inventory_22=delta.get(inv)=='22.00',grni_12_unbilled_only=delta.get(grni)=='-12.00',ap_7_open_part_only=delta.get(ap)=='-7.00',
                obligation_basis_equals_inventory=D('12.00')+D('7.00')+D('3.00')==D('22.00') and delta.get(inv)=='22.00',
                native_ap_zero=st['native_ap']==0,no_minted_invoice_or_payment=old_docs==(0,0),only_opening_journals=set(types)<={'OPENING_BALANCE','OPENING_UNINVOICED_RECEIPT'})
    return bb.verdict(checks,delta=delta,state={k:str(v) for k,v in st.items()},journals=types,oracle='Fable ALL-P03 pre-code oracle: one receipt basis, GRNI = unbilled x c, AP = open invoiced part, no duplicate obligation')

FABLE=[('FAB:S01_OPENING_AR_DIRECTION',('PASS',),s01_direction),
       ('FAB:P02_SETTLE_EXACT_THEN_CENT',('NO_ROUTE',),p02_exact_then_cent),
       ('FAB:S01_TWO_PARTIALS_REVERSE_FIRST',('NO_ROUTE',),s01_two_partials),
       ('FAB:OSS_BALANCE_OF_OTHER_BATCH_REFUSED',('NO_ROUTE',),other_batch_balance),
       ('FAB:P03_NO_DUPLICATE_OBLIGATION',('NO_ROUTE',),p03_no_duplicate)]

def main(phase):
    n=len(bb.PLAN);ids={k for k,_,_ in bb.PLAN}
    assert len(ids)==n,('BB_ORIGINAL_DUPLICATE_CASE_ID',n)
    print({'fable_bb_wrapper':True,'writer_plan_cases':n,'fable_cases':len(FABLE)},flush=True)
    for key,before,fn in FABLE:
        assert key not in ids
        bb.PLAN.append((key,before,fn))
    bb.run(phase)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=('before','after'),required=True);main(p.parse_args().phase)
