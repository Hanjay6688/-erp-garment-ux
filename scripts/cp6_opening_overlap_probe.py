"""Native counterexamples on committed AQ. No installed definition is patched."""
from pathlib import Path
from datetime import timedelta
import json,os,subprocess,traceback,uuid
import psycopg
import cp6_ao_ap_maintenance as maintenance
import cp6_ao_ap_runtime as prior
import cp6_aq_runtime as aq
import cp6_ao_ap_installed as api
from cp6_ao_ap_inventory import data

OUT=Path('cp6-proof/opening-overlap')
PG='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
ADMIN='postgresql://supabase_admin:postgres@127.0.0.1:54322/cp6_rollback'
CONTROL='postgresql://postgres:postgres@127.0.0.1:54322/postgres'

def native(cur):
    api.admin(cur)
    api.actors.actors.claims(cur,dict(sub=api.base.OPERATOR_AUTH,role='authenticated'))

def imported(cur,today,kind):
    tag='OV'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=tag,cutover_date=str(today-timedelta(days=1))))['batch_id']
    masters={}
    row=dict(balance_type=kind,control_key='CHECK')
    control=dict(balance_type=kind,control_key='CHECK',amount='17.25')
    mapping={
      'CUSTOMER_RECEIVABLE':('CUSTOMER','customer_code','customer_name',{}),
      'SUPPLIER_PAYABLE':('SUPPLIER','supplier_code','supplier_name',{'supplier_type':'MATERIAL'}),
      'VENDOR_PAYABLE':('LAUNDRY_VENDOR','vendor_code','vendor_name',{}),
      'CONTRACTOR_RECEIVABLE':('CONTRACTOR','contractor_code','contractor_name',{'contractor_type':'MANDOR'}),
      'CONTRACTOR_PAYABLE':('CONTRACTOR','contractor_code','contractor_name',{'contractor_type':'MANDOR'}),
    }
    if kind in mapping:
        entity,key,label,extra=mapping[kind]
        masters[entity]=[dict({key:tag,label:'Synthetic overlap party'},**extra)]
        row.update({key:tag,'amount':'17.25'})
    elif kind=='CASH_BANK':
        masters['CHART_ACCOUNT']=[dict(account_code=tag,account_name='Synthetic overlap cash',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT')]
        masters['CASH_ACCOUNT']=[dict(cash_account_code=tag,cash_account_name='Synthetic overlap cash',coa_account_code=tag,account_kind='BANK')]
        row.update(cash_account_code=tag,amount='17.25')
    elif kind=='MATERIAL':
        masters['LOCATION']=[dict(location_code=tag,location_name='Synthetic overlap raw',location_type='RAW_MATERIAL_WAREHOUSE')]
        masters['MATERIAL']=[dict(material_sku=tag,material_name='Synthetic overlap accessory',material_type='OTHER',unit_code='PCS')]
        row.update(material_sku=tag,location_code=tag,qty='7',unit_cost='2.25')
        control.update(qty='7',amount='15.75')
    elif kind in ('FINISHED_GOODS','BS'):
        masters['MODEL']=[dict(model_code=tag,model_name='Synthetic overlap model')]
        masters['BRAND']=[dict(brand_code=tag,brand_name='Synthetic overlap brand')]
        masters['SIZE']=[dict(size_code=tag)]
        masters['PRODUCT']=[dict(sku=tag,product_name='Synthetic overlap product',model_code=tag,brand_code=tag,size_code=tag,color_name='BLUE')]
        masters['LOCATION']=[dict(location_code=tag,location_name='Synthetic overlap FG',location_type='FG_WAREHOUSE')]
        row.update(product_sku=tag,location_code=tag,qty='7')
        control.update(qty='7',amount='15.75' if kind=='FINISHED_GOODS' else '0')
        if kind=='FINISHED_GOODS':row['unit_cost']='2.25'
    elif kind=='WIP':
        masters['MODEL']=[dict(model_code=tag,model_name='Synthetic overlap WIP')]
        row.update(model_code=tag,stage='SEWING',amount='17.25')
    else:raise AssertionError(kind)
    for entity,rows in masters.items():api.upload(cur,batch,entity,rows)
    api.upload(cur,batch,'OPENING_BALANCE_ITEM',[row]);api.upload(cur,batch,'OPENING_CONTROL',[control])
    result=api.invoke(cur,'FINALIZE',batch)
    assert result['status']=='POSTED',api.read(cur,batch)
    ident=cur.execute('select id from erp.opening_balance_headers where migration_batch_id=%s',(batch,)).fetchone()[0]
    return ident

def duplicate_via_legacy(cur,opening):
    native(cur)
    ident=cur.execute("insert into erp.opening_balance_headers(opening_number,opening_date,status,created_by,notes) select %s,opening_date,'DRAFT',erp.current_app_user_id(),'Synthetic direct legacy overlap' from erp.opening_balance_headers where id=%s returning id",('OV-LEGACY-'+uuid.uuid4().hex,opening)).fetchone()[0]
    cur.execute('''insert into erp.opening_balance_items(opening_id,balance_type,material_id,roll_id,product_id,model_id,contractor_id,customer_id,location_id,supplier_id,vendor_id,cash_account_id,stage,qty,amount,unit_cost_snapshot,quality_grade,notes,hpp_input_method,hpp_percent_of_price)
      select %s,balance_type,material_id,roll_id,product_id,model_id,contractor_id,customer_id,location_id,supplier_id,vendor_id,cash_account_id,stage,qty,amount,unit_cost_snapshot,quality_grade,'Synthetic direct legacy overlap',hpp_input_method,hpp_percent_of_price
      from erp.opening_balance_items where opening_id=%s''',(ident,opening))
    cur.execute('select erp.post_opening_balance(%s)',(ident,))
    return ident

def probe(cur,today,kind):
    first=imported(cur,today,kind)
    ledger_before=api.production.ledger(cur)
    second=duplicate_via_legacy(cur,first)
    statuses=cur.execute('select status from erp.opening_balance_headers where id=any(%s) order by id',([first,second],)).fetchall()
    assert statuses==[('POSTED',),('POSTED',)],statuses
    items=cur.execute('select count(*),sum(qty),sum(amount),sum(qty*unit_cost_snapshot) from erp.opening_balance_items where opening_id=any(%s)',([first,second],)).fetchone()
    assert items[0]==2,items
    ledger_after=api.production.ledger(cur)
    return dict(status='COUNTEREXAMPLE_CONFIRMED',balance_type=kind,posted_headers=2,opening_items=items,
        duplicate_ledger_delta={k:ledger_after[k]-ledger_before[k] for k in ledger_before if ledger_after[k]!=ledger_before[k]},
        import_transport='public RPC ordinary authenticated role',legacy_transport='native canonical function with owner claims in administrative connection')

def main():
    assert os.environ.get('CP6_OPENING_OVERLAP_CONFIRM')=='cp6_rollback'
    assert os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(status='INCOMPLETE',phase='COUNTEREXAMPLE_PROBE',cases={},production_go=False,independent_acceptance=False)
    def save():(OUT/'COUNTEREXAMPLES.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    with psycopg.connect(CONTROL) as c,c.cursor() as cur:
        prior.verified(cur,'AN');primary=data(cur)
    try:
        for family in ('AO','AP'):
            maintenance.install(family=family,target_pgurl=PG,maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'],report_path=OUT/(family+'_INSTALL.json'))
        with psycopg.connect(ADMIN) as c,c.cursor() as cur:api.seed(cur)
        report['aq_install']=aq.change('install',PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        with psycopg.connect(ADMIN) as c,c.cursor() as cur:
            report['runtime']=aq.verified(cur);baseline=data(cur)
            today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
            for kind in ['CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','CASH_BANK','MATERIAL','FINISHED_GOODS','WIP','BS']:
                cur.execute('savepoint overlap_probe')
                try:result=probe(cur,today,kind)
                except Exception as exc:result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                finally:cur.execute('rollback to savepoint overlap_probe');api.admin(cur);cur.execute('release savepoint overlap_probe')
                assert data(cur)==baseline,'PROBE_DATA_NOT_RESTORED'
                result['all_erp_tables_restored']=True;report['cases'][kind]=result;save()
                print(json.dumps(dict(case=kind,status=result['status'],error=result.get('error'))),flush=True)
            aq.verified(cur);c.rollback()
        report['status']='COUNTEREXAMPLES_CONFIRMED' if all(x['status']=='COUNTEREXAMPLE_CONFIRMED' for x in report['cases'].values()) else 'INCOMPLETE'
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(CONTROL) as c,c.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=data(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        save()
    assert report['primary_unchanged'] and report['clone_remaining']==0
    assert report['status']=='COUNTEREXAMPLES_CONFIRMED',report

if __name__=='__main__':main()
