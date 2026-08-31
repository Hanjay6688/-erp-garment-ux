-- ERP Garment v2.6.13a
-- Forward-only hardening for the already-installed own-user reminder contract.
-- No reminder data or public facade signature is changed.

begin;

set local lock_timeout = '10s';
set local statement_timeout = '120s';

do $migration_guard$
declare
  v_marker regprocedure := to_regprocedure(
    'erp.manual_reminders_v1_acl_hardening_marker()'
  );
  v_definition_aggregate text;
  v_stable_definition_aggregate text;
begin
  if to_regclass('erp.manual_reminders') is null
     or to_regprocedure('erp.guard_manual_reminder_write()') is null
     or to_regprocedure('erp.bump_row_version()') is null
     or to_regprocedure('erp.audit_manual_reminder_change()') is null
     or to_regprocedure('erp.require_manual_reminder_actor()') is null
     or to_regprocedure('erp.list_my_reminders_v1(text,integer)') is null
     or to_regprocedure('erp.save_my_reminder_v1(jsonb,uuid,bigint)') is null
     or to_regprocedure('erp.set_my_reminder_done_v1(uuid,boolean,uuid,bigint)') is null
     or to_regprocedure('erp.cancel_my_reminder_v1(uuid,text,uuid,bigint)') is null
     or to_regprocedure('public.erp_list_my_reminders_v1(text,integer)') is null
     or to_regprocedure('public.erp_save_my_reminder_v1(jsonb,uuid,bigint)') is null
     or to_regprocedure('public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)') is null
     or to_regprocedure('public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)') is null then
    raise exception 'Reminder ACL hardening requires the complete ERP v2.6.13 reminder contract';
  end if;

  if has_schema_privilege('anon','erp','CREATE')
     or has_schema_privilege('authenticated','erp','CREATE')
     or has_schema_privilege('service_role','erp','CREATE')
     or has_schema_privilege('anon','public','CREATE')
     or has_schema_privilege('authenticated','public','CREATE')
     or has_schema_privilege('service_role','public','CREATE')
     or has_schema_privilege('anon','auth','CREATE')
     or has_schema_privilege('authenticated','auth','CREATE')
     or has_schema_privilege('service_role','auth','CREATE')
     or has_schema_privilege('anon','extensions','CREATE')
     or has_schema_privilege('authenticated','extensions','CREATE')
     or has_schema_privilege('service_role','extensions','CREATE') then
    raise exception 'Untrusted API roles must not CREATE in a reminder SECURITY DEFINER search_path schema';
  end if;

  select md5(string_agg(e.signature||':'||md5(pg_get_functiondef(
           to_regprocedure(e.signature))),E'\n' order by e.signature))
  into v_definition_aggregate
  from (values
    ('erp.guard_manual_reminder_write()'),
    ('erp.audit_manual_reminder_change()'),
    ('erp.require_manual_reminder_actor()'),
    ('erp.list_my_reminders_v1(text,integer)'),
    ('erp.save_my_reminder_v1(jsonb,uuid,bigint)'),
    ('erp.set_my_reminder_done_v1(uuid,boolean,uuid,bigint)'),
    ('erp.cancel_my_reminder_v1(uuid,text,uuid,bigint)'),
    ('public.erp_list_my_reminders_v1(text,integer)'),
    ('public.erp_save_my_reminder_v1(jsonb,uuid,bigint)'),
    ('public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)'),
    ('public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)')
  ) e(signature);

  -- Optimistic locking and append-only audit are part of the reminder write
  -- contract. Pin all trigger routes, including no-WHEN/no-argument shape,
  -- and the shared row-version helper before either a fresh hardening or replay.
  if (select p.proowner<>to_regrole('postgres')::oid
             or p.prosecdef
             or p.provolatile<>'v'::"char"
             or p.proconfig is distinct from
                array['search_path=erp, public, pg_temp']::text[]
             or md5(pg_get_functiondef(p.oid)) is distinct from
                'c53b58206389af747279e6397c258acd'
      from pg_proc p where p.oid='erp.bump_row_version()'::regprocedure)
     or exists (
       select 1
       from pg_proc p,
            lateral aclexplode(coalesce(p.proacl,
              acldefault('f',p.proowner))) a
       where p.oid='erp.bump_row_version()'::regprocedure
         and (a.is_grantable or a.grantee<>p.proowner
              or a.privilege_type<>'EXECUTE')
     )
     or (select count(*) from pg_trigger t
         where t.tgrelid='erp.manual_reminders'::regclass
           and not t.tgisinternal)<>3
     or exists (
       select 1
       from (values
         ('trg_00_guard_manual_reminder_write',
           'erp.guard_manual_reminder_write()'::regprocedure,
           'ea0d7ed5b4571688f8b421b5cf2d9747'),
         ('trg_01_bump_manual_reminder_version',
           'erp.bump_row_version()'::regprocedure,
           '56a244850f61e92a5d9da1770ebac281'),
         ('trg_90_audit_manual_reminder',
           'erp.audit_manual_reminder_change()'::regprocedure,
           '59b83ca7eb05fa3c21cf63e583e81bd8')
       ) e(tgname,tgfoid,definition_md5)
       where not exists (
         select 1 from pg_trigger t
         where t.tgrelid='erp.manual_reminders'::regclass
           and t.tgname=e.tgname and t.tgfoid=e.tgfoid
           and not t.tgisinternal and t.tgenabled='O'
           and t.tgqual is null and t.tgnargs=0
           and md5(pg_get_triggerdef(t.oid,true))=e.definition_md5
       )
     ) then
    raise exception 'Reminder audit/version trigger or bump helper identity drifted';
  end if;

  select md5(string_agg(e.signature||':'||md5(pg_get_functiondef(
           to_regprocedure(e.signature))),E'\n' order by e.signature))
  into v_stable_definition_aggregate
  from (values
    ('erp.audit_manual_reminder_change()'),
    ('erp.require_manual_reminder_actor()'),
    ('erp.list_my_reminders_v1(text,integer)'),
    ('erp.save_my_reminder_v1(jsonb,uuid,bigint)'),
    ('erp.set_my_reminder_done_v1(uuid,boolean,uuid,bigint)'),
    ('erp.cancel_my_reminder_v1(uuid,text,uuid,bigint)'),
    ('public.erp_list_my_reminders_v1(text,integer)'),
    ('public.erp_save_my_reminder_v1(jsonb,uuid,bigint)'),
    ('public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)'),
    ('public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)')
  ) e(signature);

  if v_marker is null then
    if v_definition_aggregate is distinct from
         '28cd9257bf921cf769ca5b1752533e1c'
       or (select p.proowner<>to_regrole('postgres')::oid
                    or p.prosecdef
                    or p.provolatile<>'v'::"char"
                    or p.proconfig is distinct from
                       array['search_path=erp, public, pg_temp']::text[]
           from pg_proc p
           where p.oid='erp.guard_manual_reminder_write()'::regprocedure)
       or not has_table_privilege('service_role','erp.manual_reminders','SELECT')
       or not has_table_privilege('service_role','erp.manual_reminders','INSERT')
       or not has_table_privilege('service_role','erp.manual_reminders','UPDATE')
       or not has_table_privilege('service_role','erp.manual_reminders','DELETE')
       or not has_table_privilege('service_role','erp.manual_reminders','TRUNCATE')
       or has_table_privilege('anon','erp.manual_reminders','SELECT')
       or has_table_privilege('authenticated','erp.manual_reminders','SELECT') then
      raise exception 'Reminder v2.6.13 baseline drifted; refusing partial ACL hardening';
    end if;
  else
    if position('ERP_V2_6_13A_REMINDER_RPC_ONLY_V1' in
         pg_get_functiondef(v_marker))=0
       or v_stable_definition_aggregate is distinct from
          '514f765a5153d8fda88fcd79f662a283'
       or md5(pg_get_functiondef(
          'erp.guard_manual_reminder_write()'::regprocedure)) is distinct from
          '63d58dca7617907c5547bdb71d111832'
       or position('current_user <> ''postgres''' in pg_get_functiondef(
         'erp.guard_manual_reminder_write()'::regprocedure))=0
       or not (select c.relrowsecurity from pg_class c
               where c.oid='erp.manual_reminders'::regclass)
       or (select c.relowner<>to_regrole('postgres')::oid
           from pg_class c where c.oid='erp.manual_reminders'::regclass)
       or not has_table_privilege('service_role','erp.manual_reminders','SELECT')
       or has_table_privilege('service_role','erp.manual_reminders','INSERT')
       or has_table_privilege('service_role','erp.manual_reminders','UPDATE')
       or has_table_privilege('service_role','erp.manual_reminders','DELETE')
       or has_table_privilege('service_role','erp.manual_reminders','TRUNCATE')
       or has_table_privilege('service_role','erp.manual_reminders','REFERENCES')
       or has_table_privilege('service_role','erp.manual_reminders','TRIGGER')
       or has_table_privilege('anon','erp.manual_reminders','SELECT')
       or has_table_privilege('authenticated','erp.manual_reminders','SELECT')
       or exists (
         select 1
         from pg_class c,
              lateral aclexplode(coalesce(c.relacl,
                acldefault('r',c.relowner))) a
         where c.oid='erp.manual_reminders'::regclass
           and (
             a.is_grantable
             or a.grantee not in (c.relowner,to_regrole('service_role')::oid)
             or (a.grantee=to_regrole('service_role')::oid
                 and a.privilege_type<>'SELECT')
           )
       )
       or exists (
         select 1
         from (values
           ('erp.guard_manual_reminder_write()'),
           ('erp.audit_manual_reminder_change()'),
           ('erp.require_manual_reminder_actor()'),
           ('erp.list_my_reminders_v1(text,integer)'),
           ('erp.save_my_reminder_v1(jsonb,uuid,bigint)'),
           ('erp.set_my_reminder_done_v1(uuid,boolean,uuid,bigint)'),
           ('erp.cancel_my_reminder_v1(uuid,text,uuid,bigint)')
         ) e(signature)
         join pg_proc p on p.oid=to_regprocedure(e.signature)
         where p.proowner<>to_regrole('postgres')::oid
            or has_function_privilege('anon',p.oid,'EXECUTE')
            or has_function_privilege('authenticated',p.oid,'EXECUTE')
            or has_function_privilege('service_role',p.oid,'EXECUTE')
            or exists (
              select 1 from aclexplode(coalesce(p.proacl,
                acldefault('f',p.proowner))) a
              where a.is_grantable or a.grantee<>p.proowner
                 or a.privilege_type<>'EXECUTE'
            )
       )
       or exists (
         select 1
         from (values
           ('public.erp_list_my_reminders_v1(text,integer)'),
           ('public.erp_save_my_reminder_v1(jsonb,uuid,bigint)'),
           ('public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)'),
           ('public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)')
         ) e(signature)
         join pg_proc p on p.oid=to_regprocedure(e.signature)
         where p.proowner<>to_regrole('postgres')::oid
            or not p.prosecdef
            or has_function_privilege('anon',p.oid,'EXECUTE')
            or not has_function_privilege('authenticated',p.oid,'EXECUTE')
            or not has_function_privilege('service_role',p.oid,'EXECUTE')
            or exists (
              select 1 from aclexplode(coalesce(p.proacl,
                acldefault('f',p.proowner))) a
              where a.is_grantable
                 or a.privilege_type<>'EXECUTE'
                 or a.grantee not in (
                   p.proowner,to_regrole('authenticated')::oid,
                   to_regrole('service_role')::oid
                 )
            )
       )
       or (select p.proowner<>to_regrole('postgres')::oid
                  or p.prosecdef
                  or p.provolatile<>'i'::"char"
                  or p.proconfig is distinct from
                     array['search_path=pg_catalog, pg_temp']::text[]
           from pg_proc p where p.oid=v_marker)
       or exists (
         select 1
         from pg_proc p,
              lateral aclexplode(coalesce(p.proacl,
                acldefault('f',p.proowner))) a
         where p.oid=v_marker
           and (a.is_grantable or a.grantee<>p.proowner
                or a.privilege_type<>'EXECUTE')
       ) then
      raise exception 'Reminder v2.6.13a marker exists but hardened shape drifted';
    end if;
    return;
  end if;
end;
$migration_guard$;

create or replace function erp.guard_manual_reminder_write()
returns trigger
language plpgsql
security invoker
set search_path = erp, public, pg_temp
as $function$
begin
  if tg_op = 'DELETE' then
    raise exception 'Manual reminders cannot be deleted; use erp_cancel_my_reminder_v1';
  end if;

  -- A custom GUC is only routing context, never authority. Browser/API roles,
  -- including service_role, cannot authorize direct table DML by spoofing it.
  if current_user <> 'postgres'
     or current_setting('app.manual_reminder_write', true) is distinct from 'on' then
    raise exception 'Manual reminders are write-protected; use the reminder RPC facade';
  end if;

  if tg_op = 'UPDATE' then
    if (new.id, new.owner_user_id, new.created_at, new.created_by)
       is distinct from
       (old.id, old.owner_user_id, old.created_at, old.created_by) then
      raise exception 'Reminder identity, owner, and creation facts are immutable';
    end if;
    if old.status = 'CANCELLED' then
      raise exception 'Cancelled reminders are terminal';
    end if;
  end if;

  return new;
end;
$function$;

alter function erp.guard_manual_reminder_write() owner to postgres;
alter function erp.guard_manual_reminder_write() security invoker;

alter table erp.manual_reminders enable row level security;

revoke all on table erp.manual_reminders
  from public, anon, authenticated, service_role;
grant select on table erp.manual_reminders to service_role;

revoke all on function erp.guard_manual_reminder_write()
  from public, anon, authenticated, service_role;
revoke all on function erp.audit_manual_reminder_change()
  from public, anon, authenticated, service_role;
revoke all on function erp.require_manual_reminder_actor()
  from public, anon, authenticated, service_role;
revoke all on function erp.list_my_reminders_v1(text,integer)
  from public, anon, authenticated, service_role;
revoke all on function erp.save_my_reminder_v1(jsonb,uuid,bigint)
  from public, anon, authenticated, service_role;
revoke all on function erp.set_my_reminder_done_v1(uuid,boolean,uuid,bigint)
  from public, anon, authenticated, service_role;
revoke all on function erp.cancel_my_reminder_v1(uuid,text,uuid,bigint)
  from public, anon, authenticated, service_role;

-- Reassert the narrow browser surface exactly. The private implementations
-- execute as postgres through these SECURITY DEFINER facades.
revoke all on function public.erp_list_my_reminders_v1(text,integer)
  from public, anon, authenticated, service_role;
revoke all on function public.erp_save_my_reminder_v1(jsonb,uuid,bigint)
  from public, anon, authenticated, service_role;
revoke all on function public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)
  from public, anon, authenticated, service_role;
revoke all on function public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)
  from public, anon, authenticated, service_role;

grant execute on function public.erp_list_my_reminders_v1(text,integer)
  to authenticated, service_role;
grant execute on function public.erp_save_my_reminder_v1(jsonb,uuid,bigint)
  to authenticated, service_role;
grant execute on function public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)
  to authenticated, service_role;
grant execute on function public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)
  to authenticated, service_role;

comment on table erp.manual_reminders is
  'Own-user manual reminders. Writes are RPC-only; service_role has SELECT only and no TRUNCATE/DML authority.';

create or replace function erp.manual_reminders_v1_acl_hardening_marker()
returns text
language sql
immutable
set search_path = pg_catalog, pg_temp
as $function$
  select 'ERP_V2_6_13A_REMINDER_RPC_ONLY_V1'::text
$function$;

revoke all on function erp.manual_reminders_v1_acl_hardening_marker()
  from public, anon, authenticated, service_role;

notify pgrst, 'reload schema';

commit;
