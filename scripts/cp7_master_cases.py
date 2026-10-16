"""Owner D15-3 (FABLE-017, ASTRA-C17-04, KNOWN-DAILY-MASTER): master data and Mandor work rates from the app.

Native, race and real-Auth HTTP cases, spliced into the CP17 r2 harness (cp7_cp17_fix_cases.py). Every write under test
goes through the public facades (erp_cp7_save_master_v1, erp_cp7_save_work_rate_v1) or the public commands of the
screens that use the records (sales draft, receipt, Bagi Potongan, Catat selesai jahit). SQL is used only for isolation
fixtures (a posted cutting, an extra app user of a seeded role) and for oracles, never for the records under test.
Fable D15-3 oracle: a new Mandor and a new rate from the master screen -> Bagi Potongan -> "Catat selesai jahit" pays the
rate valid on the sewing date; a rate changed afterwards does not change the wage already recorded.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from decimal import Decimal as D
import json,threading,uuid
import psycopg
import cp7_snapshot_cases as auth
import cp7_sales_draft_cases as draft
import cp7_procurement_cases as proc
import cp7_cutting_correction_cases as cut
b=auth.b
refused=auth.refused

NATIVE=['CP17_R2_MASTER_CUSTOMER_LIFECYCLE','CP17_R2_MASTER_CUSTOMER_USED_IN_SALES','CP17_R2_MASTER_SUPPLIER_LOCATION_FABRIC_IN_RECEIPT',
        'CP17_R2_MASTER_VENDOR_AND_LOCATION_RULES','CP17_R2_MASTER_MANDOR_POLICY_AND_PICKUP_LIST','CP17_R2_MASTER_FABRIC_PROFILE_BENCHMARK',
        'CP17_R2_MASTER_ACCESSORY_CATEGORY_VARIANT_PRICE','CP17_R2_MASTER_ACCESS_RIGHTS','CP17_R2_MASTER_RATE_VERSIONS_AND_BOM',
        'CP17_R2_FABLE_D15_3_SCREEN_CHAIN_WAGE_AT_SEWING_DATE']
# One two-tab race per master screen (Fable D15-3: "balapan dua tab untuk setiap layar master").
RACES=['CP17_RACE_R2_MASTER_CUSTOMER_SAME_RECORD_TWO_TABS','CP17_RACE_R2_MASTER_PARTNER_SAME_CODE_TWO_TABS','CP17_RACE_R2_MASTER_MANDOR_POLICY_TWO_TABS',
       'CP17_RACE_R2_WORK_RATE_TWO_TABS','CP17_RACE_R2_MASTER_LOCATION_DEACTIVATE_AND_UPDATE_TWO_TABS','CP17_RACE_R2_MASTER_FABRIC_BENCHMARK_TWO_TABS',
       'CP17_RACE_R2_MASTER_ACCESSORY_SAME_CODE_TWO_TABS']
HTTP=['CP17_HTTP_R2_MASTER','CP17_HTTP_R2_WORK_RATE']
# Every master screen on desktop and phone (Fable D15-3), plus the screen-only chain Mandor + rate -> Bagi Potongan -> sewing.
BROWSER=[f'CP17_BROWSER_R2_MASTER_{screen}_{device}' for screen in('CUSTOMERS','PARTNERS','WORKFORCE_RATES','LOCATIONS','FABRIC','ACCESSORY')
         for device in('DESKTOP','MOBILE')]+['CP17_BROWSER_R2_FABLE_D15_3_SCREEN_CHAIN_DESKTOP']
FUNCTIONS=('erp_cp7_get_master_v1','erp_cp7_save_master_v1','erp_cp7_get_work_rates_v1','erp_cp7_save_work_rate_v1')

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def tag():return uuid.uuid4().hex[:8].upper()
def call(cur,sql,args,subject=None):
    auth.actor(cur,subject);r=one(cur,sql,args);b.api.admin(cur);return r
def ws(cur,kind,q=None,subject=None):return call(cur,'select public.erp_cp7_get_master_v1(%s,%s)',(kind,json.dumps(q or {})),subject)
def save(cur,kind,p,key=None,subject=None):return call(cur,'select public.erp_cp7_save_master_v1(%s,%s,%s)',(kind,json.dumps(p),str(key or uuid.uuid4())),subject)
def rws(cur,q,subject=None):return call(cur,'select public.erp_cp7_get_work_rates_v1(%s)',(json.dumps(q),),subject)
def rsave(cur,action,p,key=None,subject=None):return call(cur,'select public.erp_cp7_save_work_rate_v1(%s,%s,%s)',(action,json.dumps(p),str(key or uuid.uuid4())),subject)
def selected(cur,kind,id,subject=None):return ws(cur,kind,dict(id=id),subject)['selected']
def create(cur,kind,fields,reason='Data baru dari layar master',key=None,subject=None):
    return save(cur,kind,dict(action='CREATE',fields=fields,reason=reason),key,subject)
def act(cur,kind,id,action,fields=None,reason='Perubahan dari layar master',token=None,key=None,subject=None):
    p=dict(action=action,id=id,review_token=token or selected(cur,kind,id,subject)['review_token'],reason=reason)
    if fields is not None:p['fields']=fields
    return save(cur,kind,p,key,subject)
def customer_fields(code,name='Toko CP17',**kw):return dict(dict(code=code,name=name,phone=None,address=None),**kw)
def mandor_fields(code,policy_from,**kw):return dict(dict(code=code,name='Mandor '+code,attendance_required=False,is_special=False,policy_from=policy_from,notes=None),**kw)
def fabric_fields(code,**kw):return dict(dict(code=code,name='Kain '+code,unit='YD',fabric_category='Denim',composition=None,construction=None,color_name='Indigo',
    width_cm='150',gsm=None,minimum_stock_qty='0',preferred_supplier_id=None,notes=None),**kw)
def role_actor(cur,role_code):
    """An active app user of a seeded role (isolation fixture, as other suites); returns its Auth subject."""
    b.api.admin(cur);subject,user=str(uuid.uuid4()),str(uuid.uuid4())
    role=one(cur,'select id from erp.app_roles where role_code=%s',(role_code,))
    cur.execute('insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)values(%s,%s,%s,%s,%s,true)',(user,subject,'CP17 master '+role_code,role_code,role))
    return subject
def history(cur,entity):b.api.admin(cur);return one(cur,'select count(*) from cp7_master.history where entity_id=%s',(entity,))
def prod():return cut.cutting.qc.physical.b.chain.production
def wib(day):return f'{day:%Y-%m-%d}'

def cutting_only(cur,today):
    """A posted cutting of 10 pieces on a fresh PO without a Mandor (the Native writers of Buat Potongan), not yet distributed."""
    src=cut.cutting;p=prod();base=src.qc.physical.base
    f=p.estimated_receipt(cur,today);b.api.admin(cur)
    day=f['purchase_day']+timedelta(days=1);po=str(uuid.uuid4())
    cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes) values(%s,%s,%s,10,'CUTTING','CUTTING',%s,'CP17 D15-3 chain fixture')",
        (po,'CP17-MDR-'+po,p.MODEL,p.at(day,7)))
    payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=p.PATTERN,source_location_id=f['location'],cut_at=p.at(day,8),
        change_reason='CP17 D15-3 posted cutting',size_slots=[dict(slot_no=1,size_id=base.SIZE,drawing_no=1)],
        rolls=[dict(roll_id=f['roll'],qty_issued=10,qty_consumed=10,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=10)])])
    saved=p.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload)
    saved=p.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(payload,id=saved['cutting_group_id'],action='POST'),expected_version=int(saved['row_version']))
    g=saved['cutting_group_id'];b.api.admin(cur)
    return dict(group=g,po=po,model=str(p.MODEL),day=day,at=lambda h,minute=0:p.at(day,h,minute),
                number=one(cur,'select group_number from erp.cutting_groups where id=%s',(g,)))

def model_components(cur,model,since_day):
    """The model's Work BOM valid on since_day, through the rate screen: the current version when there is one, otherwise
    a first version written through SAVE_BOM (default rates 2 and 1) from that day."""
    w=rws(cur,dict(model_id=model))
    if w['model']['components']:return [c['component_id'] for c in w['model']['components'] if c['in_current_bom']],False
    c1=rsave(cur,'CREATE_COMPONENT',dict(code='JHT-'+tag(),name='Jahit CP17',category='LABOR',reason='Komponen kerja model baru'))['id']
    c2=rsave(cur,'CREATE_COMPONENT',dict(code='OBR-'+tag(),name='Obras CP17',category='LABOR',reason='Komponen kerja model baru'))['id']
    rsave(cur,'SAVE_BOM',dict(model_id=model,items=[dict(work_component_id=c1,sequence_no=1,default_rate='2'),dict(work_component_id=c2,sequence_no=2,default_rate='1')],
        effective_date=wib(since_day),review_token=w['model']['bom_review_token'],reason='Komponen kerja model dari layar'))
    return [c1,c2],True

def wage_of(cur,group):
    """Posted WORK_COMPLETION wage journal of the group's sewing records (Native rows, not the command)."""
    b.api.admin(cur)
    return cur.execute("""select coalesce(sum(l.debit) filter(where l.account_id=erp.account_id('WIP')),0),coalesce(sum(l.credit) filter(where l.account_id=erp.account_id('CONTRACTOR_PAYABLE')),0),
        count(distinct j.id) from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id join erp.work_completion_events w on w.id=j.source_id
        where j.source_type='WORK_COMPLETION' and j.status='POSTED' and w.cutting_group_id=%s""",(group,)).fetchone()


def cases(cur,today):
    import cp7_cp17_fix_cases as cp17
    def customer_lifecycle():
        code='cus-'+tag().lower();key=uuid.uuid4()
        p=dict(action='CREATE',fields=customer_fields(code,' Toko CP17 ',phone=' 0812 ',address=''),reason='Pelanggan baru dari layar')
        c=save(cur,'CUSTOMER',p,key)
        e=c['entity'];assert (e['code'],e['name'],e['phone'],e['address'],e['active'])==(code.upper(),'Toko CP17','0812',None,True),e
        assert save(cur,'CUSTOMER',p,key)==c
        refused(cur,lambda:save(cur,'CUSTOMER',dict(p,reason='Alasan lain sekali'),key),'CP7_MASTER_REQUEST_CHANGED')
        refused(cur,lambda:create(cur,'CUSTOMER',customer_fields(code.lower())),'CP7_MASTER_DUPLICATE_CODE')
        old=selected(cur,'CUSTOMER',c['id'])['review_token']
        u=act(cur,'CUSTOMER',c['id'],'UPDATE',customer_fields(code.upper(),'Toko CP17 Jaya',phone='0812'),'Nama toko dibetulkan',token=old)
        assert u['entity']['name']=='Toko CP17 Jaya'
        before=b.boundary.snapshot(cur)
        refused(cur,lambda:act(cur,'CUSTOMER',c['id'],'UPDATE',customer_fields(code.upper(),'Toko Lain',phone='0812'),token=old),'CP7_MASTER_REVIEW_CHANGED')
        refused(cur,lambda:act(cur,'CUSTOMER',c['id'],'UPDATE',customer_fields(code.upper(),'Toko CP17 Jaya',phone='0812')),'CP7_MASTER_NO_CHANGE')
        cp17.unchanged(cur,before,'master refusals')
        at=(draft.source.fg.ax.r1.now(cur)-timedelta(minutes=5)).isoformat()
        assert draft.options(cur,'CUSTOMER',at,q=code)['total']=='1'
        d=act(cur,'CUSTOMER',c['id'],'DEACTIVATE',reason='Toko tutup');assert d['entity']['active'] is False
        assert draft.options(cur,'CUSTOMER',at,q=code)['total']=='0'
        r=act(cur,'CUSTOMER',c['id'],'REACTIVATE',reason='Toko buka lagi');assert r['entity']['active'] is True
        s=selected(cur,'CUSTOMER',c['id'])
        reasons=[a['reason'] for a in s['audit']]
        assert reasons[:4]==['Toko buka lagi','Toko tutup','Nama toko dibetulkan','Pelanggan baru dari layar'],reasons
        assert history(cur,c['id'])==4
        refused(cur,lambda:cur.execute('delete from cp7_master.history where entity_id=%s',(c['id'],)),'CP7_MASTER_HISTORY_IMMUTABLE')
        return dict(status='PASS',created_normalized=e,same_request_same_answer=True,changed_request_refused=True,duplicate_code_case_insensitive_refused=True,
                    stale_review_and_no_change_refused_without_change=True,deactivated_hidden_from_sales_picker=True,audit_reasons=reasons[:4],history_rows=4,history_immutable=True)
    def customer_used_in_sales():
        f=draft.fixture(cur,today);code='CUS-'+tag()
        c=create(cur,'CUSTOMER',customer_fields(code,'Toko Baru CP17'));f['customer']=c['id']
        o=draft.options(cur,'CUSTOMER',f['sale_at'],q=code);assert o['total']=='1' and o['rows'][0]['id']==c['id'],o
        d=draft.create(cur,f)
        assert one(cur,'select customer_id::text from erp.sales_headers where id=%s',(d['sale_id'],))==c['id']
        s=selected(cur,'CUSTOMER',c['id'])
        assert s['used'] and s['usage']['sales_draft']==1 and [x['kind'] for x in s['deactivate_blockers']]==['OPEN_SALES_DRAFT'],s
        before=b.boundary.snapshot(cur)
        refused(cur,lambda:act(cur,'CUSTOMER',c['id'],'UPDATE',customer_fields(code+'X','Toko Baru CP17')),'CP7_MASTER_CODE_IN_USE')
        refused(cur,lambda:act(cur,'CUSTOMER',c['id'],'DEACTIVATE',reason='Coba nonaktif'),'CP7_MASTER_BLOCKED')
        cp17.unchanged(cur,before,'used customer refusals')
        u=act(cur,'CUSTOMER',c['id'],'UPDATE',customer_fields(code,'Toko Baru CP17 Jaya'),'Nama toko dibetulkan')
        assert u['entity']['name']=='Toko Baru CP17 Jaya' and one(cur,'select customer_id::text from erp.sales_headers where id=%s',(d['sale_id'],))==c['id']
        return dict(status='PASS',new_customer_in_sales_picker=True,sales_draft_created_with_it=d['sale_id'],code_change_after_use_refused=True,
                    deactivate_with_open_draft_refused=True,name_corrected_document_keeps_customer=True)
    def supplier_location_fabric_in_receipt():
        t=tag();sup=create(cur,'SUPPLIER',dict(code='SUP-'+t,name='Supplier CP17',supplier_type='MATERIAL',phone=None,address=None))
        loc=create(cur,'LOCATION',dict(code='GDG-'+t,name='Gudang CP17',location_type='RAW_MATERIAL_WAREHOUSE'))
        fab=create(cur,'FABRIC',fabric_fields('KAIN-'+t,preferred_supplier_id=sup['id']))
        for kind,q,id in (('SUPPLIER','SUP-'+t,sup['id']),('LOCATION','GDG-'+t,loc['id']),('MATERIAL','KAIN-'+t,fab['id'])):
            o=proc.options(cur,kind,q);assert [r['id'] for r in o['rows']]==[id],(kind,o)
        f=proc.fixture(cur,today);p=f['payload'];p['supplier_id']=sup['id'];p['location_id']=loc['id'];p['lines'][0]['material_id']=fab['id']
        d=proc.command(cur,'SAVE_DRAFT',p);posted=proc.post(cur,d)
        b.api.admin(cur)
        moved=one(cur,'select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s and location_id=%s',(fab['id'],loc['id']))
        assert D(moved)==D(p['lines'][0]['qty']),moved
        before=b.boundary.snapshot(cur)
        refused(cur,lambda:act(cur,'LOCATION',loc['id'],'DEACTIVATE',reason='Gudang ditutup'),'STOCK_AT_LOCATION')
        refused(cur,lambda:act(cur,'LOCATION',loc['id'],'UPDATE',dict(code='GDG-'+t,name='Gudang CP17',location_type='OTHER')),'CP7_MASTER_TYPE_IN_USE')
        refused(cur,lambda:act(cur,'FABRIC',fab['id'],'DEACTIVATE',reason='Kain dihentikan'),'STOCK_ON_HAND')
        refused(cur,lambda:act(cur,'FABRIC',fab['id'],'UPDATE',fabric_fields('KAIN-'+t,unit='M',preferred_supplier_id=sup['id'])),'CP7_MASTER_UNIT_IN_USE')
        refused(cur,lambda:act(cur,'SUPPLIER',sup['id'],'UPDATE',dict(code='SUP-'+t+'X',name='Supplier CP17',supplier_type='MATERIAL',phone=None,address=None)),'CP7_MASTER_CODE_IN_USE')
        cp17.unchanged(cur,before,'stocked master refusals')
        # The screen's predicate is the Native guard's: the same deactivation written directly is refused by Native too.
        refused(cur,lambda:cur.execute('update erp.locations set is_active=false where id=%s',(loc['id'],)),'Lokasi masih memiliki stok')
        # A stocked warehouse from older data with a lower-case code (the receipt fixture's): the edit form sends the stored code
        # back, which is no code change (codes are matched without case), so the type refusal is the reason given, the name can
        # still be corrected, and the stored code is kept exactly as it was.
        old=cut.cutting.qc.physical.b.chain.production.estimated_receipt(cur,today);b.api.admin(cur);lid=str(old['location'])
        code0,name0=cur.execute('select location_code,location_name from erp.locations where id=%s',(lid,)).fetchone()
        assert code0!=code0.upper(),code0
        before=b.boundary.snapshot(cur)
        refused(cur,lambda:act(cur,'LOCATION',lid,'UPDATE',dict(code=code0,name=name0,location_type='OTHER')),'CP7_MASTER_TYPE_IN_USE')
        refused(cur,lambda:act(cur,'LOCATION',lid,'UPDATE',dict(code=code0+'X',name=name0,location_type='RAW_MATERIAL_WAREHOUSE')),'CP7_MASTER_CODE_IN_USE')
        cp17.unchanged(cur,before,'older stocked location refusals')
        r=act(cur,'LOCATION',lid,'UPDATE',dict(code=code0,name='Gudang lama CP17',location_type='RAW_MATERIAL_WAREHOUSE'),'Nama gudang lama dibetulkan')
        assert(r['entity']['code'],r['entity']['name'])==(code0,'Gudang lama CP17'),r['entity']
        r=act(cur,'LOCATION',lid,'UPDATE',dict(code=code0.upper(),name='Gudang lama CP17 B',location_type='RAW_MATERIAL_WAREHOUSE'),'Nama gudang lama dibetulkan lagi')
        assert(r['entity']['code'],one(cur,'select location_code from erp.locations where id=%s',(lid,)))==(code0,code0),r['entity']
        return dict(status='PASS',new_supplier_location_fabric_in_receipt_pickers=True,receipt_posted=posted.get('purchase_id',d.get('purchase_id')),stock_at_new_location=str(moved),
                    deactivate_location_and_fabric_with_stock_refused=True,type_unit_code_after_use_refused=True,native_guard_agrees=True,
                    older_lower_case_code_kept_on_edit=code0)
    def vendor_and_location_rules():
        t=tag();v=create(cur,'LAUNDRY_VENDOR',dict(code='LDY-'+t,name='Laundry CP17',phone='021',notes='cuci batu'))
        assert act(cur,'LAUNDRY_VENDOR',v['id'],'DEACTIVATE',reason='Vendor berhenti')['entity']['active'] is False
        assert act(cur,'LAUNDRY_VENDOR',v['id'],'REACTIVATE',reason='Vendor aktif lagi')['entity']['active'] is True
        refused(cur,lambda:create(cur,'LOCATION',dict(code='WIP-'+t,name='WIP CP17',location_type='CUTTING_WIP')),'CP7_MASTER_LOCATION_TYPE')
        loc=create(cur,'LOCATION',dict(code='LOC-'+t,name='Gudang FG CP17',location_type='FG_WAREHOUSE'))
        moved=act(cur,'LOCATION',loc['id'],'UPDATE',dict(code='LOC-'+t,name='Area rusak CP17',location_type='SCRAP_AREA'),'Belum dipakai, jenis dibetulkan')
        assert moved['entity']['location_type']=='SCRAP_AREA'
        b.api.admin(cur);system=cur.execute("select id::text from erp.locations where location_type='CUTTING_WIP' and is_active limit 1").fetchone()
        blockers=None
        if system:
            blockers=[x['kind'] for x in selected(cur,'LOCATION',system[0])['deactivate_blockers']];assert 'SYSTEM_LOCATION' in blockers,blockers
            refused(cur,lambda:act(cur,'LOCATION',system[0],'DEACTIVATE',reason='Coba nonaktif'),'CP7_MASTER_BLOCKED')
        return dict(status='PASS',vendor_deactivated_and_back=True,system_type_create_refused=True,unused_type_change_allowed=True,system_location_blockers=blockers)
    def mandor_policy():
        t=tag();day=today-timedelta(days=20)
        refused(cur,lambda:create(cur,'MANDOR',mandor_fields('MDR-'+t,None)),'CP7_MASTER_POLICY_DATE')
        m=create(cur,'MANDOR',mandor_fields('MDR-'+t,wib(day),attendance_required=True))
        pol=m['entity']['policies'];assert [(x['is_special'],x['attendance_required'],x['effective_from'])for x in pol]==[(False,True,wib(day))],pol
        auth.actor(cur);queue=one(cur,"select public.erp_get_cutting_pickup_queue_v1('ALL',null,%s,100,0)",('MDR-'+t,));b.api.admin(cur)
        assert m['id'] in [x['id'] for x in queue['contractors']],queue['contractors']
        refused(cur,lambda:act(cur,'MANDOR',m['id'],'UPDATE',mandor_fields('MDR-'+t,None,attendance_required=True,is_special=True)),'CP7_MASTER_POLICY_DATE')
        sp=act(cur,'MANDOR',m['id'],'UPDATE',mandor_fields('MDR-'+t,wib(today-timedelta(days=5)),attendance_required=True,is_special=True),'Mandor jadi Special')
        pol=sp['entity']['policies'];assert [(x['is_special'],x['effective_from'],x['effective_to'])for x in pol]==[(False,wib(day),wib(today-timedelta(days=6))),(True,wib(today-timedelta(days=5)),None)],pol
        refused(cur,lambda:act(cur,'MANDOR',m['id'],'UPDATE',mandor_fields('MDR-'+t,wib(today-timedelta(days=5)),attendance_required=True,is_special=False)),'CP7_MASTER_POLICY_SAME_DAY')
        row=[r for r in ws(cur,'MANDOR',dict(q='MDR-'+t))['page']['rows']];assert row and row[0]['is_special'] is True,row
        assert act(cur,'MANDOR',m['id'],'DEACTIVATE',reason='Mandor berhenti')['entity']['active'] is False
        auth.actor(cur);queue=one(cur,"select public.erp_get_cutting_pickup_queue_v1('ALL',null,%s,100,0)",('MDR-'+t,));b.api.admin(cur)
        assert m['id'] not in [x['id'] for x in queue['contractors']]
        return dict(status='PASS',new_mandor_in_bagi_potongan_list=True,special_from_date_with_dated_policy=pol,undated_change_refused=True,inactive_mandor_leaves_list=True)
    def fabric_profile_benchmark():
        t=tag();admin=role_actor(cur,'ADMIN')
        f=create(cur,'FABRIC',fabric_fields('KAIN-'+t),subject=admin)
        refused(cur,lambda:act(cur,'FABRIC',f['id'],'UPDATE',fabric_fields('KAIN-'+t,name='Nama lain')),'CP7_MASTER_USE_RENAME')
        u=act(cur,'FABRIC',f['id'],'UPDATE',fabric_fields('KAIN-'+t,width_cm='152.5',gsm='300',composition='Katun 100%'),'Lebar diukur ulang')
        assert u['entity']['profile']['width_cm']=='152.500' and u['entity']['profile']['composition']=='Katun 100%',u['entity']['profile']
        price=dict(action='SET_BENCHMARK',id=f['id'],review_token=u['review_token'],fields=dict(price='48500',effective_date=wib(today-timedelta(days=3))),reason='Harga acuan bulan ini')
        refused(cur,lambda:save(cur,'FABRIC',price,subject=admin),'CP7_MASTER_DENIED')
        bm=save(cur,'FABRIC',price)
        assert [(x['price'],x['effective_to']) for x in bm['entity']['benchmarks']]==[('48500.000000',None)],bm['entity']['benchmarks']
        refused(cur,lambda:save(cur,'FABRIC',dict(price,review_token=bm['review_token'],fields=dict(price='49000',effective_date=wib(today-timedelta(days=10))))),'CP7_MASTER_BENCHMARK_DATE')
        bm2=save(cur,'FABRIC',dict(price,review_token=bm['review_token'],fields=dict(price='49000',effective_date=wib(today)),reason='Harga acuan naik'))
        assert [x['price'] for x in bm2['entity']['benchmarks']]==['48500.000000','49000.000000'] and bm2['entity']['benchmarks'][0]['effective_to'] is not None
        d=act(cur,'FABRIC',f['id'],'DEACTIVATE',reason='Kain tidak dipakai')
        assert d['entity']['active'] is False and d['entity']['profile']['composition']=='Katun 100%'
        return dict(status='PASS',admin_creates_fabric=True,name_and_code_only_through_rename=True,profile_updated=True,admin_price_refused=True,
                    owner_benchmark_versions=[x['price'] for x in bm2['entity']['benchmarks']],backdated_refused=True,deactivate_keeps_profile=True)
    def accessory_price():
        t=tag();m=create(cur,'MANDOR',mandor_fields('MDR-'+t,wib(today-timedelta(days=30))))
        cat=create(cur,'ACCESSORY_CATEGORY',dict(code='KCG-'+t,name='Kancing CP17',base_uom='pcs',notes=None))
        assert cat['entity']['base_uom']=='PCS'
        var=create(cur,'ACCESSORY',dict(code='kcg-'+t+'-hitam',name='Kancing hitam',category_id=cat['id']))
        assert var['entity']['code']==('KCG-'+t+'-HITAM') and var['entity']['category_id']==cat['id']
        refused(cur,lambda:act(cur,'ACCESSORY_CATEGORY',cat['id'],'DEACTIVATE',reason='Kategori lama'),'ACTIVE_VARIANTS')
        s=selected(cur,'ACCESSORY_CATEGORY',cat['id'])
        g=save(cur,'ACCESSORY_CATEGORY',dict(action='SET_MANDOR_PRICE',id=cat['id'],review_token=s['review_token'],
            fields=dict(contractor_id=None,price='495',uom='PCS',effective_date=wib(today-timedelta(days=10)),notes=None),reason='Harga mandor umum'))
        k=save(cur,'ACCESSORY_CATEGORY',dict(action='SET_MANDOR_PRICE',id=cat['id'],review_token=g['review_token'],
            fields=dict(contractor_id=m['id'],price='5400',uom='LUSIN',effective_date=wib(today-timedelta(days=5)),notes='khusus'),reason='Harga mandor khusus'))
        prices=[(x['contractor_id'],x['price'],x['uom']) for x in k['entity']['prices']]
        assert prices==[(None,'495.0000','PCS'),(m['id'],'5400.0000','LUSIN')],prices
        refused(cur,lambda:save(cur,'ACCESSORY_CATEGORY',dict(action='SET_MANDOR_PRICE',id=cat['id'],review_token=k['review_token'],
            fields=dict(contractor_id=None,price='500',uom='PCS',effective_date=wib(today-timedelta(days=10)),notes=None),reason='Harga ganda')),'CP7_MASTER_PRICE_DATE')
        act(cur,'ACCESSORY',var['id'],'DEACTIVATE',reason='Varian dihentikan')
        assert act(cur,'ACCESSORY_CATEGORY',cat['id'],'DEACTIVATE',reason='Kategori dihentikan')['entity']['active'] is False
        return dict(status='PASS',category_and_variant=True,active_variant_blocks_category=True,mandor_prices=prices,same_start_refused=True)
    def access_rights():
        aud,adm,gud=role_actor(cur,'AUDITOR_VIEW_ONLY'),role_actor(cur,'ADMIN'),role_actor(cur,'GUDANG')
        w=ws(cur,'CUSTOMER',subject=aud);assert w['can_write'] is False and w['can_price'] is False
        refused(cur,lambda:create(cur,'CUSTOMER',customer_fields('CUS-'+tag()),subject=aud),'CP7_MASTER_DENIED')
        refused(cur,lambda:ws(cur,'CUSTOMER',subject=gud),'CP7_MASTER_DENIED')
        refused(cur,lambda:rws(cur,{},subject=gud),'CP7_MASTER_DENIED')
        a=ws(cur,'MANDOR',subject=adm);assert a['can_write'] is True and a['can_price'] is False,a
        c=create(cur,'CUSTOMER',customer_fields('CUS-'+tag()),subject=adm);assert c['entity']['active']
        r=rws(cur,{},subject=adm);assert r['can_write'] is True and r['can_price'] is False
        refused(cur,lambda:rsave(cur,'CREATE_COMPONENT',dict(code='CMP-'+tag(),name='Komponen',category='LABOR',reason='Komponen dari admin'),subject=aud),'CP7_MASTER_DENIED')
        refused(cur,lambda:rsave(cur,'SAVE_BOM',dict(model_id=str(prod().MODEL),items=[],effective_date=wib(today),review_token='0'*32,reason='Admin coba ubah'),subject=adm),'CP7_MASTER_DENIED')
        b.api.admin(cur)
        anon=[r[0] for r in cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('public','cp7_master') and p.proname like any(array['erp_cp7_%%master%%','erp_cp7_%%work_rate%%','save%%','workspace','rate_workspace','save_rate']) and has_function_privilege('anon',p.oid,'EXECUTE')").fetchall()]
        assert anon==[],anon
        return dict(status='PASS',view_only_reads_not_writes=True,no_view_no_read=True,admin_writes_without_price_right=True,anon_executes_nothing=True)
    def rate_versions_and_bom():
        t=tag();b.api.admin(cur);model=str(one(cur,"insert into erp.product_models(model_code,model_name)values(%s,%s)returning id",('MDL-'+t,'Model CP17 '+t)))
        refused(cur,lambda:rsave(cur,'CREATE_COMPONENT',dict(code='bad code',name='x',category='LABOR',reason='Kode tidak sah')),'CP7_WORK_RATE_FIELDS')
        comps,_=model_components(cur,model,today-timedelta(days=30))
        dup=rsave(cur,'CREATE_COMPONENT',dict(code='DUP-'+t,name='Dup',category='OTHER',reason='Komponen dobel'))
        refused(cur,lambda:rsave(cur,'CREATE_COMPONENT',dict(code='dup-'+t.lower(),name='Dup',category='OTHER',reason='Komponen dobel')),'CP7_MASTER_DUPLICATE_CODE')
        w=rws(cur,dict(model_id=model));bom=w['model']['bom']
        assert len(bom)==1 and [i['default_rate'] for i in bom[0]['items']]==['2.00','1.00'],bom
        edited=rsave(cur,'SAVE_BOM',dict(model_id=model,items=[dict(work_component_id=comps[0],sequence_no=1,default_rate='3'),dict(work_component_id=dup['id'],sequence_no=2,default_rate='0')],
            effective_date=wib(today),review_token=w['model']['bom_review_token'],reason='Belum dipakai, komponen diganti'))
        assert len(edited['after'])==1 and [i['code'] for i in edited['after'][0]['items']]==[bom[0]['items'][0]['code'],'DUP-'+t],edited['after']
        m=create(cur,'MANDOR',mandor_fields('MDR-'+t,wib(today-timedelta(days=30))))
        w=rws(cur,dict(contractor_id=m['id'],model_id=model));c=[x for x in w['model']['components'] if x['component_id']==comps[0]][0]
        assert c['current'] is None and c['default_rate']=='3.00'
        base=dict(contractor_id=m['id'],model_id=model,work_component_id=comps[0])
        v1=rsave(cur,'SET_RATE',dict(base,rate='1500',effective_date=wib(today-timedelta(days=10)),review_token=c['review_token'],reason='Tarif awal'))
        v2=rsave(cur,'SET_RATE',dict(base,rate='1600',effective_date=wib(today-timedelta(days=2)),review_token=v1['review_token'],reason='Tarif naik'))
        assert [(x['rate'],x['effective_to'] is None) for x in v2['after']]==[('1500.00',False),('1600.00',True)],v2['after']
        refused(cur,lambda:rsave(cur,'SET_RATE',dict(base,rate='1550',effective_date=wib(today-timedelta(days=5)),review_token=v2['review_token'],reason='Sisip mundur')),'CP7_WORK_RATE_LATER_VERSION')
        refused(cur,lambda:rsave(cur,'SET_RATE',dict(base,rate='1700',effective_date=wib(today),review_token=v1['review_token'],reason='Token lama')),'CP7_WORK_RATE_REVIEW_CHANGED')
        fix=rsave(cur,'SET_RATE',dict(base,rate='1650',effective_date=wib(today-timedelta(days=2)),review_token=v2['review_token'],reason='Salah ketik, belum dipakai'))
        assert [x['rate'] for x in fix['after']]==['1500.00','1650.00']
        stop=rsave(cur,'STOP_RATE',dict(base,effective_date=wib(today+timedelta(days=1)),review_token=fix['review_token'],reason='Mandor berhenti model ini'))
        assert stop['after'][-1]['effective_to'] is not None
        refused(cur,lambda:rsave(cur,'SET_RATE',dict(base,rate='1',effective_date=wib(today),review_token=stop['review_token'],reason='Komponen luar')|dict(work_component_id=str(uuid.uuid4()))),'CP7_WORK_RATE_NOT_FOUND')
        return dict(status='PASS',component_codes_unique=True,first_bom_then_in_place_edit=True,dated_versions=[x['rate'] for x in fix['after']],
                    later_version_and_stale_review_refused=True,unused_version_corrected_in_place=True,stop_closes_open_version=True)
    def fable_chain():
        g=cutting_only(cur,today);day=g['day']
        m=create(cur,'MANDOR',mandor_fields('MDR-'+tag(),wib(day-timedelta(days=30))),'Mandor baru dari layar master')
        comps,made=model_components(cur,g['model'],day-timedelta(days=1))
        w=rws(cur,dict(contractor_id=m['id'],model_id=g['model']))
        rates={comps[0]:'1500'}|{x:'500' for x in comps[1:]}
        for c in w['model']['components']:
            if c['component_id'] in rates:
                rsave(cur,'SET_RATE',dict(contractor_id=m['id'],model_id=g['model'],work_component_id=c['component_id'],rate=rates[c['component_id']],
                    effective_date=wib(day),review_token=c['review_token'],reason='Tarif mandor baru'))
        first=[c for c in rws(cur,dict(contractor_id=m['id'],model_id=g['model']))['model']['components'] if c['component_id']==comps[0]][0]
        later=rsave(cur,'SET_RATE',dict(contractor_id=m['id'],model_id=g['model'],work_component_id=comps[0],rate='1700',effective_date=wib(day+timedelta(days=1)),
            review_token=first['review_token'],reason='Tarif naik besok'))
        cp17.native_pickup(cur,g['group'],m['id'],g['at'](9))
        assert one(cur,'select contractor_id::text from erp.production_orders where id=%s',(g['po'],))==m['id']
        sw=cp17.sewing_workspace(cur,g);per=sum(D(v) for v in rates.values());expected=per*10
        # The screen previews the rates of the sewing time it sends (rate_timeline), not today's (rate_preview has the later 1700).
        sewn_at=g['at'](10);seg=[t for t in sw['rate_timeline'] if datetime.fromisoformat(t['from'])<=sewn_at and(t['to'] is None or sewn_at<datetime.fromisoformat(t['to']))]
        assert len(seg)==1 and seg[0]['complete'] and sum(D(str(x['rate'])) for x in seg[0]['rates'])==per,(sw['rate_timeline'],per)
        assert sum(D(str(x['rate'])) for x in sw['rate_preview'])==per+200,sw['rate_preview']
        cp17.sewing_command(cur,sw,qty=10,at=sewn_at,reason='Setoran jahit mandor baru')
        wage=wage_of(cur,g['group']);assert (D(wage[0]),D(wage[1]),wage[2])==(expected,expected,1),(wage,expected)
        b.api.admin(cur)
        snap=cur.execute('select work_component_id::text,rate_per_pcs_snapshot from erp.po_work_component_snapshots where po_id=%s and bf_sku_version_id is null order by sequence_no',(g['po'],)).fetchall()
        assert {k:D(v) for k,v in snap}=={k:D(v) for k,v in rates.items()},snap
        ver=rws(cur,dict(contractor_id=m['id'],model_id=g['model']));c0=[c for c in ver['model']['components'] if c['component_id']==comps[0]][0]
        refused(cur,lambda:rsave(cur,'SET_RATE',dict(contractor_id=m['id'],model_id=g['model'],work_component_id=comps[0],rate='1800',effective_date=wib(day),
            review_token=c0['review_token'],reason='Ubah tarif yang sudah dipakai')),'CP7_WORK_RATE_USED')
        refused(cur,lambda:rsave(cur,'STOP_RATE',dict(contractor_id=m['id'],model_id=g['model'],work_component_id=comps[0],effective_date=wib(day),
            review_token=c0['review_token'],reason='Hentikan mundur')),'CP7_WORK_RATE')
        rsave(cur,'SET_RATE',dict(contractor_id=m['id'],model_id=g['model'],work_component_id=comps[0],rate='1800',effective_date=wib(day+timedelta(days=1)),
            review_token=c0['review_token'],reason='Tarif besok dibetulkan'))
        after=wage_of(cur,g['group']);assert after==wage,(after,wage)
        return dict(status='PASS',mandor_from_master_screen=m['entity']['code'],rates_from_rate_screen=rates,bom_written_by_rate_screen=made,
                    pickup_with_new_mandor=True,screen_preview_at_sewing_time=str(per),today_rate_not_used=str(per+200),wage_at_sewing_date=str(expected),later_rate_versions=[x['rate'] for x in later['after']],
                    used_version_change_refused=True,later_change_keeps_recorded_wage=True)
    named=[customer_lifecycle,customer_used_in_sales,supplier_location_fabric_in_receipt,vendor_and_location_rules,mandor_policy,fabric_profile_benchmark,
           accessory_price,access_rights,rate_versions_and_bom,fable_chain]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):
    def two(fn,payloads):
        barrier=threading.Barrier(len(payloads))
        def send(p):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=fn(cur,p);conn.commit();return('PASS',r)
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=len(payloads))as pool:return [x.result(30) for x in [pool.submit(send,p) for p in payloads]]
    def one_wins(results,code):
        assert sorted(x[0] for x in results)==['PASS','REFUSED'] and code in next(x[1] for x in results if x[0]=='REFUSED'),results
        return next(x[1] for x in results if x[0]=='PASS')
    def setup(fn):
        with tools.connect()as conn,conn.cursor()as cur:out=fn(cur);conn.commit();return out
    def updates(kind,id,token,fields_list,reason):
        return [dict(action='UPDATE',id=id,review_token=token,fields=f,reason=reason) for f in fields_list]
    def same_record():
        code='CUS-'+tag()
        c,token=setup(lambda cur:(lambda c:(c,selected(cur,'CUSTOMER',c['id'])['review_token']))(create(cur,'CUSTOMER',customer_fields(code))))
        won=one_wins(two(lambda cur,p:save(cur,'CUSTOMER',p),updates('CUSTOMER',c['id'],token,[customer_fields(code,n) for n in ('Toko Tab Satu','Toko Tab Dua')],'Dua tab ubah nama')),
            'CP7_MASTER_REVIEW_CHANGED')['entity']['name']
        with tools.connect()as conn,conn.cursor()as cur:
            assert one(cur,'select customer_name from erp.customers where id=%s',(c['id'],))==won
            assert one(cur,"select count(*) from cp7_master.history where entity_id=%s and action='UPDATE'",(c['id'],))==1
        return dict(status='PASS',screen='Pelanggan',one_update_wins=won,other_refused_stale_review=True,history_one_update=True)
    def same_code():
        code='SUP-'+tag()
        ps=[dict(action='CREATE',fields=dict(code=code,name='Supplier tab '+n,supplier_type='MATERIAL',phone=None,address=None),reason='Dua tab supplier baru') for n in ('satu','dua')]
        one_wins(two(lambda cur,p:save(cur,'SUPPLIER',p),ps),'CP7_MASTER_DUPLICATE_CODE')
        with tools.connect()as conn,conn.cursor()as cur:assert one(cur,'select count(*) from erp.suppliers where lower(supplier_code)=lower(%s)',(code,))==1
        return dict(status='PASS',screen='Supplier & Vendor',one_supplier_per_code=True,other_refused_duplicate=True)
    def mandor_policy():
        code='MDR-'+tag();start=today-timedelta(days=30)
        m,token=setup(lambda cur:(lambda m:(m,m['review_token']))(create(cur,'MANDOR',mandor_fields(code,wib(start)))))
        days=[today-timedelta(days=5),today-timedelta(days=3)]
        won=one_wins(two(lambda cur,p:save(cur,'MANDOR',p),updates('MANDOR',m['id'],token,[mandor_fields(code,wib(d),is_special=True) for d in days],'Dua tab Mandor jadi Special')),
            'CP7_MASTER_REVIEW_CHANGED')
        with tools.connect()as conn,conn.cursor()as cur:
            pol=cur.execute('select is_special,effective_from from erp.contractor_hpp_policy_versions where contractor_id=%s order by effective_from',(m['id'],)).fetchall()
            assert [x[0] for x in pol]==[False,True] and len(pol)==2,pol
        return dict(status='PASS',screen='Mandor',one_policy_change_wins=won['entity']['policies'][-1]['effective_from'],other_refused_stale_review=True,policies=len(pol))
    def rate_two_tabs():
        def make(cur):
            t=tag();b.api.admin(cur);model=str(one(cur,"insert into erp.product_models(model_code,model_name)values(%s,%s)returning id",('MDL-'+t,'Model race '+t)))
            comps,_=model_components(cur,model,today-timedelta(days=30));m=create(cur,'MANDOR',mandor_fields('MDR-'+t,wib(today-timedelta(days=30))))
            return model,comps,m,[x for x in rws(cur,dict(contractor_id=m['id'],model_id=model))['model']['components'] if x['component_id']==comps[0]][0]
        model,comps,m,c=setup(make)
        ps=[dict(contractor_id=m['id'],model_id=model,work_component_id=comps[0],rate=r,effective_date=wib(today),review_token=c['review_token'],reason='Dua tab tarif') for r in ('1500','1600')]
        won=one_wins(two(lambda cur,p:rsave(cur,'SET_RATE',p),ps),'CP7_WORK_RATE_REVIEW_CHANGED')
        with tools.connect()as conn,conn.cursor()as cur:
            n=one(cur,'select count(*) from erp.contractor_work_rates where contractor_id=%s and model_id=%s and work_component_id=%s',(m['id'],model,comps[0]));assert n==1,n
        return dict(status='PASS',screen='Mandor · Tarif upah mandor',one_rate_version=won['after'][-1]['rate'],other_refused_stale_review=True)
    def location_two_tabs():
        code='LOC-'+tag()
        loc=setup(lambda cur:create(cur,'LOCATION',dict(code=code,name='Gudang race',location_type='FG_WAREHOUSE')))
        ps=[dict(action='DEACTIVATE',id=loc['id'],review_token=loc['review_token'],reason='Tab satu menutup gudang'),
            dict(action='UPDATE',id=loc['id'],review_token=loc['review_token'],fields=dict(code=code,name='Gudang race baru',location_type='FG_WAREHOUSE'),reason='Tab dua ganti nama')]
        won=one_wins(two(lambda cur,p:save(cur,'LOCATION',p),ps),'CP7_MASTER_REVIEW_CHANGED')
        with tools.connect()as conn,conn.cursor()as cur:
            row=cur.execute('select is_active,location_name from erp.locations where id=%s',(loc['id'],)).fetchone()
            assert row==((won['action']!='DEACTIVATE'),won['entity']['name']),(row,won['action'])
            assert one(cur,"select count(*) from cp7_master.history where entity_id=%s and action<>'CREATE'",(loc['id'],))==1
        return dict(status='PASS',screen='Gudang & Lokasi',winner=won['action'],other_refused_stale_review=True,history_one_change=True)
    def benchmark_two_tabs():
        f=setup(lambda cur:create(cur,'FABRIC',fabric_fields('KAIN-'+tag())))
        ps=[dict(action='SET_BENCHMARK',id=f['id'],review_token=f['review_token'],fields=dict(price=pr,effective_date=wib(today)),reason='Dua tab harga acuan') for pr in ('48500','49000')]
        won=one_wins(two(lambda cur,p:save(cur,'FABRIC',p),ps),'CP7_MASTER_REVIEW_CHANGED')
        with tools.connect()as conn,conn.cursor()as cur:
            rows=cur.execute('select benchmark_price_per_base_uom::text from erp.fabric_benchmark_price_versions where material_id=%s',(f['id'],)).fetchall()
            assert [D(r[0]) for r in rows]==[D(won['entity']['benchmarks'][-1]['price'])],rows
        return dict(status='PASS',screen='Kain & Benchmark',one_benchmark_version=won['entity']['benchmarks'][-1]['price'],other_refused_stale_review=True)
    def accessory_same_code():
        t=tag();cat=setup(lambda cur:create(cur,'ACCESSORY_CATEGORY',dict(code='KCG-'+t,name='Kancing race',base_uom='PCS',notes=None)))
        ps=[dict(action='CREATE',fields=dict(code='KCG-'+t+'-PUTIH',name='Kancing putih '+n,category_id=cat['id']),reason='Dua tab varian baru') for n in ('satu','dua')]
        one_wins(two(lambda cur,p:save(cur,'ACCESSORY',p),ps),'CP7_MASTER_DUPLICATE_CODE')
        with tools.connect()as conn,conn.cursor()as cur:assert one(cur,'select count(*) from erp.materials where lower(material_sku)=lower(%s)',('KCG-'+t+'-PUTIH',))==1
        return dict(status='PASS',screen='Aksesori & Harga Mandor',one_variant_per_code=True,other_refused_duplicate=True)
    named=[same_record,same_code,mandor_policy,rate_two_tabs,location_two_tabs,benchmark_two_tabs,accessory_same_code]
    assert len(named)==len(RACES)
    return list(zip(RACES,named))


def http_cases(http,today):
    def master():
        owner=http.login('OWNER','cp17-master');admin=http.login('ADMIN','cp17-master-admin')
        code='CUS-'+tag()
        w=owner.rpc('erp_cp7_get_master_v1',dict(p_kind='CUSTOMER',p_query={}));assert w['status']==200 and w['body']['can_write'] is True,w
        key=str(uuid.uuid4());p=dict(action='CREATE',fields=customer_fields(code,'Toko HTTP'),reason='Pelanggan baru lewat login')
        c=owner.rpc('erp_cp7_save_master_v1',dict(p_kind='CUSTOMER',p_payload=p,p_request=key));assert c['status']==200,c
        again=owner.rpc('erp_cp7_save_master_v1',dict(p_kind='CUSTOMER',p_payload=p,p_request=key));assert again['status']==200 and again['body']==c['body'],again
        s=owner.rpc('erp_cp7_get_master_v1',dict(p_kind='CUSTOMER',p_query=dict(id=c['body']['id'])))['body']['selected']
        u=owner.rpc('erp_cp7_save_master_v1',dict(p_kind='CUSTOMER',p_request=str(uuid.uuid4()),p_payload=dict(action='UPDATE',id=c['body']['id'],review_token=s['review_token'],
            fields=customer_fields(code,'Toko HTTP Jaya'),reason='Nama dibetulkan lewat login')));assert u['status']==200 and u['body']['entity']['name']=='Toko HTTP Jaya',u
        stale=owner.rpc('erp_cp7_save_master_v1',dict(p_kind='CUSTOMER',p_request=str(uuid.uuid4()),p_payload=dict(action='UPDATE',id=c['body']['id'],review_token=s['review_token'],
            fields=customer_fields(code,'Toko HTTP Lagi'),reason='Token lama lewat login')));assert stale['status']==400 and 'CP7_MASTER_REVIEW_CHANGED' in str(stale['body']),stale
        f=admin.rpc('erp_cp7_save_master_v1',dict(p_kind='FABRIC',p_request=str(uuid.uuid4()),p_payload=dict(action='CREATE',fields=fabric_fields('KAIN-'+tag()),reason='Kain baru dari admin')))
        assert f['status']==200,f
        bm=admin.rpc('erp_cp7_save_master_v1',dict(p_kind='FABRIC',p_request=str(uuid.uuid4()),p_payload=dict(action='SET_BENCHMARK',id=f['body']['id'],review_token=f['body']['review_token'],
            fields=dict(price='48500',effective_date=wib(today)),reason='Admin coba harga')))
        assert bm['status'] in (401,403) and 'CP7_MASTER_DENIED' in str(bm['body']),bm
        return dict(status='PASS',real_Auth_create_replay_update=True,stale_review_400=True,admin_creates_fabric_but_price_refused=bm['status'])
    def work_rate():
        owner=http.login('OWNER','cp17-rate')
        with http.connect()as conn,conn.cursor()as cur:
            t=tag();model=str(one(cur,"insert into erp.product_models(model_code,model_name)values(%s,%s)returning id",('MDL-'+t,'Model HTTP '+t)));conn.commit()
        mc=owner.rpc('erp_cp7_save_master_v1',dict(p_kind='MANDOR',p_request=str(uuid.uuid4()),p_payload=dict(action='CREATE',fields=mandor_fields('MDR-'+t,wib(today-timedelta(days=30))),reason='Mandor baru lewat login')))
        assert mc['status']==200,mc
        comp=owner.rpc('erp_cp7_save_work_rate_v1',dict(p_action='CREATE_COMPONENT',p_request=str(uuid.uuid4()),p_payload=dict(code='JHT-'+t,name='Jahit HTTP',category='LABOR',reason='Komponen lewat login')))
        assert comp['status']==200,comp
        w=owner.rpc('erp_cp7_get_work_rates_v1',dict(p_query=dict(model_id=model)))['body']
        bom=owner.rpc('erp_cp7_save_work_rate_v1',dict(p_action='SAVE_BOM',p_request=str(uuid.uuid4()),p_payload=dict(model_id=model,items=[dict(work_component_id=comp['body']['id'],sequence_no=1,default_rate='2')],
            effective_date=wib(today-timedelta(days=10)),review_token=w['model']['bom_review_token'],reason='Komponen model lewat login')));assert bom['status']==200,bom
        w=owner.rpc('erp_cp7_get_work_rates_v1',dict(p_query=dict(model_id=model,contractor_id=mc['body']['id'])))['body'];c=w['model']['components'][0]
        key=str(uuid.uuid4());p=dict(contractor_id=mc['body']['id'],model_id=model,work_component_id=c['component_id'],rate='1500',effective_date=wib(today),review_token=c['review_token'],reason='Tarif lewat login')
        r=owner.rpc('erp_cp7_save_work_rate_v1',dict(p_action='SET_RATE',p_payload=p,p_request=key));assert r['status']==200,r
        again=owner.rpc('erp_cp7_save_work_rate_v1',dict(p_action='SET_RATE',p_payload=p,p_request=key));assert again['status']==200 and again['body']==r['body'],again
        changed=owner.rpc('erp_cp7_save_work_rate_v1',dict(p_action='SET_RATE',p_payload=dict(p,rate='1600'),p_request=key))
        assert changed['status']==400 and 'CP7_MASTER_REQUEST_CHANGED' in str(changed['body']),changed
        with http.connect()as conn,conn.cursor()as cur:
            assert one(cur,'select count(*) from erp.contractor_work_rates where contractor_id=%s and model_id=%s',(mc['body']['id'],model))==1
        return dict(status='PASS',real_Auth_mandor_component_bom_rate=True,same_request_same_answer=True,changed_request_refused=True)
    return list(zip(HTTP,[master,work_rate]))
