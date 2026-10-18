"""r4 fixes of the r3 audits (candidate b53b5acd), spliced into the CP17 harness after r3.

R4-02 (Astra ASTRA-R2-01 remainder, r3 report audit/astra_cp17_r3): a finished PO stayed blocked after a +2 finished-goods
adjustment and its own inverse, because the -2 inverse was counted as a use of the PO's pieces. Astra's case
ASTRA_R3_REOPEN_POSITIVE_ADJUSTMENT_INVERSE is used as written (it returns COUNTEREXAMPLE while the reopen is refused),
plus controls: the inverse of an inflow does not hide an active use, and the reopened PO finishes again with the same
stock, HPP and a zero WIP balance; two tabs reopen it once.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import threading,uuid
import psycopg

NATIVE=['CP17_R4_02_REOPEN_POSITIVE_ADJUSTMENT_INVERSE_ASTRA','CP17_R4_02_POSITIVE_INVERSE_DOES_NOT_HIDE_ACTIVE_USE',
        'CP17_R4_02_POSITIVE_INVERSE_REOPEN_THEN_FINISH_SAME']
RACES=['CP17_RACE_R4_02_POSITIVE_INVERSE_REOPEN_TWO_TABS']
HTTP=[]
BROWSER=[]
FUNCTIONS=()


def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]


def cases(cur,today):
    import cp7_cp17_fix_cases as f
    import cp7_sales_draft_cases as drafts

    # ---- R4-02: Astra's case, as written in audit/astra_cp17_r3/risk_cases.py (positive_inverse).
    def astra_positive_inverse():
        g=f.finish_fixture(cur,today,label='ASTRA-R3-FG-POSITIVE')
        f.finish_command(cur,f.finish_workspace(cur,g['po']),reason='Astra all ten pieces finished')
        def qty():
            f.b.api.admin(cur)
            return one(cur,'select sum(qty_signed) from erp.fg_stock_movements where lot_id=%s',(g['lot'],))
        assert qty()==10 and f.reopen_workspace(cur,g['po'])['eligible']
        hpp=f.po_hpp(cur,g['po'])
        loc=one(cur,'select location_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id limit 1',(g['lot'],))
        draft,_=f.fgadj.draft(cur,dict(location=loc,lot=g['lot'],product=g['product']),'2')
        posted=f.fgadj.action(cur,'POST',draft);assert qty()==12
        f.fgadj.action(cur,'REVERSE',posted)
        assert qty()==10 and f.po_hpp(cur,g['po'])==hpp
        w=f.reopen_workspace(cur,g['po']);before=f.b.boundary.snapshot(cur)
        movements=[list(x)for x in cur.execute('select id::text,qty_signed,reversal_of_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id',(g['lot'],)).fetchall()]
        evidence=dict(stock=[10,12,10],hpp_before_after=[str(x)for x in hpp],movements=movements,blockers=w['blockers'],expected='positive adjustment and its own inverse leave no active downstream use')
        if not w['eligible']:
            refusal=f.refused(cur,lambda:f.reopen_command(cur,w,reason='Astra positive child already reversed'),'CP7_PO_REOPEN_BLOCKED')
            f.unchanged(cur,before,'positive adjustment inverse reopen refusal')
            return dict(status='COUNTEREXAMPLE',refusal=refusal,**evidence)
        r=f.reopen_command(cur,w,reason='Astra positive child already reversed')
        assert r['result']['status']!='FINISHED' and qty()==10 and f.po_hpp(cur,g['po'])==hpp
        return dict(status='PASS',result=r,**evidence)

    # ---- R4-02 controls (the r3 helpers, same writers).
    def lot_qty(lot):
        f.b.api.admin(cur);return one(cur,'select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(lot,))
    def finished(label):
        g=f.finish_fixture(cur,today,label=label)
        f.finish_command(cur,f.finish_workspace(cur,g['po']),reason='CP17 r4 produksi selesai')
        assert lot_qty(g['lot'])==10 and f.reopen_workspace(cur,g['po'])['eligible']
        return g
    def location(g):return one(cur,'select location_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id limit 1',(g['lot'],))
    def plus_two_then_inverse(g):
        draft,_=f.fgadj.draft(cur,dict(location=location(g),lot=g['lot'],product=g['product']),'2')
        posted=f.fgadj.action(cur,'POST',draft);f.fgadj.action(cur,'REVERSE',posted)
    def reserve(g,qty):
        customer=str(drafts.source.fg.base.create_customer(cur,'CP17-R4-'+uuid.uuid4().hex[:8]))
        s=dict(g,location=location(g),customer=customer,tag='CP17-R4-'+uuid.uuid4().hex[:10],
               sale_at=(drafts.source.fg.ax.r1.now(cur)-timedelta(minutes=1)).isoformat())
        drafts.create(cur,s,drafts.payload(s,qty=str(qty),price='13.37'));return s

    def active_use_not_hidden():
        g=finished('CP17-R4-ACTIVE');hpp=f.po_hpp(cur,g['po'])
        draft,_=f.fgadj.draft(cur,dict(location=location(g),lot=g['lot'],product=g['product']),'2')
        posted=f.fgadj.action(cur,'POST',draft);s=reserve(g,2);assert lot_qty(g['lot'])==10
        f.fgadj.action(cur,'REVERSE',posted);assert lot_qty(g['lot'])==8
        w=f.reopen_workspace(cur,g['po'])
        assert not w['eligible'] and w['blockers']==[dict(kind='FG_USED',qty=2)],w['blockers']
        before=f.b.boundary.snapshot(cur)
        f.refused(cur,lambda:f.reopen_command(cur,w,reason='CP17 r4 draf aktif sesudah +2 dibalik'),'CP7_PO_REOPEN_BLOCKED')
        f.unchanged(cur,before,'active draft after a reversed +2')
        p,v=drafts.cmd.review(cur,s);out=drafts.cmd.command(cur,'CANCEL',p,v);assert out['status']=='CANCELLED',out
        fresh=f.reopen_workspace(cur,g['po']);assert fresh['eligible'],fresh['blockers']
        assert lot_qty(g['lot'])==10 and f.po_hpp(cur,g['po'])==hpp
        return dict(status='PASS',stock=[10,12,10,8,10],blocked=w['blockers'],after_cancel_eligible=True)

    def reopen_then_finish():
        g=finished('CP17-R4-REFINISH');hpp=f.po_hpp(cur,g['po']);wip=f.po_wip_balance(cur,g['po'])
        plus_two_then_inverse(g);assert lot_qty(g['lot'])==10 and f.po_hpp(cur,g['po'])==hpp
        r=f.reopen_command(cur,f.reopen_workspace(cur,g['po']),reason='CP17 r4 buka ulang sesudah +2 dibalik')
        assert r['result']['status']!='FINISHED'
        f.finish_command(cur,f.finish_workspace(cur,g['po']),reason='CP17 r4 selesai lagi')
        f.b.api.admin(cur)
        assert one(cur,'select status from erp.production_orders where id=%s',(g['po'],))=='FINISHED'
        assert lot_qty(g['lot'])==10 and f.po_hpp(cur,g['po'])==hpp and f.po_wip_balance(cur,g['po'])==wip,(f.po_hpp(cur,g['po']),f.po_wip_balance(cur,g['po']),hpp,wip)
        return dict(status='PASS',reopened=r['result']['status'],finished_again=True,stock=10,hpp=[str(x)for x in hpp],wip_balance=str(wip))

    named=[astra_positive_inverse,active_use_not_hidden,reopen_then_finish]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):
    import cp7_cp17_fix_cases as f
    def two(fn,args):
        barrier=threading.Barrier(len(args))
        def send(a):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=fn(cur,a);conn.commit();return('PASS',r)
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=len(args))as pool:return [x.result(60) for x in [pool.submit(send,a) for a in args]]
    def positive_inverse_two_tabs():
        with tools.connect()as conn,conn.cursor()as cur:
            g=f.finish_fixture(cur,today,label='CP17-R4-RACE');f.finish_command(cur,f.finish_workspace(cur,g['po']))
            loc=one(cur,'select location_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id limit 1',(g['lot'],))
            draft,_=f.fgadj.draft(cur,dict(location=loc,lot=g['lot'],product=g['product']),'2')
            f.fgadj.action(cur,'REVERSE',f.fgadj.action(cur,'POST',draft))
            w=f.reopen_workspace(cur,g['po']);assert w['eligible'],w['blockers'];conn.commit()
        results=two(lambda cur,n:f.reopen_command(cur,w,reason=f'CP17 r4 tab {n} membuka ulang PO')['result']['status'],[1,2])
        assert sorted(x[0] for x in results)==['PASS','REFUSED'] and 'CP7_PO_REOPEN_STALE_REVIEW' in next(x[1] for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:
            f.b.api.admin(cur);status=one(cur,'select status from erp.production_orders where id=%s',(g['po'],))
            history=one(cur,'select count(*) from cp7_cutting_correction.po_reopen_history where po_id=%s',(g['po'],))
        assert status!='FINISHED' and history==1,(status,history)
        return dict(status='PASS',two_tabs=results,reopened_once=True)
    return list(zip(RACES,[positive_inverse_two_tabs]))


def http_cases(http,today):return []
