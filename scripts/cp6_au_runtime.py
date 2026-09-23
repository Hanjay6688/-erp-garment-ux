"""Closed-admission AU install/restore; exact AT history and data remain pinned."""
from pathlib import Path
import json,os,subprocess,time
import psycopg
from psycopg import sql
import cp6_au_build as build
import cp6_at_runtime as predecessor
import cp6_ao_ap_runtime as prior
import cp6_ao_ap_maintenance as maintenance
import cp6_preuse_rollback_maintenance as core
from cp6_ao_ap_inventory import data,function_pins,platform,sha

EXPECTED_PINS='e52ce2daf6e0033dabb9265864ac69d20f95b0b96408c0e04f29a1d5833f1c2d'
def pins():
    predecessor.pins()
    assert sha(build.PINS.read_bytes())==EXPECTED_PINS,'AU_SOURCE_PINS_DRIFT'
    p=json.loads(build.PINS.read_text())
    assert sha(Path(build.__file__).read_bytes())==p['builder_sha256'],'AU_BUILDER_DRIFT'
    assert sha(Path('scripts/cp6_au_definitions.py').read_bytes())==p['definitions_sha256'],'AU_DEFINITIONS_DRIFT'
    for key in ('migration','rollback'):assert sha(Path(p[key]).read_bytes())==p[key+'_sha256'],'AU_SQL_DRIFT'
    return p

def verified(cur):
    p=pins();base,capture,before,after,_=build.model()
    cur.execute("set local search_path='';set local timezone='UTC'")
    assert function_pins(cur)==after['functions'],'AU_FUNCTION_OWNER_ACL_DRIFT'
    assert cur.execute(build.INVENTORY_SQL).fetchone()[0]==after['objects'],'AU_FULL_CATALOG_DRIFT'
    cur.execute(build.prior_guard(base,capture),prepare=False)
    cur.execute(build.package.capsule_guard('AU',p),prepare=False)
    assert cur.execute('select count(*) from erp.schema_migrations where version=%s',(build.VERSION,)).fetchone()==(1,)
    assert cur.execute('select version,name,statements from supabase_migrations.schema_migrations where version=%s or name=%s',(build.STAMP,build.NAME)).fetchall()==[(build.STAMP,build.NAME,[build.MIGRATION.read_text()])]
    assert not cur.execute('select 1 from supabase_migrations.schema_migrations where version>%s',(build.STAMP,)).fetchone()
    return dict(stage='AU',function_count=len(after['functions']),object_count=len(after['objects']),full_catalog_verified=True,
                changed_functions=list(build.FUNCTIONS),prior_permanent_sql_unchanged=True)

def change(kind,pg,control_url):
    assert kind in ('install','rollback')
    database,control_database=core._validate_connections(pg,control_url)
    p=pins();path=Path(p['migration' if kind=='install' else 'rollback'])
    with psycopg.connect(pg,autocommit=True,application_name='cp6-au-'+kind) as conn,psycopg.connect(control_url,autocommit=True) as control:
        a=core._endpoint_snapshot(conn);b=core._endpoint_snapshot(control)
        assert a['database']==database and a['user']=='postgres'
        assert b['database']==control_database and b['user']=='cp6_maintenance_admission'
        assert all(a[k] and a[k]==b[k] for k in ('server_address','server_port','system_identifier'))
        assert core._scalar(control,'select rolsuper from pg_roles where rolname=current_user')
        assert core._scalar(control,'select datallowconn from pg_database where datname=%s',(database,))
        control.execute(maintenance.LOCK)
        try:
            with conn.transaction(),conn.cursor() as cur:
                (predecessor.verified(cur) if kind=='install' else verified(cur))
            pid=core._scalar(conn,'select pg_backend_pid()')
            control.execute(sql.SQL('alter database {} with allow_connections false').format(sql.Identifier(database)))
            # The SQL guard requires every backend to drain, including a
            # finishing autovacuum worker. The inherited controller helper only
            # enumerates client backends. Keep the stricter SQL guard unchanged.
            observations=[];deadline=time.monotonic()+10
            while True:
                sessions=control.execute('select pid,backend_type,application_name,state from pg_stat_activity where datname=%s and pid<>%s order by pid',(database,pid)).fetchall()
                if sessions:
                    observations.append(dict(sessions=sessions))
                    assert time.monotonic()<deadline,('AU_REQUIRES_DRAINED_DATABASE',sessions)
                    time.sleep(.05);continue
                try:
                    with conn.transaction(),conn.cursor() as cur:
                        cur.execute(prior.sql_body(path.read_text()),prepare=False)
                        if kind=='install':cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(build.STAMP,build.NAME,[path.read_text()]))
                        result=verified(cur) if kind=='install' else predecessor.verified(cur)
                    break
                except psycopg.Error as exc:
                    # An in-flight backend can become visible between the two
                    # checks. Retry only this fail-closed pre-mutation refusal,
                    # after psycopg has rolled the entire attempt back.
                    if exc.sqlstate!='P0001' or 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE' not in str(exc):raise
                    observations.append(dict(sql_guard_refused=True))
                    if time.monotonic()>=deadline:raise
                    time.sleep(.05)
            with conn.transaction(),conn.cursor() as cur:
                (verified(cur) if kind=='install' else predecessor.verified(cur))
            control.execute(sql.SQL('alter database {} with allow_connections true').format(sql.Identifier(database)))
            assert core._scalar(control,'select datallowconn from pg_database where datname=%s',(database,))
            return dict(action=kind,status='PASS',closed_drained=True,committed_verified=True,admission_reopened=True,runtime=result,drain_observations=observations)
        finally:control.execute(maintenance.UNLOCK)

def advisors(pg,stage,path,baseline=None):
    def snapshot():
        with psycopg.connect(pg) as conn,conn.cursor() as cur:
            (predecessor.verified(cur) if stage=='AT' else verified(cur))
            return dict(data=data(cur),platform=platform(cur),catalog=cur.execute(build.INVENTORY_SQL).fetchone()[0])
    before=snapshot()
    assert subprocess.check_output(['supabase','--version'],text=True).strip()=='2.116.0'
    r=subprocess.run(['supabase','db','advisors','--db-url',pg,'--type','security','--level','info','--fail-on','none','--output-format','text','--agent','no'],capture_output=True,text=True,timeout=90)
    assert r.returncode==0,'AU_ADVISORS_FAILED'
    if r.stdout.strip():findings=json.loads(r.stdout)
    else:
        assert 'No issues found' in r.stderr.splitlines(),'AU_ADVISORS_MISSING_RESULT'
        findings=[]
    assert isinstance(findings,list) and all(isinstance(x,dict) and x.get('name') and x.get('level') for x in findings)
    assert snapshot()==before,'AU_ADVISORS_CHANGED_BOUNDARY'
    report=dict(stage=stage,status='BASELINE_RECORDED',findings=findings,boundary_unchanged=True,production_go=False,independent_acceptance=False)
    if baseline is not None:
        known={json.dumps(x,sort_keys=True) for x in baseline['findings']}
        added=[x for x in findings if json.dumps(x,sort_keys=True) not in known]
        reviewed=[];unexpected=[]
        for f in added:
            m=f.get('metadata') or {}
            if f['name']=='rls_enabled_no_policy' and f['level']=='INFO' and m.get('schema')=='erp' and m.get('name') in (build.CAP.split('.')[1],build.CONTEXT):reviewed.append(f)
            else:unexpected.append(f)
        report.update(status='PASS_REVIEWED_DELTA' if not unexpected else 'REVIEW_REQUIRED',reviewed_private_capsule_info=reviewed,new_unreviewed_findings=unexpected,baseline_findings=baseline['findings'])
    path.write_text(json.dumps(report,indent=2)+'\n')
    assert report['status']!='REVIEW_REQUIRED',report['new_unreviewed_findings']
    return report

def qualify(pg,admin,out):
    """The two pre-use cycles operate on the same seeded, nonempty AT clone."""
    control=os.environ['CP6_ADMISSION_CONTROL_PGURL'];report=dict(status='INCOMPLETE',cycles=[],production_go=False,independent_acceptance=False)
    def snapshot():
        with psycopg.connect(admin) as conn,conn.cursor() as cur:return dict(data=data(cur),platform=platform(cur))
    before=snapshot();report['nonempty_tables']=sum(v['count']>0 for v in before['data'].values())
    try:
        baseline=advisors(pg,'AT',out/'AU_ADVISORS_BEFORE.json')
        for _ in range(2):
            installed=change('install',pg,control)
            # Open admission must reject the raw rollback before changing any data.
            boundary=snapshot()
            with psycopg.connect(admin) as conn,conn.cursor() as cur:
                try:
                    with conn.transaction():cur.execute(prior.sql_body(build.ROLLBACK.read_text()),prepare=False)
                except psycopg.Error as exc:assert 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE' in str(exc)
                else:raise AssertionError('AU_OPEN_ROLLBACK_ADMITTED')
            assert snapshot()==boundary
            restored=change('rollback',pg,control);assert snapshot()==before
            report['cycles'].append(dict(install=installed,open_rollback_refused_atomically=True,restore=restored,exact_at_data_and_history_restored=True))
        report['final_install']=change('install',pg,control)
        security=advisors(pg,'AU',out/'AU_ADVISORS_AFTER.json',baseline)
        report['security_advisors']=dict(status=security['status'],baseline=len(baseline['findings']),current=len(security['findings']),reviewed_additions=len(security['reviewed_private_capsule_info']),unreviewed_additions=len(security['new_unreviewed_findings']))
        report['status']='PASS'
    finally:(out/'AU_PACKAGE.json').write_text(json.dumps(report,indent=2,default=str)+'\n')

def refuse_post_use(pg,admin,out):
    """A used AU clone cannot be restored even after linked business reversals."""
    control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
    core._validate_connections(pg,control_url)
    with psycopg.connect(pg,autocommit=True) as conn,psycopg.connect(control_url,autocommit=True) as control:
        control.execute(maintenance.LOCK)
        try:
            control.execute(sql.SQL('alter database {} with allow_connections false').format(sql.Identifier('cp6_rollback')))
            pid=core._scalar(conn,'select pg_backend_pid()');deadline=time.monotonic()+10
            while control.execute('select 1 from pg_stat_activity where datname=%s and pid<>%s',('cp6_rollback',pid)).fetchone():
                assert time.monotonic()<deadline,'AU_POST_USE_DRAIN_TIMEOUT'
                time.sleep(.05)
            with conn.transaction(),conn.cursor() as cur:
                verified(cur);before=dict(data=data(cur),platform=platform(cur))
                try:
                    with conn.transaction():cur.execute(prior.sql_body(build.ROLLBACK.read_text()),prepare=False)
                except psycopg.Error as exc:assert 'AU_POST_USE_ROLLBACK_REFUSED' in str(exc)
                else:raise AssertionError('AU_USED_ROLLBACK_ADMITTED')
                verified(cur);assert dict(data=data(cur),platform=platform(cur))==before
            control.execute(sql.SQL('alter database {} with allow_connections true').format(sql.Identifier('cp6_rollback')))
        finally:control.execute(maintenance.UNLOCK)
    (out/'AU_POST_USE_REFUSAL.json').write_text(json.dumps(dict(status='PASS',all_erp_data_unchanged=True,platform_unchanged=True,production_go=False,independent_acceptance=False),indent=2)+'\n')
