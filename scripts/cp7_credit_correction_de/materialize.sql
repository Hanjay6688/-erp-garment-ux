create function cp7_credit_correction_de.materialize_v1(p_replacement uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare w cp7_credit_correction_de.work_v1;link cp7_sales_return_correction.links;member jsonb;fact jsonb;family uuid;
 inp jsonb;result jsonb;review jsonb;f jsonb;oldf jsonb;k jsonb;c cp7_credit.cohorts;planned_manifest jsonb:='[]';components jsonb;parts jsonb;entry jsonb;
 plan uuid;component uuid;part uuid;request_ordinal int:=0;component_ordinal int;part_ordinal bigint;amount numeric;piece numeric;x jsonb;y jsonb;support_phase text;
 actual_items jsonb;expected_items jsonb;replacement_header erp.sales_returns;
 q cp7_credit.component_parts;cc cp7_credit.recognition_components;lines jsonb;j uuid;jlink cp7_credit.component_journals;actual jsonb;objects jsonb;new_objects jsonb;
begin
 perform cp7_credit_correction_de.assert_work_v1();select *into strict w from cp7_credit_correction_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and replacement_id=p_replacement and phase='POSTED';
 select *into strict link from cp7_sales_return_correction.links where original_id=w.return_id and replacement_id=w.replacement_id and sale_id=w.sale_id and actor=w.actor and request_id=w.request_id;
 select *into strict replacement_header from erp.sales_returns where id=w.replacement_id;
 if(replacement_header.sale_id,replacement_header.customer_id,replacement_header.physical_at,replacement_header.notes,replacement_header.return_number,replacement_header.status)is distinct from
  (w.sale_id,(w.before_source#>>'{sale,customer_id}')::uuid,(w.payload#>>'{replacement,physical_at}')::timestamptz,w.payload#>>'{replacement,notes}','K-'||w.request_id::text,'POSTED')then
  raise exception 'CP7_CREDIT_DE_REPLACEMENT_INTENT_CHANGED';end if;
 select jsonb_agg(jsonb_build_object('allocation_id',i.sale_stock_allocation_id,'location_id',i.location_id,'qty_pcs',i.qty_pcs::text,
  'quality_grade',i.quality_grade,'refund_amount',cp7_credit.cent_text(i.refund_amount),'notes',i.notes)order by i.sale_stock_allocation_id)into actual_items
  from erp.sales_return_items i where i.return_id=w.replacement_id;
 select jsonb_agg(v||jsonb_build_object('refund_amount',cp7_credit.cent_text((v->>'refund_amount')::numeric))order by v->>'allocation_id')into expected_items
  from jsonb_array_elements(w.payload#>'{replacement,items}')v;
 if actual_items is distinct from expected_items then raise exception 'CP7_CREDIT_DE_REPLACEMENT_ITEMS_CHANGED';end if;

 select family_id into strict family from cp7_credit.return_family_members where return_id=w.return_id;
 fact:=ow04_source_proposal.return_fact_v1(w.replacement_id);
 if(fact->>'sale_id',fact->>'family_root_sale_id',fact->>'financial_state')is distinct from(w.sale_id::text,w.sale_id::text,'JOURNAL')then raise exception 'CP7_CREDIT_DE_REPLACEMENT_SOURCE_CHANGED';end if;
 member:=jsonb_build_object('contract_version','ow04.actual-return-family-member.v1','family_id',family,'family_root_sale_id',w.sale_id,
  'return_id',w.replacement_id,'sale_id',w.sale_id,'member_kind','RETURN_CORRECTION','predecessor_return_id',w.return_id,
  'native_lineage_id',link.id,'return_item_lineage','{}'::jsonb,'financial_state',fact->'financial_state','source_journal_id',fact->'source_journal_id',
  'financial_source_sha256',fact->'financial_source_sha256','no_journal_proof',fact->'no_journal_proof');
 insert into cp7_credit.return_family_members(family_id,return_id,member_kind,source_journal_id,source_sha256,actual_lineage_snapshot,actor,request_id,financial_state,financial_source_proof)
 values(family,w.replacement_id,'RETURN_CORRECTION',(fact->>'source_journal_id')::uuid,ow04_source_proposal.sha(member),member,w.actor,w.request_id,fact->>'financial_state',fact->'no_journal_proof');
 perform ow04_source_proposal.verify_return_member_v1(w.replacement_id);
 actual:=cp7_credit.source_native_snapshot_v1(w.sale_id);
 perform cp7_credit_correction_de.assert_source_change_v1(w.before_source,actual,w.return_id,w.replacement_id);
 perform cp7_credit.source_first_nonpo_hpp_alignment_v1(actual);
 inp:=cp7_credit.initial_ordinal_input_v1(w.sale_id);result:=ow04_ordinal_wrapper.reconcile_v1(inp);
 review:=cp7_credit_correction_de.review_vectors_v1(w.before_input,inp);
 if review->'requires_undo'is distinct from'false'::jsonb or review->'credit_delta'is distinct from w.review->'credit_delta'then raise exception 'CP7_CREDIT_DE_ACTUAL_CREDIT_REVIEW_CHANGED';end if;
 for f in select value from jsonb_array_elements(review->'families')loop
  select v into strict oldf from jsonb_array_elements(w.review->'families')v where v->>'family_id'=f->>'family_id';
  if f->'vector'is distinct from oldf->'vector'or f->'needs_cohort_configuration'='true'::jsonb then raise exception 'CP7_CREDIT_DE_ACTUAL_DATED_VECTOR_CHANGED';end if;
 end loop;
 for f in select value from jsonb_array_elements(result->'families')loop
  if not(f->>'has_reconciliation_effect')::boolean then continue;end if;
  if f->>'plan_kind'<>'ADJUSTMENT'or exists(select 1 from jsonb_array_elements(f->'reconciliation_components')v where(v->>'amount')::numeric<=0)then raise exception 'CP7_CREDIT_DE_POSITIVE_ADJUSTMENT_REQUIRED';end if;
  select *into strict c from cp7_credit.cohorts where family_id=(f#>>'{registration,family_id}')::uuid;
  k:=cp7_credit.source_adjustment_kernel_v1(f);plan:=gen_random_uuid();request_ordinal:=request_ordinal+1;component_ordinal:=0;components:='[]';parts:='[]';
  for x in select value from jsonb_array_elements(k->'components')loop
   component:=gen_random_uuid();component_ordinal:=component_ordinal+1;amount:=(x->>'amount')::numeric;
   components:=components||jsonb_build_array(jsonb_build_object('id',component,'ordinal',component_ordinal,'component',x));
   for part_ordinal in 1..ceil(amount/cp7_credit.native_journal_cent_max())::bigint loop
    part:=gen_random_uuid();piece:=least(cp7_credit.native_journal_cent_max(),amount-(part_ordinal-1)*cp7_credit.native_journal_cent_max());
    parts:=parts||jsonb_build_array(jsonb_build_object('id',part,'component_id',component,'ordinal',part_ordinal,'amount',cp7_credit.cent_text(piece)));
   end loop;
  end loop;
  planned_manifest:=planned_manifest||jsonb_build_array(jsonb_build_object('plan_id',plan,'family_id',c.family_id,'cohort_id',c.id,'request_ordinal',request_ordinal,'components',components,'parts',parts));
 end loop;
 if planned_manifest='[]'::jsonb then raise exception 'CP7_CREDIT_DE_RECOGNITION_INCREMENT_REQUIRED';end if;
 update cp7_credit_correction_de.work_v1 set phase='RECONCILING',actual_source=actual,actual_input=inp,actual_result=result,manifest=planned_manifest where operation_id=w.operation_id;
 for entry in select value from jsonb_array_elements(planned_manifest)loop
  select v into strict f from jsonb_array_elements(result->'families')v where v#>>'{registration,family_id}'=entry->>'family_id';
  k:=cp7_credit.source_adjustment_kernel_v1(f);plan:=(entry->>'plan_id')::uuid;
  insert into cp7_credit.recognition_plans(id,cohort_id,plan_kind,owning_action,actor,request_id,request_ordinal,payload_sha256,review_sha256,
   family_root_sale_id,before_events,added_events,kernel_result,kernel_version,before_source_sha256,after_source_sha256,support_sha256_pg,
   components_sha256_pg,parts_sha256_pg,net_amount,has_recognition_effect,expected_component_count,expected_part_count)
  values(plan,(entry->>'cohort_id')::uuid,'ADJUSTMENT','RETURN_CORRECT',w.actor,w.request_id,(entry->>'request_ordinal')::int,
   cp7_credit.pg_jsonb_sha256(w.payload),w.review->>'review_token',w.sale_id,k->'before_events',k->'added_events',k,k->>'kernel_version',
   k->>'before_source_sha256',k->>'after_source_sha256',cp7_credit.pg_jsonb_sha256(k->'support'),cp7_credit.pg_jsonb_sha256(k->'components'),
   cp7_credit.pg_jsonb_sha256(entry->'parts'),(k->>'net_current_k')::numeric,true,jsonb_array_length(k->'components'),jsonb_array_length(entry->'parts'));
  insert into cp7_credit_correction_de.plans_v1 values(plan,w.operation_id,(entry->>'family_id')::uuid,k,(entry->>'request_ordinal')::int);
  for x in select value from jsonb_array_elements(entry->'components')loop
   y:=x->'component';insert into cp7_credit.recognition_components(id,plan_id,ordinal,economic_date,transaction_date,amount,previous_economic_date,previous_transaction_date,corners,kernel_component,component_sha256_pg)
   values((x->>'id')::uuid,plan,(x->>'ordinal')::int,(y->>'economic_date')::date,(y->>'transaction_date')::date,(y->>'amount')::numeric,
    (y->>'previous_economic_date')::date,(y->>'previous_transaction_date')::date,y->'corners',y,cp7_credit.pg_jsonb_sha256(y));
  end loop;
  for x in select value from jsonb_array_elements(entry->'parts')loop insert into cp7_credit.component_parts values((x->>'id')::uuid,(x->>'component_id')::uuid,(x->>'ordinal')::bigint,(x->>'amount')::numeric);end loop;
  select *into strict c from cp7_credit.cohorts where id=(entry->>'cohort_id')::uuid;
  foreach support_phase in array array['BEFORE','ADDED']loop
   for x in select value from jsonb_array_elements(case when support_phase='BEFORE'then k->'before_events'else k->'added_events'end)loop
    insert into cp7_credit.plan_support_events(plan_id,event_id,phase,kind,amount,economic_date,transaction_date,source_sha256,journal_id,source_fact_snapshot)
    values(plan,x->>'id',support_phase,x->>'kind',(x->>'amount')::numeric,(x->>'economic_date')::date,(x->>'transaction_date')::date,x->>'source_sha256',
     substring(x->>'id'from 9)::uuid,ow04_source_proposal.financial_journal_payload(substring(x->>'id'from 9)::uuid,c.ar_account_id));
   end loop;
  end loop;
 end loop;
 perform cp7_credit_correction_de.assert_plan_set_v1(w.operation_id);
 for q in select pp.*from cp7_credit_correction_de.plans_v1 s join cp7_credit.recognition_components component_row on component_row.plan_id=s.plan_id
  join cp7_credit.component_parts pp on pp.component_id=component_row.id where s.operation_id=w.operation_id order by s.request_ordinal,component_row.ordinal,pp.ordinal loop
  select *into strict cc from cp7_credit.recognition_components where id=q.component_id;lines:=cp7_credit.part_lines(q.id);
  perform cp7_credit_correction_de.assert_plan_set_v1(w.operation_id);
  insert into cp7_credit_correction_de.posting_v1 values(w.backend_pid,w.transaction_id,w.actor,w.operation_id,'CP7_CUSTOMER_CREDIT_RECOGNITION',q.id,cc.economic_date,cc.transaction_date,cp7_credit.native_lines_sha256(lines));
  j:=cp7_credit_correction_de._post_journal_v1('CP7_CUSTOMER_CREDIT_RECOGNITION',q.id,cc.economic_date,'Tambahan kredit pembetulan retur | '||btrim(w.payload->>'change_reason'),lines);
  insert into cp7_credit.component_journals values(q.id,j,cc.economic_date,cc.transaction_date,cp7_credit.native_lines_sha256(lines),statement_timestamp())returning *into jlink;
  insert into cp7_credit_correction_de.parts_v1 values(q.id,w.operation_id,cc.plan_id,j,to_jsonb(jlink),cp7_credit.materialized_journal_payload(j));
  delete from cp7_credit_correction_de.posting_v1 where backend_pid=w.backend_pid and transaction_id=w.transaction_id;
 end loop;
 perform cp7_credit_correction_de.assert_plan_set_v1(w.operation_id);
 actual:=cp7_credit.current_materialized_objects(w.sale_id,w.sale_id,w.sale_id);objects:=actual->'actual_objects';
 for x in select value from jsonb_array_elements(w.before_profile->'actual_objects')loop
  if not exists(select 1 from jsonb_array_elements(objects)v where v=x)then raise exception 'CP7_CREDIT_DE_RETAINED_OBJECT_CHANGED';end if;
 end loop;
 select coalesce(jsonb_agg(v order by v->>'object_kind'collate"C",v->>'object_id'collate"C"),'[]')into new_objects from jsonb_array_elements(objects)v
  where not exists(select 1 from cp7_credit.financial_materialization_objects o where o.object_kind=v->>'object_kind'and o.object_id=(v->>'object_id')::uuid);
 if new_objects='[]'::jsonb then raise exception 'CP7_CREDIT_DE_NEW_FACTS_REQUIRED';end if;
 update cp7_credit_correction_de.work_v1 set phase='MATERIALIZED',actual_objects=new_objects where operation_id=w.operation_id;
 insert into cp7_credit.financial_materializations(id,root_sale_id,actor,request_id,request_ordinal,owning_action,payload_sha256,source_plan_sha256,actual_objects,actual_objects_sha256)
 values(w.operation_id,w.sale_id,w.actor,w.request_id,1,'RETURN_CORRECT',cp7_credit.pg_jsonb_sha256(w.payload),w.review->>'review_token',new_objects,cp7_credit.pg_jsonb_sha256(new_objects));
 for x in select value from jsonb_array_elements(new_objects)loop insert into cp7_credit.financial_materialization_objects values(x->>'object_kind',(x->>'object_id')::uuid,w.operation_id,x->>'fact_sha256');end loop;
 perform cp7_credit.assert_current_materialized_profile(w.sale_id,w.sale_id,w.sale_id);
end $$;

create function cp7_credit_correction_de.finish_v1(p_response jsonb)returns void
language plpgsql volatile security definer set search_path=''as $$
declare w cp7_credit_correction_de.work_v1;q cp7_sales_return_correction.requests;begin
 select *into strict w from cp7_credit_correction_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and phase='MATERIALIZED';
 select *into strict q from cp7_sales_return_correction.requests where actor=w.actor and request_id=w.request_id;
 if(q.payload,q.expected_version,q.response)is distinct from(w.payload,w.expected_version,p_response)
  or cp7_sales_return_correction.access_now()is distinct from w.authority
  or exists(select 1 from cp7_credit_correction_de.posting_v1 where backend_pid=w.backend_pid and transaction_id=w.transaction_id)
  or exists(select 1 from cp7_sales.command_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id)then raise exception 'CP7_CREDIT_DE_FINAL_RECEIPT_OR_SCOPE_CHANGED';end if;
 insert into cp7_credit_correction_de.operations_v1(operation_id,operation_ordinal,predecessor_id,actor,request_id,sale_id,return_id,replacement_id,expected_version,payload,proof,response)
 values(w.operation_id,w.operation_ordinal,w.predecessor_id,w.actor,w.request_id,w.sale_id,w.return_id,w.replacement_id,w.expected_version,w.payload,to_jsonb(w),p_response);
 delete from cp7_credit_correction_de.work_v1 where operation_id=w.operation_id;
 perform cp7_credit_correction_de.assert_closed_v1(w.operation_id);
end $$;
create function cp7_credit_correction_de.dispatch_v1(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
begin
 -- Validate UUID/payload in the original command; selecting a completed D
 -- request preserves same-UUID lost-reply recovery after its original is retired.
 if exists(select 1 from cp7_credit_correction_de.operations_v1 where actor=auth.uid()and request_id=p_request)
  or cp7_credit_correction_de.participates_v1((p->>'return_id')::uuid)then return cp7_credit_correction_de.command_v1(p,p_request,p_expected);end if;
 return cp7_sales_return_correction.command(p,p_request,p_expected);
end $$;
