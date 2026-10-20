do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;

create function cp7_credit.initial_ordinal_input_v1(p_sale uuid,p_pending_plan uuid default null)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare f cp7_credit.return_families;events jsonb;family_events jsonb;families jsonb:='[]';all_return_ids text[]:='{}';retained jsonb;consumers jsonb;
begin
 if p_pending_plan is not null and not exists(select 1 from cp7_credit.initial_return_work w join cp7_credit.execution_context e
  on(e.backend_pid,e.transaction_id,e.actor,e.request_id,e.plan_id)=(w.backend_pid,w.transaction_id,w.actor,w.request_id,w.plan_id)
  where w.backend_pid=pg_backend_pid()and w.transaction_id=txid_current()and w.plan_id=p_pending_plan and w.source_sale_id=p_sale
   and w.phase in('ENTERED','MATERIALIZED'))then raise exception 'CP7_CREDIT_EXACT_PENDING_PLAN_BASELINE_REQUIRED';end if;
 if exists(select 1 from erp.sales_returns r where r.sale_id=p_sale and r.status<>'DRAFT'
  and not exists(select 1 from cp7_credit.return_family_members m where m.return_id=r.id))then raise exception 'CP7_CREDIT_LEGACY_RETURN_ORDER_NOT_QUALIFIED';end if;
 events:=cp7_credit.initial_base_events_v1(p_sale);
 for f in select *from cp7_credit.return_families where family_root_sale_id=p_sale order by family_ordinal loop
  with recursive journals(id)as(
   select j.id from cp7_credit.return_family_members m join erp.journal_entries j on j.source_type='SALES_RETURN'and j.source_id=m.return_id
    where m.family_id=f.id and j.reversal_of_id is null
   union select j.id from journals p join erp.journal_entries j on j.reversal_of_id=p.id or(j.source_type='JOURNAL_REVERSAL'and j.source_id=p.id))
  select coalesce(jsonb_agg(x order by x->>'id'collate"C"),'[]')into family_events from jsonb_array_elements(events)x
   where substring(x->>'id'from 9)::uuid in(select id from journals);
  select all_return_ids||coalesce(array_agg(x->>'id'),'{}')into all_return_ids from jsonb_array_elements(family_events)x;
  select coalesce(jsonb_agg(jsonb_build_object('id','part:'||pp.id::text,'amount',cp7_credit.cent_text(pp.amount),'economic_date',cj.economic_date::text,
   'transaction_date',cj.transaction_date::text,'source_sha256',cp7_credit.pg_jsonb_sha256(jsonb_build_object('part',to_jsonb(pp),'journal_link',to_jsonb(cj))))order by pp.id),'[]')into retained
   from cp7_credit.cohorts ch join cp7_credit.recognition_plans rp on rp.cohort_id=ch.id join cp7_credit.recognition_components cc on cc.plan_id=rp.id
   join cp7_credit.component_parts pp on pp.component_id=cc.id join cp7_credit.component_journals cj on cj.part_id=pp.id
   where ch.family_id=f.id and rp.id is distinct from p_pending_plan;
  select coalesce(jsonb_agg(jsonb_build_object('id','consumption:'||ce.id::text,'amount',cp7_credit.cent_text(ce.amount),'economic_date',ce.economic_date::text,
   'transaction_date',ce.transaction_date::text,'source_sha256',ce.source_sha256)order by ce.id),'[]')into consumers
   from cp7_credit.consumption_events ce join cp7_credit.cohorts ch on ch.id=ce.cohort_id where ch.family_id=f.id;
  families:=families||jsonb_build_array(jsonb_build_object('family_id',f.id,'ordinal',f.family_ordinal::text,'first_return_id',f.first_return_id,
   'registration_sha256',f.source_sha256,'events',family_events,'retained_recognition',retained,'consumptions',consumers));
 end loop;
 select coalesce(jsonb_agg(x order by x->>'id'collate"C"),'[]')into events from jsonb_array_elements(events)x where not(x->>'id'=any(all_return_ids));
 return jsonb_build_object('contract_version','ow04.ordinal-input.v1','family_root_sale_id',p_sale,'base_events',events,'families',families);
end $$;

-- Context-free facts only. This is deliberately STABLE: no auth, GUC,
-- execution_context, volatile collector, current-E call or lock acquisition.
create function cp7_credit.assert_simple_native_base_v1(p_sale uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare h erp.sales_headers;p erp.sales_payments;f erp.sales_payment_posting_facts;rv erp.sales_payment_reversal_facts;j erp.journal_entries;
 x record;ar uuid;gross numeric;expected numeric;n bigint;inverse erp.journal_entries;fact jsonb;
begin
 select *into strict h from erp.sales_headers where id=p_sale;
 if exists(select 1 from cp7_note.revisions where p_sale in(root_sale_id,previous_sale_id,replacement_sale_id))
  or exists(select 1 from cp7_sales_return_correction.links where sale_id=p_sale)
  or exists(select 1 from cp7_payment_correction.links l join erp.sales_payments p0 on p0.id in(l.original_id,l.replacement_id)where p0.sale_id=p_sale)then
  raise exception 'CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED';end if;
 ar:=cp7_credit.account_by_mapping_v1('AR_CUSTOMER');
 select coalesce(sum(line_total),0)into gross from erp.sales_items where sale_id=h.id;
 if gross<0 then raise exception 'CP7_CREDIT_CORRUPT_SALE_TOTAL';end if;
 select count(*)into n from erp.journal_entries where source_type='SALE'and source_id=h.id and reversal_of_id is null;
 if n=0 then perform ow04_source_proposal.sale_absence_fact_v1(h.id);
 elsif n<>1 then raise exception 'CP7_CREDIT_NATIVE_SALE_JOURNAL_COUNT';
 else
  select *into strict j from erp.journal_entries where source_type='SALE'and source_id=h.id and reversal_of_id is null;
  if j.economic_date<>(h.sale_date at time zone'Asia/Jakarta')::date or j.transaction_date<j.economic_date
   or j.status<>(case when h.status='REVERSED'then'REVERSED'else'POSTED'end)
   or coalesce((select sum(debit-credit)from erp.journal_lines where journal_entry_id=j.id and account_id=ar),0)<>gross
   or(select count(*)from erp.journal_lines where journal_entry_id=j.id and account_id=ar)<>(case when gross=0 then 0 else 1 end)then
   raise exception 'CP7_CREDIT_NATIVE_SALE_AR_OR_PAIR_CHANGED';end if;
 end if;
 for p in select *from erp.sales_payments where sale_id=p_sale and status<>'DRAFT'order by id loop
  select *into strict f from erp.sales_payment_posting_facts where payment_id=p.id;
  select *into strict j from erp.journal_entries where id=f.original_journal_entry_id;
  if p.status not in('POSTED','REVERSED')or p.amount<=0 or p.amount*100<>trunc(p.amount*100)
   or f.sale_id<>p_sale or f.customer_id<>h.customer_id or f.payment_snapshot is distinct from to_jsonb(p)-'status'
   or(f.payment_number,f.payment_date,f.amount,f.cash_account_id,f.replaces_payment_id)is distinct from
    (p.payment_number,p.payment_date,p.amount,p.cash_account_id,p.replaces_payment_id)
   or f.replaces_payment_id is not null or f.predecessor_reversal_journal_id is not null
   or(j.source_type,j.source_id,j.reversal_of_id,j.economic_date,j.transaction_date,j.posting_at)is distinct from
    ('SALES_PAYMENT',p.id,null::uuid,f.journal_economic_date,f.journal_transaction_date,f.journal_posting_at)
   or j.economic_date<>(p.payment_date at time zone'Asia/Jakarta')::date or j.transaction_date<j.economic_date
   or j.status<>(case when p.status='REVERSED'then'REVERSED'else'POSTED'end)
   or f.lineage_sha256 is distinct from ow04_source_proposal.native_sha(jsonb_build_array(f.payment_id,f.sale_id,f.customer_id,
    f.payment_number,f.payment_date,f.amount,f.cash_account_id,f.original_journal_entry_id,f.journal_economic_date,f.journal_transaction_date,
    f.journal_posting_at,f.replaces_payment_id,f.predecessor_reversal_journal_id,f.payment_snapshot))
   or(select count(*)from erp.journal_lines where journal_entry_id=j.id and account_id=ar)<>1
   or not exists(select 1 from erp.journal_lines where journal_entry_id=j.id and account_id=ar and customer_id=h.customer_id and debit=0 and credit=p.amount
    and vendor_id is null and contractor_id is null and po_id is null and product_id is null)then
   raise exception 'CP7_CREDIT_NATIVE_PAYMENT_FACT_CHANGED';end if;
  if p.cash_account_id is null then
   if p.payment_method<>'OPENING_ADVANCE'or not exists(select 1 from erp.initial_import_prepayment_payments l
    join erp.initial_import_prepayments a on a.id=l.advance_id where l.payment_id=p.id and l.sales_payment_id=p.id
     and l.payment_snapshot=to_jsonb(p)-'status'and a.party_type='CUSTOMER'and a.party_id=h.customer_id
     and exists(select 1 from erp.journal_lines jl where jl.journal_entry_id=j.id and jl.account_id=a.coa_account_id
      and jl.customer_id=h.customer_id and jl.debit=p.amount and jl.credit=0))then
    raise exception 'CP7_CREDIT_NATIVE_ADVANCE_FUNDING_FACT_CHANGED';end if;
  elsif not exists(select 1 from erp.cash_accounts c join erp.journal_lines jl on jl.account_id=c.coa_account_id
   where c.id=p.cash_account_id and jl.journal_entry_id=j.id and jl.customer_id=h.customer_id and jl.debit=p.amount and jl.credit=0)then
   raise exception 'CP7_CREDIT_NATIVE_CASH_FUNDING_FACT_CHANGED';end if;
  select *into rv from erp.sales_payment_reversal_facts where payment_id=p.id;
  if(p.status='REVERSED')<>(rv.payment_id is not null)then raise exception 'CP7_CREDIT_NATIVE_PAYMENT_REVERSAL_FACT_CHANGED';end if;
  if rv.payment_id is not null then
   select *into strict inverse from erp.journal_entries where id=rv.reversal_journal_entry_id;
   if rv.original_journal_entry_id<>j.id
    or(inverse.source_type,inverse.source_id,inverse.reversal_of_id,inverse.economic_date,inverse.transaction_date,inverse.posting_at)is distinct from
     ('JOURNAL_REVERSAL',j.id,j.id,rv.reversal_economic_date,rv.reversal_transaction_date,rv.reversal_posting_at)
    or rv.lineage_sha256 is distinct from ow04_source_proposal.native_sha(jsonb_build_array(rv.payment_id,rv.original_journal_entry_id,
     rv.reversal_journal_entry_id,rv.reversal_economic_date,rv.reversal_transaction_date,rv.reversal_posting_at))then
    raise exception 'CP7_CREDIT_NATIVE_PAYMENT_REVERSAL_FACT_CHANGED';end if;
  end if;
 end loop;
 for x in select r.id from erp.sales_returns r where r.sale_id=p_sale and r.status<>'DRAFT'order by r.id loop
  perform ow04_source_proposal.verify_return_member_v1(x.id);
 end loop;
 -- All real original/inverse legs must be balanced with the exact inverse
 -- vector and both source floors. Unknown restatement/correction routes refuse.
 for x in select ev from jsonb_array_elements(cp7_credit.initial_base_events_v1(p_sale))ev loop
  select *into strict j from erp.journal_entries where id=substring(x.ev->>'id'from 9)::uuid;
  if j.transaction_date<j.economic_date or not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id
   group by l.journal_entry_id having sum(l.debit)=sum(l.credit)and sum(l.debit)>0)
   or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and(l.debit<0 or l.credit<0
    or l.debit::text in('NaN','Infinity','-Infinity')or l.credit::text in('NaN','Infinity','-Infinity')))
   or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=ar and l.customer_id is distinct from h.customer_id)then
   raise exception 'CP7_CREDIT_NATIVE_BASE_JOURNAL_INVALID';end if;
  select count(*)into n from erp.journal_entries ji where ji.source_type='JOURNAL_REVERSAL'and(ji.source_id=j.id or ji.reversal_of_id=j.id);
  if j.status='REVERSED'and n<>1 or j.status='POSTED'and n<>0 then raise exception 'CP7_CREDIT_NATIVE_INVERSE_COMPLETENESS_REQUIRED';end if;
  if j.source_type='JOURNAL_REVERSAL'then
   select *into strict inverse from erp.journal_entries where id=j.reversal_of_id;
   if j.source_id<>inverse.id or inverse.status<>'REVERSED'or j.economic_date<inverse.economic_date or j.transaction_date<inverse.transaction_date
    or cp7_credit.initial_line_semantics_v1((select jsonb_agg(jsonb_build_object('account_id',l.account_id,'customer_id',l.customer_id,
     'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id,'debit',l.debit,'credit',l.credit))from erp.journal_lines l where l.journal_entry_id=j.id))
     is distinct from cp7_credit.initial_line_semantics_v1((select jsonb_agg(jsonb_build_object('account_id',l.account_id,'customer_id',l.customer_id,
     'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id,'debit',l.credit,'credit',l.debit))from erp.journal_lines l where l.journal_entry_id=inverse.id))then
    raise exception 'CP7_CREDIT_NATIVE_INVERSE_SOURCE_CHANGED';end if;
  end if;
 end loop;
end $$;

create function cp7_credit.assert_current_source_plan_profile(p_sale uuid,p_root uuid,p_leaf uuid,p_actual jsonb)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare ch cp7_credit.cohorts;p cp7_credit.recognition_plans;m cp7_credit.initial_return_materializations;
 events jsonb;ordinal_result jsonb;fresh jsonb;actual_i jsonb;expected_i jsonb;c_events jsonb;capacity jsonb;ce cp7_credit.consumption_events;o cp7_credit.initial_refund_operations;
 j erp.journal_entries;lines jsonb;expected_lines jsonb;n bigint;
begin
 if p_sale<>p_root or p_sale<>p_leaf or p_actual->>'sale_id'<>p_sale::text or p_actual->>'root_sale_id'<>p_root::text
  or p_actual->>'current_leaf_id'<>p_leaf::text
  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)then
  raise exception 'CP7_CREDIT_CURRENT_SOURCE_ROUTE_UNIMPLEMENTED';end if;
 perform cp7_credit.assert_simple_native_base_v1(p_sale);
 events:=cp7_credit.initial_base_events_v1(p_sale);
 ordinal_result:=ow04_ordinal_wrapper.reconcile_v1(cp7_credit.initial_ordinal_input_v1(p_sale));
 if not(ordinal_result->>'arithmetic_supported')::boolean or exists(select 1 from jsonb_array_elements(ordinal_result->'families')f
  where(f->>'has_reconciliation_effect')::boolean)then raise exception 'CP7_CREDIT_CURRENT_ORDINAL_RECONCILIATION_REQUIRED';end if;
 select count(*)into n from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=p_sale;
 if n=0 then
  perform cp7_credit.assert_zero_excess_v1(events);
  if(p_actual->>'I')::numeric<>0 or(p_actual->>'U')::numeric<>0 then raise exception 'CP7_CREDIT_EMPTY_FAMILY_HAS_FINANCIAL_EFFECT';end if;
  return;
 elsif n<>1 then raise exception 'CP7_CREDIT_MULTI_COHORT_RECONCILIATION_UNIMPLEMENTED';end if;
 select c.*into strict ch from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=p_sale;
 select *into strict p from cp7_credit.recognition_plans where id=ch.initial_plan_id;
 select *into strict m from cp7_credit.initial_return_materializations where cohort_id=ch.id and plan_id=p.id;
 if p.plan_kind<>'INITIAL'or exists(select 1 from cp7_credit.recognition_plans where cohort_id=ch.id and id<>p.id)
  or cp7_credit.initial_preserved_source_v1(p_sale,ch.source_return_id)is distinct from m.source_snapshot->'preserved_source'
  or cp7_credit.initial_base_events_v1(p_sale,ch.source_return_id)is distinct from p.before_events then
  raise exception 'CP7_CREDIT_RECOGNIZED_SOURCE_MUTATION_UNIMPLEMENTED';end if;
 perform cp7_credit.assert_zero_excess_v1(p.before_events);
 fresh:=ow04_pure_kernel.recognition_plan_v1(p.before_events,cp7_credit.actual_own_return_events_v1(ch.source_return_id));
 if fresh is distinct from p.kernel_result or fresh is distinct from m.actual_kernel
  or p.net_amount is distinct from(fresh->>'net_current_k')::numeric or p.net_amount<0
  or p.net_amount>(m.projection->>'return_amount')::numeric then raise exception 'CP7_CREDIT_CURRENT_SOURCE_TARGET_CHANGED';end if;
 select coalesce(jsonb_agg(cc.kernel_component order by cc.ordinal),'[]')into actual_i from cp7_credit.recognition_components cc where cc.plan_id=p.id;
 if actual_i is distinct from fresh->'components'or(p_actual->>'I')::numeric<>p.net_amount or(p_actual->>'U')::numeric<>0 then
  raise exception 'CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED';end if;
 -- Current materialized inspector already proves all actual signed part/J
 -- vectors. Only the one explicit initial REFUND consumer is implemented.
 for ce in select *from cp7_credit.consumption_events where cohort_id=ch.id loop
  select *into strict o from cp7_credit.initial_refund_operations where id=ce.id and cohort_id=ch.id;
  if ce.event_kind<>'REFUND'or ce.amount<=0 or ce.amount<>o.full_amount or ce.amount<>p.net_amount
   or ce.restores_event_id is not null or ce.target_sale_id is not null or ce.cash_account_id<>o.cash_account_id
   or m.refund_operation_id is distinct from o.id or o.initial_plan_id<>p.id
   or o.required_book_floor is distinct from(o.book_floor_manifest->>'selected_book_date')::date
   or o.book_floor_manifest is distinct from m.projection->'refund_book_plan'
   or o.book_floor_manifest is distinct from cp7_credit.initial_refund_book_plan_v1(fresh,o.full_amount,o.physical_at,
    (o.book_floor_manifest->>'lawful_book_date')::date,(select transaction_date from erp.journal_entries where id=ch.source_return_journal_id))then
   raise exception 'CP7_CREDIT_CONSUMER_ROUTE_UNIMPLEMENTED';end if;
  select *into strict j from erp.journal_entries where id=ce.journal_id;
  if(j.source_type,j.source_id,j.reversal_of_id,j.economic_date,j.transaction_date,j.status)is distinct from
   ('CP7_CUSTOMER_CREDIT_REFUND',o.id,null::uuid,ce.economic_date,ce.transaction_date,'POSTED')
   or ce.economic_date<>(o.physical_at at time zone'Asia/Jakarta')::date or ce.transaction_date<o.required_book_floor then
   raise exception 'CP7_CREDIT_REFUND_ACTUAL_SOURCE_CHANGED';end if;
  expected_lines:=cp7_credit.initial_refund_lines(ch.credit_account_id,(o.cash_account_snapshot#>>'{account,id}')::uuid,ch.customer_id,ce.amount);
  select jsonb_agg(jsonb_build_object('account_id',l.account_id,'customer_id',l.customer_id,'description',l.description,'debit',l.debit,'credit',l.credit)
   order by case when l.account_id=ch.credit_account_id then 0 else 1 end,l.id)into lines from erp.journal_lines l where l.journal_entry_id=j.id;
  if lines is distinct from expected_lines or ce.lines_sha256_pg is distinct from cp7_credit.verify_initial_refund_journal(o.id,j.id,ce.transaction_date)
   or ce.source_sha256 is distinct from cp7_credit.pg_jsonb_sha256(to_jsonb(o))
   or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and(l.vendor_id is not null or l.contractor_id is not null or l.po_id is not null or l.product_id is not null))then
   raise exception 'CP7_CREDIT_REFUND_ACTUAL_LINES_CHANGED';end if;
 end loop;
 if(select count(*)from cp7_credit.consumption_events where cohort_id=ch.id)>1 then raise exception 'CP7_CREDIT_SECOND_CONSUMPTION_UNIMPLEMENTED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',consumer.id::text,'amount',cp7_credit.cent_text(consumer.amount),'economic_date',consumer.economic_date::text,
  'transaction_date',consumer.transaction_date::text,'source_sha256',consumer.source_sha256)order by consumer.id),'[]')into c_events from cp7_credit.consumption_events consumer where consumer.cohort_id=ch.id;
 capacity:=ow04_pure_kernel.credit_capacity_v1(cp7_credit.component_movements_v1(fresh),c_events,
  (select min((x->>'economic_date')::date)::text from jsonb_array_elements(fresh->'components')x),
  (select min((x->>'transaction_date')::date)::text from jsonb_array_elements(fresh->'components')x));
 if not(capacity->>'source_prefixes_nonnegative')::boolean then raise exception 'CP7_CREDIT_CURRENT_JOINT_CAPACITY_NEGATIVE';end if;
end $$;

create function cp7_credit.assert_financial_materialization_provenance(p_actual jsonb)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare marker_id uuid;f cp7_credit.financial_materializations;m cp7_credit.initial_return_materializations;o cp7_credit.initial_refund_operations;
begin
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

create function cp7_credit.current_effective_paid(p_sale uuid)returns numeric
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare paid numeric;adjustment numeric;
begin
 select coalesce(sum(amount),0)into paid from erp.sales_payments where sale_id=p_sale and status='POSTED';
 adjustment:=erp._cp7_current_credit_adjustment(p_sale);
 if paid+adjustment<0 then raise exception 'CP7_CREDIT_NEGATIVE_EFFECTIVE_PAID';end if;
 return paid+adjustment;
end $$;
