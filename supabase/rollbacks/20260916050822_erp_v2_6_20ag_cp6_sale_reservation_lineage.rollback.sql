-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20ag -> exact AF.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py after its
-- independently pinned trust checks, admission closure and session drain.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620ag$
begin
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ag_cp6_sale_reservation_lineage')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260916050822' and name='erp_v2_6_20ag_cp6_sale_reservation_lineage'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('06d32bb921b0f19e1ffe0f8c689d6ce826aaf467163e6ea15ef7c762389c2d7f','b181c530959890659a95a665ee1ba87c54429661ed939f5d374bee72d10709c9'))
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260916050822') then
    raise exception 'AG_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620ag$;

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
lock table erp.cp6_v2620ag_rollback_capsule in access exclusive mode;

do $lock_all_erp_v2620ag$
declare v_table text;
begin
  for v_table in select relation.relname from pg_class relation join pg_namespace namespace on namespace.oid=relation.relnamespace where namespace.nspname='erp' and relation.relkind in('r','p') and relation.relname not in('schema_migrations','cp6_v2620ag_rollback_capsule') order by relation.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620ag$;

do $restore_guard_v2620ag$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20af')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20ag')
     or exists(select 1 from erp.schema_migrations
       where version not in('v2.6.20af','v2.6.20ag')
         and installed_at>(select installed_at from erp.schema_migrations where version='v2.6.20ag'))
     or (select count(*) from erp.cp6_v2620ag_rollback_capsule)<>4 then
    raise exception 'AG_ROLLBACK_MARKER_CAPSULE_OR_SUCCESSOR';
  end if;
  for r in select * from(values
    ('erp.guard_child_by_parent_status()','05d181c08289b4fa81d73e99ed1453fd8ad931bc3d99d3c0480f96a027ca3b0e','86080f579e1b2803d1bbf50b22b14b0bf3fa168aeabf190ab3816d4b23324fce',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.guard_posted_document()','573b6ec5dda2340b0c403642e42ef70d692bc0506b3c5d7a1c2abc372e7fb387','5393f2df6fb66d665fca3f5e18fcf5f5acbdf8bd1a2ae938810bf666e41819cd',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_sale(uuid)','f485761060593d1b9fac5b5ecf7556007a7907467ad5ccd90be057ec9e9823f4','32aabd5482c92cc13a3e302107fac182a6f184a3d4f8a5b96d6009bdb3c4da44',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','c5b587583c1ae3d47ea6f52b50c9b63d982da18cfd7e027046ce0f5eb5d56ee2','3a63adddefd86f83e5a94279437174d2e3abd0c0105e7a2e1e03a40a248e5364',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from erp.cp6_v2620ag_rollback_capsule cap
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
      raise exception 'AG_TRUSTED_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;
  select boundary_snapshot into v_expected from erp.cp6_v2620ag_rollback_capsule limit 1;
  if (select count(*) from (
       select relation.relname from pg_class relation
       join pg_namespace namespace on namespace.oid=relation.relnamespace
       where namespace.nspname='erp' and relation.relkind in('r','p')
         and relation.relname not in('schema_migrations','cp6_v2620ag_rollback_capsule')
     ) all_erp_tables)<>219
     or v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>219
     or exists(select 1 from erp.cp6_v2620ag_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'AG_BOUNDARY_SNAPSHOT_MISMATCH';
  end if;
  for v_table in
    select relation.relname from pg_class relation
    join pg_namespace namespace on namespace.oid=relation.relnamespace
    where namespace.nspname='erp' and relation.relkind in('r','p')
      and relation.relname not in('schema_migrations','cp6_v2620ag_rollback_capsule')
    order by relation.relname
  loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'AG_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;
  for c in select * from erp.cp6_v2620ag_rollback_capsule order by object_regidentity loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp.guard_child_by_parent_status()','05d181c08289b4fa81d73e99ed1453fd8ad931bc3d99d3c0480f96a027ca3b0e'),
    ('erp.guard_posted_document()','573b6ec5dda2340b0c403642e42ef70d692bc0506b3c5d7a1c2abc372e7fb387'),
    ('erp.post_sale(uuid)','f485761060593d1b9fac5b5ecf7556007a7907467ad5ccd90be057ec9e9823f4'),
    ('erp.run_v268_financial_report_checks()','c5b587583c1ae3d47ea6f52b50c9b63d982da18cfd7e027046ce0f5eb5d56ee2')
  ) expected(identity,sha256) loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'AG_ROLLBACK_RESTORE_HASH_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_guard_v2620ag$;

drop table erp.cp6_v2620ag_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20ag';
delete from supabase_migrations.schema_migrations
where version='20260916050822'
  and name='erp_v2_6_20ag_cp6_sale_reservation_lineage'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('06d32bb921b0f19e1ffe0f8c689d6ce826aaf467163e6ea15ef7c762389c2d7f',
       'b181c530959890659a95a665ee1ba87c54429661ed939f5d374bee72d10709c9');

do $postcheck_v2620ag$
declare r record;v_actual text;
begin
  for r in select * from(values
    ('erp.guard_child_by_parent_status()','05d181c08289b4fa81d73e99ed1453fd8ad931bc3d99d3c0480f96a027ca3b0e',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.guard_posted_document()','573b6ec5dda2340b0c403642e42ef70d692bc0506b3c5d7a1c2abc372e7fb387',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_sale(uuid)','f485761060593d1b9fac5b5ecf7556007a7907467ad5ccd90be057ec9e9823f4',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','c5b587583c1ae3d47ea6f52b50c9b63d982da18cfd7e027046ce0f5eb5d56ee2',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'AG_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20ag')
     or exists(select 1 from supabase_migrations.schema_migrations where name='erp_v2_6_20ag_cp6_sale_reservation_lineage')
     or to_regclass('erp.cp6_v2620ag_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20af')
     or to_regclass('erp.cp6_v2620af_rollback_capsule') is null then
    raise exception 'AG_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620ag$;
commit;
