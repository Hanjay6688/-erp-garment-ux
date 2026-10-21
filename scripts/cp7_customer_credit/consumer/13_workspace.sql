-- Read-only navigation for the complete isolated consumer composition. A page
-- fingerprint covers every matching row, including commits with lower UUIDs.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

create function cp7_credit.consumer_workspace_v1(p_query jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare h erp.sales_headers;assignment record;authority jsonb;kind text;q text;off integer;
 data jsonb;page jsonb:='[]';v jsonb;row_data jsonb;vectors jsonb;capacity jsonb;account jsonb;
 source_facts jsonb;dataset text;result jsonb;total integer;owner_admin boolean;capabilities jsonb;
begin
 if not cp7_sales.access_now()or not erp.has_permission('sales.return.view')then
  raise exception using errcode='42501',message='CP7_CREDIT_WORKSPACE_ACCESS_DENIED';end if;
 authority:=erp.get_my_access_v1();
 if jsonb_typeof(p_query)is distinct from'object'or
  (select array_agg(k order by k)from jsonb_object_keys(p_query)k)is distinct from
  array['dataset_sha256','expected_version','kind','limit','offset','q','review_token','sale_id']::text[]
  or jsonb_typeof(p_query->'sale_id')is distinct from'string'
  or p_query->>'sale_id'!~'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
  or jsonb_typeof(p_query->'expected_version')is distinct from'string'
  or p_query->>'expected_version'!~'^[1-9][0-9]{0,18}$'
  or(p_query->>'expected_version')::numeric>9223372036854775807
  or jsonb_typeof(p_query->'review_token')is distinct from'string'
  or p_query->>'review_token'!~'^[0-9a-f]{32}$'
  or jsonb_typeof(p_query->'kind')is distinct from'string'
  or p_query->>'kind'not in('COHORTS','TARGETS','CASH','EVENTS')
  or jsonb_typeof(p_query->'q')is distinct from'string'
  or p_query->>'q'<>btrim(p_query->>'q')or length(p_query->>'q')>120
  or jsonb_typeof(p_query->'offset')is distinct from'number'
  or p_query->>'offset'!~'^(0|[1-9][0-9]{0,6})$'
  or p_query->'limit'is distinct from'25'::jsonb
  or jsonb_typeof(p_query->'dataset_sha256')not in('null','string')
  or p_query->>'dataset_sha256'is not null and p_query->>'dataset_sha256'!~'^[0-9a-f]{64}$'then
  raise exception 'CP7_CREDIT_WORKSPACE_QUERY_INVALID';end if;
 kind:=p_query->>'kind';q:=p_query->>'q';off:=(p_query->>'offset')::integer;
 if off>1000000 or off%25<>0 or off>0 and p_query->>'dataset_sha256'is null
  or kind in('COHORTS','EVENTS')and q<>''then raise exception 'CP7_CREDIT_WORKSPACE_QUERY_INVALID';end if;
 select *into h from erp.sales_headers where id=(p_query->>'sale_id')::uuid;
 if not found then raise exception 'CP7_CREDIT_WORKSPACE_SOURCE_NOT_FOUND';end if;
 if h.row_version::text is distinct from p_query->>'expected_version'
  or cp7_sales.review_token(h.id)is distinct from p_query->>'review_token'then
  raise exception 'CP7_CREDIT_WORKSPACE_SOURCE_CHANGED';end if;
 select *into strict assignment from cp7_credit.current_leaf_assignment(h.id);
 if h.id<>assignment.current_leaf_id or h.status not in('POSTED','PARTIAL_PAID','PAID')then
  raise exception 'CP7_CREDIT_WORKSPACE_ACTIVE_CURRENT_INVOICE_REQUIRED';end if;
 -- A missing/unsupported materialization is unknown, never an empty balance.
 perform erp._cp7_current_credit_adjustment(h.id);
 owner_admin:=coalesce(erp.current_app_role(),'')in('OWNER','ADMIN');
 capabilities:=jsonb_build_object(
  'apply',erp.has_permission('sales.payment.view')and erp.has_permission('sales.payment.create')and erp.has_permission('sales.payment.post'),
  'refund',owner_admin and erp.has_permission('sales.return.create')and erp.has_permission('sales.return.post')and erp.has_permission('finance.cash.view'),
  'undo_apply',owner_admin and erp.has_permission('sales.payment.view')and erp.has_permission('sales.payment.reverse'),
  'undo_refund',owner_admin and erp.has_permission('sales.return.reverse')and erp.has_permission('finance.cash.view'));
 source_facts:=jsonb_build_object('header',to_jsonb(h),'review_token',p_query->>'review_token',
  'cohorts',coalesce((select jsonb_agg(to_jsonb(c)order by c.id)from cp7_credit.cohorts c
   join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=assignment.root_sale_id),'[]'),
  'parts',coalesce((select jsonb_agg(jsonb_build_array(to_jsonb(p),to_jsonb(part),to_jsonb(link))order by part.id)
   from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id
   join cp7_credit.recognition_plans p on p.cohort_id=c.id join cp7_credit.recognition_components component on component.plan_id=p.id
   join cp7_credit.component_parts part on part.component_id=component.id join cp7_credit.component_journals link on link.part_id=part.id
   where f.family_root_sale_id=assignment.root_sale_id),'[]'),
  'events',coalesce((select jsonb_agg(to_jsonb(e)order by e.id)from cp7_credit.consumption_events e
   join cp7_credit.cohorts c on c.id=e.cohort_id join cp7_credit.return_families f on f.id=c.family_id
   where f.family_root_sale_id=assignment.root_sale_id),'[]'));
 if kind='COHORTS'then
  select coalesce(jsonb_agg(jsonb_build_object('cohort',to_jsonb(c),'return',to_jsonb(r))order by r.physical_at,r.id,c.id),'[]')into data
   from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id
   join erp.sales_returns r on r.id=c.source_return_id where f.family_root_sale_id=assignment.root_sale_id;
 elsif kind='TARGETS'then
  select coalesce(jsonb_agg(to_jsonb(s)order by s.sale_date,s.id),'[]')into data from erp.sales_headers s
   cross join lateral cp7_credit.current_leaf_assignment(s.id)a
   where s.customer_id=h.customer_id and s.status in('POSTED','PARTIAL_PAID','PAID')
    and a.current_leaf_id=s.id and a.root_sale_id<>assignment.root_sale_id
    and(q=''or strpos(lower(s.sale_number),lower(q))>0);
 elsif kind='CASH'then
  if not owner_admin or not erp.has_permission('finance.cash.view')then
   raise exception using errcode='42501',message='CP7_CREDIT_WORKSPACE_CASH_ACCESS_DENIED';end if;
  -- Exactly the same account predicate as cash_account_facts_v1; quote/commit
  -- re-read the complete account and Native dated cash guards independently.
  select coalesce(jsonb_agg(jsonb_build_object('cash',to_jsonb(c),'account',to_jsonb(a),
   'mappings',coalesce((select jsonb_agg(to_jsonb(m)order by m.mapping_key)from erp.accounting_account_mappings m where m.account_id=a.id),'[]'))
   order by c.cash_account_code,c.id),'[]')into data
   from erp.cash_accounts c join erp.chart_accounts a on a.id=c.coa_account_id
   where c.is_active and a.is_active and a.is_postable and a.account_type='ASSET'
    and not exists(select 1 from erp.accounting_account_mappings m where m.account_id=a.id and m.mapping_key not in('CASH','BANK'))
    and(q=''or strpos(lower(concat_ws(' ',c.cash_account_code,c.cash_account_name)),lower(q))>0);
 else
  select coalesce(jsonb_agg(jsonb_build_object('event',to_jsonb(e),'return_number',r.return_number,
   'target_number',s.sale_number,'cash_name',cash.cash_account_name,
   'physical_at',cp7_credit.refund_physical_text(coalesce(o.physical_at,initial.physical_at)),
   'undone_by',(select undo.id from cp7_credit.consumption_events undo where undo.restores_event_id=e.id))
   order by e.economic_date,e.transaction_date,e.id),'[]')into data
   from cp7_credit.consumption_events e join cp7_credit.cohorts c on c.id=e.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id join erp.sales_returns r on r.id=c.source_return_id
   left join erp.sales_headers s on s.id=e.target_sale_id left join erp.cash_accounts cash on cash.id=e.cash_account_id
   left join cp7_credit.consumer_operations_v1 o on o.id=e.id
   left join cp7_credit.initial_refund_operations initial on initial.id=e.id
   where f.family_root_sale_id=assignment.root_sale_id;
 end if;
 dataset:=cp7_credit.pg_jsonb_sha256(jsonb_build_object('kind',kind,'q',q,'source',source_facts,'rows',data,'authority',authority));
 if p_query->>'dataset_sha256'is not null and p_query->>'dataset_sha256'is distinct from dataset then
  raise exception 'CP7_CREDIT_WORKSPACE_LIST_CHANGED';end if;
 total:=jsonb_array_length(data);
 for v in select value from jsonb_array_elements(data)with ordinality x(value,n)where n>off and n<=off+25 order by n loop
  if kind='COHORTS'then
   vectors:=cp7_credit.consumer_source_vectors_v1((v#>>'{cohort,id}')::uuid);
   capacity:=ow04_pure_kernel.credit_capacity_v1(vectors->'recognition',vectors->'consumptions',
    erp._cp3_business_date(statement_timestamp())::text,erp._cp3_business_date(statement_timestamp())::text);
   if capacity->'source_prefixes_nonnegative'is distinct from'true'::jsonb or(capacity->>'current_balance')::numeric<0 then
    raise exception 'CP7_CREDIT_WORKSPACE_CAPACITY_UNKNOWN';end if;
   account:=cp7_credit.credit_account_facts_v1((v#>>'{cohort,credit_account_id}')::uuid);
   row_data:=jsonb_build_object('id',v#>>'{cohort,id}','return_id',v#>>'{return,id}',
    'return_number',v#>>'{return,return_number}','available_credit',capacity->'current_balance',
    'credit_account',jsonb_build_object('id',account#>>'{account,id}','code',account#>>'{account,account_code}','name',account#>>'{account,account_name}'));
  elsif kind='TARGETS'then
   select cp7_sales.header(s,true)into strict row_data from erp.sales_headers s where s.id=(v->>'id')::uuid;
   row_data:=jsonb_build_object('id',row_data->'id','number',row_data->'number','customer_id',row_data->'customer_id',
    'row_version',row_data->'row_version','physical_at',row_data->'physical_at','status',row_data->'status',
    'open_balance',row_data#>'{financial,open_balance}');
  elsif kind='CASH'then
   account:=cp7_credit.cash_account_facts_v1((v#>>'{cash,id}')::uuid);
   row_data:=jsonb_build_object('id',account#>>'{cash,id}','code',account#>>'{cash,cash_account_code}',
    'name',account#>>'{cash,cash_account_name}','kind',account#>>'{cash,account_kind}');
  else
   perform cp7_credit.consumer_event_data_v1((v#>>'{event,id}')::uuid);
   if v->>'physical_at'is null then raise exception 'CP7_CREDIT_WORKSPACE_EVENT_PHYSICAL_UNKNOWN';end if;
   row_data:=jsonb_build_object('id',v#>>'{event,id}','cohort_id',v#>>'{event,cohort_id}',
    'kind',v#>>'{event,event_kind}','amount',cp7_credit.cent_text((v#>>'{event,amount}')::cp7_credit.cent_amount),
    'physical_at',v->'physical_at','economic_date',v#>>'{event,economic_date}','book_date',v#>>'{event,transaction_date}',
    'return_number',v->'return_number','target_sale_id',v#>'{event,target_sale_id}','target_number',v->'target_number',
    'cash_account_id',v#>'{event,cash_account_id}','cash_name',v->'cash_name',
    'restores_event_id',v#>'{event,restores_event_id}','undone_by',v->'undone_by');
  end if;
  page:=page||jsonb_build_array(row_data);
 end loop;
 if jsonb_array_length(page)<>least(25,greatest(0,total-off))then raise exception 'CP7_CREDIT_WORKSPACE_PAGE_INCOMPLETE';end if;
 result:=jsonb_build_object('contract_version','cp7.customer-credit-workspace.v1','actor_scope_id',auth.uid(),
  'read_at',statement_timestamp(),'read_only',true,'business_DML',false,'kind',kind,'q',q,
  'source',jsonb_build_object('sale_id',h.id,'number',h.sale_number,'customer_id',h.customer_id,
   'row_version',h.row_version::text,'review_token',p_query->>'review_token'),
  'capabilities',capabilities,'dataset_sha256',dataset,
  'page',jsonb_build_object('offset',off,'limit',25,'total',total::text,
   'next_offset',case when off+jsonb_array_length(page)<total then off+25 else null end,'rows',page));
 if pg_column_size(result)>8388608 then raise exception 'CP7_CREDIT_WORKSPACE_RESPONSE_TOO_LARGE';end if;
 if erp.get_my_access_v1()is distinct from authority or not cp7_sales.access_now()or not erp.has_permission('sales.return.view')then
  raise exception using errcode='42501',message='CP7_CREDIT_WORKSPACE_ACCESS_CHANGED';end if;
 return result;
end $$;
alter function cp7_credit.consumer_workspace_v1(jsonb)owner to postgres;
revoke all on function cp7_credit.consumer_workspace_v1(jsonb)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write;

create function public.erp_cp7_get_customer_credit_workspace_v1(p_query jsonb)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_credit.consumer_workspace_v1(p_query)
$$;
alter function public.erp_cp7_get_customer_credit_workspace_v1(jsonb)owner to postgres;
revoke all on function public.erp_cp7_get_customer_credit_workspace_v1(jsonb)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write;
grant execute on function public.erp_cp7_get_customer_credit_workspace_v1(jsonb)to authenticated;
