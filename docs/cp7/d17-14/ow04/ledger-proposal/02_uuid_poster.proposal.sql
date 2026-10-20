-- OW04 INTERNAL PROPOSAL ONLY. 01_immutable_facts.proposal.sql is NOT installed.
-- Deliberately unresolved, fail-closed integration interfaces are documented in
-- README.md. Do not replace them with context-exists/GUC/true placeholders.
do $not_an_installer$ begin
 raise exception 'OW04_PROPOSAL_NOT_INSTALLABLE_WITHOUT_COMPLETE_FEATURE';
end $not_an_installer$;

-- Required interfaces, implemented by the complete owning feature:
-- assert_owner_context(plan_id uuid) -> void
-- rebuild_locked_plan(plan_id uuid) -> jsonb (fresh actual Native inputs + kernel)
-- assert_source_admission(plan_id uuid) -> void (causal return scope, not arbitrary
-- funding-driven minting; old I reconciles F_before; historical overfunding denied)
-- check_credit_account(cohort_id uuid) -> void (vetted account + Native/BB lineage)
-- assert_return_owner_context(return_id uuid) -> void (before plan exists)
-- return_causal_book_floor(return_id uuid) -> date (locked real correction
-- lineage: immutable root SALE/return-family floors and actual source contract;
-- never just the active leaf or a max of unrelated funding/reversal journals)
-- _post_journal_bound(text,uuid,date,text,jsonb) -> uuid (exact private Native copy)
-- Their absence is an integration error, NEVER permission to post.
-- This prototype's concrete component validator admits INITIAL only. A future
-- ADJUSTMENT requires the authoritative per-family target-minus-retained-I
-- binding protocol described in README.md; raw invoice delta is NOT sufficient.

-- Hash the exact same cent-line representation Native post_journal stores.
-- This is needed for a scope checked both before and after its canonicalizer:
-- jsonb equality considers 0 and 0.00 equal, while jsonb::text hashes differ.
create function cp7_credit.native_cent_lines(p_lines jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
declare r jsonb;d numeric;c numeric;out_lines jsonb:='[]';
begin
 if jsonb_typeof(p_lines)is distinct from'array'or jsonb_array_length(p_lines)<2 then
  raise exception 'CP7_CREDIT_NATIVE_LINES_ARRAY_REQUIRED';end if;
 for r in select *from jsonb_array_elements(p_lines)loop
  if jsonb_typeof(r)is distinct from'object'then raise exception 'CP7_CREDIT_NATIVE_LINE_OBJECT_REQUIRED';end if;
  d:=coalesce((r->>'debit')::numeric,0);c:=coalesce((r->>'credit')::numeric,0);
  if d::text in('NaN','Infinity','-Infinity')or c::text in('NaN','Infinity','-Infinity')or d<0 or c<0 then
   raise exception 'CP7_CREDIT_NATIVE_FINITE_NONNEGATIVE_MONEY_REQUIRED';end if;
  out_lines:=out_lines||jsonb_build_array(r||jsonb_build_object('debit',round(d,2),'credit',round(c,2)));
 end loop;
 return out_lines;
end $$;
create function cp7_credit.native_lines_sha256(p_lines jsonb)returns text
language sql immutable security invoker set search_path=''as $$
 select cp7_credit.pg_jsonb_sha256(cp7_credit.native_cent_lines(p_lines))
$$;

-- Private per-part helper; the posting entry point below accepts COMPONENT UUID
-- only. A part is a deterministic storage slice, never a new financial fact.
create function cp7_credit.part_lines(p_part uuid) returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare q cp7_credit.component_parts;c cp7_credit.recognition_components;h cp7_credit.cohorts;ar uuid;
begin
 select *into strict q from cp7_credit.component_parts where id=p_part;
 select *into strict c from cp7_credit.recognition_components where id=q.component_id;
 select h0.*into strict h from cp7_credit.cohorts h0 join cp7_credit.recognition_plans p on p.cohort_id=h0.id where p.id=c.plan_id;
 -- Actual AR account of this return journal, under mapping/account locks.
 -- The source collector must reject unexplained account changes, not invent a
-- reclassification from some unrelated account or choose a new default.
 select distinct jl.account_id into strict ar from erp.journal_lines jl
  where jl.journal_entry_id=h.source_return_journal_id
   and jl.account_id=h.ar_account_id and jl.customer_id=h.customer_id and jl.credit>0;
 if ar=h.credit_account_id then raise exception 'CP7_CREDIT_ACCOUNT_COLLISION';end if;
 return cp7_credit.native_cent_lines(jsonb_build_array(
  jsonb_build_object('account_id',ar,'customer_id',h.customer_id,
   'description','OW04 source-bound recognition',
   'debit',case when q.amount>0 then q.amount else 0 end,
   'credit',case when q.amount<0 then -q.amount else 0 end),
  jsonb_build_object('account_id',h.credit_account_id,'customer_id',h.customer_id,
   'description','OW04 source-bound recognition',
   'debit',case when q.amount<0 then -q.amount else 0 end,
   'credit',case when q.amount>0 then q.amount else 0 end)));
end $$;

create function cp7_credit.validate_component(p_component uuid) returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.recognition_components;p cp7_credit.recognition_plans;h cp7_credit.cohorts;
 fresh jsonb;k jsonb;side text;events jsonb;parts jsonb;all_components jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 select *into strict c from cp7_credit.recognition_components where id=p_component;
 select *into strict p from cp7_credit.recognition_plans where id=c.plan_id;
 select *into strict h from cp7_credit.cohorts where id=p.cohort_id;
 if p.plan_kind<>'INITIAL'then raise exception 'CP7_CREDIT_BOUND_ADJUSTMENT_PROTOCOL_REQUIRED';end if;
 perform cp7_credit.assert_owner_context(p.id);
 -- Rebuilder must acquire/verify full source locks, read fresh after waits,
-- follow the actual correction family, and call the SAME pure kernel.
 fresh:=cp7_credit.rebuild_locked_plan(p.id);
 -- Hard source admission consumes the same already locked, fresh source set.
-- Re-entry after Native's period SHARE must never discover/acquire a new
-- earlier-order source/master lock; compare the locked manifest or abort.
 perform cp7_credit.assert_source_admission(p.id);
 if fresh is distinct from p.kernel_result
  or fresh->>'contract_version'is distinct from'ow04.pure-recognition-plan.v1'
  or fresh->>'kernel_version'is distinct from p.kernel_version
  or fresh->>'before_source_sha256'is distinct from p.before_source_sha256
  or fresh->>'after_source_sha256'is distinct from p.after_source_sha256
  or fresh->'before_events'is distinct from p.before_events
  or fresh->'added_events'is distinct from p.added_events
  or(fresh->>'net_current_k')::numeric is distinct from p.net_amount
  or(fresh->>'has_recognition_effect')::boolean is distinct from p.has_recognition_effect
  or jsonb_array_length(fresh->'components')is distinct from p.expected_component_count
  or cp7_credit.pg_jsonb_sha256(fresh->'components')is distinct from p.components_sha256_pg
  or cp7_credit.pg_jsonb_sha256(fresh->'support')is distinct from p.support_sha256_pg then
  raise exception 'CP7_CREDIT_PLAN_SOURCE_CHANGED';
 end if;
 -- Persisted support sidecars must cover exactly BOTH normalized input arrays.
 foreach side in array array['BEFORE','ADDED']loop
  select coalesce(jsonb_agg(jsonb_build_object('id',s.event_id,'kind',s.kind,'amount',cp7_credit.cent_text(s.amount),
   'economic_date',s.economic_date::text,'transaction_date',s.transaction_date::text,'source_sha256',s.source_sha256)
   order by s.event_id collate "C"),'[]')into events
   from cp7_credit.plan_support_events s where s.plan_id=p.id and s.phase=side;
  if events is distinct from(case side when'BEFORE'then fresh->'before_events'else fresh->'added_events'end)then
   raise exception 'CP7_CREDIT_SUPPORT_VECTOR_INCOMPLETE';end if;
 end loop;
 -- Compare ALL persisted component columns, ordinals and metadata, not only
-- the selected component or the plan's claimed expected count/hash.
 select coalesce(jsonb_agg(jsonb_build_object('amount',cp7_credit.cent_text(cc.amount),
  'economic_date',cc.economic_date::text,'transaction_date',cc.transaction_date::text,
  'previous_economic_date',cc.previous_economic_date::text,
  'previous_transaction_date',cc.previous_transaction_date::text,'corners',cc.corners)
  order by cc.ordinal),'[]')into all_components from cp7_credit.recognition_components cc where cc.plan_id=p.id;
 if all_components is distinct from fresh->'components'
  or(select coalesce(max(ordinal),0)from cp7_credit.recognition_components where plan_id=p.id)is distinct from p.expected_component_count
  or exists(select 1 from cp7_credit.recognition_components cc where cc.plan_id=p.id and
   (cc.kernel_component is distinct from fresh->'components'->(cc.ordinal-1)
    or cc.component_sha256_pg is distinct from cp7_credit.pg_jsonb_sha256(cc.kernel_component)))then
  raise exception 'CP7_CREDIT_COMPONENT_VECTOR_INCOMPLETE';end if;
 k:=fresh->'components'->(c.ordinal-1);
 if k is distinct from c.kernel_component
  or cp7_credit.pg_jsonb_sha256(k)is distinct from c.component_sha256_pg
  or(k->>'amount')::numeric is distinct from c.amount
  or(k->>'economic_date')::date is distinct from c.economic_date
  or(k->>'transaction_date')::date is distinct from c.transaction_date
  or(k->>'previous_economic_date')::date is distinct from c.previous_economic_date
  or(k->>'previous_transaction_date')::date is distinct from c.previous_transaction_date
  or k->'corners'is distinct from c.corners
  or c.amount is distinct from((c.corners->>'d_here')::numeric-(c.corners->>'d_prev_economic')::numeric
   -(c.corners->>'d_prev_transaction')::numeric+(c.corners->>'d_prev_both')::numeric)then
  raise exception 'CP7_CREDIT_COMPONENT_CHANGED';
 end if;
 if p.plan_kind='INITIAL'and(p.id is distinct from h.initial_plan_id or p.net_amount is distinct from h.initial_net_amount
  or p.expected_component_count=0)then raise exception 'CP7_CREDIT_INITIAL_COHORT_CHANGED';end if;
 -- Manifest UUIDs are part of the owning request/review, not pure arithmetic.
 -- Largest Native-supported amount first, followed by the exact remainder.
 if exists(select 1 from cp7_credit.recognition_components cc left join cp7_credit.component_parts qq on qq.component_id=cc.id
   where cc.plan_id=p.id group by cc.id,cc.amount
   having count(qq.id)::numeric<>ceil(abs(cc.amount)/cp7_credit.native_journal_cent_max())
    or sum(qq.amount)is distinct from cc.amount)
  or exists(select 1 from cp7_credit.component_parts qq join cp7_credit.recognition_components cc on cc.id=qq.component_id
   where cc.plan_id=p.id and(qq.ordinal>ceil(abs(cc.amount)/cp7_credit.native_journal_cent_max())
    or qq.amount is distinct from sign(cc.amount)*least(cp7_credit.native_journal_cent_max(),
     abs(cc.amount)-(qq.ordinal-1)*cp7_credit.native_journal_cent_max())))then
  raise exception 'CP7_CREDIT_PART_MANIFEST_CHANGED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',qq.id,'component_id',cc.id,'ordinal',qq.ordinal,
  'amount',cp7_credit.cent_text(qq.amount))order by cc.ordinal,qq.ordinal),'[]')into parts
  from cp7_credit.component_parts qq join cp7_credit.recognition_components cc on cc.id=qq.component_id where cc.plan_id=p.id;
 if jsonb_array_length(parts)::bigint is distinct from p.expected_part_count
  or cp7_credit.pg_jsonb_sha256(parts)is distinct from p.parts_sha256_pg then
  raise exception 'CP7_CREDIT_PART_MANIFEST_CHANGED';end if;
 perform cp7_credit.check_credit_account(h.id);
 perform cp7_credit.assert_owner_context(p.id); -- current authority after waits
end $$;

-- Called by the derived Native copy BEFORE its own require_internal(), and
-- again at its book-date assignment AFTER Native's period SHARE lock.
create function cp7_credit.assert_bound_post(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare x cp7_credit.posting_scope;c cp7_credit.recognition_components;q cp7_credit.component_parts;h cp7_credit.cohorts;
begin
 select *into strict x from cp7_credit.posting_scope where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'
  or(x.source_type,x.source_id,x.economic_date,x.lines_sha256_pg)is distinct from
   (p_type,p_source,p_economic,cp7_credit.native_lines_sha256(p_lines))then
  raise exception using errcode='42501',message='CP7_CREDIT_PAIRED_POST_SCOPE_REQUIRED';end if;
 if x.post_kind='COMPONENT'then
  perform cp7_credit.validate_component(x.component_id);
  select *into strict c from cp7_credit.recognition_components where id=x.component_id;
  select *into strict q from cp7_credit.component_parts where id=x.part_id and component_id=c.id;
  select h0.*into strict h from cp7_credit.cohorts h0 join cp7_credit.recognition_plans p on p.cohort_id=h0.id where p.id=c.plan_id;
  if p_type<>'CP7_CUSTOMER_CREDIT_RECOGNITION'or p_source<>q.id
   or(x.plan_id,x.source_sale_id,x.source_return_id,x.economic_date,x.transaction_date)is distinct from
    (c.plan_id,h.source_sale_id,h.source_return_id,c.economic_date,c.transaction_date)
   or cp7_credit.native_cent_lines(p_lines)is distinct from cp7_credit.part_lines(q.id)then raise exception 'CP7_CREDIT_COMPONENT_POST_SCOPE_CHANGED';end if;
 else
  perform cp7_credit.assert_return_owner_context(x.source_return_id);
  if p_type<>'SALES_RETURN'or p_source<>x.source_return_id then raise exception 'CP7_CREDIT_RETURN_POST_SCOPE_CHANGED';end if;
 end if;
end $$;

create function cp7_credit.bound_book_date(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns date
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare x cp7_credit.posting_scope;sale_j erp.journal_entries;returned erp.sales_returns;lawful date;causal date;
begin
 -- Native copy has already obtained accounting_period_control FOR SHARE.
 perform cp7_credit.assert_bound_post(p_type,p_source,p_economic,p_lines);
 select *into strict x from cp7_credit.posting_scope where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 lawful:=erp.resolve_accounting_transaction_date(p_economic);
 if lawful is null or x.transaction_date<lawful or x.transaction_date<p_economic
  or x.transaction_date>(statement_timestamp()at time zone'Asia/Jakarta')::date then
  raise exception 'CP7_CREDIT_PAIR_REPLAN_REQUIRED';end if;
 if x.post_kind='RETURN'then
  select *into strict returned from erp.sales_returns where id=x.source_return_id;
  select *into strict sale_j from erp.journal_entries where source_type='SALE'
   and source_id=x.source_sale_id and reversal_of_id is null and status='POSTED';
  causal:=cp7_credit.return_causal_book_floor(returned.id);
  if causal is null or causal<sale_j.transaction_date then raise exception 'CP7_CREDIT_RETURN_LINEAGE_FLOOR_INVALID';end if;
  if returned.sale_id<>x.source_sale_id
   or p_economic<>(returned.physical_at at time zone'Asia/Jakarta')::date
   or x.transaction_date<sale_j.transaction_date
   or x.transaction_date is distinct from greatest(lawful,causal)then
   raise exception 'CP7_CREDIT_RETURN_SALE_BOOK_FLOOR_CHANGED';end if;
 end if;
 -- For COMPONENT, exact recomputed kernel pair is preserved. A max over every
-- support funding's book day would wrongly move B's early 100 from19 to20.
 return x.transaction_date;
end $$;

create function cp7_credit.bound_audit_context()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare x cp7_credit.posting_scope;p cp7_credit.recognition_plans;
begin
 select *into strict x from cp7_credit.posting_scope where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 if x.post_kind='COMPONENT'then select *into strict p from cp7_credit.recognition_plans where id=x.plan_id;end if;
 return jsonb_build_object('book_date_basis','SOURCE_BOUND_NATIVE_PROFILE','posting_kind',x.post_kind,
  'source_sale_id',x.source_sale_id,'source_return_id',x.source_return_id,'plan_id',x.plan_id,
  'component_id',x.component_id,'part_id',x.part_id,'lines_sha256_pg',x.lines_sha256_pg,
  'lawful_book_date',erp.resolve_accounting_transaction_date(x.economic_date),
  'before_source_sha256',p.before_source_sha256,'after_source_sha256',p.after_source_sha256);
end $$;

-- The actual posting entry point accepts only an immutable server component UUID.
create function cp7_credit.post_component(p_component uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare c cp7_credit.recognition_components;p cp7_credit.recognition_plans;h cp7_credit.cohorts;
 j uuid;lines jsonb;actual erp.journal_entries;ctx cp7_credit.execution_context;
 q cp7_credit.component_parts;receipt jsonb:='[]';
begin
 select *into strict c from cp7_credit.recognition_components where id=p_component;
 select *into strict p from cp7_credit.recognition_plans where id=c.plan_id;
 select *into strict h from cp7_credit.cohorts where id=p.cohort_id;
 perform cp7_credit.assert_owner_context(p.id);
 -- The owning request envelope returns cached committed receipts before this
-- writer. Never repost a component UUID, even after its journal was reversed.
 if exists(select 1 from cp7_credit.component_journals jj join cp7_credit.component_parts qq on qq.id=jj.part_id where qq.component_id=c.id)then
  raise exception 'CP7_CREDIT_COMPONENT_ALREADY_HAS_HISTORY';end if;
 perform cp7_credit.validate_component(c.id);
 select *into strict ctx from cp7_credit.execution_context where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and plan_id=p.id;
 for q in select *from cp7_credit.component_parts where component_id=c.id order by ordinal loop
  lines:=cp7_credit.part_lines(q.id);
  insert into cp7_credit.posting_scope values(pg_backend_pid(),txid_current(),auth.uid(),ctx.request_id,'COMPONENT',
   c.id,q.id,p.id,h.source_sale_id,h.source_return_id,'CP7_CUSTOMER_CREDIT_RECOGNITION',q.id,
   c.economic_date,c.transaction_date,cp7_credit.native_lines_sha256(lines));
  j:=cp7_credit._post_journal_bound('CP7_CUSTOMER_CREDIT_RECOGNITION',q.id,c.economic_date,
   'Kredit retur: pengakuan terikat sumber',lines);
  select *into strict actual from erp.journal_entries where id=j;
  if(actual.source_type,actual.source_id,actual.economic_date,actual.transaction_date,actual.status)is distinct from
   ('CP7_CUSTOMER_CREDIT_RECOGNITION',q.id,c.economic_date,c.transaction_date,'POSTED')then
   raise exception 'CP7_CREDIT_POSTED_PAIR_CHANGED';end if;
  insert into cp7_credit.component_journals values(q.id,j,c.economic_date,c.transaction_date,
   cp7_credit.native_lines_sha256(lines),statement_timestamp());
  receipt:=receipt||jsonb_build_array(jsonb_build_object('part_id',q.id,'journal_id',j));
  delete from cp7_credit.posting_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 end loop;
 perform cp7_credit.assert_owner_context(p.id);
 return jsonb_build_object('component_id',c.id,'parts',receipt);
end $$;

-- Exact hook for Native post_sales_return's ONE journal call. The accepted body
-- still owns all quantity/allocation/stock/HPP line construction and guards.
create function cp7_credit.post_return_journal(p_type text,p_return uuid,p_economic date,p_description text,p_lines jsonb)returns uuid
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare r erp.sales_returns;sj erp.journal_entries;book date;causal date;lawful date;request uuid;j uuid;
begin
 if not exists(select 1 from cp7_credit.execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  -- Complete integration admits EVERY Native return, including ordinary empty
-- target. An ordinary context requires no account/mode/financial plan, but may
-- not skip family registration or the SALE book floor via the legacy poster.
  raise exception 'CP7_CREDIT_RETURN_OWNER_CONTEXT_REQUIRED';
 end if;
 perform cp7_credit.assert_return_owner_context(p_return);
 if p_type<>'SALES_RETURN'then raise exception 'CP7_CREDIT_RETURN_SOURCE_REQUIRED';end if;
 select *into strict r from erp.sales_returns where id=p_return;
 select *into strict sj from erp.journal_entries where source_type='SALE'and source_id=r.sale_id
  and reversal_of_id is null and status='POSTED';
 if p_economic<>(r.physical_at at time zone'Asia/Jakarta')::date then raise exception 'CP7_CREDIT_RETURN_ECONOMIC_DATE_CHANGED';end if;
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 lawful:=erp.resolve_accounting_transaction_date(p_economic);
 causal:=cp7_credit.return_causal_book_floor(r.id);
 if lawful is null or causal is null or causal<sj.transaction_date then raise exception 'CP7_CREDIT_RETURN_LINEAGE_FLOOR_INVALID';end if;
 book:=greatest(lawful,causal);
 select request_id into strict request from cp7_credit.execution_context where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 insert into cp7_credit.posting_scope values(pg_backend_pid(),txid_current(),auth.uid(),request,'RETURN',
  null,null,null,r.sale_id,r.id,p_type,r.id,p_economic,book,cp7_credit.native_lines_sha256(p_lines));
 j:=cp7_credit._post_journal_bound(p_type,r.id,p_economic,p_description,p_lines);
 delete from cp7_credit.posting_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 perform cp7_credit.assert_return_owner_context(p_return);
 return j;
end $$;

-- Generic reversal protects registered facts and every standard Native reversal
-- descendant, including reversal-of-reversal. UNION (not UNION ALL) terminates
-- even malformed cyclic lineage; both Native ancestor pointers are traversed.
create function cp7_credit.is_protected_journal(p_journal uuid)returns boolean
language sql volatile security definer set search_path=''as $$
 with recursive ancestry(id)as(
  select p_journal
  union
  select parent.id from ancestry a join erp.journal_entries child on child.id=a.id
   join erp.journal_entries parent on(parent.id=child.reversal_of_id
    or(child.source_type='JOURNAL_REVERSAL'and parent.id=child.source_id))
 )
 select exists(select 1 from ancestry a join erp.journal_entries j on j.id=a.id where
  j.source_type in('CP7_CUSTOMER_CREDIT_RECOGNITION','CP7_CUSTOMER_CREDIT_APPLY',
   'CP7_CUSTOMER_CREDIT_REFUND','CP7_CUSTOMER_CREDIT_EVENT_REVERSE')
  or exists(select 1 from cp7_credit.component_journals x where x.journal_id=j.id)
  or exists(select 1 from cp7_credit.consumption_events x where x.journal_id=j.id))
$$;

-- Owner/ACL assertions belong to exact installer verification. No EXECUTE is
-- granted to browser, service, capture, sales read/write, or unrelated modules.
revoke all on all functions in schema cp7_credit from public,anon,authenticated,service_role,
 cp7_capture,cp7_sales_read,cp7_sales_write;
