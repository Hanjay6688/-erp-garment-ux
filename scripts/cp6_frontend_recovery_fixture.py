#!/usr/bin/env python3
"""Seed masters/drafts only; real purchase posting establishes the roll ledger.

Only the disposable Auth clone is admitted. No installed function/guard/ACL is
changed. Posted facts remain until whole-clone disposal by the parent workflow.
"""
import json
import os
import sys
import uuid
from datetime import timedelta

import psycopg


def main():
    pg = os.environ['CP6_AUTH_PGURL']
    assert pg == 'postgresql://postgres:postgres@127.0.0.1:54322/cp6_auth'
    actor = str(uuid.UUID(sys.argv[1]))
    with psycopg.connect(pg) as connection, connection.cursor() as cur:
        assert cur.execute('select current_database()').fetchone()[0] == 'cp6_auth'
        now = cur.execute('select clock_timestamp()').fetchone()[0]
        material, location, po = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        number = 'CP6-REC-' + po.hex[:12]
        roll_number = number + '-ROLL'
        model, contractor = cur.execute("select model_id,contractor_id from erp.production_orders where po_number='CP6-RACE-PO'").fetchone()
        pattern = cur.execute("select id from erp.production_patterns where is_active order by pattern_code limit 1").fetchone()[0]
        size, size_code = cur.execute('select s.id,s.size_code from erp.product_model_sizes m join erp.sizes s on s.id=m.size_id where m.model_id=%s and s.is_active order by s.sort_order limit 1', (model,)).fetchone()
        supplier = cur.execute("select id from erp.suppliers where supplier_code='CP6-RACE-SUP'").fetchone()[0]
        cur.execute("insert into erp.materials(id,material_sku,material_name,material_type,unit_code) values(%s,%s,'Recovery fixture fabric','FABRIC','yd')", (material, number+'-FAB'))
        cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'Recovery fixture warehouse','RAW_MATERIAL_WAREHOUSE',true)", (location, number+'-LOC'))
        cur.execute("insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at,notes) values(%s,%s,%s,%s,10,'CUTTING','CUTTING',%s,'Disposable UI recovery fixture')", (po,number,model,contractor,now-timedelta(minutes=8)))
        cur.execute("select set_config('request.jwt.claims',%s,true)", (json.dumps({'role':'authenticated','sub':actor}),))
        # Foundation receipt uses the admitted internal purchase API in this
        # disposable fixture session. The caller creates the Cutting draft
        # through real Auth/HTTP, without changing session authorization here.
        purchase_payload = dict(purchase_number=number+'-BUY',supplier_id=supplier,location_id=location,
            physical_at=now-timedelta(minutes=10),change_reason='Recovery fixture received ten yards',
            lines=[dict(material_id=material,qty=10,unit_price=10,price_state='ESTIMATED',price_source='MANUAL_ESTIMATE',rolls=[dict(roll_number=roll_number,qty=10)])])
        purchase = cur.execute('select erp.save_material_purchase_draft_v2(%s::jsonb,%s,null)',(json.dumps(purchase_payload,default=str),uuid.uuid4())).fetchone()[0]
        cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(purchase['purchase_id'],uuid.uuid4(),purchase['row_version'],'Recovery fixture ordinary purchase post'))
        roll = cur.execute('select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s',(purchase['purchase_id'],)).fetchone()[0]
        cut_payload = dict(action='SAVE_DRAFT',po_id=po,pattern_id=pattern,source_location_id=location,
            cut_at=now-timedelta(minutes=5),change_reason='Recovery fixture exact ten-piece cut',
            size_slots=[dict(slot_no=1,size_id=size,drawing_no=1)],
            rolls=[dict(roll_id=roll,qty_issued=10,qty_consumed=10,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=10)])])
        result = dict(po=po,po_number=number,cut_payload=cut_payload,roll=roll,
            roll_number=roll_number,material=material,location=location,contractor=contractor,size=size,size_code=size_code,
            physical_pickup=(now-timedelta(minutes=2)).isoformat(),expected_cut_pcs=10,expected_cost=100)
    print(json.dumps(result,default=str))


if __name__ == '__main__':
    main()
