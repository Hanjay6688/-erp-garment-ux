"""Prepared Native QC/rework inverses; no ERP import or execution on load.

These cases require the same accepted FREE3 parent, installed component,
strict-group savepoints and complete owning restoration as the first six.
No actual ERP, Auth, browser or two-session credit is supplied by preparation.
"""
from decimal import Decimal
import uuid

IDS=(
    'NONPAYABLE_NATIVE_QC_INVERSE_AFTER_RECOST_AND_NEXT_LAWFUL_COST_REVISION',
    'NONPAYABLE_NATIVE_REWORK_NO_INITIAL_JOURNAL_INVERSE_AND_ACTIVE_LOT_RECOST',
)

def invoice_fixture(f,today):
    af=f['accessory']
    return dict(af,receipt=dict(purchase_id=af['purchase']),tag=af['code'],day=today)

def recost(cur,modules,document,today,price):
    payload=modules.invoice.payload(document,'1000',price)
    payload.update(invoice_date=str(today),received_at=modules.bc.local_at(today,8),due_date=str(today))
    made=modules.invoice.finalize(cur,document,p=payload)
    modules.bc.internal(cur,'process_cost_recalc_queue',100)
    return made

def undo_invoice(cur,modules,document,made):
    reply=modules.invoice.reverse(cur,document,made['invoice_id'])
    modules.bc.internal(cur,'process_cost_recalc_queue',100)
    return reply

def lot_state(cur,modules,f):
    from . import native_fixture
    modules.bc.api.admin(cur)
    # Preserve original journal lines and their real Native reversal records.
    # Snapshot revisions may continue after voiding; frozen basis may not.
    journals=cur.execute("""with own as (
      select j.id from erp.journal_entries j
      where (j.source_type='ACCESSORY_REIMBURSE_ACCRUAL'and j.source_id=%s)
         or (j.source_type='ACCESSORY_HPP_RECOST'and exists(
           select 1 from erp.fg_accessory_cost_revisions r
           join erp.fg_accessory_cost_snapshots s on s.id=r.snapshot_id
           where r.id=j.source_id and s.lot_id=%s)))
      select to_jsonb(j),coalesce((select jsonb_agg(to_jsonb(l)order by l.id)
        from erp.journal_lines l where l.journal_entry_id=j.id),'[]'::jsonb)
      from erp.journal_entries j where j.id in(select id from own)
         or j.reversal_of_id in(select id from own)order by j.id""",(f['lot'],f['lot'])).fetchall()
    return dict(economics=native_fixture.observe(cur,modules,f),
        lot=cur.execute('select to_jsonb(l)from erp.fg_lots l where id=%s',(f['lot'],)).fetchone()[0],
        movements=[r[0]for r in cur.execute('select to_jsonb(m)from erp.fg_stock_movements m where lot_id=%s order by id',(f['lot'],)).fetchall()],
        net_FG=str(cur.execute('select coalesce(sum(qty_signed),0)from erp.fg_stock_movements where lot_id=%s',(f['lot'],)).fetchone()[0]),
        journals=[dict(header=j,lines=lines)for j,lines in journals],
        revisions=[r[0]for r in cur.execute('select to_jsonb(r)from erp.fg_accessory_cost_revisions r '
            'join erp.fg_accessory_cost_snapshots s on s.id=r.snapshot_id where s.lot_id=%s order by r.id',(f['lot'],)).fetchall()])

def frozen(value):
    return [dict(basis=r['basis'],actual_fixed_identity=r['actual_fixed_identity'])for r in value['economics']['snapshots']]

def money(lines):
    totals={}
    for line in lines:
        key=tuple(line.get(k)for k in('account_id','customer_id','vendor_id','contractor_id','po_id','product_id'))
        totals[key]=totals.get(key,Decimal(0))+Decimal(str(line['debit']))-Decimal(str(line['credit']))
    return totals

def require_inverse(before,after):
    if (after['lot']['lot_origin']!='VOIDED_PRODUCTION'or Decimal(after['net_FG'])!=0
        or frozen(before)!=frozen(after)or after['economics']['entitlements']
        or any(Decimal(v)!=0 for v in after['economics']['booked'].values())
        or before['economics']['physical_material_movements']!=after['economics']['physical_material_movements']
        or Decimal(after['economics']['accessory_stock'])!=997):
        raise ValueError('NONPAYABLE_NATIVE_INVERSE_MUST_VOID_FG_AND_ALL_ACCESSORY_MONEY_WITH_FROZEN_HISTORY')
    by_id={j['header']['id']:j for j in after['journals']}
    originals=[j for j in before['journals']if j['header']['status']=='POSTED'and not j['header'].get('reversal_of_id')]
    if not originals:raise ValueError('NONPAYABLE_INVERSE_REQUIRES_ACTUAL_POSTED_ACCESSORY_COST')
    for original in originals:
        row=by_id.get(original['header']['id'])
        keys=('id','source_type','source_id','transaction_date','economic_date','posting_at')
        inverses=[j for j in after['journals']if j['header'].get('reversal_of_id')==original['header']['id']]
        if (row is None or row['header']['status']!='REVERSED'or row['lines']!=original['lines']
            or any(row['header'].get(k)!=original['header'].get(k)for k in keys)
            or len(inverses)!=1 or inverses[0]['header']['status']!='POSTED'
            or money(inverses[0]['lines'])!={k:-v for k,v in money(original['lines']).items()}):
            raise ValueError('NONPAYABLE_NATIVE_INVERSE_REQUIRES_ONE_EXACT_MONEY_REVERSAL_AND_ORIGINAL_DATES')
    if any(j['header']['status']=='POSTED'and not j['header'].get('reversal_of_id')for j in after['journals']):
        raise ValueError('NONPAYABLE_VOIDED_GOOD_MUST_NOT_RETAIN_OR_REVIVE_POSTED_ACCESSORY_COST')
    before_moves={r['id']:r for r in before['movements']}
    after_moves={r['id']:r for r in after['movements']}
    if any(after_moves.get(k)!=v for k,v in before_moves.items()):
        raise ValueError('NONPAYABLE_NATIVE_INVERSE_MUST_PRESERVE_ORIGINAL_FG_MOVEMENTS')

def require_voided_stays_voided(original,after_inverse,later):
    require_inverse(original,later)
    if after_inverse['journals']!=later['journals']or after_inverse['movements']!=later['movements']:
        raise ValueError('NONPAYABLE_LATER_RECOST_REVIVED_VOIDED_MONEY_OR_PHYSICAL_FG')

def qc_inverse_case(cur,today,state):
    from . import native_fixture as fixture,native_cases as first
    modules=fixture.admitted_modules(cur,state);before_findings=modules.bc.findings(cur)
    f=fixture.prepare(cur,today,modules);fixture.post_good(cur,modules,f)
    initial=lot_state(cur,modules,f);fixture.require_economics(initial['economics'],f,nonpayable=True,hpp='20')
    document=invoice_fixture(f,today);invoice=recost(cur,modules,document,today,'3.5')
    before=lot_state(cur,modules,f);fixture.require_economics(before['economics'],f,nonpayable=True,hpp='35')
    qc=str(f['good']['qc_inspection_id'])
    number=cur.execute('select inspection_number from erp.qc_inspections where id=%s',(qc,)).fetchone()[0]
    source=dict(qc=qc,number=number)
    version=next(q for q in modules.qc.workspace(cur,number)['qc_history']if q['qc_inspection_id']==qc)['row_version']
    key=str(uuid.uuid4());reply=modules.qc.reverse(cur,source,key=key,version=version)
    after=lot_state(cur,modules,f);require_inverse(before,after)
    boundary=first.boundary(cur,modules,state)
    replay=modules.qc.reverse(cur,source,key=key,version=version)
    if replay!=reply or first.boundary(cur,modules,state)!=boundary:
        raise ValueError('NONPAYABLE_QC_INVERSE_REPLAY_CHANGED_ANY_ROW_CATALOG_OR_SEQUENCE')
    inverse=undo_invoice(cur,modules,document,invoice)
    after_invoice_inverse=lot_state(cur,modules,f);require_voided_stays_voided(before,after,after_invoice_inverse)
    next_invoice=recost(cur,modules,document,today,'4')
    later=lot_state(cur,modules,f);require_voided_stays_voided(before,after,later)
    return first.finish(cur,modules,before_findings,fixture=f,actual_initial=initial,before_QC_inverse=before,
        actual_inverse_reply=reply,after_QC_inverse=after,actual_inverse_replay=replay,
        full_replay_boundary=boundary,first_invoice=invoice,lawful_invoice_inverse=inverse,
        after_invoice_inverse=after_invoice_inverse,next_invoice=next_invoice,after_next_cost_revision=later,
        original_basis_journal_lines_and_dates_retained=True,voided_cost_never_revived=True,
        no_duplicate_stock_journal_entitlement_or_replay_effect=True)

def rework_inverse_case(cur,today,state):
    from . import native_fixture as fixture,native_cases as first
    modules=fixture.admitted_modules(cur,state);bc,bd=modules.bc,modules.bd
    before_findings=bc.findings(cur)
    f=fixture.prepare(cur,today,modules,unit_cost='0.004',qty_per_good='0.1')
    fixture.post_good(cur,modules,f,good_qty=5,bs_qty=5)
    initial=lot_state(cur,modules,f);fixture.require_economics(initial['economics'],f,nonpayable=True,hpp='0.002')
    bs=cur.execute('select id::text from erp.bs_cases where cutting_group_id=%s and qc_item_id is not null',(f['group'],)).fetchall()
    if len(bs)!=1:raise ValueError('NONPAYABLE_REWORK_REQUIRES_ONE_NATIVE_FIVE_PCS_BS_SOURCE')
    when=lambda hour:bd.chain.production.at(f['good_day'],hour)
    bom=cur.execute('select erp.resolve_rework_accessory_bom_v1(%s,%s)::text',(bs[0][0],when(15))).fetchone()[0]
    items=cur.execute('select id::text from erp.accessory_bom_items where bom_version_id=%s and category_id=%s',
        (bom,f['accessory']['category'])).fetchall()
    if len(items)!=1:raise ValueError('NONPAYABLE_REWORK_EXACT_ONE_ACTUAL_SELECTED_BOM_ITEM_REQUIRED')
    payload=dict(rework_number='NP-RW-'+uuid.uuid4().hex[:12],bs_case_id=bs[0][0],destination_type='LAUNDRY',
        contractor_id=None,vendor_id=f['vendor'],qty_sent=5,physical_sent_at=when(15).isoformat(),status='IN_PROGRESS',
        return_fg_location_id=bd.chain.base.LOCATION,accessory_bom_version_id=bom,accessory_bom_item_ids=[items[0][0]],
        components=[],change_reason='Native selected company-funded accessory rework')
    made=bd.chain.bs_action(cur,'SAVE_REWORK',payload);rid=made['result']['rework_order_id'];bc.api.admin(cur)
    recipient=str(cur.execute('select reimbursement_contractor_id from erp.rework_accessory_decisions where rework_order_id=%s',(rid,)).fetchone()[0])
    if recipient!=f['contractor']:raise ValueError('NONPAYABLE_REWORK_RECIPIENT_MUST_BE_RECORDED_SOURCE_PO_MANDOR')
    completed=bd.chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=3,qty_bs=2,
        completed_at=when(16).isoformat(),return_fg_location_id=bd.chain.base.LOCATION,
        change_reason='Native three GOOD and two remaining BS'),bd.chain.version(cur,'rework_orders',rid));bc.api.admin(cur)
    rework=dict(f,lot=str(completed['result']['good_fg_lot_id']),good_qty=3)
    rework_initial=lot_state(cur,modules,rework)
    fixture.require_economics(rework_initial['economics'],rework,nonpayable=True,hpp='0.0012')
    if initial['journals']or rework_initial['journals']:
        raise ValueError('NONPAYABLE_SUBCENT_QC_AND_REWORK_MUST_HAVE_NO_INITIAL_ACCESSORY_JOURNAL')
    document=invoice_fixture(f,today);invoice=recost(cur,modules,document,today,'0.1')
    active_before=lot_state(cur,modules,f);before=lot_state(cur,modules,rework)
    fixture.require_economics(active_before['economics'],f,nonpayable=True,hpp='0.05')
    fixture.require_economics(before['economics'],rework,nonpayable=True,hpp='0.03')
    if active_before['economics']['original_accrual']or before['economics']['original_accrual']:
        raise ValueError('NONPAYABLE_LATE_COST_MUST_USE_REVISIONS_WITHOUT_MANUFACTURING_INITIAL_ACCRUAL')
    version=bd.chain.version(cur,'rework_orders',rid);key=str(uuid.uuid4())
    inverse_payload=dict(rework_order_id=rid,change_reason='Native inverse company-funded rework after late invoice')
    reply=bd.chain.bs_action(cur,'REVERSE_REWORK_COMPLETION',inverse_payload,version,key=key);bc.api.admin(cur)
    after=lot_state(cur,modules,rework);require_inverse(before,after)
    active_after=lot_state(cur,modules,f)
    if (active_after['economics']!=active_before['economics']or active_after['movements']!=active_before['movements']
        or active_after['net_FG']!=active_before['net_FG']or active_after['lot']['lot_origin']!='PRODUCTION'):
        raise ValueError('NONPAYABLE_REWORK_INVERSE_CHANGED_UNRELATED_ACTIVE_QC_ACCESSORY_COST_OR_STOCK')
    boundary=first.boundary(cur,modules,state)
    replay=bd.chain.bs_action(cur,'REVERSE_REWORK_COMPLETION',inverse_payload,version,key=key);bc.api.admin(cur)
    if replay.get('result')!=reply.get('result')or first.boundary(cur,modules,state)!=boundary:
        raise ValueError('NONPAYABLE_REWORK_INVERSE_REPLAY_CHANGED_ANY_ROW_CATALOG_OR_SEQUENCE')
    inverse=undo_invoice(cur,modules,document,invoice)
    after_invoice_inverse=lot_state(cur,modules,rework);require_voided_stays_voided(before,after,after_invoice_inverse)
    active_restored=lot_state(cur,modules,f);fixture.require_economics(active_restored['economics'],f,nonpayable=True,hpp='0.002')
    next_invoice=recost(cur,modules,document,today,'0.2')
    later=lot_state(cur,modules,rework);require_voided_stays_voided(before,after,later)
    active_later=lot_state(cur,modules,f);fixture.require_economics(active_later['economics'],f,nonpayable=True,hpp='0.1')
    if frozen(initial)!=frozen(active_later)or initial['economics']['physical_material_movements']!=active_later['economics']['physical_material_movements']:
        raise ValueError('NONPAYABLE_LATER_ACTIVE_QC_RECOST_CHANGED_FROZEN_BASIS_OR_PHYSICAL_STOCK')
    return first.finish(cur,modules,before_findings,fixture=f,rework_fixture=rework,actual_initial=initial,
        actual_rework_initial=rework_initial,actual_rework_order=made,actual_rework_completion=completed,
        active_before_inverse=active_before,rework_before_inverse=before,actual_inverse_reply=reply,
        rework_after_inverse=after,active_after_inverse=active_after,actual_inverse_replay=replay,
        full_replay_boundary=boundary,first_invoice=invoice,lawful_invoice_inverse=inverse,
        after_invoice_inverse=after_invoice_inverse,active_after_invoice_inverse=active_restored,next_invoice=next_invoice,
        rework_after_next_cost_revision=later,active_after_next_cost_revision=active_later,
        no_initial_journal=True,rework_recipient_from_actual_immutable_decision=recipient,
        voided_rework_cost_never_revived=True,unrelated_active_QC_cost_still_updates=True)

def cases(cur,today,state):
    from . import native_fixture
    native_fixture.admitted_modules(cur,state)
    if len(IDS)!=2 or len(set(IDS))!=2:raise ValueError('NONPAYABLE_TWO_UNIQUE_NATIVE_INVERSE_CASES_REQUIRED')
    return [(IDS[0],lambda:qc_inverse_case(cur,today,state)),
            (IDS[1],lambda:rework_inverse_case(cur,today,state))]
