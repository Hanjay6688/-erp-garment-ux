do $warehouse_preview$ begin
    if md5(pg_get_functiondef('erp.validate_migration_opening_stock_costs(uuid)'::regprocedure)) is distinct from '9a489942301b35e07154ea329bb13c3b'
       or (select proowner from pg_proc where oid='erp.validate_migration_opening_stock_costs(uuid)'::regprocedure) is distinct from 'postgres'::regrole::oid
    then raise exception 'Opening stock validator does not match the qualified source'; end if;
end $warehouse_preview$;
CREATE OR REPLACE FUNCTION erp.validate_migration_opening_stock_costs(p_batch_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r record;j jsonb;v_bt text;v_method text;v_product uuid;v_number numeric;v_status text;v_cutover timestamptz;v_count integer;
begin
  perform erp.require_owner_admin();
  select status into v_status from erp.migration_batches where id=p_batch_id for update;
  if v_status is null then raise exception 'Migration batch not found'; end if;
  if v_status not in('DRAFT','VALIDATING','READY','POSTING')
     or exists(select 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id and status<>'DRAFT') then
    raise exception 'AK_MIGRATION_PREVIEW_AFTER_POSTING_REFUSED';
  end if;
  select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_BALANCE_ITEM' and validation_status='VALID' loop
    begin
    j:=r.normalized_payload;v_bt:=upper(coalesce(j->>'balance_type',''));v_method:=coalesce(nullif(upper(j->>'hpp_input_method'),''),'MANUAL');
    if v_bt in('MATERIAL','FINISHED_GOODS') and nullif(btrim(j->>'unit_cost'),'') is not null then
      v_number:=(j->>'unit_cost')::numeric;
      if v_number<0 or v_number::text in('NaN','Infinity','-Infinity') then
        raise exception 'unit_cost must be finite and zero or positive';
      end if;
    end if;
    if v_bt='FINISHED_GOODS' and (j->>'qty')::numeric<>trunc((j->>'qty')::numeric) then
      raise exception 'FINISHED_GOODS qty must be whole PCS';
    end if;
    if v_bt='MATERIAL' and nullif(btrim(j->>'unit_cost'),'') is null then raise exception 'Migration opening MATERIAL row % wajib punya unit_cost (0 boleh)',r.source_row_no; end if;
    if v_bt='FINISHED_GOODS' then
      if v_method not in('MANUAL','PRICE_PERCENT') then raise exception 'Migration opening FG row % hpp_input_method harus MANUAL atau PRICE_PERCENT',r.source_row_no; end if;
      if v_method='MANUAL' and nullif(btrim(j->>'unit_cost'),'') is null then raise exception 'Migration opening FG row % wajib punya unit_cost atau PRICE_PERCENT',r.source_row_no; end if;
      if v_method='PRICE_PERCENT' and (nullif(j->>'hpp_percent_of_price','') is null or (j->>'hpp_percent_of_price')::numeric<=0) then raise exception 'Migration opening FG row % wajib punya hpp_percent_of_price > 0',r.source_row_no; end if;
    end if;
    if nullif(btrim(j->>'product_sku'),'') is not null then
      -- Same historical matching rule as resolve_opening_product_identity.
      -- New, valid staged roots are included without creating any master row.
      with candidates as (
        select p.id,lower(btrim(p.sku)) sku,lower(btrim(p.color_name)) color_name,
          lower(btrim(sz.size_code)) size_code,lower(btrim(pm.model_code)) model_code,
          lower(btrim(br.brand_code)) brand_code
        from erp.products p join erp.sizes sz on sz.id=p.size_id
        join erp.product_models pm on pm.id=p.model_id join erp.brands br on br.id=p.brand_id
        where p.effective_from<=v_cutover
        union all
        select null::uuid,lower(btrim(s.normalized_payload->>'sku')),
          lower(btrim(s.normalized_payload->>'color_name')),lower(btrim(s.normalized_payload->>'size_code')),
          lower(btrim(s.normalized_payload->>'model_code')),lower(btrim(s.normalized_payload->>'brand_code'))
        from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='PRODUCT'
          and s.validation_status='VALID' and not exists(
            select 1 from erp.products p join erp.brands br on br.id=p.brand_id join erp.sizes sz on sz.id=p.size_id
            where br.brand_code=s.normalized_payload->>'brand_code' and sz.size_code=s.normalized_payload->>'size_code'
              and lower(btrim(p.sku))=lower(btrim(s.normalized_payload->>'sku')))
      ) select count(*),(array_agg(id))[1] into v_count,v_product from candidates c
      where c.sku=lower(btrim(j->>'product_sku'))
        and (nullif(btrim(j->>'color_name'),'') is null or c.color_name=lower(btrim(j->>'color_name')))
        and (nullif(btrim(j->>'size_code'),'') is null or c.size_code=lower(btrim(j->>'size_code')))
        and (nullif(btrim(j->>'model_code'),'') is null or c.model_code=lower(btrim(j->>'model_code')))
        and (nullif(btrim(j->>'brand_code'),'') is null or c.brand_code=lower(btrim(j->>'brand_code')));
      if v_count<>1 then raise exception 'Opening product_sku must resolve exactly one identity at cutover (found %)',v_count; end if;
    end if;
    if v_bt='FINISHED_GOODS' then
      if nullif(btrim(j->>'location_code'),'') is null
         and (select count(*) from erp.locations where is_active and location_type='FG_WAREHOUSE')<>1 then
        raise exception 'Opening FG requires location when active FG warehouse count is not exactly one';
      end if;
      if v_method='PRICE_PERCENT' then
        if (j->>'hpp_percent_of_price')::numeric>1000 then raise exception 'Opening FG HPP percentage exceeds 1000'; end if;
        if v_product is null or erp.resolve_product_price_at(v_product,
          erp.product_opening_physical_at(v_product,(v_cutover at time zone 'Asia/Jakarta')::date)) is null then
          raise exception 'Opening FG selling price unavailable at cutover; use explicit manual HPP';
        end if;
      end if;
    end if;
    exception when others then
      update erp.migration_staging_rows
      set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm),
          updated_at=statement_timestamp()
      where id=r.id;
    end;
  end loop;
  -- Match the location that the master import will leave in effect when stock posts.
  -- A LOCATION in this batch takes precedence, including an explicit deactivation.
  with planned_locations as (
    select s.normalized_payload->>'location_code' as code,
           count(*)=1 and bool_and(case when s.validation_status='VALID' then
             upper(s.normalized_payload->>'location_type')='RAW_MATERIAL_WAREHOUSE'
               and coalesce(nullif(s.normalized_payload->>'is_active','')::boolean,true)
             else false end) as usable
      from erp.migration_staging_rows s
     where s.batch_id=p_batch_id and s.entity_type='LOCATION'
     group by s.normalized_payload->>'location_code'
  ), wrong_warehouse as (
    select s.id from erp.migration_staging_rows s
      left join planned_locations planned on planned.code=s.normalized_payload->>'location_code'
      left join erp.locations live on live.location_code=s.normalized_payload->>'location_code'
     where s.batch_id=p_batch_id and s.validation_status='VALID'
       and (s.entity_type='MATERIAL_ROLL' or
            (s.entity_type='OPENING_BALANCE_ITEM' and upper(s.normalized_payload->>'balance_type')='MATERIAL'))
       and case when planned.code is not null then planned.usable
                else live.is_active and live.location_type='RAW_MATERIAL_WAREHOUSE' end is not true
  )
  update erp.migration_staging_rows s
     set validation_status='ERROR',
         validation_errors=s.validation_errors||jsonb_build_array('location_code: pilih gudang bahan baku yang aktif untuk stok awal bahan atau roll.'),
         updated_at=statement_timestamp()
    from wrong_warehouse w where s.id=w.id;
  update erp.migration_batches b set
    status=case when exists(select 1 from erp.migration_staging_rows s
      where s.batch_id=b.id and s.validation_status<>'VALID') then 'DRAFT' else 'READY' end,
    validated_at=statement_timestamp(),
    error_message=case when exists(select 1 from erp.migration_staging_rows s
      where s.batch_id=b.id and s.validation_status='ERROR') then
      (select count(*) from erp.migration_staging_rows s where s.batch_id=b.id and s.validation_status='ERROR')||' staging row(s) failed validation'
      else null end
  where b.id=p_batch_id;
end$function$
;
do $warehouse_preview$ begin
    if md5(pg_get_functiondef('erp.validate_migration_opening_stock_costs(uuid)'::regprocedure)) is distinct from '694a3e8cfa70cbddca61ff4dd76fb9fa'
       or (select proowner from pg_proc where oid='erp.validate_migration_opening_stock_costs(uuid)'::regprocedure) is distinct from 'postgres'::regrole::oid
    then raise exception 'Opening stock validator does not match the qualified source'; end if;
end $warehouse_preview$;
