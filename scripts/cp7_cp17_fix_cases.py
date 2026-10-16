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
- FABLE-012 (D14-9): the EXECUTE revoke of the erp writers waits for CP7C; the exposure gate refuses a Data API
  setting that would reach schema erp while those writers are still executable by `authenticated`.
- SG-02 (D14-4): leftover fabric of a posted cutting goes back to the warehouse: the same roll returns to stock at its
  issue cost, the PO's WIP drops by exactly that value, at most the remainder recorded at cutting, once per cutting.
- R2-01 (owner D15-1; Fable FABLE-013, Sol SOL-R1-001, round dfab13bf): the cash guard also judges the book
  (transaction) date that the owner's daily cash report uses, and judges a compound correction (inverse, then
  replacement) on its end state. Fable's and Sol's scenarios run with their own amounts.
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
import cp7_payment_correction_cases as edit
import cp7_misc_cases as misc
import cp7_misc_correction_cases as misc_fix
import cp7_note_correction_cases as note_fix
import cp7_fg_adjustment_cases as fgadj
import cp7_master_cases as master
import cp7_auto_po_cases as autopo
import cp7_cutover_cases as cutover
import cp7_wave_sewing_cases as wave

auth,b,bc=s.auth,s.b,s.bc
refused=auth.refused
CONTRACT='cp7.cp17-fixes.v1'
FUNCTIONS=('erp_set_contractor_hpp_policy_v1','erp_cp7_save_nota_v1','erp_cp7_get_nota_workspace_v1','erp_save_bs_resolution_action_v1','erp_cp7_save_payroll_v1','erp_cp7_save_payroll_installment_v1','erp_cp7_create_supplier_payment_v1',
           'erp_save_laundry_bd_action_v1','erp_cp7_get_material_ledger_v1','erp_cp7_get_material_ledger_v2',
           'erp_cp7_get_cutting_return_v1','erp_cp7_return_cutting_fabric_v1','erp_cp7_get_cutting_correction_v1',
           'erp_cp7_get_kasbon_v1','erp_cp7_save_kasbon_v1','erp_cp7_get_pickup_reversal_v1','erp_cp7_reverse_pickup_v1',
           'erp_cp7_get_cutting_return_reversal_v1','erp_cp7_reverse_cutting_return_v1','erp_cp7_get_sewing_completion_v1','erp_cp7_save_sewing_completion_v1',
           'erp_cp7_list_po_finish_v1','erp_cp7_get_po_finish_v1','erp_cp7_finish_po_v1','erp_cp7_get_po_reopen_v1','erp_cp7_reopen_po_v1',
           'erp_cp7_save_misc_finance_v1','erp_cp7_correct_misc_finance_v1','erp_cp7_correct_sales_payment_v1','erp_cp7_get_sales_payment_correction_v1','erp_cp7_correct_note_v1')+master.FUNCTIONS+autopo.FUNCTIONS+cutover.FUNCTIONS
IDS=dict(
    native=['CP17_FIN01_FULL_PAY_BEFORE_ATTENDANCE_REFUSED','CP17_FIN01_WORK_ONLY_BEFORE_COMPLETION_REFUSED',
            'CP17_FIN01_INSTALLMENT_BEFORE_ACCRUAL_REFUSED','CP17_FIN01_DIRECT_NATIVE_PAYMENT_REFUSED',
            'CP17_CASH_EMPTY_BANK_REFUSED','CP17_CASH_EXACT_ZERO_ALLOWED_THEN_REFUSED','CP17_CASH_BACKDATE_BEFORE_FUNDS_REFUSED',
            'CP17_CASH_LATER_DAY_PROTECTED','CP17_CASH_PAYROLL_EMPTY_BANK_REFUSED','CP17_CASH_LAUNDRY_VENDOR_EMPTY_BANK_REFUSED',
            'CP17_FIN02_CLAIM_SAME_DAY_CONTROL','CP17_FIN02_CLAIM_BEFORE_SOURCE_REFUSED','CP17_FIN02_CLAIM_AP_NOT_AVAILABLE_REFUSED',
            'CP17_STK01_REOPEN_REPOST_CARD_NOT_NEGATIVE',
            'CP17_RWK01_ALL_SCRAP_REWORK_PAYABLE_ONCE','CP17_RWK01_GOOD_CONTROL','CP17_RWK01_OPEN_CASE_FINISHED_PART_PAID_ONCE',
            'CP17_HPP01_EXCLUDED_CONTRACTOR_POLICY_REFUSED','CP17_HPP01_UNRELATED_POLICY_CONTROL','CP17_HPP01_CANCEL_POLICY_REPLACEMENT_POOL',
            'CP17_SG02_RETURN_STOCK_VALUE_PO_COST','CP17_SG02_OVER_REMAINDER_REFUSED','CP17_SG02_ONCE_AND_SAME_REQUEST_REPLAY','CP17_SG02_BEFORE_CUT_OR_FUTURE_REFUSED',
            'CP17_SG02_CANCEL_RETURN_RESTORES_STOCK_GL_COST','CP17_SG02_CORRECT_RETURN_ONE_TRANSACTION','CP17_SG02_CANCEL_BLOCKED_BY_LATER_USE','CP17_SG02_CANCEL_REPLAY_ONCE_STALE',
            'CP17_DETECTOR_LISTS_LEGACY_ROWS',
            'CP17_KASBON_GIVE_DEDUCT_PAY','CP17_KASBON_LIMITS_REFUSED','CP17_KASBON_RELEASE_CANCEL_REPLAY',
            'CP17_SG03_REWASH_SAME_PRODUCT_NO_VENDOR_BILL',
            'CP17_SG01_PICKUP_REVERSE_BEFORE_SEWING','CP17_SG01_PICKUP_REVERSE_REFUSED',
            'CP17_FABLE012_EXPOSURE_GATE_REVOKE_FIRST',
            'CP17_G1_SEWING_RECORD_WAGE_READY_FOR_LAUNDRY','CP17_G1_SEWING_REFUSALS_UNCHANGED','CP17_G1_SEWING_CANCEL_ONLY_AT_MANDOR',
            'CP17_G2_FINISH_PO_FINAL_HPP_WIP_CLOSED','CP17_G2_FINISH_REFUSALS_UNCHANGED',
            'CP17_R2_CASH_BOOK_DATE_REFUSED','CP17_R2_SPENT_INCOME_CORRECTION_COMMITS','CP17_R2_SPENT_INCOME_NOTE_ONLY_COMMITS',
            'CP17_R2_SPENT_INCOME_GENUINE_NEGATIVE_REFUSED','CP17_R2_MISC_SPENT_INCOME_CORRECTION_COMMITS','CP17_R2_NOTE_CORRECTION_SPENT_PAYMENT_COMMITS',
            'CP17_R2_COMPOUND_SCOPE_PRIVATE_AND_CLOSED','CP17_R2_DETECTOR_BOOK_DATE_LISTED',
            'CP17_R2_ASTRA_G1_G2_TEN_PIECES_CONSERVED','CP17_R2_ASTRA_G2_UNSEWN_SIX_MUST_NOT_FINISH','CP17_R2_ASTRA_G2_SEWN_UNSENT_SIX_MUST_NOT_FINISH',
            'CP17_R2_PO_REOPEN_THEN_FINISH_SAME_HPP','CP17_R2_PO_REOPEN_BLOCKERS_UNCHANGED']+master.NATIVE+autopo.NATIVE+cutover.NATIVE+wave.NATIVE,
    races=['CP17_RACE_TWO_PAYMENTS_ONE_BANK','CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS','CP17_RACE_G1_SEWING_TWO_TABS_ONE_WINS','CP17_RACE_G2_FINISH_TWO_TABS_ONE_WINS',
           'CP17_RACE_R2_CORRECTION_AND_PAYMENT_ONE_BANK','CP17_RACE_R2_PO_REOPEN_TWO_TABS_ONE_WINS']+master.RACES+autopo.RACES+cutover.RACES+wave.RACES,
    http=['CP17_HTTP_CASH_EMPTY_BANK_REFUSED','CP17_HTTP_PAYROLL_EARLY_REFUSED','CP17_HTTP_KASBON_GIVE','CP17_HTTP_ERP_WRITERS_NOT_REACHABLE','CP17_HTTP_G1_SEWING_RECORD','CP17_HTTP_G2_FINISH_PO',
          'CP17_HTTP_R2_SPENT_INCOME_CORRECTION_COMMITS','CP17_HTTP_R2_SPENT_INCOME_GENUINE_NEGATIVE_REFUSED','CP17_HTTP_R2_PO_REOPEN']+master.HTTP+autopo.HTTP+cutover.HTTP+wave.HTTP,
    browser=['CP17_BROWSER_SG01_PICKUP_REVERSAL_DESKTOP','CP17_BROWSER_SG02_FABRIC_RETURN_MOBILE','CP17_BROWSER_KASBON_GIVE_DEDUCT_DESKTOP',
             'CP17_BROWSER_D14_5_SERIES_DOZENS_DESKTOP','CP17_BROWSER_D14_5_SERIES_DOZENS_MOBILE','CP17_BROWSER_SG02_FABRIC_RETURN_CORRECT_DESKTOP',
             'CP17_BROWSER_G1_SEWING_DESKTOP','CP17_BROWSER_G1_SEWING_MOBILE','CP17_BROWSER_G2_FINISH_DESKTOP','CP17_BROWSER_G2_FINISH_MOBILE',
             'CP17_BROWSER_R2_PO_REOPEN_DESKTOP','CP17_BROWSER_R2_PO_REOPEN_MOBILE']+master.BROWSER+autopo.BROWSER+cutover.BROWSER+wave.BROWSER,
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
def later_cutting(cur,g,at):
    """Another posted cutting (new PO, Native writers) that issues everything left on the same roll at the same warehouse."""
    src=cut.cutting;prod=src.qc.physical.b.chain.production;base=src.qc.physical.base;b.api.admin(cur)
    left=D(one(cur,'select coalesce(sum(qty_signed),0) from erp.material_stock_movements where roll_id=%s and location_id=%s',(g['roll'],g['location'])))
    qty=int(left) if left==int(left) else float(left);po=str(uuid.uuid4())
    cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes) values(%s,%s,%s,10,'CUTTING','CUTTING',%s,'CP17 SG-02 later use')",
        (po,'CP17-LATER-'+po,prod.MODEL,at))
    payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=g['location'],cut_at=at,
        change_reason='CP17 SG-02 kain kembali dipakai lagi',size_slots=[dict(slot_no=1,size_id=base.SIZE,drawing_no=1)],
        rolls=[dict(roll_id=g['roll'],qty_issued=qty,qty_consumed=qty,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=10)])])
    saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload)
    prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(payload,id=saved['cutting_group_id'],action='POST'),expected_version=int(saved['row_version']))
    b.api.admin(cur)
    return dict(group=saved['cutting_group_id'],number=one(cur,'select group_number from erp.cutting_groups where id=%s',(saved['cutting_group_id'],)),issued=left)
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
    return dict(group=g,po=po,pickup=pk,mandor=m,at=lambda h,minute=0:prod.at(day,h,minute),day=day,po_before=po_before,executor=executor)

# G1 (D14-14): the Work BOM, the CP7 sewing command and its oracles (Native rows and journals, not the command).
def work_rates(cur,g):
    """The PO model's Work BOM (two components, default rates 2 and 1) and a Mandor rate 3 for the first, from the fixture day.
    Native cases roll back, so each builds its own BOM. The browser fixtures commit: the second one (phone after desktop)
    finds the first one's BOM active on the same model and day (a second would overlap, Native guard_work_bom_overlap, first
    CI run on d53c4e92 kept) and reuses it after checking it is exactly that BOM."""
    prod=cut.cutting.qc.physical.b.chain.production;b.api.admin(cur)
    model=one(cur,'select model_id from erp.production_orders where id=%s',(g['po'],));since=g['at'](0)
    active=cur.execute("""select v.id from erp.work_bom_versions v where v.model_id=%s and v.is_active and v.effective_from<=%s
        and(v.effective_to is null or v.effective_to>%s)and v.notes='CP17 G1 BOM kerja' order by v.effective_from desc,v.version_no desc limit 1""",(model,since,since)).fetchone()
    if active:
        bom=active[0];items=cur.execute('select work_component_id::text,sequence_no,default_rate from erp.work_bom_items where bom_version_id=%s order by sequence_no',(bom,)).fetchall()
        assert [(c,n,r)for c,n,r in items if n==1]==[(str(prod.COMPONENT),1,D(2))] and len(items)==2 and items[1][1:]==(2,D(1)),('CP17_G1_REUSED_BOM_CHANGED',items)
        obras=items[1][0]
    else:
        bom=one(cur,'insert into erp.work_bom_versions(model_id,version_no,effective_from,notes)values(%s,(select coalesce(max(version_no),0)+1 from erp.work_bom_versions where model_id=%s),%s,%s)returning id',
            (model,model,since,'CP17 G1 BOM kerja'))
        obras=str(one(cur,'insert into erp.work_components(component_code,component_name)values(%s,%s)returning id',('CP17-OBRAS-'+uuid.uuid4().hex[:8],'CP17 Obras')))
        cur.execute('insert into erp.work_bom_items(bom_version_id,work_component_id,sequence_no,default_rate)values(%s,%s,1,2),(%s,%s,2,1)',(bom,prod.COMPONENT,bom,obras))
    cur.execute('insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from)values(%s,%s,%s,3,%s)',(g['mandor'],model,prod.COMPONENT,since))
    return dict(component=str(prod.COMPONENT),obras=obras)
def sewing_workspace(cur,g):
    auth.actor(cur);w=one(cur,'select public.erp_cp7_get_sewing_completion_v1(%s)',(g['group'],));b.api.admin(cur);return w
def sewing_command(cur,w,qty=None,at=None,event=None,reason='CP17 setoran jahit mandor',key=None,token=None,expected=None):
    p=dict(action='REVERSE' if event else 'RECORD',group_id=w['group_id'],review_token=token or w['review_token'],change_reason=reason)
    if event:p['event_id']=event
    else:p.update(qty_pcs=str(qty),physical_at=at.isoformat())
    auth.actor(cur);r=one(cur,'select public.erp_cp7_save_sewing_completion_v1(%s,%s,%s)',(json.dumps(p),str(key or uuid.uuid4()),expected or w['group_version']));b.api.admin(cur)
    return r
def wage_journal(cur,completion):
    return cur.execute("""select coalesce(sum(l.debit) filter(where l.account_id=erp.account_id('WIP')),0),
        coalesce(sum(l.credit) filter(where l.account_id=erp.account_id('CONTRACTOR_PAYABLE')),0),count(distinct j.id)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='WORK_COMPLETION' and j.source_id=%s and j.status='POSTED'""",(completion,)).fetchone()
def sewn_ready(cur,g):
    return cur.execute('select sewn_qty_pcs,unsent_ready_qty_pcs from erp.v_wip_control_status_v1 where cutting_group_id=%s',(g['group'],)).fetchone()
def laundry_for(cur,g):
    """A laundry vendor and wash process with a known rate on the group's distribution batch (the Native BD writers)."""
    b.api.admin(cur);vendor,process,tag=str(uuid.uuid4()),str(uuid.uuid4()),uuid.uuid4().hex[:10]
    cur.execute('insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active)values(%s,%s,%s,true)',(vendor,'CP17-G1-'+tag,'CP17 G1 laundry'))
    cur.execute('insert into erp.wash_processes(id,process_code,process_name,is_active)values(%s,%s,%s,true)',(process,'CP17-G1P-'+tag,'CP17 G1 wash'))
    batch=str(one(cur,"select d.id from erp.cutting_distribution_batches d join erp.cutting_pickups p on p.id=d.pickup_id where p.cutting_group_id=%s and p.status='POSTED'",(g['group'],)))
    wash=dict(vendor=vendor,process=process,day=g['day'],start=g['at'](0),batch=batch,group=g['group'])
    bd.process_rate(cur,wash,'2.00');b.api.admin(cur);return wash

# G2 (D14-14): finish a PO from the HPP screen; oracles from Native rows and journals, not the command.
def finish_fixture(cur,today,received=10,label='CP17-G2'):
    """Ten pieces of one PO through the chain's own writers: sewing, laundry out, `received` back GOOD and through QC into FG."""
    f=bd.fixture(cur,today-timedelta(days=3),label+'-'+uuid.uuid4().hex[:8]);bd.process_rate(cur,f,'2.00');b.api.admin(cur)
    delivery=bd.plain_delivery(cur,f,10,11);receipt=bd.receive(cur,delivery,f,received,13)['receipt_id'];b.api.admin(cur)
    product,lot=bd.finish_goods(cur,f,receipt,received,14);b.api.admin(cur)
    return dict(f,delivery=str(delivery),receipt=str(receipt),product=str(product),lot=str(lot),
                number=one(cur,'select po_number from erp.production_orders where id=%s',(f['po'],)))
def finish_workspace(cur,po):
    auth.actor(cur);w=one(cur,'select public.erp_cp7_get_po_finish_v1(%s)',(po,));b.api.admin(cur);return w
def finish_list(cur,query,offset=0):
    auth.actor(cur);w=one(cur,'select public.erp_cp7_list_po_finish_v1(%s,%s)',(query,offset));b.api.admin(cur);return w
def finish_command(cur,w,reason='CP17 PO selesai, HPP final',key=None,token=None,po=None):
    p=dict(action='FINISH',po_id=po or w['po_id'],review_token=token or w['review_token'],change_reason=reason)
    auth.actor(cur);r=one(cur,'select public.erp_cp7_finish_po_v1(%s,%s)',(json.dumps(p),str(key or uuid.uuid4())));b.api.admin(cur);return r
def po_wip_balance(cur,po):
    return one(cur,"""select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in('POSTED','REVERSED') and l.po_id=%s and l.account_id=erp.account_id('WIP')""",(po,))
def po_hpp(cur,po):
    return cur.execute("""select coalesce(sum(h.total_cost),0),coalesce(sum(h.qty_basis_pcs),0) from erp.fg_lots l join erp.v_current_hpp h on h.lot_id=l.id
        where l.po_id=%s and l.lot_origin='PRODUCTION'""",(po,)).fetchone()
def po_state(cur,po):
    return dict(status=one(cur,'select status from erp.production_orders where id=%s',(po,)),wip=po_wip_balance(cur,po),
                closed=one(cur,'select coalesce(sum(residual_amount),0) from erp.po_wip_close_events where po_id=%s',(po,)),
                history=one(cur,'select count(*) from cp7_cutting_correction.finish_history where po_id=%s',(po,)))
# R2-05 (owner D15-4, Fable FABLE-014): reopen a finished PO through the facade over Native erp.reopen_production_order.
def reopen_workspace(cur,po):
    auth.actor(cur);w=one(cur,'select public.erp_cp7_get_po_reopen_v1(%s)',(po,));b.api.admin(cur);return w
def reopen_command(cur,w,reason='CP17 PO dibuka ulang',key=None,token=None):
    p=dict(action='REOPEN',po_id=w['po_id'],review_token=token or w['review_token'],change_reason=reason)
    auth.actor(cur);r=one(cur,'select public.erp_cp7_reopen_po_v1(%s,%s)',(json.dumps(p),str(key or uuid.uuid4())));b.api.admin(cur);return r
def posted_closes(cur,po):
    return one(cur,"""select count(*) from erp.po_wip_close_events e join erp.journal_entries j on j.id=e.journal_entry_id
        where e.po_id=%s and j.source_type='PO_WIP_RESIDUAL_CLOSE' and j.status='POSTED'""",(po,))
def unbalanced_po_journals(cur,po):
    return cur.execute('select j.id from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where l.po_id=%s group by j.id having sum(l.debit)<>sum(l.credit)',(po,)).fetchall()

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
        """Owner D14-11: a BS case of 2 pieces, two rework orders of 1 piece. Order A comes back all BS (finished, counted and
        posted) while the case is still open: A's 30 is payable now. Order B is sent and not back yet: held. A is paid on
        one Nota. B then comes back GOOD (case PARTIAL): B is payable, A is not again. The last BS piece is scrapped (case
        closed): A still never returns to a Nota and B's 30 is the only rework wage left, so paid + left = accrued 60."""
        combined,nb=nota.combined,nota.b
        f=combined.fixture(cur,today);wash=combined.wash(cur,f,range(4),11);combined.finish(cur,f,[wash],range(4),13,bs={3:2})
        bs=str(one(cur,"select id from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'",(f['po'],f['roots'][3])))
        nb.chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=combined.prod.COMPONENT,completed_before_bs_qty=0)],change_reason='CP17 dua komponen belum dikerjakan'),nb.chain.version(cur,'bs_cases',bs))
        b.api.admin(cur)
        component=str(one(cur,'select id from erp.bs_case_components where bs_case_id=%s and work_component_id=%s',(bs,combined.prod.COMPONENT)))
        bom=str(one(cur,'select erp.resolve_rework_accessory_bom_v1(%s,%s)',(bs,f['when'](15))))
        def send(minute):
            made=nb.chain.bs_action(cur,'SAVE_REWORK',dict(rework_number='CP17-RW-'+uuid.uuid4().hex[:10],bs_case_id=bs,destination_type='CONTRACTOR',contractor_id=combined.prod.CONTRACTOR,vendor_id=None,qty_sent=1,
                physical_sent_at=f['when'](15,minute).isoformat(),status='IN_PROGRESS',return_fg_location_id=combined.base.LOCATION,accessory_bom_version_id=bom,accessory_bom_item_ids=[],change_reason='CP17 satu perbaikan dikerjakan',
                components=[dict(bs_case_component_id=component,qty_performed=1)]))
            b.api.admin(cur);return made['result']['rework_order_id']
        def complete(rid,good,hour,minute):
            nb.chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=1 if good else 0,qty_bs=0 if good else 1,completed_at=f['when'](hour,minute).isoformat(),return_fg_location_id=combined.base.LOCATION,change_reason='CP17 perbaikan selesai dan diperiksa'),nb.chain.version(cur,'rework_orders',rid))
            b.api.admin(cur)
        status=lambda:one(cur,'select status from erp.bs_cases where id=%s',(bs,))
        def cards(rid):
            found=[c for c in nota.read(cur,'SOURCES',contractor_id=combined.prod.CONTRACTOR)['page']['rows']if c['origin_id']==rid];b.api.admin(cur);return found
        eligible=lambda rid:[(str(r[0]),r[1]) for r in cur.execute("select e.source_id,e.remaining_amount from erp.v_payroll_eligible_work_lines e join erp.rework_component_lines l on l.id=e.source_id where e.source_type='REWORK' and l.rework_order_id=%s",(rid,)).fetchall()]
        accrued=lambda rid:cur.execute("select coalesce(sum(l.credit-l.debit),0) from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_type='REWORK_COMPLETION' and j.source_id=%s and j.status='POSTED' and l.account_id=erp.account_id('CONTRACTOR_PAYABLE')",(rid,)).fetchone()[0]
        a=send(0);complete(a,False,15,20);open_status=status()
        assert open_status not in('RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED'),open_status
        b_order=send(40);held_status=status()
        assert accrued(a)==30 and accrued(b_order)==0 and eligible(b_order)==[] and cards(b_order)==[],('CP17_RWK01_UNFINISHED_HELD',eligible(b_order))
        found=cards(a);assert len(found)==1 and D(found[0]['remaining_amount'])==30 and found[0]['lines'][0]['remaining_qty']=='1',found
        assert [D(x[1]) for x in eligible(a)]==[D(30)]
        payload=dict(contractor_id=combined.prod.CONTRACTOR,note_date=str(today),period_start=str(today),period_end=str(today),cards=[dict(card_key=found[0]['card_key'],source_token=found[0]['source_token'])])
        posted=nota.act(cur,'POST',nota.command(cur,'SAVE',payload));b.api.admin(cur)
        assert one(cur,'select labor_total from erp.payroll_settlements where id=%s',(posted['payroll_id'],))==30 and cards(a)==[] and eligible(a)==[]
        before=b.boundary.snapshot(cur);again=refused(cur,lambda:nota.command(cur,'SAVE',payload),'');unchanged(cur,before,'second Nota on the same finished rework part')
        complete(b_order,True,16,0);partial_status=status()
        assert partial_status not in('RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED'),partial_status
        assert accrued(b_order)==30 and cards(a)==[] and eligible(a)==[] and [D(x[1]) for x in eligible(b_order)]==[D(30)] and len(cards(b_order))==1
        nb.chain.bs_action(cur,'DISPOSE_BS',dict(bs_case_id=bs,resolution_type='SCRAP',qty_pcs=1,compensation_amount=0,source_laundry_claim_id=None,physical_at=f['when'](16,30).isoformat(),change_reason='CP17 potong BS terakhir dibuang'),nb.chain.version(cur,'bs_cases',bs))
        b.api.admin(cur);closed_status=status()
        assert closed_status in('RESOLVED','SCRAPPED','WRITTEN_OFF'),closed_status
        left=cards(b_order);assert cards(a)==[] and eligible(a)==[] and len(left)==1 and D(left[0]['remaining_amount'])==30
        paid=one(cur,"select coalesce(sum(w.amount),0) from erp.payroll_work_items w join erp.payroll_settlements s on s.id=w.payroll_id join erp.rework_component_lines l on l.id=w.source_id where w.source_type='REWORK' and s.status<>'REVERSED' and l.rework_order_id in(%s,%s)",(a,b_order))
        assert D(paid)+D(left[0]['remaining_amount'])==accrued(a)+accrued(b_order)==60,(paid,left)
        return dict(status='PASS',owner_decision='D14-11',bs_case=[open_status,held_status,partial_status,closed_status],finished_part_paid_while_open=30,
                    unfinished_part_held_until_back=True,one_Nota=posted['payroll_id'],second_Nota_refused=again,after_close_only_unpaid_part_left=30,paid_plus_left_equals_accrued=60)

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
        # Native ledger rule: a reversed journal stays in the ledger (status REVERSED) and its JOURNAL_REVERSAL offsets it,
        # as erp.account_daily_balances and the Native WIP health check count them. Counting only POSTED drops the original
        # but keeps its reversal (first D14-10 run 38666407687: WIP 120 instead of 100; log kept).
        return D(one(cur,"select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id('WIP') and l.po_id=%s",(g['po'],)))
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

    # ------------------------------------------------------------ SG-02 cancel / correct (owner D14-10)
    def reversal_read(g):
        auth.actor(cur);w=one(cur,'select public.erp_cp7_get_cutting_return_reversal_v1(%s)',(g['group'],));b.api.admin(cur);return w
    def reversal_payload(w,replacement=(),reason='CP17 kain kembali salah catat'):
        return dict(group_id=w['group_id'],po_id=w['po_id'],review_token=w['review_token'],change_reason=reason,
            replacement_rolls=[dict(cutting_group_roll_id=w['returned'][0]['cutting_group_roll_id'],qty_returned=q) for q in replacement])
    def reversal_send(w,p,key=None):
        auth.actor(cur);r=one(cur,'select public.erp_cp7_reverse_cutting_return_v1(%s,%s,%s)',(json.dumps(p),str(key or uuid.uuid4()),w['row_version']));b.api.admin(cur);return r
    def active_returns(g):
        return cur.execute("select m.qty_signed from erp.material_stock_movements m where m.source_type='CUTTING_GROUP_RETURN' and m.source_id=%s and not exists(select 1 from erp.material_stock_movements v where v.reversal_of_id=m.id) order by m.system_created_at",(g['group'],)).fetchall()
    def return_journals(g):
        return cur.execute("select j.status,(select count(*) from erp.journal_entries x where x.reversal_of_id=j.id and x.source_type='JOURNAL_REVERSAL' and x.status='POSTED') from erp.journal_entries j join erp.cutting_group_rolls r on r.id=j.source_id where r.cutting_group_id=%s and j.source_type='CUTTING_MATERIAL_RETURN_LINE' order by j.posting_at,j.id",(g['group'],)).fetchall()
    def material_avg(g):
        return D(one(cur,'select m.moving_average_cost from erp.materials m join erp.material_rolls r on r.material_id=m.id where r.id=%s',(g['roll'],)))
    def facts(g):
        return cur.execute('select qty_physically_returned,return_destination,returned_at from erp.cutting_group_rolls where cutting_group_id=%s',(g['group'],)).fetchone()
    def returned(g,qty,at=None):
        w=return_read(g);return return_send(w,return_payload(w,qty,at))
    def fabric_cancel():
        g=fabric_posted();stock0,wip0,avg0=roll_stock(g),po_wip(g),material_avg(g)
        r=returned(g,'2');value=D(r['value']);assert roll_stock(g)-stock0==2 and wip0-po_wip(g)==value
        w=reversal_read(g)
        assert w['eligible'] and w['blockers']==[] and len(w['returned'])==1 and D(w['returned'][0]['qty_returned'])==2 and w['returned'][0]['later_uses']==[] and w['business_DML'] is False,w
        # D14-10 "hutang/kredit": a fabric return never touched supplier AP, so its cancel may not either.
        ap="select count(*),coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.accounting_account_mappings a on a.account_id=l.account_id where a.mapping_key in('AP_SUPPLIER','AP_VENDOR')"
        ap0=cur.execute(ap).fetchone()
        out=reversal_send(w,reversal_payload(w))
        assert out['action']=='CANCEL_RETURN' and out['reversed_movements']==1 and out['reversed_journals']==1 and out['replacement'] is None,out
        assert roll_stock(g)==stock0 and po_wip(g)==wip0 and material_avg(g).quantize(D('0.000001'))==avg0.quantize(D('0.000001')),(roll_stock(g),stock0,po_wip(g),wip0,material_avg(g),avg0)
        assert return_journals(g)==[('REVERSED',1)] and active_returns(g)==[] and facts(g)==(D(0),None,None),(return_journals(g),facts(g))
        touched=sorted(r[0] for r in cur.execute("select distinct a.mapping_key from erp.journal_entries j join erp.cutting_group_rolls r on r.id=j.source_id join erp.journal_entries x on x.reversal_of_id=j.id join erp.journal_lines l on l.journal_entry_id=x.id join erp.accounting_account_mappings a on a.account_id=l.account_id and a.mapping_key in('MATERIAL_INVENTORY','WIP','AP_SUPPLIER','AP_VENDOR') where r.cutting_group_id=%s and j.source_type='CUTTING_MATERIAL_RETURN_LINE' and x.source_type='JOURNAL_REVERSAL'",(g['group'],)).fetchall())
        assert touched==['MATERIAL_INVENTORY','WIP'] and cur.execute(ap).fetchone()==ap0,('CP17_SG02_CANCEL_TOUCHED_AP',touched,ap0)
        kept=one(cur,"select count(*) from erp.material_stock_movements where source_type='CUTTING_GROUP_RETURN' and source_id=%s",(g['group'],))
        assert kept==1 and one(cur,'select material_return_posted from erp.cutting_groups where id=%s',(g['group'],)) is False
        assert one(cur,'select count(*) from cp7_cutting_correction.return_history where group_id=%s',(g['group'],))==1
        assert one(cur,'select count(*) from cp7_cutting_correction.return_reversal_history where group_id=%s',(g['group'],))==1
        again=return_read(g);assert again['eligible'],again
        r2=returned(g,'1');assert roll_stock(g)-stock0==1 and active_returns(g)==[(D(1),)]
        return dict(status='PASS',owner_decision='D14-10',stock_back=str(stock0),po_WIP_back=str(wip0),material_average_back=True,
                    original_journal='REVERSED with one posted JOURNAL_REVERSAL',reversal_accounts=touched,supplier_AP_unchanged=True,original_movement_kept_and_reversed=True,histories_kept=True,new_return_allowed_after_cancel=r2['rolls'][0]['qty_returned'])
    def fabric_correct():
        g=fabric_posted();stock0,wip0=roll_stock(g),po_wip(g)
        returned(g,'2');w=reversal_read(g);before=b.boundary.snapshot(cur)
        over=refused(cur,lambda:reversal_send(w,reversal_payload(w,('3.5',))),'CP7_CUTTING_RETURN_OVER_REMAINING');unchanged(cur,before,'correction above the recorded remainder (cancel part rolled back too)')
        assert roll_stock(g)-stock0==2 and return_journals(g)==[('POSTED',0)]
        out=reversal_send(w,reversal_payload(w,('3',)))
        cost=D(w['returned'][0]['unit_cost']);value3=(3*cost).quantize(D('0.01'),rounding=ROUND_HALF_UP)
        assert out['action']=='CORRECT_RETURN' and D(out['replacement']['value'])==value3 and out['replacement']['rolls'][0]['qty_returned']=='3',out
        assert roll_stock(g)-stock0==3 and wip0-po_wip(g)==value3 and active_returns(g)==[(D(3),)] and return_journals(g)==[('REVERSED',1),('POSTED',0)],(roll_stock(g),return_journals(g))
        row=cur.execute('select qty_physically_returned,return_destination,returned_at=%s::timestamptz from erp.cutting_group_rolls where cutting_group_id=%s',(out['at'],g['group'])).fetchone()
        assert row==(D(3),'WAREHOUSE',True) and one(cur,'select material_return_posted from erp.cutting_groups where id=%s',(g['group'],))
        return dict(status='PASS',owner_decision='D14-10',over_remainder_correction_refused_whole=over,two_corrected_to_three=True,stock_net=3,po_WIP_reduced_by=str(value3),one_transaction=True)
    def fabric_cancel_blocked():
        g=fabric_posted();now=datetime.now(timezone.utc).replace(microsecond=0)
        returned(g,'2',(now-timedelta(minutes=10)).isoformat())
        later=later_cutting(cur,g,(now-timedelta(minutes=5)).isoformat())
        w=reversal_read(g);kinds=[x['kind'] for x in w['blockers']]
        assert not w['eligible'] and kinds==['LATER_USE'] and w['blockers'][0]['uses'] and any(u['label']==later['number'] for u in w['blockers'][0]['uses']),w
        before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:reversal_send(w,reversal_payload(w)),'CP7_CUTTING_RETURN_REVERSAL_DEPENDENCIES');unchanged(cur,before,'cancel after the fabric was used again')
        assert later['number'] in detail,detail
        p,v=cut.payload(cur,dict(group=later['group']));cut.command(cur,p,v)
        fixed=reversal_read(g);assert fixed['eligible'] and fixed['blockers']==[],fixed
        stock=roll_stock(g);out=reversal_send(fixed,reversal_payload(fixed))
        assert out['action']=='CANCEL_RETURN' and roll_stock(g)==stock-2 and active_returns(g)==[]
        return dict(status='PASS',owner_decision='D14-10',later_use_named=later['number'],refused_whole=detail,after_reopening_that_cutting_cancel_succeeds=True)
    def fabric_cancel_once():
        g=fabric_posted();returned(g,'1');w=reversal_read(g);key=uuid.uuid4();p=reversal_payload(w)
        first=reversal_send(w,p,key);stock=roll_stock(g);again=reversal_send(w,p,key)
        assert again==first and roll_stock(g)==stock and active_returns(g)==[],('CP17_SG02_CANCEL_REPLAY_NOT_IDENTICAL',first,again)
        fresh=reversal_read(g);assert not fresh['eligible'] and [x['kind'] for x in fresh['blockers']]==['NOT_RETURNED'],fresh
        before=b.boundary.snapshot(cur)
        nothing=refused(cur,lambda:reversal_send(fresh,reversal_payload(fresh)),'CP7_CUTTING_RETURN_REVERSAL_DEPENDENCIES');unchanged(cur,before,'cancel with nothing returned')
        stale=refused(cur,lambda:reversal_send(w,reversal_payload(w)),'CP7_CUTTING_RETURN_REVERSAL_STALE_REVIEW');unchanged(cur,before,'cancel on a stale review')
        return dict(status='PASS',same_request_replay_identical=True,second_cancel_refused=nothing,stale_review_refused=stale)

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

    # ------------------------------------------------------------ FABLE-012 gate (owner D14-9)
    def exposure_gate():
        """D14-9: the EXECUTE revoke of the erp writers waits for CP7C; a Data API setting that would reach erp before
        that revoke is refused by the gate. Read only here: the stored override and the revoke run in a savepoint that is
        rolled back."""
        import cp7_access_inventory as access
        b.api.admin(cur)
        runbook=access.exposure_gate(cur);count=runbook['writers_without_invoker_reference']
        assert runbook['ok'] and not runbook['erp_exposed'] and runbook['stored_in_database']=={} and count>=60,runbook
        dashboard=access.exposure_gate(cur,['public','graphql_public','erp'])
        assert not dashboard['ok'] and dashboard['refusal']==access.GATE_REFUSAL and len(dashboard['revoke_first'])==count,dashboard
        search=access.exposure_gate(cur,access.RUNBOOK_SCHEMAS,['public','extensions','erp'])
        assert not search['ok'] and search['refusal']==access.GATE_REFUSAL and search['revoke_first']==dashboard['revoke_first'],search
        cur.execute('savepoint fable012_gate')
        try:
            # An override stored in the database on the authenticator role (the runbook forbids it) counts without a declaration.
            cur.execute("alter role authenticator set pgrst.db_schemas='public, graphql_public, erp'")
            stored=access.exposure_gate(cur)
            assert not stored['ok'] and stored['stored_in_database']=={'pgrst.db_schemas':['public','graphql_public','erp']} and stored['refusal']==access.GATE_REFUSAL,stored
            # The CP7C work itself: EXECUTE revoked from authenticated and PUBLIC on exactly the named writers; then the gate passes.
            for sig in dashboard['revoke_first']:cur.execute(f'revoke execute on function {sig} from authenticated, public')
            after=access.exposure_gate(cur,['public','graphql_public','erp'])
            assert after['ok'] and after['refusal'] is None and after['erp_exposed'] and after['writers_without_invoker_reference']==0,after
        finally:cur.execute('rollback to savepoint fable012_gate');cur.execute('release savepoint fable012_gate')
        assert access.exposure_gate(cur)==runbook,'CP17_FABLE012_GATE_LEFT_A_CHANGE'
        return dict(status='PASS',owner_decision='D14-9',runbook_setting=dict(schemas=runbook['served_schemas'],extra_search_path=runbook['extra_search_path'],ok=True),
                    writers_to_revoke_first=count,erp_in_exposed_schemas=dashboard['refusal'],erp_on_extra_search_path=search['refusal'],
                    stored_override_on_authenticator=stored['refusal'],after_revoking_exactly_those_writers='ok',revoke_kept=False)

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

    # ------------------------------------------------------------ G1 (D14-14): SELESAI DIJAHIT + piece-work wage from the connected WIP screen
    def sewing_ready(g):return work_rates(cur,g)
    def sewing_read(g):return sewing_workspace(cur,g)
    def sewing_send(w,**kw):return sewing_command(cur,w,**kw)
    def sewing_record():
        g=picked();rates=sewing_ready(g);w=sewing_read(g)
        assert w['eligible'] and w['blockers']==[] and w['business_DML'] is False,w
        assert (w['effective_pcs'],w['sewn_pcs'],w['max_qty'],w['rates_committed'],w['contractor_id'])==(10,0,10,False,g['mandor']),w
        # Before the first record the screen previews the rates the Native snapshot will take (Mandor 3 over BOM default 2, Obras 1).
        assert [D(str(x['rate']))for x in w['rate_preview']]==[3,1] and w['components']==[],w['rate_preview']
        assert sewn_ready(cur,g)==(0,0)
        key=uuid.uuid4();r=sewing_send(w,qty=4,at=g['at'](10),key=key);again=sewing_send(w,qty=4,at=g['at'](10),key=key)
        assert again==r and r['action']=='RECORD' and r['result']['qty_pcs']==4 and r['result']['components']==2,r
        comp=r['result']['work_completion_id']
        # Oracles from Native rows: the Mandor rate 3 wins over the BOM default 2, the second component keeps its default 1.
        lines=cur.execute('select work_component_id::text,qty_completed,qty_payable,rate_snapshot,amount_payable from erp.work_completion_lines where completion_id=%s order by rate_snapshot desc',(comp,)).fetchall()
        assert lines==[(rates['component'],4,4,D(3),D(12)),(rates['obras'],4,4,D(1),D(4))],lines
        assert one(cur,'select status from erp.work_completion_events where id=%s',(comp,))=='POSTED'
        assert wage_journal(cur,comp)==(D(16),D(16),1),wage_journal(cur,comp)
        assert D(str(r['result']['wage_amount']))==16
        assert one(cur,"select sum(qty_signed) from erp.sewing_terminal_events where cutting_group_id=%s and event_kind='SELESAI_DIJAHIT'",(g['group'],))==4
        assert sewn_ready(cur,g)==(4,4),('CP17_G1_NOT_READY_FOR_LAUNDRY',sewn_ready(cur,g))
        payroll=cur.execute('select count(*),sum(source_qty_payable) from erp.v_payroll_production_work_eligibility where source_id in(select id from erp.work_completion_lines where completion_id=%s)',(comp,)).fetchone()
        assert payroll==(2,8),('CP17_G1_WAGE_NOT_IN_PAYROLL_PIPELINE',payroll)
        w2=sewing_read(g)
        assert w2['max_qty']==6 and w2['rates_committed'] and w2['rate_preview']==[] and [(c['rate'],c['posted_qty'])for c in w2['components']]==[(3,4),(1,4)],w2
        r2=sewing_send(w2,qty=6,at=g['at'](11));w3=sewing_read(g)
        assert sewn_ready(cur,g)==(10,10) and wage_journal(cur,r2['result']['work_completion_id'])==(D(24),D(24),1)
        assert not w3['eligible'] and w3['max_qty']==0 and [b['kind']for b in w3['blockers']]==['NOTHING_TO_SEW'],w3
        assert one(cur,'select count(*) from cp7_cutting_correction.sewing_history where group_id=%s',(g['group'],))==2
        return dict(status='PASS',recorded=[4,6],wage_per_pcs=dict(mandor_rate=3,bom_default=1,total=4),wage_journals=['WIP 16 / CONTRACTOR_PAYABLE 16','WIP 24 / CONTRACTOR_PAYABLE 24'],
                    ready_for_laundry=10,payroll_pipeline_lines=2,same_request_replay_identical=True,nothing_left_blocker=True)
    def sewing_refused():
        g=picked();w0=sewing_read(g)
        assert not w0['eligible'] and [b['kind']for b in w0['blockers']]==['NO_WORK_RATE'],w0['blockers']
        before=b.boundary.snapshot(cur)
        no_rate=refused(cur,lambda:sewing_send(w0,qty=1,at=g['at'](10)),'CP7_SEWING_BLOCKED');unchanged(cur,before,'no work BOM')
        sewing_ready(g);w=sewing_read(g);before=b.boundary.snapshot(cur)
        over=refused(cur,lambda:sewing_send(w,qty=11,at=g['at'](10)),'CP7_SEWING_QTY_ABOVE_REMAINING');unchanged(cur,before,'more than the Potongan')
        early=refused(cur,lambda:sewing_send(w,qty=1,at=g['at'](8)),'CP7_SEWING_BEFORE_PICKUP');unchanged(cur,before,'before pickup')
        future=refused(cur,lambda:sewing_send(w,qty=1,at=datetime.now(timezone.utc)+timedelta(days=2)),'CP7_SEWING_FUTURE');unchanged(cur,before,'future')
        stale=refused(cur,lambda:sewing_send(w,qty=1,at=g['at'](10),token='0'*32),'CP7_SEWING_STALE_REVIEW');unchanged(cur,before,'stale review')
        version=refused(cur,lambda:sewing_send(w,qty=1,at=g['at'](10),expected=str(int(w['group_version'])+1)),'CP7_SEWING_STALE_REVIEW');unchanged(cur,before,'stale version')
        short=refused(cur,lambda:sewing_send(w,qty=1,at=g['at'](10),reason='x'),'CP7_SEWING_FIELDS');unchanged(cur,before,'short reason')
        zero=refused(cur,lambda:sewing_send(w,qty=0,at=g['at'](10)),'CP7_SEWING_FIELDS');unchanged(cur,before,'zero pieces')
        key=uuid.uuid4();sewing_send(w,qty=2,at=g['at'](10),key=key)
        changed=refused(cur,lambda:sewing_send(w,qty=3,at=g['at'](10),key=key),'CP7_SEWING_REQUEST_CHANGED')
        # Not asserted here: authenticated still holds EXECUTE on erp.post_work_completion (FABLE-012; owner D14-9 defers that
        # revoke to CP7C). First CI run on d53c4e92 wrongly expected 'permission denied' and got the Native DRAFT refusal (log
        # kept). The writer is unreachable from the browser because the Data API serves only public:
        # CP17_HTTP_ERP_WRITERS_NOT_REACHABLE.
        return dict(status='PASS',no_work_rate=no_rate,over_remaining=over,before_pickup=early,future=future,stale_review=stale,stale_version=version,
                    short_reason=short,zero_pieces=zero,same_key_other_payload=changed,native_writer_reachability='CP17_HTTP_ERP_WRITERS_NOT_REACHABLE (D14-9)')
    def sewing_cancel():
        g=picked();sewing_ready(g);w=sewing_read(g)
        first=sewing_send(w,qty=4,at=g['at'](10));second=sewing_send(sewing_read(g),qty=3,at=g['at'](10,30))
        comp=first['result']['work_completion_id'];event=first['result']['sewing_event_id']
        journal=one(cur,"select id from erp.journal_entries where source_type='WORK_COMPLETION' and source_id=%s",(comp,))
        # Three of the seven are sent to the laundry: only the record whose pieces are all still at the Mandor can be cancelled.
        wash=laundry_for(cur,g);delivery=bd.post_priced(cur,wash,{},qty=3,hour=12);b.api.admin(cur)
        w2=sewing_read(g);by={e['id']:e for e in w2['events']}
        assert (w2['ready_unsent_pcs'],w2['laundry_draft_pcs'])==(4,0),w2
        assert by[event]['cancel_blocker'] is None and by[event]['qty_pcs']==4,by
        blocked_event=second['result']['sewing_event_id']
        assert by[blocked_event]['qty_pcs']==3 and by[blocked_event]['cancel_blocker'] is None,by  # 3 <= 4 still at the Mandor
        before=b.boundary.snapshot(cur)
        key=uuid.uuid4();r=sewing_send(w2,event=event,reason='CP17 salah hitung setoran',key=key);again=sewing_send(w2,event=event,reason='CP17 salah hitung setoran',key=key)
        assert again==r and r['action']=='REVERSE' and r['result']['status']=='CANCELLED' and r['result']['qty_pcs']==4,r
        assert one(cur,'select status from erp.work_completion_events where id=%s',(comp,))=='REVERSED'
        assert one(cur,'select status from erp.journal_entries where id=%s',(journal,))=='REVERSED'
        assert cur.execute("""select coalesce(sum(l.debit) filter(where l.account_id=erp.account_id('CONTRACTOR_PAYABLE')),0),coalesce(sum(l.credit) filter(where l.account_id=erp.account_id('WIP')),0)
            from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.reversal_of_id=%s and j.status='POSTED'""",(journal,)).fetchone()==(D(16),D(16))
        assert one(cur,'select count(*) from erp.sewing_terminal_events where reversal_of_id=%s and qty_signed=-4',(event,))==1
        assert sewn_ready(cur,g)==(3,0),sewn_ready(cur,g)
        # Now everything left at the Mandor is zero: the record whose pieces went to the laundry is refused and named.
        w3=sewing_read(g);left={e['id']:e for e in w3['events']if not e['reversed']}
        assert left[blocked_event]['cancel_blocker']=='SENT_OR_DRAFTED_TO_LAUNDRY',left
        before=b.boundary.snapshot(cur)
        sent=refused(cur,lambda:sewing_send(w3,event=blocked_event,reason='CP17 coba batal sesudah laundry'),'CP7_SEWING_CANCEL_BLOCKED');unchanged(cur,before,'cancel after laundry')
        twice=refused(cur,lambda:sewing_send(w3,event=event,reason='CP17 batal kedua kali'),'CP7_SEWING_CANCEL_BLOCKED');unchanged(cur,before,'cancel twice')
        return dict(status='PASS',cancelled=dict(pieces=4,work_completion='REVERSED',wage_journal='REVERSED with JOURNAL_REVERSAL 16',sewing='REVERSAL -4'),
                    after_cancel_sewn_ready=[3,0],laundry_delivery=str(delivery.get('delivery_id')),cancel_after_laundry_refused=sent,cancel_twice_refused=twice,
                    same_request_replay_identical=True)

    # ------------------------------------------------------------ G2 (D14-14): finish the PO from the HPP screen, HPP final
    def finish_po():
        f=finish_fixture(cur,today);po=f['po'];w=finish_workspace(cur,po)
        assert w['eligible'] and w['blockers']==[] and w['business_DML'] is False and w['po_status']!='FINISHED',w
        assert (w['fg_pcs'],w['laundry_sent_pcs'],w['laundry_returned_pcs'],w['laundry_good_pcs'],w['qc_accounted_pcs'],w['open_bs_cases'])==(10,10,10,10,10,0),w
        assert w['hpp']['display_status']=='SEMENTARA' and 'PRODUKSI_BELUM_FINISHED' in w['hpp']['pending_reasons'],w['hpp']
        assert D(w['wip_balance'])==round(po_wip_balance(cur,po),2),(w['wip_balance'],po_wip_balance(cur,po))
        listed=finish_list(cur,f['number']);assert [r['id'] for r in listed['rows']]==[po] and listed['rows'][0]['fg_pcs']==10,listed
        wip_before=po_wip_balance(cur,po);key=uuid.uuid4();r=finish_command(cur,w,key=key);again=finish_command(cur,w,key=key)
        assert again==r and r['action']=='FINISH' and r['result']['status']=='FINISHED' and r['result']['wip_after']=='0.00',r
        # Oracles: the PO row, its WIP journal lines, the FG lots' current HPP and the residual close event.
        state=po_state(cur,po);total,qty=po_hpp(cur,po)
        assert state['status']=='FINISHED' and state['wip']==0 and state['history']==1,state
        assert D(r['result']['hpp']['total'])==round(total,2) and r['result']['hpp']['qty_basis_pcs']==qty==10,(r['result']['hpp'],total,qty)
        assert D(r['result']['residual_closed'])==round(state['closed'],2),(r['result'],state)
        assert 'PRODUKSI_BELUM_FINISHED' not in r['result']['hpp']['pending_reasons'] and r['result']['hpp']['display_status']!='SEMENTARA',r['result']['hpp']
        sync=one(cur,"select count(*) from erp.journal_entries where source_type='PO_HPP_GL_SYNC' and source_id=%s and status='POSTED'",(po,))
        after=finish_workspace(cur,po);assert not after['eligible'] and [x['kind'] for x in after['blockers']]==['ALREADY_FINISHED'],after['blockers']
        before=b.boundary.snapshot(cur)
        twice=refused(cur,lambda:finish_command(cur,after,reason='CP17 selesai kedua kali'),'CP7_PO_FINISH_BLOCKED');unchanged(cur,before,'finish twice')
        return dict(status='PASS',po=f['number'],status_after='FINISHED',wip_before=str(wip_before),wip_after='0.00',residual_closed=r['result']['residual_closed'],
                    final_hpp=r['result']['hpp'],hpp_gl_sync_journals=sync,same_request_replay_identical=True,second_finish_refused=twice)
    def finish_refused():
        f=finish_fixture(cur,today,received=8);po=f['po'];w=finish_workspace(cur,po)
        assert not w['eligible'] and w['blockers']==[dict(kind='LAUNDRY_OUTSTANDING',qty=2)],w['blockers']
        before=b.boundary.snapshot(cur)
        out=refused(cur,lambda:finish_command(cur,w),'CP7_PO_FINISH_BLOCKED');unchanged(cur,before,'laundry still out')
        # Native agrees on the same fact (its own refusal, called as the Owner): the facade does not invent the rule.
        native=refused(cur,lambda:bd.internal(cur,'finish_production_order',po),'unresolved laundry outstanding qty 2');unchanged(cur,before,'Native finish with laundry out')
        missing=refused(cur,lambda:finish_command(cur,w,po=str(uuid.uuid4())),'CP7_PO_FINISH_NOT_FOUND');unchanged(cur,before,'unknown PO')
        # Lawful path: the last two come back and go through QC; the old review is now stale, the fresh one finishes.
        back=bd.receive(cur,f['delivery'],f,2,15)['receipt_id'];b.api.admin(cur);bd.finish_goods(cur,f,back,2,16);b.api.admin(cur)
        stale=refused(cur,lambda:finish_command(cur,w),'CP7_PO_FINISH_STALE_REVIEW')
        w2=finish_workspace(cur,po);assert w2['eligible'] and w2['fg_pcs']==10,w2
        before=b.boundary.snapshot(cur)
        short=refused(cur,lambda:finish_command(cur,w2,reason='x'),'CP7_PO_FINISH_FIELDS');unchanged(cur,before,'short reason')
        forged=refused(cur,lambda:finish_command(cur,w2,token='0'*32),'CP7_PO_FINISH_STALE_REVIEW');unchanged(cur,before,'forged review')
        key=uuid.uuid4();finish_command(cur,w2,key=key)
        changed=refused(cur,lambda:finish_command(cur,w2,key=key,reason='CP17 alasan lain untuk kunci sama'),'CP7_PO_FINISH_REQUEST_CHANGED')
        assert po_state(cur,po)['status']=='FINISHED' and po_state(cur,po)['wip']==0
        return dict(status='PASS',laundry_out_refused=out,native_same_refusal=native,unknown_po=missing,stale_after_change=stale,short_reason=short,
                    forged_review=forged,same_key_other_payload=changed,finished_after_all_back=True)

    # ------------------------------------------------------------ R2-01 (owner D15-1; FABLE-013, SOL-R1-001)
    def cash_rows(bank):
        b.api.admin(cur)
        return [r for r in cur.execute('select kind,subject_id::text,on_day,amount from cp7_guard.findings()').fetchall() if r[0].startswith('CASH') and r[1]==bank]
    def scope_empty():
        b.api.admin(cur);return one(cur,'select count(*) from cp7_guard.compound_scope')==0 and one(cur,'select count(*) from cp7_guard.compound_touch')==0
    def spent_receipt():
        """Sol's fixture: a customer receipt of 30.01 into a fresh bank, then 20.00 of it pays a supplier (bank 10.01).
        The supplier-payment fixture leaves the session in Jakarta; the zone found before it is restored, so the payment
        correction suite's own fingerprints (taken in that zone at edit.fixture) compare like with like."""
        zone=one(cur,'show timezone')
        f=edit.fixture(cur,today,amount='30.01');out=pay.fixture(cur,today);out['cash']=f['bank']
        pay.command(cur,pay.payload(cur,out,'20.00'));assert balance(cur,f['bank'])==D('10.01')
        cur.execute("select set_config('TimeZone',%s,false)",(zone,))
        return f
    def cash_book_date():
        """Fable cp17c FABLE_CP17C:CASH_BASIS_MISMATCH with its own amounts: income dated inside the closed period is
        recognised on the first open day; an expense dated yesterday that the economic-date balance allows but that leaves
        yesterday's book-date balance (the owner's daily cash report) below zero is refused; up to that balance it posts."""
        f=misc.fixture(cur,today);b.api.admin(cur);yday=today-timedelta(days=1)
        closed=one(cur,'select closed_through from erp.accounting_period_control where singleton_id=1');closed_day=closed-timedelta(days=2)
        bank=f['cash']['id'];coa=str(f['cash']['account_id'])
        def book_until(day):
            b.api.admin(cur);return D(one(cur,"select coalesce(sum(debit_total-credit_total),0)::text from erp.account_daily_balances where account_id=%s and balance_date<=%s",(coa,day)))
        income=D(str(misc.cash_balance(cur,bank)))+D('1000.00');book_yday=book_until(yday);assert book_yday>0,book_yday
        p=misc.save_payload(f,'OTHER_INCOME',str(income));p['physical_at']=str(closed_day)+'T08:00:00+07:00'
        misc.command(cur,'POST',misc.intent(misc.command(cur,'SAVE',p)));b.api.admin(cur)
        shifted=cur.execute("select economic_date,transaction_date from erp.journal_entries where source_type='MISC_FINANCE' and economic_date=%s order by posting_at desc limit 1",(closed_day,)).fetchone()
        assert shifted[0]==closed_day and shifted[1]>closed,shifted
        pe=misc.save_payload(f,'OTHER_EXPENSE',str(book_yday+D('500.00')));pe['physical_at']=str(yday)+'T09:00:00+07:00'
        before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:misc.command(cur,'POST',misc.intent(misc.command(cur,'SAVE',pe))),'CP7_CASH_NEGATIVE');unchanged(cur,before,'expense breaking the book-date balance')
        assert 'tanggal buku' in json.dumps(detail,default=str),detail
        pe=misc.save_payload(f,'OTHER_EXPENSE',str(book_yday));pe['physical_at']=str(yday)+'T09:00:00+07:00'
        misc.command(cur,'POST',misc.intent(misc.command(cur,'SAVE',pe)))
        assert book_until(yday)==0 and cash_rows(bank)==[]
        return dict(status='PASS',closed_through=str(closed),income_economic_and_book_date=[str(shifted[0]),str(shifted[1])],
                    expense_over_book_balance_refused=detail,expense_equal_to_book_balance_posted=str(book_yday),detector_clean=True,
                    witness='Fable FABLE_CP17C:CASH_BASIS_MISMATCH (run 38786227211)')
    def spent_income_correction():
        f=spent_receipt();p,v=spent_payload(cur,f,'25.01');r=edit.correct(cur,p,v);edit.check(cur,f,p,r)
        assert balance(cur,f['bank'])==D('5.01') and cash_rows(f['bank'])==[] and scope_empty()
        return dict(status='PASS',receipt='30.01',spent='20.00',corrected_to='25.01',bank_after='5.01',witness='Sol SOL_R1_CUSTOMER_PAYMENT_CORRECTION_FINAL_POSITIVE')
    def spent_income_note_only():
        f=spent_receipt();p,v=spent_payload(cur,f,'30.01',notes='CP17 catatan dibetulkan sesudah uangnya terpakai');r=edit.correct(cur,p,v);edit.check(cur,f,p,r)
        assert balance(cur,f['bank'])==D('10.01') and scope_empty()
        return dict(status='PASS',note_only_correction_committed=True,bank_after='10.01',witness='Sol SOL_HTTP_SPENT_INCOME_NOTE_ONLY_CORRECTION')
    def spent_income_negative():
        f=spent_receipt();p,v=spent_payload(cur,f,'15.01');before=b.boundary.snapshot(cur);private=edit.private_state(cur)
        detail=refused(cur,lambda:edit.correct(cur,p,v),'CP7_CASH_NEGATIVE');unchanged(cur,before,'correction leaving the bank at -4.99')
        assert edit.private_state(cur)==private and balance(cur,f['bank'])==D('10.01') and scope_empty()
        # A lone inverse that makes the bank negative stays refused: the guard judges the end of every command.
        return dict(status='PASS',replacement_15_01_after_spending_20_refused=detail,bank_unchanged='10.01',witness='Sol SOL_HTTP_SPENT_INCOME_GENUINE_NEGATIVE_REFUSAL')
    def misc_spent_income():
        f=misc.fixture(cur,today);b.api.admin(cur);bank=f['cash']['id'];start=D(str(misc.cash_balance(cur,bank)))
        old=misc_fix.posted(cur,f,'OTHER_INCOME','30.01');misc_fix.posted(cur,f,'OTHER_EXPENSE',str(start+D('20.00')));b.api.admin(cur)
        assert D(str(misc.cash_balance(cur,bank)))==D('10.01')
        before=b.boundary.snapshot(cur)
        detail=refused(cur,lambda:misc_fix.correct(cur,misc_fix.payload(f,old,'5.00')),'CP7_CASH_NEGATIVE');unchanged(cur,before,'misc correction leaving the bank at -15.00')
        p=misc_fix.payload(f,old,'25.01');r=misc_fix.correct(cur,p);misc_fix.check(cur,f,old,r);b.api.admin(cur)
        assert D(str(misc.cash_balance(cur,bank)))==D('5.01') and scope_empty()
        return dict(status='PASS',correction_to_5_00_refused_first=detail,misc_income_30_01_spent_corrected_to_25_01_bank='5.01')
    def note_spent_payment():
        f=spent_receipt();p,v=note_fix.edit(cur,f,price='21');out=note_fix.correct(cur,p,v)
        assert out['kind']=='COMMITTED_OUTCOME' and out['previous_sale_id']==f['sale'],out
        assert balance(cur,f['bank'])==D('10.01') and scope_empty()
        replay=one(cur,'select count(*) from cp7_note.payment_replays where correction_id=%s',(out['revision_id'],));assert replay==1,replay
        return dict(status='PASS',paid_note_corrected_after_receipt_spent=True,payment_replayed=1,bank_after='10.01')
    def compound_private():
        for who in('anon','authenticated','service_role'):
            for sig in('cp7_guard.begin_compound(text)','cp7_guard.end_compound()'):
                assert not one(cur,"select has_function_privilege(%s,%s,'EXECUTE')",(who,sig)),(who,sig)
        before=b.boundary.snapshot(cur)
        def left_open():
            b.api.admin(cur);cur.execute("select cp7_guard.begin_compound('CP17 terbuka')");cur.execute('set constraints all immediate')
        open_refused=refused(cur,left_open,'CP7_GUARD_COMPOUND_OPEN');unchanged(cur,before,'scope left open')
        not_open=refused(cur,lambda:(b.api.admin(cur),cur.execute('select cp7_guard.end_compound()')),'CP7_GUARD_COMPOUND_NOT_OPEN')
        assert scope_empty()
        return dict(status='PASS',begin_end_owner_only=True,scope_left_open_refused_at_commit=open_refused,end_without_begin_refused=not_open)
    def detector_book_date():
        f=misc.fixture(cur,today);b.api.admin(cur);bank=f['cash']['id'];start=D(str(misc.cash_balance(cur,bank)))
        pe=misc.save_payload(f,'OTHER_EXPENSE',str(start+D('7.00')))
        b.api.admin(cur);cur.execute('alter table erp.journal_lines disable trigger cp7_guard_cash_not_negative')
        try:misc.command(cur,'POST',misc.intent(misc.command(cur,'SAVE',pe)))
        finally:b.api.admin(cur);cur.execute('alter table erp.journal_lines enable trigger cp7_guard_cash_not_negative')
        rows=cash_rows(bank);kinds=sorted(r[0] for r in rows)
        assert kinds==['CASH_NEGATIVE','CASH_NEGATIVE_BOOK_DATE'] and all(r[3]==D('-7') for r in rows),rows
        # Capital on the expense's own economic day (the fixture's physical day, not today) clears both bases.
        day=next(r[2] for r in rows if r[0]=='CASH_NEGATIVE');funding.fund(cur,bank,'7.00',day);b.api.admin(cur);assert cash_rows(bank)==[],cash_rows(bank)
        return dict(status='PASS',both_bases_listed=[[r[0],str(r[2]),str(r[3])] for r in rows],capital_clears_both=True)

    # ------------------------------------------------------------ R2-05 (ASTRA-C17-05, owner D15-4 / FABLE-014)
    def astra_journey(sewn,delivered):
        """Astra's own oracle (audit/astra_cp17_combined/native_probe.py, branch audit/astra-cp1-7-combined-dfab13bf-20261016),
        ported unchanged in arithmetic: 10 cut, `sewn` sewn at 4 per pcs, `delivered` washed at 2 per pcs. Added after the fix:
        the workspace itself must already name the unaccounted pieces before the click (the screen used to say eligible)."""
        g=pickup_fixture(cur,today)
        work_rates(cur,g)
        initial_wip=D(po_wip_balance(cur,g['po']))
        initial_gl=cur.execute("select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') and l.po_id=%s and l.account_id=erp.account_id('FG_INVENTORY')",(g['po'],)).fetchone()[0]
        assert initial_gl==0 and initial_wip>0, ('FIXTURE_NOT_PRISTINE',initial_gl,initial_wip)
        completions=[]
        for qty,hour in ((3,10),(sewn-3,11)):
            r=sewing_command(cur,sewing_workspace(cur,g),qty=qty,at=g['at'](hour))
            completions.append(r['result']['work_completion_id'])
        wages=cur.execute("select coalesce(sum(l.amount_payable),0) from erp.work_completion_lines l where completion_id=any(%s::uuid[])",(completions,)).fetchone()[0]
        assert wages==D(sewn)*4, ('WAGE_ARITHMETIC',wages,sewn*4)
        assert po_wip_balance(cur,g['po'])==initial_wip+sewn*4
        wash=dict(laundry_for(cur,g),po=g['po'])
        delivery=bd.post_priced(cur,wash,{},qty=delivered,hour=12)['delivery_id']
        receipt=bd.receive(cur,delivery,wash,delivered,13)['receipt_id']
        b.api.admin(cur)
        product,lot=bd.finish_goods(cur,wash,receipt,delivered,14)
        b.api.admin(cur)
        ready=sewn_ready(cur,g)
        assert ready==(sewn,sewn-delivered), ('PHYSICAL_READY',ready)
        workspace=finish_workspace(cur,g['po'])
        before=po_state(cur,g['po'])
        evidence=dict(cut=10,sewn=sewn,laundry_sent=delivered,fg=delivered,unsewn=10-sewn,sewn_unsent=sewn-delivered,
                      initial_material_wip=str(initial_wip),wages=str(wages),finish_eligible=workspace['eligible'],blockers=workspace['blockers'],hpp_before=workspace['hpp'],
                      witness='Astra '+('ASTRA_G1_G2_TEN_PIECES_CONSERVED' if delivered==10 else 'ASTRA_G2_UNSEWN_SIX_MUST_NOT_FINISH' if sewn<10 else 'ASTRA_G2_SEWN_UNSENT_SIX_MUST_NOT_FINISH'))
        if delivered<10:
            assert workspace['eligible'] is False and dict(kind='SOURCE_UNACCOUNTED',qty=10-delivered) in workspace['blockers'],workspace['blockers']
            snap=b.boundary.snapshot(cur)
            refusal=refused(cur,lambda:finish_command(cur,workspace,reason='Astra verify incomplete production cannot close'),'CP7_PO_FINISH_BLOCKED');unchanged(cur,snap,'six pieces without a disposition')
            native=refused(cur,lambda:bd.internal(cur,'finish_production_order',g['po']),'PO belum boleh FINISHED');unchanged(cur,snap,'Native finish with six pieces open')
            assert po_state(cur,g['po'])==before
            return dict(status='PASS',refusal=refusal,native_same_refusal=native,**evidence)
        result=finish_command(cur,workspace,reason='Astra ten cut pieces all finished')
        state=po_state(cur,g['po']);hpp,qty=po_hpp(cur,g['po'])
        expected=initial_wip+D(10)*D(4)+D(10)*D(2)
        assert (state['status'],state['wip'],qty,hpp)==('FINISHED',D(0),10,expected), ('COMPLETE_CHAIN_CONSERVATION',state,qty,hpp,expected)
        assert sewn_ready(cur,g)==(10,0)
        assert not unbalanced_po_journals(cur,g['po'])
        return dict(status='PASS',hpp_total=str(hpp),expected_hpp_total=str(expected),qty=qty,state=state,result=result,**evidence)
    def reopen_same_hpp():
        """Fable D15-4 oracle: reopen through the facade (review token, reason, idempotency, immutable history), WIP and HPP
        consistent with the ledger afterwards, and finishing again with nothing new gives the same final HPP."""
        f=finish_fixture(cur,today);po=f['po'];first=finish_command(cur,finish_workspace(cur,po),reason='CP17 PO selesai pertama')
        hpp1=po_hpp(cur,po);s1=po_state(cur,po);residual=D(first['result']['residual_closed']);closes=posted_closes(cur,po)
        assert s1['status']=='FINISHED' and s1['wip']==0 and closes>=(1 if residual else 0),(s1,closes,residual)
        r=reopen_workspace(cur,po)
        assert r['eligible'] and r['blockers']==[] and r['fg_used_pcs']==0 and D(r['returning_to_wip'])==residual and r['close_journals']==closes,r
        before=b.boundary.snapshot(cur)
        short=refused(cur,lambda:reopen_command(cur,r,reason='x'),'CP7_PO_REOPEN_FIELDS');unchanged(cur,before,'short reopen reason')
        forged=refused(cur,lambda:reopen_command(cur,r,token='0'*32),'CP7_PO_REOPEN_STALE_REVIEW');unchanged(cur,before,'forged reopen review')
        key=uuid.uuid4();out=reopen_command(cur,r,key=key,reason='CP17 biaya laundry belum masuk');assert reopen_command(cur,r,key=key,reason='CP17 biaya laundry belum masuk')==out
        changed=refused(cur,lambda:reopen_command(cur,r,key=key,reason='CP17 alasan lain untuk kunci sama'),'CP7_PO_REOPEN_REQUEST_CHANGED')
        s2=po_state(cur,po);assert s2['status']!='FINISHED' and s2['wip']==residual and out['result']['status']==s2['status'],(s2,residual,out)
        assert posted_closes(cur,po)==0 and not unbalanced_po_journals(cur,po)
        audit=one(cur,"select count(*) from erp.audit_logs where entity_type='production_orders' and entity_id=%s and new_data->>'correction_type'='PO_REOPEN'",(po,))
        history=one(cur,'select count(*) from cp7_cutting_correction.po_reopen_history where po_id=%s',(po,))
        assert audit==1 and history==1,(audit,history)
        immutable=refused(cur,lambda:cur.execute('delete from cp7_cutting_correction.po_reopen_history where po_id=%s',(po,)),'CP7_CUTTING_CORRECTION_HISTORY_IMMUTABLE')
        again=finish_workspace(cur,po);assert again['eligible'],again
        second=finish_command(cur,again,reason='CP17 PO selesai lagi tanpa transaksi baru');hpp2=po_hpp(cur,po);s3=po_state(cur,po)
        assert s3['status']=='FINISHED' and s3['wip']==0 and hpp2==hpp1 and D(second['result']['residual_closed'])==residual,(hpp1,hpp2,s3,second)
        stale=refused(cur,lambda:reopen_command(cur,r),'CP7_PO_REOPEN_STALE_REVIEW')
        return dict(status='PASS',residual_returned_to_wip=str(residual),restored_status=s2['status'],same_request_replay_identical=True,short_reason=short,
                    forged_review=forged,same_key_other_payload=changed,native_audit_rows=audit,history_immutable=immutable,
                    hpp_first=[str(x) for x in hpp1],hpp_after_refinish=[str(x) for x in hpp2],old_review_after_refinish=stale)
    def reopen_blockers():
        f=finish_fixture(cur,today);po=f['po']
        r0=reopen_workspace(cur,po);assert not r0['eligible'] and r0['blockers']==[dict(kind='NOT_FINISHED',qty=None)],r0
        before=b.boundary.snapshot(cur)
        open_po=refused(cur,lambda:reopen_command(cur,r0),'CP7_PO_REOPEN_BLOCKED');unchanged(cur,before,'reopen of an unfinished PO')
        finish_command(cur,finish_workspace(cur,po))
        # One finished piece leaves the lot through the accepted P10 FG adjustment: the PO's output is now used.
        location=one(cur,'select location_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id limit 1',(f['lot'],))
        d,_=fgadj.draft(cur,dict(location=location,lot=f['lot'],product=f['product']),'-1');fgadj.action(cur,'POST',d)
        r1=reopen_workspace(cur,po);assert not r1['eligible'] and r1['blockers']==[dict(kind='FG_USED',qty=1)],r1
        before=b.boundary.snapshot(cur)
        used=refused(cur,lambda:reopen_command(cur,r1),'CP7_PO_REOPEN_BLOCKED');unchanged(cur,before,'reopen after its finished goods were used')
        assert po_state(cur,po)['status']=='FINISHED'
        g=finish_fixture(cur,today,label='CP17-R2-CLOSED');finish_command(cur,finish_workspace(cur,g['po']))
        edit.source.fg.ax.boundary.historical.prior.set_open_period(cur,today)
        r2=reopen_workspace(cur,g['po']);assert not r2['eligible'] and r2['blockers']==[dict(kind='PERIOD_CLOSED',qty=None)] and r2['closed_through']==str(today),r2
        before=b.boundary.snapshot(cur)
        closed=refused(cur,lambda:reopen_command(cur,r2),'CP7_PO_REOPEN_BLOCKED');unchanged(cur,before,'reopen into a closed period')
        assert po_state(cur,g['po'])['status']=='FINISHED'
        return dict(status='PASS',not_finished=open_po,fg_used_one_piece=used,period_closed_through_today=closed)

    named=[full_attendance,work_only,installment,direct_native,empty_bank,exact_zero,backdate,later_day,payroll_empty,laundry_empty,
           claim_control,claim_before_source,claim_ap_not_available,stock_card,rework_scrap,rework_good,rework_open,
           hpp_excluded,hpp_unrelated,hpp_replacement,fabric_return,fabric_over,fabric_once,fabric_dates,fabric_cancel,fabric_correct,fabric_cancel_blocked,fabric_cancel_once,legacy_findings,
           kasbon_cycle,kasbon_limits,kasbon_release,rewash_free,pickup_reverse,pickup_refused,exposure_gate,
           sewing_record,sewing_refused,sewing_cancel,finish_po,finish_refused,
           cash_book_date,spent_income_correction,spent_income_note_only,spent_income_negative,misc_spent_income,note_spent_payment,
           compound_private,detector_book_date,
           lambda:astra_journey(10,10),lambda:astra_journey(4,4),lambda:astra_journey(10,4),reopen_same_hpp,reopen_blockers]
    assert len(named)+len(master.NATIVE)+len(autopo.NATIVE)+len(cutover.NATIVE)+len(wave.NATIVE)==REQUIRED['native']
    return list(zip(IDS['native'],named))+master.cases(cur,today)+autopo.cases(cur,today)+cutover.cases(cur,today)+wave.cases(cur,today)


def spent_payload(cur,f,amount,**changes):
    """The correction screen's own UTC-pinned workspace token (Sol's tool qualification in independent_cases.py): the
    supplier-payment fixture leaves the session in Jakarta, and the generic sales reader's token follows the session zone."""
    p,v=edit.payload(cur,f,amount,**changes);w=edit.workspace(cur,f)
    p['review_token'],v=w['review_token'],w['row_version'];return p,v

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
    def overlapping_payroll():
        # FABLE-007 (dugaan absensi dobel). Native erp.guard_payroll_period_overlap (base schema, catalog dump
        # supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz lines 10325-10342; not in this tree's
        # migrations, so a static read of the tree does not find it) takes the contractor advisory lock and refuses a
        # second non-reversed payroll whose period overlaps. First run 38631233950 hit it while building a fixture.
        # Proof: a second payroll over the attended day is refused; two overlapping payrolls sent at once leave one.
        overlap='Payroll period overlaps another active payroll for this contractor'
        with tools.connect()as conn,conn.cursor()as cur:
            f=s.review.fixture(cur,today);s.attendance(cur,f,today);b.api.admin(cur);conn.commit()
        with tools.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur)
            try:nota.seed_header(cur,f,today,today);conn.commit();sequential='ACCEPTED'
            except psycopg.Error as e:conn.rollback();sequential=str(e).splitlines()[0]
        assert sequential==overlap,sequential
        later=today+timedelta(days=1);barrier=threading.Barrier(2)
        def send(n):
            with tools.connect()as conn,conn.cursor()as cur:
                b.api.admin(cur);barrier.wait(5)
                try:
                    pid=nota.seed_header(cur,f,later,later+timedelta(days=n));threading.Event().wait(1);conn.commit();return('PASS',pid)
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(60)for x in[pool.submit(send,n)for n in(1,2)]]
        assert sorted(x[0]for x in results)==['PASS','REFUSED'] and next(x[1]for x in results if x[0]=='REFUSED')==overlap,results
        with tools.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur)
            active=cur.execute("select count(*) from erp.payroll_settlements where contractor_id=%s and status<>'REVERSED' and period_start<=%s and period_end>=%s",(f['contractor'],later+timedelta(days=2),later)).fetchone()[0]
            dup=cur.execute("select count(*) from(select i.attendance_record_id from erp.payroll_attendance_items i join erp.payroll_settlements p on p.id=i.payroll_id "
                            "where p.status<>'REVERSED' and p.contractor_id=%s group by 1 having count(*)>1)x",(f['contractor'],)).fetchone()[0]
            detector=[r for r in(x[0] for x in cur.execute('select to_jsonb(r) from erp.run_integrity_checks() r').fetchall())if 'PAYROLL_ATTENDANCE_DUPLICATE' in r.values()]
        assert active==1 and dup==0 and all(0 in r.values() for r in detector),(active,dup,detector)
        return dict(status='PASS',second_payroll_over_attended_day=sequential,concurrent_overlapping_payrolls=results,active_payrolls_left=active,
                    attendance_in_two_payrolls=0,integrity_detector=detector,guard='erp.guard_payroll_period_overlap (contractor advisory lock)',finding='FABLE-007')
    def sewing_twice():
        # G1: two tabs record 6 of the same 10 pieces at once from the same review: one is posted, the other is refused as stale.
        with tools.connect()as conn,conn.cursor()as cur:
            g=pickup_fixture(cur,today);work_rates(cur,g);w=sewing_workspace(cur,g);conn.commit()
        barrier=threading.Barrier(2)
        def send(n):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=sewing_command(cur,w,qty=6,at=g['at'](10,n));conn.commit();return('PASS',r['result']['work_completion_id'])
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(60)for x in[pool.submit(send,n)for n in(1,2)]]
        assert sorted(x[0]for x in results)==['PASS','REFUSED'] and 'CP7_SEWING_STALE_REVIEW' in next(x[1]for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);state=sewn_ready(cur,g)
            posted=one(cur,"select count(*) from erp.work_completion_events where cutting_group_id=%s and status='POSTED'",(g['group'],))
        assert state==(6,6) and posted==1,(state,posted)
        return dict(status='PASS',two_records_of_six_on_ten=results,sewn_after=6,posted_work_completions=1)
    def finish_twice():
        # G2: two tabs finish the same PO from the same review: one finishes it, the other is refused as stale; one close.
        with tools.connect()as conn,conn.cursor()as cur:
            f=finish_fixture(cur,today);w=finish_workspace(cur,f['po']);conn.commit()
        barrier=threading.Barrier(2)
        def send(n):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=finish_command(cur,w,reason=f'CP17 tab {n} menyelesaikan PO');conn.commit();return('PASS',r['result']['status'])
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(60)for x in[pool.submit(send,n)for n in(1,2)]]
        assert sorted(x[0]for x in results)==['PASS','REFUSED'] and 'CP7_PO_FINISH_STALE_REVIEW' in next(x[1]for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);state=po_state(cur,f['po'])
            closes=one(cur,'select count(*) from erp.po_wip_close_events where po_id=%s',(f['po'],))
        assert state['status']=='FINISHED' and state['wip']==0 and state['history']==1 and closes<=1,(state,closes)
        return dict(status='PASS',two_finishes_same_review=results,finished_once=True,wip_close_events=closes)
    def correction_and_payment():
        # R2-01: the compound correction and an ordinary payment on one bank, at once. Alone each fits (5.01 and 2.01);
        # together the bank would end at -2.99. The account lock orders them; exactly one is refused CP7_CASH_NEGATIVE.
        with tools.connect()as conn,conn.cursor()as cur:
            f=edit.fixture(cur,today,amount='30.01');out=pay.fixture(cur,today);out['cash']=f['bank'];pay.command(cur,pay.payload(cur,out,'20.00'))
            p,v=spent_payload(cur,f,'25.01');other=pay.fixture(cur,today);other['cash']=f['bank'];pp=pay.payload(cur,other,'8.00');conn.commit()
        barrier=threading.Barrier(2)
        def send(kind):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:
                    r=edit.correct(cur,p,v) if kind=='CORRECTION' else pay.command(cur,pp);conn.commit();return(kind,'PASS','')
                except psycopg.Error as e:conn.rollback();return(kind,'REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(60)for x in[pool.submit(send,k)for k in('CORRECTION','PAYMENT')]]
        assert sorted(x[1]for x in results)==['PASS','REFUSED']and 'CP7_CASH_NEGATIVE'in next(x[2]for x in results if x[1]=='REFUSED'),results
        winner=next(x[0]for x in results if x[1]=='PASS')
        with tools.connect()as conn,conn.cursor()as cur:
            assert balance(cur,f['bank'])==(D('5.01')if winner=='CORRECTION'else D('2.01'))
            b.api.admin(cur);assert one(cur,'select count(*) from cp7_guard.compound_scope')==0
        return dict(status='PASS',results=results,winner=winner)
    def reopen_twice():
        # R2-05 (D15-4): two tabs reopen the same finished PO from the same review: one reopens it, the other is refused stale.
        with tools.connect()as conn,conn.cursor()as cur:
            f=finish_fixture(cur,today);finish_command(cur,finish_workspace(cur,f['po']));w=reopen_workspace(cur,f['po']);conn.commit()
        barrier=threading.Barrier(2)
        def send(n):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=reopen_command(cur,w,reason=f'CP17 tab {n} membuka ulang PO');conn.commit();return('PASS',r['result']['status'])
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(60)for x in[pool.submit(send,n)for n in(1,2)]]
        assert sorted(x[0]for x in results)==['PASS','REFUSED'] and 'CP7_PO_REOPEN_STALE_REVIEW' in next(x[1]for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);state=po_state(cur,f['po']);left=posted_closes(cur,f['po'])
            history=one(cur,'select count(*) from cp7_cutting_correction.po_reopen_history where po_id=%s',(f['po'],))
            reversals=one(cur,"""select count(*) from erp.journal_entries r join erp.po_wip_close_events e on e.journal_entry_id=r.reversal_of_id where e.po_id=%s""",(f['po'],))
        assert state['status']!='FINISHED' and left==0 and history==1 and reversals<=1,(state,left,history,reversals)
        return dict(status='PASS',two_reopens_same_review=results,reopened_once=True,close_reversals=reversals)
    return [('CP17_RACE_TWO_PAYMENTS_ONE_BANK',two_payments),('CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS',overlapping_payroll),
            ('CP17_RACE_G1_SEWING_TWO_TABS_ONE_WINS',sewing_twice),('CP17_RACE_G2_FINISH_TWO_TABS_ONE_WINS',finish_twice),
            ('CP17_RACE_R2_CORRECTION_AND_PAYMENT_ONE_BANK',correction_and_payment),('CP17_RACE_R2_PO_REOPEN_TWO_TABS_ONE_WINS',reopen_twice)]+master.races(tools,today)+autopo.races(tools,today)+cutover.races(tools,today)+wave.races(tools,today)


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
    def sewing_http():
        # G1 over real Auth + PostgREST: the Admin records SELESAI DIJAHIT with its wage; a STAFF login is refused and changes nothing.
        admin=http.login('ADMIN','cp17-sewing');staff=http.login('ADMIN','cp17-sewing-staff')
        with http.connect()as conn,conn.cursor()as cur:
            g=pickup_fixture(cur,today);work_rates(cur,g)
            role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,))
            for key in('production.wip.view','production.wip.post','production.wip.reverse'):
                cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
            _,staff_role=s.source.procurement.custom(cur,['production.wip.view','production.wip.post'])
            cur.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(staff_role,staff.auth_user_id));conn.commit()
        w=admin.rpc('erp_cp7_get_sewing_completion_v1',dict(p_group=g['group']));assert w['status']==200 and w['body']['eligible'] and w['body']['max_qty']==10,w
        p=dict(action='RECORD',group_id=g['group'],qty_pcs='5',physical_at=g['at'](10).isoformat(),review_token=w['body']['review_token'],change_reason='CP17 setoran lewat login')
        denied=staff.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=w['body']['group_version']))
        assert denied['status'] in(400,401,403) and 'CP7_SEWING_DENIED' in str(denied['body']),denied
        r=admin.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=w['body']['group_version']))
        assert r['status']==200 and r['body']['result']['qty_pcs']==5,r
        with http.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);assert sewn_ready(cur,g)==(5,5) and wage_journal(cur,r['body']['result']['work_completion_id'])==(D(20),D(20),1)
        return dict(status='PASS',real_Auth_recorded=5,wage='WIP 20 / CONTRACTOR_PAYABLE 20',staff_refused=str(denied['body'])[:200])
    def finish_http():
        # G2 over real Auth + PostgREST: the Admin finishes the PO from the HPP screen path; a STAFF login is refused and changes nothing.
        admin=http.login('ADMIN','cp17-finish');staff=http.login('ADMIN','cp17-finish-staff')
        with http.connect()as conn,conn.cursor()as cur:
            f=finish_fixture(cur,today)
            role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,))
            for key in('finance.hpp.view','finance.hpp.manage'):
                cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
            _,staff_role=s.source.procurement.custom(cur,['finance.hpp.view','finance.hpp.manage'])
            cur.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(staff_role,staff.auth_user_id));conn.commit()
        found=admin.rpc('erp_cp7_list_po_finish_v1',dict(p_query=f['number'],p_offset=0));assert found['status']==200 and [r['id'] for r in found['body']['rows']]==[f['po']],found
        w=admin.rpc('erp_cp7_get_po_finish_v1',dict(p_po=f['po']));assert w['status']==200 and w['body']['eligible'],w
        p=dict(action='FINISH',po_id=f['po'],review_token=w['body']['review_token'],change_reason='CP17 PO selesai lewat login')
        denied=staff.rpc('erp_cp7_finish_po_v1',dict(p_payload=p,p_request=str(uuid.uuid4())))
        assert denied['status'] in(400,401,403) and 'CP7_PO_FINISH_DENIED' in str(denied['body']),denied
        with http.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);assert po_state(cur,f['po'])['status']!='FINISHED'
        r=admin.rpc('erp_cp7_finish_po_v1',dict(p_payload=p,p_request=str(uuid.uuid4())))
        assert r['status']==200 and r['body']['result']['status']=='FINISHED',r
        with http.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);state=po_state(cur,f['po']);assert state['status']=='FINISHED' and state['wip']==0,state
        return dict(status='PASS',real_Auth_finished=f['number'],final_hpp=r['body']['result']['hpp'],staff_refused=str(denied['body'])[:200])
    def reopen_http():
        # R2-05 (D15-4): real Auth and PostgREST; an Admin with the HPP rights reopens, a STAFF user with the same rights is refused.
        admin=http.login('ADMIN','cp17-reopen');staff=http.login('ADMIN','cp17-reopen-staff')
        with http.connect()as conn,conn.cursor()as cur:
            f=finish_fixture(cur,today);finish_command(cur,finish_workspace(cur,f['po']))
            role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,))
            for key in('finance.hpp.view','finance.hpp.manage'):
                cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
            _,staff_role=s.source.procurement.custom(cur,['finance.hpp.view','finance.hpp.manage'])
            cur.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(staff_role,staff.auth_user_id));conn.commit()
        w=admin.rpc('erp_cp7_get_po_reopen_v1',dict(p_po=f['po']));assert w['status']==200 and w['body']['eligible'],w
        p=dict(action='REOPEN',po_id=f['po'],review_token=w['body']['review_token'],change_reason='CP17 PO dibuka ulang lewat login')
        denied=staff.rpc('erp_cp7_reopen_po_v1',dict(p_payload=p,p_request=str(uuid.uuid4())))
        assert denied['status'] in(400,401,403) and 'CP7_PO_FINISH_DENIED' in str(denied['body']),denied
        with http.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);assert po_state(cur,f['po'])['status']=='FINISHED'
        r=admin.rpc('erp_cp7_reopen_po_v1',dict(p_payload=p,p_request=str(uuid.uuid4())))
        assert r['status']==200 and r['body']['result']['status']!='FINISHED',r
        with http.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);state=po_state(cur,f['po']);assert state['status']!='FINISHED' and posted_closes(cur,f['po'])==0,state
        return dict(status='PASS',real_Auth_reopened=f['number'],restored_status=state['status'],staff_refused=str(denied['body'])[:200])
    def spent_correction_http(replacement):
        # Sol correction_http.py, real Auth and PostgREST, source-bound public workspace token, own amounts.
        owner=http.login('OWNER','cp17-r2-'+replacement.replace('.','-'))
        with http.connect()as conn,conn.cursor()as cur:
            f=edit.fixture(cur,today,amount='30.01');out=pay.fixture(cur,today);out['cash']=f['bank'];pay.command(cur,pay.payload(cur,out,'20.00'))
            assert balance(cur,f['bank'])==D('10.01');conn.commit()
        w=owner.rpc(edit.READ,dict(p_query=dict(sale_id=f['sale'],payment_id=f['payment'])));assert w['status']==200 and w['body']['eligible'],w
        d=w['body']['document']
        p=dict(sale_id=f['sale'],payment_id=f['payment'],review_token=w['body']['review_token'],change_reason='CP17 koreksi penerimaan sesudah uangnya terpakai',
               replacement=dict(payment_number=d['number'],payment_date=d['physical_at'],amount=replacement,cash_account_id=d['cash_account_id'],
                                payment_method=d['method'],reference_number=d['reference'],notes=d['notes']))
        r=owner.rpc(edit.RPC,dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=w['body']['row_version']))
        with http.connect()as conn,conn.cursor()as cur:after=balance(cur,f['bank']);conn.rollback()
        return r,after
    def http_spent_positive():
        r,after=spent_correction_http('25.01');assert r['status']==200 and after==D('5.01'),(r,after)
        return dict(status='PASS',real_Auth_correction_committed=True,bank_after='5.01')
    def http_spent_negative():
        r,after=spent_correction_http('15.01');assert r['status']==400 and 'CP7_CASH_NEGATIVE' in str(r['body']) and after==D('10.01'),(r,after)
        return dict(status='PASS',real_Auth_refused=r['body'].get('message'),bank_unchanged='10.01')
    return [('CP17_HTTP_CASH_EMPTY_BANK_REFUSED',cash_refused),('CP17_HTTP_PAYROLL_EARLY_REFUSED',payroll_early),('CP17_HTTP_KASBON_GIVE',kasbon_give_http),
            ('CP17_HTTP_ERP_WRITERS_NOT_REACHABLE',erp_writers_closed),('CP17_HTTP_G1_SEWING_RECORD',sewing_http),('CP17_HTTP_G2_FINISH_PO',finish_http),
            ('CP17_HTTP_R2_SPENT_INCOME_CORRECTION_COMMITS',http_spent_positive),('CP17_HTTP_R2_SPENT_INCOME_GENUINE_NEGATIVE_REFUSED',http_spent_negative),
            ('CP17_HTTP_R2_PO_REOPEN',reopen_http)]+master.http_cases(http,today)+autopo.http_cases(http,today)+cutover.http_cases(http,today)+wave.http_cases(http,today)
