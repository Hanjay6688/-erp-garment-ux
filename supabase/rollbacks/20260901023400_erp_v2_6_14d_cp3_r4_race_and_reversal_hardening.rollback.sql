-- REVIEWED BYTE-BOUND ROLLBACK FOR ERP v2.6.14d ONLY.
-- Input migration and this file must match docs/evidence/cp3_r4_source_hashes.json.
-- Never run against an environment whose v2.6.14d marker/capsule is absent.

begin;
set local lock_timeout='10s';
set local statement_timeout='120s';

do $rollback_guard$
declare
  v_expected integer;
  v_invalid integer;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.14d') then
    raise exception 'R4 rollback refused: v2.6.14d marker is absent';
  end if;
  if to_regclass('erp.cp3_r4_rollback_capsule') is null then
    raise exception 'R4 rollback refused: exact rollback capsule is absent';
  end if;
  select count(*) into v_expected from erp.cp3_r4_rollback_capsule;
  if v_expected<>7 then
    raise exception 'R4 rollback refused: expected seven exact function definitions, found %',v_expected;
  end if;
  select count(*) into v_invalid
  from erp.cp3_r4_rollback_capsule
  where definition_sha256 is distinct from
        encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex');
  if v_invalid<>0 then
    raise exception 'R4 rollback refused: rollback capsule definition digest mismatch';
  end if;
end
$rollback_guard$;

-- Restore exact pre-14d definitions. Owning functions are restored before the
-- generic journal function; no business function is invoked during this replay.
do $restore_functions$
declare r record;
begin
  for r in
    select function_identity,function_definition
    from erp.cp3_r4_rollback_capsule
    order by case
      when function_identity like 'erp.cancel_attendance_hpp_pool_v1(%' then 10
      when function_identity like 'erp.cancel_unpaid_payroll(%' then 20
      when function_identity like 'erp.reverse_paid_payroll(%' then 30
      when function_identity like 'erp.approve_payroll(%' then 40
      when function_identity like 'erp.set_contractor_hpp_policy_v1(%' then 50
      when function_identity like 'erp.reverse_work_completion(%' then 60
      when function_identity like 'erp.reverse_journal(%' then 70
      else 999 end,
      function_identity
  loop
    execute r.function_definition;
  end loop;
end
$restore_functions$;

drop function if exists erp._cp3_r4_reverse_journal_internal(uuid,text);
drop function if exists erp._cp3_r4_active_pool_affects_contractor(uuid,date,date);

delete from erp.schema_migrations where version='v2.6.14d';
drop table erp.cp3_r4_rollback_capsule;

select pg_notify('pgrst','reload schema');
commit;
