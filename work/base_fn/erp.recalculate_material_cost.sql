-- bootstrap lines 16124-16173
CREATE OR REPLACE FUNCTION erp.recalculate_material_cost(p_material_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_recalc_from timestamptz;
begin
  -- Operational callers normally arrive here immediately after inserting a new
  -- material movement/reversal. Use the earliest not-yet-recalculated economic
  -- point so a valid closed-period checkpoint can bound the replay. If nothing
  -- is marked dirty, preserve the historical explicit-rebuild behaviour.
  select min(x.recalc_from)
  into v_recalc_from
  from (
    select msm.physical_at as recalc_from
    from erp.material_stock_movements msm
    where msm.material_id=p_material_id
      and msm.is_cost_recalculated=false
      and msm.reversal_of_id is null

    union all

    select src.physical_at as recalc_from
    from erp.material_stock_movements rv
    join erp.material_stock_movements src on src.id=rv.reversal_of_id
    where rv.material_id=p_material_id
      and rv.is_cost_recalculated=false
      and rv.reversal_of_id is not null
  ) x;

  if v_recalc_from is null then
    perform erp._recalculate_material_cost_core(p_material_id,null,false);
  else
    perform erp._recalculate_material_cost_core(p_material_id,v_recalc_from,true);

    -- Reversal rows are audit events excluded from active cost-history replay;
    -- mark them handled only after the full material recalc succeeds.
    update erp.material_stock_movements
    set is_cost_recalculated=true
    where material_id=p_material_id
      and is_cost_recalculated=false
      and reversal_of_id is not null;
  end if;
end;
$function$;

alter function "erp"."recalculate_material_cost"(p_material_id uuid) owner to "postgres";
