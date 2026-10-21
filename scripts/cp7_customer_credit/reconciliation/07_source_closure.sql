do $not_an_installer$begin raise exception 'OW04_RECONCILIATION_REQUIRES_COMPLETE_ATOMIC_COMPOSITION';end $not_an_installer$;

create function cp7_credit.assert_source_final_ar_status_v1(p_sale uuid,p_source jsonb,p_profile jsonb)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare net numeric;paid numeric;raw_ar numeric;ar uuid;current_i numeric;current_u numeric;
begin
 if(p_source#>>'{sale,id}',p_profile->>'sale_id',p_profile->>'root_sale_id',p_profile->>'current_leaf_id')
  is distinct from(p_sale::text,p_sale::text,p_sale::text,p_sale::text)then
  raise exception 'CP7_CREDIT_SOURCE_FINAL_PROFILE_IDENTITY_CHANGED';end if;
 select coalesce(sum((x->>'line_total')::numeric),0)into net from jsonb_array_elements(p_source->'items')x;
 net:=net-(select coalesce(sum((i->>'refund_amount')::numeric),0)from jsonb_array_elements(p_source->'return_items')i
  where exists(select 1 from jsonb_array_elements(p_source->'returns')r where r->>'id'=i->>'return_id'and r->>'status'='POSTED'));
 current_i:=(p_profile->>'I')::numeric;current_u:=(p_profile->>'U')::numeric;
 select coalesce(sum((x->>'amount')::numeric),0)into paid from jsonb_array_elements(p_source->'payments')x where x->>'status'='POSTED';
 paid:=paid+current_u-current_i;
 if net is null or paid is null or current_u is distinct from 0::numeric or net<0 or paid<0 or paid>net
  or p_source#>>'{sale,status}'is distinct from(case when paid=net then'PAID'when paid>0 then'PARTIAL_PAID'else'POSTED'end)then
  raise exception 'CP7_CREDIT_SOURCE_FINAL_AR_OR_STATUS_MISMATCH';end if;
 select distinct c.ar_account_id into strict ar from cp7_credit.cohorts c where c.source_sale_id=p_sale;
 select coalesce(sum(l.debit-l.credit),0)into raw_ar from erp.journal_lines l where l.account_id=ar and l.journal_entry_id in(
  select substring(x->>'id'from 9)::uuid from jsonb_array_elements(p_source->'base_events')x
  union select j.journal_id from cp7_credit.component_journals j join cp7_credit.component_parts q on q.id=j.part_id
   join cp7_credit.recognition_components cc on cc.id=q.component_id join cp7_credit.recognition_plans p on p.id=cc.plan_id
   where p.family_root_sale_id=p_sale and exists(select 1 from jsonb_array_elements(p_profile->'actual_objects')o
    where o->>'object_kind'='PART_JOURNAL'and(o->>'object_id')::uuid=q.id));
 if raw_ar is distinct from net-paid then raise exception 'CP7_CREDIT_SOURCE_FINAL_RAW_AR_MISMATCH';end if;
end $$;

create function cp7_credit.source_completion_manifest_v1(p_operation uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','ow04.source-operation-completion.v1','operation_id',m.operation_id,
  'actual_manifest_sha256',m.actual_manifest_sha256,'final_native_source',c.final_native_source,'final_profile',c.final_profile,
  'header_proof',cp7_credit.source_native_terminal_header_v1(m.actual_source,c.final_native_source,(m.actual_source_proof->>'inverse_journal_id')::uuid))
 from cp7_credit.source_operation_materializations_v1 m join cp7_credit.source_operation_completions_v1 c using(operation_id)
 where m.operation_id=p_operation
$$;

create function cp7_credit.assert_source_completion_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare m cp7_credit.source_operation_materializations_v1;c cp7_credit.source_operation_completions_v1;
 objects jsonb;expected_i numeric;
begin
 select *into strict m from cp7_credit.source_operation_materializations_v1 where operation_id=p_operation;
 select *into strict c from cp7_credit.source_operation_completions_v1 where operation_id=p_operation;
 perform cp7_credit.assert_source_materialization_v1(m.operation_id);
 if c.final_manifest_sha256 is distinct from cp7_credit.pg_jsonb_sha256(cp7_credit.source_completion_manifest_v1(m.operation_id))
  or c.final_native_source-array['sale','hpp_support']is distinct from m.actual_source-array['sale','hpp_support']then
  raise exception 'CP7_CREDIT_SOURCE_FINAL_NATIVE_MANIFEST_CHANGED';end if;
 select coalesce(jsonb_agg(x order by x->>'object_kind'collate"C",x->>'object_id'collate"C"),'[]')into objects
  from jsonb_array_elements((m.before_financial_profile->'actual_objects')||m.actual_objects)x;
 expected_i:=(m.before_financial_profile->>'I')::numeric+(select coalesce(sum(p.net_amount),0)
  from cp7_credit.source_operation_plans_v1 sp join cp7_credit.recognition_plans p on p.id=sp.plan_id where sp.operation_id=m.operation_id);
 if c.final_profile->'actual_objects'is distinct from objects
  or c.final_profile->>'actual_objects_sha256'is distinct from cp7_credit.pg_jsonb_sha256(objects)
  or(c.final_profile->>'I')::numeric is distinct from expected_i
  or(c.final_profile->>'U')::numeric is distinct from 0::numeric
  or(c.final_profile->>'adjustment')::numeric is distinct from -expected_i then
  raise exception 'CP7_CREDIT_SOURCE_FINAL_FINANCIAL_PROFILE_CHANGED';end if;
 perform cp7_credit.assert_source_final_ar_status_v1(m.sale_id,c.final_native_source,c.final_profile);
end $$;

-- Deferred closure validates the exact historical receipt and completion;
-- a later lawful operation may have changed the current invoice meanwhile.
-- Current state is checked against the latest explicit operation ordinal,
-- never forced to equal an earlier request's old status or row version.
create function cp7_credit.assert_source_operation_closed_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare m cp7_credit.source_operation_materializations_v1;c cp7_credit.source_operation_completions_v1;
 q cp7_sales.requests;expected jsonb;profile jsonb;
begin
 select *into strict m from cp7_credit.source_operation_materializations_v1 where operation_id=p_operation;
 select *into strict c from cp7_credit.source_operation_completions_v1 where operation_id=m.operation_id;
 select *into strict q from cp7_sales.requests where actor=m.actor and request_id=m.request_id;
 perform cp7_credit.assert_source_completion_v1(m.operation_id);
 expected:=jsonb_build_object('contract_version','cp7.sales-outcome.v1','kind','COMMITTED_OUTCOME','action',m.action,'request_id',m.request_id,
  'sale_id',m.sale_id,'status',c.final_native_source#>>'{sale,status}','row_version',c.final_native_source#>>'{sale,row_version}');
 if m.action='RETURN_REVERSE'then expected:=expected||jsonb_build_object('return_id',m.source_id,'return_status','REVERSED');
 else expected:=expected||jsonb_build_object('payment_id',m.source_id,'payment_status','REVERSED');end if;
 if(q.action,q.payload,q.expected_version,q.response)is distinct from(m.action,m.payload,m.expected_version,expected)
  or exists(select 1 from cp7_credit.source_operation_work_v1 w where w.operation_id=m.operation_id
   or(w.backend_pid,w.transaction_id)=(m.backend_pid,m.transaction_id))
  or exists(select 1 from cp7_credit.execution_context where backend_pid=m.backend_pid and transaction_id=m.transaction_id)
  or exists(select 1 from cp7_credit.posting_scope where backend_pid=m.backend_pid and transaction_id=m.transaction_id)
  or exists(select 1 from cp7_credit.source_mutation_scope where backend_pid=m.backend_pid and transaction_id=m.transaction_id)
  or exists(select 1 from cp7_sales.command_context where backend_pid=m.backend_pid and transaction_id=m.transaction_id)then
  raise exception 'CP7_CREDIT_SOURCE_FINAL_RECEIPT_OR_SCOPE_NOT_CLOSED';end if;
 perform cp7_credit.assert_current_materialized_profile(m.sale_id,m.sale_id,m.sale_id);
 profile:=cp7_credit.inspect_current_materialized_profile(m.sale_id,m.sale_id,m.sale_id);
 perform cp7_credit.assert_source_final_ar_status_v1(m.sale_id,cp7_credit.source_native_snapshot_v1(m.sale_id),profile);
end $$;

create function cp7_credit.enforce_source_operation_closure_v1()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='UPDATE'and old.operation_id is distinct from new.operation_id then
  perform cp7_credit.assert_source_operation_closed_v1(old.operation_id);
 end if;
 perform cp7_credit.assert_source_operation_closed_v1(new.operation_id);
 return null;
end $$;

do $source_closure$declare t text;begin
 foreach t in array array['source_operation_work_v1','source_operation_materializations_v1','source_operation_plans_v1',
  'source_operation_completions_v1','source_operation_part_seals_v1']loop
  execute 'create constraint trigger source_operation_closed after insert or update on cp7_credit.'||t||
   ' deferrable initially deferred for each row execute function cp7_credit.enforce_source_operation_closure_v1()';
 end loop;
end $source_closure$;

do $private_source_closure$declare sig text;begin
 foreach sig in array array['assert_source_final_ar_status_v1(uuid,jsonb,jsonb)','source_completion_manifest_v1(uuid)',
  'assert_source_completion_v1(uuid)','assert_source_operation_closed_v1(uuid)','enforce_source_operation_closure_v1()']loop
  execute 'alter function cp7_credit.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write';
 end loop;
end $private_source_closure$;
