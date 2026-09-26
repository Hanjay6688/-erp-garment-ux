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
WS=None
WS_N=0
def snapshot(kind,value):
    global WS_N
    if WS is not None:
        WS_N+=1;(WS/(kind+'_'+str(WS_N)+'.json')).write_text(json.dumps(value,default=str))
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
    request=str(key or uuid.uuid4())
    if auth:bdp.bcp.session(cur,auth)
    else:bdp.bcp.session(cur)
    result=cur.execute('select public.erp_save_product_conversion_action_v1(%s,%s::jsonb,%s)',
       (action,json.dumps(payload,default=str),request)).fetchone()[0]
    snapshot('response',dict(result=result,action=action,request=request,payload=payload))
    if auth is None:
        workspace=cur.execute("select public.erp_get_product_conversion_workspace_v1('{}'::jsonb)").fetchone()[0]
        snapshot('be',workspace)
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

def nonpo_roundtrip(cur,today):
    day=today-timedelta(days=3);api.admin(cur)
    boundary.historical.prior.set_open_period(cur,day-timedelta(days=1))
    product=bdp.sized_product(cur,chain.base.SIZE,'BE-OPEN-'+uuid.uuid4().hex[:8])
    target=bdp.sized_product(cur,chain.base.SIZE,'BE-NEW-'+uuid.uuid4().hex[:8]);opening=str(uuid.uuid4())
    cur.execute("insert into erp.opening_balance_headers(id,opening_number,opening_date,status,created_by) values(%s,%s,%s,'DRAFT',%s)",
      (opening,'BE-OPEN-'+opening,day,chain.base.OPERATOR_APP))
    cur.execute("insert into erp.opening_balance_items(opening_id,balance_type,product_id,location_id,qty,unit_cost_snapshot,quality_grade,hpp_input_method) values(%s,'FINISHED_GOODS',%s,%s,10,10.01,'GRADE_A','MANUAL')",
      (opening,product,chain.base.LOCATION))
    bdp.internal(cur,'post_opening_balance',opening)
    lot=one(cur,"select id::text from erp.fg_lots where product_id=%s and lot_origin='OPENING'",product)
    payload=dict(source_lot_id=lot,target_product_id=target,location_id=chain.base.LOCATION,qty_pcs=6,
      physical_at=bdp.iso(chain.production.at(day+timedelta(days=1),9)),reason='BE opening source relabel',expected_version='before')
    if not installed(cur):return bdp.no_route(cur,lambda:be(cur,'POST',payload))
    payload['expected_version']=one(cur,'select erp.be_source_revision_v1(%s,%s)',lot,chain.base.LOCATION)
    truth=bdp.all_truth(cur);result=be(cur,'POST',payload);dest=result['destination_lot_id']
    target_values=q(cur,'select * from erp.compute_non_po_product_hpp_targets_v2620f(%s)',target)[0]
    target_book=q(cur,'select * from erp.compute_non_po_product_hpp_book_v2620f(%s)',target)[0]
    source_values=q(cur,'select * from erp.compute_non_po_product_hpp_targets_v2620f(%s)',product)[0]
    source_book=q(cur,'select * from erp.compute_non_po_product_hpp_book_v2620f(%s)',product)[0]
    new_truth=bdp.all_truth(cur);quantities=(qty(cur,lot),qty(cur,dest))
    be(cur,'REVERSE',dict(conversion_id=result['conversion_id'],reason='BE opening conversion inverse'))
    return verdict(dict(physical=quantities==(4,6),source_target=source_values==source_book and source_values[0]==bdp.D('40.04'),
      destination_target=target_values==target_book and target_values[0]==bdp.D('60.06'),
      truth=bdp.truth_quiet(truth,new_truth),inverse=qty(cur,lot)==10 and qty(cur,dest)==0),source=source_values,target=target_values)

def rework_new_sku(cur,today):
    import cp6_av_probe as avp
    f=avp.rework_ready(cur,today-timedelta(days=1))
    if not installed(cur):return bdp.no_route(cur,lambda:be(cur,'SAVE_REWORK',dict(reason='BE rework new SKU')))
    original=q(cur,'select vendor_id,physical_sent_at,return_fg_location_id from erp.rework_orders where id=%s',f['order'])[0]
    chain.bs_action(cur,'SAVE_REWORK',dict(id=f['order'],action='CANCEL',change_reason='Fixture replace unbound draft'),chain.version(cur,'rework_orders',f['order']))
    api.admin(cur);target=bdp.sized_product(cur,chain.base.SIZE,'BE-REWORK-'+uuid.uuid4().hex[:8])
    bom=one(cur,'select id::text from erp.accessory_bom_versions where product_id=%s and is_active',f['product'])
    order=dict(rework_number='BE-R-'+uuid.uuid4().hex[:20],bs_case_id=str(f['bs']),destination_type='LAUNDRY',contractor_id=None,
      vendor_id=str(original[0]),qty_sent=4,physical_sent_at=original[1].isoformat(),status='IN_PROGRESS',return_fg_location_id=str(original[2]),
      accessory_bom_version_id=bom,accessory_bom_item_ids=[],components=[])
    made=be(cur,'SAVE_REWORK',dict(order=order,target_product_id=target,reason='BE same construction new SKU'))
    rework=made['rework_id'];v=chain.version(cur,'rework_orders',rework);key=str(uuid.uuid4())
    payload=dict(rework_order_id=rework,qty_good=2,qty_bs=2,completed_at=bdp.iso(chain.production.at(f['day'],16)),
      return_fg_location_id=str(original[2]),change_reason='BE two QC-good and two BS')
    # One actual completion, then an identical native request replay.
    first=chain.bs_action(cur,'COMPLETE_REWORK',payload,v,key=key)
    again=chain.bs_action(cur,'COMPLETE_REWORK',payload,v,key=key)
    source=one(cur,'select good_fg_lot_id::text from erp.rework_orders where id=%s',rework)
    destinations=q(cur,"select a.destination_lot_id::text from erp.be_conversion_sources_v1 s join erp.product_conversion_allocations a on a.conversion_id=s.conversion_id where s.rework_id=%s",rework)
    dest=destinations[0][0] if len(destinations)==1 else None
    result=verdict(dict(one_conversion=len(destinations)==1,good_once=qty(cur,source)==0 and dest is not None and qty(cur,dest)==2,
      target=dest is not None and one(cur,'select product_id::text from erp.fg_lots where id=%s',dest)==target,
      replay=first.get('result')==again.get('result')),rework=rework,destinations=destinations)
    chain.bs_action(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=rework,change_reason='BE inverse atomic target'),chain.version(cur,'rework_orders',rework))
    result['checks']['inverse']=qty(cur,source)==0 and qty(cur,dest)==0
    result['status']='PASS' if all(result['checks'].values()) else 'FAIL'
    return result

def redye_fixture(cur,today,known=True):
    import cp6_av_probe as avp
    f=avp.rework_ready(cur,today-timedelta(days=1));api.admin(cur)
    chain.bs_action(cur,'SAVE_REWORK',dict(id=f['order'],action='CANCEL',change_reason='BE paid attempt replaces unbound fixture'),chain.version(cur,'rework_orders',f['order']))
    api.admin(cur);process=one(cur,"insert into erp.wash_processes(process_code,process_name) values(%s,'BE real redye') returning id::text",'BE-'+uuid.uuid4().hex[:12])
    target=bdp.sized_product(cur,chain.base.SIZE,'BE-DYE-'+uuid.uuid4().hex[:8])
    if known:bdp.process_rate(cur,dict(vendor=chain.base.VENDOR,process=process,start=chain.production.at(f['day'],13)),'50.00')
    api.admin(cur);bom=one(cur,'select id::text from erp.accessory_bom_versions where product_id=%s and is_active',f['product'])
    order=dict(rework_number='BE-DYE-'+uuid.uuid4().hex[:15],bs_case_id=str(f['bs']),destination_type='LAUNDRY',contractor_id=None,
      vendor_id=chain.base.VENDOR,qty_sent=4,physical_sent_at=bdp.iso(chain.production.at(f['day'],14)),status='IN_PROGRESS',return_fg_location_id=chain.base.LOCATION,
      accessory_bom_version_id=bom,accessory_bom_item_ids=[],components=[])
    made=be(cur,'SAVE_REDYE',dict(order=order,target_product_id=target,wash_process_id=process,price_status='KNOWN' if known else 'UNKNOWN',reason='BE real redye new colour'))
    rid=made['rework_id'];po=one(cur,'select po_id::text from erp.bs_cases where id=%s',f['bs'])
    chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=4,qty_bs=0,completed_at=bdp.iso(chain.production.at(f['day'],16)),return_fg_location_id=chain.base.LOCATION,change_reason='BE actual four returned'),chain.version(cur,'rework_orders',rid))
    dest=one(cur,'select a.destination_lot_id::text from erp.be_conversion_sources_v1 x join erp.product_conversion_allocations a on a.conversion_id=x.conversion_id where x.rework_id=%s',rid)
    return dict(f,redye=rid,target=target,dest=dest,po=po,vendor=chain.base.VENDOR)

def redye_invoice(cur,today):
    if not installed(cur):return bdp.no_route(cur,lambda:be(cur,'SAVE_REDYE',dict(reason='BE source not installed')))
    f=redye_fixture(cur,today);before=bdp.lot_value(cur,f['dest']);truth=bdp.all_truth(cur)
    bdp.invoice_policies(cur,after='CORRECTION_DOCUMENT');api.admin(cur)
    sale=bdp.sell(cur,f,f['target'],1,17);sale_snapshot=one(cur,'select sum(total_hpp) from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id=%s)',sale)
    fg0=bdp.gl(cur,'FG_INVENTORY');cogs0=bdp.gl(cur,'COGS');ap0=bdp.D(bdp.ap(cur,f['vendor']))
    payload=dict(vendor_id=f['vendor'],invoice_number='BEI-'+uuid.uuid4().hex[:10],invoice_date=str(f['day']),header_total='240.00',
      lines=[dict(line_kind='BILL',rework_service_id=f['redye'],category='GOOD',qty=4,amount='240.00')])
    draft=bdp.bd(cur,'SAVE_INVOICE_DRAFT',payload);posted=bdp.post_draft(cur,draft)
    snapshot('bd',bdp.bd_ws(cur,dict(vendor_id=f['vendor'])))
    cost=one(cur,'select erp.be_redye_cost_v1(%s)',f['redye']);accrual=one(cur,'select erp.be_redye_accrual_v1(%s)',f['po'])
    again=bdp.bd(cur,'SAVE_INVOICE_DRAFT',dict(payload,invoice_number='BE-OVER-'+uuid.uuid4().hex[:10]))
    over=refused(cur,lambda:bdp.post_draft(cur,again),'BD_INVOICE_CAPACITY')
    return verdict(dict(source_cost=cost==240,estimate_replaced=accrual==0,lot_delta=bdp.lot_value(cur,f['dest'])-before==40,
      fg_delta=bdp.gl(cur,'FG_INVENTORY')-fg0==30,cogs_delta=bdp.gl(cur,'COGS')-cogs0==10,
      ap_once=bdp.D(bdp.ap(cur,f['vendor']))-ap0==240,over=over['ok'],truth=bdp.truth_quiet(truth,bdp.all_truth(cur)),
      snapshot=one(cur,'select sum(total_hpp) from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id=%s)',sale)==sale_snapshot),
      cost=str(cost),accrual=str(accrual),fg_delta=str(bdp.gl(cur,'FG_INVENTORY')-fg0),cogs_delta=str(bdp.gl(cur,'COGS')-cogs0),refusals=[over])

def redye_unknown(cur,today):
    if not installed(cur):return bdp.no_route(cur,lambda:be(cur,'SAVE_REDYE',dict(reason='BE source not installed')))
    f=redye_fixture(cur,today,False);before=bdp.lot_value(cur,f['dest'])
    blocked=one(cur,"select count(*) from erp.period_blockers_v1(%s,%s) where code='BE_REDYE_PRICE_UNKNOWN'",f['day'],f['day'])
    unknown=one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',f['dest'])
    key=str(uuid.uuid4());p=dict(service_id=f['redye'],rate='50.00',reason='BE vendor price first known')
    first=be(cur,'SET_REDYE_PRICE',p,key);again=be(cur,'SET_REDYE_PRICE',p,key)
    overwrite=refused(cur,lambda:be(cur,'SET_REDYE_PRICE',dict(p,rate='60.00')),'BE_PRICE_ALREADY_KNOWN')
    cleared=one(cur,"select count(*) from erp.period_blockers_v1(%s,%s) where code='BE_REDYE_PRICE_UNKNOWN'",f['day'],f['day'])
    return verdict(dict(unknown=unknown and blocked==1,cleared=cleared==0,price_added=bdp.lot_value(cur,f['dest'])-before==200,
      replay=first==again,overwrite=overwrite['ok']),refusals=[overwrite])

PLAN=[('BE01:SELECTED_LOT_REPLAY_REVERSE','NO_ROUTE',conversion_roundtrip),('BE01:CAPACITY_STALE_NO_UNSOURCED_COST','NO_ROUTE',refusals),
      ('BE01:ACTUAL_ACCESSORY_COST_ONCE_AND_INVERSE','NO_ROUTE',actual_usage),
      ('BE01:OPENING_SOURCE_VALUE_AND_INVERSE','NO_ROUTE',nonpo_roundtrip),
      ('BE02:REWORK_NEW_SKU_ATOMIC_REPLAY_INVERSE','NO_ROUTE',rework_new_sku),
      ('BE03:REAL_SERVICE_INVOICE_SOLD_VARIANCE','NO_ROUTE',redye_invoice),('BE03:UNKNOWN_PRICE_CLOSE_REPLAY','NO_ROUTE',redye_unknown)]
def cases(cur,today):return [(key,lambda f=fn:f(cur,today)) for key,_,fn in PLAN]

def run(phase):
    global WS
    WS=OUT/('workspace_'+phase);WS.mkdir(parents=True,exist_ok=True)
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
        if phase=='after':
            parsed=subprocess.run(['node',str(build.ROOT/'scripts/cp6_be_workspace_parse.mjs'),str(WS)],capture_output=True,text=True,cwd=build.ROOT)
            try:report['workspace_parse']=json.loads(parsed.stdout.strip().splitlines()[-1])
            except (ValueError,IndexError):report['workspace_parse']=dict(error=(parsed.stderr or parsed.stdout)[-2000:])
            if parsed.returncode:report['mismatch']['WORKSPACE_PARSE']=dict(expected='PASS',actual=report['workspace_parse'])
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
