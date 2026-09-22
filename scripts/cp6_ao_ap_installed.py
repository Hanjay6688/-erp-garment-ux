"""Run unchanged public-RPC case modules on committed permanent migrations."""
from pathlib import Path
from datetime import timedelta
from types import SimpleNamespace
import json,traceback,uuid
import psycopg
import cp6_v2620al_import_review as inherited
import cp6_accessory_issue_trial as accessories
import cp6_initial_import_receipt_trial as receipts
import cp6_initial_import_production_trial as production_origins
import cp6_pocket_fabric_trial as pocket
import cp6_pocket_period_trial as periods
import cp6_ao_ap_runtime as runtime
from cp6_ao_ap_inventory import data,inventory,platform

actors,base,production=inherited.actors,inherited.base,inherited.production
def admin(cur):actors.admin(cur)
def ordinary(cur):
    admin(cur)
    cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
    cur.execute('set local session authorization authenticated')
    assert cur.execute('select current_user,session_user').fetchone()==('authenticated','authenticated')
def call(cur,action,payload,key=None):
    ordinary(cur)
    result=cur.execute('select public.erp_save_initial_import_action_v1(%s,%s::jsonb,%s)',(action,json.dumps(payload,default=str),key or uuid.uuid4())).fetchone()[0]
    admin(cur);return result
def read(cur,batch=None):
    ordinary(cur);result=cur.execute('select public.erp_get_initial_import_workspace_v1(%s)',(batch,)).fetchone()[0];admin(cur);return result
def invoke(cur,action,batch,**extra):return call(cur,action,dict(batch_id=batch,expected_revision=read(cur,batch)['batch']['revision'],**extra))
def upload(cur,batch,entity,rows):return invoke(cur,'SAVE_FILE',batch,entity=entity,filename=entity+'.csv',rows=[dict(source_row_no=n+2,payload=r) for n,r in enumerate(rows)])

def seed(cur):
    admin(cur);cur.execute('grant usage on schema erp to authenticated')
    actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'))
    base.load_fixture_foundation(cur);admin(cur)
    cur.execute('revoke usage on schema erp from authenticated')

def latest_draft(cur,today):
    batch=call(cur,'CREATE',dict(batch_code='PERMANENT-'+uuid.uuid4().hex,cutover_date=str(today-timedelta(days=1))))['batch_id']
    code='P'+uuid.uuid4().hex[:14]
    upload(cur,batch,'CUSTOMER',[dict(customer_code=code,customer_name='Permanent package fixture')])
    row=dict(balance_type='CUSTOMER_RECEIVABLE',customer_code=code,amount='14.25',control_key='AR')
    control=dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='14.25')
    upload(cur,batch,'OPENING_BALANCE_ITEM',[row]);upload(cur,batch,'OPENING_CONTROL',[control])
    before=production.ledger(cur);assert invoke(cur,'VALIDATE',batch)['error_rows']==0
    row['amount']='17.25';upload(cur,batch,'OPENING_BALANCE_ITEM',[row])
    assert invoke(cur,'FINALIZE',batch)['status']=='DRAFT' and production.ledger(cur)==before
    control['amount']='17.25';upload(cur,batch,'OPENING_CONTROL',[control])
    payload=dict(batch_id=batch,expected_revision=read(cur,batch)['batch']['revision']);key=uuid.uuid4()
    posted=call(cur,'FINALIZE',payload,key);assert posted['status']=='POSTED'
    boundary=actors.boundary(cur);assert call(cur,'FINALIZE',payload,key)==posted and actors.boundary(cur)==boundary
    values=cur.execute('select count(*),sum(i.amount) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s',(batch,)).fetchone()
    assert values==(1,inherited.Decimal('17.25')),values
    return dict(status='PASS',latest_value='17.25',control_not_posted=True,replay_exact=True)

def run(url,path):
    report=dict(status='INCOMPLETE',cases={},committed_permanent_migrations=True,production_go=False,independent_acceptance=False)
    def save():path.write_text(json.dumps(report,indent=2,default=str)+'\n')
    try:
        with psycopg.connect(url) as conn,conn.cursor() as cur:
            runtime.verified(cur,'AP');baseline=data(cur);catalog=inventory(cur);ledger=platform(cur)
            cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='150s';set local lock_timeout='8s'")
            today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
            a=SimpleNamespace(**globals());cases=[('PERMANENT_LATEST_DRAFT_TOTAL_REPLAY',lambda:latest_draft(cur,today))]
            for module in (accessories,receipts,production_origins,pocket,periods):cases+=module.cases(a,cur,today)
            for name,operation in cases:
                admin(cur);before=actors.boundary(cur);cur.execute('savepoint installed_case')
                try:result=operation()
                except Exception as exc:result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                finally:cur.execute('rollback to savepoint installed_case');admin(cur);cur.execute('release savepoint installed_case')
                result['boundary_restored']=actors.boundary(cur)==before
                if not result['boundary_restored']:result['status']='INCOMPLETE'
                report['cases'][name]=result;save();print(json.dumps(dict(case=name,status=result['status'],error=result.get('error'))),flush=True)
            conn.rollback();runtime.verified(cur,'AP')
            assert data(cur)==baseline and inventory(cur)==catalog and platform(cur)==ledger
            report.update(complete_boundary_restored=True,status='PASS' if all(r['status']=='PASS' for r in report['cases'].values()) else 'INCOMPLETE')
    except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
    save();assert report['status']=='PASS',report.get('error','INSTALLED_CASE_FAILURE');return report
