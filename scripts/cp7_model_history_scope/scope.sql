create schema cp7_model_history_scope authorization cp7_capture;
revoke all on schema cp7_model_history_scope from public,anon,authenticated,service_role;
create function cp7_model_history_scope.raw(p_root uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC' as $$
with clock as materialized(select clock_timestamp()at),
-- K7: each root's first creation in one pass over every product (it was one
-- scan of the whole table per current product); same rows, same value.
established as materialized(
 select coalesce(p0.identity_root_id,p0.id)root_id,min(p0.created_at)established_at from erp.products p0 group by 1
),
products as materialized(
 select p.id,coalesce(p.identity_root_id,p.id)root_id,p.size_id,p.model_id,p.brand_id,
  p.sku,p.product_name,p.is_active,p.effective_from,p.effective_to,p.created_at,
  e.established_at,
  coalesce((select jsonb_agg(jsonb_build_object('sku_id',s.id,'sku',s.sku,'version_id',v.id,'revision',v.revision::text)order by v.id)
   from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
   join erp.bf_skus_v1 s on s.id=v.sku_id
   where m.product_root=coalesce(p.identity_root_id,p.id)and v.effective_from<=c.at
    and(v.effective_to is null or v.effective_to>c.at)),'[]')commercial
 from erp.products p cross join clock c join established e on e.root_id=coalesce(p.identity_root_id,p.id)
 where coalesce(p.identity_root_id,p.id)=p_root and p.effective_from<=c.at and(p.effective_to is null or p.effective_to>c.at)
 order by coalesce(p.identity_root_id,p.id),p.id limit 2
),
stock_limit as materialized(select count(*)n from(select 1
 from erp.fg_stock_movements m join erp.products p on p.id=m.product_id cross join clock c
 where coalesce(p.identity_root_id,p.id)in(select root_id from products)
  and m.physical_at<=c.at and m.system_created_at<=c.at limit 50001)counted),
stock as materialized(
 select m.id,coalesce(p.identity_root_id,p.id)root_id,p.size_id,m.product_id,m.lot_id,m.location_id,
  m.quality_grade,m.qty_signed::text qty_signed,m.physical_at,m.system_created_at,
  m.movement_type,m.source_type,m.source_id,m.reversal_of_id,m.book_order
 from erp.fg_stock_movements m join erp.products p on p.id=m.product_id cross join clock c
 where coalesce(p.identity_root_id,p.id)in(select root_id from products)
  and m.physical_at<=c.at and m.system_created_at<=c.at and(select n from stock_limit)<=50000 order by m.id limit 50001
),
sales as materialized(
 select i.id,h.id sale_id,coalesce(p.identity_root_id,p.id)root_id,p.size_id,
  i.product_id,i.qty_pcs::text qty_pcs,h.status,h.row_version::text revision,
  h.sale_date,h.created_at,h.updated_at,
  coalesce((select jsonb_agg(jsonb_build_object('sku_id',s.id,'version_id',v.id,'revision',v.revision::text)order by v.id)
   from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
   join erp.bf_skus_v1 s on s.id=v.sku_id
   where m.product_root=coalesce(p.identity_root_id,p.id)and v.effective_from<=h.sale_date
    and(v.effective_to is null or v.effective_to>h.sale_date)),'[]')sold_commercial
 from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id
 join erp.products p on p.id=i.product_id cross join clock c
 where coalesce(p.identity_root_id,p.id)in(select root_id from products)and h.created_at<=c.at
 order by i.id limit 50001
),
sale_journals as materialized(
 select j.id,j.source_id sale_id,j.status,j.posting_at,j.transaction_date,j.economic_date,j.reversal_of_id
 from erp.journal_entries j cross join clock c
 where(j.source_type='SALE'and j.source_id in(select sale_id from sales)
  or j.reversal_of_id in(select x.id from erp.journal_entries x
   where x.source_type='SALE'and x.source_id in(select sale_id from sales)))
  and j.posting_at<=c.at order by j.id limit 50001
),
returns as materialized(
 select ri.id,r.id return_id,r.sale_id,a.sale_item_id,ri.qty_pcs::text qty_pcs,
  r.status,r.physical_at,r.created_at
 from erp.sales_return_items ri join erp.sales_returns r on r.id=ri.return_id
 join erp.sale_stock_allocations a on a.id=ri.sale_stock_allocation_id cross join clock c
 where a.sale_item_id in(select id from sales)and r.created_at<=c.at order by ri.id limit 50001
),
return_journals as materialized(
 select j.id,j.source_id return_id,j.status,j.posting_at,j.transaction_date,j.economic_date,j.reversal_of_id
 from erp.journal_entries j cross join clock c
 where(j.source_type='SALES_RETURN'and j.source_id in(select return_id from returns)
  or j.reversal_of_id in(select x.id from erp.journal_entries x
   where x.source_type='SALES_RETURN'and x.source_id in(select return_id from returns)))
  and j.posting_at<=c.at order by j.id limit 50001
),
-- K7: built once (it was rebuilt for each later use of facts).
source as materialized(select jsonb_build_object(
 'products',coalesce((select jsonb_agg(to_jsonb(p)order by p.id)from products p),'[]'),
 'stock',coalesce((select jsonb_agg(to_jsonb(m)order by m.id)from stock m),'[]'),
 'sales',coalesce((select jsonb_agg(to_jsonb(s)order by s.id)from sales s),'[]'),
 'sale_journals',coalesce((select jsonb_agg(to_jsonb(j)order by j.id)from sale_journals j),'[]'),
 'returns',coalesce((select jsonb_agg(to_jsonb(r)order by r.id)from returns r),'[]'),
 'return_journals',coalesce((select jsonb_agg(to_jsonb(j)order by j.id)from return_journals j),'[]'))facts)
select jsonb_build_object('contract_version','cp7.model-history-facts.v1',
 'captured_at',cp7_planning.utc(c.at),'scope','SINGLE_CURRENT_PHYSICAL_ROOT',
 'status',case when jsonb_array_length(facts->'products')=1
  and(select n from stock_limit)<=50000
  and not exists(select 1 from jsonb_each(facts)where key<>'products'and jsonb_array_length(value)>50000)
  and(select count(*)from products)=(select count(distinct root_id)from products)
  and not exists(select 1 from products where jsonb_array_length(commercial)>1)
  and not exists(select 1 from sales where jsonb_array_length(sold_commercial)>1)
  and not exists(select 1 from sales s left join(select j.sale_id,count(*)n from sale_journals j where j.reversal_of_id is null group by 1)k
   on k.sale_id=s.sale_id where s.status in('POSTED','PARTIAL_PAID','PAID','REVERSED')and coalesce(k.n,0)<>1)
 then 'COMPLETE'else 'INCOMPLETE'end,'facts',facts,'stock_raw_omitted',(select n>50000 from stock_limit),'stock_rows_at_least',(select n from stock_limit))from source cross join clock c
$$;
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

create function cp7_model_history_scope.build(c jsonb,q jsonb,summary jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC' as $$
declare input jsonb;result jsonb;p jsonb;stock jsonb;target text;refs jsonb;drafts jsonb;
 current_physical numeric;native_available numeric;availability jsonb;current_rows jsonb[]:='{}';hash text;
 available_by_root jsonb;physical_by_root jsonb;drafts_by_root jsonb;
begin
 hash:=cp7_model_history_scope.identity(c);
 perform cp7_wip.fields(q,array['from_date','through_date','group_mode']);
 if cp7_demand.day(q->'through_date')<cp7_demand.day(q->'from_date')
  or cp7_demand.day(q->'through_date')-cp7_demand.day(q->'from_date')>365
  or cp7_demand.day(q->'through_date')>=((c->>'captured_at')::timestamptz at time zone'Asia/Jakarta')::date
  or q->>'group_mode'is null or q->>'group_mode'not in('AS_SOLD','RESTATED')then
  raise exception 'CP7_MODEL_HISTORY_SCOPE_QUERY';end if;
 if c->>'status'='COMPLETE'then
  if summary is not null and summary<>'null'::jsonb then raise exception 'CP7_MODEL_HISTORY_SCOPE_UNEXPECTED_SUMMARY';end if;
 else
  if summary->>'contract_version'is distinct from'cp7.reorder-stock-summary.v1'
   or summary->'captured_at'is distinct from c->'captured_at' or summary->'query'is distinct from q
   or summary->'products'is distinct from'1'::jsonb
   or summary->'raw_rows_truncated'is distinct from'false'::jsonb
   or summary->'Native_capture_status_overridden'is distinct from'false'::jsonb
   or(summary->>'raw_rows_read')::bigint is distinct from(c->'stock_reference'->>'row_count')::bigint
   or jsonb_array_length(summary->'availability')is distinct from(cp7_demand.day(q->'through_date')-cp7_demand.day(q->'from_date')+1)
   or exists(select 1 from jsonb_array_elements(summary->'availability')x where x->'target_key'is distinct from c->'target_key'
     or x->'known_at'is distinct from c->'captured_at')then
   raise exception 'CP7_MODEL_HISTORY_SCOPE_SUMMARY_BINDING';end if;
 end if;
 input:=jsonb_build_object('contract_version','cp7.demand-input.v1','snapshot_id',hash,
  'scope_id','SINGLE_CURRENT_PHYSICAL_ROOT','known_as_of',c->>'captured_at','effective_as_of',c->>'captured_at',
  'from_date',q->'from_date','through_date',q->'through_date','history_complete',true,'group_mode',q->'group_mode',
  'targets',(select coalesce(jsonb_agg(jsonb_build_object('key',(value->>'root_id')||':'||(value->>'size_id'),
   'size_id',value->>'size_id','current_group_key',coalesce(value->'commercial'->0->>'sku_id',value->>'root_id'),
   'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',value->>'id','revision','1')))order by value->>'root_id'),'[]')from jsonb_array_elements(c->'facts'->'products')),
  'events',cp7_planning.history_events(c),'availability',case when c->>'status'='COMPLETE'then cp7_planning.history_availability(c,q)else summary->'availability'end);
 result:=cp7_demand.history(input);
 -- Retain the same reservation/current-stock kernel on both input paths.
 select coalesce(array_agg(jsonb_set(x,'{availability,inputs,scope_id}',to_jsonb('SINGLE_CURRENT_PHYSICAL_ROOT'::text))order by x->>'target_key'),'{}'::jsonb[])
 into current_rows from jsonb_array_elements(cp7_reorder_inputs.current_stock(c,summary,hash))x;
 return jsonb_build_object('contract_version','cp7.scoped-demand-history.v1','scope','SINGLE_CURRENT_PHYSICAL_ROOT',
  'capture_complete',true,'target_key',c->'target_key','raw_capture_status',c->'status','raw_status_overridden',false,'captured_at',c->'captured_at','source_hash',hash,'history',result,
  'current_stock',to_jsonb(current_rows),'availability_knowledge_basis','CURRENT_CAPTURE_RESTATED_LEDGER',
  'training_known_at',c->'captured_at','model_eligibility','HISTORICAL_AVAILABILITY_KNOWLEDGE_NOT_BACKFILLED',
  'versions',jsonb_build_object('producer','scoped-native-demand-1','history','demand-1','availability','availability-1'),
  'production_go',false);
end $$;
create function cp7_model_history_scope.capture(p_target text,p_query jsonb,p_with_inputs boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb;q jsonb;summary jsonb;result jsonb;producer text;hash text;
begin
 if p_target is null or p_target!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or p_with_inputs is null then raise exception 'CP7_MODEL_HISTORY_SCOPE_QUERY';end if;
 q:=cp7_planning.history_query(p_query);
 if(q->>'through_date')::date-(q->>'from_date')::date>365 then raise exception 'CP7_MODEL_HISTORY_SCOPE_QUERY';end if;
 c:=cp7_model_history_scope.raw(split_part(p_target,':',1)::uuid);
 select encode(extensions.digest(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')into producer
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where p.prokind='f'and(n.nspname in('cp7_model_history_scope','cp7_demand','cp7_wip','cp7_history_reference')
  or n.nspname='cp7_planning'and p.proname in('history_query','history_events','history_availability','utc')
  or n.nspname='cp7_reorder_inputs'and p.proname in('current_stock','stock_summary')
  or n.nspname='cp7_analysis_stage'and p.proname in('history_stock','bounds'));
 c:=c||jsonb_build_object('target_key',p_target,'producer_hash',producer,
  'stock_reference',cp7_history_reference.stock_digest(c->'facts'->'products',(c->>'captured_at')::timestamptz));
 hash:=cp7_model_history_scope.identity(c);
 if p_with_inputs then
  if c->>'status'='INCOMPLETE'then summary:=cp7_reorder_inputs.stock_summary(c->'facts'->'products',(c->>'captured_at')::timestamptz,q);end if;
  result:=cp7_model_history_scope.build(c,q,summary);
 end if;
 return jsonb_build_object('contract_version','cp7.scoped-history-inputs.v1','scope','SINGLE_CURRENT_PHYSICAL_ROOT',
  'target_key',p_target,'query',q,'captured_at',c->'captured_at','source_hash',hash,'producer_hash',producer,
  'raw_capture_status',c->'status','raw_status_overridden',false,'source',c,'result',result,
  'actual_capture_persisted',false,'model_caller_integrated',false,'production_go',false);
end $$;

alter function cp7_model_history_scope.raw(uuid) owner to cp7_capture;
revoke all on function cp7_model_history_scope.raw(uuid) from public,anon,authenticated,service_role;
alter function cp7_model_history_scope.identity(jsonb) owner to cp7_capture;
revoke all on function cp7_model_history_scope.identity(jsonb) from public,anon,authenticated,service_role;
alter function cp7_model_history_scope.build(jsonb,jsonb,jsonb) owner to cp7_capture;
revoke all on function cp7_model_history_scope.build(jsonb,jsonb,jsonb) from public,anon,authenticated,service_role;
alter function cp7_model_history_scope.capture(text,jsonb,boolean) owner to cp7_capture;
revoke all on function cp7_model_history_scope.capture(text,jsonb,boolean) from public,anon,authenticated,service_role;
