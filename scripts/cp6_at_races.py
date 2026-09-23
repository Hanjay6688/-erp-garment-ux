"""Real two-session WIP/master schedules on a disposable committed fixture."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import queue,time
import psycopg
import cp6_at_probe as audit
import cp6_as_probe as peer
import cp6_ao_ap_installed as api
import cp6_initial_import_production_trial as production
import cp6_successor_regression as boundary


def fixture(today):
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        f=production.fixture(api,cur,today)
        api.upload(cur,f['batch'],'BRAND',[dict(brand_code=f['code'],brand_name='AT race '+f['code'])])
        _,sources=production.finalize(api,cur,f)
        model,size=cur.execute('select model_id,size_id from erp.products where sku=%s',(f['code'],)).fetchone()
        code=f['code']+'RACE';brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
        old,new=audit.series(cur,f['code'],model,brand,size,peer.invoice.at(today-timedelta(days=6),0),peer.invoice.at(today-timedelta(days=4),0))
        payload=dict(batch_id=f['batch'],opening_item_id=sources['WIP']['opening_item_id'],expected_remaining='8',operation='COMPLETE',
                     qty_pcs='4',product_sku=f['code'],brand_code=code,location_code=f['code']+'F',date=str(today-timedelta(days=3)),reason='AT concurrent master validity')
        initial=production.effects(api,cur)
    return f,new,payload,initial


def blocking(cur,waiter,holder):
    deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        row=cur.execute('select %s=any(pg_blocking_pids(%s))',(holder,waiter)).fetchone()
        if row and row[0]:return True
        time.sleep(.025)
    raise AssertionError('AT_EXPECTED_PRODUCT_ROW_BLOCK_NOT_OBSERVED')


def run(today,first,commit):
    f,product,payload,initial=fixture(today)
    ready=queue.Queue()
    def worker(action):
        try:
            with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
                cur.execute("set local lock_timeout='15s';set local statement_timeout='25s'")
                ready.put(cur.execute('select pg_backend_pid()').fetchone()[0])
                if action=='OUTPUT':return dict(ok=True,result=api.call(cur,'WIP_OUTPUT',payload))
                cur.execute('update erp.products set is_active=false where id=%s',(product,))
                return dict(ok=True,master_deactivated=True)
        except psycopg.Error as exc:return dict(ok=False,sqlstate=exc.sqlstate,message=exc.diag.message_primary)
    with psycopg.connect(boundary.ADMIN) as holder,holder.cursor() as cur,ThreadPoolExecutor(max_workers=1) as pool:
        holder_pid=cur.execute('select pg_backend_pid()').fetchone()[0]
        if first=='MASTER':cur.execute('update erp.products set is_active=false where id=%s',(product,))
        else:posted=api.call(cur,'WIP_OUTPUT',payload)
        future=pool.submit(worker,'OUTPUT' if first=='MASTER' else 'MASTER')
        waiter=ready.get(timeout=10)
        observed=blocking(cur,waiter,holder_pid)
        (holder.commit if commit else holder.rollback)()
        result=future.result(timeout=30)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        source=next(x for x in api.read(cur,f['batch'])['batch']['production_sources'] if x['balance_type']=='WIP')
        posted_expected=(first=='MASTER' and not commit) or (first=='OUTPUT' and commit)
        assert source['remaining_qty_pcs']==(4 if posted_expected else 8),(source,result)
        if first=='MASTER' and commit:
            assert not result['ok'] and result['sqlstate']=='P0001' and 'tanggal hasil' in result['message'],result
            assert production.effects(api,cur)==initial
        else:assert result['ok'],result
        lots=cur.execute('''select l.product_id,l.initial_qty_pcs from erp.initial_import_wip_outputs o
            join erp.initial_import_production_sources s on s.opening_item_id=o.opening_item_id
            join erp.fg_lots l on l.id=o.lot_id where s.batch_id=%s''',(f['batch'],)).fetchall()
        assert lots==([(product,4)] if posted_expected else []),lots
        production.truth(cur)
        if posted_expected:
            output=result['result'] if first=='MASTER' else posted
            production.reverse_output(api,cur,f,output)
            assert production.effects(api,cur)==initial
    return dict(status='PASS',first=first,first_committed=commit,blocking_observed=observed,
                business_action='ordinary_authenticated_public_RPC',master_change='administrative_fixture_display_status_update',
                output_posted=posted_expected,worker=result,linked_inverse_restores_net_ledger=posted_expected,
                committed_fixture_isolated_in_disposable_clone=True)
