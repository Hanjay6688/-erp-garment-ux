-- ERP Garment v2.6.18 / pre-CP5 Cutting Bridge: persistence, pickup, and WIP continuity.
--
-- This forward-only delta connects the existing Potongan/roll/size/yield model
-- to guarded Data API facades. It adds only the missing pickup/distribution
-- facts; it does not create a shadow cutting or pattern source of truth.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $guard$
declare
  v_save_md5 text;
  v_post_md5 text;
  v_wip_md5 text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.17a') then
    raise exception 'ERP v2.6.18 requires the recorded v2.6.17a boundary first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.18') then
    raise exception 'ERP v2.6.18 is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.cutting_bridge_v2618_rollback_capsule') is not null
     or to_regclass('erp.cutting_pickups') is not null
     or to_regclass('erp.cutting_distribution_batches') is not null
     or to_regclass('erp.cutting_distribution_allocations') is not null
     or to_regprocedure('public.erp_get_cutting_workspace_v1(text,uuid,integer,integer)') is not null
     or to_regprocedure('public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)') is not null
     or to_regprocedure('public.erp_get_cutting_pickup_queue_v1(text,text,integer,integer)') is not null
     or to_regprocedure('public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)') is not null
     or to_regprocedure('public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)') is not null
     or to_regprocedure('erp.get_cutting_workspace_v1(text,uuid,integer,integer)') is not null
     or to_regprocedure('erp.get_cutting_pickup_queue_v1(text,text,integer,integer)') is not null
     or to_regprocedure('erp.get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)') is not null
     or to_regprocedure('erp.save_cutting_pickup_v1(jsonb,uuid,bigint)') is not null
     or to_regprocedure('erp.guard_cutting_source_location()') is not null
     or to_regprocedure('erp.guard_cutting_pickup_lifecycle()') is not null
     or to_regprocedure('erp.guard_cutting_distribution_detail()') is not null
     or to_regclass('erp.idx_material_stock_location_roll') is not null
     or to_regclass('erp.idx_material_rolls_roll_number_lower') is not null then
    raise exception 'ERP v2.6.18 target guard: prior Cutting Bridge residue exists';
  end if;
  if to_regclass('erp.cutting_groups') is null
     or to_regclass('erp.cutting_group_size_slots') is null
     or to_regclass('erp.cutting_group_rolls') is null
     or to_regclass('erp.cutting_roll_yields') is null
     or to_regclass('erp.material_rolls') is null
     or to_regclass('erp.material_stock_movements') is null
     or to_regclass('erp.production_patterns') is null
     or to_regclass('erp.production_orders') is null
     or to_regclass('erp.locations') is null
     or to_regclass('erp.contractors') is null
     or to_regprocedure('erp.has_permission(text)') is null
     or to_regprocedure('erp.require_permission(text)') is null
     or to_regprocedure('erp._idempotency_begin(text,uuid,text)') is null
     or to_regprocedure('erp._idempotency_complete(text,uuid,jsonb)') is null then
    raise exception 'ERP v2.6.18 target guard: required CP4.5/core cutting contract is incomplete';
  end if;
  if exists(
    select 1 from information_schema.columns
    where table_schema='erp' and table_name='cutting_groups' and column_name='source_location_id'
  ) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: cutting_groups.source_location_id already exists';
  end if;

  select md5(pg_get_functiondef('erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)'::regprocedure)) into v_save_md5;
  select md5(pg_get_functiondef('erp.post_cutting_material_issue(uuid,uuid)'::regprocedure)) into v_post_md5;
  select md5(pg_get_functiondef('erp.get_wip_control_v1(text,uuid,text,text)'::regprocedure)) into v_wip_md5;
  if v_save_md5 is distinct from '609cea93ef82bfc12db64b8a363cd2cc'
     or v_post_md5 is distinct from '4fb3ff74878223f225f43a62a8d3abc3'
     or v_wip_md5 is distinct from '39d0d7d26688baecb07084037cc89787' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: cutting function boundary changed (save %, post %, wip %)',
      v_save_md5,v_post_md5,v_wip_md5;
  end if;
end
$guard$;

-- Exact definitions/ACLs/owners for every replaced function and exact ACLs
-- for pre-existing relations hardened by the Cutting Bridge. No business rows are stored.
create table erp.cutting_bridge_v2618_rollback_capsule(
  object_kind text not null check(object_kind in ('FUNCTION','RELATION')),
  object_identity text not null,
  object_definition text,
  definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp(),
  primary key(object_kind,object_identity),
  check(
    (object_kind='FUNCTION' and object_definition is not null and definition_sha256 is not null)
    or (object_kind='RELATION' and object_definition is null and definition_sha256 is null)
  )
);
revoke all on table erp.cutting_bridge_v2618_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cutting_bridge_v2618_rollback_capsule(
  object_kind,object_identity,object_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select
  'FUNCTION',
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,
  pg_get_userbyid(p.proowner)
from pg_proc p
join pg_namespace n on n.oid=p.pronamespace
where p.oid in (
  'erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)'::regprocedure,
  'erp.post_cutting_material_issue(uuid,uuid)'::regprocedure,
  'erp.get_wip_control_v1(text,uuid,text,text)'::regprocedure,
  'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'::regprocedure,
  'erp.sync_material_cost_revaluation(uuid)'::regprocedure,
  'erp.post_journal(text,uuid,date,text,jsonb)'::regprocedure,
  'erp.refresh_accessory_hpp_after_material_recost(uuid,text)'::regprocedure,
  'erp.refresh_material_cost_checkpoint(uuid,date)'::regprocedure
);

insert into erp.cutting_bridge_v2618_rollback_capsule(
  object_kind,object_identity,acl_snapshot,owner_snapshot
)
select
  'RELATION',format('%I.%I',n.nspname,c.relname),
  case when c.relacl is null then null else array(select a::text from unnest(c.relacl) a) end,
  pg_get_userbyid(c.relowner)
from pg_class c
join pg_namespace n on n.oid=c.relnamespace
where c.oid in (
  'erp.cutting_groups'::regclass,
  'erp.cutting_group_size_slots'::regclass,
  'erp.cutting_group_rolls'::regclass,
  'erp.cutting_roll_yields'::regclass,
  'erp.material_rolls'::regclass,
  'erp.material_stock_movements'::regclass,
  'erp.production_orders'::regclass,
  'erp.sizes'::regclass,
  'erp.locations'::regclass
);

do $capsule_guard$
begin
  if (select count(*) from erp.cutting_bridge_v2618_rollback_capsule where object_kind='FUNCTION')<>8
     or (select count(*) from erp.cutting_bridge_v2618_rollback_capsule where object_kind='RELATION')<>9
     or exists(
       select 1 from erp.cutting_bridge_v2618_rollback_capsule
       where object_kind='FUNCTION' and definition_sha256 is distinct from
         encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
     ) then
    raise exception 'ERP v2.6.18 rollback capsule is incomplete or invalid';
  end if;
end
$capsule_guard$;

alter table erp.cutting_groups add column source_location_id uuid;
alter table erp.cutting_groups add constraint cutting_groups_source_location_id_fkey
  foreign key(source_location_id) references erp.locations(id) on delete restrict;
create index idx_cutting_groups_source_location_id
  on erp.cutting_groups(source_location_id) where source_location_id is not null;
create index idx_material_stock_location_roll
  on erp.material_stock_movements(location_id,roll_id,system_created_at,id)
  where roll_id is not null;
create index idx_material_rolls_roll_number_lower
  on erp.material_rolls(lower(roll_number) text_pattern_ops);

create table erp.cutting_pickups(
  id uuid primary key default gen_random_uuid(),
  cutting_group_id uuid not null references erp.cutting_groups(id) on delete restrict,
  contractor_id uuid not null references erp.contractors(id) on delete restrict,
  picked_up_at timestamptz not null,
  allocation_mode text not null check(allocation_mode in ('ROLL','SIZE')),
  status text not null default 'DRAFT' check(status in ('DRAFT','POSTED','REVERSED')),
  notes text,
  created_by uuid not null references erp.app_users(id),
  posted_by uuid references erp.app_users(id),
  posted_at timestamptz,
  reversed_by uuid references erp.app_users(id),
  reversed_at timestamptz,
  reversal_reason text,
  row_version bigint not null default 1 check(row_version>0),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  check(
    (status='DRAFT' and posted_at is null and posted_by is null and reversed_at is null and reversed_by is null and reversal_reason is null)
    or (status='POSTED' and posted_at is not null and posted_by is not null
      and reversed_at is null and reversed_by is null and reversal_reason is null)
    or (status='REVERSED' and posted_at is not null and posted_by is not null
      and reversed_at is not null and reversed_by is not null and reversal_reason is not null)
  )
);
create unique index uq_cutting_pickups_active_group
  on erp.cutting_pickups(cutting_group_id) where status in ('DRAFT','POSTED');
create index idx_cutting_pickups_group_status
  on erp.cutting_pickups(cutting_group_id,status,updated_at desc,id desc);
create index idx_cutting_pickups_contractor
  on erp.cutting_pickups(contractor_id,picked_up_at desc,id desc);

create table erp.cutting_distribution_batches(
  id uuid primary key default gen_random_uuid(),
  pickup_id uuid not null references erp.cutting_pickups(id) on delete cascade,
  batch_no integer not null check(batch_no>0),
  notes text,
  created_at timestamptz not null default clock_timestamp(),
  unique(pickup_id,batch_no)
);
create index idx_cutting_distribution_batches_pickup
  on erp.cutting_distribution_batches(pickup_id,batch_no,id);

create table erp.cutting_distribution_allocations(
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references erp.cutting_distribution_batches(id) on delete cascade,
  cutting_roll_yield_id uuid not null references erp.cutting_roll_yields(id) on delete restrict,
  qty_pcs integer not null check(qty_pcs>0),
  created_at timestamptz not null default clock_timestamp(),
  unique(batch_id,cutting_roll_yield_id)
);
create index idx_cutting_distribution_allocations_batch
  on erp.cutting_distribution_allocations(batch_id,cutting_roll_yield_id);
create index idx_cutting_distribution_allocations_yield
  on erp.cutting_distribution_allocations(cutting_roll_yield_id,batch_id);

alter table erp.cutting_pickups enable row level security;
alter table erp.cutting_distribution_batches enable row level security;
alter table erp.cutting_distribution_allocations enable row level security;
revoke all on table erp.cutting_pickups,erp.cutting_distribution_batches,
  erp.cutting_distribution_allocations from public,anon,authenticated,service_role;

create function erp.guard_cutting_source_location()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
begin
  if new.source_location_id is not null and not exists(
    select 1 from erp.locations l
    where l.id=new.source_location_id and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  ) then
    raise exception using errcode='23514',message='ACTIVE_RAW_MATERIAL_LOCATION_REQUIRED';
  end if;
  if tg_op='UPDATE' and new.source_location_id is distinct from old.source_location_id
     and (old.material_issue_posted or old.picked_up_at is not null
       or old.status<>'CUT' or erp.cutting_group_has_downstream_after_pickup(old.id)) then
    raise exception using errcode='42501',message='CUTTING_SOURCE_LOCATION_IMMUTABLE_AFTER_POST';
  end if;
  return new;
end
$function$;
revoke all on function erp.guard_cutting_source_location() from public,anon,authenticated,service_role;
create trigger trg_07_guard_cutting_source_location
before insert or update of source_location_id on erp.cutting_groups
for each row execute function erp.guard_cutting_source_location();

create function erp.guard_cutting_pickup_lifecycle()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
begin
  if tg_op='DELETE' then
    if old.status<>'DRAFT' then
      raise exception using errcode='42501',message='POSTED_CUTTING_PICKUP_IS_IMMUTABLE';
    end if;
    return old;
  end if;
  if old.status<>'DRAFT' then
    raise exception using errcode='42501',message='POSTED_CUTTING_PICKUP_IS_IMMUTABLE';
  end if;
  if new.status not in ('DRAFT','POSTED') then
    raise exception using errcode='23514',message='INVALID_CUTTING_PICKUP_TRANSITION';
  end if;
  if new.cutting_group_id is distinct from old.cutting_group_id then
    raise exception using errcode='42501',message='CUTTING_PICKUP_SOURCE_IS_IMMUTABLE';
  end if;
  return new;
end
$function$;
revoke all on function erp.guard_cutting_pickup_lifecycle() from public,anon,authenticated,service_role;

create function erp.guard_cutting_distribution_detail()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare v_pickup_id uuid;v_previous_pickup_id uuid;v_status text;
begin
  if tg_table_name='cutting_distribution_batches' then
    v_pickup_id:=case when tg_op='DELETE' then old.pickup_id else new.pickup_id end;
    if tg_op='UPDATE' then v_previous_pickup_id:=old.pickup_id; end if;
  else
    select b.pickup_id into v_pickup_id
    from erp.cutting_distribution_batches b
    where b.id=case when tg_op='DELETE' then old.batch_id else new.batch_id end;
    if tg_op='UPDATE' then
      select b.pickup_id into v_previous_pickup_id
      from erp.cutting_distribution_batches b where b.id=old.batch_id;
    end if;
  end if;
  if tg_op='UPDATE' and v_previous_pickup_id is distinct from v_pickup_id then
    select p.status into v_status from erp.cutting_pickups p where p.id=v_previous_pickup_id for share;
    if v_status is distinct from 'DRAFT' then
      raise exception using errcode='42501',message='POSTED_CUTTING_DISTRIBUTION_IS_IMMUTABLE';
    end if;
  end if;
  select p.status into v_status from erp.cutting_pickups p where p.id=v_pickup_id for share;
  if tg_op='DELETE' and v_status is null
     and current_setting('app.cutting_pickup_delete',true)='on' then
    return old;
  end if;
  if v_status is distinct from 'DRAFT' then
    raise exception using errcode='42501',message='POSTED_CUTTING_DISTRIBUTION_IS_IMMUTABLE';
  end if;
  if tg_op='DELETE' then return old; end if;
  return new;
end
$function$;
revoke all on function erp.guard_cutting_distribution_detail() from public,anon,authenticated,service_role;

create trigger trg_00_guard_cutting_pickup_lifecycle
before update or delete on erp.cutting_pickups
for each row execute function erp.guard_cutting_pickup_lifecycle();
create trigger trg_10_bump_cutting_pickups before update on erp.cutting_pickups
for each row execute function erp.bump_row_version();
create trigger trg_20_touch_cutting_pickups before update on erp.cutting_pickups
for each row execute function erp.touch_updated_at();
create trigger trg_guard_cutting_distribution_batches
before insert or update or delete on erp.cutting_distribution_batches
for each row execute function erp.guard_cutting_distribution_detail();
create trigger trg_guard_cutting_distribution_allocations
before insert or update or delete on erp.cutting_distribution_allocations
for each row execute function erp.guard_cutting_distribution_detail();
create trigger trg_audit_cutting_pickups
after insert or update or delete on erp.cutting_pickups
for each row execute function erp.audit_row_change();
create trigger trg_audit_cutting_distribution_batches
after insert or update or delete on erp.cutting_distribution_batches
for each row execute function erp.audit_row_change();
create trigger trg_audit_cutting_distribution_allocations
after insert or update or delete on erp.cutting_distribution_allocations
for each row execute function erp.audit_row_change();

-- These five helpers are callable only by postgres/service_role (except one
-- stale authenticated ACL removed below). Their legacy role gate prevented a
-- granular custom role from completing an already-authorized cutting post.
-- Remove exactly one obsolete inner gate per byte-guarded definition; the
-- public Cutting Bridge facade remains the permission boundary.
do $private_chain$
declare
  v_identity text;
  v_expected_md5 text;
  v_def text;
  v_needle constant text:='perform erp.require_internal();';
begin
  for v_identity,v_expected_md5 in
    values
      ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','e22579757c48090ea5ea9332fb73ddbf'),
      ('erp.sync_material_cost_revaluation(uuid)','b6719703eb60333169f4f9afd8e7dd35'),
      ('erp.post_journal(text,uuid,date,text,jsonb)','dbf6138ccc575950fc6aed789863af8c'),
      ('erp.refresh_accessory_hpp_after_material_recost(uuid,text)','1fef2342c5d8e89dede7edcb3bef36ed'),
      ('erp.refresh_material_cost_checkpoint(uuid,date)','a2aa967ea4e86adf9ed65d302f4c2918')
  loop
    select pg_get_functiondef(v_identity::regprocedure) into v_def;
    if md5(v_def) is distinct from v_expected_md5
       or (length(lower(v_def))-length(replace(lower(v_def),v_needle,'')))/length(v_needle)<>1 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: private posting chain changed at %',v_identity;
    end if;
    v_def:=regexp_replace(
      v_def,'(?i)perform[[:space:]]+erp[.]require_internal[(][)][;]',
      '/* Cutting Bridge: private EXECUTE ACL + guarded caller own this boundary. */','g'
    );
    execute v_def;
  end loop;
end
$private_chain$;

revoke all on function erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean),
  erp.sync_material_cost_revaluation(uuid),
  erp.post_journal(text,uuid,date,text,jsonb),
  erp.refresh_accessory_hpp_after_material_recost(uuid,text),
  erp.refresh_material_cost_checkpoint(uuid,date)
  from public,anon,authenticated;
revoke all on function erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint),
  erp.post_cutting_material_issue(uuid,uuid) from public,anon,authenticated;

-- The browser reaches existing business tables through permission-checked
-- facades only. service_role retains its pre-existing server-side access.
revoke all on table erp.cutting_groups,erp.cutting_group_size_slots,
  erp.cutting_group_rolls,erp.cutting_roll_yields,erp.material_rolls,
  erp.material_stock_movements,erp.production_orders,erp.sizes,erp.locations
  from public,anon,authenticated;

create function erp.get_cutting_workspace_v1(
  p_roll_query text default null,p_location_id uuid default null,
  p_limit integer default 100,p_offset integer default 0
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare v_query text:=lower(nullif(btrim(p_roll_query),''));
begin
  perform erp.require_permission('production.cutting.view');
  if p_limit is null or p_limit<1 or p_limit>200 then raise exception 'limit must be between 1 and 200'; end if;
  if p_offset is null or p_offset<0 then raise exception 'offset must be nonnegative'; end if;
  if p_location_id is not null and not exists(
    select 1 from erp.locations l where l.id=p_location_id and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  ) then raise exception 'Active raw-material warehouse is required'; end if;

  return jsonb_build_object(
    'roll_query',v_query,'location_id',p_location_id,'limit',p_limit,'offset',p_offset,
    'orders',coalesce((
      select jsonb_agg(jsonb_build_object(
        'id',x.id,'po_number',x.po_number,'model_id',x.model_id,
        'model_code',x.model_code,'model_name',x.model_name,
        'status',x.status,'current_stage',x.current_stage,
        'contractor_id',x.contractor_id,'contractor_name',x.contractor_name
      ) order by x.po_number,x.id)
      from (
        select po.id,po.po_number,po.model_id,m.model_code,m.model_name,
          po.status,po.current_stage,po.contractor_id,c.contractor_name
        from erp.production_orders po
        join erp.product_models m on m.id=po.model_id
        left join erp.contractors c on c.id=po.contractor_id
        where po.status not in ('FINISHED','CANCELLED')
        order by po.po_number,po.id limit 200
      ) x
    ),'[]'::jsonb),
    'sizes',coalesce((
      select jsonb_agg(jsonb_build_object(
          'id',s.id,'code',s.size_code,'sort_order',s.sort_order,
          'model_ids',coalesce((
            select jsonb_agg(pms.model_id order by pms.sort_order,pms.model_id)
            from erp.product_model_sizes pms where pms.size_id=s.id
          ),'[]'::jsonb)
        )
        order by s.sort_order,s.size_code,s.id)
      from erp.sizes s where s.is_active
    ),'[]'::jsonb),
    'locations',coalesce((
      select jsonb_agg(jsonb_build_object('id',l.id,'code',l.location_code,'name',l.location_name)
        order by l.location_code,l.id)
      from erp.locations l where l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
    ),'[]'::jsonb),
    'contractors',coalesce((
      select jsonb_agg(jsonb_build_object('id',c.id,'code',c.contractor_code,'name',c.contractor_name)
        order by c.contractor_name,c.contractor_code,c.id)
      from erp.contractors c where c.is_active and c.contractor_type='MANDOR'
    ),'[]'::jsonb),
    'drafts',coalesce((
      select jsonb_agg(jsonb_build_object(
        'cutting_group_id',x.id,'group_number',x.group_number,'row_version',x.row_version,
        'po_id',x.po_id,'po_number',x.po_number,'model_code',x.model_code,'model_name',x.model_name,
        'cut_at',x.cut_at,'source_location_id',x.source_location_id,'notes',x.notes,
        'pattern_id',x.pattern_id,'pattern_code',x.pattern_code_snapshot,
        'pattern_revision',x.pattern_revision_snapshot,'pattern_name',x.pattern_name_snapshot,
        'pattern_is_active',x.pattern_is_active,'editable',x.editable,
        'size_slots',coalesce((
          select jsonb_agg(jsonb_build_object(
            'slot_no',ss.slot_no,'size_id',ss.size_id,'size_code',sz.size_code,
            'drawing_no',ss.drawing_no,'label_override',ss.label_override
          ) order by ss.slot_no,ss.id)
          from erp.cutting_group_size_slots ss join erp.sizes sz on sz.id=ss.size_id
          where ss.cutting_group_id=x.id
        ),'[]'::jsonb),
        'rolls',coalesce((
          select jsonb_agg(jsonb_build_object(
            'roll_id',r.roll_id,'roll_number',mr.roll_number,'material_id',mr.material_id,
            'material_sku',m.material_sku,'material_name',m.material_name,'unit_code',m.unit_code,
            'supplier_id',mr.supplier_id,'supplier_name',s.supplier_name,
            'original_qty',mr.original_qty,'qty_issued',r.qty_issued,
            'qty_consumed',coalesce(r.qty_consumed,r.qty_issued),
            'qty_reported_remaining',coalesce(r.qty_reported_remaining,greatest(r.qty_issued-coalesce(r.qty_consumed,r.qty_issued),0)),
            'yields',coalesce((
              select jsonb_agg(jsonb_build_object('slot_no',ss.slot_no,'qty_pcs',y.qty_pcs)
                order by ss.slot_no,y.id)
              from erp.cutting_roll_yields y
              join erp.cutting_group_size_slots ss on ss.id=y.size_slot_id
              where y.cutting_group_roll_id=r.id
            ),'[]'::jsonb)
          ) order by m.material_name,mr.roll_number,mr.id)
          from erp.cutting_group_rolls r
          join erp.material_rolls mr on mr.id=r.roll_id
          join erp.materials m on m.id=mr.material_id
          left join erp.suppliers s on s.id=mr.supplier_id
          where r.cutting_group_id=x.id
        ),'[]'::jsonb)
      ) order by x.updated_at desc,x.id desc)
      from (
        select g.*,po.po_number,pm.model_code,pm.model_name,p.is_active pattern_is_active,
          erp.is_cutting_group_presewing_reversible(g.id) editable
        from erp.cutting_groups g
        join erp.production_orders po on po.id=g.po_id
        join erp.product_models pm on pm.id=po.model_id
        left join erp.production_patterns p on p.id=g.pattern_id
        where g.status='CUT' and g.picked_up_at is null and not g.material_issue_posted
        order by g.updated_at desc,g.id desc limit 100
      ) x
    ),'[]'::jsonb),
    'roll_total',case when p_location_id is null then 0 else (
      with stock as (
        select msm.roll_id,sum(msm.qty_signed)::numeric available_qty
        from erp.material_stock_movements msm
        where msm.location_id=p_location_id and msm.roll_id is not null
        group by msm.roll_id having sum(msm.qty_signed)>0
      )
      select count(*) from stock st
      join erp.material_rolls r on r.id=st.roll_id
      join erp.materials m on m.id=r.material_id
      left join erp.suppliers s on s.id=r.supplier_id
      where r.status in ('AVAILABLE','HALF_USED')
        and (v_query is null or lower(concat_ws(' ',r.roll_number,m.material_sku,m.material_name,s.supplier_code,s.supplier_name)) like '%'||v_query||'%')
    ) end,
    'rolls',case when p_location_id is null then '[]'::jsonb else coalesce((
      with stock as (
        select msm.roll_id,sum(msm.qty_signed)::numeric available_qty
        from erp.material_stock_movements msm
        where msm.location_id=p_location_id and msm.roll_id is not null
        group by msm.roll_id having sum(msm.qty_signed)>0
      )
      select jsonb_agg(jsonb_build_object(
        'id',x.id,'roll_number',x.roll_number,'material_id',x.material_id,
        'material_sku',x.material_sku,'material_name',x.material_name,'unit_code',x.unit_code,
        'supplier_id',x.supplier_id,'supplier_code',x.supplier_code,'supplier_name',x.supplier_name,
        'original_qty',x.original_qty,'available_qty',x.available_qty,'status',x.status,
        'received_at',x.received_at
      ) order by x.material_name,x.roll_number,x.id)
      from (
        select r.id,r.roll_number,r.material_id,m.material_sku,m.material_name,m.unit_code,
          r.supplier_id,s.supplier_code,s.supplier_name,r.original_qty,st.available_qty,r.status,r.received_at
        from stock st
        join erp.material_rolls r on r.id=st.roll_id
        join erp.materials m on m.id=r.material_id
        left join erp.suppliers s on s.id=r.supplier_id
        where r.status in ('AVAILABLE','HALF_USED')
          and (v_query is null or lower(concat_ws(' ',r.roll_number,m.material_sku,m.material_name,s.supplier_code,s.supplier_name)) like '%'||v_query||'%')
        order by m.material_name,r.roll_number,r.id limit p_limit offset p_offset
      ) x
    ),'[]'::jsonb) end
  );
end
$function$;

create or replace function erp.post_cutting_material_issue(p_cutting_group_id uuid,p_location_id uuid)
returns void
language plpgsql
security definer
set search_path=''
as $function$
declare
  g erp.cutting_groups%rowtype;
  r record;
  v_available numeric(24,6);
  v_unit_cost numeric(24,6);
  v_total numeric(24,6):=0;
begin
  perform erp.require_permission('production.cutting.post');
  select * into g from erp.cutting_groups where id=p_cutting_group_id for update;
  if g.id is null then raise exception 'Cutting group not found'; end if;
  if g.material_issue_posted then raise exception 'Cutting material issue already posted'; end if;
  if g.pattern_id is null then
    raise exception using errcode='23502',message='PATTERN_ID_REQUIRED_FOR_CUTTING_TRANSACTION';
  end if;
  if g.status<>'CUT' or g.picked_up_at is not null then
    raise exception using errcode='23514',message='CUTTING_POST_REQUIRES_UNPICKED_CUT_DRAFT';
  end if;
  if p_location_id is null or p_location_id is distinct from g.source_location_id then
    raise exception using errcode='23514',message='CUTTING_SOURCE_LOCATION_MISMATCH';
  end if;
  if not exists(
    select 1 from erp.locations l
    where l.id=p_location_id and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  ) then raise exception 'Active raw-material warehouse is required'; end if;
  if not exists(select 1 from erp.cutting_group_rolls x where x.cutting_group_id=g.id) then
    raise exception 'At least one roll is required before posting';
  end if;
  if not exists(
    select 1 from erp.cutting_roll_yields y
    join erp.cutting_group_rolls x on x.id=y.cutting_group_roll_id
    where x.cutting_group_id=g.id and y.qty_pcs>0
  ) then raise exception 'At least one positive cutting yield is required before posting'; end if;

  -- Stable lock order plus the stock trigger's advisory lock makes two posts
  -- against the same physical roll serialize and fail closed on insufficient stock.
  for r in
    select cgr.*,mr.material_id,mr.status as roll_status
    from erp.cutting_group_rolls cgr
    join erp.material_rolls mr on mr.id=cgr.roll_id
    where cgr.cutting_group_id=g.id
    order by mr.id
    for update of mr,cgr
  loop
    perform pg_advisory_xact_lock(hashtextextended(
      'MATSTOCK|'||r.material_id::text||'|'||r.roll_id::text||'|'||p_location_id::text,0
    ));
    select coalesce(sum(msm.qty_signed),0) into v_available
    from erp.material_stock_movements msm
    where msm.material_id=r.material_id and msm.roll_id=r.roll_id and msm.location_id=p_location_id;
    if r.roll_status not in ('AVAILABLE','HALF_USED') or v_available+0.000001<r.qty_issued then
      raise exception using errcode='23514',message=format(
        'INSUFFICIENT_ROLL_STOCK roll %s available %s requested %s',r.roll_id,v_available,r.qty_issued
      );
    end if;

    insert into erp.material_stock_movements(
      material_id,roll_id,location_id,movement_type,qty_signed,
      source_type,source_id,physical_at,created_by
    ) values(
      r.material_id,r.roll_id,p_location_id,'CUTTING_ISSUE',-r.qty_issued,
      'CUTTING_GROUP',g.id,g.cut_at,erp.current_app_user_id()
    );
    perform erp.recalculate_material_cost(r.material_id);
    select msm.unit_cost_snapshot into v_unit_cost
    from erp.material_stock_movements msm
    where msm.source_type='CUTTING_GROUP' and msm.source_id=g.id
      and msm.roll_id=r.roll_id and msm.movement_type='CUTTING_ISSUE'
    order by msm.system_created_at desc,msm.id desc limit 1;
    update erp.cutting_group_rolls set unit_cost_snapshot=v_unit_cost where id=r.id;
    v_total:=v_total+(r.qty_issued*coalesce(v_unit_cost,0));
  end loop;

  update erp.cutting_groups set material_issue_posted=true,updated_at=clock_timestamp()
  where id=g.id;
  if v_total>0 then
    perform erp.post_journal(
      'CUTTING_MATERIAL_ISSUE',g.id,g.cut_at::date,'Material issued to cutting',
      jsonb_build_array(
        jsonb_build_object('mapping_key','WIP','debit',round(v_total,2),'credit',0,'po_id',g.po_id),
        jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',0,'credit',round(v_total,2),'po_id',g.po_id)
      )
    );
  end if;
end
$function$;

create or replace function erp.save_cutting_group_before_sewing_v2(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_action text:=upper(coalesce(nullif(btrim(p_payload->>'action'),''),'SAVE_DRAFT'));
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_po_id uuid:=nullif(p_payload->>'po_id','')::uuid;
  v_pattern_id uuid:=nullif(p_payload->>'pattern_id','')::uuid;
  v_location_id uuid:=nullif(p_payload->>'source_location_id','')::uuid;
  v_cut_at timestamptz:=nullif(p_payload->>'cut_at','')::timestamptz;
  v_group_number text;
  v_group erp.cutting_groups%rowtype;
  v_slot jsonb;
  v_roll jsonb;
  v_yield jsonb;
  v_group_roll_id uuid;
  v_slot_id uuid;
  v_qty numeric;
  v_consumed numeric;
  v_remaining numeric;
  v_roll_yield_total bigint;
  v_available numeric;
begin
  if v_action='SAVE' then v_action:='SAVE_DRAFT'; end if;
  if v_action not in ('SAVE_DRAFT','POST','DELETE') then raise exception 'Invalid cutting action'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if v_id is null then
    perform erp.require_permission('production.cutting.create');
    if p_expected_version is not null then raise exception 'expected_version must be null when creating Potongan'; end if;
  else
    perform erp.require_permission('production.cutting.edit_draft');
    if p_expected_version is null then raise exception 'expected_version is required for existing Potongan'; end if;
  end if;
  if v_action='POST' then perform erp.require_permission('production.cutting.post'); end if;

  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_cutting_group_before_sewing_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is not null then
    select * into v_group from erp.cutting_groups where id=v_id for update;
    if v_group.id is null then raise exception 'Potongan not found'; end if;
    if v_group.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_group.row_version;
    end if;
    if not erp.is_cutting_group_presewing_reversible(v_id) then
      raise exception 'Potongan sudah diposting/dijemput/dipakai downstream; gunakan lifecycle koreksi/reversal';
    end if;
    if v_action='DELETE' then
      delete from erp.cutting_groups where id=v_id;
      v_response:=jsonb_build_object('cutting_group_id',v_id,'status','DELETED');
      return erp._idempotency_complete('save_cutting_group_before_sewing_v2',p_client_request_id,v_response);
    end if;
    if v_group.pattern_id is not null
       and (v_pattern_id is null or v_pattern_id is distinct from v_group.pattern_id) then
      raise exception using errcode='42501',message='PATTERN_ASSIGNMENT_SNAPSHOT_IMMUTABLE';
    end if;
    if v_po_id is null then v_po_id:=v_group.po_id; end if;
    if v_po_id is distinct from v_group.po_id then
      raise exception using errcode='42501',message='CUTTING_PO_IDENTITY_IS_IMMUTABLE';
    end if;
    if v_location_id is null then v_location_id:=v_group.source_location_id; end if;
    if v_cut_at is null then v_cut_at:=v_group.cut_at; end if;
  elsif v_action='DELETE' then
    raise exception 'Potongan id is required for DELETE';
  end if;

  if v_po_id is null or not exists(
    select 1 from erp.production_orders po where po.id=v_po_id and po.status not in ('FINISHED','CANCELLED')
  ) then raise exception 'Active production order is required'; end if;
  if v_pattern_id is null then
    raise exception using errcode='23502',message='PATTERN_ID_REQUIRED_FOR_CUTTING_TRANSACTION';
  end if;
  if v_id is null and not exists(
    select 1 from erp.production_patterns p where p.id=v_pattern_id and p.is_active
  ) then raise exception using errcode='23503',message='ACTIVE_PATTERN_REQUIRED_FOR_NEW_ASSIGNMENT'; end if;
  if v_location_id is null or not exists(
    select 1 from erp.locations l
    where l.id=v_location_id and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  ) then raise exception 'Active source warehouse is required'; end if;
  if v_cut_at is null or v_cut_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'cut_at is required and cannot be in the future';
  end if;
  if jsonb_typeof(p_payload->'size_slots') is distinct from 'array'
     or jsonb_array_length(p_payload->'size_slots')=0 then
    raise exception 'size_slots must be a non-empty array';
  end if;
  if jsonb_typeof(p_payload->'rolls') is distinct from 'array'
     or jsonb_array_length(p_payload->'rolls')=0 then
    raise exception 'rolls must be a non-empty array';
  end if;

  -- Lock every selected physical roll in one deterministic order before a
  -- draft is composed. POST performs an additional advisory stock lock.
  perform 1
  from erp.material_rolls mr
  join jsonb_array_elements(p_payload->'rolls') r
    on mr.id=nullif(r->>'roll_id','')::uuid
  order by mr.id
  for update of mr;
  if (select count(*) from jsonb_array_elements(p_payload->'rolls'))<>
     (select count(distinct nullif(r->>'roll_id','')::uuid) from jsonb_array_elements(p_payload->'rolls') r) then
    raise exception using errcode='23505',message='DUPLICATE_CUTTING_ROLL';
  end if;

  if v_id is null then
    v_id:=gen_random_uuid();
    v_group_number:='POT-'||to_char(v_cut_at at time zone 'UTC','YYMMDD')||'-'||upper(substr(replace(v_id::text,'-',''),1,8));
    insert into erp.cutting_groups(
      id,po_id,group_number,cut_at,status,notes,pattern_id,source_location_id
    ) values(
      v_id,v_po_id,v_group_number,v_cut_at,'CUT',nullif(btrim(p_payload->>'notes'),''),
      v_pattern_id,v_location_id
    ) returning * into v_group;
  else
    update erp.cutting_groups
    set cut_at=v_cut_at,
        pattern_id=case when pattern_id is null then v_pattern_id else pattern_id end,
        source_location_id=v_location_id,
        notes=case when p_payload ? 'notes' then nullif(btrim(p_payload->>'notes'),'') else notes end,
        updated_at=clock_timestamp()
    where id=v_id returning * into v_group;
    delete from erp.cutting_group_rolls where cutting_group_id=v_id;
    delete from erp.cutting_group_size_slots where cutting_group_id=v_id;
  end if;

  for v_slot in select value from jsonb_array_elements(p_payload->'size_slots') loop
    if nullif(v_slot->>'slot_no','')::integer is null
       or (v_slot->>'slot_no')::integer<1
       or nullif(v_slot->>'drawing_no','')::integer is null
       or (v_slot->>'drawing_no')::integer<1
       or not exists(
         select 1
         from erp.sizes s
         join erp.product_model_sizes pms on pms.size_id=s.id
         join erp.production_orders po on po.model_id=pms.model_id
         where s.id=nullif(v_slot->>'size_id','')::uuid and s.is_active and po.id=v_po_id
       ) then raise exception 'Every size slot requires positive slot/drawing numbers and an active size'; end if;
    insert into erp.cutting_group_size_slots(
      cutting_group_id,slot_no,size_id,drawing_no,label_override
    ) values(
      v_id,(v_slot->>'slot_no')::integer,(v_slot->>'size_id')::uuid,
      (v_slot->>'drawing_no')::integer,nullif(btrim(v_slot->>'label_override'),'')
    );
  end loop;

  for v_roll in select value from jsonb_array_elements(p_payload->'rolls') loop
    v_qty:=nullif(v_roll->>'qty_issued','')::numeric;
    v_consumed:=nullif(v_roll->>'qty_consumed','')::numeric;
    v_remaining:=nullif(v_roll->>'qty_reported_remaining','')::numeric;
    if v_qty is null or v_qty<=0 then raise exception 'Every cutting roll requires positive qty_issued'; end if;
    if v_consumed is null or v_consumed<=0 or v_remaining is null or v_remaining<0
       or abs((v_consumed+v_remaining)-v_qty)>0.000001 then
      raise exception using errcode='23514',
        message='CUTTING_ROLL_USAGE_MUST_RECONCILE_ISSUED_CONSUMED_AND_REMAINING';
    end if;
    if jsonb_typeof(v_roll->'yields') is distinct from 'array'
       or jsonb_array_length(v_roll->'yields')=0 then
      raise exception 'Every cutting roll requires a non-empty yields array';
    end if;
    select coalesce(sum(msm.qty_signed),0) into v_available
    from erp.material_stock_movements msm
    where msm.roll_id=nullif(v_roll->>'roll_id','')::uuid and msm.location_id=v_location_id;
    if not exists(
      select 1 from erp.material_rolls mr
      where mr.id=nullif(v_roll->>'roll_id','')::uuid and mr.status in ('AVAILABLE','HALF_USED')
    ) or v_available+0.000001<v_qty then
      raise exception using errcode='23514',message='SELECTED_ROLL_IS_NOT_AVAILABLE_AT_SOURCE_LOCATION';
    end if;
    insert into erp.cutting_group_rolls(
      cutting_group_id,roll_id,qty_issued,qty_consumed,qty_reported_remaining,
      qty_physically_returned,return_destination,notes
    ) values(
      v_id,(v_roll->>'roll_id')::uuid,v_qty,v_consumed,v_remaining,0,'NONE',nullif(btrim(v_roll->>'notes'),'')
    ) returning id into v_group_roll_id;

    v_roll_yield_total:=0;
    for v_yield in select value from jsonb_array_elements(v_roll->'yields') loop
      if nullif(v_yield->>'qty_pcs','')::integer is null or (v_yield->>'qty_pcs')::integer<0 then
        raise exception 'Cutting yield must be a nonnegative integer';
      end if;
      select s.id into v_slot_id from erp.cutting_group_size_slots s
      where s.cutting_group_id=v_id and s.slot_no=nullif(v_yield->>'slot_no','')::integer;
      if v_slot_id is null then raise exception 'Cutting yield references an unknown slot_no'; end if;
      if (v_yield->>'qty_pcs')::integer>0 then
        insert into erp.cutting_roll_yields(cutting_group_roll_id,size_slot_id,qty_pcs)
        values(v_group_roll_id,v_slot_id,(v_yield->>'qty_pcs')::integer);
      end if;
      v_roll_yield_total:=v_roll_yield_total+(v_yield->>'qty_pcs')::integer;
    end loop;
    if v_roll_yield_total<=0 then raise exception 'Every selected roll requires at least one positive cutting yield'; end if;
  end loop;

  update erp.cutting_groups set updated_at=clock_timestamp() where id=v_id returning * into v_group;
  if v_action='POST' then
    perform erp.post_cutting_material_issue(v_id,v_location_id);
    select * into v_group from erp.cutting_groups where id=v_id;
  end if;

  v_response:=jsonb_build_object(
    'cutting_group_id',v_group.id,'group_number',v_group.group_number,
    'status',v_group.status,'row_version',v_group.row_version,
    'pattern_id',v_group.pattern_id,'pattern_code',v_group.pattern_code_snapshot,
    'pattern_revision',v_group.pattern_revision_snapshot,'pattern_name',v_group.pattern_name_snapshot,
    'source_location_id',v_group.source_location_id,
    'material_issue_posted',v_group.material_issue_posted,
    'total_rolls',(select count(*) from erp.cutting_group_rolls x where x.cutting_group_id=v_group.id),
    'total_qty_issued',(select coalesce(sum(x.qty_issued),0) from erp.cutting_group_rolls x where x.cutting_group_id=v_group.id),
    'total_qty_consumed',(select coalesce(sum(x.qty_consumed),0) from erp.cutting_group_rolls x where x.cutting_group_id=v_group.id),
    'total_qty_reported_remaining',(select coalesce(sum(x.qty_reported_remaining),0) from erp.cutting_group_rolls x where x.cutting_group_id=v_group.id),
    'total_pieces',(select coalesce(sum(y.qty_pcs),0) from erp.cutting_roll_yields y
      join erp.cutting_group_rolls x on x.id=y.cutting_group_roll_id where x.cutting_group_id=v_group.id)
  );
  return erp._idempotency_complete('save_cutting_group_before_sewing_v2',p_client_request_id,v_response);
end
$function$;

create function erp.get_cutting_pickup_queue_v1(
  p_filter text default 'WAITING',p_pattern_id uuid default null,p_query text default null,
  p_limit integer default 50,p_offset integer default 0
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare v_filter text:=upper(coalesce(nullif(btrim(p_filter),''),'WAITING'));
  v_query text:=lower(nullif(btrim(p_query),''));
begin
  perform erp.require_permission('production.distribution.view');
  if v_filter not in ('WAITING','PICKED','ALL') then raise exception 'filter must be WAITING, PICKED, or ALL'; end if;
  if p_limit is null or p_limit<1 or p_limit>100 then raise exception 'limit must be between 1 and 100'; end if;
  if p_offset is null or p_offset<0 then raise exception 'offset must be nonnegative'; end if;

  return jsonb_build_object(
    'filter',v_filter,'pattern_id',p_pattern_id,'query',v_query,'limit',p_limit,'offset',p_offset,
    'contractors',coalesce((
      select jsonb_agg(jsonb_build_object('id',c.id,'code',c.contractor_code,'name',c.contractor_name)
        order by c.contractor_name,c.contractor_code,c.id)
      from erp.contractors c where c.is_active and c.contractor_type='MANDOR'
    ),'[]'::jsonb),
    'total',(
      select count(*)
      from erp.cutting_groups g
      join erp.production_orders po on po.id=g.po_id
      join erp.product_models pm on pm.id=po.model_id
      left join erp.contractors pc on pc.id=po.contractor_id
      where g.material_issue_posted
        and (v_filter='ALL'
          or (v_filter='WAITING' and g.status='CUT' and g.picked_up_at is null)
          or (v_filter='PICKED' and g.picked_up_at is not null))
        and (p_pattern_id is null or g.pattern_id=p_pattern_id)
        and (v_query is null or lower(concat_ws(' ',g.group_number,po.po_number,pm.model_code,pm.model_name,
          g.pattern_code_snapshot,g.pattern_revision_snapshot,g.pattern_name_snapshot,g.executor_name,
          pc.contractor_name)) like '%'||v_query||'%')
    ),
    'rows',coalesce((
      select jsonb_agg(jsonb_build_object(
        'cutting_group_id',x.id,'group_number',x.group_number,'row_version',x.row_version,
        'po_id',x.po_id,'po_number',x.po_number,'model_code',x.model_code,'model_name',x.model_name,
        'assigned_contractor_id',x.assigned_contractor_id,
        'assigned_contractor_name',x.assigned_contractor_name,
        'cut_at',x.cut_at,'status',x.status,'picked_up_at',x.picked_up_at,'executor_name',x.executor_name,
        'source_location_id',x.source_location_id,'source_location_code',x.source_location_code,
        'pattern_id',x.pattern_id,'pattern_code',x.pattern_code_snapshot,
        'pattern_revision',x.pattern_revision_snapshot,'pattern_name',x.pattern_name_snapshot,
        'total_qty_issued',x.total_qty_issued,'total_pieces',x.total_pieces,
        'pickup_eligible',x.pickup_eligible,
        'pickup',x.pickup,'rolls',x.rolls
      ) order by x.cut_at,x.group_number,x.id)
      from (
        select g.*,po.po_number,pm.model_code,pm.model_name,
          po.contractor_id as assigned_contractor_id,pc.contractor_name as assigned_contractor_name,
          l.location_code as source_location_code,
          coalesce((select sum(cgr.qty_issued) from erp.cutting_group_rolls cgr where cgr.cutting_group_id=g.id),0) total_qty_issued,
          coalesce((select sum(y.qty_pcs) from erp.cutting_group_rolls cgr join erp.cutting_roll_yields y on y.cutting_group_roll_id=cgr.id where cgr.cutting_group_id=g.id),0) total_pieces,
          (g.pattern_id is not null and g.source_location_id is not null
            and g.material_issue_posted and g.status='CUT' and g.picked_up_at is null
            and not erp.cutting_group_has_downstream_after_pickup(g.id)) pickup_eligible,
          (
            select jsonb_build_object(
              'id',p.id,'contractor_id',p.contractor_id,'contractor_name',c.contractor_name,
              'picked_up_at',p.picked_up_at,'allocation_mode',p.allocation_mode,
              'status',p.status,'notes',p.notes,'row_version',p.row_version,
              'batches',coalesce((
                select jsonb_agg(jsonb_build_object(
                  'id',b.id,'batch_no',b.batch_no,'notes',b.notes,
                  'qty_pcs',coalesce((select sum(a.qty_pcs) from erp.cutting_distribution_allocations a where a.batch_id=b.id),0),
                  'allocations',coalesce((
                    select jsonb_agg(jsonb_build_object(
                      'cutting_roll_yield_id',a.cutting_roll_yield_id,'qty_pcs',a.qty_pcs
                    ) order by a.cutting_roll_yield_id,a.id)
                    from erp.cutting_distribution_allocations a where a.batch_id=b.id
                  ),'[]'::jsonb)
                ) order by b.batch_no,b.id)
                from erp.cutting_distribution_batches b where b.pickup_id=p.id
              ),'[]'::jsonb)
            )
            from erp.cutting_pickups p join erp.contractors c on c.id=p.contractor_id
            where p.cutting_group_id=g.id and p.status in ('DRAFT','POSTED')
            order by p.updated_at desc,p.id desc limit 1
          ) pickup,
          coalesce((
            select jsonb_agg(jsonb_build_object(
              'cutting_group_roll_id',cgr.id,'roll_id',mr.id,'roll_number',mr.roll_number,
              'material_id',m.id,'material_sku',m.material_sku,'material_name',m.material_name,
              'unit_code',m.unit_code,'supplier_name',s.supplier_name,
              'original_qty',mr.original_qty,'qty_issued',cgr.qty_issued,
              'qty_consumed',cgr.qty_consumed,'qty_reported_remaining',cgr.qty_reported_remaining,
              'yields',coalesce((
                select jsonb_agg(jsonb_build_object(
                  'yield_id',y.id,'size_slot_id',ss.id,'slot_no',ss.slot_no,
                  'size_id',sz.id,'size_code',sz.size_code,'drawing_no',ss.drawing_no,
                  'label',coalesce(ss.label_override,case when ss.drawing_no>1 then chr(64+least(ss.drawing_no,26)) else null end),
                  'qty_pcs',y.qty_pcs
                ) order by ss.slot_no,y.id)
                from erp.cutting_roll_yields y
                join erp.cutting_group_size_slots ss on ss.id=y.size_slot_id
                join erp.sizes sz on sz.id=ss.size_id
                where y.cutting_group_roll_id=cgr.id
              ),'[]'::jsonb)
            ) order by m.material_name,mr.roll_number,mr.id)
            from erp.cutting_group_rolls cgr
            join erp.material_rolls mr on mr.id=cgr.roll_id
            join erp.materials m on m.id=mr.material_id
            left join erp.suppliers s on s.id=mr.supplier_id
            where cgr.cutting_group_id=g.id
          ),'[]'::jsonb) rolls
        from erp.cutting_groups g
        join erp.production_orders po on po.id=g.po_id
        join erp.product_models pm on pm.id=po.model_id
        left join erp.contractors pc on pc.id=po.contractor_id
        left join erp.locations l on l.id=g.source_location_id
        where g.material_issue_posted
          and (v_filter='ALL'
            or (v_filter='WAITING' and g.status='CUT' and g.picked_up_at is null)
            or (v_filter='PICKED' and g.picked_up_at is not null))
          and (p_pattern_id is null or g.pattern_id=p_pattern_id)
          and (v_query is null or lower(concat_ws(' ',g.group_number,po.po_number,pm.model_code,pm.model_name,
          g.pattern_code_snapshot,g.pattern_revision_snapshot,g.pattern_name_snapshot,g.executor_name,
          pc.contractor_name)) like '%'||v_query||'%')
        order by g.cut_at,g.group_number,g.id limit p_limit offset p_offset
      ) x
    ),'[]'::jsonb)
  );
end
$function$;

create function erp.save_cutting_pickup_v1(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_group_id uuid:=nullif(p_payload->>'cutting_group_id','')::uuid;
  v_contractor_id uuid:=nullif(p_payload->>'contractor_id','')::uuid;
  v_picked_up_at timestamptz:=nullif(p_payload->>'picked_up_at','')::timestamptz;
  v_mode text:=upper(coalesce(nullif(btrim(p_payload->>'allocation_mode'),''),'ROLL'));
  v_action text:=upper(coalesce(nullif(btrim(p_payload->>'action'),''),'SAVE_DRAFT'));
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_expected_group_version bigint:=nullif(p_payload->>'expected_group_version','')::bigint;
  v_hash text;v_cached jsonb;v_response jsonb;
  v_pickup erp.cutting_pickups%rowtype;
  v_group erp.cutting_groups%rowtype;
  v_batch jsonb;v_allocation jsonb;v_batch_id uuid;
  v_actor uuid:=erp.current_app_user_id();
  v_po_contractor_id uuid;
  v_batch_count integer;v_max_batch integer;
begin
  if v_action='SAVE' then v_action:='SAVE_DRAFT'; end if;
  if v_action not in ('SAVE_DRAFT','POST','DELETE') then raise exception 'Invalid pickup action'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if v_id is null then
    perform erp.require_permission('production.distribution.create');
    if p_expected_version is not null then raise exception 'expected_version must be null when creating pickup'; end if;
  else
    perform erp.require_permission('production.distribution.edit_draft');
    if p_expected_version is null then raise exception 'expected_version is required for an existing pickup'; end if;
  end if;
  if v_action='POST' then perform erp.require_permission('production.distribution.post'); end if;
  if v_expected_group_version is null then raise exception 'expected_group_version is required'; end if;

  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_cutting_pickup_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is not null then
    select * into v_pickup from erp.cutting_pickups where id=v_id for update;
    if v_pickup.id is null then raise exception 'Cutting pickup not found'; end if;
    if v_pickup.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_pickup.row_version;
    end if;
    if v_pickup.status<>'DRAFT' then
      raise exception using errcode='42501',message='POSTED_CUTTING_PICKUP_IS_IMMUTABLE';
    end if;
    if v_group_id is null then v_group_id:=v_pickup.cutting_group_id; end if;
    if v_group_id is distinct from v_pickup.cutting_group_id then
      raise exception using errcode='42501',message='CUTTING_PICKUP_SOURCE_IS_IMMUTABLE';
    end if;
    if v_action='DELETE' then
      select * into v_group from erp.cutting_groups where id=v_group_id for update;
      if v_group.row_version<>v_expected_group_version then
        raise exception 'STALE_GROUP_VERSION expected %, current %',v_expected_group_version,v_group.row_version;
      end if;
      perform set_config('app.cutting_pickup_delete','on',true);
      delete from erp.cutting_pickups where id=v_pickup.id;
      v_response:=jsonb_build_object(
        'pickup_id',v_pickup.id,'cutting_group_id',v_group.id,'status','DELETED',
        'row_version',v_pickup.row_version,'group_row_version',v_group.row_version,
        'picked_up_at',v_pickup.picked_up_at,'contractor_id',v_pickup.contractor_id,
        'allocation_mode',v_pickup.allocation_mode,'batch_count',0,'allocated_pieces',0
      );
      return erp._idempotency_complete('save_cutting_pickup_v1',p_client_request_id,v_response);
    end if;
  elsif v_action='DELETE' then
    raise exception 'pickup id is required for DELETE';
  end if;

  select * into v_group from erp.cutting_groups where id=v_group_id for update;
  if v_group.id is null then raise exception 'Potongan not found'; end if;
  if v_group.row_version<>v_expected_group_version then
    raise exception 'STALE_GROUP_VERSION expected %, current %',v_expected_group_version,v_group.row_version;
  end if;
  if not v_group.material_issue_posted or v_group.pattern_id is null
     or v_group.source_location_id is null then
    raise exception using errcode='23514',message='PICKUP_REQUIRES_POSTED_PATTERN_BOUND_CUTTING';
  end if;
  if v_group.status<>'CUT' or v_group.picked_up_at is not null
     or erp.cutting_group_has_downstream_after_pickup(v_group.id) then
    raise exception using errcode='23514',message='PICKUP_REQUIRES_WAITING_CUTTING_WITHOUT_DOWNSTREAM';
  end if;
  if v_contractor_id is null or not exists(
    select 1 from erp.contractors c
    where c.id=v_contractor_id and c.is_active and c.contractor_type='MANDOR'
  ) then raise exception 'Active Mandor is required'; end if;
  if v_picked_up_at is null or v_picked_up_at<v_group.cut_at
     or v_picked_up_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'picked_up_at must be between cut_at and now';
  end if;
  if v_mode not in ('ROLL','SIZE') then raise exception 'allocation_mode must be ROLL or SIZE'; end if;
  if jsonb_typeof(p_payload->'batches') is distinct from 'array'
     or jsonb_array_length(p_payload->'batches')=0 then
    raise exception 'batches must be a non-empty array';
  end if;

  -- The existing downstream cost/payroll model owns Mandor at PO level.
  -- Lock that identity before composing a pickup, and never silently move an
  -- already assigned PO to another Mandor.
  select po.contractor_id into v_po_contractor_id
  from erp.production_orders po where po.id=v_group.po_id for update;
  if v_po_contractor_id is not null
     and v_po_contractor_id is distinct from v_contractor_id then
    raise exception using errcode='23514',message='PO_ALREADY_ASSIGNED_TO_DIFFERENT_MANDOR';
  end if;

  if v_id is null then
    insert into erp.cutting_pickups(
      cutting_group_id,contractor_id,picked_up_at,allocation_mode,status,notes,created_by
    ) values(
      v_group.id,v_contractor_id,v_picked_up_at,v_mode,'DRAFT',nullif(btrim(p_payload->>'notes'),''),v_actor
    ) returning * into v_pickup;
    v_id:=v_pickup.id;
  else
    update erp.cutting_pickups
    set contractor_id=v_contractor_id,picked_up_at=v_picked_up_at,allocation_mode=v_mode,
        notes=case when p_payload ? 'notes' then nullif(btrim(p_payload->>'notes'),'') else notes end,
        updated_at=clock_timestamp()
    where id=v_id returning * into v_pickup;
    -- Delete allocations while their draft parent batch is still visible.
    -- Relying on the FK cascade hides the deleting batch from the child guard,
    -- which correctly fails closed because it can no longer prove DRAFT state.
    delete from erp.cutting_distribution_allocations a
    using erp.cutting_distribution_batches b
    where a.batch_id=b.id and b.pickup_id=v_id;
    delete from erp.cutting_distribution_batches where pickup_id=v_id;
  end if;

  for v_batch in select value from jsonb_array_elements(p_payload->'batches') loop
    if nullif(v_batch->>'batch_no','')::integer is null or (v_batch->>'batch_no')::integer<1 then
      raise exception 'Every distribution batch requires a positive batch_no';
    end if;
    if jsonb_typeof(v_batch->'allocations') is distinct from 'array' then
      raise exception 'Every distribution batch requires an allocations array';
    end if;
    insert into erp.cutting_distribution_batches(pickup_id,batch_no,notes)
    values(v_id,(v_batch->>'batch_no')::integer,nullif(btrim(v_batch->>'notes'),''))
    returning id into v_batch_id;
    for v_allocation in select value from jsonb_array_elements(v_batch->'allocations') loop
      if nullif(v_allocation->>'qty_pcs','')::integer is null or (v_allocation->>'qty_pcs')::integer<=0 then
        raise exception 'Every distribution allocation requires positive qty_pcs';
      end if;
      if not exists(
        select 1
        from erp.cutting_roll_yields y
        join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
        where y.id=nullif(v_allocation->>'cutting_roll_yield_id','')::uuid
          and r.cutting_group_id=v_group.id
      ) then raise exception 'Distribution allocation references a yield outside this Potongan'; end if;
      insert into erp.cutting_distribution_allocations(batch_id,cutting_roll_yield_id,qty_pcs)
      values(v_batch_id,(v_allocation->>'cutting_roll_yield_id')::uuid,(v_allocation->>'qty_pcs')::integer);
    end loop;
  end loop;

  select count(*),max(batch_no) into v_batch_count,v_max_batch
  from erp.cutting_distribution_batches where pickup_id=v_id;
  if v_batch_count<1 or v_max_batch<>v_batch_count or exists(
    select 1 from generate_series(1,v_batch_count) expected(batch_no)
    where not exists(
      select 1 from erp.cutting_distribution_batches b
      where b.pickup_id=v_id and b.batch_no=expected.batch_no
    )
  ) then raise exception using errcode='23514',message='DISTRIBUTION_BATCH_NUMBERS_MUST_BE_CONTIGUOUS_FROM_ONE'; end if;
  if exists(
    select 1
    from erp.cutting_roll_yields y
    join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
    left join (
      select a.cutting_roll_yield_id,sum(a.qty_pcs)::bigint allocated
      from erp.cutting_distribution_allocations a
      join erp.cutting_distribution_batches b on b.id=a.batch_id
      where b.pickup_id=v_id group by a.cutting_roll_yield_id
    ) z on z.cutting_roll_yield_id=y.id
    where r.cutting_group_id=v_group.id and coalesce(z.allocated,0)>y.qty_pcs
  ) then raise exception using errcode='23514',message='DISTRIBUTION_EXCEEDS_CUTTING_SOURCE'; end if;

  if v_action='POST' then
    if exists(
      select 1
      from erp.cutting_roll_yields y
      join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
      left join (
        select a.cutting_roll_yield_id,sum(a.qty_pcs)::bigint allocated
        from erp.cutting_distribution_allocations a
        join erp.cutting_distribution_batches b on b.id=a.batch_id
        where b.pickup_id=v_id group by a.cutting_roll_yield_id
      ) z on z.cutting_roll_yield_id=y.id
      where r.cutting_group_id=v_group.id and coalesce(z.allocated,0)<>y.qty_pcs
    ) or exists(
      select 1 from erp.cutting_distribution_batches b
      where b.pickup_id=v_id and not exists(
        select 1 from erp.cutting_distribution_allocations a where a.batch_id=b.id
      )
    ) then raise exception using errcode='23514',message='POSTED_DISTRIBUTION_MUST_EXACTLY_RECONCILE_EVERY_SOURCE_YIELD'; end if;

    update erp.production_orders
    set contractor_id=coalesce(contractor_id,v_contractor_id),
        status=case when status in ('DRAFT','CUTTING') then 'SEWING' else status end,
        current_stage=case when current_stage='CUTTING' then 'SEWING' else current_stage end,
        updated_at=clock_timestamp()
    where id=v_group.po_id;
    update erp.cutting_pickups
    set status='POSTED',posted_by=v_actor,posted_at=clock_timestamp(),updated_at=clock_timestamp()
    where id=v_id returning * into v_pickup;
    update erp.cutting_groups
    set executor_name=(select c.contractor_name from erp.contractors c where c.id=v_contractor_id),
        picked_up_at=v_picked_up_at,status='PICKED_UP',updated_at=clock_timestamp()
    where id=v_group.id returning * into v_group;
    insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
    values('cutting_pickups',v_pickup.id,'POST',jsonb_build_object(
      'cutting_group_id',v_group.id,'contractor_id',v_contractor_id,
      'picked_up_at',v_picked_up_at,'allocation_mode',v_mode,'batch_count',v_batch_count
    ),v_actor,v_reason);
  else
    select * into v_pickup from erp.cutting_pickups where id=v_id;
  end if;

  v_response:=jsonb_build_object(
    'pickup_id',v_pickup.id,'cutting_group_id',v_group.id,'status',v_pickup.status,
    'row_version',v_pickup.row_version,'group_row_version',v_group.row_version,
    'picked_up_at',v_pickup.picked_up_at,'contractor_id',v_pickup.contractor_id,
    'allocation_mode',v_pickup.allocation_mode,'batch_count',v_batch_count,
    'allocated_pieces',(
      select coalesce(sum(a.qty_pcs),0)
      from erp.cutting_distribution_allocations a
      join erp.cutting_distribution_batches b on b.id=a.batch_id where b.pickup_id=v_pickup.id
    )
  );
  return erp._idempotency_complete('save_cutting_pickup_v1',p_client_request_id,v_response);
end
$function$;

create or replace function erp.get_wip_control_v1(
  p_filter text default 'ACTIVE',p_pattern_id uuid default null,
  p_sort text default 'PATTERN',p_query text default null
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare v_filter text:=upper(coalesce(nullif(btrim(p_filter),''),'ACTIVE'));
  v_sort text:=upper(coalesce(nullif(btrim(p_sort),''),'PATTERN'));
  v_query text:=lower(nullif(btrim(p_query),''));
begin
  perform erp.require_permission('production.wip.view');
  if v_filter not in ('ACTIVE','COMPLETED','ALL') then raise exception 'filter must be ACTIVE, COMPLETED, or ALL'; end if;
  if v_sort not in ('PATTERN','PRODUCTION','UPDATED') then raise exception 'sort must be PATTERN, PRODUCTION, or UPDATED'; end if;
  return jsonb_build_object(
    'filter',v_filter,'sort',v_sort,'pattern_id',p_pattern_id,
    'rows',coalesce((
      select jsonb_agg(
        to_jsonb(w)||jsonb_build_object(
          'distribution',(
            select jsonb_build_object(
              'pickup_id',p.id,'contractor_id',p.contractor_id,'contractor_name',c.contractor_name,
              'picked_up_at',p.picked_up_at,'allocation_mode',p.allocation_mode,
              'batches',coalesce((
                select jsonb_agg(jsonb_build_object(
                  'id',b.id,'batch_no',b.batch_no,'notes',b.notes,
                  'qty_pcs',coalesce((select sum(a.qty_pcs) from erp.cutting_distribution_allocations a where a.batch_id=b.id),0),
                  'sizes',coalesce((
                    select jsonb_agg(jsonb_build_object('size_code',z.size_code,'qty_pcs',z.qty_pcs)
                      order by z.sort_order,z.size_code)
                    from (
                      select sz.size_code,sz.sort_order,sum(a.qty_pcs)::bigint qty_pcs
                      from erp.cutting_distribution_allocations a
                      join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
                      join erp.cutting_group_size_slots ss on ss.id=y.size_slot_id
                      join erp.sizes sz on sz.id=ss.size_id
                      where a.batch_id=b.id group by sz.id,sz.size_code,sz.sort_order
                    ) z
                  ),'[]'::jsonb)
                ) order by b.batch_no,b.id)
                from erp.cutting_distribution_batches b where b.pickup_id=p.id
              ),'[]'::jsonb)
            )
            from erp.cutting_pickups p join erp.contractors c on c.id=p.contractor_id
            where p.cutting_group_id=w.cutting_group_id and p.status='POSTED'
            order by p.posted_at desc,p.id desc limit 1
          )
        ) order by
          case when v_sort='PATTERN' then coalesce(w.pattern_sort_order,2147483647) end,
          case when v_sort='PATTERN' then coalesce(w.pattern_code,'~') end,
          case when v_sort='UPDATED' then w.updated_at end desc,
          w.po_number,w.group_number,w.cutting_group_id
      )
      from erp.v_wip_control_status_v1 w
      where (v_filter='ALL' or w.control_status=v_filter)
        and (p_pattern_id is null or w.pattern_id=p_pattern_id)
        and (v_query is null or lower(concat_ws(' ',w.po_number,w.group_number,w.model_code,w.model_name,
          w.pattern_code,w.pattern_name,w.executor_name,w.group_status,w.notes)) like '%'||v_query||'%')
    ),'[]'::jsonb)
  );
end
$function$;

revoke all on function erp.get_cutting_workspace_v1(text,uuid,integer,integer),
  erp.post_cutting_material_issue(uuid,uuid),
  erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint),
  erp.get_cutting_pickup_queue_v1(text,uuid,text,integer,integer),
  erp.save_cutting_pickup_v1(jsonb,uuid,bigint),
  erp.get_wip_control_v1(text,uuid,text,text)
  from public,anon,authenticated,service_role;

create function public.erp_get_cutting_workspace_v1(
  p_roll_query text default null,p_location_id uuid default null,
  p_limit integer default 100,p_offset integer default 0
)
returns jsonb language plpgsql stable security definer set search_path=''
as $function$ begin return erp.get_cutting_workspace_v1(p_roll_query,p_location_id,p_limit,p_offset); end $function$;

create function public.erp_save_cutting_group_before_sewing_v2(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb language plpgsql security definer set search_path=''
as $function$ begin return erp.save_cutting_group_before_sewing_v2(p_payload,p_client_request_id,p_expected_version); end $function$;

create function public.erp_get_cutting_pickup_queue_v1(
  p_filter text default 'WAITING',p_pattern_id uuid default null,p_query text default null,
  p_limit integer default 50,p_offset integer default 0
)
returns jsonb language plpgsql stable security definer set search_path=''
as $function$ begin return erp.get_cutting_pickup_queue_v1(p_filter,p_pattern_id,p_query,p_limit,p_offset); end $function$;

create function public.erp_save_cutting_pickup_v1(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb language plpgsql security definer set search_path=''
as $function$ begin return erp.save_cutting_pickup_v1(p_payload,p_client_request_id,p_expected_version); end $function$;

revoke all on function public.erp_get_cutting_workspace_v1(text,uuid,integer,integer),
  public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint),
  public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer),
  public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)
  from public,anon,authenticated,service_role;
grant execute on function public.erp_get_cutting_workspace_v1(text,uuid,integer,integer),
  public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint),
  public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer),
  public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)
  to authenticated,service_role;

comment on function public.erp_get_cutting_workspace_v1(text,uuid,integer,integer) is
  'Cutting Bridge guarded lookup. Returns active orders/sizes/warehouses/Mandors plus paginated roll stock at one warehouse.';
comment on function public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint) is
  'Cutting Bridge atomic draft/post Potongan writer over canonical cutting_groups, rolls, slots, yields, material ledger, and pattern snapshot.';
comment on function public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer) is
  'Cutting Bridge guarded Bagi Potongan queue with immutable pattern and exact roll/size yield lineage.';
comment on function public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint) is
  'Cutting Bridge atomic pickup and Batch Distribusi writer. POST requires exact source-yield reconciliation.';

do $post_guard$
declare
  v_bad text;
begin
  if exists(
    select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where p.oid in (
      'erp.get_cutting_workspace_v1(text,uuid,integer,integer)'::regprocedure,
      'erp.post_cutting_material_issue(uuid,uuid)'::regprocedure,
      'erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)'::regprocedure,
      'erp.get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)'::regprocedure,
      'erp.save_cutting_pickup_v1(jsonb,uuid,bigint)'::regprocedure,
      'erp.get_wip_control_v1(text,uuid,text,text)'::regprocedure,
      'erp.guard_cutting_source_location()'::regprocedure,
      'erp.guard_cutting_pickup_lifecycle()'::regprocedure,
      'erp.guard_cutting_distribution_detail()'::regprocedure,
      'public.erp_get_cutting_workspace_v1(text,uuid,integer,integer)'::regprocedure,
      'public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)'::regprocedure,
      'public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)'::regprocedure,
      'public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)'::regprocedure
    ) and (
      not p.prosecdef or p.proconfig is distinct from array['search_path=""']::text[]
      or pg_get_userbyid(p.proowner)<>'postgres'
    )
  ) then raise exception 'ERP v2.6.18 post guard: definer/search_path/owner contract failed'; end if;

  if exists(
    select 1 from pg_proc p
    where p.oid in (
      'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'::regprocedure,
      'erp.sync_material_cost_revaluation(uuid)'::regprocedure,
      'erp.post_journal(text,uuid,date,text,jsonb)'::regprocedure,
      'erp.refresh_accessory_hpp_after_material_recost(uuid,text)'::regprocedure,
      'erp.refresh_material_cost_checkpoint(uuid,date)'::regprocedure
    ) and lower(p.prosrc) like '%require_internal%'
  ) then raise exception 'ERP v2.6.18 post guard: private posting chain still has the obsolete coarse role gate'; end if;

  if has_function_privilege('anon','public.erp_get_cutting_workspace_v1(text,uuid,integer,integer)','EXECUTE')
     or has_function_privilege('anon','public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('anon','public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)','EXECUTE')
     or has_function_privilege('anon','public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_get_cutting_workspace_v1(text,uuid,integer,integer)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)','EXECUTE') then
    raise exception 'ERP v2.6.18 post guard: public facade ACL failed';
  end if;
  if has_function_privilege('anon','erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','EXECUTE')
     or has_function_privilege('authenticated','erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','EXECUTE')
     or has_function_privilege('anon','erp.sync_material_cost_revaluation(uuid)','EXECUTE')
     or has_function_privilege('authenticated','erp.sync_material_cost_revaluation(uuid)','EXECUTE')
     or has_function_privilege('anon','erp.post_journal(text,uuid,date,text,jsonb)','EXECUTE')
     or has_function_privilege('authenticated','erp.post_journal(text,uuid,date,text,jsonb)','EXECUTE')
     or has_function_privilege('anon','erp.refresh_accessory_hpp_after_material_recost(uuid,text)','EXECUTE')
     or has_function_privilege('authenticated','erp.refresh_accessory_hpp_after_material_recost(uuid,text)','EXECUTE')
     or has_function_privilege('anon','erp.refresh_material_cost_checkpoint(uuid,date)','EXECUTE')
     or has_function_privilege('authenticated','erp.refresh_material_cost_checkpoint(uuid,date)','EXECUTE')
     or has_function_privilege('authenticated','erp.post_cutting_material_issue(uuid,uuid)','EXECUTE')
     or has_function_privilege('authenticated','erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('anon','erp.post_cutting_material_issue(uuid,uuid)','EXECUTE')
     or has_function_privilege('anon','erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)','EXECUTE') then
    raise exception 'ERP v2.6.18 post guard: private writer/helper is directly executable';
  end if;
  if has_table_privilege('anon','erp.cutting_groups','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_groups','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.cutting_group_size_slots','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_group_size_slots','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.cutting_group_rolls','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_group_rolls','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.cutting_roll_yields','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_roll_yields','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.material_rolls','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.material_rolls','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.material_stock_movements','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.material_stock_movements','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.production_orders','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.production_orders','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.sizes','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.sizes','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.locations','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.locations','SELECT,INSERT,UPDATE,DELETE') then
    raise exception 'ERP v2.6.18 post guard: authenticated still has direct core table grants';
  end if;
  if has_table_privilege('anon','erp.cutting_pickups','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_pickups','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('service_role','erp.cutting_pickups','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.cutting_distribution_batches','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_distribution_batches','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('service_role','erp.cutting_distribution_batches','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.cutting_distribution_allocations','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_distribution_allocations','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('service_role','erp.cutting_distribution_allocations','SELECT,INSERT,UPDATE,DELETE') then
    raise exception 'ERP v2.6.18 post guard: private pickup/distribution table ACL failed';
  end if;
  if exists(
    select 1 from pg_class c
    where c.oid in(
      'erp.cutting_pickups'::regclass,
      'erp.cutting_distribution_batches'::regclass,
      'erp.cutting_distribution_allocations'::regclass
    ) and (not c.relrowsecurity or pg_get_userbyid(c.relowner)<>'postgres')
  ) then raise exception 'ERP v2.6.18 post guard: private table RLS/owner contract failed'; end if;
  if exists(
    select 1
    from pg_class c
    cross join lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a
    where c.oid in(
      'erp.cutting_pickups'::regclass,
      'erp.cutting_distribution_batches'::regclass,
      'erp.cutting_distribution_allocations'::regclass
    ) and a.grantee=0 and a.privilege_type in('SELECT','INSERT','UPDATE','DELETE')
  ) then raise exception 'ERP v2.6.18 post guard: PUBLIC can reach private pickup/distribution tables'; end if;

  select string_agg(c.object_identity,',' order by c.object_identity) into v_bad
  from erp.cutting_bridge_v2618_rollback_capsule c
  where c.object_kind='FUNCTION' and c.definition_sha256 is distinct from
    encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex');
  if v_bad is not null then raise exception 'ERP v2.6.18 post guard: rollback capsule drift: %',v_bad; end if;
  if (select count(*) from erp.cutting_bridge_v2618_rollback_capsule)<>17 then
    raise exception 'ERP v2.6.18 post guard: rollback capsule count changed';
  end if;
  if not exists(
    select 1 from pg_trigger where tgrelid='erp.cutting_groups'::regclass
      and tgname='trg_07_guard_cutting_source_location' and tgenabled<>'D' and not tgisinternal
  ) or not exists(
    select 1 from pg_trigger where tgrelid='erp.cutting_pickups'::regclass
      and tgname='trg_00_guard_cutting_pickup_lifecycle' and tgenabled<>'D' and not tgisinternal
  ) or not exists(
    select 1 from pg_trigger where tgrelid='erp.cutting_distribution_batches'::regclass
      and tgname='trg_guard_cutting_distribution_batches' and tgenabled<>'D' and not tgisinternal
  ) or not exists(
    select 1 from pg_trigger where tgrelid='erp.cutting_distribution_allocations'::regclass
      and tgname='trg_guard_cutting_distribution_allocations' and tgenabled<>'D' and not tgisinternal
  ) then raise exception 'ERP v2.6.18 post guard: source/pickup/distribution lifecycle trigger missing'; end if;
end
$post_guard$;

insert into erp.schema_migrations(version,description)
values('v2.6.18','Pre-CP5 Cutting Bridge: guarded Potongan persistence, material posting, pickup distribution, and WIP continuity');

select pg_notify('pgrst','reload schema');
commit;
