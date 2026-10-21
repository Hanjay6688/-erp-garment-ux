-- Pending complete consumer composition. This factual reader is not a command,
-- authority grant or financial materialization. The current installer does
-- not load this file; retain the barrier until the complete owning path exists.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

-- Follow both directions. An undone application remains a historical edge:
-- deleting it from the graph could hide an unfunded earlier date rectangle.
-- UNION terminates even a cycle; dates, signs and mutable statuses do not filter
-- membership. The owning command must lock this exact set before period SHARE,
-- then compare a fresh capture without discovering earlier-order locks.
create function cp7_credit.consumer_dependency_graph_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare customer uuid;members uuid[];roots uuid[]:='{}';leaves uuid[]:='{}';
 cohorts uuid[];families uuid[];node uuid;a record;facts jsonb;answer jsonb;
begin
 select customer_id into strict customer from erp.sales_headers where id=p_sale;
 with recursive edges(a,b)as(
  select root_sale_id,previous_sale_id from cp7_note.revisions
  union select root_sale_id,replacement_sale_id from cp7_note.revisions
  union select f.family_root_sale_id,c.source_sale_id from cp7_credit.cohorts c
   join cp7_credit.return_families f on f.id=c.family_id
  union select f.family_root_sale_id,e.target_sale_id from cp7_credit.consumption_events e
   join cp7_credit.cohorts c on c.id=e.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id
   where e.event_kind='APPLY'
 ),connected(id)as(
  select p_sale union
  select case when e.a=g.id then e.b else e.a end from connected g
   join edges e on e.a=g.id or e.b=g.id
 )select array_agg(id order by id)into members from connected;
 foreach node in array members loop
  select *into strict a from cp7_credit.current_leaf_assignment(node);
  if a.customer_id is distinct from customer then
   raise exception 'CP7_CREDIT_CONSUMER_GRAPH_CUSTOMER_CHANGED';end if;
  roots:=roots||a.root_sale_id;leaves:=leaves||a.current_leaf_id;
 end loop;
 select array_agg(distinct x order by x)into roots from unnest(roots)x;
 select array_agg(distinct x order by x)into leaves from unnest(leaves)x;
 select coalesce(array_agg(id order by id),'{}')into families
  from cp7_credit.return_families where family_root_sale_id=any(roots);
 select coalesce(array_agg(id order by id),'{}')into cohorts
  from cp7_credit.cohorts where family_id=any(families);
 if exists(select 1 from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id
  cross join lateral cp7_credit.current_leaf_assignment(c.source_sale_id)m
  where c.id=any(cohorts)and(c.customer_id is distinct from customer
   or m.root_sale_id is distinct from f.family_root_sale_id))then
  raise exception 'CP7_CREDIT_CONSUMER_GRAPH_COHORT_ROOT_CHANGED';end if;
 facts:=jsonb_build_object(
  'headers',(select coalesce(jsonb_agg(to_jsonb(h)order by h.id),'[]')from erp.sales_headers h where h.id=any(members)),
  'revisions',(select coalesce(jsonb_agg(to_jsonb(r)order by r.root_sale_id,r.revision),'[]')from cp7_note.revisions r where r.root_sale_id=any(roots)),
  'families',(select coalesce(jsonb_agg(to_jsonb(f)order by f.id),'[]')from cp7_credit.return_families f where f.id=any(families)),
  'cohorts',(select coalesce(jsonb_agg(to_jsonb(c)order by c.id),'[]')from cp7_credit.cohorts c where c.id=any(cohorts)),
  'consumptions',(select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')from cp7_credit.consumption_events e where e.cohort_id=any(cohorts)));
 answer:=jsonb_build_object('contract_version','ow04.consumer-dependency-graph.v1',
  'requested_sale_id',p_sale,'customer_id',customer,'sale_ids',members,
  'root_sale_ids',roots,'current_leaf_ids',leaves,'family_ids',families,'cohort_ids',cohorts,
  'facts',facts,'facts_sha256',cp7_credit.pg_jsonb_sha256(facts),
  'source_authority_proven',false,'all_signed_consumer_history_included',true);
 return answer;
end $$;
alter function cp7_credit.consumer_dependency_graph_v1(uuid)owner to postgres;
revoke all on function cp7_credit.consumer_dependency_graph_v1(uuid)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
