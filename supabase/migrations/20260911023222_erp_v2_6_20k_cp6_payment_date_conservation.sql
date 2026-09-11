-- ERP Garment CP6 competition closure v2.6.20k.
-- COMP-J-01: conserve late allocation corrections per economic and GL date.
-- COMP-J-02: make immutable payment validation independent of caller TimeZone.
-- Additive migration; J and all prior source bytes remain unchanged.
-- Created by the official Supabase CLI migration new command.
begin;
set local lock_timeout='10s';
set local statement_timeout='240s';
set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,erp.cp6_v2620j_rollback_capsule in share row exclusive mode;
lock table erp.audit_logs,erp.journal_lines,erp.account_daily_balances,
  erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,
  erp.sales_returns,erp.sales_return_items,erp.sales_payments,
  erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.product_conversions,erp.product_conversion_allocations,
  erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events
in share row exclusive mode;

lock table erp.sales_payment_posting_facts,erp.sales_payment_reversal_facts
in share row exclusive mode;

do $guard_v2620k$
declare r record; v_actual text; v_count bigint;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20j')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20k')
     or to_regclass('erp.cp6_v2620k_rollback_capsule') is not null then
    raise exception 'K_REQUIRES_EXACT_J_WITHOUT_K_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20j_cp6_payment_fact_closure')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260910170556' and name='erp_v2_6_20j_cp6_payment_fact_closure'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('663cb98b2c432ce8518f922dcd7ecbaeb61d07bfb929ac49111a00ded29cad74',
              '8c3f3e0d56ea825f19f99a1c48db25c6ae916a6fc4896031560143da10ee67f1'))
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260910170556') then
    raise exception 'K_PREDECESSOR_PLATFORM_LEDGER_MISMATCH';
  end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context)
     or (select count(*) from erp.cp6_v2620j_rollback_capsule)<>3 then
    raise exception 'K_PREDECESSOR_CONTEXT_OR_CAPSULE_MISMATCH';
  end if;
  for r in select * from(values
    ('erp.post_sales_payment(uuid)','5634d6fa8fa613e455b9de57b2bd186ac6424815ea2a0aa33866c7c235918e5a',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_sales_payment(uuid,text)','00d2c2e0dea82508840c06a9aa7ddade503df9a552a29b664beeb32cd081e5b6',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','3ab1c4e42616eadac12dd0d37811703fdd0436690a57ebe962c651af56e3588f',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.guard_sales_payment_posted_identity_v2620j()','3849af0c4d17fa6fba90d87ff923dd82bf942f922d792ab5c2901f069b42a5d0',array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity);
    if v_actual is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity))
            is distinct from 'postgres'
       or (select case when p.proacl is null then null else
           array(select a::text from unnest(p.proacl) a order by a::text) end
           from pg_proc p where p.oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'K_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH';
    end if;
  end loop;
  for r in select * from(values
    ('erp.post_sales_payment(uuid)','010de4bae594258ba73348463ba90305a01485ed30b9c11918583be198c1f6df'),
    ('erp.reverse_sales_payment(uuid,text)','09c33e1cfbc673f9118878bd6da55e0df9c433252f0ecb099ef547895cab3ef6'),
    ('erp.run_v268_financial_report_checks()','c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1')
  ) expected(identity,sha256)
  loop
    if not exists(select 1 from erp.cp6_v2620j_rollback_capsule jc
      join pg_proc jp on jp.oid=to_regprocedure(jc.object_regidentity)
      where jc.object_regidentity=r.identity
        and jc.definition_sha256=r.sha256
        and encode(extensions.digest(convert_to(jc.object_definition,'UTF8'),'sha256'),'hex')=r.sha256
        and jc.installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(jp.oid),'UTF8'),'sha256'),'hex')
        and jc.owner_snapshot='postgres'
        and jc.acl_snapshot=case when jp.proacl is null then null else
          array(select ja::text from unnest(jp.proacl) ja order by ja::text) end) then
      raise exception 'K_PREDECESSOR_CAPSULE_SOURCE_PIN_MISMATCH';
    end if;
  end loop;
  -- Existing immutable UTC history is preserved byte for byte. Unknown legacy
  -- serialization or already misdated replacements require a separate reviewed
  -- data correction; this migration never rewrites posted facts or journals.
  select sum(issue_count) into v_count from erp.run_v268_financial_report_checks()
    where check_name in('V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH',
      'V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH');
  if v_count is distinct from 0 then
    raise exception 'K_PREEXISTING_PAYMENT_FACT_REVIEW_REQUIRED';
  end if;
  if exists(select 1 from erp.sales_payment_posting_facts f
    left join erp.sales_payment_reversal_facts prf on prf.payment_id=f.replaces_payment_id
    where f.replaces_payment_id is not null and(
      prf.payment_id is null
      or f.journal_economic_date is distinct from prf.reversal_economic_date
      or f.journal_transaction_date is distinct from prf.reversal_transaction_date
      or f.journal_posting_at<prf.reversal_posting_at)) then
    raise exception 'K_PREEXISTING_ALLOCATION_DATE_REVIEW_REQUIRED';
  end if;
end
$guard_v2620k$;
create table erp.cp6_v2620k_rollback_capsule(
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp(),
  boundary_snapshot jsonb
);
alter table erp.cp6_v2620k_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620k_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cp6_v2620k_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a order by a::text) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.post_sales_payment(uuid)'::regprocedure,
  'erp.reverse_sales_payment(uuid,text)'::regprocedure,
  'erp.run_v268_financial_report_checks()'::regprocedure,
  'erp.guard_sales_payment_posted_identity_v2620j()'::regprocedure
);


-- Keep the original cash receipt clock. A replacement corrects allocation on
-- its predecessor inverse's economic date; it must neutralize that inverse on
-- the same GL date as well. post_journal still enforces accounting periods.
do $patch_payment_v2620k$
declare d text; anchor text; replacement text;
begin
  select pg_get_functiondef('erp.post_sales_payment(uuid)'::regprocedure) into d;
  anchor:=$a$erp.post_journal('SALES_PAYMENT',p_payment_id,p.payment_date::date,$a$;
  replacement:=$r$erp.post_journal('SALES_PAYMENT',p_payment_id,
    case when p.replaces_payment_id is null then p.payment_date::date
      else prior_reversal.reversal_economic_date end,$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'K_PAYMENT_DATE_ANCHOR_MISMATCH';
  end if;
  d:=replace(d,anchor,replacement);
  anchor:=$a$  select * into strict j from erp.journal_entries where id=v_journal;$a$;
  replacement:=$r$  select * into strict j from erp.journal_entries where id=v_journal;
  if p.replaces_payment_id is not null and(
    j.economic_date is distinct from prior_reversal.reversal_economic_date
    or j.transaction_date is distinct from prior_reversal.reversal_transaction_date
    or j.posting_at<prior_reversal.reversal_posting_at) then
    raise exception 'PAYMENT_REPLACEMENT_DATE_CONSERVATION_REQUIRED';
  end if;$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'K_PAYMENT_POSTCONDITION_ANCHOR_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_payment_v2620k$;

do $patch_report_v2620k$
declare d text; anchor text; replacement text;
begin
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure) into d;
  anchor:=$a$and o.economic_date=p.payment_date::date$a$;
  replacement:=$r$and o.economic_date=case when p.replaces_payment_id is null
          then p.payment_date::date else (select pr.reversal_economic_date
            from erp.sales_payment_reversal_facts pr
            where pr.payment_id=p.replaces_payment_id) end$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'K_REPORT_PAYMENT_DATE_ANCHOR_MISMATCH';
  end if;
  d:=replace(d,anchor,replacement);
  anchor:=$a$  union all
  select 'V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH','CRITICAL',count(*)::bigint,$a$;
  replacement:=$r$  union all
  select 'V2620K_PAYMENT_ALLOCATION_DATE_MISMATCH','CRITICAL',count(*)::bigint,
    'Allocation replacement must conserve cash and customer AR on each economic and GL date'
  from erp.sales_payment_posting_facts f
  left join erp.sales_payment_reversal_facts pr on pr.payment_id=f.replaces_payment_id
  where f.replaces_payment_id is not null and(
    pr.payment_id is null
    or f.journal_economic_date is distinct from pr.reversal_economic_date
    or f.journal_transaction_date is distinct from pr.reversal_transaction_date
    or f.journal_posting_at<pr.reversal_posting_at)

  union all
  select 'V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH','CRITICAL',count(*)::bigint,$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'K_REPORT_CONSERVATION_ANCHOR_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_report_v2620k$;

-- JSON timestamp rendering is part of the immutable digest format. Bind its
-- producers, consumers and trigger to the established UTC representation.
-- PostgreSQL restores the caller's setting when each function returns.
alter function erp.post_sales_payment(uuid) set timezone='UTC';
alter function erp.reverse_sales_payment(uuid,text) set timezone='UTC';
alter function erp.run_v268_financial_report_checks() set timezone='UTC';
alter function erp.guard_sales_payment_posted_identity_v2620j() set timezone='UTC';
do $capture_boundary_v2620k$
declare v_table text; v_hash text; v_snapshot jsonb:='{}';
begin
  foreach v_table in array array[
    'app_users','idempotency_requests','products','audit_logs',
    'journal_entries','journal_lines','account_daily_balances',
    'sales_headers','sales_items','sale_stock_allocations',
    'sales_returns','sales_return_items','sales_payments',
    'fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions',
    'product_conversions','product_conversion_allocations',
    'laundry_deliveries','laundry_delivery_lines','laundry_receipts',
    'laundry_failed_wash_attempts','wip_stage_events',
    'cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule','cp6_v2620i_rollback_capsule',
    'sales_payment_posting_facts','sales_payment_reversal_facts','cp6_v2620j_rollback_capsule'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620k_rollback_capsule set boundary_snapshot=v_snapshot;
end
$capture_boundary_v2620k$;

do $installed_guard_v2620k$
declare r record; v_count bigint;
begin
  if (select count(*) from erp.cp6_v2620k_rollback_capsule)<>4 then
    raise exception 'ERP v2.6.20k incomplete rollback capsule';
  end if;
  for r in select c.*,p.proowner,p.proacl
    from erp.cp6_v2620k_rollback_capsule c
    join pg_proc p on p.oid=to_regprocedure(c.object_regidentity)
  loop
    if pg_get_userbyid(r.proowner) is distinct from r.owner_snapshot
       or (case when r.proacl is null then null else
             array(select a::text from unnest(r.proacl) a order by a::text) end)
          is distinct from r.acl_snapshot then
      raise exception 'ERP v2.6.20k changed owner/ACL for %',r.object_regidentity;
    end if;
  end loop;
  select issue_count into v_count from erp.run_v268_financial_report_checks()
  where check_name='V2620K_PAYMENT_ALLOCATION_DATE_MISMATCH';
  if v_count is distinct from 0 then
    raise exception 'ERP v2.6.20k immutable payment reconciliation failed: % issue(s)',v_count;
  end if;
  update erp.cp6_v2620k_rollback_capsule c set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
end
$installed_guard_v2620k$;


insert into erp.schema_migrations(version,description) values(
  'v2.6.20k','CP6 competition: payment allocation date conservation and canonical UTC fact validation'
);
commit;
