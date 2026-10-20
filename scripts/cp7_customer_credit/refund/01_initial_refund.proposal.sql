-- UNINSTALLED SOURCE PROPOSAL. No public facade, Native execution or authority stub.
do $not_an_installer$begin
 raise exception 'OW04_INITIAL_REFUND_REQUIRES_COMPLETE_OWNING_INTEGRATION';
end $not_an_installer$;

-- The owning coordinator DERIVES this immutable operation after actual INITIAL
-- recognition has materialized. Its UUID is also the consumption/source UUID.
-- No browser, service, sales role or unrelated helper receives table DML.
create table cp7_credit.initial_refund_operations(
 id uuid primary key,cohort_id uuid not null unique references cp7_credit.cohorts(id),
 initial_plan_id uuid not null unique references cp7_credit.recognition_plans(id),
 actor uuid not null,request_id uuid not null,backend_pid integer not null,transaction_id bigint not null,
 root_sale_id uuid not null references erp.sales_headers(id),
 current_leaf_id uuid not null references erp.sales_headers(id),
 full_amount cp7_credit.cent_amount not null check(full_amount>0),
 cash_account_id uuid not null references erp.cash_accounts(id),
 physical_at timestamptz not null check(isfinite(physical_at)),
 reason text not null check(reason=btrim(reason)and length(reason)between 5 and 1000),
 reference text check(length(reference)<=100),
 payload_sha256 text not null check(payload_sha256~'^[0-9a-f]{64}$'),
 quote_sha256 text not null check(quote_sha256~'^[0-9a-f]{64}$'),
 source_lock_sha256 text not null check(source_lock_sha256~'^[0-9a-f]{64}$'),
 projection_sha256 text not null check(projection_sha256~'^[0-9a-f]{64}$'),
 recognition_manifest_sha256 text not null check(recognition_manifest_sha256~'^[0-9a-f]{64}$'),
 required_book_floor date not null check(isfinite(required_book_floor)),
 book_floor_manifest jsonb not null check(jsonb_typeof(book_floor_manifest)='object'),
 materialization_ordinal bigint not null check(materialization_ordinal>0),
 authority_snapshot jsonb not null check(jsonb_typeof(authority_snapshot)='object'),
 cash_account_snapshot jsonb not null check(jsonb_typeof(cash_account_snapshot)='object'),
 recorded_at timestamptz not null default statement_timestamp(),
 unique(actor,request_id)
);
alter table cp7_credit.initial_refund_operations owner to postgres;
alter table cp7_credit.initial_refund_operations enable row level security;
create policy no_direct_access on cp7_credit.initial_refund_operations for all to public using(false)with check(false);
create trigger immutable_row before update or delete on cp7_credit.initial_refund_operations
 for each row execute function cp7_credit.immutable_fact();
create trigger immutable_truncate before truncate on cp7_credit.initial_refund_operations
 for each statement execute function cp7_credit.immutable_fact();

-- Separate, closed, one-call scope. It does not extend COMPONENT/RETURN or
-- erp.require_internal. The existing real cp7_sales RETURN context stays required.
create table cp7_credit.initial_refund_posting_scope(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 operation_id uuid not null references cp7_credit.initial_refund_operations(id),
 cohort_id uuid not null references cp7_credit.cohorts(id),request_id uuid not null,
 economic_date date not null,transaction_date date not null,lines_sha256_pg text not null,
 primary key(backend_pid,transaction_id),check(transaction_date>=economic_date),
 check(lines_sha256_pg~'^[0-9a-f]{64}$')
);
alter table cp7_credit.initial_refund_posting_scope owner to postgres;
alter table cp7_credit.initial_refund_posting_scope enable row level security;
revoke all on cp7_credit.initial_refund_operations,cp7_credit.initial_refund_posting_scope
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;

create function cp7_credit.refund_physical_text(p timestamptz)returns text
language sql immutable strict security invoker set search_path=''as $$
 select to_char(p at time zone'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
$$;

-- Pure normalization ONLY. A matching JSON object is not source/command proof.
create function cp7_credit.initial_refund_proof_shape(p jsonb)returns void
language plpgsql immutable security invoker set search_path=''as $$
declare keys text[];k text;
begin
 if jsonb_typeof(p)is distinct from'object'then raise exception 'CP7_CREDIT_REFUND_PROOF_SHAPE';end if;
 select array_agg(x order by x collate"C")into keys from jsonb_object_keys(p)x;
 if keys is distinct from array(select x from unnest(array[
  'contract_version','operation_id','cohort_id','actor','request_id','backend_pid','transaction_id','phase',
  'owning_action','stage','initial_plan_id','family_id','family_root_sale_id','current_leaf_id',
  'source_sale_id','source_return_id','full_k','cash_account_id','physical_at','reason','reference',
  'payload_sha256','quote_sha256','source_lock_sha256','projection_sha256','recognition_manifest_sha256',
  'materialization_ordinal','required_book_floor','book_floor_manifest_sha256','authority_sha256','cash_snapshot_sha256'])x order by x collate"C")then
  raise exception 'CP7_CREDIT_REFUND_PROOF_FIELDS';end if;
 for k in select jsonb_object_keys(p)loop
  if k='reference'then
   if jsonb_typeof(p->k)not in('string','null')or length(p->>k)>100 then raise exception 'CP7_CREDIT_REFUND_PROOF_SHAPE';end if;
  elsif jsonb_typeof(p->k)is distinct from'string'then raise exception 'CP7_CREDIT_REFUND_PROOF_SHAPE';end if;
 end loop;
 if p->>'contract_version'is distinct from'ow04.initial-refund-operation-proof.v1'
  or p->>'phase'not in('PREPOST','POSTPOST')or p->>'owning_action'is distinct from'RETURN_SETTLEMENT'
  or p->>'stage'is distinct from'NATIVE'then raise exception 'CP7_CREDIT_REFUND_PROOF_SHAPE';end if;
 foreach k in array array['operation_id','cohort_id','actor','request_id','initial_plan_id','family_id',
  'family_root_sale_id','current_leaf_id','source_sale_id','source_return_id','cash_account_id']loop
  if p->>k!~'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'then raise exception 'CP7_CREDIT_REFUND_PROOF_SHAPE';end if;
 end loop;
 foreach k in array array['backend_pid','transaction_id','materialization_ordinal']loop
  if p->>k!~'^[1-9][0-9]*$'then raise exception 'CP7_CREDIT_REFUND_PROOF_SHAPE';end if;
 end loop;
 foreach k in array array['payload_sha256','quote_sha256','source_lock_sha256','projection_sha256',
  'recognition_manifest_sha256','book_floor_manifest_sha256','authority_sha256','cash_snapshot_sha256']loop
  if p->>k!~'^[0-9a-f]{64}$'then raise exception 'CP7_CREDIT_REFUND_PROOF_SHAPE';end if;
 end loop;
 if p->>'full_k'!~'^(0|[1-9][0-9]*)[.][0-9]{2}$'or(p->>'full_k')::numeric<=0
  or p->>'physical_at'!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]{6}Z$'
  or not isfinite((p->>'physical_at')::timestamptz)
  or cp7_credit.refund_physical_text((p->>'physical_at')::timestamptz)is distinct from p->>'physical_at'
  or p->>'required_book_floor'!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  or not isfinite((p->>'required_book_floor')::date)
  or((p->>'required_book_floor')::date)::text is distinct from p->>'required_book_floor'
  or length(btrim(p->>'reason'))not between 5 and 1000 or p->>'reason'is distinct from btrim(p->>'reason')then
  raise exception 'CP7_CREDIT_REFUND_PROOF_SHAPE';end if;
end $$;

-- Factual floor is the minimum valid refund source book day, proved by the
-- coordinator; it is NOT max(all funding journals). REOPENED D2/D3 stays D2/D3.
create function cp7_credit.initial_refund_pair(p_physical timestamptz,p_lawful date,p_floor date,p_clock timestamptz)returns date
language plpgsql immutable security invoker set search_path=''as $$
declare e date;b date;
begin
 if p_physical is null or p_clock is null or p_lawful is null or p_floor is null
  or not isfinite(p_physical)or not isfinite(p_clock)or not isfinite(p_lawful)or not isfinite(p_floor)
  or p_physical>p_clock then raise exception 'CP7_CREDIT_REFUND_PHYSICAL_DATE';end if;
 e:=(p_physical at time zone'Asia/Jakarta')::date;b:=greatest(p_lawful,p_floor);
 if p_lawful<e or b<e or b>(p_clock at time zone'Asia/Jakarta')::date then
  raise exception 'CP7_CREDIT_REFUND_SOURCE_DATE';end if;
 return b;
end $$;

create function cp7_credit.initial_refund_capacity(p_i jsonb,p_c jsonb,p_economic date,p_book date,p_full numeric)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
declare c jsonb;
begin
 if p_full is null or p_full::text in('NaN','Infinity','-Infinity')or p_full<=0 or p_full*100<>trunc(p_full*100)then
  raise exception 'CP7_CREDIT_REFUND_POSITIVE_EXACT_FULL_K_REQUIRED';end if;
 if p_full>cp7_credit.native_journal_cent_max()then raise exception 'CP7_CREDIT_REFUND_NATIVE_JOURNAL_CAPACITY';end if;
 c:=ow04_pure_kernel.credit_capacity_v1(p_i,p_c,p_economic::text,p_book::text);
 if c->'source_prefixes_nonnegative'is distinct from'true'::jsonb
  or(c->>'current_balance')::numeric is distinct from p_full
  or(c->>'minimum_available')::numeric<p_full then
  raise exception 'CP7_CREDIT_REFUND_DATED_CAPACITY'using detail=c::text;end if;
 return c;
end $$;

create function cp7_credit.initial_refund_lines(p_liability uuid,p_cash_coa uuid,p_customer uuid,p_full numeric)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
begin
 if p_liability is null or p_cash_coa is null or p_customer is null or p_liability=p_cash_coa
  or p_full is null or p_full::text in('NaN','Infinity','-Infinity')or p_full<=0
  or p_full*100<>trunc(p_full*100)or p_full>cp7_credit.native_journal_cent_max()then
  raise exception 'CP7_CREDIT_REFUND_LINES_INVALID';end if;
 return cp7_credit.native_cent_lines(jsonb_build_array(
  jsonb_build_object('account_id',p_liability,'customer_id',p_customer,'description','Kredit retur: pengembalian uang','debit',p_full,'credit',0),
  jsonb_build_object('account_id',p_cash_coa,'customer_id',p_customer,'description','Kredit retur: pengembalian uang','debit',0,'credit',p_full)));
end $$;

create function cp7_credit.initial_refund_cash_snapshot(p_cash uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select jsonb_build_object('cash',to_jsonb(c),'account',to_jsonb(a),'mappings',coalesce(
  (select jsonb_agg(to_jsonb(m)order by m.mapping_key)from erp.accounting_account_mappings m where m.account_id=a.id),'[]'))
 from erp.cash_accounts c join erp.chart_accounts a on a.id=c.coa_account_id where c.id=p_cash
$$;

create function cp7_credit.initial_refund_recognition(p_operation uuid)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare o cp7_credit.initial_refund_operations;h cp7_credit.cohorts;a jsonb;manifest jsonb;i jsonb;c jsonb;
begin
 select *into strict o from cp7_credit.initial_refund_operations where id=p_operation;
 select *into strict h from cp7_credit.cohorts where id=o.cohort_id;
 -- Actual complete objects include every original/adjustment part and journal;
 -- planned components are not credit. Missing part/J or unbound inverse refuses.
 a:=cp7_credit.current_materialized_objects(h.source_sale_id,o.root_sale_id,o.current_leaf_id);
 select coalesce(jsonb_agg(x order by x->>'object_kind'collate"C",x->>'object_id'collate"C"),'[]')into manifest
  from jsonb_array_elements(a->'actual_objects')x where x->>'object_kind'<>'CONSUMPTION';
 if cp7_credit.pg_jsonb_sha256(manifest)is distinct from o.recognition_manifest_sha256 then
  raise exception 'CP7_CREDIT_REFUND_RECOGNITION_MANIFEST_CHANGED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('id','I:'||cc.id::text,'amount',cp7_credit.cent_text(cc.amount),
  'economic_date',cc.economic_date::text,'transaction_date',cc.transaction_date::text,'source_sha256',cc.component_sha256_pg)
  order by cc.id),'[]')into i from cp7_credit.recognition_components cc join cp7_credit.recognition_plans p on p.id=cc.plan_id
  where p.cohort_id=h.id;
 select coalesce(jsonb_agg(jsonb_build_object('id','C:'||ce.id::text,'amount',cp7_credit.cent_text(ce.amount),
  'economic_date',ce.economic_date::text,'transaction_date',ce.transaction_date::text,'source_sha256',ce.source_sha256)
  order by ce.id),'[]')into c from cp7_credit.consumption_events ce where ce.cohort_id=h.id;
 return jsonb_build_object('actual',a,'recognition',i,'consumptions',c,'recognition_objects',manifest);
end $$;

-- Conservation, not source authority. Full byte-derived Native source facts,
-- original payments (including status), all source journals/lines, stock and HPP
-- remain untouched. Only the new refund J/daily balances/consumption may change.
create function cp7_credit.initial_refund_native_snapshot(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare f jsonb;sales uuid[];returns uuid[];payments uuid[];lots uuid[];journals uuid[];v jsonb;
begin
 f:=ow04_source_proposal.family_read_v1(p_sale);
 select array_agg(value::uuid)into sales from jsonb_array_elements_text(f->'sale_ids');
 select coalesce(array_agg(id order by id),'{}')into returns from erp.sales_returns where sale_id=any(sales);
 with recursive ps(id)as(select id from erp.sales_payments where sale_id=any(sales)
  union select p.replaces_payment_id from ps join erp.sales_payments p on p.id=ps.id where p.replaces_payment_id is not null)
 select coalesce(array_agg(id order by id),'{}')into payments from ps;
 select coalesce(array_agg(distinct a.lot_id order by a.lot_id),'{}')into lots from erp.sale_stock_allocations a
  join erp.sales_items si on si.id=a.sale_item_id where si.sale_id=any(sales);
 with recursive base(id)as(
  select id from erp.journal_entries where(source_type='SALE'and source_id=any(sales))
   or(source_type='SALES_RETURN'and source_id=any(returns))or(source_type='SALES_PAYMENT'and source_id=any(payments))
  union select x.neutral_journal_id from cp7_note.journal_restatements x where x.previous_sale_id=any(sales)
  union select x.effective_journal_id from cp7_note.journal_restatements x where x.previous_sale_id=any(sales)
  union select x.neutral_journal_id from cp7_sales_return_correction.journal_restatements x where x.original_return_id=any(returns)
  union select x.effective_journal_id from cp7_sales_return_correction.journal_restatements x where x.original_return_id=any(returns)
  union select x.time_neutral_id from cp7_payment_correction.links x where x.original_id=any(payments)
  union select x.effective_inverse_id from cp7_payment_correction.links x where x.original_id=any(payments)
 ),walk(id)as(select id from base where id is not null union select j.id from walk w join erp.journal_entries j
  on j.reversal_of_id=w.id or(j.source_type='JOURNAL_REVERSAL'and j.source_id=w.id))
 select coalesce(array_agg(id order by id),'{}')into journals from walk;
 v:=jsonb_build_object('family',f,
  'sales',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.sales_headers t where id=any(sales)),
  'items',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.sales_items t where sale_id=any(sales)),
  'allocations',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.sale_stock_allocations t where sale_item_id in(select id from erp.sales_items where sale_id=any(sales))),
  'returns',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.sales_returns t where id=any(returns)),
  'return_items',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.sales_return_items t where return_id=any(returns)),
  'lots',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.fg_lots t where id=any(lots)),
  'movements',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.fg_stock_movements t where lot_id=any(lots)),
  'payments',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.sales_payments t where id=any(payments)),
  'payment_facts',(select coalesce(jsonb_agg(to_jsonb(t)order by t.payment_id),'[]')from erp.sales_payment_posting_facts t where payment_id=any(payments)),
  'payment_reversals',(select coalesce(jsonb_agg(to_jsonb(t)order by t.payment_id),'[]')from erp.sales_payment_reversal_facts t where payment_id=any(payments)),
  'advance_links',(select coalesce(jsonb_agg(to_jsonb(t)order by t.payment_id),'[]')from erp.initial_import_prepayment_payments t where payment_id=any(payments)),
  'advances',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.initial_import_prepayments t
   where id in(select advance_id from erp.initial_import_prepayment_payments where payment_id=any(payments))),
  'journals',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.journal_entries t where id=any(journals)),
  'lines',(select coalesce(jsonb_agg(to_jsonb(t)order by t.id),'[]')from erp.journal_lines t where journal_entry_id=any(journals)));
 return v;
end $$;

create function cp7_credit.require_refund_coordinator()returns void
language plpgsql stable security definer set search_path=''as $$
declare p oid;
begin
 p:=to_regprocedure('cp7_credit.assert_refund_operation_v1(uuid,uuid,text)');
 if p is null then raise exception 'CP7_CREDIT_REFUND_COORDINATOR_UNAVAILABLE';end if;
 if not exists(select 1 from pg_proc f where f.oid=p and f.prorettype='jsonb'::regtype and not f.proretset and f.prosecdef
  and f.provolatile='v'and pg_get_userbyid(f.proowner)='postgres'and f.proconfig@>array['search_path=""'])
  or exists(select 1 from unnest(array['anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write'])r
   where has_function_privilege(r,p,'EXECUTE'))then raise exception 'CP7_CREDIT_REFUND_COORDINATOR_METADATA';end if;
end $$;

-- Concrete request/context binding plus REQUIRED owning factual source proof.
-- The callback is intentionally NOT supplied here. PREPOST rechecks after both
-- period/CASH waits must NOT discover or acquire earlier source/master locks.
create function cp7_credit.assert_initial_refund_operation(p_operation uuid,p_cohort uuid,p_phase text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.initial_refund_operations;h cp7_credit.cohorts;p cp7_credit.recognition_plans;
 s cp7_credit.return_command_scope;r cp7_credit.return_requests;e cp7_credit.execution_context;
 proof jsonb;expected jsonb;current_access jsonb;cash jsonb;account erp.chart_accounts;
begin
 perform cp7_credit.require_refund_coordinator();
 if p_phase is null or p_phase not in('PREPOST','POSTPOST')or p_operation is null or p_cohort is null
  or current_setting('transaction_isolation')<>'read committed'or auth.uid()is null
  or auth.jwt()->>'role'is distinct from'authenticated'then raise exception using errcode='42501',message='CP7_CREDIT_REFUND_CURRENT_OWNER_REQUIRED';end if;
 select *into strict o from cp7_credit.initial_refund_operations where id=p_operation and cohort_id=p_cohort;
 select *into strict h from cp7_credit.cohorts where id=o.cohort_id;
 select *into strict p from cp7_credit.recognition_plans where id=o.initial_plan_id;
 select *into strict s from cp7_credit.return_command_scope where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and request_id=o.request_id;
 select *into strict r from cp7_credit.return_requests where actor=auth.uid()and request_id=o.request_id;
 select *into strict e from cp7_credit.execution_context where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 current_access:=cp7_credit.return_command_access('REFUND');
 if(o.actor,o.backend_pid,o.transaction_id)is distinct from(auth.uid(),pg_backend_pid(),txid_current())
  or(s.stage,s.mode,s.source_sale_id,s.return_id,s.family_id,s.credit_account_id,s.cash_account_id,s.refund_physical_at)is distinct from
   ('NATIVE','REFUND',h.source_sale_id,h.source_return_id,h.family_id,h.credit_account_id,o.cash_account_id,o.physical_at)
  or(s.payload_sha256,s.quote_sha256,s.source_lock_sha256,s.projection_sha256)is distinct from
   (o.payload_sha256,o.quote_sha256,o.source_lock_sha256,o.projection_sha256)
  or s.current_authority is distinct from o.authority_snapshot or current_access is distinct from o.authority_snapshot
  or s.credit_account_snapshot is distinct from h.credit_account_snapshot
  or e.authority_snapshot is distinct from o.authority_snapshot
  or(e.request_id,e.plan_id,e.owning_action,e.payload_sha256,e.review_sha256)is distinct from
   (o.request_id,p.id,'RETURN_SETTLEMENT',o.payload_sha256,o.quote_sha256)
  or r.response is not null or r.expected_version is distinct from s.expected_version
  or cp7_credit.pg_jsonb_sha256(r.payload)is distinct from o.payload_sha256
  or r.payload->>'quote_sha256'is distinct from o.quote_sha256
  or s.legacy_payload is distinct from(r.payload-'settlement'-'quote_sha256')
  or(o.cash_account_id,o.physical_at,o.reference,o.reason)is distinct from
   ((r.payload#>>'{settlement,cash_account_id}')::uuid,(r.payload#>>'{settlement,refund_physical_at}')::timestamptz,
    r.payload#>>'{settlement,reference}',btrim(r.payload->>'change_reason'))
  or r.payload#>>'{settlement,mode}'is distinct from'REFUND'
  or(r.payload#>>'{settlement,credit_account_id}')::uuid is distinct from h.credit_account_id
  or(h.initial_plan_id,h.initial_mode,h.initial_net_amount)is distinct from(p.id,'REFUND',o.full_amount)
  or(p.cohort_id,p.plan_kind,p.net_amount,p.actor,p.request_id)is distinct from(h.id,'INITIAL',o.full_amount,o.actor,o.request_id)
  or exists(select 1 from cp7_credit.recognition_plans q where q.cohort_id=h.id and q.id<>p.id)
  or not exists(select 1 from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current()and c.actor=auth.uid()and c.sale_id=h.source_sale_id and c.action='RETURN')
  or not exists(select 1 from cp7_credit.return_native_scope n where n.backend_pid=pg_backend_pid()
   and n.transaction_id=txid_current()and n.actor=auth.uid()and n.return_id=h.source_return_id
   and n.source_sale_id=h.source_sale_id and n.customer_id=h.customer_id and n.request_id=o.request_id
   and n.origin='REVIEWED_SETTLEMENT'and n.explicit_choice and n.recognition_nonempty
   and n.source_lock_sha256=o.source_lock_sha256 and n.projection_sha256=o.projection_sha256)
  or exists(select 1 from cp7_credit.posting_scope z where z.backend_pid=pg_backend_pid()and z.transaction_id=txid_current())
  or exists(select 1 from cp7_guard.compound_scope z where z.txid=txid_current())then
  raise exception using errcode='42501',message='CP7_CREDIT_REFUND_OWNING_BINDING_REQUIRED';end if;
 if o.book_floor_manifest->>'contract_version'is distinct from'ow04.initial-refund-book-plan.v1'
  or o.book_floor_manifest->>'economic_date'is distinct from((o.physical_at at time zone'Asia/Jakarta')::date)::text
  or o.book_floor_manifest->>'full_k'is distinct from cp7_credit.cent_text(o.full_amount)
  or o.book_floor_manifest->>'selected_book_date'is distinct from o.required_book_floor::text then
  raise exception 'CP7_CREDIT_REFUND_BOOK_MANIFEST_CHANGED';end if;
 if p_phase='PREPOST'and(exists(select 1 from cp7_credit.consumption_events where cohort_id=h.id)
  or exists(select 1 from erp.journal_entries where source_type='CP7_CUSTOMER_CREDIT_REFUND'and source_id=o.id))then
  raise exception 'CP7_CREDIT_REFUND_ALREADY_HAS_HISTORY';end if;
 if p_phase='POSTPOST'and((select count(*)from cp7_credit.consumption_events where cohort_id=h.id)<>1
  or not exists(select 1 from cp7_credit.consumption_events ce where ce.id=o.id and ce.cohort_id=h.id
   and ce.event_kind='REFUND'and ce.amount=o.full_amount and ce.target_sale_id is null
   and ce.cash_account_id=o.cash_account_id and ce.restores_event_id is null
   and ce.actor=o.actor and ce.request_id=o.request_id and ce.reason=o.reason
   and ce.source_sha256=cp7_credit.pg_jsonb_sha256(to_jsonb(o))))then
  raise exception 'CP7_CREDIT_REFUND_FINAL_CONSUMPTION_CHANGED';end if;
 cash:=cp7_credit.initial_refund_cash_snapshot(o.cash_account_id);
 if cash is null or cash is distinct from o.cash_account_snapshot or cash is distinct from s.cash_account_snapshot
  or cash#>'{cash,is_active}'is distinct from'true'::jsonb or cash#>'{account,is_active}'is distinct from'true'::jsonb
  or cash#>'{account,is_postable}'is distinct from'true'::jsonb or cash#>>'{account,account_type}'is distinct from'ASSET'
  or exists(select 1 from jsonb_array_elements(cash->'mappings')m where m->>'mapping_key'not in('CASH','BANK'))then
  raise exception 'CP7_CREDIT_REFUND_CASH_SOURCE_CHANGED';end if;
 select *into strict account from erp.chart_accounts where id=h.credit_account_id;
 if not account.is_active or not account.is_postable or account.account_type<>'LIABILITY'or account.normal_balance<>'CREDIT'
  or h.credit_account_id=(cash#>>'{account,id}')::uuid
  or exists(select 1 from erp.cash_accounts where coa_account_id=h.credit_account_id)
  or exists(select 1 from erp.accounting_account_mappings where account_id=h.credit_account_id)then
  raise exception 'CP7_CREDIT_REFUND_LIABILITY_SOURCE_CHANGED';end if;
 perform cp7_credit.check_credit_account(h.id);
 execute 'select cp7_credit.assert_refund_operation_v1($1,$2,$3)'into proof using o.id,h.id,p_phase;
 perform cp7_credit.initial_refund_proof_shape(proof);
 expected:=jsonb_build_object('contract_version','ow04.initial-refund-operation-proof.v1','operation_id',o.id::text,
  'cohort_id',h.id::text,'actor',o.actor::text,'request_id',o.request_id::text,'backend_pid',o.backend_pid::text,
  'transaction_id',o.transaction_id::text,'phase',p_phase,'owning_action','RETURN_SETTLEMENT','stage','NATIVE',
  'initial_plan_id',p.id::text,'family_id',h.family_id::text,'family_root_sale_id',o.root_sale_id::text,
  'current_leaf_id',o.current_leaf_id::text,'source_sale_id',h.source_sale_id::text,'source_return_id',h.source_return_id::text,
  'full_k',cp7_credit.cent_text(o.full_amount),'cash_account_id',o.cash_account_id::text,
  'physical_at',cp7_credit.refund_physical_text(o.physical_at),'reason',o.reason,'reference',o.reference,
  'payload_sha256',o.payload_sha256,'quote_sha256',o.quote_sha256,'source_lock_sha256',o.source_lock_sha256,
  'projection_sha256',o.projection_sha256,'recognition_manifest_sha256',o.recognition_manifest_sha256,
  'materialization_ordinal',o.materialization_ordinal::text,'required_book_floor',o.required_book_floor::text,
  'book_floor_manifest_sha256',cp7_credit.pg_jsonb_sha256(o.book_floor_manifest),
  'authority_sha256',cp7_credit.pg_jsonb_sha256(o.authority_snapshot),
  'cash_snapshot_sha256',cp7_credit.pg_jsonb_sha256(o.cash_account_snapshot));
 if proof is distinct from expected then raise exception 'CP7_CREDIT_REFUND_COORDINATOR_PROOF_CHANGED';end if;
 if cp7_credit.return_command_access('REFUND')is distinct from o.authority_snapshot then
  raise exception using errcode='42501',message='CP7_CREDIT_REFUND_ACCESS_CHANGED';end if;
 return proof;
end $$;

create function cp7_credit.assert_initial_refund_bound_post(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.initial_refund_posting_scope;o cp7_credit.initial_refund_operations;h cp7_credit.cohorts;lines jsonb;
begin
 select *into strict s from cp7_credit.initial_refund_posting_scope where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 select *into strict o from cp7_credit.initial_refund_operations where id=s.operation_id;
 select *into strict h from cp7_credit.cohorts where id=o.cohort_id;
 perform cp7_credit.assert_initial_refund_operation(o.id,h.id,'PREPOST');
 lines:=cp7_credit.initial_refund_lines(h.credit_account_id,(o.cash_account_snapshot#>>'{account,id}')::uuid,h.customer_id,o.full_amount);
 if(p_type,p_source,p_economic,s.cohort_id,s.request_id,s.lines_sha256_pg)is distinct from
  ('CP7_CUSTOMER_CREDIT_REFUND',o.id,(o.physical_at at time zone'Asia/Jakarta')::date,h.id,o.request_id,cp7_credit.native_lines_sha256(lines))
  or s.economic_date is distinct from p_economic or cp7_credit.native_cent_lines(p_lines)is distinct from lines then
  raise exception using errcode='42501',message='CP7_CREDIT_REFUND_BOUND_POST_REQUIRED';end if;
end $$;

-- Called by the exact Native copy AFTER its period SHARE and cent canonicalizer.
create function cp7_credit.initial_refund_bound_book_date(p_type text,p_source uuid,p_economic date,p_lines jsonb)returns date
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_credit.initial_refund_posting_scope;o cp7_credit.initial_refund_operations;b date;v jsonb;
begin
 perform cp7_credit.assert_initial_refund_bound_post(p_type,p_source,p_economic,p_lines);
 select *into strict s from cp7_credit.initial_refund_posting_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 select *into strict o from cp7_credit.initial_refund_operations where id=s.operation_id;
 b:=cp7_credit.initial_refund_pair(o.physical_at,erp.resolve_accounting_transaction_date(p_economic),o.required_book_floor,statement_timestamp());
 if b is distinct from s.transaction_date or b is distinct from o.required_book_floor then raise exception 'CP7_CREDIT_REFUND_REPLAN_REQUIRED';end if;
 v:=cp7_credit.initial_refund_recognition(o.id);
 perform cp7_credit.initial_refund_capacity(v->'recognition',v->'consumptions',p_economic,b,o.full_amount);
 return b;
end $$;

create function cp7_credit.initial_refund_bound_audit()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare s cp7_credit.initial_refund_posting_scope;o cp7_credit.initial_refund_operations;
begin
 select *into strict s from cp7_credit.initial_refund_posting_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 select *into strict o from cp7_credit.initial_refund_operations where id=s.operation_id;
 return jsonb_build_object('book_date_basis','ACTUAL_INITIAL_REFUND_SOURCE_FLOOR','operation_id',o.id,'cohort_id',o.cohort_id,
  'required_book_floor',o.required_book_floor,'lawful_book_date',erp.resolve_accounting_transaction_date(s.economic_date),
  'book_floor_manifest_sha256',cp7_credit.pg_jsonb_sha256(o.book_floor_manifest),
  'recognition_manifest_sha256',o.recognition_manifest_sha256,'lines_sha256_pg',s.lines_sha256_pg);
end $$;

create function cp7_credit.verify_initial_refund_journal(p_operation uuid,p_journal uuid,p_book date)returns text
language plpgsql stable security definer set search_path=''as $$
declare o cp7_credit.initial_refund_operations;h cp7_credit.cohorts;j erp.journal_entries;expected jsonb;actual jsonb;
begin
 select *into strict o from cp7_credit.initial_refund_operations where id=p_operation;
 select *into strict h from cp7_credit.cohorts where id=o.cohort_id;
 select *into strict j from erp.journal_entries where id=p_journal;
 if(j.source_type,j.source_id,j.status,j.reversal_of_id,j.economic_date,j.transaction_date)is distinct from
  ('CP7_CUSTOMER_CREDIT_REFUND',o.id,'POSTED',null::uuid,(o.physical_at at time zone'Asia/Jakarta')::date,p_book)
  or(select count(*)from erp.journal_entries where source_type='CP7_CUSTOMER_CREDIT_REFUND'and source_id=o.id)<>1
  or exists(select 1 from erp.journal_entries where reversal_of_id=j.id or(source_type='JOURNAL_REVERSAL'and source_id=j.id))
  or(select count(*)from erp.journal_lines where journal_entry_id=j.id)<>2
  or exists(select 1 from erp.journal_lines where journal_entry_id=j.id and(vendor_id is not null or contractor_id is not null or po_id is not null or product_id is not null))then
  raise exception 'CP7_CREDIT_REFUND_ACTUAL_JOURNAL_CHANGED';end if;
 select jsonb_agg(x order by x->>'account_id'collate"C")into expected from jsonb_array_elements(
  cp7_credit.initial_refund_lines(h.credit_account_id,(o.cash_account_snapshot#>>'{account,id}')::uuid,h.customer_id,o.full_amount))x;
 select jsonb_agg(jsonb_build_object('account_id',l.account_id,'customer_id',l.customer_id,'description',l.description,
  'debit',round(l.debit,2),'credit',round(l.credit,2))order by l.account_id::text collate"C")into actual
  from erp.journal_lines l where l.journal_entry_id=j.id;
 if actual is distinct from expected then raise exception 'CP7_CREDIT_REFUND_ACTUAL_LINES_CHANGED';end if;
 return cp7_credit.native_lines_sha256(actual);
end $$;

-- Sole writer entry: protected UUIDs only. It is called inside Native RETURN's
-- actual completion hook, with request→FG→all source/master/mapping locks already
-- owned, before outer response/final status. No late earlier-order locks here.
create function cp7_credit.post_initial_refund(p_operation uuid,p_cohort uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.initial_refund_operations;h cp7_credit.cohorts;pre jsonb;post jsonb;before_native jsonb;
 proof jsonb;capacity jsonb;lines jsonb;j uuid;e date;b date;line_sha text;event_sha text;actual_object jsonb;manifest jsonb;final_state jsonb;
begin
 proof:=cp7_credit.assert_initial_refund_operation(p_operation,p_cohort,'PREPOST');
 select *into strict o from cp7_credit.initial_refund_operations where id=p_operation;
 select *into strict h from cp7_credit.cohorts where id=p_cohort;
 perform cp7_credit.assert_current_materialized_profile(h.source_sale_id,o.root_sale_id,o.current_leaf_id);
 pre:=cp7_credit.initial_refund_recognition(o.id);
 if jsonb_array_length(pre->'consumptions')<>0 then raise exception 'CP7_CREDIT_REFUND_ALREADY_HAS_HISTORY';end if;
 before_native:=cp7_credit.initial_refund_native_snapshot(h.source_sale_id);
 -- Period may already be held by the real RETURN; preserving its SHARE remains
 -- mandatory. Fresh source/role comparison follows either possible wait.
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 if not found then raise exception 'CP7_CREDIT_REFUND_PERIOD_REQUIRED';end if;
 perform cp7_credit.assert_initial_refund_operation(o.id,h.id,'PREPOST');
 e:=(o.physical_at at time zone'Asia/Jakarta')::date;
 b:=cp7_credit.initial_refund_pair(o.physical_at,erp.resolve_accounting_transaction_date(e),o.required_book_floor,statement_timestamp());
 if b is distinct from o.required_book_floor then raise exception 'CP7_CREDIT_REFUND_REPLAN_REQUIRED';end if;
 capacity:=cp7_credit.initial_refund_capacity(pre->'recognition',pre->'consumptions',e,b,o.full_amount);
 lines:=cp7_credit.initial_refund_lines(h.credit_account_id,(o.cash_account_snapshot#>>'{account,id}')::uuid,h.customer_id,o.full_amount);
 -- Take the SAME COA lock used by the unchanged journal-line cash guard. Its
 -- AFTER INSERT call is reentrant; revalidate current authority before money.
 perform pg_advisory_xact_lock(hashtextextended('CP7_CASH|'||(o.cash_account_snapshot#>>'{account,id}'),0));
 perform cp7_credit.assert_initial_refund_operation(o.id,h.id,'PREPOST');
 if cp7_credit.initial_refund_recognition(o.id)is distinct from pre
  or cp7_credit.initial_refund_native_snapshot(h.source_sale_id)is distinct from before_native then
  raise exception 'CP7_CREDIT_REFUND_SOURCE_CHANGED_AFTER_WAIT';end if;
 insert into cp7_credit.initial_refund_posting_scope values(pg_backend_pid(),txid_current(),auth.uid(),o.id,h.id,o.request_id,e,b,cp7_credit.native_lines_sha256(lines));
 -- REQUIRED exact Native copy from 02_native_refund_transform.py, never a fake
 -- writer or a generic free-book-date overload. Its absence refuses execution.
 j:=cp7_credit._post_initial_refund_bound('CP7_CUSTOMER_CREDIT_REFUND',o.id,e,'Kredit retur: pengembalian uang',lines);
 line_sha:=cp7_credit.verify_initial_refund_journal(o.id,j,b);
 event_sha:=cp7_credit.pg_jsonb_sha256(to_jsonb(o));
 insert into cp7_credit.consumption_events(id,cohort_id,event_kind,amount,economic_date,transaction_date,target_sale_id,
  cash_account_id,restores_event_id,journal_id,source_sha256,lines_sha256_pg,actor,request_id,reason)
 values(o.id,h.id,'REFUND',o.full_amount,e,b,null,o.cash_account_id,null,j,event_sha,line_sha,o.actor,o.request_id,o.reason);
 post:=cp7_credit.initial_refund_recognition(o.id);
 if post->'recognition'is distinct from pre->'recognition'
  or post->'recognition_objects'is distinct from pre->'recognition_objects'
  or post#>>'{actual,I}'is distinct from pre#>>'{actual,I}'or post#>>'{actual,U}'is distinct from pre#>>'{actual,U}'
  or cp7_credit.initial_refund_native_snapshot(h.source_sale_id)is distinct from before_native
  or jsonb_array_length(post->'consumptions')<>1 then raise exception 'CP7_CREDIT_REFUND_I_P_SOURCE_CHANGED';end if;
 capacity:=ow04_pure_kernel.credit_capacity_v1(post->'recognition',post->'consumptions',e::text,b::text);
 if capacity->'source_prefixes_nonnegative'is distinct from'true'::jsonb
  or(capacity->>'current_balance')::numeric<>0 or(capacity->>'minimum_available')::numeric<>0 then
  raise exception 'CP7_CREDIT_REFUND_FINAL_CAPACITY_CHANGED';end if;
 select x into strict actual_object from jsonb_array_elements(post#>'{actual,actual_objects}')x
  where x->>'object_kind'='CONSUMPTION'and(x->>'object_id')::uuid=o.id;
 manifest:=jsonb_build_array(actual_object);
 -- Data-completeness only; live authority and final deferred receipt closure
 -- remain owning-coordinator obligations. No planned/unposted object is marked.
 insert into cp7_credit.financial_materializations(id,root_sale_id,actor,request_id,request_ordinal,owning_action,
  payload_sha256,source_plan_sha256,actual_objects,actual_objects_sha256)
 values(o.id,o.root_sale_id,o.actor,o.request_id,o.materialization_ordinal,'RETURN_SETTLEMENT',o.payload_sha256,
  o.projection_sha256,manifest,cp7_credit.pg_jsonb_sha256(manifest));
 insert into cp7_credit.financial_materialization_objects values('CONSUMPTION',o.id,o.id,actual_object->>'fact_sha256');
 perform cp7_guard.check_cash((o.cash_account_snapshot#>>'{account,id}')::uuid,e,b);
 perform cp7_credit.assert_initial_refund_operation(o.id,h.id,'POSTPOST');
 perform cp7_credit.assert_current_materialized_profile(h.source_sale_id,o.root_sale_id,o.current_leaf_id);
 final_state:=cp7_credit.initial_refund_recognition(o.id);
 if final_state is distinct from post
  or cp7_credit.initial_refund_cash_snapshot(o.cash_account_id)is distinct from o.cash_account_snapshot
  or cp7_credit.verify_initial_refund_journal(o.id,j,b)is distinct from line_sha
  or cp7_credit.initial_refund_native_snapshot(h.source_sale_id)is distinct from before_native then
  raise exception 'CP7_CREDIT_REFUND_COORDINATOR_CHANGED_NATIVE_SOURCE';end if;
 delete from cp7_credit.initial_refund_posting_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and actor=auth.uid()and operation_id=o.id;
 if not found then raise exception 'CP7_CREDIT_REFUND_SCOPE_LOST';end if;
 return jsonb_build_object('operation_id',o.id,'cohort_id',h.id,'consumption_event_id',o.id,'journal_id',j,
  'amount',cp7_credit.cent_text(o.full_amount),'economic_date',e,'transaction_date',b,'cash_account_id',o.cash_account_id,
  'physical_at',cp7_credit.refund_physical_text(o.physical_at),'source_type','CP7_CUSTOMER_CREDIT_REFUND',
  'materialization_id',o.id,'full_initial_refund',true);
end $$;

-- Compose with the existing generic reverse admission, including private copies.
-- No generic inverse (or inverse-of-inverse) may restore this credit on its own.
create function cp7_credit.assert_no_generic_initial_refund_reverse(p_journal uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
begin
 if p_journal is null then raise exception 'CP7_CREDIT_REFUND_JOURNAL_REQUIRED';end if;
 if exists(with recursive ancestry(id)as(select p_journal union select parent.id from ancestry a
  join erp.journal_entries child on child.id=a.id join erp.journal_entries parent
   on parent.id=child.reversal_of_id or(child.source_type='JOURNAL_REVERSAL'and parent.id=child.source_id))
  select 1 from ancestry a join erp.journal_entries j on j.id=a.id where j.source_type='CP7_CUSTOMER_CREDIT_REFUND'
   or exists(select 1 from cp7_credit.consumption_events ce where ce.journal_id=j.id and ce.event_kind='REFUND'))then
  raise exception 'CP7_CREDIT_REFUND_USE_OWNING_INVERSE_WORKFLOW';end if;
end $$;

-- Root must compose this table into context-free deferred closure (no leaked
-- refund scope, exact owning operation/receipt, materialization/profiles and
-- final status/cash/daily checks). No success placeholder trigger is installed.
do $owners$declare r record;begin
 for r in select p.oid::regprocedure signature from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='cp7_credit'and p.proname in('refund_physical_text','initial_refund_proof_shape','initial_refund_pair',
   'initial_refund_capacity','initial_refund_lines','initial_refund_cash_snapshot','initial_refund_recognition',
   'initial_refund_native_snapshot','require_refund_coordinator','assert_initial_refund_operation',
   'assert_initial_refund_bound_post','initial_refund_bound_book_date','initial_refund_bound_audit',
   'verify_initial_refund_journal','post_initial_refund','assert_no_generic_initial_refund_reverse')loop
  execute format('alter function %s owner to postgres',r.signature);
  execute format('revoke all on function %s from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write',r.signature);
 end loop;
end $owners$;
