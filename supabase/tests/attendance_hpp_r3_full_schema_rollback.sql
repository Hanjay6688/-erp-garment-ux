-- CP3 R3 full ERP Enteng schema acceptance. Every synthetic business row rolls back.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local datestyle='ISO, MDY';
set local lock_timeout='8s';
set local statement_timeout='120s';

\ir cp3_r3_full_schema_seed.sql

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

-- Nested values must be real JSON booleans, never strings silently cast to boolean.
do $test$
declare
  m jsonb;
  bad jsonb;
begin
  m:=erp._build_attendance_hpp_manifest_v1(date '2026-01-01',date '2026-01-01');
  bad:=jsonb_set(m,'{sources,0,attendance_required_snapshot}','"true"'::jsonb);
  begin
    perform erp._assert_attendance_hpp_manifest_v1(bad);
    raise exception 'Expected string boolean source rejection';
  exception when others then
    if sqlerrm not like '%invalid nested field types%' then raise; end if;
  end;
  bad:=jsonb_set(m,'{destinations,0,is_special_snapshot}','"false"'::jsonb);
  begin
    perform erp._assert_attendance_hpp_manifest_v1(bad);
    raise exception 'Expected string boolean destination rejection';
  exception when others then
    if sqlerrm not like '%invalid nested field types%' then raise; end if;
  end;
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
  if exists(select 1 from erp.contractors where contractor_code like 'CP3R3-%')
     or exists(select 1 from erp.payroll_settlements where payroll_number like 'CP3R3-%')
     or exists(select 1 from erp.production_orders where po_number like 'CP3R3-%')
     or exists(select 1 from erp.attendance_hpp_pools)
     or exists(select 1 from erp.sewing_terminal_events)
     or exists(select 1 from erp.contractor_hpp_policy_versions) then
    raise exception 'CP3 R3 full-schema rollback left synthetic residue';
  end if;
end
$residue$;

select jsonb_build_object(
  'status','PASS',
  'schema','ERP_ENTENG_FULL_RESTORE',
  'approval_cost_recognition',true,
  'payment_settlement_only',true,
  'business_timezone','Asia/Jakarta',
  'strict_nested_json',true,
  'audit_vocabulary_compatible',true,
  'active_pool_payroll_guard',true,
  'stale_draft_void_lifecycle',true,
  'zero_denominator_unassigned_wip',true,
  'residue',0
) as cp3_r3_full_schema_result;
