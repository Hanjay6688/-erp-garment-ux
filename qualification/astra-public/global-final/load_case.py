"""Measure normal writes, report reads and recost on simultaneous independent application sessions."""
from common import *
import cp7_master_cases as master
import cp7_recost_cases as recost
import cp7_supplier_payment_cases as pay
import cp7_supplier_payment_create_cases as new_pay
import cp7_supplier_payment_correction_cases as edit_pay
import cp7_p19_scale_cases as vol
import cp7_p19_report_v2_cases as rp
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from decimal import Decimal
from time import perf_counter,sleep
from threading import Barrier,Event,Lock
from math import ceil
import traceback

out=dict(environment='Preserved Global ffda5cfc on the public runner',times=[],phase='starting')
def store_case():save('AUD-G14',out)
def take_page(q,run,i,access,actor):
    return rp.staged.limited(q,'erp_cp7_read_staged_analysis_page_v1',(run,i,access),actor)
def percentile(values,p):
    values=sorted(values)
    return values[max(0,ceil(len(values)*p)-1)]
def summarise(times):
    rows={}
    for label in sorted({x['action'] for x in times}):
        vals=[x['wall_ms'] for x in times if x['action']==label]
        rows[label]=dict(n=len(vals),p50_ms=percentile(vals,.5),p95_ms=percentile(vals,.95),max_ms=max(vals))
    return rows
def integrity(q,h):
    admin(q)
    stock=recost.stock(q)
    digest=hashlib.sha256(json.dumps(stock,sort_keys=True,default=str).encode()).hexdigest()
    balance=first(q,"select count(*) from (select e.id from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id where e.status::text='POSTED' group by e.id having sum(l.debit)<>sum(l.credit)) x")
    return dict(stock=digest,unbalanced=balance,posted=first(q,"select count(*) from erp.journal_entries where status::text='POSTED'"))
def recost_fixture(q,owner):
    import production_fixture
    aa=recost.aw.chain.production
    f=aa.estimated_receipt(q,TODAY)
    production_fixture.prepare_lot(recost.aw.OrdinaryDraftCursor(q),f)
    pending=recost.read(q,subject=owner)['counts']
    entry=recost.command(q,subject=owner)
    admin(q)
    out['before_sale']=dict(po=str(f['po']),product=str(f['product']),queue_before=pending,queue_after=entry['queue_after']['counts'],hpp=recost.values(q,f))
    out['before_sale']['lot_hpp']=q.execute('select l.id::text,h.total_cost,h.qty_basis_pcs,h.is_current from erp.fg_lots l left join erp.hpp_versions h on h.lot_id=l.id where l.product_id=%s order by l.id,h.is_current',(f['product'],)).fetchall()
    store_case()
    out['cost_sources']=dict()
    out['cost_sources']['po']=q.execute('select to_jsonb(z) from erp.get_hpp_completeness(%s) z',(f['po'],)).fetchone()[0]
    out['cost_sources']['lots']=q.execute("""select l.id::text,erp.bd_lot_laundry_unknown_v1(l.id),to_jsonb(h)->>'cost_state',h.total_cost,h.qty_basis_pcs from erp.fg_lots l left join erp.hpp_versions h on h.lot_id=l.id and h.is_current where l.product_id=%s""",(f['product'],)).fetchall()
    store_case()
    import cp7_sales_command_cases as sales
    tag='A25-'+str(uuid.uuid4())
    # Use the app's normal sales command after the known cost is recorded; keep the two-piece allocation and its COGS oracle.
    try:
        with q.connection.transaction():
            sale=aa.rpc(q,'erp.save_sale_draft_v2',dict(sale_number=tag,customer_id=f['customer'],source_location_id=aa.base.LOCATION,sale_date=aa.at(TODAY,10),reason='Penjualan dua potong setelah HPP produksi dihitung',items=[dict(product_id=f['product'],qty_pcs=2,unit_price_snapshot=40,discount_amount=0)]))
            review,ver=sales.review(q,dict(sale=sale['sale_id'],tag=tag))
            posted=sales.command(q,'POST',review,ver,subject=owner)
            assert posted['status']=='POSTED',posted['status']
        f['sale']=sale['sale_id']
        out['sale_control']=dict(outcome='POSTED',qty=2,entry='public.erp_cp7_save_sale_v1')
    except psycopg.Error as e:
        if 'CP7_SKU_POOL_HPP_UNKNOWN' not in (e.diag.message_primary or ''): raise
        reason=out['cost_sources']['po'].get('pending_reason_count',0)
        unresolved=int(reason or 0)>0 or any(r[1] or r[2]=='ESTIMATED' for r in out['cost_sources']['lots'])
        out['sale_control']=dict(outcome='REFUSED',entry='public.erp_cp7_save_sale_v1',error=e.diag.message_primary,sqlstate=e.sqlstate,unresolved_source_observed=unresolved,draft_and_reservation_rolled_back=True)
        f['sale']=None
    admin(q);store_case()
    return f

def seed_scale(q,commit):
    start=perf_counter();log=vol.Phases();log.commit=commit
    before=vol.current_targets(q);missing=512-len(before)
    assert missing>=0
    rows=[]
    for off in range(0,missing,250):
        rows+=vol.import_batch(q,TODAY,min(250,missing-off),log)
        out['seed_progress']=dict(stage='opening recorded',new_targets=len(rows));store_case()
    out['seed_progress']['stage']='posting known opening-balance sales';store_case()
    vol.sell(q,TODAY,rows,log)
    out['seed_progress']['stage']='writing operating profiles';store_case()
    vol.profile(q,[row['root'] for row in rows],log)
    vol.activate(q,vol.commercial(q,rows,log),log)
    review=vol.calendar(q,TODAY,log)
    after=vol.current_targets(q)
    assert len(after)==512 and {r['target'] for r in rows}==set(after)-set(before)
    return rows,after,dict(targets=len(after),new_targets=len(rows),preexisting=len(before),known_opening_sales_post_calls=log['sale_post_writer']['calls'],writer_phases=dict(log),calendar=review,elapsed_s=round(perf_counter()-start,3),production_wip_comes_from_cut_sew_laundry_qc_fixture=True)

def measure_invoice(q,rows,owner,limit=2000):
    import cp7_sales_command_cases as sales
    from datetime import timedelta
    measures=[]
    cases=[('small',1),('regular',10),('panel maximum',100)]
    same=[r for r in rows if r['code']==rows[0]['code']]
    assert len(same)>=100
    for label,n in cases:
        tag='A25-BULK-'+uuid.uuid4().hex[:12]
        at=(datetime.now(ZoneInfo('Asia/Jakarta'))-timedelta(minutes=1)).isoformat()
        payload=dict(sale_number=tag,customer_id=same[0]['customer'],source_location_id=same[0]['location'],sale_date=at,due_date=None,payment_terms='Uji pengesahan nota dari layar penjualan',notes='Uji penjualan sintetis',change_reason='Pemilik memeriksa jumlah dan harga setiap barang',items=[dict(product_id=r['product'],qty_pcs='1',unit_price_snapshot='20',discount_amount='0',notes='Barang sintetis') for r in same[:n]])
        row=dict(label=label,distinct_lines=n,pcs=n,amount=str(n*20),rpc='public.erp_cp7_save_sale_v1',native_statement_timeout_ms=8000,operations=[])
        start=perf_counter()
        state=None
        try:
            q.execute("set local statement_timeout='8s'")
            draft=sales.command(q,'CREATE',payload,None,subject=owner);q.connection.commit()
            row['sale_id']=draft['sale_id']
            row['operations'].append(dict(action='CREATE',outcome='COMMIT',ms=round(1000*(perf_counter()-start),3)))
            stage='POST'
            review,version=sales.review(q,dict(sale=draft['sale_id'],tag=tag));q.connection.commit()
            start=perf_counter()
            q.execute("set local statement_timeout='8s'")
            posted=sales.command(q,'POST',review,version,subject=owner);q.connection.commit()
            row['operations'].append(dict(action='POST',outcome='COMMIT',ms=round(1000*(perf_counter()-start),3)))
            assert posted['status']=='POSTED',posted
        except psycopg.Error as exc:
            ms=round(1000*(perf_counter()-start),3);q.connection.rollback()
            row['operations'].append(dict(action='POST' if row.get('sale_id') else 'CREATE',outcome='ROLLBACK',sqlstate=exc.sqlstate,error=exc.diag.message_primary,ms=ms))
        if row.get('sale_id'):
            detail=sales.source.read(q,dict(tag=tag,sale=row['sale_id']),subject=owner)['detail']
            row['authoritative_status']=detail['status'];row['retained_lines']=len(detail['items'])
            row['ledger_amount']=(detail.get('financial') or {}).get('net_total')
            assert row['retained_lines']==n,(n,row)
            if row['operations'][-1]['outcome']=='COMMIT':
                assert row['authoritative_status']=='POSTED' and Decimal(row['ledger_amount'])==Decimal(n*20),row
            else:
                assert row['authoritative_status']=='DRAFT',row
        row['within_2s']=len(row['operations'])==2 and all(op['outcome']=='COMMIT' and op['ms']<=limit for op in row['operations'])
        measures.append(row);out['sales_operator_latency']=measures;store_case()
        q.connection.commit()
    return measures

def exercise():
    params=db()
    if params:
        with psycopg.connect(**params)as c,c.cursor() as q:
            out['seal']=measure_seal(q);owner,second=actors(q);staff=owner
            f=pay.fixture(q,TODAY,26);f['payment']=f['target'];out['fixture_purchase']=f['receipt']['purchase_id']
            h=recost_fixture(q,owner);out['recost_po']=h['po']
            out['before_cost']=recost.values(q,h)
            assert Decimal(out['before_cost']['hpp'])==85
            c.commit()
            out['phase']='building 512 targets through application writers';store_case()
            opening,expected_targets,seed=seed_scale(q,c.commit);out['seed']=seed
            recost.period.late(q,h);out['backlog_before']=recost.read(q,subject=owner)['counts']
            admin(q);out['population']={tab:first(q,'select count(*) from erp.'+tab)for tab in ['products','material_rolls','material_stock_movements','fg_stock_movements','journal_entries','journal_lines','supplier_payments']}
            out['integrity_before']=integrity(q,h);out['db_deadlocks_before']=first(q,'select deadlocks from pg_stat_database where datname=current_database()')
        out['phase']='measuring';store_case()
        gate=Barrier(4);done=Event();guard=Lock();failures=[];waits=[];beg=perf_counter()
        def record(label,who,start):
            with guard:out['times'].append(dict(action=label,session=who,start_s=round(start-beg,6),end_s=round(perf_counter()-beg,6),wall_ms=round(1000*(perf_counter()-start),3)))
        def ordinary_reader(who,actor,count):
            with psycopg.connect(**params,application_name='audit23_'+who)as c,c.cursor()as q:
                gate.wait(20)
                states=[]
                for i in range(count):
                    t=perf_counter();page=pay.read(q,f,25,f['target'],subject=actor);c.commit();record('histori-supplier-dan-fokus',who,t)
                    ap=page['Native_AP'];pair=(ap['paid'],ap['remaining'])
                    assert pair in [('260.00','740.00'),('255.00','745.00')],pair
                    assert page['selected_payment_id']==f['target'];states.append(pair)
                    t=perf_counter();ws=new_pay.read(q,f,actor);c.commit();record('form-buat-dan-pemilih-rekening',who,t)
                    assert ws['purchase']['id']==f['receipt']['purchase_id']
                    t=perf_counter();w=edit_pay.workspace(q,f,f['target'],actor);c.commit();record('form-koreksi-dan-jurnal',who,t)
                    assert w['document']['journal']['id']==f['journal']
                with guard:out.setdefault('readers',{})[who]=dict(cycles=count,seen=[list(v) for v in sorted(set(states))])
        def planner():
            with psycopg.connect(**params,application_name='audit23_planner')as c,c.cursor()as q:
                gate.wait(20);query=rp.staged.query(TODAY);query['from_date']=query['through_date']
                t=perf_counter();key=uuid.uuid4()
                first_state=rp.staged.checked(rp.staged.request(q,TODAY,key,staff,query),key,'RUNNING');c.commit()
                stages=[]
                state=first_state
                while state['state']=='RUNNING':
                    assert len(stages)<rp.staged.DRIVER_CALLS
                    step_t=perf_counter();next_state=rp.staged.checked(rp.staged.step(q,key,staff),key);c.commit()
                    stages.append(dict(stage=state['stage'],done=next_state['units_done'],total=next_state['unit_count'],state=next_state['state'],wall_ms=round(1000*(perf_counter()-step_t),3),elapsed_s=round(perf_counter()-t,3)))
                    assert next_state['units_done']>=state['units_done'];state=next_state
                out['analysis_progress']=stages
                assert state['state']=='DONE',state.get('failure')
                orig,ps,shape=rp.staged.fetch(q,state['run_id'],staff);c.commit()
                run=dict(run=state['run_id'],original=orig,ps=ps)
                record('analisis-512-termasuk-semua-halaman','planner',t)
                analysis=run['original']['analysis'];labels=[x['target_key'] for x in run['original']['product_labels']]
                keys=[x['target']['key'] for x in analysis['recommendations']]
                cover=vol.coverage(labels,keys,analysis['generation_warnings'],analysis['status'],expected_targets)
                out['planner']=dict(targets=len(labels),page_targets=run['ps']['targets_total'],pages=len(run['ps']['pages']),coverage=cover,warning_counts=dict(unreviewed=cover['unreviewed_named_targets']),sha256=hashlib.sha256('\n'.join(sorted(labels)).encode()).hexdigest())
                assert cover['complete'] and len(labels)==512,cover
                for p in run['ps']['pages']:
                    for _ in range(8):
                        t=perf_counter();part=take_page(q,run['run'],p['index'],run['ps']['access_epoch'],staff);c.commit();record('muat-halaman-analisis','planner',t)
                        assert part['body']
        def writer():
            with psycopg.connect(**params,application_name='audit23_writer')as c,c.cursor()as q:
                gate.wait(20)
                for kind in ['ABORT','COMMIT']:
                    payload=edit_pay.payload(q,f,'5.00',subject=second)
                    t=perf_counter();result=edit_pay.correct(q,payload,subject=second)
                    assert result['original_status']=='REVERSED'
                    if kind=='ABORT':c.rollback()
                    else:c.commit()
                    record('koreksi-supplier-'+kind.lower(),'writer',t)
                    out.setdefault('supplier_commands',{})[kind]=str(result['payment_id'])
                t=perf_counter();v=recost.command(q,subject=owner);c.commit();record('proses-antrean-hpp','writer',t)
                out['recalc']=dict(completed=v['completed'],counts_after=v['queue_after']['counts'])
        def monitor():
            with psycopg.connect(**params,application_name='observer23',autocommit=True)as c:
                while not done.is_set():
                    rows=c.execute("select application_name,wait_event_type,wait_event from pg_stat_activity where datname=current_database() and application_name like 'audit23_%' and state='active'").fetchall()
                    waits.append([round(perf_counter()-beg,5),[list(row) for row in rows]]);done.wait(.025)
        with ThreadPoolExecutor(max_workers=5)as ex:
            watch=ex.submit(monitor)
            workers=[ex.submit(ordinary_reader,'owner1',owner,35),ex.submit(ordinary_reader,'owner2',second,35),ex.submit(planner),ex.submit(writer)]
            try:
                for job in workers:
                    try:job.result()
                    except Exception as exc:failures.append(dict(message=str(exc)[:350],where=[(Path(fr.filename).name,fr.lineno,fr.name) for fr in traceback.extract_tb(exc.__traceback__)[-4:]]))
            finally:done.set();watch.result()
        out['sampling_ms']=25;out['activity_samples']=waits;out['errors']=failures
        out['metrics']=summarise(out['times']);store_case()
        assert not failures,failures
        with psycopg.connect(**params)as c,c.cursor()as q:
            admin(q);out['db_deadlocks_after']=first(q,'select deadlocks from pg_stat_database where datname=current_database()')
            after=pay.read(q,f,payment=f['target'],subject=owner);out['supplier_after']=after['Native_AP']
            assert after['Native_AP']['paid']=='255.00' and after['Native_AP']['remaining']=='745.00'
            out['cost_after']=recost.values(q,h);v={k:Decimal(x)for k,x in out['cost_after'].items()}
            expected={'hpp':Decimal(90),'fg':Decimal(54 if h['sale'] else 90),'cogs':Decimal(36 if h['sale'] else 0)}
            out['expected_after']={k:str(v) for k,v in expected.items()}
            assert v==expected and out['recalc']['counts_after']['eligible']=='0'
            assert out['db_deadlocks_after']==out['db_deadlocks_before']
            out['integrity_after']=integrity(q,h)
            assert out['integrity_before']['stock']==out['integrity_after']['stock']
            assert out['integrity_after']['unbalanced']==0 and out['integrity_after']['posted']>=out['integrity_before']['posted']
        out['metrics']=summarise(out['times'])
        multi=[t for t,rows in waits if len({r[0]for r in rows})>=2]
        assert multi
        out['simultaneous_samples']=len(multi);out['samples_with_lock_wait']=sum(any(r[1]=='Lock'for r in rows) for t,rows in waits)
        out['same_action_overlap']=True if any(a['session']!=b['session'] and a['start_s']<b['end_s'] and b['start_s']<a['end_s'] for a in out['times'] for b in out['times'] if a['action']==b['action']=='histori-supplier-dan-fokus')else False
        assert out['same_action_overlap']
        for label,metrics in out['metrics'].items():
            limit=3000 if label in ('muat-halaman-analisis','proses-antrean-hpp') else (2000 if label.startswith('koreksi-') else 1000)
            if label.startswith('analisis-512'):
                assert metrics['max_ms']<=8000 or len({v['done'] for v in out['analysis_progress']})>=2
            else:
                assert metrics['max_ms']<=limit,(label,metrics,limit)
        if out['sale_control']['outcome']=='REFUSED':
            assert out['sale_control']['unresolved_source_observed'],'Source completeness must explain the rejected sale'
        with psycopg.connect(**params) as c,c.cursor() as q:
            rows=measure_invoice(q,opening,owner)
            out['financial_workload']='PASS'
            out['operator_save_goal_ms']=2000
            out['sales_goal_reached']=all(r['within_2s'] for r in rows)
            issues=[r['distinct_lines'] for r in rows if not r['within_2s']]
            if issues:
                out['phase']='complete';out['outcome']='FAIL';out['failed_measurements_lines']=issues;store_case()
                print('AUD-G14 finished with a measured operator save above target:',issues,flush=True)
                raise SystemExit(2)
    out['phase']='complete';out['outcome']='PASS';store_case()

if __name__=='__main__':
    try:exercise()
    except Exception as err:
        store_case();record_failure('AUD-G14',err);raise
