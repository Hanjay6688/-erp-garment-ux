-- LOCAL STAND-INS ONLY. No Native accounting/authority/provenance qualification.
create table local_materialize_fixture.settings(value jsonb);
create table local_materialize_fixture.calls(name text,detail jsonb);
create sequence local_materialize_fixture.sentinel start 777;
create function local_materialize_fixture.get(p_key text)returns jsonb language sql stable set search_path=''as $$
 select value->p_key from local_materialize_fixture.settings$$;
create function local_materialize_fixture.guard(p_name text,p_detail jsonb default '{}')returns void
language sql volatile set search_path=''as $$insert into local_materialize_fixture.calls values(p_name,p_detail)$$;
create or replace function auth.uid()returns uuid language sql stable set search_path=''as $$
 select(local_materialize_fixture.get('actor')#>>'{}')::uuid$$;
create function cp7_credit.cent_text(numeric)returns text language sql immutable set search_path=''as $$select to_char($1,'FM9999999999999999999990.00')$$;
create function cp7_credit.pg_jsonb_sha256(jsonb)returns text language sql immutable set search_path=''as $$select encode(sha256(convert_to($1::text,'UTF8')),'hex')$$;
create function cp7_credit.native_lines_sha256(jsonb)returns text language sql immutable set search_path=''as $$select cp7_credit.pg_jsonb_sha256($1)$$;
create function ow04_source_proposal.sha(jsonb)returns text language sql immutable set search_path=''as $$select cp7_credit.pg_jsonb_sha256($1)$$;
create function cp7_credit.native_journal_cent_max()returns numeric language sql stable set search_path=''as $$
 select(local_materialize_fixture.get('part_max')#>>'{}')::numeric$$;
create function cp7_credit.source_native_snapshot_v1(uuid)returns jsonb language plpgsql volatile set search_path=''as $$begin
 perform local_materialize_fixture.guard('source_native_snapshot',jsonb_build_object('sale_id',$1));
 return local_materialize_fixture.get('actual_source');end$$;
create function cp7_credit.initial_ordinal_input_v1(uuid)returns jsonb language plpgsql volatile set search_path=''as $$begin
 perform local_materialize_fixture.guard('initial_ordinal_input');return local_materialize_fixture.get('after_input');end$$;
create function ow04_ordinal_wrapper.reconcile_v1(jsonb)returns jsonb language plpgsql volatile set search_path=''as $$begin
 if $1 is distinct from local_materialize_fixture.get('after_input')then raise exception 'LOCAL_WRONG_ORDINAL_INPUT';end if;
 perform local_materialize_fixture.guard('reconcile');return local_materialize_fixture.get('result');end$$;
create function cp7_credit_correction_de.review_vectors_v1(jsonb,jsonb)returns jsonb language plpgsql volatile set search_path=''as $$begin
 if $1 is distinct from local_materialize_fixture.get('before_input')or $2 is distinct from local_materialize_fixture.get('after_input')then raise exception 'LOCAL_WRONG_REVIEW_INPUTS';end if;
 perform local_materialize_fixture.guard('review_vectors');return local_materialize_fixture.get('review');end$$;
create function cp7_credit.source_adjustment_kernel_v1(jsonb)returns jsonb language plpgsql volatile set search_path=''as $$begin
 if not($1?'LOCAL_DECLARED_KERNEL')then raise exception 'LOCAL_KERNEL_NOT_DECLARED';end if;
 perform local_materialize_fixture.guard('source_adjustment_kernel');return $1->'LOCAL_DECLARED_KERNEL';end$$;
create or replace function cp7_credit_correction_de.assert_work_v1()returns void language plpgsql volatile set search_path=''as $$declare w cp7_credit_correction_de.work_v1;begin
 select *into strict w from cp7_credit_correction_de.work_v1 r where r.backend_pid=pg_backend_pid()and r.transaction_id=txid_current()and r.actor=auth.uid();
 if w.phase not in('POSTED','RECONCILING','MATERIALIZED')then raise exception 'LOCAL_WRONG_WORK_PHASE';end if;
 perform local_materialize_fixture.guard('assert_work',jsonb_build_object('phase',w.phase));end$$;
create function cp7_credit_correction_de.assert_source_change_v1(jsonb,jsonb,uuid,uuid)returns void language plpgsql volatile set search_path=''as $$begin
 if $1 is distinct from local_materialize_fixture.get('before_source')or $2 is distinct from local_materialize_fixture.get('actual_source')then raise exception 'LOCAL_SOURCE_DOUBLE_MISMATCH';end if;
 perform local_materialize_fixture.guard('assert_source_change');end$$;
create function cp7_credit.source_first_nonpo_hpp_alignment_v1(jsonb)returns void language plpgsql volatile set search_path=''as $$begin
 if $1 is distinct from local_materialize_fixture.get('actual_source')then raise exception 'LOCAL_HPP_INPUT_MISMATCH';end if;
 perform local_materialize_fixture.guard('source_first_nonpo_hpp_alignment');end$$;
create function ow04_source_proposal.return_fact_v1(p_return uuid)returns jsonb language plpgsql volatile set search_path=''as $$declare r erp.sales_returns;begin
 select *into strict r from erp.sales_returns where id=p_return;
 perform local_materialize_fixture.guard('return_fact');
 return jsonb_build_object('sale_id',r.sale_id,'family_root_sale_id',r.sale_id,'financial_state','JOURNAL',
  'source_journal_id',local_materialize_fixture.get('replacement_journal'),'financial_source_sha256',repeat('a',64),'no_journal_proof',null);end$$;
create function ow04_source_proposal.verify_return_member_v1(p_return uuid)returns void language plpgsql volatile set search_path=''as $$begin
 if not exists(select 1 from cp7_credit.return_family_members where return_id=p_return and member_kind='RETURN_CORRECTION')then raise exception 'LOCAL_MEMBER_NOT_INSERTED';end if;
 perform local_materialize_fixture.guard('verify_return_member');end$$;
create function ow04_source_proposal.financial_journal_payload(p_journal uuid,p_ar uuid)returns jsonb language plpgsql volatile set search_path=''as $$declare r erp.journal_entries;begin
 select *into strict r from erp.journal_entries where id=p_journal;
 perform local_materialize_fixture.guard('financial_journal_payload',jsonb_build_object('journal_id',p_journal,'ar',p_ar));
 return jsonb_build_object('LOCAL_JOURNAL_SOURCE_DOUBLE',true,'header',to_jsonb(r),'ar',p_ar);end$$;
create function cp7_credit.materialized_journal_payload(p_journal uuid)returns jsonb language sql stable set search_path=''as $$
 select jsonb_build_object('LOCAL_JOURNAL_PAYLOAD_DOUBLE',true,'header',to_jsonb(j),'lines',
  (select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]')from erp.journal_lines l where l.journal_entry_id=j.id))from erp.journal_entries j where j.id=p_journal$$;
create function cp7_credit_correction_de.assert_plan_set_v1(p_operation uuid)returns void language plpgsql volatile set search_path=''as $$declare w cp7_credit_correction_de.work_v1;e jsonb;p cp7_credit.recognition_plans;begin
 select *into strict w from cp7_credit_correction_de.work_v1 where operation_id=p_operation;
 if w.phase<>'RECONCILING'or w.actual_source is distinct from local_materialize_fixture.get('actual_source')then raise exception 'LOCAL_PLAN_PHASE_SOURCE_MISMATCH';end if;
 for e in select value from jsonb_array_elements(w.manifest)loop
  select *into strict p from cp7_credit.recognition_plans where id=(e->>'plan_id')::uuid;
  if p.plan_kind<>'ADJUSTMENT'or p.owning_action<>'RETURN_CORRECT'or p.expected_component_count<>jsonb_array_length(e->'components')or p.expected_part_count<>jsonb_array_length(e->'parts')then raise exception 'LOCAL_PLAN_COUNTS_MISMATCH';end if;
  if(select count(*)from cp7_credit.recognition_components c where c.plan_id=p.id)<>p.expected_component_count
   or(select count(*)from cp7_credit.component_parts q join cp7_credit.recognition_components c on c.id=q.component_id where c.plan_id=p.id)<>p.expected_part_count then raise exception 'LOCAL_COMPONENT_PART_INSERT_MISSING';end if;
 end loop;
 perform local_materialize_fixture.guard('assert_plan_set',jsonb_build_object('phase',w.phase,'plans',jsonb_array_length(w.manifest)));end$$;
create function cp7_credit.part_lines(p_part uuid)returns jsonb language sql stable set search_path=''as $$
 select jsonb_build_array(jsonb_build_object('account_id',local_materialize_fixture.get('ar'),'debit',q.amount,'credit',0),
  jsonb_build_object('account_id',local_materialize_fixture.get('credit_account'),'debit',0,'credit',q.amount))from cp7_credit.component_parts q where q.id=p_part$$;
create function cp7_credit_correction_de._post_journal_v1(p_type text,p_source uuid,p_economic date,p_description text,p_lines jsonb)returns uuid
language plpgsql volatile set search_path=''as $$declare s cp7_credit_correction_de.posting_v1;ident uuid:=gen_random_uuid();piece numeric;begin
 select *into strict s from cp7_credit_correction_de.posting_v1 r where r.backend_pid=pg_backend_pid()and r.transaction_id=txid_current()and r.actor=auth.uid();
 select amount into strict piece from cp7_credit.component_parts where id=p_source;
 if(s.source_type,s.source_id,s.economic_date,s.lines_sha256)is distinct from(p_type,p_source,p_economic,cp7_credit.native_lines_sha256(p_lines))
  or(select sum((v->>'debit')::numeric)from jsonb_array_elements(p_lines)v)<>piece
  or(select sum((v->>'credit')::numeric)from jsonb_array_elements(p_lines)v)<>piece then raise exception 'LOCAL_JOURNAL_SCOPE_LINES_MISMATCH';end if;
 insert into erp.journal_entries(id,source_type,source_id,status,economic_date,transaction_date)values(ident,p_type,p_source,'POSTED',p_economic,s.transaction_date);
 insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit)select gen_random_uuid(),ident,(v->>'account_id')::uuid,(v->>'debit')::numeric,(v->>'credit')::numeric from jsonb_array_elements(p_lines)v;
 perform local_materialize_fixture.guard('journal_stub_after_rows',jsonb_build_object('id',ident,'amount',piece));return ident;end$$;
create function cp7_credit.current_materialized_objects(uuid,uuid,uuid)returns jsonb language plpgsql volatile set search_path=''as $$declare answer jsonb;begin
 select coalesce(jsonb_agg(jsonb_build_object('object_kind','PART_JOURNAL','object_id',q.part_id,'fact_sha256',cp7_credit.pg_jsonb_sha256(cp7_credit.materialized_journal_payload(q.journal_id)))order by q.part_id),'[]')into answer from cp7_credit_correction_de.parts_v1 q;
 perform local_materialize_fixture.guard('current_materialized_objects');
 return jsonb_build_object('actual_objects',(local_materialize_fixture.get('before_profile')->'actual_objects')||answer);end$$;
create function cp7_credit.assert_current_materialized_profile(uuid,uuid,uuid)returns void language plpgsql volatile set search_path=''as $$declare w cp7_credit_correction_de.work_v1;proof jsonb;begin
 select *into strict w from cp7_credit_correction_de.work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if w.phase<>'MATERIALIZED'or not exists(select 1 from cp7_credit.financial_materializations where id=w.operation_id)
  or jsonb_array_length(w.actual_objects)<>(select count(*)from cp7_credit.financial_materialization_objects where materialization_id=w.operation_id)then raise exception 'LOCAL_FINAL_OBJECT_MARKER_MISSING';end if;
 proof:=jsonb_build_object('LOCAL_ONLY',true,'phase',w.phase,'actual_objects',jsonb_array_length(w.actual_objects),'profile_is_double',true);
 perform local_materialize_fixture.guard('assert_current_materialized_profile',proof);
 if local_materialize_fixture.get('fail_final')='true'::jsonb then raise exception 'LOCAL_AFTER_FINAL_PROFILE_FAILURE'using detail=proof::text;end if;end$$;
create function cp7_credit.assert_source_native_trigger_census_v1()returns void language plpgsql volatile set search_path=''as $$begin
 if exists(select 1 from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relname in('sales_headers','sales_payments','sales_returns','fg_stock_movements','journal_entries','hpp_versions'))then raise exception 'LOCAL_ERP_TRIGGER_DOUBLE_CHANGED';end if;
 perform local_materialize_fixture.guard('source_native_trigger_census_LOCAL_DOUBLE_ONLY');end$$;
