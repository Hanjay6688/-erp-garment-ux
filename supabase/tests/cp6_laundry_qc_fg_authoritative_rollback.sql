-- ERP v2.6.20 / CP6 authoritative Laundry -> QC -> FG acceptance.
-- Every synthetic business, finance, stock, HPP, audit, and idempotency row
-- is enclosed by this transaction and rolled back.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local datestyle='ISO, MDY';
set local lock_timeout='8s';
set local statement_timeout='180s';

\ir cp3_r4_full_schema_seed.sql

do $test$
declare
  v_owner_app constant uuid:='c7000000-0000-4000-8000-000000000001';
  v_owner_auth constant uuid:='c7000000-0000-4000-8000-000000000101';
  v_pattern constant uuid:='c7010000-0000-4000-8000-000000000001';
  v_size_s constant uuid:='c7010000-0000-4000-8000-000000000011';
  v_size_m constant uuid:='c7010000-0000-4000-8000-000000000012';
  v_size_l constant uuid:='c7010000-0000-4000-8000-000000000013';
  v_brand constant uuid:='c7010000-0000-4000-8000-000000000021';
  v_second_brand constant uuid:='c7010000-0000-4000-8000-000000000022';
  v_inactive_brand constant uuid:='c7010000-0000-4000-8000-000000000023';
  v_product_s constant uuid:='c7010000-0000-4000-8000-000000000031';
  v_product_m constant uuid:='c7010000-0000-4000-8000-000000000032';
  v_cross_brand_same_sku constant uuid:='c7010000-0000-4000-8000-000000000033';
  v_other_model constant uuid:='c7010000-0000-4000-8000-000000000040';
  v_wrong_model_product constant uuid:='c7010000-0000-4000-8000-000000000041';
  v_expired_product constant uuid:='c7010000-0000-4000-8000-000000000042';
  v_inactive_brand_product constant uuid:='c7010000-0000-4000-8000-000000000043';
  v_chain_root constant uuid:='c7010000-0000-4000-8000-000000000044';
  v_chain_successor constant uuid:='c7010000-0000-4000-8000-000000000045';
  v_chain_probe constant uuid:='c7010000-0000-4000-8000-000000000046';
  v_fg_location constant uuid:='c7020000-0000-4000-8000-000000000001';
  v_vendor constant uuid:='c7020000-0000-4000-8000-000000000002';
  v_process constant uuid:='c7020000-0000-4000-8000-000000000003';
  v_rate constant uuid:='c7020000-0000-4000-8000-000000000004';
  v_supplier constant uuid:='c7030000-0000-4000-8000-000000000001';
  v_material constant uuid:='c7030000-0000-4000-8000-000000000002';
  v_roll constant uuid:='c7030000-0000-4000-8000-000000000003';
  v_po constant uuid:='c7040000-0000-4000-8000-000000000001';
  v_cut_batch constant uuid:='c7040000-0000-4000-8000-000000000002';
  v_group constant uuid:='c7040000-0000-4000-8000-000000000003';
  v_slot constant uuid:='c7040000-0000-4000-8000-000000000004';
  v_group_roll constant uuid:='c7040000-0000-4000-8000-000000000005';
  v_yield constant uuid:='c7040000-0000-4000-8000-000000000006';
  v_pickup constant uuid:='c7040000-0000-4000-8000-000000000007';
  v_distribution_batch constant uuid:='c7040000-0000-4000-8000-000000000008';
  v_distribution_allocation constant uuid:='c7040000-0000-4000-8000-000000000009';
  v_distribution_batch_2 constant uuid:='c7040000-0000-4000-8000-000000000010';
  v_distribution_allocation_2 constant uuid:='c7040000-0000-4000-8000-000000000011';
  v_malformed_delivery constant uuid:='c7040000-0000-4000-8000-000000000012';
  v_malformed_delivery_line constant uuid:='c7040000-0000-4000-8000-000000000013';
  v_foreign_po constant uuid:='c7040000-0000-4000-8000-000000000014';
  v_foreign_cut_batch constant uuid:='c7040000-0000-4000-8000-000000000015';
  v_foreign_group constant uuid:='c7040000-0000-4000-8000-000000000016';
  v_foreign_slot constant uuid:='c7040000-0000-4000-8000-000000000017';
  v_foreign_group_roll constant uuid:='c7040000-0000-4000-8000-000000000018';
  v_foreign_yield constant uuid:='c7040000-0000-4000-8000-000000000019';
  v_foreign_qc constant uuid:='c7040000-0000-4000-8000-000000000020';
  v_malformed_receipt constant uuid:='c7040000-0000-4000-8000-000000000021';
  v_malformed_receipt_line constant uuid:='c7040000-0000-4000-8000-000000000022';
  v_malformed_receipt_line_2 constant uuid:='c7040000-0000-4000-8000-000000000023';
  v_component_snapshot constant uuid:='c7050000-0000-4000-8000-000000000001';
  v_work_completion constant uuid:='c7050000-0000-4000-8000-000000000002';
  v_work_line constant uuid:='c7050000-0000-4000-8000-000000000003';
  v_send_request constant uuid:='c7060000-0000-4000-8000-000000000001';
  v_receipt_request constant uuid:='c7060000-0000-4000-8000-000000000002';
  v_qc_request constant uuid:='c7060000-0000-4000-8000-000000000003';
  v_false_all_ready_request constant uuid:='c7060000-0000-4000-8000-000000000004';
  v_false_partial_request constant uuid:='c7060000-0000-4000-8000-000000000005';
  v_claim constant uuid:='c7070000-0000-4000-8000-000000000001';
  v_late_invoice constant uuid:='c7080000-0000-4000-8000-000000000001';
  v_late_invoice_item constant uuid:='c7080000-0000-4000-8000-000000000002';
  v_replacement_invoice constant uuid:='c7080000-0000-4000-8000-000000000003';
  v_replacement_invoice_item constant uuid:='c7080000-0000-4000-8000-000000000004';
  v_send_payload jsonb;
  v_receipt_payload jsonb;
  v_qc_payload jsonb;
  v_response jsonb;
  v_replay jsonb;
  v_workspace jsonb;
  v_group_version bigint;
  v_foreign_group_version bigint;
  v_delivery uuid;
  v_delivery_version bigint;
  v_delivery_size_line uuid;
  v_receipt uuid;
  v_receipt_line uuid;
  v_receipt_version bigint;
  v_receipt_size_line uuid;
  v_qc uuid;
  v_qc_version bigint;
  v_failed boolean;
  v_hpp numeric;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.19c')
     or to_regclass('erp.laundry_delivery_batch_size_lines') is null
     or to_regclass('erp.laundry_receipt_batch_size_lines') is null
     or to_regclass('erp.cp6_laundry_qc_execution_context') is null
     or to_regclass('erp.cp6_v2620_acl_capsule') is null
     or to_regclass('erp.idx_products_brand_sku_effective_v2620') is null
     or to_regclass('erp.uq_cp6_wip_reversal_source_v2620') is null
     or to_regprocedure('erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()') is null
     or to_regprocedure('public.erp_get_laundry_qc_workspace_v1(text,text)') is null
     or to_regprocedure('public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)') is null
     or not exists(
       select 1 from pg_trigger t
       where t.tgrelid='erp.vendor_invoices'::regclass
         and t.tgname='trg_guard_cp6_vendor_invoice_receipt_on_post_v2620'
         and t.tgenabled<>'D' and not t.tgisinternal
     )
     or (select count(*) from erp.cp6_v2620_rollback_capsule)<>7
     or (select count(*) from erp.cp6_v2620_acl_capsule)<>13 then
    raise exception 'CP6 v2.6.20 boundary is not installed completely';
  end if;
  if has_function_privilege('anon','public.erp_get_laundry_qc_workspace_v1(text,text)','EXECUTE')
     or has_function_privilege('anon','public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_get_laundry_qc_workspace_v1(text,text)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.get_laundry_qc_workspace_v1(text,text)','EXECUTE')
     or has_function_privilege('authenticated','erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()','EXECUTE')
     or has_table_privilege('authenticated','erp.laundry_delivery_batch_size_lines','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.laundry_receipt_batch_size_lines','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cp6_laundry_qc_execution_context','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cp6_v2620_rollback_capsule','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cp6_v2620_acl_capsule','SELECT,INSERT,UPDATE,DELETE')
     or exists(
       select 1 from(
         values
           ('erp.laundry_deliveries'::regclass),
           ('erp.laundry_delivery_lines'::regclass),
           ('erp.qc_inspections'::regclass),
           ('erp.qc_inspection_items'::regclass)
       ) x(rel)
       where has_table_privilege('authenticated',x.rel,'INSERT')
          or has_table_privilege('authenticated',x.rel,'UPDATE')
          or has_table_privilege('authenticated',x.rel,'DELETE')
     )
     or exists(
       select 1 from(
         values
           ('erp.apply_cutting_correction_and_post_laundry(uuid,uuid,text,text,text,jsonb,timestamp with time zone)'),
           ('erp.post_laundry_delivery(uuid)'),
           ('erp.post_laundry_receipt_v2(uuid,uuid,bigint,text)'),
           ('erp.save_laundry_receipt_draft_v2(jsonb,uuid,bigint)'),
           ('erp.reverse_laundry_delivery(uuid,text)'),
           ('erp.reverse_laundry_receipt(uuid,text)'),
           ('erp.post_qc(uuid)'),
           ('erp.reverse_qc(uuid,text)'),
           ('erp.post_fg_partial_completion_v2(jsonb,uuid,bigint)')
       ) x(sig)
       where has_function_privilege('authenticated',x.sig,'EXECUTE')
     ) then
    raise exception 'CP6 browser/private ACL boundary is open';
  end if;
  if pg_get_functiondef('erp.require_internal()'::regprocedure) not like '%cp6_laundry_qc_execution_context%'
     or pg_get_functiondef('erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure)
       not like '%browser_formula_used%false%'
     or pg_get_viewdef('erp.v_fg_partial_completion_progress'::regclass,true)
       not like '%laundry_good_returned_qty_pcs%laundry_qc_accounted_qty_pcs%' then
    raise exception 'CP6 internal delegation or Good-only QC contract is absent';
  end if;

  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_owner_app,v_owner_auth,'CP6 Synthetic Owner','OWNER',id,true
  from erp.app_roles where role_code='OWNER';
  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_owner_auth,'role','authenticated'
  )::text,true);
  perform set_config('app.change_reason','CP6 disposable full-schema fixture',true);

  insert into erp.production_patterns(
    id,pattern_code,revision,pattern_name,sort_order,is_active,created_by,updated_by
  ) values(v_pattern,'CP6-REG','R1','CP6 Reliable Pattern',9701,true,v_owner_app,v_owner_app);
  insert into erp.sizes(id,size_code,sort_order) values
    (v_size_s,'CP6-S',9701),(v_size_m,'CP6-M',9702),(v_size_l,'CP6-L',9703);
  insert into erp.product_model_sizes(model_id,size_id,sort_order) values
    ('a2000000-0000-0000-0000-000000000001',v_size_s,701),
    ('a2000000-0000-0000-0000-000000000001',v_size_m,702),
    ('a2000000-0000-0000-0000-000000000001',v_size_l,703);
  insert into erp.product_models(id,model_code,model_name)
  values(v_other_model,'CP6-OTHER','CP6 Other Model');
  insert into erp.product_model_sizes(model_id,size_id,sort_order)
  values(v_other_model,v_size_s,701),(v_other_model,v_size_l,703);
  insert into erp.brands(id,brand_code,brand_name,is_active) values
    (v_brand,'CP6-BRAND','CP6 Final Brand',true),
    (v_second_brand,'CP6-BRAND-2','CP6 Second Brand',true),
    (v_inactive_brand,'CP6-BRAND-OFF','CP6 Inactive Brand',false);
  insert into erp.products(
    id,sku,model_id,brand_id,color_name,size_id,product_name,
    identity_root_id,effective_from,effective_to,is_active,is_portal_visible
  ) values
    (v_product_s,'CP6-SKU-S','a2000000-0000-0000-0000-000000000001',v_brand,
      'NAVY',v_size_s,'CP6 Final Small',v_product_s,'2026-01-01 00:00+00',null,true,true),
    (v_product_m,'CP6-SKU-S','a2000000-0000-0000-0000-000000000001',v_brand,
      'NAVY',v_size_m,'CP6 Final Medium',v_product_m,'2026-01-01 00:00+00',null,true,true),
    (v_cross_brand_same_sku,'CP6-SKU-S',v_other_model,v_second_brand,
      'NAVY',v_size_s,'CP6 Same Number Other Brand',v_cross_brand_same_sku,
      '2026-01-01 00:00+00',null,true,true),
    (v_wrong_model_product,'CP6-WRONG-MODEL-S',v_other_model,v_brand,
      'NAVY',v_size_s,'CP6 Wrong Model Small',v_wrong_model_product,'2026-01-01 00:00+00',null,true,true),
    (v_expired_product,'CP6-EXPIRED-S','a2000000-0000-0000-0000-000000000001',v_brand,
      'NAVY',v_size_s,'CP6 Expired Small',v_expired_product,
      '2025-01-01 00:00+00','2025-12-31 00:00+00',true,true),
    (v_inactive_brand_product,'CP6-INACTIVE-BRAND-S',
      'a2000000-0000-0000-0000-000000000001',v_inactive_brand,
      'NAVY',v_size_s,'CP6 Inactive Brand Small',v_inactive_brand_product,
      '2026-01-01 00:00+00',null,true,true);
  v_failed:=false;
  begin
    insert into erp.products(
      id,sku,model_id,brand_id,color_name,size_id,product_name,
      identity_root_id,effective_from,is_active,is_portal_visible
    ) values(
      'c7010000-0000-4000-8000-000000000034','CP6-SKU-S',v_other_model,v_brand,
      'RED',v_size_s,'CP6 Duplicate Number Same Brand',
      'c7010000-0000-4000-8000-000000000034','2026-01-01 00:00+00',true,true
    );
  exception when others then
    if sqlerrm='Nomor SKU CP6-SKU-S untuk merek dan size ini sudah punya identitas aktif'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 allowed duplicate brand + SKU number + size identity'; end if;
  v_failed:=false;
  begin
    insert into erp.products(
      id,sku,model_id,brand_id,color_name,size_id,product_name,
      identity_root_id,effective_from,is_active,is_portal_visible
    ) values(
      'c7010000-0000-4000-8000-000000000035','CP6-SKU-S',v_other_model,v_brand,
      'RED',v_size_l,'CP6 Mismatched Same-Brand Variant',
      'c7010000-0000-4000-8000-000000000035','2026-01-01 00:00+00',true,true
    );
  exception when others then
    if sqlerrm='Varian size untuk merek + nomor SKU yang sama wajib memakai model dan warna yang sama'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then
    raise exception 'CP6 allowed one brand + SKU number to drift across model/color by size';
  end if;

  -- Product-version metadata is stock/HPP lineage. Prove even a trusted
  -- writer cannot detach a non-root version, fork one predecessor, or rewrite
  -- any identity/period field after creation. Display text remains editable.
  v_failed:=false;
  begin
    insert into erp.products(
      id,sku,model_id,brand_id,color_name,size_id,product_name,
      identity_root_id,effective_from,effective_to,is_active,is_portal_visible
    ) values(
      v_chain_probe,'CP6-CHAIN-L',v_other_model,v_second_brand,
      'BLACK',v_size_l,'CP6 Detached Chain Probe',v_chain_root,
      '2030-01-01 00:00+00','2031-01-01 00:00+00',true,false
    );
  exception when others then
    if sqlerrm='identity_root_id SKU wajib menunjuk root yang valid dan menunjuk dirinya sendiri'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 allowed a product version with a missing identity root'; end if;

  insert into erp.products(
    id,sku,model_id,brand_id,color_name,size_id,product_name,
    identity_root_id,effective_from,effective_to,is_active,is_portal_visible
  ) values(
    v_chain_root,'CP6-CHAIN-L',v_other_model,v_second_brand,
    'BLACK',v_size_l,'CP6 Chain Root',v_chain_root,
    '2026-01-01 00:00+00','2027-01-01 00:00+00',true,false
  );
  insert into erp.products(
    id,sku,model_id,brand_id,color_name,size_id,product_name,
    identity_root_id,effective_from,effective_to,supersedes_product_id,
    is_active,is_portal_visible
  ) values(
    v_chain_successor,'CP6-CHAIN-L',v_other_model,v_second_brand,
    'BLACK',v_size_l,'CP6 Chain Successor',v_chain_root,
    '2027-01-01 00:00+00',null,v_chain_root,true,false
  );

  v_failed:=false;
  begin
    insert into erp.products(
      id,sku,model_id,brand_id,color_name,size_id,product_name,
      identity_root_id,effective_from,effective_to,is_active,is_portal_visible
    ) values(
      v_chain_probe,'CP6-CHAIN-L',v_other_model,v_second_brand,
      'BLACK',v_size_l,'CP6 Detached Non-root Probe',v_chain_root,
      '2030-01-01 00:00+00','2031-01-01 00:00+00',true,false
    );
  exception when others then
    if sqlerrm='Versi SKU non-root wajib menunjuk predecessor'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 allowed a non-root product version without a predecessor'; end if;

  v_failed:=false;
  begin
    insert into erp.products(
      id,sku,model_id,brand_id,color_name,size_id,product_name,
      identity_root_id,effective_from,effective_to,supersedes_product_id,
      is_active,is_portal_visible
    ) values(
      v_chain_probe,'CP6-CHAIN-L',v_other_model,v_second_brand,
      'BLACK',v_size_l,'CP6 Forked Successor Probe',v_chain_root,
      '2027-01-01 00:00+00',null,v_chain_root,true,false
    );
  exception when others then
    if sqlerrm='Satu versi SKU tidak boleh memiliki lebih dari satu successor'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 allowed a branched product successor chain'; end if;

  v_failed:=false;
  begin
    update erp.products
    set effective_to='2027-02-01 00:00+00'
    where id=v_chain_root;
  exception when others then
    if sqlerrm='Identitas dan periode SKU immutable setelah row dibuat; ubah nama/status tampilan saja atau buat successor terkontrol, jangan menulis ulang sejarah stok/HPP'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 allowed a product period update to rewrite historical stock/HPP identity'; end if;

  v_failed:=false;
  begin
    update erp.products set color_name='WHITE' where id=v_chain_successor;
  exception when others then
    if sqlerrm='Identitas dan periode SKU immutable setelah row dibuat; ubah nama/status tampilan saja atau buat successor terkontrol, jangan menulis ulang sejarah stok/HPP'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 allowed a product identity update to rewrite historical stock/HPP meaning'; end if;

  update erp.products set product_name='CP6 Chain Successor Renamed' where id=v_chain_successor;
  if (select product_name from erp.products where id=v_chain_successor)<>'CP6 Chain Successor Renamed' then
    raise exception 'CP6 immutable identity guard blocked safe display-name maintenance';
  end if;

  if (select issue_count from erp.run_v259_integrity_checks()
      where check_name='PRODUCT_IDENTITY_SKU_CROSS_ROOT_OVERLAP')<>0
     or (select issue_count from erp.run_v259_integrity_checks()
      where check_name='PRODUCT_IDENTITY_BRAND_SKU_VARIANT_MISMATCH')<>0
     or (select issue_count from erp.run_v259_integrity_checks()
      where check_name='PRODUCT_IDENTITY_ROOT_INVALID')<>0
     or (select issue_count from erp.run_v259_integrity_checks()
      where check_name='PRODUCT_SUCCESSOR_CHAIN_MISMATCH')<>0
     or (select issue_count from erp.run_v259_integrity_checks()
      where check_name='PRODUCT_SUCCESSOR_BRANCH')<>0 then
    raise exception 'CP6 product checker rejected valid Brand/SKU variants or version lineage';
  end if;
  insert into erp.accessory_bom_versions(
    product_id,version_label,effective_from,is_active,notes
  ) values(
    v_product_s,'CP6-EXPLICIT-EMPTY','2026-01-01 00:00+00',true,
    'Explicit empty BOM: no fixture or silent accessory fallback'
  );
  insert into erp.locations(id,location_code,location_name,location_type)
  values(v_fg_location,'CP6-FG','CP6 FG Warehouse','FG_WAREHOUSE');
  insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active,notes)
  values(v_vendor,'CP6-LDR','CP6 Laundry Vendor',true,'Disposable CP6 fixture');
  insert into erp.wash_processes(id,process_code,process_name,is_active)
  values(v_process,'CP6-WASH','CP6 Standard Wash',true);
  insert into erp.laundry_vendor_rate_versions(
    id,vendor_id,wash_process_id,rate_per_pcs,effective_from,effective_to,notes
  ) values(v_rate,v_vendor,v_process,7,'2026-01-01 00:00+00',null,'CP6 exact rate');

  insert into erp.suppliers(id,supplier_code,supplier_name,supplier_type)
  values(v_supplier,'CP6-SUP','CP6 Synthetic Supplier','MATERIAL');
  insert into erp.materials(id,material_sku,material_name,material_type,unit_code)
  values(v_material,'CP6-FAB','CP6 Synthetic Fabric','FABRIC','yd');
  insert into erp.material_rolls(
    id,material_id,supplier_id,roll_number,original_qty,cached_qty,status,received_at
  ) values(v_roll,v_material,v_supplier,'CP6-ROLL',10,10,'AVAILABLE','2026-08-31 07:00+00');
  insert into erp.production_orders(
    id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at,notes
  ) values(
    v_po,'CP6-PO-001','a2000000-0000-0000-0000-000000000001',
    'a1000000-0000-0000-0000-000000000001',10,'SEWING','SEWING',
    '2026-09-01 07:00+00','CP6 end-to-end reliability fixture'
  );
  insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes)
  values(v_cut_batch,v_po,'CP6-CUT-001','2026-09-01 08:00+00','OPEN','CP6 fixture');
  insert into erp.cutting_groups(
    id,po_id,group_number,cut_at,status,cutting_batch_id,pattern_id,notes
  ) values(
    v_group,v_po,'CP6-GROUP-001','2026-09-01 08:00+00','CUT',v_cut_batch,v_pattern,
    'CP6 immutable size/distribution source'
  );
  insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id,drawing_no)
  values(v_slot,v_group,1,v_size_s,1);
  insert into erp.cutting_group_rolls(
    id,cutting_group_id,roll_id,qty_issued,qty_consumed,qty_reported_remaining,
    qty_physically_returned,return_destination,unit_cost_snapshot,notes
  ) values(v_group_roll,v_group,v_roll,10,10,0,0,'NONE',0,'CP6 physical source only');
  insert into erp.cutting_roll_yields(id,cutting_group_roll_id,size_slot_id,qty_pcs)
  values(v_yield,v_group_roll,v_slot,10);
  insert into erp.cutting_pickups(
    id,cutting_group_id,contractor_id,picked_up_at,allocation_mode,status,notes,created_by
  ) values(
    v_pickup,v_group,'a1000000-0000-0000-0000-000000000001',
    '2026-09-01 09:00+00','ROLL','DRAFT','CP6 exact pickup',v_owner_app
  );
  insert into erp.cutting_distribution_batches(id,pickup_id,batch_no,notes) values
    (v_distribution_batch,v_pickup,1,'CP6 exact batch'),
    (v_distribution_batch_2,v_pickup,2,'CP6 temporary second batch for one-delivery-one-batch proof');
  insert into erp.cutting_distribution_allocations(id,batch_id,cutting_roll_yield_id,qty_pcs)
  values
    (v_distribution_allocation,v_distribution_batch,v_yield,5),
    (v_distribution_allocation_2,v_distribution_batch_2,v_yield,5);
  update erp.cutting_groups
  set picked_up_at='2026-09-01 09:00+00',executor_name='CP6 Mandor',status='PICKED_UP'
  where id=v_group;

  -- A facade request always selects one batch. Prove the database trigger also
  -- rejects a trusted/internal malformed draft that attempts to combine two
  -- authoritative distribution batches into one Laundry delivery. The caught
  -- exception rolls this whole inner block back, including its temporary POST.
  v_failed:=false;
  begin
    update erp.cutting_pickups
    set status='POSTED',posted_by=v_owner_app,posted_at='2026-09-01 09:00+00'
    where id=v_pickup;
    insert into erp.laundry_deliveries(
      id,delivery_number,po_id,vendor_id,target_dyeing_color,target_wash_process_id,
      physical_at,status,created_by
    ) values(
      v_malformed_delivery,'LDR-CP6-TWO-BATCH',v_po,v_vendor,'NAVY',v_process,
      '2026-09-01 11:00+00','DRAFT',v_owner_app
    );
    insert into erp.laundry_delivery_lines(
      id,delivery_id,cutting_group_id,qty_sent_pcs,estimated_rate_snapshot,
      estimated_cost_status,notes
    ) values(
      v_malformed_delivery_line,v_malformed_delivery,v_group,10,7,'ESTIMATED',
      'Must fail because one delivery cannot merge two distribution batches'
    );
    insert into erp.laundry_delivery_batch_size_lines(
      delivery_line_id,distribution_batch_id,size_id,qty_sent_pcs,created_by
    ) values
      (v_malformed_delivery_line,v_distribution_batch,v_size_s,5,v_owner_app),
      (v_malformed_delivery_line,v_distribution_batch_2,v_size_s,5,v_owner_app);
    perform erp.post_laundry_delivery(v_malformed_delivery);
  exception when others then
    if sqlerrm='CP6 Laundry delivery must contain exactly one authoritative distribution batch'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then
    raise exception 'CP6 allowed one Laundry delivery to merge two distribution batches';
  end if;
  if exists(select 1 from erp.laundry_deliveries where id=v_malformed_delivery)
     or (select status from erp.cutting_pickups where id=v_pickup)<>'DRAFT' then
    raise exception 'CP6 malformed multi-batch rejection left transaction residue';
  end if;

  v_failed:=false;
  begin
    update erp.cutting_pickups
    set status='POSTED',posted_by=v_owner_app,posted_at='2026-09-01 09:00+00'
    where id=v_pickup;
    insert into erp.laundry_deliveries(
      id,delivery_number,po_id,vendor_id,target_dyeing_color,target_wash_process_id,
      physical_at,status,created_by
    ) values(
      v_malformed_delivery,'LDR-CP6-NO-SIZE-LINEAGE',v_po,v_vendor,'NAVY',v_process,
      '2026-09-01 11:00+00','DRAFT',v_owner_app
    );
    insert into erp.laundry_delivery_lines(
      id,delivery_id,cutting_group_id,qty_sent_pcs,estimated_rate_snapshot,
      estimated_cost_status,notes
    ) values(
      v_malformed_delivery_line,v_malformed_delivery,v_group,10,7,'ESTIMATED',
      'A trusted legacy writer still may not omit exact batch/size lineage'
    );
    perform erp.post_laundry_delivery(v_malformed_delivery);
  exception when others then
    if sqlerrm='CP6 posted Laundry delivery requires immutable distribution batch/size lineage'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed
     or exists(select 1 from erp.laundry_deliveries where id=v_malformed_delivery)
     or (select status from erp.cutting_pickups where id=v_pickup)<>'DRAFT' then
    raise exception 'CP6 trusted delivery writer bypassed exact batch/size lineage or left residue';
  end if;

  delete from erp.cutting_distribution_allocations where id=v_distribution_allocation_2;
  delete from erp.cutting_distribution_batches where id=v_distribution_batch_2;
  update erp.cutting_distribution_allocations set qty_pcs=10
  where id=v_distribution_allocation;
  update erp.cutting_pickups
  set status='POSTED',posted_by=v_owner_app,posted_at='2026-09-01 09:00+00'
  where id=v_pickup;

  insert into erp.po_work_component_snapshots(
    id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at
  ) values(
    v_component_snapshot,v_po,'a4000000-0000-0000-0000-000000000001',1,0,
    '2026-09-01 09:30+00'
  );
  insert into erp.work_completion_events(
    id,completion_number,po_id,contractor_id,cutting_group_id,
    physical_at,status,notes,created_by
  ) values(
    v_work_completion,'CP6-WC-001',v_po,'a1000000-0000-0000-0000-000000000001',v_group,
    '2026-09-01 10:00+00','DRAFT','CP6 sewn capacity',v_owner_app
  );
  insert into erp.work_completion_lines(
    id,completion_id,po_component_snapshot_id,work_component_id,
    qty_completed,qty_payable,rate_snapshot,notes
  ) values(
    v_work_line,v_work_completion,v_component_snapshot,
    'a4000000-0000-0000-0000-000000000001',10,10,0,'CP6 sewn capacity'
  );
  perform erp.post_work_completion(v_work_completion);
  perform erp.record_sewing_terminal_v1(jsonb_build_object(
    'work_completion_id',v_work_completion,'qty_pcs',10,
    'reason','CP6 authoritative sewn terminal'
  ),gen_random_uuid());

  select row_version into v_group_version from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_workspace:=public.erp_get_laundry_qc_workspace_v1('LAUNDRY','CP6-PO-001');
  if v_workspace->>'contract_version'<>'CP6_V2620'
     or v_workspace->>'scope'<>'LAUNDRY'
     or v_workspace#>>'{readiness,no_fixture_fallback}'<>'true'
     or v_workspace#>>'{readiness,failed_wash_with_charge_supported}'<>'false'
     or v_workspace#>>'{readiness,lineage_integrity_ok}'<>'true'
     or (v_workspace#>>'{readiness,lineage_issue_count}')::bigint<>0
     or jsonb_array_length(v_workspace->'ready_batches')<>1
     or (v_workspace#>>'{ready_batches,0,sizes,0,available_qty_pcs}')::integer<>10
     or (v_workspace#>>'{ready_batches,0,group_unsent_ready_qty_pcs}')::integer<>10 then
    raise exception 'CP6 Laundry workspace lost authoritative readiness/capacity: %',v_workspace;
  end if;
  if exists(
       select 1 from jsonb_array_elements(v_workspace#>'{lookups,products}') p
       where p ? 'pattern_id' or p ? 'pattern_code' or p ? 'pattern_name'
     )
     or not exists(
       select 1 from jsonb_array_elements(v_workspace#>'{lookups,products}') p
       where p->>'id'=v_product_s::text and p->>'brand_name'='CP6 Final Brand'
         and p->>'sku'='CP6-SKU-S'
         and p->>'model_name' is not null
     )
     or not exists(
       select 1 from jsonb_array_elements(v_workspace#>'{lookups,products}') p
       where p->>'id'=v_product_m::text and p->>'brand_name'='CP6 Final Brand'
         and p->>'sku'='CP6-SKU-S' and p->>'size_code'='CP6-M'
     )
     or not exists(
       select 1 from jsonb_array_elements(v_workspace#>'{lookups,products}') p
       where p->>'id'=v_cross_brand_same_sku::text
         and p->>'brand_name'='CP6 Second Brand' and p->>'sku'='CP6-SKU-S'
     )
     or exists(
       select 1 from jsonb_array_elements(v_workspace#>'{lookups,products}') p
       where p->>'id'=v_inactive_brand_product::text
     )
     or (select ordinality from jsonb_array_elements(v_workspace#>'{lookups,products}')
           with ordinality p(value,ordinality) where value->>'id'=v_product_s::text)
        >=(select ordinality from jsonb_array_elements(v_workspace#>'{lookups,products}')
           with ordinality p(value,ordinality) where value->>'id'=v_cross_brand_same_sku::text) then
    raise exception 'CP6 product lookup violated Brand -> SKU -> Model identity or leaked Pattern into SKU';
  end if;

  v_send_payload:=jsonb_build_object(
    'distribution_batch_id',v_distribution_batch,'vendor_id',v_vendor,
    'wash_process_id',v_process,'target_dyeing_color','NAVY',
    'physical_at','2026-09-01T11:00:00+00','reason','CP6 physical Laundry send checked',
    'notes','Exact distribution batch and size',
    'lines',jsonb_build_array(jsonb_build_object('size_id',v_size_s,'qty_sent_pcs',10))
  );
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_DELIVERY',v_send_payload-'physical_at',gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='An explicit timezone-qualified physical_at is required; server time is never a transactional default'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 silently defaulted a physical transaction time'; end if;
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_DELIVERY',v_send_payload||jsonb_build_object(
        'physical_at','2026-09-01T11:00:00',
        'reason','CP6 timezone ambiguity must fail'
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='An explicit timezone-qualified physical_at is required; server time is never a transactional default'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 accepted an ambiguous physical time without timezone'; end if;
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_DELIVERY',v_send_payload||jsonb_build_object(
        'physical_at','2026-02-30T11:00:00+00',
        'reason','CP6 invalid physical calendar must fail'
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='An explicit timezone-qualified physical_at is required; server time is never a transactional default'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 accepted a calendar-invalid physical time'; end if;
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_DELIVERY',v_send_payload||jsonb_build_object(
        'physical_at','2026-09-01T09:30:00+00',
        'reason','CP6 Laundry chronology must fail'
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm like 'Laundry send time predates sufficient authoritative sewing output.%'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 allowed Laundry dispatch before authoritative sewing output'; end if;
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_DELIVERY',jsonb_set(
        v_send_payload,'{lines,0,qty_sent_pcs}',to_jsonb('10'::text)
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='CP6 POST_DELIVERY line has invalid field types'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 coerced a string into a physical integer quantity'; end if;
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_DELIVERY',v_send_payload||jsonb_build_object('qty_sent',10),
      gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='CP6 POST_DELIVERY payload contains unexpected key qty_sent'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 silently ignored a misspelled physical field'; end if;
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_DELIVERY',v_send_payload,v_send_request,v_group_version
  );
  v_replay:=public.erp_save_laundry_qc_action_v1(
    'POST_DELIVERY',v_send_payload,v_send_request,v_group_version
  );
  execute 'reset role';
  if v_response is distinct from v_replay or v_response->>'status'<>'SENT'
     or v_response->>'contract_version'<>'CP6_V2620'
     or v_response->>'client_request_id'<>v_send_request::text
     or (v_response->>'committed')::boolean is distinct from true
     or (v_response->>'qty_sent_pcs')::integer<>10
     or (v_response->>'rate_per_pcs')::numeric<>7
     or (v_response->>'estimated_cost')::numeric<>70 then
    raise exception 'CP6 delivery posting/idempotent replay diverged: %, %',v_response,v_replay;
  end if;
  v_delivery:=(v_response->>'delivery_id')::uuid;
  v_delivery_version:=(v_response->>'row_version')::bigint;
  select id into v_delivery_size_line
  from erp.laundry_delivery_batch_size_lines
  where delivery_line_id in(select id from erp.laundry_delivery_lines where delivery_id=v_delivery);
  if v_delivery_size_line is null
     or (select count(*) from erp.laundry_delivery_batch_size_lines
       where delivery_line_id in(select id from erp.laundry_delivery_lines where delivery_id=v_delivery))<>1
     or (select accrued_amount from erp.laundry_cost_accrual_state where po_id=v_po)<>70
     or erp.desired_laundry_accrual(v_po)<>70
     or (select count(*) from erp.wip_stage_events
       where source_type='LAUNDRY_DELIVERY_LINE'
         and source_id in(select id from erp.laundry_delivery_lines where delivery_id=v_delivery)
         and stage_from='SEWING' and stage_to='LAUNDRY' and qty_pcs=10)<>1 then
    raise exception 'CP6 delivery lineage, WIP, or accrual did not post atomically';
  end if;

  execute 'set local role authenticated';
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_DELIVERY',v_send_payload||jsonb_build_object('notes','changed payload'),
      v_send_request,v_group_version
    );
  exception when others then
    if sqlerrm='client_request_id was already used with a different payload' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 delivery idempotency key accepted a different payload'; end if;
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_DELIVERY',v_send_payload||jsonb_build_object('reason','CP6 stale delivery blocked'),
      gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm like 'STALE_VERSION expected %, current %' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 accepted a stale duplicate Laundry send'; end if;

  execute 'reset role';
  v_failed:=false;
  begin
    insert into erp.laundry_receipts(
      id,receipt_number,delivery_id,physical_at,status,created_by
    ) values(
      v_malformed_receipt,'LRC-CP6-NO-SIZE-LINEAGE',v_delivery,
      '2026-09-01 12:00+00','DRAFT',v_owner_app
    );
    insert into erp.laundry_receipt_lines(
      id,receipt_id,delivery_line_id,actual_wash_process_id,
      qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
      actual_rate_snapshot,actual_cost_status,actual_cost,notes
    ) select
      v_malformed_receipt_line,v_malformed_receipt,dl.id,v_process,
      10,0,0,0,7,'ESTIMATED',70,
      'A trusted legacy writer still may not omit exact return batch/size lineage'
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery;
    perform erp.post_laundry_receipt(v_malformed_receipt);
  exception when others then
    if sqlerrm='CP6 posted Laundry receipt requires immutable delivery batch/size lineage'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed or exists(select 1 from erp.laundry_receipts where id=v_malformed_receipt) then
    raise exception 'CP6 trusted receipt writer bypassed exact batch/size lineage or left residue';
  end if;

  v_failed:=false;
  begin
    insert into erp.laundry_receipts(
      id,receipt_number,delivery_id,physical_at,status,created_by
    ) values(
      v_malformed_receipt,'LRC-CP6-TWO-LINES',v_delivery,
      '2026-09-01 12:00+00','DRAFT',v_owner_app
    );
    insert into erp.laundry_receipt_lines(
      id,receipt_id,delivery_line_id,actual_wash_process_id,
      qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
      actual_rate_snapshot,actual_cost_status,actual_cost,notes
    ) select
      x.id,v_malformed_receipt,dl.id,v_process,
      5,0,0,0,7,'ESTIMATED',35,'One physical receipt must keep one line'
    from erp.laundry_delivery_lines dl
    cross join (values(v_malformed_receipt_line),(v_malformed_receipt_line_2)) as x(id)
    where dl.delivery_id=v_delivery;
    insert into erp.laundry_receipt_batch_size_lines(
      receipt_line_id,delivery_batch_size_line_id,size_id,
      qty_good_received,qty_bs_laundry,bs_product_id,created_by
    ) values
      (v_malformed_receipt_line,v_delivery_size_line,v_size_s,5,0,null,v_owner_app),
      (v_malformed_receipt_line_2,v_delivery_size_line,v_size_s,5,0,null,v_owner_app);
    perform erp.post_laundry_receipt(v_malformed_receipt);
  exception when others then
    if sqlerrm='CP6 Laundry receipt must contain exactly one authoritative delivery line'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed or exists(select 1 from erp.laundry_receipts where id=v_malformed_receipt) then
    raise exception 'CP6 trusted receipt writer created a multi-line receipt or left residue';
  end if;
  execute 'set local role authenticated';

  v_receipt_payload:=jsonb_build_object(
    'delivery_id',v_delivery,'wash_process_id',v_process,
    'physical_at','2026-09-01T12:00:00+00','reason','CP6 physical Laundry return counted',
    'lines',jsonb_build_array(jsonb_build_object(
      'delivery_batch_size_line_id',v_delivery_size_line,
      'qty_good_received',5,'qty_bs_laundry',1,'bs_product_id',v_product_s
    ))
  );
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_RECEIPT',jsonb_set(
        v_receipt_payload,'{lines,0,bs_product_id}',to_jsonb(v_expired_product)
      ),gen_random_uuid(),v_delivery_version
    );
  exception when others then
    if sqlerrm='Laundry BS product must be active at physical receipt time and match the source PO model/size'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 accepted an expired SKU for a Laundry BS physical fact'; end if;
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_RECEIPT',jsonb_set(
        v_receipt_payload,'{lines,0,bs_product_id}',to_jsonb(v_inactive_brand_product)
      ),gen_random_uuid(),v_delivery_version
    );
  exception when others then
    if sqlerrm='Laundry BS product must be active at physical receipt time and match the source PO model/size'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 accepted a product whose Brand master is inactive'; end if;
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_RECEIPT',jsonb_set(
        v_receipt_payload,'{lines,0,qty_good_received}',to_jsonb(4.5::numeric)
      ),gen_random_uuid(),v_delivery_version
    );
  exception when others then
    if sqlerrm='CP6 POST_RECEIPT line has invalid field types'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 rounded a fractional physical return into integer pcs'; end if;
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_RECEIPT',v_receipt_payload,v_receipt_request,v_delivery_version
  );
  v_replay:=public.erp_save_laundry_qc_action_v1(
    'POST_RECEIPT',v_receipt_payload,v_receipt_request,v_delivery_version
  );
  execute 'reset role';
  if v_response is distinct from v_replay
     or v_response->>'contract_version'<>'CP6_V2620'
     or v_response->>'client_request_id'<>v_receipt_request::text
     or (v_response->>'committed')::boolean is distinct from true
     or v_response->>'receipt_status'<>'POSTED'
     or v_response->>'delivery_status'<>'PARTIAL_RETURN'
     or (v_response->>'good_qty_pcs')::integer<>5
     or (v_response->>'bs_qty_pcs')::integer<>1
     or (v_response->>'actual_cost')::numeric<>42 then
    raise exception 'CP6 receipt posting/idempotent replay diverged: %, %',v_response,v_replay;
  end if;
  v_receipt:=(v_response->>'receipt_id')::uuid;
  v_receipt_version:=(v_response->>'receipt_row_version')::bigint;
  v_delivery_version:=(v_response->>'delivery_row_version')::bigint;
  select id into v_receipt_line from erp.laundry_receipt_lines where receipt_id=v_receipt;
  select id into v_receipt_size_line from erp.laundry_receipt_batch_size_lines
  where receipt_line_id=v_receipt_line;
  if v_receipt_size_line is null
     or (select count(*) from erp.bs_cases where source_laundry_receipt_line_id in(
       select id from erp.laundry_receipt_lines where receipt_id=v_receipt
     ) and qty_pcs=1 and product_id=v_product_s and status='OPEN')<>1
     or (select actual_cost_status from erp.laundry_receipt_lines where id=v_receipt_line)<>'ESTIMATED'
     or v_response->>'cost_status'<>'ESTIMATED_UNBILLED'
     or v_response->>'accrual_effect'<>'PRESERVED_UNTIL_VENDOR_INVOICE'
     or (select accrued_amount from erp.laundry_cost_accrual_state where po_id=v_po)<>70
     or erp.desired_laundry_accrual(v_po)<>70
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('WIP'))<>70
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('ACCRUED_MANUFACTURING'))<>-70
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('AP_VENDOR'))<>0
     or (select count(*) from erp.wip_stage_events
       where source_type='CP6_LAUNDRY_BS_SIZE_LINE' and source_id=v_receipt_size_line
         and stage_from='QC' and stage_to='ON_HOLD' and qty_pcs=1)<>1 then
    raise exception 'CP6 receipt lineage, terminal Laundry BS, or unbilled-accrual accounting is inconsistent';
  end if;
  if not exists(
    select 1 from erp.v_fg_partial_completion_progress
    where cutting_group_id=v_group and laundry_good_returned_qty_pcs=5
      and laundry_bs_returned_qty_pcs=1 and ready_for_qc_qty_pcs=5
      and laundry_outstanding_qty_pcs=4 and remaining_qc_qty_pcs=9
  ) then raise exception 'Laundry BS was exposed as QC-ready or progress conservation diverged'; end if;

  insert into erp.laundry_claims(
    id,claim_number,vendor_id,delivery_id,qty_claimed,claim_type,
    compensation_amount,status,opened_at,resolution_date,notes
  ) values(
    v_claim,'CP6-STUCK-001',v_vendor,v_delivery,4,'STUCK',0,'OPEN',
    '2026-09-01 12:30:00+00','2026-09-01','CP6 exact outstanding claim'
  );
  if not exists(
    select 1 from erp.v_wip_control_status_v1
    where cutting_group_id=v_group and laundry_in_transit_qty_pcs=0
      and unresolved_laundry_issue_qty_pcs=4
      and (blockers->>'laundry_in_transit')::boolean=false
      and (blockers->>'laundry_issue')::boolean=true
  ) then raise exception 'Open delivery-bound STUCK claim was not classified as an explicit WIP issue'; end if;
  perform erp.resolve_laundry_claim_v2(
    v_claim,'WRITTEN_OFF','CP6 terminal physical loss',gen_random_uuid(),
    (select row_version from erp.laundry_claims where id=v_claim)
  );
  if not exists(
    select 1 from erp.v_fg_partial_completion_progress
    where cutting_group_id=v_group and resolved_claim_qty_pcs=4
      and qc_bs_qty_pcs=5 and qc_accounted_qty_pcs=5
      and laundry_outstanding_qty_pcs=0 and remaining_qc_qty_pcs=5
      and ready_for_qc_qty_pcs=5
  ) or not exists(
    select 1 from erp.v_wip_control_status_v1
    where cutting_group_id=v_group and laundry_in_transit_qty_pcs=0
      and unresolved_laundry_issue_qty_pcs=0
      and (blockers->>'laundry_issue')::boolean=false
  ) then raise exception 'Resolved delivery-bound STUCK claim did not become one terminal loss'; end if;

  -- A later physical return is not invented on top of a settled loss. The
  -- claim must first be reversed to REJECTED, then the same outstanding exact
  -- batch/size can be received. Prove the entire path (including finance/WIP)
  -- inside a disposable subtransaction and roll it back before continuing the
  -- main fixture.
  v_failed:=false;
  begin
    perform erp.reverse_laundry_claim_resolution(
      v_claim,'CP6 late physical return supersedes terminal-loss assumption'
    );
    v_response:=public.erp_save_laundry_qc_action_v1(
      'POST_RECEIPT',jsonb_build_object(
        'delivery_id',v_delivery,'wash_process_id',v_process,
        'physical_at','2026-09-01T13:00:00+00',
        'reason','CP6 authoritative late physical return after claim reversal',
        'lines',jsonb_build_array(jsonb_build_object(
          'delivery_batch_size_line_id',v_delivery_size_line,
          'qty_good_received',4,'qty_bs_laundry',0,'bs_product_id',null
        ))
      ),gen_random_uuid(),v_delivery_version
    );
    if v_response->>'receipt_status'<>'POSTED'
       or v_response->>'delivery_status'<>'RETURNED'
       or (v_response->>'good_qty_pcs')::integer<>4
       or not exists(select 1 from erp.laundry_claims where id=v_claim and status='REJECTED')
       or not exists(
         select 1 from erp.v_fg_partial_completion_progress
         where cutting_group_id=v_group and laundry_good_returned_qty_pcs=9
           and laundry_bs_returned_qty_pcs=1 and ready_for_qc_qty_pcs=9
           and laundry_outstanding_qty_pcs=0 and resolved_claim_qty_pcs=0
           and remaining_qc_qty_pcs=9
       )
       or (select accrued_amount from erp.laundry_cost_accrual_state where po_id=v_po)<>70
       or erp.desired_laundry_accrual(v_po)<>70
       or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
         where l.po_id=v_po and l.account_id=erp.account_id('AP_VENDOR'))<>0
       or (select coalesce(sum(e.qty_pcs) filter(where e.stage_to='LAUNDRY'),0)
             -coalesce(sum(e.qty_pcs) filter(where e.stage_from='LAUNDRY'),0)
           from erp.wip_stage_events e where e.cutting_group_id=v_group)<>0 then
      raise exception 'CP6 late-return-after-claim-reversal conservation diverged: %',v_response;
    end if;
    raise exception using errcode='P0699',message='CP6_LATE_RETURN_PROOF_ROLLBACK';
  exception when sqlstate 'P0699' then
    if sqlerrm='CP6_LATE_RETURN_PROOF_ROLLBACK' then v_failed:=true; else raise; end if;
  end;
  if not v_failed
     or not exists(select 1 from erp.laundry_claims where id=v_claim and status='WRITTEN_OFF')
     or not exists(select 1 from erp.laundry_deliveries where id=v_delivery and status='PARTIAL_RETURN')
     or (select count(*) from erp.laundry_receipts where delivery_id=v_delivery and status='POSTED')<>1 then
    raise exception 'CP6 disposable late-return proof did not restore its exact starting history';
  end if;

  -- A product/model/size match is not sufficient lineage. Prove a permissioned
  -- caller cannot consume Group A's exact Laundry return while minting FG/HPP
  -- under another Potongan and PO that happen to use the same model and size.
  insert into erp.production_orders(
    id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,
    physical_start_at,notes
  ) values(
    v_foreign_po,'CP6-PO-FOREIGN','a2000000-0000-0000-0000-000000000001',
    'a1000000-0000-0000-0000-000000000001',1,'CUTTING','CUTTING',
    '2026-09-01 07:00+00','Must never consume another PO Laundry source'
  );
  insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes)
  values(v_foreign_cut_batch,v_foreign_po,'CP6-CUT-FOREIGN','2026-09-01 08:00+00','OPEN','Cross-PO rejection fixture');
  insert into erp.cutting_groups(
    id,po_id,group_number,cut_at,status,cutting_batch_id,pattern_id,notes
  ) values(
    v_foreign_group,v_foreign_po,'CP6-GROUP-FOREIGN','2026-09-01 08:00+00','CUT',
    v_foreign_cut_batch,v_pattern,'Must retain its own physical lineage'
  );
  insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id,drawing_no)
  values(v_foreign_slot,v_foreign_group,1,v_size_s,1);
  insert into erp.cutting_group_rolls(
    id,cutting_group_id,roll_id,qty_issued,qty_consumed,qty_reported_remaining,
    qty_physically_returned,return_destination,unit_cost_snapshot,notes
  ) values(
    v_foreign_group_roll,v_foreign_group,v_roll,1,1,0,0,'NONE',0,
    'Cross-PO lineage rejection fixture only'
  );
  insert into erp.cutting_roll_yields(id,cutting_group_roll_id,size_slot_id,qty_pcs)
  values(v_foreign_yield,v_foreign_group_roll,v_foreign_slot,1);
  select row_version into v_foreign_group_version
  from erp.cutting_groups where id=v_foreign_group;

  v_failed:=false;
  begin
    insert into erp.qc_inspections(
      id,inspection_number,po_id,physical_at,status,notes,created_by,
      destination_location_id
    ) values(
      v_foreign_qc,'CP6-QC-FOREIGN-DIRECT',v_foreign_po,
      '2026-09-01 13:00+00','DRAFT','Trusted-writer cross-lineage probe',
      v_owner_app,v_fg_location
    );
    insert into erp.qc_inspection_items(
      inspection_id,cutting_group_id,source_laundry_receipt_line_id,
      source_laundry_receipt_batch_size_line_id,final_product_id,
      qty_good_pcs,qty_bs_pcs,notes
    ) values(
      v_foreign_qc,v_foreign_group,v_receipt_line,v_receipt_size_line,
      v_product_s,1,0,'Must be rejected by the table trigger itself'
    );
  exception when others then
    if sqlerrm='QC batch/size source belongs to a different Potongan/PO'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed or exists(select 1 from erp.qc_inspections where id=v_foreign_qc) then
    raise exception 'CP6 trusted writer bypassed the cross-Potongan/PO source trigger';
  end if;

  v_failed:=false;
  begin
    insert into erp.qc_inspections(
      id,inspection_number,po_id,physical_at,status,notes,created_by,
      destination_location_id
    ) values(
      v_foreign_qc,'CP6-QC-UNLINKED-DIRECT',v_po,
      '2026-09-01 13:00+00','DRAFT','Trusted-writer missing size-lineage probe',
      v_owner_app,v_fg_location
    );
    insert into erp.qc_inspection_items(
      inspection_id,cutting_group_id,source_laundry_receipt_line_id,
      final_product_id,qty_good_pcs,qty_bs_pcs,notes
    ) values(
      v_foreign_qc,v_group,v_receipt_line,v_product_s,1,0,
      'A private writer still may not omit exact receipt/batch/size lineage'
    );
  exception when sqlstate '23514' then
    if sqlerrm='CP6_LAUNDRY_SIZE_LINEAGE_REQUIRED'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed or exists(select 1 from erp.qc_inspections where id=v_foreign_qc) then
    raise exception 'CP6 trusted receipt-linked QC writer bypassed exact batch/size lineage';
  end if;

  -- Prove the table boundary itself conserves one exact receipt/batch/size,
  -- independently of the broader Potongan remainder checked by the facade.
  -- The receipt-size source contains five Good pieces, so six must fail and
  -- roll the temporary QC header back with the rejected item.
  v_failed:=false;
  begin
    insert into erp.qc_inspections(
      id,inspection_number,po_id,physical_at,status,notes,created_by,
      destination_location_id
    ) values(
      v_foreign_qc,'CP6-QC-SOURCE-OVERAGE-DIRECT',v_po,
      '2026-09-01 13:00+00','DRAFT','Trusted-writer exact source cap probe',
      v_owner_app,v_fg_location
    );
    insert into erp.qc_inspection_items(
      inspection_id,cutting_group_id,source_laundry_receipt_line_id,
      source_laundry_receipt_batch_size_line_id,final_product_id,
      qty_good_pcs,qty_bs_pcs,notes
    ) values(
      v_foreign_qc,v_group,v_receipt_line,v_receipt_size_line,
      v_product_s,6,0,'Must exceed this exact five-piece Good source'
    );
  exception when others then
    if sqlerrm like 'QC quantity exceeds GOOD returned for the exact Laundry batch/size.%'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed or exists(select 1 from erp.qc_inspections where id=v_foreign_qc) then
    raise exception 'CP6 exact receipt/batch/size cap failed or left QC residue';
  end if;

  execute 'set local role authenticated';
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',jsonb_build_object(
        'cutting_group_id',v_foreign_group,
        'destination_location_id',v_fg_location,
        'physical_at','2026-09-01T13:00:00+00',
        'reason','CP6 cross-Potongan source must fail closed',
        'good_qty_pcs',1,'completion_mode','PARTIAL_SELECTION',
        'lines',jsonb_build_array(jsonb_build_object(
          'final_product_id',v_product_s,'qty_good_pcs',1,'qty_bs_pcs',0,
          'source_laundry_receipt_line_id',v_receipt_line,
          'source_laundry_receipt_batch_size_line_id',v_receipt_size_line,
          'notes','This source belongs to the primary Potongan, not this PO'
        ))
      ),gen_random_uuid(),v_foreign_group_version
    );
  exception when others then
    if sqlerrm='Every Final SKU source must belong to the same Potongan and an authoritative POSTED Laundry receipt'
       or sqlerrm='QC batch/size source belongs to a different Potongan/PO'
      then v_failed:=true; else raise; end if;
  end;
  execute 'reset role';
  if not v_failed
     or exists(select 1 from erp.qc_inspections where po_id=v_foreign_po)
     or exists(select 1 from erp.fg_lots where po_id=v_foreign_po)
     or exists(select 1 from erp.hpp_versions h join erp.fg_lots l on l.id=h.lot_id where l.po_id=v_foreign_po)
     or exists(select 1 from erp.journal_lines where po_id=v_foreign_po) then
    raise exception 'CP6 cross-Potongan/PO Final-SKU rejection failed or left finance/stock/HPP residue';
  end if;

  select row_version into v_group_version from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_workspace:=public.erp_get_laundry_qc_workspace_v1('QC','CP6-PO-001');
  if v_workspace->>'scope'<>'QC'
     or jsonb_array_length(v_workspace->'ready_batches')<>0
     or jsonb_array_length(v_workspace->'deliveries')<>0
     or jsonb_array_length(v_workspace->'qc_queue')<>1
     or (v_workspace#>>'{qc_queue,0,available_for_qc_qty_pcs}')::integer<>5
     or v_workspace#>>'{qc_queue,0,source_batch_size_line_id}'<>v_receipt_size_line::text then
    raise exception 'CP6 QC workspace leaked scope or did not expose exact Good-only capacity: %',v_workspace;
  end if;

  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',jsonb_build_object(
        'cutting_group_id',v_group,'destination_location_id',v_fg_location,
        'physical_at','2026-09-01T11:59:59+00','reason','CP6 QC chronology must fail',
        'good_qty_pcs',1,'completion_mode','PARTIAL_SELECTION',
        'lines',jsonb_build_array(jsonb_build_object(
          'final_product_id',v_product_s,'qty_good_pcs',1,'qty_bs_pcs',0,
          'source_laundry_receipt_line_id',v_receipt_line,
          'source_laundry_receipt_batch_size_line_id',v_receipt_size_line
        ))
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='QC physical time cannot be earlier than its authoritative Laundry receipt'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 accepted QC before its physical Laundry receipt'; end if;

  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',jsonb_build_object(
        'cutting_group_id',v_group,'destination_location_id',v_fg_location,
        'physical_at','2026-09-01T13:00:00+00','reason','CP6 wrong size must fail',
        'good_qty_pcs',1,'completion_mode','PARTIAL_SELECTION',
        'lines',jsonb_build_array(jsonb_build_object(
          'final_product_id',v_product_m,'qty_good_pcs',1,'qty_bs_pcs',0,
          'source_laundry_receipt_line_id',v_receipt_line,
          'source_laundry_receipt_batch_size_line_id',v_receipt_size_line
        ))
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='Final SKU must be active at physical QC time and match the Laundry receipt model/size' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 accepted a Final SKU with the wrong physical size'; end if;

  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',jsonb_build_object(
        'cutting_group_id',v_group,'destination_location_id',v_fg_location,
        'physical_at','2026-09-01T13:00:00+00','reason','CP6 wrong model must fail',
        'good_qty_pcs',1,'completion_mode','PARTIAL_SELECTION',
        'lines',jsonb_build_array(jsonb_build_object(
          'final_product_id',v_wrong_model_product,'qty_good_pcs',1,'qty_bs_pcs',0,
          'source_laundry_receipt_line_id',v_receipt_line,
          'source_laundry_receipt_batch_size_line_id',v_receipt_size_line
        ))
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='Final SKU must be active at physical QC time and match the Laundry receipt model/size' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 accepted a Final SKU from another model with the same size'; end if;

  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',jsonb_build_object(
        'cutting_group_id',v_group,'destination_location_id',v_fg_location,
        'physical_at','2026-09-01T13:00:00+00','reason','CP6 expired SKU must fail',
        'good_qty_pcs',1,'completion_mode','PARTIAL_SELECTION',
        'lines',jsonb_build_array(jsonb_build_object(
          'final_product_id',v_expired_product,'qty_good_pcs',1,'qty_bs_pcs',0,
          'source_laundry_receipt_line_id',v_receipt_line,
          'source_laundry_receipt_batch_size_line_id',v_receipt_size_line
        ))
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='Every Good allocation requires an active Final SKU at physical_at'
       or sqlerrm='Final SKU must be active at physical QC time and match the Laundry receipt model/size'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 accepted an expired Final SKU at physical QC time'; end if;

  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',jsonb_build_object(
        'cutting_group_id',v_group,'destination_location_id',v_fg_location,
        'physical_at','2026-09-01T13:00:00+00','reason','CP6 missing source must fail',
        'good_qty_pcs',1,'completion_mode','PARTIAL_SELECTION',
        'lines',jsonb_build_array(jsonb_build_object(
          'final_product_id',v_product_s,'qty_good_pcs',1,'qty_bs_pcs',0
        ))
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    -- Exact Laundry lineage is part of the closed public payload contract.
    -- Omitting it must fail before any semantic quantity or source lookup.
    if sqlerrm='CP6 POST_FINAL_SKU line requires non-null key source_laundry_receipt_line_id'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 connected writer accepted source-less direct QC'; end if;

  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',jsonb_build_object(
        'cutting_group_id',v_group,'destination_location_id',v_fg_location,
        'physical_at','2026-09-01T13:00:00+00','reason','CP6 exact source overage must fail',
        'good_qty_pcs',6,'completion_mode','PARTIAL_SELECTION',
        'lines',jsonb_build_array(jsonb_build_object(
          'final_product_id',v_product_s,'qty_good_pcs',6,'qty_bs_pcs',0,
          'source_laundry_receipt_line_id',v_receipt_line,
          'source_laundry_receipt_batch_size_line_id',v_receipt_size_line
        ))
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm like 'Qty penyelesaian melebihi sisa Potongan.%'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 facade accepted quantity above authoritative Potongan remainder'; end if;

  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',jsonb_build_object(
        'cutting_group_id',v_group,'destination_location_id',v_fg_location,
        'physical_at','2026-09-01T13:00:00+00','reason','CP6 string Good must fail',
        'good_qty_pcs','4','completion_mode','ALL_READY',
        'lines',jsonb_build_array(jsonb_build_object(
          'final_product_id',v_product_s,'qty_good_pcs',4,'qty_bs_pcs',1,
          'source_laundry_receipt_line_id',v_receipt_line,
          'source_laundry_receipt_batch_size_line_id',v_receipt_size_line
        ))
      ),gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='CP6 POST_FINAL_SKU payload has invalid field types'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 coerced a string into declared Final-SKU Good quantity'; end if;

  -- The browser may suggest a completion label, but only the post-mutation
  -- authoritative balance may prove it.  Both lies must roll the entire
  -- nested QC/FG/BS/finance transaction and its idempotency envelope back.
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',jsonb_build_object(
        'cutting_group_id',v_group,'destination_location_id',v_fg_location,
        'physical_at','2026-09-01T13:00:00+00',
        'reason','CP6 false ALL READY must fail atomically',
        'good_qty_pcs',1,'completion_mode','ALL_READY',
        'lines',jsonb_build_array(jsonb_build_object(
          'final_product_id',v_product_s,'qty_good_pcs',1,'qty_bs_pcs',0,
          'source_laundry_receipt_line_id',v_receipt_line,
          'source_laundry_receipt_batch_size_line_id',v_receipt_size_line
        ))
      ),v_false_all_ready_request,v_group_version
    );
  exception when others then
    if sqlerrm like 'CP6 completion_mode ALL_READY conflicts with authoritative ready-for-QC remainder %'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 trusted a false ALL_READY browser declaration'; end if;

  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',jsonb_build_object(
        'cutting_group_id',v_group,'destination_location_id',v_fg_location,
        'physical_at','2026-09-01T13:00:00+00',
        'reason','CP6 false PARTIAL must fail atomically',
        'good_qty_pcs',4,'completion_mode','PARTIAL_SELECTION',
        'lines',jsonb_build_array(jsonb_build_object(
          'final_product_id',v_product_s,'qty_good_pcs',4,'qty_bs_pcs',1,
          'source_laundry_receipt_line_id',v_receipt_line,
          'source_laundry_receipt_batch_size_line_id',v_receipt_size_line
        ))
      ),v_false_partial_request,v_group_version
    );
  exception when others then
    if sqlerrm like 'CP6 completion_mode PARTIAL_SELECTION conflicts with authoritative ready-for-QC remainder %'
      then v_failed:=true; else raise; end if;
  end;
  execute 'reset role';
  if not v_failed
     or exists(select 1 from erp.qc_inspections where po_id=v_po)
     or exists(select 1 from erp.fg_lots where po_id=v_po)
     or exists(select 1 from erp.bs_cases b join erp.qc_inspection_items i on i.id=b.qc_item_id
       where i.cutting_group_id=v_group)
     or exists(select 1 from erp.idempotency_requests
       where client_request_id in(v_false_all_ready_request,v_false_partial_request)) then
    raise exception 'CP6 completion-mode rejection left QC, FG, BS, finance, or idempotency residue';
  end if;

  v_qc_payload:=jsonb_build_object(
    'cutting_group_id',v_group,'destination_location_id',v_fg_location,
    'physical_at','2026-09-01T13:00:00+00','reason','CP6 physical QC and Final SKU checked',
    'good_qty_pcs',4,'completion_mode','ALL_READY',
    'lines',jsonb_build_array(jsonb_build_object(
      'final_product_id',v_product_s,'qty_good_pcs',4,'qty_bs_pcs',1,
      'source_laundry_receipt_line_id',v_receipt_line,
      'source_laundry_receipt_batch_size_line_id',v_receipt_size_line,
      'notes','Exact CP6 receipt/batch/size source'
    ))
  );
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'POST_FINAL_SKU',v_qc_payload,v_qc_request,v_group_version
  );
  v_replay:=public.erp_save_laundry_qc_action_v1(
    'POST_FINAL_SKU',v_qc_payload,v_qc_request,v_group_version
  );
  execute 'reset role';
  if v_response is distinct from v_replay
     or v_response->>'contract_version'<>'CP6_V2620'
     or v_response->>'client_request_id'<>v_qc_request::text
     or (v_response->>'committed')::boolean is distinct from true
     or v_response->>'document_status'<>'POSTED'
     or (v_response->>'good_qty_pcs')::integer<>4
     or (v_response->>'bs_qty_pcs')::integer<>1
     or (v_response->>'fg_stock_in_qty_pcs')::integer<>4
     or (v_response->>'browser_formula_used')::boolean is distinct from false then
    raise exception 'CP6 QC/Final-SKU posting or replay diverged: %, %',v_response,v_replay;
  end if;
  v_qc:=(v_response->>'qc_inspection_id')::uuid;
  v_qc_version:=(v_response->>'qc_row_version')::bigint;
  select coalesce(sum(h.total_cost),0) into v_hpp
  from erp.hpp_versions h join erp.fg_lots l on l.id=h.lot_id
  where l.po_id=v_po and l.lot_origin='PRODUCTION' and h.is_current;
  if (select count(*) from erp.qc_inspection_items
      where inspection_id=v_qc and source_laundry_receipt_batch_size_line_id=v_receipt_size_line)<>1
     or (select coalesce(sum(qty_signed),0) from erp.fg_stock_movements
       where source_type='QC_ITEM' and source_id in(
         select id from erp.qc_inspection_items where inspection_id=v_qc
       ))<>4
     or (select count(*) from erp.bs_cases where qc_item_id in(
       select id from erp.qc_inspection_items where inspection_id=v_qc
     ) and qty_pcs=1 and status='OPEN')<>1
     or v_hpp<>70
     or (select hpp_total_cost from erp.po_hpp_gl_state where po_id=v_po)<>70
     or (select fg_value from erp.po_hpp_gl_state where po_id=v_po)<>70
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('WIP'))<>0
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('FG_INVENTORY'))<>70
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('ACCRUED_MANUFACTURING'))<>-70
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('AP_VENDOR'))<>0
     or exists(
       select 1 from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
       where e.status='POSTED' group by e.id having sum(l.debit)<>sum(l.credit)
     ) then
    raise exception 'CP6 FG stock, QC BS, HPP, or balanced-report invariant failed (HPP %)',v_hpp;
  end if;
  if not exists(
    select 1 from erp.v_fg_partial_completion_progress
    where cutting_group_id=v_group and qc_good_qty_pcs=4 and qc_bs_qty_pcs=6
      and qc_accounted_qty_pcs=10 and ready_for_qc_qty_pcs=0
      and laundry_outstanding_qty_pcs=0 and remaining_qc_qty_pcs=0
  ) then raise exception 'CP6 terminal quantity conservation failed after QC'; end if;

  execute 'set local role authenticated';
  v_workspace:=public.erp_get_laundry_qc_workspace_v1('QC','CP6-PO-001');
  if jsonb_array_length(v_workspace->'qc_history')<>1
     or (v_workspace#>>'{qc_history,0,reversible}')::boolean is distinct from true
     or v_workspace#>'{qc_history,0,reversal_blocker}' is distinct from 'null'::jsonb then
    raise exception 'CP6 QC workspace did not expose the authoritative reversal decision';
  end if;
  v_workspace:=public.erp_get_laundry_qc_workspace_v1('LAUNDRY','CP6-PO-001');
  execute 'reset role';
  if (v_workspace#>>'{deliveries,0,reversible}')::boolean is distinct from false
     or v_workspace#>>'{deliveries,0,reversal_blocker}'
        <>'Masih ada receipt aktif; reverse receipt terlebih dahulu.'
     or (v_workspace#>>'{deliveries,0,receipts,0,reversible}')::boolean is distinct from false
     or v_workspace#>>'{deliveries,0,receipts,0,reversal_blocker}'
        <>'Receipt sudah dipakai QC; reverse QC aktif terlebih dahulu.' then
    raise exception 'CP6 Laundry workspace offered a reversal that backend authority must reject';
  end if;

  -- A late vendor invoice is the financial finalization boundary.  The
  -- physical receipt remains immutable while AP, accrual, HPP, and FG value
  -- move together.  Reversal must restore the exact estimated snapshot, and
  -- a replacement invoice must be a new auditable document, never overwrite.
  insert into erp.vendor_invoices(
    id,invoice_number,vendor_id,invoice_date,received_at,due_date,
    status,total_amount,notes,created_by
  ) values(
    v_late_invoice,'CP6-LATE-VI-001',v_vendor,'2026-09-03','2026-09-03 08:00:00+00',
    '2026-09-17','DRAFT',54,'CP6 late actual Laundry invoice',v_owner_app
  );
  insert into erp.vendor_invoice_items(
    id,invoice_id,receipt_line_id,description,qty_pcs,actual_rate,actual_amount
  ) values(
    v_late_invoice_item,v_late_invoice,v_receipt_line,
    'Six physically returned pieces at actual rate 9',6,9,54
  );
  perform erp.post_vendor_invoice(v_late_invoice);
  select coalesce(sum(h.total_cost),0) into v_hpp
  from erp.hpp_versions h join erp.fg_lots l on l.id=h.lot_id
  where l.po_id=v_po and l.lot_origin='PRODUCTION' and h.is_current;
  if (select status from erp.vendor_invoices where id=v_late_invoice)<>'POSTED'
     or (select actual_cost_status from erp.laundry_receipt_lines where id=v_receipt_line)<>'FINAL'
     or (select actual_rate_snapshot from erp.laundry_receipt_lines where id=v_receipt_line)<>9
     or (select actual_cost from erp.laundry_receipt_lines where id=v_receipt_line)<>54
     or (select prior_actual_cost_status from erp.vendor_invoice_items where id=v_late_invoice_item)<>'ESTIMATED'
     or (select prior_actual_rate_snapshot from erp.vendor_invoice_items where id=v_late_invoice_item)<>7
     or (select prior_actual_cost from erp.vendor_invoice_items where id=v_late_invoice_item)<>42
     or (select accrued_amount from erp.laundry_cost_accrual_state where po_id=v_po)<>28
     or erp.desired_laundry_accrual(v_po)<>28
     or v_hpp<>82
     or (select hpp_total_cost from erp.po_hpp_gl_state where po_id=v_po)<>82
     or (select fg_value from erp.po_hpp_gl_state where po_id=v_po)<>82
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('WIP'))<>0
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('FG_INVENTORY'))<>82
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('ACCRUED_MANUFACTURING'))<>-28
     or (select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l
       where l.vendor_id=v_vendor and l.account_id=erp.account_id('AP_VENDOR'))<>54
     or exists(
       select 1 from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
       where e.status='POSTED' group by e.id having sum(l.debit)<>sum(l.credit)
     ) then
    raise exception 'CP6 late Laundry invoice did not atomically finalize AP/accrual/HPP/FG (HPP %)',v_hpp;
  end if;

  perform erp.reverse_vendor_invoice(
    v_late_invoice,'CP6 wrong late invoice reversed without changing receipt history'
  );
  select coalesce(sum(h.total_cost),0) into v_hpp
  from erp.hpp_versions h join erp.fg_lots l on l.id=h.lot_id
  where l.po_id=v_po and l.lot_origin='PRODUCTION' and h.is_current;
  if (select status from erp.vendor_invoices where id=v_late_invoice)<>'REVERSED'
     or (select actual_cost_status from erp.laundry_receipt_lines where id=v_receipt_line)<>'ESTIMATED'
     or (select actual_rate_snapshot from erp.laundry_receipt_lines where id=v_receipt_line)<>7
     or (select actual_cost from erp.laundry_receipt_lines where id=v_receipt_line)<>42
     or (select accrued_amount from erp.laundry_cost_accrual_state where po_id=v_po)<>70
     or erp.desired_laundry_accrual(v_po)<>70
     or v_hpp<>70
     or (select hpp_total_cost from erp.po_hpp_gl_state where po_id=v_po)<>70
     or (select fg_value from erp.po_hpp_gl_state where po_id=v_po)<>70
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('WIP'))<>0
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('FG_INVENTORY'))<>70
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('ACCRUED_MANUFACTURING'))<>-70
     or (select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l
       where l.vendor_id=v_vendor and l.account_id=erp.account_id('AP_VENDOR'))<>0 then
    raise exception 'CP6 late invoice reversal did not restore estimated accrual/HPP/FG exactly (HPP %)',v_hpp;
  end if;

  insert into erp.vendor_invoices(
    id,invoice_number,vendor_id,invoice_date,received_at,due_date,
    status,total_amount,notes,created_by
  ) values(
    v_replacement_invoice,'CP6-REPLACEMENT-VI-001',v_vendor,'2026-09-04','2026-09-04 08:00:00+00',
    '2026-09-18','DRAFT',48,'CP6 replacement for reversed late invoice',v_owner_app
  );
  insert into erp.vendor_invoice_items(
    id,invoice_id,receipt_line_id,description,qty_pcs,actual_rate,actual_amount
  ) values(
    v_replacement_invoice_item,v_replacement_invoice,v_receipt_line,
    'Replacement invoice: six pieces at actual rate 8',6,8,48
  );
  perform erp.post_vendor_invoice(v_replacement_invoice);
  select coalesce(sum(h.total_cost),0) into v_hpp
  from erp.hpp_versions h join erp.fg_lots l on l.id=h.lot_id
  where l.po_id=v_po and l.lot_origin='PRODUCTION' and h.is_current;
  if (select status from erp.vendor_invoices where id=v_replacement_invoice)<>'POSTED'
     or (select actual_cost_status from erp.laundry_receipt_lines where id=v_receipt_line)<>'FINAL'
     or (select actual_rate_snapshot from erp.laundry_receipt_lines where id=v_receipt_line)<>8
     or (select actual_cost from erp.laundry_receipt_lines where id=v_receipt_line)<>48
     or (select accrued_amount from erp.laundry_cost_accrual_state where po_id=v_po)<>28
     or v_hpp<>76
     or (select hpp_total_cost from erp.po_hpp_gl_state where po_id=v_po)<>76
     or (select fg_value from erp.po_hpp_gl_state where po_id=v_po)<>76
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('WIP'))<>0
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('FG_INVENTORY'))<>76
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('ACCRUED_MANUFACTURING'))<>-28
     or (select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l
       where l.vendor_id=v_vendor and l.account_id=erp.account_id('AP_VENDOR'))<>48 then
    raise exception 'CP6 replacement invoice did not replace financial state atomically (HPP %)',v_hpp;
  end if;
  perform erp.reverse_vendor_invoice(
    v_replacement_invoice,'CP6 replacement invoice reversed before source reversal'
  );
  -- Replaying an already completed reversal is a no-op; history cannot double.
  perform erp.reverse_vendor_invoice(
    v_replacement_invoice,'CP6 replacement invoice reversal retry'
  );
  select coalesce(sum(h.total_cost),0) into v_hpp
  from erp.hpp_versions h join erp.fg_lots l on l.id=h.lot_id
  where l.po_id=v_po and l.lot_origin='PRODUCTION' and h.is_current;
  if (select status from erp.vendor_invoices where id=v_replacement_invoice)<>'REVERSED'
     or (select actual_cost_status from erp.laundry_receipt_lines where id=v_receipt_line)<>'ESTIMATED'
     or (select actual_rate_snapshot from erp.laundry_receipt_lines where id=v_receipt_line)<>7
     or (select actual_cost from erp.laundry_receipt_lines where id=v_receipt_line)<>42
     or (select accrued_amount from erp.laundry_cost_accrual_state where po_id=v_po)<>70
     or erp.desired_laundry_accrual(v_po)<>70
     or v_hpp<>70
     or (select hpp_total_cost from erp.po_hpp_gl_state where po_id=v_po)<>70
     or (select fg_value from erp.po_hpp_gl_state where po_id=v_po)<>70
     or (select count(*) from erp.cost_adjustments
       where source_id in(v_late_invoice_item,v_replacement_invoice_item)
         and source_type in('VENDOR_INVOICE_ITEM','VENDOR_INVOICE_REVERSAL'))<>4
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('WIP'))<>0
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('FG_INVENTORY'))<>70
     or (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
       where l.po_id=v_po and l.account_id=erp.account_id('ACCRUED_MANUFACTURING'))<>-70
     or (select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l
       where l.vendor_id=v_vendor and l.account_id=erp.account_id('AP_VENDOR'))<>0
     or exists(
       select 1 from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
       where e.status='POSTED' group by e.id having sum(l.debit)<>sum(l.credit)
     ) then
    raise exception 'CP6 invoice replacement/retry left financial residue or duplicated history (HPP %)',v_hpp;
  end if;

  execute 'set local role authenticated';
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'REVERSE_RECEIPT',jsonb_build_object(
        'receipt_id',v_receipt,'reason','CP6 dependency reversal must fail'
      ),gen_random_uuid(),v_receipt_version
    );
  exception when others then
    if sqlerrm='Penerimaan laundry ini sudah dipakai QC. Reverse QC aktif terlebih dahulu.' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 reversed a Laundry receipt while active QC depended on it'; end if;

  v_response:=public.erp_save_laundry_qc_action_v1(
    'REVERSE_FINAL_SKU',jsonb_build_object(
      'qc_inspection_id',v_qc,'reason','CP6 controlled QC reversal'
    ),gen_random_uuid(),v_qc_version
  );
  if v_response->>'status'<>'REVERSED' then raise exception 'CP6 QC reversal failed: %',v_response; end if;
  execute 'reset role';
  perform erp.reverse_laundry_claim_resolution(v_claim,'CP6 reverse terminal claim before physical source reversal');
  if (select status from erp.laundry_claims where id=v_claim)<>'REJECTED' then
    raise exception 'CP6 claim resolution reversal did not restore physical outstanding';
  end if;
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'REVERSE_RECEIPT',jsonb_build_object(
      'receipt_id',v_receipt,'reason','CP6 controlled receipt reversal'
    ),gen_random_uuid(),v_receipt_version
  );
  if v_response->>'status'<>'REVERSED' then raise exception 'CP6 receipt reversal failed: %',v_response; end if;
  execute 'reset role';
  select row_version into v_group_version from erp.cutting_groups where id=v_group;
  execute 'set local role authenticated';
  v_failed:=false;
  begin
    perform public.erp_save_laundry_qc_action_v1(
      'POST_FINAL_SKU',v_qc_payload,gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm='Every Final SKU source must belong to the same Potongan and an authoritative POSTED Laundry receipt'
      then v_failed:=true; else raise; end if;
  end;
  if not v_failed then
    raise exception 'CP6 allowed Final SKU/QC posting after its Laundry receipt was reversed';
  end if;
  execute 'reset role';
  v_delivery_version:=(select row_version from erp.laundry_deliveries where id=v_delivery);
  execute 'set local role authenticated';
  v_response:=public.erp_save_laundry_qc_action_v1(
    'REVERSE_DELIVERY',jsonb_build_object(
      'delivery_id',v_delivery,'reason','CP6 failed wash no-charge redispatch boundary'
    ),gen_random_uuid(),v_delivery_version
  );
  execute 'reset role';
  if v_response->>'status'<>'REVERSED'
     or (select accrued_amount from erp.laundry_cost_accrual_state where po_id=v_po)<>0
     or (select coalesce(hpp_total_cost,0) from erp.po_hpp_gl_state where po_id=v_po)<>0
     or (select coalesce(fg_value,0) from erp.po_hpp_gl_state where po_id=v_po)<>0
     or exists(
       select 1 from erp.journal_lines l where l.po_id=v_po
       group by l.account_id having abs(sum(l.debit-l.credit))>0.005
     )
     or exists(
       select 1 from erp.fg_stock_movements m
       where m.source_type='QC_ITEM' and m.source_id in(
         select id from erp.qc_inspection_items where inspection_id=v_qc
       ) and m.movement_type<>'REVERSAL'
         and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)
     )
     or (select count(*) from erp.laundry_delivery_batch_size_lines
       where id=v_delivery_size_line)<>1
     or (select count(*) from erp.laundry_receipt_batch_size_lines
       where id=v_receipt_size_line)<>1 then
    raise exception 'CP6 controlled reversal lost history or left active stock/accrual';
  end if;
  if (select count(*) from erp.wip_stage_events
      where cutting_group_id=v_group and source_type in(
        'LAUNDRY_DELIVERY_LINE','LAUNDRY_RECEIPT_LINE',
        'CP6_LAUNDRY_BS_SIZE_LINE',
        'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL',
        'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL',
        'CP6_LAUNDRY_BS_WIP_REVERSAL'
      ))<>6
     or exists(
       select 1
       from unnest(array['SEWING','LAUNDRY','QC','ON_HOLD']) stage(name)
       where(
         select coalesce(sum(
           case when w.stage_to=stage.name then w.qty_pcs else 0 end
           -case when w.stage_from=stage.name then w.qty_pcs else 0 end
         ),0)
         from erp.wip_stage_events w
         where w.cutting_group_id=v_group and w.source_type in(
           'LAUNDRY_DELIVERY_LINE','LAUNDRY_RECEIPT_LINE',
           'CP6_LAUNDRY_BS_SIZE_LINE',
           'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL',
           'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL',
           'CP6_LAUNDRY_BS_WIP_REVERSAL'
         )
       )<>0
     ) then
    raise exception 'CP6 append-only Laundry WIP reversal history is not net zero';
  end if;

  v_failed:=false;
  begin
    update erp.laundry_delivery_batch_size_lines set qty_sent_pcs=9 where id=v_delivery_size_line;
  exception when sqlstate '42501' then
    if sqlerrm='POSTED_LAUNDRY_BATCH_SIZE_LINEAGE_IMMUTABLE' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 allowed historical delivery size overwrite'; end if;
  v_failed:=false;
  begin
    delete from erp.laundry_receipt_batch_size_lines where id=v_receipt_size_line;
  exception when sqlstate '42501' then
    if sqlerrm='POSTED_LAUNDRY_RECEIPT_BATCH_SIZE_LINEAGE_IMMUTABLE' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP6 allowed historical receipt size deletion'; end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'CP6 transaction-scoped internal context leaked';
  end if;

  execute 'set local role authenticated';
  v_workspace:=public.erp_get_laundry_qc_workspace_v1('QC','CP6-PO-001');
  execute 'reset role';
  if v_workspace#>>'{readiness,lineage_integrity_ok}'<>'true'
     or (v_workspace#>>'{readiness,lineage_issue_count}')::bigint<>0 then
    raise exception 'CP6 reversal chain did not return to an exact, readable lineage state: %',v_workspace;
  end if;

  raise notice 'CP6_AUTHORITATIVE_ACCEPTANCE_PASS %',jsonb_build_object(
    'delivery_qty',10,'receipt_good',5,'receipt_bs',1,'resolved_stuck',4,'qc_good',4,'qc_bs',1,
    'fg_stock',4,'hpp_total',v_hpp,'unbilled_accrual_before_reversal',70,
    'late_invoice_hpp',82,'replacement_invoice_hpp',76,
    'invoice_reversal_replay','NO_OP','replacement_history_preserved',true,
    'final_active_accrual',0,'final_po_ledger_net',0,
    'history_preserved',true,'browser_formula_used',false,'production_go',false
  );
end
$test$;

rollback;

do $residue$
begin
  if exists(select 1 from erp.app_users where id='c7000000-0000-4000-8000-000000000001')
     or exists(select 1 from erp.production_orders where id='c7040000-0000-4000-8000-000000000001')
     or exists(select 1 from erp.laundry_deliveries where po_id='c7040000-0000-4000-8000-000000000001')
     or exists(select 1 from erp.laundry_receipts where delivery_id in(
       select id from erp.laundry_deliveries where po_id='c7040000-0000-4000-8000-000000000001'
     ))
     or exists(select 1 from erp.qc_inspections where po_id='c7040000-0000-4000-8000-000000000001')
     or exists(select 1 from erp.laundry_claims where id='c7070000-0000-4000-8000-000000000001')
     or exists(select 1 from erp.vendor_invoices where id in(
       'c7080000-0000-4000-8000-000000000001',
       'c7080000-0000-4000-8000-000000000003'
     ))
     or exists(select 1 from erp.idempotency_requests where client_request_id in(
       'c7060000-0000-4000-8000-000000000001',
       'c7060000-0000-4000-8000-000000000002',
       'c7060000-0000-4000-8000-000000000003'
     )) then
    raise exception 'CP6 acceptance left transaction residue';
  end if;
  raise notice 'CP6_AUTHORITATIVE_RESIDUE_ZERO';
end
$residue$;
