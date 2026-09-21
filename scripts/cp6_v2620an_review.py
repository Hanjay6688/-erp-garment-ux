#!/usr/bin/env python3
"""AN installed reader verification and admission-closed exact AM restoration."""
from pathlib import Path
import argparse,importlib.util,json,os
import psycopg
import cp6_v2620an_runtime as runtime
import cp6_v2620am_review as prior
from cp6_v2620an_definitions import PRIVATE_ID,PUBLIC_ID
from cp6_v2620an_build_sql import LEGACY
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot
ROOT=Path('cp6-proof/writer-an')
URL,ADMIN=prior.URL,prior.ADMIN
normal=prior.normal


def save(name,data):
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/(name+'.json')).write_text(json.dumps(data,indent=2,default=str)+'\n')


def public_catalog(cur):
    return cur.execute("select p.oid::regprocedure::text,pg_get_functiondef(p.oid),p.proacl::text,pg_get_userbyid(p.proowner) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prokind='f' order by 1").fetchall()


def boundary(cur):return dict(catalog=function_catalog(cur),public_catalog=public_catalog(cur),boundary=snapshot(cur))


def install():
    head,tree=runtime.verify_audit_source()
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta'")
        runtime.verify_predecessor(cur);save('AM_BASELINE',boundary(cur))
        cur.execute('set local role postgres')
        cur.execute(prior.original.ah.ag.sql_body(runtime.MIGRATION),prepare=False)
        cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(runtime.STAMP,runtime.NAME,[runtime.MIGRATION.read_text()]))
        assert len(runtime.verified_successor(cur))==692
        conn.commit()
    result=dict(status='PASS',head=head,tree=tree,erp_functions=534,new_public_readers=1,objects=692,production_go=False)
    save('INSTALL',result);return result


def rollback():
    spec=importlib.util.spec_from_file_location('an_controller',runtime.ROOT/'scripts/cp6_preuse_rollback_maintenance.py')
    controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
    controller.TARGETS['AN']['rollback']=runtime.reviewed_local_rollback()
    baseline=json.loads((ROOT/'AM_BASELINE.json').read_text())
    controls={
        'PRIVATE_FUNCTION':(f"alter function {PRIVATE_ID} set work_mem='64MB'",'AN_NEW_READER_DRIFT'),
        'PUBLIC_FUNCTION':(f"alter function {PUBLIC_ID} set work_mem='64MB'",'AN_NEW_READER_DRIFT'),
        'PUBLIC_ACL':(f'grant execute on function {PUBLIC_ID} to anon','AN_NEW_READER_DRIFT'),
        'PRIVATE_ACL':(f'grant execute on function {PRIVATE_ID} to authenticated','AN_NEW_READER_DRIFT'),
        'OWNER':(f'alter function {PUBLIC_ID} owner to supabase_admin','AN_NEW_READER_DRIFT'),
        'LEGACY':(f"alter function {LEGACY} set work_mem='64MB'",'AN_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
        'EXTRA_TABLE':('create table erp.an_unexpected(id integer)','AN_BOUNDARY_SNAPSHOT_MISMATCH'),
        'MISSING_TABLE':('drop table erp.cp6_v2620ac_rollback_capsule','AN_BOUNDARY_SNAPSHOT_MISMATCH'),
        'POST_USE':("insert into erp.locations(location_code,location_name,location_type) values('AN-POST-USE','AN probe','FG_WAREHOUSE')",'AN_POST_USE_ROLLBACK_REFUSED'),
        'CAPSULE':(f"update {runtime.CAPSULE} set object_definition=object_definition||E'\\n-- changed'",'AN_TRUSTED_PREDECESSOR_PIN_MISMATCH'),
        'PLATFORM':(f"update supabase_migrations.schema_migrations set statements=array['wrong'] where name='{runtime.NAME}'",'AN_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR'),
    }
    results={}
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta'");assert len(runtime.verified_successor(cur))==692
        for name,(statement,expected) in controls.items():
            before=boundary(cur);cur.execute('savepoint an_refusal')
            try:
                cur.execute(statement)
                row=prior.original.ah.ag.expected_refusal(cur,lambda:cur.execute(prior.original.ah.ag.sql_body(runtime.ROLLBACK),prepare=False),expected)
                row['status']='PASS'
            except Exception as exc:row=dict(status='FAIL',error=str(exc))
            finally:cur.execute('rollback to savepoint an_refusal;release savepoint an_refusal')
            row['boundary_restored']=boundary(cur)==before;results[name]=row
        conn.rollback()
    save('ROLLBACK_REFUSALS',dict(cases=results,production_go=False))
    assert len(results)==11 and all(r['status']=='PASS' and r['boundary_restored'] for r in results.values()),results
    operation=controller.run_maintenance_rollback(target_name='AN',target_pgurl=URL,
        maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'],report_path=ROOT/'MAINTENANCE.json',
        drain_timeout=10,natural_grace=0,terminate_after_grace=True)
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta'");runtime.verify_predecessor(cur)
        actual=normal(boundary(cur))
    assert actual==baseline,'AN did not restore exact AM catalog/owner/ACL/table/data boundary'
    result=dict(status='PASS',functions=len(actual['catalog']),tables=len(actual['boundary']['tables']),
        public_catalog_exact=True,full_boundary_exact=True,operation=operation,production_go=False)
    save('EXACT_AM_RESTORE',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=('install','rollback'),required=True)
    result=install() if p.parse_args().phase=='install' else rollback()
    print(json.dumps({k:v for k,v in result.items() if k!='operation'},default=str))
