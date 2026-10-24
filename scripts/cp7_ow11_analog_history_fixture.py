"""Explicit SYNTHETIC historical Native facts for structural analog controls.

Newly imported products keep their true creation clocks and UNKNOWN history.
Ten additional fixture products represent existing historical comparators.
No capture/registry clock, history result, source hash or coverage is altered.
This is not an all-public-import or factory-history qualification.
"""
import uuid
import cp7_ow11_analog_candidates_cases as private


def seed(cur,imported):
    assert len(imported)==11
    private.plan.b.api.admin(cur)
    cur.execute('set local session_replication_role=replica')
    tag='OW11H-'+uuid.uuid4().hex[:10]
    out=[]
    for n,original in enumerate(imported[1:]):
        root=str(uuid.uuid4())
        cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,
         identity_root_id,effective_from,created_at,is_active,is_portal_visible)
         select %s,%s,model_id,brand_id,'OW11H',size_id,%s,%s,now()-interval'131 days',
          now()-interval'131 days',true,true from erp.products where id=%s""",
                    (root,tag+'-'+str(n),'SYNTHETIC historical comparator '+str(n),root,original['product']))
        location=private.bounded.work.dense.base.retained.formula.sales.fg.base.LOCATION
        cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,
         movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
         values(gen_random_uuid(),%s,null,%s,'GRADE_A','OPENING',800,10,
          'OW11_ANALOG_SYNTHETIC_HISTORY',now()-interval'130 days',now()-interval'130 days')""",(root,location))
        out.append(dict(root=root,target=root+':'+original['target'].split(':')[1]))
    cur.execute('set local session_replication_role=origin')
    return out
