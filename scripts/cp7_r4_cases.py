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

R4-01 (Astra ASTRA-R3-01): the CP4 public wrappers erp_create/activate_attendance_hpp_pool_v1 created and activated a pool
in a closed period and after the manage right was revoked, through the real Data API, while the CP7 facade refused both.
The 25 older public routes the app does not call (cp7_public_routes_bundle.py) now refuse a Data API session first.
Astra's two HTTP cases are used as written (audit/astra_cp17_r3/risk_cases.py; they return COUNTEREXAMPLE while the old
route writes), plus controls: every closed route refused through real Auth with its own name, nothing written, the app's
routes still answer; a database session still reaches the Native writer while the same call as a Data API session is
refused; and a new public route, an anon-only route or a closed route that lost its refusal fails the review.

R4-04 (Astra ASTRA-R3-03): the connected WIP figures were nearly white on white cards. Browser cases
(cp7_r4_readable_browser.mjs) walk every menu as OWNER, desktop and phone, and refuse any text below 2:1 contrast with
its background; the WIP figures Astra named must reach 4.5:1.

R4-05 (owner D17-1, Sol KNOWN-P19-DIRECT-LATENCY): the owner report calls erp.require_internal() about 32,000 times per
analysis with financial figures; the guard now answers the case without any private command context row with one probe
(cp7_internal_guard_bundle.py). Native cases: the installed guard and the same guard without its probe give the same
answer for eight callers (owner, unknown user, service role, a context row of this transaction with its fine refusal,
rows of another backend or transaction), and a guard whose dispatch the probe no longer stands for fails the review.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json,threading,uuid
import psycopg

NATIVE=['CP17_R4_02_REOPEN_POSITIVE_ADJUSTMENT_INVERSE_ASTRA','CP17_R4_02_POSITIVE_INVERSE_DOES_NOT_HIDE_ACTIVE_USE',
        'CP17_R4_02_POSITIVE_INVERSE_REOPEN_THEN_FINISH_SAME','CP17_R4_03_AUDIT_LISTING_MARK_REFUSALS',
        'CP17_R4_01_DATA_API_REFUSED_DATABASE_SESSION_UNCHANGED','CP17_R4_01_EVERY_PUBLIC_ROUTE_REVIEWED',
        'CP17_R4_05_INTERNAL_GUARD_SAME_ANSWER','CP17_R4_05_INTERNAL_GUARD_DISPATCH_REVIEWED']
RACES=['CP17_RACE_R4_02_POSITIVE_INVERSE_REOPEN_TWO_TABS','CP17_RACE_R4_03_AUDIT_LOWER_ID_LATE_COMMIT_ASTRA',
       'CP17_RACE_R4_03_AUDIT_ORDINARY_ORDER_KEEPS_MARK','CP17_RACE_R4_03_AUDIT_LATE_ROW_OUTSIDE_FILTER',
       'CP17_RACE_R4_03_AUDIT_NEXT_LISTING_SHOWS_ALL_ONCE']
HTTP=['CP17_HTTP_R4_01_EVERY_CLOSED_ROUTE_REFUSED_APP_ROUTES_OPEN','CP17_HTTP_R4_01_POOL_PUBLIC_CLOSED_PERIOD_ASTRA',
      'CP17_HTTP_R4_01_POOL_PUBLIC_REVOKED_MANAGE_ASTRA']
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

    # ---- R4-01: the same call as a database session (fixtures, operators) and as a Data API session (PostgREST).
    import cp7_public_routes_bundle as routes
    import cp7_r3_hpp_pool_cases as pool
    def data_api(sql,args):
        """What a PostgREST request runs: session user authenticator, role authenticated, the Owner's claims."""
        f.b.api.admin(cur);cur.execute('savepoint r4_01_data_api')
        try:
            cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':f.b.chain.production.base.OPERATOR_AUTH,'role':'authenticated'}),))
            cur.execute('set session authorization authenticator');cur.execute('set role authenticated')
            assert cur.execute('select session_user,current_user').fetchone()==('authenticator','authenticated')
            cur.execute(sql,args);return dict(passed=True)
        except psycopg.Error as e:return dict(sqlstate=e.sqlstate,message=e.diag.message_primary,detail=e.diag.message_detail)
        finally:cur.execute('rollback to savepoint r4_01_data_api');cur.execute('release savepoint r4_01_data_api');cur.execute('reset role');f.b.api.admin(cur)
    def database_session_unchanged():
        g=pool.fixture(cur,today,offset=2);day=g['day'];f.b.api.admin(cur);before=f.b.boundary.snapshot(cur)
        calls=dict(erp_preview_attendance_hpp_pool_v1=('select public.erp_preview_attendance_hpp_pool_v1(%s,%s)',(day,day)),
                   erp_create_attendance_hpp_pool_v1=('select public.erp_create_attendance_hpp_pool_v1(%s::jsonb,%s)',
                       (json.dumps(dict(period_start=str(day),period_end=str(day),reason='CP17 R4-01 jalur lama')),uuid.uuid4())),
                   erp_save_worker_roster_v1=('select public.erp_save_worker_roster_v1(%s::jsonb,%s,null)',('{}',uuid.uuid4())))
        refused={}
        for name,(sql,args) in calls.items():
            r=data_api(sql,args)
            assert r==dict(sqlstate='42501',message=routes.REFUSAL,detail=name),(name,r)
            refused[name]=r
        f.unchanged(cur,before,'Data API session on the closed routes')
        languages={name:one(cur,'select l.lanname from pg_proc p join pg_language l on l.oid=p.prolang where p.oid=%s::regprocedure',(sig,))
                   for sig in routes.CLOSED for name in [routes.route(sig)] if name in calls}
        assert set(languages.values())=={'plpgsql','sql'},languages
        # The same pool calls as a database session reach the Native writer (the direct-SQL boundary is CP7C, D14-9).
        preview=f.s.native(cur,*calls['erp_preview_attendance_hpp_pool_v1'])
        made=f.s.native(cur,*calls['erp_create_attendance_hpp_pool_v1'])
        rows=pool.native_pools(cur,day);assert len(rows)==1 and rows[0]['status']=='DRAFT',(made,rows)
        return dict(status='PASS',data_api_refused=refused,languages=languages,nothing_written_while_refused=True,
                    database_session_preview=preview.get('status') if isinstance(preview,dict) else str(preview)[:80],database_session_created='DRAFT')
    def every_route_reviewed():
        f.b.api.admin(cur);clean=routes.verify(cur)
        assert clean['closed_to_data_api']==len(routes.CLOSED)==25 and clean['kept_reminder_routes']==4,clean
        # The app names exactly the kept routes (a new one needs review here first) and none of the closed ones.
        app=routes.app_routes()
        assert app==sorted(routes.route(x)for x in routes.KEEP) and not set(app)&{routes.route(x)for x in routes.CLOSED},app
        failures={}
        def attempt(label,statements):
            cur.execute('savepoint r4_01_review')
            try:
                for statement in statements:cur.execute(statement,prepare=False)
                try:routes.verify(cur);failures[label]=None
                except AssertionError as e:
                    code,what=e.args[0];failures[label]=(code,[x.removeprefix('public.')for x in what]if isinstance(what,list)else what)
            finally:cur.execute('rollback to savepoint r4_01_review');cur.execute('release savepoint r4_01_review')
        attempt('new_public_route',["create function public.erp_cp17_r4_unreviewed_v1()returns integer language sql as 'select 1'",
                                    'revoke all on function public.erp_cp17_r4_unreviewed_v1()from public,anon',
                                    'grant execute on function public.erp_cp17_r4_unreviewed_v1()to authenticated'])
        attempt('anon_only_route',["create function public.erp_cp17_r4_anon_only_v1()returns integer language sql as 'select 1'",
                                   'revoke all on function public.erp_cp17_r4_anon_only_v1()from public,authenticated',
                                   'grant execute on function public.erp_cp17_r4_anon_only_v1()to anon'])
        sig='public.erp_create_attendance_hpp_pool_v1(jsonb,uuid)'
        definition=one(cur,'select pg_get_functiondef(%s::regprocedure)',(sig,))
        line="\n perform cp7_public_routes.refuse_data_api('erp_create_attendance_hpp_pool_v1'); "+routes.MARK+"\n"
        assert definition.count(line)==1,definition[:400]
        attempt('closed_route_recreated_without_refusal',[definition.replace(line,'')])
        assert failures==dict(new_public_route=('R4_01_UNREVIEWED_PUBLIC_ROUTE',['erp_cp17_r4_unreviewed_v1()']),
                              anon_only_route=('R4_01_UNREVIEWED_PUBLIC_ROUTE',['erp_cp17_r4_anon_only_v1()']),
                              closed_route_recreated_without_refusal=('R4_01_ROUTE_NOT_CLOSED',sig)),failures
        assert routes.verify(cur)==clean
        return dict(status='PASS',reviewed=clean,app_routes=len(app),refused_until_reviewed=failures)

    # ---- R4-05 (owner D17-1): erp.require_internal() answers the common case with one context probe.
    import cp7_internal_guard_bundle as guard
    import cp7_sales_bundle as sales_bundle
    def guard_body():return one(cur,"select prosrc from pg_proc where oid='erp.require_internal()'::regprocedure")
    def guard_same_answer():
        """The installed guard and the same guard without its probe, called side by side as a Data API session."""
        f.b.api.admin(cur);clean=guard.verify(cur);before,_=guard.unpatched(guard_body())
        cur.execute("create schema cp17_r4_05;create function cp17_r4_05.guard_before()returns void language plpgsql security definer set search_path='' as $function$"
                    +before+"$function$",prepare=False)
        cur.execute("""create function cp17_r4_05.answer(p_before boolean)returns text language plpgsql security definer set search_path='' as $f$
begin
 if p_before then perform cp17_r4_05.guard_before();else perform erp.require_internal();end if;
 return 'ALLOW';
exception when others then return sqlstate||':'||sqlerrm;
end $f$;
grant usage on schema cp17_r4_05 to authenticated;grant execute on function cp17_r4_05.answer(boolean) to authenticated""",prepare=False)
        owner,stranger=f.b.chain.production.base.OPERATOR_AUTH,str(uuid.uuid4())
        def answers(sub,role='authenticated',setup=()):
            f.b.api.admin(cur);cur.execute('savepoint r4_05_guard')
            try:
                for statement in setup:cur.execute(statement,(sub,))
                cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':sub,'role':role}),))
                cur.execute('set session authorization authenticator');cur.execute('set role authenticated')
                return tuple(one(cur,'select cp17_r4_05.answer(%s)',(old,)) for old in (True,False))
            finally:cur.execute('rollback to savepoint r4_05_guard');cur.execute('release savepoint r4_05_guard');cur.execute('reset role');f.b.api.admin(cur)
        here="insert into cp7_sales.command_context(backend_pid,transaction_id,actor,sale_id,action)values(pg_backend_pid(),txid_current(),%s,null,'POST')"
        other_backend=here.replace('pg_backend_pid(),txid_current()','pg_backend_pid()+100000,txid_current()')
        other_transaction=here.replace('pg_backend_pid(),txid_current()','pg_backend_pid(),txid_current()-1')
        procurement=("insert into cp7_procurement.execution_context(backend_pid,transaction_id,actor,action,permission_key)"
                     "values(pg_backend_pid(),txid_current(),%s,'POST','warehouse.procurement.post')")
        internal='P0001:Internal ERP access required'
        expected=dict(owner_no_context=((owner,),'ALLOW'),stranger_no_context=((stranger,),internal),
                      service_role_no_app_user=((stranger,'service_role'),'ALLOW'),
                      # A context row of this backend and transaction: the unchanged dispatch, its fine refusal first.
                      stranger_sales_context_here=((stranger,'authenticated',(here,)),'42501:CP7_SALES_ACCESS_DENIED'),
                      # (its answer depends on the Native owner grant; only before == after is required)
                      owner_sales_context_here=((owner,'authenticated',(here,)),None),
                      stranger_procurement_context_without_right=((stranger,'authenticated',(procurement,)),internal),
                      # Rows of another backend or another transaction admit nothing.
                      owner_sales_context_other_backend=((owner,'authenticated',(other_backend,)),'ALLOW'),
                      stranger_sales_context_other_transaction=((stranger,'authenticated',(other_transaction,)),internal))
        observed={k:answers(*args) for k,(args,_) in expected.items()}
        assert all(a==b and want in(None,a) for (a,b),(_,want) in zip(observed.values(),expected.values())),observed
        return dict(status='PASS',reviewed=clean,before_and_after=observed,transaction_id_assigned=one(cur,'select txid_current_if_assigned() is not null'))
    def guard_dispatch_reviewed():
        """A guard whose dispatch the probe no longer stands for fails the review (verify), so CI stops."""
        f.b.api.admin(cur);clean=guard.verify(cur)
        definition=one(cur,"select pg_get_functiondef('erp.require_internal()'::regprocedure)")
        _,fast=guard.unpatched(guard_body())
        failures={}
        def attempt(label,changed):
            assert changed!=definition,label
            cur.execute('savepoint r4_05_review')
            try:
                cur.execute(changed,prepare=False)
                try:guard.verify(cur);failures[label]=None
                except AssertionError as e:failures[label]=e.args[0] if isinstance(e.args[0],str) else e.args[0][0]
            finally:cur.execute('rollback to savepoint r4_05_review');cur.execute('release savepoint r4_05_review')
        branch=(" if exists(select 1 from cp7_misc.command_context c where c.backend_pid=pg_backend_pid()\n"
                "  and c.transaction_id=txid_current() and case when c.backend_pid=pg_backend_pid()\n"
                "   and c.transaction_id=txid_current() and c.actor=auth.uid() then true else false end) then return;end if;\n")
        attempt('context_branch_added_after_the_probe',definition.replace(sales_bundle.ANCHOR,branch+sales_bundle.ANCHOR,1))
        attempt('other_statement_in_the_dispatch',definition.replace(sales_bundle.ANCHOR," perform erp.has_permission('x');\n"+sales_bundle.ANCHOR,1))
        attempt('probe_removed',definition.replace(guard.ANCHOR+'\n'+fast,guard.ANCHOR,1))
        assert failures==dict(context_branch_added_after_the_probe='CP7_INTERNAL_GUARD_PROBE_DIFFERS',
                              other_statement_in_the_dispatch='CP7_INTERNAL_GUARD_DISPATCH_CHANGED',
                              probe_removed='CP7_INTERNAL_GUARD_PROBE_MISSING'),failures
        assert guard.verify(cur)==clean
        return dict(status='PASS',reviewed=clean,refused_until_reviewed=failures)

    named=[astra_positive_inverse,active_use_not_hidden,reopen_then_finish,audit_mark_refusals,database_session_unchanged,every_route_reviewed,
           guard_same_answer,guard_dispatch_reviewed]
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


def http_cases(http,today):
    import cp7_cp17_fix_cases as f
    import cp7_public_routes_bundle as routes
    import cp7_r3_hpp_pool_cases as pool
    def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]

    # ---- R4-01 control: every closed route through real Auth and PostgREST, with arguments of the right types.
    def every_closed_route():
        owner=http.login('OWNER','cp17-r4-01-owner')
        dummy={'jsonb':{},'uuid':lambda:str(uuid.uuid4()),'text':'CP17 R4-01 jalur lama','date':str(today),'numeric':1,'integer':1,
               'bigint':1,'boolean':False,'timestamp with time zone':lambda:f'{today}T10:00:00+07:00'}
        with http.connect()as conn,conn.cursor()as cur:
            shapes={sig:cur.execute("select p.proargnames,array(select format_type(t,null) from unnest(p.proargtypes::oid[]) t) from pg_proc p "
                                    "where p.oid=%s::regprocedure",(sig,)).fetchone() for sig in routes.CLOSED}
            granted={sig:one(cur,"select has_function_privilege('authenticated',%s,'EXECUTE')",(sig,))for sig in routes.CLOSED}
            before=f.b.boundary.snapshot(cur);conn.commit()
        assert all(granted.values()),granted
        answers={}
        for sig,(names,types) in shapes.items():
            assert names and len(names)==len(types),(sig,names,types)
            args={n:(dummy[t]()if callable(dummy[t])else dummy[t])for n,t in zip(names,types)}
            r=owner.rpc(routes.route(sig),args);body=r['body']if isinstance(r['body'],dict)else{}
            assert (r['status'],body.get('code'),body.get('message'),body.get('details'))==(403,'42501',routes.REFUSAL,routes.route(sig)),(sig,r)
            answers[sig]=r['status']
        anon=http.anon_rpc('erp_create_attendance_hpp_pool_v1',dict(p_payload={},p_client_request_id=str(uuid.uuid4())))
        assert anon['status']>=400,anon
        with http.connect()as conn,conn.cursor()as cur:assert f.b.boundary.snapshot(cur)==before,'CP17_R4_01_CLOSED_ROUTE_WROTE'
        # The routes the app calls still answer through the same Data API (the guard sits only in the closed ones).
        access=owner.rpc('erp_get_my_access_v1',{});pools=owner.rpc('erp_cp7_get_hpp_pools_v1',dict(p_offset=0,p_limit=20,p_period_start=None,p_period_end=None))
        assert access['status']==200 and pools['status']==200,(access,pools)
        return dict(status='PASS',real_Auth=True,closed_routes_refused=len(answers),answer=sorted(set(answers.values())),grants_unchanged=True,
                    anon_refused=anon['status'],nothing_written=True,app_routes_answer=dict(erp_get_my_access_v1=200,erp_cp7_get_hpp_pools_v1=200))

    # ---- R4-01: Astra's two cases, as written in audit/astra_cp17_r3/risk_cases.py (legacy_closed, legacy_permission).
    def legacy_closed():
        user=http.login('OWNER','astra-r3-pool-closed')
        with http.connect()as conn,conn.cursor()as cur:
            g=pool.fixture(cur,today,offset=3);day=g['day'];pool.set_closed(cur,day)
            pv=pool.read(cur,user.auth_user_id,day,day)['preview'];before=f.b.boundary.snapshot(cur);conn.commit()
        current=user.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CREATE',p_payload=pool.create_body(pv),p_request=str(uuid.uuid4())))
        assert current['status']>=400 and 'CP7_HPP_POOL_PERIOD_CLOSED' in json.dumps(current['body']),current
        with http.connect()as conn,conn.cursor()as cur:assert f.b.boundary.snapshot(cur)==before
        cr=user.rpc('erp_create_attendance_hpp_pool_v1',dict(p_payload=dict(period_start=str(day),period_end=str(day),reason='Astra closed period old public route'),p_client_request_id=str(uuid.uuid4())))
        if cr['status']>=400:
            with http.connect()as conn,conn.cursor()as cur:assert f.b.boundary.snapshot(cur)==before
            return dict(status='PASS',new_route=current,old_route=cr,closed_boundary_unchanged=True)
        with http.connect()as conn,conn.cursor()as cur:
            rows=pool.native_pools(cur,day);assert len(rows)==1 and rows[0]['status']=='DRAFT',rows
            pid=rows[0]['id'];version=rows[0]['row_version']
        ac=user.rpc('erp_activate_attendance_hpp_pool_v1',dict(p_pool_id=pid,p_reason='Astra old public activation closed books',p_client_request_id=str(uuid.uuid4()),p_expected_version=version))
        with http.connect()as conn,conn.cursor()as cur:
            rows=pool.native_pools(cur,day);cost=pool.active_view(cur,g['po_a'])
            journals=[list(x)for x in cur.execute("select status,source_type,economic_date,transaction_date from erp.journal_entries where source_id=%s order by economic_date,id",(pid,)).fetchall()]
            grants={n:one(cur,"select has_function_privilege('authenticated',%s,'EXECUTE')",(n,))for n in ('public.erp_create_attendance_hpp_pool_v1(jsonb,uuid)','public.erp_activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)')}
        return dict(status='COUNTEREXAMPLE',expected='closed-period pool actions refused through every reachable public route',
                    real_Auth=True,public_Data_API=True,test_only_schema_grant=False,cp7_refused=current,legacy_create=cr,legacy_activate=ac,
                    native_rows=rows,po_active_cost=str(cost),journals=journals,grants=grants,
                    owner_boundary='D14-9 deferral explicitly conditioned on functions being unreachable from internet; these are public facades')

    def legacy_permission():
        user=http.login('ADMIN','astra-r3-pool-permission')
        with http.connect()as conn,conn.cursor()as cur:
            g=pool.fixture(cur,today,offset=1);day=g['day']
            role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(user.auth_user_id,))
            cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')on conflict do nothing",(role,))
            pv=pool.read(cur,user.auth_user_id,day,day)['preview']
            cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.manage'",(role,))
            before=f.b.boundary.snapshot(cur);conn.commit()
        new=user.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CREATE',p_payload=pool.create_body(pv),p_request=str(uuid.uuid4())))
        assert new['status']>=400 and 'CP7_HPP_POOL_DENIED' in json.dumps(new['body']),new
        with http.connect()as conn,conn.cursor()as cur:assert f.b.boundary.snapshot(cur)==before
        old=user.rpc('erp_create_attendance_hpp_pool_v1',dict(p_payload=dict(period_start=str(day),period_end=str(day),reason='Astra public route after manage revoked'),p_client_request_id=str(uuid.uuid4())))
        with http.connect()as conn,conn.cursor()as cur:
            rows=pool.native_pools(cur,day)
            if old['status']>=400:assert f.b.boundary.snapshot(cur)==before
            else:assert len(rows)==1 and rows[0]['status']=='DRAFT'
        return dict(status='COUNTEREXAMPLE' if old['status']==200 else 'PASS',expected='revoked HPP manage right respected by every public pool writer',
                    real_Auth=True,public_Data_API=True,test_only_schema_grant=False,cp7_refused=new,legacy=old,native_rows=rows)
    # Astra's closed-period case leaves the books closed through its day and the permission case leaves ADMIN without
    # finance.hpp.manage (as written), so they run last.
    return list(zip(HTTP,[every_closed_route,legacy_closed,legacy_permission]))
