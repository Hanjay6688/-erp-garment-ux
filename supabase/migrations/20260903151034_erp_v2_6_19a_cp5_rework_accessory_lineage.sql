
begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $guard$
declare
  r record;
  v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.19') then
    raise exception 'ERP v2.6.19a requires recorded v2.6.19 first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.19a') then
    raise exception 'ERP v2.6.19a is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.rework_accessory_decisions') is not null
     or to_regclass('erp.rework_accessory_selection_lines') is not null
     or to_regclass('erp.bs_resolution_v2619a_rollback_capsule') is not null
     or to_regprocedure('erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone)') is not null
     or to_regprocedure('erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone)') is not null
     or to_regprocedure('erp.get_rework_accessory_decision_v1(uuid)') is not null
     or to_regprocedure('erp.guard_rework_accessory_lineage_immutable()') is not null then
    raise exception 'ERP v2.6.19a target guard: prior accessory-lineage residue exists';
  end if;
  if exists(select 1 from erp.rework_orders)
     or exists(select 1 from erp.rework_component_lines)
     or exists(select 1 from erp.fg_lots where lot_origin='PRODUCTION')
     or exists(select 1 from erp.fg_accessory_cost_snapshots)
     or exists(select 1 from erp.contractor_accessory_reimbursement_entitlements) then
    raise exception 'ERP v2.6.19a is a pre-use correction and refuses ambiguous rework/FG financial history';
  end if;
  for r in
    select * from (values
      ('erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint)','c59e0fc2f14934d3947ce5cc7f3c78bb'),
      ('erp.ensure_fg_accessory_cost_snapshot(uuid)','aae034da6699fb2f7b4c5f817e8d9f50'),
      ('erp.post_accessory_reimbursement_accrual(uuid)','36804117ef5af6f018c199518bd2e915'),
      ('erp.post_rework_completion(uuid)','bf610b5a00636297eab1f640bdc5da8c'),
      ('erp.save_rework_order_v2(jsonb,uuid,bigint)','d4f297f43858bb3c819c9cacec2972ab'),
      ('public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)',null)
    ) expected(identity,expected_md5)
  loop
    if to_regprocedure(r.identity) is null then
      raise exception 'ERP v2.6.19a target guard: required function % is absent',r.identity;
    end if;
    if r.expected_md5 is not null then
      select md5(pg_get_functiondef(to_regprocedure(r.identity))) into v_actual;
      if v_actual is distinct from r.expected_md5 then
        raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: % changed (% vs %)',r.identity,v_actual,r.expected_md5;
      end if;
    end if;
  end loop;
end
$guard$;

create table erp.bs_resolution_v2619a_rollback_capsule(
  function_identity text primary key,
  function_definition text not null,
  definition_sha256 text not null,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.bs_resolution_v2619a_rollback_capsule enable row level security;
revoke all on table erp.bs_resolution_v2619a_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.bs_resolution_v2619a_rollback_capsule(
  function_identity,function_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint)'::regprocedure,
  'erp.ensure_fg_accessory_cost_snapshot(uuid)'::regprocedure,
  'erp.post_accessory_reimbursement_accrual(uuid)'::regprocedure,
  'erp.post_rework_completion(uuid)'::regprocedure,
  'erp.save_rework_order_v2(jsonb,uuid,bigint)'::regprocedure,
  'public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)'::regprocedure
);

do $capsule_guard$
begin
  if (select count(*) from erp.bs_resolution_v2619a_rollback_capsule)<>6
     or exists(
       select 1 from erp.bs_resolution_v2619a_rollback_capsule
       where definition_sha256 is distinct from
         encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex')
     ) then
    raise exception 'ERP v2.6.19a rollback capsule is incomplete or invalid';
  end if;
end
$capsule_guard$;

create table erp.rework_accessory_decisions(
  id uuid primary key default gen_random_uuid(),
  rework_order_id uuid not null unique references erp.rework_orders(id),
  bs_case_id uuid not null references erp.bs_cases(id),
  bom_version_id uuid references erp.accessory_bom_versions(id),
  reimbursement_contractor_id uuid references erp.contractors(id),
  decision_state varchar(20) not null check(decision_state in('SELECTED','NONE','UNAVAILABLE')),
  selected_item_count integer not null check(selected_item_count>=0),
  selection_sha256 text not null check(selection_sha256~'^[0-9a-f]{64}$'),
  basis_at timestamptz not null,
  decided_by uuid references erp.app_users(id),
  client_request_id uuid not null,
  created_at timestamptz not null default clock_timestamp(),
  unique(id,rework_order_id),
  check(
    (decision_state='UNAVAILABLE' and bom_version_id is null and selected_item_count=0)
    or(decision_state='NONE' and bom_version_id is not null and selected_item_count=0)
    or(decision_state='SELECTED' and bom_version_id is not null and selected_item_count>0)
  )
);

create table erp.rework_accessory_selection_lines(
  id uuid primary key default gen_random_uuid(),
  decision_id uuid not null,
  rework_order_id uuid not null,
  bom_item_id uuid not null references erp.accessory_bom_items(id),
  category_id uuid not null references erp.accessory_categories(id),
  qty_per_good_fg_base_snapshot numeric(18,6) not null check(qty_per_good_fg_base_snapshot>0),
  hpp_method_snapshot varchar(30) not null check(hpp_method_snapshot in('CATEGORY_MOVING_AVG','BOM_STANDARD')),
  hpp_standard_unit_cost_base_snapshot numeric(18,6)
    check(hpp_standard_unit_cost_base_snapshot is null or hpp_standard_unit_cost_base_snapshot>=0),
  reimbursement_unit_rate_base_snapshot numeric(18,6) not null
    check(reimbursement_unit_rate_base_snapshot>=0),
  created_at timestamptz not null default clock_timestamp(),
  foreign key(decision_id,rework_order_id)
    references erp.rework_accessory_decisions(id,rework_order_id),
  unique(decision_id,bom_item_id),
  unique(rework_order_id,category_id),
  check(
    (hpp_method_snapshot='BOM_STANDARD' and hpp_standard_unit_cost_base_snapshot is not null)
    or hpp_method_snapshot='CATEGORY_MOVING_AVG'
  )
);

create index idx_rework_accessory_decisions_bs_case
  on erp.rework_accessory_decisions(bs_case_id,created_at desc);
create index idx_rework_accessory_selection_lines_order
  on erp.rework_accessory_selection_lines(rework_order_id,bom_item_id);
create unique index ux_rework_orders_good_fg_lot_v2619a
  on erp.rework_orders(good_fg_lot_id) where good_fg_lot_id is not null;
create index idx_bs_case_hold_events_actor
  on erp.bs_case_hold_events(actor_id) where actor_id is not null;

alter table erp.rework_accessory_decisions enable row level security;
alter table erp.rework_accessory_selection_lines enable row level security;
revoke all on table erp.rework_accessory_decisions,erp.rework_accessory_selection_lines
  from public,anon,authenticated,service_role;

create function erp.guard_rework_accessory_lineage_immutable()
returns trigger language plpgsql set search_path=''
as $function$
begin
  raise exception 'Rework accessory choice is immutable; cancel an untouched order and create a corrected order';
end
$function$;

create trigger trg_rework_accessory_decisions_immutable
before update or delete on erp.rework_accessory_decisions
for each row execute function erp.guard_rework_accessory_lineage_immutable();
create trigger trg_rework_accessory_selection_lines_immutable
before update or delete on erp.rework_accessory_selection_lines
for each row execute function erp.guard_rework_accessory_lineage_immutable();
create trigger trg_audit_rework_accessory_decisions
after insert on erp.rework_accessory_decisions
for each row execute function erp.audit_row_change();
create trigger trg_audit_rework_accessory_selection_lines
after insert on erp.rework_accessory_selection_lines
for each row execute function erp.audit_row_change();

create function erp.resolve_rework_accessory_bom_v1(
  p_bs_case_id uuid,p_basis_at timestamptz
)
returns uuid language plpgsql stable security definer set search_path=''
as $function$
declare
  v_po uuid;
  v_product uuid;
  v_po_model uuid;
  v_product_model uuid;
  v_root uuid;
  v_bom uuid;
  v_distinct integer;
begin
  select b.po_id,b.product_id,po.model_id,p.model_id,p.identity_root_id
  into v_po,v_product,v_po_model,v_product_model,v_root
  from erp.bs_cases b
  left join erp.production_orders po on po.id=b.po_id
  left join erp.products p on p.id=b.product_id
  where b.id=p_bs_case_id;
  if not found then raise exception 'BS case not found'; end if;
  if v_po is null or v_product is null then return null; end if;
  if p_basis_at is null then raise exception 'Accessory BOM basis_at is required'; end if;
  if v_product_model is distinct from v_po_model then
    raise exception 'BS product model does not match production order model';
  end if;

  select c.bom_version_id into v_bom
  from erp.po_accessory_bom_commitments c
  where c.po_id=v_po and c.product_id=v_product;
  if v_bom is not null then return v_bom; end if;

  select count(distinct c.bom_version_id) into v_distinct
  from erp.po_accessory_bom_commitments c
  join erp.products cp on cp.id=c.product_id
  where c.po_id=v_po and cp.identity_root_id=v_root;
  if coalesce(v_distinct,0)>1 then
    raise exception 'PO has ambiguous accessory BOM commitments for this logical SKU';
  end if;
  if coalesce(v_distinct,0)=1 then
    select c.bom_version_id into v_bom
    from erp.po_accessory_bom_commitments c
    join erp.products cp on cp.id=c.product_id
    where c.po_id=v_po and cp.identity_root_id=v_root
    order by c.committed_at,c.id limit 1;
    return v_bom;
  end if;

  select abv.id into v_bom
  from erp.accessory_bom_versions abv
  where abv.product_id=v_root and abv.is_active
    and abv.effective_from<=p_basis_at
    and(abv.effective_to is null or abv.effective_to>p_basis_at)
  order by abv.effective_from desc,abv.created_at desc,abv.id desc limit 1;
  return v_bom;
end
$function$;

create function erp.bs_accessory_bom_options_v1(
  p_bs_case_id uuid,p_basis_at timestamptz default statement_timestamp()
)
returns jsonb language plpgsql stable security definer set search_path=''
as $function$
declare
  v_bom uuid;
begin
  v_bom:=erp.resolve_rework_accessory_bom_v1(p_bs_case_id,p_basis_at);
  if v_bom is null then
    return jsonb_build_object(
      'state','UNAVAILABLE','bom_version_id',null,'items','[]'::jsonb
    );
  end if;
  return jsonb_build_object(
    'state',case when exists(select 1 from erp.accessory_bom_items where bom_version_id=v_bom)
      then 'AVAILABLE' else 'NONE' end,
    'bom_version_id',v_bom,
    'items',coalesce((
      select jsonb_agg(jsonb_build_object(
        'id',i.id,'category_id',i.category_id,'code',c.category_code,
        'name',c.category_name,'base_uom_code',c.base_uom_code,
        'qty_per_good_fg_base',i.qty_per_good_fg_base,
        'reimbursement_rate',i.reimbursement_rate,
        'reimbursement_uom_code',i.reimbursement_uom_code
      ) order by c.category_code,i.id)
      from erp.accessory_bom_items i
      join erp.accessory_categories c on c.id=i.category_id
      where i.bom_version_id=v_bom
    ),'[]'::jsonb)
  );
end
$function$;

create function erp.get_rework_accessory_decision_v1(p_rework_order_id uuid)
returns jsonb language sql stable security definer set search_path=''
as $function$
  select jsonb_build_object(
    'state',d.decision_state,'bom_version_id',d.bom_version_id,
    'reimbursement_contractor_id',d.reimbursement_contractor_id,
    'selected_item_count',d.selected_item_count,
    'selection_sha256',d.selection_sha256,'basis_at',d.basis_at,
    'selected_items',coalesce((
      select jsonb_agg(jsonb_build_object(
        'id',l.id,'bom_item_id',l.bom_item_id,'category_id',l.category_id,
        'code',c.category_code,'name',c.category_name,
        'qty_per_good_fg_base',l.qty_per_good_fg_base_snapshot,
        'reimbursement_unit_rate_base',l.reimbursement_unit_rate_base_snapshot
      ) order by c.category_code,l.id)
      from erp.rework_accessory_selection_lines l
      join erp.accessory_categories c on c.id=l.category_id
      where l.decision_id=d.id
    ),'[]'::jsonb)
  )
  from erp.rework_accessory_decisions d
  where d.rework_order_id=p_rework_order_id
$function$;

revoke all on function
  erp.guard_rework_accessory_lineage_immutable(),
  erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone),
  erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone),
  erp.get_rework_accessory_decision_v1(uuid)
  from public,anon,authenticated,service_role;

create or replace function erp.save_rework_order_v2(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb language plpgsql security definer
set search_path='erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_action text:=upper(coalesce(nullif(p_payload->>'action',''),'SAVE'));
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_order erp.rework_orders%rowtype;
  v_case erp.bs_cases%rowtype;
  v_component jsonb;
  v_total_return integer;
  v_previous_return integer;
  v_good integer;
  v_bad integer;
  v_accessories jsonb;
  v_selected_count integer;
  v_distinct_count integer;
  v_bom uuid;
  v_expected_bom uuid;
  v_decision uuid;
  v_recipient uuid;
  v_po_contractor uuid;
  v_item record;
  v_hpp_factor numeric(18,6);
  v_reimburse_factor numeric(18,6);
  v_hpp_base numeric(18,6);
  v_reimburse_base numeric(18,6);
  v_selection_hash text;
begin
  perform erp.require_internal();
  if p_payload is null or jsonb_typeof(p_payload)<>'object' then
    raise exception 'payload must be a JSON object';
  end if;
  if v_action not in('SAVE','CANCEL') then raise exception 'Rework action must be SAVE or CANCEL'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_rework_order_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is null then
    if v_action='CANCEL' then raise exception 'Rework id is required for CANCEL'; end if;
    if p_expected_version is not null then raise exception 'expected_version must be null when creating rework'; end if;
    if not(p_payload?'accessory_bom_item_ids')
       or jsonb_typeof(p_payload->'accessory_bom_item_ids')<>'array' then
      raise exception 'accessory_bom_item_ids must be an explicit array; use [] when nothing was installed';
    end if;
    v_accessories:=p_payload->'accessory_bom_item_ids';
    v_selected_count:=jsonb_array_length(v_accessories);
    select count(*) into v_distinct_count
    from(select distinct value::uuid from jsonb_array_elements_text(v_accessories)) x;
    if v_selected_count<>v_distinct_count then
      raise exception 'accessory_bom_item_ids must not contain duplicates';
    end if;
    if coalesce(nullif(p_payload->>'qty_good_returned','')::integer,0)<>0
       or coalesce(nullif(p_payload->>'qty_bs_returned','')::integer,0)<>0 then
      raise exception 'Create the order first; cumulative partial returns must use a versioned SAVE_REWORK update';
    end if;
    if upper(coalesce(nullif(p_payload->>'status',''),'IN_PROGRESS')) not in('OPEN','IN_PROGRESS') then
      raise exception 'New rework status must be OPEN or IN_PROGRESS';
    end if;

    insert into erp.rework_orders(
      rework_number,bs_case_id,destination_type,contractor_id,vendor_id,
      qty_sent,qty_good_returned,qty_bs_returned,physical_sent_at,status,
      return_fg_location_id,notes
    ) values(
      btrim(p_payload->>'rework_number'),(p_payload->>'bs_case_id')::uuid,
      upper(p_payload->>'destination_type'),nullif(p_payload->>'contractor_id','')::uuid,
      nullif(p_payload->>'vendor_id','')::uuid,(p_payload->>'qty_sent')::integer,
      0,0,(p_payload->>'physical_sent_at')::timestamptz,
      upper(coalesce(nullif(p_payload->>'status',''),'IN_PROGRESS')),
      nullif(p_payload->>'return_fg_location_id','')::uuid,
      nullif(btrim(p_payload->>'notes'),'')
    ) returning * into v_order;
    v_id:=v_order.id;

    select * into v_case from erp.bs_cases where id=v_order.bs_case_id for update;
    select po.contractor_id into v_po_contractor
    from erp.production_orders po where po.id=v_case.po_id;
    v_bom:=erp.resolve_rework_accessory_bom_v1(v_case.id,v_order.physical_sent_at);
    v_expected_bom:=nullif(p_payload->>'accessory_bom_version_id','')::uuid;
    if v_expected_bom is not null and v_expected_bom is distinct from v_bom then
      raise exception 'ACCESSORY_BOM_CHANGED_REFRESH';
    end if;

    if v_bom is null then
      if v_case.po_id is not null and v_case.product_id is not null then
        raise exception 'Native BS requires an effective accessory BOM, including an explicit empty BOM when there are no accessories';
      end if;
      if v_selected_count<>0 then
        raise exception 'Untracked BS without PO/product lineage cannot select accessory BOM items';
      end if;
      v_selection_hash:=encode(extensions.digest(convert_to('','UTF8'),'sha256'),'hex');
      insert into erp.rework_accessory_decisions(
        rework_order_id,bs_case_id,bom_version_id,reimbursement_contractor_id,
        decision_state,selected_item_count,selection_sha256,basis_at,
        decided_by,client_request_id
      ) values(
        v_order.id,v_case.id,null,null,'UNAVAILABLE',0,v_selection_hash,
        v_order.physical_sent_at,erp.current_app_user_id(),p_client_request_id
      ) returning id into v_decision;
    else
      if exists(
        select 1 from jsonb_array_elements_text(v_accessories) x(item_id)
        left join erp.accessory_bom_items i
          on i.id=x.item_id::uuid and i.bom_version_id=v_bom
        where i.id is null
      ) then raise exception 'Selected accessory does not belong to the authoritative BOM; refresh the workspace'; end if;

      insert into erp.po_accessory_bom_commitments(
        po_id,product_id,bom_version_id,committed_at,commit_source,committed_by
      ) values(
        v_case.po_id,v_case.product_id,v_bom,v_order.physical_sent_at,
        'FIRST_FINANCIAL_USE',erp.current_app_user_id()
      ) on conflict(po_id,product_id) do nothing;
      if (select c.bom_version_id from erp.po_accessory_bom_commitments c
          where c.po_id=v_case.po_id and c.product_id=v_case.product_id) is distinct from v_bom then
        raise exception 'ACCESSORY_BOM_CHANGED_REFRESH';
      end if;

      v_recipient:=case when v_order.destination_type='CONTRACTOR'
        then v_order.contractor_id else v_po_contractor end;
      select encode(extensions.digest(convert_to(coalesce(string_agg(
        x.item_id::uuid::text,',' order by x.item_id::uuid::text
      ),''),'UTF8'),'sha256'),'hex') into v_selection_hash
      from jsonb_array_elements_text(v_accessories) x(item_id);
      insert into erp.rework_accessory_decisions(
        rework_order_id,bs_case_id,bom_version_id,reimbursement_contractor_id,
        decision_state,selected_item_count,selection_sha256,basis_at,
        decided_by,client_request_id
      ) values(
        v_order.id,v_case.id,v_bom,v_recipient,
        case when v_selected_count>0 then 'SELECTED' else 'NONE' end,
        v_selected_count,v_selection_hash,v_order.physical_sent_at,
        erp.current_app_user_id(),p_client_request_id
      ) returning id into v_decision;

      for v_item in
        select i.* from erp.accessory_bom_items i
        join jsonb_array_elements_text(v_accessories) x(item_id)
          on x.item_id::uuid=i.id
        where i.bom_version_id=v_bom order by i.id
      loop
        if v_item.hpp_method='BOM_STANDARD' then
          v_hpp_factor:=erp.accessory_uom_factor(
            v_item.category_id,v_item.hpp_uom_code,v_order.physical_sent_at
          );
          v_hpp_base:=v_item.hpp_standard_rate/v_hpp_factor;
        else
          v_hpp_base:=null;
        end if;
        v_reimburse_factor:=erp.accessory_uom_factor(
          v_item.category_id,v_item.reimbursement_uom_code,v_order.physical_sent_at
        );
        v_reimburse_base:=v_item.reimbursement_rate/v_reimburse_factor;
        if v_reimburse_base>0 and v_recipient is null then
          raise exception 'Selected accessory reimbursement requires an authoritative Mandor';
        end if;
        insert into erp.rework_accessory_selection_lines(
          decision_id,rework_order_id,bom_item_id,category_id,
          qty_per_good_fg_base_snapshot,hpp_method_snapshot,
          hpp_standard_unit_cost_base_snapshot,reimbursement_unit_rate_base_snapshot
        ) values(
          v_decision,v_order.id,v_item.id,v_item.category_id,
          v_item.qty_per_good_fg_base,v_item.hpp_method,
          v_hpp_base,v_reimburse_base
        );
      end loop;
    end if;

    if p_payload?'components' then
      if jsonb_typeof(p_payload->'components')<>'array' then raise exception 'components must be an array'; end if;
      for v_component in select value from jsonb_array_elements(p_payload->'components') loop
        insert into erp.rework_component_lines(
          rework_order_id,bs_case_component_id,qty_performed,qty_newly_payable,
          rate_snapshot,notes
        ) values(
          v_id,(v_component->>'bs_case_component_id')::uuid,
          (v_component->>'qty_performed')::integer,0,0,
          nullif(btrim(v_component->>'notes'),'')
        );
      end loop;
    end if;
    if v_order.destination_type='CONTRACTOR' and not exists(
      select 1 from erp.rework_component_lines where rework_order_id=v_order.id
    ) then raise exception 'Contractor rework requires at least one component line'; end if;
    update erp.rework_orders set updated_at=clock_timestamp()
    where id=v_id returning * into v_order;
  else
    if p_expected_version is null then raise exception 'expected_version is required'; end if;
    select * into v_order from erp.rework_orders where id=v_id for update;
    if v_order.id is null then raise exception 'Rework order not found'; end if;
    if v_order.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_order.row_version;
    end if;
    if v_order.cost_posted or v_order.status in('COMPLETED','CANCELLED') then
      raise exception 'Completed/cancelled rework is locked; use reversal/correction';
    end if;
    if v_action='CANCEL' then
      if v_order.qty_good_returned+v_order.qty_bs_returned>0 then
        raise exception 'Partially returned rework must be fully reconciled before cancellation';
      end if;
      update erp.rework_orders
      set status='CANCELLED',notes=concat_ws(E'\n',notes,'CANCELLED: '||v_reason),
          updated_at=clock_timestamp()
      where id=v_id returning * into v_order;
      perform erp.refresh_bs_case_status(v_order.bs_case_id);
      v_response:=jsonb_build_object(
        'rework_order_id',v_order.id,'status',v_order.status,
        'row_version',v_order.row_version,
        'accessory_decision',erp.get_rework_accessory_decision_v1(v_order.id)
      );
      return erp._idempotency_complete('save_rework_order_v2',p_client_request_id,v_response);
    end if;

    if exists(
      select 1 from jsonb_object_keys(p_payload) k(key)
      where k.key not in(
        'id','action','qty_good_returned','qty_bs_returned',
        'return_fg_location_id','change_reason'
      )
    ) then
      raise exception 'Rework route, quantity sent, work components, and accessory choice are immutable after creation';
    end if;
    if not(p_payload?'qty_good_returned') and not(p_payload?'qty_bs_returned') then
      raise exception 'Partial SAVE_REWORK requires cumulative GOOD or BS quantity';
    end if;
    v_good:=coalesce(nullif(p_payload->>'qty_good_returned','')::integer,v_order.qty_good_returned);
    v_bad:=coalesce(nullif(p_payload->>'qty_bs_returned','')::integer,v_order.qty_bs_returned);
    v_previous_return:=v_order.qty_good_returned+v_order.qty_bs_returned;
    v_total_return:=v_good+v_bad;
    if v_good<v_order.qty_good_returned or v_bad<v_order.qty_bs_returned then
      raise exception 'Cumulative rework return quantities cannot decrease';
    end if;
    if v_total_return<=v_previous_return then
      raise exception 'Partial rework update must record newly returned physical quantity';
    end if;
    if v_total_return>=v_order.qty_sent then
      raise exception 'Fully reconciled return must use complete_rework_order_v2';
    end if;
    if p_payload?'return_fg_location_id'
       and nullif(p_payload->>'return_fg_location_id','') is not null
       and not exists(
         select 1 from erp.locations l
         where l.id=(p_payload->>'return_fg_location_id')::uuid
           and l.is_active and l.location_type='FG_WAREHOUSE'
       ) then raise exception 'Selected rework return location must be an active FG warehouse'; end if;
    update erp.rework_orders
    set qty_good_returned=v_good,qty_bs_returned=v_bad,status='PARTIAL',
        return_fg_location_id=case when p_payload?'return_fg_location_id'
          then nullif(p_payload->>'return_fg_location_id','')::uuid
          else return_fg_location_id end,
        notes=concat_ws(E'\n',notes,format(
          'PARTIAL RETURN: GOOD %s + BS %s / %s · %s',v_good,v_bad,qty_sent,v_reason
        )),updated_at=clock_timestamp()
    where id=v_id returning * into v_order;
  end if;

  perform erp.refresh_bs_case_status(v_order.bs_case_id);
  select * into v_order from erp.rework_orders where id=v_order.id;
  v_response:=jsonb_build_object(
    'rework_order_id',v_order.id,'status',v_order.status,
    'row_version',v_order.row_version,'bs_case_id',v_order.bs_case_id,
    'qty_good_returned',v_order.qty_good_returned,
    'qty_bs_returned',v_order.qty_bs_returned,
    'components',coalesce((
      select jsonb_agg(jsonb_build_object(
        'rework_component_line_id',l.id,'bs_case_component_id',l.bs_case_component_id,
        'qty_performed',l.qty_performed,'qty_newly_payable',l.qty_newly_payable,
        'rate_snapshot',l.rate_snapshot,'rate_basis',l.rate_basis,
        'source_contractor_rate_id',l.source_contractor_rate_id,
        'source_po_component_snapshot_id',l.source_po_component_snapshot_id
      ) order by l.id)
      from erp.rework_component_lines l where l.rework_order_id=v_order.id
    ),'[]'::jsonb),
    'accessory_decision',erp.get_rework_accessory_decision_v1(v_order.id)
  );
  return erp._idempotency_complete('save_rework_order_v2',p_client_request_id,v_response);
end
$function$;

create or replace function erp.complete_rework_order_v2(
  p_rework_order_id uuid,p_qty_good integer,p_qty_bs integer,
  p_completed_at timestamptz,p_return_fg_location_id uuid,p_reason text,
  p_client_request_id uuid,p_expected_version bigint
)
returns jsonb language plpgsql security definer
set search_path='erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_order erp.rework_orders%rowtype;
  v_case erp.bs_cases%rowtype;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if nullif(btrim(p_reason),'') is null then raise exception 'Completion reason is required'; end if;
  if p_completed_at is null or p_completed_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'Valid non-future completed_at is required';
  end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'rework_order_id',p_rework_order_id,'good',p_qty_good,'bs',p_qty_bs,
    'completed_at',p_completed_at,'location',p_return_fg_location_id,
    'reason',btrim(p_reason),'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('complete_rework_order_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_order from erp.rework_orders where id=p_rework_order_id for update;
  if v_order.id is null then raise exception 'Rework order not found'; end if;
  if v_order.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_order.row_version;
  end if;
  if v_order.status not in('OPEN','IN_PROGRESS','PARTIAL') or v_order.cost_posted then
    raise exception 'Only active unposted rework can be completed';
  end if;
  if coalesce(p_qty_good,0)<0 or coalesce(p_qty_bs,0)<0
     or coalesce(p_qty_good,0)+coalesce(p_qty_bs,0)<>v_order.qty_sent then
    raise exception 'Completion must reconcile exactly: GOOD + BS = qty sent';
  end if;
  if p_qty_good<v_order.qty_good_returned or p_qty_bs<v_order.qty_bs_returned then
    raise exception 'Final cumulative rework quantities cannot decrease a recorded partial return';
  end if;
  if p_completed_at<v_order.physical_sent_at then
    raise exception 'Completion cannot predate physical rework dispatch';
  end if;
  if not exists(
    select 1 from erp.rework_accessory_decisions d where d.rework_order_id=v_order.id
  ) then raise exception 'Rework accessory decision lineage is missing'; end if;
  if v_order.destination_type='CONTRACTOR' and not exists(
    select 1 from erp.rework_component_lines where rework_order_id=v_order.id
  ) then raise exception 'Contractor rework requires component lines'; end if;
  perform set_config('app.change_reason',btrim(p_reason),true);
  update erp.rework_orders
  set qty_good_returned=coalesce(p_qty_good,0),qty_bs_returned=coalesce(p_qty_bs,0),
      completed_at=p_completed_at,status='COMPLETED',
      return_fg_location_id=coalesce(p_return_fg_location_id,return_fg_location_id),
      notes=concat_ws(E'\n',notes,'COMPLETED: '||btrim(p_reason)),
      updated_at=clock_timestamp()
  where id=v_order.id;
  perform erp.post_rework_completion(v_order.id);
  select * into v_order from erp.rework_orders where id=v_order.id;
  select * into v_case from erp.bs_cases where id=v_order.bs_case_id;
  v_response:=jsonb_build_object(
    'rework_order_id',v_order.id,'status',v_order.status,'row_version',v_order.row_version,
    'cost_posted',v_order.cost_posted,'good_fg_lot_id',v_order.good_fg_lot_id,
    'bs_case_id',v_case.id,'bs_case_status',v_case.status,
    'bs_case_row_version',v_case.row_version,
    'accessory_decision',erp.get_rework_accessory_decision_v1(v_order.id)
  );
  return erp._idempotency_complete('complete_rework_order_v2',p_client_request_id,v_response);
end
$function$;

create or replace function erp.ensure_fg_accessory_cost_snapshot(p_lot_id uuid)
returns void language plpgsql security definer set search_path='erp','public'
as $function$
declare
  l erp.fg_lots%rowtype;
  p erp.production_orders%rowtype;
  v_bom uuid;
  r record;
  v_category_avg numeric(18,6);
  v_hpp_factor numeric(18,6);
  v_reimburse_factor numeric(18,6);
  v_hpp_base numeric(18,6);
  v_reimburse_base numeric(18,6);
  v_snapshot uuid;
  v_commit_at timestamptz;
  v_rework uuid;
  v_decision uuid;
  v_recipient uuid;
  v_selected_count integer;
  v_snapshot_count integer;
begin
  perform erp.require_internal();
  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'PRODUCTION' then return; end if;
  select * into p from erp.production_orders where id=l.po_id;
  if p.id is null then return; end if;

  select ro.id,d.id,d.bom_version_id,d.reimbursement_contractor_id,d.selected_item_count
  into v_rework,v_decision,v_bom,v_recipient,v_selected_count
  from erp.rework_orders ro
  join erp.rework_accessory_decisions d on d.rework_order_id=ro.id
  where ro.good_fg_lot_id=l.id;

  if v_rework is not null then
    select count(*) into v_snapshot_count
    from erp.fg_accessory_cost_snapshots s where s.lot_id=l.id;
    if v_snapshot_count>0 then
      if v_snapshot_count<>v_selected_count
         or exists(
           select 1 from erp.fg_accessory_cost_snapshots s
           left join erp.rework_accessory_selection_lines sl
             on sl.decision_id=v_decision and sl.bom_item_id=s.bom_item_id
           where s.lot_id=l.id and sl.id is null
         ) then
        raise exception 'Rework accessory snapshot set diverges from immutable selection lineage';
      end if;
      return;
    end if;
    if v_selected_count=0 then return; end if;
    if v_bom is null then raise exception 'Selected rework accessory lineage has no BOM version'; end if;
    if not exists(
      select 1 from erp.po_accessory_bom_commitments c
      where c.po_id=l.po_id and c.product_id=l.product_id and c.bom_version_id=v_bom
    ) then raise exception 'Rework accessory BOM commitment is missing or changed'; end if;

    for r in
      select sl.*,c.category_code
      from erp.rework_accessory_selection_lines sl
      join erp.accessory_categories c on c.id=sl.category_id
      where sl.decision_id=v_decision
      order by c.category_code,sl.id
    loop
      v_category_avg:=erp.accessory_category_weighted_avg_cost_at(r.category_id,l.produced_at);
      if r.hpp_method_snapshot='CATEGORY_MOVING_AVG' then
        if v_category_avg is null then
          raise exception 'Cannot snapshot HPP: accessory category % has no moving-average valuation history at %',r.category_id,l.produced_at;
        end if;
        v_hpp_base:=v_category_avg;
      else
        v_hpp_base:=r.hpp_standard_unit_cost_base_snapshot;
      end if;
      v_reimburse_base:=r.reimbursement_unit_rate_base_snapshot;
      insert into erp.fg_accessory_cost_snapshots(
        lot_id,po_id,product_id,bom_version_id,bom_item_id,category_id,
        good_qty_pcs,qty_per_good_fg_base,hpp_method,
        category_avg_cost_base_snapshot,hpp_unit_cost_base_snapshot,
        reimbursement_unit_rate_base_snapshot,costing_basis_at,costing_basis_source
      ) values(
        l.id,l.po_id,l.product_id,v_bom,r.bom_item_id,r.category_id,
        l.initial_qty_pcs,r.qty_per_good_fg_base_snapshot,r.hpp_method_snapshot,
        v_category_avg,v_hpp_base,v_reimburse_base,l.produced_at,'FG_ACCEPTANCE'
      ) returning id into v_snapshot;
      if v_recipient is null and v_reimburse_base>0 then
        raise exception 'Selected rework accessory reimbursement has no authoritative Mandor';
      end if;
      if v_recipient is not null and v_reimburse_base>0 then
        insert into erp.contractor_accessory_reimbursement_entitlements(
          snapshot_id,contractor_id,po_id,lot_id,product_id,category_id,physical_at,amount
        ) select
          v_snapshot,v_recipient,l.po_id,l.id,l.product_id,r.category_id,
          l.produced_at,total_reimbursement
        from erp.fg_accessory_cost_snapshots where id=v_snapshot;
      end if;
    end loop;
    return;
  end if;

  if exists(select 1 from erp.fg_accessory_cost_snapshots where lot_id=l.id) then return; end if;
  v_bom:=erp.commit_accessory_bom_for_lot(l.id);
  if v_bom is null then return; end if;
  select committed_at into v_commit_at
  from erp.po_accessory_bom_commitments
  where po_id=l.po_id and product_id=l.product_id;
  for r in
    select i.*,c.base_uom_code
    from erp.accessory_bom_items i
    join erp.accessory_categories c on c.id=i.category_id
    where i.bom_version_id=v_bom order by c.category_code
  loop
    v_category_avg:=erp.accessory_category_weighted_avg_cost_at(r.category_id,l.produced_at);
    if r.hpp_method='CATEGORY_MOVING_AVG' then
      if v_category_avg is null then
        raise exception 'Cannot snapshot HPP: accessory category % has no moving-average valuation history at %',r.category_id,l.produced_at;
      end if;
      v_hpp_base:=v_category_avg;
    else
      v_hpp_factor:=erp.accessory_uom_factor(r.category_id,r.hpp_uom_code,l.produced_at);
      v_hpp_base:=r.hpp_standard_rate/v_hpp_factor;
    end if;
    v_reimburse_factor:=erp.accessory_uom_factor(
      r.category_id,r.reimbursement_uom_code,l.produced_at
    );
    v_reimburse_base:=r.reimbursement_rate/v_reimburse_factor;
    insert into erp.fg_accessory_cost_snapshots(
      lot_id,po_id,product_id,bom_version_id,bom_item_id,category_id,
      good_qty_pcs,qty_per_good_fg_base,hpp_method,
      category_avg_cost_base_snapshot,hpp_unit_cost_base_snapshot,
      reimbursement_unit_rate_base_snapshot,costing_basis_at,costing_basis_source
    ) values(
      l.id,l.po_id,l.product_id,v_bom,r.id,r.category_id,l.initial_qty_pcs,
      r.qty_per_good_fg_base,r.hpp_method,v_category_avg,v_hpp_base,
      v_reimburse_base,l.produced_at,
      case when v_commit_at=l.produced_at then 'FIRST_FINANCIAL_USE' else 'FG_ACCEPTANCE' end
    ) returning id into v_snapshot;
    if p.contractor_id is null and v_reimburse_base>0 then
      raise exception 'PO % has accessory reimbursement BOM but no mandor/contractor',p.po_number;
    end if;
    if p.contractor_id is not null and v_reimburse_base>0 then
      insert into erp.contractor_accessory_reimbursement_entitlements(
        snapshot_id,contractor_id,po_id,lot_id,product_id,category_id,physical_at,amount
      ) select
        v_snapshot,p.contractor_id,l.po_id,l.id,l.product_id,r.category_id,
        l.produced_at,total_reimbursement
      from erp.fg_accessory_cost_snapshots where id=v_snapshot;
    end if;
  end loop;
end
$function$;

create or replace function erp.post_accessory_reimbursement_accrual(p_lot_id uuid)
returns void language plpgsql security definer set search_path='erp','public'
as $function$
declare
  l erp.fg_lots%rowtype;
  v_hpp numeric(24,6);
  v_reimburse numeric(24,6);
  v_entitlement_total numeric(24,6);
  v_variance numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
  v_contractor uuid;
  v_contractor_count integer;
begin
  perform erp.require_internal();
  perform erp.ensure_fg_accessory_cost_snapshot(p_lot_id);
  select * into l from erp.fg_lots where id=p_lot_id;
  if l.id is null or l.lot_origin<>'PRODUCTION' then return; end if;
  select coalesce(sum(total_hpp_cost),0),coalesce(sum(total_reimbursement),0)
  into v_hpp,v_reimburse
  from erp.fg_accessory_cost_snapshots where lot_id=l.id;
  if v_hpp=0 and v_reimburse=0 then return; end if;
  if exists(
    select 1 from erp.journal_entries
    where source_type='ACCESSORY_REIMBURSE_ACCRUAL'
      and source_id=l.id and status='POSTED'
  ) then return; end if;
  select count(distinct e.contractor_id),
    (array_agg(distinct e.contractor_id order by e.contractor_id))[1],
    coalesce(sum(e.amount),0)
  into v_contractor_count,v_contractor,v_entitlement_total
  from erp.contractor_accessory_reimbursement_entitlements e
  where e.lot_id=l.id and e.payroll_status<>'CANCELLED';
  if abs(v_entitlement_total-v_reimburse)>0.005 then
    raise exception 'Accessory entitlement total does not match immutable snapshot reimbursement';
  end if;
  if v_reimburse>0 and v_contractor_count<>1 then
    raise exception 'Accessory reimbursement requires exactly one authoritative Mandor';
  end if;
  if v_hpp>0 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','WIP','debit',round(v_hpp,2),'credit',0,
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  v_variance:=v_reimburse-v_hpp;
  if v_variance>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','ACCESSORY_REIMBURSE_VARIANCE',
      'debit',round(v_variance,2),'credit',0,
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  elsif v_variance< -0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','ACCESSORY_REIMBURSE_VARIANCE',
      'debit',0,'credit',round(abs(v_variance),2),
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  if v_reimburse>0 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',round(v_reimburse,2),
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  if v_reimburse=0 and v_hpp>0 then
    raise exception 'Accessory HPP snapshot has cost but zero Mandor reimbursement; configure reimbursement or use normal material issue flow';
  end if;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal(
      'ACCESSORY_REIMBURSE_ACCRUAL',l.id,l.produced_at::date,
      'Selected accessory HPP + Mandor reimbursement from GOOD rework/FG',v_lines
    );
  end if;
end
$function$;

create or replace function erp.post_rework_completion(p_rework_order_id uuid)
returns void language plpgsql security definer set search_path='erp','public'
as $function$
declare
  r erp.rework_orders%rowtype;
  b erp.bs_cases%rowtype;
  v_total numeric(20,2):=0;
  v_location uuid;
  v_location_count integer:=0;
  v_lot uuid;
  v_lot_number text;
  v_hpp numeric(18,6):=0;
  v_remaining integer:=0;
  v_completed_at timestamptz;
begin
  perform erp.require_internal();
  select * into r from erp.rework_orders where id=p_rework_order_id for update;
  if r.id is null then raise exception 'Rework order not found'; end if;
  if r.status<>'COMPLETED' then raise exception 'Rework must be COMPLETED before posting'; end if;
  if r.qty_good_returned+r.qty_bs_returned<>r.qty_sent then
    raise exception 'Rework completion must reconcile exactly: GOOD + BS must equal qty sent';
  end if;
  if r.cost_posted then return; end if;
  if not exists(
    select 1 from erp.rework_accessory_decisions d where d.rework_order_id=r.id
  ) then raise exception 'Rework accessory decision lineage is missing'; end if;
  select * into b from erp.bs_cases where id=r.bs_case_id for update;
  if b.id is null then raise exception 'BS case not found'; end if;
  v_completed_at:=coalesce(r.completed_at,clock_timestamp());

  if r.qty_good_returned>0 then
    if b.po_id is null or b.product_id is null then
      raise exception 'GOOD rework return requires native production PO and product lineage';
    end if;
    if r.return_fg_location_id is not null then
      select id into v_location from erp.locations
      where id=r.return_fg_location_id and is_active and location_type='FG_WAREHOUSE';
      if v_location is null then
        raise exception 'Selected rework return location must be an active FG warehouse';
      end if;
    else
      select count(*),(array_agg(id order by id))[1]
      into v_location_count,v_location
      from erp.locations where is_active and location_type='FG_WAREHOUSE';
      if v_location_count<>1 then
        raise exception 'Select return FG warehouse for rework GOOD output; active FG warehouse count is %',v_location_count;
      end if;
    end if;
    v_lot_number:='RW-'||r.rework_number||'-'||substr(r.id::text,1,8);
    insert into erp.fg_lots(
      lot_number,po_id,qc_item_id,cutting_group_id,product_id,
      initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin
    ) values(
      v_lot_number,b.po_id,b.qc_item_id,b.cutting_group_id,b.product_id,
      r.qty_good_returned,0,v_completed_at,true,'PRODUCTION'
    ) returning id into v_lot;
    perform erp.post_fg_movement(
      b.product_id,v_lot,v_location,'GRADE_A','REWORK_IN',r.qty_good_returned,
      0,null,'REWORK_ORDER',r.id,v_completed_at,'GOOD returned from rework',false
    );
    -- Link the lot before snapshotting so the immutable selection, including
    -- an explicit empty selection, is the only source the snapshotter can use.
    update erp.rework_orders
    set good_fg_lot_id=v_lot,return_fg_location_id=v_location,completed_at=v_completed_at
    where id=r.id;
    perform erp.ensure_fg_accessory_cost_snapshot(v_lot);
    perform erp.post_accessory_reimbursement_accrual(v_lot);
    insert into erp.bs_resolutions(
      bs_case_id,resolution_type,qty_pcs,compensation_amount,
      responsible_contractor_id,responsible_vendor_id,
      source_rework_order_id,physical_at,notes
    ) values(
      b.id,case when r.destination_type='CONTRACTOR'
        then 'REWORK_SEWING' else 'REWORK_LAUNDRY' end,
      r.qty_good_returned,0,r.contractor_id,r.vendor_id,r.id,v_completed_at,
      'Recovered to GOOD FG from rework'
    );
  else
    update erp.rework_orders set completed_at=v_completed_at where id=r.id;
  end if;

  select greatest(b.qty_pcs-coalesce(sum(br.qty_pcs),0),0)::integer
  into v_remaining from erp.bs_resolutions br where br.bs_case_id=b.id;
  update erp.bs_cases
  set status=case when v_remaining=0 then 'RESOLVED' else 'PARTIAL' end,
      updated_at=clock_timestamp()
  where id=b.id;
  if r.destination_type='CONTRACTOR' then
    select coalesce(sum(amount_payable),0) into v_total
    from erp.rework_component_lines where rework_order_id=r.id;
    if v_total>0 then
      perform erp.post_journal(
        'REWORK_COMPLETION',r.id,v_completed_at::date,'Rework labor completion',
        jsonb_build_array(
          jsonb_build_object(
            'mapping_key','WIP','debit',round(v_total,2),'credit',0,
            'contractor_id',r.contractor_id,'po_id',b.po_id
          ),
          jsonb_build_object(
            'mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',round(v_total,2),
            'contractor_id',r.contractor_id,'po_id',b.po_id
          )
        )
      );
    end if;
  end if;
  update erp.rework_orders set cost_posted=true where id=r.id;
  if b.po_id is not null and exists(select 1 from erp.fg_lots where po_id=b.po_id) then
    perform erp.rebuild_po_hpp(b.po_id,'Rework completion posted with physical GOOD return');
    perform erp.propagate_conversion_hpp_for_po(b.po_id);
    perform erp.sync_po_hpp_to_gl(b.po_id,v_completed_at::date);
    if v_lot is not null then
      select coalesce(hpp_per_pcs,0) into v_hpp
      from erp.v_current_hpp where lot_id=v_lot;
      update erp.fg_stock_movements set unit_hpp_snapshot=v_hpp
      where lot_id=v_lot and movement_type='REWORK_IN'
        and source_type='REWORK_ORDER' and source_id=r.id;
    end if;
  end if;
end
$function$;

create or replace function public.erp_get_bs_resolution_workspace_v1(
  p_filter text default 'ACTIVE',p_kind text default 'ALL',
  p_pattern_id uuid default null,p_query text default null,
  p_limit integer default 50,p_offset integer default 0
)
returns jsonb language plpgsql stable security definer set search_path=''
as $function$
declare
  v_workspace jsonb;
  v_rows jsonb;
begin
  v_workspace:=erp.get_bs_resolution_workspace_v1(
    p_filter,p_kind,p_pattern_id,p_query,p_limit,p_offset
  );
  select coalesce(jsonb_agg(
    case when q.value->>'kind'='BS' then
      jsonb_set(
        q.value||jsonb_build_object(
          'accessory_bom',erp.bs_accessory_bom_options_v1(
            (q.value->>'id')::uuid,statement_timestamp()
          )
        ),
        '{rework_orders}',
        coalesce((
          select jsonb_agg(
            o.value||jsonb_build_object(
              'accessory_decision',erp.get_rework_accessory_decision_v1(
                (o.value->>'id')::uuid
              )
            ) order by o.ord
          )
          from jsonb_array_elements(q.value->'rework_orders')
            with ordinality as o(value,ord)
        ),'[]'::jsonb),true
      )
    else q.value||jsonb_build_object('accessory_bom',null) end
    order by q.ord
  ),'[]'::jsonb) into v_rows
  from jsonb_array_elements(v_workspace->'rows') with ordinality as q(value,ord);
  return jsonb_set(v_workspace,'{rows}',v_rows,true);
end
$function$;

alter table erp.bs_resolution_v2619a_rollback_capsule owner to postgres;
alter table erp.rework_accessory_decisions owner to postgres;
alter table erp.rework_accessory_selection_lines owner to postgres;
alter function erp.guard_rework_accessory_lineage_immutable() owner to postgres;
alter function erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone) owner to postgres;
alter function erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone) owner to postgres;
alter function erp.get_rework_accessory_decision_v1(uuid) owner to postgres;
alter function erp.save_rework_order_v2(jsonb,uuid,bigint) owner to postgres;
alter function erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint) owner to postgres;
alter function erp.ensure_fg_accessory_cost_snapshot(uuid) owner to postgres;
alter function erp.post_accessory_reimbursement_accrual(uuid) owner to postgres;
alter function erp.post_rework_completion(uuid) owner to postgres;
alter function public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer) owner to postgres;

revoke all on function
  erp.save_rework_order_v2(jsonb,uuid,bigint),
  erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint),
  erp.ensure_fg_accessory_cost_snapshot(uuid),
  erp.post_accessory_reimbursement_accrual(uuid),
  erp.post_rework_completion(uuid)
  from public,anon,authenticated;
revoke all on function
  public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)
  from public,anon,authenticated,service_role;
grant execute on function
  public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)
  to authenticated,service_role;

comment on table erp.rework_accessory_decisions is
  'Immutable per-order declaration of the accessory BOM subset actually installed during CP5 rework/rewash.';
comment on table erp.rework_accessory_selection_lines is
  'Immutable selected accessory BOM lines and monetary bases; only these lines may accrue on GOOD return.';
comment on function public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer) is
  'CP5 guarded workspace enriched with authoritative accessory BOM options and immutable per-order choices.';

do $post_guard$
declare
  v_bad text;
begin
  if (select count(*) from erp.bs_resolution_v2619a_rollback_capsule)<>6
     or exists(
       select 1 from erp.bs_resolution_v2619a_rollback_capsule
       where definition_sha256 is distinct from
         encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex')
     ) then raise exception 'ERP v2.6.19a post guard: rollback capsule drift'; end if;

  if exists(
    select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='erp'
      and c.relname in(
        'bs_resolution_v2619a_rollback_capsule',
        'rework_accessory_decisions','rework_accessory_selection_lines'
      ) and not c.relrowsecurity
  ) then raise exception 'ERP v2.6.19a post guard: private-table RLS is disabled'; end if;

  if has_table_privilege('anon','erp.rework_accessory_decisions','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.rework_accessory_decisions','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('anon','erp.rework_accessory_selection_lines','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.rework_accessory_selection_lines','SELECT,INSERT,UPDATE,DELETE') then
    raise exception 'ERP v2.6.19a post guard: accessory lineage table ACL is open';
  end if;
  if has_function_privilege('anon','public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','EXECUTE')
     or has_function_privilege('authenticated','erp.save_rework_order_v2(jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone)','EXECUTE')
     or has_function_privilege('authenticated','erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone)','EXECUTE')
     or has_function_privilege('authenticated','erp.get_rework_accessory_decision_v1(uuid)','EXECUTE') then
    raise exception 'ERP v2.6.19a post guard: facade/private function ACL failed';
  end if;

  if not exists(
    select 1 from pg_trigger
    where tgrelid='erp.rework_accessory_decisions'::regclass
      and tgname='trg_rework_accessory_decisions_immutable'
      and tgenabled<>'D' and not tgisinternal
  ) or not exists(
    select 1 from pg_trigger
    where tgrelid='erp.rework_accessory_selection_lines'::regclass
      and tgname='trg_rework_accessory_selection_lines_immutable'
      and tgenabled<>'D' and not tgisinternal
  ) then raise exception 'ERP v2.6.19a post guard: immutable-lineage trigger is missing'; end if;

  if to_regclass('erp.idx_bs_case_hold_events_actor') is null
     or to_regclass('erp.ux_rework_orders_good_fg_lot_v2619a') is null then
    raise exception 'ERP v2.6.19a post guard: required integrity/performance index is missing';
  end if;
  if pg_get_functiondef('erp.save_rework_order_v2(jsonb,uuid,bigint)'::regprocedure)
       not like '%accessory_bom_item_ids must be an explicit array%'
     or pg_get_functiondef('erp.save_rework_order_v2(jsonb,uuid,bigint)'::regprocedure)
       not like '%Cumulative rework return quantities cannot decrease%'
     or pg_get_functiondef('erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint)'::regprocedure)
       not like '%Final cumulative rework quantities cannot decrease%'
     or pg_get_functiondef('erp.ensure_fg_accessory_cost_snapshot(uuid)'::regprocedure)
       not like '%rework_accessory_selection_lines%'
     or pg_get_functiondef('erp.post_rework_completion(uuid)'::regprocedure)
       not like '%Link the lot before snapshotting%'
     or pg_get_functiondef('public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)'::regprocedure)
       not like '%accessory_bom%' then
    raise exception 'ERP v2.6.19a post guard: runtime contract is incomplete';
  end if;

  select string_agg(format('%s:%s',d.rework_order_id,d.decision_state),',' order by d.rework_order_id)
  into v_bad
  from erp.rework_accessory_decisions d
  left join lateral(
    select count(*)::integer line_count
    from erp.rework_accessory_selection_lines l where l.decision_id=d.id
  ) x on true
  where d.selected_item_count<>x.line_count;
  if v_bad is not null then
    raise exception 'ERP v2.6.19a post guard: decision/line count mismatch: %',v_bad;
  end if;
end
$post_guard$;

insert into erp.schema_migrations(version,description)
values(
  'v2.6.19a',
  'CP5 forward correction: immutable selected accessory BOM lineage, cumulative partial returns, selected-only HPP/reimbursement, and positive financial proof'
);

select pg_notify('pgrst','reload schema');
commit;
