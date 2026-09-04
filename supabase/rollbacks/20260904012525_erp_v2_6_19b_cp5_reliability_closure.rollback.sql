-- REVIEWED PRE-USE ROLLBACK FOR ERP v2.6.19b / CP5 RELIABILITY CLOSURE.
--
-- Refuses to erase any claim, selected-accessory, financial, stock, HPP,
-- idempotency, or audit history created after installation. Exact prior
-- function definitions, ACLs, and owners are restored from the sealed capsule.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $rollback_guard$
declare
  r record;
  v_actual text;
  v_bad text;
  v_installed_at timestamptz;
  v_claim_constraint text;
begin
  select installed_at into v_installed_at
  from erp.schema_migrations where version='v2.6.19b';
  if v_installed_at is null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.19a') then
    raise exception 'v2.6.19b rollback refused: required application markers are absent';
  end if;
  if to_regclass('erp.bs_resolution_v2619b_rollback_capsule') is null
     or (select count(*) from erp.bs_resolution_v2619b_rollback_capsule)<>7 then
    raise exception 'v2.6.19b rollback refused: exact seven-function capsule is missing';
  end if;
  select string_agg(c.function_identity,',' order by c.function_identity) into v_bad
  from erp.bs_resolution_v2619b_rollback_capsule c
  where c.definition_sha256 is distinct from encode(extensions.digest(
          convert_to(c.function_definition,'UTF8'),'sha256'),'hex')
     or c.installed_definition_sha256 is null
     or to_regprocedure(c.function_regprocedure) is null
     or c.installed_definition_sha256 is distinct from encode(extensions.digest(
          convert_to(pg_get_functiondef(to_regprocedure(c.function_regprocedure)),'UTF8'),'sha256'
        ),'hex');
  if v_bad is not null then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.19b function/capsule drift: %',v_bad;
  end if;

  if to_regprocedure('erp.set_rework_accessory_selection_basis_v2619b()') is null
     or to_regprocedure('erp.guard_laundry_claim_delivery_source_v2619b()') is null
     or to_regprocedure('erp.guard_laundry_claim_receipt_source_v2619b()') is null
     or not exists(
       select 1 from information_schema.columns
       where table_schema='erp' and table_name='rework_accessory_selection_lines'
         and column_name='selection_basis' and is_nullable='NO'
     ) then
    raise exception 'v2.6.19b rollback refused: installed runtime contract is incomplete';
  end if;
  select pg_get_constraintdef(oid) into v_claim_constraint
  from pg_constraint where conrelid='erp.laundry_claims'::regclass
    and conname='laundry_claims_claim_type_check';
  if v_claim_constraint is null or v_claim_constraint like '%OTHER%' then
    raise exception 'v2.6.19b rollback refused: installed claim constraint drift';
  end if;

  if exists(select 1 from erp.rework_accessory_selection_lines)
     or exists(select 1 from erp.laundry_claims)
     or exists(
       select 1 from erp.rework_orders where created_at>=v_installed_at
     )
     or exists(
       select 1 from erp.fg_lots where created_at>=v_installed_at
     )
     or exists(
       select 1 from erp.fg_accessory_cost_snapshots where snapshotted_at>=v_installed_at
     )
     or exists(
       select 1 from erp.contractor_accessory_reimbursement_entitlements
       where created_at>=v_installed_at or physical_at>=v_installed_at
     )
     or exists(
       select 1 from erp.idempotency_requests
       where operation_name in(
         'save_laundry_claim_v2','resolve_laundry_claim_v2',
         'save_rework_order_v2','complete_rework_order_v2','save_bs_resolution_action_v1'
       ) and created_at>=v_installed_at
     )
     or exists(
       select 1 from erp.audit_logs
       where changed_at>=v_installed_at and entity_type in(
         'laundry_claims','rework_accessory_decisions',
         'rework_accessory_selection_lines','laundry_deliveries','laundry_receipts'
       )
     ) then
    raise exception 'v2.6.19b rollback refused: post-install business/financial/stock/HPP/audit history exists';
  end if;

  for r in select function_identity,function_regprocedure,installed_definition_sha256
    from erp.bs_resolution_v2619b_rollback_capsule order by function_identity
  loop
    select encode(extensions.digest(
      convert_to(pg_get_functiondef(to_regprocedure(r.function_regprocedure)),'UTF8'),'sha256'
    ),'hex') into v_actual;
    if v_actual is distinct from r.installed_definition_sha256 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: % changed',r.function_identity;
    end if;
  end loop;
end
$rollback_guard$;

-- Local/full-schema installs use the official timestamp. Connector installs
-- may use a generated version, but must match the exact name and source digest.
do $platform_ledger_guard$
declare
  v_match_count integer;
  v_conflict_count integer;
begin
  select count(*) into v_match_count
  from supabase_migrations.schema_migrations m
  where(
    m.version='20260904012525'
    and m.name='erp_v2_6_19b_cp5_reliability_closure'
  ) or(
    m.name='erp_v2_6_19b_cp5_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'')='89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d'
  );
  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where(
    m.version='20260904012525'
    or m.name='erp_v2_6_19b_cp5_reliability_closure'
  ) and not(
    (m.version='20260904012525'
      and m.name='erp_v2_6_19b_cp5_reliability_closure')
    or(
      m.name='erp_v2_6_19b_cp5_reliability_closure'
      and coalesce(encode(extensions.digest(
        convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
      ),'hex'),'')='89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d'
    )
  );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.19b rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_ledger_guard$;

drop trigger trg_guard_laundry_claim_delivery_source_v2619b on erp.laundry_deliveries;
drop trigger trg_guard_laundry_claim_receipt_source_v2619b on erp.laundry_receipts;
drop trigger trg_00_set_rework_accessory_selection_basis_v2619b
  on erp.rework_accessory_selection_lines;
drop function erp.guard_laundry_claim_delivery_source_v2619b();
drop function erp.guard_laundry_claim_receipt_source_v2619b();
drop function erp.set_rework_accessory_selection_basis_v2619b();

alter table erp.laundry_claims drop constraint laundry_claims_claim_type_check;
alter table erp.laundry_claims add constraint laundry_claims_claim_type_check
  check(claim_type in('MISSING','STUCK','DAMAGE','OTHER'));
alter table erp.rework_accessory_selection_lines
  drop constraint rework_accessory_selection_lines_selection_basis_check;
alter table erp.rework_accessory_selection_lines drop column selection_basis;

do $restore_functions$
declare
  r record;
  a record;
  v_grantee text;
begin
  for r in
    select function_identity,function_definition,acl_snapshot,owner_snapshot
    from erp.bs_resolution_v2619b_rollback_capsule
    order by function_identity
  loop
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
          raise exception 'v2.6.19b rollback refused: unsupported function privilege %',a.privilege_type;
        end if;
        v_grantee:=case when a.grantee=0 then 'PUBLIC'
          else format('%I',pg_get_userbyid(a.grantee)) end;
        execute format('grant execute on function %s to %s%s',
          r.function_identity,v_grantee,
          case when a.is_grantable then ' with grant option' else '' end);
      end loop;
    end if;
  end loop;
end
$restore_functions$;

comment on function public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer) is
  'CP5 guarded workspace enriched with authoritative accessory BOM options and immutable per-order choices.';

do $restore_guard$
declare
  v_bad text;
  v_claim_constraint text;
begin
  select string_agg(c.function_identity,',' order by c.function_identity) into v_bad
  from erp.bs_resolution_v2619b_rollback_capsule c
  left join(
    select p.oid,p.proacl,p.proowner,
      format('%I.%I(%s)',n.nspname,p.proname,
        pg_get_function_identity_arguments(p.oid)) function_identity
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  ) p on p.function_identity=c.function_identity
  where p.oid is null
     or encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
        is distinct from c.definition_sha256
     or coalesce((
       select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,
         x.privilege_type,x.is_grantable)
         order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
       from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x
     ),array[]::text[]) is distinct from coalesce((
       select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,
         x.privilege_type,x.is_grantable)
         order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
       from aclexplode(coalesce(c.acl_snapshot::aclitem[],acldefault('f',p.proowner))) x
     ),array[]::text[])
     or pg_get_userbyid(p.proowner) is distinct from c.owner_snapshot;
  if v_bad is not null then
    raise exception 'v2.6.19b rollback exact function/ACL/owner restoration failed: %',v_bad;
  end if;

  select pg_get_constraintdef(oid) into v_claim_constraint
  from pg_constraint where conrelid='erp.laundry_claims'::regclass
    and conname='laundry_claims_claim_type_check';
  if v_claim_constraint is null or v_claim_constraint not like '%OTHER%'
     or exists(
       select 1 from information_schema.columns
       where table_schema='erp' and table_name='rework_accessory_selection_lines'
         and column_name='selection_basis'
     )
     or to_regprocedure('erp.set_rework_accessory_selection_basis_v2619b()') is not null
     or to_regprocedure('erp.guard_laundry_claim_delivery_source_v2619b()') is not null
     or to_regprocedure('erp.guard_laundry_claim_receipt_source_v2619b()') is not null then
    raise exception 'v2.6.19b rollback left reliability-closure residue';
  end if;
end
$restore_guard$;

delete from erp.schema_migrations where version='v2.6.19b';
delete from supabase_migrations.schema_migrations m
where(
  m.version='20260904012525'
  and m.name='erp_v2_6_19b_cp5_reliability_closure'
) or(
  m.name='erp_v2_6_19b_cp5_reliability_closure'
  and coalesce(encode(extensions.digest(
    convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
  ),'hex'),'')='89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d'
);

drop table erp.bs_resolution_v2619b_rollback_capsule;
select pg_notify('pgrst','reload schema');
commit;
