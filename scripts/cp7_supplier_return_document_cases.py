"""Complete source-return documents: native money, stock and portable credit."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
from datetime import timedelta
import copy,json,threading,time,uuid
import psycopg
import cp7_supplier_return_cases as source
receipt,auth,b,material,credit=source.receipt,source.auth,source.b,source.material,source.credit


def fixture(cur,today,mixed=False):
    f=source.fixture(cur,today,not mixed,price='10')
    g=source.fixture(cur,today,True,accessory=mixed,price='20')
    transfer,_=material.draft(cur,g,'10',dest=f['location'])
    material.post(cur,transfer)
    return f,g


def payload(f,g,q1='2',q2='3'):
    p=source.payload(f,q1);p['items']+=source.payload(g,q2)['items'];return p


def save(cur,p,version=None,key=None,subject=None):return source.command(cur,'SAVE_DOCUMENT',p,version,key,subject)
def intent(f,g,d):return dict(purchase_id=f['receipt']['purchase_id'],return_id=d['return_id'],change_reason='All source receipts and outgoing quantities reviewed',reviewed_purchase_ids=sorted([f['receipt']['purchase_id'],g['receipt']['purchase_id']]))
def act(cur,action,f,g,d,key=None,subject=None):return source.command(cur,action+'_DOCUMENT',intent(f,g,d),d['row_version'],key,subject)
def options(cur,f,q='',offset=0,limit=25,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_supplier_return_sources_v1(%s,%s,%s,%s)',(f['receipt']['purchase_id'],q,offset,limit)).fetchone()[0];b.api.admin(cur);return r


def cases(cur,today):
    def lifecycle(mixed):
        f,g=fixture(cur,today,mixed);p=payload(f,g);before=b.boundary.snapshot(cur);d=save(cur,p)
        assert source.amounts(cur,f)==((0,100,10,10) if mixed else (100,0,10,10)) and source.amounts(cur,g)==(200,0,10,20)
        doc=source.read(cur,f)['page']['rows'][0];assert doc['line_count']=='2' and not doc['single_receipt']
        p.update(id=d['return_id'],reason='Updated reason, every source remains visible');d=save(cur,p,d['row_version'])
        d=act(cur,'POST',f,g,d)
        assert source.amounts(cur,f)==((0,80,8,10) if mixed else (80,0,8,10)) and source.amounts(cur,g)==(140,0,7,20)
        for x in (f,g):
            doc=source.read(cur,x)['page']['rows'][0]
            assert doc['status']=='POSTED' and len(doc['lines'])==2 and not doc['single_receipt']
            assert D(doc['finance']['ap_relief_amount'])==(60 if mixed else 80) and D(doc['finance']['grni_relief_amount'])==(20 if mixed else 0)
        if not mixed:
            cf=dict(ret=d['return_id'],purchases=[f['receipt']['purchase_id'],g['receipt']['purchase_id']])
            state=credit.state(cur,dict(material=f['material'],purchases=cf['purchases']))
            credit.call(cur,credit.payload(cur,cf,[(g['receipt']['purchase_id'],'20.00')]))
            moved=credit.state(cur,dict(material=f['material'],purchases=cf['purchases']))
            assert moved['ap']==['100.00','120.00'] and moved['ledger']==state['ledger'] and moved['values']==state['values']
            auth.refused(cur,lambda:act(cur,'REVERSE',f,g,d),'BF_CREDIT_RETURN_IN_USE')
            credit.call(cur,credit.payload(cur,cf,[]))
            assert credit.state(cur,dict(material=f['material'],purchases=cf['purchases']))==state
        rev=act(cur,'REVERSE',f,g,d)
        assert rev['status']=='REVERSED' and source.amounts(cur,f)==((0,100,10,10) if mixed else (100,0,10,10)) and source.amounts(cur,g)==(200,0,10,20)
        return dict(status='PASS',mixed_fabric_accessory=mixed,all_source_lines_read_from_both_receipts=True,ap_relief=60 if mixed else 80,grni_relief=20 if mixed else 0,stock_after=[8,7],source_inverse_restores=[10,10],portable_credit_to_other_and_back=not mixed,credit_does_not_cut_AP_twice=True)
    def atomic():
        f,g=fixture(cur,today);p=payload(f,g)
        for mutation in ('price','roll','quantity','supplier'):
            wrong=copy.deepcopy(p)
            if mutation=='price':wrong['items'][1]['supplier_credit_unit_price']='0'
            elif mutation=='roll':wrong['items'][1]['roll_id']=f['roll']
            elif mutation=='quantity':wrong['items'][1]['qty']=3
            else:wrong['supplier_id']=str(uuid.uuid4())
            before=b.boundary.snapshot(cur);auth.refused(cur,lambda:save(cur,wrong),'CP7_RETURN_');assert b.boundary.snapshot(cur)==before
        d=save(cur,p);before=b.boundary.snapshot(cur)
        for reviewed in ([f['receipt']['purchase_id']],[g['receipt']['purchase_id']],[f['receipt']['purchase_id']]*2):
            auth.refused(cur,lambda:source.command(cur,'POST_DOCUMENT',dict(intent(f,g,d),reviewed_purchase_ids=reviewed),d['row_version']),'CP7_RETURN_COMPLETE_DOCUMENT_REQUIRED')
        assert b.boundary.snapshot(cur)==before
        p.update(id=d['return_id']);p['items'][1]['qty']='11'
        auth.refused(cur,lambda:save(cur,p,d['row_version']),'Supplier return exceeds quantity from source purchase item')
        assert b.boundary.snapshot(cur)==before
        # The second source loses warehouse stock through a lawful transfer
        # after the draft was reviewed. Native POST must roll back both legs.
        transfer,_=material.draft(cur,g,'8',source=f['location'],dest=g['location'],at=source.aa.at(f['day']+timedelta(days=1),11).isoformat())
        material.post(cur,transfer);before=b.boundary.snapshot(cur)
        try:
            cur.execute('savepoint return_over');act(cur,'POST',f,g,d)
        except psycopg.Error as e:
            message=e.diag.message_primary;cur.execute('rollback to savepoint return_over');b.api.admin(cur)
        else:raise AssertionError('OVER_CAPACITY_RETURN_ACCEPTED')
        cur.execute('release savepoint return_over')
        assert b.boundary.snapshot(cur)==before and source.amounts(cur,f)==(100,0,10,10) and source.amounts(cur,g)==(200,0,10,20)
        assert material.balances(cur,g)[f['location']]==2
        return dict(status='PASS',draft_over_source_quantity_refused=True,price_foreign_roll_inexact_qty_wrong_supplier_refused=True,omitted_duplicate_and_wrong_anchor_review_refused=True,second_source_overcapacity_atomic=True,native_refusal=message)
    def replay():
        f,g=fixture(cur,today);p=payload(f,g);key=uuid.uuid4();d=save(cur,p,key=key)
        changed=copy.deepcopy(p);changed.update(id=d['return_id'],reason='Current complete draft');edit=save(cur,changed,d['row_version'])
        assert save(cur,p,key=key)==d
        auth.refused(cur,lambda:save(cur,dict(p,reason='Different intent'),key=key),'CP7_RETURN_REQUEST_PAYLOAD_CHANGED')
        auth.refused(cur,lambda:act(cur,'POST',f,g,d),'STALE_VERSION')
        request=uuid.uuid4();posted=act(cur,'POST',f,g,edit,request);rev=act(cur,'REVERSE',f,g,posted)
        assert act(cur,'POST',f,g,edit,request)==posted and source.read(cur,f)['page']['rows'][0]['status']=='REVERSED'
        assert source.amounts(cur,f)==(100,0,10,10) and source.amounts(cur,g)==(200,0,10,20)
        return dict(status='PASS',exact_cached_outcomes_after_edit_and_inverse=True,changed_payload_and_stale_header_refused=True,no_double_return=True)
    def access():
        f,g=fixture(cur,today);subject,role=receipt.custom(cur,source.PERMS)
        p=payload(f,g);d=save(cur,p,subject=subject);key=uuid.uuid4();posted=act(cur,'POST',f,g,d,key,subject)
        for f0 in (f,g):
            w=source.read(cur,f0,subject=subject)
            assert not w['financial_captured'] and all(k not in json.dumps(w) for k in ('"finance"','credit_unit_price','ap_relief_amount','grni_relief_amount'))
        search=options(cur,f,'P09-',subject=subject)
        assert all(k not in json.dumps(search) for k in ('price','amount','finance'))
        auth.refused(cur,lambda:act(cur,'REVERSE',f,g,posted,subject=subject),'CP7_RETURN_ACTION_DENIED')
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.reverse'",(role,))
        auth.refused(cur,lambda:act(cur,'POST',f,g,d,key,subject),'CP7_RETURN_ACTION_DENIED')
        assert not cur.execute("select has_table_privilege('cp7_return_write','erp.material_supplier_returns','SELECT,INSERT,UPDATE,DELETE')").fetchone()[0]
        assert not cur.execute("select has_function_privilege('authenticated','cp7_supplier_return.document_command(text,jsonb,uuid,text)','EXECUTE')").fetchone()[0]
        assert cur.execute('select count(*) from cp7_supplier_return.execution_context').fetchone()[0]==0
        return dict(status='PASS',operational_actor_posts_without_money=True,source_picker_has_no_money=True,current_permission_before_replay=True,no_private_context_or_ERP_DML=True)
    def pages():
        f,g=fixture(cur,today);pages=[options(cur,f,'P09-',off,1)['page'] for off in (0,1,2)]
        assert [len(p['rows']) for p in pages]==[1,1,0] and all(p['total']=='2' for p in pages)
        assert {p['rows'][0]['id'] for p in pages[:2]}=={f['receipt']['purchase_id'],g['receipt']['purchase_id']}
        assert pages[0]['next_offset']==1 and pages[1]['next_offset'] is None and options(cur,f,'does-not-exist')['page']['total']=='0'
        return dict(status='PASS',same_supplier_complete_paged_headers=True,no_silent_first_page_or_false_zero=True)
    return [('P09_COMBINED_RETURN_FABRIC_CREDIT_INVERSE',lambda:lifecycle(False)),('P09_COMBINED_RETURN_MIXED_AP_GRNI',lambda:lifecycle(True)),('P09_COMBINED_RETURN_ATOMIC',atomic),('P09_COMBINED_RETURN_REPLAY',replay),('P09_COMBINED_RETURN_ACCESS',access),('P09_COMBINED_RETURN_SOURCES',pages)]


def races(tools,today):
    def compete(same):
        with tools.connect() as conn,conn.cursor() as cur:
            f,g=fixture(cur,today);p=payload(f,g,'7','7');first=save(cur,p);p['return_number']+='-TWO';second=first if same else save(cur,p);conn.commit()
        gate=threading.Barrier(2);key=uuid.uuid4()
        def send(d):
            with tools.connect() as conn,conn.cursor() as cur:
                gate.wait()
                try:r=act(cur,'POST',f,g,d,key if same else uuid.uuid4());conn.commit();return ('PASS',r)
                except psycopg.Error as e:conn.rollback();return ('REFUSED',e.diag.message_primary)
        with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(send,[first,second]))
        if same:assert rows[0]==rows[1] and rows[0][0]=='PASS',rows
        else:assert sorted(r[0] for r in rows)==['PASS','REFUSED'],rows
        with tools.connect() as conn,conn.cursor() as cur:
            assert source.amounts(cur,f)==(30,0,3,10) and source.amounts(cur,g)==(60,0,3,20)
        return dict(status='PASS',same_request=same,one_complete_post_for_both_sources=True,stock=[3,3],AP=[30,60])
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f,g=fixture(cur,today);d=save(cur,payload(f,g));subject,role=receipt.custom(cur,source.PERMS);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.material_supplier_returns where id=%s for update',(d['return_id'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:act(cur,'POST',f,g,d,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                task=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                        assert blocked,'EXPECTED_RETURN_ROW_WAIT';c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.reverse'",(role,))
                finally:holder.rollback()
                result=task.result(30)
        assert 'ACCESS' in result or 'DENIED' in result or 'Internal ERP' in result,result
        with tools.connect() as conn,conn.cursor() as cur:
            assert source.amounts(cur,f)==(100,0,10,10) and source.amounts(cur,g)==(200,0,10,20)
        return dict(status='PASS',actual_row_wait_revocation_rolls_back_both_sources=True)
    return [('P09_COMBINED_RETURN_RACE_SAME',lambda:compete(True)),('P09_COMBINED_RETURN_RACE_CAPACITY',lambda:compete(False)),('P09_COMBINED_RETURN_RACE_REVOKE',revoke)]


def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','combined-return-owner')
        with http.connect() as conn,conn.cursor() as cur:f,g=fixture(cur,today);p=payload(f,g);conn.commit()
        args=dict(p_action='SAVE_DOCUMENT',p_payload=p,p_request=str(uuid.uuid4()),p_expected=None)
        assert http.anon_rpc('erp_cp7_save_supplier_return_v1',args)['status'] in(401,403)
        saved=owner.rpc('erp_cp7_save_supplier_return_v1',args);assert saved['status']==200,saved;d=saved['body']
        assert owner.rpc('erp_cp7_save_supplier_return_v1',args)['body']==d
        args=dict(p_action='POST_DOCUMENT',p_payload=intent(f,g,d),p_request=str(uuid.uuid4()),p_expected=d['row_version'])
        posted=owner.rpc('erp_cp7_save_supplier_return_v1',args);assert posted['status']==200,posted
        assert owner.rpc('erp_cp7_save_supplier_return_v1',args)['body']==posted['body']
        with http.connect() as conn,conn.cursor() as cur:
            assert source.amounts(cur,f)==(80,0,8,10) and source.amounts(cur,g)==(140,0,7,20)
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_save_supplier_return_v1',args)['status']==403
        return dict(status='PASS',real_Auth_HTTP_complete_return=True,current_revocation_before_replay=True,anonymous_denied=True,stock=[8,7],AP=[80,140])
    return [('P09_COMBINED_RETURN_HTTP',flow)]
