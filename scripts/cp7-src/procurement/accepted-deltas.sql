-- Declared CP7 deltas against exact accepted function definitions. Original CP6
-- release files stay immutable; restoration must put back these exact two defs.
do $$begin
 if encode(extensions.digest(pg_get_functiondef('erp.require_internal()'::regprocedure),'sha256'),'hex')<>'5dffcd53c0a5de609ae41482ca246d2afc806b9d92241253d680cf5c7fe1612e'
  or encode(extensions.digest(pg_get_functiondef('erp.bc_guard_zone_location_v1()'::regprocedure),'sha256'),'hex')<>'95ff4304ba90c3214a4fb718278d06f716bf3213170fa0f1cb3ab8a5375e4c26' then
  raise exception 'CP7_PROCUREMENT_PREDECESSOR_CHANGED';end if;
end $$;

create or replace function erp.require_internal() returns void
language plpgsql security definer set search_path='' as $function$
declare v_app_role text;v_jwt_role text;
begin
 if session_user in('postgres','supabase_admin') then return;end if;
 begin v_jwt_role:=coalesce(auth.jwt()->>'role','');exception when others then v_jwt_role:='';end;
 if v_jwt_role='service_role' then return;end if;
 if exists(select 1 from erp.cutting_bridge_execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and c.actor_key=erp._idempotency_actor_key() and c.action='POST_CUTTING'
  and c.permission_key='production.cutting.post' and erp.has_permission(c.permission_key)) then return;end if;
 if exists(select 1 from erp.bs_resolution_execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and c.actor_key=erp._idempotency_actor_key()
  and c.permission_key in('production.bs_rework.create','production.bs_rework.post','production.bs_rework.reverse')
  and erp.has_permission(c.permission_key)) then return;end if;
 if exists(select 1 from erp.cp6_laundry_qc_execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and c.actor_key=erp._idempotency_actor_key()
  and ((c.action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH') and c.permission_key='production.laundry.post')
    or(c.action='POST_FINAL_SKU' and c.permission_key='production.final_sku.post')
    or(c.action in('REVERSE_DELIVERY','REVERSE_RECEIPT') and c.permission_key='production.laundry.reverse')
    or(c.action='REVERSE_FINAL_SKU' and c.permission_key='production.final_sku.reverse'))
  and erp.has_permission(c.permission_key)) then return;end if;
 -- Only a private, transaction/actor-bound public-command context extends the
 -- legacy internal-role guard. Caller-controlled GUCs cannot grant this path.
 if exists(select 1 from cp7_procurement.execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
  and ((c.action='SAVE_DRAFT' and c.permission_key='warehouse.procurement.create')
    or(c.action='POST' and c.permission_key='warehouse.procurement.post'))
  and erp.has_permission('warehouse.procurement.view') and erp.has_permission(c.permission_key)) then return;end if;
 if exists(select 1 from cp7_material.execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
  and c.action in('SAVE_TRANSFER','POST_TRANSFER','REVERSE_TRANSFER','SAVE_COUNT','POST_COUNT','DELETE_COUNT','REVERSE_COUNT') and c.permission_key='warehouse.stock.adjust'
  and erp.has_permission('warehouse.material.view') and erp.has_permission(c.permission_key)) then return;end if;
 if exists(select 1 from cp7_supplier_return.execution_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
  and ((c.action='SAVE' and c.permission_key='warehouse.procurement.create')
    or(c.action in('POST','REVERSE') and c.permission_key='warehouse.procurement.reverse'))
  and erp.has_permission('warehouse.procurement.view') and erp.has_permission(c.permission_key)) then return;end if;
 v_app_role:=erp.current_app_role();
 if coalesce(v_app_role,'') not in('OWNER','ADMIN','STAFF') then raise exception 'Internal ERP access required';end if;
end $function$;

create or replace function erp.bc_guard_zone_location_v1() returns trigger
language plpgsql security definer set search_path='' as $function$
begin
 if tg_table_name='bc_accessory_zones_v1' then
  if tg_op='DELETE' or new.location_id<>old.location_id or new.zone_kind<>old.zone_kind then
   raise exception 'BC_ZONE_IMMUTABLE: jenis zona tetap; buat zona baru bila perlu';end if;
  return new;
 end if;
 -- This branch is a locations trigger: its identity is OLD.id. OLD.location_id
 -- exists only on the separate zone relation handled above.
 if exists(select 1 from erp.bc_accessory_zones_v1 where location_id=old.id) and
  (new.location_type is distinct from old.location_type or
   (old.is_active and not new.is_active and exists(select 1 from erp.material_stock_movements m
    where m.location_id=old.id group by m.material_id having sum(m.qty_signed)<>0))) then
  raise exception 'BC_ZONE_IMMUTABLE: zona tetap gudang bahan dan tidak dinonaktifkan selama masih ada stok';end if;
 return new;
end $function$;
