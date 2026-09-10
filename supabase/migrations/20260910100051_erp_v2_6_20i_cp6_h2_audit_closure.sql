-- ERP Garment v2.6.20i / independent CP6 H2 audit closure.
-- VENI. VIDI. VICI. ERP. -- I CONQUERED ERP.
-- Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.
--
-- H2-01 is closed by exact per-payment journal lineage, so equal and opposite
-- faults cannot wash between invoices owned by the same customer.
-- H2-02 is closed at install time by source-pinning every H capsule predecessor,
-- installed generation, owner, and ACL. The maintenance executor independently
-- enforces the same trust roots before any reviewed rollback can close admission.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';

lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule
in share row exclusive mode;
lock table erp.audit_logs,erp.journal_lines,erp.account_daily_balances,
  erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,
  erp.sales_returns,erp.sales_return_items,erp.sales_payments,
  erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.product_conversions,erp.product_conversion_allocations,
  erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events
in share row exclusive mode;

do $guard_v2620i$
declare
  r record;
  c record;
  v_platform_count bigint;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20h') then
    raise exception 'ERP v2.6.20i requires exact v2.6.20h first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20i')
     or to_regclass('erp.cp6_v2620i_rollback_capsule') is not null then
    raise exception 'ERP v2.6.20i already recorded or prior repair residue exists; never replay';
  end if;
  select count(*) into v_platform_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20h_cp6_expanded_audit_closure'
    and encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex')
      in('e16dbb655164595be273c03582d35c9ac33593136bd418fdd87156e592f292b8',
         'bcac43cd1cca5214f8678cd058caf6ff19ce90bdebd1c31f47675c0efd79a36f');
  if v_platform_count<>1 then
    raise exception 'ERP v2.6.20i requires one exact H platform-ledger row';
  end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'ERP v2.6.20i refuses an active CP6 execution context';
  end if;
  if (select count(*) from erp.cp6_v2620h_rollback_capsule)<>6 then
    raise exception 'TRUSTED_PREDECESSOR_PIN_MISMATCH: H capsule cardinality';
  end if;

  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()',
      '436a77b32c953e92fc8e43f953335392c4137b61bf632780d26b9b942d94e8b0',
      '4eb19d881f47dbbf57bc69f4f49ffdbb5c3071b4b126d2398d26dd2e980b2bf7',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_sales_payment(uuid)',
      '83214f0812d151b5d03cb8669f48fb5c72b4480d0c609df84d244559f3e4d988',
      '010de4bae594258ba73348463ba90305a01485ed30b9c11918583be198c1f6df',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_sales_return(uuid)',
      '217788d5f72bcfb87a387b82360c0f4a1ac191913beb0cf1a2ec5e31926a09a0',
      'd959c5e095cce32540b9f2a4310857520b4eec70c5200465f16d74cccfb45a46',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_sales_payment(uuid,text)',
      '33219c5509a43470f87d3b0fe4af472bec3f87b4808bbdba7d2eed69ea88354d',
      '09c33e1cfbc673f9118878bd6da55e0df9c433252f0ecb099ef547895cab3ef6',
      array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.reverse_sales_return(uuid,text)',
      '68e4ed3a1940e3853bcdadaf2d607ed60a78a350460efcaf4fa052a90c902bce',
      'e7155962a8aa0f0e72f16644ffdf3563d3a11658b73c5185e94d6023090ec3cb',
      array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()',
      'fd48bcf94868dbcf7087af2c34b12c82333ae861d44c6bf79cbb41b1350a8962',
      '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select h.object_regidentity,h.definition_sha256,
      encode(extensions.digest(convert_to(h.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      h.installed_definition_sha256,h.owner_snapshot,h.acl_snapshot,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c
    from erp.cp6_v2620h_rollback_capsule h
    left join pg_proc p on p.oid=to_regprocedure(h.object_regidentity)
    where h.object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or c.definition_actual is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.installed_actual is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.installed_owner is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or c.installed_acl is distinct from r.acl then
      raise exception 'TRUSTED_PREDECESSOR_PIN_MISMATCH: H capsule/function %',r.identity;
    end if;
  end loop;
end
$guard_v2620i$;

create table erp.cp6_v2620i_rollback_capsule(
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
alter table erp.cp6_v2620i_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620i_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cp6_v2620i_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a order by a::text) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid='erp.run_v268_financial_report_checks()'::regprocedure;

do $capture_boundary_v2620i$
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
    'cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620i_rollback_capsule set boundary_snapshot=v_snapshot;
end
$capture_boundary_v2620i$;

-- Exact payment-to-journal lineage. Aggregate AR checks remain useful, but
-- cannot prove which invoice/payment produced each cash and receivable line.
do $patch_report_v2620i$
declare v_definition text; v_anchor text; v_replacement text; v_actual text;
begin
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure),
    encode(extensions.digest(convert_to(pg_get_functiondef(
      'erp.run_v268_financial_report_checks()'::regprocedure),'UTF8'),'sha256'),'hex')
  into v_definition,v_actual;
  if v_actual<>'3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: I report predecessor (%)',v_actual;
  end if;
  v_anchor:=$anchor$  union all
  select 'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH','CRITICAL',count(*)::bigint,$anchor$;
  v_replacement:=$replacement$  union all
  select 'V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Each customer payment must own exactly one exact cash/AR journal and, when reversed, exactly one exact inverse'
  from(
    select p.id
    from erp.sales_payments p
    join erp.sales_headers h on h.id=p.sale_id
    where
      (p.status='DRAFT' and exists(
        select 1 from erp.journal_entries o
        where o.source_type='SALES_PAYMENT' and o.source_id=p.id
      ))
      or
      (p.status in('POSTED','REVERSED') and(
        (select count(*) from erp.journal_entries o
         where o.source_type='SALES_PAYMENT' and o.source_id=p.id)<>1
        or not exists(
          select 1
          from erp.journal_entries o
          where o.source_type='SALES_PAYMENT' and o.source_id=p.id
            and o.status=case when p.status='POSTED' then 'POSTED' else 'REVERSED' end
            and o.economic_date=p.payment_date::date
            and (select count(*) from erp.journal_lines l where l.journal_entry_id=o.id)=2
            and (select coalesce(sum(l.debit),0) from erp.journal_lines l where l.journal_entry_id=o.id)=p.amount
            and (select coalesce(sum(l.credit),0) from erp.journal_lines l where l.journal_entry_id=o.id)=p.amount
            and (select count(*) from erp.journal_lines l
                 join erp.cash_accounts ca on ca.id=p.cash_account_id and ca.coa_account_id=l.account_id
                 where l.journal_entry_id=o.id and l.debit=p.amount and l.credit=0
                   and l.customer_id=h.customer_id and l.vendor_id is null
                   and l.contractor_id is null and l.po_id is null and l.product_id is null)=1
            and (select count(*) from erp.journal_lines l
                 where l.journal_entry_id=o.id and l.account_id=erp.account_id('AR_CUSTOMER')
                   and l.debit=0 and l.credit=p.amount and l.customer_id=h.customer_id
                   and l.vendor_id is null and l.contractor_id is null
                   and l.po_id is null and l.product_id is null)=1
            and (
              (p.status='POSTED' and not exists(
                select 1 from erp.journal_entries r
                where r.source_type='JOURNAL_REVERSAL'
                  and (r.source_id=o.id or r.reversal_of_id=o.id)
              ))
              or
              (p.status='REVERSED'
                and (select count(*) from erp.journal_entries r
                     where r.source_type='JOURNAL_REVERSAL'
                       and (r.source_id=o.id or r.reversal_of_id=o.id))=1
                and exists(
                  select 1 from erp.journal_entries r
                  where r.source_type='JOURNAL_REVERSAL' and r.source_id=o.id
                    and r.reversal_of_id=o.id and r.status='POSTED'
                    and (select count(*) from erp.journal_lines x where x.journal_entry_id=r.id)=2
                    and not exists(
                      select 1 from erp.journal_lines ol
                      where ol.journal_entry_id=o.id and not exists(
                        select 1 from erp.journal_lines rl
                        where rl.journal_entry_id=r.id
                          and rl.account_id=ol.account_id
                          and rl.debit=ol.credit and rl.credit=ol.debit
                          and rl.customer_id is not distinct from ol.customer_id
                          and rl.vendor_id is not distinct from ol.vendor_id
                          and rl.contractor_id is not distinct from ol.contractor_id
                          and rl.po_id is not distinct from ol.po_id
                          and rl.product_id is not distinct from ol.product_id
                      )
                    )
                    and not exists(
                      select 1 from erp.journal_lines rl
                      where rl.journal_entry_id=r.id and not exists(
                        select 1 from erp.journal_lines ol
                        where ol.journal_entry_id=o.id
                          and ol.account_id=rl.account_id
                          and ol.debit=rl.credit and ol.credit=rl.debit
                          and ol.customer_id is not distinct from rl.customer_id
                          and ol.vendor_id is not distinct from rl.vendor_id
                          and ol.contractor_id is not distinct from rl.contractor_id
                          and ol.po_id is not distinct from rl.po_id
                          and ol.product_id is not distinct from rl.product_id
                      )
                    )
                )
              )
            )
        )
      ))
    union all
    select o.id
    from erp.journal_entries o
    where o.source_type='SALES_PAYMENT'
      and not exists(select 1 from erp.sales_payments p where p.id=o.source_id)
  ) payment_lineage_faults

  union all
  select 'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH','CRITICAL',count(*)::bigint,$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: I report insertion anchor';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_report_v2620i$;

do $installed_guard_v2620i$
declare r record; v_count bigint;
begin
  if (select count(*) from erp.cp6_v2620i_rollback_capsule)<>1 then
    raise exception 'ERP v2.6.20i incomplete rollback capsule';
  end if;
  for r in select c.*,p.proowner,p.proacl
    from erp.cp6_v2620i_rollback_capsule c join pg_proc p on p.oid=to_regprocedure(c.object_regidentity)
  loop
    if r.definition_sha256<>'3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f'
       or pg_get_userbyid(r.proowner) is distinct from r.owner_snapshot
       or (case when r.proacl is null then null else array(select a::text from unnest(r.proacl) a order by a::text) end)
          is distinct from r.acl_snapshot then
      raise exception 'ERP v2.6.20i changed predecessor hash/owner/ACL for %',r.object_regidentity;
    end if;
  end loop;
  select issue_count into v_count from erp.run_v268_financial_report_checks()
  where check_name='V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH';
  if v_count is distinct from 0 then
    raise exception 'ERP v2.6.20i payment lineage reconciliation failed: % issue(s)',v_count;
  end if;
  update erp.cp6_v2620i_rollback_capsule c set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
end
$installed_guard_v2620i$;

insert into erp.schema_migrations(version,description) values(
  'v2.6.20i',
  'CP6 H2 closure: exact per-payment journal lineage and trusted predecessor capsule pins'
);
commit;
