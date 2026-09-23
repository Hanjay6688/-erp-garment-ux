-- CP6 AK: complete reference preview and editable current opening drafts.
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

do $lock_all_erp_v2620ak$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620ak_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620ak$;


do $predecessor_v2620ak$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20aj')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20ak')
     or to_regclass('erp.cp6_v2620ak_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620aj_rollback_capsule') is null then raise exception 'AK_REQUIRES_EXACT_AJ_WITHOUT_AK_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20aj_cp6_rework_output_lineage')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='20260916202400' and name='erp_v2_6_20aj_cp6_rework_output_lineage'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='b36a6359c57ad59d93ea5cb8dc5f7e90a0dd9cd59d48c331b037aa365d400986')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260916202400')
     or (select count(*) from erp.cp6_v2620aj_rollback_capsule)<>6 then raise exception 'AK_REQUIRES_EXACT_AJ_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    ('erp._validate_migration_batch_base(uuid)','eb6fc2bc6cf419a72be75891d145782dbb1dec06186243834c2a444fc1fa9801',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.validate_migration_opening_stock_costs(uuid)','8223a856b0a0cd66d29a9eba31ebb6644434f934d910f184947a35ae0ffa77a0',array['postgres=X/postgres']::text[]),
    ('erp.prepare_migration_opening_balance(uuid,text)','89f419571e5de43434008e5090b1d4808089411ba839a53172354a145ec97323',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.apply_migration_master_rows(uuid)','6fd720835a487197a9b0d4b6246d9669ba5f472c7135993ab64cd5d9970eb1c9',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.apply_migration_open_pos(uuid)','49dd168a2dc3df0be6fcec9c962446d91e5724f9a838dc9616d894717c9844f7',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.finalize_migration_batch(uuid)','b2ca642c739fda50ffe2e5fb7d165e9a3370bcc55fad2e256c358d403f1436e3',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','0a35df9e1c385ca27f2c34f17de8e22023b58e2f6c42d9788260d0ebd69cecaa',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_opening_balance(uuid)','6460ab913c9a0614df6a622ff2a223df21c13d1361e14e6089c09375f7a95b40',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AK_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
end
$predecessor_v2620ak$;

create table erp.cp6_v2620ak_rollback_capsule(
  like erp.cp6_v2620aj_rollback_capsule including all
);
alter table erp.cp6_v2620ak_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ak_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ak_rollback_capsule(
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
where p.oid in('erp._validate_migration_batch_base(uuid)'::regprocedure,'erp.validate_migration_opening_stock_costs(uuid)'::regprocedure,'erp.prepare_migration_opening_balance(uuid,text)'::regprocedure,'erp.apply_migration_master_rows(uuid)'::regprocedure,'erp.apply_migration_open_pos(uuid)'::regprocedure,'erp.finalize_migration_batch(uuid)'::regprocedure,'erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)'::regprocedure,'erp.post_opening_balance(uuid)'::regprocedure);


do $canonical_opening_v2620ak$
begin
  execute $definition$CREATE OR REPLACE FUNCTION erp._validate_migration_batch_base(p_batch_id uuid)
 RETURNS TABLE(total_rows bigint, valid_rows bigint, error_rows bigint)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare r record;e jsonb;v_required text[];k text;v_total bigint;v_valid bigint;v_error bigint;v_bt text;v_material_type text;v_number numeric;v_status text;v_cutover timestamptz;ref record;v_code text;v_exists boolean;
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
  execute $definition$CREATE OR REPLACE FUNCTION erp.validate_migration_opening_stock_costs(p_batch_id uuid)
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
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.prepare_migration_opening_balance(p_batch_id uuid, p_opening_number text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare b erp.migration_batches%rowtype;r record;j jsonb;v_header uuid;v_material uuid;v_roll uuid;v_product uuid;v_model uuid;v_contractor uuid;v_customer uuid;v_location uuid;v_supplier uuid;v_vendor uuid;v_cash uuid;v_type text;v_number text;v_hpp_method text;v_hpp_pct numeric;
begin
  perform erp.require_owner_admin();select * into b from erp.migration_batches where id=p_batch_id for update;if b.id is null then raise exception 'Migration batch not found';end if;if b.status not in('READY','POSTING') then raise exception 'Migration batch must be READY/POSTING';end if;if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then raise exception 'Migration batch contains unvalidated/error rows';end if;
  if exists(select 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id) then select id into v_header from erp.opening_balance_headers where migration_batch_id=p_batch_id order by created_at limit 1;
    perform 1 from erp.opening_balance_headers where id=v_header for update;
    if exists(select 1 from erp.opening_balance_items where opening_id=v_header) then return v_header;end if;
    if (select status from erp.opening_balance_headers where id=v_header)<>'DRAFT' then raise exception 'AK_POSTED_OPENING_REBUILD_REFUSED';end if;
  end if;
  v_number:=coalesce(nullif(trim(p_opening_number),''),'MIG-'||b.batch_code);if v_header is null then insert into erp.opening_balance_headers(opening_number,opening_date,status,notes,created_by,migration_batch_id) values(v_number,(b.cutover_at AT TIME ZONE 'Asia/Jakarta')::date,'DRAFT','Prepared from migration batch '||b.batch_code,erp.current_app_user_id(),b.id) returning id into v_header;end if;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='MATERIAL_ROLL' and validation_status='VALID' order by source_row_no loop
    j:=r.normalized_payload;select m.id,mr.id into v_material,v_roll from erp.materials m join erp.material_rolls mr on mr.material_id=m.id where m.material_sku=j->>'material_sku' and mr.roll_number=j->>'roll_number';select id into v_location from erp.locations where location_code=j->>'location_code' and location_type='RAW_MATERIAL_WAREHOUSE' and is_active=true;if v_material is null or v_roll is null or v_location is null then raise exception 'MATERIAL_ROLL row % was not applied/resolved safely',r.source_row_no;end if;
    insert into erp.opening_balance_items(opening_id,balance_type,material_id,roll_id,location_id,qty,unit_cost_snapshot,notes) values(v_header,'MATERIAL',v_material,v_roll,v_location,(j->>'opening_qty')::numeric,(j->>'unit_cost')::numeric,coalesce(j->>'notes','Legacy roll opening row '||r.source_row_no));
  end loop;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_BALANCE_ITEM' and validation_status='VALID' order by source_row_no loop
    j:=r.normalized_payload;v_type:=upper(j->>'balance_type');v_material:=null;v_product:=null;v_model:=null;v_contractor:=null;v_customer:=null;v_location:=null;v_supplier:=null;v_vendor:=null;v_cash:=null;v_hpp_method:=coalesce(nullif(upper(j->>'hpp_input_method'),''),'MANUAL');v_hpp_pct:=nullif(j->>'hpp_percent_of_price','')::numeric;
    if nullif(trim(coalesce(j->>'material_sku','')),'') is not null then select id into v_material from erp.materials where material_sku=j->>'material_sku';if v_material is null then raise exception 'Opening row %: unknown material_sku %',r.source_row_no,j->>'material_sku';end if;end if;
    if nullif(trim(coalesce(j->>'product_sku','')),'') is not null then
      v_product:=erp.resolve_opening_product_identity(j->>'product_sku',b.cutover_at,j->>'color_name',j->>'size_code',j->>'model_code',j->>'brand_code');
    end if;
    if nullif(trim(coalesce(j->>'model_code','')),'') is not null then select id into v_model from erp.product_models where model_code=j->>'model_code';if v_model is null then raise exception 'Opening row %: unknown model_code %',r.source_row_no,j->>'model_code';end if;end if;
    if nullif(trim(coalesce(j->>'contractor_code','')),'') is not null then select id into v_contractor from erp.contractors where contractor_code=j->>'contractor_code';if v_contractor is null then raise exception 'Opening row %: unknown contractor_code %',r.source_row_no,j->>'contractor_code';end if;end if;
    if nullif(trim(coalesce(j->>'customer_code','')),'') is not null then select id into v_customer from erp.customers where customer_code=j->>'customer_code';if v_customer is null then raise exception 'Opening row %: unknown customer_code %',r.source_row_no,j->>'customer_code';end if;end if;
    if nullif(trim(coalesce(j->>'location_code','')),'') is not null then select id into v_location from erp.locations where location_code=j->>'location_code';if v_location is null then raise exception 'Opening row %: unknown location_code %',r.source_row_no,j->>'location_code';end if;end if;
    if nullif(trim(coalesce(j->>'supplier_code','')),'') is not null then select id into v_supplier from erp.suppliers where supplier_code=j->>'supplier_code';if v_supplier is null then raise exception 'Opening row %: unknown supplier_code %',r.source_row_no,j->>'supplier_code';end if;end if;
    if nullif(trim(coalesce(j->>'vendor_code','')),'') is not null then select id into v_vendor from erp.laundry_vendors where vendor_code=j->>'vendor_code';if v_vendor is null then raise exception 'Opening row %: unknown vendor_code %',r.source_row_no,j->>'vendor_code';end if;end if;
    if nullif(trim(coalesce(j->>'cash_account_code','')),'') is not null then select id into v_cash from erp.cash_accounts where cash_account_code=j->>'cash_account_code';if v_cash is null then raise exception 'Opening row %: unknown cash_account_code %',r.source_row_no,j->>'cash_account_code';end if;end if;
    insert into erp.opening_balance_items(opening_id,balance_type,material_id,product_id,model_id,contractor_id,customer_id,location_id,supplier_id,vendor_id,cash_account_id,stage,qty,amount,unit_cost_snapshot,quality_grade,notes,hpp_input_method,hpp_percent_of_price)
    values(v_header,v_type,v_material,v_product,v_model,v_contractor,v_customer,v_location,v_supplier,v_vendor,v_cash,nullif(j->>'stage',''),nullif(j->>'qty','')::numeric,nullif(j->>'amount','')::numeric,nullif(j->>'unit_cost','')::numeric,nullif(j->>'quality_grade',''),coalesce(j->>'notes','Legacy migration row '||r.source_row_no),case when v_type='FINISHED_GOODS' then v_hpp_method else 'MANUAL' end,case when v_type='FINISHED_GOODS' and v_hpp_method='PRICE_PERCENT' then v_hpp_pct else null end);
    update erp.migration_staging_rows set posted_entity_type='OPENING_BALANCE_HEADER',posted_entity_id=v_header,posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=r.id;
  end loop;return v_header;
end$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.apply_migration_master_rows(p_batch_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  r record;
  j jsonb;
  v_id uuid;
  v_model uuid;
  v_brand uuid;
  v_size uuid;
  v_category uuid;
  v_material uuid;
  v_supplier uuid;
  v_cutover timestamptz;
  v_count integer:=0;
  v_existing record;
begin
  perform erp.require_owner_admin();
  perform 1 from erp.migration_batches where id=p_batch_id for update;
  if not found then raise exception 'Migration batch not found'; end if;
  if (select status from erp.migration_batches where id=p_batch_id) not in('READY','POSTING') then
    raise exception 'Migration batch must be READY';
  end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then
    raise exception 'Migration batch contains unvalidated/error rows';
  end if;
  select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id;
  update erp.migration_batches set status='POSTING',error_message=null where id=p_batch_id;

  for r in
    select * from erp.migration_staging_rows
    where batch_id=p_batch_id and validation_status='VALID' and posted_entity_id is null
      and entity_type in(
        'BRAND','SIZE','MODEL','CUSTOMER','SUPPLIER','CONTRACTOR',
        'ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','PRODUCT'
      )
    order by case entity_type
      when 'BRAND' then 10 when 'SIZE' then 20 when 'MODEL' then 30
      when 'CUSTOMER' then 40 when 'SUPPLIER' then 50 when 'CONTRACTOR' then 60
      when 'ACCESSORY_CATEGORY' then 70 when 'MATERIAL' then 80
      when 'MATERIAL_ROLL' then 85 when 'PRODUCT' then 90 else 999 end,
      source_row_no
  loop
    j:=r.normalized_payload;
    v_id:=null;
    case r.entity_type
      when 'BRAND' then
        insert into erp.brands(brand_code,brand_name,is_active)
        values(j->>'brand_code',j->>'brand_name',coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(brand_code) do update set
          brand_name=excluded.brand_name,is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'SIZE' then
        insert into erp.sizes(size_code,sort_order,is_active)
        values(j->>'size_code',coalesce(nullif(j->>'sort_order','')::integer,0),
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(size_code) do update set
          sort_order=excluded.sort_order,is_active=excluded.is_active
        returning id into v_id;
      when 'MODEL' then
        insert into erp.product_models(model_code,model_name,description,is_active)
        values(j->>'model_code',j->>'model_name',j->>'description',
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(model_code) do update set
          model_name=excluded.model_name,description=excluded.description,
          is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'CUSTOMER' then
        insert into erp.customers(customer_code,customer_name,phone,address,is_active)
        values(j->>'customer_code',j->>'customer_name',j->>'phone',j->>'address',
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(customer_code) do update set
          customer_name=excluded.customer_name,phone=excluded.phone,address=excluded.address,
          is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'SUPPLIER' then
        insert into erp.suppliers(
          supplier_code,supplier_name,supplier_type,phone,address,is_active
        ) values(
          j->>'supplier_code',j->>'supplier_name',
          coalesce(nullif(upper(j->>'supplier_type'),''),'MATERIAL'),
          j->>'phone',j->>'address',coalesce(nullif(j->>'is_active','')::boolean,true)
        )
        on conflict(supplier_code) do update set
          supplier_name=excluded.supplier_name,supplier_type=excluded.supplier_type,
          phone=excluded.phone,address=excluded.address,is_active=excluded.is_active
        returning id into v_id;
      when 'CONTRACTOR' then
        insert into erp.contractors(
          contractor_code,contractor_name,contractor_type,attendance_required,is_active,notes
        ) values(
          j->>'contractor_code',j->>'contractor_name',
          coalesce(nullif(upper(j->>'contractor_type'),''),'MANDOR'),
          coalesce(nullif(j->>'attendance_required','')::boolean,true),
          coalesce(nullif(j->>'is_active','')::boolean,true),j->>'notes'
        )
        on conflict(contractor_code) do update set
          contractor_name=excluded.contractor_name,contractor_type=excluded.contractor_type,
          attendance_required=excluded.attendance_required,is_active=excluded.is_active,
          notes=excluded.notes,updated_at=statement_timestamp()
        returning id into v_id;
      when 'ACCESSORY_CATEGORY' then
        insert into erp.accessory_categories(
          category_code,category_name,base_uom_code,is_active,notes
        ) values(
          j->>'category_code',j->>'category_name',upper(j->>'base_uom_code'),
          coalesce(nullif(j->>'is_active','')::boolean,true),j->>'notes'
        )
        on conflict(category_code) do update set
          category_name=excluded.category_name,is_active=excluded.is_active,
          notes=excluded.notes,updated_at=statement_timestamp()
        returning id into v_id;
      when 'MATERIAL' then
        v_category:=null;
        if nullif(btrim(coalesce(j->>'accessory_category_code','')),'') is not null then
          select id into v_category from erp.accessory_categories
          where category_code=j->>'accessory_category_code';
          if v_category is null then
            raise exception 'Unknown accessory category % for material %',
              j->>'accessory_category_code',j->>'material_sku';
          end if;
        end if;
        insert into erp.materials(
          material_sku,material_name,material_type,unit_code,accessory_category_id,is_active
        ) values(
          j->>'material_sku',j->>'material_name',upper(j->>'material_type'),
          upper(j->>'unit_code'),v_category,
          coalesce(nullif(j->>'is_active','')::boolean,true)
        )
        on conflict(material_sku) do update set
          material_name=excluded.material_name,
          accessory_category_id=excluded.accessory_category_id,
          is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'MATERIAL_ROLL' then
        select id into v_material from erp.materials
        where material_sku=j->>'material_sku' and material_type='FABRIC';
        if v_material is null then
          raise exception 'MATERIAL_ROLL material % is not a FABRIC material',j->>'material_sku';
        end if;
        v_supplier:=null;
        if nullif(btrim(coalesce(j->>'supplier_code','')),'') is not null then
          select id into v_supplier from erp.suppliers where supplier_code=j->>'supplier_code';
          if v_supplier is null then
            raise exception 'Unknown supplier % for roll %',j->>'supplier_code',j->>'roll_number';
          end if;
        end if;
        if exists(select 1 from erp.material_rolls
          where material_id=v_material and roll_number=j->>'roll_number') then
          raise exception 'Migration roll already exists for material %, roll %',
            j->>'material_sku',j->>'roll_number';
        end if;
        insert into erp.material_rolls(
          material_id,purchase_item_id,supplier_id,roll_number,original_qty,
          cached_qty,status,received_at,notes
        ) values(
          v_material,null,v_supplier,j->>'roll_number',(j->>'opening_qty')::numeric,
          0,'AVAILABLE',v_cutover,coalesce(j->>'notes','Legacy roll at migration cutover')
        ) returning id into v_id;
      when 'PRODUCT' then
        select id into v_model from erp.product_models where model_code=j->>'model_code';
        select id into v_brand from erp.brands where brand_code=j->>'brand_code';
        select id into v_size from erp.sizes where size_code=j->>'size_code';
        if v_model is null or v_brand is null or v_size is null then
          raise exception 'Product % has unresolved model/brand/size mapping',j->>'sku';
        end if;
        insert into erp.product_model_sizes(model_id,size_id)
        values(v_model,v_size) on conflict(model_id,size_id) do nothing;

        select p.* into v_existing
        from erp.products p
        where p.brand_id=v_brand
          and lower(btrim(p.sku))=lower(btrim(j->>'sku'))
          and p.size_id=v_size
          and p.effective_from<=v_cutover
          and(p.effective_to is null or p.effective_to>v_cutover)
        order by p.effective_from desc,p.id desc limit 1;

        if v_existing.id is null then
          if exists(
            select 1 from erp.products p
            where p.brand_id=v_brand
              and lower(btrim(p.sku))=lower(btrim(j->>'sku'))
              and p.size_id=v_size
          ) then
            raise exception 'Migration product % already has identity history for brand % / size % but no version valid at cutover %. Do not guess a historical version; fix migration mapping/effective dates first.',
              j->>'sku',j->>'brand_code',j->>'size_code',v_cutover;
          end if;
          insert into erp.products(
            sku,model_id,brand_id,color_name,size_id,product_name,
            is_portal_visible,is_active,effective_from
          ) values(
            j->>'sku',v_model,v_brand,j->>'color_name',v_size,j->>'product_name',
            coalesce(nullif(j->>'is_portal_visible','')::boolean,true),
            coalesce(nullif(j->>'is_active','')::boolean,true),v_cutover
          ) returning id into v_id;
        else
          if v_existing.model_id is distinct from v_model
             or v_existing.brand_id is distinct from v_brand
             or lower(btrim(v_existing.color_name)) is distinct from lower(btrim(j->>'color_name'))
             or v_existing.size_id is distinct from v_size then
            raise exception 'Migration product % identity differs from the brand + SKU version already valid at cutover. Use controlled identity-version mapping instead of overwriting history.',j->>'sku';
          end if;
          v_id:=v_existing.id;
          update erp.products set
            product_name=j->>'product_name',
            is_portal_visible=coalesce(nullif(j->>'is_portal_visible','')::boolean,true),
            is_active=coalesce(nullif(j->>'is_active','')::boolean,true),updated_at=statement_timestamp()
          where id=v_id;
        end if;
    end case;
    update erp.migration_staging_rows set
      posted_entity_type=r.entity_type,posted_entity_id=v_id,
      posted_at=statement_timestamp(),updated_at=statement_timestamp()
    where id=r.id;
    v_count:=v_count+1;
  end loop;
  return v_count;
end
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.apply_migration_open_pos(p_batch_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$ DECLARE b erp.migration_batches%ROWTYPE;r record;j jsonb;v_model uuid;v_contractor uuid;v_id uuid;v_count integer:=0; BEGIN PERFORM erp.require_owner_admin();SELECT * INTO b FROM erp.migration_batches WHERE id=p_batch_id FOR UPDATE; IF b.id IS NULL THEN RAISE EXCEPTION 'Migration batch not found'; END IF; IF b.status NOT IN ('READY','POSTING') THEN RAISE EXCEPTION 'Migration batch must be READY/POSTING'; END IF; IF EXISTS(SELECT 1 FROM erp.migration_staging_rows WHERE batch_id=p_batch_id AND validation_status<>'VALID') THEN RAISE EXCEPTION 'Migration batch contains unvalidated/error rows'; END IF; UPDATE erp.migration_batches SET status='POSTING' WHERE id=p_batch_id; FOR r IN SELECT * FROM erp.migration_staging_rows WHERE batch_id=p_batch_id AND entity_type='OPEN_PO' AND validation_status='VALID' AND posted_entity_id IS NULL ORDER BY source_row_no LOOP j:=r.normalized_payload;SELECT id INTO v_model FROM erp.product_models WHERE model_code=j->>'model_code'; IF v_model IS NULL THEN RAISE EXCEPTION 'OPEN_PO row %: unknown model %',r.source_row_no,j->>'model_code'; END IF;v_contractor:=NULL; IF NULLIF(trim(COALESCE(j->>'contractor_code','')),'') IS NOT NULL THEN SELECT id INTO v_contractor FROM erp.contractors WHERE contractor_code=j->>'contractor_code'; IF v_contractor IS NULL THEN RAISE EXCEPTION 'OPEN_PO row %: unknown contractor %',r.source_row_no,j->>'contractor_code'; END IF; END IF;SELECT id INTO v_id FROM erp.production_orders WHERE po_number=j->>'po_number'; IF v_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM erp.production_orders WHERE id=v_id AND is_legacy=true AND migration_batch_id=p_batch_id) THEN RAISE EXCEPTION 'OPEN_PO row % conflicts with an existing non-migration PO number %',r.source_row_no,j->>'po_number'; END IF;v_id:=NULL;INSERT INTO erp.production_orders(po_number,model_id,contractor_id,target_qty_pcs,target_dozens,status,current_stage,physical_start_at,notes,migration_batch_id,is_legacy,legacy_reference,created_by) VALUES (j->>'po_number',v_model,v_contractor,NULLIF(j->>'target_qty_pcs','')::integer,NULLIF(j->>'target_dozens','')::numeric,upper(j->>'status'),upper(j->>'current_stage'),NULLIF(j->>'physical_start_at','')::timestamptz,COALESCE(j->>'notes','Migrated open PO'),p_batch_id,true,COALESCE(r.legacy_key,j->>'po_number'),erp.current_app_user_id()) ON CONFLICT (po_number) DO UPDATE SET contractor_id=EXCLUDED.contractor_id,target_qty_pcs=EXCLUDED.target_qty_pcs,target_dozens=EXCLUDED.target_dozens,status=EXCLUDED.status,current_stage=EXCLUDED.current_stage,physical_start_at=EXCLUDED.physical_start_at,notes=EXCLUDED.notes,migration_batch_id=EXCLUDED.migration_batch_id,is_legacy=true,legacy_reference=EXCLUDED.legacy_reference,updated_at=statement_timestamp() WHERE production_orders.is_legacy=true AND production_orders.migration_batch_id=p_batch_id RETURNING id INTO v_id; IF v_id IS NULL THEN RAISE EXCEPTION 'OPEN_PO row % could not be applied safely',r.source_row_no; END IF;UPDATE erp.migration_staging_rows SET posted_entity_type='PRODUCTION_ORDER',posted_entity_id=v_id,posted_at=statement_timestamp(),updated_at=statement_timestamp() WHERE id=r.id;v_count:=v_count+1; END LOOP;RETURN v_count;END; $function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.finalize_migration_batch(p_batch_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_opening uuid;v_status text;
begin
  perform erp.require_owner_admin();select status into v_status from erp.migration_batches where id=p_batch_id for update;if v_status is null then raise exception 'Migration batch not found';end if;if v_status='POSTED' then return;end if;if v_status not in('READY','POSTING') then raise exception 'Migration batch must be READY/POSTING';end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then raise exception 'Migration batch has validation errors';end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','OPEN_PO') and posted_entity_id is null) then raise exception 'Migration batch still has unapplied master/roll/open-PO rows';end if;
  select id into v_opening from erp.opening_balance_headers where migration_batch_id=p_batch_id order by created_at limit 1;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('OPENING_BALANCE_ITEM','MATERIAL_ROLL')) then
    if v_opening is null then raise exception 'Opening stock/balance rows exist but opening document was not prepared';end if;
    if (select status from erp.opening_balance_headers where id=v_opening)<>'POSTED' then raise exception 'Migration opening balance must be POSTED before finalizing batch';end if;
  end if;
  update erp.migration_batches set status='POSTED',posted_at=statement_timestamp(),error_message=null where id=p_batch_id;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason) values('migration_batches',p_batch_id,'POST',jsonb_build_object('status','POSTED'),erp.current_app_user_id(),'Finalize migration batch');
end;$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION erp.stage_migration_row(p_batch_id uuid, p_entity_type text, p_source_row_no integer, p_legacy_key text, p_source_payload jsonb, p_normalized_payload jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_status text; v_id uuid; v_type text:=upper(trim(p_entity_type));
begin
  perform erp.require_owner_admin();
  select status into v_status from erp.migration_batches where id=p_batch_id for update;
  if v_status is null then raise exception 'Migration batch not found'; end if;
  if v_status not in ('DRAFT','VALIDATING','READY','POSTING') then raise exception 'Migration batch % cannot be staged while status is %',p_batch_id,v_status; end if;
  -- Lock order is batch -> opening in both the editor and posting consumer.
  perform 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id order by id for update;
  if exists(select 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id and status<>'DRAFT') then
    raise exception 'AK_MIGRATION_STAGE_AFTER_POSTING_REFUSED';
  end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type=v_type
    and source_row_no=p_source_row_no and posted_entity_id is not null and entity_type<>'OPENING_BALANCE_ITEM') then
    raise exception 'AK_APPLIED_MASTER_ROW_EDIT_REQUIRES_MASTER_CORRECTION';
  end if;
  if p_source_row_no is null or p_source_row_no<=0 then raise exception 'source_row_no must be positive'; end if;
  if v_type not in ('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPEN_PO') then
    raise exception 'Unsupported migration entity_type %',v_type;
  end if;
  insert into erp.migration_staging_rows(batch_id,entity_type,source_row_no,legacy_key,source_payload,normalized_payload,validation_status,validation_errors,updated_at)
  values (p_batch_id,v_type,p_source_row_no,nullif(trim(p_legacy_key),''),coalesce(p_source_payload,'{}'::jsonb),coalesce(p_normalized_payload,'{}'::jsonb),'PENDING','[]'::jsonb,statement_timestamp())
  on conflict (batch_id,entity_type,source_row_no) do update set
    legacy_key=excluded.legacy_key,source_payload=excluded.source_payload,normalized_payload=excluded.normalized_payload,
    validation_status='PENDING',validation_errors='[]'::jsonb,posted_entity_type=null,posted_entity_id=null,posted_at=null,updated_at=statement_timestamp()
  returning id into v_id;
  -- Prepared opening is still a draft: edits remain allowed. Invalidate only
  -- its unposted lines, keep the header identity, and require fresh prepare.
  delete from erp.opening_balance_items i using erp.opening_balance_headers h
    where i.opening_id=h.id and h.migration_batch_id=p_batch_id and h.status='DRAFT';
  update erp.migration_staging_rows set posted_entity_type=null,posted_entity_id=null,posted_at=null
    where batch_id=p_batch_id and entity_type='OPENING_BALANCE_ITEM';
  update erp.migration_batches set status='DRAFT',validated_at=null,error_message=null where id=p_batch_id;
  return v_id;
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
$canonical_opening_v2620ak$;

do $installed_v2620ak$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620ak_rollback_capsule)<>8 then
    raise exception 'AK_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620ak_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp._validate_migration_batch_base(uuid)','eb6fc2bc6cf419a72be75891d145782dbb1dec06186243834c2a444fc1fa9801','cb72249e0a5ccc835d40c7468601a952a9387186545e34f13391bdf4a17ce0f7',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.validate_migration_opening_stock_costs(uuid)','8223a856b0a0cd66d29a9eba31ebb6644434f934d910f184947a35ae0ffa77a0','c97586c8656f10cfbc73a6f2ec80c30b03f6e41cf6e376757ddef467eb86abeb',array['postgres=X/postgres']::text[]),
    ('erp.prepare_migration_opening_balance(uuid,text)','89f419571e5de43434008e5090b1d4808089411ba839a53172354a145ec97323','25dec082cc725d44b22283551a53d58b368714ab845f2f7daed807010305e90f',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.apply_migration_master_rows(uuid)','6fd720835a487197a9b0d4b6246d9669ba5f472c7135993ab64cd5d9970eb1c9','605407f1e9fa8c41bf768931c4b3b4e92646930005b48bb2b74ee46927016ef4',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.apply_migration_open_pos(uuid)','49dd168a2dc3df0be6fcec9c962446d91e5724f9a838dc9616d894717c9844f7','8d7f5ce365807ea1d26885f15a66b30e6d2bf85d6328a493b3d6fa037c17c06c',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.finalize_migration_batch(uuid)','b2ca642c739fda50ffe2e5fb7d165e9a3370bcc55fad2e256c358d403f1436e3','0c72dc6eda42a90a92d13845eb7e70d1ccf5c2e3efeda83d521728f2024e0022',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','0a35df9e1c385ca27f2c34f17de8e22023b58e2f6c42d9788260d0ebd69cecaa','153138b17d4993d583390e7e6d623d2abe3343741f8651a4007126d2cd75375c',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_opening_balance(uuid)','6460ab913c9a0614df6a622ff2a223df21c13d1361e14e6089c09375f7a95b40','632075e17f4c59ceafe109059bb7105dca72b5b1fcc06e4ff67a9f050ee67543',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620ak_rollback_capsule
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
      raise exception 'AK_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;

end
$installed_v2620ak$;

do $boundary_v2620ak$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620ak_rollback_capsule') order by c.relname loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>223 then
    raise exception 'AK_FULL_ERP_BOUNDARY_CARDINALITY expected223 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620ak_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620ak$;

insert into erp.schema_migrations(version,description)
values('v2.6.20ak','Import preview resolves references; draft edits invalidate prepared lines without touching posted history');
commit;
