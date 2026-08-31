-- Transactional acceptance for ERP Enteng UAT reminder ACL hardening v2.6.13a.
-- Run only against externally verified project siimvrusnzxexizpyoib.
-- The final ROLLBACK removes every synthetic row and request claim.

begin;

set local lock_timeout = '10s';
set local statement_timeout = '120s';

do $ledger_guard$
begin
  if current_user <> 'postgres' then
    raise exception 'REMINDER_ACL_TEST_GUARD: acceptance must run as postgres';
  end if;

  if (
       select count(*)
       from supabase_migrations.schema_migrations
       where version = '20260831031520'
         and name = 'manual_reminders_v1_acl_hardening'
         and cardinality(statements) = 1
         and octet_length(statements[1]) = 16026
         and md5(statements[1]) = '5e100cdddea2600d04e48b57f101f6eb'
     ) <> 1
     or (
       select count(*)
       from supabase_migrations.schema_migrations
       where version = '20260831032911'
         and name = 'erp_v2_6_13a_manual_reminders_acl_hardening'
         and cardinality(statements) = 1
         and octet_length(statements[1]) = 16008
         and md5(statements[1]) = '25b92a27481cea76d3c7edc19a02ee63'
     ) <> 1 then
    raise exception 'REMINDER_ACL_TEST_GUARD: exact UAT primary and duplicate-normalized ledger rows are missing or drifted';
  end if;

  -- Pin the live ACL before the test temporarily grants UPDATE. Without this
  -- precondition, GRANT/REVOKE could mask an UPDATE grant that already existed.
  if (select c.relowner<>to_regrole('postgres')::oid
             or not c.relrowsecurity or c.relforcerowsecurity
      from pg_class c where c.oid='erp.manual_reminders'::regclass)
     or exists (
       with relation_identity as (
         select c.relowner,c.relacl
         from pg_class c
         where c.oid='erp.manual_reminders'::regclass
       ), live_acl as (
         select a.grantor,a.grantee,a.privilege_type,a.is_grantable
         from relation_identity c
         cross join lateral aclexplode(
           coalesce(c.relacl,acldefault('r',c.relowner))
         ) a
       ), expected_acl as (
         select a.grantor,a.grantee,a.privilege_type,a.is_grantable
         from relation_identity c
         cross join lateral aclexplode(acldefault('r',c.relowner)) a
         union all
         select c.relowner,to_regrole('service_role')::oid,'SELECT'::text,false
         from relation_identity c
       ), acl_delta as (
         (select * from live_acl except all select * from expected_acl)
         union all
         (select * from expected_acl except all select * from live_acl)
       )
       select 1 from acl_delta
     )
     or exists (
       select 1 from pg_attribute a
       where a.attrelid='erp.manual_reminders'::regclass
         and a.attnum>0 and not a.attisdropped and a.attacl is not null
     )
     or not has_table_privilege(
       'service_role','erp.manual_reminders','SELECT'
     )
     or has_table_privilege(
       'service_role','erp.manual_reminders','UPDATE'
     ) then
    raise exception 'REMINDER_ACL_TEST_GUARD: live manual_reminders ACL is not exact service SELECT-only before mutation';
  end if;
end;
$ledger_guard$;

create or replace function pg_temp.run_manual_reminder_hardening_test()
returns jsonb
language plpgsql
as $test$
declare
  v_app_user uuid := '7d3e0a61-1001-4f10-8000-000000001001';
  v_auth_user uuid := '7d3e0a61-1101-4f10-8000-000000001101';
  v_request uuid := '7d3e0a61-1201-4f10-8000-000000001201';
  v_done_request uuid := '7d3e0a61-1202-4f10-8000-000000001202';
  v_reminder uuid;
  v_result jsonb;
  v_direct_update_blocked boolean := false;
  v_direct_update_sqlstate text;
  v_direct_update_message text;
  v_truncate_blocked boolean := false;
  v_private_rpc_blocked boolean := false;
  v_anon_facade_blocked boolean := false;
begin
  insert into erp.app_users(id,auth_user_id,full_name,role,is_active)
  values (v_app_user,v_auth_user,'TST Reminder ACL Owner','OWNER',true);

  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_auth_user,'role','authenticated'
  )::text,true);
  execute 'set local role authenticated';
  v_result:=public.erp_save_my_reminder_v1(jsonb_build_object(
    'title','TST-REMINDER-ACL-HARDENING',
    'note','RPC must remain authoritative after ACL hardening',
    'due_at','2026-09-01T09:00:00+07:00',
    'priority','NORMAL',
    'module','Operasional'
  ),v_request,null);
  v_reminder:=(v_result#>>'{reminder,id}')::uuid;
  v_result:=public.erp_set_my_reminder_done_v1(
    v_reminder,true,v_done_request,1
  );
  execute 'reset role';

  if v_reminder is null
     or (v_result->>'status') is distinct from 'DONE'
     or (v_result->>'row_version')::bigint is distinct from 2
     or (select count(*) from erp.audit_logs
         where entity_type='manual_reminders' and entity_id=v_reminder)
          is distinct from 2 then
    raise exception 'Authorized authenticated reminder facade regressed: %',v_result;
  end if;

  -- Temporarily grant UPDATE so this reaches the trigger and proves that a
  -- service_role caller cannot turn the routing GUC into write authority.
  execute 'grant update on table erp.manual_reminders to service_role';
  perform set_config('request.jwt.claims','{}',true);
  execute 'set local role service_role';
  perform set_config('app.manual_reminder_write','on',true);
  perform set_config('app.manual_reminder_action','FORGED',true);

  begin
    update erp.manual_reminders set title='FORGED' where id=v_reminder;
  exception when others then
    v_direct_update_sqlstate:=sqlstate;
    v_direct_update_message:=sqlerrm;
  end;
  execute 'reset role';
  execute 'revoke update on table erp.manual_reminders from service_role';

  v_direct_update_blocked:=
    v_direct_update_sqlstate is not distinct from 'P0001'
    and v_direct_update_message is not distinct from
      'Manual reminders are write-protected; use the reminder RPC facade';

  if not v_direct_update_blocked
     or (select title from erp.manual_reminders where id=v_reminder)
          is distinct from 'TST-REMINDER-ACL-HARDENING' then
    raise exception 'Forged reminder GUC did not hit the exact trigger denial: SQLSTATE %, message %',
      v_direct_update_sqlstate,v_direct_update_message;
  end if;

  execute 'set local role service_role';

  begin
    execute 'truncate table erp.manual_reminders';
  exception when insufficient_privilege then
    v_truncate_blocked:=true;
  end;

  begin
    perform erp.save_my_reminder_v1(jsonb_build_object(
      'title','FORGED PRIVATE CALL',
      'due_at','2026-09-02T09:00:00+07:00'
    ),gen_random_uuid(),null);
  exception when insufficient_privilege then
    v_private_rpc_blocked:=true;
  end;
  execute 'reset role';

  execute 'set local role anon';
  begin
    perform public.erp_list_my_reminders_v1('ALL',200);
  exception when insufficient_privilege then
    v_anon_facade_blocked:=true;
  end;
  execute 'reset role';

  if not (v_direct_update_blocked and v_truncate_blocked
          and v_private_rpc_blocked and v_anon_facade_blocked) then
    raise exception 'Reminder ACL denial matrix failed: update %, truncate %, private %, anon %',
      v_direct_update_blocked,v_truncate_blocked,
      v_private_rpc_blocked,v_anon_facade_blocked;
  end if;

  if not has_table_privilege('service_role','erp.manual_reminders','SELECT')
     or has_table_privilege('service_role','erp.manual_reminders','INSERT')
     or has_table_privilege('service_role','erp.manual_reminders','UPDATE')
     or has_table_privilege('service_role','erp.manual_reminders','DELETE')
     or has_table_privilege('service_role','erp.manual_reminders','TRUNCATE')
     or has_table_privilege('service_role','erp.manual_reminders','REFERENCES')
     or has_table_privilege('service_role','erp.manual_reminders','TRIGGER')
     or has_table_privilege('anon','erp.manual_reminders','SELECT')
     or has_table_privilege('authenticated','erp.manual_reminders','SELECT') then
    raise exception 'manual_reminders direct-table ACL is not exact service SELECT-only';
  end if;

  if exists (
    select 1
    from (values
      ('erp.guard_manual_reminder_write()'),
      ('erp.bump_row_version()'),
      ('erp.audit_manual_reminder_change()'),
      ('erp.require_manual_reminder_actor()'),
      ('erp.list_my_reminders_v1(text,integer)'),
      ('erp.save_my_reminder_v1(jsonb,uuid,bigint)'),
      ('erp.set_my_reminder_done_v1(uuid,boolean,uuid,bigint)'),
      ('erp.cancel_my_reminder_v1(uuid,text,uuid,bigint)')
    ) e(signature)
    where has_function_privilege('anon',to_regprocedure(e.signature),'EXECUTE')
       or has_function_privilege('authenticated',to_regprocedure(e.signature),'EXECUTE')
       or has_function_privilege('service_role',to_regprocedure(e.signature),'EXECUTE')
  ) then
    raise exception 'A private reminder implementation remains API-executable';
  end if;

  if exists (
    select 1
    from (values
      ('public.erp_list_my_reminders_v1(text,integer)'),
      ('public.erp_save_my_reminder_v1(jsonb,uuid,bigint)'),
      ('public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)'),
      ('public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)')
    ) e(signature)
    join pg_proc p on p.oid=to_regprocedure(e.signature)
    where not p.prosecdef
       or has_function_privilege('anon',p.oid,'EXECUTE')
       or not has_function_privilege('authenticated',p.oid,'EXECUTE')
       or not has_function_privilege('service_role',p.oid,'EXECUTE')
       or p.proowner<>to_regrole('postgres')::oid
  ) then
    raise exception 'A public reminder facade lost its exact authenticated/service contract';
  end if;

  if not (select c.relrowsecurity from pg_class c
          where c.oid='erp.manual_reminders'::regclass)
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
           and t.tgenabled='O' and t.tgqual is null and t.tgnargs=0
           and not t.tgisinternal
           and md5(pg_get_triggerdef(t.oid,true))=e.definition_md5
       )
     )
     or (select p.proowner<>to_regrole('postgres')::oid
                or p.prosecdef
                or p.provolatile<>'v'::"char"
                or p.proconfig is distinct from
                   array['search_path=erp, public, pg_temp']::text[]
                or md5(pg_get_functiondef(p.oid)) is distinct from
                   '63d58dca7617907c5547bdb71d111832'
         from pg_proc p
         where p.oid='erp.guard_manual_reminder_write()'::regprocedure)
     or (select p.proowner<>to_regrole('postgres')::oid
                or p.prosecdef or p.provolatile<>'v'::"char"
                or p.proconfig is distinct from
                   array['search_path=erp, public, pg_temp']::text[]
                or md5(pg_get_functiondef(p.oid)) is distinct from
                   'c53b58206389af747279e6397c258acd'
         from pg_proc p where p.oid='erp.bump_row_version()'::regprocedure)
     or (select p.proowner<>to_regrole('postgres')::oid
                or p.prosecdef
                or p.provolatile<>'i'::"char"
                or p.proconfig is distinct from
                   array['search_path=pg_catalog, pg_temp']::text[]
                or position('ERP_V2_6_13A_REMINDER_RPC_ONLY_V1' in
                   pg_get_functiondef(p.oid))=0
         from pg_proc p
         where p.oid=
           'erp.manual_reminders_v1_acl_hardening_marker()'::regprocedure)
     or exists (
       select 1
       from pg_proc p,
            lateral aclexplode(coalesce(p.proacl,
              acldefault('f',p.proowner))) a
       where p.oid=
         'erp.manual_reminders_v1_acl_hardening_marker()'::regprocedure
         and (a.is_grantable or a.grantee<>p.proowner
              or a.privilege_type<>'EXECUTE')
     ) then
    raise exception 'Reminder hardening trigger/function/marker identity drifted';
  end if;

  return jsonb_build_object(
    'authenticated_rpc_round_trip',true,
    'direct_guc_spoof_blocked',v_direct_update_blocked,
    'service_truncate_blocked',v_truncate_blocked,
    'private_rpc_blocked',v_private_rpc_blocked,
    'anon_blocked',v_anon_facade_blocked,
    'service_table_acl','SELECT_ONLY',
    'residue_check_required',true
  );
end;
$test$;

select pg_temp.run_manual_reminder_hardening_test() as result;

rollback;

do $residue$
declare
  v_residue_rows bigint;
begin
  select
    (select count(*) from erp.app_users
     where id='7d3e0a61-1001-4f10-8000-000000001001'::uuid)
    + (select count(*) from erp.manual_reminders
       where title='TST-REMINDER-ACL-HARDENING')
    + (select count(*) from erp.audit_logs
       where entity_type='manual_reminders'
         and changed_by='7d3e0a61-1001-4f10-8000-000000001001'::uuid)
    + (select count(*) from erp.idempotency_requests
       where client_request_id in (
         '7d3e0a61-1201-4f10-8000-000000001201'::uuid,
         '7d3e0a61-1202-4f10-8000-000000001202'::uuid
       ))
  into v_residue_rows;

  if v_residue_rows<>0 then
    raise exception 'Reminder ACL hardening rollback left % synthetic rows',
      v_residue_rows;
  end if;

  -- Re-prove the exact ACL after ROLLBACK. This catches a fixture that appeared
  -- to pass only because its temporary REVOKE hid a pre-existing insecure grant.
  if (select c.relowner<>to_regrole('postgres')::oid
             or not c.relrowsecurity or c.relforcerowsecurity
      from pg_class c where c.oid='erp.manual_reminders'::regclass)
     or exists (
       with relation_identity as (
         select c.relowner,c.relacl
         from pg_class c
         where c.oid='erp.manual_reminders'::regclass
       ), live_acl as (
         select a.grantor,a.grantee,a.privilege_type,a.is_grantable
         from relation_identity c
         cross join lateral aclexplode(
           coalesce(c.relacl,acldefault('r',c.relowner))
         ) a
       ), expected_acl as (
         select a.grantor,a.grantee,a.privilege_type,a.is_grantable
         from relation_identity c
         cross join lateral aclexplode(acldefault('r',c.relowner)) a
         union all
         select c.relowner,to_regrole('service_role')::oid,'SELECT'::text,false
         from relation_identity c
       ), acl_delta as (
         (select * from live_acl except all select * from expected_acl)
         union all
         (select * from expected_acl except all select * from live_acl)
       )
       select 1 from acl_delta
     )
     or exists (
       select 1 from pg_attribute a
       where a.attrelid='erp.manual_reminders'::regclass
         and a.attnum>0 and not a.attisdropped and a.attacl is not null
     )
     or not has_table_privilege(
       'service_role','erp.manual_reminders','SELECT'
     )
     or has_table_privilege(
       'service_role','erp.manual_reminders','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'
     )
     or has_table_privilege('anon','erp.manual_reminders','SELECT')
     or has_table_privilege('authenticated','erp.manual_reminders','SELECT') then
    raise exception 'Reminder ACL hardening rollback did not restore exact service SELECT-only ACL';
  end if;
end;
$residue$;

select jsonb_build_object(
  'status','PASS',
  'post_rollback_residue_rows',r.residue_rows
) as rollback_result
from (
  select
    (select count(*) from erp.app_users
     where id='7d3e0a61-1001-4f10-8000-000000001001'::uuid)
    + (select count(*) from erp.manual_reminders
       where title='TST-REMINDER-ACL-HARDENING')
    + (select count(*) from erp.audit_logs
       where entity_type='manual_reminders'
         and changed_by='7d3e0a61-1001-4f10-8000-000000001001'::uuid)
    + (select count(*) from erp.idempotency_requests
       where client_request_id in (
         '7d3e0a61-1201-4f10-8000-000000001201'::uuid,
         '7d3e0a61-1202-4f10-8000-000000001202'::uuid
       )) as residue_rows
) r;
