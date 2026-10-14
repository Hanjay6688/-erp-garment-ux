"""install_file (cp6_readiness_owner_install) on a throwaway database: the per-file drain wait and the retry of only
the exact PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE refusal (Sol OPEN-AZ-FIRST). Disposable; needs a local superuser URL.

Cases: a backend that leaves is waited for; a first-statement drained refusal is rolled back and retried once (a
non-transactional sequence proves the first attempt ran, the table proves nothing of it was committed); any other
P0001 stops at once; a backend that stays stops with DRAIN_TIMEOUT_BEFORE_FILE; reopened admission stops before
the file."""
from pathlib import Path
import json,os,sys,threading,time
import psycopg
sys.path.insert(0,str(Path(__file__).resolve().parent))
import cp6_readiness_owner_install as installer

URL=os.environ.get('CP6_DRAIN_TEST_PGURL','postgresql://postgres:postgres@127.0.0.1:54322/postgres')
DB='cp6_owner_drain_test'
GUARD="""do $closed_admission$
begin
 if session_user not in('postgres','supabase_admin')
  or (select datallowconn from pg_database where datname=current_database())
  or exists(select 1 from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid()) then
  raise exception 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE';
 end if;
end $closed_admission$;
"""
# The race stand-in: refuse with the drained message the first time only (the sequence survives the rollback).
FLAKY="""do $race$ begin if nextval('drain_probe')=1 then raise exception 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE'; end if; end $race$;
"""
def text(body):return 'begin;\n'+body+'commit;\n'
def row(key):return dict(key=key,stamp='2099'+key.encode().hex()[:10].ljust(10,'0'),name='drain_'+key)

def main():
    target=URL.rsplit('/',1)[0]+'/'+DB;out={}
    with psycopg.connect(URL,autocommit=True) as admin:
        admin.execute(f'drop database if exists {DB} with (force)');admin.execute(f'create database {DB}')
    try:
        with psycopg.connect(target,autocommit=True) as setup:
            setup.execute('create schema supabase_migrations;create table supabase_migrations.schema_migrations(version text primary key,name text,statements text[]);create sequence drain_probe')
        authority=psycopg.connect(URL,autocommit=True);work=psycopg.connect(target,autocommit=True)
        pid=work.execute('select pg_backend_pid()').fetchone()[0];report={}
        lingering=psycopg.connect(target,autocommit=True)
        authority.execute(f'alter database {DB} with allow_connections false')
        # 1. A backend present before the file leaves after 0.4 s: the file waits for it, then installs.
        threading.Timer(.4,lingering.close).start();t=time.monotonic()
        installer.install_file(work,authority,DB,pid,row('W'),text(GUARD+'create table waited(x int);\n'),5,report)
        out['wait_then_install']=dict(seconds=round(time.monotonic()-t,2),table=work.execute("select to_regclass('public.waited') is not null").fetchone()[0],
            seen=report['drain_waits']['W'])
        assert out['wait_then_install']['table'] and out['wait_then_install']['seconds']>=.3 and report['drain_waits']['W']['refused_and_retried']==0,out
        # 2. The file's first statement refuses with the exact drained message once: rolled back, retried, installed once.
        installer.install_file(work,authority,DB,pid,row('R'),text(FLAKY+GUARD+'create table retried(x int);\n'),5,report)
        out['refused_then_retried']=dict(attempts=work.execute('select last_value from drain_probe').fetchone()[0],retried=report['drain_waits']['R']['refused_and_retried'],
            ledger=work.execute("select count(*) from supabase_migrations.schema_migrations where name='drain_R'").fetchone()[0])
        assert out['refused_then_retried']==dict(attempts=2,retried=1,ledger=1),out
        # 3. Any other P0001 is not retried and leaves nothing.
        try:installer.install_file(work,authority,DB,pid,row('O'),text("do $x$ begin raise exception 'AZ_PRIOR_PLATFORM_DRIFT: x'; end $x$;\ncreate table other(x int);\n"),5,report);raise AssertionError('other P0001 retried')
        except psycopg.errors.RaiseException as exc:out['other_refusal_not_retried']=exc.diag.message_primary
        assert work.execute("select to_regclass('public.other') is null").fetchone()[0] and 'O' not in report.get('drain_waits',{})
        # 4. A drained refusal that keeps coming stops at the deadline (no endless retry).
        work.execute("select setval('drain_probe',1,false)")
        try:installer.install_file(work,authority,DB,pid,row('A'),text("do $a$ begin raise exception 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE'; end $a$;\n"),.3,report);raise AssertionError('endless')
        except psycopg.errors.RaiseException:out['persistent_drained_refusal_stops']=report['drain_waits']['A']['refused_and_retried']
        assert out['persistent_drained_refusal_stops']>=1
        # 5. A backend that stays: DRAIN_TIMEOUT_BEFORE_FILE, file not run.
        authority.execute(f'alter database {DB} with allow_connections true');held=psycopg.connect(target,autocommit=True);authority.execute(f'alter database {DB} with allow_connections false')
        try:installer.install_file(work,authority,DB,pid,row('T'),text(GUARD+'create table timed(x int);\n'),.3,report);raise AssertionError('no timeout')
        except installer.Refused as exc:out['backend_stays']=str(exc)
        held.close();assert out['backend_stays']=='DRAIN_TIMEOUT_BEFORE_FILE' and work.execute("select to_regclass('public.timed') is null").fetchone()[0]
        # 6. Reopened admission stops before the file.
        authority.execute(f'alter database {DB} with allow_connections true')
        try:installer.install_file(work,authority,DB,pid,row('X'),text(GUARD),5,report);raise AssertionError('reopened accepted')
        except installer.Refused as exc:out['reopened']=str(exc)
        assert out['reopened']=='ADMISSION_REOPENED_BEFORE_FILE'
        work.close();authority.close()
        out['status']='PASS'
    finally:
        with psycopg.connect(URL,autocommit=True) as admin:
            admin.execute(f'alter database {DB} with allow_connections true');admin.execute(f'drop database if exists {DB} with (force)')
        print(json.dumps(out,default=str),flush=True)
if __name__=='__main__':main()
