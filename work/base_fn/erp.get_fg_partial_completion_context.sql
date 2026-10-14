-- bootstrap lines 8406-8507
CREATE OR REPLACE FUNCTION erp.get_fg_partial_completion_context(p_cutting_group_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'pg_temp'
AS $function$
declare
  v_group erp.cutting_groups%rowtype;
  v_progress jsonb;
  v_sizes jsonb;
  v_unassigned_adjustment bigint;
begin
  perform erp.require_internal();

  select * into v_group
  from erp.cutting_groups
  where id = p_cutting_group_id;
  if v_group.id is null then
    raise exception 'Potongan not found';
  end if;

  select to_jsonb(p) into v_progress
  from erp.v_fg_partial_completion_progress p
  where p.cutting_group_id = v_group.id;

  with original as (
    select s.size_id, sum(y.qty_pcs)::bigint as qty_pcs
    from erp.cutting_group_size_slots s
    left join erp.cutting_roll_yields y on y.size_slot_id = s.id
    where s.cutting_group_id = v_group.id
    group by s.size_id
  ), adjustment as (
    select s.size_id, sum(l.qty_delta_pcs)::bigint as qty_pcs
    from erp.cutting_qty_correction_lines l
    join erp.cutting_group_size_slots s on s.id = l.size_slot_id
    where l.cutting_group_id = v_group.id
    group by s.size_id
  ), posted as (
    select pr.size_id,
      sum(i.qty_good_pcs)::bigint as good_qty_pcs,
      sum(i.qty_bs_pcs)::bigint as bs_qty_pcs
    from erp.qc_inspection_items i
    join erp.qc_inspections q on q.id = i.inspection_id and q.status = 'POSTED'
    join erp.products pr on pr.id = i.final_product_id
    where i.cutting_group_id = v_group.id
    group by pr.size_id
  ), size_ids as (
    select size_id from original
    union select size_id from adjustment
    union select size_id from posted
  )
  select coalesce(jsonb_agg(jsonb_build_object(
    'size_id', z.size_id,
    'size_code', sz.size_code,
    'target_qty_pcs', coalesce(o.qty_pcs, 0) + coalesce(a.qty_pcs, 0),
    'good_qty_pcs', coalesce(p.good_qty_pcs, 0),
    'bs_qty_pcs', coalesce(p.bs_qty_pcs, 0),
    'remaining_qty_pcs', greatest(
      coalesce(o.qty_pcs, 0) + coalesce(a.qty_pcs, 0)
        - coalesce(p.good_qty_pcs, 0) - coalesce(p.bs_qty_pcs, 0),
      0
    ),
    'suggested_product_id', (
      select pr.id
      from erp.products pr
      join erp.production_orders po on po.model_id = pr.model_id
      where po.id = v_group.po_id
        and pr.size_id = z.size_id
        and pr.is_active = true
        and pr.effective_from <= clock_timestamp()
        and (pr.effective_to is null or pr.effective_to > clock_timestamp())
      order by pr.effective_from desc, pr.created_at desc, pr.id desc
      limit 1
    )
  ) order by sz.sort_order, sz.size_code), '[]'::jsonb)
  into v_sizes
  from size_ids z
  join erp.sizes sz on sz.id = z.size_id
  left join original o on o.size_id = z.size_id
  left join adjustment a on a.size_id = z.size_id
  left join posted p on p.size_id = z.size_id;

  select coalesce(sum(l.qty_delta_pcs), 0)::bigint
  into v_unassigned_adjustment
  from erp.cutting_qty_correction_lines l
  where l.cutting_group_id = v_group.id
    and l.size_slot_id is null;

  return jsonb_build_object(
    'cutting_group_id', v_group.id,
    'po_id', v_group.po_id,
    'group_number', v_group.group_number,
    'row_version', v_group.row_version,
    'progress', coalesce(v_progress, '{}'::jsonb),
    'sizes', coalesce(v_sizes, '[]'::jsonb),
    'unassigned_adjustment_qty_pcs', v_unassigned_adjustment
  );
end;
$function$;

alter function "erp"."get_fg_partial_completion_context"(p_cutting_group_id uuid) owner to "postgres";
