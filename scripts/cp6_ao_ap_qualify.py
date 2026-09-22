"""Committed install/restore/reinstall, strict refusals and drained-session proof.

Only the exact disposable cp6_rollback clone is admitted. No hosted endpoint,
production acceptance, independent acceptance, or automatic recovery is implied.
"""
from pathlib import Path
import json,os,threading,time,traceback
import psycopg
from psycopg import sql
import cp6_ao_ap_runtime as runtime
import cp6_ao_ap_maintenance as maintenance
import cp6_ao_ap_installed as installed
import cp6_ao_ap_advisors as advisors
from cp6_ao_ap_inventory import inventory,data,platform,sha

ROOT=Path('cp6-proof/ao-ap-package');ROOT.mkdir(parents=True,exist_ok=True)
URL='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
ADMIN='postgresql://supabase_admin:postgres@127.0.0.1:54322/cp6_rollback'
CONTROL=os.environ['CP6_ADMISSION_CONTROL_PGURL']
REPORT=dict(status='INCOMPLETE',head=json.loads((ROOT/'SOURCE.json').read_text())['head'],roundtrips=[],refusals=[],session_schedules=[],production_go=False,independent_acceptance=False,hosted_migration_installed=False)

def save(): (ROOT/'QUALIFICATION.json').write_text(json.dumps(REPORT,indent=2,default=str)+'\n')
def snapshot(cur):return dict(objects=inventory(cur),data=data(cur),platform_sha256=sha(json.dumps(platform(cur),sort_keys=True)))
def observe(stage):
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        runtime.verified(cur,stage);return snapshot(cur)
def admission(control,opened):control.execute(sql.SQL('alter database cp6_rollback with allow_connections {}').format(sql.SQL('true' if opened else 'false')))
def do_install(family,label):
    return maintenance.install(family=family,target_pgurl=URL,maintenance_pgurl=CONTROL,report_path=ROOT/(label+'.json'))
def do_rollback(family,label,**kwargs):
    return maintenance.rollback(family=family,target_pgurl=URL,maintenance_pgurl=CONTROL,report_path=ROOT/(label+'.json'),drain_timeout=kwargs.pop('drain_timeout',8),natural_grace=kwargs.pop('natural_grace',.1),terminate_after_grace=kwargs.pop('terminate_after_grace',True),**kwargs)

def refused_sql(cur,body,expected):
    before=snapshot(cur);cur.execute('savepoint refused_package');error=None
    try:cur.execute(body,prepare=False)
    except psycopg.Error as exc:error=exc.diag.message_primary
    finally:cur.execute('rollback to savepoint refused_package');cur.execute('release savepoint refused_package')
    assert error and expected in error,(expected,error)
    assert snapshot(cur)==before,'REFUSAL_CHANGED_BOUNDARY'
    return error

def guards(family):
    p=runtime.pins()['families'][family];body=runtime.sql_body((runtime.ROOT/p['rollback']).read_text());cap=p['capsule'];helper=next(iter(p['new_functions']));table='erp.'+p['new_tables'][0]
    cases=[
      ('FUNCTION_GRANT',f'grant execute on function {helper} to authenticated','CATALOG_DRIFT'),
      ('FUNCTION_OWNER',f'alter function {helper} owner to supabase_admin','CATALOG_DRIFT'),
      ('FUNCTION_CONFIGURATION',f"alter function {helper} set statement_timeout='3s'",'CATALOG_DRIFT'),
      ('TABLE_RLS',f'alter table {table} disable row level security','CATALOG_DRIFT'),
      ('TABLE_COLUMN',f'alter table {table} add column package_drift text','CATALOG_DRIFT'),
      ('TABLE_CONSTRAINT',f'alter table {table} add constraint package_drift check(true)','CATALOG_DRIFT'),
      ('INHERITED_TRIGGER','alter table erp.cutting_groups disable trigger trg_06_require_pattern_identity','CATALOG_DRIFT'),
      ('SCHEMA_GRANT','grant usage on schema erp to anon','CATALOG_DRIFT'),
      ('CAPSULE_SOURCE',f"update {cap} set object_definition=object_definition||E'\\n-- drift'",'CAPSULE_SOURCE_DRIFT'),
      ('CAPSULE_BOUNDARY',f"update {cap} set boundary_snapshot='{{}}'::jsonb",'CAPSULE_BOUNDARY'),
      ('CAPSULE_COLUMN',f'alter table {cap} add column package_drift text','CAPSULE_SHAPE_DRIFT'),
      ('CAPSULE_DURABILITY',f'alter table {cap} set unlogged','CAPSULE_SHAPE_DRIFT'),
      ('CAPSULE_GRANT',f'grant select on {cap} to authenticated','CAPSULE_SECURITY_OR_COUNT'),
      ('PLATFORM_SOURCE',f"update supabase_migrations.schema_migrations set statements=array['drift'] where version='{p['stamp']}'",'ROLLBACK_PLATFORM_OR_SUCCESSOR'),
      ('PLATFORM_SUCCESSOR',"insert into supabase_migrations.schema_migrations(version,name,statements) values('99999999999999','unexpected',array['drift'])",'ROLLBACK_PLATFORM_OR_SUCCESSOR'),
      ('BUSINESS_CHANGED',"update erp.locations set location_name=location_name||' changed' where id=(select id from erp.locations order by id limit 1)",'POST_USE_ROLLBACK_REFUSED'),
      ('NEW_TABLE_USED',"insert into erp.invoice_recost_execution_context values(1,current_date,gen_random_uuid())" if family=='AO' else "insert into erp.pocket_fabric_materials(material_id) select id from erp.materials order by id limit 1",'POST_USE_ROLLBACK_REFUSED'),
    ]
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur,psycopg.connect(CONTROL,autocommit=True) as control:
        baseline=snapshot(cur);conn.rollback()
        # A direct invocation with open admission must reject before any DDL.
        error=refused_sql(cur,body,'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE');conn.rollback()
        REPORT['refusals'].append(dict(family=family,case='OPEN_ADMISSION',error=error,atomic=True));save()
        admission(control,False)
        for name,mutation,expected in cases:
            cur.execute(mutation,prepare=False)
            error=refused_sql(cur,body,expected);conn.rollback()
            assert snapshot(cur)==baseline;conn.rollback()
            REPORT['refusals'].append(dict(family=family,case=name,error=error,atomic=True));save()
        # Valid install replay must still refuse the exact installed successor.
        error=refused_sql(cur,runtime.sql_body((runtime.ROOT/p['migration']).read_text()),'EXACT_PREDECESSOR_REQUIRED');conn.rollback()
        REPORT['refusals'].append(dict(family=family,case='INSTALL_REPLAY',error=error,atomic=True));save()
        assert snapshot(cur)==baseline;conn.rollback();admission(control,True)

def wait_for(fn,seconds=15):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        result=fn()
        if result:return result
        time.sleep(.025)
    raise AssertionError('SESSION_SCHEDULE_TIMEOUT')

def session_schedule(family,mode):
    """A real already-entered financial report waits inside its journal read."""
    before=observe(family);label=family+'_'+mode
    entered=threading.Event();result={};control=psycopg.connect(CONTROL,autocommit=True)
    blocker=psycopg.connect(ADMIN);blocker.execute('lock table erp.journal_entries in access exclusive mode')
    worker=psycopg.connect(ADMIN,application_name='cp6-package-cached-report')
    worker.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=installed.base.OPERATOR_AUTH,role='authenticated')),))
    pid=worker.execute('select pg_backend_pid()').fetchone()[0]
    def report_query():
        try:
            entered.set();worker.execute('select * from erp.run_v267_financial_truth_checks()').fetchall();worker.rollback();result['worker']='NATURAL_COMPLETE'
        except psycopg.Error as exc:result['worker']='CANCELLED_OR_TERMINATED';result['worker_sqlstate']=exc.sqlstate
        finally:worker.close()
    thread=threading.Thread(target=report_query);thread.start();assert entered.wait(2)
    wait_for(lambda:control.execute("select exists(select 1 from pg_stat_activity where pid=%s and wait_event_type='Lock' and query like 'select * from erp.run_v267_financial_truth_checks%%')",(pid,)).fetchone()[0])
    paused=ROOT/(label+'.closed');resume=ROOT/(label+'.continue')
    assert not paused.exists() and not resume.exists()
    def restore():
        try:result['maintenance']=do_rollback(family,label,natural_grace=3 if mode=='NATURAL' else .1,drain_timeout=1 if mode=='DRAIN_TIMEOUT' else 8,terminate_after_grace=mode=='TERMINATE',pause_after_close_file=paused,continue_file=resume)
        except Exception as exc:result['maintenance_error']=str(exc)
    restorer=threading.Thread(target=restore);restorer.start();wait_for(paused.exists)
    refused=False
    try:psycopg.connect(ADMIN,connect_timeout=2).close()
    except psycopg.Error:refused=True
    assert refused,'NEW_CONNECTION_ENTERED_CLOSED_DATABASE'
    if mode=='NATURAL':blocker.rollback();blocker.close()
    resume.write_text('continue\n');restorer.join(20);assert not restorer.is_alive()
    evidence=json.loads((ROOT/(label+'.json')).read_text())
    if mode=='DRAIN_TIMEOUT':
        assert evidence['status']=='FAIL' and evidence['admission_still_closed'] and not evidence['rollback_started']
        assert 'DRAIN_TIMEOUT' in result['maintenance_error']
        # Explicit recovery of this disposable fixture only, after the failed
        # controller proved it had never begun DDL. The old blocker remains our
        # inspection connection while admission is still closed.
        worker.cancel();thread.join(5);assert not thread.is_alive()
        blocker.rollback()
        with blocker.cursor() as cur:
            runtime.verified(cur,family);assert snapshot(cur)==before
        blocker.rollback();admission(control,True);blocker.close()
        result['disposable_fixture_recovery_verified']=True
    else:
        thread.join(5);assert not thread.is_alive()
        blocker.close();assert evidence['status']=='PASS' and evidence['rollback_committed'] and evidence['admission_reopened']
        assert result['worker']==('NATURAL_COMPLETE' if mode=='NATURAL' else 'CANCELLED_OR_TERMINATED')
        assert not evidence['sessions_after_drain']
    control.close();result.pop('maintenance',None)
    REPORT['session_schedules'].append(dict(family=family,mode=mode,status='PASS',new_connection_refused=True,body_observed_waiting=True,**result));save()

def main():
    maintenance.core._validate_connections(URL,CONTROL);runtime.pins()
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        runtime.verified(cur,'AN');installed.seed(cur);runtime.verified(cur,'AN')
    baseline=observe('AN');REPORT['baseline_nonempty_tables']=sum(v['count']>0 for v in baseline['data'].values());assert REPORT['baseline_nonempty_tables']>20
    (ROOT/'AN_BASELINE.json').write_text(json.dumps(baseline,indent=2)+'\n');save()
    advice=advisors.run(URL,'AN',ROOT/'ADVISORS_AN.json')
    do_install('AO','AO_INSTALL_FIRST');ao=observe('AO');guards('AO')
    advice=advisors.run(URL,'AO',ROOT/'ADVISORS_AO.json',advice)
    do_install('AP','AP_INSTALL_FIRST');ap=observe('AP');guards('AP')
    advisors.run(URL,'AP',ROOT/'ADVISORS_AP.json',advice)
    REPORT['installed_case_count']=len(installed.run(ADMIN,ROOT/'INSTALLED_CASES.json')['cases']);save()
    for number in (1,2):
        do_rollback('AP',f'AP_RESTORE_{number}');assert observe('AO')==ao
        do_rollback('AO',f'AO_RESTORE_{number}');assert observe('AN')==baseline
        do_install('AO',f'AO_REINSTALL_{number}');ao=observe('AO')
        do_install('AP',f'AP_REINSTALL_{number}');ap=observe('AP')
        REPORT['roundtrips'].append(dict(number=number,status='PASS',complete_an_restored=True,ao_and_ap_reinstalled=True));save()
    for family in ('AP','AO'):
        for mode in ('DRAIN_TIMEOUT','NATURAL','TERMINATE'):
            session_schedule(family,mode)
            if mode!='DRAIN_TIMEOUT':do_install(family,f'{family}_AFTER_{mode}')
        do_rollback(family,f'{family}_FINAL_RESTORE')
        if family=='AP':ao=observe('AO')
    assert observe('AN')==baseline
    REPORT.update(status='WRITER_PACKAGE_PASS',complete_baseline_restored=True,installed_and_removed_only_on_disposable=True);save()

if __name__=='__main__':
    try:main()
    except Exception as exc:REPORT.update(error=str(exc),traceback=traceback.format_exc());save();print(REPORT['traceback']);raise
    print(json.dumps({k:v for k,v in REPORT.items() if k not in('refusals','session_schedules')},default=str))
