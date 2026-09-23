-- CP6 AD: one canonical material-opening clock and its owner-report detector.
-- Qualified AC native counterexamples: run 34963873816; no posted history rewrite.
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

do $lock_all_erp_v2620ad$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620ad_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620ad$;


do $predecessor_v2620ad$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20ac')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20ad')
     or to_regclass('erp.cp6_v2620ad_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ac_rollback_capsule') is null
     or to_regclass('erp.cp6_v2620ac_relation_rollback_capsule') is null then
    raise exception 'AD_REQUIRES_EXACT_AC_WITHOUT_AD_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ac_cp6_temporal_surface_closure')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260915031500' and name='erp_v2_6_20ac_cp6_temporal_surface_closure'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
             ='871fb32b1d4a1e7f9aedfef684b0f2c766092732c38552620eb394061f6240d1')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260915031500')
     or (select count(*) from erp.cp6_v2620ac_rollback_capsule)<>115
     or (select count(*) from erp.cp6_v2620ac_relation_rollback_capsule)<>157 then
    raise exception 'AD_REQUIRES_EXACT_AC_PLATFORM_CAPSULES';
  end if;
  for r in select * from(values
    ('erp.post_opening_balance(uuid)','d73391c79e725c14aab7370cf5f5dfc0bd2134a02480e5693c37dc9c25bf5829',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','416b8c53665c4c2b814d4621935a9291797fdbf49067deb0a910d16dc90685fd',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'AD_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if (select count(*)::bigint
    from erp.opening_balance_items i
    join erp.opening_balance_headers h on h.id=i.opening_id
    where h.status='POSTED' and i.balance_type='MATERIAL' and (
      (select count(*) from erp.material_stock_movements m
       where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id)<>1
      or not exists(select 1 from erp.material_stock_movements m
        where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id
          and m.movement_type='OPENING' and m.material_id=i.material_id
          and m.location_id=i.location_id and m.roll_id is not distinct from i.roll_id
          and m.physical_at=(h.opening_date::timestamp at time zone 'Asia/Jakarta'))
    ))<>0 then
    raise exception 'AD_PREEXISTING_OPENING_TIMELINE_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620ad$;

create table erp.cp6_v2620ad_rollback_capsule(
  like erp.cp6_v2620ab_rollback_capsule including all
);
alter table erp.cp6_v2620ad_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ad_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ad_rollback_capsule(
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
where p.oid in('erp.post_opening_balance(uuid)'::regprocedure,'erp.run_v268_financial_report_checks()'::regprocedure);


do $canonical_opening_v2620ad$
declare d text;anchor text:='h.opening_date::timestamptz';
begin
  select pg_get_functiondef('erp.post_opening_balance(uuid)'::regprocedure) into d;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'AD_OPENING_ANCHOR';end if;
  execute replace(d,anchor,'(h.opening_date::timestamp at time zone ''Asia/Jakarta'')');
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure) into d;
  anchor:=E'\nend\n$function$';
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'AD_REPORT_ANCHOR';end if;
  execute replace(d,anchor,$replacement$
  return query
  select 'V2620AD_OPENING_MATERIAL_TIMELINE_MISMATCH'::text,'CRITICAL'::text,
    (select count(*)::bigint
    from erp.opening_balance_items i
    join erp.opening_balance_headers h on h.id=i.opening_id
    where h.status='POSTED' and i.balance_type='MATERIAL' and (
      (select count(*) from erp.material_stock_movements m
       where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id)<>1
      or not exists(select 1 from erp.material_stock_movements m
        where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id
          and m.movement_type='OPENING' and m.material_id=i.material_id
          and m.location_id=i.location_id and m.roll_id is not distinct from i.roll_id
          and m.physical_at=(h.opening_date::timestamp at time zone 'Asia/Jakarta'))
    )),
    'Every posted material opening line must own one movement at the start of its Jakarta document date'::text;

end
$function$$replacement$);
end
$canonical_opening_v2620ad$;

do $installed_v2620ad$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620ad_rollback_capsule)<>2 then
    raise exception 'AD_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620ad_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp.post_opening_balance(uuid)','d73391c79e725c14aab7370cf5f5dfc0bd2134a02480e5693c37dc9c25bf5829','cc89ac9e978723c70728cc183104490109bf2530ce8dd1a99b314018a5b0f6eb',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','416b8c53665c4c2b814d4621935a9291797fdbf49067deb0a910d16dc90685fd','6a93242cb0325baee511c2753eb65588600fe8b9a7fc62d423b85f14bf9c71d5',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620ad_rollback_capsule
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
      raise exception 'AD_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;

end
$installed_v2620ad$;

do $boundary_v2620ad$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620ad_rollback_capsule') order by c.relname loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>216 then
    raise exception 'AD_FULL_ERP_BOUNDARY_CARDINALITY expected216 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620ad_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620ad$;

insert into erp.schema_migrations(version,description)
values('v2.6.20ad','Canonical Jakarta material opening for direct and imported stock; report detects source timeline drift; posted history remains immutable');
commit;
