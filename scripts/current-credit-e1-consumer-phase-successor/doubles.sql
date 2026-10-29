-- LOCAL PGLITE DOUBLES ONLY. These table-backed dependency models are not
-- Native authorization, posting, HPP, financial or catalog qualification.
-- Complete E profile/history/prepare, consumer_execute and the protocol/data
-- validators listed in LOCAL_TYPED_INPUTS.json are the actual source bodies.
create table local_e_phase.settings(value jsonb);
create table local_e_phase.observations(label text,value jsonb);
create function local_e_phase.config()returns jsonb language sql stable as $$select value from local_e_phase.settings$$;
create function auth.uid()returns uuid language sql stable as $$select(local_e_phase.config()->>'actor')::uuid$$;
create function auth.jwt()returns jsonb language sql stable as $$select jsonb_build_object('role',local_e_phase.config()->>'jwt_role')$$;
create function erp.current_app_user_id()returns uuid language sql stable as $$select(local_e_phase.config()->>'app_user')::uuid$$;
create function cp7_note.access_now()returns jsonb language sql stable as $$select local_e_phase.config()->'authority'$$;
create function cp7_credit.consumer_command_access_v1(text,text)returns jsonb language sql stable as $$select local_e_phase.config()->'authority'$$;
create function cp7_credit.cent_text(numeric)returns text language sql immutable as $$select ow04_source_proposal.cents($1)$$;
create function cp7_credit.payment_is_intermediate_v1(uuid)returns boolean language sql stable as $$select false$$;
create function cp7_credit.payment_intermediate_adjustment_v1(uuid)returns numeric language plpgsql stable as $$begin raise exception 'LOCAL_PAYMENT_PHASE_OUT_OF_SCOPE';end$$;
create function cp7_credit.account_by_mapping_v1(p text)returns uuid language plpgsql stable as $$
declare answer uuid;begin select account_id into strict answer from erp.accounting_account_mappings where mapping_key=p;return answer;end$$;
create function cp7_sales.review_token(p uuid)returns text language sql stable as $$select md5(to_jsonb(h)::text)from erp.sales_headers h where h.id=p$$;
create function erp.resolve_accounting_transaction_date(p date)returns date language sql stable as $$
select greatest(p,coalesce((select closed_through+1 from erp.accounting_period_control where singleton_id=1),p))$$;
create function cp7_credit.assert_no_ambient_native_context()returns void language plpgsql stable as $$
begin
 if exists(select 1 from cp7_note.context where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'LOCAL_AMBIENT_NATIVE_CONTEXT';end if;
end$$;
create function cp7_credit.source_hpp_lot_ids_v1(p uuid)returns uuid[] language sql stable as $$
 select coalesce(array_agg(distinct a.lot_id order by a.lot_id),'{}')from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=p$$;
create function cp7_credit.source_first_nonpo_hpp_alignment_v1(jsonb)returns jsonb language plpgsql stable as $$
begin raise exception 'LOCAL_PREPARE_SUCCESS_HPP_OUT_OF_SCOPE';end$$;
create function cp7_credit.initial_base_events_v1(p_sale uuid,p_exclude uuid default null)returns jsonb
language plpgsql stable as $$
declare answer jsonb;begin
 if cp7_credit_note_carry_de.is_current_v1(p_sale)then return cp7_credit_note_carry_de.current_events_v1(p_sale);end if;
 select coalesce(jsonb_agg(jsonb_build_object('id','journal:'||j.id::text,'kind',case when j.source_type='SALES_PAYMENT'then'FUNDING'else'NET'end,
  'amount',cp7_credit.cent_text(case when j.source_type='SALES_PAYMENT'then-s.amount else s.amount end),
  'economic_date',j.economic_date,'transaction_date',j.transaction_date,'source_sha256',cp7_credit.pg_jsonb_sha256(to_jsonb(j)))order by j.id),'[]')into answer
 from erp.journal_entries j cross join lateral(select coalesce(sum(l.debit-l.credit),0)amount from erp.journal_lines l
  where l.journal_entry_id=j.id and l.account_id=cp7_credit.account_by_mapping_v1('AR_CUSTOMER'))s
 where(j.source_type='SALE'and j.source_id=p_sale)
  or(j.source_type='SALES_PAYMENT'and exists(select 1 from erp.sales_payments p where p.id=j.source_id and p.sale_id=p_sale))
  or(j.source_type='SALES_RETURN'and exists(select 1 from erp.sales_returns r where r.id=j.source_id and r.sale_id=p_sale));
 return answer||cp7_credit.consumer_incoming_funding_v1(p_sale);
end$$;
create function cp7_credit.source_native_snapshot_v1(p_sale uuid)returns jsonb language plpgsql stable as $$
declare doc jsonb;events jsonb;begin
 doc:=cp7_credit_note_carry_de.raw_document_v1(p_sale);events:=cp7_credit.initial_base_events_v1(p_sale);
 return doc||jsonb_build_object('base_events',events,'journals',(select coalesce(jsonb_agg(jsonb_build_object('id',j.id,
  'status',j.status,'immutable_payload',cp7_credit.materialized_journal_payload(j.id))order by j.id),'[]')from erp.journal_entries j
  where j.id in(select substring(v->>'id'from 9)::uuid from jsonb_array_elements(events)v)),
  'stock_movements',(select coalesce(jsonb_agg(to_jsonb(m)order by id),'[]')from erp.fg_stock_movements m),
  'hpp_versions',(select coalesce(jsonb_agg(to_jsonb(h)order by id),'[]')from erp.hpp_versions h),
  'return_items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=p_sale),
  'cash',(select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l join erp.cash_accounts c on c.coa_account_id=l.account_id));
end$$;
-- Complete original first assignment guard, followed by a declared bounded
-- materialized-object model. No retained financial assertion is edited.
create function cp7_credit.current_materialized_objects(p_sale uuid,p_root uuid,p_leaf uuid)returns jsonb language plpgsql stable as $$
declare a record;objects jsonb;incoming numeric;issued numeric;roots jsonb;begin
 select *into strict a from cp7_credit.current_leaf_assignment(p_sale);
 if(a.root_sale_id,a.current_leaf_id)is distinct from(p_root,p_leaf)
  or p_sale<>p_leaf or a.requested_status not in('POSTED','PARTIAL_PAID','PAID')then
  raise exception 'CP7_CREDIT_CURRENT_ASSIGNMENT_CHANGED';end if;
 select coalesce(jsonb_agg(cp7_credit.materialized_fact('CONSUMPTION',e.id,jsonb_build_object('event',to_jsonb(e),
  'actual',cp7_credit.materialized_journal_payload(e.journal_id)))order by e.id),'[]')into objects from cp7_credit.consumption_events e;
 select coalesce(sum(e.amount),0)into incoming from cp7_credit.consumption_events e where e.event_kind='APPLY'
  and cp7_credit_note_carry_de.effective_target_v1(e.id)=p_sale;
 select coalesce(sum(part.amount),0)into issued from cp7_credit.return_families f join cp7_credit.cohorts c on c.family_id=f.id
  join cp7_credit.recognition_plans p on p.cohort_id=c.id join cp7_credit.recognition_components comp on comp.plan_id=p.id
  join cp7_credit.component_parts part on part.component_id=comp.id join cp7_credit.component_journals j on j.part_id=part.id where f.family_root_sale_id=p_root;
 select jsonb_agg(v order by v)into roots from(select p_root v union select f.family_root_sale_id from cp7_credit.consumption_events e
  join cp7_credit.cohorts c on c.id=e.cohort_id join cp7_credit.return_families f on f.id=c.family_id
  where e.event_kind='APPLY'and cp7_credit_note_carry_de.effective_target_v1(e.id)=p_sale)x;
 return jsonb_build_object('contract_version','ow04.actual-materialized-objects.v1','sale_id',p_sale,'root_sale_id',p_root,
  'current_leaf_id',p_leaf,'upstream_root_ids',roots,'actual_objects',objects,'actual_objects_sha256',cp7_credit.pg_jsonb_sha256(objects),
  'I',cp7_credit.cent_text(issued),'U',cp7_credit.cent_text(incoming),'adjustment',cp7_credit.cent_text(incoming-issued),
  'LOCAL_BOUNDED_MATERIALIZED_MODEL',true);
end$$;
create function cp7_credit.inspect_current_materialized_profile(p_sale uuid,p_root uuid,p_leaf uuid)returns jsonb language plpgsql stable as $$
declare actual jsonb;fact jsonb;m cp7_credit.financial_materializations;link cp7_credit.financial_materialization_objects;begin
 actual:=cp7_credit.current_materialized_objects(p_sale,p_root,p_leaf);
 for fact in select value from jsonb_array_elements(actual->'actual_objects')loop
  select *into strict link from cp7_credit.financial_materialization_objects where object_kind=fact->>'object_kind'and object_id=(fact->>'object_id')::uuid;
  select *into strict m from cp7_credit.financial_materializations where id=link.materialization_id;
  if link.fact_sha256 is distinct from fact->>'fact_sha256'or m.actual_objects is distinct from jsonb_build_array(fact)
   or m.actual_objects_sha256 is distinct from cp7_credit.pg_jsonb_sha256(m.actual_objects)then raise exception 'LOCAL_MATERIALIZATION_FACT_CHANGED';end if;
 end loop;
 return actual||jsonb_build_object('financial_marker_verified',true,'financial_data_complete',true);
end$$;
create function cp7_credit.assert_financial_materialization_provenance(p_actual jsonb)returns void language plpgsql stable as $$
declare fact jsonb;begin
 for fact in select value from jsonb_array_elements(p_actual->'actual_objects')loop
  perform cp7_credit.consumer_actual_manifest_v1((fact->>'object_id')::uuid);
 end loop;
end$$;
create function cp7_credit.assert_current_materialized_profile(p_sale uuid,p_root uuid,p_leaf uuid)returns void language plpgsql stable as $$
declare actual jsonb;e record;begin
 actual:=cp7_credit.inspect_current_materialized_profile(p_sale,p_root,p_leaf);
 if cp7_credit_note_carry_de.has_root_v1(p_root)then
  perform cp7_credit_note_carry_de.assert_profile_v1(p_sale,p_root,p_leaf,actual);
 else
  for e in select ce.id from cp7_credit.consumption_events ce join cp7_credit.cohorts c on c.id=ce.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=p_root loop
   perform cp7_credit.consumer_event_data_v1(e.id);
  end loop;
  if(select sum(amount)from cp7_credit.consumption_events)>200 then raise exception 'LOCAL_SOURCE_CAPACITY_UNFUNDED';end if;
 end if;
 perform cp7_credit.assert_financial_materialization_provenance(actual);
end$$;
create function cp7_credit.consumer_selection_v1(jsonb)returns jsonb language sql stable as $$select local_e_phase.config()->'selection'$$;
create function cp7_credit.consumer_lock_sources_v1(jsonb)returns jsonb language plpgsql volatile as $$
declare locked jsonb:=local_e_phase.config()->'locked';current_sources jsonb;begin
 current_sources:=cp7_credit.consumer_capture_sources_v1(locked->'graph');
 if current_sources is distinct from locked->'sources'or locked->'authority'is distinct from cp7_credit.consumer_command_access_v1('APPLY','APPLY')
  or locked->'period'is distinct from(select to_jsonb(p)from erp.accounting_period_control p where singleton_id=1)then
  raise exception 'LOCAL_FRESH_LOCKED_SOURCE_CHANGED';end if;
 return locked;
end$$;
create function cp7_credit.consumer_projection_v1(jsonb,jsonb)returns jsonb language sql stable as $$select local_e_phase.config()->'projection'$$;
create function cp7_credit.consumer_journal_ids_v1(p uuid[])returns uuid[] language sql stable as $$
 select coalesce(array_agg(id order by id),'{}')from erp.journal_entries j where j.source_type='SALE'and j.source_id=any(p)
  or j.id in(select journal_id from cp7_credit.consumption_events)$$;
create function cp7_credit.consumer_source_vectors_v1(p uuid)returns jsonb language plpgsql stable as $$
declare recognition jsonb;consumptions jsonb;begin
 select coalesce(jsonb_agg(jsonb_build_object('id','part:'||part.id::text,'amount',cp7_credit.cent_text(part.amount),'economic_date',j.economic_date,'transaction_date',j.transaction_date,
  'source_sha256',cp7_credit.pg_jsonb_sha256(jsonb_build_object('part',to_jsonb(part),'link',to_jsonb(j))))),'[]')into recognition
 from cp7_credit.recognition_plans p1 join cp7_credit.recognition_components c on c.plan_id=p1.id join cp7_credit.component_parts part on part.component_id=c.id
 join cp7_credit.component_journals j on j.part_id=part.id where p1.cohort_id=p;
 select coalesce(jsonb_agg(jsonb_build_object('id','consumption:'||id::text,'amount',cp7_credit.cent_text(amount),'economic_date',economic_date,'transaction_date',transaction_date,'source_sha256',source_sha256)),'[]')into consumptions from cp7_credit.consumption_events where cohort_id=p;
 return jsonb_build_object('recognition',recognition,'consumptions',consumptions);
end$$;
create function cp7_credit.consumer_cash_balance_v1(p uuid)returns numeric language sql stable as $$select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=p$$;
create function cp7_guard.check_cash(uuid,date,date)returns void language plpgsql stable as $$begin raise exception 'LOCAL_CASH_COMMAND_OUT_OF_SCOPE';end$$;
create function cp7_credit.credit_account_facts_v1(p uuid)returns jsonb language plpgsql stable as $$
declare a erp.chart_accounts;begin select *into strict a from erp.chart_accounts where id=p;
 if a.account_type is distinct from'LIABILITY'or a.normal_balance is distinct from'CREDIT'then raise exception 'LOCAL_CREDIT_ACCOUNT_CHANGED';end if;return to_jsonb(a);end$$;
-- Declared Native poster DOUBLE. The actual operation/input/current authority
-- and posted journal/line/event/materialization validators remain source exact.
create function cp7_credit._post_consumer_bound_v1(p_type text,p_source uuid,p_date date,p_reason text,p_lines jsonb)returns uuid
language plpgsql volatile as $$
declare o cp7_credit.consumer_operations_v1;s cp7_credit.consumer_posting_scope_v1;jid uuid:=md5(p_source::text||':journal')::uuid;
 line jsonb;n int:=0;begin
 select *into strict o from cp7_credit.consumer_operations_v1 where id=p_source;
 select *into strict s from cp7_credit.consumer_posting_scope_v1 where operation_id=p_source and backend_pid=pg_backend_pid()and transaction_id=txid_current();
 perform cp7_credit.assert_consumer_operation_bound_v1(o.id);
 if(s.source_type,s.economic_date,s.transaction_date,s.lines_sha256_pg)is distinct from(p_type,p_date,o.transaction_date,cp7_credit.native_lines_sha256(p_lines))
  or not exists(select 1 from cp7_credit.consumer_execution_context where operation_id=o.id and phase='POSTING')then raise exception 'LOCAL_POST_BOUND_SCOPE_CHANGED';end if;
 insert into erp.journal_entries(id,source_type,source_id,status,economic_date,transaction_date,posting_at)
 values(jid,p_type,p_source,'POSTED',p_date,o.transaction_date,statement_timestamp());
 for line in select value from jsonb_array_elements(p_lines)loop
  n:=n+1;insert into erp.journal_lines(id,journal_entry_id,account_id,customer_id,description,debit,credit)
  values(md5(p_source::text||':line:'||n::text)::uuid,jid,(line->>'account_id')::uuid,(line->>'customer_id')::uuid,line->>'description',(line->>'debit')::numeric,(line->>'credit')::numeric);
 end loop;
 return jid;
end$$;
