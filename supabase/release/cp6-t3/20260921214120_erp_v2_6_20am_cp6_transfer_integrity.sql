-- CP6 AM: complete neutral transfers and location/roll history.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.audit_logs,erp.journal_entries,erp.journal_lines,
  erp.account_daily_balances,erp.sales_headers,erp.sales_items,
  erp.sale_stock_allocations,erp.sales_returns,erp.sales_return_items,
  erp.sales_payments,erp.fg_lots,erp.fg_stock_movements,
  erp.fg_inventory_balances,erp.hpp_versions,erp.product_conversions,
  erp.product_conversion_allocations,erp.laundry_deliveries,
  erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events,
  erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,erp.sales_payment_posting_facts,
  erp.sales_payment_reversal_facts,erp.cp6_v2620j_rollback_capsule,
  erp.cp6_v2620k_rollback_capsule,erp.accounting_period_control,
  erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts,
  erp.laundry_claims,erp.laundry_vendors,erp.cp6_v2620l_rollback_capsule,
  erp.opening_balance_headers,erp.opening_balance_items,
  erp.opening_subledger_balances,erp.opening_subledger_settlements,
  erp.opening_financial_corrections,erp.supplier_payments,
  erp.material_purchase_headers,erp.material_purchase_items,
  erp.material_supplier_invoices,erp.material_supplier_invoice_lines,
  erp.material_supplier_returns,erp.material_supplier_return_items,
  erp.material_purchase_cost_corrections,
  erp.material_purchase_cost_correction_items,erp.material_stock_movements,
  erp.material_rolls,erp.cost_recalc_queue,erp.cost_adjustments,
  erp.suppliers,erp.materials,erp.cp6_v2620m_rollback_capsule,
  erp.supplier_cent_posting_facts,erp.material_cost_history,
  erp.material_cost_revaluation_state,erp.material_cost_revaluation_events,
  erp.material_cost_checkpoints,erp.cp6_v2620n_rollback_capsule,
  erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,
  erp.cp6_v2620q_rollback_capsule,erp.cp6_v2620r_rollback_capsule,
  erp.cp6_v2620s_rollback_capsule,erp.material_adjustments,
  erp.material_adjustment_items,erp.material_adjustment_revaluation_facts,
  erp.cp6_v2620t_rollback_capsule,erp.cp6_v2620u_rollback_capsule,
  erp.misc_finance_transactions,erp.misc_finance_categories,
  erp.cp6_v2620v_rollback_capsule,erp.scrap_batches,erp.scrap_sales,
  erp.cp6_v2620w_rollback_capsule,erp.app_roles,erp.app_role_permissions,erp.app_permissions,erp.cutting_bridge_execution_context,erp.bs_resolution_execution_context,erp.cp6_laundry_qc_execution_context
in share row exclusive mode;

do $lock_all_erp_v2620am$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620am_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620am$;


do $predecessor_v2620am$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20al')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20am')
     or to_regclass('erp.cp6_v2620am_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620al_rollback_capsule') is null then raise exception 'AM_REQUIRES_EXACT_AL_WITHOUT_AM_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20al_cp6_opening_value_validation')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='20260917054049' and name='erp_v2_6_20al_cp6_opening_value_validation'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='2d16461cababd4a27827cfb8de01dd993a3a343460cdf049d427b44dd4cb6ea2')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260917054049')
     or (select count(*) from erp.cp6_v2620al_rollback_capsule)<>2 then raise exception 'AM_REQUIRES_EXACT_AL_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    ('erp.post_material_transfer_v2(uuid,uuid,bigint,text)','8fd42d9a97c72700ea121025290b63f5a081485d20e15057e6b8721509bfb1c4',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_transfer_v2(uuid,text,uuid,bigint)','75c9f545470fea44ef699c92a7fa67f1c8237f3f58c404cba6a81673b012f387',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.guard_material_negative_stock()','355c37d742415e1a99e073f8f80317607368ee9c43ec1da42981d5213aab68b3',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','50e9edac8803dea3ca8d39fc78b77fd1c4c5499820b37dbb390b13b32c233c92',array['postgres=X/postgres']::text[]),
    ('erp.refresh_material_cost_checkpoint(uuid,date)','7eea402dec46b03d5425ef9c1c052ca409de7fafa72000b7abef5fda6849b30a',array['postgres=X/postgres']::text[]),
    ('erp.save_material_transfer_draft_v2(jsonb,uuid,bigint)','68f54f8255c63943ae8ba48930506f748c7398f9888edec6e89f86ccf89f3a3b',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AM_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
end
$predecessor_v2620am$;


do $preexisting_transfer_v2620am$
begin
  if exists(select 1 from erp.material_transfers h where h.status<>'DRAFT' and
      (select count(*) from erp.material_stock_movements m
        where m.source_type='MATERIAL_TRANSFER' and m.source_id=h.id)
      <>2*(select count(*) from erp.material_transfer_items i where i.transfer_id=h.id))
    or exists(select 1 from erp.material_stock_movements m
      where m.source_type='MATERIAL_TRANSFER'
      group by m.source_id,m.material_id,m.roll_id
      having sum(m.qty_signed)<>0 or sum(m.qty_signed*m.unit_cost_snapshot)<>0)
    or exists(select 1 from erp.material_stock_movements rv
      join erp.material_stock_movements original on original.id=rv.reversal_of_id
      where original.source_type='MATERIAL_TRANSFER'
        and rv.unit_cost_snapshot is distinct from original.unit_cost_snapshot)
    or exists(select 1 from (
      select sum(m.qty_signed) over(partition by m.material_id,m.location_id,m.roll_id
        order by m.physical_at,m.system_created_at,m.id rows unbounded preceding) prefix
      from erp.material_stock_movements m where m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
    ) history where prefix<0) then
    raise exception 'AM_PREEXISTING_TRANSFER_OR_LOCATION_HISTORY_REVIEW_REQUIRED';
  end if;
end
$preexisting_transfer_v2620am$;

create table erp.cp6_v2620am_rollback_capsule(
  like erp.cp6_v2620al_rollback_capsule including all
);
alter table erp.cp6_v2620am_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620am_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620am_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,
    pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  array(select a::text from unnest(p.proacl) a order by a::text),
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in('erp.post_material_transfer_v2(uuid,uuid,bigint,text)'::regprocedure,'erp.reverse_material_transfer_v2(uuid,text,uuid,bigint)'::regprocedure,'erp.guard_material_negative_stock()'::regprocedure,'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'::regprocedure,'erp.refresh_material_cost_checkpoint(uuid,date)'::regprocedure,'erp.save_material_transfer_draft_v2(jsonb,uuid,bigint)'::regprocedure);


do $canonical_transfer_v2620am$
begin
  execute $definition$CREATE OR REPLACE FUNCTION erp.post_material_transfer_v2(p_transfer_id uuid, p_client_request_id uuid, p_expected_version bigint, p_reason text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_header erp.material_transfers%rowtype;
  r record;
  v_cost numeric(24,6);
  v_move_at timestamptz;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if nullif(btrim(p_reason), '') is null then raise exception 'Posting reason is required'; end if;
  v_hash := erp._request_hash(jsonb_build_object(
    'transfer_id', p_transfer_id, 'expected_version', p_expected_version,
    'reason', btrim(p_reason)
  ));
  v_cached := erp._idempotency_begin(
    'post_material_transfer_v2', p_client_request_id, v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason', btrim(p_reason), true);

  select * into v_header
  from erp.material_transfers where id = p_transfer_id for update;
  if v_header.id is null then raise exception 'Material transfer not found'; end if;
  if v_header.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_header.row_version;
  end if;
  if v_header.status <> 'DRAFT' then raise exception 'Material transfer must be DRAFT'; end if;
  if v_header.physical_at > clock_timestamp() + interval '5 minutes' then
    raise exception 'Transfer physical_at cannot be in the future';
  end if;
  perform 1 from erp.locations where id in(v_header.from_location_id,v_header.to_location_id)
    order by id for share;
  if not exists (
    select 1 from erp.locations l
    where l.id = v_header.from_location_id and l.is_active
      and l.location_type = 'RAW_MATERIAL_WAREHOUSE'
  ) or not exists (
    select 1 from erp.locations l
    where l.id = v_header.to_location_id and l.is_active
      and l.location_type = 'RAW_MATERIAL_WAREHOUSE'
  ) then
    raise exception 'Both transfer locations must be active raw-material warehouses';
  end if;
  if not exists (
    select 1 from erp.material_transfer_items i where i.transfer_id = v_header.id
  ) then raise exception 'Material transfer requires at least one line'; end if;

  -- Serialize the complete material set before reading prices or stock.
  -- Item writes use the same locked DRAFT header through the existing API.
  perform 1 from erp.accounting_period_control where singleton_id=1 for share;
  perform 1 from erp.materials m
  where exists(select 1 from erp.material_transfer_items i
    where i.transfer_id=v_header.id and i.material_id=m.id)
  order by m.id for update;

  -- Re-read after every lock wait. Never filter an invalid line out of a POST.
  if exists(select 1 from erp.material_transfer_items i
    left join erp.materials m on m.id=i.material_id
    where i.transfer_id=v_header.id and (m.id is null or not m.is_active)) then
    raise exception 'AM_TRANSFER_REQUIRES_EVERY_MATERIAL_ACTIVE';
  end if;
  if exists(select 1 from erp.material_transfer_items i join erp.materials m on m.id=i.material_id
    where i.transfer_id=v_header.id and
      (i.qty<=0 or i.qty::text in('NaN','Infinity','-Infinity')
       or (m.material_type='FABRIC')<>(i.roll_id is not null)
       or (i.roll_id is not null and not exists(select 1 from erp.material_rolls mr
          where mr.id=i.roll_id and mr.material_id=i.material_id)))) then
    raise exception 'AM_TRANSFER_INVALID_QUANTITY_OR_ROLL_LINEAGE';
  end if;

  for r in
    select i.*, m.moving_average_cost
    from erp.material_transfer_items i
    join erp.materials m on m.id = i.material_id
    where i.transfer_id = v_header.id
    order by i.material_id, i.roll_id nulls first, i.id
  loop
    perform pg_advisory_xact_lock(hashtextextended(
      'MATTRANSFER|' || r.material_id::text || '|' ||
      coalesce(r.roll_id::text, 'NO_ROLL'), 0
    ));
    -- Transfers have no independent acquisition price. The chronological
    -- replay derives both original snapshots from the actual OUT cost.
    v_cost := null;
    v_move_at := greatest(clock_timestamp(),v_move_at+interval '1 microsecond');
    insert into erp.material_stock_movements(
      material_id, roll_id, location_id, movement_type, qty_signed,
      input_unit_cost, source_type, source_id, physical_at, system_created_at, created_by, note
    ) values (
      r.material_id, r.roll_id, v_header.from_location_id, 'TRANSFER_OUT', -r.qty,
      v_cost, 'MATERIAL_TRANSFER', v_header.id, v_header.physical_at, v_move_at,
      erp.current_app_user_id(), coalesce(r.notes, 'Warehouse transfer out')
    );
    v_move_at := greatest(clock_timestamp(),v_move_at+interval '1 microsecond');
    insert into erp.material_stock_movements(
      material_id, roll_id, location_id, movement_type, qty_signed,
      input_unit_cost, source_type, source_id, physical_at, system_created_at, created_by, note
    ) values (
      r.material_id, r.roll_id, v_header.to_location_id, 'TRANSFER_IN', r.qty,
      v_cost, 'MATERIAL_TRANSFER', v_header.id, v_header.physical_at, v_move_at,
      erp.current_app_user_id(), coalesce(r.notes, 'Warehouse transfer in')
    );
  end loop;

  for r in
    select distinct material_id
    from erp.material_transfer_items where transfer_id = v_header.id
  loop
    perform erp.recalculate_material_cost(r.material_id);
  end loop;

  if (select count(*) from erp.material_stock_movements
      where source_type='MATERIAL_TRANSFER' and source_id=v_header.id)
     <>2*(select count(*) from erp.material_transfer_items where transfer_id=v_header.id) then
    raise exception 'AM_TRANSFER_INCOMPLETE_MOVEMENT_SET';
  end if;

  update erp.material_transfers
  set status = 'POSTED', posted_at = clock_timestamp()
  where id = v_header.id
  returning * into v_header;

  v_response := jsonb_build_object(
    'material_transfer_id', v_header.id,
    'status', v_header.status,
    'row_version', v_header.row_version,
    'posted_at', v_header.posted_at,
    'movement_count', (
      select count(*) from erp.material_stock_movements m
      where m.source_type = 'MATERIAL_TRANSFER' and m.source_id = v_header.id
    )
  );
  return erp._idempotency_complete(
    'post_material_transfer_v2', p_client_request_id, v_response
  );
end;
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.reverse_material_transfer_v2(p_transfer_id uuid, p_reason text, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_header erp.material_transfers%rowtype;
  r record;
begin
  perform erp.require_owner_admin();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if nullif(btrim(p_reason), '') is null then raise exception 'Reversal reason is required'; end if;
  v_hash := erp._request_hash(jsonb_build_object(
    'transfer_id', p_transfer_id, 'reason', btrim(p_reason),
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(
    'reverse_material_transfer_v2', p_client_request_id, v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason', btrim(p_reason), true);

  select * into v_header
  from erp.material_transfers where id = p_transfer_id for update;
  if v_header.id is null then raise exception 'Material transfer not found'; end if;
  if v_header.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_header.row_version;
  end if;
  if v_header.status <> 'POSTED' then raise exception 'Only POSTED transfer can be reversed'; end if;
  if exists (
    select 1
    from erp.material_stock_movements original
    join erp.material_stock_movements rv on rv.reversal_of_id = original.id
    where original.source_type = 'MATERIAL_TRANSFER'
      and original.source_id = v_header.id
  ) then raise exception 'Material transfer already has reversal movements'; end if;

  -- Serialize the complete material set before reading prices or stock.
  -- Item writes use the same locked DRAFT header through the existing API.
  perform 1 from erp.accounting_period_control where singleton_id=1 for share;
  perform 1 from erp.materials m
  where exists(select 1 from erp.material_transfer_items i
    where i.transfer_id=v_header.id and i.material_id=m.id)
  order by m.id for update;

  -- Reverse destination IN first so the normal negative-stock guard proves the
  -- destination still owns the quantity. Only then restore the source OUT.
  for r in
    select original.*
    from erp.material_stock_movements original
    where original.source_type = 'MATERIAL_TRANSFER'
      and original.source_id = v_header.id
    order by case original.movement_type when 'TRANSFER_IN' then 0 else 1 end,
             original.system_created_at, original.id
  loop
    insert into erp.material_stock_movements(
      material_id, roll_id, location_id, movement_type, qty_signed,
      input_unit_cost, unit_cost_snapshot, source_type, source_id, physical_at, created_by,
      reversal_of_id, note
    ) values (
      r.material_id, r.roll_id, r.location_id, 'REVERSAL', -r.qty_signed,
      r.unit_cost_snapshot, r.unit_cost_snapshot, 'MATERIAL_TRANSFER_REVERSAL', v_header.id,
      greatest(clock_timestamp(), r.physical_at), erp.current_app_user_id(),
      r.id, btrim(p_reason)
    );
  end loop;

  for r in
    select distinct material_id
    from erp.material_transfer_items where transfer_id = v_header.id
  loop
    perform erp.recalculate_material_cost(r.material_id);
  end loop;

  update erp.material_transfers
  set status = 'REVERSED', reversed_at = clock_timestamp(),
      reversal_reason = btrim(p_reason)
  where id = v_header.id
  returning * into v_header;

  v_response := jsonb_build_object(
    'material_transfer_id', v_header.id,
    'status', v_header.status,
    'row_version', v_header.row_version,
    'reversed_at', v_header.reversed_at,
    'reversal_movement_count', (
      select count(*)
      from erp.material_stock_movements m
      where m.source_type = 'MATERIAL_TRANSFER_REVERSAL'
        and m.source_id = v_header.id
    )
  );
  return erp._idempotency_complete(
    'reverse_material_transfer_v2', p_client_request_id, v_response
  );
end;
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.guard_material_negative_stock()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_available numeric(24,6);
begin
  -- All legs acquire the material row before location/roll locks and FK
  -- checks, in the same order as chronological recost. The next SQL
  -- statement observes the latest committed stock after any wait.
  perform 1 from erp.accounting_period_control where singleton_id=1 for share;
  perform 1 from erp.materials where id=new.material_id for update;
  if not found then raise exception 'Material not found'; end if;
  if new.qty_signed>=0 then return new; end if;
  if new.location_id is null then raise exception 'Material OUT movement requires location_id'; end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'MATSTOCK|'||new.material_id::text||'|'||coalesce(new.roll_id::text,'NO_ROLL')||'|'||new.location_id::text,0
  ));

  if new.source_type='MATERIAL_PURCHASE_REVERSAL'
     and current_setting('erp.allow_source_replacement_negative',true)='on' then
    return new;
  end if;

  if new.roll_id is not null then
    select coalesce(sum(qty_signed),0) into v_available from erp.material_stock_movements
    where material_id=new.material_id and roll_id=new.roll_id and location_id=new.location_id;
  else
    select coalesce(sum(qty_signed),0) into v_available from erp.material_stock_movements
    where material_id=new.material_id and roll_id is null and location_id=new.location_id;
  end if;
  if v_available+new.qty_signed < -0.000001 then
    raise exception 'Material stock would become negative at selected location/roll. Available %, requested out %',v_available,abs(new.qty_signed);
  end if;
  return new;
end;
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp._recalculate_material_cost_core(p_material_id uuid, p_recalc_from timestamp with time zone, p_allow_checkpoint boolean)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r erp.material_stock_movements%rowtype;
  rr record;
  v_stock numeric(18,6):=0;
  v_avg numeric(18,6):=0;
  v_stock_before numeric(18,6);
  v_avg_before numeric(18,6);
  v_cost numeric(18,6);
  v_new_stock numeric(18,6);
  v_new_avg numeric(18,6);
  v_closed date;
  v_cp erp.material_cost_checkpoints%rowtype;
  v_use_checkpoint boolean:=false;
  v_cutoff timestamptz;
  v_transfer_pairs jsonb;
  v_transfer_rows bigint;
  v_transfer_pair_count bigint;
  v_location_minimum numeric;
begin
  perform erp.require_internal();
  select closed_through into v_closed from erp.accounting_period_control where singleton_id=1 for share;
  perform 1 from erp.materials where id=p_material_id for update;
  if not found then raise exception 'Material not found'; end if;

  with active as (
    select m.*,row_number() over(partition by m.source_id,m.roll_id,m.physical_at,
        abs(m.qty_signed),m.movement_type order by m.system_created_at,m.id) ordinal
    from erp.material_stock_movements m
    where m.material_id=p_material_id and m.source_type='MATERIAL_TRANSFER'
      and m.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
  ), pairs as (
    select i.id incoming,o.id outgoing
    from active i join active o on o.source_id=i.source_id
      and o.roll_id is not distinct from i.roll_id and o.physical_at=i.physical_at
      and o.qty_signed=-i.qty_signed and o.ordinal=i.ordinal
      and o.movement_type='TRANSFER_OUT' and o.qty_signed<0
    where i.movement_type='TRANSFER_IN' and i.qty_signed>0
      and (o.physical_at,o.system_created_at,o.id)<(i.physical_at,i.system_created_at,i.id)
      and o.location_id<>i.location_id
  )
  select coalesce((select jsonb_object_agg(incoming::text,outgoing::text) from pairs),'{}'::jsonb),
    (select count(*) from active),(select count(*) from pairs)
  into v_transfer_pairs,v_transfer_rows,v_transfer_pair_count;
  if v_transfer_rows<>2*v_transfer_pair_count then
    raise exception 'AM_TRANSFER_PAIR_LINEAGE_UNPROVEN for material %',p_material_id;
  end if;

  -- The cost engine excludes a source and its linked inverse together. Apply
  -- the identical effective-history rule at each physical location/roll too;
  -- this preserves atomic receipt replacement and existing cancellation rules.
  select min(prefix) into v_location_minimum from (
    select sum(m.qty_signed) over(partition by m.location_id,m.roll_id
      order by m.physical_at,coalesce(o.system_created_at,m.system_created_at),
        coalesce(o.id,m.id),(o.id is not null) rows unbounded preceding) prefix
    from erp.material_stock_movements m
    left join erp.material_stock_movements o on o.id=(v_transfer_pairs->>m.id::text)::uuid
    where m.material_id=p_material_id and m.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
  ) effective_history;
  if v_location_minimum<0 then
    raise exception 'AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY for material %',p_material_id;
  end if;

  if p_allow_checkpoint and p_recalc_from is not null and v_closed is not null then
    select * into v_cp from erp.material_cost_checkpoints where material_id=p_material_id;
    if v_cp.material_id is not null
       and v_cp.checkpoint_date<=v_closed
       and erp._cp3_business_date(p_recalc_from)>v_cp.checkpoint_date then
      v_cutoff:=((v_cp.checkpoint_date+1)::timestamp at time zone 'Asia/Jakarta');

  if exists(
    with history as (
      select msm.id,msm.qty_signed,msm.unit_cost_snapshot,msm.movement_type,msm.source_type,
        h.movement_id,h.stock_before,h.stock_after,h.average_before,h.average_after,
        h.movement_qty,h.movement_unit_cost,paired_out.unit_cost_snapshot paired_cost,
        sum(msm.qty_signed) over w expected_stock,
        lag(h.average_after,1,0::numeric) over w previous_average
      from erp.material_stock_movements msm
      left join erp.material_cost_history h on h.movement_id=msm.id and h.material_id=msm.material_id
      left join erp.material_stock_movements paired_out on paired_out.id=(v_transfer_pairs->>msm.id::text)::uuid
      where msm.material_id=p_material_id and msm.physical_at<v_cutoff
        and msm.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
      window w as(order by msm.physical_at,coalesce(paired_out.system_created_at,msm.system_created_at),
        coalesce(paired_out.id,msm.id),(paired_out.id is not null) rows unbounded preceding)
    )
    select 1 from history where movement_id is null
      or movement_qty is distinct from qty_signed
      or movement_unit_cost is distinct from unit_cost_snapshot
      or stock_before is distinct from expected_stock-qty_signed
      or stock_after is distinct from expected_stock
      or average_before is distinct from previous_average
      or (qty_signed<0 and movement_unit_cost is distinct from average_before)
      or (movement_type='TRANSFER_IN' and source_type='MATERIAL_TRANSFER'
          and movement_unit_cost is distinct from paired_cost)
      or average_after is distinct from case
        when stock_after=0 then 0
        when qty_signed<0 then average_before
        else round((stock_before*average_before+qty_signed*movement_unit_cost)/nullif(stock_after,0),6)
      end
  ) then
    raise exception 'AM_LEGACY_COST_CHECKPOINT_REQUIRES_HISTORY_REVIEW for material %',p_material_id;
  end if;

      v_use_checkpoint:=true;
      v_stock:=v_cp.stock_qty;
      v_avg:=v_cp.moving_average_cost;
    end if;
  end if;

  if v_use_checkpoint then
    if v_cp.last_movement_id is null then
      delete from erp.material_cost_history where material_id=p_material_id;
    else
      delete from erp.material_cost_history h
      using erp.material_stock_movements msm
      where h.material_id=p_material_id and h.movement_id=msm.id
        and erp._cp3_business_date(msm.physical_at)>v_cp.checkpoint_date;
    end if;
  else
    delete from erp.material_cost_history where material_id=p_material_id;
  end if;

  for r in
    select msm.* from erp.material_stock_movements msm
  left join erp.material_stock_movements paired_out
    on paired_out.id=(v_transfer_pairs->>msm.id::text)::uuid
    where msm.material_id=p_material_id
      and msm.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
      and (
        not v_use_checkpoint
        or v_cp.last_movement_id is null
        or erp._cp3_business_date(msm.physical_at)>v_cp.checkpoint_date
      )
    order by msm.physical_at,coalesce(paired_out.system_created_at,msm.system_created_at),
      coalesce(paired_out.id,msm.id),(paired_out.id is not null)
    for update of msm
  loop
    v_stock_before:=v_stock;
    v_avg_before:=v_avg;
    if r.qty_signed>0 then
      if r.movement_type='TRANSFER_IN' and r.source_type='MATERIAL_TRANSFER' then
        -- The paired OUT must already have been replayed (or retained by the
        -- closed-period checkpoint). Its historical cost is the incoming cost,
        -- including a transfer of the entire balance that temporarily hits 0.
        select o.unit_cost_snapshot into v_cost
        from erp.material_stock_movements o
        join erp.material_cost_history h on h.movement_id=o.id and h.material_id=o.material_id
        where o.id=(v_transfer_pairs->>r.id::text)::uuid and o.material_id=p_material_id
          and o.is_cost_recalculated;
        if not found or v_cost is null then
          raise exception 'AM_TRANSFER_OUT_COST_NOT_REPLAYED for movement %',r.id;
        end if;
      elsif r.movement_type='REVERSAL' and r.reversal_of_id is not null then
        select x.unit_cost_snapshot into v_cost from erp.material_stock_movements x where x.id=r.reversal_of_id;
        v_cost:=coalesce(v_cost,r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      elsif r.movement_type='CUTTING_RETURN' and r.source_type='CUTTING_GROUP_RETURN' then
        select x.unit_cost_snapshot into v_cost
        from erp.material_stock_movements x
        where x.material_id=r.material_id
          and x.source_type='CUTTING_GROUP' and x.source_id=r.source_id
          and x.movement_type='CUTTING_ISSUE'
          and x.roll_id is not distinct from r.roll_id
        order by x.physical_at desc,x.system_created_at desc,x.id desc limit 1;
        v_cost:=coalesce(v_cost,r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      else
        v_cost:=coalesce(r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      end if;
      v_new_stock:=v_stock+r.qty_signed;
      if v_new_stock>0 then
        v_new_avg:=((v_stock*v_avg)+(r.qty_signed*v_cost))/v_new_stock;
      else
        v_new_avg:=0;
      end if;
    else
      v_new_stock:=v_stock+r.qty_signed;
      if v_new_stock<0 then
        raise exception 'Backdate/correction would create negative material stock for material %, movement %',p_material_id,r.id;
      end if;
      v_cost:=v_avg;
      v_new_avg:=case when v_new_stock=0 then 0 else v_avg end;
    end if;

    update erp.material_stock_movements
    set original_unit_cost_snapshot=coalesce(original_unit_cost_snapshot,v_cost),
        unit_cost_snapshot=v_cost,
        is_cost_recalculated=true
    where id=r.id;

    insert into erp.material_cost_history(material_id,movement_id,physical_at,stock_before,average_before,movement_qty,movement_unit_cost,stock_after,average_after)
    values(p_material_id,r.id,r.physical_at,v_stock_before,v_avg_before,r.qty_signed,v_cost,v_new_stock,v_new_avg);
    v_stock:=v_new_stock;
    v_avg:=v_new_avg;
  end loop;

  for rr in
    select mr.id as roll_id,coalesce(sum(msm.qty_signed),0)::numeric as roll_qty
    from erp.material_rolls mr
    left join erp.material_stock_movements msm on msm.roll_id=mr.id
    where mr.material_id=p_material_id
    group by mr.id
  loop
    if rr.roll_qty<0 then raise exception 'Correction would create negative roll stock for roll %',rr.roll_id; end if;
    update erp.material_rolls
    set cached_qty=rr.roll_qty,
        status=case when rr.roll_qty=0 then 'EXHAUSTED' when rr.roll_qty<original_qty then 'HALF_USED' else 'AVAILABLE' end,
        updated_at=statement_timestamp()
    where id=rr.roll_id and status<>'RETURNED_SUPPLIER';
  end loop;

  update erp.cutting_group_rolls cgr
  set unit_cost_snapshot=(
    select msm.unit_cost_snapshot
    from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CUTTING_GROUP'
      and msm.source_id=cgr.cutting_group_id and msm.movement_type='CUTTING_ISSUE'
      and msm.roll_id is not distinct from cgr.roll_id
    order by msm.physical_at desc,msm.system_created_at desc,msm.id desc limit 1
  )
  where exists(
    select 1 from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CUTTING_GROUP'
      and msm.source_id=cgr.cutting_group_id and msm.movement_type='CUTTING_ISSUE'
      and msm.roll_id is not distinct from cgr.roll_id
  );

  update erp.contractor_material_issue_items ii
  set unit_cost_snapshot=(
    select msm.unit_cost_snapshot from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
      and msm.source_id=ii.id and msm.movement_type='CONTRACTOR_ISSUE'
    order by msm.physical_at desc,msm.system_created_at desc,msm.id desc limit 1
  )
  where ii.material_id=p_material_id and exists(
    select 1 from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
      and msm.source_id=ii.id and msm.movement_type='CONTRACTOR_ISSUE'
  );

  update erp.materials set cached_stock_qty=v_stock,moving_average_cost=v_avg,updated_at=statement_timestamp() where id=p_material_id;

  perform erp.sync_material_cost_revaluation(p_material_id);

  insert into erp.cost_recalc_queue(entity_type,entity_id,recalc_from,reason)
  select distinct 'PO',cg.po_id,min(msm.physical_at),'Material moving-average/backdate recalculation'
  from erp.material_stock_movements msm
  join erp.cutting_groups cg on msm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and msm.source_id=cg.id
  where msm.material_id=p_material_id
    and exists(select 1 from erp.fg_lots fl where fl.po_id=cg.po_id)
    and not exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO' and q.entity_id=cg.po_id and (q.status in('PENDING','RUNNING') or (q.status='FAILED' and q.attempt_count<3)))
  group by cg.po_id;

  insert into erp.cost_recalc_queue(entity_type,entity_id,recalc_from,reason)
  select distinct 'PO',cmi.po_id,min(msm.physical_at),'Contractor material moving-average/backdate recalculation'
  from erp.material_stock_movements msm
  join erp.contractor_material_issue_items ii on msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and msm.source_id=ii.id
  join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
  where msm.material_id=p_material_id and cmi.po_id is not null
    and exists(select 1 from erp.fg_lots fl where fl.po_id=cmi.po_id)
    and not exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO' and q.entity_id=cmi.po_id and (q.status in('PENDING','RUNNING') or (q.status='FAILED' and q.attempt_count<3)))
  group by cmi.po_id;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('materials',p_material_id,'RECALCULATE',jsonb_build_object('cached_stock_qty',v_stock,'moving_average_cost',v_avg,'original_movement_snapshots_preserved',true,'gl_revaluation_synced',true,'checkpoint_used',v_use_checkpoint,'recalc_from',p_recalc_from),erp.current_app_user_id(),'Material chronological moving-average recalculation');

  perform erp.refresh_accessory_hpp_after_material_recost(p_material_id,'Material chronological moving-average recalculation');

  if not v_use_checkpoint and v_closed is not null then
    perform erp.refresh_material_cost_checkpoint(p_material_id,v_closed);
  end if;
end;
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.refresh_material_cost_checkpoint(p_material_id uuid, p_checkpoint_date date)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_stock numeric(18,6):=0;
  v_avg numeric(18,6):=0;
  v_last_physical timestamptz;
  v_last_system timestamptz;
  v_last_id uuid;
  v_has_active boolean;
  v_cutoff timestamptz;
  v_transfer_pairs jsonb;
  v_transfer_rows bigint;
  v_transfer_pair_count bigint;
  v_location_minimum numeric;
begin
  perform erp.require_internal();
  if p_checkpoint_date is null then raise exception 'Checkpoint date is required'; end if;
  v_cutoff:=((p_checkpoint_date+1)::timestamp at time zone 'Asia/Jakarta');
  perform 1 from erp.materials where id=p_material_id for update;
  if not found then raise exception 'Material not found'; end if;

  with active as (
    select m.*,row_number() over(partition by m.source_id,m.roll_id,m.physical_at,
        abs(m.qty_signed),m.movement_type order by m.system_created_at,m.id) ordinal
    from erp.material_stock_movements m
    where m.material_id=p_material_id and m.source_type='MATERIAL_TRANSFER'
      and m.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
  ), pairs as (
    select i.id incoming,o.id outgoing
    from active i join active o on o.source_id=i.source_id
      and o.roll_id is not distinct from i.roll_id and o.physical_at=i.physical_at
      and o.qty_signed=-i.qty_signed and o.ordinal=i.ordinal
      and o.movement_type='TRANSFER_OUT' and o.qty_signed<0
    where i.movement_type='TRANSFER_IN' and i.qty_signed>0
      and (o.physical_at,o.system_created_at,o.id)<(i.physical_at,i.system_created_at,i.id)
      and o.location_id<>i.location_id
  )
  select coalesce((select jsonb_object_agg(incoming::text,outgoing::text) from pairs),'{}'::jsonb),
    (select count(*) from active),(select count(*) from pairs)
  into v_transfer_pairs,v_transfer_rows,v_transfer_pair_count;
  if v_transfer_rows<>2*v_transfer_pair_count then
    raise exception 'AM_TRANSFER_PAIR_LINEAGE_UNPROVEN for material %',p_material_id;
  end if;

  -- The cost engine excludes a source and its linked inverse together. Apply
  -- the identical effective-history rule at each physical location/roll too;
  -- this preserves atomic receipt replacement and existing cancellation rules.
  select min(prefix) into v_location_minimum from (
    select sum(m.qty_signed) over(partition by m.location_id,m.roll_id
      order by m.physical_at,coalesce(o.system_created_at,m.system_created_at),
        coalesce(o.id,m.id),(o.id is not null) rows unbounded preceding) prefix
    from erp.material_stock_movements m
    left join erp.material_stock_movements o on o.id=(v_transfer_pairs->>m.id::text)::uuid
    where m.material_id=p_material_id and m.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
  ) effective_history;
  if v_location_minimum<0 then
    raise exception 'AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY for material %',p_material_id;
  end if;

  if exists(
    with history as (
      select msm.id,msm.qty_signed,msm.unit_cost_snapshot,msm.movement_type,msm.source_type,
        h.movement_id,h.stock_before,h.stock_after,h.average_before,h.average_after,
        h.movement_qty,h.movement_unit_cost,paired_out.unit_cost_snapshot paired_cost,
        sum(msm.qty_signed) over w expected_stock,
        lag(h.average_after,1,0::numeric) over w previous_average
      from erp.material_stock_movements msm
      left join erp.material_cost_history h on h.movement_id=msm.id and h.material_id=msm.material_id
      left join erp.material_stock_movements paired_out on paired_out.id=(v_transfer_pairs->>msm.id::text)::uuid
      where msm.material_id=p_material_id and msm.physical_at<v_cutoff
        and msm.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
      window w as(order by msm.physical_at,coalesce(paired_out.system_created_at,msm.system_created_at),
        coalesce(paired_out.id,msm.id),(paired_out.id is not null) rows unbounded preceding)
    )
    select 1 from history where movement_id is null
      or movement_qty is distinct from qty_signed
      or movement_unit_cost is distinct from unit_cost_snapshot
      or stock_before is distinct from expected_stock-qty_signed
      or stock_after is distinct from expected_stock
      or average_before is distinct from previous_average
      or (qty_signed<0 and movement_unit_cost is distinct from average_before)
      or (movement_type='TRANSFER_IN' and source_type='MATERIAL_TRANSFER'
          and movement_unit_cost is distinct from paired_cost)
      or average_after is distinct from case
        when stock_after=0 then 0
        when qty_signed<0 then average_before
        else round((stock_before*average_before+qty_signed*movement_unit_cost)/nullif(stock_after,0),6)
      end
  ) then
    raise exception 'AM_LEGACY_COST_CHECKPOINT_REQUIRES_HISTORY_REVIEW for material %',p_material_id;
  end if;

  select exists(
    select 1 from erp.material_stock_movements msm
    where msm.material_id=p_material_id
      and msm.physical_at<v_cutoff
      and msm.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
  ) into v_has_active;

  select h.stock_after,h.average_after,msm.physical_at,msm.system_created_at,msm.id
  into v_stock,v_avg,v_last_physical,v_last_system,v_last_id
  from erp.material_stock_movements msm
  join erp.material_cost_history h on h.movement_id=msm.id and h.material_id=p_material_id
  left join erp.material_stock_movements paired_out
    on paired_out.id=(v_transfer_pairs->>msm.id::text)::uuid
  where msm.material_id=p_material_id
    and msm.physical_at<v_cutoff
    and msm.reversal_of_id is null
    and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
  order by msm.physical_at desc,coalesce(paired_out.system_created_at,msm.system_created_at) desc,
    coalesce(paired_out.id,msm.id) desc,(paired_out.id is not null) desc
  limit 1;

  if v_has_active and v_last_id is null then
    raise exception 'Cannot checkpoint material %: chronological cost history is incomplete before %',p_material_id,p_checkpoint_date;
  end if;
  if not v_has_active then
    v_stock:=0; v_avg:=0; v_last_physical:=null; v_last_system:=null; v_last_id:=null;
  end if;

  insert into erp.material_cost_checkpoints(material_id,checkpoint_date,stock_qty,moving_average_cost,last_physical_at,last_system_created_at,last_movement_id,checkpoint_created_at)
  values(p_material_id,p_checkpoint_date,coalesce(v_stock,0),coalesce(v_avg,0),v_last_physical,v_last_system,v_last_id,clock_timestamp())
  on conflict(material_id) do update
  set checkpoint_date=excluded.checkpoint_date,
      stock_qty=excluded.stock_qty,
      moving_average_cost=excluded.moving_average_cost,
      last_physical_at=excluded.last_physical_at,
      last_system_created_at=excluded.last_system_created_at,
      last_movement_id=excluded.last_movement_id,
      checkpoint_created_at=excluded.checkpoint_created_at;
end;
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.save_material_transfer_draft_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_id uuid := nullif(p_payload->>'id', '')::uuid;
  v_action text := upper(coalesce(nullif(btrim(p_payload->>'action'), ''), 'SAVE'));
  v_reason text := nullif(btrim(p_payload->>'change_reason'), '');
  v_header erp.material_transfers%rowtype;
  v_line jsonb;
begin
  perform erp.require_internal();
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if v_action not in ('SAVE','DELETE') then raise exception 'action must be SAVE or DELETE'; end if;
  if v_action = 'SAVE' and coalesce(jsonb_typeof(p_payload->'items'), 'null') <> 'array' then
    raise exception 'items must be a JSON array';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload, 'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(
    'save_material_transfer_draft_v2', p_client_request_id, v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason', v_reason, true);

  if v_id is null then
    if v_action = 'DELETE' then raise exception 'Transfer id is required for DELETE'; end if;
    if p_expected_version is not null then
      raise exception 'expected_version must be null when creating a transfer';
    end if;
    if coalesce(btrim(p_payload->>'transfer_number'), '') = '' then
      raise exception 'transfer_number is required';
    end if;
    insert into erp.material_transfers(
      transfer_number, from_location_id, to_location_id, physical_at,
      status, notes, created_by
    ) values (
      btrim(p_payload->>'transfer_number'),
      (p_payload->>'from_location_id')::uuid,
      (p_payload->>'to_location_id')::uuid,
      (p_payload->>'physical_at')::timestamptz,
      'DRAFT', nullif(btrim(p_payload->>'notes'), ''), erp.current_app_user_id()
    ) returning * into v_header;
    v_id := v_header.id;
  else
    if p_expected_version is null then raise exception 'expected_version is required'; end if;
    select * into v_header from erp.material_transfers where id = v_id for update;
    if v_header.id is null then raise exception 'Material transfer not found'; end if;
    if v_header.row_version <> p_expected_version then
      raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_header.row_version;
    end if;
    if v_header.status <> 'DRAFT' then
      raise exception 'Only DRAFT material transfer can be saved/deleted';
    end if;
    if v_action = 'DELETE' then
      -- Remove DRAFT children while their locked parent still exists;
      -- the original parent trigger must continue validating every row.
      delete from erp.material_transfer_items where transfer_id=v_id;
      delete from erp.material_transfers where id = v_id;
      v_response := jsonb_build_object('material_transfer_id', v_id, 'status', 'DELETED');
      return erp._idempotency_complete(
        'save_material_transfer_draft_v2', p_client_request_id, v_response
      );
    end if;
    update erp.material_transfers
    set transfer_number = coalesce(
          nullif(btrim(p_payload->>'transfer_number'), ''), v_header.transfer_number
        ),
        from_location_id = case when p_payload ? 'from_location_id'
          then (p_payload->>'from_location_id')::uuid else v_header.from_location_id end,
        to_location_id = case when p_payload ? 'to_location_id'
          then (p_payload->>'to_location_id')::uuid else v_header.to_location_id end,
        physical_at = coalesce(
          nullif(p_payload->>'physical_at', '')::timestamptz, v_header.physical_at
        ),
        notes = case when p_payload ? 'notes'
          then nullif(btrim(p_payload->>'notes'), '') else v_header.notes end
    where id = v_id
    returning * into v_header;
  end if;

  if jsonb_array_length(p_payload->'items') = 0 then
    raise exception 'At least one transfer item is required';
  end if;
  delete from erp.material_transfer_items where transfer_id = v_id;
  for v_line in select value from jsonb_array_elements(p_payload->'items') loop
    insert into erp.material_transfer_items(
      id, transfer_id, material_id, roll_id, qty, notes
    ) values (
      coalesce(nullif(v_line->>'id', '')::uuid, gen_random_uuid()),
      v_id, (v_line->>'material_id')::uuid,
      nullif(v_line->>'roll_id', '')::uuid,
      (v_line->>'qty')::numeric,
      nullif(btrim(v_line->>'notes'), '')
    );
  end loop;
  select * into v_header from erp.material_transfers where id = v_id;
  v_response := jsonb_build_object(
    'material_transfer_id', v_header.id,
    'transfer_number', v_header.transfer_number,
    'status', v_header.status,
    'row_version', v_header.row_version,
    'item_count', (select count(*) from erp.material_transfer_items i where i.transfer_id = v_id),
    'total_qty', (select sum(i.qty) from erp.material_transfer_items i where i.transfer_id = v_id)
  );
  return erp._idempotency_complete(
    'save_material_transfer_draft_v2', p_client_request_id, v_response
  );
end;
$function$
$definition$;
end
$canonical_transfer_v2620am$;

do $installed_v2620am$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620am_rollback_capsule)<>6 then
    raise exception 'AM_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620am_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp.post_material_transfer_v2(uuid,uuid,bigint,text)','8fd42d9a97c72700ea121025290b63f5a081485d20e15057e6b8721509bfb1c4','e5ab13793e89dfc91480389eac86f67310282c78247b62d4dbaf9482582ae5bb',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_transfer_v2(uuid,text,uuid,bigint)','75c9f545470fea44ef699c92a7fa67f1c8237f3f58c404cba6a81673b012f387','e972291e00dea5611147389bd24dd9302ef20af78e6c4aa78fd1ec8aa54b5f21',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.guard_material_negative_stock()','355c37d742415e1a99e073f8f80317607368ee9c43ec1da42981d5213aab68b3','12051cc7a967fb83b4d0a5a7b3102b7a3a83399b73b2abb4749b5b0b5042416e',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','50e9edac8803dea3ca8d39fc78b77fd1c4c5499820b37dbb390b13b32c233c92','2069e292b0c43850a19469ae20af36616e396840619e72c43d204e209154987d',array['postgres=X/postgres']::text[]),
    ('erp.refresh_material_cost_checkpoint(uuid,date)','7eea402dec46b03d5425ef9c1c052ca409de7fafa72000b7abef5fda6849b30a','316775456f047127bffdb35310d5c0fd73024116368bfb349c5fe8218951f603',array['postgres=X/postgres']::text[]),
    ('erp.save_material_transfer_draft_v2(jsonb,uuid,bigint)','68f54f8255c63943ae8ba48930506f748c7398f9888edec6e89f86ccf89f3a3b','62cc5bead40f163681487b072299ffae411028a5249b7d533816fcf6e7169bd1',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620am_rollback_capsule
      where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'AM_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;

end
$installed_v2620am$;

do $boundary_v2620am$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620am_rollback_capsule') order by c.relname loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>225 then
    raise exception 'AM_FULL_ERP_BOUNDARY_CARDINALITY expected225 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620am_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620am$;

insert into erp.schema_migrations(version,description)
values('v2.6.20am','Every transfer line posts atomically; paired historical costs are neutral and location roll prefixes remain valid');
commit;
