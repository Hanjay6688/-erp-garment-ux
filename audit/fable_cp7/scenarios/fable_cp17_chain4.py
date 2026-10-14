"""Fable cp17 chain, run 4 = run 3 with two more plumbing fixes (run 3 38559631518: material_stock_movements has no created_at;
the claim helper ran set-role in an aborted transaction and masked the real error as 25P02). Oracles unchanged.

Run 3 docstring:
Fable cp17 chain, run 3 (only the two sub-cases that did not reach their oracle in run 2 38558699494; R1-05 is not re-run).
Run 3 changes: target dates normalised to date (run 2 TypeError), Native claim writer called as the database owner
with the OWNER JWT claims kept (run 2: 42501 on erp.save_laundry_claim_v2 for the authenticated role). Oracles unchanged.

Original run 2 docstring:
Fable cp17 chain, run 2 (run 1 = fable_cp17_chain.py, run 38557410928, kept unchanged as first-failure evidence).
Changes vs run 1 are fixture/plumbing only; oracles are stated before any observation of these cases:
  * CLOSE case never reached its oracle in run 1 (the product refuses closing through today: 'Tutup buku hanya boleh sampai
    tanggal sebelum hari ini'). Run 2 closes through yesterday (C) after creating documents dated <= C.
    Oracle (INV-T02 + D01 §3.4, owner-approved): after the close, every NEW journal has transaction_date > C (recognised in
    the open period); a new journal whose economic_date <= C must be visible as a change to the filed period
    (owner snapshot for C flags changed_since_filing, or readiness for C is not READY). Violation -> COUNTEREXAMPLE.
  * R1-05 adds detectors: payroll integrity runner, period_blockers_v1 and readiness on the day of the negative payable.
  * R3-03 reaches the Native claim writers (erp.save_laundry_claim_v2 / erp.resolve_laundry_claim) through the E01
    receipt line (run 1 failed on a column lookup before reaching any writer).
"""
from datetime import datetime,time,timedelta,timezone
from decimal import Decimal as D
import json,re,uuid
import psycopg
import cp7_p18_full_cycle_cases as full
import cp7_f03_e01_cases as e01
import cp7_receipt_correction_cases as receipt_fix
import cp7_supplier_payment_correction_cases as sp_fix
import cp7_settlement_cases as settlement
from fable_cp17_chain import worst,q,one,sp,js,prelude
b=e01.settlement.b
WIB=timezone(timedelta(hours=7))

def find(obj,key):
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k==key:return v
            r=find(v,key)
            if r is not None:return r
    if isinstance(obj,list):
        for v in obj:
            r=find(v,key)
            if r is not None:return r
    return None

def as_db_owner(cur,sql,args=()):
    """OWNER JWT claims kept, session authorization reset to the database owner (Native writers are not granted to authenticated).
    On error the exception propagates untouched; the caller's savepoint rolls back and restores the admin session."""
    e01.prod.owner(cur);cur.execute('reset session authorization')
    v=cur.execute(sql,args).fetchone()[0]
    b.api.admin(cur);return v

def detectors(cur,day):
    out={}
    for name,sql,args in (('payroll_integrity','select coalesce(jsonb_agg(to_jsonb(x)),\'[]\') from erp.run_v263a_payroll_integrity_checks() x',()),
                          ('period_blockers','select to_jsonb(erp.period_blockers_v1(%s,%s))',(day,day-timedelta(days=40))),
                          ('period_readiness','select to_jsonb(erp.period_readiness_v1(%s,%s))',(day,day-timedelta(days=40)))):
        r=sp(cur,lambda:e01.native(cur,sql,args))
        out[name]=r[1] if r[0]=='OK' else dict(error=r)
    text=json.dumps(out,default=str)
    out['mentions_payroll_or_contractor_payable']=bool(re.search(r'PAYROLL|CONTRACTOR_PAYABLE|PAYABLE_NEGATIVE|NEGATIVE',text,re.I))
    out['readiness_status']=find(out.get('period_readiness'),'status')
    return out

def cases(cur,today):
    yday=today-timedelta(days=1)
    def closed_period_recognition():
        prelude(cur,today);f=e01.production(cur,today);b.api.admin(cur)
        pre={}
        # a supplier payment dated yesterday (inside the period to be closed), through the CP7 application writer
        at=datetime.combine(yday,time(12,0),tzinfo=WIB)
        pre['supplier_payment_yesterday']=js(sp(cur,lambda:full.supplier_payment(cur,f,'400.00',at)[0]))
        pay=cur.execute("select id::text,payment_date from erp.supplier_payments where purchase_id=%s and status='POSTED' order by created_at limit 1",(f['purchase'],)).fetchone()
        auth=settlement.auth
        def ws(d):
            auth.actor(cur,None);r=one(cur,'select public.erp_cp7_get_period_control_v1(%s)',(d,));b.api.admin(cur);return r
        def close(d):
            st=ws(d);p=dict(through=str(d),review_through=str(d),review_token=st['review_token'],reason='Fable cp17 tutup buku untuk uji koreksi mundur')
            auth.actor(cur,None);r=one(cur,'select public.erp_cp7_save_period_control_v1(%s,%s,%s)',('CLOSE',json.dumps(p),uuid.uuid4()));b.api.admin(cur);return r
        closed=sp(cur,lambda:close(yday));route='APP_erp_cp7_save_period_control_v1'
        if closed[0]!='OK':
            pre['app_close_refused']=js(closed)
            closed=sp(cur,lambda:e01.native(cur,'select erp.close_accounting_through(%s,%s)::text',(yday,'Fable cp17 fallback close')));route='NATIVE_erp.close_accounting_through'
            if closed[0]!='OK':return dict(status='FAIL',reason='could not close',pre=pre,native_close=js(closed),closed_through_target=str(yday))
        C=one(cur,'select closed_through from erp.accounting_period_control where singleton_id=1')
        snap0=sp(cur,lambda:e01.native(cur,'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',(C-timedelta(days=30),C,C)))
        cut=datetime.combine(C,time(23,59,59),tzinfo=WIB)
        def mvcount():return dict(material=one(cur,"select count(*) from erp.material_stock_movements where physical_at<=%s",(cut,)),fg=one(cur,"select count(*) from erp.fg_stock_movements where physical_at<=%s",(cut,)))
        mv0=mvcount()
        t_close=one(cur,'select clock_timestamp()');attempts={}
        def attempt(name,fn,target):
            r=sp(cur,fn)
            attempts[name]=dict(outcome='ACCEPTED' if r[0]=='OK' else ('PLUMBING' if r[0]=='PY' else 'REFUSED'),result=js(r),target_date=str(target),inside_closed=bool(target and (target.date() if hasattr(target,'date') else target)<=C))
        rec_date=one(cur,"select min(economic_date) from erp.journal_entries where source_id=%s",(f['purchase'],))
        def do_receipt():
            w=receipt_fix.ws(cur,f['purchase'])
            def bump(n,item):item['unit_price']=str(D(item['unit_price'])+1)
            p=receipt_fix.payload(w,line=bump);return receipt_fix.fix(cur,p,w.get('row_version') or w.get('version'))
        attempt('CP7_RECEIPT_CORRECTION_PRICE',do_receipt,rec_date)
        if pay:
            def do_sp():
                p=sp_fix.payload(cur,dict(receipt=dict(purchase_id=f['purchase']),payment=pay[0]),amount='401.00');return sp_fix.correct(cur,p)
            attempt('CP7_SUPPLIER_PAYMENT_CORRECTION_AMOUNT',do_sp,pay[1])
        d=settlement.doc(cur,f['payroll'])
        attempt('CP7_PAYROLL_PAY_DATED_CLOSED_DAY',lambda:settlement.act(cur,'PAY',d,None,payment_date=str(yday),cash_account_id=f['bank']),yday)
        vendor=dict(target_kind='VENDOR_INVOICE',target_id=f['laundry_invoice'],amount='120.00',date=str(yday),cash_account_id=f['bank'],reason='Fable cp17 bayar laundry bertanggal periode tertutup')
        attempt('BD_VENDOR_PAY_DATED_CLOSED_DAY',lambda:e01.laundry.bd(cur,'PAY_VENDOR_DOCUMENT',vendor,key=uuid.uuid4()),yday)
        try:
            new=q(cur,"select id::text,source_type,economic_date::text,transaction_date::text,status from erp.journal_entries where created_at>%s order by created_at",(t_close,))
            recognised_in_closed=[r for r in new if r[3] and r[3]<=str(C)]
            economic_in_closed=[r for r in new if r[2] and r[2]<=str(C)]
            mv1=mvcount();mv=dict(before=mv0,after=mv1)
            snap1=sp(cur,lambda:e01.native(cur,'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',(C-timedelta(days=30),C,C)))
            flag0=find(snap0[1],'changed_since_filing') if snap0[0]=='OK' else None
            flag1=find(snap1[1],'changed_since_filing') if snap1[0]=='OK' else None
            ready1=find(snap1[1],'status') if snap1[0]=='OK' else None
            silent=bool(economic_in_closed) and flag1 is not True
            reached=[k for k,v in attempts.items() if v['outcome']!='PLUMBING' and v['inside_closed']]
            if not reached:status='FAIL'
            elif recognised_in_closed or silent:status='COUNTEREXAMPLE'
            else:status='PASS'
            return dict(status=status,close_route=route,closed_through=str(C),pre=pre,attempts=attempts,new_journals=new,
                        recognised_in_closed=recognised_in_closed,economic_in_closed=economic_in_closed,movements_after_close_dated_closed=mv,
                        changed_since_filing_before=flag0,changed_since_filing_after=flag1,snapshot_status_after=ready1,
                        oracle='INV-T02 + D01 §3.4: new journals recognised after C; economic_date<=C only with changed_since_filing visible',fixture_origin='writer E01 production')
        except Exception as e:
            b.api.admin(cur)
            return dict(status='INCOMPLETE',stage='analysis_after_attempts',error=(type(e).__name__+': '+str(e))[:400],closed_through=str(C),close_route=route,pre=pre,attempts=attempts)

    def claim_only():
        prelude(cur,today);f=e01.production(cur,today);b.api.admin(cur);subs={}
        # R3-03: Native claim writers on the E01 laundry receipt line
        try:
            line=f['receipts'][0]['line'];deliv=f['receipts'][0]['delivery']
            first_ap=one(cur,"select min(j.economic_date) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=erp.account_id('AP_VENDOR') and l.vendor_id=%s and j.status='POSTED'",(f['vendor'],))
            early_res=(first_ap or today)-timedelta(days=200)
            payload=dict(action='SAVE',claim_number='FABLE-CP17-DMG',vendor_id=f['vendor'],delivery_id=deliv,receipt_line_id=line,qty_claimed=1,claim_type='DAMAGE',
                         compensation_amount=20,opened_at=datetime.now(timezone.utc).isoformat(),resolution_date=str(early_res),change_reason='Fable cp17 R3-03 probe')
            save=sp(cur,lambda:as_db_owner(cur,'select erp.save_laundry_claim_v2(%s::jsonb,%s,null)',(json.dumps(payload),str(uuid.uuid4()))))
            claim=None;res=None
            if save[0]=='OK':
                claim=find(save[1],'claim_id') or find(save[1],'id')
                res=sp(cur,lambda:as_db_owner(cur,"select erp.resolve_laundry_claim(%s,'SETTLED',%s)::text",(claim,'Fable cp17 R3-03 settle backdated')))
            jd=q(cur,"select economic_date::text,transaction_date::text,source_type,status from erp.journal_entries where source_type='LAUNDRY_CLAIM_SETTLEMENT' and source_id::text=%s",(str(claim),)) if claim else []
            ap_asof=one(cur,"select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=erp.account_id('AP_VENDOR') and l.vendor_id=%s and j.status='POSTED' and j.economic_date<=%s",(f['vendor'],early_res))
            backdated=[x for x in jd if x[0]==str(early_res)]
            NOT_REACHED=('PY','42501','25P02')
            reached=save[0] not in NOT_REACHED and (save[0]!='OK' or (res is not None and res[0] not in NOT_REACHED))
            st='COUNTEREXAMPLE' if (res and res[0]=='OK' and backdated and D(ap_asof)<0) else ('PASS' if reached else 'FAIL')
            subs['R3_03_CLAIM_SETTLED_BEFORE_FIRST_AP']=dict(status=st,first_vendor_ap_date=str(first_ap),resolution_date=str(early_res),save=js(save),resolve=js(res),claim_journals=jd,vendor_ap_as_of_resolution_date=str(ap_asof))
        except Exception as e:
            b.api.admin(cur)
            subs['R3_03_CLAIM_SETTLED_BEFORE_FIRST_AP']=dict(status='FAIL',error=(type(e).__name__+': '+str(e))[:300],note='plumbing; not evidence')
        return dict(status=worst(subs),sub=js(subs),fixture_origin='writer E01 production (unpaid vendor invoice)')
    return [('FABLE_CHAIN4:CLOSED_PERIOD_RECOGNITION',closed_period_recognition),('FABLE_CHAIN4:R3_03_CLAIM_SETTLED_BEFORE_FIRST_AP',claim_only)]

def races(tools,today):return []
def http_cases(http,today):return []
