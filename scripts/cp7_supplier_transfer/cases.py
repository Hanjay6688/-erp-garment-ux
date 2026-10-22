"""Bounded Native checkpoint: exact group money and existing single-payment oracles.

Receipts are posted through the existing public procurement writer. Synthetic
master/bank fixtures are explicit. This is not a real-Auth or browser claim.
"""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid

import cp7_supplier_payment_create_cases as single
from cp7_contractor_correction import native_cases as shared

auth,b=single.auth,single.b
IDS=('OW06_ONE_TRANSFER_TWO_RECEIPTS_EXACT_CASH',
     'OW06_REQUEST_AND_ALLOCATION_REFUSALS_ATOMIC',
     'OW06_REVERSE_WHOLE_TRANSFER_NO_INDIVIDUAL_CHILD',
     'OW06_FOUR_CORRECTIONS_RETAIN_ECONOMIC_DATES',
     'OW06_EMPTY_BANK_AND_LAST_POST_FAILURE_ATOMIC',
     'OW06_NATIVE_DETECTOR_ZERO_ONE_ZERO_AND_USED_ROLLBACK_REFUSAL')
RETAINED=('CP7_SUPPLIER_PAYMENT_CREATE_EXACT_REPLAY_SETTLE','CP7_SUPPLIER_PAYMENT_CREATE_REFUSALS_ZERO_EFFECT',
          'CP7_SUPPLIER_PAYMENT_CREATE_CURRENT_ACCESS','CP7_SUPPLIER_PAYMENT_CREATE_PRIVATE_BOUNDARY')
REASON='Satu transfer supplier dibagi ke penerimaan'
STATE_FOR_ROLLBACK=None


def read(cur,f,transfer=None):
    auth.actor(cur)
    r=cur.execute('select public.erp_cp7_get_supplier_transfer_v1(%s)',
        (json.dumps(dict(supplier_id=f['supplier'],transfer_id=transfer)),)).fetchone()[0]
    b.api.admin(cur);return r


def command(cur,p,key=None):
    auth.actor(cur)
    r=cur.execute('select public.erp_cp7_save_supplier_transfer_v1(%s,%s)',(json.dumps(p),key or uuid.uuid4())).fetchone()[0]
    b.api.admin(cur);return r


def fixture(cur,today,capital='1000.00'):
    first=single.fixture(cur,today,capital)
    second=single.invoice.fixture(cur,today,'100','10',True)
    supplier=str(cur.execute('select supplier_id from erp.material_purchase_headers where id=%s',(first['receipt']['purchase_id'],)).fetchone()[0])
    assert supplier==str(cur.execute('select supplier_id from erp.material_purchase_headers where id=%s',(second['receipt']['purchase_id'],)).fetchone()[0])
    return dict(first=first,second=second,supplier=supplier,cash=first['cash'],
        receipts=[first['receipt']['purchase_id'],second['receipt']['purchase_id']],
        physical=single.supplier.physical_state(cur),bank_start=single.misc.cash_balance(cur,first['cash']))


def payload(cur,f,amounts=('400.00','600.00'),transfer=None,at=None):
    w=read(cur,f,transfer)
    p=dict(action='CORRECT'if transfer else'CREATE',supplier_id=f['supplier'],review_token=w['review_token'],reason=REASON,
        amount=f'{sum(D(a)for a in amounts):.2f}',cash_account_id=f['cash'],payment_date=at or single.at(cur),
        allocations=[dict(purchase_id=pid,amount=value)for pid,value in zip(f['receipts'],amounts)])
    if transfer:p['transfer_id']=transfer
    return p


def reverse_payload(cur,f,transfer):
    return dict(action='REVERSE',supplier_id=f['supplier'],transfer_id=transfer,review_token=read(cur,f,transfer)['review_token'],reason=REASON)


def snapshot(cur):
    return dict(ERP=shared.auth.b.boundary.snapshot(cur),
        private={name:cur.execute('select coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),\'[]\')from cp7_supplier_transfer.'+name+' x').fetchone()[0]
            for name in('requests_v1','transfers_v1','allocations_v1','corrections_v1','context_v1')})


def observe(cur,f,transfer,amounts,status='POSTED'):
    total=sum(D(a)for a in amounts)
    w=read(cur,f,transfer);t=w['selected'];assert t['status']==status and D(t['amount'])==total
    assert len(t['allocations'])==2 and {x['purchase_id']:D(x['amount'])for x in t['allocations']}==dict(zip(f['receipts'],map(D,amounts)))
    for pid,amt in zip(f['receipts'],map(D,amounts)):
        assert cur.execute("select coalesce(sum(amount),0)from erp.supplier_payments where purchase_id=%s and status='POSTED'",(pid,)).fetchone()[0]==(amt if status=='POSTED'else 0)
        assert single.supplier.read(cur,dict(receipt=dict(purchase_id=pid)))['Native_AP']['paid']==f'{amt if status=="POSTED"else D(0):.2f}'
    cash=single.misc.cash_balance(cur,f['cash'])-f['bank_start']
    assert cash==(-total if status=='POSTED'else 0),cash
    assert single.supplier.physical_state(cur)==f['physical'],'OW06_CHANGED_STOCK_HPP'
    assert cur.execute('select cp7_supplier_transfer.valid_transfer_v1(%s)',(transfer,)).fetchone()[0]is True
    assert cur.execute('select count(*)from cp7_supplier_transfer.context_v1').fetchone()[0]==0
    return t


def cases(cur,today):
    def exact():
        f=fixture(cur,today);p=payload(cur,f);key=uuid.uuid4();r=command(cur,p,key);t=observe(cur,f,r['transfer_id'],('400','600'))
        rows=cur.execute("select j.id,l.debit,l.credit,l.account_id::text from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_type='CP7_SUPPLIER_TRANSFER'and j.source_id=%s order by l.debit desc",(t['id'],)).fetchall()
        assert len(rows)==2 and len({x[0]for x in rows})==1 and[(x[1],x[2])for x in rows]==[(D(1000),D(0)),(D(0),D(1000))]
        before=snapshot(cur);assert command(cur,p,key)==r and snapshot(cur)==before
        return dict(status='PASS',allocation_amounts=['400.00','600.00'],one_actual_cash_credit='1000.00',one_journal_two_lines=True,
            two_Native_AP_children=True,same_UUID_replay_no_effect=True,stock_HPP_unchanged=True)

    def refusals():
        f=fixture(cur,today);p=payload(cur,f);before=snapshot(cur);out={}
        for label,bad,code in[
            ('sum',dict(p,amount='1000.01'),'ALLOCATION_TOTAL'),
            ('duplicate',dict(p,allocations=[p['allocations'][0],p['allocations'][0]],amount='800.00'),'DUPLICATE_RECEIPT'),
            ('zero',dict(p,amount='0.00'),'FIELDS'),
            ('extra',dict(p,unknown='x'),'FIELDS'),
            ('over',dict(p,amount='1000.02',allocations=[dict(purchase_id=f['receipts'][0],amount='1000.01'),dict(purchase_id=f['receipts'][1],amount='0.01')]),'EXCEEDS_REMAINING'),
            ('future',dict(p,payment_date=(cur.execute('select statement_timestamp()').fetchone()[0]+timedelta(days=1)).isoformat()),'DATE_FUTURE')]:
            out[label]=auth.refused(cur,lambda bad=bad:command(cur,bad),code);assert snapshot(cur)==before
        key=uuid.uuid4();r=command(cur,p,key);after=snapshot(cur)
        out['changed_UUID']=auth.refused(cur,lambda:command(cur,dict(p,reason='Keterangan berubah pada UUID yang sama'),key),'REQUEST_CHANGED')
        out['stale']=auth.refused(cur,lambda:command(cur,p),'STALE_REVIEW');assert snapshot(cur)==after
        return dict(status='PASS',refusals=out,all_refusals_exact_zero_effect=True)

    def reverse():
        f=fixture(cur,today);r=command(cur,payload(cur,f));t=observe(cur,f,r['transfer_id'],('400','600'))
        a=t['allocations'][0];old=single.supplier.read(cur,dict(receipt=dict(purchase_id=a['purchase_id'])))
        child=next(x for x in old['page']['rows']if x['id']==a['payment_id']);assert child['transfer']['id']==t['id']
        before=snapshot(cur)
        auth.refused(cur,lambda:single.supplier.command(cur,dict(purchase_id=a['purchase_id'],payment_id=a['payment_id'],review_token=child['review_token'],reason=REASON)),'USE_PARENT')
        assert snapshot(cur)==before
        p=reverse_payload(cur,f,t['id']);key=uuid.uuid4();rr=command(cur,p,key);back=observe(cur,f,t['id'],('400','600'),'REVERSED')
        assert back['journal']['status']=='REVERSED'and back['inverse']['status']=='POSTED'
        before=snapshot(cur);assert command(cur,p,key)==rr and snapshot(cur)==before
        return dict(status='PASS',all_allocations_reversed=True,one_exact_Native_journal_inverse=True,cash_net='0.00',old_child_route_refused=True,replay_no_effect=True)

    def generations():
        f=fixture(cur,today);at=single.invoice.aa.at(f['first']['day']+timedelta(days=1),12).isoformat()
        original=command(cur,payload(cur,f,at=at));ident=original['transfer_id'];history=[]
        for pair in[('200.00','700.00'),('300.00','500.00'),('400.00','600.00'),('500.00','400.00')]:
            old=ident;r=command(cur,payload(cur,f,pair,transfer=old,at=at));ident=r['transfer_id'];observe(cur,f,ident,pair)
            assert cur.execute('select cp7_supplier_transfer.valid_correction_v1(%s)',(old,)).fetchone()[0]is True
            assert read(cur,f,old)['selected']['status']=='REVERSED';history.append(old)
        assert cur.execute('select count(*)from cp7_supplier_transfer.corrections_v1 where original_id=any(%s::uuid[])',(history,)).fetchone()[0]==4
        assert cur.execute('select count(*)from cp7_supplier_transfer.corrections_v1 where original_id=any(%s::uuid[])and time_neutral_id is not null and effective_inverse_id is not null',(history,)).fetchone()[0]==4
        return dict(status='PASS',corrections=4,original_and_successors_retained=True,exact_current_cash='900.00',old_economic_date_preserved=True,Native_current_reversal_and_two_exact_date_restatements=True)

    def empty_bank():
        f=fixture(cur,today,capital=None);before=snapshot(cur)
        refused=auth.refused(cur,lambda:command(cur,payload(cur,f)),'CP7_CASH_NEGATIVE')
        assert snapshot(cur)==before
        # Failure occurs at the aggregate journal, after both Native child
        # posts: the entire command must remove both effects and its request.
        assert cur.execute('select count(*)from cp7_supplier_transfer.allocations_v1').fetchone()[0]==0
        return dict(status='PASS',empty_bank_refused=refused,last_post_failure_rolls_back_both_children_parent_request_journal=True)

    def detector():
        f=fixture(cur,today);r=command(cur,payload(cur,f));t=observe(cur,f,r['transfer_id'],('400','600'))
        def count():return cur.execute("select issue_count from erp.run_v267_financial_truth_checks()where check_name='OW06_SUPPLIER_TRANSFER_FACTS'").fetchone()[0]
        assert count()==0
        cur.execute('savepoint detector_tamper');cur.execute('update erp.supplier_payments set amount=amount+0.01 where id=%s',(t['allocations'][0]['payment_id'],));assert count()==1
        cur.execute('rollback to savepoint detector_tamper');cur.execute('release savepoint detector_tamper');assert count()==0
        from cp7_supplier_transfer import composition as product
        before=snapshot(cur)
        try:product.rollback_preuse(cur,STATE_FOR_ROLLBACK)
        except ValueError as error:assert str(error)=='CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE',str(error)
        else:raise AssertionError('USED_INSTALLATION_WAS_REMOVED')
        assert snapshot(cur)==before
        return dict(status='PASS',read_only_detector_counts=[0,1,0],actual_one_cent_Native_child_corruption_detected=True,used_rollback_refused_before_DDL_no_facts_deleted=True)

    new=list(zip(IDS,[exact,refusals,reverse,generations,empty_bank,detector]))
    retained=single.cases(cur,today)
    assert len(retained)==4
    return new+retained
