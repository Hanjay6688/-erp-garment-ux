-- Rehearse matched, partly matched and reversed invoices on one test receipt.
do $supplier_test$
declare
  label_ text := 'UJI-STATUS-' || left(gen_random_uuid()::text,8);
  supplier_ uuid;
  material_ uuid;
  warehouse_ uuid;
  purchase_ uuid;
  item_ uuid;
  invoice_ uuid;
  roll_ uuid;
  return_ uuid;
  return_reply_ jsonb;
  reply_ jsonb;
  scenario record;
  observed erp.v_material_purchase_liability_status%rowtype;
  results_ jsonb := '[]';
begin
  begin
    insert into erp.suppliers(supplier_code,supplier_name,supplier_type)
      values(label_,label_,'MATERIAL') returning id into supplier_;
    insert into erp.materials(material_sku,material_name,material_type,unit_code)
      values(label_,label_,'FABRIC','YARD') returning id into material_;
    insert into erp.locations(location_code,location_name,location_type)
      values(label_,label_,'RAW_MATERIAL_WAREHOUSE') returning id into warehouse_;
    reply_ := erp.save_material_purchase_draft_v2(jsonb_build_object(
      'purchase_number',label_, 'supplier_id',supplier_, 'location_id',warehouse_,
      'physical_at',statement_timestamp(), 'change_reason','Uji penerimaan dua roll kain',
      'lines',jsonb_build_array(jsonb_build_object('material_id',material_, 'qty',20,
        'unit_price',10, 'price_state','ESTIMATED', 'price_source','MANUAL_ESTIMATE',
        'rolls',jsonb_build_array(jsonb_build_object('roll_number',label_||'-A','qty',12),
          jsonb_build_object('roll_number',label_||'-B','qty',8))))),gen_random_uuid(),null);
    purchase_ := (reply_->>'purchase_id')::uuid;
    item_ := (reply_#>>'{lines,0,id}')::uuid;
    perform erp.post_material_purchase_v2(purchase_,gen_random_uuid(),(reply_->>'row_version')::bigint,'Uji penerimaan');

    for scenario in select * from (values
      ('seluruh',20,12.50,'UNPAID'),('sebagian',8,10,'UNPAID'),
      ('sebagian-gratis',8,0,'UNPAID'),('seluruh-gratis',20,0,'PAID')
    ) cases(name,qty,price,expected_status) loop
      reply_ := erp.save_material_supplier_invoice_draft_v2(jsonb_build_object(
        'invoice_number',label_||'-'||scenario.name, 'supplier_id',supplier_,
        'invoice_date',(statement_timestamp() at time zone 'Asia/Jakarta')::date,
        'change_reason','Uji tagihan kain', 'lines',jsonb_build_array(jsonb_build_object(
          'purchase_item_id',item_, 'qty_invoiced',scenario.qty, 'unit_price',scenario.price))),
        gen_random_uuid(),null);
      invoice_ := (reply_->>'supplier_invoice_id')::uuid;
      reply_ := erp.post_material_supplier_invoice_v2(invoice_,gen_random_uuid(),
        (reply_->>'row_version')::bigint,'Uji pengesahan tagihan kain');
      select * into strict observed from erp.v_material_purchase_liability_status where purchase_id=purchase_;
      if observed.payment_status is distinct from scenario.expected_status
        or observed.final_ap_amount is distinct from scenario.qty*scenario.price
        or observed.grni_estimated_amount is distinct from (20-scenario.qty)*10
      then raise exception 'Invoice % shows status %, AP %, GRNI %',scenario.name,
        observed.payment_status,observed.final_ap_amount,observed.grni_estimated_amount; end if;
      if scenario.name='sebagian' then
        select id into strict roll_ from erp.material_rolls where purchase_item_id=item_ and original_qty=12;
        return_reply_ := erp.save_material_supplier_return_draft_v2(jsonb_build_object(
          'return_number',label_||'-RET', 'supplier_id',supplier_, 'location_id',warehouse_,
          'physical_at',clock_timestamp(), 'change_reason','Uji retur bagian yang ditagih',
          'items',jsonb_build_array(jsonb_build_object('material_id',material_,'roll_id',roll_,
            'purchase_item_id',item_,'qty',8))),gen_random_uuid(),null);
        return_ := (return_reply_->>'material_supplier_return_id')::uuid;
        return_reply_ := erp.post_material_supplier_return_v2(return_,gen_random_uuid(),
          (return_reply_->>'row_version')::bigint,'Uji penyelesaian tagihan melalui retur');
        select * into strict observed from erp.v_material_purchase_liability_status where purchase_id=purchase_;
        if observed.final_ap_amount<>0 or observed.grni_estimated_amount<>120 or observed.payment_status<>'PAID'
        then raise exception 'A settled supplier return lost its cleared payment status'; end if;
        results_ := results_ || jsonb_build_array(jsonb_build_object('case','tagihan-lunas-dengan-retur',
          'status',observed.payment_status,'final_ap',observed.final_ap_amount,'grni',observed.grni_estimated_amount));
        perform erp.reverse_material_supplier_return_v2(return_,'Uji pembalikan retur supplier',
          gen_random_uuid(),(return_reply_->>'row_version')::bigint);
      end if;
      perform erp.reverse_material_supplier_invoice_v2(invoice_,'Uji pengembalian ke penerimaan',
        gen_random_uuid(),(reply_->>'row_version')::bigint);
      select * into strict observed from erp.v_material_purchase_liability_status where purchase_id=purchase_;
      if observed.payment_status is distinct from 'UNPAID' or observed.paid_amount<>0
        or observed.final_ap_amount<>0 or observed.grni_estimated_amount<>200
        or observed.active_invoice_numbers is not null
      then raise exception 'After reversing invoice %, status %, paid %, AP %, GRNI %',
        scenario.name,observed.payment_status,observed.paid_amount,observed.final_ap_amount,
        observed.grni_estimated_amount; end if;
      results_ := results_ || jsonb_build_array(jsonb_build_object('case',scenario.name,
        'invoice_status',scenario.expected_status, 'after_reversal',observed.payment_status,
        'after_reversal_grni',observed.grni_estimated_amount));
    end loop;
    raise exception using errcode='ZJ906', message='Rollback supplier regression';
  exception when sqlstate 'ZJ906' then null;
  end;
  if exists(select from erp.material_purchase_headers where purchase_number=label_) then
    raise exception 'Supplier regression left a receipt';
  end if;
  perform set_config('writer_a.supplier_status_cases',results_::text,true);
end $supplier_test$;
select current_setting('writer_a.supplier_status_cases')::jsonb as cases;
