-- Integrated by root after independent source proposal/counter review.
-- Native runtime proof remains pending; owning composition is mandatory.
do $not_an_installer$begin raise exception 'OW04_RECONCILIATION_REQUIRES_COMPLETE_ATOMIC_COMPOSITION';end $not_an_installer$;

create function cp7_credit.assert_source_operation_plan_set_v1(p_operation uuid)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;actual jsonb;expected_ids uuid[];actual_ids uuid[];side_ids uuid[];
begin
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_operation
  and backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 if w.phase<>'RECONCILING'or jsonb_typeof(w.plan_manifest)is distinct from'array'then
  raise exception 'CP7_CREDIT_SOURCE_OPERATION_MANIFEST_REQUIRED';end if;
 if exists(select 1 from jsonb_array_elements(w.plan_manifest)with ordinality a(m,n)where
   jsonb_typeof(m)is distinct from'object'or not(m?&array['plan_id','family_id','family_ordinal','cohort_id','request_ordinal','kernel_sha256','components','parts'])
   or m-array['plan_id','family_id','family_ordinal','cohort_id','request_ordinal','kernel_sha256','components','parts']<>'{}'::jsonb
   or(m->>'plan_id')is null or(m->>'family_id')is null or(m->>'cohort_id')is null
   or(m->>'request_ordinal')::bigint is distinct from n
   or(m->>'family_ordinal')::bigint<=0 or(m->>'kernel_sha256')!~'^[0-9a-f]{64}$'
   or jsonb_typeof(m->'components')is distinct from'array'or jsonb_array_length(m->'components')=0
   or jsonb_typeof(m->'parts')is distinct from'array'or jsonb_array_length(m->'parts')=0)
  or exists(select 1 from jsonb_array_elements(w.plan_manifest)m group by m->>'plan_id'having count(*)<>1)
  or exists(select 1 from jsonb_array_elements(w.plan_manifest)m group by m->>'family_id'having count(*)<>1)
  or exists(select 1 from jsonb_array_elements(w.plan_manifest)m group by m->>'cohort_id'having count(*)<>1)then
  raise exception 'CP7_CREDIT_SOURCE_OPERATION_MANIFEST_CHANGED';end if;
 select coalesce(array_agg((m->>'plan_id')::uuid order by(m->>'plan_id')::uuid),'{}')into expected_ids
  from jsonb_array_elements(w.plan_manifest)m;
 select coalesce(array_agg(p.id order by p.id),'{}')into actual_ids from cp7_credit.recognition_plans p
  where p.actor=w.actor and p.request_id=w.request_id;
 select coalesce(array_agg(s.plan_id order by s.plan_id),'{}')into side_ids from cp7_credit.source_operation_plans_v1 s
  where s.operation_id=w.operation_id;
 -- Both directions, including actual plan rows without a sidecar, are required.
 if expected_ids is distinct from actual_ids or expected_ids is distinct from side_ids then
  raise exception 'CP7_CREDIT_SOURCE_OPERATION_PLAN_SET_CHANGED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('plan_id',p.id,'family_id',s.family_id,'family_ordinal',s.family_ordinal,
   'cohort_id',p.cohort_id,'request_ordinal',p.request_ordinal,'kernel_sha256',cp7_credit.pg_jsonb_sha256(p.kernel_result),
   'components',(select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'ordinal',c.ordinal,'component',c.kernel_component)order by c.ordinal),'[]')
    from cp7_credit.recognition_components c where c.plan_id=p.id),
   'parts',(select coalesce(jsonb_agg(jsonb_build_object('id',q.id,'component_id',q.component_id,'ordinal',q.ordinal,
    'amount',cp7_credit.cent_text(q.amount))order by c.ordinal,q.ordinal),'[]')
    from cp7_credit.recognition_components c join cp7_credit.component_parts q on q.component_id=c.id where c.plan_id=p.id))
   order by p.request_ordinal),'[]')into actual from cp7_credit.source_operation_plans_v1 s
  join cp7_credit.recognition_plans p on p.id=s.plan_id where s.operation_id=w.operation_id;
 if actual is distinct from w.plan_manifest or exists(select 1 from cp7_credit.source_operation_plans_v1 s
  join cp7_credit.return_families f on f.id=s.family_id join cp7_credit.recognition_plans p on p.id=s.plan_id
  join cp7_credit.cohorts c on c.id=p.cohort_id where s.operation_id=w.operation_id and
   (f.family_root_sale_id<>w.sale_id or f.family_ordinal<>s.family_ordinal or c.family_id<>f.id
    or p.plan_kind<>'ADJUSTMENT'or p.owning_action<>w.action or p.family_root_sale_id<>w.sale_id
    or p.actor<>w.actor or p.request_id<>w.request_id or p.payload_sha256<>w.payload_sha256
    or p.review_sha256 is distinct from cp7_credit.source_operation_binding_sha256_v1(w.operation_id)
    or s.source_binding_sha256 is distinct from cp7_credit.source_operation_binding_sha256_v1(w.operation_id)
    or s.canonical_plan is distinct from p.kernel_result))
  or exists(select 1 from cp7_credit.source_operation_plans_v1 sp join cp7_credit.recognition_plans p on p.id=sp.plan_id
   join cp7_credit.recognition_components c on c.plan_id=p.id where sp.operation_id=w.operation_id and
    (c.kernel_component is distinct from p.kernel_result->'components'->(c.ordinal-1)
     or c.component_sha256_pg is distinct from cp7_credit.pg_jsonb_sha256(c.kernel_component)
     or c.kernel_component is distinct from jsonb_build_object('amount',cp7_credit.cent_text(c.amount),
      'economic_date',c.economic_date::text,'transaction_date',c.transaction_date::text,
      'previous_economic_date',c.previous_economic_date::text,'previous_transaction_date',c.previous_transaction_date::text,
      'corners',c.corners)))then
  raise exception 'CP7_CREDIT_SOURCE_OPERATION_PLAN_SET_CHANGED';end if;
end $$;

-- Read-only reentry under already-held source/account/period locks. No lock
-- acquisition is permitted here; a new source set causes exact-equality refusal.
create function cp7_credit.source_adjustment_fresh_v1(p_operation uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;inp jsonb;fresh jsonb;f jsonb;fi jsonb;s cp7_credit.source_operation_plans_v1;
 expected_families uuid[];actual_families uuid[];blocked jsonb;
begin
 perform cp7_credit.assert_source_operation_work_v1(p_operation);
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_operation;
 if w.phase<>'RECONCILING'then raise exception 'CP7_CREDIT_SOURCE_RECONCILING_REQUIRED';end if;
 perform cp7_credit.assert_source_operation_plan_set_v1(w.operation_id);
 -- Root-owned exact B->N verifier: actual inverse/source/date, physical/HPP
 -- allowed delta, preserved immutable originals. This is NOT a boolean stub.
 perform cp7_credit.assert_source_actual_v1(w.operation_id);
 if cp7_credit.source_native_snapshot_v1(w.sale_id)is distinct from w.actual_source then
  raise exception 'CP7_CREDIT_SOURCE_NATIVE_BOUNDARY_CHANGED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('event_id',e.id,'cohort_id',e.cohort_id,'event_kind',e.event_kind,
  'journal_id',e.journal_id,'source_sale_id',c.source_sale_id,'source_return_id',c.source_return_id)order by e.id),'[]')into blocked
  from cp7_credit.consumption_events e join cp7_credit.cohorts c on c.id=e.cohort_id
  join cp7_credit.return_families rf on rf.id=c.family_id where rf.family_root_sale_id=w.sale_id or e.target_sale_id=w.sale_id;
 if jsonb_array_length(blocked)>0 then raise exception 'CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO'using detail=blocked::text;end if;
 -- The existing reader has a one-way check. It is safe here only AFTER the
 -- stronger exact-set proof above. It removes ALL own part IDs together.
 inp:=cp7_credit.source_reconciliation_input_v1(w.sale_id,w.operation_id);
 if inp is distinct from w.actual_ordinal_input then raise exception 'CP7_CREDIT_SOURCE_RETAINED_BASELINE_CHANGED';end if;
 fresh:=ow04_ordinal_wrapper.reconcile_v1(inp);
 if fresh is distinct from w.actual_ordinal_result or not(fresh->>'arithmetic_supported')::boolean then
  raise exception 'CP7_CREDIT_SOURCE_ORDINAL_RESULT_CHANGED';end if;
 select coalesce(array_agg((x->'registration'->>'family_id')::uuid order by(x->'registration'->>'family_id')::uuid),'{}')into expected_families
  from jsonb_array_elements(fresh->'families')x where(x->>'has_reconciliation_effect')::boolean;
 select coalesce(array_agg(family_id order by family_id),'{}')into actual_families
  from cp7_credit.source_operation_plans_v1 where operation_id=w.operation_id;
 if expected_families is distinct from actual_families then raise exception 'CP7_CREDIT_SOURCE_AFFECTED_FAMILY_SET_CHANGED';end if;
 for f in select value from jsonb_array_elements(fresh->'families')loop
  -- Reject one unsupported family atom even if the invoice/global net looks safe.
  if coalesce((f->>'needs_cohort_configuration')::boolean,false)
   or exists(select 1 from jsonb_array_elements(f->'reconciliation_components')a where(a->>'amount')::numeric>=0)then
   raise exception 'CP7_CREDIT_SOURCE_RECONCILIATION_REVIEW_REQUIRED';end if;
  if not(f->>'has_reconciliation_effect')::boolean then continue;end if;
  if f->>'plan_kind'<>'ADJUSTMENT'then raise exception 'CP7_CREDIT_SOURCE_RECONCILIATION_REVIEW_REQUIRED';end if;
  select *into strict s from cp7_credit.source_operation_plans_v1 where operation_id=w.operation_id
   and family_id=(f->'registration'->>'family_id')::uuid;
  select x into strict fi from jsonb_array_elements(inp->'families')x where x->>'family_id'=s.family_id::text;
  if s.full_family_result is distinct from f or s.canonical_plan is distinct from cp7_credit.source_adjustment_kernel_v1(f)
   or s.before_retained_events is distinct from fi->'retained_recognition'
   or s.before_consumptions is distinct from fi->'consumptions'
   or jsonb_array_length(fi->'consumptions')<>0
   or not exists(select 1 from cp7_credit.recognition_plans p join cp7_credit.cohorts c on c.id=p.cohort_id
    where p.id=s.plan_id and c.family_id=s.family_id and c.initial_mode='CREDIT'
     and exists(select 1 from jsonb_array_elements(w.before_financial_profile->'actual_objects')o
      where o->>'object_kind'='COHORT'and(o->>'object_id')::uuid=c.id))then
   raise exception 'CP7_CREDIT_SOURCE_FAMILY_ADJUSTMENT_CHANGED';end if;
 end loop;
 return fresh;
end $$;

create function cp7_credit.assert_source_adjustment_owner_base_v1(p_plan uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare p cp7_credit.recognition_plans;s cp7_credit.source_operation_plans_v1;w cp7_credit.source_operation_work_v1;
 e cp7_credit.execution_context;c cp7_credit.cohorts;a jsonb;
begin
 select *into strict p from cp7_credit.recognition_plans where id=p_plan;
 select *into strict s from cp7_credit.source_operation_plans_v1 where plan_id=p.id;
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=s.operation_id
  and backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 perform cp7_credit.assert_source_operation_work_v1(w.operation_id);
 if w.phase<>'RECONCILING'or w.active_plan_id is distinct from p.id then
  raise exception 'CP7_CREDIT_SOURCE_ACTIVE_PLAN_REQUIRED';end if;
 select *into strict e from cp7_credit.execution_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id and actor=w.actor;
 if(p.plan_kind,p.owning_action,p.actor,p.request_id,p.payload_sha256,p.review_sha256)is distinct from
   ('ADJUSTMENT',w.action,w.actor,w.request_id,w.payload_sha256,cp7_credit.source_operation_binding_sha256_v1(w.operation_id))
  or(e.plan_id,e.request_id,e.owning_action,e.payload_sha256,e.review_sha256,e.authority_snapshot)is distinct from
   (p.id,w.request_id,w.action,w.payload_sha256,p.review_sha256,w.authority_snapshot)then
  raise exception 'CP7_CREDIT_SOURCE_ADJUSTMENT_OWNER_MISMATCH';end if;
 perform cp7_credit.source_adjustment_fresh_v1(w.operation_id);
 select *into strict c from cp7_credit.cohorts where id=p.cohort_id;
 a:=cp7_credit.credit_account_facts_v1(c.credit_account_id);
 -- Actual account eligibility/reconciliation is fresh. Only the account's
 -- immutable master snapshot is compared, since lawful own ADJs add journal IDs.
 if a->'account'is distinct from c.credit_account_snapshot->'account'
  or(select to_jsonb(ar)from erp.chart_accounts ar where ar.id=c.ar_account_id)is distinct from c.source_ar_snapshot
  or cp7_credit.account_by_mapping_v1('AR_CUSTOMER')is distinct from c.ar_account_id
  or c.ar_account_id=c.credit_account_id
  or not exists(select 1 from jsonb_array_elements(w.account_facts)x where(x->>'id')::uuid=c.ar_account_id)
  or not exists(select 1 from jsonb_array_elements(w.account_facts)x where(x->>'id')::uuid=c.credit_account_id)then
  raise exception 'CP7_CREDIT_SOURCE_ADJUSTMENT_ACCOUNT_CHANGED';end if;
end $$;

-- Exact current journal contract shared by prior-history verification and the
-- new per-part seal. Includes every dimension, source pointer, sign and pair.
create function cp7_credit.assert_source_adjustment_part_journal_v1(p_part uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare q cp7_credit.component_parts;c cp7_credit.recognition_components;o cp7_credit.component_journals;j erp.journal_entries;
 actual_lines jsonb;
begin
 select *into strict q from cp7_credit.component_parts where id=p_part;
 select *into strict c from cp7_credit.recognition_components where id=q.component_id;
 select *into strict o from cp7_credit.component_journals where part_id=q.id;
 select *into strict j from erp.journal_entries where id=o.journal_id;
 select coalesce(jsonb_agg(jsonb_build_object('account_id',l.account_id,'customer_id',l.customer_id,'vendor_id',l.vendor_id,
  'contractor_id',l.contractor_id,'product_id',l.product_id,'po_id',l.po_id,'debit',l.debit,'credit',l.credit)),'[]')into actual_lines
  from erp.journal_lines l where l.journal_entry_id=j.id;
 if(j.source_type,j.source_id,j.reversal_of_id,j.economic_date,j.transaction_date,j.status)is distinct from
   ('CP7_CUSTOMER_CREDIT_RECOGNITION',q.id,null::uuid,c.economic_date,c.transaction_date,'POSTED')
  or(o.economic_date,o.transaction_date,o.lines_sha256_pg)is distinct from
   (c.economic_date,c.transaction_date,cp7_credit.native_lines_sha256(cp7_credit.part_lines(q.id)))
  or jsonb_array_length(actual_lines)<>2
  or cp7_credit.initial_line_semantics_v1(actual_lines)is distinct from cp7_credit.initial_line_semantics_v1(cp7_credit.part_lines(q.id))
  or exists(select 1 from erp.journal_entries x where x.reversal_of_id=j.id or(x.source_type='JOURNAL_REVERSAL'and x.source_id=j.id))
  or(select count(*)from erp.journal_entries x where x.source_type='CP7_CUSTOMER_CREDIT_RECOGNITION'and x.source_id=q.id)<>1 then
  raise exception 'CP7_CREDIT_SOURCE_PART_ACTUAL_JOURNAL_CHANGED';end if;
end $$;

-- p_just_linked is legal only while the exact new part's posting_scope is still
-- present, after Native returns and its component_journals row was inserted.
-- It is NOT a general pending-part filter or a partial-resume capability.
create function cp7_credit.assert_source_operation_part_seals_v1(p_operation uuid,p_just_linked uuid default null)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;x cp7_credit.posting_scope;r record;
 v_part cp7_credit.component_parts;v_component cp7_credit.recognition_components;v_cohort cp7_credit.cohorts;
begin
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_operation;
 if p_just_linked is not null then
  select *into strict x from cp7_credit.posting_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id and actor=w.actor;
  select *into strict v_part from cp7_credit.component_parts where id=p_just_linked;
  select *into strict v_component from cp7_credit.recognition_components where id=v_part.component_id;
  select ch.*into strict v_cohort from cp7_credit.cohorts ch join cp7_credit.recognition_plans p on p.cohort_id=ch.id where p.id=v_component.plan_id;
  if(x.request_id,x.post_kind,x.plan_id,x.component_id,x.part_id,x.source_sale_id,x.source_return_id,
    x.source_type,x.source_id,x.economic_date,x.transaction_date,x.lines_sha256_pg)is distinct from
   (w.request_id,'COMPONENT',v_component.plan_id,v_component.id,v_part.id,v_cohort.source_sale_id,v_cohort.source_return_id,
    'CP7_CUSTOMER_CREDIT_RECOGNITION',v_part.id,v_component.economic_date,v_component.transaction_date,cp7_credit.native_lines_sha256(cp7_credit.part_lines(v_part.id)))
   or v_component.plan_id is distinct from w.active_plan_id
   or not exists(select 1 from cp7_credit.source_operation_plans_v1 sp where sp.operation_id=w.operation_id and sp.plan_id=v_component.plan_id)
   or exists(select 1 from cp7_credit.source_operation_part_seals_v1 where part_id=p_just_linked)
   or not exists(select 1 from cp7_credit.component_journals where part_id=p_just_linked)then
   raise exception 'CP7_CREDIT_SOURCE_JUST_LINKED_SCOPE_REQUIRED';end if;
 end if;
 -- Exact link->seal and seal->link; missing or extra sealed identities refuse.
 if exists(select 1 from cp7_credit.source_operation_plans_v1 sp join cp7_credit.recognition_components c on c.plan_id=sp.plan_id
  join cp7_credit.component_parts q on q.component_id=c.id join cp7_credit.component_journals o on o.part_id=q.id
  where sp.operation_id=w.operation_id and q.id is distinct from p_just_linked and not exists(
   select 1 from cp7_credit.source_operation_part_seals_v1 z where z.operation_id=w.operation_id and z.plan_id=sp.plan_id
    and z.component_id=c.id and z.part_id=q.id and z.journal_id=o.journal_id))
  or exists(select 1 from cp7_credit.source_operation_part_seals_v1 z where z.operation_id=w.operation_id and not exists(
   select 1 from cp7_credit.source_operation_plans_v1 sp join cp7_credit.recognition_components c on c.plan_id=sp.plan_id
    join cp7_credit.component_parts q on q.component_id=c.id join cp7_credit.component_journals o on o.part_id=q.id
    where sp.operation_id=w.operation_id and(sp.plan_id,c.id,q.id,o.journal_id)=(z.plan_id,z.component_id,z.part_id,z.journal_id)))then
  raise exception 'CP7_CREDIT_SOURCE_PART_SEAL_SET_CHANGED';end if;
 for r in select q.id part_id,to_jsonb(o) journal_link,z.actual_journal,z.actual_journal_sha256,z.source_binding_sha256,o.journal_id
  from cp7_credit.source_operation_plans_v1 sp join cp7_credit.recognition_components c on c.plan_id=sp.plan_id
  join cp7_credit.component_parts q on q.component_id=c.id left join cp7_credit.component_journals o on o.part_id=q.id
  left join cp7_credit.source_operation_part_seals_v1 z on z.part_id=q.id where sp.operation_id=w.operation_id loop
  -- A Native J without its immutable link is never excluded/ignored as pending.
  if r.journal_id is null then
   if exists(select 1 from erp.journal_entries j where j.source_type='CP7_CUSTOMER_CREDIT_RECOGNITION'and j.source_id=r.part_id)then
    raise exception 'CP7_CREDIT_SOURCE_ORPHAN_PART_JOURNAL';end if;
   continue;
  end if;
  perform cp7_credit.assert_source_adjustment_part_journal_v1(r.part_id);
  if r.part_id is not distinct from p_just_linked then continue;end if;
  if r.journal_link is distinct from(select z.journal_link from cp7_credit.source_operation_part_seals_v1 z where z.part_id=r.part_id)
   or r.actual_journal is distinct from cp7_credit.materialized_journal_payload(r.journal_id)
   or r.actual_journal_sha256 is distinct from cp7_credit.pg_jsonb_sha256(r.actual_journal)
   or r.source_binding_sha256 is distinct from cp7_credit.source_operation_binding_sha256_v1(w.operation_id)then
   raise exception 'CP7_CREDIT_SOURCE_PART_SEAL_CHANGED';end if;
 end loop;
end $$;

-- All retained actual I, including older ADJs, keeps its before-operation full
-- immutable journal/link seal. Never compare only initial_net_amount or a net.
create function cp7_credit.assert_source_retained_journals_v1(p_operation uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare w cp7_credit.source_operation_work_v1;r record;fact jsonb;
begin
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_operation;
 for r in select distinct substring(e->>'id'from 6)::uuid part_id from jsonb_array_elements(w.actual_ordinal_input->'families')f,
  lateral jsonb_array_elements(f->'retained_recognition')e loop
  perform cp7_credit.assert_source_adjustment_part_journal_v1(r.part_id);
  select cp7_credit.materialized_fact('PART_JOURNAL',o.part_id,jsonb_build_object('link',to_jsonb(o),
   'actual',cp7_credit.materialized_journal_payload(o.journal_id)))into strict fact
   from cp7_credit.component_journals o where o.part_id=r.part_id;
  if not exists(select 1 from jsonb_array_elements(w.before_financial_profile->'actual_objects')x where x=fact)then
   raise exception 'CP7_CREDIT_SOURCE_RETAINED_ACTUAL_JOURNAL_CHANGED';end if;
 end loop;
end $$;

create function cp7_credit.assert_source_adjustment_owner_v1(p_plan uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare op uuid;
begin
 perform cp7_credit.assert_source_adjustment_owner_base_v1(p_plan);
 select operation_id into strict op from cp7_credit.source_operation_plans_v1 where plan_id=p_plan;
 perform cp7_credit.assert_source_retained_journals_v1(op);
 perform cp7_credit.assert_source_operation_part_seals_v1(op);
 -- Authority/request are rechecked after all fresh reads, without new locks.
 perform cp7_credit.assert_source_operation_work_v1(op);
end $$;

create function cp7_credit.validate_source_adjustment_component_v1(p_component uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.recognition_components;p cp7_credit.recognition_plans;h cp7_credit.cohorts;
 s cp7_credit.source_operation_plans_v1;fresh jsonb;k jsonb;side text;events jsonb;components jsonb;parts jsonb;
begin
 select *into strict c from cp7_credit.recognition_components where id=p_component;
 select *into strict p from cp7_credit.recognition_plans where id=c.plan_id;
 select *into strict h from cp7_credit.cohorts where id=p.cohort_id;
 select *into strict s from cp7_credit.source_operation_plans_v1 where plan_id=p.id;
 perform cp7_credit.assert_source_adjustment_owner_v1(p.id);
 -- The owner reentry recomputes every family with ALL own new plans excluded
 -- together, checks every old actual journal and every partial own journal seal.
 fresh:=cp7_credit.source_adjustment_kernel_v1(s.full_family_result);
 if fresh is distinct from p.kernel_result or s.canonical_plan is distinct from fresh
  or fresh->>'contract_version'is distinct from'ow04.family-adjustment-plan.v1'
  or fresh->>'kernel_version'is distinct from p.kernel_version
  or fresh->>'before_source_sha256'is distinct from p.before_source_sha256
  or fresh->>'after_source_sha256'is distinct from p.after_source_sha256
  or fresh->'before_events'is distinct from p.before_events or fresh->'added_events'is distinct from p.added_events
  or(fresh->>'net_current_k')::numeric is distinct from p.net_amount
  or(fresh->>'has_recognition_effect')::boolean is distinct from p.has_recognition_effect
  or not p.has_recognition_effect or p.net_amount>=0 or p.expected_component_count<=0
  or jsonb_array_length(fresh->'components')is distinct from p.expected_component_count
  or cp7_credit.pg_jsonb_sha256(fresh->'components')is distinct from p.components_sha256_pg
  or cp7_credit.pg_jsonb_sha256(fresh->'support')is distinct from p.support_sha256_pg then
  raise exception 'CP7_CREDIT_SOURCE_ADJUSTMENT_PLAN_CHANGED';end if;
 foreach side in array array['BEFORE','ADDED']loop
  select coalesce(jsonb_agg(jsonb_build_object('id',z.event_id,'kind',z.kind,'amount',cp7_credit.cent_text(z.amount),
   'economic_date',z.economic_date::text,'transaction_date',z.transaction_date::text,'source_sha256',z.source_sha256)
   order by z.event_id collate"C"),'[]')into events from cp7_credit.plan_support_events z where z.plan_id=p.id and z.phase=side;
  if events is distinct from(case side when'BEFORE'then fresh->'before_events'else fresh->'added_events'end)then
   raise exception 'CP7_CREDIT_SOURCE_ADJUSTMENT_SUPPORT_INCOMPLETE';end if;
 end loop;
 if exists(select 1 from cp7_credit.plan_support_events z where z.plan_id=p.id and
   (z.event_id is distinct from'journal:'||z.journal_id::text
    or z.source_fact_snapshot is distinct from ow04_source_proposal.financial_journal_payload(z.journal_id,h.ar_account_id)
    or z.source_sha256 is distinct from ow04_source_proposal.sha(z.source_fact_snapshot)))then
  raise exception 'CP7_CREDIT_SOURCE_ADJUSTMENT_SUPPORT_FACT_CHANGED';end if;
 -- Compare canonical6 to canonical6. Full8 target_amount/retained_amount stays
 -- in s.full_family_result and is recomputed/proved separately by owner reentry.
 select coalesce(jsonb_agg(jsonb_build_object('amount',cp7_credit.cent_text(cc.amount),
  'economic_date',cc.economic_date::text,'transaction_date',cc.transaction_date::text,
  'previous_economic_date',cc.previous_economic_date::text,'previous_transaction_date',cc.previous_transaction_date::text,
  'corners',cc.corners)order by cc.ordinal),'[]')into components from cp7_credit.recognition_components cc where cc.plan_id=p.id;
 if components is distinct from fresh->'components'
  or(select count(*)from cp7_credit.recognition_components where plan_id=p.id)is distinct from p.expected_component_count::bigint
  or(select coalesce(max(ordinal),0)from cp7_credit.recognition_components where plan_id=p.id)is distinct from p.expected_component_count
  or exists(select 1 from cp7_credit.recognition_components cc where cc.plan_id=p.id and
   (cc.kernel_component is distinct from fresh->'components'->(cc.ordinal-1)
    or cc.component_sha256_pg is distinct from cp7_credit.pg_jsonb_sha256(cc.kernel_component)
    or cc.amount>=0))then raise exception 'CP7_CREDIT_SOURCE_ADJUSTMENT_COMPONENT_VECTOR_CHANGED';end if;
 k:=fresh->'components'->(c.ordinal-1);
 if k is distinct from c.kernel_component or cp7_credit.pg_jsonb_sha256(k)is distinct from c.component_sha256_pg
  or(k->>'amount')::numeric is distinct from c.amount or(k->>'economic_date')::date is distinct from c.economic_date
  or(k->>'transaction_date')::date is distinct from c.transaction_date
  or(k->>'previous_economic_date')::date is distinct from c.previous_economic_date
  or(k->>'previous_transaction_date')::date is distinct from c.previous_transaction_date
  or k->'corners'is distinct from c.corners
  or c.amount is distinct from((c.corners->>'d_here')::numeric-(c.corners->>'d_prev_economic')::numeric
   -(c.corners->>'d_prev_transaction')::numeric+(c.corners->>'d_prev_both')::numeric)then
  raise exception 'CP7_CREDIT_SOURCE_ADJUSTMENT_COMPONENT_CHANGED';end if;
 if exists(select 1 from cp7_credit.recognition_components cc left join cp7_credit.component_parts q on q.component_id=cc.id
   where cc.plan_id=p.id group by cc.id,cc.amount
   having count(q.id)::numeric<>ceil(abs(cc.amount)/cp7_credit.native_journal_cent_max())or sum(q.amount)is distinct from cc.amount)
  or exists(select 1 from cp7_credit.component_parts q join cp7_credit.recognition_components cc on cc.id=q.component_id where cc.plan_id=p.id
   and(q.ordinal>ceil(abs(cc.amount)/cp7_credit.native_journal_cent_max())or q.amount is distinct from
    sign(cc.amount)*least(cp7_credit.native_journal_cent_max(),abs(cc.amount)-(q.ordinal-1)*cp7_credit.native_journal_cent_max())))then
  raise exception 'CP7_CREDIT_SOURCE_ADJUSTMENT_PART_MANIFEST_CHANGED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',q.id,'component_id',cc.id,'ordinal',q.ordinal,'amount',cp7_credit.cent_text(q.amount))
  order by cc.ordinal,q.ordinal),'[]')into parts from cp7_credit.component_parts q join cp7_credit.recognition_components cc on cc.id=q.component_id
  where cc.plan_id=p.id;
 if jsonb_array_length(parts)::bigint is distinct from p.expected_part_count or cp7_credit.pg_jsonb_sha256(parts)is distinct from p.parts_sha256_pg then
  raise exception 'CP7_CREDIT_SOURCE_ADJUSTMENT_PART_MANIFEST_CHANGED';end if;
 perform cp7_credit.assert_source_adjustment_owner_v1(p.id);
end $$;

-- Activates one plan only after the entire operation's rows/manifests exist.
-- Completed older plans remain ordinary retained I and are never activatable.
create function cp7_credit.activate_source_adjustment_plan_v1(p_plan uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.source_operation_plans_v1;w cp7_credit.source_operation_work_v1;e cp7_credit.execution_context;
begin
 select *into strict s from cp7_credit.source_operation_plans_v1 where plan_id=p_plan;
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=s.operation_id
  and backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 perform cp7_credit.assert_source_operation_work_v1(w.operation_id);
 perform cp7_credit.source_adjustment_fresh_v1(w.operation_id);
 if exists(select 1 from cp7_credit.posting_scope where backend_pid=w.backend_pid and transaction_id=w.transaction_id)then
  raise exception 'CP7_CREDIT_SOURCE_POSTING_SCOPE_NOT_CLEAR';end if;
 select *into e from cp7_credit.execution_context where backend_pid=w.backend_pid and transaction_id=w.transaction_id;
 if found and(e.actor,e.request_id,e.owning_action,e.payload_sha256,e.review_sha256,e.authority_snapshot)is distinct from
  (w.actor,w.request_id,w.action,w.payload_sha256,cp7_credit.source_operation_binding_sha256_v1(w.operation_id),w.authority_snapshot)then
  raise exception 'CP7_CREDIT_SOURCE_EXECUTION_CONTEXT_NOT_OWNED';end if;
 insert into cp7_credit.execution_context(backend_pid,transaction_id,actor,request_id,plan_id,owning_action,payload_sha256,review_sha256,authority_snapshot)
 values(w.backend_pid,w.transaction_id,w.actor,w.request_id,p_plan,w.action,w.payload_sha256,
  cp7_credit.source_operation_binding_sha256_v1(w.operation_id),w.authority_snapshot)
 on conflict(backend_pid,transaction_id)do update set plan_id=excluded.plan_id;
 update cp7_credit.source_operation_work_v1 set active_plan_id=p_plan where operation_id=w.operation_id;
 perform cp7_credit.assert_source_adjustment_owner_v1(p_plan);
end $$;

-- Exact hook inside EXISTING post_component, immediately after its actual
-- component_journals INSERT, before posting_scope deletion and next owner call.
-- Invoke only for plan_kind='ADJUSTMENT'; INITIAL execution is unchanged.
create function cp7_credit.seal_source_operation_part_v1(p_part uuid)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare q cp7_credit.component_parts;c cp7_credit.recognition_components;s cp7_credit.source_operation_plans_v1;
 o cp7_credit.component_journals;actual jsonb;
begin
 select *into strict q from cp7_credit.component_parts where id=p_part;
 select *into strict c from cp7_credit.recognition_components where id=q.component_id;
 select *into strict s from cp7_credit.source_operation_plans_v1 where plan_id=c.plan_id;
 perform cp7_credit.assert_source_adjustment_owner_base_v1(c.plan_id);
 perform cp7_credit.assert_source_retained_journals_v1(s.operation_id);
 -- Allows this one just-created link, only under its still-live exact posting
 -- scope. Every other part is checked against its existing immutable seal.
 perform cp7_credit.assert_source_operation_part_seals_v1(s.operation_id,q.id);
 select *into strict o from cp7_credit.component_journals where part_id=q.id;
 actual:=cp7_credit.materialized_journal_payload(o.journal_id);
 insert into cp7_credit.source_operation_part_seals_v1(part_id,operation_id,plan_id,component_id,journal_id,journal_link,
  actual_journal,actual_journal_sha256,source_binding_sha256)
 values(q.id,s.operation_id,c.plan_id,c.id,o.journal_id,to_jsonb(o),actual,cp7_credit.pg_jsonb_sha256(actual),
  cp7_credit.source_operation_binding_sha256_v1(s.operation_id));
 perform cp7_credit.assert_source_adjustment_owner_v1(c.plan_id);
end $$;

-- Private convenience entrypoint; actual Native posting remains the existing
-- ledger02 post_component and its exact two-account negative part_lines path.
create function cp7_credit.post_source_adjustment_component_v1(p_component uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare plan uuid;answer jsonb;
begin
 select plan_id into strict plan from cp7_credit.recognition_components where id=p_component;
 perform cp7_credit.activate_source_adjustment_plan_v1(plan);
 perform cp7_credit.validate_source_adjustment_component_v1(p_component);
 answer:=cp7_credit.post_component(p_component);
 perform cp7_credit.assert_source_adjustment_owner_v1(plan);
 return answer;
end $$;

do $private_source_adjustments$declare sig text;begin
 foreach sig in array array['assert_source_operation_plan_set_v1(uuid)','source_adjustment_fresh_v1(uuid)','assert_source_adjustment_owner_base_v1(uuid)','assert_source_adjustment_part_journal_v1(uuid)','assert_source_operation_part_seals_v1(uuid,uuid)','assert_source_retained_journals_v1(uuid)','assert_source_adjustment_owner_v1(uuid)','validate_source_adjustment_component_v1(uuid)','activate_source_adjustment_plan_v1(uuid)','seal_source_operation_part_v1(uuid)','post_source_adjustment_component_v1(uuid)']loop
  execute 'alter function cp7_credit.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write';
 end loop;
end $private_source_adjustments$;
