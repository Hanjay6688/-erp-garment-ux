-- CP6 v2.6.20d independent re-audit counterexamples and adjacent lifecycle
-- regression. Caller provides the standard cp6_laundry_qc_concurrency_seed
-- in an isolated clone. Every additional fact below is rolled back.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local datestyle='ISO, MDY';
set local lock_timeout='8s';
set local statement_timeout='180s';
select set_config(
  'request.jwt.claims',
  jsonb_build_object(
    'sub','c8c00000-0000-4000-8000-000000000101',
    'role','authenticated'
  )::text,
  true
);
select set_config('app.change_reason','CP6 v20d re-audit rollback fixture',true);

do $b01_redispatch_cost_continuity$
declare
  v_po constant uuid:='c8e40000-0000-4000-8000-000000000001';
  v_group constant uuid:='c8e40000-0000-4000-8000-000000000003';
  v_batch constant uuid:='c8e40000-0000-4000-8000-000000000008';
  v_size constant uuid:='c8c10000-0000-4000-8000-000000000002';
  v_vendor constant uuid:='c8c20000-0000-4000-8000-000000000002';
  v_process constant uuid:='c8c20000-0000-4000-8000-000000000003';
  v_product constant uuid:='c8c10000-0000-4000-8000-000000000004';
  v_location constant uuid:='c8c20000-0000-4000-8000-000000000001';
  v_group_version bigint;
  v_delivery_version bigint;
  v_response jsonb;
  v_first_delivery uuid;
  v_second_delivery uuid;
  v_first_size_line uuid;
  v_second_size_line uuid;
  v_receipt_size_line uuid;
  v_receipt_line uuid;
  v_failed boolean:=false;
  v_hpp numeric;
  v_wip numeric;
  v_fg numeric;
  v_accrual numeric;
begin
  select row_version into v_group_version
  from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_DELIVERY',jsonb_build_object(
      'distribution_batch_id',v_batch,'vendor_id',v_vendor,
      'wash_process_id',v_process,'target_dyeing_color','NAVY',
      'physical_at','2026-09-01T11:00:00Z',
      'reason','CP6 v20d exact B01 first dispatch','notes','rollback fixture',
      'lines',jsonb_build_array(jsonb_build_object(
        'size_id',v_size,'qty_sent_pcs',10
      ))
    ),gen_random_uuid(),v_group_version
  );
  execute 'reset role';
  v_first_delivery:=(v_response->>'delivery_id')::uuid;
  select d.row_version,x.id into v_delivery_version,v_first_size_line
  from erp.laundry_deliveries d
  join erp.laundry_delivery_lines l on l.delivery_id=d.id
  join erp.laundry_delivery_batch_size_lines x on x.delivery_line_id=l.id
  where d.id=v_first_delivery;

  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_FAILED_WASH',jsonb_build_object(
      'delivery_id',v_first_delivery,'wash_process_id',v_process,
      'custody_outcome','RETURN_UNPROCESSED',
      'physical_at','2026-09-02T11:00:00Z',
      'reason','CP6 v20d exact B01 full physical return',
      'lines',jsonb_build_array(jsonb_build_object(
        'delivery_batch_size_line_id',v_first_size_line,'qty_attempted_pcs',10
      ))
    ),gen_random_uuid(),v_delivery_version
  );
  execute 'reset role';
  if v_response->>'delivery_status'<>'REVERSED'
     or (v_response->>'actual_cost')::numeric<>70 then
    raise exception 'v20d B01 first failed service/return is not exact: %',v_response;
  end if;

  select row_version into v_group_version
  from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_DELIVERY',jsonb_build_object(
        'distribution_batch_id',v_batch,'vendor_id',v_vendor,
        'wash_process_id',v_process,'target_dyeing_color','NAVY',
        'physical_at','2026-09-01T12:00:00Z',
        'reason','CP6 v20d impossible redispatch before return','notes','rollback fixture',
        'lines',jsonb_build_array(jsonb_build_object(
          'size_id',v_size,'qty_sent_pcs',10
        ))
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='Laundry redispatch time precedes sufficient linked physical return for this distribution batch/size'
      then v_failed:=true; else raise; end if;
  end;
  execute 'reset role';
  if not v_failed then
    raise exception 'v20d B01 accepted a redispatch before the immutable return';
  end if;

  select row_version into v_group_version
  from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_DELIVERY',jsonb_build_object(
      'distribution_batch_id',v_batch,'vendor_id',v_vendor,
      'wash_process_id',v_process,'target_dyeing_color','NAVY',
      'physical_at','2026-09-04T11:00:00Z',
      'reason','CP6 v20d exact B01 legal redispatch','notes','rollback fixture',
      'lines',jsonb_build_array(jsonb_build_object(
        'size_id',v_size,'qty_sent_pcs',10
      ))
    ),gen_random_uuid(),v_group_version
  );
  execute 'reset role';
  v_second_delivery:=(v_response->>'delivery_id')::uuid;
  select d.row_version,x.id into v_delivery_version,v_second_size_line
  from erp.laundry_deliveries d
  join erp.laundry_delivery_lines l on l.delivery_id=d.id
  join erp.laundry_delivery_batch_size_lines x on x.delivery_line_id=l.id
  where d.id=v_second_delivery;

  if (select count(*)
      from erp.laundry_redispatch_participant_allocations a
      where a.source_delivery_batch_size_line_id=v_first_size_line
        and a.successor_delivery_batch_size_line_id=v_second_size_line
        and a.source_offset_pcs=0 and a.successor_offset_pcs=0
        and a.qty_pcs=10 and a.allocation_basis='LIVE_FIFO')<>1 then
    raise exception 'v20d B01 did not persist the exact returned participant interval';
  end if;

  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_RECEIPT',jsonb_build_object(
      'delivery_id',v_second_delivery,'wash_process_id',v_process,
      'physical_at','2026-09-05T11:00:00Z',
      'reason','CP6 v20d exact B01 second receipt',
      'lines',jsonb_build_array(jsonb_build_object(
        'delivery_batch_size_line_id',v_second_size_line,
        'qty_good_received',10,'qty_bs_laundry',0,'bs_product_id',null
      ))
    ),gen_random_uuid(),v_delivery_version
  );
  execute 'reset role';
  select x.id,x.receipt_line_id into v_receipt_size_line,v_receipt_line
  from erp.laundry_receipt_batch_size_lines x
  join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
  where l.receipt_id=(v_response->>'receipt_id')::uuid;

  select row_version into v_group_version
  from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_FINAL_SKU',jsonb_build_object(
      'cutting_group_id',v_group,'destination_location_id',v_location,
      'physical_at','2026-09-06T11:00:00Z',
      'reason','CP6 v20d exact B01 all participants become FG',
      'good_qty_pcs',10,'completion_mode','ALL_READY',
      'lines',jsonb_build_array(jsonb_build_object(
        'final_product_id',v_product,'qty_good_pcs',10,'qty_bs_pcs',0,
        'source_laundry_receipt_line_id',v_receipt_line,
        'source_laundry_receipt_batch_size_line_id',v_receipt_size_line
      ))
    ),gen_random_uuid(),v_group_version
  );
  execute 'reset role';

  select coalesce(sum(h.total_cost),0) into v_hpp
  from erp.hpp_versions h join erp.fg_lots f on f.id=h.lot_id
  where f.po_id=v_po and f.lot_origin='PRODUCTION' and h.is_current;
  select coalesce(sum(l.debit-l.credit),0) into v_wip
  from erp.journal_lines l
  where l.po_id=v_po and l.account_id=erp.account_id('WIP');
  select coalesce(sum(l.debit-l.credit),0) into v_fg
  from erp.journal_lines l
  where l.po_id=v_po and l.account_id=erp.account_id('FG_INVENTORY');
  select accrued_amount into v_accrual
  from erp.laundry_cost_accrual_state where po_id=v_po;
  if v_hpp<>140 or v_wip<>0 or v_fg<>140 or v_accrual<>140
     or (select coalesce(sum(m.qty_signed),0)
       from erp.fg_stock_movements m join erp.fg_lots f on f.id=m.lot_id
       where f.po_id=v_po)<>10
     or exists(select 1 from erp.run_v268_financial_report_checks()
       where check_name in(
         'V2620C_PO_HPP_TARGET_STATE_MISMATCH',
         'V2620C_PO_HPP_BOOK_MISMATCH',
         'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH',
         'V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH'
       ) and issue_count>0) then
    raise exception 'v20d B01 cost continuity failed: HPP %, WIP %, FG %, accrual %',
      v_hpp,v_wip,v_fg,v_accrual;
  end if;
  raise notice 'CP6_V2620D_B01_REDISPATCH_COST_PASS %',jsonb_build_object(
    'hpp',v_hpp,'wip',v_wip,'fg',v_fg,'accrual',v_accrual,
    'physical_fg_pcs',10,'production_go',false
  );
end
$b01_redispatch_cost_continuity$;

do $adjacent_partial_multicycle_redispatch$
declare
  v_po constant uuid:='c8a40000-0000-4000-8000-000000000001';
  v_group constant uuid:='c8a40000-0000-4000-8000-000000000003';
  v_batch constant uuid:='c8a40000-0000-4000-8000-000000000008';
  v_size constant uuid:='c8c10000-0000-4000-8000-000000000002';
  v_vendor constant uuid:='c8c20000-0000-4000-8000-000000000002';
  v_process constant uuid:='c8c20000-0000-4000-8000-000000000003';
  v_product constant uuid:='c8c10000-0000-4000-8000-000000000004';
  v_location constant uuid:='c8c20000-0000-4000-8000-000000000001';
  v_actor constant uuid:='c8c00000-0000-4000-8000-000000000001';
  v_group_version bigint;
  v_delivery_version bigint;
  v_response jsonb;
  v_d1 uuid;v_d2 uuid;v_d3 uuid;
  v_x1 uuid;v_x2 uuid;v_x3 uuid;
  v_receipt_size uuid;v_receipt_line uuid;
  v_hpp numeric;v_wip numeric;v_fg numeric;v_accrual numeric;
begin
  insert into erp.material_rolls(
    id,material_id,supplier_id,roll_number,original_qty,cached_qty,status,received_at
  ) values(
    'c8a30000-0000-4000-8000-000000000001',
    'c8c30000-0000-4000-8000-000000000002',
    'c8c30000-0000-4000-8000-000000000001',
    'CP6-V20D-MULTI-ROLL',10,10,'AVAILABLE','2026-08-29T07:00:00Z'
  );
  insert into erp.production_orders(
    id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,
    physical_start_at,notes
  ) values(
    v_po,'CP6-V20D-MULTI-PO','a2000000-0000-0000-0000-000000000001',
    'a1000000-0000-0000-0000-000000000001',10,'SEWING','SEWING',
    '2026-08-29T07:00:00Z','v20d partial multi-cycle redispatch fixture'
  );
  insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes)
  values(
    'c8a40000-0000-4000-8000-000000000002',v_po,'CP6-V20D-MULTI-CUT',
    '2026-08-29T08:00:00Z','OPEN','v20d partial multi-cycle fixture'
  );
  insert into erp.cutting_groups(
    id,po_id,group_number,cut_at,status,cutting_batch_id,pattern_id,notes
  ) values(
    v_group,v_po,'CP6-V20D-MULTI-GROUP','2026-08-29T08:00:00Z','CUT',
    'c8a40000-0000-4000-8000-000000000002',
    'c8c10000-0000-4000-8000-000000000001','Immutable multi-cycle source'
  );
  insert into erp.cutting_group_size_slots(
    id,cutting_group_id,slot_no,size_id,drawing_no
  ) values(
    'c8a40000-0000-4000-8000-000000000004',v_group,1,v_size,1
  );
  insert into erp.cutting_group_rolls(
    id,cutting_group_id,roll_id,qty_issued,qty_consumed,qty_reported_remaining,
    qty_physically_returned,return_destination,unit_cost_snapshot,notes
  ) values(
    'c8a40000-0000-4000-8000-000000000005',v_group,
    'c8a30000-0000-4000-8000-000000000001',10,10,0,0,'NONE',0,
    'v20d partial multi-cycle fixture'
  );
  insert into erp.cutting_roll_yields(id,cutting_group_roll_id,size_slot_id,qty_pcs)
  values(
    'c8a40000-0000-4000-8000-000000000006',
    'c8a40000-0000-4000-8000-000000000005',
    'c8a40000-0000-4000-8000-000000000004',10
  );
  insert into erp.cutting_pickups(
    id,cutting_group_id,contractor_id,picked_up_at,allocation_mode,status,notes,created_by
  ) values(
    'c8a40000-0000-4000-8000-000000000007',v_group,
    'a1000000-0000-0000-0000-000000000001','2026-08-29T09:00:00Z',
    'ROLL','DRAFT','v20d partial multi-cycle fixture',v_actor
  );
  insert into erp.cutting_distribution_batches(id,pickup_id,batch_no,notes)
  values(
    v_batch,'c8a40000-0000-4000-8000-000000000007',1,
    'v20d partial multi-cycle exact batch'
  );
  insert into erp.cutting_distribution_allocations(
    id,batch_id,cutting_roll_yield_id,qty_pcs
  ) values(
    'c8a40000-0000-4000-8000-000000000009',v_batch,
    'c8a40000-0000-4000-8000-000000000006',10
  );
  update erp.cutting_groups set
    picked_up_at='2026-08-29T09:00:00Z',executor_name='CP6 v20d Mandor',status='PICKED_UP'
  where id=v_group;
  update erp.cutting_pickups set
    status='POSTED',posted_by=v_actor,posted_at='2026-08-29T09:00:00Z'
  where id='c8a40000-0000-4000-8000-000000000007';
  insert into erp.po_work_component_snapshots(
    id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at
  ) values(
    'c8a50000-0000-4000-8000-000000000001',v_po,
    'a4000000-0000-0000-0000-000000000001',1,0,'2026-08-29T09:30:00Z'
  );
  insert into erp.work_completion_events(
    id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,
    status,notes,created_by
  ) values(
    'c8a50000-0000-4000-8000-000000000002','CP6-V20D-MULTI-WC',v_po,
    'a1000000-0000-0000-0000-000000000001',v_group,'2026-08-29T10:00:00Z',
    'DRAFT','v20d partial multi-cycle sewn capacity',v_actor
  );
  insert into erp.work_completion_lines(
    id,completion_id,po_component_snapshot_id,work_component_id,
    qty_completed,qty_payable,rate_snapshot,notes
  ) values(
    'c8a50000-0000-4000-8000-000000000003',
    'c8a50000-0000-4000-8000-000000000002',
    'c8a50000-0000-4000-8000-000000000001',
    'a4000000-0000-0000-0000-000000000001',10,10,0,
    'v20d partial multi-cycle sewn capacity'
  );
  perform erp.post_work_completion('c8a50000-0000-4000-8000-000000000002');
  perform erp.record_sewing_terminal_v1(jsonb_build_object(
    'work_completion_id','c8a50000-0000-4000-8000-000000000002',
    'qty_pcs',10,'reason','CP6 v20d multi-cycle physical terminal'
  ),gen_random_uuid());

  select row_version into v_group_version from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1('POST_DELIVERY',jsonb_build_object(
    'distribution_batch_id',v_batch,'vendor_id',v_vendor,'wash_process_id',v_process,
    'target_dyeing_color','NAVY','physical_at','2026-09-01T11:00:00Z',
    'reason','v20d multi-cycle first dispatch','notes','rollback fixture',
    'lines',jsonb_build_array(jsonb_build_object('size_id',v_size,'qty_sent_pcs',10))
  ),gen_random_uuid(),v_group_version);
  execute 'reset role';
  v_d1:=(v_response->>'delivery_id')::uuid;
  select d.row_version,x.id into v_delivery_version,v_x1
  from erp.laundry_deliveries d join erp.laundry_delivery_lines l on l.delivery_id=d.id
  join erp.laundry_delivery_batch_size_lines x on x.delivery_line_id=l.id where d.id=v_d1;
  execute 'set local role authenticated';
  perform public.erp_save_laundry_qc_action_v1('POST_FAILED_WASH',jsonb_build_object(
    'delivery_id',v_d1,'wash_process_id',v_process,'custody_outcome','RETURN_UNPROCESSED',
    'physical_at','2026-09-02T11:00:00Z','reason','v20d first full failed service',
    'lines',jsonb_build_array(jsonb_build_object(
      'delivery_batch_size_line_id',v_x1,'qty_attempted_pcs',10
    ))
  ),gen_random_uuid(),v_delivery_version);
  execute 'reset role';

  select row_version into v_group_version from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1('POST_DELIVERY',jsonb_build_object(
    'distribution_batch_id',v_batch,'vendor_id',v_vendor,'wash_process_id',v_process,
    'target_dyeing_color','NAVY','physical_at','2026-09-03T11:00:00Z',
    'reason','v20d partial redispatch','notes','rollback fixture',
    'lines',jsonb_build_array(jsonb_build_object('size_id',v_size,'qty_sent_pcs',6))
  ),gen_random_uuid(),v_group_version);
  execute 'reset role';
  v_d2:=(v_response->>'delivery_id')::uuid;
  select d.row_version,x.id into v_delivery_version,v_x2
  from erp.laundry_deliveries d join erp.laundry_delivery_lines l on l.delivery_id=d.id
  join erp.laundry_delivery_batch_size_lines x on x.delivery_line_id=l.id where d.id=v_d2;
  execute 'set local role authenticated';
  perform public.erp_save_laundry_qc_action_v1('POST_FAILED_WASH',jsonb_build_object(
    'delivery_id',v_d2,'wash_process_id',v_process,'custody_outcome','RETURN_UNPROCESSED',
    'physical_at','2026-09-04T11:00:00Z','reason','v20d six participants fail twice',
    'lines',jsonb_build_array(jsonb_build_object(
      'delivery_batch_size_line_id',v_x2,'qty_attempted_pcs',6
    ))
  ),gen_random_uuid(),v_delivery_version);
  execute 'reset role';

  select row_version into v_group_version from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1('POST_DELIVERY',jsonb_build_object(
    'distribution_batch_id',v_batch,'vendor_id',v_vendor,'wash_process_id',v_process,
    'target_dyeing_color','NAVY','physical_at','2026-09-05T11:00:00Z',
    'reason','v20d mixed participant final redispatch','notes','rollback fixture',
    'lines',jsonb_build_array(jsonb_build_object('size_id',v_size,'qty_sent_pcs',10))
  ),gen_random_uuid(),v_group_version);
  execute 'reset role';
  v_d3:=(v_response->>'delivery_id')::uuid;
  select d.row_version,x.id into v_delivery_version,v_x3
  from erp.laundry_deliveries d join erp.laundry_delivery_lines l on l.delivery_id=d.id
  join erp.laundry_delivery_batch_size_lines x on x.delivery_line_id=l.id where d.id=v_d3;
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1('POST_RECEIPT',jsonb_build_object(
    'delivery_id',v_d3,'wash_process_id',v_process,'physical_at','2026-09-06T11:00:00Z',
    'reason','v20d mixed participant receipt','lines',jsonb_build_array(jsonb_build_object(
      'delivery_batch_size_line_id',v_x3,'qty_good_received',10,
      'qty_bs_laundry',0,'bs_product_id',null
    ))
  ),gen_random_uuid(),v_delivery_version);
  execute 'reset role';
  select x.id,x.receipt_line_id into v_receipt_size,v_receipt_line
  from erp.laundry_receipt_batch_size_lines x
  join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
  where l.receipt_id=(v_response->>'receipt_id')::uuid;
  select row_version into v_group_version from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  perform public.erp_save_laundry_qc_action_v1('POST_FINAL_SKU',jsonb_build_object(
    'cutting_group_id',v_group,'destination_location_id',v_location,
    'physical_at','2026-09-07T11:00:00Z','reason','v20d mixed participants become FG',
    'good_qty_pcs',10,'completion_mode','ALL_READY','lines',jsonb_build_array(jsonb_build_object(
      'final_product_id',v_product,'qty_good_pcs',10,'qty_bs_pcs',0,
      'source_laundry_receipt_line_id',v_receipt_line,
      'source_laundry_receipt_batch_size_line_id',v_receipt_size
    ))
  ),gen_random_uuid(),v_group_version);
  execute 'reset role';

  select coalesce(sum(h.total_cost),0) into v_hpp
  from erp.hpp_versions h join erp.fg_lots f on f.id=h.lot_id
  where f.po_id=v_po and h.is_current;
  select coalesce(sum(l.debit-l.credit),0) into v_wip from erp.journal_lines l
  where l.po_id=v_po and l.account_id=erp.account_id('WIP');
  select coalesce(sum(l.debit-l.credit),0) into v_fg from erp.journal_lines l
  where l.po_id=v_po and l.account_id=erp.account_id('FG_INVENTORY');
  select accrued_amount into v_accrual from erp.laundry_cost_accrual_state where po_id=v_po;
  if v_hpp<>182 or v_wip<>0 or v_fg<>182 or v_accrual<>182
     or (select count(*) from erp.laundry_redispatch_participant_allocations a
       where a.successor_delivery_batch_size_line_id in(v_x2,v_x3))<>3
     or (select coalesce(sum(a.qty_pcs),0) from erp.laundry_redispatch_participant_allocations a
       where a.successor_delivery_batch_size_line_id=v_x2)<>6
     or (select coalesce(sum(a.qty_pcs),0) from erp.laundry_redispatch_participant_allocations a
       where a.successor_delivery_batch_size_line_id=v_x3)<>10
     or exists(select 1 from erp.run_v268_financial_report_checks()
       where issue_count>0 and severity='CRITICAL') then
    raise exception 'v20d adjacent multi-cycle cost continuity failed: HPP %, WIP %, FG %, accrual %',
      v_hpp,v_wip,v_fg,v_accrual;
  end if;
  raise notice 'CP6_V2620D_ADJACENT_MULTICYCLE_PASS %',jsonb_build_object(
    'hpp',v_hpp,'wip',v_wip,'fg',v_fg,'accrual',v_accrual,
    'lineage_intervals',3,'production_go',false
  );
end
$adjacent_partial_multicycle_redispatch$;

do $b02_b03_sale_return_rounding_and_reports$
declare
  v_po constant uuid:='c8c40000-0000-4000-8000-000000000001';
  v_group constant uuid:='c8c40000-0000-4000-8000-000000000003';
  v_batch constant uuid:='c8c40000-0000-4000-8000-000000000008';
  v_size constant uuid:='c8c10000-0000-4000-8000-000000000002';
  v_vendor constant uuid:='c8c20000-0000-4000-8000-000000000002';
  v_location constant uuid:='c8c20000-0000-4000-8000-000000000001';
  v_owner constant uuid:='c8c00000-0000-4000-8000-000000000001';
  v_process constant uuid:='c8f20000-0000-4000-8000-000000000001';
  v_product constant uuid:='c8f10000-0000-4000-8000-000000000001';
  v_customer constant uuid:='c8f10000-0000-4000-8000-000000000002';
  v_return constant uuid:='c8f10000-0000-4000-8000-000000000003';
  v_group_version bigint;
  v_delivery_version bigint;
  v_response jsonb;
  v_delivery uuid;
  v_delivery_size_line uuid;
  v_receipt_size_line uuid;
  v_receipt_line uuid;
  v_lot uuid;
  v_sale uuid;
  v_return_sale uuid;
  v_return_allocation uuid;
  v_return_item uuid:='c8f10000-0000-4000-8000-000000000004';
  v_report jsonb;
  v_today date:=current_date;
  v_sales uuid[]:='{}'::uuid[];
  v_adjustment uuid;
  v_book record;
  v_n integer;
  v_hpp numeric;
  v_fg numeric;
  v_cogs numeric;
  v_other numeric;
begin
  insert into erp.wash_processes(id,process_code,process_name,is_active)
  values(v_process,'CP6-V20D-CENTS','CP6 v20d cumulative-cent wash',true);
  insert into erp.laundry_vendor_rate_versions(
    vendor_id,wash_process_id,rate_per_pcs,effective_from,notes
  ) values(v_vendor,v_process,0.01,'2026-01-01','CP6 v20d one-cent fixture');
  insert into erp.products(
    id,sku,model_id,brand_id,color_name,size_id,product_name,
    identity_root_id,effective_from,is_active,is_portal_visible
  )
  select v_product,'CP6-V20D-CENTS',model_id,brand_id,'CP6-V20D-CENTS',size_id,
    'CP6 v20d cents product',v_product,effective_from,true,true
  from erp.products where id='c8c10000-0000-4000-8000-000000000004';
  insert into erp.accessory_bom_versions(
    product_id,version_label,effective_from,is_active,notes
  ) values(v_product,'CP6-V20D-EMPTY','2026-01-01',true,'Explicit empty BOM');
  insert into erp.customers(id,customer_code,customer_name,is_active)
  values(v_customer,'CP6-V20D-CUST','CP6 v20d rollback customer',true);

  select row_version into v_group_version
  from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_DELIVERY',jsonb_build_object(
      'distribution_batch_id',v_batch,'vendor_id',v_vendor,
      'wash_process_id',v_process,'target_dyeing_color','CP6-V20D-CENTS',
      'physical_at','2026-09-01T11:00:00Z',
      'reason','CP6 v20d fractional-cost dispatch','notes','rollback fixture',
      'lines',jsonb_build_array(jsonb_build_object(
        'size_id',v_size,'qty_sent_pcs',10
      ))
    ),gen_random_uuid(),v_group_version
  );
  execute 'reset role';
  v_delivery:=(v_response->>'delivery_id')::uuid;
  select d.row_version,x.id into v_delivery_version,v_delivery_size_line
  from erp.laundry_deliveries d
  join erp.laundry_delivery_lines l on l.delivery_id=d.id
  join erp.laundry_delivery_batch_size_lines x on x.delivery_line_id=l.id
  where d.id=v_delivery;

  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_FAILED_WASH',jsonb_build_object(
      'delivery_id',v_delivery,'wash_process_id',v_process,
      'custody_outcome','RETRY_AT_VENDOR',
      'physical_at','2026-09-01T12:00:00Z',
      'reason','CP6 v20d one participant failed once',
      'lines',jsonb_build_array(jsonb_build_object(
        'delivery_batch_size_line_id',v_delivery_size_line,'qty_attempted_pcs',1
      ))
    ),gen_random_uuid(),v_delivery_version
  );
  execute 'reset role';
  select row_version into v_delivery_version
  from erp.laundry_deliveries where id=v_delivery;

  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_RECEIPT',jsonb_build_object(
      'delivery_id',v_delivery,'wash_process_id',v_process,
      'physical_at','2026-09-02T11:00:00Z',
      'reason','CP6 v20d all fractional-cost pieces returned',
      'lines',jsonb_build_array(jsonb_build_object(
        'delivery_batch_size_line_id',v_delivery_size_line,
        'qty_good_received',10,'qty_bs_laundry',0,'bs_product_id',null
      ))
    ),gen_random_uuid(),v_delivery_version
  );
  execute 'reset role';
  select x.id,x.receipt_line_id into v_receipt_size_line,v_receipt_line
  from erp.laundry_receipt_batch_size_lines x
  join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
  where l.receipt_id=(v_response->>'receipt_id')::uuid;

  select row_version into v_group_version
  from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  perform public.erp_save_laundry_qc_action_v1(
    'POST_FINAL_SKU',jsonb_build_object(
      'cutting_group_id',v_group,'destination_location_id',v_location,
      'physical_at','2026-09-02T13:00:00Z',
      'reason','CP6 v20d fractional-cost final SKU',
      'good_qty_pcs',10,'completion_mode','ALL_READY',
      'lines',jsonb_build_array(jsonb_build_object(
        'final_product_id',v_product,'qty_good_pcs',10,'qty_bs_pcs',0,
        'source_laundry_receipt_line_id',v_receipt_line,
        'source_laundry_receipt_batch_size_line_id',v_receipt_size_line
      ))
    ),gen_random_uuid(),v_group_version
  );
  execute 'reset role';
  select id into v_lot from erp.fg_lots
  where po_id=v_po and product_id=v_product and lot_origin='PRODUCTION';
  select h.total_cost into v_hpp from erp.hpp_versions h
  where h.lot_id=v_lot and h.is_current;
  if v_hpp<>0.11 then
    raise exception 'v20d B03 fixture did not produce exact HPP 0.11: %',v_hpp;
  end if;

  for v_n in 1..10 loop
    v_response:=erp.save_sale_draft_v2(jsonb_build_object(
      'sale_number',format('CP6-V20D-SALE-%s-%s',v_n,gen_random_uuid()),
      'customer_id',v_customer,'source_location_id',v_location,
      'sale_date',format('2026-09-03T15:%s:00Z',lpad((v_n-1)::text,2,'0')),
      'reason','CP6 v20d cumulative-cent sale',
      'items',jsonb_build_array(jsonb_build_object(
        'product_id',v_product,'qty_pcs',1,
        'unit_price_snapshot',20,'discount_amount',0
      ))
    ),gen_random_uuid(),null);
    v_sale:=(v_response->>'sale_id')::uuid;
    v_sales:=array_append(v_sales,v_sale);
    perform erp.post_sale(v_sale);
    if v_n=1 then
      v_return_sale:=v_sale;
      select a.id into v_return_allocation
      from erp.sale_stock_allocations a
      join erp.sales_items i on i.id=a.sale_item_id
      where i.sale_id=v_sale and a.lot_id=v_lot;
    end if;
    if exists(
      select 1
      from erp.po_hpp_gl_state s
      cross join lateral erp.compute_po_hpp_gl_book_v2620d(s.po_id) b
      where s.po_id=v_po and(
        s.hpp_total_cost<>s.fg_value+s.cogs_value+s.other_out_value
        or s.fg_value<>b.fg_value or s.cogs_value<>b.cogs_value
        or s.other_out_value<>b.other_out_value
      )
    ) then
      raise exception 'v20d B03 cumulative target diverged at sale %',v_n;
    end if;
  end loop;

  perform erp.rebuild_po_hpp(v_po,'CP6 v20d repeat recost after ten sales');
  select s.fg_value,s.cogs_value into v_fg,v_cogs
  from erp.po_hpp_gl_state s where s.po_id=v_po;
  if v_fg<>0 or v_cogs<>0.11
     or (select coalesce(sum(m.qty_signed),0)
       from erp.fg_stock_movements m where m.lot_id=v_lot)<>0
     or (select coalesce(sum(l.debit-l.credit),0)
       from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('FG_INVENTORY'))<>0
     or (select coalesce(sum(l.debit-l.credit),0)
       from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('COGS'))<>0.11 then
    raise exception 'v20d B03 stranded a cent after sale/recost: FG %, COGS %',v_fg,v_cogs;
  end if;

  v_report:=erp.get_owner_financial_snapshot_v2(
    '2026-09-03','2026-09-03','2026-09-03'
  );
  if (v_report#>>'{performance,sales_revenue_gl}')::numeric<>200
     or (v_report#>>'{performance,operational_net_sales}')::numeric<>200
     or (v_report#>>'{performance,sales_revenue_bridge_delta}')::numeric<>0
     or v_report#>>'{data_confidence,status}'<>'READY' then
    raise exception 'v20d original Sale period did not reconcile: %',v_report;
  end if;

  insert into erp.sales_returns(
    id,return_number,sale_id,customer_id,physical_at,status,notes,created_by
  ) values(
    v_return,'CP6-V20D-RETURN-1',v_return_sale,v_customer,
    '2026-09-05T11:00:00Z','DRAFT','CP6 v20d one-piece return',v_owner
  );
  insert into erp.sales_return_items(
    id,return_id,sale_stock_allocation_id,product_id,lot_id,location_id,
    quality_grade,qty_pcs,unit_hpp_snapshot,refund_amount,notes
  ) values(
    v_return_item,v_return,v_return_allocation,v_product,v_lot,v_location,
    'GRADE_A',1,0,20,'CP6 v20d exact return lineage'
  );
  perform erp.post_sales_return(v_return);
  select s.fg_value,s.cogs_value into v_fg,v_cogs
  from erp.po_hpp_gl_state s where s.po_id=v_po;
  if v_fg<>0.01 or v_cogs<>0.10 then
    raise exception 'v20d sales return did not reverse the cumulative cent: FG %, COGS %',
      v_fg,v_cogs;
  end if;
  v_report:=erp.get_owner_financial_snapshot_v2(
    '2026-09-05','2026-09-05','2026-09-05'
  );
  if (v_report#>>'{performance,sales_revenue_gl}')::numeric<>-20
     or (v_report#>>'{performance,operational_net_sales}')::numeric<>-20
     or (v_report#>>'{performance,sales_revenue_bridge_delta}')::numeric<>0 then
    raise exception 'v20d original sales-return period did not reconcile: %',v_report;
  end if;

  perform erp.reverse_sales_return(v_return,'CP6 v20d cross-period return reversal');
  v_report:=erp.get_owner_financial_snapshot_v2(v_today,v_today,v_today);
  if (v_report#>>'{performance,sales_revenue_gl}')::numeric<>20
     or (v_report#>>'{performance,operational_net_sales}')::numeric<>20
     or (v_report#>>'{performance,sales_revenue_bridge_delta}')::numeric<>0 then
    raise exception 'v20d reversal-only sales-return period did not reconcile: %',v_report;
  end if;
  v_report:=erp.get_owner_financial_snapshot_v2(
    '2026-09-05','2026-09-05',v_today
  );
  if (v_report#>>'{performance,sales_revenue_gl}')::numeric<>-20
     or (v_report#>>'{performance,operational_net_sales}')::numeric<>-20 then
    raise exception 'v20d historical return period changed after later reversal: %',v_report;
  end if;

  perform erp.reverse_sale(v_return_sale,'CP6 v20d cross-period Sale reversal');
  select s.fg_value,s.cogs_value into v_fg,v_cogs
  from erp.po_hpp_gl_state s where s.po_id=v_po;
  if v_fg<>0.01 or v_cogs<>0.10 then
    raise exception 'v20d Sale reversal lost the cumulative cent: FG %, COGS %',v_fg,v_cogs;
  end if;
  v_report:=erp.get_owner_financial_snapshot_v2(v_today,v_today,v_today);
  if (v_report#>>'{performance,sales_revenue_gl}')::numeric<>0
     or (v_report#>>'{performance,operational_net_sales}')::numeric<>0
     or (v_report#>>'{performance,sales_revenue_bridge_delta}')::numeric<>0 then
    raise exception 'v20d combined reversal-only period did not reconcile: %',v_report;
  end if;
  v_report:=erp.get_owner_financial_snapshot_v2(
    '2026-09-03','2026-09-03','2026-09-03'
  );
  if (v_report#>>'{performance,sales_revenue_gl}')::numeric<>200
     or (v_report#>>'{performance,operational_net_sales}')::numeric<>200 then
    raise exception 'v20d historical Sale period changed after later reversal: %',v_report;
  end if;

  v_response:=erp.save_sale_draft_v2(jsonb_build_object(
    'sale_number',format('CP6-V20D-REPLACEMENT-%s',gen_random_uuid()),
    'customer_id',v_customer,'source_location_id',v_location,
    'sale_date',clock_timestamp(),
    'reason','CP6 v20d replacement after cross-period reversal',
    'items',jsonb_build_array(jsonb_build_object(
      'product_id',v_product,'qty_pcs',1,
      'unit_price_snapshot',20,'discount_amount',0
    ))
  ),gen_random_uuid(),null);
  perform erp.post_sale((v_response->>'sale_id')::uuid);
  select s.fg_value,s.cogs_value into v_fg,v_cogs
  from erp.po_hpp_gl_state s where s.po_id=v_po;
  if v_fg<>0 or v_cogs<>0.11
     or exists(select 1 from erp.run_v268_financial_report_checks()
       where check_name in(
         'V2620C_PO_HPP_TARGET_STATE_MISMATCH',
         'V2620C_PO_HPP_BOOK_MISMATCH',
         'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH'
       ) and issue_count>0)
     or exists(
       select 1 from erp.journal_entries e
       join erp.journal_lines l on l.journal_entry_id=e.id
       where e.status in('POSTED','REVERSED')
       group by e.id having sum(l.debit)<>sum(l.credit)
     ) then
    raise exception 'v20d sale/return/reversal/replacement lifecycle did not close: FG %, COGS %',
      v_fg,v_cogs;
  end if;
  v_report:=erp.get_owner_financial_snapshot_v2(
    '2026-09-03',v_today,v_today
  );
  if (v_report#>>'{performance,sales_revenue_gl}')::numeric<>200
     or (v_report#>>'{performance,operational_net_sales}')::numeric<>200
     or (v_report#>>'{performance,sales_revenue_bridge_delta}')::numeric<>0
     or v_report#>>'{data_confidence,status}'<>'READY' then
    raise exception 'v20d combined replacement lifecycle did not reconcile: %',v_report;
  end if;

  -- Adjacent rounding probe: restore five pieces, then dispose of those five
  -- through the real native FG adjustment posting path. Raw COGS and raw loss
  -- are both 0.055. Independent rounding would make each 0.06, strand FG
  -- at -0.01, and overstate total outflow. Cumulative bucket allocation must
  -- instead conserve 0.11 as FG 0.00 + COGS 0.06 + other expense 0.05.
  for v_n in 2..6 loop
    perform erp.reverse_sale(v_sales[v_n],
      'CP6 v20d mixed-outflow cumulative-rounding setup');
  end loop;
  v_response:=erp.save_fg_adjustment_draft_v2(jsonb_build_object(
    'adjustment_number',format('CP6-V20D-LOSS-%s',gen_random_uuid()),
    'location_id',v_location,'physical_at',clock_timestamp(),
    'reason_code','LOSS','reason','CP6 v20d mixed-outflow cumulative rounding',
    'change_reason','CP6 v20d adjacent mixed-outflow proof',
    'items',jsonb_build_array(jsonb_build_object(
      'lot_id',v_lot,'product_id',v_product,'quality_grade','GRADE_A',
      'qty_signed',-5,'notes','Real posted FG loss after five active sales'
    ))
  ),gen_random_uuid(),null);
  v_adjustment:=(v_response->>'fg_adjustment_id')::uuid;
  perform erp.post_fg_adjustment(v_adjustment);
  select s.fg_value,s.cogs_value,s.other_out_value
  into v_fg,v_cogs,v_other
  from erp.po_hpp_gl_state s where s.po_id=v_po;
  select * into v_book from erp.compute_po_hpp_gl_book_v2620d(v_po);
  if v_fg<>0 or v_cogs<>0.06 or v_other<>0.05
     or v_book.fg_value<>v_fg or v_book.cogs_value<>v_cogs
     or v_book.other_out_value<>v_other
     or v_fg+v_cogs+v_other<>0.11
     or (select coalesce(sum(m.qty_signed),0)
       from erp.fg_stock_movements m where m.lot_id=v_lot)<>0 then
    raise exception 'v20d mixed sale/loss rounding did not conserve exact book: FG %, COGS %, other %, book %',
      v_fg,v_cogs,v_other,row_to_json(v_book);
  end if;

  raise notice 'CP6_V2620D_B02_B03_LIFECYCLE_PASS %',jsonb_build_object(
    'mixed_outflow_fg',v_fg,'mixed_outflow_cogs',v_cogs,
    'mixed_outflow_other',v_other,
    'sale_reversal_period_net',0,'combined_replacement_revenue',200,
    'production_go',false
  );
end
$b02_b03_sale_return_rounding_and_reports$;

rollback;

do $v2620d_residue$
begin
  if exists(select 1 from erp.products where id='c8f10000-0000-4000-8000-000000000001')
     or exists(select 1 from erp.customers where id='c8f10000-0000-4000-8000-000000000002')
     or exists(select 1 from erp.sales_returns where id='c8f10000-0000-4000-8000-000000000003')
     or exists(select 1 from erp.wash_processes where id='c8f20000-0000-4000-8000-000000000001')
     or exists(select 1 from erp.laundry_redispatch_participant_allocations)
     or exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'CP6 v20d re-audit regression left transactional residue';
  end if;
  raise notice 'CP6_V2620D_REAUDIT_RESIDUE_ZERO';
end
$v2620d_residue$;
