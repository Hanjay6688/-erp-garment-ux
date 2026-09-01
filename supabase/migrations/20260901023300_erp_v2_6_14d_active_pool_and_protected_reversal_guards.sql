-- ERP Garment v2.6.14d candidate hardening
-- CP3 R4: close active-pool source races, owning work-completion reversal bypass,
-- protected generic journal reversal bypass, and complete strict nested JSON proof.
-- SOURCE-ONLY. DO NOT APPLY TO UAT, MERGE, GRANT, HOOK, OR DEPLOY BEFORE INDEPENDENT AUDIT.
--
-- Invariants preserved:
--   * denominator is immutable explicit SELESAI_DIJAHIT, never QC GOOD;
--   * eligibility is explicit MANDOR + attendance_required=true + is_special=false;
--   * attendance cost is recognized exactly once at APPROVED; PAID is settlement-only;
--   * original payroll debit-line lineage, exact cents, and atomic pool cancellation remain intact.

begin;
set local lock_timeout='10s';
set local statement_timeout='120s';

do $guard$
declare
  v_audit_constraint text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.14a')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.14b')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.14c') then
    raise exception 'ERP v2.6.14d requires source candidates v2.6.14a, v2.6.14b, and v2.6.14c first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.14d') then
    raise exception 'ERP v2.6.14d is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regprocedure('erp.approve_payroll(uuid)') is null
     or to_regprocedure('erp.set_contractor_hpp_policy_v1(jsonb,uuid,uuid)') is null
     or to_regprocedure('erp.reverse_work_completion(uuid,text)') is null
     or to_regprocedure('erp.reverse_journal(uuid,text)') is null
     or to_regprocedure('erp.cancel_unpaid_payroll(uuid,text)') is null
     or to_regprocedure('erp.reverse_paid_payroll(uuid,text)') is null
     or to_regprocedure('erp.cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint)') is null
     or to_regclass('erp.attendance_hpp_pools') is null then
    raise exception 'ERP v2.6.14d target guard: reviewed ERP Enteng CP3 R3 contract is missing';
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
    raise exception 'ERP v2.6.14d target guard: audit action vocabulary differs from reviewed ERP Enteng constraint';
  end if;
end
$guard$;

-- ---------------------------------------------------------------------------
-- 1. Policy changes cannot rewrite the eligibility basis of an ACTIVE pool.
--    Lock ordering intentionally remains: pool activation takes business dates,
--    then contractor locks; policy mutation takes the contractor lock only.
-- ---------------------------------------------------------------------------

create or replace function erp._cp3_assert_policy_change_not_in_active_pool(
  p_contractor_id uuid,
  p_effective_from date,
  p_next_effective_from date
)
returns void
language plpgsql
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_pool_id uuid;
  v_period_start date;
  v_period_end date;
begin
  if p_contractor_id is null or p_effective_from is null then
    raise exception 'CP3 active-pool policy guard requires contractor_id and effective_from';
  end if;
  if p_next_effective_from is not null and p_next_effective_from <= p_effective_from then
    raise exception 'CP3 active-pool policy guard received an invalid effective range';
  end if;

  select hp.id, hp.period_start, hp.period_end
    into v_pool_id, v_period_start, v_period_end
  from erp.attendance_hpp_pools hp
  where hp.status = 'ACTIVE'
    and daterange(hp.period_start, hp.period_end + 1, '[)')
        && daterange(p_effective_from, coalesce(p_next_effective_from, 'infinity'::date), '[)')
    and (
      exists (
        select 1 from erp.attendance_hpp_pool_sources s
        where s.pool_id = hp.id and s.contractor_id = p_contractor_id
      )
      or exists (
        select 1 from erp.attendance_hpp_pool_allocations a
        where a.pool_id = hp.id and a.contractor_id = p_contractor_id
      )
      or exists (
        select 1
        from erp.payroll_settlements ps
        where ps.contractor_id = p_contractor_id
          and ps.status in ('APPROVED','PAID')
          and ps.period_start = hp.period_start
          and ps.period_end = hp.period_end
          and ps.attendance_total > 0
      )
      or exists (
        select 1
        from erp.sewing_terminal_events e
        where e.contractor_id = p_contractor_id
          and e.event_kind = 'SELESAI_DIJAHIT'
          and erp._cp3_business_date(e.physical_at) between hp.period_start and hp.period_end
          and not exists (
            select 1 from erp.sewing_terminal_events rv
            where rv.event_kind = 'REVERSAL' and rv.reversal_of_id = e.id
          )
      )
    )
  order by hp.period_start, hp.period_end, hp.id
  limit 1;

  if v_pool_id is not null then
    raise exception 'ACTIVE_ATTENDANCE_HPP_POOL_BLOCKS_POLICY_CHANGE: pool % owns contractor % for period % through %; cancel the active pool first, change policy, then rebuild the pool',
      v_pool_id, p_contractor_id, erp._cp3_canonical_date(v_period_start), erp._cp3_canonical_date(v_period_end);
  end if;
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

  perform erp._cp3_assert_policy_change_not_in_active_pool(
    v_contractor_id,
    v_effective_from,
    v_next_from
  );

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

-- ---------------------------------------------------------------------------
-- 2. Payroll APPROVED is a source mutation and cannot occur below ACTIVE pool.
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
    select 1
    from erp.attendance_hpp_pools hp
    where hp.status = 'ACTIVE'
      and hp.period_start = p.period_start
      and hp.period_end = p.period_end
  ) then
    raise exception 'ACTIVE_ATTENDANCE_HPP_POOL_BLOCKS_PAYROLL_APPROVAL: cancel the active attendance HPP pool first, then approve payroll and rebuild the pool';
  end if;

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

-- ---------------------------------------------------------------------------
-- 3. Generic journal reversal is compatibility-preserving for unprotected
--    journals, while protected CP3 source types require their owning lifecycle.
-- ---------------------------------------------------------------------------

create or replace function erp._reverse_journal_internal(
  p_journal_entry_id uuid,
  p_reason text
)
returns uuid
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  v_old erp.journal_entries%rowtype;
  v_new_id uuid;
  v_lines jsonb;
begin
  if nullif(btrim(p_reason),'') is null then
    raise exception 'Journal reversal reason is required';
  end if;

  select * into v_old
  from erp.journal_entries
  where id = p_journal_entry_id
  for update;

  if v_old.id is null or v_old.status <> 'POSTED' then
    raise exception 'Only posted journal can be reversed';
  end if;

  select jsonb_agg(jsonb_build_object(
    'account_id', jl.account_id,
    'debit', jl.credit,
    'credit', jl.debit,
    'description', 'Reversal: ' || coalesce(jl.description,''),
    'customer_id', jl.customer_id,
    'vendor_id', jl.vendor_id,
    'contractor_id', jl.contractor_id,
    'po_id', jl.po_id,
    'product_id', jl.product_id
  ) order by jl.id)
  into v_lines
  from erp.journal_lines jl
  where jl.journal_entry_id = p_journal_entry_id;

  if coalesce(jsonb_array_length(v_lines),0) = 0 then
    raise exception 'Posted journal has no lines; reversal stopped';
  end if;

  v_new_id := erp.post_journal(
    'JOURNAL_REVERSAL', p_journal_entry_id, current_date,
    'Reversal: ' || coalesce(v_old.description,'') || ' | ' || btrim(p_reason),
    v_lines
  );
  update erp.journal_entries set status='REVERSED' where id=p_journal_entry_id;
  update erp.journal_entries set reversal_of_id=p_journal_entry_id where id=v_new_id;
  return v_new_id;
end;
$function$;

create or replace function erp.reverse_journal(
  p_journal_entry_id uuid,
  p_reason text
)
returns uuid
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  v_old erp.journal_entries%rowtype;
begin
  perform erp.require_internal();
  if nullif(btrim(p_reason),'') is null then
    raise exception 'Journal reversal reason is required';
  end if;

  select * into v_old
  from erp.journal_entries
  where id = p_journal_entry_id
  for update;

  if v_old.id is null or v_old.status <> 'POSTED' then
    raise exception 'Only posted journal can be reversed';
  end if;
  if v_old.source_type = 'ATTENDANCE_HPP_POOL' then
    raise exception 'PROTECTED_JOURNAL_REQUIRES_OWNING_LIFECYCLE: cancel ATTENDANCE_HPP_POOL through cancel_attendance_hpp_pool_v1()';
  end if;
  if v_old.source_type = 'PAYROLL_ATTENDANCE_ACCRUAL' then
    raise exception 'PROTECTED_JOURNAL_REQUIRES_OWNING_LIFECYCLE: reverse payroll attendance accrual through cancel_unpaid_payroll() or reverse_paid_payroll()';
  end if;

  return erp._reverse_journal_internal(p_journal_entry_id, p_reason);
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
  loop perform erp._reverse_journal_internal(r.id,p_reason); end loop;

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
  loop perform erp._reverse_journal_internal(r.id,p_reason); end loop;

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

  v_reversal_journal_id := erp._reverse_journal_internal(v_pool.post_journal_entry_id, btrim(p_reason));

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

-- ---------------------------------------------------------------------------
-- 4. Work completion reversal cannot orphan an unreversed sewing-terminal fact.
-- ---------------------------------------------------------------------------

create or replace function erp.reverse_work_completion(
  p_completion_id uuid,
  p_reason text
)
returns void
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  h erp.work_completion_events%rowtype;
  v_journal uuid;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then
    raise exception 'Alasan reversal hasil kerja mandor wajib diisi';
  end if;

  select * into h
  from erp.work_completion_events
  where id=p_completion_id
  for update;

  if h.id is null then raise exception 'Transaksi hasil kerja mandor tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya hasil kerja mandor yang sudah POSTED yang dapat direverse'; end if;

  perform erp._cp3_lock_business_date(erp._cp3_business_date(h.physical_at));

  if exists (
    select 1
    from erp.sewing_terminal_events e
    where e.source_work_completion_id = h.id
      and e.event_kind = 'SELESAI_DIJAHIT'
      and not exists (
        select 1
        from erp.sewing_terminal_events rv
        where rv.event_kind = 'REVERSAL'
          and rv.reversal_of_id = e.id
      )
  ) then
    raise exception 'SEWING_TERMINAL_DEPENDENCY: reverse through reverse_sewing_terminal_v1() first; if the sewing event is consumed by an ACTIVE attendance HPP pool, cancel that pool first';
  end if;

  if exists(
    select 1
    from erp.payroll_work_items pwi
    join erp.payroll_settlements ps on ps.id=pwi.payroll_id
    join erp.work_completion_lines wcl on wcl.id=pwi.source_id
    where wcl.completion_id=h.id and pwi.source_type='PRODUCTION' and ps.status<>'REVERSED'
  ) then
    raise exception 'Hasil kerja ini sudah masuk payroll mandor. Cancel atau reverse payroll yang masih aktif terlebih dahulu supaya upah tidak dibayar/dicabut dua kali.';
  end if;

  select id into v_journal
  from erp.journal_entries
  where source_type='WORK_COMPLETION' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;

  if exists(select 1 from erp.work_completion_lines where completion_id=h.id and amount_payable>0) and v_journal is null then
    raise exception 'Jurnal hasil kerja mandor tidak ditemukan; reversal dibatalkan agar hutang upah/HPP tidak rusak';
  end if;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;

  update erp.work_completion_events set status='REVERSED',updated_at=now() where id=h.id;

  if exists(select 1 from erp.fg_lots where po_id=h.po_id) then
    perform erp.rebuild_po_hpp(h.po_id,'Work completion reversed: '||p_reason);
    perform erp.propagate_conversion_hpp_for_po(h.po_id);
    perform erp.sync_po_hpp_to_gl(h.po_id,current_date);
  end if;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('work_completion_events',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

-- New helper/primitive objects are private. Existing public function ACLs are
-- preserved by CREATE OR REPLACE so unprotected journal compatibility remains.
revoke execute on function erp._cp3_assert_policy_change_not_in_active_pool(uuid,date,date)
  from public,anon,authenticated,service_role;
revoke execute on function erp._reverse_journal_internal(uuid,text)
  from public,anon,authenticated,service_role;

insert into erp.schema_migrations(version,description,installed_at)
values(
  'v2.6.14d',
  'CP3 R4 active-pool approval/policy guards, owning work-completion reversal dependency, protected journal reversal lifecycle, and expanded strict nested JSON proof',
  clock_timestamp()
);

commit;
