-- OUTSIDE PRODUCT. Compose with the exact source/ledger/admission/readers and
-- Native source-capture transforms in one reviewed installation transaction.
-- This barrier is retained; the isolated check explicitly removes ONLY it.
do $not_an_installer$begin
 raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';
end $not_an_installer$;

-- Mutable work is private, PID/tx/actor/request bound, and MUST disappear at
-- command completion. It is never a financial-materialization witness.
create table cp7_credit.initial_return_work(
 operation_id uuid primary key,backend_pid integer not null,transaction_id bigint not null,
 actor uuid not null,request_id uuid not null,source_sale_id uuid not null,
 origin text not null check(origin in('ORDINARY','REVIEWED_SETTLEMENT')),
 phase text not null check(phase in('SEALED','ENTERED','MATERIALIZED','COMPLETE')),
 expected_version text not null,legacy_payload jsonb not null,settlement jsonb,
 payload_sha256 text not null,quote_sha256 text,authority_snapshot jsonb not null,
 source_snapshot jsonb not null,source_lock_sha256 text not null,
 projection jsonb not null,projection_sha256 text not null,projected_kernel jsonb not null,
 prior_causal jsonb not null,prior_causal_manifest jsonb not null,
 period_snapshot jsonb not null,credit_account_snapshot jsonb,cash_account_snapshot jsonb,
 return_id uuid unique,family_id uuid unique,family_ordinal bigint,
 actual_fact jsonb,actual_event jsonb,actual_kernel jsonb,projection_actual_proof jsonb,
 actual_manifest_sha256 text,cohort_id uuid unique,plan_id uuid unique,
 materialization_id uuid unique,refund_operation_id uuid unique,
 unique(backend_pid,transaction_id),unique(actor,request_id),
 check((phase='SEALED')=(return_id is null)),
 check(phase not in('MATERIALIZED','COMPLETE')or(actual_fact is not null and family_id is not null
  and family_ordinal>0 and actual_kernel is not null and projection_actual_proof is not null))
);

-- Immutable data-completion/provenance is available before Native's final
-- invoice status update. It is NOT a live actor capability or final receipt.
create table cp7_credit.initial_return_materializations(
 operation_id uuid primary key,actor uuid not null,request_id uuid not null,
 source_sale_id uuid not null,source_return_id uuid not null unique,family_id uuid not null unique,
 family_ordinal bigint not null check(family_ordinal>0),cohort_id uuid unique,plan_id uuid unique,
 origin text not null check(origin in('ORDINARY','REVIEWED_SETTLEMENT')),
 expected_version text not null,legacy_payload jsonb not null,settlement jsonb,
 payload_sha256 text not null,quote_sha256 text,authority_snapshot jsonb not null,
 source_snapshot jsonb not null,source_lock_sha256 text not null,
 projection jsonb not null,projection_sha256 text not null,
 prior_causal jsonb not null,prior_causal_manifest jsonb not null,
 period_snapshot jsonb not null,actual_fact jsonb not null,actual_event jsonb not null,
 actual_kernel jsonb not null,projection_actual_proof jsonb not null,
 projection_actual_proof_sha256 text not null,recognition_manifest_sha256 text not null,
 materialization_id uuid not null unique,refund_operation_id uuid unique,
 recorded_at timestamptz not null default statement_timestamp(),unique(actor,request_id),
 check((cohort_id is null)=(plan_id is null)),
 check((actual_kernel->>'has_recognition_effect')::boolean=(cohort_id is not null))
);
create table cp7_credit.initial_return_completions(
 operation_id uuid primary key references cp7_credit.initial_return_materializations(operation_id),
 actor uuid not null,request_id uuid not null,source_sale_id uuid not null,source_return_id uuid not null unique,
 origin text not null,inner_receipt jsonb not null,outer_receipt jsonb,
 final_manifest jsonb not null,final_manifest_sha256 text not null,
 recorded_at timestamptz not null default statement_timestamp(),unique(actor,request_id)
);

create table cp7_credit.source_mutation_scope(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 action text not null,source_id uuid not null,sale_id uuid not null,
 authority_snapshot jsonb not null,had_families boolean not null,
 primary key(backend_pid,transaction_id)
);

do $protect$declare t text;begin
 foreach t in array array['initial_return_work','initial_return_materializations','initial_return_completions','source_mutation_scope']loop
  execute format('alter table cp7_credit.%I owner to postgres',t);
  execute format('alter table cp7_credit.%I enable row level security',t);
  execute format('create policy deny_direct on cp7_credit.%I for all to public using(false)with check(false)',t);
  execute format('revoke all on cp7_credit.%I from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write',t);
 end loop;
 foreach t in array array['initial_return_materializations','initial_return_completions']loop
  execute format('create trigger immutable_row before update or delete on cp7_credit.%I for each row execute function cp7_credit.immutable_fact()',t);
  execute format('create trigger immutable_truncate before truncate on cp7_credit.%I for each statement execute function cp7_credit.immutable_fact()',t);
 end loop;
end $protect$;

-- Fixed factual reader. No permission, context, locking or current-E call.
-- Complete preexisting source authority is established by locked_source_family
-- before period; subsequent uses compare these actual immutable facts.
create function cp7_credit.initial_base_events_v1(p_sale uuid,p_exclude_return uuid default null)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare ar uuid;answer jsonb;
begin
 if exists(select 1 from cp7_note.revisions where p_sale in(root_sale_id,previous_sale_id,replacement_sale_id))then
  raise exception 'CP7_CREDIT_NOTE_FAMILY_INITIAL_ADAPTER_UNIMPLEMENTED';end if;
 select account_id into strict ar from erp.accounting_account_mappings where mapping_key='AR_CUSTOMER';
 with recursive originals as(
  select j.id,j.id origin,'NET'::text kind from erp.journal_entries j
   where j.source_type='SALE'and j.source_id=p_sale and j.reversal_of_id is null
  union all select j.id,j.id,'NET'from erp.journal_entries j join erp.sales_returns r on r.id=j.source_id
   where j.source_type='SALES_RETURN'and r.sale_id=p_sale and r.id is distinct from p_exclude_return and j.reversal_of_id is null
  union all select j.id,j.id,'FUNDING'from erp.journal_entries j join erp.sales_payments p on p.id=j.source_id
   where j.source_type='SALES_PAYMENT'and p.sale_id=p_sale and j.reversal_of_id is null
 ),walk(id,origin,kind)as(
  select *from originals union select child.id,w.origin,w.kind from walk w join erp.journal_entries child
   on(child.reversal_of_id=w.id or(child.source_type='JOURNAL_REVERSAL'and child.source_id=w.id))
 ),events as(
  select jsonb_build_object('id','journal:'||j.id::text,'kind',w.kind,
   'amount',cp7_credit.cent_text((case when w.kind='FUNDING'then -1 else 1 end)*coalesce(
     (select sum(l.debit-l.credit)from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=ar),0)),
   'economic_date',j.economic_date::text,'transaction_date',j.transaction_date::text,
   'source_sha256',ow04_source_proposal.sha(ow04_source_proposal.financial_journal_payload(j.id,ar)))v
  from walk w join erp.journal_entries j on j.id=w.id where j.status in('POSTED','REVERSED')
 )select coalesce(jsonb_agg(v order by v->>'id'collate"C"),'[]')into answer from events;
 return answer;
end $$;

create function cp7_credit.initial_preserved_source_v1(p_sale uuid,p_exclude_return uuid default null)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object(
  'sale',(select to_jsonb(h)-'status'-'row_version'-'updated_at'from erp.sales_headers h where h.id=p_sale),
  'items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_items i where i.sale_id=p_sale),
  'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a
   join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=p_sale),
  'payments',(select coalesce(jsonb_agg(to_jsonb(p)order by p.id),'[]')from erp.sales_payments p where p.sale_id=p_sale),
  'advance_links',(select coalesce(jsonb_agg(to_jsonb(a)order by a.payment_id),'[]')from erp.initial_import_prepayment_payments a
   join erp.sales_payments p on p.id=a.payment_id where p.sale_id=p_sale),
  'payment_posting_facts',(select coalesce(jsonb_agg(to_jsonb(f)order by f.payment_id),'[]')from erp.sales_payment_posting_facts f where f.sale_id=p_sale),
  'payment_reversal_facts',(select coalesce(jsonb_agg(to_jsonb(f)order by f.payment_id),'[]')from erp.sales_payment_reversal_facts f
   join erp.sales_payments p on p.id=f.payment_id where p.sale_id=p_sale),
  'prior_returns',(select coalesce(jsonb_agg(to_jsonb(r)order by r.id),'[]')from erp.sales_returns r where r.sale_id=p_sale and r.id is distinct from p_exclude_return),
  'prior_return_items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id
   where r.sale_id=p_sale and r.id is distinct from p_exclude_return),
  'events',cp7_credit.initial_base_events_v1(p_sale,p_exclude_return),
  'base_journals',(select coalesce(jsonb_agg(cp7_credit.materialized_journal_payload((x->>'id')::uuid)order by x->>'id'),'[]')
   from(select jsonb_build_object('id',substring(e->>'id'from 9))x from jsonb_array_elements(cp7_credit.initial_base_events_v1(p_sale,p_exclude_return))e)z),
  'customer',(select to_jsonb(c)from erp.customers c join erp.sales_headers h on h.customer_id=c.id where h.id=p_sale),
  'ar_mapping',(select to_jsonb(m)from erp.accounting_account_mappings m where m.mapping_key='AR_CUSTOMER'))
$$;

-- A zero current excess is insufficient: the complete two-dimensional base
-- excess must be identically zero. The kernel's all-breakpoint components give
-- a finite exact proof. Returns cannot authorize pre-return overfunding.
create function cp7_credit.assert_zero_excess_v1(p_events jsonb)returns void
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare k jsonb;
begin
 k:=ow04_pure_kernel.recognition_plan_v1('[]',p_events);
 if(k->>'has_recognition_effect')::boolean then raise exception 'CP7_CREDIT_HISTORICAL_BASE_OVERFUNDING';end if;
end $$;

create function cp7_credit.initial_event_semantics_v1(p_events jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(x-'id'-'source_sha256'order by x->>'economic_date',x->>'transaction_date',x->>'kind',x->>'amount'),'[]')
 from jsonb_array_elements(p_events)x
$$;

-- Exact existing cp7_sales.review_token JSON codec, omitting ONLY the own
-- inserted DRAFT and its children. Its caller separately proves current Native
-- RETURN context, actor and exact pending request; the public quote never gets
-- an exclusion parameter. Child insertion necessarily retires the raw token.
create function cp7_credit.review_before_own_draft_v1(p_sale uuid,p_return uuid)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select md5(jsonb_build_object('header',to_jsonb(h),
  'items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_items i where i.sale_id=h.id),
  'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=h.id),
  'payments',(select coalesce(jsonb_agg(to_jsonb(p)order by p.id),'[]')from erp.sales_payments p where p.sale_id=h.id),
  'returns',(select coalesce(jsonb_agg(to_jsonb(r)order by r.id),'[]')from erp.sales_returns r where r.sale_id=h.id and r.id<>p_return),
  'return_items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=h.id and r.id<>p_return),
  'reservations',(select coalesce(jsonb_agg(to_jsonb(m)order by m.id),'[]')from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id and m.source_type='SALE_ITEM'where i.sale_id=h.id))::text)
 from erp.sales_headers h where h.id=p_sale
$$;

-- Participation is a source fact, never an authorization decision. Original
-- Native require_internal/owner checks remain before/after every hook. The
-- shared core owns root-aware legacy and orphan detection; no duplicate early
-- P/zero formula is introduced here.
create function cp7_credit.has_ow04_participation_v1(p_sale uuid)returns boolean
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare f jsonb;ids uuid[];
begin
 f:=ow04_source_proposal.family_read_v1(p_sale);
 select array_agg(value::uuid)into ids from jsonb_array_elements_text(f->'sale_ids');
 if exists(select 1 from cp7_credit.return_families where family_root_sale_id=(f->>'root_sale_id')::uuid)
  or exists(select 1 from cp7_credit.cohorts where source_sale_id=any(ids))
  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=any(ids))then return true;end if;
 -- No participation may hide a malformed protected financial journal.
 if erp._cp7_current_credit_adjustment(p_sale)<>0 then raise exception 'CP7_CREDIT_UNREGISTERED_FINANCIAL_PARTICIPATION';end if;
 return false;
end $$;

create function cp7_credit.is_unchanged_native_return_v1(p_return uuid)returns boolean
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare r erp.sales_returns;
begin
 -- TEMPORARY CHECKPOINT ONLY: this preserves existing Native lifecycle but
 -- does NOT register a genuinely new direct-Native empty family. Final whole
 -- feature installation remains blocked until the protected Native technical
 -- owning-operation registration is implemented; never call this completion.
 select *into strict r from erp.sales_returns where id=p_return;
 if exists(select 1 from cp7_credit.initial_return_work where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.return_command_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_credit.return_native_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()
   and c.sale_id=r.sale_id and c.action='RETURN')then return false;end if;
 return not cp7_credit.has_ow04_participation_v1(r.sale_id);
end $$;
