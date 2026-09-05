-- Disposable F06 scale proof. Every generated row is rolled back.
-- VENI. VIDI. VICI. ERP. Reliable data is authoritative; partial collections
-- must be disclosed, never presented to an operator as complete history.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local statement_timeout='20s';

create temporary table cp6_workspace_scale_result(result jsonb) on commit drop;

do $scale$
declare
  v_po uuid;
  v_group uuid;
  v_receipt_line uuid;
  v_receipt_size_line uuid;
  v_delivery uuid;
  v_model uuid;
  v_product uuid;
  v_qc uuid;
  v_item uuid;
  v_workspace jsonb;
  v_filtered jsonb;
  v_started timestamptz;
  v_elapsed_ms numeric;
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
  v_filtered:=public.erp_get_laundry_qc_workspace_v1(
    'QC','CP6-SCALE-PRODUCT-0700'
  );
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
  if jsonb_array_length(v_filtered#>'{lookups,products}')<>1
     or v_filtered#>>'{lookups,products,0,sku}'<>'CP6-SCALE-PRODUCT-0700'
     or (v_filtered#>>'{collection_window,products_truncated}')::boolean then
    raise exception 'CP6 server-side product refinement failed: %',
      v_filtered#>'{lookups,products}';
  end if;

  perform set_config('enable_seqscan','off',true);
  for v_line in execute format(
    'explain(costs off) select receipt_id,receipt_line_id,custody_outcome,qty_attempted_pcs,return_wip_event_id from erp.laundry_failed_wash_attempts where delivery_id=%L::uuid',
    v_delivery
  ) loop
    v_plan:=v_plan||v_line||E'\n';
  end loop;
  if position('idx_laundry_failed_wash_attempts_delivery_v2620a' in v_plan)=0 then
    raise exception 'CP6 hot failed-wash dependency plan did not own the covering index: %',v_plan;
  end if;

  insert into cp6_workspace_scale_result(result) values(jsonb_build_object(
    'status','PASS',
    'dataset',jsonb_build_object('generated_products',700,'generated_qc_history',205),
    'returned',jsonb_build_object('products',500,'qc_history',200),
    'collection_window',v_workspace->'collection_window',
    'filtered_product_count',jsonb_array_length(v_filtered#>'{lookups,products}'),
    'elapsed_ms',v_elapsed_ms,
    'covering_index_observed',true,
    'transaction','ROLLBACK_ONLY',
    'production_go',false
  ));
end
$scale$;

select result from cp6_workspace_scale_result;
rollback;
