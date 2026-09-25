-- T3 release variant of supabase/rollbacks/20260921214120_erp_v2_6_20am_cp6_transfer_integrity.rollback.sql (sha256 d8e8cdd4eff7858d15ed972e28724d6d390e46c26305a95c620f662137748395), built by scripts/cp6_t3_rollback_acav.py from docs/evidence/cp6-t3/release_pins.json.
-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20am -> exact AL.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py after its
-- independently pinned trust checks, admission closure and session drain.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620am$
begin
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20am_cp6_transfer_integrity')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260921214120' and name='erp_v2_6_20am_cp6_transfer_integrity'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('8fff82f72f9c76dd032778fa43aa37fd3fde98c4304de033d9c484db54f04a60'))
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260921214120') then
    raise exception 'AM_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620am$;

lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.audit_logs,erp.journal_entries,erp.journal_lines,
  erp.account_daily_balances,erp.sales_headers,erp.sales_items,
  erp.sale_stock_allocations,erp.sales_returns,erp.sales_return_items,
  erp.sales_payments,erp.fg_lots,erp.fg_stock_movements,
  erp.fg_inventory_balances,erp.hpp_versions,erp.product_conversions,
  erp.product_conversion_allocations,erp.laundry_deliveries,
  erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events,
  erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,erp.sales_payment_posting_facts,
  erp.sales_payment_reversal_facts,erp.cp6_v2620j_rollback_capsule,
  erp.cp6_v2620k_rollback_capsule,erp.accounting_period_control,
  erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts,
  erp.laundry_claims,erp.laundry_vendors,erp.cp6_v2620l_rollback_capsule,
  erp.opening_balance_headers,erp.opening_balance_items,
  erp.opening_subledger_balances,erp.opening_subledger_settlements,
  erp.opening_financial_corrections,erp.supplier_payments,
  erp.material_purchase_headers,erp.material_purchase_items,
  erp.material_supplier_invoices,erp.material_supplier_invoice_lines,
  erp.material_supplier_returns,erp.material_supplier_return_items,
  erp.material_purchase_cost_corrections,
  erp.material_purchase_cost_correction_items,erp.material_stock_movements,
  erp.material_rolls,erp.cost_recalc_queue,erp.cost_adjustments,
  erp.suppliers,erp.materials,erp.cp6_v2620m_rollback_capsule,
  erp.supplier_cent_posting_facts,erp.material_cost_history,
  erp.material_cost_revaluation_state,erp.material_cost_revaluation_events,
  erp.material_cost_checkpoints,erp.cp6_v2620n_rollback_capsule,
  erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,
  erp.cp6_v2620q_rollback_capsule,erp.cp6_v2620r_rollback_capsule,
  erp.cp6_v2620s_rollback_capsule,erp.material_adjustments,
  erp.material_adjustment_items,erp.material_adjustment_revaluation_facts,
  erp.cp6_v2620t_rollback_capsule,erp.cp6_v2620u_rollback_capsule,
  erp.misc_finance_transactions,erp.misc_finance_categories,
  erp.cp6_v2620v_rollback_capsule,erp.scrap_batches,erp.scrap_sales,
  erp.cp6_v2620w_rollback_capsule,erp.app_roles,erp.app_role_permissions,erp.app_permissions,erp.cutting_bridge_execution_context,erp.bs_resolution_execution_context,erp.cp6_laundry_qc_execution_context
in share row exclusive mode;
lock table erp.cp6_v2620am_rollback_capsule in access exclusive mode;

do $lock_all_erp_v2620am$
declare v_table text;
begin
  for v_table in select relation.relname from pg_class relation join pg_namespace namespace on namespace.oid=relation.relnamespace where namespace.nspname='erp' and relation.relkind in('r','p') and relation.relname not in('schema_migrations','cp6_v2620am_rollback_capsule') order by relation.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620am$;

do $restore_guard_v2620am$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20al')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20am')
     or exists(select 1 from erp.schema_migrations
       where version not in('v2.6.20al','v2.6.20am')
         and installed_at>(select installed_at from erp.schema_migrations where version='v2.6.20am'))
     or (select count(*) from erp.cp6_v2620am_rollback_capsule)<>6 then
    raise exception 'AM_ROLLBACK_MARKER_CAPSULE_OR_SUCCESSOR';
  end if;
  for r in select * from(values
    ('erp.post_material_transfer_v2(uuid,uuid,bigint,text)','8fd42d9a97c72700ea121025290b63f5a081485d20e15057e6b8721509bfb1c4','e5ab13793e89dfc91480389eac86f67310282c78247b62d4dbaf9482582ae5bb',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_transfer_v2(uuid,text,uuid,bigint)','75c9f545470fea44ef699c92a7fa67f1c8237f3f58c404cba6a81673b012f387','e972291e00dea5611147389bd24dd9302ef20af78e6c4aa78fd1ec8aa54b5f21',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.guard_material_negative_stock()','355c37d742415e1a99e073f8f80317607368ee9c43ec1da42981d5213aab68b3','12051cc7a967fb83b4d0a5a7b3102b7a3a83399b73b2abb4749b5b0b5042416e',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','50e9edac8803dea3ca8d39fc78b77fd1c4c5499820b37dbb390b13b32c233c92','2069e292b0c43850a19469ae20af36616e396840619e72c43d204e209154987d',array['postgres=X/postgres']::text[]),
    ('erp.refresh_material_cost_checkpoint(uuid,date)','7eea402dec46b03d5425ef9c1c052ca409de7fafa72000b7abef5fda6849b30a','316775456f047127bffdb35310d5c0fd73024116368bfb349c5fe8218951f603',array['postgres=X/postgres']::text[]),
    ('erp.save_material_transfer_draft_v2(jsonb,uuid,bigint)','68f54f8255c63943ae8ba48930506f748c7398f9888edec6e89f86ccf89f3a3b','62cc5bead40f163681487b072299ffae411028a5249b7d533816fcf6e7169bd1',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from erp.cp6_v2620am_rollback_capsule cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or c.definition_actual is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.installed_actual is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or c.installed_owner is distinct from 'postgres'
       or c.installed_acl is distinct from r.acl then
      raise exception 'AM_TRUSTED_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;
  select boundary_snapshot into v_expected from erp.cp6_v2620am_rollback_capsule limit 1;
  if (select count(*) from (
       select relation.relname from pg_class relation
       join pg_namespace namespace on namespace.oid=relation.relnamespace
       where namespace.nspname='erp' and relation.relkind in('r','p')
         and relation.relname not in('schema_migrations','cp6_v2620am_rollback_capsule')
     ) all_erp_tables)<>225
     or v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>225
     or exists(select 1 from erp.cp6_v2620am_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'AM_BOUNDARY_SNAPSHOT_MISMATCH';
  end if;
  for v_table in
    select relation.relname from pg_class relation
    join pg_namespace namespace on namespace.oid=relation.relnamespace
    where namespace.nspname='erp' and relation.relkind in('r','p')
      and relation.relname not in('schema_migrations','cp6_v2620am_rollback_capsule')
    order by relation.relname
  loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'AM_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;
  for c in select * from erp.cp6_v2620am_rollback_capsule order by object_regidentity loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp.post_material_transfer_v2(uuid,uuid,bigint,text)','8fd42d9a97c72700ea121025290b63f5a081485d20e15057e6b8721509bfb1c4'),
    ('erp.reverse_material_transfer_v2(uuid,text,uuid,bigint)','75c9f545470fea44ef699c92a7fa67f1c8237f3f58c404cba6a81673b012f387'),
    ('erp.guard_material_negative_stock()','355c37d742415e1a99e073f8f80317607368ee9c43ec1da42981d5213aab68b3'),
    ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','50e9edac8803dea3ca8d39fc78b77fd1c4c5499820b37dbb390b13b32c233c92'),
    ('erp.refresh_material_cost_checkpoint(uuid,date)','7eea402dec46b03d5425ef9c1c052ca409de7fafa72000b7abef5fda6849b30a'),
    ('erp.save_material_transfer_draft_v2(jsonb,uuid,bigint)','68f54f8255c63943ae8ba48930506f748c7398f9888edec6e89f86ccf89f3a3b')
  ) expected(identity,sha256) loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'AM_ROLLBACK_RESTORE_HASH_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_guard_v2620am$;

drop table erp.cp6_v2620am_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20am';
delete from supabase_migrations.schema_migrations
where version='20260921214120'
  and name='erp_v2_6_20am_cp6_transfer_integrity'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('8fff82f72f9c76dd032778fa43aa37fd3fde98c4304de033d9c484db54f04a60');

do $postcheck_v2620am$
declare r record;v_actual text;
begin
  for r in select * from(values
    ('erp.post_material_transfer_v2(uuid,uuid,bigint,text)','8fd42d9a97c72700ea121025290b63f5a081485d20e15057e6b8721509bfb1c4',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_transfer_v2(uuid,text,uuid,bigint)','75c9f545470fea44ef699c92a7fa67f1c8237f3f58c404cba6a81673b012f387',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.guard_material_negative_stock()','355c37d742415e1a99e073f8f80317607368ee9c43ec1da42981d5213aab68b3',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','50e9edac8803dea3ca8d39fc78b77fd1c4c5499820b37dbb390b13b32c233c92',array['postgres=X/postgres']::text[]),
    ('erp.refresh_material_cost_checkpoint(uuid,date)','7eea402dec46b03d5425ef9c1c052ca409de7fafa72000b7abef5fda6849b30a',array['postgres=X/postgres']::text[]),
    ('erp.save_material_transfer_draft_v2(jsonb,uuid,bigint)','68f54f8255c63943ae8ba48930506f748c7398f9888edec6e89f86ccf89f3a3b',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'AM_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20am')
     or exists(select 1 from supabase_migrations.schema_migrations where name='erp_v2_6_20am_cp6_transfer_integrity')
     or to_regclass('erp.cp6_v2620am_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20al')
     or to_regclass('erp.cp6_v2620al_rollback_capsule') is null then
    raise exception 'AM_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620am$;
commit;
