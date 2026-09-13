-- CP6 W: canonical Jakarta business dates and report confidence for paid scrap sales.
-- Forward-only successor; all published migrations and rollbacks through V stay immutable.
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
  erp.cp6_v2620v_rollback_capsule,erp.scrap_batches,erp.scrap_sales
in share row exclusive mode;

do $predecessor_v2620w$
declare r record;c record;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20v')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20w')
     or to_regclass('erp.cp6_v2620w_rollback_capsule') is not null then
    raise exception 'W_REQUIRES_EXACT_V_WITHOUT_W_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20v_cp6_misc_finance_business_date')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260913135850'
         and name='erp_v2_6_20v_cp6_misc_finance_business_date'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('3bd29c1280e09bd8d36e8303c4e5e4cfdd2be951c3f852c8ce38fe170ab3648d',
              'c4955d4f0ae541b532e1aedef0c22f84f152bd8ca0eb1ba3dc0f644b70bce594'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260913135850')
     or (select count(*) from erp.cp6_v2620v_rollback_capsule)<>3 then
    raise exception 'W_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH';
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
            is distinct from case r.identity
              when 'erp.run_v267_financial_truth_checks()' then '13e1c0b7e3a9262aecd18504cb70890eeaeb61190c12e2cc7bb16f2e2d9ddfb2'
              when 'erp._v268_financial_report_checks_pre_scope()' then 'bdce68bf47700519d663e63302b5d48a720959d1c9995fcb9d8599a9516c2eef'
              else r.installed_sha256 end
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'W_TRUSTED_U_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
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
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'W_TRUSTED_V_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  -- Pin the newly corrected scrap entry point and inherited private helpers/facts.
  for r in select * from(values
    ('erp.post_scrap_sale(uuid)','53e2b8c582b342b2b4391a3fdcf91308c0e0e0f08e021c9f800b99212f64d39c',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
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
      raise exception 'W_TRUSTED_U_INPUT_OWNER_ACL_MISMATCH: %',r.identity;
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
    raise exception 'W_INHERITED_T_SECURITY_MISMATCH';
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
    raise exception 'W_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620w$;

create table erp.cp6_v2620w_rollback_capsule(
  like erp.cp6_v2620v_rollback_capsule including all
);
alter table erp.cp6_v2620w_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620w_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620w_rollback_capsule(
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
where p.oid in(
  'erp.post_scrap_sale(uuid)'::regprocedure,
  'erp.run_v267_financial_truth_checks()'::regprocedure,
  'erp._v268_financial_report_checks_pre_scope()'::regprocedure
);

do $canonical_scrap_v2620w$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.post_scrap_sale(uuid)'::regprocedure) into d;
  anchor:='s.physical_at::date';replacement:='erp._cp3_business_date(s.physical_at)';
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'W_SCRAP_DAY_ANCHOR';
  end if;
  execute replace(d,anchor,replacement);

  select pg_get_functiondef('erp.run_v267_financial_truth_checks()'::regprocedure) into d;
  anchor:=$a$  union all
  select 'V2620V_MISC_FINANCE_BUSINESS_DATE'$a$;
  replacement:=$r$  union all
  select 'V2620W_SCRAP_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Paid scrap economic dates must match the canonical Jakarta physical business date'
  from erp.journal_entries j
  join erp.scrap_sales h on h.id=j.source_id
  where j.source_type='SCRAP_SALE' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620V_MISC_FINANCE_BUSINESS_DATE'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'W_CANONICAL_DATE_DETECTOR_ANCHOR';
  end if;
  execute replace(d,anchor,replacement);

  select pg_get_functiondef('erp._v268_financial_report_checks_pre_scope()'::regprocedure) into d;
  anchor:=$a$or r.check_name like 'V2620V_%'$a$;
  replacement:=$r$or r.check_name like 'V2620V_%' or r.check_name like 'V2620W_%'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'W_CANONICAL_DATE_REPORT_SCOPE_ANCHOR';
  end if;
  execute replace(d,anchor,replacement);
end
$canonical_scrap_v2620w$;

do $installed_v2620w$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620w_rollback_capsule)<>3 then
    raise exception 'W_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620w_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
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
      raise exception 'W_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.run_v267_financial_truth_checks()
      where check_name like 'V2620W_%' and issue_count>0) then
    raise exception 'W_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED';
  end if;
  if (select count(*) from erp.run_v268_financial_report_checks()
      where check_name='V2620W_SCRAP_BUSINESS_DATE'
        and severity='CRITICAL' and issue_count=0)<>1 then
    raise exception 'W_FINANCIAL_REPORT_SCOPE_NOT_CONNECTED';
  end if;
end
$installed_v2620w$;

do $boundary_v2620w$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  foreach v_table in array array[
    'app_users','idempotency_requests','products','audit_logs','journal_entries',
    'journal_lines','account_daily_balances','sales_headers','sales_items',
    'sale_stock_allocations','sales_returns','sales_return_items','sales_payments',
    'fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions',
    'product_conversions','product_conversion_allocations','laundry_deliveries',
    'laundry_delivery_lines','laundry_receipts','laundry_failed_wash_attempts',
    'wip_stage_events','cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule',
    'cp6_v2620i_rollback_capsule','sales_payment_posting_facts',
    'sales_payment_reversal_facts','cp6_v2620j_rollback_capsule',
    'cp6_v2620k_rollback_capsule','accounting_period_control',
    'accounting_account_mappings','cash_accounts','chart_accounts','laundry_claims',
    'laundry_vendors','cp6_v2620l_rollback_capsule','opening_balance_headers',
    'opening_balance_items','opening_subledger_balances','opening_subledger_settlements',
    'opening_financial_corrections','supplier_payments','material_purchase_headers',
    'material_purchase_items','material_supplier_invoices',
    'material_supplier_invoice_lines','material_supplier_returns',
    'material_supplier_return_items','material_purchase_cost_corrections',
    'material_purchase_cost_correction_items','material_stock_movements','material_rolls',
    'cost_recalc_queue','cost_adjustments','suppliers','materials',
    'cp6_v2620m_rollback_capsule','supplier_cent_posting_facts','material_cost_history',
    'material_cost_revaluation_state','material_cost_revaluation_events',
    'material_cost_checkpoints','cp6_v2620n_rollback_capsule',
    'cp6_v2620o_rollback_capsule','cp6_v2620p_rollback_capsule',
    'cp6_v2620q_rollback_capsule','cp6_v2620r_rollback_capsule',
    'cp6_v2620s_rollback_capsule','material_adjustments','material_adjustment_items',
    'material_adjustment_revaluation_facts','cp6_v2620t_rollback_capsule',
    'cp6_v2620u_rollback_capsule','misc_finance_transactions','misc_finance_categories',
    'cp6_v2620v_rollback_capsule','scrap_batches','scrap_sales'
  ]::text[] loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620w_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620w$;

insert into erp.schema_migrations(version,description)
values('v2.6.20w','Canonical Jakarta paid scrap dates with financial report propagation');
commit;
