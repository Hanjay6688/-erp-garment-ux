"""AUDITOR SCENARIO open_2 — cross-batch opening overlap on the IMPORT path (quantifies F1-12; GATE-01).
Oracle (own): M:138 'buktikan perlindungan tumpang tindih saldo awal pada semua jalur' and M:1043 ('identitas dokumen lintas
batch ... masih perlu kontrak/tes'): a second import batch that re-declares the SAME opening item (same material/product,
same location, same cutover) must not produce a second POSTED opening; the ledger and the POSTED opening items must not
change. A FINALIZE replay of an already POSTED batch must be a no-op (M:1043 'replay dalam batch sudah diuji').
Data generator: writer's cp6_opening_overlap_probe.imported (first batch). Second batch built by the auditor from the same tag."""
from datetime import timedelta
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_opening_overlap_probe as ovp
api=awp.api

def ledger(cur):
    api.admin(cur);return api.production.ledger(cur)

def attempt(cur,fn):
    api.admin(cur);cur.execute('savepoint aud_open2')
    try:
        r=fn();cur.execute('release savepoint aud_open2');api.admin(cur);return r,None
    except psycopg.Error as exc:
        cur.execute('rollback to savepoint aud_open2');api.admin(cur);return None,dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:300])

def delta(a,b):
    return {k:str(b.get(k,0)-a.get(k,0)) for k in set(a)|set(b) if b.get(k,0)!=a.get(k,0)}

def header_info(cur,first):
    api.admin(cur)
    return cur.execute("select h.migration_batch_id,b.batch_code,h.opening_date::text,h.status from erp.opening_balance_headers h join erp.migration_batches b on b.id=h.migration_batch_id where h.id=%s",(first,)).fetchone()

def posted_items(cur,kind,tag):
    api.admin(cur)
    r=cur.execute("select count(*),coalesce(sum(i.qty),0)::text,coalesce(sum(i.amount),0)::text,count(distinct h.id) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id join erp.locations l on l.id=i.location_id where h.status='POSTED' and l.location_code=%s and i.balance_type=%s",(tag,kind)).fetchone()
    return dict(items=r[0],qty=r[1],amount=r[2],posted_headers=r[3])

def second_batch(cur,today,kind,tag,cutover_days):
    code='OV'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=cutover_days))))['batch_id']
    if kind=='MATERIAL':row=dict(balance_type='MATERIAL',control_key='CHECK',material_sku=tag,location_code=tag,qty='7',unit_cost='2.25')
    else:row=dict(balance_type='FINISHED_GOODS',control_key='CHECK',product_sku=tag,location_code=tag,qty='7',unit_cost='2.25')
    api.upload(cur,batch,'OPENING_BALANCE_ITEM',[row])
    api.upload(cur,batch,'OPENING_CONTROL',[dict(balance_type=kind,control_key='CHECK',qty='7',amount='15.75')])
    return dict(result=api.invoke(cur,'FINALIZE',batch),batch=batch,batch_code=code)

def cross_batch(cur,today,kind,cutover_days):
    first=ovp.imported(cur,today,kind);info=header_info(cur,first);tag=info[1]
    before=ledger(cur);pb=posted_items(cur,kind,tag)
    r,err=attempt(cur,lambda:second_batch(cur,today,kind,tag,cutover_days))
    after=ledger(cur);pa=posted_items(cur,kind,tag)
    posted=bool(r) and r['result'].get('status')=='POSTED'
    checks=dict(second_batch_not_posted=not posted,ledger_unchanged=before==after,posted_items_unchanged=pb==pa)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',kind=kind,second_cutover=str(today-timedelta(days=cutover_days)),first_opening_date=info[2],checks=checks,
                second_result=str(r['result'])[:300] if r else None,refusal=err,ledger_delta_second=delta(before,after),posted_items_before=pb,posted_items_after=pa,
                expected='M:138/M:1043: a second import batch re-declaring the same opening item (same item, location, cutover) is refused or not POSTED; ledger and POSTED opening items unchanged')

def replay(cur,today):
    kind='MATERIAL';first=ovp.imported(cur,today,kind);info=header_info(cur,first);tag=info[1];batch=info[0]
    before=ledger(cur);pb=posted_items(cur,kind,tag)
    r,err=attempt(cur,lambda:api.invoke(cur,'FINALIZE',batch))
    after=ledger(cur);pa=posted_items(cur,kind,tag)
    checks=dict(ledger_unchanged=before==after,posted_items_unchanged=pb==pa)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,replay_result=str(r)[:300] if r else None,refusal=err,posted_items_after=pa,ledger_delta=delta(before,after),
                expected='M:1043: FINALIZE replay on an already POSTED batch is a no-op (no second posting)')

def stock_readers(cur,today):
    api.admin(cur)
    names=[x[0] for x in cur.execute("select table_name from information_schema.tables where table_schema='erp' and (table_name ilike '%stock%' or table_name ilike '%inventory%' or table_name ilike '%balance%') order by 1").fetchall()]
    fns=[x[0] for x in cur.execute("select proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and (proname ilike '%stock%' or proname ilike '%opening%') order by 1").fetchall()]
    return dict(status='OBSERVED',tables=names[:60],functions=fns[:80],expected='informational: readers that could expose a doubled opening (for follow-up)')

def cases(cur,today):
    def wrap(fn,*a):
        def run():
            try:return fn(cur,today,*a)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1200:])
        return run
    return [('OPEN2:MATERIAL_SECOND_BATCH_SAME_CUTOVER',wrap(cross_batch,'MATERIAL',1)),
            ('OPEN2:MATERIAL_SECOND_BATCH_EARLIER_CUTOVER',wrap(cross_batch,'MATERIAL',2)),
            ('OPEN2:FG_SECOND_BATCH_SAME_CUTOVER',wrap(cross_batch,'FINISHED_GOODS',1)),
            ('OPEN2:MATERIAL_SAME_BATCH_FINALIZE_REPLAY',wrap(replay)),
            ('OPEN2:STOCK_READERS_CATALOG',wrap(stock_readers))]
