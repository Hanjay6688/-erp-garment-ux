-- bootstrap lines 17643-17783
CREATE OR REPLACE FUNCTION erp.reverse_cutting_material_flow_before_sewing_v2(p_cutting_group_id uuid, p_reason text, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_group erp.cutting_groups%rowtype;
  r record;
  v_reversed_movements integer := 0;
  v_reversed_journals integer := 0;
begin
  perform erp.require_owner_admin();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if nullif(btrim(p_reason), '') is null then raise exception 'Reversal reason is required'; end if;
  v_hash := erp._request_hash(jsonb_build_object(
    'cutting_group_id', p_cutting_group_id,
    'reason', btrim(p_reason),
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(
    'reverse_cutting_material_flow_before_sewing_v2', p_client_request_id, v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason', btrim(p_reason), true);

  select * into v_group
  from erp.cutting_groups where id = p_cutting_group_id for update;
  if v_group.id is null then raise exception 'Potongan not found'; end if;
  if v_group.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_group.row_version;
  end if;
  if v_group.status not in ('CUT','PICKED_UP') then
    raise exception 'Only CUT/PICKED_UP Potongan can use pre-sewing material reversal';
  end if;
  if erp.cutting_group_has_downstream_after_pickup(v_group.id) then
    raise exception 'Potongan already has sewing/downstream evidence; reverse downstream documents instead';
  end if;
  if not v_group.material_issue_posted
     and not v_group.material_return_posted
     and not exists (
       select 1 from erp.material_stock_movements m
       where m.source_id = v_group.id
         and m.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN')
         and not exists (
           select 1 from erp.material_stock_movements rv where rv.reversal_of_id = m.id
         )
     )
  then raise exception 'Potongan has no active cutting material flow to reverse'; end if;

  -- Reverse posted return journals first, then the original issue journal.
  -- Any later failure rolls this whole function back atomically.
  for r in
    select je.id
    from erp.journal_entries je
    join erp.cutting_group_rolls cgr on cgr.id = je.source_id
    where cgr.cutting_group_id = v_group.id
      and je.source_type = 'CUTTING_MATERIAL_RETURN_LINE'
      and je.status = 'POSTED'
    order by je.posting_at desc, je.id desc
  loop
    perform erp.reverse_journal(r.id, btrim(p_reason));
    v_reversed_journals := v_reversed_journals + 1;
  end loop;

  for r in
    select je.id
    from erp.journal_entries je
    where je.source_type = 'CUTTING_MATERIAL_ISSUE'
      and je.source_id = v_group.id
      and je.status = 'POSTED'
    order by je.posting_at desc, je.id desc
  loop
    perform erp.reverse_journal(r.id, btrim(p_reason));
    v_reversed_journals := v_reversed_journals + 1;
  end loop;

  -- Positive cutting returns are removed from warehouse first. The normal
  -- negative-stock guard blocks reversal if that returned quantity was consumed.
  -- The original issue is then restored to its source warehouse.
  for r in
    select m.*
    from erp.material_stock_movements m
    where m.source_id = v_group.id
      and m.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN')
      and not exists (
        select 1 from erp.material_stock_movements rv where rv.reversal_of_id = m.id
      )
    order by case m.source_type when 'CUTTING_GROUP_RETURN' then 0 else 1 end,
             m.system_created_at, m.id
  loop
    insert into erp.material_stock_movements(
      material_id, roll_id, location_id, movement_type, qty_signed,
      input_unit_cost, source_type, source_id, physical_at, created_by,
      reversal_of_id, note
    ) values (
      r.material_id, r.roll_id, r.location_id, 'REVERSAL', -r.qty_signed,
      r.unit_cost_snapshot, 'CUTTING_PRESEWING_REVERSAL', v_group.id,
      greatest(clock_timestamp(), r.physical_at), erp.current_app_user_id(),
      r.id, btrim(p_reason)
    );
    v_reversed_movements := v_reversed_movements + 1;
  end loop;

  for r in
    select distinct m.material_id
    from erp.material_stock_movements m
    where m.source_id = v_group.id
      and m.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN')
  loop
    perform erp.recalculate_material_cost(r.material_id);
  end loop;

  update erp.cutting_groups
  set material_issue_posted = false,
      material_return_posted = false,
      status = case when picked_up_at is null then 'CUT' else 'PICKED_UP' end,
      updated_at = now()
  where id = v_group.id
  returning * into v_group;

  v_response := jsonb_build_object(
    'cutting_group_id', v_group.id,
    'status', v_group.status,
    'row_version', v_group.row_version,
    'reversed_movement_count', v_reversed_movements,
    'reversed_journal_count', v_reversed_journals,
    'presewing_reversible', erp.is_cutting_group_presewing_reversible(v_group.id)
  );
  return erp._idempotency_complete(
    'reverse_cutting_material_flow_before_sewing_v2',
    p_client_request_id, v_response
  );
end;
$function$;

alter function "erp"."reverse_cutting_material_flow_before_sewing_v2"(p_cutting_group_id uuid, p_reason text, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
