-- P10 current FG source reads. No business writer or cached browser stock.
create role cp7_fg_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_fg authorization cp7_fg_read;
revoke all on schema cp7_fg from public,anon,authenticated,service_role;
grant usage on schema erp,auth to cp7_fg_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text),
 erp.bf_commercial_sku_at_v1(uuid,timestamptz),erp.bd_lot_laundry_unknown_v1(uuid),erp.get_hpp_completeness(uuid) to cp7_fg_read;
grant select on erp.fg_stock_movements,erp.fg_lots,erp.products,erp.sizes,erp.brands,erp.locations,erp.customers,erp.hpp_versions to cp7_fg_read;

-- Presentation lineage only. Economic/stock effects come from Native writers.
create table cp7_fg.correction_movements(
 member_id uuid primary key references erp.fg_stock_movements(id),
 origin_id uuid not null references erp.fg_stock_movements(id),
 correction_id uuid not null,recorded_at timestamptz not null,
 check(member_id<>origin_id)
);
alter table cp7_fg.correction_movements owner to cp7_fg_read;
alter table cp7_fg.correction_movements enable row level security;
create policy private_correction_movements on cp7_fg.correction_movements for all using(false)with check(false);
revoke all on cp7_fg.correction_movements from public,anon,authenticated,service_role,cp7_capture;
create function cp7_fg.immutable_correction_movement()returns trigger
language plpgsql stable security invoker set search_path=''as $$
begin raise exception 'CP7_FG_CORRECTION_LINEAGE_IMMUTABLE';end $$;
alter function cp7_fg.immutable_correction_movement()owner to cp7_fg_read;
create trigger immutable_correction_movement before update or delete on cp7_fg.correction_movements
 for each row execute function cp7_fg.immutable_correction_movement();
create function cp7_fg.validate_correction_movement()returns trigger
language plpgsql stable security invoker set search_path=''as $$
begin
 if exists(select 1 from cp7_fg.correction_movements where member_id=new.origin_id)
  or not exists(select 1 from erp.fg_stock_movements m join erp.fg_stock_movements o on o.id=new.origin_id
    where m.id=new.member_id and m.product_id=o.product_id and m.location_id=o.location_id
     and m.quality_grade=o.quality_grade and m.physical_at=o.physical_at)then
  raise exception 'CP7_FG_CORRECTION_ORIGIN_CHANGED';end if;
 return new;
end $$;
alter function cp7_fg.validate_correction_movement()owner to cp7_fg_read;
create trigger validate_correction_movement before insert on cp7_fg.correction_movements
 for each row execute function cp7_fg.validate_correction_movement();

create function cp7_fg.access_now(p_purpose text) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;permission_key text;
begin
 permission_key:=case p_purpose when 'SUMMARY' then 'warehouse.fg.view' when 'CARD' then 'warehouse.stock.view' when 'MOVEMENTS' then 'warehouse.movement.view' end;
 if permission_key is null then raise exception 'CP7_FG_PURPOSE';end if;
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_FG_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission(permission_key) then raise exception using errcode='42501',message='CP7_FG_ACCESS_DENIED';end if;
 return jsonb_build_object('actor',auth.uid(),'profile',a->'profile','permissions',a->'permissions',
  'can_value',erp.has_permission('finance.hpp.view'),'can_card',erp.has_permission('warehouse.stock.view'));
end $$;

create function cp7_fg.lot_value(p_lot uuid,p_qty numeric) returns jsonb
language sql stable security invoker set search_path='' as $$
 with source as (
  select l.id,h.id hpp_id,h.version_no,h.hpp_per_pcs,h.cost_state,h.calculated_at,
   h.id is null or h.hpp_per_pcs is null or h.cost_state='ESTIMATED' or erp.bd_lot_laundry_unknown_v1(l.id)
    or(l.po_id is not null and not exists(select 1 from erp.get_hpp_completeness(l.po_id) z where z.pending_reason_count=0)) pending
  from erp.fg_lots l left join lateral(select x.* from erp.hpp_versions x where x.lot_id=l.id and x.is_current order by x.version_no desc limit 1) h on true where l.id=p_lot
 )
 select coalesce((select jsonb_build_object('state',case when pending then 'UNKNOWN' else 'KNOWN' end,'hpp_version_id',hpp_id,'hpp_version',version_no::text,
  'cost_state',cost_state,'calculated_at',calculated_at,'unit_cost',case when not pending then hpp_per_pcs::text end,
  'value',case when not pending then round(p_qty*hpp_per_pcs,6)::text end,'basis','CURRENT_RESTATED_LOT_VALUE') from source),
  jsonb_build_object('state','UNKNOWN','hpp_version_id',null,'hpp_version',null,'cost_state',null,'calculated_at',null,'unit_cost',null,'value',null,'basis','CURRENT_RESTATED_LOT_VALUE'))
$$;
