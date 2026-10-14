-- bootstrap lines 8940-8981
CREATE OR REPLACE FUNCTION erp.guard_bs_case_component_state()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare v_used boolean:=false;
begin
  if current_user in ('postgres','service_role','supabase_admin') then
    if tg_op='DELETE' then return old; else return new; end if;
  end if;

  if tg_op='INSERT' then
    new.lifetime_newly_completed_qty:=0;
    new.lifetime_paid_qty:=0;
    return new;
  end if;

  select exists(select 1 from erp.rework_component_lines rcl where rcl.bs_case_component_id=old.id) into v_used;

  if tg_op='DELETE' then
    if v_used then raise exception 'BS component already has rework history and cannot be deleted'; end if;
    return old;
  end if;

  if new.lifetime_newly_completed_qty is distinct from old.lifetime_newly_completed_qty
     or new.lifetime_paid_qty is distinct from old.lifetime_paid_qty then
    raise exception 'BS lifetime completion/payment counters are system-managed';
  end if;

  if v_used and (
       new.bs_case_id is distinct from old.bs_case_id
       or new.po_component_snapshot_id is distinct from old.po_component_snapshot_id
       or new.work_component_id is distinct from old.work_component_id
       or new.completed_before_bs_qty is distinct from old.completed_before_bs_qty
     ) then
    raise exception 'BS component identity/completed-before-BS quantity is frozen after rework starts';
  end if;
  return new;
end;$function$;

alter function "erp"."guard_bs_case_component_state"() owner to "postgres";
