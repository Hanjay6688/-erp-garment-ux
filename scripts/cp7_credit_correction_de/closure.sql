create function cp7_credit_correction_de.assert_closed_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''set timezone='UTC'as $$
declare o cp7_credit_correction_de.operations_v1;q cp7_sales_return_correction.requests;proof jsonb;review jsonb;item jsonb;actual jsonb;s record;begin
 select *into strict o from cp7_credit_correction_de.operations_v1 where operation_id=p_operation;
 select *into strict q from cp7_sales_return_correction.requests where actor=o.actor and request_id=o.request_id;proof:=o.proof;
 if(q.payload,q.expected_version,q.response)is distinct from(o.payload,o.expected_version,o.response)
  or(proof->>'operation_id',proof->>'actor',proof->>'request_id',proof->>'sale_id',proof->>'return_id',proof->>'replacement_id',proof->>'expected_version',proof->'payload',proof->>'phase')is distinct from
   (o.operation_id::text,o.actor::text,o.request_id::text,o.sale_id::text,o.return_id::text,o.replacement_id::text,o.expected_version,o.payload,'MATERIALIZED')
  or(proof->>'operation_ordinal')::bigint<>o.operation_ordinal or(proof->>'predecessor_id')::uuid is distinct from o.predecessor_id
  or(o.operation_ordinal=1)is distinct from(o.predecessor_id is null)
  or o.predecessor_id is not null and not exists(select 1 from cp7_credit_correction_de.operations_v1 previous where previous.operation_id=o.predecessor_id and previous.sale_id=o.sale_id and previous.operation_ordinal=o.operation_ordinal-1)
  or(o.response->>'contract_version',o.response->>'kind',o.response->>'action',o.response->>'request_id',o.response->>'sale_id',o.response->>'original_return_id',o.response->>'return_id',o.response->>'original_return_status',o.response->>'return_status')is distinct from
   ('cp7.sales-return-correction.v1','COMMITTED_OUTCOME','RETURN_CORRECT',o.request_id::text,o.sale_id::text,o.return_id::text,o.replacement_id::text,'REVERSED','POSTED')then
  raise exception 'CP7_CREDIT_DE_HISTORICAL_RECEIPT_CHANGED';end if;
 review:=cp7_credit_correction_de.review_vectors_v1(proof->'before_input',proof->'actual_input');
 if review->'credit_delta'is distinct from proof#>'{review,credit_delta}'or review->'requires_undo'is distinct from'false'::jsonb
  or review->'actual_result'is distinct from proof->'actual_result'then raise exception 'CP7_CREDIT_DE_HISTORICAL_ARITHMETIC_CHANGED';end if;
 for item in select value from jsonb_array_elements(review->'families')loop
  if not exists(select 1 from jsonb_array_elements(proof#>'{review,families}')v where v->>'family_id'=item->>'family_id'and v->'vector'=item->'vector')then
   raise exception 'CP7_CREDIT_DE_HISTORICAL_REVIEW_VECTOR_CHANGED';end if;
 end loop;
 perform cp7_credit_correction_de.assert_source_change_v1(proof->'before_source',proof->'actual_source',o.return_id,o.replacement_id);
 perform ow04_source_proposal.verify_return_member_v1(o.replacement_id);
 perform cp7_credit_correction_de.assert_marker_v1(o.operation_id);
 actual:=cp7_credit.current_materialized_objects(o.sale_id,o.sale_id,o.sale_id);
 for item in select value from jsonb_array_elements((proof#>'{before_profile,actual_objects}')||(proof->'actual_objects'))loop
  if not exists(select 1 from jsonb_array_elements(actual->'actual_objects')v where v=item)then raise exception 'CP7_CREDIT_DE_HISTORICAL_OBJECT_CHANGED';end if;
 end loop;
 for s in select z.*,to_jsonb(j)actual_link from cp7_credit_correction_de.parts_v1 z join cp7_credit.component_journals j on j.part_id=z.part_id where z.operation_id=o.operation_id loop
  if s.journal_link is distinct from s.actual_link or s.journal_snapshot is distinct from cp7_credit.materialized_journal_payload(s.journal_id)then raise exception 'CP7_CREDIT_DE_HISTORICAL_PART_CHANGED';end if;
 end loop;
 if exists(select 1 from cp7_credit_correction_de.work_v1 w where w.operation_id=o.operation_id)
  or exists(select 1 from cp7_credit_correction_de.posting_v1 where operation_id=o.operation_id)then raise exception 'CP7_CREDIT_DE_TEMPORARY_SCOPE_NOT_CLEARED';end if;
 perform cp7_credit.assert_current_materialized_profile(o.sale_id,o.sale_id,o.sale_id);
end $$;
create function cp7_credit_correction_de.close_fact_v1(p_table text,p_row jsonb)returns boolean
language plpgsql stable security definer set search_path=''as $$
declare op uuid;plan uuid;begin
 if p_table in('financial_materializations','financial_materialization_objects')then
  op:=(case when p_table='financial_materializations'then p_row->>'id'else p_row->>'materialization_id'end)::uuid;
  if not exists(select 1 from cp7_credit_correction_de.operations_v1 where operation_id=op)then return false;end if;
 elsif p_table='return_family_members'then
  select operation_id into op from cp7_credit_correction_de.operations_v1 where replacement_id=(p_row->>'return_id')::uuid;
 else
  case p_table
   when'recognition_plans'then plan:=(p_row->>'id')::uuid;
   when'plan_support_events'then plan:=(p_row->>'plan_id')::uuid;
   when'recognition_components'then plan:=(p_row->>'plan_id')::uuid;
   when'component_parts'then select plan_id into plan from cp7_credit.recognition_components where id=(p_row->>'component_id')::uuid;
   when'component_journals'then select c.plan_id into plan from cp7_credit.component_parts q join cp7_credit.recognition_components c on c.id=q.component_id where q.id=(p_row->>'part_id')::uuid;
   when'plan_dependencies'then plan:=(p_row->>'plan_id')::uuid;
   else return false;
  end case;
  select operation_id into op from cp7_credit_correction_de.plans_v1 where plan_id=plan;
 end if;
 if op is null then return false;end if;perform cp7_credit_correction_de.assert_closed_v1(op);return true;
end $$;
create function cp7_credit_correction_de.enforce_closed_v1()returns trigger
language plpgsql security definer set search_path=''as $$
begin perform cp7_credit_correction_de.assert_closed_v1((to_jsonb(new)->>'operation_id')::uuid);return null;end $$;
do $closure$declare name text;begin
 foreach name in array array['work_v1','operations_v1','plans_v1','parts_v1','posting_v1']loop
  execute 'create constraint trigger operation_closed after insert or update on cp7_credit_correction_de.'||name||
   ' deferrable initially deferred for each row execute function cp7_credit_correction_de.enforce_closed_v1()';
 end loop;
end $closure$;
