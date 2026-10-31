create function cp7_credit_correction_de.input_without_own_v1(p_operation uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_correction_de.work_v1;answer jsonb;f jsonb;families jsonb:='[]';retained jsonb;excluded text[];begin
 perform cp7_credit_correction_de.assert_work_v1();select *into strict w from cp7_credit_correction_de.work_v1 where operation_id=p_operation;
 if w.phase<>'RECONCILING'then raise exception 'CP7_CREDIT_DE_RECONCILING_REQUIRED';end if;
 answer:=cp7_credit.initial_ordinal_input_v1(w.sale_id);
 select coalesce(array_agg('part:'||q.id::text),'{}')into excluded from cp7_credit_correction_de.plans_v1 s
  join cp7_credit.recognition_components c on c.plan_id=s.plan_id join cp7_credit.component_parts q on q.component_id=c.id where s.operation_id=w.operation_id;
 for f in select value from jsonb_array_elements(answer->'families')loop
  select coalesce(jsonb_agg(v order by v->>'id'collate"C"),'[]')into retained from jsonb_array_elements(f->'retained_recognition')v where not(v->>'id'=any(excluded));
  families:=families||jsonb_build_array(jsonb_set(f,'{retained_recognition}',retained));
 end loop;return jsonb_set(answer,'{families}',families);
end $$;
create function cp7_credit_correction_de.assert_plan_set_v1(p_operation uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare w cp7_credit_correction_de.work_v1;entry jsonb;p cp7_credit.recognition_plans;k jsonb;f jsonb;s cp7_credit_correction_de.plans_v1;
 actual jsonb;x jsonb;support_phase text;fresh jsonb;r record;account jsonb;begin
 perform cp7_credit_correction_de.assert_work_v1();select *into strict w from cp7_credit_correction_de.work_v1 where operation_id=p_operation;
 if w.phase<>'RECONCILING'or cp7_credit.source_native_snapshot_v1(w.sale_id)is distinct from w.actual_source
  or cp7_credit_correction_de.input_without_own_v1(w.operation_id)is distinct from w.actual_input then raise exception 'CP7_CREDIT_DE_RECONCILIATION_SOURCE_CHANGED';end if;
 fresh:=ow04_ordinal_wrapper.reconcile_v1(w.actual_input);
 if fresh is distinct from w.actual_result or fresh->'arithmetic_supported'is distinct from'true'::jsonb then raise exception 'CP7_CREDIT_DE_ACTUAL_KERNEL_CHANGED';end if;
 if(select coalesce(jsonb_agg(plan_row.id order by plan_row.id),'[]')from cp7_credit.recognition_plans plan_row where plan_row.actor=w.actor and plan_row.request_id=w.request_id)is distinct from
  (select coalesce(jsonb_agg((e->>'plan_id')::uuid order by(e->>'plan_id')::uuid),'[]')from jsonb_array_elements(w.manifest)e)
  or(select coalesce(jsonb_agg(side_row.plan_id order by side_row.plan_id),'[]')from cp7_credit_correction_de.plans_v1 side_row where side_row.operation_id=w.operation_id)is distinct from
  (select coalesce(jsonb_agg((e->>'plan_id')::uuid order by(e->>'plan_id')::uuid),'[]')from jsonb_array_elements(w.manifest)e)then raise exception 'CP7_CREDIT_DE_PLAN_SET_CHANGED';end if;
 for entry in select value from jsonb_array_elements(w.manifest)loop
  select *into strict p from cp7_credit.recognition_plans where id=(entry->>'plan_id')::uuid;
  select *into strict s from cp7_credit_correction_de.plans_v1 where plan_id=p.id;
  select v into strict f from jsonb_array_elements(fresh->'families')v where v#>>'{registration,family_id}'=entry->>'family_id';
  k:=cp7_credit.source_adjustment_kernel_v1(f);
  if s.canonical is distinct from k or p.kernel_result is distinct from k
   or(p.plan_kind,p.owning_action,p.actor,p.request_id,p.request_ordinal,p.family_root_sale_id,p.payload_sha256,p.review_sha256,p.cohort_id)is distinct from
    ('ADJUSTMENT','RETURN_CORRECT',w.actor,w.request_id,(entry->>'request_ordinal')::int,w.sale_id,cp7_credit.pg_jsonb_sha256(w.payload),w.review->>'review_token',(entry->>'cohort_id')::uuid)
   or p.net_amount is distinct from(k->>'net_current_k')::numeric or p.net_amount<=0
   or p.before_events is distinct from k->'before_events'or p.added_events is distinct from k->'added_events'
   or p.before_source_sha256 is distinct from k->>'before_source_sha256'or p.after_source_sha256 is distinct from k->>'after_source_sha256'
   or p.support_sha256_pg is distinct from cp7_credit.pg_jsonb_sha256(k->'support')or p.components_sha256_pg is distinct from cp7_credit.pg_jsonb_sha256(k->'components')
   or p.parts_sha256_pg is distinct from cp7_credit.pg_jsonb_sha256(entry->'parts')or p.expected_part_count<>jsonb_array_length(entry->'parts')
   or p.expected_component_count<>jsonb_array_length(entry->'components')then raise exception 'CP7_CREDIT_DE_CANONICAL_PLAN_CHANGED';end if;
  select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'ordinal',c.ordinal,'component',c.kernel_component)order by c.ordinal),'[]')into actual from cp7_credit.recognition_components c where c.plan_id=p.id;
  if actual is distinct from entry->'components'or exists(select 1 from cp7_credit.recognition_components c where c.plan_id=p.id and(
   c.kernel_component is distinct from k->'components'->(c.ordinal-1)or c.component_sha256_pg is distinct from cp7_credit.pg_jsonb_sha256(c.kernel_component)
   or c.kernel_component is distinct from jsonb_build_object('amount',cp7_credit.cent_text(c.amount),'economic_date',c.economic_date::text,
    'transaction_date',c.transaction_date::text,'previous_economic_date',c.previous_economic_date::text,'previous_transaction_date',c.previous_transaction_date::text,'corners',c.corners)
   or c.amount<=0))then raise exception 'CP7_CREDIT_DE_COMPONENT_SET_CHANGED';end if;
  select coalesce(jsonb_agg(jsonb_build_object('id',q.id,'component_id',q.component_id,'ordinal',q.ordinal,'amount',cp7_credit.cent_text(q.amount))order by c.ordinal,q.ordinal),'[]')into actual
   from cp7_credit.component_parts q join cp7_credit.recognition_components c on c.id=q.component_id where c.plan_id=p.id;
  if actual is distinct from entry->'parts'or exists(select 1 from cp7_credit.recognition_components c left join cp7_credit.component_parts q on q.component_id=c.id
   where c.plan_id=p.id group by c.id,c.amount having count(q.id)::numeric<>ceil(abs(c.amount)/cp7_credit.native_journal_cent_max())or sum(q.amount)<>c.amount)
   or exists(select 1 from cp7_credit.component_parts q join cp7_credit.recognition_components c on c.id=q.component_id where c.plan_id=p.id
    and(q.ordinal>ceil(c.amount/cp7_credit.native_journal_cent_max())or q.amount is distinct from least(cp7_credit.native_journal_cent_max(),c.amount-(q.ordinal-1)*cp7_credit.native_journal_cent_max())))then
   raise exception 'CP7_CREDIT_DE_PART_SET_CHANGED';end if;
  foreach support_phase in array array['BEFORE','ADDED']loop
   select coalesce(jsonb_agg(jsonb_build_object('id',z.event_id,'kind',z.kind,'amount',cp7_credit.cent_text(z.amount),'economic_date',z.economic_date::text,
    'transaction_date',z.transaction_date::text,'source_sha256',z.source_sha256)order by z.event_id collate"C"),'[]')into actual from cp7_credit.plan_support_events z where z.plan_id=p.id and z.phase=support_phase;
   if actual is distinct from(case when support_phase='BEFORE'then k->'before_events'else k->'added_events'end)then raise exception 'CP7_CREDIT_DE_SUPPORT_SET_CHANGED';end if;
  end loop;
  if exists(select 1 from cp7_credit.plan_support_events z join cp7_credit.cohorts c on c.id=p.cohort_id where z.plan_id=p.id and(z.event_id is distinct from'journal:'||z.journal_id::text
   or z.source_fact_snapshot is distinct from ow04_source_proposal.financial_journal_payload(z.journal_id,c.ar_account_id)
   or z.source_sha256 is distinct from ow04_source_proposal.sha(z.source_fact_snapshot)))then raise exception 'CP7_CREDIT_DE_SUPPORT_ACTUAL_SOURCE_CHANGED';end if;
  select cp7_credit.credit_account_facts_v1(c.credit_account_id)into strict account from cp7_credit.cohorts c where c.id=p.cohort_id;
  if not exists(select 1 from cp7_credit.cohorts c where c.id=p.cohort_id and c.family_id=s.family_id
   and account->'account'=c.credit_account_snapshot->'account'and c.ar_account_id=cp7_credit.account_by_mapping_v1('AR_CUSTOMER')
   and c.source_ar_snapshot=(select to_jsonb(a)from erp.chart_accounts a where a.id=c.ar_account_id))then raise exception 'CP7_CREDIT_DE_ACCOUNT_CHANGED';end if;
 end loop;
 -- Every old real financial object remains exact; no erase/recreate/adopt.
 for x in select value from jsonb_array_elements(w.before_profile->'actual_objects')where value->>'object_kind'='PART_JOURNAL'loop
  if not exists(select 1 from cp7_credit.component_journals j where j.part_id=(x->>'object_id')::uuid and
   x=cp7_credit.materialized_fact('PART_JOURNAL',j.part_id,jsonb_build_object('link',to_jsonb(j),'actual',cp7_credit.materialized_journal_payload(j.journal_id))))then
   raise exception 'CP7_CREDIT_DE_RETAINED_PART_JOURNAL_CHANGED';end if;
 end loop;
 for r in select q.id,o.journal_id,z.journal_snapshot,z.journal_link,to_jsonb(o)actual_link from cp7_credit_correction_de.plans_v1 side_row
  join cp7_credit.recognition_components c on c.plan_id=side_row.plan_id join cp7_credit.component_parts q on q.component_id=c.id
  left join cp7_credit.component_journals o on o.part_id=q.id left join cp7_credit_correction_de.parts_v1 z on z.part_id=q.id where side_row.operation_id=w.operation_id loop
  if r.journal_id is null then
   if r.journal_snapshot is not null or exists(select 1 from erp.journal_entries where source_type='CP7_CUSTOMER_CREDIT_RECOGNITION'and source_id=r.id)then raise exception 'CP7_CREDIT_DE_ORPHAN_PART';end if;
  else
   perform cp7_credit.assert_source_adjustment_part_journal_v1(r.id);
   if r.journal_snapshot is distinct from cp7_credit.materialized_journal_payload(r.journal_id)or r.journal_link is distinct from r.actual_link then raise exception 'CP7_CREDIT_DE_PART_SEAL_CHANGED';end if;
  end if;
 end loop;
end $$;

create function cp7_credit_correction_de.assert_bound_post_v1(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns void
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_correction_de.work_v1;s cp7_credit_correction_de.posting_v1;begin
 perform cp7_credit_correction_de.assert_work_v1();select *into strict w from cp7_credit_correction_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 select *into strict s from cp7_credit_correction_de.posting_v1 where backend_pid=w.backend_pid and transaction_id=w.transaction_id and actor=w.actor;
 if(s.operation_id,s.source_type,s.source_id,s.economic_date,s.lines_sha256)is distinct from(w.operation_id,p_type,p_source,p_economic,cp7_credit.native_lines_sha256(p_lines))then
  raise exception 'CP7_CREDIT_DE_EXACT_POSTING_SCOPE_REQUIRED';end if;
 if p_type='CP7_CUSTOMER_CREDIT_RECOGNITION'then
  perform cp7_credit_correction_de.assert_plan_set_v1(w.operation_id);
  if not exists(select 1 from cp7_credit.component_parts q join cp7_credit.recognition_components c on c.id=q.component_id
   join cp7_credit_correction_de.plans_v1 p on p.plan_id=c.plan_id where q.id=p_source and p.operation_id=w.operation_id
    and c.economic_date=p_economic and c.transaction_date=s.transaction_date and cp7_credit.native_lines_sha256(cp7_credit.part_lines(q.id))=s.lines_sha256)then
   raise exception 'CP7_CREDIT_DE_COMPONENT_POSTING_CHANGED';end if;
 elsif p_type='SALES_RETURN'then
  if w.phase<>'POSTING'or p_source<>w.replacement_id or p_economic<>((w.payload#>>'{replacement,physical_at}')::timestamptz at time zone'Asia/Jakarta')::date
   or s.transaction_date<>(select transaction_date from erp.journal_entries where source_type='SALES_RETURN'and source_id=w.return_id and reversal_of_id is null)then
   raise exception 'CP7_CREDIT_DE_RETURN_POSTING_CHANGED';end if;
 else raise exception 'CP7_CREDIT_DE_UNSUPPORTED_POSTING_TYPE';end if;
end $$;
create function cp7_credit_correction_de.bound_book_date_v1(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns date
language plpgsql volatile security definer set search_path=''as $$
declare d date;begin perform cp7_credit_correction_de.assert_bound_post_v1(p_type,p_source,p_economic,p_lines);
 select transaction_date into strict d from cp7_credit_correction_de.posting_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 if d<erp.resolve_accounting_transaction_date(p_economic)then raise exception 'CP7_CREDIT_DE_BOOK_DATE_NO_LONGER_LAWFUL';end if;return d;end $$;
create function cp7_credit_correction_de.bound_audit_context_v1()returns jsonb
language sql stable security definer set search_path=''as $$
 select jsonb_build_object('credit_correction_operation_id',operation_id,'source_bound_book_date',transaction_date)from cp7_credit_correction_de.posting_v1
 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()
$$;
create function cp7_credit_correction_de.post_return_journal_v1(p_type text,p_return uuid,p_economic date,p_description text,p_lines jsonb)returns uuid
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_correction_de.work_v1;j uuid;book date;begin
 perform cp7_credit_correction_de.assert_work_v1();select *into strict w from cp7_credit_correction_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and replacement_id=p_return and phase='POSTING';
 select transaction_date into strict book from erp.journal_entries where source_type='SALES_RETURN'and source_id=w.return_id and reversal_of_id is null;
 insert into cp7_credit_correction_de.posting_v1 values(w.backend_pid,w.transaction_id,w.actor,w.operation_id,p_type,p_return,p_economic,book,cp7_credit.native_lines_sha256(p_lines));
 j:=cp7_credit_correction_de._post_journal_v1(p_type,p_return,p_economic,p_description,p_lines);
 delete from cp7_credit_correction_de.posting_v1 where backend_pid=w.backend_pid and transaction_id=w.transaction_id;return j;
end $$;
