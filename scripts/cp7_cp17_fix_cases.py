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
Oracles do not come from the guards: dates are read from the Native accrual journals and source rows, balances
from journal lines and movements. Every refusal leaves the whole business boundary unchanged and has a lawful
control. Fixture banks receive owner capital through the accepted Native journal (cp7_cash_funding) only where the
case says so; an empty bank stays empty.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import threading,uuid
import psycopg
import cp7_settlement_cases as s
import cp7_installment_cases as instal
import cp7_supplier_payment_create_cases as pay
import cp7_cutting_correction_cases as cut
import cp7_material_cases as material
import cp6_bd_probe as bd
import cp7_cash_funding as funding

auth,b,bc=s.auth,s.b,s.bc
refused=auth.refused
CONTRACT='cp7.cp17-fixes.v1'
FUNCTIONS=('erp_cp7_save_payroll_v1','erp_cp7_save_payroll_installment_v1','erp_cp7_create_supplier_payment_v1',
           'erp_save_laundry_bd_action_v1','erp_save_bs_resolution_action_v1','erp_cp7_get_material_ledger_v1','erp_cp7_get_material_ledger_v2')
IDS=dict(
    native=['CP17_FIN01_FULL_PAY_BEFORE_ATTENDANCE_REFUSED','CP17_FIN01_WORK_ONLY_BEFORE_COMPLETION_REFUSED',
            'CP17_FIN01_INSTALLMENT_BEFORE_ACCRUAL_REFUSED','CP17_FIN01_DIRECT_NATIVE_PAYMENT_REFUSED',
            'CP17_CASH_EMPTY_BANK_REFUSED','CP17_CASH_EXACT_ZERO_ALLOWED_THEN_REFUSED','CP17_CASH_BACKDATE_BEFORE_FUNDS_REFUSED',
            'CP17_CASH_LATER_DAY_PROTECTED','CP17_CASH_PAYROLL_EMPTY_BANK_REFUSED','CP17_CASH_LAUNDRY_VENDOR_EMPTY_BANK_REFUSED',
            'CP17_FIN02_CLAIM_SAME_DAY_CONTROL','CP17_FIN02_CLAIM_BEFORE_SOURCE_REFUSED','CP17_FIN02_CLAIM_AP_NOT_AVAILABLE_REFUSED',
            'CP17_STK01_REOPEN_REPOST_CARD_NOT_NEGATIVE'],
    races=['CP17_RACE_TWO_PAYMENTS_ONE_BANK'],
    http=['CP17_HTTP_CASH_EMPTY_BANK_REFUSED','CP17_HTTP_PAYROLL_EARLY_REFUSED'],
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

    named=[full_attendance,work_only,installment,direct_native,empty_bank,exact_zero,backdate,later_day,payroll_empty,laundry_empty,
           claim_control,claim_before_source,claim_ap_not_available,stock_card]
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
    return [('CP17_RACE_TWO_PAYMENTS_ONE_BANK',two_payments)]


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
    return [('CP17_HTTP_CASH_EMPTY_BANK_REFUSED',cash_refused),('CP17_HTTP_PAYROLL_EARLY_REFUSED',payroll_early)]
