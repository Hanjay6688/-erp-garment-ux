#!/usr/bin/env python3
"""Run the same whole-family oracle before/after AD on one disposable engine.

Imported rows are synthetic, already validated staging fixtures. Actual
prepare/post/finalize calls use authenticated OWNER sessions. This does not
claim CSV parsing, signed HTTP, or browser coverage.
"""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
import argparse,hashlib,json,os,traceback,uuid
import psycopg
import cp6_ac_independent_audit as common
import cp6_v2620ad_runtime as runtime
import cp6_v2620ac_runtime as ac
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

ROOT=Path('cp6-proof/writer-ad')
CHECK='V2620AD_OPENING_MATERIAL_TIMELINE_MISMATCH'
actors,base,prior=common.actors,common.base,common.prior
one=common.one

def persist(name,r):
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/(name+'.json')).write_text(json.dumps(r,indent=2,default=str)+'\n')

def body(path):
    s=path.read_text()
    assert s.count('\nbegin;\n')==1 and s.endswith('commit;\n')
    return s.replace('\nbegin;\n','\n',1).removesuffix('commit;\n')

def expected_refusal(cur,sql,expected,ordinary=False):
    actors.admin(cur);before=actors.boundary(cur)
    cur.execute('savepoint ad_expected_refusal')
    error=None
    try:
        if ordinary:actors.owner(cur)
        cur.execute(sql,prepare=False)
    except psycopg.Error as exc:error=str(exc)
    finally:
        cur.execute('rollback to savepoint ad_expected_refusal');actors.admin(cur);cur.execute('release savepoint ad_expected_refusal')
    restored=actors.boundary(cur)==before
    if error is None or expected not in error or not restored:raise AssertionError(f'AD_REFUSAL_FAILED:{expected}:{error}:{restored}')
    return {'status':'PASS','expected_error':expected,'error':error,'boundary_restored':restored}

def owner_report(cur,day):
    actors.owner(cur)
    r=one(cur,'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',(day,day,day))
    checks=cur.execute('select check_name,severity,issue_count,details from erp.run_v268_financial_report_checks() where check_name=%s',(CHECK,)).fetchall()
    actors.admin(cur)
    return {'data_confidence':r['data_confidence'],'ad_checks':checks}

def material_evidence(cur,r,day,phase):
    material=r['material_id'];e={}
    e['report']=owner_report(cur,day)
    e['checkpoints']={}
    for date,qty,cost in ((day-timedelta(days=1),0,0),(day,10,Decimal('1.25'))):
        cur.execute('select erp.refresh_material_cost_checkpoint(%s,%s)',(material,date))
        row=cur.execute('select checkpoint_date,stock_qty,moving_average_cost from erp.material_cost_checkpoints where material_id=%s',(material,)).fetchone()
        e['checkpoints'][str(date)]={'actual':row,'expected':[date,qty,cost],'matches':row==(date,qty,cost)}
    journal_total=one(cur,"select sum(l.debit) from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_type='OPENING_BALANCE' and j.source_id=%s",(r['opening_id'],))
    if journal_total!=Decimal('12.50'):raise AssertionError('OPENING_EXACT_MONEY_CHANGED')
    e['journal_debits']=journal_total
    e['replay']=expected_refusal(cur,"select erp.post_opening_balance('"+str(r['opening_id'])+"'::uuid)",'Opening balance must be DRAFT',ordinary=True)
    strict=(r['timestamp_matches_day_start'] and all(v['qty']==v['expected_qty'] for v in r['stock_cutoffs'].values())
            and all(v['matches'] for v in e['checkpoints'].values()))
    if phase=='successor':
        if e['report']['data_confidence']['status']!='READY':raise AssertionError('AD_FALSE_BLOCKED_NORMAL_OPENING:'+json.dumps(e['report'],default=str))
        if len(e['report']['ad_checks'])!=1 or e['report']['ad_checks'][0][2]!=0:raise AssertionError('AD_NORMAL_DETECTOR_NOT_ZERO')
    if phase=='predecessor' and r['zone']=='Asia/Tokyo':
        e['preexisting_refusal']=expected_refusal(cur,body(runtime.MIGRATION),'AD_PREEXISTING_OPENING_TIMELINE_REVIEW_REQUIRED')
    e['strict_partition_matches']=strict
    return e

def run_family(phase):
    head,tree=runtime.verify_audit_source()
    expected_url='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
    if os.environ.get('PGURL')!=expected_url or os.environ.get('CP6_AD_PROOF_CONFIRM')!='postgres':raise AssertionError('AD_EXACT_DISPOSABLE_TARGET_REQUIRED')
    specs=[(kind,route,z) for kind in ('FABRIC','FABRIC_ROLL','ACCESSORY') for route in ('DIRECT','IMPORT') for z in common.ZONES]
    specs += [(kind,'DIRECT',z) for kind in ('FINISHED_GOODS','FINISHED_GOODS_PRICE','BS','BS_PRODUCT','ATTENDANCE') for z in common.ZONES]
    r={'format':'CP6_AD_FAMILY_PROOF_V1','status':'INCOMPLETE','phase':phase,'head':head,'tree':tree,'business_predecessor_head':runtime.AC_HEAD,
       'run_id':os.environ.get('GITHUB_RUN_ID'),'expected_cases':len(specs),'cases':{},'production_go':False,
       'synthetic_jwt_sql':True,'signed_http_ui_proven':False,'import_staging_prevalidated_fixture':True,
       'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    persist(phase,r)
    with psycopg.connect(expected_url.replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
        cur.execute("set local statement_timeout='180s';set local lock_timeout='8s';set local timezone='Asia/Jakarta'")
        untouched=actors.boundary(cur);catalog=function_catalog(cur);boundary=snapshot(cur)
        if phase=='predecessor':
            runtime.verify_predecessor(cur)
            if len(catalog)!=533 or len(boundary['tables'])!=218:raise AssertionError('AD_AC_FULL_CATALOG_CARDINALITY')
            persist('AC_COMPLETE_CATALOG',catalog);persist('AC_COMPLETE_BOUNDARY',boundary)
        else:
            if len(runtime.verified_successor(cur))!=274:raise AssertionError('AD_INSTALLED_RUNTIME_NOT_274')
        usage=one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
        if not usage:cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':base.OPERATOR_AUTH,'role':'authenticated'}),))
        base.load_fixture_foundation(cur);actors.admin(cur)
        day=one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
        prior.set_open_period(cur,day-timedelta(days=2))
        for kind,route,zone in specs:
            key=kind+':'+route+':'+zone;actors.admin(cur)
            before=actors.boundary(cur);cur.execute('savepoint ad_family_case')
            try:
                case=common.attendance_case(cur,zone,day) if kind=='ATTENDANCE' else common.opening_case(cur,kind,zone,day,route)
                if case.get('material_id'):
                    case['downstream']=material_evidence(cur,case,day,phase)
                    case['status']='CONTROL_PASS' if case['downstream']['strict_partition_matches'] else 'COUNTEREXAMPLE'
                if phase=='successor' and case['status']!='CONTROL_PASS':raise AssertionError('AD_ORIGINAL_COUNTEREXAMPLE_SURVIVED')
            except Exception as exc:
                case={'status':'INCOMPLETE','error':str(exc),'sqlstate':getattr(exc,'sqlstate',None),'traceback':traceback.format_exc()}
            finally:
                cur.execute('rollback to savepoint ad_family_case');actors.admin(cur);cur.execute('release savepoint ad_family_case')
            case['full_boundary_restored']=actors.boundary(cur)==before
            if not case['full_boundary_restored']:case['status']='INCOMPLETE'
            r['cases'][key]=case;persist(phase,r);print(json.dumps({'phase':phase,'case':key,'status':case['status'],'error':case.get('error')}),flush=True)
        conn.rollback();r['entire_unseeded_boundary_restored']=actors.boundary(cur)==untouched
        r['schema_usage_restored']=one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")==usage;conn.rollback()
    r['incomplete']=sum(c['status']=='INCOMPLETE' for c in r['cases'].values())
    r['counterexamples']=sum(c['status']=='COUNTEREXAMPLE' for c in r['cases'].values())
    r['controls']=sum(c['status']=='CONTROL_PASS' for c in r['cases'].values())
    r['actual_day_drift']=sum(c.get('expected_business_date')!=c.get('actual_business_date') for c in r['cases'].values() if c.get('material_id'))
    if r['incomplete']==0 and r['entire_unseeded_boundary_restored'] and r['schema_usage_restored'] and len(r['cases'])==55:
        if phase=='predecessor' and r['counterexamples']==24 and r['actual_day_drift']==12:r['status']='PASS_PREDECESSOR_NEGATIVE_CONTROL_QUALIFIED'
        if phase=='successor' and r['counterexamples']==0:r['status']='PASS_55_FAMILY_CASES'
    persist(phase,r);return r

def detector_controls():
    """Reintroduce the exact old writer transactionally; never edit posted rows."""
    result={'status':'INCOMPLETE','cases':{},'production_go':False}
    predecessor=next(f[1] for f in json.loads(Path('docs/evidence/cp6-ad-predecessor-functions.json').read_text())['functions'] if f[0]=='erp.post_opening_balance(uuid)')
    with psycopg.connect(os.environ['PGURL'].replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='180s';set local lock_timeout='8s'")
        untouched=actors.boundary(cur);assert len(runtime.verified_successor(cur))==274
        if not one(cur,"select has_schema_privilege('authenticated','erp','USAGE')"):cur.execute('grant usage on schema erp to authenticated')
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':base.OPERATOR_AUTH,'role':'authenticated'}),))
        base.load_fixture_foundation(cur);actors.admin(cur)
        day=one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3);prior.set_open_period(cur,day-timedelta(days=2))
        for kind in ('FABRIC','FABRIC_ROLL','ACCESSORY'):
            for route in ('DIRECT','IMPORT'):
                name=kind+':'+route;actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint ad_detector_control')
                try:
                    cur.execute(predecessor,prepare=False)
                    case=common.opening_case(cur,kind,'Asia/Tokyo',day,route)
                    assert case['status']=='COUNTEREXAMPLE'
                    report=owner_report(cur,day)
                    assert report['data_confidence']['status']=='BLOCKED' and len(report['ad_checks'])==1 and report['ad_checks'][0][2]==1,report
                    record={'status':'PASS','vulnerable_writer_reintroduced':True,'ordinary_posting_used':True,'report':report}
                except Exception as exc:record={'status':'FAIL','error':str(exc),'traceback':traceback.format_exc()}
                finally:cur.execute('rollback to savepoint ad_detector_control');actors.admin(cur);cur.execute('release savepoint ad_detector_control')
                record['full_boundary_restored']=actors.boundary(cur)==before
                if not record['full_boundary_restored']:record['status']='FAIL'
                result['cases'][name]=record;persist('DETECTOR_NEGATIVE_CONTROLS',result)
        conn.rollback();result['entire_boundary_restored']=actors.boundary(cur)==untouched;conn.rollback()
    if len(result['cases'])==6 and all(c['status']=='PASS' for c in result['cases'].values()) and result['entire_boundary_restored']:result['status']='PASS'
    persist('DETECTOR_NEGATIVE_CONTROLS',result);return result

def atomic_controls(phase):
    target=runtime.MIGRATION if phase=='admission' else runtime.ROLLBACK
    mutants={
      'FUNCTION_CONFIGURATION':("alter function erp.post_opening_balance(uuid) set work_mem='64MB'",'AD_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH' if phase=='admission' else 'AD_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
      'FUNCTION_ACL':('grant execute on function erp.post_opening_balance(uuid) to anon','AD_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH' if phase=='admission' else 'AD_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
      'FUNCTION_OWNER':('alter function erp.post_opening_balance(uuid) owner to supabase_admin','AD_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH' if phase=='admission' else 'AD_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
      'UNEXPECTED_TABLE':('create table erp.cp6_ad_unexpected(id integer)','AD_FULL_ERP_BOUNDARY_CARDINALITY' if phase=='admission' else 'AD_BOUNDARY_SNAPSHOT_MISMATCH'),
    }
    if phase=='admission':
        mutants['AC_PLATFORM_SOURCE']=("update supabase_migrations.schema_migrations set statements=array['wrong'] where name='erp_v2_6_20ac_cp6_temporal_surface_closure'",'AD_REQUIRES_EXACT_AC_PLATFORM_CAPSULES')
        mutants['SUCCESSOR_CAPSULE']=(f'create table {runtime.CAPSULE}(id integer)','AD_REQUIRES_EXACT_AC_WITHOUT_AD_RESIDUE')
    else:
        mutants['MISSING_TABLE']=('drop table erp.cp6_v2620ab_rollback_capsule','AD_BOUNDARY_SNAPSHOT_MISMATCH')
        mutants['POST_USE']=("insert into erp.locations(location_code,location_name,location_type) values('AD-ROLLBACK-PROBE','AD probe','FG_WAREHOUSE')",'AD_POST_USE_ROLLBACK_REFUSED')
        mutants['CAPSULE_DEFINITION']=(f"update {runtime.CAPSULE} set object_definition=object_definition||E'\\n-- corrupt'",'AD_TRUSTED_PREDECESSOR_PIN_MISMATCH')
        mutants['PLATFORM_SOURCE']=("update supabase_migrations.schema_migrations set statements=array['wrong'] where name='"+runtime.NAME+"'",'AD_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR')
    r={'status':'INCOMPLETE','phase':phase,'cases':{},'production_go':False}
    with psycopg.connect(os.environ['PGURL'].replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        for name,(mutation,error) in mutants.items():
            before=actors.boundary(cur);catalog=function_catalog(cur);cur.execute('savepoint ad_atomic')
            try:
                cur.execute(mutation)
                record=expected_refusal(cur,body(target),error)
            except Exception as exc:record={'status':'FAIL','error':str(exc),'traceback':traceback.format_exc()}
            finally:cur.execute('rollback to savepoint ad_atomic');cur.execute('release savepoint ad_atomic')
            record['entire_boundary_restored']=actors.boundary(cur)==before and function_catalog(cur)==catalog
            if not record['entire_boundary_restored']:record['status']='FAIL'
            r['cases'][name]=record;persist(phase+'_ATOMIC_CONTROLS',r)
        conn.rollback()
    if all(c['status']=='PASS' for c in r['cases'].values()):r['status']='PASS'
    persist(phase+'_ATOMIC_CONTROLS',r);return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['predecessor','successor','detector','admission','rollback'],required=True);args=p.parse_args()
    try:
        if os.environ.get('PGURL')!='postgresql://postgres:postgres@127.0.0.1:54322/postgres' or os.environ.get('CP6_AD_PROOF_CONFIRM')!='postgres':raise AssertionError('AD_EXACT_DISPOSABLE_TARGET_REQUIRED')
        runtime.verify_audit_source()
        r=run_family(args.phase) if args.phase in ('predecessor','successor') else detector_controls() if args.phase=='detector' else atomic_controls(args.phase)
    except Exception as exc:r={'status':'INCOMPLETE','error':str(exc),'traceback':traceback.format_exc(),'production_go':False};persist(args.phase+'_ERROR',r)
    print(json.dumps({k:v for k,v in r.items() if k!='cases'},default=str))
    raise SystemExit(0 if r['status'].startswith('PASS') else 1)
