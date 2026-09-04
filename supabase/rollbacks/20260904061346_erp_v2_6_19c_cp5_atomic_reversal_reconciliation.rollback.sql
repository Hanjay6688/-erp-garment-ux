-- REVIEWED PRE-USE ROLLBACK FOR ERP v2.6.19c / CP5 ATOMIC REVERSAL.
-- Refuses post-use rollback and binds the platform row to exact statement bytes.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $rollback_guard$
declare
  r erp.bs_resolution_v2619c_rollback_capsule%rowtype;
  v_installed_at timestamptz;
  v_constraint text;
begin
  select installed_at into v_installed_at
  from erp.schema_migrations where version='v2.6.19c';
  if v_installed_at is null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.19b') then
    raise exception 'v2.6.19c rollback refused: required application markers are absent';
  end if;
  if to_regclass('erp.bs_resolution_v2619c_rollback_capsule') is null
     or (select count(*) from erp.bs_resolution_v2619c_rollback_capsule)<>1 then
    raise exception 'v2.6.19c rollback refused: exact one-function capsule is missing';
  end if;
  select * into r from erp.bs_resolution_v2619c_rollback_capsule;
  if r.definition_sha256 is distinct from encode(extensions.digest(
       convert_to(r.function_definition,'UTF8'),'sha256'
     ),'hex')
     or r.installed_definition_sha256 is null
     or to_regprocedure(r.function_regprocedure) is null
     or r.installed_definition_sha256 is distinct from encode(extensions.digest(
       convert_to(pg_get_functiondef(to_regprocedure(r.function_regprocedure)),'UTF8'),'sha256'
     ),'hex') then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.19c function/capsule drift';
  end if;
  select pg_get_constraintdef(oid,true) into v_constraint
  from pg_constraint
  where conrelid='erp.bs_resolutions'::regclass
    and conname='bs_resolutions_cash_claim_contract_v2619c'
    and convalidated;
  if v_constraint is null
     or to_regprocedure('erp.guard_bs_resolution_claim_state_v2619c()') is null
     or to_regprocedure('erp.guard_laundry_claim_bs_dependency_v2619c()') is null
     or not exists(
       select 1 from pg_trigger
       where tgrelid='erp.bs_resolutions'::regclass
         and tgname='trg_00_guard_bs_resolution_claim_state_v2619c'
         and tgenabled<>'D' and not tgisinternal
     )
     or not exists(
       select 1 from pg_trigger
       where tgrelid='erp.laundry_claims'::regclass
         and tgname='trg_00_guard_laundry_claim_bs_dependency_v2619c'
         and tgenabled<>'D' and not tgisinternal
     ) then
    raise exception 'v2.6.19c rollback refused: installed invariant is incomplete';
  end if;
  if exists(
       select 1 from erp.bs_resolutions
       where resolution_type='CASH_COMPENSATION'
     )
     or exists(
       select 1 from erp.bs_resolutions where created_at>=v_installed_at
     )
     or exists(
       select 1 from erp.idempotency_requests
       where operation_name in(
         'resolve_bs_case_disposition_v2','reverse_bs_disposition_v2',
         'resolve_laundry_claim_v2','save_bs_resolution_action_v1'
       ) and created_at>=v_installed_at
     )
     or exists(
       select 1 from erp.audit_logs
       where changed_at>=v_installed_at
         and entity_type in('laundry_claims','bs_resolutions')
     ) then
    raise exception 'v2.6.19c rollback refused: post-install claim/BS financial or audit history exists';
  end if;
end
$rollback_guard$;

do $platform_ledger_guard$
declare
  v_match_count integer;
  v_conflict_count integer;
begin
  select count(*) into v_match_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_19c_cp5_atomic_reversal_reconciliation'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'')='70bafe4f4c690c6ef1548f712ee2035a78c9137e153c92c69fc57decba58e3cc';

  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where(
    m.version='20260904061346'
    or m.name='erp_v2_6_19c_cp5_atomic_reversal_reconciliation'
  ) and not(
    m.name='erp_v2_6_19c_cp5_atomic_reversal_reconciliation'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'')='70bafe4f4c690c6ef1548f712ee2035a78c9137e153c92c69fc57decba58e3cc'
  );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.19c rollback refused: platform ledger statement digest is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_ledger_guard$;

drop trigger trg_00_guard_bs_resolution_claim_state_v2619c on erp.bs_resolutions;
drop trigger trg_00_guard_laundry_claim_bs_dependency_v2619c on erp.laundry_claims;
alter table erp.bs_resolutions drop constraint bs_resolutions_cash_claim_contract_v2619c;
drop function erp.guard_bs_resolution_claim_state_v2619c();
drop function erp.guard_laundry_claim_bs_dependency_v2619c();

do $restore_function$
declare
  r erp.bs_resolution_v2619c_rollback_capsule%rowtype;
  a record;
  v_grantee text;
begin
  select * into r from erp.bs_resolution_v2619c_rollback_capsule;
  execute r.function_definition;
  execute format('alter function %s owner to %I',r.function_identity,r.owner_snapshot);

  for a in
    select distinct x.grantee
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x
    where format('%I.%I(%s)',n.nspname,p.proname,
      pg_get_function_identity_arguments(p.oid))=r.function_identity
  loop
    v_grantee:=case when a.grantee=0 then 'PUBLIC'
      else format('%I',pg_get_userbyid(a.grantee)) end;
    execute format('revoke all privileges on function %s from %s',
      r.function_identity,v_grantee);
  end loop;

  if r.acl_snapshot is null then
    execute format('grant execute on function %s to PUBLIC',r.function_identity);
  else
    for a in
      select x.* from aclexplode(r.acl_snapshot::aclitem[]) x
      order by x.grantee,x.privilege_type,x.is_grantable
    loop
      if a.privilege_type<>'EXECUTE' then
        raise exception 'v2.6.19c rollback refused: unsupported function privilege %',a.privilege_type;
      end if;
      v_grantee:=case when a.grantee=0 then 'PUBLIC'
        else format('%I',pg_get_userbyid(a.grantee)) end;
      execute format('grant execute on function %s to %s%s',
        r.function_identity,v_grantee,
        case when a.is_grantable then ' with grant option' else '' end);
    end loop;
  end if;
end
$restore_function$;

do $restore_guard$
declare
  r erp.bs_resolution_v2619c_rollback_capsule%rowtype;
begin
  select * into r from erp.bs_resolution_v2619c_rollback_capsule;
  if encode(extensions.digest(
       convert_to(pg_get_functiondef(to_regprocedure(r.function_regprocedure)),'UTF8'),'sha256'
     ),'hex') is distinct from r.definition_sha256
     or to_regprocedure('erp.guard_bs_resolution_claim_state_v2619c()') is not null
     or to_regprocedure('erp.guard_laundry_claim_bs_dependency_v2619c()') is not null
     or exists(
       select 1 from pg_constraint
       where conrelid='erp.bs_resolutions'::regclass
         and conname='bs_resolutions_cash_claim_contract_v2619c'
     )
     or exists(
       select 1 from pg_trigger
       where tgname in(
         'trg_00_guard_bs_resolution_claim_state_v2619c',
         'trg_00_guard_laundry_claim_bs_dependency_v2619c'
       ) and not tgisinternal
     ) then
    raise exception 'v2.6.19c rollback failed exact restoration or left invariant residue';
  end if;
end
$restore_guard$;

delete from erp.schema_migrations where version='v2.6.19c';
delete from supabase_migrations.schema_migrations m
where m.name='erp_v2_6_19c_cp5_atomic_reversal_reconciliation'
  and coalesce(encode(extensions.digest(
    convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
  ),'hex'),'')='70bafe4f4c690c6ef1548f712ee2035a78c9137e153c92c69fc57decba58e3cc';

drop table erp.bs_resolution_v2619c_rollback_capsule;
select pg_notify('pgrst','reload schema');
commit;
