-- Validate the global boundary before grouping facts by physical root.
create function cp7_model_target_source_v2.non_stock_rows(c jsonb,p_limit integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=c->'facts';first_target text;answer jsonb;
begin
 if jsonb_typeof(f->'products')is distinct from'array'then raise exception 'CP7_MODEL_TARGET_BINDING_FACTS';end if;
 if jsonb_array_length(f->'products')=0 then
  if p_limit is null or p_limit not between 1 and 5000
   or c->>'contract_version'is distinct from'cp7.native-demand-facts.v1'
   or c->>'scope'is distinct from'GLOBAL_CURRENT_PHYSICAL_ROOTS'
   or c->>'status'is distinct from'COMPLETE'
   or coalesce(c->'stock_raw_omitted','false'::jsonb)is distinct from'false'::jsonb then
   raise exception 'CP7_MODEL_TARGET_BINDING_SCOPE';end if;
  perform cp7_demand.instant(c->'captured_at');
  perform cp7_wip.fields(f,array['products','stock','sales','sale_journals','returns','return_journals']);
  if exists(select 1 from jsonb_each(f)where value is distinct from'[]'::jsonb)then
   raise exception 'CP7_MODEL_TARGET_BINDING_NON_STOCK_INCOMPLETE';end if;
  return'[]'::jsonb;
 end if;
 first_target:=(f->'products'->0->>'root_id')||':'||(f->'products'->0->>'size_id');
 perform cp7_model_target_binding.non_stock(c,first_target,p_limit);
 with products as materialized(select p->>'root_id'root_id,p->>'size_id'size_id,p body from jsonb_array_elements(f->'products')p),
 sales as materialized(select s->>'id'id,s->>'sale_id'sale_id,s->>'root_id'root_id,s body from jsonb_array_elements(f->'sales')s),
 sale_journals as materialized(select j->>'id'id,j->>'sale_id'sale_id,j->>'reversal_of_id'reversal_of_id,j body from jsonb_array_elements(f->'sale_journals')j),
 journal_roots as materialized(
  select distinct j.id,s.root_id,j.body from sale_journals j join sales s on s.sale_id=j.sale_id
  union
  select distinct j.id,s.root_id,j.body from sale_journals j join sale_journals original on original.id=j.reversal_of_id
   join sales s on s.sale_id=original.sale_id
 ),returns as materialized(select r->>'id'id,r->>'return_id'return_id,s.root_id,r body
  from jsonb_array_elements(f->'returns')r join sales s on s.id=r->>'sale_item_id'),
 return_journals as materialized(select j->>'id'id,j->>'return_id'return_id,j->>'reversal_of_id'reversal_of_id,j body from jsonb_array_elements(f->'return_journals')j),
 return_journal_roots as materialized(
  select distinct j.id,r.root_id,j.body from return_journals j join returns r on r.return_id=j.return_id
  union
  select distinct j.id,r.root_id,j.body from return_journals j join return_journals original on original.id=j.reversal_of_id
   join returns r on r.return_id=original.return_id
 ),s_rows as(select root_id,jsonb_agg(body order by id collate"C")rows from sales group by root_id),
 j_rows as(select root_id,jsonb_agg(body order by id collate"C")rows from journal_roots group by root_id),
 r_rows as(select root_id,jsonb_agg(body order by id collate"C")rows from returns group by root_id),
 rj_rows as(select root_id,jsonb_agg(body order by id collate"C")rows from return_journal_roots group by root_id)
 select coalesce(jsonb_agg(jsonb_build_object('target_key',p.root_id||':'||p.size_id,'non_stock',
  jsonb_build_object('products',jsonb_build_array(p.body),'sales',coalesce(s.rows,'[]'),
   'sale_journals',coalesce(j.rows,'[]'),'returns',coalesce(r.rows,'[]'),'return_journals',coalesce(rj.rows,'[]')))
  order by p.root_id collate"C",p.size_id collate"C"),'[]')into answer
 from products p left join s_rows s using(root_id)left join j_rows j using(root_id)
  left join r_rows r using(root_id)left join rj_rows rj using(root_id);
 return answer;
end $$;
alter function cp7_model_target_source_v2.non_stock_rows(jsonb,integer)owner to cp7_capture;
revoke all on function cp7_model_target_source_v2.non_stock_rows(jsonb,integer)from public,anon,authenticated,service_role;
