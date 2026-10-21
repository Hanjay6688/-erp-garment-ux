-- Complete owning composition only. No table grants, locks or business DML.
do $not_an_installer$begin raise exception 'OW04_CREDIT_DEPENDENCIES_REQUIRE_COMPLETE_COMPOSITION';end $not_an_installer$;

create function cp7_credit.sales_credit_dependencies_v1(p_query jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare sale uuid;h erp.sales_headers;assignment record;off integer;total bigint;
 rows jsonb;facts jsonb;authority jsonb;result jsonb;
begin
 if not cp7_sales.access_now()or not erp.has_permission('sales.return.view')then
  raise exception using errcode='42501',message='CP7_CREDIT_DEPENDENCY_ACCESS_DENIED';end if;
 authority:=erp.get_my_access_v1();
 if jsonb_typeof(p_query)is distinct from'object'or
  (select array_agg(k order by k)from jsonb_object_keys(p_query)k)is distinct from
  array['expected_version','limit','offset','review_token','sale_id']::text[]
  or jsonb_typeof(p_query->'sale_id')is distinct from'string'
  or p_query->>'sale_id'!~*'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
  or jsonb_typeof(p_query->'expected_version')is distinct from'string'
  or p_query->>'expected_version'!~'^[1-9][0-9]{0,18}$'
  or jsonb_typeof(p_query->'review_token')is distinct from'string'
  or p_query->>'review_token'!~'^[0-9a-f]{32}$'
  or jsonb_typeof(p_query->'offset')is distinct from'number'
  or p_query->>'offset'!~'^(0|[1-9][0-9]{0,6})$'
  or p_query->'limit'is distinct from'25'::jsonb then
  raise exception 'CP7_CREDIT_DEPENDENCY_QUERY_INVALID';end if;
 sale:=(p_query->>'sale_id')::uuid;off:=(p_query->>'offset')::integer;
 if off>1000000 or off%25<>0 or(p_query->>'expected_version')::numeric>9223372036854775807 then
  raise exception 'CP7_CREDIT_DEPENDENCY_QUERY_INVALID';end if;
 select *into h from erp.sales_headers where id=sale;
 if not found then raise exception 'CP7_CREDIT_DEPENDENCY_SOURCE_NOT_FOUND';end if;
 if h.row_version::text is distinct from p_query->>'expected_version'
  or cp7_sales.review_token(sale)is distinct from p_query->>'review_token'then
  raise exception 'CP7_CREDIT_DEPENDENCY_SOURCE_CHANGED';end if;
 select *into strict assignment from cp7_credit.current_leaf_assignment(sale);
 -- A historical invoice never borrows the current leaf's financial details.
 if sale<>assignment.current_leaf_id then raise exception 'CP7_CREDIT_DEPENDENCY_CURRENT_LEAF_REQUIRED';end if;
 -- Use the same complete actual-fact proof as the authoritative AR readers.
 -- A missing/unsupported materialization is an error, never an empty list.
 perform erp._cp7_current_credit_adjustment(sale);
 select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')into facts
 from cp7_credit.consumption_events e join cp7_credit.cohorts c on c.id=e.cohort_id
 join cp7_credit.return_families f on f.id=c.family_id
 where f.family_root_sale_id=assignment.root_sale_id or e.target_sale_id=sale;
 with active as(
  select e.*,c.source_sale_id,c.source_return_id from cp7_credit.consumption_events e
  join cp7_credit.cohorts c on c.id=e.cohort_id
  join cp7_credit.return_families f on f.id=c.family_id
  where(f.family_root_sale_id=assignment.root_sale_id or e.target_sale_id=sale)
   and e.amount>0 and not exists(select 1 from cp7_credit.consumption_events undo
    where undo.restores_event_id=e.id)
 ),page as(select *from active order by economic_date,transaction_date,id offset off limit 25)
 select(select count(*)from active),coalesce(jsonb_agg(jsonb_build_object(
  'event_id',p.id::text,'kind',p.event_kind,'amount',cp7_credit.cent_text(p.amount),
  'economic_date',p.economic_date::text,'book_date',p.transaction_date::text,
  'source_sale_id',p.source_sale_id::text,'source_sale_number',s.sale_number,
  'source_return_id',p.source_return_id::text,'source_return_number',r.return_number,
  'target_sale',case when p.target_sale_id is null then null else jsonb_build_object(
   'id',target.id::text,'number',target.sale_number)end,
  'journal_id',p.journal_id::text)
  order by p.economic_date,p.transaction_date,p.id),'[]')into total,rows
 from page p join erp.sales_headers s on s.id=p.source_sale_id
 join erp.sales_returns r on r.id=p.source_return_id
 left join erp.sales_headers target on target.id=p.target_sale_id;
 if jsonb_array_length(rows)<>least(25,greatest(0,total-off))then
  raise exception 'CP7_CREDIT_DEPENDENCY_SOURCE_INCOMPLETE';end if;
 result:=jsonb_build_object('contract_version','cp7.sales-credit-dependencies.v1',
  'actor_scope_id',auth.uid()::text,'read_at',statement_timestamp(),
  'read_only',true,'business_DML',false,
  'source',jsonb_build_object('sale_id',sale::text,'number',h.sale_number,'status',h.status::text,
   'row_version',h.row_version::text,'review_token',p_query->>'review_token'),
  'dependency_sha256',cp7_credit.pg_jsonb_sha256(facts),
  'page',jsonb_build_object('offset',off,'limit',25,'total',total::text,
   'next_offset',case when off+jsonb_array_length(rows)<total then off+25 else null end),
  'dependencies',rows);
 if erp.get_my_access_v1()is distinct from authority or not cp7_sales.access_now()
  or not erp.has_permission('sales.return.view')then
  raise exception using errcode='42501',message='CP7_CREDIT_DEPENDENCY_ACCESS_CHANGED';end if;
 return result;
end $$;
alter function cp7_credit.sales_credit_dependencies_v1(jsonb)owner to postgres;
revoke all on function cp7_credit.sales_credit_dependencies_v1(jsonb)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_write;
grant execute on function cp7_credit.sales_credit_dependencies_v1(jsonb)to cp7_sales_read;

grant create on schema public to cp7_sales_read;
create function public.erp_cp7_get_sales_credit_dependencies_v1(p_query jsonb)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_credit.sales_credit_dependencies_v1(p_query)
$$;
alter function public.erp_cp7_get_sales_credit_dependencies_v1(jsonb)owner to cp7_sales_read;
revoke create on schema public from cp7_sales_read;
revoke all on function public.erp_cp7_get_sales_credit_dependencies_v1(jsonb)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_write;
grant execute on function public.erp_cp7_get_sales_credit_dependencies_v1(jsonb)to authenticated;
