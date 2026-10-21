"""Direct Native returns against retained, literal fractional HPP vectors.

No connection/install on import. Real opening/import, sale and payment writers
prepare each source. Only the Native return DRAFT is administrative input;
post_sales_return itself writes all stock/HPP/journal/family facts. These are
not browser or end-user entry proofs. The thirteen earlier fractional expected
vectors and their source manifest remain unchanged.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import uuid

import cp7_ow04_fractional_hpp_cases as frac
import cp7_ow04_native_empty_cases as empty

nf, b, source, auth = frac.nf, frac.b, frac.source, frac.auth
EXPECTED_SHA = '6bd414a898814d15e89e68d28022c5ee0fff99b6c92808184ea8fd7f22e4d7f3'


def expected():
    raw=Path(__file__).with_name('NATIVE_EXPECTED.json').read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_SHA, 'NATIVE_HPP_FROZEN_EXPECTED_CHANGED'
    value=json.loads(raw)
    assert len(value['cases'])==14
    assert len({v['id'] for v in value['cases']})==14
    return value


def _gold(row):
    original=next(v for v in frac.expected()['cases'] if v['id']==row['source_case_id'])
    value=deepcopy(original)
    value.update(return_amount='0.00',mode=None)
    for key in ('before','after','delta','owned_before','owned_after'):
        assert value[key]==row[key], ('NATIVE_HPP_LITERAL_VECTOR_CHANGED',key)
    return value


def _draft(cur,f):
    b.api.admin(cur)
    ident=str(cur.execute("insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at,status)"
        "values(%s,%s,%s,%s,'DRAFT')returning id",
        ('NATIVE-HPP-'+uuid.uuid4().hex[:15],f['sale'],f['customer'],f['at']['returned'])).fetchone()[0])
    for allocation in f['allocations']:
        cur.execute('insert into erp.sales_return_items(return_id,product_id,lot_id,location_id,qty_pcs,'
            'unit_hpp_snapshot,refund_amount,quality_grade,sale_stock_allocation_id)'
            "values(%s,%s,%s,%s,1,0,0,'GRADE_A',%s)",
            (ident,allocation['product_id'],allocation['lot_id'],f['location'],allocation['allocation_id']))
    return ident


def _actual(cur,f,gold,ident,before):
    b.api.admin(cur)
    operation=empty.registered(cur,f,ident,int(gold['family_ordinal']))
    assert operation['hpp_projection']['hpp_amount']==gold['hpp_amount']
    assert [g['after_target'] for g in operation['hpp_projection']['groups']]
    journals=cur.execute("select id::text,economic_date,transaction_date from erp.journal_entries "
        "where source_type='SALES_RETURN'and source_id=%s",(ident,)).fetchall()
    pair=gold.get('return_pair',['D2','D2'])
    assert len(journals)==1
    journal_id,economic,book=journals[0]
    assert (economic,book)==tuple(f['dates'][key] for key in pair)
    lines=cur.execute('select account_id::text,debit,credit,customer_id::text,po_id::text,product_id::text,'
        'vendor_id::text,contractor_id::text from erp.journal_lines where journal_entry_id=%s',(journal_id,)).fetchall()
    assert Counter(lines)==frac._wanted_journal(cur,f,gold), ('NATIVE_HPP_EXACT_LINES_CHANGED',lines,gold)
    assert {str(v[0]) for v in cur.execute('select id from erp.journal_entries').fetchall()}-set(before['journals'])=={journal_id}
    frac._vectors(cur,f,gold['after'])
    frac._owned(cur,f,gold['owned_after'])
    frac._assert_preserved(cur,f,before)
    movements=cur.execute('select i.sale_stock_allocation_id::text,i.lot_id::text,i.location_id::text,'
        'i.qty_pcs,i.refund_amount,m.qty_signed,m.physical_at,m.unit_hpp_snapshot=i.unit_hpp_snapshot '
        'from erp.sales_return_items i join erp.fg_stock_movements m '
        "on m.source_type='SALES_RETURN_ITEM'and m.source_id=i.id where i.return_id=%s",(ident,)).fetchall()
    assert len(movements)==len(f['allocations'])
    assert {v[0] for v in movements}=={a['allocation_id'] for a in f['allocations']}
    assert all(v[2]==str(f['location']) and v[3:6]==(1,0,1)
        and v[6]==f['at']['returned'] and v[7] is True for v in movements)
    assert cur.execute('select status::text from erp.sales_headers where id=%s',(f['sale'],)).fetchone()==('PAID',)
    for name in ('initial_return_work','return_native_scope','return_command_scope','posting_scope',
                 'native_empty_work','native_empty_source_scope','opening_return_hpp_work_v1'):
        assert cur.execute('select count(*)from cp7_credit.'+name).fetchone()==(0,)
    cur.execute('set constraints all immediate')
    snapshot=frac._observe(cur,f)
    auth.refused(cur,lambda:empty.post(cur,ident),'Sales return must be DRAFT')
    assert frac._observe(cur,f)==snapshot, 'NATIVE_HPP_REPOST_LEFT_EFFECT'
    return dict(operation=operation,native_journal=nf.journal(cur,journal_id),
        exact_pair=[str(economic),str(book)],full_vectors_and_prior_facts_unchanged=True,
        repost_refused_without_second_effect=True,deferred_constraints_forced=True)


def _run(cur,today,row):
    with nf.isolated(cur):
        gold=_gold(row)
        f=frac._fixture(cur,today,gold)
        frac._vectors(cur,f,gold['before'])
        frac._owned(cur,f,gold['owned_before'])
        ident=_draft(cur,f)
        before=frac._preserved(cur,f)
        if row.get('diagnostic_failure'):
            # Disposable fault injection reaches the diagnostic only AFTER
            # the actual Native journal; its failure must undo every effect.
            with nf.isolated(cur):
                cur.execute("create function pg_temp.native_hpp_fail()returns trigger language plpgsql as $$begin "
                    "if not exists(select 1 from erp.journal_entries j where j.source_type='SALES_RETURN'and j.source_id='"+ident+"'::uuid)"
                    "then raise exception 'NATIVE_HPP_TEST_DIAGNOSTIC_TOO_EARLY';end if;"
                    "raise exception 'NATIVE_HPP_TEST_AFTER_JOURNAL_DIAGNOSTIC_FAILURE';end $$",prepare=False)
                cur.execute('create trigger native_hpp_fail before update on erp.opening_lot_hpp_gl_state '
                    'for each row execute function pg_temp.native_hpp_fail()',prepare=False)
                snapshot=frac._observe(cur,f)
                auth.refused(cur,lambda:empty.post(cur,ident),'NATIVE_HPP_TEST_AFTER_JOURNAL_DIAGNOSTIC_FAILURE')
                assert frac._observe(cur,f)==snapshot, 'NATIVE_HPP_ATOMIC_FAILURE_LEFT_RESIDUE'
        empty.post(cur,ident,null_human=row.get('null_human',False))
        result=_actual(cur,f,gold,ident,before)
        if row.get('null_human'):
            assert result['operation']['principal']['auth_uid'] is None
            assert result['operation']['principal']['kind']=='DATABASE_SESSION'
        return dict(status='PASS',actual_native=True,source_case_id=row['source_case_id'],
            null_human=row.get('null_human',False),diagnostic_failure_atomic=row.get('diagnostic_failure',False),
            qualification_only=True,production_go=False,**result)


IDS=tuple(v['id'] for v in json.loads(Path(__file__).with_name('NATIVE_EXPECTED.json').read_text())['cases'])


def cases(cur,today):
    return [(row['id'],lambda row=row:_run(cur,today,row)) for row in expected()['cases']]
