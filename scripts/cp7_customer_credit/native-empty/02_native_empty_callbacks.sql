-- OUTSIDE PRODUCT. Only exact overlays in 03 connect these callbacks to the
-- already source-captured Native bodies. No Native authority branch is added.
do $not_an_installer$begin
 raise exception 'OW04_NATIVE_EMPTY_REQUIRES_ATOMIC_NATIVE_COMPOSITION';
end $not_an_installer$;

create function cp7_credit.native_empty_is_direct_v1()returns boolean
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select not exists(select 1 from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  and not exists(select 1 from cp7_credit.initial_return_work where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  and not exists(select 1 from cp7_credit.return_command_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  and not exists(select 1 from cp7_credit.return_native_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  and not exists(select 1 from cp7_credit.execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())
$$;
create function cp7_credit.native_empty_owns_return_v1(p_return uuid)returns boolean
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select exists(select 1 from cp7_credit.native_empty_work where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and source_return_id=p_return)
$$;
create function cp7_credit.native_empty_post_scope_v1()returns boolean
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select exists(select 1 from cp7_credit.native_empty_work where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and phase='GUARDED'and posting_lines is not null)
$$;

-- No new financial source policy: this is the current bounded implementation
-- of an EMPTY root only. A retained credit, U or correction still refuses.
create function cp7_credit.assert_native_empty_supported_v1(p_sale uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare family jsonb;
begin
 family:=ow04_source_proposal.family_read_v1(p_sale);
 if family->>'root_sale_id'<>p_sale::text or family->>'current_leaf_id'<>p_sale::text
  or jsonb_array_length(family->'sale_ids')<>1
  or exists(select 1 from cp7_note.revisions where p_sale in(root_sale_id,previous_sale_id,replacement_sale_id))
  or exists(select 1 from cp7_sales_return_correction.links where sale_id=p_sale)
  or exists(select 1 from cp7_payment_correction.links l join erp.sales_payments p on p.id in(l.original_id,l.replacement_id)where p.sale_id=p_sale)
  or exists(select 1 from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=p_sale)
  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)then
  raise exception 'CP7_NATIVE_EMPTY_RECOGNIZED_OR_CORRECTED_SOURCE_UNIMPLEMENTED';end if;
 -- The shared core alone owns root-aware/no-orphan admission; no early P/0.
 if erp._cp7_current_credit_adjustment(p_sale)<>0 then raise exception 'CP7_NATIVE_EMPTY_FINANCIAL_SOURCE_NOT_EMPTY';end if;
end $$;

create function cp7_credit.native_empty_enter_v1(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare r erp.sales_returns;h erp.sales_headers;src jsonb;before_events jsonb;draft jsonb;prior jsonb;added jsonb:='[]';k jsonb;
 principal jsonb;period jsonb;amount numeric;economic date;book date;op uuid:=gen_random_uuid();hpp jsonb;hpp_input jsonb;
begin
 -- This is reentrant with Native's identical FG lock, before all source rows.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform erp.require_internal();
 if not cp7_credit.native_empty_is_direct_v1()then raise exception 'CP7_NATIVE_EMPTY_DIRECT_ROUTE_REQUIRED';end if;
 perform cp7_credit.assert_no_ambient_native_context();
 if exists(select 1 from cp7_credit.native_empty_work where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.native_empty_source_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'CP7_NATIVE_EMPTY_NESTED_OPERATION';end if;
 select *into strict r from erp.sales_returns where id=p_return;
 if r.status<>'DRAFT'then raise exception 'Sales return must be DRAFT';end if;
 if exists(select 1 from cp7_credit.return_family_members where return_id=p_return)
  or exists(select 1 from cp7_credit.native_empty_operations where source_return_id=p_return)
  or exists(select 1 from erp.journal_entries where source_type='SALES_RETURN'and source_id=p_return)
  or exists(select 1 from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id
   where m.source_type='SALES_RETURN_ITEM'and i.return_id=p_return)then raise exception 'CP7_NATIVE_EMPTY_NOT_FIRST_POST';end if;
 src:=ow04_source_proposal.locked_source_family(r.sale_id);
 if src->>'source_status'<>'BASE_COLLECTED'then raise exception 'CP7_NATIVE_EMPTY_LEGACY_ORDER_OR_SOURCE_UNQUALIFIED'using detail=(src->'blockers')::text;end if;
 perform cp7_credit.assert_native_empty_supported_v1(r.sale_id);
 perform cp7_credit.assert_simple_native_base_v1(r.sale_id);
 select *into strict h from erp.sales_headers where id=r.sale_id;
 if h.status not in('POSTED','PARTIAL_PAID','PAID')or h.customer_id<>r.customer_id then
  raise exception 'CP7_NATIVE_EMPTY_ACTIVE_SOURCE_REQUIRED';end if;
 before_events:=cp7_credit.initial_base_events_v1(r.sale_id);
 if cp7_credit.initial_event_semantics_v1(before_events)is distinct from cp7_credit.initial_event_semantics_v1(src->'events')then
  raise exception 'CP7_NATIVE_EMPTY_SOURCE_VECTOR_INCOMPLETE';end if;
 perform cp7_credit.assert_zero_excess_v1(before_events);
 draft:=cp7_credit.native_empty_draft_v1(p_return);
 -- The same source-derived full-vector calculator owns both return routes.
 -- Lock every sibling lot/version/cache and inventory destination BEFORE
 -- Native's period/CASH admission. No later callback discovers a new lock.
 select jsonb_build_object('sale_id',r.sale_id,'items',jsonb_agg(jsonb_build_object(
  'allocation_id',di->'sale_stock_allocation_id','location_id',di->'location_id',
  'qty_pcs',di->'qty_pcs','quality_grade',di->'quality_grade','refund_amount',di->'refund_amount')order by di->>'id'))
 into hpp_input from jsonb_array_elements(draft->'items')di;
 hpp:=cp7_credit.initial_hpp_projection_v1(hpp_input);
 perform 1 from erp.accounting_account_mappings where mapping_key in('FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME')order by mapping_key for share;
 perform 1 from erp.chart_accounts where id in(select(mv->>'account_id')::uuid from jsonb_array_elements(hpp#>'{account_facts,mappings}')mv)order by id for share;
 if cp7_credit.initial_hpp_account_facts_v1()is distinct from hpp->'account_facts'then
  raise exception 'CP7_NATIVE_EMPTY_HPP_ACCOUNT_CHANGED';end if;
 select sum(refund_amount)into amount from erp.sales_return_items where return_id=p_return;
 if amount is null or amount<0 then raise exception 'CP7_NATIVE_EMPTY_DRAFT_AMOUNT';end if;
 perform cp7_credit.cent_text(amount::cp7_credit.cent_amount);
 prior:=cp7_credit.native_empty_prior_v1(r.sale_id);
 select to_jsonb(p)into strict period from erp.accounting_period_control p where singleton_id=1;
 economic:=(r.physical_at at time zone'Asia/Jakarta')::date;
 book:=greatest(erp.resolve_accounting_transaction_date(economic),(prior->>'causal_book_floor')::date);
 if book is null or book<economic or book>(statement_timestamp()at time zone'Asia/Jakarta')::date then
  raise exception 'CP7_NATIVE_EMPTY_PROJECTED_BOOK_INVALID';end if;
 if amount<>0 then
  added:=jsonb_build_array(jsonb_build_object('id','projected-native-return:'||r.id::text,'kind','NET',
   'amount',cp7_credit.cent_text(-amount),'economic_date',economic::text,'transaction_date',book::text,
   'source_sha256',ow04_source_proposal.sha(draft)));
 end if;
 k:=ow04_pure_kernel.recognition_plan_v1(before_events,added);
 principal:=cp7_credit.native_empty_principal_v1();perform cp7_credit.assert_native_empty_principal_v1(principal);
 insert into cp7_credit.native_empty_work(operation_id,backend_pid,transaction_id,source_return_id,source_sale_id,principal,principal_sha256,
  source_snapshot,preserved_source,before_events,draft_manifest,prior_causal,period_snapshot,projected_events,projected_kernel,hpp_projection,phase)
 values(op,pg_backend_pid(),txid_current(),p_return,r.sale_id,principal,ow04_source_proposal.sha(principal),src,
  cp7_credit.initial_preserved_source_v1(r.sale_id,r.id),before_events,draft,prior,period,added,k,hpp,'ENTERED');
 -- The original Native paid guard is deliberately still reached for P>net.
 -- A nonempty K0 temporal target is rejected by guard_v1 instead of minting I.
 perform erp.require_internal();
end $$;

-- Called after source/master locks have already been acquired. Reentry after
-- period/CASH obtains NO earlier-order lock and discovers no new source set.
create function cp7_credit.assert_native_empty_work_v1(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.native_empty_work;r erp.sales_returns;
begin
 select *into strict w from cp7_credit.native_empty_work where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and source_return_id=p_return;
 if not cp7_credit.native_empty_is_direct_v1()or w.principal is distinct from cp7_credit.native_empty_principal_v1()
  or w.principal_sha256 is distinct from ow04_source_proposal.sha(w.principal)then
  raise exception 'CP7_NATIVE_EMPTY_CURRENT_OPERATION_CHANGED';end if;
 perform cp7_credit.assert_no_ambient_native_context();
 select *into strict r from erp.sales_returns where id=p_return;
 if r.sale_id<>w.source_sale_id or cp7_credit.native_empty_draft_v1(p_return)is distinct from w.draft_manifest
  or cp7_credit.initial_preserved_source_v1(w.source_sale_id,p_return)is distinct from w.preserved_source
  or cp7_credit.initial_base_events_v1(w.source_sale_id,p_return)is distinct from w.before_events
  or cp7_credit.native_empty_prior_v1(w.source_sale_id)is distinct from w.prior_causal
  or(select to_jsonb(p)from erp.accounting_period_control p where singleton_id=1)is distinct from w.period_snapshot then
  raise exception 'CP7_NATIVE_EMPTY_SOURCE_OR_PERIOD_CHANGED';end if;
 if jsonb_typeof(w.hpp_projection->'groups')is distinct from'array'
  or jsonb_typeof(w.hpp_projection->'locked_lot_ids')is distinct from'array'
  or cp7_credit.initial_hpp_account_facts_v1()is distinct from w.hpp_projection->'account_facts'
  or(select coalesce(jsonb_agg(hv.id order by hv.id),'[]')from erp.hpp_versions hv
   where(w.hpp_projection->'locked_lot_ids')?hv.lot_id::text)is distinct from w.hpp_projection->'locked_hpp_version_ids'
  or exists(select 1 from jsonb_array_elements(w.hpp_projection->'groups')hg
   where(select coalesce(jsonb_agg(fl.id order by fl.id),'[]')from erp.fg_lots fl where
    ((hg->>'po_id')::uuid is not null and fl.po_id=(hg->>'po_id')::uuid and fl.lot_origin in('PRODUCTION','CONVERSION'))
    or((hg->>'po_id')::uuid is null and fl.po_id is null and fl.product_id=(hg->>'product_id')::uuid and fl.lot_origin<>'VOIDED_PRODUCTION'))
   is distinct from(select coalesce(jsonb_agg((hl->>'lot_id')::uuid order by(hl->>'lot_id')::uuid),'[]')
    from jsonb_array_elements(hg#>'{before_profile,lots}')hl))then
  raise exception 'CP7_NATIVE_EMPTY_HPP_LOCK_MANIFEST_CHANGED';end if;
end $$;

create function cp7_credit.native_empty_guard_v1(p_return uuid,p_refund numeric,p_net_after numeric,p_raw_paid numeric)returns numeric
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.native_empty_work;amount numeric;net numeric;paid numeric;
begin
 perform cp7_credit.assert_native_empty_work_v1(p_return);
 select *into strict w from cp7_credit.native_empty_work where source_return_id=p_return;
 select sum(refund_amount)into amount from erp.sales_return_items where return_id=p_return;
 net:=(select coalesce(sum(line_total),0)from erp.sales_items where sale_id=w.source_sale_id)
  -(select coalesce(sum(i.refund_amount),0)from erp.sales_returns r join erp.sales_return_items i on i.return_id=r.id
    where r.sale_id=w.source_sale_id and r.status='POSTED'and r.id<>p_return)-amount;
 select coalesce(sum(p.amount),0)into paid from erp.sales_payments p where p.sale_id=w.source_sale_id and p.status='POSTED';
 if w.phase<>'ENTERED'or(p_refund,p_net_after,p_raw_paid)is distinct from(amount,net,paid)then
  raise exception 'CP7_NATIVE_EMPTY_NATIVE_TOTALS_CHANGED';end if;
 if p_raw_paid<=p_net_after and(w.projected_kernel->>'has_recognition_effect')::boolean then
  raise exception 'CP7_NATIVE_EMPTY_EXPLICIT_RECOGNITION_REVIEW_REQUIRED';end if;
 update cp7_credit.native_empty_work set phase='GUARDED',guard_values=jsonb_build_object(
  'refund',cp7_credit.cent_text(p_refund),'net_after',cp7_credit.cent_text(p_net_after),'raw_paid',cp7_credit.cent_text(p_raw_paid))where operation_id=w.operation_id;
 return p_raw_paid; -- original Native if P>net exception remains unchanged
end $$;

-- Narrow branch of the existing hash-pinned Native copy. Only the exact
-- generated SALES_RETURN lines of this actual guarded return are authorized.
create function cp7_credit.assert_native_empty_bound_post_v1(p_type text,p_return uuid,p_economic date,p_lines jsonb)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.native_empty_work;r erp.sales_returns;
begin
 perform cp7_credit.assert_native_empty_work_v1(p_return);
 select *into strict w from cp7_credit.native_empty_work where source_return_id=p_return;
 select *into strict r from erp.sales_returns where id=p_return;
 if p_type<>'SALES_RETURN'or r.status<>'POSTED'or w.phase<>'GUARDED'
  or(w.projected_kernel->>'has_recognition_effect')::boolean or p_economic<>(r.physical_at at time zone'Asia/Jakarta')::date
  or w.posting_lines is null or w.posting_lines is distinct from p_lines
  or w.posting_lines_sha256 is distinct from cp7_credit.native_lines_sha256(p_lines)
  or exists(select 1 from erp.journal_entries where source_type='SALES_RETURN'and source_id=p_return)then
  raise exception 'CP7_NATIVE_EMPTY_PAIRED_SCOPE_REQUIRED';end if;
end $$;
create function cp7_credit.native_empty_bound_book_v1(p_type text,p_return uuid,p_economic date,p_lines jsonb)returns date
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.native_empty_work;lawful date;expected date;
begin
 perform cp7_credit.assert_native_empty_bound_post_v1(p_type,p_return,p_economic,p_lines);
 select *into strict w from cp7_credit.native_empty_work where source_return_id=p_return;
 lawful:=erp.resolve_accounting_transaction_date(p_economic);
 expected:=greatest(lawful,(w.prior_causal->>'causal_book_floor')::date);
 if lawful is null or expected is distinct from w.planned_book_date or expected<p_economic
  or expected>(statement_timestamp()at time zone'Asia/Jakarta')::date then raise exception 'CP7_NATIVE_EMPTY_BOOK_REPLAN_REQUIRED';end if;
 return expected;
end $$;
create function cp7_credit.native_empty_bound_audit_v1()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.native_empty_work;
begin
 select *into strict w from cp7_credit.native_empty_work where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and phase='GUARDED'and posting_lines is not null;
 perform cp7_credit.assert_native_empty_work_v1(w.source_return_id);
 return jsonb_build_object('book_date_basis','SOURCE_BOUND_NATIVE_EMPTY_RETURN','native_operation_id',w.operation_id,
  'source_sale_id',w.source_sale_id,'source_return_id',w.source_return_id,'lines_sha256_pg',w.posting_lines_sha256,
  'lawful_book_date',erp.resolve_accounting_transaction_date(((w.draft_manifest#>>'{document,physical_at}')::timestamptz at time zone'Asia/Jakarta')::date),
  'causal_book_floor',w.prior_causal->'causal_book_floor','causal_proof_sha256',w.prior_causal->'proof_sha256');
end $$;
create function cp7_credit.native_empty_post_return_journal_v1(p_type text,p_return uuid,p_economic date,p_description text,p_lines jsonb)returns uuid
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.native_empty_work;answer uuid;lawful date;
begin
 perform cp7_credit.assert_native_empty_work_v1(p_return);
 select *into strict w from cp7_credit.native_empty_work where source_return_id=p_return;
 if w.posting_lines is not null then raise exception 'CP7_NATIVE_EMPTY_NESTED_POST';end if;
 lawful:=erp.resolve_accounting_transaction_date(p_economic);
 if lawful is null then raise exception 'CP7_NATIVE_EMPTY_LAWFUL_BOOK_MISSING';end if;
 update cp7_credit.native_empty_work set posting_lines=p_lines,posting_lines_sha256=cp7_credit.native_lines_sha256(p_lines),
  planned_book_date=greatest(lawful,(w.prior_causal->>'causal_book_floor')::date)where operation_id=w.operation_id;
 perform cp7_credit.assert_native_empty_bound_post_v1(p_type,p_return,p_economic,p_lines);
 answer:=cp7_credit._post_journal_bound(p_type,p_return,p_economic,p_description,p_lines);
 update cp7_credit.native_empty_work set posting_lines=null,posting_lines_sha256=null where operation_id=w.operation_id;
 perform cp7_credit.assert_native_empty_work_v1(p_return);return answer;
end $$;

create function cp7_credit.native_empty_complete_v1(p_return uuid,p_refund numeric,p_net_after numeric)returns numeric
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.native_empty_work;fact jsonb;actual_events jsonb;k jsonb;assignment jsonb;member jsonb;objects jsonb;hpp_group jsonb;actual_target jsonb;
 family uuid:=gen_random_uuid();marker uuid:=gen_random_uuid();previous uuid;ordinal bigint;uid uuid;journal jsonb;reconciled jsonb;raw_paid numeric;
begin
 perform cp7_credit.assert_native_empty_work_v1(p_return);
 select *into strict w from cp7_credit.native_empty_work where source_return_id=p_return;
 if w.phase<>'GUARDED'or(w.guard_values->>'refund',w.guard_values->>'net_after')is distinct from
  (cp7_credit.cent_text(p_refund),cp7_credit.cent_text(p_net_after))or w.posting_lines is not null then
  raise exception 'CP7_NATIVE_EMPTY_COMPLETION_TOTALS_CHANGED';end if;
 for hpp_group in select value from jsonb_array_elements(w.hpp_projection->'groups')loop
  -- Native has posted the exact journal, but refreshes its PO baseline in
  -- the original tail AFTER this callback. Compare the actual target now;
  -- the complete target/book/cache assertions run in leave after that tail.
  if(hpp_group->>'po_id')::uuid is null then
   select to_jsonb(nt)into strict actual_target from erp.compute_non_po_product_hpp_targets_v2620f((hpp_group->>'product_id')::uuid)nt;
  else
   select to_jsonb(nt)into strict actual_target from erp.compute_po_hpp_gl_targets_v2620d((hpp_group->>'po_id')::uuid)nt;
  end if;
  if actual_target is distinct from hpp_group->'after_target'then raise exception 'CP7_NATIVE_EMPTY_ACTUAL_HPP_TARGET_CHANGED';end if;
 end loop;
 fact:=ow04_source_proposal.return_fact_v1(p_return);
 if fact->>'sale_id'<>w.source_sale_id::text or fact->>'family_root_sale_id'<>w.source_sale_id::text then
  raise exception 'CP7_NATIVE_EMPTY_ACTUAL_FAMILY_CHANGED';end if;
 actual_events:=cp7_credit.actual_own_return_events_v1(p_return);
 k:=ow04_pure_kernel.recognition_plan_v1(w.before_events,actual_events);
 if(k->>'has_recognition_effect')::boolean or k->>'net_current_k'<>'0.00'
  or k->'components'is distinct from w.projected_kernel->'components'then raise exception 'CP7_NATIVE_EMPTY_ACTUAL_TARGET_NOT_EMPTY';end if;
 perform cp7_credit.assert_zero_excess_v1(w.before_events||actual_events);
 if p_refund<>0 and cp7_credit.initial_event_semantics_v1(actual_events)is distinct from cp7_credit.initial_event_semantics_v1(w.projected_events)then
  raise exception 'CP7_NATIVE_EMPTY_PROJECTED_ACTUAL_MONETARY_PAIR';end if;
 if fact->>'financial_state'='JOURNAL'then
  journal:=cp7_credit.materialized_journal_payload((fact->>'source_journal_id')::uuid);
  if w.planned_book_date is null or(journal#>>'{journal,transaction_date}')::date is distinct from w.planned_book_date then
   raise exception 'CP7_NATIVE_EMPTY_ACTUAL_JOURNAL_PAIR';end if;
 elsif w.planned_book_date is not null or jsonb_array_length(actual_events)<>0 then
  raise exception 'CP7_NATIVE_EMPTY_NO_JOURNAL_PAIR_NOT_NULL';end if;
 select coalesce(max(family_ordinal),0)+1 into ordinal from cp7_credit.return_families where family_root_sale_id=w.source_sale_id;
 select id into previous from cp7_credit.return_families where family_root_sale_id=w.source_sale_id and family_ordinal=ordinal-1;
 if exists(select 1 from erp.sales_returns r where r.sale_id=w.source_sale_id and r.status<>'DRAFT'and r.id<>p_return
  and not exists(select 1 from cp7_credit.return_family_members m where m.return_id=r.id))then raise exception 'CP7_NATIVE_EMPTY_LEGACY_ORDER_UNQUALIFIED';end if;
 assignment:=jsonb_build_object('contract_version','ow04.native-empty-return-family-assignment.v1','origin','NATIVE_RETURN',
  'operation_id',w.operation_id,'family_id',family,'family_root_sale_id',w.source_sale_id,'family_ordinal',ordinal::text,
  'first_return_id',p_return,'previous_family_id',previous,'principal_sha256',w.principal_sha256,'source_sha256',ow04_source_proposal.sha(w.source_snapshot));
 uid:=(w.principal->>'auth_uid')::uuid;
 insert into cp7_credit.return_families(id,family_root_sale_id,family_ordinal,first_return_id,assignment_kind,assignment_proof,source_sha256,actor,request_id)
 values(family,w.source_sale_id,ordinal,p_return,'NEW_POST',assignment,ow04_source_proposal.sha(assignment),uid,null);
 member:=jsonb_build_object('contract_version','ow04.actual-return-family-member.v1','family_id',family,'family_root_sale_id',w.source_sale_id,
  'return_id',p_return,'sale_id',w.source_sale_id,'member_kind','ORIGINAL','predecessor_return_id',null,'native_lineage_id',null,
  'return_item_lineage','{}'::jsonb,'financial_state',fact->'financial_state','source_journal_id',fact->'source_journal_id',
  'financial_source_sha256',fact->'financial_source_sha256','no_journal_proof',fact->'no_journal_proof');
 insert into cp7_credit.return_family_members(family_id,return_id,member_kind,source_journal_id,source_sha256,actual_lineage_snapshot,actor,request_id,financial_state,financial_source_proof)
 values(family,p_return,'ORIGINAL',(fact->>'source_journal_id')::uuid,ow04_source_proposal.sha(member),member,uid,null,fact->>'financial_state',fact->'no_journal_proof');
 select jsonb_agg(x order by x->>'object_kind'collate"C",x->>'object_id'collate"C")into objects from(
  select cp7_credit.materialized_fact('FAMILY',f.id,to_jsonb(f))x from cp7_credit.return_families f where f.id=family
  union all select cp7_credit.materialized_fact('MEMBER',m.return_id,to_jsonb(m))from cp7_credit.return_family_members m where m.return_id=p_return)s;
 insert into cp7_credit.native_empty_operations(operation_id,source_return_id,source_sale_id,family_id,family_ordinal,backend_pid,transaction_id,
  principal,principal_sha256,draft_manifest,draft_sha256,source_snapshot,source_sha256,preserved_source,before_events,prior_causal,period_snapshot,
  projected_events,projected_kernel,hpp_projection,actual_fact,actual_physical,actual_events,actual_kernel,actual_original_journal,assignment_proof,materialization_id,actual_objects,actual_objects_sha256)
 values(w.operation_id,p_return,w.source_sale_id,family,ordinal,w.backend_pid,w.transaction_id,w.principal,w.principal_sha256,w.draft_manifest,
  ow04_source_proposal.sha(w.draft_manifest),w.source_snapshot,ow04_source_proposal.sha(w.source_snapshot),w.preserved_source,w.before_events,w.prior_causal,w.period_snapshot,
  w.projected_events,w.projected_kernel,w.hpp_projection,fact,cp7_credit.native_empty_physical_v1(p_return),actual_events,k,journal,assignment,marker,objects,ow04_source_proposal.sha(objects));
 perform cp7_credit.verify_native_empty_member_v1(p_return);
 reconciled:=ow04_ordinal_wrapper.reconcile_v1(cp7_credit.initial_ordinal_input_v1(w.source_sale_id));
 if not(reconciled->>'arithmetic_supported')::boolean or exists(select 1 from jsonb_array_elements(reconciled->'families')f
  where(f->>'has_reconciliation_effect')::boolean or(f->'source_target'->>'has_recognition_effect')::boolean)then
  raise exception 'CP7_NATIVE_EMPTY_ORDINAL_PROFILE_NOT_EMPTY';end if;
 insert into cp7_credit.financial_materializations(id,root_sale_id,actor,request_id,request_ordinal,owning_action,payload_sha256,source_plan_sha256,actual_objects,actual_objects_sha256)
 values(marker,w.source_sale_id,uid,null,1,'NATIVE_EMPTY_RETURN',ow04_source_proposal.sha(w.draft_manifest),ow04_source_proposal.sha(k),objects,ow04_source_proposal.sha(objects));
 insert into cp7_credit.financial_materialization_objects(object_kind,object_id,materialization_id,fact_sha256)
 select x->>'object_kind',(x->>'object_id')::uuid,marker,x->>'fact_sha256'from jsonb_array_elements(objects)x;
 update cp7_credit.native_empty_work set phase='REGISTERED',family_id=family,materialization_id=marker where operation_id=w.operation_id;
 perform cp7_credit.assert_current_materialized_profile(w.source_sale_id,w.source_sale_id,w.source_sale_id);
 select coalesce(sum(p.amount),0)into raw_paid from erp.sales_payments p where p.sale_id=w.source_sale_id and p.status='POSTED';
 if raw_paid is distinct from(w.guard_values->>'raw_paid')::numeric or raw_paid>p_net_after or raw_paid<0 then raise exception 'CP7_NATIVE_EMPTY_FINAL_RAW_P_CHANGED';end if;
 return raw_paid;
end $$;

create function cp7_credit.assert_native_empty_closed_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.native_empty_operations;c cp7_credit.native_empty_completions;h erp.sales_headers;net numeric;paid numeric;
begin
 select *into strict o from cp7_credit.native_empty_operations where operation_id=p_operation;
 select *into strict c from cp7_credit.native_empty_completions where operation_id=p_operation;
 perform cp7_credit.verify_native_empty_member_v1(o.source_return_id);
 if c.final_manifest_sha256 is distinct from ow04_source_proposal.sha(c.final_manifest)
  or c.final_manifest->>'contract_version'is distinct from'ow04.native-empty-return-completion.v1'
  or(c.final_manifest->>'operation_id')::uuid is distinct from o.operation_id
  or(c.final_manifest->>'source_sale_id')::uuid is distinct from o.source_sale_id
  or(c.final_manifest->>'source_return_id')::uuid is distinct from o.source_return_id
  or c.final_manifest->'actual_fact'is distinct from o.actual_fact
  or c.final_manifest->>'principal_sha256'is distinct from o.principal_sha256
  or c.final_manifest->>'assignment_sha256'is distinct from ow04_source_proposal.sha(o.assignment_proof)
  or(c.final_manifest->>'materialization_id')::uuid is distinct from o.materialization_id
  or c.final_manifest->>'return_status'is distinct from'POSTED'
  or c.final_manifest->>'header_status'is distinct from(case
   when(c.final_manifest->>'raw_paid')::numeric=(c.final_manifest->>'net_after')::numeric then'PAID'
   when(c.final_manifest->>'raw_paid')::numeric>0 then'PARTIAL_PAID'else'POSTED'end)
  or(c.final_manifest->>'raw_paid')::numeric<0 or(c.final_manifest->>'raw_paid')::numeric>(c.final_manifest->>'net_after')::numeric then
  raise exception 'CP7_NATIVE_EMPTY_COMPLETION_CHANGED';end if;
 if exists(select 1 from cp7_credit.native_empty_work where operation_id=p_operation)
  or exists(select 1 from cp7_credit.native_empty_source_scope where source_sale_id=o.source_sale_id)then
  raise exception 'CP7_NATIVE_EMPTY_PRIVATE_SCOPE_LEAK';end if;
 perform cp7_credit.assert_simple_native_base_v1(o.source_sale_id);
 select *into strict h from erp.sales_headers where id=o.source_sale_id;
 if h.status in('POSTED','PARTIAL_PAID','PAID')then
  perform cp7_credit.assert_current_materialized_profile(h.id,h.id,h.id);
  net:=(select coalesce(sum(line_total),0)from erp.sales_items where sale_id=h.id)
   -(select coalesce(sum(i.refund_amount),0)from erp.sales_returns r join erp.sales_return_items i on i.return_id=r.id
    where r.sale_id=h.id and r.status='POSTED');
  paid:=cp7_credit.current_effective_paid(h.id);
  if net<0 or paid<0 or paid>net or h.status is distinct from(case when paid=net then'PAID'when paid>0 then'PARTIAL_PAID'else'POSTED'end)then
   raise exception 'CP7_NATIVE_EMPTY_FINAL_AR_OR_STATUS';end if;
 elsif h.status='REVERSED'then
  if exists(select 1 from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id where f.family_root_sale_id=h.id)
   or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=h.id)then
   raise exception 'CP7_NATIVE_EMPTY_REVERSED_WITH_CREDIT';end if;
  perform cp7_credit.assert_zero_excess_v1(cp7_credit.initial_base_events_v1(h.id));
  net:=(select coalesce(sum(case when x->>'kind'='NET'then(x->>'amount')::numeric else 0 end),0)from jsonb_array_elements(cp7_credit.initial_base_events_v1(h.id))x);
  paid:=(select coalesce(sum(case when x->>'kind'='FUNDING'then(x->>'amount')::numeric else 0 end),0)from jsonb_array_elements(cp7_credit.initial_base_events_v1(h.id))x);
  if net<>0 or paid<>0 then raise exception 'CP7_NATIVE_EMPTY_REVERSED_SOURCE_NOT_NEUTRAL';end if;
 else raise exception 'CP7_NATIVE_EMPTY_FINAL_SALE_STATE';end if;
 perform cp7_credit.assert_native_empty_provenance_v1(jsonb_build_object('materialization_ids',jsonb_build_array(o.materialization_id)));
end $$;

create function cp7_credit.native_empty_leave_v1(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.native_empty_work;h erp.sales_headers;manifest jsonb;net numeric;paid numeric;hpp_group jsonb;actual_target jsonb;
begin
 perform cp7_credit.assert_native_empty_work_v1(p_return);
 select *into strict w from cp7_credit.native_empty_work where source_return_id=p_return;
 if w.phase<>'REGISTERED'or w.posting_lines is not null or not exists(select 1 from erp.sales_returns where id=p_return and status='POSTED')then
  raise exception 'CP7_NATIVE_EMPTY_POSTED_COMPLETION_REQUIRED';end if;
 select *into strict h from erp.sales_headers where id=w.source_sale_id;
 net:=(w.guard_values->>'net_after')::numeric;paid:=(w.guard_values->>'raw_paid')::numeric;
 if h.status is distinct from(case when paid=net then'PAID'when paid>0 and paid<net then'PARTIAL_PAID'else'POSTED'end)then
  raise exception 'CP7_NATIVE_EMPTY_FINAL_HEADER_STATUS';end if;
 -- This callback is bound before the exact Native terminal END: all Native
 -- PO baseline refreshes and its own complete book checks have now run.
 for hpp_group in select value from jsonb_array_elements(w.hpp_projection->'groups')loop
  if(hpp_group->>'po_id')::uuid is null then
   perform erp.assert_non_po_product_hpp_target_book_v2620f((hpp_group->>'product_id')::uuid);
   select to_jsonb(nt)into strict actual_target from erp.compute_non_po_product_hpp_targets_v2620f((hpp_group->>'product_id')::uuid)nt;
  else
   perform erp.assert_po_hpp_target_book_v2620e((hpp_group->>'po_id')::uuid);
   select to_jsonb(nt)into strict actual_target from erp.compute_po_hpp_gl_targets_v2620d((hpp_group->>'po_id')::uuid)nt;
  end if;
  if actual_target is distinct from hpp_group->'after_target'then raise exception 'CP7_NATIVE_EMPTY_FINAL_HPP_TARGET_CHANGED';end if;
 end loop;
 manifest:=jsonb_build_object('contract_version','ow04.native-empty-return-completion.v1','operation_id',w.operation_id,
  'source_sale_id',w.source_sale_id,'source_return_id',p_return,'return_status','POSTED','header_status',h.status,
  'net_after',cp7_credit.cent_text(net),'raw_paid',cp7_credit.cent_text(paid),'actual_fact',ow04_source_proposal.return_fact_v1(p_return),
  'principal_sha256',w.principal_sha256,'assignment_sha256',(select source_sha256 from cp7_credit.return_families where id=w.family_id),
  'materialization_id',w.materialization_id);
 insert into cp7_credit.native_empty_completions(operation_id,final_manifest,final_manifest_sha256)values(w.operation_id,manifest,ow04_source_proposal.sha(manifest));
 delete from cp7_credit.native_empty_work where operation_id=w.operation_id;
 perform cp7_credit.assert_native_empty_closed_v1(w.operation_id);
 perform erp.require_internal();
end $$;

-- Direct Native EMPTY source changes preserve original Native authority,
-- including a real NULL-human service/system call. No CP7 receipt is invented.
create function cp7_credit.native_empty_source_enter_v1(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare sale uuid;finished boolean:=false;src jsonb;
begin
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if p_action in('PAYMENT','PAYMENT_REVERSE')then select sale_id,status='REVERSED'and p_action='PAYMENT_REVERSE'into strict sale,finished from erp.sales_payments where id=p_source;
 elsif p_action='RETURN_REVERSE'then select sale_id,status='REVERSED'into strict sale,finished from erp.sales_returns where id=p_source;
 elsif p_action='SALE_REVERSE'then select id,status='REVERSED'into strict sale,finished from erp.sales_headers where id=p_source;
 else raise exception 'CP7_NATIVE_EMPTY_SOURCE_ACTION';end if;
 perform cp7_credit.assert_no_ambient_native_context();
 if not cp7_credit.has_ow04_participation_v1(sale)then return;end if;
 src:=ow04_source_proposal.locked_source_family(sale);
 if src->>'source_status'<>'BASE_COLLECTED'then raise exception 'CP7_NATIVE_EMPTY_SOURCE_NOT_QUALIFIED';end if;
 perform cp7_credit.assert_native_empty_supported_v1(sale);
 perform cp7_credit.assert_simple_native_base_v1(sale);
 perform cp7_credit.assert_zero_excess_v1(cp7_credit.initial_base_events_v1(sale));
 if finished then return;end if; -- original Native replay returns before complete
 if exists(select 1 from cp7_credit.native_empty_work where backend_pid=pg_backend_pid()and transaction_id=txid_current())then raise exception 'CP7_NATIVE_EMPTY_NESTED_SOURCE';end if;
 insert into cp7_credit.native_empty_source_scope values(pg_backend_pid(),txid_current(),gen_random_uuid(),p_action,p_source,sale,
  cp7_credit.native_empty_principal_v1(),cp7_credit.initial_base_events_v1(sale),src);
end $$;
create function cp7_credit.native_empty_source_complete_v1(p_action text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.native_empty_source_scope;sale uuid;o record;
begin
 select *into s from cp7_credit.native_empty_source_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if s.operation_id is null then
  if p_action in('PAYMENT','PAYMENT_REVERSE')then select sale_id into strict sale from erp.sales_payments where id=p_source;
  elsif p_action='RETURN_REVERSE'then select sale_id into strict sale from erp.sales_returns where id=p_source;
  elsif p_action='SALE_REVERSE'then sale:=p_source;
  else raise exception 'CP7_NATIVE_EMPTY_SOURCE_ACTION';end if;
  if not cp7_credit.has_ow04_participation_v1(sale)then return;end if;
  raise exception 'CP7_NATIVE_EMPTY_SOURCE_SCOPE_REQUIRED';
 end if;
 if(s.action,s.source_id)is distinct from(p_action,p_source)or s.principal is distinct from cp7_credit.native_empty_principal_v1()
  or not cp7_credit.native_empty_is_direct_v1()then raise exception 'CP7_NATIVE_EMPTY_SOURCE_SCOPE_CHANGED';end if;
 perform cp7_credit.assert_no_ambient_native_context();
 perform cp7_credit.assert_simple_native_base_v1(s.source_sale_id);
 perform cp7_credit.assert_zero_excess_v1(cp7_credit.initial_base_events_v1(s.source_sale_id));
 -- Never call the current-E core during the mutation's incomplete midpoint.
 -- After completion its complete retained facts/markers are independently read.
 if exists(select 1 from erp.sales_headers where id=s.source_sale_id and status in('POSTED','PARTIAL_PAID','PAID'))then
  perform cp7_credit.assert_current_materialized_profile(s.source_sale_id,s.source_sale_id,s.source_sale_id);end if;
 delete from cp7_credit.native_empty_source_scope where operation_id=s.operation_id;
 for o in select operation_id from cp7_credit.native_empty_operations where source_sale_id=s.source_sale_id loop
  perform cp7_credit.assert_native_empty_closed_v1(o.operation_id);
 end loop;
end $$;

-- Dispatch is factual and context-free. In particular, COMMIT can run after
-- the caller changes inspection claims; no recorded actor is write authority.
create function cp7_credit.native_empty_closure_id_v1(p_table text,p_row jsonb)returns uuid
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare answer uuid;family uuid;marker uuid;
begin
 if p_table in('native_empty_operations','native_empty_completions')then return(p_row->>'operation_id')::uuid;
 elsif p_table='return_families'then
  if p_row->'assignment_proof'->>'contract_version'='ow04.native-empty-return-family-assignment.v1'then
   return(p_row->'assignment_proof'->>'operation_id')::uuid;end if;
 elsif p_table='return_family_members'then family:=(p_row->>'family_id')::uuid;
 elsif p_table='financial_materializations'then
  marker:=(p_row->>'id')::uuid;
  if p_row->>'owning_action'='NATIVE_EMPTY_RETURN'then
   select operation_id into strict answer from cp7_credit.native_empty_operations where materialization_id=marker;return answer;end if;
 elsif p_table='financial_materialization_objects'then marker:=(p_row->>'materialization_id')::uuid;
 end if;
 select operation_id into answer from cp7_credit.native_empty_operations where family_id=family or materialization_id=marker;
 return answer;
end $$;
create function cp7_credit.enforce_native_empty_closure_v1()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
declare operation uuid;
begin
 operation:=cp7_credit.native_empty_closure_id_v1(tg_table_name,to_jsonb(new));
 if operation is null then raise exception 'CP7_NATIVE_EMPTY_UNOWNED_FACT';end if;
 perform cp7_credit.assert_native_empty_closed_v1(operation);return null;
end $$;
create function cp7_credit.enforce_native_empty_no_scope_v1()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin
 if exists(select 1 from cp7_credit.native_empty_work where backend_pid=new.backend_pid and transaction_id=new.transaction_id)
  or exists(select 1 from cp7_credit.native_empty_source_scope where backend_pid=new.backend_pid and transaction_id=new.transaction_id)then
  raise exception 'CP7_NATIVE_EMPTY_PRIVATE_SCOPE_LEAK';end if;return null;
end $$;
do $deferred$declare t text;begin
 foreach t in array array['native_empty_operations','native_empty_completions']loop
  execute format('create constraint trigger native_empty_closed after insert on cp7_credit.%I deferrable initially deferred for each row execute function cp7_credit.enforce_native_empty_closure_v1()',t);
 end loop;
 foreach t in array array['native_empty_work','native_empty_source_scope']loop
  execute format('create constraint trigger native_empty_scope_closed after insert or update on cp7_credit.%I deferrable initially deferred for each row execute function cp7_credit.enforce_native_empty_no_scope_v1()',t);
 end loop;
end $deferred$;
do $private$declare r record;begin
 for r in select p.oid::regprocedure identity from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='cp7_credit'and(p.proname like'%native_empty%'or p.proname='without_native_empty_markers_v1')loop
  execute format('alter function %s owner to postgres',r.identity);
  execute format('revoke all on function %s from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write',r.identity);
 end loop;
end $private$;
