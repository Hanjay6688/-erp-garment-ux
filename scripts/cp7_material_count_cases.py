"""Physical-count bridge proof; accepted native stock/accounting remain the oracle."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import copy,json,threading,time,uuid
import psycopg
import cp7_material_cases as material
import cp7_material_unrolled_cases as raw
import cp7_invoice_cases as invoice
receipt,auth,b,aa=material.receipt,material.auth,material.b,material.aa

def rpc(cur,name,args,subject=None):
    assert name in ('erp_cp7_preview_material_count_v1','erp_cp7_get_material_counts_v1','erp_cp7_save_material_count_v1')
    auth.actor(cur,subject);r=cur.execute('select public.'+name+'('+','.join(['%s']*len(args))+')',args).fetchone()[0];b.api.admin(cur);return r

def command(cur,action,payload,version=None,key=None,subject=None):
    return rpc(cur,'erp_cp7_save_material_count_v1',[action,json.dumps(payload,default=str),key or uuid.uuid4(),version],subject)
def scope(f,qty='8',at=None):
    return dict(location_id=f['location'],physical_at=at or aa.at(f['day']+timedelta(days=2),10).isoformat(),items=[dict(material_id=f['material'],roll_id=f['roll'],physical_qty=qty)])
def preview(cur,p,subject=None):return rpc(cur,'erp_cp7_preview_material_count_v1',[json.dumps(p)],subject)
def payload(cur,f,qty='8',cost=None,at=None):
    p=scope(f,qty,at);r=preview(cur,p);p['items'][0]['basis_token']=r['items'][0]['basis_token']
    if cost is not None:p['items'][0]['input_unit_cost']=cost
    return dict(**p,adjustment_number=f['tag']+'-COUNT-'+uuid.uuid4().hex[:5],reason_code='COUNT_CORRECTION',change_reason='P09 physical count after second check',notes='Actual count proof')
def draft(cur,f,qty='8',cost=None,at=None):
    p=payload(cur,f,qty,cost,at);return command(cur,'SAVE',p),p

def action(cur,name,d,key=None,subject=None):return command(cur,name,dict(adjustment_id=d['adjustment_id'],change_reason='P09 checked physical quantity'),d['row_version'],key,subject)
def read(cur,ident=None,subject=None,**query):return rpc(cur,'erp_cp7_get_material_counts_v1',[json.dumps(dict(adjustment_id=ident,**query))],subject)
def qty(cur,f):return material.balances(cur,f)[f['location']]
def ledger(cur):return cur.execute("select account_id,sum(debit-credit) from erp.journal_lines group by account_id having sum(debit-credit)<>0 order by account_id").fetchall()

def multi_fixture(cur,today):
    f=raw.fixture(cur,today);other=raw.fixture(cur,today)
    transfer,_=material.draft(cur,other,'10',dest=f['location'],at=aa.at(f['day']+timedelta(days=1),10).isoformat());material.post(cur,transfer)
    other['location']=f['location']
    return f,other

def reviewed_items(cur,p):
    observed=preview(cur,{k:p[k] for k in ('location_id','physical_at','items')})['items']
    for item in p['items']:
        match=next(r for r in observed if (r['material_id'],r['roll_id'])==(item['material_id'],item['roll_id']))
        item['basis_token']=match['basis_token']
    return p

def cases(cur,today):
    def lifecycle(kind):
        f=material.fixture(cur,today) if kind=='FABRIC' else raw.fixture(cur,today)
        f['item']=str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(f['receipt']['purchase_id'],)).fetchone()[0]);initial=ledger(cur);d,p=draft(cur,f);assert qty(cur,f)==10
        r=read(cur,d['adjustment_id']);assert r['detail']['managed_count'] and Decimal(r['detail']['items'][0]['physical_qty'])==8 and Decimal(r['detail']['items'][0]['qty_signed'])==-2
        aa.zone(cur,'America/Los_Angeles');posted=action(cur,'POST',d);assert qty(cur,f)==8
        inv=invoice.finalize(cur,f,'10','12.5');assert invoice.amounts(cur,f)==(125,0,8,Decimal('12.5'))
        item=read(cur,d['adjustment_id'])['detail']['items'][0];assert Decimal(item['valuation']['restated_value'])==-25
        invoice.reverse(cur,f,inv['invoice_id']);assert invoice.amounts(cur,f)==(0,100,8,10)
        reverted=action(cur,'REVERSE',posted);assert reverted['status']=='REVERSED' and qty(cur,f)==10 and ledger(cur)==initial
        return dict(status='PASS',kind=kind,physical_count=8,server_delta=-2,session_timezone_preserves_source_identity=True,late_invoice_inventory=100,late_invoice_adjustment=-25,invoice_and_count_inverse_restore_all_accounts=True)
    def positive():
        f=raw.fixture(cur,today);initial=ledger(cur);d,p=draft(cur,f,'12','10');posted=action(cur,'POST',d)
        assert qty(cur,f)==12 and Decimal(read(cur,d['adjustment_id'])['detail']['items'][0]['valuation']['restated_value'])==20
        action(cur,'REVERSE',posted);assert qty(cur,f)==10 and ledger(cur)==initial
        return dict(status='PASS',positive_count=12,server_delta=2,input_cost=10,quantity_value_inverse=True)
    def stale_basis():
        f=material.fixture(cur,today);d,p=draft(cur,f);t,_=material.draft(cur,f,'1',at=aa.at(f['day']+timedelta(days=1),10).isoformat());material.post(cur,t)
        before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:command(cur,'SAVE',p),'CP7_COUNT_STOCK_CHANGED_REVIEW_AGAIN')
        auth.refused(cur,lambda:action(cur,'POST',d),'CP7_COUNT_STOCK_CHANGED_REVIEW_AGAIN');assert b.boundary.snapshot(cur)==before
        changed=payload(cur,f,'8');changed['id']=d['adjustment_id'];edited=command(cur,'SAVE',changed,d['row_version']);posted=action(cur,'POST',edited)
        assert qty(cur,f)==8 and material.balances(cur,f)[f['destination']]==1
        return dict(status='PASS',stale_preview_and_draft_refused=True,fresh_review_delta=-1,source_qty=8,destination_qty=1)
    def forged():
        f=material.fixture(cur,today);p=payload(cur,f);before=b.boundary.snapshot(cur)
        for key,value in (('qty_signed','-1'),('system_qty','9')):
            bad=copy.deepcopy(p);bad['items'][0][key]=value;auth.refused(cur,lambda:command(cur,'SAVE',bad),'CP7_COUNT_EXACT_PHYSICAL_QTY')
        bad=copy.deepcopy(p);bad['items'][0]['physical_qty']=8;auth.refused(cur,lambda:command(cur,'SAVE',bad),'CP7_COUNT_EXACT_PHYSICAL_QTY')
        bad=copy.deepcopy(p);bad['items'].append(copy.deepcopy(bad['items'][0]));auth.refused(cur,lambda:command(cur,'SAVE',bad),'CP7_COUNT_DUPLICATE_LINE')
        bad=payload(cur,f,'10');auth.refused(cur,lambda:command(cur,'SAVE',bad),'CP7_COUNT_NO_DIFFERENCE')
        bad=payload(cur,f,'12');auth.refused(cur,lambda:command(cur,'SAVE',bad),'CP7_COUNT_POSITIVE_COST_REQUIRED')
        assert b.boundary.snapshot(cur)==before
        other=raw.fixture(cur,today);extra=dict(material_id=other['material'],roll_id=None,physical_qty='0')
        extra['basis_token']=preview(cur,dict(location_id=f['location'],physical_at=p['physical_at'],items=[extra]))['items'][0]['basis_token']
        multi=copy.deepcopy(p);multi['items'].append(extra);d=command(cur,'SAVE',multi);detail=read(cur,d['adjustment_id'])['detail']
        assert len(detail['items'])==1 and len(detail['edit']['items'])==2
        assert {r['material_id']:r['physical_qty'] for r in detail['edit']['items']}=={f['material']:'8',other['material']:'0'}
        return dict(status='PASS',no_client_delta_or_system_balance=True,exact_physical_quantity=True,duplicate_and_zero_and_missing_cost_atomic=True,complete_edit_preserves_zero_input=True)
    def changed_native():
        f=material.fixture(cur,today);d,p=draft(cur,f)
        cur.execute("select erp.save_material_adjustment_draft_v2(%s,%s,%s)",(json.dumps(dict(id=d['adjustment_id'],change_reason='P09 legacy draft modification',items=[dict(material_id=f['material'],roll_id=f['roll'],qty_signed='-1')])),uuid.uuid4(),int(d['row_version'])))
        d['row_version']=str(cur.execute('select row_version from erp.material_adjustments where id=%s',(d['adjustment_id'],)).fetchone()[0]);before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:action(cur,'POST',d),'CP7_COUNT_DRAFT_CHANGED_REVIEW_AGAIN');assert b.boundary.snapshot(cur)==before and qty(cur,f)==10
        assert read(cur,d['adjustment_id'])['detail']['edit'] is None
        return dict(status='PASS',native_external_edit_requires_new_physical_review=True)
    def replay_delete():
        f=material.fixture(cur,today);p=payload(cur,f);key=str(uuid.uuid4());d=command(cur,'SAVE',p,key=key);assert command(cur,'SAVE',p,key=key)==d
        before=b.boundary.snapshot(cur);bad=copy.deepcopy(p);bad['items'][0]['physical_qty']='7';auth.refused(cur,lambda:command(cur,'SAVE',bad,key=key),'CP7_COUNT_REQUEST_CHANGED');assert b.boundary.snapshot(cur)==before
        k=str(uuid.uuid4());deleted=action(cur,'DELETE',d,k);assert deleted['status']=='DELETED' and deleted['row_version'] is None and action(cur,'DELETE',d,k)==deleted
        assert qty(cur,f)==10 and not cur.execute('select 1 from erp.material_adjustments where id=%s',(d['adjustment_id'],)).fetchone()
        return dict(status='PASS',same_uuid_one_draft=True,changed_intent_refused=True,delete_replay_without_effect=True)
    def access():
        f=raw.fixture(cur,today);ops,role=receipt.custom(cur,material.PERMS);p=payload(cur,f,'12','10')
        auth.refused(cur,lambda:command(cur,'SAVE',p,subject=ops),'CP7_COUNT_COST_DENIED')
        positive,p=draft(cur,f,'12','10');assert read(cur,positive['adjustment_id'],subject=ops)['detail']['edit'] is None
        d,p=draft(cur,f);detail=read(cur,d['adjustment_id'],subject=ops)['detail'];assert detail['edit']==dict(physical_qty='8') and 'input_unit_cost' not in json.dumps(detail)
        posted=action(cur,'POST',d,subject=ops);assert qty(cur,f)==8
        assert 'valuation' not in json.dumps(read(cur,d['adjustment_id'],subject=ops))
        auth.refused(cur,lambda:action(cur,'REVERSE',posted,subject=ops),'CP7_MATERIAL_REVERSE_DENIED')
        view,role=receipt.custom(cur,('warehouse.material.view',));auth.refused(cur,lambda:action(cur,'POST',d,subject=view),'CP7_MATERIAL_ADJUST_DENIED')
        for principal in ('authenticated','anon','service_role','cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,'cp7_material.count_lines(uuid,timestamptz,jsonb,boolean,uuid)','EXECUTE')",(principal,)).fetchone()[0]
        return dict(status='PASS',ops_negative_count_without_money=True,cost_input_and_inverse_authorized=True,private_helpers_unreachable=True)
    def scope_guard():
        f=raw.fixture(cur,today);zone=receipt.bc.svc(cur,'REGISTER_ZONE',dict(zone_kind='SERVICE_POST',location_code=f['tag']+'-ZONE',location_name='Count service',reason='P09 count boundary'))['location_id'];b.api.admin(cur)
        p=scope(f);p['location_id']=str(zone);auth.refused(cur,lambda:preview(cur,p),'CP7_COUNT_ORDINARY_WAREHOUSE_REQUIRED')
        p=scope(f);p['items'][0]['roll_id']=str(uuid.uuid4());auth.refused(cur,lambda:preview(cur,p),'CP7_COUNT_MATERIAL_LINEAGE')
        p=scope(f,at=aa.at(today+timedelta(days=2),10).isoformat());auth.refused(cur,lambda:preview(cur,p),'CP7_COUNT_TIME_LOCATION')
        return dict(status='PASS',service_zone_and_false_roll_and_future_date_refused=True)
    def prefix():
        f=material.fixture(cur,today);t,_=material.draft(cur,f,'4');material.post(cur,t)
        at=aa.at(f['day'],11).isoformat();d,p=draft(cur,f,'9',at=at);posted=action(cur,'POST',d)
        assert qty(cur,f)==5 and material.balances(cur,f)[f['destination']]==4
        action(cur,'REVERSE',posted);assert qty(cur,f)==6
        d,p=draft(cur,f,'2',at=at);before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:action(cur,'POST',d),'negative');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',historical_count_uses_dated_prefix=10,later_transfer_preserved=True,negative_history_atomic=True)
    def pages():
        f=raw.fixture(cur,today)
        for _ in range(3):draft(cur,f)
        seen=[]
        for offset in range(3):
            r=read(cur,q=f['tag'],offset=offset,limit=1);assert r['page']['total']=='3';seen.append(r['page']['rows'][0]['id'])
        assert len(set(seen))==3
        return dict(status='PASS',complete_native_document_pages=3)
    def multi_cycle():
        f,g=multi_fixture(cur,today);zero=raw.fixture(cur,today);before=ledger(cur)
        p=payload(cur,f);p['items'] += [dict(material_id=g['material'],roll_id=None,physical_qty='12',input_unit_cost='10',notes='positive count'),dict(material_id=zero['material'],roll_id=None,physical_qty='0',notes='checked empty')]
        d=command(cur,'SAVE',reviewed_items(cur,p));detail=read(cur,d['adjustment_id'])['detail'];assert len(detail['items'])==2 and len(detail['edit']['items'])==3
        original_time=detail['physical_at'];p['id']=d['adjustment_id'];p['items'][1]['physical_qty']='13'
        d=command(cur,'SAVE',reviewed_items(cur,p),d['row_version']);detail=read(cur,d['adjustment_id'])['detail']
        assert detail['physical_at']==original_time and [r['physical_qty'] for r in detail['edit']['items']]==['8','13','0']
        assert detail['edit']['items'][1]['input_unit_cost']=='10' and detail['edit']['items'][2]['notes']=='checked empty'
        posted=action(cur,'POST',d);assert qty(cur,f)==8 and qty(cur,g)==13
        assert cur.execute('select jsonb_array_length(input->\'items\') from cp7_material.count_documents where adjustment_id=%s',(d['adjustment_id'],)).fetchone()[0]==3
        assert cur.execute('select count(*) from erp.material_adjustment_items where adjustment_id=%s',(d['adjustment_id'],)).fetchone()[0]==2
        action(cur,'REVERSE',posted);assert qty(cur,f)==10 and qty(cur,g)==10 and ledger(cur)==before
        return dict(status='PASS',negative_positive_zero_inputs=[8,13,0],complete_edit_preserves_price_notes_and_time=True,three_physical_inputs_two_native_movements=True,inverse_restores_both_materials_and_all_accounts=True)
    def multi_access():
        f,g=multi_fixture(cur,today);ops,_=receipt.custom(cur,material.PERMS);p=payload(cur,f)
        p['items'].append(dict(material_id=g['material'],roll_id=None,physical_qty='10'));d=command(cur,'SAVE',reviewed_items(cur,p),subject=ops)
        detail=read(cur,d['adjustment_id'],subject=ops)['detail'];assert len(detail['edit']['items'])==2 and 'input_unit_cost' not in json.dumps(detail) and 'valuation' not in json.dumps(detail)
        p=payload(cur,f);p['items'].append(dict(material_id=g['material'],roll_id=None,physical_qty='12',input_unit_cost='10'));d=command(cur,'SAVE',reviewed_items(cur,p))
        assert read(cur,d['adjustment_id'],subject=ops)['detail']['edit'] is None
        return dict(status='PASS',operational_complete_inputs_without_money=True,priced_multi_input_edit_requires_value_authority=True)
    return [('P09_COUNT_FABRIC',lambda:lifecycle('FABRIC')),('P09_COUNT_ACCESSORY',lambda:lifecycle('ACCESSORY')),('P09_COUNT_POSITIVE',positive),
      ('P09_COUNT_STALE_BASIS',stale_basis),('P09_COUNT_FORGED_ATOMIC',forged),('P09_COUNT_NATIVE_EDIT',changed_native),('P09_COUNT_REPLAY_DELETE',replay_delete),
      ('P09_COUNT_ACCESS',access),('P09_COUNT_SCOPE',scope_guard),('P09_COUNT_HISTORICAL',prefix),('P09_COUNT_COMPLETE_PAGES',pages),
      ('P09_COUNT_MULTI_EDIT_INVERSE',multi_cycle),('P09_COUNT_MULTI_ACCESS',multi_access)]

def races(tools,today):
    def compete():
        with tools.connect() as conn,conn.cursor() as cur:f=raw.fixture(cur,today);one,_=draft(cur,f,'7');two,_=draft(cur,f,'5');conn.commit()
        barrier=threading.Barrier(2)
        def send(d):
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait()
                try:r=action(cur,'POST',d);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(send,d) for d in (one,two)];results=[x.result(30) for x in jobs]
        assert sum(isinstance(r,dict) for r in results)==1 and any('CP7_COUNT_STOCK_CHANGED' in r for r in results if isinstance(r,str)),results
        with tools.connect() as conn,conn.cursor() as cur:assert qty(cur,f) in (5,7)
        return dict(status='PASS',competing_physical_counts_one_commit=True,no_double_delta=True)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:f=raw.fixture(cur,today);d,_=draft(cur,f);subject,role=receipt.custom(cur,material.PERMS);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.materials where id=%s for update',(f['material'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:action(cur,'POST',d,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                        assert blocked,'EXPECTED_REAL_MATERIAL_WAIT';c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.stock.adjust'",(role,))
                finally:holder.rollback()
                result=future.result(30)
        assert 'ACCESS_CHANGED' in result or 'Internal ERP access required' in result,result
        with tools.connect() as conn,conn.cursor() as cur:assert qty(cur,f)==10
        return dict(status='PASS',revocation_at_real_material_lock_rolls_back_all=True)
    return [('P09_COUNT_RACE_PREFIX',compete),('P09_COUNT_RACE_REVOKE',revoke)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p09-count-owner');ops=http.login('ADMIN','p09-count-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=raw.fixture(cur,today);d,p=draft(cur,f);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key in('finance.hpp.view','warehouse.stock.adjust')",(role,));conn.commit()
        r=ops.rpc('erp_cp7_get_material_counts_v1',dict(p_query=dict(adjustment_id=d['adjustment_id'])));assert r['status']==200 and 'valuation' not in json.dumps(r['body'])
        args=dict(p_action='POST',p_payload=dict(adjustment_id=d['adjustment_id'],change_reason='HTTP count'),p_request=str(uuid.uuid4()),p_expected=d['row_version'])
        assert http.anon_rpc('erp_cp7_save_material_count_v1',args)['status'] in(401,403,404) and ops.rpc('erp_cp7_save_material_count_v1',args)['status']==403
        result=owner.rpc('erp_cp7_save_material_count_v1',args);assert result['status']==200,result
        assert owner.rpc('erp_cp7_save_material_count_v1',args)['body']==result['body']
        with http.connect() as conn,conn.cursor() as cur:
            assert qty(cur,f)==8;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_save_material_count_v1',args)['status']==403
        return dict(status='PASS',real_auth_http_count=True,one_effect=True,current_access_before_cache=True,ops_money_redaction=True)
    return [('P09_COUNT_HTTP',flow)]
