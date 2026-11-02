"""Prepared positive-HPP/R0 finished PO -> FG -> ordinary credit sale proof."""
from decimal import Decimal,ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
import json,subprocess,uuid

IDS=('NONPAYABLE_NATIVE_FINISHED_PO_FG_SALES_COGS_LATE_COST_AND_LAWFUL_INVERSES',)
ORIGINAL_BASE='0da4d79a4f7201ef053d6de1eb155d990b4bfa4d'
ORIGINALS={'scripts/cp7_sales_command_cases.py': (10159, 'b6d6e0b6995e3dee2ae7f0e69ab6b48c6c965ee31f15cca4027c47b5159885df'), 'scripts/cp7_sales_draft_cases.py': (11278, '9795a983aaeeae20793b6b7741d18a4486ac05193af97776882ce8014c2a84f4'), 'scripts/cp7_sales_cases.py': (9255, 'c76d05c381f712d50e61ab1d8efa367981e7619a842581fecc21a73ed9b6e185'), 'scripts/cp7_cp17_fix_cases.py': (151004, '3d387cbca883e8f69c3b8cfd88cbcd1c9a2e54bcf6ed0143a3c69bc928d458ef')}

def source_controls():
    root=Path(__file__).resolve().parents[2]
    for name,pin in ORIGINALS.items():
        raw=(root/name).read_bytes()
        if (len(raw),sha256(raw).hexdigest())!=pin or raw!=subprocess.check_output(
            ['/usr/bin/git','-C',str(root),'show',ORIGINAL_BASE+':'+name]):
            raise ValueError('NONPAYABLE_SALES_ORIGINAL_CHANGED:'+name)
    if len(ORIGINALS)!=4:raise ValueError('NONPAYABLE_FOUR_EXACT_SALES_FINISH_ORIGINALS_REQUIRED')
    return dict(status='NATIVE_FINISHED_PO_FG_SALES_COGS_SOURCE_PREPARED_NOT_EXECUTED',
        case_ids=list(IDS),unchanged_original_source_files=len(ORIGINALS),actual_SQL_executed=0,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)

def require_cost_delta(before,after,total,*,produced=10,sold=4):
    amount=Decimal(total)
    cogs=(amount*Decimal(sold)/Decimal(produced)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    actual={key:Decimal(str(after[key]))-Decimal(str(before[key]))for key in('WIP','FG_INVENTORY','COGS')}
    expected=dict(WIP=Decimal(0),FG_INVENTORY=amount-cogs,COGS=cogs)
    if actual!=expected:raise ValueError('NONPAYABLE_EXACT_FINISHED_PO_FG_COGS_DELTA_REQUIRED:'+str(actual))
    return {key:str(value)for key,value in actual.items()}

def observe(cur,modules,f,sale,finish,command):
    from . import native_fixture
    modules.bc.api.admin(cur)
    cur.execute("set local timezone='UTC'")
    projections=cur.execute("select to_jsonb(m),jsonb_build_object('id',id,'lot_id',lot_id,'product_id',product_id,"
        "'location_id',location_id,'quality_grade',quality_grade,'movement_type',movement_type,'source_type',source_type,"
        "'source_id',source_id,'reversal_of_id',reversal_of_id,'qty_signed',qty_signed,'physical_at',physical_at)"
        'from erp.fg_stock_movements m where lot_id=%s order by id',(f['lot'],)).fetchall()
    detail=command.source.read(cur,sale,subject=sale['actor'])['detail']
    modules.bc.api.admin(cur)
    headers=cur.execute('select to_jsonb(h)from erp.sales_headers h where id=%s',(sale['sale'],)).fetchone()[0]
    items=[r[0]for r in cur.execute('select to_jsonb(i)from erp.sales_items i where sale_id=%s order by id',(sale['sale'],)).fetchall()]
    commercial=dict(header={k:headers[k]for k in('id','sale_number','customer_id','source_location_id','sale_date')},
        items=[{k:i[k]for k in('id','product_id','qty_pcs','unit_price_snapshot','discount_amount')}for i in items])
    return dict(accessory=native_fixture.observe(cur,modules,f),po_status=finish.po_state(cur,f['po'])['status'],
        current_HPP=[r[0]for r in cur.execute('select to_jsonb(h)from erp.v_current_hpp h where lot_id=%s',(f['lot'],)).fetchall()],
        total_lot_HPP=str(modules.bd.lot_value(cur,f['lot'])),
        PO_GL={key:str(cur.execute("select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l "
            "join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED')"
            "and l.po_id=%s and l.account_id=erp.account_id(%s)",(f['po'],key)).fetchone()[0])for key in('WIP','FG_INVENTORY','COGS')},
        raw_FG_movements=[r[0]for r in projections],physical_FG_movements=[r[1]for r in projections],
        net_FG=str(command.available(cur,f)),sales_reader=detail,raw_sales_header=headers,raw_sales_items=items,commercial=commercial,
        sale_allocations=[r[0]for r in cur.execute('select to_jsonb(a)from erp.sale_stock_allocations a '
            'join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s order by a.id',(sale['sale'],)).fetchall()])

def require_unchanged_sale_and_stock(before,after):
    from .native_inverse_cases import frozen
    if(before['commercial']!=after['commercial']or before['physical_FG_movements']!=after['physical_FG_movements']
        or before['net_FG']!=after['net_FG']or before['sales_reader']['financial']!=after['sales_reader']['financial']
        or frozen(dict(economics=before['accessory']))!=frozen(dict(economics=after['accessory']))
        or before['accessory']['physical_material_movements']!=after['accessory']['physical_material_movements']
        or after['accessory']['entitlements']or after['po_status']!='FINISHED'):
        raise ValueError('NONPAYABLE_COST_REVISION_CHANGED_INVOICE_PHYSICAL_STOCK_FROZEN_BASIS_OR_ENTITLEMENT')

def replay(cur,modules,state,operation,expected):
    from .native_cases import boundary
    before=boundary(cur,modules,state);actual=operation();after=boundary(cur,modules,state)
    if actual!=expected or before!=after:raise ValueError('NONPAYABLE_SALES_REPLAY_CHANGED_ROW_CATALOG_OR_SEQUENCE')
    return dict(status='PASS',actual_reply=actual,before=before,after=after)

def exercise(cur,today,state):
    from . import native_fixture,native_cases,native_inverse_cases,access_cases
    modules=native_fixture.admitted_modules(cur,state);source_controls();access_cases.source_controls()
    import cp7_sales_command_cases as command
    import cp7_sales_draft_cases as draft
    import cp7_cp17_fix_cases as finish
    import cp7_master_cases as master
    bc=modules.bc;before_findings=bc.findings(cur)
    f=native_fixture.prepare(cur,today,modules);native_fixture.post_good(cur,modules,f)
    initial=native_fixture.observe(cur,modules,f);native_fixture.require_economics(initial,f,nonpayable=True,hpp='20')
    finished=finish.finish_command(cur,finish.finish_workspace(cur,f['po']),reason='Native finish with company-funded accessory HPP and zero reimbursement')
    bc.api.admin(cur)
    if finish.po_state(cur,f['po'])['status']!='FINISHED'or finish.po_wip_balance(cur,f['po'])!=0:
        raise ValueError('NONPAYABLE_NATIVE_FINISHED_PO_ZERO_WIP_REQUIRED')
    total_before=modules.bd.lot_value(cur,f['lot'])
    if total_before<20:raise ValueError('NONPAYABLE_FINISHED_LOT_HPP_MUST_INCLUDE_POSITIVE_ACCESSORY_COST')
    actor=master.role_actor(cur,'OWNER');tag='NP-SALE-'+uuid.uuid4().hex[:10]
    customer=str(modules.bd.chain.base.create_customer(cur,tag))
    sale=dict(f,tag=tag,customer=customer,location=modules.bd.chain.base.LOCATION,actor=actor,
        sale_at=native_fixture.actual_time(cur,f['good_day']).isoformat())
    accounts_before=command.accounts(cur)
    create_payload=draft.payload(sale,qty='4',price='50',discount='0');create_key=uuid.uuid4()
    made=draft.create(cur,sale,p=create_payload,key=create_key,subject=actor)
    create_replay=replay(cur,modules,state,lambda:command.command(cur,'CREATE',create_payload,None,create_key,actor),made)
    if command.available(cur,f)!=6 or command.accounts(cur)!=accounts_before:
        raise ValueError('NONPAYABLE_CREDIT_DRAFT_MUST_RESERVE_FOUR_WITHOUT_POSTING_MONEY')
    post_payload,version=command.review(cur,sale);post_key=uuid.uuid4()
    posted=command.command(cur,'POST',post_payload,version,post_key,actor)
    post_replay=replay(cur,modules,state,lambda:command.command(cur,'POST',post_payload,version,post_key,actor),posted)
    accounts_posted=command.accounts(cur)
    before=observe(cur,modules,f,sale,finish,command)
    cogs=(Decimal(total_before)*Decimal(4)/10).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    expected={command.mapping(cur,'AR_CUSTOMER'):Decimal(200),command.mapping(cur,'SALES_REVENUE'):Decimal(-200),
        command.mapping(cur,'FG_INVENTORY'):-cogs,command.mapping(cur,'COGS'):cogs}
    if (command.delta(accounts_before,command.accounts(cur))!=expected or before['net_FG']!='6'
        or Decimal(before['PO_GL']['WIP'])!=0 or before['sales_reader']['financial']['open_balance']!='200.00'):
        raise ValueError('NONPAYABLE_CREDIT_SALE_EXACT_AR_REVENUE_FG_COGS_WITHOUT_CASH_REQUIRED')
    document=native_inverse_cases.invoice_fixture(f,today)
    cheaper=native_inverse_cases.recost(cur,modules,document,today,'1')
    reduced=observe(cur,modules,f,sale,finish,command);native_fixture.require_economics(reduced['accessory'],f,nonpayable=True,hpp='10')
    decrease=require_cost_delta(before['PO_GL'],reduced['PO_GL'],'-10');require_unchanged_sale_and_stock(before,reduced)
    if Decimal(reduced['total_lot_HPP'])!=total_before-10:raise ValueError('NONPAYABLE_FINISHED_HPP_REDUCTION_MUST_BE_TEN')
    cheaper_inverse=native_inverse_cases.undo_invoice(cur,modules,document,cheaper)
    restored=observe(cur,modules,f,sale,finish,command);native_fixture.require_economics(restored['accessory'],f,nonpayable=True,hpp='20')
    require_unchanged_sale_and_stock(before,restored)
    if(restored['PO_GL']!=before['PO_GL']or Decimal(restored['total_lot_HPP'])!=total_before
        or command.accounts(cur)!=accounts_posted):
        raise ValueError('NONPAYABLE_LAWFUL_SUPPLIER_INVERSE_MUST_RESTORE_FINISHED_FG_AND_COGS')
    dearer=native_inverse_cases.recost(cur,modules,document,today,'3.5')
    increased=observe(cur,modules,f,sale,finish,command);native_fixture.require_economics(increased['accessory'],f,nonpayable=True,hpp='35')
    increase=require_cost_delta(before['PO_GL'],increased['PO_GL'],'15');require_unchanged_sale_and_stock(before,increased)
    if Decimal(increased['total_lot_HPP'])!=total_before+15:raise ValueError('NONPAYABLE_FINISHED_HPP_INCREASE_MUST_BE_FIFTEEN')
    bc.api.admin(cur)
    eligible=cur.execute("select id::text from erp.cost_recalc_queue where status='PENDING'or "
        "(status='FAILED'and attempt_count<3 and coalesce(next_attempt_at,statement_timestamp())<=statement_timestamp())order by id").fetchall()
    if eligible:raise ValueError('NONPAYABLE_REPLAY_CONTROL_REQUIRES_ACTUALLY_EMPTY_ELIGIBLE_RECOST_QUEUE:'+str(eligible))
    queue_before=native_cases.boundary(cur,modules,state)
    bc.internal(cur,'process_cost_recalc_queue',100)
    if native_cases.boundary(cur,modules,state)!=queue_before:
        raise ValueError('NONPAYABLE_REPLAYED_EMPTY_RECOST_QUEUE_CREATED_SECOND_MONEY_OR_STOCK_EFFECT')
    dearer_inverse=native_inverse_cases.undo_invoice(cur,modules,document,dearer)
    restored_again=observe(cur,modules,f,sale,finish,command);require_unchanged_sale_and_stock(before,restored_again)
    if(restored_again['PO_GL']!=before['PO_GL']or Decimal(restored_again['total_lot_HPP'])!=total_before
        or command.accounts(cur)!=accounts_posted):
        raise ValueError('NONPAYABLE_SECOND_SUPPLIER_INVERSE_MUST_RESTORE_ORIGINAL_FINISHED_COST')
    reverse_payload,reverse_version=command.review(cur,sale);reverse_key=uuid.uuid4()
    reversed_sale=command.command(cur,'SALE_REVERSE',reverse_payload,reverse_version,reverse_key,actor)
    reverse_replay=replay(cur,modules,state,lambda:command.command(cur,'SALE_REVERSE',reverse_payload,reverse_version,reverse_key,actor),reversed_sale)
    final=observe(cur,modules,f,sale,finish,command)
    native_fixture.require_economics(final['accessory'],f,nonpayable=True,hpp='20')
    if (command.accounts(cur)!=accounts_before or Decimal(final['net_FG'])!=10 or Decimal(final['PO_GL']['WIP'])!=0
        or final['po_status']!='FINISHED'or final['sales_reader']['status']!='REVERSED'):
        raise ValueError('NONPAYABLE_OWNING_SALE_INVERSE_MUST_RESTORE_STOCK_AND_ALL_COMPANY_GL_WITHOUT_CASH')
    return native_cases.finish(cur,modules,before_findings,fixture=f,sale_fixture=sale,actual_finish=finished,
        original_positive_HPP_zero_reimbursement=initial,actual_create=made,create_replay=create_replay,
        actual_post=posted,post_replay=post_replay,before_supplier_corrections=before,
        cheaper_invoice=cheaper,after_cheaper_invoice=reduced,expected_cheaper_cost_delta=decrease,
        cheaper_invoice_inverse=cheaper_inverse,after_first_inverse=restored,
        dearer_invoice=dearer,after_dearer_invoice=increased,expected_dearer_cost_delta=increase,
        dearer_invoice_inverse=dearer_inverse,after_second_inverse=restored_again,
        actual_sale_inverse=reversed_sale,sale_inverse_replay=reverse_replay,actual_final=final,
        produced_qty=10,sold_qty=4,exact_invoice_amount='200.00',no_payments_no_cash_or_kasbon=True,
        financial_HPP_decrease='-10',expected_decrease_COGS='-4',expected_decrease_FG='-6',
        financial_HPP_increase='15',expected_increase_COGS='6',expected_increase_FG='9',
        original_basis_physical_lineage_and_commercial_history_retained=True)

def cases(cur,today,state):
    from . import native_fixture
    native_fixture.admitted_modules(cur,state)
    source_controls()
    return[(IDS[0],lambda:exercise(cur,today,state))]
