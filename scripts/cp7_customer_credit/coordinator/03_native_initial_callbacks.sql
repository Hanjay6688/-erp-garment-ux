-- OUTSIDE PRODUCT. Dependencies are concrete proposals, not passing stubs.
do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;

create function cp7_credit.initial_choice_v1(p jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('mode',p->'mode','credit_account_id',p->'credit_account_id','cash_account_id',p->'cash_account_id',
  'refund_physical_at',p->'refund_physical_at','reference',p->'reference')
$$;

create function cp7_credit.initial_line_semantics_v1(p jsonb)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(v order by v::text collate"C"),'[]')from(select jsonb_build_object(
  'account_id',coalesce((x->>'account_id')::uuid,cp7_credit.account_by_mapping_v1(x->>'mapping_key')),
  'customer_id',x->'customer_id','vendor_id',x->'vendor_id','contractor_id',x->'contractor_id','po_id',x->'po_id','product_id',x->'product_id',
  'debit',cp7_credit.cent_text(coalesce((x->>'debit')::numeric,0)),'credit',cp7_credit.cent_text(coalesce((x->>'credit')::numeric,0)))v
  from jsonb_array_elements(p)x)s
$$;

create function cp7_credit.assert_initial_work_v1(p_return uuid,p_require_native boolean default true)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;s cp7_credit.return_command_scope;a jsonb;r erp.sales_returns;
begin
 if current_setting('transaction_isolation')<>'read committed'or auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_CREDIT_CURRENT_ACTOR_REQUIRED';end if;
 select *into strict w from cp7_credit.initial_return_work where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 if w.return_id is distinct from p_return or w.phase not in('ENTERED','MATERIALIZED','COMPLETE')then raise exception 'CP7_CREDIT_OWN_RETURN_BINDING_REQUIRED';end if;
 a:=cp7_credit.return_command_access(w.settlement->>'mode');
 if a is distinct from w.authority_snapshot then raise exception using errcode='42501',message='CP7_CREDIT_CURRENT_AUTHORITY_CHANGED';end if;
 if p_require_native and not exists(select 1 from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()
  and c.actor=w.actor and c.sale_id=w.source_sale_id and c.action='RETURN')then raise exception 'CP7_CREDIT_EXISTING_RETURN_CONTEXT_REQUIRED';end if;
 if p_require_native then perform cp7_credit.assert_only_own_return_native_context(w.source_sale_id);end if;
 if not exists(select 1 from cp7_sales.requests q where q.actor=w.actor and q.request_id=w.request_id and q.action='RETURN'
  and q.payload=w.legacy_payload and q.expected_version=w.expected_version
  and(q.response is null or not p_require_native and q.response->>'return_id'=p_return::text))then
  raise exception 'CP7_CREDIT_OWN_PENDING_INNER_REQUEST_REQUIRED';end if;
 if w.origin='REVIEWED_SETTLEMENT'then
  select *into strict s from cp7_credit.return_command_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id and actor=w.actor;
  if(s.request_id,s.return_id,s.source_sale_id,s.payload_sha256,s.quote_sha256,s.projection_sha256,s.source_lock_sha256)is distinct from
   (w.request_id,w.return_id,w.source_sale_id,w.payload_sha256,w.quote_sha256,w.projection_sha256,w.source_lock_sha256)
   or s.stage not in('NATIVE','COMPLETE')or not exists(select 1 from cp7_credit.return_requests q where q.actor=w.actor and q.request_id=w.request_id
    and cp7_credit.pg_jsonb_sha256(q.payload)=w.payload_sha256 and q.response is null)then raise exception 'CP7_CREDIT_OWN_OUTER_BINDING_REQUIRED';end if;
 end if;
 select *into strict r from erp.sales_returns where id=p_return;
 if r.sale_id<>w.source_sale_id or r.customer_id<>(w.projection->>'customer_id')::uuid
  or r.physical_at is distinct from(w.legacy_payload->>'physical_at')::timestamptz
  or r.return_number is distinct from btrim(w.legacy_payload->>'return_number')or r.notes is distinct from w.legacy_payload->>'notes'then
  raise exception 'CP7_CREDIT_ACTUAL_RETURN_DOCUMENT_MISMATCH';end if;
 if cp7_credit.initial_preserved_source_v1(w.source_sale_id,r.id)is distinct from w.source_snapshot->'preserved_source'then
  raise exception 'CP7_CREDIT_ORIGINAL_SOURCE_CHANGED';end if;
 if(select to_jsonb(p)from erp.accounting_period_control p where singleton_id=1)is distinct from w.period_snapshot then
  raise exception 'CP7_CREDIT_PERIOD_CHANGED';end if;
 if w.credit_account_snapshot is not null and(select to_jsonb(c)from erp.chart_accounts c where id=(w.settlement->>'credit_account_id')::uuid)
  is distinct from w.credit_account_snapshot->'account'then raise exception 'CP7_CREDIT_ACCOUNT_MASTER_CHANGED';end if;
 if w.cash_account_snapshot is not null and cp7_credit.cash_account_facts_v1((w.settlement->>'cash_account_id')::uuid)is distinct from w.cash_account_snapshot then
  raise exception 'CP7_CREDIT_CASH_MASTER_CHANGED';end if;
end $$;

create function cp7_credit.assert_return_owner_context(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$begin perform cp7_credit.assert_initial_work_v1(p_return,true);end $$;

create function cp7_credit.seal_return_settlement(p_request uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.return_command_scope;b jsonb;op uuid:=gen_random_uuid();
begin
 select *into strict s from cp7_credit.return_command_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and request_id=p_request;
 if s.stage<>'CLAIMED'then raise exception 'CP7_CREDIT_OUTER_CLAIM_REQUIRED';end if;
 perform cp7_credit.assert_pending_return_outer(p_request,s.legacy_payload,s.expected_version);
 b:=cp7_credit.build_initial_return_v1(s.legacy_payload,s.expected_version,cp7_credit.initial_choice_v1((select payload->'settlement'
  from cp7_credit.return_requests where actor=s.actor and request_id=s.request_id)));
 if b->'quote'->'readiness'->>'state'<>'READY'or b->'quote'->'binding'->>'quote_sha256'is distinct from s.quote_sha256
  or b->'authority'is distinct from s.current_authority then raise exception 'CP7_CREDIT_COMPLETE_QUOTE_CHANGED';end if;
 insert into cp7_credit.initial_return_work(operation_id,backend_pid,transaction_id,actor,request_id,source_sale_id,origin,phase,expected_version,
  legacy_payload,settlement,payload_sha256,quote_sha256,authority_snapshot,source_snapshot,source_lock_sha256,projection,projection_sha256,
  projected_kernel,prior_causal,prior_causal_manifest,period_snapshot,credit_account_snapshot,cash_account_snapshot)
 values(op,s.backend_pid,s.transaction_id,s.actor,s.request_id,s.source_sale_id,'REVIEWED_SETTLEMENT','SEALED',s.expected_version,s.legacy_payload,
  (select payload->'settlement'from cp7_credit.return_requests where actor=s.actor and request_id=s.request_id),s.payload_sha256,s.quote_sha256,
  s.current_authority,b,ow04_source_proposal.sha(b->'source'->'source_lock_ids'),b->'projection',b->'quote'->'binding'->>'projection_sha256',
  b->'projected_kernel',b->'prior_causal',b->'prior_causal_manifest',b->'period_snapshot',b->'credit_account_snapshot',b->'cash_account_snapshot');
 update cp7_credit.return_command_scope set stage='LOCKED',source_lock_sha256=ow04_source_proposal.sha(b->'source'->'source_lock_ids'),
  projection_sha256=b->'quote'->'binding'->>'projection_sha256',credit_account_snapshot=b->'credit_account_snapshot',cash_account_snapshot=b->'cash_account_snapshot'
  where backend_pid=s.backend_pid and transaction_id=s.transaction_id;
end $$;

create function cp7_credit.assert_sealed_return_source(p_request uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;
begin
 select *into strict w from cp7_credit.initial_return_work where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and request_id=p_request;
 if w.phase<>'SEALED'or w.return_id is not null or cp7_credit.initial_preserved_source_v1(w.source_sale_id)is distinct from w.source_snapshot->'preserved_source'
  or cp7_credit.return_command_access(w.settlement->>'mode')is distinct from w.authority_snapshot
  or(select to_jsonb(p)from erp.accounting_period_control p where singleton_id=1)is distinct from w.period_snapshot then
  raise exception 'CP7_CREDIT_SEALED_SOURCE_CHANGED';end if;
end $$;

create function cp7_credit.native_return_enter(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare r erp.sales_returns;w cp7_credit.initial_return_work;s cp7_credit.return_command_scope;q cp7_sales.requests;b jsonb;ids uuid[];op uuid;actual_items jsonb;expected_items jsonb;
begin
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

create function cp7_credit.native_return_guard(p_return uuid,p_refund numeric,p_net_after numeric,p_raw_paid numeric)returns numeric
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;v numeric;
begin
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

-- Replaces ONLY the existing proposal's RETURN branch. COMPONENT retains its
-- exact UUID + full-plan validator. Native's copied body still owns period,
-- balanced cent lines, source uniqueness, cash trigger and daily balances.
create or replace function cp7_credit.bound_book_date(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns date
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.posting_scope;w cp7_credit.initial_return_work;lawful date;expected date;
begin
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

create or replace function cp7_credit.post_return_journal(p_type text,p_return uuid,p_economic date,p_description text,p_lines jsonb)returns uuid
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.initial_return_work;j uuid;
begin
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
