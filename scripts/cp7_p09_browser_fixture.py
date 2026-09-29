"""Only disposable master setup and native read-back; UI creates/posts receipts."""
from datetime import date,timedelta
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_procurement_cases as cases
import cp7_material_cases as material
import cp7_invoice_cases as invoice
import cp7_supplier_return_cases as returns
import cp7_receipt_reversal_cases as reversal

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in ('127.0.0.1','localhost') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    payload=json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        if sys.argv[1] in ('create','create_transfer','create_invoice','create_return'):
            f=(material.fixture if sys.argv[1] in ('create_transfer','create_invoice','create_return') else cases.fixture)(cur,date.fromisoformat(payload['today']))
            f['material_code'],f['unit']=cur.execute('select material_sku,unit_code from erp.materials where id=%s',(f['material'],)).fetchone()
            f['supplier_name']=cur.execute('select supplier_name from erp.suppliers where id=%s',(f['payload']['supplier_id'],)).fetchone()[0]
            if sys.argv[1]=='create_invoice':
                d,_=material.draft(cur,f,at=cases.aa.at(f['day'],11).isoformat());material.post(cur,d)
                f['invoice_received_day']=str(f['day']+timedelta(days=2))
            if sys.argv[1]=='create_return':
                f['item']=str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(f['receipt']['purchase_id'],)).fetchone()[0])
                d,_=material.draft(cur,f);material.post(cur,d)
                invoice.finalize(cur,f,'10','10')
                g=invoice.fixture(cur,date.fromisoformat(payload['today']),final=True)
                f.update(target=g['receipt']['purchase_id'],target_tag=g['tag'],return_day=str(f['day']+timedelta(days=2)))
                f['ap_before']=str(cur.execute("select coalesce(sum(credit_total-debit_total),0) from erp.account_daily_balances where account_id=erp.account_id('AP_SUPPLIER')").fetchone()[0])
            conn.commit();out=f
        elif sys.argv[1]=='create_reverse':
            before=reversal.net_ledger(cur)
            out=invoice.fixture(cur,date.fromisoformat(payload['today']),final=payload['final'])
            out['ledger_before']=before;conn.commit()
        elif sys.argv[1]=='read_reverse':
            h=cur.execute('select status,row_version from erp.material_purchase_headers where id=%s',(payload['receipt']['purchase_id'],)).fetchone()
            qty,count=cases.qty(cur,payload)
            out=dict(status=h[0],version=str(h[1]),qty=str(qty),movement_count=count,ledger=reversal.net_ledger(cur),
              inverse_count=cur.execute('select count(*) from erp.material_stock_movements where material_id=%s and reversal_of_id is not null',(payload['material'],)).fetchone()[0])
            conn.rollback()
        elif sys.argv[1]=='read':
            h=cur.execute('select id,status,row_version,physical_at from erp.material_purchase_headers where purchase_number=%s',(payload['tag'],)).fetchone()
            qty,count=cases.qty(cur,payload)
            out=dict(qty=str(qty),movement_count=count,document=None,contexts=cur.execute('select count(*) from cp7_procurement.execution_context').fetchone()[0])
            if h:
                ap,grni=cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)',(h[0],h[0])).fetchone()
                out['document']=dict(id=str(h[0]),status=h[1],version=str(h[2]),physical_at=h[3].isoformat(),ap=str(ap),grni=str(grni))
            conn.rollback()
        elif sys.argv[1]=='read_invoice':
            purchase=payload['receipt']['purchase_id']
            doc_ap,grni,qty,unit=invoice.amounts(cur,payload)
            out=dict(document_ap=str(doc_ap),grni=str(grni),qty=str(qty),material_value=str(qty*unit),
              balances={str(loc):str(q) for loc,q in cur.execute('select location_id,sum(qty_signed) from erp.material_stock_movements where material_id=%s group by location_id',(payload['material'],)).fetchall()},
              invoices=[dict(id=str(i),number=n,status=st,received_at=at.isoformat(),line_qty=str(q),net_amount=str(v)) for i,n,st,at,q,v in cur.execute('select h.id,h.invoice_number,h.status,h.received_at,sum(l.qty_invoiced),sum(l.net_amount) from erp.material_supplier_invoices h join erp.material_supplier_invoice_lines l on l.invoice_id=h.id join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=%s group by h.id order by h.invoice_number',(purchase,)).fetchall()],
              ap_gl=str(cur.execute("select coalesce(sum(jl.credit-jl.debit),0) from erp.journal_lines jl join erp.journal_entries j on j.id=jl.journal_entry_id join erp.accounting_account_mappings a on a.account_id=jl.account_id where a.mapping_key='AP_SUPPLIER' and j.id in(select unnest(array[f.journal_entry_id,f.adjustment_journal_entry_id]) from erp.supplier_cent_posting_facts f where f.source_type='MATERIAL_SUPPLIER_INVOICE' and f.source_id in(select h.id from erp.material_supplier_invoices h join erp.material_supplier_invoice_lines l on l.invoice_id=h.id join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=%s))",(purchase,)).fetchone()[0]))
            conn.rollback()
        elif sys.argv[1]=='read_return':
            h=cur.execute('select id,status,row_version,physical_at from erp.material_supplier_returns where return_number=%s',(payload['tag']+'-UI-RETURN',)).fetchone()
            ap,grni,qty,unit=invoice.amounts(cur,payload)
            out=dict(source_ap=str(ap),target_ap=str(cur.execute('select erp.material_purchase_final_ap_total(%s)',(payload['target'],)).fetchone()[0]),grni=str(grni),qty=str(qty),material_value=str(qty*unit),
              balances={str(l):str(q) for l,q in cur.execute('select location_id,sum(qty_signed) from erp.material_stock_movements where material_id=%s group by location_id',(payload['material'],)).fetchall()},
              ap_gl=str(cur.execute("select coalesce(sum(credit_total-debit_total),0) from erp.account_daily_balances where account_id=erp.account_id('AP_SUPPLIER')").fetchone()[0]),
              movements=cur.execute("select coalesce(jsonb_agg(jsonb_build_array(id,qty_signed::text,unit_cost_snapshot::text) order by id),'[]'::jsonb) from erp.material_stock_movements where material_id=%s",(payload['material'],)).fetchone()[0],document=None,
              contexts=cur.execute('select count(*) from cp7_supplier_return.execution_context').fetchone()[0])
            if h:
                out['document']=dict(id=str(h[0]),status=h[1],version=str(h[2]),physical_at=h[3].isoformat(),
                  # Inverses identify the original movement, not the return item.
                  # Count both legs through the native reversal lineage.
                  movement_count=cur.execute("with originals as(select m.id from erp.material_stock_movements m join erp.material_supplier_return_items i on i.id=m.source_id where i.return_id=%s and m.source_type='MATERIAL_SUPPLIER_RETURN_ITEM' and m.movement_type='SUPPLIER_RETURN') select count(*) from erp.material_stock_movements m where m.id in(select id from originals) or m.reversal_of_id in(select id from originals)",(h[0],)).fetchone()[0],
                  credit=str(cur.execute('select erp.bf_supplier_credit_source_v1(%s,%s)',(h[0],payload['receipt']['purchase_id'])).fetchone()[0]),
                  moved=str(cur.execute('select coalesce(sum(amount),0) from erp.bf_supplier_credit_moves_v1 where return_id=%s',(h[0],)).fetchone()[0]))
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
