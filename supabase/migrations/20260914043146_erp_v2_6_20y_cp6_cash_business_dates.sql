-- CP6 Y: canonical Jakarta opening settlement, vendor and customer cash dates.
-- Native audit #173: 16 qualified counterexamples, 19 controls, no incomplete cases.
-- Append-only successor. Published migrations/rollbacks through X + R2 stay immutable.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
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

do $lock_all_erp_v2620y$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620y_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620y$;

do $predecessor_v2620y$
declare r record;c record;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20x')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20y')
     or to_regclass('erp.cp6_v2620y_rollback_capsule') is not null then
    raise exception 'Y_REQUIRES_EXACT_X_WITHOUT_Y_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20x_cp6_internal_role_fail_closed')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260913202948'
         and name='erp_v2_6_20x_cp6_internal_role_fail_closed'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('53af147202671e5919a49080ed135ab9896399867bbb71065ef2da57f6543117',
              'ae81dc594310794596a32d5719aa76068eb2b47f3898bc2780c48cc2419dccac'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260913202948')
     or (select count(*) from erp.cp6_v2620x_rollback_capsule)<>1
     or (select count(*) from erp.cp6_v2620w_rollback_capsule)<>3 then
    raise exception 'Y_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH';
  end if;
  -- Authenticate all seven U capsule rows before replacing three functions.
  for r in select * from(values
    ('erp._cp3_r4_reverse_journal_internal(uuid,text)','9b60fcd88852337ad0956d471e54c1c04bcccd35f5e85a8e5093469cc1c37249','2d54bfdf9bf0912e6b13e558ddbc4cb419020f191c3ce626a26f2c27b814b20c',array['postgres=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','8e0e303066c23476223089e2705b8ad0861b34faa2efb12c58663677f454b196','3a8af1f92f85ddbebf697b681e16f42b9c48b2cdb543b6ab2daa2a928a5bc775',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.get_owner_financial_snapshot_v2(date,date,date)','e51dbe224d112f523e51bddc609ee0f0036ecae2ef5d328b865326781aa8780c','0afb94d932b1c7488c1a787de7f734133c1674e0a43100d366c6f3f129ffb9bb',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_adjustment(uuid)','be5a163932f0678667d94095f3db519abb7e5df4ea2c4c95204e42620ee27d83','b32962d12adde0ca4ae659f2dd83a02a0a3111c3a9060d845ed2e82025696201',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_purchase(uuid)','83f51a14eef3b2942b7158e81c2db1ee1e7ec401368fd8abb6bc013bf1be95de','17547ee019fca617bf67100d9b3b899b96781a2fa62cc47c57bb2dbafe358082',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','acd6f623c83f1ce74323a11b9224955ea922b10788ed631b9973aa9345698af8','f32dcd6d6be2ef1f2762bce1dac463aeeed8965f4ef94f8e7a31f8da4451e6ce',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.sync_material_purchase_grni_on_status()','7537c077a003924fce425c9db9769824fc5ffdd0e761e7b292508b1e248ad870','e39d7cc4b457a58b929894f4fd5a9c7f47aa0da678853a3ddbee65f9630d676c',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620u_rollback_capsule
      where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
            is distinct from (case r.identity
              when 'erp.run_v267_financial_truth_checks()' then '845b9868bb0b0e25443c4e75c77cfcf815e34c4fac78b8bd38038b0476e2944a'
              when 'erp._v268_financial_report_checks_pre_scope()' then 'c77df75873558f96425b8e6b9591903259e5d985a9bd534ab96466799610e507'
              else r.installed_sha256 end)
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'Y_TRUSTED_U_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  -- Authenticate all three exact V capsules, including preserved misc cash.
  for r in select * from(values
    ('erp.post_misc_finance(uuid)','1f8973f9426efe3555a587e0df5e8a852e4431464db651ec6f630ef1893a098c','f2e403942beaeb68a31057f5a0439f87da89519a9ba02f105907aa415c488c00',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','f32dcd6d6be2ef1f2762bce1dac463aeeed8965f4ef94f8e7a31f8da4451e6ce','13e1c0b7e3a9262aecd18504cb70890eeaeb61190c12e2cc7bb16f2e2d9ddfb2',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','3a8af1f92f85ddbebf697b681e16f42b9c48b2cdb543b6ab2daa2a928a5bc775','bdce68bf47700519d663e63302b5d48a720959d1c9995fcb9d8599a9516c2eef',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620v_rollback_capsule
      where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from (case r.identity
              when 'erp.run_v267_financial_truth_checks()' then '845b9868bb0b0e25443c4e75c77cfcf815e34c4fac78b8bd38038b0476e2944a'
              when 'erp._v268_financial_report_checks_pre_scope()' then 'c77df75873558f96425b8e6b9591903259e5d985a9bd534ab96466799610e507'
              else r.installed_sha256 end)
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'Y_TRUSTED_V_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  -- Authenticate all three admitted W capsule rows.
  for r in select * from(values
    ('erp.post_scrap_sale(uuid)','53e2b8c582b342b2b4391a3fdcf91308c0e0e0f08e021c9f800b99212f64d39c','cb573efa942bbf65e770dd645cc0636ea4142633241af16842b532f36ce32131',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','13e1c0b7e3a9262aecd18504cb70890eeaeb61190c12e2cc7bb16f2e2d9ddfb2','845b9868bb0b0e25443c4e75c77cfcf815e34c4fac78b8bd38038b0476e2944a',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','bdce68bf47700519d663e63302b5d48a720959d1c9995fcb9d8599a9516c2eef','c77df75873558f96425b8e6b9591903259e5d985a9bd534ab96466799610e507',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620w_rollback_capsule
      where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'Y_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  -- Pin the shared authorization guard and inherited private helpers/facts.
  for r in select * from(values
    ('erp.post_scrap_sale(uuid)','cb573efa942bbf65e770dd645cc0636ea4142633241af16842b532f36ce32131',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.require_internal()','5dffcd53c0a5de609ae41482ca246d2afc806b9d92241253d680cf5c7fe1612e',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.current_app_role()','ca1a9e2bb44aa8c5f80911728175f923f82472ca170e68b7c21d759601da4022',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.current_app_user_id()','b65a4c13983626e8c7a218a2cb68ca24a809f511b8bf20c1f3aa2116b3fd2a10',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.has_permission(text)','a9942661396f6c1f3f535720e806a5431db10a11dc1399787a30af733a882d2b',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._idempotency_actor_key()','63f9ecea25c22be59917d9153d6686e1cdf6da5a1cf3ede839287aa08c582a92',array['postgres=X/postgres']::text[]),
    ('erp._cp3_business_date(timestamp with time zone)','adf1fb87dd9f0b6a856bcb109b5118f9c4aac5da0ac32554ecbbc009f6d88248',array['postgres=X/postgres']::text[]),
    ('erp._cp6_material_adjustment_revaluation_state(uuid)','47a2c15955a682040d2c0c6b72f2941eaae8467e2b16fa5c4bbc10dff27a3c2e',array['postgres=X/postgres']::text[]),
    ('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)','355246b52dc88e5d91643485fe796f24e7975d0629824c5b28c31074469ed7ba',array['postgres=X/postgres']::text[]),
    ('erp.guard_material_adjustment_revaluation_fact_v2620t()','c2cc7ddb076f557d0f71df9170b9d02425fc17c2f33e471bd1af48e61729829e',array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(
        to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc
         where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
         from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'Y_TRUSTED_U_INPUT_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if not exists(select 1 from pg_class
      where oid='erp.material_adjustment_revaluation_facts'::regclass
        and relrowsecurity and relowner='postgres'::regrole)
     or exists(select 1 from information_schema.role_table_grants
       where table_schema='erp' and table_name='material_adjustment_revaluation_facts'
         and grantee in('PUBLIC','anon','authenticated','service_role'))
     or (select count(*) from pg_trigger
       where tgrelid='erp.material_adjustment_revaluation_facts'::regclass
         and not tgisinternal and tgenabled='O'
         and tgfoid='erp.guard_material_adjustment_revaluation_fact_v2620t()'::regprocedure
         and tgname in('trg_material_adjustment_revaluation_fact_append_only',
           'trg_material_adjustment_revaluation_fact_no_truncate'))<>2 then
    raise exception 'Y_INHERITED_T_SECURITY_MISMATCH';
  end if;
  if exists(
    select 1 from erp.journal_entries j
    join erp.material_adjustments h on h.id=j.source_id
    where j.source_type='MATERIAL_ADJUSTMENT' and j.status in('POSTED','REVERSED')
      and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)
  ) or exists(
    select 1 from erp.journal_entries j
    where j.source_type='JOURNAL_REVERSAL' and j.status='POSTED'
      and j.economic_date is distinct from erp._cp3_business_date(j.posting_at)
  ) or exists(
    select 1 from erp.journal_entries j
    join erp.material_purchase_headers h on h.id=j.source_id
    where j.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS')
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)
  ) or exists(
    select 1 from erp.journal_entries j
    join erp.misc_finance_transactions h on h.id=j.source_id
    where j.source_type='MISC_FINANCE' and j.status in('POSTED','REVERSED')
      and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)
  ) or exists(
    select 1 from erp.journal_entries j
    join erp.scrap_sales h on h.id=j.source_id
    where j.source_type='SCRAP_SALE' and j.status in('POSTED','REVERSED')
      and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)
  ) then
    raise exception 'Y_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED';
  end if;
  -- Independent six-function predecessor pins, not capsule self-authentication.
  for r in select * from(values
    ('erp.post_opening_subledger_settlement(uuid)','c56b387a8593b19cd3b92e6dc20ac95459d2aedeb2b616b6fb1e4d812e729393',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_vendor_payment(uuid)','05b067af75c8691c4e012ff719f8793dbe597ee5f0e451db665d4baab1427316',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_sales_payment(uuid)','362e4266718275af5af6efcded3c85cd7a7a7f1faba7241979114fe6e57ffd6c',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','845b9868bb0b0e25443c4e75c77cfcf815e34c4fac78b8bd38038b0476e2944a',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','c77df75873558f96425b8e6b9591903259e5d985a9bd534ab96466799610e507',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','48d60613970b015d1afb30a2f8a7cec0e5d56d1f692c6a1acfa0ffd48684fda1',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),
        'UTF8'),'sha256'),'hex') is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity))
            is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'Y_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  select * into c from erp.cp6_v2620x_rollback_capsule
    where object_regidentity='erp.require_internal()';
  if c.object_regidentity is null
     or c.definition_sha256 is distinct from 'da4bc536f6a9b4f882c6985ee981bd4f1ea63cf3575390389d8798e3654fa91f'
     or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
          is distinct from 'da4bc536f6a9b4f882c6985ee981bd4f1ea63cf3575390389d8798e3654fa91f'
     or c.installed_definition_sha256 is distinct from '5dffcd53c0a5de609ae41482ca246d2afc806b9d92241253d680cf5c7fe1612e'
     or c.owner_snapshot is distinct from 'postgres'
     or c.acl_snapshot is distinct from array['postgres=X/postgres','service_role=X/postgres']::text[] then
    raise exception 'Y_TRUSTED_X_CAPSULE_MISMATCH';
  end if;
  if exists(select 1 from erp.journal_entries j
    join erp.opening_subledger_settlements h on h.id=j.source_id
    where j.source_type='OPENING_SUBLEDGER_SETTLEMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)) or exists(select 1 from erp.journal_entries j
    join erp.vendor_payments h on h.id=j.source_id
    where j.source_type='VENDOR_PAYMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.payment_date)) or exists(select 1 from erp.journal_entries j
    join erp.sales_payments h on h.id=j.source_id
    join erp.sales_payment_posting_facts f on f.payment_id=h.id
    where j.source_type='SALES_PAYMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and f.replaces_payment_id is null
      and (j.economic_date is distinct from erp._cp3_business_date(f.payment_date)
        or f.journal_economic_date is distinct from erp._cp3_business_date(f.payment_date))) then
    raise exception 'Y_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620y$;

create table erp.cp6_v2620y_rollback_capsule(
  like erp.cp6_v2620x_rollback_capsule including all
);
alter table erp.cp6_v2620y_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620y_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620y_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,
    pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  array(select a::text from unnest(p.proacl) a order by a::text),
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in('erp.post_opening_subledger_settlement(uuid)'::regprocedure,'erp.post_vendor_payment(uuid)'::regprocedure,'erp.post_sales_payment(uuid)'::regprocedure,'erp.run_v267_financial_truth_checks()'::regprocedure,'erp._v268_financial_report_checks_pre_scope()'::regprocedure,'erp.run_v268_financial_report_checks()'::regprocedure);

do $canonical_cash_v2620y$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.post_opening_subledger_settlement(uuid)'::regprocedure) into d;
  anchor:=$a$s.physical_at::date$a$;
  replacement:=$r$erp._cp3_business_date(s.physical_at)$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'Y_CANONICAL_DATE_ANCHOR: erp.post_opening_subledger_settlement(uuid) operand 0';
  end if;
  execute replace(d,anchor,replacement);
  select pg_get_functiondef('erp.post_vendor_payment(uuid)'::regprocedure) into d;
  anchor:=$a$p.payment_date::date$a$;
  replacement:=$r$erp._cp3_business_date(p.payment_date)$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'Y_CANONICAL_DATE_ANCHOR: erp.post_vendor_payment(uuid) operand 0';
  end if;
  execute replace(d,anchor,replacement);
  select pg_get_functiondef('erp.post_sales_payment(uuid)'::regprocedure) into d;
  anchor:=$a$p.payment_date::date$a$;
  replacement:=$r$erp._cp3_business_date(p.payment_date)$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>2 then
    raise exception 'Y_CANONICAL_DATE_ANCHOR: erp.post_sales_payment(uuid) operand 0';
  end if;
  execute replace(d,anchor,replacement);
  select pg_get_functiondef('erp.post_sales_payment(uuid)'::regprocedure) into d;
  anchor:=$a$>current_date then$a$;
  replacement:=$r$>erp._cp3_business_date(current_timestamp) then$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'Y_CANONICAL_DATE_ANCHOR: erp.post_sales_payment(uuid) operand 1';
  end if;
  execute replace(d,anchor,replacement);
  select pg_get_functiondef('erp.run_v267_financial_truth_checks()'::regprocedure) into d;
  anchor:=$a$  select 'V2620W_SCRAP_BUSINESS_DATE'$a$;
  replacement:=$r$  select 'V2620Y_OPENING_SETTLEMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Opening settlement cash and subledger dates must follow the Jakarta physical event'
  from erp.journal_entries j
    join erp.opening_subledger_settlements h on h.id=j.source_id
    where j.source_type='OPENING_SUBLEDGER_SETTLEMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620Y_VENDOR_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Vendor payment cash and AP dates must follow the Jakarta payment event'
  from erp.journal_entries j
    join erp.vendor_payments h on h.id=j.source_id
    where j.source_type='VENDOR_PAYMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.payment_date)

  union all
  select 'V2620Y_SALES_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Original customer payment cash, AR and immutable fact dates must follow the Jakarta payment event'
  from erp.journal_entries j
    join erp.sales_payments h on h.id=j.source_id
    join erp.sales_payment_posting_facts f on f.payment_id=h.id
    where j.source_type='SALES_PAYMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and f.replaces_payment_id is null
      and (j.economic_date is distinct from erp._cp3_business_date(f.payment_date)
        or f.journal_economic_date is distinct from erp._cp3_business_date(f.payment_date))

  union all
  select 'V2620W_SCRAP_BUSINESS_DATE'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'Y_CANONICAL_DATE_ANCHOR: erp.run_v267_financial_truth_checks() operand 0';
  end if;
  execute replace(d,anchor,replacement);
  select pg_get_functiondef('erp._v268_financial_report_checks_pre_scope()'::regprocedure) into d;
  anchor:=$a$or r.check_name like 'V2620Y_%'$a$;
  replacement:=$r$or r.check_name like 'V2620Y_%' or r.check_name like 'V2620Y_%'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'Y_CANONICAL_DATE_ANCHOR: erp._v268_financial_report_checks_pre_scope() operand 0';
  end if;
  execute replace(d,anchor,replacement);
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure) into d;
  anchor:=$a$p.payment_date::date$a$;
  replacement:=$r$erp._cp3_business_date(p.payment_date)$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'Y_CANONICAL_DATE_ANCHOR: erp.run_v268_financial_report_checks() operand 0';
  end if;
  execute replace(d,anchor,replacement);
end
$canonical_cash_v2620y$;

do $installed_v2620y$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620y_rollback_capsule)<>6 then
    raise exception 'Y_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620y_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp.post_opening_subledger_settlement(uuid)','c56b387a8593b19cd3b92e6dc20ac95459d2aedeb2b616b6fb1e4d812e729393','b709ed64c78b09c113e6e0541eb757b5367dfbf7dd51752a26827207fc12e97e',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_vendor_payment(uuid)','05b067af75c8691c4e012ff719f8793dbe597ee5f0e451db665d4baab1427316','cf8c1105cb6426583464d7516eb70693c28d668702ae3eb23c22f4029f07f763',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_sales_payment(uuid)','362e4266718275af5af6efcded3c85cd7a7a7f1faba7241979114fe6e57ffd6c','605db7b1ce7bea6b54e70625092f8e98365d3966dc09d220be7dff81014a1f1d',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','845b9868bb0b0e25443c4e75c77cfcf815e34c4fac78b8bd38038b0476e2944a','7ead45b0a09258adcf1b9a9dae44b5627c2ba6fec36767f513706d282f076a9c',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','c77df75873558f96425b8e6b9591903259e5d985a9bd534ab96466799610e507','f95aeb7875cd2a7de603ad33c86cff7c7b0849b7d7f401e9280962b4733c7d45',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','48d60613970b015d1afb30a2f8a7cec0e5d56d1f692c6a1acfa0ffd48684fda1','416b8c53665c4c2b814d4621935a9291797fdbf49067deb0a910d16dc90685fd',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620y_rollback_capsule
      where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'Y_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.run_v267_financial_truth_checks()
      where check_name like 'V2620Y_%' and issue_count>0) then
    raise exception 'Y_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED';
  end if;
  if (select count(*) from erp.run_v268_financial_report_checks()
      where check_name in('V2620Y_OPENING_SETTLEMENT_BUSINESS_DATE',
        'V2620Y_VENDOR_PAYMENT_BUSINESS_DATE','V2620Y_SALES_PAYMENT_BUSINESS_DATE')
        and severity='CRITICAL' and issue_count=0)<>3 then
    raise exception 'Y_FINANCIAL_REPORT_SCOPE_NOT_CONNECTED';
  end if;
end
$installed_v2620y$;

do $boundary_v2620y$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620y_rollback_capsule') order by c.relname loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>210 then
    raise exception 'Y_FULL_ERP_BOUNDARY_CARDINALITY expected210 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620y_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620y$;

insert into erp.schema_migrations(version,description)
values('v2.6.20y','Canonical Jakarta cash dates for opening settlement, vendor and sales payment; immutable facts and linked replacement conservation preserved');
commit;
