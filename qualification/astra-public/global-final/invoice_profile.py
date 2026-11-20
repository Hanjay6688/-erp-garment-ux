"""Replay the supported maximum on a smaller opening book and record the business state surrounding POST."""
from common import *
from datetime import timedelta
from time import perf_counter
import re
import cp7_p19_scale_cases as scale
import cp7_sales_command_cases as sales

def fingerprint(cur):
    admin(cur)
    names=['erp.sales_headers','erp.sales_items','erp.journal_entries','erp.journal_lines','erp.fg_stock_movements','erp.hpp_versions','erp.cost_recalc_queue']
    result={}
    for name in names:
        row=cur.execute("select count(*),md5(coalesce(string_agg(h,'' order by h),'')) from (select md5(to_jsonb(t)::text) h from "+name+" t) a").fetchone()
        result[name]=dict(rows=row[0],md5=row[1])
    return result

def run():
    report=dict(separate_from_512_target_load=True,case='100-line operator invoice on a smaller book',lines=100,statement_timeout_ms=8000,save_target_ms=2000)
    with psycopg.connect(**db()) as conn,conn.cursor() as q:
        report['seal']=measure_seal(q)
        owner,_=actors(q);conn.commit()
        log=scale.Phases();log.commit=conn.commit
        rows=scale.import_batch(q,TODAY,100,log);same=rows[0]
        report['current_targets']=len(scale.current_targets(q))
        tag='A25-ISO-'+uuid.uuid4().hex[:12]
        at=(datetime.now(ZoneInfo('Asia/Jakarta'))-timedelta(minutes=1)).isoformat()
        payload=dict(sale_number=tag,customer_id=same['customer'],source_location_id=same['location'],sale_date=at,due_date=None,payment_terms='Uji pengesahan nota dari layar penjualan',notes='Uji sintetis',change_reason='Pemilik memeriksa jumlah dan harga setiap barang',items=[dict(product_id=r['product'],qty_pcs='1',unit_price_snapshot='20',discount_amount='0',notes='Uji sintetis') for r in rows])
        t=perf_counter();q.execute("set local statement_timeout='8s'");draft=sales.command(q,'CREATE',payload,None,subject=owner);conn.commit()
        report['create_ms']=round((perf_counter()-t)*1000,3);f=dict(tag=tag,sale=draft['sale_id'])
        review,v=sales.review(q,f);before=fingerprint(q);conn.commit()
        report['before_post']=before;report['sale_id']=f['sale'];save('diagnosis-invoice',report)
        t=perf_counter()
        try:
            q.execute("set local statement_timeout='8s'")
            resp=sales.command(q,'POST',review,v,subject=owner);conn.commit()
            report['post']=dict(outcome='COMMIT',ms=round((perf_counter()-t)*1000,3),status=resp['status'])
        except psycopg.Error as e:
            elapsed=round((perf_counter()-t)*1000,3)
            names=re.findall(r'(?:PL/pgSQL|SQL) function "?([a-zA-Z_0-9.]+)',e.diag.context or '')
            report['post']=dict(outcome='ROLLBACK',ms=elapsed,sqlstate=e.sqlstate,reason=e.diag.message_primary,routines=names)
            conn.rollback()
        after=fingerprint(q);report['after_post']=after;report['unchanged_tables']=[k for k in before if before[k]==after[k]]
        detail=sales.source.read(q,f,subject=owner)['detail']
        report['document']=dict(id=detail['id'],status=detail['status'],lines=len(detail['items']),net_total=detail['financial']['net_total'])
        save('diagnosis-invoice',report)
        assert len(detail['items'])==100
        if report['post']['outcome']=='ROLLBACK':
            assert detail['status']=='DRAFT' and before==after
        else:
            assert detail['status']=='POSTED'
        report['outcome']='MEASURED';save('diagnosis-invoice',report)
if __name__=='__main__':
    try:run()
    except Exception as e:record_failure('diagnosis-invoice',e);raise
