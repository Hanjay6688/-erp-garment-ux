CREATE FUNCTION cp7_sku_conversion.pool_values_v6(p_product uuid, p_location uuid, p_grade text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare
  booked jsonb;
  physical_qty numeric;
  economic_base numeric;
  economic_cost numeric;
  economic_total numeric;
  invalid_base_source boolean;
  invalid_cost_source boolean;
begin
  -- The booked quote checks source completeness, custody, and attribution.
  booked := cp7_sku_conversion.pool_quote_v2(p_product, p_location, p_grade);

  select round(coalesce(sum(c.component_units), 0), 6),
         round(coalesce(sum(c.component_units * h.total_cost / nullif(h.qty_basis_pcs::numeric(30,12), 0)), 0), 6),
         coalesce(bool_or(h.total_cost::text in ('NaN', 'Infinity', '-Infinity') or h.qty_basis_pcs <= 0), false)
    into physical_qty, economic_base, invalid_base_source
    from cp7_sku_conversion.pool_components_v2(p_product, p_location, p_grade) c
    join erp.hpp_versions h on h.id = c.hpp_version_id;
  if physical_qty is distinct from (booked->>'qty')::numeric then
    raise exception 'CP7_SKU_ECONOMIC_POOL_QUANTITY_MISMATCH';
  end if;

  with costs as materialized (
    select c.component_units, (c.source_revision->'allocation'->>'extra')::numeric source_amount,
           (c.source_revision->'allocation'->>'qty_pcs')::numeric source_qty
    from cp7_sku_conversion.pool_cost_components_v3(p_product, p_location, p_grade) c
  )
  select round(coalesce(sum(component_units * source_amount / nullif(source_qty::numeric(30,12), 0)), 0), 6),
         coalesce(bool_or(source_amount is null or source_amount::text in ('NaN', 'Infinity', '-Infinity')
                         or source_qty is null or source_qty <= 0
                         or source_qty::text in ('NaN', 'Infinity', '-Infinity')), false)
    into economic_cost, invalid_cost_source
    from costs;
  if invalid_cost_source then
    raise exception 'CP7_SKU_ECONOMIC_POOL_EXACT_COST_SOURCE_REQUIRED';
  end if;
  economic_total := economic_base + economic_cost;
  if invalid_base_source or economic_total < 0 then
    -- A valid booked recovery can exhaust the selected lot's money while its
    -- weighted economic share is smaller. Preserve the booked amount and
    -- expose the unpriced economic read until its source is reconciled.
    return jsonb_build_object('booked', booked, 'economic', booked || jsonb_build_object(
      'state', 'UNKNOWN', 'value', null, 'base_value', null, 'adjustment', null, 'average', null));
  end if;

  -- The same snapshot revision binds the root HPP IDs, extra costs, and booked cents.
  return jsonb_build_object('booked', booked, 'economic', booked || jsonb_build_object(
    'value', economic_total::text, 'base_value', economic_base::text,
    'adjustment', economic_cost::text,
    'average', case when physical_qty > 0 then (economic_total / physical_qty)::text end));
end
$function$;
REVOKE ALL ON FUNCTION cp7_sku_conversion.pool_values_v6(uuid, uuid, text)
 FROM public, anon, authenticated, service_role;
