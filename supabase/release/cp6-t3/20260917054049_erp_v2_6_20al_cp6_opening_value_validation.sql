-- CP6 AL: complete opening values and typed row diagnostics.
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
  erp.material_cost_checkpoints,erp.cp6_v2620n_rollback_capsule,
  erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,
  erp.cp6_v2620q_rollback_capsule,erp.cp6_v2620r_rollback_capsule,
  erp.cp6_v2620s_rollback_capsule,erp.material_adjustments,
  erp.material_adjustment_items,erp.material_adjustment_revaluation_facts,
  erp.cp6_v2620t_rollback_capsule,erp.cp6_v2620u_rollback_capsule,
  erp.misc_finance_transactions,erp.misc_finance_categories,
  erp.cp6_v2620v_rollback_capsule,erp.scrap_batches,erp.scrap_sales,
  erp.cp6_v2620w_rollback_capsule,erp.app_roles,erp.app_role_permissions,erp.app_permissions,erp.cutting_bridge_execution_context,erp.bs_resolution_execution_context,erp.cp6_laundry_qc_execution_context
in share row exclusive mode;

do $lock_all_erp_v2620al$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620al_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620al$;


do $predecessor_v2620al$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20ak')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20al')
     or to_regclass('erp.cp6_v2620al_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ak_rollback_capsule') is null then raise exception 'AL_REQUIRES_EXACT_AK_WITHOUT_AL_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ak_cp6_import_reference_preview')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='20260917033516' and name='erp_v2_6_20ak_cp6_import_reference_preview'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='9d06a91bd849c80e1ef99a6ac8996863527a30ef3b4079188be58bd8f3d4311d')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260917033516')
     or (select count(*) from erp.cp6_v2620ak_rollback_capsule)<>8 then raise exception 'AL_REQUIRES_EXACT_AK_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    ('erp._validate_migration_batch_base(uuid)','cb72249e0a5ccc835d40c7468601a952a9387186545e34f13391bdf4a17ce0f7',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_opening_balance(uuid)','632075e17f4c59ceafe109059bb7105dca72b5b1fcc06e4ff67a9f050ee67543',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AL_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
end
$predecessor_v2620al$;

create table erp.cp6_v2620al_rollback_capsule(
  like erp.cp6_v2620ak_rollback_capsule including all
);
alter table erp.cp6_v2620al_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620al_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620al_rollback_capsule(
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
where p.oid in('erp._validate_migration_batch_base(uuid)'::regprocedure,'erp.post_opening_balance(uuid)'::regprocedure);


do $canonical_opening_v2620al$
begin
  execute $definition$CREATE OR REPLACE FUNCTION erp._validate_migration_batch_base(p_batch_id uuid)
 RETURNS TABLE(total_rows bigint, valid_rows bigint, error_rows bigint)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare r record;e jsonb;v_required text[];k text;v_total bigint;v_valid bigint;v_error bigint;v_bt text;v_material_type text;v_number numeric;v_status text;v_cutover timestamptz;ref record;v_code text;v_exists boolean;v_typed jsonb;
begin
  perform erp.require_owner_admin();
  select status into v_status from erp.migration_batches where id=p_batch_id for update;
  if v_status is null then raise exception 'Migration batch not found'; end if;
  if v_status not in('DRAFT','VALIDATING','READY','POSTING')
     or exists(select 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id and status<>'DRAFT') then
    raise exception 'AK_MIGRATION_PREVIEW_AFTER_POSTING_REFUSED';
  end if;
  select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id;
  update erp.migration_batches set status='VALIDATING',error_message=null where id=p_batch_id;
  update erp.migration_staging_rows set validation_status='PENDING',validation_errors='[]'::jsonb,updated_at=statement_timestamp() where batch_id=p_batch_id;
  update erp.migration_staging_rows s set validation_status='ERROR',validation_errors=jsonb_build_array('Duplicate legacy_key inside entity type'),updated_at=statement_timestamp()
  where s.batch_id=p_batch_id and s.legacy_key is not null and exists(select 1 from erp.migration_staging_rows d where d.batch_id=s.batch_id and d.entity_type=s.entity_type and d.legacy_key=s.legacy_key and d.id<>s.id);

  with keys as (
    select id,entity_type,case entity_type
      when 'PRODUCT' then jsonb_build_array(normalized_payload->>'brand_code',lower(btrim(normalized_payload->>'sku')),normalized_payload->>'size_code')
      else jsonb_build_array(normalized_payload->>case entity_type
        when 'BRAND' then 'brand_code' when 'SIZE' then 'size_code' when 'MODEL' then 'model_code'
        when 'CUSTOMER' then 'customer_code' when 'SUPPLIER' then 'supplier_code' when 'CONTRACTOR' then 'contractor_code'
        when 'ACCESSORY_CATEGORY' then 'category_code' when 'MATERIAL' then 'material_sku' when 'OPEN_PO' then 'po_number' end) end business_key
    from erp.migration_staging_rows where batch_id=p_batch_id and entity_type not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM')
  ) update erp.migration_staging_rows s set validation_status='ERROR',
      validation_errors=s.validation_errors||jsonb_build_array('Duplicate master/PO identity inside migration batch')
    where s.id in(select k.id from keys k where exists(select 1 from keys d
      where d.id<>k.id and d.entity_type=k.entity_type and d.business_key=k.business_key));

  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id order by case entity_type
      when 'BRAND' then 10 when 'SIZE' then 20 when 'MODEL' then 30
      when 'CUSTOMER' then 40 when 'SUPPLIER' then 50 when 'CONTRACTOR' then 60
      when 'ACCESSORY_CATEGORY' then 70 when 'MATERIAL' then 80 when 'MATERIAL_ROLL' then 85
      when 'PRODUCT' then 90 when 'OPEN_PO' then 100 else 110 end,source_row_no loop
    e:='[]'::jsonb;
    begin
      -- A malformed input is a row error. It must not roll back diagnostics
      -- for the entire batch or be accepted as NaN/infinite business quantity.
      foreach k in array array['qty','opening_qty','unit_cost','amount',
        'hpp_percent_of_price','target_qty_pcs','target_dozens'] loop
        if nullif(btrim(r.normalized_payload->>k),'') is not null then
          v_number:=(r.normalized_payload->>k)::numeric;
          if v_number::text in('NaN','Infinity','-Infinity') then
            e:=e||jsonb_build_array('Field must be a finite number: '||k);
          end if;
        end if;
      end loop;
    if jsonb_typeof(r.normalized_payload)<>'object' then e:=e||jsonb_build_array('normalized_payload must be a JSON object'); end if;
    v_required:=case r.entity_type
      when 'BRAND' then array['brand_code','brand_name']
      when 'SIZE' then array['size_code']
      when 'MODEL' then array['model_code','model_name']
      when 'PRODUCT' then array['sku','product_name','model_code','brand_code','color_name','size_code']
      when 'CUSTOMER' then array['customer_code','customer_name']
      when 'SUPPLIER' then array['supplier_code','supplier_name']
      when 'CONTRACTOR' then array['contractor_code','contractor_name']
      when 'ACCESSORY_CATEGORY' then array['category_code','category_name','base_uom_code']
      when 'MATERIAL' then array['material_sku','material_name','material_type','unit_code']
      when 'MATERIAL_ROLL' then array['material_sku','roll_number','opening_qty','unit_cost','location_code']
      when 'OPENING_BALANCE_ITEM' then array['balance_type']
      when 'OPEN_PO' then array['po_number','model_code','status','current_stage']
      else array[]::text[] end;
    foreach k in array v_required loop
      if nullif(trim(coalesce(r.normalized_payload->>k,'')),'') is null then e:=e||jsonb_build_array('Missing required field: '||k); end if;
    end loop;

    -- Validate only fields consumed by the matching writer. Composite casts
    -- enforce the actual column types/widths without inserting any master.
    -- Empty optional values retain the writers' existing default semantics.
    for ref in select * from(values
      ('BRAND','brands',array['brand_code','brand_name','is_active']),
      ('SIZE','sizes',array['size_code','sort_order','is_active']),
      ('MODEL','product_models',array['model_code','model_name','description','is_active']),
      ('PRODUCT','products',array['sku','product_name','color_name','is_active','is_portal_visible']),
      ('CUSTOMER','customers',array['customer_code','customer_name','phone','address','is_active']),
      ('SUPPLIER','suppliers',array['supplier_code','supplier_name','supplier_type','phone','address','is_active']),
      ('CONTRACTOR','contractors',array['contractor_code','contractor_name','contractor_type','attendance_required','is_active','notes']),
      ('ACCESSORY_CATEGORY','accessory_categories',array['category_code','category_name','base_uom_code','is_active','notes']),
      ('MATERIAL','materials',array['material_sku','material_name','material_type','unit_code','is_active']),
      ('MATERIAL_ROLL','material_rolls',array['roll_number','notes']),
      ('OPEN_PO','production_orders',array['po_number','target_qty_pcs','target_dozens','status','current_stage','physical_start_at','notes']),
      ('OPENING_BALANCE_ITEM','opening_balance_items',array['balance_type','qty','amount','stage','quality_grade','notes','hpp_input_method','hpp_percent_of_price'])
    ) fields(entity,relation_name,field_names) where fields.entity=r.entity_type loop
      select coalesce(jsonb_object_agg(field,r.normalized_payload->field),'{}'::jsonb)
        into v_typed from unnest(ref.field_names) field
        where nullif(r.normalized_payload->>field,'') is not null;
      begin
        execute format('select jsonb_populate_record(null::erp.%I,$1)',ref.relation_name) using v_typed;
      exception when data_exception then
        -- Retain the fast whole-row cast for valid imports. On a bad value,
        -- identify its field so the persisted row error tells the user what
        -- to repair; keep the original SQLSTATE and refusal semantics.
        for k in select jsonb_object_keys(v_typed) loop
          begin
            execute format('select jsonb_populate_record(null::erp.%I,$1)',ref.relation_name)
              using jsonb_build_object(k,v_typed->k);
          exception when data_exception then
            raise exception using errcode=sqlstate,message=format('%s: %s',k,sqlerrm);
          end;
        end loop;
        raise;
      end;
    end loop;
    if r.entity_type='SUPPLIER' and coalesce(nullif(upper(r.normalized_payload->>'supplier_type'),''),'MATERIAL')
      not in('MATERIAL','ACCESSORY','OTHER') then raise exception 'supplier_type must be MATERIAL, ACCESSORY or OTHER'; end if;
    if r.entity_type='OPEN_PO' then
      if nullif(r.normalized_payload->>'target_qty_pcs','') is not null
         and (r.normalized_payload->>'target_qty_pcs')::integer<=0 then raise exception 'target_qty_pcs must be positive'; end if;
      if nullif(r.normalized_payload->>'target_dozens','') is not null
         and (r.normalized_payload->>'target_dozens')::numeric<=0 then raise exception 'target_dozens must be positive'; end if;
    end if;
    if r.entity_type='MATERIAL_ROLL' then
      perform (r.normalized_payload->>'opening_qty')::numeric(18,6);
      perform (r.normalized_payload->>'unit_cost')::numeric(18,6);
    end if;
    if r.entity_type='OPENING_BALANCE_ITEM' then
      if nullif(r.normalized_payload->>'unit_cost','') is not null then
        perform (r.normalized_payload->>'unit_cost')::numeric(18,6);
      end if;
      if upper(r.normalized_payload->>'balance_type')='BS' then
        v_number:=nullif(r.normalized_payload->>'qty','')::numeric;
        if v_number is null or v_number<=0 or v_number<>trunc(v_number) or v_number>2147483647 then
          raise exception 'AL_BS_REQUIRES_POSITIVE_WHOLE_PCS';
        end if;
      end if;
      if upper(r.normalized_payload->>'balance_type')='WIP' then
        if nullif(r.normalized_payload->>'amount','') is null and
           (nullif(r.normalized_payload->>'qty','') is null or nullif(r.normalized_payload->>'unit_cost','') is null) then
          raise exception 'AL_WIP_REQUIRES_AMOUNT_OR_QTY_AND_COST';
        end if;
        foreach k in array array['qty','amount','unit_cost'] loop
          if nullif(r.normalized_payload->>k,'') is not null and (r.normalized_payload->>k)::numeric<0 then
            raise exception 'AL_WIP_VALUE_MUST_BE_NONNEGATIVE: %',k;
          end if;
        end loop;
      end if;
    end if;
    if r.entity_type='ACCESSORY_CATEGORY' and not exists(select 1 from erp.uom_definitions where unit_code=upper(r.normalized_payload->>'base_uom_code')) then e:=e||jsonb_build_array('Unknown base_uom_code'); end if;
    if r.entity_type='MATERIAL' then
      if upper(coalesce(r.normalized_payload->>'material_type','')) not in('FABRIC','ACCESSORY','OTHER') then e:=e||jsonb_build_array('material_type must be FABRIC, ACCESSORY or OTHER'); end if;
      if upper(coalesce(r.normalized_payload->>'material_type',''))='ACCESSORY' and nullif(trim(coalesce(r.normalized_payload->>'accessory_category_code','')),'') is null then e:=e||jsonb_build_array('ACCESSORY material requires accessory_category_code'); end if;
    end if;
    if r.entity_type='MATERIAL_ROLL' then
      if coalesce(nullif(r.normalized_payload->>'opening_qty','')::numeric,0)<=0 then e:=e||jsonb_build_array('MATERIAL_ROLL opening_qty must be positive'); end if;
      if coalesce(nullif(r.normalized_payload->>'unit_cost','')::numeric,-1)<0 then e:=e||jsonb_build_array('MATERIAL_ROLL unit_cost must be zero or positive'); end if;
      select material_type into v_material_type from erp.materials where material_sku=r.normalized_payload->>'material_sku';
      if v_material_type is null then
        select upper(s.normalized_payload->>'material_type') into v_material_type from erp.migration_staging_rows s
        where s.batch_id=p_batch_id and s.entity_type='MATERIAL' and s.normalized_payload->>'material_sku'=r.normalized_payload->>'material_sku' limit 1;
      end if;
      if coalesce(v_material_type,'')<>'FABRIC' then e:=e||jsonb_build_array('MATERIAL_ROLL requires a FABRIC material'); end if;
      if not exists(select 1 from erp.locations where location_code=r.normalized_payload->>'location_code' and location_type='RAW_MATERIAL_WAREHOUSE' and is_active=true) then e:=e||jsonb_build_array('MATERIAL_ROLL location_code must be an active raw-material warehouse'); end if;
      if nullif(trim(coalesce(r.normalized_payload->>'supplier_code','')),'') is not null
         and not exists(select 1 from erp.suppliers where supplier_code=r.normalized_payload->>'supplier_code')
         and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='SUPPLIER' and s.normalized_payload->>'supplier_code'=r.normalized_payload->>'supplier_code') then
        e:=e||jsonb_build_array('Unknown MATERIAL_ROLL supplier_code');
      end if;
      if exists(select 1 from erp.migration_staging_rows d where d.batch_id=p_batch_id and d.entity_type='MATERIAL_ROLL' and d.id<>r.id
                and d.normalized_payload->>'material_sku'=r.normalized_payload->>'material_sku' and d.normalized_payload->>'roll_number'=r.normalized_payload->>'roll_number') then
        e:=e||jsonb_build_array('Duplicate roll_number for material inside migration batch');
      end if;
      if exists(select 1 from erp.material_rolls mr join erp.materials m on m.id=mr.material_id where m.material_sku=r.normalized_payload->>'material_sku' and mr.roll_number=r.normalized_payload->>'roll_number' and mr.id is distinct from r.posted_entity_id) then
        e:=e||jsonb_build_array('MATERIAL_ROLL conflicts with an existing roll number');
      end if;
    end if;

    if r.entity_type='OPENING_BALANCE_ITEM' then
      v_bt:=upper(coalesce(r.normalized_payload->>'balance_type',''));
      if v_bt not in('MATERIAL','FINISHED_GOODS','WIP','BS','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','CUSTOMER_RECEIVABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE','CASH_BANK') then e:=e||jsonb_build_array('Unsupported opening balance_type for migration framework'); end if;
      if v_bt='MATERIAL' and(nullif(r.normalized_payload->>'material_sku','') is null or nullif(r.normalized_payload->>'location_code','') is null or coalesce(nullif(r.normalized_payload->>'qty','')::numeric,0)<=0) then e:=e||jsonb_build_array('MATERIAL opening needs material_sku, location_code and positive qty'); end if;
      if v_bt='MATERIAL' and exists(select 1 from erp.materials m where m.material_sku=r.normalized_payload->>'material_sku' and m.material_type='FABRIC') then e:=e||jsonb_build_array('FABRIC opening stock must use MATERIAL_ROLL rows, not anonymous MATERIAL opening'); end if;
      if v_bt='FINISHED_GOODS' and(nullif(r.normalized_payload->>'product_sku','') is null or coalesce(nullif(r.normalized_payload->>'qty','')::numeric,0)<=0) then e:=e||jsonb_build_array('FINISHED_GOODS opening needs product_sku and positive qty'); end if;
      if v_bt in('CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE') and(nullif(r.normalized_payload->>'contractor_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Contractor opening balance needs contractor_code and positive amount'); end if;
      if v_bt='CUSTOMER_RECEIVABLE' and(nullif(r.normalized_payload->>'customer_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Customer receivable opening needs customer_code and positive amount'); end if;
      if v_bt='SUPPLIER_PAYABLE' and(nullif(r.normalized_payload->>'supplier_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Supplier payable opening needs supplier_code and positive amount'); end if;
      if v_bt='VENDOR_PAYABLE' and(nullif(r.normalized_payload->>'vendor_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Vendor payable opening needs vendor_code and positive amount'); end if;
      if v_bt='CASH_BANK' and(nullif(r.normalized_payload->>'cash_account_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('CASH_BANK opening needs cash_account_code and positive amount'); end if;
    end if;
    if r.entity_type='OPEN_PO' then
      if upper(coalesce(r.normalized_payload->>'status','')) not in('DRAFT','CUTTING','SEWING','LAUNDRY','QC','FINISHED','ON_HOLD','CANCELLED') then e:=e||jsonb_build_array('Invalid PO status'); end if;
      if upper(coalesce(r.normalized_payload->>'current_stage','')) not in('CUTTING','SEWING','LAUNDRY','QC','FINISHED','ON_HOLD') then e:=e||jsonb_build_array('Invalid PO current_stage'); end if;
    end if;
    -- Topological order matches apply_migration_master_rows. A staged parent
    -- must itself be VALID; presence alone never proves a usable reference.
    for ref in select * from(values
      ('material_sku','materials','material_sku','MATERIAL',array['MATERIAL_ROLL','OPENING_BALANCE_ITEM']),
      ('model_code','product_models','model_code','MODEL',array['PRODUCT','OPEN_PO','OPENING_BALANCE_ITEM']),
      ('brand_code','brands','brand_code','BRAND',array['PRODUCT']),
      ('size_code','sizes','size_code','SIZE',array['PRODUCT']),
      ('accessory_category_code','accessory_categories','category_code','ACCESSORY_CATEGORY',array['MATERIAL']),
      ('unit_code','uom_definitions','unit_code',null,array['MATERIAL']),
      ('contractor_code','contractors','contractor_code','CONTRACTOR',array['OPEN_PO','OPENING_BALANCE_ITEM']),
      ('customer_code','customers','customer_code','CUSTOMER',array['OPENING_BALANCE_ITEM']),
      ('supplier_code','suppliers','supplier_code','SUPPLIER',array['MATERIAL_ROLL','OPENING_BALANCE_ITEM']),
      ('location_code','locations','location_code',null,array['MATERIAL_ROLL','OPENING_BALANCE_ITEM']),
      ('vendor_code','laundry_vendors','vendor_code',null,array['OPENING_BALANCE_ITEM']),
      ('cash_account_code','cash_accounts','cash_account_code',null,array['OPENING_BALANCE_ITEM'])
    ) refs(field,relation_name,code_field,staged_type,consumers)
    where r.entity_type=any(refs.consumers) loop
      v_code:=r.normalized_payload->>ref.field;
      if nullif(btrim(v_code),'') is null then continue; end if;
      if ref.field='unit_code' then v_code:=upper(v_code); end if;
      -- Identifiers are selected only from the constant allowlist above.
      execute format('select exists(select 1 from erp.%I where %I=$1)',ref.relation_name,ref.code_field)
        into v_exists using v_code;
      if not v_exists and not exists(select 1 from erp.migration_staging_rows s
        where s.batch_id=p_batch_id and s.entity_type=ref.staged_type
          and s.validation_status='VALID' and s.normalized_payload->>ref.code_field=v_code) then
        e:=e||jsonb_build_array('Unknown or invalid staged reference: '||ref.field||' = '||v_code);
      end if;
    end loop;
    if r.entity_type='OPENING_BALANCE_ITEM' and v_bt='MATERIAL'
       and exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id
         and s.entity_type='MATERIAL' and s.validation_status='VALID'
         and s.normalized_payload->>'material_sku'=r.normalized_payload->>'material_sku'
         and upper(s.normalized_payload->>'material_type')='FABRIC') then
      e:=e||jsonb_build_array('FABRIC opening stock must use MATERIAL_ROLL rows');
    end if;
    if r.entity_type='PRODUCT' then
      -- Import may maintain display data, never rewrite identity/history.
      if exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id
        join erp.sizes sz on sz.id=p.size_id join erp.product_models m on m.id=p.model_id
        where b.brand_code=r.normalized_payload->>'brand_code'
          and sz.size_code=r.normalized_payload->>'size_code'
          and lower(btrim(p.sku))=lower(btrim(r.normalized_payload->>'sku'))
      ) and not exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id
        join erp.sizes sz on sz.id=p.size_id join erp.product_models m on m.id=p.model_id
        where b.brand_code=r.normalized_payload->>'brand_code'
          and sz.size_code=r.normalized_payload->>'size_code'
          and lower(btrim(p.sku))=lower(btrim(r.normalized_payload->>'sku'))
          and p.effective_from<=v_cutover and (p.effective_to is null or p.effective_to>v_cutover)
          and m.model_code=r.normalized_payload->>'model_code'
          and lower(btrim(p.color_name))=lower(btrim(r.normalized_payload->>'color_name'))) then
        e:=e||jsonb_build_array('PRODUCT identity/history conflicts at migration cutover');
      end if;
    end if;
    exception when others then
      e:=e||jsonb_build_array('Invalid row value: '||sqlerrm);
    end;
    if r.validation_status='ERROR' and jsonb_array_length(r.validation_errors)>0 then e:=r.validation_errors||e; end if;
    update erp.migration_staging_rows set validation_status=case when jsonb_array_length(e)=0 then 'VALID' else 'ERROR' end,validation_errors=e,updated_at=statement_timestamp() where id=r.id;
  end loop;
  select count(*),count(*) filter(where validation_status='VALID'),count(*) filter(where validation_status='ERROR') into v_total,v_valid,v_error from erp.migration_staging_rows where batch_id=p_batch_id;
  update erp.migration_batches set status=case when v_error=0 then 'READY' else 'DRAFT' end,validated_at=statement_timestamp(),error_message=case when v_error=0 then null else v_error||' staging row(s) failed validation' end where id=p_batch_id;
  return query select v_total,v_valid,v_error;
end;$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.post_opening_balance(p_opening_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.opening_balance_headers%rowtype; r record; v_lot uuid; v_lot_no text; v_value numeric(24,6); v_unit_hpp numeric(20,6);
  v_debits numeric(24,6):=0; v_credits numeric(24,6):=0; v_lines jsonb:='[]'::jsonb; v_default_fg_location uuid; v_fg_count integer;
  v_product_at timestamptz;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  -- Serialize with staging before taking the header lock. A revalidated
  -- preview alone cannot revive the obsolete prepared lines removed by edit.
  perform 1 from erp.migration_batches b where b.id=(select migration_batch_id
    from erp.opening_balance_headers where id=p_opening_id) for update;
  if exists(select 1 from erp.migration_batches b join erp.opening_balance_headers opening_header on opening_header.migration_batch_id=b.id
    where opening_header.id=p_opening_id and (b.status not in('READY','POSTING') or exists(
      select 1 from erp.migration_staging_rows s where s.batch_id=b.id and s.validation_status<>'VALID'))) then
    raise exception 'AK_OPENING_REQUIRES_CURRENT_VALIDATED_BATCH';
  end if;
  select * into h from erp.opening_balance_headers where id=p_opening_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Opening balance must be DRAFT'; end if;
  if not exists(select 1 from erp.opening_balance_items where opening_id=h.id) then raise exception 'Opening balance has no lines'; end if;

  perform i.id from erp.opening_balance_items i
  where i.opening_id=h.id order by i.id for update;

  -- Ordinary opening items remain editable while DRAFT. Validate the latest
  -- locked rows before any stock, BS, subledger or journal side effect.
  for r in select * from erp.opening_balance_items where opening_id=h.id order by id loop
    if r.qty::text in('NaN','Infinity','-Infinity')
       or r.amount::text in('NaN','Infinity','-Infinity')
       or r.unit_cost_snapshot::text in('NaN','Infinity','-Infinity')
       or r.hpp_percent_of_price::text in('NaN','Infinity','-Infinity')
       or r.reference_sell_price_snapshot::text in('NaN','Infinity','-Infinity') then
      raise exception 'AL_OPENING_VALUES_MUST_BE_FINITE';
    end if;
    if r.balance_type='BS' and
       (r.qty is null or r.qty<=0 or r.qty<>trunc(r.qty) or r.qty>2147483647) then
      raise exception 'AL_BS_REQUIRES_POSITIVE_WHOLE_PCS';
    end if;
    if r.balance_type='WIP' then
      if r.amount is null and (r.qty is null or r.unit_cost_snapshot is null) then
        raise exception 'AL_WIP_REQUIRES_AMOUNT_OR_QTY_AND_COST';
      end if;
      if r.amount<0 or r.qty<0 or r.unit_cost_snapshot<0 then
        raise exception 'AL_WIP_VALUE_MUST_BE_NONNEGATIVE';
      end if;
    end if;
  end loop;
  if exists(
    select 1 from erp.opening_balance_items i
    where i.opening_id=h.id and i.roll_id is not null
      and i.balance_type<>'MATERIAL'
  ) then
    raise exception 'AE_OPENING_ROLL_ONLY_ALLOWED_FOR_MATERIAL';
  end if;
  if exists(
    select 1 from erp.opening_balance_items i
    where i.opening_id=h.id and i.balance_type='MATERIAL'
      and i.roll_id is not null
    group by i.roll_id having count(*)>1
  ) then
    raise exception 'AE_OPENING_ROLL_DUPLICATE_IN_DOCUMENT';
  end if;
  perform mr.id from erp.material_rolls mr
  where mr.id in(
    select i.roll_id from erp.opening_balance_items i
    where i.opening_id=h.id and i.roll_id is not null
  ) order by mr.id for update;
  for r in
    select i.*,m.material_type,
      mr.material_id as roll_material_id,
      mr.original_qty as roll_original_qty,
      mr.cached_qty as roll_cached_qty,
      mr.purchase_item_id as roll_purchase_item_id,
      mr.status as roll_status
    from erp.opening_balance_items i
    left join erp.materials m on m.id=i.material_id
    left join erp.material_rolls mr on mr.id=i.roll_id
    where i.opening_id=h.id and i.balance_type='MATERIAL'
    order by i.id
  loop
    if r.material_type='FABRIC' and r.roll_id is null then
      raise exception 'AE_FABRIC_OPENING_REQUIRES_ROLL';
    end if;
    if r.roll_id is not null then
      if r.material_type is distinct from 'FABRIC' then
        raise exception 'AE_OPENING_ROLL_REQUIRES_FABRIC';
      end if;
      if r.roll_material_id is distinct from r.material_id then
        raise exception 'AE_OPENING_ROLL_MATERIAL_MISMATCH';
      end if;
      if r.roll_status is distinct from 'AVAILABLE' then
        raise exception 'AE_OPENING_ROLL_NOT_AVAILABLE';
      end if;
      if r.roll_purchase_item_id is not null then
        raise exception 'AE_PURCHASE_ROLL_CANNOT_BE_OPENING_BALANCE';
      end if;
      if coalesce(r.qty,0)>r.roll_original_qty then
        raise exception 'AE_OPENING_QTY_EXCEEDS_ROLL_ORIGINAL';
      end if;
      if exists(
        select 1 from erp.opening_balance_items prior
        join erp.opening_balance_headers prior_h on prior_h.id=prior.opening_id
        where prior.roll_id=r.roll_id and prior_h.status='POSTED'
      ) then
        raise exception 'AE_OPENING_ROLL_ALREADY_POSTED';
      end if;
      if exists(select 1 from erp.material_stock_movements prior_m where prior_m.roll_id=r.roll_id)
         or coalesce(r.roll_cached_qty,0)<>0 then
        raise exception 'AE_OPENING_ROLL_HAS_EXISTING_STOCK_HISTORY';
      end if;
    end if;
  end loop;

  select count(*),(array_agg(id order by id))[1] into v_fg_count,v_default_fg_location from erp.locations where location_type='FG_WAREHOUSE' and is_active=true;
  for r in select * from erp.opening_balance_items where opening_id=h.id order by id loop
    if r.balance_type='MATERIAL' then
      if r.material_id is null or r.location_id is null or coalesce(r.qty,0)<=0 then raise exception 'Opening material needs material, location and positive qty'; end if;
      if r.unit_cost_snapshot is null or r.unit_cost_snapshot<0 then raise exception 'Opening material unit cost wajib diisi (0 boleh jika memang nilainya nol)'; end if;
      v_value:=r.qty*r.unit_cost_snapshot;
      insert into erp.material_stock_movements(material_id,roll_id,location_id,movement_type,qty_signed,input_unit_cost,unit_cost_snapshot,source_type,source_id,physical_at,created_by)
      values(r.material_id,r.roll_id,r.location_id,'OPENING',r.qty,r.unit_cost_snapshot,r.unit_cost_snapshot,'OPENING_BALANCE_ITEM',r.id,(h.opening_date::timestamp at time zone 'Asia/Jakarta'),erp.current_app_user_id());
      perform erp.recalculate_material_cost(r.material_id);
      if round(v_value,2)>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',round(v_value,2),'credit',0));v_debits:=v_debits+round(v_value,2);end if;
    elsif r.balance_type='FINISHED_GOODS' then
      if r.product_id is null or coalesce(r.qty,0)<=0 or trunc(r.qty)<>r.qty then raise exception 'Opening FG needs product and whole positive pcs qty'; end if;
      if r.location_id is null and v_fg_count<>1 then raise exception 'Opening FG requires location when active FG warehouse count is not exactly one'; end if;
      if r.hpp_input_method='MANUAL' and (r.unit_cost_snapshot is null or r.unit_cost_snapshot<0) then raise exception 'Opening FG HPP manual wajib diisi (0 boleh jika memang HPP nol), atau pilih %% dari harga jual'; end if;
      v_product_at:=erp.product_opening_physical_at(r.product_id,h.opening_date);
      v_unit_hpp:=erp.resolve_opening_fg_unit_hpp(r.id,h.opening_date);v_value:=r.qty*v_unit_hpp;
      v_lot_no:='OPEN-'||h.opening_number||'-'||substr(r.id::text,1,8);
      insert into erp.fg_lots(lot_number,po_id,qc_item_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin)
      values(v_lot_no,null,null,r.product_id,r.qty::integer,0,v_product_at,true,'OPENING') returning id into v_lot;
      insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,calculation_reason,created_by)
      values(v_lot,1,'ACTUAL',r.qty::integer,v_value,true,case when r.hpp_input_method='PRICE_PERCENT' then 'Opening FG HPP from selling price percentage snapshot' else 'Opening FG HPP' end,erp.current_app_user_id());
      perform erp.post_fg_movement(r.product_id,v_lot,coalesce(r.location_id,v_default_fg_location),coalesce(r.quality_grade,'GRADE_A'),'OPENING',r.qty::integer,v_unit_hpp,null,'OPENING_BALANCE_ITEM',r.id,v_product_at,'Opening finished goods',false);
      if round(v_value,2)>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY','debit',round(v_value,2),'credit',0,'product_id',r.product_id));v_debits:=v_debits+round(v_value,2);end if;
    elsif r.balance_type='WIP' then v_value:=coalesce(r.amount,coalesce(r.qty,0)*coalesce(r.unit_cost_snapshot,0));if round(v_value,2)>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','WIP','debit',round(v_value,2),'credit',0));v_debits:=v_debits+round(v_value,2);end if;
    elsif r.balance_type='BS' then
      if coalesce(r.qty,0)>0 and trunc(r.qty)=r.qty then
        if r.product_id is not null then v_product_at:=erp.product_opening_physical_at(r.product_id,h.opening_date); else v_product_at:=h.opening_date::timestamp at time zone 'Asia/Jakarta'; end if;
        insert into erp.bs_cases(bs_number,po_id,product_id,detected_at_stage,cause_source,untracked_type,responsible_contractor_id,qty_pcs,status,physical_at,notes)
        values('OBS-'||h.opening_number||'-'||substr(r.id::text,1,8),null,r.product_id,'UNKNOWN','UNKNOWN','LEGACY',r.contractor_id,r.qty::integer,'OPEN',v_product_at,r.notes);
      end if;
    elsif r.balance_type='CONTRACTOR_RECEIVABLE' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.contractor_id is null then raise exception 'Opening contractor receivable requires contractor and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',v_value,'credit',0,'contractor_id',r.contractor_id));v_debits:=v_debits+round(v_value,2);insert into erp.opening_subledger_balances(opening_item_id,party_type,direction,contractor_id,original_amount) values(r.id,'CONTRACTOR','RECEIVABLE',r.contractor_id,v_value);
    elsif r.balance_type='CONTRACTOR_PAYABLE' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.contractor_id is null then raise exception 'Opening contractor payable requires contractor and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_value,'contractor_id',r.contractor_id));v_credits:=v_credits+round(v_value,2);insert into erp.opening_subledger_balances(opening_item_id,party_type,direction,contractor_id,original_amount) values(r.id,'CONTRACTOR','PAYABLE',r.contractor_id,v_value);
    elsif r.balance_type='VENDOR_PAYABLE' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.vendor_id is null then raise exception 'Opening laundry vendor payable requires vendor and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',v_value,'vendor_id',r.vendor_id));v_credits:=v_credits+round(v_value,2);insert into erp.opening_subledger_balances(opening_item_id,party_type,direction,vendor_id,original_amount) values(r.id,'VENDOR','PAYABLE',r.vendor_id,v_value);
    elsif r.balance_type='SUPPLIER_PAYABLE' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.supplier_id is null then raise exception 'Opening material supplier payable requires supplier and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',0,'credit',v_value));v_credits:=v_credits+round(v_value,2);insert into erp.opening_subledger_balances(opening_item_id,party_type,direction,supplier_id,original_amount) values(r.id,'SUPPLIER','PAYABLE',r.supplier_id,v_value);
    elsif r.balance_type='CUSTOMER_RECEIVABLE' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.customer_id is null then raise exception 'Opening customer receivable requires customer and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','AR_CUSTOMER','debit',v_value,'credit',0,'customer_id',r.customer_id));v_debits:=v_debits+round(v_value,2);insert into erp.opening_subledger_balances(opening_item_id,party_type,direction,customer_id,original_amount) values(r.id,'CUSTOMER','RECEIVABLE',r.customer_id,v_value);
    elsif r.balance_type='CASH_BANK' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.cash_account_id is null then raise exception 'Opening cash/bank requires cash_account and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('account_id',(select coa_account_id from erp.cash_accounts where id=r.cash_account_id),'debit',v_value,'credit',0));v_debits:=v_debits+round(v_value,2);
    elsif r.balance_type='OTHER' then raise exception 'Generic OTHER opening balance is intentionally unsupported; use an explicit mapped balance type';
    end if;
  end loop;
  if v_debits>v_credits then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',round(v_debits-v_credits,2)));elsif v_credits>v_debits then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','OPENING_EQUITY','debit',round(v_credits-v_debits,2),'credit',0));end if;
  if jsonb_array_length(v_lines)>=2 then perform erp.post_journal('OPENING_BALANCE',h.id,h.opening_date,'ERP go-live opening balance',v_lines);end if;
  update erp.opening_balance_headers set status='POSTED' where id=h.id;
end$function$
$definition$;
end
$canonical_opening_v2620al$;

do $installed_v2620al$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620al_rollback_capsule)<>2 then
    raise exception 'AL_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620al_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp._validate_migration_batch_base(uuid)','cb72249e0a5ccc835d40c7468601a952a9387186545e34f13391bdf4a17ce0f7','95c8b9493b8cfb5ee719b6bb6501836c42457302661f59857dbcfc761033a412',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_opening_balance(uuid)','632075e17f4c59ceafe109059bb7105dca72b5b1fcc06e4ff67a9f050ee67543','16e667f49e6bb646d9a80cb30aa4080a0052b1ddc8bc760104c9c37c0e576d19',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620al_rollback_capsule
      where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'AL_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;

end
$installed_v2620al$;

do $boundary_v2620al$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620al_rollback_capsule') order by c.relname loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>224 then
    raise exception 'AL_FULL_ERP_BOUNDARY_CARDINALITY expected224 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620al_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620al$;

insert into erp.schema_migrations(version,description)
values('v2.6.20al','Opening BS and WIP values are checked before posting; master type errors persist per row');
commit;
