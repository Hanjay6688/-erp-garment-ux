-- On the seeded Enteng Uji fixture. Roll back every test document and request.
do $check_draft$
declare
  product_ uuid;
  location_ uuid;
  customer_ uuid;
  sale_ uuid;
  number_ text := 'UJI-DELTA-' || gen_random_uuid();
  physical_at_ timestamptz := statement_timestamp();
  version_ bigint;
  request_ uuid;
  qty integer;
  prior_qty integer := 0;
  before_ bigint;
  after_ bigint;
  physical_ bigint;
  reserved_ bigint;
  payload_ jsonb;
  reply_ jsonb;
  cases_ jsonb := '[]';
begin
  begin
    perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
    select id into strict product_ from erp.products where sku='UJI-NOTA-2830' and is_active;
    select id into strict location_ from erp.locations where location_code='UJI-NOTA-FG' and is_active;
    select id into strict customer_ from erp.customers where customer_code='UJI-NOTA-TOKO' and is_active;

    foreach qty in array array[4,3,3,5] loop
      select available_stock_qty_pcs into strict before_ from erp.v_fg_stock_position_v1
        where product_id=product_ and location_id=location_ and quality_grade='GRADE_A';
      payload_ := jsonb_build_object('sale_id',sale_, 'sale_number',number_, 'sale_date',physical_at_,
        'customer_id',customer_, 'source_location_id',location_, 'reason','Uji selisih reservasi aktif',
        'items',jsonb_build_array(jsonb_build_object('product_id',product_, 'qty_pcs',qty,
          'unit_price_snapshot',case when qty=prior_qty then 25 else 20 end)));
      request_ := gen_random_uuid();
      reply_ := erp.save_sale_draft_v2(payload_,request_,version_);
      if erp.save_sale_draft_v2(payload_,request_,version_) is distinct from reply_ then
        raise exception 'A retry returned a different draft receipt';
      end if;
      sale_ := (reply_->>'sale_id')::uuid;
      version_ := (reply_->>'row_version')::bigint;
      select available_stock_qty_pcs,physical_stock_qty_pcs,reserved_qty_pcs
        into strict after_,physical_,reserved_ from erp.v_fg_stock_position_v1
        where product_id=product_ and location_id=location_ and quality_grade='GRADE_A';
      if (reply_->>'sellable_stock_delta_pcs')::bigint is distinct from after_-before_
         or after_-before_ is distinct from prior_qty-qty
         or (reply_->>'released_previous_qty_pcs')::bigint is distinct from prior_qty
         or (reply_->>'reserved_qty_pcs')::bigint is distinct from qty
         or physical_<>10 or reserved_<>qty
         or exists(select from erp.journal_entries where source_id=sale_)
         or exists(select from erp.v_customer_receivables where sale_id=sale_ and outstanding_amount<>0)
      then raise exception 'Draft % to %: available % to %, receipt %',prior_qty,qty,before_,after_,reply_;
      end if;
      cases_ := cases_ || jsonb_build_array(jsonb_build_object('old_qty',prior_qty,'new_qty',qty,
        'available_before',before_,'available_after',after_,'reported_delta',reply_->'sellable_stock_delta_pcs'));
      prior_qty := qty;
    end loop;
    perform erp.cancel_sale_draft_v2(sale_,'Selesai uji selisih reservasi',gen_random_uuid(),version_);
    select available_stock_qty_pcs,reserved_qty_pcs into strict after_,reserved_ from erp.v_fg_stock_position_v1
      where product_id=product_ and location_id=location_ and quality_grade='GRADE_A';
    if after_<>physical_ or reserved_<>0 then raise exception 'Cancellation did not restore the fixture'; end if;
    raise exception using errcode='ZJ902', message='Rollback fixture';
  exception when sqlstate 'ZJ902' then null;
  end;
  if exists(select from erp.sales_headers where sale_number=number_) then
    raise exception 'A rollback test document remained';
  end if;
  perform set_config('writer_a.draft_delta_cases',cases_::text,true);
end $check_draft$;
select current_setting('writer_a.draft_delta_cases')::jsonb as cases;
