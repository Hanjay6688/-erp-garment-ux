"""r4 fixes of the r3 audits (candidate b53b5acd), spliced into the CP17 harness after r3.

R4-02 (Astra ASTRA-R2-01 remainder, r3 report audit/astra_cp17_r3): a finished PO stayed blocked after a +2 finished-goods
adjustment and its own inverse, because the -2 inverse was counted as a use of the PO's pieces. Astra's case
ASTRA_R3_REOPEN_POSITIVE_ADJUSTMENT_INVERSE is used as written (it returns COUNTEREXAMPLE while the reopen is refused),
plus controls: the inverse of an inflow does not hide an active use, and the reopened PO finishes again with the same
stock, HPP and a zero WIP balance; two tabs reopen it once.

R4-03 (Astra ASTRA-R3-02): the Audit Trail listing skipped a lower log id that committed after the first page (231 held
while 232 commits) without saying anything. Every listing now carries the mark of its rows inside the cutoff
(snapshot.listed, also in the keyset cursor) and a later page whose mark differs says so (snapshot.changed and newer).
Astra's three-session schedule ASTRA_R3_AUDIT_LOWER_ID_LATE_COMMIT is used as written (audit/astra_cp17_r3/
audit_paging_case.py), plus controls: ordinary commit order keeps the mark and walks every row once; a late row outside
the filter leaves the listing unchanged; the next listing (Muat ulang) shows all rows once; a mark without a cutoff, a
cursor mark that differs from the one sent and a malformed cursor are refused.

R4-04 (Astra ASTRA-R3-03): the connected WIP figures were nearly white on white cards. Browser cases
(cp7_r4_readable_browser.mjs) walk every menu as OWNER, desktop and phone, and refuse any text below 2:1 contrast with
its background; the WIP figures Astra named must reach 4.5:1.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import threading,uuid
import psycopg

NATIVE=['CP17_R4_02_REOPEN_POSITIVE_ADJUSTMENT_INVERSE_ASTRA','CP17_R4_02_POSITIVE_INVERSE_DOES_NOT_HIDE_ACTIVE_USE',
        'CP17_R4_02_POSITIVE_INVERSE_REOPEN_THEN_FINISH_SAME','CP17_R4_03_AUDIT_LISTING_MARK_REFUSALS']
RACES=['CP17_RACE_R4_02_POSITIVE_INVERSE_REOPEN_TWO_TABS','CP17_RACE_R4_03_AUDIT_LOWER_ID_LATE_COMMIT_ASTRA',
       'CP17_RACE_R4_03_AUDIT_ORDINARY_ORDER_KEEPS_MARK','CP17_RACE_R4_03_AUDIT_LATE_ROW_OUTSIDE_FILTER',
       'CP17_RACE_R4_03_AUDIT_NEXT_LISTING_SHOWS_ALL_ONCE']
HTTP=[]
BROWSER=['CP17_BROWSER_R4_04_CONNECTED_TEXT_READABLE_DESKTOP','CP17_BROWSER_R4_04_CONNECTED_TEXT_READABLE_MOBILE']
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

    # ---- R4-03: a listing mark belongs to one cutoff and one cursor; anything else is refused before reading.
    def audit_mark_refusals():
        import cp7_r3_audit_cases as a
        tag='R4M'+uuid.uuid4().hex[:8].upper();subject,_=a.person(cur,'OWNER','Audit tanda '+tag)
        first=a.read(cur,dict(q=tag,limit=3),subject);mark=first['snapshot']['listed']
        assert first['snapshot']['changed'] is False and first['snapshot']['newer'] is False,first['snapshot']
        refusals={}
        for name,q in (('mark_without_cutoff',dict(q=tag,listed=mark)),
                       ('cursor_mark_not_the_one_sent',dict(q=tag,as_of=first['snapshot']['as_of'],after='1:1-1',listed='2-2')),
                       ('malformed_cursor',dict(q=tag,as_of=first['snapshot']['as_of'],after='1:x'))):
            refusals[name]=f.refused(cur,lambda q=q:a.read(cur,q,subject),'CP7_AUDIT_QUERY')
        return dict(status='PASS',first_mark=mark,refused=refusals)

    named=[astra_positive_inverse,active_use_not_hidden,reopen_then_finish,audit_mark_refusals]
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
    # ---- R4-03: Astra's schedule, as written in audit/astra_cp17_r3/audit_paging_case.py (schedule).
    import cp7_r3_audit_cases as a
    import cp7_master_cases as master
    def astra_late_commit():
        tag='A3P'+uuid.uuid4().hex[:9].upper();reason='Astra audit paging '+tag
        with tools.connect()as conn,conn.cursor()as cur:
            subject,_=a.person(cur,'OWNER',tag)
            for i in range(7):master.create(cur,'CUSTOMER',master.customer_fields(tag+str(i),'Astra seed '+str(i)),reason=reason+' seed '+str(i),subject=subject)
            conn.commit()
        held=tools.connect();h=held.cursor()
        try:
            delayed=master.create(h,'CUSTOMER',master.customer_fields(tag+'A','Astra lower id late commit'),reason=reason+' HELD',subject=subject)['id']
            held_id=a.one(h,"select max(id) from erp.audit_logs where entity_id=%s and change_reason=%s",(delayed,reason+' HELD'))
            # A second writer commits a higher sequence id while the lower one is still invisible.
            with tools.connect()as conn,conn.cursor()as cur:
                higher=master.create(cur,'CUSTOMER',master.customer_fields(tag+'B','Astra higher id first commit'),reason=reason+' HIGHER',subject=subject)['id']
                higher_id=a.one(cur,"select max(id) from erp.audit_logs where entity_id=%s and change_reason=%s",(higher,reason+' HIGHER'));conn.commit()
            with tools.connect()as conn,conn.cursor()as cur:
                first=a.read(cur,dict(q=reason,limit=3),subject)
                invisible=a.one(cur,'select count(*) from erp.audit_logs where id=%s',(held_id,))==0
                session=a.one(cur,"select state from pg_stat_activity where pid=%s",(held.info.backend_pid,))
            asof=first['snapshot']['as_of']
            assert invisible and held_id<higher_id<=int(asof) and session=='idle in transaction',(invisible,held_id,higher_id,asof,session)
            assert first['page']['total']=='8' and first['page']['next_after'] is not None,first
            held.commit()
        finally:
            held.close()
        pages=[first]
        for _ in range(10):
            cursor=pages[-1]['page']['next_after']
            if cursor is None:break
            with tools.connect()as conn,conn.cursor()as cur:
                pages.append(a.read(cur,dict(q=reason,limit=3,as_of=asof,after=cursor),subject))
        assert pages[-1]['page']['next_after'] is None
        with tools.connect()as conn,conn.cursor()as cur:
            fresh=a.read(cur,dict(q=reason,limit=100,as_of=asof),subject)
            actual=[str(r[0])for r in cur.execute('select id from erp.audit_logs where change_reason like %s order by changed_at desc,id desc',(reason+'%',)).fetchall()]
        walked=[r['id']for p in pages for r in p['page']['rows']]
        current=[r['id']for r in fresh['page']['rows']]
        assert current==actual and len(actual)==9 and str(held_id) in actual,(current,actual)
        signalled=any(p['snapshot']['newer']for p in pages[1:])
        missed=sorted(set(actual)-set(walked))
        bad=bool(missed) and not signalled
        return dict(status='COUNTEREXAMPLE' if bad else 'PASS',expected='a committed row inside the listing cutoff is either visited or an explicit new-data indication requests reload',
                    ordinary_master_writes=True,native_audit_trigger=True,held_id=held_id,higher_committed_id=higher_id,as_of=asof,
                    observed_holder_state=session,held_row_invisible_at_first_page=invisible,first_count=8,final_count=9,
                    page_totals=[p['page']['total']for p in pages],page_ids=[[r['id']for r in p['page']['rows']]for p in pages],
                    all_native_ids=actual,missed_ids=missed,newer_signalled=signalled,fresh_same_cutoff_ids=current,
                    changed=[p['snapshot']['changed']for p in pages])

    # ---- R4-03 controls.
    def seed(n,label):
        tag='R4A'+uuid.uuid4().hex[:9].upper();reason=f'CP17 r4 audit {label} {tag}'
        with tools.connect()as conn,conn.cursor()as cur:
            subject,_=a.person(cur,'OWNER',tag)
            for i in range(n):master.create(cur,'CUSTOMER',master.customer_fields(f'{tag}{i}',f'Toko r4 {i}'),reason=f'{reason} seed {i}',subject=subject)
            conn.commit()
        return tag,reason,subject
    def walk(first,q,subject):
        pages=[first]
        while pages[-1]['page']['next_after'] is not None:
            with tools.connect()as conn,conn.cursor()as cur:
                pages.append(a.read(cur,dict(q,as_of=first['snapshot']['as_of'],after=pages[-1]['page']['next_after']),subject))
            assert len(pages)<=50
        return pages
    def committed(reason):
        with tools.connect()as conn,conn.cursor()as cur:
            return [str(r[0])for r in cur.execute('select id from erp.audit_logs where change_reason like %s order by changed_at desc,id desc',(reason+'%',)).fetchall()]
    def ordinary_order():
        tag,reason,subject=seed(7,'urutan biasa')
        with tools.connect()as conn,conn.cursor()as cur:first=a.read(cur,dict(q=reason,limit=3),subject)
        listed=committed(reason)
        # A write after the first page takes a higher id: outside this listing, said as newer, the mark unchanged.
        with tools.connect()as conn,conn.cursor()as cur:
            master.create(cur,'CUSTOMER',master.customer_fields(tag+'N','Toko r4 baru'),reason=reason+' baru',subject=subject);conn.commit()
        pages=walk(first,dict(q=reason,limit=3),subject)
        walked=[r['id']for p in pages for r in p['page']['rows']]
        assert walked==listed and len(set(walked))==7,(walked,listed)
        assert [p['snapshot']['changed']for p in pages]==[False]*len(pages) and all(p['snapshot']['newer']for p in pages[1:]),[p['snapshot']for p in pages]
        assert len({p['snapshot']['listed']for p in pages})==1 and all(p['page']['total']=='7' for p in pages)
        return dict(status='PASS',walked=walked,mark=first['snapshot']['listed'],changed=False,newer_after_first=True)
    def late_outside_filter():
        tag,reason,subject=seed(7,'luar filter')
        held=tools.connect();h=held.cursor()
        try:
            # The held write is another listing's (a different reason); a higher id of this listing commits first.
            master.create(h,'CUSTOMER',master.customer_fields(tag+'X','Toko r4 lain'),reason=f'CP17 r4 lain {tag}',subject=subject)
            with tools.connect()as conn,conn.cursor()as cur:
                master.create(cur,'CUSTOMER',master.customer_fields(tag+'B','Toko r4 tinggi'),reason=reason+' tinggi',subject=subject);conn.commit()
            with tools.connect()as conn,conn.cursor()as cur:first=a.read(cur,dict(q=reason,limit=3),subject)
            held.commit()
        finally:held.close()
        pages=walk(first,dict(q=reason,limit=3),subject)
        walked=[r['id']for p in pages for r in p['page']['rows']]
        assert walked==committed(reason) and len(walked)==8,walked
        assert [p['snapshot']['changed']for p in pages]==[False]*len(pages),[p['snapshot']for p in pages]
        return dict(status='PASS',walked=len(walked),late_row_outside_filter_does_not_change_listing=True)
    def next_listing():
        tag,reason,subject=seed(7,'muat ulang')
        held=tools.connect();h=held.cursor()
        try:
            master.create(h,'CUSTOMER',master.customer_fields(tag+'A','Toko r4 telat'),reason=reason+' telat',subject=subject)
            with tools.connect()as conn,conn.cursor()as cur:
                master.create(cur,'CUSTOMER',master.customer_fields(tag+'B','Toko r4 tinggi'),reason=reason+' tinggi',subject=subject);conn.commit()
            with tools.connect()as conn,conn.cursor()as cur:first=a.read(cur,dict(q=reason,limit=3),subject)
            held.commit()
        finally:held.close()
        pages=walk(first,dict(q=reason,limit=3),subject)
        assert all(p['snapshot']['changed'] and p['snapshot']['newer'] for p in pages[1:]),[p['snapshot']for p in pages]
        # Muat ulang: a new listing (no cutoff sent) has all nine, each once, and an unchanged mark to the end.
        with tools.connect()as conn,conn.cursor()as cur:again=a.read(cur,dict(q=reason,limit=3),subject)
        fresh=walk(again,dict(q=reason,limit=3),subject)
        walked=[r['id']for p in fresh for r in p['page']['rows']]
        assert walked==committed(reason) and len(walked)==len(set(walked))==9,walked
        assert [p['snapshot']['changed']for p in fresh]==[False]*len(fresh) and again['snapshot']['listed']!=first['snapshot']['listed']
        return dict(status='PASS',first_listing_said_changed=True,next_listing_rows=9,each_once=True)
    return list(zip(RACES,[positive_inverse_two_tabs,astra_late_commit,ordinary_order,late_outside_filter,next_listing]))


def http_cases(http,today):return []
