"""Measure the normal sales command against a physically restored synthetic Global."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from threading import Event
from time import monotonic, sleep
import traceback
import uuid
from zoneinfo import ZoneInfo

import psycopg
import cp7_master_cases as master
import cp7_p19_scale_cases as volume
import cp7_sales_command_cases as sales

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'product'))
from install import apply
PACKAGE = json.loads((HERE / 'candidate.json').read_text())
RESULT = Path(os.environ['WRITER_RESULTS'])
RESULT.mkdir(parents=True, exist_ok=True)
REPORT = dict(product=PACKAGE['product'], tree=PACKAGE['tree'], parent=PACKAGE['parent'],
              run=os.getenv('GITHUB_RUN_ID','local'), production_go=False,
              independent_acceptance=False, deadline_ms=8000, save_goal_ms=2000, invoices=[])
TABLES = ('erp.sales_headers','erp.sales_items','erp.sale_stock_allocations','erp.fg_stock_movements',
          'erp.hpp_versions','erp.journal_entries','erp.journal_lines','erp.cost_recalc_queue',
          'cp7_sales.requests','cp7_sku_conversion.sale_allocation_values_v2',
          'cp7_sku_conversion.sale_allocation_components_v2','cp7_sku_conversion.sale_allocation_attributions_v2',
          'cp7_sku_conversion.sale_cost_components_v3','cp7_sku_conversion.cost_events_v3')


def save():
    p = RESULT / 'writer-g14.json'
    tmp = p.with_suffix('.part')
    tmp.write_text(json.dumps(REPORT, indent=2, default=str)+'\n')
    tmp.replace(p)


def db():
    return psycopg.connect(dbname='cp6_rollback', user='supabase_admin', connect_timeout=12)


def fingerprint(q):
    sales.b.api.admin(q)
    return {name: q.execute("select count(*),md5(coalesce(string_agg(h,'' order by h),'')) "
            "from (select md5(to_jsonb(t)::text) h from "+name+" t) hashes").fetchone() for name in TABLES}


def ledger(q,sale_id):
    sales.b.api.admin(q)
    cur=q.execute("""
        select count(distinct j.id),coalesce(sum(l.debit),0),coalesce(sum(l.credit),0),
            coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('COGS')),0),
            coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('FG_INVENTORY')),0),
            coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('AR_CUSTOMER')),0),
            coalesce(sum(l.credit-l.debit) filter(where l.account_id=erp.account_id('SALES_REVENUE')),0)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='SALE' and j.source_id=%s and j.status='POSTED'""",(sale_id,))
    return dict(zip(('entries','debit','credit','cogs','fg','receivable','revenue'),cur.fetchone()))


def physical(q,sale_id):
    sales.b.api.admin(q)
    return q.execute("""
       select coalesce(sum(-m.qty_signed) filter(where m.movement_type='SALE_RESERVE'),0),
              coalesce(sum(-m.qty_signed) filter(where m.movement_type='SALE'),0),
              coalesce(sum(-m.qty_signed*m.unit_hpp_snapshot) filter(where m.movement_type='SALE'),0)
       from erp.sales_items i join erp.fg_stock_movements m on m.source_type='SALE_ITEM' and m.source_id=i.id
       where i.sale_id=%s and not exists(select 1 from erp.fg_stock_movements x where x.reversal_of_id=m.id)
    """,(sale_id,)).fetchone()


def position(q, ids):
    sales.b.api.admin(q)
    return q.execute('select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where product_id=any(%s::uuid[])',(ids,)).fetchone()[0]


def timed(c,q,owner,action,payload,version,key):
    start=monotonic()
    q.execute("set local statement_timeout='8s'")
    r=sales.command(q,action,payload,version,key=key,subject=owner)
    c.commit()
    return r,round((monotonic()-start)*1000,3)


def reader(owner, form, ready, stop):
    samples=[];statuses=set()
    with db() as c,c.cursor() as q:
        while not stop.is_set() or not samples:
            t=monotonic();data=sales.source.read(q,form,subject=owner);c.commit()
            samples.append(round((monotonic()-t)*1000,3));statuses.add(data['detail']['status'])
            ready.set()
            if len(samples)>5000:raise ValueError('Reader did not finish')
            stop.wait(.04)
    return dict(n=len(samples),max_ms=max(samples),statuses=sorted(statuses))


def invoice(c,q,owner,other,rows,n):
    ids=[r['product'] for r in rows[:n]]
    start_qty=position(q,ids);c.commit()
    at=(datetime.now(ZoneInfo('Asia/Jakarta'))-timedelta(minutes=1)).isoformat()
    tag='WR-G14-'+uuid.uuid4().hex[:12]
    payload=dict(sale_number=tag,customer_id=rows[0]['customer'],source_location_id=rows[0]['location'],
                 sale_date=at,due_date=None,payment_terms='Uji Global',notes='Data sintetis',
                 change_reason='Owner memeriksa setiap baris',items=[
                     dict(product_id=p,qty_pcs='1',unit_price_snapshot='20',discount_amount='0',notes='Data sintetis') for p in ids])
    row=dict(lines=n);REPORT['invoices'].append(row);save()
    d,row['create_ms']=timed(c,q,owner,'CREATE',payload,None,uuid.uuid4())
    form=dict(tag=tag,sale=d['sale_id'])
    review,version=sales.review(q,form);sale_id=d['sale_id'];row['sale_id']=sale_id
    row['draft_movement']=physical(q,sale_id);row['draft_journal']=ledger(q,sale_id)
    row['stock_before']=start_qty;row['stock_after_draft']=position(q,ids);c.commit()
    assert tuple(row['draft_movement'][:2])==(n,0) and row['draft_journal']['entries']==0 and row['stock_after_draft']==start_qty-n
    key=uuid.uuid4();save()
    if n==100:
        before=fingerprint(q);c.commit()
        try:
            q.execute("set local statement_timeout='8s'")
            provisional=sales.command(q,'POST',review,version,key=key,subject=owner)
            assert provisional['status']=='POSTED' and ledger(q,sale_id)['entries']==1
            q.execute('select 1/0')
        except psycopg.errors.DivisionByZero:
            c.rollback()
        with db() as check,check.cursor()as checkq:
            after=fingerprint(checkq)
            detail=sales.source.read(checkq,form,subject=other)['detail']
        row['rollback_control']=dict(injected='division_by_zero_after_post_before_commit',sqlstate='22012',
                                     before=before,after=after,status=detail['status'],lines=len(detail['items']))
        assert before==after and detail['status']=='DRAFT' and len(detail['items'])==n
        save()
    ready,stop=Event(),Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(reader,other,form,ready,stop) if n==100 else None
        try:
            if future and not ready.wait(12):
                if future.done():future.result()
                raise TimeoutError('second owner could not open invoice')
            r,row['post_ms']=timed(c,q,owner,'POST',review,version,key)
        finally:
            stop.set()
        if future:row['concurrent_reader']=future.result()
    row['post_status']=r['status'];row['journal']=ledger(q,sale_id);row['posted_movement']=physical(q,sale_id)
    row['stock_after_post']=position(q,ids)
    detail=sales.source.read(q,form,subject=other)['detail']
    row['readback']=dict(status=detail['status'],lines=len(detail['items']),net=detail['financial']['net_total'])
    gl=row['journal'];row['gross_margin']=gl['revenue']-gl['cogs']
    assert r['status']==detail['status']=='POSTED' and len(detail['items'])==n and Decimal(detail['financial']['net_total'])==20*n
    assert tuple(row['posted_movement'])==(0,n,6*n) and row['stock_after_post']==start_qty-n
    assert gl['entries']==1 and gl['debit']==gl['credit']==26*n and gl['cogs']==-gl['fg']==6*n
    assert gl['receivable']==gl['revenue']==20*n and row['gross_margin']==14*n
    old=fingerprint(q);c.commit()
    with db() as repeat,repeat.cursor()as cq:
        replay,row['replay_ms']=timed(repeat,cq,owner,'POST',review,version,key)
        latest=fingerprint(cq)
    row['replay']=dict(same_response=replay==r,identical_tables=[k for k in old if old[k]==latest[k]])
    assert replay==r and old==latest
    row['within_goal']=max(row['create_ms'],row['post_ms'])<2000
    save()


def main():
    assert PACKAGE['parent']=='ffda5cfceb7ebc196656baa650dffd18dd425047'
    for name in ('install.py','definitions.patch','manifest.json','README.md'):
        data=(HERE/'product'/name).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==PACKAGE['changed']['scripts/cp7_global_invoice_post/'+name]
    with db() as c,c.cursor() as q:
        def seal():
            return q.execute('select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()').fetchone()[0]
        def stage(label):
            REPORT['phase']=label;save()
        stage('installed parent')
        initial=seal()
        assert initial['sha256']=='a3da0ecf21909731ab8474c54a7c91afb75bb58dd8b6042cc82314b20808dbd7' and initial['groups']==25
        c.commit()
        REPORT['parent_seal']=initial
        stage('upgrade and inverse')
        results=[]
        for direction in ('up','up','down','up'):
            results.append(apply(c,direction));c.commit()
            current=seal();c.commit()
            if direction=='down':assert current==initial
            elif len(results)==1:REPORT['product_seal']=current
            else:assert current==REPORT['product_seal']
        assert REPORT['product_seal']['sha256']!=initial['sha256'] and [r['changed'] for r in results]==[True,False,True,True]
        REPORT['installation']=results
        stage('synthetic Global history')
        owner,other=[master.role_actor(q,'OWNER') for _ in range(2)];c.commit()
        date=datetime.now(ZoneInfo('Asia/Jakarta')).date();log=volume.Phases();log.commit=c.commit
        missing=512-len(volume.current_targets(q));rows=[]
        for k in range(0,missing,250):
            rows.extend(volume.import_batch(q,date,min(250,missing-k),log));c.commit()
        volume.sell(q,date,rows,log);c.commit()
        REPORT['history']=dict(targets=len(volume.current_targets(q)),historic_posts=log['sale_post_writer']['calls'],
                               stages=dict(log),opening_unit_cost='6.00',sale_unit_price='20')
        assert REPORT['history']['targets']==512
        same=[r for r in rows if r['code']==rows[0]['code']];assert len(same)>=100
        for n in (1,10,100):
            stage('invoice '+str(n));invoice(c,q,owner,other,same,n)
        stage('committed readback')
        REPORT['performance_met']=all(r['within_goal'] for r in REPORT['invoices'])
        assert REPORT['performance_met'],'invoice commit exceeded the 2000 ms save goal'
        REPORT['outcome']='WRITER_VERIFIED';save()
        print([(r['lines'],r['create_ms'],r['post_ms']) for r in REPORT['invoices']],flush=True)


if __name__=='__main__':
    try:main()
    except Exception as err:
        REPORT['outcome']='FAILED';REPORT['first_failure']=dict(kind=type(err).__name__,message=str(err).split('CONTEXT:')[0][:600],
            sqlstate=getattr(err,'sqlstate',None),frames=[(Path(x.filename).name,x.lineno,x.name) for x in traceback.extract_tb(err.__traceback__)[-6:]])
        save();raise
