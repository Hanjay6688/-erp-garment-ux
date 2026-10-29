"""Native prerequisites and complete readback on the browser host's local copy.

The UI creates every pair/conversion/inverse in the journey. Masters, opening
stock and sale draft dependencies are explicit Native setup, not screen proof.
No posted stock, cost, journal or conversion row is inserted by this module.
"""
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import importlib.util,json,os,re,sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
# Imported recovery entrypoints own an empty CLI contract. Preserve our real
# command separately, as in the bounded return browser fixture.
_arguments=sys.argv
try:
    sys.argv=sys.argv[:1]
    import cp7_p21_current_chain_rehearsal_probe
    import psycopg
    from cp7_sku_pair_conversion import composition as product
    spec=importlib.util.spec_from_file_location('sku29_browser_native_fixture',ROOT/'scripts/current-sku-pair-conversion-qualification/fixture.py')
    f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
finally:sys.argv=_arguments

def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def census(cur,label):
    assert re.fullmatch(r'SKU29_(DESKTOP|MOBILE390)_[A-Z0-9_]+',label),'SKU29_EVIDENCE_LABEL_REQUIRED'
    f.admin(cur);_,_,_,_,catalog=product.runtime()
    rows=catalog._catalog_rows(cur);data=catalog._data(cur)
    assert len(rows)==22 and all(table in data for table in product.TABLES),'SKU29_FULL_CURRENT_CENSUS_REQUIRED'
    raw=dict(catalog_rows=rows,data_and_sequences=data)
    blob=(json.dumps(raw,indent=2,sort_keys=True,default=str)+'\n').encode()
    output=Path('cp6-proof/t3')/(label+'_FULL_CURRENT_STATE.json');output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(blob)
    return dict(catalog_groups=len(rows),catalog_sha256=digest(rows),data_and_sequences=data,
      raw_evidence=dict(path=str(output),bytes=len(blob),sha256=sha256(blob).hexdigest()),
      dropped_catalog_fields=[],dropped_data_or_sequence_keys=[])

def observe(cur,fixture,label):
    f.admin(cur)
    groups=cur.execute("select request_id::text,payload from cp7_sku_conversion.groups_v1 where payload->>'source_product_id'=%s order by request_id",(fixture['source'],)).fetchall()
    members=[]
    for ident,payload in groups:
        rows=cur.execute("""select m.conversion_id::text,a.source_lot_id::text,a.destination_lot_id::text,
          a.qty_pcs,a.original_hpp_per_pcs::text,h.total_cost::text,c.status,c.conversion_number
          from cp7_sku_conversion.members_v1 m join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id
          join erp.product_conversions c on c.id=m.conversion_id
          left join erp.hpp_versions h on h.lot_id=a.destination_lot_id and h.is_current
          where m.group_id=%s order by m.line_no""",(ident,)).fetchall()
        members.extend(dict(zip(('conversion_id','source_lot_id','destination_lot_id','qty_pcs','unit_hpp','destination_value','status','number'),row),group_id=ident)for row in rows)
    endpoint_ids=[group['id']for group in fixture['groups']]
    pairs=cur.execute('select left_id::text,right_id::text from cp7_sku_conversion.pairs_v1 where left_id=any(%s::uuid[])or right_id=any(%s::uuid[])order by left_id,right_id',(endpoint_ids,endpoint_ids)).fetchall()
    event_count=f.one(cur,'select count(*)from cp7_sku_conversion.pair_events_v1 where source_id=any(%s::uuid[])',endpoint_ids)
    return dict(census=census(cur,label),ledgers=f.native_ledgers(cur),accounts=f.books(cur),
      source=f.stocks(cur,fixture['source'],fixture['location']),target=f.stocks(cur,fixture['target'],fixture['location']),
      pairs=pairs,pair_event_count=event_count,groups=[dict(id=ident,payload=payload)for ident,payload in groups],members=members,
      Native_nonPO_books={p:f.product_books(cur,p)for p in(fixture['source'],fixture['target'])})

def main():
    if sys.argv[1:]==['--check-import']:
        return dict(status='SKU29_BROWSER_FIXTURE_IMPORT_ADMITTED',arguments_preserved=True,no_database_opened=True)
    assert len(sys.argv)==2,'SKU29_FIXTURE_OPERATION_REQUIRED'
    operation=sys.argv[1];args=json.load(sys.stdin)
    url=os.environ['AUDITOR_BROWSER_DB_URL'];parsed=urlparse(url)
    assert parsed.hostname in('127.0.0.1','localhost')and parsed.port==54322 and parsed.path=='/cp6_auditor_browser','SKU29_BROWSER_COPY_ONLY'
    with psycopg.connect(url,connect_timeout=10)as conn,conn.cursor()as cur:
        assert cur.execute('select current_database()').fetchone()==('cp6_auditor_browser',)
        cur.execute("set local statement_timeout='90s';set local lock_timeout='8s'")
        f.admin(cur)
        if operation=='prepare':
            fixture=f.nonpo(cur,date.fromisoformat(args['today']))
            fixture['physical_local']=datetime.fromisoformat(fixture['at']).astimezone(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%dT%H:%M')
            fixture['physical_iso']=datetime.fromisoformat(fixture['physical_local']).replace(tzinfo=ZoneInfo('Asia/Jakarta')).isoformat()
            fixture['products']={}
            for name in('source','target','other'):
                row=cur.execute('select p.sku,p.product_name,b.brand_name,z.size_code,p.model_id::text,p.size_id::text from erp.products p join erp.brands b on b.id=p.brand_id join erp.sizes z on z.id=p.size_id where p.id=%s',(fixture[name],)).fetchone()
                fixture['products'][name]=dict(zip(('sku','name','brand','size','model_id','size_id'),row))
            fixture['group_labels']={group['id']:f.one(cur,'select cp7_sku_conversion.group_v1(%s)',group['id'])for group in fixture['groups']}
            assert fixture['products']['source']['model_id']!=fixture['products']['target']['model_id']
            assert fixture['products']['source']['size_id']!=fixture['products']['target']['size_id']
            fixture['preparation']='SYNTHETIC_MASTERS_DRAFT_OPENING_NATIVE_POST_NATIVE_SALE_RESERVATION_NOT_SCREEN_CREATION'
            fixture['baseline_accounts']=f.books(cur)
            conn.commit();return fixture
        fixture=args['fixture']
        if operation=='observe':
            value=observe(cur,fixture,args['label']);conn.rollback();return value
        if operation=='block_inverse':
            # This active real draft reserves the four old target pieces plus
            # one new conversion result. No posted lot is edited for the test.
            at=(f.one(cur,'select clock_timestamp()')-timedelta(seconds=1)).isoformat()
            sale=f.reserve(cur,fixture,fixture['target'],5,at=at)
            lots=cur.execute("select distinct m.lot_id::text from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id where i.sale_id=%s and m.movement_type='SALE_RESERVE'",(sale,)).fetchall()
            converted=cur.execute("select a.destination_lot_id::text from cp7_sku_conversion.groups_v1 g join cp7_sku_conversion.members_v1 m on m.group_id=g.request_id join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id where g.payload->>'source_product_id'=%s",(fixture['source'],)).fetchall()
            used=sorted({r[0]for r in lots}&{r[0]for r in converted});assert used,'SKU29_REAL_NEW_RESULT_USE_REQUIRED'
            conn.commit();return dict(sale_id=sale,used_conversion_lots=used,method='NATIVE_SALE_DRAFT_FIXTURE_NOT_BROWSER_CREATION')
        if operation=='release_inverse':
            f.cancel_reservation(cur,args['sale_id']);conn.commit();return dict(status='NATIVE_SALE_DRAFT_CANCELLED',browser_creation_claim=False)
        raise ValueError('SKU29_UNKNOWN_BROWSER_FIXTURE_OPERATION')

if __name__=='__main__':print(json.dumps(main(),default=str))
