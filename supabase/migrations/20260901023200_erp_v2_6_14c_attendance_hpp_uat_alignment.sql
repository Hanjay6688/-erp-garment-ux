-- ERP Garment v2.6.14c candidate hardening
-- CP3 R3: align attendance HPP with the exact ERP Enteng schema.
-- SOURCE-ONLY. DO NOT APPLY TO UAT, MERGE, GRANT, HOOK, OR DEPLOY BEFORE INDEPENDENT AUDIT.
--
-- Business contract:
--   * payroll APPROVED recognizes attendance cost into unassigned WIP;
--   * payroll payment is settlement-only and never recognizes attendance cost again;
--   * HPP denominator is immutable explicit SELESAI_DIJAHIT in Asia/Jakarta business dates;
--   * ACTIVE pool/source mutations share one deterministic advisory-lock protocol;
--   * UAT audit vocabulary remains unchanged; lifecycle detail is stored in JSON.

begin;
set local lock_timeout='10s';
set local statement_timeout='120s';

do $guard$
declare
  v_audit_constraint text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.14a')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.14b') then
    raise exception 'ERP v2.6.14c requires source candidates v2.6.14a and v2.6.14b first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.14c') then
    raise exception 'ERP v2.6.14c is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regprocedure('erp.approve_payroll(uuid)') is null
     or to_regprocedure('erp.post_payroll_payment(uuid)') is null
     or to_regprocedure('erp.cancel_unpaid_payroll(uuid,text)') is null
     or to_regprocedure('erp.reverse_paid_payroll(uuid,text)') is null
     or to_regclass('erp.audit_logs') is null then
    raise exception 'ERP v2.6.14c target guard: exact ERP Enteng payroll/audit contract is missing';
  end if;
  select pg_get_constraintdef(c.oid,true) into v_audit_constraint
  from pg_constraint c join pg_class t on t.oid=c.conrelid join pg_namespace n on n.oid=t.relnamespace
  where n.nspname='erp' and t.relname='audit_logs' and c.conname='audit_logs_action_check';
  if v_audit_constraint is null
     or v_audit_constraint not like '%INSERT%'
     or v_audit_constraint not like '%POST%'
     or v_audit_constraint not like '%REVERSE%'
     or v_audit_constraint like '%CREATE_DRAFT%'
     or v_audit_constraint like '%ACTIVATE%'
     or v_audit_constraint like '%CANCEL_ACTIVE%' then
    raise exception 'ERP v2.6.14c target guard: audit action vocabulary differs from reviewed ERP Enteng constraint';
  end if;
  if exists(select 1 from erp.payroll_settlements where status in ('APPROVED','PAID') and attendance_total>0) then
    raise exception 'ERP v2.6.14c cutover requires zero pre-existing APPROVED/PAID attendance payrolls; reconcile them explicitly before apply';
  end if;
end
$guard$;

-- ---------------------------------------------------------------------------
-- CP3 R3 deterministic business calendar and shared source/pool lock protocol
-- ---------------------------------------------------------------------------

create or replace function erp._cp3_business_date(p_value timestamptz)
returns date
language sql
immutable
security invoker
set search_path = erp, public, pg_temp
as $function$
  select case when p_value is null then null else (p_value at time zone 'Asia/Jakarta')::date end
$function$;

create or replace function erp._cp3_canonical_date(p_value date)
returns text
language sql
immutable
security invoker
set search_path = erp, public, pg_temp
as $function$
  select case when p_value is null then null else to_char(p_value, 'YYYY-MM-DD') end
$function$;

create or replace function erp._cp3_parse_canonical_date(p_value text, p_label text)
returns date
language plpgsql
immutable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_date date;
begin
  if p_value is null or p_value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then
    raise exception '% must be a canonical YYYY-MM-DD string', coalesce(p_label,'date');
  end if;
  v_date := p_value::date;
  if to_char(v_date,'YYYY-MM-DD') is distinct from p_value then
    raise exception '% is not a real canonical calendar date', coalesce(p_label,'date');
  end if;
  return v_date;
exception when datetime_field_overflow or invalid_datetime_format then
  raise exception '% is not a real canonical calendar date', coalesce(p_label,'date');
end;
$function$;

create or replace function erp._cp3_lock_business_date(p_business_date date)
returns void
language plpgsql
security invoker
set search_path = erp, public, pg_temp
as $function$
begin
  if p_business_date is null then raise exception 'CP3 business date lock requires a date'; end if;
  perform pg_advisory_xact_lock(hashtextextended(
    'ATTENDANCE_HPP_BUSINESS_DATE|' || erp._cp3_canonical_date(p_business_date), 0
  ));
end;
$function$;

create or replace function erp._cp3_lock_business_period(p_period_start date, p_period_end date)
returns void
language plpgsql
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_day date;
begin
  if p_period_start is null or p_period_end is null or p_period_end < p_period_start then
    raise exception 'CP3 business period lock requires a valid date range';
  end if;
  if p_period_end - p_period_start > 366 then
    raise exception 'CP3 business period lock is bounded to 367 calendar days';
  end if;
  for v_day in
    select d::date from generate_series(p_period_start::timestamp, p_period_end::timestamp, interval '1 day') d order by 1
  loop
    perform erp._cp3_lock_business_date(v_day);
  end loop;
end;
$function$;

create or replace function erp._cp3_lock_manifest_contractors(p_period_start date, p_period_end date)
returns void
language plpgsql
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_contractor_id uuid;
begin
  for v_contractor_id in
    select contractor_id
    from (
      select ps.contractor_id
      from erp.payroll_settlements ps
      where ps.status in ('APPROVED','PAID')
        and ps.period_start = p_period_start and ps.period_end = p_period_end
        and ps.attendance_total > 0
      union
      select e.contractor_id
      from erp.sewing_terminal_events e
      where e.event_kind = 'SELESAI_DIJAHIT'
        and erp._cp3_business_date(e.physical_at) between p_period_start and p_period_end
        and not exists (select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id)
    ) s
    order by contractor_id
  loop
    perform pg_advisory_xact_lock(hashtextextended('CONTRACTOR_HPP_POLICY|' || v_contractor_id::text, 0));
  end loop;
end;
$function$;

create or replace function erp.set_contractor_hpp_policy_v1(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_policy_id uuid default null
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'set_contractor_hpp_policy_v1';
  v_hash text;
  v_cached jsonb;
  v_contractor_id uuid;
  v_effective_from date;
  v_is_special boolean;
  v_attendance_required boolean;
  v_reason text;
  v_contractor erp.contractors%rowtype;
  v_current erp.contractor_hpp_policy_versions%rowtype;
  v_next_from date;
  v_new erp.contractor_hpp_policy_versions%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  perform erp._cp3_assert_closed_json_object(
    p_payload,
    array['contractor_id','effective_from','is_special','attendance_required','reason'],
    array['contractor_id','effective_from','is_special','attendance_required','reason'],
    'contractor HPP policy payload'
  );

  if jsonb_typeof(p_payload->'contractor_id') is distinct from 'string'
     or jsonb_typeof(p_payload->'effective_from') is distinct from 'string'
     or jsonb_typeof(p_payload->'is_special') is distinct from 'boolean'
     or jsonb_typeof(p_payload->'attendance_required') is distinct from 'boolean'
     or jsonb_typeof(p_payload->'reason') is distinct from 'string' then
    raise exception 'contractor HPP policy payload has invalid field types';
  end if;

  v_contractor_id := (p_payload->>'contractor_id')::uuid;
  v_effective_from := erp._cp3_parse_canonical_date(p_payload->>'effective_from', 'contractor HPP policy effective_from');
  v_is_special := (p_payload->>'is_special')::boolean;
  v_attendance_required := (p_payload->>'attendance_required')::boolean;
  v_reason := nullif(btrim(p_payload->>'reason'), '');

  if v_reason is null then raise exception 'HPP policy reason is required'; end if;
  if v_effective_from is null then raise exception 'effective_from is required'; end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'expected_policy_id', p_expected_policy_id
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_contractor
  from erp.contractors
  where id = v_contractor_id
  for update;

  if v_contractor.id is null then raise exception 'Contractor not found'; end if;
  if v_contractor.contractor_type <> 'MANDOR' then
    raise exception 'Attendance HPP policy is only valid for role MANDOR';
  end if;
  if v_contractor.attendance_required is distinct from v_attendance_required then
    raise exception 'attendance_required payload must explicitly match contractor master; update master first, then write a new HPP policy version';
  end if;

  perform pg_advisory_xact_lock(hashtextextended('CONTRACTOR_HPP_POLICY|' || v_contractor_id::text, 0));

  select * into v_current
  from erp.contractor_hpp_policy_versions p
  where p.contractor_id = v_contractor_id
    and v_effective_from >= p.effective_from
    and (p.effective_to is null or v_effective_from <= p.effective_to)
  order by p.effective_from desc, p.id desc
  limit 1
  for update;

  if v_current.id is distinct from p_expected_policy_id then
    raise exception 'STALE_POLICY expected %, current %', p_expected_policy_id, v_current.id;
  end if;
  if v_current.effective_from = v_effective_from then
    raise exception 'A contractor HPP policy already starts on this date';
  end if;

  select min(p.effective_from) into v_next_from
  from erp.contractor_hpp_policy_versions p
  where p.contractor_id = v_contractor_id
    and p.effective_from > v_effective_from;

  update erp.contractor_hpp_policy_versions p
  set effective_to = v_effective_from - 1,
      row_version = row_version + 1
  where p.contractor_id = v_contractor_id
    and p.effective_from < v_effective_from
    and (p.effective_to is null or p.effective_to >= v_effective_from);

  insert into erp.contractor_hpp_policy_versions(
    contractor_id, effective_from, effective_to,
    contractor_role_snapshot, attendance_required_snapshot,
    is_special, reason, created_by
  ) values (
    v_contractor_id, v_effective_from,
    case when v_next_from is null then null else v_next_from - 1 end,
    'MANDOR', v_attendance_required,
    v_is_special, v_reason, erp.current_app_user_id()
  ) returning * into v_new;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'contractor_hpp_policy_versions', v_new.id, 'INSERT',
    jsonb_build_object(
      'contractor_id', v_new.contractor_id,
      'effective_from', v_new.effective_from,
      'effective_to', v_new.effective_to,
      'contractor_role_snapshot', v_new.contractor_role_snapshot,
      'attendance_required_snapshot', v_new.attendance_required_snapshot,
      'is_special', v_new.is_special
    ),
    erp.current_app_user_id(), v_reason
  );

  v_response := jsonb_build_object(
    'policy_version_id', v_new.id,
    'contractor_id', v_new.contractor_id,
    'effective_from', v_new.effective_from,
    'effective_to', v_new.effective_to,
    'contractor_role_snapshot', v_new.contractor_role_snapshot,
    'attendance_required_snapshot', v_new.attendance_required_snapshot,
    'is_special', v_new.is_special,
    'row_version', v_new.row_version
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

-- A stale DRAFT must be voidable through the owning lifecycle instead of blocking the period forever.
alter table erp.attendance_hpp_pools
  drop constraint if exists attendance_hpp_pools_status_check;
alter table erp.attendance_hpp_pools
  add constraint attendance_hpp_pools_status_check
  check (status in ('DRAFT','ACTIVE','CANCELLED','VOIDED'));

alter table erp.attendance_hpp_pools
  drop constraint if exists attendance_hpp_pool_lifecycle_shape_check;
alter table erp.attendance_hpp_pools
  add constraint attendance_hpp_pool_lifecycle_shape_check check (
    (status = 'DRAFT' and post_journal_entry_id is null and cancellation_journal_entry_id is null)
    or (status = 'VOIDED' and post_journal_entry_id is null and cancellation_journal_entry_id is null
        and cancellation_reason is not null and cancelled_at is not null)
    or (status = 'ACTIVE' and post_journal_entry_id is not null and cancellation_journal_entry_id is null)
    or (status = 'CANCELLED' and post_journal_entry_id is not null and cancellation_journal_entry_id is not null)
  );

-- ---------------------------------------------------------------------------
-- APPROVED recognizes payroll cost; payment is settlement-only
-- ---------------------------------------------------------------------------

create or replace function erp.approve_payroll(p_payroll_id uuid)
returns void
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  p erp.payroll_settlements%rowtype;
  v_manual_reimburse numeric(20,2) := 0;
  v_extra_accrual numeric(20,2) := 0;
  v_negative_manual numeric(20,2) := 0;
  v_attendance numeric(20,2) := 0;
begin
  perform erp.require_owner_admin();
  perform erp.recalculate_payroll(p_payroll_id);
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null or p.status not in ('CALCULATED','REVIEW') then
    raise exception 'Payroll must be CALCULATED/REVIEW before approval, current status %',p.status;
  end if;

  perform erp._cp3_lock_business_period(p.period_start,p.period_end);
  if exists (
    select 1 from erp.journal_entries je
    where je.source_id=p.id
      and je.source_type in ('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION')
      and je.status='POSTED'
  ) then
    raise exception 'Payroll approval accrual already exists; inspect duplicate/ambiguous approval state';
  end if;

  select coalesce(sum(amount),0) into v_manual_reimburse
  from erp.payroll_reimbursements
  where payroll_id=p.id and source_type<>'ACCESSORY_BOM';
  v_attendance:=round(coalesce(p.attendance_total,0),2);
  v_extra_accrual:=round(v_manual_reimburse+greatest(p.manual_adjustment,0),2);
  v_negative_manual:=round(greatest(-p.manual_adjustment,0),2);

  update erp.payroll_settlements set status='APPROVED',updated_at=now() where id=p.id;

  if v_attendance>0 then
    perform erp.post_journal(
      'PAYROLL_ATTENDANCE_ACCRUAL',p.id,p.period_end,
      'Attendance payroll approved into unassigned WIP',
      jsonb_build_array(
        jsonb_build_object('mapping_key','WIP','debit',v_attendance,'credit',0,'contractor_id',p.contractor_id,
                           'description','Approved attendance cost awaiting SELESAI_DIJAHIT allocation'),
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_attendance,'contractor_id',p.contractor_id,
                           'description','Approved attendance payable')
      )
    );
  end if;
  if v_extra_accrual>0 then
    perform erp.post_journal(
      'PAYROLL_EXTRA_ACCRUAL',p.id,p.period_end,
      'Approved manual reimbursement/manual payroll accrual',
      jsonb_build_array(
        jsonb_build_object('mapping_key','LABOR_COST','debit',v_extra_accrual,'credit',0,'contractor_id',p.contractor_id),
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_extra_accrual,'contractor_id',p.contractor_id)
      )
    );
  end if;
  if v_negative_manual>0 then
    perform erp.post_journal(
      'PAYROLL_MANUAL_REDUCTION',p.id,p.period_end,
      'Approved negative manual payroll adjustment',
      jsonb_build_array(
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_negative_manual,'credit',0,'contractor_id',p.contractor_id),
        jsonb_build_object('mapping_key','LABOR_COST','debit',0,'credit',v_negative_manual,'contractor_id',p.contractor_id)
      )
    );
  end if;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values(
    'payroll_settlements',p.id,'POST',
    jsonb_build_object('lifecycle_action','APPROVE','attendance_accrual',v_attendance,
                       'extra_accrual',v_extra_accrual,'manual_reduction',v_negative_manual),
    erp.current_app_user_id(),'Payroll approved; cost recognition completed before payment'
  );
end;
$function$;

create or replace function erp.post_payroll_payment(p_payroll_id uuid)
returns void
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  p erp.payroll_settlements%rowtype;
  v_cash uuid;
  v_material_deduction numeric(20,2):=0;
  v_other_deduction numeric(20,2):=0;
  v_expected_attendance numeric(20,2):=0;
  v_actual_attendance numeric(20,2):=0;
  v_attendance_journal_count bigint:=0;
  r record;
begin
  perform erp.require_internal();
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null or p.status<>'APPROVED' then raise exception 'Payroll must be APPROVED'; end if;
  perform erp._cp3_lock_business_period(p.period_start,p.period_end);
  if p.net_payable<0 then raise exception 'Payroll net payable cannot be negative; carry deductions forward instead'; end if;
  if p.payment_date is null then raise exception 'Payroll payment date is required'; end if;
  if p.payment_date>current_date then raise exception 'Tanggal pembayaran payroll berada di masa depan'; end if;
  if p.net_payable>0 then
    select coa_account_id into v_cash from erp.cash_accounts where id=p.payment_cash_account_id and is_active=true;
    if v_cash is null then raise exception 'Active payroll cash/bank account is required when cash payment is positive'; end if;
  end if;

  v_expected_attendance:=round(coalesce(p.attendance_total,0),2);
  select count(distinct je.id),coalesce(sum(jl.debit),0)
    into v_attendance_journal_count,v_actual_attendance
  from erp.journal_entries je
  join erp.journal_lines jl on jl.journal_entry_id=je.id
  where je.source_type='PAYROLL_ATTENDANCE_ACCRUAL' and je.source_id=p.id and je.status='POSTED'
    and jl.account_id=erp.account_id('WIP') and jl.debit>0;
  if (v_expected_attendance=0 and v_attendance_journal_count<>0)
     or (v_expected_attendance>0 and (v_attendance_journal_count<>1 or round(v_actual_attendance,2) is distinct from v_expected_attendance)) then
    raise exception 'PAYROLL_APPROVAL_ACCRUAL_MISSING_OR_MISMATCH: expected attendance %, journal count %, WIP debit %',
      v_expected_attendance,v_attendance_journal_count,round(v_actual_attendance,2);
  end if;

  select coalesce(sum(amount),0) into v_material_deduction
  from erp.payroll_deductions where payroll_id=p.id and deduction_type='MATERIAL_KASBON';
  select coalesce(sum(amount),0) into v_other_deduction
  from erp.payroll_deductions where payroll_id=p.id and deduction_type<>'MATERIAL_KASBON';
  if v_material_deduction>0 then
    perform erp.post_journal('PAYROLL_MATERIAL_DEDUCTION',p.id,p.payment_date,
      'Physical material/accessory purchase deduction',jsonb_build_array(
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_material_deduction,'credit',0,'contractor_id',p.contractor_id),
        jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',v_material_deduction,'contractor_id',p.contractor_id)));
  end if;
  if v_other_deduction>0 then
    perform erp.post_journal('PAYROLL_OTHER_DEDUCTION',p.id,p.payment_date,
      'BS/penalty/other payroll deduction',jsonb_build_array(
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_other_deduction,'credit',0,'contractor_id',p.contractor_id),
        jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',v_other_deduction,'contractor_id',p.contractor_id)));
  end if;
  if p.net_payable>0 then
    perform erp.post_journal('PAYROLL_PAYMENT',p.id,p.payment_date,'Mandor payroll payment',jsonb_build_array(
      jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',p.net_payable,'credit',0,'contractor_id',p.contractor_id),
      jsonb_build_object('account_id',v_cash,'debit',0,'credit',p.net_payable,'contractor_id',p.contractor_id)));
  end if;

  update erp.payroll_settlements set status='PAID',settled_at=now(),updated_at=now() where id=p.id;
  for r in select distinct pd.contractor_issue_item_id id from erp.payroll_deductions pd
           where pd.payroll_id=p.id and pd.contractor_issue_item_id is not null
  loop perform erp.refresh_contractor_issue_payroll_status(r.id); end loop;
  update erp.contractor_accessory_reimbursement_entitlements e set payroll_status='SETTLED'
  where e.id in(select pr.source_id from erp.payroll_reimbursements pr
                where pr.payroll_id=p.id and pr.source_type='ACCESSORY_BOM' and pr.source_id is not null);
  for r in
    select distinct bc.id as bs_case_id from erp.bs_cases bc
    where exists(select 1 from erp.payroll_work_items pwi where pwi.payroll_id=p.id and pwi.po_id=bc.po_id)
       or exists(select 1 from erp.payroll_work_items pwi join erp.rework_component_lines rcl on rcl.id=pwi.source_id
                 join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
                 where pwi.payroll_id=p.id and bcc.bs_case_id=bc.id)
  loop perform erp.rebuild_bs_component_counters(r.bs_case_id); end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('payroll_settlements',p.id,'POST',
    jsonb_build_object('lifecycle_action','PAY','payment_settlement_only',true,'attendance_accrual_created_at_payment',false),
    erp.current_app_user_id(),'Payroll payment settled approved payable without recognizing attendance cost again');
end;
$function$;

create or replace function erp.cancel_unpaid_payroll(p_payroll_id uuid,p_reason text)
returns void
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  p erp.payroll_settlements%rowtype;
  r record;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Cancellation reason is required'; end if;
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null then raise exception 'Payroll not found'; end if;
  if p.status='PAID' then raise exception 'Paid payroll requires a dedicated financial reversal, not unpaid cancellation'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status not in ('DRAFT','CALCULATED','REVIEW','APPROVED') then raise exception 'Payroll cannot be cancelled in status %',p.status; end if;
  perform erp._cp3_lock_business_period(p.period_start,p.period_end);

  if exists(
    select 1 from erp.attendance_hpp_pool_sources s
    join erp.attendance_hpp_pools hp on hp.id=s.pool_id
    where s.payroll_id=p.id and hp.status='ACTIVE'
  ) then
    raise exception 'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL: cancel the active attendance HPP pool first';
  end if;

  for r in
    select je.id from erp.journal_entries je
    where je.source_id=p.id
      and je.source_type in ('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION')
      and je.status='POSTED'
    order by je.posting_at desc,je.id desc
  loop perform erp.reverse_journal(r.id,p_reason); end loop;

  update erp.payroll_settlements set status='REVERSED',settled_at=null,updated_at=now() where id=p.id;
  for r in select distinct pd.contractor_issue_item_id id from erp.payroll_deductions pd
           where pd.payroll_id=p.id and pd.contractor_issue_item_id is not null
  loop perform erp.refresh_contractor_issue_payroll_status(r.id); end loop;
  for r in select distinct pr.source_id id from erp.payroll_reimbursements pr
           where pr.payroll_id=p.id and pr.source_type='ACCESSORY_BOM' and pr.source_id is not null
  loop
    update erp.contractor_accessory_reimbursement_entitlements e
    set payroll_status=case
      when exists(select 1 from erp.payroll_reimbursements pr2 join erp.payroll_settlements ps2 on ps2.id=pr2.payroll_id
                  where pr2.source_type='ACCESSORY_BOM' and pr2.source_id=e.id and ps2.status='PAID') then 'SETTLED'
      when exists(select 1 from erp.payroll_reimbursements pr2 join erp.payroll_settlements ps2 on ps2.id=pr2.payroll_id
                  where pr2.source_type='ACCESSORY_BOM' and pr2.source_id=e.id and ps2.status<>'REVERSED') then 'ALLOCATED'
      else 'UNALLOCATED' end
    where e.id=r.id;
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('payroll_settlements',p.id,'CANCEL_UNPAID',jsonb_build_object('previous_status',p.status),erp.current_app_user_id(),p_reason);
end;
$function$;

create or replace function erp.reverse_paid_payroll(p_payroll_id uuid,p_reason text)
returns void
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  p erp.payroll_settlements%rowtype;
  r record;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Payroll reversal reason is required'; end if;
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null then raise exception 'Payroll not found'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'PAID' then raise exception 'Only PAID payroll uses reverse_paid_payroll; unpaid payroll uses cancel_unpaid_payroll'; end if;
  perform erp._cp3_lock_business_period(p.period_start,p.period_end);
  if exists(
    select 1 from erp.attendance_hpp_pool_sources s
    join erp.attendance_hpp_pools hp on hp.id=s.pool_id
    where s.payroll_id=p.id and hp.status='ACTIVE'
  ) then
    raise exception 'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL: cancel the active attendance HPP pool first';
  end if;

  for r in
    select je.id from erp.journal_entries je
    where je.source_id=p.id
      and je.source_type in ('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION',
                             'PAYROLL_MATERIAL_DEDUCTION','PAYROLL_OTHER_DEDUCTION','PAYROLL_PAYMENT')
      and je.status='POSTED'
    order by je.posting_at desc,je.id desc
  loop perform erp.reverse_journal(r.id,p_reason); end loop;

  update erp.payroll_settlements set status='REVERSED',settled_at=null,updated_at=now() where id=p.id;
  for r in select distinct pd.contractor_issue_item_id id from erp.payroll_deductions pd
           where pd.payroll_id=p.id and pd.contractor_issue_item_id is not null
  loop perform erp.refresh_contractor_issue_payroll_status(r.id); end loop;
  for r in select distinct pr.source_id id from erp.payroll_reimbursements pr
           where pr.payroll_id=p.id and pr.source_type='ACCESSORY_BOM' and pr.source_id is not null
  loop
    update erp.contractor_accessory_reimbursement_entitlements e
    set payroll_status=case
      when exists(select 1 from erp.payroll_reimbursements pr2 join erp.payroll_settlements ps2 on ps2.id=pr2.payroll_id
                  where pr2.source_type='ACCESSORY_BOM' and pr2.source_id=e.id and ps2.status='PAID') then 'SETTLED'
      when exists(select 1 from erp.payroll_reimbursements pr2 join erp.payroll_settlements ps2 on ps2.id=pr2.payroll_id
                  where pr2.source_type='ACCESSORY_BOM' and pr2.source_id=e.id and ps2.status<>'REVERSED') then 'ALLOCATED'
      else 'UNALLOCATED' end
    where e.id=r.id;
  end loop;
  for r in
    select distinct bc.id as bs_case_id from erp.bs_cases bc
    where exists(select 1 from erp.payroll_work_items pwi where pwi.payroll_id=p.id and pwi.po_id=bc.po_id)
       or exists(select 1 from erp.payroll_work_items pwi join erp.rework_component_lines rcl on rcl.id=pwi.source_id
                 join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
                 where pwi.payroll_id=p.id and bcc.bs_case_id=bc.id)
  loop perform erp.rebuild_bs_component_counters(r.bs_case_id); end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('payroll_settlements',p.id,'REVERSE_PAID',jsonb_build_object('previous_status','PAID'),erp.current_app_user_id(),p_reason);
end;
$function$;

create or replace function erp.record_sewing_terminal_v1(
  p_payload jsonb,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'record_sewing_terminal_v1';
  v_hash text;
  v_cached jsonb;
  v_work_completion_id uuid;
  v_qty integer;
  v_reason text;
  v_work erp.work_completion_events%rowtype;
  v_max_line_qty integer;
  v_cutting_qty bigint;
  v_existing_terminal_qty bigint;
  v_event erp.sewing_terminal_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_internal();
  perform erp._cp3_assert_closed_json_object(
    p_payload,
    array['work_completion_id','qty_pcs','reason'],
    array['work_completion_id','qty_pcs','reason'],
    'SELESAI_DIJAHIT payload'
  );

  if jsonb_typeof(p_payload->'work_completion_id') is distinct from 'string'
     or jsonb_typeof(p_payload->'qty_pcs') is distinct from 'number'
     or jsonb_typeof(p_payload->'reason') is distinct from 'string' then
    raise exception 'SELESAI_DIJAHIT payload has invalid field types';
  end if;

  v_work_completion_id := (p_payload->>'work_completion_id')::uuid;
  v_qty := (p_payload->>'qty_pcs')::integer;
  v_reason := nullif(btrim(p_payload->>'reason'), '');

  if v_qty <= 0 then raise exception 'SELESAI_DIJAHIT qty must be positive'; end if;
  if v_reason is null then raise exception 'SELESAI_DIJAHIT reason is required'; end if;

  v_hash := erp._request_hash(jsonb_build_object('payload', p_payload));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_work
  from erp.work_completion_events
  where id = v_work_completion_id
  for update;

  if v_work.id is null then raise exception 'Work completion not found'; end if;
  if v_work.status <> 'POSTED' then
    raise exception 'SELESAI_DIJAHIT can only reference a POSTED production work completion';
  end if;

  perform erp._cp3_lock_business_date(erp._cp3_business_date(v_work.physical_at));
  if exists (
    select 1 from erp.attendance_hpp_pools p
    where p.status = 'ACTIVE'
      and erp._cp3_business_date(v_work.physical_at) between p.period_start and p.period_end
  ) then
    raise exception 'ACTIVE_ATTENDANCE_HPP_PERIOD_LOCKED: cancel the active pool before recording late/backdated SELESAI_DIJAHIT';
  end if;
  if v_work.cutting_group_id is null then
    raise exception 'SELESAI_DIJAHIT requires cutting-group lineage';
  end if;
  if not exists (
    select 1 from erp.contractors c
    where c.id = v_work.contractor_id and c.contractor_type = 'MANDOR'
  ) then
    raise exception 'SELESAI_DIJAHIT source contractor must have explicit role MANDOR';
  end if;
  if exists (
    select 1 from erp.sewing_terminal_events e
    where e.source_work_completion_id = v_work.id
      and e.event_kind = 'SELESAI_DIJAHIT'
  ) then
    raise exception 'This work completion already has an authoritative SELESAI_DIJAHIT event';
  end if;

  select max(l.qty_completed)::integer into v_max_line_qty
  from erp.work_completion_lines l
  where l.completion_id = v_work.id;

  if coalesce(v_max_line_qty, 0) <= 0 or v_qty > v_max_line_qty then
    raise exception 'SELESAI_DIJAHIT qty % exceeds the maximum completed qty % recorded by the owning work completion',
      v_qty, coalesce(v_max_line_qty, 0);
  end if;

  perform 1 from erp.cutting_groups where id = v_work.cutting_group_id for update;
  select coalesce(v.total_pcs, 0)::bigint into v_cutting_qty
  from erp.v_cutting_group_totals v
  where v.cutting_group_id = v_work.cutting_group_id;

  select coalesce(sum(e.qty_signed), 0)::bigint into v_existing_terminal_qty
  from erp.sewing_terminal_events e
  where e.cutting_group_id = v_work.cutting_group_id;

  if v_existing_terminal_qty + v_qty > coalesce(v_cutting_qty, 0) then
    raise exception 'Cumulative SELESAI_DIJAHIT qty would exceed cutting-group physical qty. Current %, new %, maximum %',
      v_existing_terminal_qty, v_qty, coalesce(v_cutting_qty, 0);
  end if;

  insert into erp.sewing_terminal_events(
    event_number, event_kind, source_work_completion_id,
    contractor_id, po_id, cutting_group_id, physical_at,
    qty_signed, reason, created_by
  ) values (
    'SEW-' || to_char(v_work.physical_at at time zone 'UTC', 'YYYYMMDDHH24MISSUS') || '-' || substr(gen_random_uuid()::text, 1, 8),
    'SELESAI_DIJAHIT', v_work.id,
    v_work.contractor_id, v_work.po_id, v_work.cutting_group_id, v_work.physical_at,
    v_qty, v_reason, erp.current_app_user_id()
  ) returning * into v_event;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'sewing_terminal_events', v_event.id, 'POST',
    jsonb_build_object(
      'event_kind', v_event.event_kind,
      'source_work_completion_id', v_event.source_work_completion_id,
      'contractor_id', v_event.contractor_id,
      'po_id', v_event.po_id,
      'cutting_group_id', v_event.cutting_group_id,
      'physical_at_epoch_us', erp._cp3_epoch_microseconds(v_event.physical_at),
      'qty_signed', v_event.qty_signed
    ),
    erp.current_app_user_id(), v_reason
  );

  v_response := jsonb_build_object(
    'sewing_terminal_event_id', v_event.id,
    'event_number', v_event.event_number,
    'event_kind', v_event.event_kind,
    'source_work_completion_id', v_event.source_work_completion_id,
    'physical_at_epoch_us', erp._cp3_epoch_microseconds(v_event.physical_at),
    'qty_pcs', v_event.qty_signed,
    'row_version', v_event.row_version
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.reverse_sewing_terminal_v1(
  p_event_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'reverse_sewing_terminal_v1';
  v_hash text;
  v_cached jsonb;
  v_original erp.sewing_terminal_events%rowtype;
  v_reversal erp.sewing_terminal_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  if p_event_id is null or p_expected_version is null then
    raise exception 'event_id and expected_version are required';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'SELESAI_DIJAHIT reversal reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'event_id', p_event_id,
    'reason', btrim(p_reason),
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_original
  from erp.sewing_terminal_events
  where id = p_event_id
  for update;

  if v_original.id is null or v_original.event_kind <> 'SELESAI_DIJAHIT' then
    raise exception 'Original SELESAI_DIJAHIT event not found';
  end if;
  if v_original.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_original.row_version;
  end if;

  perform erp._cp3_lock_business_date(erp._cp3_business_date(v_original.physical_at));
  if exists (select 1 from erp.sewing_terminal_events where reversal_of_id = v_original.id) then
    raise exception 'SELESAI_DIJAHIT event is already reversed';
  end if;
  if exists (
    select 1
    from erp.attendance_hpp_pool_allocations a
    join erp.attendance_hpp_pools p on p.id = a.pool_id
    where a.sewing_terminal_event_id = v_original.id
      and p.status = 'ACTIVE'
  ) then
    raise exception 'SELESAI_DIJAHIT is consumed by an ACTIVE attendance HPP pool; cancel that pool first';
  end if;

  insert into erp.sewing_terminal_events(
    event_number, event_kind, reversal_of_id,
    contractor_id, po_id, cutting_group_id, physical_at,
    qty_signed, reason, created_by
  ) values (
    'SEW-RV-' || to_char(clock_timestamp() at time zone 'UTC', 'YYYYMMDDHH24MISSUS') || '-' || substr(gen_random_uuid()::text, 1, 8),
    'REVERSAL', v_original.id,
    v_original.contractor_id, v_original.po_id, v_original.cutting_group_id,
    v_original.physical_at, -v_original.qty_signed,
    btrim(p_reason), erp.current_app_user_id()
  ) returning * into v_reversal;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'sewing_terminal_events', v_original.id, 'REVERSE',
    jsonb_build_object(
      'reversal_event_id', v_reversal.id,
      'qty_signed', v_reversal.qty_signed,
      'original_physical_at_epoch_us', erp._cp3_epoch_microseconds(v_original.physical_at)
    ),
    erp.current_app_user_id(), btrim(p_reason)
  );

  v_response := jsonb_build_object(
    'original_event_id', v_original.id,
    'reversal_event_id', v_reversal.id,
    'status', 'REVERSED',
    'qty_reversed', v_original.qty_signed
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp._build_attendance_hpp_manifest_v1(
  p_period_start date,
  p_period_end date
)
returns jsonb
language sql
stable
security definer
set search_path = erp, public, pg_temp
as $function$
with eligible_payrolls as (
  select
    ps.id as payroll_id,
    ps.contractor_id,
    ps.attendance_total::numeric(20,2) as attendance_amount,
    pol.id as policy_version_id,
    pol.contractor_role_snapshot,
    pol.attendance_required_snapshot,
    pol.is_special,
    pol.effective_from as policy_effective_from,
    pol.effective_to as policy_effective_to,
    jl.id as original_debit_journal_line_id,
    jl.debit::numeric(20,2) as original_debit_amount
  from erp.payroll_settlements ps
  join lateral (
    select p.*
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id = ps.contractor_id
      and p.effective_from <= p_period_start
      and (p.effective_to is null or p.effective_to >= p_period_end)
    order by p.effective_from desc, p.id desc
    limit 1
  ) pol on true
  join lateral (
    select jl.*
    from erp.journal_entries je
    join erp.journal_lines jl on jl.journal_entry_id = je.id
    where je.source_id = ps.id
      and je.source_type = 'PAYROLL_ATTENDANCE_ACCRUAL'
      and je.status = 'POSTED'
      and jl.account_id = erp.account_id('WIP')
      and jl.debit > 0
    order by je.posting_at, je.id, jl.id
    limit 1
  ) jl on true
  where ps.status in ('APPROVED','PAID')
    and ps.period_start = p_period_start
    and ps.period_end = p_period_end
    and ps.attendance_total > 0
    and pol.contractor_role_snapshot = 'MANDOR'
    and pol.attendance_required_snapshot
    and not pol.is_special
), eligible_sewing as (
  select
    e.id as sewing_terminal_event_id,
    e.source_work_completion_id,
    e.contractor_id,
    e.po_id,
    e.cutting_group_id,
    e.physical_at,
    e.qty_signed as sewing_qty,
    pol.id as policy_version_id,
    pol.contractor_role_snapshot,
    pol.attendance_required_snapshot,
    pol.is_special
  from erp.sewing_terminal_events e
  join erp.work_completion_events w on w.id = e.source_work_completion_id
  join lateral (
    select p.*
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id = e.contractor_id
      and p.effective_from <= p_period_start
      and (p.effective_to is null or p.effective_to >= p_period_end)
    order by p.effective_from desc, p.id desc
    limit 1
  ) pol on true
  where e.event_kind = 'SELESAI_DIJAHIT'
    and erp._cp3_business_date(e.physical_at) between p_period_start and p_period_end
    and w.status = 'POSTED'
    and pol.contractor_role_snapshot = 'MANDOR'
    and pol.attendance_required_snapshot
    and not pol.is_special
    and not exists (
      select 1 from erp.sewing_terminal_events rv
      where rv.event_kind = 'REVERSAL' and rv.reversal_of_id = e.id
    )
), source_json as (
  select coalesce(jsonb_agg(jsonb_build_object(
    'payroll_id', payroll_id,
    'contractor_id', contractor_id,
    'policy_version_id', policy_version_id,
    'contractor_role_snapshot', contractor_role_snapshot,
    'attendance_required_snapshot', attendance_required_snapshot,
    'is_special_snapshot', is_special,
    'policy_effective_from', erp._cp3_canonical_date(policy_effective_from),
    'policy_effective_to', case when policy_effective_to is null then null else erp._cp3_canonical_date(policy_effective_to) end,
    'original_debit_journal_line_id', original_debit_journal_line_id,
    'original_debit_amount_cents', round(original_debit_amount * 100)::bigint,
    'attendance_amount_cents', round(attendance_amount * 100)::bigint
  ) order by contractor_id, payroll_id, original_debit_journal_line_id), '[]'::jsonb) value,
  coalesce(sum(round(attendance_amount * 100)::bigint), 0)::bigint numerator_cents
  from eligible_payrolls
), destination_json as (
  select coalesce(jsonb_agg(jsonb_build_object(
    'sewing_terminal_event_id', sewing_terminal_event_id,
    'source_work_completion_id', source_work_completion_id,
    'contractor_id', contractor_id,
    'po_id', po_id,
    'cutting_group_id', cutting_group_id,
    'policy_version_id', policy_version_id,
    'contractor_role_snapshot', contractor_role_snapshot,
    'attendance_required_snapshot', attendance_required_snapshot,
    'is_special_snapshot', is_special,
    'physical_at_epoch_us', erp._cp3_epoch_microseconds(physical_at),
    'sewing_qty', sewing_qty
  ) order by physical_at, sewing_terminal_event_id), '[]'::jsonb) value,
  coalesce(sum(sewing_qty), 0)::bigint denominator_qty
  from eligible_sewing
)
select jsonb_build_object(
  'contract_version', 'ATTENDANCE_HPP_SEWING_TERMINAL_V1',
  'operation_type', 'ATTENDANCE_HPP_POOL',
  'period_start', erp._cp3_canonical_date(p_period_start),
  'period_end', erp._cp3_canonical_date(p_period_end),
  'numerator_cents', source_json.numerator_cents,
  'denominator_qty', destination_json.denominator_qty,
  'sources', source_json.value,
  'destinations', destination_json.value
)
from source_json, destination_json
$function$;

create or replace function erp._assert_attendance_hpp_manifest_v1(p_manifest jsonb)
returns void
language plpgsql
immutable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_item jsonb;
begin
  perform erp._cp3_assert_closed_json_object(
    p_manifest,
    array['contract_version','operation_type','period_start','period_end','numerator_cents','denominator_qty','sources','destinations'],
    array['contract_version','operation_type','period_start','period_end','numerator_cents','denominator_qty','sources','destinations'],
    'attendance HPP manifest'
  );

  if jsonb_typeof(p_manifest->'contract_version') is distinct from 'string'
     or jsonb_typeof(p_manifest->'operation_type') is distinct from 'string'
     or jsonb_typeof(p_manifest->'period_start') is distinct from 'string'
     or jsonb_typeof(p_manifest->'period_end') is distinct from 'string'
     or jsonb_typeof(p_manifest->'numerator_cents') is distinct from 'number'
     or jsonb_typeof(p_manifest->'denominator_qty') is distinct from 'number'
     or jsonb_typeof(p_manifest->'sources') is distinct from 'array'
     or jsonb_typeof(p_manifest->'destinations') is distinct from 'array' then
    raise exception 'Attendance HPP manifest has invalid top-level types';
  end if;

  if p_manifest->>'contract_version' is distinct from 'ATTENDANCE_HPP_SEWING_TERMINAL_V1'
     or p_manifest->>'operation_type' is distinct from 'ATTENDANCE_HPP_POOL' then
    raise exception 'Attendance HPP manifest discriminator is invalid; claim/transfer/carry-forward/movement payloads are not accepted';
  end if;
  if p_manifest->>'period_start' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     or p_manifest->>'period_end' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then
    raise exception 'Attendance HPP manifest period dates must be canonical YYYY-MM-DD strings';
  end if;

  for v_item in select value from jsonb_array_elements(p_manifest->'sources')
  loop
    perform erp._cp3_assert_closed_json_object(
      v_item,
      array['payroll_id','contractor_id','policy_version_id','contractor_role_snapshot','attendance_required_snapshot','is_special_snapshot','policy_effective_from','original_debit_journal_line_id','original_debit_amount_cents','attendance_amount_cents'],
      array['payroll_id','contractor_id','policy_version_id','contractor_role_snapshot','attendance_required_snapshot','is_special_snapshot','policy_effective_from','policy_effective_to','original_debit_journal_line_id','original_debit_amount_cents','attendance_amount_cents'],
      'attendance HPP source'
    );
    if not (v_item ? 'policy_effective_to') then
      raise exception 'attendance HPP source requires key policy_effective_to, which may be JSON null for open-ended coverage';
    end if;
    if jsonb_typeof(v_item->'payroll_id') is distinct from 'string'
       or jsonb_typeof(v_item->'contractor_id') is distinct from 'string'
       or jsonb_typeof(v_item->'policy_version_id') is distinct from 'string'
       or jsonb_typeof(v_item->'contractor_role_snapshot') is distinct from 'string'
       or jsonb_typeof(v_item->'attendance_required_snapshot') is distinct from 'boolean'
       or jsonb_typeof(v_item->'is_special_snapshot') is distinct from 'boolean'
       or jsonb_typeof(v_item->'policy_effective_from') is distinct from 'string'
       or (v_item->'policy_effective_to' <> 'null'::jsonb
           and jsonb_typeof(v_item->'policy_effective_to') is distinct from 'string')
       or jsonb_typeof(v_item->'original_debit_journal_line_id') is distinct from 'string'
       or jsonb_typeof(v_item->'original_debit_amount_cents') is distinct from 'number'
       or jsonb_typeof(v_item->'attendance_amount_cents') is distinct from 'number' then
      raise exception 'attendance HPP source has invalid nested field types';
    end if;
    if v_item->>'contractor_role_snapshot' is distinct from 'MANDOR'
       or v_item->'attendance_required_snapshot' is distinct from 'true'::jsonb
       or v_item->'is_special_snapshot' is distinct from 'false'::jsonb then
      raise exception 'Attendance HPP source is not an eligible normal Mandor snapshot';
    end if;
    if v_item->>'policy_effective_from' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
       or (v_item->'policy_effective_to' <> 'null'::jsonb
           and v_item->>'policy_effective_to' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$') then
      raise exception 'attendance HPP source policy dates must be canonical YYYY-MM-DD strings';
    end if;
  end loop;

  for v_item in select value from jsonb_array_elements(p_manifest->'destinations')
  loop
    perform erp._cp3_assert_closed_json_object(
      v_item,
      array['sewing_terminal_event_id','source_work_completion_id','contractor_id','po_id','cutting_group_id','policy_version_id','contractor_role_snapshot','attendance_required_snapshot','is_special_snapshot','physical_at_epoch_us','sewing_qty'],
      array['sewing_terminal_event_id','source_work_completion_id','contractor_id','po_id','cutting_group_id','policy_version_id','contractor_role_snapshot','attendance_required_snapshot','is_special_snapshot','physical_at_epoch_us','sewing_qty'],
      'attendance HPP destination'
    );
    if jsonb_typeof(v_item->'sewing_terminal_event_id') is distinct from 'string'
       or jsonb_typeof(v_item->'source_work_completion_id') is distinct from 'string'
       or jsonb_typeof(v_item->'contractor_id') is distinct from 'string'
       or jsonb_typeof(v_item->'po_id') is distinct from 'string'
       or jsonb_typeof(v_item->'cutting_group_id') is distinct from 'string'
       or jsonb_typeof(v_item->'policy_version_id') is distinct from 'string'
       or jsonb_typeof(v_item->'contractor_role_snapshot') is distinct from 'string'
       or jsonb_typeof(v_item->'attendance_required_snapshot') is distinct from 'boolean'
       or jsonb_typeof(v_item->'is_special_snapshot') is distinct from 'boolean'
       or jsonb_typeof(v_item->'physical_at_epoch_us') is distinct from 'number'
       or jsonb_typeof(v_item->'sewing_qty') is distinct from 'number' then
      raise exception 'attendance HPP destination has invalid nested field types';
    end if;
    if v_item->>'contractor_role_snapshot' is distinct from 'MANDOR'
       or v_item->'attendance_required_snapshot' is distinct from 'true'::jsonb
       or v_item->'is_special_snapshot' is distinct from 'false'::jsonb then
      raise exception 'Attendance HPP destination is not an eligible normal Mandor snapshot';
    end if;
  end loop;
end;
$function$;

create or replace function erp.preview_attendance_hpp_pool_v1(
  p_period_start date,
  p_period_end date
)
returns jsonb
language plpgsql
stable
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  v_manifest jsonb;
  v_missing_policy_count bigint;
  v_bad_attendance_snapshot_count bigint;
  v_bad_journal_count bigint;
  v_numerator_cents bigint;
  v_denominator_qty bigint;
begin
  perform erp.require_internal();
  if p_period_start is null or p_period_end is null or p_period_end < p_period_start then
    raise exception 'Valid period_start and period_end are required';
  end if;

  select count(*) into v_missing_policy_count
  from erp.payroll_settlements ps
  join erp.contractors c on c.id = ps.contractor_id
  where ps.status in ('APPROVED','PAID')
    and ps.period_start = p_period_start
    and ps.period_end = p_period_end
    and ps.attendance_total > 0
    and c.contractor_type = 'MANDOR'
    and not exists (
      select 1
      from erp.contractor_hpp_policy_versions p
      where p.contractor_id = ps.contractor_id
        and p.effective_from <= p_period_start
        and (p.effective_to is null or p.effective_to >= p_period_end)
    );
  if v_missing_policy_count > 0 then
    raise exception '% approved/paid attendance payroll(s) lack one explicit HPP policy covering the full period', v_missing_policy_count;
  end if;

  select count(*) into v_bad_attendance_snapshot_count
  from erp.payroll_settlements ps
  where ps.status in ('APPROVED','PAID')
    and ps.period_start = p_period_start
    and ps.period_end = p_period_end
    and abs(ps.attendance_total - coalesce((
      select sum(pai.amount) from erp.payroll_attendance_items pai where pai.payroll_id = ps.id
    ), 0)) > 0.01;
  if v_bad_attendance_snapshot_count > 0 then
    raise exception '% payroll attendance total(s) do not reconcile to immutable attendance items', v_bad_attendance_snapshot_count;
  end if;

  select count(*) into v_bad_journal_count
  from erp.payroll_settlements ps
  join lateral (
    select count(*) as line_count, max(jl.debit) as debit_amount
    from erp.journal_entries je
    join erp.journal_lines jl on jl.journal_entry_id = je.id
    where je.source_id = ps.id
      and je.source_type = 'PAYROLL_ATTENDANCE_ACCRUAL'
      and je.status = 'POSTED'
      and jl.account_id = erp.account_id('WIP')
      and jl.debit > 0
  ) x on true
  where ps.status in ('APPROVED','PAID')
    and ps.period_start = p_period_start
    and ps.period_end = p_period_end
    and ps.attendance_total > 0
    and (x.line_count <> 1 or x.debit_amount + 0.01 < ps.attendance_total);
  if v_bad_journal_count > 0 then
    raise exception '% approved/paid attendance payroll(s) lack one unambiguous WIP debit line from PAYROLL_ATTENDANCE_ACCRUAL covering attendance amount', v_bad_journal_count;
  end if;

  v_manifest := erp._build_attendance_hpp_manifest_v1(p_period_start, p_period_end);
  perform erp._assert_attendance_hpp_manifest_v1(v_manifest);
  v_numerator_cents := (v_manifest->>'numerator_cents')::bigint;
  v_denominator_qty := (v_manifest->>'denominator_qty')::bigint;

  if v_numerator_cents <= 0 then
    raise exception 'No eligible normal-Mandor attendance payroll cost exists for this exact period';
  end if;
  if v_denominator_qty <= 0 then
    raise exception 'POSITIVE_POOL_ZERO_SEWING_OUTPUT: attendance cost exists but immutable SELESAI_DIJAHIT denominator is zero; keep cost unassigned/WIP and do not use QC GOOD fallback';
  end if;

  return jsonb_build_object(
    'status', 'READY',
    'manifest', v_manifest,
    'manifest_sha256', erp._cp3_manifest_sha256(v_manifest),
    'numerator_amount', v_numerator_cents / 100.0,
    'denominator_qty', v_denominator_qty,
    'unit_cost_per_sewn_pcs', (v_numerator_cents / 100.0) / v_denominator_qty
  );
end;
$function$;

create or replace function erp.create_attendance_hpp_pool_v1(
  p_payload jsonb,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'create_attendance_hpp_pool_v1';
  v_hash text;
  v_cached jsonb;
  v_period_start date;
  v_period_end date;
  v_reason text;
  v_correction_of uuid;
  v_preview jsonb;
  v_manifest jsonb;
  v_pool erp.attendance_hpp_pools%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  perform erp._cp3_assert_closed_json_object(
    p_payload,
    array['period_start','period_end','reason'],
    array['period_start','period_end','reason','correction_of_pool_id'],
    'attendance HPP pool payload'
  );
  if jsonb_typeof(p_payload->'period_start') is distinct from 'string'
     or jsonb_typeof(p_payload->'period_end') is distinct from 'string'
     or jsonb_typeof(p_payload->'reason') is distinct from 'string'
     or (p_payload ? 'correction_of_pool_id'
         and coalesce(jsonb_typeof(p_payload->'correction_of_pool_id'), 'missing') not in ('string','null')) then
    raise exception 'Attendance HPP pool payload has invalid field types';
  end if;

  v_period_start := erp._cp3_parse_canonical_date(p_payload->>'period_start', 'attendance HPP period_start');
  v_period_end := erp._cp3_parse_canonical_date(p_payload->>'period_end', 'attendance HPP period_end');
  v_reason := nullif(btrim(p_payload->>'reason'), '');
  v_correction_of := nullif(p_payload->>'correction_of_pool_id', '')::uuid;
  if v_reason is null then raise exception 'Attendance HPP pool reason is required'; end if;

  v_hash := erp._request_hash(jsonb_build_object('payload', p_payload));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform erp._cp3_lock_business_period(v_period_start, v_period_end);
  perform erp._cp3_lock_manifest_contractors(v_period_start, v_period_end);

  if exists (
    select 1 from erp.attendance_hpp_pools p
    where p.period_start = v_period_start
      and p.period_end = v_period_end
      and p.status in ('DRAFT','ACTIVE')
  ) then
    raise exception 'A DRAFT/ACTIVE attendance HPP pool already exists for this exact period';
  end if;
  if v_correction_of is not null and not exists (
    select 1 from erp.attendance_hpp_pools p
    where p.id = v_correction_of
      and p.status = 'CANCELLED'
      and p.period_start = v_period_start
      and p.period_end = v_period_end
  ) then
    raise exception 'correction_of_pool_id must reference a CANCELLED pool for the same exact period';
  end if;

  v_preview := erp.preview_attendance_hpp_pool_v1(v_period_start, v_period_end);
  v_manifest := v_preview->'manifest';

  insert into erp.attendance_hpp_pools(
    pool_number, period_start, period_end, correction_of_pool_id,
    numerator_amount, denominator_qty, unit_cost_per_sewn_pcs,
    source_manifest, source_manifest_sha256,
    reason, created_by
  ) values (
    'AHPP-' || to_char(clock_timestamp() at time zone 'UTC', 'YYYYMMDDHH24MISSUS') || '-' || substr(gen_random_uuid()::text, 1, 8),
    v_period_start, v_period_end, v_correction_of,
    (v_preview->>'numerator_amount')::numeric,
    (v_preview->>'denominator_qty')::bigint,
    (v_preview->>'unit_cost_per_sewn_pcs')::numeric,
    v_manifest, v_preview->>'manifest_sha256',
    v_reason, erp.current_app_user_id()
  ) returning * into v_pool;

  insert into erp.attendance_hpp_pool_sources(
    pool_id, payroll_id, contractor_id, policy_version_id,
    original_debit_journal_line_id,
    contractor_role_snapshot, attendance_required_snapshot, is_special_snapshot,
    attendance_amount
  )
  select
    v_pool.id,
    (x->>'payroll_id')::uuid,
    (x->>'contractor_id')::uuid,
    (x->>'policy_version_id')::uuid,
    (x->>'original_debit_journal_line_id')::uuid,
    x->>'contractor_role_snapshot',
    (x->>'attendance_required_snapshot')::boolean,
    (x->>'is_special_snapshot')::boolean,
    ((x->>'attendance_amount_cents')::bigint / 100.0)::numeric(20,2)
  from jsonb_array_elements(v_manifest->'sources') x;

  with destination as (
    select
      (x->>'sewing_terminal_event_id')::uuid sewing_terminal_event_id,
      (x->>'contractor_id')::uuid contractor_id,
      (x->>'po_id')::uuid po_id,
      nullif(x->>'cutting_group_id', '')::uuid cutting_group_id,
      (x->>'sewing_qty')::integer sewing_qty,
      sum((x->>'sewing_qty')::bigint) over (
        order by (x->>'physical_at_epoch_us')::bigint,
                 (x->>'sewing_terminal_event_id')::uuid
        rows between unbounded preceding and current row
      ) cumulative_qty,
      coalesce(sum((x->>'sewing_qty')::bigint) over (
        order by (x->>'physical_at_epoch_us')::bigint,
                 (x->>'sewing_terminal_event_id')::uuid
        rows between unbounded preceding and 1 preceding
      ), 0) previous_cumulative_qty
    from jsonb_array_elements(v_manifest->'destinations') x
  ), source as (
    select s.*, round(s.attendance_amount * 100)::bigint source_cents
    from erp.attendance_hpp_pool_sources s
    where s.pool_id = v_pool.id
  )
  insert into erp.attendance_hpp_pool_allocations(
    pool_id, pool_source_id, sewing_terminal_event_id,
    contractor_id, po_id, cutting_group_id,
    sewing_qty, allocated_amount
  )
  select
    v_pool.id, s.id, d.sewing_terminal_event_id,
    d.contractor_id, d.po_id, d.cutting_group_id,
    d.sewing_qty,
    (
      floor(s.source_cents::numeric * d.cumulative_qty::numeric / v_pool.denominator_qty)
      - floor(s.source_cents::numeric * d.previous_cumulative_qty::numeric / v_pool.denominator_qty)
    ) / 100.0
  from source s cross join destination d
  order by s.id, d.cumulative_qty, d.sewing_terminal_event_id;

  if exists (
    select 1
    from erp.attendance_hpp_pool_sources s
    left join erp.attendance_hpp_pool_allocations a on a.pool_source_id = s.id
    where s.pool_id = v_pool.id
    group by s.id, s.attendance_amount
    having round(coalesce(sum(a.allocated_amount), 0), 2) is distinct from round(s.attendance_amount, 2)
  ) then
    raise exception 'Deterministic allocation failed to reconcile a source debit line exactly to cents';
  end if;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'attendance_hpp_pools', v_pool.id, 'INSERT',
    jsonb_build_object(
      'period_start', v_pool.period_start,
      'period_end', v_pool.period_end,
      'numerator_amount', v_pool.numerator_amount,
      'denominator_qty', v_pool.denominator_qty,
      'manifest_sha256', v_pool.source_manifest_sha256,
      'correction_of_pool_id', v_pool.correction_of_pool_id,
      'lifecycle_action', 'CREATE_DRAFT'
    ),
    erp.current_app_user_id(), v_reason
  );

  v_response := jsonb_build_object(
    'pool_id', v_pool.id,
    'pool_number', v_pool.pool_number,
    'status', v_pool.status,
    'row_version', v_pool.row_version,
    'numerator_amount', v_pool.numerator_amount,
    'denominator_qty', v_pool.denominator_qty,
    'unit_cost_per_sewn_pcs', v_pool.unit_cost_per_sewn_pcs,
    'manifest_sha256', v_pool.source_manifest_sha256
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.validate_attendance_hpp_pool_v1(p_pool_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  v_pool erp.attendance_hpp_pools%rowtype;
  v_source_count bigint;
  v_destination_count bigint;
  v_bad_sources bigint;
  v_bad_allocations bigint;
  v_current_manifest jsonb;
  v_source_total numeric(20,2);
  v_allocation_total numeric(20,2);
  v_journal_debit numeric(20,2);
  v_journal_credit numeric(20,2);
  v_source_credit_link_count bigint;
begin
  select * into v_pool from erp.attendance_hpp_pools where id = p_pool_id;
  if v_pool.id is null then raise exception 'Attendance HPP pool not found'; end if;

  v_current_manifest := erp._build_attendance_hpp_manifest_v1(v_pool.period_start, v_pool.period_end);
  perform erp._assert_attendance_hpp_manifest_v1(v_current_manifest);
  if erp._cp3_manifest_sha256(v_current_manifest) is distinct from v_pool.source_manifest_sha256
     or v_current_manifest is distinct from v_pool.source_manifest then
    raise exception 'STALE_POOL_INPUT: payroll, policy, journal debit, or SELESAI_DIJAHIT facts changed after preview';
  end if;

  select count(*), coalesce(sum(attendance_amount), 0)
    into v_source_count, v_source_total
  from erp.attendance_hpp_pool_sources where pool_id = v_pool.id;

  select count(distinct sewing_terminal_event_id), coalesce(sum(allocated_amount), 0)
    into v_destination_count, v_allocation_total
  from erp.attendance_hpp_pool_allocations where pool_id = v_pool.id;

  select count(*) into v_bad_sources
  from erp.attendance_hpp_pool_sources s
  join erp.payroll_settlements ps on ps.id = s.payroll_id
  join erp.contractor_hpp_policy_versions p on p.id = s.policy_version_id
  join erp.journal_lines jl on jl.id = s.original_debit_journal_line_id
  join erp.journal_entries je on je.id = jl.journal_entry_id
  where s.pool_id = v_pool.id
    and (
      s.contractor_role_snapshot is distinct from 'MANDOR'
      or s.attendance_required_snapshot is distinct from true
      or s.is_special_snapshot is distinct from false
      or ps.status not in ('APPROVED','PAID')
      or ps.period_start is distinct from v_pool.period_start
      or ps.period_end is distinct from v_pool.period_end
      or p.contractor_id is distinct from s.contractor_id
      or p.effective_from > v_pool.period_start
      or (p.effective_to is not null and p.effective_to < v_pool.period_end)
      or je.status is distinct from 'POSTED'
      or je.source_id is distinct from ps.id
      or je.source_type is distinct from 'PAYROLL_ATTENDANCE_ACCRUAL'
      or jl.account_id is distinct from erp.account_id('WIP')
      or jl.debit + 0.01 < s.attendance_amount
    );

  select count(*) into v_bad_allocations
  from erp.attendance_hpp_pool_allocations a
  join erp.attendance_hpp_pool_sources s on s.id = a.pool_source_id
  join erp.sewing_terminal_events e on e.id = a.sewing_terminal_event_id
  join erp.work_completion_events w on w.id = e.source_work_completion_id
  where a.pool_id = v_pool.id
    and (
      s.pool_id is distinct from v_pool.id
      or e.event_kind is distinct from 'SELESAI_DIJAHIT'
      or e.qty_signed <= 0
      or erp._cp3_business_date(e.physical_at) not between v_pool.period_start and v_pool.period_end
      or w.status is distinct from 'POSTED'
      or exists (select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id = e.id)
      or a.contractor_id is distinct from e.contractor_id
      or a.po_id is distinct from e.po_id
      or a.cutting_group_id is distinct from e.cutting_group_id
      or a.sewing_qty is distinct from e.qty_signed
    );

  if v_source_count = 0 or v_destination_count = 0
     or v_bad_sources > 0 or v_bad_allocations > 0
     or round(v_source_total, 2) is distinct from round(v_pool.numerator_amount, 2)
     or round(v_allocation_total, 2) is distinct from round(v_pool.numerator_amount, 2)
     or v_pool.denominator_qty <> (
       select coalesce(sum(e.qty_signed), 0)::bigint
       from erp.sewing_terminal_events e
       where e.id in (
         select distinct sewing_terminal_event_id
         from erp.attendance_hpp_pool_allocations
         where pool_id = v_pool.id
       )
     )
     or exists (
       select 1
       from erp.attendance_hpp_pool_sources s
       left join erp.attendance_hpp_pool_allocations a on a.pool_source_id = s.id
       where s.pool_id = v_pool.id
       group by s.id, s.attendance_amount
       having round(coalesce(sum(a.allocated_amount), 0), 2) is distinct from round(s.attendance_amount, 2)
     ) then
    raise exception 'Attendance HPP pool failed bounded set-based source/allocation validation';
  end if;

  if v_pool.status in ('ACTIVE','CANCELLED') then
    select coalesce(sum(jl.debit),0), coalesce(sum(jl.credit),0)
      into v_journal_debit, v_journal_credit
    from erp.journal_lines jl
    where jl.journal_entry_id = v_pool.post_journal_entry_id;

    select count(*) into v_source_credit_link_count
    from erp.attendance_hpp_journal_line_links l
    where l.pool_id = v_pool.id and l.link_type = 'SOURCE_CREDIT';

    if round(v_journal_debit,2) is distinct from round(v_pool.numerator_amount,2)
       or round(v_journal_credit,2) is distinct from round(v_pool.numerator_amount,2)
       or v_source_credit_link_count <> v_source_count
       or exists (
         select 1
         from erp.attendance_hpp_pool_sources s
         left join erp.attendance_hpp_journal_line_links l
           on l.pool_source_id = s.id
          and l.link_type = 'SOURCE_CREDIT'
         where s.pool_id = v_pool.id
         group by s.id, s.original_debit_journal_line_id, s.attendance_amount
         having count(l.id) <> 1
            or bool_or(l.original_debit_journal_line_id is distinct from s.original_debit_journal_line_id)
            or round(coalesce(sum(l.amount),0),2) is distinct from round(s.attendance_amount,2)
       ) then
      raise exception 'Attendance HPP journal does not reconcile one terminal credit per original pool debit line';
    end if;
  end if;

  return jsonb_build_object(
    'pool_id', v_pool.id,
    'status', v_pool.status,
    'source_count', v_source_count,
    'destination_count', v_destination_count,
    'numerator_amount', v_pool.numerator_amount,
    'denominator_qty', v_pool.denominator_qty,
    'manifest_sha256', v_pool.source_manifest_sha256,
    'validation', 'PASS'
  );
end;
$function$;

create or replace function erp.activate_attendance_hpp_pool_v1(
  p_pool_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'activate_attendance_hpp_pool_v1';
  v_hash text;
  v_cached jsonb;
  v_pool erp.attendance_hpp_pools%rowtype;
  v_lines jsonb := '[]'::jsonb;
  v_journal_id uuid;
  v_line record;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  if p_pool_id is null or p_expected_version is null then
    raise exception 'pool_id and expected_version are required';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'Attendance HPP activation reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'pool_id', p_pool_id,
    'reason', btrim(p_reason),
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_pool
  from erp.attendance_hpp_pools
  where id = p_pool_id
  for update;

  if v_pool.id is null then raise exception 'Attendance HPP pool not found'; end if;
  if v_pool.status <> 'DRAFT' then raise exception 'Only DRAFT attendance HPP pool can be activated'; end if;
  if v_pool.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_pool.row_version;
  end if;
  if v_pool.numerator_amount <= 0 or v_pool.denominator_qty <= 0 then
    raise exception 'Attendance HPP activation requires positive numerator and immutable SELESAI_DIJAHIT denominator';
  end if;

  perform erp._cp3_lock_business_period(v_pool.period_start, v_pool.period_end);
  perform erp._cp3_lock_manifest_contractors(v_pool.period_start, v_pool.period_end);

  if exists (
    select 1 from erp.attendance_hpp_pools p
    where p.id <> v_pool.id
      and p.period_start = v_pool.period_start
      and p.period_end = v_pool.period_end
      and p.status = 'ACTIVE'
  ) then
    raise exception 'Another ACTIVE attendance HPP pool already owns this exact period';
  end if;

  perform erp.validate_attendance_hpp_pool_v1(v_pool.id);

  select coalesce(jsonb_agg(jsonb_build_object(
    'mapping_key', 'WIP',
    'debit', amount,
    'credit', 0,
    'contractor_id', contractor_id,
    'po_id', po_id,
    'description', 'Attendance HPP destination PO ' || po_id::text
  ) order by po_id, contractor_id), '[]'::jsonb)
  into v_lines
  from (
    select po_id, contractor_id, round(sum(allocated_amount),2) amount
    from erp.attendance_hpp_pool_allocations
    where pool_id = v_pool.id
    group by po_id, contractor_id
    having round(sum(allocated_amount),2) > 0
  ) d;

  v_lines := v_lines || coalesce((
    select jsonb_agg(jsonb_build_object(
      'account_id', jl.account_id,
      'debit', 0,
      'credit', round(s.attendance_amount,2),
      'contractor_id', s.contractor_id,
      'description', 'Attendance HPP source debit line ' || s.original_debit_journal_line_id::text
    ) order by s.original_debit_journal_line_id)
    from erp.attendance_hpp_pool_sources s
    join erp.journal_lines jl on jl.id = s.original_debit_journal_line_id
    where s.pool_id = v_pool.id
  ), '[]'::jsonb);

  v_journal_id := erp.post_journal(
    'ATTENDANCE_HPP_POOL', v_pool.id, v_pool.period_end,
    'Allocate normal-Mandor attendance cost by immutable SELESAI_DIJAHIT',
    v_lines
  );

  for v_line in
    select jl.id, jl.po_id, jl.debit
    from erp.journal_lines jl
    where jl.journal_entry_id = v_journal_id
      and jl.debit > 0
      and jl.po_id is not null
  loop
    insert into erp.attendance_hpp_journal_line_links(
      pool_id, journal_line_id, link_type, po_id, amount
    ) values (
      v_pool.id, v_line.id, 'DESTINATION_DEBIT', v_line.po_id, v_line.debit
    );
  end loop;

  for v_line in
    select s.id as pool_source_id, s.original_debit_journal_line_id,
           s.attendance_amount, jl2.id as journal_line_id
    from erp.attendance_hpp_pool_sources s
    join erp.journal_lines jl2
      on jl2.journal_entry_id = v_journal_id
     and jl2.credit = round(s.attendance_amount,2)
     and jl2.description = 'Attendance HPP source debit line ' || s.original_debit_journal_line_id::text
    where s.pool_id = v_pool.id
    order by s.original_debit_journal_line_id
  loop
    insert into erp.attendance_hpp_journal_line_links(
      pool_id, journal_line_id, link_type,
      pool_source_id, original_debit_journal_line_id, amount
    ) values (
      v_pool.id, v_line.journal_line_id, 'SOURCE_CREDIT',
      v_line.pool_source_id, v_line.original_debit_journal_line_id,
      v_line.attendance_amount
    );
  end loop;

  update erp.attendance_hpp_pools
  set status = 'ACTIVE',
      post_journal_entry_id = v_journal_id,
      activated_by = erp.current_app_user_id(),
      activated_at = clock_timestamp(),
      row_version = row_version + 1
  where id = v_pool.id
  returning * into v_pool;

  perform erp.validate_attendance_hpp_pool_v1(v_pool.id);

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'attendance_hpp_pools', v_pool.id, 'POST',
    jsonb_build_object(
      'journal_entry_id', v_journal_id,
      'numerator_amount', v_pool.numerator_amount,
      'denominator_qty', v_pool.denominator_qty,
      'manifest_sha256', v_pool.source_manifest_sha256,
      'lifecycle_action', 'ACTIVATE'
    ),
    erp.current_app_user_id(), btrim(p_reason)
  );

  v_response := jsonb_build_object(
    'pool_id', v_pool.id,
    'status', v_pool.status,
    'row_version', v_pool.row_version,
    'journal_entry_id', v_pool.post_journal_entry_id,
    'validation', 'PASS'
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.cancel_attendance_hpp_pool_v1(
  p_pool_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'cancel_attendance_hpp_pool_v1';
  v_hash text;
  v_cached jsonb;
  v_pool erp.attendance_hpp_pools%rowtype;
  v_reversal_journal_id uuid;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  if p_pool_id is null or p_expected_version is null then
    raise exception 'pool_id and expected_version are required';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'Attendance HPP cancellation reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'pool_id', p_pool_id,
    'reason', btrim(p_reason),
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_pool
  from erp.attendance_hpp_pools
  where id = p_pool_id
  for update;

  if v_pool.id is null then raise exception 'Attendance HPP pool not found'; end if;
  if v_pool.status not in ('DRAFT','ACTIVE') then
    raise exception 'Only DRAFT or ACTIVE attendance HPP pool can be cancelled';
  end if;
  if v_pool.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_pool.row_version;
  end if;

  perform erp._cp3_lock_business_period(v_pool.period_start, v_pool.period_end);

  if v_pool.status = 'DRAFT' then
    update erp.attendance_hpp_pools
    set status = 'VOIDED',
        cancellation_reason = btrim(p_reason),
        cancelled_by = erp.current_app_user_id(),
        cancelled_at = clock_timestamp(),
        row_version = row_version + 1
    where id = v_pool.id
    returning * into v_pool;

    insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
    values (
      'attendance_hpp_pools', v_pool.id, 'UPDATE',
      jsonb_build_object('previous_status','DRAFT','new_status','VOIDED','lifecycle_action','VOID_DRAFT'),
      erp.current_app_user_id(), btrim(p_reason)
    );

    v_response := jsonb_build_object(
      'pool_id', v_pool.id,
      'status', v_pool.status,
      'row_version', v_pool.row_version,
      'reversal_journal_entry_id', null,
      'residue_expected', 0
    );
    return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
  end if;

  if v_pool.post_journal_entry_id is null then
    raise exception 'ACTIVE attendance HPP pool has no source journal; cancellation stopped to avoid residue';
  end if;

  if not exists (
    select 1 from erp.journal_entries je
    where je.id = v_pool.post_journal_entry_id
      and je.status = 'POSTED'
      and je.source_type = 'ATTENDANCE_HPP_POOL'
      and je.source_id = v_pool.id
  ) then
    raise exception 'Pool journal is not an active posted ATTENDANCE_HPP_POOL journal';
  end if;

  v_reversal_journal_id := erp.reverse_journal(v_pool.post_journal_entry_id, btrim(p_reason));

  update erp.attendance_hpp_pools
  set status = 'CANCELLED',
      cancellation_journal_entry_id = v_reversal_journal_id,
      cancellation_reason = btrim(p_reason),
      cancelled_by = erp.current_app_user_id(),
      cancelled_at = clock_timestamp(),
      row_version = row_version + 1
  where id = v_pool.id
  returning * into v_pool;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'attendance_hpp_pools', v_pool.id, 'REVERSE',
    jsonb_build_object(
      'post_journal_entry_id', v_pool.post_journal_entry_id,
      'cancellation_journal_entry_id', v_pool.cancellation_journal_entry_id,
      'previous_status', 'ACTIVE',
      'new_status', 'CANCELLED',
      'lifecycle_action', 'CANCEL_ACTIVE'
    ),
    erp.current_app_user_id(), btrim(p_reason)
  );

  v_response := jsonb_build_object(
    'pool_id', v_pool.id,
    'status', v_pool.status,
    'row_version', v_pool.row_version,
    'reversal_journal_entry_id', v_pool.cancellation_journal_entry_id,
    'residue_expected', 0
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.attendance_hpp_exclusion_summary_v1(
  p_period_start date,
  p_period_end date
)
returns jsonb
language sql
stable
security definer
set search_path = erp, public, pg_temp
as $function$
with payroll_exclusions as (
  select
    ps.id payroll_id,
    ps.contractor_id,
    ps.attendance_total,
    case
      when pol.id is null then 'MISSING_EXPLICIT_POLICY'
      when pol.contractor_role_snapshot <> 'MANDOR' then 'ROLE_NOT_MANDOR'
      when not pol.attendance_required_snapshot then 'ATTENDANCE_NOT_REQUIRED'
      when pol.is_special then 'SPECIAL'
      else null
    end exclusion_reason
  from erp.payroll_settlements ps
  left join lateral (
    select p.*
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id=ps.contractor_id
      and p.effective_from<=p_period_start
      and (p.effective_to is null or p.effective_to>=p_period_end)
    order by p.effective_from desc,p.id desc
    limit 1
  ) pol on true
  where ps.status in ('APPROVED','PAID')
    and ps.period_start=p_period_start
    and ps.period_end=p_period_end
    and ps.attendance_total>0
), sewing_exclusions as (
  select
    e.id sewing_terminal_event_id,
    e.contractor_id,
    e.po_id,
    e.qty_signed sewing_qty,
    erp._cp3_epoch_microseconds(e.physical_at) physical_at_epoch_us,
    case
      when pol.id is null then 'MISSING_EXPLICIT_POLICY'
      when pol.contractor_role_snapshot <> 'MANDOR' then 'ROLE_NOT_MANDOR'
      when not pol.attendance_required_snapshot then 'ATTENDANCE_NOT_REQUIRED'
      when pol.is_special then 'SPECIAL'
      else null
    end exclusion_reason
  from erp.sewing_terminal_events e
  left join lateral (
    select p.*
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id=e.contractor_id
      and p.effective_from<=p_period_start
      and (p.effective_to is null or p.effective_to>=p_period_end)
    order by p.effective_from desc,p.id desc
    limit 1
  ) pol on true
  where e.event_kind='SELESAI_DIJAHIT'
    and erp._cp3_business_date(e.physical_at) between p_period_start and p_period_end
    and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id)
)
select jsonb_build_object(
  'excluded_payrolls',coalesce((
    select jsonb_agg(jsonb_build_object(
      'payroll_id',payroll_id,
      'contractor_id',contractor_id,
      'attendance_amount_cents',round(attendance_total*100)::bigint,
      'reason',exclusion_reason
    ) order by contractor_id,payroll_id)
    from payroll_exclusions where exclusion_reason is not null
  ),'[]'::jsonb),
  'excluded_sewing_events',coalesce((
    select jsonb_agg(jsonb_build_object(
      'sewing_terminal_event_id',sewing_terminal_event_id,
      'contractor_id',contractor_id,
      'po_id',po_id,
      'sewing_qty',sewing_qty,
      'physical_at_epoch_us',physical_at_epoch_us,
      'reason',exclusion_reason
    ) order by physical_at_epoch_us,sewing_terminal_event_id)
    from sewing_exclusions where exclusion_reason is not null
  ),'[]'::jsonb)
)
$function$;

comment on table erp.attendance_hpp_pools is
  'Attendance HPP pool: DRAFT snapshot, ACTIVE posted allocation, CANCELLED reversed allocation, or VOIDED stale draft; lifecycle changes use owning RPCs.';

-- New helpers are private; replacing existing payroll functions preserves their existing ACL.
revoke execute on function erp._cp3_business_date(timestamptz) from public,anon,authenticated,service_role;
revoke execute on function erp._cp3_canonical_date(date) from public,anon,authenticated,service_role;
revoke execute on function erp._cp3_parse_canonical_date(text,text) from public,anon,authenticated,service_role;
revoke execute on function erp._cp3_lock_business_date(date) from public,anon,authenticated,service_role;
revoke execute on function erp._cp3_lock_business_period(date,date) from public,anon,authenticated,service_role;
revoke execute on function erp._cp3_lock_manifest_contractors(date,date) from public,anon,authenticated,service_role;

insert into erp.schema_migrations(version,description,installed_at)
values(
  'v2.6.14c',
  'CP3 R3 UAT alignment: approval-time attendance WIP accrual, settlement-only payment, Asia/Jakarta canonical dates, strict nested JSON types, allowed audit vocabulary, and shared source/pool locks',
  clock_timestamp()
);

commit;
