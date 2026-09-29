-- Reject lossy numeric/coercion and incomplete full-document replacements before
-- calling the native draft writer. Native stock/accounting policy is unchanged.
create function cp7_sales.validate_draft(p_payload jsonb,p_edit boolean) returns void
language plpgsql immutable security invoker set search_path='' as $$
declare keys text[];line jsonb;
begin
 keys:=array['sale_number','customer_id','source_location_id','sale_date','due_date','payment_terms','notes','change_reason','items']||case when p_edit then array['sale_id','review_token'] else '{}'::text[] end;
 if jsonb_typeof(p_payload) is distinct from 'object' or not p_payload ?& keys or exists(select 1 from jsonb_each(p_payload) e where e.key<>all(keys) or(e.key<>'items' and jsonb_typeof(e.value) not in('string','null')))
  or coalesce(length(btrim(p_payload->>'sale_number')),0) not between 1 and 60
  or coalesce(length(btrim(p_payload->>'change_reason')),0) not between 5 and 1000
  or coalesce(p_payload->>'customer_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p_payload->>'source_location_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p_payload->>'sale_date','')!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$'
  or(p_payload->>'due_date' is not null and(p_payload->>'due_date')!~'^\d{4}-\d{2}-\d{2}$')
  or length(p_payload->>'payment_terms')>100 or length(p_payload->>'notes')>4000
  or (p_edit and(coalesce(p_payload->>'sale_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' or coalesce(p_payload->>'review_token','')!~'^[a-f0-9]{32}$'))
  or jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 100 then raise exception 'CP7_SALES_DRAFT_FIELDS';end if;
 for line in select value from jsonb_array_elements(p_payload->'items') loop
  if jsonb_typeof(line) is distinct from 'object' or not line ?& array['product_id','qty_pcs','unit_price_snapshot','discount_amount','notes']
   or exists(select 1 from jsonb_each(line) e where e.key not in('product_id','qty_pcs','unit_price_snapshot','discount_amount','notes') or jsonb_typeof(e.value) not in('string','null'))
   or coalesce(line->>'product_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or coalesce(line->>'qty_pcs','')!~'^[1-9][0-9]{0,8}$'
   or coalesce(line->>'unit_price_snapshot','')!~'^(0|[1-9][0-9]{0,15})(\.[0-9]{1,2})?$'
   or coalesce(line->>'discount_amount','')!~'^(0|[1-9][0-9]{0,15})(\.[0-9]{1,2})?$'
   or length(line->>'notes')>4000 then raise exception 'CP7_SALES_DRAFT_LINE';end if;
  if (line->>'discount_amount')::numeric>(line->>'qty_pcs')::integer*(line->>'unit_price_snapshot')::numeric then raise exception 'CP7_SALES_DISCOUNT';end if;
 end loop;
end $$;
alter function cp7_sales.validate_draft(jsonb,boolean) owner to cp7_sales_read;
revoke all on function cp7_sales.validate_draft(jsonb,boolean) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_sales.validate_draft(jsonb,boolean) to postgres;
