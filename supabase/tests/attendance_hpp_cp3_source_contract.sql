-- CP3 source-contract acceptance.
-- Run only after applying v2.6.14a + v2.6.14b in a disposable/local database.
-- This is not UAT E2E, not concurrency evidence, and not production approval.

begin;
set local lock_timeout = '4s';
set local statement_timeout = '60s';
set local timezone = 'UTC';

do $test$
declare
  v_rejected boolean;
  v_utc jsonb;
  v_jakarta jsonb;
  v_digest_utc text;
  v_digest_jakarta text;
  v_definition text;
  v_count bigint;
begin
  -- Positive closed JSON contract.
  perform erp.cp3_assert_json_object_v1(
    '{"name":"normal","enabled":false,"nested":{"id":"x"}}'::jsonb,
    array['name','enabled','nested'],
    array['name','enabled','nested'],
    jsonb_build_object('name','string','enabled','boolean','nested','object')
  );
  perform erp.cp3_assert_json_object_v1(
    '{"id":"x"}'::jsonb,
    array['id'], array['id'], jsonb_build_object('id','string')
  );

  -- Required key missing.
  v_rejected := false;
  begin
    perform erp.cp3_assert_json_object_v1(
      '{"enabled":false}'::jsonb,
      array['name','enabled'], array['name','enabled'],
      jsonb_build_object('name','string','enabled','boolean')
    );
  exception when others then
    if sqlerrm like 'JSON contract missing required keys:%' then v_rejected := true; else raise; end if;
  end;
  if not v_rejected then raise exception 'CP3 ASSERTION FAILED: missing required key was accepted'; end if;

  -- Required key explicit null is not equivalent to missing and still fails its type.
  v_rejected := false;
  begin
    perform erp.cp3_assert_json_object_v1(
      '{"name":null,"enabled":false}'::jsonb,
      array['name','enabled'], array['name','enabled'],
      jsonb_build_object('name','string','enabled','boolean')
    );
  exception when others then
    if sqlerrm like 'JSON key name expected type string, observed null%' then v_rejected := true; else raise; end if;
  end;
  if not v_rejected then raise exception 'CP3 ASSERTION FAILED: explicit null was accepted as string'; end if;

  -- Wrong type.
  v_rejected := false;
  begin
    perform erp.cp3_assert_json_object_v1(
      '{"name":1,"enabled":false}'::jsonb,
      array['name','enabled'], array['name','enabled'],
      jsonb_build_object('name','string','enabled','boolean')
    );
  exception when others then
    if sqlerrm like 'JSON key name expected type string, observed number%' then v_rejected := true; else raise; end if;
  end;
  if not v_rejected then raise exception 'CP3 ASSERTION FAILED: numeric/string confusion was accepted'; end if;

  -- Extra key.
  v_rejected := false;
  begin
    perform erp.cp3_assert_json_object_v1(
      '{"name":"normal","enabled":false,"extra":1}'::jsonb,
      array['name','enabled'], array['name','enabled'],
      jsonb_build_object('name','string','enabled','boolean')
    );
  exception when others then
    if sqlerrm like 'JSON contract contains unexpected keys:%' then v_rejected := true; else raise; end if;
  end;
  if not v_rejected then raise exception 'CP3 ASSERTION FAILED: extra key was accepted'; end if;

  -- false is present; missing is not silently coerced to false.
  perform erp.cp3_assert_json_object_v1(
    '{"enabled":false}'::jsonb,
    array['enabled'], array['enabled'], jsonb_build_object('enabled','boolean')
  );
  v_rejected := false;
  begin
    perform erp.cp3_assert_json_object_v1(
      '{}'::jsonb,
      array['enabled'], array['enabled'], jsonb_build_object('enabled','boolean')
    );
  exception when others then
    if sqlerrm like 'JSON contract missing required keys:%' then v_rejected := true; else raise; end if;
  end;
  if not v_rejected then raise exception 'CP3 ASSERTION FAILED: missing boolean was treated as false'; end if;

  -- Nested required key is checked explicitly on the nested object.
  v_rejected := false;
  begin
    perform erp.cp3_assert_json_object_v1(
      '{"nested":{}}'::jsonb -> 'nested',
      array['id'], array['id'], jsonb_build_object('id','string')
    );
  exception when others then
    if sqlerrm like 'JSON contract missing required keys:%' then v_rejected := true; else raise; end if;
  end;
  if not v_rejected then raise exception 'CP3 ASSERTION FAILED: nested missing key was accepted'; end if;

  -- Typed operation isolation: valid claim settlement passes.
  perform erp.cp3_assert_typed_operation_manifest_v1(
    jsonb_build_object(
      'operation_type','LAUNDRY_CLAIM',
      'version','LAUNDRY_CLAIM_V1',
      'operations',jsonb_build_array(jsonb_build_object(
        'operation_type','LAUNDRY_CLAIM','action','LAUNDRY_CLAIM_SETTLEMENT'
      ))
    ),
    'LAUNDRY_CLAIM'
  );

  -- Transfer/carry/movement cannot be smuggled into a claim manifest.
  foreach v_definition in array array['TRANSFER','CARRY_FORWARD','MOVEMENT']
  loop
    v_rejected := false;
    begin
      perform erp.cp3_assert_typed_operation_manifest_v1(
        jsonb_build_object(
          'operation_type','LAUNDRY_CLAIM',
          'version','LAUNDRY_CLAIM_V1',
          'operations',jsonb_build_array(jsonb_build_object(
            'operation_type','LAUNDRY_CLAIM','action',v_definition
          ))
        ),
        'LAUNDRY_CLAIM'
      );
    exception when others then
      if sqlerrm like 'LAUNDRY_CLAIM manifest cannot carry action %' then v_rejected := true; else raise; end if;
    end;
    if not v_rejected then
      raise exception 'CP3 ASSERTION FAILED: LAUNDRY_CLAIM accepted foreign action %', v_definition;
    end if;
  end loop;

  -- Item-level operation discriminator mismatch also fails.
  v_rejected := false;
  begin
    perform erp.cp3_assert_typed_operation_manifest_v1(
      jsonb_build_object(
        'operation_type','LAUNDRY_CLAIM',
        'version','LAUNDRY_CLAIM_V1',
        'operations',jsonb_build_array(jsonb_build_object(
          'operation_type','ATTENDANCE_HPP_POOL','action','CANCEL'
        ))
      ),
      'LAUNDRY_CLAIM'
    );
  exception when others then
    if sqlerrm like 'Mixed operation injection rejected:%' then v_rejected := true; else raise; end if;
  end;
  if not v_rejected then raise exception 'CP3 ASSERTION FAILED: mixed operation_type was accepted'; end if;

  -- Identical logical event produces identical epoch-based JSON/hash across TimeZone.
  perform set_config('TimeZone','UTC',true);
  v_utc := jsonb_build_object(
    'event_type','SELESAI_DIJAHIT',
    'effective_at_epoch_us',floor(extract(epoch from '2026-09-01 00:00:00.123456+00'::timestamptz)*1000000)::bigint,
    'effective_date','2026-09-01'::date
  );
  v_digest_utc := encode(extensions.digest(convert_to(v_utc::text,'UTF8'),'sha256'),'hex');

  perform set_config('TimeZone','Asia/Jakarta',true);
  v_jakarta := jsonb_build_object(
    'event_type','SELESAI_DIJAHIT',
    'effective_at_epoch_us',floor(extract(epoch from '2026-09-01 00:00:00.123456+00'::timestamptz)*1000000)::bigint,
    'effective_date','2026-09-01'::date
  );
  v_digest_jakarta := encode(extensions.digest(convert_to(v_jakarta::text,'UTF8'),'sha256'),'hex');

  if v_utc is distinct from v_jakarta or v_digest_utc is distinct from v_digest_jakarta then
    raise exception 'CP3 ASSERTION FAILED: epoch JSON/hash changed with session TimeZone';
  end if;

  -- Exact candidate object shape.
  if to_regclass('erp.contractor_hpp_policy_versions') is null
     or to_regclass('erp.attendance_hpp_sewing_events') is null
     or to_regclass('erp.attendance_hpp_pools') is null
     or to_regclass('erp.attendance_hpp_terminal_credit_intents') is null then
    raise exception 'CP3 ASSERTION FAILED: expected candidate relation is missing';
  end if;

  select count(*) into v_count
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public'
    and (p.proname ilike '%attendance_hpp%' or p.proname ilike '%sewing_terminal%');
  if v_count <> 0 then
    raise exception 'CP3 ASSERTION FAILED: candidate exposed % public facade(s)',v_count;
  end if;

  select count(*) into v_count
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='erp'
    and (p.proname ilike 'cp3_%'
      or p.proname ilike '%attendance_hpp%'
      or p.proname ilike '%sewing_terminal%')
    and has_function_privilege('authenticated',p.oid,'EXECUTE');
  if v_count <> 0 then
    raise exception 'CP3 ASSERTION FAILED: authenticated can execute % private candidate routine(s)',v_count;
  end if;

  -- Denominator implementation must reference explicit active sewing events and
  -- must not use the stale QC/FG fields that caused CP3-P0-01.
  select pg_get_functiondef(p.oid) into v_definition
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='erp' and p.proname='prepare_attendance_hpp_pool_v1';
  if v_definition is null then raise exception 'CP3 ASSERTION FAILED: pool prepare function missing'; end if;
  if position('v_attendance_hpp_active_sewing_events_v1' in v_definition)=0
     or position('effective_date between v_period_start and v_period_end' in v_definition)=0 then
    raise exception 'CP3 ASSERTION FAILED: denominator is not bound to active SELESAI_DIJAHIT period facts';
  end if;
  if lower(v_definition) like '%fg_lots%'
     or lower(v_definition) like '%initial_qty_pcs%'
     or lower(v_definition) like '%qc_good%'
     or lower(v_definition) like '%good_qty%' then
    raise exception 'CP3 ASSERTION FAILED: stale QC/FG denominator token found';
  end if;
  if lower(v_definition) like '%post_journal(%' then
    raise exception 'CP3 ASSERTION FAILED: source candidate posts GL before CP3 gate';
  end if;

  -- Exactly one terminal credit intent can exist per original source line.
  select count(*) into v_count
  from pg_index i
  join pg_class c on c.oid=i.indrelid
  join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp'
    and c.relname='attendance_hpp_terminal_credit_intents'
    and i.indisunique
    and pg_get_indexdef(i.indexrelid) like '%(pool_id, source_line_id)%';
  if v_count <> 1 then
    raise exception 'CP3 ASSERTION FAILED: terminal-credit source-line uniqueness is not exact';
  end if;

  -- No deferred row validator is allowed on pool evidence.
  select count(*) into v_count
  from pg_trigger t
  join pg_class c on c.oid=t.tgrelid
  join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp'
    and c.relname like 'attendance_hpp_pool%'
    and not t.tgisinternal
    and (t.tgdeferrable or t.tginitdeferred);
  if v_count <> 0 then
    raise exception 'CP3 ASSERTION FAILED: deferred pool validator trigger still exists';
  end if;

  select pg_get_functiondef(p.oid) into v_definition
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='erp' and p.proname='cp3_validate_pool_v1';
  if v_definition is null or position('O(pool_sources + pool_destinations + allocations)' in v_definition)=0 then
    raise exception 'CP3 ASSERTION FAILED: bounded set-based validator contract is missing';
  end if;

  -- READY is explicitly intent-only.
  select pg_get_functiondef(p.oid) into v_definition
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='erp' and p.proname='finalize_attendance_hpp_pool_intent_v1';
  if v_definition is null or lower(v_definition) like '%post_journal(%' then
    raise exception 'CP3 ASSERTION FAILED: intent finalization posts the general ledger';
  end if;

  if not exists (
    select 1 from erp.schema_migrations where version='v2.6.14-cp3-foundation'
  ) then
    raise exception 'CP3 ASSERTION FAILED: candidate schema marker missing';
  end if;

  raise notice 'CP3_SOURCE_CONTRACT_PASS=true';
end;
$test$;

rollback;
