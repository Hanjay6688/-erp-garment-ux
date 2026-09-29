"""P10 presentation-book oracles; stock, HPP, journals and physical time stay fixed."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json,threading,time,uuid
import psycopg
import cp7_fg_cases as fg
import cp7_fg_adjustment_cases as adj
import cp7_procurement_cases as procurement
auth,b=fg.p02,fg.b

def rpc(cur,name,args,subject=None):
    assert name in ('erp_cp7_get_fg_book_v1','erp_cp7_save_fg_book_v1','erp_cp7_get_fg_book_options_v1')
    auth.actor(cur,subject);r=cur.execute('select public.'+name+'('+','.join(['%s']*len(args))+')',args).fetchone()[0];b.api.admin(cur);return r
def read(cur,f=None,subject=None,**q):return rpc(cur,'erp_cp7_get_fg_book_v1',[json.dumps(dict(q=f['sku'] if f else '',**q))],subject)
def command(cur,action,p,key=None,subject=None):return rpc(cur,'erp_cp7_save_fg_book_v1',[action,json.dumps(p),key or uuid.uuid4()],subject)
def options(cur,kind,q='',off=0,n=25,subject=None):return rpc(cur,'erp_cp7_get_fg_book_options_v1',[kind,q,off,n],subject)
def move_payload(w,source,target,placement='BEFORE'):return dict(book_token=w['book_token'],source_id=source,target_id=target,placement=placement)
def fixture(cur,today):
    f=fg.fixture(cur,today)
    at=(fg.ax.r1.now(cur)-timedelta(minutes=40)).isoformat()
    fg.ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=f['product'],location_id=f['location'],qty_pcs=5,physical_at=at,reason='P10 book second lot',owner_unit_value='10',owner_value_reason='P10 independently supplied physical valuation'))
    d=fg.draft(cur,f);fg.post_sale(cur,d)
    rows=read(cur,f)['page']['rows'];assert len(rows)==3,rows
    return dict(f,first=rows[0]['id'],second=rows[1]['id'],sale=rows[2]['id'],brand=rows[0]['brand_id'],customer=rows[2]['customer_id'])
def facts(cur):
    # Full business movement row except its explicitly allowed presentation rank.
    return {name:cur.execute(sql).fetchone()[0] for name,sql in {
      'movements':"select md5(coalesce(jsonb_agg(to_jsonb(m)-'book_order' order by id)::text,'')) from erp.fg_stock_movements m",
      'hpp':"select md5(coalesce(jsonb_agg(to_jsonb(h) order by id)::text,'')) from erp.hpp_versions h",
      'journals':"select md5(coalesce(jsonb_agg(to_jsonb(j) order by id)::text,'')) from erp.journal_lines j",
    }.items()}

def cases(cur,today):
    def reorder():
        f=fixture(cur,today);w=read(cur,f);before=facts(cur);accounts=adj.accounts(cur)
        assert [r['book_physical_after'] for r in w['page']['rows']]==['10','15','11'],w
        initial=fg.ledger(cur,f);key=uuid.uuid4();p=move_payload(w,f['sale'],f['first']);out=command(cur,'MOVE',p,key)
        assert command(cur,'MOVE',p,key)==out
        moved=read(cur,f);rows=moved['page']['rows']
        assert [r['id'] for r in rows]==[f['sale'],f['first'],f['second']],rows
        assert [r['book_physical_after'] for r in rows]==['-4','6','11'],rows
        assert [r['official_physical_after'] for r in rows]==['11','10','15'],rows
        assert facts(cur)==before and adj.accounts(cur)==accounts and fg.qty(fg.workspace(cur,f))==[11,0,11]
        after=fg.ledger(cur,f)
        assert after['balances']==initial['balances'] and [(r['id'],r['physical_balance']) for r in after['page']['rows']]==[(r['id'],r['physical_balance']) for r in initial['page']['rows']]
        assert cur.execute("select count(*) from erp.audit_logs where entity_id=%s and new_data->>'presentation_only'='true'",(f['sale'],)).fetchone()[0]==1
        return dict(status='PASS',two_native_lots=True,book_prefix=[-4,6,11],official=[11,10,15],physical_available=11,all_movement_facts_hpp_journals_and_stock_card_unchanged=True,one_native_audit_on_exact_replay=True)
    def reset():
        f=fixture(cur,today);before=facts(cur);w=read(cur,f);command(cur,'MOVE',move_payload(w,f['sale'],f['first']))
        w=read(cur,f);key=uuid.uuid4();p=dict(book_token=w['book_token']);r=command(cur,'RESET',p,key);assert command(cur,'RESET',p,key)==r
        rows=read(cur,f)['page']['rows'];assert [r['id'] for r in rows]==[f['first'],f['second'],f['sale']]
        assert [r['book_physical_after'] for r in rows]==['10','15','11'] and facts(cur)==before
        assert cur.execute('select action,response is not null from cp7_fg.requests where request_id=%s',(key,)).fetchone()==('BOOK_RESET',True)
        return dict(status='PASS',accepted_native_reset=True,all_book_chronology_restored=True,private_actor_intent_result_record=True,business_facts_unchanged=True)
    def filters():
        f=fixture(cur,today);w=read(cur,f,limit=1,offset=2);r=w['page']['rows'][0]
        assert w['page']['total']=='3' and w['page']['next_offset'] is None and r['book_physical_before']=='15' and r['book_physical_after']=='11'
        selected=read(cur,f,brand_ids=[f['brand']],customer_ids=[f['customer']],movement_types=['SALE'],**{'from':(fg.ax.r1.now(cur)-timedelta(minutes=20)).isoformat()})
        assert selected['page']['total']=='1' and selected['page']['rows'][0]['book_physical_before']=='15',selected
        assert read(cur,f,brand_ids=[str(uuid.uuid4())])['page']['total']=='0'
        # Actual seeded masters: the ordinary stock fixture may have only one brand.
        cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s)',('BOOK-'+uuid.uuid4().hex[:12],'Book pagination control'))
        page=options(cur,'BRAND',off=0,n=1);assert len(page['page']['rows'])==1 and page['page']['next_offset']==1
        next_page=options(cur,'BRAND',off=1,n=1);assert next_page['page']['total']==page['page']['total'] and page['page']['rows'][0]['id']!=next_page['page']['rows'][0]['id']
        customer=options(cur,'CUSTOMER');assert customer['kind']=='CUSTOMER'
        auth.refused(cur,lambda:read(cur,f,brand_ids='forged'),'CP7_FG_BOOK_FILTER')
        auth.refused(cur,lambda:read(cur,f,limit=101),'CP7_FG_BOOK_QUERY')
        return dict(status='PASS',all_filters_and_page_applied_after_complete_prefix=True,sale_only_beginning=15,ending=11,option_pagination=True,second_brand_master_fixture=True)
    def reservation():
        f=fg.fixture(cur,today);d=fg.draft(cur,f);w=read(cur,f);r=w['page']['rows'][-1]
        assert [r['physical_delta'],r['reservation_delta'],r['available_delta'],r['book_physical_after'],r['book_reserved_after'],r['book_available_after']]==['0','4','-4','10','4','6']
        fg.cancel(cur,d);r=read(cur,f)['page']['rows'][-1]
        assert [r['physical_delta'],r['reservation_delta'],r['available_delta'],r['book_physical_after'],r['book_reserved_after'],r['book_available_after']]==['0','-4','4','10','0','10'],r
        return dict(status='PASS',reservations_and_cancellation_not_physical_outflow=True,physical=[10,10],available=[6,10])
    def stale():
        f=fixture(cur,today);w=read(cur,f);p=move_payload(w,f['sale'],f['first']);key=uuid.uuid4();command(cur,'MOVE',p,key);before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:command(cur,'MOVE',move_payload(w,f['second'],f['first'])),'CP7_FG_BOOK_STALE_RELOAD')
        changed=dict(p,placement='AFTER');auth.refused(cur,lambda:command(cur,'MOVE',changed,key),'CP7_FG_BOOK_REQUEST_CHANGED')
        current=read(cur,f);auth.refused(cur,lambda:command(cur,'MOVE',move_payload(current,str(uuid.uuid4()),f['first'])),'CP7_FG_BOOK_SOURCE_MISSING')
        auth.refused(cur,lambda:command(cur,'MOVE',move_payload(current,f['first'],f['first'])),'CP7_FG_BOOK_ANCHOR')
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',stale_global_order_exact_uuid_anchor_validation_atomic=True)
    def access():
        f=fixture(cur,today);subject,role=procurement.custom(cur,('warehouse.movement.view',));w=read(cur,f,subject);assert not w['can_order'] and 'hpp' not in json.dumps(w)
        auth.refused(cur,lambda:command(cur,'MOVE',move_payload(w,f['sale'],f['first']),subject=subject),'CP7_FG_BOOK_ORDER_DENIED')
        cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));auth.refused(cur,lambda:read(cur,f,subject),'CP7_FG_ACCESS_DENIED')
        for who in ('anon','authenticated','service_role','cp7_capture'):assert not cur.execute("select has_schema_privilege(%s,'cp7_fg','USAGE')",(who,)).fetchone()[0]
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_fg_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        return dict(status='PASS',book_permission_separate=True,no_money_fields=True,current_revocation=True,private_writer_no_business_select_or_dml=True)
    return [('P10_BOOK_'+k,fn) for k,fn in [('REORDER_FACTS',reorder),('RESET',reset),('FILTER_PREFIX_PAGES',filters),('RESERVATIONS',reservation),('STALE_ATOMIC',stale),('AUTH_PRIVATE',access)]]

def races(tools,today):
    def compete():
        with tools.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);w=read(cur,f);before=facts(cur);conn.commit()
        barrier=threading.Barrier(2)
        def send(source):
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait()
                try:r=command(cur,'MOVE',move_payload(w,source,f['first']));conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:jobs=[pool.submit(send,s) for s in (f['sale'],f['second'])];results=[j.result(30) for j in jobs]
        assert sum(isinstance(r,dict) for r in results)==1 and any('CP7_FG_BOOK_STALE_RELOAD' in r for r in results if isinstance(r,str)),results
        with tools.connect() as conn,conn.cursor() as cur:assert facts(cur)==before and fg.qty(fg.workspace(cur,f))==[11,0,11]
        return dict(status='PASS',one_reorder_one_stale_at_global_lock=True,stock_hpp_journals_unchanged=True)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);w=read(cur,f);before=facts(cur);subject=str(uuid.uuid4());role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) values(%s,%s,'Book revoked operator','ADMIN',%s,true)",(uuid.uuid4(),subject,role))
            for key in ('warehouse.movement.view','warehouse.stock.adjust'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s) on conflict do nothing',(role,key))
            conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('FGBOOK|GLOBAL',0))")
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:command(cur,'MOVE',move_payload(w,f['sale'],f['first']),subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                        assert blocked,'EXPECTED_REAL_BOOK_WAIT';c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
                finally:holder.rollback()
                result=future.result(30)
        assert 'access' in result.lower(),result
        with tools.connect() as conn,conn.cursor() as cur:assert read(cur,f)['book_token']==w['book_token'] and facts(cur)==before
        return dict(status='PASS',revocation_after_real_global_lock_wait=True,rank_and_business_facts_unchanged=True)
    return [('P10_BOOK_RACE_ORDER',compete),('P10_BOOK_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p10-book-owner');ops=http.login('ADMIN','p10-book-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);before=facts(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
            for key in ('warehouse.movement.view','warehouse.stock.adjust'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
            conn.commit()
        w=ops.rpc('erp_cp7_get_fg_book_v1',dict(p_query=dict(q=f['sku'])));assert w['status']==200,w
        args=dict(p_action='MOVE',p_payload=move_payload(w['body'],f['sale'],f['first']),p_request=str(uuid.uuid4()))
        assert http.anon_rpc('erp_cp7_save_fg_book_v1',args)['status'] in(401,403)
        r=ops.rpc('erp_cp7_save_fg_book_v1',args);assert r['status']==200,r;assert ops.rpc('erp_cp7_save_fg_book_v1',args)['body']==r['body']
        with http.connect() as conn,conn.cursor() as cur:assert facts(cur)==before;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(ops.auth_user_id,));conn.commit()
        assert ops.rpc('erp_cp7_save_fg_book_v1',args)['status']==403
        w=owner.rpc('erp_cp7_get_fg_book_v1',dict(p_query=dict(q=f['sku'])));r=owner.rpc('erp_cp7_save_fg_book_v1',dict(p_action='RESET',p_payload=dict(book_token=w['body']['book_token']),p_request=str(uuid.uuid4())));assert r['status']==200,r
        return dict(status='PASS',real_auth_http_move_reset=True,exact_replay_and_current_access_before_cache=True,no_operational_money=True)
    return [('P10_BOOK_HTTP',flow)]
