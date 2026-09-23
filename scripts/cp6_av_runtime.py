"""Closed-admission AV rev2 install/restore; exact AU remains the pinned predecessor."""
from pathlib import Path
import json,os,time
import psycopg
from psycopg import sql
import cp6_av_build as build
import cp6_au_runtime as predecessor
import cp6_ao_ap_runtime as prior
import cp6_ao_ap_maintenance as maintenance
import cp6_preuse_rollback_maintenance as core
from cp6_ao_ap_inventory import data,function_pins,platform,sha

EXPECTED_PINS='a653539d49e326fc2b6b0567b29856ea3c7c6dce02eba59b047f70cb725f516e'


def pins():
    predecessor.pins()
    assert sha(build.PINS.read_bytes())==EXPECTED_PINS,'AV_SOURCE_PINS_DRIFT'
    p=json.loads(build.PINS.read_text())
    assert sha(Path(build.__file__).read_bytes())==p['builder_sha256'],'AV_BUILDER_DRIFT'
    assert sha(build.DEFINITIONS.read_bytes())==p['definitions_sha256'],'AV_DEFINITIONS_DRIFT'
    for key in ('migration','rollback'):assert sha((build.ROOT/p[key]).read_bytes())==p[key+'_sha256'],'AV_SQL_DRIFT'
    return p


def verified(cur):
    p=pins();base,capture,before,after,_,au=build.model()
    cur.execute("set local search_path='';set local timezone='UTC'")
    assert function_pins(cur)==after['functions'],'AV_FUNCTION_OWNER_ACL_DRIFT'
    assert cur.execute(build.INVENTORY_SQL).fetchone()[0]==after['objects'],'AV_FULL_CATALOG_DRIFT'
    cur.execute(build.prior_guard(base,capture,au),prepare=False)
    cur.execute(build.package.capsule_guard('AV',p),prepare=False)
    assert cur.execute('select count(*) from erp.schema_migrations where version=%s',(build.VERSION,)).fetchone()==(1,)
    assert cur.execute('select version,name,statements from supabase_migrations.schema_migrations where version=%s or name=%s',(build.STAMP,build.NAME)).fetchall()==[(build.STAMP,build.NAME,[build.MIGRATION.read_text()])]
    assert not cur.execute('select 1 from supabase_migrations.schema_migrations where version>%s',(build.STAMP,)).fetchone()
    coverage=cur.execute('select erp.assert_new_stock_cutoff_coverage_v1()').fetchone()[0]
    return dict(stage='AV_REV2',function_count=len(after['functions']),object_count=len(after['objects']),full_catalog_verified=True,
                changed_functions=[f['identity'] for f in p['functions']],new_functions=[f['identity'] for f in p['new_functions']],new_tables=p['new_tables'],
                coverage=coverage,prior_permanent_sql_unchanged=True)


def change(kind,pg,control_url):
    assert kind in ('install','rollback')
    database,control_database=core._validate_connections(pg,control_url)
    p=pins();path=build.ROOT/p['migration' if kind=='install' else 'rollback']
    with psycopg.connect(pg,autocommit=True,application_name='cp6-av-'+kind) as conn,psycopg.connect(control_url,autocommit=True) as control:
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
            observations=[];deadline=time.monotonic()+10
            while True:
                sessions=control.execute('select pid,backend_type,application_name,state from pg_stat_activity where datname=%s and pid<>%s order by pid',(database,pid)).fetchall()
                if sessions:
                    observations.append(dict(sessions=sessions))
                    assert time.monotonic()<deadline,('AV_REQUIRES_DRAINED_DATABASE',sessions)
                    time.sleep(.05);continue
                try:
                    with conn.transaction(),conn.cursor() as cur:
                        cur.execute(prior.sql_body(path.read_text()),prepare=False)
                        if kind=='install':cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(build.STAMP,build.NAME,[path.read_text()]))
                        result=verified(cur) if kind=='install' else predecessor.verified(cur)
                    break
                except psycopg.Error as exc:
                    # Same fail-closed retry as AU: only the pre-mutation drain refusal.
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


def qualify(pg,admin):
    """Two exact pre-use cycles on the same seeded AU clone, then the open-admission refusal."""
    control=os.environ['CP6_ADMISSION_CONTROL_PGURL'];report=dict(status='INCOMPLETE',cycles=[],production_go=False,independent_acceptance=False)
    def snapshot():
        with psycopg.connect(admin) as conn,conn.cursor() as cur:return dict(data=data(cur),platform=platform(cur))
    before=snapshot();report['nonempty_tables']=sum(v['count']>0 for v in before['data'].values())
    for _ in range(2):
        installed=change('install',pg,control);boundary=snapshot()
        with psycopg.connect(admin) as conn,conn.cursor() as cur:
            try:
                with conn.transaction():cur.execute(prior.sql_body(build.ROLLBACK.read_text()),prepare=False)
            except psycopg.Error as exc:assert 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE' in str(exc)
            else:raise AssertionError('AV_OPEN_ROLLBACK_ADMITTED')
        assert snapshot()==boundary
        restored=change('rollback',pg,control);assert snapshot()==before
        report['cycles'].append(dict(install=installed,open_rollback_refused_atomically=True,restore=restored,exact_au_data_and_history_restored=True))
    report['final_install']=change('install',pg,control)
    report['status']='PASS'
    return report


def refuse_post_use(pg,admin):
    """Commit one real master fact on the clone; the AV restore must then refuse without change."""
    control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
    core._validate_connections(pg,control_url)
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        code='AVUSE'+os.urandom(6).hex()
        cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s)',(code,'AV post-use fact'))
    with psycopg.connect(pg,autocommit=True) as conn,psycopg.connect(control_url,autocommit=True) as control:
        control.execute(maintenance.LOCK)
        try:
            control.execute(sql.SQL('alter database {} with allow_connections false').format(sql.Identifier('cp6_rollback')))
            pid=core._scalar(conn,'select pg_backend_pid()');deadline=time.monotonic()+10
            while control.execute('select 1 from pg_stat_activity where datname=%s and pid<>%s',('cp6_rollback',pid)).fetchone():
                assert time.monotonic()<deadline,'AV_POST_USE_DRAIN_TIMEOUT'
                time.sleep(.05)
            with conn.transaction(),conn.cursor() as cur:
                verified(cur);before=dict(data=data(cur),platform=platform(cur))
                try:
                    with conn.transaction():cur.execute(prior.sql_body(build.ROLLBACK.read_text()),prepare=False)
                except psycopg.Error as exc:assert 'AV_POST_USE_ROLLBACK_REFUSED' in str(exc),str(exc)
                else:raise AssertionError('AV_USED_ROLLBACK_ADMITTED')
                verified(cur);assert dict(data=data(cur),platform=platform(cur))==before
            control.execute(sql.SQL('alter database {} with allow_connections true').format(sql.Identifier('cp6_rollback')))
        finally:control.execute(maintenance.UNLOCK)
    return dict(status='PASS',committed_use='erp.brands one row',rollback_refused='AV_POST_USE_ROLLBACK_REFUSED',all_erp_data_unchanged=True,platform_unchanged=True)
