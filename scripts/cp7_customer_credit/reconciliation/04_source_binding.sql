do $not_an_installer$begin raise exception 'OW04_RECONCILIATION_REQUIRES_COMPLETE_ATOMIC_COMPOSITION';end $not_an_installer$;

-- Common immutable binding before and after work cleanup. The posting clock,
-- active plan, phase, generated financial-marker ID and actual new output are
-- deliberately outside this input binding; their separate witnesses prove
-- exactly what was posted. A plan kernel never contains its own review hash.
create function cp7_credit.source_operation_binding_payload_v1(p_operation uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare live jsonb;saved jsonb;answer jsonb;other jsonb;
 fields text[]:=array['operation_id','operation_ordinal','predecessor_operation_id','backend_pid','transaction_id',
  'actor','request_id','action','sale_id','source_id','expected_version','payload','payload_sha256','authority_snapshot',
  'before_source','before_ordinal_input','before_ordinal_result','before_financial_profile','account_facts','period_snapshot',
  'actual_source','actual_source_proof','actual_ordinal_input','actual_ordinal_result','plan_manifest'];
begin
 select to_jsonb(w)into live from cp7_credit.source_operation_work_v1 w where operation_id=p_operation;
 select to_jsonb(m)into saved from cp7_credit.source_operation_materializations_v1 m where operation_id=p_operation;
 if live is null and saved is null then raise exception 'CP7_CREDIT_SOURCE_OPERATION_BINDING_ABSENT';end if;
 select jsonb_object_agg(key,value)into answer from jsonb_each(coalesce(saved,live))where key=any(fields);
 if(select count(*)from jsonb_object_keys(answer))<>cardinality(fields)
  or exists(select 1 from jsonb_each(answer)where key<>'predecessor_operation_id'and value='null'::jsonb)then
  raise exception 'CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE';end if;
 if live is not null and saved is not null then
  select jsonb_object_agg(key,value)into other from jsonb_each(live)where key=any(fields);
  if other is distinct from answer then raise exception 'CP7_CREDIT_SOURCE_OPERATION_SAVED_BINDING_CHANGED';end if;
 end if;
 return jsonb_build_object('contract_version','ow04.source-operation-input-binding.v1','operation',answer);
end $$;

create function cp7_credit.source_operation_binding_sha256_v1(p_operation uuid)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_credit.pg_jsonb_sha256(cp7_credit.source_operation_binding_payload_v1(p_operation))
$$;

-- Current source matching excludes mutable stock/HPP of other legitimate
-- transactions and later period closure. Those have exact B/N/Z operation
-- predicates, not perpetual equality to an old stock/cache snapshot.
create function cp7_credit.source_semantic_snapshot_v1(p_source jsonb)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select jsonb_object_agg(key,value)from jsonb_each(p_source)where key=any(array[
  'sale','items','allocations','payments','payment_posting_facts','payment_reversal_facts',
  'returns','return_items','base_events','journals','advance_links'])
$$;

create function cp7_credit.source_stored_plan_manifest_v1(p_operation uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(jsonb_build_object('plan_id',p.id,'family_id',s.family_id,'family_ordinal',s.family_ordinal,
  'cohort_id',p.cohort_id,'request_ordinal',p.request_ordinal,'kernel_sha256',cp7_credit.pg_jsonb_sha256(p.kernel_result),
  'components',(select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'ordinal',c.ordinal,'component',c.kernel_component)order by c.ordinal),'[]')
   from cp7_credit.recognition_components c where c.plan_id=p.id),
  'parts',(select coalesce(jsonb_agg(jsonb_build_object('id',q.id,'component_id',q.component_id,'ordinal',q.ordinal,
   'amount',cp7_credit.cent_text(q.amount))order by c.ordinal,q.ordinal),'[]')
   from cp7_credit.recognition_components c join cp7_credit.component_parts q on q.component_id=c.id where c.plan_id=p.id))
  order by s.family_ordinal),'[]')from cp7_credit.source_operation_plans_v1 s
 join cp7_credit.recognition_plans p on p.id=s.plan_id where s.operation_id=p_operation
$$;

create function cp7_credit.source_materialization_manifest_v1(p_operation uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','ow04.source-operation-actual-manifest.v1','operation_id',m.operation_id,
  'source_binding_sha256',cp7_credit.source_operation_binding_sha256_v1(m.operation_id),
  'financial_marker_id',m.financial_marker_id,'actual_objects',m.actual_objects)
 from cp7_credit.source_operation_materializations_v1 m where m.operation_id=p_operation
$$;

create function cp7_credit.source_historical_plan_ids_v1(p_operation uuid)returns uuid[]
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare op jsonb;answer uuid[];
begin
 op:=cp7_credit.source_operation_binding_payload_v1(p_operation)->'operation';
 select coalesce(array_agg(p.id order by p.id),'{}')into answer from cp7_credit.recognition_plans p
  join cp7_credit.cohorts c on c.id=p.cohort_id where c.source_sale_id=(op->>'sale_id')::uuid
   and exists(select 1 from jsonb_array_elements(op#>'{before_source,returns}')r
    where r->>'id'=c.source_return_id::text and r->>'status'in('POSTED','REVERSED'))
   and(p.id=c.initial_plan_id or exists(select 1 from cp7_credit.source_operation_plans_v1 sp
    join cp7_credit.source_operation_materializations_v1 old on old.operation_id=sp.operation_id
    where sp.plan_id=p.id and old.sale_id=(op->>'sale_id')::uuid and old.operation_ordinal<(op->>'operation_ordinal')::bigint));
 return answer;
end $$;

create function cp7_credit.source_snapshot_base_events_v1(p_snapshot jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare answer jsonb;ar uuid;sale uuid:=(p_snapshot#>>'{sale,id}')::uuid;row jsonb;
begin
 select distinct c.ar_account_id into strict ar from cp7_credit.cohorts c where c.source_sale_id=sale;
 for row in select value from jsonb_array_elements(p_snapshot->'journals')loop
  if cp7_credit.materialized_journal_payload((row->>'id')::uuid)is distinct from row->'immutable_payload'then
   raise exception 'CP7_CREDIT_SOURCE_HISTORICAL_JOURNAL_CHANGED';end if;
 end loop;
 with recursive roots(id,kind)as(
  select (j->>'id')::uuid,case when j#>>'{immutable_payload,journal,source_type}'='SALES_PAYMENT'then'FUNDING'else'NET'end
   from jsonb_array_elements(p_snapshot->'journals')j where j#>>'{immutable_payload,journal,reversal_of_id}'is null
    and((j#>>'{immutable_payload,journal,source_type}'='SALE'and j#>>'{immutable_payload,journal,source_id}'=sale::text)
     or(j#>>'{immutable_payload,journal,source_type}'='SALES_RETURN'and exists(select 1 from jsonb_array_elements(p_snapshot->'returns')r
      where r->>'id'=j#>>'{immutable_payload,journal,source_id}'and r->>'status'in('POSTED','REVERSED')))
     or(j#>>'{immutable_payload,journal,source_type}'='SALES_PAYMENT'and exists(select 1 from jsonb_array_elements(p_snapshot->'payments')p
      where p->>'id'=j#>>'{immutable_payload,journal,source_id}'and p->>'status'in('POSTED','REVERSED'))))
 ),walk(id,kind)as(
  select *from roots union select (j->>'id')::uuid,parent.kind from walk parent,jsonb_array_elements(p_snapshot->'journals')j
   where j#>>'{immutable_payload,journal,source_type}'='JOURNAL_REVERSAL'
    and j#>>'{immutable_payload,journal,source_id}'=parent.id::text
    and j#>>'{immutable_payload,journal,reversal_of_id}'=parent.id::text
 )select coalesce(jsonb_agg(jsonb_build_object('id','journal:'||w.id::text,'kind',w.kind,
  'amount',cp7_credit.cent_text(((case when w.kind='FUNDING'then-1 else 1 end)*coalesce(
   (select sum(l.debit-l.credit)from erp.journal_lines l where l.journal_entry_id=w.id and l.account_id=ar),0))::cp7_credit.cent_amount),
  'economic_date',j#>>'{immutable_payload,journal,economic_date}','transaction_date',j#>>'{immutable_payload,journal,transaction_date}',
  'source_sha256',ow04_source_proposal.sha(ow04_source_proposal.financial_journal_payload(w.id,ar)))order by w.id::text collate"C"),'[]')into answer
  from walk w join lateral(select x from jsonb_array_elements(p_snapshot->'journals')x where(x->>'id')::uuid=w.id)payload(j)on true;
 if answer is distinct from p_snapshot->'base_events'or jsonb_array_length(answer)<>jsonb_array_length(p_snapshot->'journals')
  or exists(select 1 from jsonb_array_elements(p_snapshot->'journals')j group by j->>'id'having count(*)<>1)then
  raise exception 'CP7_CREDIT_SOURCE_HISTORICAL_BASE_VECTOR_CHANGED';end if;
 return answer;
end $$;

-- Historical source partition is reconstructed from exact Native journal
-- ancestry and real immutable family registrations. Retained I comes from
-- INITIAL plus every explicitly earlier source operation, never from a
-- caller-supplied net, UUID order or wall-clock guess.
create function cp7_credit.source_historical_ordinal_input_v1(p_operation uuid,p_after boolean)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare op jsonb;snapshot jsonb;f cp7_credit.return_families;families jsonb:='[]';events jsonb;family_events jsonb;
 retained jsonb;all_return_ids text[]:='{}';plans uuid[];sale uuid;
begin
 op:=cp7_credit.source_operation_binding_payload_v1(p_operation)->'operation';sale:=(op->>'sale_id')::uuid;
 snapshot:=case when p_after then op->'actual_source'else op->'before_source'end;
 plans:=cp7_credit.source_historical_plan_ids_v1(p_operation);events:=cp7_credit.source_snapshot_base_events_v1(snapshot);
 for f in select rf.*from cp7_credit.return_families rf where rf.family_root_sale_id=sale
  and exists(select 1 from jsonb_array_elements(op#>'{before_source,returns}')r
   where r->>'id'=rf.first_return_id::text and r->>'status'in('POSTED','REVERSED'))order by rf.family_ordinal loop
  with recursive journals(id)as(
   select (j->>'id')::uuid from jsonb_array_elements(snapshot->'journals')j
    where j#>>'{immutable_payload,journal,source_type}'='SALES_RETURN'
     and j#>>'{immutable_payload,journal,reversal_of_id}'is null
     and exists(select 1 from cp7_credit.return_family_members mm where mm.family_id=f.id
      and mm.return_id=(j#>>'{immutable_payload,journal,source_id}')::uuid)
   union select (child->>'id')::uuid from journals parent,jsonb_array_elements(snapshot->'journals')child
    where child#>>'{immutable_payload,journal,reversal_of_id}'=parent.id::text
     or(child#>>'{immutable_payload,journal,source_type}'='JOURNAL_REVERSAL'
      and child#>>'{immutable_payload,journal,source_id}'=parent.id::text))
  select coalesce(jsonb_agg(x order by x->>'id'collate"C"),'[]')into family_events
   from jsonb_array_elements(events)x where substring(x->>'id'from 9)::uuid in(select id from journals);
  select all_return_ids||coalesce(array_agg(x->>'id'),'{}')into all_return_ids from jsonb_array_elements(family_events)x;
  select coalesce(jsonb_agg(jsonb_build_object('id','part:'||q.id::text,'amount',cp7_credit.cent_text(q.amount),
   'economic_date',j.economic_date::text,'transaction_date',j.transaction_date::text,
   'source_sha256',cp7_credit.pg_jsonb_sha256(jsonb_build_object('part',to_jsonb(q),'journal_link',to_jsonb(j))))order by q.id),'[]')into retained
   from cp7_credit.recognition_plans p join cp7_credit.cohorts c on c.id=p.cohort_id
   join cp7_credit.recognition_components cc on cc.plan_id=p.id join cp7_credit.component_parts q on q.component_id=cc.id
   join cp7_credit.component_journals j on j.part_id=q.id where p.id=any(plans)and c.family_id=f.id;
  if exists(select 1 from cp7_credit.consumption_events e join cp7_credit.cohorts c on c.id=e.cohort_id where c.family_id=f.id)then
   raise exception 'CP7_CREDIT_SOURCE_HISTORICAL_CONSUMER_ADAPTER_UNIMPLEMENTED';end if;
  families:=families||jsonb_build_array(jsonb_build_object('family_id',f.id,'ordinal',f.family_ordinal::text,
   'first_return_id',f.first_return_id,'registration_sha256',f.source_sha256,'events',family_events,
   'retained_recognition',retained,'consumptions','[]'::jsonb));
 end loop;
 select coalesce(jsonb_agg(x order by x->>'id'collate"C"),'[]')into events
  from jsonb_array_elements(events)x where not(x->>'id'=any(all_return_ids));
 return jsonb_build_object('contract_version','ow04.ordinal-input.v1','family_root_sale_id',sale,'base_events',events,'families',families);
end $$;

create function cp7_credit.source_historical_objects_v1(p_operation uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare op jsonb;objects jsonb;plans uuid[];family_ids uuid[];cohort_ids uuid[];component_ids uuid[];part_ids uuid[];member_ids uuid[];answer jsonb;
begin
 op:=cp7_credit.source_operation_binding_payload_v1(p_operation)->'operation';plans:=cp7_credit.source_historical_plan_ids_v1(p_operation);
 select coalesce(array_agg((x->>'family_id')::uuid),'{}')into family_ids
  from jsonb_array_elements(cp7_credit.source_historical_ordinal_input_v1(p_operation,false)->'families')x;
 select coalesce(array_agg(c.id),'{}')into cohort_ids from cp7_credit.cohorts c where c.family_id=any(family_ids)
  and c.initial_plan_id=any(plans);
 select coalesce(array_agg(m.return_id),'{}')into member_ids from cp7_credit.return_family_members m where m.family_id=any(family_ids)
  and exists(select 1 from jsonb_array_elements(op#>'{before_source,returns}')r where r->>'id'=m.return_id::text and r->>'status'in('POSTED','REVERSED'));
 select coalesce(array_agg(c.id),'{}')into component_ids from cp7_credit.recognition_components c where c.plan_id=any(plans);
 select coalesce(array_agg(q.id),'{}')into part_ids from cp7_credit.component_parts q where q.component_id=any(component_ids);
 objects:=cp7_credit.current_materialized_objects((op->>'sale_id')::uuid,(op->>'sale_id')::uuid,(op->>'sale_id')::uuid)->'actual_objects';
 select coalesce(jsonb_agg(x order by x->>'object_kind'collate"C",x->>'object_id'collate"C"),'[]')into answer
  from jsonb_array_elements(objects)x where(x->>'object_kind'='FAMILY'and(x->>'object_id')::uuid=any(family_ids))
   or(x->>'object_kind'='MEMBER'and(x->>'object_id')::uuid=any(member_ids))
   or(x->>'object_kind'='COHORT'and(x->>'object_id')::uuid=any(cohort_ids))
   or(x->>'object_kind'='PLAN'and(x->>'object_id')::uuid=any(plans))
   or(x->>'object_kind'='COMPONENT'and(x->>'object_id')::uuid=any(component_ids))
   or(x->>'object_kind'in('PART','PART_JOURNAL')and(x->>'object_id')::uuid=any(part_ids));
 return answer;
end $$;

-- Context-free provenance of every retained operation. This never treats a
-- current work row or permission snapshot as a substitute for actual source,
-- complete signed plans, exact part journals and materialization membership.
create function cp7_credit.assert_source_materialization_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare m cp7_credit.source_operation_materializations_v1;f cp7_credit.financial_materializations;
 sp cp7_credit.source_operation_plans_v1;p cp7_credit.recognition_plans;s cp7_credit.source_operation_part_seals_v1;
 binding text;family jsonb;input_family jsonb;k jsonb;objects jsonb;new_objects jsonb;old_object jsonb;retained_before jsonb;retained_after jsonb;
 side text;support_events jsonb;ar uuid;before_i numeric;
begin
 select *into strict m from cp7_credit.source_operation_materializations_v1 where operation_id=p_operation;
 binding:=cp7_credit.source_operation_binding_sha256_v1(m.operation_id);
 if m.payload_sha256 is distinct from cp7_credit.pg_jsonb_sha256(m.payload)
  or m.actual_manifest_sha256 is distinct from cp7_credit.pg_jsonb_sha256(cp7_credit.source_materialization_manifest_v1(m.operation_id))
  or m.plan_manifest is distinct from cp7_credit.source_stored_plan_manifest_v1(m.operation_id)
  or m.before_ordinal_input is distinct from cp7_credit.source_historical_ordinal_input_v1(m.operation_id,false)
  or m.actual_ordinal_input is distinct from cp7_credit.source_historical_ordinal_input_v1(m.operation_id,true)
  or m.before_financial_profile->'actual_objects'is distinct from cp7_credit.source_historical_objects_v1(m.operation_id)
  or m.before_ordinal_result is distinct from ow04_ordinal_wrapper.reconcile_v1(m.before_ordinal_input)
  or m.actual_ordinal_result is distinct from ow04_ordinal_wrapper.reconcile_v1(m.actual_ordinal_input)
  or not coalesce((m.before_ordinal_result->>'arithmetic_supported')::boolean,false)
  or not coalesce((m.actual_ordinal_result->>'arithmetic_supported')::boolean,false)
  or exists(select 1 from jsonb_array_elements(m.before_ordinal_result->'families')x where(x->>'has_reconciliation_effect')::boolean)
  or m.actual_source_proof is distinct from cp7_credit.source_inverse_proof_v1(m.before_source,m.actual_source,m.action,m.source_id)then
  raise exception 'CP7_CREDIT_SOURCE_MATERIALIZATION_BINDING_CHANGED';end if;
 -- Family registration, retained I and consumers are unchanged by a source
 -- operation. Only actual Native source events may change its target.
 select coalesce(jsonb_agg(x-'events'order by(x->>'ordinal')::bigint),'[]')into retained_before
  from jsonb_array_elements(m.before_ordinal_input->'families')x;
 select coalesce(jsonb_agg(x-'events'order by(x->>'ordinal')::bigint),'[]')into retained_after
  from jsonb_array_elements(m.actual_ordinal_input->'families')x;
 if retained_before is distinct from retained_after or m.actual_ordinal_input->>'family_root_sale_id'<>m.sale_id::text
  or m.before_ordinal_input->>'family_root_sale_id'<>m.sale_id::text then
  raise exception 'CP7_CREDIT_SOURCE_RETAINED_BASELINE_CHANGED';end if;
 select coalesce(sum((recognition_rows.recognition_value->>'amount')::numeric),0)into before_i
  from jsonb_array_elements(m.before_ordinal_input->'families')family_rows(family_value),
   lateral jsonb_array_elements(family_rows.family_value->'retained_recognition')recognition_rows(recognition_value);
 if m.before_financial_profile->>'actual_objects_sha256'is distinct from cp7_credit.pg_jsonb_sha256(m.before_financial_profile->'actual_objects')
  or(m.before_financial_profile->>'I')::numeric is distinct from before_i
  or(m.before_financial_profile->>'U')::numeric is distinct from 0::numeric
  or(m.before_financial_profile->>'adjustment')::numeric is distinct from -before_i
  or(m.before_financial_profile->>'sale_id',m.before_financial_profile->>'root_sale_id',m.before_financial_profile->>'current_leaf_id')
   is distinct from(m.sale_id::text,m.sale_id::text,m.sale_id::text)then
  raise exception 'CP7_CREDIT_SOURCE_BEFORE_FINANCIAL_PROFILE_CHANGED';end if;
 for sp in select *from cp7_credit.source_operation_plans_v1 where operation_id=m.operation_id order by family_ordinal loop
  select *into strict p from cp7_credit.recognition_plans where id=sp.plan_id;
  select x into strict family from jsonb_array_elements(m.actual_ordinal_result->'families')x
   where x#>>'{registration,family_id}'=sp.family_id::text;
  select x into strict input_family from jsonb_array_elements(m.actual_ordinal_input->'families')x
   where x->>'family_id'=sp.family_id::text;
  k:=cp7_credit.source_adjustment_kernel_v1(family);
  if not coalesce((family->>'has_reconciliation_effect')::boolean,false)or jsonb_array_length(k->'components')=0
   or p.net_amount>=0 or sp.full_family_result is distinct from family or sp.canonical_plan is distinct from k
   or sp.before_retained_events is distinct from input_family->'retained_recognition'
   or sp.before_consumptions is distinct from input_family->'consumptions'
   or family->>'retained_recognition_sha256'is distinct from ow04_pure_kernel.vector_sha256_v1(sp.before_retained_events)
   or family->>'consumptions_sha256'is distinct from ow04_pure_kernel.vector_sha256_v1(sp.before_consumptions)
   or sp.source_binding_sha256 is distinct from binding
   or(p.plan_kind,p.owning_action,p.actor,p.request_id,p.payload_sha256,p.review_sha256,p.family_root_sale_id)is distinct from
    ('ADJUSTMENT',m.action,m.actor,m.request_id,m.payload_sha256,binding,m.sale_id)
   or p.kernel_result is distinct from k or p.net_amount is distinct from(k->>'net_current_k')::numeric
   or p.kernel_version is distinct from k->>'kernel_version'
   or p.before_events is distinct from k->'before_events'or p.added_events is distinct from k->'added_events'
   or p.before_source_sha256 is distinct from k->>'before_source_sha256'
   or p.after_source_sha256 is distinct from k->>'after_source_sha256'
   or p.support_sha256_pg is distinct from cp7_credit.pg_jsonb_sha256(k->'support')
   or p.components_sha256_pg is distinct from cp7_credit.pg_jsonb_sha256(k->'components')
   or p.expected_component_count is distinct from jsonb_array_length(k->'components')
   or p.has_recognition_effect is distinct from(jsonb_array_length(k->'components')>0)
   or exists(select 1 from cp7_credit.plan_dependencies d where d.plan_id=p.id)
   or exists(select 1 from jsonb_array_elements(k->'components')x where(x->>'amount')::numeric>=0)
   or exists(select 1 from cp7_credit.cohorts ch where ch.id=p.cohort_id and ch.family_id<>sp.family_id)
   or not exists(select 1 from cp7_credit.return_families rf where rf.id=sp.family_id and rf.family_root_sale_id=m.sale_id and rf.family_ordinal=sp.family_ordinal)then
   raise exception 'CP7_CREDIT_SOURCE_SIGNED_PLAN_PROVENANCE_CHANGED';end if;
  select ar_account_id into strict ar from cp7_credit.cohorts where id=p.cohort_id;
  foreach side in array array['BEFORE','ADDED']loop
   select coalesce(jsonb_agg(jsonb_build_object('id',s0.event_id,'kind',s0.kind,'amount',cp7_credit.cent_text(s0.amount),
    'economic_date',s0.economic_date::text,'transaction_date',s0.transaction_date::text,'source_sha256',s0.source_sha256)
    order by s0.event_id collate"C"),'[]')into support_events from cp7_credit.plan_support_events s0 where s0.plan_id=p.id and s0.phase=side;
   if support_events is distinct from(case when side='BEFORE'then k->'before_events'else k->'added_events'end)then
    raise exception 'CP7_CREDIT_SOURCE_RETAINED_SUPPORT_VECTOR_CHANGED';end if;
  end loop;
  if exists(select 1 from cp7_credit.plan_support_events s0 where s0.plan_id=p.id and
   (s0.event_id is distinct from'journal:'||s0.journal_id::text
    or s0.source_fact_snapshot is distinct from ow04_source_proposal.financial_journal_payload(s0.journal_id,ar)
    or s0.source_sha256 is distinct from ow04_source_proposal.sha(s0.source_fact_snapshot)))then
   raise exception 'CP7_CREDIT_SOURCE_RETAINED_SUPPORT_FACT_CHANGED';end if;
 end loop;
 if exists(select 1 from cp7_credit.recognition_plans p0 where p0.actor=m.actor and p0.request_id=m.request_id
  and not exists(select 1 from cp7_credit.source_operation_plans_v1 sp0 where sp0.operation_id=m.operation_id and sp0.plan_id=p0.id))
  or exists(select 1 from jsonb_array_elements(m.actual_ordinal_result->'families')x where(x->>'has_reconciliation_effect')::boolean
   and not exists(select 1 from cp7_credit.source_operation_plans_v1 sp0 where sp0.operation_id=m.operation_id and sp0.family_id=(x#>>'{registration,family_id}')::uuid))then
  raise exception 'CP7_CREDIT_SOURCE_SIGNED_PLAN_SET_INCOMPLETE';end if;
 for s in select *from cp7_credit.source_operation_part_seals_v1 where operation_id=m.operation_id loop
  if s.actual_journal_sha256 is distinct from cp7_credit.pg_jsonb_sha256(s.actual_journal)
   or s.actual_journal is distinct from cp7_credit.materialized_journal_payload(s.journal_id)
   or s.source_binding_sha256 is distinct from binding
   or s.journal_link is distinct from(select to_jsonb(j)from cp7_credit.component_journals j where j.part_id=s.part_id and j.journal_id=s.journal_id)
   or not exists(select 1 from cp7_credit.component_parts q join cp7_credit.recognition_components cc on cc.id=q.component_id
    join cp7_credit.source_operation_plans_v1 sp0 on sp0.plan_id=cc.plan_id where q.id=s.part_id and cc.id=s.component_id
     and cc.plan_id=s.plan_id and sp0.operation_id=m.operation_id)
   or not exists(select 1 from erp.journal_entries j where j.id=s.journal_id and j.status='POSTED')
   or exists(select 1 from erp.journal_entries j where j.reversal_of_id=s.journal_id or(j.source_type='JOURNAL_REVERSAL'and j.source_id=s.journal_id))then
   raise exception 'CP7_CREDIT_SOURCE_PART_SEAL_CHANGED';end if;
 end loop;
 if exists(select 1 from cp7_credit.source_operation_plans_v1 sp0 join cp7_credit.recognition_components cc on cc.plan_id=sp0.plan_id
  join cp7_credit.component_parts q on q.component_id=cc.id where sp0.operation_id=m.operation_id
   and not exists(select 1 from cp7_credit.source_operation_part_seals_v1 s0 where s0.operation_id=m.operation_id and s0.part_id=q.id))then
  raise exception 'CP7_CREDIT_SOURCE_PART_SEAL_INCOMPLETE';end if;
 objects:=cp7_credit.current_materialized_objects(m.sale_id,m.sale_id,m.sale_id)->'actual_objects';
 for old_object in select value from jsonb_array_elements(m.before_financial_profile->'actual_objects')loop
  if not exists(select 1 from jsonb_array_elements(objects)x where x=old_object)then
   raise exception 'CP7_CREDIT_SOURCE_OLD_FINANCIAL_HISTORY_CHANGED';end if;
 end loop;
 select coalesce(jsonb_agg(x order by x->>'object_kind'collate"C",x->>'object_id'collate"C"),'[]')into new_objects
  from jsonb_array_elements(objects)x where
   (x->>'object_kind'='PLAN'and exists(select 1 from cp7_credit.source_operation_plans_v1 sp0 where sp0.operation_id=m.operation_id and sp0.plan_id=(x->>'object_id')::uuid))
   or(x->>'object_kind'='COMPONENT'and exists(select 1 from cp7_credit.recognition_components cc join cp7_credit.source_operation_plans_v1 sp0 on sp0.plan_id=cc.plan_id
    where sp0.operation_id=m.operation_id and cc.id=(x->>'object_id')::uuid))
   or(x->>'object_kind'in('PART','PART_JOURNAL')and exists(select 1 from cp7_credit.component_parts q join cp7_credit.recognition_components cc on cc.id=q.component_id
    join cp7_credit.source_operation_plans_v1 sp0 on sp0.plan_id=cc.plan_id where sp0.operation_id=m.operation_id and q.id=(x->>'object_id')::uuid));
 if new_objects is distinct from m.actual_objects or(jsonb_array_length(new_objects)=0)is distinct from(m.financial_marker_id is null)then
  raise exception 'CP7_CREDIT_SOURCE_ACTUAL_OBJECT_SET_CHANGED';end if;
 if m.financial_marker_id is not null then
  select *into strict f from cp7_credit.financial_materializations where id=m.financial_marker_id;
  if(f.root_sale_id,f.actor,f.request_id,f.request_ordinal,f.owning_action,f.payload_sha256,f.source_plan_sha256)is distinct from
   (m.sale_id,m.actor,m.request_id,1,m.action,m.payload_sha256,binding)
   or f.actual_objects is distinct from m.actual_objects or f.actual_objects_sha256 is distinct from cp7_credit.pg_jsonb_sha256(m.actual_objects)
   or exists(select 1 from jsonb_array_elements(m.actual_objects)x where not exists(select 1 from cp7_credit.financial_materialization_objects o
    where o.materialization_id=f.id and o.object_kind=x->>'object_kind'and o.object_id=(x->>'object_id')::uuid and o.fact_sha256=x->>'fact_sha256'))
   or(select count(*)from cp7_credit.financial_materialization_objects where materialization_id=f.id)<>jsonb_array_length(m.actual_objects)then
   raise exception 'CP7_CREDIT_SOURCE_FINANCIAL_MARKER_CHANGED';end if;
 end if;
end $$;

create function cp7_credit.assert_reconciled_source_profile_v1(p_sale uuid,p_actual jsonb)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare m cp7_credit.source_operation_materializations_v1;c cp7_credit.source_operation_completions_v1;
 previous uuid;ordinal bigint:=0;last_source jsonb;
begin
 for m in select *from cp7_credit.source_operation_materializations_v1 where sale_id=p_sale order by operation_ordinal loop
  ordinal:=ordinal+1;
  if m.operation_ordinal<>ordinal or m.predecessor_operation_id is distinct from previous then
   raise exception 'CP7_CREDIT_SOURCE_OPERATION_ORDER_INCOMPLETE';end if;
  if previous is not null and cp7_credit.source_semantic_snapshot_v1(m.before_source)
   is distinct from cp7_credit.source_semantic_snapshot_v1(last_source)then
   raise exception 'CP7_CREDIT_SOURCE_PREDECESSOR_SOURCE_CHANGED';end if;
  perform cp7_credit.assert_source_materialization_v1(m.operation_id);
  select *into c from cp7_credit.source_operation_completions_v1 where operation_id=m.operation_id;
  if c.operation_id is not null then perform cp7_credit.assert_source_completion_v1(m.operation_id);end if;
  if previous is not null and not exists(select 1 from cp7_credit.source_operation_completions_v1 where operation_id=previous)then
   raise exception 'CP7_CREDIT_SOURCE_PREDECESSOR_NOT_COMPLETE';end if;
  last_source:=coalesce(c.final_native_source,m.actual_source);previous:=m.operation_id;
 end loop;
 if previous is null or cp7_credit.source_document_snapshot_v1(p_sale)
  is distinct from cp7_credit.source_semantic_snapshot_v1(last_source)
  or(p_actual->>'U')::numeric<>0 then raise exception 'CP7_CREDIT_CURRENT_SIGNED_SOURCE_CHANGED';end if;
 -- Actual I is validated/summed by the shared mechanical inspector. The
 -- caller has already recomputed the complete current ordinal result with
 -- all actual signed I and required zero differences at every joint cut.
end $$;

do $private_source_bindings$declare sig text;begin
 foreach sig in array array['source_operation_binding_payload_v1(uuid)','source_operation_binding_sha256_v1(uuid)',
  'source_semantic_snapshot_v1(jsonb)','source_stored_plan_manifest_v1(uuid)','source_materialization_manifest_v1(uuid)',
  'source_historical_plan_ids_v1(uuid)','source_historical_ordinal_input_v1(uuid,boolean)','source_historical_objects_v1(uuid)',
  'source_snapshot_base_events_v1(jsonb)',
  'assert_source_materialization_v1(uuid)','assert_reconciled_source_profile_v1(uuid,jsonb)']loop
  execute 'alter function cp7_credit.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write';
 end loop;
end $private_source_bindings$;
