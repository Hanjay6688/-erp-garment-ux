"""Explicit qualification-only fixture API; never a product/Native substitute.

All writes below call the installed owning Native/public writer. Only a new
DRAFT payroll header is an administrative fixture. Unknown attendance cells
are refused, never synthesized as ABSENT/OFF. Pass the private core explicitly;
no module in the frozen parent is modified or globally monkeypatched.
"""
from datetime import timedelta
from collections import Counter
from decimal import Decimal as D
from hashlib import sha256
import json
import uuid

API = 'cp7.s03.lawful-fixture.v1'
FG_FIELDS = frozenset(('id','product_id','lot_id','location_id','quality_grade',
    'movement_type','qty_signed','unit_hpp_snapshot','customer_id','source_type',
    'source_id','physical_at','system_created_at','created_by','reversal_of_id',
    'notes','book_order'))
CACHE_TYPES = frozenset(('QC_GOOD','REWORK_IN'))


def emit(evidence, key, value):
    if evidence is not None:
        evidence.setdefault('lawful_fixture_successor', {}).setdefault(key, []).append(value)
    return value


def source_facts(cur, source, *, core):
    f = core.f
    f.admin(cur)
    return dict(source_binding=core.source_hash(cur, source),
        original_accrual=core.original_accrual(cur, source),
        payroll=f.one(cur, 'select to_jsonb(p)from erp.payroll_settlements p where id=%s', (source['payroll'],)),
        items=f.one(cur, "select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]'::jsonb)from erp.payroll_attendance_items i where payroll_id=%s", (source['payroll'],)),
        attendance=f.one(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]'::jsonb)from erp.attendance_records a where a.id in(select attendance_record_id from erp.payroll_attendance_items where payroll_id=%s)", (source['payroll'],)))


def known_worker(cur, source, output, *, core):
    """The exact P1 worker, not a newly created parallel employment period."""
    f = core.f
    f.admin(cur)
    workers = [str(row[0]) for row in cur.execute(
        'select distinct worker_id from erp.payroll_attendance_items where payroll_id=%s order by worker_id',
        (source['payroll'],)).fetchall()]
    if len(workers) != 1:
        raise ValueError('S03_LAWFUL_ONE_KNOWN_P1_WORKER_REQUIRED:' + repr(workers))
    eligible = [str(row[0]) for row in cur.execute("""select w.id from erp.contractor_workers w
        where w.contractor_id=%s and w.pay_scheme in('DAILY','HYBRID')
          and erp.worker_is_employed_on(w.id,%s) order by w.id""",
        (source['contractor'], output)).fetchall()]
    if eligible != workers:
        raise ValueError('S03_LAWFUL_UNKNOWN_ELIGIBLE_WORKER_REFUSED:' + repr(dict(known=workers, eligible=eligible)))
    return workers[0], eligible


def earned(cur, source, output, amount=D('20.02'), *, core, evidence=None, approve=True):
    """Reuse one exact P1 worker with a Native future-effective rate and PRESENT.

    Exports a new explicit API for Reader3/browser fixtures. No existing helper
    is overwritten. The P1 source/accrual/payroll/attendance snapshots must stay
    identical, including through Native P2 approval.
    """
    amount = D(str(amount))
    if output <= source['day'] or amount <= 0 or amount != amount.quantize(D('.01')):
        raise ValueError('S03_LAWFUL_LATER_EXACT_DAILY_CENTS_REQUIRED')
    f = core.f
    before = source_facts(cur, source, core=core)
    worker, eligible = known_worker(cur, source, output, core=core)
    row = f.one(cur, 'select to_jsonb(w)from erp.contractor_workers w where id=%s', (worker,))
    if row['contractor_id'] != source['contractor'] or row['pay_scheme'] not in ('DAILY','HYBRID'):
        raise ValueError('S03_LAWFUL_P1_WORKER_CONTRACTOR_MISMATCH')
    # Fresh version, real writer; no direct historical rate/worker changes.
    rate_request = str(uuid.uuid4())
    rate = f.native(cur, 'select erp.set_worker_daily_rate_v1(%s,%s,%s,%s,%s,%s)',
        (worker, amount, output, f.REASON, rate_request, row['row_version']))
    assert (str(rate['worker_id']), D(str(rate['daily_rate'])), rate['effective_from']) == (worker, amount, str(output)), rate
    assert source_facts(cur, source, core=core) == before, 'S03_LAWFUL_RATE_STALES_ORIGINAL_P1_SOURCE'
    # Enumerate again after the Native rate wait; do not cache employment truth.
    assert known_worker(cur, source, output, core=core) == (worker, eligible)
    c = f.hp.cp17(); tag = 'S03-P2-' + uuid.uuid4().hex[:12]
    f.admin(cur)
    payroll = str(f.one(cur, 'insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,payment_date)values(%s,%s,%s,%s,%s)returning id',
        (tag, source['contractor'], output, output, output)))
    attendance = dict(contractor_id=source['contractor'], period_number=tag+'-ATT',
        period_start=str(output), period_end=str(output), pay_date=str(output), reason=f.REASON,
        attendance=[dict(worker_id=worker, attendance_date=str(output), status='PRESENT')])
    ap = c.s.native(cur, 'select public.erp_save_attendance_period_v1(%s::jsonb,%s,null,false)',
        (json.dumps(attendance), uuid.uuid4()))
    c.s.native(cur, 'select public.erp_post_attendance_period_v1(%s,%s,%s,%s)',
        (c.bc.awp.find(ap,'period_id'), f.REASON, uuid.uuid4(), c.bc.awp.find(ap,'row_version')))
    c.s.act(cur, 'PREPARE', c.s.doc(cur,payroll))
    if approve:
        c.s.act(cur, 'APPROVE', c.s.doc(cur,payroll))
    f.admin(cur)
    assert D(str(c.s.doc(cur,payroll)['attendance_total'])) == amount
    actual_items = f.one(cur, "select jsonb_agg(to_jsonb(i)order by i.id)from erp.payroll_attendance_items i where payroll_id=%s", (payroll,))
    assert len(actual_items) == 1 and actual_items[0]['worker_id'] == worker, actual_items
    assert D(str(actual_items[0]['amount'])) == amount and D(str(actual_items[0]['daily_rate_snapshot'])) == amount
    assert source_facts(cur, source, core=core) == before, 'S03_LAWFUL_P2_CHANGED_ORIGINAL_P1_SOURCE'
    emit(evidence, 'P2_known_worker', dict(API=API, contractor=source['contractor'],
        source_payroll=source['payroll'], source_period=str(source['day']), output_period=str(output),
        known_worker=worker, exact_eligible_worker_ids=eligible, explicit_status='PRESENT',
        Native_rate_request=rate_request, Native_rate_receipt=rate, amount=str(amount),
        payroll=payroll, P1_facts_before=before, P1_facts_after=source_facts(cur,source,core=core),
        actual_P2_attendance_items=actual_items, unknown_cells_synthesized=False))
    return payroll


def reopen_source(cur, source, *, core, evidence=None):
    """Retain the legitimate closed REVERSE negative, then use OWNER REOPEN."""
    f = core.f
    f.refused(cur, lambda: f.save(cur, source['owner'], 'REVERSE', f.body(source['day'])),
        'CP7_S03_PERIOD_CLOSED')
    original = source_facts(cur, source, core=core)
    # Use the current date as review day; it does not change economic/book dates.
    f.admin(cur)
    today = f.one(cur, "select (statement_timestamp()at time zone 'Asia/Jakarta')::date")
    before_filings = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]'::jsonb)from erp.accounting_close_filings_v1 a")
    f.hp.auth.actor(cur, source['owner'])
    try:
        review = f.one(cur, 'select public.erp_cp7_get_period_control_v1(%s)', (today,))
        closed = review['control']['closed_through']
        target = source['day'] - timedelta(days=1)
        assert closed is not None and str(target) < closed, (target,closed)
        request = str(uuid.uuid4())
        payload = dict(through=str(target), review_through=review['through'],
            review_token=review['review_token'], reason=f.REASON+'; buka kembali sumber sebelum inverse pilihan')
        receipt = f.one(cur, 'select public.erp_cp7_save_period_control_v1(%s,%s::jsonb,%s::uuid)',
            ('REOPEN', json.dumps(payload), request))
    finally:
        if cur.connection.info.transaction_status.name != 'INERROR':
            f.admin(cur)
    assert receipt['action'] == 'REOPEN' and receipt['closed_through'] == str(target) and receipt['request_id'] == request, receipt
    assert source_facts(cur,source,core=core) == original
    assert f.one(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]'::jsonb)from erp.accounting_close_filings_v1 a") == before_filings
    emit(evidence, 'OWNER_REOPEN', dict(API=API, source_period=str(source['day']),
        closed_REVERSE_full_census_negative=True, review=review, payload=payload, receipt=receipt,
        new_request=request, immutable_filings=before_filings, original_P1_facts_unchanged=True,
        administrative_control_reset_used=False))
    return receipt


def finished_facts(cur, fixture, *, core):
    """Raw direct ERP facts, not facade financial figures or expected results."""
    f = core.f; f.admin(cur)
    fg = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(m)order by m.id),'[]'::jsonb)from erp.fg_stock_movements m where lot_id=%s", (fixture['lot'],))
    history = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(h)order by h.lot_id,h.id),'[]'::jsonb)from erp.hpp_versions h where h.lot_id in(select id from erp.fg_lots where po_id=%s and lot_origin='PRODUCTION')", (fixture['po'],))
    components = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(c)order by c.id),'[]'::jsonb)from erp.hpp_version_components c where c.hpp_version_id in(select h.id from erp.hpp_versions h where h.lot_id in(select id from erp.fg_lots where po_id=%s and lot_origin='PRODUCTION'))", (fixture['po'],))
    hpp = [r for r in history if r['is_current']]
    headers = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(j)order by j.id),'[]'::jsonb)from erp.journal_entries j where j.id in(select journal_entry_id from erp.journal_lines where po_id=%s)", (fixture['po'],))
    lines = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]'::jsonb)from erp.journal_lines l where l.journal_entry_id in(select journal_entry_id from erp.journal_lines where po_id=%s)", (fixture['po'],))
    gl = {key:D(str(f.one(cur, 'select coalesce(sum(debit-credit),0)from erp.journal_lines where po_id=%s and account_id=erp.account_id(%s)',
        (fixture['po'], key)))) for key in ('WIP','FG_INVENTORY','COGS')}
    return dict(FG=fg,current_HPP=hpp,HPP_history=history,HPP_components=components,journal_headers=headers,journal_lines=lines,GL=gl)


def hpp_money(facts):
    rows = facts['current_HPP']
    assert rows, 'S03_LAWFUL_CURRENT_NATIVE_HPP_REQUIRED'
    return sum(D(str(r['total_cost'])) for r in rows), sum(int(r['qty_basis_pcs']) for r in rows)


def assert_valuation(before, after, own_cost, *, lot, baseline_cost, before_gl, after_gl):
    """Only Native receiving valuation caches may change; all other facts exact."""
    old = {r['id']:r for r in before['FG']}; new = {r['id']:r for r in after['FG']}
    assert len(old) == len(before['FG']) and len(new) == len(after['FG']) and old.keys() == new.keys(), 'S03_LAWFUL_FG_ROWSET_CHANGED'
    hpp = {r['lot_id']:r for r in after['current_HPP']}
    original_hpp = {r['lot_id']:r for r in before['current_HPP']}
    assert hpp.keys() == original_hpp.keys(), 'S03_LAWFUL_HPP_LOTSET_CHANGED'
    assert len(hpp) == 1 and hpp_money(before)[1] == 10, 'S03_LAWFUL_RETAINED_ONE_PRODUCTION_LOT_TEN_REQUIRED'
    assert hpp_money(before)[0] == D(str(baseline_cost))
    assert hpp_money(after) == (hpp_money(before)[0]+own_cost, hpp_money(before)[1])
    assert before['GL'] == before_gl and after['GL'] == after_gl
    for key, row in old.items():
        current = new[key]
        assert set(row) == set(current) == FG_FIELDS, 'S03_LAWFUL_UNKNOWN_FG_FIELDS_REFUSED'
        if row['movement_type'] in CACHE_TYPES:
            assert {k:v for k,v in row.items() if k!='unit_hpp_snapshot'} == {k:v for k,v in current.items() if k!='unit_hpp_snapshot'}, ('S03_LAWFUL_PHYSICAL_16_CHANGED',key)
            assert D(str(row['unit_hpp_snapshot'])) == D(str(original_hpp[row['lot_id']]['hpp_per_pcs']))
            assert D(str(current['unit_hpp_snapshot'])) == D(str(hpp[row['lot_id']]['hpp_per_pcs'])), ('S03_LAWFUL_CACHE_NOT_NATIVE_HPP',key)
            assert D(str(hpp[row['lot_id']]['total_cost'])) == D(str(original_hpp[row['lot_id']]['total_cost']))+own_cost, 'S03_LAWFUL_OWN_COST_NOT_EXACT_LOT_ALLOCATION'
        else:
            assert current == row, ('S03_LAWFUL_NON_RECEIPT_ROW_CHANGED',key)
    assert any(r['movement_type']=='SALE' and int(r['qty_signed'])==-4 for r in old.values()), 'S03_LAWFUL_WHOLE_SALE_FOUR_REQUIRED'
    assert lot in hpp
    immutable_history(before,after)
    # Explicitly retain the old false predicate as a negative/provenance fact.
    old_fullrow_predicate = after['FG'] == before['FG']
    assert old_fullrow_predicate is False, 'S03_LAWFUL_NATIVE_CACHE_COUNTER_NOT_EXERCISED'
    return dict(old_full_row_predicate=old_fullrow_predicate, Native_receipt_cache_only=True,
        all_16_non_cost_fields_equal=True, entire_SALE_rows_equal=True, rowsets_equal=True,
        direct_Native_HPP_exact=True, original_money_oracles_unchanged=True)


def immutable_history(before,after,*,reversed_journal_ids=frozenset()):
    """All baseline facts survive; only Native HPP current-pointer retires."""
    for name in ('journal_headers','journal_lines','HPP_components'):
        current={r['id']:r for r in after[name]}
        assert len(current)==len(after[name]),('S03_LAWFUL_DUPLICATE_HISTORY_ROW',name)
        for row in before[name]:
            expected=row
            if name=='journal_headers'and row['id']in reversed_journal_ids:
                assert row['status']=='POSTED','S03_LAWFUL_ONLY_KNOWN_POSTED_POOL_CAN_REVERSE'
                expected=dict(row,status='REVERSED')
            assert current.get(row['id'])==expected,('S03_LAWFUL_BASELINE_HISTORY_CHANGED',name,row['id'])
    current={r['id']:r for r in after['HPP_history']}
    for row in before['HPP_history']:
        actual=current.get(row['id']);assert actual is not None,'S03_LAWFUL_HPP_HISTORY_REMOVED'
        assert {k:v for k,v in actual.items()if k!='is_current'}=={k:v for k,v in row.items()if k!='is_current'}, 'S03_LAWFUL_HPP_HISTORY_FACT_CHANGED'
        assert actual['is_current'] is False, 'S03_LAWFUL_OLD_HPP_CURRENT_POINTER_NOT_RETIRED'


def observe_valuation(cur, fixture, before, own_cost, *, core, baseline_cost, before_gl, after_gl, evidence):
    after = finished_facts(cur,fixture,core=core)
    proof = assert_valuation(before,after,own_cost,lot=fixture['lot'],baseline_cost=baseline_cost,
        before_gl=before_gl,after_gl=after_gl)
    emit(evidence,'Native_finished_valuation',dict(before=before,after_allocation=after,proof=proof,
        own_cost=str(own_cost), SHA256_json=sha256(json.dumps(after,sort_keys=True,default=str).encode()).hexdigest()))
    return after


def assert_cancelled(cur, fixture, before, *, after_allocation, core, evidence, made, cancelled, oracle):
    after = finished_facts(cur,fixture,core=core)
    assert after['FG'] == before['FG'], 'S03_LAWFUL_CANCEL_FULL_FG_ROWS_NOT_EXACT'
    assert hpp_money(after) == hpp_money(before) and after['GL'] == before['GL'], 'S03_LAWFUL_CANCEL_NATIVE_HPP_GL_NOT_BASELINE'
    immutable_history(before,after)
    f=core.f
    original_id=oracle['journal']['id'];inverse_id=cancelled['native_result']['reversal_journal_entry_id']
    # The authority is frozen BEFORE cancellation. Rereading mutated post and
    # inverse rows afterwards could otherwise accept a symmetric cost rewrite.
    frozen_posts=[r for r in after_allocation['journal_headers']if r['id']==original_id]
    assert frozen_posts==[oracle['journal']],'S03_LAWFUL_PRE_CANCEL_POOL_JOURNAL_AUTHORITY_REQUIRED'
    frozen_lines=[r for r in after_allocation['journal_lines']if r['journal_entry_id']==original_id]
    assert frozen_lines,'S03_LAWFUL_PRE_CANCEL_POOL_LINES_REQUIRED'
    immutable_history(after_allocation,after,reversed_journal_ids=frozenset((original_id,)))
    original=f.one(cur,'select to_jsonb(j)from erp.journal_entries j where id=%s',(original_id,))
    inverse=f.one(cur,'select to_jsonb(j)from erp.journal_entries j where id=%s',(inverse_id,))
    assert dict(original,status='POSTED')==oracle['journal'] and original['status']=='REVERSED'
    assert (original['source_type'],original['source_id'])==('ATTENDANCE_HPP_POOL',made['pool_id'])
    assert (inverse['source_type'],inverse['source_id'],inverse['reversal_of_id'],inverse['status'])==('JOURNAL_REVERSAL',original_id,original_id,'POSTED')
    today=str(f.one(cur,"select (statement_timestamp()at time zone 'Asia/Jakarta')::date"))
    assert inverse['economic_date']==today
    assert inverse['transaction_date']==str(f.one(cur,'select erp.resolve_accounting_transaction_date(%s)',(today,)))
    lines=lambda ident:f.one(cur,'select jsonb_agg(to_jsonb(l)order by l.id)from erp.journal_lines l where journal_entry_id=%s',(ident,))
    old_lines,new_lines=lines(original_id),lines(inverse_id)
    assert old_lines==frozen_lines,'S03_LAWFUL_ORIGINAL_POOL_LINES_CHANGED_AFTER_ALLOCATION'
    dimensions=('account_id','customer_id','vendor_id','contractor_id','po_id','product_id')
    signature=lambda row,flip:tuple(row[k]for k in dimensions)+(D(str(row['credit'if flip else'debit'])),D(str(row['debit'if flip else'credit'])),('Reversal: '+(row['description']or''))if flip else row['description'])
    assert len(frozen_lines)==len(new_lines) and Counter(signature(r,True)for r in frozen_lines)==Counter(signature(r,False)for r in new_lines),'S03_LAWFUL_CANCEL_EXACT_DIMENSION_AMOUNT_INVERSE_REQUIRED'
    # Preserve append-only journal history. IDs of new reversal/HPP versions
    # cannot equal old rows; compare money above and retain every raw row here.
    emit(evidence,'Native_finished_cancel',dict(before=before,after_allocation=after_allocation,after_cancel=after,
        full_FG_rows_exact=True,current_HPP_money_and_GL_exact=True,
        original_pool_journal=original,Native_inverse_journal=inverse,
        original_pool_lines=old_lines,Native_inverse_lines=new_lines,
        linked_inverse_signs_dimensions_both_dates_exact=True,
        frozen_post_allocation_history_retained=True,full_original_pool_lines_immutable=True,
        all_intermediate_HPP_versions_and_components_retained=True,
        raw_journal_history_retained=True, journal_rows_projected_as_unchanged=False))
    return after
