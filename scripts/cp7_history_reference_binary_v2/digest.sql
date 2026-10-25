create schema cp7_history_reference_binary_v2 authorization cp7_capture;
revoke all on schema cp7_history_reference_binary_v2 from public,anon,authenticated,service_role;
create function cp7_history_reference_binary_v2.stock_digest(p_products jsonb,p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare answer jsonb;
begin
 if current_setting('server_version_num')::integer/10000<>17
  or current_setting('server_encoding')is distinct from'UTF8'then
  raise exception 'CP7_HISTORY_REFERENCE_V2_SERVER_CONTRACT';end if;
 if array['uuid'::regtype::oid,'bytea'::regtype::oid,'timestamptz'::regtype::oid,'int8'::regtype::oid]
  is distinct from array[2950,17,1184,20]::oid[]then
  raise exception 'CP7_HISTORY_REFERENCE_V2_BUILTIN_TYPES';end if;
 if p_at is null or not pg_catalog.isfinite(p_at) or jsonb_typeof(p_products)is distinct from'array'
  or jsonb_array_length(p_products)>5000 then raise exception 'CP7_HISTORY_REFERENCE_V2_SCOPE';end if;
 if exists(select 1 from jsonb_array_elements(p_products)p where p->>'root_id'is null)
  or jsonb_array_length(p_products)<>(select count(distinct(p->>'root_id')::uuid)from jsonb_array_elements(p_products)p)then
  raise exception 'CP7_HISTORY_REFERENCE_V2_ROOTS';end if;
 with clock as materialized(select p_at at),
 products as materialized(select(p->>'root_id')::uuid root_id from jsonb_array_elements(p_products)p),
 -- One consumer: retain the exact Native projection without a temporary copy.
 stock as not materialized(
 select m.id,coalesce(p.identity_root_id,p.id)root_id,p.size_id,m.product_id,m.lot_id,m.location_id,
  m.quality_grade,m.qty_signed::text qty_signed,m.physical_at,m.system_created_at,
  m.movement_type,m.source_type,m.source_id,m.reversal_of_id,m.book_order
 from erp.fg_stock_movements m join erp.products p on p.id=m.product_id cross join clock c
 where coalesce(p.identity_root_id,p.id)in(select root_id from products)
  and m.physical_at<=c.at and m.system_created_at<=c.at
 ),
 framed as(select count(*)n,coalesce(string_agg(encode(extensions.digest(pg_catalog.record_send(row(m.id::pg_catalog.uuid,m.root_id::pg_catalog.uuid,m.size_id::pg_catalog.uuid,m.product_id::pg_catalog.uuid,m.lot_id::pg_catalog.uuid,m.location_id::pg_catalog.uuid,pg_catalog.convert_to(m.quality_grade::text,'UTF8'),pg_catalog.convert_to(m.qty_signed::text,'UTF8'),m.physical_at::pg_catalog.timestamptz,m.system_created_at::pg_catalog.timestamptz,pg_catalog.convert_to(m.movement_type::text,'UTF8'),pg_catalog.convert_to(m.source_type::text,'UTF8'),m.source_id::pg_catalog.uuid,m.reversal_of_id::pg_catalog.uuid,m.book_order::pg_catalog.int8)),'sha256'),'hex'),
  E'\n'order by m.id),'')frames from stock m)
 select jsonb_build_object('contract_version','cp7.native-stock-row-digest.v2',
  'encoding','POSTGRES17_RECORD_SEND_TEXT_AS_UTF8_BYTEA_V1','layout_sha256','9fa5d22b53d337a6472898a5eec99ae7b221aea93313d693588e69cc6e83f32a',
  'scope','ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS','captured_at',cp7_planning.utc(p_at),
  'row_count',n::text,'rows_sha256',encode(extensions.digest(convert_to(
   E'cp7.native-stock-row-digest.v2\nPOSTGRES17_RECORD_SEND_TEXT_AS_UTF8_BYTEA_V1\n9fa5d22b53d337a6472898a5eec99ae7b221aea93313d693588e69cc6e83f32a\n'||n::text||E'\n'||frames,'UTF8'),'sha256'),'hex'),
  'raw_rows_truncated',false,'raw_rows_materialized_as_JSON_array',false,
  'raw_native_capture_status_overridden',false,'apply_enabled',false,'production_go',false)
 into answer from framed;
 return answer;
end $$;
alter function cp7_history_reference_binary_v2.stock_digest(jsonb,timestamptz)owner to cp7_capture;
revoke all on function cp7_history_reference_binary_v2.stock_digest(jsonb,timestamptz)from public,anon,authenticated,service_role;
