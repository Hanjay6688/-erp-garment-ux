-- CP6 O: cumulative AP/GRNI allocation across every line in one supplier return.
-- Forward-only successor; the published N migration and rollback remain byte-identical.
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
  erp.material_cost_checkpoints,erp.cp6_v2620n_rollback_capsule
in share row exclusive mode;

do $predecessor_v2620o$
declare r record;c record;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20n')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20o')
     or to_regclass('erp.cp6_v2620o_rollback_capsule') is not null then
    raise exception 'O_REQUIRES_EXACT_N_WITHOUT_O_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20n_cp6_supplier_cent_lifecycle')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260911124328'
         and name='erp_v2_6_20n_cp6_supplier_cent_lifecycle'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('4b351432f4ddd8781f42c3c194b78fc575257e3a5fd60753e310c9928590b21e',
              '3cccb407130c862d66bfb7ee74eb00a3be98121c1892cc646901a9ca2d62d273'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260911124328')
     or (select count(*) from erp.cp6_v2620n_rollback_capsule)<>7 then
    raise exception 'O_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH';
  end if;
  for r in select * from(values
    ('erp.post_material_supplier_return(uuid)',
      'f5f6603b258eeda0b34a10f06a301b94c488525dfddfe0863e5ded8f56244ad1',
      'b4ac34b5df0e35f0cf1afe85d4a92e0b369922f91d0ce9eb4e2589a71367d607',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()',
      'efde954275e89f01793f405e2b000c6c599bae0be731869802f288994dd154fa',
      'f50decac0d38f9ddc2cfc5a28af53607fb8c1cf38cde5a65f13b38ec748a6fda',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620n_rollback_capsule
    where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(
            pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
            is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'O_TRUSTED_N_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if not exists(select 1 from pg_class
      where oid='erp.supplier_cent_posting_facts'::regclass
        and relrowsecurity and relowner='postgres'::regrole)
     or exists(select 1 from information_schema.role_table_grants
       where table_schema='erp' and table_name='supplier_cent_posting_facts'
         and grantee in('PUBLIC','anon','authenticated','service_role')) then
    raise exception 'O_INHERITED_N_SECURITY_MISMATCH';
  end if;

  -- Refuse ambiguous legacy facts. A separate reviewed correction is required
  -- for any already-posted over-allocation; O never rewrites business history.
  if exists(
    select 1
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where rh.status='POSTED' and(
      ri.ap_relief_qty_snapshot is null or ri.grni_relief_qty_snapshot is null
      or ri.ap_relief_amount_snapshot is null or ri.grni_relief_amount_snapshot is null
      or ri.ap_relief_qty_snapshot<0 or ri.grni_relief_qty_snapshot<0
      or ri.ap_relief_qty_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.grni_relief_qty_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.ap_relief_amount_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.grni_relief_amount_snapshot::text in('NaN','Infinity','-Infinity')
      or abs(ri.ap_relief_qty_snapshot+ri.grni_relief_qty_snapshot-ri.qty)>0.000001
      or abs(ri.ap_relief_amount_snapshot
        -ri.ap_relief_qty_snapshot*ri.supplier_credit_unit_price)>0.000001
      or abs(ri.grni_relief_amount_snapshot
        -ri.grni_relief_qty_snapshot*i.unit_price)>0.000001
    )
  ) or exists(
    select 1
    from erp.material_purchase_items i
    where coalesce((
      select sum(ri.ap_relief_qty_snapshot)
      from erp.material_supplier_return_items ri
      join erp.material_supplier_returns rh on rh.id=ri.return_id
      where ri.purchase_item_id=i.id and rh.status='POSTED'
    ),0)>case when i.invoice_match_state='DIRECT_FINAL' then i.qty
      else erp.material_purchase_posted_invoice_qty(i.id) end+0.000001
  ) or exists(
    -- A later invoice must never launder an AP allocation that exceeded the
    -- invoice capacity available when an immutable return fact was recorded.
    with legacy_capacity as(
      select i.id purchase_item_id,
        case when i.invoice_match_state='DIRECT_FINAL' then i.qty else
          coalesce((
            select sum(il.qty_invoiced)
            from erp.material_supplier_invoice_lines il
            join erp.material_supplier_invoices ih on ih.id=il.invoice_id
            where il.purchase_item_id=i.id and ih.status='POSTED'
              and not exists(
                select 1 from erp.supplier_cent_posting_facts f
                where f.source_type='MATERIAL_SUPPLIER_INVOICE'
                  and f.source_id=ih.id and f.phase='POST'
              )
          ),0)
        end-coalesce((
          select sum(ri.ap_relief_qty_snapshot)
          from erp.material_supplier_return_items ri
          join erp.material_supplier_returns rh on rh.id=ri.return_id
          where ri.purchase_item_id=i.id and rh.status='POSTED'
            and not exists(
              select 1 from erp.supplier_cent_posting_facts f
              where f.source_type='MATERIAL_SUPPLIER_RETURN'
                and f.source_id=rh.id and f.phase='POST'
            )
        ),0) opening_capacity
      from erp.material_purchase_items i
    ), allocation_events as(
      select il.purchase_item_id,f.recorded_at,f.source_id,
        0 event_order,sum(il.qty_invoiced)::numeric delta,'INVOICE'::text event_kind
      from erp.supplier_cent_posting_facts f
      join erp.material_supplier_invoices ih
        on ih.id=f.source_id and ih.status='POSTED'
      join erp.material_supplier_invoice_lines il on il.invoice_id=ih.id
      join erp.material_purchase_items i on i.id=il.purchase_item_id
      where f.source_type='MATERIAL_SUPPLIER_INVOICE' and f.phase='POST'
        and i.invoice_match_state<>'DIRECT_FINAL'
      group by il.purchase_item_id,f.recorded_at,f.source_id
      union all
      select ri.purchase_item_id,f.recorded_at,f.source_id,
        1 event_order,-sum(ri.ap_relief_qty_snapshot)::numeric,'RETURN'::text
      from erp.supplier_cent_posting_facts f
      join erp.material_supplier_returns rh
        on rh.id=f.source_id and rh.status='POSTED'
      join erp.material_supplier_return_items ri on ri.return_id=rh.id
      where f.source_type='MATERIAL_SUPPLIER_RETURN' and f.phase='POST'
      group by ri.purchase_item_id,f.recorded_at,f.source_id
    ), running_capacity as(
      select e.purchase_item_id,e.event_kind,l.opening_capacity+
        sum(e.delta) over(
          partition by e.purchase_item_id
          order by e.recorded_at,e.event_order,e.source_id
          rows between unbounded preceding and current row
        ) capacity_after
      from allocation_events e
      join legacy_capacity l using(purchase_item_id)
    )
    select 1 from running_capacity
    where event_kind='RETURN' and capacity_after < -0.000001
  ) then
    raise exception 'O_PREEXISTING_RETURN_ALLOCATION_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620o$;

create table erp.cp6_v2620o_rollback_capsule(
  like erp.cp6_v2620n_rollback_capsule including all
);
alter table erp.cp6_v2620o_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620o_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620o_rollback_capsule(
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
  'erp.post_material_supplier_return(uuid)'::regprocedure,
  'erp.run_v267_financial_truth_checks()'::regprocedure
);

do $patch_return_v2620o$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.post_material_supplier_return(uuid)'::regprocedure)
  into d;
  anchor:=$a$  v_prior_ap_qty numeric;
  v_ap_qty numeric;$a$;
  replacement:=$r$  v_prior_ap_qty numeric;
  v_current_purchase_item uuid;
  v_document_ap_qty numeric:=0;
  v_ap_qty numeric;$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'O_RETURN_DECLARATION_ANCHOR_MISMATCH';
  end if;
  d:=replace(d,anchor,replacement);
  anchor:=$a$    v_invoiced_qty:=case when r.invoice_match_state='DIRECT_FINAL'
      then r.receipt_qty else erp.material_purchase_posted_invoice_qty(r.purchase_item_id) end;
    select coalesce(sum(coalesce(x.ap_relief_qty_snapshot,0)),0)
    into v_prior_ap_qty
    from erp.material_supplier_return_items x
    join erp.material_supplier_returns xh on xh.id=x.return_id
    where x.purchase_item_id=r.purchase_item_id and xh.status='POSTED';
    v_ap_qty:=least(r.qty,greatest(v_invoiced_qty-v_prior_ap_qty,0));$a$;
  replacement:=$r$    if v_current_purchase_item is distinct from r.purchase_item_id then
      v_current_purchase_item:=r.purchase_item_id;
      v_document_ap_qty:=0;
      v_invoiced_qty:=case when r.invoice_match_state='DIRECT_FINAL'
        then r.receipt_qty else erp.material_purchase_posted_invoice_qty(r.purchase_item_id) end;
      select coalesce(sum(coalesce(x.ap_relief_qty_snapshot,0)),0)
      into v_prior_ap_qty
      from erp.material_supplier_return_items x
      join erp.material_supplier_returns xh on xh.id=x.return_id
      where x.purchase_item_id=r.purchase_item_id and xh.status='POSTED';
    end if;
    v_ap_qty:=least(r.qty,
      greatest(v_invoiced_qty-v_prior_ap_qty-v_document_ap_qty,0));$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'O_RETURN_ALLOCATION_ANCHOR_MISMATCH';
  end if;
  d:=replace(d,anchor,replacement);
  anchor:=$a$        grni_relief_amount_snapshot=v_grni_qty*r.estimate_unit_cost
    where id=r.id;$a$;
  replacement:=$r$        grni_relief_amount_snapshot=v_grni_qty*r.estimate_unit_cost
    where id=r.id;
    v_document_ap_qty:=v_document_ap_qty+v_ap_qty;$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'O_RETURN_ACCUMULATOR_ANCHOR_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_return_v2620o$;

do $patch_report_v2620o$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.run_v267_financial_truth_checks()'::regprocedure)
  into d;
  anchor:=$a$  union all
  select 'V2620N_SUPPLIER_CENT_FACT_LEDGER','CRITICAL',count(*)::bigint,$a$;
  replacement:=$r$  union all
  select 'V2620O_SUPPLIER_RETURN_ALLOCATION','CRITICAL',count(*)::bigint,
    'Posted supplier-return AP/GRNI snapshots must partition each line and AP relief must not exceed invoiced quantity'
  from erp.material_purchase_items i
  where exists(
    select 1
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where ri.purchase_item_id=i.id and rh.status='POSTED' and(
      ri.ap_relief_qty_snapshot is null or ri.grni_relief_qty_snapshot is null
      or ri.ap_relief_amount_snapshot is null or ri.grni_relief_amount_snapshot is null
      or ri.ap_relief_qty_snapshot<0 or ri.grni_relief_qty_snapshot<0
      or ri.ap_relief_qty_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.grni_relief_qty_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.ap_relief_amount_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.grni_relief_amount_snapshot::text in('NaN','Infinity','-Infinity')
      or abs(ri.ap_relief_qty_snapshot+ri.grni_relief_qty_snapshot-ri.qty)>0.000001
      or abs(ri.ap_relief_amount_snapshot
        -ri.ap_relief_qty_snapshot*ri.supplier_credit_unit_price)>0.000001
      or abs(ri.grni_relief_amount_snapshot
        -ri.grni_relief_qty_snapshot*i.unit_price)>0.000001
    )
  ) or coalesce((
    select sum(ri.ap_relief_qty_snapshot)
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where ri.purchase_item_id=i.id and rh.status='POSTED'
  ),0)>case when i.invoice_match_state='DIRECT_FINAL' then i.qty
    else erp.material_purchase_posted_invoice_qty(i.id) end+0.000001
  or i.id in(
    with legacy_capacity as(
      select pi.id purchase_item_id,
        case when pi.invoice_match_state='DIRECT_FINAL' then pi.qty else
          coalesce((
            select sum(il.qty_invoiced)
            from erp.material_supplier_invoice_lines il
            join erp.material_supplier_invoices ih on ih.id=il.invoice_id
            where il.purchase_item_id=pi.id and ih.status='POSTED'
              and not exists(
                select 1 from erp.supplier_cent_posting_facts f
                where f.source_type='MATERIAL_SUPPLIER_INVOICE'
                  and f.source_id=ih.id and f.phase='POST'
              )
          ),0)
        end-coalesce((
          select sum(ri.ap_relief_qty_snapshot)
          from erp.material_supplier_return_items ri
          join erp.material_supplier_returns rh on rh.id=ri.return_id
          where ri.purchase_item_id=pi.id and rh.status='POSTED'
            and not exists(
              select 1 from erp.supplier_cent_posting_facts f
              where f.source_type='MATERIAL_SUPPLIER_RETURN'
                and f.source_id=rh.id and f.phase='POST'
            )
        ),0) opening_capacity
      from erp.material_purchase_items pi
    ), allocation_events as(
      select il.purchase_item_id,f.recorded_at,f.source_id,
        0 event_order,sum(il.qty_invoiced)::numeric delta,'INVOICE'::text event_kind
      from erp.supplier_cent_posting_facts f
      join erp.material_supplier_invoices ih
        on ih.id=f.source_id and ih.status='POSTED'
      join erp.material_supplier_invoice_lines il on il.invoice_id=ih.id
      join erp.material_purchase_items pi on pi.id=il.purchase_item_id
      where f.source_type='MATERIAL_SUPPLIER_INVOICE' and f.phase='POST'
        and pi.invoice_match_state<>'DIRECT_FINAL'
      group by il.purchase_item_id,f.recorded_at,f.source_id
      union all
      select ri.purchase_item_id,f.recorded_at,f.source_id,
        1 event_order,-sum(ri.ap_relief_qty_snapshot)::numeric,'RETURN'::text
      from erp.supplier_cent_posting_facts f
      join erp.material_supplier_returns rh
        on rh.id=f.source_id and rh.status='POSTED'
      join erp.material_supplier_return_items ri on ri.return_id=rh.id
      where f.source_type='MATERIAL_SUPPLIER_RETURN' and f.phase='POST'
      group by ri.purchase_item_id,f.recorded_at,f.source_id
    ), running_capacity as(
      select e.purchase_item_id,e.event_kind,l.opening_capacity+
        sum(e.delta) over(
          partition by e.purchase_item_id
          order by e.recorded_at,e.event_order,e.source_id
          rows between unbounded preceding and current row
        ) capacity_after
      from allocation_events e
      join legacy_capacity l using(purchase_item_id)
    )
    select purchase_item_id from running_capacity
    where event_kind='RETURN' and capacity_after < -0.000001
  )

  union all
  select 'V2620N_SUPPLIER_CENT_FACT_LEDGER','CRITICAL',count(*)::bigint,$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'O_REPORT_ALLOCATION_ANCHOR_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_report_v2620o$;

do $installed_v2620o$
declare r record;c record;v_count bigint;
begin
  if (select count(*) from erp.cp6_v2620o_rollback_capsule)<>2 then
    raise exception 'O_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620o_rollback_capsule cap
  set installed_definition_sha256=encode(extensions.digest(convert_to(
    pg_get_functiondef(to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp.post_material_supplier_return(uuid)',
      'b4ac34b5df0e35f0cf1afe85d4a92e0b369922f91d0ce9eb4e2589a71367d607',
      'eff9b9a2a19eca7f51d51ac0fc73983d53f7fa5e4c699407813580dac91bbace',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()',
      'f50decac0d38f9ddc2cfc5a28af53607fb8c1cf38cde5a65f13b38ec748a6fda',
      'fc3edcc094fb4843886206466801f96441907d83efeed01c92c5604f658a96d0',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620o_rollback_capsule
    where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(
            pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
            is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'O_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  select issue_count into v_count from erp.run_v267_financial_truth_checks()
  where check_name='V2620O_SUPPLIER_RETURN_ALLOCATION';
  if v_count is distinct from 0 then
    raise exception 'O_INSTALLED_RETURN_ALLOCATION_RECONCILIATION_FAILED: %',v_count;
  end if;
end
$installed_v2620o$;

do $boundary_v2620o$
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
    'material_cost_checkpoints','cp6_v2620n_rollback_capsule'
  ]::text[]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620o_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620o$;

insert into erp.schema_migrations(version,description)
values('v2.6.20o',
  'Cumulative per-document supplier-return AP/GRNI allocation and posted snapshot reconciliation');
commit;
