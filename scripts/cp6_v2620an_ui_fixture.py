#!/usr/bin/env python3
"""Synthetic masters and genuine receipt; caller creates every draft over HTTP."""
from datetime import timedelta
import json,os,sys,uuid
import psycopg

def run():
    pg=os.environ['CP6_AUTH_PGURL'];assert pg=='postgresql://postgres:postgres@127.0.0.1:54322/cp6_auth'
    actor=str(uuid.UUID(sys.argv[1]));prefix='ZZ-AN-'+uuid.uuid4().hex[:12]
    with psycopg.connect(pg) as conn,conn.cursor() as cur:
        assert cur.execute('select current_database()').fetchone()[0]=='cp6_auth'
        now=cur.execute('select clock_timestamp()').fetchone()[0]
        model,contractor=cur.execute("select model_id,contractor_id from erp.production_orders where po_number='CP6-RACE-PO'").fetchone()
        pattern=cur.execute('select id from erp.production_patterns where is_active order by pattern_code limit 1').fetchone()[0]
        size,size_code=cur.execute('select s.id,s.size_code from erp.product_model_sizes m join erp.sizes s on s.id=m.size_id where m.model_id=%s and s.is_active order by s.sort_order limit 1',(model,)).fetchone()
        supplier=cur.execute("select id from erp.suppliers where supplier_code='CP6-RACE-SUP'").fetchone()[0]
        material=cur.execute("insert into erp.materials(material_sku,material_name,material_type,unit_code) values(%s,'AN selector fabric','FABRIC','yd') returning id",(prefix,)).fetchone()[0]
        location=cur.execute("insert into erp.locations(location_code,location_name,location_type,is_active) values(%s,'AN selector warehouse','RAW_MATERIAL_WAREHOUSE',true) returning id",(prefix,)).fetchone()[0]
        orders=[]
        for i in range(201):
            number=prefix+'-'+str(i).zfill(4)
            po=cur.execute("insert into erp.production_orders(po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at,notes) values(%s,%s,%s,%s,'CUTTING','CUTTING',%s,'AN synthetic selector case') returning id",(number,model,contractor,101 if i==200 else 1,now-timedelta(minutes=8))).fetchone()[0]
            orders.append(dict(id=po,number=number))
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=actor,role='authenticated')),))
        receipt=dict(purchase_number=prefix+'-BUY',supplier_id=supplier,location_id=location,physical_at=now-timedelta(minutes=10),change_reason='AN 101 real rolls for independent draft paging',
            lines=[dict(material_id=material,qty=101,unit_price=1,price_state='ESTIMATED',price_source='MANUAL_ESTIMATE',
                rolls=[dict(roll_number=prefix+'-R'+str(i).zfill(3),qty=1) for i in range(101)])])
        saved=cur.execute('select erp.save_material_purchase_draft_v2(%s::jsonb,%s,null)',(json.dumps(receipt,default=str),uuid.uuid4())).fetchone()[0]
        cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(saved['purchase_id'],uuid.uuid4(),saved['row_version'],'AN ordinary receipt'))
        rolls=cur.execute('select r.id,r.roll_number from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s order by r.roll_number',(saved['purchase_id'],)).fetchall()
        assert len(rolls)==101
        payloads=[dict(action='SAVE_DRAFT',po_id=orders[-1]['id'],pattern_id=pattern,source_location_id=location,
            cut_at=now-timedelta(minutes=5),change_reason='AN ordinary draft beyond original display limits',
            size_slots=[dict(slot_no=1,size_id=size,drawing_no=1)],
            rolls=[dict(roll_id=rid,qty_issued=1,qty_consumed=1,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=1)])]) for rid,_ in rolls]
        return dict(prefix=prefix,po=orders[-1]['id'],po_number=orders[-1]['number'],model=model,location=location,material=material,
            size=size,size_code=size_code,roll=rolls[0][0],roll_number=rolls[0][1],payloads=payloads)

if __name__=='__main__':print(json.dumps(run(),default=str))
