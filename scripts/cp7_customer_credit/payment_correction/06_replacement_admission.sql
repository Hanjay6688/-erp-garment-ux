do $not_an_installer$begin raise exception 'OW04_PAYMENT_SOURCE_REQUIRES_COMPLETE_OWNING_COMPOSITION';end $not_an_installer$;

-- Admission data for this exact pending replacement, never actual posted I.
-- The original Native effective-paid value and all ordinary overpayment
-- refusals remain intact. Actual positive I is posted only after Native P.
create function cp7_credit.payment_replacement_admitted_v1(p_payment uuid,p_total numeric,p_paid numeric,p_amount numeric)returns boolean
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.payment_source_context_v1;w cp7_credit.source_operation_work_v1;p erp.sales_payments;
 old_event jsonb;new_event jsonb;events jsonb;expected_input jsonb;fresh jsonb;
 projected_i numeric;actual_i numeric;actual_p numeric;actual_u numeric;projected_effective numeric;
begin
 select *into c from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if not found then return false;end if;
 perform cp7_credit.payment_source_assert_pending_v1(c.operation_id);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=c.operation_id;
 select *into strict p from erp.sales_payments where id=p_payment;
 if c.phase<>'REPLACEMENT_ENTERED'or c.replacement_id is distinct from p.id
  or p.sale_id<>w.sale_id or to_jsonb(p)is distinct from c.replacement_draft
  or p.status<>'DRAFT'or p.amount is distinct from p_amount
  or p_amount is distinct from(w.payload#>>'{replacement,amount}')::numeric
  or p_total is distinct from erp.sale_net_total(w.sale_id)
  or p_paid is distinct from cp7_credit.current_effective_paid(w.sale_id)then
  raise exception 'CP7_CREDIT_PAYMENT_REPLACEMENT_ADMISSION_CHANGED';end if;
 -- Reprove the actual inverse/time-pair/DRAFT boundary and unchanged old I/U.
 -- This function deliberately leaves that actual intermediate value intact.
 perform cp7_credit.payment_intermediate_adjustment_v1(w.sale_id);
 select x into strict old_event from jsonb_array_elements(w.before_ordinal_input->'base_events')x
  where x->>'id'='journal:'||(select j.id::text from erp.journal_entries j
   where j.source_type='SALES_PAYMENT'and j.source_id=w.source_id and j.reversal_of_id is null);
 select x into strict new_event from jsonb_array_elements(c.projected_input->'base_events')x
  where x->>'id'='PROJECTION_ONLY:payment-correction:'||w.request_id::text;
 if old_event->>'kind'<>'FUNDING'or new_event-'source_sha256'is distinct from
  (old_event||jsonb_build_object('id','PROJECTION_ONLY:payment-correction:'||w.request_id::text,
   'amount',cp7_credit.cent_text(p_amount::cp7_credit.cent_amount)))-'source_sha256'
  or coalesce(new_event->>'source_sha256','')!~'^[0-9a-f]{64}$'then
  raise exception 'CP7_CREDIT_PAYMENT_PROJECTED_REPLACEMENT_CHANGED';end if;
 select jsonb_agg(event order by event->>'id'collate"C")into events from(
  select x as event from jsonb_array_elements(w.before_ordinal_input->'base_events')x where x->>'id'<>old_event->>'id'
  union all select new_event)projected_events;
 expected_input:=jsonb_set(w.before_ordinal_input,'{base_events}',events);
 fresh:=ow04_ordinal_wrapper.reconcile_v1(expected_input);
 if expected_input is distinct from c.projected_input or fresh is distinct from c.projected_result
  or not coalesce((fresh->>'arithmetic_supported')::boolean,false)
  or jsonb_array_length(fresh->'families')<>1
  or exists(select 1 from jsonb_array_elements(fresh->'families')f where
   coalesce((f->>'needs_cohort_configuration')::boolean,false)
   or f#>>'{target_full_prefix_capacity,source_prefixes_nonnegative}'is distinct from'true'
   or not exists(select 1 from cp7_credit.cohorts ch where ch.source_sale_id=w.sale_id
    and ch.family_id=(f#>>'{registration,family_id}')::uuid))then
  raise exception 'CP7_CREDIT_PAYMENT_PROJECTED_CAPACITY_NOT_ADMITTED';end if;
 select coalesce(sum((r->>'amount')::numeric),0)into actual_i
  from jsonb_array_elements(expected_input->'families')f cross join lateral jsonb_array_elements(f->'retained_recognition')r;
 select actual_i+coalesce(sum((x->>'amount')::numeric),0)into projected_i
  from jsonb_array_elements(fresh->'families')f cross join lateral jsonb_array_elements(f->'reconciliation_components')x;
 actual_u:=(w.before_financial_profile->>'U')::numeric;
 select coalesce(sum(amount),0)into actual_p from erp.sales_payments where sale_id=w.sale_id and status='POSTED';
 if actual_i is distinct from(w.before_financial_profile->>'I')::numeric
  or actual_u is distinct from 0::numeric or projected_i<0
  or p_paid is distinct from actual_p+actual_u-actual_i
  or actual_p+p_amount>coalesce((select sum(line_total)from erp.sales_items where sale_id=w.sale_id),0)then
  raise exception 'CP7_CREDIT_PAYMENT_ACTUAL_AND_PROJECTED_CAPACITY_CHANGED';end if;
 projected_effective:=actual_p+p_amount+actual_u-projected_i;
 return projected_effective>=0 and projected_effective<=p_total;
end $$;
