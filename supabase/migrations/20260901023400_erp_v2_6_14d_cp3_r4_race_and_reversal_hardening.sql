-- ERP Garment v2.6.14d candidate hardening
-- CP3 R4: close active-pool races, owning reversal bypasses, and protected journal bypass.
-- SOURCE-ONLY. DO NOT APPLY TO UAT, MERGE, GRANT, HOOK, OR DEPLOY BEFORE INDEPENDENT AUDIT.
--
-- Business invariants retained:
--   * denominator is immutable explicit SELESAI_DIJAHIT, never QC GOOD;
--   * eligibility is explicit MANDOR + attendance_required=true + is_special=false;
--   * attendance cost is recognized once at payroll APPROVED; PAID is settlement-only;
--   * original payroll debit-line lineage and exact-cent reconciliation remain authoritative.

begin;
set local lock_timeout='10s';
set local statement_timeout='120s';

-- ---------------------------------------------------------------------------
-- Exact target and immutable-forward guard
-- ---------------------------------------------------------------------------
do $guard$
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.14c') then
    raise exception 'ERP v2.6.14d requires v2.6.14c first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.14d') then
    raise exception 'ERP v2.6.14d is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regprocedure('erp.approve_payroll(uuid)') is null
     or to_regprocedure('erp.set_contractor_hpp_policy_v1(jsonb,uuid,uuid)') is null
     or to_regprocedure('erp.reverse_work_completion(uuid,text)') is null
     or to_regprocedure('erp.reverse_journal(uuid,text)') is null
     or to_regclass('erp.attendance_hpp_pools') is null
     or to_regclass('erp.attendance_hpp_pool_sources') is null
     or to_regclass('erp.sewing_terminal_events') is null then
    raise exception 'ERP v2.6.14d target guard: exact CP3 R3/UAT contract is missing';
  end if;
  if to_regclass('erp.cp3_r4_rollback_capsule') is not null
     or to_regprocedure('erp._cp3_r4_reverse_journal_internal(uuid,text)') is not null
     or to_regprocedure('erp._cp3_r4_active_pool_affects_contractor(uuid,date,date)') is not null then
    raise exception 'ERP v2.6.14d target guard: prior R4 residue exists';
  end if;
end
$guard$;

-- ---------------------------------------------------------------------------
-- Exact private rollback capsule. This stores only function source/ACL metadata,
-- never business data. It allows the reviewed rollback to restore byte-equivalent
-- pre-14d definitions without guessing which historical migration supplied them.
-- ---------------------------------------------------------------------------
create table erp.cp3_r4_rollback_capsule(
  function_identity text primary key,
  function_definition text not null,
  definition_sha256 text not null,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
revoke all on table erp.cp3_r4_rollback_capsule from public, anon, authenticated, service_role;

insert into erp.cp3_r4_rollback_capsule(
  function_identity,function_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  p.proacl::text[],
  pg_get_userbyid(p.proowner)
from pg_proc p
join pg_namespace n on n.oid=p.pronamespace
where n.nspname='erp'
  and p.proname in (
    'approve_payroll',
    'set_contractor_hpp_policy_v1',
    'reverse_work_completion',
    'reverse_journal',
    'cancel_attendance_hpp_pool_v1',
    'cancel_unpaid_payroll',
    'reverse_paid_payroll'
  );

do $capsule_guard$
declare v_counts jsonb;
begin
  select jsonb_object_agg(proname,cnt) into v_counts
  from (
    select split_part(split_part(function_identity,'.',2),'(',1) proname,count(*) cnt
    from erp.cp3_r4_rollback_capsule group by 1
  ) s;
  if coalesce((v_counts->>'approve_payroll')::int,0)<>1
     or coalesce((v_counts->>'set_contractor_hpp_policy_v1')::int,0)<>1
     or coalesce((v_counts->>'reverse_work_completion')::int,0)<>1
     or coalesce((v_counts->>'reverse_journal')::int,0)<>1
     or coalesce((v_counts->>'cancel_attendance_hpp_pool_v1')::int,0)<>1
     or coalesce((v_counts->>'cancel_unpaid_payroll')::int,0)<>1
     or coalesce((v_counts->>'reverse_paid_payroll')::int,0)<>1 then
    raise exception 'ERP v2.6.14d rollback capsule target cardinality mismatch: %',v_counts;
  end if;
end
$capsule_guard$;

-- ---------------------------------------------------------------------------
-- Private active-pool membership test. It is schema-compatible with the exact
-- restored ERP Enteng source/destination lineage and intentionally checks every
-- pool child table that can identify a contractor.
-- ---------------------------------------------------------------------------
create or replace function erp._cp3_r4_active_pool_affects_contractor(
  p_contractor_id uuid,
  p_effective_from date,
  p_next_effective_from date default null
)
returns boolean
language plpgsql
stable
security invoker
set search_path=erp,public,pg_temp
as $function$
declare
  r record;
  v_sql text;
  v_hit boolean;
  v_join text;
  v_contractor_expr text;
begin
  if p_contractor_id is null or p_effective_from is null then
    raise exception 'R4 active-pool policy overlap requires contractor and effective_from';
  end if;

  for r in
    select c.table_name
    from information_schema.columns c
    where c.table_schema='erp'
      and c.column_name='pool_id'
      and c.table_name like 'attendance_hpp_pool_%'
    group by c.table_name
    order by c.table_name
  loop
    v_join:='';
    v_contractor_expr:=null;

    if exists(select 1 from information_schema.columns c where c.table_schema='erp' and c.table_name=r.table_name and c.column_name='contractor_id') then
      v_contractor_expr:='x.contractor_id';
    elsif exists(select 1 from information_schema.columns c where c.table_schema='erp' and c.table_name=r.table_name and c.column_name='payroll_id') then
      v_join:=' join erp.payroll_settlements ps on ps.id=x.payroll_id ';
      v_contractor_expr:='ps.contractor_id';
    elsif exists(select 1 from information_schema.columns c where c.table_schema='erp' and c.table_name=r.table_name and c.column_name='source_payroll_id') then
      v_join:=' join erp.payroll_settlements ps on ps.id=x.source_payroll_id ';
      v_contractor_expr:='ps.contractor_id';
    elsif exists(select 1 from information_schema.columns c where c.table_schema='erp' and c.table_name=r.table_name and c.column_name='payroll_settlement_id') then
      v_join:=' join erp.payroll_settlements ps on ps.id=x.payroll_settlement_id ';
      v_contractor_expr:='ps.contractor_id';
    elsif exists(select 1 from information_schema.columns c where c.table_schema='erp' and c.table_name=r.table_name and c.column_name='sewing_terminal_event_id') then
      v_join:=' join erp.sewing_terminal_events ste on ste.id=x.sewing_terminal_event_id ';
      v_contractor_expr:='ste.contractor_id';
    elsif exists(select 1 from information_schema.columns c where c.table_schema='erp' and c.table_name=r.table_name and c.column_name='destination_event_id') then
      v_join:=' join erp.sewing_terminal_events ste on ste.id=x.destination_event_id ';
      v_contractor_expr:='ste.contractor_id';
    elsif exists(select 1 from information_schema.columns c where c.table_schema='erp' and c.table_name=r.table_name and c.column_name='source_journal_line_id') then
      v_join:=' join erp.journal_lines jl on jl.id=x.source_journal_line_id join erp.journal_entries je on je.id=jl.journal_entry_id join erp.payroll_settlements ps on ps.id=je.source_id ';
      v_contractor_expr:='ps.contractor_id';
    elsif exists(select 1 from information_schema.columns c where c.table_schema='erp' and c.table_name=r.table_name and c.column_name='original_payroll_debit_journal_line_id') then
      v_join:=' join erp.journal_lines jl on jl.id=x.original_payroll_debit_journal_line_id join erp.journal_entries je on je.id=jl.journal_entry_id join erp.payroll_settlements ps on ps.id=je.source_id ';
      v_contractor_expr:='ps.contractor_id';
    end if;

    if v_contractor_expr is not null then
      v_sql:=format(
        'select exists(select 1 from erp.%I x join erp.attendance_hpp_pools p on p.id=x.pool_id %s where p.status=''ACTIVE'' and p.period_end >= $2 and ($3 is null or p.period_start < $3) and %s=$1)',
        r.table_name,v_join,v_contractor_expr
      );
      execute v_sql into v_hit using p_contractor_id,p_effective_from,p_next_effective_from;
      if v_hit then return true; end if;
    end if;
  end loop;

  return false;
end
$function$;
revoke all on function erp._cp3_r4_active_pool_affects_contractor(uuid,date,date) from public, anon, authenticated, service_role;

-- ---------------------------------------------------------------------------
-- Clone the exact pre-14d journal primitive privately, then keep the established
-- generic RPC compatible for every unprotected source type. Protected CP3 source
-- types can only be reversed by their owning lifecycle functions below.
-- ---------------------------------------------------------------------------
do $clone_reverse$
declare v_def text;
begin
  select function_definition into v_def
  from erp.cp3_r4_rollback_capsule
  where function_identity='erp.reverse_journal(p_journal_entry_id uuid, p_reason text)';
  if v_def is null then raise exception 'R4 reverse_journal capsule definition missing'; end if;
  v_def:=replace(v_def,'FUNCTION erp.reverse_journal','FUNCTION erp._cp3_r4_reverse_journal_internal');
  if v_def not like '%FUNCTION erp._cp3_r4_reverse_journal_internal%' then
    raise exception 'R4 could not create the private journal primitive deterministically';
  end if;
  execute v_def;
end
$clone_reverse$;
revoke all on function erp._cp3_r4_reverse_journal_internal(uuid,text) from public, anon, authenticated, service_role;

create or replace function erp.reverse_journal(p_journal_entry_id uuid,p_reason text)
returns uuid
language plpgsql
security definer
set search_path=erp,public,pg_temp
as $function$
declare v_source_type text;
begin
  perform erp.require_internal();
  if nullif(btrim(p_reason),'') is null then raise exception 'Journal reversal reason is required'; end if;
  select source_type into v_source_type
  from erp.journal_entries where id=p_journal_entry_id for update;
  if v_source_type is null then raise exception 'Journal entry not found'; end if;
  if v_source_type in ('ATTENDANCE_HPP_POOL','PAYROLL_ATTENDANCE_ACCRUAL') then
    raise exception 'Protected journal source type % cannot be reversed through generic reverse_journal. Use the owning attendance HPP pool or payroll cancellation/reversal flow.',v_source_type;
  end if;
  return erp._cp3_r4_reverse_journal_internal(p_journal_entry_id,p_reason);
end
$function$;

-- ---------------------------------------------------------------------------
-- Deterministic source patch helper. Every replacement is cardinality-guarded;
-- a changed target definition aborts instead of silently applying a partial fix.
-- ---------------------------------------------------------------------------
create function pg_temp.cp3_r4_replace_function(
  p_proname text,
  p_old text,
  p_new text,
  p_expected_functions integer,
  p_expected_occurrences_per_function integer
)
returns void
language plpgsql
as $function$
declare r record;v_count integer;v_seen integer:=0;v_new_def text;
begin
  for r in
    select p.oid,pg_get_functiondef(p.oid) def
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='erp' and p.proname=p_proname
    order by p.oid
  loop
    v_seen:=v_seen+1;
    v_count:=(length(r.def)-length(replace(r.def,p_old,'')))/nullif(length(p_old),0);
    if v_count<>p_expected_occurrences_per_function then
      raise exception 'R4 patch % expected % anchor occurrence(s), found %',p_proname,p_expected_occurrences_per_function,v_count;
    end if;
    v_new_def:=replace(r.def,p_old,p_new);
    execute v_new_def;
  end loop;
  if v_seen<>p_expected_functions then
    raise exception 'R4 patch % expected % overload(s), found %',p_proname,p_expected_functions,v_seen;
  end if;
end
$function$;

-- 1. Approval after ACTIVE pool: same period lock, then fail closed.
select pg_temp.cp3_r4_replace_function(
  'approve_payroll',
  'perform erp._cp3_lock_business_period(p.period_start,p.period_end);',
  $patch$perform erp._cp3_lock_business_period(p.period_start,p.period_end);
  if exists(
    select 1 from erp.attendance_hpp_pools hp
    where hp.status='ACTIVE'
      and hp.period_start=p.period_start
      and hp.period_end=p.period_end
  ) then
    raise exception 'Attendance HPP pool for payroll period % through % is already ACTIVE. Cancel the ACTIVE pool first before approving this payroll.',p.period_start,p.period_end;
  end if;$patch$,
  1,1
);

-- 2. Policy change after ACTIVE pool: lock is already held by the R3 setter;
-- check the exact new effective slice after next-version boundary is known.
select pg_temp.cp3_r4_replace_function(
  'set_contractor_hpp_policy_v1',
  $anchor$select min(p.effective_from) into v_next_from
  from erp.contractor_hpp_policy_versions p
  where p.contractor_id = v_contractor_id
    and p.effective_from > v_effective_from;$anchor$,
  $patch$select min(p.effective_from) into v_next_from
  from erp.contractor_hpp_policy_versions p
  where p.contractor_id = v_contractor_id
    and p.effective_from > v_effective_from;

  if erp._cp3_r4_active_pool_affects_contractor(v_contractor_id,v_effective_from,v_next_from) then
    raise exception 'Contractor HPP policy effective from % overlaps an ACTIVE attendance HPP pool. Cancel the ACTIVE pool first, then write the new policy version.',v_effective_from;
  end if;$patch$,
  1,1
);

-- 3. Owning work-completion reversal cannot bypass sewing-terminal lineage.
select pg_temp.cp3_r4_replace_function(
  'reverse_work_completion',
  $anchor$if h.status<>'POSTED' then raise exception 'Hanya hasil kerja mandor yang sudah POSTED yang dapat direverse'; end if;$anchor$,
  $patch$if h.status<>'POSTED' then raise exception 'Hanya hasil kerja mandor yang sudah POSTED yang dapat direverse'; end if;

  perform erp._cp3_lock_business_date(erp._cp3_business_date(h.physical_at));
  if exists(
    select 1
    from erp.sewing_terminal_events e
    where e.source_work_completion_id=h.id
      and e.event_kind='SELESAI_DIJAHIT'
      and not exists(
        select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id
      )
  ) then
    raise exception 'Work completion masih memiliki SELESAI_DIJAHIT aktif. Reverse melalui reverse_sewing_terminal_v1() terlebih dahulu; jika sudah dikonsumsi ACTIVE pool, cancel pool tersebut lebih dulu.';
  end if;$patch$,
  1,1
);

-- 4. Owning protected lifecycles use the private primitive. Existing unrelated
-- reverse_journal call sites remain on the compatibility-safe generic wrapper.
select pg_temp.cp3_r4_replace_function(
  'cancel_attendance_hpp_pool_v1','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,1
);
select pg_temp.cp3_r4_replace_function(
  'cancel_unpaid_payroll','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,1
);
select pg_temp.cp3_r4_replace_function(
  'reverse_paid_payroll','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,1
);

-- Fail closed if a transformed owning function still references the generic RPC.
do $post_patch_guard$
declare v_bad text;
begin
  select string_agg(p.proname,',' order by p.proname) into v_bad
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='erp'
    and p.proname in ('cancel_attendance_hpp_pool_v1','cancel_unpaid_payroll','reverse_paid_payroll')
    and pg_get_functiondef(p.oid) like '%erp.reverse_journal(%';
  if v_bad is not null then raise exception 'R4 protected owning function still calls generic reverse_journal: %',v_bad; end if;

  if not exists(
    select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='erp' and p.proname='approve_payroll'
      and pg_get_functiondef(p.oid) like '%Cancel the ACTIVE pool first before approving this payroll%'
  ) then raise exception 'R4 approve_payroll active-pool guard missing'; end if;
  if not exists(
    select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='erp' and p.proname='set_contractor_hpp_policy_v1'
      and pg_get_functiondef(p.oid) like '%overlaps an ACTIVE attendance HPP pool%'
  ) then raise exception 'R4 policy active-pool guard missing'; end if;
  if not exists(
    select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='erp' and p.proname='reverse_work_completion'
      and pg_get_functiondef(p.oid) like '%reverse_sewing_terminal_v1()%'
  ) then raise exception 'R4 reverse_work_completion sewing dependency guard missing'; end if;
end
$post_patch_guard$;

insert into erp.schema_migrations(version,description)
values('v2.6.14d','CP3 R4 active-pool race, owning reversal, protected journal, and strict-proof hardening');

select pg_notify('pgrst','reload schema');
commit;
