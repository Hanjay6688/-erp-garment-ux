-- Bounded READ-ONLY refusal proof on the actual Native payment-correction
-- route. It does not admit a successful recognized-source correction.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

create function cp7_credit.consumer_payment_restatement_preflight_v1(p jsonb,p_request uuid,p_expected text)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare sale uuid:=(p->>'sale_id')::uuid;original erp.sales_payments;j erp.journal_entries;
 authority jsonb;graph jsonb;sources jsonb;sales uuid[];journals uuid[];lots uuid[];hpp uuid[];
 fresh_lots uuid[];fresh_hpp uuid[];period jsonb;before_input jsonb;before_result jsonb;
 proposed jsonb;events jsonb;old_event jsonb;replacement_event jsonb;result jsonb;family jsonb;
 amount numeric;binding text;ar uuid;
begin
 if not cp7_credit.has_ow04_participation_v1(sale)then return;end if;
 perform cp7_credit.consumer_payload_kind_v1(jsonb_build_object('action','APPLY'));
 authority:=cp7_payment_correction.access_now();
 perform cp7_payment_correction.validate(p);
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'
  or current_setting('transaction_isolation')<>'read committed'
  or not exists(select 1 from cp7_payment_correction.context c where c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current()and c.actor=auth.uid()and c.request_id=p_request
   and c.payload=p and c.expected_version=p_expected)
  or exists(select 1 from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception using errcode='42501',message='CP7_CREDIT_RESTATEMENT_ACTUAL_PENDING_CORRECTION_REQUIRED';end if;
 -- Native apply already owns FG and its original source locks. Complete the
 -- bidirectional historical application graph before taking period SHARE.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_payment_correction.access_now()is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_RESTATEMENT_ACCESS_CHANGED';end if;
 graph:=cp7_credit.consumer_joined_graph_v1(sale,null);
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
 perform 1 from erp.customers where id=(graph->>'customer_id')::uuid for share;
 journals:=cp7_credit.consumer_journal_ids_v1(sales);
 perform 1 from erp.journal_entries where id=any(journals)order by id for update;
 perform 1 from erp.journal_lines where journal_entry_id=any(journals)order by id for share;
 if cp7_credit.consumer_journal_ids_v1(sales)is distinct from journals then
  raise exception 'CP7_CREDIT_RESTATEMENT_JOURNAL_LOCK_SET_CHANGED';end if;
 if cp7_payment_correction.access_now()is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_RESTATEMENT_ACCESS_CHANGED';end if;
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
 if(fresh_lots,fresh_hpp)is distinct from(lots,hpp)then raise exception 'CP7_CREDIT_RESTATEMENT_HPP_LOCK_SET_CHANGED';end if;
 if exists(select 1 from erp.opening_lot_hpp_gl_state where lot_id=any(lots))
  or exists(select 1 from erp.fg_lots where id=any(lots)and(po_id is not null or lot_origin='CONVERSION'))then
  raise exception 'CP7_CREDIT_RESTATEMENT_EXTENDED_HPP_ADAPTER_REQUIRED';end if;
 perform 1 from erp.cash_accounts where id in(select cash_account_id from erp.sales_payments where sale_id=any(sales))order by id for share;
 perform 1 from erp.chart_accounts where id in(select account_id from erp.journal_lines where journal_entry_id=any(journals))order by id for share;
 perform 1 from erp.accounting_account_mappings order by mapping_key for share;
 if cp7_payment_correction.access_now()is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_RESTATEMENT_ACCESS_CHANGED';end if;
 if cp7_credit.consumer_joined_graph_v1(sale,null)is distinct from graph then
  raise exception 'CP7_CREDIT_RESTATEMENT_GRAPH_LOCK_SET_CHANGED';end if;
 sources:=cp7_credit.consumer_capture_sources_v1(graph);
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 select to_jsonb(c)into strict period from erp.accounting_period_control c where singleton_id=1;
 if cp7_payment_correction.access_now()is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_RESTATEMENT_ACCESS_CHANGED';end if;
 if cp7_credit.consumer_capture_sources_v1(graph)is distinct from sources
  or cp7_credit.consumer_joined_graph_v1(sale,null)is distinct from graph
  or(sources#>>array[sale::text,'native','sale','row_version'])is distinct from p_expected
  or cp7_sales.review_token(sale)is distinct from p->>'review_token'then
  raise exception 'CP7_CREDIT_RESTATEMENT_SOURCE_OR_REVIEW_CHANGED';end if;
 perform cp7_credit.consumer_source_undone_v1(sale);
 select *into strict original from erp.sales_payments where id=(p->>'payment_id')::uuid and sale_id=sale;
 amount:=(p#>>'{replacement,amount}')::numeric;
 -- Exact bounded timing proof: same original cash/date, lower positive cents,
 -- open original book pair. The real Native inverse+neutral cancel at its
 -- current pair; effective inverse plus replacement give this exact net
 -- FUNDING vector at the original pair. No actual journal is reinterpreted.
 if original.status<>'POSTED'or original.replaces_payment_id is not null
  or original.cash_account_id is null or original.payment_method not in('CASH','BANK_TRANSFER')
  or amount<=0 or amount>=original.amount or amount*100<>trunc(amount*100)
  or(p#>>'{replacement,payment_date}')::timestamptz is distinct from original.payment_date
  or(p#>>'{replacement,cash_account_id}')::uuid is distinct from original.cash_account_id
  or p#>>'{replacement,payment_method}'is distinct from original.payment_method
  or p#>>'{replacement,payment_number}'is distinct from original.payment_number
  or exists(select 1 from cp7_payment_correction.links where original_id=original.id or replacement_id=original.id)
  or exists(select 1 from cp7_credit.source_operation_materializations_v1 where sale_id=sale)
  or(select count(*)from cp7_credit.cohorts where source_sale_id=sale)<>1 then
  raise exception 'CP7_CREDIT_RESTATEMENT_FULL_CORRECTION_ADAPTER_REQUIRED';end if;
 select *into strict j from erp.journal_entries where source_type='SALES_PAYMENT'and source_id=original.id and reversal_of_id is null;
 if j.status<>'POSTED'or j.economic_date is distinct from(original.payment_date at time zone'Asia/Jakarta')::date
  or j.transaction_date is distinct from j.economic_date
  or erp.resolve_accounting_transaction_date(j.economic_date)is distinct from j.transaction_date then
  raise exception 'CP7_CREDIT_RESTATEMENT_CLOSED_DATE_ADAPTER_REQUIRED';end if;
 before_input:=cp7_credit.initial_ordinal_input_v1(sale);before_result:=ow04_ordinal_wrapper.reconcile_v1(before_input);
 if not(before_result->>'arithmetic_supported')::boolean
  or exists(select 1 from jsonb_array_elements(before_result->'families')f where(f->>'has_reconciliation_effect')::boolean)then
  raise exception 'CP7_CREDIT_RESTATEMENT_BEFORE_PROFILE_UNRECONCILED';end if;
 select x into strict old_event from jsonb_array_elements(before_input->'base_events')x where x->>'id'='journal:'||j.id::text;
 ar:=(cp7_credit.consumer_invoice_ar_source_v1(sale)->>'account_id')::uuid;
 if old_event->>'kind'is distinct from'FUNDING'or(old_event->>'amount')::numeric is distinct from original.amount
  or old_event->>'source_sha256'is distinct from ow04_source_proposal.sha(ow04_source_proposal.financial_journal_payload(j.id,ar))then
  raise exception 'CP7_CREDIT_RESTATEMENT_ACTUAL_PAYMENT_VECTOR_CHANGED';end if;
 binding:=cp7_credit.pg_jsonb_sha256(jsonb_build_object('request_id',p_request,'payload',p,'expected_version',p_expected,
  'authority',authority,'locked_sources',sources,'graph',graph,'period',period,'original_payment',to_jsonb(original),
  'original_journal',cp7_credit.materialized_journal_payload(j.id)));
 replacement_event:=old_event||jsonb_build_object('id','PROJECTION_ONLY:payment-correction:'||p_request::text,
  'amount',cp7_credit.cent_text(amount::cp7_credit.cent_amount),'source_sha256',binding);
 select jsonb_agg(event order by event->>'id'collate"C")into events from(
  select x as event from jsonb_array_elements(before_input->'base_events')x where x->>'id'<>old_event->>'id'
  union all select replacement_event)projected_events;
 proposed:=jsonb_set(before_input,'{base_events}',events);result:=ow04_ordinal_wrapper.reconcile_v1(proposed);
 for family in select f from jsonb_array_elements(result->'families')f
  where f#>>'{target_full_prefix_capacity,source_prefixes_nonnegative}'='false'loop
  raise exception 'CP7_CREDIT_RESTATEMENT_HISTORICAL_CAPACITY_NEGATIVE'using detail=jsonb_build_object(
   'contract_version','ow04.bound-payment-restatement-refusal.v1','actual_pending_native_correction',true,
   'request_id',p_request,'sale_id',sale,'original_payment_id',original.id,'binding_sha256',binding,
   'before_input_sha256',before_result->>'input_sha256','projected_input_sha256',result->>'input_sha256',
   'original_amount',cp7_credit.cent_text(original.amount),'replacement_amount',cp7_credit.cent_text(amount::cp7_credit.cent_amount),
   'family',family,'actual_signed_consumptions',(select f->'consumptions'from jsonb_array_elements(proposed->'families')f
    where f->>'family_id'=family#>>'{registration,family_id}'),
   'Native_financial_effects_started',false,'successful_correction_qualified',false)::text;
 end loop;
 -- This new route proves a specific unsafe intent, not successful general
 -- restatement. Keep the original fail-closed execution boundary explicit.
 raise exception 'CP7_CREDIT_RESTATEMENT_FULL_CORRECTION_ADAPTER_REQUIRED';
end $$;
alter function cp7_credit.consumer_payment_restatement_preflight_v1(jsonb,uuid,text)owner to postgres;
revoke all on function cp7_credit.consumer_payment_restatement_preflight_v1(jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write;
