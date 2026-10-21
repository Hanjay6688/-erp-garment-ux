-- Pending whole composition/qualification. Bounded first consumer vertical:
-- no note/correction adapter or new family recognition is silently adopted.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

create function cp7_credit.consumer_selection_v1(p jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare ch cp7_credit.cohorts;old cp7_credit.consumption_events;kind text;amount numeric;
 target uuid;cash uuid;original uuid;source_assignment record;target_assignment record;
begin
 kind:=cp7_credit.consumer_payload_kind_v1(p);
 if p->>'action'='UNDO'then
  select *into strict old from cp7_credit.consumption_events where id=(p->>'restores_event_id')::uuid;
  perform cp7_credit.consumer_event_data_v1(old.id);
  if exists(select 1 from cp7_credit.consumption_events where restores_event_id=old.id)then
   raise exception 'CP7_CREDIT_CONSUMER_ORIGINAL_ALREADY_UNDONE';end if;
  original:=old.id;amount:=-old.amount;target:=old.target_sale_id;cash:=old.cash_account_id;
  select *into strict ch from cp7_credit.cohorts where id=old.cohort_id;
 else
  select *into strict ch from cp7_credit.cohorts where id=(p->>'cohort_id')::uuid;
  amount:=(p->>'amount')::numeric;target:=(p->>'target_sale_id')::uuid;cash:=(p->>'cash_account_id')::uuid;
 end if;
 select *into strict source_assignment from cp7_credit.current_leaf_assignment(ch.source_sale_id);
 if source_assignment.requested_status not in('POSTED','PARTIAL_PAID','PAID')
  or(source_assignment.root_sale_id,source_assignment.current_leaf_id)is distinct from(ch.source_sale_id,ch.source_sale_id)then
  raise exception 'CP7_CREDIT_CONSUMER_SOURCE_CORRECTION_ADAPTER_REQUIRED';end if;
 if target is not null then
  select *into strict target_assignment from cp7_credit.current_leaf_assignment(target);
  if target_assignment.customer_id<>ch.customer_id or target_assignment.root_sale_id=source_assignment.root_sale_id then
   raise exception 'CP7_CREDIT_CONSUMER_DISTINCT_SAME_CUSTOMER_TARGET_REQUIRED';end if;
  if target_assignment.requested_status not in('POSTED','PARTIAL_PAID','PAID')
   or(target_assignment.root_sale_id,target_assignment.current_leaf_id)is distinct from(target,target)then
   raise exception 'CP7_CREDIT_CONSUMER_TARGET_CORRECTION_ADAPTER_REQUIRED';end if;
 end if;
 return jsonb_build_object('action',p->>'action','event_kind',kind,'cohort_id',ch.id,'customer_id',ch.customer_id,
  'source_sale_id',ch.source_sale_id,'source_root_sale_id',source_assignment.root_sale_id,
  'source_current_leaf_id',source_assignment.current_leaf_id,'target_sale_id',target,
  'target_root_sale_id',case when target is not null then target_assignment.root_sale_id end,
  'target_current_leaf_id',case when target is not null then target_assignment.current_leaf_id end,
  'cash_account_id',cash,'restores_event_id',original,'amount',cp7_credit.cent_text(amount::cp7_credit.cent_amount));
end $$;

create function cp7_credit.consumer_joined_graph_v1(p_source uuid,p_target uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare source_graph jsonb;target_graph jsonb;sales jsonb;
begin
 source_graph:=cp7_credit.consumer_dependency_graph_v1(p_source);
 if p_target is not null then
  target_graph:=cp7_credit.consumer_dependency_graph_v1(p_target);
  if target_graph->>'customer_id'is distinct from source_graph->>'customer_id'then
   raise exception 'CP7_CREDIT_CONSUMER_GRAPH_CUSTOMER_CHANGED';end if;
 end if;
 select jsonb_agg(v order by v)into sales from(select distinct value v from jsonb_array_elements_text(
  (source_graph->'sale_ids')||coalesce(target_graph->'sale_ids','[]')))all_ids;
 return jsonb_build_object('contract_version','ow04.consumer-joined-graph.v1','source',source_graph,
  'target',target_graph,'customer_id',source_graph->'customer_id','sale_ids',sales);
end $$;

-- Exclude only consumer-owned monetary journal events from Native invariants.
-- They have their own exact actual-data proof. Everything else, including
-- payment rows, Native originals/inverses, stock and HPP, remains byte-exact.
create function cp7_credit.consumer_native_invariant_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare native jsonb;events jsonb;journals jsonb;
begin
 native:=cp7_credit.source_native_snapshot_v1(p_sale);
 select coalesce(jsonb_agg(v order by v->>'id'collate"C"),'[]')into events
  from jsonb_array_elements(native->'base_events')v where not exists(select 1 from cp7_credit.consumption_events ce
   where ce.event_kind='APPLY'and ce.target_sale_id=p_sale and ce.journal_id=substring(v->>'id'from 9)::uuid);
 select coalesce(jsonb_agg(v order by v->>'id'collate"C"),'[]')into journals
  from jsonb_array_elements(native->'journals')v where not exists(select 1 from cp7_credit.consumption_events ce
   where ce.event_kind='APPLY'and ce.target_sale_id=p_sale and ce.journal_id=(v->>'id')::uuid);
 -- The opaque support hash contains ALLOCATION.sale including the very
 -- status/version/touch fields retired by this command. Raw allocations,
 -- items, movements, lots, HPP versions/caches/GL/targets remain exact here.
 -- The qualified source terminal proof makes the same distinction.
 return (native-'hpp_support')||jsonb_build_object('sale',(native->'sale')-'status'-'row_version'-'updated_at',
  'base_events',events,'journals',journals);
end $$;

create function cp7_credit.consumer_source_vectors_v1(p_cohort uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare ch cp7_credit.cohorts;e cp7_credit.consumption_events;i jsonb;c jsonb;
begin
 select *into strict ch from cp7_credit.cohorts where id=p_cohort;
 -- The full locked materialized profile proves every component/part/J first.
 perform cp7_credit.assert_current_materialized_profile(ch.source_sale_id,ch.source_sale_id,ch.source_sale_id);
 select coalesce(jsonb_agg(jsonb_build_object('id','part:'||part.id::text,'amount',cp7_credit.cent_text(part.amount),
  'economic_date',link.economic_date::text,'transaction_date',link.transaction_date::text,
  'source_sha256',cp7_credit.pg_jsonb_sha256(jsonb_build_object('part',to_jsonb(part),'link',to_jsonb(link))))order by part.id),'[]')into i
  from cp7_credit.recognition_plans plan join cp7_credit.recognition_components component on component.plan_id=plan.id
  join cp7_credit.component_parts part on part.component_id=component.id join cp7_credit.component_journals link on link.part_id=part.id
  where plan.cohort_id=ch.id;
 for e in select *from cp7_credit.consumption_events where cohort_id=ch.id order by id loop
  perform cp7_credit.consumer_event_data_v1(e.id);
 end loop;
 select coalesce(jsonb_agg(jsonb_build_object('id','consumption:'||ce.id::text,'amount',cp7_credit.cent_text(ce.amount),
  'economic_date',ce.economic_date::text,'transaction_date',ce.transaction_date::text,'source_sha256',ce.source_sha256)order by ce.id),'[]')into c
  from cp7_credit.consumption_events ce where ce.cohort_id=ch.id;
 return jsonb_build_object('recognition',i,'consumptions',c);
end $$;

create function cp7_credit.consumer_capture_sources_v1(p_graph jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare sale uuid;sources jsonb:='{}';profile jsonb;
begin
 for sale in select value::uuid from jsonb_array_elements_text(p_graph->'sale_ids')order by value loop
  perform cp7_credit.assert_current_materialized_profile(sale,sale,sale);
  profile:=cp7_credit.inspect_current_materialized_profile(sale,sale,sale);
  sources:=sources||jsonb_build_object(sale::text,jsonb_build_object('native',cp7_credit.source_native_snapshot_v1(sale),
   'profile',profile,'review_token',cp7_sales.review_token(sale)));
 end loop;
 return sources;
end $$;

create function cp7_credit.consumer_journal_ids_v1(p_sales uuid[])returns uuid[]
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 with recursive roots(id)as(
  select j.id from erp.journal_entries j where(j.source_type='SALE'and j.source_id=any(p_sales))
   or(j.source_type='SALES_PAYMENT'and exists(select 1 from erp.sales_payments p where p.id=j.source_id and p.sale_id=any(p_sales)))
   or(j.source_type='SALES_RETURN'and exists(select 1 from erp.sales_returns r where r.id=j.source_id and r.sale_id=any(p_sales)))
  union select cj.journal_id from cp7_credit.component_journals cj join cp7_credit.component_parts part on part.id=cj.part_id
   join cp7_credit.recognition_components component on component.id=part.component_id
   join cp7_credit.recognition_plans plan on plan.id=component.plan_id join cp7_credit.cohorts c on c.id=plan.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=any(p_sales)
  union select ce.journal_id from cp7_credit.consumption_events ce join cp7_credit.cohorts c on c.id=ce.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=any(p_sales)or ce.target_sale_id=any(p_sales)
 ),walk(id)as(select id from roots union select j.id from walk w join erp.journal_entries j
  on j.reversal_of_id=w.id or(j.source_type='JOURNAL_REVERSAL'and j.source_id=w.id))
 select coalesce(array_agg(id order by id),'{}'::uuid[])from walk
$$;

create function cp7_credit.consumer_cash_balance_v1(p_account uuid)returns numeric
language sql stable security definer set search_path=''as $$
 select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
  where l.account_id=p_account and j.status in('POSTED','REVERSED')
$$;

create function cp7_credit.consumer_lock_sources_v1(p_payload jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare selection jsonb;authority jsonb;graph jsonb;fresh jsonb;sales uuid[];lots uuid[];hpp uuid[];
 fresh_lots uuid[];fresh_hpp uuid[];journals uuid[];
 cash uuid;cash_coa uuid;period jsonb;sources jsonb;
begin
 selection:=cp7_credit.consumer_selection_v1(p_payload);
 authority:=cp7_credit.consumer_command_access_v1(selection->>'action',selection->>'event_kind');
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_credit.consumer_command_access_v1(selection->>'action',selection->>'event_kind')is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_ACCESS_CHANGED_AFTER_FG_WAIT';end if;
 perform cp7_credit.assert_source_native_trigger_census_v1();
 fresh:=cp7_credit.consumer_selection_v1(p_payload);
 if fresh is distinct from selection then raise exception 'CP7_CREDIT_CONSUMER_SELECTION_CHANGED_AFTER_WAIT';end if;
 graph:=cp7_credit.consumer_joined_graph_v1((selection->>'source_sale_id')::uuid,(selection->>'target_sale_id')::uuid);
 select array_agg(value::uuid order by value)into sales from jsonb_array_elements_text(graph->'sale_ids');
 perform 1 from erp.sales_headers where id=any(sales)order by id for update;
 perform 1 from erp.sales_items where sale_id=any(sales)order by id for share;
 perform 1 from erp.sale_stock_allocations a where a.sale_item_id in(select id from erp.sales_items where sale_id=any(sales))order by a.id for share;
 perform 1 from erp.sales_payments where sale_id=any(sales)order by id for update;
 perform 1 from erp.sales_payment_posting_facts where sale_id=any(sales)order by payment_id for share;
 perform 1 from erp.sales_payment_reversal_facts where payment_id in(select id from erp.sales_payments where sale_id=any(sales))order by payment_id for share;
 perform 1 from erp.sales_returns where sale_id=any(sales)order by id for update;
 perform 1 from erp.sales_return_items where return_id in(select id from erp.sales_returns where sale_id=any(sales))order by id for share;
 perform 1 from cp7_credit.return_families where family_root_sale_id=any(sales)order by id for update;
 perform 1 from cp7_credit.cohorts where source_sale_id=any(sales)order by id for update;
 perform 1 from cp7_credit.consumption_events where cohort_id in(select id from cp7_credit.cohorts where source_sale_id=any(sales))order by id for share;
 perform 1 from erp.customers where id=(selection->>'customer_id')::uuid for share;
 journals:=cp7_credit.consumer_journal_ids_v1(sales);
 perform 1 from erp.journal_entries where id=any(journals)order by id for update;
 perform 1 from erp.journal_lines where journal_entry_id=any(journals)order by id for share;
 if cp7_credit.consumer_journal_ids_v1(sales)is distinct from journals then
  raise exception 'CP7_CREDIT_CONSUMER_JOURNAL_LOCK_SET_CHANGED';end if;
 if cp7_credit.consumer_command_access_v1(selection->>'action',selection->>'event_kind')is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_ACCESS_CHANGED_AFTER_SOURCE_WAIT';end if;
 select coalesce(array_agg(distinct lot order by lot),'{}')into lots from unnest(sales)s
  cross join lateral unnest(cp7_credit.source_hpp_lot_ids_v1(s))lot;
 perform 1 from erp.fg_lots where id=any(lots)order by id for update;
 select coalesce(array_agg(id order by id),'{}')into hpp from erp.hpp_versions where lot_id=any(lots);
 perform 1 from erp.hpp_versions where id=any(hpp)order by id for share;
 perform 1 from erp.opening_lot_hpp_gl_state where lot_id=any(lots)order by lot_id for update;
 perform 1 from erp.opening_hpp_corrections where lot_id=any(lots)order by id for share;
 perform 1 from erp.po_hpp_gl_state where po_id in(select po_id from erp.fg_lots where id=any(lots))order by po_id for update;
 select coalesce(array_agg(distinct lot order by lot),'{}')into fresh_lots from unnest(sales)s
  cross join lateral unnest(cp7_credit.source_hpp_lot_ids_v1(s))lot;
 select coalesce(array_agg(id order by id),'{}')into fresh_hpp from erp.hpp_versions where lot_id=any(lots);
 if(fresh_lots,fresh_hpp)is distinct from(lots,hpp)then
  raise exception 'CP7_CREDIT_CONSUMER_HPP_LOCK_SET_CHANGED';end if;
 -- Bounded first vertical refuses cache/conversion effects before any money.
 -- Full general HPP support remains open; Native callbacks are never disabled.
 if exists(select 1 from erp.opening_lot_hpp_gl_state where lot_id=any(lots))
  or exists(select 1 from erp.fg_lots where id=any(lots)and(po_id is not null or lot_origin='CONVERSION'))then
  raise exception 'CP7_CREDIT_CONSUMER_EXTENDED_HPP_CLOSURE_REQUIRED';end if;
 cash:=(selection->>'cash_account_id')::uuid;
 if cash is not null then
  perform 1 from erp.cash_accounts where id=cash for share;
  select coa_account_id into strict cash_coa from erp.cash_accounts where id=cash;
 end if;
 perform 1 from erp.chart_accounts where id in(select credit_account_id from cp7_credit.cohorts where source_sale_id=any(sales)
  union select ar_account_id from cp7_credit.cohorts where source_sale_id=any(sales)
  union select account_id from erp.journal_lines where customer_id=(selection->>'customer_id')::uuid
  union select cash_coa)order by id for share;
 perform 1 from erp.accounting_account_mappings order by mapping_key for share;
 if cp7_credit.consumer_command_access_v1(selection->>'action',selection->>'event_kind')is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_ACCESS_CHANGED_AFTER_MASTER_WAIT';end if;
 fresh:=cp7_credit.consumer_joined_graph_v1((selection->>'source_sale_id')::uuid,(selection->>'target_sale_id')::uuid);
 if fresh is distinct from graph then raise exception 'CP7_CREDIT_CONSUMER_GRAPH_LOCK_SET_CHANGED';end if;
 sources:=cp7_credit.consumer_capture_sources_v1(graph);
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 select to_jsonb(p)into strict period from erp.accounting_period_control p where singleton_id=1;
 if cash_coa is not null then perform pg_advisory_xact_lock(hashtextextended('CP7_CASH|'||cash_coa::text,0));end if;
 if cp7_credit.consumer_command_access_v1(selection->>'action',selection->>'event_kind')is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_CONSUMER_ACCESS_CHANGED_AFTER_PERIOD_OR_CASH_WAIT';end if;
 if cp7_credit.consumer_capture_sources_v1(graph)is distinct from sources
  or cp7_credit.consumer_selection_v1(p_payload)is distinct from selection then
  raise exception 'CP7_CREDIT_CONSUMER_SOURCE_CHANGED_AFTER_FINAL_WAIT';end if;
 return jsonb_build_object('selection',selection,'authority',authority,'graph',graph,'sources',sources,'period',period,
  'locked_lot_ids',lots,'locked_hpp_ids',hpp,'cash_balance_before',case when cash_coa is not null then
   cp7_credit.cent_text(cp7_credit.consumer_cash_balance_v1(cash_coa)::cp7_credit.cent_amount)end);
end $$;

create function cp7_credit.consumer_projection_v1(p_payload jsonb,p_locked jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare selection jsonb:=p_locked->'selection';ch cp7_credit.cohorts;old cp7_credit.consumption_events;
 physical timestamptz:=(p_payload->>'physical_at')::timestamptz;economic date;lawful date;floor date;book date;
 amount numeric:=(selection->>'amount')::numeric;vectors jsonb;credit jsonb;cash jsonb;target_ar jsonb;
 capacity jsonb;after_capacity jsonb;added jsonb;book_plan jsonb;target_input jsonb;target_result jsonb;
 source_profile jsonb;target_profile jsonb;projection jsonb;versions jsonb:='{}';sale text;before_native jsonb:='{}';
begin
 select *into strict ch from cp7_credit.cohorts where id=(selection->>'cohort_id')::uuid;
 if not isfinite(physical)or physical>statement_timestamp()
  or physical<(select physical_at from erp.sales_returns where id=ch.source_return_id)then
  raise exception 'CP7_CREDIT_CONSUMER_PHYSICAL_SOURCE_DATE_INVALID';end if;
 economic:=(physical at time zone'Asia/Jakarta')::date;
 lawful:=erp.resolve_accounting_transaction_date(economic);floor:=lawful;
 vectors:=cp7_credit.consumer_source_vectors_v1(ch.id);
 credit:=cp7_credit.credit_account_facts_v1(ch.credit_account_id);
 if selection->>'target_sale_id'is not null then
  target_ar:=cp7_credit.consumer_invoice_ar_source_v1((selection->>'target_sale_id')::uuid);
  if physical<(select sale_date from erp.sales_headers where id=(selection->>'target_sale_id')::uuid)then
   raise exception 'CP7_CREDIT_CONSUMER_PHYSICAL_BEFORE_TARGET';end if;
  floor:=greatest(floor,(target_ar#>>'{financial_source,transaction_date}')::date);
 end if;
 if selection->>'cash_account_id'is not null then
  cash:=cp7_credit.cash_account_facts_v1((selection->>'cash_account_id')::uuid);
  if p_payload->>'action'='UNDO'then
   -- Restoring the same immutable cash account is mandatory; current cash
   -- eligibility/Native dated cash guards remain mandatory as well.
   if (cp7_credit.consumer_event_data_v1((selection->>'restores_event_id')::uuid)->>'other_account_id')
    is distinct from cash#>>'{account,id}'then raise exception 'CP7_CREDIT_CONSUMER_ORIGINAL_CASH_MAPPING_CHANGED';end if;
  end if;
 end if;
 if amount>0 then
  book_plan:=cp7_credit.consumer_positive_credit_book_bound_v1(vectors->'recognition',vectors->'consumptions',amount,physical,lawful,floor,statement_timestamp());
  book:=(book_plan->>'minimum_source_book_date')::date;
 else
  select *into strict old from cp7_credit.consumption_events where id=(selection->>'restores_event_id')::uuid;
  if economic<old.economic_date then raise exception 'CP7_CREDIT_CONSUMER_UNDO_BEFORE_ORIGINAL';end if;
  if exists(select 1 from cp7_credit.consumer_operations_v1 o where o.id=old.id and physical<o.physical_at)
   or exists(select 1 from cp7_credit.initial_refund_operations o where o.id=old.id and physical<o.physical_at)then
   raise exception 'CP7_CREDIT_CONSUMER_UNDO_BEFORE_ORIGINAL_PHYSICAL';end if;
  book:=greatest(floor,old.transaction_date);
  if book>erp._cp3_business_date(statement_timestamp())then raise exception 'CP7_CREDIT_CONSUMER_UNDO_BOOK_IN_FUTURE';end if;
  book_plan:=jsonb_build_object('basis','EXACT_ORIGINAL_AND_CURRENT_NATIVE_LAWFUL_INVERSE',
   'original_event_id',old.id,'original_economic_date',old.economic_date,'original_book_date',old.transaction_date,
   'lawful_book_date',lawful,'source_floor',floor);
 end if;
 book_plan:=book_plan||jsonb_build_object('selected_book_date',book);
 added:=jsonb_build_object('id','consumer-review:'||cp7_credit.pg_jsonb_sha256(p_payload-'quote_sha256'),
  'amount',cp7_credit.cent_text(amount::cp7_credit.cent_amount),'economic_date',economic::text,'transaction_date',book::text,
  'source_sha256',cp7_credit.pg_jsonb_sha256(p_payload-'quote_sha256'));
 after_capacity:=ow04_pure_kernel.credit_capacity_v1(vectors->'recognition',
  (vectors->'consumptions')||jsonb_build_array(added),economic::text,book::text);
 if after_capacity->'source_prefixes_nonnegative'is distinct from'true'::jsonb
  or(after_capacity->>'current_balance')::numeric<0 then raise exception 'CP7_CREDIT_CONSUMER_FINAL_JOINT_CAPACITY_NEGATIVE';end if;
 if selection->>'target_sale_id'is not null then
  target_input:=cp7_credit.initial_ordinal_input_v1((selection->>'target_sale_id')::uuid);
  target_input:=jsonb_set(target_input,'{base_events}',(target_input->'base_events')||jsonb_build_array(added||jsonb_build_object('kind','FUNDING')));
  target_result:=ow04_ordinal_wrapper.reconcile_v1(target_input);
  if target_result->'arithmetic_supported'is distinct from'true'::jsonb
   or exists(select 1 from jsonb_array_elements(target_result->'families')f where(f->>'has_reconciliation_effect')::boolean)then
   raise exception 'CP7_CREDIT_CONSUMER_FAMILY_ADJUSTMENT_REVIEW_REQUIRED';end if;
  target_profile:=p_locked#>array['sources',selection->>'target_sale_id','profile'];
 end if;
 for sale in select value from jsonb_array_elements_text(p_locked#>'{graph,sale_ids}')order by value loop
  versions:=versions||jsonb_build_object(sale,p_locked#>>array['sources',sale,'native','sale','row_version']);
  before_native:=before_native||jsonb_build_object(sale,cp7_credit.consumer_native_invariant_v1(sale::uuid));
 end loop;
 source_profile:=p_locked#>array['sources',selection->>'source_sale_id','profile'];
 projection:=jsonb_build_object('contract_version','ow04.consumer-projection.v1','selection',selection,
  'economic_date',economic,'transaction_date',book,'physical_at',cp7_credit.refund_physical_text(physical),
  'vectors_before',vectors,'signed_added_consumption',added,'source_capacity_after',after_capacity,
  'credit_account',credit,'cash_account',cash,'target_ar_source',target_ar,'book_manifest',book_plan,
  'target_ordinal_after',target_result,'before_source_profile',source_profile,'before_target_profile',target_profile,
  'expected_versions',versions,'before_native',before_native,'locked_lot_ids',p_locked->'locked_lot_ids',
  'locked_hpp_ids',p_locked->'locked_hpp_ids','cash_balance_before',p_locked->'cash_balance_before');
 return projection;
end $$;

do $private$declare sig text;begin
 foreach sig in array array['consumer_selection_v1(jsonb)','consumer_joined_graph_v1(uuid,uuid)',
 'consumer_native_invariant_v1(uuid)','consumer_source_vectors_v1(uuid)','consumer_capture_sources_v1(jsonb)',
 'consumer_journal_ids_v1(uuid[])','consumer_cash_balance_v1(uuid)','consumer_lock_sources_v1(jsonb)','consumer_projection_v1(jsonb,jsonb)']loop
  execute'alter function cp7_credit.'||sig||' owner to postgres';
  execute'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
 end loop;
end $private$;
