"""r3 fixes of the r2 audits (candidate 2e9d6a46), spliced into the CP17 harness.

R3-01 (Astra ASTRA-R2-02, Sol SOL-R2-001): the automatic PO number of Buat Potongan passes 999. The auditors' own failing
cases are used as written (Sol: 998 and 999 unused DRAFT headers on the cutting day, a 3 s limit; Astra: an empty day,
998 headers, then 999 and 1000 with the roll going 10 -> 8 -> 6 under a 10 s limit), plus 1001, 9999 -> 10000, two
sessions at the 999/1000 boundary and a resend with the same UUID.

R3-09 (owner D16-2, D16-3, D16-4): cp7_r3_rate_cases.py, the old or new Mandor rate when sewing is finished.

R3-02 (Astra ASTRA-R2-01): reopening a finished PO is no longer blocked by a use of its finished goods that was cancelled
or reversed. Astra's two cases are used as written (a cancelled sales draft; a reversed finished-goods adjustment, with
the account deltas of Native sync_po_hpp_to_gl that Astra qualified), plus controls: an active use still blocks, an
unrelated inflow does not offset an active use, cancelling one of two drafts leaves the other blocking, reopen then
finish again gives the same stock and HPP, and two tabs reopen once.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import json,threading,time,uuid
import psycopg
import cp7_auto_po_cases as po
import cp7_r3_rate_cases as rate
b=po.b

NATIVE=['CP17_R3_01_AUTO_PO_NUMBER_999_CONTROL','CP17_R3_01_AUTO_PO_NUMBER_1000_BOUNDED','CP17_R3_01_AUTO_PO_NUMBER_999_TO_1000_ASTRA',
        'CP17_R3_01_AUTO_PO_NUMBER_1001_AND_10000','CP17_R3_01_AUTO_PO_NUMBER_REFUSAL_AND_SAME_UUID_PAST_1000',
        'CP17_R3_02_REOPEN_AFTER_CANCELLED_SALES_DRAFT','CP17_R3_02_REOPEN_AFTER_REVERSED_FG_ADJUSTMENT',
        'CP17_R3_02_ACTIVE_USE_STILL_BLOCKS','CP17_R3_02_UNRELATED_INFLOW_DOES_NOT_OFFSET_ACTIVE_USE',
        'CP17_R3_02_ONE_OF_TWO_DRAFTS_CANCELLED_STILL_BLOCKS','CP17_R3_02_REOPEN_AFTER_CANCEL_THEN_FINISH_SAME_HPP']
RACES=['CP17_RACE_R3_01_AUTO_PO_NUMBER_BOUNDARY_TWO_SESSIONS','CP17_RACE_R3_02_REOPEN_AFTER_CANCEL_TWO_TABS']
HTTP=[]
BROWSER=[]
# R3-09 (owner D16-2, D16-3, D16-4): the rate choice when sewing is finished (cp7_r3_rate_cases.py).
NATIVE=NATIVE+rate.NATIVE
RACES=RACES+rate.RACES
HTTP=HTTP+rate.HTTP
BROWSER=BROWSER+rate.BROWSER

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def fill(cur,prefix,body,last,note):
    """Unused lawful DRAFT/CUTTING PO headers numbered 001..last on the cutting day (no stock, journal or cutting), the
    auditors' isolation fixture; numbers that already exist are kept."""
    b.api.admin(cur)
    cur.execute("""insert into erp.production_orders(po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
      select %s||lpad(i::text,greatest(3,length(i::text)),'0'),%s,1,'DRAFT','CUTTING',%s::timestamptz,%s
      from generate_series(1,%s)i where not exists(select 1 from erp.production_orders o where o.po_number=%s||lpad(i::text,greatest(3,length(i::text)),'0'))""",
      (prefix,po.prod().MODEL,body['cutting']['cut_at'],note,last,prefix))
def oracle_next(cur,prefix):
    """The oracle's own next free number: that day's count + 1, then the first free one, at its natural width (min 3)."""
    b.api.admin(cur);numbers={x[0] for x in cur.execute('select po_number from erp.production_orders where po_number like %s',(prefix+'%',))}
    n=len(numbers)+1
    while prefix+str(n).zfill(3) in numbers:n+=1
    return prefix+str(n).zfill(3)
def bounded(cur,fn,seconds):
    """Run one public command under a declared statement limit inside a savepoint; the limit is never raised to pass."""
    started=time.monotonic();cur.execute('savepoint r3_bounded');cur.execute(f"set local statement_timeout='{seconds}s'")
    try:answer=fn();error=None
    except psycopg.Error as exc:
        answer=None;error=dict(sqlstate=exc.sqlstate,message=exc.diag.message_primary,context=exc.diag.context)
        cur.execute('rollback to savepoint r3_bounded')
    finally:
        cur.execute('release savepoint r3_bounded');b.api.admin(cur);cur.execute("set local statement_timeout='240s'")
    return answer,error,round(time.monotonic()-started,3)


def cases(cur,today):
    import cp7_cp17_fix_cases as f
    import cp7_sales_draft_cases as drafts

    # ---- R3-01: Sol's case (number_case), unchanged numbers and limit; it must now pass at 999 and at 1000.
    def sol_number(last):
        g=po.receipt(cur,today);body=po.post_body(g);prefix=po.prefix(cur,body['cutting']['cut_at'])
        fill(cur,prefix,body,last,'Sol synthetic number boundary')
        expected=oracle_next(cur,prefix);assert expected==prefix+str(last+1).zfill(3),(expected,last)
        assert po.roll_stock(cur,g)==10
        before=b.boundary.snapshot(cur)
        answer,error,elapsed=bounded(cur,lambda:po.command(cur,body),3)
        if answer is None:
            assert b.boundary.snapshot(cur)==before and po.roll_stock(cur,g)==10
            raise AssertionError(dict(expected_number=expected,existing_daily_numbers=last,deadline_seconds=3,elapsed_seconds=elapsed,error=error))
        assert answer['po_number']==expected and po.roll_stock(cur,g)==0,answer
        assert po.po_state(cur,expected)['posted']==1
        return dict(status='PASS',expected_number=expected,actual_number=answer['po_number'],existing_daily_numbers=last,
                    elapsed_seconds=elapsed,deadline_seconds=3,one_posted_cutting=True,stock_after='0',session_role='OWNER')

    # ---- R3-01: Astra's case (test_auto_po_carry), unchanged fixture, day and limit (each case runs in its own savepoint).
    def astra_carry():
        g=po.receipt(cur,today)
        body=po.post_body(g,qty=2,pieces=2);pre=po.prefix(cur,body['cutting']['cut_at']);b.api.admin(cur)
        assert one(cur,'select count(*) from erp.production_orders where po_number like %s',(pre+'%',))==0
        cur.execute("""insert into erp.production_orders(po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
          select %s||lpad(n::text,3,'0'),%s,1,'DRAFT','CUTTING',%s::timestamptz,'Astra numbering boundary fixture'
          from generate_series(1,998)n""",(pre,body['model_id'],body['cutting']['cut_at']))
        control=po.command(cur,body)
        assert control['po_number']==pre+'999' and po.roll_stock(cur,g)==8,control
        result,error,elapsed=bounded(cur,lambda:po.command(cur,body),10)
        assert error is None,dict(expected=pre+'1000',error=error,elapsed_seconds=elapsed)
        assert result['po_number']==pre+'1000' and po.roll_stock(cur,g)==6,result
        return dict(status='PASS',numbers=[control['po_number'],result['po_number']],stock=[10,8,6],elapsed_seconds=elapsed,statement_timeout='10s')

    # ---- R3-01: past 1000 and the next width change; the limit stays 3 s per post.
    def past_1000():
        out=[]
        for last in (1000,9999):
            g=po.receipt(cur,today);body=po.post_body(g);prefix=po.prefix(cur,body['cutting']['cut_at'])
            fill(cur,prefix,body,last,'CP17 r3 number width')
            expected=oracle_next(cur,prefix);assert expected==prefix+str(last+1),(expected,last)
            answer,error,elapsed=bounded(cur,lambda:po.command(cur,body),3)
            assert error is None,dict(expected=expected,error=error,elapsed_seconds=elapsed)
            assert answer['po_number']==expected and po.roll_stock(cur,g)==0 and po.po_state(cur,expected)['posted']==1,answer
            out.append(dict(after=last,number=answer['po_number'],elapsed_seconds=elapsed))
        return dict(status='PASS',numbers=out,no_digit_cut=True)

    # ---- R3-01: past 1000 a resend with the same UUID is the same answer; a refused post uses no number.
    def same_uuid_past_1000():
        g=po.receipt(cur,today);body=po.post_body(g);prefix=po.prefix(cur,body['cutting']['cut_at'])
        fill(cur,prefix,body,1001,'CP17 r3 number boundary resend')
        expected=oracle_next(cur,prefix);key=uuid.uuid4();before=po.po_count(cur)
        po.refused(cur,lambda:po.command(cur,po.post_body(g,qty=11)),'SELECTED_ROLL_IS_NOT_AVAILABLE_AT_SOURCE_LOCATION')
        assert po.po_count(cur)==before and oracle_next(cur,prefix)==expected
        r=po.command(cur,body,key);again=po.command(cur,body,key)
        assert r==again and r['po_number']==expected and po.po_count(cur)==before+1 and po.roll_stock(cur,g)==0,(r,again)
        return dict(status='PASS',number=r['po_number'],same_uuid_same_answer=True,refused_post_used_no_number=True,one_po=True)

    # ---- R3-02 helpers (Astra's own).
    def lot_qty(lot):
        b.api.admin(cur);return one(cur,'select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(lot,))
    def finished(label):
        g=f.finish_fixture(cur,today,label=label)
        f.finish_command(cur,f.finish_workspace(cur,g['po']),reason='Astra complete production control')
        assert lot_qty(g['lot'])==10 and f.reopen_workspace(cur,g['po'])['eligible']
        return g
    def location(g):return one(cur,'select location_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id limit 1',(g['lot'],))
    def sale_of(g):
        customer=str(drafts.source.fg.base.create_customer(cur,'CP17-R3-'+uuid.uuid4().hex[:8]))
        return dict(g,location=location(g),customer=customer,tag='CP17-R3-'+uuid.uuid4().hex[:10],
                    sale_at=(drafts.source.fg.ax.r1.now(cur)-timedelta(minutes=1)).isoformat())
    def reserve(g,qty):
        s=sale_of(g);drafts.create(cur,s,drafts.payload(s,qty=str(qty),price='13.37'));return s
    def cancel(s):
        p,v=drafts.cmd.review(cur,s);out=drafts.cmd.command(cur,'CANCEL',p,v);assert out['status']=='CANCELLED',out;return out
    def blocked_by(g,qty,what):
        w=f.reopen_workspace(cur,g['po']);assert not w['eligible'] and dict(kind='FG_USED',qty=qty) in w['blockers'],(what,w['blockers'])
        before=b.boundary.snapshot(cur)
        f.refused(cur,lambda:f.reopen_command(cur,w,reason='CP17 r3 '+what),'CP7_PO_REOPEN_BLOCKED');f.unchanged(cur,before,what)
        return w['blockers']

    def astra_sales_cancel():
        g=finished('ASTRA-R2-REOPEN');accounts=drafts.cmd.accounts(cur)
        s=reserve(g,2);assert lot_qty(g['lot'])==8
        blocked=f.reopen_workspace(cur,g['po']);assert not blocked['eligible']
        out=cancel(s);assert lot_qty(g['lot'])==10 and drafts.cmd.accounts(cur)==accounts
        fresh=f.reopen_workspace(cur,g['po']);assert fresh['eligible'],fresh['blockers']
        r=f.reopen_command(cur,fresh,reason='Astra reopen after cancelled sales draft')
        assert r['result']['status']!='FINISHED' and lot_qty(g['lot'])==10
        return dict(status='PASS',draft_status=out['status'],stock=[10,8,10],reopened=r['result']['status'])

    def astra_adjustment_reverse():
        g=finished('ASTRA-R2-REOPEN');hpp=f.po_hpp(cur,g['po']);accounts=f.fgadj.accounts(cur)
        draft,_=f.fgadj.draft(cur,dict(location=location(g),lot=g['lot'],product=g['product']),'-2')
        posted=f.fgadj.action(cur,'POST',draft)
        blocked=f.reopen_workspace(cur,g['po'])
        assert lot_qty(g['lot'])==8 and blocked['blockers']==[dict(kind='FG_USED',qty=2)],blocked
        f.fgadj.action(cur,'REVERSE',posted)
        observed_stock=lot_qty(g['lot']);observed_hpp=f.po_hpp(cur,g['po']);after=f.fgadj.accounts(cur)
        old=dict(accounts);new=dict(after);delta={str(k):new.get(k,D(0))-old.get(k,D(0)) for k in set(old)|set(new) if new.get(k,D(0))!=old.get(k,D(0))}
        mapped={k:str(one(cur,'select erp.account_id(%s)',(k,))) for k in ('OTHER_EXPENSE','OTHER_INCOME')}
        loss=round(D(hpp[0])/D(hpp[1])*2,2)
        # Astra's qualified oracle: Native production lots use sync_po_hpp_to_gl (OTHER_EXPENSE +loss, OTHER_INCOME -loss).
        assert observed_stock==10 and observed_hpp==hpp,(observed_stock,observed_hpp,hpp)
        assert delta=={mapped['OTHER_EXPENSE']:loss,mapped['OTHER_INCOME']:-loss},delta
        fresh=f.reopen_workspace(cur,g['po']);assert fresh['eligible'],fresh['blockers']
        r=f.reopen_command(cur,fresh,reason='Astra reopen after child reversal')
        assert r['result']['status']!='FINISHED' and lot_qty(g['lot'])==10 and f.po_hpp(cur,g['po'])==hpp
        return dict(status='PASS',stock=[10,8,10],hpp=[str(x) for x in hpp],account_delta={k:str(v) for k,v in delta.items()},reopened=r['result']['status'])

    def active_use_blocks():
        g=finished('CP17-R3-ACTIVE');s=reserve(g,2);assert lot_qty(g['lot'])==8
        blockers=blocked_by(g,2,'active sales draft')
        cancel(s);assert f.reopen_workspace(cur,g['po'])['eligible']
        return dict(status='PASS',active_draft_blocks=blockers,after_cancel_eligible=True)

    def unrelated_inflow():
        g=finished('CP17-R3-INFLOW');reserve(g,2)
        draft,_=f.fgadj.draft(cur,dict(location=location(g),lot=g['lot'],product=g['product']),'2')
        f.fgadj.action(cur,'POST',draft);assert lot_qty(g['lot'])==10
        blockers=blocked_by(g,2,'active draft with an unrelated +2 adjustment')
        return dict(status='PASS',stock=10,active_reservation=2,still_blocked=blockers,inflow_does_not_offset=True)

    def one_of_two():
        g=finished('CP17-R3-TWO');first=reserve(g,2);reserve(g,3);assert lot_qty(g['lot'])==5
        blocked_by(g,5,'two active drafts')
        cancel(first);assert lot_qty(g['lot'])==7
        blockers=blocked_by(g,3,'second draft still active')
        return dict(status='PASS',stock=[10,5,7],blocked_qty=[5,3],remaining=blockers)

    def reopen_then_finish():
        g=finished('CP17-R3-REFINISH');hpp=f.po_hpp(cur,g['po']);s=reserve(g,2);cancel(s)
        r=f.reopen_command(cur,f.reopen_workspace(cur,g['po']),reason='CP17 r3 buka ulang sesudah draf batal')
        assert r['result']['status']!='FINISHED'
        again=f.finish_command(cur,f.finish_workspace(cur,g['po']),reason='CP17 r3 selesai lagi')
        assert lot_qty(g['lot'])==10 and f.po_hpp(cur,g['po'])==hpp,(f.po_hpp(cur,g['po']),hpp)
        b.api.admin(cur);assert one(cur,'select status from erp.production_orders where id=%s',(g['po'],))=='FINISHED'
        return dict(status='PASS',reopened=r['result']['status'],finished_again=True,stock=10,hpp_same=[str(x) for x in hpp],finish=again['result']['status'] if 'result' in again else None)

    named=[lambda:sol_number(998),lambda:sol_number(999),astra_carry,past_1000,same_uuid_past_1000,
           astra_sales_cancel,astra_adjustment_reverse,active_use_blocks,unrelated_inflow,one_of_two,reopen_then_finish]
    assert len(named)+len(rate.NATIVE)==len(NATIVE)
    return list(zip(NATIVE[:len(named)],named))+rate.cases(cur,today)


def races(tools,today):
    import cp7_cp17_fix_cases as f
    import cp7_sales_draft_cases as drafts
    def two(fn,args):
        barrier=threading.Barrier(len(args))
        def send(a):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=fn(cur,a);conn.commit();return('PASS',r)
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=len(args))as pool:return [x.result(60) for x in [pool.submit(send,a) for a in args]]
    def boundary_two_sessions():
        # A day with no PO yet (each race has its own database copy): 998 unused headers, then two sessions post two
        # different rolls at once -> 999 and 1000.
        with tools.connect()as conn,conn.cursor()as cur:
            g1,g2=po.receipt(cur,today),po.receipt(cur,today)
            bodies=[po.post_body(g) for g in (g1,g2)];pre=po.prefix(cur,bodies[0]['cutting']['cut_at'])
            assert po.prefix(cur,bodies[1]['cutting']['cut_at'])==pre
            b.api.admin(cur);assert one(cur,'select count(*) from erp.production_orders where po_number like %s',(pre+'%',))==0
            fill(cur,pre,bodies[0],998,'CP17 r3 race boundary');start=oracle_next(cur,pre);assert start==pre+'999';conn.commit()
        results=two(lambda cur,body:po.command(cur,body),bodies)
        assert [x[0] for x in results]==['PASS','PASS'],results
        numbers=sorted((x[1]['po_number'] for x in results),key=lambda n:(len(n),n))
        n0=int(start.rsplit('-',1)[1]);assert numbers==[pre+str(n0).zfill(3),pre+str(n0+1).zfill(3)],(numbers,start)
        with tools.connect()as conn,conn.cursor()as cur:
            assert po.roll_stock(cur,g1)==0 and po.roll_stock(cur,g2)==0
            for n in numbers:assert po.po_state(cur,n)['posted']==1
        return dict(status='PASS',numbers=numbers,two_distinct_numbers=True,both_posted=True)
    def reopen_after_cancel():
        with tools.connect()as conn,conn.cursor()as cur:
            g=f.finish_fixture(cur,today,label='CP17-R3-RACE');f.finish_command(cur,f.finish_workspace(cur,g['po']))
            loc=one(cur,'select location_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id limit 1',(g['lot'],))
            customer=str(drafts.source.fg.base.create_customer(cur,'CP17-R3-'+uuid.uuid4().hex[:8]))
            s=dict(g,location=loc,customer=customer,tag='CP17-R3-'+uuid.uuid4().hex[:10],sale_at=(drafts.source.fg.ax.r1.now(cur)-timedelta(minutes=1)).isoformat())
            drafts.create(cur,s,drafts.payload(s,qty='2',price='13.37'))
            p,v=drafts.cmd.review(cur,s);drafts.cmd.command(cur,'CANCEL',p,v)
            w=f.reopen_workspace(cur,g['po']);assert w['eligible'],w['blockers'];conn.commit()
        results=two(lambda cur,n:f.reopen_command(cur,w,reason=f'CP17 r3 tab {n} membuka ulang PO')['result']['status'],[1,2])
        assert sorted(x[0] for x in results)==['PASS','REFUSED'] and 'CP7_PO_REOPEN_STALE_REVIEW' in next(x[1] for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);status=one(cur,'select status from erp.production_orders where id=%s',(g['po'],))
            history=one(cur,'select count(*) from cp7_cutting_correction.po_reopen_history where po_id=%s',(g['po'],))
        assert status!='FINISHED' and history==1,(status,history)
        return dict(status='PASS',two_tabs=results,reopened_once=True)
    return list(zip(RACES[:2],[boundary_two_sessions,reopen_after_cancel]))+rate.races(tools,today)


def http_cases(http,today):return rate.http_cases(http,today)
