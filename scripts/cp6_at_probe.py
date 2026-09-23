"""Independent AS review on the exact frozen runtime, never patching its functions.

Fixtures may use admin; every business action uses the authenticated public RPC.
All sequential cases restore ERP, auth, history and ACL snapshots. The clone is
destroyed in finally and the primary AN snapshot must remain exactly unchanged.
"""
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import traceback
import uuid

import psycopg

FROZEN = '8a170ce9931523f6fabe02ac5c24154d3333236b'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.cwd() / 'scripts'))
import cp6_as_trial as writer
import cp6_as_runtime as runtime
import cp6_as_probe as old_probe
import cp6_as_cases as old_cases
import cp6_ar_runtime as ar
import cp6_ao_ap_installed as api
import cp6_ao_ap_runtime as prior
import cp6_successor_regression as boundary
import cp6_initial_import_production_trial as production
from cp6_ao_ap_inventory import function_pins

OUT = ROOT / 'cp6-proof/at-audit'


def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (name + '.json')).write_text(json.dumps(data, indent=2, default=str) + '\n')


def series(cur, sku, model, brand, size, start, split, active_old=True, color='Blue'):
    """Two valid nonoverlapping immutable versions, created through live guards."""
    old = uuid.uuid4()
    cur.execute('''insert into erp.products(id,sku,product_name,model_id,brand_id,size_id,
        color_name,is_active,effective_from,effective_to,identity_root_id)
        values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        (old,sku,'AT historical identity',model,brand,size,color,active_old,start,split,old))
    new = cur.execute('''insert into erp.products(sku,product_name,model_id,brand_id,size_id,
        color_name,is_active,effective_from,identity_root_id,supersedes_product_id)
        values(%s,%s,%s,%s,%s,%s,true,%s,%s,%s) returning id''',
        (sku,'AT current identity',model,brand,size,color,split,old,old)).fetchone()[0]
    return old,new


def attempt(cur, operation):
    before = boundary.snapshot(cur)
    cur.execute('savepoint at_rpc')
    error = result = None
    try:
        result = operation()
    except psycopg.Error as exc:
        error = dict(sqlstate=exc.sqlstate, message=exc.diag.message_primary)
        cur.execute('rollback to savepoint at_rpc')
    api.admin(cur)
    cur.execute('release savepoint at_rpc')
    if error:
        assert boundary.snapshot(cur) == before, 'REFUSAL_CHANGED_BOUNDARY'
    return result,error


def versioned_bs(cur,today,active_old):
    f = production.fixture(api,cur,today)
    code = f['code']
    model = cur.execute('insert into erp.product_models(model_code,model_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
    brand = cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
    size = cur.execute('insert into erp.sizes(size_code) values(%s) returning id',(code,)).fetchone()[0]
    old,new = series(cur,code,model,brand,size,old_probe.invoice.at(today-timedelta(days=20),0),
                     old_probe.invoice.at(today-timedelta(days=10),0),active_old)
    for row in f['rows']:
        if row['balance_type'] in ('BS','FINISHED_GOODS'):
            row.update(brand_code=code,model_code=code,size_code=code,color_name='Blue')
    api.upload(cur,f['batch'],'OPENING_BALANCE_ITEM',f['rows'])
    counts = api.invoke(cur,'VALIDATE',f['batch'])
    rows = api.read(cur,f['batch'])['batch']['rows']
    errors = [dict(entity=r['entity'],payload=r['payload'],errors=r['errors']) for r in rows if r['validation_status']=='ERROR']
    result = None
    if not counts['error_rows']:
        result = api.invoke(cur,'FINALIZE',f['batch'])
        assert result['status']=='POSTED',result
        selected = cur.execute('''select i.product_id from erp.opening_balance_items i
            join erp.opening_balance_headers h on h.id=i.opening_id
            where h.migration_batch_id=%s and i.balance_type='BS' ''',(f['batch'],)).fetchone()[0]
        assert selected == new,(selected,new)
        production.truth(cur)
    return dict(status='COUNTEREXAMPLE' if errors else 'PASS',expected='Unique version valid at cutover is accepted',
                old_display_active=active_old,old_product=old,expected_product=new,errors=errors,result=result)


def versioned_wip(cur,today,variant,zone):
    f = production.fixture(api,cur,today)
    _,sources = production.finalize(api,cur,f)
    model,size = cur.execute('select model_id,size_id from erp.products where sku=%s',(f['code'],)).fetchone()
    brand_code = f['code']+'AT'
    brand = cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(brand_code,brand_code)).fetchone()[0]
    day = today-timedelta(days=3)
    split = old_probe.invoice.at(day-timedelta(days=1),12)
    old,new = series(cur,f['code'],model,brand,size,old_probe.invoice.at(today-timedelta(days=6),0),split,
                     active_old=variant!='OLD_INACTIVE')
    payload = dict(batch_id=f['batch'],opening_item_id=sources['WIP']['opening_item_id'],expected_remaining='8',
                   operation='COMPLETE',qty_pcs='4',product_sku=f['code'],brand_code=brand_code,
                   location_code=f['code']+'F',date=str(day),reason='AT temporal identity audit')
    expected = new
    if variant=='EXPLICIT_CURRENT':payload['product_id']=str(new)
    if variant=='EXPIRED_ID':payload['product_id']=str(old)
    cur.execute('select set_config(\'TimeZone\',%s,true)',(zone,))
    key = uuid.uuid4()
    result,error = attempt(cur,lambda:api.call(cur,'WIP_OUTPUT',payload,key))
    observed = None
    failures = {}
    if result:
        observed = cur.execute('''select l.product_id,l.produced_at,p.effective_from,p.effective_to,l.initial_qty_pcs
            from erp.fg_lots l join erp.products p on p.id=l.product_id where l.id=%s''',(result['lot_id'],)).fetchone()
        if observed[0]!=expected or not (observed[1]>=observed[2] and (observed[3] is None or observed[1]<observed[3])):
            failures['identity_or_physical_time'] = dict(expected=expected,actual=observed)
        before = boundary.snapshot(cur)
        assert api.call(cur,'WIP_OUTPUT',payload,key)==result
        assert boundary.snapshot(cur)==before,'REPLAY_CHANGED_BOUNDARY'
        production.truth(cur)
        production.reverse_output(api,cur,f,result)
        assert next(s for s in api.read(cur,f['batch'])['batch']['production_sources'] if s['balance_type']=='WIP')['remaining_qty_pcs']==8
    if variant=='EXPIRED_ID':
        if result:failures['expired_identity_accepted']=observed
    elif error:
        failures['valid_unique_version_refused']=error
    return dict(status='COUNTEREXAMPLE' if failures else 'PASS',variant=variant,zone=zone,
                candidate_periods=[str(split)],expected_product=expected,result=result,refusal=error,
                observation=observed,mismatches=failures,ordinary_authenticated_rpc=True)


def cases(cur,today):
    rows=[]
    # Reproduce the three peer defect families on both real AR and AS catalogs.
    for zone in ('Asia/Jakarta','UTC','Etc/GMT+12','Pacific/Kiritimati'):
        rows.append(('PEER_DATE:'+zone,lambda z=zone:old_probe.invoice_dates(cur,today,z,True,True,'20.003')))
    rows.extend([
        ('PEER_WIP_AMBIGUOUS',lambda:old_probe.wip_identity(cur,today,'AMBIGUOUS')),
        ('PEER_WIP_EXPLICIT',lambda:old_probe.wip_identity(cur,today,'EXPLICIT_SECOND')),
        ('PEER_STAGED_BS',lambda:old_cases.staged_brand(cur,today)),
    ])
    for active in (True,False):
        rows.append(('VERSIONED_BS:'+str(active),lambda a=active:versioned_bs(cur,today,a)))
    for zone in ('UTC','Pacific/Kiritimati'):
        for variant in ('AUTO_CURRENT','EXPLICIT_CURRENT','EXPIRED_ID','OLD_INACTIVE'):
            rows.append(('VERSIONED_WIP:'+zone+':'+variant,lambda v=variant,z=zone:versioned_wip(cur,today,v,z)))
    return rows


def group(stage):
    verify = ar.verified if stage=='AR' else runtime.verified
    result=dict(stage=stage,status='INCOMPLETE',cases={},production_go=False,independent_acceptance=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        result['runtime_before']=verify(cur)
        initial=boundary.snapshot(cur);catalog=function_pins(cur)
        if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:
            cur.execute('grant usage on schema erp to authenticated')
        if not initial['erp']['app_users']['count']:api.seed(cur)
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        boundary.historical.prior.set_open_period(cur,date(2026,8,31))
        planned=cases(cur,today);result['planned_case_ids']=[k for k,_ in planned]
        for key,operation in planned:
            before=boundary.snapshot(cur);cur.execute('savepoint at_case')
            try:row=operation()
            except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint at_case');api.admin(cur);cur.execute('release savepoint at_case')
            row['full_boundary_restored']=boundary.snapshot(cur)==before
            if not row['full_boundary_restored']:row['status']='INCOMPLETE'
            result['cases'][key]=row;save(stage,result)
            print(json.dumps(dict(stage=stage,case=key,**row),default=str),flush=True)
        assert function_pins(cur)==catalog,'CASE_MUTATED_FUNCTION_OR_ACL'
        conn.rollback();result['runtime_after']=verify(cur)
        result['full_boundary_restored']=boundary.snapshot(cur)==initial
        conn.rollback()
    result['counts']=dict(Counter(r['status'] for r in result['cases'].values()))
    result['status']='INCOMPLETE' if result['counts'].get('INCOMPLETE') or not result['full_boundary_restored'] else 'COUNTEREXAMPLE' if result['counts'].get('COUNTEREXAMPLE') else 'PASS'
    save(stage,result);return result


def run():
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback'
    assert os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==FROZEN
    writer.source()
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    changed=subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only',FROZEN,head],text=True).splitlines()
    allowed={'.github/workflows/cp6-at-audit.yml','scripts/cp6_at_probe.py','docs/cp6-at-audit.md'}
    assert set(changed)==allowed,('AUDITOR_SCOPE',changed)
    assert not subprocess.check_output(['git','-C',str(ROOT),'diff','HEAD','--name-only'],text=True).strip()
    report=dict(status='INCOMPLETE',auditor_head=head,frozen_source=FROZEN,
                auditor_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(allowed)},
                installed_functions_patched_for_testing=False,production_go=False,independent_acceptance=False)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        writer.install_ar()
        report['AR']=group('AR')['counts']
        runtime.change('install',boundary.PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        after=group('AS');report['AS']=after['counts'];report['status']=after['status']
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN')
            report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        save('RESULT',report)
    print(json.dumps(report,default=str),flush=True)
    assert report['status']=='PASS',report


if __name__=='__main__':run()
