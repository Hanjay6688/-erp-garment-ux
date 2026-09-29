"""Dated accessory purchase units through the connected receipt boundary."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import copy,json,threading,time,uuid
import psycopg
import cp7_procurement_cases as receipt
import cp7_receipt_reversal_cases as reversal
auth,b,bc,aa=receipt.auth,receipt.b,receipt.bc,receipt.aa

def fixture(cur,today,uom='LUSIN',qty='2',price='120',final=False):
    f=receipt.fixture(cur,today);a=bc.fixture(cur,today,purchase=False,zones=False)
    f.update(material=a['material'],category=a['category'],unit=a['pcs'])
    f['payload']['lines']=[dict(material_id=a['material'],purchase_qty_entered=qty,purchase_uom_code=uom,purchase_price_per_uom_snapshot=price,
      price_state='FINAL' if final else 'ESTIMATED',price_source='SUPPLIER_INVOICE' if final else 'MANUAL_ESTIMATE',rolls=[])]
    return f

def options(cur,f,at=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_procurement_uom_v1(%s,%s)',(f['material'],at or f['payload']['physical_at'])).fetchone()[0]
    b.api.admin(cur);return r

def row(cur,d):
    return cur.execute('select qty,unit_price,line_total,purchase_qty_entered,purchase_uom_code,purchase_uom_factor_snapshot,purchase_price_per_uom_snapshot from erp.material_purchase_items where purchase_id=%s',(d['purchase_id'],)).fetchone()

def custom_uom(cur,f,factor,at,unit=None):
    unit=unit or 'P09-'+uuid.uuid4().hex[:10].upper()
    if not cur.execute('select exists(select 1 from erp.uom_definitions where unit_code=%s)',(unit,)).fetchone()[0]:
        cur.execute("insert into erp.uom_definitions(unit_code,unit_name,dimension,is_active) values(%s,'P09 supplier pack','COUNT',true)",(unit,))
    version=cur.execute('select row_version from erp.accessory_categories where id=%s',(f['category'],)).fetchone()[0]
    bc.internal(cur,'set_accessory_uom_conversion_v2',f['category'],unit,Decimal(factor),at,'Supplier packing unit','P09 effective unit master',str(uuid.uuid4()),version)
    b.api.admin(cur);return unit

def cases(cur,today):
    def convert(gross):
        before=reversal.net_ledger(cur);f=fixture(cur,today,'GROSS' if gross else 'LUSIN','0.5' if gross else '2','1440' if gross else '120',gross)
        choices=options(cur,f);u=next(u for u in choices['rows'] if u['code']==f['payload']['lines'][0]['purchase_uom_code'])
        factor=144 if gross else 12;qty=72 if gross else 24;amount=720 if gross else 240
        assert Decimal(u['factor'])==factor
        d=receipt.command(cur,'SAVE_DRAFT',f['payload']);assert receipt.qty(cur,f)==(0,0)
        assert row(cur,d)==(qty,10,amount,Decimal('0.5' if gross else '2'),'GROSS' if gross else 'LUSIN',factor,1440 if gross else 120),row(cur,d)
        w=receipt.workspace(cur,dict(purchase_id=d['purchase_id']));assert Decimal(w['detail']['items'][0]['finance']['purchase_price_per_uom'])==(1440 if gross else 120)
        f['receipt']=receipt.post(cur,d);assert receipt.qty(cur,f)==(qty,1)
        ap,grni=cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)',(d['purchase_id'],d['purchase_id'])).fetchone()
        assert (ap,grni)==((amount,0) if gross else (0,amount)),(ap,grni)
        reversal.reverse(cur,f);assert receipt.qty(cur,f)==(0,2) and reversal.net_ledger(cur)==before
        return dict(status='PASS',unit=u['code'],factor=factor,stock_qty=qty,unit_cost=10,document_value=amount,price_per_purchase_unit_preserved=True,inverse_all_account_balances_restored=True)
    def dated():
        f=fixture(cur,today);at=aa.at(f['day']-timedelta(days=1),0);unit=custom_uom(cur,f,'10',at)
        split=aa.at(f['day']+timedelta(days=1),0);custom_uom(cur,f,'20',split,unit)
        p=f['payload'];p['lines'][0].update(purchase_uom_code=unit,purchase_price_per_uom_snapshot='100')
        d=receipt.command(cur,'SAVE_DRAFT',p);assert row(cur,d)==(20,10,200,2,unit,10,100),row(cur,d)
        future=copy.deepcopy(p);future.update(purchase_number=p['purchase_number']+'-NEXT',physical_at=aa.at(f['day']+timedelta(days=2),10).isoformat())
        assert Decimal(next(x for x in options(cur,f)['rows'] if x['code']==unit)['factor'])==10
        assert Decimal(next(x for x in options(cur,f,future['physical_at'])['rows'] if x['code']==unit)['factor'])==20
        next_d=receipt.command(cur,'SAVE_DRAFT',future);assert row(cur,next_d)==(40,5,200,2,unit,20,100),row(cur,next_d)
        receipt.post(cur,d);receipt.post(cur,next_d);assert receipt.qty(cur,f)==(60,2)
        return dict(status='PASS',dated_factor=[10,20],base_qty=[20,40],same_entered_qty=2,price_per_pack=100,each_document_value=200)
    def invalid():
        f=fixture(cur,today);before=b.boundary.snapshot(cur)
        bad=copy.deepcopy(f['payload']);bad['lines'][0]['purchase_qty_entered']='0.1'
        auth.refused(cur,lambda:receipt.command(cur,'SAVE_DRAFT',bad),'fractional base pieces')
        bad=copy.deepcopy(f['payload']);bad['lines'][0]['purchase_uom_factor_snapshot']='999'
        auth.refused(cur,lambda:receipt.command(cur,'SAVE_DRAFT',bad),'CP7_PROCUREMENT_FIELDS')
        bad=copy.deepcopy(f['payload']);bad['lines'][0]['unit_price']='0'
        auth.refused(cur,lambda:receipt.command(cur,'SAVE_DRAFT',bad),'CP7_PROCUREMENT_UOM_FIELDS')
        bad=copy.deepcopy(f['payload']);bad['lines'][0]['purchase_qty_entered']=2
        auth.refused(cur,lambda:receipt.command(cur,'SAVE_DRAFT',bad),'CP7_PROCUREMENT_FIELDS')
        assert b.boundary.snapshot(cur)==before
        fabric=receipt.fixture(cur,today);bad=copy.deepcopy(f['payload']);bad['lines'][0]['material_id']=fabric['material']
        auth.refused(cur,lambda:receipt.command(cur,'SAVE_DRAFT',bad),'CP7_PROCUREMENT_ACCESSORY_REQUIRED')
        assert receipt.qty(cur,f)==(0,0) and receipt.qty(cur,fabric)==(0,0)
        return dict(status='PASS',fractional_count_and_forged_factor_refused=True,no_dummy_base_price=True,exact_string_quantity=True,no_fabric_uom_conversion=True,all_rejections_atomic=True)
    def replay_access():
        f=fixture(cur,today);unit=custom_uom(cur,f,'10',aa.at(f['day']-timedelta(days=1),0));f['payload']['lines'][0]['purchase_uom_code']=unit
        key=str(uuid.uuid4());d=receipt.command(cur,'SAVE_DRAFT',f['payload'],key)
        cur.execute('update erp.uom_definitions set is_active=false where unit_code=%s',(unit,))
        assert receipt.command(cur,'SAVE_DRAFT',f['payload'],key)==d
        auth.refused(cur,lambda:receipt.command(cur,'SAVE_DRAFT',f['payload']),'CP7_PROCUREMENT_ACTIVE_UOM_REQUIRED')
        assert all(u['code']!=unit for u in options(cur,f)['rows'])
        ops,role=receipt.custom(cur,receipt.OPS)
        assert options(cur,f,subject=ops)['rows']
        w=receipt.workspace(cur,dict(purchase_id=d['purchase_id']),ops)
        assert 'purchase_price_per_uom' not in json.dumps(w) and 'finance' not in w['detail']
        auth.refused(cur,lambda:receipt.command(cur,'SAVE_DRAFT',f['payload'],key,subject=ops),'CP7_PROCUREMENT_VALUE_DENIED')
        for principal in ('authenticated','anon','service_role','cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,'cp7_procurement.validate_uom_lines(jsonb)','EXECUTE')",(principal,)).fetchone()[0]
        return dict(status='PASS',replay_after_master_deactivation=True,new_intent_refuses_inactive_unit=True,ops_units_without_money=True,financial_write_permission_current=True,private_validator_no_public_execute=True)
    def mixed():
        f=fixture(cur,today);fabric=receipt.fixture(cur,today);p=copy.deepcopy(f['payload']);p['lines'].append(fabric['payload']['lines'][0])
        d=receipt.command(cur,'SAVE_DRAFT',p);receipt.post(cur,d)
        assert receipt.qty(cur,f)==(24,1) and receipt.qty(cur,fabric)==(10,1)
        assert cur.execute('select erp.material_purchase_grni_total(%s)',(d['purchase_id'],)).fetchone()[0]==340
        return dict(status='PASS',mixed_fabric_base_and_accessory_purchase_units=True,fabric_qty=10,accessory_qty=24,grni=340)
    return [('P09_UOM_DOZEN',lambda:convert(False)),('P09_UOM_GROSS_FINAL',lambda:convert(True)),('P09_UOM_DATED_MASTER',dated),('P09_UOM_ATOMIC_INVALID',invalid),('P09_UOM_REPLAY_ACCESS',replay_access),('P09_UOM_MIXED_RECEIPT',mixed)]

def races(tools,today):
    def same():
        with tools.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);conn.commit()
        barrier=threading.Barrier(2);key=str(uuid.uuid4())
        def send():
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait(5);r=receipt.command(cur,'SAVE_DRAFT',f['payload'],key);conn.commit();return r
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(send);z=pool.submit(send);results=[a.result(20),z.result(20)]
        assert results[0]==results[1]
        with tools.connect() as conn,conn.cursor() as cur:
            assert cur.execute('select count(*) from erp.material_purchase_headers where purchase_number=%s',(f['tag'],)).fetchone()[0]==1
            assert row(cur,results[0])[:3]==(24,10,240) and receipt.qty(cur,f)==(0,0)
        return dict(status='PASS',same_request_one_draft=True,authoritative_conversion_once=True)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);d=receipt.command(cur,'SAVE_DRAFT',f['payload']);subject,role=receipt.custom(cur,[*receipt.OPS,'finance.ap.view']);conn.commit()
        p=copy.deepcopy(f['payload']);p['id']=d['purchase_id'];p['lines'][0]['purchase_qty_entered']='3'
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.material_purchase_headers where id=%s for update',(d['purchase_id'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:receipt.command(cur,'SAVE_DRAFT',p,version=d['row_version'],subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                task=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspector,inspector.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                    assert blocked,'UOM_SAVE_NOT_WAITING'
                    with tools.connect() as conn,conn.cursor() as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.create'",(role,));conn.commit()
                finally:holder.rollback()
                error=task.result(20)
        assert 'CP7_PROCUREMENT_ACCESS_CHANGED' in error or 'Internal ERP access required' in error,error
        with tools.connect() as conn,conn.cursor() as cur:assert row(cur,d)[:3]==(24,10,240) and receipt.qty(cur,f)==(0,0)
        return dict(status='PASS',current_revoke_at_real_draft_wait=True,no_partial_quantity_or_price_change=True)
    return [('P09_UOM_RACE_SAME_SAVE',same),('P09_UOM_RACE_REVOKE_SAVE',revoke)]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','p09-uom-owner');ops=http.login('ADMIN','p09-uom-ops')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);cur.execute("delete from erp.app_role_permissions where role_id=(select id from erp.app_roles where role_code='ADMIN') and permission_key='finance.ap.view'");conn.commit()
        choice=ops.rpc('erp_cp7_get_procurement_uom_v1',dict(p_material=f['material'],p_at=f['payload']['physical_at']));assert choice['status']==200,choice
        args=dict(p_action='SAVE_DRAFT',p_payload=f['payload'],p_request=str(uuid.uuid4()),p_expected=None)
        assert ops.rpc('erp_cp7_save_procurement_v1',args)['status']==403
        d=owner.rpc('erp_cp7_save_procurement_v1',args);assert d['status']==200,d
        assert owner.rpc('erp_cp7_save_procurement_v1',args)['body']==d['body']
        w=ops.rpc('erp_cp7_get_procurement_v1',dict(p_query=dict(purchase_id=d['body']['purchase_id'])));assert w['status']==200 and 'purchase_price_per_uom' not in json.dumps(w['body'])
        post=dict(p_action='POST',p_payload=dict(purchase_id=d['body']['purchase_id'],change_reason='Review purchase units'),p_request=str(uuid.uuid4()),p_expected=d['body']['row_version'])
        r=owner.rpc('erp_cp7_save_procurement_v1',post);assert r['status']==200,r
        with http.connect() as conn,conn.cursor() as cur:assert receipt.qty(cur,f)==(24,1)
        return dict(status='PASS',real_auth_and_dated_master=True,purchase_unit_price_redacted=True,one_posted_effect=True,base_stock=24)
    return [('P09_UOM_HTTP',flow)]
