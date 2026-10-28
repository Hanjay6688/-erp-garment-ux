-- Bridge captured global baseline facts to scoped history without claiming that
-- an omitted/truncated global stock array is complete or materializing it anew.
create schema cp7_model_target_binding authorization cp7_capture;
revoke all on schema cp7_model_target_binding from public,anon,authenticated,service_role;

create function cp7_model_target_binding.non_stock(c jsonb,p_target text,p_limit integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=c->'facts';root text;products jsonb;sales jsonb;journals jsonb;returns jsonb;return_journals jsonb;
begin
 if c->>'contract_version'is distinct from'cp7.native-demand-facts.v1'
  or c->>'scope'is distinct from'GLOBAL_CURRENT_PHYSICAL_ROOTS'
  or p_limit is null or p_limit not between 1 and 5000
  or p_target is null or p_target!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then
  raise exception 'CP7_MODEL_TARGET_BINDING_SCOPE';end if;
 perform cp7_demand.instant(c->'captured_at');
 perform cp7_wip.fields(f,array['products','stock','sales','sale_journals','returns','return_journals']);
 if exists(select 1 from jsonb_each(f)where jsonb_typeof(value)is distinct from'array')then
  raise exception 'CP7_MODEL_TARGET_BINDING_FACTS';end if;
 -- Mirror the pinned global capture completeness predicate. Only its known
 -- raw-stock overflow can use the separate complete SQL row digest below.
 if jsonb_array_length(f->'products')>p_limit
  or jsonb_array_length(f->'products')<>(select count(distinct x->>'root_id')from jsonb_array_elements(f->'products')x)
  or exists(select 1 from jsonb_each(f)where key not in('products','stock')and jsonb_array_length(value)>50000)
  or exists(select 1 from jsonb_array_elements(f->'products')x where jsonb_array_length(x->'commercial')>1)
  or exists(select 1 from jsonb_array_elements(f->'sales')x where jsonb_array_length(x->'sold_commercial')>1)
  or exists(select 1 from jsonb_array_elements(f->'sales')sale left join(
   select j->>'sale_id'sale_id,count(*)n from jsonb_array_elements(f->'sale_journals')j
    where j->'reversal_of_id'='null'::jsonb group by 1)originals on originals.sale_id=sale->>'sale_id'
   where sale->>'status'in('POSTED','PARTIAL_PAID','PAID','REVERSED')and coalesce(originals.n,0)<>1)then
  raise exception 'CP7_MODEL_TARGET_BINDING_NON_STOCK_INCOMPLETE';end if;
 if c->>'status'='COMPLETE'then
  if jsonb_array_length(f->'stock')>50000 or coalesce(c->'stock_raw_omitted','false'::jsonb)is distinct from'false'::jsonb then
   raise exception 'CP7_MODEL_TARGET_BINDING_RAW_STATUS';end if;
 elsif c->>'status'='INCOMPLETE'then
  if not(jsonb_array_length(f->'stock')=50001 or
   coalesce(c->'stock_raw_omitted'='true'::jsonb and c->'stock_rows_at_least'='50001'::jsonb and jsonb_array_length(f->'stock')=0,false))then
   raise exception 'CP7_MODEL_TARGET_BINDING_RAW_STATUS';end if;
 else raise exception 'CP7_MODEL_TARGET_BINDING_RAW_STATUS';end if;
 root:=split_part(p_target,':',1);
 select coalesce(jsonb_agg(x order by (x->>'id')collate"C"),'[]')into products from jsonb_array_elements(f->'products')x where x->>'root_id'=root;
 if jsonb_array_length(products)<>1 or(products->0->>'root_id')||':'||(products->0->>'size_id')is distinct from p_target then
  raise exception 'CP7_MODEL_TARGET_BINDING_TARGET_UNAVAILABLE';end if;
 select coalesce(jsonb_agg(x order by (x->>'id')collate"C"),'[]')into sales from jsonb_array_elements(f->'sales')x where x->>'root_id'=root;
 select coalesce(jsonb_agg(x order by (x->>'id')collate"C"),'[]')into journals from jsonb_array_elements(f->'sale_journals')x
  where x->>'sale_id'in(select s->>'sale_id'from jsonb_array_elements(sales)s)
   or x->>'reversal_of_id'in(select j->>'id'from jsonb_array_elements(f->'sale_journals')j
    where j->>'sale_id'in(select s->>'sale_id'from jsonb_array_elements(sales)s));
 select coalesce(jsonb_agg(x order by (x->>'id')collate"C"),'[]')into returns from jsonb_array_elements(f->'returns')x
  where x->>'sale_item_id'in(select s->>'id'from jsonb_array_elements(sales)s);
 select coalesce(jsonb_agg(x order by (x->>'id')collate"C"),'[]')into return_journals from jsonb_array_elements(f->'return_journals')x
  where x->>'return_id'in(select r->>'return_id'from jsonb_array_elements(returns)r)
   or x->>'reversal_of_id'in(select j->>'id'from jsonb_array_elements(f->'return_journals')j
    where j->>'return_id'in(select r->>'return_id'from jsonb_array_elements(returns)r));
 return jsonb_build_object('products',products,'sales',sales,'sale_journals',journals,'returns',returns,'return_journals',return_journals);
end $$;

create function cp7_model_target_binding.reference(c jsonb,p_target text,p_limit integer,p_stock jsonb,p_producer text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare facts jsonb;identity jsonb;raw_count bigint;frames text;raw_hash text;source_hash text;
begin
 facts:=cp7_model_target_binding.non_stock(c,p_target,p_limit);
 if p_producer is null or p_producer!~'^[0-9a-f]{64}$'
  or p_stock->>'contract_version'is distinct from'cp7.native-stock-row-digest.v1'
  or p_stock->>'scope'is distinct from'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS'
  or p_stock->'captured_at'is distinct from c->'captured_at'
  or p_stock->>'row_count'is null or p_stock->>'row_count'!~'^(0|[1-9][0-9]{0,18})$'
  or p_stock->>'rows_sha256'is null or p_stock->>'rows_sha256'!~'^[0-9a-f]{64}$'
  or p_stock->'raw_rows_truncated'is distinct from'false'::jsonb
  or p_stock->'raw_native_capture_status_overridden'is distinct from'false'::jsonb then
  raise exception 'CP7_MODEL_TARGET_BINDING_STOCK_REFERENCE';end if;
 -- When all raw stock is present, independently verify the supplied digest
 -- against that exact captured subset, with the existing row framing contract.
 if c->>'status'='COMPLETE'then
  select count(*),coalesce(string_agg(encode(pg_catalog.sha256(convert_to(x::text,'UTF8')),'hex'),E'\n'order by (x->>'id')collate"C"),'')
   into raw_count,frames from jsonb_array_elements(c->'facts'->'stock')x where x->>'root_id'=split_part(p_target,':',1);
  raw_hash:=encode(pg_catalog.sha256(convert_to(E'cp7.native-stock-row-digest.v1\n'||raw_count::text||E'\n'||frames,'UTF8')),'hex');
  if p_stock->>'row_count'is distinct from raw_count::text or p_stock->>'rows_sha256'is distinct from raw_hash then
   raise exception 'CP7_MODEL_TARGET_BINDING_STOCK_MISMATCH';end if;
 end if;
 -- Same identity payload as pinned cp7_model_history_scope.identity; this is
 -- a binding to captured facts, never a fabricated complete scoped raw source.
 identity:=jsonb_build_object('contract','cp7.scoped-history-source.v1','target_key',p_target,
  'non_stock',facts,'full_stock',p_stock->'rows_sha256','stock_rows',p_stock->'row_count','producer',p_producer);
 source_hash:=encode(pg_catalog.sha256(convert_to(identity::text,'UTF8')),'hex');
 return jsonb_build_object('contract_version','cp7.model-target-physical-binding.v1','target_key',p_target,
  'captured_at',c->'captured_at','scoped_source_hash',source_hash,'producer_hash',p_producer,
  'global_raw_capture_status',c->'status','global_non_stock_complete',true,'stock_reference',p_stock,
  'raw_native_capture_status_overridden',false,'target_caller_integrated',false,'production_go',false);
end $$;

alter function cp7_model_target_binding.non_stock(jsonb,text,integer)owner to cp7_capture;
alter function cp7_model_target_binding.reference(jsonb,text,integer,jsonb,text)owner to cp7_capture;
revoke all on all functions in schema cp7_model_target_binding from public,anon,authenticated,service_role;
