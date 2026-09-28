-- One physical identity for every historical row. Never distribute an imported aggregate.
CREATE OR REPLACE FUNCTION erp.bf_resolve_import_product_v1(p_batch uuid,p_value jsonb,p_allow_staged boolean DEFAULT false,p_optional boolean DEFAULT false)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_at timestamptz;v_ids uuid[];v_count integer;v_staged integer;v_id uuid;v_key text;
begin
 select cutover_at into strict v_at from erp.migration_batches where id=p_batch;
 if nullif(btrim(p_value->>'product_sku'),'') is null and nullif(btrim(p_value->>'product_id'),'') is null then
   if p_optional then return null;end if;raise exception 'BF_IMPORT_PRODUCT_REQUIRED';
 end if;
 v_id:=erp.bd_uuid_v1(p_value,'product_id',false);
 select coalesce(array_agg(p.id),'{}') into v_ids from erp.products p
 join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes z on z.id=p.size_id
 where p.effective_from<=v_at and (v_id is null or p.id=v_id)
   and (nullif(btrim(p_value->>'product_sku'),'') is null or lower(btrim(p.sku))=lower(btrim(p_value->>'product_sku')))
   and (nullif(btrim(p_value->>'size_code'),'') is null or lower(btrim(z.size_code))=lower(btrim(p_value->>'size_code')))
   and (nullif(btrim(p_value->>'brand_code'),'') is null or lower(btrim(b.brand_code))=lower(btrim(p_value->>'brand_code')))
   and (nullif(btrim(p_value->>'model_code'),'') is null or lower(btrim(m.model_code))=lower(btrim(p_value->>'model_code')))
   and (nullif(btrim(p_value->>'color_name'),'') is null or lower(btrim(p.color_name))=lower(btrim(p_value->>'color_name')));
 v_count:=cardinality(v_ids);v_staged:=0;
 if p_allow_staged and v_id is null then
   select count(*) into v_staged from erp.migration_staging_rows s
   where s.batch_id=p_batch and s.entity_type='PRODUCT' and s.validation_status='VALID'
     and lower(btrim(s.normalized_payload->>'sku'))=lower(btrim(p_value->>'product_sku'))
     and not exists(select 1 from unnest(array['size_code','brand_code','model_code','color_name']) k
       where nullif(btrim(p_value->>k),'') is not null and lower(btrim(s.normalized_payload->>k)) is distinct from lower(btrim(p_value->>k)))
     and not exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes z on z.id=p.size_id
       where p.id=any(v_ids) and lower(btrim(b.brand_code))=lower(btrim(s.normalized_payload->>'brand_code'))
       and lower(btrim(m.model_code))=lower(btrim(s.normalized_payload->>'model_code')) and lower(btrim(z.size_code))=lower(btrim(s.normalized_payload->>'size_code'))
       and lower(btrim(p.color_name))=lower(btrim(s.normalized_payload->>'color_name')));
 end if;
 if v_count+v_staged=0 then raise exception 'BF_IMPORT_PRODUCT_NOT_FOUND: identitas fisik tidak cocok pada cutover';end if;
 if v_count+v_staged<>1 then raise exception 'SIZE_ALLOCATION_REQUIRED: SKU punya % identitas; isi product_id atau size_code/merek/model/warna sumber historis',v_count+v_staged;end if;
 return v_ids[1];
end;$function$;
