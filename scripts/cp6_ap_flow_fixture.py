"""Disposable committed fixtures and read-only independent data observations.

Setup calls are native administrative fixture preparation, not HTTP evidence.
No persistent grant, function, trigger or policy change is permitted.
"""
from pathlib import Path
from datetime import timedelta
import hashlib,json,os,re,sys,uuid
import psycopg
from psycopg import sql
import cp6_ao_ap_installed as a
import cp6_ao_ap_runtime as runtime
from cp6_ao_ap_inventory import data
import cp6_initial_import_receipt_trial as receipts
import cp6_pocket_fabric_trial as pocket
import cp6_foundation_qualification as foundation

PG='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
ADMIN=PG.replace('postgres:postgres@','supabase_admin:postgres@')
OUT=Path('cp6-proof/ap-flow')

# Known synthetic master keys resolve identities from the verified disposable DB.
# The saved FIXTURE.json is evidence only, never input to HTTP commands.
IDENTITIES_SQL="""select jsonb_build_object(
 'today',(statement_timestamp() at time zone 'Asia/Jakarta')::date::text,
 'day',((statement_timestamp() at time zone 'Asia/Jakarta')::date-1)::text,
 'period_start','2026-09-01','schema_acl_unchanged',true,
 'accessory',(select jsonb_build_object('material',m.id,'contractor',p.contractor_id,'location',l.id,'price',v.id)
  from erp.materials m cross join erp.locations l cross join erp.production_orders p
  join erp.contractor_accessory_price_versions v on v.contractor_id=p.contractor_id
  where m.material_sku='CP6-AP-FLOW-ACC' and l.location_code='CP6-AP-FLOW-ACC'
   and p.po_number='CP6-RACE-PO' and v.category_id=m.accessory_category_id),
 'pocket',(select jsonb_build_object('code','CP6-AP-FLOW-POCKET','material_id',m.id,'roll_id',r.id,'location_id',l.id)
  from erp.materials m join erp.material_rolls r on r.material_id=m.id cross join erp.locations l
  where m.material_sku='CP6-AP-FLOW-POCKET' and l.location_code='CP6-AP-FLOW-POCKET'))"""

def identities(cur):
    value=cur.execute(IDENTITIES_SQL).fetchone()[0]
    assert value['accessory'] and value['pocket'],'DISPOSABLE_FIXTURE_IDENTITIES_MISSING'
    return value

def native(cur,name,*args):
    a.admin(cur)
    a.actors.actors.claims(cur,dict(sub=a.base.OPERATOR_AUTH,role='authenticated'))
    return cur.execute(sql.SQL('select {}({})').format(sql.Identifier(*name.split('.')),sql.SQL(',').join(sql.Placeholder() for _ in args)),args).fetchone()[0]

def browser_foundation(cur):
    """Same pre-insertion UUID qualification as the earlier AN browser fixture.

    Frozen seed files and product parsers are not edited. Only synthetic UUID
    version/variant bits change, consistently before any fixture rows exist.
    """
    a.admin(cur)
    initial=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()
    a.actors.actors.claims(cur,dict(sub=a.base.OPERATOR_AUTH,role='authenticated'))
    pattern=re.compile(r'\b([0-9a-f]{8}-[0-9a-f]{4})-0000-0000-([0-9a-f]{12})\b')
    mapping={};manifest=[]
    for name in ('cp3_r4_full_schema_seed.sql','cp6_laundry_qc_concurrency_seed.sql'):
        original=a.base.read_psql_seed(Path('supabase/tests')/name)
        def canonical(match):
            replacement=match[1]+'-4000-8000-'+match[2]
            assert replacement not in original,'FIXTURE_UUID_COLLISION'
            mapping[match[0]]=replacement;return replacement
        qualified,count=pattern.subn(canonical,original)
        manifest.append(dict(source=name,replacements=count,original_sha256=hashlib.sha256(original.encode()).hexdigest(),qualified_sha256=hashlib.sha256(qualified.encode()).hexdigest()))
        if name.startswith('cp3_'):cur.execute('alter table erp.cutting_groups disable trigger trg_06_require_pattern_identity')
        cur.execute(qualified,prepare=False)
        if name.startswith('cp3_'):cur.execute('alter table erp.cutting_groups enable trigger trg_06_require_pattern_identity')
    assert mapping and len(set(mapping.values()))==len(mapping)
    a.admin(cur)
    assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()==initial
    (OUT/'UI_FIXTURE.json').write_text(json.dumps(dict(sources=manifest,mapping=mapping,pre_insertion_only=True,source_files_changed=False,product_parser_changed=False,production_go=False),indent=2)+'\n')

def seed(cur):
    runtime.verified(cur,'AP');browser_foundation(cur)
    today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    a.production.prior.set_open_period(cur,today-timedelta(days=90));a.admin(cur)
    start=a.production.at(today-timedelta(days=2),0)
    model,contractor=cur.execute("select model_id,contractor_id from erp.production_orders where po_number='CP6-RACE-PO'").fetchone()
    foundation.MASTER=dict(model=model,contractor=contractor,start=start,supplier=cur.execute("select id from erp.suppliers where supplier_code='CP6-RACE-SUP'").fetchone()[0],pcs='PCS')
    cat,uom=foundation.category(cur,12);mat=foundation.material(cur,'ACCESSORY',cat);loc,_=foundation.locations(cur)
    cur.execute("update erp.materials set material_sku='CP6-AP-FLOW-ACC' where id=%s",(mat,))
    cur.execute("update erp.locations set location_code='CP6-AP-FLOW-ACC' where id=%s",(loc,))
    payload=dict(purchase_number=foundation.tag(),supplier_id=str(foundation.MASTER['supplier']),location_id=str(loc),
        physical_at=(start+timedelta(hours=1)).isoformat(),change_reason='Native disposable accessory fixture',
        lines=[dict(material_id=str(mat),qty=300,unit_price=2,price_state='ESTIMATED',price_source='MANUAL_ESTIMATE')])
    draft=native(cur,'erp.save_material_purchase_draft_v2',json.dumps(payload),uuid.uuid4(),None)
    native(cur,'erp.post_material_purchase_v2',draft['purchase_id'],uuid.uuid4(),draft['row_version'],'Native disposable receipt')
    price=cur.execute('insert into erp.contractor_accessory_price_versions(contractor_id,category_id,selling_price,selling_uom_code,effective_from) values(%s,%s,36,%s,%s) returning id',(contractor,cat,uom,start)).fetchone()[0]
    # The existing receipt builder uses the unchanged public import facade.
    imported=receipts.fixture(a,cur,today,True,code='CP6-AP-FLOW-POCKET')
    roll=receipts.finalize(a,cur,imported)
    pocket.call(a,cur,'REGISTER',dict(material_id=roll['material_id'],reason='Universal pocket fabric'))
    a.admin(cur)
    runtime.verified(cur,'AP')
    return identities(cur)

def state(cur):
    f=identities(cur)
    m=f['accessory']['material'];r=f['pocket']['roll_id']
    stock=cur.execute('select cached_stock_qty::text from erp.materials where id=%s',(m,)).fetchone()[0]
    roll=cur.execute('select coalesce(sum(qty_signed),0)::text from erp.material_stock_movements where roll_id=%s',(r,)).fetchone()[0]
    ledger={k:cur.execute('select coalesce(sum(debit-credit),0)::text from erp.journal_lines where account_id=erp.account_id(%s)',(k,)).fetchone()[0] for k in ('MATERIAL_INVENTORY','WIP','FG_INVENTORY','COGS','OTHER_EXPENSE')}
    all_ledger=dict(cur.execute('select account_id::text,sum(debit-credit)::text from erp.journal_lines group by account_id having sum(debit-credit)<>0 order by account_id').fetchall())
    journals=cur.execute('select count(*) from (select journal_entry_id from erp.journal_lines group by journal_entry_id having sum(debit)<>sum(credit)) s').fetchone()[0]
    counts={name:cur.execute(sql.SQL('select count(*) from erp.{}').format(sql.Identifier(name))).fetchone()[0] for name in ('contractor_material_issues','material_stock_movements','journal_entries','pocket_fabric_usage','pocket_periods','opening_balance_items')}
    return dict(accessory_stock=stock,pocket_stock=roll,ledger=ledger,all_ledger=all_ledger,unbalanced=journals,counts=counts)

def main():
    mode=sys.argv[1]
    assert os.environ.get('CP6_AP_FLOW_CONFIRM')=='cp6_rollback'
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
        if mode=='seed':
            result=seed(cur);(OUT/'FIXTURE.json').write_text(json.dumps(result,indent=2)+'\n')
        elif mode=='state':result=state(cur)
        elif mode=='identities':result=identities(cur)
        elif mode=='boundary':
            snapshot=data(cur);result=dict(sha256=hashlib.sha256(json.dumps(snapshot,sort_keys=True,default=str).encode()).hexdigest(),tables=len(snapshot))
        elif mode=='verify':
            import cp6_aq_runtime as aq
            result=aq.verified(cur)
        else:raise AssertionError('Unknown fixture operation')
        print(json.dumps(result,default=str))

if __name__=='__main__':main()
