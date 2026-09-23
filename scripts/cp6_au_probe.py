"""Independent AT review and ordinary master-identity lifecycle controls."""
from collections import Counter
from datetime import date,timedelta
from pathlib import Path
import hashlib,json,os,subprocess,sys,traceback,uuid
import psycopg

ROOT=Path(__file__).resolve().parents[1]
FROZEN='a8a8771cdab3bec28f04600c86870142270e8487'
sys.path.insert(0,str(Path.cwd()/'scripts'))
import cp6_at_trial as writer
import cp6_at_runtime as runtime
import cp6_at_cases as temporal
import cp6_at_probe as peer
import cp6_as_probe as dates
import cp6_ao_ap_installed as api
import cp6_initial_import_production_trial as production
import cp6_successor_regression as boundary
import cp6_ao_ap_runtime as prior
from cp6_ao_ap_inventory import function_pins

OUT=ROOT/'cp6-proof/au-review'
def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\n')

def master_case(cur,today,variant):
    f=production.fixture(api,cur,today)
    # Normal finalized opening supplies the product's historical reference.
    _,sources=production.finalize(api,cur,f)
    product=cur.execute('select id,model_id,brand_id,size_id from erp.products where sku=%s',(f['code'],)).fetchone()
    if variant in ('UNUSED_IDENTITY','DISPLAY_NAME'):
        code=f['code']+'UNUSED'
        brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
        pid=cur.execute('''insert into erp.products(sku,product_name,model_id,brand_id,size_id,color_name,is_active,effective_from)
            values(%s,%s,%s,%s,%s,'Blue',true,%s) returning id''',(code,code,product[1],brand,product[3],dates.invoice.at(today-timedelta(days=2),0))).fetchone()[0]
        product=(pid,product[1],brand,product[3])
    original=cur.execute('select sku,product_name,color_name,effective_from,effective_to from erp.products where id=%s',(product[0],)).fetchone()
    before=boundary.snapshot(cur)
    api.ordinary(cur)
    if variant.startswith('CANCEL_'):
        api.admin(cur)
        code=f['code']+'CANCEL'
        brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
        old,new=peer.series(cur,code,product[1],brand,product[3],dates.invoice.at(today-timedelta(days=2),0),dates.invoice.at(today+timedelta(days=1),0))
        before=boundary.snapshot(cur)
        def operation():
            api.ordinary(cur)
            return cur.execute('select erp.cancel_product_identity_successor(%s,%s)',(new,'AU cancel unused future version')).fetchone()[0]
        result,error=peer.attempt(cur,operation)
        observations=cur.execute('select id,effective_to from erp.products where id=any(%s) order by id',([old,new],)).fetchall()
        correct=result==old and observations==[(old,None)]
    else:
        effective=cur.execute('select clock_timestamp()+interval \'1 minute\'').fetchone()[0]
        color='Blue' if variant=='DISPLAY_NAME' else 'Green'
        def operation():
            api.ordinary(cur)
            return cur.execute('select erp.edit_product_identity_effective(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (product[0],original[0],product[1],product[2],color,product[3],'AU corrected master',effective,'AU ordinary identity lifecycle')).fetchone()[0]
        result,error=peer.attempt(cur,operation)
        observations=cur.execute('select id,sku,color_name,effective_from,effective_to,supersedes_product_id from erp.products where identity_root_id=%s order by effective_from',(product[0],)).fetchall()
        correct=result is not None and not error
        if correct and variant=='USED_SUCCESSOR':
            correct=len(observations)==2 and result!=product[0] and observations[0][2]=='Blue' and observations[0][4]==effective and observations[1][0]==result and observations[1][2]=='Green'
        if correct and variant=='UNUSED_IDENTITY':correct=result==product[0] and observations[0][2]=='Green'
        if correct and variant=='DISPLAY_NAME':correct=result==product[0] and observations[0][2]=='Blue'
    api.admin(cur)
    return dict(status='PASS' if correct else 'COUNTEREXAMPLE',variant=variant,ordinary_authenticated_rpc=True,
                expected='Owner-admin ordinary product lifecycle succeeds with valid unused/current input',result=result,refusal=error,
                observations=observations,refusal_unchanged=boundary.snapshot(cur)==before if error else None)

def audit_group():
    report=dict(status='INCOMPLETE',cases={},production_go=False,independent_acceptance=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        report['runtime_before']=runtime.verified(cur);initial=boundary.snapshot(cur);catalog=function_pins(cur)
        if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:cur.execute('grant usage on schema erp to authenticated')
        if not initial['erp']['app_users']['count']:api.seed(cur)
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='120s';set local lock_timeout='8s'")
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        boundary.historical.prior.set_open_period(cur,date(2026,8,31))
        cases=[('MASTER:'+v,lambda v=v:master_case(cur,today,v)) for v in ('DISPLAY_NAME','UNUSED_IDENTITY','USED_SUCCESSOR','CANCEL_FUTURE')]
        report['planned_case_ids']=[k for k,_ in cases]
        for key,operation in cases:
            before=boundary.snapshot(cur);cur.execute('savepoint au_case')
            try:row=operation()
            except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
            finally:cur.execute('rollback to savepoint au_case');api.admin(cur);cur.execute('release savepoint au_case')
            row['full_boundary_restored']=boundary.snapshot(cur)==before
            if not row['full_boundary_restored']:row['status']='INCOMPLETE'
            report['cases'][key]=row;save('AT_MASTER',report)
            print(json.dumps(dict(group='AT_MASTER',case=key,**row),default=str),flush=True)
        assert function_pins(cur)==catalog
        conn.rollback();report['runtime_after']=runtime.verified(cur);report['full_boundary_restored']=boundary.snapshot(cur)==initial;conn.rollback()
    report['counts']=dict(Counter(r['status'] for r in report['cases'].values()))
    report['status']='INCOMPLETE' if report['counts'].get('INCOMPLETE') or not report['full_boundary_restored'] else 'REVIEW_COMPLETE'
    save('AT_MASTER',report);return report

def run():
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==FROZEN
    writer.source()
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    allowed={'.github/workflows/cp6-au-review.yml','scripts/cp6_au_probe.py','docs/cp6-au-review.md'}
    assert set(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only',FROZEN,head],text=True).splitlines())==allowed
    assert not subprocess.check_output(['git','-C',str(ROOT),'diff','HEAD','--name-only'],text=True).strip()
    report=dict(status='INCOMPLETE',auditor_head=head,frozen_product_source=FROZEN,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(allowed)},
                installed_functions_patched_for_testing=False,production_go=False,independent_acceptance=False)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        writer.install_as()
        as_result=writer.group('AU_AS_REPRO',lambda cur,today:[x for x in temporal.cases(cur,today) if x[0].startswith('WIP_VERSION:')],stage='AS')
        report['as_reproduction']=as_result['counts']
        assert as_result['counts']['COUNTEREXAMPLE']==4 and as_result['counts']['PASS']==4 and not as_result['counts']['INCOMPLETE']
        runtime.change('install',boundary.PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
        at=writer.group('AU_AT_REPLAY',temporal.cases)
        report['at_controls']=at['counts'];assert len(at['cases'])==16 and at['status']=='WRITER_PASS'
        master=audit_group();report['new_master_cases']=master['counts'];assert master['status']=='REVIEW_COMPLETE'
        report['status']='REVIEW_COMPLETE_WITH_FINDINGS' if master['counts'].get('COUNTEREXAMPLE') else 'REVIEW_COMPLETE_NO_NEW_FINDINGS'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        save('RESULT',report)
    print(json.dumps(report,default=str),flush=True)
    assert report['status'].startswith('REVIEW_COMPLETE'),report

if __name__=='__main__':run()
