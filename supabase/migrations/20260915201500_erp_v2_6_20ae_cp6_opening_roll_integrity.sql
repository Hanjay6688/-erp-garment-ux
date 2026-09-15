-- CP6 AE: one physical roll can enter opening stock once and never above its original quantity.
-- Qualified AD comparison run 35016787895; no posted history rewrite.
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

do $lock_all_erp_v2620ae$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620ae_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620ae$;


do $predecessor_v2620ae$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20ad')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20ae')
     or to_regclass('erp.cp6_v2620ae_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ad_rollback_capsule') is null then
    raise exception 'AE_REQUIRES_EXACT_AD_WITHOUT_AE_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
        where name='erp_v2_6_20ad_cp6_opening_material_business_day')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260915113627'
         and name='erp_v2_6_20ad_cp6_opening_material_business_day'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
             ='cd4879eb9b053e3b7a975e1430f481131e377f260ece2f19f07bfb4c98498c1d')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260915113627')
     or (select count(*) from erp.cp6_v2620ad_rollback_capsule)<>2 then
    raise exception 'AE_REQUIRES_EXACT_AD_PLATFORM_CAPSULE';
  end if;
  for r in select * from(values
    ('erp.post_opening_balance(uuid)','cc89ac9e978723c70728cc183104490109bf2530ce8dd1a99b314018a5b0f6eb',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','6a93242cb0325baee511c2753eb65588600fe8b9a7fc62d423b85f14bf9c71d5',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'AE_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if (select count(*)::bigint
    from erp.opening_balance_items i
    join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
    left join erp.materials material on material.id=i.material_id
    left join erp.material_rolls roll on roll.id=i.roll_id
    where (i.roll_id is not null and i.balance_type<>'MATERIAL')
      or (i.balance_type='MATERIAL' and (
      (material.material_type='FABRIC' and i.roll_id is null)
      or (i.roll_id is not null and (
        material.material_type is distinct from 'FABRIC'
        or
        roll.material_id is distinct from i.material_id
        or roll.purchase_item_id is not null
        or i.qty>roll.original_qty
        or (select count(*) from erp.opening_balance_items other_i
            join erp.opening_balance_headers other_h on other_h.id=other_i.opening_id
            where other_h.status='POSTED' and other_i.balance_type='MATERIAL'
              and other_i.roll_id=i.roll_id)<>1
        or (select count(*) from erp.material_stock_movements opening_m
            where opening_m.roll_id=i.roll_id and opening_m.movement_type='OPENING'
              and opening_m.reversal_of_id is null)<>1
        or exists(select 1 from erp.material_stock_movements purchase_m
            where purchase_m.roll_id=i.roll_id and purchase_m.movement_type='PURCHASE'
              and purchase_m.reversal_of_id is null)
      ))
    )))<>0 then
    raise exception 'AE_PREEXISTING_OPENING_ROLL_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620ae$;

create table erp.cp6_v2620ae_rollback_capsule(
  like erp.cp6_v2620ad_rollback_capsule including all
);
alter table erp.cp6_v2620ae_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ae_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ae_rollback_capsule(
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


do $canonical_opening_v2620ae$
declare d text;anchor text;
begin
  select pg_get_functiondef('erp.post_opening_balance(uuid)'::regprocedure) into d;
  anchor:=$anchor$  if not exists(select 1 from erp.opening_balance_items where opening_id=h.id) then raise exception 'Opening balance has no lines'; end if;
  select count(*),(array_agg(id order by id))[1] into v_fg_count,v_default_fg_location from erp.locations where location_type='FG_WAREHOUSE' and is_active=true;$anchor$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'AE_OPENING_GUARD_ANCHOR';
  end if;
  execute replace(d,anchor,$replacement$  if not exists(select 1 from erp.opening_balance_items where opening_id=h.id) then raise exception 'Opening balance has no lines'; end if;

  perform i.id from erp.opening_balance_items i
  where i.opening_id=h.id order by i.id for update;
  if exists(
    select 1 from erp.opening_balance_items i
    where i.opening_id=h.id and i.roll_id is not null
      and i.balance_type<>'MATERIAL'
  ) then
    raise exception 'AE_OPENING_ROLL_ONLY_ALLOWED_FOR_MATERIAL';
  end if;
  if exists(
    select 1 from erp.opening_balance_items i
    where i.opening_id=h.id and i.balance_type='MATERIAL'
      and i.roll_id is not null
    group by i.roll_id having count(*)>1
  ) then
    raise exception 'AE_OPENING_ROLL_DUPLICATE_IN_DOCUMENT';
  end if;
  perform mr.id from erp.material_rolls mr
  where mr.id in(
    select i.roll_id from erp.opening_balance_items i
    where i.opening_id=h.id and i.roll_id is not null
  ) order by mr.id for update;
  for r in
    select i.*,m.material_type,
      mr.material_id as roll_material_id,
      mr.original_qty as roll_original_qty,
      mr.cached_qty as roll_cached_qty,
      mr.purchase_item_id as roll_purchase_item_id,
      mr.status as roll_status
    from erp.opening_balance_items i
    left join erp.materials m on m.id=i.material_id
    left join erp.material_rolls mr on mr.id=i.roll_id
    where i.opening_id=h.id and i.balance_type='MATERIAL'
    order by i.id
  loop
    if r.material_type='FABRIC' and r.roll_id is null then
      raise exception 'AE_FABRIC_OPENING_REQUIRES_ROLL';
    end if;
    if r.roll_id is not null then
      if r.material_type is distinct from 'FABRIC' then
        raise exception 'AE_OPENING_ROLL_REQUIRES_FABRIC';
      end if;
      if r.roll_material_id is distinct from r.material_id then
        raise exception 'AE_OPENING_ROLL_MATERIAL_MISMATCH';
      end if;
      if r.roll_status is distinct from 'AVAILABLE' then
        raise exception 'AE_OPENING_ROLL_NOT_AVAILABLE';
      end if;
      if r.roll_purchase_item_id is not null then
        raise exception 'AE_PURCHASE_ROLL_CANNOT_BE_OPENING_BALANCE';
      end if;
      if coalesce(r.qty,0)>r.roll_original_qty then
        raise exception 'AE_OPENING_QTY_EXCEEDS_ROLL_ORIGINAL';
      end if;
      if exists(
        select 1 from erp.opening_balance_items prior
        join erp.opening_balance_headers prior_h on prior_h.id=prior.opening_id
        where prior.roll_id=r.roll_id and prior_h.status='POSTED'
      ) then
        raise exception 'AE_OPENING_ROLL_ALREADY_POSTED';
      end if;
      if exists(select 1 from erp.material_stock_movements prior_m where prior_m.roll_id=r.roll_id)
         or coalesce(r.roll_cached_qty,0)<>0 then
        raise exception 'AE_OPENING_ROLL_HAS_EXISTING_STOCK_HISTORY';
      end if;
    end if;
  end loop;

  select count(*),(array_agg(id order by id))[1] into v_fg_count,v_default_fg_location from erp.locations where location_type='FG_WAREHOUSE' and is_active=true;$replacement$);
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure) into d;
  anchor:=E'\nend\n$function$';
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'AE_REPORT_ANCHOR';
  end if;
  execute replace(d,anchor,$replacement$
  return query
  select 'V2620AE_OPENING_MATERIAL_ROLL_INTEGRITY'::text,'CRITICAL'::text,
    (select count(*)::bigint
    from erp.opening_balance_items i
    join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
    left join erp.materials material on material.id=i.material_id
    left join erp.material_rolls roll on roll.id=i.roll_id
    where (i.roll_id is not null and i.balance_type<>'MATERIAL')
      or (i.balance_type='MATERIAL' and (
      (material.material_type='FABRIC' and i.roll_id is null)
      or (i.roll_id is not null and (
        material.material_type is distinct from 'FABRIC'
        or
        roll.material_id is distinct from i.material_id
        or roll.purchase_item_id is not null
        or i.qty>roll.original_qty
        or (select count(*) from erp.opening_balance_items other_i
            join erp.opening_balance_headers other_h on other_h.id=other_i.opening_id
            where other_h.status='POSTED' and other_i.balance_type='MATERIAL'
              and other_i.roll_id=i.roll_id)<>1
        or (select count(*) from erp.material_stock_movements opening_m
            where opening_m.roll_id=i.roll_id and opening_m.movement_type='OPENING'
              and opening_m.reversal_of_id is null)<>1
        or exists(select 1 from erp.material_stock_movements purchase_m
            where purchase_m.roll_id=i.roll_id and purchase_m.movement_type='PURCHASE'
              and purchase_m.reversal_of_id is null)
      ))
    ))),
    'Each posted opening roll must belong to one fabric line, enter once, and stay within original quantity'::text;

end
$function$$replacement$);
end
$canonical_opening_v2620ae$;

do $installed_v2620ae$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620ae_rollback_capsule)<>2 then
    raise exception 'AE_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620ae_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp.post_opening_balance(uuid)','cc89ac9e978723c70728cc183104490109bf2530ce8dd1a99b314018a5b0f6eb','6460ab913c9a0614df6a622ff2a223df21c13d1361e14e6089c09375f7a95b40',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','6a93242cb0325baee511c2753eb65588600fe8b9a7fc62d423b85f14bf9c71d5','b213246d9d2373924699d6a13186b6ebe0e6e87867c0818c70b4e6e54ec09aef',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620ae_rollback_capsule
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
      raise exception 'AE_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;

end
$installed_v2620ae$;

do $boundary_v2620ae$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620ae_rollback_capsule') order by c.relname loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>217 then
    raise exception 'AE_FULL_ERP_BOUNDARY_CARDINALITY expected217 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620ae_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620ae$;

insert into erp.schema_migrations(version,description)
values('v2.6.20ae','One physical fabric roll enters opening stock once, within original quantity; invalid history makes owner reports not ready');
commit;
