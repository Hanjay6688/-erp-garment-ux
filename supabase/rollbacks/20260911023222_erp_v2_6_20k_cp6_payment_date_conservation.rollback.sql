-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20k -> exact J.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py. The
-- controller verifies independently pinned source/capsule/function trust roots,
-- closes database admission, and drains old invocations before these bytes run.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';
set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;

do $platform_guard_v2620k$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20k_cp6_payment_date_conservation')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
      where name='erp_v2_6_20k_cp6_payment_date_conservation'
        and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
          in('567ede242847e7f0a428e673f896d61886f4cbb23e8bb55becf06c34a358b880',
             'ef8b8d4f5e3d1e723cadd0c3c5257fbeadb7c79c238295982172861ee462f614')) then
    raise exception 'v2.6.20k rollback refused: exact platform ledger identity is ambiguous';
  end if;
end
$platform_guard_v2620k$;

lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,erp.cp6_v2620j_rollback_capsule in share row exclusive mode;
lock table erp.cp6_v2620k_rollback_capsule in access exclusive mode;
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

do $guard_restore_v2620k$
declare
  c record;
  r record;
  v_table text;
  v_hash text;
  v_expected jsonb;
  v_platform text;
  v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20k')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20j')
     or (select count(*) from erp.cp6_v2620k_rollback_capsule)<>4 then
    raise exception 'v2.6.20k rollback refused: required application markers/capsule absent';
  end if;
  select version into strict v_platform from supabase_migrations.schema_migrations
  where name='erp_v2_6_20k_cp6_payment_date_conservation';
  if exists(select 1 from supabase_migrations.schema_migrations where version>v_platform)
     or exists(select 1 from erp.schema_migrations where version<>'v2.6.20k'
       and installed_at>(select installed_at from erp.schema_migrations where version='v2.6.20k')) then
    raise exception 'v2.6.20k rollback refused: successor installed';
  end if;

  for r in select * from(values
    ('erp.post_sales_payment(uuid)','5634d6fa8fa613e455b9de57b2bd186ac6424815ea2a0aa33866c7c235918e5a','362e4266718275af5af6efcded3c85cd7a7a7f1faba7241979114fe6e57ffd6c',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_sales_payment(uuid,text)','00d2c2e0dea82508840c06a9aa7ddade503df9a552a29b664beeb32cd081e5b6','e5f48784389148a40b2f71fbe9a3e133ff9a7bc95ec969da74e27163b0c5b069',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','3ab1c4e42616eadac12dd0d37811703fdd0436690a57ebe962c651af56e3588f','2bffd2d8f33ad2d918d1fb2f767676dc403ac777ad9a8ff69d4f32bf74067eff',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.guard_sales_payment_posted_identity_v2620j()','3849af0c4d17fa6fba90d87ff923dd82bf942f922d792ab5c2901f069b42a5d0','bc2f8539173958e7c8c8dd8287e193131598ee71286146e7d76d258d700e1617',array['postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select j.*,
      encode(extensions.digest(convert_to(j.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from erp.cp6_v2620k_rollback_capsule j
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
      raise exception 'TRUSTED_PREDECESSOR_PIN_MISMATCH: v2.6.20k %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected
  from erp.cp6_v2620k_rollback_capsule limit 1;
  if v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>30
     or exists(select 1 from erp.cp6_v2620k_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20k incomplete business boundary';
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
    'sales_payment_posting_facts','sales_payment_reversal_facts','cp6_v2620j_rollback_capsule'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'v2.6.20k rollback refused: post-install business history exists (%)',v_table;
    end if;
  end loop;

  for c in select * from erp.cp6_v2620k_rollback_capsule order by object_regidentity
  loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp.post_sales_payment(uuid)','5634d6fa8fa613e455b9de57b2bd186ac6424815ea2a0aa33866c7c235918e5a'),
    ('erp.reverse_sales_payment(uuid,text)','00d2c2e0dea82508840c06a9aa7ddade503df9a552a29b664beeb32cd081e5b6'),
    ('erp.run_v268_financial_report_checks()','3ab1c4e42616eadac12dd0d37811703fdd0436690a57ebe962c651af56e3588f'),
    ('erp.guard_sales_payment_posted_identity_v2620j()','3849af0c4d17fa6fba90d87ff923dd82bf942f922d792ab5c2901f069b42a5d0')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'v2.6.20k rollback restore hash mismatch for %: %',r.identity,v_actual;
    end if;
  end loop;
end
$guard_restore_v2620k$;

drop table erp.cp6_v2620k_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20k';
delete from supabase_migrations.schema_migrations
where name='erp_v2_6_20k_cp6_payment_date_conservation'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('567ede242847e7f0a428e673f896d61886f4cbb23e8bb55becf06c34a358b880',
       'ef8b8d4f5e3d1e723cadd0c3c5257fbeadb7c79c238295982172861ee462f614');

do $postcheck_v2620k$
declare r record; v_actual text;
begin
  for r in select * from(values
    ('erp.post_sales_payment(uuid)','5634d6fa8fa613e455b9de57b2bd186ac6424815ea2a0aa33866c7c235918e5a'),
    ('erp.reverse_sales_payment(uuid,text)','00d2c2e0dea82508840c06a9aa7ddade503df9a552a29b664beeb32cd081e5b6'),
    ('erp.run_v268_financial_report_checks()','3ab1c4e42616eadac12dd0d37811703fdd0436690a57ebe962c651af56e3588f'),
    ('erp.guard_sales_payment_posted_identity_v2620j()','3849af0c4d17fa6fba90d87ff923dd82bf942f922d792ab5c2901f069b42a5d0')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'v2.6.20k rollback postcondition function mismatch for %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20k')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20k_cp6_payment_date_conservation')
     or to_regclass('erp.cp6_v2620k_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20j')
     or to_regclass('erp.cp6_v2620j_rollback_capsule') is null
     or to_regclass('erp.sales_payment_posting_facts') is null
     or to_regclass('erp.sales_payment_reversal_facts') is null then
    raise exception 'v2.6.20k rollback postcondition failed';
  end if;
end
$postcheck_v2620k$;
commit;
