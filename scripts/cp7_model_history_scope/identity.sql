create function cp7_model_history_scope.identity(c jsonb)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=c->'facts';stock jsonb:=c->'stock_reference';p jsonb;target_value text:=c->>'target_key';n bigint;
begin
 if c->>'contract_version'is distinct from'cp7.model-history-facts.v1'
  or c->>'scope'is distinct from'SINGLE_CURRENT_PHYSICAL_ROOT'
  or target_value is null or target_value!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or c->>'producer_hash'is null or c->>'producer_hash'!~'^[0-9a-f]{64}$'then raise exception 'CP7_MODEL_HISTORY_SCOPE_SOURCE';end if;
 perform cp7_demand.instant(c->'captured_at');
 perform cp7_wip.fields(f,array['products','stock','sales','sale_journals','returns','return_journals']);
 if exists(select 1 from jsonb_each(f)where jsonb_typeof(value)<>'array')
  or jsonb_array_length(f->'products')is distinct from 1 then raise exception 'CP7_MODEL_HISTORY_SCOPE_TARGET';end if;
 p:=f->'products'->0;
 if(p->>'root_id')||':'||(p->>'size_id')is distinct from target_value or jsonb_array_length(p->'commercial')is distinct from 0 and jsonb_array_length(p->'commercial')is distinct from 1
  or exists(select 1 from jsonb_each(f)where key not in('products','stock')and jsonb_array_length(value)>50000)
  or exists(select 1 from jsonb_array_elements(f->'sales')x where x->>'root_id'is distinct from p->>'root_id' or jsonb_array_length(x->'sold_commercial')>1)
  or exists(select 1 from jsonb_array_elements(f->'sales')sale left join(
   select j->>'sale_id'sale_id,count(*)n from jsonb_array_elements(f->'sale_journals')j where j->'reversal_of_id'='null'::jsonb group by 1)originals
   on originals.sale_id=sale->>'sale_id'where sale->>'status'in('POSTED','PARTIAL_PAID','PAID','REVERSED')and coalesce(originals.n,0)<>1)then
  raise exception 'CP7_MODEL_HISTORY_SCOPE_NON_STOCK_INCOMPLETE';end if;
 if stock->>'contract_version'is distinct from'cp7.native-stock-row-digest.v1'
  or stock->>'scope'is distinct from'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS'
  or stock->'captured_at'is distinct from c->'captured_at'
  or stock->>'row_count'is null or stock->>'row_count'!~'^(0|[1-9][0-9]{0,18})$'
  or stock->>'rows_sha256'is null or stock->>'rows_sha256'!~'^[0-9a-f]{64}$'
  or stock->'raw_rows_truncated'is distinct from'false'::jsonb
  or stock->'raw_native_capture_status_overridden'is distinct from'false'::jsonb then
  raise exception 'CP7_MODEL_HISTORY_SCOPE_STOCK_REFERENCE';end if;
 n:=(stock->>'row_count')::bigint;
 if c->>'status'='COMPLETE'then
  if n>50000 or n<>jsonb_array_length(f->'stock')or c->'stock_raw_omitted'is distinct from'false'::jsonb then
   raise exception 'CP7_MODEL_HISTORY_SCOPE_STOCK_BOUND';end if;
 elsif c->>'status'='INCOMPLETE'then
  if n<50001 or c->'stock_raw_omitted'is distinct from'true'::jsonb
   or c->'stock_rows_at_least'is distinct from'50001'::jsonb or jsonb_array_length(f->'stock')<>0 then
   raise exception 'CP7_MODEL_HISTORY_SCOPE_STOCK_BOUND';end if;
 else raise exception 'CP7_MODEL_HISTORY_SCOPE_SOURCE';end if;
 return encode(extensions.digest(convert_to(jsonb_build_object('contract','cp7.scoped-history-source.v1',
  'target_key',target_value,'non_stock',f-'stock','full_stock',stock->'rows_sha256','stock_rows',stock->'row_count',
  'producer',c->'producer_hash')::text,'UTF8'),'sha256'),'hex');
end $$;
