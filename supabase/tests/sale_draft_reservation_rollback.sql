-- Transactional regression for all-day Sales Draft reservations.
-- PT001 rolls back every synthetic row after assertions finish.

create or replace function pg_temp.run_sale_draft_reservation_test()
returns jsonb
language plpgsql
as $test$
declare
  v_brand uuid := gen_random_uuid();
  v_model uuid := gen_random_uuid();
  v_size uuid := gen_random_uuid();
  v_product uuid := gen_random_uuid();
  v_location uuid := gen_random_uuid();
  v_customer uuid := gen_random_uuid();
  v_lot uuid := gen_random_uuid();
  v_sale_at timestamptz := clock_timestamp()-interval '1 day';
  v_cancel_at timestamptz := clock_timestamp()-interval '12 hours';
  v_create_req uuid := gen_random_uuid();
  v_edit_req uuid := gen_random_uuid();
  v_post_req uuid := gen_random_uuid();
  v_cancel_create_req uuid := gen_random_uuid();
  v_cancel_req uuid := gen_random_uuid();
  v_first jsonb;
  v_retry jsonb;
  v_edited jsonb;
  v_posted jsonb;
  v_post_retry jsonb;
  v_cancel_draft jsonb;
  v_cancelled jsonb;
  v_sale_id uuid;
  v_balance integer;
  v_active_reserve bigint;
  v_active_sale bigint;
  v_progress record;
  v_result jsonb;
begin
  begin
    insert into erp.brands(id,brand_code,brand_name)
    values(v_brand,'TST-SDR','Test Sale Draft Reserve');
    insert into erp.product_models(id,model_code,model_name)
    values(v_model,'TST-SDR-MODEL','Test Sale Draft Reserve Model');
    insert into erp.sizes(id,size_code,sort_order)
    values(v_size,'TST-SDR-SIZE',991);
    insert into erp.product_model_sizes(model_id,size_id,sort_order)
    values(v_model,v_size,1);
    insert into erp.products(
      id,sku,model_id,brand_id,color_name,size_id,product_name,
      identity_root_id,effective_from,is_active
    ) values(
      v_product,'TST-SDR-001',v_model,v_brand,'Test',v_size,'Test Sale Draft Product',
      v_product,clock_timestamp()-interval '3 days',true
    );
    insert into erp.locations(id,location_code,location_name,location_type)
    values(v_location,'TST-SDR-WH','Test Sale Draft Warehouse','FG_WAREHOUSE');
    insert into erp.customers(id,customer_code,customer_name)
    values(v_customer,'TST-SDR-CUST','Test Sale Draft Customer');
    insert into erp.fg_lots(
      id,lot_number,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,lot_origin
    ) values(
      v_lot,'TST-SDR-LOT',v_product,10,0,clock_timestamp()-interval '2 days','OTHER'
    );
    perform erp.post_fg_movement(
      v_product,v_lot,v_location,'GRADE_A','OPENING',10,0,null,
      'TEST_SEED',v_lot,clock_timestamp()-interval '2 days','Rollback-only FG seed',false
    );

    v_first:=erp.save_sale_draft_v2(
      jsonb_build_object(
        'sale_number','TST-SDR-SALE-1','customer_id',v_customer,
        'source_location_id',v_location,'sale_date',v_sale_at,
        'reason','Create rollback-only all-day Draft',
        'items',jsonb_build_array(jsonb_build_object(
          'product_id',v_product,'qty_pcs',4,'unit_price_snapshot',0,'discount_amount',0
        ))
      ),v_create_req,null
    );
    v_retry:=erp.save_sale_draft_v2(
      jsonb_build_object(
        'sale_number','TST-SDR-SALE-1','customer_id',v_customer,
        'source_location_id',v_location,'sale_date',v_sale_at,
        'reason','Create rollback-only all-day Draft',
        'items',jsonb_build_array(jsonb_build_object(
          'product_id',v_product,'qty_pcs',4,'unit_price_snapshot',0,'discount_amount',0
        ))
      ),v_create_req,null
    );
    v_sale_id:=(v_first->>'sale_id')::uuid;
    select cached_qty_pcs into v_balance from erp.fg_inventory_balances
    where product_id=v_product and location_id=v_location and quality_grade='GRADE_A';
    if v_balance<>6 then raise exception 'Draft reserve did not immediately reduce sellable stock: %',v_balance; end if;
    if v_retry is distinct from v_first then raise exception 'Draft save idempotency failed'; end if;

    v_edited:=erp.save_sale_draft_v2(
      jsonb_build_object(
        'sale_id',v_sale_id,'sale_number','TST-SDR-SALE-1','customer_id',v_customer,
        'source_location_id',v_location,'sale_date',v_sale_at,
        'reason','Increase rollback-only Draft from 4 to 6',
        'items',jsonb_build_array(jsonb_build_object(
          'product_id',v_product,'qty_pcs',6,'unit_price_snapshot',0,'discount_amount',0
        ))
      ),v_edit_req,(v_first->>'row_version')::bigint
    );
    select cached_qty_pcs into v_balance from erp.fg_inventory_balances
    where product_id=v_product and location_id=v_location and quality_grade='GRADE_A';
    select * into v_progress from erp.v_sale_reservation_progress where sale_id=v_sale_id;
    if v_balance<>4 or v_progress.item_qty_pcs<>6 or v_progress.allocated_qty_pcs<>6
       or v_progress.active_reserved_qty_pcs<>6 or v_progress.reservation_status<>'RESERVED' then
      raise exception 'Edited Draft reservation mismatch: balance %, progress %',v_balance,to_jsonb(v_progress);
    end if;

    v_posted:=erp.post_sale_v2(v_sale_id,v_post_req,(v_edited->>'row_version')::bigint);
    v_post_retry:=erp.post_sale_v2(v_sale_id,v_post_req,(v_edited->>'row_version')::bigint);
    select cached_qty_pcs into v_balance from erp.fg_inventory_balances
    where product_id=v_product and location_id=v_location and quality_grade='GRADE_A';
    select coalesce(sum(abs(m.qty_signed)),0) into v_active_reserve
    from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
    where i.sale_id=v_sale_id and m.movement_type='SALE_RESERVE'
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);
    select coalesce(sum(abs(m.qty_signed)),0) into v_active_sale
    from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
    where i.sale_id=v_sale_id and m.movement_type='SALE'
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);
    if v_posted is distinct from v_post_retry then raise exception 'Post sale idempotency failed'; end if;
    if v_balance<>4 or (v_posted->>'post_stock_delta_pcs')::integer<>0
       or v_active_reserve<>0 or v_active_sale<>6 then
      raise exception 'Post made a second stock movement or failed to convert reserve: balance %, reserve %, sale %, result %',
        v_balance,v_active_reserve,v_active_sale,v_posted;
    end if;

    perform erp.reverse_sale(v_sale_id,'Rollback test reverse posted invoice');
    select cached_qty_pcs into v_balance from erp.fg_inventory_balances
    where product_id=v_product and location_id=v_location and quality_grade='GRADE_A';
    if v_balance<>10 then raise exception 'Sale reversal did not restore FG: %',v_balance; end if;

    v_cancel_draft:=erp.save_sale_draft_v2(
      jsonb_build_object(
        'sale_number','TST-SDR-SALE-2','customer_id',v_customer,
        'source_location_id',v_location,'sale_date',v_cancel_at,
        'reason','Create Draft to test cancellation',
        'items',jsonb_build_array(jsonb_build_object(
          'product_id',v_product,'qty_pcs',2,'unit_price_snapshot',0,'discount_amount',0
        ))
      ),v_cancel_create_req,null
    );
    v_cancelled:=erp.cancel_sale_draft_v2(
      (v_cancel_draft->>'sale_id')::uuid,'Customer cancelled before store close',
      v_cancel_req,(v_cancel_draft->>'row_version')::bigint
    );
    select cached_qty_pcs into v_balance from erp.fg_inventory_balances
    where product_id=v_product and location_id=v_location and quality_grade='GRADE_A';
    if v_balance<>10 or v_cancelled->>'status'<>'CANCELLED'
       or (v_cancelled->>'released_qty_pcs')::integer<>2 then
      raise exception 'Draft cancellation did not release stock: balance %, result %',v_balance,v_cancelled;
    end if;

    v_result:=jsonb_build_object(
      'draft_immediate_balance',6,'edited_balance',4,'post_balance_unchanged',4,
      'post_stock_delta_pcs',0,'post_idempotent',v_post_retry=v_posted,
      'reverse_balance',10,'cancel_balance',v_balance,'test_data_persisted',false
    );
    raise exception using errcode='PT001',message='ROLLBACK_SALE_DRAFT_RESERVATION_TEST';
  exception when sqlstate 'PT001' then
    if sqlerrm<>'ROLLBACK_SALE_DRAFT_RESERVATION_TEST' then raise; end if;
    return v_result;
  end;
end;
$test$;

select pg_temp.run_sale_draft_reservation_test() as result;
