-- Later ordinary Native reversals/payments have no qualified E adapter yet.
-- The retained callback's raw target UUID predicate would miss carried money;
-- guard its complete owned note family before its direct-Native fast path.
-- E's exact private inverse uses reverse_enter_v1 instead of this callback.
create function cp7_credit_note_carry_de.guard_later_native_source_v1(p_action text,p_source uuid)returns void
language plpgsql stable security definer set search_path=''as $$
declare sale uuid;begin
 if p_action in('PAYMENT','PAYMENT_REVERSE')then select sale_id into sale from erp.sales_payments where id=p_source;
 elsif p_action='RETURN_REVERSE'then select sale_id into sale from erp.sales_returns where id=p_source;
 elsif p_action='SALE_REVERSE'then sale:=p_source;
 else return;end if;
 if exists(select 1 from cp7_note.revisions r where sale in(r.root_sale_id,r.previous_sale_id,r.replacement_sale_id)
  and cp7_credit_note_carry_de.has_root_v1(r.root_sale_id))then
  raise exception 'CP7_CREDIT_NOTE_CARRY_LATER_NATIVE_MUTATION_ADAPTER_REQUIRED';end if;
end $$;
create function cp7_credit_note_carry_de.assert_work_v1()returns void
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_note_carry_de.work_v1;q cp7_note.requests;begin
 select *into strict w from cp7_credit_note_carry_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 select *into strict q from cp7_note.requests where actor=w.actor and request_id=w.request_id;
 if(q.payload,q.expected_version,q.response)is distinct from(w.payload,w.expected_version,null::jsonb)
  or cp7_note.access_now()is distinct from w.authority
  or(select to_jsonb(p)from erp.accounting_period_control p where singleton_id=1)is distinct from w.period
  or not exists(select 1 from cp7_note.context c where c.backend_pid=w.backend_pid and c.transaction_id=w.transaction_id and c.actor=w.actor and c.source_sale_id=w.source_sale_id)
  or not exists(select 1 from cp7_sales.command_context c where c.backend_pid=w.backend_pid and c.transaction_id=w.transaction_id and c.actor=w.actor and c.sale_id=w.source_sale_id and c.action='SALE_REVERSE')then
  raise exception 'CP7_CREDIT_NOTE_CARRY_OWN_PENDING_CONTEXT_REQUIRED';end if;
end $$;
create function cp7_credit_note_carry_de.prepare_v1(p jsonb,p_request uuid,p_expected text,p_revision uuid,p_authority jsonb)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare basis jsonb;plan jsonb;net numeric;graph jsonb;sources jsonb;sales uuid[];lots uuid[];journal_ids uuid[];source_doc jsonb;begin
 -- Called after retained Native FG/FGBOOK, invoice CAS and original eligibility.
 if exists(select 1 from cp7_credit_note_carry_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())then raise exception 'CP7_CREDIT_NOTE_CARRY_NESTED_OPERATION';end if;
 graph:=cp7_credit.consumer_dependency_graph_v1((p->>'sale_id')::uuid);
 select array_agg(value::uuid order by value)into sales from jsonb_array_elements_text(graph->'sale_ids');
 perform 1 from erp.sales_headers where id=any(sales)order by id for update;
 perform 1 from erp.sales_items where sale_id=any(sales)order by id for share;
 perform 1 from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id=any(sales))order by id for share;
 perform 1 from erp.sales_payments where sale_id=any(sales)order by id for update;
 perform 1 from erp.sales_returns where sale_id=any(sales)order by id for update;
 perform 1 from cp7_credit.return_families where family_root_sale_id=any(sales)order by id for update;
 perform 1 from cp7_credit.cohorts where source_sale_id=any(sales)order by id for update;
 perform 1 from cp7_credit.consumption_events where cohort_id in(select id from cp7_credit.cohorts where source_sale_id=any(sales))order by id for share;
 perform 1 from erp.customers where id=(p->>'customer_id')::uuid for share;
 journal_ids:=cp7_credit.consumer_journal_ids_v1(sales);
 perform 1 from erp.journal_entries where id=any(journal_ids)order by id for share;
 perform 1 from erp.journal_lines where journal_entry_id=any(journal_ids)order by id for share;
 select coalesce(array_agg(distinct lot order by lot),'{}')into lots from unnest(sales)s cross join lateral unnest(cp7_credit.source_hpp_lot_ids_v1(s))lot;
 perform 1 from erp.fg_stock_movements where lot_id=any(lots)order by id for update;
 perform 1 from erp.fg_inventory_balances b where product_id in(select product_id from erp.fg_lots where id=any(lots))order by product_id,location_id,quality_grade for update;
 perform 1 from erp.fg_lots where id=any(lots)order by id for update;
 perform 1 from erp.hpp_versions where lot_id=any(lots)order by id for share;
 perform 1 from erp.opening_lot_hpp_gl_state where lot_id=any(lots)order by lot_id for update;
 perform 1 from erp.opening_hpp_corrections where lot_id=any(lots)order by id for share;
 perform 1 from erp.po_hpp_gl_state where po_id in(select po_id from erp.fg_lots where id=any(lots))order by po_id for update;
 lock table erp.accounting_account_mappings in share mode;
 perform 1 from erp.chart_accounts where id in(select account_id from erp.accounting_account_mappings
  union select credit_account_id from cp7_credit.cohorts where source_sale_id=any(sales))order by id for share;
 if graph is distinct from cp7_credit.consumer_dependency_graph_v1((p->>'sale_id')::uuid)or journal_ids is distinct from cp7_credit.consumer_journal_ids_v1(sales)then
  raise exception 'CP7_CREDIT_NOTE_CARRY_LOCK_GRAPH_CHANGED';end if;
 sources:=cp7_credit.consumer_capture_sources_v1(jsonb_build_object('sale_ids',sales));
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 basis:=cp7_credit_note_carry_de.basis_v1((p->>'sale_id')::uuid);net:=cp7_credit_note_carry_de.assert_price_only_v1(p);
 if basis is null then raise exception 'CP7_CREDIT_NOTE_CARRY_INCOMING_REQUIRED';end if;
 plan:=cp7_credit_note_carry_de.plan_v1(basis,cp7_credit.cent_text(net));
 if plan->>'state'<>'READY'then raise exception 'CP7_CREDIT_NOTE_CARRY_REVIEW_REFUSED'using detail=cp7_credit_note_carry_de.public_basis_v1(basis)::text;end if;
 if p->'credit_carry_review'is distinct from cp7_credit_note_carry_de.review_payload_v1(plan)then raise exception 'CP7_CREDIT_NOTE_CARRY_STALE_REVIEW';end if;
 if cp7_note.access_now()is distinct from p_authority then raise exception 'CP7_NOTE_ACCESS_CHANGED';end if;
 perform cp7_credit.assert_source_native_trigger_census_v1();
 source_doc:=cp7_credit_note_carry_de.raw_native_snapshot_v1((p->>'sale_id')::uuid);
 perform cp7_credit.source_first_nonpo_hpp_alignment_v1(source_doc);
 insert into cp7_credit_note_carry_de.work_v1(operation_id,backend_pid,transaction_id,actor,request_id,source_sale_id,revision_id,expected_version,payload,
  authority,period,basis,review,graph,before_sources,before_materialized,phase)
 values(gen_random_uuid(),pg_backend_pid(),txid_current(),auth.uid(),p_request,(p->>'sale_id')::uuid,p_revision,p_expected,p,p_authority,
  (select to_jsonb(x)from erp.accounting_period_control x where singleton_id=1),basis,plan,graph,sources,basis->'materialized','PREPARED');
end $$;
create function cp7_credit_note_carry_de.reverse_enter_v1(p_action text,p_sale uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_note_carry_de.work_v1;begin
 perform cp7_credit_note_carry_de.assert_work_v1();select *into strict w from cp7_credit_note_carry_de.work_v1
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 if p_action<>'SALE_REVERSE'or w.source_sale_id<>p_sale or w.phase<>'PREPARED'
  or cp7_credit_note_carry_de.raw_native_snapshot_v1(p_sale)is distinct from w.basis->'native'then raise exception 'CP7_CREDIT_NOTE_CARRY_NATIVE_ENTRY_CHANGED';end if;
end $$;
create function cp7_credit_note_carry_de.reverse_complete_v1(p_action text,p_sale uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
begin
 perform cp7_credit_note_carry_de.assert_work_v1();
 if p_action<>'SALE_REVERSE'or not exists(select 1 from erp.sales_headers where id=p_sale and status='REVERSED')then raise exception 'CP7_CREDIT_NOTE_CARRY_NATIVE_INVERSE_INCOMPLETE';end if;
 update cp7_credit_note_carry_de.work_v1 set phase='REVERSED'where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and source_sale_id=p_sale and phase='PREPARED';
 if not found then raise exception 'CP7_CREDIT_NOTE_CARRY_NATIVE_PHASE_CHANGED';end if;
end $$;
create function cp7_credit_note_carry_de.materialize_v1(p_replacement uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare w cp7_credit_note_carry_de.work_v1;actual jsonb;effect jsonb;item jsonb;e cp7_credit.consumption_events;amount numeric;net numeric;begin
 perform cp7_credit_note_carry_de.assert_work_v1();select *into strict w from cp7_credit_note_carry_de.work_v1
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and phase='REVERSED';
 if not exists(select 1 from cp7_note.revisions where id=w.revision_id and root_sale_id=w.source_sale_id and previous_sale_id=w.source_sale_id
  and replacement_sale_id=p_replacement and revision=1 and actor=w.actor and request_id=w.request_id)then raise exception 'CP7_CREDIT_NOTE_CARRY_ACTUAL_REVISION_REQUIRED';end if;
 actual:=cp7_credit_note_carry_de.raw_native_snapshot_v1(p_replacement);net:=(w.review->>'replacement_net')::numeric;amount:=(w.review->>'transfer_amount')::numeric;
 effect:=cp7_credit_note_carry_de.assert_effect_v1(w.basis->'native',actual,w.source_sale_id,p_replacement,net);
 perform cp7_credit.source_first_nonpo_hpp_alignment_v1(actual);
 for item in select value from jsonb_array_elements(w.basis->'incoming_facts')loop
  select *into strict e from cp7_credit.consumption_events where id=(item#>>'{event,id}')::uuid;
  if to_jsonb(e)is distinct from item->'event'or cp7_credit.materialized_journal_payload(e.journal_id)is distinct from item->'journal'
   or cp7_credit.consumer_event_data_v1(e.id)is distinct from item->'actual_data'then raise exception 'CP7_CREDIT_NOTE_CARRY_ORIGINAL_MONEY_CHANGED';end if;
  insert into cp7_credit_note_carry_de.assignments_v1 values(w.operation_id,e.id,'APPLY',e.target_sale_id,w.source_sale_id,p_replacement,
   to_jsonb(e),cp7_credit.materialized_journal_payload(e.journal_id),cp7_credit.pg_jsonb_sha256(to_jsonb(e)),cp7_credit.pg_jsonb_sha256(cp7_credit.materialized_journal_payload(e.journal_id)));
 end loop;
 if(select count(*)from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=w.source_sale_id)<>jsonb_array_length(w.basis->'incoming_facts')then
  raise exception 'CP7_CREDIT_NOTE_CARRY_EVENT_SET_CHANGED';end if;
 update cp7_credit_note_carry_de.work_v1 set replacement_sale_id=p_replacement,actual_source=actual,actual_proof=effect,phase='MATERIALIZED'where operation_id=w.operation_id;
 update erp.sales_headers set status=case when amount=net then'PAID'when amount>0 then'PARTIAL_PAID'else'POSTED'end where id=p_replacement;
 update cp7_credit_note_carry_de.work_v1 set actual_source=cp7_credit_note_carry_de.raw_native_snapshot_v1(p_replacement)where operation_id=w.operation_id;
 perform cp7_credit.assert_current_materialized_profile(p_replacement,w.source_sale_id,p_replacement);
end $$;
create function cp7_credit_note_carry_de.finish_v1(p_response jsonb)returns void
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_note_carry_de.work_v1;q cp7_note.requests;begin
 select *into strict w from cp7_credit_note_carry_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and phase='MATERIALIZED';
 select *into strict q from cp7_note.requests where actor=w.actor and request_id=w.request_id;
 if(q.payload,q.expected_version,q.response)is distinct from(w.payload,w.expected_version,p_response)
  or cp7_note.access_now()is distinct from w.authority
  or exists(select 1 from cp7_note.context where backend_pid=w.backend_pid and transaction_id=w.transaction_id)
  or exists(select 1 from cp7_sales.command_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id)then raise exception 'CP7_CREDIT_NOTE_CARRY_FINAL_RECEIPT_OR_SCOPE_CHANGED';end if;
 insert into cp7_credit_note_carry_de.operations_v1(operation_id,actor,request_id,source_sale_id,replacement_sale_id,revision_id,payload,expected_version,proof,response)
 values(w.operation_id,w.actor,w.request_id,w.source_sale_id,w.replacement_sale_id,w.revision_id,w.payload,w.expected_version,to_jsonb(w),p_response);
 delete from cp7_credit_note_carry_de.work_v1 where operation_id=w.operation_id;
 perform cp7_credit_note_carry_de.assert_closed_v1(w.operation_id);
end $$;
create function cp7_credit_note_carry_de.dispatch_v1(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
begin
 if exists(select 1 from cp7_credit_note_carry_de.operations_v1 where actor=auth.uid()and request_id=p_request)
  or exists(select 1 from cp7_credit.consumption_events e where e.event_kind='APPLY'and cp7_credit_note_carry_de.effective_target_v1(e.id)=(p->>'sale_id')::uuid)then
  return cp7_credit_note_carry_de.command_v1(p,p_request,p_expected);end if;
 return cp7_note.command(p,p_request,p_expected);
end $$;
