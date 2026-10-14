"""CP1–CP7 audit fix r1: the dated guards and the stock card, on the real Native writers and CP7 commands.

Locked reports (Fable, Astra, Sol on 0b7049d9) and owner decisions of 15 Oct 2026:
- FIN01 (D14-2): an ordinary payroll payment may not be dated before the latest payable source it settles
  (attendance accrual on period_end, work on its WIB completion date). Paying earlier is a kasbon, not a payment.
- CASH (D14-3, Sol SOL-001): no posting may leave a cash/bank account below zero on its economic date or any later
  date, whichever writer posts it (supplier, payroll, laundry vendor).
- FIN02 (Astra/Fable): a laundry claim settlement may not precede its claim/source, nor take the vendor's dated
  payable below zero.
- STK01 (Astra): after REOPEN and re-POST of a cutting on its own day, the stock card never shows the old and the
  new issue as two active consumptions.
- RWK01 (Astra/Fable): a rework wage accrued at completion stays payable when the BS case ends SCRAPPED, exactly
  once; a case without a final outcome (OPEN after an all-BS return, PARTIAL after a partial disposal) stays
  unpayable as before.
- HPP01 (Astra/Fable): a contractor HPP policy write that would leave an ACTIVE attendance HPP pool on a stale basis
  is refused; an unrelated policy is not; cancel pool -> policy -> replacement pool is the lawful path.
- Detector: cp7_guard.findings() lists rows already in the books that the guards would refuse today (data from
  before the guards), and a lawful correction (owner capital on that day) clears the cash row.
- KASBON (D14-6): cash given to a contractor before wages exist (the lawful path D14-2 points to): Dr receivable /
  Cr bank on its date, the bank never negative (D14-3), recovered as a CASH_ADVANCE deduction on a payroll draft that
  the accepted Native payment posts; capped by the kasbon and by the payroll's earnings; cancel only while unused.
- SG-03 (D06, Lampiran C6 LAU-06a): rewash of the same product at the laundry vendor is free: no vendor payable, no
  vendor journal line, no rework wage; the pieces come back as goods.
- SG-01 (FABLE-009 / Astra SG-01): a POSTED pickup (Bagi Potongan) is reversed before any sewing: pickup REVERSED with its
  batches kept, group back to CUT with its fabric posted, PO stage and Mandor back to their values before the POST; the
  Native guards still refuse every other write; once sewing has started the reversal names the document and refuses.
- SG-02 (D14-4): leftover fabric of a posted cutting goes back to the warehouse: the same roll returns to stock at its
  issue cost, the PO's WIP drops by exactly that value, at most the remainder recorded at cutting, once per cutting.
Oracles do not come from the guards: dates are read from the Native accrual journals and source rows, balances
from journal lines and movements. Every refusal leaves the whole business boundary unchanged and has a lawful
control. Fixture banks receive owner capital through the accepted Native journal (cp7_cash_funding) only where the
case says so; an empty bank stays empty.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from datetime import datetime,timezone
from decimal import Decimal as D,ROUND_HALF_UP
import json,threading,uuid
import psycopg
import cp7_settlement_cases as s
import cp7_installment_cases as instal
import cp7_supplier_payment_create_cases as pay
import cp7_cutting_correction_cases as cut
import cp7_material_cases as material
import cp7_nota_cases as nota
import cp6_bd_probe as bd
import cp7_cash_funding as funding

auth,b,bc=s.auth,s.b,s.bc
refused=auth.refused
CONTRACT='cp7.cp17-fixes.v1'
FUNCTIONS=('erp_set_contractor_hpp_policy_v1','erp_cp7_save_nota_v1','erp_cp7_get_nota_workspace_v1','erp_save_bs_resolution_action_v1','erp_cp7_save_payroll_v1','erp_cp7_save_payroll_installment_v1','erp_cp7_create_supplier_payment_v1',
           'erp_save_laundry_bd_action_v1','erp_cp7_get_material_ledger_v1','erp_cp7_get_material_ledger_v2',
           'erp_cp7_get_cutting_return_v1','erp_cp7_return_cutting_fabric_v1','erp_cp7_get_cutting_correction_v1',
           'erp_cp7_get_kasbon_v1','erp_cp7_save_kasbon_v1','erp_cp7_get_pickup_reversal_v1','erp_cp7_reverse_pickup_v1')
IDS=dict(
    native=['CP17_FIN01_FULL_PAY_BEFORE_ATTENDANCE_REFUSED','CP17_FIN01_WORK_ONLY_BEFORE_COMPLETION_REFUSED',
            'CP17_FIN01_INSTALLMENT_BEFORE_ACCRUAL_REFUSED','CP17_FIN01_DIRECT_NATIVE_PAYMENT_REFUSED',
            'CP17_CASH_EMPTY_BANK_REFUSED','CP17_CASH_EXACT_ZERO_ALLOWED_THEN_REFUSED','CP17_CASH_BACKDATE_BEFORE_FUNDS_REFUSED',
            'CP17_CASH_LATER_DAY_PROTECTED','CP17_CASH_PAYROLL_EMPTY_BANK_REFUSED','CP17_CASH_LAUNDRY_VENDOR_EMPTY_BANK_REFUSED',
            'CP17_FIN02_CLAIM_SAME_DAY_CONTROL','CP17_FIN02_CLAIM_BEFORE_SOURCE_REFUSED','CP17_FIN02_CLAIM_AP_NOT_AVAILABLE_REFUSED',
            'CP17_STK01_REOPEN_REPOST_CARD_NOT_NEGATIVE',
            'CP17_RWK01_ALL_SCRAP_REWORK_PAYABLE_ONCE','CP17_RWK01_GOOD_CONTROL','CP17_RWK01_UNFINISHED_CASE_STILL_HELD',
            'CP17_HPP01_EXCLUDED_CONTRACTOR_POLICY_REFUSED','CP17_HPP01_UNRELATED_POLICY_CONTROL','CP17_HPP01_CANCEL_POLICY_REPLACEMENT_POOL',
            'CP17_SG02_RETURN_STOCK_VALUE_PO_COST','CP17_SG02_OVER_REMAINDER_REFUSED','CP17_SG02_ONCE_AND_SAME_REQUEST_REPLAY','CP17_SG02_BEFORE_CUT_OR_FUTURE_REFUSED',
            'CP17_DETECTOR_LISTS_LEGACY_ROWS',
            'CP17_KASBON_GIVE_DEDUCT_PAY','CP17_KASBON_LIMITS_REFUSED','CP17_KASBON_RELEASE_CANCEL_REPLAY',
            'CP17_SG03_REWASH_SAME_PRODUCT_NO_VENDOR_BILL',
            'CP17_SG01_PICKUP_REVERSE_BEFORE_SEWING','CP17_SG01_PICKUP_REVERSE_REFUSED'],
    races=['CP17_RACE_TWO_PAYMENTS_ONE_BANK','CP17_RACE_ATTENDANCE_ONE_PAYROLL'],
    http=['CP17_HTTP_CASH_EMPTY_BANK_REFUSED','CP17_HTTP_PAYROLL_EARLY_REFUSED','CP17_HTTP_KASBON_GIVE','CP17_HTTP_ERP_WRITERS_NOT_REACHABLE'],
    browser=['CP17_BROWSER_SG01_PICKUP_REVERSAL_DESKTOP','CP17_BROWSER_SG02_FABRIC_RETURN_MOBILE','CP17_BROWSER_KASBON_GIVE_DEDUCT_DESKTOP'],
)
REQUIRED={k:len(v)for k,v in IDS.items()}
EXPECTED=sum(REQUIRED.values())


# ---------------------------------------------------------------- shared observations
def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]

def balance(cur,bank):
    """Bank balance from its journal lines (debit minus credit)."""
    b.api.admin(cur)
    return D(one(cur,"select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id "
                     "join erp.cash_accounts c on c.coa_account_id=l.account_id where c.id=%s and j.status in('POSTED','REVERSED')",(bank,)))

def accrued_day(cur,contractor):
    """Latest economic date on which a payable to this (fresh) contractor was recognized: its own accrual journals."""
    b.api.admin(cur)
    return one(cur,"select max(j.economic_date) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id "
                   "where l.contractor_id=%s and l.account_id=erp.account_id('CONTRACTOR_PAYABLE') and l.credit>0 and j.status='POSTED'",(contractor,))

def unchanged(cur,before,what):
    assert b.boundary.snapshot(cur)==before,('CP17_REFUSAL_CHANGED_BOUNDARY',what)

def approved_payroll(cur,today,attendance=True):
    f=s.review.fixture(cur,today)
    if attendance:s.attendance(cur,f,today)
    pid=f['payroll'];s.act(cur,'PREPARE',s.doc(cur,pid));s.act(cur,'APPROVE',s.doc(cur,pid))
    d=s.doc(cur,pid);assert d['status']=='APPROVED',d
    return f,pid,D(d['net_payable'])

# ---------------------------------------------------------------- D14-6 kasbon helpers
def kasbon_read(cur,contractor,subject=None):
    auth.actor(cur,subject);w=one(cur,'select public.erp_cp7_get_kasbon_v1(%s)',(contractor,));b.api.admin(cur);return w
def kasbon(cur,action,payload,w,key=None,subject=None):
    auth.actor(cur,subject)
    r=one(cur,'select public.erp_cp7_save_kasbon_v1(%s,%s,%s,%s)',(action,json.dumps(payload),str(key or uuid.uuid4()),w['review_token']));b.api.admin(cur);return r
def kasbon_give(cur,contractor,bank,amount,day,key=None):
    # The cash review token comes from the kasbon workspace, as the screen takes it (computed under UTC there; a token
    # computed in this session's own time zone does not match, job 116054424923).
    w=kasbon_read(cur,contractor);token=next(x['review_token'] for x in w['cash_accounts'] if x['id']==bank)
    return kasbon(cur,'GIVE',dict(contractor_id=contractor,cash_account_id=bank,cash_review_token=token,advance_date=str(day),amount=amount,reason='CP17 kasbon tunai'),w,key)
def kasbon_allocate(cur,contractor,advance,payroll,amount,key=None):
    w=kasbon_read(cur,contractor);d=next(x for x in w['payroll_drafts'] if x['id']==payroll)
    return kasbon(cur,'ALLOCATE',dict(contractor_id=contractor,advance_id=advance,payroll_id=payroll,payroll_version=d['row_version'],amount=amount),w,key)
def receivable(cur,contractor):
    b.api.admin(cur)
    return D(one(cur,"select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id "
                     "where l.contractor_id=%s and l.account_id=erp.account_id('CONTRACTOR_RECEIVABLE') and j.status in('POSTED','REVERSED')",(contractor,)))

def wib(day,hour=12):return pay.invoice.aa.at(day,hour).isoformat()


# ---------------------------------------------------------------- FIN01 (owner D14-2)
def early_then_paid(cur,f,pid,net,day):
    """Refused one day before the accrual, paid on it; the bank holds owner capital from that day (D14-3)."""
    bank=s.cash(cur,None);funding.fund(cur,bank,net,day);b.api.admin(cur)
    before=b.boundary.snapshot(cur)
    detail=refused(cur,lambda:s.act(cur,'PAY',s.doc(cur,pid),payment_date=str(day-timedelta(days=1)),cash_account_id=bank),'CP7_PAYROLL_PAID_BEFORE_ACCRUAL')
    unchanged(cur,before,'early payroll payment');assert s.doc(cur,pid)['status']=='APPROVED'
    s.act(cur,'PAY',s.doc(cur,pid),payment_date=str(day),cash_account_id=bank)
    assert s.doc(cur,pid)['status']=='PAID' and s.journal(cur,pid,'PAYROLL_PAYMENT')[1]==net and balance(cur,bank)==0
    return detail,bank

# ---------------------------------------------------------------- SG-02 / SG-01 fixtures (native cases and browser cases)
def fabric_fixture(cur,today):
    """A posted cutting of 10 from one roll: 7 consumed, 3 recorded as left (Native writers, as cutting.posted)."""
    src=cut.cutting;prod=src.qc.physical.b.chain.production;base=src.qc.physical.base
    f=prod.estimated_receipt(cur,today);b.api.admin(cur)
    day=f['purchase_day']+timedelta(days=1);po=str(uuid.uuid4())
    cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes) values(%s,%s,%s,10,'CUTTING','CUTTING',%s,'CP17 SG-02 fixture')",
        (po,'CP17-RET-'+po,prod.MODEL,prod.at(day,7)))
    payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=f['location'],cut_at=prod.at(day,8),
        change_reason='CP17 SG-02 posted cutting with fabric left',size_slots=[dict(slot_no=1,size_id=base.SIZE,drawing_no=1)],
        rolls=[dict(roll_id=f['roll'],qty_issued=10,qty_consumed=7,qty_reported_remaining=3,yields=[dict(slot_no=1,qty_pcs=10)])])
    saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload)
    prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(payload,id=saved['cutting_group_id'],action='POST'),expected_version=int(saved['row_version']))
    b.api.admin(cur)
    return dict(group=saved['cutting_group_id'],po=po,roll=str(f['roll']),location=str(f['location']))
def mandor_row(cur,tag):
    b.api.admin(cur)
    return str(one(cur,"insert into erp.contractors(contractor_code,contractor_name,contractor_type,is_active,attendance_required)values(%s,%s,'MANDOR',true,false)returning id",(tag,tag)))
def native_pickup(cur,group,contractor_id,at):
    """The ordinary Native pickup: draft, then POST distributing all 10 pieces in one batch."""
    prod=cut.cutting.qc.physical.b.chain.production;b.api.admin(cur)
    y=str(one(cur,'select y.id from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id where r.cutting_group_id=%s',(group,)))
    p=dict(action='SAVE_DRAFT',cutting_group_id=group,contractor_id=contractor_id,picked_up_at=at,allocation_mode='ROLL',
           expected_group_version=int(one(cur,'select row_version from erp.cutting_groups where id=%s',(group,))),
           change_reason='CP17 SG-01 bagi potongan',batches=[dict(batch_no=1,allocations=[dict(cutting_roll_yield_id=y,qty_pcs=10)])])
    d=prod.rpc(cur,'public.erp_save_cutting_pickup_v1',p)
    d=prod.rpc(cur,'public.erp_save_cutting_pickup_v1',dict(p,id=d['pickup_id'],action='POST'),expected_version=int(d['row_version']));b.api.admin(cur)
    assert d['status']=='POSTED',d
    return d['pickup_id']
def pickup_fixture(cur,today):
    """A posted cutting of 10 (Native writers) on a PO without a Mandor, distributed by the Native pickup POST."""
    src=cut.cutting;prod=src.qc.physical.b.chain.production;base=src.qc.physical.base
    f=prod.estimated_receipt(cur,today);b.api.admin(cur)
    day=f['purchase_day']+timedelta(days=1);po=str(uuid.uuid4())
    cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes) values(%s,%s,%s,10,'CUTTING','CUTTING',%s,'CP17 SG-01 fixture')",
        (po,'CP17-PICK-'+po,prod.MODEL,prod.at(day,7)))
    payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=f['location'],cut_at=prod.at(day,8),
        change_reason='CP17 SG-01 posted cutting',size_slots=[dict(slot_no=1,size_id=base.SIZE,drawing_no=1)],
        rolls=[dict(roll_id=f['roll'],qty_issued=10,qty_consumed=10,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=10)])])
    saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload)
    saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(payload,id=saved['cutting_group_id'],action='POST'),expected_version=int(saved['row_version']))
    g=saved['cutting_group_id'];b.api.admin(cur)
    # Oracle: the PO and group as they were before the pickup, read directly (not from the audit trail the command uses).
    po_before=cur.execute('select status,current_stage,contractor_id from erp.production_orders where id=%s',(po,)).fetchone()
    executor=one(cur,'select executor_name from erp.cutting_groups where id=%s',(g,))
    m=mandor_row(cur,'CP17-SG01-A-'+uuid.uuid4().hex[:8]);pk=native_pickup(cur,g,m,prod.at(day,9))
    assert one(cur,'select contractor_id::text from erp.production_orders where id=%s',(po,))==m
    return dict(group=g,po=po,pickup=pk,mandor=m,at=lambda h:prod.at(day,h),po_before=po_before,executor=executor)

def cases(cur,today):
    def full_attendance():
        f,pid,net=approved_payroll(cur,today);day=accrued_day(cur,f['contractor'])
        assert day==today==one(cur,"select max(economic_date) from erp.journal_entries where source_id=%s and source_type='PAYROLL_ATTENDANCE_ACCRUAL' and status='POSTED'",(pid,))
        detail,_=early_then_paid(cur,f,pid,net,day)
        return dict(status='PASS',attendance_accrued=str(day),paid_one_day_earlier_refused=detail,paid_on_accrual_day=True,net=str(net))
    def work_only():
        f,pid,net=approved_payroll(cur,today,attendance=False);day=accrued_day(cur,f['contractor'])
        assert day is not None and one(cur,"select count(*) from erp.journal_entries where source_id=%s and source_type='PAYROLL_ATTENDANCE_ACCRUAL'",(pid,))==0
        detail,_=early_then_paid(cur,f,pid,net,day)
        return dict(status='PASS',work_accrued=str(day),paid_one_day_earlier_refused=detail,paid_on_work_day=True,net=str(net))
    def installment():
        f=instal.fixture(cur,today);day=accrued_day(cur,f['contractor']);assert str(day)==f['payment_date'],(day,f['payment_date'])
        bank=f['cash']['id']  # holds the payroll's net from the earliest open business date (instal.fixture, D14-3)
        before=b.boundary.snapshot(cur);f['payment_date']=str(day-timedelta(days=1))
        detail=refused(cur,lambda:instal.act(cur,f,amount='600.00'),'CP7_PAYROLL_PAID_BEFORE_ACCRUAL');unchanged(cur,before,'early installment')
        f['payment_date']=str(day);instal.act(cur,f,amount='600.00');instal.act(cur,f,amount='400.00')
        assert s.doc(cur,f['payroll'])['status']=='PAID' and balance(cur,bank)==0
        return dict(status='PASS',attendance_accrued=str(day),early_installment_refused=detail,installments_600_400_on_accrual_day=True)
    def direct_native():
        f,pid,net=approved_payroll(cur,today);day=accrued_day(cur,f['contractor']);early=day-timedelta(days=1)
        # Capital before the early date, so only the payroll date rule can refuse the direct Native call.
        bank=s.cash(cur,None);funding.fund(cur,bank,net,early-timedelta(days=1));b.api.admin(cur)
        cur.execute('update erp.payroll_settlements set payment_date=%s,payment_cash_account_id=%s where id=%s',(early,bank,pid))
        before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:bc.internal(cur,'post_payroll_payment',pid),'CP7_PAYROLL_PAID_BEFORE_ACCRUAL');unchanged(cur,before,'direct Native payment')
        cur.execute('update erp.payroll_settlements set payment_date=%s where id=%s',(day,pid));bc.internal(cur,'post_payroll_payment',pid);b.api.admin(cur)
        assert s.doc(cur,pid)['status']=='PAID' and balance(cur,bank)==0
        return dict(status='PASS',direct_Native_post_payroll_payment_early_refused=detail,same_call_on_accrual_day_paid=True)

    # ------------------------------------------------------------ CASH (owner D14-3)
    def empty_bank():
        f=pay.fixture(cur,today);assert balance(cur,f['cash'])==0;p=pay.payload(cur,f,'1.00');before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:pay.command(cur,p),'CP7_CASH_NEGATIVE');unchanged(cur,before,'empty bank')
        assert balance(cur,f['cash'])==0 and pay.state(cur,f)['payments']==[]
        return dict(status='PASS',empty_bank_supplier_payment_refused=detail,witness='Sol SOL_CASH_EMPTY_BANK_WITHOUT_OVERDRAFT_POLICY')
    def exact_zero():
        f=pay.funded(cur,today,'100');r=pay.command(cur,pay.payload(cur,f,'100.00'));assert r['status']=='POSTED' and balance(cur,f['cash'])==0
        before=b.boundary.snapshot(cur);detail=refused(cur,lambda:pay.command(cur,pay.payload(cur,f,'0.01')),'CP7_CASH_NEGATIVE');unchanged(cur,before,'one cent over')
        assert pay.read(cur,f)['Native_AP']['remaining']=='900.00'
        return dict(status='PASS',capital100_paid100_bank_zero_allowed=True,one_more_cent_refused_while_AP900_open=detail)
    def backdate():
        f=pay.fixture(cur,today);funded=today-timedelta(days=1);funding.fund(cur,f['cash'],'100',funded);b.api.admin(cur)
        p=dict(pay.payload(cur,f,'60.00'),payment_date=wib(today-timedelta(days=2)));before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:pay.command(cur,p),'CP7_CASH_NEGATIVE');unchanged(cur,before,'payment before the money came in')
        r=pay.command(cur,dict(pay.payload(cur,f,'60.00'),payment_date=wib(funded)));assert r['status']=='POSTED' and balance(cur,f['cash'])==40
        return dict(status='PASS',current_balance100_but_payment_dated_before_capital_refused=detail,same_payment_on_capital_day_posted=True)
    def later_day():
        f=pay.funded(cur,today,'100');r=pay.command(cur,pay.payload(cur,f,'100.00'));assert r['status']=='POSTED' and balance(cur,f['cash'])==0
        p=dict(pay.payload(cur,f,'50.00'),payment_date=wib(today-timedelta(days=2)));before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:pay.command(cur,p),'CP7_CASH_NEGATIVE');unchanged(cur,before,'backdated payment breaking a later day')
        return dict(status='PASS',backdated50_fits_its_own_day_but_today_would_be_minus50_refused=detail)
    def payroll_empty():
        f,pid,net=approved_payroll(cur,today);day=accrued_day(cur,f['contractor']);bank=s.cash(cur,None);assert balance(cur,bank)==0
        before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:s.act(cur,'PAY',s.doc(cur,pid),payment_date=str(day),cash_account_id=bank),'CP7_CASH_NEGATIVE');unchanged(cur,before,'payroll from empty bank')
        assert s.doc(cur,pid)['status']=='APPROVED'
        return dict(status='PASS',lawful_payroll_date_but_empty_bank_refused=detail)
    def laundry_empty():
        f=bd.fixture(cur,today-timedelta(days=3),'CP17-CASH-LAUNDRY');bd.process_rate(cur,f,'20.00');bd.invoice_policies(cur)
        delivery=bd.plain_delivery(cur,f,5,11);receipt=bd.receive(cur,delivery,f,4,13);line=bd.receipt_line(cur,receipt['receipt_id'])
        draft,_=bd.invoice(cur,f,[dict(line=line,qty=4,amount='80.00')],'80.00');b.api.admin(cur)
        bank=str(bc.bank_account(cur,'CP17L'+uuid.uuid4().hex[:8]));vendor=dict(target_kind='VENDOR_INVOICE',target_id=draft['invoice_id'],amount='80.00',date=str(f['day']),cash_account_id=bank,reason='CP17 pelunasan tagihan laundry')
        before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:bd.bd(cur,'PAY_VENDOR_DOCUMENT',vendor),'CP7_CASH_NEGATIVE');unchanged(cur,before,'laundry vendor from empty bank')
        funding.fund(cur,bank,'80.00',f['day']);b.api.admin(cur);paid=bd.bd(cur,'PAY_VENDOR_DOCUMENT',vendor);b.api.admin(cur)
        assert paid['remaining']=='0.00' and balance(cur,bank)==0 and D(bd.ap(cur,f['vendor']))==0
        return dict(status='PASS',empty_bank_vendor_payment_refused=detail,funded_same_day_paid=True)

    # ------------------------------------------------------------ FIN02 (Astra/Fable)
    def claim_fixture(invoice_day_offset=0):
        f=bd.fixture(cur,today-timedelta(days=3),'CP17-CLAIM');bd.process_rate(cur,f,'20.00');bd.invoice_policies(cur)
        delivery=bd.plain_delivery(cur,f,5,11);receipt=bd.receive(cur,delivery,f,4,13);line=bd.receipt_line(cur,receipt['receipt_id'])
        bd.invoice(cur,dict(f,day=f['day']+timedelta(days=invoice_day_offset)),[dict(line=line,qty=4,amount='80.00')],'80.00')
        number='CP17-CLAIM-'+uuid.uuid4().hex[:12]
        bd.d12_bs(cur,'SAVE_CLAIM',dict(action='SAVE',claim_number=number,vendor_id=f['vendor'],delivery_id=delivery,qty_claimed=1,claim_type='MISSING',
            compensation_amount=0,opened_at=str(f['day'])+'T15:00:00+07:00',change_reason='CP17 lima dikirim, empat kembali, satu hilang'))
        b.api.admin(cur);claim=str(one(cur,'select id from erp.laundry_claims where claim_number=%s',(number,)))
        return f,claim
    def settle(f,claim,day):
        def run():
            version=lambda:one(cur,'select row_version from erp.laundry_claims where id=%s',(claim,))
            bd.d12_bs(cur,'SAVE_CLAIM',dict(id=claim,action='SAVE',status='ACCEPTED',compensation_amount=20,resolution_date=str(day),change_reason='CP17 vendor setuju ganti dua puluh'),version())
            bd.d12_bs(cur,'RESOLVE_CLAIM',dict(laundry_claim_id=claim,resolution='SETTLED',change_reason='CP17 klaim diselesaikan'),version())
            b.api.admin(cur)
        return run
    def dated_ap(cur,vendor,day):
        b.api.admin(cur)
        return D(one(cur,"select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id "
                         "where l.vendor_id=%s and l.account_id=erp.account_id('AP_VENDOR') and j.status in('POSTED','REVERSED') and j.economic_date<=%s",(vendor,day)))
    def claim_control():
        f,claim=claim_fixture();assert dated_ap(cur,f['vendor'],f['day'])==80
        settle(f,claim,f['day'])();assert one(cur,'select status from erp.laundry_claims where id=%s',(claim,))=='SETTLED'
        assert dated_ap(cur,f['vendor'],f['day'])==60 and D(bd.ap(cur,f['vendor']))==60
        return dict(status='PASS',same_day_compensation20_dated_AP80_to60=True)
    def claim_before_source():
        f,claim=claim_fixture();before=b.boundary.snapshot(cur)
        detail=refused(cur,settle(f,claim,f['day']-timedelta(days=1)),'CP7_LAUNDRY_CLAIM_BEFORE_SOURCE');unchanged(cur,before,'claim before its source')
        assert one(cur,'select status from erp.laundry_claims where id=%s',(claim,))=='OPEN' and dated_ap(cur,f['vendor'],f['day'])==80
        return dict(status='PASS',settled_the_day_before_delivery_and_claim_refused=detail,witness='Astra CP17-ASTRA-CLAIM-02-BEFORE-SOURCE')
    def claim_ap_not_available():
        f,claim=claim_fixture(invoice_day_offset=1);later=f['day']+timedelta(days=1)
        assert dated_ap(cur,f['vendor'],f['day'])==0 and D(bd.ap(cur,f['vendor']))==80
        before=b.boundary.snapshot(cur)
        detail=refused(cur,settle(f,claim,f['day']),'CP7_LAUNDRY_CLAIM_AP_NOT_AVAILABLE');unchanged(cur,before,'claim before the vendor payable exists')
        settle(f,claim,later)();assert dated_ap(cur,f['vendor'],later)==60 and dated_ap(cur,f['vendor'],f['day'])==0
        return dict(status='PASS',current_AP80_but_dated_AP0_on_claim_day_refused=detail,same_claim_after_invoice_day_settled=True)

    # ------------------------------------------------------------ STK01 (Astra)
    def stock_card():
        f=cut.fixture(cur,today);roll=f['roll']
        location,material_id=cur.execute('select g.source_location_id::text,r.material_id::text from erp.cutting_groups g,erp.material_rolls r where g.id=%s and r.id=%s',(f['group'],roll)).fetchone()
        p,v=cut.payload(cur,f);r=cut.command(cur,p,v);d=cut.verify_effect(cur,f,p,r)
        prod=cut.cutting.qc.physical.b.chain.production
        again=dict(id=f['group'],action='SAVE_DRAFT',po_id=f['po'],pattern_id=d['pattern_id'],source_location_id=d['source_location_id'],cut_at=d['cut_at'],
            change_reason='CP17 STK01 posted again on its own cutting day',size_slots=[{k:x[k]for k in('slot_no','size_id','drawing_no','label_override')}for x in d['size_slots']],
            rolls=[dict(roll_id=roll,qty_issued=int(f['qty']),qty_consumed=int(f['qty']),qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=10)])])
        saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',again,expected_version=int(r['row_version']))
        prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(again,action='POST'),expected_version=int(saved['row_version']));b.api.admin(cur)
        stock=cut.stock(cur,f);assert stock==f['before_stock'],(stock,f['before_stock'])
        moves=cur.execute('select qty_signed,reversal_of_id is not null from erp.material_stock_movements where roll_id=%s and location_id=%s',(roll,location)).fetchall()
        assert sum(q for q,_ in moves)==stock and sum(1 for _,rv in moves if rv)>=1
        f.update(material=material_id)
        v1=material.ledger(cur,f,location)['page']
        auth.actor(cur);v2=one(cur,'select public.erp_cp7_get_material_ledger_v2(%s,%s,%s,0,100)',(material_id,roll,location))['page'];b.api.admin(cur)
        for name,page in(('v1',v1),('v2',v2)):
            run=[D(x['running_qty'])for x in page['rows']]
            assert page['next_offset']is None and run and min(run)>=0,(name,'CP17_STK01_NEGATIVE_PREFIX',page['rows'])
            assert run[0]==stock,(name,run,stock)
        assert int(v1['total'])==len(moves)
        corrected=[x for x in v2['rows']if int(x['correction_count'])>0]
        assert corrected and all(D(x['qty_signed'])==0 for x in corrected),v2['rows']
        return dict(status='PASS',reopen_then_repost_same_cut_day=True,stock=str(stock),v1_running=[x['running_qty']for x in v1['rows']],
                    v2_running=[x['running_qty']for x in v2['rows']],all_rows_kept_v1=len(moves),witness='Astra STK01 (prefix -10)')

    # ------------------------------------------------------------ RWK01 (Astra/Fable)
    def rework(outcome):
        """Two components actually re-sewn by the contractor at rate 30 (Astra's witness flow), then GOOD, all SCRAP, or left open."""
        combined,nb=nota.combined,nota.b
        f=combined.fixture(cur,today);wash=combined.wash(cur,f,range(4),11);combined.finish(cur,f,[wash],range(4),13,bs={3:2})
        bs=str(one(cur,"select id from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'",(f['po'],f['roots'][3])))
        nb.chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=combined.prod.COMPONENT,completed_before_bs_qty=0)],change_reason='CP17 dua komponen belum dikerjakan'),nb.chain.version(cur,'bs_cases',bs))
        b.api.admin(cur)  # bs_action leaves the session as the authenticated actor; these lookups are admin reads
        component=str(one(cur,'select id from erp.bs_case_components where bs_case_id=%s and work_component_id=%s',(bs,combined.prod.COMPONENT)))
        bom=str(one(cur,'select erp.resolve_rework_accessory_bom_v1(%s,%s)',(bs,f['when'](15))))
        made=nb.chain.bs_action(cur,'SAVE_REWORK',dict(rework_number='CP17-RW-'+uuid.uuid4().hex[:10],bs_case_id=bs,destination_type='CONTRACTOR',contractor_id=combined.prod.CONTRACTOR,vendor_id=None,qty_sent=2,
            physical_sent_at=f['when'](15).isoformat(),status='IN_PROGRESS',return_fg_location_id=combined.base.LOCATION,accessory_bom_version_id=bom,accessory_bom_item_ids=[],change_reason='CP17 dua perbaikan dikerjakan',
            components=[dict(bs_case_component_id=component,qty_performed=2)]))
        rid=made['result']['rework_order_id'];good=outcome=='GOOD'
        nb.chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=2 if good else 0,qty_bs=0 if good else 2,completed_at=f['when'](16).isoformat(),return_fg_location_id=combined.base.LOCATION,change_reason='CP17 perbaikan selesai'),nb.chain.version(cur,'rework_orders',rid))
        if outcome=='SCRAP':
            nb.chain.bs_action(cur,'DISPOSE_BS',dict(bs_case_id=bs,resolution_type='SCRAP',qty_pcs=2,compensation_amount=0,source_laundry_claim_id=None,physical_at=f['when'](17).isoformat(),change_reason='CP17 dua potong dibuang'),nb.chain.version(cur,'bs_cases',bs))
        b.api.admin(cur)
        accrued=cur.execute("select coalesce(sum(l.credit-l.debit),0) from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_type='REWORK_COMPLETION' and j.source_id=%s and j.status='POSTED' and l.account_id=erp.account_id('CONTRACTOR_PAYABLE')",(rid,)).fetchone()[0]
        assert accrued==60,('CP17_RWK01_ACCRUAL',accrued)
        cards=lambda:[c for c in nota.read(cur,'SOURCES',contractor_id=combined.prod.CONTRACTOR)['page']['rows']if c['origin_id']==rid]
        return dict(f=f,bs=bs,rework=rid,status=one(cur,'select status from erp.bs_cases where id=%s',(bs,)),cards=cards,contractor=combined.prod.CONTRACTOR)
    def paid_once(r):
        found=r['cards']();assert len(found)==1 and D(found[0]['remaining_amount'])==60 and found[0]['lines'][0]['remaining_qty']=='2',found
        card=dict(card_key=found[0]['card_key'],source_token=found[0]['source_token'])
        payload=dict(contractor_id=r['contractor'],note_date=str(today),period_start=str(today),period_end=str(today),cards=[card])
        posted=nota.act(cur,'POST',nota.command(cur,'SAVE',payload));b.api.admin(cur)
        assert one(cur,'select labor_total from erp.payroll_settlements where id=%s',(posted['payroll_id'],))==60 and r['cards']()==[]
        before=b.boundary.snapshot(cur);detail=refused(cur,lambda:nota.command(cur,'SAVE',payload),'');unchanged(cur,before,'second Nota on the same rework')
        return posted,detail
    def rework_scrap():
        r=rework('SCRAP');assert r['status']=='SCRAPPED',r['status']
        posted,again=paid_once(r)
        return dict(status='PASS',bs_case='SCRAPPED',accrued_rework_wage=60,on_one_Nota=posted['payroll_id'],second_Nota_refused=again,witness='Astra ASTRA-CP17-RWK-01')
    def rework_good():
        r=rework('GOOD');assert r['status']=='RESOLVED',r['status']
        posted,again=paid_once(r)
        return dict(status='PASS',bs_case='RESOLVED',accrued_rework_wage=60,on_one_Nota=posted['payroll_id'],second_Nota_refused=again)
    def rework_open():
        # An all-BS return with nothing resolved is OPEN (canonical reducer erp.refresh_bs_case_status; the CP5 proof
        # cp5_bs_resolution_recovery_rollback.sql requires OPEN, not the legacy PARTIAL). Disposing 1 of 2 makes it PARTIAL.
        r=rework('OPEN');assert r['status']=='OPEN',r['status']
        eligible=lambda:one(cur,"select count(*) from erp.v_payroll_eligible_work_lines where source_type='REWORK' and bs_case_id=%s",(r['bs'],))
        assert r['cards']()==[];b.api.admin(cur);assert eligible()==0
        nota.b.chain.bs_action(cur,'DISPOSE_BS',dict(bs_case_id=r['bs'],resolution_type='SCRAP',qty_pcs=1,compensation_amount=0,source_laundry_claim_id=None,
            physical_at=r['f']['when'](17).isoformat(),change_reason='CP17 satu dari dua potong dibuang'),nota.b.chain.version(cur,'bs_cases',r['bs']))
        b.api.admin(cur);assert one(cur,'select status from erp.bs_cases where id=%s',(r['bs'],))=='PARTIAL'
        assert r['cards']()==[];b.api.admin(cur);assert eligible()==0
        return dict(status='PASS',bs_case=['OPEN','PARTIAL'],accrued=60,not_yet_on_a_Nota=True,rule='only final outcomes RESOLVED/SCRAPPED/WRITTEN_OFF are payable (owner decision pending for PARTIAL/ON_HOLD)')

    # ------------------------------------------------------------ HPP01 (Astra/Fable); fixture after Astra's pool witness
    day=today-timedelta(days=1)
    def native_call(sql,args):return instal.physical.source.fixture_journal_call(cur,sql,args)
    def policy(cid,effective):
        return s.native(cur,'select public.erp_set_contractor_hpp_policy_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=cid,effective_from=str(effective),
            is_special=False,attendance_required=True,reason='CP17 kebijakan mandor biasa')),uuid.uuid4()))
    def contractor(tag):
        b.api.admin(cur);return str(one(cur,'insert into erp.contractors(contractor_code,contractor_name,attendance_required)values(%s,%s,true)returning id',(tag,tag)))
    def attendance_payroll(cid,tag):
        """One earned attendance day 1000 on `day`, approved (the Native accrual debits WIP)."""
        instal.physical.source.receipt.aa.prior.set_open_period(cur,day-timedelta(days=1))
        pid=str(one(cur,'insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,payment_date)values(%s,%s,%s,%s,%s)returning id',(tag,cid,day,day,day)))
        w=s.native(cur,'select public.erp_save_worker_roster_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=cid,worker_code=tag,worker_name=tag,job_description='Jahit',pay_scheme='DAILY',
            initial_daily_rate=1000,rate_effective_from=str(day),joined_at=str(day),is_active=True,reason='CP17 satu hari kerja')),uuid.uuid4()))
        ap=s.native(cur,'select public.erp_save_attendance_period_v1(%s::jsonb,%s,null,false)',(json.dumps(dict(contractor_id=cid,period_number=tag+'-ATT',period_start=str(day),period_end=str(day),
            pay_date=str(day),reason='CP17 absensi nyata',attendance=[dict(worker_id=str(bc.awp.find(w,'worker_id')),attendance_date=str(day),status='PRESENT')])),uuid.uuid4()))
        s.native(cur,'select public.erp_post_attendance_period_v1(%s,%s,%s,%s)',(bc.awp.find(ap,'period_id'),'CP17 absensi diposting',uuid.uuid4(),bc.awp.find(ap,'row_version')))
        s.act(cur,'PREPARE',s.doc(cur,pid));s.act(cur,'APPROVE',s.doc(cur,pid));assert D(s.doc(cur,pid)['attendance_total'])==1000
        return pid
    def sewn(cid,label):
        prod=instal.wip_source.b.chain.production;old=prod.CONTRACTOR
        try:
            prod.CONTRACTOR=cid;return instal.wip_source.b.two_size_fixture(cur,today+timedelta(days=1),label,q1=7,q2=3)
        finally:prod.CONTRACTOR=old
    def active_pool():
        native_call('select erp.preview_attendance_hpp_pool_v1(%s,%s)',(day,day))
        made=native_call('select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',(json.dumps(dict(period_start=str(day),period_end=str(day),reason='CP17 pool absensi')),uuid.uuid4()))
        native_call('select erp.activate_attendance_hpp_pool_v1(%s,%s,%s,%s)',(made['pool_id'],'CP17 sumber diperiksa',uuid.uuid4(),made['row_version']));b.api.admin(cur)
        return made['pool_id']
    def pool_state(pool):
        b.api.admin(cur)
        return cur.execute('select status,numerator_amount,denominator_qty,unit_cost_per_sewn_pcs,source_manifest_sha256 from erp.attendance_hpp_pools where id=%s',(pool,)).fetchone()
    def hpp_fixture():
        a=contractor('CP17-HPP-A-'+uuid.uuid4().hex[:8]);attendance_payroll(a,'CP17-HPP-'+uuid.uuid4().hex[:10]);policy(a,day-timedelta(days=1));sewn(a,'CP17-HPP-A')
        c=contractor('CP17-HPP-C-'+uuid.uuid4().hex[:8]);sewn(c,'CP17-HPP-C')
        pool=active_pool();state=pool_state(pool)
        assert state[0]=='ACTIVE' and (D(state[1]),int(state[2]),D(state[3]))==(1000,10,100),state
        native_call('select erp.validate_attendance_hpp_pool_v1(%s)',(pool,))
        return a,c,pool,state
    def hpp_excluded():
        a,c,pool,state=hpp_fixture();before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:policy(c,day-timedelta(days=1)),'CP7_HPP_POLICY_CHANGES_ACTIVE_POOL');unchanged(cur,before,'policy that would make the ACTIVE pool stale')
        assert pool_state(pool)==state;native_call('select erp.validate_attendance_hpp_pool_v1(%s)',(pool,))
        return dict(status='PASS',excluded_contractor_policy_refused=detail,pool_still_valid_1000_10_100=True,witness='Astra CP17-ASTRA-POOL-03-POLICY-AFTER-ACTIVE')
    def hpp_unrelated():
        a,c,pool,state=hpp_fixture();d=contractor('CP17-HPP-D-'+uuid.uuid4().hex[:8])
        policy(d,day-timedelta(days=1));assert pool_state(pool)==state;native_call('select erp.validate_attendance_hpp_pool_v1(%s)',(pool,))
        return dict(status='PASS',policy_for_contractor_without_facts_in_the_period_accepted=True,pool_unchanged_and_valid=True)
    def hpp_replacement():
        a,c,pool,state=hpp_fixture()
        version=one(cur,'select row_version from erp.attendance_hpp_pools where id=%s',(pool,))
        native_call('select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',(pool,'CP17 batalkan sebelum kebijakan baru',uuid.uuid4(),version))
        assert pool_state(pool)[0]=='CANCELLED',pool_state(pool)
        policy(c,day-timedelta(days=1));replacement=active_pool();new=pool_state(replacement)
        assert new[0]=='ACTIVE' and (D(new[1]),int(new[2]),D(new[3]))==(1000,20,50),new
        native_call('select erp.validate_attendance_hpp_pool_v1(%s)',(replacement,))
        return dict(status='PASS',cancel_then_policy_then_replacement_pool=True,replacement_1000_over_20_is_50=True,original_pool='CANCELLED')

    # ------------------------------------------------------------ SG-02 (owner D14-4): fabric back to the warehouse
    def fabric_posted():return fabric_fixture(cur,today)
    def return_read(g):
        auth.actor(cur);w=one(cur,'select public.erp_cp7_get_cutting_return_v1(%s)',(g['group'],));b.api.admin(cur);return w
    def return_payload(w,qty,at=None):
        return dict(group_id=w['group_id'],po_id=w['po_id'],review_token=w['review_token'],returned_at=at or datetime.now(timezone.utc).isoformat(timespec='seconds'),
            change_reason='CP17 sisa kain kembali ke gudang',rolls=[dict(cutting_group_roll_id=w['rolls'][0]['cutting_group_roll_id'],qty_returned=qty)])
    def return_send(w,p,key=None):
        auth.actor(cur);r=one(cur,'select public.erp_cp7_return_cutting_fabric_v1(%s,%s,%s)',(json.dumps(p),str(key or uuid.uuid4()),w['row_version']));b.api.admin(cur);return r
    def roll_stock(g):
        return D(one(cur,'select coalesce(sum(qty_signed),0) from erp.material_stock_movements where roll_id=%s and location_id=%s',(g['roll'],g['location'])))
    def po_wip(g):
        return D(one(cur,"select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status='POSTED' and l.account_id=erp.account_id('WIP') and l.po_id=%s",(g['po'],)))
    def returns(g):
        return cur.execute("select qty_signed,input_unit_cost,roll_id::text,location_id::text from erp.material_stock_movements where source_type='CUTTING_GROUP_RETURN' and source_id=%s and movement_type='CUTTING_RETURN'",(g['group'],)).fetchall()
    def fabric_return():
        g=fabric_posted();w=return_read(g)
        assert w['eligible'] and w['blockers']==[] and len(w['rolls'])==1 and D(w['rolls'][0]['qty_reported_remaining'])==3 and w['business_DML'] is False,w
        cost=D(w['rolls'][0]['unit_cost']);value=(2*cost).quantize(D('0.01'),rounding=ROUND_HALF_UP);assert value>0
        stock0,wip0=roll_stock(g),po_wip(g)
        p=return_payload(w,'2');r=return_send(w,p)
        assert r['action']=='RETURN_FABRIC' and r['group_id']==g['group'] and D(r['value'])==value,(r,value)
        assert roll_stock(g)-stock0==2 and returns(g)==[(D(2),cost,g['roll'],g['location'])],returns(g)
        assert wip0-po_wip(g)==value,('CP17_SG02_PO_COST_NOT_REDUCED',wip0,po_wip(g),value)
        lines=cur.execute("select case l.account_id when erp.account_id('MATERIAL_INVENTORY') then 'MATERIAL_INVENTORY' when erp.account_id('WIP') then 'WIP' else l.account_id::text end k,l.debit,l.credit,l.po_id::text "
                          "from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_type='CUTTING_MATERIAL_RETURN_LINE' and j.source_id=%s and j.status='POSTED' order by 1",(w['rolls'][0]['cutting_group_roll_id'],)).fetchall()
        assert lines==[('MATERIAL_INVENTORY',value,D(0),g['po']),('WIP',D(0),value,g['po'])],lines
        row=cur.execute('select qty_physically_returned,return_destination,returned_at=%s::timestamptz from erp.cutting_group_rolls where cutting_group_id=%s',(p['returned_at'],g['group'])).fetchone()
        assert row==(D(2),'WAREHOUSE',True),row
        assert one(cur,'select material_return_posted from erp.cutting_groups where id=%s',(g['group'],))
        assert one(cur,'select count(*) from cp7_cutting_correction.return_history where group_id=%s',(g['group'],))==1
        after=return_read(g);assert not after['eligible'] and {x['kind']for x in after['blockers']}=={'ALREADY_RETURNED','RETURN_FACTS_PRESENT'},after
        reopen=cut.read(cur,dict(group=g['group']));assert any(x['kind']=='MATERIAL_FLOW' for x in reopen['blockers']),reopen
        return dict(status='PASS',same_roll_back_in_stock=2,issue_unit_cost=str(cost),po_WIP_reduced_by=str(value),journal='Dr MATERIAL_INVENTORY / Cr WIP (PO)',
                    once_per_cutting=True,reopen_after_return_blocked=True,owner_decision='D14-4')
    def fabric_over():
        g=fabric_posted();w=return_read(g);before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:return_send(w,return_payload(w,'3.000001')),'CP7_CUTTING_RETURN_OVER_REMAINING');unchanged(cur,before,'return above the recorded remainder')
        stock0=roll_stock(g);r=return_send(w,return_payload(w,'3'))
        assert roll_stock(g)-stock0==3 and returns(g)[0][0]==3 and r['rolls'][0]['qty_returned']=='3'
        return dict(status='PASS',more_than_remainder_refused=detail,exact_remainder3_returned=True)
    def fabric_once():
        g=fabric_posted();w=return_read(g);key=uuid.uuid4();p=return_payload(w,'1')
        first=return_send(w,p,key);stock1=roll_stock(g);again=return_send(w,p,key)
        assert again==first and len(returns(g))==1 and roll_stock(g)==stock1,('CP17_SG02_REPLAY_NOT_IDENTICAL',first,again)
        fresh=return_read(g);assert not fresh['eligible']
        before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:return_send(fresh,return_payload(fresh,'1')),'CP7_CUTTING_RETURN_DEPENDENCIES');unchanged(cur,before,'second return of one cutting')
        stale=refused(cur,lambda:return_send(w,return_payload(w,'1')),'CP7_CUTTING_RETURN_STALE_REVIEW');unchanged(cur,before,'return on a stale review')
        assert len(returns(g))==1 and roll_stock(g)==stock1
        return dict(status='PASS',same_request_replay_identical=True,second_return_refused=detail,stale_review_refused=stale)
    def fabric_dates():
        g=fabric_posted();w=return_read(g);cut_at=datetime.fromisoformat(w['cut_at']);before=b.boundary.snapshot(cur)
        early=refused(cur,lambda:return_send(w,return_payload(w,'1',(cut_at-timedelta(minutes=1)).isoformat())),'CP7_CUTTING_RETURN_BEFORE_CUT');unchanged(cur,before,'return before the cut')
        future=refused(cur,lambda:return_send(w,return_payload(w,'1',(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(timespec='seconds'))),'CP7_CUTTING_RETURN_IN_FUTURE');unchanged(cur,before,'return in the future')
        r=return_send(w,return_payload(w,'1',cut_at.isoformat()))
        assert datetime.fromisoformat(r['returned_at'])==cut_at and one(cur,"select (j.economic_date=(%s::timestamptz at time zone 'Asia/Jakarta')::date) from erp.journal_entries j where j.source_type='CUTTING_MATERIAL_RETURN_LINE' and j.source_id=%s",(cut_at.isoformat(),w['rolls'][0]['cutting_group_roll_id']))
        return dict(status='PASS',one_minute_before_cut_refused=early,tomorrow_refused=future,at_cut_time_returned_and_journal_on_WIB_day=True)

    # ------------------------------------------------------------ Detector: rows in the books from before the guards
    def legacy_findings():
        def without(trigger,table,action):
            b.api.admin(cur);cur.execute('alter table erp.'+table+' disable trigger '+trigger)
            try:return action()
            finally:b.api.admin(cur);cur.execute('alter table erp.'+table+' enable trigger '+trigger)
        def found(kind,subject):
            b.api.admin(cur)
            return [r for r in cur.execute('select kind,subject_id::text,on_day,amount,floor_day from cp7_guard.findings()').fetchall() if r[0]==kind and r[1]==subject]
        # A supplier payment of 7.00 out of an empty bank, as data posted before the guard would hold it.
        f=pay.fixture(cur,today);p=pay.payload(cur,f,'7.00');without('cp7_guard_cash_not_negative','journal_lines',lambda:pay.command(cur,p))
        pay_day=one(cur,"select max(j.economic_date) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.cash_accounts c on c.coa_account_id=l.account_id where c.id=%s",(f['cash'],))
        cash=found('CASH_NEGATIVE',f['cash']);assert cash==[('CASH_NEGATIVE',f['cash'],pay_day,D('-7'),None)],cash
        # A payroll paid one day before its accrual through the direct Native call.
        g,pid,net=approved_payroll(cur,today);day=accrued_day(cur,g['contractor']);early=day-timedelta(days=1)
        bank=s.cash(cur,None);funding.fund(cur,bank,net,early);b.api.admin(cur)
        cur.execute('update erp.payroll_settlements set payment_date=%s,payment_cash_account_id=%s where id=%s',(early,bank,pid))
        without('cp7_payroll_paid_date_guard','payroll_settlements',lambda:bc.internal(cur,'post_payroll_payment',pid))
        paid=found('PAYROLL_PAID_BEFORE_ACCRUAL',pid);assert paid==[('PAYROLL_PAID_BEFORE_ACCRUAL',pid,early,None,day)],paid
        # Owner capital dated on the payment day clears the cash row; the early payroll stays listed.
        funding.fund(cur,f['cash'],'7.00',pay_day)
        assert found('CASH_NEGATIVE',f['cash'])==[] and found('PAYROLL_PAID_BEFORE_ACCRUAL',pid)
        assert not any(cur.execute("select has_function_privilege(r,'cp7_guard.findings()','EXECUTE') from unnest(array['anon','authenticated','service_role']) r").fetchall()[i][0] for i in range(3))
        return dict(status='PASS',empty_bank_payment_listed=dict(day=str(pay_day),lowest='-7.00'),early_payroll_listed=dict(paid=str(early),accrued=str(day)),
                    capital_on_that_day_clears_cash_row=True,detector_owner_only=True)

    # ------------------------------------------------------------ D14-6 kasbon tunai
    def kasbon_payroll():
        """A work-only payroll draft (6000.00 earned on its WIB work day) and a funded bank."""
        f=s.review.fixture(cur,today);c=f['contractor'];pid=f['payroll'];day=accrued_day(cur,c);bank=s.cash(cur);opened=funding.open_day(cur)
        return f,c,pid,day,bank,max(opened,day-timedelta(days=1))
    def kasbon_cycle():
        f,c,pid,day,bank,kday=kasbon_payroll();bank0=balance(cur,bank);r0=receivable(cur,c)
        given=kasbon_give(cur,c,bank,'2500.00',kday);k=given['advance'];assert k['free']=='2500.00' and k['advance_date']==str(kday),k
        assert balance(cur,bank)-bank0==-2500 and receivable(cur,c)-r0==2500
        assert one(cur,"select economic_date from erp.journal_entries where source_type='CP7_KASBON' and source_id=%s and status='POSTED'",(k['id'],))==kday
        a=kasbon_allocate(cur,c,k['id'],pid,'2500.00');assert a['payroll']['deduction_total']=='2500.00' and a['payroll']['net_payable']=='3500.00',a
        d=s.doc(cur,pid);s.act(cur,'PREPARE',d);d=s.doc(cur,pid);s.act(cur,'APPROVE',d);d=s.doc(cur,pid)
        s.act(cur,'PAY',d,payment_date=str(day),cash_account_id=bank);b.api.admin(cur)
        assert s.doc(cur,pid)['status']=='PAID' and s.journal(cur,pid,'PAYROLL_CASH_ADVANCE_DEDUCTION')[1]==2500 and s.journal(cur,pid,'PAYROLL_PAYMENT')[2]==3500
        assert receivable(cur,c)==r0 and balance(cur,bank)-bank0==-6000
        st=kasbon_read(cur,c)['advances'][0];assert st['recovered']=='2500.00' and st['free']=='0.00',st
        before=b.boundary.snapshot(cur)
        used=refused(cur,lambda:kasbon(cur,'CANCEL',dict(contractor_id=c,advance_id=k['id'],reason='CP17 tidak boleh batal'),kasbon_read(cur,c)),'CP7_KASBON_IN_USE');unchanged(cur,before,'cancel a recovered kasbon')
        b.api.admin(cur);truth=one(cur,"select issue_count from erp.run_v267_financial_truth_checks() where check_name='AP_CASH_ADVANCE_SOURCE'")
        assert truth==0,truth
        return dict(status='PASS',kasbon_before_wages=str(kday),wages_accrued=str(day),deducted=2500,paid_cash=3500,receivable_back_to_start=True,
                    cancel_after_recovery_refused=used,truth_AP_CASH_ADVANCE_SOURCE=0,owner_decision='D14-6')
    def kasbon_limits():
        f,c,pid,day,bank,kday=kasbon_payroll();empty=s.cash(cur,None);before=b.boundary.snapshot(cur);out={}
        out['empty_bank']=refused(cur,lambda:kasbon_give(cur,c,empty,'10.00',kday),'CP7_CASH_NEGATIVE');unchanged(cur,before,'kasbon from an empty bank')
        out['future']=refused(cur,lambda:kasbon_give(cur,c,bank,'10.00',today+timedelta(days=1)),'CP7_KASBON_IN_FUTURE');unchanged(cur,before,'kasbon in the future')
        closed=one(cur,'select closed_through from erp.accounting_period_control where singleton_id=1')
        out['closed']=refused(cur,lambda:kasbon_give(cur,c,bank,'10.00',closed),'CP7_KASBON_PERIOD_CLOSED');unchanged(cur,before,'kasbon in a closed period')
        k=kasbon_give(cur,c,bank,'7000.00',kday)['advance'];before=b.boundary.snapshot(cur)
        out['over_earnings']=refused(cur,lambda:kasbon_allocate(cur,c,k['id'],pid,'6000.01'),'CP7_KASBON_OVER_EARNINGS');unchanged(cur,before,'deduction above earnings')
        small=kasbon_give(cur,c,bank,'100.00',kday)['advance'];before=b.boundary.snapshot(cur)
        out['over_remaining']=refused(cur,lambda:kasbon_allocate(cur,c,small['id'],pid,'100.01'),'CP7_KASBON_OVER_REMAINING');unchanged(cur,before,'deduction above the kasbon')
        out['direct_deduction']=refused(cur,lambda:cur.execute("insert into erp.payroll_deductions(payroll_id,deduction_type,amount) values(%s,'CASH_ADVANCE',5)",(pid,)),'CP7_KASBON_DEDUCTION_PRIVATE');unchanged(cur,before,'direct kasbon deduction')
        jid=one(cur,'select journal_id from cp7_kasbon.advances where id=%s',(k['id'],))
        # The journal guard is probed as the owner of the Native writer (authenticated cannot even call it).
        out['direct_reverse']=refused(cur,lambda:instal.physical.source.fixture_journal_call(cur,'select erp.reverse_journal(%s,%s)',(jid,'CP17 bypass')),'CP7_KASBON_JOURNAL_PRIVATE');unchanged(cur,before,'direct reverse of a kasbon journal')
        out['direct_reverse_as_authenticated']=refused(cur,lambda:bc.internal(cur,'reverse_journal',jid,'CP17 bypass'),'permission denied for function reverse_journal');unchanged(cur,before,'authenticated reverse of a kasbon journal')
        d=s.doc(cur,pid);s.act(cur,'PREPARE',d);d=s.doc(cur,pid);s.act(cur,'APPROVE',d);b.api.admin(cur);before=b.boundary.snapshot(cur)
        w=kasbon_read(cur,c);assert all(x['id']!=pid for x in w['payroll_drafts'])
        late=dict(contractor_id=c,advance_id=small['id'],payroll_id=pid,payroll_version=s.doc(cur,pid)['row_version'],amount='1.00')
        out['approved_payroll']=refused(cur,lambda:kasbon(cur,'ALLOCATE',late,w),'');unchanged(cur,before,'deduction on an approved payroll')
        return dict(status='PASS',**out)
    def kasbon_release():
        f,c,pid,day,bank,kday=kasbon_payroll();bank0=balance(cur,bank);r0=receivable(cur,c)
        k=kasbon_give(cur,c,bank,'800.00',kday)['advance'];assert balance(cur,bank)-bank0==-800
        kasbon_allocate(cur,c,k['id'],pid,'500.00');before=b.boundary.snapshot(cur)
        used=refused(cur,lambda:kasbon(cur,'CANCEL',dict(contractor_id=c,advance_id=k['id'],reason='CP17 batal saat dipesan'),kasbon_read(cur,c)),'CP7_KASBON_IN_USE');unchanged(cur,before,'cancel while reserved')
        released=kasbon_allocate(cur,c,k['id'],pid,'0');assert released['advance']['free']=='800.00' and released['payroll']['deduction_total']=='0.00',released
        w=kasbon_read(cur,c);ckey=uuid.uuid4();payload=dict(contractor_id=c,advance_id=k['id'],reason='CP17 kasbon salah catat')
        cancelled=kasbon(cur,'CANCEL',payload,w,ckey);replay=kasbon(cur,'CANCEL',payload,w,ckey)
        assert cancelled==replay and cancelled['advance']['status']=='CANCELLED' and balance(cur,bank)==bank0 and receivable(cur,c)==r0
        rev=one(cur,"select count(*) from erp.journal_entries j join cp7_kasbon.advances a on a.cancel_journal_id=j.id where a.id=%s and j.reversal_of_id=a.journal_id",(k['id'],))
        assert rev==1
        return dict(status='PASS',cancel_while_reserved_refused=used,release_frees_kasbon=True,cancel_reverses_journal=True,same_request_replay_identical=True,bank_back_to_start=True)

    # ------------------------------------------------------------ SG-03 (D06 / LAU-06a): free rewash of the same product
    def rewash_free():
        combined,nb=nota.combined,nota.b
        f=combined.fixture(cur,today);wash=combined.wash(cur,f,range(4),11);combined.finish(cur,f,[wash],range(4),13,bs={3:2});b.api.admin(cur)
        bs=str(one(cur,"select id from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'",(f['po'],f['roots'][3])))
        nb.chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=combined.prod.COMPONENT,completed_before_bs_qty=0)],
            change_reason='CP17 cuci ulang produk sama'),nb.chain.version(cur,'bs_cases',bs))
        b.api.admin(cur);bom=str(one(cur,'select erp.resolve_rework_accessory_bom_v1(%s,%s)',(bs,f['when'](15))))
        vendor_lines=lambda:one(cur,'select count(*) from erp.journal_lines where vendor_id=%s',(f['vendor'],))
        vendor_ap=lambda:D(one(cur,"select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.vendor_id=%s and l.account_id=erp.account_id('AP_VENDOR') and j.status in('POSTED','REVERSED')",(f['vendor'],)))
        lines0,ap0=vendor_lines(),vendor_ap()
        made=nb.chain.bs_action(cur,'SAVE_REWORK',dict(rework_number='CP17-RWASH-'+uuid.uuid4().hex[:10],bs_case_id=bs,destination_type='LAUNDRY',contractor_id=None,vendor_id=f['vendor'],
            qty_sent=2,physical_sent_at=f['when'](15).isoformat(),status='IN_PROGRESS',return_fg_location_id=combined.base.LOCATION,accessory_bom_version_id=bom,
            accessory_bom_item_ids=[],components=[],change_reason='CP17 cuci ulang garansi di vendor'))
        rid=made['result']['rework_order_id']
        done=nb.chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=2,qty_bs=0,completed_at=f['when'](16).isoformat(),return_fg_location_id=combined.base.LOCATION,
            change_reason='CP17 cuci ulang selesai'),nb.chain.version(cur,'rework_orders',rid));b.api.admin(cur)
        assert vendor_lines()==lines0 and vendor_ap()==ap0,('CP17_SG03_VENDOR_MONEY',vendor_lines(),lines0,vendor_ap(),ap0)
        assert one(cur,'select count(*) from erp.journal_entries where source_id=%s',(rid,))==0,'CP17_SG03_REWORK_JOURNAL'
        assert one(cur,'select count(*) from erp.rework_component_lines where rework_order_id=%s',(rid,))==0
        lot=done['result'].get('good_fg_lot_id');assert lot and one(cur,'select product_id::text from erp.fg_lots where id=%s',(lot,))==str(f['roots'][3])
        return dict(status='PASS',rewash_same_product=True,vendor_payable_unchanged=str(ap0),vendor_journal_lines_unchanged=lines0,no_rework_wage=True,
                    good_pieces_back_as_same_product=2,owner_decision='D06 / Lampiran C6 LAU-06a')

    # ------------------------------------------------------------ SG-01 (FABLE-009 / Astra SG-01): reverse a POSTED pickup before sewing
    def mandor(tag):return mandor_row(cur,tag)
    def pickup_post(group,contractor_id,at):return native_pickup(cur,group,contractor_id,at)
    def picked():return pickup_fixture(cur,today)
    def pickup_read(g):
        auth.actor(cur);w=one(cur,'select public.erp_cp7_get_pickup_reversal_v1(%s)',(g['group'],));b.api.admin(cur);return w
    def pickup_send(w,reason='CP17 salah mandor, bagi ulang',key=None,token=None):
        p=dict(group_id=w['group_id'],pickup_id=w['pickup_id'],review_token=token or w['review_token'],change_reason=reason)
        auth.actor(cur);r=one(cur,'select public.erp_cp7_reverse_pickup_v1(%s,%s,%s)',(json.dumps(p),str(key or uuid.uuid4()),w['pickup_version']));b.api.admin(cur);return r
    def material_facts(g):
        return (one(cur,'select count(*) from erp.material_stock_movements where source_id=%s',(g['group'],)),
                one(cur,'select count(*) from erp.journal_lines where po_id=%s',(g['po'],)))
    def pickup_reverse():
        g=picked();w=pickup_read(g)
        assert w['eligible'] and w['blockers']==[] and w['business_DML'] is False and w['pickup_id']==g['pickup'] and w['pieces']==10,w
        assert w['restore']['clear_mandor'] is True and w['restore']['executor_name']==g['executor'],(w['restore'],g['executor'])
        assert [w['restore']['po_status'],w['restore']['po_stage']]==list(g['po_before'][:2]),(w['restore'],g['po_before'])
        facts0=material_facts(g);key=uuid.uuid4()
        r=pickup_send(w,key=key);again=pickup_send(w,key=key)
        assert again==r and r['action']=='REVERSE_PICKUP' and r['result']['pickup_status']=='REVERSED' and r['result']['mandor_cleared'] is True,r
        assert cur.execute('select status,reversal_reason,reversed_by is not null from erp.cutting_pickups where id=%s',(g['pickup'],)).fetchone()==('REVERSED','CP17 salah mandor, bagi ulang',True)
        grp=cur.execute('select status,picked_up_at,executor_name,material_issue_posted from erp.cutting_groups where id=%s',(g['group'],)).fetchone()
        assert grp==('CUT',None,g['executor'],True),grp
        assert cur.execute('select status,current_stage,contractor_id from erp.production_orders where id=%s',(g['po'],)).fetchone()==g['po_before']
        assert one(cur,'select count(*) from erp.cutting_distribution_batches where pickup_id=%s',(g['pickup'],))==1,'CP17_SG01_HISTORY_NOT_KEPT'
        assert material_facts(g)==facts0,('CP17_SG01_STOCK_OR_JOURNAL_CHANGED',facts0,material_facts(g))
        assert one(cur,'select count(*) from cp7_cutting_correction.pickup_history where pickup_id=%s',(g['pickup'],))==1
        # The group waits again: the ordinary Native POST distributes it to the right Mandor.
        right=mandor('CP17-SG01-B-'+uuid.uuid4().hex[:8]);reposted=pickup_post(g['group'],right,g['at'](10))
        assert one(cur,'select contractor_id::text from erp.production_orders where id=%s',(g['po'],))==right
        assert one(cur,'select status from erp.cutting_pickups where id=%s',(g['pickup'],))=='REVERSED'
        return dict(status='PASS',pickup='REVERSED',cutting_group='CUT with fabric still posted',po_restored=[str(x) for x in g['po_before']],mandor_cleared=True,
                    batches_kept_as_history=True,no_stock_or_journal=True,same_request_replay_identical=True,reposted_to_other_mandor=reposted)
    def pickup_refused():
        g=picked();w=pickup_read(g);before=b.boundary.snapshot(cur)
        # Outside the command the two Native guards refuse exactly as before.
        direct=refused(cur,lambda:cur.execute("update erp.cutting_pickups set status='REVERSED',reversed_by=posted_by,reversed_at=clock_timestamp(),reversal_reason='langsung' where id=%s",(g['pickup'],)),
                       'POSTED_CUTTING_PICKUP_IS_IMMUTABLE')
        clear=refused(cur,lambda:cur.execute('update erp.cutting_groups set picked_up_at=null where id=%s',(g['group'],)),'Pickup date cannot be cleared')
        unchanged(cur,before,'direct pickup writes')
        stale=refused(cur,lambda:pickup_send(w,token='0'*32),'CP7_PICKUP_REVERSAL_STALE_REVIEW');unchanged(cur,before,'stale review')
        short=refused(cur,lambda:pickup_send(w,reason='x'),'CP7_PICKUP_REVERSAL_FIELDS');unchanged(cur,before,'short reason')
        # Sewing started (a draft work completion): the reversal names it and refuses.
        wc=uuid.uuid4();b.chain.peer.ordinary(cur)
        cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)values(%s,%s,%s,%s,%s,%s,'DRAFT','CP17 SG-01 jahit draf',%s)",
                    (wc,'CP17-WC-'+str(wc),g['po'],g['mandor'],g['group'],g['at'](11),b.chain.base.OPERATOR_APP));b.api.admin(cur)
        w2=pickup_read(g);assert not w2['eligible'] and any(x['kind']=='WORK_COMPLETION' and x['id']==str(wc) for x in w2['blockers']),w2['blockers']
        before=b.boundary.snapshot(cur)
        blocked=refused(cur,lambda:pickup_send(w2),'CP7_PICKUP_REVERSAL_DEPENDENCIES');unchanged(cur,before,'reversal after sewing started')
        assert one(cur,'select status from erp.cutting_pickups where id=%s',(g['pickup'],))=='POSTED'
        return dict(status='PASS',native_guards_still_refuse=[direct,clear],stale_review_refused=stale,short_reason_refused=short,after_sewing_started_refused=blocked)

    named=[full_attendance,work_only,installment,direct_native,empty_bank,exact_zero,backdate,later_day,payroll_empty,laundry_empty,
           claim_control,claim_before_source,claim_ap_not_available,stock_card,rework_scrap,rework_good,rework_open,
           hpp_excluded,hpp_unrelated,hpp_replacement,fabric_return,fabric_over,fabric_once,fabric_dates,legacy_findings,
           kasbon_cycle,kasbon_limits,kasbon_release,rewash_free,pickup_reverse,pickup_refused]
    assert len(named)==REQUIRED['native']
    return list(zip(IDS['native'],named))


def races(tools,today):
    def two_payments():
        with tools.connect()as conn,conn.cursor()as cur:
            first=pay.funded(cur,today,'100');second=pay.fixture(cur,today);second['cash']=first['cash']
            payloads=[pay.payload(cur,first,'60.00'),pay.payload(cur,second,'60.00')];conn.commit()
        barrier=threading.Barrier(2)
        def send(p):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=pay.command(cur,p);conn.commit();return('PASS',r['payment_id'])
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(30)for x in[pool.submit(send,p)for p in payloads]]
        assert sorted(x[0]for x in results)==['PASS','REFUSED']and 'CP7_CASH_NEGATIVE'in next(x[1]for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:assert balance(cur,first['cash'])==40
        return dict(status='PASS',two_purchases_one_bank100_two_payments60_one_posted_one_refused=results)
    def attendance_once():
        # FABLE-007 regression (refuted by Astra PAY02/PAY03 on sequential routes; concurrency was not certified): one
        # posted attendance day, two payroll drafts of the same Mandor covering that day, both prepared at once. The
        # contractor advisory lock in the CP7 settlement command serializes them, so the day lands in one payroll only.
        with tools.connect()as conn,conn.cursor()as cur:
            f=s.review.fixture(cur,today);s.attendance(cur,f,today);b.api.admin(cur)
            second=nota.seed_header(cur,f,today,today);docs=[s.doc(cur,f['payroll']),s.doc(cur,second)];conn.commit()
        barrier=threading.Barrier(2)
        def send(d):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=s.act(cur,'PREPARE',d);conn.commit();return('PASS',r['status'])
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(60)for x in[pool.submit(send,d)for d in docs]]
        with tools.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur)
            days=cur.execute("select count(*) from erp.attendance_records where contractor_id=%s and attendance_date=%s",(f['contractor'],today)).fetchone()[0]
            items=dict(cur.execute("select payroll_id::text,count(*) from erp.payroll_attendance_items where payroll_id in(%s,%s) group by 1",(f['payroll'],second)).fetchall())
            dup=cur.execute("select count(*) from(select i.attendance_record_id from erp.payroll_attendance_items i join erp.payroll_settlements p on p.id=i.payroll_id "
                            "where p.status<>'REVERSED' and p.contractor_id=%s group by 1 having count(*)>1)x",(f['contractor'],)).fetchone()[0]
            detector=[r for r in(x[0] for x in cur.execute('select to_jsonb(r) from erp.run_integrity_checks() r').fetchall())if 'PAYROLL_ATTENDANCE_DUPLICATE' in r.values()]
        assert any(x[0]=='PASS' for x in results),results
        assert days>=1 and sum(items.values())==days and len(items)==1 and dup==0,(days,items,dup,results)
        assert all(0 in r.values() for r in detector),detector
        return dict(status='PASS',posted_attendance_days=days,payrolls_holding_them=len(items),duplicates=0,prepares=results,integrity_detector=detector,finding='FABLE-007')
    return [('CP17_RACE_TWO_PAYMENTS_ONE_BANK',two_payments),('CP17_RACE_ATTENDANCE_ONE_PAYROLL',attendance_once)]


def http_cases(http,today):
    def cash_refused():
        owner=http.login('ADMIN','cp17-cash')
        with http.connect()as conn,conn.cursor()as cur:
            f=pay.fixture(cur,today);role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(owner.auth_user_id,))
            for key in pay.supplier.PERMISSIONS:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
            when=pay.at(cur);conn.commit()
        w=owner.rpc(pay.READ,dict(p_query=dict(purchase_id=f['receipt']['purchase_id'])));assert w['status']==200,w
        p=dict(purchase_id=f['receipt']['purchase_id'],review_token=w['body']['review_token'],amount='250.00',cash_account_id=f['cash'],payment_date=when,note=pay.NOTE)
        r=owner.rpc(pay.WRITE,dict(p_payload=p,p_request=str(uuid.uuid4())))
        assert r['status']==400 and 'CP7_CASH_NEGATIVE'in str(r['body']),r
        with http.connect()as conn,conn.cursor()as cur:
            assert balance(cur,f['cash'])==0 and pay.state(cur,f)['payments']==[]
            funding.fund(cur,f['cash'],'250.00',f['day']);conn.commit()
        ok=owner.rpc(pay.WRITE,dict(p_payload=p,p_request=str(uuid.uuid4())));assert ok['status']==200 and ok['body']['remaining_after']=='750.00',ok
        return dict(status='PASS',real_Auth_empty_bank_refused=r['body'].get('message'),same_payment_after_capital_posted=True)
    def payroll_early():
        user=http.login('ADMIN','cp17-payroll')
        with http.connect()as conn,conn.cursor()as cur:
            f,pid,net=approved_payroll(cur,today);day=accrued_day(cur,f['contractor']);bank=s.cash(cur,None);funding.fund(cur,bank,net,day-timedelta(days=1))
            _,role=s.source.procurement.custom(cur,s.PERMS);cur.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(role,user.auth_user_id));conn.commit()
        def read():
            r=user.rpc('erp_cp7_get_payroll_workspace_v1',dict(p_section='PAYROLLS',p_query=dict(id=pid)));assert r['status']==200,r;return r['body']['page']['rows'][0]
        d=read();early=dict(p_action='PAY',p_payload=s.args(d,'PAY',payment_date=str(day-timedelta(days=1)),cash_account_id=bank),p_request=str(uuid.uuid4()),p_expected=d['row_version'])
        r=user.rpc('erp_cp7_save_payroll_v1',early);assert r['status']==400 and 'CP7_PAYROLL_PAID_BEFORE_ACCRUAL'in str(r['body']),r
        assert read()['status']=='APPROVED'
        d=read();ok=user.rpc('erp_cp7_save_payroll_v1',dict(p_action='PAY',p_payload=s.args(d,'PAY',payment_date=str(day),cash_account_id=bank),p_request=str(uuid.uuid4()),p_expected=d['row_version']))
        assert ok['status']==200 and read()['status']=='PAID',ok
        return dict(status='PASS',real_Auth_early_payroll_refused=r['body'].get('message'),paid_on_accrual_day=str(day))
    def kasbon_give_http():
        admin=http.login('ADMIN','cp17-kasbon')
        with http.connect()as conn,conn.cursor()as cur:
            f=s.review.fixture(cur,today);c=f['contractor'];bank=s.cash(cur);day=funding.open_day(cur)
            role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,))
            for key in s.PERMS:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
            bank0=balance(cur,bank);conn.commit()
        w=admin.rpc('erp_cp7_get_kasbon_v1',dict(p_contractor=c));assert w['status']==200 and w['body']['advances']==[],w
        token=next(x['review_token'] for x in w['body']['cash_accounts'] if x['id']==bank)
        p=dict(contractor_id=c,cash_account_id=bank,cash_review_token=token,advance_date=str(day),amount='150.00',reason='CP17 kasbon lewat login')
        stale=admin.rpc('erp_cp7_save_kasbon_v1',dict(p_action='GIVE',p_payload=p,p_request=str(uuid.uuid4()),p_expected='0'*32))
        assert stale['status']==400 and 'CP7_KASBON_STALE_REVIEW' in str(stale['body']),stale
        r=admin.rpc('erp_cp7_save_kasbon_v1',dict(p_action='GIVE',p_payload=p,p_request=str(uuid.uuid4()),p_expected=w['body']['review_token']))
        assert r['status']==200 and r['body']['advance']['free']=='150.00' and r['body']['advance']['advance_date']==str(day),r
        with http.connect()as conn,conn.cursor()as cur:assert balance(cur,bank)-bank0==-150
        return dict(status='PASS',real_Auth_kasbon_given=r['body']['advance']['number'],stale_review_refused=True)
    def erp_writers_closed():
        """FABLE-012: the erp writers that nothing running with the caller's rights refers to are not reachable over the
        Data API. The PostgREST of this copy serves only `public` (PGRST_DB_SCHEMAS=public, as the hosted runbook
        requires); every such writer asked for through the erp profile is refused before any SQL runs."""
        import cp6_auditor_modes as modes,cp7_access_inventory as access
        user=http.login('OWNER','cp17-erp-direct')
        with http.connect()as conn,conn.cursor()as cur:
            inv=access.inventory(cur);before=b.boundary.snapshot(cur);conn.rollback()
        writers=inv['writers_without_invoker_reference'];assert len(writers)>=60,len(writers)
        refused,other=[],[]
        for sig in writers:
            name=sig.split('(',1)[0].split('.',1)[1]
            r=modes._call(modes.REST_URL+'/rpc/'+name,{},{'apikey':http._anon,'Authorization':'Bearer '+user._token,'Content-Profile':'erp'})
            body=r['body'] if isinstance(r['body'],dict) else {}
            (refused if r['status']==406 and body.get('code')=='PGRST106' else other).append([sig,r['status'],body.get('code')])
        assert not other,('CP17_ERP_WRITER_REACHABLE',other[:5])
        with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before,'CP17_ERP_DIRECT_CHANGED_BOUNDARY'
        return dict(status='PASS',writers_without_invoker_reference=len(writers),refused_by_data_api=len(refused),
                    refusal='406 PGRST106 (schema not exposed)',exposed_schemas=['public'],hosted_setting='to be read by Fable (owner D14-7)')
    return [('CP17_HTTP_CASH_EMPTY_BANK_REFUSED',cash_refused),('CP17_HTTP_PAYROLL_EARLY_REFUSED',payroll_early),('CP17_HTTP_KASBON_GIVE',kasbon_give_http),
            ('CP17_HTTP_ERP_WRITERS_NOT_REACHABLE',erp_writers_closed)]
