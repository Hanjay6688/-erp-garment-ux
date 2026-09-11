-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20l -> exact K.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py. The
-- controller verifies independently pinned source/capsule/function trust roots,
-- closes database admission, and drains old invocations before these bytes run.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';
set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;

do $platform_guard_v2620l$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20l_cp6_exact_ledger_conservation')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
      where name='erp_v2_6_20l_cp6_exact_ledger_conservation'
        and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
          in('f46e70911e9e582fa9b7dd742c9a94d455662fa52eac256afd86f590f4d4b815',
             '8ba7ed8baf7fb97bca277b66e4901a5b9cff773cfec7d91bb7e9402fb28d9a04')) then
    raise exception 'v2.6.20l rollback refused: exact platform ledger identity is ambiguous';
  end if;
end
$platform_guard_v2620l$;

lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,erp.cp6_v2620j_rollback_capsule in share row exclusive mode;
lock table erp.cp6_v2620k_rollback_capsule,erp.accounting_period_control,erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts,erp.laundry_claims,erp.laundry_vendors in share row exclusive mode;
lock table erp.cp6_v2620l_rollback_capsule in access exclusive mode;
lock table erp.sales_payment_reversal_facts,erp.sales_payment_posting_facts
in access exclusive mode;
lock table erp.audit_logs,erp.journal_lines,erp.account_daily_balances,
  erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,
  erp.sales_returns,erp.sales_return_items,erp.sales_payments,
  erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.product_conversions,erp.product_conversion_allocations,
  erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events
in share row exclusive mode;

do $guard_restore_v2620l$
declare
  c record;
  r record;
  v_table text;
  v_hash text;
  v_expected jsonb;
  v_platform text;
  v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20l')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20k')
     or (select count(*) from erp.cp6_v2620l_rollback_capsule)<>3 then
    raise exception 'v2.6.20l rollback refused: required application markers/capsule absent';
  end if;
  select version into strict v_platform from supabase_migrations.schema_migrations
  where name='erp_v2_6_20l_cp6_exact_ledger_conservation';
  if exists(select 1 from supabase_migrations.schema_migrations where version>v_platform)
     or exists(select 1 from erp.schema_migrations where version<>'v2.6.20l'
       and installed_at>(select installed_at from erp.schema_migrations where version='v2.6.20l')) then
    raise exception 'v2.6.20l rollback refused: successor installed';
  end if;

  for r in select * from(values
    ('erp.post_journal(text,uuid,date,text,jsonb)','c9bfb4804246a2c7b2352ef0a67db5e035939e29f292f2dff34e0b2b590d4e76','1ae479c9c32b9489e659d83d99a9829ef88876643f3e8f8aa276fee6d96a9cdf',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','4eb19d881f47dbbf57bc69f4f49ffdbb5c3071b4b126d2398d26dd2e980b2bf7','dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.resolve_laundry_claim(uuid,text,text)','51ebcf8c01d7d47279112808424d7c18e2ea637d9fa7a41472a21de15b17b54b','20eba16640912f04220437c21df018a6799dc48b06d8147abfbd2454e2d60425',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select j.*,
      encode(extensions.digest(convert_to(j.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from erp.cp6_v2620l_rollback_capsule j
    left join pg_proc p on p.oid=to_regprocedure(j.object_regidentity)
    where j.object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or c.definition_actual is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.installed_actual is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.installed_owner is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or c.installed_acl is distinct from r.acl then
      raise exception 'TRUSTED_PREDECESSOR_PIN_MISMATCH: v2.6.20l %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected
  from erp.cp6_v2620l_rollback_capsule limit 1;
  if v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>37
     or exists(select 1 from erp.cp6_v2620l_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20l incomplete business boundary';
  end if;
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
    'sales_payment_posting_facts','sales_payment_reversal_facts','cp6_v2620j_rollback_capsule',
    'cp6_v2620k_rollback_capsule','accounting_period_control','accounting_account_mappings','cash_accounts','chart_accounts','laundry_claims','laundry_vendors'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'v2.6.20l rollback refused: post-install business history exists (%)',v_table;
    end if;
  end loop;

  for c in select * from erp.cp6_v2620l_rollback_capsule order by object_regidentity
  loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp.post_journal(text,uuid,date,text,jsonb)','c9bfb4804246a2c7b2352ef0a67db5e035939e29f292f2dff34e0b2b590d4e76'),
    ('erp._v268_financial_report_checks_pre_scope()','4eb19d881f47dbbf57bc69f4f49ffdbb5c3071b4b126d2398d26dd2e980b2bf7'),
    ('erp.resolve_laundry_claim(uuid,text,text)','51ebcf8c01d7d47279112808424d7c18e2ea637d9fa7a41472a21de15b17b54b')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'v2.6.20l rollback restore hash mismatch for %: %',r.identity,v_actual;
    end if;
  end loop;
end
$guard_restore_v2620l$;

drop table erp.cp6_v2620l_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20l';
delete from supabase_migrations.schema_migrations
where name='erp_v2_6_20l_cp6_exact_ledger_conservation'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('f46e70911e9e582fa9b7dd742c9a94d455662fa52eac256afd86f590f4d4b815',
       '8ba7ed8baf7fb97bca277b66e4901a5b9cff773cfec7d91bb7e9402fb28d9a04');

do $postcheck_v2620l$
declare r record; v_actual text;
begin
  for r in select * from(values
    ('erp.post_journal(text,uuid,date,text,jsonb)','c9bfb4804246a2c7b2352ef0a67db5e035939e29f292f2dff34e0b2b590d4e76'),
    ('erp._v268_financial_report_checks_pre_scope()','4eb19d881f47dbbf57bc69f4f49ffdbb5c3071b4b126d2398d26dd2e980b2bf7'),
    ('erp.resolve_laundry_claim(uuid,text,text)','51ebcf8c01d7d47279112808424d7c18e2ea637d9fa7a41472a21de15b17b54b')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'v2.6.20l rollback postcondition function mismatch for %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20l')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20l_cp6_exact_ledger_conservation')
     or to_regclass('erp.cp6_v2620l_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20k')
     or to_regclass('erp.cp6_v2620k_rollback_capsule') is null
     or to_regclass('erp.sales_payment_posting_facts') is null
     or to_regclass('erp.sales_payment_reversal_facts') is null then
    raise exception 'v2.6.20l rollback postcondition failed';
  end if;
end
$postcheck_v2620l$;
commit;
