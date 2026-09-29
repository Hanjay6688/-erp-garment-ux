"""Native current stock and ordinary transfers for materials without rolls."""
from decimal import Decimal
import copy,json,uuid
import cp7_material_cases as material
import cp7_procurement_cases as receipt
import cp7_invoice_cases as invoice
auth,b,bc=receipt.auth,receipt.b,receipt.bc

def fixture(cur,today,kind='ACCESSORY'):
    f=receipt.fixture(cur,today);master=bc.fixture(cur,today,purchase=False,zones=False)
    if kind=='ACCESSORY':f['material']=master['material']
    else:
        f['material']=str(cur.execute("insert into erp.materials(material_sku,material_name,material_type,unit_code) values(%s,'P09 unrolled other','OTHER',%s) returning id",(f['tag']+'-OTHER',master['pcs'])).fetchone()[0])
    f['payload']['lines']=[dict(material_id=f['material'],qty='10',unit_price='10',price_state='ESTIMATED',price_source='MANUAL_ESTIMATE',rolls=[])]
    d=receipt.command(cur,'SAVE_DRAFT',f['payload']);f['receipt']=receipt.post(cur,d)
    f['roll']=None;f['item']=str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(d['purchase_id'],)).fetchone()[0])
    f['destination']=str(uuid.uuid4());cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,%s,'RAW_MATERIAL_WAREHOUSE',true)",(f['destination'],f['tag']+'-TO',f['tag']+' destination'))
    return f

def cases(cur,today):
    def transfer(kind):
        f=fixture(cur,today,kind);w=material.stock(cur,f);r=w['page']['rows'][0]
        assert r['material_type']==kind and r['roll_id'] is None and r['roll_number'] is None and r['quality']=='KNOWN' and r['availability']=='ON_HAND'
        d,p=material.draft(cur,f);d=material.post(cur,d)
        assert material.balances(cur,f)=={f['location']:6,f['destination']:4}
        source=material.ledger(cur,f,f['location'],0,1);assert source['roll_id'] is None and Decimal(source['page']['rows'][0]['running_qty'])==6 and source['page']['next_offset']==1
        assert Decimal(material.ledger(cur,f,f['location'],1,1)['page']['rows'][0]['running_qty'])==10
        inv=invoice.finalize(cur,f,'10','12.5');assert invoice.amounts(cur,f)==(125,0,10,Decimal('12.5'))
        assert sum(Decimal(r['valuation']['value']) for r in material.stock(cur,f)['page']['rows'])==125
        invoice.reverse(cur,f,inv['invoice_id']);material.reverse(cur,d)
        assert material.balances(cur,f)=={f['location']:10,f['destination']:0} and invoice.amounts(cur,f)==(0,100,10,10)
        ops,role=receipt.custom(cur,material.PERMS)
        assert 'valuation' not in json.dumps(material.ledger(cur,f,f['location'],subject=ops))
        return dict(status='PASS',kind=kind,null_roll_is_valid_stock=True,warehouse_balances=[6,4],late_invoice_value=125,invoice_inverse_value=100,transfer_inverse_stock=[10,0],server_ops_redaction=True)
    def zones_replay():
        f=fixture(cur,today);zone=bc.svc(cur,'REGISTER_ZONE',dict(zone_kind='SERVICE_POST',location_code=f['tag']+'-ZONE',location_name='P09 accessory service',reason='P09 service workflow boundary'))['location_id'];b.api.admin(cur)
        d,p=material.draft(cur,f);before=b.boundary.snapshot(cur)
        for key in ('from_location_id','to_location_id'):
            bad=copy.deepcopy(p);bad[key]=str(zone)
            auth.refused(cur,lambda:material.command(cur,'SAVE_TRANSFER',bad),'CP7_MATERIAL_SERVICE_ZONE_WORKFLOW_REQUIRED')
        bad=copy.deepcopy(p);bad['items'][0]['roll_id']=str(uuid.uuid4())
        auth.refused(cur,lambda:material.command(cur,'SAVE_TRANSFER',bad),'CP7_MATERIAL_LINEAGE_REQUIRED')
        assert b.boundary.snapshot(cur)==before
        key=str(uuid.uuid4());p['transfer_number']+='-CACHE';saved=material.command(cur,'SAVE_TRANSFER',p,key=key)
        cur.execute('update erp.locations set is_active=false where id=%s',(f['destination'],))
        assert material.command(cur,'SAVE_TRANSFER',p,key=key)==saved
        auth.refused(cur,lambda:material.command(cur,'SAVE_TRANSFER',p),'CP7_MATERIAL_ACTIVE_WAREHOUSES_REQUIRED')
        auth.refused(cur,lambda:material.post(cur,saved),'CP7_MATERIAL_ACTIVE_WAREHOUSES_REQUIRED')
        assert material.balances(cur,f)=={f['location']:10}
        for principal in ('authenticated','anon','service_role','cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,'cp7_material.validate_transfer_scope(uuid,uuid,uuid)','EXECUTE')",(principal,)).fetchone()[0]
        return dict(status='PASS',service_locations_require_service_workflow=True,no_fake_roll=True,cached_outcome_before_mutable_master_check=True,new_intent_requires_active_warehouses=True)
    def pages():
        f=fixture(cur,today);d,p=material.draft(cur,f,'3');material.post(cur,d)
        other=str(cur.execute("insert into erp.locations(location_code,location_name,location_type,is_active) values(%s,'P09 third warehouse','RAW_MATERIAL_WAREHOUSE',true) returning id",(f['tag']+'-THREE',)).fetchone()[0])
        d,p=material.draft(cur,f,'2',dest=other);material.post(cur,d)
        offset=0;seen=[]
        while True:
            w=material.stock(cur,f,limit=1,offset=offset)
            assert w['page']['total']=='3' and len(w['totals_by_unit'])==1 and Decimal(w['totals_by_unit'][0]['qty'])==10
            seen.extend(r['location_id'] for r in w['page']['rows']);offset=w['page']['next_offset']
            if offset is None:break
        assert set(seen)=={f['location'],f['destination'],other} and len(seen)==3
        return dict(status='PASS',null_roll_pages_complete=3,total_qty=10,no_synthetic_roll_identity=True)
    return [('P09_ACCESSORY_LEDGER_TRANSFER',lambda:transfer('ACCESSORY')),('P09_OTHER_LEDGER_TRANSFER',lambda:transfer('OTHER')),
      ('P09_UNROLLED_SERVICE_ZONE_REPLAY',zones_replay),('P09_UNROLLED_COMPLETE_PAGES',pages)]
