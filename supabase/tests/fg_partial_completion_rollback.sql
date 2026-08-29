-- Transactional regression for erp.post_fg_partial_completion_v2.
-- The inner PT001 exception deliberately rolls back every synthetic business row.

create or replace function pg_temp.run_fg_partial_completion_test()
returns jsonb
language plpgsql
as $test$
declare
  v_brand uuid := gen_random_uuid();
  v_model uuid := gen_random_uuid();
  v_size uuid := gen_random_uuid();
  v_product uuid := gen_random_uuid();
  v_location uuid := gen_random_uuid();
  v_contractor uuid := gen_random_uuid();
  v_po uuid := gen_random_uuid();
  v_batch uuid := gen_random_uuid();
  v_group uuid := gen_random_uuid();
  v_slot uuid := gen_random_uuid();
  v_correction uuid := gen_random_uuid();
  v_req1 uuid := gen_random_uuid();
  v_req2 uuid := gen_random_uuid();
  v_req_stale uuid := gen_random_uuid();
  v_req_over uuid := gen_random_uuid();
  v_payload1 jsonb;
  v_payload2 jsonb;
  v_first jsonb;
  v_retry jsonb;
  v_second jsonb;
  v_partial_finish_blocked boolean := false;
  v_stale_blocked boolean := false;
  v_overpost_blocked boolean := false;
  v_progress record;
  v_stock_qty bigint;
  v_stock_events bigint;
  v_lots bigint;
  v_po_status text;
  v_result jsonb;
begin
  begin
    insert into erp.brands(id,brand_code,brand_name)
    values(v_brand,'TST-FGP','Test FG Partial');

    insert into erp.product_models(id,model_code,model_name)
    values(v_model,'TST-FGP-MODEL','Test FG Partial Model');

    insert into erp.sizes(id,size_code,sort_order)
    values(v_size,'TST-32',1);

    insert into erp.product_model_sizes(model_id,size_id,sort_order)
    values(v_model,v_size,1);

    insert into erp.products(
      id,sku,model_id,brand_id,color_name,size_id,product_name,
      identity_root_id,effective_from,is_active
    ) values(
      v_product,'TST-FGP-001',v_model,v_brand,'Test',v_size,'Test FG Partial Product',
      v_product,clock_timestamp()-interval '3 days',true
    );

    insert into erp.accessory_bom_versions(
      product_id,version_label,effective_from,is_active,notes
    ) values(
      v_product,'NO-ACCESSORY-TEST',clock_timestamp()-interval '3 days',true,
      'Empty BOM declaration for rolled-back partial FG test'
    );

    insert into erp.locations(id,location_code,location_name,location_type)
    values(v_location,'TST-FG-WH','Test FG Warehouse','FG_WAREHOUSE');

    insert into erp.contractors(
      id,contractor_code,contractor_name,contractor_type,attendance_required
    ) values(v_contractor,'TST-MANDOR','Test Mandor','MANDOR',false);

    insert into erp.production_orders(
      id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at
    ) values(
      v_po,'TST-PO-FGP',v_model,v_contractor,10,'SEWING','SEWING',
      clock_timestamp()-interval '2 days'
    );

    insert into erp.cutting_batches(
      id,po_id,batch_number,cut_at,status,notes
    ) values(
      v_batch,v_po,'TST-BATCH-1',clock_timestamp()-interval '2 days','OPEN','Rollback test'
    );

    insert into erp.cutting_groups(
      id,po_id,group_number,cut_at,picked_up_at,status,cutting_batch_id,notes
    ) values(
      v_group,v_po,'TST-GROUP-1',clock_timestamp()-interval '2 days',
      clock_timestamp()-interval '1 day','PICKED_UP',v_batch,'Rollback test'
    );

    insert into erp.cutting_group_size_slots(
      id,cutting_group_id,slot_no,size_id,drawing_no
    ) values(v_slot,v_group,1,v_size,1);

    insert into erp.cutting_qty_corrections(
      id,correction_number,cutting_batch_id,correction_type,reason_code,reason,physical_at
    ) values(
      v_correction,'TST-CORR-FGP',v_batch,'RECOUNT','TEST_SEED',
      'Create 10 effective pieces for rollback-only test',clock_timestamp()-interval '1 day'
    );

    insert into erp.cutting_qty_correction_lines(
      correction_id,cutting_group_id,size_slot_id,qty_delta_pcs,notes
    ) values(v_correction,v_group,v_slot,10,'Rollback-only seed');

    v_payload1 := jsonb_build_object(
      'cutting_group_id',v_group,
      'destination_location_id',v_location,
      'physical_at',clock_timestamp()-interval '2 hours',
      'reason','Test partial completion 4 of 10',
      'completion_mode','PARTIAL_SELECTION',
      'lines',jsonb_build_array(jsonb_build_object(
        'final_product_id',v_product,
        'qty_good_pcs',4,
        'qty_bs_pcs',0,
        'notes','First partial'
      ))
    );

    v_first := erp.post_fg_partial_completion_v2(v_payload1,v_req1,1);
    v_retry := erp.post_fg_partial_completion_v2(v_payload1,v_req1,1);

    begin
      perform erp.finish_production_order(v_po);
    exception when others then
      if sqlerrm like 'PO belum boleh FINISHED.%' then
        v_partial_finish_blocked := true;
      else
        raise;
      end if;
    end;

    v_payload2 := jsonb_build_object(
      'cutting_group_id',v_group,
      'destination_location_id',v_location,
      'physical_at',clock_timestamp()-interval '1 hour',
      'reason','Test final completion 6 of 10',
      'completion_mode','ALL_READY',
      'lines',jsonb_build_array(jsonb_build_object(
        'final_product_id',v_product,
        'qty_good_pcs',6,
        'qty_bs_pcs',0,
        'notes','Second partial'
      ))
    );

    begin
      perform erp.post_fg_partial_completion_v2(v_payload2,v_req_stale,1);
    exception when others then
      if sqlerrm like 'STALE_VERSION expected 1, current %' then
        v_stale_blocked := true;
      else
        raise;
      end if;
    end;

    v_second := erp.post_fg_partial_completion_v2(
      v_payload2,v_req2,(v_first->>'row_version')::bigint
    );

    begin
      perform erp.post_fg_partial_completion_v2(
        jsonb_build_object(
          'cutting_group_id',v_group,
          'destination_location_id',v_location,
          'physical_at',clock_timestamp()-interval '30 minutes',
          'reason','Test forbidden overpost',
          'lines',jsonb_build_array(jsonb_build_object(
            'final_product_id',v_product,
            'qty_good_pcs',1,
            'qty_bs_pcs',0
          ))
        ),
        v_req_over,
        (v_second->>'row_version')::bigint
      );
    exception when others then
      if sqlerrm like 'Qty penyelesaian melebihi sisa Potongan.%' then
        v_overpost_blocked := true;
      else
        raise;
      end if;
    end;

    select * into v_progress
    from erp.v_fg_partial_completion_progress
    where cutting_group_id=v_group;

    select coalesce(sum(qty_signed),0),count(*)
    into v_stock_qty,v_stock_events
    from erp.fg_stock_movements
    where movement_type='QC_GOOD'
      and source_id in (
        select i.id
        from erp.qc_inspection_items i
        join erp.qc_inspections q on q.id=i.inspection_id
        where q.po_id=v_po
      );

    select count(*) into v_lots
    from erp.fg_lots
    where po_id=v_po and lot_origin='PRODUCTION';

    perform erp.finish_production_order(v_po);
    select status into v_po_status from erp.production_orders where id=v_po;

    if v_retry is distinct from v_first then
      raise exception 'Idempotent retry returned a different response';
    end if;
    if v_first->>'completion_status' <> 'PARTIAL_SELECTION'
       or v_first->>'completion_mode' <> 'PARTIAL_SELECTION' then
      raise exception 'Intentional partial completion was not classified separately: %',v_first;
    end if;
    if not v_partial_finish_blocked then
      raise exception 'Partial PO close was not blocked';
    end if;
    if not v_stale_blocked then
      raise exception 'Stale version was not blocked';
    end if;
    if not v_overpost_blocked then
      raise exception 'Overposting was not blocked';
    end if;
    if v_progress.completion_status <> 'QC_COMPLETE'
       or v_progress.qc_accounted_qty_pcs <> 10
       or v_progress.remaining_qc_qty_pcs <> 0
       or v_progress.completion_count <> 2 then
      raise exception 'Unexpected cumulative progress: %',to_jsonb(v_progress);
    end if;
    if v_stock_qty <> 10 or v_stock_events <> 2 or v_lots <> 2 then
      raise exception 'Unexpected FG ledger: qty %, events %, lots %',
        v_stock_qty,v_stock_events,v_lots;
    end if;
    if v_po_status <> 'FINISHED' then
      raise exception 'PO did not close after complete accounting';
    end if;

    v_result := jsonb_build_object(
      'partial_first',v_first,
      'idempotent_retry_same',v_retry=v_first,
      'partial_finish_blocked',v_partial_finish_blocked,
      'stale_version_blocked',v_stale_blocked,
      'second_completion',v_second,
      'overpost_blocked',v_overpost_blocked,
      'final_progress',to_jsonb(v_progress),
      'fg_stock_qty_pcs',v_stock_qty,
      'fg_stock_event_count',v_stock_events,
      'fg_lot_count',v_lots,
      'po_status_after_complete',v_po_status,
      'test_data_persisted',false
    );

    raise exception using errcode='PT001',message='ROLLBACK_FG_PARTIAL_TEST';
  exception when sqlstate 'PT001' then
    if sqlerrm <> 'ROLLBACK_FG_PARTIAL_TEST' then
      raise;
    end if;
    return v_result;
  end;
end;
$test$;

select pg_temp.run_fg_partial_completion_test() as result;
