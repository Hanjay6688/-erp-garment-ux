"""Prepared actual-ERP monetary callbacks. Importing these earns no case credit.

All authoritative stock, cost, invoice, sale, return and inverse facts use the
retained Native/public writers. Only masters and drafts are synthetic setup.
The original six moving-average callbacks remain separate and unchanged.
Actual Auth/HTTP, concurrent sessions, automatic rework/redye lifecycle and
the complete owning backup restore are additional required qualifications.
"""
from datetime import datetime,timedelta
from decimal import Decimal as D,ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo
import importlib.util,json,uuid

ROOT=Path(__file__).resolve().parents[2]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module

moving=load('sku_money_retained_six_native',ROOT/'scripts/cp7_sku_moving_average/qualification_cases.py')
n=load('sku_money_retained_native_fixture',ROOT/'scripts/current-sku-group-cost-qualification/native_fixture.py')
f=moving.f

NEW_IDS=(
 'SKU_MONEY_NATIVE_LEGACY_PHYSICAL_OPENING_LATE_INVOICE_CURRENT_INVERSE',
 'SKU_MONEY_NATIVE_LEGACY_PHYSICAL_CONVERTED_LATE_INVOICE_CURRENT_INVERSE',
 'SKU_MONEY_NATIVE_SOLD_LATE_INVOICE_PARTIAL_RETURN_AND_BOTH_INVERSES',
 'SKU_MONEY_NATIVE_BASE_CENT_BEFORE_OPENING_LOT_TRANSFER',
 'SKU_MONEY_NATIVE_BASE_CENT_BEFORE_CONVERTED_LOT_TRANSFER',
 'SKU_MONEY_NATIVE_BASE_CENT_AFTER_CONVERTED_LOT_TRANSFER',
 'SKU_MONEY_NATIVE_RECOVERY_UNDER_PHYSICAL_FIRST_CHILD_LIMIT',
 'SKU_MONEY_NATIVE_RECOVERY_EQUAL_PHYSICAL_FIRST_CHILD_LIMIT',
 'SKU_MONEY_NATIVE_RECOVERY_OVER_PHYSICAL_FIRST_CHILD_LIMIT_REFUSED',
 'SKU_MONEY_NATIVE_LEGACY_OTHER_LOT_STALE_RETURNS_REPLAY_INVERSE',
 'SKU_MONEY_NATIVE_TWO_CHILD_CURRENT_REVISION_POST_COST_AND_INVERSE',
 'SKU_MONEY_NATIVE_SIGNED_RECOVERY_BEFORE_OPENING_LOT_THEN_NATIVE_ZERO',
 'SKU_MONEY_NATIVE_SIGNED_RECOVERY_BEFORE_CONVERTED_LOT_THEN_NATIVE_ZERO',
)
IDS=tuple(moving.IDS)+NEW_IDS

def at(x,seconds=0):
    return(datetime.fromisoformat(x['at'])+timedelta(seconds=seconds)).astimezone(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds')

def exact_book(cur,product,total,fg,cogs=0):
    expected=tuple(map(D,map(str,(total,fg,cogs,0))))
    actual=tuple(map(D,f.product_books(cur,product)));assert actual==expected,(product,expected,actual)
    return[str(x)for x in actual]

def cent_split(total,weights):
    """Independent cumulative integer-cent allocation, predicted before writes."""
    total=D(str(total));weights={str(k):D(str(v))for k,v in weights.items()}
    denominator=sum(weights.values());assert denominator>0 and all(v>0 for v in weights.values())
    result={};cumulative=D(0);previous=D(0)
    for key in sorted(weights):
        cumulative+=weights[key]
        target=(total*cumulative/denominator).quantize(D('.01'),rounding=ROUND_HALF_UP)
        result[key]=target-previous;previous=target
    assert sum(result.values())==total
    return result

def canonical(cur,today,*,expected_returns=None):
    x=moving.canonical(cur,today)
    if expected_returns is None:made,preview=moving.forward(cur,x)
    else:
        payload,preview=f.review(cur,dict(x['payload'],expected_returns=expected_returns))
        assert D(preview['cost']['source_value'])==20
        made=f.action(cur,'POST',payload)
        exact_book(cur,x['source'],60,60);exact_book(cur,x['target'],70,70)
    parts=f.allocations(cur,made);assert len(parts)==1 and parts[0]['qty_pcs']==1
    assert D(parts[0]['unit_hpp'])==10 and D(parts[0]['destination_value'])==10
    x.update(made=made,part=parts[0],next=n.clone_same_dimensions(cur,x['target']))
    return x

def legacy_payload(cur,x,physical,**extra):
    lot=x['target_lot']if physical=='OPENING'else x['part']['destination_lot_id']
    f.admin(cur)
    payload=dict(source_lot_id=lot,target_product_id=x['next'],location_id=x['location'],qty_pcs=1,
        physical_at=at(x,15),reason='Prepared Native economic legacy transfer',
        expected_version=f.one(cur,'select erp.be_source_revision_v1(%s,%s)',lot,x['location']))
    payload.update(extra);return payload

def legacy_post(cur,x,physical,expected='35.00',**extra):
    payload=legacy_payload(cur,x,physical,**extra);preview=f.preview(cur,payload)
    assert D(preview['cost']['source_value'])==D(expected)
    key=str(uuid.uuid4());made=f.action(cur,'POST',payload,key)
    f.admin(cur)
    allocation=cur.execute('select source_lot_id::text,destination_lot_id::text,qty_pcs from erp.product_conversion_allocations where conversion_id=%s',
        (made['conversion_id'],)).fetchone()
    assert allocation[0]==payload['source_lot_id']and allocation[2]==1
    proof=f.one(cur,'select to_jsonb(g)from cp7_sku_conversion.legacy_groups_v4 g where group_id=%s',made['conversion_id'])
    assert proof['source_lot_id']==payload['source_lot_id']and proof['origin_kind']=='FG'and proof['rework_id']is None
    assert proof['original_preview']['source_revision']==payload['expected_version']
    held=n.capture(cur);assert f.action(cur,'POST',payload,key)==made
    replay=n.unchanged(cur,held,'MONEY_LEGACY_POST_REPLAY')
    return made,proof,replay

def usage(cur,x,acc):
    ident=x['made']['conversion_id'];f.admin(cur)
    payload=dict(conversion_id=ident,expected_version=f.one(cur,'select erp.be_conversion_revision_v1(%s)',ident),
        location_id=acc['main'],physical_at=at(x,1),items=[dict(material_id=acc['material'],qty='1')],
        reason='Native sourced cost before economic descendants')
    key=str(uuid.uuid4());result=f.action(cur,'POST_USAGE',payload,key)
    assert result['status']=='POSTED';exact_book(cur,x['target'],72,72)
    held=n.capture(cur);assert f.action(cur,'POST_USAGE',payload,key)==result
    return result,n.unchanged(cur,held,'MONEY_USAGE_REPLAY')

def invoice(cur,acc,today,unit='3.01'):
    payload=dict(invoice_number='SKU-MONEY-'+uuid.uuid4().hex,supplier_id=acc['supplier'],invoice_date=str(today),
        change_reason='Native independent material price2 to'+unit,
        lines=[dict(purchase_item_id=acc['item'],qty_invoiced='100',unit_price=unit)])
    draft=f.b.internal(cur,'save_material_supplier_invoice_draft_v2',json.dumps(payload),str(uuid.uuid4()),None)
    args=(draft['supplier_invoice_id'],str(uuid.uuid4()),draft['row_version'],'Native sourced-cost correction')
    result=f.b.internal(cur,'post_material_supplier_invoice_v2',*args);f.admin(cur)
    held=n.capture(cur);assert f.b.internal(cur,'post_material_supplier_invoice_v2',*args)==result
    return result,n.unchanged(cur,held,'MONEY_INVOICE_REPLAY')

def reverse_conversion(cur,ident):
    return f.action(cur,'REVERSE',dict(conversion_id=ident,reason='Native current monetary inverse'))

def descendant_cost(cur,today,physical):
    x=canonical(cur,today);acc=n.material(cur,today);used,usage_replay=usage(cur,x,acc)
    made,proof,post_replay=legacy_post(cur,x,physical,'36.00')
    for product in(x['target'],x['next']):exact_book(cur,product,36,36)
    original=n.immutable(cur,[x['made']['conversion_id'],made['conversion_id']]);source=n.source_hpp(cur,x)
    allocation=cent_split('3.01',{x['target']:'.5',x['next']:'.5'})
    expected={p:D(35)+v for p,v in allocation.items()}
    posted,invoice_replay=invoice(cur,acc,today)
    for product,value in expected.items():exact_book(cur,product,value,value)
    assert n.immutable(cur,[x['made']['conversion_id'],made['conversion_id']])==original
    assert n.source_hpp(cur,x)==source
    reverse_conversion(cur,made['conversion_id']);exact_book(cur,x['target'],'73.01','73.01');exact_book(cur,x['next'],0,0)
    # Parent's active sourced invoice/usage remains an original Native refusal.
    held=n.capture(cur)
    refusal=n.refused(cur,lambda:reverse_conversion(cur,x['made']['conversion_id']),'BE_REVERSE_DEPENDANTS')
    refused=n.unchanged(cur,held,'MONEY_PARENT_ACTIVE_COST_REFUSAL')
    n.reverse_invoice(cur,posted);exact_book(cur,x['target'],72,72)
    n.bc.reverse(cur,used['cost_document_id'],'Native legitimate usage inverse');exact_book(cur,x['target'],70,70)
    reverse_conversion(cur,x['made']['conversion_id']);exact_book(cur,x['source'],80,80);exact_book(cur,x['target'],50,50)
    return dict(status='PASS',physical_choice=physical,legacy_group=made['conversion_id'],source_request=proof['native_request_id'],
        independent_cent_targets={k:str(v)for k,v in expected.items()},current_descendant_inverse='73.01/0',
        usage_replay=usage_replay,legacy_replay=post_replay,invoice_replay=invoice_replay,
        active_cost_refusal=refusal,complete_refusal=refused,original_cost_guards_and_final_inverse_preserved=True)

def sold_return(cur,today):
    x=canonical(cur,today);acc=n.material(cur,today);usage(cur,x,acc)
    sale=f.reserve(cur,x,x['target'],2,at=x['now'].isoformat());sf=dict(sale=sale,tag='',destination=x['location'])
    payload,version=moving.sales_cmd.review(cur,sf);assert moving.sales_cmd.command(cur,'POST',payload,version)['status']=='POSTED'
    exact_book(cur,x['target'],72,0,72);original=n.immutable(cur,[x['made']['conversion_id']],sale)
    posted,_=invoice(cur,acc,today);exact_book(cur,x['target'],'73.01',0,'73.01')
    assert n.immutable(cur,[x['made']['conversion_id']],sale)==original
    sf['allocations']=moving.sales_returns.read(cur,sf)['page']['rows']
    selected=f.one(cur,'select a.id::text from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s and a.lot_id=%s',sale,x['target_lot'])
    payload,version=moving.sales_returns.payload(cur,sf,qty='1',refund='185000',allocation=selected,destination=x['location'])
    returned=moving.sales_cmd.command(cur,'RETURN',payload,version);ident=returned['return_id']
    exact_book(cur,x['target'],'73.01','36.51','36.50')
    f.admin(cur);snapshot=cur.execute('select to_jsonb(v)from cp7_sku_conversion.sales_return_values_v2 v where return_id=%s',(ident,)).fetchall()
    assert sum(D(str(v[0]['effective_value']))for v in snapshot)==D('36.51')
    n.reverse_invoice(cur,posted);exact_book(cur,x['target'],72,36,36)
    f.admin(cur);assert cur.execute('select to_jsonb(v)from cp7_sku_conversion.sales_return_values_v2 v where return_id=%s',(ident,)).fetchall()==snapshot
    assert moving.sales_returns.inverse(cur,sf,ident)['return_status']=='REVERSED';exact_book(cur,x['target'],72,0,72)
    assert moving.sales_returns.reverse_sale(cur,sf)['status']=='REVERSED';exact_book(cur,x['target'],72,72)
    return dict(status='PASS',sale_id=sale,return_id=ident,late_invoice_COGS='73.01',partial_return='36.51',
        remaining_COGS='36.50',invoice_inverse_FG_COGS=['36.00','36.00'],posted_return_snapshot_immutable=True,
        current_return_and_sale_inverses_restore_FG='72.00')

def base_price(cur,today,physical,when):
    x=canonical(cur,today)
    if when=='BEFORE':
        f.b.internal(cur,'post_opening_hpp_correction',x['target_lot'],D('50.01'),'Native base cents before transfer',today)
        exact_book(cur,x['target'],'70.01','70.01')
        made,_,_=legacy_post(cur,x,physical,'35.01');expected={x['target']:D(35),x['next']:D('35.01')}
    else:
        assert physical=='CONVERTED','Original physically used opening guard remains required'
        made,_,_=legacy_post(cur,x,physical)
        expected={p:D(10)+v for p,v in cent_split('50.01',{x['target']:'.5',x['next']:'.5'}).items()}
        f.b.internal(cur,'post_opening_hpp_correction',x['target_lot'],D('50.01'),'Native base cents after transfer',today)
    for product,value in expected.items():exact_book(cur,product,value,value)
    reverse_conversion(cur,made['conversion_id']);exact_book(cur,x['target'],'70.01','70.01');exact_book(cur,x['next'],0,0)
    return dict(status='PASS',physical_choice=physical,source_price_timing=when,
        independent_targets={k:str(v)for k,v in expected.items()},current_inverse=['70.01','0.00'])

def recovery(cur,today,unit):
    acc=n.material(cur,today,cost=unit,recovery=True)
    x=canonical(cur,today,expected_returns=[dict(material_id=acc['material'],qty='1',holder='Native bounded cost source')])
    f.admin(cur);outstanding=f.one(cur,'select outstanding_id::text from erp.be_conversion_returns_v1 where conversion_id=%s',x['made']['conversion_id'])
    lot=n.bc.receive(cur,acc,'TEARDOWN',[(1,outstanding)],physical_at=at(x,20),reference='Native exact first-child recovery')['lot_ids'][0]
    n.bc.inspect(cur,lot,at(x,30),'Native money recovery inspector',usable=1)
    payload=dict(lot_id=lot,condition='USABLE',qty='1',unit_value=unit,location_id=acc['main'],physical_at=at(x,40),reason='Native first-child physical limit unchanged')
    before=n.books(cur);facts=n.immutable(cur,[x['made']['conversion_id']]);key=str(uuid.uuid4())
    if unit=='10.01':
        held=n.capture(cur);refusal=n.refused(cur,lambda:n.bc.svc(cur,'VALUE_CUSTODY',payload,key=key),'BE_RECOVERY_EXCEEDS_VALUE')
        proof=n.unchanged(cur,held,'MONEY_RECOVERY_PHYSICAL_LIMIT')
        exact_book(cur,x['target'],70,70)
        return dict(status='PASS',unit=unit,physical_first_child_value='10.00',economic_pool_value='70.00',
            existing_guard_not_relaxed=True,refusal=refusal,complete_refusal=proof)
    result=n.bc.svc(cur,'VALUE_CUSTODY',payload,key=key);assert result['status']=='POSTED'
    expected=D(70)-D(unit);exact_book(cur,x['target'],expected,expected)
    assert f.b.lot_value(cur,x['part']['destination_lot_id'])==D(10)-D(unit)
    held=n.capture(cur);assert n.bc.svc(cur,'VALUE_CUSTODY',payload,key=key)==result
    replay=n.unchanged(cur,held,'MONEY_RECOVERY_REPLAY')
    assert n.immutable(cur,[x['made']['conversion_id']])==facts
    n.bc.reverse(cur,key,'Native signed recovery inverse');exact_book(cur,x['target'],70,70)
    assert n.books(cur)==before and n.immutable(cur,[x['made']['conversion_id']])==facts
    return dict(status='PASS',unit=unit,expected_economic_pool=str(expected),physical_first_child_after=str(D(10)-D(unit)),
        replay=replay,legitimate_Native_recovery_inverse_exact=True)

def legacy_stale(cur,today):
    x=canonical(cur,today);acc=n.material(cur,today)
    returns=[dict(material_id=acc['material'],qty='1',holder='Native legacy expected return')]
    old=legacy_payload(cur,x,'CONVERTED',expected_returns=returns)
    f.b.internal(cur,'post_opening_hpp_correction',x['target_lot'],D('50.01'),'Native other physical lot correction',today)
    held=n.capture(cur);refusal=n.refused(cur,lambda:f.action(cur,'POST',old),'STALE_VERSION')
    proof=n.unchanged(cur,held,'MONEY_LEGACY_STALE_OTHER_PHYSICAL_LOT')
    made,_,replay=legacy_post(cur,x,'CONVERTED','35.01',expected_returns=returns)
    assert made['pending_returns']==1;exact_book(cur,x['target'],35,35);exact_book(cur,x['next'],'35.01','35.01')
    reverse_conversion(cur,made['conversion_id']);exact_book(cur,x['target'],'70.01','70.01');exact_book(cur,x['next'],0,0)
    f.admin(cur)
    assert f.one(cur,'select status from erp.bc_outstanding_returns_v1 where id=(select outstanding_id from erp.be_conversion_returns_v1 where conversion_id=%s)',made['conversion_id'])=='CANCELLED'
    return dict(status='PASS',old_other_lot_revision_refused=refusal,complete_stale_refusal=proof,
        fresh_legacy_replay=replay,original_expected_return_created_and_cancelled=True)

def two_child(cur,today):
    x=canonical(cur,today);acc=n.material(cur,today);used,_=usage(cur,x,acc)
    payload,preview=f.review(cur,f.payload(x,2,source=x['target'],target=x['next'],at=at(x,15)))
    assert len(preview['allocations'])==2 and D(preview['cost']['source_value'])==72
    made=f.action(cur,'POST',payload);assert len(made['conversion_ids'])==2
    exact_book(cur,x['target'],0,0);exact_book(cur,x['next'],72,72)
    posted,_=invoice(cur,acc,today);exact_book(cur,x['target'],0,0);exact_book(cur,x['next'],'73.01','73.01')
    reverse_conversion(cur,made['conversion_id']);exact_book(cur,x['target'],'73.01','73.01');exact_book(cur,x['next'],0,0)
    n.reverse_invoice(cur,posted);n.bc.reverse(cur,used['cost_document_id'],'Native source cost inverse after both children')
    exact_book(cur,x['target'],70,70)
    return dict(status='PASS',group_id=made['conversion_id'],members=made['conversion_ids'],
        actual_two_Native_children=True,late_cost_total='73.01',current_group_inverse_exact=True)

def signed_before(cur,today,physical):
    acc=n.material(cur,today,cost='2.01',recovery=True)
    x=canonical(cur,today,expected_returns=[dict(material_id=acc['material'],qty='1',holder='Native signed-cost source')])
    f.admin(cur);outstanding=f.one(cur,'select outstanding_id::text from erp.be_conversion_returns_v1 where conversion_id=%s',x['made']['conversion_id'])
    lot=n.bc.receive(cur,acc,'TEARDOWN',[(1,outstanding)],physical_at=at(x,20),reference='Native signed source before transfer')['lot_ids'][0]
    n.bc.inspect(cur,lot,at(x,30),'Native signed-source inspector',usable=1)
    payload=dict(lot_id=lot,condition='USABLE',qty='1',unit_value='2.01',location_id=acc['main'],physical_at=at(x,40),reason='Native signed source before both physical choices')
    before=n.books(cur);key=str(uuid.uuid4())
    result=n.bc.svc(cur,'VALUE_CUSTODY',payload,key=key);assert result['status']=='POSTED'
    exact_book(cur,x['target'],'67.99','67.99')
    made,_,replay=legacy_post(cur,x,physical,'34.00',physical_at=at(x,50))
    exact_book(cur,x['target'],'33.99','33.99');exact_book(cur,x['next'],34,34)
    facts=n.immutable(cur,[x['made']['conversion_id'],made['conversion_id']])
    # This is the original BC inverse, not a direct change to a posted cost.
    # Both base values must return to35 when the independent recovery becomes0.
    n.bc.reverse(cur,key,'Native recovery inverse with live economic descendant')
    exact_book(cur,x['target'],35,35);exact_book(cur,x['next'],35,35)
    assert n.books(cur)==before and n.immutable(cur,[x['made']['conversion_id'],made['conversion_id']])==facts
    assert n.bc.stock(cur,acc['material'],acc['main'])==100
    assert n.bc.lot_state(cur,lot)['usable']==1
    reverse_conversion(cur,made['conversion_id']);exact_book(cur,x['target'],70,70);exact_book(cur,x['next'],0,0)
    return dict(status='PASS',physical_choice=physical,recovery='-2.01',forward=['33.99','34.00'],
        Native_recovery_inverse_with_active_descendant=['35.00','35.00'],current_conversion_inverse=['70.00','0.00'],
        base_cents_not_scaled_by_signed_net_value=True,posted_facts_unchanged=True,legacy_replay=replay)

def cases(cur,today):
    n.require_local(cur)
    retained=moving.cases(cur,today);assert tuple(key for key,_ in retained)==tuple(moving.IDS)
    operations=(lambda:descendant_cost(cur,today,'OPENING'),lambda:descendant_cost(cur,today,'CONVERTED'),
        lambda:sold_return(cur,today),lambda:base_price(cur,today,'OPENING','BEFORE'),
        lambda:base_price(cur,today,'CONVERTED','BEFORE'),lambda:base_price(cur,today,'CONVERTED','AFTER'),
        lambda:recovery(cur,today,'9.99'),lambda:recovery(cur,today,'10.00'),lambda:recovery(cur,today,'10.01'),
        lambda:legacy_stale(cur,today),lambda:two_child(cur,today),
        lambda:signed_before(cur,today,'OPENING'),lambda:signed_before(cur,today,'CONVERTED'))
    assert len(operations)==len(NEW_IDS)and len(set(IDS))==19
    return retained+list(zip(NEW_IDS,operations))
