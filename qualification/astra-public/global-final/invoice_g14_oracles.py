"""Independent per-product stock and double-entry controls for the operator's ordinary invoice workflow."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from decimal import Decimal
from threading import Event
from time import perf_counter
from zoneinfo import ZoneInfo
import uuid
import psycopg
import cp7_sales_command_cases as sales
from common import admin,db,save

TABLES=('erp.sales_headers','erp.sales_items','erp.sale_stock_allocations','erp.fg_stock_movements',
        'erp.hpp_versions','erp.journal_entries','erp.journal_lines','erp.cost_recalc_queue',
        'cp7_sales.requests','cp7_sku_conversion.sale_allocation_values_v2',
        'cp7_sku_conversion.sale_allocation_components_v2','cp7_sku_conversion.sale_allocation_attributions_v2',
        'cp7_sku_conversion.sale_cost_components_v3','cp7_sku_conversion.cost_events_v3')
ROLES=('COGS','FG_INVENTORY','AR_CUSTOMER','SALES_REVENUE')
def fingerprint(q):
    admin(q)
    return {name:q.execute("select count(*),md5(coalesce(string_agg(h,'' order by h),'')) from (select md5(to_jsonb(t)::text) h from "+name+" t) as rows").fetchone() for name in TABLES}

def position(q,ids,loc):
    admin(q)
    rows=q.execute("select product_id::text,sum(qty_signed) from erp.fg_stock_movements where product_id=any(%s::uuid[]) and location_id=%s group by product_id",(ids,loc)).fetchall()
    assert len(rows)==len(ids)
    return {sku:Decimal(amount) for sku,amount in rows}

def financial(q,sale):
    admin(q)
    money=q.execute("""select count(distinct e.id),coalesce(sum(l.debit),0),coalesce(sum(l.credit),0)
      from erp.journal_entries e join erp.journal_lines l on e.id=l.journal_entry_id
      where e.source_type='SALE' and e.source_id=%s and e.status='POSTED'""",(sale,)).fetchone()
    rows=q.execute("""with roles as (select k,erp.account_id(k) aid from unnest(%s::text[]) k)
      select roles.k,coalesce(sum(l.debit-l.credit),0) from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
      join roles on roles.aid=l.account_id where e.source_type='SALE' and e.source_id=%s and e.status='POSTED' group by roles.k""",(list(ROLES),sale)).fetchall()
    postings={k:Decimal(v) for k,v in rows}
    units=q.execute("""select coalesce(sum(-m.qty_signed) filter (where m.movement_type='SALE_RESERVE'),0),
      coalesce(sum(-m.qty_signed) filter (where m.movement_type='SALE'),0),
      coalesce(sum(-m.qty_signed*m.unit_hpp_snapshot) filter (where m.movement_type='SALE'),0)
      from erp.sales_items i join erp.fg_stock_movements m on m.source_type='SALE_ITEM' and m.source_id=i.id
      where i.sale_id=%s and not exists(select 1 from erp.fg_stock_movements inv where inv.reversal_of_id=m.id)""",(sale,)).fetchone()
    return dict(entries=money[0],debit=money[1],credit=money[2],postings=postings,reserve=units[0],sold=units[1],fg_cost=units[2])
def timed(q,who,action,payload,version,key):
    start=perf_counter()
    q.execute("set local statement_timeout='8s'")
    result=sales.command(q,action,payload,version,key=key,subject=who)
    q.connection.commit()
    return result,start,perf_counter()

def make_payload(rows):
    return dict(sale_number='ASTRA-G14-'+uuid.uuid4().hex[:14],customer_id=rows[0]['customer'],
       source_location_id=rows[0]['location'],sale_date=(datetime.now(ZoneInfo('Asia/Jakarta'))-timedelta(minutes=2)).isoformat(),
       due_date=None,payment_terms='Uji nota sintetis',notes='AUD-G14',change_reason='Owner memeriksa unit, harga, dan gudang pada nota sintetis',
       items=[dict(product_id=r['product'],qty_pcs='1',unit_price_snapshot='20',discount_amount='0',notes='Uji sintetis') for r in rows])

def observe(form,who,ready,stop):
    result=[]
    with psycopg.connect(**db()) as c,c.cursor() as q:
        while not stop.is_set():
            start=perf_counter()
            d=sales.source.read(q,form,subject=who)['detail'];c.commit()
            result.append(dict(start=start,finish=perf_counter(),status=d['status'],lines=len(d['items'])))
            ready.set();stop.wait(.015)
    return result

def qualify(q,rows,owner,other,out,store):
    pool=[r for r in rows if r['code']==rows[0]['code']]
    assert len(pool)>=100 and owner!=other
    measures=[];out['sales_operator_latency']=measures
    for n in (1,10,100):
        subset=pool[:n];ids=[r['product'] for r in subset];loc=subset[0]['location'];payload=make_payload(subset)
        initial=position(q,ids,loc);q.connection.commit()
        result,begin,end=timed(q,owner,'CREATE',payload,None,uuid.uuid4());sid=result['sale_id'];form=dict(tag=payload['sale_number'],sale=sid)
        row=dict(distinct_lines=n,sale_id=sid,pcs=n,operations=[dict(action='CREATE',outcome='COMMIT',ms=round(1000*(end-begin),3))])
        measures.append(row);store()
        review,version=sales.review(q,form)
        draft=financial(q,sid);reserved=position(q,ids,loc);q.connection.commit()
        assert draft['entries']==draft['debit']==draft['credit']==draft['sold']==0 and draft['reserve']==n
        assert all(reserved[i]==initial[i]-1 for i in ids)
        key=uuid.uuid4();ready,stop=Event(),Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            reader=executor.submit(observe,form,other,ready,stop) if n==100 else None
            try:
                if reader and not ready.wait(10):
                    if reader.done():reader.result()
                    raise TimeoutError('Owner kedua belum menyelesaikan pembacaan')
                result,begin,end=timed(q,owner,'POST',review,version,key)
            finally:stop.set()
            if reader:
                reads=reader.result(timeout=15)
                overlap=[r for r in reads if r['start']<end and r['finish']>begin]
                assert overlap and all(r['lines']==n and r['status'] in ('DRAFT','POSTED') for r in reads)
                row['second_owner']=dict(total_reads=len(reads),overlap=len(overlap),status=sorted({r['status'] for r in reads}),maximum_ms=round(max((r['finish']-r['start'])*1000 for r in reads),3))
        row['operations'].append(dict(action='POST',outcome='COMMIT',ms=round(1000*(end-begin),3)))
        seen=sales.source.read(q,form,subject=other)['detail'];posted=financial(q,sid);final=position(q,ids,loc)
        expected=dict(COGS=6*n,FG_INVENTORY=-6*n,AR_CUSTOMER=20*n,SALES_REVENUE=-20*n)
        row.update(authoritative_status=seen['status'],retained_lines=len(seen['items']),net=seen['financial']['net_total'],
                   stock_before=sum(initial.values()),stock_after_draft=sum(reserved.values()),stock_after_post=sum(final.values()),
                   draft=draft,journal=posted,margin=-posted['postings']['SALES_REVENUE']-posted['postings']['COGS'])
        store()
        assert result['status']==seen['status']=='POSTED' and len(seen['items'])==n and Decimal(row['net'])==20*n
        assert posted['entries']==1 and posted['debit']==posted['credit']==26*n and posted['postings']==expected
        assert final==reserved and posted['reserve']==0 and posted['sold']==n and posted['fg_cost']==6*n and row['margin']==14*n
        before=fingerprint(q);q.connection.commit()
        with psycopg.connect(**db()) as rc,rc.cursor() as rq:
            replay,_,_=timed(rq,owner,'POST',review,version,key);after=fingerprint(rq)
        assert replay==result and before==after
        row['idempotency']=dict(response_identical=True,identical_tables=len(before))
        row['within_2s']=max(v['ms'] for v in row['operations'])<=2000
        store()
    subset=pool[:100];p=make_payload(subset)
    draft,_,_=timed(q,owner,'CREATE',p,None,uuid.uuid4());sid=draft['sale_id'];form=dict(tag=p['sale_number'],sale=sid)
    review,v=sales.review(q,form);source=fingerprint(q);q.connection.commit()
    key=uuid.uuid4();q.execute("set local statement_timeout='8s'")
    transient=sales.command(q,'POST',review,v,key=key,subject=owner)
    assert transient['status']=='POSTED' and financial(q,sid)['entries']==1
    q.connection.rollback()
    with psycopg.connect(**db()) as cc,cc.cursor() as rq:
        rolled=fingerprint(rq);reopened=sales.source.read(rq,form,subject=other)['detail']
    assert source==rolled and reopened['status']=='DRAFT' and len(reopened['items'])==100
    final,_,_=timed(q,owner,'POST',review,v,key)
    assert final['status']=='POSTED' and financial(q,sid)['entries']==1
    out['rollback_100']=dict(sale_id=sid,rollback_after_native_post=True,confirmed_draft_lines=100,restored_tables=list(source),table_hashes_before=source,table_hashes_after=rolled,retry_same_id='POSTED',posted_journals_after_retry=1)
    store()
    return measures
