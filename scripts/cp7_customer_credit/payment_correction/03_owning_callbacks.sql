do $not_an_installer$begin raise exception 'OW04_PAYMENT_SOURCE_REQUIRES_COMPLETE_OWNING_COMPOSITION';end $not_an_installer$;

create function cp7_credit.payment_is_intermediate_v1(p_sale uuid)returns boolean
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select exists(select 1 from cp7_credit.payment_source_context_v1 c join cp7_credit.source_operation_work_v1 w on w.operation_id=c.operation_id
  where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()and c.actor=auth.uid()
   and w.sale_id=p_sale and w.action='PAYMENT_CORRECT'and c.phase in('INVERSE_EFFECT','REPLACEMENT_ENTERED'))
$$;

create function cp7_credit.payment_source_assert_pending_v1(p_operation uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;c cp7_credit.payment_source_context_v1;q cp7_payment_correction.requests;
begin
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_operation
  and backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and action='PAYMENT_CORRECT';
 select *into strict c from cp7_credit.payment_source_context_v1 where operation_id=w.operation_id
  and(backend_pid,transaction_id,actor,request_id)=(w.backend_pid,w.transaction_id,w.actor,w.request_id);
 select *into strict q from cp7_payment_correction.requests where actor=w.actor and request_id=w.request_id;
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'
  or current_setting('transaction_isolation')<>'read committed'
  or q.response is not null or(q.payload,q.expected_version)is distinct from(w.payload,w.expected_version)
  or w.payload_sha256 is distinct from cp7_credit.pg_jsonb_sha256(w.payload)
  or(w.payload->>'sale_id',w.payload->>'payment_id')is distinct from(w.sale_id::text,w.source_id::text)
  or not exists(select 1 from cp7_payment_correction.context pc where pc.backend_pid=w.backend_pid
   and pc.transaction_id=w.transaction_id and pc.actor=w.actor and pc.request_id=w.request_id
   and pc.payload=w.payload and pc.expected_version=w.expected_version)then
  raise exception using errcode='42501',message='CP7_CREDIT_PAYMENT_ACTUAL_PENDING_PARENT_REQUIRED';end if;
 perform cp7_credit.payment_source_ambient_guard_v1(w.sale_id);
 if exists(select 1 from cp7_sales.command_context sc where sc.backend_pid=w.backend_pid and sc.transaction_id=w.transaction_id
  and(sc.actor is distinct from w.actor or sc.sale_id is distinct from w.sale_id
   or sc.action not in('PAYMENT_REVERSE','PAYMENT')
   or sc.action='PAYMENT_REVERSE'and c.phase not in('PREPARED','INVERSE_ENTERED','INVERSE_EFFECT','INVERSE_COMPLETE')
   or sc.action='PAYMENT'and c.phase not in('REPLACEMENT_READY','REPLACEMENT_ENTERED','RECONCILING','RECONCILED','REPLACEMENT_COMPLETE')))then
  raise exception 'CP7_CREDIT_PAYMENT_ACTUAL_CHILD_CONTEXT_CHANGED';end if;
 if cp7_payment_correction.access_now()is distinct from w.authority_snapshot then
  raise exception using errcode='42501',message='CP7_CREDIT_RESTATEMENT_ACCESS_CHANGED';end if;
 if(select to_jsonb(pc)from erp.accounting_period_control pc where singleton_id=1)is distinct from w.period_snapshot
  or exists(select 1 from jsonb_array_elements(w.account_facts)x where
   (select to_jsonb(a)from erp.chart_accounts a where a.id=(x->>'id')::uuid)is distinct from x)then
  raise exception 'CP7_CREDIT_PAYMENT_PERIOD_OR_ACCOUNT_CHANGED';end if;
end $$;

create function cp7_credit.payment_source_enter_v1(p jsonb,p_request uuid,p_expected text)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare reviewed jsonb;sale uuid:=(p->>'sale_id')::uuid;op uuid:=gen_random_uuid();accounts jsonb;before_source jsonb;
begin
 reviewed:=cp7_credit.payment_source_preflight_v1(p,p_request,p_expected);
 if reviewed is null then return;end if;
 perform cp7_credit.assert_source_native_trigger_census_v1();
 if exists(select 1 from cp7_credit.source_operation_work_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'CP7_CREDIT_PAYMENT_NESTED_SOURCE_OPERATION';end if;
 select jsonb_agg(to_jsonb(a)order by a.id)into accounts from erp.chart_accounts a where a.id in(
  select ch.ar_account_id from cp7_credit.cohorts ch where ch.source_sale_id=sale
  union select ch.credit_account_id from cp7_credit.cohorts ch where ch.source_sale_id=sale
  union select ca.coa_account_id from erp.cash_accounts ca where ca.id=(p#>>'{replacement,cash_account_id}')::uuid);
 before_source:=cp7_credit.source_native_snapshot_v1(sale);
 insert into cp7_credit.source_operation_work_v1(operation_id,operation_ordinal,backend_pid,transaction_id,actor,request_id,
  action,sale_id,source_id,expected_version,payload,payload_sha256,authority_snapshot,phase,before_source,before_ordinal_input,
  before_ordinal_result,before_financial_profile,account_facts,period_snapshot)
 values(op,1,pg_backend_pid(),txid_current(),auth.uid(),p_request,'PAYMENT_CORRECT',sale,(p->>'payment_id')::uuid,
  p_expected,p,cp7_credit.pg_jsonb_sha256(p),reviewed->'authority','PREPARED',before_source,reviewed->'before_input',
  reviewed->'before_result',cp7_credit.inspect_current_materialized_profile(sale,sale,sale),accounts,reviewed->'period');
 insert into cp7_credit.payment_source_context_v1(operation_id,backend_pid,transaction_id,actor,request_id,phase,projected_input,projected_result)
 values(op,pg_backend_pid(),txid_current(),auth.uid(),p_request,'PREPARED',reviewed->'proposed',reviewed->'result');
 perform cp7_credit.payment_source_assert_pending_v1(op);
end $$;

-- Dispatch returns false only when no declared compound owner exists. A
-- mismatched action/source while that owner exists is an error, not fallback.
create function cp7_credit.payment_native_enter_v1(p_action text,p_source uuid)returns boolean
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.payment_source_context_v1;w cp7_credit.source_operation_work_v1;p erp.sales_payments;actual jsonb;expected jsonb;
begin
 select *into c from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if not found then return false;end if;
 perform cp7_credit.payment_source_assert_pending_v1(c.operation_id);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=c.operation_id;
 if p_action='PAYMENT_REVERSE'and p_source=w.source_id and c.phase='PREPARED'then
  if cp7_credit.source_native_snapshot_v1(w.sale_id)is distinct from w.before_source
   or cp7_credit.source_reconciliation_input_v1(w.sale_id)is distinct from w.before_ordinal_input then
   raise exception 'CP7_CREDIT_PAYMENT_INVERSE_ENTRY_CHANGED';end if;
  update cp7_credit.payment_source_context_v1 set phase='INVERSE_ENTERED'where operation_id=w.operation_id;
 elsif p_action='PAYMENT'and c.phase='REPLACEMENT_READY'then
  select *into strict p from erp.sales_payments where id=p_source;
  if p.status<>'DRAFT'or p.sale_id<>w.sale_id or p.replaces_payment_id is not null
   or p.amount is distinct from(w.payload#>>'{replacement,amount}')::numeric
   or p.payment_date is distinct from(w.payload#>>'{replacement,payment_date}')::timestamptz
   or p.cash_account_id is distinct from(w.payload#>>'{replacement,cash_account_id}')::uuid
   or p.payment_method is distinct from w.payload#>>'{replacement,payment_method}'
   or p.reference_number is distinct from w.payload#>>'{replacement,reference_number}'
   or p.notes is distinct from w.payload#>>'{replacement,notes}'
   or p.payment_number is distinct from left((select x->>'payment_number'from jsonb_array_elements(w.before_source->'payments')x
    where x->>'id'=w.source_id::text),20)||' · K-'||replace(w.request_id::text,'-','')then
   raise exception 'CP7_CREDIT_PAYMENT_REPLACEMENT_DRAFT_CHANGED';end if;
  actual:=cp7_credit.source_native_snapshot_v1(w.sale_id);
  expected:=jsonb_set(c.replacement_before,'{payments}',cp7_credit.source_rows_v1((c.replacement_before->'payments')||jsonb_build_array(to_jsonb(p))));
  if cp7_credit.source_rows_v1(actual->'payments')is distinct from expected->'payments'
   or actual-'payments'is distinct from expected-'payments'then raise exception 'CP7_CREDIT_PAYMENT_REPLACEMENT_ENTRY_CHANGED';end if;
  update cp7_credit.payment_source_context_v1 set phase='REPLACEMENT_ENTERED',replacement_id=p.id,replacement_draft=to_jsonb(p)
   where operation_id=w.operation_id;
 else raise exception 'CP7_CREDIT_PAYMENT_NATIVE_LEG_NOT_ADMITTED';end if;
 return true;
end $$;

create function cp7_credit.payment_inverse_effect_v1(p_action text,p_source uuid)returns boolean
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.payment_source_context_v1;w cp7_credit.source_operation_work_v1;actual jsonb;
begin
 select *into c from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if not found then return false;end if;
 perform cp7_credit.payment_source_assert_pending_v1(c.operation_id);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=c.operation_id;
 if(p_action,p_source,c.phase)is distinct from('PAYMENT_REVERSE',w.source_id,'INVERSE_ENTERED')then
  raise exception 'CP7_CREDIT_PAYMENT_INVERSE_EFFECT_PHASE_CHANGED';end if;
 actual:=cp7_credit.source_native_snapshot_v1(w.sale_id);
 perform cp7_credit.source_inverse_proof_v1(w.before_source,actual,'PAYMENT_REVERSE',w.source_id);
 update cp7_credit.payment_source_context_v1 set phase='INVERSE_EFFECT',inverse_native=actual where operation_id=w.operation_id;
 return true;
end $$;

-- Return only the ACTUAL unchanged signed ledger adjustment in the private
-- half-transaction. A negative intermediate effective payment is not a final
-- invoice fact, quote or receipt. No projection is returned as actual money.
create function cp7_credit.payment_intermediate_adjustment_v1(p_sale uuid)returns numeric
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.payment_source_context_v1;w cp7_credit.source_operation_work_v1;actual jsonb;profile jsonb;expected jsonb;
begin
 select c0.*into strict c from cp7_credit.payment_source_context_v1 c0 join cp7_credit.source_operation_work_v1 w0 on w0.operation_id=c0.operation_id
  where c0.backend_pid=pg_backend_pid()and c0.transaction_id=txid_current()and w0.sale_id=p_sale;
 perform cp7_credit.payment_source_assert_pending_v1(c.operation_id);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=c.operation_id;
 actual:=cp7_credit.source_native_snapshot_v1(p_sale);
 if c.phase='INVERSE_EFFECT'then expected:=c.inverse_native;
 elsif c.phase='REPLACEMENT_ENTERED'then
  expected:=jsonb_set(c.replacement_before,'{payments}',cp7_credit.source_rows_v1((c.replacement_before->'payments')||jsonb_build_array(c.replacement_draft)));
 else raise exception 'CP7_CREDIT_PAYMENT_INTERMEDIATE_PHASE_REQUIRED';end if;
 if cp7_credit.source_rows_v1(actual->'payments')is distinct from cp7_credit.source_rows_v1(expected->'payments')
  or actual-'payments'is distinct from expected-'payments'then raise exception 'CP7_CREDIT_PAYMENT_INTERMEDIATE_NATIVE_CHANGED';end if;
 profile:=cp7_credit.inspect_current_materialized_profile(p_sale,p_sale,p_sale);
 if profile is distinct from w.before_financial_profile then raise exception 'CP7_CREDIT_PAYMENT_INTERMEDIATE_LEDGER_CHANGED';end if;
 return(profile->>'U')::numeric-(profile->>'I')::numeric;
end $$;

create function cp7_credit.payment_replacement_prepare_v1(p_request uuid,p_neutral uuid,p_effective uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.payment_source_context_v1;w cp7_credit.source_operation_work_v1;actual jsonb;
begin
 select *into c from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and request_id=p_request;
 if not found then return;end if;
 perform cp7_credit.payment_source_assert_pending_v1(c.operation_id);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=c.operation_id;
 if c.phase<>'INVERSE_COMPLETE'then raise exception 'CP7_CREDIT_PAYMENT_REPLACEMENT_PREPARE_PHASE_CHANGED';end if;
 actual:=cp7_credit.source_native_snapshot_v1(w.sale_id);
 perform cp7_credit.payment_time_pair_v1(c.inverse_final,actual,w.source_id,p_neutral,p_effective);
 update cp7_credit.payment_source_context_v1 set phase='REPLACEMENT_READY',replacement_before=actual,
  time_neutral_id=p_neutral,effective_inverse_id=p_effective where operation_id=w.operation_id;
end $$;

create function cp7_credit.payment_posted_reconcile_v1(p_payment uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.payment_source_context_v1;w cp7_credit.source_operation_work_v1;actual jsonb;comp record;result jsonb;
begin
 select *into c from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if not found then return;end if;
 perform cp7_credit.payment_source_assert_pending_v1(c.operation_id);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=c.operation_id;
 if c.phase<>'REPLACEMENT_ENTERED'or c.replacement_id is distinct from p_payment then
  raise exception 'CP7_CREDIT_PAYMENT_POSTED_RECONCILE_PHASE_CHANGED';end if;
 insert into cp7_credit.payment_source_legs_v1(operation_id,inverse_native,inverse_final,replacement_before,replacement_draft,
  replacement_id,time_neutral_id,effective_inverse_id)
 values(c.operation_id,c.inverse_native,c.inverse_final,c.replacement_before,c.replacement_draft,c.replacement_id,c.time_neutral_id,c.effective_inverse_id);
 update cp7_credit.payment_source_context_v1 set phase='RECONCILING'where operation_id=w.operation_id;
 update cp7_credit.source_operation_work_v1 set phase='ENTERED'where operation_id=w.operation_id;
 actual:=cp7_credit.assert_source_actual_v1(w.operation_id);
 perform cp7_credit.store_source_adjustments_v1(w.operation_id,actual);
 for comp in select cc.id from cp7_credit.source_operation_plans_v1 sp join cp7_credit.recognition_components cc on cc.plan_id=sp.plan_id
  where sp.operation_id=w.operation_id order by sp.family_ordinal,cc.ordinal loop
  perform cp7_credit.post_source_adjustment_component_v1(comp.id);
 end loop;
 perform cp7_credit.materialize_source_operation_v1(w.operation_id);
 update cp7_credit.payment_source_context_v1 set phase='RECONCILED'where operation_id=w.operation_id;
end $$;

create function cp7_credit.payment_native_complete_v1(p_action text,p_source uuid)returns boolean
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.payment_source_context_v1;w cp7_credit.source_operation_work_v1;actual jsonb;inverse uuid;
begin
 select *into c from cp7_credit.payment_source_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if not found then return false;end if;
 perform cp7_credit.payment_source_assert_pending_v1(c.operation_id);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=c.operation_id;
 actual:=cp7_credit.source_native_snapshot_v1(w.sale_id);
 if(p_action,p_source,c.phase)=('PAYMENT_REVERSE',w.source_id,'INVERSE_EFFECT')then
  select reversal_journal_entry_id into strict inverse from erp.sales_payment_reversal_facts where payment_id=w.source_id;
  perform cp7_credit.source_native_terminal_header_v1(c.inverse_native,actual,inverse);
  update cp7_credit.payment_source_context_v1 set phase='INVERSE_COMPLETE',inverse_final=actual where operation_id=w.operation_id;
 elsif(p_action,p_source,c.phase)=('PAYMENT',c.replacement_id,'RECONCILED')then
  perform cp7_credit.payment_terminal_header_v1(w.actual_source,actual,c.replacement_id);
  update cp7_credit.payment_source_context_v1 set phase='REPLACEMENT_COMPLETE'where operation_id=w.operation_id;
 else raise exception 'CP7_CREDIT_PAYMENT_NATIVE_COMPLETE_PHASE_CHANGED';end if;
 return true;
end $$;
