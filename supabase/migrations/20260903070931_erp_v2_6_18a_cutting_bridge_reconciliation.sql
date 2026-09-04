-- ERP Garment v2.6.18a / Cutting Bridge recorded-source reconciliation.
--
-- v2.6.18 was already recorded on ERP Enteng UAT before its local source was
-- hardened. This forward-only delta preserves the recorded business behavior
-- while restoring every canonical require_internal() guard through a private,
-- transaction-scoped capability. It also closes the Pattern lookup and private
-- rollback-capsule RLS gaps. It creates no business facts.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $guard$
declare
  r record;
  v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.18') then
    raise exception 'ERP v2.6.18a requires the recorded v2.6.18 boundary first';
  end if;
  if exists(select 1 from erp.schema_migrations where version in('v2.6.18a','v2.6.19')) then
    raise exception 'ERP v2.6.18a is already recorded or CP5 is already installed';
  end if;
  if to_regclass('erp.cutting_bridge_v2618_rollback_capsule') is null
     or (select count(*) from erp.cutting_bridge_v2618_rollback_capsule where object_kind='FUNCTION')<>8
     or (select count(*) from erp.cutting_bridge_v2618_rollback_capsule where object_kind='RELATION')<>9
     or to_regclass('erp.cutting_bridge_v2618a_rollback_capsule') is not null
     or to_regclass('erp.cutting_bridge_execution_context') is not null
     or to_regclass('erp.idx_material_stock_location_roll') is null
     or to_regclass('erp.idx_material_stock_roll_location') is not null then
    raise exception 'ERP v2.6.18a target guard: recorded v2.6.18 object boundary drifted';
  end if;
  if (select relrowsecurity from pg_class where oid='erp.cutting_bridge_v2618_rollback_capsule'::regclass) then
    raise exception 'ERP v2.6.18a target guard: recorded rollback capsule RLS state drifted';
  end if;
  if exists(select 1 from erp.cutting_pickups)
     or exists(select 1 from erp.cutting_distribution_batches)
     or exists(select 1 from erp.cutting_distribution_allocations)
     or exists(select 1 from erp.cutting_groups where source_location_id is not null)
     or exists(
       select 1 from erp.idempotency_requests
       where operation_name in('save_cutting_group_before_sewing_v2','save_cutting_pickup_v1')
     )
     or exists(
       select 1 from erp.audit_logs
       where entity_type in('cutting_pickups','cutting_distribution_batches','cutting_distribution_allocations')
     ) then
    raise exception 'ERP v2.6.18a reconciliation requires the unused recorded v2.6.18 boundary';
  end if;

  for r in
    select * from (values
      ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','cb366d2728b7e7f6693fdc0098c239cb'),
      ('erp.sync_material_cost_revaluation(uuid)','0188292c0383564b59c17743a26c3195'),
      ('erp.post_journal(text,uuid,date,text,jsonb)','c692b9ce872625113cb7677bf53b7fb1'),
      ('erp.refresh_accessory_hpp_after_material_recost(uuid,text)','31e871d98fdcf9c17aeb88b1598da585'),
      ('erp.refresh_material_cost_checkpoint(uuid,date)','97280ef7ea68595d003b20204358a735'),
      ('erp.require_internal()','785838675ae23699ce163e4218f058bf'),
      ('erp.list_patterns_v1(text,text,integer,integer)','feff17283c331b4883b208227bc99079'),
      ('erp.post_cutting_material_issue(uuid,uuid)','bf91c08814f5eba65412439b7edb07bb'),
      ('erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)','d88d6bb0a2fd464a6fc8aa924a5bb321'),
      ('erp.get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)','42b1bdae9629bdb782999107432453a9'),
      ('erp.save_cutting_pickup_v1(jsonb,uuid,bigint)','0efe19cfa2684ad96781d8ef7bdc8ce6')
    ) expected(identity,expected_md5)
  loop
    if to_regprocedure(r.identity) is null then
      raise exception 'ERP v2.6.18a target guard: required function % is absent',r.identity;
    end if;
    select md5(pg_get_functiondef(to_regprocedure(r.identity))) into v_actual;
    if v_actual is distinct from r.expected_md5 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: % changed (% vs %)',r.identity,v_actual,r.expected_md5;
    end if;
  end loop;
  if exists(
    select 1 from pg_proc p
    where p.oid in(
      'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'::regprocedure,
      'erp.sync_material_cost_revaluation(uuid)'::regprocedure,
      'erp.post_journal(text,uuid,date,text,jsonb)'::regprocedure,
      'erp.refresh_accessory_hpp_after_material_recost(uuid,text)'::regprocedure,
      'erp.refresh_material_cost_checkpoint(uuid,date)'::regprocedure
    ) and lower(p.prosrc) like '%require_internal%'
  ) then raise exception 'ERP v2.6.18a target guard: recorded helper state is not the known vulnerable boundary'; end if;
end
$guard$;

-- Capture the exact recorded-v2.6.18 runtime before correcting it. The
-- correction rollback is pre-use only and restores this byte-for-byte before
-- the original v2.6.18 rollback is allowed to run.
create table erp.cutting_bridge_v2618a_rollback_capsule(
  object_identity text primary key,
  object_definition text not null,
  definition_sha256 text not null,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.cutting_bridge_v2618a_rollback_capsule enable row level security;
revoke all on table erp.cutting_bridge_v2618a_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cutting_bridge_v2618a_rollback_capsule(
  object_identity,object_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,
  pg_get_userbyid(p.proowner)
from pg_proc p
join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'::regprocedure,
  'erp.sync_material_cost_revaluation(uuid)'::regprocedure,
  'erp.post_journal(text,uuid,date,text,jsonb)'::regprocedure,
  'erp.refresh_accessory_hpp_after_material_recost(uuid,text)'::regprocedure,
  'erp.refresh_material_cost_checkpoint(uuid,date)'::regprocedure,
  'erp.require_internal()'::regprocedure,
  'erp.list_patterns_v1(text,text,integer,integer)'::regprocedure,
  'erp.post_cutting_material_issue(uuid,uuid)'::regprocedure
);

do $capsule_guard$
begin
  if (select count(*) from erp.cutting_bridge_v2618a_rollback_capsule)<>8
     or exists(
       select 1 from erp.cutting_bridge_v2618a_rollback_capsule
       where definition_sha256 is distinct from
         encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
     ) then
    raise exception 'ERP v2.6.18a rollback capsule is incomplete or invalid';
  end if;
end
$capsule_guard$;

alter table erp.cutting_bridge_v2618_rollback_capsule enable row level security;

drop index erp.idx_material_stock_location_roll;
create index idx_material_stock_roll_location
  on erp.material_stock_movements(roll_id,location_id,system_created_at,id)
  where roll_id is not null;

create table erp.cutting_bridge_execution_context(
  backend_pid integer not null,
  transaction_id bigint not null,
  actor_key text not null check(btrim(actor_key)<>''),
  action text not null check(action='POST_CUTTING'),
  permission_key text not null check(permission_key='production.cutting.post'),
  created_at timestamptz not null default clock_timestamp(),
  primary key(backend_pid,transaction_id)
);
alter table erp.cutting_bridge_execution_context enable row level security;
revoke all on table erp.cutting_bridge_execution_context from public,anon,authenticated,service_role;

-- Restore the five canonical helpers from the pre-v2.6.18 capsule. CREATE OR
-- REPLACE preserves the already-hardened ACL while restoring each inner guard.
do $restore_private_guards$
declare r record;v_restored integer:=0;
begin
  for r in
    select object_identity,object_definition
    from erp.cutting_bridge_v2618_rollback_capsule
    where object_kind='FUNCTION' and object_identity like any(array[
      'erp._recalculate_material_cost_core(%',
      'erp.sync_material_cost_revaluation(%',
      'erp.post_journal(%',
      'erp.refresh_accessory_hpp_after_material_recost(%',
      'erp.refresh_material_cost_checkpoint(%'
    ])
    order by object_identity
  loop
    execute r.object_definition;
    v_restored:=v_restored+1;
  end loop;
  if v_restored<>5 then
    raise exception 'ERP v2.6.18a private posting chain is incomplete: restored % of 5 helpers',v_restored;
  end if;
end
$restore_private_guards$;

create or replace function erp.require_internal()
returns void
language plpgsql
volatile
security definer
set search_path=''
as $function$
declare
  v_app_role text;
  v_jwt_role text;
begin
  if session_user in('postgres','supabase_admin') then return; end if;
  begin
    v_jwt_role:=coalesce(auth.jwt()->>'role','');
  exception when others then
    v_jwt_role:='';
  end;
  if v_jwt_role='service_role' then return; end if;
  if exists(
    select 1
    from erp.cutting_bridge_execution_context c
    where c.backend_pid=pg_backend_pid()
      and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key()
      and c.action='POST_CUTTING'
      and c.permission_key='production.cutting.post'
      and erp.has_permission(c.permission_key)
  ) then return; end if;
  v_app_role:=erp.current_app_role();
  if v_app_role not in('OWNER','ADMIN','STAFF') then
    raise exception 'Internal ERP access required';
  end if;
end
$function$;

create or replace function erp.list_patterns_v1(
  p_status text default 'ACTIVE',p_query text default null,
  p_limit integer default 100,p_offset integer default 0
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare v_status text:=upper(coalesce(nullif(btrim(p_status),''),'ACTIVE'));
  v_query text:=lower(nullif(btrim(p_query),''));
begin
  if not erp.has_permission('master.pattern.view')
     and not erp.has_permission('production.cutting.view')
     and not erp.has_permission('production.distribution.view')
     and not erp.has_permission('production.wip.view')
     and not erp.has_permission('production.bs_rework.view') then
    raise exception using errcode='42501',message='PERMISSION_DENIED: master.pattern.view or production lookup access';
  end if;
  if v_status not in ('ACTIVE','INACTIVE','ALL') then raise exception 'status must be ACTIVE, INACTIVE, or ALL'; end if;
  if p_limit is null or p_limit<1 or p_limit>200 then raise exception 'limit must be between 1 and 200'; end if;
  if p_offset is null or p_offset<0 then raise exception 'offset must be nonnegative'; end if;
  return jsonb_build_object(
    'status',v_status,'query',v_query,'limit',p_limit,'offset',p_offset,
    'total',(
      select count(*) from erp.production_patterns p
      where (v_status='ALL' or p.is_active=(v_status='ACTIVE'))
        and (v_query is null or lower(concat_ws(' ',p.pattern_code,p.revision,p.pattern_name)) like '%'||v_query||'%')
    ),
    'rows',coalesce((
      select jsonb_agg(jsonb_build_object(
        'id',x.id,'code',x.pattern_code,'revision',x.revision,'name',x.pattern_name,
        'sort_order',x.sort_order,'is_active',x.is_active,'row_version',x.row_version,
        'updated_at',x.updated_at,'updated_by',x.updated_by_name,'usage_count',x.usage_count
      ) order by x.sort_order,x.pattern_code,x.revision,x.id)
      from (
        select p.*,u.full_name as updated_by_name,(
          select count(*) from erp.cutting_groups g where g.pattern_id=p.id
        ) usage_count
        from erp.production_patterns p left join erp.app_users u on u.id=p.updated_by
        where (v_status='ALL' or p.is_active=(v_status='ACTIVE'))
          and (v_query is null or lower(concat_ws(' ',p.pattern_code,p.revision,p.pattern_name)) like '%'||v_query||'%')
        order by p.sort_order,p.pattern_code,p.revision,p.id
        limit p_limit offset p_offset
      ) x
    ),'[]'::jsonb)
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

  insert into erp.cutting_bridge_execution_context(
    backend_pid,transaction_id,actor_key,action,permission_key
  ) values(
    pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),
    'POST_CUTTING','production.cutting.post'
  );

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
  delete from erp.cutting_bridge_execution_context
  where backend_pid=pg_backend_pid()
    and transaction_id=txid_current()
    and actor_key=erp._idempotency_actor_key();
  if not found then raise exception 'Cutting Bridge execution context was lost before completion'; end if;
end
$function$;

revoke all on function erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean),
  erp.sync_material_cost_revaluation(uuid),
  erp.post_journal(text,uuid,date,text,jsonb),
  erp.refresh_accessory_hpp_after_material_recost(uuid,text),
  erp.refresh_material_cost_checkpoint(uuid,date),
  erp.require_internal(),
  erp.list_patterns_v1(text,text,integer,integer),
  erp.post_cutting_material_issue(uuid,uuid)
  from public,anon,authenticated;

do $post_guard$
declare
  r record;
  v_actual text;
  v_internal_def text;
begin
  for r in
    select * from (values
      ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','e22579757c48090ea5ea9332fb73ddbf'),
      ('erp.sync_material_cost_revaluation(uuid)','b6719703eb60333169f4f9afd8e7dd35'),
      ('erp.post_journal(text,uuid,date,text,jsonb)','dbf6138ccc575950fc6aed789863af8c'),
      ('erp.refresh_accessory_hpp_after_material_recost(uuid,text)','1fef2342c5d8e89dede7edcb3bef36ed'),
      ('erp.refresh_material_cost_checkpoint(uuid,date)','a2aa967ea4e86adf9ed65d302f4c2918')
    ) expected(identity,expected_md5)
  loop
    select md5(pg_get_functiondef(to_regprocedure(r.identity))) into v_actual;
    if v_actual is distinct from r.expected_md5 then
      raise exception 'ERP v2.6.18a failed to restore private guard at % (% vs %)',r.identity,v_actual,r.expected_md5;
    end if;
  end loop;
  select pg_get_functiondef('erp.require_internal()'::regprocedure) into v_internal_def;
  if v_internal_def not like '%cutting_bridge_execution_context%'
     or v_internal_def not like '%transaction_id=txid_current()%'
     or v_internal_def not like '%actor_key=erp._idempotency_actor_key()%'
     or v_internal_def not like '%erp.has_permission(c.permission_key)%'
     or position('production.distribution.view' in pg_get_functiondef('erp.list_patterns_v1(text,text,integer,integer)'::regprocedure))=0
     or position('production.bs_rework.view' in pg_get_functiondef('erp.list_patterns_v1(text,text,integer,integer)'::regprocedure))=0
     or position('insert into erp.cutting_bridge_execution_context' in pg_get_functiondef('erp.post_cutting_material_issue(uuid,uuid)'::regprocedure))=0
     or position('Cutting Bridge execution context was lost before completion' in pg_get_functiondef('erp.post_cutting_material_issue(uuid,uuid)'::regprocedure))=0 then
    raise exception 'ERP v2.6.18a scoped delegation or Pattern lookup contract is incomplete';
  end if;
  if exists(
    select 1 from pg_proc p
    where p.oid in(
      'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'::regprocedure,
      'erp.sync_material_cost_revaluation(uuid)'::regprocedure,
      'erp.post_journal(text,uuid,date,text,jsonb)'::regprocedure,
      'erp.refresh_accessory_hpp_after_material_recost(uuid,text)'::regprocedure,
      'erp.refresh_material_cost_checkpoint(uuid,date)'::regprocedure
    ) and lower(p.prosrc) not like '%require_internal%'
  ) then raise exception 'ERP v2.6.18a left a canonical private helper unguarded'; end if;
  if has_table_privilege('anon','erp.cutting_bridge_execution_context','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_bridge_execution_context','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.cutting_bridge_v2618a_rollback_capsule','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_bridge_v2618a_rollback_capsule','SELECT,INSERT,UPDATE,DELETE')
     or has_function_privilege('authenticated','erp.require_internal()','EXECUTE')
     or has_function_privilege('authenticated','erp.post_cutting_material_issue(uuid,uuid)','EXECUTE')
     or exists(select 1 from erp.cutting_bridge_execution_context)
     or not (select relrowsecurity from pg_class where oid='erp.cutting_bridge_v2618_rollback_capsule'::regclass)
     or not (select relrowsecurity from pg_class where oid='erp.cutting_bridge_v2618a_rollback_capsule'::regclass)
     or to_regclass('erp.idx_material_stock_roll_location') is null
     or to_regclass('erp.idx_material_stock_location_roll') is not null
     or (select count(*) from erp.cutting_bridge_v2618a_rollback_capsule)<>8 then
    raise exception 'ERP v2.6.18a private relation, ACL, index, or capsule contract failed';
  end if;
end
$post_guard$;

insert into erp.schema_migrations(version,description)
values(
  'v2.6.18a',
  'Reconcile recorded Cutting Bridge: restore private accounting guards with transaction-scoped delegation, protect rollback capsule, and open permission-scoped Pattern lookup'
);

select pg_notify('pgrst','reload schema');
commit;
