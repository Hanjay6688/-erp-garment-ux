-- ERP Garment v2.6.17a / CP4.5 pattern-assignment integrity correction.
--
-- Forward-only delta for P2-CP45-001. The recorded v2.6.17 migration remains
-- byte-frozen. A Potongan may bind its canonical Pola exactly once, while it
-- is still a pristine CUT draft and before any downstream production fact.
-- Later correction must use a future append-only lifecycle; this migration
-- intentionally exposes no overwrite or unassign path.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $guard$
declare
  v_assign_md5 text;
  v_snapshot_guard_md5 text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.17') then
    raise exception 'ERP v2.6.17a requires the recorded v2.6.17 boundary first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.17a') then
    raise exception 'ERP v2.6.17a is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.cp45_v2617a_rollback_capsule') is not null
     or to_regprocedure('erp.assert_pattern_initial_assignment_allowed(uuid)') is not null then
    raise exception 'ERP v2.6.17a target guard: prior correction residue exists';
  end if;
  if to_regprocedure('erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint)') is null
     or to_regprocedure('erp.guard_pattern_assignment_snapshot()') is null
     or to_regprocedure('public.erp_assign_pattern_v1(uuid,uuid,text,uuid,bigint)') is null
     or to_regclass('erp.production_patterns') is null
     or to_regclass('erp.production_pattern_audit') is null
     or to_regclass('erp.cutting_groups') is null
     or to_regclass('erp.cutting_qty_correction_lines') is null
     or to_regclass('erp.work_completion_events') is null
     or to_regclass('erp.sewing_terminal_events') is null
     or to_regclass('erp.laundry_delivery_lines') is null
     or to_regclass('erp.qc_inspection_items') is null
     or to_regclass('erp.fg_lots') is null
     or to_regclass('erp.bs_cases') is null
     or to_regclass('erp.attendance_hpp_pool_allocations') is null
     or to_regclass('erp.wip_stage_events') is null
     or to_regclass('erp.wip_control_flags') is null
     or to_regclass('erp.scrap_batches') is null then
    raise exception 'ERP v2.6.17a target guard: exact CP4.5/downstream contract is incomplete';
  end if;
  if not exists(
    select 1 from pg_trigger
    where tgrelid='erp.cutting_groups'::regclass
      and tgname='trg_05_pattern_assignment_snapshot'
      and tgfoid='erp.guard_pattern_assignment_snapshot()'::regprocedure
      and tgenabled<>'D'
      and not tgisinternal
  ) then
    raise exception 'ERP v2.6.17a target guard: pattern snapshot trigger is missing or disabled';
  end if;

  select md5(pg_get_functiondef('erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint)'::regprocedure))
    into v_assign_md5;
  select md5(pg_get_functiondef('erp.guard_pattern_assignment_snapshot()'::regprocedure))
    into v_snapshot_guard_md5;
  if v_assign_md5 is distinct from '5d291996e4297426b790e64eef163412'
     or v_snapshot_guard_md5 is distinct from '8da2f40884705902230695dbf85a5fea' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: CP4.5 pattern functions changed (assign %, snapshot %)',
      v_assign_md5,v_snapshot_guard_md5;
  end if;
end
$guard$;

-- Exact pre-correction definitions, ACLs, and owners. No business data is
-- stored here. Rollback can therefore restore the reviewed v2.6.17 boundary
-- without guessing which migration supplied either function.
create table erp.cp45_v2617a_rollback_capsule(
  function_identity text primary key,
  function_definition text not null,
  definition_sha256 text not null,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
revoke all on table erp.cp45_v2617a_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cp45_v2617a_rollback_capsule(
  function_identity,function_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,
  pg_get_userbyid(p.proowner)
from pg_proc p
join pg_namespace n on n.oid=p.pronamespace
where p.oid in (
  'erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint)'::regprocedure,
  'erp.guard_pattern_assignment_snapshot()'::regprocedure
);

do $capsule_guard$
begin
  if (select count(*) from erp.cp45_v2617a_rollback_capsule)<>2
     or exists(
       select 1 from erp.cp45_v2617a_rollback_capsule
       where definition_sha256 is distinct from
         encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex')
     ) then
    raise exception 'ERP v2.6.17a rollback capsule is incomplete or invalid';
  end if;
end
$capsule_guard$;

-- FOR UPDATE is deliberate. It serializes an initial binding with other
-- assignments and with concurrent child FK inserts. Child rows already used
-- to compose the draft (rolls and size slots) are not downstream facts.
create function erp.assert_pattern_initial_assignment_allowed(p_cutting_group_id uuid)
returns void
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_group erp.cutting_groups%rowtype;
begin
  if p_cutting_group_id is null then
    raise exception using errcode='23502',message='CUTTING_GROUP_ID_REQUIRED_FOR_PATTERN_ASSIGNMENT';
  end if;

  select * into v_group
  from erp.cutting_groups
  where id=p_cutting_group_id
  for update;

  if v_group.id is null then
    raise exception using errcode='P0002',message='Potongan not found';
  end if;
  if v_group.pattern_id is not null then
    raise exception using errcode='23514',message='PATTERN_IDENTITY_ALREADY_BOUND';
  end if;
  if v_group.status<>'CUT'
     or v_group.picked_up_at is not null
     or v_group.material_issue_posted
     or v_group.material_return_posted then
    raise exception using errcode='23514',message='PATTERN_INITIAL_ASSIGNMENT_REQUIRES_PRISTINE_CUTTING';
  end if;

  if exists(
       select 1 from erp.production_pattern_audit a
       where a.entity_type='ASSIGNMENT' and a.entity_id=p_cutting_group_id
     )
     or exists(select 1 from erp.cutting_qty_correction_lines x where x.cutting_group_id=p_cutting_group_id)
     or exists(select 1 from erp.work_completion_events x where x.cutting_group_id=p_cutting_group_id)
     or exists(select 1 from erp.sewing_terminal_events x where x.cutting_group_id=p_cutting_group_id)
     or exists(select 1 from erp.laundry_delivery_lines x where x.cutting_group_id=p_cutting_group_id)
     or exists(select 1 from erp.qc_inspection_items x where x.cutting_group_id=p_cutting_group_id)
     or exists(select 1 from erp.fg_lots x where x.cutting_group_id=p_cutting_group_id)
     or exists(select 1 from erp.bs_cases x where x.cutting_group_id=p_cutting_group_id)
     or exists(select 1 from erp.attendance_hpp_pool_allocations x where x.cutting_group_id=p_cutting_group_id)
     or exists(select 1 from erp.wip_stage_events x where x.cutting_group_id=p_cutting_group_id)
     or exists(select 1 from erp.wip_control_flags x where x.cutting_group_id=p_cutting_group_id)
     or exists(select 1 from erp.scrap_batches x where x.source_cutting_group_id=p_cutting_group_id) then
    raise exception using errcode='23514',message='PATTERN_INITIAL_ASSIGNMENT_REQUIRES_PRISTINE_CUTTING';
  end if;
end
$function$;
revoke all on function erp.assert_pattern_initial_assignment_allowed(uuid)
  from public,anon,authenticated,service_role;

create or replace function erp.guard_pattern_assignment_snapshot()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare v_pattern erp.production_patterns%rowtype;
begin
  if tg_op='INSERT' and new.pattern_id is not null
     and (new.status<>'CUT'
       or new.picked_up_at is not null
       or new.material_issue_posted
       or new.material_return_posted) then
    raise exception using errcode='23514',message='PATTERN_INITIAL_ASSIGNMENT_REQUIRES_PRISTINE_CUTTING';
  end if;

  if tg_op='UPDATE' then
    -- Once bound, the identity and every historical display snapshot are
    -- append-only. This also blocks direct unbind and privileged SQL rebind.
    if old.pattern_id is not null then
      if new.pattern_id is distinct from old.pattern_id
         or new.pattern_code_snapshot is distinct from old.pattern_code_snapshot
         or new.pattern_name_snapshot is distinct from old.pattern_name_snapshot
         or new.pattern_revision_snapshot is distinct from old.pattern_revision_snapshot
         or new.pattern_type is distinct from old.pattern_type then
        raise exception using errcode='42501',message='PATTERN_ASSIGNMENT_SNAPSHOT_IMMUTABLE';
      end if;
      return new;
    end if;

    if new.pattern_id is null then
      if new.pattern_code_snapshot is distinct from old.pattern_code_snapshot
         or new.pattern_name_snapshot is distinct from old.pattern_name_snapshot
         or new.pattern_revision_snapshot is distinct from old.pattern_revision_snapshot
         or new.pattern_type is distinct from old.pattern_type then
        raise exception using errcode='42501',message='PATTERN_ASSIGNMENT_SNAPSHOT_IMMUTABLE';
      end if;
      return new;
    end if;

    perform erp.assert_pattern_initial_assignment_allowed(old.id);
  end if;

  if new.pattern_id is null then
    new.pattern_code_snapshot:=null;
    new.pattern_name_snapshot:=null;
    new.pattern_revision_snapshot:=null;
    new.pattern_type:=null;
    return new;
  end if;

  select * into v_pattern
  from erp.production_patterns
  where id=new.pattern_id and is_active;
  if v_pattern.id is null then
    raise exception using errcode='23503',message='ACTIVE_PATTERN_REQUIRED_FOR_NEW_ASSIGNMENT';
  end if;
  new.pattern_code_snapshot:=v_pattern.pattern_code;
  new.pattern_name_snapshot:=v_pattern.pattern_name;
  new.pattern_revision_snapshot:=v_pattern.revision;
  new.pattern_type:=v_pattern.pattern_name;
  return new;
end
$function$;

create or replace function erp.assign_pattern_v1(
  p_cutting_group_id uuid,p_pattern_id uuid,p_reason text,p_client_request_id uuid,p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_group erp.cutting_groups%rowtype;v_pattern erp.production_patterns%rowtype;
  v_hash text;v_cached jsonb;v_response jsonb;v_actor uuid:=erp.current_app_user_id();v_old_snapshot jsonb;
begin
  if not erp.has_permission('production.cutting.edit_draft')
     and not erp.has_permission('production.wip.adjust') then
    raise exception using errcode='42501',message='PERMISSION_DENIED: production pattern assignment';
  end if;
  if nullif(btrim(p_reason),'') is null then raise exception 'reason is required'; end if;
  if p_pattern_id is null then
    raise exception using errcode='23502',message='PATTERN_ID_REQUIRED_FOR_CUTTING_TRANSACTION';
  end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'cutting_group_id',p_cutting_group_id,'pattern_id',p_pattern_id,
    'reason',btrim(p_reason),'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('assign_pattern_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_group
  from erp.cutting_groups
  where id=p_cutting_group_id
  for update;
  if v_group.id is null then raise exception 'Potongan not found'; end if;
  if v_group.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_group.row_version;
  end if;

  perform erp.assert_pattern_initial_assignment_allowed(v_group.id);
  select * into v_pattern from erp.production_patterns where id=p_pattern_id;
  if v_pattern.id is null or not v_pattern.is_active then
    raise exception 'Active pattern is required for new assignment';
  end if;

  v_old_snapshot:=jsonb_build_object(
    'pattern_id',v_group.pattern_id,'code',v_group.pattern_code_snapshot,
    'revision',v_group.pattern_revision_snapshot,'name',v_group.pattern_name_snapshot
  );
  update erp.cutting_groups set pattern_id=p_pattern_id,updated_at=clock_timestamp()
  where id=v_group.id returning * into v_group;
  insert into erp.production_pattern_audit(
    entity_type,entity_id,pattern_id,action,old_data,new_data,change_reason,client_request_id,actor_app_user_id
  ) values(
    'ASSIGNMENT',v_group.id,p_pattern_id,'ASSIGN',
    v_old_snapshot,
    jsonb_build_object(
      'pattern_id',v_group.pattern_id,'code',v_group.pattern_code_snapshot,
      'revision',v_group.pattern_revision_snapshot,'name',v_group.pattern_name_snapshot,
      'pattern_type_snapshot',v_group.pattern_type,'row_version',v_group.row_version
    ),
    btrim(p_reason),p_client_request_id,v_actor
  );
  v_response:=jsonb_build_object(
    'cutting_group_id',v_group.id,'pattern_id',v_group.pattern_id,
    'code_snapshot',v_group.pattern_code_snapshot,'revision_snapshot',v_group.pattern_revision_snapshot,
    'name_snapshot',v_group.pattern_name_snapshot,'pattern_type_snapshot',v_group.pattern_type,
    'row_version',v_group.row_version
  );
  return erp._idempotency_complete('assign_pattern_v1',p_client_request_id,v_response);
end
$function$;

-- CREATE OR REPLACE must preserve the exact reviewed owner and ACL. The new
-- helper remains private even to service_role; callers use the public facade.
revoke all on function erp.assert_pattern_initial_assignment_allowed(uuid)
  from public,anon,authenticated,service_role;

comment on function erp.assert_pattern_initial_assignment_allowed(uuid) is
  'CP4.5 v2.6.17a private initial-only pattern binding guard. Locks the Potongan and rejects every downstream fact; no reassignment lifecycle is exposed.';
comment on function erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint) is
  'CP4.5 v2.6.17a canonical first pattern assignment only. Historical identity correction requires a future append-only lifecycle.';

do $post_guard$
declare
  v_bad text;
  v_helper_def text;
  v_assign_def text;
  v_snapshot_def text;
begin
  select pg_get_functiondef('erp.assert_pattern_initial_assignment_allowed(uuid)'::regprocedure) into v_helper_def;
  select pg_get_functiondef('erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint)'::regprocedure) into v_assign_def;
  select pg_get_functiondef('erp.guard_pattern_assignment_snapshot()'::regprocedure) into v_snapshot_def;

  if lower(v_helper_def) not like '%for update%'
     or v_helper_def not like '%PATTERN_IDENTITY_ALREADY_BOUND%'
     or v_helper_def not like '%PATTERN_INITIAL_ASSIGNMENT_REQUIRES_PRISTINE_CUTTING%'
     or v_assign_def not like '%assert_pattern_initial_assignment_allowed%'
     or v_snapshot_def not like '%old.pattern_id is not null%'
     or v_snapshot_def not like '%assert_pattern_initial_assignment_allowed%'
     or v_snapshot_def not like '%PATTERN_ASSIGNMENT_SNAPSHOT_IMMUTABLE%' then
    raise exception 'ERP v2.6.17a post guard: immutable assignment source is incomplete';
  end if;

  if exists(
    select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where p.oid in (
      'erp.assert_pattern_initial_assignment_allowed(uuid)'::regprocedure,
      'erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint)'::regprocedure,
      'erp.guard_pattern_assignment_snapshot()'::regprocedure
    ) and (
      not p.prosecdef
      or pg_get_functiondef(p.oid) not like '%SET search_path TO ''''%'
      or pg_get_userbyid(p.proowner)<>'postgres'
    )
  ) then
    raise exception 'ERP v2.6.17a post guard: definer/search_path/owner contract failed';
  end if;

  if has_function_privilege('public','erp.assert_pattern_initial_assignment_allowed(uuid)','EXECUTE')
     or has_function_privilege('anon','erp.assert_pattern_initial_assignment_allowed(uuid)','EXECUTE')
     or has_function_privilege('authenticated','erp.assert_pattern_initial_assignment_allowed(uuid)','EXECUTE')
     or has_function_privilege('service_role','erp.assert_pattern_initial_assignment_allowed(uuid)','EXECUTE') then
    raise exception 'ERP v2.6.17a post guard: private helper is executable by an API role';
  end if;

  select string_agg(c.function_identity,',' order by c.function_identity) into v_bad
  from erp.cp45_v2617a_rollback_capsule c
  left join (
    select p.oid,p.proacl,p.proowner,
      format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)) function_identity
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp'
  ) p on p.function_identity=c.function_identity
  where p.oid is null
     or coalesce((
          select array_agg(format('%s:%s:%s:%s',a.grantor,a.grantee,a.privilege_type,a.is_grantable)
            order by a.grantor,a.grantee,a.privilege_type,a.is_grantable)
          from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
        ),array[]::text[])
        is distinct from coalesce((
          select array_agg(format('%s:%s:%s:%s',a.grantor,a.grantee,a.privilege_type,a.is_grantable)
            order by a.grantor,a.grantee,a.privilege_type,a.is_grantable)
          from aclexplode(coalesce(c.acl_snapshot::aclitem[],acldefault('f',p.proowner))) a
        ),array[]::text[])
     or pg_get_userbyid(p.proowner) is distinct from c.owner_snapshot;
  if v_bad is not null then
    raise exception 'ERP v2.6.17a post guard: function ACL/owner drift: %',v_bad;
  end if;

  if not exists(
       select 1 from pg_trigger
       where tgrelid='erp.cutting_groups'::regclass
         and tgname='trg_05_pattern_assignment_snapshot'
         and tgfoid='erp.guard_pattern_assignment_snapshot()'::regprocedure
         and tgenabled<>'D'
         and not tgisinternal
     ) or md5(pg_get_functiondef('erp.require_owner_admin()'::regprocedure))
          is distinct from '965de305e5a381cfdf5588f2b9d4babc' then
    raise exception 'ERP v2.6.17a post guard: trigger or frozen CP4 owner boundary changed';
  end if;
end
$post_guard$;

insert into erp.schema_migrations(version,description)
values('v2.6.17a','CP4.5 initial-only immutable pattern assignment and downstream/race guard');

select pg_notify('pgrst','reload schema');
commit;
