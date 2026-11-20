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
    # Use the app's normal sales command after the known cost is recorded; keep the two-piece allocation and its COGS oracle.
    sale=aa.rpc(q,'erp.save_sale_draft_v2',dict(sale_number='A25-'+str(uuid.uuid4()),customer_id=f['customer'],source_location_id=aa.base.LOCATION,sale_date=aa.at(TODAY,10),reason='Penjualan dua potong setelah HPP produksi dihitung',items=[dict(product_id=f['product'],qty_pcs=2,unit_price_snapshot=40,discount_amount=0)]))
    q.execute('select erp.post_sale_v2(%s,%s,%s)',(sale['sale_id'],uuid.uuid4(),int(sale['row_version'])))
    admin(q);f['sale']=sale['sale_id'];return f
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
            seed=vol.ensure(q,TODAY,512,False,commit=c.commit);out['seed']=seed
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
                t=perf_counter();run=rp.staged_run(q,TODAY,staff,query);c.commit();record('analisis-512-termasuk-semua-halaman','planner',t)
                keys=[x['target']['key'] for x in run['original']['analysis']['recommendations']]
                assert len(keys)==len(set(keys))==512
                out['planner']=dict(targets=len(keys),pages=len(run['ps']['pages']),sha256=hashlib.sha256('\n'.join(sorted(keys)).encode()).hexdigest())
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
                    except Exception as exc:failures.append(str(exc)[:250])
            finally:done.set();watch.result()
        out['sampling_ms']=25;out['activity_samples']=waits;out['errors']=failures
        assert not failures,failures
        with psycopg.connect(**params)as c,c.cursor()as q:
            admin(q);out['db_deadlocks_after']=first(q,'select deadlocks from pg_stat_database where datname=current_database()')
            after=pay.read(q,f,payment=f['target'],subject=owner);out['supplier_after']=after['Native_AP']
            assert after['Native_AP']['paid']=='255.00' and after['Native_AP']['remaining']=='745.00'
            out['cost_after']=recost.values(q,h);v={k:Decimal(x)for k,x in out['cost_after'].items()}
            assert v=={'hpp':Decimal(90),'fg':Decimal(54),'cogs':Decimal(36)} and out['recalc']['counts_after']['eligible']=='0'
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
    out['phase']='complete';out['outcome']='PASS';store_case()

if __name__=='__main__':
    try:exercise()
    except Exception as err:
        store_case();record_failure('AUD-G14',err);raise
