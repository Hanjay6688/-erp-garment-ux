"""Three prepared actual Native callbacks. No runtime PASS until executed.

Native7 original must be admitted explicitly before strict_group invokes cases.
The recovery case proves a safety refusal, never whole-group recovery support.
"""
from decimal import Decimal as D
from pathlib import Path
import importlib.util,re,uuid

HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
n=load('sku_group_cost_Native_fixture',HERE/'native_fixture.py')
o=load('sku_group_cost_independent_oracle',HERE/'oracle.py')
guard=load('sku_group_cost_source_guard',HERE/'source_guard.py')
IDS=(
 'SKU29_COST_GROUP_RETURN_OVER_FIRST_PART_SAFETY_REFUSAL_ONLY',
 'SKU29_COST_BOTH_PARTS_USAGE_LATE_INVOICE_SOLD_AND_DESCENDANT',
 'SKU29_COST_FIRST_PART_ACTIVE_USAGE_ATOMIC_GROUP_INVERSE',
)
NATIVE7_IDS=(
 'SKU29_PAIR_BIDIRECTIONAL_REPLACE_DELETE_NO_LEDGER',
 'SKU29_NONPO_MULTILOT_FIFO_RESERVATION_VALUE_REPLAY',
 'SKU29_ANY_ACTIVE_MODEL_SIZE_MANUAL_BACK_CURRENT_SOURCE_COST',
 'SKU29_STALE_SOURCE_TARGET_RESERVATIONS_REFUSE_ZERO_EFFECT',
 'SKU29_GROUP_REVERSE_ACTIVE_SALE_REFUSAL_THEN_RELEASE',
 'SKU29_MIXED_PO_NONPO_NATIVE_LINEAGE_VALUE_CONSERVATION',
 'SKU29_LEGACY_ACCESSORY_COST_AND_INVERSE_PRESERVED',
)
NATIVE7_ADMISSION=None

def admit_native7(native_group,*,original_report_sha256,backend_commit):
    """Caller verifies the exact raw original/package before supplying its group.

    This is a test-run dependency gate, not an application permission endpoint.
    It neither starts a run nor reads or synthesizes Auth credentials.
    """
    global NATIVE7_ADMISSION
    NATIVE7_ADMISSION=None
    assert backend_commit=='21c69cf25defcee854beb08e998062d7e883d968','SKU_COST_EXACT_BACKEND_REQUIRED'
    assert re.fullmatch('[a-f0-9]{64}',original_report_sha256),'SKU_COST_ORIGINAL_REPORT_DIGEST_REQUIRED'
    assert native_group.get('counts')=={'PASS':7}and set(native_group.get('cases',{}))==set(NATIVE7_IDS),'SKU_COST_NATIVE7_PASS_REQUIRED'
    assert not native_group.get('error')and all(case.get('status')=='PASS'and case.get('full_boundary_restored')is True for case in native_group['cases'].values()),'SKU_COST_NATIVE7_BOUNDARY_REQUIRED'
    NATIVE7_ADMISSION=dict(backend_commit=backend_commit,original_report_sha256=original_report_sha256,
      actual_Native7_original_admitted_by_outer_adapter=True,all_seven_original_case_ids=list(NATIVE7_IDS))
    return NATIVE7_ADMISSION

def recovery_safety(cur,today):
    fixture=n.f.nonpo(cur,today);acc=n.material(cur,today,cost='30.03',recovery=True)
    made,parts=n.make_group(cur,fixture,[dict(material_id=acc['material'],qty='1',holder='SKU cost group recovery holder')])
    expected=o.recovery_limit();assert n.values(cur,parts)==o.BASE_VALUES
    n.f.admin(cur)
    links=cur.execute('select conversion_id::text,outstanding_id::text from erp.be_conversion_returns_v1 where conversion_id=any(%s::uuid[])order by conversion_id',(made['conversion_ids'],)).fetchall()
    assert len(links)==1 and links[0][0]==parts[0]['conversion_id'],links
    receipt=n.bc.receive(cur,acc,'TEARDOWN',[(1,links[0][1])],physical_at=n.at(fixture,20),reference='SKU cost one actual recovery')['lot_ids'][0]
    n.bc.inspect(cur,receipt,n.at(fixture,30),'SKU cost Native inspector',usable=1)
    payload=dict(lot_id=receipt,condition='USABLE',qty='1',unit_value='30.03',location_id=acc['main'],
      physical_at=n.at(fixture,40),reason='SKU cost recovery exceeds first part but not whole group')
    before=n.capture(cur);refusal=n.refused(cur,lambda:n.bc.svc(cur,'VALUE_CUSTODY',payload),'BE_RECOVERY_EXCEEDS_VALUE')
    evidence=n.unchanged(cur,before,'RECOVERY_OVER_FIRST_PART_REFUSAL')
    assert n.values(cur,parts)==o.BASE_VALUES and n.statuses(cur,parts)==['POSTED','POSTED']
    assert n.f.stocks(cur,fixture['source'],fixture['location'])==dict(physical=6,reserved=1,available=5)
    return dict(status='PASS',coverage='NATIVE_SAFETY_REFUSAL_ONLY_NOT_WHOLE_GROUP_RECOVERY_CAPABILITY',
      group_recovery_supported=False,first_child_only_limitation_confirmed=True,Native_guard_not_relaxed=True,
      conversion_group_id=made['conversion_id'],independent_fixture_math={key:str(value)if isinstance(value,D)else value for key,value in expected.items()},
      actual_recovery_refusal=refusal,complete_refusal_evidence=evidence,
      receipt_inspection_actual_Native_prerequisites=True,full_group_recovery_acceptance=False)

def both_parts_recost(cur,today):
    fixture=n.f.nonpo(cur,today);acc=n.material(cur,today)
    target=n.clone_same_dimensions(cur,fixture['target'])
    made,parts=n.make_group(cur,fixture);original_source=n.source_hpp(cur,fixture)
    usage_replays=[]
    for number,(part,qty)in enumerate(zip(parts,o.USAGE_PCS),1):
        used,payload,key=n.usage(cur,fixture,acc,part,qty);frozen=n.capture(cur)
        assert n.f.action(cur,'POST_USAGE',payload,key)==used
        usage_replays.append(n.unchanged(cur,frozen,'PART_'+str(number)+'_USAGE_SAME_UUID_REPLAY'))
    assert n.values(cur,parts)==(D('22.02'),D('44.04'))
    assert n.bc.stock(cur,acc['material'],acc['main'])==97
    child=n.descendant(cur,fixture,parts[1],target)
    assert n.f.b.lot_value(cur,child['destination_lot_id'])==D('22.02')
    # Prediction precedes the actual sale. Both group destinations share the
    # declared parent time, so Native's produced_at,id order is UUID order.
    predicted=sorted(range(2),key=lambda index:parts[index]['destination_lot_id'])
    ordered=cur.execute('select id::text from erp.fg_lots where id=any(%s::uuid[])order by produced_at,id',([fixture['target_lot'],*(part['destination_lot_id']for part in parts)],)).fetchall()
    assert [row[0]for row in ordered]==[fixture['target_lot'],*(parts[index]['destination_lot_id']for index in predicted)],ordered
    expected=o.gold(predicted[0]);sale=n.sale(cur,fixture,5)
    allocation=cur.execute('select a.lot_id::text,a.qty_pcs from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s order by a.lot_id',(sale,)).fetchall()
    assert sorted(allocation)==sorted([(fixture['target_lot'],4),(parts[predicted[0]]['destination_lot_id'],1)]),allocation
    facts=n.immutable(cur,[*made['conversion_ids'],child['conversion_id']],sale)
    before=n.books(cur);catalog=n.capture(cur)['catalog'];truth=n.f.b.all_truth(cur)
    invoice,args=n.invoice(cur,acc,today);after=n.books(cur)
    assert n.values(cur,parts)==expected['after_invoice']
    assert n.f.b.lot_value(cur,child['destination_lot_id'])==expected['descendant_after']
    assert after['FG_INVENTORY']-before['FG_INVENTORY']==expected['FG_invoice_delta'],(before,after,expected)
    assert after['COGS']-before['COGS']==expected['COGS_invoice_delta'],(before,after,expected)
    assert after['MATERIAL_INVENTORY']-before['MATERIAL_INVENTORY']==expected['material_inventory_invoice_delta']
    assert all(after[key]==before[key]for key in('OTHER_INCOME','OTHER_EXPENSE','WIP'))
    assert n.bc.stock(cur,acc['material'],acc['main'])==97
    assert n.immutable(cur,[*made['conversion_ids'],child['conversion_id']],sale)==facts
    assert n.source_hpp(cur,fixture)==original_source
    assert n.capture(cur)['catalog']==catalog
    assert n.f.b.truth_quiet(truth,n.f.b.all_truth(cur))
    product_books={product:n.f.product_books(cur,product)for product in(fixture['source'],fixture['target'],target)}
    # Replay the same posted supplier invoice UUID through the real Native API.
    frozen=n.capture(cur);again=n.f.b.internal(cur,'post_material_supplier_invoice_v2',*args)
    assert again==invoice
    replay=n.unchanged(cur,frozen,'LATE_INVOICE_SAME_UUID_REPLAY')
    n.reverse_invoice(cur,invoice)
    assert n.values(cur,parts)==expected['after_usage']
    assert n.f.b.lot_value(cur,child['destination_lot_id'])==expected['descendant_before']
    assert n.books(cur)==before
    assert n.immutable(cur,[*made['conversion_ids'],child['conversion_id']],sale)==facts
    assert n.source_hpp(cur,fixture)==original_source
    assert n.f.b.truth_quiet(truth,n.f.b.all_truth(cur))
    return dict(status='PASS',coverage='NATIVE_BOTH_PARTS_USAGE_AND_LATE_INVOICE_PROPAGATION',conversion_group_id=made['conversion_id'],
      initial_values=['20.02','40.04'],usage_values=['22.02','44.04'],invoiced_values=['23.02','46.04'],
      group_initial='60.06',group_usage='66.06',group_invoiced='69.06',material_physical_before=100,material_physical_after=97,
      predicted_before_sale_part_number=predicted[0]+1,actual_sale_allocations=allocation,
      invoice_FG_delta=str(expected['FG_invoice_delta']),invoice_COGS_delta=str(expected['COGS_invoice_delta']),
      descendant_conversion_id=child['conversion_id'],descendant_before='22.02',descendant_after='23.02',
      old_complete_conversion_allocation_and_sale_snapshots_immutable=True,original_source_HPP_rows_unchanged=True,
      Native_product_targets_books=product_books,usage_replay_complete_evidence=usage_replays,replay_complete_evidence=replay,legitimate_invoice_inverse_restores_costs_and_accounts=True,
      whole_group_recovery_capability=False)

def atomic_inverse(cur,today):
    fixture=n.f.nonpo(cur,today);acc=n.material(cur,today);before=n.books(cur)
    made,parts=n.make_group(cur,fixture);use,_,_=n.usage(cur,fixture,acc,parts[0],1)
    assert n.values(cur,parts)==(D('22.02'),D('40.04'))
    assert n.statuses(cur,parts)==['POSTED','POSTED']
    assert n.f.one(cur,'select count(*)from erp.be_conversion_cost_sources_v1 where conversion_id=%s',parts[1]['conversion_id'])==0
    # The actual immutable member order proves the unblocked second part is
    # attempted first, then the first part's active usage refuses the command.
    order=cur.execute('select conversion_id::text from cp7_sku_conversion.members_v1 where group_id=%s order by line_no desc',(made['conversion_id'],)).fetchall()
    assert [row[0]for row in order]==[parts[1]['conversion_id'],parts[0]['conversion_id']]
    frozen=n.capture(cur)
    refusal=n.refused(cur,lambda:n.f.action(cur,'REVERSE',dict(conversion_id=parts[1]['conversion_id'],reason='Must rollback second part before first dependant')),'BE_REVERSE_DEPENDANTS')
    evidence=n.unchanged(cur,frozen,'GROUP_INVERSE_FIRST_PART_ACTIVE_USAGE')
    assert n.statuses(cur,parts)==['POSTED','POSTED']
    assert n.values(cur,parts)==(D('22.02'),D('40.04'))
    frozen=n.capture(cur)
    direct=n.refused(cur,lambda:n.f.b.internal(cur,'reverse_product_conversion',parts[1]['conversion_id'],'Partial inverse is forbidden'),'CP7_SKU_GROUP_REVERSE_REQUIRED')
    direct_evidence=n.unchanged(cur,frozen,'DIRECT_PARTIAL_INVERSE_REFUSAL')
    n.bc.reverse(cur,use['cost_document_id'],'SKU cost legitimate usage inverse')
    assert n.values(cur,parts)==o.BASE_VALUES and n.bc.stock(cur,acc['material'],acc['main'])==100
    result=n.f.action(cur,'REVERSE',dict(conversion_id=parts[1]['conversion_id'],reason='SKU cost legitimate whole group inverse'))
    assert set(result['conversion_ids'])==set(made['conversion_ids'])and n.statuses(cur,parts)==['REVERSED','REVERSED']
    assert n.f.stocks(cur,fixture['source'],fixture['location'])==dict(physical=10,reserved=1,available=9)
    assert n.f.stocks(cur,fixture['target'],fixture['location'])==dict(physical=4,reserved=0,available=4)
    assert n.books(cur)==before
    return dict(status='PASS',coverage='NATIVE_GROUP_INVERSE_WITH_SECOND_PART_DML_BEFORE_FIRST_PART_COST_REFUSAL',conversion_group_id=made['conversion_id'],
      Native_inverse_order=[row[0]for row in order],active_cost_part=1,unblocked_inverse_attempt_part=2,
      earlier_second_part_DML_path_inferred_from_exact_Native_source_order_and_later_first_part_error=True,
      Native_cost_dependant_refusal=refusal,complete_atomic_refusal_evidence=evidence,direct_partial_refusal=direct,
      complete_direct_refusal_evidence=direct_evidence,legitimate_usage_inverse_then_whole_inverse=True,
      source_physical=10,source_reserved=1,source_available=9,target_physical=4,material_physical=100,all_account_balances_restored=True,
      whole_group_recovery_capability=False)

def cases(cur,today):
    assert NATIVE7_ADMISSION is not None,'SKU_COST_REQUIRES_PRIOR_ACTUAL_NATIVE7_PASS'
    guard.admitted();n.require_local(cur)
    return [(name,lambda operation=operation:operation(cur,today))for name,operation in zip(IDS,(recovery_safety,both_parts_recost,atomic_inverse))]
