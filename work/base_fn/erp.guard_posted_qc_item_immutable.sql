-- bootstrap lines 10382-10410
CREATE OR REPLACE FUNCTION erp.guard_posted_qc_item_immutable()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_status text;
begin
  if tg_op in ('UPDATE','DELETE') then
    select q.status into v_status
    from erp.qc_inspections q where q.id=old.inspection_id;
    if v_status is not null and v_status<>'DRAFT' then
      raise exception using errcode='42501',message='POSTED_FINAL_SKU_IDENTITY_IMMUTABLE';
    end if;
  end if;
  if tg_op in ('INSERT','UPDATE') then
    select q.status into v_status
    from erp.qc_inspections q where q.id=new.inspection_id;
    if v_status is not null and v_status<>'DRAFT' then
      raise exception using errcode='42501',message='POSTED_FINAL_SKU_IDENTITY_IMMUTABLE';
    end if;
  end if;
  if tg_op='DELETE' then return old; end if;
  return new;
end;
$function$;

alter function "erp"."guard_posted_qc_item_immutable"() owner to "postgres";
