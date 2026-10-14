-- bootstrap lines 9173-9215
CREATE OR REPLACE FUNCTION erp.guard_cutting_detail_after_post()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_group_id uuid;
  v_locked boolean;
  v_return_posted boolean:=false;
  v_row jsonb;
begin
  if current_user in ('postgres','service_role','supabase_admin') then
    if tg_op='DELETE' then return old; else return new; end if;
  end if;

  v_row:=case when tg_op='DELETE' then to_jsonb(old) else to_jsonb(new) end;
  if tg_table_name in ('cutting_group_rolls','cutting_group_size_slots') then
    v_group_id:=nullif(v_row->>'cutting_group_id','')::uuid;
  elsif tg_table_name='cutting_roll_yields' then
    select cgr.cutting_group_id into v_group_id from erp.cutting_group_rolls cgr where cgr.id=nullif(v_row->>'cutting_group_roll_id','')::uuid;
  end if;

  select (material_issue_posted or picked_up_at is not null or status not in ('CUT')),material_return_posted
  into v_locked,v_return_posted
  from erp.cutting_groups where id=v_group_id;

  if coalesce(v_locked,false) then
    if tg_table_name='cutting_group_rolls' and tg_op='UPDATE' and not coalesce(v_return_posted,false)
       and new.cutting_group_id=old.cutting_group_id
       and new.roll_id=old.roll_id
       and new.qty_issued=old.qty_issued
       and new.unit_cost_snapshot is not distinct from old.unit_cost_snapshot then
      return new;
    end if;
    raise exception 'Cutting core detail is frozen after material issue/pickup; only consumption/remaining/physical-return result fields may be updated until return posting';
  end if;

  if tg_op='DELETE' then return old; else return new; end if;
end;
$function$;

alter function "erp"."guard_cutting_detail_after_post"() owner to "postgres";
