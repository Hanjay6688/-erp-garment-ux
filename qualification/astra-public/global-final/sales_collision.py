"""Two authorised operators competing for one synthetic SKU through the normal invoice command."""
import json
import select
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
import psycopg
from psycopg import sql
import cp7_p19_scale_cases as opening
import cp7_sales_command_cases as sales
from common import db, admin, actors, measure_seal, save, record_failure, TODAY
from invoice_g14_oracles import financial, fingerprint, make_payload, position

out={'phase':'start','waits':[]}
def checkpoint(phase):
    out['phase']=phase
    save('sales-collision',out)

def intent(pcs,row):
    p=make_payload([row])
    p['sale_number']='ASTRA-CROSS-'+uuid.uuid4().hex[:15]
    p['items'][0]['qty_pcs']=str(pcs)
    return p

def command(q,who,action,p,version=None,key=None):
    q.execute("set local statement_timeout='8s'")
    return sales.command(q,action,p,version,key=key or uuid.uuid4(),subject=who)

def review(q,who,doc,action):
    det=sales.source.read(q,dict(tag=doc['p']['sale_number'],sale=doc['id']),subject=who)['detail']
    if action=='EDIT':
        args=dict(deepcopy(doc['p']),sale_id=doc['id'],review_token=det['review_token'])
    else:
        args=dict(sale_id=doc['id'],review_token=det['review_token'],change_reason='Diperiksa operator atas barang dan nilai nota sintetis')
    return args,det['row_version']

def stock(q,row):
    return position(q,[row['product']],row['location'])[row['product']]

def blocked(observer,holder,waiter):
    start=time.monotonic()
    while time.monotonic()-start<4:
        if observer.execute('select %s = any(pg_blocking_pids(%s))',(holder,waiter)).fetchone()[0]:
            return True
        time.sleep(.015)
    return False

def refused(q,actor,action,p,v,key):
    try:
        result=command(q,actor,action,p,v,key);q.connection.commit()
    except psycopg.Error as err:
        q.connection.rollback()
        reason=err.diag.message_primary or ''
        return dict(shortage='insufficient fg stock' in reason.lower(),message=reason[:160],state=err.sqlstate)
    return dict(shortage=False,unexpected=result)

def collide(action,winner,loser,reviewer,first,second,observer):
    wa,pa,va=winner
    wb,pb,vb=loser
    key=uuid.uuid4()
    result=command(first,wa,action,pa,va)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(refused,second,wb,action,pb,vb,key)
        try:
            saw_wait=blocked(observer,first.connection.info.backend_pid,second.connection.info.backend_pid)
        finally:
            first.connection.commit()
        rejection=future.result(timeout=15)
    reviewer.connection.commit()
    admin(reviewer)
    receipts=reviewer.execute('select count(*) from cp7_sales.requests where request_id=%s',(key,)).fetchone()[0]
    evidence=dict(action=action,first_pid=first.connection.info.backend_pid,second_pid=second.connection.info.backend_pid,
                  second_blocked_by_first=saw_wait,loser=rejection,loser_request_rows=receipts)
    out['waits'].append(evidence);checkpoint(action+' concurrent')
    assert saw_wait and rejection['shortage'] and receipts==0,evidence
    return result

def balance(q,sid,pcs,revenue):
    r=financial(q,sid)
    assert r['entries']==1 and r['sold']==pcs and r['reserve']==0 and r['fg_cost']==pcs*6,r
    assert r['debit']==r['credit']==revenue+pcs*6 and r['postings']=={
        'COGS':6*pcs,'FG_INVENTORY':-6*pcs,'AR_CUSTOMER':revenue,'SALES_REVENUE':-revenue},r
    detail=q.execute("""select a.lot_id::text,a.qty_pcs,a.unit_hpp_snapshot
        from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
        where i.sale_id=%s order by a.lot_id,i.id""",(sid,)).fetchall()
    assert sum(qty for _,qty,_ in detail)==pcs and all(cost==6 for _,_,cost in detail),detail
    return dict(**r,allocations=detail)

def run():
    with psycopg.connect(**db()) as a, psycopg.connect(**db()) as b, psycopg.connect(**db()) as oracle, psycopg.connect(**db(),autocommit=True) as observer:
        first,second,q=a.cursor(),b.cursor(),oracle.cursor()
        out['seal']=measure_seal(q)
        actor_a,actor_b=actors(q); assert actor_a!=actor_b
        out['actors_distinct']=True
        row,duplicate=opening.import_batch(q,TODAY,2,opening.Phases())
        oracle.commit()
        assert stock(q,row)==50
        history_ids=[]
        for n in range(30):
            who=actor_b if n%2 else actor_a
            p=intent(1,row)
            draft=command(first,who,'CREATE',p);a.commit()
            doc=dict(p=p,id=draft['sale_id']);rp,v=review(first,who,doc,'POST')
            command(first,who,'POST',rp,v);a.commit()
            history_ids.append(doc['id'])
        admin(q)
        hist=q.execute("""select count(distinct e.id),sum(l.debit),sum(l.credit) from erp.journal_entries e
            join erp.journal_lines l on l.journal_entry_id=e.id where e.source_type='SALE'
            and e.status='POSTED' and e.source_id=any(%s::uuid[])""",(history_ids,)).fetchone()
        assert hist==(30,780,780) and stock(q,row)==20,hist
        out['fixture']=dict(product=row['product'],location=row['location'],opening_pcs=50,hpp=6,price=20,
                            historical_posted_invoices=30,history_journal=hist,available_after_history=20)
        oracle.commit();checkpoint('histori siap')
        pa,pb=intent(14,row),intent(13,row)
        result=collide('CREATE',(actor_a,pa,None),(actor_b,pb,None),q,first,second,observer)
        da=dict(id=result['sale_id'],p=pa)
        assert stock(q,row)==6 and financial(q,da['id'])['reserve']==14
        assert q.execute('select count(*) from erp.sales_headers where sale_number=%s',(pb['sale_number'],)).fetchone()[0]==0
        pb['items'][0]['qty_pcs']='4';res=command(second,actor_b,'CREATE',pb);b.commit()
        dbdoc=dict(id=res['sale_id'],p=pb)
        assert stock(q,row)==2
        xa,va=review(first,actor_a,da,'EDIT');xb,vb=review(second,actor_b,dbdoc,'EDIT');a.commit();b.commit()
        xa['items'][0]['qty_pcs']='16';xb['items'][0]['qty_pcs']='6'
        collide('EDIT',(actor_a,xa,va),(actor_b,xb,vb),q,first,second,observer)
        assert stock(q,row)==0 and financial(q,da['id'])['reserve']==16 and financial(q,dbdoc['id'])['reserve']==4
        out['drafts_before_post']=dict(a=16,b=4,available=0)
        rp_a,va=review(first,actor_a,da,'POST');rp_b,vb=review(second,actor_b,dbdoc,'POST');a.commit();b.commit()
        cmd_b=command(second,actor_b,'POST',rp_b,vb)
        # Send POST and COMMIT in one PostgreSQL protocol query. No result is read by operator A.
        request=uuid.uuid4()
        sales.auth.actor(first,actor_a)
        first.execute("set local statement_timeout='8s'")
        wire=sql.SQL('select public.erp_cp7_save_sale_v1({},{}::jsonb,{}::uuid,{}::text);commit').format(
            sql.Literal('POST'),sql.Literal(json.dumps(rp_a)),sql.Literal(str(request)),sql.Literal(str(va)))
        pid=a.info.backend_pid
        a.pgconn.send_query(wire.as_bytes(a))
        while a.pgconn.flush()==1:
            if not select.select([], [a.fileno()], [], 3)[1]:raise TimeoutError('Send POST')
        wait=blocked(observer,b.info.backend_pid,pid);b.commit()
        out['waits'].append(dict(action='POST',first_pid=b.info.backend_pid,second_pid=pid,second_blocked_by_first=wait))
        cache=None;deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            entry=observer.execute('select response from cp7_sales.requests where actor=%s and request_id=%s',(actor_a,request)).fetchone()
            if entry and entry[0]:cache=entry[0];break
            time.sleep(.02)
        # A separate connection verified commit before closing the unread transport.
        observe_journal=observer.execute("select count(*) from erp.journal_entries where source_type='SALE' and source_id=%s and status='POSTED'",(da['id'],)).fetchone()[0]
        out['lost_reply']=dict(operator_observed_responses=0,committed_seen_by_other=bool(cache),journal_seen_before_disconnect=observe_journal)
        a.close();checkpoint('koneksi terputus setelah commit')
        assert wait and cache and cache['status']==cmd_b['status']=='POSTED' and observe_journal==1,out['lost_reply']
        sig=fingerprint(q);oracle.commit()
        with psycopg.connect(**db()) as fresh, fresh.cursor() as f:
            replay=command(f,actor_a,'POST',rp_a,va,key=request);fresh.commit()
            assert replay==cache and fingerprint(f)==sig
            out['lost_reply'].update(retry_pid=fresh.info.backend_pid,first_pid=pid,same_result=replay==cache,identical_tables=len(sig))
        assert stock(q,row)==0
        out['final']=dict(available=0,invoice_a=balance(q,da['id'],16,320),invoice_b=balance(q,dbdoc['id'],4,80))
        zero=refused(second,actor_b,'CREATE',intent(1,row),None,uuid.uuid4())
        assert zero['shortage'] and fingerprint(q)==sig
        out['out_of_stock_refusal']=zero
        checkpoint('race verified')
        multi=intent(2,duplicate)
        multi['items'].append(dict(multi['items'][0],qty_pcs='3',unit_price_snapshot='22'))
        before=fingerprint(q);oracle.commit()
        try:
            submitted=command(second,actor_b,'CREATE',multi)
        except psycopg.Error as err:
            b.rollback();code=err.diag.message_primary or ''
            out['duplicate_line']=dict(outcome='REFUSED',message=code,unchanged=fingerprint(q)==before)
            checkpoint('multiple lines')
            assert ('duplicate' in code.lower() or 'duplikat' in code.lower()) and out['duplicate_line']['unchanged']
        else:
            b.commit()
            rp,v=review(second,actor_b,dict(p=multi,id=submitted['sale_id']),'POST')
            command(second,actor_b,'POST',rp,v);b.commit()
            out['duplicate_line']=dict(outcome='POSTED',units=[2,3],prices=[20,22],net=106,available=stock(q,duplicate),
                                       journal=balance(q,submitted['sale_id'],5,106))
            assert out['duplicate_line']['available']==45
        out['outcome']='PASS';checkpoint('complete')
if __name__=='__main__':
    try:run()
    except Exception as exc: record_failure('sales-collision',exc);raise
