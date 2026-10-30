"""Two additional actual Native callbacks, PREPARED until the full runner runs.

No posted facts, price clocks or cost rows are seeded. All business writes use
the retained public Native conversion/BC APIs and immutable Native fixtures.
"""
from datetime import datetime,timedelta
from decimal import Decimal as D
from zoneinfo import ZoneInfo
import uuid

IDS=('SKU30_RECOVERY_UNDER_FIRST_PART_NATIVE_POST_REPLAY_INVERSE',
     'SKU30_RECOVERY_EQUAL_FIRST_PART_NATIVE_POST_REPLAY_INVERSE')

def bc_at(fixture,seconds):
    value=datetime.fromisoformat(fixture['at'])+timedelta(seconds=seconds)
    assert value.tzinfo is not None,'SKU27_BC_AWARE_CLOCK_REQUIRED'
    return value.astimezone(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds')

def prepared(cur,today,n,unit):
    fixture=n.f.nonpo(cur,today);accessory=n.material(cur,today,cost=unit,recovery=True)
    made,parts=n.make_group(cur,fixture,[dict(material_id=accessory['material'],qty='1',holder='SKU30 bounded recovery')])
    assert n.values(cur,parts)==(D('20.02'),D('40.04'))
    links=cur.execute('select conversion_id::text,outstanding_id::text from erp.be_conversion_returns_v1 where conversion_id=any(%s::uuid[])order by conversion_id',
                      (made['conversion_ids'],)).fetchall()
    assert len(links)==1 and links[0][0]==parts[0]['conversion_id'],links
    lot=n.bc.receive(cur,accessory,'TEARDOWN',[(1,links[0][1])],physical_at=bc_at(fixture,20),reference='SKU30 Native recovery')['lot_ids'][0]
    n.bc.inspect(cur,lot,bc_at(fixture,30),'SKU30 Native inspector',usable=1)
    payload=dict(lot_id=lot,condition='USABLE',qty='1',unit_value=unit,location_id=accessory['main'],physical_at=bc_at(fixture,40),reason='SKU30 bounded Native recovery '+unit)
    return dict(fixture=fixture,accessory=accessory,made=made,parts=parts,lot=lot,payload=payload,request=str(uuid.uuid4()))

def positive(cur,today,n,unit):
    assert unit in('20.01','20.02');n.require_local(cur)
    f=prepared(cur,today,n,unit);parts=f['parts'];expected=D('0.01')if unit=='20.01'else D('0.00')
    before_books=n.books(cur);source=n.source_hpp(cur,f['fixture']);immutable=n.immutable(cur,f['made']['conversion_ids'])
    truth=n.f.b.all_truth(cur);assert n.bc.stock(cur,f['accessory']['material'],f['accessory']['main'])==100
    result=n.bc.svc(cur,'VALUE_CUSTODY',f['payload'],key=f['request'])
    assert result['status']=='POSTED'and result['document_id']==f['request']and D(result['value'])==D(unit),result
    assert n.values(cur,parts)==(expected,D('40.04'))
    hpp=cur.execute('select qty_basis_pcs,total_cost,hpp_per_pcs from erp.v_current_hpp where lot_id=%s',(parts[0]['destination_lot_id'],)).fetchone()
    assert hpp==(2,expected,D('0.005000')if unit=='20.01'else D('0.000000')),hpp
    assert n.bc.stock(cur,f['accessory']['material'],f['accessory']['main'])==101
    after=n.books(cur)
    assert after['MATERIAL_INVENTORY']-before_books['MATERIAL_INVENTORY']==D(unit)
    assert after['FG_INVENTORY']-before_books['FG_INVENTORY']==-D(unit)
    assert all(after[k]==before_books[k]for k in('COGS','WIP','OTHER_INCOME','OTHER_EXPENSE'))
    assert n.source_hpp(cur,f['fixture'])==source and n.immutable(cur,f['made']['conversion_ids'])==immutable
    assert n.f.b.truth_quiet(truth,n.f.b.all_truth(cur))
    held=n.capture(cur);assert n.bc.svc(cur,'VALUE_CUSTODY',f['payload'],key=f['request'])==result
    replay=n.unchanged(cur,held,'RECOVERY_'+('UNDER'if unit=='20.01'else'EQUAL')+'_SAME_UUID_REPLAY')
    n.bc.reverse(cur,f['request'],'SKU30 legitimate bounded recovery inverse')
    assert n.values(cur,parts)==(D('20.02'),D('40.04'))and n.statuses(cur,parts)==['POSTED','POSTED']
    assert n.bc.stock(cur,f['accessory']['material'],f['accessory']['main'])==100 and n.books(cur)==before_books
    assert n.bc.lot_state(cur,f['lot'])['usable']==1
    assert n.source_hpp(cur,f['fixture'])==source and n.immutable(cur,f['made']['conversion_ids'])==immutable
    assert n.f.b.truth_quiet(truth,n.f.b.all_truth(cur))
    return dict(status='PASS',scope='ACTUAL_NATIVE_FIRST_PART_BOUNDED_RECOVERY_NOT_WHOLE_GROUP_ALLOCATION',unit=unit,
      pending_recovery=unit,first_part_before='20.02',first_part_after=str(expected),second_part_unchanged='40.04',
      literal_hpp=[str(x)for x in hpp],Native_material_stock_before=100,Native_material_stock_after=101,Native_material_stock_after_inverse=100,
      Native_material_GL_delta=unit,Native_FG_GL_delta=str(-D(unit)),Native_other_GL_unchanged=True,
      immutable_complete_source_and_conversion_facts=True,exact_UUID_replay_full_current_census=replay,
      legitimate_Native_inverse_restores_HPP_stock_and_accounts=True,whole_group_recovery_capability=False)

def cases(cur,today,*,native_fixture):
    return[(name,lambda unit=unit:positive(cur,today,native_fixture,unit))for name,unit in zip(IDS,('20.01','20.02'))]
