-- One server statement/snapshot and the Native capture clock. Lead/manual
-- operands are read here, never accepted from a warehouse user's payload.
create function cp7_reorder_inputs.source_within(p_products integer)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if p_products is null or p_products not between 1 and 5000 then raise exception 'CP7_REORDER_SOURCE_PRODUCT_BOUND';end if;
 return(
 with native as materialized(select cp7_baseline_native.source_within(p_products)c),
 boundary as materialized(select c,(c->>'captured_at')::timestamptz at from native),
 policy as materialized(select jsonb_build_object(
  'service_level',to_char((cp7_stock_formula.current_settings()->>'service_level')::numeric,'FM0.00'),
  'window_days',cp7_stock_formula.current_settings()->>'window_days')defaults),
 wanted_models as materialized(select distinct(x->>'model_id')::uuid model_id
  from native,jsonb_array_elements(c->'facts'->'products')x where x->>'model_id'is not null),
 lead_observations as materialized(
  select po.model_id,g.id group_id,extract(epoch from lot.produced_at-g.cut_at)/86400.0 days
  from erp.fg_lots lot join erp.cutting_groups g on g.id=lot.cutting_group_id
  join erp.production_orders po on po.id=g.po_id join wanted_models wanted on wanted.model_id=po.model_id
  join erp.qc_inspection_items qi on qi.id=lot.qc_item_id join erp.qc_inspections qc on qc.id=qi.inspection_id cross join boundary
  where lot.lot_origin='PRODUCTION'and qc.status='POSTED'and g.material_issue_posted
   and lot.produced_at<=boundary.at and lot.produced_at>boundary.at-interval'365 days'and lot.produced_at>=g.cut_at),
 lead_rows as materialized(select model_id,count(*)lots,count(distinct group_id)groups,
  case when count(distinct group_id)>=3 then round(percentile_cont(0.5)within group(order by days)::numeric,2)end days
  from lead_observations group by model_id),
 leads as materialized(select coalesce(jsonb_agg(jsonb_build_object('model_id',model_id::text,'lead_days',days::text,
  'lot_count',lots::text,'group_count',groups::text)order by model_id),'[]')rows from lead_rows),
 latest_manual as materialized(select distinct on(m.root_id)m.root_id,m.product_version_id,m.size_id,m.revision,m.reorder_point_pcs
  from cp7_stock_formula.manual_points m cross join boundary
  where m.root_id::text in(select x->>'root_id'from jsonb_array_elements(boundary.c->'facts'->'products')x)
   and m.recorded_at<=boundary.at order by m.root_id,m.revision desc),
 manuals as materialized(select coalesce(jsonb_agg(jsonb_build_object('root_id',root_id::text,'product_version_id',product_version_id::text,
  'size_id',size_id::text,'revision',revision::text,'reorder_point_pcs',reorder_point_pcs::text)order by root_id),'[]')rows from latest_manual),
 engine as materialized(select encode(extensions.digest(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),
  E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')hash
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in('cp7_reorder_inputs','cp7_reorder_reader','cp7_planning','cp7_profile','cp7_baseline_native','cp7_analysis_stage','cp7_demand','cp7_baseline','cp7_stock_formula')
   and p.prokind='f'),
 query as materialized(select jsonb_build_object(
  'from_date',((boundary.at at time zone'Asia/Jakarta')::date-(policy.defaults->>'window_days')::integer)::text,
  'through_date',((boundary.at at time zone'Asia/Jakarta')::date-1)::text,'group_mode','AS_SOLD')q from boundary cross join policy),
 complete_stock as materialized(select case when jsonb_array_length(boundary.c->'facts'->'stock')=50001 then
  cp7_reorder_inputs.stock_summary(boundary.c->'facts'->'products',boundary.at,query.q)end summary
  from boundary cross join query),
 history_stock_key as materialized(select case when complete_stock.summary is not null then complete_stock.summary->'history_data_hash'
  else(select coalesce(jsonb_agg(m order by ord),'[]')from jsonb_array_elements(boundary.c->'facts'->'stock')with ordinality movements(m,ord)
   where(m->>'physical_at')::timestamptz<((boundary.at at time zone'Asia/Jakarta')::date::timestamp at time zone'Asia/Jakarta'))end value
  from boundary cross join complete_stock)
 select jsonb_build_object('contract_version','cp7.reorder-native-source.v1','status',boundary.c->'status',
  'captured_at',boundary.c->'captured_at','query',query.q,'native',boundary.c,'defaults',policy.defaults,'product_bound',p_products,
  'stock_summary',complete_stock.summary,
  'leads',leads.rows,'manuals',manuals.rows,'engine_hash',engine.hash,
  'threshold_hash',encode(extensions.digest(convert_to(jsonb_build_object('native_non_stock',(boundary.c->'facts')-'stock',
    'native_status',boundary.c->'status','product_bound',p_products,'history_stock',history_stock_key.value,
    'profiles',boundary.c->'profiles','production_policies',boundary.c->'production_policies'->'rows',
    'query',query.q,'defaults',policy.defaults,'leads',leads.rows,'manuals',manuals.rows,'engine',engine.hash)::text,'UTF8'),'sha256'),'hex'),
  'context_hash',encode(extensions.digest(convert_to(jsonb_build_object('facts',boundary.c->'facts',
    'profiles',boundary.c->'profiles','production_policies',boundary.c->'production_policies'->'rows',
    'query',query.q,'defaults',policy.defaults,'leads',leads.rows,'manuals',manuals.rows,'engine',engine.hash,
    'complete_stock_summary',complete_stock.summary->'data_hash')::text,'UTF8'),'sha256'),'hex'),
  'apply_enabled',false,'production_go',false)
 from boundary cross join policy cross join leads cross join manuals cross join engine cross join query cross join complete_stock cross join history_stock_key);
end $$;
alter function cp7_reorder_inputs.source_within(integer)owner to cp7_capture;
revoke all on function cp7_reorder_inputs.source_within(integer)from public,anon,authenticated,service_role;
