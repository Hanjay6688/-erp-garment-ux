"""Only disposable master setup and native read-back; UI creates/posts receipts."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_procurement_cases as cases
import cp7_material_cases as material

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in ('127.0.0.1','localhost') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    payload=json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        if sys.argv[1] in ('create','create_transfer'):
            f=(material.fixture if sys.argv[1]=='create_transfer' else cases.fixture)(cur,date.fromisoformat(payload['today']))
            f['material_code'],f['unit']=cur.execute('select material_sku,unit_code from erp.materials where id=%s',(f['material'],)).fetchone()
            f['supplier_name']=cur.execute('select supplier_name from erp.suppliers where id=%s',(f['payload']['supplier_id'],)).fetchone()[0]
            conn.commit();out=f
        elif sys.argv[1]=='read':
            h=cur.execute('select id,status,row_version,physical_at from erp.material_purchase_headers where purchase_number=%s',(payload['tag'],)).fetchone()
            qty,count=cases.qty(cur,payload)
            out=dict(qty=str(qty),movement_count=count,document=None,contexts=cur.execute('select count(*) from cp7_procurement.execution_context').fetchone()[0])
            if h:
                ap,grni=cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)',(h[0],h[0])).fetchone()
                out['document']=dict(id=str(h[0]),status=h[1],version=str(h[2]),physical_at=h[3].isoformat(),ap=str(ap),grni=str(grni))
            conn.rollback()
        elif sys.argv[1]=='read_transfer':
            h=cur.execute('select id,status,row_version,physical_at from erp.material_transfers where transfer_number=%s',(payload['tag']+'-UI-TRANSFER',)).fetchone()
            balances={str(loc):str(qty) for loc,qty in cur.execute('select location_id,sum(qty_signed) from erp.material_stock_movements where material_id=%s group by location_id',(payload['material'],)).fetchall()}
            out=dict(balances=balances,document=None,contexts=cur.execute('select count(*) from cp7_material.execution_context').fetchone()[0],
              total_value=str(cur.execute('select sum(sm.qty_signed)*m.moving_average_cost from erp.material_stock_movements sm join erp.materials m on m.id=sm.material_id where m.id=%s group by m.moving_average_cost',(payload['material'],)).fetchone()[0]))
            if h:
                count,net_qty,net_value=cur.execute('select count(*),coalesce(sum(qty_signed),0),coalesce(sum(qty_signed*unit_cost_snapshot),0) from erp.material_stock_movements where source_id=%s',(h[0],)).fetchone()
                out['document']=dict(id=str(h[0]),status=h[1],version=str(h[2]),physical_at=h[3].isoformat(),movements=count,net_qty=str(net_qty),net_value=str(net_value))
            conn.rollback()
        else:raise ValueError('Unknown fixture operation')
    print(json.dumps(out,default=str))

if __name__=='__main__':main()
