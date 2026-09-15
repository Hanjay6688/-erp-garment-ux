#!/usr/bin/env python3
"""Close admission, drain, restore AD to all 533 functions / 218 tables of AC."""
from pathlib import Path
import json,os,traceback
import psycopg
import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620ad_runtime as runtime
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

ROOT=Path('cp6-proof/writer-ad')
REPORT=ROOT/'AD_EXACT_AC_RESTORE.json'

def normalized(x):return json.loads(json.dumps(x,default=str))

def run():
    head,tree=runtime.verify_audit_source()
    if os.environ.get('PGURL')!='postgresql://postgres:postgres@127.0.0.1:54322/postgres':raise AssertionError('AD_EXACT_DISPOSABLE_RESTORE_REQUIRED')
    if os.environ.get('CP6_MAINTENANCE_CONFIRM_DATABASE')!='postgres' or os.environ.get('CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE')!='postgres':raise AssertionError('AD_EXPLICIT_DISPOSABLE_SYSTEM_DATABASE_REQUIRED')
    with psycopg.connect(os.environ['PGURL']) as conn,conn.cursor() as cur:
        if len(runtime.verified_successor(cur))!=274:raise AssertionError('AD_RESTORE_SOURCE_MISMATCH')
    result=maintenance.run_maintenance_rollback(target_name='AD',target_pgurl=os.environ['PGURL'],
        maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'],report_path=ROOT/'AD_MAIN_MAINTENANCE_ROLLBACK.json',
        drain_timeout=10,natural_grace=0,terminate_after_grace=True)
    required={'ENDPOINT_VERIFIED','CAPSULE_VERIFIED','ADMISSION_CLOSED','DRAINED','ROLLBACK_STARTED','ROLLBACK_COMMITTED','PREDECESSOR_VERIFIED','ADMISSION_REOPENED'}
    if not required.issubset({s['phase'] for s in result['phases']}):raise AssertionError('AD_MAINTENANCE_PHASES_INCOMPLETE')
    with psycopg.connect(os.environ['PGURL']) as conn,conn.cursor() as cur:
        runtime.verify_predecessor(cur)
        catalog=normalized(function_catalog(cur));boundary=normalized(snapshot(cur))
        before_catalog=json.loads((ROOT/'AC_COMPLETE_CATALOG.json').read_text())
        before_boundary=json.loads((ROOT/'AC_COMPLETE_BOUNDARY.json').read_text())
        exact=catalog==before_catalog and boundary==before_boundary
        users=cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
    r={'status':'PASS' if exact and len(catalog)==533 and len(boundary['tables'])==218 and users==(0,0) else 'FAIL',
       'head':head,'tree':tree,'restored_candidate':runtime.AC_HEAD,'functions':len(catalog),'tables':len(boundary['tables']),
       'full_function_owner_acl_and_data_boundary_exact':exact,'auth_users':users[0],'app_users':users[1],
       'new_edge':'AD -> AC','older_ladder':'REUSED Native200 AC -> CP4.5; source unchanged','production_go':False}
    REPORT.write_text(json.dumps(r,indent=2)+'\n');return r

if __name__=='__main__':
    try:r=run()
    except Exception as exc:r={'status':'FAIL','error':str(exc),'traceback':traceback.format_exc(),'production_go':False};ROOT.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r));raise SystemExit(0 if r['status']=='PASS' else 1)
