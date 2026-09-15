#!/usr/bin/env python3
"""Independent AC audit of the date-to-instant family, on a disposable engine.

Business source is the separately checked-out immutable AC candidate. Every
case uses ordinary posting functions and reverts its complete boundary.
"""
from pathlib import Path
from datetime import datetime,time,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import hashlib,json,os,subprocess,traceback,uuid
import psycopg
import cp6_v2620ac_runtime as runtime
import cp6_x_independent_audit as actors
import cp6_z_expanded_integrity_audit as prior
import cp6_v2620e_counterexample_regression as base

HEAD='1bdca3766f7c9800d68295ff5122798060b8a05d'
TREE='334629c626257b8b713826f491cdf62385d5299b'
ZONES=('Asia/Jakarta','UTC','Asia/Tokyo','Pacific/Kiritimati','Etc/GMT+12')
JAKARTA=ZoneInfo('Asia/Jakarta')
REPORT=Path('cp6-proof/ac-independent/AC_DATE_TO_INSTANT_AUDIT.json')
one=base.one

def save(result):
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(result,indent=2,default=str)+'\n')

def opening_day_valid(day,physical,journal,kind):
    return physical.astimezone(JAKARTA).date()==day and (
        journal==[] if kind=='BS' else journal==[(day,day,'POSTED')])

def opening_case(cur,kind,zone,day):
    actors.admin(cur);actors.zone(cur,'Asia/Jakarta')
    h,item=uuid.uuid4(),uuid.uuid4()
    number='ACOP-'+h.hex[:20]
    material=product=None
    if kind in ('FABRIC','ACCESSORY'):
        material=prior.clone_material(cur,'date-to-instant')
        if kind=='ACCESSORY':
            category=one(cur,'select id from erp.accessory_categories order by id limit 1')
            if category is None:
                category=uuid.uuid4()
                cur.execute("insert into erp.accessory_categories(id,category_code,category_name,base_uom_code) values(%s,%s,'AC isolated accessory category','PCS')",(category,'AC-CAT-'+category.hex[:20]))
            cur.execute("update erp.materials set material_type='ACCESSORY',unit_code='PCS',accessory_category_id=%s where id=%s",(category,material))
    elif kind=='FINISHED_GOODS':
        product=base.create_product(cur,uuid.uuid4().hex[:16])
    location=uuid.uuid4()
    cur.execute('insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,%s,%s,true)',
                (location,'AC-AUD-'+location.hex[:16],'AC isolated opening',
                 'RAW_MATERIAL_WAREHOUSE' if material else 'FG_WAREHOUSE'))
    actors.owner(cur);actors.zone(cur,zone)
    cur.execute("insert into erp.opening_balance_headers(id,opening_number,opening_date,status) values(%s,%s,%s,'DRAFT')",(h,number,day))
    cur.execute('insert into erp.opening_balance_items(id,opening_id,balance_type,material_id,product_id,location_id,qty,unit_cost_snapshot,hpp_input_method) values(%s,%s,%s,%s,%s,%s,10,1.25,%s)',
                (item,h,'MATERIAL' if material else kind,material,product,location,'MANUAL'))
    cur.execute('select erp.post_opening_balance(%s)',(h,))
    actor=cur.execute('select current_user,session_user,erp.current_app_role()').fetchone()
    assert actor==('authenticated','authenticated','OWNER')
    # Posting ran under the ordinary owner. Read private evidence as auditor;
    # granting the caller ledger access would change the candidate's ACLs.
    actors.admin(cur)
    if material:
        movements=cur.execute("select physical_at,qty_signed,unit_cost_snapshot from erp.material_stock_movements where source_type='OPENING_BALANCE_ITEM' and source_id=%s order by id",(item,)).fetchall()
    elif product:
        movements=cur.execute("select physical_at,qty_signed,unit_hpp_snapshot from erp.fg_stock_movements where source_type='OPENING_BALANCE_ITEM' and source_id=%s order by id",(item,)).fetchall()
    else:
        movements=cur.execute("select physical_at,qty_pcs,0::numeric from erp.bs_cases where bs_number=%s",('OBS-'+number+'-'+str(item)[:8],)).fetchall()
    assert len(movements)==1 and Decimal(movements[0][1])==10
    physical,qty,cost=movements[0]
    expected_at=datetime.combine(day,time(0),tzinfo=JAKARTA)
    actual_day=physical.astimezone(JAKARTA).date()
    journal=cur.execute("select economic_date,transaction_date,status from erp.journal_entries where source_type='OPENING_BALANCE' and source_id=%s",(h,)).fetchall()
    if kind!='BS':assert len(journal)==1 and journal[0]==(day,day,'POSTED')
    snapshots={}
    if material:
        for label,at in (('prior_day_end',expected_at-timedelta(microseconds=1)),('opening_day_start',expected_at),('opening_day_end',expected_at+timedelta(days=1)-timedelta(microseconds=1))):
            q=one(cur,'select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s and physical_at<=%s',(material,at))
            snapshots[label]={'at':at,'qty':q,'expected_qty':0 if label=='prior_day_end' else 10}
    status='CONTROL_PASS' if opening_day_valid(day,physical,journal,kind) else 'COUNTEREXAMPLE'
    r={'status':status,'kind':kind,'zone':zone,'opening_id':h,'item_id':item,'actor':actor,'expected_business_date':day,'actual_business_date':actual_day,'expected_day_start':expected_at,'actual_physical_at':physical,'quantity':qty,'unit_cost':cost,'journal':journal,'stock_cutoffs':snapshots,'timestamp_matches_day_start':physical==expected_at,'classification':'OPENING_MATERIAL_BUSINESS_DAY_DRIFT' if status=='COUNTEREXAMPLE' else 'BUSINESS_DAY_CONTROL','severity':'P2' if status=='COUNTEREXAMPLE' else None}
    # A tampered observation is never written to business tables. This checks
    # that the independent date oracle cannot accept a deliberately wrong day.
    control_journal=[] if kind=='BS' else [(day,day,'POSTED')]
    assert opening_day_valid(day,expected_at,control_journal,kind)
    r['negative_control_wrong_day_rejected']=not opening_day_valid(day,expected_at-timedelta(days=1),control_journal,kind)
    assert r['negative_control_wrong_day_rejected']
    if kind!='BS':
        r['negative_control_wrong_journal_day_rejected']=not opening_day_valid(day,expected_at,[(day-timedelta(days=1),day,'POSTED')],kind)
        assert r['negative_control_wrong_journal_day_rejected']
    return r

def attendance_case(cur,zone,day):
    actors.admin(cur);actors.zone(cur,zone)
    contractor=uuid.UUID('a1000000-0000-0000-0000-000000000001')
    workers=cur.execute("select id from erp.contractor_workers where contractor_id=%s and pay_scheme in ('DAILY','HYBRID') and erp.worker_is_employed_on(id,%s)",(contractor,day)).fetchall()
    assert workers,'ATTENDANCE_CONTROL_REQUIRES_WORKERS'
    records=[dict(worker_id=str(w[0]),attendance_date=str(d),status='PRESENT') for d in (day,day+timedelta(days=1)) for w in workers]
    payload=dict(contractor_id=str(contractor),period_number='AC-AUD-ATT-'+uuid.uuid4().hex,period_start=str(day),period_end=str(day+timedelta(days=1)),pay_date=str(day+timedelta(days=2)),reason='AC independent calendar roundtrip',attendance=records)
    actors.owner(cur)
    draft=one(cur,'select erp.save_attendance_period_v1(%s::jsonb,%s,null,false)',(json.dumps(payload),uuid.uuid4()))
    posted=one(cur,'select erp.post_attendance_period_v1(%s,%s,%s,%s)',(draft['period_id'],'AC independent calendar roundtrip',uuid.uuid4(),int(draft['row_version'])))
    actor=cur.execute('select current_user,session_user,erp.current_app_role()').fetchone()
    assert actor==('authenticated','authenticated','OWNER')
    actors.admin(cur)
    actual=cur.execute('select worker_id,attendance_date,record_lifecycle from erp.attendance_records where attendance_period_id=%s order by worker_id,attendance_date',(draft['period_id'],)).fetchall()
    expected=sorted((str(w[0]),str(d),'POSTED') for d in (day,day+timedelta(days=1)) for w in workers)
    observed=sorted(tuple(map(str,row)) for row in actual)
    assert observed==expected and posted['status']=='POSTED'
    return {'status':'CONTROL_PASS','classification':'DATE_DOMAIN_SERIES_ROUND_TRIP','zone':zone,'actor':actor,'expected':expected,'actual':observed,'negative_control_missing_date_rejected':observed[:-1]!=expected}

def run():
    assert os.environ.get('PGURL')=='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
    assert os.environ.get('CP6_AC_INDEPENDENT_CONFIRM')=='postgres'
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==HEAD
    assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip()==TREE
    result={'format':'CP6_AC_INDEPENDENT_DATE_TO_INSTANT_V1','status':'INCOMPLETE','head':HEAD,'tree':TREE,'audit_harness_head':os.environ['CP6_AUDIT_HARNESS_HEAD'],'run_id':os.environ['GITHUB_RUN_ID'],'run_attempt':os.environ['GITHUB_RUN_ATTEMPT'],'production_go':False,'hosted_database_used':False,'synthetic_jwt_context':True,'http_ui_reachability_proven':False,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'expected_cases':25,'cases':{}}
    save(result)
    with psycopg.connect(os.environ['PGURL'].replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
        cur.execute("set local statement_timeout='90s';set local lock_timeout='8s';set local timezone='Asia/Jakarta'")
        before=actors.boundary(cur)
        installed=runtime.verified_successor(cur);assert len(installed)==272
        result['runtime_objects_verified']=len(installed);result['engine']=one(cur,'select version()')
        assert one(cur,"select current_setting('server_version')").startswith('17.6')
        usage=one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
        if not usage:cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':base.OPERATOR_AUTH,'role':'authenticated'}),))
        base.load_fixture_foundation(cur)
        actors.admin(cur)
        day=one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
        prior.set_open_period(cur,day-timedelta(days=2))
        specs=[(kind,z) for kind in ('FABRIC','ACCESSORY','FINISHED_GOODS','BS','ATTENDANCE') for z in ZONES]
        for kind,z in specs:
            actors.admin(cur);cur.execute('savepoint ac_independent_case');baseline=actors.boundary(cur)
            try:r=attendance_case(cur,z,day) if kind=='ATTENDANCE' else opening_case(cur,kind,z,day)
            except Exception as exc:r={'status':'INCOMPLETE','error':str(exc),'sqlstate':getattr(exc,'sqlstate',None),'traceback':traceback.format_exc()}
            finally:
                cur.execute('rollback to savepoint ac_independent_case');actors.admin(cur);cur.execute('release savepoint ac_independent_case')
            r['full_boundary_restored']=actors.boundary(cur)==baseline
            if not r['full_boundary_restored']:r['status']='INCOMPLETE'
            result['cases'][kind+':'+z]=r;save(result);print(json.dumps({'case':kind+':'+z,'status':r['status'],'error':r.get('error')}),flush=True)
        conn.rollback();result['entire_unseeded_runtime_restored']=actors.boundary(cur)==before
        result['schema_usage_restored']=one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")==usage
        conn.rollback()
    for label,status in (('controls','CONTROL_PASS'),('counterexamples','COUNTEREXAMPLE'),('incomplete','INCOMPLETE')):result[label]=sum(r['status']==status for r in result['cases'].values())
    if len(result['cases'])==25 and result['incomplete']==0 and result['entire_unseeded_runtime_restored'] and result['schema_usage_restored']:
        result['status']='FAIL_NEW_COUNTEREXAMPLE' if result['counterexamples'] else 'PASS_BOUNDED_INDEPENDENT_AUDIT'
    save(result);return result

if __name__=='__main__':
    try:r=run()
    except Exception as exc:
        r={'status':'INCOMPLETE','error':str(exc),'traceback':traceback.format_exc(),'production_go':False};save(r)
    print(json.dumps({k:v for k,v in r.items() if k!='cases'},default=str))
    raise SystemExit(0 if r['status']=='PASS_BOUNDED_INDEPENDENT_AUDIT' else 1 if r['status']=='FAIL_NEW_COUNTEREXAMPLE' else 2)
