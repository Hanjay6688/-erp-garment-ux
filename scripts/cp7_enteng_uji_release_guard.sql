do $enteng_uji_precondition$
begin
 if session_user<>'postgres' or current_user<>'postgres' or current_setting('is_superuser')<>'off'
    or (select version from erp.schema_migrations order by installed_at desc,version desc limit 1)<>'v2.6.20bf'
    or (select count(*) from supabase_migrations.schema_migrations)<>138
    or to_regnamespace('cp7_global_release_guard') is not null
    or to_regnamespace('cp7_global_nonpo_envelope') is not null
    or exists(select from pg_event_trigger where evtname='cp7_global_release_ddl') then
  raise exception 'Expected the verified BF baseline and an empty release guard in Enteng Uji';
 end if;
end $enteng_uji_precondition$;
create schema cp7_global_release_guard authorization postgres;
revoke all on schema cp7_global_release_guard from public,anon,authenticated,service_role;

create function cp7_global_release_guard.lock_ddl() returns event_trigger
language plpgsql volatile security invoker set search_path=''
as $ddl_fence$
begin
 if not pg_catalog.pg_try_advisory_xact_lock(274831, 47409) then
  raise exception using errcode='55P03',message='CP7_GLOBAL_CORRECTION_IN_PROGRESS';
 end if;
end
$ddl_fence$;
revoke all on function cp7_global_release_guard.lock_ddl() from public,anon,authenticated,service_role;

create event trigger cp7_global_release_ddl on ddl_command_start
 execute function cp7_global_release_guard.lock_ddl();
alter event trigger cp7_global_release_ddl enable always;

create function cp7_global_release_guard.assert_ddl_fence() returns void
language plpgsql stable security invoker set search_path=''
as $ddl_assert$
begin
 if current_setting('event_triggers') <> 'on' or not exists (
   select from pg_event_trigger event
     join pg_proc fn on fn.oid=event.evtfoid
     join pg_namespace ns on ns.oid=fn.pronamespace
    where event.evtname='cp7_global_release_ddl' and event.evtevent='ddl_command_start'
      and event.evtenabled='A' and event.evttags is null
      and event.evtowner='postgres'::regrole
      and ns.nspname='cp7_global_release_guard' and ns.nspowner='postgres'::regrole
      and fn.proname='lock_ddl' and fn.proowner='postgres'::regrole
      and fn.pronargs=0 and fn.prorettype='event_trigger'::regtype
      and fn.provolatile='v' and not fn.prosecdef
      and fn.proconfig=array['search_path=""']
      and encode(sha256(convert_to(fn.prosrc,'UTF8')),'hex')='4c37f24965f9dedfd93e46985cc6e485799a977f22c53ae1a814beb125239eb7'
 ) then
   raise exception using errcode='55000',message='CP7_GLOBAL_DDL_FENCE_CHANGED';
 end if;
end
$ddl_assert$;

create function cp7_global_release_guard.enter_correction() returns void
language plpgsql volatile security invoker set search_path=''
as $ddl_reader$
begin
 if current_setting('transaction_isolation')<>'read committed' then
   raise exception using errcode='25001',message='CP7_GLOBAL_READ_COMMITTED_REQUIRED';
 end if;
 if not pg_try_advisory_xact_lock_shared(274831, 47409) then
   raise exception using errcode='55P03',message='CP7_GLOBAL_RELEASE_IN_PROGRESS';
 end if;
 perform cp7_global_release_guard.assert_ddl_fence();
end
$ddl_reader$;

create function cp7_global_release_guard.enter_release() returns void
language plpgsql volatile security invoker set search_path=''
as $ddl_writer$
begin
 if not pg_try_advisory_xact_lock(274831, 47409) then
   raise exception using errcode='55P03',message='CP7_GLOBAL_CORRECTION_IN_PROGRESS';
 end if;
 perform cp7_global_release_guard.assert_ddl_fence();
end
$ddl_writer$;
revoke all on all functions in schema cp7_global_release_guard from public,anon,authenticated,service_role;
select cp7_global_release_guard.assert_ddl_fence();

do $enteng_uji_postcondition$
begin
 if exists(select from unnest(array['anon','authenticated','service_role']) r
            where has_schema_privilege(r,'cp7_global_release_guard','USAGE')
               or has_function_privilege(r,'cp7_global_release_guard.enter_correction()','EXECUTE')
               or has_function_privilege(r,'cp7_global_release_guard.enter_release()','EXECUTE')) then
  raise exception 'The Enteng release guard must stay private';
 end if;
 perform cp7_global_release_guard.enter_release();
end $enteng_uji_postcondition$;
