-- Disposable F06 scale proof. Every generated row is rolled back.
-- VENI. VIDI. VICI. ERP. Reliable data is authoritative; partial collections
-- must be disclosed, never presented to an operator as complete history.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local statement_timeout='20s';

create temporary table cp6_workspace_scale_result(result jsonb) on commit drop;
create temporary table cp6_workspace_scale_seen_products(
  id uuid primary key,
  sku text not null
) on commit drop;

do $scale$
declare
  v_po uuid;
  v_group uuid;
  v_receipt_line uuid;
  v_receipt_size_line uuid;
  v_laundry_source uuid;
  v_closed_delivery_source uuid;
  v_delivery uuid;
  v_model uuid;
  v_product uuid;
  v_qc uuid;
  v_item uuid;
  v_workspace jsonb;
  v_workspace_after_search jsonb;
  v_page jsonb;
  v_exact jsonb;
  v_laundry_exact jsonb;
  v_laundry_closed_rejected boolean:=false;
  v_hpp_book_gate_rejected boolean:=false;
  v_wip_gate_rejected boolean:=false;
  v_revenue_gate_rejected boolean:=false;
  v_gate_issue_count bigint:=0;
  v_post jsonb;
  v_financial jsonb;
  v_cursor text:=null;
  v_next_cursor text;
  v_pages integer:=0;
  v_seen integer:=0;
  v_generated_seen integer:=0;
  v_group_version bigint;
  v_queue_snapshot jsonb;
  v_started timestamptz;
  v_elapsed_ms numeric;
  v_resolver_started timestamptz;
  v_resolver_elapsed_ms numeric;
  v_plan text:='';
  v_line text;
  i integer;
begin
  select po.id,g.id,rl.id,rx.id,d.id,po.model_id
  into strict v_po,v_group,v_receipt_line,v_receipt_size_line,v_delivery,v_model
  from erp.production_orders po
  join erp.cutting_groups g on g.po_id=po.id
  join erp.laundry_delivery_lines dl on dl.cutting_group_id=g.id
  join erp.laundry_deliveries d on d.id=dl.delivery_id
  join erp.laundry_receipt_lines rl on rl.delivery_line_id=dl.id
  join erp.laundry_receipts r on r.id=rl.receipt_id
  join erp.laundry_receipt_batch_size_lines rx on rx.receipt_line_id=rl.id
  where po.po_number='CP6-MX-REVQC_INVOICE_REV'
    and r.status='POSTED'
    and not exists(
      select 1
      from erp.qc_inspection_items qi
      join erp.qc_inspections qh on qh.id=qi.inspection_id
      where qi.source_laundry_receipt_batch_size_line_id=rx.id
        and qh.status<>'REVERSED'
    )
  order by r.physical_at desc,r.id desc
  limit 1;

  -- This is a disposable performance fixture, not business history.  Keep
  -- every row trigger enabled: products follow normal identity validation,
  -- while each historical QC is created DRAFT, receives one valid exact
  -- lineage item, and only then transitions to REVERSED.  The outer rollback
  -- removes both fixture rows and their audit rows.
  for i in 1..700 loop
    v_product:=md5('CP6-WORKSPACE-SCALE-PRODUCT-'||i::text)::uuid;
    insert into erp.products(
      id,sku,model_id,brand_id,color_name,size_id,product_name,
      identity_root_id,effective_from,is_active,is_portal_visible
    ) values(
      v_product,'CP6-SCALE-PRODUCT-'||lpad(i::text,4,'0'),v_model,
      'c8c10000-0000-4000-8000-000000000003',
      'SCALE-'||lpad(i::text,4,'0'),
      'c8c10000-0000-4000-8000-000000000002',
      'CP6 scale product '||lpad(i::text,4,'0'),v_product,
      '2026-01-01 00:00:00+00',true,true
    );
  end loop;

  -- Product 0700 is posted below, so its master data must be operational—not
  -- merely searchable. Declare the intentional no-accessory choice explicitly;
  -- the HPP writer must keep rejecting every undeclared BOM fallback.
  insert into erp.accessory_bom_versions(
    product_id,version_label,effective_from,is_active,notes
  ) values(
    md5('CP6-WORKSPACE-SCALE-PRODUCT-700')::uuid,
    'CP6-SCALE-NO-ACCESSORY-0700','2026-01-01 00:00:00+00',true,
    'Explicit empty BOM for rollback-only product 0700 transaction proof'
  );

  for i in 1..205 loop
    v_qc:=md5('CP6-WORKSPACE-SCALE-QC-'||i::text)::uuid;
    v_item:=md5('CP6-WORKSPACE-SCALE-QC-ITEM-'||i::text)::uuid;
    insert into erp.qc_inspections(
      id,inspection_number,po_id,physical_at,status,notes,created_by,
      destination_location_id
    ) values(
      v_qc,'CP6-SCALE-QC-'||lpad(i::text,4,'0'),v_po,
      '2026-09-02 13:00:00+00'::timestamptz+(i||' seconds')::interval,
      'DRAFT','Rollback-only bounded-history scale proof',
      'c8c00000-0000-4000-8000-000000000001',
      'c8c20000-0000-4000-8000-000000000001'
    );
    insert into erp.qc_inspection_items(
      id,inspection_id,cutting_group_id,source_laundry_receipt_line_id,
      source_laundry_receipt_batch_size_line_id,final_product_id,
      qty_good_pcs,qty_bs_pcs,notes
    ) values(
      v_item,v_qc,v_group,v_receipt_line,v_receipt_size_line,
      'c8c10000-0000-4000-8000-000000000004',10,0,
      'Rollback-only bounded-history scale proof'
    );
    update erp.qc_inspections
    set status='REVERSED'
    where id=v_qc;
  end loop;

  analyze erp.products;
  analyze erp.qc_inspections;
  analyze erp.qc_inspection_items;

  perform set_config(
    'request.jwt.claims',
    jsonb_build_object(
      'sub','c8c00000-0000-4000-8000-000000000101',
      'role','authenticated'
    )::text,
    true
  );
  execute 'set local role authenticated';
  v_started:=clock_timestamp();
  v_workspace:=public.erp_get_laundry_qc_workspace_v1('QC',null);
  v_elapsed_ms:=round(extract(epoch from(clock_timestamp()-v_started))*1000,3);
  execute 'reset role';
  v_queue_snapshot:=v_workspace->'qc_queue';

  -- Page the source-bound resolver to completion. Every product is unique in
  -- the temporary seen set, so a repeated/omitted keyset boundary fails.
  v_resolver_started:=clock_timestamp();
  loop
    execute 'set local role authenticated';
    v_page:=public.erp_search_final_sku_products_v1(
      v_receipt_size_line,'2026-09-03 14:00:00+00',null,v_cursor,100
    );
    execute 'reset role';
    v_pages:=v_pages+1;
    insert into cp6_workspace_scale_seen_products(id,sku)
    select (x->>'id')::uuid,x->>'sku'
    from jsonb_array_elements(v_page->'products') x;
    exit when not (v_page->>'has_more')::boolean;
    v_next_cursor:=v_page->>'next_cursor';
    if v_next_cursor is null or v_next_cursor is not distinct from v_cursor then
      raise exception 'CP6 product resolver returned a missing/repeated cursor: %',v_page;
    end if;
    v_cursor:=v_next_cursor;
    if v_pages>100 then
      raise exception 'CP6 product resolver paging did not terminate';
    end if;
  end loop;
  v_resolver_elapsed_ms:=round(
    extract(epoch from(clock_timestamp()-v_resolver_started))*1000,3
  );
  select count(*),count(*) filter(where sku like 'CP6-SCALE-PRODUCT-%')
  into v_seen,v_generated_seen from cp6_workspace_scale_seen_products;

  execute 'set local role authenticated';
  v_exact:=public.erp_search_final_sku_products_v1(
    v_receipt_size_line,'2026-09-03 14:00:00+00',
    'CP6-SCALE-PRODUCT-0700',null,100
  );
  v_workspace_after_search:=public.erp_get_laundry_qc_workspace_v1('QC',null);
  execute 'reset role';

  -- Laundry-BS uses its own outstanding delivery-size authority. Product
  -- 0700 is outside the workspace's bounded first 500 but must remain
  -- selectable through this exact source-bound endpoint.
  select sx.id into strict v_laundry_source
  from erp.laundry_delivery_batch_size_lines sx
  join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
  join erp.laundry_deliveries d on d.id=dl.delivery_id
    and d.status in('SENT','PARTIAL_RETURN')
  join erp.cutting_groups g on g.id=dl.cutting_group_id
  join erp.production_orders po on po.id=g.po_id
  where po.model_id=v_model and sx.size_id='c8c10000-0000-4000-8000-000000000002'
    and sx.qty_sent_pcs>coalesce((
      select sum(rx.qty_good_received+rx.qty_bs_laundry)
      from erp.laundry_receipt_batch_size_lines rx
      join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
      join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
      where rx.delivery_batch_size_line_id=sx.id
    ),0)
  order by d.physical_at,sx.id
  limit 1;
  select delivery_batch_size_line_id into strict v_closed_delivery_source
  from erp.laundry_receipt_batch_size_lines where id=v_receipt_size_line;

  execute 'set local role authenticated';
  v_laundry_exact:=public.erp_search_laundry_bs_products_v1(
    v_laundry_source,'2026-09-03 14:00:00+00',
    'CP6-SCALE-PRODUCT-0700',null,100
  );
  begin
    perform public.erp_search_laundry_bs_products_v1(
      v_closed_delivery_source,'2026-09-03 14:00:00+00',null,null,100
    );
    raise exception 'Closed Laundry source unexpectedly remained selectable';
  exception when others then
    if sqlerrm not like '%no longer an authoritative outstanding delivery-size row%' then
      raise;
    end if;
    v_laundry_closed_rejected:=true;
  end;
  execute 'reset role';

  if jsonb_array_length(v_workspace#>'{lookups,products}')<>500
     or jsonb_array_length(v_workspace->'qc_history')<>200
     or (v_workspace#>>'{collection_window,product_limit}')::integer<>500
     or (v_workspace#>>'{collection_window,transaction_limit}')::integer<>200
     or (v_workspace#>>'{collection_window,products_truncated}')::boolean is not true
     or (v_workspace#>>'{collection_window,qc_history_truncated}')::boolean is not true
     or (v_workspace#>>'{collection_window,any_truncated}')::boolean is not true
     or (v_workspace#>>'{collection_window,query_required_for_more}')::boolean is not true
     or (v_workspace#>>'{readiness,lineage_integrity_ok}')::boolean is not true then
    raise exception 'CP6 bounded workspace scale contract mismatch: %',
      v_workspace->'collection_window';
  end if;
  if v_generated_seen<>700 or v_pages<7
     or jsonb_array_length(v_exact->'products')<>1
     or v_exact#>>'{products,0,sku}'<>'CP6-SCALE-PRODUCT-0700'
     or (v_exact->>'has_more')::boolean
     or jsonb_array_length(v_laundry_exact->'products')<>1
     or v_laundry_exact#>>'{products,0,sku}'<>'CP6-SCALE-PRODUCT-0700'
     or v_laundry_exact->>'source_delivery_batch_size_line_id'<>v_laundry_source::text
     or not v_laundry_closed_rejected
     or v_workspace_after_search->'qc_queue' is distinct from v_queue_snapshot then
    raise exception 'CP6 source-bound product paging/queue isolation failed: pages %, seen %, exact %, queue stable %',
      v_pages,v_generated_seen,v_exact,
      v_workspace_after_search->'qc_queue' is not distinct from v_queue_snapshot;
  end if;

  -- Prove product 0700 is operational, not merely searchable. The entire
  -- mutation stays inside this outer rollback-only transaction.
  select row_version into strict v_group_version
  from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_post:=public.erp_save_laundry_qc_action_v1(
    'POST_FINAL_SKU',jsonb_build_object(
      'cutting_group_id',v_group,
      'destination_location_id','c8c20000-0000-4000-8000-000000000001',
      'physical_at','2026-09-03T14:00:00Z',
      'reason','CP6 scale product 0700 real transaction proof',
      'good_qty_pcs',1,
      'completion_mode','PARTIAL_SELECTION',
      'lines',jsonb_build_array(jsonb_build_object(
        'final_product_id',md5('CP6-WORKSPACE-SCALE-PRODUCT-700')::uuid,
        'qty_good_pcs',1,'qty_bs_pcs',0,
        'source_laundry_receipt_line_id',v_receipt_line,
        'source_laundry_receipt_batch_size_line_id',v_receipt_size_line,
        'notes','Beyond-first-500 SKU posted through authoritative facade'
      ))
    ),'ca6e0000-0000-4000-8000-000000000700',v_group_version
  );
  execute 'reset role';
  select jsonb_build_object(
    'committed',v_post->'committed',
    'posted_product',(select p.sku from erp.fg_lots l
      join erp.products p on p.id=l.product_id
      where l.qc_item_id in(select id from erp.qc_inspection_items
        where inspection_id=(v_post->>'qc_inspection_id')::uuid)),
    'fg_qty',(select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m
      join erp.fg_lots l on l.id=m.lot_id where l.po_id=v_po),
    'active_laundry_hpp',(select coalesce(sum(c.total_cost),0)
      from erp.hpp_versions h
      join erp.hpp_version_components c on c.hpp_version_id=h.id
        and c.component_type='LAUNDRY'
      join erp.fg_lots l on l.id=h.lot_id
      where l.po_id=v_po and l.lot_origin='PRODUCTION' and h.is_current),
    'hpp_state',(select min(h.cost_state) from erp.hpp_versions h
      join erp.fg_lots l on l.id=h.lot_id
      where l.po_id=v_po and l.lot_origin='PRODUCTION' and h.is_current),
    'wip_net',(select coalesce(sum(j.debit-j.credit),0) from erp.journal_lines j
      where j.po_id=v_po and j.account_id=erp.account_id('WIP')),
    'fg_net',(select coalesce(sum(j.debit-j.credit),0) from erp.journal_lines j
      where j.po_id=v_po and j.account_id=erp.account_id('FG_INVENTORY')),
    'accrued_net',(select coalesce(sum(j.debit-j.credit),0) from erp.journal_lines j
      where j.po_id=v_po and j.account_id=erp.account_id('ACCRUED_MANUFACTURING')),
    'remaining_qc',(select qty_good_received-coalesce((select sum(
        qi.qty_good_pcs+qi.qty_bs_pcs) from erp.qc_inspection_items qi
        join erp.qc_inspections q on q.id=qi.inspection_id
        where qi.source_laundry_receipt_batch_size_line_id=v_receipt_size_line
          and q.status<>'REVERSED'),0)
      from erp.laundry_receipt_batch_size_lines where id=v_receipt_size_line),
    -- Scope the journal *entries* by PO, then balance every line in each
    -- selected entry.  Filtering journal lines by PO before summing would
    -- discard legitimate counterparty/AP lines whose PO dimension is null and
    -- falsely report a globally balanced journal as unbalanced.
    'unbalanced_journals',(select count(*) from(
      select e.id
      from erp.journal_entries e
      join erp.journal_lines j on j.journal_entry_id=e.id
      where exists(
        select 1 from erp.journal_lines scoped
        where scoped.journal_entry_id=e.id and scoped.po_id=v_po
      )
      group by e.id having sum(j.debit)<>sum(j.credit)
    ) bad)
  ) into v_financial;
  if v_financial<>jsonb_build_object(
    'committed',true,'posted_product','CP6-SCALE-PRODUCT-0700',
    'fg_qty',1,'active_laundry_hpp',7,'hpp_state','ESTIMATED',
    'wip_net',63,'fg_net',7,'accrued_net',-70,'remaining_qc',9,
    'unbalanced_journals',0
  ) then
    raise exception 'CP6 product 0700 mutation/HPP/WIP mismatch: %',v_financial;
  end if;

  -- The confidence gate must prove actual books, not merely return an empty
  -- list on clean data. Each deliberately corrupted state lives in an inner
  -- exception subtransaction and is rolled back before the next probe.
  select coalesce(sum(issue_count),0) into v_gate_issue_count
  from erp.run_v268_financial_report_checks()
  where severity='CRITICAL';
  if v_gate_issue_count<>0 then
    raise exception 'CP6 confidence gate is not clean before corruption probes: %',v_gate_issue_count;
  end if;

  begin
    update erp.po_hpp_gl_state set fg_value=fg_value+1 where po_id=v_po;
    if not exists(
      select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620C_PO_HPP_BOOK_MISMATCH' and issue_count>0
    ) then
      raise exception 'CP6 HPP/GL book corruption was not detected';
    end if;
    raise exception 'CP6_EXPECTED_HPP_BOOK_GATE_ROLLBACK';
  exception when raise_exception then
    if sqlerrm<>'CP6_EXPECTED_HPP_BOOK_GATE_ROLLBACK' then raise; end if;
    v_hpp_book_gate_rejected:=true;
  end;

  begin
    update erp.po_hpp_gl_state set hpp_total_cost=hpp_total_cost+1 where po_id=v_po;
    if not exists(
      select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620C_WIP_SOURCE_CONSERVATION_MISMATCH' and issue_count>0
    ) then
      raise exception 'CP6 WIP/source corruption was not detected';
    end if;
    raise exception 'CP6_EXPECTED_WIP_GATE_ROLLBACK';
  exception when raise_exception then
    if sqlerrm<>'CP6_EXPECTED_WIP_GATE_ROLLBACK' then raise; end if;
    v_wip_gate_rejected:=true;
  end;

  begin
    insert into erp.customers(id,customer_code,customer_name,is_active)
    values(
      'ca6e0000-0000-4000-8000-000000009001',
      'CP6-GATE-CUSTOMER','CP6 rollback-only gate customer',true
    );
    insert into erp.sales_headers(
      id,sale_number,customer_id,sale_date,status,source_location_id,created_by
    ) values(
      'ca6e0000-0000-4000-8000-000000009002',
      'CP6-GATE-UNJOURNALED-SALE',
      'ca6e0000-0000-4000-8000-000000009001',
      '2026-09-03 15:00:00+00','POSTED',
      'c8c20000-0000-4000-8000-000000000001',
      'c8c00000-0000-4000-8000-000000000001'
    );
    insert into erp.sales_items(
      sale_id,product_id,qty_pcs,unit_price_snapshot,discount_amount
    ) values(
      'ca6e0000-0000-4000-8000-000000009002',
      md5('CP6-WORKSPACE-SCALE-PRODUCT-700')::uuid,1,10,0
    );
    if not exists(
      select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620C_SALE_REVENUE_REPORT_INPUT_MISMATCH' and issue_count>0
    ) then
      raise exception 'CP6 sale/report revenue corruption was not detected';
    end if;
    raise exception 'CP6_EXPECTED_REVENUE_GATE_ROLLBACK';
  exception when raise_exception then
    if sqlerrm<>'CP6_EXPECTED_REVENUE_GATE_ROLLBACK' then raise; end if;
    v_revenue_gate_rejected:=true;
  end;

  select coalesce(sum(issue_count),0) into v_gate_issue_count
  from erp.run_v268_financial_report_checks()
  where severity='CRITICAL';
  if v_gate_issue_count<>0 or not v_hpp_book_gate_rejected
     or not v_wip_gate_rejected or not v_revenue_gate_rejected then
    raise exception 'CP6 confidence corruption probes left residue or skipped a gate: %, %, %, %',
      v_gate_issue_count,v_hpp_book_gate_rejected,v_wip_gate_rejected,
      v_revenue_gate_rejected;
  end if;

  -- Natural planner only: never disable sequential scans to manufacture an
  -- index claim. Equality on model/size plus the native key order should own
  -- this bounded candidate page under the representative catalog.
  for v_line in execute format(
    'explain(analyze,buffers,costs off) select id,sku from erp.products where model_id=%L::uuid and size_id=%L::uuid and is_active and is_portal_visible and effective_from<=%L::timestamptz order by effective_from,id limit 100',
    v_model,'c8c10000-0000-4000-8000-000000000002','2026-09-03 14:00:00+00'
  ) loop
    v_plan:=v_plan||v_line||E'\n';
  end loop;
  if position('idx_products_qc_model_size_effective_v2620b' in v_plan)=0
     or current_setting('enable_seqscan')<>'on' then
    raise exception 'CP6 natural product candidate plan did not own the v20b index: %',v_plan;
  end if;

  insert into cp6_workspace_scale_result(result) values(jsonb_build_object(
    'status','PASS',
    'dataset',jsonb_build_object(
      'generated_products',700,'generated_qc_history',205,
      'explicit_empty_bom_products',1
    ),
    'returned',jsonb_build_object('products',500,'qc_history',200),
    'collection_window',v_workspace->'collection_window',
    'resolver',jsonb_build_object(
      'pages',v_pages,'all_seen',v_seen,'generated_seen',v_generated_seen,
      'exact_0700_count',jsonb_array_length(v_exact->'products'),
      'queue_preserved',true,'elapsed_ms',v_resolver_elapsed_ms
    ),
    'laundry_bs_resolver',jsonb_build_object(
      'contract_version',v_laundry_exact->>'contract_version',
      'exact_0700_count',jsonb_array_length(v_laundry_exact->'products'),
      'outside_initial_500',true,
      'closed_or_wrong_source_rejected',v_laundry_closed_rejected
    ),
    'product_0700_transaction',v_financial,
    'confidence_gate',jsonb_build_object(
      'clean_critical_issue_count',v_gate_issue_count,
      'hpp_state_vs_actual_book_detected',v_hpp_book_gate_rejected,
      'wip_source_conservation_detected',v_wip_gate_rejected,
      'sale_revenue_input_detected',v_revenue_gate_rejected,
      'corruption_probe_residue',0
    ),
    'workspace_elapsed_ms',v_elapsed_ms,
    'natural_index_observed',true,
    'natural_plan',v_plan,
    'transaction','ROLLBACK_ONLY',
    'production_go',false
  ));
end
$scale$;

select result from cp6_workspace_scale_result;
rollback;
