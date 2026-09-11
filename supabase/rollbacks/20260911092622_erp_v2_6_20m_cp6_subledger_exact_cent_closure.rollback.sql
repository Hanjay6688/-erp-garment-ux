-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20m -> exact L.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py. The
-- controller verifies independently pinned source/capsule/function trust roots,
-- closes database admission, and drains old invocations before these bytes run.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';
set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;

do $platform_guard_v2620m$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20m_cp6_subledger_exact_cent_closure')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
      where name='erp_v2_6_20m_cp6_subledger_exact_cent_closure'
        and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
          in('c5404de584a4734fb235f5253f10fb10a1d13f01f3f993b99150a422008e2268',
             'b1e5014c656fc654ff9e1d79736420adacf062a67a26716951293a2dabb3451f')) then
    raise exception 'v2.6.20m rollback refused: exact platform ledger identity is ambiguous';
  end if;
end
$platform_guard_v2620m$;

lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.audit_logs,
  erp.journal_lines,
  erp.account_daily_balances,
  erp.sales_headers,
  erp.sales_items,
  erp.sale_stock_allocations,
  erp.sales_returns,
  erp.sales_return_items,
  erp.sales_payments,
  erp.fg_lots,
  erp.fg_stock_movements,
  erp.fg_inventory_balances,
  erp.hpp_versions,
  erp.product_conversions,
  erp.product_conversion_allocations,
  erp.laundry_deliveries,
  erp.laundry_delivery_lines,
  erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,
  erp.wip_stage_events,
  erp.cp6_v2620g_rollback_capsule,
  erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,
  erp.sales_payment_posting_facts,
  erp.sales_payment_reversal_facts,
  erp.cp6_v2620j_rollback_capsule,
  erp.cp6_v2620k_rollback_capsule,
  erp.accounting_period_control,
  erp.accounting_account_mappings,
  erp.cash_accounts,
  erp.chart_accounts,
  erp.laundry_claims,
  erp.laundry_vendors,
  erp.cp6_v2620l_rollback_capsule,
  erp.opening_balance_headers,
  erp.opening_balance_items,
  erp.opening_subledger_balances,
  erp.opening_subledger_settlements,
  erp.opening_financial_corrections,
  erp.supplier_payments,
  erp.material_purchase_headers,
  erp.material_purchase_items,
  erp.material_supplier_invoices,
  erp.material_supplier_invoice_lines,
  erp.material_supplier_returns,
  erp.material_supplier_return_items,
  erp.material_purchase_cost_corrections,
  erp.material_purchase_cost_correction_items,
  erp.material_stock_movements,
  erp.material_rolls,
  erp.cost_recalc_queue,
  erp.cost_adjustments,
  erp.suppliers,
  erp.materials
in share row exclusive mode;
lock table erp.cp6_v2620m_rollback_capsule in access exclusive mode;

do $guard_restore_v2620m$
declare
  c record;
  r record;
  v_table text;
  v_hash text;
  v_expected jsonb;
  v_platform text;
  v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20m')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20l')
     or (select count(*) from erp.cp6_v2620m_rollback_capsule)<>15 then
    raise exception 'v2.6.20m rollback refused: required application markers/capsule absent';
  end if;
  select version into strict v_platform from supabase_migrations.schema_migrations
  where name='erp_v2_6_20m_cp6_subledger_exact_cent_closure';
  if exists(select 1 from supabase_migrations.schema_migrations where version>v_platform)
     or exists(select 1 from erp.schema_migrations where version<>'v2.6.20m'
       and installed_at>(select installed_at from erp.schema_migrations where version='v2.6.20m')) then
    raise exception 'v2.6.20m rollback refused: successor installed';
  end if;

  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108','98fac1a865982d5c60fc5e6a5caae9033755ff915b7e53d22213c0d1d1765ca1',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_purchase_cost_correction(uuid)','d80d5d357acddd562412ada1a27fced5ac979c0ab1aa1dc0a9cbefa81aee0ad8','9542acde669945e633d5929cb5b441a2119b8f3bf9a69919ae46725d598e8ba9',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_material_supplier_invoice(uuid)','ec73a81f2bae980039edde861f01157337814a3bb9a0554f9d0275716c1f19d5','65ae76bce50952c2ced64ad7ec25c1039a1e3086048e5ea39eae71ec4c8b7d69',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_supplier_return(uuid)','562140bee0171cb892501ca4499e93e8b6d661772d1d03c95271283e6cea8714','f5f6603b258eeda0b34a10f06a301b94c488525dfddfe0863e5ded8f56244ad1',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_opening_financial_correction(uuid,numeric,text,date)','41ef3e9b7e9be5432cd09db2e4cba4d303c6c7205c2dcf92cb052293dc4062a7','95ad1f5db523bdc19d7b21d1f1b9e1baa49a499fb791f937fe43b0291d4bd7f1',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_opening_subledger_settlement(uuid)','95eb1e84cd0dabd02b3f11dc8745f72997b56fea47c04a9f56a9e18e9a9ebdf2','c56b387a8593b19cd3b92e6dc20ac95459d2aedeb2b616b6fb1e4d812e729393',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_supplier_payment(uuid)','3d77b3cc0339606aa7eb456b9b341af33f8251a7a0415229a2d7c08cfe54ef60','231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_purchase_cost_correction(uuid,text)','2cbfb722a7b644d47886e23555ef8dcffb2ea2060525c6251afa43e52689389b','dc17e41110f001f6f16d18d065745dc8e85bb9e58ef28e162522976da45c4a6f',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.reverse_material_supplier_invoice(uuid,text)','c269a2cb171184f49be2720e195bd24292f76d0127cb752ffc158a894768d1cb','76ee31ad50c747b5a9f5730a5a3e81ba79c1685f57f716ac211197f11aa7080e',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_supplier_return(uuid,text)','570bb23aeebdf5f309e34a84071a247ff201855b6c283f8a6264b7389816eaa6','ac2504b1f04d5eaf8bf63b13ce945adf17fda0104ac6e4f6c44ac831c255706b',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_opening_financial_correction(uuid,text)','5d794a5d6d4d63b2bc5e4b6407523488d1b87ba5c47ab557056fd566442ec50c','1ce99785ee8dc682b1b0f2aa9171f2110614baf4c9a99ecf4880b547496947fe',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.reverse_opening_subledger_settlement(uuid,text)','d5c1e4b368a13de3738d458c89584ec181149f6f070cc697111c61e56bfba07e','c01292aebb98ea09d0fb440215f9c4cdbd9ece3b98caa641b9b308faec542e1a',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.reverse_supplier_payment(uuid,text)','b6518df0cc3941554eca06016e483e8e020112778db67dad69202d4c032d40be','9733b0e39d82732fb4b2ec7be17c66bcff2a088a81cccd25892eb440d4923102',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','368c7f97b895ce7d08aa6b5fa5a77b50957191465a44e26ef9268b6424c93aea','efde954275e89f01793f405e2b000c6c599bae0be731869802f288994dd154fa',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','2bffd2d8f33ad2d918d1fb2f767676dc403ac777ad9a8ff69d4f32bf74067eff','48d60613970b015d1afb30a2f8a7cec0e5d56d1f692c6a1acfa0ffd48684fda1',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select j.*,
      encode(extensions.digest(convert_to(j.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from erp.cp6_v2620m_rollback_capsule j
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
      raise exception 'TRUSTED_PREDECESSOR_PIN_MISMATCH: v2.6.20m %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected
  from erp.cp6_v2620m_rollback_capsule limit 1;
  if v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>58
     or exists(select 1 from erp.cp6_v2620m_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20m incomplete business boundary';
  end if;
  foreach v_table in array array[
    'app_users','idempotency_requests','products','audit_logs',
    'journal_entries','journal_lines','account_daily_balances','sales_headers',
    'sales_items','sale_stock_allocations','sales_returns','sales_return_items',
    'sales_payments','fg_lots','fg_stock_movements','fg_inventory_balances',
    'hpp_versions','product_conversions','product_conversion_allocations','laundry_deliveries',
    'laundry_delivery_lines','laundry_receipts','laundry_failed_wash_attempts','wip_stage_events',
    'cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule','cp6_v2620i_rollback_capsule','sales_payment_posting_facts',
    'sales_payment_reversal_facts','cp6_v2620j_rollback_capsule','cp6_v2620k_rollback_capsule','accounting_period_control',
    'accounting_account_mappings','cash_accounts','chart_accounts','laundry_claims',
    'laundry_vendors','cp6_v2620l_rollback_capsule','opening_balance_headers','opening_balance_items',
    'opening_subledger_balances','opening_subledger_settlements','opening_financial_corrections','supplier_payments',
    'material_purchase_headers','material_purchase_items','material_supplier_invoices','material_supplier_invoice_lines',
    'material_supplier_returns','material_supplier_return_items','material_purchase_cost_corrections','material_purchase_cost_correction_items',
    'material_stock_movements','material_rolls','cost_recalc_queue','cost_adjustments',
    'suppliers','materials'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'v2.6.20m rollback refused: post-install business history exists (%)',v_table;
    end if;
  end loop;

  for c in select * from erp.cp6_v2620m_rollback_capsule order by object_regidentity
  loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108'),
    ('erp.post_material_purchase_cost_correction(uuid)','d80d5d357acddd562412ada1a27fced5ac979c0ab1aa1dc0a9cbefa81aee0ad8'),
    ('erp.post_material_supplier_invoice(uuid)','ec73a81f2bae980039edde861f01157337814a3bb9a0554f9d0275716c1f19d5'),
    ('erp.post_material_supplier_return(uuid)','562140bee0171cb892501ca4499e93e8b6d661772d1d03c95271283e6cea8714'),
    ('erp.post_opening_financial_correction(uuid,numeric,text,date)','41ef3e9b7e9be5432cd09db2e4cba4d303c6c7205c2dcf92cb052293dc4062a7'),
    ('erp.post_opening_subledger_settlement(uuid)','95eb1e84cd0dabd02b3f11dc8745f72997b56fea47c04a9f56a9e18e9a9ebdf2'),
    ('erp.post_supplier_payment(uuid)','3d77b3cc0339606aa7eb456b9b341af33f8251a7a0415229a2d7c08cfe54ef60'),
    ('erp.reverse_material_purchase_cost_correction(uuid,text)','2cbfb722a7b644d47886e23555ef8dcffb2ea2060525c6251afa43e52689389b'),
    ('erp.reverse_material_supplier_invoice(uuid,text)','c269a2cb171184f49be2720e195bd24292f76d0127cb752ffc158a894768d1cb'),
    ('erp.reverse_material_supplier_return(uuid,text)','570bb23aeebdf5f309e34a84071a247ff201855b6c283f8a6264b7389816eaa6'),
    ('erp.reverse_opening_financial_correction(uuid,text)','5d794a5d6d4d63b2bc5e4b6407523488d1b87ba5c47ab557056fd566442ec50c'),
    ('erp.reverse_opening_subledger_settlement(uuid,text)','d5c1e4b368a13de3738d458c89584ec181149f6f070cc697111c61e56bfba07e'),
    ('erp.reverse_supplier_payment(uuid,text)','b6518df0cc3941554eca06016e483e8e020112778db67dad69202d4c032d40be'),
    ('erp.run_v267_financial_truth_checks()','368c7f97b895ce7d08aa6b5fa5a77b50957191465a44e26ef9268b6424c93aea'),
    ('erp.run_v268_financial_report_checks()','2bffd2d8f33ad2d918d1fb2f767676dc403ac777ad9a8ff69d4f32bf74067eff')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'v2.6.20m rollback restore hash mismatch for %: %',r.identity,v_actual;
    end if;
  end loop;
end
$guard_restore_v2620m$;

drop table erp.cp6_v2620m_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20m';
delete from supabase_migrations.schema_migrations
where name='erp_v2_6_20m_cp6_subledger_exact_cent_closure'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('c5404de584a4734fb235f5253f10fb10a1d13f01f3f993b99150a422008e2268',
       'b1e5014c656fc654ff9e1d79736420adacf062a67a26716951293a2dabb3451f');

do $postcheck_v2620m$
declare r record; v_actual text;
begin
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108'),
    ('erp.post_material_purchase_cost_correction(uuid)','d80d5d357acddd562412ada1a27fced5ac979c0ab1aa1dc0a9cbefa81aee0ad8'),
    ('erp.post_material_supplier_invoice(uuid)','ec73a81f2bae980039edde861f01157337814a3bb9a0554f9d0275716c1f19d5'),
    ('erp.post_material_supplier_return(uuid)','562140bee0171cb892501ca4499e93e8b6d661772d1d03c95271283e6cea8714'),
    ('erp.post_opening_financial_correction(uuid,numeric,text,date)','41ef3e9b7e9be5432cd09db2e4cba4d303c6c7205c2dcf92cb052293dc4062a7'),
    ('erp.post_opening_subledger_settlement(uuid)','95eb1e84cd0dabd02b3f11dc8745f72997b56fea47c04a9f56a9e18e9a9ebdf2'),
    ('erp.post_supplier_payment(uuid)','3d77b3cc0339606aa7eb456b9b341af33f8251a7a0415229a2d7c08cfe54ef60'),
    ('erp.reverse_material_purchase_cost_correction(uuid,text)','2cbfb722a7b644d47886e23555ef8dcffb2ea2060525c6251afa43e52689389b'),
    ('erp.reverse_material_supplier_invoice(uuid,text)','c269a2cb171184f49be2720e195bd24292f76d0127cb752ffc158a894768d1cb'),
    ('erp.reverse_material_supplier_return(uuid,text)','570bb23aeebdf5f309e34a84071a247ff201855b6c283f8a6264b7389816eaa6'),
    ('erp.reverse_opening_financial_correction(uuid,text)','5d794a5d6d4d63b2bc5e4b6407523488d1b87ba5c47ab557056fd566442ec50c'),
    ('erp.reverse_opening_subledger_settlement(uuid,text)','d5c1e4b368a13de3738d458c89584ec181149f6f070cc697111c61e56bfba07e'),
    ('erp.reverse_supplier_payment(uuid,text)','b6518df0cc3941554eca06016e483e8e020112778db67dad69202d4c032d40be'),
    ('erp.run_v267_financial_truth_checks()','368c7f97b895ce7d08aa6b5fa5a77b50957191465a44e26ef9268b6424c93aea'),
    ('erp.run_v268_financial_report_checks()','2bffd2d8f33ad2d918d1fb2f767676dc403ac777ad9a8ff69d4f32bf74067eff')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'v2.6.20m rollback postcondition function mismatch for %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20m')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20m_cp6_subledger_exact_cent_closure')
     or to_regclass('erp.cp6_v2620m_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20l')
     or to_regclass('erp.cp6_v2620l_rollback_capsule') is null
     or to_regclass('erp.sales_payment_posting_facts') is null
     or to_regclass('erp.sales_payment_reversal_facts') is null then
    raise exception 'v2.6.20m rollback postcondition failed';
  end if;
end
$postcheck_v2620m$;
commit;
