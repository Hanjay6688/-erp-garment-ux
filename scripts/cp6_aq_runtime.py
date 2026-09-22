"""Closed-admission AQ install/restore; exact AP history and data remain pinned."""
from pathlib import Path
import json,os
import psycopg
from psycopg import sql
import cp6_aq_build as build
import cp6_ao_ap_runtime as prior
import cp6_ao_ap_maintenance as maintenance
import cp6_preuse_rollback_maintenance as core
from cp6_ao_ap_inventory import data,function_pins,platform,sha

EXPECTED_PINS='2f58f2b3ef00367e04c4ed2aa2f9418642452220b15139936c30608f700f8f9a'
def pins():
    prior.pins()
    assert sha(build.PINS.read_bytes())==EXPECTED_PINS,'AQ_SOURCE_PINS_DRIFT'
    p=json.loads(build.PINS.read_text())
    assert sha(Path(build.__file__).read_bytes())==p['builder_sha256'],'AQ_BUILDER_DRIFT'
    for key in ('migration','rollback'):assert sha(Path(p[key]).read_bytes())==p[key+'_sha256'],'AQ_SQL_DRIFT'
    return p

def verified(cur):
    p=pins();base,capture,before,after,_=build.model()
    cur.execute("set local search_path='';set local timezone='UTC'")
    assert function_pins(cur)==after['functions'],'AQ_FUNCTION_OWNER_ACL_DRIFT'
    assert cur.execute(build.INVENTORY_SQL).fetchone()[0]==after['objects'],'AQ_FULL_CATALOG_DRIFT'
    cur.execute(build.prior_guard(base,capture),prepare=False)
    cur.execute(build.package.capsule_guard('AQ',p),prepare=False)
    assert cur.execute('select count(*) from erp.schema_migrations where version=%s',(build.VERSION,)).fetchone()==(1,)
    assert cur.execute('select version,name,statements from supabase_migrations.schema_migrations where version=%s or name=%s',(build.STAMP,build.NAME)).fetchall()==[(build.STAMP,build.NAME,[build.MIGRATION.read_text()])]
    assert not cur.execute('select 1 from supabase_migrations.schema_migrations where version>%s',(build.STAMP,)).fetchone()
    return dict(stage='AQ',function_count=len(after['functions']),object_count=len(after['objects']),full_catalog_verified=True,
                changed_functions=[build.IDENTITY],prior_permanent_sql_unchanged=True)

def change(kind,pg,control_url):
    assert kind in ('install','rollback')
    database,control_database=core._validate_connections(pg,control_url)
    p=pins();path=Path(p['migration' if kind=='install' else 'rollback'])
    with psycopg.connect(pg,autocommit=True,application_name='cp6-aq-'+kind) as conn,psycopg.connect(control_url,autocommit=True) as control:
        a=core._endpoint_snapshot(conn);b=core._endpoint_snapshot(control)
        assert a['database']==database and a['user']=='postgres'
        assert b['database']==control_database and b['user']=='cp6_maintenance_admission'
        assert all(a[k] and a[k]==b[k] for k in ('server_address','server_port','system_identifier'))
        assert core._scalar(control,'select rolsuper from pg_roles where rolname=current_user')
        assert core._scalar(control,'select datallowconn from pg_database where datname=%s',(database,))
        control.execute(maintenance.LOCK)
        try:
            with conn.transaction(),conn.cursor() as cur:
                (prior.verified(cur,'AP') if kind=='install' else verified(cur))
            pid=core._scalar(conn,'select pg_backend_pid()')
            control.execute(sql.SQL('alter database {} with allow_connections false').format(sql.Identifier(database)))
            assert not core._sessions(control,database,pid),'AQ_REQUIRES_DRAINED_DATABASE'
            with conn.transaction(),conn.cursor() as cur:
                cur.execute(prior.sql_body(path.read_text()),prepare=False)
                if kind=='install':cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(build.STAMP,build.NAME,[path.read_text()]))
                result=verified(cur) if kind=='install' else prior.verified(cur,'AP')
            with conn.transaction(),conn.cursor() as cur:
                (verified(cur) if kind=='install' else prior.verified(cur,'AP'))
            control.execute(sql.SQL('alter database {} with allow_connections true').format(sql.Identifier(database)))
            assert core._scalar(control,'select datallowconn from pg_database where datname=%s',(database,))
            return dict(action=kind,status='PASS',closed_drained=True,committed_verified=True,admission_reopened=True,runtime=result)
        finally:control.execute(maintenance.UNLOCK)

def qualify(pg,admin,out):
    """The two pre-use cycles operate on the same seeded, nonempty AP clone."""
    control=os.environ['CP6_ADMISSION_CONTROL_PGURL'];report=dict(status='INCOMPLETE',cycles=[],production_go=False,independent_acceptance=False)
    def snapshot():
        with psycopg.connect(admin) as conn,conn.cursor() as cur:return dict(data=data(cur),platform=platform(cur))
    before=snapshot();report['nonempty_tables']=sum(v['count']>0 for v in before['data'].values())
    try:
        for _ in range(2):
            installed=change('install',pg,control)
            # Open admission must reject the raw rollback before changing any data.
            boundary=snapshot()
            with psycopg.connect(admin) as conn,conn.cursor() as cur:
                try:
                    with conn.transaction():cur.execute(prior.sql_body(build.ROLLBACK.read_text()),prepare=False)
                except psycopg.Error as exc:assert 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE' in str(exc)
                else:raise AssertionError('AQ_OPEN_ROLLBACK_ADMITTED')
            assert snapshot()==boundary
            restored=change('rollback',pg,control);assert snapshot()==before
            report['cycles'].append(dict(install=installed,open_rollback_refused_atomically=True,restore=restored,exact_ap_data_and_history_restored=True))
        report['final_install']=change('install',pg,control);report['status']='PASS'
    finally:(out/'AQ_PACKAGE.json').write_text(json.dumps(report,indent=2,default=str)+'\n')

def refuse_post_use(pg,admin,out):
    """A used AQ clone cannot be restored even after linked business reversals."""
    control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
    core._validate_connections(pg,control_url)
    with psycopg.connect(pg,autocommit=True) as conn,psycopg.connect(control_url,autocommit=True) as control:
        control.execute(maintenance.LOCK)
        try:
            control.execute(sql.SQL('alter database {} with allow_connections false').format(sql.Identifier('cp6_rollback')))
            assert not core._sessions(control,'cp6_rollback',core._scalar(conn,'select pg_backend_pid()'))
            with conn.transaction(),conn.cursor() as cur:
                verified(cur);before=dict(data=data(cur),platform=platform(cur))
                try:
                    with conn.transaction():cur.execute(prior.sql_body(build.ROLLBACK.read_text()),prepare=False)
                except psycopg.Error as exc:assert 'AQ_POST_USE_ROLLBACK_REFUSED' in str(exc)
                else:raise AssertionError('AQ_USED_ROLLBACK_ADMITTED')
                verified(cur);assert dict(data=data(cur),platform=platform(cur))==before
            control.execute(sql.SQL('alter database {} with allow_connections true').format(sql.Identifier('cp6_rollback')))
        finally:control.execute(maintenance.UNLOCK)
    (out/'AQ_POST_USE_REFUSAL.json').write_text(json.dumps(dict(status='PASS',all_erp_data_unchanged=True,platform_unchanged=True,production_go=False,independent_acceptance=False),indent=2)+'\n')
