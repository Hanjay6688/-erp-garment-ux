"""BE writer T1_FAMILY probe. Expected comes from M:4828-4843/5057-5096, C6 and the ALL-C04 errata.
Stage 1 covers the selected-lot conversion; other required BE flows remain explicitly unfinished.
"""
from datetime import timedelta
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,traceback,uuid
import psycopg
import cp6_bd_probe as bdp
import cp6_be_build as build
import cp6_layers

api,chain,one,q,verdict,refused=bdp.api,bdp.chain,bdp.one,bdp.q,bdp.verdict,bdp.refused
boundary,r1,prior=bdp.boundary,bdp.r1,bdp.prior
OUT=Path(__file__).resolve().parents[1]/'cp6-proof/be'
bdp.bcp.NO_ROUTE_MESSAGES+=('erp_save_product_conversion_action_v1(',)

def installed(cur):return bool(one(cur,"select count(*) from erp.schema_migrations where version='v2.6.20be'"))

def verified(cur):
    result=bdp.bd_verified(cur)
    assert installed(cur),'BE_MARKER_MISSING'
    sql=build.OUT.read_text()
    for signature in dict.fromkeys(build.REPLACED+build.new_functions()):
        name=signature.split('(')[0];schema,fn=name.split('.')
        start=list(re.finditer(r'(?i)create or replace function '+re.escape(name)+r'\(',sql))[-1].start()
        body_start=sql.index('$function$',start)+len('$function$');body=sql[body_start:sql.index('$function$',body_start)]
        actual=q(cur,'select p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.proname=%s',schema,fn)
        assert len(actual)==1 and actual[0][0]==body,('BE_INSTALLED_SOURCE_MISMATCH',signature)
    for table in build.NEW_TABLES:assert one(cur,'select to_regclass(%s) is not null','erp.'+table),table
    return dict(result,stage='BD_PLUS_BE_T1',be_sql_sha256=hashlib.sha256(sql.encode()).hexdigest())

def install_be():
    with psycopg.connect(boundary.PG,autocommit=True) as conn:conn.execute(build.OUT.read_text(),prepare=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        result=verified(cur);conn.rollback()
    return result

def be(cur,action,payload,key=None,auth=None):
    if auth:bdp.bcp.session(cur,auth)
    else:bdp.bcp.session(cur)
    result=cur.execute('select public.erp_save_product_conversion_action_v1(%s,%s::jsonb,%s)',
       (action,json.dumps(payload,default=str),str(key or uuid.uuid4()))).fetchone()[0]
    api.admin(cur);return result

def fixture(cur,today):
    fx=bdp.fixture(cur,today-timedelta(days=1),'BE-CONVERSION')
    bdp.process_rate(cur,fx,'5000.00')
    rec=bdp.receive(cur,bdp.plain_delivery(cur,fx,10,11),fx,10,13)
    product,lot=bdp.finish_goods(cur,fx,rec['receipt_id'],10,14)
    target=bdp.sized_product(cur,chain.base.SIZE,'BE-'+uuid.uuid4().hex[:8])
    loc=one(cur,'select location_id::text from erp.fg_stock_movements where lot_id=%s order by physical_at,id limit 1',lot)
    payload=dict(source_lot_id=lot,target_product_id=target,location_id=loc,qty_pcs=6,
                 physical_at=bdp.iso(chain.production.at(fx['day'],15)),reason='BE real relabel',expected_version='before')
    if installed(cur):payload['expected_version']=one(cur,'select erp.be_source_revision_v1(%s,%s)',lot,loc)
    return dict(fx,product=product,lot=lot,target=target,location=loc,payload=payload)

def qty(cur,lot):return one(cur,'select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',lot)

def conversion_roundtrip(cur,today):
    f=fixture(cur,today)
    if not installed(cur):return bdp.no_route(cur,lambda:be(cur,'POST',f['payload']))
    before=bdp.all_truth(cur);value=bdp.lot_value(cur,f['lot']);key=str(uuid.uuid4())
    result=be(cur,'POST',f['payload'],key);dest=result['destination_lot_id']
    replay=be(cur,'POST',f['payload'],key)
    quantities=(qty(cur,f['lot']),qty(cur,dest));hpp=bdp.lot_value(cur,dest)
    after=bdp.all_truth(cur)
    be(cur,'REVERSE',dict(conversion_id=result['conversion_id'],reason='BE inverse physical relabel'))
    return verdict(dict(exact_selected_lot=one(cur,'select source_lot_id::text from erp.fg_lots where id=%s',dest)==f['lot'],
       quantity=quantities==(4,6),value=hpp==value*bdp.D('0.6'),replay=replay['conversion_id']==result['conversion_id']
          and one(cur,'select count(*) from erp.product_conversions where id=%s',key)==1,
       inverse=(qty(cur,f['lot']),qty(cur,dest))==(10,0),truth=bdp.truth_quiet(before,after)),quantities=quantities,value=str(value),target_value=str(hpp))

def refusals(cur,today):
    f=fixture(cur,today)
    if not installed(cur):return bdp.no_route(cur,lambda:be(cur,'POST',f['payload']))
    stale=refused(cur,lambda:be(cur,'POST',dict(f['payload'],expected_version='stale')),'STALE_VERSION')
    over=refused(cur,lambda:be(cur,'POST',dict(f['payload'],qty_pcs=11)),'BE_SOURCE_CAPACITY')
    same=refused(cur,lambda:be(cur,'POST',dict(f['payload'],target_product_id=f['product'])),'BE_SAME_SKU')
    extra=bdp.bcp.denied(cur,lambda:be(cur,'POST',dict(f['payload'],conversion_cost_total='99.00')),'contains unexpected key conversion_cost_total')
    return verdict(dict(stale=stale['ok'],over=over['ok'],same=same['ok'],unsourced=extra['ok'],unchanged=qty(cur,f['lot'])==10),refusals=[stale,over,same,extra])

def actual_usage(cur,today):
    f=fixture(cur,today)
    if not installed(cur):return bdp.no_route(cur,lambda:be(cur,'POST',f['payload']))
    bc=bdp.bcp;acc=bc.fixture(cur,f['day'],stock_qty=100,cost='2.00')
    bc.policy(cur,'ACC_DEC04',dict(OWN_FG_REPAIR_account_id=bc.account(cur,'5100')))
    bc.policy(cur,'ACC_DEC07',dict(approval='NONE'))
    api.admin(cur);cur.execute('grant usage on schema erp to authenticated')
    source=be(cur,'POST',f['payload']);dest=source['destination_lot_id']
    old_hpp=bdp.lot_value(cur,dest);old_expense=bdp.gl(cur,'OTHER_EXPENSE');truth=bdp.all_truth(cur)
    payload=dict(conversion_id=source['conversion_id'],expected_version=one(cur,'select erp.be_conversion_revision_v1(%s)',source['conversion_id']),
      location_id=acc['main'],physical_at=f['payload']['physical_at'],items=[dict(material_id=acc['material'],qty='6')],reason='BE actual six replacement buttons')
    posted=be(cur,'POST_USAGE',payload)
    hpp=bdp.lot_value(cur,dest);expense=bdp.gl(cur,'OTHER_EXPENSE');new_truth=bdp.all_truth(cur)
    used_qty=bc.stock(cur,acc['material'],acc['main'])
    blocked=refused(cur,lambda:be(cur,'REVERSE',dict(conversion_id=source['conversion_id'],reason='must refuse before source inverse')),'BE_REVERSE_DEPENDANTS')
    doc=posted['cost_document_id']
    bc.svc(cur,'REVERSE',dict(document_id=doc,expected_version='1',reason='BE source inverse'))
    restored_hpp=bdp.lot_value(cur,dest)
    be(cur,'REVERSE',dict(conversion_id=source['conversion_id'],reason='BE inverse after sources'))
    return verdict(dict(cost_once=hpp-old_hpp==bdp.D('12.00'),not_double_expense=expense==old_expense,
       material_once=used_qty==94 and bc.stock(cur,acc['material'],acc['main'])==100,truth=bdp.truth_quiet(truth,new_truth),
       linked_inverse=blocked['ok'] and restored_hpp==old_hpp and qty(cur,f['lot'])==10),
       cost=str(hpp-old_hpp),refusals=[blocked])

PLAN=[('BE01:SELECTED_LOT_REPLAY_REVERSE','NO_ROUTE',conversion_roundtrip),('BE01:CAPACITY_STALE_NO_UNSOURCED_COST','NO_ROUTE',refusals),
      ('BE01:ACTUAL_ACCESSORY_COST_ONCE_AND_INVERSE','NO_ROUTE',actual_usage)]
def cases(cur,today):return [(key,lambda f=fn:f(cur,today)) for key,_,fn in PLAN]

def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    r1.OUT=OUT;primary=None
    report=dict(status='INCOMPLETE',label='T1_FAMILY',phase=phase,production_go=False,independent_acceptance=False,release_evidence=False)
    report['run_identity']=bdp.run_identity.announce('T1_FAMILY',phase=phase)
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at();control=os.environ['CP6_ADMISSION_CONTROL_PGURL'];bbp=bdp.bbp
        awp,axp,ayp,azp,bap=bbp.awp,bbp.axp,bbp.ayp,bbp.azp,bbp.bap
        report['au_install']=awp.au_runtime.change('install',boundary.PG,control)['status']
        report['av_install']=awp.av_runtime.change('install',boundary.PG,control)['status']
        for name,fn in [('aw',awp.install_aw),('ax',axp.install_ax),('ay',ayp.install_ay),('az',azp.install_az),
          ('ba',bap.install_ba),('bb',bbp.install_bb),('bc',bdp.bcp.install_bc),('bd',bdp.install_bd)]:report[name+'_install']=fn()
        verify=bdp.bd_verified
        if phase=='after':report['be_install']=install_be();verify=verified
        group=r1.group('BE_CASES_'+phase.upper(),cases,verify)
        report['final']={k:v['status'] for k,v in group['cases'].items()}
        expected={k:e if phase=='before' else 'PASS' for k,e,_ in PLAN}
        report['mismatch']={k:dict(expected=e,actual=report['final'].get(k)) for k,e in expected.items() if report['final'].get(k)!=e}
        report['status']='REVIEW_COMPLETE' if group['status']!='INCOMPLETE' and not report['mismatch'] else 'INCOMPLETE'
    except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=one(cur,"select count(*) from pg_database where datname='cp6_rollback'")
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_'+phase.upper(),report)
    print(json.dumps(dict(be_probe_phase=phase,**report),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error') or report.get('mismatch')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=('before','after'),required=True);run(p.parse_args().phase)
