-- Generated exact additive helper overlays. No Native body or role grant changes.
do $not_an_installer$begin raise exception 'OW04_NATIVE_EMPTY_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;
do $frozen_predecessors$begin
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.is_unchanged_native_return_v1(uuid)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='a53cf43cf44362cfd1701c2b9e8e67b61b3e912534e8ec2ba5ed06f106c5b493'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='s'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.is_unchanged_native_return_v1(uuid)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.native_return_enter(uuid)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='b6f61de7cb23a5da66c771e2e4a5b5d6cc963ebcc2543dcde563be50fa4e583a'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.native_return_enter(uuid)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.native_return_guard(uuid,numeric,numeric,numeric)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='1d37cc37540a982f7c8bfbf19b6945f8ae4b8d93a4a85f0e6dbd534d8b39f200'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.native_return_guard(uuid,numeric,numeric,numeric)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.post_return_journal(text,uuid,date,text,jsonb)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='dcd2dd2737a249f6b0fff9fd30765be5e5d7bef61a55f52c802b6184722cf140'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.post_return_journal(text,uuid,date,text,jsonb)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.native_return_complete(uuid,numeric,numeric)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='a98db4b645991db1b6b3d93ad614edb54382c57a2395b184eb1b45f052d970f1'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.native_return_complete(uuid,numeric,numeric)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.native_return_leave(uuid)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='507136a7bbcce2e2234ba6f82d6038a4891ad7bb37521e695782c27b3d52a11f'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.native_return_leave(uuid)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.assert_bound_post(text,uuid,date,jsonb)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='0a6cef4f65c8b0ad0f380f13a312c1688bd82075df2605de51f20c9c46ec3334'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.assert_bound_post(text,uuid,date,jsonb)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.bound_book_date(text,uuid,date,jsonb)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='e00a52b3cf7e05120f1df0c1ee7cab21f815b77b447bfb4c02d90a7bd4d66b62'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.bound_book_date(text,uuid,date,jsonb)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.bound_audit_context()'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='0fe9f09937ad330668a17aac3a4fc3f2fd35c210832be9c5f29b856440147c16'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.bound_audit_context()';end if;
 if not exists(select 1 from pg_proc p where p.oid='ow04_source_proposal.verify_return_member_v1(uuid)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='d9332a1ed9b54187ef57c3879b92ad89c0f177e7530171f22244ddacc45559ce'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='s'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: ow04_source_proposal.verify_return_member_v1(uuid)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.assert_financial_materialization_provenance(jsonb)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='564734f5709cfc9529b41688b3f7f82fcf3f833e822f04f4616a6e9a1ad24f33'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='s'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.assert_financial_materialization_provenance(jsonb)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.enforce_initial_return_closure_v1()'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='8b6bb6b8a241be53e2855554c758759fb156e59696b7ca336ddeef5644bec59c'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.enforce_initial_return_closure_v1()';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.native_source_enter(text,uuid)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='3c1ed9947d1a9e785334aa9cd6fde9f02564c93b7074376830277104c96f5cbe'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.native_source_enter(text,uuid)';end if;
 if not exists(select 1 from pg_proc p where p.oid='cp7_credit.native_source_complete(text,uuid)'::regprocedure
  and encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex')='519f15aaf60c712d971a72cbfc13583446cdd2b03a4f05af058032864985be1b'
  and p.proowner='postgres'::regrole and p.prosecdef and p.provolatile='v'
  and p.proconfig@>array['search_path=""','TimeZone=UTC']
  and not has_function_privilege('authenticated',p.oid,'EXECUTE')
  and not has_function_privilege('anon',p.oid,'EXECUTE')
  and not has_function_privilege('service_role',p.oid,'EXECUTE'))then
  raise exception 'OW04_NATIVE_EMPTY_FROZEN_HELPER_OR_METADATA_CHANGED: cp7_credit.native_source_complete(text,uuid)';end if;
end $frozen_predecessors$;

create or replace function cp7_credit.is_unchanged_native_return_v1(p_return uuid)returns boolean
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
begin
 -- No unregistered Native bypass remains after the technical operation is installed.
 return false;
end $$;

create or replace function cp7_credit.native_return_enter(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare r erp.sales_returns;w cp7_credit.initial_return_work;s cp7_credit.return_command_scope;q cp7_sales.requests;b jsonb;ids uuid[];op uuid;actual_items jsonb;expected_items jsonb;
begin
 if cp7_credit.native_empty_is_direct_v1()then perform cp7_credit.native_empty_enter_v1(p_return);return;end if;
 -- Called after the exact Native require_internal + FG. No new admission
 -- branch is installed into require_internal by these functions.
 select *into strict r from erp.sales_returns where id=p_return;
 if r.status<>'DRAFT'then raise exception 'CP7_CREDIT_PRIOR_SEAL_OWN_DRAFT_REQUIRED';end if;
 if cp7_credit.is_unchanged_native_return_v1(p_return)then return;end if;
 if not exists(select 1 from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()
  and c.actor=auth.uid()and c.sale_id=r.sale_id and c.action='RETURN')then
  raise exception 'CP7_CREDIT_RETURN_CORRECTION_OR_NATIVE_ROUTE_UNIMPLEMENTED';end if;
 perform cp7_credit.assert_only_own_return_native_context(r.sale_id);
 select *into w from cp7_credit.initial_return_work where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if w.operation_id is null then
  -- Existing ordinary CP7 RETURN remains possible, including subsequent empty
  -- families. The exact pending request must be uniquely attributable.
  select array_agg(q0.request_id)into ids from cp7_sales.requests q0 where q0.actor=auth.uid()and q0.action='RETURN'and q0.response is null
   and(q0.payload->>'sale_id')::uuid=r.sale_id and q0.payload->>'return_number'=r.return_number
   and(q0.payload->>'physical_at')::timestamptz=r.physical_at;
  if cardinality(ids)is distinct from 1 then raise exception 'CP7_CREDIT_ORDINARY_REQUEST_NOT_ATTRIBUTABLE';end if;
  select *into strict q from cp7_sales.requests where actor=auth.uid()and request_id=ids[1];
  b:=cp7_credit.build_initial_return_for_draft_v1(q.payload,q.expected_version,cp7_credit.initial_choice_v1(null),r.id);
  -- The own DRAFT is part of the Native lock manifest, but it is not BEFORE
  -- financial history. This exclusion is derived here from the actual own
  -- pending RETURN context, never from a caller-chosen quote/exclusion ID.
  b:=jsonb_set(b,'{preserved_source}',cp7_credit.initial_preserved_source_v1(r.sale_id,r.id));
  op:=gen_random_uuid();
  insert into cp7_credit.initial_return_work(operation_id,backend_pid,transaction_id,actor,request_id,source_sale_id,origin,phase,expected_version,
   legacy_payload,settlement,payload_sha256,quote_sha256,authority_snapshot,source_snapshot,source_lock_sha256,projection,projection_sha256,
   projected_kernel,prior_causal,prior_causal_manifest,period_snapshot)
  values(op,pg_backend_pid(),txid_current(),auth.uid(),q.request_id,r.sale_id,'ORDINARY','SEALED',q.expected_version,q.payload,null,
   cp7_credit.pg_jsonb_sha256(q.payload),null,b->'authority',b,ow04_source_proposal.sha(b->'source'->'source_lock_ids'),b->'projection',
   ow04_source_proposal.sha(b->'projection'),b->'projected_kernel',b->'prior_causal',b->'prior_causal_manifest',b->'period_snapshot');
  select *into strict w from cp7_credit.initial_return_work where operation_id=op;
 else
  if w.origin<>'REVIEWED_SETTLEMENT'or w.phase<>'SEALED'or w.source_sale_id<>r.sale_id then raise exception 'CP7_CREDIT_OWN_REVIEWED_SCOPE_REQUIRED';end if;
  if cp7_credit.initial_preserved_source_v1(w.source_sale_id,r.id)is distinct from w.source_snapshot->'preserved_source'
   or cp7_credit.return_command_access(w.settlement->>'mode')is distinct from w.authority_snapshot
   or(select to_jsonb(p)from erp.accounting_period_control p where singleton_id=1)is distinct from w.period_snapshot then
   raise exception 'CP7_CREDIT_SEALED_SOURCE_CHANGED';end if;
 end if;
 select coalesce(jsonb_agg(jsonb_build_object('allocation_id',i.sale_stock_allocation_id,'location_id',i.location_id,'qty_pcs',i.qty_pcs::text,
  'quality_grade',i.quality_grade,'refund_amount',cp7_credit.cent_text(i.refund_amount),'notes',i.notes)order by i.sale_stock_allocation_id),'[]')into actual_items
  from erp.sales_return_items i where i.return_id=r.id;
 select jsonb_agg(x||jsonb_build_object('refund_amount',cp7_credit.cent_text((x->>'refund_amount')::numeric))order by x->>'allocation_id')into expected_items
  from jsonb_array_elements(w.legacy_payload->'items')x;
 if actual_items is distinct from expected_items then raise exception 'CP7_CREDIT_DRAFT_TO_ACTUAL_ITEMS_MISMATCH';end if;
 update cp7_credit.initial_return_work set return_id=r.id,phase='ENTERED'where operation_id=w.operation_id;
 if w.origin='REVIEWED_SETTLEMENT'then update cp7_credit.return_command_scope set return_id=r.id,stage='NATIVE'
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and request_id=w.request_id;end if;
 insert into cp7_credit.return_native_scope(backend_pid,transaction_id,actor,return_id,source_sale_id,customer_id,origin,request_id,
  source_lock_sha256,projection_sha256,prior_causal,prior_causal_manifest,journal_effect,planned_book_date,recognition_nonempty,explicit_choice)
 values(pg_backend_pid(),txid_current(),auth.uid(),r.id,r.sale_id,r.customer_id,w.origin,w.request_id,w.source_lock_sha256,w.projection_sha256,
  w.prior_causal,w.prior_causal_manifest,w.projection->>'journal_effect',(w.projection->>'planned_book_date')::date,
  (w.projected_kernel->>'has_recognition_effect')::boolean,w.settlement is not null and w.settlement<>'null'::jsonb);
 insert into cp7_credit.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),w.request_id,null,
  case when w.origin='REVIEWED_SETTLEMENT'then'RETURN_SETTLEMENT'else'RETURN'end,w.payload_sha256,coalesce(w.quote_sha256,w.projection_sha256),w.authority_snapshot);
 perform cp7_credit.assert_return_owner_context(r.id);
end $$;

create or replace function cp7_credit.native_return_guard(p_return uuid,p_refund numeric,p_net_after numeric,p_raw_paid numeric)returns numeric
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;v numeric;
begin
 if cp7_credit.native_empty_owns_return_v1(p_return)then return cp7_credit.native_empty_guard_v1(p_return,p_refund,p_net_after,p_raw_paid);end if;
 if cp7_credit.is_unchanged_native_return_v1(p_return)then return p_raw_paid;end if;
 perform cp7_credit.assert_return_owner_context(p_return);
 select *into strict w from cp7_credit.initial_return_work where return_id=p_return;
 perform cp7_credit.cent_text(p_refund::cp7_credit.cent_amount);
 if(p_refund,p_net_after,p_raw_paid)is distinct from((w.projection->>'return_amount')::numeric,(w.projection->>'net_after')::numeric,(w.projection->>'raw_paid')::numeric)then
  raise exception 'CP7_CREDIT_NATIVE_RETURN_TOTALS_CHANGED';end if;
 if w.origin='ORDINARY'then
  -- Preserve the unchanged Native paid exception and its original wording.
  if p_raw_paid>p_net_after then return p_raw_paid;end if;
  if(w.projected_kernel->>'has_recognition_effect')::boolean then raise exception 'CP7_CREDIT_EXPLICIT_RECOGNITION_REVIEW_REQUIRED';end if;
  v:=p_raw_paid;
 else
  if(w.projected_kernel->>'has_recognition_effect')::boolean and(w.settlement->>'mode'is null or w.credit_account_snapshot is null)then
   raise exception 'CP7_CREDIT_EXPLICIT_RECOGNITION_REVIEW_REQUIRED';end if;
  v:=p_raw_paid-(w.projected_kernel->>'net_current_k')::numeric;
 end if;
 update cp7_credit.return_native_scope set native_refund=p_refund,native_net_after=p_net_after,guard_effective_paid=v
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and return_id=p_return;
 return v;
end $$;

create or replace function cp7_credit.post_return_journal(p_type text,p_return uuid,p_economic date,p_description text,p_lines jsonb)returns uuid
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;j uuid;
begin
 if cp7_credit.native_empty_owns_return_v1(p_return)then return cp7_credit.native_empty_post_return_journal_v1(p_type,p_return,p_economic,p_description,p_lines);end if;
 if cp7_credit.is_unchanged_native_return_v1(p_return)then
  if p_type<>'SALES_RETURN'or p_economic is distinct from(select(physical_at at time zone'Asia/Jakarta')::date from erp.sales_returns where id=p_return)then
   raise exception 'CP7_CREDIT_LEGACY_NATIVE_RETURN_SOURCE_CHANGED';end if;
  return erp.post_journal(p_type,p_return,p_economic,p_description,p_lines);
 end if;
 perform cp7_credit.assert_return_owner_context(p_return);
 select *into strict w from cp7_credit.initial_return_work where return_id=p_return;
 if p_type<>'SALES_RETURN'or p_economic<>(w.projection->>'economic_date')::date
  or w.projection->>'journal_effect'<>'JOURNAL_EXPECTED'
  or cp7_credit.initial_line_semantics_v1(p_lines)is distinct from cp7_credit.initial_line_semantics_v1(w.projection->'lines')then
  raise exception 'CP7_CREDIT_NATIVE_RETURN_PROJECTION_CHANGED';end if;
 insert into cp7_credit.posting_scope values(pg_backend_pid(),txid_current(),auth.uid(),w.request_id,'RETURN',null,null,null,
  w.source_sale_id,p_return,p_type,p_return,p_economic,(w.projection->>'planned_book_date')::date,cp7_credit.native_lines_sha256(p_lines));
 j:=cp7_credit._post_journal_bound(p_type,p_return,p_economic,p_description,p_lines);
 delete from cp7_credit.posting_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 perform cp7_credit.assert_return_owner_context(p_return);return j;
end $$;

create or replace function cp7_credit.native_return_complete(p_return uuid,p_refund numeric,p_net_after numeric)returns numeric
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;x record;a jsonb;recognition_sha text;refund_op uuid;full_k numeric;result numeric;
begin
 if cp7_credit.native_empty_owns_return_v1(p_return)then return cp7_credit.native_empty_complete_v1(p_return,p_refund,p_net_after);end if;
 if cp7_credit.is_unchanged_native_return_v1(p_return)then
  return(select coalesce(sum(p.amount),0)from erp.sales_payments p join erp.sales_returns r on r.sale_id=p.sale_id where r.id=p_return and p.status='POSTED');
 end if;
 perform cp7_credit.assert_return_owner_context(p_return);
 select *into strict w from cp7_credit.initial_return_work where return_id=p_return;
 if w.phase<>'ENTERED'or(p_refund,p_net_after)is distinct from((w.projection->>'return_amount')::numeric,(w.projection->>'net_after')::numeric)then
  raise exception 'CP7_CREDIT_NATIVE_COMPLETION_TOTALS_CHANGED';end if;
 perform cp7_credit.store_initial_plan_v1(w.operation_id);
 select *into strict w from cp7_credit.initial_return_work where operation_id=w.operation_id;
 if w.plan_id is not null then
  for x in select id from cp7_credit.recognition_components where plan_id=w.plan_id order by ordinal loop perform cp7_credit.post_component(x.id);end loop;
 end if;
 a:=cp7_credit.materialize_initial_objects_v1(w.operation_id);
 recognition_sha:=cp7_credit.pg_jsonb_sha256(a->'actual_objects');
 full_k:=(w.actual_kernel->>'net_current_k')::numeric;
 if w.settlement->>'mode'='REFUND'then
  if full_k<=0 or w.cohort_id is null then raise exception 'CP7_CREDIT_NO_ZERO_OR_UNBOUND_REFUND';end if;
  refund_op:=gen_random_uuid();
  update cp7_credit.initial_return_work set refund_operation_id=refund_op where operation_id=w.operation_id;
 end if;
 select *into strict w from cp7_credit.initial_return_work where operation_id=w.operation_id;
 insert into cp7_credit.initial_return_materializations(operation_id,actor,request_id,source_sale_id,source_return_id,family_id,family_ordinal,cohort_id,plan_id,origin,
  expected_version,legacy_payload,settlement,payload_sha256,quote_sha256,authority_snapshot,source_snapshot,source_lock_sha256,projection,projection_sha256,
  prior_causal,prior_causal_manifest,period_snapshot,actual_fact,actual_event,actual_kernel,projection_actual_proof,projection_actual_proof_sha256,
  recognition_manifest_sha256,materialization_id,refund_operation_id)
 values(w.operation_id,w.actor,w.request_id,w.source_sale_id,w.return_id,w.family_id,w.family_ordinal,w.cohort_id,w.plan_id,w.origin,w.expected_version,w.legacy_payload,w.settlement,
  w.payload_sha256,w.quote_sha256,w.authority_snapshot,w.source_snapshot,w.source_lock_sha256,w.projection,w.projection_sha256,w.prior_causal,w.prior_causal_manifest,w.period_snapshot,
  w.actual_fact,w.actual_event,w.actual_kernel,w.projection_actual_proof,ow04_source_proposal.sha(w.projection_actual_proof),recognition_sha,w.materialization_id,refund_op);
 if refund_op is not null then
  insert into cp7_credit.initial_refund_operations(id,cohort_id,initial_plan_id,actor,request_id,backend_pid,transaction_id,root_sale_id,current_leaf_id,full_amount,
   cash_account_id,physical_at,reason,reference,payload_sha256,quote_sha256,source_lock_sha256,projection_sha256,recognition_manifest_sha256,required_book_floor,
   materialization_ordinal,authority_snapshot,cash_account_snapshot,book_floor_manifest)
  values(refund_op,w.cohort_id,w.plan_id,w.actor,w.request_id,w.backend_pid,w.transaction_id,w.source_sale_id,w.source_sale_id,full_k,(w.settlement->>'cash_account_id')::uuid,
   (w.settlement->>'refund_physical_at')::timestamptz,btrim(w.legacy_payload->>'change_reason'),w.settlement->>'reference',w.payload_sha256,w.quote_sha256,
   w.source_lock_sha256,w.projection_sha256,recognition_sha,(w.projection->'refund_book_plan'->>'selected_book_date')::date,
   2,w.authority_snapshot,w.cash_account_snapshot,w.projection->'refund_book_plan');
  perform cp7_credit.post_initial_refund(refund_op,w.cohort_id);
 end if;
 perform cp7_credit.assert_current_materialized_profile(w.source_sale_id,w.source_sale_id,w.source_sale_id);
 result:=(w.projection->>'raw_paid')::numeric-full_k;
 if result<0 or result>p_net_after then raise exception 'CP7_CREDIT_ACTUAL_EFFECTIVE_PAID_INVALID';end if;
 update cp7_credit.return_native_scope set completed=true,guard_effective_paid=result where backend_pid=w.backend_pid and transaction_id=w.transaction_id and return_id=p_return;
 update cp7_credit.initial_return_work set phase='COMPLETE'where operation_id=w.operation_id;
 perform cp7_credit.assert_return_owner_context(p_return);return result;
end $$;

create or replace function cp7_credit.native_return_leave(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;h erp.sales_headers;net numeric;paid numeric;
begin
 if cp7_credit.native_empty_owns_return_v1(p_return)then perform cp7_credit.native_empty_leave_v1(p_return);return;end if;
 if cp7_credit.is_unchanged_native_return_v1(p_return)then return;end if;
 perform cp7_credit.assert_return_owner_context(p_return);
 select *into strict w from cp7_credit.initial_return_work where return_id=p_return;
 if w.phase<>'COMPLETE'or not exists(select 1 from cp7_credit.return_native_scope n where n.backend_pid=w.backend_pid and n.transaction_id=w.transaction_id
  and n.return_id=p_return and n.completed)then raise exception 'CP7_CREDIT_NATIVE_COMPLETION_REQUIRED';end if;
 select *into strict h from erp.sales_headers where id=w.source_sale_id;
 net:=(w.projection->>'net_after')::numeric;paid:=cp7_credit.current_effective_paid(w.source_sale_id);
 if h.status is distinct from(case when paid=net then'PAID'when paid>0 and paid<net then'PARTIAL_PAID'else'POSTED'end)then
  raise exception 'CP7_CREDIT_FINAL_NATIVE_STATUS_CHANGED';end if;
 if exists(select 1 from cp7_credit.posting_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id)
  or exists(select 1 from cp7_credit.initial_refund_posting_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id)then
  raise exception 'CP7_CREDIT_POSTING_SCOPE_LEAK';end if;
 delete from cp7_credit.return_native_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id and return_id=p_return;
 delete from cp7_credit.execution_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id and actor=w.actor;
 if w.origin='ORDINARY'then delete from cp7_credit.initial_return_work where operation_id=w.operation_id;end if;
end $$;

create or replace function cp7_credit.assert_bound_post(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare x cp7_credit.posting_scope;c cp7_credit.recognition_components;q cp7_credit.component_parts;h cp7_credit.cohorts;
begin
 if cp7_credit.native_empty_post_scope_v1()then perform cp7_credit.assert_native_empty_bound_post_v1(p_type,p_source,p_economic,p_lines);return;end if;
 select *into strict x from cp7_credit.posting_scope where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'
  or(x.source_type,x.source_id,x.economic_date,x.lines_sha256_pg)is distinct from
   (p_type,p_source,p_economic,cp7_credit.native_lines_sha256(p_lines))then
  raise exception using errcode='42501',message='CP7_CREDIT_PAIRED_POST_SCOPE_REQUIRED';end if;
 if x.post_kind='COMPONENT'then
  perform cp7_credit.validate_component(x.component_id);
  select *into strict c from cp7_credit.recognition_components where id=x.component_id;
  select *into strict q from cp7_credit.component_parts where id=x.part_id and component_id=c.id;
  select h0.*into strict h from cp7_credit.cohorts h0 join cp7_credit.recognition_plans p on p.cohort_id=h0.id where p.id=c.plan_id;
  if p_type<>'CP7_CUSTOMER_CREDIT_RECOGNITION'or p_source<>q.id
   or(x.plan_id,x.source_sale_id,x.source_return_id,x.economic_date,x.transaction_date)is distinct from
    (c.plan_id,h.source_sale_id,h.source_return_id,c.economic_date,c.transaction_date)
   or cp7_credit.native_cent_lines(p_lines)is distinct from cp7_credit.part_lines(q.id)then raise exception 'CP7_CREDIT_COMPONENT_POST_SCOPE_CHANGED';end if;
 else
  perform cp7_credit.assert_return_owner_context(x.source_return_id);
  if p_type<>'SALES_RETURN'or p_source<>x.source_return_id then raise exception 'CP7_CREDIT_RETURN_POST_SCOPE_CHANGED';end if;
 end if;
end $$;

create or replace function cp7_credit.bound_book_date(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns date
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.posting_scope;w cp7_credit.initial_return_work;lawful date;expected date;
begin
 if cp7_credit.native_empty_post_scope_v1()then return cp7_credit.native_empty_bound_book_v1(p_type,p_source,p_economic,p_lines);end if;
 perform cp7_credit.assert_bound_post(p_type,p_source,p_economic,p_lines);
 select *into strict s from cp7_credit.posting_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 lawful:=erp.resolve_accounting_transaction_date(p_economic);
 if lawful is null or s.transaction_date<lawful or s.transaction_date<p_economic
  or s.transaction_date>(statement_timestamp()at time zone'Asia/Jakarta')::date then raise exception 'CP7_CREDIT_BOUND_DATE_INVALID';end if;
 if s.post_kind='RETURN'then
  select *into strict w from cp7_credit.initial_return_work where return_id=s.source_return_id;
  if p_economic<>(w.projection->>'economic_date')::date or w.projection->>'journal_effect'<>'JOURNAL_EXPECTED'
   or cp7_credit.initial_line_semantics_v1(p_lines)is distinct from cp7_credit.initial_line_semantics_v1(w.projection->'lines')then
   raise exception 'CP7_CREDIT_NATIVE_RETURN_PROJECTION_CHANGED';end if;
  if w.prior_causal->>'proof_sha256'is distinct from ow04_source_proposal.sha(w.prior_causal_manifest)then raise exception 'CP7_CREDIT_PRIOR_PROOF_CHANGED';end if;
  expected:=greatest(lawful,(w.prior_causal->>'causal_book_floor')::date);
  if s.transaction_date is distinct from expected or s.transaction_date is distinct from(w.projection->>'planned_book_date')::date then
   raise exception 'CP7_CREDIT_NATIVE_RETURN_BOOK_PROJECTION_CHANGED';end if;
 end if;
 return s.transaction_date;
end $$;

create or replace function cp7_credit.bound_audit_context()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare x cp7_credit.posting_scope;p cp7_credit.recognition_plans;
begin
 if cp7_credit.native_empty_post_scope_v1()then return cp7_credit.native_empty_bound_audit_v1();end if;
 select *into strict x from cp7_credit.posting_scope where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 if x.post_kind='COMPONENT'then select *into strict p from cp7_credit.recognition_plans where id=x.plan_id;end if;
 return jsonb_build_object('book_date_basis','SOURCE_BOUND_NATIVE_PROFILE','posting_kind',x.post_kind,
  'source_sale_id',x.source_sale_id,'source_return_id',x.source_return_id,'plan_id',x.plan_id,
  'component_id',x.component_id,'part_id',x.part_id,'lines_sha256_pg',x.lines_sha256_pg,
  'lawful_book_date',erp.resolve_accounting_transaction_date(x.economic_date),
  'before_source_sha256',p.before_source_sha256,'after_source_sha256',p.after_source_sha256);
end $$;

create or replace function ow04_source_proposal.verify_return_member_v1(p_return uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare member jsonb;registration jsonb;parent jsonb;family_rows jsonb;members jsonb;fact jsonb;proof jsonb;
 expected jsonb;assignment jsonb;actual_assignment jsonb;item_lineage jsonb;member_kind text;predecessor uuid;lineage_id uuid;
 r erp.sales_returns;old erp.sales_returns;link cp7_sales_return_correction.links;revision cp7_note.revisions;
 previous_family uuid;family_id uuid;root uuid;ordinal bigint;seen uuid[];cursor uuid;cursor_row jsonb;n bigint;one record;
 source_family jsonb;causal_sales uuid[];sale_position bigint;causal_floor date;source_book date;
begin
 if exists(select 1 from cp7_credit.native_empty_operations where source_return_id=p_return)then return cp7_credit.verify_native_empty_member_v1(p_return);end if;
 if to_regclass('cp7_credit.return_families')is null or to_regclass('cp7_credit.return_family_members')is null then
  raise exception 'OW04_MEMBER_REGISTRY_MISSING';end if;
 execute 'select to_jsonb(m)from cp7_credit.return_family_members m where m.return_id=$1'into member using p_return;
 if member is null then raise exception 'OW04_MEMBER_UNREGISTERED_RETURN';end if;
 family_id:=(member->>'family_id')::uuid;
 execute 'select to_jsonb(f)from cp7_credit.return_families f where f.id=$1'into registration using family_id;
 if registration is null then raise exception 'OW04_MEMBER_REGISTRATION_MISSING';end if;
 root:=(registration->>'family_root_sale_id')::uuid;ordinal:=(registration->>'family_ordinal')::bigint;
 execute 'select coalesce(jsonb_agg(to_jsonb(f)order by f.family_ordinal),''[]'')from cp7_credit.return_families f where f.family_root_sale_id=$1'into family_rows using root;
 execute 'select coalesce(jsonb_agg(to_jsonb(m)order by m.return_id),''[]'')from cp7_credit.return_family_members m where m.family_id=$1'into members using family_id;
 if registration->>'assignment_kind'is distinct from'NEW_POST'then
  raise exception 'OW04_MEMBER_HISTORICAL_ORDER_NOT_QUALIFIED';end if;
 -- This checks protected persisted assignment facts. Only the owning writer
 -- can attest NEW_POST under FG. It cannot retroactively manufacture order.
 n:=0;
 for one in select value from jsonb_array_elements(family_rows)loop
  n:=n+1;
  if(one.value->>'family_ordinal')::bigint<>n then raise exception 'OW04_MEMBER_ORDINAL_CHAIN_INVALID';end if;
 end loop;
 if ordinal<1 then raise exception 'OW04_MEMBER_ORDINAL_CHAIN_INVALID';end if;
 select(x->>'id')::uuid into previous_family from jsonb_array_elements(family_rows)x where(x->>'family_ordinal')::bigint=ordinal-1;
 assignment:=jsonb_build_object('contract_version','ow04.return-family-assignment.v1','family_id',family_id,
  'family_root_sale_id',root,'family_ordinal',ordinal::text,'first_return_id',registration->'first_return_id',
  'previous_family_id',previous_family,'actor',registration->'actor','request_id',registration->'request_id');
 actual_assignment:=registration->'assignment_proof';
 if actual_assignment is distinct from assignment or registration->>'source_sha256'is distinct from ow04_source_proposal.sha(assignment)then
  raise exception 'OW04_MEMBER_ASSIGNMENT_PROOF_CHANGED';end if;
 select *into strict r from erp.sales_returns where id=p_return;
 fact:=ow04_source_proposal.return_fact_v1(p_return);
 if(fact->>'family_root_sale_id')::uuid<>root then raise exception 'OW04_MEMBER_WRONG_ROOT';end if;
 proof:=member->'actual_lineage_snapshot';member_kind:=member->>'member_kind';
 predecessor:=(proof->>'predecessor_return_id')::uuid;lineage_id:=(proof->>'native_lineage_id')::uuid;
 item_lineage:=proof->'return_item_lineage';
 if member_kind='ORIGINAL'then
  if p_return is distinct from(registration->>'first_return_id')::uuid or predecessor is not null or lineage_id is not null
   or member->>'actor'is distinct from registration->>'actor'or member->>'request_id'is distinct from registration->>'request_id'
   or item_lineage is distinct from'{}'::jsonb then raise exception 'OW04_MEMBER_ORIGINAL_BINDING_INVALID';end if;
 elsif member_kind in('RETURN_CORRECTION','NOTE_REPLAY')then
  select value into parent from jsonb_array_elements(members)where(value->>'return_id')::uuid=predecessor;
  if parent is null or predecessor=p_return then raise exception 'OW04_MEMBER_PREDECESSOR_INVALID';end if;
  select *into strict old from erp.sales_returns where id=predecessor;
  if old.status<>'REVERSED'or old.customer_id<>r.customer_id then raise exception 'OW04_MEMBER_PREDECESSOR_STATE_INVALID';end if;
  if member_kind='RETURN_CORRECTION'then
   select *into strict link from cp7_sales_return_correction.links where id=lineage_id;
   if link.original_id<>predecessor or link.replacement_id<>p_return or link.sale_id<>r.sale_id or old.sale_id<>r.sale_id
    or member->>'actor'is distinct from link.actor::text or member->>'request_id'is distinct from link.request_id::text
    or item_lineage is distinct from'{}'::jsonb then raise exception 'OW04_MEMBER_RETURN_CORRECTION_BINDING_INVALID';end if;
   perform ow04_source_proposal.require_restatement_v1(j.id,'RETURN')from erp.journal_entries j
    where j.source_type='SALES_RETURN'and j.source_id=predecessor and j.reversal_of_id is null;
  else
   select *into strict revision from cp7_note.revisions where id=lineage_id;
   if revision.root_sale_id<>root or revision.previous_sale_id<>old.sale_id or revision.replacement_sale_id<>r.sale_id
    or member->>'actor'is distinct from revision.actor::text or member->>'request_id'is distinct from revision.request_id::text
    or r.physical_at<>old.physical_at or jsonb_typeof(item_lineage)is distinct from'object'
    or(select count(*)from jsonb_object_keys(item_lineage))<>(select count(*)from erp.sales_return_items where return_id=p_return)
    or(select count(*)from erp.sales_return_items where return_id=p_return)<>(select count(*)from erp.sales_return_items where return_id=predecessor)
    or(select count(distinct value)from jsonb_each_text(item_lineage))<>(select count(*)from jsonb_each_text(item_lineage))then
    raise exception 'OW04_MEMBER_NOTE_HEADER_OR_ITEMS_INVALID';end if;
   if exists(select 1 from jsonb_each_text(item_lineage)m left join erp.sales_return_items ni on ni.id=m.key::uuid and ni.return_id=p_return
    left join erp.sales_return_items oi on oi.id=m.value::uuid and oi.return_id=predecessor
    left join erp.sale_stock_allocations na on na.id=ni.sale_stock_allocation_id
    left join erp.sale_stock_allocations oa on oa.id=oi.sale_stock_allocation_id
    where ni.id is null or oi.id is null or(ni.product_id,ni.lot_id,ni.location_id,ni.quality_grade,ni.qty_pcs,ni.refund_amount)
      is distinct from(oi.product_id,oi.lot_id,oi.location_id,oi.quality_grade,oi.qty_pcs,oi.refund_amount)
     or not exists(select 1 from cp7_note.item_lineage il where il.correction_id=revision.id
      and il.previous_item_id=oa.sale_item_id and il.replacement_item_id=na.sale_item_id))then
    raise exception 'OW04_MEMBER_NOTE_ITEM_LINEAGE_INVALID';end if;
   perform ow04_source_proposal.require_restatement_v1(j.id,'NOTE')from erp.journal_entries j
    where j.source_type='SALES_RETURN'and j.source_id=predecessor and j.reversal_of_id is null;
  end if;
 else raise exception 'OW04_MEMBER_KIND_INVALID';end if;
 -- Every member follows one persisted, cycle-free chain to this family's
 -- original. The same old header cannot be claimed by two replay branches.
 if exists(select 1 from jsonb_array_elements(members)x where x->>'member_kind'<>'ORIGINAL'
  group by x->'actual_lineage_snapshot'->>'predecessor_return_id'having count(*)<>1)then
  raise exception 'OW04_MEMBER_RETURN_LINEAGE_FORK';end if;
 cursor:=p_return;seen:='{}';
 loop
  if cursor=any(seen)then raise exception 'OW04_MEMBER_RETURN_LINEAGE_CYCLE';end if;seen:=seen||cursor;
  select value into cursor_row from jsonb_array_elements(members)where(value->>'return_id')::uuid=cursor;
  if cursor_row is null then raise exception 'OW04_MEMBER_RETURN_LINEAGE_GAP';end if;
  if cursor_row->>'member_kind'='ORIGINAL'then
   if cursor is distinct from(registration->>'first_return_id')::uuid then raise exception 'OW04_MEMBER_MULTIPLE_ORIGINALS';end if;exit;
  end if;
  cursor:=(cursor_row->'actual_lineage_snapshot'->>'predecessor_return_id')::uuid;
  if cursor is null then raise exception 'OW04_MEMBER_RETURN_LINEAGE_GAP';end if;
 end loop;
 source_family:=ow04_source_proposal.family_read_v1(r.sale_id);
 select x.ordinal into strict sale_position from jsonb_array_elements_text(source_family->'sale_ids')with ordinality as x(value,ordinal)
  where value::uuid=r.sale_id;
 select array_agg(value::uuid order by position)into causal_sales from
  jsonb_array_elements_text(source_family->'sale_ids')with ordinality as x(value,position)where position<=sale_position;
 select max(j.transaction_date)into causal_floor from erp.journal_entries j where j.reversal_of_id is null
  and(j.source_type='SALE'and j.source_id=any(causal_sales)or j.source_type='SALES_RETURN'and j.source_id=any(seen));
 if fact->>'financial_state'='JOURNAL'then
  select transaction_date into strict source_book from erp.journal_entries where id=(fact->>'source_journal_id')::uuid;
  if causal_floor is null or source_book<causal_floor then raise exception 'OW04_MEMBER_RETURN_PRECEDES_CAUSAL_BOOK_FLOOR';end if;
 end if;
 expected:=jsonb_build_object('contract_version','ow04.actual-return-family-member.v1','family_id',family_id,
  'family_root_sale_id',root,'return_id',p_return,'sale_id',r.sale_id,'member_kind',member_kind,
  'predecessor_return_id',predecessor,'native_lineage_id',lineage_id,'return_item_lineage',item_lineage,
  'financial_state',fact->'financial_state','source_journal_id',fact->'source_journal_id',
  'financial_source_sha256',fact->'financial_source_sha256','no_journal_proof',fact->'no_journal_proof');
 if proof is distinct from expected or member->>'source_sha256'is distinct from ow04_source_proposal.sha(expected)
  or member->>'financial_state'is distinct from fact->>'financial_state'
  or member->'source_journal_id'is distinct from fact->'source_journal_id'
  or(member->>'financial_state'='NO_JOURNAL'and member->'financial_source_proof'is distinct from fact->'no_journal_proof')then
  raise exception using message='OW04_MEMBER_IMMUTABLE_SOURCE_BINDING_CHANGED',detail=jsonb_build_object(
   'snapshot_matches',proof is not distinct from expected,
   'snapshot_digest_matches',member->>'source_sha256'is not distinct from ow04_source_proposal.sha(expected),
   'financial_state_matches',member->>'financial_state'is not distinct from fact->>'financial_state',
   'journal_matches',member->'source_journal_id'is not distinct from fact->'source_journal_id',
   'no_journal_proof_matches',member->'financial_source_proof'is not distinct from fact->'no_journal_proof')::text;end if;
 return jsonb_build_object('contract_version','ow04.verified-return-member.v1','family_id',family_id,
  'family_root_sale_id',root,'family_ordinal',ordinal::text,'return_id',p_return,'sale_id',r.sale_id,
  'member_kind',member_kind,'predecessor_return_id',predecessor,'native_lineage_id',lineage_id,
  'financial_state',fact->'financial_state','source_journal_id',fact->'source_journal_id',
  'financial_source_sha256',fact->'financial_source_sha256','member_sha256',member->'source_sha256',
  'registration_sha256',registration->'source_sha256','causal_book_floor',causal_floor);
end $$;

create or replace function cp7_credit.assert_financial_materialization_provenance(p_actual jsonb)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare marker_id uuid;f cp7_credit.financial_materializations;m cp7_credit.initial_return_materializations;o cp7_credit.initial_refund_operations;
begin
 perform cp7_credit.assert_native_empty_provenance_v1(p_actual);
 p_actual:=cp7_credit.without_native_empty_markers_v1(p_actual);
 for marker_id in select value::uuid from jsonb_array_elements_text(p_actual->'materialization_ids')loop
  select fm.*into strict f from cp7_credit.financial_materializations fm where fm.id=marker_id;
  select *into m from cp7_credit.initial_return_materializations where materialization_id=f.id;
  if m.operation_id is not null then
   if(f.root_sale_id,f.actor,f.request_id,f.request_ordinal,f.payload_sha256,f.source_plan_sha256)is distinct from
    (m.source_sale_id,m.actor,m.request_id,1,m.payload_sha256,m.projection_sha256)
    or f.owning_action<>(case when m.origin='ORDINARY'then'RETURN'else'RETURN_SETTLEMENT'end)
    or m.projection_sha256 is distinct from ow04_source_proposal.sha(m.projection)
    or m.projection_actual_proof_sha256 is distinct from ow04_source_proposal.sha(m.projection_actual_proof)
    or m.prior_causal->>'proof_sha256'is distinct from ow04_source_proposal.sha(m.prior_causal_manifest)
    or not exists(select 1 from cp7_credit.return_families rf where rf.id=m.family_id and rf.first_return_id=m.source_return_id
     and rf.family_ordinal=m.family_ordinal and rf.actor=m.actor and rf.request_id=m.request_id)then
    raise exception 'CP7_CREDIT_INITIAL_PROVENANCE_CHANGED';end if;
  elsif exists(select 1 from cp7_credit.source_operation_materializations_v1 where financial_marker_id=f.id)then
   perform cp7_credit.assert_source_materialization_v1((select operation_id from cp7_credit.source_operation_materializations_v1 where financial_marker_id=f.id));
  else
   select *into strict o from cp7_credit.initial_refund_operations where id=f.id;
   select *into strict m from cp7_credit.initial_return_materializations where refund_operation_id=o.id;
   if(f.root_sale_id,f.actor,f.request_id,f.request_ordinal,f.owning_action,f.payload_sha256,f.source_plan_sha256)is distinct from
    (m.source_sale_id,m.actor,m.request_id,o.materialization_ordinal,'RETURN_SETTLEMENT',m.payload_sha256,m.projection_sha256)
    or not exists(select 1 from cp7_credit.consumption_events ce where ce.id=o.id and ce.cohort_id=m.cohort_id)
    or jsonb_array_length(f.actual_objects)<>1 or f.actual_objects->0->>'object_kind'<>'CONSUMPTION'
    or f.actual_objects->0->>'object_id'<>o.id::text then raise exception 'CP7_CREDIT_REFUND_PROVENANCE_CHANGED';end if;
  end if;
 end loop;
end $$;

create or replace function cp7_credit.enforce_initial_return_closure_v1()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
declare operation uuid;source_operation uuid;row jsonb:=to_jsonb(new);family uuid;plan uuid;
begin
 operation:=cp7_credit.native_empty_closure_id_v1(tg_table_name,to_jsonb(new));
 if operation is not null then perform cp7_credit.assert_native_empty_closed_v1(operation);return null;end if;
 if tg_table_name in('financial_materializations','financial_materialization_objects')then
  select operation_id into source_operation from cp7_credit.source_operation_materializations_v1
   where financial_marker_id=(case when tg_table_name='financial_materializations'then row->>'id'else row->>'materialization_id'end)::uuid;
  if source_operation is not null then perform cp7_credit.assert_source_operation_closed_v1(source_operation);return null;end if;
 end if;
 if tg_table_name in('initial_return_materializations','initial_return_completions')then operation:=(row->>'operation_id')::uuid;
 elsif tg_table_name='initial_refund_operations'then select operation_id into operation from cp7_credit.initial_return_materializations where refund_operation_id=(row->>'id')::uuid;
 elsif tg_table_name='financial_materializations'then select operation_id into operation from cp7_credit.initial_return_materializations where materialization_id=(row->>'id')::uuid or refund_operation_id=(row->>'id')::uuid;
 elsif tg_table_name='financial_materialization_objects'then select operation_id into operation from cp7_credit.initial_return_materializations where materialization_id=(row->>'materialization_id')::uuid or refund_operation_id=(row->>'materialization_id')::uuid;
 else
  case tg_table_name
   when'return_families'then family:=(row->>'id')::uuid;
   when'return_family_members'then family:=(row->>'family_id')::uuid;
   when'cohorts'then family:=(row->>'family_id')::uuid;
   when'recognition_plans'then plan:=(row->>'id')::uuid;
   when'plan_support_events'then plan:=(row->>'plan_id')::uuid;
   when'recognition_components'then plan:=(row->>'plan_id')::uuid;
   when'component_parts'then select plan_id into plan from cp7_credit.recognition_components where id=(row->>'component_id')::uuid;
   when'component_journals'then select cc.plan_id into plan from cp7_credit.component_parts pp join cp7_credit.recognition_components cc on cc.id=pp.component_id where pp.id=(row->>'part_id')::uuid;
   when'consumption_events'then select family_id into family from cp7_credit.cohorts where id=(row->>'cohort_id')::uuid;
   when'plan_dependencies'then plan:=(row->>'plan_id')::uuid;
   else raise exception 'CP7_CREDIT_CLOSURE_TABLE_UNRECOGNIZED';
  end case;
  select operation_id into source_operation from cp7_credit.source_operation_plans_v1 where plan_id=plan;
  if source_operation is not null then perform cp7_credit.assert_source_operation_closed_v1(source_operation);return null;end if;
  select operation_id into operation from cp7_credit.initial_return_materializations where family_id=family or plan_id=plan;
 end if;
 if operation is null then raise exception 'CP7_CREDIT_UNOWNED_IMMUTABLE_FACT';end if;
 perform cp7_credit.assert_initial_return_closed_v1(operation);return null;
end $$;

create or replace function cp7_credit.native_source_enter(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare sale uuid;a jsonb;families boolean;finished boolean:=false;
begin
 if cp7_credit.native_empty_is_direct_v1()then perform cp7_credit.native_empty_source_enter_v1(p_action,p_source);return;end if;
 if p_action in('PAYMENT','PAYMENT_REVERSE')then select sale_id,status='REVERSED'and p_action='PAYMENT_REVERSE'into strict sale,finished from erp.sales_payments where id=p_source;
 elsif p_action='RETURN_REVERSE'then select sale_id,status='REVERSED'into strict sale,finished from erp.sales_returns where id=p_source;
 elsif p_action='SALE_REVERSE'then select id,status='REVERSED'into strict sale,finished from erp.sales_headers where id=p_source;
 else raise exception 'CP7_CREDIT_SOURCE_ACTION_UNIMPLEMENTED';end if;
 if cp7_credit.source_operation_owns_v1(p_action,p_source)then
  perform cp7_credit.source_operation_native_enter_v1(p_action,p_source);return;
 end if;
 if not cp7_credit.has_ow04_participation_v1(sale)then return;end if;
 -- Original Native require_internal/owner checks still surround this callback.
 a:=cp7_sales.command_access(p_action);
 select exists(select 1 from cp7_credit.return_families where family_root_sale_id=sale)into families;
 if exists(select 1 from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id where f.family_root_sale_id=sale)
  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=sale)then
  raise exception 'CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION';end if;
 if finished then return;end if; -- Native early replay has no completion hook.
 insert into cp7_credit.source_mutation_scope values(pg_backend_pid(),txid_current(),auth.uid(),p_action,p_source,sale,a,families);
 if families then perform cp7_credit.assert_simple_native_base_v1(sale);perform cp7_credit.assert_zero_excess_v1(cp7_credit.initial_base_events_v1(sale));end if;
 if cp7_sales.command_access(p_action)is distinct from a then raise exception using errcode='42501',message='CP7_CREDIT_SOURCE_ACCESS_CHANGED';end if;
end $$;

create or replace function cp7_credit.native_source_complete(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.source_mutation_scope;sale uuid;
begin
 if exists(select 1 from cp7_credit.native_empty_source_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or cp7_credit.native_empty_is_direct_v1()then perform cp7_credit.native_empty_source_complete_v1(p_action,p_source);return;end if;
 if cp7_credit.source_operation_owns_v1(p_action,p_source)then
  perform cp7_credit.source_operation_native_complete_v1(p_action,p_source);return;
 end if;
 select *into s from cp7_credit.source_mutation_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 if s.source_id is null then
  if p_action in('PAYMENT','PAYMENT_REVERSE')then select sale_id into strict sale from erp.sales_payments where id=p_source;
  elsif p_action='RETURN_REVERSE'then select sale_id into strict sale from erp.sales_returns where id=p_source;
  elsif p_action='SALE_REVERSE'then sale:=p_source;
  else raise exception 'CP7_CREDIT_SOURCE_ACTION_UNIMPLEMENTED';end if;
  if not cp7_credit.has_ow04_participation_v1(sale)then return;end if;
  raise exception 'CP7_CREDIT_PARTICIPATING_SOURCE_SCOPE_REQUIRED';
 end if;
 if(s.action,s.source_id)is distinct from(p_action,p_source)then raise exception 'CP7_CREDIT_SOURCE_SCOPE_CHANGED';end if;
 if cp7_sales.command_access(p_action)is distinct from s.authority_snapshot then raise exception using errcode='42501',message='CP7_CREDIT_SOURCE_ACCESS_CHANGED';end if;
 if s.had_families then
  perform cp7_credit.assert_simple_native_base_v1(s.sale_id);
  perform cp7_credit.assert_zero_excess_v1(cp7_credit.initial_base_events_v1(s.sale_id));
 end if;
 delete from cp7_credit.source_mutation_scope where backend_pid=s.backend_pid and transaction_id=s.transaction_id;
end $$;
