"""Pending consumer Native fixture preparation; not registered or executed.

Importing performs no SQL, connection, installation or commit. The future closed
harness owns the cursor, savepoint and exact restoration. Business setup uses
retained public Native stock/CREATE/POST/settlement writers. Administrative
masters and the existing period fixture retain their explicit classifications.
This file adds no Native case and implements no APPLY/UNDO command.
"""
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json

import cp7_ow04_signed_source_cases as signed

native = signed.native
ROOT = Path(__file__).resolve().parents[3]
EXPECTED = ROOT / 'docs/cp7/d17-14/ow04/consumer-command/PREDECLARED_ARITHMETIC.json'
EXPECTED_SHA256 = '437c6b2f0fe338e96a4880b6acff01e6af2f79d4f9d8ef0de29c0b4676be22ac'
INITIAL = dict(
    source=dict(gross='1000.00',net='800.00',P='1000.00',U='0.00',I='200.00',
                E='800.00',AR='0.00',available_credit='200.00',net_consumption='0.00'),
    target=dict(gross='500.00',net='500.00',P='0.00',U='0.00',I='0.00',
                E='0.00',AR='500.00'),cash='1000.00')


def expected():
    raw = EXPECTED.read_bytes()
    assert sha256(raw).hexdigest() == EXPECTED_SHA256, 'OW04_CONSUMER_FROZEN_ARITHMETIC_CHANGED'
    value = json.loads(raw)
    assert len(value['cases']) == 9 and value['independent_audit'] is False
    assert value['classification'] == 'PREIMPLEMENTATION_LITERAL_EXPECTATIONS_NOT_NATIVE_OR_IMPLEMENTED_FEATURE'
    return value


def _money(value):
    # psycopg numeric is Decimal. Refuse a float-based financial oracle.
    assert isinstance(value,(Decimal,int,str)) and not isinstance(value,bool)
    amount=Decimal(value)
    assert amount.is_finite() and amount*100==(amount*100).to_integral_value()
    return format(amount,'.2f')


def _document_ar(cur,sale,customer,account):
    """Actual document-owned GL, including inverse descendants and incoming U.

    A customer-wide balance is unsuitable here: both test invoices deliberately
    belong to the same customer. This bounded fixture has no note restatement;
    its genuine return/payment inverse descendants remain part of the sum.
    """
    return cur.execute("""with recursive originals(id)as(
      select j.id from erp.journal_entries j where
       (j.source_type='SALE'and j.source_id=%s)
       or(j.source_type='SALES_PAYMENT'and exists(select 1 from erp.sales_payments p where p.id=j.source_id and p.sale_id=%s))
       or(j.source_type='SALES_RETURN'and exists(select 1 from erp.sales_returns r where r.id=j.source_id and r.sale_id=%s))
      union select cj.journal_id from cp7_credit.component_journals cj
       join cp7_credit.component_parts q on q.id=cj.part_id join cp7_credit.recognition_components cc on cc.id=q.component_id
       join cp7_credit.recognition_plans rp on rp.id=cc.plan_id join cp7_credit.cohorts c on c.id=rp.cohort_id
       join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=%s
      union select e.journal_id from cp7_credit.consumption_events e where e.event_kind='APPLY'and e.target_sale_id=%s
     ),actual(id)as(select id from originals union select j.id from actual a join erp.journal_entries j
      on j.reversal_of_id=a.id or(j.source_type='JOURNAL_REVERSAL'and j.source_id=a.id))
     select coalesce(sum(l.debit-l.credit),0)from actual a join erp.journal_entries j on j.id=a.id
      join erp.journal_lines l on l.journal_entry_id=j.id where j.status in('POSTED','REVERSED')
      and l.customer_id=%s and l.account_id=%s""",(sale,sale,sale,sale,sale,customer,account)).fetchone()[0]


def profiles(cur,pair):
    expected()
    result={}
    for name,f in (('source',pair['source']['f']),('target',pair['target'])):
        detail=native.source.read(cur,f)['detail']
        native.b.api.admin(cur)
        sale=f['sale']
        assert not cur.execute('select exists(select 1 from cp7_note.revisions where %s::uuid '
            'in(root_sale_id,previous_sale_id,replacement_sale_id))',(sale,)).fetchone()[0], 'BOUNDED_CONSUMER_FIXTURE_HAS_NOTE_RESTATEMENT'
        gross,returned,paid=cur.execute("""select
         (select coalesce(sum(line_total),0)from erp.sales_items where sale_id=%s),
         (select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=%s and r.status='POSTED'),
         (select coalesce(sum(amount),0)from erp.sales_payments where sale_id=%s and status='POSTED')""",(sale,sale,sale)).fetchone()
        issued=cur.execute("""select coalesce(sum(q.amount),0)from cp7_credit.component_parts q
         join cp7_credit.component_journals cj on cj.part_id=q.id join erp.journal_entries j on j.id=cj.journal_id
         join cp7_credit.recognition_components cc on cc.id=q.component_id join cp7_credit.recognition_plans rp on rp.id=cc.plan_id
         join cp7_credit.cohorts c on c.id=rp.cohort_id join cp7_credit.return_families f on f.id=c.family_id
         where f.family_root_sale_id=%s and j.status in('POSTED','REVERSED')""",(sale,)).fetchone()[0]
        incoming=cur.execute("select coalesce(sum(amount),0)from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=%s",(sale,)).fetchone()[0]
        net=gross-returned;effective=paid+incoming-issued
        ar=_document_ar(cur,sale,f['customer'],pair['ar'][name])
        assert ar==net-effective, 'OW04_CONSUMER_DOCUMENT_GL_DIFFERS_FROM_P_U_I'
        profile={key:_money(value)for key,value in dict(gross=gross,net=net,P=paid,U=incoming,I=issued,E=effective,AR=ar).items()}
        if name=='source':
            used=cur.execute('select coalesce(sum(amount),0)from cp7_credit.consumption_events where cohort_id=%s',(pair['initial_result']['credit_id'],)).fetchone()[0]
            profile.update(available_credit=_money(issued-used),net_consumption=_money(used))
        assert {key:detail['financial'][key]for key in('gross_total','net_total','paid_total','open_balance')}==dict(
            gross_total=profile['gross'],net_total=profile['net'],paid_total=profile['E'],open_balance=profile['AR'])
        result[name]=profile
    native.b.api.admin(cur)
    cash_account=native.payments.bank_account(cur,pair['source']['f'])
    result['cash']=_money(cur.execute('select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=%s',(cash_account,)).fetchone()[0])
    return result


def prepare(cur,today,initial_mode='CREDIT'):
    """Actual owning setup only when called by an isolated Native case."""
    expected()
    assert initial_mode in('CREDIT','REFUND')
    source,credit,outcome,actual=signed._setup(cur,today,initial_mode)
    native.b.api.admin(cur)
    target=native.note.stock(cur,today,10,datetime.fromisoformat(source['physical']['stock']))
    target['customer']=source['f']['customer']
    target['sale_at']=source['physical']['sale']
    native.note.posted(cur,target,'5','100')
    native.b.api.admin(cur)
    ar=native.cmd.mapping(cur,'AR_CUSTOMER')
    pair=dict(source=source,target=target,credit=credit,initial_result=outcome,initial_actual=actual,
              ar=dict(source=ar,target=ar),classification='ACTUAL_FIXTURE_SETUP_WITH_SUPPLIED_CURSOR_NOT_CONSUMER_EXECUTION_PROOF')
    if initial_mode=='REFUND':
        # The initial cash event has its own explicit physical instant (13:00),
        # distinct from the source return (12:00). A later undo must name and
        # follow that actual immutable cash event, not merely the return clock.
        at=cur.execute('select physical_at from cp7_credit.initial_refund_operations where id=%s and cohort_id=%s',
                       (outcome['refund_event_id'],outcome['credit_id'])).fetchone()[0]
        pair['initial_refund_physical_at']=at.isoformat()
    # Bind the test's AR IDs to both actual original SALE journals now; later
    # observations use these saved IDs, not a changed current mapping.
    for f in(source['f'],target):
        gross=cur.execute('select sum(line_total)from erp.sales_items where sale_id=%s',(f['sale'],)).fetchone()[0]
        assert cur.execute("select count(*)from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id "
            "where j.source_type='SALE'and j.source_id=%s and j.reversal_of_id is null and l.account_id=%s "
            'and l.customer_id=%s and l.debit=%s and l.credit=0',(f['sale'],ar,f['customer'],gross)).fetchone()[0]==1
    initial=json.loads(json.dumps(INITIAL))
    if initial_mode=='REFUND':
        initial['source'].update(available_credit='0.00',net_consumption='200.00')
        initial['cash']='800.00'
    assert profiles(cur,pair)==initial
    assert native.payment_snapshot(cur,source['f']['payment'])==source['payment_before']
    assert cur.execute('select count(*)from erp.sales_payments where sale_id=%s',(target['sale'],)).fetchone()[0]==0
    cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
    return pair
