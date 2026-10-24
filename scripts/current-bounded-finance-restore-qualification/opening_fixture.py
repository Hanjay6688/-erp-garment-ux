"""Explicit synthetic historical masters; every stock/cache/HPP/GL fact is Native.

The ten NEW comparator masters have declared historical identity clocks. No
existing product or source clock is edited. New imports retain their real clocks.
No production, laundry or work is needed to exercise confirmation metadata.
"""
from datetime import timedelta
from decimal import Decimal
import uuid
import cp7_ow11_analog_choice_cases as analog
import cp6_af_independent_review as owner


def ready(cur,day):
    value=owner.confidence(cur,day)
    assert value['data_confidence']['status']=='READY',value
    assert value['financial_position']['balance_difference']==0,value
    analog.plan.b.api.admin(cur)
    return value


def protected_rows(cur,table):
    zone=cur.execute('show TimeZone').fetchone()[0]
    cur.execute("set local TimeZone='UTC'")
    try:return cur.execute('select to_jsonb(t)from erp.'+table+' t order by id').fetchall()
    finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))


def prepare(cur,today,report):
    day=today-timedelta(days=4)
    report['before']=ready(cur,day)
    imported=analog.volume.import_batch(cur,today,11,analog.volume.Phases())
    report['after_public_import']=ready(cur,day)
    admin=analog.plan.b.api.admin
    admin(cur)
    protected=('work_completion_events','work_completion_lines','laundry_deliveries',
               'laundry_delivery_lines','laundry_receipts','laundry_receipt_lines',
               'payroll_settlements','payroll_work_items','attendance_hpp_pools')
    before={t:protected_rows(cur,t)for t in protected}
    product_clocks=cur.execute('select id::text,created_at,effective_from from erp.products order by id').fetchall()
    # Explicit new synthetic master rows, as in the frozen B historical fixture.
    # Replica applies to these ten masters ONLY. All Native posting below runs
    # with origin triggers, current OWNER permissions and unchanged source SQL.
    assert cur.execute('show session_replication_role').fetchone()==('origin',)
    cur.execute('set local session_replication_role=replica')
    tag='OW11N-'+uuid.uuid4().hex[:10]
    historical=[]
    try:
        for n,original in enumerate(imported[1:]):
            root=str(uuid.uuid4())
            cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,
                identity_root_id,effective_from,created_at,is_active,is_portal_visible)
                select %s,%s,model_id,brand_id,'OW11N',size_id,%s,%s,now()-interval'131 days',
                now()-interval'131 days',true,true from erp.products where id=%s""",
                (root,tag+'-'+str(n),'SYNTHETIC Native-stock comparator '+str(n),root,original['product']))
            assert cur.rowcount==1
            historical.append(dict(root=root,target=root+':'+original['target'].split(':')[1]))
    finally:cur.execute('set local session_replication_role=origin')
    header=uuid.uuid4();location=imported[0]['location']
    owner.ordinary(cur)
    cur.execute("insert into erp.opening_balance_headers(id,opening_number,opening_date,status)values(%s,%s,%s,'DRAFT')",
                (header,tag,day))
    for product in historical:
        cur.execute("""insert into erp.opening_balance_items
            (opening_id,balance_type,product_id,location_id,qty,unit_cost_snapshot,quality_grade,hpp_input_method)
            values(%s,'FINISHED_GOODS',%s,%s,800,10,'GRADE_A','MANUAL')""",
            (header,product['root'],location))
    assert cur.execute('show session_replication_role').fetchone()==('origin',)
    cur.execute('select erp.post_opening_balance(%s)',(header,))
    admin(cur)
    assert cur.execute('select status from erp.opening_balance_headers where id=%s',(header,)).fetchone()==('POSTED',)
    roots=[p['root']for p in historical]
    balances=cur.execute("""select p.id::text,
        (select sum(m.qty_signed)from erp.fg_stock_movements m where m.product_id=p.id),
        (select sum(b.cached_qty_pcs)from erp.fg_inventory_balances b where b.product_id=p.id),
        (select sum(l.initial_qty_pcs)from erp.fg_lots l where l.product_id=p.id),
        (select sum(h.total_cost)from erp.hpp_versions h join erp.fg_lots l on l.id=h.lot_id
          where l.product_id=p.id and h.is_current)
        from erp.products p where p.id=any(%s::uuid[])order by p.id""",(roots,)).fetchall()
    assert len(balances)==10 and all(r[1:]==(800,800,800,Decimal('8000'))for r in balances),balances
    journals=cur.execute("""select j.source_type,j.status,sum(l.debit),sum(l.credit)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_id=%s group by j.source_type,j.status""",(header,)).fetchall()
    assert len(journals)==1 and journals[0][1:]==('POSTED',Decimal('80000'),Decimal('80000')),journals
    report.update(historical_master_fixture='TEN_NEW_SYNTHETIC_MASTERS_WITH_DECLARED_131_DAY_CLOCKS',
        historical_products=historical,opening_header=str(header),opening_day=str(day),
        Native_stock_cache_lots_HPP=balances,Native_balanced_journal=journals,
        stock_inserted_directly=False,existing_source_clocks_changed=False,
        new_import_creation_clocks_changed=False)
    report['after_Native_opening']=ready(cur,day)
    target=imported[0]['target'];source=next(p['target']for p in historical if p['target'].split(':')[1]==target.split(':')[1])
    analog.plan.previous.select_profiles(cur,imported[0]['root'],True)
    analog.reader.explicit_profile(cur,imported[0]['root'])
    analog.plan.plan.review_work(cur,today)
    report['after_explicit_planning_reviews']=ready(cur,day)
    for t in protected:
        assert protected_rows(cur,t)==before[t],('UNRELATED_PRODUCTION_SOURCE_CHANGED',t)
    assert cur.execute('select id::text,created_at,effective_from from erp.products where id=any(%s::uuid[])order by id',([p[0]for p in product_clocks],)).fetchall()==product_clocks
    report['production_laundry_work_payroll_and_HPP_pools_unchanged']=True
    x=dict(root=imported[0]['root'],target=target)
    f=analog.reader.from_current(cur,today,x)
    analog.bounded.finish(cur,f)
    f.update(target=target,source=source,imported=imported,size=None)
    f['payload']=dict(contract_version='cp7.product-analog-choice-command.v1',source_request=f['key'],
        source_hash=f['pages']['reference']['source_hash'],access_epoch=f['pages']['access_epoch'],
        target_key=target,source_key=source,scale_factor='1.25',
        reason='Explicit SYNTHETIC Native-stock comparison; not an owner factory setting',reviewed=True,
        expected_revision='0',action='CONFIRM')
    report['after_actual_bounded_DONE']=ready(cur,day)
    return f
