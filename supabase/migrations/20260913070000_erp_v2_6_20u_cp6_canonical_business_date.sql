-- CP6 U: canonical Jakarta business dates for material accounting and owner reports.
-- Forward-only successor; all published migrations and rollbacks through T stay immutable.
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
  erp.cp6_v2620t_rollback_capsule
in share row exclusive mode;

do $predecessor_v2620u$
declare r record;c record;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20t')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20u')
     or to_regclass('erp.cp6_v2620u_rollback_capsule') is not null then
    raise exception 'U_REQUIRES_EXACT_T_WITHOUT_U_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20t_cp6_material_adjustment_revaluation')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260912171034'
         and name='erp_v2_6_20t_cp6_material_adjustment_revaluation'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('e888fa66bd40abda0ba1152662df9d0855193325dcf1c8491d47b522cdd00add',
              '564538094fb948dded4ff26223595227222166030ac8b8c7c77495245ebe3890'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260912171034')
     or (select count(*) from erp.cp6_v2620t_rollback_capsule)<>6 then
    raise exception 'U_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH';
  end if;
  -- Trust the complete T capsule, not only the two rows U replaces.
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','2eb47603dcfefe58ea89e8f3cf832aca187f397d66b99bd7a4ab3bb5d6c428ad','8e0e303066c23476223089e2705b8ad0861b34faa2efb12c58663677f454b196',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.resolve_accounting_transaction_date(date)','13fa7b70e1b723bb5d0f0f112f19ff9f7f928c587aef75b9ad4737e135b0a769','92e6c30c60bce3406178bd661ca5df2e5d12e17380fad2a8730be0c91d86bf48',array['postgres=X/postgres']::text[]),
    ('erp.reverse_journal(uuid,text)','3ff7dec1176c79b58a981e5fdc68a3ce47908cfd5347cbd192d40022c9d7aee1','a6f635cd2319a68a1afa522fa4682921a6f7b80afd0e31fbdc4271cf53fcfef4',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_adjustment(uuid,text)','38800321130b33af3b127928b724f4e2b7b02342c62087a25536580c1eba8043','c90fd34d4045a060ae4d36413d6520068281066d0de52dc766583c5f6e7d7288',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','e5f4d8749851824e11bb7b76bb3614963aa26feca7034962f47cc198a7962e89','acd6f623c83f1ce74323a11b9224955ea922b10788ed631b9973aa9345698af8',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.sync_material_cost_revaluation(uuid)','57b213f5b7adb8abc78eafd8639cbc1907fd49319027534166a10365cfb69b83','3334800b5888000a4388dda4362ebd0db4c5f0dcdc0bbf3e41acfcf629d720f0',array['postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620t_rollback_capsule
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
            is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'U_TRUSTED_T_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  -- Pin the additional U inputs and T's inherited private helpers/facts.
  for r in select * from(values
    ('erp._cp3_r4_reverse_journal_internal(uuid,text)','9b60fcd88852337ad0956d471e54c1c04bcccd35f5e85a8e5093469cc1c37249',array['postgres=X/postgres']::text[]),
    ('erp.post_material_adjustment(uuid)','be5a163932f0678667d94095f3db519abb7e5df4ea2c4c95204e42620ee27d83',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.get_owner_financial_snapshot_v2(date,date,date)','e51dbe224d112f523e51bddc609ee0f0036ecae2ef5d328b865326781aa8780c',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
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
      raise exception 'U_TRUSTED_T_INPUT_OWNER_ACL_MISMATCH: %',r.identity;
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
    raise exception 'U_INHERITED_T_SECURITY_MISMATCH';
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
  ) then
    raise exception 'U_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620u$;

create table erp.cp6_v2620u_rollback_capsule(
  like erp.cp6_v2620t_rollback_capsule including all
);
alter table erp.cp6_v2620u_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620u_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620u_rollback_capsule(
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
  'erp._cp3_r4_reverse_journal_internal(uuid,text)'::regprocedure,
  'erp.post_material_adjustment(uuid)'::regprocedure,
  'erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure,
  'erp.run_v267_financial_truth_checks()'::regprocedure,
  'erp._v268_financial_report_checks_pre_scope()'::regprocedure
);

do $canonical_material$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp._cp3_r4_reverse_journal_internal(uuid,text)'::regprocedure) into d;
  anchor:='CURRENT_DATE';replacement:='erp._cp3_business_date(current_timestamp)';
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'U_JOURNAL_REVERSAL_DAY_ANCHOR';
  end if;
  execute replace(d,anchor,replacement);

  select pg_get_functiondef('erp.post_material_adjustment(uuid)'::regprocedure) into d;
  anchor:='h.physical_at::date';replacement:='erp._cp3_business_date(h.physical_at)';
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>2 then
    raise exception 'U_MATERIAL_ADJUSTMENT_DAY_ANCHOR';
  end if;
  execute replace(d,anchor,replacement);
end
$canonical_material$;

do $canonical_owner_report$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure) into d;
  anchor:='p_as_of date DEFAULT CURRENT_DATE';
  replacement:='p_as_of date DEFAULT erp._cp3_business_date(current_timestamp)';
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'U_OWNER_DEFAULT_AS_OF_ANCHOR';
  end if;
  d:=replace(d,anchor,replacement);
  anchor:='h.physical_at::date';replacement:='erp._cp3_business_date(h.physical_at)';
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>2 then
    raise exception 'U_OWNER_MATERIAL_CUTOFF_ANCHOR';
  end if;
  d:=replace(d,anchor,replacement);
  anchor:='w.physical_at::date';replacement:='erp._cp3_business_date(w.physical_at)';
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'U_OWNER_WIP_CUTOFF_ANCHOR';
  end if;
  execute replace(d,anchor,replacement);
end
$canonical_owner_report$;

do $detector_v2620u$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.run_v267_financial_truth_checks()'::regprocedure) into d;
  anchor:=$a$  union all
  select 'V2620T_JOURNAL_FUTURE_BUSINESS_DATE'$a$;
  replacement:=$r$  union all
  select 'V2620U_MATERIAL_ADJUSTMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Material adjustment journals must use the canonical Jakarta date of physical_at'
  from erp.journal_entries j
  join erp.material_adjustments h on h.id=j.source_id
  where j.source_type='MATERIAL_ADJUSTMENT' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620U_JOURNAL_REVERSAL_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Generic journal reversals must use the canonical Jakarta date of posting_at'
  from erp.journal_entries j
  where j.source_type='JOURNAL_REVERSAL' and j.status='POSTED'
    and j.economic_date is distinct from erp._cp3_business_date(j.posting_at)

  union all
  select 'V2620T_JOURNAL_FUTURE_BUSINESS_DATE'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'U_CANONICAL_DATE_DETECTOR_ANCHOR';
  end if;
  execute replace(d,anchor,replacement);

  select pg_get_functiondef('erp._v268_financial_report_checks_pre_scope()'::regprocedure) into d;
  anchor:=$a$or r.check_name like 'V2620T_%'$a$;
  replacement:=$r$or r.check_name like 'V2620T_%' or r.check_name like 'V2620U_%'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'U_CANONICAL_DATE_REPORT_SCOPE_ANCHOR';
  end if;
  execute replace(d,anchor,replacement);
end
$detector_v2620u$;

do $installed_v2620u$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620u_rollback_capsule)<>5 then
    raise exception 'U_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620u_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp._cp3_r4_reverse_journal_internal(uuid,text)','9b60fcd88852337ad0956d471e54c1c04bcccd35f5e85a8e5093469cc1c37249','2d54bfdf9bf0912e6b13e558ddbc4cb419020f191c3ce626a26f2c27b814b20c',array['postgres=X/postgres']::text[]),
    ('erp.post_material_adjustment(uuid)','be5a163932f0678667d94095f3db519abb7e5df4ea2c4c95204e42620ee27d83','b32962d12adde0ca4ae659f2dd83a02a0a3111c3a9060d845ed2e82025696201',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.get_owner_financial_snapshot_v2(date,date,date)','e51dbe224d112f523e51bddc609ee0f0036ecae2ef5d328b865326781aa8780c','78210a408d3cf6bf48e3e86200c3a429adacff19a339b11669598accceaaf9cb',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','acd6f623c83f1ce74323a11b9224955ea922b10788ed631b9973aa9345698af8','61819c08662b2a493212035792333006737d2fa158259dc9ce045ca2cf9b55e9',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','8e0e303066c23476223089e2705b8ad0861b34faa2efb12c58663677f454b196','3a8af1f92f85ddbebf697b681e16f42b9c48b2cdb543b6ab2daa2a928a5bc775',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620u_rollback_capsule
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
      raise exception 'U_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.run_v267_financial_truth_checks()
      where check_name like 'V2620U_%' and issue_count>0) then
    raise exception 'U_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED';
  end if;
  if (select count(*) from erp.run_v268_financial_report_checks()
      where check_name in('V2620U_MATERIAL_ADJUSTMENT_BUSINESS_DATE',
        'V2620U_JOURNAL_REVERSAL_BUSINESS_DATE')
        and severity='CRITICAL' and issue_count=0)<>2 then
    raise exception 'U_FINANCIAL_REPORT_SCOPE_NOT_CONNECTED';
  end if;
end
$installed_v2620u$;

do $boundary_v2620u$
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
    'material_adjustment_revaluation_facts','cp6_v2620t_rollback_capsule'
  ]::text[] loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620u_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620u$;

insert into erp.schema_migrations(version,description)
values('v2.6.20u','Canonical Jakarta material accounting, journal reversal and owner-report business dates');
commit;
