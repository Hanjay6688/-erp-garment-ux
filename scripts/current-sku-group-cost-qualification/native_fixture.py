"""Native calls and unprojected census; no authoritative row is seeded here."""
from datetime import datetime,timedelta
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
import importlib.util,json,re,uuid
import psycopg
from cp7_sku_pair_conversion import composition as product

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('sku_cost_existing_Native_fixture',ROOT/'scripts/current-sku-pair-conversion-qualification/fixture.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
bc=f.b.bcp
KEYS=('MATERIAL_INVENTORY','FG_INVENTORY','COGS','WIP','OTHER_INCOME','OTHER_EXPENSE')

def require_local(cur):
    info=cur.connection.info
    assert info.host in('localhost','127.0.0.1')and info.port==54322,'SKU_COST_LOCAL_NATIVE_ONLY'
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',),'SKU_COST_NATIVE_CLONE_ONLY'

def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def books(cur):f.admin(cur);return {key:f.b.gl(cur,key)for key in KEYS}
def at(fixture,seconds):return(datetime.fromisoformat(fixture['at'])+timedelta(seconds=seconds)).isoformat()

def capture(cur):
    f.admin(cur);_,_,_,_,catalog=product.runtime()
    snapshot=dict(catalog=catalog._catalog_rows(cur),data_and_sequences=catalog._data(cur))
    assert len(snapshot['catalog'])==22 and all(table in snapshot['data_and_sequences']for table in product.TABLES),'SKU_COST_FULL_CURRENT_CENSUS_REQUIRED'
    return snapshot

def unchanged(cur,before,label):
    assert re.fullmatch('[A-Z0-9_]+',label)
    after=capture(cur);prefix='SKU_COST_'+label+'_'+uuid.uuid4().hex[:12]
    path=Path('cp6-proof/t3')/(prefix+'_FULL_CURRENT_CENSUS.json');path.parent.mkdir(parents=True,exist_ok=True)
    blob=(json.dumps(dict(before=before,after=after),indent=2,sort_keys=True,default=str)+'\n').encode();path.write_bytes(blob)
    if after!=before:
        catalog_changes=[key for key in before['catalog']if before['catalog'][key]!=after['catalog'].get(key)]
        data_changes=[key for key in set(before['data_and_sequences'])|set(after['data_and_sequences'])if before['data_and_sequences'].get(key)!=after['data_and_sequences'].get(key)]
        raise AssertionError(dict(error='SKU_COST_CURRENT_CENSUS_CHANGED',label=label,catalog_groups=catalog_changes,data_or_sequences=sorted(data_changes),raw=str(path)))
    return dict(all22_and_all_current_rows_sequences_unchanged=True,raw_path=str(path),bytes=len(blob),sha256=sha256(blob).hexdigest(),
      before_sha256=digest(before),after_sha256=digest(after),dropped_fields=[])

def refused(cur,call,code):
    f.admin(cur);cur.execute('savepoint sku_cost_refusal')
    try:call()
    except psycopg.Error as error:
        result=dict(sqlstate=error.sqlstate,message=error.diag.message_primary)
        cur.execute('rollback to savepoint sku_cost_refusal');cur.execute('release savepoint sku_cost_refusal');f.admin(cur)
        assert result['sqlstate']=='P0001'and code in(result['message']or''),(code,result)
        return result
    cur.execute('rollback to savepoint sku_cost_refusal');cur.execute('release savepoint sku_cost_refusal');f.admin(cur)
    raise AssertionError('SKU_COST_EXPECTED_NATIVE_REFUSAL:'+code)

def material(cur,today,cost='2.00',recovery=False):
    acc=bc.fixture(cur,today,stock_qty=100,cost=cost)
    bc.policy(cur,'ACC_DEC04',dict(OWN_FG_REPAIR_account_id=bc.account(cur,'5100')))
    bc.policy(cur,'ACC_DEC07',dict(approval='NONE'))
    if recovery:bc.policy(cur,'ACC_DEC03',dict(credit_account_id=bc.account(cur,'4100'),unit_value_cap='MOVING_AVERAGE'))
    f.admin(cur);return acc

def make_group(cur,fixture,expected_returns=None):
    payload=dict(fixture['payload'])
    if expected_returns is not None:payload['expected_returns']=expected_returns
    payload,preview=f.review(cur,payload);made=f.action(cur,'POST',payload)
    parts=f.allocations(cur,made)
    assert [(part['source_lot_id'],part['qty_pcs'],D(part['unit_hpp']),D(part['destination_value']))for part in parts]==[
      (fixture['lots'][0],2,D('10.01'),D('20.02')),(fixture['lots'][1],2,D('20.02'),D('40.04'))],parts
    return made,parts

def values(cur,parts):return tuple(f.b.lot_value(cur,part['destination_lot_id'])for part in parts)
def statuses(cur,parts):
    f.admin(cur);return [cur.execute('select status from erp.product_conversions where id=%s',(part['conversion_id'],)).fetchone()[0]for part in parts]

def usage(cur,fixture,acc,part,qty):
    ident=part['conversion_id'];revision=f.one(cur,'select erp.be_conversion_revision_v1(%s)',ident)
    payload=dict(conversion_id=ident,expected_version=revision,location_id=acc['main'],
      physical_at=at(fixture,1),items=[dict(material_id=acc['material'],qty=str(qty))],reason='SKU cost actual sourced accessory usage')
    key=str(uuid.uuid4());return f.action(cur,'POST_USAGE',payload,key),payload,key

def immutable(cur,conversion_ids,sale=None):
    f.admin(cur)
    def rows(table,column,ids):
        return cur.execute('select coalesce(jsonb_agg(to_jsonb(r)order by r.id),\'[]\'::jsonb)from erp.'+table+' r where '+column+'=any(%s::uuid[])',(ids,)).fetchone()[0]
    # Complete raw facts; no field is removed to make a recost compare equal.
    return dict(conversions=rows('product_conversions','r.id',conversion_ids),
      allocations=rows('product_conversion_allocations','r.conversion_id',conversion_ids),
      source_links=cur.execute('select coalesce(jsonb_agg(to_jsonb(r)order by r.conversion_id),\'[]\'::jsonb)from erp.be_conversion_sources_v1 r where conversion_id=any(%s::uuid[])',(conversion_ids,)).fetchone()[0],
      sales=[]if sale is None else cur.execute('select coalesce(jsonb_agg(to_jsonb(a)order by a.id),\'[]\'::jsonb)from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s',(sale,)).fetchone()[0])

def source_hpp(cur,fixture):
    f.admin(cur)
    return cur.execute('select coalesce(jsonb_agg(to_jsonb(h)order by h.id),\'[]\'::jsonb)from erp.hpp_versions h where lot_id=any(%s::uuid[])',(fixture['lots'],)).fetchone()[0]

def clone_same_dimensions(cur,source):
    f.admin(cur);ident=str(uuid.uuid4());tag=uuid.uuid4().hex[:10]
    # Synthetic master identity is chosen at INSERT, never patched after use.
    cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active,is_portal_visible)
      select %s,%s,model_id,brand_id,%s,size_id,'SKU cost Native downstream',%s,effective_from,true,true from erp.products where id=%s""",
      (ident,'S29C-'+tag,'S29C-'+tag,ident,source));assert cur.rowcount==1
    cur.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes)values(%s,'S29C-EMPTY','2026-01-01',true,'Explicit empty synthetic BOM')",(ident,))
    return ident

def descendant(cur,fixture,part,target):
    payload=dict(source_lot_id=part['destination_lot_id'],target_product_id=target,location_id=fixture['location'],qty_pcs=1,
      physical_at=at(fixture,15),reason='SKU cost one real downstream conversion',
      expected_version=f.one(cur,'select erp.be_source_revision_v1(%s,%s)',part['destination_lot_id'],fixture['location']))
    return f.action(cur,'POST',payload)

def sale(cur,fixture,qty):
    ident=f.reserve(cur,fixture,fixture['target'],qty,at=at(fixture,30))
    revision=f.one(cur,'select row_version from erp.sales_headers where id=%s',ident)
    f.b.internal(cur,'post_sale_v2',ident,str(uuid.uuid4()),revision);f.admin(cur);return ident

def invoice(cur,acc,today):
    payload=dict(invoice_number='S29C-INVOICE-'+uuid.uuid4().hex,supplier_id=acc['supplier'],invoice_date=str(today),
      change_reason='SKU cost material price2 to3',lines=[dict(purchase_item_id=acc['item'],qty_invoiced='100',unit_price='3.00')])
    draft=f.b.internal(cur,'save_material_supplier_invoice_draft_v2',json.dumps(payload),str(uuid.uuid4()),None)
    key=str(uuid.uuid4());args=(draft['supplier_invoice_id'],key,draft['row_version'],'SKU cost actual late supplier invoice')
    result=f.b.internal(cur,'post_material_supplier_invoice_v2',*args);f.admin(cur)
    return result,args

def reverse_invoice(cur,invoice):
    return f.b.internal(cur,'reverse_material_supplier_invoice_v2',invoice['supplier_invoice_id'],'SKU cost legitimate invoice inverse',str(uuid.uuid4()),invoice['row_version'])
