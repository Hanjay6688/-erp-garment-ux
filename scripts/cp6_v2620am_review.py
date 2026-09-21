#!/usr/bin/env python3
"""Fresh AM regression using unchanged, hash-pinned AL business assertions."""
from pathlib import Path
import argparse,hashlib,json,os,traceback
import psycopg
import cp6_v2620am_runtime as runtime
import cp6_v2620al_review as al
import cp6_v2620al_import_review as imports
import cp6_v2620al_value_review as values
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

ROOT=Path('cp6-proof/writer-am')
URL,ADMIN=al.URL,al.ADMIN
actors,original=al.actors,al.original
normal=al.normal


def save(name,data):
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/(name+'.json')).write_text(json.dumps(data,indent=2,default=str)+'\n')


def bind():
    evidence=json.loads((runtime.ROOT/'docs/evidence/cp6-am-regression-oracle-pins.json').read_text())
    for name,expected in evidence['sha256'].items():
        assert hashlib.sha256((runtime.ROOT/'scripts'/(name+'.py')).read_bytes()).hexdigest()==expected,name
    for module in (al,imports,values):
        module.runtime=runtime;module.ROOT=ROOT
    def am_save(name,data):
        save(name,{**data,'runtime_generation':'AM','regression_oracles':evidence,
            'independent_acceptance':False})
    al.save=am_save
    return evidence


def install():
    head,tree=runtime.verify_audit_source()
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta'")
        runtime.verify_predecessor(cur)
        save('AL_BASELINE',dict(catalog=function_catalog(cur),boundary=snapshot(cur)))
        cur.execute('set local role postgres')
        cur.execute(original.ah.ag.sql_body(runtime.MIGRATION),prepare=False)
        cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',
            (runtime.STAMP,runtime.NAME,[runtime.MIGRATION.read_text()]))
        assert len(runtime.verified_successor(cur))==690
        conn.commit()
    result=dict(status='PASS',head=head,tree=tree,functions=533,objects=690,production_go=False)
    save('INSTALL',result);return result


def regression(phase):
    evidence=bind()
    if phase=='business':result=al.run_cases();name='BUSINESS'
    elif phase=='imports':result=imports.run(False);name='IMPORT'
    elif phase=='values':result=values.run(False);name='VALUES'
    elif phase=='concurrency':result=al.concurrency();name='CONCURRENCY'
    else:
        if phase=='import-concurrency':
            import cp6_v2620al_import_concurrency as module
        else:
            assert phase=='direct-concurrency'
            import cp6_v2620al_direct_concurrency as module
        module.ROOT=ROOT/phase
        result=module.run();name=phase+'/manifest'
    result.update(runtime_generation='AM',regression_oracles=evidence,independent_acceptance=False)
    save(name,result);return result

def rollback():
 from importlib.util import spec_from_file_location,module_from_spec
 spec=spec_from_file_location('am_maintenance_controller',runtime.ROOT/'scripts/cp6_preuse_rollback_maintenance.py')
 maintenance=module_from_spec(spec);spec.loader.exec_module(maintenance)
 maintenance.TARGETS['AM']['rollback']=runtime.reviewed_local_rollback()
 before=json.loads((ROOT/'AL_BASELINE.json').read_text())
 controls={
  'FUNCTION':("alter function erp.post_material_transfer_v2(uuid,uuid,bigint,text) set work_mem='64MB'",'AM_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
  'ACL':('grant execute on function erp.post_material_transfer_v2(uuid,uuid,bigint,text) to anon','AM_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
  'OWNER':('alter function erp.post_material_transfer_v2(uuid,uuid,bigint,text) owner to supabase_admin','AM_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
  'EXTRA_TABLE':('create table erp.cp6_am_unexpected(id integer)','AM_BOUNDARY_SNAPSHOT_MISMATCH'),
  'MISSING_TABLE':('drop table erp.cp6_v2620ac_rollback_capsule','AM_BOUNDARY_SNAPSHOT_MISMATCH'),
  'POST_USE':("insert into erp.locations(location_code,location_name,location_type) values('AM-POST-USE','AM probe','FG_WAREHOUSE')",'AM_POST_USE_ROLLBACK_REFUSED'),
  'CAPSULE':(f"update {runtime.CAPSULE} set object_definition=object_definition||E'\\n-- changed'",'AM_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
  'PLATFORM':(f"update supabase_migrations.schema_migrations set statements=array['wrong'] where name='{runtime.NAME}'",'AM_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR')}
 atomic={}
 with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta'");assert len(runtime.verified_successor(cur))==690
  for name,(statement,expected) in controls.items():
   boundary,catalog=actors.boundary(cur),function_catalog(cur);cur.execute('savepoint am_refusal')
   try:
    cur.execute(statement)
    row=original.ah.ag.expected_refusal(cur,lambda:cur.execute(original.ah.ag.sql_body(runtime.ROLLBACK),prepare=False),expected)
    row['status']='PASS'
   except Exception as exc:row=dict(status='FAIL',error=str(exc))
   finally:cur.execute('rollback to savepoint am_refusal;release savepoint am_refusal')
   row['boundary_restored']=actors.boundary(cur)==boundary and function_catalog(cur)==catalog
   atomic[name]=row
  conn.rollback()
 save('ROLLBACK_REFUSALS',dict(cases=atomic,production_go=False))
 assert all(x['status']=='PASS' and x['boundary_restored'] for x in atomic.values()),atomic
 operation=maintenance.run_maintenance_rollback(target_name='AM',target_pgurl=URL,
  maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'],report_path=ROOT/'MAINTENANCE.json',drain_timeout=10,natural_grace=0,terminate_after_grace=True)
 with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta'");runtime.verify_predecessor(cur)
  actual=normal(dict(catalog=function_catalog(cur),boundary=snapshot(cur)))
 assert before==actual,'AM rollback did not restore the exact AL boundary'
 result=dict(status='PASS',functions=len(actual['catalog']),tables=len(actual['boundary']['tables']),full_boundary_exact=True,operation=operation,production_go=False)
 save('EXACT_AL_RESTORE',result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase',required=True,choices=('install','business','imports','values','concurrency','import-concurrency','direct-concurrency','rollback'))
    phase=parser.parse_args().phase
    try:
        assert os.environ['PGURL']==URL and os.environ['CP6_AI_INDEPENDENT_CONFIRM']=='postgres'
        result=install() if phase=='install' else rollback() if phase=='rollback' else regression(phase)
    except Exception as exc:
        result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc(),production_go=False)
        save(phase.upper()+'_FAILURE',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','operation','planned_case_ids','reused_evidence','regression_oracles')},default=str))
    hold=phase=='business' and result['status']=='HOLD' and result.get('counts')==dict(PASS=179,CONTROL_PASS=39,BUG_PROVEN=0,GAP_PROVEN=0,DATE_POLICY_REVIEW_REQUIRED=12,INCOMPLETE=0,FAIL=0)
    raise SystemExit(0 if hold or result['status'] in ('PASS','WRITER_PASS','PASS_REVIEWED_SCOPE') else 1)
