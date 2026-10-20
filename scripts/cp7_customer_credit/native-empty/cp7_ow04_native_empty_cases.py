"""Predeclared actual Native EMPTY paths; not executed and not active product.

Normal stock/sale/payment/return writers create all financial/physical facts.
Party/account/period inputs are labelled disposable administrative fixtures.
Only N04 intentionally replays the pinned pre-extension helper generation to
create a genuine legacy return, then reapplies the same candidate overlays.
N12 is an explicitly privileged private-scope fault injection, never authority.
"""
from collections import Counter
from datetime import timedelta
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path
import uuid

import cp7_ow04_native_source_fixture as nf
import cp7_ow04_initial_settlement_cases as initial

b, source, cmd, auth = nf.b, nf.source, nf.cmd, nf.auth
IDS = tuple('OW04_NATIVE_EMPTY_N%02d' % n for n in range(1, 13))
EXPECTED_SHA = '5e713283516288011b6c8ccdff4af85d3df3c077e771e36de2b2bc2c16abfd3b'


def expected():
    raw = Path(__file__).with_name('EXPECTED.json').read_bytes()
    assert sha256(raw).hexdigest() == EXPECTED_SHA, 'OW04_NATIVE_EMPTY_EXPECTED_CHANGED'
    result = json.loads(raw)
    assert tuple(x['id'].split('_', 1)[0] for x in result['cases']) == tuple('N%02d' % n for n in range(1, 13))
    return result


def counts(cur):
    b.api.admin(cur)
    return {name: nf._array(cur, 'cp7_credit.'+name, 'true', ()) for name in (
        'return_families', 'return_family_members', 'native_empty_operations',
        'native_empty_completions', 'native_empty_work', 'native_empty_source_scope',
        'cohorts', 'recognition_plans', 'consumption_events', 'financial_materializations')}


def fixture(cur, today, *, cost='10', closed=False, gross='80'):
    b.api.admin(cur)
    dates, at = nf._calendar(cur)
    nf.source.fg.ax.boundary.historical.prior.set_open_period(cur, dates['D-2'])
    product, _ = source.fg.ax.owner_only_model_product(cur,
        effective_from=at['stock']-timedelta(days=1))
    receipt = source.fg.ax.post(cur, dict(source_kind='FOUND_AT_OPNAME',
        product_id=product, location_id=source.fg.base.LOCATION, qty_pcs=10,
        physical_at=at['stock'].isoformat(), reason='Native EMPTY physical stock fixture',
        owner_unit_value=cost, owner_value_reason='Explicit isolated owner unit value'))
    b.api.admin(cur)
    f = dict(product=str(product),
        lot=str(cur.execute('select lot_id from erp.fg_unsourced_receipts_v1 where id=%s',
            (receipt['receipt_id'],)).fetchone()[0]), location=source.fg.base.LOCATION,
        customer=str(source.fg.base.create_customer(cur,'EMPTY-'+uuid.uuid4().hex[:12])),
        tag='EMPTY-'+uuid.uuid4().hex[:12], sale_at=at['sale'].isoformat(),
        bank=str(source.bc.bank_account(cur,'EMPTY-'+uuid.uuid4().hex[:8])), dates=dates, at=at)
    f['before_sale']=cmd.accounts(cur)
    f['destination']=f['location']
    if closed:
        nf.source.fg.ax.boundary.historical.prior.set_open_period(cur, dates['D2'])
    nf.note.posted(cur, f, '4', format(D(gross)/4,'.2f'))
    f['allocations']=nf.returns.read(cur,f)['page']['rows']
    assert len(f['allocations'])==1
    if closed:
        w=nf.period.read(cur,dates['D2'])
        nf.period.command(cur,'REOPEN',nf.period.intent(w,'REOPEN',str(dates['D-2'])))
    return f


def pay(cur, f, amount='30', at=None):
    b.api.admin(cur)
    ident=str(cur.execute("insert into erp.sales_payments(sale_id,payment_number,"
        "payment_date,amount,cash_account_id,payment_method,status)"
        "values(%s,%s,%s,%s,%s,'BANK_TRANSFER','DRAFT')returning id",
        (f['sale'],'EMPTY-PAY-'+uuid.uuid4().hex[:10],at or f['at']['payment'],amount,f['bank'])).fetchone()[0])
    source.native(cur,'select erp.post_sales_payment(%s)',(ident,))
    return ident


def draft_return(cur, f, refund='20', physical=None):
    b.api.admin(cur)
    ident=str(cur.execute("insert into erp.sales_returns(return_number,sale_id,customer_id,"
        "physical_at,status)values(%s,%s,%s,%s,'DRAFT')returning id",
        ('EMPTY-RET-'+uuid.uuid4().hex[:12],f['sale'],f['customer'],physical or f['at']['returned'])).fetchone()[0])
    cur.execute("insert into erp.sales_return_items(return_id,product_id,lot_id,location_id,"
        "qty_pcs,unit_hpp_snapshot,refund_amount,quality_grade,sale_stock_allocation_id)"
        "values(%s,%s,%s,%s,1,0,%s,'GRADE_A',%s)",
        (ident,f['product'],f['lot'],f['location'],refund,f['allocations'][0]['allocation_id']))
    return ident


def native(cur, sql, args, null_human=False):
    if not null_human:
        return source.native(cur, sql, args)
    b.api.admin(cur)
    cur.execute("select set_config('request.jwt.claim.sub','',true)")
    cur.execute("select set_config('request.jwt.claims','{}',true)")
    assert cur.execute('select auth.uid()is null').fetchone()[0]
    result = cur.execute(sql,args).fetchone()[0]
    b.api.admin(cur)
    return result


def post(cur, ident, null_human=False):
    return native(cur,'select erp.post_sales_return(%s)',(ident,),null_human)


def registered(cur, f, ident, ordinal=1):
    b.api.admin(cur)
    row=cur.execute('select to_jsonb(o),to_jsonb(rf),to_jsonb(m)'
        'from cp7_credit.native_empty_operations o join cp7_credit.return_families rf on rf.id=o.family_id '
        'join cp7_credit.return_family_members m on m.return_id=o.source_return_id '
        'where o.source_return_id=%s',(ident,)).fetchone()
    assert row is not None
    op,family,member=row
    assert op['family_ordinal']==family['family_ordinal']==ordinal
    assert family['first_return_id']==member['return_id']==ident
    assert family['request_id']is None and member['request_id']is None
    assert op['actual_kernel']['net_current_k']=='0.00'
    assert op['actual_kernel']['has_recognition_effect']is False
    assert not cur.execute('select exists(select 1 from cp7_credit.cohorts where family_id=%s)',
        (family['id'],)).fetchone()[0]
    cur.execute('select cp7_credit.assert_native_empty_closed_v1(%s)',(op['operation_id'],))
    assert cur.execute('select count(*)from cp7_credit.native_empty_work').fetchone()[0]==0
    assert cur.execute('select count(*)from cp7_credit.native_empty_source_scope').fetchone()[0]==0
    return op


def cases(cur, today, *, before_helpers, reapply_overlay):
    expected()  # Frozen before implementation: never infer expectations from output.
    def isolated_case(operation):
        with nf.isolated(cur):
            result=operation()
            b.api.admin(cur)
            # Factual closure must survive the loss of live inspection claims.
            cur.execute("select set_config('request.jwt.claims','{}',true)")
            cur.execute("select set_config('request.jwt.claim.sub','',true)")
            cur.execute('set constraints all immediate')
            return dict(status='PASS',actual_native=True,deferred_constraints_forced=True,
                production_go=False,**result)

    def first(null_human=False):
        f=fixture(cur,today);pay(cur,f);r=draft_return(cur,f);post(cur,r,null_human)
        o=registered(cur,f,r)
        if null_human:
            assert o['principal']['auth_uid']is None and o['principal']['kind']=='DATABASE_SESSION'
        detail=source.read(cur,f)['detail']; amounts=source.numbers(detail)
        assert amounts==dict(gross_total=D(80),return_total=D(20),net_total=D(60),paid_total=D(30),open_balance=D(30))
        assert detail['status']=='PARTIAL_PAID' and detail['returned_qty']=='1'
        bank_coa=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(f['bank'],)).fetchone()[0])
        assert cmd.delta(f['before_sale'],cmd.accounts(cur))=={
            cmd.mapping(cur,'AR_CUSTOMER'):D(30),cmd.mapping(cur,'SALES_REVENUE'):D(-60),
            cmd.mapping(cur,'FG_INVENTORY'):D(-30),cmd.mapping(cur,'COGS'):D(30),bank_coa:D(30)}
        assert cur.execute('select cached_qty_pcs from erp.fg_lots where id=%s',(f['lot'],)).fetchone()[0]==7
        return dict(net=str(amounts['net_total']),raw_paid=str(amounts['paid_total']),receivable=str(amounts['open_balance']),ordinal=1,
            actual_null_human=null_human)

    def append():
        f=fixture(cur,today);one=draft_return(cur,f);post(cur,one);registered(cur,f,one)
        two=draft_return(cur,f);post(cur,two);registered(cur,f,two,2)
        assert source.read(cur,f)['detail']['financial']['open_balance']=='40.00'
        mixed=fixture(cur,today)
        payload,version=nf.returns.payload(cur,mixed)
        payload['physical_at']=mixed['at']['returned'].isoformat()
        ordinary=cmd.command(cur,'RETURN',payload,version)['return_id']
        old_family=nf._array(cur,'cp7_credit.return_families','first_return_id=%s',(ordinary,))
        old_member=nf._array(cur,'cp7_credit.return_family_members','return_id=%s',(ordinary,))
        assert len(old_family['document'])==len(old_member['document'])==1
        assert old_family['document'][0]['family_ordinal']==1
        assert old_family['document'][0]['request_id'] is not None
        added=draft_return(cur,mixed);post(cur,added);registered(cur,mixed,added,2)
        assert nf._array(cur,'cp7_credit.return_families','first_return_id=%s',(ordinary,))==old_family
        assert nf._array(cur,'cp7_credit.return_family_members','return_id=%s',(ordinary,))==old_member
        assert source.read(cur,mixed)['detail']['financial']['open_balance']=='40.00'
        return dict(actual_native_families=2,ordinals=[1,2],receivable='40.00',cp7_then_native_append=True,prior_cp7_family_unchanged=True)

    def legacy():
        f=fixture(cur,today)
        # Explicit upgrade fixture: the real previous helper generation writes
        # a completed return; no financial row or ordinal is fabricated.
        for definition in before_helpers:
            cur.execute(definition,prepare=False)
        old=draft_return(cur,f);post(cur,old)
        reapply_overlay(cur)
        new=draft_return(cur,f);before=(b.boundary.snapshot(cur),counts(cur))
        auth.refused(cur,lambda:post(cur,new),'CP7_NATIVE_EMPTY_LEGACY_ORDER_OR_SOURCE_UNQUALIFIED')
        assert (b.boundary.snapshot(cur),counts(cur))==before
        assert not cur.execute('select exists(select 1 from cp7_credit.return_family_members where return_id=%s)',(old,)).fetchone()[0]
        return dict(actual_pre_extension_native_return=True,unknown_order_refused=True,no_backfill=True)

    def zero(hpp_only=False):
        f=fixture(cur,today,cost='10'if hpp_only else'0',closed=hpp_only)
        before=cmd.accounts(cur)
        originals={str(j):nf.journal(cur,str(j))for (j,)in cur.execute("select id from erp.journal_entries where source_type='SALE'and source_id=%s",(f['sale'],)).fetchall()}
        assert len(originals)==1
        r=draft_return(cur,f,'0');post(cur,r);o=registered(cur,f,r)
        if hpp_only:
            assert o['actual_fact']['financial_state']=='JOURNAL'
            j=o['actual_original_journal']['journal']
            assert j['economic_date']==str(f['dates']['D2']) and j['transaction_date']==str(f['dates']['D3'])
            assert cur.execute('select erp.resolve_accounting_transaction_date(%s)',(f['dates']['D2'],)).fetchone()[0]==f['dates']['D2']
            fg, cogs=cmd.mapping(cur,'FG_INVENTORY'),cmd.mapping(cur,'COGS')
            assert cmd.delta(before,cmd.accounts(cur))=={fg:D(10),cogs:D(-10)}
            lines=cur.execute('select account_id::text,debit,credit from erp.journal_lines where journal_entry_id=%s',(o['actual_fact']['source_journal_id'],)).fetchall()
            assert Counter(lines)==Counter([(fg,D(10),D(0)),(cogs,D(0),D(10))])
        else:
            assert o['actual_fact']['financial_state']=='NO_JOURNAL'
            assert o['actual_fact']['source_journal_id']is None and o['actual_original_journal']is None
            assert not cur.execute("select exists(select 1 from erp.journal_entries where source_type='SALES_RETURN'and source_id=%s)",(r,)).fetchone()[0]
            assert cmd.accounts(cur)==before
        assert cur.execute('select cached_qty_pcs from erp.fg_lots where id=%s',(f['lot'],)).fetchone()[0]==7
        assert all(nf.journal(cur,ident)==snapshot for ident,snapshot in originals.items())
        return dict(zero_refund=True,hpp_only=hpp_only,true_no_journal=not hpp_only)

    def temporal():
        f=fixture(cur,today,gross='1000');p=pay(cur,f,'500',f['at']['sale']+timedelta(hours=1))
        pay(cur,f,'400',f['at']['payment'])
        source.native(cur,'select erp.reverse_sales_payment(%s,%s)',(p,'Native EMPTY temporal original inverse'))
        physical=f['at']['payment']+timedelta(hours=1)
        r=draft_return(cur,f,'200',physical);before=(b.boundary.snapshot(cur),counts(cur))
        events=cur.execute('select cp7_credit.initial_base_events_v1(%s)',(f['sale'],)).fetchone()[0]
        actual=cur.execute('select ow04_pure_kernel.recognition_plan_v1(%s,%s)',
            (json.dumps(events),json.dumps([dict(id='declared-hypothetical-return',kind='NET',amount='-200.00',
                economic_date=str(physical.date()),transaction_date=str(physical.date()),source_sha256='a'*64)]))).fetchone()[0]
        assert actual['net_current_k']=='0.00'and actual['has_recognition_effect']is True
        assert sorted(x['amount']for x in actual['components'])==['-100.00','100.00']
        auth.refused(cur,lambda:post(cur,r),'CP7_NATIVE_EMPTY_EXPLICIT_RECOGNITION_REVIEW_REQUIRED')
        assert (b.boundary.snapshot(cur),counts(cur))==before
        return dict(current_k='0.00',signed_components=['100.00','-100.00'],native_refused_atomically=True)

    def paid():
        f=fixture(cur,today);pay(cur,f,'80');r=draft_return(cur,f);before=(b.boundary.snapshot(cur),counts(cur))
        auth.refused(cur,lambda:post(cur,r),'membuat pembayaran customer melebihi nilai penjualan tersisa')
        assert (b.boundary.snapshot(cur),counts(cur))==before
        return dict(original_paid_guard_preserved=True,atomic_refusal=True)

    def replay():
        f=fixture(cur,today);r=draft_return(cur,f);post(cur,r);registered(cur,f,r)
        before=(b.boundary.snapshot(cur),counts(cur))
        auth.refused(cur,lambda:post(cur,r),'Sales return must be DRAFT')
        assert (b.boundary.snapshot(cur),counts(cur))==before
        return dict(original_native_repeat_refused=True,no_duplicate_family=True)

    def inverses():
        operation_ids=[]
        for null_human in (False,True):
            f=fixture(cur,today);p=pay(cur,f);r=draft_return(cur,f);post(cur,r,null_human);o=registered(cur,f,r)
            if null_human:assert o['principal']['auth_uid']is None and o['principal']['kind']=='DATABASE_SESSION'
            for sql,args in [('select erp.reverse_sales_payment(%s,%s)',(p,'Native EMPTY payment inverse')),
                ('select erp.reverse_sales_return(%s,%s)',(r,'Native EMPTY return inverse')),
                ('select erp.reverse_sale(%s,%s)',(f['sale'],'Native EMPTY sale inverse'))]:
                native(cur,sql,args,null_human)
                registered(cur,f,r)
            assert cmd.accounts(cur)==f['before_sale']
            assert cur.execute('select cached_qty_pcs from erp.fg_lots where id=%s',(f['lot'],)).fetchone()[0]==10
            operation_ids.append(o['operation_id'])
        return dict(native_payment_return_sale_inverses=True,neutral_gl=True,physical_stock10=True,
            null_human_inverses=True,original_operation_ids=operation_ids)

    def credit():
        gold=next(x for x in initial.expected()['cases']if x['id']=='OW04_INITIAL_1000_OPEN_CREDIT')
        x=nf.prepared(cur,today,gold['paid'],gold['profile']);master=initial._credit_master(cur)
        query=initial._input(x,gold,master);quote=nf.call_quote(cur,query)
        outcome=initial._settle(cur,initial._envelope(query,quote),uuid.uuid4())
        f=x['f'];before=(b.boundary.snapshot(cur),counts(cur))
        auth.refused(cur,lambda:source.native(cur,'select erp.reverse_sales_payment(%s,%s)',
            (f['payment'],'Native EMPTY must not bypass retained credit')),
            'CP7_NATIVE_EMPTY_RECOGNIZED_OR_CORRECTED_SOURCE_UNIMPLEMENTED')
        assert (b.boundary.snapshot(cur),counts(cur))==before
        return dict(real_credit_id=outcome['credit_id'],retained_credit_native_mutation_refused=True)

    def closure():
        f=fixture(cur,today);r=draft_return(cur,f);post(cur,r);o=registered(cur,f,r)
        before=(b.boundary.snapshot(cur),counts(cur))
        def leak():
            # Privileged fault injection in the disposable private registry.
            # It is not an admission path or a synthetic financial posting.
            cur.execute("insert into cp7_credit.native_empty_work(operation_id,backend_pid,transaction_id,source_return_id,source_sale_id,"
                "principal,principal_sha256,source_snapshot,preserved_source,before_events,draft_manifest,prior_causal,period_snapshot,"
                "projected_events,projected_kernel,phase,family_id,materialization_id)"
                "select operation_id,pg_backend_pid(),txid_current(),source_return_id,source_sale_id,principal,principal_sha256,"
                "source_snapshot,preserved_source,before_events,draft_manifest,prior_causal,period_snapshot,projected_events,projected_kernel,"
                "'REGISTERED',family_id,materialization_id from cp7_credit.native_empty_operations where operation_id=%s",(o['operation_id'],))
            cur.execute("select set_config('request.jwt.claims','{}',true)")
            cur.execute('set constraints all immediate')
        auth.refused(cur,leak,'CP7_NATIVE_EMPTY_PRIVATE_SCOPE_LEAK')
        assert (b.boundary.snapshot(cur),counts(cur))==before
        return dict(privileged_fault_injection_labelled=True,deferred_scope_leak_refused=True,
            closure_after_claims_removed=True,no_partial_effect=True)

    ops=[first,lambda:first(True),append,legacy,zero,lambda:zero(True),temporal,paid,replay,inverses,credit,closure]
    return [(name,lambda operation=operation:isolated_case(operation))for name,operation in zip(IDS,ops)]
