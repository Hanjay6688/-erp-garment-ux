"""Build the candidate database DDL fence for the Enteng Uji rehearsal.

Supabase Hosted delegates creation of database event triggers to the postgres
project role. This module covers database-local DDL that fires these triggers.
Changes to roles and to the event trigger itself must enter the release lock
explicitly before changing anything. The canonical CP7 Global entry points
and catalogue checks are outside this rehearsal.
"""

import argparse
from contextlib import contextmanager
from hashlib import sha256

SCHEMA = 'cp7_global_release_guard'
TRIGGER = 'cp7_global_release_ddl'
LOCK_KEY = '274831, 47409'
MIGRATION_NAME = 'enteng_uji_cp7_managed_release_guard'
MIGRATION_STATEMENT_SHA256 = '1fc71e109592c02fda9e2ce762dffdc94a1a07cc0d8cc48a6c939962550e784e'
GUARD_DIGESTS = {
    'assert_ddl_fence()': ('109fff51d98d3ccc52f05ac4d1f4b041', 'dd7b82e6226fc5964c102d70c5e8d3205049d78191742a177412d10ee1aa2257'),
    'enter_correction()': ('d89ec2a5c28870ed585f1e10029b86ca', '7ce472d1d19cacccdac88ea6d181242b6a7bf7334f6d61b7b34aa0637aca5041'),
    'enter_release()': ('2048499353509b6f0055f76f03358c32', 'be6d0d2542c1105bce3021d788138b15f0f10e6a1724ab3065b9ddef22114dc4'),
    'lock_ddl()': ('863d3cde64df185ce26b17cc9e9589cc', 'b681118747634af02f4a3dd28711e3e75f14e54964bb6699a6c753c49549e1ad'),
}
EVENT_BODY = f"""
begin
 if not pg_catalog.pg_try_advisory_xact_lock({LOCK_KEY}) then
  raise exception using errcode='55P03',message='CP7_GLOBAL_CORRECTION_IN_PROGRESS';
 end if;
end
"""
EVENT_HASH = sha256(EVENT_BODY.encode()).hexdigest()

BODY = f"""create schema {SCHEMA} authorization postgres;
revoke all on schema {SCHEMA} from public,anon,authenticated,service_role;

create function {SCHEMA}.lock_ddl() returns event_trigger
language plpgsql volatile security invoker set search_path=''
as $ddl_fence${EVENT_BODY}$ddl_fence$;
revoke all on function {SCHEMA}.lock_ddl() from public,anon,authenticated,service_role;

create event trigger {TRIGGER} on ddl_command_start
 execute function {SCHEMA}.lock_ddl();
alter event trigger {TRIGGER} enable always;

create function {SCHEMA}.assert_ddl_fence() returns void
language plpgsql stable security invoker set search_path=''
as $ddl_assert$
begin
 if current_setting('event_triggers') <> 'on' or not exists (
   select from pg_event_trigger event
     join pg_proc fn on fn.oid=event.evtfoid
     join pg_namespace ns on ns.oid=fn.pronamespace
    where event.evtname='{TRIGGER}' and event.evtevent='ddl_command_start'
      and event.evtenabled='A' and event.evttags is null
      and event.evtowner='postgres'::regrole
      and ns.nspname='{SCHEMA}' and ns.nspowner='postgres'::regrole
      and fn.proname='lock_ddl' and fn.proowner='postgres'::regrole
      and fn.pronargs=0 and fn.prorettype='event_trigger'::regtype
      and fn.provolatile='v' and not fn.prosecdef
      and fn.proconfig=array['search_path=""']
      and encode(sha256(convert_to(fn.prosrc,'UTF8')),'hex')='{EVENT_HASH}'
 ) then
   raise exception using errcode='55000',message='CP7_GLOBAL_DDL_FENCE_CHANGED';
 end if;
end
$ddl_assert$;

create function {SCHEMA}.enter_correction() returns void
language plpgsql volatile security invoker set search_path=''
as $ddl_reader$
begin
 if current_setting('transaction_isolation')<>'read committed' then
   raise exception using errcode='25001',message='CP7_GLOBAL_READ_COMMITTED_REQUIRED';
 end if;
 if not pg_try_advisory_xact_lock_shared({LOCK_KEY}) then
   raise exception using errcode='55P03',message='CP7_GLOBAL_RELEASE_IN_PROGRESS';
 end if;
 perform {SCHEMA}.assert_ddl_fence();
end
$ddl_reader$;

create function {SCHEMA}.enter_release() returns void
language plpgsql volatile security invoker set search_path=''
as $ddl_writer$
begin
 if not pg_try_advisory_xact_lock({LOCK_KEY}) then
   raise exception using errcode='55P03',message='CP7_GLOBAL_CORRECTION_IN_PROGRESS';
 end if;
 perform {SCHEMA}.assert_ddl_fence();
end
$ddl_writer$;
revoke all on all functions in schema {SCHEMA} from public,anon,authenticated,service_role;
select {SCHEMA}.assert_ddl_fence();
"""


@contextmanager
def release_transaction(cur):
    """Take the release lock before any DDL, including changes to roles."""
    from psycopg.pq import TransactionStatus

    if cur.connection.info.transaction_status != TransactionStatus.INTRANS:
        raise ValueError('An explicit release transaction is required')
    with cur.connection.transaction():
        actor = cur.execute("select session_user,current_user,rolsuper from pg_roles where rolname=current_user").fetchone()
        if actor != ('postgres', 'postgres', False):
            raise ValueError('Managed postgres release identity required')
        cur.execute(f'select {SCHEMA}.enter_release()')
        yield
        cur.execute(f'select {SCHEMA}.assert_ddl_fence()')


def verified_on_baseline(conn, migration_count):
    """Recognize the reviewed guard as the sole extra migration after CP6 BF."""
    schema, trigger = conn.execute("""
        select to_regnamespace(%s) is not null,
               exists(select from pg_event_trigger where evtname=%s)
    """, (SCHEMA, TRIGGER)).fetchone()
    if migration_count == 138 and not schema and not trigger:
        return False
    if migration_count != 139 or not schema or not trigger:
        raise ValueError('Unexpected guard or migration count on the Enteng BF baseline')
    statement_hashes = conn.execute("""
        select encode(sha256(convert_to(array_to_json(statements)::text,'UTF8')),'hex')
          from supabase_migrations.schema_migrations where name=%s
    """, (MIGRATION_NAME,)).fetchall()
    if statement_hashes != [(MIGRATION_STATEMENT_SHA256,)]:
        raise ValueError('The deployed Enteng guard migration differs from the reviewed SQL')
    path = conn.execute('show search_path').fetchone()[0]
    conn.execute("set local search_path=''")
    functions = conn.execute("""
        select p.oid::regprocedure::text,md5(pg_get_functiondef(p.oid)),
               encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex'),p.proowner::regrole::text,
               (select jsonb_agg(jsonb_build_array(a.grantee::regrole::text,a.privilege_type,a.is_grantable)
                                 order by a.grantee,a.privilege_type,a.is_grantable)
                from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a)
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s order by 1
    """, (SCHEMA,)).fetchall()
    conn.execute("select set_config('search_path',%s,true)", (path,))
    expected = [(f'{SCHEMA}.{name}', *digests, 'postgres', [['postgres', 'EXECUTE', False]])
                for name, digests in sorted(GUARD_DIGESTS.items())]
    if functions != expected:
        raise ValueError('The deployed guard functions or their private ACLs differ from the reviewed migration')
    conn.execute(f'select {SCHEMA}.assert_ddl_fence()')
    return True


def hosted_rehearsal():
    return f"""begin;
set local statement_timeout='8s';
set local lock_timeout='2s';
do $require_project_role$
begin
 if current_user<>'postgres' or session_user<>'postgres'
    or current_setting('is_superuser')<>'off' then
   raise exception 'CP7_GLOBAL_ORDINARY_PROJECT_ROLE_REQUIRED';
 end if;
end
$require_project_role$;
{BODY}
create function {SCHEMA}.sample() returns integer language sql immutable as 'select 7';
alter function {SCHEMA}.sample() stable;
grant execute on function {SCHEMA}.sample() to postgres;
revoke all on function {SCHEMA}.sample() from public;
do $check$
begin
 if not exists (select from pg_locks where locktype='advisory' and classid=274831 and objid=47409
                and pid=pg_backend_pid() and mode='ExclusiveLock' and granted) then
  raise exception 'CP7_GLOBAL_DDL_LOCK_EXPECTED';
 end if;
 if exists(select from unnest(array['anon','authenticated','service_role']) r
            where has_schema_privilege(r,'{SCHEMA}','USAGE')
               or has_function_privilege(r,'{SCHEMA}.enter_correction()','EXECUTE')) then
  raise exception 'CP7_GLOBAL_DDL_FENCE_PRIVATE_EXPECTED';
 end if;
 perform {SCHEMA}.enter_correction();
 perform {SCHEMA}.enter_release();
end
$check$;
rollback;
select true as ordinary_role_verified, to_regnamespace('{SCHEMA}') is null as schema_rolled_back,
 not exists(select from pg_event_trigger where evtname='{TRIGGER}') as trigger_rolled_back;
"""


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(hosted_rehearsal(), end='')
