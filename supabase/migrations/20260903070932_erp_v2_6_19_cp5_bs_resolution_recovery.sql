-- ERP Garment v2.6.19 / CP5 BS Resolution and downstream recovery.
--
-- This delta follows the recorded-source v2.6.18a reconciliation and exposes
-- the existing authoritative BS, rework, Laundry-claim,
-- FG, HPP, and reversal machinery through one permission-checked browser
-- boundary. HOLD is persisted as an explicit, auditable state. No duplicate
-- BS ledger, shadow rework table, or client-authored accounting is introduced.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $guard$
declare
  r record;
  v_actual text;
  v_status_constraint text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.18')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.18a') then
    raise exception 'ERP v2.6.19 requires the recorded v2.6.18 plus reconciled v2.6.18a Cutting Bridge boundary first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.19') then
    raise exception 'ERP v2.6.19 is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.bs_resolution_v2619_rollback_capsule') is not null
     or to_regclass('erp.bs_case_hold_events') is not null
     or to_regclass('erp.bs_resolution_execution_context') is not null
     or to_regprocedure('erp.get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)') is not null
     or to_regprocedure('erp.save_bs_resolution_action_v1(text,jsonb,uuid,bigint)') is not null
     or to_regprocedure('public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)') is not null
     or to_regprocedure('public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)') is not null
     or to_regprocedure('erp.guard_bs_case_hold_event_immutable()') is not null then
    raise exception 'ERP v2.6.19 target guard: prior CP5 residue exists';
  end if;
  if to_regclass('erp.bs_cases') is null
     or to_regclass('erp.bs_case_components') is null
     or to_regclass('erp.bs_resolutions') is null
     or to_regclass('erp.rework_orders') is null
     or to_regclass('erp.rework_component_lines') is null
     or to_regclass('erp.laundry_claims') is null
     or to_regclass('erp.cutting_bridge_execution_context') is null
     or to_regclass('erp.cutting_groups') is null
     or to_regclass('erp.production_patterns') is null
     or to_regprocedure('erp.require_internal()') is null
     or to_regprocedure('erp.require_permission(text)') is null
     or to_regprocedure('erp.has_permission(text)') is null
     or to_regprocedure('erp.list_patterns_v1(text,text,integer,integer)') is null
     or to_regprocedure('erp._idempotency_actor_key()') is null
     or to_regprocedure('erp._idempotency_begin(text,uuid,text)') is null
     or to_regprocedure('erp._idempotency_complete(text,uuid,jsonb)') is null then
    raise exception 'ERP v2.6.19 target guard: required BS/Rework/Laundry/CP4.5 contract is incomplete';
  end if;

  select pg_get_constraintdef(c.oid,true) into v_status_constraint
  from pg_constraint c
  where c.conrelid='erp.bs_cases'::regclass and c.conname='bs_cases_status_check';
  if v_status_constraint is null
     or v_status_constraint not like '%OPEN%IN_REWORK%PARTIAL%RESOLVED%SCRAPPED%WRITTEN_OFF%CANCELLED%'
     or v_status_constraint like '%ON_HOLD%' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: bs_cases status boundary changed';
  end if;

  for r in
    select * from (values
      ('erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)','b1ef668ab9541a8b4abea71c2bb95bf5'),
      ('erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint)','c59e0fc2f14934d3947ce5cc7f3c78bb'),
      ('erp.create_manual_bs_case_v2(jsonb,uuid)','01f6aab85855fd121587a107af171489'),
      ('erp.ensure_fg_accessory_cost_snapshot(uuid)','aae034da6699fb2f7b4c5f817e8d9f50'),
      ('erp.guard_bs_case_lifecycle()','a5c9065c699693f5339618ada86e9dbf'),
      ('erp.post_accessory_reimbursement_accrual(uuid)','36804117ef5af6f018c199518bd2e915'),
      ('erp.post_fg_movement(uuid,uuid,uuid,text,text,integer,numeric,uuid,text,uuid,timestamp with time zone,text,boolean)','63f4aabc5cf34afd0765017c578e4416'),
      ('erp.post_rework_completion(uuid)','bf610b5a00636297eab1f640bdc5da8c'),
      ('erp.propagate_conversion_hpp_for_po(uuid)','f3c86a2a1d282927d9c9e1af1404fa93'),
      ('erp.rebuild_po_hpp(uuid,text)','bf5593c35375abb35c0c6d531ee375e6'),
      ('erp.refresh_bs_case_status(uuid)','ee4c1b83f51f194c16d7ee470f2b199f'),
      ('erp.resolve_bs_case_disposition_v2(uuid,text,integer,numeric,uuid,timestamp with time zone,text,uuid,bigint)','63da04a3aea6a6f5a4c5f956358e3f61'),
      ('erp.resolve_laundry_claim_v2(uuid,text,text,uuid,bigint)','3397f799634f9d6fe9fc2f4cbb60359d'),
      ('erp.reverse_bs_disposition_v2(uuid,text,uuid,bigint)','18d30304914850d90fb11bfd885d8f93'),
      ('erp.reverse_laundry_claim_resolution(uuid,text)','685a8ff668c28b5673cd24a2a89c6f7f'),
      ('erp.reverse_rework_completion(uuid,text)','03922a375d81a03085ba97df420d3547'),
      ('erp.save_laundry_claim_v2(jsonb,uuid,bigint)','3ce81f61adc7d56c5bd9d048dafda180'),
      ('erp.save_rework_order_v2(jsonb,uuid,bigint)','d4f297f43858bb3c819c9cacec2972ab'),
      ('erp.sync_po_hpp_to_gl(uuid,date)','0ecc997982964a03e0d8c93efcb9ddcc')
    ) expected(identity,expected_md5)
  loop
    if to_regprocedure(r.identity) is null then
      raise exception 'ERP v2.6.19 target guard: required function % is absent',r.identity;
    end if;
    select md5(pg_get_functiondef(to_regprocedure(r.identity))) into v_actual;
    if v_actual is distinct from r.expected_md5 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: % changed (% vs %)',r.identity,v_actual,r.expected_md5;
    end if;
  end loop;
  if (
    select md5(p.prosrc) from pg_proc p
    where p.oid='erp.require_internal()'::regprocedure
  ) is distinct from 'c3659641c0ed8112d22b015a04130c95' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.18 scoped require_internal changed';
  end if;
  if position('production.distribution.view' in pg_get_functiondef('erp.list_patterns_v1(text,text,integer,integer)'::regprocedure))=0
     or position('production.bs_rework.view' in pg_get_functiondef('erp.list_patterns_v1(text,text,integer,integer)'::regprocedure))=0 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.18 production Pattern lookup changed';
  end if;
end
$guard$;

-- Exact pre-CP5 function definitions/ACLs/owners and relation ACLs/owners.
-- The capsule contains no business rows and is itself RLS-protected.
create table erp.bs_resolution_v2619_rollback_capsule(
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
alter table erp.bs_resolution_v2619_rollback_capsule enable row level security;
revoke all on table erp.bs_resolution_v2619_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.bs_resolution_v2619_rollback_capsule(
  object_kind,object_identity,object_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select 'FUNCTION',
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in (
  'erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)'::regprocedure,
  'erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint)'::regprocedure,
  'erp.create_manual_bs_case_v2(jsonb,uuid)'::regprocedure,
  'erp.ensure_fg_accessory_cost_snapshot(uuid)'::regprocedure,
  'erp.guard_bs_case_lifecycle()'::regprocedure,
  'erp.post_accessory_reimbursement_accrual(uuid)'::regprocedure,
  'erp.post_fg_movement(uuid,uuid,uuid,text,text,integer,numeric,uuid,text,uuid,timestamp with time zone,text,boolean)'::regprocedure,
  'erp.post_rework_completion(uuid)'::regprocedure,
  'erp.propagate_conversion_hpp_for_po(uuid)'::regprocedure,
  'erp.rebuild_po_hpp(uuid,text)'::regprocedure,
  'erp.refresh_bs_case_status(uuid)'::regprocedure,
  'erp.require_internal()'::regprocedure,
  'erp.resolve_bs_case_disposition_v2(uuid,text,integer,numeric,uuid,timestamp with time zone,text,uuid,bigint)'::regprocedure,
  'erp.resolve_laundry_claim_v2(uuid,text,text,uuid,bigint)'::regprocedure,
  'erp.reverse_bs_disposition_v2(uuid,text,uuid,bigint)'::regprocedure,
  'erp.reverse_laundry_claim_resolution(uuid,text)'::regprocedure,
  'erp.reverse_rework_completion(uuid,text)'::regprocedure,
  'erp.save_laundry_claim_v2(jsonb,uuid,bigint)'::regprocedure,
  'erp.save_rework_order_v2(jsonb,uuid,bigint)'::regprocedure,
  'erp.sync_po_hpp_to_gl(uuid,date)'::regprocedure
);

insert into erp.bs_resolution_v2619_rollback_capsule(
  object_kind,object_identity,acl_snapshot,owner_snapshot
)
select 'RELATION',format('%I.%I',n.nspname,c.relname),
  case when c.relacl is null then null else array(select a::text from unnest(c.relacl) a) end,
  pg_get_userbyid(c.relowner)
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where c.oid in (
  'erp.bs_cases'::regclass,'erp.bs_case_components'::regclass,
  'erp.bs_resolutions'::regclass,'erp.rework_orders'::regclass,
  'erp.rework_component_lines'::regclass,'erp.laundry_claims'::regclass,
  'erp.laundry_deliveries'::regclass,'erp.laundry_delivery_lines'::regclass,
  'erp.laundry_receipts'::regclass,'erp.laundry_receipt_lines'::regclass
);

do $capsule_guard$
begin
  if (select count(*) from erp.bs_resolution_v2619_rollback_capsule where object_kind='FUNCTION')<>20
     or (select count(*) from erp.bs_resolution_v2619_rollback_capsule where object_kind='RELATION')<>10
     or exists(
       select 1 from erp.bs_resolution_v2619_rollback_capsule
       where object_kind='FUNCTION' and definition_sha256 is distinct from
         encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
     ) then raise exception 'ERP v2.6.19 rollback capsule is incomplete or invalid'; end if;
end
$capsule_guard$;

alter table erp.bs_cases drop constraint bs_cases_status_check;
alter table erp.bs_cases add constraint bs_cases_status_check check(status in(
  'OPEN','IN_REWORK','PARTIAL','ON_HOLD','RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED'
));

create table erp.bs_case_hold_events(
  id uuid primary key default gen_random_uuid(),
  bs_case_id uuid not null references erp.bs_cases(id) on delete restrict,
  action text not null check(action in('HOLD','RELEASE')),
  previous_status text not null,
  resulting_status text not null,
  reason text not null check(btrim(reason)<>''),
  physical_at timestamptz not null,
  actor_id uuid references erp.app_users(id),
  client_request_id uuid not null unique,
  created_at timestamptz not null default clock_timestamp()
);
create index idx_bs_case_hold_events_case on erp.bs_case_hold_events(bs_case_id,physical_at desc,id desc);
alter table erp.bs_case_hold_events enable row level security;
revoke all on table erp.bs_case_hold_events from public,anon,authenticated,service_role;

-- A transaction-scoped capability lets the permission-checked CP5 facade call
-- the legacy FG/HPP/accounting chain without weakening require_internal for any
-- other caller. Browser roles cannot read or forge this private context.
create table erp.bs_resolution_execution_context(
  backend_pid integer not null,
  transaction_id bigint not null,
  actor_key text not null check(btrim(actor_key)<>''),
  action text not null check(action in(
    'CREATE_MANUAL_BS','CLASSIFY_BS','SAVE_REWORK','COMPLETE_REWORK',
    'DISPOSE_BS','HOLD_BS','RELEASE_HOLD','REVERSE_DISPOSITION',
    'REVERSE_REWORK_COMPLETION','SAVE_CLAIM','RESOLVE_CLAIM',
    'REVERSE_CLAIM_RESOLUTION'
  )),
  permission_key text not null,
  created_at timestamptz not null default clock_timestamp(),
  primary key(backend_pid,transaction_id),
  check(
    permission_key='production.bs_rework.create'
      and action in('CREATE_MANUAL_BS','CLASSIFY_BS','SAVE_REWORK','SAVE_CLAIM')
    or permission_key='production.bs_rework.post'
      and action in('COMPLETE_REWORK','DISPOSE_BS','HOLD_BS','RELEASE_HOLD','RESOLVE_CLAIM')
    or permission_key='production.bs_rework.reverse'
      and action in('REVERSE_DISPOSITION','REVERSE_REWORK_COMPLETION','REVERSE_CLAIM_RESOLUTION')
  )
);
alter table erp.bs_resolution_execution_context enable row level security;
revoke all on table erp.bs_resolution_execution_context from public,anon,authenticated,service_role;

create function erp.guard_bs_case_hold_event_immutable()
returns trigger language plpgsql security definer set search_path=''
as $function$
begin
  raise exception using errcode='42501',message='BS_HOLD_HISTORY_IS_APPEND_ONLY';
end
$function$;
revoke all on function erp.guard_bs_case_hold_event_immutable() from public,anon,authenticated,service_role;
create trigger trg_guard_bs_case_hold_event_immutable
before update or delete on erp.bs_case_hold_events
for each row execute function erp.guard_bs_case_hold_event_immutable();
create trigger trg_audit_bs_case_hold_events
after insert on erp.bs_case_hold_events
for each row execute function erp.audit_row_change();

create or replace function erp.guard_bs_case_lifecycle()
returns trigger
language plpgsql
set search_path=''
as $function$
declare v_hold_transition text:=upper(coalesce(current_setting('app.bs_hold_transition',true),''));
begin
  if tg_op='UPDATE' and new.status is distinct from old.status
     and (old.status='ON_HOLD' or new.status='ON_HOLD')
     and session_user not in('postgres','supabase_admin')
     and not(
       new.status='ON_HOLD' and old.status<>'ON_HOLD' and v_hold_transition='HOLD'
       or old.status='ON_HOLD' and new.status<>'ON_HOLD' and v_hold_transition='RELEASE'
     ) then
    raise exception using errcode='42501',message='BS_HOLD_TRANSITION_REQUIRES_CP5_ACTION';
  end if;
  if current_user in('postgres','service_role','supabase_admin') then
    if tg_op='DELETE' then return old; else return new; end if;
  end if;
  if tg_op='INSERT' then new.status:='OPEN';return new;end if;
  if tg_op='DELETE' then
    raise exception 'BS case cannot be deleted directly; use controlled correction/resolution flow';
  end if;
  if new.status is distinct from old.status then
    raise exception 'BS status is system-managed by rework/resolution posting';
  end if;
  if new.qty_pcs is distinct from old.qty_pcs
     or new.po_id is distinct from old.po_id
     or new.cutting_group_id is distinct from old.cutting_group_id
     or new.qc_item_id is distinct from old.qc_item_id
     or new.product_id is distinct from old.product_id
     or new.detected_at_stage is distinct from old.detected_at_stage
     or new.physical_at is distinct from old.physical_at then
    raise exception 'BS quantity/lineage is immutable; use controlled correction flow';
  end if;
  return new;
end
$function$;

create or replace function erp.refresh_bs_case_status(p_bs_case_id uuid)
returns void
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_case erp.bs_cases%rowtype;
  v_resolved integer;
  v_active boolean;
  v_status text;
  v_hold_transition text:=upper(coalesce(current_setting('app.bs_hold_transition',true),''));
begin
  select * into v_case from erp.bs_cases where id=p_bs_case_id for update;
  if v_case.id is null or v_case.status='CANCELLED' then return; end if;
  if v_case.status='ON_HOLD' and v_hold_transition<>'RELEASE' then return; end if;
  select coalesce(sum(qty_pcs),0)::integer into v_resolved
  from erp.bs_resolutions where bs_case_id=v_case.id;
  select exists(
    select 1 from erp.rework_orders
    where bs_case_id=v_case.id and status in('OPEN','IN_PROGRESS','PARTIAL')
  ) into v_active;
  if v_resolved>=v_case.qty_pcs then
    if exists(select 1 from erp.bs_resolutions where bs_case_id=v_case.id)
       and not exists(select 1 from erp.bs_resolutions where bs_case_id=v_case.id and resolution_type<>'SCRAP') then
      v_status:='SCRAPPED';
    elsif exists(select 1 from erp.bs_resolutions where bs_case_id=v_case.id)
       and not exists(select 1 from erp.bs_resolutions where bs_case_id=v_case.id and resolution_type<>'WRITE_OFF') then
      v_status:='WRITTEN_OFF';
    else v_status:='RESOLVED'; end if;
  elsif v_active then v_status:='IN_REWORK';
  elsif v_resolved>0 then v_status:='PARTIAL';
  else v_status:='OPEN'; end if;
  if v_case.status is distinct from v_status then
    update erp.bs_cases set status=v_status,updated_at=clock_timestamp() where id=v_case.id;
  end if;
end
$function$;

-- Manual recovery starts with cause_source UNKNOWN and an untracked_type.
-- Once an operator classifies the cause, keep the legacy reference as audit
-- lineage but clear the no-longer-true untracked flag so bs_cases_check holds.
create or replace function erp.classify_bs_case_v2(
  p_bs_case_id uuid,p_payload jsonb,p_client_request_id uuid,p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path=erp,public,auth,extensions,pg_temp
as $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_case erp.bs_cases%rowtype;
  v_cause text;v_contractor uuid;v_vendor uuid;
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_component jsonb;v_snapshot uuid;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'bs_case_id',p_bs_case_id,'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('classify_bs_case_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_case from erp.bs_cases where id=p_bs_case_id for update;
  if v_case.id is null then raise exception 'BS case not found'; end if;
  if v_case.status not in('OPEN','PARTIAL','IN_REWORK') then raise exception 'Closed/cancelled BS case cannot be classified'; end if;
  if v_case.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_case.row_version;
  end if;
  v_cause:=upper(coalesce(nullif(p_payload->>'cause_source',''),v_case.cause_source));
  v_contractor:=case when p_payload?'responsible_contractor_id'
    then nullif(p_payload->>'responsible_contractor_id','')::uuid else v_case.responsible_contractor_id end;
  v_vendor:=case when p_payload?'responsible_vendor_id'
    then nullif(p_payload->>'responsible_vendor_id','')::uuid else v_case.responsible_vendor_id end;
  if v_cause='SEWING' and v_contractor is null then raise exception 'SEWING cause requires responsible contractor'; end if;
  if v_cause='LAUNDRY' and v_vendor is null then raise exception 'LAUNDRY cause requires responsible vendor'; end if;
  if v_cause not in('SEWING','LAUNDRY','UNKNOWN') then raise exception 'Invalid cause_source'; end if;
  perform set_config('app.change_reason',v_reason,true);
  update erp.bs_cases
  set cause_source=v_cause,responsible_contractor_id=v_contractor,
      responsible_vendor_id=v_vendor,
      untracked_type=case when v_cause='UNKNOWN' then untracked_type else null end,
      notes=case when p_payload?'notes' then nullif(btrim(p_payload->>'notes'),'') else notes end,
      legacy_reference=case when p_payload?'legacy_reference' then nullif(btrim(p_payload->>'legacy_reference'),'') else legacy_reference end,
      updated_at=now()
  where id=v_case.id returning * into v_case;

  if p_payload?'components' then
    if exists(
      select 1 from erp.rework_component_lines rcl
      join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
      where bcc.bs_case_id=v_case.id
    ) then raise exception 'BS components are frozen after rework lines exist'; end if;
    if jsonb_typeof(p_payload->'components')<>'array' then raise exception 'components must be an array'; end if;
    delete from erp.bs_case_components where bs_case_id=v_case.id;
    for v_component in select value from jsonb_array_elements(p_payload->'components') loop
      select id into v_snapshot from erp.po_work_component_snapshots
      where po_id=v_case.po_id and work_component_id=(v_component->>'work_component_id')::uuid
      order by committed_at desc,id desc limit 1;
      insert into erp.bs_case_components(
        bs_case_id,po_component_snapshot_id,work_component_id,completed_before_bs_qty,notes
      ) values(
        v_case.id,v_snapshot,(v_component->>'work_component_id')::uuid,
        coalesce(nullif(v_component->>'completed_before_bs_qty','')::integer,0),
        nullif(btrim(v_component->>'notes'),'')
      );
    end loop;
    update erp.bs_cases set updated_at=now() where id=v_case.id returning * into v_case;
  end if;
  v_response:=jsonb_build_object(
    'bs_case_id',v_case.id,'status',v_case.status,'cause_source',v_case.cause_source,
    'untracked_type',v_case.untracked_type,'legacy_reference',v_case.legacy_reference,
    'row_version',v_case.row_version,'component_count',(
      select count(*) from erp.bs_case_components where bs_case_id=v_case.id
    )
  );
  return erp._idempotency_complete('classify_bs_case_v2',p_client_request_id,v_response);
end
$function$;
alter function erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint) owner to postgres;

-- Preserve the legacy internal boundary for every existing flow. Only a live,
-- private capability row created by the CP5 facade may delegate through it.
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
  if exists(
    select 1
    from erp.bs_resolution_execution_context c
    where c.backend_pid=pg_backend_pid()
      and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key()
      and c.permission_key in(
        'production.bs_rework.create','production.bs_rework.post','production.bs_rework.reverse'
      )
      and erp.has_permission(c.permission_key)
  ) then return; end if;
  v_app_role:=erp.current_app_role();
  if v_app_role not in('OWNER','ADMIN','STAFF') then
    raise exception 'Internal ERP access required';
  end if;
end
$function$;

revoke all on function
  erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint),
  erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint),
  erp.create_manual_bs_case_v2(jsonb,uuid),
  erp.resolve_bs_case_disposition_v2(uuid,text,integer,numeric,uuid,timestamp with time zone,text,uuid,bigint),
  erp.resolve_laundry_claim_v2(uuid,text,text,uuid,bigint),
  erp.reverse_bs_disposition_v2(uuid,text,uuid,bigint),
  erp.reverse_laundry_claim_resolution(uuid,text),
  erp.reverse_rework_completion(uuid,text),
  erp.save_laundry_claim_v2(jsonb,uuid,bigint),
  erp.save_rework_order_v2(jsonb,uuid,bigint)
  from public,anon,authenticated;

revoke all on function
  erp.ensure_fg_accessory_cost_snapshot(uuid),
  erp.post_accessory_reimbursement_accrual(uuid),
  erp.post_fg_movement(uuid,uuid,uuid,text,text,integer,numeric,uuid,text,uuid,timestamp with time zone,text,boolean),
  erp.post_rework_completion(uuid),
  erp.propagate_conversion_hpp_for_po(uuid),
  erp.rebuild_po_hpp(uuid,text),
  erp.require_internal(),
  erp.sync_po_hpp_to_gl(uuid,date)
  from public,anon,authenticated;

revoke all on table
  erp.bs_cases,erp.bs_case_components,erp.bs_resolutions,
  erp.rework_orders,erp.rework_component_lines,erp.laundry_claims,
  erp.laundry_deliveries,erp.laundry_delivery_lines,
  erp.laundry_receipts,erp.laundry_receipt_lines,
  erp.bs_resolution_execution_context
  from public,anon,authenticated;

create function erp.get_bs_resolution_workspace_v1(
  p_filter text default 'ACTIVE',p_kind text default 'ALL',
  p_pattern_id uuid default null,p_query text default null,
  p_limit integer default 50,p_offset integer default 0
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare
  v_filter text:=upper(coalesce(nullif(btrim(p_filter),''),'ACTIVE'));
  v_kind text:=upper(coalesce(nullif(btrim(p_kind),''),'ALL'));
  v_query text:=lower(nullif(btrim(p_query),''));
  v_result jsonb;
begin
  perform erp.require_permission('production.bs_rework.view');
  if v_filter not in('ACTIVE','CLOSED','ALL') then
    raise exception 'filter must be ACTIVE, CLOSED, or ALL';
  end if;
  if v_kind not in('BS','LAUNDRY_CLAIM','ALL') then
    raise exception 'kind must be BS, LAUNDRY_CLAIM, or ALL';
  end if;
  if p_limit is null or p_limit<1 or p_limit>100 then
    raise exception 'limit must be between 1 and 100';
  end if;
  if p_offset is null or p_offset<0 then raise exception 'offset must be nonnegative'; end if;

  with base as (
    select
      'BS'::text kind,'BS:'||b.id::text case_key,b.id,b.bs_number number,
      b.status::text status,b.row_version,b.qty_pcs,
      coalesce(rs.resolved_qty,0)::integer resolved_qty,
      coalesce(rw.active_rework_qty,0)::integer active_rework_qty,
      greatest(b.qty_pcs-coalesce(rs.resolved_qty,0)-coalesce(rw.active_rework_qty,0),0)::integer available_qty,
      b.physical_at opened_at,
      b.po_id,po.po_number,pm.model_name,b.cutting_group_id,cg.group_number,
      case when cg.pattern_id is null then '[]'::jsonb else jsonb_build_array(jsonb_build_object(
        'id',cg.pattern_id,'code',cg.pattern_code_snapshot,
        'revision',cg.pattern_revision_snapshot,'name',cg.pattern_name_snapshot
      )) end patterns,
      b.product_id,p.sku,p.product_name,
      b.responsible_contractor_id,ct.contractor_name,
      b.responsible_vendor_id,lv.vendor_name,
      b.detected_at_stage::text detected_stage,b.cause_source::text cause_source,
      b.untracked_type::text untracked_type,
      null::text claim_type,0::numeric compensation_amount,
      source_receipt.delivery_id laundry_delivery_id,
      b.source_laundry_receipt_line_id laundry_receipt_line_id,
      b.legacy_reference,b.notes,
      case when b.status='ON_HOLD' then 'RELEASE_HOLD'
           when b.status in('OPEN','PARTIAL') then 'START_REWORK_OR_DISPOSITION'
           when b.status='IN_REWORK' then 'COMPLETE_REWORK'
           else 'VIEW_OR_REVERSE' end next_action,
      (b.status in('RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED')) is_closed,
      lower(concat_ws(' ',b.bs_number,po.po_number,pm.model_name,cg.group_number,
        cg.pattern_code_snapshot,cg.pattern_revision_snapshot,cg.pattern_name_snapshot,
        p.sku,p.product_name,ct.contractor_name,lv.vendor_name,b.status,
        b.detected_at_stage,b.cause_source,b.untracked_type,b.legacy_reference,b.notes)) search_text,
      coalesce((
        select jsonb_agg(jsonb_build_object(
          'id',bc.id,'work_component_id',bc.work_component_id,
          'code',wc.component_code,'name',wc.component_name,'category',wc.component_category,
          'completed_before_bs_qty',bc.completed_before_bs_qty,
          'lifetime_newly_completed_qty',bc.lifetime_newly_completed_qty,
          'lifetime_paid_qty',bc.lifetime_paid_qty,'notes',bc.notes
        ) order by wc.sequence_default,wc.component_code,bc.id)
        from erp.bs_case_components bc
        join erp.work_components wc on wc.id=bc.work_component_id
        where bc.bs_case_id=b.id
      ),'[]'::jsonb) components,
      coalesce((
        select jsonb_agg(jsonb_build_object(
          'id',br.id,'resolution_type',br.resolution_type,'qty_pcs',br.qty_pcs,
          'compensation_amount',br.compensation_amount,
          'responsible_contractor_id',br.responsible_contractor_id,
          'responsible_vendor_id',br.responsible_vendor_id,
          'source_rework_order_id',br.source_rework_order_id,
          'source_laundry_claim_id',br.source_laundry_claim_id,
          'physical_at',br.physical_at,'notes',br.notes,'created_at',br.created_at
        ) order by br.physical_at desc,br.created_at desc,br.id desc)
        from erp.bs_resolutions br where br.bs_case_id=b.id
      ),'[]'::jsonb) resolutions,
      coalesce((
        select jsonb_agg(jsonb_build_object(
          'id',ro.id,'rework_number',ro.rework_number,
          'destination_type',ro.destination_type,'contractor_id',ro.contractor_id,
          'contractor_name',rc.contractor_name,'vendor_id',ro.vendor_id,
          'vendor_name',rv.vendor_name,'qty_sent',ro.qty_sent,
          'qty_good_returned',ro.qty_good_returned,'qty_bs_returned',ro.qty_bs_returned,
          'physical_sent_at',ro.physical_sent_at,'completed_at',ro.completed_at,
          'status',ro.status,'cost_posted',ro.cost_posted,
          'return_fg_location_id',ro.return_fg_location_id,
          'return_fg_location_name',rl.location_name,'good_fg_lot_id',ro.good_fg_lot_id,
          'row_version',ro.row_version,'notes',ro.notes,
          'components',coalesce((
            select jsonb_agg(jsonb_build_object(
              'id',rcl.id,'bs_case_component_id',rcl.bs_case_component_id,
              'work_component_id',bcc.work_component_id,'component_code',rwc.component_code,
              'component_name',rwc.component_name,'qty_performed',rcl.qty_performed,
              'qty_newly_payable',rcl.qty_newly_payable,'rate_snapshot',rcl.rate_snapshot,
              'amount_payable',rcl.amount_payable,'rate_basis',rcl.rate_basis,'notes',rcl.notes
            ) order by rwc.sequence_default,rwc.component_code,rcl.id)
            from erp.rework_component_lines rcl
            join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
            join erp.work_components rwc on rwc.id=bcc.work_component_id
            where rcl.rework_order_id=ro.id
          ),'[]'::jsonb)
        ) order by ro.physical_sent_at desc,ro.created_at desc,ro.id desc)
        from erp.rework_orders ro
        left join erp.contractors rc on rc.id=ro.contractor_id
        left join erp.laundry_vendors rv on rv.id=ro.vendor_id
        left join erp.locations rl on rl.id=ro.return_fg_location_id
        where ro.bs_case_id=b.id
      ),'[]'::jsonb) rework_orders,
      coalesce((
        select jsonb_agg(jsonb_build_object(
          'id',he.id,'action',he.action,'previous_status',he.previous_status,
          'resulting_status',he.resulting_status,'reason',he.reason,
          'physical_at',he.physical_at,'actor_id',he.actor_id,
          'actor_name',hu.full_name,'created_at',he.created_at
        ) order by he.physical_at desc,he.created_at desc,he.id desc)
        from erp.bs_case_hold_events he
        left join erp.app_users hu on hu.id=he.actor_id
        where he.bs_case_id=b.id
      ),'[]'::jsonb) hold_events
    from erp.bs_cases b
    left join erp.production_orders po on po.id=b.po_id
    left join erp.product_models pm on pm.id=po.model_id
    left join erp.cutting_groups cg on cg.id=b.cutting_group_id
    left join erp.laundry_receipt_lines source_receipt_line
      on source_receipt_line.id=b.source_laundry_receipt_line_id
    left join erp.laundry_receipts source_receipt
      on source_receipt.id=source_receipt_line.receipt_id
    left join erp.products p on p.id=b.product_id
    left join erp.contractors ct on ct.id=b.responsible_contractor_id
    left join erp.laundry_vendors lv on lv.id=b.responsible_vendor_id
    left join lateral(
      select coalesce(sum(x.qty_pcs),0)::integer resolved_qty
      from erp.bs_resolutions x where x.bs_case_id=b.id
    ) rs on true
    left join lateral(
      select coalesce(sum(x.qty_sent),0)::integer active_rework_qty
      from erp.rework_orders x
      where x.bs_case_id=b.id and x.status in('OPEN','IN_PROGRESS','PARTIAL')
    ) rw on true
    where (p_pattern_id is null or cg.pattern_id=p_pattern_id)

    union all

    select
      'LAUNDRY_CLAIM'::text kind,'LAUNDRY_CLAIM:'||c.id::text case_key,
      c.id,c.claim_number number,c.status::text status,c.row_version,c.qty_claimed qty_pcs,
      case when c.status in('SETTLED','WRITTEN_OFF') then c.qty_claimed else 0 end resolved_qty,
      0::integer active_rework_qty,
      case when c.status in('SETTLED','WRITTEN_OFF','REJECTED') then 0 else c.qty_claimed end available_qty,
      c.opened_at,ld.po_id,po.po_number,pm.model_name,null::uuid cutting_group_id,
      null::text group_number,coalesce(cp.patterns,'[]'::jsonb) patterns,
      null::uuid product_id,null::text sku,null::text product_name,
      null::uuid responsible_contractor_id,null::text contractor_name,
      c.vendor_id responsible_vendor_id,lv.vendor_name,
      'LAUNDRY'::text detected_stage,'LAUNDRY'::text cause_source,
      null::text untracked_type,c.claim_type::text claim_type,c.compensation_amount,
      ld.id laundry_delivery_id,c.receipt_line_id laundry_receipt_line_id,
      null::text legacy_reference,c.notes,
      case when c.status in('OPEN','ACCEPTED') then 'RESOLVE_CLAIM' else 'VIEW_OR_REVERSE' end next_action,
      (c.status in('SETTLED','WRITTEN_OFF','REJECTED')) is_closed,
      lower(concat_ws(' ',c.claim_number,c.claim_type,c.status,ld.delivery_number,
        po.po_number,pm.model_name,lv.vendor_name,c.qty_claimed,c.compensation_amount,
        cp.search_patterns,c.notes)) search_text,
      '[]'::jsonb components,
      coalesce((
        select jsonb_agg(jsonb_build_object(
          'id',br.id,'bs_case_id',br.bs_case_id,'resolution_type',br.resolution_type,
          'qty_pcs',br.qty_pcs,'compensation_amount',br.compensation_amount,
          'source_laundry_claim_id',br.source_laundry_claim_id,
          'physical_at',br.physical_at,'notes',br.notes,'created_at',br.created_at
        ) order by br.physical_at desc,br.created_at desc,br.id desc)
        from erp.bs_resolutions br where br.source_laundry_claim_id=c.id
      ),'[]'::jsonb) resolutions,
      '[]'::jsonb rework_orders,'[]'::jsonb hold_events
    from erp.laundry_claims c
    left join erp.laundry_receipt_lines lrl on lrl.id=c.receipt_line_id
    left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    left join erp.laundry_deliveries ld on ld.id=coalesce(c.delivery_id,lr.delivery_id)
    left join erp.production_orders po on po.id=ld.po_id
    left join erp.product_models pm on pm.id=po.model_id
    left join erp.laundry_vendors lv on lv.id=c.vendor_id
    left join lateral(
      select jsonb_agg(jsonb_build_object(
          'id',z.pattern_id,'code',z.pattern_code_snapshot,
          'revision',z.pattern_revision_snapshot,'name',z.pattern_name_snapshot
        ) order by z.pattern_code_snapshot,z.pattern_revision_snapshot,z.pattern_id) patterns,
        string_agg(concat_ws(' ',z.pattern_code_snapshot,z.pattern_revision_snapshot,z.pattern_name_snapshot),' ') search_patterns
      from(
        select distinct cg.pattern_id,cg.pattern_code_snapshot,
          cg.pattern_revision_snapshot,cg.pattern_name_snapshot
        from erp.laundry_delivery_lines dl
        join erp.cutting_groups cg on cg.id=dl.cutting_group_id
        where cg.pattern_id is not null and (
          (c.receipt_line_id is not null and dl.id=lrl.delivery_line_id)
          or (c.receipt_line_id is null and dl.delivery_id=ld.id)
        )
      ) z
    ) cp on true
    where p_pattern_id is null or exists(
      select 1 from erp.laundry_delivery_lines fdl
      join erp.cutting_groups fcg on fcg.id=fdl.cutting_group_id
      where fcg.pattern_id=p_pattern_id and (
        (c.receipt_line_id is not null and fdl.id=lrl.delivery_line_id)
        or (c.receipt_line_id is null and fdl.delivery_id=ld.id)
      )
    )
  ), filtered as (
    select * from base
    where (v_kind='ALL' or kind=v_kind)
      and (v_filter='ALL' or (v_filter='ACTIVE' and not is_closed) or (v_filter='CLOSED' and is_closed))
      and (v_query is null or search_text like '%'||v_query||'%')
  ), page as (
    select * from filtered
    order by is_closed,opened_at desc,number,id
    limit p_limit offset p_offset
  )
  select jsonb_build_object(
    'filter',v_filter,'kind',v_kind,'pattern_id',p_pattern_id,'query',v_query,
    'limit',p_limit,'offset',p_offset,'total',(select count(*) from filtered),
    'lookups',jsonb_build_object(
      'contractors',coalesce((select jsonb_agg(jsonb_build_object(
        'id',x.id,'code',x.contractor_code,'name',x.contractor_name
      ) order by x.contractor_name,x.contractor_code,x.id)
        from erp.contractors x where x.is_active and x.contractor_type='MANDOR'),'[]'::jsonb),
      'vendors',coalesce((select jsonb_agg(jsonb_build_object(
        'id',x.id,'code',x.vendor_code,'name',x.vendor_name
      ) order by x.vendor_name,x.vendor_code,x.id)
        from erp.laundry_vendors x where x.is_active),'[]'::jsonb),
      'fg_locations',coalesce((select jsonb_agg(jsonb_build_object(
        'id',x.id,'code',x.location_code,'name',x.location_name
      ) order by x.location_name,x.location_code,x.id)
        from erp.locations x where x.is_active and x.location_type='FG_WAREHOUSE'),'[]'::jsonb),
      'work_components',coalesce((select jsonb_agg(jsonb_build_object(
        'id',x.id,'code',x.component_code,'name',x.component_name,'category',x.component_category
      ) order by x.sequence_default,x.component_code,x.id)
        from erp.work_components x where x.is_active),'[]'::jsonb),
      'products',coalesce((select jsonb_agg(jsonb_build_object(
        'id',x.id,'sku',x.sku,'name',x.product_name
      ) order by x.sku,x.id)
        from erp.products x where x.is_active and x.effective_to is null),'[]'::jsonb),
      'laundry_sources',coalesce((select jsonb_agg(jsonb_build_object(
        'id',s.id,'number',s.delivery_number,'vendor_id',s.vendor_id,
        'vendor_name',s.vendor_name,'po_number',s.po_number,
        'physical_at',s.physical_at,'qty_sent_pcs',s.qty_sent_pcs,
        'qty_claimable_pcs',s.qty_claimable_pcs
      ) order by s.physical_at desc,s.delivery_number,s.id)
        from(
          select d.id,d.delivery_number,d.vendor_id,v.vendor_name,po.po_number,
            d.physical_at,sum(dl.qty_sent_pcs)::integer qty_sent_pcs,
            greatest(
              sum(dl.qty_sent_pcs)
              -coalesce((
                select sum(rl.qty_good_received+rl.qty_bs_laundry)
                from erp.laundry_receipt_lines rl
                join erp.laundry_receipts r on r.id=rl.receipt_id
                where r.delivery_id=d.id and r.status='POSTED'
              ),0)
              -coalesce((
                select sum(c.qty_claimed) from erp.laundry_claims c
                where c.delivery_id=d.id and c.claim_type in('MISSING','STUCK')
                  and c.status<>'REJECTED'
              ),0),0
            )::integer qty_claimable_pcs
          from erp.laundry_deliveries d
          join erp.laundry_delivery_lines dl on dl.delivery_id=d.id
          join erp.laundry_vendors v on v.id=d.vendor_id
          join erp.production_orders po on po.id=d.po_id
          where d.status in('SENT','PARTIAL_RETURN','RETURNED','CLOSED')
          group by d.id,d.delivery_number,d.vendor_id,v.vendor_name,po.po_number,d.physical_at
          order by d.physical_at desc,d.id limit 100
        ) s),'[]'::jsonb),
      'laundry_receipt_sources',coalesce((select jsonb_agg(jsonb_build_object(
        'id',s.id,'receipt_id',s.receipt_id,'number',s.receipt_number,
        'delivery_id',s.delivery_id,'delivery_number',s.delivery_number,
        'vendor_id',s.vendor_id,'vendor_name',s.vendor_name,'po_number',s.po_number,
        'physical_at',s.physical_at,'qty_bs_laundry',s.qty_bs_laundry,
        'qty_claimable_pcs',s.qty_claimable_pcs
      ) order by s.physical_at desc,s.receipt_number,s.id)
        from(
          select rl.id,r.id receipt_id,r.receipt_number,d.id delivery_id,
            d.delivery_number,d.vendor_id,v.vendor_name,po.po_number,r.physical_at,
            rl.qty_bs_laundry,
            greatest(rl.qty_bs_laundry-coalesce((
              select sum(c.qty_claimed) from erp.laundry_claims c
              where c.receipt_line_id=rl.id and c.claim_type='DAMAGE'
                and c.status<>'REJECTED'
            ),0),0)::integer qty_claimable_pcs
          from erp.laundry_receipt_lines rl
          join erp.laundry_receipts r on r.id=rl.receipt_id and r.status='POSTED'
          join erp.laundry_deliveries d on d.id=r.delivery_id
          join erp.laundry_vendors v on v.id=d.vendor_id
          join erp.production_orders po on po.id=d.po_id
          where rl.qty_bs_laundry>0
            and rl.qty_bs_laundry>coalesce((
              select sum(c.qty_claimed) from erp.laundry_claims c
              where c.receipt_line_id=rl.id and c.claim_type='DAMAGE'
                and c.status<>'REJECTED'
            ),0)
          order by r.physical_at desc,r.id desc,rl.id desc limit 100
        ) s where s.qty_claimable_pcs>0),'[]'::jsonb),
      'settled_claims',coalesce((select jsonb_agg(jsonb_build_object(
        'id',s.id,'number',s.claim_number,'vendor_id',s.vendor_id,
        'vendor_name',s.vendor_name,'delivery_id',s.delivery_id,
        'receipt_line_id',s.receipt_line_id,'qty_claimed',s.qty_claimed,
        'compensation_amount',s.compensation_amount,
        'available_qty',s.available_qty,'available_amount',s.available_amount
      ) order by s.resolved_at desc,s.claim_number,s.id)
        from(
          select c.id,c.claim_number,c.vendor_id,v.vendor_name,
            coalesce(c.delivery_id,claim_receipt.delivery_id) delivery_id,
            c.receipt_line_id,c.qty_claimed,c.compensation_amount,c.resolved_at,
            greatest(c.qty_claimed-coalesce(u.used_qty,0),0)::integer available_qty,
            greatest(c.compensation_amount-coalesce(u.used_amount,0),0)::numeric available_amount
          from erp.laundry_claims c
          join erp.laundry_vendors v on v.id=c.vendor_id
          left join erp.laundry_receipt_lines claim_receipt_line
            on claim_receipt_line.id=c.receipt_line_id
          left join erp.laundry_receipts claim_receipt
            on claim_receipt.id=claim_receipt_line.receipt_id
          left join lateral(
            select coalesce(sum(br.qty_pcs),0)::integer used_qty,
              coalesce(sum(br.compensation_amount),0)::numeric used_amount
            from erp.bs_resolutions br where br.source_laundry_claim_id=c.id
          ) u on true
          where c.status='SETTLED'
            and c.qty_claimed>coalesce(u.used_qty,0)
            and c.compensation_amount>coalesce(u.used_amount,0)
          order by c.resolved_at desc,c.id desc limit 100
        ) s where s.available_qty>0 and s.available_amount>0),'[]'::jsonb)
    ),
    'rows',coalesce((select jsonb_agg(jsonb_build_object(
      'case_key',x.case_key,'kind',x.kind,'id',x.id,'number',x.number,
      'status',x.status,'row_version',x.row_version,'qty_pcs',x.qty_pcs,
      'resolved_qty',x.resolved_qty,'active_rework_qty',x.active_rework_qty,
      'available_qty',x.available_qty,'opened_at',x.opened_at,
      'po_id',x.po_id,'po_number',x.po_number,'model_name',x.model_name,
      'cutting_group_id',x.cutting_group_id,'group_number',x.group_number,
      'patterns',x.patterns,'product_id',x.product_id,'sku',x.sku,
      'product_name',x.product_name,
      'responsible_contractor_id',x.responsible_contractor_id,
      'contractor_name',x.contractor_name,
      'responsible_vendor_id',x.responsible_vendor_id,'vendor_name',x.vendor_name,
      'detected_stage',x.detected_stage,'cause_source',x.cause_source,
      'untracked_type',x.untracked_type,'claim_type',x.claim_type,
      'compensation_amount',x.compensation_amount,
      'laundry_delivery_id',x.laundry_delivery_id,
      'laundry_receipt_line_id',x.laundry_receipt_line_id,
      'legacy_reference',x.legacy_reference,'notes',x.notes,
      'next_action',x.next_action,'is_closed',x.is_closed,
      'components',x.components,'resolutions',x.resolutions,
      'rework_orders',x.rework_orders,'hold_events',x.hold_events
    ) order by x.is_closed,x.opened_at desc,x.number,x.id) from page x),'[]'::jsonb)
  ) into v_result;
  return v_result;
end
$function$;

create function erp.save_bs_resolution_action_v1(
  p_action text,p_payload jsonb,p_client_request_id uuid,
  p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_action text:=upper(coalesce(nullif(btrim(p_action),''),''));
  v_permission text;
  v_hash text;
  v_cached jsonb;
  v_nested jsonb;
  v_response jsonb;
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_physical_at timestamptz:=nullif(p_payload->>'physical_at','')::timestamptz;
  v_case erp.bs_cases%rowtype;
  v_order erp.rework_orders%rowtype;
  v_claim erp.laundry_claims%rowtype;
  v_actor uuid;
  v_resolved integer;
  v_active integer;
  v_previous_status text;
  v_last_hold_at timestamptz;
begin
  if v_action not in(
    'CREATE_MANUAL_BS','CLASSIFY_BS','SAVE_REWORK','COMPLETE_REWORK',
    'DISPOSE_BS','HOLD_BS','RELEASE_HOLD','REVERSE_DISPOSITION',
    'REVERSE_REWORK_COMPLETION','SAVE_CLAIM','RESOLVE_CLAIM',
    'REVERSE_CLAIM_RESOLUTION'
  ) then raise exception 'Unsupported CP5 action'; end if;

  if v_action in('CREATE_MANUAL_BS','CLASSIFY_BS','SAVE_REWORK','SAVE_CLAIM') then
    v_permission:='production.bs_rework.create';
  elsif v_action in('COMPLETE_REWORK','DISPOSE_BS','HOLD_BS','RELEASE_HOLD','RESOLVE_CLAIM') then
    v_permission:='production.bs_rework.post';
  else
    v_permission:='production.bs_rework.reverse';
  end if;
  perform erp.require_permission(v_permission);

  if p_payload is null or jsonb_typeof(p_payload)<>'object' then
    raise exception 'payload must be a JSON object';
  end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'action',v_action,'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('save_bs_resolution_action_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  insert into erp.bs_resolution_execution_context(
    backend_pid,transaction_id,actor_key,action,permission_key
  ) values(
    pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,v_permission
  );

  case v_action
    when 'CREATE_MANUAL_BS' then
      if p_expected_version is not null then
        raise exception 'expected_version must be null when creating manual BS';
      end if;
      v_nested:=erp.create_manual_bs_case_v2(p_payload,p_client_request_id);

    when 'CLASSIFY_BS' then
      v_nested:=erp.classify_bs_case_v2(
        (p_payload->>'bs_case_id')::uuid,p_payload,p_client_request_id,p_expected_version
      );

    when 'SAVE_REWORK' then
      if nullif(p_payload->>'id','') is null then
        select * into v_case from erp.bs_cases
        where id=(p_payload->>'bs_case_id')::uuid for update;
        if v_case.id is null then raise exception 'BS case not found'; end if;
        if v_case.status not in('OPEN','PARTIAL') then
          raise exception 'Release HOLD or finish the active lifecycle before creating rework';
        end if;
      end if;
      v_nested:=erp.save_rework_order_v2(p_payload,p_client_request_id,p_expected_version);

    when 'COMPLETE_REWORK' then
      v_nested:=erp.complete_rework_order_v2(
        (p_payload->>'rework_order_id')::uuid,
        coalesce(nullif(p_payload->>'qty_good','')::integer,0),
        coalesce(nullif(p_payload->>'qty_bs','')::integer,0),
        nullif(p_payload->>'completed_at','')::timestamptz,
        nullif(p_payload->>'return_fg_location_id','')::uuid,
        p_payload->>'change_reason',p_client_request_id,p_expected_version
      );
      -- The legacy poster labels an all-BS return PARTIAL even when no piece
      -- was actually resolved. Re-run the canonical status reducer and return
      -- its fresh state so the CP5 boundary never leaks that stale label.
      select * into v_order from erp.rework_orders
      where id=(p_payload->>'rework_order_id')::uuid;
      perform erp.refresh_bs_case_status(v_order.bs_case_id);
      select * into v_case from erp.bs_cases where id=v_order.bs_case_id;
      v_nested:=v_nested||jsonb_build_object(
        'bs_case_status',v_case.status,'bs_case_row_version',v_case.row_version
      );

    when 'DISPOSE_BS' then
      v_nested:=erp.resolve_bs_case_disposition_v2(
        (p_payload->>'bs_case_id')::uuid,p_payload->>'resolution_type',
        coalesce(nullif(p_payload->>'qty_pcs','')::integer,0),
        coalesce(nullif(p_payload->>'compensation_amount','')::numeric,0),
        nullif(p_payload->>'source_laundry_claim_id','')::uuid,
        nullif(p_payload->>'physical_at','')::timestamptz,
        p_payload->>'change_reason',p_client_request_id,p_expected_version
      );

    when 'HOLD_BS' then
      if p_expected_version is null then raise exception 'expected_version is required'; end if;
      if v_reason is null then raise exception 'change_reason is required'; end if;
      if v_physical_at is null or v_physical_at>clock_timestamp()+interval '5 minutes' then
        raise exception 'Valid non-future physical_at is required';
      end if;
      select * into v_case from erp.bs_cases
      where id=(p_payload->>'bs_case_id')::uuid for update;
      if v_case.id is null then raise exception 'BS case not found'; end if;
      if v_case.row_version<>p_expected_version then
        raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_case.row_version;
      end if;
      if v_case.status not in('OPEN','PARTIAL') then
        raise exception 'Only unresolved BS without an active lifecycle can be put on HOLD';
      end if;
      if v_physical_at<v_case.physical_at then raise exception 'HOLD cannot predate BS detection'; end if;
      select coalesce(sum(x.qty_pcs),0)::integer into v_resolved
      from erp.bs_resolutions x where x.bs_case_id=v_case.id;
      select coalesce(sum(x.qty_sent),0)::integer into v_active
      from erp.rework_orders x
      where x.bs_case_id=v_case.id and x.status in('OPEN','IN_PROGRESS','PARTIAL');
      if v_active>0 then raise exception 'Active rework must be completed or cancelled before HOLD'; end if;
      if v_resolved>=v_case.qty_pcs then raise exception 'Fully resolved BS cannot be put on HOLD'; end if;
      v_actor:=erp.current_app_user_id();
      perform set_config('app.change_reason',v_reason,true);
      perform set_config('app.bs_hold_transition','HOLD',true);
      v_previous_status:=v_case.status;
      update erp.bs_cases set status='ON_HOLD',updated_at=clock_timestamp()
      where id=v_case.id returning * into v_case;
      perform set_config('app.bs_hold_transition','',true);
      insert into erp.bs_case_hold_events(
        bs_case_id,action,previous_status,resulting_status,reason,
        physical_at,actor_id,client_request_id
      ) values(
        v_case.id,'HOLD',v_previous_status,v_case.status,v_reason,
        v_physical_at,v_actor,p_client_request_id
      );
      v_nested:=jsonb_build_object(
        'bs_case_id',v_case.id,'status',v_case.status,'row_version',v_case.row_version,
        'physical_at',v_physical_at
      );

    when 'RELEASE_HOLD' then
      if p_expected_version is null then raise exception 'expected_version is required'; end if;
      if v_reason is null then raise exception 'change_reason is required'; end if;
      if v_physical_at is null or v_physical_at>clock_timestamp()+interval '5 minutes' then
        raise exception 'Valid non-future physical_at is required';
      end if;
      select * into v_case from erp.bs_cases
      where id=(p_payload->>'bs_case_id')::uuid for update;
      if v_case.id is null then raise exception 'BS case not found'; end if;
      if v_case.row_version<>p_expected_version then
        raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_case.row_version;
      end if;
      if v_case.status<>'ON_HOLD' then raise exception 'Only ON_HOLD BS can be released'; end if;
      select max(x.physical_at) into v_last_hold_at
      from erp.bs_case_hold_events x where x.bs_case_id=v_case.id;
      if v_physical_at<coalesce(v_last_hold_at,v_case.physical_at) then
        raise exception 'HOLD release cannot predate the latest HOLD event';
      end if;
      v_actor:=erp.current_app_user_id();
      perform set_config('app.change_reason',v_reason,true);
      perform set_config('app.bs_hold_transition','RELEASE',true);
      v_previous_status:=v_case.status;
      perform erp.refresh_bs_case_status(v_case.id);
      select * into v_case from erp.bs_cases where id=v_case.id;
      perform set_config('app.bs_hold_transition','',true);
      insert into erp.bs_case_hold_events(
        bs_case_id,action,previous_status,resulting_status,reason,
        physical_at,actor_id,client_request_id
      ) values(
        v_case.id,'RELEASE',v_previous_status,v_case.status,v_reason,
        v_physical_at,v_actor,p_client_request_id
      );
      v_nested:=jsonb_build_object(
        'bs_case_id',v_case.id,'status',v_case.status,'row_version',v_case.row_version,
        'physical_at',v_physical_at
      );

    when 'REVERSE_DISPOSITION' then
      v_nested:=erp.reverse_bs_disposition_v2(
        (p_payload->>'resolution_id')::uuid,p_payload->>'change_reason',
        p_client_request_id,p_expected_version
      );

    when 'REVERSE_REWORK_COMPLETION' then
      if p_expected_version is null then raise exception 'expected_version is required'; end if;
      if v_reason is null then raise exception 'change_reason is required'; end if;
      select * into v_order from erp.rework_orders
      where id=(p_payload->>'rework_order_id')::uuid for update;
      if v_order.id is null then raise exception 'Rework order not found'; end if;
      if v_order.row_version<>p_expected_version then
        raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_order.row_version;
      end if;
      perform erp.reverse_rework_completion(v_order.id,v_reason);
      select * into v_order from erp.rework_orders where id=v_order.id;
      select * into v_case from erp.bs_cases where id=v_order.bs_case_id;
      v_nested:=jsonb_build_object(
        'rework_order_id',v_order.id,'status',v_order.status,
        'row_version',v_order.row_version,'bs_case_id',v_case.id,
        'bs_case_status',v_case.status,'bs_case_row_version',v_case.row_version
      );

    when 'SAVE_CLAIM' then
      v_nested:=erp.save_laundry_claim_v2(p_payload,p_client_request_id,p_expected_version);

    when 'RESOLVE_CLAIM' then
      v_nested:=erp.resolve_laundry_claim_v2(
        (p_payload->>'laundry_claim_id')::uuid,p_payload->>'resolution',
        p_payload->>'change_reason',p_client_request_id,p_expected_version
      );

    when 'REVERSE_CLAIM_RESOLUTION' then
      if p_expected_version is null then raise exception 'expected_version is required'; end if;
      if v_reason is null then raise exception 'change_reason is required'; end if;
      select * into v_claim from erp.laundry_claims
      where id=(p_payload->>'laundry_claim_id')::uuid for update;
      if v_claim.id is null then raise exception 'Laundry claim not found'; end if;
      if v_claim.row_version<>p_expected_version then
        raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_claim.row_version;
      end if;
      perform erp.reverse_laundry_claim_resolution(v_claim.id,v_reason);
      select * into v_claim from erp.laundry_claims where id=v_claim.id;
      v_nested:=jsonb_build_object(
        'laundry_claim_id',v_claim.id,'status',v_claim.status,
        'row_version',v_claim.row_version
      );
  end case;

  delete from erp.bs_resolution_execution_context
  where backend_pid=pg_backend_pid()
    and transaction_id=txid_current()
    and actor_key=erp._idempotency_actor_key();
  if not found then raise exception 'CP5 execution context was lost before completion'; end if;
  v_response:=jsonb_build_object('action',v_action,'result',v_nested);
  return erp._idempotency_complete('save_bs_resolution_action_v1',p_client_request_id,v_response);
end
$function$;

revoke all on function
  erp.get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer),
  erp.save_bs_resolution_action_v1(text,jsonb,uuid,bigint)
  from public,anon,authenticated,service_role;

create function public.erp_get_bs_resolution_workspace_v1(
  p_filter text default 'ACTIVE',p_kind text default 'ALL',
  p_pattern_id uuid default null,p_query text default null,
  p_limit integer default 50,p_offset integer default 0
)
returns jsonb language plpgsql stable security definer set search_path=''
as $function$
begin
  return erp.get_bs_resolution_workspace_v1(
    p_filter,p_kind,p_pattern_id,p_query,p_limit,p_offset
  );
end
$function$;

create function public.erp_save_bs_resolution_action_v1(
  p_action text,p_payload jsonb,p_client_request_id uuid,
  p_expected_version bigint default null
)
returns jsonb language plpgsql security definer set search_path=''
as $function$
begin
  return erp.save_bs_resolution_action_v1(
    p_action,p_payload,p_client_request_id,p_expected_version
  );
end
$function$;

revoke all on function
  public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer),
  public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)
  from public,anon,authenticated,service_role;
grant execute on function
  public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer),
  public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)
  to authenticated,service_role;

comment on function public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer) is
  'CP5 guarded BS/Rework/Laundry-claim workspace with server-side Pattern, lifecycle, and search filters.';
comment on function public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint) is
  'CP5 permission-checked dispatcher over canonical BS classification, rework/rewash, HOLD, disposition, claim, completion, and reversal functions.';

do $post_guard$
declare v_bad text;v_status_constraint text;v_internal_def text;
begin
  if exists(
    select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where p.oid in(
      'erp.get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)'::regprocedure,
      'erp.save_bs_resolution_action_v1(text,jsonb,uuid,bigint)'::regprocedure,
      'erp.require_internal()'::regprocedure,
      'public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)'::regprocedure,
      'public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)'::regprocedure
    ) and(
      not p.prosecdef or p.proconfig is distinct from array['search_path=""']::text[]
      or pg_get_userbyid(p.proowner)<>'postgres'
    )
  ) then raise exception 'ERP v2.6.19 post guard: definer/search_path/owner contract failed'; end if;

  if has_function_privilege('anon','public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','EXECUTE')
     or has_function_privilege('anon','public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)','EXECUTE') then
    raise exception 'ERP v2.6.19 post guard: public facade ACL failed';
  end if;
  if has_function_privilege('authenticated','erp.require_internal()','EXECUTE')
     or has_function_privilege('authenticated','erp.create_manual_bs_case_v2(jsonb,uuid)','EXECUTE')
     or has_function_privilege('authenticated','erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.save_rework_order_v2(jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.resolve_bs_case_disposition_v2(uuid,text,integer,numeric,uuid,timestamp with time zone,text,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.reverse_bs_disposition_v2(uuid,text,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.save_laundry_claim_v2(jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.resolve_laundry_claim_v2(uuid,text,text,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.reverse_rework_completion(uuid,text)','EXECUTE')
     or has_function_privilege('authenticated','erp.reverse_laundry_claim_resolution(uuid,text)','EXECUTE') then
    raise exception 'ERP v2.6.19 post guard: private CP5 action remains directly executable';
  end if;

  if exists(
    select 1 from (values
      ('erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint)','c59e0fc2f14934d3947ce5cc7f3c78bb'),
      ('erp.create_manual_bs_case_v2(jsonb,uuid)','01f6aab85855fd121587a107af171489'),
      ('erp.ensure_fg_accessory_cost_snapshot(uuid)','aae034da6699fb2f7b4c5f817e8d9f50'),
      ('erp.post_accessory_reimbursement_accrual(uuid)','36804117ef5af6f018c199518bd2e915'),
      ('erp.post_fg_movement(uuid,uuid,uuid,text,text,integer,numeric,uuid,text,uuid,timestamp with time zone,text,boolean)','63f4aabc5cf34afd0765017c578e4416'),
      ('erp.post_rework_completion(uuid)','bf610b5a00636297eab1f640bdc5da8c'),
      ('erp.propagate_conversion_hpp_for_po(uuid)','f3c86a2a1d282927d9c9e1af1404fa93'),
      ('erp.rebuild_po_hpp(uuid,text)','bf5593c35375abb35c0c6d531ee375e6'),
      ('erp.resolve_bs_case_disposition_v2(uuid,text,integer,numeric,uuid,timestamp with time zone,text,uuid,bigint)','63da04a3aea6a6f5a4c5f956358e3f61'),
      ('erp.save_laundry_claim_v2(jsonb,uuid,bigint)','3ce81f61adc7d56c5bd9d048dafda180'),
      ('erp.save_rework_order_v2(jsonb,uuid,bigint)','d4f297f43858bb3c819c9cacec2972ab'),
      ('erp.sync_po_hpp_to_gl(uuid,date)','0ecc997982964a03e0d8c93efcb9ddcc')
    ) expected(identity,expected_md5)
    where md5(pg_get_functiondef(to_regprocedure(expected.identity))) is distinct from expected.expected_md5
  ) then raise exception 'ERP v2.6.19 post guard: a legacy private function was weakened or drifted'; end if;
  if position(
       'untracked_type=case when v_cause=''UNKNOWN'' then untracked_type else null end'
       in pg_get_functiondef('erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)'::regprocedure)
     )=0
     or position(
       '''untracked_type'',v_case.untracked_type,''legacy_reference'',v_case.legacy_reference'
       in pg_get_functiondef('erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)'::regprocedure)
     )=0 then
    raise exception 'ERP v2.6.19 post guard: manual BS classification recovery is incomplete';
  end if;
  select pg_get_functiondef('erp.require_internal()'::regprocedure) into v_internal_def;
  if v_internal_def not like '%bs_resolution_execution_context%'
     or v_internal_def not like '%cutting_bridge_execution_context%'
     or v_internal_def not like '%production.cutting.post%'
     or v_internal_def not like '%transaction_id=txid_current()%'
     or v_internal_def not like '%actor_key=erp._idempotency_actor_key()%'
     or v_internal_def not like '%erp.has_permission(c.permission_key)%' then
    raise exception 'ERP v2.6.19 post guard: scoped internal delegation is incomplete';
  end if;

  if has_table_privilege('anon','erp.bs_cases','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.bs_cases','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.bs_resolutions','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.bs_resolutions','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.rework_orders','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.rework_orders','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.laundry_claims','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.laundry_claims','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.bs_case_hold_events','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.bs_case_hold_events','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.bs_resolution_execution_context','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.bs_resolution_execution_context','SELECT,INSERT,UPDATE,DELETE') then
    raise exception 'ERP v2.6.19 post guard: browser role retains direct CP5 table access';
  end if;

  select pg_get_constraintdef(c.oid,true) into v_status_constraint
  from pg_constraint c
  where c.conrelid='erp.bs_cases'::regclass and c.conname='bs_cases_status_check';
  if v_status_constraint not like '%ON_HOLD%' then
    raise exception 'ERP v2.6.19 post guard: ON_HOLD status constraint is missing';
  end if;
  if not exists(
    select 1 from pg_trigger where tgrelid='erp.bs_case_hold_events'::regclass
      and tgname='trg_guard_bs_case_hold_event_immutable' and tgenabled<>'D' and not tgisinternal
  ) then raise exception 'ERP v2.6.19 post guard: append-only HOLD trigger is missing'; end if;
  if exists(
    select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='erp' and c.relname in(
      'bs_resolution_v2619_rollback_capsule','bs_case_hold_events','bs_resolution_execution_context'
    )
      and not c.relrowsecurity
  ) then raise exception 'ERP v2.6.19 post guard: CP5 private-table RLS is disabled'; end if;

  select string_agg(c.object_identity,',' order by c.object_identity) into v_bad
  from erp.bs_resolution_v2619_rollback_capsule c
  where c.object_kind='FUNCTION' and c.definition_sha256 is distinct from
    encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex');
  if v_bad is not null then raise exception 'ERP v2.6.19 post guard: rollback capsule drift: %',v_bad; end if;
  if exists(select 1 from erp.bs_resolution_execution_context) then
    raise exception 'ERP v2.6.19 post guard: execution context leaked during install';
  end if;
  if (select count(*) from erp.bs_resolution_v2619_rollback_capsule)<>30 then
    raise exception 'ERP v2.6.19 post guard: rollback capsule count changed';
  end if;
end
$post_guard$;

insert into erp.schema_migrations(version,description)
values('v2.6.19','CP5 authoritative BS Resolution: classification, rework/rewash, HOLD, disposition, Laundry claim, recovery, and reversal facade');

select pg_notify('pgrst','reload schema');
commit;
