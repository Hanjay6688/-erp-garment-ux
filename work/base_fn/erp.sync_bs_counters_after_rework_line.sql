-- bootstrap lines 24536-24551
CREATE OR REPLACE FUNCTION erp.sync_bs_counters_after_rework_line()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_bs uuid;
begin
  select bcc.bs_case_id into v_bs from erp.bs_case_components bcc where bcc.id=case when tg_op='DELETE' then old.bs_case_component_id else new.bs_case_component_id end;
  perform erp.rebuild_bs_component_counters(v_bs);
  if tg_op='DELETE' then return old; else return new; end if;
end;
$function$;

alter function "erp"."sync_bs_counters_after_rework_line"() owner to "postgres";
