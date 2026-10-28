-- Complete stock row framing shared with the existing single-root digest.
create schema cp7_model_target_source_v2 authorization cp7_capture;
revoke all on schema cp7_model_target_source_v2 from public,anon,authenticated,service_role;

create function cp7_model_target_source_v2.stock_digests(p_products jsonb,p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare answer jsonb;
begin
 if p_at is null or not isfinite(p_at)or jsonb_typeof(p_products)is distinct from'array'
  or jsonb_array_length(p_products)>5000 then raise exception 'CP7_MODEL_TARGET_STOCK_SCOPE';end if;
 if exists(select 1 from jsonb_array_elements(p_products)p where p->>'root_id'is null or p->>'size_id'is null)
  or jsonb_array_length(p_products)<>(select count(distinct(p->>'root_id')::uuid)from jsonb_array_elements(p_products)p)then
  raise exception 'CP7_MODEL_TARGET_STOCK_ROOTS';end if;
 with products as materialized(select(p->>'root_id')::uuid root_id,(p->>'size_id')::uuid size_id from jsonb_array_elements(p_products)p),
 stock as materialized(
  select m.id,coalesce(p.identity_root_id,p.id)root_id,p.size_id,m.product_id,m.lot_id,m.location_id,
   m.quality_grade,m.qty_signed::text qty_signed,m.physical_at,m.system_created_at,
   m.movement_type,m.source_type,m.source_id,m.reversal_of_id,m.book_order
  from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
  where coalesce(p.identity_root_id,p.id)in(select root_id from products)
   and m.physical_at<=p_at and m.system_created_at<=p_at
 ),framed as materialized(
  select m.root_id,count(*)n,string_agg(encode(pg_catalog.sha256(convert_to(to_jsonb(m)::text,'UTF8')),'hex'),E'\n'order by m.id)frames
  from stock m group by m.root_id
 )
 select coalesce(jsonb_agg(jsonb_build_object('target_key',p.root_id::text||':'||p.size_id::text,
  'stock_reference',jsonb_build_object('contract_version','cp7.native-stock-row-digest.v1',
   'scope','ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS','captured_at',cp7_planning.utc(p_at),
   'row_count',coalesce(f.n,0)::text,'rows_sha256',encode(pg_catalog.sha256(convert_to(
    E'cp7.native-stock-row-digest.v1\n'||coalesce(f.n,0)::text||E'\n'||coalesce(f.frames,''),'UTF8')),'hex'),
   'raw_rows_truncated',false,'raw_rows_materialized_as_JSON_array',false,
   'raw_native_capture_status_overridden',false,'apply_enabled',false,'production_go',false))
   order by p.root_id,p.size_id),'[]')into answer
 from products p left join framed f on f.root_id=p.root_id;
 return answer;
end $$;
alter function cp7_model_target_source_v2.stock_digests(jsonb,timestamp with time zone)owner to cp7_capture;
revoke all on function cp7_model_target_source_v2.stock_digests(jsonb,timestamp with time zone)from public,anon,authenticated,service_role;
