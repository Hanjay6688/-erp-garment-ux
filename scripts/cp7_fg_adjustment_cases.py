"""P10 exact FG corrections using only accepted native stock/accounting writers."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import copy,json,threading,time,uuid
import psycopg
import cp7_fg_cases as fg
import cp7_procurement_cases as procurement
auth,b,base=fg.p02,fg.b,fg.base

def rpc(cur,name,args,subject=None):
    assert name in ('erp_cp7_get_fg_adjustments_v1','erp_cp7_save_fg_adjustment_v1')
    auth.actor(cur,subject);r=cur.execute('select public.'+name+'('+','.join(['%s']*len(args))+')',args).fetchone()[0];b.api.admin(cur);return r
def command(cur,action,payload,version=None,key=None,subject=None):return rpc(cur,'erp_cp7_save_fg_adjustment_v1',[action,json.dumps(payload,default=str),key or uuid.uuid4(),version],subject)
def read(cur,ident=None,subject=None,**q):return rpc(cur,'erp_cp7_get_fg_adjustments_v1',[json.dumps(dict(adjustment_id=ident,**q))],subject)
def payload(cur,f,qty='-2'):
    return dict(adjustment_number='P10-ADJ-'+uuid.uuid4().hex[:10],location_id=f['location'],physical_at=(fg.ax.r1.now(cur)-timedelta(minutes=2)).isoformat(),reason_code='COUNT_CORRECTION',reason='Fixed actual FG discrepancy',change_reason='P10 reviewed physical correction',notes='Exact lot and size',items=[dict(lot_id=f['lot'],product_id=f['product'],quality_grade='GRADE_A',qty_signed=qty,notes=None)])
def draft(cur,f,qty='-2'):
    p=payload(cur,f,qty);return command(cur,'SAVE',p),p
def action(cur,name,d,key=None,subject=None):return command(cur,name,dict(adjustment_id=d['adjustment_id'],change_reason='P10 reviewed correction'),d['row_version'],key,subject)
def accounts(cur):return cur.execute('select account_id,sum(debit-credit) from erp.journal_lines group by account_id having sum(debit-credit)<>0 order by account_id').fetchall()
def qty(cur,f):return fg.qty(fg.workspace(cur,f,show_zero=True))

def cases(cur,today):
    def lifecycle(delta):
        f=fg.fixture(cur,today);initial=accounts(cur);d,p=draft(cur,f,str(delta));assert qty(cur,f)==[10,0,10]
        detail=read(cur,d['adjustment_id'])['detail'];assert detail['managed'] and detail['editable'] and len(detail['items'])==1
        posted=action(cur,'POST',d);assert qty(cur,f)==[10+delta,0,10+delta]
        item=read(cur,d['adjustment_id'])['detail']['items'][0];assert Decimal(item['valuation']['unit_cost'])==10 and Decimal(item['valuation']['value'])==delta*10,item
        k=uuid.uuid4();reverted=action(cur,'REVERSE',posted,k);assert action(cur,'REVERSE',posted,k)==reverted
        assert qty(cur,f)==[10,0,10] and accounts(cur)==initial
        assert cur.execute("select count(*) from erp.fg_stock_movements m join erp.fg_adjustment_items i on i.id=m.source_id where i.adjustment_id=%s and m.source_type='FG_ADJUSTMENT_ITEM'",(d['adjustment_id'],)).fetchone()[0]==2
        return dict(status='PASS',signed_correction=delta,stock=10+delta,value=delta*10,inverse_stock=10,inverse_all_accounts=True,one_inverse_pair=True)
    def multi():
        f=fg.fixture(cur,today);g=fg.fixture(cur,today);p=payload(cur,f);p['items']+=payload(cur,g,'3')['items'];d=command(cur,'SAVE',p)
        detail=read(cur,d['adjustment_id'])['detail'];assert len(detail['items'])==2 and detail['line_count']=='2' and detail['editable']
        p['id']=d['adjustment_id'];p['items'][0]['qty_signed']='-1';edited=command(cur,'SAVE',p,d['row_version'])
        before=b.boundary.snapshot(cur);auth.refused(cur,lambda:action(cur,'POST',d),'STALE_VERSION');assert b.boundary.snapshot(cur)==before
        posted=action(cur,'POST',edited);assert qty(cur,f)==[9,0,9] and qty(cur,g)==[13,0,13];action(cur,'REVERSE',posted)
        assert qty(cur,f)==qty(cur,g)==[10,0,10]
        return dict(status='PASS',two_complete_lot_product_lines=True,edit_preserves_all_lines=True,stale_version_atomic=True,stock_after=[9,13],inverse=[10,10])
    def replay():
        f=fg.fixture(cur,today);p=payload(cur,f);key=uuid.uuid4();d=command(cur,'SAVE',p,key=key);assert command(cur,'SAVE',p,key=key)==d
        changed=copy.deepcopy(p);changed['items'][0]['qty_signed']='-3';auth.refused(cur,lambda:command(cur,'SAVE',changed,key=key),'CP7_FG_ADJUST_REQUEST_CHANGED')
        k=uuid.uuid4();deleted=action(cur,'DELETE',d,k);assert action(cur,'DELETE',d,k)==deleted and deleted['row_version'] is None and qty(cur,f)==[10,0,10]
        assert not cur.execute('select 1 from erp.fg_adjustments where id=%s',(d['adjustment_id'],)).fetchone()
        return dict(status='PASS',same_uuid_exact_replay=True,changed_intent_refused=True,delete_replay=True,stock_unchanged=True)
    def forged():
        f=fg.fixture(cur,today);p=payload(cur,f);before=b.boundary.snapshot(cur)
        for key,val in [('unit_hpp_snapshot','0'),('qty_signed',-2),('qty_signed','-2.1'),('qty_signed','0')]:
            bad=copy.deepcopy(p);bad['items'][0][key]=val;auth.refused(cur,lambda:command(cur,'SAVE',bad),'CP7_FG_ADJUST_EXACT_LINE')
        bad=copy.deepcopy(p);bad['items'].append(bad['items'][0]);auth.refused(cur,lambda:command(cur,'SAVE',bad),'CP7_FG_ADJUST_DUPLICATE')
        bad=copy.deepcopy(p);bad['items'][0]['product_id']=str(uuid.uuid4());auth.refused(cur,lambda:command(cur,'SAVE',bad),'CP7_FG_ADJUST_LINEAGE')
        bad=copy.deepcopy(p);bad['physical_at']=(fg.ax.r1.now(cur)+timedelta(days=1)).isoformat();auth.refused(cur,lambda:command(cur,'SAVE',bad),'CP7_FG_ADJUST_TIME_LOCATION')
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',no_client_hpp=True,exact_integer_duplicate_lineage_future_time_atomic=True)
    def external():
        f=fg.fixture(cur,today);d,p=draft(cur,f)
        # Ordinary accepted native edit outside this companion binding.
        p['id']=d['adjustment_id'];p['items'][0]['qty_signed']='-3'
        b.chain.production.rpc(cur,'erp.save_fg_adjustment_draft_v2',p,uuid.uuid4(),int(d['row_version']))
        d['row_version']=str(cur.execute('select row_version from erp.fg_adjustments where id=%s',(d['adjustment_id'],)).fetchone()[0])
        before=b.boundary.snapshot(cur);auth.refused(cur,lambda:action(cur,'POST',d),'CP7_FG_ADJUST_DRAFT_CHANGED_REVIEW_AGAIN');assert b.boundary.snapshot(cur)==before
        assert not read(cur,d['adjustment_id'])['detail']['editable']
        native=cur.execute("select adjustment_id::text from erp.fg_adjustment_items where id in(select source_id from erp.fg_stock_movements where lot_id=%s and source_type='FG_ADJUSTMENT_ITEM')",(f['lot'],)).fetchone()
        if native:auth.refused(cur,lambda:command(cur,'REVERSE',dict(adjustment_id=native[0],change_reason='not owned by bridge'),'1'),'CP7_FG_ADJUST_SOURCE_WORKFLOW_REQUIRED')
        return dict(status='PASS',externally_changed_native_draft_not_posted=True,foreign_workflow_not_adopted=True)
    def unknown():
        c=fg.cut.fixture(cur,today);r=fg.workspace(cur,dict(sku=b.one(cur,'select sku from erp.products where id=%s',c['product'])))['page']['rows'][0]
        f=dict(product=r['product_id'],lot=r['lot_id'],location=r['location_id'],sku=r['product_sku']);d,p=draft(cur,f);posted=action(cur,'POST',d)
        item=read(cur,d['adjustment_id'])['detail']['items'][0];assert item['valuation']['state']=='UNKNOWN' and item['valuation']['value'] is None and qty(cur,f)==[13,0,13]
        action(cur,'REVERSE',posted);assert qty(cur,f)==[15,0,15]
        return dict(status='PASS',deferred_laundry_unknown_not_zero=True,stock_after=13,inverse=15)
    def access():
        f=fg.fixture(cur,today);d,p=draft(cur,f);subject,role=procurement.custom(cur,('warehouse.fg.view','warehouse.stock.adjust'))
        w=read(cur,d['adjustment_id'],subject=subject);assert not w['can_adjust'] and 'valuation' not in json.dumps(w)
        auth.refused(cur,lambda:action(cur,'POST',d,subject=subject),'CP7_FG_ADJUST_DENIED')
        for who in ('anon','authenticated','service_role','cp7_capture'):
            assert not cur.execute("select has_schema_privilege(%s,'cp7_fg','USAGE')",(who,)).fetchone()[0]
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_fg_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        return dict(status='PASS',native_owner_admin_boundary_retained=True,money_redacted=True,command_role_no_business_select_or_dml=True)
    return [('P10_ADJUST_'+k,fn) for k,fn in [('NEGATIVE_VALUE',lambda:lifecycle(-2)),('POSITIVE_VALUE',lambda:lifecycle(2)),('MULTI_EDIT_VERSION',multi),('REPLAY_DELETE',replay),('FORGED_ATOMIC',forged),('EXTERNAL_DRAFT',external),('DEFERRED_UNKNOWN',unknown),('AUTH_PRIVATE',access)]]

def races(tools,today):
    def compete():
        with tools.connect() as conn,conn.cursor() as cur:f=fg.fixture(cur,today);one,_=draft(cur,f,'-7');two,_=draft(cur,f,'-7');conn.commit()
        barrier=threading.Barrier(2)
        def send(d):
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait()
                try:r=action(cur,'POST',d);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:jobs=[pool.submit(send,d) for d in (one,two)];results=[x.result(30) for x in jobs]
        assert sum(isinstance(r,dict) for r in results)==1,results
        with tools.connect() as conn,conn.cursor() as cur:assert qty(cur,f)==[3,0,3]
        return dict(status='PASS',competing_native_corrections_one_post=True,physical_available=3,loser_atomic=True)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:f=fg.fixture(cur,today);d,_=draft(cur,f);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:action(cur,'POST',d);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                        assert blocked,'EXPECTED_REAL_FG_WAIT';c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(base.OPERATOR_AUTH,))
                finally:holder.rollback()
                result=future.result(30)
        assert 'ACCESS' in result or 'OWNER or ADMIN' in result,result
        with tools.connect() as conn,conn.cursor() as cur:
            actual=cur.execute('select sum(qty_signed) from erp.fg_stock_movements where lot_id=%s',(f['lot'],)).fetchone()[0];assert actual==10
            assert cur.execute('select status from erp.fg_adjustments where id=%s',(d['adjustment_id'],)).fetchone()[0]=='DRAFT'
        return dict(status='PASS',revocation_after_real_native_lock_wait_atomic=True,stock=10,draft_retained=True)
    return [('P10_ADJUST_RACE_STOCK',compete),('P10_ADJUST_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p10-adjust-owner');ops=http.login('ADMIN','p10-adjust-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=fg.fixture(cur,today);p=payload(cur,f);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'",(role,));conn.commit()
        args=dict(p_action='SAVE',p_payload=p,p_request=str(uuid.uuid4()),p_expected=None);r=ops.rpc('erp_cp7_save_fg_adjustment_v1',args);assert r['status']==200,r;d=r['body']
        w=ops.rpc('erp_cp7_get_fg_adjustments_v1',dict(p_query=dict(adjustment_id=d['adjustment_id'])));assert w['status']==200 and 'valuation' not in json.dumps(w['body']),w
        args=dict(p_action='POST',p_payload=dict(adjustment_id=d['adjustment_id'],change_reason='HTTP exact correction'),p_request=str(uuid.uuid4()),p_expected=d['row_version'])
        assert http.anon_rpc('erp_cp7_save_fg_adjustment_v1',args)['status'] in(401,403)
        posted=ops.rpc('erp_cp7_save_fg_adjustment_v1',args);assert posted['status']==200,posted;assert ops.rpc('erp_cp7_save_fg_adjustment_v1',args)['body']==posted['body']
        with http.connect() as conn,conn.cursor() as cur:assert qty(cur,f)==[8,0,8];cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(ops.auth_user_id,));conn.commit()
        assert ops.rpc('erp_cp7_save_fg_adjustment_v1',args)['status']==403
        p=posted['body'];args=dict(p_action='REVERSE',p_payload=dict(adjustment_id=p['adjustment_id'],change_reason='HTTP correction withdrawn'),p_request=str(uuid.uuid4()),p_expected=p['row_version'])
        r=owner.rpc('erp_cp7_save_fg_adjustment_v1',args);assert r['status']==200,r
        with http.connect() as conn,conn.cursor() as cur:assert qty(cur,f)==[10,0,10]
        return dict(status='PASS',real_auth_write_and_inverse=True,ops_no_money=True,one_effect_on_retry=True,access_before_cache=True,stock=[10,8,10])
    return [('P10_ADJUST_HTTP',flow)]
