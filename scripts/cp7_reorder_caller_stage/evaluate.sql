-- No raw WIP enters this adapter. Supply is the already validated global
-- good/ETA projection; candidates remain conditional and never mute alerts.
create schema cp7_reorder_caller authorization cp7_capture;
revoke all on schema cp7_reorder_caller from public,anon,authenticated,service_role,cp7_alert;

create function cp7_reorder_caller.evaluate(v jsonb,supply jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare products jsonb;stocks jsonb;projections jsonb;seen jsonb;history_statistics jsonb;p jsonb;product jsonb;stock jsonb;
 projected jsonb;net jsonb;lead_net jsonb;kernel jsonb;config jsonb;hist jsonb;k text;root text;item jsonb;
 free numeric;point numeric;good numeric;base_position numeric;candidate numeric;conditional_position numeric;
 status text;reason text;state text;basis text;bound boolean;analysis_at timestamptz;lead numeric;review numeric;
 rows_out jsonb[]:='{}';metadata jsonb;row_value jsonb;
begin
 perform cp7_wip.fields(v,array['points','products','threshold_source_hash','input_path','history_statistics',
  'contract_version','captured_at','query','defaults','leads','manuals','current_stock','threshold_hash',
  'threshold_captured_at','context_hash','engine_hash','native_capture_status','cache_hit','live_ROP_caller_changed','apply_enabled','production_go']);
 if v->>'contract_version'is distinct from'cp7.reorder-reader-snapshot.v1'
  or v->'points'->'query'is distinct from v->'query'or v->'apply_enabled'is distinct from'false'::jsonb
  or v->'production_go'is distinct from'false'::jsonb then raise exception 'CP7_REORDER_EVALUATE_SNAPSHOT';end if;
 perform cp7_demand.instant(v->'captured_at');perform cp7_demand.instant(v->'threshold_captured_at');
 perform cp7_demand.items(v->'products',5000);perform cp7_demand.items(v->'current_stock',5000);
 perform cp7_demand.items(v->'points'->'rows',5000);
 perform cp7_wip.fields(supply,array['contract_version','checked_at','query','status','reason','job','projection','apply_enabled','production_go']);
 if supply->>'contract_version'is distinct from'cp7.reorder-supply-cache.v1'
  or supply->>'status'is null or supply->>'status'not in('UNKNOWN','SCENARIO','PARTIAL')
  or supply->'query'is distinct from v->'query'or supply->'apply_enabled'is distinct from'false'::jsonb
  or supply->'production_go'is distinct from'false'::jsonb then raise exception 'CP7_REORDER_EVALUATE_SUPPLY';end if;
 select coalesce(jsonb_object_agg(x->>'root_id',x),'{}')into products from jsonb_array_elements(v->'products')x;
 select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into stocks from jsonb_array_elements(v->'current_stock')x;
 if(select count(*)from jsonb_each(products))<>jsonb_array_length(v->'products')
  or(select count(*)from jsonb_each(stocks))<>jsonb_array_length(v->'current_stock')then raise exception 'CP7_REORDER_EVALUATE_DUPLICATE';end if;
 if supply->'projection'<>'null'::jsonb then
  if supply->'projection'->'query'is distinct from v->'query'then raise exception 'CP7_REORDER_EVALUATE_SUPPLY';end if;
  perform cp7_demand.items(supply->'projection'->'rows',5000);
  select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into projections from jsonb_array_elements(supply->'projection'->'rows')x;
  if(select count(*)from jsonb_each(projections))<>jsonb_array_length(supply->'projection'->'rows')then raise exception 'CP7_REORDER_EVALUATE_DUPLICATE';end if;
  if supply->'projection'->>'contract_version'is distinct from'cp7.reorder-supply.v1'
   or(select count(*)from jsonb_each(projections))<>jsonb_array_length(v->'points'->'rows')
   or exists(select 1 from jsonb_each(projections)x where not stocks?x.key)then
   raise exception 'CP7_REORDER_EVALUATE_SUPPLY_SCOPE';end if;
 end if;
 -- Build the validated identity set once, instead of copying a growing
 -- object for every target. Keep the same duplicate/scope refusal.
 select coalesce(jsonb_object_agg(cp7_wip.key(x->'target_key'),true),'{}')into seen
  from jsonb_array_elements(v->'points'->'rows')x;
 if(select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'points'->'rows')then
  raise exception 'CP7_REORDER_EVALUATE_IDENTITY';end if;
 history_statistics:=v->'history_statistics';
 for p in select value from jsonb_array_elements(v->'points'->'rows')loop
  k:=cp7_wip.key(p->'target_key');root:=split_part(k,':',1);product:=products->root;stock:=stocks->k;
  if product is null or stock is null or product->'id'is distinct from p->'product_version_id'
   or product->'size_id'is distinct from p->'size_id'or stock->'size_id'is distinct from p->'size_id'
   or stock->>'root_id'is distinct from root then raise exception 'CP7_REORDER_EVALUATE_IDENTITY';end if;
  free:=cp7_wip.pcs(stock->'native_available_pcs');
  point:=null;if p->'point_pcs'<>'null'::jsonb then point:=cp7_wip.pcs(p->'point_pcs');end if;
  kernel:=p->'target';config:=kernel->'inputs';hist:=history_statistics->k;
  if hist is null then raise exception 'CP7_REORDER_EVALUATE_HISTORY';end if;
  good:=null;base_position:=null;candidate:=null;conditional_position:=null;analysis_at:=null;
  status:='UNKNOWN';reason:=coalesce(supply->>'reason','GLOBAL_ALLOCATION_UNAVAILABLE');net:=null;lead_net:=null;
  projected:=projections->k;lead:=null;review:=null;
  if p->'lead_days'<>'null'::jsonb then lead:=cp7_demand.decimal(p->'lead_days');end if;
  if config->'review_days'<>'null'::jsonb then review:=cp7_demand.decimal(config->'review_days');end if;
  bound:=false;
  if supply->>'status'in('SCENARIO','PARTIAL')and projected->>'status'='SCENARIO'
   and projected->'net'->'lead_net'->>'status'='SCENARIO'and lead is not null and review is not null
   and supply->'job'->>'state'='DONE'then
   net:=projected->'net';lead_net:=net->'lead_net';analysis_at:=cp7_demand.instant(supply->'job'->'captured_at');
   -- ROP manual replaces the trigger only. Reuse the Native L position,
   -- comparing it with that manual threshold; do not change the production
   -- target or call net() with a point above its own full target.
   bound:=projected->'size_id'=p->'size_id'and net->'inputs'->>'target_key'=k
    and net->'inputs'->'size_id'=p->'size_id'
    and net->'inputs'->'target_pcs'=kernel->'target_pcs'
    and net->'inputs'->'reorder_point_pcs'=p->'formula_point_pcs'
    and cp7_demand.instant(net->'inputs'->'lead_deadline')=analysis_at+lead*interval'1 day'
    and cp7_demand.instant(net->'inputs'->'deadline')=analysis_at+(lead+review)*interval'1 day'
    and(net->'inputs'->>'available_fg_pcs')::numeric=free
    and cp7_demand.instant(supply->'checked_at')>=cp7_demand.instant(v->'captured_at');
   if bound then
    good:=cp7_wip.pcs(lead_net->'directed_on_time_pcs')+cp7_wip.pcs(lead_net->'incoming_on_time_pcs');
    base_position:=free+good;
    if base_position is distinct from(net->>'lead_position_base_pcs')::numeric then raise exception 'CP7_REORDER_EVALUATE_POSITION';end if;
    if net->'lead_position_conditional_pcs'<>'null'::jsonb then
     conditional_position:=(net->>'lead_position_conditional_pcs')::numeric;candidate:=conditional_position-base_position;
     if candidate<0 then raise exception 'CP7_REORDER_EVALUATE_POSITION';end if;
    end if;
    status:='COMPLETE';reason:=null;
   else reason:='CURRENT_TARGET_STOCK_OR_HORIZON_CHANGED';end if;
  elsif projected is not null then reason:=coalesce(projected->>'reason',reason);end if;
  if status<>'COMPLETE'then net:=null;lead_net:=null;analysis_at:=null;end if;
  basis:=case when point is null then'NOT_ENOUGH_DATA'when p->>'point_basis'='MANUAL'then'MANUAL'else'FORMULA'end;
  state:=case when point is null or point=0 then'NO_POINT'
   when coalesce(base_position,free)<=point then'AT_OR_BELOW'else'ABOVE'end;
  metadata:=jsonb_build_object('contract_version','cp7.fg-reorder-projection.v1',
   'threshold_source',p->'source_kind','threshold_checked_at',v->'threshold_captured_at','stock_checked_at',v->'captured_at',
   'analysis_at',case when analysis_at is not null then cp7_planning.utc(analysis_at)end,
   'lead_deadline',case when bound then net->'inputs'->'lead_deadline'else'null'::jsonb end,
   'target_deadline',case when bound then net->'inputs'->'deadline'else'null'::jsonb end,
   'base_position_pcs',base_position::text,'conditional_position_pcs',conditional_position::text,
   'candidate_pcs',candidate::text,'target_pcs',kernel->'target_pcs',
   'production_base_pcs',case when bound then net->'q_base_pcs'else'null'::jsonb end,
   'production_conditional_pcs',case when bound then net->'q_conditional_pcs'else'null'::jsonb end,
   'manual_state',p->'manual_state','manual_reference',p->'manual_reference',
   'raw_WIP_credited',false,'candidate_mutes_alert',false);
  row_value:=jsonb_build_object('contract_version','cp7.fg-reorder-row.v2','target_key',k,'root_id',root,
   'size_id',p->'size_id','model_id',product->'model_id','product_id',product->'id','sku',product->'sku',
   'product_name',product->'product_name','size_code',null,'free_pcs',free::text,'sales_pcs',p->'available_total_pcs',
   'counted_days',(p->>'available_days')::integer,'sale_days',(hist->>'sale_days')::integer,
   -- Display the demand input the Native target actually used. A selected
   -- manual demand profile must not be labelled with its historical mean.
   'daily_mean',((config->>'daily_total_pcs')::numeric/nullif((config->>'counted_days')::numeric,0))::text,
   'daily_sd',p->'daily_sd','lead_days',p->'lead_days','lead_basis',p->'lead_basis',
   'lead_lots',null,'lead_groups',null,'buffer_mode',config->'mode','buffer_days',config->'buffer_days',
   'service_level',case when config->>'mode'='STATISTICAL'then config->'service_level'else'null'::jsonb end,
   'z',case when config->>'mode'='STATISTICAL'then cp7_stock_formula.z((config->>'service_level')::numeric)::text end,
   'safety_pcs',kernel->'lead_safety_pcs','formula_point',p->'formula_point_pcs',
   'manual_point',case when p->>'manual_state'='ACTIVE'then p->'point_pcs'else'null'::jsonb end,
   'manual_revision',case when p->'manual_reference'<>'null'::jsonb then(p->'manual_reference'->>'revision')::integer end,
   'point',point::text,'basis',basis,'reason',case when point is null then p->'reason'else'null'::jsonb end,
   'wip_pcs',good::text,'wip_status',status,'wip_reason',reason,'state',state,'changed_at',v->'captured_at','projection',metadata);
  if product->'is_active'='true'::jsonb then rows_out:=array_append(rows_out,row_value);end if;
 end loop;
 if(select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'products')
  or(select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'current_stock')then raise exception 'CP7_REORDER_EVALUATE_SCOPE';end if;
 return jsonb_build_object('contract_version','cp7.fg-reorder-evaluation.v2','captured_at',v->'captured_at',
  'query',v->'query','rows',to_jsonb(rows_out),'live_ROP_caller_changed',false,'apply_enabled',false,'production_go',false);
end $$;
alter function cp7_reorder_caller.evaluate(jsonb,jsonb)owner to cp7_capture;
revoke all on function cp7_reorder_caller.evaluate(jsonb,jsonb)from public,anon,authenticated,service_role,cp7_alert;
