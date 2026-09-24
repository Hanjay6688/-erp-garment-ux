"""AUDITOR SCENARIO xaudit_3 — two-session races on 9add57e (independent auditor). BY DESIGN this run ends INCOMPLETE:
the races need committed data visible to a second connection, so the side connections COMMIT to the disposable clone and
the runtime's boundary snapshot will differ (the clone is dropped after the job). Read the per-case JSON, not the job colour.
Races: (1) two sessions FINALIZE two different import batches of the SAME opening item at once (F1-12 under concurrency);
(2) two sessions close the same accounting date at once (exactly one filing, or exact refusal); (3) two sessions COMPLETE
the same WIP opening source with the same expected_remaining at once (M:369: stale remaining version refused).
Oracles: M:138/M:1043 (overlap), M:1057-1065/M:3816 (atomic, one close), M:369-371 (stale version refused), M:4321 (two-connection concurrency)."""
from datetime import timedelta
import json,threading,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_opening_overlap_probe as ovp
import cp6_initial_import_production_trial as pt
api,boundary=awp.api,awp.boundary;prod=awp.chain.production

def side():
    c=psycopg.connect(boundary.PG,autocommit=False);k=c.cursor();api.admin(k);return c,k

def race(fns):
    """Run callables concurrently (one per side connection); each commits its own transaction. Returns per-thread result/error."""
    out=[None]*len(fns);bar=threading.Barrier(len(fns))
    def run(i):
        c,k=side()
        try:
            bar.wait(timeout=30);r=fns[i](k);c.commit();out[i]=dict(result=str(r)[:300],error=None)
        except psycopg.Error as exc:
            c.rollback();out[i]=dict(result=None,error=dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:300]))
        except Exception as exc:
            c.rollback();out[i]=dict(result=None,error=dict(message=str(exc)[:300]))
        finally:c.close()
    ts=[threading.Thread(target=run,args=(i,)) for i in range(len(fns))]
    for t in ts:t.start()
    for t in ts:t.join(timeout=120)
    return out

def second_batch(k,today,tag,row):
    code='XA3'+uuid.uuid4().hex[:10]
    batch=api.call(k,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=1))))['batch_id']
    api.upload(k,batch,'OPENING_BALANCE_ITEM',[dict(balance_type='MATERIAL',control_key='CHECK',material_sku=row[0],location_code=row[1],qty=str(row[2]),unit_cost=str(row[3]))])
    api.upload(k,batch,'OPENING_CONTROL',[dict(balance_type='MATERIAL',control_key='CHECK',qty=str(row[2]),amount=str(row[2]*row[3]))])
    return api.invoke(k,'FINALIZE',batch)

def race_import(cur,today):
    c,k=side();first=ovp.imported(k,today,'MATERIAL');c.commit()
    row=k.execute("select m.material_sku,l.location_code,i.qty,i.unit_cost_snapshot from erp.opening_balance_items i join erp.materials m on m.id=i.material_id join erp.locations l on l.id=i.location_id where i.opening_id=%s",(first,)).fetchone()
    tag=row[0];c.close()
    res=race([lambda k:second_batch(k,today,tag,row),lambda k:second_batch(k,today,tag,row)])
    c,k=side()
    posted=k.execute("select count(*),coalesce(sum(i.qty),0)::text from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id join erp.locations l on l.id=i.location_id where h.status='POSTED' and l.location_code=%s",(row[1],)).fetchone()
    c.close()
    n_posted=sum(1 for r in res if r and r['result'] and "'POSTED'" in r['result'])
    checks=dict(at_most_one_posted_beyond_first=posted[0]<=1)
    return dict(status='PASS' if checks['at_most_one_posted_beyond_first'] else 'COUNTEREXAMPLE',checks=checks,threads=res,posted_items_for_location=posted[0],posted_qty=posted[1],
                second_batches_posted=n_posted,expected='M:138/M:1043 under two sessions: the same opening item is never POSTED more than once (first import + 0 of the two racing batches)')

def race_close(cur,today):
    d=str(today-timedelta(days=1))
    c,k=side();prod.owner(k);pre=k.execute('select public.erp_accounting_close_preflight_v1(%s::date)',(d,)).fetchone()[0];c.rollback();c.close()
    def close(k):prod.owner(k);return k.execute("select public.erp_close_accounting_through_v1(%s::date,'XA3 race close')",(d,)).fetchone()[0]
    res=race([close,close])
    c,k=side();filings=k.execute("select count(*) from erp.accounting_close_filings_v1 where closed_through=%s::date",(d,)).fetchone()[0] if k.execute("select to_regclass('erp.accounting_close_filings_v1') is not null").fetchone()[0] else None
    ct=k.execute("select current_setting('app.closed_through',true)").fetchone()[0];c.close()
    ok=sum(1 for r in res if r and r['error'] is None)
    checks=dict(at_most_one_success=ok<=1,filings_at_most_one=(filings is None) or filings<=1)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,preflight_status=(pre or {}).get('status'),threads=res,filings=filings,
                expected='M:3816/M:1057-1065: two concurrent closes of the same date yield exactly one filing; the other is refused with the product message (or both refused if BLOCKED)')

def race_wip(cur,today):
    c,k=side();f=pt.fixture(api,k,today);receipt,sources=pt.finalize(api,k,f);c.commit()
    s=next(x for x in api.read(k,f['batch'])['batch']['production_sources'] if x['balance_type']=='WIP');c.close()
    def complete(k):
        payload=dict(batch_id=f['batch'],opening_item_id=s['opening_item_id'],expected_remaining=str(s['remaining_qty_pcs']),operation='COMPLETE',qty_pcs='8',
                     product_sku=f['code'],location_code=f['code']+'F',date=str(today-timedelta(days=2)),reason='XA3 race completion')
        return api.call(k,'WIP_OUTPUT',payload,uuid.uuid4())
    res=race([complete,complete])
    c,k=side();outputs=k.execute('select count(*),coalesce(sum(qty_pcs),0)::text from erp.initial_import_wip_outputs where opening_item_id=%s',(s['opening_item_id'],)).fetchone();c.close()
    ok=sum(1 for r in res if r and r['error'] is None)
    checks=dict(exactly_one_success=ok==1,total_output_not_above_source=int(float(outputs[1]))<=8)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,threads=res,outputs=[str(x) for x in outputs],
                expected='M:369-371 under two sessions: the second completion with the same expected_remaining is refused (STALE_VERSION) and total output never exceeds the source qty')

def cases(cur,today):
    def wrap(fn):
        def run():
            try:return fn(cur,today)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1500:])
        return run
    return [('XA3:RACE_TWO_SESSIONS_SECOND_IMPORT_BATCH_SAME_ITEM',wrap(race_import)),
            ('XA3:RACE_TWO_SESSIONS_CLOSE_SAME_DATE',wrap(race_close)),
            ('XA3:RACE_TWO_SESSIONS_WIP_COMPLETE_SAME_REMAINING',wrap(race_wip))]
