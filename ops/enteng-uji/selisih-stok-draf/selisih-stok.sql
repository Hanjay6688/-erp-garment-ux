-- An edit first releases the old reservation, then reserves the new lines.
do $draft_receipt$
declare
  target regprocedure := 'erp.save_sale_draft_v2(jsonb,uuid,bigint)'::regprocedure;
  original text := pg_get_functiondef(target);
  old_field constant text := '''sellable_stock_delta_pcs'',-v_reserved,';
  new_field constant text := '''sellable_stock_delta_pcs'',v_released - v_reserved,';
begin
  if md5(original) <> '8a73a486d3470db970695d893c824a69'
     or (select proowner from pg_proc where oid = target) <> 'postgres'::regrole
     or position(old_field in original) = 0 then
    raise exception 'Unexpected native sale draft function in Enteng Uji';
  end if;
  execute replace(original, old_field, new_field);
end $draft_receipt$;
