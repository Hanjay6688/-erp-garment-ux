"""The 28 unexecuted frozen AR race operations, each in a fresh FULL clone.

The original sequential146 and replacement1 are not executed again. This
driver qualifies the FULL runtime instead of the superseded BA verifier and
disposes only the OID it created, preserving the parent FULL state exactly.
"""
import json,subprocess,traceback
import psycopg
import cp6_ar_trial as ar
import full_stack

def run(report):
    parent=ar.ADMIN
    db='astra_cp17_ar_fixture'
    clone=parent.rsplit('/',1)[0]+'/'+db
    with psycopg.connect(parent) as c,c.cursor() as cur:
        full_stack.composition.verify(cur)
        before=full_stack.package.boundary.snapshot(cur)
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    cases=[]
    for kind in ar.KINDS:
        for winner in ('imported','legacy'):
            cases.append(('CONCURRENT_'+kind+'_'+winner.upper()+'_FIRST',lambda k=kind,w=winner:ar.concurrency(today,k,w)))
    for winner in ('imported','legacy'):
        for same in (False,True):
            cases.append((('SAME_HEADER_' if same else 'WINNER_ABORT_')+winner.upper(),lambda w=winner,s=same:ar.concurrency(today,'MATERIAL',w,commit=s,same_header=s)))
    for variant in ('REPLAY','PAYLOAD','ACTION'):
        cases.append(('REQUEST_CONCURRENT_'+variant,lambda v=variant:ar.request_concurrency(today,v)))
    cases.append(('STALE_SNAPSHOT_ISOLATION',lambda:ar.isolation_guard(today)))
    assert len(cases)==28
    report.update(planned_case_ids=[k for k,_ in cases],cases={})
    full_stack.save('CP17_AR_RACES_PREEXECUTION',report)
    for key,op in cases:
        owned_oid=None;row={}
        try:
            with psycopg.connect(parent) as c:
                assert not c.execute('select 1 from pg_database where datname=%s',(db,)).fetchone(),'AUDIT_CLONE_ALREADY_EXISTS'
            subprocess.run(['docker','exec','supabase_db_cp5-local','createdb','-U','supabase_admin','--maintenance-db=template1','-T','cp6_rollback',db],check=True)
            with psycopg.connect(parent) as c:
                owned_oid=c.execute('select oid from pg_database where datname=%s',(db,)).fetchone()[0]
            ar.ADMIN=clone
            with psycopg.connect(clone) as c,c.cursor() as cur:
                full_stack.composition.verify(cur);ar.api.seed(cur)
            row=op()
        except Exception as exc:
            row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
        finally:
            ar.ADMIN=parent
            if owned_oid is not None:
                with psycopg.connect(parent) as c:
                    observed=c.execute('select oid from pg_database where datname=%s',(db,)).fetchone()
                if observed==(owned_oid,):
                    subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--force','--maintenance-db=template1',db],check=True)
                else:row.update(status='INCOMPLETE',cleanup_error='AUDIT_CLONE_OID_CHANGED')
            with psycopg.connect(parent) as c,c.cursor() as cur:
                row['parent_full_boundary_unchanged']=full_stack.package.boundary.snapshot(cur)==before
                row['fixture_clone_remaining']=cur.execute('select count(*) from pg_database where datname=%s',(db,)).fetchone()[0]
                full_stack.composition.verify(cur)
            if not row['parent_full_boundary_unchanged'] or row['fixture_clone_remaining']:
                row['status']='INCOMPLETE'
        row['owned_fixture_oid']=owned_oid
        report['cases'][key]=row;full_stack.save('CP17_AR_RACES',report)
        print(json.dumps(dict(row,group='AR_CONCURRENCY',case_id=key),default=str),flush=True)
    report['status']='WRITER_PASS' if all(r['status']=='PASS' for r in report['cases'].values()) else 'DISPOSITION_REQUIRED'
