"""Seven intended Native cases. They have not run until actual report says so.

No locally observed value defines an expected value. The mixed-PO case checks
allocation conservation from each existing source and independently declared
FIFO order, without inventing the source PO's cost. Native's legacy accessory
case is a regression only, not complete group accessory/recovery qualification.
"""
from datetime import timedelta
from decimal import Decimal as D
import importlib.util,json,uuid
from pathlib import Path

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('sku29_actual_fixture',HERE/'fixture.py')
f=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(f)

IDS=(
 'SKU29_PAIR_BIDIRECTIONAL_REPLACE_DELETE_NO_LEDGER',
 'SKU29_NONPO_MULTILOT_FIFO_RESERVATION_VALUE_REPLAY',
 'SKU29_ANY_ACTIVE_MODEL_SIZE_MANUAL_BACK_CURRENT_SOURCE_COST',
 'SKU29_STALE_SOURCE_TARGET_RESERVATIONS_REFUSE_ZERO_EFFECT',
 'SKU29_GROUP_REVERSE_ACTIVE_SALE_REFUSAL_THEN_RELEASE',
 'SKU29_MIXED_PO_NONPO_NATIVE_LINEAGE_VALUE_CONSERVATION',
 'SKU29_LEGACY_ACCESSORY_COST_AND_INVERSE_PRESERVED',
)

def pairs(cur,today):
    fixture=f.nonpo(cur,today);groups=fixture['groups'];ids=[g['id']for g in groups]
    before=f.native_ledgers(cur)
    assert f.one(cur,'select count(*)from erp.fg_stock_movements')>0
    assert f.one(cur,'select count(*)from erp.journal_lines')>0
    saved,payload=f.pair(cur,ids[0],ids[1]);request=saved['request_id']
    replay=f.public(cur,'erp_save_sku_action_v1','SAVE_PAIR',json.dumps(payload),request)
    assert replay['replayed']is True and replay['source_group_id']==ids[0]
    assert f.one(cur,'select cp7_sku_conversion.partner_v1(%s)::text',ids[1])==ids[0]
    f.pair(cur,ids[1],ids[0])
    assert f.one(cur,'select count(*)from cp7_sku_conversion.pairs_v1')==1
    f.pair(cur,ids[2],ids[3]);f.pair(cur,ids[0],ids[2])
    assert f.one(cur,'select cp7_sku_conversion.partner_v1(%s)',ids[1])is None
    assert f.one(cur,'select cp7_sku_conversion.partner_v1(%s)',ids[3])is None
    f.pair(cur,ids[2],None)
    assert f.one(cur,'select count(*)from cp7_sku_conversion.pairs_v1')==0
    assert f.native_ledgers(cur)==before
    return dict(status='PASS',Native_ledger_rows_present_before_pair=True,bidirectional=True,reverse_pair_not_duplicated=True,
      old_partners_cleaned=True,delete_from_reverse_side=True,all_stock_HPP_components_journals_and_sale_allocations_exact=True,
      commercial_source_sizes=len(fixture['source_roots']),commercial_target_sizes=len(fixture['target_roots']))

def multilots(cur,today):
    fixture=f.nonpo(cur,today);p,v=f.review(cur,fixture['payload']);key=str(uuid.uuid4());before=f.books(cur)
    assert v['source_stock']==dict(physical=10,reserved=1,available=9),v
    assert v['target_stock']==dict(physical=4,reserved=0,available=4),v
    assert v['source_after']==dict(physical=6,reserved=1,available=5),v
    assert v['target_after']==dict(physical=8,reserved=0,available=8),v
    assert [a['source_lot_id']for a in v['allocations']]==fixture['lots']
    assert [a['qty_pcs']for a in v['allocations']]==[2,2]
    assert D(v['cost']['source_value'])==D('60.06')
    made=f.action(cur,'POST',p,key);after=f.native_ledgers(cur);again=f.action(cur,'POST',p,key)
    assert again==made and f.native_ledgers(cur)==after
    rows=f.allocations(cur,made)
    assert [(a['source_lot_id'],a['qty_pcs'],D(a['unit_hpp']))for a in rows]==[(fixture['lots'][0],2,D('10.01')),(fixture['lots'][1],2,D('20.02'))],rows
    assert sum(D(a['destination_value'])for a in rows)==D('60.06')
    assert sum(D(a['unit_hpp'])*a['qty_pcs']for a in rows)==D('60.06')
    assert f.stocks(cur,fixture['source'],fixture['location'])==v['source_after']
    assert f.stocks(cur,fixture['target'],fixture['location'])==v['target_after']
    assert f.books(cur)==before
    books={p:f.product_books(cur,p)for p in(fixture['source'],fixture['target'])}
    truth=f.b.all_truth(cur);assert all(value==0 for key,value in truth.items()if key.startswith('V2620F_NON_PO_PRODUCT_HPP'))
    return dict(status='PASS',request_id=key,allocations=rows,source_before=v['source_stock'],source_after=v['source_after'],
      target_before=v['target_stock'],target_after=v['target_after'],source_target_exact_value='60.06',Native_books=books,
      replay_no_new_ledger_rows=True,active_sales_reservation_preserved=True,new_FG_average_created=False)

def arbitrary_target(cur,today):
    fixture=f.nonpo(cur,today);p,v=f.review(cur,fixture['payload']);f.action(cur,'POST',p)
    # No counterpart was entered. Actual model and size both differ.
    source_dimensions=cur.execute('select model_id,size_id from erp.products where id=%s',(fixture['source'],)).fetchone()
    target_dimensions=cur.execute('select model_id,size_id from erp.products where id=%s',(fixture['target'],)).fetchone()
    assert source_dimensions[0]!=target_dimensions[0]and source_dimensions[1]!=target_dimensions[1]
    reverse=f.payload(fixture,1,source=fixture['target'],target=fixture['source'],at=fixture['back_at'])
    back,before=f.review(cur,reverse);made=f.action(cur,'POST',back);rows=f.allocations(cur,made)
    assert len(rows)==1 and rows[0]['source_lot_id']==fixture['target_lot']
    assert D(rows[0]['unit_hpp'])==D('30.03')and D(rows[0]['destination_value'])==D('30.03')
    assert before['qty_pcs']==1
    return dict(status='PASS',counterpart_not_required=True,actual_different_model=True,actual_different_size=True,
      manual_back_source_lot=fixture['target_lot'],manual_back_current_source_value='30.03',batch_pairing_not_required=True)

def stale(cur,today):
    fixture=f.nonpo(cur,today);controls={}
    for name,change in(
      ('SOURCE_RESERVATION',lambda:f.reserve(cur,fixture,fixture['source'],1)),
      ('TARGET_STOCK',lambda:f.opening(cur,fixture['target'],1,'30.03',today-timedelta(days=1))),
      ('RESERVATION_TO_POSTED_SALE',None)):
        p,_=f.review(cur,fixture['payload']);cur.execute('savepoint sku29_external_change')
        try:
            if change is not None:change()
            else:
                sale=fixture['reserved_sale'];version=f.one(cur,'select row_version from erp.sales_headers where id=%s',sale)
                f.b.internal(cur,'post_sale_v2',sale,str(uuid.uuid4()),version)
            expected=f.native_ledgers(cur)
            refusal=f.b.refused(cur,lambda:f.action(cur,'POST',p),'STALE_VERSION')
            assert refusal['ok'],(name,refusal)
            assert f.native_ledgers(cur)==expected
            assert f.one(cur,'select count(*)from cp7_sku_conversion.groups_v1')==0
            controls[name]=refusal
        finally:
            cur.execute('rollback to savepoint sku29_external_change');cur.execute('release savepoint sku29_external_change');f.admin(cur)
    same=f.b.refused(cur,lambda:f.preview(cur,f.payload(fixture,target=fixture['source'])),'CP7_SKU_SAME_PRODUCT')
    over=f.b.refused(cur,lambda:f.preview(cur,f.payload(fixture,10)),'CP7_SKU_INSUFFICIENT')
    assert same['ok']and over['ok'],(same,over)
    valid,_=f.review(cur,fixture['payload']);made=f.action(cur,'POST',valid)
    before=f.native_ledgers(cur);statuses=cur.execute('select id,status from erp.product_conversions where id=any(%s::uuid[])order by id',(made['conversion_ids'],)).fetchall()
    commands=[]
    for command in(None,'','UNKNOWN_ACTION'):
        refusal=f.b.refused(cur,lambda command=command:f.action(cur,command,dict(conversion_id=made['conversion_id'],reason='Must not become reverse')),'BE_ACTION_UNKNOWN')
        assert refusal['ok']and f.native_ledgers(cur)==before,refusal
        assert cur.execute('select id,status from erp.product_conversions where id=any(%s::uuid[])order by id',(made['conversion_ids'],)).fetchall()==statuses
        commands.append(dict(action=command,refusal=refusal))
    return dict(status='PASS',controls=controls,same_SKU_zero_effect=same,insufficient_available_zero_effect=over,
      changed_source_target_or_reservation_requires_new_review=True,NULL_blank_unknown_public_commands_existing_group_zero_effect=commands)

def inverse(cur,today):
    fixture=f.nonpo(cur,today);p,v=f.review(cur,fixture['payload']);made=f.action(cur,'POST',p);rows=f.allocations(cur,made)
    # Reserve all four old target pieces, then one actual new piece. Native
    # chooses the equal-time new lots by their IDs; record which part it used
    # rather than inventing an ID order or mutating a posted lot for the test.
    sale=f.reserve(cur,fixture,fixture['target'],5,at=fixture['back_at'])
    blocked_lots=cur.execute("select distinct m.lot_id::text from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id where i.sale_id=%s and m.movement_type='SALE_RESERVE'",(sale,)).fetchall()
    blocked_new=[i+1 for i,row in enumerate(rows)if row['destination_lot_id']in{r[0]for r in blocked_lots}]
    assert blocked_new,(rows,blocked_lots)
    before=f.native_ledgers(cur);reason='Owner29 reverse whole physical correction';payload=dict(conversion_id=made['conversion_id'],reason=reason)
    refusal=f.b.bcp.denied(cur,lambda:f.action(cur,'REVERSE',payload),'downstream')
    assert refusal['ok'],refusal
    assert f.native_ledgers(cur)==before
    direct=f.b.refused(cur,lambda:f.b.internal(cur,'reverse_product_conversion',made['conversion_id'],reason),'CP7_SKU_GROUP_REVERSE_REQUIRED')
    assert direct['ok']and f.native_ledgers(cur)==before,direct
    f.cancel_reservation(cur,sale)
    inverse=f.action(cur,'REVERSE',payload)
    assert len(inverse['conversion_ids'])==2
    assert f.stocks(cur,fixture['source'],fixture['location'])==dict(physical=10,reserved=1,available=9)
    assert f.stocks(cur,fixture['target'],fixture['location'])==dict(physical=4,reserved=0,available=4)
    statuses=cur.execute('select status from erp.product_conversions where id=any(%s::uuid[])',(made['conversion_ids'],)).fetchall()
    assert statuses==[('REVERSED',),('REVERSED',)]
    return dict(status='PASS',group=made['conversion_id'],active_downstream_refusal=refusal,
      Native_direct_partial_inverse_refused=direct,whole_group_reversed_after_real_sale_draft_cancel=True,
      zero_partial_ledger_on_refusal=True,blocked_Native_part_numbers=blocked_new,original_source_reservation_preserved=True)

def mixed(cur,today):
    po=f.be.fixture(cur,today)
    early=f.opening(cur,po['product'],3,'10.01',today-timedelta(days=3))
    p=dict(source_product_id=po['product'],target_product_id=po['target'],location_id=po['location'],qty_pcs=5,
      physical_at=po['payload']['physical_at'],reason='Owner29 mixed opening and production sources')
    source_cost=D(f.one(cur,'select hpp_per_pcs from erp.v_current_hpp where lot_id=%s',po['lot']))
    expected=D('30.03')+2*source_cost;truth=f.b.all_truth(cur);before=f.books(cur)
    frozen,v=f.review(cur,p);made=f.action(cur,'POST',frozen);rows=f.allocations(cur,made)
    assert [(a['source_lot_id'],a['qty_pcs'])for a in rows]==[(early,3),(po['lot'],2)],rows
    assert sum(D(a['destination_value'])for a in rows)==expected
    assert sum(D(a['unit_hpp'])*a['qty_pcs']for a in rows)==expected
    assert f.books(cur)==before
    assert f.b.truth_quiet(truth,f.b.all_truth(cur))
    f.action(cur,'REVERSE',dict(conversion_id=made['conversion_id'],reason='Owner29 Native mixed inverse'))
    assert f.be.qty(cur,early)==3 and f.be.qty(cur,po['lot'])==10
    return dict(status='PASS',Native_PO_and_non_PO_sources=True,allocations=rows,
      expected_source_value=str(expected),existing_PO_source_unit_hpp=str(source_cost),
      quantity_and_exact_lot_value_conserved=True,Native_financial_detectors_unchanged=True)

def legacy_accessories(cur,today):
    result=f.be.actual_usage(cur,today)
    assert result['status']=='PASS',result
    return dict(result,coverage='UNCHANGED_LEGACY_SELECTED_LOT_ACCESSORY_USAGE_AND_INVERSE_ONLY',
      full_manual_group_accessory_recovery_claim=False,expected_returns_first_child_limitation_not_closed=True)

def cases(cur,today):
    return [(name,lambda operation=operation:operation(cur,today))for name,operation in zip(IDS,
      (pairs,multilots,arbitrary_target,stale,inverse,mixed,legacy_accessories))]
