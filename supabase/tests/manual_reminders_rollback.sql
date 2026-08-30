-- Transactional acceptance for ERP Garment manual reminders V1.
-- Run only after 20260830182142_manual_reminders_v1.sql.
-- Every synthetic row is rolled back by the final ROLLBACK.

begin;

create or replace function pg_temp.run_manual_reminders_test()
returns jsonb
language plpgsql
as $test$
declare
  -- Fixed synthetic identities let the post-ROLLBACK query prove residue is zero.
  v_owner_a uuid := '7d3e0a61-0001-4f10-8000-000000000001';
  v_owner_b uuid := '7d3e0a61-0002-4f10-8000-000000000002';
  v_customer uuid := '7d3e0a61-0003-4f10-8000-000000000003';
  v_inactive uuid := '7d3e0a61-0004-4f10-8000-000000000004';
  v_auth_a uuid := '7d3e0a61-0101-4f10-8000-000000000101';
  v_auth_b uuid := '7d3e0a61-0102-4f10-8000-000000000102';
  v_auth_customer uuid := '7d3e0a61-0103-4f10-8000-000000000103';
  v_auth_inactive uuid := '7d3e0a61-0104-4f10-8000-000000000104';
  v_create_request uuid := gen_random_uuid();
  v_edit_request uuid := gen_random_uuid();
  v_done_request uuid := gen_random_uuid();
  v_done_noop_request uuid := gen_random_uuid();
  v_reopen_request uuid := gen_random_uuid();
  v_save_noop_request uuid := gen_random_uuid();
  v_cancel_request uuid := gen_random_uuid();
  v_other_create_request uuid := gen_random_uuid();
  v_reminder_id uuid;
  v_other_reminder_id uuid;
  v_created jsonb;
  v_other_created jsonb;
  v_create_replay jsonb;
  v_edited jsonb;
  v_done jsonb;
  v_done_replay jsonb;
  v_done_noop jsonb;
  v_reopened jsonb;
  v_save_noop jsonb;
  v_cancelled jsonb;
  v_authenticated_done jsonb;
  v_authenticated_cancelled jsonb;
  v_list jsonb;
  v_version bigint;
  v_audit_count integer;
  v_idempotency_count integer;
  v_index_count integer;
  v_rls_a_total integer;
  v_rls_a_owned integer;
  v_rls_b_total integer;
  v_rls_b_owned integer;
  v_authenticated_facades_passed boolean := false;
  v_runtime_rls_passed boolean := false;
  v_payload_mismatch_blocked boolean := false;
  v_stale_version_blocked boolean := false;
  v_done_edit_blocked boolean := false;
  v_blank_reason_blocked boolean := false;
  v_terminal_done_blocked boolean := false;
  v_terminal_edit_blocked boolean := false;
  v_cross_owner_blocked boolean := false;
  v_customer_blocked boolean := false;
  v_inactive_blocked boolean := false;
  v_anon_blocked boolean := false;
  v_hard_delete_blocked boolean := false;
  v_direct_insert_blocked boolean := false;
  v_direct_update_blocked boolean := false;
  v_unsupported_field_blocked boolean := false;
  v_non_scalar_field_blocked boolean := false;
  v_implicit_timezone_blocked boolean := false;
  v_infinite_due_blocked boolean := false;
begin
  insert into erp.app_users(id, auth_user_id, full_name, role, is_active)
  values
    (v_owner_a, v_auth_a, 'TST Reminder Owner A', 'OWNER', true),
    (v_owner_b, v_auth_b, 'TST Reminder Owner B', 'STAFF', true),
    (v_customer, v_auth_customer, 'TST Reminder Customer', 'CUSTOMER', true),
    (v_inactive, v_auth_inactive, 'TST Reminder Inactive', 'OWNER', false);

  perform set_config(
    'request.jwt.claims',
    jsonb_build_object('sub', v_auth_a, 'role', 'authenticated')::text,
    true
  );

  v_created := public.erp_save_my_reminder_v1(
    jsonb_build_object(
      'title', 'TST-REMINDER-PRIVATE-TITLE',
      'note', 'TST-REMINDER-PRIVATE-NOTE',
      'due_at', '2026-08-31T09:00:00+07:00',
      'priority', 'URGENT',
      'module', 'Laundry'
    ),
    v_create_request,
    null
  );
  v_reminder_id := (v_created#>>'{reminder,id}')::uuid;

  if v_reminder_id is null
     or (v_created#>>'{reminder,row_version}')::bigint is distinct from 1
     or (v_created#>>'{reminder,status}') is distinct from 'OPEN' then
    raise exception 'Reminder create returned an invalid authoritative row: %', v_created;
  end if;

  if (select due_at from erp.manual_reminders where id = v_reminder_id)
       is distinct from timestamptz '2026-08-31 02:00:00+00' then
    raise exception 'WIB due_at did not round-trip to the correct UTC instant';
  end if;

  select count(*) into v_audit_count
  from erp.audit_logs
  where entity_type = 'manual_reminders' and entity_id = v_reminder_id;

  v_create_replay := public.erp_save_my_reminder_v1(
    jsonb_build_object(
      'title', 'TST-REMINDER-PRIVATE-TITLE',
      'note', 'TST-REMINDER-PRIVATE-NOTE',
      'due_at', '2026-08-31T09:00:00+07:00',
      'priority', 'URGENT',
      'module', 'Laundry'
    ),
    v_create_request,
    null
  );
  if v_create_replay is distinct from v_created
     or (select count(*) from erp.manual_reminders where id = v_reminder_id) is distinct from 1
     or (select count(*) from erp.audit_logs where entity_type = 'manual_reminders' and entity_id = v_reminder_id)
        is distinct from v_audit_count then
    raise exception 'Create idempotency replay changed response, row count, or audit count';
  end if;

  begin
    perform public.erp_save_my_reminder_v1(
      jsonb_build_object(
        'title', 'TST-REMINDER-DIFFERENT-PAYLOAD',
        'note', 'TST-REMINDER-PRIVATE-NOTE',
        'due_at', '2026-08-31T09:00:00+07:00',
        'priority', 'URGENT',
        'module', 'Laundry'
      ),
      v_create_request,
      null
    );
  exception when others then
    if sqlerrm like 'client_request_id was already used with a different payload%' then
      v_payload_mismatch_blocked := true;
    else
      raise;
    end if;
  end;

  begin
    perform public.erp_save_my_reminder_v1(
      jsonb_build_object(
        'title', 'Bad unsupported payload',
        'due_at', '2026-08-31T09:00:00+07:00',
        'owner_user_id', v_owner_b
      ),
      gen_random_uuid(),
      null
    );
  exception when others then
    if sqlerrm = 'Reminder payload contains unsupported fields' then
      v_unsupported_field_blocked := true;
    else
      raise;
    end if;
  end;

  begin
    perform public.erp_save_my_reminder_v1(
      jsonb_build_object(
        'title', jsonb_build_object('nested', 'not allowed'),
        'due_at', '2026-08-31T09:00:00+07:00'
      ),
      gen_random_uuid(),
      null
    );
  exception when others then
    if sqlerrm = 'Reminder payload fields must be strings or null' then
      v_non_scalar_field_blocked := true;
    else
      raise;
    end if;
  end;

  begin
    perform public.erp_save_my_reminder_v1(
      jsonb_build_object('title', 'Implicit timezone', 'due_at', '2026-08-31T09:00:00'),
      gen_random_uuid(),
      null
    );
  exception when others then
    if sqlerrm = 'Reminder due_at must be ISO-8601 with an explicit UTC offset' then
      v_implicit_timezone_blocked := true;
    else
      raise;
    end if;
  end;

  begin
    perform public.erp_save_my_reminder_v1(
      jsonb_build_object('title', 'Infinite due', 'due_at', 'infinity'),
      gen_random_uuid(),
      null
    );
  exception when others then
    if sqlerrm like 'Reminder due_at must be ISO-8601 with an explicit UTC offset%'
       or sqlerrm = 'Reminder due_at must be finite' then
      v_infinite_due_blocked := true;
    else
      raise;
    end if;
  end;

  v_edited := public.erp_save_my_reminder_v1(
    jsonb_build_object(
      'id', v_reminder_id,
      'title', 'TST-REMINDER-PRIVATE-TITLE-EDITED',
      'note', 'TST-REMINDER-PRIVATE-NOTE-EDITED',
      'due_at', '2026-09-01T10:30:00+07:00',
      'priority', 'NORMAL',
      'module', 'Bagi Potongan'
    ),
    v_edit_request,
    1
  );
  if (v_edited#>>'{reminder,row_version}')::bigint is distinct from 2 then
    raise exception 'Reminder edit did not bump row_version exactly once';
  end if;

  begin
    perform public.erp_save_my_reminder_v1(
      jsonb_build_object(
        'id', v_reminder_id,
        'title', 'Stale overwrite',
        'note', '',
        'due_at', '2026-09-02T10:30:00+07:00',
        'priority', 'LOW',
        'module', 'Operasional'
      ),
      gen_random_uuid(),
      1
    );
  exception when others then
    if sqlerrm like 'STALE_VERSION expected 1, current 2%' then
      v_stale_version_blocked := true;
    else
      raise;
    end if;
  end;

  v_done := public.erp_set_my_reminder_done_v1(v_reminder_id, true, v_done_request, 2);
  v_done_replay := public.erp_set_my_reminder_done_v1(v_reminder_id, true, v_done_request, 2);
  if v_done_replay is distinct from v_done
     or (v_done->>'status') is distinct from 'DONE'
     or (v_done->>'row_version')::bigint is distinct from 3 then
    raise exception 'DONE transition or replay is invalid: % / %', v_done, v_done_replay;
  end if;

  v_audit_count := (
    select count(*) from erp.audit_logs
    where entity_type = 'manual_reminders' and entity_id = v_reminder_id
  );
  v_done_noop := public.erp_set_my_reminder_done_v1(v_reminder_id, true, v_done_noop_request, 3);
  if (v_done_noop->>'row_version')::bigint is distinct from 3
     or (select count(*) from erp.audit_logs where entity_type = 'manual_reminders' and entity_id = v_reminder_id)
        is distinct from v_audit_count then
    raise exception 'DONE no-op unexpectedly bumped version or audit';
  end if;

  begin
    perform public.erp_save_my_reminder_v1(
      jsonb_build_object(
        'id', v_reminder_id,
        'title', 'Edit done should fail',
        'note', '',
        'due_at', '2026-09-01T10:30:00+07:00',
        'priority', 'NORMAL',
        'module', 'Bagi Potongan'
      ),
      gen_random_uuid(),
      3
    );
  exception when others then
    if sqlerrm like 'Only OPEN reminders can be edited%' then
      v_done_edit_blocked := true;
    else
      raise;
    end if;
  end;

  v_reopened := public.erp_set_my_reminder_done_v1(v_reminder_id, false, v_reopen_request, 3);
  if (v_reopened->>'status') is distinct from 'OPEN'
     or (v_reopened->>'row_version')::bigint is distinct from 4
     or (select completed_at from erp.manual_reminders where id = v_reminder_id) is not null then
    raise exception 'Reopen did not clear completion facts exactly once';
  end if;

  v_audit_count := (
    select count(*) from erp.audit_logs
    where entity_type = 'manual_reminders' and entity_id = v_reminder_id
  );
  v_save_noop := public.erp_save_my_reminder_v1(
    jsonb_build_object(
      'id', v_reminder_id,
      'title', 'TST-REMINDER-PRIVATE-TITLE-EDITED',
      'note', 'TST-REMINDER-PRIVATE-NOTE-EDITED',
      'due_at', '2026-09-01T10:30:00+07:00',
      'priority', 'NORMAL',
      'module', 'Bagi Potongan'
    ),
    v_save_noop_request,
    4
  );
  if (v_save_noop#>>'{reminder,row_version}')::bigint is distinct from 4
     or (select count(*) from erp.audit_logs where entity_type = 'manual_reminders' and entity_id = v_reminder_id)
        is distinct from v_audit_count then
    raise exception 'Save no-op unexpectedly bumped version or audit';
  end if;

  begin
    perform public.erp_cancel_my_reminder_v1(v_reminder_id, '   ', gen_random_uuid(), 4);
  exception when others then
    if sqlerrm like 'Cancellation reason must contain 1 to 1000 characters%' then
      v_blank_reason_blocked := true;
    else
      raise;
    end if;
  end;

  v_cancelled := public.erp_cancel_my_reminder_v1(
    v_reminder_id,
    'TST-REMINDER-PRIVATE-CANCEL-REASON',
    v_cancel_request,
    4
  );
  if (v_cancelled->>'status') is distinct from 'CANCELLED'
     or (v_cancelled->>'row_version')::bigint is distinct from 5 then
    raise exception 'Cancel did not create a terminal version 5';
  end if;

  begin
    perform public.erp_set_my_reminder_done_v1(v_reminder_id, true, gen_random_uuid(), 5);
  exception when others then
    if sqlerrm = 'Cancelled reminders are terminal' then
      v_terminal_done_blocked := true;
    else
      raise;
    end if;
  end;

  begin
    perform public.erp_save_my_reminder_v1(
      jsonb_build_object(
        'id', v_reminder_id,
        'title', 'Terminal edit',
        'note', '',
        'due_at', '2026-09-01T10:30:00+07:00',
        'priority', 'NORMAL',
        'module', 'Operasional'
      ),
      gen_random_uuid(),
      5
    );
  exception when others then
    if sqlerrm like 'Only OPEN reminders can be edited%'
       or sqlerrm = 'Cancelled reminders are terminal' then
      v_terminal_edit_blocked := true;
    else
      raise;
    end if;
  end;

  v_list := public.erp_list_my_reminders_v1('ACTIVE', 200);
  if jsonb_array_length(v_list->'items') is distinct from 0
     or (v_list#>>'{counts,cancelled}')::integer is distinct from 1 then
    raise exception 'ACTIVE filter did not hide the cancelled reminder: %', v_list;
  end if;
  v_list := public.erp_list_my_reminders_v1('CANCELLED', 200);
  if jsonb_array_length(v_list->'items') is distinct from 1 then
    raise exception 'CANCELLED filter did not return the owner reminder';
  end if;

  perform set_config(
    'request.jwt.claims',
    jsonb_build_object('sub', v_auth_b, 'role', 'authenticated')::text,
    true
  );
  -- Exercise the browser facades with the real SQL role used by PostgREST.
  execute 'set local role authenticated';
  v_list := public.erp_list_my_reminders_v1('ALL', 200);
  if jsonb_array_length(v_list->'items') is distinct from 0 then
    raise exception 'Owner B could read Owner A reminders';
  end if;

  begin
    perform public.erp_set_my_reminder_done_v1(v_reminder_id, true, gen_random_uuid(), 5);
  exception when others then
    if sqlerrm = 'Reminder not found' then
      v_cross_owner_blocked := true;
    else
      raise;
    end if;
  end;

  v_other_created := public.erp_save_my_reminder_v1(
    jsonb_build_object(
      'title', 'TST Owner B past-due reminder',
      'note', '',
      'due_at', '2020-01-01T00:00:00Z',
      'priority', 'LOW',
      'module', 'Operasional'
    ),
    v_other_create_request,
    null
  );
  v_other_reminder_id := (v_other_created#>>'{reminder,id}')::uuid;
  if v_other_reminder_id is null then raise exception 'Past-due reminder was not accepted'; end if;

  v_authenticated_done := public.erp_set_my_reminder_done_v1(
    v_other_reminder_id, true, gen_random_uuid(), 1
  );
  v_authenticated_cancelled := public.erp_cancel_my_reminder_v1(
    v_other_reminder_id, 'TST actual authenticated facade cancellation', gen_random_uuid(), 2
  );
  if (v_authenticated_done->>'status') is distinct from 'DONE'
     or (v_authenticated_done->>'row_version')::bigint is distinct from 2
     or (v_authenticated_cancelled->>'status') is distinct from 'CANCELLED'
     or (v_authenticated_cancelled->>'row_version')::bigint is distinct from 3 then
    raise exception 'Actual authenticated facade lifecycle failed: % / %',
      v_authenticated_done, v_authenticated_cancelled;
  end if;
  v_authenticated_facades_passed := true;
  execute 'reset role';

  perform set_config(
    'request.jwt.claims',
    jsonb_build_object('sub', v_auth_customer, 'role', 'authenticated')::text,
    true
  );
  execute 'set local role authenticated';
  begin
    perform public.erp_list_my_reminders_v1('ACTIVE', 10);
  exception when others then
    if sqlerrm like 'Mapped active internal ERP user required%'
       or sqlerrm like 'Internal ERP access required%' then
      v_customer_blocked := true;
    else
      raise;
    end if;
  end;
  execute 'reset role';

  perform set_config(
    'request.jwt.claims',
    jsonb_build_object('sub', v_auth_inactive, 'role', 'authenticated')::text,
    true
  );
  execute 'set local role authenticated';
  begin
    perform public.erp_list_my_reminders_v1('ACTIVE', 10);
  exception when others then
    if sqlerrm like 'Mapped active internal ERP user required%'
       or sqlerrm like 'Internal ERP access required%' then
      v_inactive_blocked := true;
    else
      raise;
    end if;
  end;
  execute 'reset role';

  perform set_config('request.jwt.claims', '{"role":"anon"}', true);
  execute 'set local role anon';
  begin
    perform public.erp_list_my_reminders_v1('ACTIVE', 10);
  exception when sqlstate '42501' then
    v_anon_blocked := true;
  end;
  execute 'reset role';

  perform set_config(
    'request.jwt.claims',
    jsonb_build_object('sub', v_auth_a, 'role', 'authenticated')::text,
    true
  );
  begin
    insert into erp.manual_reminders(
      owner_user_id, title, note, due_at, priority, module,
      created_by, updated_by, last_client_request_id
    ) values (
      v_owner_a, 'Direct insert forbidden', '', clock_timestamp(), 'NORMAL', 'Operasional',
      v_owner_a, v_owner_a, gen_random_uuid()
    );
  exception when others then
    if sqlerrm like 'Manual reminders are write-protected%' then
      v_direct_insert_blocked := true;
    else
      raise;
    end if;
  end;
  begin
    update erp.manual_reminders
    set title = 'Direct update forbidden'
    where id = v_reminder_id;
  exception when others then
    if sqlerrm like 'Manual reminders are write-protected%' then
      v_direct_update_blocked := true;
    else
      raise;
    end if;
  end;
  perform set_config('app.manual_reminder_write', 'on', true);
  begin
    delete from erp.manual_reminders where id = v_reminder_id;
  exception when others then
    if sqlerrm like 'Manual reminders cannot be deleted%' then
      v_hard_delete_blocked := true;
    else
      raise;
    end if;
  end;
  perform set_config('app.manual_reminder_write', 'off', true);

  select count(*) into v_audit_count
  from erp.audit_logs
  where entity_type = 'manual_reminders' and entity_id = v_reminder_id;
  if v_audit_count is distinct from 5 then
    raise exception 'Reminder audit count expected 5 fact changes, got %', v_audit_count;
  end if;
  if exists (
    select 1
    from erp.audit_logs a
    where a.entity_type = 'manual_reminders'
      and a.entity_id = v_reminder_id
      and concat_ws(' ', a.old_data::text, a.new_data::text, a.change_reason) similar to
          '%(TST-REMINDER|2026-08-31|2026-09-01|URGENT|NORMAL|Laundry|Bagi Potongan)%'
  ) then
    raise exception 'Shared audit log leaked reminder content or schedule metadata';
  end if;
  if exists (
    select 1
    from erp.audit_logs a
    where a.entity_type = 'manual_reminders'
      and a.entity_id = v_reminder_id
      and a.changed_by is distinct from v_owner_a
  ) then
    raise exception 'Reminder audit attribution is not the authoritative Owner A actor';
  end if;
  if (select cancellation_reason from erp.manual_reminders where id = v_reminder_id)
       is distinct from 'TST-REMINDER-PRIVATE-CANCEL-REASON' then
    raise exception 'Private cancellation reason was not retained on the reminder row';
  end if;

  select count(*) into v_idempotency_count
  from erp.idempotency_requests r
  where r.actor_key = v_owner_a::text
    and r.operation_name in (
      'save_my_reminder_v1','set_my_reminder_done_v1','cancel_my_reminder_v1'
    );
  if v_idempotency_count is distinct from 7 then
    raise exception 'Expected 7 completed/no-op Owner A idempotency rows, got %', v_idempotency_count;
  end if;
  if exists (
    select 1
    from erp.idempotency_requests r
    where r.actor_key = v_owner_a::text
      and r.operation_name in (
        'save_my_reminder_v1','set_my_reminder_done_v1','cancel_my_reminder_v1'
      )
      and (r.status is distinct from 'COMPLETED' or r.response_payload is null)
  ) then
    raise exception 'An Owner A idempotency row is not COMPLETED with a cached response';
  end if;

  if current_setting('app.manual_reminder_write', true) is distinct from 'off'
     or current_setting('app.manual_reminder_action', true) is distinct from '' then
    raise exception 'Reminder write capability GUC leaked after RPC completion';
  end if;

  if not v_payload_mismatch_blocked
     or not v_stale_version_blocked
     or not v_done_edit_blocked
     or not v_blank_reason_blocked
     or not v_terminal_done_blocked
     or not v_terminal_edit_blocked
     or not v_cross_owner_blocked
     or not v_customer_blocked
     or not v_inactive_blocked
     or not v_anon_blocked
     or not v_authenticated_facades_passed
     or not v_hard_delete_blocked
     or not v_direct_insert_blocked
     or not v_direct_update_blocked
     or not v_unsupported_field_blocked
     or not v_non_scalar_field_blocked
     or not v_implicit_timezone_blocked
     or not v_infinite_due_blocked then
    raise exception 'One or more negative controls did not fire: %', jsonb_build_object(
      'payload_mismatch', v_payload_mismatch_blocked,
      'stale_version', v_stale_version_blocked,
      'done_edit', v_done_edit_blocked,
      'blank_reason', v_blank_reason_blocked,
      'terminal_done', v_terminal_done_blocked,
      'terminal_edit', v_terminal_edit_blocked,
      'cross_owner', v_cross_owner_blocked,
      'customer', v_customer_blocked,
      'inactive', v_inactive_blocked,
      'anon', v_anon_blocked,
      'authenticated_facades', v_authenticated_facades_passed,
      'hard_delete', v_hard_delete_blocked,
      'direct_insert', v_direct_insert_blocked,
      'direct_update', v_direct_update_blocked,
      'unsupported_field', v_unsupported_field_blocked,
      'non_scalar_field', v_non_scalar_field_blocked,
      'implicit_timezone', v_implicit_timezone_blocked,
      'infinite_due', v_infinite_due_blocked
    );
  end if;

  -- Temporarily expose SELECT only inside this rollback transaction so the
  -- real authenticated role exercises the table policy, not a catalog string.
  execute 'grant select on erp.manual_reminders to authenticated';
  perform set_config(
    'request.jwt.claims',
    jsonb_build_object('sub', v_auth_a, 'role', 'authenticated')::text,
    true
  );
  execute 'set local role authenticated';
  select count(*), count(*) filter (where owner_user_id = v_owner_a)
  into v_rls_a_total, v_rls_a_owned
  from erp.manual_reminders;
  execute 'reset role';

  perform set_config(
    'request.jwt.claims',
    jsonb_build_object('sub', v_auth_b, 'role', 'authenticated')::text,
    true
  );
  execute 'set local role authenticated';
  select count(*), count(*) filter (where owner_user_id = v_owner_b)
  into v_rls_b_total, v_rls_b_owned
  from erp.manual_reminders;
  execute 'reset role';
  execute 'revoke select on erp.manual_reminders from authenticated';

  if v_rls_a_total is distinct from 1 or v_rls_a_owned is distinct from 1
     or v_rls_b_total is distinct from 1 or v_rls_b_owned is distinct from 1 then
    raise exception 'Runtime own-user RLS failed: A total/own=%/%, B total/own=%/%',
      v_rls_a_total, v_rls_a_owned, v_rls_b_total, v_rls_b_owned;
  end if;
  v_runtime_rls_passed := true;

  if exists (
    select 1
    from information_schema.table_privileges g
    where g.table_schema = 'erp'
      and g.table_name = 'manual_reminders'
      and g.grantee in ('PUBLIC','anon','authenticated')
  ) then
    raise exception 'Private reminder table received a direct browser grant';
  end if;

  if not coalesce((
    select c.relrowsecurity
    from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'erp' and c.relname = 'manual_reminders'
  ), false) then
    raise exception 'manual_reminders does not have RLS enabled';
  end if;

  if (select count(*) from pg_policies p
      where p.schemaname = 'erp' and p.tablename = 'manual_reminders') is distinct from 1
     or (
    select count(*)
    from pg_policies p
    where p.schemaname = 'erp'
      and p.tablename = 'manual_reminders'
      and p.policyname = 'own_internal_read'
      and p.cmd = 'SELECT'
      and 'authenticated' = any(p.roles)
      and p.qual like '%owner_user_id%current_app_user_id%'
  ) is distinct from 1 then
    raise exception 'Own-user reminder RLS policy is not the single expected read policy';
  end if;

  if (
    select count(*)
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname in (
        'erp_list_my_reminders_v1','erp_save_my_reminder_v1',
        'erp_set_my_reminder_done_v1','erp_cancel_my_reminder_v1'
      )
  ) is distinct from 4 then
    raise exception 'Expected exactly four public reminder facades';
  end if;

  if exists (
    select 1
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname in (
        'erp_list_my_reminders_v1','erp_save_my_reminder_v1',
        'erp_set_my_reminder_done_v1','erp_cancel_my_reminder_v1'
      )
      and (
        has_function_privilege('anon', p.oid, 'EXECUTE')
        or not has_function_privilege('authenticated', p.oid, 'EXECUTE')
        or not p.prosecdef
        or not (
          'search_path=erp, public, auth, pg_temp'
          = any(coalesce(p.proconfig, array[]::text[]))
        )
      )
  ) then
    raise exception 'Public reminder facade ACL or fixed search_path is unsafe';
  end if;

  if exists (
    select 1
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'erp'
      and p.proname in (
        'require_manual_reminder_actor','list_my_reminders_v1','save_my_reminder_v1',
        'set_my_reminder_done_v1','cancel_my_reminder_v1',
        'guard_manual_reminder_write','audit_manual_reminder_change'
      )
      and (
        has_function_privilege('anon', p.oid, 'EXECUTE')
        or has_function_privilege('authenticated', p.oid, 'EXECUTE')
        or not (
          case
            when p.proname = 'guard_manual_reminder_write'
              then 'search_path=erp, public, pg_temp'
            when p.proname in (
              'audit_manual_reminder_change','require_manual_reminder_actor',
              'list_my_reminders_v1'
            ) then 'search_path=erp, public, auth, pg_temp'
            else 'search_path=erp, public, auth, extensions, pg_temp'
          end = any(coalesce(p.proconfig, array[]::text[]))
        )
      )
  ) then
    raise exception 'Internal reminder helper ACL or fixed search_path is unsafe';
  end if;

  if exists (
    select 1
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'erp'
      and p.proname in (
        'require_manual_reminder_actor','list_my_reminders_v1','save_my_reminder_v1',
        'set_my_reminder_done_v1','cancel_my_reminder_v1','audit_manual_reminder_change'
      )
      and not p.prosecdef
  ) then
    raise exception 'A privileged reminder implementation is not SECURITY DEFINER';
  end if;

  select count(*) into v_index_count
  from pg_indexes i
  where i.schemaname = 'erp'
    and i.tablename = 'manual_reminders'
    and i.indexname <> 'manual_reminders_pkey';
  if v_index_count is distinct from 1 then
    raise exception 'Reminder table should have exactly one non-PK query-path index, got %', v_index_count;
  end if;

  select row_version into v_version
  from erp.manual_reminders where id = v_reminder_id;

  return jsonb_build_object(
    'create_replay_exact', v_create_replay is not distinct from v_created,
    'wib_due_at_utc', '2026-08-31T02:00:00Z',
    'final_status', v_cancelled->>'status',
    'final_row_version', v_version,
    'owner_isolation', v_cross_owner_blocked,
    'authenticated_facades', v_authenticated_facades_passed,
    'runtime_rls', v_runtime_rls_passed,
    'customer_blocked', v_customer_blocked,
    'inactive_blocked', v_inactive_blocked,
    'anon_blocked', v_anon_blocked,
    'hard_delete_blocked', v_hard_delete_blocked,
    'direct_insert_blocked', v_direct_insert_blocked,
    'direct_update_blocked', v_direct_update_blocked,
    'audit_rows', v_audit_count,
    'audit_content_redacted', true,
    'audit_actor_attributed', true,
    'owner_a_idempotency_rows', v_idempotency_count,
    'idempotency_rows_completed', true,
    'non_pk_indexes', v_index_count,
    'post_rollback_residue_check_required', true
  );
end;
$test$;

select pg_temp.run_manual_reminders_test() as result;

rollback;

do $residue$
declare
  v_residue_count bigint;
begin
  select
    (select count(*) from erp.app_users
      where id in (
        '7d3e0a61-0001-4f10-8000-000000000001'::uuid,
        '7d3e0a61-0002-4f10-8000-000000000002'::uuid,
        '7d3e0a61-0003-4f10-8000-000000000003'::uuid,
        '7d3e0a61-0004-4f10-8000-000000000004'::uuid
      ))
    + (select count(*) from erp.manual_reminders
      where owner_user_id in (
        '7d3e0a61-0001-4f10-8000-000000000001'::uuid,
        '7d3e0a61-0002-4f10-8000-000000000002'::uuid
      ))
    + (select count(*) from erp.audit_logs
      where entity_type = 'manual_reminders'
        and changed_by in (
          '7d3e0a61-0001-4f10-8000-000000000001'::uuid,
          '7d3e0a61-0002-4f10-8000-000000000002'::uuid
        ))
    + (select count(*) from erp.idempotency_requests
      where actor_key in (
        '7d3e0a61-0001-4f10-8000-000000000001',
        '7d3e0a61-0002-4f10-8000-000000000002'
      ))
  into v_residue_count;

  if v_residue_count is distinct from 0 then
    raise exception 'Rollback left % synthetic reminder-related rows', v_residue_count;
  end if;
end;
$residue$;

select jsonb_build_object(
  'synthetic_data_persisted', false,
  'post_rollback_residue_rows', 0
) as post_rollback_result;
