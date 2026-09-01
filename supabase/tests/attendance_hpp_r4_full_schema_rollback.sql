-- CP3 R4 full ERP Enteng schema acceptance. Every synthetic business row rolls back.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local datestyle='ISO, MDY';
set local lock_timeout='8s';
set local statement_timeout='120s';

\ir cp3_r4_full_schema_seed.sql

-- APPROVED is the cost-recognition gate; payment has not happened yet.
do $test$
declare
  r record;
  v_count bigint;
  v_debit numeric;
begin
  for r in
    select * from (values
      ('a6000000-0000-0000-0000-000000000001'::uuid,100::numeric),
      ('a6000000-0000-0000-0000-000000000002'::uuid,50::numeric),
      ('a6000000-0000-0000-0000-000000000003'::uuid,999::numeric)
    ) x(payroll_id,expected_attendance)
  loop
    if (select status from erp.payroll_settlements where id=r.payroll_id) is distinct from 'APPROVED' then
      raise exception 'Payroll % was not left APPROVED after cost recognition',r.payroll_id;
    end if;
    select count(distinct je.id),coalesce(sum(jl.debit),0)
      into v_count,v_debit
    from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.source_type='PAYROLL_ATTENDANCE_ACCRUAL' and je.source_id=r.payroll_id and je.status='POSTED'
      and jl.account_id=erp.account_id('WIP') and jl.debit>0;
    if v_count<>1 or round(v_debit,2) is distinct from r.expected_attendance then
      raise exception 'Approval attendance WIP accrual mismatch payroll %, count %, debit %',r.payroll_id,v_count,v_debit;
    end if;
    if exists(select 1 from erp.journal_entries where source_id=r.payroll_id and source_type='PAYROLL_PAYMENT') then
      raise exception 'Approval unexpectedly settled payroll %',r.payroll_id;
    end if;
  end loop;
end
$test$;

-- Fixed Asia/Jakarta business date and canonical date text must ignore session timezone/DateStyle.
do $test$
declare
  h_utc text;
  h_jakarta text;
  h_new_york text;
  m jsonb;
  s jsonb;
begin
  set local timezone='UTC'; set local datestyle='ISO, MDY';
  m:=erp._build_attendance_hpp_manifest_v1(date '2026-01-01',date '2026-01-01');
  perform erp._assert_attendance_hpp_manifest_v1(m);
  h_utc:=erp._cp3_manifest_sha256(m);
  if m->>'period_start' is distinct from '2026-01-01'
     or (m->>'numerator_cents')::bigint<>15000
     or (m->>'denominator_qty')::bigint<>100 then
    raise exception 'Canonical manifest basis mismatch: %',m;
  end if;

  set local timezone='Asia/Jakarta'; set local datestyle='SQL, DMY';
  h_jakarta:=erp._cp3_manifest_sha256(erp._build_attendance_hpp_manifest_v1(date '2026-01-01',date '2026-01-01'));
  set local timezone='America/New_York'; set local datestyle='German, DMY';
  h_new_york:=erp._cp3_manifest_sha256(erp._build_attendance_hpp_manifest_v1(date '2026-01-01',date '2026-01-01'));
  if h_utc is distinct from h_jakarta or h_utc is distinct from h_new_york then
    raise exception 'Manifest digest changed across timezone/DateStyle: UTC %, Jakarta %, NewYork %',h_utc,h_jakarta,h_new_york;
  end if;
  if erp._cp3_business_date('2025-12-31 17:30:00+00'::timestamptz) is distinct from date '2026-01-01' then
    raise exception 'Jakarta midnight boundary was classified into the wrong business date';
  end if;

  begin
    perform erp.set_contractor_hpp_policy_v1(
      jsonb_build_object('contractor_id','a1000000-0000-0000-0000-000000000001',
                         'effective_from','01/02/2026','is_special',false,
                         'attendance_required',true,'reason','must reject ambiguous date'),
      gen_random_uuid(),(select id from erp.contractor_hpp_policy_versions
                         where contractor_id='a1000000-0000-0000-0000-000000000001'
                         order by effective_from desc limit 1));
    raise exception 'Expected ambiguous contractor policy date rejection';
  exception when others then
    if sqlerrm not like '%canonical YYYY-MM-DD%' then raise; end if;
  end;

  begin
    perform erp.create_attendance_hpp_pool_v1(
      jsonb_build_object('period_start','01/01/2026','period_end','01/01/2026','reason','must reject ambiguous pool date'),
      gen_random_uuid());
    raise exception 'Expected ambiguous pool date rejection';
  exception when others then
    if sqlerrm not like '%canonical YYYY-MM-DD%' then raise; end if;
  end;

  begin
    perform erp.create_attendance_hpp_pool_v1(
      jsonb_build_object('period_start','2026-02-30','period_end','2026-02-30','reason','must reject impossible pool date'),
      gen_random_uuid());
    raise exception 'Expected impossible pool date rejection';
  exception when others then
    if sqlerrm not like '%real canonical calendar date%' then raise; end if;
  end;

  s:=erp.attendance_hpp_exclusion_summary_v1(date '2026-01-01',date '2026-01-01');
  if jsonb_array_length(s->'excluded_payrolls')<>1
     or jsonb_array_length(s->'excluded_sewing_events')<>2 then
    raise exception 'Special/exempt exclusion summary mismatch: %',s;
  end if;
end
$test$;

-- Exact restored-schema nested JSON matrix: fail closed on missing/null/extra/type/string/empty cases.
create or replace function pg_temp.cp3_r4_expect_manifest_reject(
  p_label text,
  p_manifest jsonb,
  p_expected_fragment text
)
returns void
language plpgsql
as $function$
begin
  begin
    perform erp._assert_attendance_hpp_manifest_v1(p_manifest);
    raise exception 'CP3_R4_EXPECTED_REJECTION_NOT_RAISED: %',p_label;
  exception when others then
    if sqlerrm like 'CP3_R4_EXPECTED_REJECTION_NOT_RAISED:%'
       or position(lower(p_expected_fragment) in lower(sqlerrm))=0 then
      raise exception 'CP3 R4 JSON case % returned wrong error: %',p_label,sqlerrm;
    end if;
  end;
end
$function$;

do $test$
declare
  m jsonb;
  source_item jsonb;
  destination_item jsonb;
begin
  m:=erp._build_attendance_hpp_manifest_v1(date '2026-01-01',date '2026-01-01');
  perform erp._assert_attendance_hpp_manifest_v1(m);

  if jsonb_typeof(m#>'{sources,0,attendance_required_snapshot}') is distinct from 'boolean'
     or m#>'{sources,0,attendance_required_snapshot}' is distinct from 'true'::jsonb
     or jsonb_typeof(m#>'{sources,0,is_special_snapshot}') is distinct from 'boolean'
     or m#>'{sources,0,is_special_snapshot}' is distinct from 'false'::jsonb
     or jsonb_typeof(m#>'{destinations,0,attendance_required_snapshot}') is distinct from 'boolean'
     or m#>'{destinations,0,attendance_required_snapshot}' is distinct from 'true'::jsonb
     or jsonb_typeof(m#>'{destinations,0,is_special_snapshot}') is distinct from 'boolean'
     or m#>'{destinations,0,is_special_snapshot}' is distinct from 'false'::jsonb then
    raise exception 'CP3 R4 base manifest did not preserve real JSON boolean true/false values';
  end if;

  source_item:=m#>'{sources,0}';
  destination_item:=m#>'{destinations,0}';

  perform pg_temp.cp3_r4_expect_manifest_reject('source required key missing',
    jsonb_set(m,'{sources,0}',source_item-'payroll_id'),'requires non-null key payroll_id');
  perform pg_temp.cp3_r4_expect_manifest_reject('source required key null',
    jsonb_set(m,'{sources,0,payroll_id}','null'::jsonb),'requires non-null key payroll_id');
  perform pg_temp.cp3_r4_expect_manifest_reject('source extra key',
    jsonb_set(m,'{sources,0}',source_item||jsonb_build_object('unexpected_key',1)),'contains unexpected key unexpected_key');
  perform pg_temp.cp3_r4_expect_manifest_reject('source wrong type',
    jsonb_set(m,'{sources,0,attendance_amount_cents}','"100"'::jsonb),'invalid nested field types');
  perform pg_temp.cp3_r4_expect_manifest_reject('source string true',
    jsonb_set(m,'{sources,0,attendance_required_snapshot}','"true"'::jsonb),'invalid nested field types');
  perform pg_temp.cp3_r4_expect_manifest_reject('source string false',
    jsonb_set(m,'{sources,0,is_special_snapshot}','"false"'::jsonb),'invalid nested field types');
  perform pg_temp.cp3_r4_expect_manifest_reject('source real boolean wrong eligibility',
    jsonb_set(m,'{sources,0,is_special_snapshot}','true'::jsonb),'not an eligible normal Mandor');
  perform pg_temp.cp3_r4_expect_manifest_reject('source empty object',
    jsonb_set(m,'{sources,0}','{}'::jsonb),'requires non-null key payroll_id');
  perform pg_temp.cp3_r4_expect_manifest_reject('source nested missing nullable key',
    jsonb_set(m,'{sources,0}',source_item-'policy_effective_to'),'requires key policy_effective_to');

  perform pg_temp.cp3_r4_expect_manifest_reject('destination required key missing',
    jsonb_set(m,'{destinations,0}',destination_item-'sewing_terminal_event_id'),'requires non-null key sewing_terminal_event_id');
  perform pg_temp.cp3_r4_expect_manifest_reject('destination required key null',
    jsonb_set(m,'{destinations,0,sewing_terminal_event_id}','null'::jsonb),'requires non-null key sewing_terminal_event_id');
  perform pg_temp.cp3_r4_expect_manifest_reject('destination extra key',
    jsonb_set(m,'{destinations,0}',destination_item||jsonb_build_object('unexpected_key',1)),'contains unexpected key unexpected_key');
  perform pg_temp.cp3_r4_expect_manifest_reject('destination wrong type',
    jsonb_set(m,'{destinations,0,sewing_qty}','"60"'::jsonb),'invalid nested field types');
  perform pg_temp.cp3_r4_expect_manifest_reject('destination string true',
    jsonb_set(m,'{destinations,0,attendance_required_snapshot}','"true"'::jsonb),'invalid nested field types');
  perform pg_temp.cp3_r4_expect_manifest_reject('destination string false',
    jsonb_set(m,'{destinations,0,is_special_snapshot}','"false"'::jsonb),'invalid nested field types');
  perform pg_temp.cp3_r4_expect_manifest_reject('destination real boolean wrong eligibility',
    jsonb_set(m,'{destinations,0,attendance_required_snapshot}','false'::jsonb),'not an eligible normal Mandor');
  perform pg_temp.cp3_r4_expect_manifest_reject('destination empty object',
    jsonb_set(m,'{destinations,0}','{}'::jsonb),'requires non-null key sewing_terminal_event_id');
  perform pg_temp.cp3_r4_expect_manifest_reject('destination nested missing key',
    jsonb_set(m,'{destinations,0}',destination_item-'policy_version_id'),'requires non-null key policy_version_id');
end
$test$;

-- Exact idempotency and stale-version behavior on the owning pool lifecycle.
do $test$
declare
  request_id constant uuid:='44444444-4444-4444-8444-444444444444';
  payload jsonb:=jsonb_build_object('period_start','2026-01-01','period_end','2026-01-01','reason','CP3 R4 idempotency');
  first_result jsonb;
  second_result jsonb;
  pool_id uuid;
begin
  first_result:=erp.create_attendance_hpp_pool_v1(payload,request_id);
  second_result:=erp.create_attendance_hpp_pool_v1(payload,request_id);
  if first_result is distinct from second_result then
    raise exception 'Same idempotency key/same payload did not return the cached result';
  end if;
  pool_id:=(first_result->>'pool_id')::uuid;

  begin
    perform erp.create_attendance_hpp_pool_v1(payload||jsonb_build_object('reason','CP3 R4 changed payload'),request_id);
    raise exception 'Expected same idempotency key/different payload rejection';
  exception when others then
    if sqlerrm like 'Expected same idempotency%'
       or position('client_request_id' in lower(sqlerrm)) = 0
       or position('different payload' in lower(sqlerrm)) = 0 then
      raise;
    end if;
  end;

  begin
    perform erp.cancel_attendance_hpp_pool_v1(pool_id,'CP3 R4 stale version',gen_random_uuid(),999);
    raise exception 'Expected stale pool version rejection';
  exception when others then
    if sqlerrm not like 'STALE_VERSION%' then raise; end if;
  end;
  perform erp.cancel_attendance_hpp_pool_v1(pool_id,'CP3 R4 idempotency cleanup',gen_random_uuid(),1);
end
$test$;

insert into cp3_r3_ids(key,value)
values('voidable_pool',erp.create_attendance_hpp_pool_v1(
  jsonb_build_object('period_start','2026-01-01','period_end','2026-01-01','reason','CP3 R3 voidable DRAFT'),
  gen_random_uuid()));
insert into cp3_r3_ids(key,value)
values('voided_pool',erp.cancel_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='voidable_pool'),
  'CP3 R3 void stale DRAFT',gen_random_uuid(),1));
do $test$
declare p uuid:=(select (value->>'pool_id')::uuid from cp3_r3_ids where key='voidable_pool');
begin
  if (select status from erp.attendance_hpp_pools where id=p) is distinct from 'VOIDED'
     or (select post_journal_entry_id from erp.attendance_hpp_pools where id=p) is not null
     or not exists(select 1 from erp.audit_logs where entity_type='attendance_hpp_pools' and entity_id=p
                   and action='UPDATE' and new_data->>'lifecycle_action'='VOID_DRAFT') then
    raise exception 'DRAFT pool was not voided cleanly through the owning lifecycle';
  end if;
end
$test$;

insert into cp3_r3_ids(key,value)
values('pool',erp.create_attendance_hpp_pool_v1(
  jsonb_build_object('period_start','2026-01-01','period_end','2026-01-01','reason','CP3 R3 full-schema pool'),
  gen_random_uuid()));

insert into cp3_r3_ids(key,value)
values('active',erp.activate_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool'),
  'CP3 R3 activate',gen_random_uuid(),1));

-- Exact journal lineage and target-faithful audit vocabulary.
do $test$
declare
  p uuid:=(select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool');
  j uuid;
begin
  select post_journal_entry_id into j from erp.attendance_hpp_pools where id=p;
  if (select count(*) from erp.attendance_hpp_journal_line_links where pool_id=p and link_type='SOURCE_CREDIT')<>2 then
    raise exception 'Terminal source credit is not one-per-original-debit-line';
  end if;
  if (select round(sum(debit),2) from erp.journal_lines where journal_entry_id=j)<>150
     or (select round(sum(credit),2) from erp.journal_lines where journal_entry_id=j)<>150 then
    raise exception 'Attendance HPP allocation journal does not balance to 150';
  end if;
  if exists(
    select 1 from erp.audit_logs
    where entity_type in ('attendance_hpp_pools','sewing_terminal_events','contractor_hpp_policy_versions')
      and action not in ('INSERT','UPDATE','DELETE','POST','REVERSE','RECALCULATE','WORK_BOM_COMMIT','CANCEL_UNPAID','REVERSE_PAID')
  ) then
    raise exception 'CP3 wrote an audit action outside ERP Enteng vocabulary';
  end if;
  perform erp.validate_attendance_hpp_pool_v1(p);
end
$test$;

-- Generic reversal cannot bypass protected pool/payroll ownership.
do $test$
declare
  pool_id uuid:=(select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool');
  pool_journal uuid;
  payroll_journal uuid;
begin
  select post_journal_entry_id into pool_journal from erp.attendance_hpp_pools where id=pool_id;
  select id into payroll_journal from erp.journal_entries
  where source_type='PAYROLL_ATTENDANCE_ACCRUAL'
    and source_id='a6000000-0000-0000-0000-000000000001'
    and status='POSTED';

  begin
    perform erp.reverse_journal(pool_journal,'must use owning pool cancel');
    raise exception 'Expected generic pool-journal reversal rejection';
  exception when others then
    if sqlerrm not like 'PROTECTED_JOURNAL_REQUIRES_OWNING_LIFECYCLE:%ATTENDANCE_HPP_POOL%' then raise; end if;
  end;
  begin
    perform erp.reverse_journal(payroll_journal,'must use owning payroll reversal');
    raise exception 'Expected generic payroll-accrual reversal rejection';
  exception when others then
    if sqlerrm not like 'PROTECTED_JOURNAL_REQUIRES_OWNING_LIFECYCLE:%PAYROLL_ATTENDANCE_ACCRUAL%' then raise; end if;
  end;
  if (select status from erp.journal_entries where id=pool_journal) is distinct from 'POSTED'
     or (select status from erp.journal_entries where id=payroll_journal) is distinct from 'POSTED' then
    raise exception 'Protected generic reversal changed journal state despite rejection';
  end if;
end
$test$;

-- Owning work-completion reversal cannot orphan its unreversed terminal event.
do $test$
begin
  begin
    perform erp.reverse_work_completion('a5000000-0000-0000-0000-000000000001','must reverse terminal first');
    raise exception 'Expected work completion terminal-dependency rejection';
  exception when others then
    if sqlerrm not like 'SEWING_TERMINAL_DEPENDENCY:%reverse_sewing_terminal_v1%' then raise; end if;
  end;
  if (select status from erp.work_completion_events where id='a5000000-0000-0000-0000-000000000001') is distinct from 'POSTED' then
    raise exception 'Rejected work-completion reversal changed source status';
  end if;
end
$test$;

-- Payment settles existing payable and must not recognize attendance again.
do $test$
declare
  h_before text;
  h_after text;
  v_accrual_count bigint;
begin
  h_before:=erp._cp3_manifest_sha256(erp._build_attendance_hpp_manifest_v1(date '2026-01-01',date '2026-01-01'));
  perform erp.post_payroll_payment('a6000000-0000-0000-0000-000000000001');
  if (select status from erp.payroll_settlements where id='a6000000-0000-0000-0000-000000000001') is distinct from 'PAID' then
    raise exception 'Payment did not settle APPROVED payroll';
  end if;
  select count(*) into v_accrual_count from erp.journal_entries
  where source_id='a6000000-0000-0000-0000-000000000001'
    and source_type='PAYROLL_ATTENDANCE_ACCRUAL' and status='POSTED';
  if v_accrual_count<>1
     or exists(select 1 from erp.journal_entries where source_id='a6000000-0000-0000-0000-000000000001' and source_type='PAYROLL_EXTRA_ACCRUAL') then
    raise exception 'Payment duplicated or deferred payroll cost recognition';
  end if;
  if not exists(select 1 from erp.journal_entries where source_id='a6000000-0000-0000-0000-000000000001' and source_type='PAYROLL_PAYMENT' and status='POSTED') then
    raise exception 'Settlement payment journal missing';
  end if;
  h_after:=erp._cp3_manifest_sha256(erp._build_attendance_hpp_manifest_v1(date '2026-01-01',date '2026-01-01'));
  if h_before is distinct from h_after then
    raise exception 'APPROVED to PAID settlement changed the HPP source manifest';
  end if;
end
$test$;

-- ACTIVE February pool serializes and blocks a new payroll approval for the exact period.
insert into cp3_r3_ids(key,value)
values('pool_feb',erp.create_attendance_hpp_pool_v1(
  jsonb_build_object('period_start','2026-02-01','period_end','2026-02-01','reason','CP3 R4 approval guard pool'),gen_random_uuid()));
insert into cp3_r3_ids(key,value)
values('active_feb',erp.activate_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool_feb'),'CP3 R4 activate February',gen_random_uuid(),1));
do $test$
begin
  begin
    perform erp.approve_payroll('a6000000-0000-0000-0000-000000000021');
    raise exception 'Expected ACTIVE pool payroll approval rejection';
  exception when others then
    if sqlerrm not like 'ACTIVE_ATTENDANCE_HPP_POOL_BLOCKS_PAYROLL_APPROVAL:%cancel the active attendance HPP pool first%' then raise; end if;
  end;
  if (select status from erp.payroll_settlements where id='a6000000-0000-0000-0000-000000000021')='APPROVED'
     or exists(select 1 from erp.journal_entries where source_type='PAYROLL_ATTENDANCE_ACCRUAL'
               and source_id='a6000000-0000-0000-0000-000000000021' and status='POSTED') then
    raise exception 'Rejected approval created payroll approval/accrual below ACTIVE pool';
  end if;
end
$test$;
select erp.cancel_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool_feb'),'CP3 R4 cancel February',gen_random_uuid(),2);
select erp.approve_payroll('a6000000-0000-0000-0000-000000000021');
insert into cp3_r3_ids(key,value)
values('pool_feb_rebuilt',erp.create_attendance_hpp_pool_v1(
  jsonb_build_object('period_start','2026-02-01','period_end','2026-02-01','reason','CP3 R4 rebuilt after approval'),gen_random_uuid()));
do $test$
declare p uuid:=(select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool_feb_rebuilt');
begin
  if (select count(*) from erp.attendance_hpp_pool_sources where pool_id=p)<>2 then
    raise exception 'Rebuilt February pool did not include the newly approved payroll source';
  end if;
  perform erp.validate_attendance_hpp_pool_v1(p);
end
$test$;
select erp.cancel_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool_feb_rebuilt'),'CP3 R4 void rebuilt February DRAFT',gen_random_uuid(),1);

-- ACTIVE March pool blocks overlapping policy history but permits a future non-overlap version.
insert into cp3_r3_ids(key,value)
values('pool_mar',erp.create_attendance_hpp_pool_v1(
  jsonb_build_object('period_start','2026-03-01','period_end','2026-03-01','reason','CP3 R4 policy guard pool'),gen_random_uuid()));
insert into cp3_r3_ids(key,value)
values('active_mar',erp.activate_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool_mar'),'CP3 R4 activate March',gen_random_uuid(),1));
do $test$
declare
  current_policy uuid:=(select id from erp.contractor_hpp_policy_versions
                         where contractor_id='a1000000-0000-0000-0000-000000000001'
                           and date '2026-03-01' between effective_from and coalesce(effective_to,'infinity'::date));
  request_id constant uuid:='55555555-5555-4555-8555-555555555555';
  future_payload jsonb:=jsonb_build_object(
    'contractor_id','a1000000-0000-0000-0000-000000000001','effective_from','2027-01-01',
    'is_special',false,'attendance_required',true,'reason','CP3 R4 future non-overlap');
  first_result jsonb;
  second_result jsonb;
begin
  begin
    perform erp.set_contractor_hpp_policy_v1(jsonb_build_object(
      'contractor_id','a1000000-0000-0000-0000-000000000001','effective_from','2026-03-01',
      'is_special',false,'attendance_required',true,'reason','must block overlapping active pool'),
      gen_random_uuid(),current_policy);
    raise exception 'Expected ACTIVE pool policy update rejection';
  exception when others then
    if sqlerrm not like 'ACTIVE_ATTENDANCE_HPP_POOL_BLOCKS_POLICY_CHANGE:%cancel the active pool first%' then raise; end if;
  end;

  first_result:=erp.set_contractor_hpp_policy_v1(future_payload,request_id,current_policy);
  second_result:=erp.set_contractor_hpp_policy_v1(future_payload,request_id,current_policy);
  if first_result is distinct from second_result then
    raise exception 'Future policy same idempotency key/same payload did not return cached response';
  end if;
  begin
    perform erp.set_contractor_hpp_policy_v1(future_payload||jsonb_build_object('reason','changed'),request_id,current_policy);
    raise exception 'Expected future policy same key/different payload rejection';
  exception when others then
    if sqlerrm like 'Expected future policy%'
       or position('idempot' in lower(sqlerrm))=0 then raise; end if;
  end;
end
$test$;
select erp.cancel_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool_mar'),'CP3 R4 cancel March',gen_random_uuid(),2);
insert into cp3_r3_ids(key,value)
select 'policy_a_mar',erp.set_contractor_hpp_policy_v1(jsonb_build_object(
  'contractor_id','a1000000-0000-0000-0000-000000000001','effective_from','2026-03-01',
  'is_special',false,'attendance_required',true,'reason','CP3 R4 apply after pool cancel'),
  gen_random_uuid(),id)
from erp.contractor_hpp_policy_versions
where contractor_id='a1000000-0000-0000-0000-000000000001'
  and date '2026-03-01' between effective_from and coalesce(effective_to,'infinity'::date);
insert into cp3_r3_ids(key,value)
values('pool_mar_rebuilt',erp.create_attendance_hpp_pool_v1(
  jsonb_build_object('period_start','2026-03-01','period_end','2026-03-01','reason','CP3 R4 rebuilt after policy'),gen_random_uuid()));
select erp.cancel_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool_mar_rebuilt'),'CP3 R4 void rebuilt March DRAFT',gen_random_uuid(),1);

-- ACTIVE April pool plus terminal dependency protects owning work reversal.
insert into cp3_r3_ids(key,value)
values('pool_apr',erp.create_attendance_hpp_pool_v1(
  jsonb_build_object('period_start','2026-04-01','period_end','2026-04-01','reason','CP3 R4 reverse work guard pool'),gen_random_uuid()));
insert into cp3_r3_ids(key,value)
values('active_apr',erp.activate_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool_apr'),'CP3 R4 activate April',gen_random_uuid(),1));
do $test$
begin
  begin
    perform erp.reverse_work_completion('a5000000-0000-0000-0000-000000000040','must reverse terminal first');
    raise exception 'Expected ACTIVE-period work completion dependency rejection';
  exception when others then
    if sqlerrm not like 'SEWING_TERMINAL_DEPENDENCY:%reverse_sewing_terminal_v1%' then raise; end if;
  end;
end
$test$;
select erp.cancel_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool_apr'),'CP3 R4 cancel April',gen_random_uuid(),2);
select erp.reverse_sewing_terminal_v1(
  (select id from erp.sewing_terminal_events where source_work_completion_id='a5000000-0000-0000-0000-000000000040' and event_kind='SELESAI_DIJAHIT'),
  'CP3 R4 owning terminal reversal',gen_random_uuid(),
  (select row_version from erp.sewing_terminal_events where source_work_completion_id='a5000000-0000-0000-0000-000000000040' and event_kind='SELESAI_DIJAHIT'));
select erp.reverse_work_completion('a5000000-0000-0000-0000-000000000040','CP3 R4 owning work reversal after terminal');
do $test$
begin
  if (select status from erp.work_completion_events where id='a5000000-0000-0000-0000-000000000040') is distinct from 'REVERSED' then
    raise exception 'Owning terminal-to-work reversal chain did not reverse work completion';
  end if;
end
$test$;

-- Active pool owns the source; payroll cannot be cancelled/reversed underneath it.
do $test$
begin
  begin
    perform erp.cancel_unpaid_payroll('a6000000-0000-0000-0000-000000000002','must block under active pool');
    raise exception 'Expected active-pool payroll cancellation block';
  exception when others then
    if sqlerrm not like 'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL%' then raise; end if;
  end;
  begin
    perform erp.reverse_paid_payroll('a6000000-0000-0000-0000-000000000001','must block under active pool');
    raise exception 'Expected active-pool paid reversal block';
  exception when others then
    if sqlerrm not like 'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL%' then raise; end if;
  end;
end
$test$;

select erp.cancel_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp3_r3_ids where key='pool'),
  'CP3 R3 cancel active',gen_random_uuid(),2);
select erp.reverse_paid_payroll('a6000000-0000-0000-0000-000000000001','CP3 R3 reverse paid after pool cancel');
select erp.cancel_unpaid_payroll('a6000000-0000-0000-0000-000000000002','CP3 R3 cancel B after pool cancel');
select erp.cancel_unpaid_payroll('a6000000-0000-0000-0000-000000000003','CP3 R3 cancel special');

-- Positive approved attendance with no SELESAI_DIJAHIT remains unassigned WIP and hard-blocks allocation.
insert into cp3_r3_ids(key,value)
select 'attendance_zero',erp.save_attendance_period_v1(jsonb_build_object(
  'contractor_id','a1000000-0000-0000-0000-000000000001','period_number','CP3R3-ATT-ZERO',
  'period_start','2026-01-02','period_end','2026-01-02','pay_date','2026-01-03','reason','CP3 R3 zero denominator',
  'attendance',jsonb_build_array(jsonb_build_object('worker_id',(select value->>'worker_id' from cp3_r3_ids where key='worker_a'),'attendance_date','2026-01-02','status','PRESENT'))
),gen_random_uuid(),null,false);
select erp.post_attendance_period_v1((select (value->>'period_id')::uuid from cp3_r3_ids where key='attendance_zero'),'CP3 R3 zero post',gen_random_uuid(),(select (value->>'row_version')::bigint from cp3_r3_ids where key='attendance_zero'));
insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,notes)
values('a6000000-0000-0000-0000-000000000010','CP3R3-PAY-ZERO','a1000000-0000-0000-0000-000000000001','2026-01-02','2026-01-02','DRAFT','CP3 R3 zero denominator');
select erp.populate_payroll_draft('a6000000-0000-0000-0000-000000000010');
select erp.approve_payroll('a6000000-0000-0000-0000-000000000010');
do $test$
begin
  begin
    perform erp.preview_attendance_hpp_pool_v1(date '2026-01-02',date '2026-01-02');
    raise exception 'Expected positive pool zero sewing hard block';
  exception when others then
    if sqlerrm not like 'POSITIVE_POOL_ZERO_SEWING_OUTPUT%' then raise; end if;
  end;
  if not exists(
    select 1 from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.source_type='PAYROLL_ATTENDANCE_ACCRUAL' and je.source_id='a6000000-0000-0000-0000-000000000010'
      and je.status='POSTED' and jl.account_id=erp.account_id('WIP') and jl.debit>0
  ) then
    raise exception 'Zero-denominator cost was not retained in unassigned WIP';
  end if;
end
$test$;
select erp.cancel_unpaid_payroll('a6000000-0000-0000-0000-000000000010','CP3 R3 clear zero denominator fixture');

rollback;

-- Outer rollback must leave no synthetic business residue while schema migrations remain.
do $residue$
begin
  if exists(select 1 from erp.contractors where (contractor_code like 'CP3R3-%' or contractor_code like 'CP3R4-%'))
     or exists(select 1 from erp.payroll_settlements where (payroll_number like 'CP3R3-%' or payroll_number like 'CP3R4-%'))
     or exists(select 1 from erp.production_orders where (po_number like 'CP3R3-%' or po_number like 'CP3R4-%'))
     or exists(select 1 from erp.attendance_hpp_pools)
     or exists(select 1 from erp.sewing_terminal_events)
     or exists(select 1 from erp.contractor_hpp_policy_versions) then
    raise exception 'CP3 R4 full-schema rollback left synthetic residue';
  end if;
end
$residue$;

select jsonb_build_object(
  'status','PASS',
  'schema','ERP_ENTENG_FULL_RESTORE',
  'approval_cost_recognition',true,
  'payment_settlement_only',true,
  'business_timezone','Asia/Jakarta',
  'strict_nested_json_matrix_cases',18,
  'audit_vocabulary_compatible',true,
  'active_pool_payroll_guard',true,
  'active_pool_policy_guard',true,
  'work_completion_terminal_guard',true,
  'protected_generic_reversal_guard',true,
  'stale_draft_void_lifecycle',true,
  'zero_denominator_unassigned_wip',true,
  'residue',0
) as cp3_r4_full_schema_result;
