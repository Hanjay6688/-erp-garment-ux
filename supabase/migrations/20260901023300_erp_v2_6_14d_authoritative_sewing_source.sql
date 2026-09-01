-- ERP Garment v2.6.14d — CP3 SOURCE CANDIDATE HARDENING
-- Bind every SELESAI_DIJAHIT event to a terminal authoritative
-- work_completion/work_completion_line snapshot. Operator-supplied PO, Mandor,
-- quantity, and date/time are removed from the write contract.

begin;
set local lock_timeout = '10s';
set local statement_timeout = '120s';

do $guard$
begin
  if to_regclass('erp.attendance_hpp_sewing_events') is null
     or to_regclass('erp.contractor_hpp_policy_versions') is null
     or to_regclass('erp.work_completions') is null
     or to_regclass('erp.work_completion_lines') is null
     or to_regclass('erp.work_components') is null then
    raise exception 'v2.6.14d requires v2.6.14a-c and the verified work-completion baseline';
  end if;
end;
$guard$;

create or replace function erp.cp3_sewing_source_snapshot_v2(
  p_source_work_completion_line_id uuid
)
returns jsonb
language plpgsql
stable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_line jsonb;
  v_header jsonb;
  v_component jsonb;
  v_completion_id uuid;
  v_component_id uuid;
  v_po_id uuid;
  v_contractor_id uuid;
  v_status text;
  v_component_label text;
  v_quantity numeric;
  v_effective_at timestamptz;
  v_effective_date date;
  v_payload jsonb;
  v_hash text;
begin
  if p_source_work_completion_line_id is null then
    raise exception 'source_work_completion_line_id is required';
  end if;

  select to_jsonb(w) into v_line
  from erp.work_completion_lines w
  where w.id = p_source_work_completion_line_id;
  if v_line is null then raise exception 'Work completion line not found'; end if;

  v_completion_id := nullif(coalesce(
    v_line ->> 'work_completion_id',
    v_line ->> 'completion_id',
    v_line ->> 'work_completion_header_id'
  ), '')::uuid;
  if v_completion_id is null then
    raise exception 'Work completion line has no authoritative header identity';
  end if;

  select to_jsonb(w) into v_header
  from erp.work_completions w
  where w.id = v_completion_id;
  if v_header is null then raise exception 'Work completion header not found'; end if;

  v_status := upper(coalesce(
    nullif(v_header ->> 'status',''),
    nullif(v_line ->> 'status',''),
    ''
  ));
  if v_status not in ('POSTED','COMPLETED','FINAL','CLOSED') then
    raise exception 'Work completion must be terminal; observed status %', v_status;
  end if;
  if upper(concat_ws('|',
       v_header ->> 'lifecycle_status',
       v_header ->> 'reversal_status',
       v_line ->> 'lifecycle_status',
       v_line ->> 'reversal_status'
     )) ~ '(REVERSED|CANCELLED|VOID)' then
    raise exception 'Reversed/cancelled work completion cannot source SELESAI_DIJAHIT';
  end if;

  v_component_id := nullif(coalesce(
    v_line ->> 'work_component_id',
    v_header ->> 'work_component_id'
  ), '')::uuid;
  if v_component_id is not null then
    select to_jsonb(c) into v_component
    from erp.work_components c
    where c.id = v_component_id;
  end if;

  v_component_label := upper(concat_ws('|',
    v_line ->> 'source_type',
    v_line ->> 'completion_type',
    v_line ->> 'work_type',
    v_header ->> 'source_type',
    v_header ->> 'completion_type',
    v_component ->> 'component_code',
    v_component ->> 'component_name',
    v_component ->> 'component_type',
    v_component ->> 'process_code'
  ));
  if v_component_label ~ '(QC|FG|LAUNDRY|REWORK|REWASH|SUSULAN|RETURN)' then
    raise exception 'Work completion is a downstream destination, not SELESAI_DIJAHIT';
  end if;
  if v_component_label !~ '(SEW|JAHIT)' then
    raise exception 'Work completion is not explicitly a sewing/Jahit component';
  end if;

  v_po_id := nullif(coalesce(
    v_line ->> 'po_id',
    v_line ->> 'production_order_id',
    v_header ->> 'po_id',
    v_header ->> 'production_order_id'
  ), '')::uuid;
  v_contractor_id := nullif(coalesce(
    v_line ->> 'contractor_id',
    v_line ->> 'mandor_id',
    v_header ->> 'contractor_id',
    v_header ->> 'mandor_id'
  ), '')::uuid;
  if v_po_id is null or v_contractor_id is null then
    raise exception 'Terminal sewing completion must identify production order and Mandor';
  end if;
  if not exists (select 1 from erp.production_orders p where p.id = v_po_id) then
    raise exception 'Terminal sewing completion references a missing production order';
  end if;
  if not exists (
    select 1 from erp.contractors c
    where c.id = v_contractor_id and c.contractor_type = 'MANDOR'
  ) then
    raise exception 'Terminal sewing completion references a non-Mandor contractor';
  end if;

  v_quantity := coalesce(
    nullif(v_line ->> 'qty_completed','')::numeric,
    nullif(v_line ->> 'completed_qty','')::numeric,
    nullif(v_line ->> 'quantity','')::numeric,
    nullif(v_line ->> 'qty','')::numeric
  );
  if v_quantity is null or v_quantity <= 0 then
    raise exception 'Terminal sewing completion must carry positive authoritative quantity';
  end if;

  v_effective_at := coalesce(
    nullif(v_line ->> 'physical_at','')::timestamptz,
    nullif(v_line ->> 'completed_at','')::timestamptz,
    nullif(v_line ->> 'posted_at','')::timestamptz,
    nullif(v_header ->> 'physical_at','')::timestamptz,
    nullif(v_header ->> 'completed_at','')::timestamptz,
    nullif(v_header ->> 'posted_at','')::timestamptz
  );
  if v_effective_at is null or not isfinite(v_effective_at) then
    raise exception 'Terminal sewing completion must carry finite physical/completed/posted time';
  end if;

  v_effective_date := coalesce(
    nullif(v_line ->> 'physical_date','')::date,
    nullif(v_line ->> 'completion_date','')::date,
    nullif(v_header ->> 'physical_date','')::date,
    nullif(v_header ->> 'completion_date','')::date,
    (v_effective_at at time zone 'Asia/Jakarta')::date
  );

  v_payload := jsonb_build_object(
    'source_work_completion_line_id', p_source_work_completion_line_id,
    'work_completion_id', v_completion_id,
    'work_component_id', v_component_id,
    'production_order_id', v_po_id,
    'contractor_id', v_contractor_id,
    'terminal_status', v_status,
    'event_type', 'SELESAI_DIJAHIT',
    'business_source_kind', 'SEWING_TERMINAL',
    'quantity', v_quantity,
    'effective_date', v_effective_date,
    'effective_at_epoch_us', floor(extract(epoch from v_effective_at) * 1000000)::bigint
  );
  v_hash := erp._request_hash(v_payload);
  return v_payload || jsonb_build_object('source_payload_hash', v_hash);
end;
$function$;

-- Compatibility validator now delegates to the authoritative snapshot and
-- compares, rather than inventing, supplied identity/quantity.
create or replace function erp.cp3_validate_sewing_source_v1(
  p_source_work_completion_line_id uuid,
  p_production_order_id uuid,
  p_contractor_id uuid,
  p_quantity numeric
)
returns jsonb
language plpgsql
stable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_snapshot jsonb;
begin
  v_snapshot := erp.cp3_sewing_source_snapshot_v2(p_source_work_completion_line_id);
  if (v_snapshot ->> 'production_order_id')::uuid is distinct from p_production_order_id then
    raise exception 'Work completion source belongs to a different production order';
  end if;
  if (v_snapshot ->> 'contractor_id')::uuid is distinct from p_contractor_id then
    raise exception 'Work completion source belongs to a different contractor';
  end if;
  if (v_snapshot ->> 'quantity')::numeric is distinct from p_quantity then
    raise exception 'SELESAI_DIJAHIT quantity must equal authoritative completion-line quantity';
  end if;
  return v_snapshot;
end;
$function$;

-- The owning record RPC accepts only source identity, reviewed source hash,
-- event discriminator, and reason. PO/Mandor/qty/date/time are derived.
create or replace function erp.record_sewing_terminal_event_v1(
  p_payload jsonb,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'record_sewing_terminal_event_v1';
  v_hash text;
  v_cached jsonb;
  v_source_line_id uuid;
  v_expected_source_hash text;
  v_reason text;
  v_snapshot jsonb;
  v_policy erp.contractor_hpp_policy_versions%rowtype;
  v_event erp.attendance_hpp_sewing_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_internal();
  perform erp.cp3_assert_json_object_v1(
    p_payload,
    array[
      'event_type','business_source_kind','source_work_completion_line_id',
      'expected_source_payload_hash','reason'
    ],
    array[
      'event_type','business_source_kind','source_work_completion_line_id',
      'expected_source_payload_hash','reason'
    ],
    jsonb_build_object(
      'event_type','string','business_source_kind','string',
      'source_work_completion_line_id','string',
      'expected_source_payload_hash','string','reason','string'
    )
  );

  if upper(p_payload ->> 'event_type') <> 'SELESAI_DIJAHIT'
     or upper(p_payload ->> 'business_source_kind') <> 'SEWING_TERMINAL' then
    raise exception 'Only explicit SELESAI_DIJAHIT / SEWING_TERMINAL events are accepted';
  end if;

  v_source_line_id := (p_payload ->> 'source_work_completion_line_id')::uuid;
  v_expected_source_hash := p_payload ->> 'expected_source_payload_hash';
  v_reason := nullif(btrim(p_payload ->> 'reason'), '');
  if v_reason is null then raise exception 'Sewing-terminal reason is required'; end if;

  v_snapshot := erp.cp3_sewing_source_snapshot_v2(v_source_line_id);
  if v_snapshot ->> 'source_payload_hash' is distinct from v_expected_source_hash then
    raise exception 'STALE_SEWING_SOURCE expected %, current %',
      v_expected_source_hash, v_snapshot ->> 'source_payload_hash';
  end if;
  v_policy := erp.require_eligible_contractor_hpp_policy_v1(
    (v_snapshot ->> 'contractor_id')::uuid,
    (v_snapshot ->> 'effective_date')::date
  );

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'authoritative_source', v_snapshot,
    'contract_version', 'SELESAI_DIJAHIT_V2'
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform pg_advisory_xact_lock(hashtextextended('SEWING_TERMINAL|' || v_source_line_id::text, 0));
  v_snapshot := erp.cp3_sewing_source_snapshot_v2(v_source_line_id);
  if v_snapshot ->> 'source_payload_hash' is distinct from v_expected_source_hash then
    raise exception 'STALE_SEWING_SOURCE changed while waiting for lock';
  end if;
  if exists (
    select 1
    from erp.v_attendance_hpp_active_sewing_events_v1 e
    where e.source_work_completion_line_id = v_source_line_id
  ) then
    raise exception 'An active SELESAI_DIJAHIT event already exists for this source line';
  end if;

  perform set_config('app.change_reason', v_reason, true);
  perform set_config('app.attendance_hpp_sewing_write', 'on', true);
  insert into erp.attendance_hpp_sewing_events(
    event_key, event_action, event_type, business_source_kind,
    production_order_id, contractor_id, source_work_completion_line_id,
    effective_date, effective_at, quantity_signed, policy_version_id,
    source_payload_hash, reason, created_by
  ) values (
    p_client_request_id, 'RECORD', 'SELESAI_DIJAHIT', 'SEWING_TERMINAL',
    (v_snapshot ->> 'production_order_id')::uuid,
    (v_snapshot ->> 'contractor_id')::uuid,
    v_source_line_id,
    (v_snapshot ->> 'effective_date')::date,
    to_timestamp((v_snapshot ->> 'effective_at_epoch_us')::numeric / 1000000.0),
    (v_snapshot ->> 'quantity')::numeric,
    v_policy.id,
    v_snapshot ->> 'source_payload_hash',
    v_reason,
    erp.current_app_user_id()
  ) returning * into v_event;

  v_response := jsonb_build_object(
    'event_id', v_event.id,
    'event_action', v_event.event_action,
    'event_type', v_event.event_type,
    'source_work_completion_line_id', v_event.source_work_completion_line_id,
    'production_order_id', v_event.production_order_id,
    'contractor_id', v_event.contractor_id,
    'effective_date', v_event.effective_date,
    'effective_at_epoch_us', floor(extract(epoch from v_event.effective_at) * 1000000)::bigint,
    'quantity', v_event.quantity_signed,
    'policy_version_id', v_event.policy_version_id,
    'source_payload_hash', v_event.source_payload_hash,
    'is_active', true
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

-- The old correction contract accepted operator-supplied qty/date/time and is
-- now deliberately disabled before any UAT apply.
create or replace function erp.correct_sewing_terminal_event_v1(
  p_event_id uuid,
  p_new_effective_date date,
  p_new_effective_at timestamptz,
  p_new_quantity numeric,
  p_reason text,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
begin
  perform erp.require_internal();
  raise exception 'correct_sewing_terminal_event_v1 is disabled; use v2 with a replacement terminal work-completion line';
end;
$function$;

create or replace function erp.correct_sewing_terminal_event_v2(
  p_event_id uuid,
  p_replacement_source_work_completion_line_id uuid,
  p_expected_replacement_source_hash text,
  p_reason text,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'correct_sewing_terminal_event_v2';
  v_hash text;
  v_cached jsonb;
  v_source erp.attendance_hpp_sewing_events%rowtype;
  v_snapshot jsonb;
  v_policy erp.contractor_hpp_policy_versions%rowtype;
  v_reverse_id uuid;
  v_corrected erp.attendance_hpp_sewing_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_internal();
  if p_event_id is null or p_replacement_source_work_completion_line_id is null
     or coalesce(btrim(p_expected_replacement_source_hash),'')=''
     or coalesce(btrim(p_reason),'')='' then
    raise exception 'event_id, replacement source/hash, and reason are required';
  end if;

  v_snapshot := erp.cp3_sewing_source_snapshot_v2(p_replacement_source_work_completion_line_id);
  if v_snapshot ->> 'source_payload_hash' is distinct from p_expected_replacement_source_hash then
    raise exception 'STALE_SEWING_SOURCE expected %, current %',
      p_expected_replacement_source_hash, v_snapshot ->> 'source_payload_hash';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'event_id',p_event_id,
    'replacement_source',v_snapshot,
    'reason',p_reason,
    'contract_version','SELESAI_DIJAHIT_CORRECTION_V2'
  ));
  v_cached := erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_source
  from erp.attendance_hpp_sewing_events e
  where e.id=p_event_id and e.event_action in ('RECORD','CORRECTION')
  for update;
  if v_source.id is null then raise exception 'Active sewing event source not found'; end if;
  if exists (select 1 from erp.attendance_hpp_sewing_events r where r.reversal_of_event_id=v_source.id) then
    raise exception 'Sewing event is no longer active';
  end if;
  if (v_snapshot ->> 'production_order_id')::uuid <> v_source.production_order_id
     or (v_snapshot ->> 'contractor_id')::uuid <> v_source.contractor_id then
    raise exception 'Correction replacement must retain production order and Mandor';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'SEWING_TERMINAL|' || least(v_source.source_work_completion_line_id::text,p_replacement_source_work_completion_line_id::text),0
  ));
  perform pg_advisory_xact_lock(hashtextextended(
    'SEWING_TERMINAL|' || greatest(v_source.source_work_completion_line_id::text,p_replacement_source_work_completion_line_id::text),0
  ));

  v_snapshot := erp.cp3_sewing_source_snapshot_v2(p_replacement_source_work_completion_line_id);
  if v_snapshot ->> 'source_payload_hash' is distinct from p_expected_replacement_source_hash then
    raise exception 'STALE_SEWING_SOURCE changed while waiting for lock';
  end if;
  if exists (
    select 1 from erp.v_attendance_hpp_active_sewing_events_v1 e
    where e.source_work_completion_line_id=p_replacement_source_work_completion_line_id
      and e.id<>v_source.id
  ) then
    raise exception 'Replacement work-completion line already has an active sewing event';
  end if;

  v_policy := erp.require_eligible_contractor_hpp_policy_v1(
    v_source.contractor_id,(v_snapshot ->> 'effective_date')::date
  );
  perform set_config('app.change_reason',p_reason,true);
  perform set_config('app.attendance_hpp_sewing_write','on',true);

  insert into erp.attendance_hpp_sewing_events(
    event_key,event_action,event_type,business_source_kind,
    production_order_id,contractor_id,source_work_completion_line_id,
    effective_date,effective_at,quantity_signed,policy_version_id,
    reversal_of_event_id,source_payload_hash,reason,created_by
  ) values (
    gen_random_uuid(),'REVERSAL','SELESAI_DIJAHIT','SEWING_TERMINAL',
    v_source.production_order_id,v_source.contractor_id,v_source.source_work_completion_line_id,
    v_source.effective_date,v_source.effective_at,-v_source.quantity_signed,v_source.policy_version_id,
    v_source.id,v_source.source_payload_hash,'Correction reversal: '||p_reason,erp.current_app_user_id()
  ) returning id into v_reverse_id;

  insert into erp.attendance_hpp_sewing_events(
    event_key,event_action,event_type,business_source_kind,
    production_order_id,contractor_id,source_work_completion_line_id,
    effective_date,effective_at,quantity_signed,policy_version_id,
    correction_of_event_id,source_payload_hash,reason,created_by
  ) values (
    p_client_request_id,'CORRECTION','SELESAI_DIJAHIT','SEWING_TERMINAL',
    v_source.production_order_id,v_source.contractor_id,p_replacement_source_work_completion_line_id,
    (v_snapshot ->> 'effective_date')::date,
    to_timestamp((v_snapshot ->> 'effective_at_epoch_us')::numeric / 1000000.0),
    (v_snapshot ->> 'quantity')::numeric,v_policy.id,
    v_source.id,v_snapshot ->> 'source_payload_hash',p_reason,erp.current_app_user_id()
  ) returning * into v_corrected;

  v_response:=jsonb_build_object(
    'source_event_id',v_source.id,
    'reversal_event_id',v_reverse_id,
    'corrected_event_id',v_corrected.id,
    'replacement_source_work_completion_line_id',v_corrected.source_work_completion_line_id,
    'effective_date',v_corrected.effective_date,
    'effective_at_epoch_us',floor(extract(epoch from v_corrected.effective_at)*1000000)::bigint,
    'quantity',v_corrected.quantity_signed,
    'source_payload_hash',v_corrected.source_payload_hash,
    'policy_version_id',v_corrected.policy_version_id,
    'is_active',true
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

-- Rebuild the trigger guard so CORRECTION may use a replacement source line,
-- while exact REVERSAL still negates the original event.
create or replace function erp.guard_attendance_hpp_sewing_event_v1()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
declare
  v_source erp.attendance_hpp_sewing_events%rowtype;
  v_policy erp.contractor_hpp_policy_versions%rowtype;
begin
  if current_setting('app.attendance_hpp_sewing_write',true) is distinct from 'on' then
    raise exception 'Sewing-terminal events are append-only; use authoritative record/correct/reverse RPCs';
  end if;
  if tg_op<>'INSERT' then raise exception 'Sewing-terminal facts cannot be updated or deleted'; end if;
  if new.event_type<>'SELESAI_DIJAHIT' or new.business_source_kind<>'SEWING_TERMINAL'
     or not isfinite(new.effective_at) then
    raise exception 'Only finite explicit SELESAI_DIJAHIT / SEWING_TERMINAL facts are accepted';
  end if;

  select * into v_policy from erp.contractor_hpp_policy_versions where id=new.policy_version_id;
  if v_policy.id is null or v_policy.contractor_id<>new.contractor_id
     or new.effective_date<v_policy.effective_from
     or (v_policy.effective_to is not null and new.effective_date>v_policy.effective_to)
     or v_policy.contractor_role<>'MANDOR' or not v_policy.attendance_required or v_policy.is_special then
    raise exception 'Sewing event policy does not prove explicit normal-Mandor eligibility on effective_date';
  end if;

  if new.event_action in ('RECORD','CORRECTION') then
    perform erp.cp3_validate_sewing_source_v1(
      new.source_work_completion_line_id,new.production_order_id,new.contractor_id,new.quantity_signed
    );
  end if;

  if new.event_action='REVERSAL' then
    select * into v_source from erp.attendance_hpp_sewing_events where id=new.reversal_of_event_id;
    if v_source.id is null or v_source.event_action not in ('RECORD','CORRECTION')
       or new.production_order_id<>v_source.production_order_id
       or new.contractor_id<>v_source.contractor_id
       or new.source_work_completion_line_id<>v_source.source_work_completion_line_id
       or new.effective_date<>v_source.effective_date or new.effective_at<>v_source.effective_at
       or new.policy_version_id<>v_source.policy_version_id
       or new.quantity_signed<>-v_source.quantity_signed
       or new.source_payload_hash<>v_source.source_payload_hash then
      raise exception 'Reversal must exactly negate one authoritative sewing event';
    end if;
  elsif new.event_action='CORRECTION' then
    select * into v_source from erp.attendance_hpp_sewing_events where id=new.correction_of_event_id;
    if v_source.id is null or v_source.event_action not in ('RECORD','CORRECTION')
       or new.production_order_id<>v_source.production_order_id
       or new.contractor_id<>v_source.contractor_id then
      raise exception 'Correction must retain source production-order and Mandor lineage';
    end if;
  end if;
  return new;
end;
$function$;

revoke execute on function erp.cp3_sewing_source_snapshot_v2(uuid) from public,anon,authenticated;
revoke execute on function erp.correct_sewing_terminal_event_v2(uuid,uuid,text,text,uuid) from public,anon,authenticated;
revoke execute on function erp.correct_sewing_terminal_event_v1(uuid,date,timestamptz,numeric,text,uuid) from service_role;
grant execute on function erp.cp3_sewing_source_snapshot_v2(uuid) to service_role;
grant execute on function erp.correct_sewing_terminal_event_v2(uuid,uuid,text,text,uuid) to service_role;

comment on function erp.cp3_sewing_source_snapshot_v2(uuid) is
  'Fail-closed immutable snapshot of a terminal sewing work completion. It derives PO, Mandor, qty, physical date/time, and source hash; no QC/FG/downstream inference.';
comment on function erp.record_sewing_terminal_event_v1(jsonb,uuid) is
  'Owning write contract accepts only source identity/hash and reason. All HPP denominator facts are derived from terminal work completion.';
comment on function erp.correct_sewing_terminal_event_v2(uuid,uuid,text,text,uuid) is
  'Correction requires a replacement terminal work-completion line and exact reviewed source hash; operator-supplied qty/date/time are forbidden.';

insert into erp.schema_migrations(version,description,installed_at)
values (
  'v2.6.14-cp3-authoritative-source',
  'CP3 source hardening: derive sewing HPP facts from terminal work completion, source-hash lock, disable arbitrary v1 correction, add replacement-source correction v2',
  clock_timestamp()
);

notify pgrst,'reload schema';
commit;
