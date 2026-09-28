-- A sourced recovery is a credit to conversion cost. Only that component may
-- have a signed unit amount; ordinary material/work prices stay nonnegative.
alter table erp.hpp_version_components drop constraint hpp_version_components_unit_cost_check;
alter table erp.hpp_version_components add constraint hpp_version_components_unit_cost_check
 check(unit_cost>=0 or(component_type='CONVERSION' and source_type='PRODUCT_CONVERSION_ALLOCATION' and source_id is not null));

CREATE OR REPLACE FUNCTION erp.be_guard_signed_hpp_component_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare a erp.product_conversion_allocations%rowtype;h erp.hpp_versions%rowtype;v_extra numeric;
begin
 if new.unit_cost>=0 then return new;end if;
 select * into a from erp.product_conversion_allocations where id=new.source_id;
 select * into h from erp.hpp_versions where id=new.hpp_version_id;
 v_extra:=erp.be_allocation_extra_v1(a.id);
 if new.component_type<>'CONVERSION' or new.source_type is distinct from 'PRODUCT_CONVERSION_ALLOCATION'
   or a.id is null or h.lot_id is distinct from a.destination_lot_id or h.total_cost<0
   or new.qty_basis is distinct from a.qty_pcs::numeric or v_extra is null or v_extra>=0
   or new.total_cost is distinct from v_extra or new.unit_cost is distinct from (v_extra/a.qty_pcs)::numeric(18,6)
   or not exists(select 1 from erp.be_conversion_cost_sources_v1 where conversion_id=a.conversion_id and kind='RECOVERY') then
   raise exception 'BE_SIGNED_HPP_REQUIRES_SOURCED_RECOVERY';
 end if;
 return new;
end;$function$;
create trigger be_signed_hpp_component before insert or update on erp.hpp_version_components
 for each row execute function erp.be_guard_signed_hpp_component_v1();

CREATE OR REPLACE FUNCTION erp.be_pocket_periods_v1(p_query text default '',p_offset integer default 0)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare q text:=lower(btrim(coalesce(p_query,'')));v_result jsonb;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');
 if length(q)>120 or p_offset is null or p_offset<0 then raise exception 'BE_INVALID_PERIOD_FILTER';end if;
 with matching as materialized (
  select p.* from erp.pocket_periods p where q='' or
   strpos(lower(concat_ws(' ',p.id::text,p.period_start::text,p.period_end::text,p.reason)),q)>0 or
   (q ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' and q between p.period_start::text and p.period_end::text)
 ), page as(select * from matching order by created_at desc,id limit 50 offset p_offset)
 select jsonb_build_object('periods',coalesce((select jsonb_agg(erp.pocket_period_state_v1(id) order by created_at desc,id) from page),'[]'::jsonb),
  'period_count',(select count(*) from matching),'period_offset',p_offset,
  'period_next_offset',case when (select count(*) from matching)>p_offset+50 then p_offset+50 else null end) into v_result;
 return v_result;
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_get_pocket_periods_v1(p_query text default '',p_offset integer default 0)
 RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.be_pocket_periods_v1(p_query,p_offset);$function$;

-- CP4's three-argument wrapper called a nonexistent native overload. Match the
-- native optimistic-version contract. Legacy calls fail with its explicit
-- expected_version-required message, before a mutation or idempotency entry.
drop function public.erp_reverse_sewing_terminal_v1(uuid,text,uuid);
CREATE OR REPLACE FUNCTION public.erp_reverse_sewing_terminal_v1(
 p_event_id uuid,p_reason text,p_client_request_id uuid,p_expected_version bigint default null)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
 perform erp.require_owner_admin();
 return erp.reverse_sewing_terminal_v1(p_event_id,p_reason,p_client_request_id,p_expected_version);
end;$function$;
