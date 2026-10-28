-- Bind complete target digests without repeating global array scans per target.
create function cp7_model_target_source_v2.physical_rows(c jsonb,p_limit integer,p_stock_rows jsonb,p_producer text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare non_stock jsonb;facts_by_target jsonb;raw_by_root jsonb;entry jsonb;stock_value jsonb;target_value text;facts_value jsonb;
 raw_value jsonb;source_hash text;answer jsonb[]:='{}';
begin
 non_stock:=cp7_model_target_source_v2.non_stock_rows(c,p_limit);
 if p_producer is null or p_producer!~'^[0-9a-f]{64}$'
  or jsonb_typeof(p_stock_rows)is distinct from'array'or jsonb_array_length(p_stock_rows)>5000 then
  raise exception 'CP7_MODEL_TARGET_BINDING_STOCK_REFERENCE';end if;
 select coalesce(jsonb_object_agg(x->>'target_key',x->'non_stock'),'{}')into facts_by_target from jsonb_array_elements(non_stock)x;
 if jsonb_array_length(p_stock_rows)<>(select count(distinct x->>'target_key')from jsonb_array_elements(p_stock_rows)x)
  or exists(select 1 from jsonb_array_elements(p_stock_rows)x where not facts_by_target?(x->>'target_key'))then
  raise exception 'CP7_MODEL_TARGET_BINDING_TARGET_UNAVAILABLE';end if;
 if c->>'status'='COMPLETE'then
  with framed as(select x->>'root_id'root_id,count(*)n,
   string_agg(encode(pg_catalog.sha256(convert_to(x::text,'UTF8')),'hex'),E'\n'order by(x->>'id')collate"C")frames
   from jsonb_array_elements(c->'facts'->'stock')x group by 1)
  select coalesce(jsonb_object_agg(root_id,jsonb_build_object('row_count',n::text,'rows_sha256',
   encode(pg_catalog.sha256(convert_to(E'cp7.native-stock-row-digest.v1\n'||n::text||E'\n'||frames,'UTF8')),'hex'))),'{}')into raw_by_root from framed;
 end if;
 for entry in select value from jsonb_array_elements(p_stock_rows)order by value->>'target_key'collate"C"loop
  target_value:=entry->>'target_key';stock_value:=entry->'stock_reference';facts_value:=facts_by_target->target_value;
  if stock_value->>'contract_version'is distinct from'cp7.native-stock-row-digest.v1'
   or stock_value->>'scope'is distinct from'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS'
   or stock_value->'captured_at'is distinct from c->'captured_at'
   or stock_value->>'row_count'is null or stock_value->>'row_count'!~'^(0|[1-9][0-9]{0,18})$'
   or stock_value->>'rows_sha256'is null or stock_value->>'rows_sha256'!~'^[0-9a-f]{64}$'
   or stock_value->'raw_rows_truncated'is distinct from'false'::jsonb
   or stock_value->'raw_native_capture_status_overridden'is distinct from'false'::jsonb then
   raise exception 'CP7_MODEL_TARGET_BINDING_STOCK_REFERENCE';end if;
  if c->>'status'='COMPLETE'then
   raw_value:=coalesce(raw_by_root->split_part(target_value,':',1),jsonb_build_object('row_count','0','rows_sha256',
    encode(pg_catalog.sha256(convert_to(E'cp7.native-stock-row-digest.v1\n0\n','UTF8')),'hex')));
   if stock_value->'row_count'is distinct from raw_value->'row_count'or stock_value->'rows_sha256'is distinct from raw_value->'rows_sha256'then
    raise exception 'CP7_MODEL_TARGET_BINDING_STOCK_MISMATCH';end if;
  end if;
  source_hash:=encode(pg_catalog.sha256(convert_to(jsonb_build_object('contract','cp7.scoped-history-source.v1',
   'target_key',target_value,'non_stock',facts_value,'full_stock',stock_value->'rows_sha256',
   'stock_rows',stock_value->'row_count','producer',p_producer)::text,'UTF8')),'hex');
  answer:=array_append(answer,jsonb_build_object('target_key',target_value,'reference',jsonb_build_object(
   'contract_version','cp7.model-target-physical-binding.v1','target_key',target_value,'captured_at',c->'captured_at',
   'scoped_source_hash',source_hash,'producer_hash',p_producer,'global_raw_capture_status',c->'status',
   'global_non_stock_complete',true,'stock_reference',stock_value,'raw_native_capture_status_overridden',false,
   'target_caller_integrated',false,'production_go',false)));
 end loop;
 return to_jsonb(answer);
end $$;
alter function cp7_model_target_source_v2.physical_rows(jsonb,integer,jsonb,text)owner to cp7_capture;
revoke all on function cp7_model_target_source_v2.physical_rows(jsonb,integer,jsonb,text)from public,anon,authenticated,service_role;
