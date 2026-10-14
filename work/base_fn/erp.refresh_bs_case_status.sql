-- bootstrap lines 16394-16434
CREATE OR REPLACE FUNCTION erp.refresh_bs_case_status(p_bs_case_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_case erp.bs_cases%rowtype;
  v_resolved integer;
  v_active boolean;
  v_status text;
begin
  select * into v_case from erp.bs_cases where id=p_bs_case_id for update;
  if v_case.id is null or v_case.status='CANCELLED' then return; end if;
  select coalesce(sum(qty_pcs),0)::integer into v_resolved
  from erp.bs_resolutions where bs_case_id=v_case.id;
  select exists(
    select 1 from erp.rework_orders
    where bs_case_id=v_case.id and status in('OPEN','IN_PROGRESS','PARTIAL')
  ) into v_active;

  if v_resolved>=v_case.qty_pcs then
    if exists(select 1 from erp.bs_resolutions where bs_case_id=v_case.id)
       and not exists(select 1 from erp.bs_resolutions where bs_case_id=v_case.id and resolution_type<>'SCRAP') then
      v_status:='SCRAPPED';
    elsif exists(select 1 from erp.bs_resolutions where bs_case_id=v_case.id)
       and not exists(select 1 from erp.bs_resolutions where bs_case_id=v_case.id and resolution_type<>'WRITE_OFF') then
      v_status:='WRITTEN_OFF';
    else v_status:='RESOLVED'; end if;
  elsif v_active then v_status:='IN_REWORK';
  elsif v_resolved>0 then v_status:='PARTIAL';
  else v_status:='OPEN'; end if;

  if v_case.status is distinct from v_status then
    update erp.bs_cases set status=v_status,updated_at=now() where id=v_case.id;
  end if;
end;
$function$;

alter function "erp"."refresh_bs_case_status"(p_bs_case_id uuid) owner to "postgres";
