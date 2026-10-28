"""Actual disposable Native cases, using existing production/BD/import writers.

Only synthetic masters are inserted directly. Money is funded through the
retained Native capital journal, never by bypassing a guard or seeding balances.
"""
from datetime import timedelta
from decimal import Decimal as D
import uuid
import cp6_bd_probe as bd
import cp7_cash_funding as funding

IDS=('OW08B_VENDOR_PAID_CORRECTION_AR_HPP_EXACT',
     'OW08B_VENDOR_UNPAID_ORIGIN_AUTO_APPLICATION',
     'OW08B_VENDOR_NEXT_INVOICE_AND_CASH_REFUND',
     'OW08B_VENDOR_REFUND_REPLAY_INVERSE_HISTORY',
     'OW08B_VENDOR_AMOUNT_DATE_ACCOUNT_REFUSALS',
     'OW08B_VENDOR_OPENING_APPLICATION_AND_INVERSE',
     'OW08B_VENDOR_UNLINKED_JOURNAL_DETECTED')

def one(cur,sql,*args):return cur.execute(sql,args).fetchone()[0]

def screen(cur,f):return bd.bd_ws(cur,dict(vendor_id=f['vendor']))['payables']

def fixture(cur,today,paid=True,goods=False,opening=False):
    opening_balance=None;vendor=None
    if opening:
        imported=bd.bbp.production_post(cur,today,bd.w05_rows(today,claims=(),payable=('10000000.00','0.00')))
        vendor=one(cur,'select id::text from erp.laundry_vendors where vendor_code=%s',imported['code'])
        opening_balance=one(cur,"select id::text from erp.opening_subledger_balances where vendor_id=%s and party_type='VENDOR'and direction='PAYABLE'",vendor)
    f=bd.fixture(cur,today-timedelta(days=3),'OW08B_VENDOR_AR')
    if vendor:f['vendor']=vendor
    bd.process_rate(cur,f,'7000.00');bd.invoice_policies(cur,after='CORRECTION_DOCUMENT')
    receipt=bd.receive(cur,bd.plain_delivery(cur,f,10,11),f,10,13)
    f['line']=bd.receipt_line(cur,receipt['receipt_id'])
    if goods:
        f['product'],f['lot']=bd.finish_goods(cur,f,receipt['receipt_id'],10,14)
        bd.sell(cur,f,f['product'],4,16)
    _,invoice=bd.invoice(cur,f,[dict(line=f['line'],qty=10,amount='70000.00')],'70000.00')
    f['invoice']=invoice['invoice_id']
    # Synthetic dedicated masters; no ledger amounts are written directly.
    bd.api.admin(cur)
    f['ar']=str(one(cur,"insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active)values(%s,'OW08b vendor receivable','ASSET','CURRENT_ASSETS','DEBIT',true,true)returning id",'VAR'+uuid.uuid4().hex[:12]))
    f['cash']=bd.bcp.bank_account(cur,'VAR'+uuid.uuid4().hex[:10])
    if paid:
        funding.fund(cur,f['cash'],'70000.00',f['day'])
        bd.bd(cur,'PAY_VENDOR_DOCUMENT',dict(target_kind='VENDOR_INVOICE',target_id=f['invoice'],amount='70000.00',
            date=str(f['day']),cash_account_id=f['cash'],reason='OW08b bayar invoice sumber'))
    f['today']=today;f['opening']=opening_balance
    return f

def correction(cur,f,amount='-3000.00',account=True):
    draft,_=bd.correction(cur,f,f['line'],amount,f['invoice'],f['today'],post=False)
    p=dict(invoice_id=draft['invoice_id'],expected_version=draft['row_version'])
    if account:p['vendor_receivable_account_id']=f['ar']
    return bd.bd(cur,'POST_INVOICE',p)

def refund(cur,f,source,amount='1000.00',key=None,**changes):
    p=dict(source_id=source,amount=amount,date=str(f['today']),cash_account_id=f['cash'],reason='OW08b pengembalian bank dari vendor')
    return bd.bd(cur,'RECEIVE_VENDOR_REFUND',dict(p,**changes),key=key)

def use(cur,f,source,target,amount,kind='VENDOR_INVOICE',key=None):
    return bd.bd(cur,'APPLY_CLAIM_CREDIT',dict(source_kind='INVOICE_CORRECTION',source_id=source,target_kind=kind,
        target_id=target,amount=amount,date=str(f['today']),reason='OW08b pakai piutang untuk tagihan vendor'),key=key)

def state(cur,f):
    bd.api.admin(cur)
    # Retained refusal/boundary helpers select UTC. to_jsonb(timestamptz)
    # follows that GUC, so compare every original field in one representation.
    # No timestamp, column or business amount is removed or changed (E25z).
    zone=cur.execute('show timezone').fetchone()[0]
    try:
        cur.execute("select set_config('TimeZone','UTC',true)")
        return dict(origin=cur.execute("select h.status,h.total_amount::text,(select jsonb_agg(to_jsonb(p)order by p.id)from erp.vendor_payments p where p.vendor_invoice_id=h.id)from erp.vendor_invoices h where h.id=%s",(f['invoice'],)).fetchone(),
            ar=str(one(cur,"select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED')and l.account_id=%s",f['ar'])),
            ap=bd.ap(cur,f['vendor']),cash=str(one(cur,"select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED')and l.account_id=%s",funding.coa(cur,f['cash']))))
    finally:
        cur.execute("select set_config('TimeZone',%s,true)",(zone,))

def cases(cur,today):
    def paid_hpp():
        f=fixture(cur,today,goods=True);before=state(cur,f);history=bd.d12_history(cur,f['vendor'],f['day'])
        truth=bd.all_truth(cur);g={k:bd.gl(cur,k)for k in('WIP','FG_INVENTORY','COGS')}
        c=correction(cur,f);after=state(cur,f);s=screen(cur,f)
        delta={k:bd.gl(cur,k)-v for k,v in g.items()}
        assert delta==dict(WIP=D(0),FG_INVENTORY=D('-1800.00'),COGS=D('-1200.00')),delta
        assert after['origin']==before['origin']and after['ar']=='3000.00'and D(after['ap'])==0,(before,after)
        assert history==bd.d12_history(cur,f['vendor'],f['day'])
        assert s['ledger']['matches']and s['ledger']['receivable_balance']=='3000.00',s
        assert bd.truth_quiet(truth,bd.all_truth(cur))
        return dict(status='PASS',correction=c['invoice_id'],hpp_delta={k:str(v)for k,v in delta.items()},before=before,after=after,ledger=s['ledger'],original_history_immutable=True)

    def unpaid():
        f=fixture(cur,today,paid=False);c=correction(cur,f);s=screen(cur,f);credit=next(x for x in s['credits']if x['id']==c['invoice_id'])
        assert credit['available']=='0.00'and credit['applied']=='3000.00',credit
        assert s['ledger']['matches']and s['ledger']['receivable_balance']=='0.00'and D(bd.ap(cur,f['vendor']))==D('67000.00'),s
        return dict(status='PASS',credit=credit,ledger=s['ledger'])

    def next_invoice():
        f=fixture(cur,today);c=correction(cur,f)
        _,up=bd.correction(cur,f,f['line'],'1000.00',f['invoice'],today)
        use(cur,f,c['invoice_id'],up['invoice_id'],'1000.00')
        r=refund(cur,f,c['invoice_id'],'2000.00');s=screen(cur,f)
        assert state(cur,f)['ar']=='0.00'and D(bd.ap(cur,f['vendor']))==0
        assert s['ledger']['matches']and s['ledger']['receivable_balance']=='0.00'
        assert next(x for x in s['documents']if x['id']==up['invoice_id'])['status']=='PAID'
        refused=bd.refused(cur,lambda:refund(cur,f,c['invoice_id'],'0.01'),'BD_CLAIM_CREDIT_EXCEEDS_AVAILABLE')
        assert refused['ok'],refused
        return dict(status='PASS',refund=r,ledger=s['ledger'],double_use_refused=refused)

    def replay_inverse():
        f=fixture(cur,today);before=state(cur,f);origin=before['origin'];c=correction(cur,f);key=uuid.uuid4()
        r=refund(cur,f,c['invoice_id'],key=key);again=refund(cur,f,c['invoice_id'],key=key)
        assert again['replayed']is True and again['refund_id']==r['refund_id']
        assert one(cur,'select count(*)from cp7_vendor_receivable.refunds_v1 where id=%s',str(key))==1
        bad=bd.refused(cur,lambda:refund(cur,f,c['invoice_id'],'1001.00',key=key),'BD_REQUEST_REUSED');assert bad['ok'],bad
        version=str(one(cur,'select row_version from erp.bd_laundry_invoices_v1 where id=%s',c['invoice_id']))
        locked=bd.refused(cur,lambda:bd.bd(cur,'REVERSE_INVOICE',dict(invoice_id=c['invoice_id'],expected_version=version,reason='OW08b masih ada uang dikembalikan')),'BD_CLAIM_CREDIT_IN_USE');assert locked['ok'],locked
        inv=bd.bd(cur,'REVERSE_VENDOR_REFUND',dict(refund_id=r['refund_id'],reason='OW08b batal bukti pengembalian'))
        after_refund_inverse=state(cur,f)
        assert after_refund_inverse['ar']=='3000.00'and after_refund_inverse['origin']==origin,dict(expected_ar='3000.00',expected_origin=origin,observed=after_refund_inverse)
        assert one(cur,'select count(*)from cp7_vendor_receivable.refunds_v1 where id=%s',r['refund_id'])==1
        bd.bd(cur,'REVERSE_INVOICE',dict(invoice_id=c['invoice_id'],expected_version=version,reason='OW08b batal koreksi sesudah refund dibalik'))
        after_source_inverse=state(cur,f)
        assert after_source_inverse['ar']=='0.00'and after_source_inverse['origin']==origin,dict(expected_ar='0.00',expected_origin=origin,observed=after_source_inverse)
        return dict(status='PASS',original_refund=r,replayed=again,reversal=inv,before=before,
            after_refund_inverse=after_refund_inverse,after_source_inverse=after_source_inverse,
            origin_history_immutable=True,source_reversed=True,metadata_comparison_timezone='UTC')

    def refusals():
        f=fixture(cur,today)
        old=bd.refused(cur,lambda:correction(cur,f,account=False),'BD_CORRECTION_EXCEEDS_PAYABLE');assert old['ok'],old
        c=correction(cur,f);before=state(cur,f)
        checks=[bd.refused(cur,lambda:refund(cur,f,c['invoice_id'],'3000.01'),'BD_CLAIM_CREDIT_EXCEEDS_AVAILABLE'),
            bd.refused(cur,lambda:refund(cur,f,c['invoice_id'],date=str(today-timedelta(days=1))),'BD_CLAIM_CREDIT_BEFORE_APPROVAL'),
            bd.refused(cur,lambda:refund(cur,f,c['invoice_id'],cash_account_id=f['ar']),'BD_CASH_ACCOUNT_REQUIRED'),
            bd.refused(cur,lambda:refund(cur,f,c['invoice_id'],'0.001'),'BD_AMOUNT_INVALID')]
        assert all(x['ok']for x in checks),checks
        assert state(cur,f)==before
        return dict(status='PASS',old_AP_refusal_retained=old,refusals=checks,all_refused_zero_effect=True)

    def opening():
        f=fixture(cur,today,opening=True);c=correction(cur,f);before=D(bd.ap(cur,f['vendor']));key=uuid.uuid4()
        use(cur,f,c['invoice_id'],f['opening'],'3000.00','OPENING_PAYABLE',key)
        s=screen(cur,f);assert s['ledger']['matches']and state(cur,f)['ar']=='0.00'
        assert D(bd.ap(cur,f['vendor']))==before-D('3000.00')
        bd.bd(cur,'REVERSE_VENDOR_SETTLEMENT',dict(target_kind='OPENING_PAYABLE',settlement_id=str(key),reason='OW08b balik pemakaian piutang saldo awal'))
        assert state(cur,f)['ar']=='3000.00'and D(bd.ap(cur,f['vendor']))==before
        assert screen(cur,f)['ledger']['matches']
        return dict(status='PASS',opening_balance=f['opening'],application=str(key),inverse_AR_AP_exact=True)

    def provenance():
        f=fixture(cur,today);correction(cur,f)
        bd.api.admin(cur);cur.execute('savepoint vendor_ar_unlinked')
        try:
            import cp7_finance_analysis_cases as journals
            journals.journal(cur,today,[dict(account_id=f['ar'],vendor_id=f['vendor'],debit='1.00'),dict(account_id=f['ar'],vendor_id=f['vendor'],credit='1.00')],'OW08b explicit unrelated zero-net sensitivity')
            detected=bd.refused(cur,lambda:one(cur,'select cp7_vendor_receivable.prove_v1(%s)',f['vendor']),'CP7_VENDOR_RECEIVABLE_MATERIALIZATION_UNPROVEN')
            assert detected['ok'],detected
        finally:cur.execute('rollback to vendor_ar_unlinked');bd.api.admin(cur)
        assert screen(cur,f)['ledger']['matches']
        return dict(status='PASS',zero_net_unrelated_lines_detected=detected,control_rolled_back=True)

    return list(zip(IDS,(paid_hpp,unpaid,next_invoice,replay_inverse,refusals,opening,provenance)))
