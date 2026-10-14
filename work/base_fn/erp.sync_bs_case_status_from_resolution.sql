-- bootstrap lines 24496-24515
CREATE OR REPLACE FUNCTION erp.sync_bs_case_status_from_resolution()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if tg_op='DELETE' then
    perform erp.refresh_bs_case_status(old.bs_case_id);return old;
  end if;
  perform erp.refresh_bs_case_status(new.bs_case_id);
  if tg_op='UPDATE' and old.bs_case_id is distinct from new.bs_case_id then
    perform erp.refresh_bs_case_status(old.bs_case_id);
  end if;
  return new;
end;
$function$;

alter function "erp"."sync_bs_case_status_from_resolution"() owner to "postgres";
